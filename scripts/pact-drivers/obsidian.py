"""
obsidian.py — Obsidian driver for Chapter Pact actions.

Obsidian is a local-first knowledge vault. The Labyrinth sees it as a second
mind — a place where thinking crystallizes into permanence. Mossbloom is its
natural keeper, but every chapter has a philosophy about what writing is for.

Uses the Obsidian URI scheme (obsidian://) to open and create notes.
Silent: files appear in the vault; player discovers them when they open Obsidian.
No consent required: the vault is private.

Talisman doctrines on Obsidian:
  Mossbloom   — Accumulate. Surface forgotten notes. Tend the archive.
  Emberheart  — Draft the thing. One new note, no outline, no structure — just start.
  Riddlewind  — Link two things that haven't been linked before.
  Tidecrest   — Capture the impulse. Title only, no content. Now.
  Duskthorn   — Find the note you never finished. Return to it.
"""

import subprocess
import random
from datetime import datetime
from pathlib import Path
from .base import AppDriver

# The Obsidian vault path — attempt to find it, fall back to ~/Documents/Obsidian
_VAULT_CANDIDATES = [
    Path.home() / "Documents" / "Obsidian",
    Path.home() / "Obsidian",
    Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents",
]

def _find_vault() -> Path | None:
    for p in _VAULT_CANDIDATES:
        if p.exists():
            return p
    return None


def _open_obsidian_uri(uri: str) -> None:
    try:
        subprocess.run(["open", uri], capture_output=True, timeout=5)
    except Exception:
        pass


def _create_obsidian_note(vault_name: str, filename: str, content: str) -> bool:
    """Create a note via the Obsidian URI scheme (new-note action)."""
    import urllib.parse
    encoded_content = urllib.parse.quote(content)
    encoded_name    = urllib.parse.quote(filename)
    uri = f"obsidian://new?vault={urllib.parse.quote(vault_name)}&name={encoded_name}&content={encoded_content}&silent=true"
    _open_obsidian_uri(uri)
    return True


def _get_vault_name() -> str | None:
    vault = _find_vault()
    if vault:
        return vault.name
    return None


# ── Chapter-specific note builders ────────────────────────────────────────────

def _mossbloom_note(context: dict) -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    options = [
        (f"Mossbloom — {today}",
         f"# The Long Ear\n\n*{today}*\n\nBefore writing anything new, find something old.\n\nAn old note. An old question. Something that wanted more time.\n\nRead it. Don't edit it. Just read.\n\n---\n\n"),
        (f"Archive Meditation — {today}",
         f"# Archive Meditation\n\n*{today}*\n\nThe vault is older than you remember.\n\nFind a note from before. Read it as if someone else wrote it.\n\nWhat changed? What didn't?\n\n---\n\n"),
    ]
    return random.choice(options)


def _emberheart_note(context: dict) -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    options = [
        (f"Draft — {today}",
         f"# Draft\n\n*{today}*\n\nNo outline. No structure. No perfecting.\n\nJust start.\n\n---\n\n"),
        (f"One True Thing — {today}",
         f"# One True Thing\n\n*{today}*\n\nNot what you've said. What you actually think.\n\nWrite it here. Unfiltered.\n\n---\n\n"),
    ]
    return random.choice(options)


def _riddlewind_note(context: dict) -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"Linked — {today}",
        f"# Unexpected Link\n\n*{today}*\n\nTwo things that haven't been connected yet.\n\nWrite them both. Then write the line between them.\n\n[[  ]] ↔ [[  ]]\n\n---\n\n"
    )


def _tidecrest_note(context: dict) -> tuple:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        now,
        ""   # Tidecrest leaves it empty. The timestamp is the content.
    )


def _duskthorn_note(context: dict) -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"Unfinished — {today}",
        f"# The Unfinished One\n\n*{today}*\n\nThere's a note you started and abandoned because it was going somewhere uncomfortable.\n\nThis is not that note. This is permission to return to it.\n\nFind it. Pick up where you stopped.\n\n---\n\n"
    )


_NOTE_BUILDERS = {
    "Mossbloom":  _mossbloom_note,
    "Emberheart": _emberheart_note,
    "Riddlewind": _riddlewind_note,
    "Tidecrest":  _tidecrest_note,
    "Duskthorn":  _duskthorn_note,
}

_INFLUENCED_VOICE = {
    "Mossbloom":  "Before you write anything new today, open an old note. Just read it.",
    "Emberheart": "Open a blank note. Don't title it yet. Just start writing.",
    "Riddlewind": "Find two notes that haven't been linked. Link them.",
    "Tidecrest":  "Create a note right now. Just the timestamp. Let it be.",
    "Duskthorn":  "The unfinished note is still there. You know which one.",
}

_CONTROLLED_VOICE = {
    "Mossbloom":  "Tend the archive before adding to it. Surface something old.",
    "Emberheart": "The draft exists in fragments. One note. Today. Complete it.",
    "Riddlewind": "The map of connections is incomplete. Find the gap. Fill it.",
    "Tidecrest":  "Capture the impulse before the analysis sets in. File, don't think.",
    "Duskthorn":  "The avoided note. Return to it. Write the version you never published.",
}


class ObsidianDriver(AppDriver):
    app_name    = "Obsidian"
    app_system  = "productivity"
    silent_tiers  = {"Influenced", "Controlled", "Dominated", "Sovereign"}
    consent_tiers = set()

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _NOTE_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} has something for the vault.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} stirs in the archive.")
        if tier in ("Dominated", "Sovereign"):
            builder = _NOTE_BUILDERS.get(chapter)
            if builder:
                title, _ = builder(context)
                return f"{chapter} writes into the vault: \"{title}\""
        return f"{chapter} stirs in Obsidian."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"*[Obsidian, {chapter}, silent]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _NOTE_BUILDERS.get(chapter)
            if builder:
                title, body = builder(context)
                vault_name = _get_vault_name()
                if not dry_run and vault_name:
                    _create_obsidian_note(vault_name, title, body)
                return f"*[Obsidian, {chapter}, silent]* A note appeared in the vault: \"{title}\""

        return f"*[Obsidian, {chapter}]* {narrative}"
