# Vibrating Tube Densitometer — Theory of Operation

## Principle

The Brew Sense measures specific gravity (SG) using a **vibrating tube densitometer** — the same principle used in laboratory-grade density meters (Anton Paar, Mettler Toledo), miniaturized for homebrew.

### Physical Model

A stainless-steel tube, clamped at one end and free to vibrate, is excited at its resonant frequency by a piezoelectric driver. When the tube vibrates in air, it resonates at frequency `f_air`. When submerged in liquid of density `ρ`, the resonant frequency shifts to `f_liquid` because the effective mass of the vibrating system increases.

The relationship is:

```
f_res = (1 / 2π) × √(k / (m_tube + ρ_fluid × V_tube))
```

Where:
- `k` = stiffness of the tube + piezo system (N/m)
- `m_tube` = mass of the tube + piezo elements (kg)
- `ρ_fluid` = density of the surrounding fluid (kg/m³)
- `V_tube` = effective displaced volume of the tube (m³)

### Two-Point Calibration

By measuring the resonant frequency at two known densities:

1. **Air calibration** (`ρ ≈ 1.2 kg/m³`, SG ≈ 0.001):
   - Measure `f_air`

2. **Water calibration** (`ρ = 998.2 kg/m³` at 20°C, SG = 1.000):
   - Measure `f_water`

We can solve for any unknown density:

```
ρ_fluid = ρ_water × (f_water² × f²) / (f_water² × f_air²)

More precisely:
SG = (f_water² - f²) / (f_water² - f_air²)
```

This linearized form assumes the tube stiffness and geometry remain constant between calibrations.

### Frequency Sweep Method

The STM32L476 generates a frequency sweep (1-8 kHz) through the DAC output (PA4) amplified by a complementary PWM signal (PB4). At each frequency step, the receiver piezo (connected to PA0/ADC) is sampled to measure the amplitude response.

The sweep identifies the resonant peak:
- **Resonant frequency**: frequency of maximum amplitude
- **Amplitude**: peak amplitude (indicates coupling quality)
- **Q factor**: ratio of resonant frequency to bandwidth at -3dB points

Parabolic interpolation around the peak provides sub-step frequency resolution (~1 Hz accuracy).

### Temperature Compensation

The vibrating tube's stiffness and geometry change with temperature. The OIML (International Organization of Legal Metrology) recommends:

```
SG_corrected = SG_measured × [1 + α × (T_measured - T_calibration)²]
```

Where:
- `α ≈ 0.0000025` (empirical correction coefficient)
- `T_measured` = current temperature from DS18B20
- `T_calibration` = temperature at water calibration

For higher accuracy, use the OIML polynomial for water density:

```
ρ_w(t) = 999.842594 + 6.793952×10⁻²×t - 9.095290×10⁻³×t²
         + 1.001685×10⁻⁴×t³ - 1.120083×10⁻⁶×t⁴ + 6.536332×10⁻⁹×t⁵
```

## Practical Considerations

### Vibration Isolation

The densitometer is sensitive to external vibrations:
- Mount the PCB firmly to the fermenter wall using magnetic backing
- Use foam grommets on the vibrating tube assembly
- Average multiple sweeps (default: 3) to reduce noise

### Tube Geometry

The 316L stainless tube specifications:
- **Outer diameter**: 4mm
- **Inner diameter**: 3mm
- **Wall thickness**: 0.5mm
- **Length**: 50mm (vibrating section)
- **Effective mass**: ~2.4g (tube + piezo elements)
- **Expected resonant frequency**: ~4-5 kHz in air, ~3-4 kHz in water

### Accuracy Targets

| Parameter | Target | Method |
|-----------|--------|--------|
| SG accuracy | ±0.002 | Two-point calibration |
| SG resolution | ±0.0005 | Parabolic interpolation |
| Temperature range | 0-40°C | DS18B20 ±0.1°C |
| Measurement time | 2 seconds | 3-sweep average |
| Long-term drift | ±0.001/month | Re-calibrate monthly |

### Bubble Mitigation

Air bubbles on the vibrating tube will cause erroneous high-SG readings (air has lower density than liquid). Mitigation:
1. Mount tube vertically (bubbles rise off)
2. Shake gently after submerging to dislodge bubbles
3. Discard first 3 readings after submersion
4. If Q factor drops below 10, flag reading as unreliable

## Alternative: Capacitive Method

If the vibrating tube proves too difficult to assemble, a simpler (but less accurate) alternative is to use a **capacitive sensor**:
- Two parallel plates submerged in the wort
- Dielectric constant of wort changes with sugar content
- SG is proportional to dielectric constant
- Accuracy: ±0.005 (vs ±0.002 for vibrating tube)
- No moving parts, easier assembly

The STM32L476's ADC can measure capacitance using charge-time measurement on GPIO pins.