"""Раскладка города: кому какой участок.

Мир делим на сетку участков вокруг центра. Новые постройки занимают
свободные участки по спирали от центра, поэтому город растёт плотно
и равномерно, а не длинной кишкой. Между участками остаются дороги.

Занятые участки храним в файле, чтобы перезапуск воркера не начал
застраивать город заново поверх готового.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Iterator

from .schema import BuildProgram

PLOT = 48               # сторона участка
ROAD = 8                # ширина дороги между участками
CELL = PLOT + ROAD      # шаг сетки
MAX_RING = 14           # 29x29 участков — на день хакатона с запасом

STATE_FILE = Path(os.getenv("PLOTS_FILE", "data/plots.json"))

ROAD_BLOCK = "gray_concrete"
PLOT_BLOCK = "light_gray_concrete"

Cell = tuple[int, int]
Vec3 = tuple[int, int, int]


def spiral_cells(max_ring: int = MAX_RING) -> Iterator[Cell]:
    """Клетки сетки по спирали от центра: (0,0), потом кольцо 1, 2, …"""
    yield (0, 0)
    for r in range(1, max_ring + 1):
        for i in range(-r, r):
            yield (i, -r)
        for j in range(-r, r):
            yield (r, j)
        for i in range(r, -r, -1):
            yield (i, r)
        for j in range(r, -r, -1):
            yield (-r, j)


class City:
    """Сетка участков с запоминанием занятых."""

    def __init__(self, center: Vec3 | None = None,
                 state_file: Path | None = None):
        cx = int(os.getenv("CITY_X", 0))
        cz = int(os.getenv("CITY_Z", 0))
        ground = int(os.getenv("GROUND_Y", -60))
        self.center: Vec3 = center or (cx, ground, cz)
        self.state_file = state_file or STATE_FILE
        self.taken: dict[str, dict] = {}
        self._load()

    # --- состояние -------------------------------------------------------

    def _load(self) -> None:
        if self.state_file.exists():
            self.taken = json.loads(self.state_file.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self.taken, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reset(self) -> None:
        """Забыть всё — город можно застраивать заново (перед демо)."""
        self.taken = {}
        self._save()

    @property
    def count(self) -> int:
        return len({v["request_id"] for v in self.taken.values()
                    if v.get("request_id") is not None}) or len(self.taken)

    # --- выдача участков -------------------------------------------------

    def _cells_needed(self, size: Vec3) -> tuple[int, int]:
        """Сколько клеток нужно по x и z под постройку такого размера."""
        def need(side: int) -> int:
            # n клеток дают n*PLOT + (n-1)*ROAD полезной длины
            n = 1
            while n * PLOT + (n - 1) * ROAD < side:
                n += 1
            return n
        return need(size[0]), need(size[2])

    def reserve(self, size: Vec3, name: str = "",
                request_id: int | None = None) -> Vec3:
        """Занимает свободное место и возвращает точку постройки.

        Постройка ставится по центру занятых клеток, поэтому между
        соседями всегда остаётся дорога.
        """
        need_x, need_z = self._cells_needed(size)
        for anchor in spiral_cells():
            block = [(anchor[0] + i, anchor[1] + j)
                     for i in range(need_x) for j in range(need_z)]
            if any(f"{i},{j}" in self.taken for i, j in block):
                continue
            for i, j in block:
                self.taken[f"{i},{j}"] = {"name": name, "request_id": request_id}
            self._save()
            return self._origin_for(block, size)
        raise RuntimeError("свободных участков больше нет — увеличь MAX_RING")

    def _origin_for(self, block: list[Cell], size: Vec3) -> Vec3:
        """Точка постройки: центр занятой области по горизонтали."""
        cx, ground, cz = self.center
        min_i = min(i for i, _ in block)
        min_j = min(j for _, j in block)
        span_x = len({i for i, _ in block}) * CELL - ROAD
        span_z = len({j for _, j in block}) * CELL - ROAD
        # левый-нижний угол области участков
        base_x = cx + min_i * CELL - PLOT // 2
        base_z = cz + min_j * CELL - PLOT // 2
        return (base_x + (span_x - size[0]) // 2,
                ground,
                base_z + (span_z - size[2]) // 2)

    def pad_program(self, origin: Vec3, size: Vec3) -> BuildProgram:
        """Площадка под постройку и дорожка вокруг неё.

        Кладём на один блок ниже уровня земли, прямо вместо травы, чтобы
        постройка по-прежнему начиналась с y=0.
        """
        pad_w = min(PLOT, max(size[0] + 4, 12))
        pad_d = min(PLOT, max(size[2] + 4, 12))
        x0 = origin[0] - (pad_w - size[0]) // 2
        z0 = origin[2] - (pad_d - size[2]) // 2
        # координаты в программе относительные, origin тот же
        rx, rz = x0 - origin[0], z0 - origin[2]
        return BuildProgram(
            name="Площадка",
            size=(pad_w + 4, 1, pad_d + 4),
            parts=[
                {"type": "box", "block": ROAD_BLOCK,
                 "from": [rx - 2, -1, rz - 2],
                 "to": [rx + pad_w + 1, -1, rz + pad_d + 1]},
                {"type": "box", "block": PLOT_BLOCK,
                 "from": [rx, -1, rz],
                 "to": [rx + pad_w - 1, -1, rz + pad_d - 1]},
            ],
        )


def distance_from_center(origin: Vec3, center: Vec3) -> int:
    """Нужно только для экрана: как далеко постройка от центра города."""
    return int(math.dist((origin[0], origin[2]), (center[0], center[2])))
