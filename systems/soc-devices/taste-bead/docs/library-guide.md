# Taste Bead — Library Guide

## Building the Reference Library

The Taste Bead identifies liquids by comparing their impedance fingerprint against a stored reference library. To get good results, you need to build a library of known liquids first.

## Library Capacity

- **Maximum entries**: 50 (stored in NVS flash)
- **Per entry**: 32-byte label + 48-feature vector (192 bytes) = 224 bytes
- **Total storage**: ~11 KB in NVS

## Adding a New Reference

### Via Phone App (recommended)

1. Put Taste Bead in **Learn mode** (press MODE button until LED is red)
2. Open the companion app (`taste_bead.py --ble`)
3. Send the LEARN command with a label:
   ```python
   python3 taste_bead.py --ble --learn "Whole Milk 2%"
   ```
4. Dip the probe in the sample liquid
5. Press the ID button on the device
6. Wait ~12 seconds for the sweep to complete
7. The fingerprint is stored in the library

### Via On-Device Buttons

1. Switch to **Learn mode** (MODE button → red LED)
2. Dip probe in sample
3. Press the ID button
4. The device captures the fingerprint and stores it with a default name
5. Rename it later via BLE

## Recommended Reference Library

For general liquid identification, capture references for:

| # | Category | Liquid | Notes |
|---|----------|--------|-------|
| 1 | Water | Distilled water | Baseline — lowest conductivity |
| 2 | Water | Tap water (local) | Geo-specific (varies by city) |
| 3 | Water | Bottled spring water | Compare with tap |
| 4 | Water | 0.01 M KCl | Calibration reference |
| 5 | Water | 0.1 M NaCl | High conductivity reference |
| 6 | Milk | Whole milk (fresh) | |
| 7 | Milk | Skim milk (fresh) | |
| 8 | Milk | Whole milk (spoiled 24h) | Compare with fresh |
| 9 | Juice | Orange juice (100%) | |
| 10 | Juice | Apple juice (100%) | |
| 11 | Juice | Cranberry juice | |
| 12 | Oil | Extra virgin olive oil | Low conductivity |
| 13 | Oil | Refined olive oil | Compare with EVOO |
| 14 | Oil | Vegetable oil | |
| 15 | Alcohol | 40% vodka | |
| 16 | Alcohol | 12% wine (red) | |
| 17 | Alcohol | 5% beer | |
| 18 | Sweet | Honey (pure) | |
| 19 | Sweet | Honey + 20% corn syrup | Adulteration test |
| 20 | Coffee | Fresh brewed (dark roast) | |
| 21 | Coffee | Fresh brewed (light roast) | |
| 22 | Coffee | Stale (24h old) | Compare with fresh |
| 23 | Soap | 1% dish soap solution | |
| 24 | Chemical | 0.1 M HCl | Acid reference |
| 25 | Chemical | 0.1 M NaOH | Base reference |

## Improving Accuracy

### Multiple Measurements

The library automatically averages multiple measurements of the same liquid. To improve a reference entry:
- In Learn mode, press ID multiple times on the same sample
- Each measurement updates the running average
- Recommended: 3-5 measurements per reference

### Temperature Control

Impedance is temperature-dependent (ionic conductivity increases ~2%/°C). For best results:
- Measure references and samples at the same temperature (room temperature)
- The device estimates liquid temperature from impedance shift and compensates
- For critical measurements, use a water bath to control temperature

### Probe Care

- **Rinse** the probe with distilled water between measurements
- **Gently wipe** electrodes with a lint-free cloth
- **Avoid scratching** glassy carbon and gold electrodes
- **Store** with the protective cap on
- **Re-calibrate** weekly if used daily (or if readings seem off)
- **Replace** copper electrode if it oxidizes (tarnishes over months)

## Deleting Library Entries

1. Switch to **Library mode** (MODE button → blue LED)
2. Press LIB button to browse entries (OLED shows index/total and label)
3. To delete the currently displayed entry: press and hold the ID and LIB buttons simultaneously for 3 seconds
4. To clear the entire library: use the phone app command:
   ```python
   python3 taste_bead.py --ble --clear-library
   ```

## Exporting/Importing Library

The library can be exported via BLE or read from the SD card CSV log:

```python
# Export library to JSON
python3 taste_bead.py --ble --export-library library.json

# Import library from JSON (requires firmware update mode)
python3 taste_bead.py --ble --import-library library.json
```