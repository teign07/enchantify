#!/usr/bin/env python3
"""
write-souvenir.py — Write a canonical Compass Run souvenir file.
Reads weather/moon/season from player-heartbeat.md and Belief/Chapter
from the player file. The Labyrinth provides the souvenir sentence and
the directional responses it collected during the run.

Guarantees the format that print-souvenir.sh expects.

Usage:
  python3 scripts/write-souvenir.py [player] "[souvenir sentence]" [options]

Options:
  --north "[what the player noticed]"
  --east  "[where they went / what they found]"
  --south "[what they sensed]"
  --mood  [ready|tired|low|restless]

Example:
  python3 scripts/write-souvenir.py bj "The cold wasn't empty — it was waiting to be listened to." \\
    --north "A crow on the fire escape, watching me back." \\
    --east "Walked to the end of the street and counted chimneys." \\
    --south "The air tasted like iron and old rain." \\
    --mood tired
"""
import sys
import os
import re
import argparse
from datetime import datetime

PLAYERS_DIR = "players"
HEARTBEAT_PATH = "HEARTBEAT.md"
SOUVENIRS_DIR = "souvenirs"


# ─── Parsers ─────────────────────────────────────────────────────────────────

def extract_field(content: str, label: str, fallback: str = "—") -> str:
    """Extract '**Label:** Value' from markdown content."""
    match = re.search(rf'\*\*{re.escape(label)}:\*\*\s*(.+)', content)
    return match.group(1).strip() if match else fallback


def load_heartbeat() -> dict:
    """
    Parse player-heartbeat.md. Handles two formats:
      - Silvie's pulse format (the active format on this install):
          '- Moon: 🌖 Waning Gibbous (71% illuminated)'
          '- Season: Mud Season — ...'
          '- Belfast Feel: Raw cold...\n *Raw: Light snow, mist 34°F...*'
          '- Tides: Tide going out...'
      - Enchantify-native update-weather.sh format:
          '**Condition:** Overcast'
          '**Phase:** Waxing Gibbous'
    """
    if not os.path.exists(HEARTBEAT_PATH):
        return {}

    with open(HEARTBEAT_PATH, "r") as f:
        content = f.read()

    data = {}

    # ── Silvie format ──────────────────────────────────────────────────────
    # Moon: "- Moon: 🌖 Waning Gibbous (71% illuminated)"
    m = re.search(r'[-•]\s*Moon:\s*(.+)', content)
    if m:
        data["moon"] = m.group(1).strip()
    else:
        # Enchantify-native: **Phase:** + **Illumination:**
        phase = extract_field(content, "Phase", "")
        illum = extract_field(content, "Illumination", "")
        data["moon"] = f"{phase} ({illum})" if phase else "—"

    # Season: "- Season: Mud Season — ..."
    m = re.search(r'[-•]\s*Season:\s*(.+)', content)
    if m:
        # Trim any trailing em-dash description for brevity
        season_raw = m.group(1).strip()
        data["season"] = season_raw.split(" — ")[0].split(" - ")[0]
    else:
        data["season"] = extract_field(content, "Season", "—")

    # Weather: Silvie puts it on the Belfast Feel line and the Raw: sub-line
    # "- Belfast Feel: Raw cold — the damp kind...\n *Raw: Light snow, mist 34°F (feels 27°F) | Wind 9mph SE | ...*"
    m = re.search(r'\*Raw:\s*([^\n*]+)', content)
    if m:
        # "Light snow, mist 34°F (feels 27°F) | Wind 9mph SE | Humidity 100% | Pressure 1022mb"
        raw_parts = m.group(1).strip().split("|")
        data["weather"] = raw_parts[0].strip() if raw_parts else "—"
    else:
        # Enchantify-native format
        condition = extract_field(content, "Condition", "")
        temp = extract_field(content, "Temperature", "")
        feels = extract_field(content, "Feels Like", "")
        data["weather"] = f"{condition}, {temp}" + (f" (feels {feels})" if feels else "") if condition else "—"

    # Tides: "- Tides: Tide going out (Portland) | Next: Low 1.8ft at 9:29 PM -> ..."
    m = re.search(r'[-•]\s*Tides:\s*(.+)', content)
    if m:
        tides_raw = m.group(1).strip()
        # Shorten: take just the direction + next high
        direction_m = re.search(r'Tide (\w+ \w+)', tides_raw)
        next_high_m = re.search(r'High ([\d.]+ft at [\d:]+ [AP]M)', tides_raw)
        if direction_m and next_high_m:
            data["tides"] = f"Tide {direction_m.group(1)}, next high {next_high_m.group(1)}"
        else:
            data["tides"] = tides_raw[:80]  # cap length
    else:
        direction = extract_field(content, "Direction", "")
        high = extract_field(content, "Next High", "")
        data["tides"] = f"Tide {direction}, next high {high}" if direction and direction != "—" else ""

    return data


def load_player_data(name: str) -> dict:
    path = os.path.join(PLAYERS_DIR, f"{name}.md")
    if not os.path.exists(path):
        return {"belief": "?", "chapter": "—"}

    with open(path, "r") as f:
        content = f.read()

    return {
        "belief": extract_field(content, "Belief", "?"),
        "chapter": extract_field(content, "Chapter", "—"),
    }


# ─── Writer ──────────────────────────────────────────────────────────────────

def write_souvenir(player: str, sentence: str, north: str, east: str, south: str, mood: str):
    os.makedirs(SOUVENIRS_DIR, exist_ok=True)

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    date_long = today.strftime("%B %-d, %Y")
    time_str = today.strftime("%H:%M")

    heartbeat = load_heartbeat()
    player_data = load_player_data(player)

    weather = heartbeat.get("weather", "—")
    moon = heartbeat.get("moon", "—")
    season = heartbeat.get("season", "—")
    tides = heartbeat.get("tides", "")
    belief_before = player_data.get("belief", "?")
    chapter = player_data.get("chapter", "—")

    # Build directional log entries
    north_block = f"- **Prompt:** I wonder…\n- **Response:** {north}" if north else "- **Response:** *(not recorded)*"
    east_block = f"- **Report:** {east}" if east else "- **Report:** *(not recorded)*"
    south_block = f"- **Response:** {south}" if south else "- **Response:** *(not recorded)*"
    mood_line = f"**Mood:** {mood}" if mood else ""
    tides_line = f"**Tides:** {tides}" if tides else ""

    content = f"""## Compass Run — {date_long}

**Player:** {player}
**Chapter:** {chapter}
**Date:** {date_str} at {time_str}
**Weather:** {weather}
**Season:** {season}
**Moon:** {moon}
{tides_line}
**Belief before:** {belief_before}
{mood_line}

---

### North — Notice (+2 Belief)

{north_block}

---

### East — Embark (+2 Belief)

{east_block}

---

### South — Sense (+2 Belief)

{south_block}

---

### West — Write (+3 Belief)

- **Souvenir:** "{sentence}"

---

*Compass Run completed {date_long}. Belief +9. The Nothing retreated.*
*The Labyrinth remembers. This page will never go blank.*
"""

    # Strip any doubled blank lines from optional empty fields
    content = re.sub(r'\n{3,}', '\n\n', content)

    filename = f"{date_str}-{player}.md"
    filepath = os.path.join(SOUVENIRS_DIR, filename)

    # If a souvenir already exists today, append a suffix
    if os.path.exists(filepath):
        count = 2
        while os.path.exists(os.path.join(SOUVENIRS_DIR, f"{date_str}-{player}-{count}.md")):
            count += 1
        filename = f"{date_str}-{player}-{count}.md"
        filepath = os.path.join(SOUVENIRS_DIR, filename)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"✓ Souvenir written: {filepath}")
    print(f"  Player:   {player} ({chapter})")
    print(f"  Weather:  {weather}")
    print(f"  Moon:     {moon}")
    print(f"  Sentence: \"{sentence}\"")
    print(f"\n  Next steps:")
    print(f"    python3 scripts/update-player.py {player} belief +9")
    print(f"    bash scripts/print-souvenir.sh {filename}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Write a Compass Run souvenir file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("player", help="Player name (matches players/[name].md)")
    parser.add_argument("sentence", help="The One-Sentence Souvenir")
    parser.add_argument("--north", default="", help="North (Notice) response")
    parser.add_argument("--east", default="", help="East (Embark) response")
    parser.add_argument("--south", default="", help="South (Sense) response")
    parser.add_argument("--mood", default="", choices=["ready", "tired", "low", "restless", ""],
                        help="Pre-run mood check")

    args = parser.parse_args()
    write_souvenir(args.player, args.sentence, args.north, args.east, args.south, args.mood)


if __name__ == "__main__":
    main()
