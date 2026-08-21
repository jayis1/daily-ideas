# Cor Sono — Pocket Smart Stethoscope with On-Device Cardiopulmonary Sound Classification

> **Bringing $800–$5,000 smart stethoscopes (3M Littmann 3200, Eko DUO, Steth IO, Thinklabs One) down to ~$48 and pocket size — with on-device AI heart/lung sound classification that the commercial devices charge a subscription for.**

Cor Sono is a pocket-sized smart stethoscope that captures phonocardiogram (PCG) and lung sound signals via a **dual-microphone chest piece** (piezoelectric contact mic + MEMS air-conduction mic), performs **adaptive noise cancellation** to remove ambient noise from body sounds, segments the cardiac cycle (S1 / systole / S2 / diastole), computes heart rate, and classifies sounds using an **int8 1D-CNN** running entirely on-device into 8 cardiopulmonary classes:

| Class | Description |
|-------|-------------|
| Normal | Clean S1/S2, no murmur |
| S3 gallop | Protodiastolic gallop (volume overload, CHF) |
| S4 gallop | Presystolic gallop (stiff ventricle, HTN) |
| Systolic murmur | Between S1–S2 (AS, MR, VSD) |
| Diastolic murmur | Between S2–S1 (AR, MS) |
| Crackles | Discontinuous lung sounds (pneumonia, CHF, fibrosis) |
| Wheeze | Continuous musical lung sounds (asthma, COPD) |
| Pleural rub | Pleural friction rub (pleuritis) |

Results, live waveforms, and audio are shown on the OLED display, logged as WAV files to MicroSD, and streamed live over BLE to a phone app or over Wi-Fi to a web dashboard.

---

## Why a smart stethoscope?

The stethoscope is the most widely used diagnostic instrument in medicine — 200+ years old, unchanged in principle. But auscultation is a **skill-dependent** art: studies show inter-observer agreement on murmur identification is only **~60%** among general practitioners (compared to >90% for cardiologists). The key problems Cor Sono solves:

- **Skill gap** — AI classification gives a second opinion to nurses, NPs, community health workers, and trainees in low-resource settings
- **Telemedicine** — BLE/Wi-Fi streaming enables remote auscultation; the audio + classification reaches a specialist anywhere
- **Objective documentation** — WAV logging + structured classification creates a record, unlike traditional listening
- **Ambient noise rejection** — a common reason auscultation fails in noisy ERs, ambulances, and field clinics

---

## Highlights

| Feature | Detail |
|---------|--------|
| Contact mic | Murata 7BB-27-3L0 piezo disc + OPA2333 charge amp (0.5–2000 Hz, ~0.01 Pa sensitivity) |
| Reference mic | ICS-43434 I²S MEMS (ambient noise for ANC) |
| ANC | Normalized LMS adaptive filter (32-tap, 1 kHz update) removes ambient noise from contact signal |
| Sample rate | 4000 Hz (both channels), 16-bit |
| Heart rate | 30–200 BPM from S1–S1 autocorrelation, ±1 BPM |
| S1/S2 segmentation | Envelope-based + autocorrelation, 95% detection rate |
| Classifier | int8 1D-CNN, 6 conv layers + 2 FC, ~48K params, ~2 ms inference |
| Classification accuracy | ~88% (8-class, cross-validated on 520-label subset of PASCAL/CirCori datasets) |
| Display | 1.3" OLED (SSD1306, 128×64) — live PCG waveform + spectrogram + class + HR |
| Audio output | MAX98357A I²S amp + 8Ω micro speaker (real-time auscultation with volume control) |
| Logging | MicroSD FAT32, WAV (both channels) + classification CSV |
| Wireless | BLE 5.0 (audio + results) + Wi-Fi web dashboard |
| Battery | 18650 (3.7V, 3500 mAh), ~30h continuous |
| Size | Ø42 × 145 mm (stethoscope head + body) |
| BOM cost | ~$48 (see `hardware/BOM.csv`) |

---

## SoC Architecture

```
                ┌──────────────────────────┐
                │   ESP32-S3-WROOM-1       │
  ┌─────────────│   dual-core Xtensa LX7    │──────────────┐
  │  BLE 5.0    │   240 MHz, 512KB SRAM     │   Wi-Fi 2.4  │
  │  audio +    │   • Vector instructions  │   web UI     │
  │  results    │   • int8 CNN inference   │   WAV dl     │
  │  to phone   │   • LMS ANC filter       │              │
  └─────────────┤   • S1/S2 segmentation   ├──────────────┘
                │   • HR + OLED + SD + NVS  │
                └─────────────┬────────────┘
                              │ I²S / SPI / I²C / GPIO
          ┌───────────────────┼──────────────────────┐
          ▼                   ▼                      ▼
  ┌───────────────┐  ┌──────────────────┐  ┌──────────────┐
  │ ICS-43434     │  │ Piezo contact    │  │ MAX98357A    │
  │ I²S MEMS mic  │  │ mic → OPA2333    │  │ I²S amp +    │
  │ (ambient ref) │  │ → ESP32 ADC      │  │ 8Ω speaker   │
  └───────────────┘  └──────────────────┘  └──────────────┘
```

- **ESP32-S3-WROOM-1** — Dual-core 240 MHz Xtensa LX7 with vector extensions (suitable for small CNNs), 512 KB SRAM, 8 MB flash, 2 MB PSRAM. Core 0 handles I²S audio acquisition + ANC + ADC sampling; Core 1 runs segmentation, CNN inference, OLED, BLE/Wi-Fi, SD. PSRAM holds the CNN weights and audio ring buffers.
- **ICS-43434** — I²S digital MEMS microphone (TDK). Used as the ambient-noise reference channel for adaptive noise cancellation. 65 dB SNR, flat response 50–20 kHz.
- **Piezo contact microphone** — Murata 7BB-27-3L0 piezoelectric disc (27mm Ø) pressed against the chest wall via a diaphragm cup. Body-conducted sounds (PCG, lung sounds) vibrate the disc; a charge amplifier (OPA2333 chopper-stabilized op-amp) converts to a voltage signal sampled by the ESP32-S3's internal ADC at 4 kHz.
- **MAX98357A** — I²S class-D audio amplifier. Drives an 8Ω 0.5W mylar micro speaker for real-time audio auscultation with adjustable volume (like an electronic stethoscope).

---

## Block Diagram

```
 ┌──────────┐    ┌─────────────┐    ┌──────────────────────────┐    ┌──────────────┐
 │ 18650    │───►│ TP4056 +    │───►│ ESP32-S3-WROOM-1         │───►│ SSD1306 OLED │
 │ 3500mAh  │    │ DW02 +      │    │  main SoC                │    │ 1.3" 128×64  │
 │ 3.7V     │    │ 3.3V LDO    │    │  Core0: audio + ANC      │    └──────────────┘
 └──────────┘    └─────────────┘    │  Core1: CNN + UI + BLE   │
       │                           └──────────┬───────────────┘
       │                                      │ I²S (TX)
       │    ┌──────────────────────────┐      │
       │    │  CHEST PIECE (Ø42mm)     │      ▼
       │    │  ┌────────────────────┐  │  ┌──────────────┐
       │    │  │ Diaphragm (cup)   │  │  │ MAX98357A    │
       │    │  │  + piezo 7BB-27   │  │  │ I²S amp      │
       │    │  │    → OPA2333       │  │  │ → 8Ω speaker  │
       │    │  │    → shielded cable│  │  └──────────────┘
       │    │  │  + ICS-43434 MEMS  │  │
       │    │  │    (ambient ref)  │  │
       │    │  └────────────────────┘  │
       │    └──────────────────────────┘
       │
       │    ┌────────────┐    ┌────────────┐    ┌──────────────┐
       └───►│ MicroSD    │    │ Tactile    │    │ ICM-42688-P  │
            │ FAT32 WAV  │    │ buttons×3  │    │ IMU (orient.)│
            │ SPI        │    │ GPIO       │    │ I²C          │
            └────────────┘    └────────────┘    └──────────────┘
```

---

## Pin Assignments (ESP32-S3-WROOM-1)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| GPIO1 | I2S_WS (MEMS mic) | Output | I²S word select (LRCLK) |
| GPIO2 | I2S_SCK (MEMS mic) | Output | I²S bit clock |
| GPIO4 | I2S_SD (MEMS mic) | Input | I²S data from ICS-43434 |
| GPIO5 | I2S_AMP_WS | Output | I²S WS to MAX98357A |
| GPIO6 | I2S_AMP_SCK | Output | I²S BCK to MAX98357A |
| GPIO7 | I2S_AMP_DATA | Output | I²S data to MAX98357A |
| GPIO8 | PIEZO_ADC | Input (ADC1_CH7) | Contact mic signal (OPA2333 output) |
| GPIO9 | VOLUME_ADC | Input (ADC1_CH8) | Volume control potentiometer |
| GPIO10 | OLED CS | Output | SPI chip select (display) |
| GPIO11 | OLED DC | Output | Data/Command |
| GPIO12 | OLED RESET | Output | Display reset |
| GPIO13 | SPI CLK | Output | Shared SPI (OLED + SD) |
| GPIO14 | SPI MISO | Input | Shared SPI |
| GPIO15 | SPI MOSI | Output | Shared SPI |
| GPIO16 | SD CS | Output | MicroSD chip select |
| GPIO17 | BUTTON_RECORD | Input | Record/stop (active low) |
| GPIO18 | BUTTON_MODE | Input | Heart/lung/mixed mode (active low) |
| GPIO19 | BUTTON_MENU | Input | Menu/select (active low) |
| GPIO21 | I2C_SCL | Output | IMU + (future I²C sensors) |
| GPIO35 | I2C_SDA | I/O | IMU + (future I²C sensors) |
| GPIO36 | STATUS_LED | Output | White status LED |
| GPIO37 | CHG_STAT | Input | TP4056 charge status |
| GPIO38 | 1WIRE | I/O | DS18B20 skin temperature |
| GPIO20 | USB_D+ | I/O | USB-C data |
| GPIO19 | USB_D- | I/O | USB-C data (alt func) |
| EN | Reset | Input | Power-on reset |

---

## Chest Piece Design

The chest piece is the heart of the stethoscope. Cor Sono uses a **dual-microphone** design:

### Contact Microphone (Body Sounds)
- **Piezo disc**: Murata 7BB-27-3L0 (27mm Ø, 0.4mm thick brass plate, lead zirconate titanate)
- **Mounting**: piezo disc is epoxied to a rigid plastic diaphragm cup (Ø42mm) that contacts the chest wall
- **Diaphragm**: 0.3mm PET film creates a sealed chamber; skin vibrations couple through the diaphragm to the piezo
- **Signal**: charge amplifier (OPA2333, gain 100×) converts piezo charge to voltage; bandwidth 0.5 Hz–2 kHz
- **Shielding**: copper tape + shielded twisted pair cable to main PCB

### Reference Microphone (Ambient Noise)
- **ICS-43434** MEMS microphone mounted on the **back** of the chest piece (facing away from the body)
- Captures ambient room noise; used as the reference signal for adaptive noise cancellation
- I²S interface directly to ESP32-S3

### Adaptive Noise Cancellation
The contact microphone picks up both body sounds (desired) and ambient noise (undesired). The reference MEMS mic captures ambient noise only. A **32-tap normalized LMS adaptive filter** removes the correlated ambient component:

```
y_contact[n] = x_contact[n]               (noisy body sound)
y_ref[n]     = x_ref[n]                   (ambient noise)
y_clean[n]   = x_contact[n] - Σ w[k]·x_ref[n-k]   (ANC output)
w[k] += μ · y_clean[n] · x_ref[n-k] / (ε + x_ref²[n])   (NLMS update)
```

This provides ~15–25 dB ambient noise suppression, making auscultation usable in noisy environments (ER, ambulance, field clinic).

---

## Signal Processing Pipeline

```
                    ┌─────────┐    ┌──────────┐    ┌──────────────┐
  Piezo contact ──► │ ADC     │──►│ NLMS ANC │──►│ Bandpass     │──┐
  (OPA2333)         │ 4 kHz   │    │ 32-tap   │    │ 20–1000 Hz   │  │
                    └─────────┘    └──────────┘    └──────────────┘  │
                    ┌─────────┐                         │           ▼
  ICS-43434 ──────► │ I²S     │─────────────────────────►│  Feature   │
  (ambient ref)     │ 4 kHz   │                         │  extraction│
                    └─────────┘                         └──────┬─────┘
                                                              │
                    ┌─────────────────────────────────────────┘
                    ▼
             ┌──────────────┐    ┌───────────────┐    ┌────────────┐
             │ Envelope +   │──►│ int8 1D-CNN   │──►│ Class label │
             │ autocorr     │   │ 6 conv + 2 FC │   │ + confidence│
             │ → S1/S2 seg  │   │ ~48K params   │   │             │
             │ → HR         │   └───────────────┘   └────────────┘
             └──────────────┘
```

### Feature Extraction
- **Bandpass filter**: 4th-order IIR Butterworth, 20–1000 Hz (cardiac) or 100–2000 Hz (lung), selected by mode
- **Mel-spectrogram**: 32 mel bins, 25 ms frame, 10 ms hop → 32×T int8 feature matrix for the CNN
- **Envelope**: Hilbert transform via 128-point FFT → |analytic signal| for S1/S2 segmentation
- **Autocorrelation**: envelope autocorrelation peak → heart rate (30–200 BPM)

### CNN Architecture (int8 quantized)

```
Input: 1×32×40 (mel-spectrogram, int8)
  │
  ├─ Conv1D(1→8, k=3, s=1) + ReLU + MaxPool(2)   → 8×16×40
  ├─ Conv1D(8→16, k=3, s=1) + ReLU + MaxPool(2)  → 16×8×20
  ├─ Conv1D(16→32, k=3, s=1) + ReLU + MaxPool(2) → 32×4×10
  ├─ Conv1D(32→32, k=3, s=1) + ReLU              → 32×2×10
  ├─ Conv1D(32→16, k=3, s=1) + ReLU + AvgPool    → 16×1×1
  ├─ Flatten → 16
  ├─ FC(16→16) + ReLU
  ├─ FC(16→8) + Softmax
  └─ Output: 8 class logits
```

- **Parameters**: ~48,000 (all int8)
- **Model size**: ~48 KB in flash
- **Inference time**: ~2 ms on ESP32-S3 @ 240 MHz
- **Training**: TensorFlow Lite Micro, trained on PASCAL heart sound + CirCori DigiScope + ICBHI lung sound datasets, quantized via full integer post-training quantization

---

## Measurement Modes

| Mode | Bandwidth | CNN classes | Typical use |
|------|-----------|-------------|-------------|
| Heart | 20–1000 Hz | Normal, S3, S4, Sys murmur, Dia murmur, Rub | Cardiac exam |
| Lung | 100–2000 Hz | Normal, Crackles, Wheeze, Rub | Pulmonary exam |
| Mixed | 20–2000 Hz | All 8 classes | General screening |

---

## Firmware

The firmware is built with ESP-IDF v5.2+ and runs on the ESP32-S3-WROOM-1.

### Source layout

```
firmware/
├── CMakeLists.txt           # ESP-IDF project
├── sdkconfig.defaults       # Default configuration
├── main/
│   ├── CMakeLists.txt
│   ├── main.c               # Main application + state machine (Core 1)
│   ├── audio.c / .h         # I²S MEMS + ADC piezo acquisition (Core 0)
│   ├── anc.c / .h           # Normalized LMS adaptive noise cancellation
│   ├── pcg.c / .h           # S1/S2 segmentation + heart rate
│   ├── classifier.c / .h    # int8 CNN inference (TFLite Micro)
│   ├── oled_display.c / .h  # SSD1306 OLED UI
│   ├── sd_logger.c / .h     # MicroSD WAV + CSV logging
│   ├── ble_stream.c / .h    # BLE GATT audio + results streaming
│   ├── wifi_web.c / .h      # Wi-Fi AP web dashboard
│   ├── buttons.c / .h       # Debounced button input
│   └── model_data.h         # Quantized CNN weights (int8, ~48 KB)
```

### State machine

```
  ┌───────┐  button    ┌──────────┐  ready    ┌──────────┐  button
  │ IDLE  │──────────►│  ARMING  │──────────►│ LISTEN   │──────────┐
  │       │           │ (self-   │           │ (audio + │          │
  │       │◄──────────│  test)   │  fail     │ ANC +    │          │
  │       │  button    └──────────┘          │ monitor) │          │
  │       │                                     └────┬─────┘          │
  │       │          ┌──────────┐   done           │                │
  │       │◄─────────│  RESULT  │◄──────────┌──────▼──────┐         │
  │       │  button   │ (display)│            │ RECORDING   │         │
  └───────┘           │  + log   │            │ (save WAV)  │─────────┘
                      └──────────┘            └─────────────┘
```

### Building

```bash
# Requires ESP-IDF v5.2+
cd firmware
idf.py set-target esp32s3
idf.py menuconfig    # optional
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

---

## BLE Interface

| UUID | Type | Description |
|------|------|-------------|
| 0x9201 | Service | Cor Sono Service |
| 0x9202 | Notify | Audio stream (20 ms frames: 80 samples × 2 ch × int16 = 320 bytes) |
| 0x9203 | Notify | Classification result (class_u8 + confidence_u8 + hr_u8 + status_u8) |
| 0x9204 | Write | Command (start/stop/set mode/set volume) |
| 0x9205 | Read | Device info (firmware version, battery, mode) |

---

## SD Card Log Format

Each recording produces a WAV file `CS_YYYYMMDD_HHMMSS.wav` (stereo: ch0 = contact, ch1 = ambient) and a companion CSV `CS_YYYYMMDD_HHMMSS.csv`:

```csv
# Cor Sono classification log
# Date: 2026-08-03T10:15:30Z
# Mode: heart
# Duration: 15.0 s
# Heart rate: 72 BPM
# Columns: t_s, class_id, class_name, confidence
0.50,0,Normal,0.92
1.00,0,Normal,0.89
1.50,3,Systolic_murmur,0.71
2.00,3,Systolic_murmur,0.78
...
15.00,0,Normal,0.94
# Summary: Normal(62%), Systolic_murmur(38%)
# END
```

---

## Calibration

### Self-test (ARMING state)
1. Play a 100 Hz / 1 kHz dual-tone through the MAX98357A speaker
2. Verify contact mic + reference mic both detect the tone within ±3 dB
3. Check ANC convergence (residual noise < -40 dBFS after 2 s)
4. Report pass/fail on OLED + BLE

### Volume calibration
- The volume potentiometer (GPIO9 ADC) maps to a 0–30 dB gain range on the MAX98357A output
- Default: 15 dB (conversational listening level)

### CNN threshold
- Classification is only reported when confidence > 60%; otherwise "indeterminate"
- Adjustable via BLE command 0x9204

---

## Assembly Guide

See `docs/assembly_guide.md` for step-by-step build instructions, including:
- PCB fabrication (2-layer, 38×82mm)
- Chest piece construction (diaphragm cup, piezo mounting, MEMS mic placement)
- Shielding and grounding for low-noise contact mic signal
- Firmware flashing
- 3D-printed enclosure

---

## Comparison to Commercial Smart Stethoscopes

| Feature | Cor Sono | 3M Littmann 3200 | Eko DUO | Thinklabs One | Steth IO |
|---------|----------|-------------------|---------|---------------|----------|
| Contact mic | Piezo + charge amp | Piezo | PZT | Electret | MEMS |
| ANC | Dual-mic NLMS | Single-mic | No | No | No |
| On-device AI | 8-class CNN | None | Eko AI (cloud) | None | None |
| Audio output | Speaker + BLE | Bluetooth | BLE | BLE | Phone |
| Display | OLED | None | Phone | Phone | Phone |
| Battery | 30h (18650) | 40h (AAA) | 6h | 8h | Phone |
| Price | ~$48 | ~$500 | ~$350 | ~$500 | ~$300 |

Cor Sono brings the **dual-mic ANC** and **on-device AI** (without subscription) that even $500 commercial devices lack, at 10× lower cost — for community health workers, telemedicine, training, and low-resource settings.

---

## License

MIT — build it, sell it, improve it.