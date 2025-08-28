#!/usr/bin/env python3

import socket
import json
import logging
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any

try:
    from samsungtvws import SamsungTVWS
except ImportError:
    print("Error: samsungtvws library not found. Please install it with:")
    print("pip install samsungtvws[async,encrypted]")
    exit(1)


class SamsungTVDiscovery:
    """Discover Samsung TVs on the local network"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
    
    def get_network_range(self) -> List[str]:
        """Get the local network range to scan"""
        try:
            # Get the default gateway
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    gateway = parts[2]
                    # Extract network from gateway (assume /24)
                    network_base = '.'.join(gateway.split('.')[:-1])
                    return [f"{network_base}.{i}" for i in range(1, 255)]
        except Exception as e:
            self.logger.error(f"Failed to get network range: {e}")
        
        # Fallback to common ranges
        return [f"192.168.1.{i}" for i in range(1, 255)]
    
    def check_samsung_tv(self, ip: str, port: int = 8002) -> Optional[Dict[str, Any]]:
        """Check if a Samsung TV is at the given IP"""
        try:
            # Quick port check first
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result != 0:
                return None
            
            # Try to connect with Samsung TV API
            tv = SamsungTVWS(host=ip, port=port, timeout=3)
            info = tv.rest_device_info()
            
            if info and 'device' in info:
                device = info['device']
                return {
                    'ip': ip,
                    'port': port,
                    'name': device.get('name', 'Unknown Samsung TV'),
                    'model': device.get('modelName', 'Unknown'),
                    'version': device.get('version', 'Unknown'),
                    'device_info': info
                }
                
        except Exception as e:
            self.logger.debug(f"No Samsung TV at {ip}: {e}")
        
        return None
    
    def discover_tvs(self, max_workers: int = 50) -> List[Dict[str, Any]]:
        """Discover Samsung TVs on the network"""
        self.logger.info("Scanning network for Samsung TVs...")
        
        network_ips = self.get_network_range()
        found_tvs = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(self.check_samsung_tv, ip): ip 
                for ip in network_ips
            }
            
            completed = 0
            total = len(future_to_ip)
            
            for future in as_completed(future_to_ip):
                completed += 1
                if completed % 20 == 0:
                    self.logger.info(f"Scanned {completed}/{total} IPs...")
                
                result = future.result()
                if result:
                    found_tvs.append(result)
                    self.logger.info(f"Found Samsung TV: {result['name']} at {result['ip']}")
        
        return found_tvs
    
    def update_config(self, tv_info: Dict[str, Any], config_path: str = "config.json"):
        """Update config.json with discovered TV information"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            config['samsung_tv']['ip_address'] = tv_info['ip']
            config['samsung_tv']['port'] = tv_info['port']
            
            # Try to get MAC address for Wake-on-LAN
            try:
                result = subprocess.run(['arp', '-n', tv_info['ip']], 
                                      capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if tv_info['ip'] in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', parts[2])
                            if mac_match:
                                config['samsung_tv']['mac_address'] = mac_match.group(0)
                                config['samsung_tv']['wake_on_lan'] = True
                                break
            except Exception:
                self.logger.warning("Could not determine MAC address for Wake-on-LAN")
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info(f"Updated {config_path} with TV configuration")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
            return False


def main():
    """Main discovery function"""
    print("Samsung TV Discovery Tool")
    print("=" * 40)
    
    discovery = SamsungTVDiscovery()
    tvs = discovery.discover_tvs()
    
    if not tvs:
        print("\nNo Samsung TVs found on the network.")
        print("Make sure your TV is:")
        print("- Connected to the same network")
        print("- Powered on")
        print("- Has Smart Hub features enabled")
        return
    
    print(f"\nFound {len(tvs)} Samsung TV(s):")
    print("-" * 40)
    
    for i, tv in enumerate(tvs, 1):
        print(f"{i}. {tv['name']}")
        print(f"   IP: {tv['ip']}")
        print(f"   Model: {tv['model']}")
        print(f"   Version: {tv['version']}")
        print()
    
    if len(tvs) == 1:
        choice = input("Update config.json with this TV? (y/n): ").lower()
        if choice == 'y':
            success = discovery.update_config(tvs[0])
            if success:
                print("Configuration updated successfully!")
                print(f"You can now test the connection with:")
                print(f"python3 samsung_tv_control.py")
    else:
        try:
            choice = int(input("Select TV to use (1-{}): ".format(len(tvs))))
            if 1 <= choice <= len(tvs):
                selected_tv = tvs[choice - 1]
                success = discovery.update_config(selected_tv)
                if success:
                    print("Configuration updated successfully!")
                    print(f"You can now test the connection with:")
                    print(f"python3 samsung_tv_control.py")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")


if __name__ == "__main__":
    main()