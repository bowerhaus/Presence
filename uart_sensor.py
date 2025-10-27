#!/usr/bin/env python3
"""
UART-based sensor module for DFRobot SENS0395 mmWave sensor
Reads presence data via serial communication in $JYBSS format
"""

import serial
import threading
import time
import logging
from datetime import datetime


class UARTSensor:
    """UART-based presence sensor handler"""
    
    def __init__(self, port="/dev/ttyAMA1", baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        self.serial_conn = None
        self.presence_detected = False
        self.last_update = None
        self.running = False
        self.read_thread = None
        
        # Callbacks
        self.on_presence_detected = None
        self.on_presence_lost = None

    def meters_to_increments(self, meters):
        """Convert meters to 15cm increments (sensor native units)"""
        return round(meters / 0.15)

    def increments_to_meters(self, increments):
        """Convert 15cm increments back to meters"""
        return increments * 0.15

    def send_command(self, command, wait_time=1.0):
        """Send a command to the sensor and wait for response"""
        if not self.serial_conn:
            self.logger.error("No serial connection for sending command")
            return False, ""

        try:
            self.logger.debug(f"Sending command: {command}")
            self.serial_conn.write((command + '\r\n').encode('utf-8'))
            time.sleep(wait_time)

            # Read response
            response = ""
            while self.serial_conn.in_waiting > 0:
                response += self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')

            if response:
                self.logger.debug(f"Command response: {response.strip()}")
            return True, response.strip()
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return False, str(e)

    def flush_buffer(self):
        """Flush serial input buffer to discard stale data"""
        if not self.serial_conn:
            return

        try:
            if self.serial_conn.in_waiting > 0:
                bytes_discarded = self.serial_conn.in_waiting
                self.serial_conn.reset_input_buffer()
                self.logger.debug(f"Flushed {bytes_discarded} bytes from serial buffer")
        except Exception as e:
            self.logger.warning(f"Failed to flush serial buffer: {e}")

    def configure_range(self, min_meters=0.5, max_meters=3.0):
        """Configure detection range using proper 15cm increments"""

        # Convert meters to 15cm increments
        min_increments = self.meters_to_increments(min_meters)
        max_increments = self.meters_to_increments(max_meters)

        # Validate range (sensor supports 0-127 increments = 0-19.05m)
        if min_increments < 0 or max_increments > 127:
            max_supported = self.increments_to_meters(127)
            self.logger.error(f"Range out of bounds. Max supported range is {max_supported:.1f}m")
            return False

        self.logger.info(f"Configuring range: {min_meters}m to {max_meters}m ({min_increments} to {max_increments} increments)")

        try:
            # Stop sensor for configuration
            success, response = self.send_command("sensorStop")
            if not success:
                return False

            # Set detection range using proper increment values
            range_cmd = f"detRangeCfg -1 {min_increments} {max_increments}"
            success, response = self.send_command(range_cmd)
            if not success:
                return False

            # Save configuration
            save_cmd = "saveCfg 0x45670123 0xCDEF89AB 0x956128C6 0xDF54AC89"
            success, response = self.send_command(save_cmd)
            if not success:
                return False

            # Restart sensor
            success, response = self.send_command("sensorStart")
            if not success:
                return False

            self.logger.info(f"Range configured successfully: {min_meters}m to {max_meters}m")
            return True

        except Exception as e:
            self.logger.error(f"Error configuring range: {e}")
            return False

    def connect(self):
        """Initialize serial connection"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            self.logger.info(f"Connected to sensor on {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            self.logger.error(f"Failed to connect to sensor: {e}")
            return False
    
    def start(self):
        """Start monitoring sensor data"""
        if not self.serial_conn:
            if not self.connect():
                return False

        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()

        # Wait briefly for initial sensor data to sync state
        self._sync_initial_state()

        self.logger.info("Started sensor monitoring")
        return True

    def _sync_initial_state(self):
        """Wait for initial sensor reading to sync internal state with hardware"""
        self.logger.debug("Syncing initial sensor state...")

        # Wait up to 3 seconds for first sensor reading
        sync_timeout = 3.0
        start_time = time.time()

        while (time.time() - start_time) < sync_timeout and self.running:
            if self.last_update is not None:
                # We got our first reading, state is now synced
                initial_state = "PRESENT" if self.presence_detected else "ABSENT"
                self.logger.info(f"Initial sensor state synced: {initial_state}")
                return
            time.sleep(0.1)

        # Timeout - assume no presence if no data received
        if self.last_update is None:
            self.logger.warning("No initial sensor data received - assuming no presence")
            self.presence_detected = False

    def stop(self):
        """Stop monitoring sensor data"""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
        
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
        
        self.logger.info("Stopped sensor monitoring")
    
    def _read_loop(self):
        """Main loop for reading sensor data"""
        consecutive_errors = 0
        max_errors = 5
        
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    
                    if line.startswith('$JYBSS'):
                        self._parse_sensor_data(line)
                        consecutive_errors = 0
                    
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except (serial.SerialException, UnicodeDecodeError) as e:
                consecutive_errors += 1
                self.logger.warning(f"Read error ({consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    self.logger.error("Too many consecutive errors, attempting reconnection")
                    self._reconnect()
                    consecutive_errors = 0
                
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Unexpected error in read loop: {e}")
                time.sleep(1)
    
    def _parse_sensor_data(self, line):
        """Parse sensor data line in $JYBSS format"""
        try:
            # Format: $JYBSS,1, , , * (1=presence, 0=no presence)
            parts = line.split(',')
            if len(parts) >= 2:
                presence_value = parts[1].strip()
                new_presence = (presence_value == '1')

                # Update timestamp
                self.last_update = datetime.now()

                # First reading - establish initial state without triggering callbacks
                if not hasattr(self, '_first_reading_done'):
                    self._first_reading_done = True
                    self.presence_detected = new_presence
                    self.logger.debug(f"First sensor reading: {'PRESENT' if new_presence else 'ABSENT'}")
                    # Don't trigger callbacks on first reading, just establish state
                    return

                # Check for state change (only after first reading)
                if new_presence != self.presence_detected:
                    old_state = self.presence_detected
                    self.presence_detected = new_presence

                    self.logger.debug(f"State change: {old_state} -> {new_presence}")

                    if new_presence:
                        self.logger.info("Presence detected")
                        if self.on_presence_detected:
                            self.on_presence_detected()
                    else:
                        self.logger.info("Presence lost")
                        if self.on_presence_lost:
                            self.on_presence_lost()

        except Exception as e:
            self.logger.warning(f"Failed to parse sensor data '{line}': {e}")
    
    def _reconnect(self):
        """Attempt to reconnect to the sensor"""
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None

        # Reset first reading flag on reconnection to re-establish state
        if hasattr(self, '_first_reading_done'):
            delattr(self, '_first_reading_done')

        time.sleep(1)
        self.connect()
    
    def get_presence(self):
        """Get current presence status"""
        return self.presence_detected
    
    def is_connected(self):
        """Check if sensor is connected and receiving data"""
        if not self.serial_conn or not self.last_update:
            return False
        
        # Consider disconnected if no update for 5 seconds
        time_since_update = (datetime.now() - self.last_update).total_seconds()
        return time_since_update < 5


if __name__ == "__main__":
    # Test the sensor module
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    sensor = UARTSensor()
    
    # Set up callbacks
    sensor.on_presence_detected = lambda: print(">>> PRESENCE DETECTED!")
    sensor.on_presence_lost = lambda: print(">>> PRESENCE LOST!")
    
    print("Starting UART sensor test (Press Ctrl+C to stop)...")
    
    if not sensor.start():
        print("Failed to start sensor")
        sys.exit(1)
    
    try:
        last_status = None
        while True:
            time.sleep(0.5)
            if sensor.is_connected():
                status = "PRESENT" if sensor.get_presence() else "ABSENT"
                if status != last_status:
                    print(f"\n*** Status changed to: {status} ***")
                    last_status = status
                print(f"\rStatus: {status} | Connected: Yes | Last update: {sensor.last_update}", end="", flush=True)
            else:
                print("\rSensor disconnected or no data", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\nStopping sensor...")
    finally:
        sensor.stop()