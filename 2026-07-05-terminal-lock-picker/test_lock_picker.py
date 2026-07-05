#!/usr/bin/env python3
"""Test script for lock_picker module (non-interactive)."""
import random
from lock_picker import Lock

def test_lock_creation():
    random.seed(42)
    lock = Lock(5, 2)
    assert lock.num_pins == 5
    assert len(lock.pins) == 5
    print(f"✓ Created lock with {lock.num_pins} pins")

def test_tension_and_binding():
    random.seed(42)
    lock = Lock(5, 2)
    lock.apply_tension(0.3)
    bound_count = sum(1 for p in lock.pins if p.is_bound)
    assert bound_count > 0, "At least one pin should bind with tension"
    print(f"✓ Applied tension — {bound_count} pins binding")

def test_lifting_and_setting():
    random.seed(42)
    lock = Lock(5, 2)
    lock.apply_tension(0.4)
    for i, pin in enumerate(lock.pins):
        if pin.is_bound:
            attempts = 0
            while not pin.is_set and attempts < 500:
                lock.lift_pin(i, 0.02)
                attempts += 1
            assert pin.is_set, f"Bound pin {i+1} should be settable"
            print(f"✓ Pin {i+1} set after {attempts} lifts")
            break

def test_full_pick():
    random.seed(99)
    lock = Lock(4, 1)
    lock.apply_tension(0.5)
    
    for attempt in range(5000):
        if lock.check_open():
            break
        lock.apply_tension(lock.tension)  # Re-update bindings
        found_bound = False
        for i, pin in enumerate(lock.pins):
            if pin.is_bound and not pin.is_set:
                lock.lift_pin(i, 0.02)
                found_bound = True
                break
        if not found_bound:
            lock.apply_tension(min(1.0, lock.tension + 0.02))
    
    assert lock.is_open, "Lock should be pickable"
    print(f"✓ Full lock pick successful")

def test_open_check():
    random.seed(999)
    lock = Lock(3, 1)
    lock.apply_tension(0.5)
    for pin in lock.pins:
        pin.is_set = True
        pin.current_height = pin.key_height
    result = lock.check_open()
    assert result == True, "Lock should open when all pins set and tension applied"
    print(f"✓ Lock opens when all pins set + tension")

def test_springs_push_down():
    random.seed(77)
    lock = Lock(4, 2)
    pin = lock.pins[0]
    pin.current_height = 0.5
    old_height = pin.current_height
    # Simulate physics decay
    pin.current_height = max(0.0, pin.current_height - pin.spring_tension * 0.5)
    assert pin.current_height < old_height, "Spring should push pin down"
    print(f"✓ Springs push pins down ({old_height:.3f} → {pin.current_height:.3f})")

if __name__ == '__main__':
    print("Testing Terminal Lock Picker...\n")
    test_lock_creation()
    test_tension_and_binding()
    test_lifting_and_setting()
    test_full_pick()
    test_open_check()
    test_springs_push_down()
    print("\n✅ All tests passed!")