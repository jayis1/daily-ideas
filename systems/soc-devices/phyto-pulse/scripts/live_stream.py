#!/usr/bin/env python3
"""
live_stream.py — Connect to Phyto Pulse Wi-Fi WebSocket and plot live data.

Connects to ws://192.168.4.1/ws, receives JSON sample/event messages,
and displays a real-time scrolling waveform + event markers.

Usage:
    python3 live_stream.py [--ip 192.168.4.1]

Requirements:
    pip install websocket-client matplotlib numpy
"""

import argparse
import json
import threading
import time
from collections import deque
import sys

try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

import numpy as np


class PhytoPulseStream:
    def __init__(self, ip='192.168.4.1'):
        self.ip = ip
        self.ws = None
        self.connected = False
        self.samples = deque(maxlen=4000)  # 4 s at 1 kHz (display decimated)
        self.events = deque(maxlen=100)
        self.lock = threading.Lock()

    def connect(self):
        url = f"ws://{self.ip}/ws"
        print(f"Connecting to {url}...")
        try:
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open,
            )
            self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.thread.start()
            time.sleep(2)
            return self.connected
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def on_open(self, ws):
        self.connected = True
        print("WebSocket connected!")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type', data.get('t', ''))

            if msg_type in ('sample', 's'):
                t = data.get('t', data.get('ts', 0))
                v = data.get('v', 0)
                with self.lock:
                    self.samples.append((t, v))

            elif msg_type in ('event', 'e'):
                cls = data.get('c', data.get('class', '?'))
                amp = data.get('a', data.get('amp', 0))
                ts = data.get('ts', data.get('t', 0))
                with self.lock:
                    self.events.append({'ts': ts, 'class': cls, 'amp': amp})
                print(f"  EVENT: {cls} amp={amp:.2f}mV at t={ts}ms")

            elif msg_type == 'swp':
                mean = data.get('mean', 0)
                pp = data.get('pp', 0)
                print(f"  SWP: mean={mean:.3f}mV pp={pp:.3f}mV")

            elif msg_type in ('stat', 'heartbeat'):
                pass  # status update

        except json.JSONDecodeError:
            pass

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")
        self.connected = False

    def on_close(self, ws, *args):
        print("WebSocket closed")
        self.connected = False

    def get_waveform(self):
        with self.lock:
            if not self.samples:
                return [], []
            ts, vs = zip(*self.samples)
            return list(ts), list(vs)

    def get_events(self):
        with self.lock:
            return list(self.events)

    def send_command(self, cmd):
        if self.ws and self.connected:
            self.ws.send(json.dumps(cmd))
            print(f"Sent: {cmd}")


def main():
    parser = argparse.ArgumentParser(description='Phyto Pulse live stream viewer')
    parser.add_argument('--ip', default='192.168.4.1', help='Device IP')
    args = parser.parse_args()

    if not HAS_WS:
        print("websocket-client not installed. Install with: pip install websocket-client")
        sys.exit(1)

    print(f"Phyto Pulse Live Stream Viewer")
    print(f"Connecting to PhytoPulse AP at {args.ip}...")

    stream = PhytoPulseStream(args.ip)
    if not stream.connect():
        print("Failed to connect. Make sure you're connected to the PhytoPulse-XXXX Wi-Fi AP.")
        sys.exit(1)

    if not HAS_MPL:
        print("\nmatplotlib not available. Text-mode streaming:")
        print("(Install matplotlib for live plot: pip install matplotlib numpy)")
        try:
            while True:
                time.sleep(0.5)
                ts, vs = stream.get_waveform()
                if vs:
                    print(f"\rSamples: {len(vs)}, Latest: {vs[-1]:.3f} mV", end='', flush=True)
        except KeyboardInterrupt:
            print("\nDisconnected.")
        return

    # Matplotlib live plot
    fig, ax = plt.subplots(figsize=(14, 5))
    line, = ax.plot([], [], linewidth=0.5, color='blue')
    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Voltage (mV)')
    ax.set_title('Phyto Pulse — Live Stream')
    ax.grid(True, alpha=0.3)

    def update_plot(frame):
        ts, vs = stream.get_waveform()
        if ts and vs:
            line.set_data(ts, vs)
            ax.set_xlim(ts[0], ts[-1])
            vmin, vmax = min(vs), max(vs)
            margin = max(abs(vmin), abs(vmax), 1) * 0.2
            ax.set_ylim(vmin - margin, vmax + margin)

            # Mark events
            events = stream.get_events()
            ax.lines = [line]  # remove old event markers
            for ev in events[-10:]:  # last 10 events
                if ts[0] <= ev['ts'] <= ts[-1]:
                    color = {'AP': 'red', 'VP': 'orange', 'ART': 'gray'}.get(ev['class'], 'green')
                    ax.axvline(ev['ts'], color=color, alpha=0.5, linestyle='--')

        return line,

    ani = animation.FuncAnimation(fig, update_plot, interval=50, blit=False)
    plt.show()

    print("\nDisconnected.")


if __name__ == '__main__':
    main()