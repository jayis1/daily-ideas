import unittest

from daily_ideas.catalog import App
from daily_ideas.tui import BrowserState


def app(app_id, category="creative"):
    return App(app_id, app_id.title(), f"Description for {app_id}", "2026-01-01",
               f"2026-01-01-{app_id}", f"{app_id}.py", category, "cli")


class BrowserStateTests(unittest.TestCase):
    def setUp(self):
        self.state = BrowserState([
            app("alpha-tool", "utility"),
            app("beta-game", "game"),
            app("gamma-game", "game"),
        ])

    def test_filter_combines_search_and_category(self):
        self.state.category = "game"
        self.state.set_query("gamma")
        self.assertEqual(["gamma-game"], [item.id for item in self.state.filtered])

    def test_move_clamps_to_results(self):
        self.state.move(99)
        self.assertEqual(2, self.state.selected)
        self.state.move(-99)
        self.assertEqual(0, self.state.selected)

    def test_category_cycles_through_all(self):
        self.assertIsNone(self.state.category)
        self.state.cycle_category()
        self.assertEqual("game", self.state.category)
        self.state.cycle_category()
        self.assertEqual("utility", self.state.category)
        self.state.cycle_category()
        self.assertIsNone(self.state.category)

    def test_empty_results_have_no_current_app(self):
        self.state.set_query("missing")
        self.assertIsNone(self.state.current)

    def test_random_selection_stays_in_filter(self):
        self.state.category = "game"
        self.state.choose_random(seed=7)
        self.assertIn(self.state.current.id, {"beta-game", "gamma-game"})
