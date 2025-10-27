#!/usr/bin/env python3
"""
Check current configuration of DFRobot SENS0395 mmWave sensor
"""

import serial
import time
import json
import os
from datetime import datetime

def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            print(f"⚠️  Config file not found: {config_path}")
            return None
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
        return None

def display_config_range(config):
    """Display range configuration from config file"""
    if not config:
        print("• No config file available")
        return

    range_config = config.get("sensor", {}).get("range_meters", {})

    if not range_config:
        print("• No range configuration found in config file")
        return

    print("--- Configuration File Range Settings ---")
    min_range = range_config.get("min", "Not set")
    max_range = range_config.get("max", "Not set")
    apply_on_startup = range_config.get("apply_on_startup", False)
    last_applied = range_config.get("last_applied", "Never")

    print(f"• Min range: {min_range}m")
    print(f"• Max range: {max_range}m")
    print(f"• Apply on startup: {'✓ Enabled' if apply_on_startup else '✗ Disabled'}")

    if last_applied and last_applied != "Never":
        try:
            applied_time = datetime.fromisoformat(last_applied.replace('Z', '+00:00'))
            time_ago = datetime.now() - applied_time.replace(tzinfo=None)
            print(f"• Last applied: {applied_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_ago.total_seconds():.0f}s ago)")
        except:
            print(f"• Last applied: {last_applied}")
    else:
        print("• Last applied: Never")

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

def check_configuration():
    """Check current sensor configuration"""
    print("Checking sensor configuration...")
    print("=" * 50)

    # Load and display config file settings first
    config = load_config()
    if config:
        display_config_range(config)
    else:
        print("--- Configuration File Range Settings ---")
        print("• No config file available")

    try:
        ser = serial.Serial(
            port="/dev/ttyAMA1",
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )

        # Stop sensor for configuration check
        send_command(ser, "sensorStop")

        # Check firmware version first
        print("\n--- Firmware Information ---")
        send_command(ser, "getVerFW")

        # Note: The sensor doesn't support reading back configuration values
        # These commands are for setting, not reading:
        # detRangeCfg -1 <min> <max>  (sets range)
        # outputLatency -1 <detect> <post>  (sets timing)

        print("\n--- Sensor Hardware Limitations ---")
        print("• Range configuration: Cannot be read back from sensor")
        print("• Timing configuration: Cannot be read back from sensor")
        print("• Sensor uses 15cm increments for range (0-127 = 0-19m max)")
        print("• Sensor uses 25ms increments for timing")
        print("• Sensor stores settings in non-volatile memory")

        # Restart sensor
        send_command(ser, "sensorStart")

        print("\n" + "=" * 50)
        print("Monitoring sensor output for 5 seconds...")

        # Monitor output briefly to verify sensor is working
        readings = 0
        presence_count = 0
        start_time = time.time()

        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if '$JYBSS' in line:
                    readings += 1
                    if ',1,' in line:
                        presence_count += 1
                        print(f"🟢 Presence detected: {line}")
                    elif readings % 5 == 0:  # Show every 5th no-presence reading
                        print(f"⚫ No presence #{readings}: {line}")
            time.sleep(0.1)

        ser.close()

        print(f"\nSensor Status Summary:")
        print(f"• Total readings: {readings}")
        print(f"• Presence detections: {presence_count}")
        print(f"• Sensor is {'✓ WORKING' if readings > 0 else '✗ NOT RESPONDING'}")

        if readings == 0:
            print("\n⚠️  No sensor readings detected. Check:")
            print("   - UART connection to /dev/ttyAMA1")
            print("   - Sensor power supply")
            print("   - Baud rate (should be 115200)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_configuration()