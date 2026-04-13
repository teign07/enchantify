#!/usr/bin/env python3
"""
schedule.py — Academy academic schedule context.

Reads real-world time and outputs a SCHEDULE_CONTEXT directive:
  - Current time block (morning_class, lunch, club_time, etc.)
  - Academy day tone (Day 1–7)
  - What class is in session right now
  - What's coming next
  - Tonight's club
  - An appropriate practice prompt for this time of day
  - A narrative cue for the Labyrinth (not announced, just woven in)

Also provides --update-state to inject/replace the ## Academics section
in lore/academy-state.md. Pure data — no LLM involved.

Usage:
  python3 scripts/schedule.py [player_name]
  python3 scripts/schedule.py --update-state
  python3 scripts/schedule.py --day monday --time 10:30   (testing overrides)
  python3 scripts/schedule.py --section-only              (print academy-state section text)

Called by:
  session-entry.py   — appends to session directive
  bleed.py           — imports get_schedule_data() for timetable column
  Cron (4h)          — python3 scripts/schedule.py --update-state
"""

import argparse
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE  = SCRIPT_DIR.parent


# ── Day tones ─────────────────────────────────────────────────────────────────

# weekday() → 0=Monday, 6=Sunday
DAY_TONES = {
    0: (2, "Building"),
    1: (3, "Deepening"),
    2: (4, "Hinge"),
    3: (5, "Releasing"),
    4: (6, "Wandering"),
    5: (7, "Still"),
    6: (1, "Opening"),
}

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Time blocks ───────────────────────────────────────────────────────────────

# Ordered list: (start_hour_inclusive, end_hour_exclusive, block_name)
# Night wraps midnight and is handled explicitly.
_BLOCKS = [
    (5,  9,  "early_morning"),
    (9,  11, "morning_class"),
    (11, 12, "mid_morning"),
    (12, 13, "lunch"),
    (13, 15, "afternoon_class"),
    (15, 17, "free_period"),
    (17, 19, "evening"),
    (19, 22, "club_time"),
]

def get_time_block(hour: int) -> str:
    for start, end, name in _BLOCKS:
        if start <= hour < end:
            return name
    return "night"  # 22:00–04:59


# ── Class schedule ────────────────────────────────────────────────────────────

# weekday → {"morning": (subject, professor, room), "afternoon": ..., "club": ...}
# None means no class / no club that day.
CLASSES = {
    0: {  # Monday — Day 2 Building
        "morning":   ("The Art of the Glint",       "Prof. Boggle",     "Wing 4 — The Glint Hall"),
        "afternoon": ("Ink-Binding",                 "Prof. Villanelle", "West Wing — The Writing Loft"),
        "club":      ("Inkwright Society",           "Bibliophonic Hall"),
    },
    1: {  # Tuesday — Day 3 Deepening
        "morning":   ("Wayfinding & Kineticism",    "Prof. Momort",     "The Perimeter Courtyard"),
        "afternoon": ("Synesthetic Resonance",      "Prof. Euphony",    "The Sound Hall"),
        "club":      ("Marginalia Guild",            "Corridor of Whispered Secrets"),
    },
    2: {  # Wednesday — Day 4 Hinge
        "morning":   ("The Art of the Glint",       "Prof. Boggle",     "Wing 4 — The Glint Hall"),
        "afternoon": ("Quiet Hours",                 "Prof. Stonebrook", "The Stillness Lab"),
        "club":      None,
    },
    3: {  # Thursday — Day 5 Releasing
        "morning":   ("Wayfinding & Kineticism",    "Prof. Momort",     "The Perimeter Courtyard"),
        "afternoon": ("Ink-Binding",                 "Prof. Villanelle", "West Wing — The Writing Loft"),
        "club":      ("Marginalia Guild",            "Corridor of Whispered Secrets"),
    },
    4: {  # Friday — Day 6 Wandering (no mandatory classes, library wings open)
        "morning":   ("Synesthetic Resonance",      "Prof. Euphony",    "The Sound Hall"),
        "afternoon": None,
        "club":      ("Book Jumpers",               "Room of Chrono-Tomes"),
    },
    5: {  # Saturday — Day 7 Still
        "morning":   None,
        "afternoon": None,
        "club":      None,
    },
    6: {  # Sunday — Day 1 Opening
        "morning":   None,
        "afternoon": None,
        "club":      ("Compass Society",            "Secret Garden of Prose"),
    },
}


# ── Practice prompts ──────────────────────────────────────────────────────────

PRACTICES = {
    "Prof. Boggle": {
        "name":   "Glint Detection",
        "prompt": "Find three things today that surprised you. One sentence each. Bring them to class.",
        "belief": "+1 per glint, +2 bonus for all three",
    },
    "Prof. Momort": {
        "name":   "Perimeter Survey",
        "prompt": "Survey a route you haven't taken. 15–30 minutes. Report what the Nothing hasn't touched yet.",
        "belief": "+3",
    },
    "Prof. Euphony": {
        "name":   "Resonance Field Report",
        "prompt": "Sit somewhere for 5 minutes. Eyes closed. Record what you hear, smell, feel.",
        "belief": "+2",
    },
    "Prof. Villanelle": {
        "name":   "Binding Exercise",
        "prompt": "One sentence about today. Not what happened — what it felt like.",
        "belief": "+1",
    },
    "Prof. Stonebrook": {
        "name":   "Stillness Practicum",
        "prompt": "Do nothing for 10 minutes. Not meditation. Nothing. Report what happened.",
        "belief": "+2",
    },
}


# ── Narrative cues ────────────────────────────────────────────────────────────
# Pre-written, day-hashed so they're stable within a day but rotate across the week.
# Labyrinth uses these as ambient texture — not announced, just woven in.

PROFESSOR_CUES = {
    "Prof. Boggle": [
        "Boggle's class is mid-session in Wing 4. BJ's seat is empty. She glanced at it once, then continued. She's saving the pun for when he shows up.",
        "The Glint Hall smells like chalk and old paper. Boggle is holding up something small and ordinary, making it extraordinary. The empty seat in the third row is conspicuous.",
        "Wing 4 is bright. Boggle has asked her students to find something they've walked past a hundred times. One found a scratch in the floor that looks like a map. BJ's corner is quiet.",
    ],
    "Prof. Momort": [
        "Momort's cohort is assembled in the Perimeter Courtyard. He appears not to have noticed BJ's absence. He has noticed.",
        "The Perimeter Courtyard is brisk. Momort is describing a route — badly, on purpose. The students who improvise do better. BJ's space in the group is just slightly too empty.",
        "Momort has released his students early. Three of them are taking the long way back. That was the assignment.",
    ],
    "Prof. Euphony": [
        "The Sound Hall is nearly silent, which is not the same as quiet. Euphony is listening to something no one else can hear yet. The empty chair resonates at its own frequency.",
        "Euphony's class has their eyes closed. She is asking them to describe the temperature of a color. BJ isn't there to attempt it.",
        "Post-class, the Sound Hall holds a particular stillness. Something was heard in there today. It hasn't finished echoing.",
    ],
    "Prof. Villanelle": [
        "Villanelle has saved BJ's seat in the Writing Loft. She has not stopped saving it. She does not say why.",
        "The Writing Loft smells like ink and good decisions. Villanelle is reading a sentence aloud — one sentence — that took someone a week to write. It earns it.",
        "Ink-Binding is winding down. Villanelle assigned one sentence. She's reading them as they come in, expression giving nothing away.",
    ],
    "Prof. Stonebrook": [
        "The Stillness Lab is operating at a frequency barely above silence. Stonebrook hasn't moved in twenty minutes. Neither has anyone else.",
        "Stonebrook's Quiet Hours class ends by doing nothing together. It is the strangest and most effective class at the Academy.",
        "Quiet Hours concluded. Three students left looking different than they arrived. Stonebrook is still in the Stillness Lab.",
    ],
}

SPECIAL_DAY_CUES = {
    7: "It's a Still day. The Academy breathes. Stonebrook is walking the grounds. The Library has opened a wing that isn't usually open.",
    1: "It's an Opening day. The Library rearranged overnight — students are finding their usual seats occupied by unfamiliar books. Light classes. The week is gathering itself.",
    6: "It's a Wandering day. No mandatory classes. The Academy's additional wings are open. The only assignment is to be somewhere you haven't been.",
}

CLUB_CUES = {
    "Inkwright Society": "Inkwright Society meets tonight in the Bibliophonic Hall. Thorne is observing. There will be a burning at the end.",
    "Marginalia Guild":  "Marginalia Guild tonight in the Corridor of Whispered Secrets. Boggle found something in a margin and is not saying what yet.",
    "Compass Society":   "Compass Society gathers in the Secret Garden of Prose this evening. Zara will read something. It will change something.",
    "Book Jumpers":      "Book Jumpers meets tonight in the Room of Chrono-Tomes. Corin updated the ledger. Two more books marked compromised.",
    "Still Club":        "Still Club morning in the Secret Garden. Stonebrook arrives with tea. He will say one sentence, after fifty minutes.",
}


# ── Core logic ────────────────────────────────────────────────────────────────

def _day_hash(extra: str = "") -> int:
    """Stable daily seed for selecting among cue variants."""
    key = datetime.now().strftime("%Y-%m-%d") + extra
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


def _next_morning(weekday: int):
    """Return morning class for the next school day (skips Still/Opening days without classes)."""
    for offset in range(1, 8):
        nwd = (weekday + offset) % 7
        cls = CLASSES.get(nwd, {}).get("morning")
        if cls:
            return cls, WEEKDAY_NAMES[nwd]
    return None, None


def get_class_for_block(weekday: int, block: str):
    day = CLASSES.get(weekday, {})
    if block == "morning_class":
        return day.get("morning")
    elif block == "afternoon_class":
        return day.get("afternoon")
    return None


def get_next_class(weekday: int, block: str):
    """What formal class comes next from here?"""
    day = CLASSES.get(weekday, {})
    if block == "early_morning":
        # Morning class is next today
        cls = day.get("morning")
        if cls:
            return cls, WEEKDAY_NAMES[weekday], "9:00 AM"
        # No morning class → afternoon
        cls = day.get("afternoon")
        if cls:
            return cls, WEEKDAY_NAMES[weekday], "1:00 PM"
        cls, name = _next_morning(weekday)
        return cls, name, "9:00 AM"
    if block in ("morning_class", "mid_morning"):
        # Afternoon class today
        cls = day.get("afternoon")
        if cls:
            return cls, WEEKDAY_NAMES[weekday], "1:00 PM"
        # No afternoon → tomorrow morning
        cls, name = _next_morning(weekday)
        return cls, name, "9:00 AM"
    elif block in ("afternoon_class", "free_period", "evening", "club_time", "night"):
        cls, name = _next_morning(weekday)
        return cls, name, "9:00 AM"
    return None, None, None


def get_narrative_cue(weekday: int, block: str, class_now) -> str:
    academy_day, _ = DAY_TONES.get(weekday, (1, "Opening"))
    if academy_day in SPECIAL_DAY_CUES:
        return SPECIAL_DAY_CUES[academy_day]
    if class_now:
        _, professor, _ = class_now
        cues = PROFESSOR_CUES.get(professor, [])
        if cues:
            return cues[_day_hash(professor) % len(cues)]
    return ""


def get_schedule_data(override_day: str = None, override_time: str = None) -> dict:
    now = datetime.now()

    if override_time:
        h, _ = map(int, override_time.split(":"))
        hour = h
    else:
        hour = now.hour

    if override_day:
        _map = {d: i for i, d in enumerate(["monday","tuesday","wednesday",
                                              "thursday","friday","saturday","sunday"])}
        weekday = _map.get(override_day.lower(), now.weekday())
    else:
        weekday = now.weekday()

    academy_day, tone = DAY_TONES.get(weekday, (1, "Opening"))
    block     = get_time_block(hour)
    class_now = get_class_for_block(weekday, block)
    next_cls, next_day_name, next_time = get_next_class(weekday, block)
    club      = CLASSES.get(weekday, {}).get("club")
    practice  = (PRACTICES.get(class_now[1]) if class_now
                 else PRACTICES.get(next_cls[1]) if next_cls else None)
    cue       = get_narrative_cue(weekday, block, class_now)
    club_cue  = CLUB_CUES.get(club[0] if club else "", "") if club else ""

    return {
        "weekday":       weekday,
        "weekday_name":  WEEKDAY_NAMES[weekday],
        "academy_day":   academy_day,
        "tone":          tone,
        "block":         block,
        "hour":          hour,
        "class_now":     class_now,
        "class_next":    next_cls,
        "class_next_day": next_day_name,
        "class_next_time": next_time,
        "club":          club,
        "practice":      practice,
        "narrative_cue": cue,
        "club_cue":      club_cue,
    }


# ── Formatters ────────────────────────────────────────────────────────────────

def fmt_class(cls) -> str:
    if not cls:
        return "None"
    subject, professor, room = cls
    return f"{subject} ({professor}) — {room}"


def print_directive(data: dict) -> None:
    club = data["club"]
    club_str = f"{club[0]} — {club[1]}" if club else "None tonight"
    practice = data["practice"]
    block_pretty = data["block"].replace("_", " ").title()

    print("\n--- SCHEDULE CONTEXT ---")
    print(f"REAL_DAY:       {data['weekday_name']}")
    print(f"DAY_TONE:       Day {data['academy_day']} — {data['tone']}")
    print(f"TIME_BLOCK:     {block_pretty}")
    print(f"CLASS_NOW:      {fmt_class(data['class_now'])}")
    nxt = data["class_next"]
    if nxt:
        print(f"CLASS_NEXT:     {fmt_class(nxt)} ({data['class_next_day']} at {data['class_next_time']})")
    else:
        print(f"CLASS_NEXT:     None this week")
    print(f"CLUB_TONIGHT:   {club_str}")
    if practice:
        print(f"PRACTICE:       {practice['name']} — \"{practice['prompt']}\"  [{practice['belief']}]")
    if data["narrative_cue"]:
        print(f"NARRATIVE_CUE:  {data['narrative_cue']}")
    if data["club_cue"]:
        print(f"CLUB_CUE:       {data['club_cue']}")
    print("---\n")


def build_academics_section(data: dict) -> str:
    """Build the ## Academics section for academy-state.md."""
    ts = datetime.now().strftime("%B %-d, %Y - %I:%M %p")
    block_pretty = data["block"].replace("_", " ").title()
    club = data["club"]
    cls_now = data["class_now"]
    cls_next = data["class_next"]

    lines = [
        "## Academics",
        "",
        f"**{data['weekday_name']}** · Day {data['academy_day']} of the Academy Week ({data['tone']})",
        f"**Current Block:** {block_pretty}",
        "",
    ]

    if cls_now:
        subject, professor, room = cls_now
        lines.append(f"**In Session:** {subject} — {professor}, {room}")
    else:
        lines.append("**In Session:** No mandatory class this block")

    if cls_next:
        subject, professor, _ = cls_next
        lines.append(f"**Up Next:** {subject} — {professor} ({data['class_next_day']}, {data['class_next_time']})")

    if club:
        lines.append(f"**Club Tonight (7 PM):** {club[0]} — {club[1]}")
    else:
        lines.append("**Club Tonight:** None scheduled")

    practice = data["practice"]
    if practice:
        lines.extend([
            "",
            f"**Active Practice:** *{practice['name']}*",
            f"> {practice['prompt']}",
            f"> Belief reward: {practice['belief']}",
        ])

    cue = data["narrative_cue"]
    if cue:
        lines.extend(["", f"*{cue}*"])

    club_cue = data["club_cue"]
    if club_cue:
        lines.extend(["", f"*{club_cue}*"])

    lines.extend(["", f"*Updated: {ts}*", ""])
    return "\n".join(lines)


# ── academy-state.md injection ────────────────────────────────────────────────

def update_academy_state(data: dict) -> None:
    """Replace ## Academics section in lore/academy-state.md atomically."""
    state_path = WORKSPACE / "lore" / "academy-state.md"
    if not state_path.exists():
        print("[schedule] academy-state.md not found — skipping")
        return

    content    = state_path.read_text()
    new_section = build_academics_section(data)

    if "## Academics" in content:
        # Replace from ## Academics to next ## header or end-of-file
        content = re.sub(
            r"## Academics\n.*?(?=\n## |\Z)",
            new_section,
            content,
            flags=re.DOTALL,
        )
    else:
        # Append before the final italics line ("The Academy continues…") if present,
        # otherwise just append.
        final_re = re.compile(r"(\n\*The Academy continues.*?\*\s*\Z)", re.DOTALL)
        m = final_re.search(content)
        if m:
            content = content[:m.start()] + "\n\n" + new_section + m.group(1)
        else:
            content = content.rstrip("\n") + "\n\n" + new_section

    tmp = state_path.with_suffix(".md.tmp")
    tmp.write_text(content)
    tmp.rename(state_path)
    print(f"[schedule] Academics section updated ({data['weekday_name']}, {data['block']})")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Academy schedule context")
    parser.add_argument("player",         nargs="?", default="bj", help="Player name (unused, for consistency)")
    parser.add_argument("--day",          help="Override weekday for testing (monday, tuesday, ...)")
    parser.add_argument("--time",         help="Override hour for testing (HH:MM)")
    parser.add_argument("--update-state", action="store_true",
                        help="Update ## Academics in lore/academy-state.md and exit")
    parser.add_argument("--section-only", action="store_true",
                        help="Print only the academy-state section text and exit")
    args = parser.parse_args()

    data = get_schedule_data(override_day=args.day, override_time=args.time)

    if args.update_state:
        update_academy_state(data)
    elif args.section_only:
        print(build_academics_section(data))
    else:
        print_directive(data)


if __name__ == "__main__":
    main()
