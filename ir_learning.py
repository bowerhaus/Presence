#!/usr/bin/env python3

import lgpio
import time

class IRReceiver:
    """Simple IR receiver for learning remote codes"""

    def __init__(self, chip=0, rx_pin=22):
        self.chip = chip
        self.rx_pin = rx_pin
        self.chip_handle = None

    def start_learning(self, duration=30):
        """Learn IR codes by detecting signal changes"""
        print(f"IR Learning Mode - GPIO {self.rx_pin} for {duration} seconds")
        print("Point your Samsung remote at the IR receiver and press buttons...")

        try:
            self.chip_handle = lgpio.gpiochip_open(self.chip)
            lgpio.gpio_claim_input(self.chip_handle, self.rx_pin)

            start_time = time.time()
            last_state = lgpio.gpio_read(self.chip_handle, self.rx_pin)
            pulse_times = []
            last_change = time.time()

            while (time.time() - start_time) < duration:
                current_state = lgpio.gpio_read(self.chip_handle, self.rx_pin)

                if current_state != last_state:
                    now = time.time()
                    pulse_duration = (now - last_change) * 1000000  # microseconds

                    if pulse_duration > 50:  # Filter out noise
                        pulse_times.append((last_state, int(pulse_duration)))

                    last_state = current_state
                    last_change = now

                time.sleep(0.00001)  # 10us sampling

            # Analyze pulses
            if pulse_times:
                print(f"\nDetected {len(pulse_times)} pulse changes:")
                for i, (state, duration) in enumerate(pulse_times[:20]):  # Show first 20
                    level = "HIGH" if state else "LOW"
                    print(f"  {i+1}: {level} for {duration}μs")

                if len(pulse_times) > 20:
                    print(f"  ... and {len(pulse_times) - 20} more")
            else:
                print("No IR signals detected. Check:")
                print("- Remote is pointed at receiver")
                print("- Remote is working")
                print("- Receiver wiring")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            if self.chip_handle:
                try:
                    lgpio.gpio_free(self.chip_handle, self.rx_pin)
                    lgpio.gpiochip_close(self.chip_handle)
                except:
                    pass

def main():
    receiver = IRReceiver()
    receiver.start_learning()

if __name__ == "__main__":
    main()