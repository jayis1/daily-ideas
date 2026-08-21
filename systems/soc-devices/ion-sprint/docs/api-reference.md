# API Reference — Ion Sprint

## BLE GATT Service

The ESP32-C3 BLE bridge exposes a custom GATT service with the
following characteristics:

| UUID | Name | Type | Direction | Description |
|------|------|------|-----------|-------------|
| `0000fe21-...` | Ion Sprint Service | Service | — | Main service |
| `0000fe22-...` | Electropherogram | Notify | Device→Phone | Live electropherogram data |
| `0000fe23-...` | Results | Read/Notify | Device→Phone | Peak table (final results) |
| `0000fe24-...` | Command | Write | Phone→Device | Control commands |
| `0000fe25-...` | Status | Read/Notify | Device→Phone | Device status (state, HV, temp) |
| `0000fe26-...` | Settings | Read/Write | Bidirectional | Run parameters |
| `0000fe27-...` | Error | Notify | Device→Phone | Error messages |

## Packet Protocol

All BLE characteristics use a binary framed packet format:

```
[START 0xAA] [TYPE] [LEN_H] [LEN_L] [PAYLOAD...] [CRC8]
```

### Packet Types

#### 0x01 — Electropherogram Chunk (PKT_EPH)
Live electropherogram data, sent at 10 Hz during a run.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | hv_kv | float32 — measured HV voltage (kV) |
| 4 | 4 | current_ua | float32 — measured HV current (µA) |
| 8 | 2 | sample_count | uint16 — number of samples in this chunk |
| 10 | N×4 | samples | float32[] — electropherogram data points |

### 0x02 — Results (PKT_RESULTS)
Final peak table, sent at run completion.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | run_id | uint16 — run identifier |
| 2 | 1 | count | uint8 — number of results |
| 3 | 25×N | results | ion_result_t[] — see below |

**ion_result_t** (25 bytes each):
| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | ion_id | uint8 — library index (0–39) |
| 1 | 12 | ion_name | char[12] — ion name string |
| 13 | 4 | migration_time | float32 — seconds from injection |
| 17 | 4 | area | float32 — peak area (arbitrary units) |
| 21 | 4 | concentration_mM | float32 — concentration (mM) |

### 0x03 — Error (PKT_ERROR)
Error/fault message.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | msg_len | uint8 — message length |
| 1 | N | message | char[] — error message |
| 1+N | 4 | current_ua | float32 — HV current at fault |
| 5+N | 4 | voltage_kv | float32 — HV voltage at fault |

### 0x04 — Command (PKT_COMMAND, phone→device)
Commands sent from the phone app to the device.

| Type | Value | Description |
|------|-------|-------------|
| 0x01 | START | Start a run |
| 0x02 | ABORT | Abort current run |
| 0x03 | SET_HV | Set HV voltage (followed by float32 kV) |
| 0x04 | SET_BGE | Set BGE recipe (followed by uint8 index) |
| 0x05 | SET_INJ | Set injection mode (0=EK, 1=HD) |
| 0x06 | CALIBRATE | Enter calibration mode |
| 0x07 | FLUSH | Flush capillary |

## SD Card File Format

### RUN_xxxx.CSV
```
Run,0042
BGE,0
HV_setpoint_kV,20.0
HV_measured_kV,19.8
Temp_C,24.5
Eph_samples,60000

Ion,t_m(s),Area,Height,Conc(mM)
K+,68.2,1.234,0.0567,0.98
Na+,72.1,0.876,0.0456,0.85
Cl-,205.3,1.567,0.0678,1.12
```

### RUN_xxxx.BIN
Raw electropherogram: `eph_count × 4` bytes (float32 array, 100 Hz).

## Python Helper Scripts

### `ionsprint_app.py`
BLE companion app: connects via BLE, plots live electropherogram,
displays peak table, logs to CSV.

```
python3 ionsprint_app.py [--mac AA:BB:CC:DD:EE:FF]
```

### `calibrate.py`
Calibration script: runs a series of standards via BLE commands,
records peak areas, and computes response factors.

```
python3 calibrate.py --standards standards.json --mac AA:BB:CC:DD:EE:FF
```

## Wi-Fi Streaming Mode

The ESP32-C3 can also serve a WebSocket endpoint for PC-based plotting:

1. Connect to Ion Sprint Wi-Fi AP (password: `ionsprint`)
2. Open browser to `http://192.168.4.1`
3. Web page shows live electropherogram + peak table

Or use the Python script:
```
python3 ionsprint_app.py --wifi 192.168.4.1
```