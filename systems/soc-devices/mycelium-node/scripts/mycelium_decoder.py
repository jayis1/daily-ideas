#!/usr/bin/env python3
"""
Mycelium Node — MQTT Payload Decoder

Decodes Mycelium Node MQTT JSON payloads into structured Python objects.
Useful for Home Assistant integration, Node-RED, or custom dashboards.

Usage:
    python3 mycelium_decoder.py --payload '{"id":"mycelium-a1b2c3",...}'
    
    Or use as a library:
        from mycelium_decoder import MyceliumReading
        reading = MyceliumReading.from_mqtt(payload_bytes)
"""

import json
import sys
import argparse
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChamberData:
    """Chamber sensor readings (SHT40 + SCD41 + TSL2591)."""
    temp_c: float = 0.0       # °C
    rh_pct: float = 0.0       # %RH
    co2_ppm: int = 0          # ppm
    light_lux: float = 0.0    # lux


@dataclass
class SubstrateData:
    """Substrate sensor readings (SHT40 + DS18B20)."""
    temp_c: float = 0.0       # °C
    rh_pct: float = 0.0       # %RH
    deep_temp_1_c: float = 0.0  # °C (3cm depth)
    deep_temp_2_c: float = 0.0  # °C (7cm depth)


@dataclass
class ActuatorData:
    """Current actuator output percentages."""
    humidifier_pct: float = 0.0  # 0-100%
    heater_pct: float = 0.0      # 0-100%
    fan_pct: float = 0.0         # 0-100%
    light_pct: float = 0.0       # 0-100%


@dataclass
class PowerData:
    """Power rail voltages."""
    lipo_v: float = 0.0      # V
    usb_v: float = 0.0       # V
    rail_12v: float = 0.0    # V


@dataclass
class MyceliumReading:
    """Complete Mycelium Node sensor reading."""
    device_id: str = ""
    timestamp: int = 0
    phase: str = ""
    chamber: ChamberData = field(default_factory=ChamberData)
    substrate: SubstrateData = field(default_factory=SubstrateData)
    actuators: ActuatorData = field(default_factory=ActuatorData)
    power: PowerData = field(default_factory=PowerData)

    @classmethod
    def from_mqtt(cls, payload: bytes) -> 'MyceliumReading':
        """Decode an MQTT payload into a MyceliumReading object."""
        data = json.loads(payload.decode('utf-8'))
        reading = cls()
        reading.device_id = data.get('id', '')
        reading.timestamp = data.get('ts', 0)
        reading.phase = data.get('phase', '')

        if 'chamber' in data:
            c = data['chamber']
            reading.chamber = ChamberData(
                temp_c=c.get('temp_c', 0.0),
                rh_pct=c.get('rh_pct', 0.0),
                co2_ppm=c.get('co2_ppm', 0),
                light_lux=c.get('light_lux', 0.0),
            )

        if 'substrate' in data:
            s = data['substrate']
            reading.substrate = SubstrateData(
                temp_c=s.get('temp_c', 0.0),
                rh_pct=s.get('rh_pct', 0.0),
                deep_temp_1_c=s.get('deep_temp_1_c', 0.0),
                deep_temp_2_c=s.get('deep_temp_2_c', 0.0),
            )

        if 'actuators' in data:
            a = data['actuators']
            reading.actuators = ActuatorData(
                humidifier_pct=a.get('humidifier_pct', 0.0),
                heater_pct=a.get('heater_pct', 0.0),
                fan_pct=a.get('fan_pct', 0.0),
                light_pct=a.get('light_pct', 0.0),
            )

        if 'power' in data:
            p = data['power']
            reading.power = PowerData(
                lipo_v=p.get('lipo_v', 0.0),
                usb_v=p.get('usb_v', 0.0),
                rail_12v=p.get('rail_12v', 0.0),
            )

        return reading

    def to_influxdb(self, measurement: str = "mycelium") -> str:
        """Convert to InfluxDB line protocol format."""
        tags = f"device={self.device_id},phase={self.phase}"
        fields = (
            f"chamber_temp={self.chamber.temp_c},"
            f"chamber_rh={self.chamber.rh_pct},"
            f"co2={self.chamber.co2_ppm}i,"
            f"light={self.chamber.light_lux},"
            f"substrate_temp={self.substrate.temp_c},"
            f"substrate_rh={self.substrate.rh_pct},"
            f"deep_temp_1={self.substrate.deep_temp_1_c},"
            f"deep_temp_2={self.substrate.deep_temp_2_c},"
            f"humidifier={self.actuators.humidifier_pct},"
            f"heater={self.actuators.heater_pct},"
            f"fan={self.actuators.fan_pct},"
            f"light_out={self.actuators.light_pct},"
            f"lipo_v={self.power.lipo_v},"
            f"usb_v={self.power.usb_v},"
            f"rail_12v={self.power.rail_12v}"
        )
        return f"{measurement},{tags} {fields} {self.timestamp}"

    def to_prometheus(self) -> str:
        """Convert to Prometheus exposition format."""
        prefix = "mycelium"
        lines = [
            f"# HELP {prefix}_chamber_temp Chamber temperature in Celsius",
            f"# TYPE {prefix}_chamber_temp gauge",
            f'{prefix}_chamber_temp{{device="{self.device_id}",phase="{self.phase}"}} {self.chamber.temp_c}',
            f"# HELP {prefix}_chamber_rh Chamber relative humidity in percent",
            f"# TYPE {prefix}_chamber_rh gauge",
            f'{prefix}_chamber_rh{{device="{self.device_id}",phase="{self.phase}"}} {self.chamber.rh_pct}',
            f"# HELP {prefix}_co2 CO2 concentration in ppm",
            f"# TYPE {prefix}_co2 gauge",
            f'{prefix}_co2{{device="{self.device_id}",phase="{self.phase}"}} {self.chamber.co2_ppm}',
            f"# HELP {prefix}_substrate_temp Substrate temperature in Celsius",
            f"# TYPE {prefix}_substrate_temp gauge",
            f'{prefix}_substrate_temp{{device="{self.device_id}",phase="{self.phase}"}} {self.substrate.temp_c}',
            f"# HELP {prefix}_humidifier Humidifier output in percent",
            f"# TYPE {prefix}_humidifier gauge",
            f'{prefix}_humidifier{{device="{self.device_id}",phase="{self.phase}"}} {self.actuators.humidifier_pct}',
            f"# HELP {prefix}_fan Fan output in percent",
            f"# TYPE {prefix}_fan gauge",
            f'{prefix}_fan{{device="{self.device_id}",phase="{self.phase}"}} {self.actuators.fan_pct}',
        ]
        return '\n'.join(lines)

    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"[{self.device_id}] Phase: {self.phase}\n"
            f"  Chamber:  {self.chamber.temp_c:.1f}°C / {self.chamber.rh_pct:.1f}% RH / "
            f"CO₂={self.chamber.co2_ppm}ppm / Light={self.chamber.light_lux:.0f}lux\n"
            f"  Substrate: {self.substrate.temp_c:.1f}°C / {self.substrate.rh_pct:.1f}% RH / "
            f"Deep: {self.substrate.deep_temp_1_c:.1f}°C, {self.substrate.deep_temp_2_c:.1f}°C\n"
            f"  Actuators: Hum={self.actuators.humidifier_pct:.0f}% / "
            f"Heat={self.actuators.heater_pct:.0f}% / "
            f"Fan={self.actuators.fan_pct:.0f}% / "
            f"Light={self.actuators.light_pct:.0f}%\n"
            f"  Power: LiPo={self.power.lipo_v:.2f}V / USB={self.power.usb_v:.2f}V / "
            f"12V={self.power.rail_12v:.1f}V"
        )


# ============================================================
# Home Assistant MQTT Discovery Configuration Generator
# ============================================================

def generate_ha_discovery(device_id: str, broker: str = "mqtt.local") -> list[dict]:
    """Generate Home Assistant MQTT discovery configuration payloads."""
    base = f"mycelium/node/{device_id}"
    device_info = {
        "identifiers": [device_id],
        "name": f"Mycelium Node {device_id}",
        "manufacturer": "SoC Device Inventions",
        "model": "Mycelium Node v1.0",
        "sw_version": "1.0.0",
    }

    entities = [
        {
            "platform": "sensor",
            "name": f"Chamber Temperature",
            "stat_t": f"{base}/sensors",
            "val_tpl": "{{ value_json.chamber.temp_c }}",
            "unit_of_meas": "°C",
            "dev_cla": "temperature",
            "state_class": "measurement",
            "uniq_id": f"{device_id}_chamber_temp",
        },
        {
            "platform": "sensor",
            "name": f"Chamber Humidity",
            "stat_t": f"{base}/sensors",
            "val_tpl": "{{ value_json.chamber.rh_pct }}",
            "unit_of_meas": "%",
            "dev_cla": "humidity",
            "state_class": "measurement",
            "uniq_id": f"{device_id}_chamber_rh",
        },
        {
            "platform": "sensor",
            "name": f"CO2",
            "stat_t": f"{base}/sensors",
            "val_tpl": "{{ value_json.chamber.co2_ppm }}",
            "unit_of_meas": "ppm",
            "icon": "mdi:molecule-co2",
            "state_class": "measurement",
            "uniq_id": f"{device_id}_co2",
        },
        {
            "platform": "sensor",
            "name": f"Light",
            "stat_t": f"{base}/sensors",
            "val_tpl": "{{ value_json.chamber.light_lux }}",
            "unit_of_meas": "lux",
            "dev_cla": "illuminance",
            "state_class": "measurement",
            "uniq_id": f"{device_id}_light",
        },
        {
            "platform": "sensor",
            "name": f"Substrate Temperature",
            "stat_t": f"{base}/sensors",
            "val_tpl": "{{ value_json.substrate.temp_c }}",
            "unit_of_meas": "°C",
            "dev_cla": "temperature",
            "state_class": "measurement",
            "uniq_id": f"{device_id}_substrate_temp",
        },
        {
            "platform": "sensor",
            "name": f"CO2 Threshold",
            "stat_t": f"{base}/status",
            "val_tpl": "{{ value_json.setpoints.co2_max_ppm }}",
            "unit_of_meas": "ppm",
            "icon": "mdi:molecule-co2",
            "uniq_id": f"{device_id}_co2_max",
        },
        {
            "platform": "select",
            "name": f"Growth Phase",
            "stat_t": f"{base}/sensors",
            "val_tpl": "{{ value_json.phase }}",
            "cmd_t": f"{base}/phase",
            "options": ["colonization", "pinning", "fruiting", "harvest", "manual"],
            "uniq_id": f"{device_id}_phase",
        },
        {
            "platform": "number",
            "name": f"Temperature Setpoint",
            "stat_t": f"{base}/status",
            "val_tpl": "{{ value_json.setpoints.temp_c }}",
            "cmd_t": f"{base}/setpoint",
            "cmd_tpl": '{"temp_c": {{ value }} }',
            "min": 5,
            "max": 40,
            "step": 0.5,
            "unit_of_meas": "°C",
            "uniq_id": f"{device_id}_temp_setpoint",
        },
        {
            "platform": "number",
            "name": f"Humidity Setpoint",
            "stat_t": f"{base}/status",
            "val_tpl": "{{ value_json.setpoints.rh_pct }}",
            "cmd_t": f"{base}/setpoint",
            "cmd_tpl": '{"rh_pct": {{ value }} }',
            "min": 30,
            "max": 100,
            "step": 1,
            "unit_of_meas": "%",
            "uniq_id": f"{device_id}_rh_setpoint",
        },
    ]

    # Add device info to each entity
    for entity in entities:
        entity["device"] = device_info

    return entities


def main():
    parser = argparse.ArgumentParser(description='Mycelium Node MQTT Payload Decoder')
    parser.add_argument('--payload', help='Raw MQTT payload (JSON string)')
    parser.add_argument('--influxdb', action='store_true', help='Output InfluxDB line protocol')
    parser.add_argument('--prometheus', action='store_true', help='Output Prometheus format')
    parser.add_argument('--ha-discovery', action='store_true', help='Generate Home Assistant discovery configs')
    parser.add_argument('--device', default='mycelium-a1b2c3', help='Device ID for HA discovery')
    args = parser.parse_args()

    if args.ha_discovery:
        configs = generate_ha_discovery(args.device)
        for config in configs:
            topic = f"homeassistant/{config['platform']}/mycelium_{args.device}/{config['uniq_id']}/config"
            print(f"\nTopic: {topic}")
            print(json.dumps(config, indent=2))
        return

    if args.payload:
        reading = MyceliumReading.from_mqtt(args.payload.encode('utf-8'))
        if args.influxdb:
            print(reading.to_influxdb())
        elif args.prometheus:
            print(reading.to_prometheus())
        else:
            print(reading)
    else:
        # Demo with sample data
        sample = json.dumps({
            "id": "mycelium-a1b2c3",
            "ts": 1718534400,
            "phase": "fruiting",
            "chamber": {"temp_c": 22.3, "rh_pct": 91.2, "co2_ppm": 856, "light_lux": 420},
            "substrate": {"temp_c": 23.1, "rh_pct": 88.7, "deep_temp_1_c": 22.8, "deep_temp_2_c": 22.5},
            "actuators": {"humidifier_pct": 45, "heater_pct": 12, "fan_pct": 30, "light_pct": 70},
            "power": {"lipo_v": 3.92, "usb_v": 5.01, "rail_12v": 12.1}
        })
        reading = MyceliumReading.from_mqtt(sample.encode('utf-8'))
        
        print("=== Sample Reading ===")
        print(reading)
        print("\n=== InfluxDB Line Protocol ===")
        print(reading.to_influxdb())
        print("\n=== Prometheus Format ===")
        print(reading.to_prometheus())


if __name__ == '__main__':
    main()