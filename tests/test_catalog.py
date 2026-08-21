import re
import unittest
from pathlib import Path

from daily_ideas.catalog import load_apps, search, validate_apps

ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = load_apps(ROOT / "src/daily_ideas/apps.json")

    def test_catalog_has_all_canonical_apps(self):
        canonical = {p.name for p in ROOT.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+", p.name)}
        self.assertEqual(canonical, {app.path for app in self.apps})

    def test_catalog_is_valid(self):
        self.assertEqual([], validate_apps(self.apps, ROOT))

    def test_ids_are_unique(self):
        ids = [app.id for app in self.apps]
        self.assertEqual(len(ids), len(set(ids)))

    def test_search(self):
        self.assertIn("ascii-dungeon-generator", {app.id for app in search(self.apps, "dungeon")})
        self.assertEqual([], search(self.apps, "definitely-not-an-app"))
