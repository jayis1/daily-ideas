# Assembly Guide — Phyto Pulse

## PCB Fabrication

1. **Order the 4-layer PCB** from JLCPCB (or similar):
   - Size: 80 × 50 mm, 4 layers, 1.6 mm thickness
   - Layers: F.Cu (signal) / In1.Cu (GND plane) / In2.Cu (VDD plane) / B.Cu (signal)
   - Minimum trace: 0.2 mm, minimum via: 0.6 mm / 0.3 mm drill
   - Upload the KiCad gerbers from `schematic/phyto_pulse.kicad_pcb`
   - Cost: ~$8 for 5 boards

2. **Solder components** in order (smallest to largest):
   - SMD passives (R, C, L) — 0805 package, use solder paste + hot plate or iron
   - ICs: STM32G474RET6 (LQFP-64), ESP32-C3-MINI-1, ADS1256 (SSOP-28), INA333 (MSOP-8), OPA2333 (SOIC-8), 74HC4051 (SOIC-16)
   - Power: MCP73831 (SOT-23-5), AP2112 (SOT-23-5), TPS7A02 (SOT-23-5)
   - Connectors: BNC jacks (×2), microSD socket, USB-C connector
   - Through-hole: tactile buttons (×3), 8 MHz crystal

3. **3D-print the enclosure**:
   - Two-piece case (top + bottom), snap-fit or screw
   - Cutouts for BNC jacks (left), USB-C (bottom), OLED window (top)
   - STL files in `hardware/` (generate from PCB dimensions)
   - PLA or PETG, 0.2 mm layer height

## Electrode Construction

Each electrode costs ~$1.50 and takes 10 minutes to build:

1. **Materials**:
   - Ag/AgCl pellet (A-M Systems 726775, 2 mm, ~$1.20)
   - 1 mL pipette tip (cut to 3 cm)
   - 30 AWG wire with header pin
   - KCl powder (Sigma P9333) + agar powder
   - BNC plug (solder the pellet wire to center pin)

2. **Assembly**:
   - Solder the Ag/AgCl pellet to the wire inside the pipette tip (pellet at the narrow end)
   - Prepare 0.1 M KCl + 2% agar solution: dissolve 0.745 g KCl + 2 g agar in 100 mL DI water, heat to 90°C while stirring
   - Fill the pipette tip with the KCl-agar solution while warm
   - Let cool to gel (the agar solidifies, holding the KCl in place)
   - Attach BNC plug to the wire end

3. **Storage**:
   - Keep electrodes in 0.1 M KCl solution when not in use
   - Replace gel every 1–2 weeks (dry gel → high impedance)
   - Clean the Ag/AgCl pellet with DI water between sessions

## Firmware Flashing

### STM32G474 (main MCU)

1. **Toolchain**: Install `arm-none-eabi-gcc` and `openocd`
   ```bash
   sudo apt install gcc-arm-none-eabi openocd
   ```

2. **Build**:
   ```bash
   cd firmware
   make -j8
   ```

3. **Flash via ST-Link V2**:
   - Connect ST-Link: SWDIO → PA13, SWCLK → PA14, GND → GND, 3.3V → 3.3V
   - Flash:
   ```bash
   make flash
   # or:
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
     -c "program build/phyto-pulse.bin exit 0x08000000"
   ```

4. **Alternative**: Use STM32CubeIDE — open `phyto-pulse.ioc`, build, flash

### ESP32-C3 (connectivity MCU)

1. **Toolchain**: Install ESP-IDF v5.x
   ```bash
   git clone --recursive https://github.com/espressif/esp-idf.git
   cd esp-idf && ./install.sh
   source export.sh
   ```

2. **Build + flash**:
   ```bash
   cd firmware/esp32-c3
   idf.py set-target esp32c3
   idf.py menuconfig   # verify: BT enabled, WiFi AP enabled
   idf.py build
   idf.py -p /dev/ttyUSB0 flash
   ```

## Initial Setup

1. **Insert microSD** card (FAT32, any size — 32 GB gives ~2800 hours of raw data)
2. **Charge** the battery via USB-C (LED red while charging, green when full)
3. **Attach electrodes** to a plant:
   - E1 (active): clip to the leaf blade or petiole
   - E2 (reference): clip to the stem
   - Wait 2–5 minutes for the electrode-plant interface to stabilize
4. **Power on** — press any button to wake from sleep
5. **Press RECORD** — the device auto-ranges gain, then starts recording
6. **Stimulate** the plant and watch spikes appear on the OLED
7. **Press RECORD** again to stop and save

## Calibration

The ADS1256 performs self-calibration on init. No user calibration needed for the analog front-end.

For the spike classifier, the int8 CNN weights need to be trained and flashed. See `scripts/train_cnn.py` for the training pipeline (TensorFlow → TFLM → C header).

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| No signal on OLED | Electrodes not making contact | Re-wet KCl gel; clean leaf surface |
| Baseline drifts > 50 mV | Electrode junction not stabilized | Wait longer (5+ min); replace gel |
| High noise (> 1 mV) | 60 Hz mains pickup | Move away from power lines; use shielded BNC cables |
| No SD card detected | Card not inserted or not FAT32 | Reformat card as FAT32 |
| Battery drains fast | ESP32-C3 Wi-Fi always on | Disable Wi-Fi in config menu (BLE-only mode) |
| OLED blank | I2C not connected | Check PB0/PB1 wiring; verify 3.3V power |
| CNN classifies all as "ART" | Weights not loaded (placeholder zeros) | Train and flash real weights |