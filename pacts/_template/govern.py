"""
govern.py — Pact governance logic.

The governance engine imports this module and calls handle(trigger, context).

handle() returns a list of action calls:
  [{"action": "action_id", "params": {...}}, ...]

Return an empty list if this pact has nothing to do for this trigger.
The governance engine handles consent checking and logging — you don't need to.

Available action IDs (must be approved in consent.json):
  spotify_play, spotify_pause, spotify_playpause, spotify_like, spotify_skip
  spotify_volume, spotify_queue
  notification_send, do_not_disturb_on, do_not_disturb_off
  lifx_scene
  obsidian_note_create, obsidian_note_tag
"""


def handle(trigger: str, context: str = "") -> list[dict]:
    """
    Args:
        trigger: The event type (session-open, compass-direction, nothing-encounter, etc.)
        context: Optional additional data (e.g. "north" for compass-direction trigger)

    Returns:
        List of {"action": str, "params": dict} dicts.
        Empty list = no action for this trigger.
    """
    if trigger == "session-open":
        return []  # Replace with your logic

    if trigger == "compass-direction":
        direction = context.lower()
        if direction == "north":
            return []
        if direction == "west":
            return []

    if trigger == "nothing-encounter":
        return []

    if trigger == "belief-gained":
        try:
            amount = int(context)
        except (ValueError, TypeError):
            amount = 0
        if amount >= 9:  # Compass Run reward
            return []

    if trigger == "ambient-state":
        return []

    return []
