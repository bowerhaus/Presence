#!/usr/bin/env python3

import sys
import time
from presence_sensor import LEDController

def test_led_dimming():
    """Test LED dimming functionality"""
    print("Testing LED PWM dimming functionality...")

    # Initialize LED controller on GPIO pin 12 (hardware PWM)
    led = LEDController(12)

    try:
        print("Testing basic brightness levels...")

        # Test different brightness levels
        brightness_levels = [0, 25, 50, 75, 100]

        for brightness in brightness_levels:
            print(f"Setting brightness to {brightness}%")
            led.set_brightness(brightness)
            time.sleep(2)

        print("\nTesting fade effects...")

        # Test fade in
        print("Fading in to 100% over 2 seconds")
        led.set_brightness(0)
        led.fade_in(duration=2.0, target_brightness=100)
        time.sleep(3)

        # Test fade out
        print("Fading out to 0% over 2 seconds")
        led.fade_out(duration=2.0)
        time.sleep(3)

        # Test fade to specific brightness
        print("Fading to 30% over 1 second")
        led.fade_to(30, duration=1.0)
        time.sleep(2)

        # Test on() with specific brightness
        print("Turning on at 60% brightness")
        led.on(60)
        time.sleep(2)

        print("Test completed successfully!")

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        print("Cleaning up...")
        led.cleanup()

if __name__ == "__main__":
    test_led_dimming()