# Soil Whisper — Assembly Guide

## Overview

This guide walks you through assembling the Soil Whisper soil intelligence probe, from PCB fabrication to final deployment in the field.

## Prerequisites

### Skills Required
- Surface-mount soldering (QFN-48, TSSOP, SOIC packages)
- Through-hole soldering (supercapacitor, DS18B20 probes)
- Basic KiCad proficiency (for any design modifications)
- Patience with waterproofing (this is an IP68 device)

### Tools Required
| Tool | Purpose |
|------|---------|
| Soldering iron (fine tip, 300-350°C) | SMD and through-hole soldering |
| Hot air rework station | QFN-48 (STM32WL55JC) placement |
| Solder paste + stencil | Consistent SMD solder joints |
| Multimeter (continuity + voltage) | Debugging |
| Oscilloscope (2+ channel, 50 MHz) | Verifying 555 oscillators and 1-Wire |
| ST-Link v2 programmer | Flashing firmware |
| KiCad 8+ | Schematic/PCB modifications |
| Torx T8 driver | Opening the stake tube |
| Epoxy resin (marine grade) | Waterproofing probe windows |
| Crimp tool (JST-SH) | Sensor cable connectors |

### Parts

See `hardware/BOM.csv` for the complete bill of materials. Total cost is approximately **$350** including the NPK/pH ion-selective electrodes.

**Tip:** The ion-selective electrodes (NO₃⁻, H₂PO₄⁻, K⁺) and pH glass electrode are the most expensive components. They are also replaceable via BNC connectors, so you can start with just moisture/temperature sensing and add NPK/pH later.

## Step 1: PCB Fabrication

1. Generate Gerber files from the KiCad project:
   ```bash
   cd schematic/
   kicad-cli pcb export gerber soil-whisper.kicad_pcb
   kicad-cli pcb export drill soil-whisper.kicad_pcb
   ```

2. Order from JLCPCB (or equivalent):
   - **Layers:** 4
   - **Thickness:** 1.6 mm
   - **Finish:** ENIG (for the ISE electrode contacts)
   - **Color:** Green
   - **Size:** 50 mm × 200 mm (matches stake tube inner diameter)
   - **Surface:** HASL Lead-Free is acceptable, but ENIG provides better corrosion resistance

3. Also order the **capacitive moisture sensing boards** (3 each):
   - These are separate 2-layer PCBs (20 mm × 40 mm) with interdigitated traces
   - The 555 oscillator circuits are on the main board; the sensing pads connect via 2-wire cable
   - See the `schematic/` folder for the moisture probe PCB design

## Step 2: SMD Assembly

### 2a. Apply Solder Paste

1. Use the stencil to apply solder paste to the main PCB
2. Inspect under magnification for consistent paste deposits
3. Pay special attention to the QFN-48 pads (STM32WL55JC) — avoid bridges

### 2b. Place Components

Place components in this order (smallest to largest):

| Order | Reference | Package | Notes |
|-------|-----------|---------|-------|
| 1 | C3-C6, C9, R1-R2 | 0402 | Smallest passives first |
| 2 | C7-C8 | 0603 | Bulk caps |
| 3 | C2 | 1206 | Buck-boost filter cap |
| 4 | LED1-LED3 | 0402 | Status LEDs |
| 5 | U14 (TPS7A02) | SOT-23-5 | LDO |
| 6 | Q1 (SI2301DS) | SOT-23 | P-Channel MOSFET |
| 7 | U7-U8 (TLV8542) | TSSOP-8 | Op-amps |
| 8 | U2 (ADS1115) | TSSOP-10 | ADC |
| 9 | U4-U6 (TLC555) | SOIC-8 | Timers |
| 10 | U3 (CD74HC4067) | TSSOP-24 | Multiplexer |
| 11 | U13 (BQ25570) | VQFN-14 | Solar harvester |
| 12 | U1 (STM32WL55JC) | QFN-48 | Main SoC — **most critical** |
| 13 | U9 (SHT40) | DFN-4 | Humidity sensor |

### 2c. Reflow

1. Use hot air rework station or reflow oven
2. Profile: 150°C soak for 60s, then ramp to 250°C peak for 20s
3. Inspect under microscope for solder bridges, especially on QFN-48

### 2d. Touch-Up

1. Fix any bridges with solder wick
2. Add flux and reflow any cold joints
3. Verify continuity on critical nets (VDD, GND, I2C, SWD)

## Step 3: Through-Hole Assembly

1. **Supercapacitor (C1):** Solder the 10F supercapacitor to the board. Note polarity!
2. **DS18B20 probes (U10-U12):** Insert through TO-92 holes, bend leads to route along the stake
3. **Solar panel connector (J1):** Solder screw terminal for solar panel wires
4. **BNC connectors (J2-J5):** Solder BNC jacks for ISE and pH electrodes
5. **IPEX antenna connector (AE1):** Solder U.FL/IPEX connector for LoRa antenna
6. **Capacitive moisture probes:** Connect via JST-SH 2-pin connectors at depth markers

## Step 4: Waterproofing

This is the most critical step. The Soil Whisper must survive months submerged in wet soil.

### 4a. Probe Windows

1. The capacitive moisture sensing pads and DS18B20 probes must be exposed to soil
2. Apply a thin layer of marine-grade epoxy around the edges of each sensing pad
3. The DS18B20 stainless steel probes poke through sealed windows in the tube
4. Use silicone O-rings on all cable glands

### 4b. PCB Conformal Coating

1. Apply conformal coating (acrylic or silicone) to the entire PCB
2. **Exception:** Do NOT coat:
   - SHT40 humidity sensor opening
   - Antenna feed point
   - BNC connector contacts
3. Let cure for 24 hours

### 4c. Tube Assembly

1. Slide the PCB into the polycarbonate tube (Ø50mm × 600mm)
2. Align the moisture sensing windows and probe holes with the depth markers
3. Seal both ends with silicone O-rings and end caps
4. Route the solar panel wires through the top cap cable gland
5. Route the LoRa antenna wire through the top cap

## Step 5: Firmware Flashing

### 5a. Connect ST-Link

1. Connect ST-Link v2 to the SWD pads on the PCB:
   - **SWDIO** → PA13
   - **SWCLK** → PA14
   - **GND** → GND
   - **3.3V** → VDD (optional, for powering from ST-Link)

2. Verify connection:
   ```bash
   openocd -f interface/stlink.cfg -f target/stm32wlx.cfg -c "init; halt; exit"
   ```

### 5b. Flash Bootloader

```bash
cd firmware/
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain-arm-none-eabi.cmake ..
make -j$(nproc)
arm-none-eabi-objcopy -Oihex soil-whisper.elf soil-whisper.hex
openocd -f interface/stlink.cfg -f target/stm32wlx.cfg \
  -c "program soil-whisper.hex verify reset exit"
```

### 5c. Verify

1. Connect a USB-UART adapter to the debug UART (PA2=TX, PA3=RX, 115200 baud)
2. Power cycle the device
3. You should see:
   ```
   Soil Whisper v1.0 booting
   Waking sensors...
   Sampling complete
   LoRa TX complete
   Entering STOP2 sleep for 1800s
   ```

## Step 6: Calibration

### 6a. Moisture Calibration

```bash
# Connect serial console at 115200 baud
SOIL> cal moisture 0 air
  Moisture ch0 air: 21934 Hz → stored

SOIL> cal moisture 0 water
  Moisture ch0 water: 48723 Hz → stored

# Repeat for channels 1 and 2
SOIL> cal moisture 1 air
SOIL> cal moisture 1 water
SOIL> cal moisture 2 air
SOIL> cal moisture 2 water
```

### 6b. pH Calibration

Use pH 4.0 and pH 7.0 buffer solutions:

```bash
SOIL> cal ph 4.0
  pH 4.0: ADC=8234 → stored

SOIL> cal ph 7.0
  pH 7.0: ADC=13201 → stored
```

### 6c. NPK Calibration

Use standard solutions (e.g., 100 ppm for each ion):

```bash
SOIL> cal npk no3 100
  NO3⁻ 100ppm: ADC=18456 → stored

SOIL> cal npk po4 100
  H2PO4⁻ 100ppm: ADC=16234 → stored

SOIL> cal npk k 100
  K⁺ 100ppm: ADC=20112 → stored
```

## Step 7: Field Deployment

### 7a. Choose a Location

- Select a representative spot in the field
- Avoid areas with large rocks or compacted soil
- The solar panel should receive at least 4 hours of direct sunlight

### 7b. Insert the Probe

1. Use a soil corer or dibber to make a pilot hole (Ø55mm, 450mm deep)
2. Gently insert the stake into the pilot hole
3. Firm the soil around the stake to ensure good probe-to-soil contact
4. Ensure the solar panel is above ground level and oriented toward the equator

### 7c. LoRaWAN Gateway Setup

1. Set up a LoRaWAN gateway within range (up to 15 km rural / 2 km urban)
2. Register the Soil Whisper device in your LoRaWAN Network Server (TTN, ChirpStack, etc.)
3. Use ABP or OTAA provisioning with the keys in `firmware/main.c`
4. Configure an application integration to forward data to your dashboard

### 7d. Verify Data Flow

1. Force an immediate sample:
   ```bash
   SOIL> sample now
   ```
2. Check your LoRaWAN server for the uplink
3. Use the Python decoder script to parse the payload

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No serial output | Power issue | Check supercap voltage (should be > 2.5V) |
| Moisture reads 0% | 555 not oscillating | Check probe connections, verify with oscilloscope |
| pH stuck at 7 | Op-amp not powered | Check PB0 (NPK/pH power gate) |
| LoRa not joining | Wrong region/frequency | Verify 868/915 MHz match your gateway |
| Battery drops overnight | Solar panel disconnected or damaged | Check J1 connector and panel orientation |
| NPK readings drift | ISE electrodes need recalibration | Re-calibrate with standard solutions monthly |

## Maintenance

- **ISE electrodes:** Replace every 6-12 months (they degrade over time)
- **pH electrode:** Replace every 12-18 months
- **DS18B20 probes:** Should last 5+ years in soil
- **Supercapacitor:** Replace every 3-5 years (capacitance degrades)
- **Solar panel:** Clean monthly (dirt reduces efficiency)
- **Calibration:** Re-run monthly for pH, quarterly for NPK

## Safety Notes

- **Do NOT** touch the BNC connectors while the device is powered (high-impedance op-amp outputs)
- **Do NOT** submerge the solar panel
- **Always** disconnect the supercapacitor before servicing the PCB
- The BQ25570 can charge the supercap to 3.6V — treat it as a live power source