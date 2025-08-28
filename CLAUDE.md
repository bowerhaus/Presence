# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi-based human presence detection system that controls a Samsung Frame 43" TV. The system uses a DFRobot SENS0395 mmWave sensor (GPIO 14) to detect human presence and controls the TV via CEC (for power on) and IR blaster (for power off) to ensure reliable state management.

## Key Architecture Decisions

### Hardware Control Strategy
- **Sensor**: DFRobot SENS0395 on GPIO 14 (trigger mode initially, UART mode planned)
- **TV Control**: Hybrid approach using CEC for ON commands (reliable) and IR for OFF commands (avoids CEC state issues)
- **IR Blaster**: Adafruit ADA5990 (GPIO pin TBD)

### Timing Logic
- **Turn ON**: Immediate with 1-2 second debouncing
- **Turn OFF**: 10-minute delay after last presence detected
- **State Machine**: TV OFF → Presence Detected → TV ON → 10 min timeout → TV OFF

## Development Commands

```bash
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

## Project Structure (Planned)

```
presence_sensor.py       # Main application
config.json             # Configuration file
ir_codes.json          # Learned IR codes
lib/
  sensor.py            # Sensor abstraction
  tv_control.py        # CEC/IR control logic
  state_machine.py     # State management
tests/
  test_sensor.py
  test_tv_control.py
scripts/
  install.sh           # Installation script
  learn_ir.py          # IR code learning utility
```

## Configuration

The system uses a JSON configuration file (`config.json`) with the following structure:
- `sensor`: GPIO pin and debounce settings
- `tv_control`: Timing parameters
- `cec`: CEC control settings
- `ir`: IR blaster configuration and codes
- `logging`: Log levels and file paths
- `dev_mode`: Development mode settings

## Important Implementation Notes

1. **Python 3.x** is the chosen language
2. **RPi.GPIO** for sensor reading
3. **python-cec** or **cec-utils** for CEC control
4. **LIRC** or custom IR library for IR transmission
5. **systemd** for service management

## Testing Approach

- Mock hardware interfaces for unit testing
- Integration tests with actual hardware
- Long-term stability testing (24+ hours)
- Performance benchmarks (< 2s response, < 5% CPU)

## Future Enhancements

- **Phase 2**: UART sensor mode for advanced configuration
- **Phase 3**: Home automation integration
- **Phase 4**: Multi-device control
- Keep track of the current project status in status.md and use this as a way of tracking step by step progress in long term memory