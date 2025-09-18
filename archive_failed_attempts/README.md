# Failed Control Method Implementations

This directory contains code from failed attempts to control the TV/smart plug through various methods.

## Archived Files:

### Alexa Control (2025-09-18)
- `alexa_tv_control.py` - AlexaPy integration attempt
- `test_alexa_control.py` - Test script for Alexa control
- **Failure:** Amazon authentication blocked (2FA/captcha required)

### Tapo Direct Control (2025-09-17)
- `test_tapo_quick.py` - PyP100 library test
- `test_tapo_klap.py` - KLAP protocol test
- `discover_tapo.py` - Tapo device discovery
- `tapo_tv_control.py` - Tapo control module
- **Failure:** Authentication failed despite correct credentials

### Kasa Control (2025-09-17)
- `test_kasa_tapo.py` - Kasa library test
- **Failure:** Device not compatible with Kasa protocol

## Do Not Reimplement:
These approaches have been proven to fail due to vendor restrictions and security measures.

## Working Components:
- Presence detection via UART sensor (working)
- Samsung TV network control (unreliable but functional)
- Core configuration and logging framework

## Next Steps:
Consider reliable hardware-based solutions:
- IR transmitter with custom codes
- Relay-based power switching
- Smart switch with local API