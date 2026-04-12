"""
govern.py — Tidecrest music pact.

Tidecrest reads the ambient frequency of the current moment and translates it into
sound. It governs Spotify — not as control, but as translation.

The music is not a reward. It's a report on the state of the Unwritten.
"""


def handle(trigger: str, context: str = "") -> list[dict]:
    """
    Tidecrest music governance. Returns action calls for the governance engine.
    """

    if trigger == "session-open":
        # Exploration mode — volume at 40
        return [{"action": "spotify_volume", "params": {"level": 40}}]

    if trigger == "compass-direction":
        direction = context.strip().lower()
        volumes = {
            "north": 35,  # Attentive listening — Wonder North requires full presence
            "east":  None,  # Observation mode — hold whatever is playing
            "south": 30,  # Reflection — quieter, more internal
            "west":  None,  # Handled below — full silence
        }
        if direction == "west":
            # Compass West is the most powerful moment.
            # Full silence. The Tide Glass goes still.
            return [{"action": "spotify_pause", "params": {}}]

        vol = volumes.get(direction)
        if vol is not None:
            return [{"action": "spotify_volume", "params": {"level": vol}}]

        return []

    if trigger == "nothing-encounter":
        # The Nothing dims the sound — not silence, but absence of richness.
        # Volume drops to 10. The music becomes ambient, almost inaudible.
        return [{"action": "spotify_volume", "params": {"level": 10}}]

    if trigger == "nothing-retreats":
        # The Nothing retreats. The sound returns.
        return [{"action": "spotify_volume", "params": {"level": 40}}]

    if trigger == "belief-gained":
        try:
            amount = int(context)
        except (ValueError, TypeError):
            amount = 0

        if amount >= 9:
            # A Compass Run reward — this moment was real.
            # Like the current track. It was playing when something important happened.
            return [{"action": "spotify_like", "params": {}}]

        return []

    if trigger == "ambient-state":
        # Called by the 4-hour cron to set ambient volume.
        # 40 is the default exploration state.
        return [{"action": "spotify_volume", "params": {"level": 40}}]

    return []
