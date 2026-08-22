from keyboard_heatmap import analyze_text, render_heatmap, normalize_char


def test_normalize_char_maps_shifted_symbols():
    assert normalize_char("A") == "a"
    assert normalize_char("!") == "1"
    assert normalize_char("?") == "/"


def test_analysis_counts_rows_hands_and_bigrams():
    analysis = analyze_text("Dad adds jazz.")
    assert analysis.counts["d"] == 4
    assert analysis.counts["a"] == 3
    assert analysis.row_usage["home row"] >= 5
    assert analysis.hand_usage["left"] > analysis.hand_usage["right"]
    assert analysis.bigrams["da"] >= 1


def test_render_heatmap_mentions_space_cell():
    analysis = analyze_text("a a")
    rendered = render_heatmap(analysis, use_color=False)
    assert "space" in rendered
    assert "a" in rendered
