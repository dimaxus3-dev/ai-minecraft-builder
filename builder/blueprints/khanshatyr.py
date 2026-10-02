"""Хан Шатыр (Астана): гигантский прозрачный шатёр с вогнутым профилем, рёбрами и наклонной мачтой."""

from __future__ import annotations

import math

from .kit import Canvas

C, H, R = 36, 56, 30


def build() -> dict:
    c = Canvas()
    for x in range(0, 2 * C + 1):
        for z in range(0, 2 * C + 1):
            d = math.hypot(x - C, z - C)
            c.set(x, 0, z, "smooth_quartz" if d <= R + 4 else "moss_block")
    base_h = 5
    for y in range(1, base_h + 1):                                    # кольцевая стена основания
        for ang in range(0, 360, 2):
            a = math.radians(ang)
            c.set(C + R * math.cos(a), y, C + R * 0.93 * math.sin(a), "white_concrete")
    for ang in (0, 90, 180, 270):                                     # четыре входа
        a = math.radians(ang)
        cx, cz = C + R * math.cos(a), C + R * 0.93 * math.sin(a)
        c.box((cx - 2, 1, cz - 2), (cx + 2, 3, cz + 2), "air")
    for y in range(base_h, H):                                        # оболочка шатра
        t = (y - base_h) / (H - base_h)
        r = R * (1 - t) ** 1.7 + 0.6
        ox = 7 * t ** 2.2                                             # наклон верхушки
        steps = max(24, int(2 * math.pi * r * 1.6))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            rib = abs(((a / (2 * math.pi)) * 20) % 1 - 0.5) < 0.1
            c.set(C + ox + r * math.cos(a), y, C + 0.93 * r * math.sin(a),
                  "white_concrete" if rib else "white_stained_glass")
    tipx = C + 7
    c.line((C, 1, C), (tipx, H + 10, C), "iron_block", 2)             # центральная мачта
    c.line((tipx, H + 10, C), (tipx, H + 22, C), "iron_block", 1)
    c.set(tipx, H + 23, C, "glowstone")
    for ang in range(0, 360, 24):                                     # растяжки от мачты к кольцу
        a = math.radians(ang)
        c.line((tipx, H + 6, C), (C + (R + 2) * math.cos(a), 2, C + 0.93 * (R + 2) * math.sin(a)), "light_gray_concrete", 1)
    return c.v
