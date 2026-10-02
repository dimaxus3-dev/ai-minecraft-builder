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
