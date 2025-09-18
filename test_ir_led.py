#!/usr/bin/env python3

import lgpio
import time

def test_ir_led(chip=0, pin=17):
    """Simple test to make IR LED blink visibly"""
    print(f"Testing IR LED on GPIO {pin} (chip {chip})")

    try:
        handle = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_output(handle, pin, 0)

        print("Blinking IR LED for 10 seconds...")
        print("You should see the yellow 'IN' LED blinking on the ADA5990")

        for i in range(20):
            # Turn LED on for 0.25 seconds
            lgpio.gpio_write(handle, pin, 1)
            time.sleep(0.25)

            # Turn LED off for 0.25 seconds
            lgpio.gpio_write(handle, pin, 0)
            time.sleep(0.25)

            print(f"Blink {i+1}/20")

        print("Test complete")

        lgpio.gpio_free(handle, pin)
        lgpio.gpiochip_close(handle)

    except Exception as e:
        print(f"Error: {e}")
        try:
            lgpio.gpiochip_close(handle)
        except:
            pass

if __name__ == "__main__":
    test_ir_led()