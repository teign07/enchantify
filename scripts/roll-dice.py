#!/usr/bin/env python3
"""
roll-dice.py — True random d100 for Enchantify.
The Labyrinth calls this and narrates the result — it does not pick the number.

Usage: python3 scripts/roll-dice.py [belief] [difficulty]

  belief:     Current Belief score (0-100). Defaults to 50.
  difficulty: routine | standard | dramatic | desperate
              Defaults to standard.

Examples:
  python3 scripts/roll-dice.py 34
  python3 scripts/roll-dice.py 70 dramatic
  python3 scripts/roll-dice.py 34 desperate
"""
import sys
from dice import roll_d100, DIFFICULTY_MODIFIERS

OUTCOME_ICONS = {
    "CRITICAL_SUCCESS": "✨",
    "SUCCESS":          "✅",
    "NEAR_MISS":        "⚡",
    "FAILURE":          "❌",
    "CRITICAL_FAILURE": "💀",
}

OUTCOME_GUIDANCE = {
    "CRITICAL_SUCCESS": (
        "Something spectacular happens beyond what the player hoped for. "
        "Award +2 extra Belief on top of any normal reward. "
        "Surprise everyone, including yourself."
    ),
    "SUCCESS": "Narrate the positive outcome. Award Belief if the action warranted it.",
    "NEAR_MISS": (
        "Near miss. Consider a partial success or interesting complication "
        "rather than outright failure — something was almost enough. "
        "Deduct Belief if the stakes called for it."
    ),
    "FAILURE": (
        "Clear failure. Narrate the consequence with narrative interest — "
        "open a new path, reveal information, or create a complication worth exploring. "
        "Deduct Belief if the stakes called for it."
    ),
    "CRITICAL_FAILURE": (
        "Something goes dramatically wrong — but create story, not punishment. "
        "The spell backfires into a revelation. The fall lands somewhere unexpected. "
        "Critical failures are plot generators."
    ),
}


def main():
    try:
        belief = int(sys.argv[1])
    except (IndexError, ValueError):
        belief = 50

    difficulty = sys.argv[2].lower() if len(sys.argv) > 2 else "standard"
    if difficulty not in DIFFICULTY_MODIFIERS:
        print(f"⚠️  Unknown difficulty '{difficulty}'. Using 'standard'.")
        difficulty = "standard"

    r = roll_d100(belief, difficulty)
    icon     = OUTCOME_ICONS[r["outcome"]]
    guidance = OUTCOME_GUIDANCE[r["outcome"]]
    margin_str = f"{abs(r['margin'])} {'under' if r['margin'] <= 0 else 'over'}"

    print(f"\n--- DICE ROLL ---")
    print(f"Belief:     {r['belief']}  |  Difficulty: {r['difficulty']}")
    print(f"Threshold:  ≤ {r['threshold']} to succeed")
    print(f"Rolled:     {r['roll']}  →  {icon} {r['outcome']}  (margin: {margin_str})")
    if r["outcome"] == "NEAR_MISS":
        print(f"⚡ NEAR MISS")
    print(f"Guidance:   {guidance}")
    print(f"--- END ROLL ---\n")


if __name__ == "__main__":
    main()
