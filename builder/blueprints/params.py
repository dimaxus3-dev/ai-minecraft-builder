"""Цвет, размер и материал из самого запроса.

Благодаря этому один чертёж даёт много разных построек: «большой красный самолёт»,
«маленький белый самолёт» и «золотой самолёт» — три разные модели, а не одна и та же.
Слова ищем и по-русски, и по-английски.
"""

from __future__ import annotations

import re

# цвет -> (основной блок, блок-акцент)
COLORS: dict[tuple[str, ...], tuple[str, str]] = {
    ("красн", "алый", "red", "scarlet"): ("red_concrete", "white_concrete"),
    ("син", "голуб", "blue", "cyan", "лазур"): ("blue_concrete", "white_concrete"),
    ("зелён", "зелен", "green", "изумруд", "emerald"): ("green_concrete", "lime_concrete"),
    ("жёлт", "желт", "yellow", "золот", "gold", "golden"): ("yellow_concrete", "gold_block"),
    ("бел", "white", "снежн", "snow"): ("white_concrete", "light_gray_concrete"),
    ("чёрн", "черн", "black", "тёмн", "темн", "dark"): ("black_concrete", "gray_concrete"),
    ("сер", "gray", "grey", "стальн", "steel"): ("light_gray_concrete", "gray_concrete"),
    ("оранж", "orange", "рыж"): ("orange_concrete", "yellow_concrete"),
    ("розов", "pink", "магент", "magenta"): ("pink_concrete", "magenta_concrete"),
    ("фиолет", "purple", "сирен", "violet"): ("purple_concrete", "magenta_concrete"),
    ("коричн", "brown", "бурый"): ("brown_concrete", "brown_terracotta"),
    ("бирюз", "turquoise", "teal"): ("cyan_concrete", "light_blue_concrete"),
}

# материал перебивает цвет: «деревянный корабль», «каменная статуя»
MATERIALS: dict[tuple[str, ...], tuple[str, str]] = {
    ("деревян", "wood", "wooden", "дубов", "oak"): ("oak_planks", "dark_oak_planks"),
    ("камен", "stone", "гранит", "granite"): ("stone_bricks", "polished_andesite"),
    ("кирпич", "brick"): ("bricks", "red_terracotta"),
    ("железн", "iron", "metal", "металл"): ("iron_block", "gray_concrete"),
    ("стекл", "glass", "glassy"): ("light_blue_stained_glass", "white_concrete"),
    ("золот", "gold", "golden"): ("gold_block", "yellow_concrete"),
    ("алмаз", "diamond"): ("diamond_block", "light_blue_concrete"),
    ("изумруд", "emerald"): ("emerald_block", "lime_concrete"),
    ("медн", "copper"): ("weathered_copper", "oxidized_copper"),
    ("мрамор", "marble", "кварц", "quartz"): ("quartz_block", "smooth_quartz"),
    ("песчан", "sandstone", "sand"): ("smooth_sandstone", "cut_sandstone"),
    ("снежн", "snow", "лед", "лёд", "ice"): ("snow_block", "packed_ice"),
    ("обсидиан", "obsidian"): ("obsidian", "blackstone"),
}

# стиль задаёт пару материалов целиком: «viking mansion», «ледяной замок», «неоновый робот»
STYLES: dict[tuple[str, ...], tuple[str, str]] = {
    ("викинг", "viking", "норд", "nordic", "скандинав"): ("spruce_planks", "stone_bricks"),
    ("пират", "pirate", "корсар"): ("dark_oak_planks", "black_concrete"),
    ("готич", "gothic", "вампир", "vampire", "хэллоуин", "halloween"): ("deepslate_bricks", "blackstone"),
    ("футурист", "futuristic", "космич", "space", "sci", "будущ"): ("quartz_block", "light_blue_concrete"),
    ("современ", "modern", "минимал", "minimal"): ("smooth_quartz", "light_gray_concrete"),
    ("античн", "ancient", "римск", "roman", "греч", "greek"): ("smooth_sandstone", "quartz_block"),
    ("пустын", "desert", "египет", "egypt", "египт"): ("smooth_sandstone", "gold_block"),
    ("ледян", "frozen", "зимн", "winter", "арктич", "arctic"): ("packed_ice", "snow_block"),
    ("джунгл", "jungle", "тропич", "tropical"): ("jungle_planks", "mossy_cobblestone"),
    ("адск", "nether", "демон", "demon", "вулкан", "volcano"): ("nether_bricks", "red_nether_bricks"),
    ("неон", "neon", "кибер", "cyber"): ("black_concrete", "cyan_concrete"),
    ("королев", "royal", "царск", "imperial", "императорск"): ("quartz_block", "gold_block"),
    ("военн", "military", "army", "армейск", "камуфляж"): ("green_concrete", "gray_concrete"),
    ("гоноч", "racing", "спортивн", "sport", "супер", "super"): ("red_concrete", "black_concrete"),
    ("лесн", "forest", "эльф", "elven", "друид"): ("oak_planks", "green_concrete"),
    ("стимпанк", "steampunk", "индустриал", "industrial"): ("weathered_copper", "polished_blackstone"),
}

BIG = ("больш", "огромн", "гигант", "великан", "big", "huge", "giant", "massive", "mega", "tall")
SMALL = ("маленьк", "мал", "небольш", "крошеч", "мини", "small", "tiny", "little", "mini")


def _hit(text: str, words) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(w), text) for w in words)


def parse(text: str) -> dict[str, float | str]:
    """Параметры чертежа из запроса. Чего в запросе нет, в ответе нет: чертёж
    останется при своих значениях по умолчанию."""
    low = re.sub(r"[^\w\s]", " ", text.lower().replace("ё", "е"))
    params: dict[str, float | str] = {}

    for words, (main, accent) in STYLES.items():
        if _hit(low, [w.replace("ё", "е") for w in words]):
            params["main"], params["accent"] = main, accent
            break
    else:
        for words, (main, accent) in MATERIALS.items():
            if _hit(low, [w.replace("ё", "е") for w in words]):
                params["main"], params["accent"] = main, accent
                break
        else:
            for words, (main, accent) in COLORS.items():
                if _hit(low, [w.replace("ё", "е") for w in words]):
                    params["main"], params["accent"] = main, accent
                    break

    if _hit(low, BIG):
        params["scale"] = 1.45
    elif _hit(low, SMALL):
        params["scale"] = 0.65
    return params
