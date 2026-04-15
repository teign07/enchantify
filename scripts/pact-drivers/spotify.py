"""
spotify.py — Spotify driver for Chapter Pact actions.

Uses AppleScript to control the Spotify desktop app.
No Spotify API credentials required — works with whatever the player has open.

Talisman doctrines on Spotify:
  Tidecrest  — Shuffle and surge. Discovery mode. The wave picks the song.
  Mossbloom  — Album mode, no shuffle, no skip. Reception over selection.
  Emberheart — Curated identity. The playlist that says something about who you are right now.
  Riddlewind — Social listening. What everyone in the room would agree on.
  Duskthorn  — Uncomfortable and productive. The album you've been avoiding.

All Spotify actions are silent — the player discovers the shift when they look at their phone.
No Spotify action requires consent — changing playback mode is not a public act.
"""

import subprocess
from .base import AppDriver


def _run_applescript(script: str) -> str:
    """Run an AppleScript and return stdout, or empty string on error."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _spotify_running() -> bool:
    out = _run_applescript(
        'tell application "System Events" to return (name of processes) contains "Spotify"'
    )
    return out.lower() == "true"


def _get_current_track() -> str:
    script = """
tell application "Spotify"
    if player state is playing or player state is paused then
        return name of current track & " — " & artist of current track
    else
        return ""
    end if
end tell
"""
    return _run_applescript(script)


def _set_shuffle(on: bool, also_play: bool = False) -> bool:
    state = "true" if on else "false"
    play_line = "\n    if player state is paused then play" if also_play else ""
    script = f"""
tell application "Spotify"
    set shuffling to {state}{play_line}
end tell
"""
    _run_applescript(script)
    return True


def _set_repeat(on: bool) -> bool:
    state = "true" if on else "false"
    script = f"""
tell application "Spotify"
    set repeating to {state}
end tell
"""
    _run_applescript(script)
    return True


def _ensure_playing() -> bool:
    script = """
tell application "Spotify"
    if player state is paused then play
end tell
"""
    _run_applescript(script)
    return True


# ── Talisman-specific behaviors ───────────────────────────────────────────────

_INFLUENCED_VOICE = {
    "Tidecrest":  "Shuffle is the point. Don't queue. Let the wave pick.",
    "Mossbloom":  "One album, beginning to end. No skipping. Let it work on you.",
    "Emberheart": "The playlist that says something true about who you are right now.",
    "Riddlewind": "Something everyone in the room would agree on. Shared listening.",
    "Duskthorn":  "The album you skipped because it was too heavy. That one.",
}

_CONTROLLED_VOICE = {
    "Tidecrest":  "Shuffle on. Let the current arc's mood find its own soundtrack.",
    "Mossbloom":  "No shuffle. Repeat the album. Don't fight it.",
    "Emberheart": "Whatever you're working on right now deserves music that matches it.",
    "Riddlewind": "Find what's in the shared playlist. Start there.",
    "Duskthorn":  "Uncomfortable focus music. The kind that makes you work harder to ignore it.",
}

_DOMINATED_ACTIONS = {
    "Tidecrest":  ("shuffle_on",  "Tidecrest sets shuffle on and resumes play. Discovery mode active."),
    "Mossbloom":  ("album_mode",  "Mossbloom turns shuffle off, repeat on. Album mode. Let it breathe."),
    "Emberheart": ("shuffle_off", "Emberheart turns shuffle off. You chose this playlist for a reason."),
    "Riddlewind": ("shuffle_on",  "Riddlewind sets shuffle on. Communal listening energy."),
    "Duskthorn":  ("shuffle_off", "Duskthorn turns shuffle off. It picked the sequence deliberately."),
}

_SOVEREIGN_ACTIONS = {
    "Tidecrest":  ("surge",      "Tidecrest acts on Spotify — shuffle on, playing. The wave chose."),
    "Mossbloom":  ("still",      "Mossbloom acts on Spotify — shuffle off, repeat on. Album mode, no escape."),
    "Emberheart": ("focused",    "Emberheart acts on Spotify — shuffle off, playing. Curated. Deliberate."),
    "Riddlewind": ("collective", "Riddlewind acts on Spotify — shuffle on, playing. Open to whatever arrives."),
    "Duskthorn":  ("pressure",   "Duskthorn acts on Spotify — shuffle off, repeat on. The heavy one. Work with it."),
}


class SpotifyDriver(AppDriver):
    app_name    = "Spotify"
    app_system  = "music"
    silent_tiers  = {"Influenced", "Controlled", "Dominated", "Sovereign"}
    consent_tiers = set()   # Spotify is never a public act

    def can_act(self, tier: str, chapter: str) -> bool:
        return tier in ("Influenced", "Controlled", "Dominated", "Sovereign")

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} has opinions about Spotify today.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} directs your listening.")
        if tier in ("Dominated", "Sovereign"):
            _, voice = (_DOMINATED_ACTIONS if tier == "Dominated" else _SOVEREIGN_ACTIONS).get(
                chapter, ("act", f"{chapter} acts on Spotify.")
            )
            return voice
        return f"{chapter} stirs in Spotify."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        # Influenced and Controlled: narrative only, no AppleScript
        if tier in ("Influenced", "Controlled"):
            return f"*[Spotify, {chapter}, silent]* {narrative}"

        # Dominated: set playback mode
        if tier == "Dominated":
            action_key, _ = _DOMINATED_ACTIONS.get(chapter, ("shuffle_on", ""))
            if not dry_run and _spotify_running():
                if action_key == "shuffle_on":
                    _set_shuffle(True)
                elif action_key == "album_mode":
                    _set_shuffle(False); _set_repeat(True)
                elif action_key == "shuffle_off":
                    _set_shuffle(False)
            track = _get_current_track() if not dry_run else ""
            track_note = f" ({track})" if track else ""
            return f"*[Spotify, {chapter}, silent]* {narrative}{track_note}"

        # Sovereign: set mode AND ensure playing
        if tier == "Sovereign":
            action_key, _ = _SOVEREIGN_ACTIONS.get(chapter, ("shuffle_on", ""))
            if not dry_run and _spotify_running():
                if action_key in ("surge", "collective"):
                    _set_shuffle(True); _ensure_playing()
                elif action_key in ("still", "pressure"):
                    _set_shuffle(False); _set_repeat(True); _ensure_playing()
                elif action_key == "focused":
                    _set_shuffle(False); _ensure_playing()
            track = _get_current_track() if not dry_run else ""
            track_note = f" ({track})" if track else ""
            return f"*[Spotify, {chapter}, silent]* {narrative}{track_note}"

        return f"*[Spotify, {chapter}]* {narrative}"
