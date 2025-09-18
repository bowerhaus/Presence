#!/usr/bin/env python3
"""
Test Tapo P100 with python-kasa library
"""

import asyncio
from kasa import Discover, SmartPlug

async def test_tapo_with_kasa():
    # Discover devices
    print("Discovering devices...")
    devices = await Discover.discover()
    
    # Find our device
    target_ip = "192.168.0.150"
    device = None
    
    for ip, dev_info in devices.items():
        print(f"Found device at {ip}: {dev_info}")
        if ip == target_ip:
            device = dev_info
            break
    
    if not device:
        print(f"Device at {target_ip} not found in discovery")
        return False
    
    # Try to connect with credentials
    print(f"Connecting to device at {target_ip}...")
    try:
        # Try creating a smart plug instance
        plug = SmartPlug(target_ip)
        
        # Set credentials
        # Note: newer kasa library may handle this differently
        await plug.update()
        
        print("✅ Connected successfully!")
        print(f"Device info: {plug.model}")
        print(f"Is on: {plug.is_on}")
        
        # Test control
        print("Testing power control...")
        if plug.is_on:
            await plug.turn_off()
            print("Turned OFF")
            await asyncio.sleep(2)
            await plug.turn_on()
            print("Turned ON")
        else:
            await plug.turn_on()
            print("Turned ON")
            await asyncio.sleep(2)
            await plug.turn_off()
            print("Turned OFF")
        
        return True
        
    except Exception as e:
        print(f"❌ Error connecting: {e}")
        return False

if __name__ == "__main__":
    print("Testing Tapo P100 with python-kasa")
    print("=" * 40)
    
    result = asyncio.run(test_tapo_with_kasa())
    if result:
        print("✅ Test successful!")
    else:
        print("❌ Test failed!")