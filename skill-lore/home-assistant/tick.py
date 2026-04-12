#!/usr/bin/env python3
"""
home-assistant/tick.py — Read HA state and write narrative seeds for significant changes.

Checks Home Assistant entity states. Filters for meaningful changes (presence,
doors, temperature, light) and writes narrative seeds to tick-queue.md.

Requires: pip3 install requests
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent.parent))
SKILL_ID   = os.environ.get("ENCHANTIFY_SKILL_ID", "home-assistant")
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"
STATE_CACHE = BASE_DIR / "config" / "ha-state-cache.json"

HA_URL     = os.environ.get("ENCHANTIFY_HA_URL", "").rstrip("/")
HA_TOKEN   = os.environ.get("ENCHANTIFY_HA_TOKEN", "")
HA_WATCH   = os.environ.get("ENCHANTIFY_HA_ENTITIES", "")

if not HA_URL or not HA_TOKEN:
    print(f"[{SKILL_ID}] Missing config: ENCHANTIFY_HA_URL and/or ENCHANTIFY_HA_TOKEN", file=sys.stderr)
    sys.exit(0)

try:
    import requests
except ImportError:
    print(f"[{SKILL_ID}] Missing dependency. Run: pip3 install requests", file=sys.stderr)
    sys.exit(0)

INTERESTING_PREFIXES = [
    "person.", "binary_sensor.", "sensor.", "input_boolean.", "switch."
]
INTERESTING_KEYWORDS = [
    "door", "motion", "occupancy", "temperature", "presence",
    "home", "away", "arrived", "lock", "window"
]


def get_states() -> list[dict]:
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    try:
        resp = requests.get(f"{HA_URL}/api/states", headers=headers, timeout=10)
        resp.raise_for_status()
        states = resp.json()

        if HA_WATCH:
            watch_ids = {e.strip() for e in HA_WATCH.split(",")}
            return [s for s in states if s["entity_id"] in watch_ids]

        # Auto-filter to interesting entities
        def is_interesting(s):
            eid = s["entity_id"]
            if any(eid.startswith(p) for p in INTERESTING_PREFIXES):
                return True
            return any(kw in eid.lower() for kw in INTERESTING_KEYWORDS)

        return [s for s in states if is_interesting(s)]

    except Exception as e:
        print(f"[{SKILL_ID}] HA API error: {e}", file=sys.stderr)
        return []


def load_cache() -> dict:
    if STATE_CACHE.exists():
        try:
            return json.loads(STATE_CACHE.read_text())
        except Exception:
            pass
    return {}


def save_cache(states: list[dict]) -> None:
    STATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = {s["entity_id"]: s["state"] for s in states}
    STATE_CACHE.write_text(json.dumps(cache))


def find_changes(states: list[dict], cache: dict) -> list[dict]:
    """Return entities whose state changed since last run."""
    changes = []
    for s in states:
        eid   = s["entity_id"]
        state = s["state"]
        old   = cache.get(eid)
        if old is not None and old != state:
            changes.append({
                "entity_id": eid,
                "old_state": old,
                "new_state": state,
                "attributes": s.get("attributes", {}),
            })
    return changes


def translate(change: dict) -> tuple[str, str] | None:
    eid   = change["entity_id"]
    old   = change["old_state"]
    new   = change["new_state"]
    attrs = change.get("attributes", {})
    name  = attrs.get("friendly_name", eid.replace("_", " ").replace(".", " "))

    raw = f"{name}: {old} → {new}"

    # Person presence
    if eid.startswith("person."):
        person = name.split(".")[-1] if "." in name else name
        if new == "home" and old != "home":
            seed = f"The player returned home — the chapter rooms were waiting."
        elif old == "home" and new != "home":
            seed = f"The player left — the chapter rooms are empty now."
        else:
            return None  # minor transition, skip
        return raw, seed

    # Doors
    if "door" in eid.lower():
        if new == "on" or new == "open":
            seed = f"A threshold crossed — {name} opened."
        else:
            seed = f"{name} closed. The house settled."
        return raw, seed

    # Motion / occupancy
    if "motion" in eid.lower() or "occupancy" in eid.lower():
        if new == "on" or new == "detected":
            seed = f"Motion in {name} — someone is moving through."
        else:
            return None  # cleared motion is noise
        return raw, seed

    # Temperature (only if significant change)
    if "temperature" in eid.lower():
        try:
            temp_new = float(new)
            temp_old = float(old)
            if abs(temp_new - temp_old) < 2:
                return None  # minor change, skip
            direction = "dropped" if temp_new < temp_old else "climbed"
            seed = f"The temperature in {name} {direction} to {temp_new}° — the Academy feels it."
        except ValueError:
            return None
        return raw, seed

    return None  # unrecognized — skip


def fetch() -> list[dict]:
    states  = get_states()
    cache   = load_cache()
    changes = find_changes(states, cache)
    save_cache(states)

    items = []
    for change in changes:
        result = translate(change)
        if result:
            raw, seed = result
            items.append({"raw": raw, "seed": seed})

    return items[:5]  # cap at 5 per tick


def write_to_queue(items: list[dict]) -> None:
    if not items:
        print(f"[{SKILL_ID}] No significant state changes.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)

    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text(
            "# Tick Queue\n\n"
            "*Populated by skill-lore and tick.py. Read at session open.*\n\n---\n"
        )

    with TICK_QUEUE.open("a") as f:
        for item in items:
            f.write(
                f"\n## [{SKILL_ID}] {timestamp}\n"
                f"*Raw: {item['raw']}*\n"
                f"Narrative seed: {item['seed']}\n"
            )

    print(f"[{SKILL_ID}] Wrote {len(items)} change(s) to tick queue.")


if __name__ == "__main__":
    try:
        write_to_queue(fetch())
    except Exception as e:
        print(f"[{SKILL_ID}] Error: {e}", file=sys.stderr)
        sys.exit(0)
