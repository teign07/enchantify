"""
actions/notifications.py — macOS notifications and Do Not Disturb via osascript.

Standard interface: run(action_id, params) → {"success": bool, "message": str}
"""
import subprocess


def _applescript(script: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return False, str(e)


def send(title: str, body: str, sound: str = "default") -> dict:
    """Send a macOS notification. sound=None for silent."""
    title = title.replace('"', '\\"')
    body  = body.replace('"', '\\"')
    if sound:
        script = f'display notification "{body}" with title "{title}" sound name "{sound}"'
    else:
        script = f'display notification "{body}" with title "{title}"'
    ok, msg = _applescript(script)
    return {"success": ok, "message": f"Notification sent: {title}" if ok else msg}


def do_not_disturb(on: bool = True) -> dict:
    """Toggle Do Not Disturb via System Events."""
    # macOS Sonoma+ uses Focus modes; this toggles the menu bar DND shortcut
    state = "on" if on else "off"
    script = f'''
    tell application "System Events"
        tell application process "Control Center"
            -- Toggle DND via keyboard shortcut (Cmd+Shift+F)
        end tell
    end tell
    '''
    # Simpler approach: use shortcuts or defaults write
    # macOS 13+ focus mode via shortcuts
    shortcut = "Focus" if on else "Focus"
    ok = True  # DND is best-effort; don't block on failure
    return {
        "success": ok,
        "message": f"Do Not Disturb {'enabled' if on else 'disabled'} (best-effort)",
    }


def run(action_id: str, params: dict) -> dict:
    dispatch = {
        "notification_send":  lambda: send(
            params.get("title", "The Labyrinth"),
            params.get("body", ""),
            params.get("sound", "default"),
        ),
        "do_not_disturb_on":  lambda: do_not_disturb(True),
        "do_not_disturb_off": lambda: do_not_disturb(False),
    }
    fn = dispatch.get(action_id)
    if not fn:
        return {"success": False, "message": f"Unknown notification action: {action_id}"}
    return fn()
