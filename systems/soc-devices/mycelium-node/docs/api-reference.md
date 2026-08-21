# Mycelium Node — API Reference

## Serial Debug Interface

**Configuration**: 115200 baud, 8 data bits, no parity, 1 stop bit (8N1)

**Prompt**: `MYC> `

All commands are case-insensitive. Arguments are separated by spaces.

---

## Command Reference

### Status & Monitoring

| Command | Description |
|---------|-------------|
| `status` | Display all sensor readings, actuator outputs, phase, and power status |
| `sensors` | Display raw sensor values with CRC status |
| `pid` | Display current PID gains and state (integral, derivative) |
| `uptime` | Display system uptime in seconds |
| `errors` | Display error flags (sensor failures, overtemp, low battery) |

### Setpoint Configuration

| Command | Arguments | Description |
|---------|-----------|-------------|
| `set humidity` | `<0-100>` | Set chamber humidity setpoint (% RH) |
| `set temp` | `<-10 to 50>` | Set temperature setpoint (°C) |
| `set co2_max` | `<0-40000>` | Set maximum CO₂ before fan activates (ppm). 0 = no CO₂ control |
| `set light` | `<0-100>` | Set grow light intensity (%) |
| `set light_hours` | `<0-24>` | Set photoperiod (hours of light per day) |

### Growth Phase Control

| Command | Description |
|---------|-------------|
| `phase col` | Switch to Colonization phase (24°C, 82% RH, 5000 ppm CO₂, 10% light) |
| `phase pin` | Switch to Pinning phase (18°C, 92% RH, 1000 ppm CO₂, 50% light) |
| `phase frt` | Switch to Fruiting phase (22°C, 93% RH, 1000 ppm CO₂, 70% light) |
| `phase har` | Switch to Harvest phase (20°C, 75% RH, no CO₂ control, light off) |
| `phase man` | Switch to Manual phase (keeps current setpoints, no auto-advance) |
| `auto on` | Enable auto-advance between phases |
| `auto off` | Disable auto-advance |
| `advance` | Manually advance to next phase |

### Species Presets

| Command | Arguments | Description |
|---------|-----------|-------------|
| `species list` | — | List available species presets |
| `species apply` | `<name>` | Apply species preset (sets all phase parameters) |
| `species show` | `<name>` | Show parameters for a species |

Available presets: `Oyster`, `LionsMane`, `Shiitake`, `Reishi`, `Chestnut`

### PID Tuning

| Command | Arguments | Description |
|---------|-----------|-------------|
| `pid humidity kp` | `<float>` | Set humidity PID proportional gain |
| `pid humidity ki` | `<float>` | Set humidity PID integral gain |
| `pid humidity kd` | `<float>` | Set humidity PID derivative gain |
| `pid temp kp` | `<float>` | Set temperature PID proportional gain |
| `pid temp ki` | `<float>` | Set temperature PID integral gain |
| `pid temp kd` | `<float>` | Set temperature PID derivative gain |
| `pid co2 kp` | `<float>` | Set CO₂ PID proportional gain |
| `pid co2 ki` | `<float>` | Set CO₂ PID integral gain |
| `pid co2 kd` | `<float>` | Set CO₂ PID derivative gain |
| `pid reset` | — | Reset all PID integrals and derivatives |

### Manual Override

| Command | arguments | Description |
|---------|-----------|-------------|
| `override humidifier` | `<0-100>` | Force humidifier to % (auto-clears in 10 min) |
| `override heater` | `<0-100>` | Force heater to % (auto-clears in 10 min) |
| `override fan` | `<0-100>` | Force fan to % (auto-clears in 10 min) |
| `override light` | `<0-100>` | Force light to % (auto-clears in 10 min) |
| `override clear` | — | Clear all manual overrides |

### Sensor Calibration

| Command | arguments | Description |
|---------|-----------|-------------|
| `calibrate co2` | `<ppm>` | SCD41 forced recalibration at known CO₂ concentration (expose to fresh air first, use 420) |
| `calibrate co2 reset` | — | SCD41 factory reset (clears all calibration data) |
| `calibrate temp offset` | `<°C>` | SCD41 temperature offset (e.g., +4°C to compensate for self-heating) |
| `calibrate altitude` | `<m>` | SCD41 altitude compensation (adjusts CO₂ for barometric pressure) |

### WiFi & MQTT

| Command | arguments | Description |
|---------|-----------|-------------|
| `wifi scan` | — | Scan for available WiFi networks |
| `wifi connect` | `"<ssid>" "<pass>"` | Connect to WiFi network |
| `wifi disconnect` | — | Disconnect from WiFi |
| `wifi status` | — | Show WiFi connection status and IP |
| `mqtt start` | — | Start MQTT client and connect to broker |
| `mqtt stop` | — | Stop MQTT client |
| `mqtt status` | — | Show MQTT connection status |
| `mqtt broker` | `<host> <port>` | Set MQTT broker address |

### System

| Command | arguments | Description |
|---------|-----------|-------------|
| `save` | — | Save current config to NVS (persists across reboots) |
| `load` | — | Load config from NVS |
| `reset` | — | Factory reset (erase NVS, restore defaults, reboot) |
| `reboot` | — | Reboot the device |
| `version` | — | Show firmware version |
| `help` | — | Display command list |

---

## MQTT API

### Connection

| Parameter | Default |
|-----------|---------|
| **Broker** | Configurable (default: `mqtt.local`) |
| **Port** | 1883 |
| **Client ID** | `mycelium-{MAC_LAST_3}` |
| **Username** | None (configurable) |
| **Password** | None (configurable) |
| **Keepalive** | 60 s |
| **QoS** | 1 (at least once) |

### Topic Structure

All topics use the prefix `mycelium/node/{device_id}/` where `{device_id}` is derived from the device's MAC address (e.g., `mycelium-a1b2c3`).

### Publish Topics

#### `mycelium/node/{id}/sensors` (every 60 s)

```json
{
  "id": "mycelium-a1b2c3",
  "ts": 1718534400,
  "phase": "fruiting",
  "chamber": {
    "temp_c": 22.3,
    "rh_pct": 91.2,
    "co2_ppm": 856,
    "light_lux": 420
  },
  "substrate": {
    "temp_c": 23.1,
    "rh_pct": 88.7,
    "deep_temp_1_c": 22.8,
    "deep_temp_2_c": 22.5
  },
  "actuators": {
    "humidifier_pct": 45,
    "heater_pct": 12,
    "fan_pct": 30,
    "light_pct": 70
  },
  "power": {
    "lipo_v": 3.92,
    "usb_v": 5.01,
    "rail_12v": 12.1
  }
}
```

#### `mycelium/node/{id}/status` (every 300 s)

```json
{
  "id": "mycelium-a1b2c3",
  "ts": 1718534700,
  "uptime_s": 86400,
  "phase": "fruiting",
  "phase_day": 5,
  "setpoints": {
    "temp_c": 22.0,
    "rh_pct": 93.0,
    "co2_max_ppm": 1000,
    "light_pct": 70
  },
  "pid": {
    "humidity": { "kp": 2.0, "ki": 0.1, "kd": 0.5, "output": 45.2 },
    "temperature": { "kp": 1.5, "ki": 0.05, "kd": 0.3, "output": 12.1 },
    "co2": { "kp": 3.0, "ki": 0.2, "kd": 0.0, "output": 30.0 }
  },
  "wifi_rssi": -52,
  "mqtt_connected": true,
  "errors": 0
}
```

### Subscribe Topics

#### `mycelium/node/{id}/setpoint`

Set target values. Example:
```json
{
  "temp_c": 22.0,
  "rh_pct": 93.0,
  "co2_max_ppm": 1000,
  "light_pct": 70
}
```

#### `mycelium/node/{id}/phase`

Change growth phase. Payload is a string: `"colonization"`, `"pinning"`, `"fruiting"`, `"harvest"`, `"manual"`

#### `mycelium/node/{id}/override`

Manual actuator override. Example:
```json
{
  "humidifier_pct": 50,
  "heater_pct": 0,
  "fan_pct": 40,
  "light_pct": 100,
  "timeout_s": 600
}
```

#### `mycelium/node/{id}/config`

Full configuration update. Example:
```json
{
  "pid_humidity": { "kp": 2.5, "ki": 0.15, "kd": 0.5 },
  "pid_temperature": { "kp": 1.5, "ki": 0.05, "kd": 0.3 },
  "pid_co2": { "kp": 3.0, "ki": 0.2, "kd": 0.0 },
  "sensor_interval_s": 5,
  "mqtt_interval_s": 60,
  "auto_advance": true
}
```

---

## BLE GATT Services

### Service: Environment (0x181A)

| Characteristic | UUID | Type | Access | Description |
|---------------|------|------|--------|-------------|
| Chamber Temp | 0x2A6E | float32 | Read | Chamber air temperature (°C) |
| Chamber RH | 0x2A6F | float32 | Read | Chamber relative humidity (%) |
| Substrate Temp | 2A1C-custom | float32 | Read | Substrate surface temperature (°C) |
| Substrate RH | 2A1D-custom | float32 | Read | Substrate relative humidity (%) |
| CO₂ | 2A1E-custom | uint16 | Read | CO₂ concentration (ppm) |
| Light | 2A1F-custom | float32 | Read | Ambient light (lux) |

### Service: Control (0x1820)

| Characteristic | UUID | Type | Access | Description |
|---------------|------|------|--------|-------------|
| Humidifier % | 2A20-custom | uint8 | Read/Write | Humidifier output 0–100% |
| Heater % | 2A21-custom | uint8 | Read/Write | Heater output 0–100% |
| Fan % | 2A22-custom | uint8 | Read/Write | Fan output 0–100% |
| Light % | 2A23-custom | uint8 | Read/Write | Light output 0–100% |

### Service: Phase (0x1821)

| Characteristic | UUID | Type | Access | Description |
|---------------|------|------|--------|-------------|
| Current Phase | 2A24-custom | uint8 | Read/Write | 0=colonization, 1=pinning, 2=fruiting, 3=harvest, 4=manual |
| Days in Phase | 2A25-custom | uint8 | Read | Days since phase transition |
| Auto-advance | 2A26-custom | bool | Read/Write | Enable/disable auto-advance |

### Service: Config (0x1822)

| Characteristic | UUID | Type | Access | Description |
|---------------|------|------|--------|-------------|
| Temp Setpoint | 2A27-custom | float32 | Read/Write | Target temperature (°C) |
| RH Setpoint | 2A28-custom | float32 | Read/Write | Target humidity (%) |
| CO₂ Max | 2A29-custom | uint16 | Read/Write | CO₂ threshold (ppm) |
| Light % | 2A2A-custom | uint8 | Read/Write | Light intensity 0–100% |

---

## Home Assistant MQTT Discovery

Mycelium Node auto-publishes Home Assistant MQTT discovery configs for all sensors and controls.

### Auto-discovered Entities

| Entity | Platform | Topic |
|--------|----------|-------|
| Chamber Temperature | `sensor` | `homeassistant/sensor/mycelium_{id}/chamber_temp/config` |
| Chamber Humidity | `sensor` | `homeassistant/sensor/mycelium_{id}/chamber_rh/config` |
| Substrate Temperature | `sensor` | `homeassistant/sensor/mycelium_{id}/substrate_temp/config` |
| Substrate Humidity | `sensor` | `homeassistant/sensor/mycelium_{id}/substrate_rh/config` |
| CO₂ | `sensor` | `homeassistant/sensor/mycelium_{id}/co2/config` |
| Light | `sensor` | `homeassistant/sensor/mycelium_{id}/light/config` |
| Humidifier Output | `sensor` | `homeassistant/sensor/mycelium_{id}/humidifier/config` |
| Heater Output | `sensor` | `homeassistant/sensor/mycelium_{id}/heater/config` |
| Fan Output | `sensor` | `homeassistant/sensor/mycelium_{id}/fan/config` |
| Light Output | `sensor` | `homeassistant/sensor/mycelium_{id}/light_out/config` |
| Growth Phase | `select` | `homeassistant/select/mycelium_{id}/phase/config` |
| Temperature Setpoint | `number` | `homeassistant/number/mycelium_{id}/temp_setpoint/config` |
| Humidity Setpoint | `number` | `homeassistant/number/mycelium_{id}/rh_setpoint/config` |
| CO₂ Threshold | `number` | `homeassistant/number/mycelium_{id}/co2_max/config` |
| LiPo Voltage | `sensor` | `homeassistant/sensor/mycelium_{id}/lipo_v/config` |

---

## Safety Features

1. **Thermal cutoff**: If chamber temperature exceeds 40°C, the safety relay opens and all actuators are shut off immediately. The relay must be manually reset via serial command or power cycle.

2. **LiPo protection**: If LiPo voltage drops below 3.3V, the device enters reduced-power mode (sensors only, no WiFi, 10-minute MQTT interval).

3. **Actuator limits**: The exhaust fan PWM is limited to 80% maximum to prevent excessive drying. The humidifier has a 5-minute maximum runtime with 30-second cooldown.

4. **I2C watchdog**: If any I2C sensor fails 10 consecutive reads, it is marked as failed and the error flag is set. PID controllers fall back to the last valid reading.

5. **SCD41 warm-up**: The SCD41 requires 60 seconds after power-on before readings are valid. The firmware discards readings during this period.