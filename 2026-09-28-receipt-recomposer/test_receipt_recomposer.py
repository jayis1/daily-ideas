import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from receipt_recomposer import Item, find_matches, load_items, main, parse_item, parse_money


class ReceiptRecomposerTests(unittest.TestCase):
    def test_parse_money_uses_exact_cents(self):
        self.assertEqual(parse_money("$12.05"), 1205)
        self.assertEqual(parse_money("7.5"), 750)
        self.assertEqual(parse_money("0"), 0)

    def test_parse_money_rejects_ambiguous_or_negative_values(self):
        for value in ("1.234", "-1.00", "1,000", "free"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_money(value)

    def test_parse_item_allows_equals_in_name(self):
        self.assertEqual(parse_item("A=B sign=$3.25"), Item("A=B sign", 325))
        with self.assertRaises(ValueError):
            parse_item("Nameless")
        with self.assertRaises(ValueError):
            parse_item("Coupon=0")

    def test_find_matches_is_stable_and_exact(self):
        items = [Item("Tea", 250), Item("Cake", 375), Item("Book", 750), Item("Pen", 125)]
        matches = find_matches(items, 500)
        self.assertEqual(matches, [(items[1], items[3])])

    def test_duplicate_prices_remain_distinct_items(self):
        items = [Item("Apple", 100), Item("Pear", 100), Item("Tea", 200)]
        self.assertEqual(find_matches(items, 200), [(items[2],), (items[0], items[1])])

    def test_size_bounds_and_limit(self):
        items = [Item("A", 100), Item("B", 100), Item("C", 100)]
        self.assertEqual(find_matches(items, 200, min_items=2, max_items=2, limit=2), [
            (items[0], items[1]),
            (items[0], items[2]),
        ])
        with self.assertRaises(ValueError):
            find_matches(items, 200, min_items=3, max_items=2)

    def test_load_items_ignores_comments_and_reports_line(self):
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "receipt.txt"
            valid.write_text("# lunch\nSoup=4.50\n\nBread=2\n", encoding="utf-8")
            self.assertEqual(load_items(valid), [Item("Soup", 450), Item("Bread", 200)])
            invalid = Path(directory) / "bad.txt"
            invalid.write_text("Tea=2\nBroken\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"bad\.txt:2"):
                load_items(invalid)

    def test_cli_text_and_json_outputs(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--target", "5.00", "Tea=2.50", "Cake=3.75", "Pen=1.25"])
        self.assertEqual(status, 0)
        self.assertIn("Cake ($3.75) + Pen ($1.25)", output.getvalue())

        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--target", "2.50", "--json", "Tea=2.50"])
        self.assertEqual(status, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["matches"][0]["items"][0]["name"], "Tea")

    def test_cli_reports_no_match_successfully(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--target", "9.99", "Tea=2.50"])
        self.assertEqual(status, 0)
        self.assertIn("No exact combinations", output.getvalue())


if __name__ == "__main__":
    unittest.main()
