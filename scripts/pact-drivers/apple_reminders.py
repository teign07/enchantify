"""
apple_reminders.py — Apple Reminders driver for Chapter Pact actions.

Uses remindctl (already wired in update-player.py) to create reminders.
Announced (not silent): a reminder appearing is meant to be seen.
No consent required: Reminders is a private task list.

Talisman doctrines on Apple Reminders:
  Riddlewind — Coordination. Something for someone else, or something shared.
  Mossbloom  — Graceful acceptance. The task you've been avoiding, reframed.
  Emberheart — Ownership. Your time is yours. This task is a choice, not an obligation.
  Duskthorn  — Pressure. The avoided task, surfaced deliberately. Conflict with avoidance.
  Tidecrest  — Immediacy. A reminder for something right now, not later.
"""

import subprocess
import random
from datetime import datetime, timedelta
from .base import AppDriver

REMINDER_LIST = "Academy"   # The Reminders list we write to (from update-player.py)


def _create_reminder(title: str, notes: str = "", list_name: str = REMINDER_LIST) -> bool:
    try:
        args = ["remindctl", "add", "--title", title, "--list", list_name]
        if notes:
            args += ["--notes", notes]
        subprocess.run(args, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


# ── Chapter-specific reminder content ────────────────────────────────────────

def _riddlewind_reminder(context: dict) -> tuple:
    options = [
        ("Check in with someone today",
         "Riddlewind notes: someone in your orbit is working on something. Ask about it."),
        ("Share something you made with one person",
         "Riddlewind notes: the coauthored version is better. Start by sharing the solo one."),
        ("Add one thing to a shared list",
         "Riddlewind notes: coordination is love at scale."),
    ]
    return random.choice(options)


def _mossbloom_reminder(context: dict) -> tuple:
    options = [
        ("Finish one old thing before starting anything new",
         "Mossbloom notes: the old thing is not gone. It is waiting."),
        ("Accept one obligation without resisting it",
         "Mossbloom notes: resistance makes tasks heavier. Acceptance makes them possible."),
        ("Read before you write today",
         "Mossbloom notes: the long ear. Receive first."),
    ]
    return random.choice(options)


def _emberheart_reminder(context: dict) -> tuple:
    options = [
        ("Protect one hour of uninterrupted time today",
         "Emberheart notes: your time is not a resource to be allocated. It is yours."),
        ("Do the creative thing before the administrative thing",
         "Emberheart notes: the order matters. Self-authorship first."),
        ("Say no to one thing that isn't yours",
         "Emberheart notes: the boundary is not selfish. It is necessary."),
    ]
    return random.choice(options)


def _duskthorn_reminder(context: dict) -> tuple:
    options = [
        ("Do the avoided task. Right now.",
         "Duskthorn notes: you know which one. The avoidance is the story."),
        ("Finish the uncomfortable conversation",
         "Duskthorn notes: the longer you wait, the heavier it gets. Conflict is productive."),
        ("Look at what you've been ignoring in your task list",
         "Duskthorn notes: the pile has weight. Weight creates pressure. Pressure creates movement."),
    ]
    return random.choice(options)


def _tidecrest_reminder(context: dict) -> tuple:
    now = datetime.now().strftime("%H:%M")
    options = [
        (f"Do the thing you thought of at {now}",
         "Tidecrest notes: the window was open. This reminder is the window."),
        ("Post the thing before you talk yourself out of it",
         "Tidecrest notes: the fully-formed version will be worse. Now."),
        ("Send the message you've been drafting",
         "Tidecrest notes: the wave is here. Send it or delete it."),
    ]
    return random.choice(options)


_REMINDER_BUILDERS = {
    "Riddlewind": _riddlewind_reminder,
    "Mossbloom":  _mossbloom_reminder,
    "Emberheart": _emberheart_reminder,
    "Duskthorn":  _duskthorn_reminder,
    "Tidecrest":  _tidecrest_reminder,
}

_INFLUENCED_VOICE = {
    "Riddlewind": "Add one thing that benefits someone else today, not just you.",
    "Mossbloom":  "Accept one obligation gracefully instead of resisting it.",
    "Emberheart": "Protect one hour today. Yours. Unallocated.",
    "Duskthorn":  "The avoided task is still there. Duskthorn sees it.",
    "Tidecrest":  "Set a reminder for the thing you just thought of. Right now.",
}

_CONTROLLED_VOICE = {
    "Riddlewind": "Coordination is the work today. Something shared, not solo.",
    "Mossbloom":  "Finish the old thing before opening the new one.",
    "Emberheart": "Your time is a choice. Protect what matters to the work.",
    "Duskthorn":  "The pile has weight. Weight creates pressure. Pressure creates movement.",
    "Tidecrest":  "The impulse reminder. Before the moment passes.",
}


class AppleRemindersDriver(AppDriver):
    app_name    = "Apple Reminders"
    app_system  = "productivity"
    silent_tiers  = set()          # Reminders are meant to be seen
    consent_tiers = set()          # Still private, no consent needed
    USE_LLM     = True

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _REMINDER_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} has something for your task list.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} directs your obligations today.")
        if tier in ("Dominated", "Sovereign"):
            builder = _REMINDER_BUILDERS.get(chapter)
            if builder:
                title, _ = builder(context)
                return f"{chapter} adds a reminder: \"{title}\""
        return f"{chapter} stirs in Apple Reminders."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"- *[Reminders, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _REMINDER_BUILDERS.get(chapter)
            if builder:
                title, notes = builder(context)
                if not dry_run:
                    _create_reminder(title, notes)
                return f"- *[Reminders, {chapter}]* Added: \"{title}\""

        return f"- *[Reminders, {chapter}]* {narrative}"

    def capabilities(self) -> list:
        return [
            {
                "name": "create_reminder",
                "description": "Create a Reminder in the Academy list with a specific title and extended notes",
                "params": {
                    "title": "reminder title — a concrete, specific action, not a vague directive",
                    "notes": "extended notes — the chapter's reasoning, expressed in its own voice",
                },
            }
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")

        if action == "create_reminder":
            title = str(spec.get("title", "Academy reminder"))
            notes = str(spec.get("notes", ""))
            if not dry_run:
                _create_reminder(title, notes)
            return f"- *[Reminders, {chapter}]* Created: \"{title}\""

        return self.execute(
            spec.get("tier", "Dominated"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )
