"""Несколько провайдеров в одной гонке: NVIDIA и Gemini рядом.

Модель называется «провайдер/имя». Без ключа модель молча выпадает из цепочки,
иначе её отсутствие стоило бы ожидания на каждом запросе.
"""

import os
import unittest
from unittest import mock

from backend import ai


class EndpointTests(unittest.TestCase):
    def test_gemini_уходит_к_google(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "тест-ключ"}):
            base, key, name, headers = ai.endpoint_for("google/gemini-3.8-flash")
        self.assertIn("generativelanguage.googleapis.com", base)
        self.assertEqual(name, "gemini-3.8-flash")     # префикс провайдера не отправляем
        self.assertEqual(key, "тест-ключ")
        self.assertEqual(headers["Authorization"], "Bearer тест-ключ")

    def test_псевдоним_gemini_работает_так_же(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "тест-ключ"}):
            base_a, _, name_a, _ = ai.endpoint_for("google/gemini-3.8-flash")
            base_b, _, name_b, _ = ai.endpoint_for("gemini/gemini-3.8-flash")
        self.assertEqual((base_a, name_a), (base_b, name_b))

    def test_остальные_модели_идут_на_основной_endpoint(self):
        with mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "nv"}, clear=False):
            base, key, name, headers = ai.endpoint_for("nvidia/nemotron-3-super-120b-a12b")
        self.assertIn("integrate.api.nvidia.com", base)
        self.assertEqual(name, "nvidia/nemotron-3-super-120b-a12b")   # имя идёт целиком
        self.assertEqual(headers["Authorization"], "Bearer nv")

    def test_без_ключа_модель_не_попадает_в_цепочку(self):
        env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=True):
            _, key, _, _ = ai.endpoint_for("google/gemini-3.8-flash")
        self.assertIsNone(key)

    def test_запрос_без_ключа_это_ошибка_ключа_а_не_таймаут(self):
        env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ai.AuthError):
                ai._chat([{"role": "user", "content": "hi"}], "google/gemini-3.8-flash", 5, 0.4, 10)
