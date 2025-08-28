# Project Status: Presence Detection System

## Current Phase: Not Started
**Last Updated:** 2025-08-28

---

## Phase 1: IR Code Learning and Testing
**Status:** 🔴 Not Started  
**Objective:** Learn Samsung TV IR codes and verify control

### LIRC Setup Instructions:

**IMPORTANT: Use LIRC for Adafruit IR hardware**

1. [ ] **Install LIRC System**
   ```bash
   sudo ./setup_ir_lirc.sh
   sudo reboot  # Required for GPIO overlay changes
   ```

2. [ ] **Test IR Receiver**
   ```bash
   sudo python3 ir_control_lirc.py test
   ```
   - Should show pulse data when pressing remote buttons
   - Press Ctrl+C to stop

3. [ ] **Learn Samsung Remote Codes**
   ```bash
   sudo python3 ir_control_lirc.py learn --remote samsung
   ```
   - Follow prompts to press buttons randomly for noise sampling
   - Then record specific buttons (suggest: KEY_POWER)
   - This creates samsung.lircd.conf with learned codes

4. [ ] **Test Sending Commands**
   ```bash
   python3 ir_control_lirc.py send --remote samsung --key KEY_POWER
   ```

5. [ ] **Verify Setup**
   ```bash
   python3 ir_control_lirc.py list  # Show available remotes
   ```

### Additional Commands:
- `python3 ir_control_lirc.py send --remote samsung --key KEY_POWER --count 3` (send 3 times)
- `sudo mode2 -d /dev/lirc0` (raw test mode)
- `irrecord` and `irsend` work directly after setup

### Hardware Connections:
- IR Receiver: GPIO 23 (Physical Pin 16)
- IR Transmitter: GPIO 24 (Physical Pin 18)
- Both: Connect VCC to 3.3V, GND to GND

**Success Criteria:** TV reliably turns on/off via IR commands

---

## Phase 2: Basic Presence Sensor Integration
**Status:** 🔴 Not Started  
**Objective:** Integrate DFRobot SENS0395 sensor with basic detection

### Steps:
1. [ ] **Sensor Hardware Setup**
   - Connect sensor to GPIO 14
   - Verify 5V power supply
   - Test physical mounting position

2. [ ] **Basic Sensor Reading**
   - Create `lib/sensor.py` module
   - Implement GPIO trigger mode reading
   - Add basic debouncing (1-2 seconds)
   - Log presence detection events

3. [ ] **Simple Control Loop**
   - Create main `presence_sensor.py`
   - Implement: Presence → TV ON
   - Implement: No Presence (10 min) → TV OFF
   - Add verbose logging for debugging

4. [ ] **Initial Testing**
   - Test detection accuracy
   - Verify timing logic
   - Run for 1 hour continuous test

**Success Criteria:** Sensor reliably detects presence and triggers actions

---

## Phase 3: Full System Integration
**Status:** 🔴 Not Started  
**Objective:** Complete system with CEC, state management, and service

### Steps:
1. [ ] **CEC Integration**
   - Install python-cec or cec-utils
   - Implement CEC power ON command
   - Create `lib/tv_control.py` module
   - Test hybrid control (CEC on, IR off)

2. [ ] **State Machine Implementation**
   - Create `lib/state_machine.py`
   - Track TV state (ON/OFF/UNKNOWN)
   - Handle edge cases and recovery
   - Add state persistence

3. [ ] **Configuration System**
   - Create `config.json` template
   - Add configurable timeouts
   - Add device-specific settings
   - Implement config validation

4. [ ] **Service Setup**
   - Create systemd service file
   - Implement proper signal handling
   - Add auto-restart on failure
   - Setup logging rotation

**Success Criteria:** System runs reliably as a service for 24+ hours

---

## Phase 4: Production Deployment
**Status:** 🔴 Not Started  
**Objective:** Deploy and optimize for long-term operation

### Steps:
1. [ ] **Installation Script**
   - Create `scripts/install.sh`
   - Automate dependency installation
   - Configure permissions
   - Setup service auto-start

2. [ ] **Monitoring & Logging**
   - Implement health checks
   - Add performance metrics
   - Setup alert thresholds
   - Create log analysis tools

3. [ ] **Optimization**
   - Minimize CPU usage (< 5%)
   - Optimize response time (< 2s)
   - Reduce false positives/negatives
   - Implement adaptive timing

4. [ ] **Documentation**
   - Complete README.md
   - Add troubleshooting guide
   - Document all configurations
   - Create user manual

**Success Criteria:** System runs unattended for 1+ week without issues

---

## Phase 5: Advanced Features (Future)
**Status:** 🔴 Planning  
**Objective:** Enhanced capabilities and integrations

### Potential Features:
- [ ] UART mode for advanced sensor configuration
- [ ] Multiple zone detection
- [ ] Home Assistant integration
- [ ] Mobile app control
- [ ] Schedule-based overrides
- [ ] Multi-device control
- [ ] Power consumption tracking
- [ ] Ambient light consideration

---

## Known Issues
### LIRC Installation Issues - RESOLVED (2025-08-28)
- **Problem:** LIRC installation left IR module's yellow transmit light permanently on
- **Root Cause:** GPIO IR transmitter overlay (`dtoverlay=gpio-ir-tx,gpio_pin=24`) held GPIO 24 in active state
- **Resolution Applied:**
  1. ✅ Stopped and disabled lircd service and socket
  2. ✅ Removed LIRC packages (`sudo apt-get remove --purge -y lirc`)
  3. ✅ Removed GPIO IR overlays from `/boot/firmware/config.txt`:
     - Removed `# IR blaster on GPIO 24 (for presence detection TV control)`
     - Removed `dtoverlay=gpio-ir-tx,gpio_pin=24`
  4. ✅ Cleaned up auto-installed dependencies
  5. ⚠️  **REBOOT REQUIRED** to clear kernel device tree overlays and release GPIO 24
- **Status:** Changes reverted, system ready for reboot to complete cleanup

## Dependencies Checklist
- [ ] Python 3.x
- [ ] RPi.GPIO
- [ ] LIRC (for IR control)
- [ ] python-cec or cec-utils
- [ ] systemd (for service)

## Hardware Checklist
- [ ] Raspberry Pi (any model with GPIO)
- [ ] DFRobot SENS0395 mmWave sensor
- [ ] Adafruit ADA5990 IR blaster
- [ ] Samsung Frame 43" TV
- [ ] Jumper wires and breadboard
- [ ] 5V power supply for sensor

---

## Notes
- Starting with IR control ensures we can reliably control the TV before adding complexity
- Testing each component independently reduces debugging complexity
- The 10-minute timeout can be adjusted based on usage patterns
- Consider seasonal adjustments (winter vs summer behavior)