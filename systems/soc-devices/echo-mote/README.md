# Echo Mote

**A pocket-sized room acoustic analyzer with stereo MEMS mic array, swept-sine speaker output, on-device FFT, and BLE/Wi-Fi reporting.**

---

## What It Does

The Echo Mote is a credit-card-sized PCB that you place in any room, press a button, and 8 seconds later you have a complete acoustic profile:

- **Reverberation time (RT60)** — swept-sine burst + decay capture measures T20, T30, T60 across 6 octave bands (125 Hz – 4 kHz)
- **Frequency response** — log-swept sine (20 Hz – 20 kHz, 5 s) captured by dual MEMS mics, deconvolved to produce magnitude + phase response
- **Room modes** — sustained narrowband excitation + decay reveals standing-wave resonances with ±2 Hz accuracy
- **Clarity indices** — C50, C80, and D50 computed from impulse response energy ratios
- **Background noise** — ambient NC curve estimation from 30 s of silence
- **Stereo cross-correlation** — dual-mic spacing (40 mm) gives inter-aural cross-correlation (IACC) for spatial impression assessment

All processing runs on-device using the **ESP32-S3** (240 MHz dual-core Xtensa with 512 KB SRAM + 8 MB PSRAM). Results are displayed on a **1.3" IPS LCD** (240×240) and streamed over **BLE 5.0** or **Wi-Fi** to a companion app for detailed plotting.

Battery life: **200+ measurements** on a single 800 mAh Lipo (each measurement: ~10 s active, ~5 mA sleep between).

Use cases:
- Home studio and home theater setup — find the best speaker/listener positions
- Office and classroom design — verify speech intelligibility (C50 > 0 dB, RT60 < 0.6 s)
- Architectural acoustics — quick surveys without hauling a laptop + full measurement rig
- HVAC noise audit — NC curve from background noise capture
- Live sound — check venue RT60 before a gig

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         ECHO MOTE                                 │
│                                                                   │
│  ┌───────────────┐   ┌───────────────┐   ┌─────────────────────┐ │
│  │ ICS-43434     │   │ ICS-43434     │   │ 28 mm Micro Speaker │ │
│  │ MEMS Mic L    │   │ MEMS Mic R    │   │ 8 Ω, 0.5 W         │ │
│  │ I²S output   │   │ I²S output   │   │   │                  │ │
│  │  (40mm sep)  │   │  (40mm sep)  │   │ ┌─▼──────────────┐  │ │
│  └──────┬───────┘   └──────┬───────┘   │ │ MAX98357A      │  │ │
│         │ I²S_SD0          │ I²S_SD1  │ │ I²S DAC + Amp  │  │ │
│         │                  │          │ │ 3 W Class-D     │  │ │
│         │                  │          │ └──┬─────────────┘  │ │
│  ┌──────▼──────────────────▼──────────▼────▼──────────────┐  │ │
│  │                   ESP32-S3-WROOM-1-N8R8                 │  │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐ │  │ │
│  │  │ Xtensa LX7│  │ I²S x2     │  │ 8 MB PSRAM       │ │  │ │
│  │  │ Dual 240MHz│ │ TX (speaker)│ │ (impulse resp)   │ │  │ │
│  │  │ (FFT + IR) │  │ RX (mics)  │  │                  │ │  │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘ │  │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐ │  │ │
│  │  │ SPI LCD   │  │ BLE 5.0   │  │ Wi-Fi 6          │ │  │ │
│  │  │ 240×240   │  │ GATT server│  │ MQTT/REST uplink │ │  │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘ │  │ │
│  └─────────────────────┬──────────────────────────────────────┘ │
│                        │                                          │
│  ┌─────────────────────▼────────────────────────────────────┐   │
│  │  ST7789V 1.3" IPS LCD (SPI) — RT60 bars, freq response  │   │
│  │  240×240, 4-wire SPI + DC                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  BME280 (T/H/P for air-density compensation)   I²C 0x76 │   │
│  │  Power: MCP73831 charger + AP2112-3.3V LDO             │   │
│  │  Battery: 800 mAh Lipo (3.7V)                           │   │
│  │  USB-C: charging + UART flash                           │   │
│  │  User: 3 buttons (Measure, Mode, Power)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (ESP32-S3-WROOM-1-N8R8)

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| GPIO1 | I²S_MCLK | MAX98357A + both ICS-43434 | Master clock, 256×Fs |
| GPIO2 | I²S0_BCLK | I2S0 bit clock | Mic + speaker share BCLK |
| GPIO3 | I²S0_WS | I2S0 word select | L/R select |
| GPIO4 | I²S0_DATA_IN | ICS-43434 L data out | Left MEMS mic |
| GPIO5 | I²S0_DATA_OUT | MAX98357A DIN | Speaker DAC data in |
| GPIO6 | I²S1_BCLK | I2S1 bit clock | Second I²S bus for mic R |
| GPIO7 | I²S1_WS | I2S1 word select | Right mic word select |
| GPIO8 | I²S1_DATA_IN | ICS-43434 R data out | Right MEMS mic |
| GPIO9 | SPI_CLK | ST7789V SCL | LCD SPI clock |
| GPIO10 | SPI_MOSI | ST7789V SDA | LCD SPI data |
| GPIO11 | SPI_DC | ST7789V DC | LCD data/command |
| GPIO12 | SPI_CS | ST7789V CS | LCD chip select (active low) |
| GPIO13 | LCD_RST | ST7789V RES | LCD reset (active low) |
| GPIO14 | LCD_BL | ST7789V BL | LCD backlight (PWM dimmable) |
| GPIO15 | I²C_SDA | BME280 SDA | 4.7 kΩ pullup |
| GPIO16 | I²C_SCL | BME280 SCL | 4.7 kΩ pullup |
| GPIO17 | BTN_MEASURE | Tactile switch | Active-low, internal pullup |
| GPIO18 | BTN_MODE | Tactile switch | Active-low, internal pullup |
| GPIO19 | BTN_POWER | Tactile switch | Active-low, internal pullup |
| GPIO20 | AMP_SD | MAX98357A SD | Shutdown control (low = mute) |
| GPIO21 | LED_R | WS2812B data | Status LED (RGB) |
| GPIO38 | CHARGE_STAT | MCP73831 STAT | Charge status input |
| GPIO39 | VBAT_SENSE | Voltage divider | ADC1_CH3, 1:2 divider |
| GPIO40 | BAT_TEMP | NTC 10k | ADC1_CH4, battery temp |
| GPIO41 | USB_D+ | USB-C D+ | Native USB |
| GPIO42 | USB_D- | USB-C D- | Native USB |
| GPIO43 | UART_TX | Debug/flash | 3.3V UART |
| GPIO44 | UART_RX | Debug/flash | 3.3V UART |
| GPIO46 | MIC_L_EN | ICS-43434 L L/R select | Tie high for left |
| GPIO47 | MIC_R_EN | ICS-43434 R L/R select | Tie low for right |

---

## Power Architecture

```
USB-C (5V) ──► MCP73831 ──► Lipo (3.7V, 800 mAh) ──► AP2112-3.3V ──► VDD (3.3V)

Quiescent: ~15 µA (deep sleep, RTC on, LCD off, amp shutdown)
Active (measurement, 8 s): ~120 mA avg (speaker + mics + FFT + LCD)
Active (BLE advertising, idle): ~5 mA avg
Sleep (between measurements): ~15 µA

Battery life: 800 mAh / (10 s × 120 mA + sleep) ≈ 200+ measurements per charge
Standby (BLE on, 1 Hz adv): ~160 hours
```

Power states:
1. **OFF** — LDO disabled, deep sleep, only RTC on (~15 µA)
2. **IDLE** — LCD on, BLE advertising, waiting for button press (~5 mA)
3. **MEASURING** — Speaker + mics + FFT active, LCD updating (~120 mA, 8–10 s)
4. **STREAMING** — Wi-Fi connected, sending results to app (~70 mA, 5 s)

---

## Measurement Pipeline

### Step 1: Swept-Sine Excitation (5 seconds)

The ESP32-S3 generates a logarithmic swept sine (also called a "chirp") from 20 Hz to 20 kHz over 5 seconds. The signal is output via I²S to the MAX98357A amplifier, driving the 28 mm speaker at ~0.3 W (comfortable room volume, ~75 dB SPL at 1 m).

```
f(t) = 20 × (1000)^(t/5)  Hz    (t = 0..5 s)
```

### Step 2: Impulse Response Extraction

Both MEMS mics capture the room response simultaneously at 48 kHz / 16-bit (dual I²S buses). The 5-second captured signal is cross-correlated with the inverse swept-sine to deconvolve the room's impulse response (IR). This is computed in PSRAM using overlap-save FFT:

```
IR = IFFT( FFT(captured) × FFT(inverse_chirp) )
```

The inverse chirp is precomputed and stored in flash. The IR is typically 2–4 seconds for normal rooms; we retain 4 seconds post-peak.

### Step 3: Acoustic Parameter Computation

From the impulse response, we compute:

| Parameter | Method | Bands |
|-----------|--------|-------|
| RT60 (T20/T30/T60) | Schroeder backward integration | 6 octave bands: 125, 250, 500, 1k, 2k, 4k Hz |
| C50 (clarity) | 10²×(E_0-50ms / E_50ms-∞) dB | Broadband + per-octave |
| C80 (clarity) | 10²×(E_0-80ms / E_80ms-∞) dB | Broadband + per-octave |
| D50 (definition) | E_0-50ms / E_total | Broadband + per-octave |
| Frequency response | Magnitude of FFT(IR) | 20 Hz – 20 kHz, 1/3-octave smoothed |
| Room modes | Peak detection in low-freq IR spectrum | 20–300 Hz, ±2 Hz |
| IACC | Cross-correlation of L/R IR | Broadband inter-aural cross-corr |

### Step 4: Background Noise (optional, 30 s capture)

If the user selects "Noise" mode, the device captures 30 s of ambient sound with the speaker muted, computes 1/3-octave band levels, and maps to an NC (Noise Criteria) curve.

---

## Room Mode Detection

Room modes are standing-wave resonances determined by room dimensions. The Echo Mote detects them by:

1. Generating a sustained sine at each candidate frequency (20–300 Hz, 1 Hz steps) for 50 ms
2. Measuring the decay time after each burst
3. Frequencies with decay times >2× the broadband average are flagged as room modes
4. Mode frequencies are classified as axial, tangential, or oblique by their harmonic relationship

This "ping and listen" method is more reliable than pure IR analysis for low-frequency modes because the speaker's low-frequency output rolls off, but the resonance ring-down is clearly audible.

---

## Measurement Modes

The MODE button cycles through 5 measurement modes:

| Mode | Button Label | Duration | Output |
|------|-------------|----------|--------|
| RT60 | "RT60" | 8 s | T20/T30/T60 per octave band |
| FREQ | "FREQ" | 8 s | Magnitude + phase response |
| MODES | "MODES" | 25 s | Room mode scan (20–300 Hz) |
| CLARITY | "C50/80" | 8 s | C50, C80, D50 per octave |
| NOISE | "NC" | 30 s | Background NC curve |

---

## BLE GATT Service

```
Service UUID: 0xFFB0 (EchoMote)
  ├── Char 0xFFB1: Measurement Command (write) — uint8 (1=RT60, 2=FREQ, 3=MODES, 4=CLARITY, 5=NOISE)
  ├── Char 0xFFB2: RT60 Results (read/notify) — 24 bytes (6× float32 T60 values)
  ├── Char 0xFFB3: Freq Response (read) — 240 bytes (60× float32, 1/3-octave bands)
  ├── Char 0xFFB4: Room Modes (read/notify) — 32 bytes (8× struct {freq_u16, decay_u16, type_u8})
  ├── Char 0xFFB5: Clarity (read/notify) — 28 bytes (6× C50 + 6× C80, int8 dB)
  ├── Char 0xFFB6: NC Curve (read) — 32 bytes (16× uint8 dB SPL per 1/3-octave)
  ├── Char 0xFFB7: Device Status (read/notify) — uint8 (0=idle, 1=measuring, 2=streaming, 3=error)
  └── Char 0xFFB8: Battery Level (read) — uint8 (%)
```

BLE advertising packet (31 bytes):
```
[Flags] [Complete 16-bit UUID: FFB0] [Mfr-specific: status(1), battery%(1), last_rt60_500Hz(2)]
```

---

## Wi-Fi REST API

When Wi-Fi is enabled (hold MODE button during boot), the Echo Mote hosts a tiny HTTP server:

```
GET  /api/status        → JSON: {status, battery, last_measurement}
POST /api/measure       → JSON: {mode: "rt60"|"freq"|"modes"|"clarity"|"noise"}
GET  /api/results       → JSON: {rt60, freq, modes, clarity, nc}
GET  /api/impulse_resp  → Binary: 4s × 48kHz × 2ch × 16bit = 768 KB (raw impulse response)
GET  /api/waterfall      → JSON: {frequencies[], magnitudes[]} (1/24-octave resolution)
```

---

## Air-Density Compensation

Speed of sound varies with temperature:

```
c = 331.3 × sqrt(1 + T/273.15)  m/s
```

The BME280 provides temperature (and humidity for slight correction). This is used to:
1. Convert time-domain IR delays to physical distances (e.g., first reflection distance)
2. Correct room mode frequency estimates for actual speed of sound
3. Report air absorption coefficients at measured humidity

---

## Mechanical

- PCB: 85 × 54 mm (credit-card form factor), 1.6 mm FR4, 4-layer
- Height: 12 mm (components) + 4 mm speaker = 16 mm total
- Speaker: 28 mm round, mounted in center cutout with acoustic porting
- Mic array: 2× ICS-43434, 40 mm spacing (approximate human ear spacing), top edge of PCB
- LCD: 1.3" IPS mounted above speaker, 4 mounting screws
- Buttons: 3 tactile switches on right edge (thumb-operable)
- Top: USB-C port for charging + programming
- Bottom: battery pocket + rubber feet
- Enclosure: optional 3D-printed snap-fit case (files in `hardware/`)
- Weight: 45 g (PCB + battery + LCD)

Acoustic design considerations:
- Speaker porting: 2 mm slot on bottom edge couples speaker to surface for boundary reinforcement
- Mic baffles: 3 mm raised acoustic baffles around each MEMS mic reduce wind/handling noise
- Vibration isolation: 4× silicone grommet feet decouple PCB from surface vibrations

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── app_main.c            # Entry point, NVS init, button handlers, state machine
│   ├── chirp_generator.c     # Log swept-sine synthesis + inverse chirp precomp
│   ├── chirp_generator.h
│   ├── i2s_manager.c         # Dual I²S bus init, DMA capture, speaker output
│   ├── i2s_manager.h
│   ├── impulse_response.c   # Cross-correlation, deconvolution, IR extraction
│   ├── impulse_response.h
│   ├── acoustic_params.c    # RT60, C50, C80, D50 computation per octave
│   ├── acoustic_params.h
│   ├── room_modes.c         # Low-frequency mode scanning + classification
│   ├── room_modes.h
│   ├── noise_analyzer.c     # Background NC curve estimation
│   ├── noise_analyzer.h
│   ├── lcd_display.c        # ST7789V driver, UI rendering, bar graphs
│   ├── lcd_display.h
│   ├── ble_service.c        # GATT server, measurement results
│   ble_service.h
│   ├── wifi_server.c        # HTTP REST API server
│   ├── wifi_server.h
│   ├── bme280_driver.c      # T/H/P sensor driver
│   ├── bme280_driver.h
│   ├── power_manager.c      # Deep sleep, battery monitoring, charge status
│   └── power_manager.h
├── components/
│   └── dsp/
│       ├── dsps_fft2r.h     # ESP-DSP FFT routines (from ESP-IDF component)
│       └── dsps_fft2r.c
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow

```c
void app_main(void) {
    nvs_init();
    i2c_bus_init();
    bme280_init();
    i2s_manager_init();       // Dual I²S: TX (speaker) + RX (mics L/R)
    lcd_display_init();
    ble_service_init();
    chirp_generator_init();   // Precompute inverse chirp in PSRAM
    power_manager_init();

    // Register button handlers
    gpio_isr_handler_add(BTN_MEASURE, measure_isr, NULL);
    gpio_isr_handler_add(BTN_MODE, mode_isr, NULL);
    gpio_isr_handler_add(BTN_POWER, power_isr, NULL);

    // Main loop
    while (true) {
        if (measure_pending) {
            measure_pending = false;
            run_measurement(current_mode);
        }
        lcd_display_idle_screen();  // Battery, last mode, prompt
        power_manager_light_sleep(100);  // 100 ms wake for button poll
    }
}

void run_measurement(measure_mode_t mode) {
    float temp, hum;
    bme280_read(&temp, &hum, NULL);
    float speed_of_sound = 331.3f * sqrtf(1.0f + temp / 273.15f);

    lcd_display_measuring(mode);

    // Mute amp during setup, then unmute
    gpio_set_level(AMP_SD, 0);  // Mute
    i2s_manager_start_capture(48000, mode == MODE_NOISE ? 30 : 8);

    if (mode != MODE_NOISE) {
        gpio_set_level(AMP_SD, 1);  // Unmute
        chirp_generator_play(mode);  // Swept sine / mode pings
        vTaskDelay(pdMS_TO_TICKS(mode == MODE_ROOM_MODES ? 25000 : 8000));
        gpio_set_level(AMP_SD, 0);  // Mute
    } else {
        vTaskDelay(pdMS_TO_TICKS(30000));  // 30 s ambient capture
    }

    // Stop capture
    int16_t *captured_l, *captured_r;
    uint32_t num_samples;
    i2s_manager_stop_capture(&captured_l, &captured_r, &num_samples);

    // Process
    float *impulse_l = impulse_response_extract(captured_l, num_samples);
    float *impulse_r = (mode != MODE_NOISE) ? 
                        impulse_response_extract(captured_r, num_samples) : NULL;

    acoustic_results_t results = {0};

    switch (mode) {
    case MODE_RT60:
        acoustic_params_compute_rt60(impulse_l, num_samples, speed_of_sound, &results);
        break;
    case MODE_FREQ:
        acoustic_params_compute_freq_response(impulse_l, num_samples, &results);
        break;
    case MODE_ROOM_MODES:
        room_modes_detect(captured_l, num_samples, speed_of_sound, &results);
        break;
    case MODE_CLARITY:
        acoustic_params_compute_clarity(impulse_l, num_samples, &results);
        break;
    case MODE_NOISE:
        noise_analyzer_compute_nc(captured_l, num_samples, &results);
        break;
    }

    // Display + BLE notify
    lcd_display_results(mode, &results);
    ble_service_notify_results(mode, &results);

    // Free capture buffers
    free(captured_l);
    free(captured_r);
    free(impulse_l);
    free(impulse_r);
}
```

---

## LCD UI Screens

### Idle Screen
```
┌────────────────────┐
│  ECHO MOTE         │
│  ■■■■■□□□ 75%      │
│                    │
│  Mode: RT60        │
│  Press ● to measure│
│                    │
│  24.3°C  48% RH    │
└────────────────────┘
```

### Measuring Screen
```
┌────────────────────┐
│  MEASURING RT60... │
│  ▓▓▓▓▓▓▓▓░░ 80%   │
│                    │
│  ♪ Chirp playing   │
│  → 3.2s elapsed    │
│                    │
│  ■■■■■□□□ 75%      │
└────────────────────┘
```

### RT60 Results Screen
```
┌────────────────────┐
│  RT60 Results      │
│  125Hz: 0.82s ██▌  │
│  250Hz: 0.71s ██▏  │
│  500Hz: 0.63s ███▌ │
│  1kHz:  0.58s ███▏ │
│  2kHz:  0.49s ████ │
│  4kHz:  0.38s █████│
│  Avg: 0.60s        │
└────────────────────┘
```

### Frequency Response Screen
```
┌────────────────────┐
│  Frequency Response│
│  20  50 200 1k 8k20│
│  │   ╱╲  ╱╲   ╱  ││
│  │  ╱  ╲╱  ╲ ╱   ││
│  │ ╱        ╲╱    ││
│  │╱              ╲ ││
│  ───────────────── │
│  ±6 dB range      │
└────────────────────┘
```

---

## DSP Implementation Details

### FFT Configuration

- Sample rate: 48 kHz (captures up to 24 kHz, well above 20 kHz requirement)
- FFT size: 32768 points (for 5-second deconvolution, ~0.68 Hz resolution)
- Data type: int16_t capture → float32_t processing
- Memory: 32768 × 4 bytes × 2 channels = 256 KB for captured audio (fits in PSRAM)
- Inverse chirp: 32768 × 4 bytes = 128 KB (stored in flash, loaded to PSRAM at init)
- Impulse response: 4 s × 48000 × 4 bytes = 768 KB per channel (PSRAM)

### Overlap-Save Deconvolution

Direct FFT of 5-second buffers (240,000 samples) is too large for a single FFT. We use overlap-save with 32,768-point FFTs:

1. Divide captured signal into 32,768-sample blocks with 16,384-sample overlap
2. Zero-pad inverse chirp to 32,768 points
3. FFT each block → multiply by FFT(inverse_chirp) → IFFT
4. Discard first 16,384 samples of each IFFT output (circular convolution artifacts)
5. Concatenate valid outputs → full impulse response

### Octave-Band Filtering

RT60 and clarity metrics require octave-band filtering. We use 6th-order Butterworth bandpass filters (12 dB/octave rolloff):

| Band | Center | Lower | Upper |
|------|--------|-------|-------|
| 1 | 125 Hz | 88 Hz | 177 Hz |
| 2 | 250 Hz | 177 Hz | 354 Hz |
| 3 | 500 Hz | 354 Hz | 707 Hz |
| 4 | 1 kHz | 707 Hz | 1414 Hz |
| 5 | 2 kHz | 1414 Hz | 2828 Hz |
| 6 | 4 kHz | 2828 Hz | 5657 Hz |

Filter coefficients are precomputed and stored in flash. Biquad cascade implementation runs in SRAM.

### Schroeder Backward Integration

RT60 is computed from the octave-filtered impulse response using Schroeder's method:

1. Compute energy decay curve: `E(t) = 10 × log10(∫t^∞ h²(τ)dτ / ∫0^∞ h²(τ)dτ)`
2. Start from the end of the IR, integrate backwards
3. Fit a line to the -5 dB to -35 dB portion (T30) or -5 dB to -25 dB (T20)
4. Extrapolate to -60 dB for T60

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | ESP32-S3-WROOM-1-N8R8 | Module | 1 | $3.80 | Dual-core 240MHz, 8MB PSRAM |
| 2 | ICS-43434 | LGA-6 | 2 | $1.80 | MEMS mic, I²S, -26 dBFS sensitivity |
| 3 | MAX98357A | QFN-16 | 1 | $1.20 | I²S DAC + 3W Class-D amp |
| 4 | 28 mm Speaker | Round | 1 | $0.80 | 8Ω, 0.5W, front-firing |
| 5 | ST7789V 1.3" IPS | Module | 1 | $2.50 | 240×240, SPI, 4-wire |
| 6 | BME280 | LGA-8 | 1 | $2.00 | T/H/P for air-density comp |
| 7 | MCP73831 | SOT-23-5 | 1 | $0.40 | Lipo charger, 500 mA |
| 8 | AP2112-3.3 | SOT-223 | 1 | $0.30 | LDO, 600 mA |
| 9 | Lipo 800 mAh | Pouch | 1 | $3.00 | 3.7V, with protection PCB |
| 10 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Power + data |
| 11 | WS2812B-2020 | 2020 | 1 | $0.15 | Status RGB LED |
| 12 | Tactile switch 6×6 | SMD | 3 | $0.15 | Measure, Mode, Power buttons |
| 13 | NTC 10kΩ | 0402 | 1 | $0.05 | Battery temperature sense |
| 14 | Resistors/caps | 0402 | ~40 | $0.60 | Pullups, decoupling, dividers |
| 15 | PCB 4-layer 85×54mm | Rect | 1 | $2.00 | JLCPCB |

**Total estimated BOM: ~$18.10** (qty 1)

---

## Directory Structure

```
echo-mote/
├── README.md                  # This file
├── schematic/
│   ├── echo_mote.kicad_sch
│   ├── echo_mote.kicad_pcb
│   └── echo_mote.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── app_main.c
│   │   ├── chirp_generator.c
│   │   ├── chirp_generator.h
│   │   ├── i2s_manager.c
│   │   ├── i2s_manager.h
│   │   ├── impulse_response.c
│   │   ├── impulse_response.h
│   │   ├── acoustic_params.c
│   │   ├── acoustic_params.h
│   │   ├── room_modes.c
│   │   ├── room_modes.h
│   │   ├── noise_analyzer.c
│   │   ├── noise_analyzer.h
│   │   ├── lcd_display.c
│   │   ├── lcd_display.h
│   │   ├── ble_service.c
│   │   ├── ble_service.h
│   │   ├── wifi_server.c
│   │   ├── wifi_server.h
│   │   ├── bme280_driver.c
│   │   ├── bme280_driver.h
│   │   ├── power_manager.c
│   │   └── power_manager.h
│   ├── components/
│   │   └── dsp/
│   │       ├── dsps_fft2r.h
│   │       └── dsps_fft2r.c
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── hardware/
│   └── BOM.csv
├── scripts/
│   ├── plot_results.py
│   ├── calibrate_mics.py
│   └── generate_chirp.py
└── docs/
    ├── assembly_guide.md
    ├── api_reference.md
    └── measurement_theory.md
```

---

## Getting Started

### Flash Firmware

```bash
# Install ESP-IDF v5.3+
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/echo-mote/firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

### Take a Measurement

1. Place Echo Mote on a stable surface (table, tripod, or floor)
2. Press MODE to select measurement type (RT60, FREQ, MODES, CLARITY, NOISE)
3. Press MEASURE — the device chirps and records
4. Read results on the LCD or via BLE/Wi-Fi

### Read Results via BLE (Python)

```bash
pip install bleak
python3 scripts/plot_results.py --mac AA:BB:CC:DD:EE:FF --mode rt60
```

### Generate Custom Chirp

```python
# Custom chirp with different frequency range or duration:
python3 scripts/generate_chirp.py --fmin 50 --fmax 16000 --duration 3.0
# Output: inverse_chirp.bin → copy to firmware/components/dsp/
```

### Calibrate Microphones

```bash
# Place device in anechoic chamber (or quiet outdoor open space)
# Runs white noise and measures mic response for matching:
python3 scripts/calibrate_mics.py --port /dev/ttyUSB0
```

---

## Calibration

### Speaker Level Calibration

The factory speaker output is ~75 dB SPL at 1 m. For precise measurements, calibrate against a reference SPL meter:

1. Place SPL meter 1 m from Echo Mote speaker
2. Hold MEASURE button for 3 seconds → enters calibration mode
3. Device plays 1 kHz tone at maximum volume
4. Use USB-C console: `cal spm <measured_dB>` (e.g., `cal spm 78.5`)
5. Offset stored in NVS, applied to all future measurements

### Microphone Sensitivity Matching

The dual MEMS mics are factory-matched to ±1 dB. For critical IACC measurements, a software calibration matches them:

1. Play pink noise from the speaker
2. Both mics capture simultaneously
3. Compute magnitude ratio per band
4. Store compensation factors in NVS
5. Apply in all future captures

---

## Serial Console Commands

USB-C serial console at 115200 baud, 8N1:

```
> measure rt60          # Start RT60 measurement
> measure freq          # Start frequency response measurement
> measure modes         # Start room mode scan
> measure clarity       # Start clarity measurement
> measure noise         # Start NC measurement
> cal spm <dB>          # Calibrate speaker SPL
> cal mic               # Calibrate mic matching
> wifi start <ssid> <pass>  # Connect to Wi-Fi
> wifi stop             # Disconnect Wi-Fi
> ble start             # Start BLE advertising
> ble stop              # Stop BLE advertising
> sleep                 # Enter deep sleep
> status                # Show device status
> results               # Show last measurement results
```

---

## Companion App

The Python `plot_results.py` script provides a quick companion experience:

```bash
# Real-time RT60 measurement with live plot
python3 scripts/plot_results.py --mac AA:BB:CC:DD:EE:FF --mode rt60 --live

# Export frequency response as CSV
python3 scripts/plot_results.py --mac AA:BB:CC:DD:EE:FF --mode freq --export freq_response.csv

# Compare two rooms
python3 scripts/plot_results.py --compare room1.json room2.json
```

---

## License

MIT — build it, sell it, improve it.

---

*Invented 2026-06-15 by [jayis1](https://github.com/jayis1) — SoC Device Inventions.*