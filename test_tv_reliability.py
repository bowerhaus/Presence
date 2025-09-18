#!/usr/bin/env python3
"""
Comprehensive TV Control Reliability Testing Framework

This script tests the reliability of both Samsung Network API and CEC control
methods under various scenarios and provides detailed diagnostics.
"""

import json
import logging
import time
import argparse
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from samsung_tv_control import SamsungTVController
import subprocess


@dataclass
class TestResult:
    """Single test operation result"""
    method: str
    operation: str
    success: bool
    duration: float
    error: Optional[str]
    initial_state: Optional[str]
    final_state: Optional[str]
    timestamp: datetime
    additional_info: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'method': self.method,
            'operation': self.operation,
            'success': self.success,
            'duration': self.duration,
            'error': self.error,
            'initial_state': self.initial_state,
            'final_state': self.final_state,
            'timestamp': self.timestamp.isoformat(),
            'additional_info': self.additional_info or {}
        }


@dataclass
class TestSummary:
    """Summary statistics for a test series"""
    total_tests: int
    successes: int
    failures: int
    success_rate: float
    avg_duration: float
    min_duration: float
    max_duration: float
    failure_reasons: Dict[str, int]


class TVReliabilityTester:
    """Comprehensive TV control reliability testing"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.load_config()
        self.setup_logging()
        self.results: List[TestResult] = []
        self.tv_controller = None

        # Initialize TV controller if Samsung network control is enabled
        try:
            self.tv_controller = SamsungTVController(config_path)
            self.logger.info("Samsung TV Controller initialized")
        except Exception as e:
            self.logger.warning(f"Samsung TV Controller not available: {e}")

    def load_config(self):
        """Load configuration"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

        self.cec_config = self.config.get('cec', {})
        self.samsung_config = self.config.get('samsung_tv', {})

    def setup_logging(self):
        """Setup detailed logging"""
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def get_cec_power_state(self) -> Optional[str]:
        """Get power state via CEC"""
        try:
            result = subprocess.run([
                'bash', '-c', 'echo "pow 0" | cec-client -s -d 1'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                output = result.stdout.lower()
                if 'power status: on' in output:
                    return 'on'
                elif 'power status: standby' in output or 'power status: in transition' in output:
                    return 'standby'
                else:
                    return 'unknown'
        except Exception as e:
            self.logger.debug(f"CEC power state check failed: {e}")
        return None

    def cec_power_on(self) -> bool:
        """Send CEC power on command"""
        try:
            result = subprocess.run([
                'bash', '-c', 'echo "on 0" | cec-client -s -d 1'
            ], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def cec_power_off(self) -> bool:
        """Send CEC power off command"""
        try:
            result = subprocess.run([
                'bash', '-c', 'echo "standby 0" | cec-client -s -d 1'
            ], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def test_samsung_network_operation(self, operation: str, retries: int = 3) -> TestResult:
        """Test Samsung network API operation"""
        start_time = time.time()
        initial_state = None
        final_state = None
        error_msg = None
        success = False
        additional_info = {}

        if not self.tv_controller:
            return TestResult(
                method='samsung_network',
                operation=operation,
                success=False,
                duration=0,
                error="TV controller not available",
                initial_state=None,
                final_state=None,
                timestamp=datetime.now()
            )

        try:
            # Get initial state
            initial_state = self.tv_controller._get_actual_power_state()
            additional_info['network_reachable'] = self.tv_controller._is_tv_reachable()

            # Perform operation
            if operation == 'power_on':
                success = self.tv_controller.power_on()
            elif operation == 'power_off':
                success = self.tv_controller.power_off()
            elif operation == 'get_state':
                state = self.tv_controller.get_power_state()
                success = state is not None
                additional_info['state'] = state
            elif operation == 'toggle':
                current_state = self.tv_controller.get_power_state()
                if current_state is not None:
                    if current_state:
                        success = self.tv_controller.power_off()
                    else:
                        success = self.tv_controller.power_on()
                else:
                    success = False
                    error_msg = "Could not determine current state for toggle"
            else:
                success = False
                error_msg = f"Unknown operation: {operation}"

            # Get final state
            time.sleep(2)  # Allow time for state change
            final_state = self.tv_controller._get_actual_power_state()

        except Exception as e:
            error_msg = str(e)
            success = False

        duration = time.time() - start_time

        return TestResult(
            method='samsung_network',
            operation=operation,
            success=success,
            duration=duration,
            error=error_msg,
            initial_state=initial_state,
            final_state=final_state,
            timestamp=datetime.now(),
            additional_info=additional_info
        )

    def test_cec_operation(self, operation: str) -> TestResult:
        """Test CEC operation"""
        start_time = time.time()
        initial_state = self.get_cec_power_state()
        error_msg = None
        success = False
        additional_info = {}

        try:
            if operation == 'power_on':
                success = self.cec_power_on()
            elif operation == 'power_off':
                success = self.cec_power_off()
            elif operation == 'get_state':
                state = self.get_cec_power_state()
                success = state is not None
                additional_info['state'] = state
            else:
                success = False
                error_msg = f"Unknown CEC operation: {operation}"
        except Exception as e:
            error_msg = str(e)
            success = False

        duration = time.time() - start_time
        time.sleep(2)  # Allow time for state change
        final_state = self.get_cec_power_state()

        return TestResult(
            method='cec',
            operation=operation,
            success=success,
            duration=duration,
            error=error_msg,
            initial_state=initial_state,
            final_state=final_state,
            timestamp=datetime.now(),
            additional_info=additional_info
        )

    def run_test_series(self, method: str, operation: str, count: int, delay: float = 10.0) -> List[TestResult]:
        """Run a series of identical tests"""
        results = []

        self.logger.info(f"Running {count} {method} {operation} tests with {delay}s delay between tests")

        for i in range(count):
            self.logger.info(f"Test {i+1}/{count}: {method} {operation}")

            if method == 'samsung_network':
                result = self.test_samsung_network_operation(operation)
            elif method == 'cec':
                result = self.test_cec_operation(operation)
            else:
                self.logger.error(f"Unknown test method: {method}")
                continue

            results.append(result)
            self.results.append(result)

            # Log result
            status = "✓" if result.success else "✗"
            self.logger.info(f"  {status} Duration: {result.duration:.2f}s, "
                           f"States: {result.initial_state} → {result.final_state}")
            if result.error:
                self.logger.warning(f"  Error: {result.error}")

            # Wait between tests (except for last test)
            if i < count - 1:
                self.logger.info(f"  Waiting {delay}s before next test...")
                time.sleep(delay)

        return results

    def calculate_summary(self, results: List[TestResult]) -> TestSummary:
        """Calculate summary statistics"""
        if not results:
            return TestSummary(0, 0, 0, 0.0, 0.0, 0.0, 0.0, {})

        successes = sum(1 for r in results if r.success)
        failures = len(results) - successes
        success_rate = successes / len(results) * 100

        durations = [r.duration for r in results]
        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        # Count failure reasons
        failure_reasons = {}
        for r in results:
            if not r.success and r.error:
                reason = r.error[:50] + "..." if len(r.error) > 50 else r.error
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        return TestSummary(
            total_tests=len(results),
            successes=successes,
            failures=failures,
            success_rate=success_rate,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            failure_reasons=failure_reasons
        )

    def print_summary(self, results: List[TestResult], title: str):
        """Print test summary"""
        summary = self.calculate_summary(results)

        print(f"\n{title}")
        print("=" * len(title))
        print(f"Total Tests: {summary.total_tests}")
        print(f"Successes: {summary.successes}")
        print(f"Failures: {summary.failures}")
        print(f"Success Rate: {summary.success_rate:.1f}%")
        print(f"Duration - Avg: {summary.avg_duration:.2f}s, "
              f"Min: {summary.min_duration:.2f}s, Max: {summary.max_duration:.2f}s")

        if summary.failure_reasons:
            print(f"\nFailure Reasons:")
            for reason, count in sorted(summary.failure_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"  {count}x: {reason}")

    def save_results(self, filename: str):
        """Save results to JSON file"""
        data = {
            'test_session': {
                'timestamp': datetime.now().isoformat(),
                'config_path': self.config_path,
                'total_results': len(self.results)
            },
            'results': [r.to_dict() for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Results saved to {filename}")

    def run_comprehensive_test(self, network_tests: int = 10, cec_tests: int = 10, delay: float = 15.0):
        """Run comprehensive reliability test suite"""
        print("TV Control Reliability Test Suite")
        print("=" * 40)

        all_results = []

        # Test Samsung Network Control
        if self.tv_controller and self.samsung_config.get('enabled', False):
            print(f"\n🌐 Testing Samsung Network Control...")

            # Test power operations
            network_on_results = self.run_test_series('samsung_network', 'power_on', network_tests, delay)
            all_results.extend(network_on_results)
            time.sleep(delay)

            network_off_results = self.run_test_series('samsung_network', 'power_off', network_tests, delay)
            all_results.extend(network_off_results)
            time.sleep(delay)

            # Test state checking
            network_state_results = self.run_test_series('samsung_network', 'get_state', 5, 5.0)
            all_results.extend(network_state_results)

            self.print_summary(network_on_results, "Samsung Network Power ON Results")
            self.print_summary(network_off_results, "Samsung Network Power OFF Results")
            self.print_summary(network_state_results, "Samsung Network State Check Results")
        else:
            print("\n❌ Samsung Network Control disabled or not available")

        # Test CEC Control
        if self.cec_config.get('enabled', False):
            print(f"\n📺 Testing CEC Control...")

            # Test power operations
            cec_on_results = self.run_test_series('cec', 'power_on', cec_tests, delay)
            all_results.extend(cec_on_results)
            time.sleep(delay)

            cec_off_results = self.run_test_series('cec', 'power_off', cec_tests, delay)
            all_results.extend(cec_off_results)
            time.sleep(delay)

            # Test state checking
            cec_state_results = self.run_test_series('cec', 'get_state', 5, 5.0)
            all_results.extend(cec_state_results)

            self.print_summary(cec_on_results, "CEC Power ON Results")
            self.print_summary(cec_off_results, "CEC Power OFF Results")
            self.print_summary(cec_state_results, "CEC State Check Results")
        else:
            print("\n❌ CEC Control disabled or not available")

        # Overall summary
        self.print_summary(all_results, "Overall Test Results")

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tv_reliability_test_{timestamp}.json"
        self.save_results(filename)

        print(f"\nDetailed results saved to: {filename}")

        return all_results


def main():
    parser = argparse.ArgumentParser(description="TV Control Reliability Testing")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--network-tests", type=int, default=10, help="Number of network control tests")
    parser.add_argument("--cec-tests", type=int, default=10, help="Number of CEC control tests")
    parser.add_argument("--delay", type=float, default=15.0, help="Delay between tests (seconds)")
    parser.add_argument("--quick", action="store_true", help="Quick test mode (fewer tests, shorter delays)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.quick:
        args.network_tests = 5
        args.cec_tests = 5
        args.delay = 10.0
        print("Quick test mode enabled (5 tests each, 10s delays)")

    try:
        tester = TVReliabilityTester(args.config)
        results = tester.run_comprehensive_test(args.network_tests, args.cec_tests, args.delay)

        # Final recommendations
        network_results = [r for r in results if r.method == 'samsung_network']
        cec_results = [r for r in results if r.method == 'cec']

        print(f"\n🔍 Recommendations:")

        if network_results:
            network_summary = tester.calculate_summary(network_results)
            print(f"- Samsung Network Control: {network_summary.success_rate:.1f}% success rate")

        if cec_results:
            cec_summary = tester.calculate_summary(cec_results)
            print(f"- CEC Control: {cec_summary.success_rate:.1f}% success rate")

        if network_results and cec_results:
            network_success = tester.calculate_summary(network_results).success_rate
            cec_success = tester.calculate_summary(cec_results).success_rate

            if network_success > cec_success + 10:
                print("→ Recommend using Samsung Network Control as primary method")
            elif cec_success > network_success + 10:
                print("→ Recommend using CEC Control as primary method")
            else:
                print("→ Consider implementing hybrid approach with both methods")

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())