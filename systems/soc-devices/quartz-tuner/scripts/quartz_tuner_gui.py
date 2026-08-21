#!/usr/bin/env python3
"""
Quartz Tuner GUI — Companion application for live visualization
and analysis of crystal characterization data.

Connects to the Quartz Tuner via BLE or USB-CDC serial.
Provides real-time admittance circle, Bode plot, turnover curve,
Allan deviation, and parameter display.

Requirements:
    pip install bleak pyqtgraph PyQt5 numpy

Usage:
    python quartz_tuner_gui.py --ble --device "QuartzTuner"
    python quartz_tuner_gui.py --serial /dev/ttyACM0
"""

import argparse
import json
import struct
import sys
import time
import threading
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("numpy required: pip install numpy")
    sys.exit(1)

try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
except ImportError:
    print("pyqtgraph + PyQt5 required: pip install pyqtgraph PyQt5")
    sys.exit(1)

# BLE UUIDs
QUARTZ_TUNER_SERVICE = "0000qt01-0000-1000-8000-00805f9b34fb"
SWEEP_DATA_CHAR = "0000qt02-0000-1000-8000-00805f9b34fb"
PARAMS_CHAR = "0000qt03-0000-1000-8000-00805f9b34fb"
CLASSIFY_CHAR = "0000qt04-0000-1000-8000-00805f9b34fb"
TURNOVER_CHAR = "0000qt05-0000-1000-8000-00805f9b34fb"
COMMAND_CHAR = "0000qt06-0000-1000-8000-00805f9b34fb"
STATUS_CHAR = "0000qt07-0000-1000-8000-00805f9b34fb"


@dataclass
class SweepPoint:
    freq_hz: float
    real: float  # conductance (S)
    imag: float  # susceptance (S)


@dataclass
class MotionalParams:
    f_s: float
    R1: float
    C1: float
    L1: float
    C0: float
    Q: float
    ESR: float
    pullability: float


@dataclass
class Classification:
    label: str
    confidence: float


@dataclass
class TurnoverPoint:
    temp_c: float
    delta_f_ppm: float


class QuartzTunerModel:
    """Data model holding measurement results."""

    def __init__(self):
        self.sweep_points: list[SweepPoint] = []
        self.params: MotionalParams | None = None
        self.classification: Classification | None = None
        self.turnover: list[TurnoverPoint] = []
        self.allan_tau: list[float] = []
        self.allan_sigma: list[float] = []

    def clear(self):
        self.sweep_points.clear()
        self.params = None
        self.classification = None
        self.turnover.clear()
        self.allan_tau.clear()
        self.allan_sigma.clear()

    def extract_parameters(self) -> MotionalParams | None:
        """Extract motional parameters from sweep data using
        the admittance circle method (Kasa fit)."""
        if len(self.sweep_points) < 10:
            return None

        G = np.array([p.real for p in self.sweep_points])
        B = np.array([p.imag for p in self.sweep_points])
        f = np.array([p.freq_hz for p in self.sweep_points])
        mag = np.sqrt(G**2 + B**2)

        # Find peak
        peak_idx = np.argmax(mag)
        f_s = f[peak_idx]

        # Kasa circle fit
        n = len(G)
        Sx = np.sum(G)
        Sy = np.sum(B)
        Sxx = np.sum(G**2)
        Sxy = np.sum(G * B)
        Syy = np.sum(B**2)
        Sxxx = np.sum(G**3)
        Sxxy = np.sum(G**2 * B)
        Sxyy = np.sum(G * B**2)
        Syyy = np.sum(B**3)

        A_mat = np.array([
            [Sxx, Sxy, Sx],
            [Sxy, Syy, Sy],
            [Sx, Sy, n]
        ])
        b_vec = np.array([
            -(Sxxx + Sxyy),
            -(Sxxy + Syyy),
            -(Sxx + Syy)
        ])

        try:
            coeff = np.linalg.solve(A_mat, b_vec)
        except np.linalg.LinAlgError:
            return None

        A, B_coeff = coeff[0], coeff[1]
        center_G = -A / 2
        center_B = -B_coeff / 2
        radius = np.sqrt(center_G**2 + center_B**2)

        R1 = 1.0 / (2.0 * radius)

        # 3 dB bandwidth
        Y_peak = mag[peak_idx]
        Y_3dB = Y_peak / np.sqrt(2)

        # Find -3dB frequencies
        below_peak = mag[:peak_idx]
        above_peak = mag[peak_idx:]

        f_minus = f_s
        f_plus = f_s

        for i in range(len(below_peak) - 1, 0, -1):
            if below_peak[i] <= Y_3dB and below_peak[i-1] > Y_3dB:
                frac = (Y_3dB - below_peak[i]) / (below_peak[i-1] - below_peak[i])
                f_minus = f[i] - frac * (f[i] - f[i-1])
                break

        for i in range(len(above_peak) - 1):
            if above_peak[i] <= Y_3dB and above_peak[i+1] > Y_3dB:
                idx = peak_idx + i + 1
                frac = (Y_3dB - above_peak[i]) / (above_peak[i+1] - above_peak[i])
                f_plus = f[idx] + frac * (f[idx+1] - f[idx]) if idx + 1 < len(f) else f[idx]
                break

        delta_f = abs(f_plus - f_minus)
        Q = f_s / delta_f if delta_f > 0 else 0

        omega_s = 2 * np.pi * f_s
        L1 = (Q * R1) / omega_s if omega_s > 0 else 0
        C1 = 1.0 / (omega_s**2 * L1) if L1 > 0 else 0

        # C0 from off-resonance susceptance
        n_off = max(1, len(f) // 10)
        B_off = np.mean(B[:n_off].tolist() + B[-n_off:].tolist())
        omega_off = 2 * np.pi * np.mean(f[:n_off].tolist() + f[-n_off:].tolist())
        C0 = B_off / omega_off if omega_off > 0 else 0

        ESR = R1  # first order approximation

        self.params = MotionalParams(
            f_s=f_s, R1=R1, C1=C1, L1=L1, C0=C0,
            Q=Q, ESR=ESR, pullability=C1 / (2 * C0) * 1e6 if C0 > 0 else 0
        )
        return self.params

    def classify(self) -> Classification:
        """Classify crystal type from motional parameters."""
        if self.params is None:
            return Classification("Unknown", 0.0)

        p = self.params
        Q = p.Q
        ratio = p.C1 / p.C0 if p.C0 > 0 else 0

        # Simple decision tree
        if p.f_s < 200000:
            label, conf = "XY-fork", 0.9
        elif Q > 50000 and ratio < 0.001:
            label, conf = "SC-cut", 0.7
        elif Q > 10000 and 0.001 < ratio < 0.005:
            label, conf = "AT-cut", 0.8
        elif Q > 2000 and ratio > 0.005:
            label, conf = "BT-cut", 0.6
        elif Q < 2000:
            label, conf = "Ceramic", 0.7
        else:
            label, conf = "Unknown", 0.3

        self.classification = Classification(label, conf)
        return self.classification


class SerialConnection:
    """USB-CDC serial connection to Quartz Tuner."""

    def __init__(self, port: str):
        self.port = port
        self.serial = None

    def connect(self):
        import serial
        self.serial = serial.Serial(self.port, 115200, timeout=1.0)

    def disconnect(self):
        if self.serial:
            self.serial.close()

    def send_command(self, cmd: str) -> str:
        if self.serial:
            self.serial.write((cmd + "\n").encode())
            time.sleep(0.1)
            return self.serial.readline().decode().strip()
        return ""

    def read_line(self) -> str | None:
        if self.serial:
            line = self.serial.readline()
            if line:
                return line.decode().strip()
        return None


class BLEConnection:
    """BLE connection to Quartz Tuner."""

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.client = None

    async def connect(self):
        try:
            from bleak import BleakClient, BleakScanner
            devices = await BleakScanner.discover()
            for d in devices:
                if self.device_name in d.name:
                    self.client = BleakClient(d.address)
                    await self.client.connect()
                    return True
        except ImportError:
            print("bleak not installed: pip install bleak")
        return False

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    async def read_params(self) -> dict:
        if self.client:
            data = await self.client.read_gatt_char(PARAMS_CHAR)
            return struct.unpack("<8f", data)
        return {}


class QuartzTunerGUI(QtWidgets.QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quartz Tuner")
        self.setGeometry(100, 100, 1200, 800)

        self.model = QuartzTunerModel()

        # Central widget with tab layout
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Parameters
        self.params_tab = self._create_params_tab()
        self.tabs.addTab(self.params_tab, "Parameters")

        # Tab 2: Admittance Circle
        self.circle_tab = self._create_circle_tab()
        self.tabs.addTab(self.circle_tab, "Admittance Circle")

        # Tab 3: Bode Plot
        self.bode_tab = self._create_bode_tab()
        self.tabs.addTab(self.bode_tab, "Bode Plot")

        # Tab 4: Turnover Curve
        self.turnover_tab = self._create_turnover_tab()
        self.tabs.addTab(self.turnover_tab, "Turnover")

        # Tab 5: Allan Deviation
        self.allan_tab = self._create_allan_tab()
        self.tabs.addTab(self.allan_tab, "Allan Dev")

        # Status bar
        self.statusBar().showMessage("Disconnected")

        # Connection
        self.connection = None

    def _create_params_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.params_labels = {}
        for name in ["f_s (Hz)", "R1 (Ω)", "C1 (F)", "L1 (H)", "C0 (F)",
                      "Q", "ESR (Ω)", "Pullability (ppm/pF)", "Class", "Confidence"]:
            row = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(f"{name}:")
            label.setFont(QtGui.QFont("Monospace", 12))
            value = QtWidgets.QLabel("—")
            value.setFont(QtGui.QFont("Monospace", 12, QtGui.QFont.Bold))
            row.addWidget(label)
            row.addWidget(value)
            layout.addLayout(row)
            self.params_labels[name] = value
        return widget

    def _create_circle_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.circle_plot = pg.PlotWidget(title="Admittance Circle")
        self.circle_plot.setLabel("bottom", "G", units="S")
        self.circle_plot.setLabel("left", "B", units="S")
        self.circle_plot.setAspectLocked(True)
        layout.addWidget(self.circle_plot)
        return widget

    def _create_bode_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.bode_plot_mag = pg.PlotWidget(title="|Y| vs Frequency")
        self.bode_plot_mag.setLabel("bottom", "Frequency", units="Hz")
        self.bode_plot_mag.setLabel("left", "|Y|", units="S")
        layout.addWidget(self.bode_plot_mag)
        self.bode_plot_phase = pg.PlotWidget(title="Phase vs Frequency")
        self.bode_plot_phase.setLabel("bottom", "Frequency", units="Hz")
        self.bode_plot_phase.setLabel("left", "Phase", units="°")
        layout.addWidget(self.bode_plot_phase)
        return widget

    def _create_turnover_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.turnover_plot = pg.PlotWidget(title="Frequency vs Temperature")
        self.turnover_plot.setLabel("bottom", "Temperature", units="°C")
        self.turnover_plot.setLabel("left", "Δf/f₀", units="ppm")
        layout.addWidget(self.turnover_plot)
        return widget

    def _create_allan_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.allan_plot = pg.PlotWidget(title="Allan Deviation")
        self.allan_plot.setLabel("bottom", "τ", units="s")
        self.allan_plot.setLabel("left", "σ_y(τ)")
        self.allan_plot.setLogMode(True, True)
        layout.addWidget(self.allan_plot)
        return widget

    def update_from_model(self):
        """Update all plots from the model data."""
        if self.model.params:
            p = self.model.params
            self.params_labels["f_s (Hz)"].setText(f"{p.f_s:,.3f}")
            self.params_labels["R1 (Ω)"].setText(f"{p.R1:.3f}")
            self.params_labels["C1 (F)"].setText(f"{p.C1:.3e}")
            self.params_labels["L1 (H)"].setText(f"{p.L1:.3e}")
            self.params_labels["C0 (F)"].setText(f"{p.C0:.3e}")
            self.params_labels["Q"].setText(f"{p.Q:,.0f}")
            self.params_labels["ESR (Ω)"].setText(f"{p.ESR:.3f}")
            self.params_labels["Pullability (ppm/pF)"].setText(f"{p.pullability:.2f}")

        if self.model.classification:
            self.params_labels["Class"].setText(self.model.classification.label)
            self.params_labels["Confidence"].setText(f"{self.model.classification.confidence:.0%}")

        if self.model.sweep_points:
            G = np.array([p.real for p in self.model.sweep_points])
            B = np.array([p.imag for p in self.model.sweep_points])
            f = np.array([p.freq_hz for p in self.model.sweep_points])
            mag = np.sqrt(G**2 + B**2)
            phase = np.degrees(np.arctan2(B, G))

            # Admittance circle
            self.circle_plot.clear()
            self.circle_plot.plot(G, B, pen=pg.mkPen('b', width=2))

            # Bode magnitude
            self.bode_plot_mag.clear()
            self.bode_plot_mag.plot(f, mag, pen=pg.mkPen('r', width=2))

            # Bode phase
            self.bode_plot_phase.clear()
            self.bode_plot_phase.plot(f, phase, pen=pg.mkPen('g', width=2))

        if self.model.turnover:
            temps = np.array([t.temp_c for t in self.model.turnover])
            deltas = np.array([t.delta_f_ppm for t in self.model.turnover])
            self.turnover_plot.clear()
            self.turnover_plot.plot(temps, deltas, pen=pg.mkPen('m', width=2))

        if self.model.allan_tau:
            self.allan_plot.clear()
            self.allan_plot.plot(
                self.model.allan_tau,
                self.model.allan_sigma,
                pen=pg.mkPen('c', width=2),
                symbol='o'
            )

    def load_from_json(self, path: str):
        """Load a measurement from a JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        self.model.clear()

        # Load sweep data
        for point in data.get('data', []):
            self.model.sweep_points.append(SweepPoint(
                freq_hz=point[0],
                real=point[1],
                imag=point[2]
            ))

        # Load parameters
        if 'f_s' in data:
            self.model.params = MotionalParams(
                f_s=data['f_s'],
                R1=data['R1'],
                C1=data['C1'],
                L1=data['L1'],
                C0=data['C0'],
                Q=data['Q'],
                ESR=data['ESR'],
                pullability=data.get('pullability', 0)
            )

        # Load classification
        if 'class' in data:
            self.model.classification = Classification(
                label=data['class'],
                confidence=data.get('confidence', 0)
            )

        self.update_from_model()

    def save_to_json(self, path: str):
        """Save current model to a JSON file."""
        data = {
            'sweep_points': [
                [p.freq_hz, p.real, p.imag]
                for p in self.model.sweep_points
            ]
        }
        if self.model.params:
            p = self.model.params
            data.update({
                'f_s': p.f_s, 'R1': p.R1, 'C1': p.C1, 'L1': p.L1,
                'C0': p.C0, 'Q': p.Q, 'ESR': p.ESR, 'pullability': p.pullability
            })
        if self.model.classification:
            data['class'] = self.model.classification.label
            data['confidence'] = self.model.classification.confidence

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def export_touchstone(self, path: str):
        """Export sweep data as a Touchstone .s1p file."""
        with open(path, 'w') as f:
            f.write("# Hz S RI R 50\n")
            f.write("! Quartz Tuner measurement\n")
            for p in self.model.sweep_points:
                # Convert admittance to S11: S11 = (1 - Y*Z0) / (1 + Y*Z0)
                Z0 = 12.5  # pi-network impedance
                Y = complex(p.real, p.imag)
                S11 = (1 - Y * Z0) / (1 + Y * Z0)
                f.write(f"{p.freq_hz:.1f} {S11.real:.6e} {S11.imag:.6e}\n")


def main():
    parser = argparse.ArgumentParser(description="Quartz Tuner GUI")
    parser.add_argument("--ble", action="store_true", help="Connect via BLE")
    parser.add_argument("--serial", type=str, help="Connect via USB-CDC serial port")
    parser.add_argument("--device", type=str, default="QuartzTuner", help="BLE device name")
    parser.add_argument("--load", type=str, help="Load from JSON file")
    parser.add_argument("--export", type=str, help="Export to format (json/s1p)")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    window = QuartzTunerGUI()

    if args.load:
        window.load_from_json(args.load)

    if args.export and args.load:
        if args.export.endswith('.s1p'):
            window.export_touchstone(args.export)
        else:
            window.save_to_json(args.export)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()