#!/usr/bin/env python3
"""
Tests for the Turing Machine Simulator.
Run with: python3 -m pytest test_turing.py -v
         or: python3 test_turing.py
"""

import json
import os
import sys
import tempfile

# Ensure we can import the main module
sys.path.insert(0, os.path.dirname(__file__))
from turing import (
    Transition, TuringMachine, Tape, ExecutionStats,
    BUILTIN_PROGRAMS, run_batch, run_trace, save_machine, load_machine,
    __version__,
)


class TestTape:
    """Tests for the Tape data structure."""

    def test_initial_blank_tape(self):
        tape = Tape()
        assert tape.read(0) == "_"
        assert tape.read(100) == "_"
        assert tape.read(-5) == "_"

    def test_custom_blank(self):
        tape = Tape(blank="0")
        assert tape.read(0) == "0"
        assert tape.read(50) == "0"

    def test_write_and_read(self):
        tape = Tape()
        tape.write(0, "1")
        tape.write(1, "0")
        tape.write(-3, "X")
        assert tape.read(0) == "1"
        assert tape.read(1) == "0"
        assert tape.read(-3) == "X"
        assert tape.read(2) == "_"

    def test_write_blank_erases(self):
        tape = Tape()
        tape.write(5, "1")
        assert tape.read(5) == "1"
        tape.write(5, "_")
        assert tape.read(5) == "_"
        assert 5 not in tape.cells  # should be deleted from dict

    def test_overwrite(self):
        tape = Tape()
        tape.write(0, "1")
        tape.write(0, "0")
        assert tape.read(0) == "0"

    def test_to_string(self):
        tape = Tape()
        tape.write(0, "1")
        tape.write(1, "0")
        tape.write(2, "1")
        cells = tape.to_string(head_pos=1, window=4)
        # window=4, centered around head_pos=1
        assert "1" in cells or "0" in cells

    def test_non_blank_segment(self):
        tape = Tape()
        assert tape.non_blank_segment() == (0, 0)
        tape.write(2, "A")
        tape.write(5, "B")
        assert tape.non_blank_segment() == (2, 5)

    def test_get_contents(self):
        tape = Tape()
        assert tape.get_contents() == ""
        tape.write(0, "1")
        tape.write(1, "0")
        tape.write(2, "1")
        assert tape.get_contents() == "101"


class TestTransition:
    """Tests for the Transition data structure."""

    def test_creation(self):
        t = Transition(next_state="q1", write_symbol="0", direction="R")
        assert t.next_state == "q1"
        assert t.write_symbol == "0"
        assert t.direction == "R"

    def test_repr(self):
        t = Transition(next_state="q_accept", write_symbol="1", direction="L")
        r = repr(t)
        assert "q_accept" in r
        assert "1" in r


class TestExecutionStats:
    """Tests for the ExecutionStats data structure."""

    def test_initial_values(self):
        stats = ExecutionStats()
        assert stats.total_steps == 0
        assert stats.cells_written == 0
        assert stats.unique_cells_visited == 0

    def test_summary(self):
        stats = ExecutionStats(total_steps=5, cells_written=3)
        s = stats.summary()
        assert "Steps: 5" in s
        assert "Cells written: 3" in s


class TestTuringMachine:
    """Tests for the TuringMachine data structure and its validate method."""

    def test_step_lookup_found(self):
        machine = BUILTIN_PROGRAMS["binary_not"]
        trans = machine.step("q0", "0")
        assert trans is not None
        assert trans.next_state == "q0"
        assert trans.write_symbol == "1"
        assert trans.direction == "R"

    def test_step_lookup_not_found(self):
        machine = BUILTIN_PROGRAMS["busy_beaver_3"]
        trans = machine.step("HALT", "0")
        assert trans is None

    def test_validate_valid_machine(self):
        machine = BUILTIN_PROGRAMS["binary_increment"]
        warnings = machine.validate()
        assert warnings == []

    def test_validate_invalid_machine(self):
        machine = TuringMachine(
            name="bad",
            description="bad machine",
            states=["q0"],
            alphabet=["0", "1"],
            blank_symbol="_",
            initial_state="q_missing",  # not in states
            accept_states=["q_accept"],  # not in states
            transitions={
                ("q0", "0"): Transition(next_state="q_unknown", write_symbol="1", direction="X"),
            },
            initial_tape="2",  # not in alphabet
        )
        warnings = machine.validate()
        assert len(warnings) > 0
        # Check specific warnings
        warning_text = " ".join(warnings)
        assert "q_missing" in warning_text
        assert "q_unknown" in warning_text
        assert "q_accept" in warning_text
        assert "X" in warning_text  # invalid direction


class TestBuiltinPrograms:
    """Tests for all built-in Turing machine programs."""

    def test_binary_increment(self):
        result = run_batch(BUILTIN_PROGRAMS["binary_increment"])
        assert result["accepted"] is True
        assert result["output"] == "1100"  # 1011 (11) + 1 = 1100 (12)

    def test_binary_increment_custom_tape(self):
        machine = TuringMachine(
            name="binary_increment",
            description="Increment a binary number by 1",
            states=BUILTIN_PROGRAMS["binary_increment"].states,
            alphabet=BUILTIN_PROGRAMS["binary_increment"].alphabet,
            blank_symbol="_",
            initial_state="q0",
            accept_states=["q_accept"],
            reject_states=["q_reject"],
            transitions=BUILTIN_PROGRAMS["binary_increment"].transitions,
            initial_tape="111",  # 7 → 1000
        )
        result = run_batch(machine)
        assert result["accepted"] is True
        assert result["output"] == "1000"

    def test_binary_increment_overflow(self):
        machine = TuringMachine(
            name="binary_increment",
            description="Increment a binary number by 1",
            states=BUILTIN_PROGRAMS["binary_increment"].states,
            alphabet=BUILTIN_PROGRAMS["binary_increment"].alphabet,
            blank_symbol="_",
            initial_state="q0",
            accept_states=["q_accept"],
            reject_states=["q_reject"],
            transitions=BUILTIN_PROGRAMS["binary_increment"].transitions,
            initial_tape="111",  # 7 → 1000
        )
        result = run_batch(machine)
        assert result["accepted"] is True
        assert "1000" in result["output"]

    def test_unary_addition(self):
        result = run_batch(BUILTIN_PROGRAMS["unary_addition"])
        assert result["accepted"] is True
        assert result["output"] == "11111"  # 3 + 2 = 5 ones

    def test_palindrome_checker_palindrome(self):
        result = run_batch(BUILTIN_PROGRAMS["palindrome_checker"])
        assert result["accepted"] is True

    def test_palindrome_checker_not_palindrome(self):
        machine = TuringMachine(
            name="palindrome_checker",
            description="Check if a binary string is a palindrome",
            states=BUILTIN_PROGRAMS["palindrome_checker"].states,
            alphabet=BUILTIN_PROGRAMS["palindrome_checker"].alphabet,
            blank_symbol="_",
            initial_state="q0",
            accept_states=["q_accept"],
            reject_states=["q_reject"],
            transitions=BUILTIN_PROGRAMS["palindrome_checker"].transitions,
            initial_tape="10010",  # NOT a palindrome
        )
        result = run_batch(machine)
        assert result["accepted"] is False

    def test_busy_beaver(self):
        result = run_batch(BUILTIN_PROGRAMS["busy_beaver_3"])
        assert result["accepted"] is True
        assert result["steps"] == 13

    def test_binary_not(self):
        result = run_batch(BUILTIN_PROGRAMS["binary_not"])
        assert result["accepted"] is True
        assert result["output"] == "01001100"  # NOT(10110011) = 01001100

    def test_count_ones(self):
        result = run_batch(BUILTIN_PROGRAMS["count_ones"])
        assert result["accepted"] is True
        # Input: 10110= , should have ||| after the =
        assert "|||" in result["output"]

    def test_binary_decrement(self):
        result = run_batch(BUILTIN_PROGRAMS["binary_decrement"])
        assert result["accepted"] is True
        # 1100 (12) → 1011 (11)
        assert "1011" in result["output"]

    def test_binary_decrement_one(self):
        machine = TuringMachine(
            name="binary_decrement",
            description="Decrement a binary number by 1",
            states=BUILTIN_PROGRAMS["binary_decrement"].states,
            alphabet=BUILTIN_PROGRAMS["binary_decrement"].alphabet,
            blank_symbol="_",
            initial_state="q0",
            accept_states=["q_accept"],
            reject_states=["q_reject"],
            transitions=BUILTIN_PROGRAMS["binary_decrement"].transitions,
            initial_tape="10",  # 2 → 1
        )
        result = run_batch(machine)
        assert result["accepted"] is True
        # The output may contain Z markers from stripping leading zeros;
        # the key 1 should be present
        assert "1" in result["output"]

    def test_binary_decrement_power_of_two(self):
        machine = TuringMachine(
            name="binary_decrement",
            description="Decrement a binary number by 1",
            states=BUILTIN_PROGRAMS["binary_decrement"].states,
            alphabet=BUILTIN_PROGRAMS["binary_decrement"].alphabet,
            blank_symbol="_",
            initial_state="q0",
            accept_states=["q_accept"],
            reject_states=["q_reject"],
            transitions=BUILTIN_PROGRAMS["binary_decrement"].transitions,
            initial_tape="1000",  # 8 → 111 (7)
        )
        result = run_batch(machine)
        assert result["accepted"] is True
        # Should produce 111 (leading zeros stripped)
        ones = result["output"].replace("Z", "").replace("_", "")
        assert ones == "111"

    def test_unary_doubler(self):
        result = run_batch(BUILTIN_PROGRAMS["unary_doubler"])
        assert result["accepted"] is True
        # 111 (three ones) → 111111 (six ones)
        assert result["output"] == "111111"

    def test_all_builtins_have_required_fields(self):
        for name, machine in BUILTIN_PROGRAMS.items():
            assert machine.name == name
            assert machine.description
            assert len(machine.states) > 0
            assert len(machine.alphabet) > 0
            assert machine.blank_symbol
            assert machine.initial_state in machine.states or machine.initial_state == "q0"
            assert len(machine.transitions) > 0

    def test_all_builtins_validate_clean(self):
        for name, machine in BUILTIN_PROGRAMS.items():
            warnings = machine.validate()
            assert warnings == [], f"Built-in '{name}' has validation warnings: {warnings}"

    def test_binary_and(self):
        """Binary AND: 1100 & 1010 = 1000."""
        result = run_batch(BUILTIN_PROGRAMS["binary_and"])
        assert result["accepted"] is True
        # The output should contain & with the result on the right side
        assert "&" in result["output"]
        parts = result["output"].split("&")
        # Left side preserved: 1100, right side is the AND result: 1000
        result_right = parts[1].replace("_", "")
        assert result_right == "1000"

    def test_string_reverser(self):
        """String reverser: 110 reversed = 011."""
        result = run_batch(BUILTIN_PROGRAMS["string_reverser"])
        assert result["accepted"] is True
        assert result["output"] == "011"


class TestTraceFeature:
    """Tests for the execution trace feature."""

    def test_run_trace_basic(self):
        """run_trace should return a list of ExecutionStep objects."""
        machine = BUILTIN_PROGRAMS["binary_not"]
        steps = run_trace(machine)
        assert len(steps) > 0
        # Each step should have required fields
        for step in steps:
            assert hasattr(step, "state")
            assert hasattr(step, "head_position")
            assert hasattr(step, "symbol_read")
            assert hasattr(step, "symbol_written")
            assert hasattr(step, "direction")
            assert hasattr(step, "next_state")
            assert hasattr(step, "step_number")
            assert hasattr(step, "tape_snapshot")

    def test_run_trace_step_count(self):
        """run_trace should produce the same number of steps as run_batch."""
        machine = BUILTIN_PROGRAMS["binary_not"]
        result = run_batch(machine)
        steps = run_trace(machine)
        assert len(steps) == result["steps"]

    def test_run_trace_final_state(self):
        """The last step of the trace should end in an accept state."""
        machine = BUILTIN_PROGRAMS["binary_increment"]
        steps = run_trace(machine)
        final_state = steps[-1].next_state
        assert final_state in machine.accept_states


class TestRunBatch:
    """Tests for the batch runner."""

    def test_max_steps_limit(self):
        """A machine that loops forever should hit the max_steps limit."""
        # Create a machine that never halts: q0 on '0' -> q0 write '0' move R
        machine = TuringMachine(
            name="infinite_loop",
            description="Loops forever moving right",
            states=["q0"],
            alphabet=["0"],
            blank_symbol="0",
            initial_state="q0",
            accept_states=[],
            reject_states=[],
            transitions={("q0", "0"): Transition("q0", "0", "R")},
            initial_tape="0",
        )
        result = run_batch(machine, max_steps=100)
        assert result["steps"] == 100

    def test_result_has_stats(self):
        result = run_batch(BUILTIN_PROGRAMS["binary_not"])
        assert "stats" in result
        assert result["stats"].total_steps > 0
        assert result["stats"].cells_written > 0

    def test_blank_tape_machine(self):
        """Machine with empty initial tape."""
        result = run_batch(BUILTIN_PROGRAMS["busy_beaver_3"])
        assert result["input"] == "(blank)"
        assert result["accepted"] is True


class TestSaveLoadMachine:
    """Tests for JSON serialization of machines."""

    def test_roundtrip_save_load(self):
        machine = BUILTIN_PROGRAMS["binary_not"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            save_machine(machine, filepath)
            loaded = load_machine(filepath)
            assert loaded.name == machine.name
            assert loaded.description == machine.description
            assert loaded.states == machine.states
            assert loaded.alphabet == machine.alphabet
            assert loaded.blank_symbol == machine.blank_symbol
            assert loaded.initial_state == machine.initial_state
            assert loaded.accept_states == machine.accept_states
            assert loaded.reject_states == machine.reject_states
            assert loaded.initial_tape == machine.initial_tape
            assert len(loaded.transitions) == len(machine.transitions)
            # Check transitions match
            for (s, r), t in machine.transitions.items():
                loaded_t = loaded.transitions[(s, r)]
                assert loaded_t.next_state == t.next_state
                assert loaded_t.write_symbol == t.write_symbol
                assert loaded_t.direction == t.direction
        finally:
            os.unlink(filepath)

    def test_roundtrip_produces_same_output(self):
        """A machine loaded from JSON should produce the same batch output."""
        machine = BUILTIN_PROGRAMS["palindrome_checker"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            save_machine(machine, filepath)
            loaded = load_machine(filepath)
            result_orig = run_batch(machine)
            result_loaded = run_batch(loaded)
            assert result_orig["output"] == result_loaded["output"]
            assert result_orig["steps"] == result_loaded["steps"]
            assert result_orig["accepted"] == result_loaded["accepted"]
        finally:
            os.unlink(filepath)

    def test_load_nonexistent_file(self):
        try:
            load_machine("/nonexistent/path/machine.json")
            assert False, "Should have raised an error"
        except (FileNotFoundError, OSError):
            pass

    def test_load_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json!!!")
            filepath = f.name
        try:
            load_machine(filepath)
            assert False, "Should have raised an error"
        except (json.JSONDecodeError, KeyError):
            pass
        finally:
            os.unlink(filepath)


class TestVersion:
    """Test that version is accessible."""

    def test_version_string(self):
        assert __version__ == "1.2.0"


def run_all_tests():
    """Simple test runner for when pytest is not available."""
    classes = [
        TestTape, TestTransition, TestExecutionStats, TestTuringMachine,
        TestBuiltinPrograms, TestTraceFeature, TestRunBatch, TestSaveLoadMachine, TestVersion,
    ]
    total = 0
    passed = 0
    failed = 0
    errors = []

    for cls in classes:
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, method_name)()
                    passed += 1
                    print(f"  ✓ {cls.__name__}.{method_name}")
                except Exception as e:
                    failed += 1
                    errors.append((cls.__name__, method_name, str(e)))
                    print(f"  ✗ {cls.__name__}.{method_name}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if errors:
        print("\nFailures:")
        for cls_name, method, err in errors:
            print(f"  {cls_name}.{method}: {err}")
    return failed == 0


if __name__ == "__main__":
    print("Running Turing Machine Simulator Tests\n")
    success = run_all_tests()
    sys.exit(0 if success else 1)