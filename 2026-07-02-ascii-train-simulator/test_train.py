#!/usr/bin/env python3
"""Test script for the ASCII Train Simulator."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import train_simulator as ts

def test_world():
    w = ts.World(seed=42)
    e = w.get_elevation(0)
    assert isinstance(e, int), f"Elevation should be int, got {type(e)}"
    
    t = w.get_terrain_type(0)
    assert t in [0, 1, 2, 3, 4, 5, 6], f"Invalid terrain type: {t}"
    
    name = w.get_station_name(200)
    assert isinstance(name, str), f"Station name should be str, got {type(name)}"
    print(f"  Station name at 200: {name}")
    
    sig = w.get_signal(70)
    assert sig is None or sig in [0, 1, 2], f"Invalid signal: {sig}"
    print("  ✓ World generation works")

def test_train():
    t = ts.Train()
    assert t.speed == 0, "Train should start stationary"
    assert t.coal > 0, "Train should start with coal"
    
    w = ts.World(seed=42)
    t.throttle = 5
    t.update(1.0, w)
    assert t.speed > 0, f"Train should accelerate with throttle=5, got speed={t.speed}"
    assert t.pressure > 0, "Pressure should build with throttle"
    print(f"  Speed after 1s throttle=5: {t.speed:.2f}")
    
    t.stoke_coal()
    assert t.coal > 50, f"Coal should increase after stoking, got {t.coal}"
    
    t.sound_whistle()
    assert t.whistle > 0, "Whistle should be active"
    print("  ✓ Train physics works")

def test_train_no_fuel():
    t = ts.Train()
    w = ts.World(seed=42)
    t.throttle = 8
    t.coal = 0
    t.water = 0
    t.update(1.0, w)
    assert t.speed < 1, "Train without fuel should not accelerate much"
    print("  ✓ Train no-fuel handling works")

def test_braking():
    t = ts.Train()
    w = ts.World(seed=42)
    t.throttle = 5
    for i in range(20):
        t.update(0.5, w)
    old_speed = t.speed
    t.brake = 1.0
    t.throttle = 0
    for i in range(20):
        t.update(0.5, w)
    assert t.speed < old_speed, f"Braking should reduce speed: was {old_speed}, now {t.speed}"
    print(f"  ✓ Braking works (speed: {old_speed:.2f} → {t.speed:.2f})")

def test_score():
    t = ts.Train()
    w = ts.World(seed=42)
    t.throttle = 3
    for i in range(100):
        t.update(0.1, w)
    assert t.score >= 0, f"Score should be non-negative, got {t.score}"
    assert t.distance > 0, "Train should have moved"
    print(f"  Distance: {t.distance:.1f}, Score: {t.score}")
    print("  ✓ Score calculation works")

if __name__ == "__main__":
    print("Testing World generation...")
    test_world()
    print("\nTesting Train physics...")
    test_train()
    print("\nTesting no-fuel scenario...")
    test_train_no_fuel()
    print("\nTesting braking...")
    test_braking()
    print("\nTesting score...")
    test_score()
    print("\n✅ All tests passed!")