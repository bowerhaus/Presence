#!/usr/bin/env python3
"""
Test Tapo P100 with plugp100 library (correct approach)
"""

import asyncio
import logging
from plugp100.common.credentials import AuthCredential
from plugp100.new.device_factory import connect, DeviceConnectConfiguration

async def test_tapo_with_factory():
    ip = "192.168.0.150"
    email = "bower@object-arts.com"
    password = "R0osh@Ry"
    
    try:
        print(f"Connecting to Tapo P100 at {ip}...")
        
        # Create credentials
        credentials = AuthCredential(email, password)
        
        # Create device configuration
        device_config = DeviceConnectConfiguration(
            host=ip,
            credentials=credentials,
            device_type="SMART.TAPOPLUG",
            encryption_type="klap",
            encryption_version=2,
        )
        
        # Connect to device
        print("Connecting...")
        device = await connect(device_config)
        
        # Update device state
        print("Updating device state...")
        await device.update()
        
        print("✅ Connected successfully!")
        print(f"Device type: {type(device)}")
        print(f"Protocol: {device.protocol_version}")
        print(f"Raw state: {device.raw_state}")
        
        # Try to get power state
        if hasattr(device, 'is_on'):
            is_on = device.is_on
            print(f"Current state: {'ON' if is_on else 'OFF'}")
            
            # Test power control
            print("\nTesting power control...")
            
            if is_on:
                print("Turning OFF...")
                await device.off()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after OFF: {'ON' if device.is_on else 'OFF'}")
                
                print("Turning ON...")
                await device.on()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after ON: {'ON' if device.is_on else 'OFF'}")
            else:
                print("Turning ON...")
                await device.on()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after ON: {'ON' if device.is_on else 'OFF'}")
                
                print("Turning OFF...")
                await device.off()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after OFF: {'ON' if device.is_on else 'OFF'}")
            
            print("✅ Power control test successful!")
        else:
            print("Device doesn't have is_on attribute, checking raw_state...")
            print(f"Raw state: {device.raw_state}")
        
        # Close connection
        await device.client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Tapo P100 with plugp100 Device Factory")
    print("=" * 50)
    
    result = asyncio.run(test_tapo_with_factory())
    if result:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")