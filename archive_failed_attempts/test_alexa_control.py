#!/usr/bin/env python3
"""
Quick test script for Alexa TV control
Tests turning the device on and off via Amazon Alexa API
"""

import sys
import time
import logging
from alexa_tv_control import AlexaTVControlSync

def test_alexa_control():
    """Test Alexa device control"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Credentials from config.json
    amazon_email = "bower@object-arts.com"
    amazon_password = "Unvented 55@@ving55"
    device_name = "manypaintings"
    
    print("Alexa TV Control Test")
    print("=" * 30)
    print(f"Device: {device_name}")
    print(f"Email: {amazon_email}")
    print()
    
    # Create controller
    controller = AlexaTVControlSync(amazon_email, amazon_password, device_name)
    
    try:
        # Test connection
        print("1. Testing connection...")
        success = controller.connect()
        if not success:
            print("❌ Failed to connect to Alexa")
            return False
        print("✅ Connected to Alexa successfully")
        print()
        
        # Get initial state
        print("2. Getting initial device state...")
        initial_state = controller.get_power_state()
        print(f"Initial state: {initial_state}")
        print()
        
        # Test turning OFF
        print("3. Testing turn OFF...")
        success = controller.turn_off()
        if success:
            print("✅ Turn OFF command sent successfully")
        else:
            print("❌ Turn OFF command failed")
        print("Waiting 5 seconds...")
        time.sleep(5)
        
        # Check state after turn off
        state = controller.get_power_state()
        print(f"State after turn OFF: {state}")
        print()
        
        # Test turning ON
        print("4. Testing turn ON...")
        success = controller.turn_on()
        if success:
            print("✅ Turn ON command sent successfully")
        else:
            print("❌ Turn ON command failed")
        print("Waiting 5 seconds...")
        time.sleep(5)
        
        # Check final state
        final_state = controller.get_power_state()
        print(f"Final state: {final_state}")
        print()
        
        # Test ensure methods
        print("5. Testing ensure methods...")
        
        print("Testing ensure_off...")
        success = controller.ensure_off()
        print(f"Ensure OFF: {'✅ Success' if success else '❌ Failed'}")
        time.sleep(3)
        
        print("Testing ensure_on...")
        success = controller.ensure_on()
        print(f"Ensure ON: {'✅ Success' if success else '❌ Failed'}")
        time.sleep(3)
        
        print()
        print("🎉 Test completed!")
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        controller.disconnect()
        print("Disconnected from Alexa")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        # Quick command mode
        controller = AlexaTVControlSync("bower@object-arts.com", "Unvented 55@@ving55", "manypaintings")
        
        try:
            if command == "on":
                print("Turning device ON...")
                success = controller.turn_on()
                print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                
            elif command == "off":
                print("Turning device OFF...")
                success = controller.turn_off()
                print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                
            elif command == "status":
                print("Getting device status...")
                if controller.connect():
                    state = controller.get_power_state()
                    print(f"Device state: {state}")
                else:
                    print("❌ Failed to connect")
                    
            else:
                print(f"Unknown command: {command}")
                print("Usage: python3 test_alexa_control.py [on|off|status]")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            controller.disconnect()
    else:
        # Full test mode
        test_alexa_control()