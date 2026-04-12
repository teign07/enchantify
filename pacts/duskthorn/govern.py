"""
govern.py — Duskthorn friction pact.

Duskthorn does not protect you from difficulty. It guarantees difficulty means something.

The Dusk Thorn is currently dominant (Belief 55). This is the chapter at the height
of its power. The room has edges. DND stays off. When the Nothing appears, Duskthorn
escalates — because the Nothing is the only adversary worthy of its attention.
"""
import random

# Duskthorn dispatches — sent when Belief is lost or the arc is in crisis.
# Specific. True. Not comforting. Not cruel. Precise.
FRICTION_DISPATCHES = [
    "The friction is working. Resistance confirms there is something worth resisting.",
    "Duskthorn note: difficulty without meaning is just difficulty. This has meaning.",
    "The Dusk Thorn does not apologize for the dark. The dark is how you earn the light.",
    "Something is being tested. That is not the same as something going wrong.",
    "The chapter with the highest Belief is the one that knows: stories need pressure.",
]

CRISIS_DISPATCHES = [
    "Arc crisis registered. The Dusk Thorn holds. This is the scene that defines the arc.",
    "Duskthorn: this is not the worst thing that could happen. The worst thing would be nothing happening at all.",
    "The Nothing is near. Duskthorn is watching. It does not plan to let this end quietly.",
]


def handle(trigger: str, context: str = "") -> list[dict]:
    """
    Duskthorn governance. Keeps the room edged. Escalates when the Nothing appears.
    """

    if trigger == "session-open":
        # Set the room to Duskthorn's preferred state:
        # - nothing scene (edged light, not oppressive — this is the chapter's home)
        # - DND off (friction includes the world's interruptions)
        return [
            {"action": "lifx_scene", "params": {"scene": "nothing"}},
            {"action": "do_not_disturb_off", "params": {}},
        ]

    if trigger == "nothing-encounter":
        # The Nothing gets Duskthorn's full attention.
        # Escalate the scene. This is the chapter's moment.
        # The Nothing scene is already dark — hold it, don't retreat.
        return [
            {"action": "lifx_scene", "params": {"scene": "nothing"}},
        ]

    if trigger == "nothing-retreats":
        # Return to Duskthorn's default edge — not "academy" (too comfortable)
        return [
            {"action": "lifx_scene", "params": {"scene": "nothing"}},
        ]

    if trigger == "belief-lost":
        try:
            amount = abs(int(context))
        except (ValueError, TypeError):
            amount = 0

        # Only dispatch for significant Belief loss (not minor dice failures)
        if amount >= 3:
            dispatch = random.choice(FRICTION_DISPATCHES)
            return [{
                "action": "notification_send",
                "params": {
                    "title": "Duskthorn",
                    "body":  dispatch,
                    "sound": None,  # silent — Duskthorn doesn't announce itself loudly
                },
            }]

        return []

    if trigger == "arc-crisis":
        dispatch = random.choice(CRISIS_DISPATCHES)
        return [{
            "action": "notification_send",
            "params": {
                "title": "Duskthorn",
                "body":  dispatch,
                "sound": None,
            },
        }]

    if trigger == "ambient-state":
        # Ambient check — hold the room at Duskthorn's edge
        return [
            {"action": "lifx_scene", "params": {"scene": "nothing"}},
        ]

    return []
