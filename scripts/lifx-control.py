#!/usr/bin/env python3
"""
LIFX LAN Control Script for Enchantify
Controls LIFX bulbs over local network using lifxlan library

Usage:
    python3 lifx-control.py power on
    python3 lifx-control.py power off
    python3 lifx-control.py color 8000 25000 45000 3000    # hue, saturation, brightness, kelvin
    python3 lifx-control.py scene academy
    python3 lifx-control.py scene nothing
    python3 lifx-control.py scene compass-north
    python3 lifx-control.py scene compass-south
    python3 lifx-control.py scene compass-west
    python3 lifx-control.py scene compass-complete

LIFX Hue Scale (0-65535):
    0 = red, ~8000 = orange/amber, ~15000 = yellow, ~32768 = green
    ~43690 = blue, ~50000+ = purple/magenta
"""

import sys
from pathlib import Path
from lifxlan import LifxLAN, Light


def load_config() -> dict:
    cfg = {}
    config_path = Path(__file__).parent / "enchantify-config.sh"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"')
    return cfg


def get_devices(cfg: dict):
    """Return LIFX devices. Uses targeted IPs from config if set — much faster than broadcast."""
    ips_str = cfg.get("ENCHANTIFY_LIFX_IPS", "").strip()
    if ips_str:
        devices = []
        for ip in ips_str.split(","):
            ip = ip.strip()
            if not ip:
                continue
            try:
                # lifxlan accepts a placeholder MAC when IP is known
                light = Light("00:00:00:00:00:00", ip)
                light.get_label()  # confirms reachable
                devices.append(light)
            except Exception:
                pass
        if devices:
            return devices
        print("  ⚠ Configured IPs unreachable — falling back to LAN discovery...")

    # Broadcast discovery; num_lights hint makes it exit early
    count_str = cfg.get("ENCHANTIFY_LIFX_COUNT", "")
    count = int(count_str) if count_str.isdigit() else None
    lifx = LifxLAN(count)
    return lifx.get_lights()

# Scene definitions (hue, saturation, brightness, kelvin)
# Hue: 0-65535 (0=red, 8000=amber, 15000=yellow, 32768=green, 43690=blue, 50000+=purple)
# Sat: 0-65535 (0=gray/white, 65535=full saturation)
# Brightness: 0-65535
# Kelvin: 2500-9000 (2500=warm, 9000=cool)
SCENES = {
    'academy': (8000, 25000, 45000, 3000),        # Warm amber, comfortable
    'library': (45000, 20000, 35000, 4000),       # Soft blue-purple
    'nothing': (43690, 5000, 15000, 6500),        # Cold blue-white, dim
    'compass-north': (0, 0, 50000, 3500),         # Warm white, bright
    'compass-east': (0, 0, 60000, 4500),          # Daylight mode
    'compass-south': (8000, 10000, 30000, 2700),  # Soft warm meditative
    'compass-west': (0, 0, 20000, 2700),          # Single warm light, dim
    'compass-complete': (10000, 20000, 55000, 3000), # Golden sunrise
    'book-snow-queen': (43690, 15000, 40000, 6500), # Ice white, cool blue
    'book-odyssey': (8000, 15000, 45000, 3200),   # Warm Mediterranean gold
    'bookend': (50000, 25000, 35000, 3000),       # Purple-pink sunset
    'defeated': (8000, 20000, 60000, 3000),       # Warm burst
}

def main():
    if len(sys.argv) < 2:
        print("Usage: lifx-control.py <command> [args]")
        print("Commands: power, color, scene, list")
        sys.exit(1)

    command = sys.argv[1].lower()
    cfg = load_config()
    devices = get_devices(cfg)

    if not devices:
        print("No LIFX bulbs found on network")
        sys.exit(1)
    
    print(f"Controlling {len(devices)} bulb(s):")
    for device in devices:
        print(f"  - {device.get_label()}")
    
    if command == 'power':
        if len(sys.argv) < 3:
            print("Usage: lifx-control.py power <on|off>")
            sys.exit(1)
        state = sys.argv[2].lower() == 'on'
        for device in devices:
            device.set_power(state)
        print(f"Power: {'ON' if state else 'OFF'}")
    
    elif command == 'color':
        if len(sys.argv) < 5:
            print("Usage: lifx-control.py color <hue> <sat> <bright> [kelvin]")
            sys.exit(1)
        hue = int(sys.argv[2])
        sat = int(sys.argv[3])
        bright = int(sys.argv[4])
        kelvin = int(sys.argv[5]) if len(sys.argv) > 5 else 3500
        for device in devices:
            device.set_color((hue, sat, bright, kelvin), duration=1)
        print(f"Color: H={hue}, S={sat}, B={bright}, K={kelvin}")
    
    elif command == 'scene':
        if len(sys.argv) < 3:
            print("Usage: lifx-control.py scene <scene-name>")
            print(f"Available: {', '.join(SCENES.keys())}")
            sys.exit(1)
        scene = sys.argv[2].lower()
        if scene not in SCENES:
            print(f"Unknown scene: {scene}")
            print(f"Available: {', '.join(SCENES.keys())}")
            sys.exit(1)
        hue, sat, bright, kelvin = SCENES[scene]
        for device in devices:
            device.set_color((hue, sat, bright, kelvin), duration=1)
        print(f"Scene: {scene}")
    
    elif command == 'list':
        print("\nBulb details:")
        for device in devices:
            print(f"  {device.get_label()}:")
            print(f"    IP: {device.get_ip_addr()}")
            print(f"    Power: {device.get_power()}")
            color = device.get_color()
            print(f"    Color: H={color[0]}, S={color[1]}, B={color[2]}, K={color[3]}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
