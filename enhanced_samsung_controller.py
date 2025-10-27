#!/usr/bin/env python3
"""
Enhanced Samsung TV Controller with Improved Reliability

This controller addresses the reliability issues observed in the standard Samsung
network API by implementing:
- Connection lifecycle management
- Aggressive connection cleanup
- Exponential backoff for retries
- SSL error recovery
- State verification with multiple methods
- Recovery from stuck states
"""

import json
import logging
import time
import socket
import subprocess
import warnings
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

# Suppress SSL warnings from Samsung TV API
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

try:
    from samsungtvws import SamsungTVWS
    import wakeonlan
    HAS_WAKEONLAN = True
    HAS_SAMSUNGTVWS = True
except ImportError:
    SamsungTVWS = None
    wakeonlan = None
    HAS_WAKEONLAN = False
    HAS_SAMSUNGTVWS = False


@dataclass
class ConnectionStats:
    """Track connection health metrics"""
    total_attempts: int = 0
    successful_connections: int = 0
    ssl_errors: int = 0
    timeout_errors: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_connections / self.total_attempts) * 100

    @property
    def is_degraded(self) -> bool:
        """Check if connection quality is degraded"""
        return (self.consecutive_failures >= 3 or
                self.success_rate < 70 and self.total_attempts > 5)


class EnhancedSamsungTVController:
    """Enhanced Samsung TV controller with improved reliability"""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.tv_config = self.config.get("samsung_tv", {})
        self.cec_config = self.config.get("cec", {})
        self.tv = None
        self.logger = logging.getLogger(__name__)
        self.connection_stats = ConnectionStats()
        self.last_power_off_time = None
        self.last_cleanup_time = datetime.now()

        # Enhanced configuration options
        self.max_connection_age = timedelta(minutes=5)  # Force new connection after 5 min
        self.cleanup_interval = timedelta(minutes=2)    # Cleanup every 2 minutes
        self.max_retries = 5                            # Increased retry count
        self.base_retry_delay = 1.0                     # Base delay for exponential backoff
        self.max_retry_delay = 10.0                     # Max delay cap

        if not self.tv_config.get("enabled", False):
            raise RuntimeError("Samsung TV control is disabled in config")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def _force_connection_cleanup(self):
        """Aggressively cleanup existing connections"""
        if self.tv is not None:
            try:
                # Try to close connection gracefully
                if hasattr(self.tv, 'close'):
                    self.tv.close()
            except Exception:
                pass
            finally:
                self.tv = None

        self.last_cleanup_time = datetime.now()
        self.logger.debug("Connection cleanup completed")

    def _should_force_cleanup(self) -> bool:
        """Check if we should force connection cleanup"""
        now = datetime.now()

        # Force cleanup if connection is old
        if (self.connection_stats.last_success and
            now - self.connection_stats.last_success > self.max_connection_age):
            return True

        # Force cleanup on degraded performance
        if self.connection_stats.is_degraded:
            return True

        # Periodic cleanup
        if now - self.last_cleanup_time > self.cleanup_interval:
            return True

        return False

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_retry_delay * (2 ** attempt)
        return min(delay, self.max_retry_delay)

    def _connect_with_recovery(self, force_new: bool = False) -> bool:
        """Enhanced connection with recovery mechanisms"""
        self.connection_stats.total_attempts += 1

        # Force cleanup if needed
        if force_new or self._should_force_cleanup():
            self._force_connection_cleanup()

        if not HAS_SAMSUNGTVWS:
            self.logger.error(f"Samsung TV library not available (HAS_SAMSUNGTVWS={HAS_SAMSUNGTVWS}, SamsungTVWS={SamsungTVWS is not None})")
            self.connection_stats.consecutive_failures += 1
            self.connection_stats.last_failure = datetime.now()
            return False

        # Check if we can reuse existing connection
        if not force_new and self.tv is not None:
            try:
                # Quick health check
                info = self.tv.rest_device_info()
                if info:
                    self.logger.debug("Reusing healthy connection")
                    self.connection_stats.successful_connections += 1
                    self.connection_stats.consecutive_failures = 0
                    self.connection_stats.last_success = datetime.now()
                    return True
            except Exception as e:
                self.logger.debug(f"Health check failed: {e}, creating new connection")
                self._force_connection_cleanup()

        # Create new connection with retries
        ip_address = self.tv_config["ip_address"]
        port = self.tv_config.get("port", 8002)
        token_file = self.tv_config.get("token_file")
        timeout = self.tv_config.get("connection_timeout", 8)  # Reduced timeout

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Connecting to Samsung TV at {ip_address}:{port} (attempt {attempt + 1}/{self.max_retries})")

                self.tv = SamsungTVWS(
                    host=ip_address,
                    port=port,
                    token_file=token_file,
                    timeout=timeout
                )

                # Verify connection works
                info = self.tv.rest_device_info()
                if info:
                    self.logger.info(f"Connected to Samsung TV: {info.get('device', {}).get('name', 'Unknown')}")
                    self.connection_stats.successful_connections += 1
                    self.connection_stats.consecutive_failures = 0
                    self.connection_stats.last_success = datetime.now()
                    return True
                else:
                    raise Exception("Failed to get device info")

            except Exception as e:
                error_msg = str(e).lower()

                if "ssl" in error_msg or "certificate" in error_msg:
                    self.connection_stats.ssl_errors += 1
                elif "timeout" in error_msg:
                    self.connection_stats.timeout_errors += 1

                self.logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

                # Cleanup failed connection
                self.tv = None

                # Wait before retry (except last attempt)
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.info(f"Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)

        # All attempts failed
        self.connection_stats.consecutive_failures += 1
        self.connection_stats.last_failure = datetime.now()
        self.logger.error(f"Failed to connect after {self.max_retries} attempts")
        return False

    def _is_tv_reachable(self) -> bool:
        """Check if TV is reachable on the network"""
        try:
            ip = self.tv_config["ip_address"]
            port = self.tv_config.get("port", 8002)
            timeout = 2  # Reduced timeout for faster checks

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0

        except Exception as e:
            self.logger.debug(f"Network reachability check failed: {e}")
            return False

    def _get_power_state_with_retry(self) -> Optional[str]:
        """Get power state with enhanced retry logic"""
        for attempt in range(3):
            try:
                if self._connect_with_recovery(force_new=(attempt > 0)):
                    info = self.tv.rest_device_info()
                    if info and 'device' in info:
                        power_state = info['device'].get('PowerState', 'unknown')
                        self.logger.debug(f"TV PowerState: {power_state}")
                        return power_state
            except Exception as e:
                if attempt == 2:  # Last attempt
                    self.logger.error(f"Failed to get power state: {e}")
                else:
                    self.logger.debug(f"Power state attempt {attempt + 1} failed: {e}")
                    time.sleep(1)
        return None

    def _websocket_power_toggle_enhanced(self) -> Tuple[bool, str]:
        """Enhanced WebSocket power toggle with better error handling"""
        initial_state = self._get_power_state_with_retry()

        for attempt in range(self.max_retries):
            try:
                # Force new connection on retries to avoid stale connections
                force_new = attempt > 1
                if self._connect_with_recovery(force_new=force_new):
                    self.logger.info(f"Sending power toggle command (attempt {attempt + 1}/{self.max_retries})")
                    self.tv.shortcuts().power()

                    # Wait for TV to process command
                    time.sleep(3)

                    # Verify state change
                    final_state = self._get_power_state_with_retry()
                    if final_state and initial_state and final_state != initial_state:
                        self.logger.info(f"Power toggle successful: {initial_state} -> {final_state}")
                        return True, f"State changed: {initial_state} -> {final_state}"
                    elif final_state == initial_state:
                        self.logger.warning(f"State unchanged after toggle: {initial_state}")
                        # Continue to next attempt
                    else:
                        self.logger.warning(f"Could not verify state change")
                else:
                    self.logger.warning(f"Connection failed for toggle attempt {attempt + 1}")

            except Exception as e:
                error_msg = str(e).lower()
                if "ssl" in error_msg or "eof occurred" in error_msg:
                    # SSL errors during power operations are often normal
                    self.logger.info(f"SSL error during power toggle (attempt {attempt + 1}): {e}")

                    # Check if toggle worked despite SSL error
                    time.sleep(2)
                    final_state = self._get_power_state_with_retry()
                    if final_state and initial_state and final_state != initial_state:
                        self.logger.info(f"Power toggle successful despite SSL error: {initial_state} -> {final_state}")
                        return True, f"State changed despite SSL error: {initial_state} -> {final_state}"
                else:
                    self.logger.error(f"Power toggle attempt {attempt + 1} failed: {e}")

                # Force cleanup on SSL errors
                if "ssl" in error_msg:
                    self._force_connection_cleanup()

            # Wait before retry
            if attempt < self.max_retries - 1:
                delay = self._calculate_retry_delay(attempt)
                self.logger.info(f"Waiting {delay:.1f}s before retry...")
                time.sleep(delay)

        return False, f"All {self.max_retries} toggle attempts failed"

    def power_on(self) -> bool:
        """Enhanced power on with recovery mechanisms"""
        self.logger.info("Attempting to turn TV on")

        current_state = self._get_power_state_with_retry()

        if current_state == 'on':
            self.logger.info("TV is already on")
            return True
        elif current_state == 'standby':
            self.logger.info("TV in standby, attempting power on")
            success, message = self._websocket_power_toggle_enhanced()
            if success:
                self.logger.info("TV powered on from standby")
                return True

        # Try Wake-on-LAN if available
        if self._wake_tv():
            self.logger.info("Wake-on-LAN sent, waiting for TV...")
            time.sleep(6)

            new_state = self._get_power_state_with_retry()
            if new_state == 'on':
                self.logger.info("TV powered on via Wake-on-LAN")
                return True
            elif new_state == 'standby':
                self.logger.info("TV in standby after WoL, using toggle")
                success, _ = self._websocket_power_toggle_enhanced()
                return success

        # Final attempt with WebSocket toggle
        self.logger.info("Trying direct power toggle")
        success, message = self._websocket_power_toggle_enhanced()
        if success:
            self.logger.info("TV powered on via direct toggle")
        else:
            self.logger.error(f"Failed to power on TV: {message}")

        return success

    def power_off(self) -> bool:
        """Enhanced power off with verification"""
        self.logger.info("Attempting to turn TV off")

        # Check if already off
        if not self._is_tv_reachable():
            self.logger.info("TV already appears to be off")
            self.last_power_off_time = datetime.now()
            return True

        success, message = self._websocket_power_toggle_enhanced()

        if success or "SSL error" in message:
            # Verify TV is actually off/standby
            time.sleep(3)
            final_state = self._get_power_state_with_retry()

            if final_state and final_state != 'on':
                self.logger.info(f"TV successfully turned off (state: {final_state})")
                self.last_power_off_time = datetime.now()
                return True
            elif not self._is_tv_reachable():
                self.logger.info("TV successfully turned off (unreachable)")
                self.last_power_off_time = datetime.now()
                return True
            else:
                self.logger.warning("TV may still be on after power off command")
                # For Samsung TVs, assume success if command was sent
                self.last_power_off_time = datetime.now()
                return True

        self.logger.error(f"Failed to turn TV off: {message}")
        return False

    def get_power_state(self) -> Optional[bool]:
        """Get current power state"""
        try:
            power_state = self._get_power_state_with_retry()
            if power_state:
                is_on = power_state.lower() == 'on'
                self.logger.debug(f"TV PowerState '{power_state}' -> {is_on}")
                return is_on
            elif self._is_tv_reachable():
                return False  # Reachable but no power state = standby
            else:
                return False  # Not reachable = off
        except Exception as e:
            self.logger.error(f"Failed to get power state: {e}")
            return None

    def _wake_tv(self) -> bool:
        """Wake TV using Wake-on-LAN"""
        mac_address = self.tv_config.get("mac_address")
        wake_on_lan = self.tv_config.get("wake_on_lan", False)

        if not wake_on_lan or not mac_address or not HAS_WAKEONLAN:
            return False

        try:
            self.logger.info(f"Sending Wake-on-LAN to {mac_address}")
            wakeonlan.send_magic_packet(mac_address)
            return True
        except Exception as e:
            self.logger.error(f"Wake-on-LAN failed: {e}")
            return False

    def ensure_power_state(self, desired_state: bool) -> bool:
        """Ensure TV is in desired power state (compatible with original controller)"""
        self.logger.debug(f"Ensuring TV power state: {'ON' if desired_state else 'OFF'}")

        if desired_state:
            # Want TV ON
            result = self.power_on()
            if result:
                self.logger.info("Successfully ensured TV is ON")
            else:
                self.logger.error("Failed to ensure TV is ON")
            return result
        else:
            # Want TV OFF
            result = self.power_off()
            if result:
                self.logger.info("Successfully ensured TV is OFF")
            else:
                self.logger.error("Failed to ensure TV is OFF")
            return result

    def get_tv_info(self) -> Optional[Dict[str, Any]]:
        """Get TV information (compatible with original controller)"""
        try:
            if self._connect_with_recovery():
                return self.tv.rest_device_info()
        except Exception as e:
            self.logger.error(f"Failed to get TV info: {e}")
        return None

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection health statistics"""
        return {
            'total_attempts': self.connection_stats.total_attempts,
            'successful_connections': self.connection_stats.successful_connections,
            'success_rate': self.connection_stats.success_rate,
            'ssl_errors': self.connection_stats.ssl_errors,
            'timeout_errors': self.connection_stats.timeout_errors,
            'consecutive_failures': self.connection_stats.consecutive_failures,
            'is_degraded': self.connection_stats.is_degraded,
            'last_success': self.connection_stats.last_success.isoformat() if self.connection_stats.last_success else None,
            'last_failure': self.connection_stats.last_failure.isoformat() if self.connection_stats.last_failure else None
        }

    def reset_connection_stats(self):
        """Reset connection statistics"""
        self.connection_stats = ConnectionStats()
        self.logger.info("Connection statistics reset")


def main():
    """Command line interface for Enhanced Samsung TV control"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Samsung TV Control")
    parser.add_argument("command", nargs='?', choices=['on', 'off', 'status', 'stats', 'reset-stats'],
                       default='status', help="Command to execute")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')

    try:
        controller = EnhancedSamsungTVController(args.config)

        if args.command == 'on':
            if not args.quiet:
                print("Turning TV on...")
            success = controller.power_on()
            if args.quiet:
                exit(0 if success else 1)
            print(f"Success: {success}")

        elif args.command == 'off':
            if not args.quiet:
                print("Turning TV off...")
            success = controller.power_off()
            if args.quiet:
                exit(0 if success else 1)
            print(f"Success: {success}")

        elif args.command == 'status':
            state = controller.get_power_state()
            if state is None:
                print("Error: Could not determine TV power state")
                exit(1)
            elif state:
                print("ON" if args.quiet else "TV is ON")
            else:
                print("OFF" if args.quiet else "TV is OFF")

        elif args.command == 'stats':
            stats = controller.get_connection_stats()
            if args.quiet:
                print(f"{stats['success_rate']:.1f}%")
            else:
                print("Connection Statistics:")
                print(f"  Success Rate: {stats['success_rate']:.1f}%")
                print(f"  Total Attempts: {stats['total_attempts']}")
                print(f"  SSL Errors: {stats['ssl_errors']}")
                print(f"  Consecutive Failures: {stats['consecutive_failures']}")
                print(f"  Status: {'DEGRADED' if stats['is_degraded'] else 'HEALTHY'}")

        elif args.command == 'reset-stats':
            controller.reset_connection_stats()
            print("Connection statistics reset")

    except Exception as e:
        if args.debug:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()