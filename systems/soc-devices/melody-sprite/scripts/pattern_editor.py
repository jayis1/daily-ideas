#!/usr/bin/env python3
"""
Melody Sprite — Pattern Editor
A desktop tool for creating and editing sequencer patterns,
then uploading them to the device via serial or saving to files.

Usage:
    python pattern_editor.py                    # Interactive mode
    python pattern_editor.py --port /dev/ttyACM0 # Connect to device
    python pattern_editor.py --load pattern.bin  # Load from file
    python pattern_editor.py --save pattern.bin   # Save to file
"""

import argparse
import struct
import sys
import time

# Try to import pyserial for device communication
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Constants from firmware
NUM_STEPS = 64
DEFAULT_TEMPO = 120
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_note_name(midi_note):
    """Convert MIDI note number to note name string."""
    if midi_note == 0xFF or midi_note < 12 or midi_note > 95:
        return "---"
    octave = (midi_note // 12) - 1
    note = midi_note % 12
    return f"{NOTE_NAMES[note]}{octave}"

def note_name_to_midi(name):
    """Convert note name string to MIDI note number."""
    name = name.strip()
    for i, note in enumerate(NOTE_NAMES):
        # Handle both sharp (#) and flat (b) notation
        flat_names = {'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
                      'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'}
        search_name = flat_names.get(name[:-1], name[:-1])
        if search_name == note:
            try:
                octave = int(name[-1])
                return (octave + 1) * 12 + i
            except ValueError:
                continue
    return 0xFF  # Invalid

class SequencerPattern:
    """Represents a 64-step sequencer pattern."""

    def __init__(self):
        self.tempo = DEFAULT_TEMPO
        self.swing = 0
        self.current_bank = 0
        self.steps = []
        for _ in range(NUM_STEPS):
            self.steps.append({
                'note': 0xFF,  # Empty
                'velocity': 0,
                'gate': 100,
                'accent': False
            })

    def set_step(self, step, note=0xFF, velocity=100, gate=80, accent=False):
        """Set a step's parameters."""
        if 0 <= step < NUM_STEPS:
            self.steps[step] = {
                'note': note,
                'velocity': velocity,
                'gate': gate,
                'accent': accent
            }

    def clear_step(self, step):
        """Clear a step (make it a rest)."""
        self.set_step(step)

    def clear_all(self):
        """Clear all steps."""
        for i in range(NUM_STEPS):
            self.clear_step(i)

    def to_bytes(self):
        """Serialize pattern to binary format (matches firmware seq_pattern_to_bytes)."""
        data = bytearray()
        # Tempo (2 bytes, little-endian)
        data += struct.pack('<H', self.tempo)
        # Swing (1 byte)
        data += struct.pack('B', self.swing)
        # Current bank (1 byte)
        data += struct.pack('B', self.current_bank)
        # Steps: 4 bytes each × 64 steps
        for step in self.steps:
            data += struct.pack('B', step['note'])
            data += struct.pack('B', step['velocity'])
            data += struct.pack('B', step['gate'])
            data += struct.pack('B', 0x01 if step['accent'] else 0x00)
        return bytes(data)

    @classmethod
    def from_bytes(cls, data):
        """Deserialize pattern from binary format."""
        pat = cls()
        offset = 0
        pat.tempo = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        pat.swing = data[offset]
        offset += 1
        pat.current_bank = data[offset]
        offset += 1
        for i in range(NUM_STEPS):
            note = data[offset]
            velocity = data[offset + 1]
            gate = data[offset + 2]
            accent = data[offset + 3] != 0
            pat.steps[i] = {'note': note, 'velocity': velocity, 'gate': gate, 'accent': accent}
            offset += 4
        return pat

    def display(self, show_steps=16):
        """Print a visual representation of the pattern."""
        print(f"\n{'='*60}")
        print(f"  Tempo: {self.tempo} BPM  |  Swing: {self.swing}%  |  Bank: {self.current_bank}")
        print(f"{'='*60}")

        # Show up to show_steps at a time
        for bank in range(4):
            start = bank * 16
            end = start + 16
            print(f"\n  Bank {bank} (Steps {start+1}-{end}):")
            print(f"  {'Step':>4}", end="")
            for s in range(start, min(end, start + show_steps)):
                print(f" {s+1:>3}", end="")
            print()
            print(f"  {'Note':>4}", end="")
            for s in range(start, end):
                note = self.steps[s]['note']
                name = midi_to_note_name(note) if note != 0xFF else "---"
                print(f" {name:>3}", end="")
            print()
            print(f"  {' Vel':>4}", end="")
            for s in range(start, end):
                vel = self.steps[s]['velocity']
                print(f" {vel:>3}", end="")
            print()
            print(f"  {'Gate':>4}", end="")
            for s in range(start, end):
                gate = self.steps[s]['gate']
                print(f" {gate:>3}", end="")
            print()

            # Visual grid
            print(f"  {'    ':>4}", end="")
            for s in range(start, end):
                has_note = self.steps[s]['note'] != 0xFF
                print(f" {'█' if has_note else '·':>3}", end="")
            print()

    def create_demo_pattern(self, pattern_type="arp"):
        """Generate a demo pattern."""
        if pattern_type == "arp":
            # Arpeggiated C major pattern
            notes = [60, 64, 67, 72, 67, 64, 60, 64,
                     67, 72, 76, 72, 67, 64, 60, 0xFF]
            for i, note in enumerate(notes):
                if note != 0xFF:
                    self.set_step(i, note=note, velocity=80 + (i % 4) * 15,
                                  gate=70 + (i % 3) * 10, accent=(i % 4 == 0))
                else:
                    self.clear_step(i)
            self.tempo = 140

        elif pattern_type == "bass":
            # Simple bass line
            bass_notes = [36, 0xFF, 36, 0xFF, 43, 0xFF, 43, 0xFF,
                          41, 0xFF, 41, 0xFF, 43, 0xFF, 36, 0xFF]
            for i, note in enumerate(bass_notes):
                if note != 0xFF:
                    self.set_step(i, note=note, velocity=100, gate=60, accent=(i % 4 == 0))
            self.tempo = 120

        elif pattern_type == "melody":
            # Melodic pattern with rests
            melody = [(67, 80), (0xFF, 0), (69, 85), (0xFF, 0),
                      (71, 90), (0xFF, 0), (72, 95), (74, 100),
                      (0xFF, 0), (0xFF, 0), (72, 90), (0xFF, 0),
                      (71, 85), (69, 80), (67, 75), (0xFF, 0)]
            for i, (note, vel) in enumerate(melody):
                if note != 0xFF:
                    self.set_step(i, note=note, velocity=vel, gate=80, accent=(i % 4 == 0))
            self.tempo = 100

    def save_to_file(self, filename):
        """Save pattern to a binary file."""
        data = self.to_bytes()
        with open(filename, 'wb') as f:
            f.write(data)
        print(f"Saved pattern to {filename} ({len(data)} bytes)")

    @classmethod
    def load_from_file(cls, filename):
        """Load pattern from a binary file."""
        with open(filename, 'rb') as f:
            data = f.read()
        return cls.from_bytes(data)


class MelodySpriteSerial:
    """Serial communication with the Melody Sprite device."""

    def __init__(self, port, baudrate=115200):
        if not HAS_SERIAL:
            print("Error: pyserial not installed. Install with: pip install pyserial")
            sys.exit(1)
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=1.0)
        time.sleep(2)  # Wait for device reset
        print(f"Connected to Melody Sprite on {port}")

    def send_command(self, cmd):
        """Send a serial command and read response."""
        self.ser.write((cmd + '\n').encode())
        time.sleep(0.1)
        response = self.ser.read(4096).decode(errors='replace')
        return response.strip()

    def upload_pattern(self, pattern):
        """Upload a pattern to the device."""
        # Set tempo
        resp = self.send_command(f"SEQ:SET_TEMPO {pattern.tempo}")
        print(f"  Set tempo: {resp}")

        # Set swing
        resp = self.send_command(f"SEQ:SET_SWING {pattern.swing}")
        print(f"  Set swing: {resp}")

        # Upload each non-empty step
        for i, step in enumerate(pattern.steps):
            if step['note'] != 0xFF:
                note_name = midi_to_note_name(step['note'])
                resp = self.send_command(
                    f"SEQ:SET_STEP {i} {step['note']} {step['velocity']} {step['gate']}"
                )
                print(f"  Step {i+1}: {note_name} vel={step['velocity']} gate={step['gate']}")

        # Save pattern
        resp = self.send_command("SEQ:SAVE 0")
        print(f"  Save: {resp}")

    def start_playback(self):
        self.send_command("SEQ:PLAY")

    def stop_playback(self):
        self.send_command("SEQ:STOP")

    def close(self):
        self.ser.close()


def interactive_mode(pattern):
    """Interactive pattern editor."""
    print("\n♪ Melody Sprite — Pattern Editor ♪")
    print("Commands: show, set, clear, tempo, swing, demo, save, load, help, quit")

    while True:
        try:
            cmd = input("\n> ").strip().lower()
        except EOFError:
            break

        if not cmd:
            continue

        parts = cmd.split()

        if parts[0] == 'quit' or parts[0] == 'exit':
            break

        elif parts[0] == 'show':
            pattern.display()

        elif parts[0] == 'set':
            if len(parts) < 3:
                print("Usage: set <step> <note> [velocity] [gate]")
                continue
            step = int(parts[1])
            note = note_name_to_midi(parts[2]) if parts[2] != '---' else 0xFF
            vel = int(parts[3]) if len(parts) > 3 else 100
            gate = int(parts[4]) if len(parts) > 4 else 80
            pattern.set_step(step, note=note, velocity=vel, gate=gate)
            print(f"Step {step}: {midi_to_note_name(note)} vel={vel} gate={gate}")

        elif parts[0] == 'clear':
            if len(parts) > 1:
                pattern.clear_step(int(parts[1]))
                print(f"Cleared step {parts[1]}")
            else:
                pattern.clear_all()
                print("Cleared all steps")

        elif parts[0] == 'tempo':
            if len(parts) > 1:
                pattern.tempo = int(parts[1])
                print(f"Tempo set to {pattern.tempo} BPM")
            else:
                print(f"Tempo: {pattern.tempo} BPM")

        elif parts[0] == 'swing':
            if len(parts) > 1:
                pattern.swing = int(parts[1])
                print(f"Swing set to {pattern.swing}%")
            else:
                print(f"Swing: {pattern.swing}%")

        elif parts[0] == 'demo':
            dtype = parts[1] if len(parts) > 1 else "arp"
            pattern.create_demo_pattern(dtype)
            print(f"Loaded demo pattern: {dtype}")
            pattern.display()

        elif parts[0] == 'save':
            fname = parts[1] if len(parts) > 1 else "pattern.bin"
            pattern.save_to_file(fname)

        elif parts[0] == 'load':
            fname = parts[1] if len(parts) > 1 else "pattern.bin"
            pattern = SequencerPattern.load_from_file(fname)
            print(f"Loaded pattern from {fname}")
            pattern.display()

        elif parts[0] == 'help':
            print("""
Commands:
  show                    - Display current pattern
  set <step> <note> [vel] [gate] - Set a step (e.g., set 0 C4 100 80)
  clear [step]            - Clear a step or all steps
  tempo <bpm>             - Set tempo
  swing <percent>         - Set swing
  demo <arp|bass|melody>  - Load a demo pattern
  save <file>             - Save pattern to file
  load <file>             - Load pattern from file
  quit                    - Exit editor
            """)

        else:
            print(f"Unknown command: {parts[0]}. Type 'help' for commands.")


def main():
    parser = argparse.ArgumentParser(description='Melody Sprite Pattern Editor')
    parser.add_argument('--port', '-p', help='Serial port for device communication')
    parser.add_argument('--load', '-l', help='Load pattern from file')
    parser.add_argument('--save', '-s', help='Save pattern to file')
    parser.add_argument('--demo', '-d', choices=['arp', 'bass', 'melody'],
                       help='Load a demo pattern')
    parser.add_argument('--tempo', '-t', type=int, help='Set tempo (BPM)')
    parser.add_argument('--upload', '-u', action='store_true',
                       help='Upload pattern to device via serial')

    args = parser.parse_args()

    # Create pattern
    pattern = SequencerPattern()

    # Load from file
    if args.load:
        pattern = SequencerPattern.load_from_file(args.load)
        print(f"Loaded pattern from {args.load}")

    # Load demo
    if args.demo:
        pattern.create_demo_pattern(args.demo)
        print(f"Loaded demo pattern: {args.demo}")

    # Set tempo
    if args.tempo:
        pattern.tempo = args.tempo

    # Display pattern
    pattern.display()

    # Save to file
    if args.save:
        pattern.save_to_file(args.save)

    # Upload to device
    if args.upload and args.port:
        dev = MelodySpriteSerial(args.port)
        try:
            dev.upload_pattern(pattern)
            print("\nPattern uploaded successfully!")
        finally:
            dev.close()
    elif args.port:
        # Just connect and enter interactive mode
        dev = MelodySpriteSerial(args.port)
        try:
            interactive_mode(pattern)
        finally:
            dev.close()
    else:
        # Standalone interactive mode
        interactive_mode(pattern)


if __name__ == '__main__':
    main()