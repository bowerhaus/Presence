#!/usr/bin/env python3
"""
Test Enhanced Samsung Controller Reliability

Compare the enhanced controller against the original to measure improvements
in reliability and connection handling.
"""

import json
import logging
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
from enhanced_samsung_controller import EnhancedSamsungTVController


class EnhancedReliabilityTest:
    """Test enhanced Samsung controller reliability"""

    def __init__(self, config_path: str = "config.json"):
        self.controller = EnhancedSamsungTVController(config_path)
        self.logger = logging.getLogger(__name__)
        self.results = []

    def test_power_cycle_enhanced(self, cycle_num: int) -> Dict[str, Any]:
        """Test a complete power cycle with enhanced controller"""
        print(f"\n🔄 Enhanced Cycle {cycle_num}: Testing power on/off...")

        result = {
            'cycle': cycle_num,
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }

        # Step 1: Get initial state
        print("  📊 Getting initial state...")
        start_time = time.time()
        try:
            initial_state = self.controller.get_power_state()
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'get_initial_state',
                'success': initial_state is not None,
                'duration': duration,
                'result': initial_state,
                'error': None
            })
            print(f"     Initial state: {'ON' if initial_state else 'OFF'} ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'get_initial_state',
                'success': False,
                'duration': duration,
                'result': None,
                'error': str(e)
            })
            print(f"     ❌ Failed to get initial state: {e}")
            return result

        # Step 2: Turn OFF (if not already off)
        if initial_state:
            print("  🔴 Turning OFF...")
            start_time = time.time()
            try:
                success = self.controller.power_off()
                duration = time.time() - start_time
                result['steps'].append({
                    'action': 'power_off',
                    'success': success,
                    'duration': duration,
                    'result': success,
                    'error': None
                })
                status = "✓" if success else "❌"
                print(f"     {status} Power OFF: {success} ({duration:.2f}s)")
            except Exception as e:
                duration = time.time() - start_time
                result['steps'].append({
                    'action': 'power_off',
                    'success': False,
                    'duration': duration,
                    'result': False,
                    'error': str(e)
                })
                print(f"     ❌ Power OFF failed: {e}")
        else:
            print("  🔴 Already OFF, skipping power off")

        # Step 3: Wait and verify OFF state
        print("  ⏳ Waiting 3s and verifying OFF state...")
        time.sleep(3)
        start_time = time.time()
        try:
            off_state = self.controller.get_power_state()
            duration = time.time() - start_time
            is_off = not off_state
            result['steps'].append({
                'action': 'verify_off',
                'success': off_state is not None,
                'duration': duration,
                'result': off_state,
                'error': None
            })
            status = "✓" if is_off else "⚠️"
            print(f"     {status} Verify OFF: {is_off} ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'verify_off',
                'success': False,
                'duration': duration,
                'result': None,
                'error': str(e)
            })
            print(f"     ❌ Verify OFF failed: {e}")

        # Step 4: Turn ON
        print("  🟢 Turning ON...")
        start_time = time.time()
        try:
            success = self.controller.power_on()
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'power_on',
                'success': success,
                'duration': duration,
                'result': success,
                'error': None
            })
            status = "✓" if success else "❌"
            print(f"     {status} Power ON: {success} ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'power_on',
                'success': False,
                'duration': duration,
                'result': False,
                'error': str(e)
            })
            print(f"     ❌ Power ON failed: {e}")

        # Step 5: Wait and verify ON state
        print("  ⏳ Waiting 3s and verifying ON state...")
        time.sleep(3)
        start_time = time.time()
        try:
            on_state = self.controller.get_power_state()
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'verify_on',
                'success': on_state is not None,
                'duration': duration,
                'result': on_state,
                'error': None
            })
            status = "✓" if on_state else "⚠️"
            print(f"     {status} Verify ON: {on_state} ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start_time
            result['steps'].append({
                'action': 'verify_on',
                'success': False,
                'duration': duration,
                'result': None,
                'error': str(e)
            })
            print(f"     ❌ Verify ON failed: {e}")

        # Get connection stats
        stats = self.controller.get_connection_stats()
        result['connection_stats'] = stats

        # Calculate cycle success
        successful_steps = sum(1 for step in result['steps'] if step['success'])
        total_steps = len(result['steps'])
        cycle_success = successful_steps == total_steps

        result['cycle_success'] = cycle_success
        result['successful_steps'] = successful_steps
        result['total_steps'] = total_steps

        status = "✅ SUCCESS" if cycle_success else "❌ FAILED"
        print(f"     {status} ({successful_steps}/{total_steps} steps)")
        print(f"     📊 Connection Success Rate: {stats['success_rate']:.1f}%, SSL Errors: {stats['ssl_errors']}")

        return result

    def run_enhanced_reliability_test(self, cycles: int = 5, delay: float = 8.0):
        """Run multiple power cycles to test enhanced reliability"""
        print(f"🧪 Enhanced Samsung Controller Reliability Test")
        print(f"{'='*60}")
        print(f"Testing {cycles} power cycles with {delay}s delay between cycles")

        for cycle in range(1, cycles + 1):
            result = self.test_power_cycle_enhanced(cycle)
            self.results.append(result)

            # Wait between cycles (except last one)
            if cycle < cycles:
                print(f"  ⏰ Waiting {delay}s before next cycle...")
                time.sleep(delay)

        # Print summary
        self.print_summary()
        self.save_results()

    def print_summary(self):
        """Print test summary"""
        if not self.results:
            return

        total_cycles = len(self.results)
        successful_cycles = sum(1 for r in self.results if r['cycle_success'])
        success_rate = (successful_cycles / total_cycles) * 100

        print(f"\n📊 Enhanced Controller Test Summary")
        print(f"{'='*40}")
        print(f"Total Cycles: {total_cycles}")
        print(f"Successful Cycles: {successful_cycles}")
        print(f"Success Rate: {success_rate:.1f}%")

        # Connection stats evolution
        if self.results:
            final_stats = self.results[-1]['connection_stats']
            print(f"\n📈 Final Connection Statistics:")
            print(f"  Overall Success Rate: {final_stats['success_rate']:.1f}%")
            print(f"  Total Connection Attempts: {final_stats['total_attempts']}")
            print(f"  SSL Errors: {final_stats['ssl_errors']}")
            print(f"  Consecutive Failures: {final_stats['consecutive_failures']}")
            print(f"  Connection Health: {'DEGRADED' if final_stats['is_degraded'] else 'HEALTHY'}")

        # Step-by-step analysis
        step_stats = {}
        for result in self.results:
            for step in result['steps']:
                action = step['action']
                if action not in step_stats:
                    step_stats[action] = {'total': 0, 'successful': 0, 'durations': []}

                step_stats[action]['total'] += 1
                if step['success']:
                    step_stats[action]['successful'] += 1
                if step['duration']:
                    step_stats[action]['durations'].append(step['duration'])

        print(f"\n📋 Step Analysis:")
        for action, stats in step_stats.items():
            success_rate = (stats['successful'] / stats['total']) * 100
            avg_duration = sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0
            print(f"  {action:15}: {stats['successful']:2}/{stats['total']:2} ({success_rate:5.1f}%) - Avg: {avg_duration:.2f}s")

        # Failed cycles details
        failed_cycles = [r for r in self.results if not r['cycle_success']]
        if failed_cycles:
            print(f"\n❌ Failed Cycles Details:")
            for cycle in failed_cycles:
                failed_steps = [s for s in cycle['steps'] if not s['success']]
                print(f"  Cycle {cycle['cycle']}: {len(failed_steps)} failed steps")
                for step in failed_steps:
                    print(f"    - {step['action']}: {step['error']}")

        # Performance comparison hint
        print(f"\n💡 Compare with previous network_reliability_test results to see improvements")

    def save_results(self):
        """Save detailed results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_reliability_test_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump({
                'test_info': {
                    'timestamp': datetime.now().isoformat(),
                    'total_cycles': len(self.results),
                    'controller_type': 'enhanced',
                    'config_path': 'config.json'
                },
                'results': self.results
            }, f, indent=2)

        print(f"📄 Enhanced test results saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Enhanced Samsung Controller Reliability Test")
    parser.add_argument("--cycles", type=int, default=5, help="Number of power cycles to test")
    parser.add_argument("--delay", type=float, default=8.0, help="Delay between cycles in seconds")
    parser.add_argument("--quick", action="store_true", help="Quick test (3 cycles, 5s delay)")
    parser.add_argument("--stress", action="store_true", help="Stress test (10 cycles, 5s delay)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.quick:
        args.cycles = 3
        args.delay = 5.0
        print("🚀 Quick test mode: 3 cycles, 5s delay")
    elif args.stress:
        args.cycles = 10
        args.delay = 5.0
        print("🔥 Stress test mode: 10 cycles, 5s delay")

    try:
        tester = EnhancedReliabilityTest()
        tester.run_enhanced_reliability_test(args.cycles, args.delay)
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())