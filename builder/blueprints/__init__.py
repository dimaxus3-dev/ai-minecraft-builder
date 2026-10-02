"""Библиотека готовых чертежей знаменитых зданий.

Модель, которая выдаёт числа для линий и коробок, не нарисует узнаваемую Эйфелеву башню,
поэтому такие здания написаны кодом (кривые профиля, фермы, арки) и проверены по картинке
(`python -m builder.preview`). Всё остальное строит LLM, а эти чертежи показывает ей как образцы.

Чертёж = функция build() -> {(x, y, z): блок}. Реестр ищет здание по названию в запросе.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

from .kit import normalize


@dataclass
class Entry:
    id: str
    title_en: str
    title_ru: str
    # каждая «ловушка» — набор кусочков, которые должны ВСЕ встретиться в запросе (основы слов,
    # чтобы «эйфелеву башню» и «tour Eiffel» ловились одинаково)
    aliases: list[tuple[str, ...]]
    fn: Callable[..., dict]
    about: str = field(default="")
    generic: bool = False      # типовое здание: берём чертёж только на короткий запрос


REGISTRY: dict[str, Entry] = {}


def register(entry: Entry) -> None:
    REGISTRY[entry.id] = entry


def _load() -> None:
    from . import archetypes as A
    from . import (baiterek, colosseum, eiffel, goldengate, khanshatyr, motherland,
                   palace_of_peace, pyramid, saintsophia, tajmahal, transamerica)
    register(Entry("eiffel_tower", "Eiffel Tower", "Эйфелева башня",
                   [("эйфел",), ("eiffel",), ("eifel",), ("эйфеля",)], eiffel.build,
                   "iron lattice tower, tapering legs, arches, three platforms, spire"))
    register(Entry("golden_gate_bridge", "Golden Gate Bridge", "Мост Золотые Ворота",
                   [("golden", "gate"), ("золот", "ворот"), ("золоты", "врат")], goldengate.build,
                   "orange suspension bridge, two towers, main cables, side spans"))
    register(Entry("transamerica_pyramid", "Transamerica Pyramid", "Пирамида Трансамерика",
                   [("transamerica",), ("трансамерик",), ("транс", "америк")], transamerica.build,
                   "slim white tapering skyscraper in San Francisco, two wings, long spire, redwoods"))
    register(Entry("taj_mahal", "Taj Mahal", "Тадж-Махал",
                   [("тадж",), ("taj",)], tajmahal.build,
                   "white marble mausoleum, big dome, four minarets, reflecting pool"))
    register(Entry("colosseum", "Colosseum", "Колизей",
                   [("колизей",), ("colosseum",), ("coliseum",), ("колосс", "рим")], colosseum.build,
                   "elliptical Roman amphitheatre, three tiers of arches, broken wall"))
    register(Entry("baiterek", "Baiterek", "Байтерек",
                   [("байтерек",), ("бәйтерек",), ("baiterek",), ("bayterek",)], baiterek.build,
                   "Astana monument: white tapering lattice trunk with a golden glass sphere on top"))
    register(Entry("khan_shatyr", "Khan Shatyr", "Хан Шатыр",
                   [("хан", "шатыр"), ("хан", "шатер"), ("khan", "shatyr")], khanshatyr.build,
                   "Astana: giant translucent tent with ribs and a tilted central mast"))
    register(Entry("palace_of_peace", "Palace of Peace and Reconciliation", "Дворец мира и согласия",
                   [("дворец", "мира"), ("palace", "peace"), ("pyramid", "astana"), ("пирамид", "астан")],
                   palace_of_peace.build, "Astana: stepped glass pyramid"))
    register(Entry("saint_sophia", "Saint Sophia Cathedral, Kyiv", "Софийский собор (Киев)",
                   [("софийск",), ("софійськ",), ("sophia", "kyiv"), ("sophia", "kiev"),
                    ("собор", "киев"), ("собор", "київ")], saintsophia.build,
                   "Kyiv: white cathedral, green roofs, thirteen golden domes, bell tower"))
    register(Entry("motherland_monument", "Motherland Monument, Kyiv", "Батьківщина-мати (Киев)",
                   [("батьківщина", "мати"), ("родина", "мать", "киев"), ("родина", "мать", "київ"),
                    ("motherland", "monument"), ("motherland", "kyiv"), ("motherland", "kiev")],
                   motherland.build, "Kyiv: huge statue of a woman with raised sword and shield on a round pedestal"))
    register(Entry("great_pyramid", "Great Pyramid of Giza", "Великая пирамида",
                   [("хеопс",), ("khufu",), ("cheops",), ("гиз",), ("пирамид",), ("pyramid",)], pyramid.build,
                   "stepped sandstone pyramid with gold cap, three small queens' pyramids"))
    # здания-плагины из landmarks/: каждый файл (кроме «_шаблона») подхватывается сам, до типовых
    import importlib
    import pkgutil

    from . import landmarks
    for info in sorted(pkgutil.iter_modules(landmarks.__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{__name__}.landmarks.{info.name}")
            register(Entry(mod.ID, mod.TITLE_EN, mod.TITLE_RU, [tuple(a) for a in mod.ALIASES],
                           mod.build, getattr(mod, "ABOUT", "")))
        except Exception as e:                      # кривой плагин не должен ронять всю библиотеку
            import logging
            logging.getLogger("hack.blueprints").warning("плагин %s не загружен: %s", info.name, e)
    for id_, en, ru, al, fn, about in (
        ("castle", "Castle", "Замок", [("замок",), ("castle",), ("крепост",), ("fortress",)], A.castle,
         "stone castle with moat, four corner towers with red cone roofs, gatehouse, keep"),
        ("house", "House", "Дом", [("дом",), ("house",), ("cottage",), ("коттедж",), ("избушк",)], A.house,
         "timber-framed cottage with gable roof, chimney, fence, path"),
        ("skyscraper", "Skyscraper", "Небоскрёб", [("небоскр",), ("skyscraper",), ("высотк",)], A.skyscraper,
         "glass office tower with setbacks, antenna"),
        ("cathedral", "Cathedral", "Собор", [("собор",), ("cathedral",), ("церков",), ("church",)], A.cathedral,
         "gothic cathedral: nave, transept, two towers with spires, stained glass, rose window"),
        ("pagoda", "Pagoda", "Пагода", [("пагод",), ("pagoda",)], A.pagoda,
         "five-tier pagoda with upturned eaves and gold finial"),
        ("windmill", "Windmill", "Мельница", [("мельниц",), ("windmill",)], A.windmill,
         "stone windmill with four sails"),
        ("lighthouse", "Lighthouse", "Маяк", [("маяк",), ("lighthouse",)], A.lighthouse,
         "red and white striped lighthouse on rocks, lantern room"),
    ):
        register(Entry(id_, en, ru, al, fn, about, generic=True))


def _text(s: str) -> str:
    return re.sub(r"[^\w\s]", " ", s.lower().replace("ё", "е"))


def _has_stem(text: str, stem: str) -> bool:
    """Корень ищем только с начала слова. Иначе «lighthouse» ловилось на корень «house»
    (дом зарегистрирован раньше маяка) и запрос про маяк строил дом; то же было бы с
    «greenhouse», «courthouse», «подвал» и «вал»."""
    return re.search(r"(?<!\w)" + re.escape(stem), text) is not None


def match(text: str) -> str | None:
    """id чертежа, если запрос про известное здание, иначе None."""
    t = _text(text)
    words = len(t.split())
    for entry in REGISTRY.values():
        if entry.generic and words > 3:
            continue          # «красный замок с драконом» — пожелания, пусть думает модель
        if any(all(_has_stem(t, part) for part in alias) for alias in entry.aliases):
            return entry.id
    return None


@lru_cache(maxsize=32)
def _built(id: str, params: tuple) -> dict:
    return normalize(REGISTRY[id].fn(**dict(params)))


def build(id: str, params: dict | None = None) -> dict:
    """Блоки чертежа {(x, y, z): блок} со сдвигом в ноль."""
    if id not in REGISTRY:
        raise ValueError(f"нет такого чертежа: {id}")
    return _built(id, tuple(sorted((params or {}).items())))


def title(id: str, request_text: str = "") -> str:
    e = REGISTRY[id]
    return e.title_ru if re.search("[а-яА-Я]", request_text) else e.title_en


def listing() -> str:
    """Список чертежей для подсказки LLM."""
    lines = []
    for e in REGISTRY.values():
        v = build(e.id)
        w, h, d = (max(p[i] for p in v) + 1 for i in range(3))
        lines.append(f'- "{e.id}" ({w}x{h}x{d} blocks): {e.title_en} - {e.about}')
    return "\n".join(lines)


_load()
