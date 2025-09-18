#!/usr/bin/env python3
"""
Test Tapo P100 with plugp100 library (KLAP protocol)
"""

import asyncio
from plugp100.new.tapodevice import TapoDevice
from plugp100.api.tapo_client import TapoClient
from plugp100.common.credentials import AuthCredential

async def test_tapo_plugp100():
    ip = "192.168.0.150"
    email = "bower@object-arts.com"
    password = "R0osh@Ry"
    
    try:
        print(f"Connecting to Tapo P100 at {ip}...")
        
        # Create credentials
        credential = AuthCredential(email, password)
        
        # Create client
        client = TapoClient.create(credential)
        
        # Create device
        device = TapoDevice(ip, 80, client)
        
        # Get device info
        print("Getting device info...")
        device_info = await device.get_device_info()
        print(f"✅ Connected! Device: {device_info}")
        
        # Get current state
        print("Getting current state...")
        state = await device.get_state()
        print(f"Current state: {state}")
        
        is_on = state.get('device_on', False)
        print(f"Device is: {'ON' if is_on else 'OFF'}")
        
        # Test power control
        print("\nTesting power control...")
        
        if is_on:
            print("Turning OFF...")
            await device.off()
            await asyncio.sleep(2)
            
            print("Checking state after OFF...")
            state = await device.get_state()
            print(f"State after OFF: {'ON' if state.get('device_on', False) else 'OFF'}")
            
            print("Turning ON...")
            await device.on()
            await asyncio.sleep(2)
            
            print("Checking state after ON...")
            state = await device.get_state()
            print(f"State after ON: {'ON' if state.get('device_on', False) else 'OFF'}")
        else:
            print("Turning ON...")
            await device.on()
            await asyncio.sleep(2)
            
            print("Checking state after ON...")
            state = await device.get_state()
            print(f"State after ON: {'ON' if state.get('device_on', False) else 'OFF'}")
            
            print("Turning OFF...")
            await device.off()
            await asyncio.sleep(2)
            
            print("Checking state after OFF...")
            state = await device.get_state()
            print(f"State after OFF: {'ON' if state.get('device_on', False) else 'OFF'}")
        
        print("✅ Power control test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Tapo P100 with plugp100 Library")
    print("=" * 40)
    
    result = asyncio.run(test_tapo_plugp100())
    if result:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")