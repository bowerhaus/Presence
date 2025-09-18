#!/usr/bin/env python3
"""
Enhanced TV Power ON Script

Simple script to turn TV on using the enhanced Samsung controller
with improved reliability and error handling.
"""

import sys
import logging
import time
from datetime import datetime
from enhanced_samsung_controller import EnhancedSamsungTVController


def main():
    """Turn TV on with detailed feedback"""

    # Setup logging for user feedback
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    print(f"📺 TV Power ON - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 40)

    try:
        # Create enhanced controller
        print("🔌 Initializing enhanced TV controller...")
        controller = EnhancedSamsungTVController()

        # Check current state
        print("📊 Checking current TV state...")
        start_time = time.time()
        current_state = controller.get_power_state()
        check_duration = time.time() - start_time

        if current_state is None:
            print("❌ Error: Could not determine TV state")
            return 1
        elif current_state:
            print(f"✓ TV is already ON ({check_duration:.2f}s)")
            return 0
        else:
            print(f"📍 TV is currently OFF ({check_duration:.2f}s)")

        # Turn TV on
        print("🟢 Turning TV ON...")
        start_time = time.time()
        success = controller.power_on()
        power_duration = time.time() - start_time

        if success:
            print(f"✅ TV successfully turned ON ({power_duration:.2f}s)")

            # Verify final state
            print("🔍 Verifying TV is ON...")
            time.sleep(2)
            final_state = controller.get_power_state()

            if final_state:
                print("✓ Confirmed: TV is ON")
            else:
                print("⚠️  Warning: TV may not be fully on yet")

        else:
            print(f"❌ Failed to turn TV ON ({power_duration:.2f}s)")
            return 1

        # Show connection stats
        stats = controller.get_connection_stats()
        print(f"\n📈 Connection Stats:")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        print(f"   Total Attempts: {stats['total_attempts']}")
        if stats['ssl_errors'] > 0:
            print(f"   SSL Errors: {stats['ssl_errors']}")

        return 0

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())