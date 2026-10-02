"""Библиотека готовых чертежей знаменитых зданий.

Модель, которая выдаёт числа для линий и коробок, не нарисует узнаваемую Эйфелеву башню,
поэтому такие здания написаны кодом (кривые профиля, фермы, арки) и проверены по картинке
(`python -m builder.preview`). Всё остальное строит LLM, а эти чертежи показывает ей как образцы.

Чертёж = функция build() -> {(x, y, z): блок}. Реестр ищет здание по названию в запросе.
"""

from __future__ import annotations

import os
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
    tunable: bool = False      # принимает цвет/размер/материал из запроса (params.py)
    max_words: int = 3         # предел длины запроса для generic-записей


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
    # Предметы (не здания): карта их не знает, а модель рисует технику плохо.
    # Все принимают цвет, материал и размер из запроса, поэтому вариантов тысячи.
    from . import things as T
    for id_, en, ru, al, fn, about in (
        ("plane", "Airplane", "Самолёт",
         [("самолет",), ("самолёт",), ("самолёта",), ("самолётик",), ("plane",), ("airplane",),
          ("aeroplane",), ("aircraft",), ("jet",), ("боинг",), ("boeing",), ("airbus",),
          ("аэробус",), ("лайнер",), ("авиалайнер",)], T.plane,
         "airliner on a runway: tapered fuselage, swept wings, two engines, tail fin, landing gear"),
        ("ship", "Sailing ship", "Корабль",
         [("корабл",), ("кораблик",), ("судно",), ("парусник",), ("фрегат",), ("каравелл",),
          ("галеон",), ("ship",), ("boat",), ("sailboat",), ("galleon",), ("frigate",),
          ("яхта",), ("yacht",), ("титаник",), ("titanic",)], T.ship,
         "wooden sailing ship on water: hull, deck, three masts with sails, stern cabin, bowsprit"),
        ("rocket", "Rocket", "Ракета",
         [("ракет",), ("rocket",), ("шаттл",), ("shuttle",), ("starship",), ("звездолет",),
          ("звездолёт",), ("spaceship",), ("spacecraft",)], T.rocket,
         "rocket on a launch pad: striped body, nose cone, four fins, nozzles, service tower"),
        ("train", "Steam train", "Поезд",
         [("поезд",), ("паровоз",), ("локомотив",), ("электричк",), ("train",), ("locomotive",),
          ("railway",), ("железная", "дорога")], T.train,
         "steam locomotive with tender and carriage on rails: boiler, chimney, cab, wheels, embankment"),
        ("car", "Car", "Машина",
         [("машин",), ("автомобил",), ("тачк",), ("car",), ("automobile",), ("джип",), ("jeep",),
          ("грузовик",), ("truck",), ("bus",), ("автобус",)], T.car,
         "car on asphalt: body, cabin with glass, four wheels, headlights"),
        ("tank", "Tank", "Танк",
         [("танк",), ("tank",), ("бронетехник",)], T.tank,
         "tank: hull, tracks with road wheels, turret with a long gun, hatch, antenna"),
        ("robot", "Robot", "Робот",
         [("робот",), ("robot",), ("андроид",), ("android",), ("меха",), ("mech",),
          ("киборг",), ("cyborg",)], T.robot,
         "standing robot: boxy body, head with a glowing visor, arms with shoulder balls, legs on a plate"),
        ("ferris_wheel", "Ferris wheel", "Колесо обозрения",
         [("колесо", "обозрен"), ("ferris",), ("обозрения",), ("чертово", "колесо"),
          ("чёртово", "колесо")], T.ferris_wheel,
         "ferris wheel: rim with spokes, twelve coloured cabins, two legs, platform"),
        ("fountain", "Fountain", "Фонтан",
         [("фонтан",), ("fountain",)], T.fountain,
         "fountain: round basin, stacked bowls, water jets, lanterns on the rim"),
        ("statue", "Statue", "Статуя",
         [("статуя",), ("статую",), ("статуи",), ("statue",), ("памятник",), ("изваяние",)], T.statue,
         "statue on a pedestal: figure with a raised torch, cloak, crown, steps"),
        ("stadium", "Stadium", "Стадион",
         [("стадион",), ("stadium",), ("арена",), ("arena",)], T.stadium,
         "stadium: oval tiered stands, green pitch with markings, goals, floodlights"),
        ("tree", "Great tree", "Дерево",
         [("дерево",), ("дерева",), ("деревья",), ("tree",), ("баобаб",), ("baobab",),
          ("сакура",), ("sakura",), ("дубрав",)], T.tree,
         "huge tree: twisting trunk, branches, leaf crown, grass mound, mossy rocks"),
        ("helicopter", "Helicopter", "Вертолёт",
         [("вертолет",), ("вертолёт",), ("вертушк",), ("helicopter",), ("chopper",),
          ("вертолёта",)], T.helicopter,
         "helicopter on a pad: glazed cabin, tail boom, main and tail rotors, skids"),
        ("submarine", "Submarine", "Подводная лодка",
         [("подводн", "лодк"), ("субмарин",), ("submarine",), ("подлодк",), ("u-boat",)], T.submarine,
         "submarine in water: cigar hull, conning tower with periscope, fins, propeller"),
        ("bridge", "Arch bridge", "Мост",
         [("мост",), ("мосты",), ("bridge",), ("виадук",), ("viaduct",), ("акведук",),
          ("aqueduct",)], T.bridge,
         "stone arch bridge over a river: piers, four arches, deck, railings, lanterns"),
        ("mosque", "Mosque", "Мечеть",
         [("мечет",), ("mosque",), ("масджид",), ("мінарет",), ("минарет",)], T.mosque,
         "mosque: domed prayer hall, four minarets, arched portal, small domes, courtyard"),
        ("obelisk", "Obelisk", "Обелиск",
         [("обелиск",), ("obelisk",), ("стела",), ("stele",)], T.obelisk,
         "obelisk on steps: tapering shaft, gilded pyramidion, fire bowls"),
        ("triumphal_arch", "Triumphal arch", "Триумфальная арка",
         [("триумфальн",), ("triumphal",), ("арка",), ("арку",), ("arc", "triomphe"),
          ("ворота",)], T.triumphal_arch,
         "triumphal arch: big vaulted opening, side passages, columns, cornice, quadriga on top"),
        ("clock_tower", "Clock tower", "Часовая башня",
         [("часов", "башн"), ("clock", "tower"), ("биг", "бен"), ("big", "ben"),
          ("куранты",), ("clocktower",)], T.clock_tower,
         "clock tower: tall shaft, belfry with four clock faces, pinnacles, tall spire with a lamp"),
        ("mansion", "Mansion", "Особняк",
         [("особняк",), ("mansion",), ("усадьб",), ("поместь",), ("villa",), ("вилла",),
          ("manor",), ("резиденц",), ("estate",), ("chateau",), ("шато",)], T.mansion,
         "two-storey manor: side wings, tall hip roof, rooftop turret, columned porch, chimneys, garden"),
        ("supercar", "Supercar", "Суперкар",
         [("суперкар",), ("supercar",), ("спорткар",), ("sportscar",), ("sports", "car"),
          ("гоноч",), ("racing", "car"), ("ferrari",), ("феррари",), ("lamborghini",),
          ("ламборг",), ("porsche",), ("порше",), ("болид",), ("bugatti",)], T.car,
         "low sports car on asphalt: sleek body, glazed cabin, wide wheels"),
        ("igloo", "Igloo", "Иглу",
         [("иглу",), ("igloo",), ("снежн", "дом"), ("ледян", "дом")], T.igloo,
         "igloo: snow dome with ice courses, entrance tunnel, ice windows, campfire, snow drifts"),
    ):
        register(Entry(id_, en, ru, al, fn, about, tunable=True))

    for id_, en, ru, al, fn, about in (
        ("castle", "Castle", "Замок", [("замок",), ("castle",), ("крепост",), ("fortress",), ("форт",), ("fort",),
          ("цитадел",), ("citadel",), ("кремл",), ("kremlin",), ("бастион",), ("keep",)], A.castle,
         "stone castle with moat, four corner towers with red cone roofs, gatehouse, keep"),
        ("house", "House", "Дом", [("дом",), ("house",), ("cottage",), ("коттедж",), ("избушк",), ("домик",), ("хижин",),
          ("hut",), ("cabin",), ("шале",), ("chalet",), ("бунгало",), ("bungalow",), ("изба",)], A.house,
         "timber-framed cottage with gable roof, chimney, fence, path"),
        ("skyscraper", "Skyscraper", "Небоскрёб", [("небоскр",), ("skyscraper",), ("высотк",), ("башня",), ("башню",), ("tower",),
          ("офис",), ("office",), ("бизнес",), ("hotel",), ("отел",), ("гостиниц",)], A.skyscraper,
         "glass office tower with setbacks, antenna"),
        ("cathedral", "Cathedral", "Собор", [("собор",), ("cathedral",), ("церков",), ("church",), ("храм",), ("temple",),
          ("часовн",), ("chapel",), ("монастыр",), ("monastery",), ("базилик",), ("basilica",),
          ("костёл",), ("костел",), ("kirche",)], A.cathedral,
         "gothic cathedral: nave, transept, two towers with spires, stained glass, rose window"),
        ("pagoda", "Pagoda", "Пагода", [("пагод",), ("pagoda",)], A.pagoda,
         "five-tier pagoda with upturned eaves and gold finial"),
        ("windmill", "Windmill", "Мельница", [("мельниц",), ("windmill",)], A.windmill,
         "stone windmill with four sails"),
        ("lighthouse", "Lighthouse", "Маяк", [("маяк",), ("lighthouse",)], A.lighthouse,
         "red and white striped lighthouse on rocks, lantern room"),
    ):
        register(Entry(id_, en, ru, al, fn, about, generic=True, tunable=False))


def _text(s: str) -> str:
    return re.sub(r"[^\w\s]", " ", s.lower().replace("ё", "е"))


def _has_stem(text: str, stem: str) -> bool:
    """Корень ищем только с начала слова. Иначе «lighthouse» ловилось на корень «house»
    (дом зарегистрирован раньше маяка) и запрос про маяк строил дом; то же было бы с
    «greenhouse», «courthouse», «подвал» и «вал»."""
    return re.search(r"(?<!\w)" + re.escape(stem), text) is not None


def match(text: str) -> str | None:
    """id чертежа, если запрос про известное здание или предмет, иначе None."""
    t = _text(text)
    words = len(t.split())
    for entry in REGISTRY.values():
        if entry.generic and words > entry.max_words:
            continue          # «красный замок с драконом» — пожелания, пусть думает модель
        if any(all(_has_stem(t, part) for part in alias) for alias in entry.aliases):
            return entry.id
    # Мягкий проход — только для коротких запросов-существительных («Supercar»,
    # «Viking mansion»). Длинное описание («розовый замок с драконом на крыше») —
    # это задача для модели, в ней весь смысл открытого ИИ в проекте.
    return soft_match(t) if words <= int(os.getenv("SOFT_MATCH_WORDS", 3)) else None


def soft_match(text: str) -> str | None:
    """Второй проход: корень разрешаем и внутри слова, но только длинный.
    «supercar» -> машина, «greenhouse» -> дом, «skyscrapers» -> небоскрёб.
    Короткие корни («дом», «car») сюда не попадают: они ловили бы пол-словаря."""
    t = _text(text)
    best, best_len = None, 0
    for entry in REGISTRY.values():
        for alias in entry.aliases:
            if all(part in t for part in alias):
                length = sum(len(part) for part in alias)
                if length >= 5 and length > best_len:
                    best, best_len = entry.id, length
    return best


# что перекрашивать нельзя: земля, вода, стекло и всё светящееся — иначе
# «ледяной замок» получит ледяную траву и погасшие окна
KEEP = {"air", "water", "lava", "grass_block", "dirt", "dirt_path", "gravel", "sand",
        "glass", "iron_bars", "glowstone", "sea_lantern", "lantern", "torch", "fire",
        "campfire", "redstone_lamp", "coal_block", "oak_leaves", "spruce_leaves"}


def _recolor(voxels: dict, main: str | None, accent: str | None) -> dict:
    """Перекраска готового чертежа: две самые частые несущие породы меняем на
    запрошенные. Так стиль и цвет работают даже там, где генератор про них не знает —
    «ледяной замок», «золотая эйфелева башня»."""
    if not main:
        return voxels
    from collections import Counter
    counts = Counter(b for b in voxels.values()
                     if b not in KEEP and not b.endswith("_stained_glass"))
    top = [b for b, _ in counts.most_common(2)]
    swap: dict[str, str] = {}
    if top:
        swap[top[0]] = main
    if accent and len(top) > 1:
        swap[top[1]] = accent
    return {p: swap.get(b, b) for p, b in voxels.items()}


@lru_cache(maxsize=256)
def _built(id: str, params: tuple) -> dict:
    return normalize(REGISTRY[id].fn(**dict(params)))


def build(id: str, params: dict | None = None) -> dict:
    """Блоки чертежа {(x, y, z): блок} со сдвигом в ноль."""
    if id not in REGISTRY:
        raise ValueError(f"нет такого чертежа: {id}")
    params = dict(params or {})
    if REGISTRY[id].tunable:
        return _built(id, tuple(sorted(params.items())))
    # генератор параметров не принимает — красим уже готовые блоки
    return _recolor(_built(id, ()), params.get("main"), params.get("accent"))


def params_for(id: str, request_text: str) -> dict:
    """Цвет, размер и материал из запроса — для чертежей, которые их принимают.
    Благодаря этому один чертёж даёт тысячи разных построек."""
    entry = REGISTRY.get(id)
    if not entry:
        return {}
    from . import params
    found = params.parse(request_text)
    if not entry.tunable:
        found.pop("scale", None)      # чужой генератор размера не понимает
    return found


def title(id: str, request_text: str = "") -> str:
    """Название постройки. По умолчанию английское: показ идёт на английском, даже
    когда человек написал запрос по-русски. SHOW_LANG=ru возвращает прежнее поведение."""
    e = REGISTRY[id]
    if os.getenv("SHOW_LANG", "en").lower().startswith("ru") and re.search("[а-яА-Я]", request_text):
        return e.title_ru
    return e.title_en


def listing() -> str:
    """Список чертежей для подсказки LLM."""
    lines = []
    for e in REGISTRY.values():
        v = build(e.id)
        w, h, d = (max(p[i] for p in v) + 1 for i in range(3))
        lines.append(f'- "{e.id}" ({w}x{h}x{d} blocks): {e.title_en} - {e.about}')
    return "\n".join(lines)


_load()
