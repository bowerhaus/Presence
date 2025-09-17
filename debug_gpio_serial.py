#!/usr/bin/env python3
"""
Debug program to read serial data directly from GPIO 15 using bit-banging
Since hardware UART might be occupied by console, we'll read GPIO 15 directly
"""

import RPi.GPIO as GPIO
import time
import sys
from datetime import datetime

# GPIO pin for sensor data (RX)
SENSOR_GPIO = 15

# UART settings for DFRobot SENS0395
BAUD_RATE = 115200
BIT_DURATION = 1.0 / BAUD_RATE  # Duration of one bit in seconds

def setup_gpio():
    """Setup GPIO for reading serial data"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENSOR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print(f"GPIO {SENSOR_GPIO} configured for input with pull-up")

def read_byte_bitbang():
    """Read one byte using bit-banging (software UART)"""
    # Wait for start bit (high to low transition)
    while GPIO.input(SENSOR_GPIO) == 1:
        time.sleep(0.0001)  # Small delay
    
    # Confirm start bit and wait for middle of bit
    time.sleep(BIT_DURATION / 2)
    if GPIO.input(SENSOR_GPIO) != 0:
        return None  # False start bit
    
    # Read 8 data bits (LSB first)
    byte_value = 0
    for bit_pos in range(8):
        time.sleep(BIT_DURATION)  # Wait for middle of next bit
        if GPIO.input(SENSOR_GPIO):
            byte_value |= (1 << bit_pos)
    
    # Read stop bit
    time.sleep(BIT_DURATION)
    
    return byte_value

def monitor_gpio_simple():
    """Simple GPIO state monitoring"""
    print(f"Monitoring GPIO {SENSOR_GPIO} state changes (Press Ctrl+C to stop)...")
    print("High=1, Low=0")
    print("-" * 60)
    
    last_state = GPIO.input(SENSOR_GPIO)
    print(f"Initial state: {last_state}")
    
    change_count = 0
    try:
        while True:
            current_state = GPIO.input(SENSOR_GPIO)
            if current_state != last_state:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                change_count += 1
                print(f"[{timestamp}] #{change_count:04d}: GPIO {SENSOR_GPIO} changed to {current_state}")
                last_state = current_state
            time.sleep(0.001)  # 1ms polling
            
    except KeyboardInterrupt:
        print(f"\n\nTotal state changes detected: {change_count}")

def monitor_serial_bitbang():
    """Monitor serial data using bit-banging"""
    print(f"Monitoring serial data on GPIO {SENSOR_GPIO} at {BAUD_RATE} baud (Press Ctrl+C to stop)...")
    print("-" * 60)
    
    byte_count = 0
    line_buffer = []
    
    try:
        while True:
            byte_val = read_byte_bitbang()
            if byte_val is not None:
                byte_count += 1
                
                # Convert to character if printable
                if 32 <= byte_val <= 126:  # Printable ASCII
                    char = chr(byte_val)
                    line_buffer.append(char)
                    if char == '\n' or char == '\r':
                        if line_buffer:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            line = ''.join(line_buffer).strip()
                            if line:
                                print(f"[{timestamp}] #{byte_count:04d}: {line}")
                            line_buffer = []
                else:
                    # Non-printable character
                    if byte_val in [0x0A, 0x0D]:  # Newline/Carriage return
                        if line_buffer:
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            line = ''.join(line_buffer).strip()
                            if line:
                                print(f"[{timestamp}] #{byte_count:04d}: {line}")
                            line_buffer = []
                    else:
                        line_buffer.append(f"[0x{byte_val:02X}]")
            
    except KeyboardInterrupt:
        print(f"\n\nTotal bytes received: {byte_count}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug GPIO 15 serial data from DFRobot sensor')
    parser.add_argument('--mode', choices=['simple', 'bitbang'], default='simple',
                       help='Monitoring mode: simple (state changes) or bitbang (serial decode)')
    parser.add_argument('--duration', type=int, help='Monitoring duration in seconds')
    
    args = parser.parse_args()
    
    print("DFRobot SENS0395 GPIO Serial Monitor")
    print("=" * 50)
    print(f"Monitoring GPIO {SENSOR_GPIO}")
    print(f"Mode: {args.mode}")
    print("=" * 50)
    
    try:
        setup_gpio()
        
        if args.mode == 'simple':
            monitor_gpio_simple()
        else:
            monitor_serial_bitbang()
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()
        print("GPIO cleanup complete")

if __name__ == "__main__":
    main()