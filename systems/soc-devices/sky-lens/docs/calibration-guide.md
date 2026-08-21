# Sky Lens — Calibration Guide

## 1. SiPM discriminator threshold

Each TLV3501 comparator has a 10 kΩ trim pot that sets the threshold.
The goal is to set the threshold just above the single-photo-electron
(SPE) noise floor so that real muon pulses (typically 200–1000 PE) are
reliably detected while dark-count noise is rejected.

1. Power on the device with the scintillator stack in place but **no
   coincidence window** set (set the window to 500 ns temporarily to
   see all singles).
2. Connect the debug UART (GPIO40/41) at 115200 baud and watch the
   singles rate log.
3. Adjust the threshold pot until the singles rate is ~100–500 Hz
   (dominated by real gamma events, not dark counts). If the rate is
   >1 kHz, the threshold is too low. If it's <10 Hz, it's too high.
4. Repeat for both channels (top and bottom).

## 2. Coincidence window

With the thresholds set, restore the coincidence window to 60 ns and
verify that the coincidence rate is ~20–30 cpm (the expected muon rate
through a 50×50 mm tile at sea level). If the rate is much higher,
reduce the window to 40 ns. If it's near zero, the timestamps are not
arriving — check the RMT channel wiring (GPIO1, GPIO2).

## 3. Barometric pressure coefficient

The muon rate at sea level varies with pressure by ~−0.7%/hPa. To
calibrate the coefficient `β` for your specific location:

1. Run the device for several days, logging the raw rate and the BMP390
   pressure every 10 minutes.
2. Plot `ln(rate)` vs `pressure` and fit a line. The slope is `−β`.
3. Update `BETA_PER_HPA` in `pressure.c` if it differs significantly
   from the default 0.012 (this can happen at altitude or in unusual
   atmospheric conditions).

## 4. IMU attitude alignment

The IMU attitude quaternion must be consistent with the physical
orientation of the detector. To align:

1. Place the device face-up on a level surface. The gravity vector
   should read [0, 0, +9.81] m/s². If not, apply an offset in
   `imu_read_accel()`.
2. The yaw is arbitrary (no magnetometer), so the skymap azimuth is
   relative to the device's orientation at boot. For an absolute
   skymap, note the device heading at the start of a run and apply the
   offset in the app.
3. For long runs, the Mahony filter will drift slowly in yaw (~1°/min);
   this is acceptable for a cos²θ fit but not for a precise skymap. For
   a precise skymap, keep the device stationary.

## 5. Pulse-height calibration (optional)

The ADS7946 reads the peak-hold voltage in millivolts. To convert to
deposited energy (MeV):

1. Place a known gamma source (e.g. Cs-137, 662 keV) near the tile.
2. The Compton edge for 662 keV in plastic is ~478 keV. Identify the
   Compton edge in the pulse-height spectrum.
3. The conversion factor is `MeV = (peak_mV - baseline_mV) / gain_mV_per_MeV`.
4. Store the gain factor in NVS and apply it in the firmware.

This step is optional — the pulse height is primarily used for a
relative energy cut, not absolute calibration.

## 6. Muon-lifetime verification

To check the lifetime mode:

1. Place a 20 mm aluminium absorber above the bottom tile.
2. Select "Lifetime" mode in the app or via the MODE button.
3. Run for 4–8 hours. The decay histogram should populate with an
   exponential of τ ≈ 2.197 µs.
4. The firmware reports τ_µ and its 1-σ error. A good run gives
   τ_µ = 2.2 ± 0.2 µs.