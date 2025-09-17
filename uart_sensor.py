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
        self.logger.info("Started sensor monitoring")
        return True
    
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
                
                # Check for state change
                if new_presence != self.presence_detected:
                    self.presence_detected = new_presence
                    
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