"""Tests de l'écriture atomique (autosave, file d'attente, sauvegarde de projet)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_utils import atomic_write_json, atomic_write_text


class AtomicWriteTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "data.json")

    def tearDown(self):
        self.dir.cleanup()

    def _read(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def test_creates_and_overwrites(self):
        atomic_write_json(self.path, {"a": 1})
        self.assertEqual(self._read(), {"a": 1})
        atomic_write_json(self.path, {"a": 2, "texte": "é à ç"})
        self.assertEqual(self._read(), {"a": 2, "texte": "é à ç"})
        self.assertEqual(os.listdir(self.dir.name), ["data.json"])  # pas de .tmp qui traîne

    def test_unserializable_data_keeps_old_file(self):
        atomic_write_json(self.path, {"ok": True})
        with self.assertRaises(TypeError):
            atomic_write_json(self.path, {"bad": object()})
        self.assertEqual(self._read(), {"ok": True})
        self.assertEqual(os.listdir(self.dir.name), ["data.json"])

    def test_failure_during_replace_keeps_old_file_and_cleans_tmp(self):
        atomic_write_json(self.path, {"ok": True})
        with mock.patch("app_utils.os.replace", side_effect=OSError("disque plein")):
            with self.assertRaises(OSError):
                atomic_write_text(self.path, json.dumps({"new": 1}))
        self.assertEqual(self._read(), {"ok": True})
        self.assertEqual(os.listdir(self.dir.name), ["data.json"])

    def test_failure_during_write_keeps_old_file_and_cleans_tmp(self):
        atomic_write_json(self.path, {"ok": True})
        with mock.patch("app_utils.os.fsync", side_effect=OSError("erreur E/S")):
            with self.assertRaises(OSError):
                atomic_write_text(self.path, json.dumps({"new": 1}))
        self.assertEqual(self._read(), {"ok": True})
        self.assertEqual(os.listdir(self.dir.name), ["data.json"])

    def test_indent_option(self):
        atomic_write_json(self.path, {"a": 1}, indent=4)
        with open(self.path, encoding="utf-8") as f:
            self.assertIn('\n    "a": 1', f.read())


if __name__ == "__main__":
    unittest.main()
