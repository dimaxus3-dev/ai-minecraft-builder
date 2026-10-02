"""Семейства классической архитектуры: колоннада, купол, ступенчатая пирамида.

Та же мысль, что и в towers.py: Парфенон, Капитолий и Чичен-Ица отличаются
пропорциями и набором деталей, а не принципом. Один генератор на семейство,
а каждое здание в реестре задаёт свои числа.
"""

from __future__ import annotations

import math

from .kit import Canvas


def temple(main: str = "quartz_block", accent: str = "smooth_stone", scale: float = 1.0,
           width: int = 34, depth: int = 20, columns: int = 8, col_h: int = 16,
           steps: int = 4, pediment: int = 1, roof_style: str = "gable",
           inner: int = 1, statue: int = 0, wings: int = 0) -> dict:
    """Храм с колоннадой: ступени по периметру, портик, фронтон, целла внутри."""
    c = Canvas()
    W = max(14, round(width * scale)) // 2
    D = max(10, round(depth * scale)) // 2
    H = max(8, round(col_h * scale))
    cx, cz = W + steps + 4, D + steps + 4

    for k in range(steps):                                           # стилобат
        c.box((cx - W - steps + k, k, cz - D - steps + k),
              (cx + W + steps - k, k, cz + D + steps - k), accent)
    base = steps

    gap = max(3, (2 * W) // max(1, columns - 1))
    for x in range(cx - W, cx + W + 1, gap):                         # колонны по периметру
        for z in (cz - D, cz + D):
            c.cyl((x, base, z), 1, H, main)
            c.cyl((x, base + H, z), 2, 1, main)
            c.cyl((x, base - 1, z), 2, 1, main)
    for z in range(cz - D, cz + D + 1, gap):
        for x in (cx - W, cx + W):
            c.cyl((x, base, z), 1, H, main)
            c.cyl((x, base + H, z), 2, 1, main)
            c.cyl((x, base - 1, z), 2, 1, main)

    arch = base + H + 1                                              # антаблемент
    c.box((cx - W - 2, arch, cz - D - 2), (cx + W + 2, arch + 1, cz + D + 2), main)
    c.box((cx - W - 2, arch + 2, cz - D - 2), (cx + W + 2, arch + 2, cz + D + 2), accent)

    if inner:                                                         # целла
        c.hollow((cx - W + 4, base, cz - D + 4), (cx + W - 4, arch - 1, cz + D - 4), main, 1)
        c.carve((cx - 3, base, cz - D + 4), (cx + 3, base + 7, cz - D + 4))
    if statue:                                                        # фигура внутри
        c.box((cx - 2, base, cz), (cx + 2, base + 2, cz + 2), accent)
        c.box((cx - 1, base + 3, cz), (cx + 1, base + 10, cz + 1), "gold_block")
        c.sphere((cx, base + 12, cz), 2, "gold_block")

    if roof_style == "gable" and pediment:                            # двускатная крыша с фронтоном
        c.roof((cx - W - 3, arch + 3, cz - D - 3), (cx + W + 3, arch + 3, cz + D + 3),
               accent, style="gable", axis="x")
        for z in (cz - D - 2, cz + D + 2):                            # тимпан
            for k in range(min(W, 10)):
                c.box((cx - W - 2 + k, arch + 3 + k, z), (cx + W + 2 - k, arch + 3 + k, z), main)
    elif roof_style == "flat":
        c.box((cx - W - 3, arch + 3, cz - D - 3), (cx + W + 3, arch + 3, cz + D + 3), accent)
    elif roof_style == "hip":
        c.roof((cx - W - 3, arch + 3, cz - D - 3), (cx + W + 3, arch + 3, cz + D + 3),
               accent, style="hip")

    if wings:                                                         # боковые крылья
        for side in (1, -1):
            wx = cx + side * (W + max(8, round(12 * scale)))
            c.hollow((wx - 6, base, cz - D + 2), (wx + 6, arch - 4, cz + D - 2), main, 1)
            c.box((wx - 7, arch - 3, cz - D + 1), (wx + 7, arch - 3, cz + D - 1), accent)
            for z in range(cz - D + 4, cz + D - 3, 4):
                c.box((wx + side * 6, base + 3, z), (wx + side * 6, base + 6, z), "glass")
    return c.v


def domed(main: str = "white_concrete", accent: str = "light_gray_concrete",
          scale: float = 1.0, body: int = 30, body_h: int = 18, drum: int = 12,
          drum_h: int = 12, dome_r: int = 12, lantern: int = 1, portico: int = 1,
          wings: int = 1, colonnade: int = 1, minarets: int = 0,
          dome_block: str = "") -> dict:
    """Купольное здание: корпус, барабан с колоннами, купол, портик, крылья."""
    c = Canvas()
    B = max(12, round(body * scale)) // 2
    H = max(8, round(body_h * scale))
    DR = max(5, round(drum * scale)) // 2
    DH = max(5, round(drum_h * scale))
    R = max(5, round(dome_r * scale))
    cx = cz = B + max(14, round(18 * scale))
    cap = dome_block or accent

    c.box((cx - B - 6, 0, cz - B - 6), (cx + B + 6, 0, cz + B + 6), "smooth_stone")
    c.hollow((cx - B, 1, cz - B), (cx + B, H, cz + B), main, 2)       # корпус
    c.box((cx - B - 1, H + 1, cz - B - 1), (cx + B + 1, H + 1, cz + B + 1), accent)
    for x in range(cx - B + 3, cx + B - 2, 4):                        # окна
        for y in (4, H - 5):
            c.box((x, y, cz - B), (x + 1, y + 3, cz - B), "glass")
            c.box((x, y, cz + B), (x + 1, y + 3, cz + B), "glass")

    drum_y = H + 2                                                    # барабан
    c.cyl((cx, drum_y, cz), DR, DH, main, hollow=True)
    if colonnade:
        for a in range(0, 360, 18):
            t = math.radians(a)
            c.cyl((cx + (DR + 1) * math.cos(t), drum_y, cz + (DR + 1) * math.sin(t)), 1, DH - 2, accent)
        c.cyl((cx, drum_y + DH - 2, cz), DR + 2, 1, accent)
    for a in range(0, 360, 36):
        t = math.radians(a)
        for y in range(drum_y + 3, drum_y + DH - 3):
            c.set(cx + DR * math.cos(t), y, cz + DR * math.sin(t), "glass")

    top = drum_y + DH
    c.dome((cx, top, cz), R, cap)                                     # купол
    c.dome((cx, top, cz), R - 2, "air")
    c.cyl((cx, top, cz), R, 1, cap)
    if lantern:                                                       # фонарик с крестом
        c.cyl((cx, top + R, cz), 3, 4, main, hollow=True)
        c.dome((cx, top + R + 4, cz), 3, cap)
        c.line((cx, top + R + 7, cz), (cx, top + R + 11, cz), "gold_block", 1)
        c.set(cx, top + R + 12, cz, "glowstone")

    if portico:                                                       # портик
        for x in range(cx - 8, cx + 9, 4):
            c.cyl((x, 1, cz - B - 4), 1, H - 4, main)
            c.cyl((x, H - 3, cz - B - 4), 2, 1, main)
        c.box((cx - 10, H - 2, cz - B - 6), (cx + 10, H - 1, cz - B), accent)
        for k in range(6):
            c.box((cx - 10 + k, H + k, cz - B - 6), (cx + 10 - k, H + k, cz - B - 6), main)
        for k in range(4):
            c.box((cx - 9 + k, k, cz - B - 7 + k), (cx + 9 - k, k, cz - B - 7 + k), accent)
    if wings:                                                         # крылья
        for side in (1, -1):
            wx = cx + side * (B + max(10, round(14 * scale)))
            c.hollow((wx - 8, 1, cz - B + 3), (wx + 8, H - 4, cz + B - 3), main, 1)
            c.box((wx - 9, H - 3, cz - B + 2), (wx + 9, H - 3, cz + B - 2), accent)
            for z in range(cz - B + 5, cz + B - 4, 4):
                c.box((wx + side * 8, 4, z), (wx + side * 8, 7, z), "glass")
    if minarets:
        for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            mx, mz = cx + sx * (B + 3), cz + sz * (B + 3)
            mh = max(24, round(36 * scale))
            c.cyl((mx, 1, mz), 2, mh, main, hollow=True)
            c.cyl((mx, round(mh * 0.7), mz), 3, 1, accent)
            c.cone((mx, mh + 1, mz), 2, 5, accent)
    return c.v


def step_pyramid(main: str = "smooth_sandstone", accent: str = "chiseled_sandstone",
                 scale: float = 1.0, base: int = 48, tiers: int = 9, tier_h: int = 4,
                 stairs: int = 1, temple_top: int = 1, round_corners: int = 0,
                 spiral: int = 0) -> dict:
    """Ступенчатая пирамида: Чичен-Ица, зиккурат, храм-гора."""
    c = Canvas()
    B = max(16, round(base * scale)) // 2
    TH = max(2, round(tier_h * scale))
    cx = cz = B + 6

    c.box((cx - B - 5, 0, cz - B - 5), (cx + B + 5, 0, cz + B + 5), "grass_block")
    for k in range(tiers):
        r = B * (1 - k / tiers)
        y0 = 1 + k * TH
        for y in range(y0, y0 + TH):
            if round_corners:
                for dx in range(-round(r), round(r) + 1):
                    for dz in range(-round(r), round(r) + 1):
                        if math.hypot(dx, dz) <= r:
                            c.set(cx + dx, y, cz + dz, main if y != y0 + TH - 1 else accent)
            else:
                c.box((cx - round(r), y, cz - round(r)), (cx + round(r), y, cz + round(r)),
                      main if y != y0 + TH - 1 else accent)
        if spiral:                                                     # пандус по кругу
            a = math.radians(k * 360 / tiers)
            c.box((cx + round(r * math.cos(a)) - 1, y0, cz + round(r * math.sin(a)) - 1),
                  (cx + round(r * math.cos(a)) + 1, y0 + TH, cz + round(r * math.sin(a)) + 1), accent)

    top_y = 1 + tiers * TH
    if stairs:                                                         # лестницы по граням
        sides = ((0, -1), (0, 1), (-1, 0), (1, 0))[:stairs if stairs <= 4 else 4]
        for sx, sz in sides:
            for k in range(tiers * TH):
                r = B * (1 - (k // TH) / tiers) + 1
                px, pz = cx + sx * round(r), cz + sz * round(r)
                c.box((px - 2 * abs(sz), 1 + k, pz - 2 * abs(sx)),
                      (px + 2 * abs(sz), 1 + k, pz + 2 * abs(sx)), accent)
    if temple_top:                                                     # святилище наверху
        t = max(3, round(B * 0.22))
        c.hollow((cx - t, top_y, cz - t), (cx + t, top_y + max(6, round(9 * scale)), cz + t), main, 1)
        c.carve((cx - 1, top_y, cz - t), (cx + 1, top_y + 4, cz - t))
        c.box((cx - t - 1, top_y + max(6, round(9 * scale)) + 1, cz - t - 1),
              (cx + t + 1, top_y + max(6, round(9 * scale)) + 1, cz + t + 1), accent)
        c.set(cx, top_y + max(6, round(9 * scale)) + 2, cz, "glowstone")
    return c.v
