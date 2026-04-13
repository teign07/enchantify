#!/usr/bin/env python3
"""
arc-tick.py — Arc day counter and phase transition monitor.

Reads lore/current-arc.md, calculates real elapsed days since the arc started,
updates the ## Day: N line, and writes a tick-queue priority seed when the arc
crosses a phase transition threshold.

Does NOT auto-advance phases — that requires narrative judgment from the Labyrinth.
Instead it flags the transition as [PRIORITY: HIGH] so the Labyrinth can surface
it at the next session open.

Phase thresholds (default):
  SETUP     → RISING    at Day 5
  RISING    → CLIMAX    at Day 12
  CLIMAX    → FALLING   at Day 16
  FALLING   → RESOLUTION at Day 20

Usage:
  python3 scripts/arc-tick.py            # normal run
  python3 scripts/arc-tick.py --dry-run  # print what would change, no writes
  python3 scripts/arc-tick.py --status   # just print current arc state
"""

import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
ARC_FILE   = BASE_DIR / "lore" / "current-arc.md"
QUEUE_FILE = BASE_DIR / "memory" / "tick-queue.md"

# Real-world days before the arc should transition to the next phase.
# These are soft thresholds — the Labyrinth decides when to pull the trigger.
PHASE_THRESHOLDS = {
    "SETUP":    5,
    "RISING":   12,
    "CLIMAX":   16,
    "FALLING":  20,
}

PHASE_ORDER = ["SETUP", "RISING", "CLIMAX", "FALLING", "RESOLUTION"]

PHASE_TRANSITION_NOTES = {
    "SETUP": (
        "RISING",
        "The arc has been building for {day} days. The seeds are planted. "
        "The story is ready to escalate — NPCs acting on their own agendas, "
        "complications arriving uninvited. Consider advancing to RISING."
    ),
    "RISING": (
        "CLIMAX",
        "The arc has been rising for {day} days. Pressure is near its peak. "
        "The Nothing is strongest; the decision point is close. "
        "Consider advancing to CLIMAX — no comfort moves, force a choice."
    ),
    "CLIMAX": (
        "FALLING",
        "The arc has been at climax for {day} days. Something has to give. "
        "The player has faced the decision or avoided it — either way, "
        "consequences are accumulating. Consider advancing to FALLING."
    ),
    "FALLING": (
        "RESOLUTION",
        "The arc has been falling for {day} days. The world is adjusting. "
        "The player has seen what their choice cost. "
        "Consider advancing to RESOLUTION — let things settle, show the scar."
    ),
}


def read_arc():
    if not ARC_FILE.exists():
        return None, None
    text = ARC_FILE.read_text(encoding="utf-8")
    return text, ARC_FILE


def parse_arc_state(text):
    phase_m   = re.search(r"^## Phase:\s*(\w+)", text, re.MULTILINE)
    day_m     = re.search(r"^## Day:\s*(\d+)", text, re.MULTILINE)
    started_m = re.search(r"^## Started:\s*(.+)", text, re.MULTILINE)
    title_m   = re.search(r"^# Current Arc[^\n]*—\s*([^\n]+)", text)

    phase   = phase_m.group(1).upper().strip() if phase_m else "SETUP"
    day     = int(day_m.group(1)) if day_m else 1
    started = started_m.group(1).strip() if started_m else ""
    title   = title_m.group(1).strip() if title_m else "Unknown Arc"

    return phase, day, started, title


def parse_start_date(started_str):
    """Parse 'Sunday, April 5, 2026' → date object. Returns None on failure."""
    formats = [
        "%A, %B %d, %Y",   # Sunday, April 5, 2026
        "%B %d, %Y",        # April 5, 2026
        "%Y-%m-%d",         # 2026-04-05
    ]
    for fmt in formats:
        try:
            return datetime.strptime(started_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def elapsed_days(start_date):
    return (date.today() - start_date).days + 1  # Day 1 = the start day


def update_arc_day(text, new_day):
    """Replace ## Day: N with the new value. Returns updated text."""
    return re.sub(r"^(## Day:\s*)\d+", rf"\g<1>{new_day}", text, flags=re.MULTILINE)


def write_arc(text, dry_run=False):
    if dry_run:
        return
    tmp = ARC_FILE.with_suffix(".md.tmp")
    bak = ARC_FILE.with_suffix(".md.bak")
    shutil.copy2(ARC_FILE, bak)
    tmp.write_text(text, encoding="utf-8")
    tmp.rename(ARC_FILE)


def read_queue():
    if not QUEUE_FILE.exists():
        return ""
    return QUEUE_FILE.read_text(encoding="utf-8")


def write_queue(text, dry_run=False):
    if dry_run:
        return
    tmp = QUEUE_FILE.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.rename(QUEUE_FILE)


def queue_has_phase_seed(queue_text, phase):
    """Return True if there's already a phase transition seed in the queue."""
    return f"arc phase transition" in queue_text.lower() and phase in queue_text


def append_phase_seed(queue_text, phase, day, title, dry_run=False):
    """Append a [PRIORITY: HIGH] tick-queue entry for phase transition."""
    next_phase, note_template = PHASE_TRANSITION_NOTES[phase]
    note = note_template.format(day=day)

    seed = (
        f"\n- **[PRIORITY: HIGH]** Arc phase transition ready — *{title}*\n"
        f"  Current: {phase} (Day {day}) → Candidate: {next_phase}\n"
        f"  {note}\n"
        f"  *Labyrinth judgment required — advance the phase when the narrative is ready.*\n"
    )

    if dry_run:
        print(f"[arc-tick] Would append to tick-queue:\n{seed}")
        return queue_text

    new_text = queue_text.rstrip() + "\n" + seed + "\n"
    return new_text


def main():
    dry_run = "--dry-run" in sys.argv
    status  = "--status" in sys.argv

    text, arc_path = read_arc()
    if text is None:
        print("[arc-tick] No current-arc.md found — nothing to advance.")
        return

    phase, current_day, started, title = parse_arc_state(text)

    if status:
        print(f"Arc: {title}")
        print(f"Phase: {phase} · Day {current_day} · Started: {started}")
        start_date = parse_start_date(started)
        if start_date:
            real_day = elapsed_days(start_date)
            print(f"Real elapsed: Day {real_day} ({(date.today() - start_date).days} days since start)")
            threshold = PHASE_THRESHOLDS.get(phase)
            if threshold:
                print(f"Phase threshold: Day {threshold} → transition candidate")
                if real_day >= threshold:
                    print(f"  ⚠ THRESHOLD CROSSED — transition to next phase overdue")
        return

    start_date = parse_start_date(started)
    if start_date is None:
        print(f"[arc-tick] Could not parse start date: '{started}' — skipping day update.")
        return

    real_day = elapsed_days(start_date)

    # ── Update day counter ──────────────────────────────────────────────────────

    if real_day != current_day:
        if dry_run:
            print(f"[arc-tick] Would update Day: {current_day} → {real_day}")
        else:
            new_text = update_arc_day(text, real_day)
            write_arc(new_text)
            print(f"[arc-tick] {title}: Day {current_day} → {real_day}")
        text = update_arc_day(text, real_day)
    else:
        print(f"[arc-tick] {title}: Day {real_day} (up to date)")

    # ── Phase transition check ─────────────────────────────────────────────────

    if phase == "RESOLUTION":
        # No further transitions — arc is winding down
        print(f"[arc-tick] Phase: RESOLUTION — arc completing, no transition to flag.")
        return

    threshold = PHASE_THRESHOLDS.get(phase)
    if threshold is None:
        return

    if real_day >= threshold:
        queue_text = read_queue()

        if queue_has_phase_seed(queue_text, phase):
            print(f"[arc-tick] Phase transition seed already in queue — skipping duplicate.")
        else:
            next_phase = PHASE_TRANSITION_NOTES[phase][0]
            print(f"[arc-tick] Day {real_day} >= threshold {threshold}: flagging {phase} → {next_phase} transition")
            new_queue = append_phase_seed(queue_text, phase, real_day, title, dry_run=dry_run)
            if not dry_run:
                write_queue(new_queue)
                print(f"[arc-tick] [PRIORITY: HIGH] seed written to tick-queue.")


if __name__ == "__main__":
    main()
