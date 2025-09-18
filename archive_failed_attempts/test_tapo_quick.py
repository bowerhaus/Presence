#!/usr/bin/env python3
"""
Quick Tapo P100 test script
Edit the credentials below and run this script
"""

from PyP100 import PyP100

# EDIT THESE VALUES:
TAPO_IP = "192.168.0.150"
TPLINK_EMAIL = "bower@object-arts.com"  # Replace with your TP-Link email
TPLINK_PASSWORD = "R0osh@Ry"        # Replace with your TP-Link password

def test_tapo():
    try:
        print(f"Testing Tapo plug at {TAPO_IP}...")
        
        # Create P100 device
        p100 = PyP100.P100(TAPO_IP, TPLINK_EMAIL, TPLINK_PASSWORD)
        
        # Connect
        print("Connecting...")
        p100.handshake()
        p100.login()
        print("✅ Connected successfully!")
        
        # Get info and debug the response
        print("Getting device info...")
        info = p100.getDeviceInfo()
        print(f"Raw response: {info}")
        print(f"Response type: {type(info)}")
        if info:
            print(f"Response keys: {list(info.keys()) if isinstance(info, dict) else 'Not a dict'}")
        
        # Try to find device info in different formats
        device = None
        if isinstance(info, dict):
            if 'result' in info:
                device = info['result']
                print("Found device info in 'result' key")
            elif 'device_info' in info:
                device = info['device_info']
                print("Found device info in 'device_info' key")
            else:
                # Maybe the info IS the device data
                device = info
                print("Using info directly as device data")
        
        if device:
            print("✅ SUCCESS!")
            print(f"Device: {device.get('nickname', device.get('alias', 'Unknown'))}")
            print(f"State: {'ON' if device.get('device_on', False) else 'OFF'}")
            
            # Test basic control
            current_state = device.get('device_on', False)
            print(f"\nCurrent state: {'ON' if current_state else 'OFF'}")
            
            # Test turning off then on
            print("Testing power control...")
            p100.turnOff()
            print("Turned OFF")
            import time
            time.sleep(2)
            
            p100.turnOn()
            print("Turned ON")
            time.sleep(1)
            
            print("✅ Power control test successful!")
            return True
        else:
            print("❌ Could not find device data in response")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Tapo P100 Quick Test")
    print("=" * 30)
    
    if TPLINK_EMAIL == "your-email@example.com":
        print("❌ Please edit the script and add your TP-Link credentials!")
        print("Edit test_tapo_quick.py and replace:")
        print("- TPLINK_EMAIL with your actual email")
        print("- TPLINK_PASSWORD with your actual password")
    else:
        test_tapo()