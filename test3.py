from gdpc import Editor, Block, geometry

editor = Editor(buffering=True)

# 1. box: стена 10x5
geometry.placeCuboid(editor, (0, -60, 0), (9, -56, 0), Block("orange_concrete"))

# 2. cylinder: радиус 3, высота 8, центр (15, -60, 5)
cx, cy, cz, r, h = 15, -60, 5, 3, 8
for x in range(cx - r, cx + r + 1):
    for z in range(cz - r, cz + r + 1):
        if (x - cx) ** 2 + (z - cz) ** 2 <= r * r:
            geometry.placeCuboid(editor, (x, cy, z), (x, cy + h - 1, z), Block("white_concrete"))

# 3. line: от (22, -60, 0) до (32, -50, 10)
a, b = (22, -60, 0), (32, -50, 10)
steps = 40
for i in range(steps + 1):
    t = i / steps
    p = tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))
    editor.placeBlock(p, Block("gray_concrete"))

editor.flushBuffer()
print("Готово")
