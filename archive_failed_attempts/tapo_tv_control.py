#!/usr/bin/env python3
"""
Tapo P100 Smart Plug TV Control Module
Provides reliable TV power control via TP-Link Tapo smart plug
"""

import json
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path
from PyP100 import PyP100


class TapoTVController:
    """Control TV power via Tapo P100 smart plug"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.tv_config = self.config.get("tv_control", {})
        
        # Tapo connection details
        self.plug_ip = self.tv_config.get("plug_ip")
        self.email = self.tv_config.get("email")
        self.password = self.tv_config.get("password")
        
        # Timing configuration
        self.boot_wait_time = self.tv_config.get("boot_wait_time", 15)
        self.power_cycle_delay = self.tv_config.get("power_cycle_delay", 5)
        
        # State tracking
        self.plug = None
        self.last_state = None
        self.last_power_change = None
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        self.logger = logging.getLogger(__name__)
        
        if not all([self.plug_ip, self.email, self.password]):
            raise RuntimeError("Tapo plug configuration incomplete (need IP, email, password)")
        
        # Connect on initialization
        self._connect()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")
    
    def _connect(self, retry: bool = True) -> bool:
        """Establish connection to Tapo plug"""
        try:
            self.logger.info(f"Connecting to Tapo plug at {self.plug_ip}")
            
            # Create new P100 instance
            self.plug = PyP100.P100(self.plug_ip, self.email, self.password)
            
            # Perform handshake
            self.plug.handshake()
            
            # Login
            self.plug.login()
            
            # Verify connection with device info
            info = self.plug.getDeviceInfo()
            if info and 'result' in info:
                device_name = info['result'].get('nickname', 'Unknown')
                self.logger.info(f"Connected to Tapo plug: {device_name}")
                self.connection_attempts = 0
                return True
            else:
                raise Exception("Failed to get device info")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Tapo plug: {e}")
            self.plug = None
            
            if retry and self.connection_attempts < self.max_connection_attempts:
                self.connection_attempts += 1
                self.logger.info(f"Retrying connection (attempt {self.connection_attempts}/{self.max_connection_attempts})...")
                time.sleep(2)
                return self._connect(retry=True)
            
            return False
    
    def _ensure_connection(self) -> bool:
        """Ensure we have a valid connection to the plug"""
        if self.plug is None:
            return self._connect()
        
        # Test existing connection
        try:
            info = self.plug.getDeviceInfo()
            if info and 'result' in info:
                return True
        except:
            self.logger.debug("Lost connection to plug, reconnecting...")
            self.plug = None
            return self._connect()
        
        return False
    
    def power_on(self) -> bool:
        """Turn TV on by powering the plug"""
        try:
            # Check if we just powered off (prevent rapid cycling)
            if self.last_power_change:
                time_since_change = time.time() - self.last_power_change
                if time_since_change < self.power_cycle_delay:
                    wait_time = self.power_cycle_delay - time_since_change
                    self.logger.info(f"Waiting {wait_time:.1f}s to prevent rapid power cycling")
                    time.sleep(wait_time)
            
            # Ensure connection
            if not self._ensure_connection():
                self.logger.error("Cannot connect to Tapo plug")
                return False
            
            # Turn on plug
            self.logger.info("Turning TV ON via Tapo plug")
            self.plug.turnOn()
            
            # Update state tracking
            self.last_state = True
            self.last_power_change = time.time()
            
            # Wait for TV to boot if configured
            if self.boot_wait_time > 0:
                self.logger.info(f"Waiting {self.boot_wait_time}s for TV to boot")
                time.sleep(self.boot_wait_time)
            
            self.logger.info("TV powered on successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to turn TV on: {e}")
            # Try reconnecting and retry once
            if self._connect():
                try:
                    self.plug.turnOn()
                    self.last_state = True
                    self.last_power_change = time.time()
                    return True
                except:
                    pass
            return False
    
    def power_off(self) -> bool:
        """Turn TV off by cutting power to the plug"""
        try:
            # Ensure connection
            if not self._ensure_connection():
                self.logger.error("Cannot connect to Tapo plug")
                return False
            
            # Turn off plug
            self.logger.info("Turning TV OFF via Tapo plug")
            self.plug.turnOff()
            
            # Update state tracking
            self.last_state = False
            self.last_power_change = time.time()
            
            self.logger.info("TV powered off successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to turn TV off: {e}")
            # Try reconnecting and retry once
            if self._connect():
                try:
                    self.plug.turnOff()
                    self.last_state = False
                    self.last_power_change = time.time()
                    return True
                except:
                    pass
            return False
    
    def get_power_state(self) -> Optional[bool]:
        """Get current power state of the plug/TV"""
        try:
            # Ensure connection
            if not self._ensure_connection():
                # If we can't connect, return last known state
                return self.last_state
            
            # Get device info
            info = self.plug.getDeviceInfo()
            if info and 'result' in info:
                is_on = info['result'].get('device_on', False)
                self.last_state = is_on
                self.logger.debug(f"Tapo plug state: {'ON' if is_on else 'OFF'}")
                return is_on
            
            return self.last_state
            
        except Exception as e:
            self.logger.error(f"Failed to get power state: {e}")
            return self.last_state
    
    def ensure_power_state(self, desired_state: bool) -> bool:
        """Ensure TV is in the desired power state"""
        current_state = self.get_power_state()
        
        if current_state is None:
            self.logger.warning("Cannot determine current state, attempting to set desired state")
            if desired_state:
                return self.power_on()
            else:
                return self.power_off()
        
        if current_state == desired_state:
            self.logger.debug(f"TV already in desired state: {'ON' if desired_state else 'OFF'}")
            return True
        
        if desired_state:
            return self.power_on()
        else:
            return self.power_off()
    
    def get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get detailed information about the Tapo plug"""
        try:
            if not self._ensure_connection():
                return None
            
            info = self.plug.getDeviceInfo()
            if info and 'result' in info:
                return info['result']
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            return None


def main():
    """Command line interface for Tapo TV control"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tapo P100 TV Control")
    parser.add_argument("command", nargs='?', 
                       choices=['on', 'off', 'toggle', 'status', 'info', 'test'],
                       default='status', help="Command to execute")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        controller = TapoTVController(args.config)
        
        if args.command == 'on':
            success = controller.power_on()
            print(f"Power ON: {'✅ Success' if success else '❌ Failed'}")
            exit(0 if success else 1)
            
        elif args.command == 'off':
            success = controller.power_off()
            print(f"Power OFF: {'✅ Success' if success else '❌ Failed'}")
            exit(0 if success else 1)
            
        elif args.command == 'toggle':
            state = controller.get_power_state()
            if state is None:
                print("Error: Could not determine current state")
                exit(1)
            
            new_state = not state
            success = controller.ensure_power_state(new_state)
            print(f"Toggle {'ON' if new_state else 'OFF'}: {'✅ Success' if success else '❌ Failed'}")
            exit(0 if success else 1)
            
        elif args.command == 'status':
            state = controller.get_power_state()
            if state is None:
                print("Error: Could not determine power state")
                exit(1)
            print(f"TV is {'ON' if state else 'OFF'}")
            
        elif args.command == 'info':
            info = controller.get_device_info()
            if not info:
                print("Error: Could not get device information")
                exit(1)
            
            print(f"Device Name: {info.get('nickname', 'Unknown')}")
            print(f"Model: {info.get('model', 'Unknown')}")
            print(f"Current State: {'ON' if info.get('device_on', False) else 'OFF'}")
            print(f"MAC Address: {info.get('mac', 'Unknown')}")
            print(f"Hardware Version: {info.get('hw_ver', 'Unknown')}")
            print(f"Firmware Version: {info.get('fw_ver', 'Unknown')}")
            
        elif args.command == 'test':
            print("Testing Tapo TV Control")
            print("=" * 40)
            
            # Test connection
            print("Testing connection...")
            info = controller.get_device_info()
            if info:
                print(f"✅ Connected to: {info.get('nickname', 'Unknown')}")
            else:
                print("❌ Connection failed")
                exit(1)
            
            # Test state reading
            print("\nTesting state reading...")
            state = controller.get_power_state()
            if state is not None:
                print(f"✅ Current state: {'ON' if state else 'OFF'}")
            else:
                print("❌ Could not read state")
            
            # Test power control
            test_control = input("\nTest power control? (y/n): ").lower()
            if test_control == 'y':
                print("\nTurning OFF...")
                if controller.power_off():
                    print("✅ Turned OFF successfully")
                    time.sleep(3)
                    
                    print("\nTurning ON...")
                    if controller.power_on():
                        print("✅ Turned ON successfully")
                    else:
                        print("❌ Failed to turn ON")
                else:
                    print("❌ Failed to turn OFF")
            
            print("\n✅ All tests completed!")
            
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()