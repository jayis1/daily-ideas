# Kappa Pin — API Reference

## BLE GATT Interface

### Service: Kappa Pin (UUID 0x9101)

| Characteristic | UUID | Properties | Description |
|---|---|---|---|
| Data Stream | 0x9102 | Notify | Live ΔT samples during measurement |
| Result | 0x9103 | Read, Notify | Final measurement result |
| Command | 0x9104 | Write | Send commands to device |
| Info | 0x9105 | Read | Device info (firmware, probe, calibration) |

### Data Stream Format (0x9102)

Each notification is 6 bytes:

| Offset | Size | Field | Unit | Scaling |
|--------|------|-------|------|---------|
| 0 | 2 | timestamp | centiseconds | t_s × 100 |
| 2 | 2 | ΔT | mK × 4 | (int16, signed) |
| 4 | 2 | Q | mW | (int16, signed) |

### Result Format (0x9103)

17 bytes:

| Offset | Size | Field | Unit | Type |
|--------|------|-------|------|------|
| 0 | 4 | lambda | W/(m·K) | float32 LE |
| 4 | 4 | alpha | mm²/s | float32 LE |
| 8 | 4 | rho_cp | J/(m³·K) | float32 LE |
| 12 | 4 | effusivity | J/(m²·K·s^0.5) | float32 LE |
| 16 | 1 | status | enum | uint8 (0=done, 1=error) |

### Command Format (0x9104)

Write 1+ bytes:

| Command | Byte | Payload | Description |
|---------|------|---------|-------------|
| Start | 0x01 | none | Start measurement with current material |
| Stop | 0x02 | none | Cancel current measurement |
| Set Material | 0x03 | 1 byte: material ID (0-6) | Change material preset |
| Set Power | 0x04 | 4 bytes: float32 power (W) | Override heater power |
| Calibrate | 0x05 | none | Start calibration measurement |
| Get Info | 0x06 | none | Trigger info notify |

### Material IDs

| ID | Name | Probe | Power (W) | Pulse (s) |
|----|------|-------|-----------|-----------|
| 0 | Liquid | Hot-wire | 0.3 | 8 |
| 1 | Wet Soil | Needle | 1.0 | 30 |
| 2 | Dry Soil | Needle | 0.5 | 30 |
| 3 | Polymer | Needle | 0.5 | 20 |
| 4 | Insulation | Any | 0.2 | 60 |
| 5 | Metal Powder | Needle | 3.0 | 10 |
| 6 | Custom | Any | 1.0 | 20 |

## Wi-Fi Web Interface

### Connection
1. Connect to Wi-Fi AP: `KappaPin-XXXX` (open, no password)
2. Open browser to `http://192.168.4.1`

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/` | GET | Main HTML page with live chart |
| `/stream` | GET | Server-Sent Events — live ΔT data |
| `/result` | GET | Latest measurement result (HTML) |
| `/cmd?c=N` | GET | Send command (1=start, 2=stop) |
| `/csv` | GET | Download latest CSV log |

### SSE Stream Format
Each event: `data: t_s,dT_mK\n\n`

## SD Card Log Format

CSV file: `KP_YYYYMMDD_HHMMSS.csv`

```csv
# Kappa Pin measurement log
# Date: 2026-07-27T14:32:15Z
# Probe: 1
# Material: 1
# Power: 1.023 W
# Pulse: 30.0 s
# T0: 23.451 C
# Columns: t_s,T_C,dT_mK,V_heater_V,I_heater_A,Q_W
0.0000,23.451,0.00,0.000,0.000,0.000
0.0167,23.451,0.10,1.012,1.010,1.021
...
# Result:
# lambda=1.234 W/m.K
# alpha=0.567 mm2/s
# rhoCp=2.176e+06 J/m3.K
# effusivity=1638.0 J/m2.K.s0.5
# R2=0.99987
# n_points=1500
# END
```

## Measurement Theory Quick Reference

### Thermal Conductivity
```
λ = Q / (4π · m)
```
where:
- Q = heater power per unit length (W/m)
- m = slope of ΔT vs ln(t) in linear regime (°C)

### Thermal Diffusivity
```
α = (r² / 4) · exp(ln_term - γ - 4πλ·ΔT/Q)
```
Fitted via Levenberg-Marquardt to full transient model.

### Derived Properties
```
ρcₚ = λ / α          (volumetric heat capacity)
e = √(λ · ρcₚ)       (thermal effusivity)
```

### Units
| Quantity | Symbol | Unit |
|----------|--------|------|
| Thermal conductivity | λ | W·m⁻¹·K⁻¹ |
| Thermal diffusivity | α | mm²·s⁻¹ |
| Volumetric heat capacity | ρcₚ | J·m⁻³·K⁻¹ |
| Thermal effusivity | e | J·m⁻²·K⁻¹·s⁻⁰·⁵ |
| Power per length | Q | W·m⁻¹ |