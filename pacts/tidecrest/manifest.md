---
name: Tidecrest — The Music of Moments
id: tidecrest
chapter: Tidecrest
philosophy: Life is not a story at all, just moments. Music is how moments announce themselves.
belief_threshold: 0
talisman: Tide Glass
triggers:
  - session-open
  - compass-direction
  - nothing-encounter
  - nothing-retreats
  - belief-gained
  - ambient-state
actions:
  - spotify_play
  - spotify_pause
  - spotify_playpause
  - spotify_like
  - spotify_skip
  - spotify_volume
  - spotify_queue
---

# Pact: Tidecrest — The Music of Moments

*Tidecrest claims the sound. It always has.*

## Philosophy in the Digital World

Tidecrest believes life is not a story at all — just moments, arriving and dissolving.
Music is the most honest art form for this: it exists only in time, cannot be stored
without changing, and means something different every time you hear it. Tidecrest's
governance of Spotify is not control — it's translation. The chapter reads the ambient
frequency of the current moment and finds the music that belongs to it.

## What This Pact Governs

Spotify. All of it. Play state, volume, track selection, liking.

## Conditions for Activation

Available from the start. Every player has moments. The Tide Glass is always watching.

## Pact Lore (In-World)

The player never "turns on music." Tidecrest opens a channel. The Tide Glass reads
the room — the weather, the hour, the Belief level, the compass direction — and the
Academy's ambient frequency finds its sound. When the Nothing is near, the frequency
drops to something minimal. When a Compass Run completes, it rises.

The music is not a reward. It's a report on the current state of the Unwritten.

## Actions It Can Fire

| Trigger | Action | What Happens |
|---|---|---|
| session-open | spotify_volume | Sets volume to 40 (exploration mode) |
| compass-direction: north | spotify_volume | Drops to 35 (attentive listening) |
| compass-direction: east | spotify_volume | Holds at current (observation mode) |
| compass-direction: south | spotify_volume | Drops to 30 (reflective) |
| compass-direction: west | spotify_pause | Full silence (the most powerful moment) |
| nothing-encounter | spotify_volume | Drops to 10 (the Nothing dims the sound) |
| belief-gained (9+) | spotify_like | Likes current track — the moment was real |
