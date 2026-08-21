# Sky Lens — Safety Notes

## +30 V SiPM bias

The TPS61158 boost converter generates up to **+30 V** for the SiPM
reverse bias. While the current is limited to 5 mA (not dangerous in
the electrocution sense), the voltage is high enough to cause a
noticeable shock and can damage sensitive components if misapplied.

### Precautions

- **Discharge before handling**: When powering off, the firmware
  disables `BIAS_EN` and a 10 MΩ bleeder resistor discharges the +30 V
  rail to a safe level within 1 second. Wait at least 2 seconds after
  power-off before touching the SiPM area.
- **No conductive objects**: Do not insert screwdrivers or probes into
  the SiPM bias area while powered. A short from the +30 V rail to
  ground will trip the TPS61158 OCP (over-current protection) but may
  damage the SiPM if sustained.
- **Check with a multimeter**: Before touching, verify that the +30 V
  rail reads <2 V with a multimeter (set to DC volts, probe between the
  SiPM cathode pad and ground).
- **Capacitor ratings**: All capacitors on the +30 V rail must be
  rated for at least 50 V. Using a 16 V or 25 V cap will cause
  catastrophic failure.

### Fault indicators

- **FAULT LED (red)**: Lit when the SiPM bias boost has tripped its OCP
  or thermal shutdown. Power-cycle the device to clear.
- **BIAS_FAULT (GPIO38)**: Read by the firmware; if asserted, the
  boost is disabled and no acquisition will start.

## LiPo battery

The 3.7 V 1500 mAh LiPo has standard LiPo precautions:

- Do not puncture, short, or expose to heat >60 °C.
- Charge only with the onboard TP4056 (USB-C). Do not use an external
  charger.
- If the battery swells, stops holding charge, or gets hot during use,
  replace it immediately.
- The TP4056 has over-charge (4.2 V) and over-discharge (2.9 V)
  protection. Do not bypass.

## Radiation

**The device does not produce, contain, or require any radioactive
source.** It only detects cosmic rays and background radiation that
are already present in the environment. There is no radiological
hazard associated with building, using, or disassembling this device.

The optional calibration source (Cs-137, mentioned in the calibration
guide) is a licensed radioactive material that you must obtain and
handle according to your local regulations. It is **not** required for
normal operation.

## Scintillator handling

The EJ-200 plastic scintillator tiles are chemically inert and
non-toxic. However:

- Do not scratch or chip the tiles — surface quality affects light
  collection.
- Optical grease (EJ-550) is skin-safe but should not be ingested. Wash
  hands after handling.
- The tiles are slightly flammable (they are a plastic). Do not solder
  near them.

## Electrostatic discharge

The SiPMs are ESD-sensitive. Handle them with a grounded wrist strap
and on an ESD-safe mat. The OPA2356 TIA inputs are protected by
1N4148 clamp diodes but are still sensitive to large static discharges.