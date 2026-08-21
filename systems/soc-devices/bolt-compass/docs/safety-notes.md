# Bolt Compass — Safety Notes

## ⚡ Lightning is lethal. Read this before deploying. ⚡

### The #1 rule

**Never deploy or stand near the Bolt Compass during an active storm
with lightning within 5 km.** The device is a *sensor* for studying
storms from a safe distance — it is NOT a storm-chasing instrument. A
direct or nearby lightning strike will:

- destroy the front end (spark-gap + TVS only survives nearby strikes,
  not direct hits),
- conduct lethal current through the tripod / ground strap,
- kill you.

### Safe deployment distances

| Storm distance | Action |
|---------------|--------|
| > 30 km | Deploy, listen, enjoy |
| 10–30 km | Monitor remotely (BLE/Wi-Fi), stay indoors |
| 5–10 km | **Do not approach the device.** Retrieve it later. |
| < 5 km | **Do not be outdoors at all.** |

### What the protection circuit handles

The E-field whip input has:
- a **90 V spark-gap** (Bourns 2049) to bleed static charge buildup,
- a **3.3 V TVS diode** (ESD9B3.3) to clamp transients,
- a **100 kΩ series resistor** to limit current.

This protects against:
- static charge buildup on the whip (fair-weather E-field),
- nearby (≥1 km) strike electromagnetic transients,
- ESD during handling.

This does **NOT** protect against:
- a direct strike to the whip / tripod,
- a strike within ~100 m (induced surge exceeds the spark-gap rating).

### Grounding

- The **enclosure must be bonded to earth ground** via the tripod and a
  ground strap to a ground rod. Never operate un-grounded — a floating
  enclosure can accumulate lethal charge.
- The ground strap should be at least 10 AWG and ≤ 3 m long.
- Do NOT use a household water pipe as a ground — use a dedicated
  ground rod.

### Indoor use

VLF sferics penetrate buildings, so the device works indoors (through
walls). However:
- Bearing accuracy degrades near **rebar / steel framing** (the loops
  see the rebar as a reflector).
- Keep ≥ 2 m from appliances, fluorescent lamps, and dimmer switches
  (they generate impulsive noise in the VLF band).
- Indoor deployment is fine for *detection* and *counting*; use outdoors
  for *bearing* and *distance*.

### Battery safety

- Use a protected 18650 cell (internal NTC + PTC).
- Do not leave in direct sun > 50 °C (the enclosure can get hot).
- The TP4056 + MCP73871 charge at 500 mA — do not bypass current
  limiting.
- If the cell swells or vents, discontinue use immediately.

### Solar panel

- The 5 W panel is weather-resistant but not submersion-rated.
- Do not short the panel leads (MCP73871 handles this, but don't).
- In a storm, the panel is fine — it has no exposed conductors that
  would attract a strike.