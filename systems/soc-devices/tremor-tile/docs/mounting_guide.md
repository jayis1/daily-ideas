# Tremor Tile — Mounting Guide

## Choosing a Mounting Location

The Tremor Tile measures structural vibration at the point where it is mounted. Location selection is critical for meaningful data.

### General Principles

1. **Mount on the structure itself** — not on secondary surfaces, conduits, or brackets
2. **Choose a rigid surface** — avoid thin panels, flexible mounts, or damping materials
3. **Minimize distance from the vibration source** — closer = stronger signal
4. **Mount at points of interest** — bearings, joints, mid-span, foundation
5. **Ensure good contact** — the entire bottom surface should be flush against the structure

### Application-Specific Guidance

#### Bridges
- **Mid-span**: Captures traffic-induced oscillation and natural frequency
- **Bearing supports**: Detects bearing degradation, expansion joint problems
- **Cable anchors**: Monitors cable tension changes (vibration frequency correlates with tension)
- **Foundation**: Detects soil-structure interaction, scour

#### Wind Turbines
- **Tower base**: Monitors tower oscillation and natural frequency
- **Nacelle**: Detects gearbox and generator vibration
- **Blade root**: Monitors blade imbalance and flutter

#### Buildings
- **Roof level**: Captures wind-induced oscillation
- **Foundation**: Monitors soil-structure interaction
- **Each floor**: Maps mode shapes across building height
- **Elevator machine room**: Monitors elevator vibration

#### Industrial Machinery
- **Bearing housing**: Direct measurement at the vibration source
- **Motor end bell**: Captures motor bearing and rotor vibration
- **Gearbox case**: Monitors gear mesh frequencies
- **Pump casing**: Detects cavitation, imbalance, misalignment

## Mounting Methods

### Magnetic Mount (Steel Surfaces)

The Tremor Tile includes two N35 neodymium magnets (6×3mm) embedded in the bottom case.

**For steel surfaces:**
1. Clean the surface with alcohol
2. Place the device flat against the surface
3. The magnets will snap into place automatically
4. Verify by gently tugging — the device should hold firmly

**Note:** Magnetic mounting may introduce a small amount of compliance (0.1–0.5mm), which attenuates frequencies above ~500Hz. For high-frequency measurements (>500Hz), use bolted or bonded mounting.

### Bolted Mount (Concrete, Steel, Wood)

Use the four M3 bolt holes in the corners of the PCB.

**For concrete:**
1. Drill 4× M3 holes using a hammer drill
2. Insert M3 concrete anchors
3. Bolt the device with M3×10 stainless steel screws
4. Apply thread-locking compound (Loctite 243)

**For steel:**
1. Drill 4× M3 holes or weld M3 studs
2. Bolt with M3×8 stainless steel screws
3. Use lock washers for vibration resistance

**For wood:**
1. Use M3×16 wood screws or M3 threaded inserts
2. Ensure the wood is solid (not plywood or particle board)

### Adhesive Mount (Any Surface)

Use 3M VHB 4941 double-sided tape (1mm thick) or 3M DP460 epoxy adhesive.

**3M VHB tape (removable):**
1. Clean both surfaces with alcohol
2. Apply tape to the bottom of the device
3. Press firmly for 30 seconds
4. Allow 24 hours for full bond strength

**Epoxy adhesive (permanent):**
1. Clean and roughen both surfaces
2. Mix 3M DP460 epoxy
3. Apply thin, even coat to device bottom
4. Press into position and hold for 5 minutes
5. Allow 24 hours cure time

## Orientation

The ADXL355 coordinate system:
- **X-axis**: Along the long dimension of the PCB (85mm)
- **Y-axis**: Along the short dimension (54mm)
- **Z-axis**: Perpendicular to the PCB surface (pointing up)

**Important:** For vertical structures (columns, walls), orient the device so that the Z-axis is perpendicular to the surface. The default firmware analyzes the Z-axis, which captures out-of-plane vibration.

For measuring vibration in a specific direction, orient accordingly:
- **Horizontal vibration**: X or Y axis aligned with motion direction
- **Vertical vibration**: Z axis aligned with gravity

## Environmental Considerations

### Temperature

| Range | Notes |
|-------|-------|
| -40°C to +85°C | ADXL355 operating range |
| -20°C to +60°C | Recommended practical range |
| +85°C to +125°C | LiFePO4 battery stress risk |

### Moisture

- **Indoor**: No special protection needed
- **Outdoor (sheltered)**: Conformal coat the PCB
- **Outdoor (exposed)**: Conformal coat + IP67 enclosure
- **Submerged**: Not recommended (pressure on ADXL355 affects readings)

### Vibration Environment

- **Continuous**: The ADXL355 is rated for continuous vibration
- **Shock**: Avoid >10,000g shocks (sensor damage)
- **EMI**: Keep away from high-current conductors (>10A) — they create magnetic fields that can induce noise

## Solar Panel Placement

For solar-powered operation:

1. The on-board PowerFilm MPT3.6-75 cell should face ambient light
2. Even 200 lux indoor lighting provides ~5mA charging current
3. For outdoor use, the solar cell can be extended via a 2-wire cable
4. **Never** expose the LiFePO4 battery to direct sunlight — keep it shaded

## Anti-Tamper

The reed switch on the PCB detects case opening. When the case is opened:
1. An alert is sent over LoRa
2. The buzzer sounds continuously
3. The status LED turns red
4. The event is logged to flash

This ensures data integrity — if someone moves or tampers with the device, you'll know.