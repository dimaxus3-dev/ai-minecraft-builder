"""Байтерек (Астана): белая сужающаяся колонна на четырёх опорах и золотой стеклянный шар на «ветвях»."""

from __future__ import annotations

import math

from .kit import Canvas

C, H = 24, 58


def w(y: float) -> float:
    return 8.5 - 5.0 * (y / H) ** 0.8


def build() -> dict:
    c = Canvas()
    for x in range(0, 2 * C + 1):
        for z in range(0, 2 * C + 1):
            d = math.hypot(x - C, z - C)
            c.set(x, 0, z, "smooth_quartz" if d <= 9 else ("light_gray_concrete" if d <= 20 else "moss_block"))
            if 9 < d <= 10 or 17 < d <= 18:
                c.set(x, 0, z, "yellow_concrete")
    c.cyl((C, 1, C), 10, 2, "white_concrete"); c.cyl((C, 3, C), 8, 1, "quartz_block")
    n = 14
    ys = [H * i / n for i in range(n + 1)]
    for k in range(4):                                    # четыре ноги, сходящиеся к стволу
        a = math.radians(45 + 90 * k)
        pts = [(C + w(y) * math.cos(a), 4 + y, C + w(y) * math.sin(a)) for y in ys]
        for i in range(n):
            c.line(pts[i], pts[i + 1], "white_concrete", 3 if ys[i] < 30 else 2)
    c.cyl((C, 4, C), 2, H + 2, "quartz_block")            # центральная шахта лифта
    for y in (18, 34, 48):                                # кольца-перекрытия и кресты между ногами
        r = w(y) + 1.5
        c.cyl((C, 4 + y, C), round(r), 1, "smooth_quartz", hollow=True)
    for y0, y1 in ((8, 24), (24, 40), (40, 54)):
        for k in range(4):
            a1, a2 = math.radians(45 + 90 * k), math.radians(45 + 90 * (k + 1))
            p = lambda y, a: (C + w(y) * math.cos(a), 4 + y, C + w(y) * math.sin(a))
            c.line(p(y0, a1), p(y1, a2), "light_gray_concrete", 1)
            c.line(p(y0, a2), p(y1, a1), "light_gray_concrete", 1)
    top = 4 + H
    c.cyl((C, top, C), 6, 1, "gold_block"); c.cyl((C, top + 1, C), 5, 1, "quartz_block")
    cy, R = top + 12, 9
    for k in range(8):                                    # ветви под шаром
        th = math.radians(k * 45)
        pts = [(C + 4 * math.cos(th), top + 1, C + 4 * math.sin(th)),
               (C + 6.5 * math.cos(th), top + 4, C + 6.5 * math.sin(th)),
               (C + 6.8 * math.cos(th), cy - 6.4, C + 6.8 * math.sin(th))]
        c.poly(pts, "white_concrete", 2)
    c.sphere((C, cy, C), R, "yellow_stained_glass", hollow=True)
    for k in range(8):                                    # золотые меридианы
        th = math.radians(k * 45)
        pts = [(C + R * math.sin(math.radians(p)) * math.cos(th), cy + R * math.cos(math.radians(p)),
                C + R * math.sin(math.radians(p)) * math.sin(th)) for p in range(0, 181, 12)]
        c.poly(pts, "gold_block", 1)
    for ang in range(0, 360, 6):                          # экватор
        a = math.radians(ang)
        c.set(C + R * math.cos(a), cy, C + R * math.sin(a), "gold_block")
    c.sphere((C, cy, C), 4, "light_blue_stained_glass", hollow=True)
    c.sphere((C, cy, C), 1, "sea_lantern")
    c.line((C, cy + R, C), (C, cy + R + 10, C), "gold_block", 1)
    c.sphere((C, cy + R + 10, C), 1, "gold_block")
    return c.v
