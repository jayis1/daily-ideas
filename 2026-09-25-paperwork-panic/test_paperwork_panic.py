import io
import unittest
from contextlib import redirect_stdout

from paperwork_panic import Form, apply_command, make_forms, play, render_board


class PaperworkPanicTests(unittest.TestCase):
    def test_seed_is_repeatable(self):
        self.assertEqual(make_forms(25), make_forms(25))
        self.assertNotEqual(make_forms(25), make_forms(26))

    def test_move_then_stamp(self):
        forms = [Form("Test", "STAMP", "ARCHIVE")]
        message, stamps = apply_command(forms, "move 1 archive", 1)
        self.assertIn("Moved", message)
        self.assertEqual(forms[0].current, "ARCHIVE")
        message, stamps = apply_command(forms, "stamp 1", stamps)
        self.assertIn("Stamped", message)
        self.assertEqual(forms[0].current, "DONE")
        self.assertEqual(stamps, 0)

    def test_invalid_office_does_not_change_form(self):
        forms = [Form("Test", "STAMP", "ARCHIVE")]
        message, stamps = apply_command(forms, "move 1 moon", 1)
        self.assertIn("does not exist", message)
        self.assertEqual(forms[0].current, "STAMP")
        self.assertEqual(stamps, 1)

    def test_demo_board_is_readable(self):
        board = render_board(make_forms(25), 3, 1, 12)
        self.assertIn("PAPERWORK PANIC", board)
        self.assertIn("Commands:", board)

    def test_play_can_win_with_scripted_commands(self):
        forms = make_forms(25)
        commands = []
        for index, form in enumerate(forms, 1):
            commands += [f"move {index} {form.destination.lower()}", f"stamp {index}"]
        commands_iter = iter(commands)
        output = io.StringIO()
        with redirect_stdout(output):
            won = play(25, max_turns=12, input_fn=lambda _prompt: next(commands_iter))
        self.assertTrue(won)
        self.assertIn("ALL FORMS APPROVED", output.getvalue())


if __name__ == "__main__":
    unittest.main()
