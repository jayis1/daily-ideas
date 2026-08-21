# Aero Reed — Build Notes

## ADC / Touch Pin Conflict

The ESP32-S3's ADC1 channels overlap with touch-capable pins (GPIO1-14).
Since Aero Reed uses all 14 touch pads (T1-T14 = GPIO1-GPIO14), the three
analog sensors (breath, lip, battery) cannot use ADC1 without conflicting.

### Solution: ADS1115 I2C ADC (Recommended for production)

Use a Texas Instruments **ADS1115** 4-channel 16-bit I2C ADC for all
three analog inputs:

| ADS1115 Channel | Sensor | Notes |
|-----------------|--------|-------|
| AIN0 | MP3V5004G breath | 0..3.0 kPa |
| AIN1 | FSR-402 lip | 0..1 N force |
| AIN2 | Battery divider | VBAT × (220k / (100k+220k)) |
| AIN3 | spare | (future use) |

The ADS1115 connects via I2C (address 0x48), sharing the bus with the
SSD1306 OLED (0x3C) and MAX17048 fuel gauge (0x36).

The firmware includes a compile-time flag `USE_ADS1115` (in `breath.c` and
`lip.c`) to switch between direct-ADC mode (for prototyping with fewer
touch pads) and ADS1115 mode (production). The reference firmware defaults
to stubbed ADC reads; enable `USE_ADS1115` in `sdkconfig.defaults`:

```
CONFIG_AERO_REED_USE_ADS1115=y
```

### Alternative: Use ADC2

ADC2 on the ESP32-S3 does not overlap with touch pads but is shared with
Wi-Fi. Since Aero Reed uses BLE (not Wi-Fi) for MIDI, ADC2 channels
(GPIO5-7 on some variants) could be used. However, ADC2 availability
varies by module, so ADS1115 is the safer choice.

## USB-C Power + Data on Same Connector

The USB-C receptacle serves double duty:
1. **Power input** for TP4056 LiPo charging (VBUS → TP4056 VCC)
2. **USB MIDI data** via ESP32-S3 native USB (D+/D-)

This works because:
- The TP4056 draws power from VBUS (pin A4/B9 on USB-C).
- The ESP32-S3's USB D+/D- connect to the USB-C data pins (A6/A7).
- Both can operate simultaneously: the ESP32-S3 enumerates as a USB MIDI
  device while the TP4056 charges the battery from the same VBUS.

Make sure to add a 5.1 kΩ pull-down on the CC1/CC2 pins of the USB-C
receptacle to signal a UFP (upstream-facing port) device.

## Touch Pad Sensitivity

The ESP32-S3 touch peripheral measures capacitance by charging/discharging
the pad and measuring the discharge time. A touch increases capacitance,
which **decreases** the measured reading (counterintuitive).

The firmware auto-calibrates baselines at boot and tracks slow drift
(1/16 exponential moving average). A pad is "held" when:
1. The reading drops below 75% of baseline, AND
2. The deviation from baseline exceeds 12.5%

For best sensitivity:
- Use 8-12 mm diameter copper pads on the top PCB layer.
- Keep the ground plane **away** from directly under the pads (it
  increases parasitic capacitance and reduces sensitivity).
- A thin (≤0.5 mm) acrylic or PCB overlay works well. Avoid thick plastic.
- If sensitivity is poor, increase the touch measurement time in
  `touch_init()` (`touch_pad_set_meas_time`).

## Audio Grounding

The PCM5102A DAC and MAX98357A amplifier are sensitive to ground noise.
Use a star-ground topology: all audio grounds return to a single point
near the DAC. Keep the I2S signal traces short and away from the touch pad
traces.

## Speaker vs Headphone

The MAX98357A drives the on-board speaker (28 mm, 8 Ω). When headphones
are plugged into J1, the amplifier should be shut down (AMP_SD = GPIO33)
to avoid driving both loads simultaneously. The headphone jack's detect
switch can be wired to a GPIO for automatic switching (not shown in the
reference schematic; add a jack with switched contacts).

## LiPo Safety

- The TP4056 has built-in overcharge (4.2 V), over-discharge (2.9 V),
  and thermal protection.
- Use only protected 3.7 V LiPo cells.
- The MAX17048 fuel gauge provides accurate state-of-charge; the firmware
  displays battery % on the OLED and can enter deep sleep at <10%.
- Never short the battery terminals. Add a PTC fuse (0.5 A) on the VBAT
  rail for additional protection (not shown in the reference schematic).

## 3D-Printed Parts

STL files for the mouthpiece and instrument body are provided in
`docs/`:
- `mouthpiece.stl` — two-chamber mouthpiece (breath + lip FSR)
- `body.stl` — main instrument body (50 × 180 mm, holds PCB + battery)
- `body_lid.stl` — back cover with M2 screw bosses

Recommended print settings:
- Material: PETG or ABS (for dimensional stability)
- Layer height: 0.2 mm
- Infill: 30%
- Wall count: 3