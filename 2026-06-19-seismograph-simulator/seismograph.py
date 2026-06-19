#!/usr/bin/env python3
"""
Terminal Seismograph Simulator
Simulates earthquake seismic waves propagating through multiple monitoring stations.
Visualizes P-waves, S-waves, and surface waves with realistic travel-time curves.
"""

__version__ = "1.1.0"

import time
import math
import random
import argparse
import sys
import os
from collections import namedtuple

# ── Physical Constants & Models ──────────────────────────────────────────────

EARTH_RADIUS_KM = 6371.0
P_WAVE_VELOCITY = 6.5    # km/s (approximate upper mantle avg)
S_WAVE_VELOCITY = 3.7    # km/s
SURFACE_WAVE_VELOCITY = 3.0  # km/s (Rayleigh wave approx)

# Seismic magnitude → amplitude scaling (simplified)
def magnitude_to_amplitude(mag):
    """Rough amplitude scaling: each unit ~10x increase.
    Clamped to a minimum to ensure even small quakes are visible."""
    amplitude = 10 ** ((mag - 3.0) * 0.8) * 0.3
    # Ensure a minimum visible amplitude for very small magnitudes
    return max(amplitude, 0.05)

# ── Data Structures ──────────────────────────────────────────────────────────

Station = namedtuple("Station", ["name", "distance_km", "angle_deg"])
Earthquake = namedtuple("Earthquake", ["magnitude", "depth_km", "lat", "lon"])

SEISMIC_STATIONS = [
    Station("Alpha Ridge",    45,   0),
    Station("Bravo Peak",     120,  30),
    Station("Charlie Flat",   250,  65),
    Station("Delta Creek",    80,   110),
    Station("Echo Valley",    380,  145),
    Station("Foxtrot Mesa",   190,  200),
    Station("Gulf Station",   550,  240),
    Station("Hotel Point",    310,  290),
    Station("India Base",     670,  330),
    Station("Juliet Dock",    150,  355),
]

# ── Waveform Generation ──────────────────────────────────────────────────────

def p_wave_arrival_time(distance_km, depth_km=10):
    """P-wave travel time in seconds (simplified linear model)."""
    hyp_distance = math.sqrt(distance_km**2 + depth_km**2)
    return hyp_distance / P_WAVE_VELOCITY

def s_wave_arrival_time(distance_km, depth_km=10):
    """S-wave travel time in seconds (simplified linear model)."""
    hyp_distance = math.sqrt(distance_km**2 + depth_km**2)
    return hyp_distance / S_WAVE_VELOCITY

def surface_wave_arrival_time(distance_km, depth_km=10):
    """Surface wave travel time — slower but only propagates along surface.
    Note: depth_km is accepted for API consistency but not used, as surface
    waves travel along the surface regardless of earthquake depth."""
    return distance_km / SURFACE_WAVE_VELOCITY

def generate_p_wave(t, arrival, amplitude):
    """Generate P-wave signal: high frequency, lower amplitude."""
    if t < arrival:
        return 0.0
    dt = t - arrival
    # Decay envelope
    envelope = amplitude * math.exp(-dt * 0.8)
    freq = 8.0  # Hz — P-waves are high frequency
    return envelope * math.sin(2 * math.pi * freq * dt) * 0.6

def generate_s_wave(t, arrival, amplitude):
    """Generate S-wave signal: medium frequency, higher amplitude."""
    if t < arrival:
        return 0.0
    dt = t - arrival
    envelope = amplitude * math.exp(-dt * 0.5)
    freq = 4.0  # Hz
    return envelope * math.sin(2 * math.pi * freq * dt) * 1.0

def generate_surface_wave(t, arrival, amplitude):
    """Generate surface wave: low frequency, highest amplitude, longest duration."""
    if t < arrival:
        return 0.0
    dt = t - arrival
    envelope = amplitude * math.exp(-dt * 0.25)
    freq = 1.5  # Hz
    return envelope * math.sin(2 * math.pi * freq * dt) * 1.4

def generate_noise(amplitude=0.02):
    """Generate background microseismic noise."""
    return random.gauss(0, amplitude)

def compute_waveform(t, station, earthquake):
    """Compute full seismogram value at time t for a station."""
    amp = magnitude_to_amplitude(earthquake.magnitude)
    p_arr = p_wave_arrival_time(station.distance_km, earthquake.depth_km)
    s_arr = s_wave_arrival_time(station.distance_km, earthquake.depth_km)
    surf_arr = surface_wave_arrival_time(station.distance_km, earthquake.depth_km)

    val = 0.0
    val += generate_p_wave(t, p_arr, amp)
    val += generate_s_wave(t, s_arr, amp)
    val += generate_surface_wave(t, surf_arr, amp)
    val += generate_noise()
    return val, p_arr, s_arr, surf_arr

# ── Terminal Rendering ───────────────────────────────────────────────────────

def get_terminal_size():
    """Get terminal dimensions."""
    try:
        cols, rows = os.get_terminal_size()
        return max(cols, 60), max(rows, 20)
    except OSError:
        return 100, 30

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_BLUE = "\033[44m"

def render_seismogram(station_name, waveform_history, max_amp, width, 
                       p_arrival=0, s_arrival=0, surf_arrival=0, 
                       current_time=0, show_arrivals=True):
    """Render a single station's seismogram as a text line."""
    display_width = width - len(station_name) - 3
    
    # Build the waveform display
    mid = display_width // 2
    line = list(" " * display_width)
    
    for i in range(min(len(waveform_history), display_width)):
        idx = len(waveform_history) - display_width + i
        if idx < 0:
            continue
        val = waveform_history[idx]
        offset = int(val / max(max_amp, 0.01) * mid)
        offset = max(-mid, min(mid, offset))
        pos = mid + offset
        if 0 <= pos < display_width:
            line[pos] = "█"
            # Fill between center and signal for area effect
            step = 1 if pos > mid else -1 if pos < mid else 0
            fill_pos = mid + step
            while fill_pos != pos + step:
                if 0 <= fill_pos < display_width and line[fill_pos] == " ":
                    line[fill_pos] = "▒"
                fill_pos += step
    
    # Build colored output
    result = f"{Colors.BOLD}{station_name:<16s}{Colors.RESET}│"
    
    # Add arrival markers
    for ch in line:
        if ch == "█":
            result += f"{Colors.GREEN}█{Colors.RESET}"
        elif ch == "▒":
            result += f"{Colors.DIM}{Colors.GREEN}▒{Colors.RESET}"
        else:
            result += ch
    
    # Show arrival time annotations
    if show_arrivals:
        arrivals = []
        if current_time >= p_arrival:
            arrivals.append(f"P:{p_arrival:.1f}s")
        if current_time >= s_arrival:
            arrivals.append(f"S:{s_arrival:.1f}s")
        if current_time >= surf_arrival:
            arrivals.append(f"Surf:{surf_arrival:.1f}s")
        if arrivals:
            result += f" {Colors.CYAN}[{' '.join(arrivals)}]{Colors.RESET}"
    
    return result

def render_seismograph_line(station_name, value, max_amp, width):
    """Render a single real-time seismograph line with a moving cursor."""
    display_width = width - 20
    mid = display_width // 2
    
    # Scale value
    if max_amp > 0:
        offset = int((value / max_amp) * mid)
    else:
        offset = 0
    offset = max(-mid, min(mid, offset))
    
    pos = mid + offset
    line = list("─" * display_width)
    line[mid] = "┼"  # center mark
    
    if 0 <= pos < display_width:
        line[pos] = "●"
    
    result = f"{Colors.BOLD}{station_name:<16s}{Colors.RESET}│"
    result += "".join(line)
    result += f"│"
    return result

def draw_map(earthquake, stations, width=60, height=15):
    """Draw a simplified map showing epicenter and stations."""
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    
    # Place epicenter at center
    cx, cy = width // 2, height // 2
    
    # Draw concentric distance rings
    for ring_km in [100, 200, 400, 600]:
        ring_chars = ring_km / 10  # scale
        for angle in range(0, 360, 2):
            rad = math.radians(angle)
            rx = int(cx + ring_chars * math.cos(rad))
            ry = int(cy + ring_chars * math.sin(rad) * 0.4)  # squish for perspective
            if 0 <= rx < width and 0 <= ry < height:
                canvas[ry][rx] = "·"
    
    # Draw stations
    for station in stations:
        sx = int(cx + (station.distance_km / 10) * math.cos(math.radians(station.angle_deg)))
        sy = int(cy + (station.distance_km / 10) * math.sin(math.radians(station.angle_deg)) * 0.4)
        sx = max(0, min(width - 1, sx))
        sy = max(0, min(height - 1, sy))
        if canvas[sy][sx] in ("·", " "):
            canvas[sy][sx] = "▲"
    
    # Epicenter
    canvas[cy][cx] = "★"
    
    # Render
    result = []
    result.append(f"  {Colors.RED}{'━' * width}{Colors.RESET}")
    for row in canvas:
        line = ""
        for ch in row:
            if ch == "★":
                line += f"{Colors.RED}{Colors.BOLD}★{Colors.RESET}"
            elif ch == "▲":
                line += f"{Colors.CYAN}▲{Colors.RESET}"
            elif ch == "·":
                line += f"{Colors.DIM}·{Colors.RESET}"
            else:
                line += ch
        result.append(f"  {Colors.RED}┃{Colors.RESET}{line}{Colors.RED}┃{Colors.RESET}")
    result.append(f"  {Colors.RED}{'━' * width}{Colors.RESET}")
    result.append(f"       {Colors.RED}★ Epicenter (M{earthquake.magnitude:.1f}, depth {earthquake.depth_km:.0f}km){Colors.RESET}    "
                  f"{Colors.CYAN}▲ Station{Colors.RESET}")
    return "\n".join(result)

def draw_travel_time_curve(stations, earthquake, width=70, height=12):
    """Draw travel-time curves showing P, S, and Surface wave arrivals."""
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    
    max_dist = max((s.distance_km for s in stations), default=100) * 1.1
    # Guard against zero-distance stations causing division by zero
    if max_dist <= 0:
        max_dist = 100.0
    max_time = surface_wave_arrival_time(max_dist, earthquake.depth_km) * 1.1
    if max_time <= 0:
        max_time = 100.0
    
    # Draw axes
    for x in range(width):
        canvas[height - 1][x] = "─"
    for y in range(height):
        canvas[y][0] = "│"
    canvas[height - 1][0] = "└"
    
    # Plot travel-time curves
    for dist in range(10, int(max_dist), 5):
        # P-wave curve
        pt = p_wave_arrival_time(dist, earthquake.depth_km)
        px = int((dist / max_dist) * (width - 5)) + 2
        py = int((1 - pt / max_time) * (height - 3)) + 1
        if 0 <= px < width and 0 <= py < height:
            if canvas[py][px] == " ":
                canvas[py][px] = "·"
        
        # S-wave curve
        st = s_wave_arrival_time(dist, earthquake.depth_km)
        sx = int((dist / max_dist) * (width - 5)) + 2
        sy_pos = int((1 - st / max_time) * (height - 3)) + 1
        if 0 <= sx < width and 0 <= sy_pos < height:
            if canvas[sy_pos][sx] == " ":
                canvas[sy_pos][sx] = "∘"
        
        # Surface wave curve
        sft = surface_wave_arrival_time(dist, earthquake.depth_km)
        sfx = int((dist / max_dist) * (width - 5)) + 2
        sfy = int((1 - sft / max_time) * (height - 3)) + 1
        if 0 <= sfx < width and 0 <= sfy < height:
            if canvas[sfy][sfx] == " ":
                canvas[sfy][sfx] = "○"
    
    # Mark station positions
    for station in stations:
        for wave_type, char, color in [
            ("p", "·", Colors.YELLOW),
            ("s", "∘", Colors.GREEN),
            ("surf", "○", Colors.CYAN),
        ]:
            if wave_type == "p":
                t = p_wave_arrival_time(station.distance_km, earthquake.depth_km)
            elif wave_type == "s":
                t = s_wave_arrival_time(station.distance_km, earthquake.depth_km)
            else:
                t = surface_wave_arrival_time(station.distance_km, earthquake.depth_km)
            
            x = int((station.distance_km / max_dist) * (width - 5)) + 2
            y = int((1 - t / max_time) * (height - 3)) + 1
            if 0 <= x < width and 0 <= y < height:
                canvas[y][x] = "◆"
    
    result = []
    result.append(f"  {Colors.BOLD}Travel-Time Curves{Colors.RESET}")
    for row in canvas:
        line = ""
        for ch in row:
            if ch == "·":
                line += f"{Colors.YELLOW}·{Colors.RESET}"
            elif ch == "∘":
                line += f"{Colors.GREEN}∘{Colors.RESET}"
            elif ch == "○":
                line += f"{Colors.CYAN}○{Colors.RESET}"
            elif ch == "◆":
                line += f"{Colors.RED}◆{Colors.RESET}"
            elif ch in ("│", "─", "└"):
                line += f"{Colors.DIM}{ch}{Colors.RESET}"
            else:
                line += ch
        result.append(f"  {line}")
    result.append(f"    {Colors.YELLOW}· P-wave{Colors.RESET}  "
                  f"{Colors.GREEN}∘ S-wave{Colors.RESET}  "
                  f"{Colors.CYAN}○ Surface{Colors.RESET}  "
                  f"{Colors.RED}◆ Stations{Colors.RESET}")
    result.append(f"    Distance →     Time ↑")
    return "\n".join(result)

def draw_richter_scale(magnitude):
    """Draw a visual Richter scale."""
    bar_width = 30
    fill = min(int((magnitude / 10.0) * bar_width), bar_width)
    
    if magnitude < 3:
        color = Colors.GREEN
        label = "Minor"
    elif magnitude < 5:
        color = Colors.YELLOW
        label = "Moderate"
    elif magnitude < 7:
        color = Colors.RED
        label = "Strong"
    elif magnitude < 8:
        color = Colors.RED
        label = "Major"
    else:
        color = Colors.MAGENTA + Colors.BOLD
        label = "Great"
    
    result = f"  {Colors.BOLD}Richter Scale{Colors.RESET}  "
    result += f"{color}{'█' * fill}{'░' * (bar_width - fill)}{Colors.RESET} "
    result += f"{color}M{magnitude:.1f} ({label}){Colors.RESET}"
    return result

def draw_phase_diagram(current_time, earthquake):
    """Draw a phase identification diagram."""
    phases = [
        ("P-wave",     "High freq, low amp",    Colors.YELLOW, 
         p_wave_arrival_time(0, earthquake.depth_km)),
        ("S-wave",     "Medium freq, med amp",   Colors.GREEN,
         s_wave_arrival_time(0, earthquake.depth_km)),
        ("Surface",    "Low freq, high amp",     Colors.CYAN,
         surface_wave_arrival_time(100, earthquake.depth_km)),
    ]
    
    result = f"  {Colors.BOLD}Wave Phase Guide{Colors.RESET}\n"
    for name, desc, color, base_time in phases:
        elapsed = current_time - base_time if current_time >= base_time else 0
        indicator = f"{color}● ACTIVE{Colors.RESET}" if elapsed > 0 else f"{Colors.DIM}○ waiting{Colors.RESET}"
        result += f"    {color}{name:<10s}{Colors.RESET} {desc:28s} {indicator}\n"
    return result

# ── Main Simulation Loop ─────────────────────────────────────────────────────

def run_simulation(earthquake, stations, duration=60.0, speed=1.0, no_map=False):
    """Run the seismograph simulation."""
    
    # Validate speed to prevent ZeroDivisionError or negative sleep
    if speed <= 0:
        print(f"  {Colors.RED}Error: speed must be positive (got {speed}). "
              f"Defaulting to 1.0x.{Colors.RESET}")
        speed = 1.0
    if duration <= 0:
        print(f"  {Colors.RED}Error: duration must be positive (got {duration}). "
              f"Defaulting to 60s.{Colors.RESET}")
        duration = 60.0
    
    cols, rows = get_terminal_size()
    
    # Pre-compute arrivals for all stations
    station_data = []
    for station in stations:
        p_arr = p_wave_arrival_time(station.distance_km, earthquake.depth_km)
        s_arr = s_wave_arrival_time(station.distance_km, earthquake.depth_km)
        surf_arr = surface_wave_arrival_time(station.distance_km, earthquake.depth_km)
        max_amp = magnitude_to_amplitude(earthquake.magnitude)
        # Closer stations get more amplitude
        distance_factor = max(0.1, 1.0 / (1 + station.distance_km / 200))
        effective_amp = max_amp * distance_factor
        station_data.append({
            "station": station,
            "p_arrival": p_arr,
            "s_arrival": s_arr,
            "surf_arrival": surf_arr,
            "max_amp": effective_amp,
            "waveform": [],
        })
    
    global_max_amp = max(d["max_amp"] for d in station_data) * 1.5
    
    dt = 0.1  # 100ms per sample
    t = 0.0
    
    # Buffer sizes for waveform display
    waveform_length = min(200, cols - 25)
    
    try:
        while t < duration:
            # Compute waveforms
            for sd in station_data:
                val = compute_waveform(t, sd["station"], earthquake)[0]
                sd["waveform"].append(val)
                if len(sd["waveform"]) > waveform_length:
                    sd["waveform"] = sd["waveform"][-waveform_length:]
            
            # Clear screen
            output = []
            output.append(f"\033[2J\033[H")  # clear + home
            
            # Header
            output.append(f"  {Colors.RED}{Colors.BOLD}{'═' * (cols - 4)}{Colors.RESET}")
            output.append(f"  {Colors.RED}{Colors.BOLD}  🌍 SEISMOGRAPH SIMULATOR  │  "
                         f"Live Seismic Monitoring{Colors.RESET}")
            output.append(f"  {Colors.RED}{Colors.BOLD}{'═' * (cols - 4)}{Colors.RESET}")
            output.append(f"  Epicenter: ({earthquake.lat:.1f}°, {earthquake.lon:.1f}°)  "
                         f"Magnitude: {Colors.RED}{Colors.BOLD}M{earthquake.magnitude:.1f}{Colors.RESET}  "
                         f"Depth: {earthquake.depth_km:.0f} km  "
                         f"Time: {Colors.YELLOW}{t:.1f}s{Colors.RESET}")
            output.append(draw_richter_scale(earthquake.magnitude))
            output.append("")
            
            # Seismograph traces
            output.append(f"  {Colors.BOLD}{'─' * (cols - 4)}{Colors.RESET}")
            output.append(f"  {Colors.BOLD}  Real-Time Seismograms{Colors.RESET}")
            output.append(f"  {Colors.BOLD}{'─' * (cols - 4)}{Colors.RESET}")
            
            for sd in station_data:
                station = sd["station"]
                waveform = sd["waveform"]
                max_amp = sd["max_amp"]
                
                if len(waveform) < 2:
                    continue
                
                # Draw waveform as a single-line trace
                trace_width = min(cols - 22, 80)
                mid = trace_width // 2
                
                # Sample the waveform to fit trace_width
                if len(waveform) >= trace_width:
                    step = len(waveform) / trace_width
                    samples = [waveform[int(i * step)] for i in range(trace_width)]
                else:
                    samples = list(waveform) + [0] * (trace_width - len(waveform))
                
                # Build the line
                line_chars = list(" " * trace_width)
                for i, val in enumerate(samples):
                    if max_amp > 0:
                        offset = int((val / (global_max_amp)) * mid * 0.8)
                    else:
                        offset = 0
                    offset = max(-mid, min(mid, offset))
                    pos = mid + offset
                    if 0 <= pos < trace_width:
                        line_chars[pos] = "█"
                        # Fill toward center
                        step_dir = 1 if offset > 0 else -1 if offset < 0 else 0
                        fill_pos = mid + step_dir
                        while fill_pos != pos:
                            if 0 <= fill_pos < trace_width and line_chars[fill_pos] == " ":
                                line_chars[fill_pos] = "░"
                            fill_pos += step_dir
                
                # Determine wave phase for coloring
                p_arr = sd["p_arrival"]
                s_arr = sd["s_arrival"]
                surf_arr = sd["surf_arrival"]
                
                if t < p_arr:
                    phase_color = Colors.DIM
                    phase = "pre-event"
                elif t < s_arr:
                    phase_color = Colors.YELLOW
                    phase = "P-wave"
                elif t < surf_arr:
                    phase_color = Colors.GREEN
                    phase = "S-wave"
                else:
                    phase_color = Colors.CYAN
                    phase = "Surface"
                
                trace_str = ""
                for ch in line_chars:
                    if ch == "█":
                        trace_str += f"{phase_color}█{Colors.RESET}"
                    elif ch == "░":
                        trace_str += f"{phase_color}{Colors.DIM}░{Colors.RESET}"
                    else:
                        trace_str += " "
                
                # Station label with distance
                dist_str = f"{station.distance_km:>3d}km"
                output.append(
                    f"  {Colors.BOLD}{station.name:<14s}{Colors.RESET}"
                    f"{Colors.DIM}{dist_str:>6s}{Colors.RESET} │"
                    f"{trace_str}│ {phase_color}{phase}{Colors.RESET}"
                )
            
            output.append(f"  {Colors.BOLD}{'─' * (cols - 4)}{Colors.RESET}")
            
            # Phase diagram
            output.append(draw_phase_diagram(t, earthquake))
            
            # Travel-time info
            output.append(f"  {Colors.BOLD}Arrival Times (from epicenter):{Colors.RESET}")
            for sd in station_data[:5]:  # Show first 5
                station = sd["station"]
                p = sd["p_arrival"]
                s = sd["s_arrival"]
                surf = sd["surf_arrival"]
                
                def time_status(arrival, current):
                    if current >= arrival:
                        return f"{Colors.GREEN}{arrival:>6.1f}s ✓{Colors.RESET}"
                    else:
                        eta = arrival - current
                        return f"{Colors.DIM}{arrival:>6.1f}s (ETA {eta:.1f}s){Colors.RESET}"
                
                output.append(
                    f"    {station.name:<14s} {station.distance_km:>3d}km  "
                    f"P:{time_status(p, t)}  "
                    f"S:{time_status(s, t)}  "
                    f"Surf:{time_status(surf, t)}"
                )
            
            if not no_map and t < 5:  # Show map at start
                output.append("")
                output.append(draw_map(earthquake, stations, 
                                       width=min(cols - 4, 60), height=12))
            
            # Footer
            output.append("")
            output.append(f"  {Colors.DIM}Press Ctrl+C to stop │ Speed: {speed:.1f}x │ "
                         f"Duration: {duration:.0f}s{Colors.RESET}")
            
            sys.stdout.write("\n".join(output))
            sys.stdout.flush()
            
            time.sleep(dt / speed)
            t += dt
    
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.YELLOW}Simulation stopped by user.{Colors.RESET}")
        return

def generate_random_earthquake():
    """Generate a random earthquake."""
    magnitude = round(random.uniform(3.0, 8.5), 1)
    depth = round(random.uniform(5, 100), 0)
    lat = round(random.uniform(-60, 60), 1)
    lon = round(random.uniform(-180, 180), 1)
    return Earthquake(magnitude, depth, lat, lon)

def list_historical_earthquakes():
    """List some notable historical earthquakes."""
    return [
        Earthquake(9.1, 30, 3.3, 95.9),    # 2004 Indian Ocean
        Earthquake(9.0, 24, 38.3, 142.4),   # 2011 Tohoku
        Earthquake(8.8, 35, -36.1, -72.9),  # 2010 Chile
        Earthquake(7.9, 19, 31.1, 103.3),   # 2008 Sichuan
        Earthquake(7.0, 13, 18.4, -72.5),   # 2010 Haiti
        Earthquake(6.9, 19, 37.8, -122.2),  # 1989 Loma Prieta
        Earthquake(6.7, 15, 34.2, -118.5),  # 1994 Northridge
        Earthquake(6.4, 10, 35.1, 25.5),    # Crete 2021
        Earthquake(5.5, 10, 51.6, -0.1),    # Hypothetical London
        Earthquake(4.5, 8, 37.8, -122.4),   # Bay Area small
    ]

def main():
    parser = argparse.ArgumentParser(
        description="🌍 Terminal Seismograph Simulator — Watch seismic waves propagate!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Random earthquake, default settings
  %(prog)s -m 7.5                 # Specify magnitude
  %(prog)s -m 9.1 -d 30           # Magnitude 9.1, depth 30km
  %(prog)s --historical            # Simulate a famous earthquake
  %(prog)s --list                  # List historical earthquakes
  %(prog)s -m 5.0 --speed 3        # Run at 3x speed
  %(prog)s -m 6.0 --duration 120   # Run for 120 seconds
  %(prog)s --interactive           # Choose from historical events
        """
    )
    parser.add_argument("-m", "--magnitude", type=float, help="Earthquake magnitude (1.0-10.0)")
    parser.add_argument("-d", "--depth", type=float, default=10, help="Depth in km (default: 10)")
    parser.add_argument("--lat", type=float, default=35.6, help="Latitude (default: 35.6)")
    parser.add_argument("--lon", type=float, default=139.7, help="Longitude (default: 139.7)")
    parser.add_argument("--duration", type=float, default=60, help="Simulation duration in seconds (default: 60)")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (default: 1.0, must be > 0)")
    parser.add_argument("--historical", action="store_true", help="Simulate a random historical earthquake")
    parser.add_argument("--interactive", action="store_true", help="Choose from historical earthquake list")
    parser.add_argument("--list", action="store_true", help="List historical earthquakes and exit")
    parser.add_argument("--no-map", action="store_true", help="Skip the station map display")
    parser.add_argument("--stations", type=int, default=10, help="Number of stations (default: 10)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    args = parser.parse_args()
    
    if args.list:
        quakes = list_historical_earthquakes()
        print(f"\n  {Colors.BOLD}Notable Historical Earthquakes{Colors.RESET}\n")
        print(f"  {'#':<4} {'Magnitude':<12} {'Depth':<10} {'Location':<30} {'Description'}")
        print(f"  {'─'*4} {'─'*12} {'─'*10} {'─'*30} {'─'*20}")
        descriptions = [
            "2004 Indian Ocean Tsunami",
            "2011 Tohoku (Fukushima)",
            "2010 Chile (Maule)",
            "2008 Sichuan, China",
            "2010 Haiti",
            "1989 Loma Prieta, CA",
            "1994 Northridge, CA",
            "2021 Crete",
            "Hypothetical London",
            "Small Bay Area",
        ]
        for i, (q, desc) in enumerate(zip(quakes, descriptions)):
            print(f"  {i+1:<4} M{q.magnitude:<10.1f} {q.depth_km:<8.0f}km "
                  f"({q.lat}, {q.lon}){'':<10s} {desc}")
        print()
        return
    
    if args.interactive:
        quakes = list_historical_earthquakes()
        descriptions = [
            "2004 Indian Ocean Tsunami",
            "2011 Tohoku (Fukushima)",
            "2010 Chile (Maule)",
            "2008 Sichuan, China",
            "2010 Haiti",
            "1989 Loma Prieta, CA",
            "1994 Northridge, CA",
            "2021 Crete",
            "Hypothetical London",
            "Small Bay Area",
        ]
        print(f"\n  {Colors.BOLD}Choose an earthquake:{Colors.RESET}\n")
        for i, (q, desc) in enumerate(zip(quakes, descriptions)):
            print(f"  {i+1:>2}. M{q.magnitude:.1f} — {desc}")
        print()
        try:
            choice = int(input("  Enter number: ")) - 1
            if 0 <= choice < len(quakes):
                earthquake = quakes[choice]
            else:
                print("  Invalid choice, using random.")
                earthquake = generate_random_earthquake()
        except (ValueError, EOFError):
            earthquake = generate_random_earthquake()
    elif args.historical:
        earthquake = random.choice(list_historical_earthquakes())
    elif args.magnitude:
        magnitude = max(1.0, min(10.0, args.magnitude))
        depth = max(0.0, args.depth)  # Depth must be non-negative
        earthquake = Earthquake(magnitude, depth, args.lat, args.lon)
    else:
        earthquake = generate_random_earthquake()
    
    # Select stations
    num_stations = max(3, min(args.stations, len(SEISMIC_STATIONS)))
    stations = SEISMIC_STATIONS[:num_stations]
    
    # Print intro
    print(f"\n  {Colors.BOLD}🌍 SEISMOGRAPH SIMULATOR{Colors.RESET}")
    print(f"  {'─' * 40}")
    print(f"  Epicenter: ({earthquake.lat:.1f}°, {earthquake.lon:.1f}°)")
    print(f"  Magnitude: M{earthquake.magnitude:.1f}")
    print(f"  Depth: {earthquake.depth_km:.0f} km")
    print(f"  Stations: {len(stations)}")
    print(f"  Speed: {args.speed:.1f}x")
    print(f"  {'─' * 40}")
    print(f"  Starting in 2 seconds...")
    time.sleep(2)
    
    run_simulation(earthquake, stations, duration=args.duration, 
                   speed=args.speed, no_map=args.no_map)

if __name__ == "__main__":
    main()