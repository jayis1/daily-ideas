# Echo Mote — Measurement Theory

## Logarithmic Swept-Sine (Exponential Chirp)

The Echo Mote uses a logarithmic swept sine (also called an exponential chirp) as its primary excitation signal. This technique, developed by Farina (2000), has several advantages over other room measurement methods:

### Why Log Sweep?

1. **High SNR**: The swept sine concentrates energy at each frequency for the full duration, unlike impulse or MLS which spread energy across all frequencies simultaneously
2. **Immune to harmonic distortion**: Harmonics of the excitation signal appear at different time positions in the deconvolved impulse response, so they can be separated from the linear response
3. **Robust to time-variance**: Short-term time variations in the room (doors opening, people moving) affect only a small portion of the sweep
4. **Full bandwidth**: Sweeps from 20 Hz to 20 kHz, covering the entire audible range

### Chirp Signal Definition

The instantaneous frequency of a logarithmic chirp increases exponentially with time:

```
f(t) = f_min × (f_max / f_min)^(t/T)
```

The phase is the integral of the instantaneous angular frequency:

```
φ(t) = 2π × f_min × T / ln(f_max/f_min) × [(f_max/f_min)^(t/T) - 1]
```

The resulting signal sweeps slowly through low frequencies (where more integration time is needed) and quickly through high frequencies (where less is needed), producing a pink-noise-like spectral envelope.

### Inverse Filter and Deconvolution

To extract the impulse response from the captured room response, we apply the inverse filter:

```
h(t) = IFFT( FFT(captured(t)) × FFT(inverse_chirp(t)) )
```

The inverse filter is computed in the frequency domain as:

```
H_inv(f) = conj(H_chirp(f)) / |H_chirp(f)|²
```

Where H_chirp(f) = FFT(chirp(t)). This is equivalent to:

```
H_inv(f) = 1 / H_chirp(f)    (with regularization)
```

The regularization prevents division by zero at frequencies where the chirp has very low energy.

### Overlap-Save Convolution

For long signals (5 seconds at 48 kHz = 240,000 samples), a single FFT is impractical. We use overlap-save convolution with 32,768-point FFTs:

1. Divide the captured signal into blocks of N = 32768 samples
2. Each block overlaps the previous by L = 16384 samples
3. The valid output from each block is N - L = 16384 samples
4. Discard the first L samples of each IFFT output (circular convolution artifacts)
5. Concatenate valid outputs to form the complete impulse response

## Schroeder Backward Integration

RT60 is measured using Schroeder's backward integration method (Schroeder, 1965):

```
L(t) = 10 × log10(∫t^∞ h²(τ) dτ / ∫0^∞ h²(τ) dτ)
```

This produces a smooth decay curve that:
- Is always monotonically decreasing
- Is independent of the excitation signal phase
- Provides a deterministic result (no averaging needed)

### T20, T30, and T60

From the Schroeder curve:
- **T20**: Fit a line from -5 dB to -25 dB, multiply by 3 for T60
- **T30**: Fit a line from -5 dB to -35 dB, multiply by 2 for T60
- **T60**: Direct measurement requires -60 dB decay, which is often below the noise floor

T30 is preferred when the SNR allows, as it uses more of the decay and is more robust.

## Octave-Band Filtering

Room acoustic parameters are traditionally reported per octave band. The Echo Mote uses 6th-order Butterworth bandpass filters for the standard octave bands:

| Band | Center | -3 dB Points | Bandwidth |
|------|--------|-------------|-----------|
| 1 | 125 Hz | 88–177 Hz | 89 Hz |
| 2 | 250 Hz | 177–354 Hz | 177 Hz |
| 3 | 500 Hz | 354–707 Hz | 353 Hz |
| 4 | 1 kHz | 707–1414 Hz | 707 Hz |
| 5 | 2 kHz | 1414–2828 Hz | 1414 Hz |
| 6 | 4 kHz | 2828–5657 Hz | 2833 Hz |

Butterworth filters provide maximally flat passband response and -18 dB/octave rolloff per pole. With 6th order, the rolloff is -36 dB/octave (120 dB/decade).

## Room Mode Detection

Room modes are standing waves that occur at frequencies where the room dimension is an integer multiple of half the wavelength:

```
f_nx = n × c / (2 × L_x)
```

Where:
- n = mode number (1, 2, 3, ...)
- c = speed of sound
- L_x = room dimension in that axis

The Echo Mote detects modes using two complementary methods:

### Method 1: Ping-and-Listen

1. Play brief (50 ms) sine tones at 1 Hz intervals from 20–300 Hz
2. After each ping, measure the decay time
3. Frequencies where decay time > 2× the broadband average are flagged as room modes

This method is effective because at a resonant frequency, the room "rings" longer than at non-resonant frequencies.

### Method 2: IR Spectral Analysis

1. Examine the FFT magnitude of the impulse response at low frequencies
2. Peaks above 20 dB relative to the local noise floor are flagged
3. Bandwidth of each peak gives the Q factor and decay time:
   - Q = f_center / bandwidth_3dB
   - decay_time ≈ Q / (π × f_center)

### Mode Classification

Modes are classified by their physical origin:

| Type | Surfaces Involved | Relative Strength | Decay Characteristic |
|------|------------------|-------------------|---------------------|
| Axial | 2 parallel walls | Strongest | Longest decay |
| Tangential | 4 walls + floor/ceiling | Moderate | Shorter decay |
| Oblique | All 6 surfaces | Weakest | Shortest decay |

Classification is inferred from harmonic relationships: if a mode frequency is an integer multiple of a lower mode, it's a higher-order axial mode.

## Speed of Sound Correction

The speed of sound depends on temperature:

```
c = 331.3 × √(1 + T/273.15)  m/s
```

At 20°C: c = 343.2 m/s
At 25°C: c = 346.2 m/s

This 1% change affects:
- Room mode frequencies (affects which frequencies are resonant)
- First-reflection distance estimation (from IR delay)
- Air absorption coefficients (affects high-frequency RT60)

The BME280 provides real-time temperature for automatic correction.

## Noise Criteria (NC) Curves

NC curves are defined by ASHRAE as maximum permissible sound pressure levels in 8 octave bands (63 Hz to 8 kHz). The NC rating of a room is the lowest NC contour that the measured noise spectrum does not exceed at any band.

### Typical NC Requirements

| Space Type | NC Rating |
|-----------|-----------|
| Concert hall | NC-15 to NC-20 |
| Recording studio | NC-15 to NC-20 |
| Courtroom | NC-25 to NC-30 |
| Conference room | NC-25 to NC-30 |
| Open office | NC-35 to NC-40 |
| Classroom | NC-25 to NC-30 |
| Hospital room | NC-25 to NC-30 |

## References

1. Farina, A. (2000). "Simultaneous measurement of impulse response and distortion with a swept-sine technique." *108th AES Convention*.
2. Schroeder, M.R. (1965). "New method of measuring reverberation time." *J. Acoust. Soc. Am.*, 37(3), 409–412.
3. ISO 3382-1:2009. "Acoustics — Measurement of room acoustic parameters — Part 1: Performance spaces."
4. ASHRAE Handbook — HVAC Applications, Chapter 48: Sound and Vibration Control.

---

*Echo Mote Measurement Theory — SoC Device Inventions*