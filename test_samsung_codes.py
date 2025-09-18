#!/usr/bin/env python3

import time
from ir_tv_control import SamsungIRController

# Common Samsung TV IR codes to try
TEST_CODES = {
    'samsung_toggle_1': 0xE0E040BF,
    'samsung_on_1': 0xE0E09966,
    'samsung_off_1': 0xE0E019E6,
    'samsung_toggle_2': 0x0707F40B,
    'samsung_on_2': 0x0707FC03,
    'samsung_off_2': 0x0707F807,
    'nec_power': 0xFF629D,
    'samsung_power_alt': 0xE0E08877,
}

def test_all_codes():
    controller = SamsungIRController()

    print("Testing multiple Samsung IR codes...")
    print("Point the ADA5990 directly at your TV's IR sensor")
    print("Watch for any TV response...")

    for name, code in TEST_CODES.items():
        print(f"\nTesting {name}: 0x{code:08X}")
        controller._send_samsung_code(code)
        print("  -> Sent! Check TV response")
        time.sleep(3)  # Wait 3 seconds between codes

    print("\nTest complete. Did any codes work?")

if __name__ == "__main__":
    test_all_codes()