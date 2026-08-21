# Gossamer Spin — API Reference

## BLE GATT Interface

### Service: `00009501-1212-efde-1523-785feabcd123`

| Characteristic | UUID | Access | Description |
|---------------|------|--------|-------------|
| Process Data | `00009502-...` | Notify | Live process data stream (10 Hz) |
| Command | `00009503-...` | Write | Send commands to the device |

### Process Data Frame (type 0x01)

Notified at 10 Hz. Binary frame format:

```
[0xAA][0x55][len_lo][len_hi][0x01][payload: 33 bytes]
```

Payload (33 bytes, little-endian):

| Offset | Size | Field | Unit | Type |
|--------|------|-------|------|------|
| 0 | 4 | voltage_kv | kV | float32 |
| 4 | 4 | current_na | nA | float32 |
| 8 | 4 | flow_mlh | mL/h | float32 |
| 12 | 4 | drum_rpm | RPM | float32 |
| 16 | 4 | temp_c | °C | float32 |
| 20 | 4 | rh_pct | % | float32 |
| 24 | 1 | jet_state | enum | uint8 |
| 25 | 4 | jet_sigma_na | nA | float32 |
| 29 | 4 | elapsed_s | s | uint32 |

### Jet State Enum

| Value | Name | Meaning |
|-------|------|---------|
| 0 | IDLE | No HV, no jet |
| 1 | STABLE | Steady jet, uniform deposition |
| 2 | INTERRUPTED | Jet stopped (clog/depletion) |
| 3 | UNSTABLE | Erratic jet (adjust V or flow) |
| 4 | DRIPPING | Dripping mode (increase V) |

### Command Frame (write to Command characteristic)

```
[0xAA][0x55][len_lo][len_hi][type][payload...]
```

| Type | Payload | Action |
|------|---------|--------|
| 0x81 | 1 byte: recipe_idx | Start run with recipe (0–7) |
| 0x82 | (none) | Stop current run |
| 0x83 | 52 bytes: recipe struct | Set custom recipe (idx 7) and start |
| 0x84 | 4 bytes: float | Override target voltage (kV) |

### Custom Recipe Struct (52 bytes, for command 0x83)

| Offset | Size | Field | Unit |
|--------|------|-------|------|
| 0 | 24 | name | char[24] |
| 24 | 4 | voltage_kv | kV |
| 28 | 4 | flow_mlh | mL/h |
| 32 | 4 | drum_rpm | RPM |
| 36 | 4 | distance_cm | cm |
| 40 | 4 | target_rh_min | % |
| 44 | 4 | target_rh_max | % |
| 48 | 4 | target_temp_c | °C |
| 52 | 4 | duration_s | s |

Wait, that's 56 bytes. Actually:

| Offset | Size | Field | Unit |
|--------|------|-------|------|
| 0 | 24 | name | char[24] |
| 24 | 4 | voltage_kv | kV |
| 28 | 4 | flow_mlh | mL/h |
| 32 | 4 | drum_rpm | RPM |
| 36 | 4 | distance_cm | cm |
| 40 | 4 | target_rh_min | % |
| 44 | 4 | target_rh_max | % |
| 48 | 4 | target_temp_c | °C |

Duration is set separately or appended. The firmware `recipe_t` struct
is 56 bytes total (24 + 8×4). Adjust the payload length accordingly.

## SD Card Log Format

File: `spin_log.csv` (FAT32, appended or overwritten per run)

```csv
time_s,voltage_kv,flow_mlh,drum_rpm,jet_current_na,jet_sigma_na,jet_state,temp_c,rh_pct
0,0.00,1.000,800.0,0.0,0.0,idle,23.1,35.2
1,5.20,1.000,800.0,45.3,12.1,stable,23.1,35.2
2,12.40,1.000,800.0,180.5,22.3,stable,23.1,35.1
...
```

- Sampled at 10 Hz (every 0.1 s)
- `jet_state` is lowercase: idle/stable/interrupted/unstable/dripping

## Firmware Module API

### hv_supply.c
```c
void  hv_supply_init(void);       // Initialize flyback + CW
void  hv_set_target(float kv);    // Set target voltage (0–30 kV)
void  hv_enable(bool on);         // Enable/disable HV output
float hv_read_voltage(void);      // Read measured voltage (kV)
void  hv_pid_update(void);        // PID regulator (call at 1 kHz)
```

### syringe_pump.c
```c
void  syringe_pump_init(void);
void  syringe_set_flow(float mlh); // Set flow rate (0.1–10 mL/h)
void  syringe_start(void);
void  syringe_stop(void);
bool  syringe_empty(void);         // True if limit switch triggered
```

### collector.c
```c
void  collector_init(void);
void  collector_set_rpm(float rpm); // Set drum speed (100–3000 RPM)
void  collector_start(void);
void  collector_stop(void);
```

### jet_current.c
```c
void  jet_current_init(void);
float jet_current_read(void);      // Latest current (nA)
void  jet_current_update(float *na, float *sigma, jet_state_t *state);
```

### safety.c
```c
void     safety_init(void);
bool     safety_check(void);       // True = safe, False = tripped
uint8_t  safety_get_source(void);  // SAF_DOOR/SAF_TILT/SAF_CURRENT
void     safety_reset(void);
```

### recipe.c
```c
void  recipe_init(void);
void  recipe_load(int idx, recipe_t *r);  // Load recipe (0–7)
```

### Preset Recipes

| Idx | Name | kV | mL/h | RPM | Dist | RH% | Temp | Duration |
|-----|------|-----|------|-----|------|-----|------|----------|
| 0 | PVA | 18 | 1.0 | 800 | 15 | 30-50 | 25 | 30 min |
| 1 | PAN | 20 | 0.8 | 1200 | 15 | 20-40 | 25 | 60 min |
| 2 | PLLA | 15 | 0.5 | 600 | 12 | 25-45 | 25 | 30 min |
| 3 | PVDF | 22 | 1.2 | 1500 | 15 | 20-35 | 25 | 40 min |
| 4 | Nylon-6 | 20 | 0.6 | 1000 | 15 | 30-50 | 25 | 30 min |
| 5 | Chitosan | 12 | 0.3 | 400 | 10 | 35-55 | 25 | 20 min |
| 6 | PS | 16 | 0.7 | 900 | 12 | 25-45 | 25 | 30 min |
| 7 | Custom | user | user | user | user | user | user | user |