#!/usr/bin/env python3

import lgpio
import time

class RawIRTransmitter:
    def __init__(self, chip=0, pin=17):
        self.chip = chip
        self.pin = pin
        self.handle = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_output(self.handle, pin, 0)

    def pulse_microseconds(self, us):
        """Send a pulse (38kHz carrier) for given microseconds"""
        cycles = int(us * 38)  # 38 cycles per 1000us for 38kHz
        for _ in range(cycles):
            lgpio.gpio_write(self.handle, self.pin, 1)
            lgpio.gpio_write(self.handle, self.pin, 0)

    def space_microseconds(self, us):
        """Send space (no carrier) for given microseconds"""
        lgpio.gpio_write(self.handle, self.pin, 0)
        time.sleep(us / 1000000.0)

    def send_nec_code(self, code):
        """Send code in NEC format"""
        print(f"Sending NEC code: 0x{code:08X}")

        # NEC header
        self.pulse_microseconds(9000)
        self.space_microseconds(4500)

        # Send 32 bits
        for i in range(32):
            bit = (code >> (31-i)) & 1
            self.pulse_microseconds(560)  # Mark
            if bit:
                self.space_microseconds(1690)  # 1 bit
            else:
                self.space_microseconds(560)   # 0 bit

        # Stop bit
        self.pulse_microseconds(560)
        self.space_microseconds(1000)

    def send_samsung_code(self, code):
        """Send code in Samsung format"""
        print(f"Sending Samsung code: 0x{code:08X}")

        # Samsung header (different from NEC)
        self.pulse_microseconds(4500)
        self.space_microseconds(4500)

        # Send 32 bits
        for i in range(32):
            bit = (code >> (31-i)) & 1
            self.pulse_microseconds(560)
            if bit:
                self.space_microseconds(1690)
            else:
                self.space_microseconds(560)

        # Stop
        self.pulse_microseconds(560)

    def send_raw_pattern(self, pattern):
        """Send raw on/off pattern in microseconds"""
        print(f"Sending raw pattern: {len(pattern)} pulses")
        for i, duration in enumerate(pattern):
            if i % 2 == 0:  # Even = mark (on)
                self.pulse_microseconds(duration)
            else:  # Odd = space (off)
                self.space_microseconds(duration)

    def cleanup(self):
        lgpio.gpio_free(self.handle, self.pin)
        lgpio.gpiochip_close(self.handle)

def test_protocols():
    transmitter = RawIRTransmitter()

    # Test Samsung codes with multiple protocols
    samsung_power = 0xE0E040BF

    print("Testing IR with different protocols...")
    print("Point ADA5990 directly at TV, very close (1 foot)")

    try:
        # Test 1: NEC protocol
        print("\n1. Testing NEC protocol format:")
        transmitter.send_nec_code(samsung_power)
        time.sleep(2)

        # Test 2: Samsung protocol
        print("\n2. Testing Samsung protocol format:")
        transmitter.send_samsung_code(samsung_power)
        time.sleep(2)

        # Test 3: Raw pattern (known working Samsung remote pattern)
        print("\n3. Testing raw Samsung power pattern:")
        # This is a captured Samsung power button pattern
        raw_samsung = [
            4500, 4500,  # Header
            560, 1690,   # 1
            560, 1690,   # 1
            560, 1690,   # 1
            560, 560,    # 0
            560, 560,    # 0
            560, 560,    # 0
            560, 560,    # 0
            560, 560,    # 0
            # Continue for all 32 bits...
            560, 1690,   # 1
            560, 560,    # 0
            560
        ]
        transmitter.send_raw_pattern(raw_samsung)
        time.sleep(2)

        # Test 4: Very simple test - just blast IR
        print("\n4. Testing simple IR blast:")
        for _ in range(100):
            transmitter.pulse_microseconds(1000)
            transmitter.space_microseconds(1000)

    finally:
        transmitter.cleanup()

    print("\nTest complete. Did any work?")

if __name__ == "__main__":
    test_protocols()