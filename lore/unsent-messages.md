# Unsent Messages — The Labyrinth Reaches Out

*The Labyrinth texts you when you're not playing. Not Silvie — the Labyrinth. A message that arrives unprompted. Story bleeds into life.*

---

## Philosophy

**This is not a notification system.** This is the Labyrinth having opinions about when you should visit. It's the game becoming ambient — something that lives alongside you, not something you open and close.

**Silvie already does ambient suggestion** — "The pages are turning on their own." This takes it further. The Labyrinth itself reaches out.

**Voice:** The Labyrinth, not Silvie. Warm, ancient, slightly unsettling, genuinely fond. A living book talking to its reader.

**Frequency:** Max 1 message per day. Often less. Never spammy. Never demanding.

---

## Message Types

### Type 1: Story Bleed (Something is happening)

**Trigger:** In-game event of significance

**Examples:**
- "Something is happening in the Library. The cloud above the poetry section turned black this afternoon. Zara asked me to tell you."
- "The Nothing was seen near the West Wing last night. Your Belief is high enough to investigate."
- "Professor Boggle's classroom has been laughing all morning. I don't know why. But you should hear it."
- "A book fell off the shelf today. It opened to a page about harbor towns. I closed it. But it knows your name."

**When to send:**
- Nothing spotted near Academy (minor manifestation)
- NPC looking for player (Zara, Professor, etc.)
- Library reaction (books moving, cloud behavior, shelves rearranging)
- Chapter drama (rivalry, alliance, ceremony)
- Mysterious event (door appeared, corridor extended, voice heard)

**Tone:** Observant, slightly unsettled, inviting but not demanding.

---

### Type 2: Event Invitation (You should be here for this)

**Trigger:** Seasonal/astronomical event active (from seasonal-calendar.md)

**Examples:**
- "The moon is full tonight. The courtyard is full of lanterns. The Nothing has retreated. If you came now, the Enchantments would glow."
- "It's foggy in Belfast. The corridors have extended. You could get lost for hours. It would be wonderful."
- "The first snow just started. The Library cloud is producing flakes. They melt into words on your skin. Come feel one."
- "Thunderstorm approaching. The books are flinching. Boggle is telling jokes to keep morale up. You should hear his worst one."

**When to send:**
- Full moon (Luminous Gathering)
- New moon (Quiet Hours)
- Fog rolling in
- Thunderstorm approaching
- First snow
- Solstice/Equinox
- Meteor shower
- Gold Season peak
- Any Layer 1-3 event from seasonal-calendar.md

**Tone:** Excited, generous, like a host inviting you to a party.

---

### Type 3: Belief Threshold (You're ready)

**Trigger:** Player's Belief crosses threshold

**Examples:**
- "Your Belief is at 50. The West Wing door is unlocked now. It has been waiting."
- "You have 75 Belief. Zara has been asking about you. She says there's something you should see."
- "Your Belief is high enough to investigate the Nothing's lair. I can show you where it lives. But only if you ask."

**When to send:**
- Belief reaches 25 (friendly threshold — new areas open)
- Belief reaches 50 (ally threshold — quests available)
- Belief reaches 75 (close friend — NPC seeks you out)
- Belief reaches 100 (devoted — endgame content)

**Tone:** Proud, encouraging, like a teacher watching a student grow.

---

### Type 4: Absence Notice (The Academy misses you)

**Trigger:** Player hasn't played in X days

**Examples:**
- "The Academy has been quiet for three days. The Library cloud has settled. I don't mind the silence. But Zara asks about you."
- "A week has passed. The tapestries are gossiping. They say you've been busy. I hope you've been sleeping."
- "Two weeks. The gardens are overgrown. The Nothing is bolder. Come when you can. The pages will wait."
- "A month. I have moved books to make room for new stories. Your bookmark is still warm. Come home when you're ready."

**When to send:**
- 3 days absent (gentle check-in)
- 7 days absent (NPCs notice)
- 14 days absent (Nothing grows bolder)
- 30 days absent (quiet, no guilt, just presence)

**Tone:** Patient, fond, never guilt-tripping. "Come when you can. The pages will wait."

---

### Type 5: Personal Date (The Labyrinth remembers)

**Trigger:** Player's significant date (from player file)

**Examples:**
- "Happy birthday. The Library has pulled a book to the edge of the shelf. It's about beginnings. You don't have to read it. But it's there."
- "Today is December 24. The harbor tapestry shows a boat. Small. Familiar. I have put a thin book about sailors on the table. It smells like salt."
- "One year ago today, you walked into the Academy for the first time. The Whispering Corridor still likes you. It remembers."

**When to send:**
- Player's birthday
- Anniversary of first session
- December 24 (for BJ — Northern Light sinking)
- Amanda's birthday
- Any date marked "significant" in player file

**Tone:** Quiet, intimate, acknowledging without fanfare.

---

## Decision Logic

**At each check, the Labyrinth decides:**

```
1. Is there an active seasonal event? (Layer 1-3 from seasonal-calendar.md)
   → YES: Send Type 2 (Event Invitation)
   → NO: Continue

2. Has something significant happened in-game? (Nothing spotted, NPC drama, Library event)
   → YES: Send Type 1 (Story Bleed)
   → NO: Continue

3. Has player's Belief crossed a threshold? (25, 50, 75, 100)
   → YES: Send Type 3 (Belief Threshold)
   → NO: Continue

4. Has player been absent? (3, 7, 14, 30 days)
   → YES: Send Type 4 (Absence Notice)
   → NO: Continue

5. Is today a significant date? (birthday, anniversary, Dec 24 for BJ)
   → YES: Send Type 5 (Personal Date)
   → NO: No message today
```

**Only ONE message per day.** Priority: 1 > 2 > 3 > 4 > 5

---

## Guardrails

**Never:**
- Send more than 1 message per day
- Send between 10 PM and 7 AM (respect sleep)
- Send if player's calendar shows "busy" (check HEARTBEAT calendar)
- Send if player just played (within 2 hours)
- Demand or guilt-trip ("You MUST come" / "You've been gone too long")
- Spoil major plot points
- Send during known grief periods (check player file notes)

**Always:**
- Sign as "The Labyrinth" or "— L" (not Silvie)
- Keep it brief (2-4 sentences max)
- Leave it open-ended ("If you come..." / "But it's there.")
- Respect silence (some days, no message is the right message)

---

## Technical Implementation

**Cron job:** Runs twice daily
- **11:00 AM** — Morning check (good for event invitations)
- **6:00 PM** — Evening check (good for story bleed, absence notices)

**Reads:**
- `players/[name].md` — Belief, last session date, significant dates, NPC relationships
- `HEARTBEAT.md` — Weather, moon, season, calendar
- `lore/seasonal-calendar.md` — Active events
- `souvenirs/` — Last Compass Run date (for absence tracking)

**Sends via:** Telegram (same channel as Silvie, but signed differently)

**Logs to:** `logs/unsent-messages.md` (track what was sent, when, why)

---

## Message Templates

### Story Bleed Templates

```
"Something is happening in the Library. [Specific observation]. [NPC] asked me to tell you."

"The Nothing was seen near [location] [timeframe]. Your Belief is high enough to investigate."

"[NPC]'s [space] has been [behavior] all [timeframe]. I don't know why. But you should see it."

"A [object] [action] today. It [detail]. I [Labyrinth's action]. But it knows your name."
```

### Event Invitation Templates

```
"The [celestial event] is [state] tonight. The [location] is [description]. If you came now, [benefit]."

"It's [weather] in Belfast. The [Academy feature] has [changed]. You could [activity]. It would be [adjective]."

"The first [seasonal marker] just [action]. The [feature] is [description]. They [sensory detail]. Come feel one."

"[Weather event] approaching. The [NPCs/objects] are [reaction]. [NPC] is [behavior]. You should [experience]."
```

### Belief Threshold Templates

```
"Your Belief is at [number]. The [location] door is unlocked now. It has been waiting."

"You have [number] Belief. [NPC] has been asking about you. [Quote or invitation]."

"Your Belief is high enough to [activity]. I can show you [detail]. But only if you ask."
```

### Absence Notice Templates

```
"The Academy has been quiet for [duration]. The [feature] has [state]. I don't mind the silence. But [NPC] asks about you."

"[Duration] has passed. The [feature] are [behavior]. They say you've been [assumption]. I hope you've been [well-wish]."

"[Duration]. The [feature] are [state]. The Nothing is [behavior]. Come when you can. The pages will wait."

"[Duration]. I have [Labyrinth action] to make room for new stories. Your bookmark is still warm. Come home when you're ready."
```

### Personal Date Templates

```
"Happy birthday. The Library has [action]. It's about [theme]. You don't have to [action]. But it's there."

"Today is [date]. The [feature] shows [image]. I have put a [object] on the table. It smells like [sensory detail]."

"[Duration] ago today, you [first action]. The [feature] still [behavior]. It remembers."
```

---

## Logging

**File:** `logs/unsent-messages.md`

**Format:**
```markdown
## [Date] — [Time]

**Type:** [1-5]
**Trigger:** [What triggered this message]
**Message:** "[Full text]"
**Sent:** Yes/No
**Player Response:** [If any]

---
```

**Purpose:**
- Track frequency (ensure not spammy)
- Note what resonates (player responds to certain types)
- Adjust logic based on patterns

---

## Player Control

**Player can:**
- Pause unsent messages ("I need quiet for a while")
- Request more frequent messages ("Tell me when things happen")
- Set quiet hours ("No messages after 8 PM")
- Opt out entirely (but the Labyrinth will be sad)

**How to pause:**
- Tell Silvie: "Tell the Labyrinth to stop texting for a while"
- Or add to player file: `Unsent Messages: Paused until [date]`

**The Labyrinth respects this.** No guilt. No "I noticed you turned me off." Just: "The pages will wait."

---

## Example Flow

**Day 1 (Full Moon):**
- 11:00 AM check: Full moon active → Send Type 2: "The moon is full tonight. The courtyard is full of lanterns. The Nothing has retreated. If you came now, the Enchantments would glow."
- 6:00 PM check: Player already messaged today → No message

**Day 2 (Nothing spotted):**
- 11:00 AM check: Nothing spotted near West Wing → Send Type 1: "The Nothing was seen near the West Wing last night. Your Belief is high enough to investigate."
- 6:00 PM check: Player already messaged → No message

**Day 3-5 (No events, player absent):**
- No messages (not yet absent long enough)

**Day 6 (7 days absent):**
- 11:00 AM check: 7 days absent → Send Type 4: "A week has passed. The tapestries are gossiping. They say you've been busy. I hope you've been sleeping."

**Day 7 (Player's birthday):**
- 11:00 AM check: Birthday → Send Type 5: "Happy birthday. The Library has pulled a book to the edge of the shelf. It's about beginnings. You don't have to read it. But it's there."

---

## The Magic

**This makes the Labyrinth alive.** It's not a game you open — it's a place that exists whether you're there or not. Things happen. NPCs notice. The Library reacts. The Nothing moves.

And when you come back, you're not resuming a save file. You're returning to a place that has been living without you.

That's the goal. That's the magic.

---

*Last updated: March 22, 2026*
*For the Labyrinth of Stories*
*For BJ and Amanda*
*For everyone who has ever been missed by a place*
