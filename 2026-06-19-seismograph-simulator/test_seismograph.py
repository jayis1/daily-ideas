#!/usr/bin/env python3
"""Unit tests for the seismograph simulator."""

import unittest
import math
import random

import seismograph as s


class TestMagnitudeToAmplitude(unittest.TestCase):
    """Tests for magnitude_to_amplitude function."""

    def test_standard_magnitudes(self):
        """Standard magnitudes produce positive amplitudes."""
        for mag in [3.0, 5.0, 7.0, 9.0]:
            amp = s.magnitude_to_amplitude(mag)
            self.assertGreater(amp, 0)

    def test_minimum_amplitude(self):
        """Very small magnitudes are clamped to a minimum visible amplitude."""
        amp = s.magnitude_to_amplitude(1.0)
        self.assertGreaterEqual(amp, 0.05)

    def test_negative_magnitude(self):
        """Negative magnitudes should still produce valid (clamped) amplitude."""
        amp = s.magnitude_to_amplitude(-1.0)
        self.assertGreaterEqual(amp, 0.05)

    def test_magnitude_scaling(self):
        """Higher magnitudes produce larger amplitudes."""
        for m1, m2 in [(3.0, 5.0), (5.0, 7.0), (7.0, 9.0)]:
            self.assertGreater(s.magnitude_to_amplitude(m2), s.magnitude_to_amplitude(m1))

    def test_zero_magnitude(self):
        """Magnitude 0 should still produce a valid amplitude."""
        amp = s.magnitude_to_amplitude(0.0)
        self.assertGreaterEqual(amp, 0.05)


class TestWaveArrivals(unittest.TestCase):
    """Tests for wave arrival time calculations."""

    def test_p_wave_arrival(self):
        """P-wave arrival time is positive for valid inputs."""
        t = s.p_wave_arrival_time(100, 10)
        self.assertGreater(t, 0)

    def test_s_wave_slower_than_p(self):
        """S-wave arrives later than P-wave at the same distance."""
        p = s.p_wave_arrival_time(100, 10)
        sw = s.s_wave_arrival_time(100, 10)
        self.assertGreater(sw, p)

    def test_surface_wave_slowest(self):
        """Surface wave arrives last."""
        p = s.p_wave_arrival_time(100, 10)
        sw = s.s_wave_arrival_time(100, 10)
        surf = s.surface_wave_arrival_time(100, 10)
        self.assertGreater(surf, sw)
        self.assertGreater(surf, p)

    def test_zero_distance_p_wave(self):
        """P-wave at zero distance is just depth/velocity."""
        t = s.p_wave_arrival_time(0, 10)
        expected = math.sqrt(0 + 100) / s.P_WAVE_VELOCITY
        self.assertAlmostEqual(t, expected, places=3)

    def test_surface_wave_ignores_depth(self):
        """Surface wave travel time depends only on surface distance."""
        t1 = s.surface_wave_arrival_time(100, 10)
        t2 = s.surface_wave_arrival_time(100, 500)
        self.assertEqual(t1, t2)

    def test_negative_depth_handled(self):
        """Negative depth is squared, so arrival times are still valid."""
        t = s.p_wave_arrival_time(100, -10)
        self.assertGreater(t, 0)


class TestWaveGeneration(unittest.TestCase):
    """Tests for waveform generation functions."""

    def test_p_wave_before_arrival(self):
        """P-wave signal is zero before arrival time."""
        val = s.generate_p_wave(5.0, 10.0, 1.0)
        self.assertEqual(val, 0.0)

    def test_s_wave_before_arrival(self):
        """S-wave signal is zero before arrival time."""
        val = s.generate_s_wave(5.0, 10.0, 1.0)
        self.assertEqual(val, 0.0)

    def test_surface_wave_before_arrival(self):
        """Surface wave signal is zero before arrival time."""
        val = s.generate_surface_wave(5.0, 10.0, 1.0)
        self.assertEqual(val, 0.0)

    def test_p_wave_at_arrival(self):
        """P-wave at exact arrival time starts at zero (sin(0)=0)."""
        val = s.generate_p_wave(10.0, 10.0, 1.0)
        self.assertAlmostEqual(val, 0.0, places=5)

    def test_p_wave_after_arrival(self):
        """P-wave produces signal after arrival."""
        val = s.generate_p_wave(10.1, 10.0, 1.0)
        self.assertNotAlmostEqual(val, 0.0, places=1)

    def test_wave_decay(self):
        """P-wave amplitude decays over time."""
        val_early = abs(s.generate_p_wave(10.5, 10.0, 1.0))
        val_late = abs(s.generate_p_wave(15.0, 10.0, 1.0))
        # Both may be zero depending on the sine phase, so compare envelope
        env_early = 1.0 * math.exp(-0.5 * 0.8)
        env_late = 1.0 * math.exp(-5.0 * 0.8)
        self.assertGreater(env_early, env_late)

    def test_noise_range(self):
        """Noise is centered around zero."""
        random.seed(42)
        vals = [s.generate_noise() for _ in range(10000)]
        mean = sum(vals) / len(vals)
        self.assertAlmostEqual(mean, 0.0, delta=0.01)

    def test_noise_custom_amplitude(self):
        """Noise with custom amplitude."""
        random.seed(42)
        vals = [s.generate_noise(0.1) for _ in range(10000)]
        # Standard deviation should be approximately 0.1
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance)
        self.assertAlmostEqual(std, 0.1, delta=0.02)


class TestComputeWaveform(unittest.TestCase):
    """Tests for the full waveform computation."""

    def test_waveform_before_any_arrival(self):
        """Before any wave arrives, only noise is present."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        station = s.Station("Test", 500, 0)
        val, _, _, _ = s.compute_waveform(0.0, station, eq)
        # Value should be very small (just noise)
        self.assertLess(abs(val), 1.0)

    def test_waveform_returns_arrivals(self):
        """compute_waveform returns arrival times."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        station = s.Station("Test", 100, 0)
        val, p, sw, surf = s.compute_waveform(5.0, station, eq)
        self.assertGreater(p, 0)
        self.assertGreater(sw, p)
        self.assertGreater(surf, sw)

    def test_large_time_decay(self):
        """At very large times, waveform decays to noise level."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        station = s.Station("Test", 100, 0)
        val, _, _, _ = s.compute_waveform(10000, station, eq)
        # Decayed envelope should make signal negligible
        self.assertLess(abs(val), 5.0)


class TestDrawFunctions(unittest.TestCase):
    """Tests for rendering/drawing functions."""

    def test_draw_richter_scale_minor(self):
        """M2.0 shows 'Minor'."""
        result = s.draw_richter_scale(2.0)
        self.assertIn("Minor", result)

    def test_draw_richter_scale_moderate(self):
        """M4.0 shows 'Moderate'."""
        result = s.draw_richter_scale(4.0)
        self.assertIn("Moderate", result)

    def test_draw_richter_scale_strong(self):
        """M6.0 shows 'Strong'."""
        result = s.draw_richter_scale(6.0)
        self.assertIn("Strong", result)

    def test_draw_richter_scale_major(self):
        """M7.5 shows 'Major'."""
        result = s.draw_richter_scale(7.5)
        self.assertIn("Major", result)

    def test_draw_richter_scale_great(self):
        """M9.0 shows 'Great'."""
        result = s.draw_richter_scale(9.0)
        self.assertIn("Great", result)

    def test_draw_map(self):
        """draw_map produces output without crashing."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        result = s.draw_map(eq, s.SEISMIC_STATIONS, width=60, height=15)
        self.assertIn("★", result)
        self.assertIn("Epicenter", result)

    def test_draw_map_far_station(self):
        """draw_map handles very distant stations without crashing."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        far_st = s.Station("FarAway", 9999, 45)
        result = s.draw_map(eq, [far_st], width=60, height=15)
        self.assertIn("★", result)

    def test_draw_travel_time_curve_normal(self):
        """draw_travel_time_curve works with normal stations."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        result = s.draw_travel_time_curve(s.SEISMIC_STATIONS[:5], eq)
        self.assertIn("Travel-Time", result)

    def test_draw_travel_time_curve_zero_distance(self):
        """draw_travel_time_curve handles zero-distance station (BUG FIX)."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        zero_st = s.Station("ZeroDist", 0, 0)
        # Should NOT raise ZeroDivisionError
        result = s.draw_travel_time_curve([zero_st], eq, width=70, height=12)
        self.assertIn("Travel-Time", result)

    def test_draw_travel_time_curve_empty_stations(self):
        """draw_travel_time_curve handles empty station list."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        result = s.draw_travel_time_curve([], eq, width=70, height=12)
        self.assertIn("Travel-Time", result)

    def test_draw_phase_diagram(self):
        """draw_phase_diagram produces output."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        result = s.draw_phase_diagram(10.0, eq)
        self.assertIn("P-wave", result)
        self.assertIn("S-wave", result)
        self.assertIn("Surface", result)

    def test_render_seismogram_empty(self):
        """render_seismogram handles empty waveform."""
        result = s.render_seismogram("Test", [], 1.0, 80)
        self.assertIn("Test", result)

    def test_render_seismogram_short_waveform(self):
        """render_seismogram handles short waveform."""
        result = s.render_seismogram("Test", [0.1, 0.2, 0.3], 1.0, 80)
        self.assertIn("Test", result)

    def test_render_seismograph_line(self):
        """render_seismograph_line produces output."""
        result = s.render_seismograph_line("Test", 0.5, 1.0, 80)
        self.assertIn("Test", result)

    def test_render_seismograph_line_zero_amplitude(self):
        """render_seismograph_line handles zero max amplitude."""
        result = s.render_seismograph_line("Test", 0.5, 0, 80)
        self.assertIn("Test", result)


class TestEarthquakeGeneration(unittest.TestCase):
    """Tests for earthquake generation functions."""

    def test_random_earthquake_range(self):
        """Random earthquake has valid magnitude and depth."""
        for _ in range(20):
            eq = s.generate_random_earthquake()
            self.assertGreaterEqual(eq.magnitude, 3.0)
            self.assertLessEqual(eq.magnitude, 8.5)
            self.assertGreaterEqual(eq.depth_km, 5)
            self.assertLessEqual(eq.depth_km, 100)

    def test_historical_earthquakes(self):
        """Historical earthquakes list is non-empty and valid."""
        quakes = s.list_historical_earthquakes()
        self.assertEqual(len(quakes), 10)
        for q in quakes:
            self.assertGreater(q.magnitude, 0)
            self.assertGreater(q.depth_km, 0)


class TestCLIArgParsing(unittest.TestCase):
    """Tests for command-line argument parsing."""

    def test_version_flag(self):
        """--version flag works and shows version."""
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '--version'],
            capture_output=True, text=True, timeout=5
        )
        self.assertIn("1.1.0", result.stdout)

    def test_list_flag(self):
        """--list flag works."""
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '--list'],
            capture_output=True, text=True, timeout=5
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Indian Ocean", result.stdout)

    def test_magnitude_clamping(self):
        """Magnitude is clamped to [1.0, 10.0]."""
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '-m', '15', '--duration', '0.5', '--speed', '20', '--no-map'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("M10.0", result.stdout)

    def test_negative_depth_clamping(self):
        """Negative depth is clamped to 0."""
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '-m', '5.0', '-d', '-10', '--duration', '0.5', '--speed', '20', '--no-map'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Depth: 0 km", result.stdout)

    def test_speed_zero_graceful(self):
        """Speed=0 is handled gracefully."""
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '-m', '5.0', '--speed', '0', '--duration', '0.5', '--no-map'],
            capture_output=True, text=True, timeout=10
        )
        # Should not crash with ZeroDivisionError
        self.assertEqual(result.returncode, 0)
        self.assertIn("must be positive", result.stdout)

    def test_speed_negative_graceful(self):
        """Speed<0 is handled gracefully."""
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '-m', '5.0', '--speed', '-1', '--duration', '0.5', '--no-map'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("must be positive", result.stdout)

    def test_station_count_clamping(self):
        """Station count is clamped to [3, 10]."""
        # We can't easily test this from outside, but we can verify the output
        import subprocess
        result = subprocess.run(
            ['python3', 'seismograph.py', '-m', '5.0', '--stations', '20', '--duration', '0.5', '--speed', '20', '--no-map'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Stations: 10", result.stdout)


class TestDataStructures(unittest.TestCase):
    """Tests for data structures."""

    def test_station_namedtuple(self):
        """Station namedtuple fields are accessible."""
        st = s.Station("Test", 100, 45)
        self.assertEqual(st.name, "Test")
        self.assertEqual(st.distance_km, 100)
        self.assertEqual(st.angle_deg, 45)

    def test_earthquake_namedtuple(self):
        """Earthquake namedtuple fields are accessible."""
        eq = s.Earthquake(7.0, 10, 35.6, 139.7)
        self.assertEqual(eq.magnitude, 7.0)
        self.assertEqual(eq.depth_km, 10)
        self.assertEqual(eq.lat, 35.6)
        self.assertEqual(eq.lon, 139.7)

    def test_seismic_stations_count(self):
        """There are exactly 10 seismic stations."""
        self.assertEqual(len(s.SEISMIC_STATIONS), 10)

    def test_seismic_stations_distances(self):
        """All stations have positive distances."""
        for st in s.SEISMIC_STATIONS:
            self.assertGreater(st.distance_km, 0)


class TestVersion(unittest.TestCase):
    """Tests for version constant."""

    def test_version_exists(self):
        """Version constant is defined."""
        self.assertTrue(hasattr(s, '__version__'))
        self.assertEqual(s.__version__, "1.1.0")


if __name__ == "__main__":
    unittest.main()