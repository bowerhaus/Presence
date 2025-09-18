# Project Status: Presence Detection System

## 🚨 CRITICAL: All TV Control Methods Failed
**Last Updated:** 2025-09-18
**Status:** 🔴 CRITICAL - Need new approach after multiple control method failures

### Failed Control Methods Summary:

#### 1. Samsung Direct Network Control ❌ FAILED
**Issues:**
- Samsung WebSocket API fails intermittently from presence sensor
- TV gets stuck in standby mode with "WebSocket power toggle failed after 3 attempts"
- Connection reuse issues causing stale WebSocket connections
- Wake-on-LAN unreliable from standby mode
- Complex state management with poor reliability

#### 2. Samsung CEC Control ❌ FAILED  
**Issues:**
- CEC power-on has 25-second cooldown after power-off
- CEC power-off does not work reliably
- No reliable power state feedback mechanism
- Hardware complexity with limited functionality

#### 3. Direct Tapo PyP100 Control ❌ FAILED
**Issues:**
- PyP100 connection failed despite correct credentials
- Authentication errors with TP-Link cloud services
- Inconsistent API behavior with newer firmware

#### 4. Amazon Alexa AlexaPy Control ❌ FAILED
**Issues:**
- AlexaPy login fails due to Amazon security measures
- Requires 2FA/captcha handling not supported by library
- Amazon actively blocks unofficial API access
- Unofficial library with no guarantee of continued functionality

### Root Cause Analysis:
All attempted control methods rely on unofficial APIs, proprietary protocols, or cloud services that are either unreliable or actively restricted by vendors.

---

## 📋 FAILED ATTEMPTS DOCUMENTATION

### ❌ Alexa AlexaPy Integration (ABANDONED)
**Status:** FAILED - AlexaPy cannot authenticate with Amazon
**Date:** 2025-09-18

#### What Was Attempted:
- [x] Installed AlexaPy library v1.29.8
- [x] Created alexa_tv_control.py module with async/sync interfaces
- [x] Updated config.json with Amazon credentials
- [x] Integrated with presence_sensor.py
- [x] Created test scripts

#### Failure Points:
- Amazon login fails due to security measures (2FA/captcha)
- AlexaPy is unofficial and Amazon actively blocks such access
- No reliable way to bypass Amazon's authentication requirements
- Library may break at any time due to Amazon changes

#### Lessons Learned:
- Unofficial APIs for major cloud services are unreliable
- Amazon has strong anti-automation measures
- Voice control works manually but programmatic access is blocked

---

## 🧹 CODEBASE CLEANUP NEEDED

### Files to Archive/Remove:
- `alexa_tv_control.py` - Failed Alexa integration
- `test_alexa_control.py` - Failed test script
- AlexaPy dependency in requirements
- Alexa config section in config.json

### Failed Code Artifacts:
- Samsung WebSocket reconnection logic
- CEC control implementation 
- Tapo PyP100 integration attempts
- AlexaPy authentication code

### What to Keep:
- Core presence detection (UART sensor working)
- Configuration framework
- Logging infrastructure
- Basic TV control interface structure

---

## Previous Phases (For Reference)

### ~~Samsung Network Control Implementation~~ ❌ DEPRECATED
**Status:** 🔴 FAILED - Unreliable in production
**Reason:** WebSocket API intermittent failures, connection management issues

---

## ✅ MILESTONE: Samsung Network Control Implementation (2025-08-28)
**Status:** 🟢 COMPLETED  
**Objective:** Replace IR/CEC control with Samsung network API for reliable TV control

### Completed Implementation:
1. **✅ Samsung Network Library Integration**
   - Installed `samsungtvws[async,encrypted]` in virtual environment
   - Full support for Samsung Frame TV network control via WebSocket API
   - Eliminated IR blaster hardware dependency (GPIO 24 now available)

2. **✅ Configuration Updates**
   - Added `samsung_tv` section with network settings (IP, port, token, Wake-on-LAN)
   - Configured TV discovery and MAC address detection
   - Disabled `ir` and `cec` sections (kept as backup)

3. **✅ Samsung TV Controller Module (`samsung_tv_control.py`)**
   - Network connectivity checking and retry logic
   - Accurate power state detection using Samsung's `PowerState` API (`on`/`standby`)
   - Smart multi-strategy power control (WebSocket, Wake-on-LAN, CEC fallback)
   - Comprehensive error handling and SSL warning suppression

4. **✅ Updated Presence Sensor (`presence_sensor.py`)**
   - Integrated Samsung network control instead of IR
   - Maintained same timing logic (immediate on, 10min delay off)
   - Added development mode with dry-run testing

5. **✅ TV Discovery Tool (`discover_samsung_tv.py`)**
   - Network scanning to find Samsung TVs automatically
   - Auto-configuration of IP address, port, and MAC address for Wake-on-LAN

### Key Technical Insights Discovered:
- ❌ Samsung WebSocket API **does not support** explicit `KEY_POWERON`/`KEY_POWEROFF` commands
- ✅ Samsung WebSocket API **only supports** `KEY_POWER` (toggle) commands  
- ✅ Samsung `PowerState` API accurately reports TV state: `on`, `standby`, or unreachable
- ✅ WebSocket toggle works reliably: `on` ↔ `standby` 
- ✅ Wake-on-LAN works for fully powered-off TVs (requires MAC address)

### Optimal Control Strategy Implemented:
**Power ON (Smart State-Aware):**
1. If TV reports `on` → Already on, return success
2. If TV reports `standby` → Use WebSocket toggle (instant, reliable)
3. If TV unreachable → Wake-on-LAN + WebSocket toggle fallback
4. CEC backup (with 25s cooldown tracking)

**Power OFF:**
1. WebSocket toggle: `on` → `standby` (Samsung TVs stay network-reachable in standby)
2. Accurate standby detection via PowerState API

### Available Commands:
```bash
# Activate virtual environment (required)
source venv/bin/activate

# TV Discovery and Configuration
python3 discover_samsung_tv.py

# Power Control (now working reliably)
python3 samsung_tv_control.py ensure-on    # Smart context-aware power on
python3 samsung_tv_control.py ensure-off   # Smart context-aware power off
python3 samsung_tv_control.py status       # Accurate power state detection
python3 samsung_tv_control.py on/off/toggle/info

# Presence System Testing
python3 presence_sensor.py --dev --dry-run --verbose
```

**Success Criteria MET:** ✅ TV reliably controlled via network API with accurate state detection

---

## ✅ MILESTONE: Basic Presence Sensor Integration (2025-08-28)
**Status:** 🟢 COMPLETED  
**Objective:** Integrate DFRobot SENS0395 sensor with network-based TV control

### Completed Implementation:
1. **✅ CM5 GPIO Library Integration**
   - Installed and configured `lgpio` library for Raspberry Pi CM5 compatibility
   - GPIO pin 14 successfully initialized via chip 0
   - Real-time sensor state reading working correctly

2. **✅ Hardware Sensor Integration**
   - DFRobot SENS0395 mmWave sensor connected and tested on GPIO 14
   - Sensor state transitions detected (HIGH/LOW presence detection)
   - Hardware debouncing and state management implemented

3. **✅ End-to-End System Validation**
   - ✅ Presence Detection: Real sensor triggers immediate TV power-on
   - ✅ Samsung Network Control: TV turned on successfully via WebSocket API
   - ✅ Timing Logic: 10-minute delay timer activated on presence loss
   - ✅ State Management: Proper transitions between presence/no-presence states

### Technical Implementation Details:
- **GPIO Library**: `lgpio` (modern library for CM5, replaces RPi.GPIO)
- **Sensor Pin**: GPIO 14 (BCM numbering)
- **Debounce Time**: 2.0 seconds (configurable)
- **Turn-off Delay**: 600 seconds (10 minutes)
- **TV Control**: Samsung WebSocket API with Wake-on-LAN fallback

### Test Results:
```
lgpio initialized - sensor on pin 14 via chip 0 (current: 1)
PRESENCE DETECTED → TV turned on successfully
PRESENCE LOST → Scheduling TV off in 600 seconds
```

**Success Criteria MET:** ✅ Sensor reliably detects presence and triggers network TV control

---

## Phase 3: Production Service Setup  
**Status:** 🔴 Not Started  
**Objective:** Deploy as systemd service with monitoring

### Planned Steps:
1. [ ] **Service Configuration**
   - Create systemd service file
   - Configure auto-restart and logging
   - Setup service dependencies (virtual environment path)

2. [ ] **Installation Script**
   - Automate virtual environment setup
   - Configure Samsung TV discovery and pairing
   - Setup service auto-start

3. [ ] **Monitoring & Health Checks**
   - Implement network connectivity monitoring
   - Add TV responsiveness checks
   - Setup log rotation and alerting

**Success Criteria:** System runs reliably as a service for 24+ hours

---

## ~~Phase 1: IR Code Learning~~ - OBSOLETED
**Status:** 🟪 OBSOLETED by Network Control  
**Reason:** Samsung network API provides superior reliability and eliminates hardware complexity

### LIRC Cleanup Status: RESOLVED ✅
- **Previous Issue:** LIRC installation left IR transmitter permanently on
- **Resolution:** Fully removed LIRC, disabled GPIO overlays, system cleaned up
- **Status:** GPIO 24 now available for other uses, no IR hardware needed

---

## Architecture Decision: Network vs IR/CEC

### ✅ **Chosen: Samsung Network API**
**Benefits:**
- **Reliability:** No line-of-sight issues, works through walls
- **Speed:** Immediate network commands vs IR delays
- **Accuracy:** Real-time power state detection (`PowerState` API)
- **Simplicity:** No IR hardware required, eliminates GPIO 24 dependency
- **Features:** Access to TV info, apps, Frame art mode controls

### ❌ **Rejected: IR + CEC Hybrid**
**Limitations Discovered:**
- CEC power-on has 25-second cooldown after power-off
- CEC power-off does not work reliably
- IR requires line-of-sight and hardware complexity
- No reliable power state feedback mechanism

---

## Current System Status

### ✅ **Working Components:**
- Samsung Frame TV network control (WebSocket API)
- Power state detection (`on`/`standby`)
- TV discovery and auto-configuration  
- Presence detection framework (ready for sensor)
- Development mode with dry-run testing

### 📋 **Dependencies:**
- ✅ Python 3.x + virtual environment
- ✅ samsungtvws[async,encrypted] library
- ✅ Samsung Frame TV on same network
- ⏳ DFRobot SENS0395 mmWave sensor (ready to integrate)
- ⏳ systemd service configuration (next phase)

### 🔧 **Hardware Status:**
- ✅ Raspberry Pi GPIO available
- ✅ Samsung Frame 43" TV (network configured: 192.168.0.171)
- ✅ TV Wake-on-LAN configured (MAC: 28:af:42:46:a8:0e)
- ⏳ DFRobot SENS0395 sensor (GPIO 14 reserved)
- 🟪 Adafruit IR hardware (no longer needed)

---

## 🔄 CURRENT ACTION PLAN (2025-09-17)
**Status:** 🟡 IN PROGRESS  
**Platform:** Raspberry Pi Compute Module 5 (CM5)
**Last Updated:** 2025-09-17

---

## 🎯 PROJECT GOAL
Create a reliable presence detection system using DFRobot SENS0395 mmWave sensor to automatically control Samsung Frame TV via network API.

---

## 📋 IMPLEMENTATION PLAN & PROGRESS

### Phase 1: Resolve Sensor Communication ✅ COMPLETED (2025-09-17)
**Objective:** Get reliable data from DFRobot SENS0395 sensor

#### Tasks:
- [x] **Hardware Verification**
  - [x] Verified sensor wiring (TX→GPIO1/RX, 5V power, GND)
  - [x] Confirmed proper pin connections on CM5
  - [x] Power and data lines tested successfully

- [x] **UART Communication Testing**
  - [x] Tested `/dev/ttyAMA1` availability and permissions ✅
  - [x] Successfully ran `debug_sensor_strings.py --port /dev/ttyAMA1`
  - [x] Confirmed 115200 baud rate working correctly
  - [x] Captured sensor output: `$JYBSS,0/1, , , *` format

- [x] **Sensor Configuration**
  - [x] Configured detection range to 2 meters
  - [x] Settings saved to non-volatile memory
  - [x] Configuration persists across power cycles

**Resolution:** 
- UART mode working perfectly on `/dev/ttyAMA1`
- Sensor outputs presence data at 1Hz
- Detection range successfully limited to 2 meters

---

### Phase 2: Implement Sensor String Parsing ✅ COMPLETED (2025-09-17)
**Objective:** Parse UART data for presence detection

#### Tasks:
- [x] **Parse Sensor Protocol**
  - [x] Decoded UART string format: `$JYBSS,1, , , *` (presence) / `$JYBSS,0, , , *` (no presence)
  - [x] Identified presence indicators (1=detected, 0=not detected)
  - [x] Documented in debug scripts and sensor module

- [x] **Update Presence Detection Code**
  - [x] Created `uart_sensor.py` module for UART communication
  - [x] Modified `presence_sensor.py` to support both UART and GPIO modes
  - [x] Added robust error handling and reconnection logic
  - [x] Implemented callbacks for presence state changes

- [x] **Testing**
  - [x] Tested parsing logic with real sensor data
  - [x] Integration tested with presence detection system
  - [x] Verified sub-second response time

---

### Phase 3: Configuration Updates ✅ COMPLETED (2025-09-17)
**Objective:** Support both trigger and UART modes

#### Tasks:
- [x] **Update config.json**
  - [x] Added sensor mode selection (trigger/uart)
  - [x] Added UART settings (port, baud, timeout)
  - [x] Maintained backward compatibility with trigger mode

- [ ] **Example Configuration**
  ```json
  "sensor": {
    "mode": "uart",
    "uart": {
      "port": "/dev/ttyAMA1",
      "baudrate": 115200,
      "timeout": 1.0
    },
    "trigger": {
      "gpio_pin": 14,
      "debounce_time": 2.0
    }
  }
  ```

---

### Phase 4: System Integration Testing ⏳ WAITING
**Objective:** Validate end-to-end functionality

#### Tasks:
- [ ] **Functional Testing**
  - [ ] Test presence detection → TV on (immediate)
  - [ ] Test no presence → TV off (10 min delay)
  - [ ] Verify state persistence across restarts

- [ ] **Reliability Testing**
  - [ ] 24-hour continuous operation test
  - [ ] Network interruption recovery test
  - [ ] Power cycle recovery test

- [ ] **Performance Validation**
  - [ ] Response time < 2 seconds
  - [ ] CPU usage < 5%
  - [ ] Memory usage stable

---

### Phase 5: Production Deployment ⏳ WAITING
**Objective:** Deploy as reliable system service

#### Tasks:
- [ ] **Service Configuration**
  - [ ] Create `/etc/systemd/system/presence-sensor.service`
  - [ ] Configure auto-restart on failure
  - [ ] Set up proper dependencies

- [ ] **Installation Automation**
  - [ ] Create `install.sh` script
  - [ ] Automate virtual environment setup
  - [ ] Handle Samsung TV pairing

- [ ] **Monitoring Setup**
  - [ ] Configure log rotation
  - [ ] Add health check endpoint
  - [ ] Set up alerting for failures

---

### Phase 6: Optional Enhancements 🔵 FUTURE
**Objective:** Add advanced features

#### Potential Features:
- [ ] MQTT integration for Home Assistant
- [ ] Web interface for configuration
- [ ] Mobile app for manual control
- [ ] Scheduling (disable during certain hours)
- [ ] Multi-zone detection with multiple sensors
- [ ] Energy usage tracking

---

## 🚧 CURRENT BLOCKERS

1. **Primary Blocker: Sensor Communication**
   - Cannot proceed until sensor data is readable
   - May need hardware debugging tools
   - Consider purchasing alternative sensor as backup

2. **Platform Issues:**
   - CM5 incompatible with some GPIO libraries
   - Limited to hardware UART (no software serial)
   - May need to document CM5-specific setup

---

## ✅ COMPLETED COMPONENTS

### Samsung TV Control Module
- Network discovery and auto-configuration
- WebSocket API integration
- Power state detection
- Wake-on-LAN support
- Smart power control logic

### Core Framework
- Presence detection state machine
- Configuration system
- Logging infrastructure
- Development/dry-run modes
- Timer management

### Development Tools
- `discover_samsung_tv.py` - TV discovery
- `samsung_tv_control.py` - TV control testing
- `debug_sensor_strings.py` - UART debugging
- Multiple debug utilities for sensor testing

---

## 📝 NOTES FOR TRACKING

### Test Commands Reference:
```bash
# Activate virtual environment
source venv/bin/activate

# Test TV control
python3 samsung_tv_control.py status

# Test sensor UART
python3 debug_sensor_strings.py --port /dev/ttyAMA1 --duration 30

# Run presence system (dry run)
python3 presence_sensor.py --dev --dry-run --verbose
```

### Hardware Checklist:
- [x] Raspberry Pi CM5 setup
- [x] Samsung Frame TV network configured (192.168.0.171)
- [ ] DFRobot SENS0395 sensor working
- [x] Virtual environment with dependencies
- [ ] Systemd service configured

### Documentation To Update:
- [ ] README.md - final setup instructions
- [ ] CLAUDE.md - any new development patterns
- [ ] GPIO_PINOUT.md - final pin assignments

---

## 🔄 PROGRESS TRACKING

**Last Action:** Successfully integrated UART sensor and tested end-to-end system (2025-09-17)
**Next Action:** Deploy as systemd service for production use
**Status:** System fully functional in development mode - ready for production deployment

### Today's Achievements (2025-09-17):
- ✅ Fixed UART sensor communication on CM5
- ✅ Configured sensor for 2-meter detection range
- ✅ Created modular UART sensor module
- ✅ Updated presence_sensor.py for dual-mode support
- ✅ Successfully tested presence → TV ON → absence → TV OFF cycle
- ✅ Created configuration and debugging utilities

---

## Notes
- Network control approach eliminates hardware complexity while improving reliability
- Samsung Frame TV API provides all necessary control and feedback capabilities  
- Virtual environment ensures clean dependency management
- Ready to focus on presence detection optimization rather than TV control debugging