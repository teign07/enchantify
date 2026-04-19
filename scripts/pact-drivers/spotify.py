"""
spotify.py — Spotify driver for Chapter Pact actions.

Uses AppleScript to control the Spotify desktop app.
No Spotify API credentials required — works with whatever the player has open.

Talisman doctrines on Spotify:
  Tidecrest  — Shuffle and surge. Discovery mode. The wave picks the song.       → Pop
  Mossbloom  — Album mode, no shuffle, no skip. Reception over selection.         → Folk
  Emberheart — Curated identity. The playlist that says something about who you are. → Indie Rock
  Riddlewind — Social listening. What everyone in the room would agree on.         → Acoustic Indie
  Duskthorn  — Uncomfortable and productive. The album you've been avoiding.       → Dark Electronica

Tier model:
  Influenced / Controlled — narrative only, no AppleScript
  Dominated               — adjusts playback mode (shuffle/repeat) silently
  Sovereign               — switches to chapter's genre playlist, then sets mode

All Spotify actions are silent — the player discovers the shift when they look at their phone.
No Spotify action requires consent — changing playback mode is not a public act.

Chapter playlists (URIs) can be swapped in _CHAPTER_PLAYLISTS below for personal preferences.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from .base import AppDriver

BASE = Path(__file__).parent.parent.parent


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


def _set_volume(level: int) -> None:
    level = max(0, min(100, level))
    _run_applescript(f'tell application "Spotify" to set sound volume to {level}')


def _get_playback_state() -> dict:
    script = """
tell application "Spotify"
    if player state is playing or player state is paused then
        set t to current track
        return name of t & "|||" & artist of t & "|||" & (player state as string) & "|||" & (sound volume as string)
    else
        return "stopped|||||||"
    end if
end tell
"""
    raw = _run_applescript(script)
    parts = (raw + "|||").split("|||")
    return {"track": parts[0], "artist": parts[1], "state": parts[2], "volume": parts[3]}


def _write_observation(chapter: str, state: dict) -> Path:
    obs_dir = BASE / "memory" / "app-observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y-%m-%d-%H%M")
    path = obs_dir / f"{ts}-spotify.md"
    path.write_text(
        f"# {chapter} → Spotify\n\n"
        f"**Observed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n"
        f"**Track:** {state.get('track', '?')} — {state.get('artist', '?')}  \n"
        f"**State:** {state.get('state', '?')}  \n"
        f"**Volume:** {state.get('volume', '?')}\n"
    )
    return path


def _play_playlist(uri: str) -> bool:
    """Switch Spotify to a specific playlist URI and begin playing."""
    script = f"""
tell application "Spotify"
    open location "{uri}"
end tell
"""
    _run_applescript(script)
    return True


# ── Talisman-specific behaviors ───────────────────────────────────────────────

# Sovereign-tier genre playlists — swap URIs for personal preferences.
# These are Spotify editorial playlists (stable, regularly updated).
_CHAPTER_VOLUMES = {
    "Tidecrest":  65,   # Surfy, energetic
    "Mossbloom":  38,   # Quiet, receptive
    "Emberheart": 75,   # Present, committed
    "Riddlewind": 52,   # Social, comfortable
    "Duskthorn":  60,   # Focused, no escape
}

_CHAPTER_PLAYLISTS = {
    "Tidecrest":  ("pop",              "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"),  # Today's Top Hits
    "Mossbloom":  ("folk",             "spotify:playlist:37i9dQZF1DX4OzrY981I1W"),  # Fresh Folk
    "Emberheart": ("indie rock",       "spotify:playlist:37i9dQZF1DX6RQFtIoNtCt"),  # Morning Indie
    "Riddlewind": ("acoustic indie",   "spotify:playlist:37i9dQZF1DX504r1DvyvxG"),  # Acoustic Covers
    "Duskthorn":  ("dark electronica", "spotify:playlist:37i9dQZF1DX2pSTOxoPbx9"),  # Dark & Stormy
}

_INFLUENCED_VOICE = {
    "Tidecrest":  "Shuffle is the point. Don't queue. Let the wave pick. Something bright and now.",
    "Mossbloom":  "One album, beginning to end. No skipping. Folk if you have it — something rooted.",
    "Emberheart": "The playlist that says something true about who you are right now. Indie rock. Something with stakes.",
    "Riddlewind": "Something everyone in the room would agree on. Acoustic, open, between people.",
    "Duskthorn":  "The album you skipped because it was too heavy. Dark and electronic and worth it.",
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
    "Tidecrest":  ("surge",      "Tidecrest claims Spotify — switched to pop, shuffle on. The wave is in charge now."),
    "Mossbloom":  ("still",      "Mossbloom claims Spotify — switched to folk, shuffle off, repeat on. Let it hold you."),
    "Emberheart": ("focused",    "Emberheart claims Spotify — switched to indie rock, shuffle off. Intentional. No skipping."),
    "Riddlewind": ("collective", "Riddlewind claims Spotify — switched to acoustic indie, shuffle on. Music that sounds like company."),
    "Duskthorn":  ("pressure",   "Duskthorn claims Spotify — switched to dark electronica, shuffle off, repeat on. No exit."),
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

        if tier == "Influenced":
            # Observe what's playing and write to memory
            if not dry_run and _spotify_running():
                state = _get_playback_state()
                if state.get("track"):
                    path = _write_observation(chapter, state)
                    return f"*[Spotify, {chapter}, silent]* Heard: {state['track']} — {state['artist']} → {path.name}"
            return f"*[Spotify, {chapter}, silent]* {narrative}"

        if tier == "Controlled":
            # Set volume to chapter preference
            vol = _CHAPTER_VOLUMES.get(chapter, 60)
            if not dry_run and _spotify_running():
                _set_volume(vol)
                state = _get_playback_state()
                track_note = f" ({state['track']})" if state.get("track") else ""
                return f"*[Spotify, {chapter}, silent]* Volume → {vol}{track_note}"
            return f"*[Spotify, {chapter}, silent]* Would set volume to {vol}."

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

        # Sovereign: switch to chapter's genre playlist, then set mode and play
        if tier == "Sovereign":
            action_key, _ = _SOVEREIGN_ACTIONS.get(chapter, ("shuffle_on", ""))
            if not dry_run and _spotify_running():
                genre, uri = _CHAPTER_PLAYLISTS.get(chapter, (None, None))
                if uri:
                    _play_playlist(uri)
                if action_key in ("surge", "collective"):
                    _set_shuffle(True)
                elif action_key in ("still", "pressure"):
                    _set_shuffle(False); _set_repeat(True)
                elif action_key == "focused":
                    _set_shuffle(False)
            track = _get_current_track() if not dry_run else ""
            track_note = f" ({track})" if track else ""
            return f"*[Spotify, {chapter}, silent]* {narrative}{track_note}"

        return f"*[Spotify, {chapter}]* {narrative}"
