# Human Presence Sensor System - Product Requirements Document

## 1. Executive Summary

### 1.1 Project Overview
A Raspberry Pi-based human presence detection system that automatically controls a Samsung Frame 43" TV, turning it on when humans are detected in the room and off when the room is vacant.

### 1.2 Key Goals
- Automatic TV power management based on human presence
- Energy efficiency through intelligent control
- Reliable state management using hybrid CEC/IR control
- Extensible architecture for future enhancements

## 2. System Components

### 2.1 Hardware Requirements
| Component | Model | Purpose | Connection |
|-----------|-------|---------|------------|
| Single Board Computer | Raspberry Pi (Model TBD) | Main controller | - |
| Presence Sensor | DFRobot SENS0395 | 9m mmWave human detection | GPIO 14 (trigger mode) |
| IR Blaster | Adafruit ADA5990 | IR remote control | GPIO (TBD) |
| Target Display | Samsung Frame 43" TV | Controlled device | HDMI (CEC) + IR |

### 2.2 Software Stack
- **Operating System**: Raspberry Pi OS (Latest stable)
- **Programming Language**: Python 3.x
- **Key Libraries**:
  - RPi.GPIO - GPIO control
  - python-cec or cec-utils - CEC control
  - LIRC or custom IR library - IR transmission
  - systemd - Service management
  - logging - System logging

## 3. Functional Requirements

### 3.1 Core Features

#### 3.1.1 Presence Detection
- **Sensor Mode**: GPIO trigger mode (initial implementation)
- **GPIO Pin**: 14
- **Detection Range**: Up to 9 meters
- **Response**: Binary presence/no-presence signal
- **Debouncing**: Required to prevent false triggers

#### 3.1.2 TV Power Control

##### State Management Strategy
Due to potential CEC state reporting limitations:
- **Turn ON**: Use CEC command (reliable)
- **Turn OFF**: Use IR command (reliable)
- **Rationale**: Ensures predictable state without relying on CEC state queries

##### Timing Parameters
- **Turn ON Delay**: Immediate (with debouncing, ~1-2 seconds)
- **Turn OFF Delay**: 10 minutes after last presence detected
- **Debounce Period**: 1-2 seconds for presence detection

#### 3.1.3 System Modes

##### Production Mode
- Runs as systemd service on boot
- Automatic operation
- Standard logging to systemd journal
- Minimal console output

##### Development Mode
- Manual start/stop capability
- Verbose logging to console and file
- Manual TV control commands available
- Sensor state visualization
- Dry-run option (log actions without executing)

### 3.2 Control Logic

```
STATE MACHINE:
┌─────────────┐
│   STARTUP   │
└──────┬──────┘
       │ Initialize
       ▼
┌─────────────┐     Presence      ┌─────────────┐
│   TV OFF    │◄──────────────────│   TV ON     │
│   WAITING   │                   │   ACTIVE    │
└──────┬──────┘                   └──────▲──────┘
       │                                  │
       └────────Presence Detected────────┘
                                          │
                                   10 min timeout
                                   (no presence)
```

### 3.3 IR Control Requirements

#### IR Code Discovery
- System must support IR code learning/recording
- Store learned codes in configuration file
- Support for Samsung Frame specific codes:
  - Power Off (required)
  - Power Toggle (fallback)
  - Other codes as discovered

#### IR Blaster Configuration
- Support Adafruit ADA5990 pinout
- Configurable IR LED GPIO pins
- Adjustable transmission parameters (carrier frequency, timing)

### 3.4 CEC Control Requirements

- Use HDMI CEC for TV power-on command
- Device identification and addressing
- Fallback handling if CEC unavailable
- Command retry logic with configurable attempts

## 4. Non-Functional Requirements

### 4.1 Performance
- Presence detection response: < 2 seconds
- TV control command execution: < 1 second
- System startup time: < 30 seconds
- CPU usage: < 5% average
- Memory usage: < 100MB

### 4.2 Reliability
- Automatic recovery from crashes (systemd restart)
- Graceful handling of hardware failures
- Persistent state across reboots (last known TV state)
- Watchdog timer implementation

### 4.3 Logging
- Structured logging with levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation to prevent disk fill
- Remote syslog support (optional)
- Event categories:
  - Presence state changes
  - TV control commands sent
  - Errors and exceptions
  - System startup/shutdown

### 4.4 Security
- No network services in base implementation
- Local configuration file with appropriate permissions
- No sensitive data storage

## 5. Configuration

### 5.1 Configuration File Structure (config.json)
```json
{
  "sensor": {
    "gpio_pin": 14,
    "debounce_ms": 1000
  },
  "tv_control": {
    "off_timeout_minutes": 10,
    "on_delay_ms": 1000
  },
  "cec": {
    "enabled": true,
    "device_address": "0.0.0.0",
    "retry_attempts": 3
  },
  "ir": {
    "enabled": true,
    "gpio_pin": null,
    "codes": {
      "power_off": "learned_code_here",
      "power_toggle": "fallback_code"
    }
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/presence-sensor.log",
    "max_size_mb": 100
  },
  "dev_mode": {
    "enabled": false,
    "verbose": true,
    "dry_run": false
  }
}
```

## 6. Development & Testing

### 6.1 Development Environment Setup
1. Install Raspberry Pi OS
2. Enable required interfaces (GPIO, CEC)
3. Install Python dependencies
4. Configure IR blaster hardware
5. Learn IR codes from TV remote

### 6.2 Testing Requirements
- Unit tests for core logic
- Integration tests for hardware interfaces
- Mock modes for sensor and TV control
- Performance benchmarking
- Long-term stability testing (24+ hours)

### 6.3 Development Tools
- CLI interface for:
  - Manual TV control
  - Sensor state monitoring
  - Configuration validation
  - IR code learning
  - System diagnostics

## 7. Deployment

### 7.1 Installation Process
1. Clone repository
2. Run installation script (install.sh)
3. Configure using setup wizard or manual config
4. Test in dev mode
5. Enable systemd service

### 7.2 Service Management
```bash
# Service commands
sudo systemctl start presence-sensor
sudo systemctl stop presence-sensor
sudo systemctl enable presence-sensor
sudo systemctl status presence-sensor

# Dev mode
python3 presence_sensor.py --dev --verbose
```

## 8. Future Enhancements

### 8.1 Phase 2: UART Sensor Mode
- Advanced sensor configuration via UART
- Sensitivity adjustment
- Zone-based detection
- Movement tracking
- Presence count estimation

### 8.2 Phase 3: Smart Features
- Time-based profiles (different behavior day/night)
- Integration with home automation (Home Assistant, etc.)
- Web interface for configuration and monitoring
- Mobile app for manual override
- Multi-sensor support
- Machine learning for pattern recognition

### 8.3 Phase 4: Advanced Control
- Control multiple devices
- Scene management (lights, audio, etc.)
- Vacation mode (security presence simulation)
- Energy usage tracking and reporting

## 9. Error Handling & Recovery

### 9.1 Failure Scenarios
| Scenario | Detection | Recovery Action |
|----------|-----------|-----------------|
| Sensor disconnection | GPIO read timeout | Log error, retry, alert if persistent |
| CEC command failure | No ACK received | Retry 3x, fall back to IR |
| IR transmission failure | No state change detected | Log error, retry once |
| System crash | Systemd monitoring | Automatic restart with backoff |
| Configuration error | Validation failure | Use defaults, log warning |

### 9.2 Monitoring & Alerts
- Health check endpoint (future)
- Heartbeat logging
- Error rate monitoring
- System resource alerts

## 10. Success Metrics

- **Reliability**: 99% uptime
- **Accuracy**: < 1% false positive/negative rate
- **Response Time**: < 2 seconds for presence detection
- **Energy Savings**: Measurable reduction in TV runtime
- **User Satisfaction**: Seamless, unnoticed operation

## 11. Project Timeline

### Phase 1: MVP (Current)
- Basic presence detection (GPIO trigger mode)
- CEC + IR control implementation
- Dev mode with logging
- Systemd service setup

### Phase 2: Enhancement (Future)
- UART sensor mode
- Web interface
- Advanced configuration

### Phase 3: Integration (Future)
- Home automation integration
- Multi-device support
- Advanced analytics

## 12. Appendices

### A. Samsung Frame TV Specifications
- Model: Frame 43"
- CEC Support: Yes (limited state reporting)
- IR Requirements: Standard Samsung protocol
- Power Consumption: TBD

### B. Reference Documentation
- [DFRobot SENS0395 Datasheet](https://www.dfrobot.com/)
- [Adafruit ADA5990 Documentation](https://www.adafruit.com/)
- [HDMI CEC Specification](https://www.hdmi.org/)
- [Samsung IR Codes Database](TBD)

### C. Glossary
- **CEC**: Consumer Electronics Control - HDMI control protocol
- **IR**: Infrared - Remote control technology
- **GPIO**: General Purpose Input/Output
- **mmWave**: Millimeter wave radar technology
- **Debouncing**: Filtering rapid signal changes to prevent false triggers

---
*Document Version: 1.0*  
*Last Updated: 2025-08-28*  
*Status: Initial Draft*