"""Монумент «Батьківщина-мати» (Киев): стилизованная фигура с поднятым мечом и щитом на круглом
постаменте-музее."""

from __future__ import annotations

import math

from .kit import Canvas

C = 26
S, L, STEEL, DARK = "smooth_stone", "light_gray_concrete", "iron_block", "gray_concrete"


def build() -> dict:
    c = Canvas()
    for x in range(0, 2 * C + 1):
        for z in range(0, 2 * C + 1):
            d = math.hypot(x - C, z - C)
            c.set(x, 0, z, "smooth_quartz" if d <= 22 else "moss_block")
    c.cyl((C, 1, C), 19, 3, DARK); c.cyl((C, 4, C), 16, 5, S); c.cyl((C, 9, C), 13, 12, L, hollow=False)
    for ang in range(0, 360, 30):                                    # ниши по окружности
        a = math.radians(ang)
        c.box((C + 13 * math.cos(a) - 1, 11, C + 13 * math.sin(a) - 1), (C + 13 * math.cos(a) + 1, 17, C + 13 * math.sin(a) + 1), DARK)
    c.cyl((C, 21, C), 12, 1, S)
    y0 = 22
    c.cone((C, y0, C), 7, 20, L)                                     # складки одежды
    c.cyl((C, y0 + 8, C), 3, 14, L)                                  # торс
    c.box((C - 5, y0 + 20, C - 1), (C + 5, y0 + 21, C + 1), L)       # плечи
    c.cyl((C, y0 + 22, C), 1, 2, L)                                  # шея
    c.sphere((C, y0 + 25, C), 3, L)                                  # голова
    for k in (-2, 2):                                                # складки спереди
        c.line((C + k, y0 + 18, C - 3), (C + k * 2, y0, C - 5), S, 1)
    # правая рука с мечом (слева на экране от зрителя спереди)
    c.poly([(C + 5, y0 + 20, C), (C + 9, y0 + 27, C), (C + 10, y0 + 33, C)], L, 2)
    c.box((C + 8, y0 + 33, C - 1), (C + 12, y0 + 34, C + 1), STEEL)  # гарда
    c.line((C + 10, y0 + 34, C), (C + 10, y0 + 56, C), STEEL, 2)     # клинок
    c.line((C + 10, y0 + 56, C), (C + 10, y0 + 60, C), STEEL, 1)
    # левая рука со щитом
    c.poly([(C - 5, y0 + 20, C), (C - 9, y0 + 16, C - 1), (C - 10, y0 + 13, C - 2)], L, 2)
    for dx in range(-7, 8):
        for dy in range(-9, 10):
            d = math.hypot(dx / 7, dy / 9)
            if d <= 1:
                c.set(C - 12 + dx, y0 + 14 + dy, C - 3, DARK if d > 0.8 else (S if d > 0.35 else "blue_concrete"))
    for dy in range(-4, 5):
        c.set(C - 12, y0 + 14 + dy, C - 4, "yellow_concrete")        # трезубец на щите
    for dx in (-2, 2):
        for dy in range(2, 5):
            c.set(C - 12 + dx, y0 + 14 + dy, C - 4, "yellow_concrete")
    c.line((C - 14, y0 + 11, C - 4), (C - 10, y0 + 11, C - 4), "yellow_concrete", 1)
    return c.v
