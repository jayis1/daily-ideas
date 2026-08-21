# Melody Sprite — Assembly Guide

## Overview

This guide walks you through assembling a Melody Sprite from a bare PCB and components. Estimated time: 2–3 hours for experienced builders, 4–5 hours for beginners.

## Tools Required

| Tool | Purpose |
|------|---------|
| Soldering iron (temperature-controlled) | All soldering |
| Solder (0.5mm, 60/40 or lead-free) | Component attachment |
| Flux pen or paste | SMD soldering aid |
| Tweezers (ESD-safe, fine tip) | Placing 0402 components |
| Multimeter | Continuity and voltage checks |
| Magnifying lens or loupe | Inspecting joints |
| PCB vise or helping hands | Holding PCB during soldering |
| Isopropyl alcohol (99%) | Cleaning flux residue |
| USB-C cable | Power and programming |
| Computer with USB port | Firmware flashing |

## Assembly Order

### Phase 1: Power Supply (Bottom-Up)

1. **LDO (U3 — AP2112K-3.3)**
   - Solder the SOT-23-5 package on the bottom of the PCB
   - Pin 1 (VIN) faces the battery connector
   - Verify: 3.3V output when USB-C is connected

2. **LiPo Charger (U2 — MCP73831)**
   - Solder the SOT-23-5 package
   - Add the 5.1kΩ PROG resistor (R1) — sets charge current to 200mA
   - Add 10µF input and output capacitors

3. **USB-C Connector (J1)**
   - Solder the SMD USB-C receptacle
   - This is the most mechanically stressed component — use plenty of solder on the shield tabs
   - Verify: 5V on VBUS when USB-C cable is plugged in

4. **Battery Connector (J2)**
   - Solder the JST-PH 2-pin connector
   - Observe polarity! Red = VBAT, Black = GND
   - **Do NOT connect the battery yet**

5. **Power Test #1**
   - Connect USB-C power
   - Measure 3.3V on the 3V3 test point
   - Measure ~4.2V on VBAT test point (charger output)
   - If voltages are wrong, debug before proceeding

### Phase 2: RP2040 and Flash

6. **RP2040 (U1)**
   - Apply flux to the QFN-56 pads
   - Align the IC (pin 1 dot in corner)
   - Solder using drag-soldering or hot air
   - This is the hardest part — take your time

7. **Crystal (Y1 — 12MHz)**
   - Solder the 3225 SMD crystal
   - Add 22pF load capacitors (C1, C2)

8. **Boot Button (SW1)**
   - Solder the tactile switch

9. **External Flash (U9 — W25Q16)**
   - Solder the SOIC-8 flash chip
   - Verify with a continuity check

10. **Power Test #2**
    - Connect USB-C
    - Hold BOOTSEL and press reset (or plug in while holding BOOTSEL)
    - The RP2040 should appear as a USB mass storage device
    - If it doesn't, check soldering on the RP2040

### Phase 3: Decoupling and Passives

11. **Decoupling Capacitors**
    - Solder all 100nF bypass caps near IC power pins (8 total)
    - Solder 10µF bulk caps (4 total)
    - Solder 1µF caps near MCP73831

12. **Pull-up Resistors**
    - 4.7kΩ I2C pull-ups (R2 on SDA, R3 on SCL)
    - 10kΩ pull-ups on encoder and IRQ lines

13. **Voltage Divider**
    - 100kΩ resistors for VSYS monitor (GPIO24)

### Phase 4: Audio Section

14. **I2S DAC (U4 — PCM5102A)**
    - Solder the TSSOP-20 package
    - Add decoupling caps near the IC
    - Connect FMT pin to GND (I2S mode)
    - Connect XSMT pin to 3.3V (unmute)

15. **Class-D Amplifier (U5 — MAX98357A)**
    - Solder the QFN-16 package
    - Connect GAIN pin to GND (9dB gain)
    - Connect SD_MODE to 3.3V (left channel mono)

16. **Speaker Connector (J3)**
    - Solder through-hole 2-pin header for 8Ω speaker
    - Or solder speaker wires directly

17. **Headphone Jack (J4)**
    - Solder the 3.5mm stereo switched jack
    - The jack switch disconnects the speaker when headphones are plugged in

### Phase 5: Capacitive Touch

18. **MPR121 #1 (U6 — Keyboard)**
    - Solder the QFN-20 package
    - This is I2C address 0x5A
    - Connect IRQ pin to GPIO14

19. **MPR121 #2 (U7 — Function Buttons)**
    - Solder the QFN-20 package
    - This is I2C address 0x5B ( ADDR pin tied high)
    - Connect IRQ pin to GPIO15

20. **Touch Pads**
    - The 16 keyboard pads and 8 function button pads are etched on the PCB
    - No additional soldering needed
    - For best touch sensitivity, avoid conformal coating on these areas

### Phase 6: OLED Display

21. **SSD1306 OLED Module (U8)**
    - Solder the 0.96" OLED module using the header footprint
    - Connect via I2C (shared bus with MPR121s)
    - Pin connections: VCC→3.3V, GND→GND, SCL→GPIO9, SDA→GPIO8

### Phase 7: Controls

22. **Potentiometers (RV1–RV4)**
    - Insert the four PTV09A potentiometers from the top of the PCB
    - Solder all three pins of each pot
    - Add knobs after testing

23. **Rotary Encoder (SW2)**
    - Solder the PEC11R encoder
    - Connect A→GPIO10, B→GPIO11, SW→GPIO12

24. **Status LEDs (D1, D2)**
    - Solder the blue (D1) and green (D2) 0603 LEDs
    - Add 1kΩ current-limiting resistors

### Phase 8: Final Assembly

25. **Battery**
    - Connect the 800mAh LiPo battery to J2
    - Verify charging: LED should indicate charging status

26. **Speaker**
    - Connect the 8Ω 40mm speaker to J3
    - Or use the headphone jack for private listening

27. **Enclosure**
    - Place the assembled PCB in the enclosure
    - Secure with M2 screws through the mounting holes
    - The capacitive touch pads should be accessible from outside

## Firmware Flashing

1. Download the latest `melody_sprite.uf2` from the releases page
2. Hold the BOOTSEL button on the PCB
3. Connect USB-C to your computer
4. Release BOOTSEL — the RP2040 appears as a USB drive
5. Copy `melody_sprite.uf2` to the drive
6. The device automatically reboots into the synthesizer firmware

## Initial Calibration

1. Power on the device
2. The OLED shows the boot splash screen
3. Wait 1.5 seconds for initialization
4. The display switches to waveform mode
5. Touch any key to verify audio output
6. Adjust potentiometers to hear parameter changes
7. If touch sensitivity is off, run the calibration script:
   ```
   python scripts/calibrate_touch.py
   ```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No display | I2C wiring or OLED power | Check I2C bus with scanner script |
| No sound | I2S wiring or DAC power | Verify 3.3V on PCM5102A VDD |
| Touch not responding | MPR121 I2C address or IRQ | Check I2C address with scanner |
| Distorted audio | Grounding or decoupling | Add 100nF caps near audio ICs |
| Battery not charging | MCP73831 wiring | Verify PROG resistor value |
| RP2040 not recognized | Boot mode or soldering | Check QFN soldering with loupe |

## Safety Warnings

- **Never short the battery terminals**
- **Never charge beyond 4.2V** (the MCP73831 handles this automatically)
- **Disconnect battery before soldering near the power section**
- **The MAX98357A can produce 3W — start with low volume**