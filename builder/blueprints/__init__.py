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
    listed: bool = True        # показывать ли модели как основу для вариации


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
                           mod.build, getattr(mod, "ABOUT", ""),
                           generic=getattr(mod, "GENERIC", False),
                           tunable=getattr(mod, "TUNABLE", False),
                           max_words=getattr(mod, "MAX_WORDS", 3)))
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

    _load_families()

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


def _load_families() -> None:
    """Семейства: один генератор, десятки узнаваемых силуэтов.

    Небоскрёбы, античные храмы, купольные здания и ступенчатые пирамиды
    отличаются пропорциями, а не принципом, поэтому каждое здание здесь —
    это набор чисел, а не отдельный файл. Все принимают цвет и размер."""
    from functools import partial

    from . import classic as K
    from . import small as M
    from . import towers as W

    def add(id_, en, ru, aliases, fn, about, **kw):
        register(Entry(id_, en, ru, [tuple(a) for a in aliases],
                       partial(fn, **kw) if kw else fn, about,
                       tunable=True, listed=False))

    # --- небоскрёбы --------------------------------------------------------
    T = W.tower
    add("salesforce_tower", "Salesforce Tower", "Башня Salesforce",
        [("salesforce",), ("сейлсфорс",), ("сейлфорс",), ("сейлсфорса",)], T,
        "San Francisco: tapering round glass obelisk with a glowing lattice crown",
        height=112, base=9, taper=0.58, shape="round", crown="lattice", bands=4,
        main="white_concrete", accent="light_blue_stained_glass")
    add("empire_state_building", "Empire State Building", "Эмпайр-стейт-билдинг",
        [("empire", "state"), ("эмпайр",)], T,
        "New York: limestone setbacks, pyramid crown, tall mooring mast",
        height=104, base=13, taper=0.5, setbacks=4, crown="pyramid", spire=16,
        main="light_gray_concrete", accent="gray_concrete")
    add("chrysler_building", "Chrysler Building", "Крайслер-билдинг",
        [("chrysler",), ("крайслер",)], T,
        "New York: art deco steel crown of stacked arches and a needle spire",
        height=96, base=11, taper=0.45, setbacks=3, crown="arch", spire=18,
        main="light_gray_concrete", accent="iron_block")
    add("one_world_trade", "One World Trade Center", "Башня Свободы",
        [("world", "trade"), ("freedom", "tower"), ("башня", "свобод"), ("wtc",)], T,
        "New York: square base turning to octagon, mirrored glass, long spire",
        height=110, base=11, taper=0.42, shape="octagon", crown="flat", spire=22,
        main="light_blue_stained_glass", accent="white_concrete")
    add("flatiron_building", "Flatiron Building", "Утюг",
        [("flatiron",), ("флэтайрон",), ("утюг",)], T,
        "New York: triangular wedge, no taper, cornice on top",
        height=52, base=12, taper=0.08, shape="triangle", crown="flat",
        main="brown_terracotta", accent="smooth_sandstone")
    add("willis_tower", "Willis Tower", "Уиллис-тауэр",
        [("willis",), ("sears",), ("уиллис",), ("сирс",)], T,
        "Chicago: bundled black tubes stepping back, two antennas",
        height=104, base=12, taper=0.3, setbacks=4, crown="flat", spire=14,
        main="black_concrete", accent="gray_concrete")
    add("space_needle", "Space Needle", "Спейс-Нидл",
        [("space", "needle"), ("спейс", "нидл")], T,
        "Seattle: slim tripod shaft with a flying-saucer observation deck",
        height=72, base=5, taper=0.3, shape="round", crown="saucer", spire=14,
        main="white_concrete", accent="orange_concrete")
    add("burj_khalifa", "Burj Khalifa", "Бурдж-Халифа",
        [("burj", "khalifa"), ("бурдж", "халиф"), ("халифа",)], T,
        "Dubai: spiralling setbacks narrowing to the world's tallest spire",
        height=130, base=12, taper=0.72, setbacks=7, crown="flat", spire=26,
        main="light_gray_concrete", accent="light_blue_stained_glass")
    add("shanghai_tower", "Shanghai Tower", "Шанхайская башня",
        [("shanghai",), ("шанхай",)], T,
        "Shanghai: round glass shaft twisted through 120 degrees",
        height=118, base=11, taper=0.42, shape="round", twist=120, crown="flat",
        main="light_blue_stained_glass", accent="white_concrete")
    add("taipei_101", "Taipei 101", "Тайбэй 101",
        [("taipei",), ("тайбэй",), ("тайпей",), ("101",)], T,
        "Taipei: eight stacked pagoda sections flaring outward, pinnacle",
        height=100, base=10, taper=-0.08, setbacks=8, crown="pyramid", spire=20,
        main="cyan_concrete", accent="light_blue_stained_glass")
    add("petronas_towers", "Petronas Towers", "Башни Петронас",
        [("petronas",), ("петронас",)], T,
        "Kuala Lumpur: twin octagonal towers joined by a skybridge, ringed crowns",
        height=94, base=8, taper=0.38, shape="octagon", crown="pyramid", spire=14, twin=1,
        main="light_gray_concrete", accent="light_blue_stained_glass")
    add("the_shard", "The Shard", "Осколок",
        [("shard",), ("шард",), ("осколок",)], T,
        "London: splintered glass pyramid of sloping facets, open top",
        height=100, base=12, taper=0.8, shape="triangle", crown="flat", spire=10,
        main="light_blue_stained_glass", accent="white_concrete")
    add("gherkin", "30 St Mary Axe", "Корнишон",
        [("gherkin",), ("корнишон",), ("огурец",), ("mary", "axe")], T,
        "London: bulging glass barrel with a diamond grid and rounded top",
        height=68, base=9, taper=0.55, shape="round", barrel=0.5, crown="dome", bands=8,
        main="light_blue_stained_glass", accent="green_concrete")
    add("lotte_world_tower", "Lotte World Tower", "Лотте-Ворлд-Тауэр",
        [("lotte",), ("лотте",)], T,
        "Seoul: smooth tapering cone split by a vertical seam, lit spire",
        height=112, base=10, taper=0.62, shape="round", crown="flat", spire=20,
        main="white_concrete", accent="light_blue_stained_glass")
    add("cn_tower", "CN Tower", "Си-Эн Тауэр",
        [("cn", "tower"), ("си", "эн"), ("торонто",), ("toronto",)], T,
        "Toronto: slender concrete shaft, round observation pod, long mast",
        height=108, base=5, taper=0.45, shape="round", pod=0.66, crown="flat", spire=26,
        main="light_gray_concrete", accent="white_concrete")
    add("ostankino_tower", "Ostankino Tower", "Останкинская башня",
        [("останкин",), ("ostankino",)], T,
        "Moscow: tapering concrete needle with a ringed restaurant pod",
        height=116, base=6, taper=0.6, shape="round", pod=0.55, crown="flat", spire=24,
        main="white_concrete", accent="red_concrete")
    add("tokyo_tower", "Tokyo Tower", "Токийская башня",
        [("tokyo", "tower"), ("токийская", "башня"), ("токио",)], T,
        "Tokyo: red and white lattice tower with two decks and a mast",
        height=86, base=12, taper=0.72, crown="lattice", spire=18, bands=9,
        main="red_concrete", accent="white_concrete")
    add("lakhta_center", "Lakhta Center", "Лахта-центр",
        [("лахта",), ("lakhta",)], T,
        "Saint Petersburg: twisted glass flame tapering to a point",
        height=120, base=10, taper=0.78, shape="pentagon", twist=90, crown="flat", spire=16,
        main="light_blue_stained_glass", accent="white_concrete")
    add("federation_tower", "Federation Tower", "Башня Федерация",
        [("федерация",), ("federation",), ("москва", "сити"), ("moscow", "city")], T,
        "Moscow City: sheer glass slab tapering to a flat top",
        height=106, base=10, taper=0.55, shape="triangle", crown="flat", spire=12,
        main="light_blue_stained_glass", accent="gray_concrete")
    add("stalin_highrise", "Seven Sisters tower", "Сталинская высотка",
        [("высотка",), ("сталинск",), ("мгу",), ("seven", "sisters"), ("гостиница", "украина")], T,
        "Moscow: wedding-cake setbacks, tiered crown and a gilded spire",
        height=98, base=14, taper=0.62, setbacks=6, crown="pyramid", spire=22,
        main="smooth_sandstone", accent="light_gray_concrete")
    add("kyiv_tv_tower", "Kyiv TV Tower", "Киевская телебашня",
        [("телебашн",), ("tv", "tower"), ("телевышк",)], T,
        "Kyiv: free-standing steel lattice needle, no guy wires",
        height=112, base=11, taper=0.8, crown="lattice", spire=20,
        main="iron_block", accent="gray_concrete")
    add("hotel_tower", "Grand hotel tower", "Башня-отель",
        [("небоскрёб", "отель"), ("башня", "отел"), ("grand", "hotel"), ("hotel", "tower")], T,
        "slab hotel tower with a rooftop terrace and glass bands",
        height=74, base=11, taper=0.2, crown="flat", bands=6,
        main="smooth_sandstone", accent="light_blue_stained_glass")
    add("office_tower", "Office tower", "Офисная башня",
        [("офисн", "башн"), ("office", "tower"), ("бизнес", "центр")], T,
        "plain modern office tower: glass curtain wall, flat roof",
        height=70, base=10, taper=0.15, crown="flat", bands=5,
        main="gray_concrete", accent="light_blue_stained_glass")
    add("twin_towers", "Twin towers", "Башни-близнецы",
        [("близнец",), ("twin", "towers"), ("twins",)], T,
        "two identical square towers side by side with a skybridge",
        height=96, base=9, taper=0.1, crown="flat", spire=8, twin=1,
        main="light_gray_concrete", accent="light_blue_stained_glass")
    add("pencil_tower", "Pencil tower", "Башня-карандаш",
        [("карандаш",), ("pencil",), ("supertall",), ("суперстройн",)], T,
        "ultra-slim residential needle, very small footprint",
        height=120, base=5, taper=0.25, crown="flat", spire=12,
        main="smooth_quartz", accent="black_concrete")
    add("brutalist_tower", "Brutalist tower", "Брутализм",
        [("брутал",), ("brutalist",), ("панельк",), ("хрущёвк",), ("хрущевк",)], T,
        "raw concrete slab block with deep window bands",
        height=56, base=13, taper=0.05, crown="flat", bands=9,
        main="light_gray_concrete", accent="gray_concrete")
    add("pagoda_tower", "Pagoda tower", "Башня-пагода",
        [("пагод", "башн"), ("pagoda", "tower")], T,
        "tiered oriental tower with flaring roofs at every level",
        height=78, base=11, taper=0.5, setbacks=7, crown="pyramid", spire=10,
        main="red_terracotta", accent="gold_block")
    add("observation_tower", "Observation tower", "Смотровая башня",
        [("смотров", "башн"), ("observation",), ("обзорн", "башн")], T,
        "slim shaft with a wide glazed observation deck near the top",
        height=80, base=6, taper=0.35, shape="round", pod=0.72, crown="dome",
        main="white_concrete", accent="light_blue_stained_glass")

    # --- античность и колоннады -------------------------------------------
    P = K.temple
    add("parthenon", "Parthenon", "Парфенон",
        [("парфенон",), ("parthenon",), ("акропол",), ("acropolis",)], P,
        "Athens: marble peripteral temple, fluted columns, pediments",
        width=42, depth=24, columns=10, col_h=17, steps=4, statue=1)
    add("greek_temple", "Greek temple", "Греческий храм",
        [("греческ", "храм"), ("greek", "temple"), ("антич", "храм")], P,
        "classical Greek temple with a colonnade and gabled pediment",
        width=32, depth=20, columns=8, col_h=14, steps=3)
    add("roman_temple", "Roman temple", "Римский храм",
        [("римск", "храм"), ("roman", "temple"), ("форум",), ("forum",)], P,
        "Roman temple on a high podium, deep portico",
        width=28, depth=22, columns=6, col_h=15, steps=6,
        main="smooth_sandstone", accent="cut_sandstone")
    add("lincoln_memorial", "Lincoln Memorial", "Мемориал Линкольна",
        [("lincoln",), ("линкольн",)], P,
        "Washington: broad colonnade on a tall stepped base, flat roof",
        width=46, depth=28, columns=12, col_h=16, steps=7, roof_style="flat", statue=1)
    add("supreme_court", "Courthouse", "Здание суда",
        [("суд",), ("courthouse",), ("supreme", "court"), ("судебн",)], P,
        "neoclassical courthouse: columned portico, wings, pediment",
        width=34, depth=22, columns=8, col_h=15, steps=5, wings=1)
    add("museum", "Museum", "Музей",
        [("музей",), ("museum",), ("галере",), ("gallery",)], P,
        "museum: colonnade, side wings, grand steps",
        width=38, depth=24, columns=10, col_h=15, steps=5, wings=1,
        main="smooth_sandstone", accent="quartz_block")
    add("library", "Library", "Библиотека",
        [("библиотек",), ("library",)], P,
        "public library: columned front, long reading wings",
        width=34, depth=26, columns=8, col_h=14, steps=4, wings=1,
        main="quartz_block", accent="smooth_stone")
    add("opera_house", "Opera house", "Оперный театр",
        [("опер",), ("opera",), ("театр",), ("theatre",), ("theater",)], P,
        "opera house: portico with columns, hip roof, side wings",
        width=38, depth=26, columns=8, col_h=16, steps=5, wings=1, roof_style="hip",
        main="smooth_sandstone", accent="green_concrete")
    add("city_hall", "City hall", "Ратуша",
        [("ратуш",), ("city", "hall"), ("мэри",), ("town", "hall")], P,
        "city hall: colonnaded front, hip roof, clock over the entrance",
        width=32, depth=22, columns=8, col_h=14, steps=4, roof_style="hip", wings=1)
    add("bank", "Bank", "Банк",
        [("банк",), ("bank",), ("биржа",), ("exchange",)], P,
        "bank: heavy columns, stone facade, flat roof",
        width=30, depth=20, columns=8, col_h=15, steps=5, roof_style="flat",
        main="smooth_stone", accent="polished_andesite")

    # --- купола -------------------------------------------------------------
    D = K.domed
    add("us_capitol", "United States Capitol", "Капитолий",
        [("капитоли",), ("capitol",)], D,
        "Washington: white dome on a colonnaded drum, two long wings, portico",
        body=34, body_h=18, drum=14, drum_h=13, dome_r=14, wings=1, portico=1)
    add("st_peters", "St Peter's Basilica", "Собор Святого Петра",
        [("святого", "петра"), ("peter", "basilica"), ("ватикан",), ("vatican",)], D,
        "Rome: vast basilica, ribbed dome on a colonnaded drum, lantern",
        body=40, body_h=22, drum=16, drum_h=16, dome_r=17, wings=1,
        main="smooth_sandstone", accent="quartz_block")
    add("pantheon", "Pantheon", "Пантеон",
        [("пантеон",), ("pantheon",)], D,
        "Rome: cylindrical rotunda under a shallow dome with a portico",
        body=30, body_h=14, drum=15, drum_h=4, dome_r=15, wings=0, lantern=0,
        main="smooth_sandstone", accent="red_terracotta")
    add("st_pauls", "St Paul's Cathedral", "Собор Святого Павла",
        [("святого", "павла"), ("paul", "cathedral"), ("st", "pauls")], D,
        "London: baroque dome with a colonnade and golden lantern",
        body=34, body_h=20, drum=13, drum_h=15, dome_r=14, wings=1,
        main="quartz_block", accent="light_gray_concrete")
    add("isaac_cathedral", "Saint Isaac's Cathedral", "Исаакиевский собор",
        [("исаакиев",), ("isaac",)], D,
        "Saint Petersburg: granite colonnades and a gilded dome",
        body=32, body_h=18, drum=12, drum_h=13, dome_r=13, wings=0, portico=1,
        dome_block="gold_block", main="light_gray_concrete", accent="polished_granite")
    add("reichstag", "Reichstag", "Рейхстаг",
        [("рейхстаг",), ("reichstag",), ("бундестаг",)], D,
        "Berlin: stone block with corner towers and a glass dome",
        body=36, body_h=18, drum=11, drum_h=6, dome_r=11, wings=1,
        dome_block="light_blue_stained_glass", main="smooth_stone", accent="light_gray_concrete")
    add("blue_mosque", "Blue Mosque", "Голубая мечеть",
        [("голубая", "мечет"), ("blue", "mosque"), ("айя",), ("hagia",), ("софия", "стамбул")], D,
        "Istanbul: cascading domes and slender minarets",
        body=32, body_h=16, drum=14, drum_h=8, dome_r=15, wings=0, minarets=1,
        main="light_gray_concrete", accent="cyan_concrete", dome_block="cyan_concrete")
    add("jefferson_memorial", "Jefferson Memorial", "Мемориал Джефферсона",
        [("джефферсон",), ("jefferson",), ("ротонд",), ("rotunda",)], D,
        "Washington: open rotunda ringed by columns under a white dome",
        body=24, body_h=12, drum=13, drum_h=5, dome_r=13, wings=0, lantern=0, portico=1,
        main="quartz_block", accent="smooth_quartz")
    add("planetarium", "Planetarium", "Планетарий",
        [("планетари",), ("planetarium",), ("обсерватори",), ("observatory",)], D,
        "planetarium: low drum under a smooth metal dome",
        body=24, body_h=10, drum=14, drum_h=4, dome_r=14, wings=0, lantern=0,
        colonnade=0, main="light_gray_concrete", accent="iron_block",
        dome_block="light_gray_concrete")

    # --- ступенчатые пирамиды ----------------------------------------------
    Y = K.step_pyramid
    add("chichen_itza", "Chichen Itza", "Чичен-Ица",
        [("чичен",), ("chichen",), ("кукулькан",), ("kukulcan",), ("майя",), ("maya",)], Y,
        "Mexico: nine-tier Mayan pyramid, stairs on all four sides, temple on top",
        base=46, tiers=9, tier_h=4, stairs=4)
    add("ziggurat", "Ziggurat", "Зиккурат",
        [("зиккурат",), ("ziggurat",), ("вавилон",), ("babylon",), ("ур",)], Y,
        "Mesopotamia: three massive mud-brick terraces with a front ramp",
        base=52, tiers=3, tier_h=9, stairs=1,
        main="packed_mud", accent="mud_bricks")
    add("teotihuacan", "Pyramid of the Sun", "Пирамида Солнца",
        [("теотиуакан",), ("teotihuacan",), ("солнца", "пирамид"), ("sun", "pyramid")], Y,
        "Mexico: broad five-tier pyramid with one long frontal stairway",
        base=60, tiers=5, tier_h=6, stairs=1, temple_top=1,
        main="cobblestone", accent="andesite")
    add("borobudur", "Borobudur", "Боробудур",
        [("боробудур",), ("borobudur",), ("ступа",), ("stupa",)], Y,
        "Java: round terraces stacked into a bell-shaped stupa mountain",
        base=50, tiers=7, tier_h=4, stairs=4, round_corners=1,
        main="andesite", accent="polished_andesite")
    add("tower_of_babel", "Tower of Babel", "Вавилонская башня",
        [("вавилонск", "башн"), ("babel",), ("спиральн", "башн")], Y,
        "spiral ziggurat climbing in many shrinking tiers",
        base=56, tiers=11, tier_h=4, stairs=0, spiral=1,
        main="smooth_sandstone", accent="cut_sandstone")

    # --- малые формы --------------------------------------------------------
    for id_, en, ru, aliases, fn, about in (
        ("well", "Well", "Колодец",
         [("колодец",), ("колодца",), ("well",)], M.well,
         "stone well with a gabled shelter, bucket on a chain"),
        ("tent", "Circus tent", "Шатёр",
         [("шатер",), ("шатёр",), ("палатк",), ("tent",), ("цирк",), ("circus",), ("marquee",)], M.tent,
         "striped big-top tent with guy ropes, flag and a campfire"),
        ("barn", "Barn", "Амбар",
         [("амбар",), ("barn",), ("сара",), ("хлев",), ("granary",), ("житниц",)], M.barn,
         "red barn with a gambrel roof, big doors, silo, fence and fields"),
        ("water_tower", "Water tower", "Водонапорная башня",
         [("водонапорн",), ("water", "tower"), ("водокачк",)], M.water_tower,
         "water tank on four braced legs with a conical roof and ladder"),
        ("crane", "Tower crane", "Башенный кран",
         [("кран",), ("crane",), ("стройк",), ("construction",)], M.crane,
         "tower crane: lattice mast, jib with counterweight, hook on a chain"),
        ("radio_tower", "Radio mast", "Радиовышка",
         [("радиовышк",), ("радиомачт",), ("radio", "tower"), ("antenna",), ("антенн",),
          ("вышка",), ("мачта",), ("mast",)], M.radio_tower,
         "red and white lattice mast with guy wires, dishes and a beacon"),
        ("gazebo", "Gazebo", "Беседка",
         [("беседк",), ("gazebo",), ("pavilion",), ("павильон",), ("ротонда", "парк")], M.gazebo,
         "octagonal garden gazebo: columns, benches, conical roof, lantern"),
        ("greenhouse_build", "Greenhouse", "Теплица",
         [("теплиц",), ("оранжере",), ("greenhouse",), ("conservatory",)], M.greenhouse,
         "glass greenhouse with white frames, raised beds and a water barrel"),
        ("snowman", "Snowman", "Снеговик",
         [("снеговик",), ("снежная", "баба"), ("snowman",), ("olaf",)], M.snowman,
         "three-ball snowman with a bucket hat, carrot nose, scarf and stick arms"),
        ("hot_air_balloon", "Hot air balloon", "Воздушный шар",
         [("воздушн", "шар"), ("balloon",), ("аэростат",), ("montgolfier",)], M.hot_air_balloon,
         "striped balloon envelope, ropes and a wicker basket on the ground"),
        ("treehouse", "Treehouse", "Домик на дереве",
         [("домик", "дерев"), ("treehouse",), ("на", "дереве")], M.treehouse,
         "cabin on a platform in a big tree, railings, ladder, leafy crown"),
        ("chess_rook", "Chess rook", "Шахматная ладья",
         [("шахмат",), ("ладья",), ("chess",), ("rook",), ("пешк",)], M.chess_rook,
         "giant chess rook on a chequered board: turned profile, battlements"),
        ("maze", "Hedge maze", "Лабиринт",
         [("лабиринт",), ("maze",), ("labyrinth",)], M.maze,
         "hedge maze on a grid with an entrance, an exit and a central fountain"),
        ("pier", "Pier", "Причал",
         [("причал",), ("пирс",), ("pier",), ("dock",), ("пристан",), ("harbour",), ("harbor",)], M.pier,
         "wooden pier on piles with bollards, a lantern and a moored boat"),
        ("pool", "Swimming pool", "Бассейн",
         [("бассейн",), ("pool",), ("аквапарк",), ("waterpark",)], M.pool,
         "swimming pool with lane lines, diving tower, sun loungers and umbrellas"),
        ("farm", "Farm", "Ферма",
         [("ферма",), ("farm",), ("огород",), ("поле",), ("field",), ("пашн",)], M.farm,
         "farm: irrigated crop rows, shed, hay bales, scarecrow and a fence"),
    ):
        register(Entry(id_, en, ru, [tuple(a) for a in aliases], fn, about, tunable=True))


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
    best, best_score = None, 0
    for entry in REGISTRY.values():
        if entry.generic and words > entry.max_words:
            continue          # «красный замок с драконом» — пожелания, пусть думает модель
        for alias in entry.aliases:
            if all(_has_stem(t, part) for part in alias):
                # Побеждает самая точная ловушка, а не первая по порядку: иначе
                # «planetarium» уходило в самолёт («plane» стоит в начале слова),
                # а «пирамида Солнца» — в пирамиду Хеопса.
                score = sum(len(part) for part in alias) + 10 * (len(alias) - 1)
                if score > best_score:
                    best, best_score = entry.id, score
    if best:
        return best
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
    found = params.parse(_without_own_words(entry, request_text))
    if not entry.tunable:
        found.pop("scale", None)      # чужой генератор размера не понимает
    return found


def _without_own_words(entry: Entry, text: str) -> str:
    """Убирает из запроса слова собственного названия здания.

    «Golden Gate Bridge» перекрашивался в золото: слово Golden из его же имени
    срабатывало как цвет, и международный оранжевый превращался в золотой блок.
    То же было бы с «Белым домом» и «Голубой мечетью»."""
    own = {part for alias in entry.aliases for part in alias}
    own |= {w for title in (entry.title_en, entry.title_ru) for w in _text(title).split()}
    kept = []
    for word in _text(text).split():
        if any(word.startswith(o) or o.startswith(word) for o in own if len(o) >= 3):
            continue
        kept.append(word)
    return " ".join(kept)


def title(id: str, request_text: str = "") -> str:
    """Название постройки. По умолчанию английское: показ идёт на английском, даже
    когда человек написал запрос по-русски. SHOW_LANG=ru возвращает прежнее поведение."""
    e = REGISTRY[id]
    if os.getenv("SHOW_LANG", "en").lower().startswith("ru") and re.search("[а-яА-Я]", request_text):
        return e.title_ru
    return e.title_en


def listing() -> str:
    """Список чертежей для подсказки LLM — только те, что годятся как основа.

    Показывать модели все сто с лишним незачем: точное название ловит `match`
    задолго до неё, а лишние три тысячи токенов в каждом запросе её только
    замедляют. Модели нужны образцы, на которых строят вариацию
    («замок с драконом»), поэтому семейства башен и классики сюда не идут."""
    lines = []
    for e in REGISTRY.values():
        if not e.listed:
            continue
        v = build(e.id)
        w, h, d = (max(p[i] for p in v) + 1 for i in range(3))
        lines.append(f'- "{e.id}" ({w}x{h}x{d} blocks): {e.title_en} - {e.about}')
    return "\n".join(lines)


_load()
