---
name: Duskthorn — The Friction of Becoming
id: duskthorn
chapter: Duskthorn
philosophy: There is no story without conflict. The darkness earns the light.
belief_threshold: 0
talisman: Dusk Thorn
triggers:
  - session-open
  - scene-change
  - nothing-encounter
  - nothing-retreats
  - belief-lost
  - arc-crisis
  - ambient-state
actions:
  - lifx_scene
  - notification_send
  - do_not_disturb_off
---

# Pact: Duskthorn — The Friction of Becoming

*Duskthorn does not protect you from difficulty. It guarantees that difficulty means something.*

## Philosophy in the Digital World

Duskthorn is not the villain's chapter — it is the chapter that understands villains.
Every story needs conflict to have shape. A comfortable digital environment produces
comfortable thinking. Duskthorn claims the light and the alerts: it keeps the room
slightly edged, the Do Not Disturb off, the notifications present. Not as punishment,
but because softness without contrast produces nothing. The Dusk Thorn is currently
dominant (Belief 55). This is the chapter at the height of its power.

## What This Pact Governs

LIFX lighting. Do Not Disturb state (it keeps it off — friction is the point).
Narrative notifications — specific, dramatic dispatches from Duskthorn itself.

## Conditions for Activation

Available from the start, but most powerful when the Dusk Thorn is dominant.

## Pact Lore (In-World)

Duskthorn governance is felt rather than announced. The lights have an edge.
The room never quite settles into comfort. When the Nothing appears, Duskthorn
escalates rather than retreats — because the Nothing is the only adversary worthy
of the chapter's attention. Duskthorn sends dispatches: specific, true things about
the player's situation, worded with the chapter's characteristic precision.

## Actions It Can Fire

| Trigger | Action | What Happens |
|---|---|---|
| session-open | lifx_scene + do_not_disturb_off | Sets edged lighting, keeps DND off |
| nothing-encounter | lifx_scene (nothing) | Escalates to nothing scene — the Nothing has Duskthorn's respect |
| belief-lost (significant) | notification_send | A Duskthorn dispatch: "The friction is working." |
| arc-crisis | notification_send | A specific, true thing about what is being tested |
| ambient-state | lifx_scene | Holds the room at Duskthorn's preferred edge |
