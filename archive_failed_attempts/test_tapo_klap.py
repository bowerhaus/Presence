#!/usr/bin/env python3
"""
Test Tapo P100 with modern kasa library and KLAP protocol
"""

import asyncio
from kasa import Discover, Device, Credentials

async def test_tapo_modern():
    target_ip = "192.168.0.150"
    email = "bower@object-arts.com"
    password = "R0osh@Ry"
    
    try:
        print(f"Connecting to Tapo device at {target_ip}...")
        
        # Create credentials
        creds = Credentials(email, password)
        
        # Discover single device with credentials
        device = await Discover.discover_single(target_ip, credentials=creds)
        
        if device:
            print("✅ Device discovered!")
            print(f"Device: {device}")
            print(f"Model: {device.model}")
            
            # Connect and update
            await device.update()
            
            print(f"Device name: {device.alias}")
            print(f"Is on: {device.is_on}")
            
            # Test power control
            print("\nTesting power control...")
            
            if device.is_on:
                print("Turning OFF...")
                await device.turn_off()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after OFF: {device.is_on}")
                
                print("Turning ON...")
                await device.turn_on()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after ON: {device.is_on}")
            else:
                print("Turning ON...")
                await device.turn_on()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after ON: {device.is_on}")
                
                print("Turning OFF...")
                await device.turn_off()
                await asyncio.sleep(2)
                await device.update()
                print(f"State after OFF: {device.is_on}")
            
            print("✅ Power control test successful!")
            return True
        else:
            print("❌ Failed to discover device")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Tapo P100 with Modern Kasa Library")
    print("=" * 45)
    
    result = asyncio.run(test_tapo_modern())
    if result:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")