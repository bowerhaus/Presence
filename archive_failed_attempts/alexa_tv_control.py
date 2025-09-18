#!/usr/bin/env python3
"""
Alexa TV Control Module

Controls TV via Tapo smart plug "many paintings" using Amazon Alexa API.
Uses AlexaPy library for programmatic control of Alexa devices.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any

import alexapy
from alexapy import AlexaAPI, AlexaLogin


class AlexaTVControl:
    """
    TV control via Alexa smart home device.
    
    Controls the Tapo smart plug named "many paintings" through
    Amazon Alexa API using AlexaPy library.
    """
    
    def __init__(self, amazon_email: str, amazon_password: str, device_name: str = "many paintings"):
        """
        Initialize Alexa TV control.
        
        Args:
            amazon_email: Amazon account email
            amazon_password: Amazon account password
            device_name: Name of the smart plug device in Alexa
        """
        self.amazon_email = amazon_email
        self.amazon_password = amazon_password
        self.device_name = device_name.lower()
        
        self.alexa = None
        self.login = None
        self.device_entity_id = None
        
        self.logger = logging.getLogger(__name__)
        
        # Connection state
        self.is_connected = False
        self.last_connection_attempt = 0
        self.connection_retry_delay = 30  # seconds
        
    async def connect(self) -> bool:
        """
        Connect to Amazon Alexa and discover the target device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Avoid frequent reconnection attempts
            current_time = time.time()
            if (current_time - self.last_connection_attempt) < self.connection_retry_delay:
                self.logger.debug(f"Skipping connection attempt, last attempt {current_time - self.last_connection_attempt:.1f}s ago")
                return self.is_connected
                
            self.last_connection_attempt = current_time
            
            self.logger.info("Connecting to Amazon Alexa...")
            
            # Create login session
            self.login = AlexaLogin(
                url="amazon.com",
                email=self.amazon_email,
                password=self.amazon_password,
                outputpath=lambda filename: f"./{filename}"
            )
            
            # Login to Amazon
            await self.login.login()
            
            if not await self.login.test_loggedin():
                self.logger.error("Failed to login to Amazon")
                return False
                
            # Create API instance
            self.alexa = AlexaAPI(self.login, None)
            
            # Discover devices
            await self.alexa.init()
            
            # Find our target device
            self.device_entity_id = await self._find_device()
            
            if not self.device_entity_id:
                self.logger.error(f"Device '{self.device_name}' not found in Alexa")
                return False
                
            self.is_connected = True
            self.logger.info(f"✅ Connected to Alexa, found device: {self.device_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Alexa: {e}")
            self.is_connected = False
            return False
    
    async def _find_device(self) -> Optional[str]:
        """
        Find the target device entity ID in Alexa.
        
        Returns:
            Device entity ID if found, None otherwise
        """
        try:
            # Get all devices
            devices = await self.alexa.get_devices()
            
            self.logger.debug(f"Found {len(devices)} Alexa devices")
            
            # Search for our device by name
            for device in devices:
                device_info = devices[device]
                device_display_name = device_info.get('accountName', '').lower()
                
                self.logger.debug(f"Checking device: '{device_display_name}' (entity: {device})")
                
                if self.device_name in device_display_name:
                    self.logger.info(f"Found target device: '{device_display_name}' -> {device}")
                    return device
                    
            # If exact match not found, list all available devices for debugging
            self.logger.warning("Target device not found. Available devices:")
            for device in devices:
                device_info = devices[device]
                device_display_name = device_info.get('accountName', 'Unknown')
                self.logger.warning(f"  - '{device_display_name}' (entity: {device})")
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding device: {e}")
            return None
    
    async def _ensure_connected(self) -> bool:
        """
        Ensure we have a valid connection to Alexa.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.is_connected:
            return await self.connect()
            
        # Test if connection is still valid
        try:
            if self.login and not await self.login.test_loggedin():
                self.logger.warning("Alexa login expired, reconnecting...")
                self.is_connected = False
                return await self.connect()
        except Exception as e:
            self.logger.warning(f"Connection test failed: {e}, reconnecting...")
            self.is_connected = False
            return await self.connect()
            
        return True
    
    async def turn_on(self) -> bool:
        """
        Turn on the TV by powering on the smart plug.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_connected():
                return False
                
            self.logger.info(f"Turning ON device '{self.device_name}' via Alexa...")
            
            # Send turn on command
            success = await self.alexa.turn_on(self.device_entity_id)
            
            if success:
                self.logger.info("✅ TV turned ON via Alexa")
                return True
            else:
                self.logger.error("❌ Failed to turn ON TV via Alexa")
                return False
                
        except Exception as e:
            self.logger.error(f"Error turning on TV: {e}")
            return False
    
    async def turn_off(self) -> bool:
        """
        Turn off the TV by powering off the smart plug.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_connected():
                return False
                
            self.logger.info(f"Turning OFF device '{self.device_name}' via Alexa...")
            
            # Send turn off command
            success = await self.alexa.turn_off(self.device_entity_id)
            
            if success:
                self.logger.info("✅ TV turned OFF via Alexa")
                return True
            else:
                self.logger.error("❌ Failed to turn OFF TV via Alexa")
                return False
                
        except Exception as e:
            self.logger.error(f"Error turning off TV: {e}")
            return False
    
    async def get_power_state(self) -> Optional[str]:
        """
        Get current power state of the smart plug.
        
        Returns:
            "on", "off", or None if unable to determine
        """
        try:
            if not await self._ensure_connected():
                return None
                
            # Get device state
            devices = await self.alexa.get_devices()
            
            if self.device_entity_id in devices:
                device_info = devices[self.device_entity_id]
                
                # Try to determine power state from device info
                # This may vary depending on device type and Alexa API
                power_state = device_info.get('powerState', {}).get('value', 'unknown')
                
                if power_state.lower() == 'on':
                    return "on"
                elif power_state.lower() == 'off':
                    return "off"
                else:
                    self.logger.warning(f"Unknown power state: {power_state}")
                    return None
            else:
                self.logger.error("Device not found when checking power state")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting power state: {e}")
            return None
    
    async def ensure_on(self) -> bool:
        """
        Ensure TV is on. Only turn on if currently off.
        
        Returns:
            True if TV is on (was already on or successfully turned on)
        """
        current_state = await self.get_power_state()
        
        if current_state == "on":
            self.logger.info("TV already on")
            return True
        elif current_state == "off":
            return await self.turn_on()
        else:
            # Unknown state, try to turn on anyway
            self.logger.warning("Unknown power state, attempting to turn on")
            return await self.turn_on()
    
    async def ensure_off(self) -> bool:
        """
        Ensure TV is off. Only turn off if currently on.
        
        Returns:
            True if TV is off (was already off or successfully turned off)
        """
        current_state = await self.get_power_state()
        
        if current_state == "off":
            self.logger.info("TV already off")
            return True
        elif current_state == "on":
            return await self.turn_off()
        else:
            # Unknown state, try to turn off anyway
            self.logger.warning("Unknown power state, attempting to turn off")
            return await self.turn_off()
    
    def disconnect(self):
        """Clean up connections."""
        self.is_connected = False
        self.alexa = None
        self.login = None
        self.device_entity_id = None
        self.logger.info("Disconnected from Alexa")


# Synchronous wrapper functions for compatibility
class AlexaTVControlSync:
    """Synchronous wrapper for AlexaTVControl."""
    
    def __init__(self, amazon_email: str, amazon_password: str, device_name: str = "many paintings"):
        self.async_controller = AlexaTVControl(amazon_email, amazon_password, device_name)
        self.loop = None
        
    def _run_async(self, coro):
        """Run async function in sync context."""
        try:
            # Try to get existing event loop
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop, create one
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
        return self.loop.run_until_complete(coro)
    
    def connect(self) -> bool:
        """Connect to Alexa (sync version)."""
        return self._run_async(self.async_controller.connect())
    
    def turn_on(self) -> bool:
        """Turn on TV (sync version)."""
        return self._run_async(self.async_controller.turn_on())
    
    def turn_off(self) -> bool:
        """Turn off TV (sync version)."""
        return self._run_async(self.async_controller.turn_off())
    
    def get_power_state(self) -> Optional[str]:
        """Get power state (sync version)."""
        return self._run_async(self.async_controller.get_power_state())
    
    def ensure_on(self) -> bool:
        """Ensure TV is on (sync version)."""
        return self._run_async(self.async_controller.ensure_on())
    
    def ensure_off(self) -> bool:
        """Ensure TV is off (sync version)."""
        return self._run_async(self.async_controller.ensure_off())
    
    def disconnect(self):
        """Disconnect from Alexa."""
        self.async_controller.disconnect()


async def main():
    """Test script for Alexa TV control."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 4:
        print("Usage: python3 alexa_tv_control.py <email> <password> <command>")
        print("Commands: connect, on, off, status, ensure-on, ensure-off")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    command = sys.argv[3].lower()
    
    controller = AlexaTVControl(email, password)
    
    try:
        if command == "connect":
            success = await controller.connect()
            print(f"Connection: {'SUCCESS' if success else 'FAILED'}")
            
        elif command == "on":
            success = await controller.turn_on()
            print(f"Turn ON: {'SUCCESS' if success else 'FAILED'}")
            
        elif command == "off":
            success = await controller.turn_off()
            print(f"Turn OFF: {'SUCCESS' if success else 'FAILED'}")
            
        elif command == "status":
            state = await controller.get_power_state()
            print(f"Power State: {state if state else 'UNKNOWN'}")
            
        elif command == "ensure-on":
            success = await controller.ensure_on()
            print(f"Ensure ON: {'SUCCESS' if success else 'FAILED'}")
            
        elif command == "ensure-off":
            success = await controller.ensure_off()
            print(f"Ensure OFF: {'SUCCESS' if success else 'FAILED'}")
            
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())