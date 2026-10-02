"""Геометрические примитивы.

Здесь только математика: каждая функция возвращает список целых координат
(x, y, z) — относительно точки постройки. Minecraft здесь не упоминается,
поэтому всё можно проверять без запущенной игры.

Оси: x — вправо, y — вверх, z — вперёд.
"""

import math

Vec3 = tuple[int, int, int]
Cells = list[Vec3]

AXES = {"x": 0, "y": 1, "z": 2}


# --- мелкие помощники ----------------------------------------------------

def _bounds(a: Vec3, b: Vec3) -> tuple[Vec3, Vec3]:
    """Сортирует два угла в (минимальный, максимальный)."""
    lo = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
    hi = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
    return lo, hi


def _ball_offsets(thickness: int) -> Cells:
    """Смещения для «толстой» точки: 1 -> один блок, 2 -> 2x2x2, 3 -> шарик r=1."""
    if thickness <= 1:
        return [(0, 0, 0)]
    if thickness == 2:
        # у чётной толщины нет центра, поэтому просто куб 2x2x2
        return [(dx, dy, dz)
                for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
    r = (thickness - 1) / 2
    rng = range(-math.ceil(r), math.ceil(r) + 1)
    return [
        (dx, dy, dz)
        for dx in rng for dy in rng for dz in rng
        if dx * dx + dy * dy + dz * dz <= (r + 0.35) ** 2
    ]


def _disk(radius: int, hollow: bool) -> list[tuple[int, int]]:
    """Диск (или кольцо) радиуса radius в 2D, центр в (0, 0)."""
    r2 = (radius + 0.5) ** 2
    inside = {
        (u, v)
        for u in range(-radius, radius + 1)
        for v in range(-radius, radius + 1)
        if u * u + v * v <= r2
    }
    if not hollow:
        return sorted(inside)
    # кольцо: клетка диска, у которой хотя бы один сосед снаружи
    ring = [
        (u, v) for (u, v) in inside
        if any((u + du, v + dv) not in inside
               for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    ]
    return sorted(ring)


# --- примитивы -----------------------------------------------------------

def box(start: Vec3, end: Vec3) -> Cells:
    """Сплошной параллелепипед, оба угла включительно."""
    lo, hi = _bounds(start, end)
    return [
        (x, y, z)
        for x in range(lo[0], hi[0] + 1)
        for y in range(lo[1], hi[1] + 1)
        for z in range(lo[2], hi[2] + 1)
    ]


def hollow_box(start: Vec3, end: Vec3, thickness: int = 1) -> Cells:
    """Коробка-скорлупа: все шесть стенок толщиной thickness, внутри пусто."""
    lo, hi = _bounds(start, end)
    t = max(1, thickness)
    return [
        (x, y, z)
        for x in range(lo[0], hi[0] + 1)
        for y in range(lo[1], hi[1] + 1)
        for z in range(lo[2], hi[2] + 1)
        if (x - lo[0] < t or hi[0] - x < t
            or y - lo[1] < t or hi[1] - y < t
            or z - lo[2] < t or hi[2] - z < t)
    ]


def cylinder(center: Vec3, radius: int, height: int,
             hollow: bool = False, axis: str = "y") -> Cells:
    """Цилиндр. center — центр основания, height идёт по оси axis вверх/вперёд."""
    ai = AXES.get(axis, 1)
    ui, vi = [i for i in range(3) if i != ai]
    cells: Cells = []
    for u, v in _disk(max(0, radius), hollow):
        for k in range(max(1, height)):
            p = [0, 0, 0]
            p[ai] = center[ai] + k
            p[ui] = center[ui] + u
            p[vi] = center[vi] + v
            cells.append((p[0], p[1], p[2]))
    return cells


def sphere(center: Vec3, radius: int, hollow: bool = False) -> Cells:
    """Шар или сфера-скорлупа (одна стенка)."""
    r = max(0, radius)
    outer = (r + 0.5) ** 2
    inner = (r - 0.5) ** 2
    cx, cy, cz = center
    cells: Cells = []
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            for dz in range(-r, r + 1):
                d2 = dx * dx + dy * dy + dz * dz
                if d2 > outer:
                    continue
                if hollow and d2 < inner:
                    continue
                cells.append((cx + dx, cy + dy, cz + dz))
    return cells


def line(start: Vec3, end: Vec3, thickness: int = 1) -> Cells:
    """Прямая линия между двумя точками (как Брезенхем, но в 3D и с толщиной)."""
    steps = max(abs(end[i] - start[i]) for i in range(3)) or 1
    offsets = _ball_offsets(thickness)
    seen: set[Vec3] = set()
    for i in range(steps + 1):
        t = i / steps
        base = tuple(round(start[k] + (end[k] - start[k]) * t) for k in range(3))
        for ox, oy, oz in offsets:
            seen.add((base[0] + ox, base[1] + oy, base[2] + oz))
    return sorted(seen)


def roof(start: Vec3, end: Vec3, style: str = "gable",
         height: int | None = None, axis: str | None = None) -> Cells:
    """Крыша над прямоугольником start..end. Высота y берётся из start.

    gable   — двускатная, конёк вдоль длинной стороны (или вдоль axis);
    pyramid — четырёхскатная, сходится в точку;
    flat    — плоская плита в один блок.
    """
    lo, hi = _bounds(start, end)
    base_y = lo[1]
    x1, x2, z1, z2 = lo[0], hi[0], lo[2], hi[2]
    wx, wz = x2 - x1 + 1, z2 - z1 + 1

    if style == "flat":
        return box((x1, base_y, z1), (x2, base_y, z2))

    if style == "pyramid":
        max_h = (min(wx, wz) + 1) // 2
        h = max(1, min(height or max_h, max_h))
        cells: Cells = []
        for k in range(h):
            ax1, ax2 = x1 + k, x2 - k
            az1, az2 = z1 + k, z2 - k
            if ax1 > ax2 or az1 > az2:
                break
            y = base_y + k
            if ax2 - ax1 <= 1 or az2 - az1 <= 1:
                cells += box((ax1, y, az1), (ax2, y, az2))   # шапка целиком
            else:
                cells += hollow_box((ax1, y, az1), (ax2, y, az2))
        return cells

    # gable: конёк вдоль длинной стороны, если ось не задана явно
    ridge = axis if axis in ("x", "z") else ("x" if wx >= wz else "z")
    span = wz if ridge == "x" else wx
    max_h = (span + 1) // 2
    h = max(1, min(height or max_h, max_h))
    cells = []
    for k in range(h):
        y = base_y + k
        if ridge == "x":
            a, b = z1 + k, z2 - k
            if a > b:
                break
            cells += box((x1, y, a), (x2, y, a))
            if b != a:
                cells += box((x1, y, b), (x2, y, b))
        else:
            a, b = x1 + k, x2 - k
            if a > b:
                break
            cells += box((a, y, z1), (a, y, z2))
            if b != a:
                cells += box((b, y, z1), (b, y, z2))
    return cells


def arch(start: Vec3, end: Vec3, height: int, thickness: int = 1) -> Cells:
    """Арка: полуэллипс от основания start до основания end, апогей на height.

    У краёв стенки идут вертикально — выглядит как настоящая арка, а не как горка.
    """
    h = max(1, height)
    span = max(
        abs(end[0] - start[0]), abs(end[2] - start[2]), abs(end[1] - start[1])
    ) or 1
    steps = max(span * 4, h * 4, 8)
    offsets = _ball_offsets(thickness)
    seen: set[Vec3] = set()
    for i in range(steps + 1):
        t = i / steps
        x = start[0] + (end[0] - start[0]) * t
        z = start[2] + (end[2] - start[2]) * t
        y0 = start[1] + (end[1] - start[1]) * t
        rise = h * math.sqrt(max(0.0, 1.0 - (2 * t - 1) ** 2))
        base = (round(x), round(y0 + rise), round(z))
        for ox, oy, oz in offsets:
            seen.add((base[0] + ox, base[1] + oy, base[2] + oz))
    return sorted(seen)


# --- выбор примитива по его типу ----------------------------------------

def cells_of(part) -> Cells:
    """Координаты одной части программы. Работает с любым объектом,
    у которого есть поле .type и нужные поля — pydantic-модель или простой
    объект. Нарочно не импортируем здесь схему: этот модуль остаётся
    чистой математикой без зависимостей.
    """
    t = part.type
    if t == "box":
        return box(part.start, part.end)
    if t == "hollow_box":
        return hollow_box(part.start, part.end, part.thickness)
    if t == "cylinder":
        return cylinder(part.center, part.radius, part.height,
                        part.hollow, part.axis)
    if t == "sphere":
        return sphere(part.center, part.radius, part.hollow)
    if t == "line":
        return line(part.start, part.end, part.thickness)
    if t == "roof":
        return roof(part.start, part.end, part.style, part.height, part.axis)
    if t == "arch":
        return arch(part.start, part.end, part.height, part.thickness)
    raise ValueError(f"неизвестный примитив: {t}")
