#!/usr/bin/env python3
"""
_template/tick.py — Reference implementation for a skill-lore contract.

Copy to your skill-lore directory and fill in the three marked sections:
  1. FETCH     — read data from the real-world source
  2. TRANSLATE — turn each item into a narrative seed (one sentence)
  3. (write)   — handled by write_to_queue() — don't change this

Run by: python3 scripts/skill-scheduler.py --trigger cron
         python3 scripts/skill-scheduler.py --trigger session-open

Environment variables set by skill-scheduler.py:
  ENCHANTIFY_BASE_DIR   — absolute path to the enchantify workspace
  ENCHANTIFY_SKILL_ID   — this skill-lore's id (from manifest.md)
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Setup ─────────────────────────────────────────────────────────────────────

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent.parent))
SKILL_ID   = os.environ.get("ENCHANTIFY_SKILL_ID", "template")
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"

# Config — loaded from enchantify-config.sh by skill-scheduler.py before running.
# Replace with your actual config key from manifest.md.
SETTING = os.environ.get("ENCHANTIFY_TEMPLATE_SETTING", "")

if not SETTING:
    print(f"[{SKILL_ID}] Missing config: ENCHANTIFY_TEMPLATE_SETTING", file=sys.stderr)
    print(f"[{SKILL_ID}] Add it to scripts/enchantify-config.sh and re-run.", file=sys.stderr)
    sys.exit(0)  # Exit cleanly — never crash the tick run


# ── 1. FETCH ──────────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    """
    Read data from the real-world source.

    Return a list of dicts. Each dict = one thing worth narrating.
    Return [] if nothing new to report — that's normal and expected.

    Keep items factual and specific. The narrative interpretation
    happens in translate(), not here.

    Example return values:
      [{"raw": "Meeting: Quarterly review, 2pm tomorrow, 8 attendees"}]
      [{"raw": "Front door: opened 07:42, closed 07:44"}]
      [{"raw": "New note: On the nature of fog.md, 847 words"}]
    """
    # ── YOUR CODE HERE ────────────────────────────────────────────────────────
    return []


# ── 2. TRANSLATE ──────────────────────────────────────────────────────────────

def translate(item: dict) -> str:
    """
    Turn one raw data item into a narrative seed — one sentence.

    The seed describes what this *means* in the Academy world, not just
    what it is. The Labyrinth will read lore.md and this seed together
    to decide what to do with it.

    Write in present tense. Be specific. Don't over-dramatize — the
    Labyrinth handles the drama. Your job is to hand it a clear signal.

    Good: "A formal gathering is scheduled for tomorrow — eight voices, one agenda."
    Good: "Someone arrived home earlier than usual. The house held its breath."
    Good: "A new manuscript has appeared, still warm, title unclear."

    Bad:  "Something happened." (too vague)
    Bad:  "The darkness descends as the calendar reveals a meeting!" (overdone)
    """
    raw = item.get("raw", "")

    # ── YOUR CODE HERE ────────────────────────────────────────────────────────
    return f"Something from {SKILL_ID}: {raw}"


# ── Write ─────────────────────────────────────────────────────────────────────

def write_to_queue(items: list[dict]) -> None:
    """Append narrative seeds to tick-queue.md. Don't modify this."""
    if not items:
        print(f"[{SKILL_ID}] Nothing to report.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)

    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text(
            "# Tick Queue\n\n"
            "*Populated by skill-lore and tick.py. Read at session open. "
            "Cleared by clear-tick-queue.py.*\n\n---\n"
        )

    with TICK_QUEUE.open("a") as f:
        for item in items:
            seed = translate(item)
            f.write(
                f"\n## [{SKILL_ID}] {timestamp}\n"
                f"*Raw: {item.get('raw', '')}*\n"
                f"Narrative seed: {seed}\n"
            )

    print(f"[{SKILL_ID}] Wrote {len(items)} seed(s) to tick queue.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        items = fetch()
        write_to_queue(items)
    except Exception as e:
        # IMPORTANT: always exit cleanly — never crash the tick run
        print(f"[{SKILL_ID}] Error: {e}", file=sys.stderr)
        sys.exit(0)
