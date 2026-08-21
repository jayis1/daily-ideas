# Brew Sense — API Reference

## BLE GATT Service

### Service: BrewSense (0xFFB0)

| Characteristic | UUID  | Type      | Access      | Description                          |
|---------------|-------|-----------|-------------|--------------------------------------|
| Gravity       | FFB1  | float32   | Read/Notify | Specific gravity (e.g., 1.050)        |
| Temperature   | FFB2  | float32   | Read/Notify | Temperature in °C                     |
| CO₂           | FFB3  | uint16    | Read/Notify | CO₂ concentration in ppm              |
| pH             | FFB4  | float32   | Read/Notify | pH value (0.0-14.0)                   |
| Pressure      | FFB5  | float32   | Read        | Barometric pressure in hPa            |
| Stage         | FFB6  | uint8     | Read/Notify | Fermentation stage (0-5)             |
| Activity      | FFB7  | uint8     | Read/Notify | Activity index (0-100)               |
| Battery       | FFB8  | uint8     | Read        | Battery percentage (0-100)           |
| Trend         | FFB9  | int8      | Read/Notify | Gravity trend (-2 to +2)             |
| Device Info   | FFBA  | string    | Read        | Device info string                   |

### Fermentation Stage Values

| Value | Stage     | Description                              |
|-------|-----------|------------------------------------------|
| 0     | LAG       | Yeast adapting, high gravity, low activity |
| 1     | ACTIVE    | Gravity dropping, CO₂ rising, krausen forming |
| 2     | PEAK      | Maximum activity, gravity plateau         |
| 3     | SLOWING   | Activity declining, gravity slowly dropping |
| 4     | FINISHED  | Gravity stable, CO₂ near zero             |
| 5     | STUCK     | No change for >48h, possible stuck ferment |

### Trend Values

| Value | Meaning        |
|-------|----------------|
| -2    | Dropping fast   |
| -1    | Dropping slowly |
| 0     | Stable          |
| +1    | Rising slowly   |
| +2    | Rising fast     |

### Advertising Data Format

```
Byte 0:  Length (0x1A = 26)
Byte 1:  Type (0xFF = Manufacturer-specific)
Byte 2-3: Company ID (0x0001 custom)
Byte 4-7: Gravity (float32 LE)
Byte 8-9: Temperature (int16, 0.1°C units)
Byte 10: Stage (uint8)
Byte 11: Activity (uint8)
```

## MQTT Topics

All topics follow the pattern: `brewsense/{device_id}/{metric}`

| Topic                    | Type   | Unit  | Description               |
|--------------------------|--------|-------|---------------------------|
| brewsense/{id}/gravity   | float  | SG    | Specific gravity          |
| brewsense/{id}/temperature | float | °C    | Temperature               |
| brewsense/{id}/co2       | uint16 | ppm   | CO₂ concentration         |
| brewsense/{id}/ph        | float  | -     | pH value                  |
| brewsense/{id}/pressure  | float  | hPa   | Barometric pressure       |
| brewsense/{id}/stage     | string | -     | LAG/ACTIVE/PEAK/SLOWING/FINISHED/STUCK |
| brewsense/{id}/activity  | uint8  | 0-100 | Activity index            |
| brewsense/{id}/trend      | int8   | -2..2 | Gravity trend             |
| brewsense/{id}/status    | JSON   | -     | All fields combined       |

### Status JSON Format

```json
{
  "device_id": "brewsense-001",
  "timestamp": 1718354400,
  "gravity": 1.0500,
  "temperature": 20.5,
  "co2": 850,
  "ph": 4.2,
  "pressure": 1013.25,
  "stage": "ACTIVE",
  "activity": 72,
  "trend": -1,
  "battery_pct": 85
}
```

## Serial Command Interface

Connect via UART2 (115200 baud, 8N1) for configuration and calibration.

### Commands

| Command            | Description                    | Response                     |
|--------------------|--------------------------------|------------------------------|
| `CALS,air`        | Air calibration (densitometer) | `CAL:AIR,f=4250.3`          |
| `CALS,water`      | Water calibration at current T | `CAL:WATER,f=3980.7`        |
| `CALR`             | Read calibration data          | `CAL:f_air=4250.3,f_water=3980.7,t=20.0` |
| `CALZ`             | Erase calibration              | `CAL:ERASED`                 |
| `OG,1.050`         | Set original gravity           | `OG:1.050`                   |
| `FG,1.010`         | Set target final gravity       | `FG:1.010`                   |
| `PH4`              | Calibrate pH at 4.0            | `PH:CAL4,OK`                 |
| `PH7`              | Calibrate pH at 7.0            | `PH:CAL7,OK`                 |
| `RESET`            | Reset fermentation engine      | `RESET:OK`                   |
| `WIFI,ssid,pass`   | Configure Wi-Fi credentials    | `WIFI:OK` or `WIFI:ERROR`    |
| `MQTT,broker,port` | Configure MQTT broker          | `MQTT:OK` or `MQTT:ERROR`   |
| `READ`             | Read all sensors now           | `SG:1.050,T:20.5,CO2:850,...` |
| `SLEEP`            | Enter low-power mode           | `SLEEP:OK`                   |
| `WAKE`             | Wake from low-power            | `WAKE:OK`                    |
| `INFO`             | Device info                    | `BrewSense v1.0,STM32L476,...` |

## Home Assistant Integration

Add to `configuration.yaml`:

```yaml
mqtt:
  sensor:
    - name: "Brew Sense Gravity"
      state_topic: "brewsense/brewsense-001/gravity"
      unit_of_measurement: "SG"
      device_class: "distance"
    
    - name: "Brew Sense Temperature"
      state_topic: "brewsense/brewsense-001/temperature"
      unit_of_measurement: "°C"
      device_class: "temperature"
    
    - name: "Brew Sense CO2"
      state_topic: "brewsense/brewsense-001/co2"
      unit_of_measurement: "ppm"
      device_class: "carbon_dioxide"
    
    - name: "Brew Sense pH"
      state_topic: "brewsense/brewsense-001/ph"
      device_class: "ph"
    
    - name: "Brew Sense Stage"
      state_topic: "brewsense/brewsense-001/stage"
    
    - name: "Brew Sense Activity"
      state_topic: "brewsense/brewsense-001/activity"
      unit_of_measurement: "%"
    
    - name: "Brew Sense Battery"
      state_topic: "brewsense/brewsense-001/status"
      value_template: "{{ value_json.battery_pct }}"
      unit_of_measurement: "%"
      device_class: "battery"
```

## Brewfather Custom Stream

Configure in Brewfather → Settings → Custom Stream:

```
URL: mqtt://your-broker:1883
Topic: brewsense/brewsense-001/status
```

Or use the HTTP push method via scripts/brewfather_sync.py.