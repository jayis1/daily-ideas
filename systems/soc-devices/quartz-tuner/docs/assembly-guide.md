# Quartz Tuner — Assembly Guide

## 1. Bill of Materials

See [`hardware/BOM.csv`](../hardware/BOM.csv) for the complete priced BOM. Total cost is approximately **$50 USD**.

## 2. PCB Layout Guidelines

### 2.1 Layer Stack (4-layer)

| Layer | Function |
|-------|----------|
| Top | Signal + component pads |
| Inner 1 | Ground plane (solid) |
| Inner 2 | Power plane (3V3) |
| Bottom | Signal + analog routing |

### 2.2 Critical Layout Rules

1. **π-Network fixture**: Place the 6× 12.5 Ω resistors and ZIF socket as close together as possible. The Si5351A CLK0 output should be within 10 mm of the first π-network resistor. The AD5933 VIN+/VIN- inputs should be within 10 mm of the last π-network resistor.

2. **Analog ground**: The AD5933 and its associated components (RFB, RSET, VIN+/VIN-) must have a clean analog ground. Use a star ground point near the AD5933's GND pin. Do not route digital switching signals under the AD5933.

3. **Separate analog 3V3A rail**: Route the LC-filtered 3V3A rail (L1 10 µH + C9 22 µF) as a separate power domain for the Si5351A and AD5933. Connect to the main 3V3 rail only at a single point near the LDO output.

4. **Si5351A clock routing**: Route CLK0 (stimulus) as a short, impedance-controlled 50 Ω trace to the π-network. Keep it away from the AD5933 analog inputs.

5. **Crystal reference (Y1 25 MHz)**: Place the 25 MHz crystal as close to the Si5351A as possible (XA/XB pins). Use 10 pF load capacitors. Guard with ground vias.

6. **DS18B20 placement**: Mount the DS18B20 in a small hole in the PCB directly under the ZIF socket, with thermal paste to the crystal package for accurate temperature measurement.

7. **Heater MOSFET**: Place Q1 (Si2302) and its gate resistor near the crystal socket. The heater trace (PC6 → gate resistor → Q1 gate) should be short and wide.

## 3. Assembly Steps

### Step 1: Solder the STM32G491RET6 (LQFP-64)
- Apply solder paste to the footprint.
- Place the IC using tweezers or a pick-and-place tool.
- Reflow with a hot-air station or reflow oven.
- Inspect all 64 joints under magnification.

### Step 2: Solder the Si5351A (MSOP-10)
- This is a fine-pitch (0.5 mm) package. Use solder paste and reflow.
- Ensure the 25 MHz reference crystal (Y1) and its 10 pF load capacitors are placed adjacent.

### Step 3: Solder the AD5933 (TSSOP-16)
- Another fine-pitch component. Use solder paste and reflow.
- Place RFB (10 kΩ) and RSET (200 Ω) close to the AD5933 pins.

### Step 4: Solder the π-Network Resistors
- Use 0603 thin-film 12.5 Ω ±0.1% resistors (6×).
- The placement accuracy directly affects measurement quality.

### Step 5: Solder the ZIF Socket
- Use a 14-pin ZIF socket for HC-49 crystals.
- For SMD crystals (3225/5032/7050), provide a secondary footprint with SMD pads.

### Step 6: Solder Remaining Components
- DS18B20 (TO-92) in the thermal well under the ZIF socket.
- SSD1306 OLED module (solder headers).
- microSD socket.
- USB-C receptacle.
- MOSFET, LEDs, buttons, passives.

### Step 7: Calibrate
- Follow the calibration procedure in the README (Section 9).
- Use the provided 50 Ω ±0.1% load standard and shorting bar.

## 4. Enclosure

The PCB fits in a 100×60×25 mm aluminum die-cast enclosure (Hammond 1550 or similar). The ZIF socket and OLED are accessible through a cutout in the lid. The USB-C port is accessible through an end-panel cutout.

## 5. Testing

1. **Power test**: Connect USB-C and verify 3V3 rail is stable.
2. **I²C scan**: Use the debug console to scan for Si5351A (0x60), AD5933 (0x0D), MAX17048 (0x36), and OLED (0x3C).
3. **Si5351A test**: Set CLK0 to 10 MHz and verify with a frequency counter.
4. **AD5933 test**: Measure a known 50 Ω load and verify the admittance reading.
5. **Full sweep**: Insert a 10 MHz AT-cut crystal and run a sweep. Verify R₁ ≈ 20–30 Ω, Q > 10,000.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No I²C devices found | I²C bus short or open | Check SDA/SCL continuity |
| Si5351A no output | PLL not locked | Verify 25 MHz crystal, check I²C writes |
| AD5933 returns 0 | MCLK missing | Verify Si5351A CLK1 output |
| Poor circle fit | Fixture parasitics | Re-run OSLT calibration |
| Inconsistent R₁ | Poor ZIF contact | Clean ZIF contacts, try different crystal |
| Heater not working | MOSFET gate drive | Check DAC output and MOSFET gate voltage |