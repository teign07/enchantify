#!/usr/bin/env python3
"""
calendar/tick.py — Read iCal feed and write narrative seeds for upcoming events.

Reads ENCHANTIFY_ICAL_URL, looks at events in the next N days, and writes
one seed per notable event to tick-queue.md.

Requires: pip3 install icalendar requests
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

BASE_DIR   = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent.parent))
SKILL_ID   = os.environ.get("ENCHANTIFY_SKILL_ID", "calendar")
TICK_QUEUE = BASE_DIR / "memory" / "tick-queue.md"

ICAL_URL   = os.environ.get("ENCHANTIFY_ICAL_URL", "")
DAYS_AHEAD = int(os.environ.get("ENCHANTIFY_ICAL_DAYS_AHEAD", "2"))

if not ICAL_URL:
    print(f"[{SKILL_ID}] Missing config: ENCHANTIFY_ICAL_URL", file=sys.stderr)
    sys.exit(0)

try:
    import requests
    from icalendar import Calendar
except ImportError:
    print(f"[{SKILL_ID}] Missing dependencies. Run: pip3 install icalendar requests", file=sys.stderr)
    sys.exit(0)


def fetch_events() -> list[dict]:
    try:
        resp = requests.get(ICAL_URL, timeout=10)
        resp.raise_for_status()
        cal = Calendar.from_ical(resp.content)
    except Exception as e:
        print(f"[{SKILL_ID}] Failed to fetch calendar: {e}", file=sys.stderr)
        return []

    now    = datetime.now(timezone.utc)
    window = now + timedelta(days=DAYS_AHEAD)
    events = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        try:
            dtstart = component.get("DTSTART").dt
            dtend   = component.get("DTEND").dt

            # Normalize to timezone-aware datetime
            if hasattr(dtstart, "date") and not hasattr(dtstart, "hour"):
                # all-day event
                from datetime import date
                dtstart = datetime.combine(dtstart, datetime.min.time(), tzinfo=timezone.utc)
                dtend   = datetime.combine(dtend, datetime.min.time(), tzinfo=timezone.utc)
            elif dtstart.tzinfo is None:
                dtstart = dtstart.replace(tzinfo=timezone.utc)
                dtend   = dtend.replace(tzinfo=timezone.utc)

            if not (now <= dtstart <= window):
                continue

            summary    = str(component.get("SUMMARY", "Untitled"))
            attendees  = component.get("ATTENDEE", [])
            if not isinstance(attendees, list):
                attendees = [attendees] if attendees else []
            n_attendees = len(attendees)
            recurrence  = bool(component.get("RRULE"))
            duration_m  = int((dtend - dtstart).total_seconds() / 60)
            time_str    = dtstart.strftime("%a %b %-d, %-I:%M%p").lower()

            events.append({
                "summary":    summary,
                "time_str":   time_str,
                "attendees":  n_attendees,
                "recurring":  recurrence,
                "duration_m": duration_m,
                "dtstart":    dtstart,
            })
        except Exception:
            continue

    # Sort by start time, cap at 3
    events.sort(key=lambda e: e["dtstart"])
    return events[:3]


def translate(event: dict) -> tuple[str, str]:
    summary   = event["summary"]
    attendees = event["attendees"]
    recur     = event["recurring"]
    dur       = event["duration_m"]
    time_str  = event["time_str"]

    raw = (f"Event {time_str} — \"{summary}\" "
           f"({dur}min"
           f"{f', {attendees} attendees' if attendees > 1 else ''}"
           f"{', recurring' if recur else ''})")

    # Classify
    title_lower = summary.lower()
    if attendees >= 9:
        kind = "A convocation"
    elif attendees >= 3:
        kind = "A formal gathering"
    elif attendees == 2:
        kind = "A private audience"
    elif dur >= 120:
        kind = "A long stretch of dedicated work"
    else:
        kind = "An appointment"

    cadence = "recurring, part of an established ritual" if recur else "a one-time event"
    seed = f"{kind} is scheduled for {time_str} — \"{summary}\" ({cadence}, {dur} minutes)."

    return raw, seed


def write_to_queue(events: list[dict]) -> None:
    if not events:
        print(f"[{SKILL_ID}] No events in next {DAYS_AHEAD} day(s).")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)

    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text(
            "# Tick Queue\n\n"
            "*Populated by skill-lore and tick.py. Read at session open.*\n\n---\n"
        )

    with TICK_QUEUE.open("a") as f:
        for event in events:
            raw, seed = translate(event)
            f.write(
                f"\n## [{SKILL_ID}] {timestamp}\n"
                f"*Raw: {raw}*\n"
                f"Narrative seed: {seed}\n"
            )

    print(f"[{SKILL_ID}] Wrote {len(events)} event(s) to tick queue.")


if __name__ == "__main__":
    try:
        write_to_queue(fetch_events())
    except Exception as e:
        print(f"[{SKILL_ID}] Error: {e}", file=sys.stderr)
        sys.exit(0)
