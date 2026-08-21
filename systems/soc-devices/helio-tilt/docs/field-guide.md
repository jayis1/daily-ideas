# Field Guide — Helio Tilt

## Quick Start

1. **Charge**: Connect USB-C cable. Green LED = charging, off = full.
2. **Insert SD**: Insert a FAT32-formatted microSD card.
3. **Power on**: Press any button. OLED shows "HELIO TILT v1.0".
4. **Place outdoors**: Set on a flat surface with clear sky view.
5. **Start tracking**: Press Start/Stop button. Device acquires GPS,
   homes steppers, and begins tracking the sun.
6. **Read DNI**: The OLED shows a DNI bar chart (0–1400 W/m²) and
   AOD values at 6 wavelengths.
7. **Stop**: Press Start/Stop again to return to IDLE.

## Optimal Measurement Conditions

- **Clear sky**: No clouds in the sun's direction. Thin cirrus is
  acceptable but degrades AOD accuracy.
- **Sun elevation > 5°**: Below 5°, atmospheric refraction and
  increased air mass reduce accuracy.
- **Stable aerosol**: For Langley calibration, aerosol must be stable
  over 2–3 hours (clear morning or evening).

## Understanding the Measurements

### DNI (Direct Normal Irradiance)
- **Range**: 0–1400 W/m²
- **Clear sky**: 800–1000 W/m² (midday, sea level)
- **Hazy**: 500–800 W/m²
- **Overcast**: <200 W/m² (instrument won't measure AOD without sun)

### AOD (Aerosol Optical Depth)
- **Clean air**: 0.02–0.10
- **Moderate haze**: 0.10–0.30
- **Heavy haze / dust**: 0.30–1.00
- **Dust storm / smoke**: 1.00–3.00+

### Ångström Exponent (α)
- **α > 1.5**: Fine-mode aerosols (urban, industrial, biomass burning)
- **α ≈ 1.0**: Mixed aerosol
- **α < 0.5**: Coarse-mode aerosols (dust, sea salt)

### PWV (Precipitable Water Vapor)
- **Dry**: 0.5–1.5 cm
- **Moderate**: 1.5–3.0 cm
- **Humid**: 3.0–5.0 cm
- **Tropical**: >5.0 cm

## Langley Calibration

### When to Calibrate
- First use (factory defaults are approximate)
- After filter wheel replacement
- Monthly for best accuracy
- After firmware update

### How to Calibrate
1. Choose a clear, stable-aerosol day
2. Start in the morning (after sunrise, elevation >5°) or evening
3. Press the Calibrate button (or select "Langley Cal" from menu)
4. The device tracks the sun and logs V(λ) vs. air mass every 2 min
5. After 60+ points (~2 hours), regression quality is checked
6. R² > 0.99 → calibration accepted, V₀ stored
7. R² < 0.99 → calibration rejected (aerosol was not stable enough)

### What R² Means
- R² = 1.0: Perfect linear fit (ideal stable atmosphere)
- R² > 0.99: Excellent calibration
- R² 0.95–0.99: Marginal (acceptable but less accurate)
- R² < 0.95: Reject — aerosol changed during calibration

## Deploying as a Fixed Station

1. Mount on a pole or tripod at a fixed location
2. Ensure the AZ home switch aligns with true north
   - Use a compass (correct for magnetic declination)
   - Or: calibrate the magnetometer, then point AZ home = north
3. Connect USB-C for continuous power (disables battery)
4. The device will track from sunrise to sunset automatically
5. Data is logged to SD card continuously
6. For real-time streaming, connect via BLE to a nearby phone/Gateway

## Data Analysis

### Python Companion App
Use `scripts/helio_app.py` to connect over BLE and plot:
- DNI time series
- AOD at all wavelengths
- Ångström exponent time series
- PWV time series
- Langley regression plot

### AERONET Data Format
The SD card CSV is compatible with AERONET data processing tools.
Upload data to the AERONET data submission portal for inclusion in
the global sun photometer network.

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| No GPS fix | Indoor / antenna blocked | Move outdoors, wait 30 s |
| Steppers not moving | Battery low / not enabled | Check battery >3.5V |
| DNI reads 0 | Sun not in FOV | Check tracking, re-home |
| AOD negative | V₀ not calibrated | Run Langley calibration |
| AOD noisy | Clouds / unstable air | Wait for clear conditions |
| R² < 0.99 | Aerosol changed | Retry on a more stable day |
| OLED blank | I2C issue / power | Check connections, reboot |

## Maintenance

- **Clean collimator lens**: Wipe with lens tissue + isopropyl
  alcohol. Dust on the aperture degrades DNI accuracy.
- **Check filter wheel**: Ensure filters are clean and seated. Replace
  if scratched or delaminated.
- **Calibrate magnetometer**: After moving to a new location or
  changing the mounting orientation.
- **Check SD card**: Replace annually (wear from continuous logging).
- **Battery**: Replace 18650 cell after ~500 charge cycles.