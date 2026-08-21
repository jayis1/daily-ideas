# Dent Scope — API Reference

## BLE GATT Interface

### Service: Dent Scope (UUID 0x8801)

| Characteristic | UUID | Properties | Description |
|---|---|---|---|
| Data | 0x8802 | Notify | Live P-h data points (12 bytes: force_mN:f32, depth_um:f32, t_ms:u32) |
| Result | 0x8803 | Read | Latest test result (JSON string) |
| Command | 0x8804 | Write | Send commands to device |

### Data Point Format (12 bytes)

| Offset | Size | Field | Type |
|---|---|---|---|
| 0 | 4 | force_mN | float32 LE |
| 4 | 4 | depth_um | float32 LE |
| 8 | 4 | t_ms | uint32 LE (ms since test start) |

### Result Format (JSON string, Read)

```json
{
  "HV": 126.5,
  "E_GPa": 200.1,
  "eta": 0.03,
  "Pmax_mN": 5000,
  "material": 8
}
```

Material index mapping: see `docs/measurement_theory.md` for the full 30-material table.

### Commands (Write)

| Byte | Command |
|---|---|
| 0xAA 0x55 0x10 0x00 0x00 [crc16] | START test |
| 0xAA 0x55 0x11 0x00 0x00 [crc16] | STOP / retract |

## Wi-Fi Captive Portal

Connect to Wi-Fi AP **DentScope** (password: `12345678`).

- **GET /** — Web dashboard with live P-h plot via WebSocket
- **GET /result** — Latest test result (JSON)

## UART Protocol (STM32 ↔ ESP32-C3)

Binary frames, 115200 baud, 8N1.

| Frame | Format |
|---|---|
| Header | 0xAA 0x55 |
| Type | 1 byte |
| Length | 2 bytes LE |
| Payload | Length bytes |
| CRC16 | 2 bytes LE (CRC-16/ARC) |

| Type | Direction | Payload |
|---|---|---|
| 0x01 | STM32→ESP32 | Data point (12 bytes) |
| 0x02 | STM32→ESP32 | Result (21 bytes: HV:f32, E:f32, eta:f32, Pmax:f32, material:i8) |
| 0x03 | STM32→ESP32 | Status (state:u8, force:f32, depth:f32, tilt:f32) |
| 0x10 | ESP32→STM32 | START command |
| 0x11 | ESP32→STM32 | STOP command |

## SD Card Log Format

CSV files: `indent_XXXX.csv`

```
t_ms,force_mN,depth_um,state
0,0.0,0.000,1
10,51.2,0.035,2
20,102.4,0.071,2
...
```

State codes: 0=IDLE, 1=APPROACHING, 2=LOADING, 3=HOLDING, 4=UNLOADING, 5=RETRACTING, 6=ALARM

## Python Streaming API

```python
from dent_scope import DentScope

ds = DentScope.connect_ble()  # or connect_wifi("192.168.4.1")

ds.start_test(target_force_N=10, loading_rate=1.0, hold_s=5)

for point in ds.stream():
    print(f"t={point.t_ms}ms  P={point.force_mN:.1f}mN  h={point.depth_um:.3f}um")

result = ds.get_result()
print(f"HV={result.HV:.1f}  E={result.E_GPa:.1f}GPa  η={result.eta:.2f}")
print(f"Material: {result.material_name}")
```