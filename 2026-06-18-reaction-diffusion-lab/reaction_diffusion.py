#!/usr/bin/env python3
"""
ASCII Reaction-Diffusion Lab
=============================
Simulates the Gray-Scott reaction-diffusion model in the terminal,
producing stunning organic patterns like coral, mitosis, spots, and stripes.

The Gray-Scott model:
  dU/dt = Du * ∇²U - U*V² + F*(1 - U)
  dV/dt = Dv * ∇²V + U*V² - (F + k)*V

Where U and V are two chemical concentrations, Du and Dv are diffusion rates,
F is the feed rate, and k is the kill rate.
"""

import os
import sys
import time
import copy
import random
import argparse
import signal

# ─── Presets: (name, F, k, Du, Dv, description) ────────────────────────────

PRESETS = {
    "coral":     (0.0545, 0.062, 0.18, 0.05, "Branching coral growth"),
    "mitosis":   (0.028,  0.062, 0.18, 0.05, "Cell-like splitting patterns"),
    "spots":     (0.030,  0.062, 0.18, 0.05, "Stable spot formation"),
    "stripes":   (0.040,  0.060, 0.18, 0.05, "Worm-like stripe patterns"),
    "maze":      (0.029,  0.057, 0.18, 0.05, "Labyrinthine maze structures"),
    "waves":     (0.014,  0.045, 0.18, 0.05, "Oscillating wave patterns"),
    "ripples":   (0.018,  0.051, 0.18, 0.05, "Expanding ripple rings"),
    "fingers":   (0.050,  0.064, 0.18, 0.05, "Finger-like protrusions"),
    "solitons":  (0.030,  0.057, 0.18, 0.05, "Isolated moving spots"),
    "pulsing":   (0.025,  0.050, 0.18, 0.05, "Pulsating organic clusters"),
    "bubbles":   (0.012,  0.050, 0.18, 0.05, "Bubble-like structures"),
    "worms":     (0.039,  0.058, 0.18, 0.05, "Wriggling worm patterns"),
    "chaos":     (0.026,  0.051, 0.18, 0.05, "Chaotic turbulent mixing"),
    "flowers":   (0.055,  0.063, 0.18, 0.05, "Flower-like formations"),
    "web":       (0.044,  0.063, 0.18, 0.05, "Web-like network structures"),
}

# ─── ASCII density ramps ────────────────────────────────────────────────────

RAMP_STANDARD = " .:-=+*#%@"
RAMP_BLOCKS   = " ░▒▓█"
RAMP_DOTS     = " ·•●⬤"
RAMP_SIMPLE   = " .:oO@"
RAMP_DENSE    = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

RAMPS = {
    "standard": RAMP_STANDARD,
    "blocks": RAMP_BLOCKS,
    "dots": RAMP_DOTS,
    "simple": RAMP_SIMPLE,
    "dense": RAMP_DENSE,
}

# ─── Color schemes (ANSI 256-color codes) ──────────────────────────────────

COLOR_SCHEMES = {
    "fire":    [196, 202, 208, 214, 220, 226, 230, 255, 231],
    "ocean":   [16, 17, 18, 19, 20, 21, 26, 27, 33, 39, 45, 51],
    "forest":  [22, 28, 34, 40, 46, 47, 48, 49, 83, 119, 120, 156],
    "plasma":  [53, 55, 57, 93, 99, 129, 135, 165, 171, 201, 207, 213],
    "mono":    None,  # No color, just ASCII
    "aurora":  [16, 23, 29, 30, 36, 37, 43, 49, 48, 84, 120, 156, 183, 189, 231],
    "heat":    [16, 52, 88, 124, 160, 196, 202, 208, 214, 220, 226, 230, 231],
    "ice":     [17, 19, 21, 27, 33, 39, 45, 51, 87, 117, 153, 189, 231],
}


class ReactionDiffusion:
    """Gray-Scott reaction-diffusion simulator."""

    def __init__(self, width, height, F, k, Du, Dv):
        self.width = width
        self.height = height
        self.F = F
        self.k = k
        self.Du = Du
        self.Dv = Dv
        self.step_count = 0

        # Chemical concentrations
        self.U = [[1.0 for _ in range(width)] for _ in range(height)]
        self.V = [[0.0 for _ in range(width)] for _ in range(height)]

        self._seed_center()

    def _seed_center(self):
        """Seed V in the center of the grid."""
        cx, cy = self.width // 2, self.height // 2
        r = min(self.width, self.height) // 6
        for y in range(max(0, cy - r), min(self.height, cy + r)):
            for x in range(max(0, cx - r), min(self.width, cx + r)):
                if (x - cx) ** 2 + (y - cy) ** 2 < r ** 2:
                    self.U[y][x] = 0.50
                    self.V[y][x] = 0.25
                    # Add small noise to break symmetry
                    self.U[y][x] += random.uniform(-0.01, 0.01)
                    self.V[y][x] += random.uniform(-0.01, 0.01)

    def seed_at(self, x, y, radius=3):
        """Seed V at a specific location."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                ny = y + dy
                nx = x + dx
                if 0 <= ny < self.height and 0 <= nx < self.width:
                    if dx * dx + dy * dy <= radius * radius:
                        self.U[ny][nx] = 0.50 + random.uniform(-0.01, 0.01)
                        self.V[ny][nx] = 0.25 + random.uniform(-0.01, 0.01)

    def seed_random(self, count=5):
        """Seed V at random locations."""
        for _ in range(count):
            x = random.randint(5, self.width - 6)
            y = random.randint(5, self.height - 6)
            self.seed_at(x, y, radius=random.randint(2, 5))

    def step(self, iterations=1):
        """Advance the simulation by the given number of iterations."""
        for _ in range(iterations):
            self._single_step()
            self.step_count += 1

    def _single_step(self):
        """One step of the Gray-Scott model using 2D Laplacian."""
        w, h = self.width, self.height
        U = self.U
        V = self.V
        F = self.F
        k = self.k
        Du = self.Du
        Dv = self.Dv

        # Create new arrays
        new_U = [[0.0] * w for _ in range(h)]
        new_V = [[0.0] * w for _ in range(h)]

        for y in range(h):
            for x in range(w):
                # Laplacian with wrapping (toroidal)
                up = (y - 1) % h
                down = (y + 1) % h
                left = (x - 1) % w
                right = (x + 1) % w

                lu = (U[up][x] + U[down][x] + U[y][left] + U[y][right]) - 4.0 * U[y][x]
                lv = (V[up][x] + V[down][x] + V[y][left] + V[y][right]) - 4.0 * V[y][x]

                uvv = U[y][x] * V[y][x] * V[y][x]

                new_U[y][x] = U[y][x] + Du * lu - uvv + F * (1.0 - U[y][x])
                new_V[y][x] = V[y][x] + Dv * lv + uvv - (F + k) * V[y][x]

                # Clamp values
                new_U[y][x] = max(0.0, min(1.0, new_U[y][x]))
                new_V[y][x] = max(0.0, min(1.0, new_V[y][x]))

        self.U = new_U
        self.V = new_V

    def get_v_array(self):
        """Return the V concentration array for rendering."""
        return self.V


def render_ascii(sim, ramp_name="standard"):
    """Render the simulation state as ASCII art."""
    ramp = RAMPS.get(ramp_name, RAMP_STANDARD)
    ramp_len = len(ramp)
    V = sim.get_v_array()

    lines = []
    for y in range(sim.height):
        row = []
        for x in range(sim.width):
            v = V[y][x]
            # V is typically 0..0.5 in interesting patterns
            idx = min(int(v * ramp_len * 3), ramp_len - 1)
            row.append(ramp[idx])
        lines.append("".join(row))
    return lines


def render_color(sim, color_scheme="fire", ramp_name="standard"):
    """Render the simulation state with ANSI 256-color support."""
    colors = COLOR_SCHEMES.get(color_scheme)
    ramp = RAMPS.get(ramp_name, RAMP_STANDARD)
    V = sim.get_v_array()

    if colors is None:
        return render_ascii(sim, ramp_name)

    num_colors = len(colors)
    lines = []
    for y in range(sim.height):
        row = []
        for x in range(sim.width):
            v = V[y][x]
            ci = min(int(v * num_colors * 3), num_colors - 1)
            color = colors[ci]
            row.append(f"\033[48;5;{color}m ")
        lines.append("".join(row) + "\033[0m")
    return lines


def clear_screen():
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")


def hide_cursor():
    """Hide the terminal cursor."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Show the terminal cursor."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def move_cursor_home():
    """Move cursor to top-left without clearing."""
    sys.stdout.write("\033[H")
    sys.stdout.flush()


def get_terminal_size():
    """Get terminal dimensions, with fallback."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except (OSError, AttributeError):
        return 80, 40


def print_help():
    """Print the interactive help screen."""
    print("""
╔══════════════════════════════════════════════════════╗
║          ASCII Reaction-Diffusion Lab                ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  The Gray-Scott model simulates two chemicals        ║
║  (U and V) reacting and diffusing, producing         ║
║  beautiful organic patterns.                         ║
║                                                      ║
║  CONTROLS:                                           ║
║   SPACE    - Seed new pattern at center               ║
║   R        - Seed random patterns                     ║
║   C        - Clear and restart                        ║
║   P        - Pause/resume simulation                  ║
║   +/-      - Speed up/slow down (iterations/frame)    ║
║   1-9,0    - Switch preset pattern                    ║
║   S        - Cycle color scheme                       ║
║   D        - Cycle ASCII density ramp                 ║
║   F/B      - Increase/decrease feed rate (F)         ║
║   K/L      - Increase/decrease kill rate (k)         ║
║   H/?      - Show this help                           ║
║   Q/Esc    - Quit                                     ║
║                                                      ║
║  PRESETS:                                            ║
║   1=coral  2=mitosis  3=spots   4=stripes            ║
║   5=maze   6=waves    7=ripples 8=fingers            ║
║   9=solitons 0=pulsing                              ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
""")


def list_presets():
    """Print available presets."""
    print("\nAvailable Presets:")
    print("-" * 50)
    for i, (name, (F, k, Du, Dv, desc)) in enumerate(PRESETS.items(), 1):
        print(f"  {i:2d}. {name:12s} F={F:.4f} k={k:.4f} - {desc}")
    print()


def run_interactive(sim, iters_per_frame=4, ramp_name="standard", color_scheme="fire"):
    """Run the interactive simulation loop."""
    paused = False
    iters = iters_per_frame
    current_ramp = ramp_name
    current_color = color_scheme
    use_color = color_scheme != "mono"

    # Set up terminal
    clear_screen()
    hide_cursor()

    # Get terminal size for status bar area
    term_w, term_h = get_terminal_size()

    # Pre-render the first frame
    sim_height = sim.height
    status_height = 3

    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Move to home position and draw
    sys.stdout.write("\033[H")

    # Initial render
    if use_color:
        frame_lines = render_color(sim, current_color, current_ramp)
    else:
        frame_lines = render_ascii(sim, current_ramp)

    # Build status bar
    preset_list = list(PRESETS.keys())
    current_preset_idx = 0  # default to coral

    # Find current preset
    for i, (name, (F, k, Du, Dv, desc)) in enumerate(PRESETS.items()):
        if abs(F - sim.F) < 0.0001 and abs(k - sim.k) < 0.0001:
            current_preset_idx = i
            break

    frame_count = 0
    last_time = time.time()
    fps = 0.0

    try:
        while running:
            # Step simulation
            if not paused:
                sim.step(iters)

            # Render
            if use_color:
                frame_lines = render_color(sim, current_color, current_ramp)
            else:
                frame_lines = render_ascii(sim, current_ramp)

            # Calculate FPS
            frame_count += 1
            now = time.time()
            elapsed = now - last_time
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                frame_count = 0
                last_time = now

            # Build output
            output = []
            # Title bar
            preset_name = preset_list[current_preset_idx] if current_preset_idx < len(preset_list) else "custom"
            status_line = f" Reaction-Diffusion Lab │ Step: {sim.step_count:6d} │ FPS: {fps:4.1f} │ Iters/frame: {iters}"
            param_line = f" Preset: {preset_name:10s} │ F={sim.F:.4f} │ k={sim.k:.4f} │ Color: {current_color} │ Ramp: {current_ramp}"
            if paused:
                status_line += " │ PAUSED"

            output.append(f"\033[1;37;44m{status_line:<{sim.width}}\033[0m")
            output.append(f"\033[1;37;44m{param_line:<{sim.width}}\033[0m")

            # Simulation frame
            for line in frame_lines:
                output.append(line)

            # Bottom bar
            controls = " [SPACE]seed [R]random [C]clear [P]pause [+/-]speed [S]color [D]ramp [1-9,0]preset [Q]uit "
            output.append(f"\033[1;37;44m{controls:<{sim.width}}\033[0m")

            # Write frame
            sys.stdout.write("\033[H")
            sys.stdout.write("\n".join(output))
            sys.stdout.flush()

            # Check for key press (non-blocking)
            try:
                import select
                dr, dw, de = select.select([sys.stdin], [], [], 0.02)
                if dr:
                    key = sys.stdin.read(1)
                    if key == "q" or key == "Q" or key == "\x1b":
                        running = False
                    elif key == " ":
                        sim.seed_at(sim.width // 2, sim.height // 2, radius=max(3, sim.width // 15))
                    elif key == "r" or key == "R":
                        sim.seed_random(count=random.randint(3, 8))
                    elif key == "c" or key == "C":
                        sim.__init__(sim.width, sim.height, sim.F, sim.k, sim.Du, sim.Dv)
                    elif key == "p" or key == "P":
                        paused = not paused
                    elif key == "+" or key == "=":
                        iters = min(iters + 1, 20)
                    elif key == "-" or key == "_":
                        iters = max(iters - 1, 1)
                    elif key == "s" or key == "S":
                        schemes = list(COLOR_SCHEMES.keys())
                        idx = schemes.index(current_color) if current_color in schemes else 0
                        current_color = schemes[(idx + 1) % len(schemes)]
                        use_color = current_color != "mono"
                    elif key == "d" or key == "D":
                        ramps = list(RAMPS.keys())
                        idx = ramps.index(current_ramp) if current_ramp in ramps else 0
                        current_ramp = ramps[(idx + 1) % len(ramps)]
                    elif key == "f" or key == "F":
                        sim.F = round(sim.F + 0.001, 4)
                        current_preset_idx = len(preset_list)  # "custom"
                    elif key == "b" or key == "B":
                        sim.F = round(sim.F - 0.001, 4)
                        current_preset_idx = len(preset_list)
                    elif key == "l" or key == "L":
                        sim.k = round(sim.k + 0.001, 4)
                        current_preset_idx = len(preset_list)
                    elif key == "k" or key == "K":
                        sim.k = round(sim.k - 0.001, 4)
                        current_preset_idx = len(preset_list)
                    elif key == "h" or key == "?":
                        show_cursor()
                        clear_screen()
                        print_help()
                        input("Press Enter to continue...")
                        clear_screen()
                        hide_cursor()
                    elif key in "1234567890":
                        idx = (int(key) - 1) % 10
                        preset_keys = list(PRESETS.keys())
                        if idx < len(preset_keys):
                            name = preset_keys[idx]
                            F, k, Du, Dv, desc = PRESETS[name]
                            sim.F = F
                            sim.k = k
                            sim.Du = Du
                            sim.Dv = Dv
                            current_preset_idx = idx
            except (ImportError, ValueError):
                # select not available or no input
                time.sleep(0.02)

    finally:
        show_cursor()
        clear_screen()
        print(f"\nSimulation ended at step {sim.step_count}.")
        print(f"Final parameters: F={sim.F:.4f}, k={sim.k:.4f}")


def render_snapshot(sim, ramp_name="standard", color_scheme="mono", width=80):
    """Render a single snapshot of the simulation for non-interactive mode."""
    if color_scheme == "mono" or not sys.stdout.isatty():
        lines = render_ascii(sim, ramp_name)
    else:
        lines = render_color(sim, color_scheme, ramp_name)

    print(f"Step {sim.step_count} | F={sim.F:.4f} k={sim.k:.4f}")
    print("═" * min(sim.width, width))
    for line in lines:
        print(line)
    print("═" * min(sim.width, width))


def main():
    parser = argparse.ArgumentParser(
        description="ASCII Reaction-Diffusion Lab - Gray-Scott model simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Presets: coral, mitosis, spots, stripes, maze, waves, ripples,
         fingers, solitons, pulsing, bubbles, worms, chaos, flowers, web

Examples:
  %(prog)s                          # Interactive (default: coral)
  %(prog)s --preset mitosis         # Interactive with mitosis preset
  %(prog)s --preset spots --color ocean  # Colored spots
  %(prog)s --snapshot --steps 500   # Single snapshot to stdout
  %(prog)s --list-presets           # Show all presets
  %(prog)s --preset coral --width 60 --height 30  # Custom size
"""
    )
    parser.add_argument("--preset", "-p", default="coral",
                        choices=list(PRESETS.keys()) + ["custom"],
                        help="Pattern preset (default: coral)")
    parser.add_argument("--feed", "-F", type=float, default=None,
                        help="Feed rate F (overrides preset)")
    parser.add_argument("--kill", "-k", type=float, default=None,
                        help="Kill rate k (overrides preset)")
    parser.add_argument("--du", type=float, default=0.18,
                        help="Diffusion rate for U (default: 0.18)")
    parser.add_argument("--dv", type=float, default=0.05,
                        help="Diffusion rate for V (default: 0.05)")
    parser.add_argument("--width", "-W", type=int, default=70,
                        help="Grid width (default: 70)")
    parser.add_argument("--height", "-H", type=int, default=35,
                        help="Grid height (default: 35)")
    parser.add_argument("--steps", "-s", type=int, default=500,
                        help="Steps to simulate in snapshot mode (default: 500)")
    parser.add_argument("--iters", "-i", type=int, default=4,
                        help="Iterations per frame in interactive mode (default: 4)")
    parser.add_argument("--ramp", "-r", default="standard",
                        choices=list(RAMPS.keys()),
                        help="ASCII density ramp style (default: standard)")
    parser.add_argument("--color", "-c", default="fire",
                        choices=list(COLOR_SCHEMES.keys()),
                        help="Color scheme (default: fire)")
    parser.add_argument("--mono", "-m", action="store_true",
                        help="Monochrome mode (no ANSI colors)")
    parser.add_argument("--snapshot", "-S", action="store_true",
                        help="Non-interactive mode: render a single snapshot")
    parser.add_argument("--list-presets", action="store_true",
                        help="List all available presets and exit")
    parser.add_argument("--random-seeds", type=int, default=3,
                        help="Number of random initial seed locations (default: 3)")
    parser.add_argument("--help-interactive", action="store_true",
                        help="Show interactive controls help")

    args = parser.parse_args()

    if args.list_presets:
        list_presets()
        return

    if args.help_interactive:
        print_help()
        return

    # Get preset values
    if args.preset == "custom":
        F = args.feed if args.feed is not None else 0.055
        k = args.kill if args.kill is not None else 0.062
        Du = args.du
        Dv = args.dv
    else:
        F, k, Du, Dv, desc = PRESETS[args.preset]

    # Override with explicit values
    if args.feed is not None:
        F = args.feed
    if args.kill is not None:
        k = args.kill
    Du = args.du
    Dv = args.dv

    color_scheme = "mono" if args.mono else args.color

    # Create simulation
    sim = ReactionDiffusion(args.width, args.height, F, k, Du, Dv)

    # Add random seeds for more interesting initial conditions
    sim.seed_random(count=args.random_seeds)

    if args.snapshot:
        # Non-interactive: simulate and print
        print(f"Simulating {args.steps} steps...")
        sim.step(args.steps)
        render_snapshot(sim, args.ramp, color_scheme, args.width)
    else:
        # Interactive mode
        # Try to set terminal to raw mode for key reading
        try:
            import tty
            import termios
            old_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setraw(sys.stdin.fileno())
            try:
                run_interactive(sim, args.iters, args.ramp, color_scheme)
            finally:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
        except (ImportError, termios.error):
            # Fallback without raw mode (less responsive but works)
            run_interactive(sim, args.iters, args.ramp, color_scheme)


if __name__ == "__main__":
    main()