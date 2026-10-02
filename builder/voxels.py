"""Программа постройки -> воксели {координата: блок}. Без Minecraft и gdpc, поэтому
работает и на сервере, и в предпросмотре."""

from __future__ import annotations

from collections import defaultdict

from . import primitives as P
from .schema import MAX_BLOCKS, BuildProgram

Vec3 = tuple[int, int, int]
Voxels = dict[Vec3, str]

cells_of = P.cells_of      # вся геометрия и выбор примитива живут в primitives.py


def render(program: BuildProgram, origin: Vec3 = (0, 0, 0)) -> Voxels:
    """Части идут по порядку, последняя главнее: часть с блоком "air" вырезает окна
    и двери в уже поставленной стене. Часть-чертёж (blueprint) приносит готовые блоки."""
    ox, oy, oz = origin
    voxels: Voxels = {}
    for part in program.parts:
        if part.type == "blueprint":
            from .blueprints import build as build_blueprint
            for (x, y, z), block in build_blueprint(part.id, part.params).items():
                voxels[(ox + x, oy + y, oz + z)] = block
            continue
        if part.type == "voxels":
            for y, z, x0, x1, i in part.runs:
                for x in range(x0, x1 + 1):
                    voxels[(ox + x, oy + y, oz + z)] = part.palette[i]
            continue
        block = part.block
        for x, y, z in cells_of(part):
            voxels[(ox + x, oy + y, oz + z)] = block
    if len(voxels) > MAX_BLOCKS:
        raise ValueError(
            f"постройка слишком большая: {len(voxels)} блоков (предел {MAX_BLOCKS})")
    return voxels


def layers(voxels: Voxels) -> list[tuple[int, list[tuple[Vec3, str]]]]:
    """Группирует воксели по высоте y, снизу вверх."""
    by_y: dict[int, list[tuple[Vec3, str]]] = defaultdict(list)
    for pos, block in voxels.items():
        by_y[pos[1]].append((pos, block))
    return [(y, by_y[y]) for y in sorted(by_y)]


def bounds(voxels: Voxels) -> tuple[Vec3, Vec3]:
    """Габариты постройки в абсолютных координатах."""
    xs = [p[0] for p in voxels]; ys = [p[1] for p in voxels]; zs = [p[2] for p in voxels]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
