"""Дракон: изогнутый позвоночник, перепончатые крылья, рогатая голова.

Дракона просят чаще всего, а модель рисует его крестом из коробок. Здесь он
собран по-настоящему: тело идёт по гладкой кривой (Catmull-Rom) с меняющейся
толщиной, крылья натянуты на «пальцы» как перепонка, вдоль хребта гребень,
голова с челюстью, рогами и светящимися глазами. Поза — вздыбленная, на скале.

    python -m builder.preview programs/dragon.json -o dragon.png
"""

from __future__ import annotations

import math

from ..kit import Canvas

ID = "dragon"
TITLE_EN = "Dragon"
TITLE_RU = "Дракон"
ALIASES = [("дракон",), ("dragon",), ("виверн",), ("wyvern",), ("змей", "горыныч"),
           ("ender", "dragon"), ("драконь",)]
ABOUT = ("rearing dragon on a rock: curved body and tail, spread membrane wings, "
         "horned head with glowing eyes, spine crest, clawed legs")
TUNABLE = True        # цвет чешуи и размер приходят из запроса
GENERIC = True        # «замок с драконом на крыше» — работа для модели, она их совместит
MAX_WORDS = 4         # «большой чёрный дракон» ещё чертёж, длиннее — уже модель


# --- кривая ----------------------------------------------------------------

def _catmull(p0, p1, p2, p3, t: float):
    """Точка на гладкой кривой между p1 и p2. Каждая точка — (x, y, z, радиус)."""
    t2, t3 = t * t, t * t * t
    return tuple(
        0.5 * ((2 * a1) + (-a0 + a2) * t
               + (2 * a0 - 5 * a1 + 4 * a2 - a3) * t2
               + (-a0 + 3 * a1 - 3 * a2 + a3) * t3)
        for a0, a1, a2, a3 in zip(p0, p1, p2, p3))


def _spine(points: list[tuple], per_segment: int = 10) -> list[tuple]:
    """Плотная выборка по хребту: на концах точки дублируем, чтобы кривая их прошла."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(len(pts) - 3):
        for k in range(per_segment):
            out.append(_catmull(pts[i], pts[i + 1], pts[i + 2], pts[i + 3], k / per_segment))
    out.append(points[-1])
    return out


def _flesh(c: Canvas, spine: list[tuple], block: str, belly: str | None = None) -> None:
    """Мясо вокруг хребта: на каждом шаге шар нужного радиуса, низ другим блоком."""
    for x, y, z, r in spine:
        ri = max(1, int(round(r)))
        for dx in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                for dz in range(-ri, ri + 1):
                    if dx * dx + dy * dy + dz * dz <= r * r:
                        # брюхо светлее: так силуэт читается даже против неба
                        use = belly if (belly and dy < -r * 0.45) else block
                        c.set(x + dx, y + dy, z + dz, use)


# --- части ------------------------------------------------------------------

def _wing(c: Canvas, root: tuple, side: int, span: float, main: str, membrane: str) -> None:
    """Крыло: несколько «пальцев» из одной точки и перепонка между ними."""
    rx, ry, rz = root
    # (угол вверх, угол назад, длина) — от переднего края к заднему
    fingers = [(0.70, -0.10, 1.00), (0.44, 0.16, 0.97), (0.18, 0.40, 0.88),
               (-0.08, 0.60, 0.74), (-0.34, 0.74, 0.56)]
    tips = []
    for up, back, length in fingers:
        L = span * length
        tip = (rx + side * L * math.cos(up) * 0.92,
               ry + L * math.sin(up) * 0.95,
               rz + L * back)
        tips.append(tip)
        c.line((rx, ry, rz), tip, main, 1)                    # кость пальца
        c.sphere((round(tip[0]), round(tip[1]), round(tip[2])), 1, main)
        if up > 0.3:                                          # коготь на переднем пальце
            c.line(tip, (tip[0] + side * 3, tip[1] + 2, tip[2] - 1), "bone_block", 1)

    # Перепонка: веер линий от корня к краю. Шагов берём по длине края, иначе
    # соседние линии расходятся и в крыле остаются дыры.
    for a, b in zip(tips, tips[1:]):
        steps = max(12, int(math.dist(a, b) * 2.2))
        for k in range(steps + 1):
            t = k / steps
            edge = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
            sag = math.sin(math.pi * t) * span * 0.10      # край провисает между костями
            edge = (edge[0], edge[1] - sag, edge[2] + sag * 0.4)
            c.line((rx, ry, rz), edge, membrane, 1)
        # поперечная штриховка: веер один всё равно оставляет просветы у края
        for j in range(1, max(10, int(span))):
            u = j / max(10, int(span))
            pa = (rx + (a[0] - rx) * u, ry + (a[1] - ry) * u, rz + (a[2] - rz) * u)
            pb = (rx + (b[0] - rx) * u, ry + (b[1] - ry) * u, rz + (b[2] - rz) * u)
            c.line(pa, pb, membrane, 1)
    # плечевая кость потолще
    c.line((rx, ry, rz), (rx + side * span * 0.28, ry + span * 0.22, rz), main, 2)


def _leg(c: Canvas, hip: tuple, side: int, length: float, main: str, forward: float = 0.0) -> None:
    """Нога: бедро, голень, ступня и три когтя."""
    hx, hy, hz = hip
    knee = (hx + side * length * 0.42, hy - length * 0.46, hz + forward + length * 0.18)
    foot = (hx + side * length * 0.52, hy - length * 0.96, hz + forward + length * 0.04)
    c.line((hx, hy, hz), knee, main, 2)
    c.line(knee, foot, main, 2)
    c.sphere((round(knee[0]), round(knee[1]), round(knee[2])), 2, main)
    for k in (-1, 0, 1):                                      # пальцы с когтями
        toe = (foot[0] + side * 1.5 + k * 0.6, foot[1], foot[2] + 3.4 + k * 1.1)
        c.line(foot, toe, main, 1)
        c.set(round(toe[0]) + side, round(toe[1]), round(toe[2]) + 1, "bone_block")


def _head(c: Canvas, base: tuple, main: str, accent: str, size: float) -> None:
    """Голова: череп, вытянутая морда, нижняя челюсть, рога, глаза, зубы."""
    hx, hy, hz = base
    s = size
    c.sphere((hx, hy, hz), round(s), main)                                  # череп
    # морда клином вперёд
    for k in range(round(s * 2.6)):
        t = k / max(1, s * 2.6)
        r = max(1.0, s * (0.92 - 0.55 * t))
        c.sphere((hx, hy - t * s * 0.42, hz + s * 0.7 + k), round(r), main)
    snout = hz + s * 0.7 + round(s * 2.6)
    # нижняя челюсть — чуть ниже и короче, пасть приоткрыта
    for k in range(round(s * 2.1)):
        t = k / max(1, s * 2.1)
        r = max(1.0, s * (0.72 - 0.45 * t))
        c.sphere((hx, hy - s * 0.95 - t * s * 0.18, hz + s * 0.8 + k), round(r), main)
    for k in (-1, 1):                                                        # зубы
        for d in range(3):
            c.set(hx + k * round(s * 0.5), hy - s * 0.55, hz + s * 1.4 + d * 2, "bone_block")
    for k in (-1, 1):                                                        # глаза
        c.set(hx + k * round(s * 0.72), hy + s * 0.34, hz + s * 0.95, accent)
        c.set(hx + k * round(s * 0.72), hy + s * 0.34, hz + s * 0.95 + 1, accent)
        c.set(hx + k * round(s * 0.62), hy + s * 0.62, hz + s * 0.80, main)   # надбровье
    for k in (-1, 1):                                                        # рога назад
        root = (hx + k * s * 0.6, hy + s * 0.78, hz - s * 0.1)
        mid = (hx + k * s * 1.25, hy + s * 1.7, hz - s * 1.5)
        tip = (hx + k * s * 1.5, hy + s * 2.5, hz - s * 3.2)
        c.line(root, mid, "bone_block", 2)
        c.line(mid, tip, "bone_block", 1)
        c.line((hx + k * s * 0.5, hy + s * 0.2, hz - s * 0.6),               # малый рог у щеки
               (hx + k * s * 1.1, hy + s * 0.5, hz - s * 1.8), "bone_block", 1)
    c.set(hx, round(hy + s * 0.9), round(hz - s * 0.2), accent)              # гребень на лбу


def build(main: str = "black_concrete", accent: str = "purple_concrete",
          scale: float = 1.0) -> dict:
    """Дракон целиком. main — чешуя, accent — глаза и перепонка."""
    c = Canvas()
    S = max(0.75, scale)
    membrane = {"black_concrete": "purple_concrete"}.get(main, accent)
    belly = {"black_concrete": "gray_concrete"}.get(main, "light_gray_concrete")

    # Хребет: (x, y, z, радиус). Хвост слева внизу, тело в центре, шея вверх.
    k = S
    nodes = [
        (0,  12 * k,  0,           1.0 * k),   # кончик хвоста
        (2 * k,  13 * k, 10 * k,  1.8 * k),
        (1 * k,  15 * k, 22 * k,  2.8 * k),
        (0,  18 * k, 33 * k,      4.0 * k),   # бёдра
        (0,  21 * k, 44 * k,      5.4 * k),   # грудная клетка
        (0,  23 * k, 54 * k,      5.0 * k),   # плечи
        (0,  27 * k, 61 * k,      3.6 * k),   # шея пошла вверх
        (0,  34 * k, 65 * k,      3.0 * k),
        (0,  41 * k, 66 * k,      2.7 * k),
        (0,  46 * k, 70 * k,      2.6 * k),   # затылок
    ]
    offset = round(26 * k)                      # сдвиг по x, чтобы крылья влезли
    spine = [(x + offset, y, z, r) for x, y, z, r in _spine(nodes)]

    # Скала под лапами: не блин, а валун с рваным краем — дракону нужен постамент,
    # иначе он висит в воздухе непонятно на чём.
    for x in range(2 * offset + 1):
        for z in range(round(66 * k)):
            d = math.hypot((x - offset) / 1.15, (z - 36 * k) / 1.45)
            edge = 20 * k + 2.2 * math.sin(x * 0.7) + 2.2 * math.cos(z * 0.55)
            if d < edge:
                h = max(1, round((10 * k) * math.sqrt(max(0.0, 1 - (d / edge) ** 2))))
                for y in range(0, h + 1):
                    if y == h:
                        c.set(x, y, z, "stone" if (x + z) % 7 else "mossy_cobblestone")
                    else:
                        c.set(x, y, z, "andesite" if (x * 3 + z) % 5 else "cobblestone")

    _flesh(c, spine, main, belly)

    # гребень вдоль всего хребта
    for i, (x, y, z, r) in enumerate(spine):
        if i % 3:
            continue
        t = i / len(spine)
        h = max(1, round((1.2 + 2.6 * math.sin(math.pi * min(1.0, t * 1.15))) * k))
        c.line((x, y + r, z), (x, y + r + h, z), "bone_block", 1)

    shoulder = spine[int(len(spine) * 0.56)]
    hip = spine[int(len(spine) * 0.33)]
    for side in (1, -1):
        _wing(c, (shoulder[0] + side * shoulder[3] * 0.8, shoulder[1] + shoulder[3] * 0.7,
                  shoulder[2]), side, 34 * k, main, membrane)
        _leg(c, (shoulder[0] + side * shoulder[3], shoulder[1] - shoulder[3] * 0.5,
                 shoulder[2] + 2 * k), side, 15 * k, main, forward=2 * k)
        _leg(c, (hip[0] + side * hip[3], hip[1] - hip[3] * 0.3, hip[2]),
             side, 19 * k, main)

    head = spine[-1]
    _head(c, (head[0], head[1] + 1.5 * k, head[2]), main, accent, 3.2 * k)

    # шипы на хвосте
    for i in range(6, 26, 4):
        x, y, z, r = spine[i]
        for side in (1, -1):
            c.line((x, y, z), (x + side * (r + 2 * k), y - 1, z - 2 * k), "bone_block", 1)
    return c.v
