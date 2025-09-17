#!/usr/bin/env python3
"""
Simple software serial using RPi.GPIO with improved timing
Works on any GPIO pin without interfering with hardware UART
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

class SimpleSerial:
    def __init__(self, gpio_pin, baud_rate=115200):
        self.gpio_pin = gpio_pin
        self.baud_rate = baud_rate
        self.bit_time = 1.0 / baud_rate  # ~8.68 microseconds for 115200
        
    def setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"Simple serial setup on GPIO {self.gpio_pin} at {self.baud_rate} baud")
        
    def cleanup(self):
        GPIO.cleanup()
        
    def wait_for_start_bit(self, timeout=1.0):
        """Wait for start bit (high to low transition)"""
        start_time = time.time()
        
        # Wait for line to be idle (high)
        while GPIO.input(self.gpio_pin) == 0:
            if time.time() - start_time > timeout:
                return False
                
        # Wait for start bit (high to low)
        while GPIO.input(self.gpio_pin) == 1:
            if time.time() - start_time > timeout:
                return False
                
        return True
        
    def read_byte(self):
        """Read one byte using bit timing"""
        # Wait for start bit
        if not self.wait_for_start_bit(0.1):
            return None
            
        # Wait to middle of start bit to confirm it's valid
        time.sleep(self.bit_time * 0.5)
        if GPIO.input(self.gpio_pin) != 0:
            return None  # Not a valid start bit
            
        # Read 8 data bits (LSB first)
        byte_value = 0
        for bit_pos in range(8):
            time.sleep(self.bit_time)  # Move to middle of data bit
            if GPIO.input(self.gpio_pin):
                byte_value |= (1 << bit_pos)
                
        # Skip stop bit
        time.sleep(self.bit_time)
        
        return byte_value

def monitor_continuous(gpio_pin=15, duration=None):
    """Continuously monitor for serial data"""
    serial = SimpleSerial(gpio_pin)
    
    try:
        serial.setup()
        print(f"Monitoring GPIO {gpio_pin} for serial data...")
        print("Move near sensor to trigger data output")
        print("-" * 50)
        
        start_time = time.time()
        byte_count = 0
        line_buffer = []
        
        while True:
            if duration and (time.time() - start_time) > duration:
                break
                
            byte_val = serial.read_byte()
            if byte_val is not None:
                byte_count += 1
                
                # Handle printable characters
                if 32 <= byte_val <= 126:
                    char = chr(byte_val)
                    line_buffer.append(char)
                elif byte_val in [0x0A, 0x0D]:  # Newline/CR
                    if line_buffer:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        line = ''.join(line_buffer).strip()
                        if line:
                            print(f"[{timestamp}] #{byte_count}: {line}")
                        line_buffer = []
                else:
                    # Non-printable byte
                    line_buffer.append(f"[{byte_val:02X}]")
                    
    except KeyboardInterrupt:
        print(f"\nReceived {byte_count} bytes total")
    finally:
        serial.cleanup()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple software serial for DFRobot sensor')
    parser.add_argument('--gpio', type=int, default=15, help='GPIO pin (default: 15)')
    parser.add_argument('--duration', type=int, help='Duration in seconds')
    
    args = parser.parse_args()
    
    print("DFRobot SENS0395 Simple Serial Monitor")
    print("=" * 50)
    
    monitor_continuous(args.gpio, args.duration)

if __name__ == "__main__":
    main()