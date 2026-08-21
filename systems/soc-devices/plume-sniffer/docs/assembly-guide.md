# Plume Sniffer — Assembly Guide

This guide walks through building a Plume Sniffer from the BOM. No special
skills beyond through-hole/SMD soldering and basic mechanical assembly are
required. Expect ~4–6 hours for a first build.

## Tools Needed

- Soldering iron (fine tip) + solder + flux
- Hot-air station (for SMD passives — optional but recommended)
- Digital multimeter
- Small bench vise / third-hand
- Tubing bender (or just careful hand-bending of 1/16" SS tubing)
- PTFE ferrule crimper (or just finger-tight + 1/4 turn with a wrench)
- Calipers
- 3D printer (for the enclosure) or a printing service
- Precision scale (0.1 mg) for packing Tenax TA — optional, a measuring
  scoop marked for 20 mg works fine

## Step 1: PCB Fabrication

Send `schematic/plume_sniffer.kicad_pcb` to JLCPCB / PCBWay / OSH Park.
Order a 4-layer board, 1.6 mm thickness, 1 oz copper, in the 142 × 36 mm
form factor. The layer stackup:

| Layer | Purpose |
|-------|---------|
| Top   | Signal + component pads |
| L2    | GND plane (solid) |
| L3    | Power plane (3.3V + 1.8V split) |
| Bottom | Signal + heater MOSFET pours |

## Step 2: Solder SMD Components

Work from smallest to largest:

1. **Passives** — 0805 resistors, capacitors. Use a stencil + paste or
   hand-solder with fine-tipped iron. Pay attention to:
   - 10 kΩ pull-ups on I2C (SDA/SCL)
   - NTC divider resistors (10 kΩ to 3.3 V, NTC to GND)
   - Battery voltage divider (100 kΩ / 100 kΩ, 2:1)
   - 100 Ω gate resistors on heater MOSFETs
2. **ICs** — ESP32-C3-MINI-1 (U1), ADS122U04 (U2), BME280 (U4), TP4056 (U6),
   MCP1640B (U7), AP2112 (U8), LP5907 (U9). Use hot-air for the QFN/BGA
   packages. The ESP32-C3-MINI-1 is a castellated module — solder the
   edge pads with plenty of flux and drag-solder the perimeter.
3. **MOSFETs** — IRLML2502 (Q1–Q4), SOT-23. These carry up to ~1 A for the
   heaters; add a copper pour on the bottom layer as a heat sink.
4. **Connectors** — USB-C (J1), microSD slot (J2), OLED header (if using
   a breakout; solder directly if using a bare SSD1306 panel).

## Step 3: Mechanical / Fluidic Assembly

This is the most fiddly part. Take your time.

### 3a. Coil the Column

1. Cut 1 m of 1/16" OD × 0.75 mm ID stainless steel tubing.
2. Gently coil it around a 35 mm diameter mandrel (a socket wrench
   extension works well) — 3 full loops.
3. The column is pre-packed (bought from Restek as a micro-packed OV-101
   column). If you're packing it yourself:
   - Silanize the empty tube (rinse with 5% DMDCS in toluene, dry at
     120 °C for 1 h).
   - Plug the outlet end with silanized glass wool (5 mm).
   - Pour in 5% OV-101 on Chromosorb WHP (80/100 mesh) while vibrating
     the tube with a sonic toothbrush.
   - Plug the inlet end with glass wool.

### 3b. Prepare the Preconcentrator

1. Cut 30 mm of 1/16" SS tubing.
2. Plug one end with silanized glass wool.
3. Weigh 20 mg Tenax TA (60/80 mesh) and pour it in.
4. Plug the other end with glass wool.

### 3c. Wind the Heaters

1. **Column heater**: Wrap 0.1 mm nichrome-60 wire around the column
   coil. Space the turns ~3 mm apart. Total length ~2 m → ~24 Ω → ~1 W
   at 5 V (you need more power; use two parallel strands for ~12 Ω,
   giving ~4 W at 5 V / 2.1 A — check your MOSFET rating).
   - Insulate with Kapton tape between the wire and the SS tube (the
     tube is grounded; the nichrome must not short to it).
2. **Preconcentrator heater**: Wrap nichrome around the 30 mm tube,
   ~0.5 m length → ~6 Ω → ~2.5 W at 5 V. Kapton-insulate.

### 3d. Mount the NTC Thermistors

1. **TH1 (column)**: Epoxy the 10 kΩ NTC bead to the column coil, on
   the underside, midway along the length. Cover with a small piece of
   aerogel blanket.
2. **TH2 (preconcentrator)**: Epoxy to the preconcentrator tube, midway.
3. **TH3 (TCD body)**: Epoxy to the MEMS TCD cell housing.

### 3e. Assemble the Flow Path

1. Connect: Carbon filter → Pump → 3-way valve → Preconcentrator →
   Column → TCD → Exhaust trap.
2. Use PTFE ferrules at every SS-to-SS connection. Finger-tight + 1/4
   turn with a 6 mm wrench. Do not overtighten — the ferrule will deform
   and seal.
3. The 3-way valve: common port → preconcentrator inlet; port A →
   sample inlet (with a PTFE sample filter); port B → carbon filter
   (carrier gas).

### 3f. Mount the MEMS TCD

1. Solder the MEMS TCD cell to the PCB (it's a small SMD module with 4
   pads: Vexc+, Vexc−, Vout+, Vout−).
2. Wire Vexc to the 1.8 V rail (through the ADS122U04 IDAC), Vout to
   ADS122U04 AIN0/AIN1 (differential).
3. The TCD cell must be thermally stable — mount it on a small copper
   block if using the optional Peltier, or just float it in the aerogel
   insulation with the reference filament sealed in carrier gas.

## Step 4: Enclosure

1. 3D print the enclosure (`enclosure.stl` — not included in this repo;
   design a flashlight-style tube, 142 × 36 mm ID, with end caps).
2. The heated zone (column + preconcentrator) sits in the middle third,
   wrapped in 5 mm aerogel blanket, inside an aluminum tube liner.
3. The PCB sits in the rear third with the battery; the pump and valve
   in the front third.
4. Drill ventilation holes for the cooldown blower.

## Step 5: First Power-Up

1. **Do not insert a battery yet.** Connect USB-C and verify:
   - TP4056 CHRG LED is on (charging).
   - 3.3 V rail measures 3.30 ± 0.05 V.
   - 1.8 V rail measures 1.80 ± 0.05 V.
   - 5.0 V boost rail measures 5.0 ± 0.1 V (only when battery is
     present — the MCP1640B needs a battery input).
2. Insert a charged 18650. Verify the boost rail now reads 5.0 V.
3. Press the RUN button — the OLED should show "PLUME SNIFFER" then the
   menu. If the OLED is blank, check I2C wiring (SDA=GPIO1, SCL=GPIO0).

## Step 6: Firmware Flash

```bash
cd plume-sniffer/firmware
idf.py set-target esp32c3
idf.py menuconfig   # verify BLE enabled, flash size 4MB
idf.py build
idf.py flash -p /dev/ttyUSB0 -b 460800
idf.py monitor -p /dev/ttyUSB0
```

You should see boot logs for each subsystem. The OLED should show the
menu after ~2 seconds.

## Step 7: Leak Test

Before the first run, leak-test the flow path:

1. Cap the sample inlet and exhaust.
2. Turn on the pump (you can do this from the menu — or just run the
   pump at 100% via a test command).
3. The pump should pressurize the system. Listen for hissing. Soap-test
   every ferrule connection.
4. A small leak will ruin chromatography — all connections must be
   gas-tight.

## Step 8: n-Alkane Calibration

Before field use, calibrate the Kovats retention-index anchors:

1. Prepare a headspace vial with a few drops each of pentane, hexane,
   heptane, octane, nonane, decane (C5–C10 is sufficient for most
   volatiles; C11–C16 for semivolatiles).
2. Run the `M_ETHOS` method with 250 mL sample from the vial headspace.
3. Note the retention times of each alkane peak (they're evenly spaced
   and easy to identify).
4. Run `scripts/alkane_cal.py` to compute and upload the anchors to the
   device via BLE.

After calibration, the device is ready for field use.

---

*Questions? Open an issue at the
[SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions)
repo.*