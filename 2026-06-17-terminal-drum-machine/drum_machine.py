#!/usr/bin/env python3
"""
Terminal Drum Machine — A step-sequencer drum machine that runs in your terminal.
Synthesizes drum sounds from scratch using numpy, displays an animated sequencer
grid, and exports patterns as WAV files. No external audio libraries needed!
"""

import numpy as np
import struct
import wave
import os
import sys
import time
import threading
import argparse
from enum import Enum


# ─── Sound Synthesis ───────────────────────────────────────────────────────

SAMPLE_RATE = 44100


def _envelope(samples, attack=0.005, decay=0.1, sustain_level=0.3, release=0.05):
    """Apply ADSR envelope to samples."""
    n = len(samples)
    t = np.linspace(0, len(samples) / SAMPLE_RATE, n, endpoint=False)
    env = np.ones(n)
    
    attack_samples = int(attack * SAMPLE_RATE)
    decay_samples = int(decay * SAMPLE_RATE)
    release_samples = int(release * SAMPLE_RATE)
    
    # Attack
    if attack_samples > 0:
        env[:attack_samples] = t[:attack_samples] / attack
    
    # Decay
    if decay_samples > 0:
        decay_end = min(attack_samples + decay_samples, n)
        decay_region = slice(attack_samples, decay_end)
        decay_len = decay_end - attack_samples
        if decay_len > 0:
            env[decay_region] = sustain_level + (1.0 - sustain_level) * (1 - t[decay_region] / decay)
    
    # Sustain
    sustain_start = attack_samples + decay_samples
    if sustain_start < n - release_samples:
        env[sustain_start:n - release_samples] = sustain_level
    
    # Release
    if release_samples > 0:
        release_start = max(n - release_samples, sustain_start)
        if release_start < n:
            release_len = n - release_start
            env[release_start:] = sustain_level * (1 - (t[release_start:] - t[release_start]) / (release_len / SAMPLE_RATE))
            env[release_start:] = np.maximum(env[release_start:], 0)
    
    return samples * env


def synth_kick(duration=0.4):
    """Synthesize a kick drum — pitch-swept sine wave with fast decay."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    # Pitch sweep from 150Hz down to 40Hz
    freq = 150 * np.exp(-t * 12) + 40
    phase = np.cumsum(freq) / SAMPLE_RATE * 2 * np.pi
    signal = np.sin(phase) * 0.9
    
    # Add a tiny click at the start for attack
    click_len = int(0.005 * SAMPLE_RATE)
    signal[:click_len] += np.random.randn(click_len) * 0.3
    
    # Envelope
    env = np.exp(-t * 8)
    signal *= env
    return signal / np.max(np.abs(signal) + 1e-10) * 0.95


def synth_snare(duration=0.3):
    """Synthesize a snare drum — tone + noise mixture."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    # Tone component
    tone = np.sin(2 * np.pi * 200 * t) + 0.5 * np.sin(2 * np.pi * 350 * t)
    
    # Noise component
    noise = np.random.randn(n)
    
    # Mix
    signal = 0.4 * tone + 0.6 * noise
    
    # Envelope
    env = np.exp(-t * 15)
    signal *= env
    
    # Bandpass-ish filter using moving average
    kernel_size = 20
    kernel = np.ones(kernel_size) / kernel_size
    signal = np.convolve(signal, kernel, mode='same')
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.9


def synth_hihat_closed(duration=0.08):
    """Synthesize a closed hi-hat — filtered noise burst."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    signal = np.random.randn(n)
    
    # High-pass-ish by subtracting low frequencies
    low = np.convolve(signal, np.ones(30) / 30, mode='same')
    signal = signal - low * 0.8
    
    # Fast decay
    env = np.exp(-t * 50)
    signal *= env
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.7


def synth_hihat_open(duration=0.3):
    """Synthesize an open hi-hat — longer noise burst."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    signal = np.random.randn(n)
    low = np.convolve(signal, np.ones(30) / 30, mode='same')
    signal = signal - low * 0.8
    
    env = np.exp(-t * 12)
    signal *= env
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.7


def synth_clap(duration=0.15):
    """Synthesize a clap — layered noise bursts."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    signal = np.random.randn(n)
    
    # Create multiple small bursts
    for offset in [0, 0.01, 0.02, 0.025]:
        idx = int(offset * SAMPLE_RATE)
        if idx < n:
            signal[idx:idx+int(0.005*SAMPLE_RATE)] *= 1.5
    
    env = np.exp(-t * 20)
    signal *= env
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.85


def synth_tom(duration=0.25):
    """Synthesize a tom — mid-frequency swept sine."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    freq = 200 * np.exp(-t * 6) + 100
    phase = np.cumsum(freq) / SAMPLE_RATE * 2 * np.pi
    signal = np.sin(phase)
    
    env = np.exp(-t * 10)
    signal *= env
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.9


def synth_rim(duration=0.05):
    """Synthesize a rimshot — short click."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    signal = np.random.randn(n) * 0.5 + np.sin(2 * np.pi * 800 * t) * 0.5
    env = np.exp(-t * 60)
    signal *= env
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.7


def synth_cowbell(duration=0.2):
    """Synthesize a cowbell — two detuned square-ish waves."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    
    # Two detuned frequencies
    sig1 = np.sign(np.sin(2 * np.pi * 560 * t))
    sig2 = np.sign(np.sin(2 * np.pi * 845 * t))
    signal = 0.5 * sig1 + 0.5 * sig2
    
    env = np.exp(-t * 8)
    signal *= env
    
    return signal / np.max(np.abs(signal) + 1e-10) * 0.65


# ─── Drum Machine ──────────────────────────────────────────────────────────

class DrumName(Enum):
    KICK = "Kick"
    SNARE = "Snare"
    HH_CLOSED = "HH-C"
    HH_OPEN = "HH-O"
    CLAP = "Clap"
    TOM = "Tom"
    RIM = "Rim"
    COWBELL = "Cow"


DRUM_SYNTHS = {
    DrumName.KICK: synth_kick,
    DrumName.SNARE: synth_snare,
    DrumName.HH_CLOSED: synth_hihat_closed,
    DrumName.HH_OPEN: synth_hihat_open,
    DrumName.CLAP: synth_clap,
    DrumName.TOM: synth_tom,
    DrumName.RIM: synth_rim,
    DrumName.COWBELL: synth_cowbell,
}

DRUM_ORDER = [
    DrumName.KICK,
    DrumName.SNARE,
    DrumName.HH_CLOSED,
    DrumName.HH_OPEN,
    DrumName.CLAP,
    DrumName.TOM,
    DrumName.RIM,
    DrumName.COWBELL,
]


class DrumMachine:
    """Terminal-based step sequencer drum machine."""

    def __init__(self, bpm=120, steps=16):
        self.bpm = bpm
        self.steps = steps
        self.drums = DRUM_ORDER
        self.pattern = {drum: [False] * steps for drum in self.drums}
        self.synths = {
            DrumName.KICK: synth_kick,
            DrumName.SNARE: synth_snare,
            DrumName.HH_CLOSED: synth_hihat_closed,
            DrumName.HH_OPEN: synth_hihat_open,
            DrumName.CLAP: synth_clap,
            DrumName.TOM: synth_tom,
            DrumName.RIM: synth_rim,
            DrumName.COWBELL: synth_cowbell,
        }
        self.current_step = 0
        self.playing = False
        self._play_thread = None
        self._stop_event = threading.Event()

    def load_preset(self, name):
        """Load a preset pattern."""
        presets = {
            "four-on-floor": {
                DrumName.KICK:    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
                DrumName.SNARE:   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
                DrumName.HH_CLOSED:[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
            },
            "hiphop": {
                DrumName.KICK:    [1,0,0,0, 0,0,1,0, 0,0,1,0, 0,0,0,0],
                DrumName.SNARE:  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,1],
                DrumName.HH_CLOSED:[1,1,0,1, 1,0,1,1, 1,1,0,1, 1,0,1,0],
            },
            "breakbeat": {
                DrumName.KICK:    [1,0,0,0, 0,0,1,0, 0,0,1,0, 0,0,0,0],
                DrumName.SNARE:  [0,0,0,0, 1,0,0,1, 0,0,0,0, 1,0,0,0],
                DrumName.HH_CLOSED:[1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
                DrumName.HH_OPEN: [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,1,0],
            },
            "reggaeton": {
                DrumName.KICK:    [1,0,0,1, 0,0,1,0, 1,0,0,1, 0,0,1,0],
                DrumName.SNARE:  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
                DrumName.HH_CLOSED:[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
                DrumName.RIM:    [0,0,0,1, 0,0,0,0, 0,0,0,1, 0,0,0,0],
            },
            "bossa-nova": {
                DrumName.KICK:    [1,0,0,0, 0,0,1,0, 0,0,1,0, 0,0,0,0],
                DrumName.RIM:    [0,0,0,1, 0,0,0,1, 0,0,0,0, 1,0,0,1],
                DrumName.HH_CLOSED:[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
                DrumName.COWBELL: [0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
            },
            "dnb": {
                DrumName.KICK:    [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
                DrumName.SNARE:  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
                DrumName.HH_CLOSED:[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
                DrumName.HH_OPEN: [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,1],
            },
        }

        name_lower = name.lower().replace("-", "").replace(" ", "")
        for key, pattern in presets.items():
            if key.replace("-", "").replace(" ", "") == name_lower:
                # Clear current pattern
                for drum in self.drums:
                    self.pattern[drum] = [False] * self.steps
                # Load preset
                for drum, steps in pattern.items():
                    self.pattern[drum] = [bool(s) for s in steps]
                return True
        return False

    def toggle(self, drum, step):
        """Toggle a step on/off."""
        self.pattern[drum][step] = not self.pattern[drum][step]

    def step_duration(self):
        """Duration of one step in seconds (16th note)."""
        return 60.0 / self.bpm / 4

    def mix_step(self, step):
        """Mix all active sounds for a given step."""
        duration = self.step_duration()
        n = int(SAMPLE_RATE * duration)
        mixed = np.zeros(n)

        for drum in self.drums:
            if self.pattern[drum][step]:
                sound = self.synths[drum](duration=min(duration, 0.5))
                # Trim or pad to match step length
                if len(sound) > n:
                    sound = sound[:n]
                elif len(sound) < n:
                    sound = np.pad(sound, (0, n - len(sound)))
                mixed += sound

        # Normalize
        peak = np.max(np.abs(mixed))
        if peak > 0.95:
            mixed = mixed / peak * 0.95
        return mixed

    def render_full_loop(self):
        """Render the full pattern as a numpy array."""
        loop = np.concatenate([self.mix_step(s) for s in range(self.steps)])
        return loop

    def render_to_wav(self, filename, loops=2):
        """Render pattern to a WAV file."""
        loop = self.render_full_loop()
        full = np.tile(loop, loops)

        # Add a tiny fade at the very end
        fade_len = min(int(0.01 * SAMPLE_RATE), len(full))
        if fade_len > 0:
            full[-fade_len:] *= np.linspace(1, 0, fade_len)

        # Convert to 16-bit PCM
        full = (full * 32767).astype(np.int16)

        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(full.tobytes())

        return filename

    def display_grid(self, highlight_step=None):
        """Return a string representation of the sequencer grid."""
        lines = []
        header = "Drum Machine  │ "
        header += "┼".join(f"{i+1:2}" for i in range(self.steps))
        header += " │"
        
        sep = "─" * (len("Drum Machine  ") + 1) + "┼" + "─" * (self.steps * 3 - 1) + "┼─"
        lines.append(sep)
        lines.append(header)
        lines.append(sep)

        for drum in self.drums:
            row = f"{drum.value:>13} │ "
            for i in range(self.steps):
                if self.pattern[drum][i]:
                    if highlight_step is not None and i == highlight_step:
                        marker = "◉ "
                    else:
                        marker = "● "
                else:
                    if highlight_step is not None and i == highlight_step:
                        marker = "◦ "
                    else:
                        marker = "· "
                row += marker
            row += "│"
            lines.append(row)

        lines.append(sep)
        bpm_str = f"BPM: {self.bpm}  Steps: {self.steps}"
        if highlight_step is not None:
            bpm_str += f"  Step: {highlight_step + 1}"
        lines.append(f"  {bpm_str}")
        return "\n".join(lines)

    def display_presets(self):
        """Show available presets."""
        presets = [
            ("four-on-floor", "Classic 4/4 dance beat"),
            ("hiphop", "Boom-bap hip-hop groove"),
            ("breakbeat", "Amen-inspired breakbeat"),
            ("reggaeton", "Dembow rhythm"),
            ("bossa-nova", "Brazilian bossa nova feel"),
            ("dnb", "Drum and bass"),
        ]
        lines = ["Available Presets:", ""]
        for name, desc in presets:
            lines.append(f"  {name:<20} — {desc}")
        return "\n".join(lines)


def try_play_audio(audio_data):
    """Try to play audio using available system tools."""
    import subprocess
    import tempfile

    # Write to temp WAV
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    
    try:
        samples = (audio_data * 32767).astype(np.int16)
        with wave.open(tmp.name, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(samples.tobytes())

        # Try different audio players
        for player in ['aplay', 'paplay', 'play', 'afplay']:
            if os.path.exists(f'/usr/bin/{player}') or os.path.exists(f'/usr/local/bin/{player}'):
                try:
                    subprocess.run([player, tmp.name], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    continue
        return False
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def interactive_mode(machine):
    """Run the drum machine in interactive mode."""
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║       🥁  TERMINAL DRUM MACHINE  🥁        ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  Commands:                                  ║")
    print("║  <drum> <step>  — Toggle a step             ║")
    print("║     e.g. 'kick 1' or 'snare 5'              ║")
    print("║  preset <name>  — Load a preset             ║")
    print("║  presets        — List presets               ║")
    print("║  bpm <n>        — Set BPM                   ║")
    print("║  clear          — Clear pattern              ║")
    print("║  random         — Random pattern             ║")
    print("║  play           — Play pattern (audio)       ║")
    print("║  export <file>  — Export to WAV              ║")
    print("║  grid           — Show grid                  ║")
    print("║  quit           — Exit                       ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    drum_map = {d.value.lower(): d for d in DRUM_ORDER}
    # Also add shorthand aliases
    drum_map["k"] = DrumName.KICK
    drum_map["s"] = DrumName.SNARE
    drum_map["hhc"] = DrumName.HH_CLOSED
    drum_map["hho"] = DrumName.HH_OPEN
    drum_map["c"] = DrumName.CLAP
    drum_map["t"] = DrumName.TOM
    drum_map["r"] = DrumName.RIM
    drum_map["cb"] = DrumName.COWBELL

    print(machine.display_grid())
    print()

    while True:
        try:
            cmd = input("🥁 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not cmd:
            continue

        parts = cmd.lower().split()

        if parts[0] == "quit" or parts[0] == "exit" or parts[0] == "q":
            print("Bye!")
            break

        elif parts[0] == "grid":
            print(machine.display_grid())
            print()

        elif parts[0] == "presets":
            print(machine.display_presets())
            print()

        elif parts[0] == "preset":
            if len(parts) < 2:
                print("Usage: preset <name>")
                continue
            name = parts[1]
            if machine.load_preset(name):
                print(f"Loaded preset: {name}")
                print(machine.display_grid())
            else:
                print(f"Unknown preset: {name}. Type 'presets' to see available presets.")
            print()

        elif parts[0] == "bpm":
            if len(parts) < 2:
                print(f"Current BPM: {machine.bpm}")
                continue
            try:
                machine.bpm = int(parts[1])
                if machine.bpm < 30 or machine.bpm > 300:
                    print("BPM must be between 30 and 300")
                    machine.bpm = max(30, min(300, machine.bpm))
                else:
                    print(f"BPM set to {machine.bpm}")
            except ValueError:
                print("Invalid BPM value")
            print()

        elif parts[0] == "clear":
            for drum in machine.drums:
                machine.pattern[drum] = [False] * machine.steps
            print("Pattern cleared.")
            print(machine.display_grid())
            print()

        elif parts[0] == "random":
            import random
            for drum in machine.drums:
                density = random.uniform(0.1, 0.5) if drum != DrumName.KICK else random.uniform(0.2, 0.4)
                machine.pattern[drum] = [random.random() < density for _ in range(machine.steps)]
            print("Random pattern generated!")
            print(machine.display_grid())
            print()

        elif parts[0] == "play":
            print("Playing pattern...")
            loop = machine.render_full_loop()
            played = try_play_audio(loop)
            if not played:
                # Save to temp and print
                outfile = "/tmp/drum_machine_output.wav"
                machine.render_to_wav(outfile)
                print(f"Audio playback not available. Saved to {outfile}")
            print()

        elif parts[0] == "export":
            if len(parts) < 2:
                print("Usage: export <filename.wav>")
                continue
            filename = parts[1]
            if not filename.endswith('.wav'):
                filename += '.wav'
            machine.render_to_wav(filename)
            print(f"Exported to {filename}")
            print()

        elif parts[0] in drum_map:
            drum = drum_map[parts[0]]
            if len(parts) < 2:
                print(f"Usage: {parts[0]} <step_number> (1-{machine.steps})")
                continue
            try:
                step = int(parts[1]) - 1
                if step < 0 or step >= machine.steps:
                    print(f"Step must be between 1 and {machine.steps}")
                    continue
                machine.toggle(drum, step)
                state = "ON" if machine.pattern[drum][step] else "OFF"
                print(f"{drum.value} step {step+1}: {state}")
                print(machine.display_grid(highlight_step=step))
            except ValueError:
                print("Invalid step number")
            print()

        else:
            # Try to parse as "drum step"
            print(f"Unknown command: {parts[0]}")
            print("Type 'quit' to exit.")


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Drum Machine — Step sequencer that synthesizes drum sounds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 drum_machine.py                        # Interactive mode
  python3 drum_machine.py --preset hiphop         # Load preset and show grid
  python3 drum_machine.py --export beat.wav       # Export preset to WAV
  python3 drum_machine.py --bpm 140 --preset dnb --export dnb.wav
  python3 drum_machine.py --random --export rand.wav
        """
    )
    parser.add_argument("--bpm", type=int, default=120, help="Beats per minute (default: 120)")
    parser.add_argument("--preset", type=str, help="Load a preset pattern")
    parser.add_argument("--export", type=str, metavar="FILE.wav", help="Export to WAV file")
    parser.add_argument("--loops", type=int, default=2, help="Number of loops for export (default: 2)")
    parser.add_argument("--random", action="store_true", help="Generate random pattern")
    parser.add_argument("--play", action="store_true", help="Play the pattern (if audio available)")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")

    args = parser.parse_args()

    machine = DrumMachine(bpm=args.bpm)

    if args.list_presets:
        print(machine.display_presets())
        return

    if args.preset:
        if not machine.load_preset(args.preset):
            print(f"Unknown preset: {args.preset}")
            print(machine.display_presets())
            sys.exit(1)

    if args.random:
        import random
        for drum in machine.drums:
            density = random.uniform(0.1, 0.4)
            machine.pattern[drum] = [random.random() < density for _ in range(machine.steps)]

    # Show the grid
    print()
    print(machine.display_grid())
    print()

    if args.export:
        machine.render_to_wav(args.export, loops=args.loops)
        print(f"✓ Exported {args.loops} loop(s) to: {args.export}")
        print(f"  BPM: {machine.bpm}, Steps: {machine.steps}")

    if args.play:
        print("Playing pattern...")
        loop = machine.render_full_loop()
        played = try_play_audio(loop)
        if not played:
            print("(Audio playback not available on this system)")

    if args.interactive or (not args.export and not args.play and not args.list_presets):
        interactive_mode(machine)


if __name__ == "__main__":
    main()