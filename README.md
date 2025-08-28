# Presence Detection System

A Raspberry Pi-based human presence detection system that automatically controls a Samsung Frame 43" TV based on room occupancy using Samsung's network API.

## Features

- **Network-Based TV Control**: Reliable Samsung TV control via WiFi/Ethernet (no IR hardware required)
- **Accurate Power State Detection**: Real-time TV state monitoring using Samsung PowerState API
- **Human Presence Detection**: DFRobot SENS0395 mmWave sensor for reliable occupancy detection
- **Smart Power Management**: Immediate TV on, 10-minute delayed TV off
- **Auto-Discovery**: Automatic Samsung TV detection and configuration on local network
- **Development Mode**: Dry-run testing with verbose logging
- **Virtual Environment**: Clean dependency management with isolated Python environment

## Hardware Requirements

- **Raspberry Pi** (tested on Pi 4/5)
- **DFRobot SENS0395 mmWave sensor** (GPIO 14, configurable)
- **Samsung Frame TV** (or other Samsung Smart TV with network API support, 2016+)
- **Network Connection**: TV and Pi on same network (WiFi/Ethernet)

### ~~Eliminated Hardware~~ ✅
- ~~Adafruit IR blaster~~ - No longer needed with network control
- ~~HDMI CEC connection~~ - Optional backup only

## Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd presence-detection

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install samsungtvws[async,encrypted]
```

### 2. Discover and Configure TV
```bash
# Activate virtual environment (always required)
source venv/bin/activate

# Auto-discover Samsung TV on network
python3 discover_samsung_tv.py
```
This will automatically configure your TV's IP address, port, and Wake-on-LAN settings in `config.json`.

### 3. Test TV Control
```bash
# Test power control
python3 samsung_tv_control.py status    # Check current TV state
python3 samsung_tv_control.py on        # Turn TV on
python3 samsung_tv_control.py off       # Turn TV off
python3 samsung_tv_control.py info      # Show TV details
```

### 4. Test Presence Detection System
```bash
# Test in development mode (simulated sensor)
python3 presence_sensor.py --dev --dry-run --verbose

# With actual sensor connected
python3 presence_sensor.py --dev --verbose
```

## Configuration

The system uses `config.json` for all settings. Key sections:

### Samsung TV Network Settings (Auto-configured)
```json
{
  "samsung_tv": {
    "enabled": true,
    "ip_address": "192.168.1.100",      // Auto-detected
    "port": 8002,
    "token_file": "/home/user/.samsung_tv_token",
    "mac_address": "aa:bb:cc:dd:ee:ff", // Auto-detected for Wake-on-LAN
    "wake_on_lan": true,
    "connection_timeout": 10
  }
}
```

### Sensor Configuration
```json
{
  "sensor": {
    "gpio_pin": 14,           // GPIO pin for presence sensor
    "debounce_time": 2.0,     // Sensor debounce seconds
    "mode": "trigger"         // Sensor mode (trigger/uart)
  }
}
```

### Timing Configuration
```json
{
  "tv_control": {
    "turn_off_delay": 600,    // 10 minutes before TV off
    "turn_on_delay": 0,       // Immediate TV on
    "retry_attempts": 3,      // Connection retry count
    "retry_delay": 2          // Seconds between retries
  }
}
```

### Development Options
```json
{
  "dev_mode": {
    "enabled": false,         // Development mode
    "dry_run": false,         // Simulate TV control
    "verbose": false,         // Verbose logging
    "log_to_console": true    // Console vs file logging
  }
}
```

## Available Commands

### TV Control Commands
```bash
# Always activate virtual environment first
source venv/bin/activate

# Direct TV control
python3 samsung_tv_control.py on           # Turn TV on (smart method selection)
python3 samsung_tv_control.py off          # Turn TV off (to standby)
python3 samsung_tv_control.py toggle       # Smart toggle based on current state
python3 samsung_tv_control.py status       # Show current power state
python3 samsung_tv_control.py info         # Show TV information

# Context-aware control (recommended for automation)
python3 samsung_tv_control.py ensure-on    # Ensure TV is on
python3 samsung_tv_control.py ensure-off   # Ensure TV is off

# Discovery and configuration
python3 discover_samsung_tv.py             # Find and configure Samsung TVs
```

### Presence Detection Commands
```bash
# Development testing
python3 presence_sensor.py --dev --verbose       # Development with real sensor
python3 presence_sensor.py --dev --dry-run       # Simulated TV control
python3 presence_sensor.py --dev --dry-run --verbose  # Full simulation

# Custom configuration
python3 presence_sensor.py --config custom.json  # Use custom config file
```

## Samsung TV Network Control

The system uses Samsung's WebSocket API for reliable TV control over the network.

### Key Benefits
- **No Hardware Required**: Eliminates IR blaster and complex wiring
- **Reliable Control**: Works through walls, no line-of-sight needed
- **Accurate State Detection**: Real-time power state from TV API
- **Faster Response**: Immediate network commands vs IR delays
- **Additional Features**: Access to TV info, apps, Frame art mode

### Technical Details
- **Supported Models**: Samsung TVs 2016+ with TizenOS
- **Power Control**: WebSocket toggle commands (`on` ↔ `standby`)
- **Power On Methods**: WebSocket (from standby), Wake-on-LAN (from fully off)
- **State Detection**: Samsung PowerState API reports `on`, `standby`, or unreachable
- **Network Requirements**: TV and Pi on same network, port 8002 accessible

### Samsung API Limitations (Research Findings)
- ❌ Explicit `KEY_POWERON`/`KEY_POWEROFF` commands not supported by Samsung
- ✅ `KEY_POWER` (toggle) commands work reliably
- ✅ PowerState API provides accurate state information
- ℹ️ Samsung TVs remain network-reachable in standby mode

## Architecture

### Control Flow
1. **Presence Detected** → Immediate TV power on (WebSocket/Wake-on-LAN)
2. **TV ON State** → Monitor continued presence
3. **No Presence** → Start 10-minute countdown timer  
4. **Timer Expires** → TV power off to standby mode
5. **Presence Returns** → Cancel timer, ensure TV remains on

### Smart Power Control Strategy
**Power ON Logic:**
1. Check current TV state via PowerState API
2. If TV is `on` → Already on, return success
3. If TV is `standby` → Use WebSocket toggle (instant)
4. If TV is unreachable → Use Wake-on-LAN + WebSocket fallback

**Power OFF Logic:**
1. WebSocket toggle command: `on` → `standby`
2. Verify state change via PowerState API
3. Samsung TVs remain network-accessible in standby

## Project Structure

```
presence_sensor.py          # Main application with Samsung network integration
samsung_tv_control.py       # Samsung TV network control module  
discover_samsung_tv.py      # TV discovery and auto-configuration
config.json                 # System configuration (GPIO, network, timing)
venv/                       # Python virtual environment with dependencies
├── lib/python3.11/site-packages/
│   └── samsungtvws/        # Samsung TV WebSocket library
lib/                        # Future modular components (planned)
├── sensor.py              # Sensor abstraction (planned)
└── state_machine.py       # State management (planned)
tests/                     # Test suite (planned)
scripts/                   # Installation automation (planned)
└── install.sh            # Service installation (planned)
```

## Installation as Service (Production)

### Manual Service Setup
```bash
# Create service file
sudo tee /etc/systemd/system/presence-sensor.service << EOF
[Unit]
Description=Presence Detection TV Control
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/presence-detection
Environment=PATH=/home/pi/presence-detection/venv/bin
ExecStart=/home/pi/presence-detection/venv/bin/python presence_sensor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable presence-sensor
sudo systemctl start presence-sensor

# Check status
sudo systemctl status presence-sensor
journalctl -u presence-sensor -f
```

## Troubleshooting

### TV Control Issues
```bash
# Test network connectivity to TV
python3 samsung_tv_control.py status --debug

# Check TV network settings
python3 discover_samsung_tv.py

# Verify TV settings:
# - TV on same network as Pi
# - Smart Hub features enabled
# - Network standby enabled (for Wake-on-LAN)
```

### Sensor Issues
```bash
# Test sensor in development mode
python3 presence_sensor.py --dev --verbose

# Check GPIO connections:
# - Sensor GPIO 14 (configurable in config.json)
# - 5V power supply to sensor
# - Ground connection
```

### Virtual Environment Issues
```bash
# Recreate virtual environment if needed
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install samsungtvws[async,encrypted]
```

### Common Error Messages
- **"TV unreachable"**: Check TV IP address and network connectivity
- **"SSL verification warnings"**: Normal, warnings are suppressed automatically
- **"TV still reachable after power toggle"**: Expected behavior, Samsung TVs stay in network standby
- **"CEC cooldown active"**: CEC has 25-second cooldown, WebSocket method used instead

## Development Status

- ✅ **Samsung Network Control**: Complete and tested
- ✅ **TV Discovery & Auto-Configuration**: Complete
- ✅ **Power State Detection**: Complete with Samsung PowerState API
- ✅ **Development Framework**: Complete with dry-run and verbose modes
- ⏳ **Sensor Integration**: Ready for physical sensor connection
- 🔄 **Service Deployment**: Planned next phase

See `status.md` for detailed development progress and technical decisions.

## License

MIT License - see LICENSE file for details

## Contributing

Pull requests welcome! Please ensure:
- Code follows Python PEP 8 style guide  
- Virtual environment activated for testing
- Samsung TV network control tested
- Configuration changes documented
- Update status.md for significant changes