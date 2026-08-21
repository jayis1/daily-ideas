# Four-Node Platform

This is the unifying system for the complete [SoC Device Inventions repository](https://github.com/jayis1/SoC-Device-Inventions). It turns all 57 independent hardware designs into one interoperable family of sensors, scientific instruments, controllers, interfaces, and network nodes.

The two repositories have distinct responsibilities:

| Repository | Responsibility |
|---|---|
| [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) | Canonical device designs: schematics, firmware, BOMs, host tools, assembly instructions, and device-level documentation |
| [Daily Ideas Unified System](https://github.com/jayis1/daily-ideas) | Fleet registry, common protocol, four-node roles, composition rules, validation, and the larger system interface |

No device is replaced or hidden by this system. Each remains independently buildable in the source collection and also gains a defined place in the unified architecture.

## The four nodes

```text
                     findings
  physical world                 people + fleet
        │                            ▲
        ▼                            │
  ┌───────────┐ telemetry ┌────────┴───┐
  │  OBSERVE  ├──────────►│   REASON   │◄──── policy ────┐
  └─────▲─────┘           └─────┬──────┘                 │
        │ feedback              │ commands         ┌─────┴──────┐
        │                       ▼                  │ COORDINATE │
        │                 ┌────────────┐           └────────────┘
        └─────────────────┤    ACT     │
                          └────────────┘
```

| Node | Responsibility | Example device foundations |
|---|---|---|
| Observe | Acquire calibrated physical measurements and events | Neuro Sense Puck, Canopy Listener, Halo Pin, Terra Pin |
| Reason | Fuse signals, run DSP/ML, and produce findings or commands | Phase Scope, Spectra Charm, Echo Mote, Sky Lens |
| Act | Perform guarded physical work and close the feedback loop | Mycelium Node, Therma Weave, Levia Forge, Glyph Press |
| Coordinate | Connect users, history, policies, and groups of deployments | Hive Mind, Soil Whisper, Tremor Tile, Sap Watch |

These are logical roles, not four mandatory circuit boards. A small deployment may place several roles on one SoC; a larger deployment can replicate each node and connect many devices. The stable boundary is the [Unified Device Protocol](./protocol/), so hardware can evolve without rebuilding the entire system.

## One fleet, all 57 designs

Every imported design is registered in [`devices.json`](./devices.json), including instruments, monitors, creative interfaces, controllers, and fabrication tools. A device can serve several roles: for example, Mycelium Node observes its chamber, reasons over environmental state, acts through PID-controlled equipment, and coordinates remote monitoring.

The registry is deliberately separate from firmware. Each design retains its native real-time implementation while a thin adapter publishes the shared protocol. This lets the greater system combine devices by capability instead of forcing 57 firmware projects onto one hardware stack.

### How every device is linked

[`devices.json`](./devices.json) is the complete connection map. Every entry uses the original SoC repository directory name as its stable device type, identifies its application domain, and assigns all roles the device can fulfill. The registry currently covers all 57 source directories with no omissions.

Most measurement instruments combine **Observe** and **Reason**. Devices with motors, heaters, excitation sources, haptics, printing mechanisms, or environmental controls also join **Act**. Field monitors and connected tools that publish fleet state additionally join **Coordinate**. Multi-purpose designs can participate in all four roles.

```text
SoC Device Inventions repository
  │
  ├── schematics + BOM ───────► physical device
  ├── firmware ───────────────► native sensing/control
  └── scripts + documentation ► protocol adapter
                                      │
                                      ▼
                              Unified Device Protocol
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                 Observe ─────────► Reason ──────────► Act
                                      ▲                 │
                                      └── Coordinate ◄──┘
```

### Interoperability boundary

The [Unified Device Protocol](./protocol/) normalizes six message families: `telemetry`, `finding`, `command`, `feedback`, `health`, and `policy`. Transport adapters can carry those messages over BLE, Wi-Fi, MQTT, LoRaWAN, UART, removable storage, or another device-native link. This preserves hardware-specific real-time behavior while giving the greater system one consistent identity, routing, audit, and safety model.

The architecture does not require every device to communicate directly with every other device. Devices interconnect through role contracts. An Observe implementation can therefore be replaced or multiplied without rewriting Reason, and an Act implementation can enforce local safety even when Coordinate is offline.

### Building a complete deployment

A unified deployment selects devices by capability rather than by repository position. For example:

1. one or more **Observe** devices acquire calibrated physical measurements;
2. a **Reason** device or service fuses measurements and produces confidence-scored findings;
3. an **Act** device performs an authorized, bounded response and reports feedback; and
4. **Coordinate** stores history, applies policy, presents the system to users, and joins multiple local loops into a fleet.

The result can range from a single multi-role SoC to a replicated network containing many instances of several designs.

## Try it

```bash
daily-ideas system list
daily-ideas system info observe
daily-ideas system devices
daily-ideas system devices --node act
daily-ideas system devices --domain analytical-chemistry
daily-ideas system doctor
```

The canonical topology is [`platform.json`](./platform.json). `system doctor` checks that it contains exactly four uniquely named nodes, that every link resolves, and that all 57 device directories appear exactly once in the unified registry.

## From invention to system

1. Start with a device under `soc-devices/` and identify the role it fulfills.
2. Wrap its measurements or controls in the matching versioned contract.
3. Connect it to one adjacent node and validate a single end-to-end path.
4. Add coordination only when the local observe–reason–act loop is safe and useful.

This keeps each invention independently buildable while allowing several inventions to become one larger product.

## Source and navigation

- Browse the original hardware collection: [github.com/jayis1/SoC-Device-Inventions](https://github.com/jayis1/SoC-Device-Inventions)
- Browse the imported device tree in this monorepo: [`soc-devices/`](./soc-devices/)
- Inspect the complete connection registry: [`devices.json`](./devices.json)
- Read the shared protocol: [`protocol/`](./protocol/)
- Return to the unified repository front page: [Daily Ideas](https://github.com/jayis1/daily-ideas)
