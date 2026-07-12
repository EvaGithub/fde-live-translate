import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app import app
from lib.cache import TwoTierCache
from lib.llm import translate_text


class TranslateErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_translate_text_propagates_provider_errors(self):
        client = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("boom"))))
        with patch("lib.llm._get_client", return_value=client):
            with self.assertRaises(RuntimeError):
                asyncio.run(translate_text("Hello", "es-MX", model="claude-sonnet-5"))

    def test_cache_init_creates_parent_directory_for_sqlite_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "nested", "translations.db")
            cache = TwoTierCache(db_path)
            asyncio.run(cache.init())
            self.assertTrue(os.path.exists(db_path))

    def test_translate_returns_400_for_empty_input(self):
        response = self.client.post("/translate", json={"text": "   ", "target": "es-MX"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid input"})

    def test_translate_returns_502_when_upstream_translation_fails(self):
        with patch("app.translate_one", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            response = self.client.post("/translate", json={"text": "Hello", "target": "es-MX"})

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.json())


if __name__ == "__main__":
    unittest.main()
