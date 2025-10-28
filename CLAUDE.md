# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi CM5-based human presence detection system that was intended to control a Samsung Frame 43" TV. **The presence detection system is fully functional with LED visual feedback, but TV control remains problematic due to API limitations.**

## Current Project Status (2025-10-28)

**Note**: Currently on `Presence-LED` feature branch, which adds LED visual feedback system.

⚠️ **CRITICAL: Multiple TV control methods have failed**

### Working Components ✅
- **Presence Detection**: DFRobot SENS0395 mmWave sensor via UART (`/dev/ttyAMA1`)
- **LED Visual Feedback**: PWM-controlled LED on GPIO 12 with fade effects (0-100% brightness)
- **Periodic Sensor Reset**: Automatic sensor reset every 60s to prevent firmware glitches from ground loop interference
- **Sensor Framework**: Complete UART and GPIO trigger mode support
- **Configuration System**: JSON-based config with development modes (includes LED settings)
- **Development Tools**: Debug scripts, dry-run testing, verbose logging, LED testing

### Failed Components ❌ (Archived in `archive_failed_attempts/`)
- **Samsung TV Network Control**: Intermittent WebSocket API failures
- **Direct Tapo Control**: PyP100 authentication failures
- **Alexa API Control**: AlexaPy blocked by Amazon security measures
- **Kasa Protocol**: Device incompatibility

## Key Architecture Decisions

### Hardware Control Strategy (Updated)
- **Sensor**: DFRobot SENS0395 on UART `/dev/ttyAMA1` (working perfectly)
- **TV Control**: **UNRELIABLE** - Samsung network API has intermittent failures
- **Platform**: Raspberry Pi CM5 with lgpio library

### Timing Logic (Implemented)
- **Turn ON**: Immediate with 1-2 second debouncing, LED fades in
- **Turn OFF**: 60-second delay after last presence detected, LED fades out
- **Sensor Reset**: Automatic reset every 60 seconds (preventive maintenance)
- **State Machine**: Presence Detected → LED fade in + TV Control Attempt → 60s timeout → LED fade out + TV Control Attempt

## Development Commands

```bash
# Activate virtual environment (always required)
source venv/bin/activate

# Test presence detection (WORKING)
python3 presence_sensor.py --dev --dry-run --verbose
python3 debug_sensor_strings.py --port /dev/ttyAMA1 --duration 30

# Test TV control (UNRELIABLE)
python3 discover_samsung_tv.py                    # TV discovery
python3 samsung_tv_control.py status              # Check TV state (may fail)
python3 power_on.py                                # Turn TV on (may fail)
python3 power_off.py                               # Turn TV off (may fail)

# Configure sensor settings
python3 configure_sensor.py                       # Set detection range
python3 check_sensor_config.py                    # Verify sensor settings

# Test LED functionality
python3 test_led_dimming.py                       # Test LED brightness and fade effects

# Service management (not recommended until TV control is reliable)
sudo systemctl status presence-sensor             # Check service status
journalctl -u presence-sensor -f                  # View logs if service exists
```

## Project Structure (Current)

```
# Core working components
presence_sensor.py           # Main application (presence detection + LED control working, TV control unreliable)
uart_sensor.py              # UART sensor interface (WORKING)
samsung_tv_control.py        # Samsung TV control (UNRELIABLE)
discover_samsung_tv.py       # TV discovery utility
config.json                  # System configuration (sensor, TV, LED, timing)

# Control scripts
power_on.py                  # Manual TV power on script
power_off.py                 # Manual TV power off script

# Debug and development tools
debug_sensor_strings.py      # UART sensor debugging (WORKING)
configure_sensor.py          # Sensor range configuration
check_sensor_config.py       # Sensor settings verification
test_led_dimming.py          # LED brightness and fade effect testing

# Environment and dependencies
venv/                        # Python virtual environment (clean)
status.md                    # Detailed project status and failed attempts
README.md                    # User documentation with current status

# Failed implementations (DO NOT REIMPLEMENT)
archive_failed_attempts/     # All failed control methods
├── alexa_tv_control.py     # Failed AlexaPy integration
├── tapo_tv_control.py      # Failed direct Tapo control
├── discover_tapo.py        # Failed Tapo discovery
└── test_*.py               # Failed test scripts
```

## Configuration

The system uses a JSON configuration file (`config.json`) with the following structure:
- `sensor`: UART settings (UART mode working on `/dev/ttyAMA1`), range config, reset interval
- `tv_control`: Timing parameters and control type (60s turn-off delay)
- `samsung_tv`: Network TV control settings (UNRELIABLE)
- `led`: LED brightness and fade duration settings
- `logging`: Log levels and file paths
- `dev_mode`: Development mode settings

**Key Configuration Values:**
- `sensor.range_meters.max`: 3.5m (maximum detection range)
- `sensor.reset_interval_seconds`: 60 (automatic sensor reset interval)
- `tv_control.turn_off_delay`: 60 (seconds before TV turns off)
- `led.brightness`: 50 (LED brightness 0-100%)
- `led.fade_duration`: 1.0 (fade effect duration in seconds)

**Removed sections:** `ir_control`, `cec`, and `sensor.trigger` (GPIO pin config) are no longer needed.

## Important Implementation Notes

1. **Platform**: Raspberry Pi CM5 with lgpio library (not RPi.GPIO)
2. **Sensor Communication**: UART via `/dev/ttyAMA1` at 115200 baud (WORKING)
3. **LED Control**: GPIO pin 12 with PWM for brightness control (0-100%)
4. **Periodic Sensor Reset**: Automatic reset every 60s to prevent firmware glitches from ground loop interference
5. **TV Control**: samsungtvws library for Samsung TV WebSocket API (UNRELIABLE)
6. **Virtual Environment**: Clean dependency management (failed libraries removed)
7. **Power State Detection**: Samsung PowerState API when working
8. **Development Mode**: Comprehensive dry-run and debug capabilities

## Critical Notes for Future Development

⚠️ **DO NOT REIMPLEMENT FAILED METHODS**
- All code in `archive_failed_attempts/` has been proven to fail
- Direct smart plug control via PyP100, AlexaPy, Kasa all failed
- Samsung WebSocket API is unreliable for automation use
- IR and CEC control methods have been removed from codebase

✅ **RELIABLE COMPONENTS TO BUILD ON**
- UART sensor communication is rock-solid
- LED visual feedback system working perfectly
- Periodic sensor reset mechanism prevents firmware glitches
- Configuration framework is robust
- Development and debugging tools are comprehensive

## Testing Approach (Current)

✅ **Working Tests:**
- UART sensor communication testing with `debug_sensor_strings.py`
- LED brightness and fade testing with `test_led_dimming.py`
- Presence detection simulation with dry-run mode
- Configuration validation and sensor setup verification
- Periodic sensor reset verification

⚠️ **Problematic Tests:**
- Samsung TV control tests may fail intermittently
- End-to-end automation tests unreliable due to TV control issues

## Samsung TV Network Control (PROBLEMATIC ⚠️)

The Samsung network API implementation has significant issues:

### What Works Sometimes:
- **Network Discovery**: Can detect Samsung TVs on local network
- **Basic Commands**: Simple on/off commands work occasionally
- **Power State Detection**: PowerState API works when TV is responsive

### Critical Issues Discovered:
- ❌ **Intermittent WebSocket failures**: Connection timeouts and stale connections
- ❌ **Connection reuse problems**: API becomes unresponsive after multiple calls
- ❌ **Unreliable automation**: Fails when used from presence detection system
- ⚠️ **Manual control works**: TV responds to direct manual commands

### Root Cause Analysis:
The Samsung TV WebSocket API was designed for occasional manual control, not automated systems making frequent state checks and control commands.

## Next Development Options

### Option 1: Hardware Control (Recommended)
- **Relay Module**: Hardware power switching via smart plug relay
- **GPIO Control**: Direct GPIO relay control for 100% reliability

### Option 2: Cloud Integration
- **IFTTT Webhooks**: HTTP-based cloud automation
- **Home Assistant**: Dedicated home automation platform
- **OpenHAB**: Open-source home automation

### Option 3: Presence-Only System
- **MQTT Publishing**: Send presence data to other systems
- **Web API**: HTTP endpoint for presence status
- **Data Logging**: Focus on presence analytics rather than control

## Development Notes
- **status.md** contains detailed failure analysis and timeline
- **README.md** reflects current working/non-working status
- All failed attempts archived to prevent re-implementation
- Focus on reliable presence detection capabilities that work consistently