"""Сборка программы в блоки и постройка в Minecraft слоями.

Два шага:
  1. render()  — программа -> словарь {абсолютная координата: блок}. Без игры.
  2. build()   — словарь -> блоки в мире, слой за слоем снизу вверх,
                 с паузой, чтобы постройка «росла» на глазах.

Запуск вручную:
    python -m builder.build programs/showcase.json
    python -m builder.build programs/lighthouse.json --clear --duration 8
    python -m builder.build programs/showcase.json --origin 100 -60 100
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

from gdpc import Block, Editor, interface

from . import primitives as P
from .schema import MAX_BLOCKS, BuildProgram

Vec3 = tuple[int, int, int]
Voxels = dict[Vec3, str]

# Настройки окружения (читаются в main(), чтобы импорт модуля был дешёвым)
DEFAULT_GROUND_Y = -60
DEFAULT_DELAY = 0.12


# --- шаг 1: программа -> воксели ----------------------------------------

cells_of = P.cells_of   # вся геометрия и выбор примитива живут в primitives.py


def render(program: BuildProgram, origin: Vec3 = (0, 0, 0)) -> Voxels:
    """Программа -> {координата: блок}. Части идут по порядку, последняя главнее.

    Благодаря этому часть с блоком "air" вырезает окна и двери в уже
    поставленной стене.
    """
    ox, oy, oz = origin
    voxels: Voxels = {}
    for part in program.parts:
        block = part.block
        for x, y, z in cells_of(part):
            voxels[(ox + x, oy + y, oz + z)] = block
    if len(voxels) > MAX_BLOCKS:
        raise ValueError(
            f"постройка слишком большая: {len(voxels)} блоков (предел {MAX_BLOCKS})"
        )
    return voxels


def layers(voxels: Voxels) -> list[tuple[int, list[tuple[Vec3, str]]]]:
    """Группирует воксели по высоте y, снизу вверх."""
    by_y: dict[int, list[tuple[Vec3, str]]] = defaultdict(list)
    for pos, block in voxels.items():
        by_y[pos[1]].append((pos, block))
    return [(y, by_y[y]) for y in sorted(by_y)]


def bounds(voxels: Voxels) -> tuple[Vec3, Vec3]:
    """Габариты постройки в абсолютных координатах."""
    xs = [p[0] for p in voxels]
    ys = [p[1] for p in voxels]
    zs = [p[2] for p in voxels]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


# --- шаг 2: воксели -> Minecraft ----------------------------------------

def make_editor(host: str = "http://localhost:9000") -> Editor:
    """Editor без обновлений блоков: быстрее, и вода/песок не расползаются."""
    editor = Editor(buffering=True, bufferLimit=4096, host=host, retries=4)
    editor.doBlockUpdates = False
    return editor


def clear_area(editor: Editor, lo: Vec3, hi: Vec3, margin: int = 0) -> None:
    """Вычищает место под постройку воздухом."""
    air = Block("air")
    for x in range(lo[0] - margin, hi[0] + margin + 1):
        for y in range(lo[1], hi[1] + margin + 1):
            for z in range(lo[2] - margin, hi[2] + margin + 1):
                editor.placeBlock((x, y, z), air)
    editor.flushBuffer()


def build(
    program: BuildProgram,
    origin: Vec3,
    editor: Editor | None = None,
    delay: float = DEFAULT_DELAY,
    duration: float | None = None,
    clear: bool = False,
    on_layer: Callable[[int, int], None] | None = None,
) -> dict:
    """Строит программу в мире слоями. Возвращает отчёт для очереди/экрана.

    delay    — пауза между слоями;
    duration — если задано, пауза подбирается так, чтобы уложиться в эти секунды;
    on_layer — колбэк (сделано_слоёв, всего_слоёв) для статусов по WebSocket.
    """
    editor = editor or make_editor()
    voxels = render(program, origin)
    stack = layers(voxels)
    lo, hi = bounds(voxels)

    if clear:
        clear_area(editor, lo, hi)

    if duration is not None and stack:
        delay = max(0.0, duration / len(stack))

    started = time.time()
    for done, (_y, cells) in enumerate(stack, start=1):
        for pos, block in cells:
            editor.placeBlock(pos, Block(block))
        editor.flushBuffer()          # слой появляется целиком
        if on_layer:
            on_layer(done, len(stack))
        if delay:
            time.sleep(delay)

    return {
        "name": program.name,
        "blocks": len(voxels),
        "layers": len(stack),
        "origin": origin,
        "bounds": [list(lo), list(hi)],
        "seconds": round(time.time() - started, 1),
    }


# --- где строить ---------------------------------------------------------

_POS_RE = re.compile(r"Pos:\[([-\d.]+)d,([-\d.]+)d,([-\d.]+)d\]")


def player_position() -> Vec3 | None:
    """Координаты первого игрока. Нужны, чтобы строить рядом с ним.

    Берём их по HTTP, а не командой с `~`: команда выполняется от имени
    сервера в точке (0,0,0), и любое `~` считается от начала координат мира.
    """
    try:
        players = interface.getPlayers()
    except Exception:
        return None
    for player in players:
        match = _POS_RE.search(player.get("data", ""))
        if match:
            x, y, z = (float(g) for g in match.groups())
            return (int(x // 1), int(y // 1), int(z // 1))
    return None


def surface_y(x: int, z: int, footprint: tuple[int, int] = (16, 16),
              host: str = "http://localhost:9000") -> int:
    """Уровень земли в точке (x, z): первый свободный блок над поверхностью.

    Берём медиану по площадке, чтобы одиночное дерево или ямка не сдвинули
    всю постройку. Нужно для обычного мира; в плоском мире проще взять GROUND_Y.
    """
    import numpy as np

    fw, fd = max(1, footprint[0]), max(1, footprint[1])
    heights = interface.getHeightmap(
        position=(x - fw // 2, 0, z - fd // 2),
        size=(fw, 1, fd),
        heightmapType="MOTION_BLOCKING_NO_LEAVES",
        host=host,
    )
    return int(np.median(heights))


def origin_near_player(offset: Vec3 = (0, 0, 20),
                       ground_y: int | str | None = DEFAULT_GROUND_Y,
                       footprint: tuple[int, int] = (16, 16),
                       host: str = "http://localhost:9000") -> Vec3:
    """Точка постройки рядом с игроком.

    ground_y:
      число      — фиксированный уровень земли (плоский мир: -60);
      "surface"  — найти поверхность по карте высот (обычный мир);
      None       — строить на высоте игрока.
    """
    pos = player_position() or (0, DEFAULT_GROUND_Y, 0)
    x, z = pos[0] + offset[0], pos[2] + offset[2]
    if ground_y is None:
        y = pos[1]
    elif ground_y == "surface":
        y = surface_y(x, z, footprint, host)
    else:
        y = int(ground_y)
    return (x, y + offset[1], z)


# --- командная строка ----------------------------------------------------

def load_program(path: str | Path, limit: int | None = None) -> BuildProgram:
    """Читает и проверяет JSON-программу с диска."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    program = BuildProgram.model_validate(data)
    if limit and not program.fits(limit):
        raise ValueError(f"{program.name}: размер {program.size} больше лимита {limit}")
    return program


def main(argv: Iterable[str] | None = None) -> None:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    ground_env = os.getenv("GROUND_Y", str(DEFAULT_GROUND_Y))
    host = os.getenv("MC_HTTP", "http://localhost:9000")

    ap = argparse.ArgumentParser(description="Построить программу в Minecraft")
    ap.add_argument("program", help="путь к JSON-программе")
    ap.add_argument("--origin", nargs=3, type=int, metavar=("X", "Y", "Z"),
                    help="точка постройки; по умолчанию рядом с игроком")
    ap.add_argument("--delay", type=float,
                    default=float(os.getenv("BUILD_DELAY", DEFAULT_DELAY)),
                    help="пауза между слоями, сек")
    ap.add_argument("--duration", type=float,
                    help="уложить всю постройку в столько секунд")
    ap.add_argument("--clear", action="store_true",
                    help="сначала вычистить место воздухом")
    ap.add_argument("--here", action="store_true",
                    help="строить на высоте игрока, а не на GROUND_Y")
    ap.add_argument("--surface", action="store_true",
                    help="найти землю по карте высот (для обычного мира)")
    ap.add_argument("--dry-run", action="store_true",
                    help="только посчитать блоки, в игру ничего не ставить")
    args = ap.parse_args(list(argv) if argv is not None else None)

    program = load_program(args.program)

    if args.origin:
        origin = tuple(args.origin)                      # type: ignore[assignment]
    else:
        ground: int | str | None = int(ground_env)
        if args.here:
            ground = None
        elif args.surface:
            ground = "surface"
        origin = origin_near_player(
            ground_y=ground,
            footprint=(program.size[0], program.size[2]),
            host=host,
        )

    if args.dry_run:
        voxels = render(program, origin)
        lo, hi = bounds(voxels)
        print(f"{program.name}: {len(voxels)} блоков, "
              f"{len(layers(voxels))} слоёв, габариты {lo} .. {hi}")
        return

    print(f"Строю «{program.name}» в {origin} …")
    report = build(
        program, origin,
        editor=make_editor(host),
        delay=args.delay,
        duration=args.duration,
        clear=args.clear,
        on_layer=lambda done, total: print(f"\r  слой {done}/{total}", end=""),
    )
    print(f"\rГотово: {report['blocks']} блоков, {report['layers']} слоёв, "
          f"{report['seconds']} сек")


if __name__ == "__main__":
    main()
