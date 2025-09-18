#!/usr/bin/env python3
"""
Continuous TV State Monitoring Tool

This script continuously monitors TV state using multiple methods and logs
state changes, network availability, and response times to help identify
patterns in TV behavior and control reliability.
"""

import json
import logging
import time
import argparse
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import socket

from samsung_tv_control import SamsungTVController


@dataclass
class StateSnapshot:
    """Single TV state snapshot"""
    timestamp: datetime
    network_reachable: bool
    network_response_time: Optional[float]
    samsung_api_state: Optional[str]
    samsung_api_response_time: Optional[float]
    samsung_api_error: Optional[str]
    cec_state: Optional[str]
    cec_response_time: Optional[float]
    cec_error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def get_consensus_state(self) -> Optional[str]:
        """Get consensus TV state from available methods"""
        states = []

        if self.samsung_api_state:
            states.append('on' if self.samsung_api_state.lower() == 'on' else 'off')

        if self.cec_state:
            states.append('on' if self.cec_state.lower() == 'on' else 'off')

        # Network reachability as a fallback indicator
        if not states and self.network_reachable:
            states.append('standby')
        elif not states and not self.network_reachable:
            states.append('off')

        # Return most common state, or None if no consensus
        if not states:
            return None

        # Simple majority vote
        on_count = states.count('on')
        off_count = states.count('off') + states.count('standby')

        if on_count > off_count:
            return 'on'
        elif off_count > on_count:
            return 'off'
        else:
            return 'unknown'


class TVStateMonitor:
    """Continuous TV state monitoring system"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.load_config()
        self.setup_logging()
        self.snapshots: List[StateSnapshot] = []
        self.tv_controller = None
        self.running = False
        self.last_consensus_state = None
        self.state_changes = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Initialize TV controller if available
        try:
            self.tv_controller = SamsungTVController(config_path)
            self.logger.info("Samsung TV Controller initialized")
        except Exception as e:
            self.logger.warning(f"Samsung TV Controller not available: {e}")

    def load_config(self):
        """Load configuration"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

        self.samsung_config = self.config.get('samsung_tv', {})
        self.cec_config = self.config.get('cec', {})

    def setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger(__name__)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler for detailed logging
        file_handler = logging.FileHandler('tv_monitor.log')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        self.logger.setLevel(logging.INFO)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def check_network_reachability(self) -> tuple[bool, Optional[float]]:
        """Check if TV is reachable on network and measure response time"""
        if not self.samsung_config.get('ip_address'):
            return False, None

        try:
            ip = self.samsung_config['ip_address']
            port = self.samsung_config.get('port', 8002)

            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip, port))
            response_time = time.time() - start_time
            sock.close()

            return result == 0, response_time

        except Exception as e:
            self.logger.debug(f"Network check failed: {e}")
            return False, None

    def check_samsung_api_state(self) -> tuple[Optional[str], Optional[float], Optional[str]]:
        """Check TV state via Samsung API"""
        if not self.tv_controller:
            return None, None, "Controller not available"

        try:
            start_time = time.time()
            state = self.tv_controller._get_actual_power_state()
            response_time = time.time() - start_time
            return state, response_time, None
        except Exception as e:
            response_time = time.time() - start_time if 'start_time' in locals() else 0
            return None, response_time, str(e)

    def check_cec_state(self) -> tuple[Optional[str], Optional[float], Optional[str]]:
        """Check TV state via CEC"""
        if not self.cec_config.get('enabled', False):
            return None, None, "CEC disabled"

        try:
            start_time = time.time()
            result = subprocess.run([
                'bash', '-c', 'echo "pow 0" | cec-client -s -d 1'
            ], capture_output=True, text=True, timeout=8)
            response_time = time.time() - start_time

            if result.returncode == 0:
                output = result.stdout.lower()
                if 'power status: on' in output:
                    return 'on', response_time, None
                elif 'power status: standby' in output:
                    return 'standby', response_time, None
                elif 'power status: in transition' in output:
                    return 'transition', response_time, None
                else:
                    return 'unknown', response_time, None
            else:
                return None, response_time, f"CEC command failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return None, 8.0, "CEC command timed out"
        except Exception as e:
            return None, None, str(e)

    def take_snapshot(self) -> StateSnapshot:
        """Take a complete state snapshot"""
        timestamp = datetime.now()

        # Check network reachability
        network_reachable, network_response_time = self.check_network_reachability()

        # Check Samsung API state
        samsung_state, samsung_response_time, samsung_error = self.check_samsung_api_state()

        # Check CEC state
        cec_state, cec_response_time, cec_error = self.check_cec_state()

        snapshot = StateSnapshot(
            timestamp=timestamp,
            network_reachable=network_reachable,
            network_response_time=network_response_time,
            samsung_api_state=samsung_state,
            samsung_api_response_time=samsung_response_time,
            samsung_api_error=samsung_error,
            cec_state=cec_state,
            cec_response_time=cec_response_time,
            cec_error=cec_error
        )

        return snapshot

    def analyze_state_change(self, prev_snapshot: StateSnapshot, curr_snapshot: StateSnapshot):
        """Analyze and log state changes"""
        prev_consensus = prev_snapshot.get_consensus_state()
        curr_consensus = curr_snapshot.get_consensus_state()

        if prev_consensus != curr_consensus:
            self.state_changes += 1
            self.logger.info(f"🔄 TV State Change #{self.state_changes}: {prev_consensus} → {curr_consensus}")

            # Log detailed state info
            self.logger.info(f"  Samsung API: {prev_snapshot.samsung_api_state} → {curr_snapshot.samsung_api_state}")
            self.logger.info(f"  CEC: {prev_snapshot.cec_state} → {curr_snapshot.cec_state}")
            self.logger.info(f"  Network: {prev_snapshot.network_reachable} → {curr_snapshot.network_reachable}")

    def analyze_reliability(self, snapshots: List[StateSnapshot]) -> Dict[str, Any]:
        """Analyze reliability metrics from recent snapshots"""
        if len(snapshots) < 2:
            return {}

        # Count successful vs failed checks
        samsung_successes = sum(1 for s in snapshots if s.samsung_api_state is not None)
        cec_successes = sum(1 for s in snapshots if s.cec_state is not None and s.cec_error is None)
        network_successes = sum(1 for s in snapshots if s.network_reachable)

        total_snapshots = len(snapshots)

        # Calculate response times
        samsung_times = [s.samsung_api_response_time for s in snapshots
                        if s.samsung_api_response_time is not None]
        cec_times = [s.cec_response_time for s in snapshots
                    if s.cec_response_time is not None]
        network_times = [s.network_response_time for s in snapshots
                        if s.network_response_time is not None]

        # Count state consensus issues
        consensus_issues = 0
        for snapshot in snapshots:
            states = []
            if snapshot.samsung_api_state:
                states.append(snapshot.samsung_api_state.lower())
            if snapshot.cec_state and snapshot.cec_state != 'unknown':
                states.append(snapshot.cec_state.lower())

            # Check if all methods agree
            if len(set(states)) > 1:
                consensus_issues += 1

        return {
            'total_snapshots': total_snapshots,
            'samsung_api_success_rate': samsung_successes / total_snapshots * 100,
            'cec_success_rate': cec_successes / total_snapshots * 100,
            'network_success_rate': network_successes / total_snapshots * 100,
            'samsung_avg_response_time': sum(samsung_times) / len(samsung_times) if samsung_times else 0,
            'cec_avg_response_time': sum(cec_times) / len(cec_times) if cec_times else 0,
            'network_avg_response_time': sum(network_times) / len(network_times) if network_times else 0,
            'consensus_issues': consensus_issues,
            'state_changes': self.state_changes
        }

    def print_status_summary(self, snapshot: StateSnapshot):
        """Print current status summary"""
        consensus = snapshot.get_consensus_state()

        # Status indicators
        network_status = "🌐" if snapshot.network_reachable else "❌"
        samsung_status = "📱" if snapshot.samsung_api_state else "❌"
        cec_status = "📺" if snapshot.cec_state else "❌"

        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
              f"State: {consensus:>8} | "
              f"{network_status} Net | {samsung_status} API | {cec_status} CEC | "
              f"Changes: {self.state_changes}", end='', flush=True)

    def save_snapshots(self, filename: Optional[str] = None):
        """Save snapshots to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tv_monitor_{timestamp}.json"

        data = {
            'monitoring_session': {
                'start_time': self.snapshots[0].timestamp.isoformat() if self.snapshots else None,
                'end_time': self.snapshots[-1].timestamp.isoformat() if self.snapshots else None,
                'total_snapshots': len(self.snapshots),
                'state_changes': self.state_changes,
                'config_path': self.config_path
            },
            'snapshots': [s.to_dict() for s in self.snapshots]
        }

        # Add reliability analysis
        if len(self.snapshots) >= 10:
            data['reliability_analysis'] = self.analyze_reliability(self.snapshots[-60:])  # Last 60 snapshots

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Monitoring data saved to {filename}")
        return filename

    def run_monitoring(self, interval: float = 30.0, duration: Optional[int] = None,
                      report_interval: int = 20):
        """Run continuous monitoring"""
        self.running = True
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration) if duration else None
        last_report_time = start_time

        self.logger.info(f"Starting TV monitoring (interval: {interval}s)")
        if duration:
            self.logger.info(f"Will run for {duration} seconds until {end_time.strftime('%H:%M:%S')}")
        else:
            self.logger.info("Running indefinitely (Ctrl+C to stop)")

        print(f"\n📊 Live TV State Monitor")
        print(f"{'='*60}")

        try:
            while self.running:
                # Check if we've reached the duration limit
                if end_time and datetime.now() >= end_time:
                    self.logger.info("Monitoring duration reached")
                    break

                # Take snapshot
                snapshot = self.take_snapshot()

                # Analyze state changes
                if self.snapshots:
                    self.analyze_state_change(self.snapshots[-1], snapshot)

                self.snapshots.append(snapshot)

                # Update consensus state
                current_consensus = snapshot.get_consensus_state()
                if current_consensus != self.last_consensus_state:
                    self.last_consensus_state = current_consensus

                # Print live status
                self.print_status_summary(snapshot)

                # Periodic detailed report
                current_time = datetime.now()
                if (current_time - last_report_time).total_seconds() >= report_interval * 60:
                    self._print_detailed_report()
                    last_report_time = current_time

                # Wait for next interval
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
            print(f"\n❌ Monitoring error: {e}")

        finally:
            self.running = False
            print(f"\n\n📋 Final Report")
            print(f"{'='*40}")
            self._print_detailed_report()

            # Save data
            if self.snapshots:
                filename = self.save_snapshots()
                print(f"📄 Data saved to: {filename}")

    def _print_detailed_report(self):
        """Print detailed reliability report"""
        if len(self.snapshots) < 2:
            return

        # Analyze recent snapshots
        recent_snapshots = self.snapshots[-20:] if len(self.snapshots) >= 20 else self.snapshots
        analysis = self.analyze_reliability(recent_snapshots)

        print(f"\n\n📊 Reliability Report (last {len(recent_snapshots)} snapshots)")
        print(f"─" * 50)
        print(f"Samsung API Success Rate: {analysis.get('samsung_api_success_rate', 0):.1f}%")
        print(f"CEC Success Rate: {analysis.get('cec_success_rate', 0):.1f}%")
        print(f"Network Success Rate: {analysis.get('network_success_rate', 0):.1f}%")
        print(f"Avg Response Times - Samsung: {analysis.get('samsung_avg_response_time', 0):.2f}s, "
              f"CEC: {analysis.get('cec_avg_response_time', 0):.2f}s")
        print(f"Total State Changes: {analysis.get('state_changes', 0)}")
        if analysis.get('consensus_issues', 0) > 0:
            print(f"⚠️  Method Disagreements: {analysis.get('consensus_issues', 0)}")

        # Recent errors
        recent_errors = []
        for snapshot in recent_snapshots[-10:]:
            if snapshot.samsung_api_error:
                recent_errors.append(f"Samsung: {snapshot.samsung_api_error[:50]}")
            if snapshot.cec_error and "disabled" not in snapshot.cec_error.lower():
                recent_errors.append(f"CEC: {snapshot.cec_error[:50]}")

        if recent_errors:
            print(f"\n🔍 Recent Errors:")
            for error in recent_errors[-3:]:  # Show last 3 errors
                print(f"  • {error}")


def main():
    parser = argparse.ArgumentParser(description="TV State Monitoring")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--interval", type=float, default=30.0, help="Monitoring interval in seconds")
    parser.add_argument("--duration", type=int, help="Monitoring duration in seconds")
    parser.add_argument("--report-interval", type=int, default=20, help="Detailed report interval in minutes")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Minimal output mode")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        monitor = TVStateMonitor(args.config)

        if args.quiet:
            # Disable console output in quiet mode
            monitor.logger.removeHandler(monitor.logger.handlers[0])

        monitor.run_monitoring(args.interval, args.duration, args.report_interval)

    except Exception as e:
        print(f"Monitor failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())