# QCM Halo — API Reference

## BLE Protocol

The ESP32-C3 provides a BLE GATT service for communication with a phone or PC.

### Service & Characteristics

| UUID | Type | Direction | Description |
|------|------|-----------|-------------|
| `6e400001-...` | Service | — | Nordic UART-like service |
| `6e400002-...` | Characteristic | Write | Commands from phone → device |
| `6e400003-...` | Characteristic | Notify | Data from device → phone |

### Frame Format

All communication uses framed packets:

```
[SYNC0=0xA5][SYNC1=0x5A][CMD][LEN][DATA(LEN bytes)][CRC8]
```

CRC8: polynomial 0x07, initial value 0x00.

### Commands (Phone → Device, via ESP32-C3 → STM32)

| CMD | Name | Payload | Description |
|-----|------|---------|-------------|
| 0x81 | START_MEASURE | [channel, overtone_idx, sweep_flag] | Start a measurement |
| 0x82 | STOP | — | Stop current measurement |
| 0x83 | SET_CHANNEL | [channel] | Set active QCM channel (0 or 1) |
| 0x84 | SET_OVERTONE | [overtone_idx] | Set overtone (0-5: 1st/3rd/5th/7th/9th/11th) |
| 0x85 | SET_TEMP | [float: target°C] | Set TEC target temperature (15-50°C, 0=off) |
| 0x86 | SET_PUMP | [float: mL/min] | Set pump flow rate (0-5 mL/min, 0=stop) |
| 0x87 | SET_VALVE | [position] | Set valve position (0-5: buffer/sample/wash/rinse/waste/air) |
| 0x88 | CALIBRATE | — | Run baseline calibration |
| 0x89 | START_EXPERIMENT | [uint32: duration_s] | Start timed experiment |
| 0x8A | GET_STATUS | — | Query device status |
| 0x8B | SET_PARAMS | [acq_params_t struct] | Set all parameters at once |
| 0x8C | CONN_STATUS | [uint8: connected] | BLE connection status (ESP32→STM32) |

### Data Messages (Device → Phone)

| CMD | Name | Payload | Description |
|-----|------|---------|-------------|
| 0x01 | RESULT | 26 bytes | Single QCM-D measurement result |
| 0x02 | SWEEP | 56 bytes | Full overtone sweep (6 overtones) |
| 0x03 | VOIGT | 20 bytes | Voigt fit results |
| 0x04 | STATUS | 12 bytes | Device status (temp, battery, state) |
| 0x05 | RAW | variable | Raw text line |
| 0x06 | QUERY_CONN | — | Query BLE connection status |

### Result Packet (CMD 0x01, 26 bytes)

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 1 | channel | uint8 | QCM channel (0 or 1) |
| 1 | 1 | overtone_n | uint8 | Overtone number (1,3,5,7,9,11) |
| 2 | 4 | delta_f | float32 | Frequency shift (Hz) |
| 6 | 4 | dissipation | float32 | Dissipation factor D |
| 10 | 4 | delta_d | float32 | Dissipation shift ΔD |
| 14 | 4 | temperature | float32 | Crystal temperature (°C) |
| 18 | 4 | sauerbrey_mass | float32 | Sauerbrey areal mass (ng/cm²) |
| 22 | 4 | timestamp | uint32 | Milliseconds since boot |

### Sweep Packet (CMD 0x02, 56 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0-23 | 6×4 | delta_f[6] | Δf for each overtone (Hz) |
| 24-47 | 6×4 | delta_d[6] | ΔD for each overtone |
| 48 | 4 | temperature | Crystal temperature (°C) |
| 52 | 4 | timestamp | ms since boot |

### Voigt Packet (CMD 0x03, 20 bytes)

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | thickness_nm | float32 | Film thickness |
| 4 | 4 | viscosity_pa_s | float32 | Film viscosity |
| 8 | 4 | shear_mod_pa | float32 | Film shear modulus |
| 12 | 1 | converged | uint8 | Fit converged? |
| 13 | 1 | iterations | uint8 | LM iterations |
| 14 | 4 | residual | uint32 | Fit residual |

## Python API

### Connecting

```python
from bleak import BleakClient

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHAR_UUID  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
RX_CHAR_UUID  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

async with BleakClient("QCM Halo") as client:
    await client.start_notify(RX_CHAR_UUID, handler)
```

### Sending Commands

```python
def make_frame(cmd, payload=b''):
    frame = bytes([0xA5, 0x5A, cmd, len(payload)]) + payload
    crc = crc8(frame[2:])
    return frame + bytes([crc])

# Start measurement on channel 0, 3rd overtone
await client.write_gatt_char(TX_CHAR_UUID,
    make_frame(0x81, bytes([0, 1, 0])))

# Set temperature to 25°C
import struct
await client.write_gatt_char(TX_CHAR_UUID,
    make_frame(0x85, struct.pack('<f', 25.0)))
```

## SD Card Log Format

### CSV Format (single measurements)

```
timestamp_ms,channel,overtone_n,frequency,delta_f,dissipation,delta_d,temperature,sauerbrey_mass,sauerbrey_thickness
12345,1,3,5000123.4,-15.3,2.5e-5,1.2e-5,25.02,271.2,2.71
```

### CSV Format (overtone sweeps)

```
# Sweep t=12345 T=25.02
1st,5000123.4,-15.3,1.2e-5
3rd,15000370.2,-46.1,3.5e-5
5th,25000617.1,-76.8,5.8e-5
7th,35000864.3,-107.5,8.1e-5
9th,45001111.5,-138.2,1.04e-4
11th,55001358.8,-168.9,1.27e-4
```

## Firmware API (C)

### Key Functions

```c
/* Measure frequency at a specific overtone */
float qcm_measure_frequency(uint8_t channel, uint32_t gate_ms);

/* Full QCM-D measurement (freq + dissipation + Sauerbrey) */
qcm_result_t qcm_measure(uint8_t channel, uint8_t overtone_idx,
                         float temperature, int do_ringdown, int do_voigt);

/* Multi-overtone sweep */
int overtone_sweep(uint8_t channel, float temperature, overtone_sweep_t *sweep);

/* Voigt viscoelastic model fitting */
voigt_params_t voigt_fit(const float *f_n, const float *df_n, const float *dd_n,
                         uint8_t n_ov, const float *rho_l_eta_l,
                         float f0, float rho_q, float mu_q);

/* Sauerbrey mass calculation */
float sauerbrey_mass(float delta_f_hz, float f0_hz, float area_cm2);

/* Temperature control */
float temperature_pid_step(float target);
void temperature_set_target(float target_c);

/* Liquid handling */
void pump_set_rate(float ml_per_min);
void valve_set_position(uint8_t pos);
```