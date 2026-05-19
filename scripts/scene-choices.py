#!/usr/bin/env python3
"""
scene-choices.py — validate and strip Rule of Three category tags from a scene file.

The agent MUST tag each of the three choices with [LIFE], [ARC], or [SURPRISE]
before calling this script. This enforces the Rule of Three format and strips
the tags from the scene file so players never see them.

Category definitions:
  [LIFE]     Slice of life — grounded, ordinary, human. Even in a crisis this option
             lives in the mundane: someone suggests tea, checks on a detail in the room,
             asks how the other person is holding up. Never advances the plot directly.
  [ARC]      Story thread — advances the current investigation, quest, or main arc.
             The expected move. What the momentum of the scene is already pointing toward.
  [SURPRISE] Surprising or sideways — leaves the current thread entirely or reframes it
             from an unexpected angle. Goes somewhere no one expected. Not random, but
             genuinely off the established path.

Usage:
  python3 scripts/scene-choices.py --scene-file /tmp/enchantify-scene.txt

Exit codes:
  0 — all three categories present, tags stripped and file updated
  1 — missing categories; scene must be revised before delivery
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED = {"LIFE", "ARC", "SURPRISE"}
TAG_RE = re.compile(r"\[(LIFE|ARC|SURPRISE)\]\s*", re.IGNORECASE)
PLOT_WORDS = {
    "investigate", "investigation", "nothing", "duskthorn", "wicker", "threat",
    "attack", "clue", "reveal", "accuse", "confront", "quest", "mission",
    "shadow", "danger", "restricted", "solve", "mystery", "drawer", "letter",
    "note", "mark", "marked", "symbol", "seam",
}
LIFE_WORDS = {
    "tea", "snack", "breakfast", "lunch", "dinner", "sleep", "rest", "laundry",
    "desk", "window", "weather", "blanket", "chair", "mug", "homework", "class",
    "walk", "breathe", "tired", "hungry", "okay", "alright", "room", "table",
    "slow", "slower", "pause", "explain", "listen", "gathered", "stay", "sit",
}
SURPRISE_WORDS = {
    "follow", "sound", "draft", "door", "corridor", "outside", "unexpected",
    "sideways", "ask", "instead", "leave", "turn", "strange", "unrelated",
}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z']+", text.lower()))


def _tagged_choice_bodies(text: str) -> dict[str, str]:
    choices: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"\[(LIFE|ARC|SURPRISE)\]\s*(.+)", line, re.IGNORECASE)
        if not m:
            continue
        label = m.group(1).upper()
        body = m.group(2).strip()
        if not body and i + 1 < len(lines):
            body = lines[i + 1].strip()
        choices[label] = body
    return choices


def _balance_failures(text: str) -> list[str]:
    choices = _tagged_choice_bodies(text)
    failures: list[str] = []
    if REQUIRED - set(choices):
        return failures

    life = _words(choices["LIFE"])
    arc = _words(choices["ARC"])
    surprise = _words(choices["SURPRISE"])
    if not (life & LIFE_WORDS):
        failures.append("[LIFE] needs a concrete ordinary care/action beat")
    if life & PLOT_WORDS and not life & LIFE_WORDS:
        failures.append("[LIFE] reads plot-forward; make it mundane")
    if not (arc & PLOT_WORDS):
        failures.append("[ARC] should clearly touch the current story thread")
    if not (surprise & SURPRISE_WORDS):
        failures.append("[SURPRISE] should move sideways or reframe the scene")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Rule of Three tags and strip them from the scene file."
    )
    parser.add_argument("--scene-file", type=Path, required=True)
    parser.add_argument(
        "--strict-balance",
        action="store_true",
        help="Also check that LIFE is mundane, ARC is plot-facing, and SURPRISE is sideways.",
    )
    args = parser.parse_args()

    if not args.scene_file.exists():
        sys.stderr.write(f"scene-choices: file not found: {args.scene_file}\n")
        return 1

    text = args.scene_file.read_text(encoding="utf-8")

    found = {m.group(1).upper() for m in TAG_RE.finditer(text)}
    missing = REQUIRED - found

    if missing:
        sys.stderr.write(
            f"CHOICE VALIDATION FAILED — missing: {', '.join(f'[{t}]' for t in sorted(missing))}\n"
            "Tag all three choices before delivery:\n"
            "  *(1) [LIFE] ...\n"
            "  *(2) [ARC] ...\n"
            "  *(3) [SURPRISE] ...\n"
            "Categories:\n"
            "  [LIFE]     — grounded, ordinary, mundane. Never plot-advancing.\n"
            "  [ARC]      — advances the current thread or main arc.\n"
            "  [SURPRISE] — sideways, unexpected, off the established path.\n"
        )
        return 1

    if args.strict_balance:
        failures = _balance_failures(text)
        if failures:
            sys.stderr.write("CHOICE BALANCE FAILED\n")
            for failure in failures:
                sys.stderr.write(f"- {failure}\n")
            return 1

    cleaned = TAG_RE.sub("", text)
    args.scene_file.write_text(cleaned, encoding="utf-8")
    print(f"CHOICE VALIDATION OK — [LIFE] [ARC] [SURPRISE] all present. Tags stripped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
