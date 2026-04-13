#!/usr/bin/env python3
"""
dorm-generate.py — Generate the player's permanent dorm room description.

Called once at T13 (first dorm arrival during tutorial), or manually to
regenerate. Uses all accumulated player data to write a room that is
unmistakably theirs. Writes directly to players/[name].md.

The static description is permanent — the felt character of the room never
changes. Seasonal updates (4x/year) adjust the light and air, not the soul.

Usage:
  python3 scripts/dorm-generate.py [player_name]
  python3 scripts/dorm-generate.py [player_name] --season [spring|summer|autumn|winter]
  python3 scripts/dorm-generate.py [player_name] --dry-run
"""

import os
import re
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
WORKSPACE   = SCRIPT_DIR.parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_safe(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text().strip()
    if limit:
        return "\n".join(text.splitlines()[:limit])
    return text


def get_current_season() -> str:
    month = datetime.now().month
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    else:
        return "autumn"


def load_player_data(player_name: str) -> dict:
    """Extract everything the Labyrinth knows about this player."""
    player_path = WORKSPACE / "players" / f"{player_name}.md"
    content = read_safe(player_path, 80)

    def extract(pattern, default=""):
        m = re.search(pattern, content, re.IGNORECASE)
        return m.group(1).strip() if m else default

    return {
        "name":         player_name,
        "belief":       extract(r'\*\*Belief:\*\*\s*(\d+)', "?"),
        "chapter":      extract(r'\*\*Chapter:\*\*\s*(\S+)', "Unknown"),
        "anchor":       extract(r'\*\*Anchor:\*\*\s*(.+)'),
        "appearance":   extract(r'\*\*Appearance:\*\*\s*(.+)'),
        "snack":        extract(r'\*\*Snack:\*\*\s*(.+)'),
        "traits":       extract(r'\*\*Traits:\*\*\s*(.+)'),
        "core_belief":  extract(r'\*\*Core Belief:\*\*\s*(.+)'),
        "enchanted":    _extract_enchanted_objects(content),
        "raw":          content[:600],
    }


def _extract_enchanted_objects(content: str) -> str:
    m = re.search(r'## Enchanted Objects\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip()[:300]


def call_agent(prompt: str) -> str:
    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True, timeout=180
    )
    output = result.stdout.strip()
    # Strip ANSI codes
    import re as _re
    ansi = _re.compile(r'\x1b\[[0-9;]*m')
    output = ansi.sub('', output)
    # Strip plugin noise
    noise = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    clean = [l for l in output.splitlines()
             if not any(l.strip().lower().startswith(p) for p in noise)]
    return "\n".join(clean).strip()


# ── Generation ────────────────────────────────────────────────────────────────

CHAPTER_FEEL = {
    "Riddlewind":  "wind from a cracked window, pages turning on their own, "
                   "the color of sky just before rain, the feeling of a sentence "
                   "that completes itself without you",
    "Duskthorn":   "edged light, shadows with opinions, the satisfying weight "
                   "of a difficult truth, warmth earned not given",
    "Emberheart":  "amber lamplight, the smell of something baking, "
                   "a room that wants to be lived in loudly",
    "Mossbloom":   "green light through glass, something growing on the windowsill, "
                   "the hush of a room that listens",
    "Tidecrest":   "the sound of water somewhere, shifting light, "
                   "the feeling of being between things",
}


def generate_dorm(player: dict, season: str, dry_run: bool = False) -> str:
    chapter_feel = CHAPTER_FEEL.get(player["chapter"], "the atmosphere of this chapter")

    prompt = f"""You are the Labyrinth of Stories, writing the permanent dorm room for a player.

This room is written ONCE and lasts forever — it is the physical expression of who this person is.
It must feel unmistakably like them. Not a generic Academy dorm. Their room.

PLAYER DATA:
- Name: {player['name']}
- Chapter: {player['chapter']}
- Anchor Object: {player['anchor']}
- Appearance: {player['appearance']}
- Snack/drink: {player['snack']}
- Traits & interests: {player['traits']}
- Core Belief: {player['core_belief']}
- Enchanted Objects: {player['enchanted'] or 'none yet'}

CHAPTER FEEL for {player['chapter']}: {chapter_feel}
CURRENT SEASON: {season}

Write two things:

1. STATIC DESCRIPTION (4–6 sentences, present tense):
The permanent soul of the room — the window, the desk, the light, the smell.
What is always true here regardless of season or story. This is what the player
returns to. It should contain at least one detail from their appearance, one from
their traits/interests translated into Academy terms, and one from their core belief
embedded in the physical space. The Anchor Object lives on the desk. Write it as
prose, not a list. Never use the word "cozy."

2. OBJECTS ON THE DESK (3–5 items, one per line, starting with "- "):
The permanent objects. Begins with the Anchor Object. Then 2–4 more that emerge
from their character — not inventory items, but things that are simply always there.
Each item in italics followed by one sentence of felt description.
Example format:
- *The Obsidian Chronograph* — cool and heavy, precisely angled, watching.

Output EXACTLY this format — no preamble:

STATIC:
[4–6 sentence description]

DESK:
[- items]"""

    if dry_run:
        print("\n[DRY RUN — prompt only, no agent call]\n")
        print(prompt)
        return ""

    print("  Generating dorm description...")
    return call_agent(prompt)


def write_dorm_to_player(player_name: str, generated: str):
    """Parse generated output and write into players/[name].md."""
    player_path = WORKSPACE / "players" / f"{player_name}.md"
    if not player_path.exists():
        print(f"❌ Player file not found: {player_path}")
        return

    content = player_path.read_text()

    # Parse sections from generated output
    static_m = re.search(r'STATIC:\n(.*?)(?=\nDESK:|\Z)', generated, re.DOTALL)
    desk_m   = re.search(r'DESK:\n(.*?)(?=\Z)', generated, re.DOTALL)

    static_text = static_m.group(1).strip() if static_m else generated.strip()
    desk_items  = desk_m.group(1).strip() if desk_m else ""

    today = datetime.now().strftime("%Y-%m-%d")

    # Replace the static description placeholder
    static_replacement = f"**Static description:** *Generated {today}.*\n\n{static_text}"
    content = re.sub(
        r'\*\*Static description:\*\*.*?(?=\n\*\*Objects|\n\n\*\*|$)',
        static_replacement,
        content, flags=re.DOTALL
    )

    # Replace the Anchor Object placeholder on the desk
    if desk_items:
        desk_replacement = f"**Objects on the desk:**\n{desk_items}"
        content = re.sub(
            r'\*\*Objects on the desk:\*\*.*?(?=\n\n|\*\*Dynamic|\Z)',
            desk_replacement,
            content, flags=re.DOTALL
        )

    player_path.write_text(content)
    print(f"  ✓ Dorm written → {player_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate player dorm room description.")
    parser.add_argument("player", nargs="?", default="bj", help="Player name")
    parser.add_argument("--season", choices=["spring", "summer", "autumn", "winter"],
                        help="Override current season")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt, no generation")
    args = parser.parse_args()

    player_name = args.player
    season      = args.season or get_current_season()

    print(f"\n  Dorm generator — {player_name} ({season})")

    player = load_player_data(player_name)

    if not player["chapter"] or player["chapter"] == "Unknown":
        print("  ⚠ Player has no chapter assigned yet. "
              "Run at T13 or later when chapter is known.")
        return

    generated = generate_dorm(player, season, dry_run=args.dry_run)

    if generated and not args.dry_run:
        print(f"\n  Generated:\n{'─'*40}")
        print(generated[:600])
        print(f"{'─'*40}")
        write_dorm_to_player(player_name, generated)
        print(f"\n  ✓ {player_name}'s dorm room is now permanent.")


if __name__ == "__main__":
    main()
