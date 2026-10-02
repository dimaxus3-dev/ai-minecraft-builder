"""Мост Золотые Ворота: две башни с порталами, главный пролёт с параболическими тросами,
подвески, боковые пролёты, ферма под полотном, море и два мыса по берегам.

Без берегов мост висел в пустой воде и не читался: настоящий Golden Gate узнают
по тому, что он соединяет два холма над проливом."""

from __future__ import annotations

import math

from .kit import Canvas

SPAN = 68               # главный пролёт между башнями
SIDE = 30               # боковой пролёт с каждой стороны
DECK = 12               # высота полотна над морем
TOP = 46                # высота верха башен над морем
HW = 6                  # половина ширины полотна
LAND = 20               # длина мыса за каждым концом моста
OR = "orange_concrete"
DARK = "red_concrete"


def build() -> dict:
    c = Canvas()
    half = SPAN // 2
    L = half + SIDE                       # конец моста по x (от центра)
    cz = 0

    # море: плитки двух оттенков, чтобы не было плоской заливки
    for x in range(-L - LAND - 2, L + LAND + 3):
        for z in range(-24, 25):
            c.set(x, 0, z, "blue_concrete" if (x * 7 + z * 13) % 11 else "light_blue_concrete")

    # Мысы: холмы со скальным обрывом к воде. Дорога идёт по ним в выемке,
    # поэтому полотно продолжается, а не обрывается в пустоту.
    for sign in (-1, 1):
        for i in range(LAND + 1):
            x = sign * (L + i)
            t = i / LAND
            crest = DECK + round(16 * t)                   # холм поднимается от моста
            for z in range(-24, 25):
                shore = 21 - abs(z) * 0.25
                if abs(z) > shore:
                    continue
                # склон косинусом, а не прямой: иначе мыс выходит столовой горой
                fall = min(1.0, max(0.0, (abs(z) - 7) / max(1.0, shore - 7)))
                h = round(crest * (0.5 + 0.5 * math.cos(math.pi * fall)))
                h += round(1.6 * math.sin(x * 0.6) + 1.6 * math.cos(z * 0.45))   # неровность
                if h < 1:
                    continue
                for y in range(0, h + 1):
                    if y == h:
                        c.set(x, y, z, "grass_block" if h > DECK - 2 else "sand")
                    elif y > h - 3:
                        c.set(x, y, z, "dirt" if h > DECK - 2 else "sand")
                    else:
                        c.set(x, y, z, "stone" if (x * 3 + y + z) % 6 else "andesite")
            # выемка под дорогу
            c.box((x, DECK + 1, -HW), (x, DECK + 6, HW), "air")
            c.box((x, DECK, -HW), (x, DECK, HW), "gray_concrete")
            if x % 4 in (0, 1):
                c.set(x, DECK, 0, "yellow_concrete")
            for z in (-HW, HW):                            # откосы выемки
                c.set(x, DECK + 1, z, "stone_bricks")
            # деревья по гребню
            if i > 4 and i % 5 == 0:
                for z in (-15, 16):
                    fall = min(1.0, max(0.0, (abs(z) - 7) / max(1.0, 21 - abs(z) * 0.25 - 7)))
                    base_h = round(crest * (0.5 + 0.5 * math.cos(math.pi * fall)))
                    base_h += round(1.6 * math.sin(x * 0.6) + 1.6 * math.cos(z * 0.45))
                    c.line((x, base_h, z), (x, base_h + 5, z), "spruce_log", 1)
                    c.sphere((x, base_h + 7, z), 3, "spruce_leaves")

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
            # ар-деко: уступы с тенью, по ним башню и узнают
            for k, y in enumerate(range(DECK + 12, TOP - 5, 7)):
                c.box((tx - 1, y, z - 1), (tx + 1, y, z + 1), DARK)
                c.box((tx - 1, y + 1, z - 1), (tx + 1, y + 1, z + 1), OR)
            c.box((tx - 1, TOP - 5, z - 1), (tx, TOP, z), DARK)                # навершие
            c.box((tx - 2, TOP - 5, z - 2), (tx + 1, TOP - 5, z + 1), DARK)    # карниз
            c.set(tx, TOP + 1, z, "red_concrete")                              # огонь на вершине
            c.set(tx, TOP + 2, z, "glowstone")
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
