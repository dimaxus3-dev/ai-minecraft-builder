"""Предпросмотр чертежа без Minecraft: изометрия + вид спереди и сбоку в PNG.

Нужен, чтобы оценивать здание глазами, не запуская игру:
    python -m builder.preview programs/lighthouse.json -o /tmp/lighthouse.png
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

from .build import load_program, render

# цвета по названию блока: сначала точные куски имени, потом цвет-префикс
SPECIFIC = [
    ("sandstone", (215, 200, 150)), ("leaves", (60, 130, 50)), ("moss", (95, 140, 50)),
    ("smooth_stone", (160, 160, 160)),
    ("stone_bricks", (125, 125, 125)), ("cobblestone", (110, 110, 110)), ("stone", (125, 125, 125)),
    ("nether_bricks", (55, 28, 32)), ("bricks", (150, 82, 66)), ("sandstone", (215, 200, 150)),
    ("dark_oak", (70, 50, 30)), ("spruce", (110, 80, 50)), ("birch", (205, 190, 130)),
    ("jungle", (160, 115, 80)), ("acacia", (175, 95, 55)), ("cherry", (225, 170, 175)),
    ("oak", (170, 135, 80)), ("bamboo", (200, 190, 80)), ("leaves", (60, 130, 50)),
    ("quartz", (236, 230, 225)), ("gold", (250, 215, 60)), ("iron", (215, 215, 215)),
    ("diamond", (90, 220, 210)), ("emerald", (60, 200, 90)), ("lapis", (40, 70, 160)),
    ("netherite", (60, 55, 60)), ("oxidized", (80, 170, 140)), ("weathered", (100, 160, 130)),
    ("copper", (190, 110, 75)), ("glowstone", (250, 220, 130)), ("sea_lantern", (180, 220, 210)),
    ("lava", (240, 120, 20)), ("water", (60, 90, 200)), ("dirt", (120, 85, 55)),
    ("grass", (95, 150, 60)), ("sand", (220, 205, 150)), ("snow", (245, 245, 250)),
    ("ice", (150, 190, 240)), ("obsidian", (25, 15, 40)), ("deepslate", (70, 70, 75)),
    ("blackstone", (40, 35, 40)), ("prismarine", (100, 170, 150)), ("purpur", (165, 115, 165)),
    ("netherrack", (110, 40, 40)), ("calcite", (225, 225, 220)), ("tuff", (110, 110, 100)),
    ("andesite", (135, 135, 135)), ("diorite", (190, 190, 190)), ("granite", (160, 110, 90)),
    ("bone", (230, 225, 200)), ("hay", (200, 170, 40)), ("terracotta", (155, 95, 70)),
]
COLORS = [
    ("light_blue", (100, 170, 225)), ("light_gray", (160, 160, 160)), ("white", (235, 235, 235)),
    ("gray", (90, 90, 95)), ("black", (25, 25, 30)), ("brown", (110, 75, 45)), ("red", (170, 40, 40)),
    ("orange", (225, 120, 30)), ("yellow", (240, 210, 60)), ("lime", (130, 200, 40)),
    ("green", (70, 110, 40)), ("cyan", (40, 140, 150)), ("blue", (50, 70, 170)),
    ("purple", (120, 50, 160)), ("magenta", (190, 70, 180)), ("pink", (235, 140, 170)),
]


def color_for(block: str) -> tuple[int, int, int]:
    name = block.lower()
    base = None
    for key, rgb in COLORS:                         # «red_concrete», «white_wool»…
        if name.startswith(key + "_"):
            base = rgb
            break
    if base is None:
        for key, rgb in SPECIFIC:
            if key in name:
                base = rgb
                break
    base = base or (140, 140, 140)
    if "glass" in name:                             # стекло — светлое и бледное
        base = tuple(int(c * 0.5 + 125) for c in base)
    return base


def _shade(rgb, k):
    return tuple(max(0, min(255, int(c * k))) for c in rgb)


def isometric(voxels: dict, max_px: int = 1100) -> Image.Image:
    """Изометрия, камера смотрит с +x, +y, +z. Рисуем дальние кубы раньше ближних."""
    xs = [p[0] for p in voxels]; ys = [p[1] for p in voxels]; zs = [p[2] for p in voxels]
    x0, y0, z0 = min(xs), min(ys), min(zs)
    w, h, d = max(xs) - x0 + 1, max(ys) - y0 + 1, max(zs) - z0 + 1
    c, hh = math.cos(math.radians(30)), 0.5
    width_u, height_u = (w + d) * c, (w + d) * hh + h
    s = max(1.0, min(10.0, max_px / max(width_u, height_u)))
    pad = 12
    img = Image.new("RGB", (int(width_u * s) + 2 * pad, int(height_u * s) + 2 * pad), (214, 232, 247))
    dr = ImageDraw.Draw(img)
    ox, oy = d * c * s + pad, h * s + pad

    def P(x, y, z):
        return (ox + ((x - x0) - (z - z0)) * c * s, oy + ((x - x0) + (z - z0)) * hh * s - (y - y0) * s)

    for (x, y, z), block in sorted(voxels.items(), key=lambda kv: kv[0][0] + kv[0][1] + kv[0][2]):
        rgb = color_for(block)
        if (x, y + 1, z) not in voxels:
            dr.polygon([P(x, y + 1, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)], fill=rgb)
        if (x, y, z + 1) not in voxels:
            dr.polygon([P(x, y, z + 1), P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)], fill=_shade(rgb, 0.78))
        if (x + 1, y, z) not in voxels:
            dr.polygon([P(x + 1, y, z), P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x + 1, y + 1, z)], fill=_shade(rgb, 0.58))
    return img


def elevation(voxels: dict, side: bool = False, max_px: int = 520) -> Image.Image:
    """Вид спереди (по z) или сбоку (по x): берём ближайший к зрителю блок."""
    a = 2 if side else 0                                  # горизонтальная ось
    b = 0 if side else 2                                  # глубина
    hs = [p[a] for p in voxels]; ys = [p[1] for p in voxels]
    h0, y0 = min(hs), min(ys)
    W, H = max(hs) - h0 + 1, max(ys) - y0 + 1
    s = max(1, min(12, max_px // max(W, H)))
    img = Image.new("RGB", (W * s, H * s), (214, 232, 247))
    dr = ImageDraw.Draw(img)
    nearest: dict = {}
    for p, block in voxels.items():
        key = (p[a], p[1])
        if key not in nearest or p[b] > nearest[key][0]:
            nearest[key] = (p[b], block)
    for (hx, y), (_, block) in nearest.items():
        px, py = (hx - h0) * s, (H - 1 - (y - y0)) * s
        dr.rectangle([px, py, px + s - 1, py + s - 1], fill=color_for(block))
    return img


def preview(voxels: dict, out: str | Path) -> Path:
    iso, front, side = isometric(voxels), elevation(voxels), elevation(voxels, side=True)
    row_h = max(front.height, side.height)
    canvas = Image.new("RGB", (max(iso.width, front.width + side.width + 24),
                               iso.height + row_h + 24), (255, 255, 255))
    canvas.paste(iso, (0, 0))
    canvas.paste(front, (0, iso.height + 12))
    canvas.paste(side, (front.width + 24, iso.height + 12))
    out = Path(out)
    canvas.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="PNG-предпросмотр чертежа без Minecraft")
    ap.add_argument("program"); ap.add_argument("-o", "--out", default="preview.png")
    args = ap.parse_args()
    prog = load_program(args.program)
    vox = {p: b for p, b in render(prog, (0, 0, 0)).items() if b != "air"}
    print(f"{prog.name}: {len(vox)} блоков, габариты {list(prog.real_size())} -> {preview(vox, args.out)}")


if __name__ == "__main__":
    main()
