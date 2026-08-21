# Iono Pin — Safety Notes

⚠️ **Read this before building or operating.**

## 1. Radioactive source (Ni-63)

### What it is
Nickel-63 is a pure beta emitter (E_max = 67 keV, half-life 100 years). At ≤ 37 kBq (1 µCi), the sealed foil is **exempt-quantity radioactive material** in most jurisdictions:
- **US**: 10 CFR 30.71 Schedule B — Ni-63 exempt quantity is 100 µCi (3.7 MBq), so 1 µCi is well below.
- **EU**: EURATOM 2013/59 (Basic Safety Standards) — exempt activity for Ni-63 is 100 kBq, so 37 kBq is below.
- **Check your country** — rules vary. In some jurisdictions any radioactive material requires a license.

### Why it's safe at this activity
- **Beta range**: Ni-63 betas travel < 10 cm in air and are stopped by the drift tube wall + enclosure. No external dose at contact distance.
- **Sealed source**: the Ni-63 is electroplated on a metal foil and sealed. No contamination risk if the foil is intact.
- **No neutron/gamma**: pure beta, no secondary radiation.

### Handling rules
- Do **not** open, cut, or grind the source foil.
- Store in its designated shielded container when not in use.
- If the foil is damaged, treat as contamination: double-bag, contact your radiation safety officer / local authority.
- Do **not** eat, drink, or smoke near the source.
- Dispose of via licensed radioactive-waste channels — never household trash.

### Non-radioactive alternative
The **corona-discharge ionizer** (tungsten needle + 2N7002 driver) avoids radioactive material entirely, at ~2× lower sensitivity and slightly less stable ionization. **Recommended for educational and unrestricted use.**

## 2. High voltage (2125 V drift, 5 kV supply)

### Hazard
- 2125 V across the drift tube and 5 kV on the EMCO supply can deliver a **painful, potentially dangerous electric shock**.
- The drift tube resistor chain (80 MΩ total) limits current to ~25 µA at 2125 V, which is below the let-go threshold but still unpleasant.

### Mandatory safety chain
1. **Reed interlock** (PC3): the HV/ionizer cannot enable unless the enclosure lid is closed. Never bypass.
2. **TLV3201 over-current comparator** (PC4): if the HV rail draws excess current (short, arc), it latches a fault and kills the HV instantly.
3. **IWDG watchdog**: if firmware hangs, the MCU resets and HV defaults to OFF.
4. **250 °C thermal fuse** on the EMCO module: hardware overtemperature cutoff.
5. **10 MΩ bleeder resistor** across the HV output: discharges the drift tube to safe voltage in <10 ms after shutdown.
6. **Never operate with the lid open.** The interlock exists for a reason.

### Before working on the device
1. Power off + remove 18650.
2. Wait 30 s for the bleeder to discharge the HV.
3. Verify with a multimeter that the drift tube rings read < 10 V.
4. Only then touch the drift tube / Faraday plate / ionizer.

## 3. Toxic samples

**Do not introduce actual chemical warfare agents, explosives, or illicit drugs.**

The device is designed for **simulants** and **safe reference compounds** at trace levels:
- **DMMP** (dimethyl methylphosphonate) — Sarin simulant, low toxicity, available from chemical suppliers.
- **DNT** (dinitrotoluene) — TNT simulant, less sensitive than TNT.
- **Acetone, toluene, ethanol** — common VOCs for testing the RIP/product-ion behavior.
- **Ammonia solution** (dilute) — for the ammonium adduct peak.

If you do not have a controlled-substance handling protocol, **do not** acquire or test with real CWAs, explosives, or drugs. This is an educational/research instrument, not a certified detector.

## 4. Ozone (corona ionizer)

If using the corona-discharge alternative, it produces **ozone (O₃)** at low levels. Operate in a ventilated area. The drift-gas flow is closed-loop through a charcoal scrubber, but some ozone may escape at the exhaust.

## 5. Ethical use

This is an open instrument for **understanding** a widely-deployed security technology. It is not a substitute for certified detectors in safety-critical settings (aviation security, military, first response). Do not use it to defeat or circumvent security screening. Do not use it to test for controlled substances on people without consent and legal authority.

## 6. Legal

You are responsible for compliance with all applicable laws regarding radioactive material, high-voltage equipment, and chemical handling in your jurisdiction. The MIT license covers the design files; it does not grant legal permission to handle regulated materials.