#!/usr/bin/env python3
"""
Configuration tool for DFRobot SENS0395 mmWave sensor
Properly handles 15cm increment range parameters as per sensor specification
"""

import serial
import time
import sys
import argparse

def meters_to_increments(meters):
    """Convert meters to 15cm increments (sensor native units)"""
    return round(meters / 0.15)

def increments_to_meters(increments):
    """Convert 15cm increments back to meters"""
    return increments * 0.15

def seconds_to_latency_units(seconds):
    """Convert seconds to 25ms latency units (sensor native units)"""
    return round(seconds / 0.025)

def latency_units_to_seconds(units):
    """Convert 25ms latency units back to seconds"""
    return units * 0.025

def send_command(ser, command, wait_time=1.0):
    """Send a command to the sensor and wait for response"""
    print(f"Sending: {command}")
    ser.write((command + '\r\n').encode('utf-8'))
    time.sleep(wait_time)

    # Read response
    response = ""
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

    if response:
        print(f"Response: {response.strip()}")
    return response

def configure_range(ser, min_meters=0.5, max_meters=3.0):
    """Configure detection range using proper 15cm increments"""

    # Convert meters to 15cm increments
    min_increments = meters_to_increments(min_meters)
    max_increments = meters_to_increments(max_meters)

    # Validate range (sensor supports 0-127 increments = 0-19.05m)
    if min_increments < 0 or max_increments > 127:
        print(f"Error: Range out of bounds. Max supported range is {increments_to_meters(127):.1f}m")
        return False

    print(f"Setting range: {min_meters}m to {max_meters}m")
    print(f"Increments: {min_increments} to {max_increments} (15cm units)")

    try:
        # Stop sensor
        send_command(ser, "sensorStop")

        # Set detection range using proper increment values
        range_cmd = f"detRangeCfg -1 {min_increments} {max_increments}"
        send_command(ser, range_cmd)

        # Save configuration
        save_cmd = "saveCfg 0x45670123 0xCDEF89AB 0x956128C6 0xDF54AC89"
        send_command(ser, save_cmd)

        # Restart sensor
        send_command(ser, "sensorStart")

        print(f"✓ Range configured: {min_meters}m to {max_meters}m")
        return True

    except Exception as e:
        print(f"Error configuring range: {e}")
        return False

def configure_timing(ser, detect_delay_sec=2.5, post_delay_sec=10.0):
    """Configure detection timing delays using proper 25ms increments"""

    # Convert seconds to 25ms units
    detect_units = seconds_to_latency_units(detect_delay_sec)
    post_units = seconds_to_latency_units(post_delay_sec)

    print(f"Setting timing: {detect_delay_sec}s detection delay, {post_delay_sec}s post-detection delay")
    print(f"Units: {detect_units} to {post_units} (25ms increments)")

    try:
        send_command(ser, "sensorStop")

        # Set output latency using proper 25ms increment values
        timing_cmd = f"outputLatency -1 {detect_units} {post_units}"
        send_command(ser, timing_cmd)

        # Save configuration
        save_cmd = "saveCfg 0x45670123 0xCDEF89AB 0x956128C6 0xDF54AC89"
        send_command(ser, save_cmd)

        send_command(ser, "sensorStart")

        print(f"✓ Timing configured: {detect_delay_sec}s/{post_delay_sec}s")
        return True

    except Exception as e:
        print(f"Error configuring timing: {e}")
        return False

def monitor_sensor(ser, duration=10):
    """Monitor sensor output for testing"""
    print(f"Monitoring sensor output for {duration} seconds...")
    print("Format: $JYBSS,0/1, , , * (0=no presence, 1=presence detected)")
    print("-" * 60)

    start_time = time.time()
    detection_count = 0
    total_readings = 0

    try:
        while time.time() - start_time < duration:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if '$JYBSS' in line:
                    total_readings += 1
                    timestamp = time.strftime('%H:%M:%S')

                    if ',1,' in line:  # Presence detected
                        detection_count += 1
                        print(f"[{timestamp}] 🟢 PRESENCE DETECTED - {line}")
                    elif total_readings % 5 == 0:  # Show every 5th 'no presence'
                        print(f"[{timestamp}] #{total_readings:04d}: No presence - {line}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

    print(f"\nMonitoring Summary:")
    print(f"Total readings: {total_readings}")
    print(f"Presence detections: {detection_count}")
    if total_readings > 0:
        print(f"Detection rate: {(detection_count/total_readings)*100:.1f}%")

def interactive_config():
    """Interactive configuration mode"""
    print("DFRobot SENS0395 Interactive Configuration")
    print("=" * 50)

    try:
        ser = serial.Serial(
            port="/dev/ttyAMA1",
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        print("✓ Connected to sensor")

        while True:
            print(f"\nConfiguration Options:")
            print(f"1. Set detection range (current: optimized for room detection)")
            print(f"2. Set timing delays")
            print(f"3. Monitor sensor output")
            print(f"4. Factory reset")
            print(f"5. Exit")

            choice = input("\nEnter choice (1-5): ").strip()

            if choice == '1':
                print(f"\nDetection Range Configuration")
                print(f"Sensor uses 15cm increments internally")
                print(f"Recommended ranges:")
                print(f"  Close range: 0.5m to 2m (good for desk/chair)")
                print(f"  Room range: 0.5m to 5m (good for living room)")
                print(f"  Wide range: 0.5m to 9m (maximum sensitivity)")

                max_range = input("Enter maximum detection range in meters (0.5-9.0): ").strip()
                try:
                    max_val = float(max_range)
                    if 0.5 <= max_val <= 9.0:
                        configure_range(ser, min_meters=0.5, max_meters=max_val)
                    else:
                        print("Range must be between 0.5 and 9.0 meters")
                except ValueError:
                    print("Invalid input")

            elif choice == '2':
                print(f"\nTiming Configuration")
                print(f"Sensor uses 25ms increments internally")
                print(f"Detection delay: How long before confirming presence")
                print(f"Post-detection delay: How long to maintain 'presence' after movement stops")
                print(f"Default: 2.5s detection, 10s post-detection (100, 400 units)")

                detect_sec = input("Detection delay in seconds (0.1-25, default 2.5): ").strip() or "2.5"
                post_sec = input("Post-detection delay in seconds (0.5-50, default 10): ").strip() or "10"

                try:
                    d_val = float(detect_sec)
                    p_val = float(post_sec)
                    if 0.1 <= d_val <= 25 and 0.5 <= p_val <= 50:
                        configure_timing(ser, d_val, p_val)
                    else:
                        print("Invalid timing values")
                except ValueError:
                    print("Invalid input")

            elif choice == '3':
                duration = input("Monitor duration in seconds (default 10): ").strip() or "10"
                try:
                    dur_val = int(duration)
                    monitor_sensor(ser, dur_val)
                except ValueError:
                    print("Invalid duration")

            elif choice == '4':
                confirm = input("Factory reset sensor? This will restore default settings (y/N): ").strip().lower()
                if confirm == 'y':
                    print("Performing factory reset...")
                    send_command(ser, "sensorStop")
                    send_command(ser, "factoryReset")
                    time.sleep(2)
                    send_command(ser, "sensorStart")
                    print("✓ Factory reset complete")

            elif choice == '5':
                break

            else:
                print("Invalid choice")

        ser.close()
        print("Configuration session ended")

    except serial.SerialException as e:
        print(f"Error connecting to sensor: {e}")
        return False

    return True

def set_range_simple(port="/dev/ttyAMA1", range_meters=3.0):
    """Simple function to set detection range"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )

        print(f"Setting detection range to {range_meters} meters...")

        # Convert to increments for proper sensor configuration
        min_increments = meters_to_increments(0.5)  # Always start at 0.5m
        max_increments = meters_to_increments(range_meters)

        print(f"Using increments: {min_increments} to {max_increments} (15cm units)")

        commands = [
            "sensorStop",
            f"detRangeCfg -1 {min_increments} {max_increments}",
            "saveCfg 0x45670123 0xCDEF89AB 0x956128C6 0xDF54AC89",
            "sensorStart"
        ]

        for cmd in commands:
            send_command(ser, cmd)

        # Monitor output briefly to verify
        print(f"\nMonitoring sensor output for 5 seconds to verify...")
        monitor_sensor(ser, 5)

        ser.close()
        print(f"\n✓ Range configuration complete: 0.5m to {range_meters}m")
        print("Note: Power cycle sensor if detection seems inconsistent")

    except Exception as e:
        print(f"Error: {e}")

def set_timing_simple(port="/dev/ttyAMA1", detect_sec=2.5, post_sec=10.0):
    """Simple function to set detection timing"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )

        print(f"Setting detection timing: {detect_sec}s detection, {post_sec}s post-detection...")

        # Convert to units for proper sensor configuration
        detect_units = seconds_to_latency_units(detect_sec)
        post_units = seconds_to_latency_units(post_sec)

        print(f"Using units: {detect_units} to {post_units} (25ms increments)")

        commands = [
            "sensorStop",
            f"outputLatency -1 {detect_units} {post_units}",
            "saveCfg 0x45670123 0xCDEF89AB 0x956128C6 0xDF54AC89",
            "sensorStart"
        ]

        for cmd in commands:
            send_command(ser, cmd)

        ser.close()
        print(f"\n✓ Timing configuration complete: {detect_sec}s detection, {post_sec}s post-detection")

    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Configure DFRobot SENS0395 sensor')
    parser.add_argument('--port', default='/dev/ttyAMA1', help='Serial port')
    parser.add_argument('--range', type=float, help='Set detection range in meters (0.5-9)')
    parser.add_argument('--detect-delay', type=float, help='Detection delay in seconds (0.1-25)')
    parser.add_argument('--post-delay', type=float, help='Post-detection delay in seconds (0.5-50)')
    parser.add_argument('--interactive', action='store_true', help='Interactive configuration mode')

    args = parser.parse_args()

    if args.range is not None:
        if 0.5 <= args.range <= 9.0:
            set_range_simple(args.port, args.range)
        else:
            print("Error: Range must be between 0.5 and 9.0 meters")
            sys.exit(1)
    elif args.detect_delay is not None or args.post_delay is not None:
        detect_sec = args.detect_delay if args.detect_delay is not None else 2.5
        post_sec = args.post_delay if args.post_delay is not None else 10.0

        if not (0.1 <= detect_sec <= 25 and 0.5 <= post_sec <= 50):
            print("Error: Detection delay must be 0.1-25s, post-delay must be 0.5-50s")
            sys.exit(1)

        set_timing_simple(args.port, detect_sec, post_sec)
    elif args.interactive:
        interactive_config()
    else:
        print("DFRobot SENS0395 Configuration Tool")
        print("Usage examples:")
        print(f"  {sys.argv[0]} --range 3                        # Set 3-meter range")
        print(f"  {sys.argv[0]} --detect-delay 1.5 --post-delay 5  # Set timing: 1.5s detect, 5s post")
        print(f"  {sys.argv[0]} --interactive                    # Interactive mode")
        print(f"  {sys.argv[0]} --range 5                        # Set 5-meter range")

if __name__ == "__main__":
    main()