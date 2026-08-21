# Schematic — Ion Sprint

This folder contains the KiCad project files for the Ion Sprint pocket
capillary electrophoresis instrument with contactless conductivity
detection (C4D).

## Files

- `ion_sprint.kicad_pro` — KiCad project file
- `ion_sprint.kicad_sch` — schematic (top sheet)
- `ion_sprint.kicad_pcb` — PCB layout (placeholder, 4-layer, 80×50 mm)

## Schematic Overview

The schematic is organized into these sections:

1. **Power** — USB-C 5 V → TP4056 charger → 18650 cell → MCP1640B
   boost (3.7→5 V) → AP2112-3.3 (digital) + LP5907-3.3 (analog) +
   REF3030 (3.0 V reference). Ferrite beads isolate analog/digital
   ground planes.

2. **HV Supply (Cockcroft-Walton)** — MC34063A boost converter
   generates 100 V AC at 50 kHz, feeding a 5-stage Cockcroft-Walton
   voltage multiplier (US1M diodes + 1 nF 3 kV caps) producing up to
   30 kV DC. DAC1 sets the control voltage (0–3.3 V → 0–30 kV).
   HV current monitor: 100 Ω sense resistor → AD8629 amp (×100)
   → ADC2 (10 µA resolution). HV voltage monitor: 10000:1 divider
   (100 MΩ / 10 kΩ) → ADC3 (1 V/kV). HV bleeder: 1 GΩ resistor
   discharges to GND when PB6 goes low. Safety: TLV3201 comparator
   trips at 250 µA, gates off CW oscillator via PC2 within 1 µs.

3. **C4D Front End** — DAC2 generates 100 kHz AC excitation (±1.65 V
   centered on 1.65 V) for the driver electrode (E1, copper tube 2 mm
   wide). The pickup electrode (E2, copper tube 2 mm, 1 mm gap) feeds
   OPA656 JFET op-amp in transimpedance configuration (R30/R31 = 1 MΩ
   feedback). 4th-order Bessel BPF (90–110 kHz) passes the 100 kHz
   carrier to ADC1 (PA0). Firmware lock-in demodulation extracts the
   amplitude envelope (electropherogram). Guard shield (PB10) driven
   at driver potential to minimize parasitic capacitance.

4. **SoC** — STM32G474RET6 (LQFP64). DAC1 drives HV setpoint, DAC2
   drives C4D excitation, ADC1 captures C4D signal, ADC2/ADC3 monitor
   HV current/voltage. CORDIC accelerates lock-in I/Q demodulation.
   I2C1 drives OLED + DS18B20. SPI1 drives microSD. SPI2 drives
   W25Q128 flash. USART1 drives ESP32-C3 BLE bridge. TIM2 drives
   NEMA8 stepper (vial lift). TIM4 drives peristaltic pump.

5. **Capillary & Vial System** — Fused silica capillary (50 µm ID,
   365 µm OD, 25 cm total). Polyimide removed at detection window
   (2 mm) for C4D electrodes. Inlet vial: 1.5 mL microcentrifuge
   tube with Pt wire electrode (HV+). Outlet vial: 1.5 mL tube with
   Pt wire electrode (GND). NEMA8 stepper (DRV8833 driver) lifts
   inlet vial for hydrodynamic injection. Peristaltic pump (DRV8833
   driver) flushes capillary between runs.

6. **Sensors** — DS18B20 (BGE temperature, 1-Wire on PC6). TLV3201
   (HW current-limit, 250 µA trip). TCRT5000 optical sensors (PC10/
   PC11/PC12) detect vial presence.

7. **Memory / logging** — microSD (SPI1, FAT32) for CSV + raw binary
   electropherogram. W25Q128 (SPI2, 16 MB) for electropherogram ring
   buffer (BLE streaming).

8. **Display** — SH1106 1.3" 128×64 OLED (I2C1, 0x3D).

9. **BLE bridge** — ESP32-C3-MINI-1 (USART1, 921600 baud) for BLE 5 +
   Wi-Fi 4 streaming of electropherogram + results.

10. **UI** — EC11 rotary encoder + 3 tactile buttons (Mode, Start/Stop,
    Inject) + 2 status LEDs (red HV armed, green running) + WS2812B
    RGB status LED. Lid interlock switch (SW5) on PB7.

## HV Safety

The 30 kV HV rail is the highest-voltage node in this device. Safety
measures:

- **Current-limited supply**: Cockcroft-Walton stage is inherently
  current-limited; max output 200 µA at 30 kV.
- **Hardware current cutoff**: TLV3201 comparator monitors HV return
  current. If >250 µA, PC2 goes low, gating off CW oscillator in <1 µs.
- **Active bleeder**: PB6 (active-low) connects 1 GΩ resistor from
  30 kV node to GND. 30 kV → 0 V in <1 s (10τ).
- **Interlock**: PB7 (pulled high) reads lid interlock switch. If
  open, firmware refuses to arm HV.
- **Voltage monitor**: ADC3 reads 10000:1 divider. If measured
  voltage deviates >±2 kV from setpoint, firmware aborts.
- **Soft-start**: DAC1 ramps from 0 to target over 5 s to avoid
  capillary overheating.

## HV PCB Layout Notes

- The 30 kV HV section requires ≥10 mm creepage on the PCB.
- Use a 2 mm slot around the CW multiplier section to increase
  creepage distance. Conformal coat after assembly.
- The 100 MΩ / 10 kΩ divider and 1 GΩ bleeder must be on the HV
  side of the slot, with the ADC3/PB6 traces crossing via a single
  clearance-drilled via pair.
- The C4D electrode assembly is off-board: the copper tube electrodes
  mount in a 3D-printed cell that clamps onto the capillary. Connect
  via shielded micro-coax (RG-178, <5 cm).

## Grounding

- **AGND / DGND split**: analog ground (OPA656, AD8629, REF3030, C4D
  electrodes, HV return) ties to AGND; digital ground (STM32, ESP32-C3,
  OLED, SD, W25Q128) ties to DGND. They meet at a single star point
  under the STM32.
- **HV return**: the CW multiplier return is a separate net that ties
  to AGND at the star point only.
- **C4D shield**: guard shield (PB10) driven at driver electrode
  potential to minimize parasitic capacitance.

## Opening in KiCad

```
kicad ion_sprint.kicad_pro
```

Requires KiCad 7.0+ (uses the 20231120 file format).