#!/usr/bin/env python3
"""
Debug program to monitor UART string output from DFRobot SENS0395 mmWave sensor
This program reads and displays strings sent by the sensor over UART communication.
"""

import serial
import time
import sys
import argparse
from datetime import datetime

# Common UART settings for mmWave sensors
DEFAULT_BAUDRATE = 115200  # DFRobot SENS0395 specification
# GPIO 15 (RXD) receives UART data from the sensor
DEFAULT_PORT = "/dev/ttyAMA1"  # Hardware UART on GPIO 14/15 (CM5 uses AMA1)
DEFAULT_DURATION = 30  # Default monitoring duration in seconds
ALTERNATIVE_PORTS = ["/dev/ttyAMA0", "/dev/serial0", "/dev/ttyS0"]

def setup_serial(port, baudrate, timeout=1):
    """Setup serial connection with error handling"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
        return ser
    except serial.SerialException as e:
        print(f"Failed to open {port} at {baudrate} baud: {e}")
        return None

def read_sensor_strings(port, baudrate, duration=None):
    """Read and display strings from the sensor"""
    ser = setup_serial(port, baudrate)
    if not ser:
        return False
    
    print(f"Connected to {port} at {baudrate} baud")
    print("Monitoring sensor strings (Press Ctrl+C to stop)...")
    print("Looking for format: $JYBSS,0/1, , , * (0=no presence, 1=presence detected)")
    print("-" * 60)
    
    start_time = time.time()
    line_count = 0
    
    try:
        while True:
            if duration and (time.time() - start_time) > duration:
                break
                
            if ser.in_waiting > 0:
                try:
                    # Try to read a line
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        line_count += 1
                        
                        # Parse $JYBSS format for presence detection
                        if line.startswith('$JYBSS'):
                            parts = line.split(',')
                            if len(parts) >= 2:
                                presence = parts[1].strip()
                                if presence == '1':
                                    print(f"[{timestamp}] #{line_count:04d}: *** PRESENCE DETECTED *** - {line}")
                                elif presence == '0':
                                    print(f"[{timestamp}] #{line_count:04d}: No presence - {line}")
                                else:
                                    print(f"[{timestamp}] #{line_count:04d}: {line}")
                            else:
                                print(f"[{timestamp}] #{line_count:04d}: {line}")
                        else:
                            print(f"[{timestamp}] #{line_count:04d}: {line}")
                except UnicodeDecodeError:
                    # If UTF-8 fails, try reading raw bytes
                    raw_data = ser.read(ser.in_waiting)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp}] RAW: {raw_data.hex()} | ASCII: {raw_data}")
                except Exception as e:
                    print(f"Read error: {e}")
            else:
                time.sleep(0.01)  # Small delay to prevent busy waiting
                
    except KeyboardInterrupt:
        print(f"\n\nStopped monitoring. Total lines received: {line_count}")
    finally:
        ser.close()
        
    return True

def test_multiple_bauds(port):
    """Test multiple common baud rates"""
    common_bauds = [9600, 115200, 19200, 38400, 57600]
    
    for baud in common_bauds:
        print(f"\n=== Testing {port} at {baud} baud ===")
        ser = setup_serial(port, baud, timeout=0.5)
        if ser:
            print(f"Port opened successfully. Testing for 5 seconds...")
            time.sleep(0.1)  # Let port settle
            
            # Check for immediate data
            found_data = False
            for _ in range(50):  # Test for 5 seconds
                if ser.in_waiting > 0:
                    try:
                        data = ser.read(min(ser.in_waiting, 100))
                        print(f"Data found: {data}")
                        found_data = True
                        break
                    except:
                        pass
                time.sleep(0.1)
            
            if not found_data:
                print("No data received at this baud rate")
            ser.close()
        else:
            print(f"Failed to open port at {baud} baud")

def main():
    parser = argparse.ArgumentParser(description='Debug DFRobot SENS0395 UART string output')
    parser.add_argument('--port', default=DEFAULT_PORT, help=f'Serial port (default: {DEFAULT_PORT})')
    parser.add_argument('--baudrate', type=int, default=DEFAULT_BAUDRATE, 
                       help=f'Baud rate (default: {DEFAULT_BAUDRATE})')
    parser.add_argument('--duration', type=int, default=DEFAULT_DURATION, help=f'Monitoring duration in seconds (default: {DEFAULT_DURATION})')
    parser.add_argument('--test-bauds', action='store_true', 
                       help='Test multiple baud rates to find the correct one')
    parser.add_argument('--test-ports', action='store_true',
                       help='Test multiple serial ports')
    
    args = parser.parse_args()
    
    print("DFRobot SENS0395 mmWave Sensor String Monitor")
    print("=" * 50)
    
    if args.test_ports:
        all_ports = [DEFAULT_PORT] + ALTERNATIVE_PORTS
        for port in all_ports:
            print(f"\n=== Testing port {port} ===")
            if read_sensor_strings(port, args.baudrate, duration=5):
                print(f"Port {port} accessible")
            else:
                print(f"Port {port} not accessible")
        return
    
    if args.test_bauds:
        test_multiple_bauds(args.port)
        return
    
    # Normal monitoring
    success = read_sensor_strings(args.port, args.baudrate, args.duration)
    if not success:
        print(f"\nTrying alternative ports...")
        for alt_port in ALTERNATIVE_PORTS:
            print(f"Trying {alt_port}...")
            if read_sensor_strings(alt_port, args.baudrate, args.duration):
                break

if __name__ == "__main__":
    main()