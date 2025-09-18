# Presence Detection System

A Raspberry Pi-based human presence detection system that automatically controls a Samsung Frame 43" TV based on room occupancy.

⚠️ **PROJECT STATUS: TV CONTROL UNDER DEVELOPMENT** ⚠️

The presence detection system is **fully functional** but TV control remains **unreliable** due to Samsung WebSocket API limitations. Multiple control methods have been attempted and documented in `archive_failed_attempts/`.

## Current Status

✅ **Working Components:**
- **Human Presence Detection**: DFRobot SENS0395 mmWave sensor via UART (2m range configured)
- **Sensor Framework**: Complete UART communication and GPIO trigger modes
- **Configuration System**: JSON-based configuration with development modes
- **Logging Infrastructure**: Comprehensive logging with file/console output

⚠️ **Problematic Components:**
- **Samsung TV Control**: Network API has intermittent WebSocket failures
- **Power State Management**: Connection reuse issues cause stale connections

❌ **Failed Control Methods (See `archive_failed_attempts/`):**
- Direct Tapo PyP100 smart plug control (authentication failures)
- Amazon Alexa AlexaPy integration (2FA/security blocking)
- Kasa smart plug protocol (device incompatibility)

## Hardware Requirements

✅ **Currently Working:**
- **Raspberry Pi CM5** (tested and configured)
- **DFRobot SENS0395 mmWave sensor** (UART on `/dev/ttyAMA1`, 2m detection range)
- **Network Connection**: WiFi connectivity established

⚠️ **TV Control Hardware (Unreliable):**
- **Samsung Frame 43" TV** (WebSocket API intermittently functional)
- **TP-Link Tapo Smart Plug** (manual Alexa control works, API control failed)

### Eliminated Hardware ❌
- ~~Adafruit IR blaster~~ - Complex setup, limited reliability
- ~~HDMI CEC connection~~ - 25-second cooldowns, poor power-off support

## Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd Presence

# Virtual environment already configured with dependencies
source venv/bin/activate
```

### 2. Test Presence Detection (Working)
```bash
# Activate virtual environment (always required)
source venv/bin/activate

# Test presence detection with real sensor
python3 presence_sensor.py --dev --dry-run --verbose

# Test sensor UART communication directly
python3 debug_sensor_strings.py --port /dev/ttyAMA1 --duration 30
```

### 3. Test TV Control (Unreliable)
```bash
# Discover Samsung TV on network
python3 discover_samsung_tv.py

# Test power control (may fail intermittently)
python3 samsung_tv_control.py status    # Check current TV state
python3 samsung_tv_control.py on        # Turn TV on
python3 samsung_tv_control.py off       # Turn TV off
```

### 4. Current Functional Test
```bash
# Test the working presence detection system
python3 presence_sensor.py --dev --dry-run --verbose
# This will show presence detection working with simulated TV control
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

### Sensor Configuration (Working)
```json
{
  "sensor": {
    "mode": "uart",                    // UART mode (working)
    "uart": {
      "port": "/dev/ttyAMA1",          // UART port for CM5
      "baudrate": 115200,              // Communication speed
      "timeout": 1.0                   // Read timeout
    },
    "trigger": {
      "gpio_pin": 14,                  // GPIO pin (backup mode)
      "debounce_time": 2.0             // Sensor debounce seconds
    }
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

✅ **Completed & Working:**
- **Presence Detection**: UART sensor communication fully functional
- **Sensor Framework**: Both UART and GPIO trigger modes implemented
- **Configuration System**: Complete JSON-based configuration
- **Development Tools**: Debug utilities, dry-run modes, verbose logging
- **Hardware Integration**: Raspberry Pi CM5 + DFRobot SENS0395 working

⚠️ **Problematic (Documented):**
- **Samsung TV Control**: Intermittent WebSocket API failures
- **Smart Plug Control**: All attempted methods failed (see `archive_failed_attempts/`)

🔄 **Next Phase Options:**
- Investigate reliable hardware control methods (IR, relay)
- Implement IFTTT webhooks as cloud-based alternative
- Focus on presence detection applications beyond TV control

See `status.md` for detailed development progress, failed attempts, and technical decisions.

## License

MIT License - see LICENSE file for details

## Contributing

Pull requests welcome! Please ensure:
- Code follows Python PEP 8 style guide  
- Virtual environment activated for testing
- Samsung TV network control tested
- Configuration changes documented
- Update status.md for significant changes