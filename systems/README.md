# unified TREE

The canonical home of this system is [github.com/jayis1/unified-TREE](https://github.com/jayis1/unified-TREE). This directory is its integration inside Daily Ideas.

**unified TREE** is the unifying system for the complete and growing [SoC Device Inventions repository](https://github.com/jayis1/SoC-Device-Inventions). **Every current and future hardware design becomes a node in the greater system.** Together they form one interoperable family of sensors, scientific instruments, controllers, interfaces, and network nodes.

The two repositories have distinct responsibilities:

| Repository | Responsibility |
|---|---|
| [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) | Canonical device designs: schematics, firmware, BOMs, host tools, assembly instructions, and device-level documentation |
| [unified TREE](https://github.com/jayis1/unified-TREE) | Node registry, common protocol, four functional roles, composition rules, validation, and the larger system interface |

No device is replaced or hidden by this system. Each remains independently buildable in the source collection and also gains a defined place in the unified architecture.

## A growing node tree and four roles

The device inventions are the nodes. **Observe, Reason, Act, and Coordinate are roles those nodes perform**, not four additional devices. A node can perform one role or several roles depending on its sensors, processing, actuators, and communications.

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

These roles are logical capabilities, not four mandatory circuit boards. A small deployment may place several roles on one SoC node; a larger deployment can connect and replicate many device nodes. The stable boundary is the [Unified Device Protocol](./protocol/), so hardware can evolve without rebuilding the entire system.

## One fleet for every design

Every imported design is registered in [`devices.json`](./devices.json), including instruments, monitors, creative interfaces, controllers, and fabrication tools. A device can serve several roles: for example, Mycelium Node observes its chamber, reasons over environmental state, acts through PID-controlled equipment, and coordinates remote monitoring.

The registry is deliberately separate from firmware. Each design retains its native real-time implementation while a thin adapter publishes the shared protocol. This lets the greater system combine devices by capability without forcing every firmware project onto one hardware stack.

### The unified interconnection fabric

All nodes join the same logical message fabric. They do not need bespoke pairwise integrations:

```text
Current and future SoC device nodes
        │
        ├── publish: telemetry, findings, feedback, health
        └── consume: commands, policy, relevant findings
                            │
                            ▼
                 Unified Device Protocol
                            │
              identity + routing + contracts
                            │
          BLE / Wi-Fi / MQTT / LoRaWAN / UART / SD
```

Role-based routing creates the interconnections. Observe output routes to any compatible Reason node; Reason output routes to Act and Coordinate nodes; Act feedback returns to Observe and Reason; Coordinate policy returns to Reason and Act. Each physical node advertises its roles and device type from the registry, allowing the system to discover valid routes instead of hard-coding device pairs.

This creates a many-node system while keeping local safety and real-time control inside each SoC. Network loss may interrupt coordination, but it must never bypass an Act node's hardware interlocks or local limits.

### How every device is linked

[`devices.json`](./devices.json) is the growing connection map. Every entry uses the original SoC repository directory name as its stable device type, identifies its application domain, and assigns all roles the device can fulfill. It expands as new inventions are added.

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
daily-ideas system roles
daily-ideas system info observe
daily-ideas system nodes
daily-ideas system nodes --role act
daily-ideas system nodes --domain analytical-chemistry
daily-ideas system doctor
```

The canonical topology is [`platform.json`](./platform.json). `system doctor` checks that it contains exactly four uniquely named roles, that every role link resolves, and that every device-node directory appears exactly once in the unified registry. There is no maximum node count.

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
- Open the canonical unified repository: [unified TREE](https://github.com/jayis1/unified-TREE)
