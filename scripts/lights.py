#!/usr/bin/env python3
"""
lights.py — Smart light control for Enchantify.

Replaces lifx-control.py. Supports multiple backends and any color input —
not just named presets. The Labyrinth can call this with a hex code, an HSB
value, a color temperature, a CSS name, or a named scene.

Backends (in priority order from LIGHTS_BACKEND config):
  lifx     — LIFX bulbs over LAN (no hub, fastest)
  ha       — Home Assistant REST (covers Matter, HomeKit, LIFX, Hue, everything)
  hue      — Philips Hue bridge REST
  homekit  — macOS Shortcuts CLI (scene-level only; arbitrary color needs ha backend)

Usage:
  python3 scripts/lights.py scene library
  python3 scripts/lights.py scene nothing
  python3 scripts/lights.py set --color "#FF6B35"
  python3 scripts/lights.py set --color "deep violet" --bright 60
  python3 scripts/lights.py set --color "warm amber"
  python3 scripts/lights.py set --hue 240 --sat 80 --bright 70
  python3 scripts/lights.py set --kelvin 2700 --bright 85
  python3 scripts/lights.py set --color "#C0A0FF" --kelvin 3200 --transition 3
  python3 scripts/lights.py off
  python3 scripts/lights.py on
  python3 scripts/lights.py test
  python3 scripts/lights.py status
  python3 scripts/lights.py list-scenes
  python3 scripts/lights.py --backend lifx scene library
"""

import os
import re
import sys
import json
import math
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

SCRIPT_DIR    = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent


# ── Universal color format ─────────────────────────────────────────────────────
# All internal colors are dicts with these keys (all optional with defaults):
#   hue:        0–360  (degrees, 0=red, 120=green, 240=blue)
#   sat:        0–100  (percent)
#   bright:     0–100  (percent)
#   kelvin:     2500–9000
#   transition: seconds (float)

DEFAULT_KELVIN     = 3200
DEFAULT_BRIGHT     = 80
DEFAULT_TRANSITION = 1.5


# ── Named scenes ──────────────────────────────────────────────────────────────
# Universal format. hue=0 + sat=0 means white (kelvin-only).
# These are starting points — the Labyrinth can always call `set` for anything else.

SCENES: dict[str, dict] = {
    # Academy spaces
    "academy":          {"hue": 30,  "sat": 55, "bright": 90, "kelvin": 3000, "transition": 1.5},
    "library":          {"hue": 220, "sat": 25, "bright": 55, "kelvin": 4000, "transition": 2.0},
    "dorm":             {"hue": 25,  "sat": 40, "bright": 70, "kelvin": 2800, "transition": 1.5},
    "great-hall":       {"hue": 35,  "sat": 50, "bright": 85, "kelvin": 3200, "transition": 2.0},
    "outer-stacks":     {"hue": 270, "sat": 30, "bright": 45, "kelvin": 4500, "transition": 3.0},

    # Narrative states
    "nothing":          {"hue": 210, "sat": 15, "bright": 20, "kelvin": 6500, "transition": 3.0},
    "defeated":         {"hue": 35,  "sat": 60, "bright": 100,"kelvin": 3000, "transition": 0.5},
    "tension":          {"hue": 0,   "sat": 30, "bright": 35, "kelvin": 5000, "transition": 2.5},
    "wonder":           {"hue": 280, "sat": 50, "bright": 75, "kelvin": 4000, "transition": 2.0},
    "revelation":       {"hue": 55,  "sat": 70, "bright": 95, "kelvin": 3500, "transition": 1.0},

    # Compass directions
    "compass-north":    {"hue": 0,   "sat": 0,  "bright": 90, "kelvin": 3500, "transition": 1.5},
    "compass-east":     {"hue": 0,   "sat": 0,  "bright": 100,"kelvin": 5000, "transition": 1.0},
    "compass-south":    {"hue": 25,  "sat": 20, "bright": 55, "kelvin": 2700, "transition": 2.0},
    "compass-west":     {"hue": 0,   "sat": 0,  "bright": 30, "kelvin": 2700, "transition": 2.5},
    "compass-complete": {"hue": 42,  "sat": 65, "bright": 100,"kelvin": 3000, "transition": 0.8},

    # Book jumps
    "book-snow-queen":  {"hue": 210, "sat": 30, "bright": 65, "kelvin": 7000, "transition": 2.0},
    "book-odyssey":     {"hue": 32,  "sat": 55, "bright": 90, "kelvin": 3200, "transition": 1.5},
    "bookend":          {"hue": 300, "sat": 40, "bright": 70, "kelvin": 3000, "transition": 2.0},

    # Chapter talismans
    "emberheart":       {"hue": 15,  "sat": 80, "bright": 85, "kelvin": 2800, "transition": 2.0},
    "mossbloom":        {"hue": 130, "sat": 55, "bright": 65, "kelvin": 3500, "transition": 3.0},
    "riddlewind":       {"hue": 55,  "sat": 45, "bright": 75, "kelvin": 4000, "transition": 2.5},
    "tidecrest":        {"hue": 200, "sat": 60, "bright": 70, "kelvin": 5000, "transition": 2.5},
    "duskthorn":        {"hue": 270, "sat": 35, "bright": 30, "kelvin": 5500, "transition": 3.0},
}

# Aliases so ambient-state.py chapter mappings work
SCENE_ALIASES = {
    "compass-complete": "compass-complete",
    "compass-north":    "compass-north",
    "compass-east":     "compass-east",
    "compass-south":    "compass-south",
    "compass-west":     "compass-west",
}


# ── CSS named colors (subset — common + narrative-useful) ─────────────────────
# Maps lowercase name → (R, G, B) 0-255

CSS_COLORS: dict[str, tuple] = {
    "red": (255, 0, 0), "crimson": (220, 20, 60), "firebrick": (178, 34, 34),
    "darkred": (139, 0, 0), "orangered": (255, 69, 0), "tomato": (255, 99, 71),
    "coral": (255, 127, 80), "salmon": (250, 128, 114), "orange": (255, 165, 0),
    "darkorange": (255, 140, 0), "amber": (255, 191, 0), "gold": (255, 215, 0),
    "yellow": (255, 255, 0), "khaki": (240, 230, 140), "lemonchiffon": (255, 250, 205),
    "yellowgreen": (154, 205, 50), "limegreen": (50, 205, 50), "lime": (0, 255, 0),
    "green": (0, 128, 0), "darkgreen": (0, 100, 0), "forestgreen": (34, 139, 34),
    "seagreen": (46, 139, 87), "teal": (0, 128, 128), "darkcyan": (0, 139, 139),
    "cyan": (0, 255, 255), "aqua": (0, 255, 255), "lightcyan": (224, 255, 255),
    "lightblue": (173, 216, 230), "skyblue": (135, 206, 235), "cornflowerblue": (100, 149, 237),
    "royalblue": (65, 105, 225), "blue": (0, 0, 255), "mediumblue": (0, 0, 205),
    "darkblue": (0, 0, 139), "navy": (0, 0, 128), "midnightblue": (25, 25, 112),
    "blueviolet": (138, 43, 226), "indigo": (75, 0, 130), "darkviolet": (148, 0, 211),
    "violet": (238, 130, 238), "purple": (128, 0, 128), "darkmagenta": (139, 0, 139),
    "magenta": (255, 0, 255), "fuchsia": (255, 0, 255), "orchid": (218, 112, 214),
    "plum": (221, 160, 221), "pink": (255, 192, 203), "hotpink": (255, 105, 180),
    "deeppink": (255, 20, 147), "white": (255, 255, 255), "ghostwhite": (248, 248, 255),
    "ivory": (255, 255, 240), "seashell": (255, 245, 238), "linen": (250, 240, 230),
    "snow": (255, 250, 250), "floralwhite": (255, 250, 240), "oldlace": (253, 245, 230),
    "antiquewhite": (250, 235, 215), "bisque": (255, 228, 196), "peachpuff": (255, 218, 185),
    "mistyrose": (255, 228, 225), "lavender": (230, 230, 250), "lavenderblush": (255, 240, 245),
    "aliceblue": (240, 248, 255), "azure": (240, 255, 255), "honeydew": (240, 255, 240),
    "mintcream": (245, 255, 250), "beige": (245, 245, 220), "wheat": (245, 222, 179),
    "tan": (210, 180, 140), "burlywood": (222, 184, 135), "peru": (205, 133, 63),
    "chocolate": (210, 105, 30), "saddlebrown": (139, 69, 19), "sienna": (160, 82, 45),
    "brown": (165, 42, 42), "maroon": (128, 0, 0), "rosybrown": (188, 143, 143),
    "dimgray": (105, 105, 105), "gray": (128, 128, 128), "darkgray": (169, 169, 169),
    "silver": (192, 192, 192), "lightgray": (211, 211, 211), "gainsboro": (220, 220, 220),
    "black": (0, 0, 0),
    # Narrative extras
    "warm amber": (255, 180, 50), "deep violet": (80, 0, 160), "midnight blue": (25, 25, 112),
    "ice white": (200, 230, 255), "golden": (255, 200, 0), "emerald": (0, 200, 100),
    "rose gold": (255, 150, 120), "electric blue": (0, 100, 255), "neon green": (50, 255, 50),
    "blood red": (180, 0, 0), "dusk": (80, 50, 120), "dawn": (255, 180, 120),
    "fog": (200, 210, 220), "ember": (255, 80, 20), "ash": (150, 150, 160),
    "forest": (30, 100, 30), "ocean": (20, 100, 180), "candle": (255, 160, 60),
    "moonlight": (200, 210, 240), "sunlight": (255, 240, 180), "starlight": (180, 190, 255),
}


# ── Color parsing ─────────────────────────────────────────────────────────────

def rgb_to_hsb(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB (0-255) to HSB (hue 0-360, sat 0-100, bright 0-100)."""
    r_, g_, b_ = r / 255, g / 255, b / 255
    cmax = max(r_, g_, b_)
    cmin = min(r_, g_, b_)
    delta = cmax - cmin

    bright = cmax * 100
    sat = (delta / cmax * 100) if cmax != 0 else 0

    if delta == 0:
        hue = 0.0
    elif cmax == r_:
        hue = 60 * (((g_ - b_) / delta) % 6)
    elif cmax == g_:
        hue = 60 * ((b_ - r_) / delta + 2)
    else:
        hue = 60 * ((r_ - g_) / delta + 4)

    return round(hue, 1), round(sat, 1), round(bright, 1)


def parse_color_spec(spec: str) -> Optional[dict]:
    """Parse a color string into universal format dict.

    Accepts:
      "#FF6B35"          hex
      "FF6B35"           hex without hash
      "warm amber"       CSS or narrative name
      "hue:240,sat:80"   explicit components
    Returns dict with hue/sat/bright keys, or None if unparseable.
    """
    spec = spec.strip()

    # Hex
    hex_m = re.match(r'^#?([0-9a-fA-F]{6})$', spec)
    if hex_m:
        h = hex_m.group(1)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        hue, sat, bright = rgb_to_hsb(r, g, b)
        return {"hue": hue, "sat": sat, "bright": bright}

    # CSS / narrative name (exact match first, then fuzzy)
    lower = spec.lower()
    if lower in CSS_COLORS:
        r, g, b = CSS_COLORS[lower]
        hue, sat, bright = rgb_to_hsb(r, g, b)
        return {"hue": hue, "sat": sat, "bright": bright}

    # Fuzzy: find the CSS entry whose name has the most words in common
    spec_words = set(lower.split())
    best_score, best_name = 0, None
    for name in CSS_COLORS:
        score = len(spec_words & set(name.split()))
        if score > best_score:
            best_score, best_name = score, name
    if best_score > 0 and best_name:
        r, g, b = CSS_COLORS[best_name]
        hue, sat, bright = rgb_to_hsb(r, g, b)
        return {"hue": hue, "sat": sat, "bright": bright}

    return None


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    for path in [
        WORKSPACE_DIR / "config" / "secrets.env",
        Path(__file__).parent / "enchantify-config.sh",
    ]:
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    cfg[key.strip()] = val.strip().strip('"').strip("'")
    return cfg


# ── Backend: LIFX LAN ─────────────────────────────────────────────────────────

def _lifx_set(color: dict, cfg: dict) -> bool:
    try:
        from lifxlan import LifxLAN, Light
    except ImportError:
        print("  ⚠ lifxlan not installed: pip3 install lifxlan")
        return False

    # Discover devices
    ips_str = cfg.get("ENCHANTIFY_LIFX_IPS", "").strip()
    devices = []
    if ips_str:
        for ip in ips_str.split(","):
            ip = ip.strip()
            if not ip:
                continue
            try:
                light = Light("00:00:00:00:00:00", ip)
                light.get_label()
                devices.append(light)
            except Exception:
                pass

    if not devices:
        count_hint = cfg.get("ENCHANTIFY_LIFX_COUNT", "")
        count = int(count_hint) if count_hint.isdigit() else None
        lifx = LifxLAN(count)
        devices = lifx.get_lights()

    if not devices:
        print("  ⚠ No LIFX bulbs found on network.")
        return False

    hue    = int(color.get("hue",    0)   / 360  * 65535)
    sat    = int(color.get("sat",    0)   / 100  * 65535)
    bright = int(color.get("bright", DEFAULT_BRIGHT) / 100 * 65535)
    kelvin = int(color.get("kelvin", DEFAULT_KELVIN))
    dur_ms = int(color.get("transition", DEFAULT_TRANSITION) * 1000)

    kelvin = max(2500, min(9000, kelvin))

    for device in devices:
        try:
            device.set_power(True)
            device.set_color((hue, sat, bright, kelvin), duration=dur_ms)
        except Exception as e:
            print(f"  ⚠ LIFX error ({device}): {e}")

    labels = []
    for d in devices:
        try:
            labels.append(d.get_label())
        except Exception:
            labels.append("?")
    print(f"  ✓ LIFX → {', '.join(labels)}")
    return True


def _lifx_power(on: bool, cfg: dict) -> bool:
    try:
        from lifxlan import LifxLAN, Light
    except ImportError:
        return False

    ips_str = cfg.get("ENCHANTIFY_LIFX_IPS", "").strip()
    devices = []
    if ips_str:
        for ip in ips_str.split(","):
            ip = ip.strip()
            if not ip:
                continue
            try:
                light = Light("00:00:00:00:00:00", ip)
                light.get_label()
                devices.append(light)
            except Exception:
                pass
    if not devices:
        count_hint = cfg.get("ENCHANTIFY_LIFX_COUNT", "")
        count = int(count_hint) if count_hint.isdigit() else None
        devices = LifxLAN(count).get_lights()

    for device in devices:
        try:
            device.set_power(on)
        except Exception:
            pass
    print(f"  ✓ LIFX power {'ON' if on else 'OFF'}")
    return bool(devices)


# ── Backend: Home Assistant ───────────────────────────────────────────────────

def _ha_request(method: str, path: str, body: Optional[dict], cfg: dict) -> Optional[dict]:
    url   = cfg.get("HA_URL", "").rstrip("/")
    token = cfg.get("HA_TOKEN", "")
    if not url or not token:
        return None

    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(
        f"{url}/api/{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠ HA request failed: {e}")
        return None


def _ha_set(color: dict, cfg: dict) -> bool:
    entities_str = cfg.get("ENCHANTIFY_HA_LIGHT_ENTITIES", "")
    if not entities_str:
        # Try to discover light entities
        result = _ha_request("GET", "states", None, cfg)
        if result:
            lights = [e["entity_id"] for e in result
                      if e.get("entity_id", "").startswith("light.")]
            entities_str = ",".join(lights[:8])  # cap at 8

    if not entities_str:
        print("  ⚠ No HA light entities configured (ENCHANTIFY_HA_LIGHT_ENTITIES)")
        return False

    hue    = color.get("hue",    None)
    sat    = color.get("sat",    None)
    bright = color.get("bright", DEFAULT_BRIGHT)
    kelvin = color.get("kelvin", None)
    dur_s  = color.get("transition", DEFAULT_TRANSITION)

    service_data: dict = {
        "brightness": int(bright / 100 * 255),
        "transition": dur_s,
    }

    # If we have hue+sat, use hs_color; otherwise use color_temp
    if hue is not None and sat is not None and sat > 0:
        service_data["hs_color"] = [hue, sat]
    elif kelvin:
        service_data["color_temp"] = int(1_000_000 / kelvin)  # mireds

    success = False
    for entity_id in [e.strip() for e in entities_str.split(",") if e.strip()]:
        service_data["entity_id"] = entity_id
        result = _ha_request("POST", "services/light/turn_on", service_data, cfg)
        if result is not None:
            success = True

    if success:
        print(f"  ✓ Home Assistant lights updated")
    return success


def _ha_power(on: bool, cfg: dict) -> bool:
    entities_str = cfg.get("ENCHANTIFY_HA_LIGHT_ENTITIES", "")
    if not entities_str:
        return False

    service = "turn_on" if on else "turn_off"
    for entity_id in [e.strip() for e in entities_str.split(",") if e.strip()]:
        _ha_request("POST", f"services/light/{service}", {"entity_id": entity_id}, cfg)
    print(f"  ✓ HA lights {'ON' if on else 'OFF'}")
    return True


# ── Backend: Philips Hue ──────────────────────────────────────────────────────

def _hue_request(method: str, path: str, body: Optional[dict], cfg: dict) -> Optional[dict]:
    bridge = cfg.get("HUE_BRIDGE_IP", "")
    token  = cfg.get("HUE_TOKEN", "")
    if not bridge or not token:
        return None

    url  = f"http://{bridge}/api/{token}/{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠ Hue request failed: {e}")
        return None


def _hue_set(color: dict, cfg: dict) -> bool:
    # Get all lights
    lights = _hue_request("GET", "lights", None, cfg)
    if not lights:
        print("  ⚠ Hue: no lights found (check HUE_BRIDGE_IP / HUE_TOKEN)")
        return False

    hue    = color.get("hue",    0)
    sat    = color.get("sat",    0)
    bright = color.get("bright", DEFAULT_BRIGHT)
    kelvin = color.get("kelvin", DEFAULT_KELVIN)
    dur_ds = int(color.get("transition", DEFAULT_TRANSITION) * 10)  # deciseconds

    body: dict = {
        "on":         True,
        "bri":        int(bright / 100 * 254),
        "transitiontime": dur_ds,
    }
    if sat > 0:
        body["hue"] = int(hue / 360 * 65535)
        body["sat"] = int(sat / 100 * 254)
    else:
        # White — use ct (mireds)
        body["ct"] = max(153, min(500, int(1_000_000 / kelvin)))

    success = False
    for light_id in lights:
        result = _hue_request("PUT", f"lights/{light_id}/state", body, cfg)
        if result:
            success = True

    if success:
        print(f"  ✓ Hue lights updated ({len(lights)} bulb(s))")
    return success


def _hue_power(on: bool, cfg: dict) -> bool:
    lights = _hue_request("GET", "lights", None, cfg)
    if not lights:
        return False
    for light_id in lights:
        _hue_request("PUT", f"lights/{light_id}/state", {"on": on}, cfg)
    print(f"  ✓ Hue lights {'ON' if on else 'OFF'}")
    return True


# ── Backend: HomeKit (macOS Shortcuts) ────────────────────────────────────────
# Full color control requires HA or LIFX backends.
# This backend fires a pre-made Shortcut named "Enchantify: <scene>".
# The user creates these Shortcuts in the Shortcuts app, pointing at HomeKit scenes.

def _homekit_scene(scene_name: str, cfg: dict) -> bool:
    shortcut_name = cfg.get(
        f"ENCHANTIFY_HOMEKIT_SHORTCUT_{scene_name.upper().replace('-', '_')}",
        f"Enchantify: {scene_name}",
    )
    shortcuts_bin = shutil.which("shortcuts")
    if not shortcuts_bin:
        print("  ⚠ HomeKit backend: 'shortcuts' CLI not found (macOS 12+ required)")
        return False

    result = subprocess.run(
        [shortcuts_bin, "run", shortcut_name],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        print(f"  ✓ HomeKit Shortcut: '{shortcut_name}'")
        return True
    else:
        print(f"  ⚠ HomeKit: Shortcut '{shortcut_name}' failed or not found")
        print(f"     Create it in Shortcuts.app → trigger a HomeKit scene")
        return False


# ── Dispatch ──────────────────────────────────────────────────────────────────

def get_backends(cfg: dict, override: Optional[str] = None) -> list[str]:
    """Return ordered list of backends to try."""
    if override:
        return [override]
    configured = cfg.get("LIGHTS_BACKEND", "none").lower()
    if configured == "none":
        return []
    # Support comma-separated fallback chain: "lifx,ha"
    return [b.strip() for b in configured.split(",") if b.strip()]


def set_color(color: dict, cfg: dict, backend_override: Optional[str] = None) -> bool:
    """Set lights to the given universal color dict. Returns True if any backend succeeded."""
    backends = get_backends(cfg, backend_override)
    if not backends:
        print("  ℹ Lights not configured (LIGHTS_BACKEND=none)")
        return False

    for backend in backends:
        if backend == "lifx":
            if _lifx_set(color, cfg):
                return True
        elif backend == "ha":
            if _ha_set(color, cfg):
                return True
        elif backend == "hue":
            if _hue_set(color, cfg):
                return True
        elif backend == "homekit":
            # HomeKit can only do scenes — skip for raw color calls
            print("  ℹ HomeKit backend doesn't support arbitrary colors; use lifx or ha backend")
            return False
        else:
            print(f"  ⚠ Unknown backend: {backend}")

    return False


def set_power(on: bool, cfg: dict, backend_override: Optional[str] = None) -> bool:
    backends = get_backends(cfg, backend_override)
    if not backends:
        print("  ℹ Lights not configured (LIGHTS_BACKEND=none)")
        return False

    for backend in backends:
        if backend == "lifx":
            if _lifx_power(on, cfg):
                return True
        elif backend == "ha":
            if _ha_power(on, cfg):
                return True
        elif backend == "hue":
            if _hue_power(on, cfg):
                return True
    return False


def fire_scene(scene_name: str, cfg: dict,
               bright_override: Optional[float] = None,
               backend_override: Optional[str] = None) -> bool:
    """Fire a named scene. Falls back to HomeKit shortcut if color backends fail."""
    scene_name = scene_name.lower().strip()
    scene = SCENES.get(scene_name)

    if scene is None:
        print(f"  ⚠ Unknown scene: '{scene_name}'. Available: {', '.join(sorted(SCENES))}")
        return False

    color = dict(scene)
    if bright_override is not None:
        color["bright"] = bright_override

    backends = get_backends(cfg, backend_override)
    if not backends:
        print(f"  ℹ Lights not configured (scene '{scene_name}' not fired)")
        return False

    for backend in backends:
        if backend == "lifx":
            if _lifx_set(color, cfg):
                return True
        elif backend == "ha":
            if _ha_set(color, cfg):
                return True
        elif backend == "hue":
            if _hue_set(color, cfg):
                return True
        elif backend == "homekit":
            if _homekit_scene(scene_name, cfg):
                return True

    return False


# ── Test ──────────────────────────────────────────────────────────────────────

def run_test(cfg: dict, backend_override: Optional[str] = None):
    """Cycle through a few colors to verify the setup."""
    import time

    test_colors = [
        ("Red",         {"hue": 0,   "sat": 100, "bright": 70, "kelvin": 3200, "transition": 1.0}),
        ("Green",       {"hue": 120, "sat": 100, "bright": 70, "kelvin": 3200, "transition": 1.0}),
        ("Blue",        {"hue": 240, "sat": 100, "bright": 70, "kelvin": 3200, "transition": 1.0}),
        ("Warm white",  {"hue": 0,   "sat": 0,   "bright": 80, "kelvin": 2700, "transition": 1.0}),
        ("Cool white",  {"hue": 0,   "sat": 0,   "bright": 80, "kelvin": 6500, "transition": 1.0}),
        ("Academy",     SCENES["academy"]),
    ]

    print("Testing lights — cycling through colors...")
    for name, color in test_colors:
        print(f"  → {name}")
        set_color(color, cfg, backend_override)
        time.sleep(2.5)

    print("Test complete. Returning to Academy scene.")
    fire_scene("academy", cfg, backend_override=backend_override)


# ── Status ────────────────────────────────────────────────────────────────────

def show_status(cfg: dict):
    backends = get_backends(cfg)
    print(f"LIGHTS_BACKEND: {cfg.get('LIGHTS_BACKEND', 'none')}")
    print(f"Active backends: {backends or ['none']}")

    if "lifx" in backends:
        ips = cfg.get("ENCHANTIFY_LIFX_IPS", "(auto-discover)")
        print(f"  LIFX IPs: {ips}")

    if "ha" in backends:
        url = cfg.get("HA_URL", "(not set)")
        entities = cfg.get("ENCHANTIFY_HA_LIGHT_ENTITIES", "(auto-discover)")
        print(f"  HA URL: {url}")
        print(f"  HA entities: {entities}")

    if "hue" in backends:
        bridge = cfg.get("HUE_BRIDGE_IP", "(not set)")
        print(f"  Hue bridge: {bridge}")

    if "homekit" in backends:
        shortcuts_ok = bool(shutil.which("shortcuts"))
        print(f"  macOS shortcuts CLI: {'found' if shortcuts_ok else 'NOT FOUND'}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # --backend override
    backend_override = None
    if "--backend" in args:
        idx = args.index("--backend")
        backend_override = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if not args:
        print(__doc__)
        sys.exit(0)

    cfg     = load_config()
    command = args[0].lower()

    # ── scene ─────────────────────────────────────────────────────────────────
    if command == "scene":
        if len(args) < 2:
            print("Usage: lights.py scene <name>")
            sys.exit(1)
        scene_name = args[1].lower()
        ok = fire_scene(scene_name, cfg, backend_override=backend_override)
        sys.exit(0 if ok else 1)

    # ── set ───────────────────────────────────────────────────────────────────
    elif command == "set":
        color: dict = {}

        i = 1
        while i < len(args):
            a = args[i]
            if a == "--color" and i + 1 < len(args):
                parsed = parse_color_spec(args[i + 1])
                if parsed:
                    color.update(parsed)
                else:
                    print(f"  ⚠ Could not parse color: '{args[i+1]}' — try a hex code like #FF6B35")
                i += 2
            elif a == "--hue" and i + 1 < len(args):
                color["hue"] = float(args[i + 1])
                i += 2
            elif a == "--sat" and i + 1 < len(args):
                color["sat"] = float(args[i + 1])
                i += 2
            elif a in ("--bright", "--brightness") and i + 1 < len(args):
                color["bright"] = float(args[i + 1])
                i += 2
            elif a in ("--kelvin", "--temp") and i + 1 < len(args):
                color["kelvin"] = int(args[i + 1])
                i += 2
            elif a == "--transition" and i + 1 < len(args):
                color["transition"] = float(args[i + 1])
                i += 2
            else:
                i += 1

        if not color:
            print("  ⚠ No color specified. Use --color, --hue/--sat/--bright, or --kelvin")
            sys.exit(1)

        ok = set_color(color, cfg, backend_override)
        sys.exit(0 if ok else 1)

    # ── off / on ──────────────────────────────────────────────────────────────
    elif command == "off":
        ok = set_power(False, cfg, backend_override)
        sys.exit(0 if ok else 1)

    elif command == "on":
        # Turn on — restore academy scene
        ok = fire_scene("academy", cfg, backend_override=backend_override)
        if not ok:
            ok = set_power(True, cfg, backend_override)
        sys.exit(0 if ok else 1)

    # ── test ──────────────────────────────────────────────────────────────────
    elif command == "test":
        run_test(cfg, backend_override)

    # ── status ────────────────────────────────────────────────────────────────
    elif command == "status":
        show_status(cfg)

    # ── list-scenes ───────────────────────────────────────────────────────────
    elif command == "list-scenes":
        print("Available scenes:")
        for name, s in sorted(SCENES.items()):
            desc = f"H:{s['hue']}° S:{s['sat']}% B:{s['bright']}% K:{s['kelvin']}K"
            print(f"  {name:<20} {desc}")

    # ── legacy color command (backward compat) ────────────────────────────────
    elif command == "color":
        # lifx-control.py color <hue> <sat> <bright> [kelvin]
        # Old format was raw LIFX values (0-65535). Convert to universal.
        if len(args) < 4:
            print("Usage: lights.py color <hue 0-65535> <sat 0-65535> <bright 0-65535> [kelvin]")
            sys.exit(1)
        h = int(args[1]) / 65535 * 360
        s = int(args[2]) / 65535 * 100
        b = int(args[3]) / 65535 * 100
        k = int(args[4]) if len(args) > 4 else DEFAULT_KELVIN
        ok = set_color({"hue": h, "sat": s, "bright": b, "kelvin": k}, cfg, backend_override)
        sys.exit(0 if ok else 1)

    elif command == "power":
        on = len(args) > 1 and args[1].lower() == "on"
        ok = set_power(on, cfg, backend_override)
        sys.exit(0 if ok else 1)

    else:
        print(f"Unknown command: {command}")
        print("Commands: scene, set, off, on, test, status, list-scenes")
        sys.exit(1)


if __name__ == "__main__":
    main()
