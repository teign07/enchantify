#!/usr/bin/env python3
"""
ambient-state.py — Dominant chapter talisman → digital environment.

Reads the Chapter Talismans from world-register.md, finds the one with
the highest Belief, and shapes the player's digital environment to match
that chapter's philosophy. Called by governance-engine.py on session-open
and by the 4-hour cron.

The dominant talisman is currently: Dusk Thorn (55) — "No conflict, no story."

Each chapter has an environment profile:
  - LIFX scene
  - Spotify mood descriptor (written to tick-queue for the Labyrinth to narrate)
  - Do Not Disturb default
  - Narrative texture (one sentence, woven into session opening)
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent))
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"

# Chapter environment profiles
# These are the digital translations of each chapter's philosophy.
PROFILES = {
    "duskthorn": {
        "lifx_scene":   "nothing",
        "spotify_mood": "dramatic, tense, minor-key — music with teeth. Something that earns its resolution.",
        "dnd":          False,   # Duskthorn invites friction. DND shields from it.
        "narrative":    "The Dusk Thorn holds the room. The light has edges. Something in the air says: this matters.",
        "description":  "Darkness earns the light — Duskthorn dominant",
    },
    "riddlewind": {
        "lifx_scene":   "library",
        "spotify_mood": "collaborative, acoustic, folk or ambient — music that sounds like it was made with someone else in the room.",
        "dnd":          False,   # Riddlewind is between you and the world. Stay open.
        "narrative":    "The Wind Cipher is brightest here. The corridors feel co-written — as if the world is waiting for your next line.",
        "description":  "The story is co-authored — Riddlewind dominant",
    },
    "emberheart": {
        "lifx_scene":   "academy",
        "spotify_mood": "focused, instrumental, deep work — music that clears the room and leaves only you and the page.",
        "dnd":          True,    # Emberheart writes alone. Shield the work.
        "narrative":    "The Ember Seal is steady. The Academy sharpens. This is the hour of self-authorship.",
        "description":  "The story is yours to write — Emberheart dominant",
    },
    "mossbloom": {
        "lifx_scene":   "compass-complete",
        "spotify_mood": "gentle, ambient, nature sounds or slow instrumentals — music that holds space rather than fills it.",
        "dnd":          True,    # Mossbloom surrenders. Protect that quiet.
        "narrative":    "The Moss Clasp settles over everything. The Academy breathes. Something larger than you is writing through you today.",
        "description":  "Something larger writes through you — Mossbloom dominant",
    },
    "tidecrest": {
        "lifx_scene":   "compass-north",
        "spotify_mood": "present-tense, alive, whatever fits this specific hour — no genre rules. Let the moment name its own music.",
        "dnd":          False,   # Tidecrest has no fixed meaning. Stay open.
        "narrative":    "The Tide Glass holds the room loosely. There is no arc here — only this moment, which is enough.",
        "description":  "Life is a poem, not a plot — Tidecrest dominant",
    },
}

TALISMAN_TO_CHAPTER = {
    "Dusk Thorn":   "duskthorn",
    "Wind Cipher":  "riddlewind",
    "Ember Seal":   "emberheart",
    "Moss Clasp":   "mossbloom",
    "Tide Glass":   "tidecrest",
}


def parse_dominant_talisman(register_text: str) -> tuple[str, str, int]:
    """
    Returns (talisman_name, chapter_id, belief) for the highest-Belief talisman.
    """
    best_name    = None
    best_chapter = None
    best_belief  = -1

    for line in register_text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue

        name = parts[0]
        if name not in TALISMAN_TO_CHAPTER:
            continue

        belief_m = re.search(r"(\d+)", parts[2])
        if not belief_m:
            continue

        belief = int(belief_m.group(1))
        if belief > best_belief:
            best_belief  = belief
            best_name    = name
            best_chapter = TALISMAN_TO_CHAPTER[name]

    return best_name, best_chapter, best_belief


def fire_lifx(scene: str) -> bool:
    result = subprocess.run(
        ["python3", str(BASE_DIR / "scripts" / "lifx-control.py"), "scene", scene],
        capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0


def write_ambient_seed(profile: dict, talisman: str, belief: int) -> None:
    """Write the ambient state as a tick-queue seed for the Labyrinth to narrate."""
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text("# Tick Queue\n\n*Populated by skill-lore and world systems. Read at session open.*\n\n---\n")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with TICK_QUEUE.open("a") as f:
        f.write(
            f"\n## [ambient-state] {timestamp}\n"
            f"*Raw: Dominant talisman: {talisman} (Belief {belief}) — {profile['description']}*\n"
            f"Narrative seed: {profile['narrative']}\n"
            f"Spotify mood for today: {profile['spotify_mood']}\n"
        )


def run(dry_run: bool = False) -> None:
    register_path = BASE_DIR / "lore" / "world-register.md"
    if not register_path.exists():
        print("[ambient-state] world-register.md not found", file=sys.stderr)
        return

    register = register_path.read_text()
    talisman, chapter, belief = parse_dominant_talisman(register)

    if not chapter:
        print("[ambient-state] No talismans found in world register", file=sys.stderr)
        return

    profile = PROFILES.get(chapter)
    if not profile:
        print(f"[ambient-state] No profile for chapter: {chapter}", file=sys.stderr)
        return

    print(f"[ambient-state] Dominant: {talisman} (Belief {belief}) — {chapter}")
    print(f"[ambient-state] Profile: {profile['description']}")

    if dry_run:
        print(f"[ambient-state] [DRY RUN] Would fire: LIFX {profile['lifx_scene']}, DND={profile['dnd']}")
        print(f"[ambient-state] [DRY RUN] Spotify mood: {profile['spotify_mood']}")
        return

    # Fire LIFX
    lifx_ok = fire_lifx(profile["lifx_scene"])
    print(f"[ambient-state] LIFX scene '{profile['lifx_scene']}': {'✓' if lifx_ok else '✗ (offline?)'}")

    # Write to tick-queue for Labyrinth narration
    write_ambient_seed(profile, talisman, belief)
    print(f"[ambient-state] Wrote ambient seed to tick-queue")

    print(f"[ambient-state] Done.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run(dry_run)
