"""Transamerica Pyramid (Сан-Франциско): сужающаяся белая башня с тёмными окнами, два «крыла»
на боках и длинный шпиль; у основания — парк с секвойями."""

from __future__ import annotations

from .kit import Canvas

HB, R0, R1, C = 74, 12, 3, 20


def hw(y: float) -> float:
    return R0 - (R0 - R1) * y / HB


def build() -> dict:
    c = Canvas()
    c.box((0, 0, 0), (2 * C, 0, 2 * C), "moss_block")
    c.box((C - 2, 0, 0), (C + 2, 0, 2 * C), "smooth_stone")
    c.box((0, 0, C - 2), (2 * C, 0, C + 2), "smooth_stone")
    for y in range(1, HB):
        r = round(hw(y))
        floor = y % 3 == 0
        for x in range(C - r, C + r + 1):
            for z in range(C - r, C + r + 1):
                if not (x in (C - r, C + r) or z in (C - r, C + r)):
                    continue
                corner = x in (C - r, C + r) and z in (C - r, C + r)
                col = (x - C) % 4 == 0 or (z - C) % 4 == 0
                c.set(x, y, z, "quartz_block" if (floor or corner or col) else "gray_stained_glass")
    # два крыла (шахты лифтов) на восточной и западной стороне
    for s in (-1, 1):
        for y in range(34, 66):
            for x in range(C + s * round(hw(34)) , C + s * (round(hw(34)) + 3) + s, s):
                for z in range(C - 3, C + 4):
                    edge = z in (C - 3, C + 3) or x == C + s * (round(hw(34)) + 3)
                    if edge or y % 3 == 0:
                        c.set(x, y, z, "quartz_block" if y % 3 == 0 or z in (C - 3, C + 3) else "gray_stained_glass")
        c.box((C + s * round(hw(34)) - (0 if s > 0 else 3), 66, C - 3),
              (C + s * round(hw(34)) + (3 if s > 0 else 0), 66, C + 3), "iron_block")
    # венец и шпиль
    c.box((C - 3, HB, C - 3), (C + 3, HB, C + 3), "iron_block")
    c.cone((C, HB + 1, C), 3, 8, "quartz_block")
    c.line((C, HB + 9, C), (C, HB + 24, C), "iron_block", 1)
    c.set(C, HB + 25, C, "glowstone")
    # секвойи вокруг
    for tx, tz in ((4, 4), (36, 4), (4, 36), (36, 36), (4, 20), (36, 20), (20, 4), (20, 36), (10, 8), (30, 32)):
        c.cyl((tx, 1, tz), 0, 8, "spruce_log")
        c.cone((tx, 3, tz), 3, 11, "spruce_leaves")
    return c.v
