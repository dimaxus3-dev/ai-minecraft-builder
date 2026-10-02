"""Шаблон нового здания. Скопируй в landmarks/<имя>.py и переименуй константы.

Проверка по картинке:   python -m builder.blueprints <ID> -o docs/previews/<ID>.png
Потом ОТКРОЙ картинку, сравни с настоящим зданием, поправь и повтори.
"""

from __future__ import annotations

from ..kit import Canvas

ID = "template_tower"                           # латиницей, без пробелов, уникальный
TITLE_EN = "Template Tower"
TITLE_RU = "Шаблонная башня"
# каждая «ловушка» — набор кусочков, которые ВСЕ должны встретиться в запросе (основы слов, нижний регистр,
# «ё» = «е», дефисы как пробелы): ловит «башню», «Башня» и «tower» одинаково
ALIASES = [("шаблонн", "башн"), ("template", "tower")]
ABOUT = "одной строкой по-английски: как выглядит здание (идёт в подсказку модели)"


def build() -> dict:
    """Вернуть {(x, y, z): блок}. y — высота (0 = земля), блоки только из палитры builder/blocks.py.
    Холст рисует теми же фигурами, что и модель: box, hollow, cyl, sphere, dome, cone, line, poly, arch, roof."""
    c = Canvas()
    c.box((0, 0, 0), (20, 0, 20), "light_gray_concrete")               # площадка
    c.hollow((5, 1, 5), (15, 30, 15), "stone_bricks", 1)               # стены
    c.carve((9, 1, 5), (11, 4, 5))                                      # дверь (воздух)
    c.cone((10, 31, 10), 7, 10, "red_concrete")                         # крыша
    return c.v
