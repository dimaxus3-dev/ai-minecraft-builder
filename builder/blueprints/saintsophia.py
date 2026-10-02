"""Софийский собор (Киев): белые стены, зелёные кровли, тринадцать куполов с золотыми главами,
апсиды с востока и отдельная колокольня."""

from __future__ import annotations

from .kit import Canvas

WALL, GREEN, GOLD = "white_concrete", "weathered_copper", "gold_block"


def drum_dome(c, x, y, z, rd, hd, rdome, hdome, dome_block):
    c.cyl((x, y, z), rd, hd, WALL, hollow=True)
    for dx, dz in ((rd, 0), (-rd, 0), (0, rd), (0, -rd)):
        c.set(x + dx, y + 1, z + dz, "glass"); c.set(x + dx, y + 2, z + dz, "glass")
    c.dome((x, y + hd, z), rdome, dome_block, h=hdome)
    top = y + hd + hdome
    c.line((x, top, z), (x, top + 3, z), GOLD, 1); c.set(x - 1, top + 2, z, GOLD); c.set(x + 1, top + 2, z, GOLD)


def build() -> dict:
    c = Canvas()
    X0, Z0, L, Wd = 12, 8, 34, 26
    cx, cz = X0 + L // 2, Z0 + Wd // 2
    c.box((0, 0, 0), (66, 0, 56), "light_gray_concrete")
    c.box((0, 0, 0), (66, 0, 3), "moss_block"); c.box((0, 0, 53), (66, 0, 56), "moss_block")
    # главный объём и боковые нефы
    c.hollow((X0, 1, Z0), (X0 + L, 15, Z0 + Wd), WALL, 1)
    c.box((X0 - 1, 15, Z0 - 1), (X0 + L + 1, 15, Z0 + Wd + 1), "smooth_quartz")
    for z0, z1 in ((Z0 - 8, Z0 - 1), (Z0 + Wd + 1, Z0 + Wd + 8)):
        c.hollow((X0 + 2, 1, z0), (X0 + L - 2, 9, z1), WALL, 1)
        c.roof((X0 + 1, 10, z0 - 1), (X0 + L - 1, 10, z1 + 1), GREEN, "gable", h=3, axis="x")
    c.roof((X0 - 1, 16, Z0 - 1), (X0 + L + 1, 16, Z0 + Wd + 1), GREEN, "pyramid", h=5)
    # окна по фасадам
    for x in range(X0 + 3, X0 + L - 2, 4):
        for z in (Z0, Z0 + Wd):
            c.box((x, 6, z), (x + 1, 11, z), "light_blue_stained_glass")
    # три апсиды на востоке
    for dz, r, h in ((0, 5, 13), (-9, 3, 10), (9, 3, 10)):
        c.cyl((X0 + L + 2, 1, cz + dz), r, h, WALL, hollow=False)
        c.dome((X0 + L + 2, 1 + h, cz + dz), r, GREEN if r == 3 else GOLD, h=r + 2)
    # центральный купол и четыре боковых главы
    drum_dome(c, cx, 17, cz, 7, 8, 8, 10, GOLD)
    for dx, dz in ((-12, -8), (12, -8), (-12, 8), (12, 8)):
        drum_dome(c, cx + dx, 17, cz + dz, 3, 5, 4, 5, GOLD)
    # малые зелёные купола на боковых нефах
    for x in (cx - 12, cx - 4, cx + 4, cx + 12):
        for z in (Z0 - 5, Z0 + Wd + 5):
            drum_dome(c, x, 10, z, 2, 3, 2, 3, GREEN)
    # колокольня
    bx, bz = X0 - 8, Z0 + Wd + 14
    for i, (h, r) in enumerate(((14, 5), (9, 4), (7, 3))):
        y0 = 1 + sum(t[0] for t in ((14, 5), (9, 4), (7, 3))[:i])
        c.hollow((bx - r, y0, bz - r), (bx + r, y0 + h - 1, bz + r), "yellow_concrete" if i == 0 else WALL, 1)
        c.box((bx - r - 1, y0 + h - 1, bz - r - 1), (bx + r + 1, y0 + h - 1, bz + r + 1), "smooth_quartz")
        if i:
            for s in (-1, 1):
                c.carve((bx + s * r, y0 + 2, bz - 1), (bx + s * r, y0 + 5, bz + 1)); c.carve((bx - 1, y0 + 2, bz + s * r), (bx + 1, y0 + 5, bz + s * r))
    drum_dome(c, bx, 31, bz, 2, 2, 3, 6, GOLD)
    return c.v
