#!/usr/bin/env python3

import lgpio
import time

def test_ir_receiver():
    """Simple test to see what the IR receiver is doing"""
    print("IR Receiver Test")
    print("Point Samsung remote directly at ADA5990 and press power button")

    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_input(chip, 22, lgpio.SET_PULL_UP)

    print("Monitoring IR receiver for 10 seconds...")
    print("State changes will be shown:")

    last_state = lgpio.gpio_read(chip, 22)
    print(f"Initial state: {last_state}")

    changes = []
    start_time = time.time()

    while time.time() - start_time < 10:
        current_state = lgpio.gpio_read(chip, 22)

        if current_state != last_state:
            timestamp = time.time() - start_time
            changes.append((timestamp, current_state))
            print(f"{timestamp:.3f}s: {last_state} -> {current_state}")
            last_state = current_state

        time.sleep(0.0001)  # 100us polling

    print(f"\nTest complete. Detected {len(changes)} changes.")

    if changes:
        print("Time between changes:")
        for i in range(1, min(10, len(changes))):
            duration = (changes[i][0] - changes[i-1][0]) * 1000
            print(f"  Change {i}: {duration:.1f}ms")
    else:
        print("No changes detected - try pressing remote button")

    lgpio.gpio_free(chip, 22)
    lgpio.gpiochip_close(chip)

if __name__ == "__main__":
    test_ir_receiver()