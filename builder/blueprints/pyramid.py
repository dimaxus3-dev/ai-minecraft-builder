"""Великая пирамида в Гизе: ступенчатые «слои» песчаника, золотая вершина, вход на севере
и три малые пирамиды царниц рядом."""

from __future__ import annotations

from .kit import Canvas


def _pyramid(c: Canvas, cx: int, cz: int, R: int, H: int, gold: bool) -> None:
    for y in range(H):
        r = round(R * (1 - y / H))
        b = "sandstone" if (y // 3) % 2 == 0 else "cut_sandstone"
        if gold and y >= H - 3:
            b = "gold_block"
        yy = 1 + y
        c.box((cx - r, yy, cz - r), (cx + r, yy, cz - r), b)
        c.box((cx - r, yy, cz + r), (cx + r, yy, cz + r), b)
        c.box((cx - r, yy, cz - r), (cx - r, yy, cz + r), b)
        c.box((cx + r, yy, cz - r), (cx + r, yy, cz + r), b)


def build() -> dict:
    c = Canvas()
    R, H = 32, 42
    cx = cz = R + 6
    c.box((0, 0, 0), (2 * cx + 36, 0, 2 * cz), "sand")
    _pyramid(c, cx, cz, R, H, True)
    c.carve((cx - 1, 1, cz - R - 1), (cx + 1, 3, cz - R + 3))          # вход
    c.box((cx - 1, 1, cz - R + 3), (cx + 1, 3, cz - R + 3), "black_concrete")
    for k in (-1, 0, 1):                                                # малые пирамиды
        _pyramid(c, 2 * cx + 18, cz + k * 24, 7, 10, False)
    return c.v
