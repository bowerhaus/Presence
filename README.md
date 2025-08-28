# Presence Detection System

A Raspberry Pi-based human presence detection system that automatically controls a Samsung Frame 43" TV based on room occupancy.

## Features

- Detects human presence using DFRobot SENS0395 mmWave sensor
- Automatically turns TV on when presence is detected
- Turns TV off after 10 minutes of no presence
- Hybrid control using CEC (for power on) and IR blaster (for power off)
- Configurable GPIO pins and timing parameters via config.json
- Development mode with dry-run option for testing

## Hardware Requirements

- Raspberry Pi (tested on Pi 4/5)
- DFRobot SENS0395 mmWave sensor (configurable GPIO, default: 14)
- Adafruit ADA5990 IR blaster (configurable GPIO, default: 24)
- Samsung Frame TV (or other CEC/IR compatible TV)
- HDMI cable (for CEC communication)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/presence-detection
cd presence-detection

# Install dependencies
pip3 install -r requirements.txt

# Configure the system
cp config.json config.json.backup  # Backup existing config
# Edit config.json with your GPIO pins and settings

# Install as systemd service (optional)
sudo ./scripts/install.sh
```

## Configuration

The system is configured via `config.json`. All GPIO pins and timing parameters are customizable.

### GPIO Pin Configuration
```json
{
  "sensor": {
    "gpio_pin": 14,        // GPIO pin for presence sensor (configurable)
    "debounce_time": 2.0   // Seconds to debounce sensor readings
  },
  "ir": {
    "gpio_pin": 24         // GPIO pin for IR blaster (configurable)
  }
}
```

### Timing Configuration
```json
{
  "tv_control": {
    "turn_off_delay": 600,  // Seconds to wait before turning off TV (default: 10 minutes)
    "turn_on_delay": 0      // Seconds to wait before turning on TV (default: immediate)
  }
}
```

### Development Mode
```json
{
  "dev_mode": {
    "enabled": false,       // Enable development mode
    "dry_run": false,       // Simulate TV control without actual commands
    "verbose": false        // Enable verbose logging
  }
}
```

## Usage

### Development Mode
```bash
# Run with verbose output
python3 presence_sensor.py --dev --verbose

# Run in dry-run mode (no actual TV control)
python3 presence_sensor.py --dev --dry-run

# View logs
tail -f /var/log/presence-sensor.log
```

### Production Mode
```bash
# Start the service
sudo systemctl start presence-sensor

# Enable auto-start on boot
sudo systemctl enable presence-sensor

# Check status
sudo systemctl status presence-sensor

# View logs
journalctl -u presence-sensor -f
```

## Architecture

The system uses a state machine with the following states:
- **TV OFF**: Waiting for presence detection
- **Presence Detected**: Immediate TV power on via CEC
- **TV ON**: Monitoring for continued presence
- **No Presence Timer**: 10-minute countdown after last presence
- **TV OFF Command**: Power off via IR blaster

## Project Structure

```
presence_sensor.py       # Main application
config.json             # Configuration file (GPIO pins, timing, etc.)
ir_codes.json          # Learned IR codes
lib/
  sensor.py            # Sensor abstraction
  tv_control.py        # CEC/IR control logic
  state_machine.py     # State management
tests/
  test_sensor.py       # Unit tests
  test_tv_control.py
scripts/
  install.sh           # Installation script
  learn_ir.py          # IR code learning utility
```

## Troubleshooting

### Sensor not detecting presence
- Check GPIO pin connection (verify pin number in config.json)
- Verify sensor power supply (5V)
- Adjust debounce time in config.json

### TV not responding to commands
- Verify CEC is enabled on TV
- Check HDMI cable supports CEC
- Test IR blaster positioning and codes
- Run in dry-run mode to verify logic

### Service not starting
- Check logs: `journalctl -u presence-sensor -n 50`
- Verify config.json is valid JSON
- Ensure GPIO permissions: user must be in `gpio` group

## Complete Configuration Example

See `config.json` for the complete configuration structure with all available options including:
- Sensor GPIO pin and debounce settings
- TV control timing parameters
- CEC configuration and retry logic
- IR blaster GPIO pin and protocol settings
- Logging levels and file paths
- Development mode options

## License

MIT License - see LICENSE file for details

## Contributing

Pull requests welcome! Please ensure:
- Code follows Python PEP 8 style guide
- Unit tests pass
- Configuration changes are documented
- Hardware connections are clearly described