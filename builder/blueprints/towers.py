"""Семейство башен: один генератор, десятки узнаваемых силуэтов.

Небоскрёбы отличаются немногим: формой сечения, сужением, уступами, закруткой,
навершием и шпилем. Поэтому вместо полусотни почти одинаковых файлов — один
генератор с параметрами, а каждая башня в реестре задаёт свой набор. Так
Salesforce Tower, Empire State и Shanghai Tower выходят разными по-настоящему,
а не перекрашенной копией.

    python -m builder.preview  # картинка по чертежу
"""

from __future__ import annotations

import math

from .kit import Canvas

CROWNS = ("flat", "pyramid", "dome", "chisel", "slant", "arch", "saucer", "lattice")


def _section(shape: str, r: float, angle: float) -> list[tuple[int, int]]:
    """Точки сечения на высоте: квадрат, круг, восьмиугольник или треугольник,
    повёрнутые на angle. Возвращаем целые смещения (dx, dz)."""
    pts: set[tuple[int, int]] = set()
    ri = max(1, int(round(r)))
    if shape == "round":
        for x in range(-ri, ri + 1):
            for z in range(-ri, ri + 1):
                if x * x + z * z <= r * r:
                    pts.add((x, z))
        return sorted(pts)
    sides = {"square": 4, "octagon": 8, "triangle": 3, "hexagon": 6}.get(shape, 4)
    corners = [(r * math.cos(math.radians(angle + k * 360 / sides + 45 * (sides == 4))),
                r * math.sin(math.radians(angle + k * 360 / sides + 45 * (sides == 4))))
               for k in range(sides)]
    # заливка выпуклого многоугольника по полуплоскостям
    for x in range(-ri - 1, ri + 2):
        for z in range(-ri - 1, ri + 2):
            inside = True
            for (ax, az), (bx, bz) in zip(corners, corners[1:] + corners[:1]):
                if (bx - ax) * (z - az) - (bz - az) * (x - ax) < -0.5:
                    inside = False
                    break
            if inside:
                pts.add((x, z))
    return sorted(pts)


def _radius_at(t: float, base: float, taper: float, setbacks: int, barrel: float) -> float:
    """Радиус на доле высоты t: сужение, уступы и бочка (Gherkin)."""
    r = base * (1 - taper * t)
    if setbacks:
        step = math.floor(t * setbacks) / setbacks
        r = base * (1 - taper * step) * (1 - 0.06 * math.floor(t * setbacks))
    if barrel:
        r *= 1 + barrel * math.sin(math.pi * t) - barrel * 0.35
    return max(1.5, r)


def tower(main: str = "light_gray_concrete", accent: str = "light_blue_stained_glass",
          scale: float = 1.0, height: int = 90, base: float = 9.0, taper: float = 0.45,
          shape: str = "square", twist: float = 0.0, setbacks: int = 0,
          crown: str = "flat", spire: int = 0, bands: int = 0, twin: int = 0,
          pod: float = 0.0, barrel: float = 0.0, podium: int = 1) -> dict:
    """Одна башня по описанию силуэта. Все размеры множатся на scale."""
    c = Canvas()
    H = max(24, round(height * scale))
    B = max(3.0, base * scale)
    half = round(B + 10)
    cx = cz = half
    offsets = [0] if not twin else [-round(B + 3), round(B + 3)]
    span = half + (abs(offsets[0]) if twin else 0)
    cx = cz = span + 6

    # стилобат
    if podium:
        c.box((cx - round(B) - 6 - (abs(offsets[0]) if twin else 0), 0, cz - round(B) - 6),
              (cx + round(B) + 6 + (abs(offsets[0]) if twin else 0), 0, cz + round(B) + 6),
              "smooth_stone")
        for ox in offsets:
            for y in range(1, 3):
                for dx, dz in _section(shape, B + 3, 0):
                    c.set(cx + ox + dx, y, cz + dz, main)

    for ox in offsets:
        top = H
        for y in range(3, H):
            t = (y - 3) / max(1, H - 3)
            r = _radius_at(t, B, taper, setbacks, barrel)
            angle = twist * t
            ring = _section(shape, r, angle)
            # остекление полосами: каждый третий этаж — лента окон
            glassy = accent if (y % 3 == 1 and 0.04 < t < 0.97) else main
            if bands and round(t * bands) != round((t - 1 / max(1, H)) * bands):
                glassy = accent
            edge = {(dx, dz) for dx, dz in ring
                    if (dx + 1, dz) not in set(ring) or (dx - 1, dz) not in set(ring)
                    or (dx, dz + 1) not in set(ring) or (dx, dz - 1) not in set(ring)}
            for dx, dz in ring:
                if (dx, dz) in edge or y % 8 == 3:        # оболочка плюс редкие плиты
                    c.set(cx + ox + dx, y, cz + dz, glassy if (dx, dz) in edge else main)

            if pod and abs(t - pod) < 0.012:              # смотровая «шайба»
                for dx, dz in _section("round", r + 5, 0):
                    for yy in range(y, y + 4):
                        c.set(cx + ox + dx, yy, cz + dz, main if yy != y + 1 else accent)

        # навершие
        r_top = _radius_at(1.0, B, taper, setbacks, barrel)
        a_top = twist
        if crown == "pyramid":
            for k in range(round(r_top) + 1):
                for dx, dz in _section(shape, r_top - k, a_top):
                    c.set(cx + ox + dx, top + k, cz + dz, main)
        elif crown == "dome":
            c.dome((cx + ox, top, cz), round(r_top), accent)
        elif crown == "chisel":                            # срез как у Transamerica
            for k in range(round(r_top * 2)):
                for dx, dz in _section(shape, max(1, r_top - k * 0.5), a_top):
                    c.set(cx + ox + dx, top + k, cz + dz, main)
        elif crown == "slant":                             # косой срез
            for k in range(round(r_top * 1.6)):
                for dx, dz in _section(shape, r_top, a_top):
                    if dz < r_top - k * 1.2:
                        c.set(cx + ox + dx, top + k, cz + dz, main)
        elif crown == "arch":                              # «веер» Chrysler
            for k in range(round(r_top * 2.2)):
                rr = r_top * math.sqrt(max(0.0, 1 - (k / (r_top * 2.2)) ** 2))
                for dx, dz in _section("round", max(1, rr), 0):
                    c.set(cx + ox + dx, top + k, cz + dz, accent if k % 2 else main)
        elif crown == "saucer":                            # «тарелка» Space Needle
            for k, rr in ((0, r_top + 6), (1, r_top + 8), (2, r_top + 8), (3, r_top + 5)):
                for dx, dz in _section("round", rr, 0):
                    c.set(cx + ox + dx, top + k, cz + dz, accent if k == 1 else main)
        elif crown == "lattice":                           # решётчатая макушка
            for k in range(round(r_top * 3)):
                rr = max(1, r_top - k * 0.4)
                for dx, dz in _section(shape, rr, a_top):
                    if abs(dx) > rr - 1.6 or abs(dz) > rr - 1.6:
                        c.set(cx + ox + dx, top + k, cz + dz, main)

        if spire:
            base_y = top + {"flat": 0, "pyramid": round(r_top), "dome": round(r_top),
                            "chisel": round(r_top * 2), "slant": round(r_top * 1.6),
                            "arch": round(r_top * 2.2), "saucer": 4,
                            "lattice": round(r_top * 3)}.get(crown, 0)
            sp = max(4, round(spire * scale))
            for k in range(sp):
                rr = 2 if k < sp * 0.35 else 1
                for dx, dz in _section("round", rr, 0):
                    c.set(cx + ox + dx, base_y + k, cz + dz, main)
            c.set(cx + ox, base_y + sp, cz, "glowstone")

    if twin:                                               # переход между башнями
        y = round(H * 0.55)
        for yy in (y, y + 1, y + 2):
            c.box((cx + offsets[0], yy, cz - 2), (cx + offsets[1], yy, cz + 2),
                  accent if yy == y + 1 else main)
    return c.v
