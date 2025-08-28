#!/usr/bin/env python3

import json
import logging
import time
import socket
import subprocess
import warnings
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

# Suppress SSL warnings from Samsung TV API
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

try:
    from samsungtvws import SamsungTVWS
    import wakeonlan
    HAS_WAKEONLAN = True
except ImportError:
    wakeonlan = None
    HAS_WAKEONLAN = False


class SamsungTVController:
    """Samsung TV control via network API"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.tv_config = self.config.get("samsung_tv", {})
        self.cec_config = self.config.get("cec", {})
        self.tv = None
        self.logger = logging.getLogger(__name__)
        self.last_power_off_time = None
        
        if not self.tv_config.get("enabled", False):
            raise RuntimeError("Samsung TV control is disabled in config")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")
    
    def _connect(self) -> bool:
        """Establish connection to Samsung TV"""
        if self.tv is not None:
            try:
                info = self.tv.rest_device_info()
                if info:
                    return True
            except Exception:
                self.tv = None
        
        try:
            ip_address = self.tv_config["ip_address"]
            port = self.tv_config.get("port", 8002)
            token_file = self.tv_config.get("token_file")
            timeout = self.tv_config.get("connection_timeout", 10)
            
            self.logger.info(f"Connecting to Samsung TV at {ip_address}:{port}")
            
            self.tv = SamsungTVWS(
                host=ip_address,
                port=port,
                token_file=token_file,
                timeout=timeout
            )
            
            info = self.tv.rest_device_info()
            if info:
                self.logger.info(f"Connected to Samsung TV: {info.get('device', {}).get('name', 'Unknown')}")
                return True
            else:
                self.logger.error("Failed to get device info from TV")
                self.tv = None
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Samsung TV: {e}")
            self.tv = None
            return False
    
    def _is_tv_reachable(self) -> bool:
        """Check if TV is reachable on the network"""
        try:
            ip = self.tv_config["ip_address"]
            port = self.tv_config.get("port", 8002)
            timeout = 3
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
            
        except Exception as e:
            self.logger.debug(f"Network reachability check failed: {e}")
            return False
    
    def _wake_tv(self) -> bool:
        """Attempt to wake TV using Wake-on-LAN if configured"""
        mac_address = self.tv_config.get("mac_address")
        wake_on_lan = self.tv_config.get("wake_on_lan", False)
        
        if not wake_on_lan or not mac_address or not HAS_WAKEONLAN:
            return False
        
        try:
            self.logger.info(f"Sending Wake-on-LAN to {mac_address}")
            wakeonlan.send_magic_packet(mac_address)
            time.sleep(3)
            return True
        except Exception as e:
            self.logger.error(f"Wake-on-LAN failed: {e}")
            return False
    
    def _cec_power_on(self) -> bool:
        """Turn TV on using CEC (with cooldown check)"""
        if not self.cec_config.get("enabled", False):
            return False
            
        # Check if we're within the CEC cooldown period
        if self.last_power_off_time:
            cooldown = self.cec_config.get("cooldown_period", 25)
            time_since_off = (datetime.now() - self.last_power_off_time).total_seconds()
            if time_since_off < cooldown:
                remaining = cooldown - time_since_off
                self.logger.info(f"CEC cooldown active, {remaining:.1f}s remaining")
                return False
        
        try:
            self.logger.info("Attempting CEC power on")
            # Use cec-client to send power on command
            result = subprocess.run([
                'bash', '-c', 'echo "on 0" | cec-client -s -d 1'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.logger.info("CEC power on command sent successfully")
                return True
            else:
                self.logger.warning(f"CEC power on failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"CEC power on error: {e}")
            return False
    
    def power_on(self, force_wol: bool = False) -> bool:
        """Turn TV on using optimal method based on current state"""
        self.logger.info("Attempting to turn TV on")
        
        # Check current state
        current_state = self._get_actual_power_state()
        
        if current_state == 'on':
            self.logger.info("TV is already on")
            return True
        elif current_state == 'standby':
            # TV is in standby - WebSocket toggle should work
            self.logger.info("TV in standby, using WebSocket toggle")
            return self._websocket_power_toggle()
        else:
            # TV is fully off or unknown state - try multiple strategies
            self.logger.info("TV appears fully off, trying multiple power-on methods")
            
            # Strategy 1: Wake-on-LAN (for fully off TV)
            if self._wake_tv() or force_wol:
                self.logger.info("Wake-on-LAN sent, waiting for TV to boot...")
                time.sleep(8)
                
                # Check if TV came online
                new_state = self._get_actual_power_state()
                if new_state == 'on':
                    self.logger.info("TV successfully powered on via Wake-on-LAN")
                    return True
                elif new_state == 'standby':
                    self.logger.info("TV in standby after WoL, using WebSocket toggle")
                    return self._websocket_power_toggle()
                else:
                    self.logger.warning("TV not responding after Wake-on-LAN")
            
            # Strategy 2: CEC (if available and out of cooldown)
            if self._cec_power_on():
                self.logger.info("CEC power on sent, waiting for response...")
                time.sleep(5)
                new_state = self._get_actual_power_state()
                if new_state == 'on':
                    self.logger.info("TV successfully powered on via CEC")
                    return True
                elif new_state == 'standby':
                    self.logger.info("TV in standby after CEC, using WebSocket toggle")
                    return self._websocket_power_toggle()
                else:
                    self.logger.warning("TV not responding after CEC command")
            
            # Strategy 3: Direct WebSocket toggle (last resort)
            self.logger.info("Trying direct WebSocket power toggle as final attempt")
            return self._websocket_power_toggle()
    
    def _websocket_power_toggle(self) -> bool:
        """Send WebSocket power toggle command"""
        retry_count = self.config.get("tv_control", {}).get("retry_attempts", 3)
        retry_delay = self.config.get("tv_control", {}).get("retry_delay", 2)
        
        for attempt in range(retry_count):
            try:
                if self._connect():
                    initial_state = self._get_actual_power_state()
                    self.tv.shortcuts().power()
                    self.logger.info("WebSocket power toggle command sent")
                    time.sleep(3)
                    
                    # Verify state changed
                    final_state = self._get_actual_power_state()
                    if final_state and final_state != initial_state:
                        self.logger.info(f"TV state changed: {initial_state} -> {final_state}")
                        return final_state == 'on'
                    else:
                        self.logger.warning(f"TV state unchanged after toggle: {final_state}")
                else:
                    self.logger.warning(f"WebSocket connection attempt {attempt + 1} failed")
                    
            except Exception as e:
                self.logger.error(f"WebSocket toggle attempt {attempt + 1} failed: {e}")
            
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
        
        self.logger.error("WebSocket power toggle failed")
        return False
    
    def _get_actual_power_state(self) -> Optional[str]:
        """Get actual power state from Samsung TV API"""
        try:
            if self._connect():
                info = self.tv.rest_device_info()
                if info and 'device' in info:
                    power_state = info['device'].get('PowerState', 'unknown')
                    self.logger.debug(f"TV reports PowerState: {power_state}")
                    return power_state
        except Exception as e:
            self.logger.debug(f"Could not get power state: {e}")
        return None
    
    def _check_tv_standby(self) -> bool:
        """Check if TV is in standby mode"""
        power_state = self._get_actual_power_state()
        if power_state:
            # TV is responding with power state
            return power_state.lower() in ['standby', 'off']
        elif self._is_tv_reachable():
            # TV is reachable but not responding to WebSocket - likely standby
            return True
        else:
            # TV is not reachable - fully off
            return False
    
    def power_off(self) -> bool:
        """Turn TV off using WebSocket toggle"""
        self.logger.info("Attempting to turn TV off")
        
        # Check if TV is reachable first
        if not self._is_tv_reachable():
            self.logger.info("TV already appears to be off (not reachable)")
            self.last_power_off_time = datetime.now()
            return True
        
        initial_state_reachable = True
        retry_count = self.config.get("tv_control", {}).get("retry_attempts", 3)
        retry_delay = self.config.get("tv_control", {}).get("retry_delay", 2)
        
        for attempt in range(retry_count):
            try:
                if self._connect():
                    self.tv.shortcuts().power()
                    self.logger.info("TV power toggle command sent (should turn off)")
                    time.sleep(3)  # Give TV more time to enter standby
                    
                    # Check multiple indicators of TV being off/standby
                    still_reachable = self._is_tv_reachable()
                    in_standby = self._check_tv_standby()
                    
                    if not still_reachable:
                        # TV is completely off (ideal)
                        self.logger.info("TV successfully turned off (unreachable)")
                        self.last_power_off_time = datetime.now()
                        return True
                    elif in_standby:
                        # TV is in standby mode (acceptable for Samsung TVs)
                        self.logger.info("TV successfully turned off (standby mode)")
                        self.last_power_off_time = datetime.now()
                        return True
                    else:
                        self.logger.warning("TV still appears fully on after power toggle")
                        
                else:
                    self.logger.warning(f"Connection attempt {attempt + 1} failed")
                    
            except Exception as e:
                self.logger.error(f"Power off attempt {attempt + 1} failed: {e}")
            
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
        
        # Final check - even if we can't verify, assume success if we sent the command
        # Samsung TVs often stay network-reachable in standby mode
        self.logger.warning("Could not verify TV is off, but command was sent")
        self.last_power_off_time = datetime.now()
        return True  # Assume success for Samsung TV behavior
    
    def get_power_state(self) -> Optional[bool]:
        """Get current power state of TV using PowerState API"""
        try:
            power_state = self._get_actual_power_state()
            if power_state:
                # Use the actual PowerState from Samsung API
                is_on = power_state.lower() == 'on'
                self.logger.debug(f"TV PowerState '{power_state}' -> {is_on}")
                return is_on
            elif self._is_tv_reachable():
                # TV is reachable but not responding to WebSocket - assume standby
                return False
            else:
                # TV is not reachable - fully off
                return False
        except Exception as e:
            self.logger.error(f"Failed to get power state: {e}")
            return None
    
    def ensure_power_state(self, desired_state: bool) -> bool:
        """Ensure TV is in desired power state (context-aware control)"""
        if desired_state:
            # Want TV ON - always try power_on (it will handle current state)
            return self.power_on()
        else:
            # Want TV OFF - only try if TV appears to be on
            if self._is_tv_reachable():
                return self.power_off()
            else:
                # TV already appears off
                self.logger.info("TV already appears to be off")
                return True
    
    def get_tv_info(self) -> Optional[Dict[str, Any]]:
        """Get TV information"""
        try:
            if self._connect():
                return self.tv.rest_device_info()
        except Exception as e:
            self.logger.error(f"Failed to get TV info: {e}")
        return None


def main():
    """Command line interface for Samsung TV control"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Samsung TV Control")
    parser.add_argument("command", nargs='?', choices=['on', 'off', 'toggle', 'ensure-on', 'ensure-off', 'status', 'info'], 
                       default='test', help="Command to execute")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode (minimal output)")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    try:
        controller = SamsungTVController(args.config)
        
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
            
        elif args.command == 'toggle':
            state = controller.get_power_state()
            if state is None:
                print("Error: Could not determine TV power state")
                exit(1)
            
            if state:
                if not args.quiet:
                    print("TV is on, turning off...")
                success = controller.power_off()
            else:
                if not args.quiet:
                    print("TV is off, turning on...")
                success = controller.power_on()
            
            if args.quiet:
                exit(0 if success else 1)
            print(f"Success: {success}")
            
        elif args.command == 'ensure-on':
            if not args.quiet:
                print("Ensuring TV is on...")
            success = controller.ensure_power_state(True)
            if args.quiet:
                exit(0 if success else 1)
            print(f"Success: {success}")
            
        elif args.command == 'ensure-off':
            if not args.quiet:
                print("Ensuring TV is off...")
            success = controller.ensure_power_state(False)
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
                
        elif args.command == 'info':
            info = controller.get_tv_info()
            if not info:
                print("Error: Could not get TV information")
                exit(1)
            
            if args.quiet:
                device = info.get('device', {})
                print(f"{device.get('name', 'Unknown')} - {device.get('modelName', 'Unknown')}")
            else:
                device = info.get('device', {})
                print(f"TV Name: {device.get('name', 'Unknown')}")
                print(f"Model: {device.get('modelName', 'Unknown')}")
                print(f"Version: {device.get('version', 'Unknown')}")
                print(f"Network MAC: {device.get('wifiMac', 'Unknown')}")
                print(f"Device ID: {device.get('id', 'Unknown')}")
                
        else:  # test mode (default)
            print("Samsung TV Controller Test")
            print("=" * 30)
            
            print("\nGetting TV info...")
            info = controller.get_tv_info()
            if info:
                device = info.get('device', {})
                print(f"TV: {device.get('name', 'Unknown')}")
                print(f"Model: {device.get('modelName', 'Unknown')}")
            
            print("\nChecking power state...")
            state = controller.get_power_state()
            print(f"Power state: {'ON' if state else 'OFF' if state is not None else 'UNKNOWN'}")
            
            print("\nTesting power toggle...")
            if state:
                print("TV is on, turning off...")
                success = controller.power_off()
            elif state is False:
                print("TV is off, turning on...")
                success = controller.power_on()
            else:
                print("Cannot determine TV state, trying toggle...")
                success = controller.power_on()  # Default to power on
            
            print(f"Command success: {success}")
        
    except Exception as e:
        if args.debug:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()