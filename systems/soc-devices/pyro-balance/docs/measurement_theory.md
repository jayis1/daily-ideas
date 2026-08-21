# Pyro Balance — Measurement Theory

## 1. What TGA measures

Thermogravimetric analysis (TGA) tracks the **mass** of a sample as a function of temperature (or time) while the sample is subjected to a controlled temperature program. The resulting **TG curve** (mass % vs temperature) and its first derivative (**DTG curve**) reveal:

- **Moisture / solvent loss** (low-temperature mass loss)
- **Volatile content** (mid-range)
- **Thermal decomposition** steps (main polymer backbone break, filler decomposition)
- **Oxidative stability** (in air vs inert atmosphere)
- **Residual mass** (ash, char, inorganic filler)

TGA is the complementary technique to DSC (heat-flow analysis). DSC tells you *when* energy is absorbed/released; TGA tells you *when* mass changes. Together they fully characterize a material's thermal behavior.

## 2. The TG curve

Let $m_0$ be the initial sample mass. At each point:

$$ \text{mass \%}(T) = \frac{m(T)}{m_0} \times 100\% $$

The TG curve typically decreases in steps. Each step corresponds to a decomposition or evaporation event.

## 3. The DTG curve

The derivative thermogravimetric (DTG) curve is:

$$ \text{DTG}(T) = \frac{dm}{dT} \approx \frac{m_{i+1} - m_{i-1}}{T_{i+1} - T_{i-1}} $$

Or, if the heating rate $\beta = dT/dt$ is constant:

$$ \text{DTG} = \frac{1}{\beta} \frac{dm}{dt} $$

Peaks in the DTG curve mark the temperatures of maximum mass-loss rate. Each peak defines a decomposition step.

## 4. Step detection

For each DTG peak, we extract:

- **Onset temperature** $T_{\text{onset}}$: the temperature at which the step begins (extrapolated tangent intersection).
- **Peak temperature** $T_p$: the DTG peak (maximum mass-loss rate).
- **Endset temperature** $T_{\text{endset}}$: the temperature at which the step ends.
- **Step mass loss** $\Delta m$: integrated mass change over the step window.

The device uses an adaptive threshold (mean + k·std of |DTG|, k=4) with a 30 s refractory to avoid double-counting adjacent steps.

## 5. Residual mass

The mass at the final temperature is the **residual** (ash, char, or inorganic filler). For polymer QC:

$$ \text{filler content \%} = \text{residual \%} $$

assuming the polymer fully decomposes below the final temperature.

## 6. Buoyancy correction

As temperature rises, the density of the surrounding gas decreases, reducing the buoyant force on the sample and crucible — an apparent mass *increase*. This is corrected by running an **empty-crucible blank** through the same temperature program and subtracting the blank curve from the sample curve. Pyro Balance supports this via `scripts/analyze_tga.py --blank`.

## 7. Decomposition kinetics (multi-rate method)

Running the same sample at multiple heating rates $\beta_1, \beta_2, \beta_3$ (e.g., 2, 5, 10 °C/min) and recording the DTG peak temperature $T_p$ for a given step enables activation energy $E_a$ estimation without assuming a reaction model.

### 7.1 Kissinger method

$$ \ln\!\left(\frac{\beta}{T_p^2}\right) = \ln\!\left(\frac{AR}{E_a}\right) - \frac{E_a}{R \, T_p} $$

Plotting $\ln(\beta/T_p^2)$ vs $1/T_p$ gives a line with slope $-E_a/R$. Since $R = 8.314$ J/(mol·K):

$$ E_a = -\text{slope} \times R $$

### 7.2 Ozawa–Flynn–Wall (OFW) method

$$ \ln \beta = \text{const} - 1.052 \frac{E_a}{R \, T_p} $$

Plotting $\ln \beta$ vs $1/T_p$ gives slope $-1.052 E_a / R$.

### 7.3 Practical notes

- Use at least 3 heating rates (5 is better).
- The Kissinger and OFW methods agree to within ~5–10% for most polymer decompositions.
- Report $E_a$ in kJ/mol. Typical polymer decompositions: 100–250 kJ/mol.
- For the highest accuracy, use isoconversional methods (Friedman, KAS) — these require conversion vs temperature data and are available in `scripts/analyze_tga.py --kinetics isoconv`.

## 8. Atmosphere effects

Running in air vs N₂ distinguishes oxidative decomposition from pyrolysis:

- **N₂ (inert)**: pyrolysis — polymer backbone breaks without oxygen. Reveals true thermal stability.
- **Air (oxidative)**: oxidation reactions add mass-loss steps (especially for char oxidation at high T).
- **Switching mid-run**: run N₂ to 500 °C (pyrolysis), then switch to air at 500–600 °C → the char oxidizes and the residual drops to the inorganic ash content. This is the standard method for **filler content** in filled polymers.

## 9. Callendar–Van Dusen (RTD)

The PT1000 RTD resistance follows:

$$ R(t) = R_0 \left(1 + A t + B t^2\right) \quad (t \ge 0\,°C) $$

with $R_0 = 1000\,\Omega$, $A = 3.9083 \times 10^{-3}$, $B = -5.775 \times 10^{-7}$. Solving the quadratic for $t$ given measured $R$:

$$ t = \frac{-A + \sqrt{A^2 - 4B(1 - R/R_0)}}{2B} $$

For $t < 0$ the full CVD equation (with the $C(t-100)t^3$ term) is used; Pyro Balance focuses on $T \ge 0$.

## 10. Accuracy and limits

| Parameter | Pyro Balance | Benchtop TGA (TA Q500) |
|---|---|---|
| Mass resolution | ~5 µg | 0.1 µg |
| Temperature range | RT–600 °C | RT–1000 °C |
| Temperature accuracy | ±2 °C | ±1 °C |
| Heating rate | 0.5–20 °C/min | 0.1–100 °C/min |
| Sample size | 2–50 mg | 1–200 mg |
| Atmosphere | air / N₂ | air / N₂ / O₂ / Ar |
| Cost | ~$81 | $15k–$50k |

Pyro Balance trades the ultimate resolution and temperature range for portability and cost — suitable for field polymer identification, QC screening, education, and citizen science where a benchtop instrument is unavailable or impractical.

## References

- ASTM E1131 — Standard Test Method for Compositional Analysis by TGA
- ASTM E1640 — Assignment of Glass Transition Temperature by TGA
- Kissinger, H. E. (1957). *Anal. Chem.* 29(11), 1702–1706.
- Ozawa, T. (1965). *Bull. Chem. Soc. Jpn.* 38(11), 1881–1886.
- Callendar, H. L. (1887). On the practical measurement of temperature. *Phil. Mag.*