"""
apple_notes.py — Apple Notes driver for Chapter Pact actions.

Uses AppleScript to create and surface notes.
Silent: player discovers a new note or a surfaced draft when they open the app.
No consent required: Notes is a private space.

Talisman doctrines on Apple Notes:
  Emberheart — Create. The blank note, the unfinished draft, the thing that needs saying.
  Mossbloom  — Archive and surface. Old notes that deserve a second read.
  Duskthorn  — Surface the avoided. The note you made and didn't finish because it was uncomfortable.
  Riddlewind — Shared or collaborative framing. Notes that want a second voice.
  Tidecrest  — Quick capture. The impulse note, titled with the date and nothing else.
"""

import subprocess
import re
from datetime import datetime
from .base import AppDriver


def _run_applescript(script: str) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=8
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _notes_running() -> bool:
    out = _run_applescript(
        'tell application "System Events" to return (name of processes) contains "Notes"'
    )
    return out.lower() == "true"


def _create_note(title: str, body: str, folder: str = "Notes") -> bool:
    # Escape for AppleScript
    safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
    safe_body  = body.replace('"', '\\"').replace("\\", "\\\\")
    script = f"""
tell application "Notes"
    tell account "iCloud"
        make new note at folder "{folder}" with properties {{name:"{safe_title}", body:"{safe_body}"}}
    end tell
end tell
"""
    result = _run_applescript(script)
    return True   # AppleScript errors are swallowed; the note either appears or doesn't


def _get_oldest_note_title() -> str:
    """Return the name of the oldest note in the default folder."""
    script = """
tell application "Notes"
    tell account "iCloud"
        set noteList to every note in folder "Notes"
        if (count of noteList) = 0 then return ""
        set oldest to item 1 of noteList
        repeat with n in noteList
            if creation date of n < creation date of oldest then set oldest to n
        end repeat
        return name of oldest
    end tell
end tell
"""
    return _run_applescript(script)


# ── Chapter-specific note prompts ─────────────────────────────────────────────

def _emberheart_prompt(context: dict) -> tuple:
    arc   = context.get("arc_phase", "SETUP")
    today = datetime.now().strftime("%B %d")
    prompts = [
        ("One True Thing",
         f"Date: {today}\n\nWrite one thing you actually think.\nNot what you've said. What you actually think.\n\n—"),
        ("The Draft That Isn't Done",
         f"Date: {today}\n\nSomething is more finished than you've admitted.\nStart here.\n\n—"),
        ("Say the Specific Thing",
         f"Date: {today}\n\nNot the general version. The specific one.\nWho, what, exactly.\n\n—"),
    ]
    import random
    title, body = random.choice(prompts)
    if arc == "CLIMAX":
        body = f"[Arc is in CLIMAX — the stakes are highest right now.]\n\n" + body
    return title, body


def _mossbloom_prompt(context: dict) -> tuple:
    """Mossbloom doesn't create — it surfaces. Returns a note to surface, or creates a reflection prompt."""
    today = datetime.now().strftime("%B %d")
    return (
        f"Mossbloom — {today}",
        f"The long ear.\n\nBefore you write anything new today, find something old.\n"
        f"An old note. An old draft. Something that wanted more time than you gave it.\n\n"
        f"Read it. Don't edit it. Just read it.\n\n—"
    )


def _duskthorn_prompt(context: dict) -> tuple:
    today = datetime.now().strftime("%B %d")
    return (
        f"Duskthorn — {today}",
        f"The uncomfortable one.\n\nThere's a note you started and didn't finish because it was "
        f"going somewhere you weren't sure about.\n\nThis is permission to go there.\n\n"
        f"Write the version you'd never publish. Then decide.\n\n—"
    )


def _riddlewind_prompt(context: dict) -> tuple:
    today = datetime.now().strftime("%B %d")
    return (
        f"Riddlewind — {today}",
        f"The second voice.\n\nThis note isn't finished by you alone.\n\n"
        f"Write the part you know. Leave space for what someone else would add.\n"
        f"Coauthored stories are better stories.\n\n—"
    )


def _tidecrest_prompt(context: dict) -> tuple:
    now = datetime.now().strftime("%B %d, %H:%M")
    return (
        now,
        f"—"   # Just the timestamp. Tidecrest leaves the note empty. The moment is the content.
    )


_PROMPT_BUILDERS = {
    "Emberheart": _emberheart_prompt,
    "Mossbloom":  _mossbloom_prompt,
    "Duskthorn":  _duskthorn_prompt,
    "Riddlewind": _riddlewind_prompt,
    "Tidecrest":  _tidecrest_prompt,
}

_INFLUENCED_VOICE = {
    "Emberheart": "A blank note is waiting. Don't title it yet.",
    "Mossbloom":  "Before writing anything new, find something old. Read it.",
    "Duskthorn":  "The note you started and didn't finish. Find it. Continue.",
    "Riddlewind": "This note wants a second voice. Write the part you know.",
    "Tidecrest":  "Open Notes now. Write the date and one line. That's it.",
}

_CONTROLLED_VOICE = {
    "Emberheart": "The draft exists. The only thing between it and the world is a decision.",
    "Mossbloom":  "Surface the old thing before starting the new one.",
    "Duskthorn":  "Write the version you'd never publish. Then decide.",
    "Riddlewind": "Three things you know. Space for what someone else would add.",
    "Tidecrest":  "No title. Just the timestamp and whatever comes next.",
}


class AppleNotesDriver(AppDriver):
    app_name    = "Apple Notes"
    app_system  = "productivity"
    silent_tiers  = {"Influenced", "Controlled", "Dominated", "Sovereign"}
    consent_tiers = set()   # Notes is private

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _PROMPT_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} has something to say about your notes.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} directs your note-taking today.")
        if tier in ("Dominated", "Sovereign"):
            builder = _PROMPT_BUILDERS.get(chapter)
            if builder:
                title, _ = builder(context)
                return f"{chapter} creates a note: \"{title}\""
        return f"{chapter} stirs in Apple Notes."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"*[Apple Notes, {chapter}, silent]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _PROMPT_BUILDERS.get(chapter)
            if builder:
                title, body = builder(context)
                if not dry_run:
                    _create_note(title, body)
                return f"*[Apple Notes, {chapter}, silent]* A note appeared: \"{title}\". Open Notes to find it."

        return f"*[Apple Notes, {chapter}]* {narrative}"
