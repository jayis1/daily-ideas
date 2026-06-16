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
    
    # Should NOT contain bottom 3 (D, E, F)
    # Note: these might appear in different forms, check carefully
    # F=10 is lowest so shouldn't be in top 3
    # Count lines that have a rank prefix (#1, #2, etc) indicating data rows
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