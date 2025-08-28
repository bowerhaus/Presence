# GPIO Pin Reference

## Current Configuration
We are using **BCM (GPIO) numbering**, not physical pin numbers.

### Pin Assignments:
| Function | GPIO (BCM) | Physical Pin | Notes |
|----------|------------|--------------|-------|
| **Presence Sensor** | GPIO 14 | Pin 8 | DFRobot SENS0395 trigger output |

### Available GPIO Pins:
| GPIO (BCM) | Physical Pin | Status | Notes |
|------------|--------------|--------|-------|
| GPIO 23 | Pin 16 | Available | Previously used for IR receiver |
| GPIO 24 | Pin 18 | Available | Previously used for IR transmitter |

### Important Notes:
- `GPIO.setmode(GPIO.BCM)` is used in all scripts
- GPIO numbers refer to the Broadcom SOC channel numbers
- These are different from the physical pin numbers on the header
- GPIO 23 and 24 are now available for other uses since IR hardware was removed

### Quick Reference:
```python
# In Python with RPi.GPIO:
GPIO.setmode(GPIO.BCM)  # Use GPIO numbers
GPIO.setup(14, GPIO.IN)  # Presence sensor on GPIO14, not physical pin 14

# To use physical pins instead (NOT what we're doing):
# GPIO.setmode(GPIO.BOARD)  # Would use physical pin numbers
```

### Full Raspberry Pi GPIO Pinout:
```
                 3V3  (1) (2)  5V
       (GPIO2)  SDA1  (3) (4)  5V
       (GPIO3)  SCL1  (5) (6)  GND
        (GPIO4)  GP4  (7) (8)  TXD  (GPIO14) <- PRESENCE SENSOR
                 GND  (9) (10) RXD  (GPIO15)
       (GPIO17) GP17 (11) (12) GP18 (GPIO18)
       (GPIO27) GP27 (13) (14) GND
       (GPIO22) GP22 (15) (16) GP23 (GPIO23) <- AVAILABLE
                 3V3 (17) (18) GP24 (GPIO24) <- AVAILABLE
      (GPIO10) MOSI  (19) (20) GND
       (GPIO9) MISO  (21) (22) GP25 (GPIO25)
      (GPIO11) SCLK  (23) (24) CE0  (GPIO8)
                 GND (25) (26) CE1  (GPIO7)
        (GPIO0) ID_SD (27) (28) ID_SC (GPIO1)
        (GPIO5) GP5  (29) (30) GND
        (GPIO6) GP6  (31) (32) GP12 (GPIO12)
       (GPIO13) GP13 (33) (34) GND
       (GPIO19) GP19 (35) (36) GP16 (GPIO16)
       (GPIO26) GP26 (37) (38) GP20 (GPIO20)
                 GND (39) (40) GP21 (GPIO21)
```

### Wiring Summary:
1. **DFRobot SENS0395 Presence Sensor**:
   - VCC → 5V (Pin 2 or 4)  
   - GND → GND (Any GND pin)
   - OUT → GPIO 14 (Physical Pin 8)

### Network Control Benefits:
- No GPIO pins needed for TV control (network-based)  
- Simplified wiring with only sensor connection required
- GPIO 23 and 24 available for future expansion