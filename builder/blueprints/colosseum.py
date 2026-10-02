"""Колизей: эллиптическое кольцо из трёх ярусов арок и аттика, ступенчатые трибуны,
арена с песком и обрушенный участок внешней стены, как у настоящего."""

from __future__ import annotations

import math

from .kit import Canvas

A, B, T, TH, ATTIC = 30, 24, 3, 7, 6
NARCH = 40
H = 3 * TH + ATTIC


def build() -> dict:
    c = Canvas()
    aa, ab = 14, 8                                        # арена
    for x in range(-A - 2, A + 3):
        for z in range(-B - 2, B + 3):
            e_out = (x / A) ** 2 + (z / B) ** 2
            e_in = (x / (A - T)) ** 2 + (z / (B - T)) ** 2
            e_ar = (x / aa) ** 2 + (z / ab) ** 2
            th = math.atan2(z / B, x / A)
            f = (th / (2 * math.pi) * NARCH) % 1.0
            if e_out > 1.0 and e_out <= 1.15:
                c.set(x, 0, z, "coarse_dirt")
            if e_out > 1.15:
                continue
            c.set(x, 0, z, "sand" if e_ar <= 1 else "stone_bricks")
            if e_ar <= 1:
                continue
            if e_in <= 1:                                  # трибуны: ступени растут от арены к стене
                s = math.sqrt(e_in); sa = 1.0
                k = (math.sqrt(e_ar) - 1) / ((A - T) / aa - 1) if (A - T) / aa > 1 else 0
                h = 1 + 2 * round((k * 18) / 2)
                for y in range(1, h + 1):
                    c.set(x, y, z, "cut_sandstone" if y == h else "stone_bricks")
                continue
            if e_out > 1.0:
                continue
            # внешняя стена с арками; на участке th в (1.9..3.1) стена обрушена
            broken = 1.9 < th < 3.1
            cap = H
            if broken:
                mid = 1 - abs((th - 2.5) / 0.6)
                cap = round(TH + 3 + (H - TH - 3) * (1 - mid)) - ((x * 31 + z * 17) % 4)
            for y in range(1, min(H, cap) + 1):
                tier = (y - 1) // TH
                ly = (y - 1) % TH
                if tier >= 3:
                    block = "cut_sandstone"
                    if 0.35 < f < 0.65 and ly in (2, 3):
                        continue
                elif ly == TH - 1:
                    block = "smooth_sandstone"
                else:
                    block = "sandstone" if tier != 1 else "cut_sandstone"
                    if 0.2 < f < 0.8 and 1 <= ly <= 4 and not (ly == 4 and not 0.32 < f < 0.68):
                        continue
                c.set(x, y, z, block)
    return c.v
