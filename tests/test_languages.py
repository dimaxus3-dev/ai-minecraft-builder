"""Два языка: здание должно находиться и по-русски, и по-английски.

Проверки появились после живого бага: запрос «lighthouse» строил дом, потому что
корень «house» искали в любом месте слова.
"""

import unittest

from backend import research
from builder import blueprints, osm


class BlueprintMatchTests(unittest.TestCase):
    def test_каждый_чертёж_находится_по_своему_названию(self):
        for entry in blueprints.REGISTRY.values():
            for title in (entry.title_en, entry.title_ru):
                with self.subTest(title=title):
                    self.assertEqual(blueprints.match(title), entry.id)

    def test_корень_ищется_только_с_начала_слова(self):
        self.assertEqual(blueprints.match("lighthouse"), "lighthouse")
        self.assertEqual(blueprints.match("маяк"), "lighthouse")
        self.assertEqual(blueprints.match("house"), "house")
        self.assertEqual(blueprints.match("дом"), "house")

    def test_общее_слово_в_длинном_запросе_отдаём_модели(self):
        self.assertEqual(blueprints.match("замок"), "castle")
        self.assertIsNone(blueprints.match("розовый замок с драконом на крыше"))

    def test_название_чертежа_на_языке_запроса(self):
        self.assertEqual(blueprints.title("lighthouse", "маяк"), "Маяк")
        self.assertEqual(blueprints.title("lighthouse", "lighthouse"), "Lighthouse")


class LanguageTests(unittest.TestCase):
    def test_язык_запроса_выбирает_языки_карты(self):
        self.assertEqual(osm.languages_for("Empire State Building"), "en")
        self.assertEqual(osm.languages_for("Эмпайр стейт билдинг"), "ru,en")
        self.assertEqual(osm.languages_for("Білий дім"), "uk,ru,en")

    def test_язык_запроса_выбирает_языки_справки(self):
        self.assertEqual(research.languages_for("Empire State Building"), ["en"])
        self.assertEqual(research.languages_for("Эмпайр стейт билдинг"), ["ru", "en"])

    def test_имена_здания_с_карты_берутся_из_всех_языков(self):
        found = {"display_name": "Empire State Building, New York",
                 "namedetails": {"name": "Empire State Building",
                                 "name:ru": "Эмпайр-Стейт-Билдинг"}}
        names = osm._names_of(found)
        self.assertIn("эмпайр", names)
        self.assertIn("empire", names)
