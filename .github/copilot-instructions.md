# TsuryPhone Home Assistant Integration - AI Coding Agent Instructions

## Project Overview

This repository contains the **Home Assistant custom integration** for TsuryPhone - a vintage rotary phone converted to work with modern cellular networks. This integration communicates with the ESP32-based hardware device.

**Related Repository:** [`TsuryPhone`](https://github.com/Tsury/TsuryPhone) - ESP32 firmware for the physical device

## Core Architecture

### Custom Integration Structure

Standard HA custom component using coordinator pattern:

- `coordinator.py` - Main data coordinator with WebSocket real-time updates and HTTP polling
- Platform files (`sensor.py`, `switch.py`, etc.) - 13 sensors, 4 binary sensors, controls
- `config_flow.py` - UI-based configuration flow with device discovery
- `services.py` - Custom services for phonebook management, call control

### Communication with Device

- **HTTP REST API:** Actions (call, hangup, phonebook management) via `/action` endpoint
- **WebSocket:** Real-time state updates from device at `/ws`
- **Webhook Configuration:** Automatically configures device with HA server URL

## Development Workflows

### Integration Development

```bash
# Install in development HA instance
cp -r custom_components/tsuryphone /config/custom_components/
# Restart HA, then add integration via UI

# Check logs for debugging
tail -f /config/home-assistant.log | grep tsuryphone
```

### Testing Integration

```bash
# Test device connectivity
curl http://device-ip/status
curl http://device-ip/stats

# Verify entities in HA Developer Tools
# Check integration health in HA Settings > Integrations
```

## Key Patterns & Conventions

### Coordinator Pattern

```python
class TsuryPhoneDataUpdateCoordinator(DataUpdateCoordinator):
    async def _async_update_data(self) -> Dict[str, Any]:
        # HTTP polling for critical data (60s intervals)
        # WebSocket handles real-time updates
```

### Service Actions

```python
async def call_number(self, number: str) -> None:
    await self._make_action_request(ACTION_CALL, {"number": number})
```

### Entity Configuration

All entities use the coordinator for data updates and share common device info:

```python
@property
def device_info(self) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, self.coordinator.device_id)},
        name=self.coordinator.device_name,
        manufacturer=MANUFACTURER,
        model=MODEL,
    )
```

## API Endpoints (Device)

### Core Endpoints

- `GET /status` - Phone state, call info, DnD status, WiFi details
- `GET /stats` - Uptime, call counters, memory usage, hardware specs
- `POST /action` - Unified action endpoint with JSON payloads

### Action Payloads

```json
{"action": "call_custom", "number": "1234567890"}
{"action": "ring_pattern", "durations": [1000, 500], "repeats": 3}
{"action": "add_quick_dial", "name": "John", "number": "555-0123"}
```

## Integration Points with Firmware

### Device Discovery

- **mDNS:** Auto-discovery via `tsuryphone.local`
- **Manual:** IP address configuration in integration setup

### Real-time Updates

- **WebSocket connection** for instant state changes
- **HTTP polling fallback** for reliability (60s intervals)
- **Fast refresh** (1s intervals) after user actions

### Configuration Sync

The integration automatically configures the device with HA server details for webhook functionality.

## Error Handling & Debugging

### Common Issues

- **Connection failures:** Check device IP and network connectivity
- **Missing entities:** Restart HA after firmware updates
- **WebSocket drops:** Integration handles reconnection automatically
- **Action timeouts:** 10s timeout with proper error reporting

### Debug Logging

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.tsuryphone: debug
```

### Health Checks

- Monitor coordinator update success in HA logs
- Check device `/stats` endpoint for memory issues
- Verify WebSocket connection status in coordinator

## Testing & Validation

### HACS Integration

This component is designed for HACS distribution:

```yaml
# hacs.json configuration
{ "name": "TsuryPhone", "domain": "tsuryphone", "iot_class": "local_polling" }
```

### Entity Verification

- 13 sensors (state, uptime, memory, call info, hardware specs)
- 4 binary sensors (call active, DnD, WiFi, call waiting)
- Controls (buttons, switches, selects, time inputs)
- 6 custom services for device management

## Code Organization Principles

- **Async/await patterns:** All network calls are properly async
- **Error boundaries:** Graceful degradation when device unavailable
- **Memory efficiency:** Reasonable polling intervals, WebSocket for real-time data
- **User experience:** Fast feedback for actions, reliable state updates

When modifying the integration, ensure compatibility with firmware builds that don't have `HOME_ASSISTANT_INTEGRATION` enabled - the integration should handle connection failures gracefully.
