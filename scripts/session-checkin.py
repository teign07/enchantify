#!/usr/bin/env python3
"""
session-checkin.py — Player mood and dream check-in.
Appends a check-in section to player-heartbeat.md so the Labyrinth
has emotional context without needing a Silvie connection.

Called by the Labyrinth at session start (or the player can run it directly).
The act of answering is itself part of the re-enchantment practice.

Usage:
  python3 scripts/session-checkin.py [player]              # interactive
  python3 scripts/session-checkin.py [player] --sleep "ok" --mood "tired but here"
  python3 scripts/session-checkin.py [player] --sleep "well" --mood "ready" --dream "water"
"""
import sys
import os
import re
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent
HEARTBEAT_PATH = WORKSPACE_DIR / "HEARTBEAT.md"


def load_config() -> dict:
    config_path = SCRIPT_DIR / "enchantify-config.sh"
    cfg = {}
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"')
    return cfg


def ask(prompt: str) -> str:
    try:
        return input(f"  {prompt}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def main():
    parser = argparse.ArgumentParser(description="Session check-in for the Labyrinth.")
    parser.add_argument("player", nargs="?", help="Player name")
    parser.add_argument("--sleep", default="", help="How did you sleep?")
    parser.add_argument("--mood", default="", help="How are you feeling?")
    parser.add_argument("--dream", default="", help="Anything from your dreams?")
    args = parser.parse_args()

    cfg = load_config()
    player = args.player or cfg.get("ENCHANTIFY_DEFAULT_PLAYER", "")

    if not player:
        player = ask("Who is opening the book?")

    print(f"\n  The pages turn. The Academy stirs.")
    print(f"  Three questions, before the story begins.\n")

    sleep = args.sleep or ask("How did you sleep last night?")
    mood = args.mood or ask("How are you feeling right now?")
    dream = args.dream or ask("Anything worth noting from your dreams? (Enter to skip)")

    now = datetime.now()
    time_str = now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%A, %B %-d")

    # Build the check-in block
    lines = [
        f"\n## 🌙 Session Check-In — {date_str} at {time_str}",
        f"",
        f"**Player:** {player}",
        f"**Sleep:** {sleep}" if sleep else None,
        f"**Mood:** {mood}" if mood else None,
        f"**Dream fragment:** {dream}" if dream else None,
        f"",
    ]
    block = "\n".join(line for line in lines if line is not None)

    # Find the heartbeat file
    heartbeat_file = Path(cfg.get("ENCHANTIFY_OUTPUT", str(HEARTBEAT_PATH)))
    if not heartbeat_file.exists():
        heartbeat_file = HEARTBEAT_PATH

    if heartbeat_file.exists():
        # Remove any previous check-in from today (keep only the most recent)
        with open(heartbeat_file, "r") as f:
            content = f.read()

        today_pattern = re.compile(
            r'\n## 🌙 Session Check-In — ' + re.escape(date_str) + r'.*?(?=\n## |\Z)',
            re.DOTALL
        )
        content = today_pattern.sub("", content).rstrip()
        new_content = content + block

        with open(heartbeat_file, "w") as f:
            f.write(new_content)
        print(f"\n  ✓ Check-in written to heartbeat.")
    else:
        # Heartbeat doesn't exist yet — write a minimal file with the check-in
        heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        with open(heartbeat_file, "w") as f:
            f.write(f"# Player Heartbeat — Enchantify\n{block}")
        print(f"\n  ✓ Check-in written (heartbeat created at {heartbeat_file}).")

    # Soft reflection based on mood/sleep (for the Labyrinth to pick up)
    print()
    mood_lower = (mood + " " + sleep).lower()
    if any(w in mood_lower for w in ["tired", "exhausted", "rough", "bad", "awful"]):
        print("  *(The corridors will be quieter today. The Academy knows.)*")
    elif any(w in mood_lower for w in ["good", "great", "ready", "excited", "well"]):
        print("  *(The Academy feels the energy. The bookshelves are already rearranging.)*")
    else:
        print("  *(The pages settle, noting your presence. The story continues.)*")
    print()


if __name__ == "__main__":
    main()
