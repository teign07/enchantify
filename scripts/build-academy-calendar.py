#!/usr/bin/env python3
"""
build-academy-calendar.py — generate the Enchantify Academy iCalendar feed.

The schedule source of truth is scripts/schedule.py. This script writes the
public .ics file used by Apple Calendar so Mission Control, active play, the
Bleed, and the calendar stay in one timetable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import sys

BASE = Path(__file__).parent.parent
HOOKS = BASE / "hooks"
OUT = HOOKS / "enchantify_schedule.ics"

sys.path.insert(0, str(BASE / "scripts"))
import schedule  # type: ignore  # noqa: E402

TZID = "America/New_York"

# Dates from the original feed's first academy week. RRULE handles recurrence.
WEEK_STARTS = {
    0: "20260413",  # Monday
    1: "20260414",
    2: "20260415",
    3: "20260416",
    4: "20260417",
    5: "20260418",
    6: "20260412",  # Sunday
}

SLOTS = {
    "morning": ("090000", "110000"),
    "afternoon": ("130000", "150000"),
    "club": ("190000", "200000"),
}

BYDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

UIDS = {
    (0, "morning"): "enchantify-event-0@academy",
    (0, "afternoon"): "enchantify-event-1@academy",
    (0, "club"): "enchantify-event-2@academy",
    (1, "morning"): "enchantify-event-3@academy",
    (1, "afternoon"): "enchantify-event-4@academy",
    (1, "club"): "enchantify-event-5@academy",
    (2, "morning"): "enchantify-event-6@academy",
    (2, "afternoon"): "enchantify-event-7@academy",
    (3, "morning"): "enchantify-event-8@academy",
    (3, "afternoon"): "enchantify-event-9@academy",
    (3, "club"): "enchantify-event-10@academy",
    (4, "morning"): "enchantify-event-11@academy",
    (4, "afternoon"): "enchantify-event-12@academy",
    (4, "club"): "enchantify-event-13@academy",
    (6, "club"): "enchantify-event-14@academy",
    (5, "morning"): "enchantify-event-15@academy",
    (6, "morning"): "enchantify-event-16@academy",
}


def escape_ics(value: str) -> str:
    value = str(value or "")
    value = value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return value.replace("\n", "\\n")


def fold_line(line: str) -> list[str]:
    if len(line) <= 74:
        return [line]
    chunks = []
    while len(line) > 74:
        cut = 74
        chunks.append(line[:cut])
        line = " " + line[cut:]
    chunks.append(line)
    return chunks


def professor_label(name: str) -> str:
    return re.sub(r"^(?:Prof\.|Professor)\s+", "Prof. ", name or "").strip()


def event_summary(entry: tuple[str, ...], slot: str) -> str:
    if slot == "club":
        return entry[0]
    subject, professor, *_ = entry
    return f"{subject} ({professor_label(professor)})"


def event_location(entry: tuple[str, ...], slot: str) -> str:
    if slot == "club":
        return entry[1] if len(entry) > 1 else ""
    return entry[2] if len(entry) > 2 else ""


def event_description(entry: tuple[str, ...], slot: str) -> str:
    kind = "Academy Club" if slot == "club" else "Enchantify Academy Class"
    loc = event_location(entry, slot)
    return f"{kind}" + (f" — {loc}" if loc else "")


def build_calendar() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Enchantify Academy//NONSGML v1.0//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Enchantify Academy",
        f"X-WR-TIMEZONE:{TZID}",
    ]

    for weekday in range(7):
        day = schedule.CLASSES.get(weekday, {})
        for slot in ("morning", "afternoon", "club"):
            entry = day.get(slot)
            if not entry:
                continue
            start_time, end_time = SLOTS[slot]
            start_date = WEEK_STARTS[weekday]
            summary = event_summary(entry, slot)
            location = event_location(entry, slot)
            description = event_description(entry, slot)
            event_lines = [
                "BEGIN:VEVENT",
                f"UID:{UIDS[(weekday, slot)]}",
                f"DTSTAMP:{stamp}",
                f"DTSTART;TZID={TZID}:{start_date}T{start_time}",
                f"DTEND;TZID={TZID}:{start_date}T{end_time}",
                f"RRULE:FREQ=WEEKLY;BYDAY={BYDAY[weekday]}",
                f"SUMMARY:{escape_ics(summary)}",
            ]
            if location:
                event_lines.append(f"LOCATION:{escape_ics(location)}")
            event_lines.extend([
                f"DESCRIPTION:{escape_ics(description)}",
                "END:VEVENT",
            ])
            for line in event_lines:
                lines.extend(fold_line(line))

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    OUT.write_text(build_calendar())
    print(f"Generated {OUT}")


if __name__ == "__main__":
    main()
