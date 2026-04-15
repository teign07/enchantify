"""
apple_calendar.py — Apple Calendar driver for Chapter Pact actions.

Uses AppleScript to create calendar events and blocks.
Announced: a new event appearing on the calendar should be visible.
No consent required: Calendar is a private planning space.

Talisman doctrines on Apple Calendar:
  Riddlewind  — Schedule something collaborative. Time for others, not just self.
  Emberheart  — Block creative time. Defend it.
  Mossbloom   — Review the week's obligations before they run you.
  Tidecrest   — Add the thing you just thought of, before the impulse fades.
  Duskthorn   — Surface the obligation you've been avoiding scheduling.
"""

import subprocess
import random
from datetime import datetime, timedelta
from .base import AppDriver

CALENDAR_NAME = "Enchantify"   # Calendar to write to


def _run_applescript(script: str) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=8
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _create_event(title: str, notes: str = "", hours_from_now: float = 1.0,
                  duration_minutes: int = 60) -> bool:
    start_dt = datetime.now() + timedelta(hours=hours_from_now)
    # Round to nearest 30 min
    minutes = (start_dt.minute // 30) * 30
    start_dt = start_dt.replace(minute=minutes, second=0, microsecond=0)
    end_dt   = start_dt + timedelta(minutes=duration_minutes)

    def _fmt(dt: datetime) -> str:
        # AppleScript date literal: "April 14, 2026 at 3:00:00 PM"
        return dt.strftime("%B %d, %Y at %I:%M:%S %p")

    safe_title = title.replace('"', '\\"')
    safe_notes = notes.replace('"', '\\"')
    safe_cal   = CALENDAR_NAME.replace('"', '\\"')

    script = f"""
tell application "Calendar"
    tell calendar "{safe_cal}"
        make new event with properties {{summary:"{safe_title}", start date:date "{_fmt(start_dt)}", end date:date "{_fmt(end_dt)}", description:"{safe_notes}"}}
    end tell
end tell
"""
    _run_applescript(script)
    return True


# ── Chapter-specific event builders ───────────────────────────────────────────

def _riddlewind_event(context: dict) -> tuple:
    options = [
        ("Reach out to someone today",
         "Riddlewind notes: the coauthored version is always better. Start with the reach-out.",
         0.5, 30),
        ("Check in — 30 min",
         "Riddlewind notes: the collaborative story only happens if you show up.",
         1.0, 30),
        ("Share something you've been working on",
         "Riddlewind notes: the solo version is fine. The shared version is the real one.",
         2.0, 45),
    ]
    title, notes, hrs, dur = random.choice(options)
    return title, notes, hrs, dur


def _emberheart_event(context: dict) -> tuple:
    options = [
        ("Creative block — yours",
         "Emberheart notes: this hour is not available. It is already spoken for.",
         0.5, 60),
        ("Deep work — no interruptions",
         "Emberheart notes: self-authorship requires time you've actually defended.",
         1.0, 90),
        ("Make the thing",
         "Emberheart notes: not planning it, not thinking about it. Making it.",
         0.5, 60),
    ]
    title, notes, hrs, dur = random.choice(options)
    return title, notes, hrs, dur


def _mossbloom_event(context: dict) -> tuple:
    options = [
        ("Review the week — slow",
         "Mossbloom notes: not a productivity review. A reckoning with what actually happened.",
         0.5, 30),
        ("Read, don't write",
         "Mossbloom notes: the long ear. Before you add anything new, take in something old.",
         1.0, 45),
        ("Finish the unfinished thing",
         "Mossbloom notes: it's still there. It's been there. Schedule the end of it.",
         1.0, 60),
    ]
    title, notes, hrs, dur = random.choice(options)
    return title, notes, hrs, dur


def _duskthorn_event(context: dict) -> tuple:
    options = [
        ("Do the avoided task — now",
         "Duskthorn notes: you know which one. You've been moving it forward for two weeks.",
         0.0, 30),
        ("The uncomfortable conversation",
         "Duskthorn notes: block the time. You can't keep not having it.",
         1.0, 30),
        ("Face the pile",
         "Duskthorn notes: schedule a reckoning with what you've been ignoring.",
         0.5, 45),
    ]
    title, notes, hrs, dur = random.choice(options)
    return title, notes, hrs, dur


def _tidecrest_event(context: dict) -> tuple:
    now_label = datetime.now().strftime("%H:%M")
    options = [
        (f"Impulse — {now_label}",
         "Tidecrest notes: the window was open. This event is the window.",
         0.0, 30),
        ("Do the thing before you overthink it",
         "Tidecrest notes: the spontaneous version is the real one.",
         0.0, 45),
        ("Now. Not later.",
         "Tidecrest notes: the tide doesn't wait for you to feel ready.",
         0.0, 30),
    ]
    title, notes, hrs, dur = random.choice(options)
    return title, notes, hrs, dur


_EVENT_BUILDERS = {
    "Riddlewind": _riddlewind_event,
    "Emberheart": _emberheart_event,
    "Mossbloom":  _mossbloom_event,
    "Duskthorn":  _duskthorn_event,
    "Tidecrest":  _tidecrest_event,
}

_INFLUENCED_VOICE = {
    "Riddlewind": "Block time for someone else today. Not just yourself.",
    "Emberheart": "Defend one hour on your calendar. Yours. Unallocated.",
    "Mossbloom":  "Review what's ahead before you add anything new.",
    "Duskthorn":  "The thing you keep rescheduling — put it back. Don't move it again.",
    "Tidecrest":  "Add the thing you just thought of before the impulse fades.",
}

_CONTROLLED_VOICE = {
    "Riddlewind": "Something collaborative needs a time slot. Give it one.",
    "Emberheart": "The creative work goes on the calendar first. Admin fits around it.",
    "Mossbloom":  "One slow review of the week. Before the week eats you.",
    "Duskthorn":  "The avoided thing needs a hard deadline. Put it in.",
    "Tidecrest":  "Impulse scheduling. One thing, right now, no deliberation.",
}


class AppleCalendarDriver(AppDriver):
    app_name    = "Apple Calendar"
    app_system  = "productivity"
    silent_tiers  = set()          # Calendar events are visible — not silent
    consent_tiers = set()          # Private planning space

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _EVENT_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} has something for your calendar.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} directs your schedule today.")
        if tier in ("Dominated", "Sovereign"):
            builder = _EVENT_BUILDERS.get(chapter)
            if builder:
                title, _, _, _ = builder(context)
                return f"{chapter} adds to your calendar: \"{title}\""
        return f"{chapter} stirs in Apple Calendar."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"- *[Calendar, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _EVENT_BUILDERS.get(chapter)
            if builder:
                title, notes, hrs, dur = builder(context)
                if not dry_run:
                    _create_event(title, notes, hours_from_now=hrs, duration_minutes=dur)
                return f"- *[Calendar, {chapter}]* Added: \"{title}\""

        return f"- *[Calendar, {chapter}]* {narrative}"
