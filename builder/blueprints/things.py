"""Чертежи не-зданий: самолёт, корабль, ракета, поезд, танк, робот и прочее, что
просят в зале чаще всего.

Карта OpenStreetMap знает только здания, а модель рисует технику плохо (её самолёт —
крест из двух коробок). Поэтому популярные предметы собраны кодом, но с параметрами:
цвет, размер и вариант приходят из самого запроса, поэтому «большой красный самолёт» и
«маленький белый самолёт» — разные постройки. См. builder/blueprints/params.py.

Каждая функция возвращает {(x, y, z): блок}: x вправо, y вверх, z вперёд (длина).
"""

from __future__ import annotations

import math

from .kit import Canvas


# --- помощники ------------------------------------------------------------

def _tube_z(c: Canvas, cx: float, cy: float, z0: int, z1: int, radius, block: str,
            hollow: bool = False) -> None:
    """Труба вдоль z: на каждом срезе круг радиуса radius(z). Примитив cylinder
    растёт только вверх, а фюзеляж, корпус и вагон лежат лёжа."""
    for z in range(z0, z1 + 1):
        r = radius(z) if callable(radius) else radius
        if r < 0.5:
            continue
        inner = (r - 1.2) ** 2
        for x in range(-math.ceil(r), math.ceil(r) + 1):
            for y in range(-math.ceil(r), math.ceil(r) + 1):
                d = x * x + y * y
                if d <= r * r and not (hollow and d < inner):
                    c.set(cx + x, cy + y, z, block)


def _mirror_x(c: Canvas, cx: float, cells: list[tuple[float, float, float]], block: str) -> None:
    """Рисуем половину и отражаем: крылья, гусеницы, руки — симметричны."""
    for x, y, z in cells:
        c.set(cx + x, y, z, block)
        c.set(cx - x, y, z, block)


def _pad(c: Canvas, x0: int, z0: int, x1: int, z1: int, block: str = "gray_concrete") -> None:
    """Площадка под технику: без неё самолёт висит в воздухе непонятно на чём."""
    c.box((x0, 0, z0), (x1, 0, z1), block)


# --- техника --------------------------------------------------------------

def plane(main: str = "white_concrete", accent: str = "light_blue_concrete",
          scale: float = 1.0) -> dict:
    """Пассажирский самолёт на полосе: фюзеляж, стрельчатые крылья, два двигателя, киль."""
    c = Canvas()
    L = max(30, round(52 * scale))                 # длина фюзеляжа
    R = max(3, round(4.5 * scale))                 # радиус фюзеляжа
    cx, cy = R + max(18, round(24 * scale)), R + 5
    span = max(12, round(22 * scale))              # полукрыло

    _pad(c, 0, 0, 2 * cx, L + 6)
    for z in range(0, L + 7, 6):                   # разметка полосы
        c.box((cx, 0, z), (cx, 0, z + 2), "white_concrete")

    nose, tail = L * 0.12, L * 0.82

    def radius(z: float) -> float:
        if z < nose:                               # нос обтекаемый
            return R * math.sqrt(max(0.05, z / nose))
        if z > tail:                               # хвост сужается
            return R * max(0.35, 1 - (z - tail) / (L - tail) * 0.7)
        return R

    _tube_z(c, cx, cy, 0, L, radius, main)
    _tube_z(c, cx, cy, 1, round(nose) + 2, lambda z: radius(z) * 0.8, accent)  # кабина
    for z in range(round(nose) + 1, round(nose) + 4):                          # лобовые стёкла
        c.set(cx, cy + R - 1, z, "glass")
        c.set(cx + 1, cy + R - 2, z, "glass")
        c.set(cx - 1, cy + R - 2, z, "glass")
    for z in range(round(nose) + 6, round(tail), 3):                           # иллюминаторы
        c.set(cx + R, cy + 1, z, "glass")
        c.set(cx - R, cy + 1, z, "glass")

    # крыло: стрела назад, к концу тоньше
    root = round(L * 0.42)
    wing: list[tuple[float, float, float]] = []
    for s in range(span + 1):
        back = round(s * 0.55)                     # стрельчатость
        chord = max(2, round((10 - s * 0.3) * scale))
        for d in range(chord):
            wing.append((R - 1 + s, cy - 1 - (s // 10), root + back + d))
    _mirror_x(c, cx, wing, main)
    _mirror_x(c, cx, [(R + span - 2, cy - 1, root + round(span * 0.55) + 1)], accent)

    # двигатели под крылом
    for side in (1, -1):
        ex = cx + side * (R + round(span * 0.45))
        _tube_z(c, ex, cy - 3, root + 2, root + round(9 * scale), max(2, round(2.4 * scale)), "gray_concrete")
        _tube_z(c, ex, cy - 3, root + 2, root + 3, max(2, round(2.4 * scale)), accent)

    # киль и стабилизатор
    fin = max(8, round(13 * scale))
    for y in range(fin):
        back = round(y * 0.6)
        c.box((cx, cy + R - 1 + y, round(tail) + back), (cx, cy + R - 1 + y, L), accent)
    stab: list[tuple[float, float, float]] = []
    for s in range(max(5, round(9 * scale)) + 1):
        for d in range(max(2, round(5 * scale) - s // 3)):
            stab.append((s, cy + 1, L - 4 + round(s * 0.4) + d))
    _mirror_x(c, cx, stab, main)

    # шасси
    for side in (1, -1):
        c.box((cx + side * (R - 1), cy - R - 2, root + 3), (cx + side * (R - 1), cy - R, root + 4), "stone")
        c.set(cx + side * (R - 1), cy - R - 3, root + 3, "black_concrete")
    c.box((cx, cy - R - 2, round(nose) + 3), (cx, cy - R, round(nose) + 4), "stone")
    c.set(cx, cy - R - 3, round(nose) + 3, "black_concrete")
    return c.v


def ship(main: str = "dark_oak_planks", accent: str = "white_wool",
         scale: float = 1.0) -> dict:
    """Парусник: корпус-ладья, три мачты с реями и парусами, вода вокруг."""
    c = Canvas()
    L = max(34, round(58 * scale))
    W = max(5, round(8 * scale))
    cx = W + 4
    deck = max(6, round(9 * scale))

    c.box((0, 0, 0), (2 * cx, 0, L + 4), "water")          # вода вокруг корпуса

    for z in range(L + 1):
        t = z / L
        # нос острый, корма полная
        w = W * math.sin(math.pi * min(1.0, 0.18 + t * 0.9)) if t < 0.9 else W * 0.7
        w = max(1.0, w)
        for y in range(1, deck + 1):
            narrow = w * (0.45 + 0.55 * (y / deck))        # борт расходится кверху
            for x in range(-math.ceil(narrow), math.ceil(narrow) + 1):
                if abs(x) <= narrow:
                    edge = abs(x) > narrow - 1.2
                    if edge or y == 1:
                        c.set(cx + x, y, z, main)
        if t > 0.05:                                        # палуба
            w_deck = max(1.0, w * 0.95)
            for x in range(-math.ceil(w_deck), math.ceil(w_deck) + 1):
                if abs(x) <= w_deck - 1:
                    c.set(cx + x, deck, z, "spruce_planks")

    c.box((cx - 2, deck + 1, L - 10), (cx + 2, deck + 4, L - 2), main)   # надстройка на корме
    for y in range(deck + 2, deck + 4):
        c.set(cx - 3, y, L - 6, "glass")
        c.set(cx + 3, y, L - 6, "glass")

    # мачты с парусами
    for k, zm in enumerate((round(L * 0.28), round(L * 0.52), round(L * 0.76))):
        h = max(14, round((26 - k * 3) * scale))
        c.line((cx, deck, zm), (cx, deck + h, zm), "oak_log", 1)
        for level, frac in ((0.42, 0.9), (0.72, 0.65)):
            y = deck + round(h * level)
            arm = max(4, round(W * frac))
            c.line((cx - arm, y, zm), (cx + arm, y, zm), "oak_log", 1)
            for x in range(-arm + 1, arm):                  # полотно паруса
                for dy in range(1, max(4, round(h * 0.26))):
                    c.set(cx + x, y - dy, zm, accent)
        c.set(cx, deck + h + 1, zm, "red_wool")             # флажок
    c.line((cx, deck + 3, 1), (cx, deck + 9, 6), "oak_log", 1)           # бушприт
    return c.v


def rocket(main: str = "white_concrete", accent: str = "red_concrete",
           scale: float = 1.0) -> dict:
    """Ракета на стартовом столе: корпус, обтекатель, четыре стабилизатора, ферма."""
    c = Canvas()
    H = max(40, round(76 * scale))
    R = max(3, round(5 * scale))
    cx = R + 10

    c.cyl((cx, 0, cx), R + 7, 1, "gray_concrete")                 # стартовый стол
    c.cyl((cx, 1, cx), R + 7, 1, "polished_blackstone", hollow=True)

    body = round(H * 0.68)
    for y in range(2, body):
        block = main if (y // max(6, round(10 * scale))) % 2 == 0 else accent
        c.cyl((cx, y, cx), R, 1, block, hollow=True)
    c.cyl((cx, 2, cx), R, 1, main)
    for y in range(body, body + round(H * 0.2)):                   # обтекатель
        r = max(1, round(R * (1 - (y - body) / (H * 0.2))))
        c.cyl((cx, y, cx), r, 1, main, hollow=r > 2)
    c.line((cx, body + round(H * 0.2), cx), (cx, H, cx), "iron_block", 1)   # шпиль

    for k in range(4):                                             # стабилизаторы
        a = math.radians(k * 90 + 45)
        dx, dz = math.cos(a), math.sin(a)
        for s in range(max(5, round(8 * scale))):
            h = max(4, round((14 - s * 1.4) * scale))
            for y in range(2, 2 + h):
                c.set(cx + dx * (R + s), y, cx + dz * (R + s), accent)
    for k in range(4):                                             # сопла
        a = math.radians(k * 90)
        c.cyl((cx + round(math.cos(a) * R * 0.5), 2, cx + round(math.sin(a) * R * 0.5)),
              2, 2, "blackstone")

    tower = round(H * 0.62)                                        # ферма обслуживания
    tx = cx + R + 6
    for y in range(1, tower):
        c.set(tx, y, cx - 3, "iron_block")
        c.set(tx, y, cx + 3, "iron_block")
        if y % 5 == 0:
            c.line((tx, y, cx - 3), (tx, y, cx + 3), "iron_block", 1)
            c.line((tx, y, cx), (cx + R, y, cx), "iron_block", 1)
    return c.v


def train(main: str = "green_concrete", accent: str = "black_concrete",
          scale: float = 1.0) -> dict:
    """Паровоз с тендером и вагоном на рельсах: котёл, труба, колёса, насыпь."""
    c = Canvas()
    R = max(3, round(4 * scale))
    cx, cy = R + 6, 3
    L = max(46, round(74 * scale))

    c.box((cx - 5, 0, 0), (cx + 5, 0, L), "gravel")                 # насыпь
    for z in range(L + 1):
        c.set(cx - 2, 1, z, "iron_block")
        c.set(cx + 2, 1, z, "iron_block")
        if z % 3 == 0:
            c.box((cx - 4, 1, z), (cx + 4, 1, z), "dark_oak_planks")

    def wheels(z0: int, z1: int, radius: int = 2) -> None:
        for z in range(z0, z1 + 1, 5):
            for side in (1, -1):
                for a in range(0, 360, 30):
                    r = math.radians(a)
                    c.set(cx + side * 3, cy - 1 + radius * math.sin(r), z + radius * math.cos(r), accent)

    # паровоз
    boiler_end = round(L * 0.34)
    _tube_z(c, cx, cy + R, 4, boiler_end, R, main)
    c.cyl((cx, cy + R + R - 1, 8), 2, max(5, round(8 * scale)), accent, hollow=True)   # труба
    c.cyl((cx, cy + 2 * R + max(5, round(8 * scale)) - 1, 8), 3, 1, accent)
    c.sphere((cx, cy + R + R, 14), 2, "gold_block")                                    # колпак
    c.box((cx - R, cy + 1, boiler_end - 9), (cx + R, cy + 2 * R, boiler_end), main)     # будка
    c.carve((cx - R + 1, cy + 2, boiler_end - 8), (cx + R - 1, cy + 2 * R - 1, boiler_end - 1))
    for y in range(cy + 3, cy + 2 * R - 1):
        c.set(cx - R, y, boiler_end - 5, "glass")
        c.set(cx + R, y, boiler_end - 5, "glass")
    c.box((cx - R, cy + 2 * R + 1, boiler_end - 9), (cx + R, cy + 2 * R + 1, boiler_end), accent)
    c.box((cx - 2, cy, 1), (cx + 2, cy + 3, 3), accent)                                # отбойник
    wheels(6, boiler_end - 4)

    # тендер и вагон
    z = boiler_end + 3
    for length, roofed in ((round(L * 0.18), False), (round(L * 0.34), True)):
        c.box((cx - R, cy, z), (cx + R, cy + 1, z + length), main)
        c.hollow((cx - R, cy + 1, z), (cx + R, cy + R + 2, z + length), main)
        if roofed:
            c.box((cx - R - 1, cy + R + 3, z), (cx + R + 1, cy + R + 3, z + length), accent)
            for zz in range(z + 3, z + length - 2, 4):
                for y in range(cy + 3, cy + R + 2):
                    c.set(cx - R, y, zz, "glass")
                    c.set(cx + R, y, zz, "glass")
        else:
            c.box((cx - R + 1, cy + 2, z + 1), (cx + R - 1, cy + R, z + length - 1), "coal_block")
        wheels(z + 3, z + length - 3)
        z += length + 3
    return c.v


def car(main: str = "red_concrete", accent: str = "black_concrete",
        scale: float = 1.0) -> dict:
    """Легковая машина на асфальте: кузов, кабина со стёклами, четыре колеса, фары."""
    c = Canvas()
    L = max(18, round(30 * scale))
    W = max(4, round(6 * scale))
    cx, cy = W + 4, 2

    _pad(c, 0, 0, 2 * cx, L + 4, "polished_blackstone")
    for z in range(2, L + 3, 5):
        c.box((cx, 0, z), (cx, 0, z + 2), "yellow_concrete")

    c.box((cx - W, cy, 2), (cx + W, cy + 2, L), main)                       # кузов
    for z in (3, L - 1):                                                     # скосы
        c.box((cx - W, cy + 2, z), (cx + W, cy + 2, z), main)
    cab0, cab1 = round(L * 0.3), round(L * 0.72)
    c.box((cx - W, cy + 3, cab0), (cx + W, cy + 4, cab1), main)              # кабина
    c.box((cx - W + 1, cy + 5, cab0 + 1), (cx + W - 1, cy + 5, cab1 - 1), accent)   # крыша
    for y in (cy + 3, cy + 4):                                               # стёкла
        c.box((cx - W, y, cab0), (cx - W, y, cab1), "light_blue_stained_glass")
        c.box((cx + W, y, cab0), (cx + W, y, cab1), "light_blue_stained_glass")
        c.box((cx - W + 1, y, cab0), (cx + W - 1, y, cab0), "light_blue_stained_glass")
        c.box((cx - W + 1, y, cab1), (cx + W - 1, y, cab1), "light_blue_stained_glass")
    for side in (1, -1):                                                     # колёса
        for z in (round(L * 0.22), round(L * 0.82)):
            for a in range(0, 360, 25):
                r = math.radians(a)
                c.set(cx + side * (W + 1), cy + 1 + 2 * math.sin(r), z + 2 * math.cos(r), accent)
    for side in (1, -1):
        c.set(cx + side * (W - 1), cy + 1, 2, "glowstone")                   # фары
        c.set(cx + side * (W - 1), cy + 1, L, "red_concrete")                # стопы
    return c.v


def tank(main: str = "green_concrete", accent: str = "gray_concrete",
         scale: float = 1.0) -> dict:
    """Танк: корпус, гусеницы с катками, башня с пушкой."""
    c = Canvas()
    L = max(22, round(34 * scale))
    W = max(5, round(7 * scale))
    cx, cy = W + 5, 2

    _pad(c, 0, 0, 2 * cx, L + 4, "dirt_path")
    for side in (1, -1):                                                     # гусеницы
        tx = cx + side * (W + 1)
        c.box((tx, cy, 2), (tx, cy + 2, L), accent)
        c.box((tx, cy - 1, 4), (tx, cy - 1, L - 2), accent)
        c.box((tx, cy + 3, 4), (tx, cy + 3, L - 2), accent)
        for z in range(5, L - 2, 4):
            for a in range(0, 360, 40):
                r = math.radians(a)
                c.set(tx, cy + 1 + 1.6 * math.sin(r), z + 1.6 * math.cos(r), "black_concrete")

    c.box((cx - W, cy + 1, 3), (cx + W, cy + 3, L - 1), main)                # корпус
    for x in range(-W, W + 1):                                               # скошенный нос
        c.set(cx + x, cy + 3, 2, main)
    c.box((cx - W + 1, cy + 4, 5), (cx + W - 1, cy + 4, L - 3), main)

    tz = round(L * 0.56)
    c.cyl((cx, cy + 5, tz), max(4, round(5 * scale)), 3, main)               # башня
    c.cyl((cx, cy + 8, tz), max(3, round(4 * scale)), 1, main)
    barrel = max(10, round(18 * scale))
    _tube_z(c, cx, cy + 6, tz - barrel, tz - 3, 1.6, accent)                 # пушка
    _tube_z(c, cx, cy + 6, tz - barrel - 2, tz - barrel, 2.2, accent)        # дульный тормоз
    c.set(cx + 2, cy + 9, tz + 1, "black_concrete")                          # люк
    c.line((cx - 3, cy + 9, tz + 2), (cx - 3, cy + 13, tz + 2), "iron_bars", 1)   # антенна
    return c.v


def robot(main: str = "iron_block", accent: str = "light_blue_concrete",
          scale: float = 1.0) -> dict:
    """Робот: корпус, голова с визором, руки, ноги на плите."""
    c = Canvas()
    S = max(1.0, scale)
    W = max(5, round(9 * S))            # полуширина корпуса
    legs = max(10, round(16 * S))
    body = max(14, round(22 * S))
    cx = W + 8
    cz = W + 8

    c.cyl((cx, 0, cz), W + 6, 1, "polished_andesite")                        # плита

    for side in (1, -1):                                                     # ноги
        lx = cx + side * round(W * 0.5)
        c.box((lx - 2, 1, cz - 2), (lx + 2, legs, cz + 2), accent)
        c.box((lx - 3, 1, cz - 4), (lx + 3, 2, cz + 3), "gray_concrete")     # ступня
        c.box((lx - 3, round(legs * 0.5), cz - 3), (lx + 3, round(legs * 0.5) + 1, cz + 3), "gray_concrete")

    c.hollow((cx - W, legs, cz - round(W * 0.6)), (cx + W, legs + body, cz + round(W * 0.6)), main)
    c.box((cx - W + 2, legs + round(body * 0.55), cz - round(W * 0.6)),
          (cx + W - 2, legs + round(body * 0.8), cz - round(W * 0.6)), accent)   # нагрудник
    c.set(cx, legs + round(body * 0.45), cz - round(W * 0.6), "redstone_lamp")

    for side in (1, -1):                                                     # руки
        ax = cx + side * (W + 2)
        c.sphere((ax, legs + body - 2, cz), 2, main)
        c.box((ax - 1, legs + round(body * 0.25), cz - 1), (ax + 1, legs + body - 3, cz + 1), accent)
        c.box((ax - 2, legs + round(body * 0.18), cz - 2), (ax + 2, legs + round(body * 0.25), cz + 2), main)

    head = legs + body + 1                                                   # голова
    hw = max(3, round(W * 0.55))
    c.hollow((cx - hw, head, cz - hw), (cx + hw, head + 2 * hw, cz + hw), main)
    c.box((cx - hw + 1, head + hw, cz - hw), (cx + hw - 1, head + hw + 1, cz - hw), "cyan_stained_glass")
    for side in (1, -1):
        c.line((cx + side * hw, head + 2 * hw, cz), (cx + side * hw, head + 2 * hw + 3, cz), "iron_bars", 1)
        c.set(cx + side * hw, head + 2 * hw + 4, cz, "redstone_lamp")
    return c.v


# --- природа и малые формы -------------------------------------------------

def tree(main: str = "oak_log", accent: str = "oak_leaves",
         scale: float = 1.0) -> dict:
    """Большое дерево: витой ствол, ветви, шапка листвы, трава и камни у корней."""
    c = Canvas()
    H = max(18, round(30 * scale))
    cx = max(14, round(20 * scale))

    for x in range(2 * cx + 1):                                              # холмик
        for z in range(2 * cx + 1):
            if math.hypot(x - cx, z - cx) <= cx - 1:
                c.set(x, 0, z, "grass_block")

    for y in range(1, H):                                                    # ствол
        r = max(1.0, (3.2 - 2.2 * y / H) * scale)
        sway = math.sin(y / 7) * 1.5
        for x in range(-math.ceil(r), math.ceil(r) + 1):
            for z in range(-math.ceil(r), math.ceil(r) + 1):
                if x * x + z * z <= r * r:
                    c.set(cx + x + sway, y, cx + z, main)

    for k in range(6):                                                       # ветви
        a = math.radians(k * 60 + 15)
        y0 = round(H * (0.55 + 0.06 * (k % 3)))
        tip = (cx + math.cos(a) * cx * 0.6, y0 + H * 0.22, cx + math.sin(a) * cx * 0.6)
        c.line((cx, y0, cx), tip, main, 1)
        c.sphere((round(tip[0]), round(tip[1]), round(tip[2])), max(3, round(5 * scale)), accent)

    crown = max(7, round(11 * scale))                                        # шапка
    c.sphere((cx, H, cx), crown, accent)
    c.sphere((cx, H + round(crown * 0.6), cx), round(crown * 0.7), accent)
    for k in range(5):                                                       # камни у корней
        a = math.radians(k * 72)
        c.sphere((cx + math.cos(a) * (cx - 3), 0, cx + math.sin(a) * (cx - 3)), 1, "mossy_cobblestone")
    return c.v


def ferris_wheel(main: str = "iron_block", accent: str = "red_concrete",
                 scale: float = 1.0) -> dict:
    """Колесо обозрения: обод со спицами, кабинки, две опоры, площадка."""
    c = Canvas()
    R = max(14, round(24 * scale))
    cy = R + 3
    cx = R + 4
    cz = 8

    c.box((0, 0, 0), (2 * cx, 0, 2 * cz), "smooth_stone")                    # площадка
    for side in (1, -1):                                                     # опоры
        c.line((cx + side * round(R * 0.5), 1, cz - 4), (cx, cy, cz), main, 1)
        c.line((cx + side * round(R * 0.5), 1, cz + 4), (cx, cy, cz), main, 1)
    c.cyl((cx, cy - 1, cz), 2, 3, main)                                      # ступица

    for a in range(0, 360, 4):                                               # обод
        r = math.radians(a)
        for dz in (-2, 2):
            c.set(cx + R * math.cos(r), cy + R * math.sin(r), cz + dz, main)
    for k in range(12):                                                      # спицы и кабинки
        a = math.radians(k * 30)
        tip = (cx + R * math.cos(a), cy + R * math.sin(a), cz)
        c.line((cx, cy, cz - 2), (tip[0], tip[1], cz - 2), main, 1)
        c.line((cx, cy, cz + 2), (tip[0], tip[1], cz + 2), main, 1)
        bx, by = cx + (R - 3) * math.cos(a), cy + (R - 3) * math.sin(a)
        colour = accent if k % 2 == 0 else "yellow_concrete"
        c.box((bx - 1, by - 2, cz - 2), (bx + 1, by, cz + 2), colour)
        c.box((bx - 1, by - 3, cz - 1), (bx + 1, by - 3, cz + 1), "glass")
    return c.v


def fountain(main: str = "quartz_block", accent: str = "prismarine",
             scale: float = 1.0) -> dict:
    """Фонтан: чаши, струи, бортик с фонарями, мокрая площадь."""
    c = Canvas()
    R = max(10, round(16 * scale))
    cx = R + 2

    c.cyl((cx, 0, cx), R, 1, "smooth_stone")                                 # площадь
    c.cyl((cx, 1, cx), R - 1, 1, main, hollow=True)
    c.cyl((cx, 1, cx), R - 2, 1, "water")
    c.cyl((cx, 2, cx), R - 1, 1, main, hollow=True)

    c.cyl((cx, 2, cx), max(4, round(6 * scale)), 3, accent)                  # нижняя чаша
    c.cyl((cx, 5, cx), max(5, round(7 * scale)), 1, main, hollow=True)
    c.cyl((cx, 5, cx), max(4, round(6 * scale)) - 1, 1, "water")
    c.cyl((cx, 6, cx), 2, max(5, round(7 * scale)), accent)                  # колонна
    top = 6 + max(5, round(7 * scale))
    c.cyl((cx, top, cx), max(3, round(4 * scale)), 1, main, hollow=True)
    c.cyl((cx, top, cx), max(3, round(4 * scale)) - 1, 1, "water")
    c.sphere((cx, top + 3, cx), 2, "water")                                  # верхняя струя
    c.line((cx, top + 1, cx), (cx, top + 3, cx), "water", 1)

    for k in range(8):                                                       # струи по кругу
        a = math.radians(k * 45)
        jx, jz = cx + (R - 3) * math.cos(a), cx + (R - 3) * math.sin(a)
        c.line((jx, 3, jz), (jx, 6, jz), "water", 1)
        if k % 2 == 0:                                                       # фонари на бортике
            lx, lz = cx + (R - 1) * math.cos(a), cx + (R - 1) * math.sin(a)
            c.line((lx, 3, lz), (lx, 6, lz), "iron_bars", 1)
            c.set(lx, 7, lz, "lantern")
    return c.v


def statue(main: str = "quartz_block", accent: str = "gold_block",
           scale: float = 1.0) -> dict:
    """Статуя на постаменте: фигура с поднятой рукой, плащ, ступени."""
    c = Canvas()
    S = max(1.0, scale)
    ped = max(8, round(12 * S))
    cx = cz = max(12, round(16 * S))

    for k in range(3):                                                       # ступени
        c.box((k, k, k), (2 * cx - k, k, 2 * cz - k), "smooth_stone")
    c.hollow((4, 3, 4), (2 * cx - 4, ped, 2 * cz - 4), "chiseled_stone_bricks")
    c.box((3, ped, 3), (2 * cx - 3, ped, 2 * cz - 3), "polished_andesite")
    c.box((cx - 4, ped - 3, 3), (cx + 4, ped - 1, 3), accent)                # табличка

    legs = max(10, round(15 * S))
    for side in (1, -1):                                                     # ноги
        c.box((cx + side * 2 - 1, ped + 1, cz - 2), (cx + side * 2 + 1, ped + legs, cz + 2), main)
    torso = max(12, round(18 * S))
    c.hollow((cx - 4, ped + legs, cz - 3), (cx + 4, ped + legs + torso, cz + 3), main)
    for y in range(ped + legs, ped + legs + torso):                          # плащ: по краям и со спины
        w = 5 + round((y - ped - legs) / torso * 3)
        for side in (1, -1):
            c.set(cx + side * w, y, cz + 3, accent)
            c.box((cx + side * w, y, cz + 4), (cx + side * (w - 1), y, cz + 4), accent)

    sh = ped + legs + torso
    c.box((cx - 6, sh - 2, cz - 2), (cx + 6, sh, cz + 2), main)              # плечи
    arm = max(8, round(12 * S))
    for y in range(arm):                                                     # поднятая рука
        c.box((cx + 5 + y // 4, sh + y, cz - 1), (cx + 6 + y // 4, sh + y, cz + 1), main)
    c.sphere((cx + 6 + arm // 4, sh + arm + 1, cz), 2, accent)               # факел
    c.set(cx + 6 + arm // 4, sh + arm + 3, cz, "glowstone")
    c.box((cx - 7, sh - 1, cz - 1), (cx - 6, sh + round(arm * 0.5), cz + 1), main)   # опущенная рука
    c.box((cx - 8, sh + round(arm * 0.4), cz - 2), (cx - 5, sh + round(arm * 0.5), cz + 2), accent)

    c.box((cx - 2, sh + 1, cz - 1), (cx + 2, sh + 2, cz + 1), main)          # шея
    c.sphere((cx, sh + 6, cz), 3, main)                                      # голова
    c.set(cx - 1, sh + 6, cz - 3, "black_concrete")
    c.set(cx + 1, sh + 6, cz - 3, "black_concrete")
    for k in range(7):                                                       # венец
        a = math.radians(k * 26 - 78)
        c.set(cx + 5 * math.sin(a), sh + 10, cz - 5 * math.cos(a) * 0.4, accent)
    return c.v


def stadium(main: str = "white_concrete", accent: str = "red_concrete",
            scale: float = 1.0) -> dict:
    """Стадион: овальные трибуны, поле с разметкой, прожекторы по углам."""
    c = Canvas()
    A = max(26, round(40 * scale))        # полуось вдоль x
    B = max(18, round(28 * scale))        # полуось вдоль z
    cx, cz = A + 4, B + 4

    for x in range(2 * cx + 1):                                              # поле
        for z in range(2 * cz + 1):
            e = ((x - cx) / (A - 7)) ** 2 + ((z - cz) / (B - 7)) ** 2
            if e <= 1:
                c.set(x, 0, z, "green_concrete")
    c.box((cx - 1, 0, cz - B + 7), (cx + 1, 0, cz + B - 7), "white_concrete")     # центр
    for z in (cz - round(B * 0.55), cz + round(B * 0.55)):                        # ворота
        c.box((cx - 6, 0, z), (cx + 6, 0, z), "white_concrete")
        c.box((cx - 5, 1, z), (cx + 5, 3, z), "iron_bars")

    for tier in range(max(5, round(8 * scale))):                             # трибуны
        for a in range(0, 360, 2):
            r = math.radians(a)
            x = cx + (A - 6 + tier) * math.cos(r)
            z = cz + (B - 6 + tier) * math.sin(r)
            colour = accent if (tier + a // 18) % 3 == 0 else main
            for y in range(tier, tier + 2):
                c.set(x, y, z, colour)
    for a in range(0, 360, 3):                                               # кромка козырька
        r = math.radians(a)
        tier = max(5, round(8 * scale))
        c.set(cx + (A + 1) * math.cos(r), tier + 3, cz + (B + 1) * math.sin(r), "light_gray_concrete")
        c.set(cx + (A - 2) * math.cos(r), tier + 4, cz + (B - 2) * math.sin(r), "light_gray_concrete")

    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):                      # прожекторы
        px, pz = cx + sx * round(A * 0.78), cz + sz * round(B * 0.78)
        h = max(14, round(20 * scale))
        c.line((px, 0, pz), (px, h, pz), "iron_block", 1)
        c.box((px - 2, h, pz - 1), (px + 2, h + 2, pz + 1), "glowstone")
    return c.v


# --- вторая партия: ещё техника и малые формы ------------------------------

def helicopter(main: str = "green_concrete", accent: str = "black_concrete",
               scale: float = 1.0) -> dict:
    """Вертолёт на площадке: кабина со стеклом, хвостовая балка, два винта, полозья."""
    c = Canvas()
    L = max(26, round(40 * scale))
    R = max(3, round(5 * scale))
    cx, cy = R + max(14, round(20 * scale)), R + 4

    c.cyl((cx, 0, round(L * 0.35)), max(10, round(14 * scale)), 1, "polished_blackstone")
    for a in range(0, 360, 6):                                               # буква H на площадке
        pass
    c.box((cx - 4, 0, round(L * 0.35) - 5), (cx - 4, 0, round(L * 0.35) + 5), "white_concrete")
    c.box((cx + 4, 0, round(L * 0.35) - 5), (cx + 4, 0, round(L * 0.35) + 5), "white_concrete")
    c.box((cx - 4, 0, round(L * 0.35)), (cx + 4, 0, round(L * 0.35)), "white_concrete")

    cab = round(L * 0.45)
    _tube_z(c, cx, cy, 2, cab, lambda z: R * (0.55 + 0.45 * math.sin(math.pi * min(1, z / cab))), main)
    for z in range(3, 7):                                                    # остекление кабины
        for y in range(cy, cy + R - 1):
            c.set(cx - round(R * 0.8), y, z, "light_blue_stained_glass")
            c.set(cx + round(R * 0.8), y, z, "light_blue_stained_glass")
            c.set(cx, y + 1, z - 1, "light_blue_stained_glass")
    _tube_z(c, cx, cy + 1, cab, L, lambda z: max(1.4, R * 0.45 * (1 - (z - cab) / (L - cab) * 0.5)), main)

    fin = max(6, round(9 * scale))                                           # киль
    for y in range(fin):
        c.box((cx, cy + 2 + y, L - 3 + y // 3), (cx, cy + 2 + y, L), accent)
    for a in range(0, 360, 20):                                              # рулевой винт
        r = math.radians(a)
        c.set(cx + 1, cy + 4 + 4 * math.sin(r), L - 2 + 4 * math.cos(r), accent)

    mast = cy + R + 2                                                        # мачта и несущий винт
    c.box((cx - 1, cy + R - 1, round(L * 0.26)), (cx + 1, mast, round(L * 0.3)), accent)
    blade = max(14, round(22 * scale))
    for k in range(4):
        a = math.radians(k * 90 + 12)
        c.line((cx, mast + 1, round(L * 0.28)),
               (cx + blade * math.cos(a), mast + 1, round(L * 0.28) + blade * math.sin(a)), accent, 1)
    for side in (1, -1):                                                     # полозья
        sx = cx + side * (R - 1)
        c.box((sx, cy - R - 1, 4), (sx, cy - R - 1, cab - 2), "iron_block")
        for z in (6, cab - 4):
            c.box((sx, cy - R - 1, z), (sx, cy - R + 1, z), "iron_block")
    return c.v


def submarine(main: str = "black_concrete", accent: str = "yellow_concrete",
              scale: float = 1.0) -> dict:
    """Подводная лодка: сигарообразный корпус, рубка с перископом, винт, вода."""
    c = Canvas()
    L = max(40, round(64 * scale))
    R = max(4, round(6 * scale))
    cx, cy = R + 4, R + 2

    c.box((0, 0, 0), (2 * cx, cy - 1, L + 6), "water")
    nose, tail = L * 0.16, L * 0.82

    def radius(z: float) -> float:
        if z < nose:
            return R * math.sqrt(max(0.06, z / nose))
        if z > tail:
            return R * max(0.3, 1 - (z - tail) / (L - tail) * 0.8)
        return R

    _tube_z(c, cx, cy, 0, L, radius, main)
    for z in range(round(nose) + 2, round(tail), 6):                         # полоса по борту
        c.set(cx + R, cy, z, accent)
        c.set(cx - R, cy, z, accent)

    tower = round(L * 0.36)                                                  # рубка
    c.box((cx - 2, cy + R - 1, tower), (cx + 2, cy + R + max(5, round(7 * scale)), tower + round(L * 0.16)), main)
    c.box((cx - 2, cy + R + max(5, round(7 * scale)), tower), (cx + 2, cy + R + max(5, round(7 * scale)),
          tower + round(L * 0.16)), accent)
    top = cy + R + max(5, round(7 * scale))
    c.line((cx, top + 1, tower + 2), (cx, top + 5, tower + 2), "iron_bars", 1)       # перископ
    c.set(cx, top + 6, tower + 2, "glowstone")
    for side in (1, -1):                                                     # горизонтальные рули
        c.box((cx + side * 3, cy + R - 2, tower + 2), (cx + side * 6, cy + R - 2, tower + 5), main)
        c.box((cx + side * (R + 1), cy, L - 8), (cx + side * (R + 5), cy, L - 4), main)
    c.box((cx, cy - R - 4, L - 8), (cx, cy + R + 4, L - 4), main)            # вертикальный руль
    for k in range(5):                                                       # винт
        a = math.radians(k * 72)
        c.line((cx, cy, L + 1), (cx + 3 * math.cos(a), cy + 3 * math.sin(a), L + 2), accent, 1)
    return c.v


def bridge(main: str = "stone_bricks", accent: str = "polished_andesite",
           scale: float = 1.0) -> dict:
    """Арочный мост через реку: быки, арки, настил, перила и фонари."""
    c = Canvas()
    span = max(14, round(20 * scale))          # пролёт
    n = 4                                      # сколько арок
    L = span * n + 8
    W = max(5, round(8 * scale))
    deck = max(12, round(16 * scale))
    cx = W + 3

    c.box((0, 0, 0), (2 * cx, 0, L), "water")                                # река
    for z in (0, L):                                                         # берега
        c.box((0, 0, max(0, z - 6)), (2 * cx, 2, min(L, z + 6)), "grass_block")

    for k in range(n + 1):                                                   # быки и арки
        z = 4 + k * span
        c.box((cx - W, 1, z - 2), (cx + W, deck - 1, z + 2), main)
        if k < n:
            h = round(span * 0.45)
            c.arch((cx - W, deck - 1 - h, z + 3), (cx - W, deck - 1, z + span - 3), h, main, 2)
            c.arch((cx + W, deck - 1 - h, z + 3), (cx + W, deck - 1, z + span - 3), h, main, 2)
            for x in range(-W + 1, W):                                       # свод
                c.arch((cx + x, deck - 1 - h, z + 3), (cx + x, deck - 1, z + span - 3), h, accent)

    c.box((cx - W, deck, 0), (cx + W, deck, L), accent)                      # настил
    c.box((cx - W + 1, deck + 1, 0), (cx + W - 1, deck + 1, L), "gravel")
    for side in (1, -1):                                                     # перила и фонари
        for z in range(0, L + 1):
            c.set(cx + side * W, deck + 1, z, main)
            if z % 2 == 0:
                c.set(cx + side * W, deck + 2, z, "iron_bars")
        for z in range(4, L, span // 2 or 1):
            c.line((cx + side * W, deck + 2, z), (cx + side * W, deck + 5, z), main, 1)
            c.set(cx + side * W, deck + 6, z, "lantern")
    return c.v


def mosque(main: str = "white_concrete", accent: str = "cyan_concrete",
           scale: float = 1.0) -> dict:
    """Мечеть: купольный зал, четыре минарета, портал с аркой, двор."""
    c = Canvas()
    S = max(16, round(24 * scale))             # полуширина зала
    cx = cz = S + 8

    c.box((cx - S - 7, 0, cz - S - 7), (cx + S + 7, 0, cz + S + 7), "smooth_sandstone")   # двор
    c.hollow((cx - S, 1, cz - S), (cx + S, max(14, round(20 * scale)), cz + S), main, 2)
    wall = max(14, round(20 * scale))
    c.box((cx - S, wall + 1, cz - S), (cx + S, wall + 1, cz + S), accent)

    c.dome((cx, wall + 2, cz), S - 2, accent)                                # главный купол
    c.cyl((cx, wall + 2 + S - 2, cz), 2, 3, "gold_block")
    c.sphere((cx, wall + 5 + S - 2, cz), 2, "gold_block")
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):                        # малые купола
        c.dome((cx + dx * round(S * 0.7), wall + 2, cz + dz * round(S * 0.7)), max(4, round(6 * scale)), accent)

    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):                      # минареты
        mx, mz = cx + sx * (S + 4), cz + sz * (S + 4)
        h = max(28, round(42 * scale))
        c.cyl((mx, 1, mz), 3, h, main, hollow=True)
        c.cyl((mx, round(h * 0.65), mz), 4, 1, accent)
        c.cyl((mx, round(h * 0.65) + 1, mz), 4, 2, main, hollow=True)
        c.cone((mx, h + 1, mz), 3, 6, accent)
        c.set(mx, h + 8, mz, "gold_block")

    portal = max(8, round(12 * scale))                                       # портал
    c.box((cx - portal, 1, cz - S - 2), (cx + portal, wall + 4, cz - S - 1), main)
    c.arch((cx - portal + 3, 1, cz - S - 2), (cx + portal - 3, portal, cz - S - 1), portal, accent, 2)
    c.carve((cx - portal + 4, 1, cz - S - 2), (cx + portal - 4, portal - 2, cz - S - 1))
    for y in range(4, wall, 4):                                              # окна
        for x in range(-S + 4, S - 3, 6):
            c.box((cx + x, y, cz + S), (cx + x, y + 1, cz + S), "light_blue_stained_glass")
    return c.v


def obelisk(main: str = "smooth_sandstone", accent: str = "gold_block",
            scale: float = 1.0) -> dict:
    """Обелиск на ступенях: сужающийся столб, золотая пирамидка, чаши с огнём."""
    c = Canvas()
    H = max(36, round(58 * scale))
    base = max(5, round(7 * scale))
    cx = cz = base + 8

    for k in range(4):                                                       # ступени
        c.box((cx - base - 4 + k, k, cz - base - 4 + k), (cx + base + 4 - k, k, cz + base + 4 - k), "smooth_stone")
    c.box((cx - base, 4, cz - base), (cx + base, 7, cz + base), main)        # цоколь
    for y in range(8, H):                                                    # столб
        r = max(1, round(base * 0.7 * (1 - 0.45 * (y - 8) / (H - 8))))
        c.box((cx - r, y, cz - r), (cx + r, y, cz + r), main)
    tip = max(3, round(base * 0.4))
    c.cone((cx, H, cz), tip, tip * 2, accent)                                # пирамидка
    for y in range(10, H - 4, 6):                                            # иероглифы-насечки
        c.set(cx, y, cz - max(1, round(base * 0.7 * (1 - 0.45 * (y - 8) / (H - 8)))), accent)
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):                      # чаши с огнём
        fx, fz = cx + sx * (base + 3), cz + sz * (base + 3)
        c.cyl((fx, 4, fz), 2, 3, main)
        c.cyl((fx, 7, fz), 2, 1, accent)
        c.set(fx, 8, fz, "glowstone")
    return c.v


def triumphal_arch(main: str = "smooth_sandstone", accent: str = "gold_block",
                   scale: float = 1.0) -> dict:
    """Триумфальная арка: большой проём, колонны, карниз, квадрига на крыше."""
    c = Canvas()
    W = max(14, round(22 * scale))             # полуширина
    H = max(22, round(34 * scale))
    D = max(5, round(8 * scale))
    cx, cz = W + 3, D + 3

    c.box((cx - W - 3, 0, cz - D - 3), (cx + W + 3, 0, cz + D + 3), "smooth_stone")
    c.box((cx - W, 1, cz - D), (cx + W, H, cz + D), main)                    # массив
    hole = round(W * 0.42)                                                   # главный проём
    c.carve((cx - hole, 1, cz - D), (cx + hole, round(H * 0.45), cz + D))
    for x in range(-hole, hole + 1):
        c.arch((cx + x, round(H * 0.45), cz - D), (cx + x, round(H * 0.45), cz + D), hole, main)
    c.put([(cx + x, y, z) for x, y, z in []], main)
    for z in range(cz - D, cz + D + 1):                                      # свод проёма
        c.arch((cx - hole, round(H * 0.45) - hole, z), (cx + hole, round(H * 0.45), z), hole, main)
    c.carve((cx - hole + 1, 1, cz - D), (cx + hole - 1, round(H * 0.45) - 1, cz + D))

    for side in (1, -1):                                                     # боковые проёмы
        sx = cx + side * round(W * 0.72)
        c.carve((sx - 2, 1, cz - D), (sx + 2, round(H * 0.24), cz + D))
    for side in (1, -1):                                                     # колонны
        for k in (0.5, 0.95):
            px = cx + side * round(W * k)
            for z in (cz - D, cz + D):
                c.cyl((px, 1, z), 2, round(H * 0.6), accent if k > 0.9 else main)
                c.cyl((px, 1 + round(H * 0.6), z), 3, 1, accent)
    c.box((cx - W - 2, H - 3, cz - D - 2), (cx + W + 2, H - 1, cz + D + 2), accent)   # карниз
    c.box((cx - W, H, cz - D), (cx + W, H, cz + D), main)

    qx = cx                                                                   # квадрига
    c.box((qx - 3, H + 1, cz - 1), (qx + 3, H + 3, cz + 1), accent)
    for k in range(4):
        hx = qx - 5 + k * 3
        c.box((hx, H + 1, cz - 4), (hx, H + 4, cz - 2), main)
        c.set(hx, H + 5, cz - 4, main)
    return c.v


def clock_tower(main: str = "smooth_sandstone", accent: str = "gold_block",
                scale: float = 1.0) -> dict:
    """Часовая башня: подножие, ствол, четыре циферблата, шпиль с фонарём."""
    c = Canvas()
    S = max(6, round(9 * scale))               # полуширина
    H = max(42, round(64 * scale))
    cx = cz = S + 6

    c.box((cx - S - 3, 0, cz - S - 3), (cx + S + 3, 1, cz + S + 3), "stone_bricks")
    c.hollow((cx - S, 2, cz - S), (cx + S, round(H * 0.72), cz + S), main, 2)
    for y in range(6, round(H * 0.7), 7):                                     # вертикальные тяги
        for x in (-S, S):
            c.box((cx + x, y, cz - S + 2), (cx + x, y + 4, cz - S + 2), accent)
            c.box((cx + x, y, cz + S - 2), (cx + x, y + 4, cz + S - 2), accent)
    c.carve((cx - 2, 2, cz - S), (cx + 2, 7, cz - S))                         # вход
    c.arch((cx - 2, 2, cz - S), (cx + 2, 7, cz - S), 3, accent)
    # стрельчатые окна по ярусам: голый ствол выглядел пустым
    for y in range(12, round(H * 0.68), 11):
        for ddx, ddz in ((0, -S), (0, S), (-S, 0), (S, 0)):
            wx, wz = cx + ddx, cz + ddz
            c.box((wx - (1 if ddz else 0), y, wz - (1 if ddx else 0)),
                  (wx + (1 if ddz else 0), y + 4, wz + (1 if ddx else 0)), "light_blue_stained_glass")
            c.box((wx - (1 if ddz else 0), y + 5, wz - (1 if ddx else 0)),
                  (wx + (1 if ddz else 0), y + 5, wz + (1 if ddx else 0)), accent)

    face = round(H * 0.74)                                                    # ярус с часами
    c.box((cx - S - 2, face - 2, cz - S - 2), (cx + S + 2, face - 1, cz + S + 2), accent)
    c.hollow((cx - S - 1, face, cz - S - 1), (cx + S + 1, face + 2 * S, cz + S + 1), main, 2)
    r = S - 1
    for dx, dz, nx, nz in ((0, -S - 1, 1, 0), (0, S + 1, 1, 0), (-S - 1, 0, 0, 1), (S + 1, 0, 0, 1)):
        fy = face + S
        # белое поле циферблата: на песчанике стрелки терялись, часы читаются издалека
        for u in range(-r, r + 1):
            for v in range(-r, r + 1):
                if u * u + v * v <= (r - 1) ** 2:
                    c.set(cx + dx + nx * u, fy + v, cz + dz + nz * u, "white_concrete")
        for a in range(0, 360, 4):                                            # ободок
            t = math.radians(a)
            c.set(cx + dx + nx * r * math.cos(t), fy + r * math.sin(t), cz + dz + nz * r * math.cos(t), accent)
        for a in range(0, 360, 30):                                           # деления
            t = math.radians(a)
            c.set(cx + dx + nx * (r - 1) * math.cos(t), fy + (r - 1) * math.sin(t),
                  cz + dz + nz * (r - 1) * math.cos(t), "black_concrete")
        for s in range(r - 2):                                                # стрелки
            c.set(cx + dx + nx * 0, fy + s, cz + dz + nz * 0, "black_concrete")
        for s in range(r - 4):
            c.set(cx + dx + nx * s, fy, cz + dz + nz * s, "black_concrete")

    top = face + 2 * S
    c.box((cx - S - 2, top, cz - S - 2), (cx + S + 2, top + 1, cz + S + 2), accent)
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):                       # пинакли
        c.cone((cx + sx * (S + 1), top + 2, cz + sz * (S + 1)), 2, 5, main)
    c.cone((cx, top + 2, cz), S, max(12, round(18 * scale)), main)            # шпиль
    c.set(cx, top + 2 + max(12, round(18 * scale)), cz, "glowstone")
    c.line((cx, top + 3 + max(12, round(18 * scale)), cz),
           (cx, top + 6 + max(12, round(18 * scale)), cz), accent, 1)
    return c.v


def igloo(main: str = "snow_block", accent: str = "packed_ice",
          scale: float = 1.0) -> dict:
    """Иглу: снежный купол, тоннель-вход, ледяное окно, костёр и сугробы."""
    c = Canvas()
    R = max(9, round(13 * scale))
    cx = cz = R + 9

    for x in range(2 * cx + 1):                                               # снежная поляна
        for z in range(2 * cz + 1):
            if math.hypot(x - cx, z - cz) <= cx - 1:
                c.set(x, 0, z, "snow_block")

    c.dome((cx, 1, cz), R, main, hollow=True)                                 # купол
    c.dome((cx, 1, cz), R - 2, "air")
    for y in range(1, R):                                                     # кладка полосами
        if y % 3 == 0:
            for a in range(0, 360, 5):
                t = math.radians(a)
                rr = math.sqrt(max(0.0, R * R - (y - 1) ** 2))
                c.set(cx + rr * math.cos(t), y, cz + rr * math.sin(t), accent)
    c.set(cx, R, cz, accent)                                                  # люк дымохода
    c.set(cx + 1, round(R * 0.62), cz - round(R * 0.78), "light_blue_stained_glass")
    c.set(cx - 1, round(R * 0.62), cz - round(R * 0.78), "light_blue_stained_glass")

    tz = cz - R                                                               # тоннель
    for z in range(tz - max(5, round(7 * scale)), tz + 2):
        c.dome((cx, 1, z), 3, main, hollow=True)
    c.carve((cx - 2, 1, tz - max(5, round(7 * scale))), (cx + 2, 3, tz + 1))
    c.box((cx - 1, 1, tz - max(5, round(7 * scale)) - 1), (cx + 1, 3, tz - max(5, round(7 * scale)) - 1), "air")

    fx, fz = cx + R + 4, cz                                                   # костёр
    for a in range(0, 360, 45):
        t = math.radians(a)
        c.set(fx + 2 * math.cos(t), 1, fz + 2 * math.sin(t), "cobblestone")
    c.set(fx, 1, fz, "campfire")
    c.set(fx, 2, fz, "fire")
    for k in range(6):                                                        # сугробы
        a = math.radians(k * 61)
        c.sphere((cx + math.cos(a) * (R + 6), 0, cz + math.sin(a) * (R + 6)), 2, main)
    return c.v


def mansion(main: str = "spruce_planks", accent: str = "stone_bricks",
            scale: float = 1.0) -> dict:
    """Особняк: два этажа с крыльями, высокая крыша, башенка, крыльцо с колоннами, сад."""
    c = Canvas()
    W = max(14, round(21 * scale))             # полуширина центрального корпуса
    D = max(10, round(15 * scale))             # полуглубина
    floor = max(6, round(8 * scale))
    cx, cz = W + 12, D + 12

    # сад, дорожка и ограда
    c.box((cx - W - 11, 0, cz - D - 11), (cx + W + 11, 0, cz + D + 11), "grass_block")
    c.box((cx - 3, 0, cz - D - 11), (cx + 3, 0, cz - D - 1), "gravel")
    for x in range(cx - W - 11, cx + W + 12, 3):
        c.box((x, 1, cz - D - 11), (x, 2, cz - D - 11), accent)
        c.box((x, 1, cz + D + 11), (x, 2, cz + D + 11), accent)

    # цоколь и два этажа
    c.box((cx - W, 1, cz - D), (cx + W, 1, cz + D), accent)
    for level in range(2):
        y0 = 2 + level * floor
        c.hollow((cx - W, y0, cz - D), (cx + W, y0 + floor - 1, cz + D), main, 1)
        for x in range(cx - W + 3, cx + W - 2, 5):          # окна
            c.box((x, y0 + 2, cz - D), (x + 1, y0 + 4, cz - D), "glass")
            c.box((x, y0 + 2, cz + D), (x + 1, y0 + 4, cz + D), "glass")
        for z in range(cz - D + 3, cz + D - 2, 5):
            c.box((cx - W, y0 + 2, z), (cx - W, y0 + 4, z + 1), "glass")
            c.box((cx + W, y0 + 2, z), (cx + W, y0 + 4, z + 1), "glass")
        c.box((cx - W, y0 - 1, cz - D), (cx + W, y0 - 1, cz + D), accent)   # поясок

    top = 2 + 2 * floor
    # боковые крылья пониже
    for side in (1, -1):
        wx = cx + side * (W + max(5, round(8 * scale)))
        c.hollow((wx - 5, 2, cz - D + 3), (wx + 5, 2 + floor, cz + D - 3), main, 1)
        c.roof((wx - 6, 3 + floor, cz - D + 2), (wx + 6, 3 + floor, cz + D - 2), accent, style="gable")
        for z in range(cz - D + 5, cz + D - 4, 4):
            c.box((wx + side * 5, 4, z), (wx + side * 5, 6, z), "glass")

    c.roof((cx - W - 1, top, cz - D - 1), (cx + W + 1, top, cz + D + 1), accent, style="hip")

    # крыльцо с колоннами и ступенями
    for x in (-5, -2, 2, 5):
        c.cyl((cx + x, 2, cz - D - 4), 1, floor + 2, accent)
    c.box((cx - 7, 2 + floor + 2, cz - D - 6), (cx + 7, 2 + floor + 3, cz - D), accent)
    c.roof((cx - 7, 2 + floor + 4, cz - D - 6), (cx + 7, 2 + floor + 4, cz - D), accent, style="gable")
    for k in range(3):
        c.box((cx - 6 + k, 1 + k, cz - D - 7 + k), (cx + 6 - k, 1 + k, cz - D - 7 + k), accent)
    c.carve((cx - 2, 2, cz - D), (cx + 2, 6, cz - D))
    c.box((cx - 2, 2, cz - D), (cx + 2, 5, cz - D), "dark_oak_planks")

    # башенка на крыше
    tw = max(4, round(6 * scale))
    c.hollow((cx - tw, top, cz - tw), (cx + tw, top + max(9, round(13 * scale)), cz + tw), accent, 1)
    ty = top + max(9, round(13 * scale))
    for side in (-1, 1):
        c.box((cx + side * tw, top + 3, cz - 1), (cx + side * tw, top + 6, cz + 1), "glass")
        c.box((cx - 1, top + 3, cz + side * tw), (cx + 1, top + 6, cz + side * tw), "glass")
    c.cone((cx, ty + 1, cz), tw + 1, max(8, round(11 * scale)), main)
    c.line((cx, ty + 1 + max(8, round(11 * scale)), cz),
           (cx, ty + 4 + max(8, round(11 * scale)), cz), "iron_bars", 1)
    c.set(cx, ty + 5 + max(8, round(11 * scale)), cz, "gold_block")

    # трубы
    for side in (1, -1):
        c.box((cx + side * (W - 4), top + 1, cz + D - 4), (cx + side * (W - 2), top + 7, cz + D - 2), accent)
    return c.v
