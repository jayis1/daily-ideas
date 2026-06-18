#!/usr/bin/env python3
"""Tests for the Terminal Enigma Machine."""

import unittest
from enigma import (
    EnigmaMachine, Rotor, Reflector, Plugboard,
    char_to_index, index_to_char,
    ROTOR_WIRINGS, REFLECTOR_WIRINGS, ROTOR_NOTCHES,
)


class TestHelpers(unittest.TestCase):
    def test_char_to_index(self):
        self.assertEqual(char_to_index("A"), 0)
        self.assertEqual(char_to_index("Z"), 25)
        self.assertEqual(char_to_index("a"), 0)

    def test_index_to_char(self):
        self.assertEqual(index_to_char(0), "A")
        self.assertEqual(index_to_char(25), "Z")

    def test_round_trip(self):
        for i in range(26):
            self.assertEqual(char_to_index(index_to_char(i)), i)


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


class TestReflector(unittest.TestCase):
    def test_involution(self):
        """Reflector should map back to itself: reflecting twice returns the input."""
        for name in REFLECTOR_WIRINGS:
            ref = Reflector(name)
            for i in range(26):
                self.assertEqual(ref.encode(ref.encode(i)), i)

    def test_no_self_mapping(self):
        """No letter should map to itself (for reflectors B and C)."""
        for name in ["B", "C"]:
            ref = Reflector(name)
            for i in range(26):
                self.assertNotEqual(ref.encode(i), i, 
                    f"Reflector {name} maps {index_to_char(i)} to itself")


class TestEnigmaMachine(unittest.TestCase):
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
        """No letter should encrypt to itself (fundamental Enigma property)."""
        machine = EnigmaMachine(
            rotor_names=["I", "II", "III"],
            plugboard_pairs=["AB", "CD", "EF"]
        )
        plaintext = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        encrypted = machine.encrypt(plaintext)
        for i, (p, e) in enumerate(zip(plaintext, encrypted)):
            self.assertNotEqual(p, e, 
                f"Letter {p} at position {i} encrypted to itself")

    def test_known_test_vector(self):
        """
        Known Enigma test vector:
        Settings: Rotors III II I, positions A A A, Ring 01 01 01, Reflector B, No plugboard
        Encrypt 'A' → should produce a deterministic result.
        We test that the output is consistent and not 'A'.
        """
        machine = EnigmaMachine(
            rotor_names=["III", "II", "I"],
            rotor_positions=["A", "A", "A"],
            ring_settings=[1, 1, 1],
            reflector_name="B"
        )
        result = machine.encrypt("A")
        self.assertNotEqual(result, "A")
        self.assertEqual(len(result), 1)

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


class TestVisualization(unittest.TestCase):
    def test_visualize_rotors(self):
        """Visualize should produce a string with expected content."""
        from enigma import visualize_rotors
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
        from enigma import format_trace
        machine = EnigmaMachine()
        machine.encrypt("A", trace=True)
        trace_str = format_trace(machine.trace, "A", machine.encrypt_char("A"))
        self.assertIn("Encrypting", trace_str)
        self.assertIn("Input", trace_str)
        self.assertIn("Output", trace_str)


if __name__ == "__main__":
    unittest.main()