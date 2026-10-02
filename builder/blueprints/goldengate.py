"""Мост Золотые Ворота: две башни с порталами, главный пролёт с параболическими тросами,
подвески, боковые пролёты, ферма под полотном, море."""

from __future__ import annotations

from .kit import Canvas

SPAN = 68               # главный пролёт между башнями
SIDE = 30               # боковой пролёт с каждой стороны
DECK = 12               # высота полотна над морем
TOP = 46                # высота верха башен над морем
HW = 6                  # половина ширины полотна
OR = "orange_concrete"
DARK = "red_concrete"


def build() -> dict:
    c = Canvas()
    half = SPAN // 2
    L = half + SIDE                       # конец моста по x (от центра)
    cz = 0

    # море: плитки двух оттенков, чтобы не было плоской заливки
    for x in range(-L - 4, L + 5):
        for z in range(-20, 21):
            c.set(x, 0, z, "blue_concrete" if (x * 7 + z * 13) % 11 else "light_blue_concrete")

    # полотно дороги, разметка, ограждение, фонари
    for x in range(-L, L + 1):
        c.box((x, DECK, -HW), (x, DECK, HW), "gray_concrete")
        if x % 4 in (0, 1):
            c.set(x, DECK, 0, "yellow_concrete")
        c.set(x, DECK, -HW + 1, "white_concrete"); c.set(x, DECK, HW - 1, "white_concrete")
        c.set(x, DECK + 1, -HW, OR); c.set(x, DECK + 1, HW, OR)
        if x % 8 == 0 and abs(x) != half:
            c.set(x, DECK + 2, -HW, "sea_lantern"); c.set(x, DECK + 2, HW, "sea_lantern")
    # ферма под полотном вдоль обоих краёв
    for z in (-HW, HW):
        for x in range(-L, L, 4):
            c.line((x, DECK - 1, z), (x + 4, DECK - 1, z), OR, 1)
            c.line((x, DECK - 1, z), (x + 2, DECK - 4, z), OR, 1)
            c.line((x + 2, DECK - 4, z), (x + 4, DECK - 1, z), OR, 1)
        c.line((-L, DECK - 4, z), (L, DECK - 4, z), OR, 1)
    # поперечные балки под полотном
    for x in range(-L, L + 1, 4):
        c.line((x, DECK - 1, -HW), (x, DECK - 1, HW), "gray_concrete", 1)

    # башни: две ноги, порталы-перемычки, ступенчатая вершина
    for tx in (-half, half):
        for z in (-HW, HW):
            c.box((tx - 1, 0, z - 1), (tx + 1, DECK + 8, z + 1), OR)          # нижняя часть шире
            c.box((tx - 1, DECK + 8, z - 1), (tx, TOP - 5, z), OR)
            c.box((tx - 1, TOP - 5, z - 1), (tx, TOP, z), DARK)                # навершие
        for y in (DECK + 8, DECK + 17, DECK + 26, TOP - 3):
            c.box((tx - 1, y, -HW + 2), (tx, y + 1, HW - 2), OR)              # поперечная балка
        for y in (DECK + 8, DECK + 17, DECK + 26):                            # кресты между балками
            c.line((tx, y + 1, -HW + 1), (tx, y + 8, HW - 1), OR, 1)
            c.line((tx, y + 1, HW - 1), (tx, y + 8, -HW + 1), OR, 1)

    # тросы: параболы главного пролёта и пологие боковые
    def cable_main(x):
        return DECK + 3 + (TOP - 1 - (DECK + 3)) * (x / half) ** 2

    def cable_side(x, sign):
        t = (abs(x) - half) / SIDE                  # 0 у башни, 1 у конца
        return TOP - 1 - (TOP - 1 - (DECK + 3)) * (t ** 1.4)

    for z in (-HW, HW):
        pts = [(x, cable_main(x), z) for x in range(-half, half + 1, 2)]
        c.poly([(a, round(b), cc) for a, b, cc in pts], OR, 2)
        for s in (-1, 1):
            side = [(s * (half + i * 2), round(cable_side(s * (half + i * 2), s)), z)
                    for i in range(SIDE // 2 + 1)]
            c.poly(side, OR, 2)
        # подвески
        for x in range(-half + 3, half - 2, 3):
            c.line((x, DECK + 2, z), (x, round(cable_main(x)), z), OR, 1)
        for s in (-1, 1):
            for i in range(2, SIDE, 3):
                x = s * (half + i)
                c.line((x, DECK + 2, z), (x, round(cable_side(x, s)), z), OR, 1)
    # пилоны по берегам (опоры концов)
    for s in (-1, 1):
        for z in (-HW, HW):
            c.box((s * L - 1, 0, z - 1), (s * L + 1, DECK, z + 1), "gray_concrete")
    return c.v
