#!/usr/bin/env python3
"""
Levia Forge — BLE Companion App (PyQt6)

Connects to the Levia Forge ESP32-C3 BLE bridge and provides:
- 3D position sliders (X, Y, Z) for trap control
- Pattern selection dropdown
- Live particle height readout
- Battery and temperature monitoring
- Session logging to CSV

Usage:
    python3 levia_app.py

Requires:
    pip install PyQt6 bleak
"""

import sys
import csv
import time
import asyncio
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QSlider, QPushButton, QComboBox, QTextEdit,
        QGroupBox, QFormLayout, QProgressBar, QFileDialog
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
except ImportError:
    print("PyQt6 not installed. Install with: pip install PyQt6")
    sys.exit(1)

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("bleak not installed. Install with: pip install bleak")
    sys.exit(1)


# BLE UUIDs (matching ESP32-C3 firmware)
SERVICE_UUID        = "00001800-0000-1000-8000-00805f9b34fb"
CHAR_STATE_UUID     = "00002a01-0000-1000-8000-00805f9b34fb"
CHAR_CMD_UUID       = "00002a02-0000-1000-8000-00805f9b34fb"
CHAR_PATTERN_UUID   = "00002a03-0000-1000-8000-00805f9b34fb"

DEVICE_NAME = "Levia Forge"

PATTERNS = [
    "Point (single trap)",
    "Twin (two traps)",
    "Vortex (spinning)",
    "Bottle (hollow)",
    "Bending (tilted)",
    "Conveyor (transport)",
]


class BLEThread(QThread):
    """Background thread for BLE communication."""
    state_received = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.client = None
        self.running = True
        self.cmd_queue = []

    async def scan_and_connect(self):
        """Scan for Levia Forge device and connect."""
        self.error.emit("Scanning for Levia Forge...")
        devices = await BleakScanner.discover(timeout=10.0)
        target = None
        for d in devices:
            if d.name and DEVICE_NAME in d.name:
                target = d
                break

        if not target:
            self.error.emit("Levia Forge not found!")
            return False

        self.error.emit(f"Connecting to {target.name}...")
        self.client = BleakClient(target.address)
        await self.client.connect()
        self.connected.emit()

        # Subscribe to state characteristic notifications
        await self.client.start_notify(CHAR_STATE_UUID,
                                        self._notification_handler)
        return True

    def _notification_handler(self, sender, data):
        """Handle incoming BLE notifications (state updates)."""
        try:
            text = data.decode('utf-8')
            self.state_received.emit(text)
        except Exception:
            pass

    async def send_command(self, cmd):
        """Send a command string to the device."""
        if self.client and self.client.is_connected:
            await self.client.write_gatt_char(CHAR_CMD_UUID,
                                               cmd.encode('utf-8'))

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.disconnected.emit()

    def run(self):
        """Main thread loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.scan_and_connect())

            while self.running:
                # Process command queue
                while self.cmd_queue:
                    cmd = self.cmd_queue.pop(0)
                    loop.run_until_complete(self.send_command(cmd))

                # Poll state (read characteristic)
                if self.client and self.client.is_connected:
                    try:
                        data = loop.run_until_complete(
                            self.client.read_gatt_char(CHAR_STATE_UUID)
                        )
                        if data:
                            text = data.decode('utf-8')
                            self.state_received.emit(text)
                    except Exception:
                        pass

                loop.run_until_complete(asyncio.sleep(0.1))

        except Exception as e:
            self.error.emit(f"BLE error: {e}")
        finally:
            loop.run_until_complete(self.disconnect())
            loop.close()

    def stop(self):
        self.running = False

    def queue_command(self, cmd):
        self.cmd_queue.append(cmd)


class LeviaForgeApp(QMainWindow):
    """Main companion app window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Levia Forge — Control App")
        self.setMinimumSize(500, 600)

        self.ble_thread = BLEThread()
        self.ble_thread.state_received.connect(self.on_state)
        self.ble_thread.connected.connect(self.on_connected)
        self.ble_thread.disconnected.connect(self.on_disconnected)
        self.ble_thread.error.connect(self.on_error)

        self.log_data = []
        self.connected = False

        self._build_ui()

        # Auto-connect on startup
        QTimer.singleShot(500, self.ble_thread.start)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Connection status
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)
        self.conn_label = QLabel("Disconnected")
        self.conn_label.setStyleSheet("color: red; font-weight: bold;")
        conn_layout.addWidget(self.conn_label)
        self.connect_btn = QPushButton("Reconnect")
        self.connect_btn.clicked.connect(self.reconnect)
        conn_layout.addWidget(self.connect_btn)
        layout.addWidget(conn_group)

        # Position control
        pos_group = QGroupBox("Trap Position (mm)")
        pos_layout = QFormLayout(pos_group)

        self.x_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_slider.setRange(-150, 150)  # ±15.0 mm × 10
        self.x_slider.setValue(0)
        self.x_slider.valueChanged.connect(self.on_position_changed)
        self.x_label = QLabel("0.0")
        pos_layout.addRow("X:", self._slider_with_label(self.x_slider,
                                                         self.x_label))

        self.y_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_slider.setRange(-150, 150)
        self.y_slider.setValue(0)
        self.y_slider.valueChanged.connect(self.on_position_changed)
        self.y_label = QLabel("0.0")
        pos_layout.addRow("Y:", self._slider_with_label(self.y_slider,
                                                         self.y_label))

        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setRange(0, 200)  # 0–20.0 mm × 10
        self.z_slider.setValue(100)
        self.z_slider.valueChanged.connect(self.on_position_changed)
        self.z_label = QLabel("10.0")
        pos_layout.addRow("Z:", self._slider_with_label(self.z_slider,
                                                         self.z_label))

        layout.addWidget(pos_group)

        # Pattern selection
        pat_group = QGroupBox("Phase Pattern")
        pat_layout = QHBoxLayout(pat_group)
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(PATTERNS)
        self.pattern_combo.currentIndexChanged.connect(self.on_pattern_changed)
        pat_layout.addWidget(self.pattern_combo)

        self.active_btn = QPushButton("Activate")
        self.active_btn.setCheckable(True)
        self.active_btn.clicked.connect(self.on_active_toggled)
        pat_layout.addWidget(self.active_btn)

        layout.addWidget(pat_group)

        # Status display
        status_group = QGroupBox("Status")
        status_layout = QFormLayout(status_group)

        self.particle_label = QLabel("No object")
        status_layout.addRow("Particle:", self.particle_label)

        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(0)
        status_layout.addRow("Battery:", self.battery_bar)

        self.temp_label = QLabel("--")
        status_layout.addRow("Temperature:", self.temp_label)

        self.safety_label = QLabel("OK")
        self.safety_label.setStyleSheet("color: green; font-weight: bold;")
        status_layout.addRow("Safety:", self.safety_label)

        layout.addWidget(status_group)

        # Log output
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)

        log_btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.export_csv)
        log_btn_layout.addWidget(self.export_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_log)
        log_btn_layout.addWidget(self.clear_btn)
        log_layout.addLayout(log_btn_layout)

        layout.addWidget(log_group)

    def _slider_with_label(self, slider, label):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(slider)
        layout.addWidget(label)
        return widget

    def on_position_changed(self):
        x = self.x_slider.value() / 10.0
        y = self.y_slider.value() / 10.0
        z = self.z_slider.value() / 10.0
        self.x_label.setText(f"{x:.1f}")
        self.y_label.setText(f"{y:.1f}")
        self.z_label.setText(f"{z:.1f}")
        cmd = f"CMD,SET_XYZ,{x:.2f},{y:.2f},{z:.2f}"
        self.ble_thread.queue_command(cmd)

    def on_pattern_changed(self, idx):
        cmd = f"CMD,SET_PATTERN,{idx}"
        self.ble_thread.queue_command(cmd)
        self.log(f"Pattern: {PATTERNS[idx]}")

    def on_active_toggled(self, checked):
        cmd = f"CMD,SET_ACTIVE,{1 if checked else 0}"
        self.ble_thread.queue_command(cmd)
        self.active_btn.setText("Deactivate" if checked else "Activate")
        self.log("Transducers activated" if checked else "Transducers deactivated")

    def on_state(self, state_text):
        """Parse state update from device."""
        # Format: STATE,<x>,<y>,<z>,<pattern>,<particle>,<bat_mv>,<safety>
        parts = state_text.replace("STATE,", "").split(",")
        if len(parts) >= 7:
            try:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                pattern = int(parts[3])
                particle = int(parts[4])
                bat_mv = int(parts[5])
                safety = int(parts[6])

                # Update particle status
                if particle:
                    self.particle_label.setText("Detected")
                    self.particle_label.setStyleSheet(
                        "color: green; font-weight: bold;")
                else:
                    self.particle_label.setText("No object")
                    self.particle_label.setStyleSheet("color: gray;")

                # Update battery
                bat_pct = max(0, min(100, (bat_mv - 6000) * 100 // 2400))
                self.battery_bar.setValue(bat_pct)

                # Update safety
                safety_names = ["OK", "LID OPEN", "TILT!", "LOW BAT",
                                "HOT!", "RELEASE", "WDG", "OFF"]
                if safety == 0:
                    self.safety_label.setText("OK")
                    self.safety_label.setStyleSheet(
                        "color: green; font-weight: bold;")
                else:
                    name = safety_names[safety] if safety < len(safety_names) else "???"
                    self.safety_label.setText(name)
                    self.safety_label.setStyleSheet(
                        "color: red; font-weight: bold;")

                # Log data
                self.log_data.append({
                    'timestamp': datetime.now().isoformat(),
                    'x': x, 'y': y, 'z': z,
                    'pattern': pattern,
                    'particle': particle,
                    'battery_mv': bat_mv,
                    'safety': safety,
                })

            except (ValueError, IndexError):
                pass

    def on_connected(self):
        self.connected = True
        self.conn_label.setText("Connected")
        self.conn_label.setStyleSheet("color: green; font-weight: bold;")
        self.log("BLE connected to Levia Forge")

    def on_disconnected(self):
        self.connected = False
        self.conn_label.setText("Disconnected")
        self.conn_label.setStyleSheet("color: red; font-weight: bold;")
        self.log("BLE disconnected")

    def on_error(self, msg):
        self.log(f"Error: {msg}")

    def reconnect(self):
        if self.ble_thread.isRunning():
            self.ble_thread.stop()
            self.ble_thread.wait(2000)
        self.ble_thread = BLEThread()
        self.ble_thread.state_received.connect(self.on_state)
        self.ble_thread.connected.connect(self.on_connected)
        self.ble_thread.disconnected.connect(self.on_disconnected)
        self.ble_thread.error.connect(self.on_error)
        self.ble_thread.start()

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")

    def clear_log(self):
        self.log_text.clear()
        self.log_data.clear()

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Session Log", "levia_session.csv",
            "CSV Files (*.csv)")
        if filename:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'timestamp', 'x', 'y', 'z', 'pattern',
                    'particle', 'battery_mv', 'safety'
                ])
                writer.writeheader()
                writer.writerows(self.log_data)
            self.log(f"Exported {len(self.log_data)} rows to {filename}")

    def closeEvent(self, event):
        if self.ble_thread.isRunning():
            self.ble_thread.stop()
            self.ble_thread.wait(3000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = LeviaForgeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()