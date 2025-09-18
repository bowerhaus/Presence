#!/usr/bin/env python3

import time
from samsung_tv_control import SamsungTVController
from test_raw_ir import RawIRTransmitter

def test_ir_response():
    """Test if IR commands cause any TV response"""
    print("TV + IR Response Test")

    # Check initial TV state
    tv = SamsungTVController()
    ir = RawIRTransmitter()

    try:
        initial_state = tv.get_power_state()
        print(f"Initial TV state: {initial_state}")

        # Test different IR patterns
        test_codes = [
            0xE0E040BF,  # Samsung toggle
            0xE0E09966,  # Samsung on
            0xE0E019E6,  # Samsung off
            0x0707F40B,  # Alternative Samsung
            0xFF629D,    # NEC power
        ]

        for i, code in enumerate(test_codes):
            print(f"\nTest {i+1}: Sending 0x{code:08X}")

            # Send NEC format
            ir.send_nec_code(code)
            time.sleep(2)

            # Check TV state
            new_state = tv.get_power_state()
            if new_state != initial_state:
                print(f"SUCCESS! TV state changed: {initial_state} -> {new_state}")
                print(f"Working code: 0x{code:08X}")
                break
            else:
                print("No change detected")

            time.sleep(1)

        print("\nTest complete")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        ir.cleanup()

if __name__ == "__main__":
    test_ir_response()