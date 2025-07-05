# TsuryPhone Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/Tsury/TsuryPhone.svg)](https://github.com/Tsury/TsuryPhone/releases)
[![License](https://img.shields.io/github/license/Tsury/TsuryPhone.svg)](LICENSE)

A comprehensive Home Assistant integration for controlling and monitoring your TsuryPhone vintage rotary phone device.

## 📱 What is TsuryPhone?

TsuryPhone is a vintage rotary phone converted to work with modern cellular networks, featuring ESP32-based hardware that connects to GSM networks while maintaining the classic rotary dial and bell ringing experience.

## ✨ Features

### 📊 Monitoring
- **Real-time Phone State**: Idle, In Call, Dialing, Incoming Call, etc.
- **Call Information**: Active call number, call ID, call waiting status
- **System Statistics**: Uptime, memory usage, call counters, reset counts
- **WiFi Status**: Connection status, IP address, signal strength
- **Hardware Metrics**: CPU frequency, flash size, sketch size

### 🎮 Controls
- **Call Management**: Make calls, hang up, call from phonebook
- **Do Not Disturb**: Enable/disable DnD with custom time schedules
- **Device Management**: Reset, reboot, ring device remotely
- **Phonebook Management**: Add/remove contacts via services
- **Call Screening**: Block unwanted numbers

### 🏠 Home Assistant Entities

#### Sensors (13)
- Phone state, uptime, memory, WiFi signal
- Call counters, active call info
- Hardware specifications

#### Binary Sensors (4)
- Call active, DnD status, WiFi connected, call waiting

#### Controls (4)
- Buttons: Hangup, Reset, Reboot, Ring
- Switch: Do Not Disturb toggle
- Numbers: DnD time configuration (4 entities)
- Select: Phonebook contacts for calling

#### Services (6)
- Call number, ring device
- Phonebook: add/remove entries
- Call screening: add/remove blocked numbers

## 🚀 Installation via HACS

### Prerequisites
1. **HACS installed** in your Home Assistant
2. **TsuryPhone device** with Home Assistant integration enabled
3. **Same network** - device and HA on same WiFi/LAN

### Step 1: Install Integration

#### Option A: HACS Default Repository (Recommended)
1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Search for **"TsuryPhone"**
4. Click **Download**
5. Restart Home Assistant

#### Option B: Custom Repository
1. Open HACS → **Integrations**
2. Click **⋮** (menu) → **Custom repositories**
3. Add repository: `https://github.com/Tsury/TsuryPhone`
4. Category: **Integration**
5. Click **Add** → **Download**
6. Restart Home Assistant

### Step 2: Enable Integration in Device
Build and flash your TsuryPhone with Home Assistant enabled:
```bash
# Use any HA-enabled environment
pio run -e debugHA -t upload
# or
pio run -e releaseHA -t upload
```

### Step 3: Add Device to Home Assistant
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **"TsuryPhone"**
4. Enter your device's **IP address**
5. Click **Submit**

### Step 4: Verify Installation
✅ Check that you see:
- TsuryPhone device in your devices list
- 13 sensors, 4 binary sensors, and various controls
- Real-time phone state updates

## 📖 Quick Start Examples

### Make a Call
```yaml
service: tsuryphone.call_number
data:
  device_id: "tsuryphone_device_id"
  number: "1234567890"
```

### Ring Device as Doorbell
```yaml
automation:
  - alias: "Ring Phone When Doorbell Pressed"
    trigger:
      platform: state
      entity_id: binary_sensor.doorbell
      to: "on"
    action:
      service: tsuryphone.ring_device
      data:
        device_id: "tsuryphone_device_id"
        duration: 5000  # 5 seconds
```

### Auto Do Not Disturb
```yaml
automation:
  - alias: "Auto DnD at Night"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      service: switch.turn_on
      target:
        entity_id: switch.tsuryphone_dnd
```

## 🔧 Configuration

### Device Settings
Access device configuration at: `http://[device-ip]/`

### Integration Options
Configure via **Settings** → **Devices & Services** → **TsuryPhone**

## 📚 Full Documentation

For complete documentation, automation examples, troubleshooting, and API reference, see:
[**Complete Integration Guide**](custom_components/tsuryphone/README.md)

## 🐛 Troubleshooting

### Common Issues

**❌ Integration not found**
- Ensure HACS is installed and updated
- Check if repository was added correctly
- Restart Home Assistant

**❌ Device not connecting**
- Verify device IP address is correct
- Ensure device and HA are on same network
- Check that HA integration is enabled in firmware

**❌ Missing entities**
- Restart Home Assistant after firmware updates
- Check HA logs for errors
- Verify device responds at `http://[device-ip]/status`

### Getting Help
- 📋 [Issues](https://github.com/Tsury/TsuryPhone/issues)
- 💬 [Discussions](https://github.com/Tsury/TsuryPhone/discussions)
- 📖 [Wiki](https://github.com/Tsury/TsuryPhone/wiki)

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ If you find this project useful, please give it a star on GitHub!**
