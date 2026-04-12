#!/usr/bin/env python3
"""
configure.py — Enchantify Setup Wizard
Writes scripts/enchantify-config.sh which is read by update-weather.sh,
lifx-control.py, sparky.py, dream.py, and other scripts.

Run once on first install, or re-run anytime to change settings.
Usage: python3 scripts/configure.py
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
WORKSPACE_DIR = SCRIPT_DIR.parent
CONFIG_OUT = SCRIPT_DIR / "enchantify-config.sh"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def ask(prompt: str, default: str = "") -> str:
    display = f" [{default}]" if default else ""
    try:
        val = input(f"{prompt}{display}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        sys.exit(0)
    return val if val else default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        val = input(f"{prompt} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        sys.exit(0)
    if not val:
        return default
    return val.startswith("y")


def geocode(location: str) -> tuple[str, str] | None:
    """Look up lat/long from a location name using Nominatim (free, no key)."""
    try:
        query = urllib.parse.urlencode({"q": location, "format": "json", "limit": 1})
        req = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/search?{query}",
            headers={"User-Agent": "Enchantify-Setup/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            results = json.loads(r.read())
        if results:
            return results[0]["lat"], results[0]["lon"]
    except Exception:
        pass
    return None


def detect_timezone() -> str:
    """Best-effort system timezone detection (IANA format)."""
    # macOS / Linux: read /etc/localtime symlink
    try:
        lt = Path("/etc/localtime").resolve()
        parts = lt.parts
        for i, part in enumerate(parts):
            if part == "zoneinfo":
                return "/".join(parts[i+1:])
    except Exception:
        pass
    # fallback: TZ env or date command
    tz = os.environ.get("TZ", "")
    if tz:
        return tz
    try:
        result = subprocess.run(["date", "+%Z"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return "America/New_York"


def load_existing_config() -> dict:
    """Parse existing enchantify-config.sh if present."""
    config = {}
    if not CONFIG_OUT.exists():
        return config
    with open(CONFIG_OUT) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            config[key.strip()] = val.strip().strip('"')
    return config


def detect_silvie() -> str | None:
    """Check if Silvie's HEARTBEAT.md is reachable."""
    candidates = [
        Path.home() / ".openclaw/workspace/HEARTBEAT.md",
        WORKSPACE_DIR.parent / "HEARTBEAT.md",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║      Enchantify — Setup Wizard               ║")
    print("║      The Labyrinth is learning your world.   ║")
    print("╚══════════════════════════════════════════════╝")

    existing = load_existing_config()
    if existing:
        print(f"\n  Existing configuration found. Defaults shown in [brackets].")
        print(f"  Press Enter to keep, or type a new value.")

    cfg = {}

    # ── Silvie mode ───────────────────────────────────────────────────────────
    section("1 / 7  —  Silvie Connection")
    silvie_path = detect_silvie()

    if silvie_path:
        print(f"\n  ✨ Silvie detected at: {silvie_path}")
        print(f"  In Silvie mode, the heartbeat is read from Silvie's HEARTBEAT.md.")
        print(f"  Weather, Sparky, and diary data flows through Silvie automatically.")
        silvie_mode = ask_yes_no("  Use Silvie mode?", default=True)
    else:
        silvie_mode = False

    cfg["ENCHANTIFY_SILVIE_MODE"] = "yes" if silvie_mode else "no"

    if silvie_mode:
        cfg["ENCHANTIFY_SILVIE_HEARTBEAT"] = silvie_path
        cfg["ENCHANTIFY_OUTPUT"] = silvie_path  # read from Silvie's file directly
        print(f"\n  ✓ Silvie mode enabled. Skipping standalone data setup.")
    else:
        cfg["ENCHANTIFY_SILVIE_HEARTBEAT"] = ""
        heartbeat_path = str(WORKSPACE_DIR / "config" / "player-heartbeat.md")
        cfg["ENCHANTIFY_OUTPUT"] = existing.get("ENCHANTIFY_OUTPUT", heartbeat_path)

    # ── Location ──────────────────────────────────────────────────────────────
    section("2 / 7  —  Location")
    print("\n  Used for weather, moon, tides, and heartbeat atmosphere.")

    default_loc = existing.get("ENCHANTIFY_LOCATION", "")
    location = ask("  Your town or city", default_loc)
    cfg["ENCHANTIFY_LOCATION"] = location

    default_lat = existing.get("ENCHANTIFY_LAT", "")
    default_lon = existing.get("ENCHANTIFY_LONG", "")

    if not default_lat and location:
        print(f"  Looking up coordinates for '{location}'...")
        coords = geocode(location)
        if coords:
            default_lat, default_lon = coords
            print(f"  Found: {default_lat}, {default_lon}")
        else:
            print("  Could not auto-detect. Please enter manually.")

    lat = ask("  Latitude", default_lat)
    lon = ask("  Longitude", default_lon)
    cfg["ENCHANTIFY_LAT"] = lat
    cfg["ENCHANTIFY_LONG"] = lon

    tz_detected = detect_timezone()
    default_tz = existing.get("ENCHANTIFY_TIMEZONE", tz_detected)
    print(f"\n  Common timezones: America/New_York, America/Chicago, America/Los_Angeles,")
    print(f"                    Europe/London, Europe/Paris, Australia/Sydney")
    tz = ask("  Timezone (IANA format)", default_tz)
    cfg["ENCHANTIFY_TIMEZONE"] = tz

    # Hemisphere + season names
    hemi = ask("  Hemisphere (north/south)", existing.get("ENCHANTIFY_HEMISPHERE", "north"))
    cfg["ENCHANTIFY_HEMISPHERE"] = hemi
    cfg["ENCHANTIFY_S_WINTER"] = ask("  Name for winter", existing.get("ENCHANTIFY_S_WINTER", "Winter"))
    cfg["ENCHANTIFY_S_SPRING"] = ask("  Name for spring", existing.get("ENCHANTIFY_S_SPRING", "Spring"))
    cfg["ENCHANTIFY_S_SUMMER"] = ask("  Name for summer", existing.get("ENCHANTIFY_S_SUMMER", "Summer"))
    cfg["ENCHANTIFY_S_AUTUMN"] = ask("  Name for autumn", existing.get("ENCHANTIFY_S_AUTUMN", "Autumn"))

    # ── Tides ─────────────────────────────────────────────────────────────────
    section("3 / 7  —  Tides (Optional)")
    print("\n  Tides use NOAA's free API (US coastal stations only).")
    print("  Find your station at: https://tidesandcurrents.noaa.gov/map/")
    print("  Skip if you're inland or non-US.")

    default_noaa = existing.get("ENCHANTIFY_NOAA_STATION", "")
    noaa = ask("  NOAA station ID (leave blank to skip)", default_noaa)
    cfg["ENCHANTIFY_NOAA_STATION"] = noaa

    # ── Integrations ──────────────────────────────────────────────────────────
    section("4 / 7  —  Integrations")

    if not silvie_mode:
        print()
        spotify = ask_yes_no(
            "  Spotify (macOS only — reads current track for atmosphere)?",
            existing.get("ENCHANTIFY_ENABLE_SPOTIFY", "yes") == "yes"
        )
        cfg["ENCHANTIFY_ENABLE_SPOTIFY"] = "yes" if spotify else "no"

        fuel = ask_yes_no(
            "  Fuel Gauge (log food via log-fuel.sh for NPC care responses)?",
            existing.get("ENCHANTIFY_ENABLE_FUEL", "yes") == "yes"
        )
        cfg["ENCHANTIFY_ENABLE_FUEL"] = "yes" if fuel else "no"

        steps = ask_yes_no(
            "  Steps (macOS Shortcuts → Apple Health — requires 'Get Steps Today' shortcut)?",
            existing.get("ENCHANTIFY_ENABLE_STEPS", "no") == "yes"
        )
        cfg["ENCHANTIFY_ENABLE_STEPS"] = "yes" if steps else "no"

        gw2 = ask_yes_no(
            "  Guild Wars 2 (reads daily AP via API)?",
            existing.get("ENCHANTIFY_ENABLE_GW2", "no") == "yes"
        )
        cfg["ENCHANTIFY_ENABLE_GW2"] = "yes" if gw2 else "no"
        if gw2:
            default_key = existing.get("ENCHANTIFY_GW2_API_KEY", "")
            cfg["ENCHANTIFY_GW2_API_KEY"] = ask("    GW2 API key", default_key)
        else:
            cfg["ENCHANTIFY_GW2_API_KEY"] = existing.get("ENCHANTIFY_GW2_API_KEY", "")
    else:
        # Silvie handles all data feeds — just carry through any existing values
        for key in ["ENCHANTIFY_ENABLE_SPOTIFY", "ENCHANTIFY_ENABLE_FUEL",
                    "ENCHANTIFY_ENABLE_STEPS", "ENCHANTIFY_ENABLE_GW2", "ENCHANTIFY_GW2_API_KEY"]:
            cfg[key] = existing.get(key, "no")

    # ── LIFX ──────────────────────────────────────────────────────────────────
    section("5 / 7  —  Smart Lights (Optional)")
    print("\n  Enchantify controls LIFX bulbs over your local network.")
    print("  Auto-discovery finds bulbs automatically — IPs are optional")
    print("  but improve reliability on busy or complex networks.")

    lifx = ask_yes_no(
        "  Enable LIFX smart lights?",
        existing.get("ENCHANTIFY_ENABLE_LIFX", "no") == "yes"
    )
    cfg["ENCHANTIFY_ENABLE_LIFX"] = "yes" if lifx else "no"

    if lifx:
        default_ips = existing.get("ENCHANTIFY_LIFX_IPS", "")
        print("  Enter bulb IPs as comma-separated list, or leave blank for auto-discovery.")
        ips = ask("  LIFX bulb IPs", default_ips)
        cfg["ENCHANTIFY_LIFX_IPS"] = ips

    # ── Printer ───────────────────────────────────────────────────────────────
    print()
    printer = ask_yes_no(
        "  Enable souvenir printing after Compass Runs?",
        existing.get("ENCHANTIFY_ENABLE_PRINTER", "no") == "yes"
    )
    cfg["ENCHANTIFY_ENABLE_PRINTER"] = "yes" if printer else "no"

    if printer:
        print("\n  Run 'lpstat -p' to see available printer names.")
        cfg["ENCHANTIFY_PRINTER"] = ask(
            "  Printer name (primary)",
            existing.get("ENCHANTIFY_PRINTER", "")
        )
        cfg["ENCHANTIFY_PRINTER_BACKUP"] = ask(
            "  Printer name (backup, optional)",
            existing.get("ENCHANTIFY_PRINTER_BACKUP", "")
        )

    # ── Sparky + Labyrinth inner life ─────────────────────────────────────────
    section("6 / 7  —  Sparky & The Labyrinth's Inner Life")

    if not silvie_mode:
        print("\n  Sparky is the margin creature — it finds pattern-connections between")
        print("  your world and the Academy. Requires an Anthropic API key.")
        sparky = ask_yes_no(
            "  Enable standalone Sparky (daily pattern-finding)?",
            existing.get("ENCHANTIFY_ENABLE_SPARKY", "no") == "yes"
        )
        cfg["ENCHANTIFY_ENABLE_SPARKY"] = "yes" if sparky else "no"
        cfg["ENCHANTIFY_SPARKY_MODE"] = "standalone" if sparky else "off"
        cfg["ENCHANTIFY_SPARKY_SOURCE"] = ""
    else:
        cfg["ENCHANTIFY_ENABLE_SPARKY"] = "yes"
        cfg["ENCHANTIFY_SPARKY_MODE"] = "silvie"
        cfg["ENCHANTIFY_SPARKY_SOURCE"] = silvie_path or ""
        print(f"  ✓ Sparky runs via Silvie.")

    print("\n  The Labyrinth keeps its own diary (written at session close) and")
    print("  dreams overnight (generated by cron). Both require an Anthropic API key.")
    diary = ask_yes_no(
        "  Enable Labyrinth diary & dreams?",
        existing.get("ENCHANTIFY_ENABLE_DIARY", "yes") == "yes"
    )
    cfg["ENCHANTIFY_ENABLE_DIARY"] = "yes" if diary else "no"
    cfg["ENCHANTIFY_ENABLE_DREAMS"] = "yes" if diary else "no"

    if (not silvie_mode and sparky) or diary:
        print("\n  An Anthropic API key is needed for Sparky and/or the Labyrinth's dreams.")
        print("  Get one at: https://console.anthropic.com")
        print("  If already set in your environment (ANTHROPIC_API_KEY), leave blank.")
        api_key = ask("  Anthropic API key (leave blank if set in environment)",
                      existing.get("ENCHANTIFY_ANTHROPIC_API_KEY", ""))
        cfg["ENCHANTIFY_ANTHROPIC_API_KEY"] = api_key
    else:
        cfg["ENCHANTIFY_ANTHROPIC_API_KEY"] = existing.get("ENCHANTIFY_ANTHROPIC_API_KEY", "")

    # ── Player ────────────────────────────────────────────────────────────────
    section("7 / 7  —  Player")
    default_player = existing.get("ENCHANTIFY_DEFAULT_PLAYER", "")
    cfg["ENCHANTIFY_DEFAULT_PLAYER"] = ask(
        "  Default player name (matches players/[name].md)",
        default_player
    )

    # ── Write config ──────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  Writing configuration...")

    lines = [
        "#!/bin/bash",
        "# enchantify-config.sh — Generated by configure.py",
        f"# Created: {time.strftime('%Y-%m-%d %H:%M')}",
        "# Re-run: python3 scripts/configure.py",
        "",
        "# ── Silvie Integration ──────────────────────────────",
        f'ENCHANTIFY_SILVIE_MODE="{cfg["ENCHANTIFY_SILVIE_MODE"]}"',
        f'ENCHANTIFY_SILVIE_HEARTBEAT="{cfg["ENCHANTIFY_SILVIE_HEARTBEAT"]}"',
        "",
        "# ── Location ────────────────────────────────────────",
        f'ENCHANTIFY_LOCATION="{cfg["ENCHANTIFY_LOCATION"]}"',
        f'ENCHANTIFY_LAT="{cfg["ENCHANTIFY_LAT"]}"',
        f'ENCHANTIFY_LONG="{cfg["ENCHANTIFY_LONG"]}"',
        f'ENCHANTIFY_TIMEZONE="{cfg["ENCHANTIFY_TIMEZONE"]}"',
        f'ENCHANTIFY_HEMISPHERE="{cfg["ENCHANTIFY_HEMISPHERE"]}"',
        f'ENCHANTIFY_S_WINTER="{cfg["ENCHANTIFY_S_WINTER"]}"',
        f'ENCHANTIFY_S_SPRING="{cfg["ENCHANTIFY_S_SPRING"]}"',
        f'ENCHANTIFY_S_SUMMER="{cfg["ENCHANTIFY_S_SUMMER"]}"',
        f'ENCHANTIFY_S_AUTUMN="{cfg["ENCHANTIFY_S_AUTUMN"]}"',
        "",
        "# ── Heartbeat Output ────────────────────────────────",
        f'ENCHANTIFY_OUTPUT="{cfg["ENCHANTIFY_OUTPUT"]}"',
        "",
        "# ── Tides (NOAA) ────────────────────────────────────",
        f'ENCHANTIFY_NOAA_STATION="{cfg["ENCHANTIFY_NOAA_STATION"]}"',
        "",
        "# ── Integrations ────────────────────────────────────",
        f'ENCHANTIFY_ENABLE_SPOTIFY="{cfg["ENCHANTIFY_ENABLE_SPOTIFY"]}"',
        f'ENCHANTIFY_ENABLE_FUEL="{cfg["ENCHANTIFY_ENABLE_FUEL"]}"',
        f'ENCHANTIFY_ENABLE_STEPS="{cfg["ENCHANTIFY_ENABLE_STEPS"]}"',
        f'ENCHANTIFY_ENABLE_GW2="{cfg["ENCHANTIFY_ENABLE_GW2"]}"',
        f'ENCHANTIFY_GW2_API_KEY="{cfg["ENCHANTIFY_GW2_API_KEY"]}"',
        "",
        "# ── Smart Lights (LIFX) ─────────────────────────────",
        f'ENCHANTIFY_ENABLE_LIFX="{cfg["ENCHANTIFY_ENABLE_LIFX"]}"',
        f'ENCHANTIFY_LIFX_IPS="{cfg.get("ENCHANTIFY_LIFX_IPS", "")}"',
        "",
        "# ── Printer ─────────────────────────────────────────",
        f'ENCHANTIFY_ENABLE_PRINTER="{cfg["ENCHANTIFY_ENABLE_PRINTER"]}"',
        f'ENCHANTIFY_PRINTER="{cfg.get("ENCHANTIFY_PRINTER", "")}"',
        f'ENCHANTIFY_PRINTER_BACKUP="{cfg.get("ENCHANTIFY_PRINTER_BACKUP", "")}"',
        "",
        "# ── Sparky & Labyrinth Inner Life ───────────────────",
        f'ENCHANTIFY_ENABLE_SPARKY="{cfg["ENCHANTIFY_ENABLE_SPARKY"]}"',
        f'ENCHANTIFY_SPARKY_MODE="{cfg["ENCHANTIFY_SPARKY_MODE"]}"',
        f'ENCHANTIFY_SPARKY_SOURCE="{cfg["ENCHANTIFY_SPARKY_SOURCE"]}"',
        f'ENCHANTIFY_ENABLE_DIARY="{cfg["ENCHANTIFY_ENABLE_DIARY"]}"',
        f'ENCHANTIFY_ENABLE_DREAMS="{cfg["ENCHANTIFY_ENABLE_DREAMS"]}"',
        f'ENCHANTIFY_ANTHROPIC_API_KEY="{cfg["ENCHANTIFY_ANTHROPIC_API_KEY"]}"',
        "",
        "# ── Player ──────────────────────────────────────────",
        f'ENCHANTIFY_DEFAULT_PLAYER="{cfg["ENCHANTIFY_DEFAULT_PLAYER"]}"',
    ]

    with open(CONFIG_OUT, "w") as f:
        f.write("\n".join(lines) + "\n")

    os.chmod(CONFIG_OUT, 0o644)

    # ── Create required directories ───────────────────────────────────────────
    dirs = [
        WORKSPACE_DIR / "memory" / "diary",
        WORKSPACE_DIR / "memory" / "dreams",
        WORKSPACE_DIR / "sparky" / "shinies",
        WORKSPACE_DIR / "souvenirs",
        WORKSPACE_DIR / "logs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"  ✓ Written: {CONFIG_OUT}")
    print()
    print("  Suggested cron jobs (run: crontab -e to add):")
    print()
    ws = WORKSPACE_DIR
    print(f"  # Enchantify — weather/heartbeat update (every hour)")
    print(f"  0 * * * * bash {ws}/scripts/update-weather.sh >> {ws}/logs/weather.log 2>&1")
    print()
    if cfg["ENCHANTIFY_ENABLE_SPARKY"] == "yes" and cfg["ENCHANTIFY_SPARKY_MODE"] == "standalone":
        print(f"  # Enchantify — Sparky daily shiny (8am)")
        print(f"  0 8 * * * python3 {ws}/scripts/sparky.py >> {ws}/logs/sparky.log 2>&1")
        print()
    if cfg["ENCHANTIFY_ENABLE_DREAMS"] == "yes":
        print(f"  # Enchantify — Labyrinth dreams (2am)")
        print(f"  0 2 * * * python3 {ws}/scripts/dream.py >> {ws}/logs/dream.log 2>&1")
        print()
    print()
    print("  Run this to fetch your first heartbeat:")
    print(f"  bash {ws}/scripts/update-weather.sh")
    print()
    print("  The Labyrinth is ready. Open the book when you are.")
    print()


if __name__ == "__main__":
    main()
