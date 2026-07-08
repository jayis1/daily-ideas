#!/usr/bin/env python3
"""Deeper bug hunting for lock_picker."""

import random
from lock_picker import Lock, Pin, DIFFICULTY_NAMES, MIN_PINS, MAX_PINS, get_pick_health_bar

bugs_found = []

# Bug: get_pick_health_bar for low health shows indistinguishable bar
# When health < 0.2, both filled and unfilled are '·'
bar_10pct = get_pick_health_bar(0.1, 20)
bar_0pct = get_pick_health_bar(0.0, 20)
print(f'10% health: {bar_10pct}')
print(f' 0% health: {bar_0pct}')
# They look identical except for the percentage - this is a UI bug
# The filled portion should use a different character than unfilled
if '·' in bar_10pct and '·' in bar_0pct:
    # Check if the bar sections are distinguishable
    # The bar format is: "Pick: [····················] 10%" vs "Pick: [····················] 0%"
    # Both are 20 dots - can't tell remaining health from the bar alone
    print("BUG: Low health bar uses same character for filled/unfilled - can't distinguish from zero")

# Bug: Raking wears pick on Medium (difficulty 3) but lift only wears on Hard (difficulty 4+)
# This is inconsistent - raking and lifting have different thresholds
# rack() line 285-286: if self.difficulty >= 3
# lift_pin() line 212: if self.difficulty >= 4
# So on Medium, raking damages pick but lifting doesn't
print()
print("Inconsistency: rack() wears pick at difficulty >= 3, lift_pin() wears at difficulty >= 4")
print("This means on Medium difficulty, raking damages the pick but lifting doesn't.")

# Bug: Demo mode doesn't check for broken pick
# In run_demo(), after many rounds of lifting/raking on Hard/Master,
# the pick can break. After that, lift_pin returns False forever,
# making the demo spin for max_rounds=800 doing nothing useful.
# There's no early exit for broken pick.
print()
print("BUG: Demo mode has no check for broken pick - will spin for 800 rounds doing nothing")

# Bug: rack() doesn't check for broken pick
# Even in the game, when you press R to rake, it checks pick_health > 0
# But rack() itself doesn't check - if called directly, it would still
# modify pin heights even with broken pick
lock = Lock(3, 4)
lock.apply_tension(0.5)
lock.pick_health = 0.0
# rack() will still try to set pins, ignoring broken pick
# Actually looking at the code, rack() modifies pin heights directly
# without checking pick_health. The game UI checks before calling rack(),
# but the Lock class method itself doesn't enforce it.
# This is a design inconsistency - lift_pin checks but rack doesn't
print("BUG: rack() doesn't check pick_health (unlike lift_pin which does)")

# Bug: Victory loop elapsed time keeps incrementing
# Line 876: elapsed = time.time() - self.start_time
# This is recalculated every frame, so the displayed time keeps ticking
# on the victory screen. The time shown at victory doesn't match the
# time recorded in best_times (which is captured at the moment of victory)
# Actually wait - the best time is recorded in _picking_loop at line 553
# as: elapsed = time.time() - self.start_time
# But on the victory screen, it recalculates at line 876
# This means if you sit on the victory screen for 10 seconds, the
# displayed time is 10 seconds more than the recorded best time
# Not a critical bug but confusing
print("BUG: Victory screen elapsed time keeps ticking (doesn't freeze at completion time)")

# Bug: Potential issue with _update_binding being called via apply_tension in the middle of setting pins
# When you set a pin, apply_tension is called in the full pick loop to update binding.
# But in lift_pin, after a pin is set, the binding doesn't update until next frame.
# This is actually by design in the game, but could cause a brief state where
# a newly-set pin is still marked as bound. Not really a bug.

# Bug: The victory screen checks best time using:
# is_best = best_time is not None and abs(elapsed - best_time) < 0.05
# This uses the recalculated elapsed which keeps ticking, so the check
# can be inaccurate if you stay on the victory screen for > 0.05 seconds
# However, the actual best time recording happens at the moment of victory
# in _picking_loop, so this is just a display inconsistency

# Let me check if there's a bug in the main() function's result handling
# Line 1071: result = None
# Line 1077: result = curses.wrapper(curses_main)  
# Line 1080: print(f"\nLocks picked this session: {result if result is not None else 'interrupted'}")
# If curses.wrapper raises an exception other than KeyboardInterrupt (e.g., curses.error),
# result stays None and the message says "interrupted" which is misleading
# Actually, looking more carefully:
# try:
#     result = curses.wrapper(curses_main)
# except KeyboardInterrupt:
#     print(...)
# The except only catches KeyboardInterrupt. Other exceptions would crash.
# And the print on line 1080 is OUTSIDE the try/except, so it runs after normal exit.
# On normal exit, result should be the return value of game.run(), which is self.locks_picked
# So on normal exit it works fine. On KeyboardInterrupt, the print inside except runs,
# then... wait, the print on line 1080 runs after the except block too!
# So after a KeyboardInterrupt:
# 1. "Thanks for playing..." is printed
# 2. Then "Locks picked this session: interrupted" is printed
# That's fine actually.
# But what if the game crashes with an unhandled exception inside curses.wrapper?
# The curses.wrapper function restores terminal state before re-raising.
# So any exception would crash the program. Not a handled bug.

# Bug: Check demo mode spring decay simulation
# In demo mode (line 970-972):
# for p in lock.pins:
#     if not p.is_set and p.current_height > 0:
#         p.current_height = max(0.0, p.current_height - p.spring_tension * 0.5)
# This matches the game loop spring decay (line 548-549).
# OK, no bug here.

# Bug: In the game, when you start a new lock (N key), it creates a new Lock object
# but doesn't reset pick_health or other state. Actually, new_lock() does:
# self.lock = Lock(self.num_pins, self.difficulty)
# Which creates a fresh Lock with pick_health=1.0. OK.

# Bug: Check if check_open() in the picking loop is called BEFORE spring decay
# Lines 544-567: Physics update (spring decay) then check_open
# So springs push pins down, THEN check_open runs
# This means a pin could be pushed below threshold and unset
# before check_open runs. Wait - check_open only checks is_set flag:
# all(pin.is_set for pin in self.pins) and self.tension >= 0.2
# The is_set flag is only changed by lift_pin or rack, not by spring decay
# So spring decay lowers pin height but doesn't change is_set
# However, lift_pin checks if a pin that WAS set has moved too far:
# if pin.is_set and abs(pin.current_height - pin.key_height) > tolerance * 2.5:
#     pin.is_set = False
# This check happens in lift_pin, not in spring decay
# So spring decay CAN cause a pin to drift from its set position,
# but it won't be unset until the player tries to lift that pin again
# This seems like a minor bug - spring decay can make set pins drift
# without unsetting them, so check_open can still succeed even if
# the pin has physically moved away from the shear line
print()
print("MINOR: Spring decay moves set pin heights but doesn't unset them. "
      "check_open could succeed with pins that have drifted from their set position.")

# Bug: In the game loop, after lifting a pin, there's no re-application of tension
# to update binding. The player has to manually adjust tension or the binding
# updates happen at the next physics step (next frame).
# But in the _picking_loop, the only tension update is via A/Z keys.
# In the demo, apply_tension is called every round to re-bind.
# In the game, apply_tension is only called when the player presses A or Z.
# Wait, looking more carefully:
# In the _picking_loop, there's no periodic call to apply_tension
# So after setting a pin, the binding doesn't update until the player
# changes tension. This means the game is actually harder than intended
# because you need to adjust tension to re-bind after each set.
# Actually, this might be intentional game design - you need to adjust tension
# to find the next binding pin. But it's different from how real locks work
# (binding would update automatically). Let me check the demo:
# Demo line 975: lock.apply_tension(lock.tension)
# This is called every round, which triggers _update_binding automatically
# So the demo has an advantage over the player - binding updates every round
# while in the game it only updates when you press A/Z.
# This is an inconsistency between demo and game behavior.
print("BUG: Demo re-applies tension every round (updating binding), but the game doesn't. "
      "Demo has an advantage - pins rebind automatically after being set.")

# Bug: Let me also verify that the test file covers the raking unset logic properly
# Test line 256-270: tests that raking on hard locks doesn't crash
# But it doesn't verify that pins can actually be unset

# Bug: In _picking_loop, after victory transition (line 567: return),
# the remaining code in the function (input handling) doesn't execute
# But wait - check_open() is called at line 552 and if it returns True,
# the victory state is set and the function returns at line 567
# The input handling at the bottom of _picking_loop is never reached
# in the victory frame. This is correct - the next iteration of the main loop
# will enter _victory_loop(). OK.

# Bug: The victory loop uses self.start_time which was set when the lock was created
# but doesn't freeze the elapsed time. So time keeps ticking.
# The recorded best time is captured at the exact moment of victory (line 553)
# but the displayed time on the victory screen (line 876) keeps incrementing.
print("BUG: Victory screen displays increasing time (not frozen at completion time)")

# Bug: In victory screen, there's a sparkle animation using random coordinates
# Line 922: sx = random.randint(0, max(0, w - 1))
# Line 923: sy = random.randint(0, max(0, h - 1))
# These sparkles are drawn but immediately overwritten by stdscr.refresh() on the same frame
# Actually, the sparkles are drawn BEFORE refresh(), so they should appear.
# But they only appear for one frame (50ms), making them barely visible.
# Not really a bug, more of a design choice.

# Bug: Let me check the _draw_centered method for potential off-by-one errors
# Line 443: x = max(0, (w - len(text)) // 2)
# This can place text past the right edge of the screen if the text is wider than w
# addstr will raise curses.error which is caught, so this is handled

# Bug: Check if the lock can be opened without tension
lock = Lock(3, 1)
for pin in lock.pins:
    pin.is_set = True
    pin.current_height = pin.key_height
lock.tension = 0.0
result = lock.check_open()
print(f"check_open with all set but 0% tension: {result}")  # Should be False

lock.tension = 0.19
result = lock.check_open()
print(f"check_open with all set but 19% tension: {result}")  # Should be False

# Summary
print()
print('=== Summary of Bugs Found ===')
for i, bug in enumerate(bugs_found, 1):
    print(f'  {i}. {bug}')

# Add the bugs found in the first script
print('  Additional issues found:')
print('  - Raking wears pick on Medium (difficulty>=3) but lift only on Hard (difficulty>=4)')
print('  - get_pick_health_bar low health bar uses same char for filled/unfilled')
print('  - Demo mode has no check for broken pick (infinite loop scenario)')
print('  - rack() does not check pick_health (inconsistency with lift_pin)')
print('  - Victory screen time keeps ticking instead of freezing')
print('  - Spring decay moves pin heights but doesnt unset them (inconsistency)')