# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi-based human presence detection system that controls a Samsung Frame 43" TV. The system uses a DFRobot SENS0395 mmWave sensor (GPIO 14) to detect human presence and controls the TV via Samsung's network API for reliable power management.

## Key Architecture Decisions

### Hardware Control Strategy
- **Sensor**: DFRobot SENS0395 on GPIO 14 (trigger mode initially, UART mode planned)
- **TV Control**: Samsung network API via WiFi/Ethernet (replaces CEC/IR for reliability)
- **Network Library**: samsungtvws Python library with WebSocket control

### Timing Logic
- **Turn ON**: Immediate with 1-2 second debouncing
- **Turn OFF**: 10-minute delay after last presence detected
- **State Machine**: TV OFF → Presence Detected → TV ON → 10 min timeout → TV OFF

## Development Commands

```bash
# Activate virtual environment (required for Samsung TV control)
source venv/bin/activate

# Discover Samsung TV on network and configure
python3 discover_samsung_tv.py

# Test Samsung TV network control
python3 samsung_tv_control.py

# Run in development mode
python3 presence_sensor.py --dev --verbose

# Run with dry-run (no actual TV control)
python3 presence_sensor.py --dev --dry-run

# Service management (production)
sudo systemctl start presence-sensor
sudo systemctl stop presence-sensor
sudo systemctl enable presence-sensor
sudo systemctl status presence-sensor

# View logs
journalctl -u presence-sensor -f  # Production logs
tail -f /var/log/presence-sensor.log  # Development logs
```

## Project Structure (Current)

```
presence_sensor.py       # Main application with Samsung network control
samsung_tv_control.py    # Samsung network TV control module
discover_samsung_tv.py   # TV discovery and auto-configuration utility
config.json             # Configuration file with Samsung network settings
venv/                   # Python virtual environment with dependencies
lib/                    # Future modular components (planned)
  sensor.py            # Sensor abstraction (planned)
  state_machine.py     # State management (planned)
tests/                  # Test suite (planned)
  test_sensor.py       # Tests (planned)
  test_tv_control.py   # Tests (planned)
scripts/                # Installation and setup scripts (planned)
  install.sh           # Installation script (planned)
```

## Configuration

The system uses a JSON configuration file (`config.json`) with the following structure:
- `sensor`: GPIO pin and debounce settings
- `tv_control`: Timing parameters
- `samsung_tv`: Network TV control settings (IP, port, token, Wake-on-LAN)
- `cec`: CEC control settings (backup only)
- `logging`: Log levels and file paths
- `dev_mode`: Development mode settings

## Important Implementation Notes

1. **Python 3.x** is the chosen language
2. **RPi.GPIO** for sensor reading
3. **samsungtvws[async,encrypted]** library for Samsung TV network control via WebSocket API
4. **Virtual environment** for clean dependency management  
5. **Samsung PowerState API** for accurate TV power state detection (`on`/`standby`)
6. **Wake-on-LAN** for powering on fully-off TVs (requires MAC address)
7. **systemd** for service management (production deployment)

## Testing Approach

- Mock hardware interfaces for unit testing
- Integration tests with actual hardware
- Long-term stability testing (24+ hours)
- Performance benchmarks (< 2s response, < 5% CPU)

## Samsung TV Network Control (Implementation Complete ✅)

The system now uses Samsung's network API instead of IR/CEC for reliable TV control:

### Key Features Implemented:
- **Network Discovery**: Auto-detect Samsung TVs on local network
- **Power State Detection**: Accurate detection using Samsung PowerState API
- **Smart Control Strategy**: State-aware power control (WebSocket + Wake-on-LAN)
- **No Hardware Dependencies**: Eliminated need for IR blaster hardware

### Samsung TV API Limitations Discovered:
- ❌ `KEY_POWERON`/`KEY_POWEROFF` commands not supported
- ✅ `KEY_POWER` (toggle) commands work reliably
- ✅ PowerState API reports `on`, `standby`, or unreachable
- ✅ WebSocket control works: `on` ↔ `standby`

### Control Strategy Implemented:
**Power ON:** Check current state → Use appropriate method (WebSocket toggle for standby, Wake-on-LAN for fully off)  
**Power OFF:** WebSocket toggle to standby mode (Samsung TVs remain network-reachable)

## Future Enhancements

- **Phase 2**: Complete mmWave sensor integration and testing
- **Phase 3**: Production service deployment and monitoring
- **Phase 4**: Advanced features (multi-zone detection, scheduling, home automation)
- **Long-term**: UART sensor mode, mobile app control, multi-device support

## Development Notes
- Keep track of the current project status in status.md and use this as a way of tracking step by step progress in long term memory
- keep readme.md up to date with any documentation changes
- Samsung network control approach provides superior reliability over IR/CEC methods