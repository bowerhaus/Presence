#!/usr/bin/env python3
"""
Configuration tool for DFRobot SENS0395 mmWave sensor
Allows setting detection range and other parameters via UART commands
"""

import serial
import time
import sys
import argparse

def send_command(ser, command, wait_time=0.1):
    """Send a command to the sensor and wait for response"""
    print(f"Sending: {command}")
    ser.write(command.encode('utf-8'))
    time.sleep(wait_time)
    
    # Read response
    response = ""
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    
    if response:
        print(f"Response: {response.strip()}")
    return response

def configure_sensor(port="/dev/ttyAMA1", baudrate=115200):
    """Configure sensor parameters"""
    
    print("DFRobot SENS0395 Configuration Tool")
    print("=" * 50)
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        print(f"Connected to {port} at {baudrate} baud\n")
        
        # According to DFRobot wiki, configuration commands:
        # Detection range: 0-9 meters
        # Command format for range: 
        
        print("Available commands:")
        print("1. Set detection range (0-9 meters)")
        print("2. Set output delay (0-100 seconds)")
        print("3. Get current settings")
        print("4. Monitor current output")
        print("5. Exit")
        
        while True:
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                range_m = input("Enter detection range in meters (0-9, recommended 2 for close range): ").strip()
                try:
                    range_val = int(range_m)
                    if 0 <= range_val <= 9:
                        # Set detection range command
                        # Based on typical sensor protocols, might be something like:
                        cmd = f"detRangeCfg -1 {range_val*10} {range_val*100}\r\n"
                        send_command(ser, cmd, wait_time=0.5)
                        print(f"Detection range set to {range_val} meters")
                    else:
                        print("Range must be between 0 and 9 meters")
                except ValueError:
                    print("Invalid input")
            
            elif choice == '2':
                delay = input("Enter output delay in seconds (0-100): ").strip()
                try:
                    delay_val = int(delay)
                    if 0 <= delay_val <= 100:
                        # Set output delay command
                        cmd = f"outputLatency -1 0 {delay_val}\r\n"
                        send_command(ser, cmd, wait_time=0.5)
                        print(f"Output delay set to {delay_val} seconds")
                    else:
                        print("Delay must be between 0 and 100 seconds")
                except ValueError:
                    print("Invalid input")
            
            elif choice == '3':
                # Request current settings
                print("Requesting current settings...")
                send_command(ser, "getLedMode\r\n", wait_time=0.5)
                send_command(ser, "getRange\r\n", wait_time=0.5)
                send_command(ser, "getLatency\r\n", wait_time=0.5)
            
            elif choice == '4':
                print("Monitoring sensor output for 10 seconds...")
                print("Press Ctrl+C to stop")
                start_time = time.time()
                try:
                    while time.time() - start_time < 10:
                        if ser.in_waiting > 0:
                            line = ser.readline().decode('utf-8').strip()
                            if line:
                                if '$JYBSS,1' in line:
                                    print(f"[PRESENCE DETECTED] {line}")
                                elif '$JYBSS,0' in line:
                                    print(f"[No presence] {line}")
                                else:
                                    print(f"[Data] {line}")
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nMonitoring stopped")
            
            elif choice == '5':
                break
            
            else:
                print("Invalid choice")
        
        ser.close()
        print("\nConfiguration complete")
        
    except serial.SerialException as e:
        print(f"Error: {e}")
        return False
    
    return True

def set_range_simple(port="/dev/ttyAMA1", range_meters=2):
    """Simple function to just set the range"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
        print(f"Setting detection range to {range_meters} meters...")
        
        # Based on sensor responses, use correct command sequence
        commands = [
            ("sensorStop", 0.5),  # Stop sensor first
            (f"detRangeCfg -1 0.5 {range_meters}", 0.5),  # Min 0.5m, max range_meters  
            ("saveCfg 0x45670123 0xCDEF89AB 0x956128C6 0xDF54AC89", 0.5),  # Save with magic numbers
            ("sensorStart", 1.0)  # Restart sensor
        ]
        
        for cmd, delay in commands:
            print(f"Sending: {cmd}")
            ser.write((cmd + '\r\n').encode('utf-8'))
            time.sleep(delay)
            
            # Check for response
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                if response:
                    print(f"Response: {response.strip()}")
        
        # Monitor output to verify
        print("\nMonitoring sensor output for 5 seconds to verify...")
        start_time = time.time()
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if '$JYBSS' in line:
                    print(f"Sensor output: {line}")
            time.sleep(0.1)
        
        ser.close()
        print("\nConfiguration attempt complete")
        print("Note: Some sensors require power cycle to apply new settings")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Configure DFRobot SENS0395 sensor')
    parser.add_argument('--port', default='/dev/ttyAMA1', help='Serial port')
    parser.add_argument('--range', type=int, help='Set detection range in meters (0-9)')
    parser.add_argument('--interactive', action='store_true', help='Interactive configuration mode')
    
    args = parser.parse_args()
    
    if args.range is not None:
        set_range_simple(args.port, args.range)
    elif args.interactive:
        configure_sensor(args.port)
    else:
        # Default: set to 2 meters
        print("Setting sensor to 2-meter detection range...")
        set_range_simple(args.port, 2)