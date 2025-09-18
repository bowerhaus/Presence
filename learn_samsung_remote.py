#!/usr/bin/env python3

import lgpio
import time
import json

class IRLearner:
    def __init__(self, chip=0, pin=22):
        self.chip = chip
        self.pin = pin
        self.handle = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_input(self.handle, pin, lgpio.SET_PULL_UP)

    def learn_code(self, button_name, timeout=10):
        print(f"\nLearning '{button_name}' button...")
        print("Point Samsung remote at ADA5990 and press the button when ready.")
        input("Press Enter when ready, then immediately press the remote button...")

        pulses = []
        start_time = time.time()
        last_state = 1  # Start high (pulled up)
        last_change = start_time

        # Wait for first signal
        while time.time() - start_time < timeout:
            state = lgpio.gpio_read(self.handle, self.pin)
            if state != last_state:
                break
            time.sleep(0.00001)

        if state == last_state:
            print("No signal detected!")
            return None

        print("Signal detected! Recording...")
        last_change = time.time()

        # Record pulses for 200ms after first change
        end_time = time.time() + 0.2

        while time.time() < end_time:
            state = lgpio.gpio_read(self.handle, self.pin)

            if state != last_state:
                duration = int((time.time() - last_change) * 1000000)  # microseconds
                if duration > 50:  # Filter noise
                    pulses.append(duration)
                last_state = state
                last_change = time.time()

            time.sleep(0.00001)

        print(f"Recorded {len(pulses)} pulses")
        return pulses

    def analyze_pulses(self, pulses):
        if not pulses:
            return

        print(f"\nPulse analysis:")
        print(f"Total pulses: {len(pulses)}")
        print(f"Total duration: {sum(pulses)/1000:.1f}ms")

        # Show first 20 pulses
        print("\nFirst 20 pulses (microseconds):")
        for i, pulse in enumerate(pulses[:20]):
            pulse_type = "MARK" if i % 2 == 0 else "SPACE"
            print(f"  {i+1:2d}: {pulse_type:5s} {pulse:5d}μs")

        if len(pulses) > 20:
            print(f"  ... and {len(pulses) - 20} more")

    def save_codes(self, codes, filename="learned_codes.json"):
        with open(filename, 'w') as f:
            json.dump(codes, f, indent=2)
        print(f"Codes saved to {filename}")

    def cleanup(self):
        lgpio.gpio_free(self.handle, self.pin)
        lgpio.gpiochip_close(self.handle)

def main():
    learner = IRLearner()
    learned_codes = {}

    try:
        buttons = ["power", "power_on", "power_off"]

        for button in buttons:
            pulses = learner.learn_code(button)
            if pulses:
                learned_codes[button] = pulses
                learner.analyze_pulses(pulses)

            cont = input(f"\nLearn another button? (y/n): ")
            if cont.lower() != 'y':
                break

        if learned_codes:
            learner.save_codes(learned_codes)
            print(f"\nLearned {len(learned_codes)} codes!")
        else:
            print("No codes learned.")

    finally:
        learner.cleanup()

if __name__ == "__main__":
    main()