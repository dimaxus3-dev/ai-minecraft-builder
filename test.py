from gdpc import Editor, Block, geometry

editor = Editor(buffering=True)
geometry.placeCuboid(editor, (0, -60, 0), (5, -55, 5), Block("gold_block"))
editor.flushBuffer()
print("Готово")
