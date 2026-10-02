"""Малые формы: то, что просят между делом и что должно появляться мгновенно.

Каждая вещь небольшая, поэтому генераторы короткие. Все принимают цвет,
материал и размер из запроса — см. params.py.
"""

from __future__ import annotations

import math

from .kit import Canvas


def well(main: str = "cobblestone", accent: str = "oak_planks", scale: float = 1.0) -> dict:
    """Колодец: круглая кладка, стойки, двускатный навес, ведро на верёвке."""
    c = Canvas()
    R = max(3, round(4 * scale))
    cx = R + 4
    for x in range(2 * cx + 1):
        for z in range(2 * cx + 1):
            if math.hypot(x - cx, z - cx) <= R + 2:
                c.set(x, 0, z, "grass_block")
    c.cyl((cx, 1, cx), R, 3, main, hollow=True)
    c.cyl((cx, 1, cx), R - 1, 1, "water")
    c.cyl((cx, 4, cx), R, 1, accent, hollow=True)
    for side in (1, -1):
        c.line((cx + side * (R - 1), 4, cx), (cx + side * (R - 1), 4 + max(5, round(7 * scale)), cx), accent, 1)
    top = 4 + max(5, round(7 * scale))
    c.roof((cx - R - 1, top, cx - R - 1), (cx + R + 1, top, cx + R + 1), accent, style="gable")
    c.line((cx - R + 1, top - 1, cx), (cx + R - 1, top - 1, cx), "oak_log", 1)
    c.line((cx, top - 2, cx), (cx, 5, cx), "chain", 1)
    c.box((cx - 1, 4, cx - 1), (cx + 1, 4, cx + 1), "spruce_planks")
    return c.v


def tent(main: str = "red_wool", accent: str = "white_wool", scale: float = 1.0) -> dict:
    """Шатёр: полосатый конус на опорах, вход, флажок, костёр рядом."""
    c = Canvas()
    R = max(7, round(11 * scale))
    cx = R + 5
    for x in range(2 * cx + 1):
        for z in range(2 * cx + 1):
            if math.hypot(x - cx, z - cx) <= R + 4:
                c.set(x, 0, z, "grass_block")
    H = max(12, round(18 * scale))
    for y in range(1, H):
        r = R * (1 - (y - 1) / H)
        for a in range(0, 360, 3):
            t = math.radians(a)
            colour = main if (round(a / 18) % 2 == 0) else accent
            c.set(cx + r * math.cos(t), y, cx + r * math.sin(t), colour)
    c.line((cx, H - 1, cx), (cx, H + 3, cx), "oak_log", 1)
    c.box((cx, H + 2, cx + 1), (cx, H + 3, cx + 3), "yellow_wool")
    c.carve((cx - 2, 1, cx - R - 1), (cx + 2, 6, cx - R + 2))
    for k in range(6):                                    # растяжки
        a = math.radians(k * 60)
        c.line((cx + (R - 1) * math.cos(a), 3, cx + (R - 1) * math.sin(a)),
               (cx + (R + 3) * math.cos(a), 0, cx + (R + 3) * math.sin(a)), "chain", 1)
    c.set(cx + R + 5, 1, cx, "campfire")
    return c.v


def barn(main: str = "red_concrete", accent: str = "white_concrete", scale: float = 1.0) -> dict:
    """Амбар с силосной башней: ломаная крыша, большие ворота, забор, грядки."""
    c = Canvas()
    W = max(8, round(12 * scale))
    D = max(11, round(16 * scale))
    H = max(8, round(11 * scale))
    cx, cz = W + 10, D + 8
    c.box((cx - W - 9, 0, cz - D - 7), (cx + W + 9, 0, cz + D + 7), "grass_block")
    c.hollow((cx - W, 1, cz - D), (cx + W, H, cz + D), main, 1)
    for k in range(W):                                    # ломаная крыша
        y = H + 1 + k
        r = W - k
        if k < W // 2:
            r = W - k // 2
        c.box((cx - r, y, cz - D - 1), (cx + r, y, cz + D + 1), accent if k % 3 else main)
        if r <= 1:
            break
    c.carve((cx - 3, 1, cz - D), (cx + 3, 7, cz - D))      # ворота
    c.box((cx - 3, 1, cz - D), (cx + 3, 7, cz - D), "dark_oak_planks")
    c.box((cx - 3, 8, cz - D), (cx + 3, 8, cz - D), accent)
    for side in (1, -1):                                  # окна
        for z in range(cz - D + 4, cz + D - 3, 5):
            c.box((cx + side * W, 4, z), (cx + side * W, 6, z), "glass")
    sx = cx + W + 6                                       # силос
    c.cyl((sx, 1, cz), max(3, round(4 * scale)), max(14, round(20 * scale)), accent, hollow=True)
    c.dome((sx, 1 + max(14, round(20 * scale)), cz), max(3, round(4 * scale)), "light_gray_concrete")
    for x in range(cx - W - 8, cx + W + 9, 3):            # забор и грядки
        c.box((x, 1, cz + D + 6), (x, 2, cz + D + 6), "oak_planks")
    for z in range(cz - D, cz + D, 3):
        c.box((cx - W - 8, 1, z), (cx - W - 5, 1, z), "farmland")
    return c.v


def water_tower(main: str = "light_gray_concrete", accent: str = "red_concrete",
                scale: float = 1.0) -> dict:
    """Водонапорная башня: бак на четырёх опорах, лестница, конус крыши."""
    c = Canvas()
    R = max(5, round(8 * scale))
    H = max(14, round(22 * scale))
    cx = R + 5
    c.box((cx - R - 4, 0, cx - R - 4), (cx + R + 4, 0, cx + R + 4), "grass_block")
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):   # опоры
        px, pz = cx + sx * (R - 2), cx + sz * (R - 2)
        c.line((px, 1, pz), (cx + sx * 2, H, cx + sz * 2), "iron_block", 1)
        for y in range(4, H, 5):                          # раскосы
            c.line((px, y, pz), (cx - sx * (R - 2), y, cx + sz * (R - 2)), "iron_bars", 1)
    c.cyl((cx, H, cx), R, max(7, round(10 * scale)), main, hollow=True)
    c.cyl((cx, H, cx), R, 1, main)
    band = H + max(7, round(10 * scale)) // 2
    c.cyl((cx, band, cx), R + 1, 1, accent)
    c.cone((cx, H + max(7, round(10 * scale)), cx), R, max(4, round(6 * scale)), accent)
    for y in range(1, H):                                 # лестница
        c.set(cx + R, y, cx, "ladder" if y % 1 else "iron_bars")
        c.set(cx + R, y, cx, "iron_bars")
    return c.v


def crane(main: str = "yellow_concrete", accent: str = "gray_concrete", scale: float = 1.0) -> dict:
    """Башенный кран: решётчатая мачта, стрела с противовесом, крюк на тросе."""
    c = Canvas()
    H = max(28, round(44 * scale))
    arm = max(20, round(30 * scale))
    back = max(8, round(11 * scale))
    cx = arm // 2 + 8
    cz = back + 8
    c.box((cx - 5, 0, cz - 5), (cx + 5, 1, cz + 5), "smooth_stone")
    for y in range(2, H):                                 # мачта
        for dx, dz in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            c.set(cx + dx, y, cz + dz, main)
        if y % 4 == 0:
            c.line((cx - 2, y, cz - 2), (cx + 2, y, cz + 2), accent, 1)
            c.line((cx + 2, y, cz - 2), (cx - 2, y, cz + 2), accent, 1)
    c.box((cx - 3, H, cz - 3), (cx + 3, H + 3, cz + 3), accent)        # кабина
    c.box((cx - 2, H + 1, cz - 3), (cx + 2, H + 2, cz - 3), "glass")
    y = H + 4
    c.box((cx - back, y, cz), (cx + arm, y, cz), main)                 # стрела
    for z in (-1, 1):
        c.box((cx - back, y + 2, cz + z), (cx + arm, y + 2, cz + z), main)
    for x in range(cx - back, cx + arm, 3):                            # фермы
        c.line((x, y, cz), (x + 2, y + 2, cz + 1), accent, 1)
    c.box((cx - back - 2, y - 2, cz - 2), (cx - back, y + 1, cz + 2), accent)   # противовес
    hook = cx + round(arm * 0.7)
    c.line((hook, y, cz), (hook, 6, cz), "chain", 1)
    c.box((hook - 1, 4, cz - 1), (hook + 1, 5, cz + 1), accent)
    c.line((cx, y + 8, cz), (cx + arm, y + 2, cz), "chain", 1)
    c.line((cx, y + 8, cz), (cx - back, y + 2, cz), "chain", 1)
    c.box((cx - 1, y + 3, cz - 1), (cx + 1, y + 8, cz + 1), main)
    return c.v


def radio_tower(main: str = "red_concrete", accent: str = "white_concrete",
                scale: float = 1.0) -> dict:
    """Радиомачта: решётчатая ферма, красно-белые пояса, растяжки, маяк."""
    c = Canvas()
    H = max(40, round(64 * scale))
    B = max(5, round(7 * scale))
    cx = B + 12
    c.box((cx - B - 11, 0, cx - B - 11), (cx + B + 11, 0, cx + B + 11), "grass_block")
    c.box((cx - B, 0, cx - B), (cx + B, 1, cx + B), "smooth_stone")
    for y in range(2, H):
        t = y / H
        r = max(1.2, B * (1 - 0.7 * t))
        colour = main if (y // max(4, round(7 * scale))) % 2 == 0 else accent
        for a in (45, 135, 225, 315):
            px, pz = cx + r * math.cos(math.radians(a)), cx + r * math.sin(math.radians(a))
            c.set(px, y, pz, colour)
        if y % 3 == 0:
            pts = [(cx + r * math.cos(math.radians(a)), y, cx + r * math.sin(math.radians(a)))
                   for a in (45, 135, 225, 315)]
            c.poly(pts + [pts[0]], colour, 1)
    for k, a in enumerate((45, 165, 285)):                 # растяжки
        t = math.radians(a)
        c.line((cx + 1.5 * math.cos(t), round(H * 0.78), cx + 1.5 * math.sin(t)),
               (cx + (B + 10) * math.cos(t), 1, cx + (B + 10) * math.sin(t)), "chain", 1)
    c.line((cx, H, cx), (cx, H + max(5, round(8 * scale)), cx), accent, 1)
    c.set(cx, H + max(5, round(8 * scale)) + 1, cx, "redstone_lamp")
    for y in (round(H * 0.45), round(H * 0.72)):           # тарелки
        c.dome((cx + 3, y, cx), 3, accent)
    return c.v


def gazebo(main: str = "oak_planks", accent: str = "dark_oak_planks", scale: float = 1.0) -> dict:
    """Беседка: восьмигранник, колонны, резной купол, скамьи, дорожка."""
    c = Canvas()
    R = max(6, round(9 * scale))
    cx = R + 5
    for x in range(2 * cx + 1):
        for z in range(2 * cx + 1):
            if math.hypot(x - cx, z - cx) <= R + 4:
                c.set(x, 0, z, "grass_block")
    c.cyl((cx, 1, cx), R, 1, "smooth_stone")
    c.cyl((cx, 2, cx), R - 1, 1, main)
    H = max(6, round(9 * scale))
    for k in range(8):
        a = math.radians(k * 45)
        px, pz = cx + (R - 1) * math.cos(a), cx + (R - 1) * math.sin(a)
        c.line((px, 3, pz), (px, 3 + H, pz), accent, 1)
        c.set(px, 3 + H - 1, pz, main)
        nx, nz = cx + (R - 1) * math.cos(math.radians(k * 45 + 45)), cx + (R - 1) * math.sin(math.radians(k * 45 + 45))
        c.line((px, 3 + H, pz), (nx, 3 + H, nz), accent, 1)
        c.line((px, 4, pz), (nx, 4, nz), main, 1)          # скамьи
    c.cone((cx, 4 + H, cx), R, max(5, round(7 * scale)), accent)
    c.line((cx, 4 + H + max(5, round(7 * scale)), cx), (cx, 6 + H + max(5, round(7 * scale)), cx), "iron_bars", 1)
    c.set(cx, 7 + H + max(5, round(7 * scale)), cx, "lantern")
    c.box((cx - 1, 1, cx + R), (cx + 1, 1, cx + R + 4), "gravel")
    return c.v


def greenhouse(main: str = "glass", accent: str = "white_concrete", scale: float = 1.0) -> dict:
    """Теплица: стеклянные стены, двускатная крыша, грядки, бочка с водой."""
    c = Canvas()
    W = max(6, round(9 * scale))
    D = max(9, round(14 * scale))
    H = max(6, round(8 * scale))
    cx, cz = W + 5, D + 5
    c.box((cx - W - 4, 0, cz - D - 4), (cx + W + 4, 0, cz + D + 4), "grass_block")
    c.box((cx - W, 1, cz - D), (cx + W, 1, cz + D), accent)
    c.hollow((cx - W, 2, cz - D), (cx + W, H, cz + D), main, 1)
    for x in range(cx - W, cx + W + 1, 4):                 # переплёты
        c.box((x, 2, cz - D), (x, H, cz - D), accent)
        c.box((x, 2, cz + D), (x, H, cz + D), accent)
    c.roof((cx - W, H + 1, cz - D), (cx + W, H + 1, cz + D), main, style="gable", axis="x")
    for k in range(W + 1):
        c.set(cx - W + k, H + 1 + k, cz - D, accent)
        c.set(cx + W - k, H + 1 + k, cz - D, accent)
        c.set(cx - W + k, H + 1 + k, cz + D, accent)
        c.set(cx + W - k, H + 1 + k, cz + D, accent)
    c.carve((cx - 1, 2, cz - D), (cx + 1, 5, cz - D))
    for z in range(cz - D + 2, cz + D - 1, 3):             # грядки
        for x in (cx - W + 2, cx + W - 2):
            c.set(x, 2, z, "farmland")
            c.set(x, 3, z, "wheat")
    c.cyl((cx + W - 2, 2, cz + D - 2), 1, 3, "spruce_planks")
    c.set(cx + W - 2, 5, cz + D - 2, "water")
    return c.v


def snowman(main: str = "snow_block", accent: str = "black_concrete", scale: float = 1.0) -> dict:
    """Снеговик: три кома, ведро, руки-ветки, шарф, сугробы."""
    c = Canvas()
    R = max(5, round(7 * scale))
    cx = R + 6
    for x in range(2 * cx + 1):
        for z in range(2 * cx + 1):
            if math.hypot(x - cx, z - cx) <= cx - 1:
                c.set(x, 0, z, "snow_block")
    r1, r2, r3 = R, round(R * 0.72), round(R * 0.5)
    y1 = 1 + r1
    c.sphere((cx, y1, cx), r1, main)
    y2 = y1 + r1 + r2 - 1
    c.sphere((cx, y2, cx), r2, main)
    y3 = y2 + r2 + r3 - 1
    c.sphere((cx, y3, cx), r3, main)
    for dz in (-1, 0, 1):                                  # глаза и рот
        c.set(cx + dz, y3 + 1, cx - r3, accent)
    c.set(cx, y3, cx - r3, "orange_concrete")
    c.set(cx, y3 - 1, cx - r3, "orange_concrete")
    c.cyl((cx, y3 + r3, cx), r3 - 1, 1, accent)            # ведро
    c.cyl((cx, y3 + r3 + 1, cx), max(2, r3 - 2), 3, accent, hollow=True)
    for side in (1, -1):                                   # руки
        c.line((cx + side * r2, y2, cx), (cx + side * (r2 + 4), y2 + 3, cx), "stick" if False else "oak_log", 1)
        c.line((cx + side * (r2 + 3), y2 + 2, cx), (cx + side * (r2 + 5), y2 + 4, cx - 1), "oak_log", 1)
    for a in range(0, 360, 20):                            # шарф
        t = math.radians(a)
        c.set(cx + (r3 + 0.6) * math.cos(t), y3 - r3, cx + (r3 + 0.6) * math.sin(t), "red_wool")
    c.box((cx + r3, y3 - r3 - 3, cx), (cx + r3, y3 - r3 - 1, cx), "red_wool")
    return c.v


def hot_air_balloon(main: str = "red_wool", accent: str = "yellow_wool",
                    scale: float = 1.0) -> dict:
    """Воздушный шар: полосатый купол, стропы, корзина, мешки балласта."""
    c = Canvas()
    R = max(8, round(13 * scale))
    cx = R + 4
    basket_h = max(4, round(5 * scale))
    ground = 1
    c.box((0, 0, 0), (2 * cx, 0, 2 * cx), "grass_block")
    bx = cx
    c.hollow((bx - 3, ground, cx - 3), (bx + 3, ground + basket_h, cx + 3), "oak_planks", 1)
    c.box((bx - 3, ground + basket_h, cx - 3), (bx + 3, ground + basket_h, cx + 3), "oak_log")
    base = ground + basket_h + max(5, round(7 * scale))
    for y in range(base, base + 2 * R):                    # купол
        dy = (y - base) / (2 * R)
        r = R * math.sin(math.pi * max(0.06, min(0.97, dy + 0.03)))
        for a in range(0, 360, 3):
            t = math.radians(a)
            colour = main if (round(a / 22.5) % 2 == 0) else accent
            c.set(cx + r * math.cos(t), y, cx + r * math.sin(t), colour)
    for k in range(6):                                     # стропы
        a = math.radians(k * 60)
        c.line((cx + (R * 0.45) * math.cos(a), base + 1, cx + (R * 0.45) * math.sin(a)),
               (bx + 3 * math.cos(a), ground + basket_h, cx + 3 * math.sin(a)), "chain", 1)
    c.set(cx, base + 2 * R, cx, accent)
    for k, (dx, dz) in enumerate(((5, 5), (-5, 5), (5, -5))):
        c.set(bx + dx, ground, cx + dz, "sand")
    return c.v


def treehouse(main: str = "oak_log", accent: str = "oak_planks", scale: float = 1.0) -> dict:
    """Домик на дереве: толстый ствол, крона, площадка, хижина, лестница."""
    c = Canvas()
    H = max(16, round(24 * scale))
    cx = max(14, round(18 * scale))
    for x in range(2 * cx + 1):
        for z in range(2 * cx + 1):
            if math.hypot(x - cx, z - cx) <= cx - 2:
                c.set(x, 0, z, "grass_block")
    for y in range(1, H + 10):                             # ствол
        r = max(1.4, 3.4 - 2.0 * y / (H + 10))
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                if dx * dx + dz * dz <= r * r:
                    c.set(cx + dx, y, cz_ := cx + dz, main)
    plat = H
    c.box((cx - 8, plat, cx - 8), (cx + 8, plat, cx + 8), accent)       # площадка
    for side in (1, -1):
        c.line((cx + side * 7, plat + 1, cx - 7), (cx + side * 7, plat + 2, cx - 7), accent, 1)
    for x in range(cx - 8, cx + 9, 2):                                  # перила
        c.set(x, plat + 1, cx - 8, "oak_fence" if False else accent)
        c.set(x, plat + 1, cx + 8, accent)
    c.hollow((cx - 6, plat + 1, cx - 6), (cx + 2, plat + 7, cx + 4), accent, 1)   # хижина
    c.roof((cx - 7, plat + 8, cx - 7), (cx + 3, plat + 8, cx + 5), main, style="gable")
    c.carve((cx - 2, plat + 1, cx - 6), (cx, plat + 4, cx - 6))
    c.box((cx - 5, plat + 3, cx - 6), (cx - 4, plat + 5, cx - 6), "glass")
    for y in range(1, plat):                                            # лестница
        c.set(cx + 4, y, cx, main)
        if y % 2 == 0:
            c.set(cx + 5, y, cx, accent)
    for k in range(7):                                                  # крона
        a = math.radians(k * 51)
        c.sphere((cx + math.cos(a) * 9, plat + 12 + (k % 3) * 3, cx + math.sin(a) * 9),
                 max(4, round(6 * scale)), "oak_leaves")
    c.sphere((cx, plat + 18, cx), max(6, round(9 * scale)), "oak_leaves")
    return c.v


def chess_rook(main: str = "quartz_block", accent: str = "black_concrete",
               scale: float = 1.0) -> dict:
    """Шахматная ладья-башня: точёный профиль, зубцы, клетчатая подставка."""
    c = Canvas()
    R = max(6, round(9 * scale))
    H = max(20, round(30 * scale))
    cx = R + 6
    for x in range(2 * cx + 1):                                         # клетчатая доска
        for z in range(2 * cx + 1):
            c.set(x, 0, z, main if ((x // 4) + (z // 4)) % 2 == 0 else accent)
    profile = [(0.0, 1.0), (0.10, 1.0), (0.16, 0.72), (0.5, 0.6), (0.72, 0.68),
               (0.80, 0.95), (1.0, 0.95)]
    for y in range(1, H):
        t = (y - 1) / (H - 1)
        r = R
        for (t0, r0), (t1, r1) in zip(profile, profile[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / max(1e-6, t1 - t0)
                r = R * (r0 + (r1 - r0) * k)
                break
        c.cyl((cx, y, cx), max(2, round(r)), 1, main, hollow=(0.2 < t < 0.75))
    for k in range(8):                                                  # зубцы
        a = math.radians(k * 45)
        px, pz = cx + (R * 0.95 - 1) * math.cos(a), cx + (R * 0.95 - 1) * math.sin(a)
        c.box((px - 1, H, pz - 1), (px + 1, H + 3, pz + 1), main)
    c.cyl((cx, H, cx), max(2, round(R * 0.6)), 1, main)
    return c.v


def maze(main: str = "mossy_stone_bricks", accent: str = "oak_leaves",
         scale: float = 1.0) -> dict:
    """Лабиринт: живые изгороди по сетке, вход, выход, фонтанчик в центре."""
    c = Canvas()
    cells = max(7, round(11 * scale)) | 1          # нечётное
    step = 4
    size = cells * step
    H = max(4, round(5 * scale))
    c.box((0, 0, 0), (size, 0, size), "grass_block")
    # стены по сетке: простой и читаемый узор, не требующий генерации пути
    for i in range(cells + 1):
        for j in range(cells + 1):
            x, z = i * step, j * step
            c.box((x, 1, z), (x, H, z), main)
            if (i + j) % 3 and i < cells:
                c.box((x, 1, z), (x + step, H, z), accent)
            if (i * 2 + j) % 3 and j < cells:
                c.box((x, 1, z), (x, H, z + step), accent)
    c.carve((step, 1, 0), (2 * step - 1, H, 0))                        # вход
    c.carve((size - 2 * step + 1, 1, size), (size - step, H, size))    # выход
    mid = (cells // 2) * step
    c.carve((mid - step + 1, 1, mid - step + 1), (mid + step - 1, H, mid + step - 1))
    c.cyl((mid, 1, mid), 3, 1, "smooth_stone")
    c.cyl((mid, 2, mid), 2, 1, "water")
    c.line((mid, 2, mid), (mid, 5, mid), "water", 1)
    return c.v


def pier(main: str = "oak_planks", accent: str = "spruce_log", scale: float = 1.0) -> dict:
    """Причал: настил на сваях, тумбы, лодка у края, вода."""
    c = Canvas()
    L = max(24, round(38 * scale))
    W = max(3, round(5 * scale))
    cx = W + 8
    c.box((0, 0, 0), (2 * cx, 0, L + 6), "water")
    c.box((0, 0, 0), (2 * cx, 2, 6), "sand")
    deck = 4
    c.box((cx - W, deck, 4), (cx + W, deck, L), main)
    for z in range(6, L + 1, 4):                                       # сваи
        for side in (1, -1):
            c.line((cx + side * W, 0, z), (cx + side * W, deck - 1, z), accent, 1)
    for z in range(8, L, 6):                                           # тумбы и фонари
        c.box((cx + W, deck + 1, z), (cx + W, deck + 2, z), accent)
        c.box((cx - W, deck + 1, z), (cx - W, deck + 2, z), accent)
    c.line((cx + W, deck + 1, L - 4), (cx + W, deck + 5, L - 4), "iron_bars", 1)
    c.set(cx + W, deck + 6, L - 4, "lantern")
    bx = cx + W + 5                                                    # лодка
    for z in range(L - 14, L - 2):
        t = (z - (L - 14)) / 12
        w = max(1, round(3 * math.sin(math.pi * max(0.12, t))))
        for x in range(-w, w + 1):
            c.set(bx + x, 1, z, main)
            if abs(x) == w:
                c.set(bx + x, 2, z, main)
    c.line((bx, 3, L - 9), (bx, 12, L - 9), accent, 1)
    for y in range(4, 11):
        c.box((bx + 1, y, L - 9), (bx + (11 - y) // 2 + 1, y, L - 9), "white_wool")
    return c.v


def pool(main: str = "light_blue_concrete", accent: str = "white_concrete",
         scale: float = 1.0) -> dict:
    """Бассейн: чаша с дорожками, бортик, вышка, шезлонги, зонты."""
    c = Canvas()
    W = max(10, round(16 * scale))
    D = max(14, round(22 * scale))
    cx, cz = W + 9, D + 9
    c.box((cx - W - 8, 1, cz - D - 8), (cx + W + 8, 1, cz + D + 8), accent)   # площадка
    c.box((cx - W - 1, 0, cz - D - 1), (cx + W + 1, 0, cz + D + 1), main)    # дно чаши
    c.carve((cx - W, 1, cz - D), (cx + W, 1, cz + D))                        # сама чаша
    c.box((cx - W, 0, cz - D), (cx + W, 0, cz + D), "water")
    for x in range(cx - W + 4, cx + W - 3, 5):                               # дорожки по дну
        c.box((x, 0, cz - D, ), (x, 0, cz + D), main)
    tx = cx + W + 5                                                    # вышка
    H = max(8, round(11 * scale))
    for side in (1, -1):
        c.line((tx + side, 1, cz - 2), (tx + side, H, cz - 2), "iron_block", 1)
        c.line((tx + side, 1, cz + 2), (tx + side, H, cz + 2), "iron_block", 1)
    c.box((tx - 2, H, cz - 2), (tx + 2, H, cz + 2), accent)
    c.box((tx - 1, H, cz - 6), (tx + 1, H, cz - 3), accent)
    for y in range(2, H, 2):
        c.box((tx - 2, y, cz), (tx + 2, y, cz), "iron_bars")
    for k, z in enumerate(range(cz - D + 2, cz + D - 2, 7)):           # шезлонги и зонты
        c.box((cx - W - 5, 1, z), (cx - W - 3, 1, z + 1), "white_wool")
        c.box((cx - W - 5, 2, z), (cx - W - 5, 3, z + 1), "white_wool")
        if k % 2 == 0:
            c.line((cx - W - 7, 1, z), (cx - W - 7, 5, z), accent, 1)
            c.cone((cx - W - 7, 6, z), 3, 2, "red_wool")
    return c.v


def farm(main: str = "oak_planks", accent: str = "hay_block", scale: float = 1.0) -> dict:
    """Ферма: грядки с водой, сарайчик, стога, пугало, забор."""
    c = Canvas()
    S = max(16, round(26 * scale))
    c.box((0, 0, 0), (S + 12, 0, S + 12), "grass_block")
    for x in range(3, S, 5):                                           # грядки и канавки
        for z in range(3, S):
            c.set(x, 0, z, "farmland")
            c.set(x, 1, z, "wheat")
            c.set(x + 1, 0, z, "farmland")
            c.set(x + 1, 1, z, "wheat")
            if x + 3 < S:
                c.set(x + 3, 0, z, "water")
    c.hollow((S - 2, 1, 2), (S + 9, max(6, round(8 * scale)), 11), main, 1)   # сарай
    c.roof((S - 3, max(6, round(8 * scale)) + 1, 1), (S + 10, max(6, round(8 * scale)) + 1, 12),
           "dark_oak_planks", style="gable")
    c.carve((S + 2, 1, 2), (S + 4, 5, 2))
    for k in range(3):                                                 # стога
        c.cyl((S + 3 + k * 4, 1, S - 4), 2, 3, accent)
        c.cyl((S + 3 + k * 4, 4, S - 4), 1, 1, accent)
    sx, sz = S // 2, S // 2                                            # пугало
    c.line((sx, 1, sz), (sx, 6, sz), "oak_log", 1)
    c.line((sx - 3, 5, sz), (sx + 3, 5, sz), "oak_log", 1)
    c.set(sx, 7, sz, "hay_block")
    c.box((sx - 1, 3, sz), (sx + 1, 4, sz), "brown_wool")
    for x in range(0, S + 13, 3):                                      # забор
        c.box((x, 1, 0), (x, 2, 0), main)
        c.box((x, 1, S + 12), (x, 2, S + 12), main)
    for z in range(0, S + 13, 3):
        c.box((0, 1, z), (0, 2, z), main)
    return c.v
