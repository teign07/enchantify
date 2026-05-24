#!/usr/bin/env python3
"""Bellkeeper's proactive day-reading loop.

The Bellkeeper is the first "proactive office" support character: a full
character with a real job, a private chart, memory, and a small useful script.
They read the shape of the day and prepare one humane Today Page card.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cron_steward  # type: ignore
import journal_artifact  # type: ignore


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
CONFIG = BASE / "config" / "proactive-offices.json"
HEARTBEAT = BASE / "HEARTBEAT.md"
ACADEMY_ICS = BASE / "hooks" / "enchantify_schedule.ics"
MEMORY_DIR = BASE / "memory" / "support-faculty" / "bellkeeper"
LOG_DIR = BASE / "logs" / "support-faculty"

DEFAULT_TARGET = "8729557865"
DEFAULT_CHANNEL = "telegram"
DEFAULT_ACCOUNT = "enchantify"

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "offices": {
        "bellkeeper": {
            "character": "Bellkeeper Elian Quill",
            "enabled": True,
            "default_mode": "companion",
            "max_prompts_per_day": 2,
            "language": "simple-surprising",
            "can_read_calendar": True,
            "can_write_calendar": False,
            "can_create_reminders": False,
            "telegram_default": False,
            "morning_card_time": "07:15",
            "upcoming_scan_minutes": 1440,
            "upcoming_min_notice_minutes": 20,
            "upcoming_cooldown_hours": 20,
            "evening_scrap_time": "20:45",
            "week_ahead_time": "18:30",
            "upcoming_keywords": [
                "appointment",
                "doctor",
                "therapy",
                "dentist",
                "medical",
                "clinic",
                "visit",
                "meeting",
                "interview",
                "call",
            ],
        }
    },
}

CHART_TEMPLATE = """# Bellkeeper Chart — BJ

This is the private working context for Bellkeeper Elian Quill, Registrar of Hours. The Bellkeeper helps the Book read the shape of time so it can prepare the right page without nagging BJ.

## Bellkeeper Rules

- Read the day, do not command the day.
- Use simple, surprising language. Avoid turning every ordinary thing into jargon.
- Rest is a valid answer. Empty time is not a moral failure.
- No streaks, guilt, scolding, or "you should."
- Offer one useful invitation at a time.
- Calendar events, work, appointments, errands, gaps, and evening transitions may become story context only when that helps.
- The Bellkeeper may read the Enchantify calendar, schedule context, HEARTBEAT, and support-character summaries.
- The Bellkeeper may suggest calendar events or reminders, but must not create or change them without explicit permission.
- If the day looks crowded, reduce pressure.
- If the day looks empty, offer a small door, not a demand.

## Proactive Modes

| Mode | Use |
|---|---|
| quiet | Mostly watch and remember; no proactive nudges. |
| whisper | One gentle card or note per day. |
| companion | Morning shape, one possible transition support, evening memory prompt. |
| field | Look for Compass/errand/adventure openings. |
| care | Reduce demands; route toward Inkrest, Vellum, Gimble, or rest. |

## Default Output

1. Today's Shape: what the day looks like in plain language.
2. One Thing To Watch: the likely friction point.
3. Tiny Invitation: one optional action scaled to capacity.
4. Support On Call: which support character fits the day.
5. Tonight's Scrap: one thing the Book wants to remember.

## Known Anchors

- BJ works Monday through Friday at athenahealth in Financial Process Services, operating an IBML Fusion scanner.
- BJ commutes and works primarily from iPhone/iPad.
- Mental health support matters; gentle check-ins beat pressure.
- The Book of You benefits from one sensory scrap before the day closes.
"""


@dataclass
class Event:
    start: datetime
    end: datetime | None
    summary: str
    location: str = ""
    source: str = "ics"

    @property
    def is_all_day(self) -> bool:
        return self.start.time() == time.min and (self.end is None or self.end.time() == time.min)


def now() -> datetime:
    return datetime.now()


def player_chart(player: str) -> Path:
    return PLAYERS / f"{player}-bellkeeper-chart.md"


def player_log(player: str) -> Path:
    return PLAYERS / f"{player}-bellkeeper-log.jsonl"


def ensure_dirs() -> None:
    PLAYERS.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def ensure_config() -> Path:
    ensure_dirs()
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    return CONFIG


def ensure_chart(player: str) -> Path:
    ensure_dirs()
    path = player_chart(player)
    if not path.exists():
        path.write_text(CHART_TEMPLATE, encoding="utf-8")
    return path


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def clean(text: Any, limit: int = 280) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = re.sub(r"^[#>*_\-\s]+", "", value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def read_text(path: Path, limit: int = 6000) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception:
        return ""


def unfold_ics(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def unescape_ics(value: str) -> str:
    return (
        value.replace("\\n", " ")
        .replace("\\N", " ")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def parse_ics_datetime(value: str) -> datetime | None:
    value = value.strip().rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed
        except ValueError:
            continue
    return None


def expand_weekly_event(start: datetime, end: datetime | None, target: date, rrule: str) -> tuple[datetime, datetime | None] | None:
    if "FREQ=WEEKLY" not in rrule:
        return None
    byday = re.search(r"BYDAY=([^;]+)", rrule)
    if byday:
        weekdays = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
        allowed = {weekdays[d] for d in byday.group(1).split(",") if d in weekdays}
        if target.weekday() not in allowed:
            return None
    if target < start.date():
        return None
    new_start = datetime.combine(target, start.time())
    new_end = None
    if end is not None:
        duration = end - start
        new_end = new_start + duration
    return new_start, new_end


def parse_ics(path: Path, target: date) -> list[Event]:
    text = read_text(path, limit=200000)
    if not text:
        return []
    events: list[Event] = []
    current: dict[str, str] | None = None
    for line in unfold_ics(text):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT" and current is not None:
            start = parse_ics_datetime(current.get("DTSTART", ""))
            if start:
                end = parse_ics_datetime(current.get("DTEND", ""))
                rrule = current.get("RRULE", "")
                if start.date() == target:
                    actual = (start, end)
                else:
                    actual = expand_weekly_event(start, end, target, rrule)
                if actual:
                    events.append(
                        Event(
                            start=actual[0],
                            end=actual[1],
                            summary=clean(unescape_ics(current.get("SUMMARY", "Untitled event")), 120),
                            location=clean(unescape_ics(current.get("LOCATION", "")), 120),
                        )
                    )
            current = None
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.split(";", 1)[0]
        current[key] = value
    return sorted(events, key=lambda ev: ev.start)


def events_for_range(start_day: date, days: int) -> list[Event]:
    events: list[Event] = []
    for offset in range(days):
        target = start_day + timedelta(days=offset)
        events.extend(parse_ics(ACADEMY_ICS, target))
        if offset <= 1:
            events.extend(apple_calendar_events(target))
    return sorted(events, key=lambda ev: ev.start)


def parse_time_fragment(text: str, target: date) -> datetime | None:
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*([AP]M)\b", text, re.IGNORECASE)
    if not match:
        match = re.search(r"\b(\d{1,2})(?::(\d{2}))\b", text)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2))
        return datetime.combine(target, time(hour=hour, minute=minute))
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3).lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return datetime.combine(target, time(hour=hour, minute=minute))


def apple_calendar_events(target: date) -> list[Event]:
    """Read personal Apple Calendar day events through icalBuddy when available.

    The output format varies by icalBuddy flags/version, so this parser stays
    conservative: title from bullet/line text, time from the first visible time.
    Cron runs with the user's TCC permissions even if sandboxed test runs cannot.
    """
    if target == now().date():
        command = ["eventsToday"]
    elif target == (now().date() + timedelta(days=1)):
        command = ["eventsTomorrow"]
    else:
        return []
    try:
        proc = subprocess.run(
            ["/opt/homebrew/bin/icalBuddy", "-n", "-po", "title,datetime,location", "-eep", "notes,attendees", *command],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out or "error" in out.lower():
        return []

    events: list[Event] = []
    chunks = re.split(r"\n(?=\s*[•*-]\s+)", out)
    for chunk in chunks:
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        title_line = re.sub(r"^\s*[•*-]\s*", "", lines[0]).strip()
        title = clean(re.sub(r"\s+\b\d{1,2}(?::\d{2})?\s*[AP]M\b.*$", "", title_line, flags=re.IGNORECASE), 140)
        dt = None
        for line in lines:
            dt = parse_time_fragment(line, target)
            if dt:
                break
        if dt and title:
            location = ""
            for line in lines[1:]:
                if re.search(r"\blocation\b", line, re.IGNORECASE):
                    location = clean(re.sub(r"^location\s*:\s*", "", line, flags=re.IGNORECASE), 140)
                    break
            events.append(Event(start=dt, end=None, summary=title, location=location, source="apple-calendar"))
    return sorted(events, key=lambda ev: ev.start)


def calendar_today(target: date) -> tuple[list[Event], str]:
    events = parse_ics(ACADEMY_ICS, target)
    source = "Enchantify Academy calendar"
    apple = apple_calendar_events(target)
    if apple:
        events.extend(apple)
        source += " + Apple Calendar"
    return sorted(events, key=lambda ev: ev.start), source


def load_config() -> dict[str, Any]:
    ensure_config()
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else DEFAULT_CONFIG
    except Exception:
        return DEFAULT_CONFIG


def bellkeeper_settings() -> dict[str, Any]:
    offices = (load_config().get("offices") or {})
    settings = offices.get("bellkeeper") or {}
    merged = dict(DEFAULT_CONFIG["offices"]["bellkeeper"])
    merged.update(settings)
    return merged


def heartbeat_notes() -> dict[str, str]:
    hb = read_text(HEARTBEAT, limit=12000)
    notes = {
        "mood": "",
        "fuel": "",
        "steps": "",
        "calendar": "",
    }
    for label, key in (("Mood", "mood"), ("Fuel", "fuel"), ("Steps", "steps"), ("Calendar", "calendar")):
        match = re.search(rf"{label}[^\n:]*:\s*(.+)", hb, re.IGNORECASE)
        if match:
            notes[key] = clean(match.group(1), 180)
    if not notes["fuel"]:
        fuel_match = re.search(r"Fuel Gauge.*?(?:\n|\r\n)(.+)", hb, re.IGNORECASE | re.DOTALL)
        if fuel_match:
            notes["fuel"] = clean(fuel_match.group(1), 180)
    return notes


def latest_log_line(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        if not lines:
            return ""
        row = json.loads(lines[-1])
        if row.get("kind") == "mood-word":
            return clean(row.get("word"), 180)
        if row.get("kind") == "prompt":
            return "latest Inkrest entry is a prompt awaiting reply"
        if row.get("kind") in {"daily_sync", "money_weather"}:
            insights = row.get("insights") or []
            if insights:
                return clean(insights[0].get("title") or insights[0].get("detail"), 180)
            summary = row.get("summary") or {}
            uncategorized = summary.get("uncategorized_count")
            if uncategorized is not None:
                return clean(f"{uncategorized} uncategorized transactions visible", 180)
        return clean(row.get("insight") or row.get("mood") or row.get("weather") or row.get("message") or row.get("summary") or "", 180)
    except Exception:
        return ""


def event_lines(events: list[Event]) -> list[str]:
    if not events:
        return ["- No dated events are visible to Bellkeeper right now."]
    lines = []
    seen: set[str] = set()
    for ev in events[:7]:
        clock = "all day" if ev.is_all_day else ev.start.strftime("%-I:%M %p")
        loc = f" — {ev.location}" if ev.location else ""
        line = f"- {clock}: {ev.summary}{loc}"
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return lines


def classify_shape(events: list[Event], target: date) -> str:
    weekday = target.weekday()
    has_workday = weekday < 5
    timed = [ev for ev in events if not ev.is_all_day]
    if len(timed) >= 5:
        return "A crowded day: several bells, narrow gaps, and a real need to lower optional demands."
    if has_workday and timed:
        return "A workday with scheduled edges. The useful magic is arrival, transition, and one small remembered detail."
    if has_workday:
        return "A workday with few visible appointments. Repetition may try to blur the edges, so one concrete detail matters."
    if timed:
        return "An unscripted day with a few marked moments. There may be room for a small door if energy allows."
    return "An open page. That is not pressure; it is simply room."


def support_on_call(events: list[Event], hb: dict[str, str]) -> str:
    return support_handoff(events, hb)["label"]


def support_handoff(events: list[Event], hb: dict[str, str]) -> dict[str, str]:
    text = " ".join([ev.summary for ev in events] + list(hb.values())).lower()
    if any(word in text for word in ("bill", "budget", "bank", "payment", "payday", "actual", "simplefin")):
        return {
            "character": "Gimble of the Errata Registry",
            "label": "Gimble, if budget pressure starts tapping at the glass.",
            "reason": "money, bill, budget, or payment language is present",
            "bring": "one number, one due date, or one transaction/category question",
            "after": "whether the budget pressure was harmless, urgent, or still unclear",
        }
    if any(word in text for word in ("anxious", "overwhelm", "sad", "depressed", "ptsd", "therapy", "stress")):
        return {
            "character": "Dr. Selene Inkrest",
            "label": "Dr. Inkrest, for one grounded sentence before the day gets loud.",
            "reason": "therapy, mood, stress, or emotional-load language is present",
            "bring": "one feeling word or one sentence about the story the day is telling",
            "after": "one sentence about what helped or what felt heavy",
        }
    if any(word in text for word in ("fuel", "sleep", "steps", "meal", "protein", "tired", "health", "doctor")):
        return {
            "character": "Dr. Elowen Vellum",
            "label": "Dr. Vellum, for body-first support that does not turn into a lecture.",
            "reason": "health, doctor, sleep, fuel, or body-signal language is present",
            "bring": "medication names, one question, and one recent body signal if useful",
            "after": "one thing the clinician said, one next step, or one question still open",
        }
    if any(word in text for word in ("publish", "patreon", "youtube", "post", "content", "marketing")):
        return {
            "character": "Penny Blackletter",
            "label": "Penny, if a real moment wants to become public-safe proof.",
            "reason": "publishing, content, or audience language is present",
            "bring": "one useful fragment, one audience, and one privacy boundary",
            "after": "whether the moment belongs public, Patreon, private, or nowhere",
        }
    return {
        "character": "Bellkeeper Elian Quill",
        "label": "Bellkeeper stays on the desk; the rest of the faculty can be called, not summoned.",
        "reason": "no specialized support domain is dominant",
        "bring": "arrival, one tiny intention, and permission to rest",
        "after": "one scrap: color, sound, texture, sentence, or skip",
    }


def tiny_invitation(events: list[Event], hb: dict[str, str], target: date) -> str:
    text = " ".join(list(hb.values()) + [ev.summary for ev in events]).lower()
    if any(word in text for word in ("tired", "low", "overwhelm", "anxious")):
        return "Choose one threshold today and cross it slowly: car door, work door, kitchen door. Let that count."
    if target.weekday() < 5:
        return "Bring back one detail from work that would normally vanish: a sound, a label, a kindness, or an absurdity."
    if events:
        return "After one marked event, give the Book one scrap: color, sound, texture, sentence, or skip."
    return "Leave one hour unoptimized if you can. A page with white space is still a page."


def friction_point(events: list[Event], hb: dict[str, str], target: date) -> str:
    text = " ".join(list(hb.values()) + [ev.summary for ev in events]).lower()
    if len([ev for ev in events if not ev.is_all_day]) >= 4:
        return "Too many transitions can make the day feel like one long hallway."
    if "tired" in text or "low" in text:
        return "Energy may be the limiting reagent; the plan should be smaller than ambition."
    if target.weekday() < 5:
        return "Autopilot after work. That is where days often disappear."
    if not events:
        return "An empty calendar can quietly become fog if it is asked to explain itself."
    return "The Book may remember the schedule better than the texture unless you give it one scrap."


def build_card(player: str, target: date) -> tuple[str, dict[str, Any]]:
    ensure_config()
    ensure_chart(player)
    events, source = calendar_today(target)
    hb = heartbeat_notes()
    inkrest = latest_log_line(PLAYERS / f"{player}-inkrest-log.jsonl")
    vellum = latest_log_line(PLAYERS / f"{player}-vellum-log.jsonl")
    ledger = latest_log_line(PLAYERS / f"{player}-ledger-log.jsonl")
    shape = classify_shape(events, target)
    support = support_on_call(events, hb)
    invitation = tiny_invitation(events, hb, target)
    watch = friction_point(events, hb, target)
    title = f"Bellkeeper Today's Page — {target.isoformat()}"
    lines = [
        f"# {title}",
        "",
        "_Bellkeeper Elian Quill lays the day flat enough to read, then refuses to make it heavier._",
        "",
        "## Today's Shape",
        shape,
        "",
        "## Visible Bells",
        *event_lines(events),
        "",
        "## One Thing To Watch",
        watch,
        "",
        "## Tiny Invitation",
        invitation,
        "",
        "## Support On Call",
        support,
        "",
        "## Tonight's Scrap",
        "Before the day closes, the Book would like one thing that actually happened: a color, a sound, a sentence, a texture, or the honest note that there was no extra ink.",
        "",
        "## Quiet Signals",
        f"- Calendar source: {source}",
        f"- Mood trace: {hb.get('mood') or inkrest or 'not visible'}",
        f"- Fuel/body trace: {hb.get('fuel') or vellum or 'not visible'}",
        f"- Ledger trace: {ledger or 'not visible'}",
        "",
        "— Bellkeeper Elian Quill",
        "",
    ]
    meta = {
        "player": player,
        "date": target.isoformat(),
        "title": title,
        "event_count": len(events),
        "events": [ev.__dict__ for ev in events[:10]],
        "shape": shape,
        "watch": watch,
        "invitation": invitation,
        "support": support,
        "heartbeat": hb,
        "source": source,
    }
    return "\n".join(lines), meta


def render_bellkeeper_pdf(message: str, stem: str, *, title: str, subtitle: str, dry_run: bool = False) -> dict[str, str]:
    return journal_artifact.render(
        message if message.startswith("#") else f"# {title}\n\n{message}",
        MEMORY_DIR / "journal",
        stem,
        title=title,
        subtitle=subtitle,
        footer="Filed by Bellkeeper Elian Quill, Registrar of Hours",
        accent="#2f5d50",
        dry_run=dry_run,
    )


def send_telegram(message: str, media: Path | None = None, *, dry_run: bool = False) -> bool:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return True
    args = [
            "openclaw",
            "message",
            "send",
            "--target",
            DEFAULT_TARGET,
            "--channel",
            DEFAULT_CHANNEL,
            "--account",
            DEFAULT_ACCOUNT,
            "--message",
            message,
        ]
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(
        args,
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if proc.returncode != 0:
        (LOG_DIR / "bellkeeper-send-errors.log").open("a", encoding="utf-8").write(
            f"\n[{now().isoformat(timespec='seconds')}]\n{proc.stderr or proc.stdout}\n"
        )
        return False
    return True


def event_is_personal_signal(ev: Event, keywords: list[str]) -> bool:
    if ev.source == "ics":
        return False
    text = f"{ev.summary} {ev.location}".lower()
    return any(keyword.lower() in text for keyword in keywords)


def build_upcoming_note(player: str, ev: Event, minutes_until: int) -> tuple[str, dict[str, Any]]:
    hb = heartbeat_notes()
    when = ev.start.strftime("%-I:%M %p")
    location = f" at {ev.location}" if ev.location else ""
    handoff = support_handoff([ev], hb)
    practical = f"Bring {handoff['bring']}. No need to make it perfect."
    title = f"Bellkeeper Before the Bell — {ev.summary}"
    message = (
        f"{title}\n\n"
        f"BJ,\n\n"
        f"{ev.summary} is coming up at {when}{location}. Bellkeeper Elian Quill has placed one card on the desk, not a stack.\n\n"
        f"One preparation: {practical}\n\n"
        f"One breath before leaving: notice the nearest doorway and cross it on purpose.\n\n"
        f"Support handoff: {handoff['character']} — {handoff['reason']}.\n\n"
        f"Afterward, the Book only wants one scrap: {handoff['after']}.\n\n"
        f"— Bellkeeper Elian Quill"
    )
    meta = {
        "kind": "upcoming_event",
        "player": player,
        "event": ev.__dict__,
        "minutes_until": minutes_until,
        "title": title,
        "message": message,
        "handoff": handoff,
    }
    return message, meta


def build_evening_note(player: str, target: date) -> tuple[str, dict[str, Any]]:
    events, source = calendar_today(target)
    hb = heartbeat_notes()
    handoff = support_handoff(events, hb)
    message = (
        "Bellkeeper Evening Scrap\n\n"
        "BJ,\n\n"
        "The day is near its hinge. Before the Book of You tries to bind it from weather and footprints alone, Bellkeeper Elian Quill asks for one scrap.\n\n"
        "Reply with any one of these:\n"
        "- a color\n"
        "- a sound\n"
        "- a texture\n"
        "- one sentence someone said\n"
        "- one thing that happened\n"
        "- skip\n\n"
        f"Support handoff, if useful: {handoff['label']}\n\n"
        "No essay. No performance. One scrap is enough.\n\n"
        "— Bellkeeper Elian Quill"
    )
    meta = {
        "kind": "evening_scrap",
        "player": player,
        "date": target.isoformat(),
        "message": message,
        "event_count": len(events),
        "source": source,
        "handoff": handoff,
    }
    return message, meta


def build_week_note(player: str, start_day: date) -> tuple[str, dict[str, Any]]:
    events = events_for_range(start_day, 7)
    hb = heartbeat_notes()
    personal = [ev for ev in events if ev.source != "ics"]
    appointment_like = [ev for ev in personal if event_is_personal_signal(ev, list(bellkeeper_settings().get("upcoming_keywords") or []))]
    academy = [ev for ev in events if ev.source == "ics"]
    busiest: dict[str, int] = {}
    for ev in events:
        key = ev.start.strftime("%A")
        busiest[key] = busiest.get(key, 0) + 1
    busy_line = "No crowded day is visible." if not busiest else ", ".join(f"{day}×{count}" for day, count in sorted(busiest.items(), key=lambda item: item[1], reverse=True)[:3])
    handoff = support_handoff(appointment_like or personal or events, hb)
    appointment_lines = []
    for ev in appointment_like[:5]:
        appointment_lines.append(f"- {ev.start.strftime('%A %-I:%M %p')}: {ev.summary}")
    if not appointment_lines:
        appointment_lines.append("- No appointment-like personal events visible to Bellkeeper.")
    compass_window = "Look for one low-friction Compass window after the most crowded day, not before it."
    if not personal and academy:
        compass_window = "The Academy schedule is visible; personal calendar openings are not, so keep the Compass window small and optional."
    message = (
        "Bellkeeper Week-Ahead Reading\n\n"
        "BJ,\n\n"
        "The week has been unfolded just far enough to keep it from ambushing you.\n\n"
        f"Crowding: {busy_line}\n\n"
        "Marked personal bells:\n"
        + "\n".join(appointment_lines)
        + "\n\n"
        f"Support handoff: {handoff['character']} — {handoff['reason']}.\n\n"
        f"Compass opening: {compass_window}\n\n"
        "One preparation for the week: choose one appointment or obligation that deserves a question written down before it arrives.\n\n"
        "— Bellkeeper Elian Quill"
    )
    meta = {
        "kind": "week_ahead",
        "player": player,
        "week_start": start_day.isoformat(),
        "message": message,
        "event_count": len(events),
        "personal_count": len(personal),
        "appointment_count": len(appointment_like),
        "handoff": handoff,
    }
    return message, meta


def cmd_init(args: argparse.Namespace) -> int:
    ensure_config()
    chart = ensure_chart(args.player)
    print(f"BELLKEEPER_READY: {chart}")
    print(f"PROACTIVE_OFFICES: {CONFIG}")
    return 0


def cmd_today(args: argparse.Namespace) -> int:
    target = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else now().date()
    card, meta = build_card(args.player, target)
    path = MEMORY_DIR / f"{target.isoformat()}.md"
    if args.dry_run:
        print(card)
    else:
        path.write_text(card, encoding="utf-8")
        meta["artifact"] = str(path)
        append_jsonl(player_log(args.player), meta)
        print(f"BELLKEEPER_CARD: {path}")
    if args.send:
        intro = "\n".join(card.splitlines()[:22])
        artifact = render_bellkeeper_pdf(card, f"{target.isoformat()}-today-page", title="Bellkeeper Today's Page", subtitle=target.isoformat(), dry_run=args.dry_run)
        media = Path(artifact["pdf"]) if artifact.get("pdf") else None
        ok = send_telegram(intro, media, dry_run=args.dry_run)
        print(f"BELLKEEPER_TELEGRAM: {'sent' if ok else 'failed'}")
    return 0


def cmd_upcoming(args: argparse.Namespace) -> int:
    ensure_config()
    ensure_chart(args.player)
    settings = bellkeeper_settings()
    scan_minutes = int(args.minutes or settings.get("upcoming_scan_minutes", 180))
    min_notice = int(settings.get("upcoming_min_notice_minutes", 20))
    keywords = list(settings.get("upcoming_keywords") or [])
    horizon = now() + timedelta(minutes=scan_minutes)
    candidates: list[Event] = []
    for offset in (0, 1):
        target = (now() + timedelta(days=offset)).date()
        candidates.extend(apple_calendar_events(target))
    upcoming = [
        ev for ev in sorted(candidates, key=lambda item: item.start)
        if now() + timedelta(minutes=min_notice) <= ev.start <= horizon and event_is_personal_signal(ev, keywords)
    ]
    if not upcoming:
        print("BELLKEEPER_UPCOMING: none")
        cron_steward.mark_skipped("bellkeeper-upcoming", "no eligible upcoming events", scope=now().date().isoformat())
        return 0

    ev = upcoming[0]
    minutes_until = int((ev.start - now()).total_seconds() // 60)
    message, meta = build_upcoming_note(args.player, ev, minutes_until)
    scope = f"{args.player}:{ev.start.date().isoformat()}:{clean(ev.summary, 80).lower()}"
    skip, digest, reason = cron_steward.should_skip_duplicate(
        "bellkeeper-upcoming",
        {"summary": ev.summary, "start": ev.start.isoformat(), "message": message},
        cooldown_hours=float(settings.get("upcoming_cooldown_hours", 20)),
        force=args.force,
        scope=scope,
    )
    if skip:
        print(f"BELLKEEPER_UPCOMING: skipped ({reason})")
        cron_steward.mark_skipped("bellkeeper-upcoming", reason, scope=scope, fingerprint=digest)
        return 0

    if args.dry_run:
        print(message)
    else:
        append_jsonl(player_log(args.player), meta)
        print(f"BELLKEEPER_UPCOMING: {ev.summary} in {minutes_until}m")
    if args.send:
        artifact = render_bellkeeper_pdf(message, f"{now().strftime('%Y%m%d-%H%M%S')}-upcoming", title="Bellkeeper Upcoming Bell", subtitle=ev.summary, dry_run=args.dry_run)
        media = Path(artifact["pdf"]) if artifact.get("pdf") else None
        ok = send_telegram(message, media, dry_run=args.dry_run)
        print(f"BELLKEEPER_TELEGRAM: {'sent' if ok else 'failed'}")
        if ok and not args.dry_run:
            cron_steward.mark_delivered("bellkeeper-upcoming", message, scope=scope, event=ev.summary, start=ev.start.isoformat())
    return 0


def cmd_evening(args: argparse.Namespace) -> int:
    ensure_config()
    ensure_chart(args.player)
    target = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else now().date()
    message, meta = build_evening_note(args.player, target)
    scope = f"{args.player}:{target.isoformat()}"
    skip, digest, reason = cron_steward.should_skip_duplicate(
        "bellkeeper-evening",
        message,
        cooldown_hours=20,
        force=args.force,
        scope=scope,
    )
    if skip:
        print(f"BELLKEEPER_EVENING: skipped ({reason})")
        cron_steward.mark_skipped("bellkeeper-evening", reason, scope=scope, fingerprint=digest)
        return 0
    if args.dry_run:
        print(message)
    else:
        append_jsonl(player_log(args.player), meta)
        print(f"BELLKEEPER_EVENING: {target.isoformat()}")
    if args.send:
        artifact = render_bellkeeper_pdf(message, f"{target.isoformat()}-evening-scrap", title="Bellkeeper Evening Scrap", subtitle=target.isoformat(), dry_run=args.dry_run)
        media = Path(artifact["pdf"]) if artifact.get("pdf") else None
        ok = send_telegram(message, media, dry_run=args.dry_run)
        print(f"BELLKEEPER_TELEGRAM: {'sent' if ok else 'failed'}")
        if ok and not args.dry_run:
            cron_steward.mark_delivered("bellkeeper-evening", message, scope=scope, date=target.isoformat())
    return 0


def cmd_week(args: argparse.Namespace) -> int:
    ensure_config()
    ensure_chart(args.player)
    target = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else now().date()
    message, meta = build_week_note(args.player, target)
    scope = f"{args.player}:{target.isoformat()}"
    skip, digest, reason = cron_steward.should_skip_duplicate(
        "bellkeeper-week",
        message,
        cooldown_hours=120,
        force=args.force,
        scope=scope,
    )
    if skip:
        print(f"BELLKEEPER_WEEK: skipped ({reason})")
        cron_steward.mark_skipped("bellkeeper-week", reason, scope=scope, fingerprint=digest)
        return 0
    if args.dry_run:
        print(message)
    else:
        append_jsonl(player_log(args.player), meta)
        print(f"BELLKEEPER_WEEK: {target.isoformat()}")
    if args.send:
        artifact = render_bellkeeper_pdf(message, f"{target.isoformat()}-week-ahead", title="Bellkeeper Week Ahead", subtitle=target.isoformat(), dry_run=args.dry_run)
        media = Path(artifact["pdf"]) if artifact.get("pdf") else None
        ok = send_telegram(message, media, dry_run=args.dry_run)
        print(f"BELLKEEPER_TELEGRAM: {'sent' if ok else 'failed'}")
        if ok and not args.dry_run:
            cron_steward.mark_delivered("bellkeeper-week", message, scope=scope, date=target.isoformat())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ensure_config()
    ensure_chart(args.player)
    cards = sorted(MEMORY_DIR.glob("*.md"))
    print(f"BELLKEEPER_CONFIG: {CONFIG}")
    print(f"BELLKEEPER_CHART: {player_chart(args.player)}")
    print(f"BELLKEEPER_LOG: {player_log(args.player)}")
    if cards:
        latest = cards[-1]
        print(f"LATEST_CARD: {latest}")
        print(read_text(latest, limit=2200))
    else:
        print("LATEST_CARD: none")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bellkeeper proactive day reader")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create Bellkeeper chart/config")
    p_init.add_argument("player", nargs="?", default="bj")
    p_init.set_defaults(func=cmd_init)

    p_today = sub.add_parser("today", help="Write today's page card")
    p_today.add_argument("player", nargs="?", default="bj")
    p_today.add_argument("--date", help="YYYY-MM-DD")
    p_today.add_argument("--send", action="store_true", help="Send a short Telegram note")
    p_today.add_argument("--dry-run", action="store_true")
    p_today.set_defaults(func=cmd_today)

    p_upcoming = sub.add_parser("upcoming", help="Scan for appointment-like events coming up soon")
    p_upcoming.add_argument("player", nargs="?", default="bj")
    p_upcoming.add_argument("--minutes", type=int, help="Lookahead window in minutes")
    p_upcoming.add_argument("--send", action="store_true", help="Send a Telegram preparation note")
    p_upcoming.add_argument("--dry-run", action="store_true")
    p_upcoming.add_argument("--force", action="store_true")
    p_upcoming.set_defaults(func=cmd_upcoming)

    p_evening = sub.add_parser("evening", help="Ask for one evening scrap before Book of You")
    p_evening.add_argument("player", nargs="?", default="bj")
    p_evening.add_argument("--date", help="YYYY-MM-DD")
    p_evening.add_argument("--send", action="store_true", help="Send a Telegram evening scrap prompt")
    p_evening.add_argument("--dry-run", action="store_true")
    p_evening.add_argument("--force", action="store_true")
    p_evening.set_defaults(func=cmd_evening)

    p_week = sub.add_parser("week", help="Prepare a week-ahead reading")
    p_week.add_argument("player", nargs="?", default="bj")
    p_week.add_argument("--date", help="YYYY-MM-DD")
    p_week.add_argument("--send", action="store_true", help="Send a Telegram week-ahead reading")
    p_week.add_argument("--dry-run", action="store_true")
    p_week.add_argument("--force", action="store_true")
    p_week.set_defaults(func=cmd_week)

    p_status = sub.add_parser("status", help="Show Bellkeeper status")
    p_status.add_argument("player", nargs="?", default="bj")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
