"""
actions/spotify.py — Spotify control via AppleScript (macOS).

Standard interface: every action function returns:
  {"success": bool, "message": str}

Called by governance-engine.py. Never call directly during sessions —
always route through the governance engine so consent is checked and
actions are logged to action-chronicle.md.
"""
import subprocess


def _applescript(script: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or "AppleScript error"
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def play(uri: str = None) -> dict:
    """Play Spotify. If uri provided, play that track/playlist URI."""
    if uri:
        ok, msg = _applescript(f'tell application "Spotify" to play track "{uri}"')
    else:
        ok, msg = _applescript('tell application "Spotify" to play')
    return {"success": ok, "message": msg or ("Playing" if ok else "Failed to play")}


def pause() -> dict:
    ok, msg = _applescript('tell application "Spotify" to pause')
    return {"success": ok, "message": "Paused" if ok else msg}


def playpause() -> dict:
    ok, msg = _applescript('tell application "Spotify" to playpause')
    return {"success": ok, "message": "Toggled" if ok else msg}


def skip() -> dict:
    ok, msg = _applescript('tell application "Spotify" to next track')
    return {"success": ok, "message": "Skipped" if ok else msg}


def volume(level: int) -> dict:
    """Set volume 0–100."""
    level = max(0, min(100, int(level)))
    ok, msg = _applescript(f'tell application "Spotify" to set sound volume to {level}')
    return {"success": ok, "message": f"Volume → {level}" if ok else msg}


def like() -> dict:
    """
    Mark current track — Spotify removed AppleScript 'starred' in v1.2+.
    Fires a macOS notification as a reminder to like it manually, and
    copies the track name to clipboard for easy searching.
    """
    # Get current track info first
    info_script = '''
    tell application "Spotify"
        set t to name of current track
        set a to artist of current track
        return t & " — " & a
    end tell
    '''
    ok, track = _applescript(info_script)
    if not ok:
        return {"success": False, "message": "Spotify not running"}

    # Send a notification as a heartbeat mark
    track_safe = track.replace('"', '\\"')
    notif_script = f'display notification "♥ Mark this one: {track_safe}" with title "The Labyrinth" sound name "default"'
    _applescript(notif_script)

    return {"success": True, "message": f"Marked moment: {track} (Spotify API required for actual like)"}


def current_track() -> dict:
    """Return name + artist of currently playing track."""
    script = '''
    tell application "Spotify"
        set t to name of current track
        set a to artist of current track
        return t & " — " & a
    end tell
    '''
    ok, msg = _applescript(script)
    return {"success": ok, "track": msg if ok else None, "message": msg}


# Dispatch table — governance engine calls run(action_id, params)
def run(action_id: str, params: dict) -> dict:
    dispatch = {
        "spotify_play":      lambda: play(params.get("uri")),
        "spotify_pause":     pause,
        "spotify_playpause": playpause,
        "spotify_skip":      skip,
        "spotify_like":      like,
        "spotify_volume":    lambda: volume(params.get("level", 50)),
        "spotify_queue":     lambda: play(params.get("uri")),  # queue = play for now
    }
    fn = dispatch.get(action_id)
    if not fn:
        return {"success": False, "message": f"Unknown Spotify action: {action_id}"}
    return fn()
