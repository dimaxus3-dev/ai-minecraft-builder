"""Библиотека предметов: всё собирается, влезает в мир и слушается запроса."""

import unittest

from builder import blueprints
from builder.blueprints import params
from builder.schema import MAX_COORD


class BuildTests(unittest.TestCase):
    def test_каждый_чертёж_собирается_и_влезает(self):
        for entry in blueprints.REGISTRY.values():
            with self.subTest(id=entry.id):
                voxels = blueprints.build(entry.id)
                self.assertGreater(len(voxels), 200, "подозрительно пусто")
                for axis in range(3):
                    self.assertLess(max(p[axis] for p in voxels), MAX_COORD)

    def test_предметы_узнаются_на_двух_языках(self):
        for text, expected in (
            ("самолёт", "plane"), ("plane", "plane"), ("боинг", "plane"),
            ("корабль", "ship"), ("sailing ship", "ship"), ("титаник", "ship"),
            ("ракета", "rocket"), ("rocket", "rocket"),
            ("поезд", "train"), ("locomotive", "train"),
            ("машина", "car"), ("car", "car"),
            ("танк", "tank"), ("tank", "tank"),
            ("робот", "robot"), ("robot", "robot"),
            ("колесо обозрения", "ferris_wheel"), ("ferris wheel", "ferris_wheel"),
            ("фонтан", "fountain"), ("fountain", "fountain"),
            ("статуя", "statue"), ("statue", "statue"),
            ("стадион", "stadium"), ("arena", "stadium"),
            ("дерево", "tree"), ("tree", "tree"),
        ):
            with self.subTest(text=text):
                self.assertEqual(blueprints.match(text), expected)


class ParamTests(unittest.TestCase):
    def test_цвет_и_размер_из_запроса(self):
        self.assertEqual(params.parse("большой красный самолёт"),
                         {"main": "red_concrete", "accent": "white_concrete", "scale": 1.45})
        self.assertEqual(params.parse("small white plane")["scale"], 0.65)
        self.assertEqual(params.parse("деревянный корабль")["main"], "oak_planks")
        self.assertEqual(params.parse("самолёт"), {})

    def test_материал_важнее_цвета(self):
        # «золотой» — и цвет, и материал; побеждает материал
        self.assertEqual(params.parse("золотая статуя")["main"], "gold_block")

    def test_разные_запросы_дают_разные_постройки(self):
        red = blueprints.build("plane", {"main": "red_concrete"})
        white = blueprints.build("plane", {})
        self.assertNotEqual(sorted(set(red.values())), sorted(set(white.values())))
        big = blueprints.build("plane", {"scale": 1.45})
        self.assertGreater(len(big), len(white))

    def test_цвет_работает_и_там_где_генератор_о_нём_не_знает(self):
        # свой параметр у самолёта, перекраска готовых блоков у башни
        self.assertEqual(blueprints.params_for("plane", "красный самолёт")["main"], "red_concrete")
        self.assertEqual(blueprints.params_for("eiffel_tower", "золотая эйфелева башня")["main"],
                         "gold_block")
        # размер понимает только тот, кто умеет: чужому генератору его не передаём
        self.assertNotIn("scale", blueprints.params_for("eiffel_tower", "большая эйфелева башня"))
        self.assertIn("scale", blueprints.params_for("plane", "большой самолёт"))


class SoftMatchTests(unittest.TestCase):
    """Любой запрос должен во что-то попадать, а не падать в минутное ожидание."""

    def test_корень_внутри_слова_находит_ближайшее(self):
        self.assertEqual(blueprints.match("Supercar"), "supercar")
        self.assertEqual(blueprints.match("Viking mansion"), "mansion")
        self.assertEqual(blueprints.match("greenhouse"), "greenhouse_build")
        self.assertEqual(blueprints.match("clubhouse"), "house")
        self.assertEqual(blueprints.match("skyscrapers"), "skyscraper")

    def test_короткий_корень_в_мягкий_проход_не_идёт(self):
        # «car» и «дом» слишком коротки, иначе они ловили бы пол-словаря
        self.assertIsNone(blueprints.soft_match("oscar wilde"))
        self.assertIsNone(blueprints.soft_match("бездомный кот"))

    def test_стиль_из_запроса_красит_любой_чертёж(self):
        from collections import Counter
        plain = Counter(blueprints.build("castle").values())
        icy = Counter(blueprints.build("castle", {"main": "packed_ice",
                                                  "accent": "snow_block"}).values())
        self.assertGreater(icy["packed_ice"], 100)
        self.assertEqual(plain["air"], icy["air"])     # форма та же, цвет другой

    def test_стиль_разбирается_из_текста(self):
        self.assertEqual(params.parse("viking mansion")["main"], "spruce_planks")
        self.assertEqual(params.parse("ледяной замок")["main"], "packed_ice")
        self.assertEqual(params.parse("supercar")["main"], "red_concrete")
