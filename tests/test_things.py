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

    def test_параметры_принимают_только_настраиваемые_чертежи(self):
        self.assertEqual(blueprints.params_for("plane", "красный самолёт")["main"], "red_concrete")
        self.assertEqual(blueprints.params_for("eiffel_tower", "красная эйфелева башня"), {})
