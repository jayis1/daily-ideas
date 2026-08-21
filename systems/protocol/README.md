# Unified Device Protocol

Every SoC design keeps its native firmware and physical transport. An adapter translates BLE characteristics, Wi-Fi messages, LoRaWAN uplinks, UART frames, or SD records into one logical envelope:

```json
{
  "specversion": "1.0",
  "id": "01J...",
  "time": "2026-08-22T12:00:00Z",
  "source": "soc://site/device-instance",
  "device_type": "halo-pin",
  "node": "observe",
  "type": "telemetry.v1",
  "subject": "air.particle_distribution",
  "data": {}
}
```

The envelope separates system meaning from transport. A local deployment can use newline-delimited JSON over UART; a fleet can carry the same object over MQTT or encode it as CBOR over LoRaWAN.

## Message types

| Type | Producer → consumer | Meaning |
|---|---|---|
| `telemetry.v1` | Observe → Reason | Calibrated samples or windows |
| `finding.v1` | Reason → Coordinate | Derived result with confidence and provenance |
| `command.v1` | Reason/Coordinate → Act | Requested state change, expiry, and safety limits |
| `feedback.v1` | Act → Observe/Reason | Accepted/rejected command and measured outcome |
| `health.v1` | Any → Coordinate | Power, connectivity, calibration, and fault state |
| `policy.v1` | Coordinate → Reason/Act | Deployment limits and operator intent |

Commands must carry an expiry time and idempotency key. Act nodes reject expired, duplicate, unauthorized, or out-of-bounds commands locally. Safety interlocks remain functional without a network connection.

## Identity

The stable type is the device directory name, such as `therma-weave`. Each physical unit adds a deployment-scoped instance ID. Messages retain both so the platform can route by capability while audit history remains tied to real hardware.
