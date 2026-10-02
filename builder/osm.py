"""Здание из реальных данных OpenStreetMap: название -> геокодер Nominatim -> контуры, высоты и формы
крыш из Overpass -> воксели. Работает для любого здания, которое есть на карте (любая страна).

    python -m builder.osm "Burj Khalifa" -o /tmp/burj.png

Это только массив здания (контур, этажность, крыша, цвет), без орнамента: для главных достопримечательностей
чертёж в builder/blueprints лучше, а карта закрывает всё остальное.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

UA = {"User-Agent": "ai-minecraft-builder/1.0 (hackathon project; https://github.com/dimaxus3-dev/ai-minecraft-builder)"}
OVERPASS = ["https://overpass.openstreetmap.fr/api/interpreter", "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]
CACHE_DIR = Path(os.getenv("OSM_CACHE", "data/osm_cache"))
OK_CATEGORIES = {"building", "tourism", "historic", "man_made", "amenity", "leisure", "office", "shop"}
TARGET = 80                  # во сколько блоков вписываем длинную сторону
FLOOR_M = 3.2                # метров на этаж, если высота не указана

COLOR_NAMES = {
    "white": "white_concrete", "gray": "light_gray_concrete", "grey": "light_gray_concrete",
    "black": "gray_concrete", "red": "red_terracotta", "yellow": "yellow_concrete",
    "beige": "smooth_sandstone", "cream": "smooth_sandstone", "tan": "smooth_sandstone",
    "brown": "brown_terracotta", "green": "green_concrete", "blue": "light_blue_concrete",
    "orange": "orange_concrete", "pink": "pink_concrete", "gold": "gold_block", "golden": "gold_block",
    "silver": "iron_block", "turquoise": "cyan_concrete", "lightblue": "light_blue_concrete",
}
HEX_TABLE = [((233, 236, 236), "white_concrete"), ((125, 125, 115), "light_gray_concrete"),
             ((55, 58, 62), "gray_concrete"), ((140, 33, 33), "red_terracotta"),
             ((240, 175, 21), "yellow_concrete"), ((215, 200, 150), "smooth_sandstone"),
             ((96, 60, 32), "brown_terracotta"), ((73, 91, 36), "green_concrete"),
             ((36, 137, 199), "light_blue_concrete"), ((224, 97, 1), "orange_concrete"),
             ((213, 101, 142), "pink_concrete"), ((250, 215, 60), "gold_block"),
             ((21, 119, 136), "cyan_concrete"), ((150, 82, 66), "bricks")]
MATERIALS = {"brick": "bricks", "stone": "stone_bricks", "glass": "light_blue_stained_glass",
             "concrete": "light_gray_concrete", "plaster": "white_concrete", "render": "white_concrete",
             "wood": "oak_planks", "metal": "iron_block", "steel": "iron_block", "copper": "weathered_copper",
             "sandstone": "smooth_sandstone", "marble": "quartz_block", "tiles": "red_terracotta"}


# --- сеть ------------------------------------------------------------------

def _fetch(url: str, data: bytes | None = None, timeout: float = 25.0):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def languages_for(query: str) -> str:
    """Какими языками просить названия у карты. Nominatim отдаёт `display_name` на одном
    языке, и для русского запроса он приходил по-английски: проверка «нашли то же самое»
    по корням слов не срабатывала, и всё здание терялось. Просим оба языка сразу."""
    low = query.lower()
    if re.search("[іїєґ]", low):
        return "uk,ru,en"
    if re.search("[әңғүұқөһ]", low):
        return "kk,ru,en"
    if re.search("[а-я]", low):
        return "ru,en"
    return "en"


def _names_of(r: dict) -> str:
    """Все названия найденного в одну строку: и `display_name`, и все `name:*` из
    namedetails. Так русский запрос узнаёт себя в английском здании и наоборот."""
    parts = [str(r.get("display_name") or ""), str(r.get("name") or "")]
    details = r.get("namedetails")
    if isinstance(details, dict):
        parts += [str(v) for v in details.values()]
    return " | ".join(parts).lower()


def geocode(query: str) -> dict | None:
    """Первое подходящее здание по названию: way или relation (у точки нет контура)."""
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 10, "namedetails": 1,
         "accept-language": languages_for(query)})
    stems = [w[:5] for w in re.findall(r"\w{4,}", query.lower())]
    for r in _fetch(url, timeout=10):
        cat = r.get("category") or r.get("class")
        if r.get("osm_type") in ("way", "relation") and cat in OK_CATEGORIES:
            if not stems or any(s in _names_of(r) for s in stems):   # найденное должно быть про то же
                return r
    return None


def overpass(osm_type: str, osm_id: int, bbox: list[float]) -> list[dict]:
    s, n, w, e = (float(v) for v in bbox)
    pad = 0.0004
    kind = "way" if osm_type == "way" else "rel"
    q = (f'[out:json][timeout:25];{kind}({osm_id});out tags geom;'
         f'(way["building:part"]({s - pad},{w - pad},{n + pad},{e + pad});'
         f'rel["building:part"]({s - pad},{w - pad},{n + pad},{e + pad}););out tags geom;')
    # зеркала публичные и то и дело падают: спрашиваем все сразу, берём первый ответ
    from concurrent.futures import ThreadPoolExecutor, as_completed
    payload = urllib.parse.urlencode({"data": q}).encode()
    pool = ThreadPoolExecutor(max_workers=len(OVERPASS))
    futures = [pool.submit(_fetch, url, payload, 22.0) for url in OVERPASS]
    last = None
    try:
        for f in as_completed(futures, timeout=26):
            try:
                return f.result()["elements"]
            except Exception as ex:
                last = ex
    except Exception as ex:
        last = ex
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    raise RuntimeError(f"Overpass недоступен: {last}")


# --- геометрия -------------------------------------------------------------

def _stitch(segs: list[list[tuple]]) -> list[list[tuple]]:
    """Склеиваем куски границы relation в замкнутые кольца."""
    segs = [list(s) for s in segs if len(s) >= 2]
    rings = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[-2::-1]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[:0:-1] + ring
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def _rings(el: dict) -> tuple[list, list]:
    if el["type"] == "way":
        g = [(p["lat"], p["lon"]) for p in el.get("geometry") or []]
        return ([g], []) if len(g) >= 4 else ([], [])
    outer, inner = [], []
    for m in el.get("members", []):
        if m.get("type") == "way" and m.get("geometry"):
            seg = [(p["lat"], p["lon"]) for p in m["geometry"]]
            (inner if m.get("role") == "inner" else outer).append(seg)
    return _stitch(outer), _stitch(inner)


def _num(v) -> float | None:
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v or ""))
    return float(m.group().replace(",", ".")) if m else None


def _color_block(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower().replace(" ", "")
    if v in COLOR_NAMES:
        return COLOR_NAMES[v]
    m = re.fullmatch(r"#?([0-9a-f]{6})", v)
    if m:
        rgb = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
        return min(HEX_TABLE, key=lambda t: sum((a - b) ** 2 for a, b in zip(rgb, t[0])))[1]
    return None


def _materials(value: str | None) -> str | None:
    v = (value or "").lower()
    return next((b for k, b in MATERIALS.items() if k in v), None)


def _shape_info(tags: dict) -> dict:
    levels = _num(tags.get("building:levels"))
    height = _num(tags.get("height")) or (levels * FLOOR_M if levels else None)
    min_h = _num(tags.get("min_height")) or ((_num(tags.get("building:min_level")) or 0) * FLOOR_M)
    roof_h = _num(tags.get("roof:height")) or ((_num(tags.get("roof:levels")) or 0) * FLOOR_M or None)
    shape = (tags.get("roof:shape") or "").lower() or None
    wall = _color_block(tags.get("building:colour") or tags.get("colour")) or \
        _materials(tags.get("building:material") or tags.get("material")) or "light_gray_concrete"
    roof = _color_block(tags.get("roof:colour")) or _materials(tags.get("roof:material"))
    return dict(height=height, min_h=min_h, roof_h=roof_h, shape=shape, wall=wall, roof=roof, tags=tags)


# --- воксели ---------------------------------------------------------------

def voxelize(main: dict | None, parts: list[dict], target: int = TARGET):
    """Контуры -> воксельная модель. Если есть building:part, контур целиком не рисуем (правило OSM)."""
    items = parts if parts else ([main] if main else [])
    shapes = []
    for el in items:
        outer, inner = _rings(el)
        if outer:
            shapes.append((outer, inner, _shape_info(el.get("tags", {}))))
    if not shapes:
        raise ValueError("у объекта нет контура")
    lats = [p[0] for o, _, _ in shapes for r in o for p in r]
    lons = [p[1] for o, _, _ in shapes for r in o for p in r]
    lat0, lon0 = (min(lats) + max(lats)) / 2, min(lons)
    kx, kz = 111320 * math.cos(math.radians(lat0)), 110540

    def xy(p):                                           # метры; север — в сторону -z, как в игре
        return (p[1] - lon0) * kx, -(p[0] - lat0) * kz
    all_pts = [xy(p) for o, _, _ in shapes for r in o for p in r]
    xs, zs = [p[0] for p in all_pts], [p[1] for p in all_pts]
    x0, z0 = min(xs), min(zs)
    width, depth = max(xs) - x0, max(zs) - z0
    default_h = 12.0
    tops = [(s[2]["height"] or default_h) for s in shapes]
    top_m = max(tops)
    m = max(width / target, depth / target, top_m / (target * 1.3), 1.0)     # метров на блок
    nx, nz = int(width / m) + 3, int(depth / m) + 3
    voxels: dict = {}
    for outer, inner, info in sorted(shapes, key=lambda s: s[2]["min_h"]):
        img = Image.new("L", (nx, nz), 0)
        dr = ImageDraw.Draw(img)
        for ring in outer:
            dr.polygon([((xy(p)[0] - x0) / m + 1, (xy(p)[1] - z0) / m + 1) for p in ring], fill=255)
        for ring in inner:
            dr.polygon([((xy(p)[0] - x0) / m + 1, (xy(p)[1] - z0) / m + 1) for p in ring], fill=0)
        mask = np.array(img) > 0
        if not mask.any():
            continue
        dist = distance_transform_edt(mask)
        dmax = float(dist.max())
        total = info["height"] or default_h
        shape = info["shape"]
        pitched = shape in ("gabled", "hipped", "pyramidal", "dome", "onion", "cone", "round", "half-hipped", "gambrel", "mansard")
        roof_m = info["roof_h"] if info["roof_h"] else (None if not pitched else 0.45 * dmax * m * (1.6 if shape in ("dome", "onion", "cone") else 0.8))
        roof_cells = round((roof_m or 0) / m) if pitched else 0
        y0 = round(info["min_h"] / m)
        y1 = max(y0 + 1, round((total - (roof_m or 0)) / m))
        wall_block = info["wall"]
        roof_block = info["roof"] or ("red_terracotta" if shape in ("gabled", "hipped", "half-hipped", "gambrel", "mansard", "pyramidal")
                                      else ("weathered_copper" if shape in ("dome", "onion", "cone", "round") else "gray_concrete"))
        zz, xx = np.nonzero(mask)
        for z, x in zip(zz, xx):
            d = dist[z, x]
            facade = d <= 1.5
            for y in range(y0, y1):
                if facade:
                    window = (y - y0) % 3 == 1 and (x + z) % 2 == 0 and (y1 - y0) > 4 and y > y0 + 1 and y < y1 - 1
                    voxels[(int(x), y, int(z))] = "light_blue_stained_glass" if window else wall_block
                elif (y - y0) % 6 == 0:
                    voxels[(int(x), y, int(z))] = wall_block              # перекрытие этажа
            if roof_cells and dmax > 0:
                frac = min(1.0, d / dmax)
                if shape in ("dome", "onion", "round"):
                    extra = round(roof_cells * math.sqrt(max(0.0, 1 - (1 - frac) ** 2)))
                else:
                    extra = round(roof_cells * frac)
                for y in range(y1, y1 + max(1, extra)):
                    voxels[(int(x), y, int(z))] = roof_block
            else:
                voxels[(int(x), y1 - 1, int(z))] = roof_block                 # плоская кровля
    return voxels, dict(meters_per_block=round(m, 2), width_m=round(width), depth_m=round(depth), height_m=round(top_m),
                        parts=len(parts))


def _shift_to_zero(v: dict) -> dict:
    mx, my, mz = (min(p[i] for p in v) for i in range(3))
    return {(x - mx, y - my, z - mz): b for (x, y, z), b in v.items()}


@lru_cache(maxsize=64)
def _from_name_net(query: str):
    """Название -> (воксели, сведения) или None, если здания нет на карте."""
    hit = geocode(query)
    if not hit:
        return None
    elements = overpass(hit["osm_type"], int(hit["osm_id"]), hit["boundingbox"])
    main = next((e for e in elements if e["type"] == hit["osm_type"].replace("relation", "relation") and e["id"] == int(hit["osm_id"])), None)
    parts = [e for e in elements if e.get("tags", {}).get("building:part") and not (main and e["id"] == main["id"] and e["type"] == main["type"])]
    s, n, w, e_ = (float(v) for v in hit["boundingbox"])
    def inside(el):                                # центр части должен лежать в габарите главного здания
        outer, _ = _rings(el)
        pts = [pt for r in outer for pt in r]
        if not pts:
            return False
        la = sum(p[0] for p in pts) / len(pts); lo = sum(p[1] for p in pts) / len(pts)
        return s <= la <= n and w <= lo <= e_
    parts = [e for e in parts if inside(e)]
    voxels, info = voxelize(main, parts)
    voxels = _shift_to_zero(voxels)
    info["osm"] = f"{hit['osm_type']}/{hit['osm_id']}"
    info["title"] = hit.get("display_name", query).split(",")[0]
    return voxels, info


def to_runs(voxels: dict) -> tuple[list[str], list[list[int]]]:
    """Воксели -> компактные пробеги (y, z, x0, x1, индекс палитры): так программа весит в десятки раз меньше."""
    palette: list[str] = []
    index: dict[str, int] = {}
    rows: dict = {}
    for (x, y, z), b in voxels.items():
        rows.setdefault((y, z), []).append((x, b))
    runs: list[list[int]] = []
    for (y, z), cells in sorted(rows.items()):
        cells.sort()
        x0, prev, cur = cells[0][0], cells[0][0], cells[0][1]
        for x, b in cells[1:] + [(10**9, None)]:
            if b == cur and x == prev + 1:
                prev = x
                continue
            if cur not in index:
                index[cur] = len(palette)
                palette.append(cur)
            runs.append([y, z, x0, prev, index[cur]])
            x0, prev, cur = x, x, b
    return palette, runs


def _cache_path(query: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(query.strip().lower().encode()).hexdigest()[:16] + ".json")


def from_name(query: str):
    """Название -> (воксели, сведения) или None. Результат лежит на диске: повтор мгновенный и без сети."""
    path = _cache_path(query)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("none"):
            return None
        if max(data["info"]["width_m"], data["info"]["depth_m"], data["info"]["height_m"]) < 15:
            return None                       # нашлась мелочь (фонтан, табличка), а не здание
        vox = {}
        for y, z, x0, x1, i in data["runs"]:
            for x in range(x0, x1 + 1):
                vox[(x, y, z)] = data["palette"][i]
        return vox, data["info"]
    got = _from_name_net(query)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not got:
        path.write_text(json.dumps({"none": True}), encoding="utf-8")
        return None
    palette, runs = to_runs(got[0])
    path.write_text(json.dumps({"info": got[1], "palette": palette, "runs": runs}), encoding="utf-8")
    if max(got[1]["width_m"], got[1]["depth_m"], got[1]["height_m"]) < 15:
        return None
    return got


def program_for(query: str):
    """BuildProgram из реального здания или None: блоки едут в программе (часть voxels)."""
    from .schema import BuildProgram
    got = from_name(query)
    if not got:
        return None
    voxels, info = got
    if info.get("parts", 0) < int(os.getenv("OSM_MIN_PARTS", 3)):
        return None        # здание на карте нарисовано одним контуром: выйдет коробка или обломок, лучше модель
    palette, runs = to_runs(voxels)
    program = BuildProgram.model_validate({
        "name": info["title"][:80], "size": [1, 1, 1],
        "parts": [{"type": "voxels", "palette": palette, "runs": runs}]})
    program.size = program.real_size()
    program.source = "osm"
    return program


def main() -> None:
    import argparse
    from .preview import preview
    ap = argparse.ArgumentParser(description="Здание из OpenStreetMap -> PNG-предпросмотр")
    ap.add_argument("query"); ap.add_argument("-o", "--out", default="osm.png")
    args = ap.parse_args()
    got = from_name(args.query)
    if not got:
        print("на карте не нашлось здания с таким названием"); return
    voxels, info = got
    print(info, "| блоков:", len(voxels))
    preview(voxels, args.out)


if __name__ == "__main__":
    main()
