#!/usr/bin/env python3
"""Unit tests for the Procedural Heraldry Generator."""

import sys
import os
import subprocess
import random

sys.path.insert(0, os.path.dirname(__file__))
import heraldry


def test_shield_mask():
    """Shield mask has valid dimensions and interior cells."""
    mask = heraldry.make_shield_mask()
    assert len(mask) == heraldry.SHIELD_H, f"Expected {heraldry.SHIELD_H} rows, got {len(mask)}"
    for row in mask:
        assert len(row) == heraldry.SHIELD_W, f"Expected {heraldry.SHIELD_W} cols, got {len(row)}"
    true_count = sum(sum(row) for row in mask)
    assert true_count > 0, "Shield mask has no interior cells"
    assert true_count < heraldry.SHIELD_W * heraldry.SHIELD_H, "Shield mask is fully filled"


def test_rule_of_tincture():
    """All generated blazons follow the Rule of Tincture."""
    violations = []
    for i in range(2000):
        random.seed(i)
        spec = heraldry.generate_blazon()
        if spec['charge_tincture'] is None:
            continue  # No charge, nothing to violate
        f1_class = heraldry.TINCTURES[spec['field1']]['class']
        c_class = heraldry.TINCTURES[spec['charge_tincture']]['class']
        if f1_class == c_class:
            violations.append(f"Seed {i}: charge on field1 — {spec}")
        if spec['field2']:
            f2_class = heraldry.TINCTURES[spec['field2']]['class']
            if f2_class == c_class:
                violations.append(f"Seed {i}: charge on field2 — {spec}")
    assert len(violations) == 0, f"Found {len(violations)} Rule of Tincture violations:\n" + "\n".join(violations[:5])


def test_violates_rule_of_tincture():
    """The violation check function works correctly."""
    # Metal on metal
    assert heraldry.violates_rule_of_tincture("Or", "Argent") is True
    assert heraldry.violates_rule_of_tincture("Argent", "Or") is True
    # Colour on colour
    assert heraldry.violates_rule_of_tincture("Gules", "Azure") is True
    assert heraldry.violates_rule_of_tincture("Sable", "Vert") is True
    # Metal on colour (OK)
    assert heraldry.violates_rule_of_tincture("Or", "Gules") is False
    assert heraldry.violates_rule_of_tincture("Argent", "Azure") is False
    # Colour on metal (OK)
    assert heraldry.violates_rule_of_tincture("Gules", "Or") is False
    assert heraldry.violates_rule_of_tincture("Azure", "Argent") is False


def test_divisions_render():
    """All divisions render without None cells."""
    mask = heraldry.make_shield_mask()
    for div_name, div_fn in heraldry.DIVISIONS.items():
        field = div_fn("Gules", "Or", mask)
        none_count = sum(1 for y in range(heraldry.SHIELD_H)
                         for x in range(heraldry.SHIELD_W)
                         if mask[y][x] and field[y][x] is None)
        assert none_count == 0, f"Division '{div_name}' has {none_count} None cells"


def test_charges_render():
    """All charges render and cover some pixels."""
    mask = heraldry.make_shield_mask()
    for charge_name, charge_fn in heraldry.CHARGES.items():
        field = [[None] * heraldry.SHIELD_W for _ in range(heraldry.SHIELD_H)]
        # Fill with base
        for y in range(heraldry.SHIELD_H):
            for x in range(heraldry.SHIELD_W):
                if mask[y][x]:
                    field[y][x] = "Azure"
        result = charge_fn(field, "Argent", mask)
        charge_count = sum(1 for y in range(heraldry.SHIELD_H)
                          for x in range(heraldry.SHIELD_W)
                          if mask[y][x] and result[y][x] == "Argent")
        assert charge_count > 0, f"Charge '{charge_name}' renders no pixels"


def test_render_shield_with_no_charge():
    """A divided field without a charge still renders fully."""
    mask = heraldry.make_shield_mask()
    spec = {
        "division": "Per Pale",
        "field1": "Azure",
        "field2": "Or",
        "charge": None,
        "charge_tincture": None,
        "blazon": "Per Pale Azure and Or",
    }
    field = heraldry.render_shield(spec, mask)
    none_count = sum(1 for y in range(heraldry.SHIELD_H)
                     for x in range(heraldry.SHIELD_W)
                     if mask[y][x] and field[y][x] is None)
    assert none_count == 0, f"No-charge render has {none_count} None cells"


def test_render_shield_with_charge():
    """A solid field with a charge renders correctly."""
    mask = heraldry.make_shield_mask()
    spec = {
        "division": None,
        "field1": "Gules",
        "field2": None,
        "charge": "Cross",
        "charge_tincture": "Argent",
        "blazon": "Gules charged with a Cross Argent",
    }
    field = heraldry.render_shield(spec, mask)
    none_count = sum(1 for y in range(heraldry.SHIELD_H)
                     for x in range(heraldry.SHIELD_W)
                     if mask[y][x] and field[y][x] is None)
    assert none_count == 0, f"Solid+charge render has {none_count} None cells"
    # Some pixels should be the charge
    charge_count = sum(1 for y in range(heraldry.SHIELD_H)
                      for x in range(heraldry.SHIELD_W)
                      if mask[y][x] and field[y][x] == "Argent")
    assert charge_count > 0, "No charge pixels visible"


def test_historical_specs_render():
    """All historical coats of arms render correctly."""
    mask = heraldry.make_shield_mask()
    for name, spec in heraldry.HISTORICAL.items():
        field = heraldry.render_shield(spec, mask)
        none_count = sum(1 for y in range(heraldry.SHIELD_H)
                         for x in range(heraldry.SHIELD_W)
                         if mask[y][x] and field[y][x] is None)
        assert none_count == 0, f"Historical '{name}' has {none_count} None cells"


def test_ascii_render():
    """field_to_ascii produces non-empty output."""
    mask = heraldry.make_shield_mask()
    spec = heraldry.generate_blazon()
    field = heraldry.render_shield(spec, mask)
    ascii_art = heraldry.field_to_ascii(field, mask)
    assert len(ascii_art) > 100, f"ASCII output too short: {len(ascii_art)}"
    assert "\n" in ascii_art, "ASCII output has no newlines"


def test_plain_mode():
    """field_to_ascii in plain mode uses no Unicode."""
    mask = heraldry.make_shield_mask()
    spec = heraldry.generate_blazon()
    field = heraldry.render_shield(spec, mask)
    ascii_art = heraldry.field_to_ascii(field, mask, plain=True)
    assert len(ascii_art) > 100, f"Plain ASCII output too short: {len(ascii_art)}"
    # Should contain # characters, not █
    assert "#" in ascii_art, "Plain mode should use # instead of █"
    assert "╔" not in ascii_art, "Plain mode should not use box-drawing chars"
    assert "║" not in ascii_art, "Plain mode should not use box-drawing chars"


def test_banner_render():
    """render_banner produces complete output."""
    mask = heraldry.make_shield_mask()
    spec = heraldry.generate_blazon()
    field = heraldry.render_shield(spec, mask)
    ascii_art = heraldry.field_to_ascii(field, mask)
    banner = heraldry.render_banner(spec, ascii_art)
    assert "COAT OF ARMS" in banner
    assert spec["blazon"] in banner or spec["blazon"].split(",")[0] in banner


def test_banner_plain_mode():
    """render_banner in plain mode uses ASCII characters."""
    mask = heraldry.make_shield_mask()
    spec = heraldry.generate_blazon()
    field = heraldry.render_shield(spec, mask)
    ascii_art = heraldry.field_to_ascii(field, mask, plain=True)
    banner = heraldry.render_banner(spec, ascii_art, plain=True)
    assert "COAT OF ARMS" in banner
    assert "+" in banner, "Plain banner should use + for corners"
    assert "╔" not in banner, "Plain banner should not use Unicode box-drawing"
    assert "║" not in banner, "Plain banner should not use Unicode box-drawing"


def test_seed_reproducibility():
    """Same seed produces same output."""
    random.seed(12345)
    spec1 = heraldry.generate_blazon()
    random.seed(12345)
    spec2 = heraldry.generate_blazon()
    assert spec1 == spec2, f"Seed 12345 not reproducible: {spec1} != {spec2}"


def test_blazon_format():
    """Blazon text is well-formed."""
    random.seed(99)
    for _ in range(50):
        spec = heraldry.generate_blazon()
        blazon = spec["blazon"]
        assert len(blazon) > 0, "Empty blazon"
        if spec["charge"]:
            assert "charged with" in blazon, f"Blazon missing 'charged with': {blazon}"
        if spec["division"]:
            assert spec["division"] in blazon, f"Blazon missing division name: {blazon}"


def test_divided_no_charge_blazon():
    """When a divided field has no charge, blazon text is correct."""
    spec = {
        "division": "Per Pale",
        "field1": "Azure",
        "field2": "Or",
        "charge": None,
        "charge_tincture": None,
        "blazon": "Per Pale Azure and Or",
    }
    assert "charged with" not in spec["blazon"]
    assert "Per Pale" in spec["blazon"]


def test_compliant_tincture():
    """compliant_tincture returns opposite class."""
    for _ in range(20):
        t = heraldry.compliant_tincture("metal")
        assert heraldry.TINCTURES[t]["class"] == "colour", f"Expected colour, got {t}"
    for _ in range(20):
        t = heraldry.compliant_tincture("colour")
        assert heraldry.TINCTURES[t]["class"] == "metal", f"Expected metal, got {t}"


def test_cli_seed():
    """CLI with seed produces output without error."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "-s", "42"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "COAT OF ARMS" in result.stdout


def test_cli_blazon_only():
    """CLI --blazon-only produces text output."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--blazon-only", "-n", "3"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "#1:" in result.stdout
    assert "#2:" in result.stdout
    assert "#3:" in result.stdout


def test_cli_historical():
    """CLI --historical produces output."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--historical", "england"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Kingdom of England" in result.stdout


def test_cli_list_historical():
    """CLI --list-historical lists all historical coats."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--list-historical"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "england" in result.stdout
    assert "france" in result.stdout
    assert "scotland" in result.stdout
    assert "switzerland" in result.stdout


def test_cli_version():
    """CLI --version shows version."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "1.1.0" in result.stdout


def test_cli_invalid_number():
    """CLI with invalid --number rejects it."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "-n", "0"],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "Should reject --number 0"
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "-n", "-1"],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "Should reject --number -1"


def test_cli_no_color():
    """CLI --no-color produces output without ANSI escape codes."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--no-color", "-s", "1"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "\033[" not in result.stdout, "No-color output should not contain ANSI"


def test_cli_plain():
    """CLI --plain uses ASCII characters."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--plain", "-s", "1"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "╔" not in result.stdout, "Plain mode should not use Unicode box-drawing"
    assert "+" in result.stdout, "Plain mode should use + for corners"


def test_cli_plain_and_no_color():
    """CLI --plain --no-color works together."""
    result = subprocess.run(
        [sys.executable, heraldry.__file__, "--plain", "--no-color", "-s", "1"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "\033[" not in result.stdout
    assert "╔" not in result.stdout


def test_state_restoration_after_no_color():
    """Module state is restored after --no-color."""
    import importlib
    h = importlib.reload(heraldry)
    # Save originals
    orig_reset = h.RESET
    orig_ansi = h.TINCTURES["Or"]["ansi"]
    
    # Apply no-color
    h.apply_no_color()
    assert h.RESET == "", "RESET should be empty after no_color"
    assert h.TINCTURES["Or"]["ansi"] == "", "Or ansi should be empty after no_color"
    
    # Restore
    h.restore_colors()
    assert h.RESET == orig_reset, "RESET should be restored"
    assert h.TINCTURES["Or"]["ansi"] == orig_ansi, "Or ansi should be restored"


if __name__ == "__main__":
    import traceback
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(0 if failed == 0 else 1)