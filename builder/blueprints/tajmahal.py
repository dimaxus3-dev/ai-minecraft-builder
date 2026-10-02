"""Тадж-Махал: мавзолей с восьмиугольным основанием, большой купол и четыре малых,
арочные порталы, четыре минарета, терраса, бассейн с кипарисами."""

from __future__ import annotations

from .kit import Canvas

Q, SQ, PIL = "quartz_block", "smooth_quartz", "quartz_pillar"


def octagon(dx, dz, r, cut):
    return abs(dx) <= r and abs(dz) <= r and abs(dx) + abs(dz) <= r + cut


def build() -> dict:
    c = Canvas()
    W, D, cx, mz = 64, 100, 32, 80
    c.box((0, 0, 0), (W, 0, D), "moss_block")
    c.box((cx - 2, 0, 0), (cx + 2, 0, 58), "smooth_sandstone")
    c.box((cx - 5, 0, 12), (cx + 5, 0, 54), "light_blue_concrete")
    for x0, x1, z0, z1 in ((cx - 6, cx - 6, 11, 55), (cx + 6, cx + 6, 11, 55), (cx - 6, cx + 6, 11, 11), (cx - 6, cx + 6, 55, 55)):
        c.box((x0, 0, z0), (x1, 0, z1), "smooth_sandstone")
    for s in (-1, 1):                                                   # кипарисы вдоль бассейна
        for z in range(14, 55, 8):
            c.cyl((cx + s * 11, 1, z), 0, 2, "spruce_log")
            c.cone((cx + s * 11, 2, z), 1, 7, "spruce_leaves")
    # терраса и ступени
    c.box((6, 1, 58), (58, 4, 98), Q)
    c.box((cx - 8, 1, 56), (cx + 8, 1, 57), Q)
    c.box((cx - 8, 2, 57), (cx + 8, 2, 57), Q)
    # мавзолей: восьмиугольная оболочка
    for y in range(5, 26):
        for dx in range(-12, 13):
            for dz in range(-12, 13):
                if octagon(dx, dz, 12, 6) and not octagon(dx, dz, 10, 5):
                    c.set(cx + dx, y, mz + dz, SQ if y in (5, 14, 25) else Q)
    for dx in range(-11, 12):
        for dz in range(-11, 12):
            if octagon(dx, dz, 11, 5):
                c.set(cx + dx, 26, mz + dz, Q)
    # порталы-иваны с арочным углублением на четырёх сторонах
    for ax, sgn in ((0, 1), (0, -1), (1, 1), (1, -1)):
        for u in range(-3, 4):
            for y in range(7, 21):
                if y > 15 and abs(u) > 3.6 - (y - 15) * 0.75:
                    continue
                for depth in range(0, 3):
                    v = sgn * (12 - depth)
                    x, z = (cx + u, mz + v) if ax == 0 else (cx + v, mz + u)
                    c.set(x, y, z, "air")
                v = sgn * 9
                x, z = (cx + u, mz + v) if ax == 0 else (cx + v, mz + u)
                c.set(x, y, z, "gray_concrete")
    # барабан и главный купол, шпиль
    c.cyl((cx, 27, mz), 8, 4, Q, hollow=True)
    c.dome((cx, 31, mz), 8, SQ, h=13)
    c.line((cx, 44, mz), (cx, 52, mz), "gold_block", 1)
    c.sphere((cx, 49, mz), 1, "gold_block")
    # четыре малых купола-чхатри
    for sx, sz in ((-8, -8), (8, -8), (-8, 8), (8, 8)):
        c.cyl((cx + sx, 27, mz + sz), 1, 4, PIL)
        c.dome((cx + sx, 31, mz + sz), 2, SQ, h=3)
        c.line((cx + sx, 34, mz + sz), (cx + sx, 37, mz + sz), "gold_block", 1)
    # минареты
    for mx, zz in ((8, 62), (56, 62), (8, 94), (56, 94)):
        c.box((mx - 2, 5, zz - 2), (mx + 2, 7, zz + 2), Q)
        c.cyl((mx, 8, zz), 1, 30, PIL)
        for yb in (15, 23, 31):
            c.cyl((mx, yb, zz), 2, 1, SQ)
        c.cyl((mx, 38, zz), 2, 2, Q)
        c.dome((mx, 40, zz), 2, SQ, h=3)
        c.line((mx, 43, zz), (mx, 46, zz), "gold_block", 1)
    return c.v
