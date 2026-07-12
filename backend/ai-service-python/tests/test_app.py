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

    def test_batch_uses_single_llm_call_and_preserves_order(self):
        # A batch of misses must go out in ONE translate_batch_text call, and the
        # results must line up 1:1 with the inputs in the same order.
        batch = AsyncMock(return_value=["uno", "dos", "tres"])
        with patch("app.cache.get", new_callable=AsyncMock, return_value=None), \
             patch("app.cache.set", new_callable=AsyncMock), \
             patch("app.translate_batch_text", batch):
            response = self.client.post(
                "/translate/batch", json={"texts": ["one", "two", "three"], "target": "es-MX"}
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([r["translated"] for r in body["results"]], ["uno", "dos", "tres"])
        self.assertTrue(all(r["cached"] is False for r in body["results"]))
        batch.assert_awaited_once()  # exactly one LLM call for the whole batch

    def test_batch_falls_back_to_per_string_on_malformed_response(self):
        # If the single-call batch raises (e.g. bad count), we fall back to
        # per-string translation rather than failing the whole page.
        with patch("app.cache.get", new_callable=AsyncMock, return_value=None), \
             patch("app.cache.set", new_callable=AsyncMock), \
             patch("app.translate_batch_text", new_callable=AsyncMock, side_effect=ValueError("count mismatch")), \
             patch("app.translate_text", new_callable=AsyncMock, side_effect=lambda t, *a, **k: t.upper()):
            response = self.client.post(
                "/translate/batch", json={"texts": ["a", "b"], "target": "es-MX"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["translated"] for r in response.json()["results"]], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
