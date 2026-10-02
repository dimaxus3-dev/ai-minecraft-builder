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

    def test_показ_идёт_на_английском(self):
        # запрос может быть на любом языке, но в игре и на экране — английский
        self.assertEqual(blueprints.title("lighthouse", "маяк"), "Lighthouse")
        self.assertEqual(blueprints.title("lighthouse", "lighthouse"), "Lighthouse")
        self.assertEqual(blueprints.title("plane", "самолёт"), "Airplane")

    def test_SHOW_LANG_возвращает_русские_названия(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"SHOW_LANG": "ru"}):
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


class CooldownTests(unittest.TestCase):
    """Отказ по ключу не должен стоить минуту на каждом запросе."""

    def setUp(self):
        from backend import ai
        self.ai = ai
        ai._COOLDOWN.clear()
        self.addCleanup(ai._COOLDOWN.clear)

    def test_модель_с_плохим_ключом_уходит_в_простой(self):
        calls = []

        def call(name):
            calls.append(name)
            raise self.ai.AuthError(f"{name}: HTTP 403")

        with self.assertRaises(self.ai.LLMError):
            self.ai._race(["a", "b"], 0.0, call)
        self.assertEqual(sorted(calls), ["a", "b"])
        self.assertGreater(self.ai._cooldown_left("a"), 0)

        # второй запрос не ждёт провайдера вовсе
        calls.clear()
        with self.assertRaises(self.ai.AuthError):
            self.ai._race(["a", "b"], 0.0, call)
        self.assertEqual(calls, [])

    def test_обычная_ошибка_модель_не_отключает(self):
        def call(name):
            raise self.ai.LLMError(f"{name}: битый JSON")

        with self.assertRaises(self.ai.LLMError):
            self.ai._race(["a"], 0.0, call)
        self.assertEqual(self.ai._cooldown_left("a"), 0)
