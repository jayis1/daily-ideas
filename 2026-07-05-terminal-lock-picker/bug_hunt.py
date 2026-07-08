#!/usr/bin/env python3
"""Bug hunting script for lock_picker module."""

import random
import sys
from lock_picker import Lock, Pin, DIFFICULTY_NAMES, MIN_PINS, MAX_PINS

bugs_found = []

# Bug 1: Raking wears pick on Medium difficulty, but README says only Hard/Master
random.seed(42)
lock = Lock(4, 3)  # Medium difficulty
lock.apply_tension(0.5)
initial_health = lock.pick_health
lock.rack()
print(f'Medium raking wear: {initial_health} -> {lock.pick_health}')
if lock.pick_health < initial_health:
    bugs_found.append('BUG: Raking wears pick on Medium difficulty (3), but README claims only Hard/Master. Code at line 285-286 checks difficulty >= 3.')

# Bug 2: Broken pick lift
random.seed(100)
lock = Lock(3, 5)
lock.apply_tension(0.4)
lock.pick_health = 0.0
result2 = lock.lift_pin(0, 0.02)
print(f'Broken pick lift result: {result2}')
if result2 is not False:
    bugs_found.append(f'BUG: Broken pick should return False, got {result2}')

# Bug 3: Rake-only open test
random.seed(42)
lock = Lock(3, 1)
lock.apply_tension(0.5)
for _ in range(100):
    lock.rack()
    if lock.check_open():
        print('Rake-only open: OK')
        break
else:
    print('Rake-only: Could not open (may be expected)')

# Bug 4: Lifting an already-set pin can potentially unset it
random.seed(42)
lock = Lock(3, 1)
lock.apply_tension(0.5)
for i, pin in enumerate(lock.pins):
    if pin.is_bound:
        while not pin.is_set:
            lock.lift_pin(i, 0.02)
        # Now try lifting it again  
        result = lock.lift_pin(i, 0.02)
        print(f'Lift already-set pin: result={result}, is_set={pin.is_set}')
        if not pin.is_set:
            bugs_found.append('BUG: Lifting an already-set pin can unset it!')
        break

# Bug 5: Overset pin handling
random.seed(42)
lock = Lock(3, 1)
lock.apply_tension(0.5)
for i, pin in enumerate(lock.pins):
    if not pin.is_bound:
        pin.current_height = 0.9
        lock.lift_pin(i, 0.2)
        print(f'Non-bound pin overset: height={pin.current_height:.3f}, is_set={pin.is_set}')
        break

# Bug 6: Binding at 0% tension
random.seed(42)
lock = Lock(5, 2)
lock.apply_tension(0.3)
bound_before = sum(1 for p in lock.pins if p.is_bound)
lock.apply_tension(0.0)
bound_after = sum(1 for p in lock.pins if p.is_bound)
print(f'Binding at 30%: {bound_before}, Binding at 0%: {bound_after}')
if bound_after > 0:
    bugs_found.append('BUG: Pins still bound at 0% tension!')

# Bug 7: check_open at exactly 0.2 tension
lock = Lock(3, 1)
for pin in lock.pins:
    pin.is_set = True
    pin.current_height = pin.key_height
lock.tension = 0.2
lock._update_binding()
print(f'check_open at exactly 0.2 tension: {lock.check_open()}')

# Bug 8: release_pin boundary
lock = Lock(5, 1)
pin = lock.pins[0]
pin.current_height = 0.01
lock.release_pin(0)
print(f'Very low pin after release: {pin.current_height}')

# Bug 9: Pin wobble
random.seed(42)
lock = Lock(5, 1)
for pin in lock.pins:
    print(f'Novice wobble: {pin.wobble:.4f}')

# Bug 10: pins_set_count consistency during full pick
random.seed(42)
lock = Lock(5, 2)
lock.apply_tension(0.5)
for _ in range(200):
    for i, pin in enumerate(lock.pins):
        if pin.is_bound and not pin.is_set:
            lock.lift_pin(i, 0.02)
    lock.apply_tension(lock.tension)
    computed = lock.pins_set_count
    actual = sum(1 for p in lock.pins if p.is_set)
    if computed != actual:
        bugs_found.append(f'BUG: pins_set_count={computed} but actual={actual}')
        break
    if lock.check_open():
        break

# Bug 11: Demo mode doesn't check for broken pick
# In run_demo, if pick_health goes to 0 on Master difficulty, the demo will keep
# calling lift_pin which returns False, stuck in an infinite loop
print()
print("=== Checking demo pick break issue ===")
random.seed(42)
lock = Lock(3, 5)  # Master difficulty
lock.apply_tension(0.4)
# Simulate what demo does - check if pick can break and cause infinite loop
for i, pin in enumerate(lock.pins):
    if pin.is_bound and not pin.is_set:
        # Wear the pick down to almost broken
        lock.pick_health = 0.001
        for attempt in range(5000):
            result = lock.lift_pin(i, 0.02)
            if pin.is_set or lock.pick_health <= 0:
                break
        print(f'Pick health after heavy lifting: {lock.pick_health}')
        if lock.pick_health <= 0:
            print(f'Pick BROKEN. Further lift results: {lock.lift_pin(i, 0.02)}')
            # In demo mode, this would cause an infinite loop since no pins can be set
            bugs_found.append('BUG: Demo mode can infinite-loop when pick breaks on Hard/Master difficulty - no check for broken pick')
        break

# Bug 12: main() doesn't print session result properly on KeyboardInterrupt path
# Line 1080: print(f"\\nLocks picked this session: {result if result is not None else 'interrupted'}")
# If curses.wrapper raises an exception other than KeyboardInterrupt, result is None but not from interrupt
# This is a minor display issue but not a crash

# Bug 13: In demo mode, spring decay is applied but the game's spring decay logic is in the game loop
# The demo applies its own spring decay at line 971 - let's verify it matches
# Game loop: decay = pin.spring_tension * 0.5
# Demo: pin.current_height = max(0.0, pin.current_height - pin.spring_tension * 0.5)
# These match - OK

# Bug 14: Check if _update_binding is called after a pin is set in the demo
# After setting a pin, the demo calls lock.apply_tension(lock.tension) which calls _update_binding
# This is correct - OK

# Bug 15: Check for race condition in rack() - raking can unset pins that were JUST set in same call
# Looking at the code (lines 280-283):
# The unset check happens AFTER the main loop, so this was already fixed in v1.2.0
# But let me verify
random.seed(42)
lock = Lock(4, 4)
lock.apply_tension(0.5)
# Set one pin manually
lock.pins[0].is_set = True
lock.pins[0].current_height = lock.pins[0].key_height
set_before = sum(1 for p in lock.pins if p.is_set)
lock.rack()
set_after = sum(1 for p in lock.pins if p.is_set)
print(f'Set pins before rake: {set_before}, after: {set_after}')
# This is working as designed - raking can unset on Hard+

# Bug 16: The main() function passes args.pins and args.difficulty directly to game
# even when they're None, but game handles it with start_pins/start_difficulty params
# Let me check: line 1074 uses start_pins=args.pins
# But args.pins can be None if not specified!
# The LockPickerGame constructor does: self.num_pins = start_pins if start_pins is not None else 5
# So that's fine

# Bug 17: What happens if you pass --pins without --difficulty or vice versa?
# --pins defaults to None, --difficulty defaults to None
# In main(): pins = args.pins if args.pins is not None else 5
#            difficulty = args.difficulty if args.difficulty is not None else 1
# Then: game = LockPickerGame(stdscr, start_pins=args.pins, start_difficulty=args.difficulty)
# Wait - this uses args.pins directly, not the local `pins` variable!
# So if --pins is not provided, args.pins is None, and start_pins=None
# In LockPickerGame: self.num_pins = start_pins if start_pins is not None else 5
# This actually works correctly since it falls back to 5. OK, no bug here.

# Bug 18: What if args.pins is None but args.difficulty is provided?
# start_pins=None -> num_pins=5 (default), start_difficulty=provided value. Fine.

# Bug 19: The victory loop calculates elapsed time incorrectly
# Line 876: elapsed = time.time() - self.start_time
# But self.start_time is set in new_lock() and the victory state transition
# already happened in _picking_loop where elapsed was also calculated.
# The victory loop recalculates elapsed from start_time, so it keeps ticking.
# This is actually correct behavior for a running clock, but it means the
# "time" displayed keeps changing during the victory screen. Not really a bug.

# Bug 20: Check that rack() returns correct count when pins are already set
random.seed(42)
lock = Lock(3, 1)
lock.apply_tension(0.5)
# Set all pins first
for pin in lock.pins:
    pin.is_set = True
    pin.current_height = pin.key_height
clicks = lock.rack()
print(f'Rack with all pins set: clicks={clicks}')
if clicks != 0:
    bugs_found.append(f'BUG: rack() should return 0 when all pins already set, got {clicks}')

# Bug 21: Check rack() tolerance difference
# In lift_pin: tolerance = 0.06 - (self.difficulty * 0.006)  -> Novice=0.054, Master=0.030
# In rack: tolerance = 0.06 - (self.difficulty * 0.008)  -> Novice=0.052, Master=0.020
# The tolerance for raking is STRICTER than for lifting, which makes sense (raking is less precise)
# But this isn't documented and could be confusing. Not really a bug.

# Bug 22: get_pick_health_bar has a visual bug for low health
# When health < 0.2, the bar uses '·' for both filled and unfilled portions
# Line 357: bar = '·' * filled + '·' * (width - filled)
# This means you can't tell how much health remains - the whole bar looks the same!
from lock_picker import get_pick_health_bar
bar_low = get_pick_health_bar(0.1, 20)
print(f'Low health bar: {bar_low}')
# Check if filled and unfilled are indistinguishable
bar_zero = get_pick_health_bar(0.0, 20)
print(f'Zero health bar: {bar_zero}')
# Both look the same - this is a UI bug

# Bug 23: Check lift_pin with broken pick (health=0)
lock = Lock(3, 1)
lock.pick_health = 0.0
result = lock.lift_pin(0, 0.02)
print(f'Lift with broken pick: {result}')  # Should be False
if result is not False:
    bugs_found.append(f'BUG: lift_pin with broken pick should return False, got {result}')

# Bug 24: Check the demo mode for the broken pick infinite loop more carefully
# In run_demo(), the loop condition is: while not lock.is_open and round_num < max_rounds
# If pick_health reaches 0, lift_pin returns False, pins can never be set
# The no_progress_count will increment but it resets to 0 after raking attempts
# Raking with broken pick also does nothing useful but still decrements pick_health
# Actually wait - raking checks lock.pick_health > 0 in the GAME but NOT in demo
# In demo, rack() is called at line 1005 regardless of pick health
# And rack() doesn't check pick health at all!
# Actually looking at rack() code - it doesn't check pick_health either
# But in the game's _picking_loop, there IS a check (line 843-854)
# In demo mode, there's no check for broken pick before calling lift_pin or rack

# Let me verify rack() doesn't check pick_health
lock = Lock(3, 4)
lock.apply_tension(0.5)
lock.pick_health = 0.0
clicks = lock.rack()
print(f'Rack with broken pick: clicks={clicks}')
# rack() will still try to set pins even with broken pick - that's a bug

# Bug 25: Check demo mode behavior with Master difficulty
# On Master, pick can break during demo, and the demo will keep trying
# forever (up to max_rounds=800), which wastes time but doesn't infinite loop
# However, rack() doesn't check pick_health, so raking still happens
# This means even with a broken pick, the demo keeps raking
# This is a minor issue but not a crash

print()
print('=== All Bugs Found ===')
for bug in bugs_found:
    print(f'  {bug}')
if not bugs_found:
    print('  None')