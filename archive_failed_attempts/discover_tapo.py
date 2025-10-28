#!/usr/bin/env python3
"""
Discover and test Tapo P100 smart plug
"""

import sys
from PyP100 import PyP100

def test_tapo_connection(ip, email, password):
    """Test connection to Tapo plug"""
    try:
        print(f"Attempting to connect to Tapo plug at {ip}...")
        
        # Create P100 device
        p100 = PyP100.P100(ip, email, password)
        
        # Handshake
        print("Performing handshake...")
        p100.handshake()
        
        # Login
        print("Logging in...")
        p100.login()
        
        # Get device info
        print("Getting device info...")
        info = p100.getDeviceInfo()
        
        if info and 'result' in info:
            device = info['result']
            print("\n✅ Successfully connected to Tapo plug!")
            print(f"Device Name: {device.get('nickname', 'Unknown')}")
            print(f"Device ID: {device.get('device_id', 'Unknown')}")
            print(f"Model: {device.get('model', 'Unknown')}")
            print(f"Current State: {'ON' if device.get('device_on', False) else 'OFF'}")
            print(f"MAC Address: {device.get('mac', 'Unknown')}")
            print(f"Hardware Version: {device.get('hw_ver', 'Unknown')}")
            print(f"Firmware Version: {device.get('fw_ver', 'Unknown')}")
            
            # Test power control
            test = input("\nTest power control? (y/n): ").lower()
            if test == 'y':
                current_state = device.get('device_on', False)
                
                # Toggle state
                if current_state:
                    print("Turning OFF...")
                    p100.turnOff()
                else:
                    print("Turning ON...")
                    p100.turnOn()
                
                print("Power command sent successfully!")
                
                # Toggle back
                toggle_back = input("Toggle back to original state? (y/n): ").lower()
                if toggle_back == 'y':
                    if current_state:
                        print("Turning back ON...")
                        p100.turnOn()
                    else:
                        print("Turning back OFF...")
                        p100.turnOff()
                    print("Restored original state!")
            
            return True
        else:
            print("❌ Failed to get device info")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("Tapo P100 Discovery and Test Tool")
    print("=" * 40)
    
    # Get connection details
    ip = input("Enter Tapo plug IP address (e.g., 192.168.0.100): ").strip()
    email = input("Enter TP-Link account email: ").strip()
    password = input("Enter TP-Link account password: ").strip()
    
    if not all([ip, email, password]):
        print("Error: All fields are required!")
        sys.exit(1)
    
    # Test connection
    if test_tapo_connection(ip, email, password):
        print(f"\n✅ Success! Your Tapo plug at {ip} is working correctly.")
        print("\nAdd these settings to your config.json:")
        print(f'''
  "tv_control": {{
    "type": "tapo",
    "plug_ip": "{ip}",
    "email": "{email}",
    "password": "<your-password>",
    "turn_off_delay": 600,
    "turn_on_delay": 0,
    "boot_wait_time": 15
  }}
        ''')
    else:
        print("\n❌ Failed to connect to Tapo plug.")
        print("\nTroubleshooting tips:")
        print("1. Ensure the Tapo plug is on the same network")
        print("2. Check the IP address is correct")
        print("3. Verify your TP-Link email and password")
        print("4. Make sure the plug is set up in the Tapo app")

if __name__ == "__main__":
    main()