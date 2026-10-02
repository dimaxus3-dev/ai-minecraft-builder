"""Инструменты для чертежей-генераторов: холст, на котором рисуют теми же примитивами,
но с кодом вокруг (кривые, фермы, повторы). Результат — словарь {(x, y, z): блок}."""

from __future__ import annotations

import math

from .. import primitives as P


class Canvas:
    def __init__(self) -> None:
        self.v: dict[tuple[int, int, int], str] = {}

    def put(self, cells, block: str) -> "Canvas":
        for c in cells:
            self.v[(int(c[0]), int(c[1]), int(c[2]))] = block
        return self

    def set(self, x, y, z, block): self.v[(round(x), round(y), round(z))] = block; return self
    def box(self, a, b, block): return self.put(P.box(_i(a), _i(b)), block)
    def hollow(self, a, b, block, t=1): return self.put(P.hollow_box(_i(a), _i(b), t), block)
    def line(self, a, b, block, t=1): return self.put(P.line(_i(a), _i(b), t), block)
    def cyl(self, c, r, h, block, hollow=False): return self.put(P.cylinder(_i(c), r, h, hollow), block)
    def sphere(self, c, r, block, hollow=False): return self.put(P.sphere(_i(c), r, hollow), block)
    def dome(self, c, r, block, h=None, hollow=False): return self.put(P.dome(_i(c), r, h, hollow), block)
    def cone(self, c, r, h, block, hollow=False): return self.put(P.cone(_i(c), r, h, hollow), block)
    def arch(self, a, b, h, block, t=1): return self.put(P.arch(_i(a), _i(b), h, t), block)
    def roof(self, a, b, block, style="gable", h=None, axis=None):
        return self.put(P.roof(_i(a), _i(b), style, h, axis), block)

    def poly(self, pts, block, t=1):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b, block, t)
        return self

    def carve(self, a, b): return self.box(a, b, "air")


def _i(p):
    return (round(p[0]), round(p[1]), round(p[2]))


def normalize(v: dict) -> dict:
    """Сдвигает чертёж так, чтобы минимум был в нуле; воздух вне габаритов выкидываем."""
    live = [p for p, b in v.items() if b != "air"]
    mx, my, mz = (min(p[i] for p in live) for i in range(3))
    return {(x - mx, y - my, z - mz): b for (x, y, z), b in v.items()
            if x >= mx and y >= my and z >= mz}
