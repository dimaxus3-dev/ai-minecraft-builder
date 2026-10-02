"""Палитра блоков.

Мы НЕ даём LLM ставить любой блок: берём только проверенный список,
который точно существует в Minecraft 1.21.4. Всё неизвестное становится stone.
Так постройка никогда не ломается из-за выдуманного id (и из-за блоков
из версий новее 1.21.4).

PALETTE_BY_GROUP нужен ещё и для промпта LLM на Фазе 2: список блоков
отдаём модели как есть, чтобы она выбирала из него.
"""

FALLBACK = "stone"

PALETTE_BY_GROUP: dict[str, list[str]] = {
    "камень": [
        "stone", "cobblestone", "mossy_cobblestone", "stone_bricks",
        "mossy_stone_bricks", "cracked_stone_bricks", "chiseled_stone_bricks",
        "smooth_stone", "andesite", "polished_andesite", "diorite",
        "polished_diorite", "granite", "polished_granite", "deepslate",
        "polished_deepslate", "deepslate_bricks", "deepslate_tiles",
        "cobbled_deepslate", "tuff", "polished_tuff", "calcite", "basalt",
        "smooth_basalt", "blackstone", "polished_blackstone",
        "polished_blackstone_bricks", "gilded_blackstone", "obsidian",
        "bedrock", "mud_bricks", "packed_mud",
    ],
    "кирпич_и_песчаник": [
        "bricks", "sandstone", "smooth_sandstone", "cut_sandstone",
        "chiseled_sandstone", "red_sandstone", "smooth_red_sandstone",
        "cut_red_sandstone", "nether_bricks", "red_nether_bricks",
        "chiseled_nether_bricks", "quartz_block", "smooth_quartz",
        "chiseled_quartz_block", "quartz_bricks", "quartz_pillar",
        "purpur_block", "purpur_pillar", "end_stone", "end_stone_bricks",
        "prismarine", "prismarine_bricks", "dark_prismarine", "sea_lantern",
    ],
    "дерево": [
        "oak_planks", "spruce_planks", "birch_planks", "jungle_planks",
        "acacia_planks", "dark_oak_planks", "mangrove_planks",
        "cherry_planks", "bamboo_planks", "bamboo_mosaic", "crimson_planks",
        "warped_planks", "oak_log", "spruce_log", "birch_log", "jungle_log",
        "acacia_log", "dark_oak_log", "cherry_log", "mangrove_log",
        "stripped_oak_log", "stripped_spruce_log", "stripped_birch_log",
        "stripped_dark_oak_log", "oak_leaves", "spruce_leaves",
        "birch_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves",
        "cherry_leaves", "azalea_leaves",
    ],
    "бетон": [
        "white_concrete", "orange_concrete", "magenta_concrete",
        "light_blue_concrete", "yellow_concrete", "lime_concrete",
        "pink_concrete", "gray_concrete", "light_gray_concrete",
        "cyan_concrete", "purple_concrete", "blue_concrete", "brown_concrete",
        "green_concrete", "red_concrete", "black_concrete",
    ],
    "шерсть": [
        "white_wool", "orange_wool", "magenta_wool", "light_blue_wool",
        "yellow_wool", "lime_wool", "pink_wool", "gray_wool",
        "light_gray_wool", "cyan_wool", "purple_wool", "blue_wool",
        "brown_wool", "green_wool", "red_wool", "black_wool",
    ],
    "терракота": [
        "terracotta", "white_terracotta", "orange_terracotta",
        "light_blue_terracotta", "yellow_terracotta", "lime_terracotta",
        "gray_terracotta", "light_gray_terracotta", "cyan_terracotta",
        "purple_terracotta", "blue_terracotta", "brown_terracotta",
        "green_terracotta", "red_terracotta", "black_terracotta",
    ],
    "стекло": [
        "glass", "tinted_glass", "white_stained_glass",
        "light_blue_stained_glass", "yellow_stained_glass",
        "lime_stained_glass", "cyan_stained_glass", "blue_stained_glass",
        "purple_stained_glass", "red_stained_glass", "green_stained_glass",
        "orange_stained_glass", "pink_stained_glass", "gray_stained_glass",
        "black_stained_glass", "brown_stained_glass",
        "magenta_stained_glass", "light_gray_stained_glass",
    ],
    "металл_и_блеск": [
        "iron_block", "gold_block", "diamond_block", "emerald_block",
        "lapis_block", "redstone_block", "netherite_block", "copper_block",
        "exposed_copper", "weathered_copper", "oxidized_copper",
        "cut_copper", "raw_iron_block", "raw_gold_block", "raw_copper_block",
        "amethyst_block", "bone_block",
    ],
    "свет": [
        "glowstone", "shroomlight", "ochre_froglight", "verdant_froglight",
        "pearlescent_froglight", "redstone_lamp", "magma_block",
        "jack_o_lantern", "crying_obsidian", "beacon", "lantern",
        "soul_lantern", "torch", "end_rod",
    ],
    "природа": [
        "dirt", "coarse_dirt", "rooted_dirt", "grass_block", "podzol",
        "mycelium", "sand", "red_sand", "gravel", "clay", "mud",
        "snow_block", "packed_ice", "blue_ice", "ice", "moss_block",
        "hay_block", "pumpkin", "melon", "water", "lava", "air",
        "dripstone_block", "sculk", "netherrack", "soul_sand", "soul_soil",
    ],
}

# Плоский список для быстрой проверки
PALETTE: set[str] = {b for group in PALETTE_BY_GROUP.values() for b in group}

# Частые ошибки LLM: что она пишет -> что есть в игре
ALIASES: dict[str, str] = {
    "wood": "oak_planks",
    "planks": "oak_planks",
    "wooden_planks": "oak_planks",
    "log": "oak_log",
    "leaves": "oak_leaves",
    "concrete": "light_gray_concrete",
    "wool": "white_wool",
    "brick": "bricks",
    "brick_block": "bricks",
    "stone_brick": "stone_bricks",
    "glass_block": "glass",
    "glass_pane": "glass",
    "cobble": "cobblestone",
    "steel_block": "iron_block",
    "metal_block": "iron_block",
    "copper": "copper_block",
    "gold": "gold_block",
    "iron": "iron_block",
    "diamond": "diamond_block",
    "emerald": "emerald_block",
    "lapis_lazuli_block": "lapis_block",
    "quartz": "quartz_block",
    "sand_stone": "sandstone",
    "glow_stone": "glowstone",
    "light": "glowstone",
    "lamp": "redstone_lamp",
    "snow": "snow_block",
    "hay": "hay_block",
    "grass": "grass_block",
    "stone_slab": "smooth_stone",
    "road": "gray_concrete",
    "asphalt": "gray_concrete",
    "marble": "quartz_block",
    "white_marble": "smooth_quartz",
    "steel": "iron_block",
    "cable": "orange_concrete",
    "rope": "brown_wool",
}


def normalize(block: str | None) -> str:
    """Приводит id блока к безопасному виду из палитры.

    'minecraft:Stone_Bricks' -> 'stone_bricks', 'unobtainium' -> 'stone'.
    """
    if not block:
        return FALLBACK
    name = str(block).strip().lower()
    if ":" in name:                    # minecraft:stone -> stone
        name = name.split(":")[-1]
    name = name.replace(" ", "_").replace("-", "_")
    if name in PALETTE:
        return name
    if name in ALIASES:
        return ALIASES[name]
    return FALLBACK


def palette_for_prompt() -> str:
    """Палитра одной строкой на группу — для системного промпта LLM."""
    return "\n".join(
        f"{group}: {', '.join(blocks)}"
        for group, blocks in PALETTE_BY_GROUP.items()
    )
