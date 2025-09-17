#!/usr/bin/env python3
"""
Software serial reader using pigpio library
This can read serial data from any GPIO pin without interfering with hardware UART
"""

import pigpio
import time
import threading
from datetime import datetime

class SoftwareSerial:
    def __init__(self, gpio_pin, baud_rate=115200):
        self.gpio_pin = gpio_pin
        self.baud_rate = baud_rate
        self.pi = None
        self.data_buffer = []
        self.running = False
        
    def start(self):
        """Initialize pigpio and start monitoring"""
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise Exception("Failed to connect to pigpio daemon")
        
        # Set up GPIO as input with pull-up
        self.pi.set_mode(self.gpio_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.gpio_pin, pigpio.PUD_UP)
        
        print(f"Software serial initialized on GPIO {self.gpio_pin} at {self.baud_rate} baud")
        return True
        
    def stop(self):
        """Stop monitoring and cleanup"""
        self.running = False
        if self.pi:
            self.pi.stop()
            
    def read_byte(self, timeout=1.0):
        """Read one byte using software serial"""
        bit_time = 1.0 / self.baud_rate
        
        # Wait for start bit (1 to 0 transition)
        start_time = time.time()
        while self.pi.read(self.gpio_pin) == 1:
            if time.time() - start_time > timeout:
                return None
            time.sleep(0.00001)  # 10us
        
        # Wait for middle of start bit to confirm
        time.sleep(bit_time * 0.5)
        if self.pi.read(self.gpio_pin) != 0:
            return None  # False start
            
        # Read 8 data bits (LSB first)
        byte_value = 0
        for bit_pos in range(8):
            time.sleep(bit_time)
            if self.pi.read(self.gpio_pin):
                byte_value |= (1 << bit_pos)
                
        # Wait for stop bit
        time.sleep(bit_time)
        
        return byte_value
        
    def read_line(self, timeout=5.0):
        """Read a complete line of text"""
        line_buffer = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            byte_val = self.read_byte(timeout=0.1)
            if byte_val is not None:
                if byte_val == 0x0A or byte_val == 0x0D:  # Newline
                    if line_buffer:
                        return ''.join(chr(b) for b in line_buffer if 32 <= b <= 126)
                else:
                    line_buffer.append(byte_val)
                    
        return None

def monitor_sensor_data(gpio_pin=15, duration=None):
    """Monitor sensor data from specified GPIO pin"""
    serial = SoftwareSerial(gpio_pin, 115200)
    
    try:
        serial.start()
        print(f"Monitoring sensor data on GPIO {gpio_pin} (Press Ctrl+C to stop)")
        print("-" * 60)
        
        start_time = time.time()
        line_count = 0
        
        while True:
            if duration and (time.time() - start_time) > duration:
                break
                
            line = serial.read_line(timeout=1.0)
            if line:
                line_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] #{line_count:04d}: {line}")
                
    except KeyboardInterrupt:
        print(f"\n\nReceived {line_count} lines")
    finally:
        serial.stop()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Software serial monitor for DFRobot sensor')
    parser.add_argument('--gpio', type=int, default=15, help='GPIO pin number (default: 15)')
    parser.add_argument('--duration', type=int, help='Monitor duration in seconds')
    
    args = parser.parse_args()
    
    print("DFRobot SENS0395 Software Serial Monitor")
    print("=" * 50)
    
    # Check if pigpio daemon is running
    import subprocess
    try:
        subprocess.check_output(['pgrep', 'pigpiod'])
        print("✓ pigpio daemon is running")
    except subprocess.CalledProcessError:
        print("⚠ Starting pigpio daemon...")
        subprocess.run(['sudo', 'pigpiod'], check=True)
        time.sleep(1)
    
    monitor_sensor_data(args.gpio, args.duration)

if __name__ == "__main__":
    main()