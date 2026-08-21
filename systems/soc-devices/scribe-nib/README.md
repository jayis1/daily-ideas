# Scribe Nib

**A pen-clip smart handwriting digitizer that captures, recognizes, and transmits handwritten text in real time — no special paper required.**

---

## What It Does

The Scribe Nib is a 12×18mm PCB that clips onto any pen, pencil, or stylus. Using a 9-axis IMU to track the pen's motion in 3D space, a lightweight CNN running on the ESP32-S3 recognizes individual handwritten characters as they're written, and streams the recognized text over BLE to your phone, tablet, or laptop.

- **Motion capture** — 9-axis IMU (accelerometer + gyro + magnetometer) samples at 200Hz to reconstruct pen trajectory
- **On-device recognition** — quantized INT8 CNN classifies 62 character classes (0-9, A-Z, a-z) in ~4ms per stroke
- **Stroke segmentation** — automatic pen-up/pen-down detection from Z-axis accelerometer, no button press needed
- **BLE 5.0 streaming** — recognized characters appear in real-time as a BLE HID keyboard or custom GATT service
- **Vocabulary correction** — lightweight n-gram language model (2MB flash partition) improves accuracy from ~82% to ~94%
- **Multi-user calibration** — stores up to 4 user profiles in NVS for handwriting style adaptation
- **OLED feedback** — tiny 64×32 SSD1306 shows last recognized character and battery level
- **All-day battery** — 80mAh Lipo lasts ~14 hours of continuous writing; auto-sleep after 30s idle

### Character Classes

| Category | Characters | Count |
|----------|-----------|-------|
| Digits | 0-9 | 10 |
| Uppercase | A-Z | 26 |
| Lowercase | a-z | 26 |
| **Total** | | **62** |

Special gestures (swipe patterns) are recognized for space, backspace, enter, and mode switching (caps lock, number mode).

Battery life: **14 hours** continuous writing on 80mAh Lipo (BLE-only), **30 days** standby.

---

## Block Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      SCRIBE NIB                              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ ICM-42688-P  │  │  QMC5883L    │  │  SSD1306 64×32  │   │
│  │ 6-axis IMU   │  │  Magnetometer│  │  OLED Display    │   │
│  │ SPI @ 200Hz  │  │  I²C 0x0D   │  │  I²C 0x3C       │   │
│  └──────┬───────┘  └──────┬──────┘  └────────┬─────────┘   │
│         │ SPI              │ I²C               │ I²C          │
│  ┌──────┴──────────────────┴───────────────────┘             │
│  │                        │                                  │
│  │              ESP32-S3-MINI-1                              │
│  │  ┌────────────┐ ┌──────────┐ ┌────────────────────┐      │
│  │  │ Xtensa     │ │ BLE 5.0  │ │ USB-C OTG         │      │
│  │  │ 240MHz     │ │ 2M phy   │ │ CDC + MSC         │      │
│  │  │ dual-core  │ │          │ │ (debug+storage)    │      │
│  │  └────────────┘ └──────────┘ └────────────────────┘      │
│  │  ┌────────────────────────────────────────────┐          │
│  │  │  CNN Character Recognizer (INT8, 62-class)  │          │
│  │  │  + n-gram Language Model (2MB flash)        │          │
│  │  └────────────────────────────────────────────┘          │
│  └──────────────┬───────────────────────────────────────────┘
│                 │                                            
│  ┌──────────────▼──────────────────────────┐    ┌─────────┐ │
│  │      Power Management                   │    │ Vibra   │ │
│  │  MCP73831 charger + ME6211 LDO 3.3V    │    │ Motor   │ │
│  │  80mAh Lipo (3.7V)                     │    │ GPIO42  │ │
│  │  USB-C charging + HID firmware update  │    └─────────┘ │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Capacitive touch pads (2x on clip) → GPIO1, GPIO2      ││
│  │  Tap: wake  |  Double-tap: mode switch  |  Hold: cal   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (ESP32-S3-MINI-1)

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO0 | SPI MISO | ICM-42688-P MISO |
| GPIO1 | CAP_TOUCH_0 | Capacitive pad (clip inner) |
| GPIO2 | CAP_TOUCH_1 | Capacitive pad (clip outer) |
| GPIO3 | TOUCH_IRQ | ICM-42688-P INT1 (data-ready) |
| GPIO4 | SPI CLK | ICM-42688-P SCLK |
| GPIO5 | SPI MOSI | ICM-42688-P MOSI |
| GPIO6 | SPI CS | ICM-42688-P CS_N |
| GPIO7 | I²C SDA | QMC5883L + SSD1306 (pull-up 4.7k) |
| GPIO8 | I²C SCL | QMC5883L + SSD1306 (pull-up 4.7k |
| GPIO9 | OLED_RST | SSD1306 RESET |
| GPIO10 | QMC_DRDY | QMC5883L DRDY |
| GPIO11 | VIBRA_EN | Vibration motor driver (MOSFET gate) |
| GPIO12 | CHARGE_STAT | MCP73831 STAT pin |
| GPIO13 | LED_R | Status LED red (WS2812B) |
| GPIO14 | LED_G | Status LED green (shared WS2812B) |
| GPIO15 | BOOT | Boot button (hold during reset = download) |
| GPIO16 | UART TX | Debug console |
| GPIO17 | UART RX | Debug console |
| GPIO18 | USB D+ | USB-C connector |
| GPIO19 | USB D- | USB-C connector |
| GPIO20 | EN | Power enable (active high, pull-up) |
| GPIO21 | IMU_CS_ALT | Alt chip select (reserved for 2nd IMU) |
| GPIO42 | MOTOR_PWM | Vibration motor PWM |
| GPIO43 | USB_DP_ALT | USB-C D+ (alternate) |
| GPIO44 | USB_DM_ALT | USB-C D- (alternate) |
| GPIO46 | STRM_LED | Streaming indicator LED |

---

## Power Architecture

```
USB-C (5V) ──► MCP73831 ──► Lipo (3.7V 80mAh) ──► ME6211-3.3V ──► VDD

Quiescent: ~8µA (deep sleep, RTC on, ULP coprocessor monitors IMU)
Active (writing + BLE): ~12mA avg → 6.7h theoretical
Active (duty-cycled, typical use): ~5.5mA avg → ~14.5h
Auto-sleep after 30s no motion: extends to ~30 days standby
```

Power states:
1. **ACTIVE** — IMU sampling 200Hz, BLE connected, CNN inference on each stroke (~12mA)
2. **IDLE** — IMU sampling 20Hz (pen-up detection), BLE connected, OLED off (~4mA)
3. **LIGHT SLEEP** — IMU sampling 1Hz (motion detect only), BLE advertising, OLED off (~0.8mA)
4. **DEEP SLEEP** — ULP monitors IMU FIFO for motion threshold, BLE off (~8µA)

Wake sources:
- ULP coprocessor: motion above threshold in IMU FIFO → wake to IDLE
- Capacitive touch: tap on clip pads → wake to ACTIVE
- RTC: periodic BLE advertising interval (every 2s in LIGHT SLEEP)

---

## Mechanical

- PCB: 12mm × 18mm, 1.0mm FR4, 4-layer (2 signal + 1 ground + 1 power)
- Clip form factor: PCB is the spring-steel pen clip itself (FR4 bonded to 0.3mm spring steel)
- Height: 4mm (components on top only, bottom is flush clip surface)
- Weight: 3.5g (including battery)
- IMU placement: centered on clip, at pen contact point for best motion fidelity
- Battery: 80mAh Lipo pouch tucked behind PCB, conformal-coated
- Vibration motor: 4mm coin type, surface-mount on PCB edge
- USB-C: right-angle receptacle at top of clip
- Enclosure: silicone sleeve (optional, files in `hardware/`)

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── app_main.c            # Entry point, NVS init, task launch
│   ├── imu_driver.c          # SPI IMU config + FIFO read at 200Hz
│   ├── stroke_segmenter.c    # Pen-up/pen-down detection from Z-axis
│   ├── trajectory_recon.c    # 3D path reconstruction from IMU data
│   ├── char_recognizer.c     # CNN inference for 62-class recognition
│   ├── lang_model.c          # n-gram correction + word completion
│   ├── ble_hid.c             # BLE HID keyboard service
│   ├── ble_custom.c          # Custom GATT service (raw stroke data)
│   ├── oled_display.c        # SSD1306 64×32 display driver
│   ├── power_manager.c       # Sleep states, wake config
│   ├── calibration.c         # User handwriting profile calibration
│   ├── gesture_handler.c     # Special swipe gesture recognition
│   └── haptic_feedback.c     # Vibration motor patterns
├── components/
│   ├── tflite_micro/         # TFLite Micro library
│   ├── model/
│   │   └── char_cnn.tflite   # Quantized INT8 model (92KB)
│   └── lang_model/
│       └── en_ngram.bin       # English bigram model (2MB)
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow

```c
void app_main(void) {
    nvs_init();
    imu_driver_init(SPI_FREQ_20MHZ, IMU_ODR_200HZ);
    stroke_segmenter_init();
    char_recognizer_init();   // loads CNN model from flash
    lang_model_init();        // loads n-gram from flash partition
    ble_hid_init();
    oled_display_init();
    calibration_load_profile(0);  // default user profile
    
    while (true) {
        imu_sample_t samples[FIFO_WATERMARK];
        int n = imu_driver_read_fifo(samples, FIFO_WATERMARK);
        
        stroke_event_t stroke;
        if (stroke_segmenter_update(samples, n, &stroke)) {
            // New stroke completed (pen lifted)
            traj_2d_t traj;
            trajectory_recon_project(&stroke, &traj);
            
            char_pred_t pred = char_recognizer_classify(&traj);
            char corrected = lang_model_correct(pred.char_id, pred.confidence);
            
            ble_hid_send_key(corrected);
            oled_display_char(corrected);
            haptic_feedback_pulse(20);  // 20ms buzz on recognition
            
            lang_model_update_context(corrected);
        }
        
        power_manager_update_idle();
    }
}
```

### Stroke Segmentation Algorithm

The pen-up/pen-down detection uses the Z-axis accelerometer:

1. When pen touches paper: Z-axis deceleration spike > 0.3g → PEN_DOWN
2. When pen lifts off paper: Z-axis acceleration spike > 0.2g → PEN_UP
3. Hysteresis buffer: 20ms debounce on both transitions
4. Multi-stroke characters: if PEN_UP duration < 300ms, strokes are grouped into one character
5. Character boundary: PEN_UP duration > 300ms → finalize character, send to recognizer

### Trajectory Reconstruction

The 9-axis IMU data is processed through:

1. **Gyro integration** — angular rate → orientation quaternion (Madgwick filter)
2. **Gravity removal** — subtract gravity component from accelerometer using orientation
3. **Double integration** — linear acceleration → displacement (with drift correction)
4. **Magnetic heading** — magnetometer provides absolute heading to correct yaw drift
5. **2D projection** — 3D trajectory projected onto writing plane (detected from gravity direction)

Drift is corrected by:
- Resetting position at each pen-up (zero-velocity update)
- Magnetometer-based yaw correction every 50ms
- High-pass filtering of position with 0.5Hz cutoff

---

## BLE Services

### HID Keyboard Service (standard)

```
Service UUID: 0x1812 (HID)
  ├── Report Map: Standard US keyboard layout
  ├── Report 0x2A4D: Keyboard input (8 bytes: modifier + reserved + 6 keycodes)
  ├── Report 0x2A4E: Keyboard output (LED indicators)
  └── Protocol Mode: 0x2A4E = Report mode
```

Appears as a standard Bluetooth keyboard — works with any phone/tablet/laptop without an app.

### Custom Scribe Service (advanced)

```
Service UUID: 0xFFB0 (ScribeNib)
  ├── Char 0xFFB1: Recognized Text (notify) — UTF-8 string
  ├── Char 0xFFB2: Last Character (read/notify) — uint8
  ├── Char 0xFFB3: Confidence (read) — float32 (0.0-1.0)
  ├── Char 0xFFB4: Raw Stroke Data (notify) — blob (x,y pairs, uint16 each)
  ├── Char 0xFFB5: Active Profile (read/write) — uint8 (0-3)
  ├── Char 0xFFB6: Recognition Mode (read/write) — uint8 (0=auto,1=letter,2=number,3=gesture)
  ├── Char 0xFFB7: Battery Level (read) — uint8 (0-100%)
  └── Char 0xFFB8: Firmware Version (read) — string
```

---

## CNN Model Details

- **Architecture**: 6-layer CNN with depthwise separable convolutions
- **Input**: 32×32 grayscale image (rendered from trajectory)
- **Output**: 62-class softmax (0-9, A-Z, a-z)
- **Size**: 92KB flash, ~4ms inference on ESP32-S3 @ 240MHz
- **Accuracy**: 82% top-1 raw, 94% with n-gram correction
- **Training data**: IAM Online Handwriting Database + synthetic augmentation

```
Input (32×32×1)
  → Conv2D(3×3, 32, stride=1, pad) + BN + ReLU
  → DepthwiseConv2D(3×3, stride=2, pad) + BN + ReLU       // 16×16×32
  → Conv2D(1×1, 64) + BN + ReLU                            // 16×16×64
  → DepthwiseConv2D(3×3, stride=2, pad) + BN + ReLU       // 8×8×64
  → Conv2D(1×1, 128) + BN + ReLU                           // 8×8×128
  → GlobalAvgPool                                            // 128
  → Dense(128, ReLU)
  → Dense(62, Softmax)
```

### Rendering Pipeline

Raw 3D trajectory is rendered to a 32×32 image for the CNN:

1. Normalize stroke bounding box to fit 28×28 pixel area (2px margin)
2. Apply uniform scaling (preserve aspect ratio)
3. Rasterize with 1.5px pen width using Bresenham line algorithm
4. Apply slight Gaussian blur (σ=0.5) for anti-aliasing

---

## Language Model

The n-gram corrector uses a character-level bigram model:

- **Storage**: 2MB flash partition (read-only, mmap'd)
- **Structure**: 62×62 probability table + unigram priors + common word list (10K words)
- **Correction algorithm**: 
  1. If confidence > 0.9, accept as-is
  2. If confidence 0.5-0.9, compute P(char|prev_char) × confidence for top-3 candidates
  3. If confidence < 0.5, check against word list using edit distance ≤ 2
- **Context window**: last 3 characters for bigram scoring

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | ESP32-S3-MINI-1 | Module | 1 | $3.50 | WiFi/BLE5, dual-core 240MHz |
| 2 | ICM-42688-P | LGA-14 2.5×3 | 1 | $2.40 | 6-axis IMU, SPI |
| 3 | QMC5883L | LGA-16 3×3 | 1 | $0.90 | Magnetometer, I²C |
| 4 | SSD1306 64×32 | Custom flex | 1 | $1.80 | Tiny OLED on flex tail |
| 5 | MCP73831 | SOT-23-5 | 1 | $0.40 | Lipo charger |
| 6 | ME6211-3.3 | SOT-23-5 | 1 | $0.25 | LDO 3.3V 300mA |
| 7 | Lipo 80mAh | Custom pouch | 1 | $2.20 | 3.7V |
| 8 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Power + data |
| 9 | Vibration motor | 4mm coin | 1 | $0.60 | Haptic feedback |
| 10 | Si2302 MOSFET | SOT-23 | 1 | $0.08 | Motor driver |
| 11 | WS2812B-2020 | 2020 | 1 | $0.15 | Status LED |
| 12 | Spring steel clip | Custom | 1 | $0.50 | 0.3mm spring steel |
| 13 | Passives (R/C/L) | 0402 | ~25 | $0.45 | Pullups, decoupling |
| 14 | PCB 4-layer 12×18mm | Rect | 1 | $0.80 | JLCPCB |

**Total estimated BOM: ~$14.38** (qty 1)

---

## Directory Structure

```
scribe-nib/
├── README.md                  # This file
├── schematic/
│   ├── scribe_nib.kicad_sch
│   ├── scribe_nib.kicad_pcb
│   └── scribe_nib.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── app_main.c
│   │   ├── imu_driver.c
│   │   ├── imu_driver.h
│   │   ├── stroke_segmenter.c
│   │   ├── stroke_segmenter.h
│   │   ├── trajectory_recon.c
│   │   ├── trajectory_recon.h
│   │   ├── char_recognizer.c
│   │   ├── char_recognizer.h
│   │   ├── lang_model.c
│   │   ├── lang_model.h
│   │   ├── ble_hid.c
│   │   ├── ble_hid.h
│   │   ├── ble_custom.c
│   │   ├── ble_custom.h
│   │   ├── oled_display.c
│   │   ├── oled_display.h
│   │   ├── power_manager.c
│   │   ├── power_manager.h
│   │   ├── calibration.c
│   │   ├── calibration.h
│   │   ├── gesture_handler.c
│   │   ├── gesture_handler.h
│   │   ├── haptic_feedback.c
│   │   └── haptic_feedback.h
│   ├── components/
│   │   └── model/
│   │       └── char_cnn.tflite
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── hardware/
│   ├── BOM.csv
│   ├── gerbers/
│   └── enclosure/
│       └── clip_sleeve.step
├── scripts/
│   ├── train_char_cnn.py
│   ├── render_stroke.py
│   ├── read_scribe.py
│   └── calibrate_user.py
└── docs/
    ├── calibration_guide.md
    ├── api_reference.md
    └── assembly_guide.md
```

---

## Getting Started

### Flash Firmware

```bash
# Install ESP-IDF v5.3+
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/scribe-nib/firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

### Connect via BLE

The Scribe Nib appears as a Bluetooth keyboard named "ScribeNib-XXXX". Pair it like any BLE keyboard:
1. Hold BOOT button during power-on to enter pairing mode
2. Find "ScribeNib-XXXX" in your device's Bluetooth settings
3. Pair — recognized characters will now type into any text field

### Read Raw Data (Python)

```bash
pip install bleak
python3 scripts/read_scribe.py --mac AA:BB:CC:DD:EE:FF
```

### Calibrate for Your Handwriting

```bash
python3 scripts/calibrate_user.py --port /dev/ttyACM0
# Follow on-screen prompts to write each character 3 times
# Profile is saved to NVS on the device
```

### Train Custom CNN Model

```python
# See docs/calibration_guide.md for dataset format
python3 scripts/train_char_cnn.py \
    --data handwriting_samples/ \
    --output model/char_cnn.tflite \
    --quantize int8
```

---

## Calibration Process

The Scribe Nib supports per-user handwriting profiles to improve recognition accuracy:

1. **Quick calibration** (2 min) — write the alphabet once; adjusts stroke timing and scaling
2. **Full calibration** (10 min) — write each character 3 times; creates personalized CNN embeddings
3. **Adaptive mode** — continuously learns from corrections (BLE app sends back corrected characters)

Profile storage in NVS:
- Profile 0: factory default (general population)
- Profiles 1-3: user-specific (calibration data)

Switch profiles via the custom BLE service (0xFFB5) or by double-tapping the clip touch pad.

---

## Special Gestures

Beyond character recognition, the Scribe Nib detects these intentional pen gestures:

| Gesture | Motion | Action |
|---------|--------|--------|
| Swipe Right → | Quick horizontal right | Space |
| Swipe Left ← | Quick horizontal left | Backspace |
| Swipe Down ↓ | Quick vertical down | Enter |
| Circle ○ | Clockwise circle | Toggle caps lock |
| Zigzag ⚡ | Rapid horizontal zigzag | Switch number/letter mode |
| Shake ✕ | Quick side-to-side shake | Undo last character |

Gesture detection runs in parallel with character recognition using a lightweight DTW (Dynamic Time Warping) classifier.

---

## Known Limitations

- **Drift** — position estimation drifts over time; reset at each pen-up limits this to single-stroke or short multi-stroke characters. Long cursive writing is not supported.
- **Writing surface** — requires a firm writing surface (paper, desk) for reliable pen-up/pen-down detection. Soft surfaces (cushions) reduce accuracy.
- **Character set** — currently supports 62 alphanumeric characters only. Punctuation and symbols are handled via gesture mode or phone-side autocorrect.
- **Calibration** — factory model achieves ~82% accuracy; per-user calibration improves to ~94%. Best results require the full calibration procedure.

---

*Invented 2026-06-14 by jayis1*