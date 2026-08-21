# Refracto Bead — API Reference

## BLE GATT Service

### Service UUID: `0xFFC0` (RefractoBead)

| Characteristic | UUID | Access | Description |
|----------------|------|--------|-------------|
| Command | 0xFFC1 | Write | Measurement command (uint8) |
| RI Results | 0xFFC2 | Read/Notify | Refractive index data (32 bytes) |
| Derived Results | 0xFFC3 | Read/Notify | Brix/SG/ABV/FP (20 bytes) |
| Compound Match | 0xFFC4 | Read/Notify | k-NN match details (48 bytes) |
| Raw Waveform | 0xFFC5 | Read | 256-pixel CCD data (256 bytes) |
| Status | 0xFFC6 | Read/Notify | Device status (1 byte) |
| Battery | 0xFFC7 | Read | Battery level (1 byte) |
| Library Entry | 0xFFC8 | Read/Write | Compound library entry (32 bytes) |

### RI Results (0xFFC2) — 32 bytes

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | n_D | float32 | RI at 589 nm |
| 4 | 4 | n_F | float32 | RI at 470 nm |
| 8 | 4 | n_C | float32 | RI at 655 nm |
| 12 | 4 | abbe_vd | float32 | Abbe number V_D |
| 16 | 4 | t_prism | float32 | Prism temperature (°C) |
| 20 | 4 | dispersion | float32 | n_F − n_C |
| 24 | 8 | reserved | — | Padding |

### Derived Results (0xFFC3) — 20 bytes

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | brix | float32 | Sugar content (°Bx) |
| 4 | 4 | sg | float32 | Specific gravity |
| 8 | 4 | abv | float32 | Alcohol by volume (%) |
| 12 | 4 | freeze_point | float32 | Coolant freeze point (°C) |
| 16 | 1 | compound_id | uint8 | Library index (0–59, 255=unknown) |
| 17 | 3 | reserved | — | Padding |

### Compound Match (0xFFC4) — 48 bytes

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 16 | name | char[16] | Compound name (null-terminated) |
| 16 | 4 | n_D | float32 | Library n_D value |
| 20 | 4 | abbe_vd | float32 | Library V_D value |
| 24 | 4 | confidence | float32 | Match confidence (0.0–1.0) |
| 28 | 20 | reserved | — | (3-match slots) |

### Command (0xFFC1) — Write

| Value | Action |
|-------|--------|
| 1 | Start measurement |
| 2 | Calibrate with water |
| 3 | Calibrate with RI standard oil |
| 4 | Enter Wi-Fi config mode |
| 5 | Power down |

### Library Entry (0xFFC8) — Read/Write — 32 bytes

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 1 | id | uint8 | Library index (0–59) |
| 1 | 16 | name | char[16] | Compound name |
| 17 | 4 | n_D | float32 | Reference RI |
| 21 | 4 | abbe_vd | float32 | Reference Abbe number |
| 25 | 4 | dn_dt | float32 | Temperature coefficient |
| 29 | 3 | reserved | — | Padding |

---

## Wi-Fi HTTP REST API

Base URL: `http://<device-ip>/api/`

### `GET /api/status`
Returns device status.

**Response:**
```json
{
  "status": "idle",
  "battery": 75,
  "wifi_connected": true,
  "last_measurement": "2026-07-17T14:32:00Z"
}
```

### `POST /api/measure`
Triggers a measurement.

**Request:**
```json
{ "mode": "ri" }
```

**Response:**
```json
{ "status": "measuring" }
```

### `GET /api/results`
Returns the last measurement results.

**Response:**
```json
{
  "n_D": 1.4657,
  "n_F": 1.4756,
  "n_C": 1.4650,
  "dispersion": 0.0106,
  "abbe_vd": 47.1,
  "brix": 42.3,
  "sg": 1.034,
  "abv": 0.0,
  "freeze_point": -12.5,
  "t_prism": 20.1,
  "t_ambient": 22.3,
  "compound": "Sunflower oil",
  "compound_id": 13,
  "confidence": 0.98
}
```

### `GET /api/library`
Returns the full compound library.

**Response:**
```json
{
  "size": 60,
  "entries": [
    { "id": 0, "name": "Water", "n_D": 1.3330, "abbe_vd": 55.8, "dn_dt": -0.00008 },
    { "id": 1, "name": "Ethanol", "n_D": 1.3611, "abbe_vd": 59.0, "dn_dt": -0.0004 }
  ]
}
```

### `POST /api/library`
Adds or updates a custom library entry.

**Request:**
```json
{
  "name": "Custom Oil",
  "n_D": 1.4700,
  "abbe_vd": 46.5,
  "dn_dt": -0.00038
}
```

### `GET /api/waveform?wl=589`
Returns raw CCD waveform (256 pixels).

**Response:** Binary, 256 × uint8 (0–255)

### `POST /api/calibrate`
Initiates calibration with a reference standard.

**Request:**
```json
{
  "standard": "water",
  "expected_nD": 1.3330
}
```

---

## UART Protocol (STM32 ↔ ESP32-C3)

### Frame Format

```
[0xAA][0x55][cmd][len_hi][len_lo][payload...][crc8]
```

- **Sync bytes**: 0xAA 0x55
- **cmd**: Command byte (0x01 = result, 0x02 = status, 0x03 = cal)
- **len**: 16-bit big-endian payload length
- **payload**: Command-specific data
- **crc8**: CRC-8 (polynomial 0x07, init 0x00) over payload only

### Baud Rate: 460800

---

*Refracto Bead API Reference — SoC Device Inventions*