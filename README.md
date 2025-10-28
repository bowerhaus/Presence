# Presence Detection System

A Raspberry Pi-based human presence detection system that automatically controls a Samsung Frame 43" TV based on room occupancy.

⚠️ **PROJECT STATUS: TV CONTROL UNDER DEVELOPMENT** ⚠️

The presence detection system is **fully functional** but TV control remains **unreliable** due to Samsung WebSocket API limitations. Multiple control methods have been attempted and documented in `archive_failed_attempts/`.

## Current Status

✅ **Working Components:**
- **Human Presence Detection**: DFRobot SENS0395 mmWave sensor via UART (3.5m max range configured)
- **LED Visual Feedback**: PWM-controlled LED on GPIO 12 with fade effects (brightness 0-100%)
- **Periodic Sensor Reset**: Automatic sensor reset every 60s to prevent firmware glitches from ground loop interference
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
- IR hardware control attempts (removed from codebase)

## Hardware Requirements

✅ **Currently Working:**
- **Raspberry Pi CM5** (tested and configured)
- **DFRobot SENS0395 mmWave sensor** (UART on `/dev/ttyAMA1`, 3.5m max detection range)
- **LED Indicator** (GPIO pin 12, PWM-controlled for brightness/fade effects)
- **Network Connection**: WiFi connectivity established

⚠️ **TV Control Hardware (Unreliable):**
- **Samsung Frame 43" TV** (WebSocket API intermittently functional)
- **TP-Link Tapo Smart Plug** (manual Alexa control works, API control failed)

### Eliminated Hardware ❌
- ~~IR hardware control~~ - All IR-related code removed from project
- ~~HDMI CEC connection~~ - CEC-related code removed from project

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
python3 power_on.py                      # Turn TV on
python3 power_off.py                     # Turn TV off
```

### 4. Production Setup (Recommended)
```bash
# Install and start as a system service
./service_manager.sh install    # One-time setup
./service_manager.sh start      # Start the service
./service_manager.sh logs       # Monitor activity

# This runs the presence detection automatically in the background
```

### 5. Development Testing
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
    "range_meters": {
      "min": 0.75,                     // Minimum detection range
      "max": 3.5,                      // Maximum detection range
      "apply_on_startup": true         // Apply range on startup
    },
    "reset_interval_seconds": 60       // Auto-reset every 60s (prevents firmware glitches)
  }
}
```

### Timing Configuration
```json
{
  "tv_control": {
    "turn_off_delay": 60,     // 60 seconds before TV off
    "turn_on_delay": 0,       // Immediate TV on
    "retry_attempts": 3,      // Connection retry count
    "retry_delay": 2          // Seconds between retries
  }
}
```

### LED Configuration
```json
{
  "led": {
    "brightness": 50,         // LED brightness (0-100%)
    "fade_duration": 1.0      // Fade effect duration in seconds
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

### Service Management (Recommended)
```bash
# Service management script (no venv activation needed)
./service_manager.sh install    # Install systemd service (one-time setup)
./service_manager.sh start      # Start presence detection service
./service_manager.sh stop       # Stop the service
./service_manager.sh restart    # Restart the service
./service_manager.sh status     # Check service status
./service_manager.sh logs       # View live service logs
./service_manager.sh kill       # Emergency stop and disable
./service_manager.sh uninstall  # Remove service completely
```

### Manual TV Control Commands
```bash
# Always activate virtual environment first
source venv/bin/activate

# Direct TV control
python3 power_on.py                         # Turn TV on
python3 power_off.py                        # Turn TV off

# Discovery and configuration
python3 discover_samsung_tv.py              # Find and configure Samsung TVs
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

### LED Testing Commands
```bash
# Test LED functionality
python3 test_led_dimming.py                      # Test LED brightness and fade effects
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
1. **Presence Detected** → LED fades in + Immediate TV power on (WebSocket/Wake-on-LAN)
2. **TV ON State** → Monitor continued presence, LED stays on
3. **No Presence** → LED fades out + Start 60-second countdown timer
4. **Timer Expires** → TV power off to standby mode
5. **Presence Returns** → Cancel timer, LED fades in, ensure TV remains on
6. **Sensor Auto-Reset** → Periodic reset every 60s to prevent firmware glitches

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
# Core Components
presence_sensor.py          # Main application with Samsung network integration and LED control
uart_sensor.py              # UART sensor interface for DFRobot SENS0395
enhanced_samsung_controller.py  # Enhanced Samsung TV network control module
discover_samsung_tv.py      # TV discovery and auto-configuration
config.json                 # System configuration (sensor, TV, LED, timing)

# Service Management
service_manager.sh          # Systemd service management script
                           # (install, start, stop, restart, status, logs, kill)

# Control Scripts
power_on.py                 # Manual TV power on script
power_off.py                # Manual TV power off script

# Development Tools
debug_sensor_strings.py     # UART sensor debugging utility
configure_sensor.py         # Sensor range configuration tool
check_sensor_config.py      # Sensor settings verification
test_led_dimming.py         # LED brightness and fade effect testing

# Environment
venv/                       # Python virtual environment with dependencies
archive_failed_attempts/    # Failed control methods (reference only)
```

## Installation as Service (Production)

### Recommended: Automated Service Setup
```bash
# Use the service manager script (easiest method)
./service_manager.sh install    # Install and enable the service
./service_manager.sh start      # Start the service
./service_manager.sh status     # Verify it's running

# Monitor the service
./service_manager.sh logs       # View live logs
```

### Service Management
```bash
# Daily operations
./service_manager.sh status     # Check if running
./service_manager.sh restart    # Restart after config changes
./service_manager.sh stop       # Temporarily stop
./service_manager.sh start      # Start again

# Troubleshooting
./service_manager.sh logs       # See what's happening
./service_manager.sh kill       # Emergency stop
./service_manager.sh uninstall  # Remove completely
```

### Manual Service Setup (Advanced)
If you prefer manual systemd commands:
```bash
# The service manager script creates this service file:
# /etc/systemd/system/presence-sensor.service

# Manual systemd commands
sudo systemctl status presence-sensor    # Check status
sudo systemctl restart presence-sensor   # Restart
journalctl -u presence-sensor -f         # View logs
```

## Troubleshooting

### Service Issues
```bash
# Check service status
./service_manager.sh status

# View detailed logs
./service_manager.sh logs

# Restart if having issues
./service_manager.sh restart

# Emergency stop
./service_manager.sh kill
```

### TV Control Issues
```bash
# Test TV connectivity manually
source venv/bin/activate
python3 power_on.py     # Test TV power on
python3 power_off.py    # Test TV power off

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
- **LED Visual Feedback**: PWM-controlled LED with brightness and fade effects
- **Periodic Sensor Reset**: Automatic 60s reset to prevent firmware glitches
- **Sensor Framework**: Both UART and GPIO trigger modes implemented
- **Configuration System**: Complete JSON-based configuration with LED settings
- **Development Tools**: Debug utilities, dry-run modes, verbose logging, LED testing
- **Hardware Integration**: Raspberry Pi CM5 + DFRobot SENS0395 + LED indicator working

⚠️ **Problematic (Documented):**
- **Samsung TV Control**: Intermittent WebSocket API failures
- **Smart Plug Control**: All attempted methods failed (see `archive_failed_attempts/`)

🔄 **Next Phase Options:**
- Investigate reliable hardware control methods (relay switching)
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