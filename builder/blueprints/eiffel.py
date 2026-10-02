"""Эйфелева башня: четыре сужающихся ноги по кривой, три платформы, арки у основания,
ферма из балок и крестов между ногами, шпиль."""

from __future__ import annotations

from .kit import Canvas

C = 24                  # центр по x и z
HB = 80                 # высота «тела» башни без шпиля
W0 = 17                 # половина ширины по внешним краям ног у земли


def w(y: float) -> float:
    """Половина ширины башни на высоте y: быстро сужается вверху (как у настоящей)."""
    return W0 * max(0.0, 1 - y / (HB * 1.06)) ** 3.2 + 1.0


def lw(y: float) -> float:
    """Толщина ноги: широкая внизу, к верху сливается в одну колонну."""
    return max(1.2, 6.5 * (1 - y / (HB * 0.55)) + 1.2)


def build() -> dict:
    c = Canvas()
    metal, dark, light = "brown_concrete", "brown_terracotta", "smooth_stone"
    n = 16
    ys = [HB * i / n for i in range(n + 1)]
    corners = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    # площадка-основание
    c.box((C - 22, 0, C - 22), (C + 22, 0, C + 22), light)

    # ноги: внешняя и внутренняя линия, перемычки и кресты между ними
    for sx, sz in corners:
        O = [(C + sx * w(y), 1 + y, C + sz * w(y)) for y in ys]
        I = [(C + sx * max(0.6, w(y) - lw(y)), 1 + y, C + sz * max(0.6, w(y) - lw(y))) for y in ys]
        for i in range(n):
            t = 3 if ys[i] < 30 else 2 if ys[i] < 58 else 1
            c.line(O[i], O[i + 1], metal, t)
            c.line(I[i], I[i + 1], metal, t)
            c.line(O[i], I[i], dark, 1)
            c.line(O[i], I[i + 1], dark, 1)
            c.line(I[i], O[i + 1], dark, 1)

    # ферма между ногами на каждой стороне (балки и кресты)
    levels = [18, 24, 31, 38, 46, 54, 62]
    for a, b in zip(levels, levels[1:]):
        for fx, fz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            def pt(y, s):
                wy = w(y) - 0.5
                return (C + (fx * wy if fx else s * wy), 1 + y, C + (fz * wy if fz else s * wy))
            c.line(pt(a, -1), pt(a, 1), dark, 1)
            c.line(pt(a, -1), pt(b, 1), dark, 1)
            c.line(pt(a, 1), pt(b, -1), dark, 1)

    # арки у основания между ногами
    arch_w = W0 - lw(0) - 1
    for fx, fz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        zc = W0 - lw(0) / 2
        if fx == 0:
            a, b = (C - arch_w, 1, C + fz * zc), (C + arch_w, 1, C + fz * zc)
        else:
            a, b = (C + fx * zc, 1, C - arch_w), (C + fx * zc, 1, C + arch_w)
        c.arch(a, b, 13, metal, 2)

    # платформы: нижняя, средняя, верхняя
    for y, half, th in ((15, w(15) + 1.5, 2), (29, w(29) + 1.5, 2), (66, w(66) + 2, 2)):
        yy = 1 + y
        c.box((C - half, yy, C - half), (C + half, yy + th - 1, C + half), light)
        c.hollow((C - half, yy + th, C - half), (C + half, yy + th + 1, C + half), metal)
        c.carve((C - half + 1, yy + th, C - half + 1), (C + half - 1, yy + th + 1, C + half - 1))

    # верхний павильон и шпиль
    top = 1 + 66 + 3
    c.box((C - 1, top, C - 1), (C + 1, top + 4, C + 1), dark)
    c.set(C, top + 2, C, "glowstone")
    c.cone((C, top + 5, C), 2, 6, metal)
    c.line((C, top + 10, C), (C, top + 20, C), "iron_block", 1)
    c.set(C, top + 21, C, "glowstone")
    return c.v
