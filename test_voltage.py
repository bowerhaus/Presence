#!/usr/bin/env python3

import lgpio
import time

def voltage_test(chip=0, pin=17):
    """Test GPIO voltage output for multimeter measurement"""
    print(f"GPIO voltage test on pin {pin} (chip {chip})")
    print("Use a multimeter to check voltage on GPIO 17 (physical pin 11)")

    try:
        handle = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_output(handle, pin, 0)

        while True:
            command = input("\nEnter 'on', 'off', or 'quit': ").strip().lower()

            if command == 'quit':
                break
            elif command == 'on':
                lgpio.gpio_write(handle, pin, 1)
                print(f"GPIO {pin} set to HIGH (should read ~3.3V)")
            elif command == 'off':
                lgpio.gpio_write(handle, pin, 0)
                print(f"GPIO {pin} set to LOW (should read ~0V)")
            else:
                print("Invalid command")

        lgpio.gpio_free(handle, pin)
        lgpio.gpiochip_close(handle)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    voltage_test()