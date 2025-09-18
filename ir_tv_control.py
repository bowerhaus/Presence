#!/usr/bin/env python3

import json
import logging
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import lgpio
    HAS_LGPIO = True
except ImportError:
    lgpio = None
    HAS_LGPIO = False


class SamsungIRController:
    """Samsung TV IR control using lgpio for CM5 compatibility"""

    # Samsung IR protocol constants (using NEC-like timing)
    CARRIER_FREQ = 38000  # 38kHz carrier frequency
    HEADER_MARK = 9000    # Header mark in microseconds (NEC format)
    HEADER_SPACE = 4500   # Header space in microseconds
    BIT_MARK = 560        # Bit mark in microseconds
    ZERO_SPACE = 560      # Zero bit space in microseconds
    ONE_SPACE = 1690      # One bit space in microseconds

    # Samsung Frame TV IR codes (try both Samsung and NEC format)
    SAMSUNG_CODES = {
        'power_on': 0xE0E09966,
        'power_off': 0xE0E019E6,
        'power_toggle': 0xE0E040BF
    }

    def __init__(self, config_path: str = "config.json", tx_pin: int = 17):
        self.config = self._load_config(config_path)
        self.ir_config = self.config.get("ir_control", {})
        self.tx_pin = tx_pin
        self.chip_handle = None
        self.logger = logging.getLogger(__name__)
        self._carrier_thread = None
        self._stop_carrier = False

        if not self.ir_config.get("enabled", False):
            raise RuntimeError("IR control is disabled in config")

        if not HAS_LGPIO:
            raise RuntimeError("lgpio library not available. Install with: pip install lgpio")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def _connect(self) -> bool:
        """Initialize lgpio connection"""
        if self.chip_handle is not None:
            return True

        try:
            # Open lgpio chip 0 (same as sensor)
            self.chip_handle = lgpio.gpiochip_open(0)

            # Set TX pin as output
            lgpio.gpio_claim_output(self.chip_handle, self.tx_pin, 0)

            self.logger.info(f"IR transmitter initialized on GPIO {self.tx_pin}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize IR transmitter: {e}")
            self.chip_handle = None
            return False

    def _disconnect(self):
        """Clean up lgpio resources"""
        if self.chip_handle is not None:
            try:
                lgpio.gpio_free(self.chip_handle, self.tx_pin)
                lgpio.gpiochip_close(self.chip_handle)
            except:
                pass
            self.chip_handle = None

    def _generate_carrier(self, duration_us: int):
        """Generate 38kHz carrier wave for specified duration"""
        if not self.chip_handle:
            return

        # For Python timing limitations, use lgpio's wave functionality if available
        # Otherwise use a simplified approach for testing
        cycles = int((duration_us * self.CARRIER_FREQ) / 1000000)

        # Simple toggle approach - not perfect 38kHz but should work for testing
        for _ in range(cycles):
            lgpio.gpio_write(self.chip_handle, self.tx_pin, 1)
            lgpio.gpio_write(self.chip_handle, self.tx_pin, 0)

    def _send_mark(self, duration_us: int):
        """Send IR mark (carrier on) for specified duration"""
        if not self.chip_handle:
            return

        # Generate 38kHz pulses for the duration
        end_time = time.time() + (duration_us / 1000000)
        while time.time() < end_time:
            lgpio.gpio_write(self.chip_handle, self.tx_pin, 1)
            time.sleep(0.000013)  # ~13us high
            lgpio.gpio_write(self.chip_handle, self.tx_pin, 0)
            time.sleep(0.000013)  # ~13us low (38kHz = 26us period)

    def _send_space(self, duration_us: int):
        """Send IR space (carrier off) for specified duration"""
        if self.chip_handle:
            lgpio.gpio_write(self.chip_handle, self.tx_pin, 0)
        time.sleep(duration_us / 1000000)  # Convert to seconds

    def _send_samsung_header(self):
        """Send Samsung protocol header"""
        self._send_mark(self.HEADER_MARK)
        self._send_space(self.HEADER_SPACE)

    def _send_samsung_bit(self, bit: int):
        """Send Samsung protocol bit (0 or 1)"""
        self._send_mark(self.BIT_MARK)
        if bit:
            self._send_space(self.ONE_SPACE)
        else:
            self._send_space(self.ZERO_SPACE)

    def _send_samsung_code(self, code: int):
        """Send complete Samsung IR code"""
        if not self._connect():
            return False

        try:
            # Send header
            self._send_samsung_header()

            # Send 32-bit code (MSB first)
            for i in range(32):
                bit = (code >> (31 - i)) & 1
                self._send_samsung_bit(bit)

            # Ensure carrier is off
            self._stop_carrier = True
            if self.chip_handle:
                lgpio.gpio_write(self.chip_handle, self.tx_pin, 0)

            self.logger.debug(f"Sent Samsung IR code: 0x{code:08X}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send IR code: {e}")
            return False

    def power_on(self) -> bool:
        """Turn TV power on using discrete IR code"""
        self.logger.info("Sending Samsung TV power ON command via IR")
        return self._send_samsung_code(self.SAMSUNG_CODES['power_on'])

    def power_off(self) -> bool:
        """Turn TV power off using discrete IR code"""
        self.logger.info("Sending Samsung TV power OFF command via IR")
        return self._send_samsung_code(self.SAMSUNG_CODES['power_off'])

    def power_toggle(self) -> bool:
        """Toggle TV power using standard IR code"""
        self.logger.info("Sending Samsung TV power TOGGLE command via IR")
        return self._send_samsung_code(self.SAMSUNG_CODES['power_toggle'])

    def send_code(self, code_name: str) -> bool:
        """Send IR code by name"""
        if code_name not in self.SAMSUNG_CODES:
            self.logger.error(f"Unknown IR code: {code_name}")
            return False

        return self._send_samsung_code(self.SAMSUNG_CODES[code_name])

    def get_power_state(self) -> Optional[str]:
        """IR cannot detect power state - return None"""
        # IR is transmit-only, cannot detect TV state
        return None

    def __del__(self):
        """Cleanup on destruction"""
        self._disconnect()


def main():
    """Command line interface for IR TV control"""
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python3 ir_tv_control.py <command>")
        print("Commands: on, off, toggle, test")
        return

    try:
        controller = SamsungIRController()
        command = sys.argv[1].lower()

        if command == "on":
            success = controller.power_on()
        elif command == "off":
            success = controller.power_off()
        elif command == "toggle":
            success = controller.power_toggle()
        elif command == "test":
            print("Testing IR transmission...")
            success = controller.power_toggle()
            time.sleep(2)
            success = controller.power_toggle()
        else:
            print(f"Unknown command: {command}")
            return

        if success:
            print(f"IR command '{command}' sent successfully")
        else:
            print(f"Failed to send IR command '{command}'")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()