# Fluor Cast — API Reference

## UART Binary Protocol

Communication between the STM32G474 and ESP32-C3 uses a binary framed protocol at 921600 baud (8N1).

### Frame Format

```
[SOF: 0xAA][LEN: 2 bytes LE][CMD: 1 byte][PAYLOAD: LEN bytes][CRC16: 2 bytes LE][EOF: 0x55]
```

- **SOF**: Start of frame (0xAA)
- **LEN**: Payload length (little-endian, max 4096)
- **CMD**: Command byte
- **PAYLOAD**: Variable length data
- **CRC16**: CRC16-CCITT (polynomial 0x1021, init 0xFFFF) over CMD + PAYLOAD
- **EOF**: End of frame (0x55)

### Commands: STM32 → ESP32

| CMD | Name | Payload | Description |
|---|---|---|---|
| 0x01 | EEM_DATA | EEM matrix chunks | Full EEM data (sent in 512-byte chunks) |
| 0x02 | RESULT | Classification result | Top-5 k-NN matches with confidences |
| 0x03 | STATUS | state(1), battery(1), temp(4f) | Device status update |
| 0x04 | LOG_ENTRY | CSV line (string) | Log entry for relay to phone |
| 0x05 | CALIBRATION | Calibration coefficients | Wavelength + intensity calibration |

### Commands: ESP32 → STM32

| CMD | Name | Payload | Description |
|---|---|---|---|
| 0x10 | START_SCAN | None | Trigger EEM acquisition |
| 0x11 | SET_PARAMS | acq_params_t (binary) | Set acquisition parameters |
| 0x12 | GET_STATUS | None | Request status update |
| 0x13 | CALIBRATE | None | Start calibration mode |
| 0x14 | SET_LIBRARY | library_entry_t | Update library entry |
| 0x15 | SET_TIME | uint32 timestamp | Sync RTC |

### EEM_DATA Payload Format

EEM data is sent in multiple chunks:

1. **Metadata** (12 bytes): timestamp(4u), temp_c(4f), duration_ms(4u)
2. **Matrix** (4096 bytes): 8×256 array of uint16, sent in 8× 512-byte chunks
3. **Features** (192 bytes): 48 float32 values

### RESULT Payload Format

| Offset | Size | Field | Type |
|---|---|---|---|
| 0 | 5 | indices[5] | uint8[5] |
| 5 | 20 | distances[5] | float32[5] |
| 25 | 20 | confidences[5] | float32[5] |
| 45 | 1 | top_match | uint8 |
| 46 | 4 | top_confidence | float32 |
| 50 | 4 | estimated_conc | float32 |

### acq_params_t (SET_PARAMS payload)

| Offset | Size | Field | Type | Default |
|---|---|---|---|---|
| 0 | 2 | integration_ms | uint16 | 500 |
| 2 | 1 | hdr_mode | uint8 | 1 |
| 3 | 1 | scan_mask | uint8 | 0xFF (all) |
| 4 | 1 | auto_expose | uint8 | 1 |
| 5 | 2 | target_counts | uint16 | 3000 |
| 7 | 4 | led_current_ma | float32 | 50.0 |
| 11 | 1 | classify | uint8 | 1 |
| 12 | 1 | log_to_sd | uint8 | 1 |
| 13 | 1 | stream_ble | uint8 | 1 |

---

## BLE Service (ESP32-C3)

### Service UUID: `0000fc01-0000-1000-8000-00805f9b34fb`

| Characteristic | UUID | Properties | Description |
|---|---|---|---|
| Command | `...fc02...` | Write | Send commands to device |
| EEM Stream | `...fc03...` | Notify | EEM data notifications |
| Result | `...fc04...` | Notify | Classification result |
| Status | `...fc05...` | Read/Notify | Device status |
| Library | `...fc06...` | Read/Write | Compound library |

---

## Wi-Fi Web Dashboard

When connected to Wi-Fi, the ESP32-C3 serves a web dashboard at `http://fluorcast.local` (mDNS) or the device's IP address.

### Endpoints

| Path | Method | Description |
|---|---|---|
| `/` | GET | Web dashboard (single-page app) |
| `/api/status` | GET | JSON device status |
| `/api/scan` | POST | Start EEM acquisition |
| `/api/eem` | GET | Latest EEM data (JSON) |
| `/api/result` | GET | Latest classification result |
| `/api/library` | GET | Full compound library |
| `/api/library/{id}` | PUT | Update library entry |
| `/api/logs` | GET | List log files on SD |
| `/api/logs/{file}` | GET | Download log file |
| `/api/calibrate` | POST | Start calibration |
| `/api/params` | PUT | Set acquisition parameters |

---

## Python Script APIs

### calibrate.py
```
python3 calibrate.py [--port /dev/ttyUSB0] [--baud 921600] [--output calibration.json]
```

### live_view.py
```
python3 live_view.py [--port /dev/ttyUSB0] [--mac AA:BB:CC:DD:EE:FF]
```

### library_manager.py
```
python3 library_manager.py list
python3 library_manager.py add --name "Compound" --ex 380 --em 450
python3 library_manager.py remove 23
python3 library_manager.py export library.json
python3 library_manager.py import library.json
```

### export_eem.py
```
python3 export_eem.py input_dir/ output_dir/ --format csv|mat|json|all --plot
```

### stern_volmer.py
```
python3 stern_volmer.py --input quench_data.csv
python3 stern_volmer.py --F0 10000 --Ksv 200 --Q 0.005
```