import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from path_collision_scout import (
    collision_key,
    find_collisions,
    main,
    path_parts,
    read_path_file,
)


class PathCollisionScoutTests(unittest.TestCase):
    def test_splits_both_slash_styles(self):
        self.assertEqual(path_parts(r"Art\Drafts/logo.svg"), ["Art", "Drafts", "logo.svg"])

    def test_rejects_empty_and_traversal_paths(self):
        for value in ("", "./note.txt", "docs/../note.txt"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                path_parts(value)

    def test_default_key_case_folds_and_normalizes_unicode(self):
        composed = collision_key("Caf\N{LATIN SMALL LETTER E WITH ACUTE}.txt")
        decomposed = collision_key("CAFE\N{COMBINING ACUTE ACCENT}.TXT")
        self.assertEqual(composed, decomposed)

    def test_case_sensitive_mode_preserves_case(self):
        self.assertNotEqual(
            collision_key("Logo.svg", case_sensitive=True),
            collision_key("logo.svg", case_sensitive=True),
        )

    def test_flatten_finds_same_basename_in_different_folders(self):
        collisions = find_collisions(["draft/logo.svg", "final/LOGO.svg"], flatten=True)
        self.assertEqual(collisions, {"logo.svg": ["draft/logo.svg", "final/LOGO.svg"]})
        self.assertEqual(find_collisions(["draft/logo.svg", "final/logo.svg"]), {})

    def test_portable_mode_trims_component_endings(self):
        paths = ["notes/report.txt", "notes/report.txt. "]
        self.assertEqual(list(find_collisions(paths, portable=True)), ["notes/report.txt"])
        self.assertEqual(find_collisions(paths), {})
        with self.assertRaises(ValueError):
            collision_key("notes/...", portable=True)

    def test_compatibility_normalization_catches_width_variants(self):
        paths = ["prices/1.txt", "prices/\N{FULLWIDTH DIGIT ONE}.txt"]
        self.assertEqual(find_collisions(paths), {})
        self.assertEqual(list(find_collisions(paths, normalization="NFKC")), ["prices/1.txt"])

    def test_path_file_ignores_blanks_and_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "paths.txt"
            source.write_text("# export\nA.txt\n\n a.TXT \n", encoding="utf-8")
            self.assertEqual(read_path_file(source), ["A.txt", "a.TXT"])

    def test_cli_text_reports_collision_and_nonzero_status(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--flatten", "draft/logo.svg", "final/LOGO.svg"])
        self.assertEqual(status, 1)
        self.assertIn("Found 1 collision across 2 paths", output.getvalue())
        self.assertIn("<- draft/logo.svg", output.getvalue())

    def test_cli_json_no_collision(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--json", "one.txt", "two.txt"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), {
            "paths_checked": 2,
            "collision_count": 0,
            "collisions": [],
        })


if __name__ == "__main__":
    unittest.main()
