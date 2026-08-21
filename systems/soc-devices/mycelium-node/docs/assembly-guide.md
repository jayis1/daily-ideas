# Mycelium Node — Assembly Guide

## Tools Required

- Soldering iron (fine tip, temperature controlled, 300–350°C)
- Hot air rework station (for ESP32-C6-MINI-1 module and QFN packages)
- Solder paste (Type 4, no-clean)
- Multimeter
- Oscilloscope (helpful for verifying PWM and I2C signals)
- ESP-Prog or USB-UART bridge (for initial flash)
- KiCad 8+ (for schematic review)
- 3D printer (for DIN-rail enclosure)
- Heat gun or toaster oven (for reflow, if not using hot air)

## PCB Fabrication

Order a 4-layer PCB from JLCPCB, PCBWay, or similar:

| Parameter | Value |
|-----------|-------|
| **Layers** | 4 |
| **Thickness** | 1.6 mm |
| **Surface finish** | ENIG (gold) — better for I2C sensor contacts |
| **Copper weight** | 1 oz outer, 0.5 oz inner |
| **Solder mask** | Green (or white for better visibility) |
| **Silkscreen** | White |
| **Board size** | 105 mm × 75 mm |
| **Minimum trace/space** | 6/6 mil |
| **Minimum via** | 0.3 mm drill / 0.6 mm pad |

### Layer Stack-up

```
Top:      Signal (components, I2C, PWM routing)
Inner 1:  Ground plane (solid GND pour)
Inner 2:  Power plane (3.3V and 5V islands)
Bottom:   Signal (power routing, actuator traces)
```

## Assembly Order

### Step 1: SMD Components (Bottom Side)

1. Apply solder paste to all bottom-side pads
2. Place components in this order (largest to smallest):
   - USB-C receptacle (J1)
   - Barrel jack (J3)
   - Relay (K1)
   - MT3608 boost converter (U3)
   - ME6211 LDO (U4)
   - TP4056 charger (U2)
3. Reflow using hot air (250°C peak, 60–90 s)

### Step 2: SMD Components (Top Side)

1. Apply solder paste to all top-side pads
2. Place components in this order:
   - ESP32-C6-MINI-1 module (U10) — **most critical placement**
   - IRLML6344 MOSFETs (Q1–Q6) — 6 total
   - SHT40 sensors (U20, U21)
   - SCD41 (U22)
   - TSL2591 (U23)
   - All passive components (resistors, capacitors, inductors)
3. Reflow using hot air or reflow oven (250°C peak)

### Step 3: ESP32-C6-MINI-1 Module

⚠️ **Critical**: The ESP32-C6-MINI-1 has castellated edge pads. Use generous solder paste on the pads, align carefully, and reflow with hot air. Do NOT use a soldering iron directly on the module.

- Center the module on its pads
- Apply heat from above with hot air at 250°C
- Watch for solder wicking up the castellated edges — this is normal
- Inspect all edges for proper wetting

### Step 4: Through-Hole Components

1. Install DS18B20 jack connectors (J4 × 2) — 3.5mm audio jacks
2. Install rotary encoder (SW1) — snap-in type
3. Install piezo buzzer (BZ1) — SMD type already placed
4. Install electrolytic capacitors (C8 bulk, C9 output)
5. Install inductor (L1) — 4.7 µH shielded

### Step 5: Sensor Board Assembly

The SHT40 (substrate) and SCD41 are on separate small PCBs connected via ribbon cable:

1. **Chamber SHT40** (U20) — on main PCB, inside enclosure
2. **Substrate SHT40** (U21) — on a 15mm × 15mm daughterboard, connected via 4-pin JST-SH I2C cable
3. **SCD41** (U22) — on a 20mm × 20mm daughterboard, connected via 4-pin JST-SH I2C + reset cable
4. **TSL2591** (U23) — on main PCB, facing chamber through a window

For each daughterboard:
- Solder the sensor onto the small PCB
- Attach a PTFE membrane filter over the SHT40 (substrate unit) to protect from water droplets
- Connect I2C cable (3.3V, GND, SDA, SCL) to main board

### Step 6: DS18B20 Waterproof Probes

1. Solder DS18B20 waterproof probes to 3.5mm audio jack plugs:
   - Tip = Data (GPIO9 with 4.7K pull-up)
   - Ring = VCC (switched, via MOSFET on GPIO16)
   - Sleeve = GND
2. Seal the connector joint with heat-shrink tubing
3. Label probes: "Deep 1 (3cm)" and "Deep 2 (7cm)"

### Step 7: Actuator Wiring

| Actuator | Connector | Wires |
|----------|-----------|-------|
| Ultrasonic mister | JST-PH 2-pin | VCC (5V switched), GND |
| Heat pad | JST-PH 2-pin | VCC (5V switched), GND |
| Exhaust fan | JST-PH 3-pin | VCC (12V), GND, PWM tach |
| Grow light | JST-PH 2-pin | VCC (12V switched), GND |

⚠️ **Important**: The 12V actuator rail comes from the barrel jack. Do NOT connect 12V loads to the 5V USB supply.

### Step 8: Power Supply Verification

Before connecting the ESP32-C6:

1. Connect USB-C 5V power supply
2. Measure 3.3V at the ME6211 output — should read 3.28–3.36V
3. Connect 12V barrel jack
4. Measure 12V rail at fan connector — should read 11.5–12.5V
5. Insert LiPo battery (3.7V 2000mAh)
6. Verify TP4056 charging: measure current draw from USB (~500 mA with depleted battery)
7. Measure LiPo voltage at ADC divider: should be ~1.8–2.0V (half of battery voltage)

### Step 9: Firmware Flash

1. Connect ESP-Prog to SWD header (or use USB-UART on GPIO1/GPIO2)
2. Flash bootloader + application:
   ```
   idf.py -p /dev/ttyUSB0 flash
   ```
3. Verify boot on serial console (115200 baud):
   ```
   === Mycelium Node v1.0 ===
   Mushroom Fruiting Chamber Environmental Controller
   I2C bus initialized on SDA=3 SCL=4 @ 400000 Hz
   SHT40 at 0x44 initialized
   SHT40 at 0x45 initialized
   SCD41 CO2 sensor initialized (warm-up: 60s)
   TSL2591 light sensor initialized (gain=25x, integ=500ms)
   DS18B20 1-Wire bus initialized on GPIO 9
   Actuators initialized (4 PWM channels + safety relay)
   Power monitoring ADC initialized
   SSD1306 OLED initialized (128x64, I2C 0x3C)
   Rotary encoder initialized on A=10 B=11 SW=12
   Phase changed to FRUITING (temp=22.0°C, rh=93%, co2_max=1000, light=70%)
   MYC>
   ```

### Step 10: Enclosure Assembly

1. 3D-print the DIN-rail enclosure (STL files in `hardware/` directory)
2. Insert main PCB into the enclosure slots
3. Route sensor cables through the bottom cable glands
4. Route actuator cables through the side cable glands
5. Snap the OLED display into its window
6. Press the rotary encoder shaft through the front panel knob
7. Close the enclosure and mount on DIN rail

### Step 11: Commissioning

1. Power on via USB-C
2. Verify all sensors on the debug console:
   ```
   MYC> status
   ```
3. Calibrate SCD41 by placing the device in fresh outdoor air for 10 minutes:
   ```
   MYC> calibrate co2 420
   ```
4. Set WiFi credentials:
   ```
   MYC> wifi connect "YourSSID" "YourPassword"
   ```
5. Start MQTT:
   ```
   MYC> mqtt start
   ```
6. Place sensor daughterboards in the fruiting chamber:
   - Chamber SHT40: inside chamber, above substrate level
   - Substrate SHT40: taped to the outside of a grow bag, under the filter patch
   - SCD41: inside chamber, at canopy level
   - DS18B20 probes: inserted into substrate at 3 cm and 7 cm depth

7. Verify PID control by setting a setpoint and watching the actuators respond:
   ```
   MYC> set humidity 95
   MYC> override humidifier 50
   ```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| SHT40 reads 0°C / 0% RH | I2C address wrong or pull-ups missing | Check A0 pin on SHT40 variant; verify 4.7K pull-ups |
| SCD41 returns 0 ppm | Not warmed up yet | Wait 60 seconds after power-on |
| OLED blank | I2C conflict or wrong address | Verify 0x3C address; scan bus with `i2cdetect` |
| Humidifier stays on | PID integral windup | Reset PID: `pid humidity ki 0` then restore |
| Fan won't spin | 12V supply missing | Check barrel jack; fan needs 12V rail |
| ESP32 won't boot | LDO not enabled | Check GPIO27 (LDO_EN) is HIGH |
| DS18B20 reads 85°C | Conversion not complete | Increase delay in `ds18b20_read_all()` or check pull-up |
| SCD41 reads 400 ppm constantly | ABC not calibrated | Run outdoor calibration: `calibrate co2 420` |