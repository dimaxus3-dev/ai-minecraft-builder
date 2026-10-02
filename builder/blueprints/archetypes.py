"""Типовые здания: замок, дом, небоскрёб, собор, пагода, мельница, маяк. Каждое — чертёж-генератор
с настоящими деталями (зубцы, порталы, окна, кровля), а не коробка из одного материала."""

from __future__ import annotations

import math

from .kit import Canvas


def castle() -> dict:
    c = Canvas(); S, O = 24, 34
    W, WL = "stone_bricks", "mossy_stone_bricks"
    for x in range(0, 2 * O + 1):
        for z in range(0, 2 * O + 1):
            d = max(abs(x - O), abs(z - O))
            c.set(x, 0, z, "blue_concrete" if S + 2 <= d <= S + 5 else ("cobblestone" if d <= S else "moss_block"))
    # стены с зубцами
    for (a, b) in (((O - S, O - S), (O + S, O - S + 2)), ((O - S, O + S - 2), (O + S, O + S)),
                   ((O - S, O - S), (O - S + 2, O + S)), ((O + S - 2, O - S), (O + S, O + S))):
        c.box((a[0], 1, a[1]), (b[0], 14, b[1]), W)
        for x in range(a[0], b[0] + 1):
            for z in range(a[1], b[1] + 1):
                if (x + z) % 2 == 0:
                    c.set(x, 15, z, W)
    c.hollow((O - S, 1, O - S), (O + S, 14, O + S), W, 1)            # ровная кладка по периметру
    c.carve((O - S + 3, 2, O - S + 3), (O + S - 3, 15, O + S - 3))
    for x in range(O - S + 3, O + S - 2):                              # дорожка стражи
        for z in (O - S + 2, O + S - 2):
            c.set(x, 14, z, "oak_planks")
    # угловые башни с конусными крышами
    for sx, sz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        tx, tz = O + sx * S, O + sz * S
        c.cyl((tx, 1, tz), 5, 22, W, hollow=True)
        c.cyl((tx, 23, tz), 6, 1, "cobblestone")
        c.cone((tx, 24, tz), 6, 11, "red_concrete")
        c.line((tx, 35, tz), (tx, 40, tz), "iron_block", 1)
        c.box((tx, 38, tz), (tx + 2 * sx, 40, tz), "red_wool")
        for y in (8, 14, 19):
            c.carve((tx + sx * 5, y, tz), (tx + sx * 5, y + 1, tz))
    # привратная башня с воротами и подъёмным мостом
    gz = O + S
    c.box((O - 7, 1, gz - 3), (O + 7, 20, gz + 2), W)
    c.carve((O - 2, 1, gz - 4), (O + 2, 8, gz + 3))
    c.box((O - 2, 1, gz + 2), (O + 2, 7, gz + 2), "dark_oak_planks")
    c.box((O - 8, 21, gz - 3), (O + 8, 21, gz + 2), "cobblestone")
    for x in range(O - 8, O + 9, 2):
        c.box((x, 22, gz - 3), (x, 22, gz - 3), W); c.box((x, 22, gz + 2), (x, 22, gz + 2), W)
    c.box((O - 2, 1, gz + 3), (O + 2, 1, gz + 9), "oak_planks")
    # донжон
    c.hollow((O - 8, 1, O - 8), (O + 8, 32, O + 8), W, 2)
    for x in range(O - 8, O + 9):
        for z in (O - 8, O + 8):
            if x % 2 == 0: c.set(x, 33, z, W)
    for z in range(O - 8, O + 9):
        for x in (O - 8, O + 8):
            if z % 2 == 0: c.set(x, 33, z, W)
    for y in (10, 18, 26):
        for s in (-1, 1):
            c.carve((O + s * 8, y, O - 1), (O + s * 8, y + 2, O + 1)); c.carve((O - 1, y, O + s * 8), (O + 1, y + 2, O + s * 8))
    c.line((O, 34, O), (O, 46, O), "iron_block", 1); c.box((O + 1, 42, O), (O + 6, 45, O), "red_wool")
    return c.v


def house() -> dict:
    c = Canvas(); W, D, H = 19, 15, 6
    c.box((0, 0, 0), (W + 8, 0, D + 10), "grass_block")
    c.box((W // 2 - 1, 0, D + 2), (W // 2 + 1, 0, D + 10), "gravel")
    c.box((3, 1, 3), (3 + W, 1, 3 + D), "cobblestone")
    c.hollow((3, 2, 3), (3 + W, 2 + H, 3 + D), "birch_planks", 1)
    for x in (3, 3 + W):                                              # каркас из тёмного дуба по углам и через 5
        for z in range(3, 4 + D, 1):
            if (z - 3) % 5 == 0 or z in (3, 3 + D): c.box((x, 2, z), (x, 2 + H, z), "dark_oak_log")
    for z in (3, 3 + D):
        for x in range(3, 4 + W):
            if (x - 3) % 5 == 0: c.box((x, 2, z), (x, 2 + H, z), "dark_oak_log")
    for x in range(5, 3 + W, 5):                                      # окна с ставнями
        for z, step in ((3, 1), (3 + D, 1)):
            c.box((x + 1, 4, z), (x + 3, 6, z), "glass")
    for z in range(5, 3 + D, 5):
        for x in (3, 3 + W):
            c.box((x, 4, z + 1), (x, 6, z + 3), "glass")
    c.carve((3 + W // 2 - 1, 2, 3 + D), (3 + W // 2 + 1, 4, 3 + D))
    c.box((3 + W // 2 - 1, 2, 3 + D), (3 + W // 2 + 1, 4, 3 + D), "air")
    c.box((3 + W // 2, 2, 3 + D), (3 + W // 2, 3, 3 + D), "dark_oak_planks")
    c.roof((1, 3 + H, 1), (5 + W, 3 + H, 5 + D), "dark_oak_planks", "gable", axis="x")
    c.box((3 + W - 3, 3 + H, 5), (3 + W - 2, 3 + H + 7, 6), "bricks")     # труба
    for x in range(1, 7 + W, 2):                                       # забор
        for z in (D + 9,):
            c.box((x, 1, z), (x, 2, z), "oak_planks")
    return c.v


def skyscraper() -> dict:
    c = Canvas(); C = 20
    c.box((0, 0, 0), (2 * C, 0, 2 * C), "gray_concrete")
    segs = [(0, 14, 17), (14, 40, 13), (40, 58, 10), (58, 68, 6)]    # (от, до, полуширина)
    for y0, y1, r in segs:
        for y in range(1 + y0, 1 + y1):
            floor = (y % 4 == 0) or y == 1 + y0
            for x in range(C - r, C + r + 1):
                for z in range(C - r, C + r + 1):
                    if not (x in (C - r, C + r) or z in (C - r, C + r)):
                        continue
                    corner = x in (C - r, C + r) and z in (C - r, C + r)
                    mull = (x - C) % 3 == 0 or (z - C) % 3 == 0
                    c.set(x, y, z, "white_concrete" if (floor or corner) else ("gray_concrete" if mull else "light_blue_stained_glass"))
        c.box((C - r, 1 + y1, C - r), (C + r, 1 + y1, C + r), "gray_concrete")
    c.carve((C - 2, 1, C - 17), (C + 2, 4, C - 17))
    c.box((C - 2, 1, C - 17), (C + 2, 4, C - 17), "glass")
    c.carve((C - 1, 1, C - 17), (C + 1, 3, C - 17))
    c.cyl((C, 69, C), 2, 6, "iron_block"); c.line((C, 75, C), (C, 90, C), "iron_block", 1)
    c.set(C, 91, C, "red_concrete")
    return c.v


def cathedral() -> dict:
    c = Canvas(); L, WID, WH = 56, 17, 16
    S, G, R, GL = "stone_bricks", "smooth_stone", "deepslate_tiles", ["blue_stained_glass", "light_blue_stained_glass", "purple_stained_glass"]
    cx = 20
    c.box((0, 0, 0), (2 * cx, 0, L + 14), "gray_concrete")
    x0, x1 = cx - WID // 2, cx + WID // 2
    c.hollow((x0, 1, 10), (x1, WH, 10 + L), S, 2)                      # неф
    c.roof((x0 - 1, WH + 1, 9), (x1 + 1, WH + 1, 11 + L), R, "gable", h=10, axis="z")
    # трансепт
    c.hollow((cx - 17, 1, 10 + 22), (cx + 17, WH, 10 + 34), S, 2)
    c.roof((cx - 18, WH + 1, 10 + 21), (cx + 18, WH + 1, 10 + 35), R, "gable", h=8, axis="x")
    # окна-стрельчатые с витражом по бокам нефа
    for i, z in enumerate(range(14, 10 + L - 4, 5)):
        for xw in (x0, x1):
            for dz in (0, 1, 2):
                for y in range(5, 5 + 8):
                    if y > 10 and dz == 0 or y > 10 and dz == 2 and y > 11:
                        continue
                    c.set(xw, y, z + dz, GL[(i + dz) % 3])
    # контрфорсы
    for z in range(13, 10 + L, 5):
        for xw, s in ((x0 - 1, -1), (x1 + 1, 1)):
            c.box((xw, 1, z), (xw, WH - 2, z), S)
            c.line((xw, WH - 2, z), (xw - s, WH + 4, z), S, 1)
    # фасад: розетка и портал
    for dx in range(-5, 6):
        for dy in range(-5, 6):
            d = math.hypot(dx, dy)
            if d <= 4.6:
                c.set(cx + dx, 20 + dy, 10, GL[int(d) % 3] if d > 1.2 else "yellow_stained_glass")
    c.carve((cx - 2, 1, 9), (cx + 2, 8, 12))
    c.box((cx - 2, 1, 10), (cx + 2, 8, 10), "dark_oak_planks"); c.carve((cx - 1, 1, 10), (cx + 1, 6, 10))
    # две башни со шпилями
    for tx in (x0 - 2, x1 + 2):
        c.hollow((tx - 4, 1, 4), (tx + 4, 36, 12), S, 2)
        for y in (24, 30):
            c.carve((tx - 1, y, 4), (tx + 1, y + 3, 4))
        c.box((tx - 4, 37, 4), (tx + 4, 37, 12), G)
        c.cone((tx, 38, 8), 5, 20, "deepslate_bricks")
        c.line((tx, 58, 8), (tx, 62, 8), "iron_block", 1)
    # центральная башенка-флеш
    c.cone((cx, WH + 11, 10 + 28), 3, 16, "deepslate_bricks")
    # апсида
    c.dome((cx, 1, 10 + L), 7, S, h=WH, hollow=True)
    return c.v


def pagoda() -> dict:
    c = Canvas(); C = 22
    c.box((0, 0, 0), (2 * C, 0, 2 * C), "smooth_stone")
    c.box((C - 14, 1, C - 14), (C + 14, 2, C + 14), "stone_bricks")
    y = 3
    for i in range(5):
        r = 10 - 2 * i
        c.hollow((C - r, y, C - r), (C + r, y + 5, C + r), "red_concrete", 1)
        c.carve((C - r + 1, y + 1, C - r + 1), (C + r - 1, y + 4, C + r - 1))
        for x in range(C - r, C + r + 1):
            for z in (C - r, C + r):
                if (x - C) % 3 == 0: c.box((x, y, z), (x, y + 5, z), "dark_oak_log")
        for z in range(C - r, C + r + 1):
            for x in (C - r, C + r):
                if (z - C) % 3 == 0: c.box((x, y, z), (x, y + 5, z), "dark_oak_log")
        for s in (-1, 1):
            c.carve((C + s * r, y + 2, C - 1), (C + s * r, y + 4, C + 1)); c.carve((C - 1, y + 2, C + s * r), (C + 1, y + 4, C + s * r))
        c.roof((C - r - 3, y + 6, C - r - 3), (C + r + 3, y + 6, C + r + 3), "dark_oak_planks", "pyramid", h=4)
        for sx, sz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):             # загнутые углы
            c.line((C + sx * (r + 3), y + 6, C + sz * (r + 3)), (C + sx * (r + 4), y + 8, C + sz * (r + 4)), "dark_oak_planks", 1)
        y += 7
    c.cone((C, y - 1, C), 3, 5, "dark_oak_planks")
    c.line((C, y + 4, C), (C, y + 12, C), "gold_block", 1)
    for k in (6, 8, 10):
        c.sphere((C, y + k, C), 1, "gold_block")
    return c.v


def windmill() -> dict:
    c = Canvas(); C = 24
    c.box((0, 0, 0), (2 * C, 0, 2 * C), "grass_block")
    for y in range(1, 26):
        r = round(7 - 2 * (y / 25))
        c.cyl((C, y, C), r, 1, "white_concrete" if (y // 5) % 2 else "stone_bricks", hollow=True)
    c.cone((C, 26, C), 5, 7, "dark_oak_planks")
    c.carve((C - 1, 1, C - 8), (C + 1, 4, C - 6)); c.box((C, 1, C - 7), (C, 3, C - 7), "dark_oak_planks")
    for y in (8, 14, 20):
        for dx, dz in ((6, 0), (-6, 0), (0, 6)):
            c.set(C + dx, y, C + dz, "glass")
    c.box((C - 1, 20, C - 8), (C + 1, 22, C - 6), "oak_planks")          # ступица
    for k in range(4):                                                  # лопасти
        a = math.radians(k * 90 + 25)
        tip = (C + 16 * math.cos(a), 21 + 16 * math.sin(a), C - 9)
        c.line((C, 21, C - 9), tip, "oak_planks", 1)
        px, py = -math.sin(a), math.cos(a)
        for t in range(4, 17):
            bx, by = C + t * math.cos(a), 21 + t * math.sin(a)
            for off in (1, 2, 3):
                c.set(bx + px * off, by + py * off, C - 9, "white_wool")
    return c.v


def lighthouse() -> dict:
    c = Canvas(); C = 16
    for x in range(0, 2 * C + 1):
        for z in range(0, 2 * C + 1):
            d = math.hypot(x - C, z - C)
            if d <= 13:
                h = max(0, round(4 - d / 4 + ((x * 7 + z * 3) % 3)))
                for y in range(0, h + 1):
                    c.set(x, y, z, "stone" if y < h else "andesite")
    base = 5
    for y in range(base, base + 30):
        r = round(6 - 2 * ((y - base) / 30))
        c.cyl((C, y, C), r, 1, "red_concrete" if ((y - base) // 4) % 2 == 0 else "white_concrete", hollow=True)
    top = base + 30
    c.cyl((C, top, C), 6, 1, "iron_block")
    c.cyl((C, top + 1, C), 6, 1, "iron_block", hollow=True)
    c.cyl((C, top + 1, C), 3, 4, "glass", hollow=True)
    c.sphere((C, top + 3, C), 1, "glowstone")
    c.cone((C, top + 5, C), 4, 6, "red_concrete")
    c.line((C, top + 11, C), (C, top + 14, C), "iron_block", 1)
    c.carve((C - 1, base, C - 6), (C + 1, base + 3, C - 4))
    c.box((C, base, C - 5), (C, base + 2, C - 5), "dark_oak_planks")
    for y in (base + 9, base + 17, base + 24):
        c.carve((C + 4, y, C - 1), (C + 4, y + 1, C + 1))
    return c.v
