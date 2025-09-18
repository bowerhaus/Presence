#!/usr/bin/env python3

import json
import logging
import time
import threading
import signal
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

try:
    import lgpio
except ImportError:
    lgpio = None

from samsung_tv_control import SamsungTVController
from uart_sensor import UARTSensor


class PresenceSensor:
    """Human presence detection system for Samsung TV control"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        self.sensor_mode = self.config["sensor"].get("mode", "trigger")
        self.turn_off_delay = self.config["tv_control"]["turn_off_delay"]
        
        self.tv_controller = None
        self.presence_detected = False
        self.last_presence_time = None
        self.last_presence_lost_time = None
        self.tv_on = False
        self.running = False
        self.turn_off_timer = None
        
        # Sensor handling variables
        self.uart_sensor = None
        self.gpio_handle = None
        self.use_lgpio = False
        
        self.dev_mode = self.config.get("dev_mode", {})
        self.dry_run = self.dev_mode.get("dry_run", False)
        
        if self.sensor_mode == "uart":
            self._setup_uart_sensor()
        else:
            self.sensor_pin = self.config["sensor"]["trigger"]["gpio_pin"]
            self.debounce_time = self.config["sensor"]["trigger"]["debounce_time"]
            self._setup_gpio()
            
        self._setup_tv_controller()
        self._sync_tv_state()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO").upper())
        
        # Configure root logger to ensure all modules get the same config
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if self.config.get("dev_mode", {}).get("log_to_console", True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            log_file = log_config.get("file_path", "/var/log/presence-sensor.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Also configure samsung_tv_control logger
        tv_logger = logging.getLogger('samsung_tv_control')
        tv_logger.setLevel(log_level)
        
        return logger
    
    def _setup_uart_sensor(self):
        """Initialize UART sensor"""
        uart_config = self.config["sensor"]["uart"]
        self.uart_sensor = UARTSensor(
            port=uart_config["port"],
            baudrate=uart_config["baudrate"],
            timeout=uart_config.get("timeout", 1.0)
        )
        
        # Set up callbacks
        self.uart_sensor.on_presence_detected = self._on_presence_detected_uart
        self.uart_sensor.on_presence_lost = self._on_presence_lost_uart
        
        if not self.uart_sensor.start():
            self.logger.error("Failed to start UART sensor")
            raise RuntimeError("UART sensor initialization failed")
        
        self.logger.info("UART sensor initialized successfully")
    
    def _on_presence_detected_uart(self):
        """Callback when UART sensor detects presence"""
        if not self.presence_detected:
            self.presence_detected = True
            self.last_presence_time = datetime.now()
            self.logger.info("PRESENCE DETECTED")
            self._cancel_tv_off()
            self._turn_tv_on()
    
    def _on_presence_lost_uart(self):
        """Callback when UART sensor loses presence"""
        if self.presence_detected:
            self.presence_detected = False
            self.last_presence_lost_time = datetime.now()
            self.logger.info("PRESENCE LOST")
            self._schedule_tv_off()
    
    def _setup_gpio(self):
        """Initialize GPIO for sensor reading"""
        # Use lgpio (modern library for CM5)
        if lgpio is not None:
            try:
                # Try different GPIO chips
                chip_candidates = [0, 4, 1, 2]
                
                for chip_num in chip_candidates:
                    try:
                        self.gpio_handle = lgpio.gpiochip_open(chip_num)
                        lgpio.gpio_claim_input(self.gpio_handle, self.sensor_pin)
                        
                        # Test read to verify it works
                        test_value = lgpio.gpio_read(self.gpio_handle, self.sensor_pin)
                        self.use_lgpio = True
                        self.logger.info(f"lgpio initialized - sensor on pin {self.sensor_pin} via chip {chip_num} (current: {test_value})")
                        return
                        
                    except Exception as e:
                        if self.gpio_handle is not None:
                            try:
                                lgpio.gpiochip_close(self.gpio_handle)
                            except:
                                pass
                        self.gpio_handle = None
                        continue
                        
            except Exception as e:
                self.logger.error(f"lgpio setup failed: {e}")
        
        # Fallback to RPi.GPIO if available
        if GPIO is not None:
            try:
                gpio_mode = self.config.get("gpio_mode", "BCM")
                if gpio_mode == "BCM":
                    GPIO.setmode(GPIO.BCM)
                else:
                    GPIO.setmode(GPIO.BOARD)
                
                GPIO.setup(self.sensor_pin, GPIO.IN)
                self.use_lgpio = False
                self.logger.info(f"RPi.GPIO initialized - sensor on pin {self.sensor_pin}")
                return
                
            except Exception as e:
                self.logger.warning(f"RPi.GPIO setup failed: {e}")
        
        # No GPIO available - this is an error for production use
        self.logger.error("No GPIO library available - hardware sensor required!")
        sys.exit(1)
    
    def _setup_tv_controller(self):
        """Initialize Samsung TV controller"""
        try:
            self.tv_controller = SamsungTVController()
            self.logger.info("Samsung TV controller initialized")
        except Exception as e:
            self.logger.error(f"TV controller setup failed: {e}")
            sys.exit(1)
    
    def _sync_tv_state(self):
        """Synchronize internal TV state with actual TV state"""
        if self.dry_run:
            self.logger.info("DRY RUN: Skipping TV state sync")
            return
            
        try:
            actual_state = self.tv_controller.get_power_state()
            self.tv_on = actual_state
            self.logger.info(f"TV state synchronized: {self.tv_on}")
            
            # If TV is ON but no presence detected, schedule turn off
            if self.tv_on and not self.presence_detected:
                self.logger.info("TV is ON with no presence detected, scheduling turn off")
                self._schedule_tv_off()
        except Exception as e:
            self.logger.warning(f"Could not sync TV state: {e}")
            # Default to False (off) if we can't determine state
            self.tv_on = False
    
    def _read_sensor(self) -> bool:
        """Read the presence sensor state"""
        # Use lgpio if available
        if self.use_lgpio and self.gpio_handle is not None:
            try:
                raw_value = lgpio.gpio_read(self.gpio_handle, self.sensor_pin)
                # Check if sensor uses inverted logic (LOW = presence detected)
                inverted = self.config.get("sensor", {}).get("inverted_logic", False)
                if inverted:
                    return raw_value == 0
                else:
                    return raw_value == 1
            except Exception as e:
                self.logger.error(f"lgpio read error: {e}")
                return False
        
        # Use RPi.GPIO if available
        if GPIO is not None and not self.use_lgpio:
            try:
                return GPIO.input(self.sensor_pin) == GPIO.HIGH
            except Exception as e:
                self.logger.error(f"RPi.GPIO read error: {e}")
                return False
        
        self.logger.error("No GPIO method available to read sensor!")
        return False
    
    def _turn_tv_on(self):
        """Turn TV on immediately"""
        if self.tv_on:
            self.logger.debug("TV already on")
            return
        
        self.logger.info("Turning TV ON")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would turn TV on")
            self.tv_on = True
            return
        
        try:
            # Use ensure_power_state for more reliable control
            success = self.tv_controller.ensure_power_state(True)
            if success:
                self.tv_on = True
                self.logger.info("TV turned on successfully")
            else:
                self.logger.error("Failed to turn TV on")
        except Exception as e:
            self.logger.error(f"Error turning TV on: {e}")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    def _turn_tv_off(self):
        """Turn TV off after delay"""
        if not self.tv_on:
            self.logger.debug("TV already off")
            return
        
        self.logger.info("Turning TV OFF")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would turn TV off")
            self.tv_on = False
            return
        
        try:
            # Use ensure_power_state for more reliable control
            success = self.tv_controller.ensure_power_state(False)
            if success:
                self.tv_on = False
                self.logger.info("TV turned off successfully")
            else:
                self.logger.error("Failed to turn TV off")
        except Exception as e:
            self.logger.error(f"Error turning TV off: {e}")
    
    def _schedule_tv_off(self):
        """Schedule TV to turn off after delay"""
        if self.turn_off_timer:
            self.turn_off_timer.cancel()
        
        self.logger.info(f"Scheduling TV off in {self.turn_off_delay} seconds")
        self.turn_off_timer = threading.Timer(self.turn_off_delay, self._turn_tv_off)
        self.turn_off_timer.start()
    
    def _cancel_tv_off(self):
        """Cancel scheduled TV off"""
        if self.turn_off_timer:
            self.turn_off_timer.cancel()
            self.turn_off_timer = None
            self.logger.info("Cancelled scheduled TV off")
    
    def _on_presence_detected(self):
        """Handle presence detection"""
        now = datetime.now()
        
        if (self.last_presence_time is None or 
            (now - self.last_presence_time).total_seconds() > self.debounce_time):
            
            if not self.presence_detected:
                self.logger.info("PRESENCE DETECTED")
                self.presence_detected = True
                self._cancel_tv_off()
                self._turn_tv_on()
            
            self.last_presence_time = now
    
    def _on_presence_lost(self):
        """Handle loss of presence"""
        now = datetime.now()
        
        if (self.last_presence_lost_time is None or 
            (now - self.last_presence_lost_time).total_seconds() > self.debounce_time):
            
            if self.presence_detected:
                self.logger.info("PRESENCE LOST")
                self.presence_detected = False
                self._schedule_tv_off()
            
            self.last_presence_lost_time = now
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("Starting presence monitoring...")
        
        if self.sensor_mode == "uart":
            # UART mode uses callbacks, just keep the main thread alive
            while self.running:
                try:
                    if self.dev_mode.get("verbose", False):
                        status = "PRESENT" if self.presence_detected else "ABSENT"
                        self.logger.debug(f"Status: {status}, TV: {'ON' if self.tv_on else 'OFF'}")
                    time.sleep(1)  # 1s status check
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitor loop: {e}")
                    time.sleep(1)
        else:
            # GPIO trigger mode - polling loop
            last_sensor_state = False
            
            while self.running:
                try:
                    current_state = self._read_sensor()
                    
                    if current_state and not last_sensor_state:
                        self._on_presence_detected()
                    elif not current_state and last_sensor_state:
                        self._on_presence_lost()
                    
                    last_sensor_state = current_state
                    
                    if self.dev_mode.get("verbose", False):
                        self.logger.debug(f"Sensor: {current_state}, Presence: {self.presence_detected}, TV: {self.tv_on}")
                    
                    time.sleep(0.1)  # 100ms polling
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitor loop: {e}")
                    time.sleep(1)
    
    def start(self):
        """Start the presence detection system"""
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            self.logger.info("Presence sensor system starting...")
            self._monitor_loop()
        except Exception as e:
            self.logger.error(f"System error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the presence detection system"""
        self.logger.info("Stopping presence sensor system...")
        self.running = False
        
        if self.turn_off_timer:
            self.turn_off_timer.cancel()
        
        # Cleanup sensor resources
        if self.sensor_mode == "uart":
            if self.uart_sensor:
                self.uart_sensor.stop()
        else:
            # Cleanup GPIO resources
            if self.use_lgpio and self.gpio_handle is not None:
                try:
                    lgpio.gpio_free(self.gpio_handle, self.sensor_pin)
                    lgpio.gpiochip_close(self.gpio_handle)
                except:
                    pass
            
            if GPIO is not None and not self.use_lgpio:
                try:
                    GPIO.cleanup()
                except:
                    pass
        
        self.logger.info("System stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}")
        self.running = False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Presence Detection TV Control")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no TV control)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Override config with command line arguments
    if args.dev or args.dry_run or args.verbose:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
            
            if args.dev:
                config["dev_mode"]["enabled"] = True
                config["dev_mode"]["log_to_console"] = True
            
            if args.dry_run:
                config["dev_mode"]["dry_run"] = True
            
            if args.verbose:
                config["dev_mode"]["verbose"] = True
                config["logging"]["level"] = "DEBUG"
            
            # Write temp config
            temp_config = "temp_config.json"
            with open(temp_config, 'w') as f:
                json.dump(config, f, indent=2)
            
            args.config = temp_config
            
        except Exception as e:
            print(f"Error updating config: {e}")
            sys.exit(1)
    
    try:
        sensor = PresenceSensor(args.config)
        sensor.start()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()