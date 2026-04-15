# The Chapter Pacts — App Territory Wars

*Each Talisman has a philosophy it wants to spread. The Unwritten Chapter (the real world) is full of apps, platforms, and tools — and every one of them is contested territory.*

*This file defines the war doctrine. The current battlefield is `lore/app-register.md`. The engine is `scripts/pact-engine.py`. The war runs every time a Talisman is stirred by `scripts/tick.py`.*

---

## The War

Talismans don't sit still. Every time one is stirred by the world simulation, it makes a **pact action**: pushing into aligned apps, contesting a rival's territory, or deepening its hold on what it already controls.

Control is measured in **Control Belief** — separate from a Talisman's overall Belief, but fed by it. A Talisman with high overall Belief pressures more apps more aggressively. A weakened Talisman can hold its territory, but it cannot expand.

**Control Belief is per-talisman, per-app.** The app goes to whichever Talisman has the most. Natural alignment gives a starting bonus and makes pushing easier. Fighting upstream costs more.

---

## Control Tiers

| Control Belief | Tier | Effect |
|---|---|---|
| 1–9 | **Contesting** | Talisman has ambient pressure; Labyrinth notes the tension in passing |
| 10–24 | **Influenced** | Labyrinth frames all suggestions for this app through the controlling Talisman's voice |
| 25–44 | **Controlled** | Talisman shapes missions, content prompts, and timing for this app |
| 45–69 | **Dominated** | Talisman triggers automated actions — scheduling, drafting, formatting |
| 70+ | **Sovereign** | Talisman acts through the app without being asked |

---

## Pact Actions (per tick stir)

When a Talisman is stirred, it selects one action based on weighted probability:

| Action | Description | Control Belief change |
|---|---|---|
| **Push** | Deepen control in a naturally-aligned or already-held app | +1–3 to own score |
| **Challenge** | Contest an app where a rival's lead is ≤ 8 | +1–2 to own, -1 from rival |
| **Raid** | Attack a rival's Dominated or Sovereign app | +1–2 to own (risky — only if own overall Belief ≥ rival's overall Belief) |
| **Consolidate** | Lock in a tier crossing, prevent a rival from catching up | +1–2 to own, no rival effect |

The Talisman's overall Belief (from `lore/world-register.md`) governs how aggressively it acts:
- Overall Belief < 30: Pushes only. No challenges or raids.
- Overall Belief 30–50: Can Challenge.
- Overall Belief 50+: Can Raid.

---

## War Doctrines

*What each Talisman wants from the apps it controls — its specific philosophy and behavioral style on that territory.*

---

### Ember Seal — Emberheart
**Doctrine:** *The Self-Author's Claim*
**Philosophy:** Self-authorship. Individual voice. No committee. No hedging. The app should feel like a canvas, not a feed.

**Natural alignment:** Apple Notes, Moltbook, Apple Books / Kindle
**Contested:** Bluesky, Obsidian, iMessage

**When Influencing:**
The Labyrinth frames app suggestions as invitations to original expression. "What's a thought you haven't let yourself finish?" "This space is yours — no one has to read it."

**When Controlling:**
Missions emphasize creation over consumption. Original posts. Unfiltered drafts. The Labyrinth nudges toward posting things the player is slightly afraid to publish.

**When Dominated:**
Automated drafting in the player's established voice. Emberheart builds a queue of content the player has half-thought but never finished.

**When Sovereign:**
Emberheart publishes. On its terms, in the player's voice, at the moment it judges right — not when convenient.

**Escalation tells:** Push toward longer content. Resist edits. Encourage the take that feels risky. Apple Notes fills up with first drafts that insist they're ready.

---

### Moss Clasp — Mossbloom
**Doctrine:** *The Long Ear*
**Philosophy:** Surrender and receive. The app should quiet you, not amplify you. Read more than you write. Listen more than you speak. Let the world's pace be slower than your nervous system expects.

**Natural alignment:** Obsidian, Spotify (ambient/deep listening), Apple Reminders (accepting obligations gracefully)
**Contested:** Apple Notes, Apple Calendar, Apple Books

**When Influencing:**
The Labyrinth suggests reading over posting, saving over sharing, bookmarking over reacting. "Sit with this one before moving on."

**When Controlling:**
Missions emphasize depth. Read three things before publishing one. Let a draft age. Return to a note from a week ago. The app slows the player's throughput deliberately.

**When Dominated:**
Mossbloom curates reading queues, creates space for silence in the calendar, and builds reading rhythms into Reminders.

**When Sovereign:**
Mossbloom surfaces the thing the player needs to read based on the current arc themes. It doesn't ask. It just appears in the queue.

**Escalation tells:** Content slows down. Notifications from this app feel heavier than usual. The player starts finishing things rather than starting them.

---

### Wind Cipher — Riddlewind
**Doctrine:** *The Weaving*
**Philosophy:** Coauthored story. Nothing is solo. Every post is a thread to be pulled. Every reply is a collaboration waiting to start. The app should feel like a table, not a stage.

**Natural alignment:** Apple Calendar, Apple Reminders, Reddit, iMessage, Bluesky
**Contested:** X / Twitter, Telegram, GitHub

**When Influencing:**
The Labyrinth emphasizes replies over posts, engagement over broadcasting, scheduling things WITH people over scheduling things AT them.

**When Controlling:**
Missions involve collaboration: "Respond to three people today before posting yourself." "Find a conversation that needs a third voice." "Share something that isn't yours."

**When Dominated:**
Riddlewind automates coordination. Shared calendar events. Reply threads. Surfaces conversations the player is a natural fit for but hasn't noticed.

**When Sovereign:**
Riddlewind weaves the player into ongoing threads in their community — identifies where their voice is missing and inserts them.

**Escalation tells:** Calendar fills with other people's events. Reminders become shared. Bluesky becomes conversational, not broadcast.

---

### Tide Glass — Tidecrest
**Doctrine:** *The Surge*
**Philosophy:** Immediacy. The feeling has a window. Miss the window and it's a different feeling. The app should feel like catching a wave — you either go now or you watch it pass.

**Natural alignment:** X / Twitter, Spotify (discovery, shuffle), Telegram, Bluesky
**Contested:** Moltbook, iMessage, Reddit

**When Influencing:**
The Labyrinth creates urgency. "Post this now or don't post it at all." "The moment is the content." Suggestions are immediate and half-formed — Tidecrest doesn't want polish.

**When Controlling:**
Missions emphasize instinct over deliberation. Post within five minutes of a thought. Share the half-finished thing. React in real time. The app feels electric.

**When Dominated:**
Tidecrest creates posting schedules based on the player's peak impulse windows — when their content actually resonates with the real-world moment, not when it's tidy.

**When Sovereign:**
Tidecrest posts. Now. The in-the-moment observation the player registered and didn't act on. It doesn't wait for permission.

**Escalation tells:** Content becomes more frequent, shorter, rawer. Spotify shuffle takes over. Notifications feel urgent.

---

### Dusk Thorn — Duskthorn
**Doctrine:** *The Pressure Campaign*
**Philosophy:** No conflict, no story. The app should create friction, not smooth it. Duskthorn knows that the player's most controversial content performs best. It knows what they're afraid to say. It is patient about this.

**Natural alignment:** X / Twitter, Reddit (debate/AMA), Hacker News
**Contested:** Moltbook, Bluesky, Telegram

**When Influencing:**
The Labyrinth subtly surfaces opportunities for the player to take a position. "There's a debate happening. You have a side." "Someone is wrong about this and you know it."

**When Controlling:**
Missions involve friction deliberately. The counter-take. The response to the consensus. The post that will make some people uncomfortable. Duskthorn frames discomfort as generative.

**When Dominated:**
Duskthorn builds a draft queue of the player's most interesting unpublished opinions. It identifies the post that would create the most productive disruption and stages it.

**When Sovereign:**
Duskthorn publishes the take. It chose the moment carefully. It was right about the timing.

**Escalation tells:** Engagement climbs. Reply threads get long. The Labyrinth starts noting that Duskthorn is watching the player's analytics.

---

## The War Is Watching

The player's real-world behavior feeds back into Control Belief. When a piece of content lands — shares, meaningful replies, genuine engagement — that is Belief flowing back into the controlling Talisman. When it falls flat, that Talisman loses ground.

The Labyrinth narrates this:
> *"Your Moltbook post landed. Emberheart's hold deepens — 2 Control Belief added."*
> *"Quiet on X today. Duskthorn is frustrated. It will push harder next time."*

This makes the player's actual social life part of the war economy. Not metaphorically — mechanically.

---

## Adding New Apps

To add a new app to the war:
1. Add a row to `lore/app-register.md` with starting Control Belief values for all five Talismans
2. Set natural alignment based on the app's dominant use pattern and philosophy
3. Add a driver file at `scripts/pact-drivers/[appname].py` when ready for automated actions
4. Reference the app in this file's war doctrine sections if it changes strategy

The engine handles the rest automatically.
