#!/usr/bin/env python3
"""Tests for the Terminal Enigma Machine."""

import json
import os
import tempfile
import unittest
from enigma import (
    EnigmaMachine, Rotor, Reflector, Plugboard,
    char_to_index, index_to_char,
    random_config, format_output, format_trace, format_full_trace,
    visualize_rotors, visualize_signal_path,
    ROTOR_WIRINGS, REFLECTOR_WIRINGS, ROTOR_NOTCHES,
    __version__,
)


class TestHelpers(unittest.TestCase):
    def test_char_to_index(self):
        self.assertEqual(char_to_index("A"), 0)
        self.assertEqual(char_to_index("Z"), 25)
        self.assertEqual(char_to_index("a"), 0)

    def test_index_to_char(self):
        self.assertEqual(index_to_char(0), "A")
        self.assertEqual(index_to_char(25), "Z")

    def test_index_to_char_wrapping(self):
        """index_to_char should wrap around for values >= 26."""
        self.assertEqual(index_to_char(26), "A")
        self.assertEqual(index_to_char(27), "B")

    def test_round_trip(self):
        for i in range(26):
            self.assertEqual(char_to_index(index_to_char(i)), i)

    def test_version_defined(self):
        """Version should be a non-empty string."""
        self.assertIsInstance(__version__, str)
        self.assertTrue(len(__version__) > 0)
        # Should be semver-like
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)


class TestPlugboard(unittest.TestCase):
    def test_identity(self):
        pb = Plugboard()
        for i in range(26):
            self.assertEqual(pb.encode(i), i)

    def test_single_pair(self):
        pb = Plugboard(["AB"])
        self.assertEqual(pb.encode(0), 1)  # A→B
        self.assertEqual(pb.encode(1), 0)  # B→A
        self.assertEqual(pb.encode(2), 2)  # C→C

    def test_multiple_pairs(self):
        pb = Plugboard(["AB", "CD", "EF"])
        self.assertEqual(pb.encode(0), 1)
        self.assertEqual(pb.encode(1), 0)
        self.assertEqual(pb.encode(2), 3)
        self.assertEqual(pb.encode(3), 2)
        self.assertEqual(pb.encode(4), 5)
        self.assertEqual(pb.encode(5), 4)
        self.assertEqual(pb.encode(6), 6)

    def test_involution(self):
        """Plugboard should be its own inverse."""
        pb = Plugboard(["AB", "CD", "YZ"])
        for i in range(26):
            self.assertEqual(pb.encode(pb.encode(i)), i)

    def test_duplicate_letter_rejected(self):
        """A letter appearing in multiple pairs should be rejected."""
        with self.assertRaises(ValueError):
            Plugboard(["AB", "AC"])  # A appears twice

    def test_self_swap_rejected(self):
        """A pair swapping a letter with itself should be rejected."""
        with self.assertRaises(ValueError):
            Plugboard(["AA"])

    def test_invalid_pair_length_rejected(self):
        """Pairs that are not exactly 2 letters should be rejected."""
        with self.assertRaises(ValueError):
            Plugboard(["A"])  # too short
        with self.assertRaises(ValueError):
            Plugboard(["ABC"])  # too long

    def test_non_alpha_pair_rejected(self):
        """Pairs with non-alpha characters should be rejected."""
        with self.assertRaises(ValueError):
            Plugboard(["12"])  # numeric

    def test_case_insensitive_pairs(self):
        """Lowercase pairs should be handled (converted to uppercase)."""
        pb = Plugboard(["ab"])
        self.assertEqual(pb.encode(0), 1)  # A→B
        self.assertEqual(pb.encode(1), 0)  # B→A

    def test_is_identity(self):
        """is_identity should return True for empty plugboard."""
        pb_empty = Plugboard()
        self.assertTrue(pb_empty.is_identity())
        pb_with_pairs = Plugboard(["AB"])
        self.assertFalse(pb_with_pairs.is_identity())

    def test_pairs_stored(self):
        """Plugboard should store its pairs for later retrieval."""
        pb = Plugboard(["AB", "CD"])
        self.assertEqual(pb.pairs, ["AB", "CD"])

    def test_repr(self):
        """Plugboard repr should be informative."""
        pb_identity = Plugboard()
        self.assertEqual(repr(pb_identity), "Plugboard(identity)")
        pb = Plugboard(["AB"])
        self.assertIn("AB", repr(pb))


class TestRotor(unittest.TestCase):
    def test_creation(self):
        rotor = Rotor("I", "A", 1)
        self.assertEqual(rotor.name, "I")
        self.assertEqual(rotor.position, 0)

    def test_position_setting(self):
        rotor = Rotor("I", "C", 1)
        self.assertEqual(rotor.position, 2)

    def test_ring_setting(self):
        rotor = Rotor("I", "A", 2)
        self.assertEqual(rotor.ring_setting, 1)  # 0-indexed

    def test_step(self):
        rotor = Rotor("I", "A", 1)
        rotor.step()
        self.assertEqual(rotor.position, 1)
        self.assertEqual(rotor.get_position_char(), "B")

    def test_step_wraps(self):
        rotor = Rotor("I", "Z", 1)
        rotor.step()
        self.assertEqual(rotor.position, 0)
        self.assertEqual(rotor.get_position_char(), "A")

    def test_notch_detection(self):
        # Rotor I has a notch at Q
        rotor = Rotor("I", "P", 1)  # one step before Q
        at_notch_before = index_to_char(rotor.position) in rotor.notch_positions
        self.assertFalse(at_notch_before)
        rotor.step()
        at_notch_after = index_to_char(rotor.position) in rotor.notch_positions
        self.assertTrue(at_notch_after)

    def test_unknown_rotor_raises(self):
        with self.assertRaises(ValueError):
            Rotor("X", "A", 1)

    def test_encode_right_to_left_identity_position(self):
        """At position A with ring setting 1, encoding should match the wiring."""
        rotor = Rotor("I", "A", 1)
        # Rotor I: EKMFLGDQVZNTOWYHXUSPAIBRCJ
        # A(0) → E(4)
        self.assertEqual(rotor.encode_right_to_left(0), 4)
        # B(1) → K(10)
        self.assertEqual(rotor.encode_right_to_left(1), 10)

    def test_encode_left_to_right(self):
        """Reverse path through the rotor."""
        rotor = Rotor("I", "A", 1)
        # Forward: A(0) → E(4), so Reverse: E(4) → A(0)
        self.assertEqual(rotor.encode_left_to_right(4), 0)
        # Forward: B(1) → K(10), so Reverse: K(10) → B(1)
        self.assertEqual(rotor.encode_left_to_right(10), 1)

    def test_round_trip(self):
        """Encoding forward then backward should return the input."""
        rotor = Rotor("III", "G", 5)
        for i in range(26):
            forward = rotor.encode_right_to_left(i)
            backward = rotor.encode_left_to_right(forward)
            self.assertEqual(backward, i)

    def test_set_position(self):
        """set_position should update the rotor position."""
        rotor = Rotor("I", "A", 1)
        rotor.set_position("M")
        self.assertEqual(rotor.position, 12)
        self.assertEqual(rotor.get_position_char(), "M")

    def test_repr(self):
        """Rotor repr should show name, position, and ring setting."""
        rotor = Rotor("I", "A", 1)
        r = repr(rotor)
        self.assertIn("I", r)
        self.assertIn("A", r)


class TestReflector(unittest.TestCase):
    def test_involution(self):
        """Reflector should map back to itself: reflecting twice returns the input."""
        for name in REFLECTOR_WIRINGS:
            ref = Reflector(name)
            for i in range(26):
                self.assertEqual(ref.encode(ref.encode(i)), i)

    def test_no_self_mapping_b_c(self):
        """No letter should map to itself (for reflectors B and C)."""
        for name in ["B", "C"]:
            ref = Reflector(name)
            for i in range(26):
                self.assertNotEqual(ref.encode(i), i,
                    f"Reflector {name} maps {index_to_char(i)} to itself")

    def test_reflector_a_no_self_mapping(self):
        """Reflector A has no self-mappings either."""
        ref = Reflector("A")
        for i in range(26):
            self.assertNotEqual(ref.encode(i), i,
                f"Reflector A maps {index_to_char(i)} to itself")

    def test_repr(self):
        ref = Reflector("B")
        self.assertIn("B", repr(ref))


class TestEnigmaMachine(unittest.TestCase):
    def test_known_test_vector_bdqzgo(self):
        """
        Known Enigma I test vector:
        Settings: Rotors I II III (left to right), positions A A A, Ring 01 01 01, Reflector B, No plugboard
        Input: AAAAA
        Expected: BDZGO (widely-cited standard test vector)
        """
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "A", "A"],
            ring_settings=[1, 1, 1],
            reflector_name="B"
        )
        result = machine.encrypt("AAAAA")
        self.assertEqual(result, "BDZGO",
            f"Known test vector failed: expected BDZGO, got {result}")

    def test_reciprocal_property(self):
        """Encrypting twice with the same initial settings should return plaintext."""
        for rotors in [["I", "II", "III"], ["IV", "V", "I"], ["VI", "VII", "VIII"]]:
            machine1 = EnigmaMachine(rotor_names=rotors, rotor_positions=["A", "A", "A"])
            machine2 = EnigmaMachine(rotor_names=rotors, rotor_positions=["A", "A", "A"])
            plaintext = "HELLO"
            encrypted = machine1.encrypt(plaintext)
            decrypted = machine2.encrypt(encrypted)
            self.assertEqual(decrypted, plaintext,
                f"Failed reciprocal property for rotors {rotors}")

    def test_reciprocal_with_plugboard(self):
        """Reciprocal property with plugboard."""
        machine1 = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            plugboard_pairs=["AB", "CD", "EF"]
        )
        machine2 = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            plugboard_pairs=["AB", "CD", "EF"]
        )
        plaintext = "TESTMESSAGE"
        encrypted = machine1.encrypt(plaintext)
        decrypted = machine2.encrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_no_self_encryption(self):
        """No letter should encrypt to itself (fundamental Enigma property for reflectors B and C)."""
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            plugboard_pairs=["AB", "CD", "EF"]
        )
        plaintext = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        encrypted = machine.encrypt(plaintext)
        for i, (p, e) in enumerate(zip(plaintext, encrypted)):
            self.assertNotEqual(p, e,
                f"Letter {p} at position {i} encrypted to itself")

    def test_different_settings_different_output(self):
        """Different rotor settings should produce different output."""
        machine1 = EnigmaMachine(rotor_names=["I", "II", "III"], rotor_positions=["A", "A", "A"])
        machine2 = EnigmaMachine(rotor_names=["I", "II", "III"], rotor_positions=["B", "A", "A"])
        text = "HELLO"
        self.assertNotEqual(machine1.encrypt(text), machine2.encrypt(text))

    def test_different_rotors_different_output(self):
        """Different rotor choices should produce different output."""
        machine1 = EnigmaMachine(rotor_names=["I", "II", "III"])
        machine2 = EnigmaMachine(rotor_names=["IV", "V", "I"])
        text = "TEST"
        self.assertNotEqual(machine1.encrypt(text), machine2.encrypt(text))

    def test_plugboard_changes_output(self):
        """Adding plugboard pairs should change the output."""
        machine1 = EnigmaMachine(plugboard_pairs=[])
        machine2 = EnigmaMachine(plugboard_pairs=["AB"])
        # Use text containing A and B so the plugboard actually affects it
        text = "ABCDEF"
        self.assertNotEqual(machine1.encrypt(text), machine2.encrypt(text))

    def test_non_alpha_passthrough(self):
        """Non-alphabetic characters should pass through unchanged."""
        machine = EnigmaMachine()
        result = machine.encrypt("HELLO, WORLD! 123")
        # Letters should be encrypted, non-alpha should pass through
        self.assertEqual(result[5], ",")
        self.assertEqual(result[12], "!")
        self.assertEqual(result[14], "1")

    def test_rotor_stepping(self):
        """Verify that rotors step correctly during encryption."""
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "A", "A"]
        )
        # After encrypting one char, right rotor should advance
        machine.encrypt("A")
        self.assertEqual(machine.rotors[2].position, 1)  # III advanced from A to B

    def test_middle_rotor_stepping(self):
        """Middle rotor should step when right rotor hits its notch."""
        # Rotor III has notch at V (position 21)
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "A", "V"]  # right rotor at notch
        )
        initial_middle = machine.rotors[1].position
        machine.encrypt("A")
        # Middle rotor should have stepped due to right rotor notch
        self.assertNotEqual(machine.rotors[1].position, initial_middle)

    def test_double_stepping(self):
        """Test the famous double-stepping mechanism."""
        # Set middle rotor at its notch position
        # Rotor II has notch at E (position 4)
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "E", "V"]  # middle at notch, right at notch
        )
        initial_left = machine.rotors[0].position
        machine.encrypt("A")
        # Left rotor should step due to double stepping
        self.assertNotEqual(machine.rotors[0].position, initial_left)

    def test_double_stepping_detailed(self):
        """Detailed double-stepping test with specific position tracking."""
        # Setup: positions A, D, V (middle one before notch E, right at notch V)
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "D", "V"]
        )
        # After 1st char: right at notch -> middle steps D->E, right steps V->W
        machine.encrypt_char("A")
        self.assertEqual(machine.get_state_string(), "A E W")
        # After 2nd char: middle at notch E -> double step: left steps A->B, middle steps E->F
        # and right steps W->X
        machine.encrypt_char("A")
        self.assertEqual(machine.get_state_string(), "B F X")

    def test_ring_setting_affects_output(self):
        """Different ring settings should produce different output."""
        machine1 = EnigmaMachine(ring_settings=[1, 1, 1])
        machine2 = EnigmaMachine(ring_settings=[5, 3, 7])
        text = "RINGSETTINGSTEST"
        self.assertNotEqual(machine1.encrypt(text), machine2.encrypt(text))

    def test_reflector_changes_output(self):
        """Different reflectors should produce different output."""
        machine1 = EnigmaMachine(reflector_name="B")
        machine2 = EnigmaMachine(reflector_name="C")
        text = "REFLECTORTEST"
        self.assertNotEqual(machine1.encrypt(text), machine2.encrypt(text))

    def test_trace_mode(self):
        """Trace mode should populate machine.trace."""
        machine = EnigmaMachine()
        machine.encrypt("A", trace=True)
        self.assertIsNotNone(machine.trace)
        self.assertTrue(len(machine.trace) > 0)
        # Trace should start with Input and end with Output
        self.assertEqual(machine.trace[0][0], "Input")
        self.assertEqual(machine.trace[-1][0], "Output")

    def test_all_traces(self):
        """get_all_traces should return per-character traces."""
        machine = EnigmaMachine()
        result = machine.encrypt("ABC", trace=True)
        traces = machine.get_all_traces()
        self.assertEqual(len(traces), 3)  # 3 letters
        for trace in traces:
            self.assertEqual(trace[0][0], "Input")
            self.assertEqual(trace[-1][0], "Output")

    def test_empty_string(self):
        """Encrypting empty string should return empty string."""
        machine = EnigmaMachine()
        self.assertEqual(machine.encrypt(""), "")

    def test_get_state_string(self):
        """State string should show rotor positions."""
        machine = EnigmaMachine(rotor_positions=["A", "B", "C"])
        state = machine.get_state_string()
        self.assertEqual(state, "A B C")

    def test_all_rotors_available(self):
        """All documented rotors should be creatable."""
        for name in ROTOR_WIRINGS:
            rotor = Rotor(name, "A", 1)
            self.assertEqual(rotor.name, name)

    def test_all_reflectors_available(self):
        """All documented reflectors should be creatable."""
        for name in REFLECTOR_WIRINGS:
            ref = Reflector(name)
            self.assertEqual(ref.name, name)

    def test_long_message(self):
        """Encrypting a long message should work and maintain reciprocal property."""
        machine1 = EnigmaMachine(
            rotor_names=["IV", "II", "I"],
            plugboard_pairs=["AB", "SZ", "UJ", "MY"]
        )
        machine2 = EnigmaMachine(
            rotor_names=["IV", "II", "I"],
            plugboard_pairs=["AB", "SZ", "UJ", "MY"]
        )
        plaintext = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
        encrypted = machine1.encrypt(plaintext)
        decrypted = machine2.encrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_machine_initialization_errors(self):
        """Invalid initialization should raise errors."""
        with self.assertRaises(ValueError):
            EnigmaMachine(rotor_names=["X", "Y", "Z"])
        with self.assertRaises(ValueError):
            EnigmaMachine(rotor_names=["I", "II"])  # only 2 rotors
        with self.assertRaises(ValueError):
            EnigmaMachine(reflector_name="Z")  # invalid reflector

    def test_ring_setting_validation(self):
        """Ring settings outside 1-26 should raise ValueError."""
        with self.assertRaises(ValueError):
            EnigmaMachine(ring_settings=[0, 1, 1])
        with self.assertRaises(ValueError):
            EnigmaMachine(ring_settings=[27, 1, 1])
        with self.assertRaises(ValueError):
            EnigmaMachine(ring_settings=[1, -1, 1])
        # Valid ring settings should work
        machine = EnigmaMachine(ring_settings=[1, 13, 26])
        self.assertIsNotNone(machine)

    def test_plugboard_validation_in_machine(self):
        """Plugboard validation should catch errors."""
        with self.assertRaises(ValueError):
            EnigmaMachine(plugboard_pairs=["AB", "AC"])  # duplicate A
        with self.assertRaises(ValueError):
            EnigmaMachine(plugboard_pairs=["AA"])  # self-swap
        with self.assertRaises(ValueError):
            EnigmaMachine(plugboard_pairs=["A"])  # too short
        with self.assertRaises(ValueError):
            EnigmaMachine(plugboard_pairs=["12"])  # non-alpha

    def test_signal_path_order(self):
        """
        Verify the signal path goes through the RIGHT rotor first.
        With rotors I II III (left to right), the forward path should be:
        III (right) -> II (middle) -> I (left) -> reflector
        This is verified by the BDZGO test vector.
        """
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "A", "A"],
            ring_settings=[1, 1, 1],
            reflector_name="B"
        )
        # The known test vector AAAAA -> BDZGO confirms correct signal path
        result = machine.encrypt("AAAAA")
        self.assertEqual(result, "BDZGO")

    def test_encrypt_char_lowercase(self):
        """encrypt_char should pass through lowercase letters unchanged."""
        machine = EnigmaMachine()
        result = machine.encrypt_char("a")
        self.assertEqual(result, "a")

    def test_encrypt_lowercase(self):
        """encrypt should convert lowercase to uppercase."""
        machine = EnigmaMachine()
        result = machine.encrypt("hello")
        self.assertTrue(result.isupper())

    def test_position_wrapping(self):
        """Rotor position should wrap from Z to A."""
        machine = EnigmaMachine(rotor_positions=["Z", "Z", "Z"])
        machine.encrypt_char("A")
        # Right rotor wraps from Z to A
        self.assertEqual(machine.rotors[2].get_position_char(), "A")

    def test_reset_positions(self):
        """reset_positions should restore initial rotor positions."""
        machine = EnigmaMachine(rotor_positions=["A", "B", "C"])
        machine.encrypt("HELLO")
        # Positions have changed
        self.assertNotEqual(machine.get_state_string(), "A B C")
        # Reset
        machine.reset_positions()
        self.assertEqual(machine.get_state_string(), "A B C")

    def test_reset_positions_custom(self):
        """reset_positions should accept custom positions."""
        machine = EnigmaMachine(rotor_positions=["A", "A", "A"])
        machine.reset_positions(["X", "Y", "Z"])
        self.assertEqual(machine.get_state_string(), "X Y Z")

    def test_reset_positions_invalid(self):
        """reset_positions with wrong count should raise ValueError."""
        machine = EnigmaMachine()
        with self.assertRaises(ValueError):
            machine.reset_positions(["A", "B"])  # only 2 positions

    def test_get_config(self):
        """get_config should return a valid configuration dict."""
        machine = EnigmaMachine(
            rotor_names=["IV", "II", "I"],
            rotor_positions=["A", "B", "C"],
            ring_settings=[5, 3, 7],
            reflector_name="B",
            plugboard_pairs=["AB", "CD"]
        )
        config = machine.get_config()
        self.assertEqual(config["rotor_names"], ["IV", "II", "I"])
        self.assertEqual(config["rotor_positions"], ["A", "B", "C"])
        self.assertEqual(config["ring_settings"], [5, 3, 7])
        self.assertEqual(config["reflector_name"], "B")
        self.assertEqual(config["plugboard_pairs"], ["AB", "CD"])
        self.assertIn("version", config)

    def test_config_round_trip(self):
        """Config from get_config should recreate an equivalent machine."""
        machine1 = EnigmaMachine(
            rotor_names=["IV", "V", "I"],
            rotor_positions=["D", "E", "F"],
            ring_settings=[10, 11, 12],
            reflector_name="C",
            plugboard_pairs=["AB", "ZX"]
        )
        config = machine1.get_config()
        machine2 = EnigmaMachine(
            rotor_names=config["rotor_names"],
            rotor_positions=config["rotor_positions"],
            ring_settings=config["ring_settings"],
            reflector_name=config["reflector_name"],
            plugboard_pairs=config["plugboard_pairs"],
        )
        # Both machines should produce the same output for the same input
        self.assertEqual(
            machine1.encrypt("TESTMESSAGE"),
            machine2.encrypt("TESTMESSAGE")
        )


class TestFormatOutput(unittest.TestCase):
    def test_plain_format(self):
        """Plain format should return text as-is."""
        result = format_output("HELLO WORLD", style="plain")
        self.assertEqual(result, "HELLO WORLD")

    def test_grouped_format(self):
        """Grouped format should split letters into groups."""
        result = format_output("HELLOWORLD", style="grouped", group_size=5)
        self.assertEqual(result, "HELLO WORLD")

    def test_grouped_format_custom_size(self):
        """Grouped format with custom group size."""
        result = format_output("HELLOWORLD", style="grouped", group_size=4)
        self.assertEqual(result, "HELL OWOR LD")

    def test_grouped_strips_non_alpha(self):
        """Grouped format should strip non-alpha characters."""
        result = format_output("HELLO, WORLD!", style="grouped", group_size=5)
        self.assertEqual(result, "HELLO WORLD")

    def test_verbose_format(self):
        """Verbose format should show per-character mappings."""
        result = format_output("AB", style="verbose")
        self.assertIn("1:", result)
        self.assertIn("2:", result)
        self.assertIn("→", result)

    def test_verbose_format_with_original(self):
        """Verbose format with original text should show input→output mapping."""
        # When original text is provided, verbose should show input→output
        result = format_output("XYZ", style="verbose", original="ABC")
        self.assertIn("A → X", result)
        self.assertIn("B → Y", result)
        self.assertIn("C → Z", result)

    def test_verbose_format_without_original(self):
        """Verbose format without original text should fall back to self-mapping."""
        # When no original is provided, it should still produce output
        result = format_output("ABC", style="verbose")
        self.assertIn("1:", result)
        self.assertIn("→", result)

    def test_verbose_format_mixed_alpha(self):
        """Verbose format should only show alpha characters."""
        result = format_output("XZ", style="verbose", original="AB")
        self.assertIn("A → X", result)
        self.assertIn("B → Z", result)

    def test_signal_mode_without_trace_flag(self):
        """--signal should work without --trace by enabling trace internally."""
        machine = EnigmaMachine()
        # Simulate what the CLI does: trace is enabled when signal is requested
        result = machine.encrypt("HELLO", trace=True)
        self.assertIsNotNone(machine.trace)
        vis = visualize_signal_path(machine.trace)
        self.assertIn("SIGNAL", vis)


class TestRandomConfig(unittest.TestCase):
    def test_random_config_structure(self):
        """random_config should return a valid config dict."""
        config = random_config()
        self.assertIn("rotor_names", config)
        self.assertIn("rotor_positions", config)
        self.assertIn("ring_settings", config)
        self.assertIn("reflector_name", config)
        self.assertIn("plugboard_pairs", config)

    def test_random_config_valid_rotors(self):
        """random_config should produce valid rotor names."""
        for _ in range(20):  # Test multiple random configs
            config = random_config()
            self.assertEqual(len(config["rotor_names"]), 3)
            for name in config["rotor_names"]:
                self.assertIn(name, ROTOR_WIRINGS)

    def test_random_config_valid_positions(self):
        """random_config should produce valid positions."""
        config = random_config()
        self.assertEqual(len(config["rotor_positions"]), 3)
        for pos in config["rotor_positions"]:
            self.assertIn(pos, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def test_random_config_valid_ring_settings(self):
        """random_config should produce valid ring settings."""
        config = random_config()
        self.assertEqual(len(config["ring_settings"]), 3)
        for rs in config["ring_settings"]:
            self.assertGreaterEqual(rs, 1)
            self.assertLessEqual(rs, 26)

    def test_random_config_valid_reflector(self):
        """random_config should produce a valid reflector name."""
        config = random_config()
        self.assertIn(config["reflector_name"], REFLECTOR_WIRINGS)

    def test_random_config_produces_working_machine(self):
        """random_config should produce a config that creates a working EnigmaMachine."""
        for _ in range(10):
            config = random_config()
            machine = EnigmaMachine(
                rotor_names=config["rotor_names"],
                rotor_positions=config["rotor_positions"],
                ring_settings=config["ring_settings"],
                reflector_name=config["reflector_name"],
                plugboard_pairs=config["plugboard_pairs"],
            )
            result = machine.encrypt("TEST")
            self.assertTrue(len(result) > 0)

    def test_random_config_reciprocal(self):
        """Random configs should maintain reciprocal property."""
        for _ in range(5):
            config = random_config()
            m1 = EnigmaMachine(
                rotor_names=config["rotor_names"],
                rotor_positions=config["rotor_positions"],
                ring_settings=config["ring_settings"],
                reflector_name=config["reflector_name"],
                plugboard_pairs=config["plugboard_pairs"],
            )
            m2 = EnigmaMachine(
                rotor_names=config["rotor_names"],
                rotor_positions=config["rotor_positions"],
                ring_settings=config["ring_settings"],
                reflector_name=config["reflector_name"],
                plugboard_pairs=config["plugboard_pairs"],
            )
            plaintext = "HELLO WORLD"
            encrypted = m1.encrypt(plaintext)
            decrypted = m2.encrypt(encrypted)
            self.assertEqual(decrypted, plaintext)


class TestVisualization(unittest.TestCase):
    def test_visualize_rotors(self):
        """Visualize should produce a string with expected content."""
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            rotor_positions=["A", "A", "A"]
        )
        vis = visualize_rotors(machine)
        self.assertIn("ENIGMA", vis)
        self.assertIn("I", vis)
        self.assertIn("II", vis)
        self.assertIn("III", vis)

    def test_format_trace(self):
        """Format trace should produce a readable string."""
        machine = EnigmaMachine()
        machine.encrypt("A", trace=True)
        trace_str = format_trace(machine.trace, "A", machine.encrypt_char("A"))
        self.assertIn("Encrypting", trace_str)
        self.assertIn("Input", trace_str)
        self.assertIn("Output", trace_str)

    def test_visualize_signal_path(self):
        """visualize_signal_path should produce a readable visualization."""
        machine = EnigmaMachine()
        machine.encrypt_char("A", trace=True)
        vis = visualize_signal_path(machine.trace)
        self.assertIn("SIGNAL", vis)
        self.assertIn("Input", vis)
        self.assertIn("Output", vis)

    def test_visualize_signal_path_empty(self):
        """visualize_signal_path with empty trace should return fallback."""
        vis = visualize_signal_path(None)
        self.assertIn("No trace", vis)

    def test_format_full_trace(self):
        """format_full_trace should produce a full trace for all characters."""
        machine = EnigmaMachine()
        result = machine.encrypt("ABC", trace=True)
        traces = machine.get_all_traces()
        full_trace = format_full_trace(traces, "ABC", result)
        self.assertIn("Plaintext", full_trace)
        self.assertIn("Ciphertext", full_trace)
        self.assertIn("Character 1", full_trace)
        self.assertIn("Character 3", full_trace)


class TestConfigSaveLoad(unittest.TestCase):
    def test_save_and_load_config(self):
        """Config should survive a save/load round trip to JSON."""
        machine = EnigmaMachine(
            rotor_names=["IV", "II", "I"],
            rotor_positions=["A", "B", "C"],
            ring_settings=[5, 3, 7],
            reflector_name="B",
            plugboard_pairs=["AB", "CD"]
        )
        config = machine.get_config()

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            tmppath = f.name

        try:
            # Load it back
            with open(tmppath, 'r') as f:
                loaded_config = json.load(f)

            # Create new machine from loaded config
            machine2 = EnigmaMachine(
                rotor_names=loaded_config["rotor_names"],
                rotor_positions=loaded_config["rotor_positions"],
                ring_settings=loaded_config["ring_settings"],
                reflector_name=loaded_config["reflector_name"],
                plugboard_pairs=loaded_config["plugboard_pairs"],
            )
            # Both machines should produce same output
            self.assertEqual(
                machine.encrypt("ROUNDTRIPTEST"),
                machine2.encrypt("ROUNDTRIPTEST")
            )
        finally:
            os.unlink(tmppath)


class TestCLISmokeTest(unittest.TestCase):
    """Smoke tests for CLI functionality (basic argument parsing)."""

    def test_imports_work(self):
        """All public functions and classes should be importable."""
        from enigma import (
            EnigmaMachine, Rotor, Reflector, Plugboard,
            random_config, format_output, format_trace, format_full_trace,
            visualize_rotors, visualize_signal_path, interactive_mode,
            list_components, main,
            ROTOR_WIRINGS, REFLECTOR_WIRINGS, ROTOR_NOTCHES, ALPHABET
        )
        # Just verify they exist
        self.assertIsNotNone(EnigmaMachine)
        self.assertIsNotNone(Rotor)
        self.assertIsNotNone(Reflector)
        self.assertIsNotNone(Plugboard)
        self.assertIsNotNone(random_config)
        self.assertIsNotNone(format_output)


if __name__ == "__main__":
    unittest.main()