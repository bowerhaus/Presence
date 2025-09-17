#!/usr/bin/env python3
"""
Check current sensor configuration
"""

import serial
import time
import sys

def check_config(port="/dev/ttyAMA1"):
    """Check current sensor configuration"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
        print("Checking sensor configuration...")
        print("=" * 50)
        
        # Commands to check configuration
        commands = [
            "sensorStop",  # Stop sensor to access config
            "detRangeCfg -1",  # Query current range config
            "outputLatency -1",  # Query output latency
            "sensorStart"  # Restart sensor
        ]
        
        for cmd in commands:
            print(f"\nSending: {cmd}")
            ser.write((cmd + '\r\n').encode('utf-8'))
            time.sleep(0.5)
            
            # Read response
            response = ""
            while ser.in_waiting > 0:
                response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            
            if response:
                print(f"Response: {response.strip()}")
        
        # Monitor output briefly to confirm it's working
        print("\n" + "=" * 50)
        print("Monitoring sensor output for 5 seconds...")
        start_time = time.time()
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if '$JYBSS' in line:
                    if ',1,' in line:
                        print(f"PRESENCE DETECTED: {line}")
                    else:
                        print(f"No presence: {line}")
            time.sleep(0.1)
        
        ser.close()
        print("\nConfiguration check complete")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_config()