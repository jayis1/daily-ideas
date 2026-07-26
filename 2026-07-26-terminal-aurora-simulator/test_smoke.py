import aurora

# Smoke test: init state and build several frames for every palette
for name in aurora.PALETTE_ORDER:
    s = aurora.init_state(80, 24, 42, name)
    s.time = 3.0
    frame = aurora.build_frame(s)
    assert len(frame) > 0
    # verify palette lookup works across the range
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        c = aurora.palette_color(name, t)
        assert len(c) == 3 and all(0 <= x <= 255 for x in c)
    # advance time and render a few more frames to exercise the loop
    for _ in range(5):
        s.time += 0.1
        f2 = aurora.build_frame(s)
        assert len(f2) > 0

# Verify resize reinit
s = aurora.init_state(80, 24, 42, "green")
aurora.reinit_for_size(s, 100, 30)
assert s.width == 100 and s.height == 30

# Verify handle_key
assert aurora.handle_key("q", s) is True
assert aurora.handle_key("esc", s) is True
assert aurora.handle_key(None, s) is False
assert aurora.handle_key("c", s) is False
assert s.palette_name in aurora.PALETTE_ORDER

print("OK: all palettes render, resize + keys work, smoke test passed")