"""Дворец мира и согласия (Астана): стеклянная пирамида на ступенчатом основании с «солнцем» наверху."""

from __future__ import annotations

import math

from .kit import Canvas

C, R, H = 30, 24, 32


def build() -> dict:
    c = Canvas()
    c.box((0, 0, 0), (2 * C, 0, 2 * C), "smooth_quartz")
    for i in range(3):
        c.box((C - 28 + 3 * i, 1 + i, C - 28 + 3 * i), (C + 28 - 3 * i, 1 + i, C + 28 - 3 * i), "quartz_block" if i % 2 == 0 else "smooth_quartz")
    for y in range(H):
        r = round(R * (1 - y / H)) + 1
        yy = 4 + y
        floor = y % 4 == 0
        for x in range(C - r, C + r + 1):
            for z in range(C - r, C + r + 1):
                if not (x in (C - r, C + r) or z in (C - r, C + r)):
                    continue
                rib = (x - C) % 6 == 0 or (z - C) % 6 == 0
                c.set(x, yy, z, "gray_concrete" if (floor or rib) else ("light_blue_stained_glass" if (x + z + y) % 7 else "cyan_stained_glass"))
    top = 4 + H
    c.box((C - 1, top, C - 1), (C + 1, top + 1, C + 1), "gold_block")
    c.cyl((C, top + 2, C), 2, 1, "gold_block"); c.line((C, top + 3, C), (C, top + 9, C), "gold_block", 1)
    return c.v
