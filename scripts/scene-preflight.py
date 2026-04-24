#!/usr/bin/env python3
"""
scene-preflight.py — verify named characters and voice assignments before a scene reply.

Usage:
  python3 scripts/scene-preflight.py --speaker "Zara Finch" --speaker "Professor Lydia Boggle"
  python3 scripts/scene-preflight.py --speaker "Zara Finch" --expect-voice "Zara Finch=af_nicole"
  python3 scripts/scene-preflight.py --speaker "Mara" --strict

Checks:
- character appears in project lore/player files
- character has a voice assignment in config/voice-assignments.md
- optional expected voice matches assigned voice
- notes whether character is active in lore/academy-state.md right now

Exit code:
- 0 when all requested checks pass
- 1 when any strict check fails
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
VOICE_FILE = BASE / "config" / "voice-assignments.md"
ACADEMY_STATE = BASE / "lore" / "academy-state.md"
SEARCH_DIRS = [BASE / "lore", BASE / "players", BASE / "memory"]


def normalize_name(name: str) -> str:
    clean = name.strip()
    clean = re.sub(r"\s*\([^)]*\)", "", clean).strip()
    clean = clean.replace('“', '"').replace('”', '"')
    clean = clean.replace('.', '')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.lower()


def alias_forms(name: str) -> set[str]:
    clean = re.sub(r"\s*\([^)]*\)", "", name).strip()
    forms = {clean, clean.lower()}
    variants = {clean}
    if clean.lower().startswith('professor '):
        variants.add(re.sub(r'^Professor\s+', 'Prof. ', clean, flags=re.IGNORECASE).strip())
    if clean.lower().startswith('prof. '):
        variants.add(re.sub(r'^Prof\.\s+', 'Professor ', clean, flags=re.IGNORECASE).strip())
    for pattern in [r"^Professor\s+", r"^Prof\.\s+", r"^Headmistress\s+", r"^Headmaster\s+"]:
        next_variants = set()
        for item in variants:
            next_variants.add(re.sub(pattern, "", item, flags=re.IGNORECASE).strip())
        variants |= next_variants
    for item in variants:
        item = item.strip()
        if item:
            forms.add(item)
            forms.add(item.lower())
            parts = item.split()
            if parts:
                forms.add(parts[-1])
                forms.add(parts[-1].lower())
                if len(parts) >= 2:
                    forms.add(" ".join(parts[-2:]))
                    forms.add(" ".join(parts[-2:]).lower())
    nickname = re.search(r'"([^"]+)"', clean)
    if nickname:
        forms.add(nickname.group(1))
        forms.add(nickname.group(1).lower())
    return {f for f in forms if f}


def load_voice_map() -> dict[str, str]:
    text = VOICE_FILE.read_text(encoding="utf-8")
    voice_map: dict[str, str] = {}

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- **") and "`" in line:
            m = re.match(r"-\s+\*\*(.+?)\*\*:?\s+`([^`]+)`", line)
            if not m:
                continue
            name = m.group(1).strip().rstrip(":").strip()
            voice = m.group(2).strip()
            for form in alias_forms(name):
                voice_map[normalize_name(form)] = voice

        elif line.startswith("|") and "`" in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 2 and parts[0].startswith("`") and parts[0].endswith("`"):
                voice = parts[0].strip("`").strip()
                name = parts[1]
                for form in alias_forms(name):
                    voice_map[normalize_name(form)] = voice

    return voice_map


def search_name(name: str) -> list[str]:
    hits: list[str] = []
    needle = name.lower()
    for root in SEARCH_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if needle in text.lower():
                hits.append(str(path.relative_to(BASE)))
    return hits


def active_now(name: str) -> bool:
    if not ACADEMY_STATE.exists():
        return False
    text = ACADEMY_STATE.read_text(encoding="utf-8", errors="ignore")
    for form in alias_forms(name):
        if f"**{form}**" in text or form in text:
            return True
    return False


def parse_expected(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --expect-voice value: {item!r}. Use 'Name=voice'.")
        name, voice = item.split("=", 1)
        result[name.strip()] = voice.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--speaker", action="append", default=[], help="Named speaking character to verify")
    parser.add_argument("--expect-voice", action="append", default=[], help="Expected mapping in the form Name=voice")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any speaker is missing or mismatched")
    args = parser.parse_args()

    if not args.speaker:
        print("No speakers supplied. Pass one or more --speaker values.")
        return 1

    voice_map = load_voice_map()
    expected = parse_expected(args.expect_voice)
    failures = 0

    for speaker in args.speaker:
        print(f"SPEAKER: {speaker}")
        hits = search_name(speaker)
        if hits:
            print(f"  lore: OK ({', '.join(hits[:6])})")
        else:
            print("  lore: MISSING")
            failures += 1

        assigned = voice_map.get(normalize_name(speaker))
        if assigned:
            print(f"  voice: {assigned}")
        else:
            print("  voice: MISSING")
            failures += 1

        if speaker in expected and assigned != expected[speaker]:
            print(f"  expected: {expected[speaker]} (MISMATCH)")
            failures += 1
        elif speaker in expected:
            print(f"  expected: {expected[speaker]} (match)")

        print(f"  active_now: {'yes' if active_now(speaker) else 'no'}")

    if failures:
        print(f"\nRESULT: FAIL ({failures} issue{'s' if failures != 1 else ''})")
        return 1 if args.strict else 0

    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
