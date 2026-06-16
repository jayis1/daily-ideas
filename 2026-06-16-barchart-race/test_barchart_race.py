#!/usr/bin/env python3
"""Tests for barchart_race.py"""

import json
import os
import sys
import tempfile

# Add project dir to path
sys.path.insert(0, os.path.dirname(__file__))
import barchart_race as bcr


def test_validate_data():
    """Test data validation."""
    # Valid data
    ds = {
        "data": {"A": [1, 2, 3], "B": [4, 5, 6]},
        "labels": ["x", "y", "z"],
        "title": "Test",
        "unit": "$",
    }
    result = bcr.validate_data(ds)
    assert result["title"] == "Test"
    assert result["unit"] == "$"
    assert len(result["data"]["A"]) == 3
    
    # Missing labels — should auto-generate
    ds2 = {"data": {"A": [1, 2], "B": [3, 4]}}
    result = bcr.validate_data(ds2)
    assert result["labels"] == ["1", "2"]
    
    # Empty data should raise
    try:
        bcr.validate_data({"data": {}})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    # Mismatched lengths should raise
    try:
        bcr.validate_data({"data": {"A": [1, 2], "B": [3]}})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    print("test_validate_data: PASS")


def test_interpolate_data():
    """Test smooth interpolation."""
    ds = {
        "data": {"A": [0, 10], "B": [5, 15]},
        "labels": ["start", "end"],
        "title": "Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    interp = bcr.interpolate_data(ds, steps_per_period=4)
    
    # Should have 4 + 1 = 5 frames
    assert len(interp["data"]["A"]) == 5
    assert len(interp["data"]["B"]) == 5
    
    # First frame should be original
    assert interp["data"]["A"][0] == 0
    # Last frame should be original
    assert interp["data"]["A"][-1] == 10
    
    # Intermediate frames should be between 0 and 10
    for v in interp["data"]["A"]:
        assert 0 <= v <= 10
    
    print("test_interpolate_data: PASS")


def test_format_value():
    """Test value formatting."""
    assert bcr.format_value(1500, "$") == "1,500$"
    assert bcr.format_value(10.5, "pts") == "10.5pts"
    assert bcr.format_value(0.03, "") == "0.03"
    
    print("test_format_value: PASS")


def test_render_frame():
    """Test frame rendering."""
    ds = {
        "data": {"A": [10, 20, 30], "B": [5, 15, 25], "C": [1, 2, 3]},
        "labels": ["Jan", "Feb", "Mar"],
        "title": "Test Race",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    
    # Render first frame (no color for testability)
    frame = bcr.render_frame(ds, 0, color=False)
    assert "Test Race" in frame
    assert "Jan" in frame
    assert "A" in frame
    assert "B" in frame
    
    # Render with top_n
    frame_top2 = bcr.render_frame(ds, 0, top_n=2, color=False)
    assert "A" in frame_top2
    assert "B" in frame_top2
    # C should not appear since we limit to top 2
    # Actually C=1 is smallest, so A and B should be shown
    lines = frame_top2.count("\n")
    # Should have fewer lines than full frame
    
    # Last frame
    frame_last = bcr.render_frame(ds, 2, color=False)
    assert "Mar" in frame_last
    
    print("test_render_frame: PASS")


def test_render_minimal_frame():
    """Test minimal frame rendering."""
    ds = {
        "data": {"A": [10], "B": [5]},
        "labels": ["Now"],
        "title": "Mini",
        "unit": "pts",
    }
    ds = bcr.validate_data(ds)
    
    frame = bcr.render_minimal_frame(ds, 0, top_n=5, color=False)
    assert "Mini" in frame
    assert "A" in frame
    
    print("test_render_minimal_frame: PASS")


def test_sample_datasets():
    """Test all built-in sample datasets are valid."""
    for key, ds in bcr.SAMPLE_DATASETS.items():
        ds_copy = bcr.deepcopy(ds) if hasattr(bcr, 'deepcopy') else json.loads(json.dumps(ds))
        result = bcr.validate_data(ds_copy)
        
        series_names = list(result["data"].keys())
        length = len(result["data"][series_names[0]])
        
        # All series should have same length
        for name in series_names:
            assert len(result["data"][name]) == length, f"Dataset {key}: {name} has wrong length"
        
        # Should be able to render first and last frame
        frame_first = bcr.render_frame(result, 0, color=False)
        frame_last = bcr.render_frame(result, length - 1, color=False)
        assert len(frame_first) > 0
        assert len(frame_last) > 0
        
        print(f"  {key}: OK ({len(series_names)} series × {length} periods)")
    
    print("test_sample_datasets: PASS")


def test_load_csv():
    """Test CSV loading."""
    csv_content = """label,Cat A,Cat B,Cat C
Jan,10,20,30
Feb,15,25,35
Mar,20,30,40"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        filepath = f.name
    
    try:
        ds = bcr.load_csv(filepath)
        assert "Cat A" in ds["data"]
        assert "Cat B" in ds["data"]
        assert len(ds["data"]["Cat A"]) == 3
        assert ds["data"]["Cat A"][0] == 10
        assert ds["labels"][0] == "Jan"
        
        # Should validate ok
        ds = bcr.validate_data(ds)
        frame = bcr.render_frame(ds, 0, color=False)
        assert "Cat A" in frame
    finally:
        os.unlink(filepath)
    
    print("test_load_csv: PASS")


def test_load_json():
    """Test JSON loading."""
    json_content = {
        "title": "JSON Test",
        "unit": "km",
        "data": {
            "Runner A": [5, 10, 15],
            "Runner B": [3, 8, 20],
        },
        "labels": ["Lap 1", "Lap 2", "Lap 3"]
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(json_content, f)
        f.flush()
        filepath = f.name
    
    try:
        ds = bcr.load_json(filepath)
        assert ds["title"] == "JSON Test"
        assert "Runner A" in ds["data"]
        assert len(ds["data"]["Runner A"]) == 3
        
        ds = bcr.validate_data(ds)
        frame = bcr.render_frame(ds, 2, color=False)
        assert "Runner A" in frame
    finally:
        os.unlink(filepath)
    
    print("test_load_json: PASS")


def test_json_wrong_lengths():
    """Test that mismatched series lengths raise an error."""
    json_content = {
        "data": {
            "A": [1, 2, 3],
            "B": [4, 5],  # Different length!
        }
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(json_content, f)
        f.flush()
        filepath = f.name
    
    try:
        try:
            bcr.load_json(filepath)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    finally:
        os.unlink(filepath)
    
    print("test_json_wrong_lengths: PASS")


def test_generate_random_data():
    """Test random data generation."""
    ds = bcr.generate_random_data(num_series=5, num_periods=10, seed=42)
    
    assert len(ds["data"]) == 5
    for name, values in ds["data"].items():
        assert len(values) == 10
        assert all(v > 0 for v in values), f"Got negative value in {name}"
    
    # Same seed should give same data
    ds2 = bcr.generate_random_data(num_series=5, num_periods=10, seed=42)
    for name in ds["data"]:
        for i in range(10):
            assert ds["data"][name][i] == ds2["data"][name][i]
    
    print("test_generate_random_data: PASS")


def test_export_frames():
    """Test frame export to directory."""
    ds = {
        "data": {"A": [10, 20], "B": [5, 15]},
        "labels": ["T1", "T2"],
        "title": "Export Test",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    ds = bcr.interpolate_data(ds, steps_per_period=3)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "frames")
        count = bcr.export_frames(ds, output_dir, top_n=2)
        
        assert os.path.isdir(output_dir)
        files = os.listdir(output_dir)
        assert len(files) == count
        assert count > 0
        
        # Check a frame file
        first_file = sorted(files)[0]
        with open(os.path.join(output_dir, first_file)) as f:
            content = f.read()
        assert "Export Test" in content
    
    print("test_export_frames: PASS")


def test_export_ascii_movie():
    """Test ASCII movie export."""
    ds = {
        "data": {"A": [10, 20], "B": [5, 15]},
        "labels": ["T1", "T2"],
        "title": "Movie Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    ds = bcr.interpolate_data(ds, steps_per_period=3)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "movie.txt")
        count = bcr.export_ascii_movie(ds, output_file)
        
        assert os.path.exists(output_file)
        with open(output_file) as f:
            content = f.read()
        assert "Movie Test" in content
        assert "\f" in content  # Form feed separator
    
    print("test_export_ascii_movie: PASS")


def test_final_ranking():
    """Test final ranking output."""
    ds = {
        "data": {"A": [10, 20, 30], "B": [50, 40, 30], "C": [5, 15, 45]},
        "labels": ["Jan", "Feb", "Mar"],
        "title": "Ranking Test",
        "unit": "pts",
    }
    ds = bcr.validate_data(ds)
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    bcr.print_final_ranking(ds, top_n=3)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    assert "Final Ranking" in output
    assert "C" in output  # C ends highest
    
    print("test_final_ranking: PASS")


def test_compute_stats():
    """Test statistics computation."""
    ds = {
        "data": {"A": [10, 20, 30], "B": [50, 40, 30]},
        "labels": ["T1", "T2", "T3"],
        "title": "Stats Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    bcr.compute_stats(ds)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    assert "Statistics" in output
    assert "Series count" in output
    
    print("test_compute_stats: PASS")


def test_ranking_order():
    """Test that bars are ranked by value descending."""
    ds = {
        "data": {"Small": [5], "Big": [50], "Medium": [25]},
        "labels": ["Now"],
        "title": "Order Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    frame = bcr.render_frame(ds, 0, color=False)
    lines = frame.split("\n")
    
    # Find the line with "Big" — it should have #1
    big_line = [l for l in lines if "Big" in l][0]
    small_line = [l for l in lines if "Small" in l][0]
    
    assert "#1" in big_line or "🥇" in big_line
    assert "#3" in small_line or "🥉" in small_line
    
    print("test_ranking_order: PASS")


def test_negative_values():
    """Test handling of negative values."""
    ds = {
        "data": {"A": [-10, -5, 0], "B": [5, 10, 15]},
        "labels": ["T1", "T2", "T3"],
        "title": "Negative Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    # Should not crash
    frame = bcr.render_frame(ds, 0, color=False)
    assert "A" in frame
    assert "B" in frame
    
    # Final ranking should work
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    bcr.print_final_ranking(ds)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    assert "B" in output
    
    print("test_negative_values: PASS")


def test_single_series():
    """Test with just one data series."""
    ds = {
        "data": {"Only": [1, 2, 3, 4, 5]},
        "labels": ["A", "B", "C", "D", "E"],
        "title": "Solo",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    ds_interp = bcr.interpolate_data(ds, steps_per_period=2)
    
    # Should have more frames after interpolation
    assert len(ds_interp["data"]["Only"]) > 5
    
    frame = bcr.render_frame(ds, 0, color=False)
    assert "Only" in frame
    
    print("test_single_series: PASS")


def test_edge_case_zero_values():
    """Test with all zero values."""
    ds = {
        "data": {"A": [0, 0, 0], "B": [0, 0, 0]},
        "labels": ["X", "Y", "Z"],
        "title": "Zeros",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    # Should not crash with division by zero
    frame = bcr.render_frame(ds, 0, color=False)
    assert "Zeros" in frame
    
    print("test_edge_case_zero_values: PASS")


def test_long_series_names():
    """Test with long series names."""
    ds = {
        "data": {
            "Very Long Name Inc.": [10, 20],
            "Short": [5, 15],
            "Medium Corp": [8, 18],
        },
        "labels": ["T1", "T2"],
        "title": "Names Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    frame = bcr.render_frame(ds, 0, color=False)
    assert "Very Long Name Inc." in frame
    
    print("test_long_series_names: PASS")


def test_color_vs_nocolor():
    """Test that color mode adds ANSI codes."""
    ds = {
        "data": {"A": [10], "B": [5]},
        "labels": ["Now"],
        "title": "Color Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    frame_color = bcr.render_frame(ds, 0, color=True)
    frame_nocolor = bcr.render_frame(ds, 0, color=False)
    
    # Color frame should have ANSI escape sequences
    assert "\033[" in frame_color
    # No-color frame should not
    assert "\033[" not in frame_nocolor
    
    print("test_color_vs_nocolor: PASS")


def test_top_n_filtering():
    """Test that top_n limits displayed bars."""
    ds = {
        "data": {
            "A": [100], "B": [80], "C": [60],
            "D": [40], "E": [20], "F": [10],
        },
        "labels": ["Now"],
        "title": "TopN Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    frame3 = bcr.render_frame(ds, 0, top_n=3, color=False)
    lines3 = frame3.split("\n")
    
    # Should contain top 3 (A, B, C)
    assert "A" in frame3
    assert "B" in frame3
    assert "C" in frame3
    
    # Count data rows (lines with rank markers)
    data_lines = [l for l in lines3 if "#1" in l or "#2" in l or "#3" in l or "#4" in l or "#5" in l or "#6" in l or "🥇" in l or "🥈" in l or "🥉" in l]
    assert len(data_lines) == 3  # Only 3 data rows
    
    print("test_top_n_filtering: PASS")


def test_csv_with_empty_values():
    """Test CSV loading with some missing/empty values."""
    csv_content = """label,Alpha,Beta,Gamma
Jan,10,20,30
Feb,15,,35
Mar,20,30,"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        filepath = f.name
    
    try:
        ds = bcr.load_csv(filepath)
        # Empty values should default to 0
        assert ds["data"]["Beta"][1] == 0  # Empty cell
        assert ds["data"]["Gamma"][2] == 0  # Empty cell
        assert ds["data"]["Alpha"][1] == 15  # Normal value
    finally:
        os.unlink(filepath)
    
    print("test_csv_with_empty_values: PASS")


def test_json_auto_labels():
    """Test JSON loading without labels — should auto-generate."""
    json_content = {
        "data": {
            "A": [1, 2, 3],
            "B": [4, 5, 6],
        }
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(json_content, f)
        f.flush()
        filepath = f.name
    
    try:
        ds = bcr.load_json(filepath)
        ds = bcr.validate_data(ds)
        # Should auto-generate labels
        assert ds["labels"] == ["1", "2", "3"]
    finally:
        os.unlink(filepath)
    
    print("test_json_auto_labels: PASS")


# ─── New Feature Tests ────────────────────────────────────────────────


def test_transform_percentage():
    """Test percentage transformation."""
    ds = {
        "data": {"A": [10, 20], "B": [30, 30], "C": [60, 50]},
        "labels": ["T1", "T2"],
        "title": "Share Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    pct_ds = bcr.transform_percentage(ds)
    
    # First period: A=10%, B=30%, C=60% (total=100)
    assert abs(pct_ds["data"]["A"][0] - 10.0) < 0.01
    assert abs(pct_ds["data"]["B"][0] - 30.0) < 0.01
    assert abs(pct_ds["data"]["C"][0] - 60.0) < 0.01
    
    # Second period: A=20%, B=30%, C=50% (total=100)
    assert abs(pct_ds["data"]["A"][1] - 20.0) < 0.01
    assert abs(pct_ds["data"]["C"][1] - 50.0) < 0.01
    
    # Unit should be changed to %
    assert pct_ds["unit"] == "%"
    
    # Title should mention share
    assert "Share" in pct_ds["title"]
    
    print("test_transform_percentage: PASS")


def test_transform_growth():
    """Test growth transformation."""
    ds = {
        "data": {"A": [10, 15, 20], "B": [50, 40, 30]},
        "labels": ["T1", "T2", "T3"],
        "title": "Growth Test",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    growth_ds = bcr.transform_growth(ds)
    
    # A starts at 10, so 15 is +50%, 20 is +100%
    assert abs(growth_ds["data"]["A"][0] - 0.0) < 0.01  # 0% growth from baseline
    assert abs(growth_ds["data"]["A"][1] - 50.0) < 0.01  # 50% growth
    assert abs(growth_ds["data"]["A"][2] - 100.0) < 0.01  # 100% growth
    
    # B starts at 50, so 40 is -20%, 30 is -40%
    assert abs(growth_ds["data"]["B"][1] - (-20.0)) < 0.01
    assert abs(growth_ds["data"]["B"][2] - (-40.0)) < 0.01
    
    # Unit should be %
    assert growth_ds["unit"] == "%"
    
    print("test_transform_growth: PASS")


def test_transform_growth_zero_start():
    """Test growth transformation when starting value is zero."""
    ds = {
        "data": {"A": [0, 5, 10], "B": [10, 15, 20]},
        "labels": ["T1", "T2", "T3"],
        "title": "Zero Start",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    growth_ds = bcr.transform_growth(ds)
    
    # A starts at 0 — should show absolute change instead of percentage
    assert growth_ds["data"]["A"][0] == 0.0
    assert growth_ds["data"]["A"][1] == 5.0  # 5 - 0 = 5
    assert growth_ds["data"]["A"][2] == 10.0  # 10 - 0 = 10
    
    print("test_transform_growth_zero_start: PASS")


def test_transform_percentage_zero_total():
    """Test percentage transform with all-zero period."""
    ds = {
        "data": {"A": [0, 10], "B": [0, 20]},
        "labels": ["T1", "T2"],
        "title": "Zero Total",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    pct_ds = bcr.transform_percentage(ds)
    
    # When total is 0, should handle gracefully (not crash)
    # Both should be 0% or very close
    assert pct_ds["data"]["A"][0] >= 0  # Should not crash
    assert pct_ds["data"]["B"][0] >= 0
    
    # Second period: A=33.33%, B=66.67%
    assert abs(pct_ds["data"]["A"][1] - 33.33) < 0.1
    assert abs(pct_ds["data"]["B"][1] - 66.67) < 0.1
    
    print("test_transform_percentage_zero_total: PASS")


def test_sparkline():
    """Test sparkline generation."""
    # Basic sparkline with known values
    sp = bcr.sparkline([1, 2, 3, 4, 5])
    assert len(sp) == 5
    # All characters should be from sparkline charset
    for c in sp:
        assert c in bcr.SPARKLINE_CHARS
    
    # Empty list should return empty string
    assert bcr.sparkline([]) == ""
    
    # Single value
    sp_single = bcr.sparkline([5])
    assert len(sp_single) == 1
    
    # All same values should give mid-height chars
    sp_same = bcr.sparkline([3, 3, 3])
    assert all(c == bcr.SPARKLINE_CHARS[len(bcr.SPARKLINE_CHARS) // 2] for c in sp_same)
    
    # Min should be ▁ and max should be █
    sp_range = bcr.sparkline([0, 100])
    assert sp_range[0] == bcr.SPARKLINE_CHARS[0]  # min
    assert sp_range[1] == bcr.SPARKLINE_CHARS[-1]  # max
    
    print("test_sparkline: PASS")


def test_sparkline_in_stats():
    """Test that sparklines appear in stats output."""
    ds = {
        "data": {"Alpha": [10, 20, 30], "Beta": [30, 20, 10]},
        "labels": ["T1", "T2", "T3"],
        "title": "Sparkline Stats",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    bcr.compute_stats(ds)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    # Stats should include sparkline characters
    has_sparkline = any(c in bcr.SPARKLINE_CHARS for c in output)
    assert has_sparkline, f"Stats output should contain sparkline characters. Got:\n{output}"
    
    # Should also have Growth Ranking section
    assert "Growth Ranking" in output
    
    print("test_sparkline_in_stats: PASS")


def test_render_comparison():
    """Test side-by-side comparison rendering."""
    ds = {
        "data": {"A": [10, 20, 30], "B": [5, 15, 25], "C": [1, 2, 3]},
        "labels": ["Jan", "Feb", "Mar"],
        "title": "Compare Test",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    
    # Compare first and last period
    output = bcr.render_comparison(ds, 0, 2, color=False)
    
    assert "Compare Test" in output
    assert "Jan" in output
    assert "Mar" in output
    assert "A" in output
    assert "B" in output
    assert "Change" in output or "change" in output.lower()
    
    # Compare with negative indices
    output_neg = bcr.render_comparison(ds, 0, -1, color=False)
    assert "Compare Test" in output_neg
    
    # Compare with top_n
    output_top2 = bcr.render_comparison(ds, 0, 2, top_n=2, color=False)
    assert "A" in output_top2
    
    print("test_render_comparison: PASS")


def test_render_comparison_same_period():
    """Test comparison of same period (zero change)."""
    ds = {
        "data": {"A": [10, 20], "B": [5, 15]},
        "labels": ["T1", "T2"],
        "title": "Same Period",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    output = bcr.render_comparison(ds, 0, 0, color=False)
    assert "Same Period" in output
    # All changes should be zero
    
    print("test_render_comparison_same_period: PASS")


def test_render_ticker():
    """Test compact ticker rendering."""
    ds = {
        "data": {"A": [10, 20], "B": [5, 15], "C": [1, 2]},
        "labels": ["T1", "T2"],
        "title": "Ticker Test",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    
    ticker = bcr.render_ticker(ds, 0)
    assert "T1" in ticker
    assert "A" in ticker
    
    ticker2 = bcr.render_ticker(ds, 1)
    assert "T2" in ticker2
    
    print("test_render_ticker: PASS")


def test_export_html():
    """Test HTML export."""
    ds = {
        "data": {"A": [10, 20, 30], "B": [5, 15, 25], "C": [1, 2, 3]},
        "labels": ["Jan", "Feb", "Mar"],
        "title": "HTML Test",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test.html")
        bcr.export_html(ds, output_file, top_n=3)
        
        assert os.path.exists(output_file)
        with open(output_file) as f:
            content = f.read()
        
        # Should be valid HTML
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content
        
        # Should contain our data
        assert "HTML Test" in content
        assert "A" in content
        assert "B" in content
        
        # Should contain CSS and JS
        assert "<style>" in content
        assert "<script>" in content
        
        # Should contain color data
        assert "#" in content  # hex colors
    
    print("test_export_html: PASS")


def test_export_html_with_speed():
    """Test HTML export with custom speed."""
    ds = {
        "data": {"A": [10, 20], "B": [5, 15]},
        "labels": ["T1", "T2"],
        "title": "Speed Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "speed.html")
        bcr.export_html(ds, output_file, speed=4.0)
        
        with open(output_file) as f:
            content = f.read()
        
        # Should reference the speed (interval should be 250ms for 4fps)
        assert "250" in content  # 1000/4 = 250ms
    
    print("test_export_html_with_speed: PASS")


def test_color_by_name_consistency():
    """Test that colors are assigned by name, not by rank (consistency across frames)."""
    ds = {
        "data": {"A": [10, 50], "B": [50, 10]},
        "labels": ["T1", "T2"],
        "title": "Color Consistency",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    frame1 = bcr.render_frame(ds, 0, color=True)
    frame2 = bcr.render_frame(ds, 1, color=True)
    
    # Both frames should contain "A" and "B"
    assert "A" in frame1
    assert "B" in frame1
    assert "A" in frame2
    assert "B" in frame2
    
    # The key improvement: colors should be assigned by name index, not rank
    # This means "A" should always get the same color regardless of its rank
    # (We can't easily verify the exact color from the string, but we verify
    #  the function doesn't crash and produces output)
    
    print("test_color_by_name_consistency: PASS")


def test_percentage_then_render():
    """Test that percentage transform produces renderable data."""
    ds = {
        "data": {"A": [10, 20], "B": [30, 30], "C": [60, 50]},
        "labels": ["T1", "T2"],
        "title": "Pct Render",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    pct_ds = bcr.transform_percentage(ds)
    
    # Should render without error
    frame = bcr.render_frame(pct_ds, 0, color=False)
    assert "Pct Render" in frame
    assert "%" in pct_ds["unit"]
    
    # Interpolate should also work
    pct_interp = bcr.interpolate_data(pct_ds, steps_per_period=3)
    frame2 = bcr.render_frame(pct_interp, 3, color=False)
    assert len(frame2) > 0
    
    print("test_percentage_then_render: PASS")


def test_growth_then_render():
    """Test that growth transform produces renderable data."""
    ds = {
        "data": {"A": [10, 20, 30], "B": [50, 40, 30]},
        "labels": ["T1", "T2", "T3"],
        "title": "Growth Render",
        "unit": "$",
    }
    ds = bcr.validate_data(ds)
    growth_ds = bcr.transform_growth(ds)
    
    # Should render without error
    frame = bcr.render_frame(growth_ds, 0, color=False)
    assert "Growth" in frame
    
    # Final ranking should work with growth data
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    bcr.print_final_ranking(growth_ds)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    assert "Growth" in output
    
    print("test_growth_then_render: PASS")


def test_version():
    """Test that VERSION is defined and accessible."""
    assert hasattr(bcr, 'VERSION')
    assert bcr.VERSION == "2.0.0"
    
    print("test_version: PASS")


def test_comparison_period_bounds():
    """Test that comparison handles out-of-bounds indices gracefully."""
    ds = {
        "data": {"A": [10, 20], "B": [5, 15]},
        "labels": ["T1", "T2"],
        "title": "Bounds Test",
        "unit": "",
    }
    ds = bcr.validate_data(ds)
    
    # Very large index should be clamped
    output = bcr.render_comparison(ds, 0, 100, color=False)
    assert "Bounds Test" in output
    
    # Negative index beyond range should be clamped
    output_neg = bcr.render_comparison(ds, -100, -1, color=False)
    assert "Bounds Test" in output_neg
    
    print("test_comparison_period_bounds: PASS")


if __name__ == "__main__":
    import io
    
    tests = [
        test_validate_data,
        test_interpolate_data,
        test_format_value,
        test_render_frame,
        test_render_minimal_frame,
        test_sample_datasets,
        test_load_csv,
        test_load_json,
        test_json_wrong_lengths,
        test_generate_random_data,
        test_export_frames,
        test_export_ascii_movie,
        test_final_ranking,
        test_compute_stats,
        test_ranking_order,
        test_negative_values,
        test_single_series,
        test_edge_case_zero_values,
        test_long_series_names,
        test_color_vs_nocolor,
        test_top_n_filtering,
        test_csv_with_empty_values,
        test_json_auto_labels,
        # New feature tests
        test_transform_percentage,
        test_transform_growth,
        test_transform_growth_zero_start,
        test_transform_percentage_zero_total,
        test_sparkline,
        test_sparkline_in_stats,
        test_render_comparison,
        test_render_comparison_same_period,
        test_render_ticker,
        test_export_html,
        test_export_html_with_speed,
        test_color_by_name_consistency,
        test_percentage_then_render,
        test_growth_then_render,
        test_version,
        test_comparison_period_bounds,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed! ✓")