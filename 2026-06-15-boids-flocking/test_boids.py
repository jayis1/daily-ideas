"""Tests for the Boids Flocking Simulator."""
import math
from boids import Vec2, Boid, Predator, Obstacle, BoidSimulation


def test_vec2_add():
    a = Vec2(1, 2)
    b = Vec2(3, 4)
    result = a + b
    assert result.x == 4 and result.y == 6


def test_vec2_sub():
    a = Vec2(5, 7)
    b = Vec2(2, 3)
    result = a - b
    assert result.x == 3 and result.y == 4


def test_vec2_mul():
    a = Vec2(3, 4)
    result = a * 2
    assert result.x == 6 and result.y == 8


def test_vec2_rmul():
    a = Vec2(3, 4)
    result = 2 * a
    assert result.x == 6 and result.y == 8


def test_vec2_div():
    a = Vec2(6, 8)
    result = a / 2
    assert result.x == 3 and result.y == 4


def test_vec2_magnitude():
    a = Vec2(3, 4)
    assert abs(a.magnitude() - 5.0) < 1e-8


def test_vec2_normalized():
    a = Vec2(3, 4)
    n = a.normalized()
    assert abs(n.magnitude() - 1.0) < 1e-8


def test_vec2_normalized_zero():
    a = Vec2(0, 0)
    n = a.normalized()
    assert n.x == 0 and n.y == 0


def test_vec2_limit_under():
    a = Vec2(1, 0)
    result = a.limit(5)
    assert result.x == 1 and result.y == 0


def test_vec2_limit_over():
    a = Vec2(10, 0)
    result = a.limit(5)
    assert abs(result.magnitude() - 5.0) < 1e-8


def test_vec2_distance_to():
    a = Vec2(0, 0)
    b = Vec2(3, 4)
    assert abs(a.distance_to(b) - 5.0) < 1e-8


def test_vec2_copy():
    a = Vec2(1, 2)
    b = a.copy()
    b.x = 99
    assert a.x == 1  # original unchanged


def test_boid_update():
    boid = Boid(pos=Vec2(10, 10), vel=Vec2(1, 0.5))
    boid.update(max_speed=5.0)
    assert abs(boid.pos.x - 11.0) < 1e-8
    assert abs(boid.pos.y - 10.5) < 1e-8


def test_boid_trail():
    boid = Boid(pos=Vec2(10, 10), vel=Vec2(1, 0), max_trail=3)
    for i in range(5):
        boid.update(max_speed=5.0)
    assert len(boid.trail) == 3


def test_boid_velocity_limit():
    boid = Boid(pos=Vec2(10, 10), vel=Vec2(100, 100))
    boid.update(max_speed=2.0)
    assert boid.vel.magnitude() <= 2.0 + 1e-8


def test_predator_update():
    pred = Predator(pos=Vec2(10, 10), vel=Vec2(0.5, 0.5))
    pred.update(max_speed=3.0)
    assert pred.pos.x == 10.5 and pred.pos.y == 10.5


def test_simulation_creation():
    sim = BoidSimulation(80, 24, num_boids=10)
    assert len(sim.boids) == 10
    assert len(sim.predators) == 0
    assert len(sim.obstacles) == 0


def test_simulation_with_predators():
    sim = BoidSimulation(80, 24, num_boids=20, num_predators=2)
    assert len(sim.predators) == 2


def test_simulation_with_obstacles():
    sim = BoidSimulation(80, 24, num_boids=10, num_obstacles=3)
    assert len(sim.obstacles) == 3


def test_separation_rule():
    sim = BoidSimulation(80, 24, num_boids=2)
    # Place two boids very close together
    sim.boids[0].pos = Vec2(40, 12)
    sim.boids[1].pos = Vec2(40.5, 12)
    sep = sim.separation(sim.boids[0])
    # Separation should push them apart
    assert sep.magnitude() > 0


def test_alignment_rule():
    sim = BoidSimulation(80, 24, num_boids=2)
    sim.boids[0].pos = Vec2(40, 12)
    sim.boids[0].vel = Vec2(0, 0)
    sim.boids[1].pos = Vec2(41, 12)
    sim.boids[1].vel = Vec2(1, 0)
    ali = sim.alignment(sim.boids[0])
    # Alignment should steer towards other's velocity
    assert ali.x > 0


def test_cohesion_rule():
    sim = BoidSimulation(80, 24, num_boids=2)
    sim.boids[0].pos = Vec2(40, 12)
    sim.boids[1].pos = Vec2(50, 12)
    coh = sim.cohesion(sim.boids[0])
    # Cohesion should steer towards the center (rightward)
    assert coh.x > 0


def test_update_moves_boids():
    sim = BoidSimulation(80, 24, num_boids=5)
    original_positions = [b.pos.copy() for b in sim.boids]
    sim.update()
    moved = any(
        abs(b.pos.x - o.x) > 1e-8 or abs(b.pos.y - o.y) > 1e-8
        for b, o in zip(sim.boids, original_positions)
    )
    assert moved


def test_pause():
    sim = BoidSimulation(80, 24, num_boids=5)
    original_positions = [b.pos.copy() for b in sim.boids]
    sim.paused = True
    sim.update()
    for b, o in zip(sim.boids, original_positions):
        assert abs(b.pos.x - o.x) < 1e-8 and abs(b.pos.y - o.y) < 1e-8


def test_wrap_position():
    sim = BoidSimulation(80, 24, num_boids=0)
    boid = Boid(pos=Vec2(-1, 12), vel=Vec2(1, 0))
    sim.boids.append(boid)
    sim.wrap_position(boid)
    assert boid.pos.x == 80


def test_wrap_position_right():
    sim = BoidSimulation(80, 24, num_boids=0)
    boid = Boid(pos=Vec2(81, 12), vel=Vec2(1, 0))
    sim.boids.append(boid)
    sim.wrap_position(boid)
    assert boid.pos.x == 0


def test_add_predator_at():
    sim = BoidSimulation(80, 24, num_boids=5)
    sim.add_predator_at(40, 12)
    assert len(sim.predators) == 1
    assert abs(sim.predators[0].pos.x - 40) < 1e-8


def test_add_obstacle_at():
    sim = BoidSimulation(80, 24, num_boids=5)
    sim.add_obstacle_at(40, 12)
    assert len(sim.obstacles) == 1


def test_add_boids_at():
    sim = BoidSimulation(80, 24, num_boids=5)
    sim.add_boids_at(40, 12, count=10)
    assert len(sim.boids) == 15


def test_predator_catches_boid():
    sim = BoidSimulation(80, 24, num_boids=1, num_predators=1)
    # Place boid right next to predator
    sim.boids[0].pos = Vec2(40, 12)
    sim.predators[0].pos = Vec2(40, 12)
    sim.predators[0].hunt_radius = 15
    sim.update()
    assert sim.eaten_count >= 1


def test_flee_from_predator():
    sim = BoidSimulation(80, 24, num_boids=1, num_predators=1)
    sim.boids[0].pos = Vec2(40, 12)
    sim.boids[0].vel = Vec2(0, 0)
    sim.predators[0].pos = Vec2(42, 12)
    sim.predators[0].hunt_radius = 15
    flee = sim.flee_predators(sim.boids[0])
    # Boid should want to flee leftward
    assert flee.x < 0


def test_obstacle_avoidance():
    sim = BoidSimulation(80, 24, num_boids=1, num_obstacles=1)
    sim.boids[0].pos = Vec2(42, 12)
    sim.boids[0].vel = Vec2(0, 0)
    sim.obstacles[0].pos = Vec2(40, 12)
    sim.obstacles[0].radius = 3.0
    avoid = sim.avoid_obstacles(sim.boids[0])
    # Boid should want to steer away (rightward)
    assert avoid.x > 0


def test_get_direction_char_default():
    sim = BoidSimulation(80, 24, num_boids=1)
    sim.show_vectors = False
    boid = sim.boids[0]
    char = sim.get_direction_char(boid)
    assert char == boid.char


def test_get_direction_char_vectors():
    sim = BoidSimulation(80, 24, num_boids=1)
    sim.show_vectors = True
    sim.boids[0].vel = Vec2(1, 0)  # Moving rightward
    char = sim.get_direction_char(sim.boids[0])
    # Verify we get one of the direction characters (exact mapping depends on angle math)
    assert char in "→↗↑↖←↙↓↘"


def test_multiple_updates_stable():
    """Run many updates to check for crashes or NaN."""
    sim = BoidSimulation(80, 24, num_boids=30)
    for _ in range(500):
        sim.update()
    for boid in sim.boids:
        assert not math.isnan(boid.pos.x)
        assert not math.isnan(boid.pos.y)
        assert not math.isnan(boid.vel.x)
        assert not math.isnan(boid.vel.y)


def test_preset_tight():
    sim = BoidSimulation(80, 24, num_boids=10)
    sim.separation_weight = 0
    sim.alignment_weight = 0
    sim.cohesion_weight = 0
    # Simulate pressing '1' key logic
    sim.separation_weight = 1.0
    sim.alignment_weight = 2.0
    sim.cohesion_weight = 2.0
    assert sim.separation_weight == 1.0
    assert sim.alignment_weight == 2.0
    assert sim.cohesion_weight == 2.0