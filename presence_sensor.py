#!/usr/bin/env python3

import json
import logging
import time
import threading
import signal
import sys
import argparse
import queue
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

try:
    import lgpio
except ImportError:
    lgpio = None

from enhanced_samsung_controller import EnhancedSamsungTVController
from uart_sensor import UARTSensor


class LEDController:
    """LED controller with PWM dimming support using lgpio"""

    def __init__(self, pin: int):
        self.pin = pin
        self.gpio_handle = None
        self.state = False
        self.brightness = 0  # 0-100%
        self.pwm_frequency = 1000  # 1kHz PWM frequency
        self._setup_gpio()

    def _setup_gpio(self):
        """Initialize GPIO for LED control"""
        if lgpio is not None:
            try:
                self.gpio_handle = lgpio.gpiochip_open(0)
                lgpio.gpio_claim_output(self.gpio_handle, self.pin)
                lgpio.gpio_write(self.gpio_handle, self.pin, 0)  # Start with LED off
            except Exception as e:
                print(f"Failed to setup LED GPIO: {e}")
                self.gpio_handle = None

    def set_brightness(self, percentage: float):
        """Set LED brightness (0-100%)"""
        if self.gpio_handle is not None:
            try:
                percentage = max(0, min(100, percentage))  # Clamp to 0-100%
                self.brightness = percentage

                if percentage == 0:
                    # Use PWM at 0% duty cycle instead of turning off
                    lgpio.tx_pwm(self.gpio_handle, self.pin, self.pwm_frequency, 0)
                    self.state = False
                elif percentage == 100:
                    # Use PWM at 100% duty cycle instead of turning off
                    lgpio.tx_pwm(self.gpio_handle, self.pin, self.pwm_frequency, 100)
                    self.state = True
                else:
                    # Use PWM for intermediate brightness
                    # lgpio tx_pwm expects: frequency, duty_cycle_percent (0-100)
                    lgpio.tx_pwm(self.gpio_handle, self.pin, self.pwm_frequency, percentage)
                    self.state = True

            except Exception as e:
                print(f"Failed to set LED brightness: {e}")

    def on(self, brightness: float = 100):
        """Turn LED on at specified brightness (default 100%)"""
        self.set_brightness(brightness)

    def off(self):
        """Turn LED off"""
        self.set_brightness(0)

    def fade_to(self, target_brightness: float, duration: float = 1.0, steps: int = 50):
        """Fade LED to target brightness over specified duration"""
        if self.gpio_handle is None:
            return

        import threading
        import time

        def fade_thread():
            start_brightness = self.brightness
            step_delay = duration / steps
            brightness_step = (target_brightness - start_brightness) / steps

            for i in range(steps + 1):
                current_brightness = start_brightness + (brightness_step * i)
                self.set_brightness(current_brightness)
                if i < steps:  # Don't sleep after the last step
                    time.sleep(step_delay)

        # Run fade in background thread
        thread = threading.Thread(target=fade_thread, daemon=True)
        thread.start()

    def fade_in(self, duration: float = 1.0, target_brightness: float = 100):
        """Fade LED in from current brightness to target brightness"""
        self.fade_to(target_brightness, duration)

    def fade_out(self, duration: float = 1.0):
        """Fade LED out to off"""
        self.fade_to(0, duration)

    def cleanup(self):
        """Cleanup GPIO resources"""
        if self.gpio_handle is not None:
            try:
                # Turn off LED using PWM at 0%
                lgpio.tx_pwm(self.gpio_handle, self.pin, self.pwm_frequency, 0)
                lgpio.gpio_free(self.gpio_handle, self.pin)
                lgpio.gpiochip_close(self.gpio_handle)
            except:
                pass


class TVCommand(Enum):
    """TV control commands"""
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    CANCEL_OFF_TIMER = "cancel_off_timer"


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

        # TV command queue and worker thread (non-blocking TV control)
        self.tv_command_queue = queue.Queue()
        self.tv_worker_thread = None
        self.tv_worker_running = False

        # Sensor handling variables
        self.uart_sensor = None
        self.gpio_handle = None
        self.use_lgpio = False

        # LED control
        self.led_controller = LEDController(12)
        self.led_brightness = self.config.get("led", {}).get("brightness", 100)
        self.led_fade_duration = self.config.get("led", {}).get("fade_duration", 1.0)
        
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

        # Get logger and clear any existing handlers to prevent duplicates
        logger = logging.getLogger(__name__)
        logger.handlers.clear()
        logger.setLevel(log_level)

        # Set root logger level but don't use basicConfig (prevents duplicate handlers)
        logging.getLogger().setLevel(log_level)

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
        
        # Also configure enhanced samsung controller logger
        tv_logger = logging.getLogger('enhanced_samsung_controller')
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

        # Configure sensor range if specified in config
        self._configure_sensor_range()

        self.logger.info("UART sensor initialized successfully")

    def _configure_sensor_range(self):
        """Configure sensor range if needed based on config settings"""
        range_config = self.config["sensor"].get("range_meters", {})

        # Check if range configuration should be applied
        apply_on_startup = range_config.get("apply_on_startup", False)

        if not apply_on_startup:
            self.logger.debug("Range configuration on startup disabled")
            return

        min_range = range_config.get("min", 0.5)
        max_range = range_config.get("max", 3.0)

        self.logger.info(f"Applying range configuration: {min_range}m to {max_range}m")

        try:
            # Configure the range using the UART sensor's method
            if self.uart_sensor.configure_range(min_range, max_range):
                # Update the last_applied timestamp
                from datetime import datetime
                import json

                # Read current config, update timestamp, write back
                try:
                    with open("config.json", 'r') as f:
                        config_data = json.load(f)

                    config_data["sensor"]["range_meters"]["last_applied"] = datetime.now().isoformat()

                    with open("config.json", 'w') as f:
                        json.dump(config_data, f, indent=2)

                    self.logger.info("Range configuration applied and timestamp updated")
                except Exception as e:
                    self.logger.warning(f"Failed to update config timestamp: {e}")
            else:
                self.logger.error("Failed to configure sensor range")
        except Exception as e:
            self.logger.error(f"Error during range configuration: {e}")

    def _tv_command_worker(self):
        """Worker thread that processes TV commands asynchronously"""
        self.logger.info("TV command worker thread started")

        while self.tv_worker_running:
            try:
                # Wait for command with timeout so we can check running flag
                try:
                    command = self.tv_command_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                self.logger.debug(f"Processing TV command: {command}")

                # Flush serial buffer before TV operation to clear any stale data
                if self.uart_sensor:
                    self.uart_sensor.flush_buffer()
                    self.logger.debug("Flushed serial buffer before TV operation")

                # Process the command
                if command == TVCommand.TURN_ON:
                    self._turn_tv_on_blocking()
                elif command == TVCommand.TURN_OFF:
                    self._turn_tv_off_blocking()
                elif command == TVCommand.CANCEL_OFF_TIMER:
                    self._cancel_tv_off_blocking()

                # Flush serial buffer after TV operation
                if self.uart_sensor:
                    self.uart_sensor.flush_buffer()
                    self.logger.debug("Flushed serial buffer after TV operation")

                # Brief pause to let sensor settle
                time.sleep(0.5)

                # Verify sensor state after TV operation to detect any changes during operation
                if self.uart_sensor:
                    current_sensor_state = self.uart_sensor.get_presence()
                    self.logger.debug(f"Post-TV-operation sensor check: {current_sensor_state}, internal: {self.presence_detected}")

                    # If sensor state differs from our internal state, log warning
                    # (don't auto-correct as this could cause loops - let natural state change handle it)
                    if current_sensor_state != self.presence_detected:
                        self.logger.warning(f"Sensor state mismatch after TV operation: sensor={current_sensor_state}, internal={self.presence_detected}")

                self.tv_command_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error in TV command worker: {e}")
                import traceback
                self.logger.debug(f"Worker traceback: {traceback.format_exc()}")
                time.sleep(1)

        self.logger.info("TV command worker thread stopped")

    def _enqueue_tv_command(self, command: TVCommand):
        """Enqueue a TV command for async processing"""
        try:
            self.tv_command_queue.put(command, block=False)
            self.logger.debug(f"Enqueued TV command: {command}")
        except queue.Full:
            self.logger.error(f"TV command queue full, dropping command: {command}")

    def _on_presence_detected_uart(self):
        """Callback when UART sensor detects presence (NON-BLOCKING)"""
        if not self.presence_detected:
            self.presence_detected = True
            self.last_presence_time = datetime.now()
            self.logger.info("PRESENCE DETECTED")
            self.led_controller.fade_in(self.led_fade_duration, self.led_brightness)
            # Enqueue commands instead of calling directly (non-blocking)
            self._enqueue_tv_command(TVCommand.CANCEL_OFF_TIMER)
            self._enqueue_tv_command(TVCommand.TURN_ON)

    def _on_presence_lost_uart(self):
        """Callback when UART sensor loses presence (NON-BLOCKING)"""
        if self.presence_detected:
            self.presence_detected = False
            self.last_presence_lost_time = datetime.now()
            self.logger.info("PRESENCE LOST")
            self.led_controller.fade_out(self.led_fade_duration)
            # Schedule TV off through timer (already non-blocking)
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
        """Initialize Enhanced Samsung TV controller"""
        try:
            self.tv_controller = EnhancedSamsungTVController()
            self.logger.info("Enhanced Samsung TV controller initialized")
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
    
    def _turn_tv_on_blocking(self):
        """Turn TV on immediately (BLOCKING - should only be called from worker thread)"""
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
    
    def _turn_tv_off_blocking(self):
        """Turn TV off (BLOCKING - should only be called from worker thread)"""
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
        # Schedule enqueue of TURN_OFF command instead of calling method directly
        self.turn_off_timer = threading.Timer(self.turn_off_delay,
                                              lambda: self._enqueue_tv_command(TVCommand.TURN_OFF))
        self.turn_off_timer.start()

    def _cancel_tv_off_blocking(self):
        """Cancel scheduled TV off (BLOCKING - called from worker thread)"""
        if self.turn_off_timer:
            self.turn_off_timer.cancel()
            self.turn_off_timer = None
            self.logger.info("Cancelled scheduled TV off")
    
    def _on_presence_detected(self):
        """Handle presence detection (GPIO mode - NON-BLOCKING)"""
        now = datetime.now()

        if (self.last_presence_time is None or
            (now - self.last_presence_time).total_seconds() > self.debounce_time):

            if not self.presence_detected:
                self.logger.info("PRESENCE DETECTED")
                self.presence_detected = True
                self.led_controller.fade_in(self.led_fade_duration, self.led_brightness)
                # Enqueue commands instead of calling directly (non-blocking)
                self._enqueue_tv_command(TVCommand.CANCEL_OFF_TIMER)
                self._enqueue_tv_command(TVCommand.TURN_ON)

            self.last_presence_time = now

    def _on_presence_lost(self):
        """Handle loss of presence (GPIO mode - NON-BLOCKING)"""
        now = datetime.now()

        if (self.last_presence_lost_time is None or
            (now - self.last_presence_lost_time).total_seconds() > self.debounce_time):

            if self.presence_detected:
                self.logger.info("PRESENCE LOST")
                self.presence_detected = False
                self.led_controller.fade_out(self.led_fade_duration)
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

        # Start TV command worker thread
        self.tv_worker_running = True
        self.tv_worker_thread = threading.Thread(target=self._tv_command_worker, daemon=True, name="TV-Worker")
        self.tv_worker_thread.start()

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

        # Stop TV command worker thread
        self.tv_worker_running = False
        if self.tv_worker_thread and self.tv_worker_thread.is_alive():
            self.logger.info("Waiting for TV command worker to finish...")
            self.tv_worker_thread.join(timeout=5)
            if self.tv_worker_thread.is_alive():
                self.logger.warning("TV command worker did not stop gracefully")

        if self.turn_off_timer:
            self.turn_off_timer.cancel()

        # Cleanup LED controller
        if self.led_controller:
            self.led_controller.cleanup()

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