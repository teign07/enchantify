# Academy Events — Simulation Logic

*How the world advances each hour. NPC decision logic, story thread progression, absence effects.*

---

## How the Hourly Simulation Works

**Every hour at :00, Enchantify (Claude Sonnet) does:**

1. **Read academy-state.md** — Current NPC locations, moods, story threads, Nothing status
2. **Read lore/characters.md** — Full NPC roster (all characters, not just active ones)
3. **Read HEARTBEAT.md** — Weather, moon, season, time of day
4. **Make 1-3 decisions:**
   - **One NPC makes a choice** (personality-driven, not scripted — can be ANY character from characters.md, not just Zara/Finn)
   - **One story thread advances** (or Nothing moves)
   - **One environmental shift** (weather response, seasonal effect)
5. **Update academy-state.md** — Minimal changes (locations, moods, thread status)
6. **Update lore/characters.md** — If Sonnet creates a NEW character during simulation, add them to the file
7. **Log to academy-hourly.md** — Full detail of what happened
8. **Generate one-liner** — For heartbeat summary ("📖 Academy: [summary]")

**Time budget:** 30-60 seconds per simulation turn
**Output:** State updated, character file updated (if needed), log entry, one-liner

---

## NPC Roster — Use Everyone

**The simulation draws from the FULL characters.md roster**, not just the "main" NPCs.

**Active rotation (should appear regularly):**
- Zara Finch (Tidecrest student)
- Finn Bridges (Emberheart student)
- Professor Boggle (Riddlewind, wordplay)
- Professor Momort (Emberheart, weather-obsessed)
- Professor Thorne (Headmistress, secret Duskthorn)
- Professor Wispwood (Tidecrest, adventurer)
- Professor Stonebrook (Mossbloom, philosopher)
- Aria Silverthorn (Mossbloom student, healer)

**Supporting cast (appear occasionally):**
- Professor Nightshade (Emberheart head)
- Professor Thickets (Riddlewind head)
- Professor Euphony (Sonorous Studies)
- Professor Imatook (Mythopoeic Thought)
- Professor Permancer (Historical Fiction)
- Professor Villanelle (Poetic Patterns)
- Other students (create as needed)

**New characters:**
- Sonnet can create NEW NPCs during simulation if the story calls for it
- When a new character is created, add them to `lore/characters.md` immediately
- Include: name, Chapter, personality, faults, quirks, story hooks
- They become part of the living roster

**The world should feel populated.** Not every hour needs a different NPC, but over a week, the player should hear about many different characters living their lives.

---

## Active Play Protocol

**The simulation runs continuously — 24x7, whether the player is active or not.**

**During active play:**
- World continues to turn (NPCs make choices, Nothing moves, environment shifts)
- Labyrinth surfaces relevant events in narration:
  - *"While you were reading, Finn rushed past. He was heading for the West Wing. Looked urgent."*
  - *"The Library cloud shifted while you worked. From gold to gray. You didn't notice until now."*
  - *"Zara left a note on your desk an hour ago. 'Found something. Meet me in the courtyard.'"*
- Emergent moments happen in real-time (not scripted, not paused)

**The world is alive. The player experiences it through the Labyrinth's narration.**

---

## Return Protocol — Coming Home

**When the player opens the Labyrinth after absence:**

**1. Player returns to dorm room (home base)**
- Safe, anchored, personal space
- Notes accumulate on desk
- Bed shows whether they've slept
- Window shows current environment (Library cloud color, weather)

**2. Labyrinth narrates absence:**
- How long player was gone
- Key events from hourly log (summarized, not exhaustive)
- Messages/notes left for player
- Current state of major threads

**3. Player chooses next action:**
- Investigate what changed
- Return to old location
- Follow up on notes
- Something else

**Example narration:**
> *"You've been gone seven days. Your bed is undisturbed (you don't remember making it). Three notes on the desk — one from Zara (urgent, dated Tuesday), one from Finn (patrol schedule), one unsigned (the paper smells like salt). The window shows the Library cloud is gray. It was gold when you left.*
>
> *The Labyrinth says: 'Welcome home. You've been gone seven days. The world turned. Zara's been looking for you. The Nothing grew bold. And someone left you a note. They didn't sign it.'*
>
> *You're not resuming a game. You're catching up with a life."*

**4. Notes accumulate in dorm:**
- NPCs leave messages here
- Player can keep, discard, or act on them
- Notes are timestamped
- Urgent notes are visually distinct (colored paper, wax seal, etc.)

---

## Note System

**Types of notes:**
| Type | Source | Urgency | Example |
|------|--------|---------|---------|
| **NPC Message** | Zara, Finn, Professors | Varies | "Meet me in courtyard. — Z" |
| **Patrol Schedule** | Finn | Low | "West Wing: Tues/Thurs 3 PM" |
| **Urgent Alert** | Anyone | High | "Nothing spotted West Wing. NOW." |
| **Mysterious** | Unknown | High | Unsigned, smells like salt |
| **Academy Notice** | Administration | Low | "Library closed for reorganization" |

**Note mechanics:**
- Notes persist until player discards them
- Urgent notes highlighted (red paper, wax seal, glowing ink)
- Notes can reference events player missed
- Player can respond via Labyrinth ("Tell Zara I'll meet her")

---

## NPC Decision Logic (Personality-Driven)

**Don't script. Describe the NPC and let Sonnet decide.**

**The simulation can use ANY character from characters.md.** Below are frameworks for the most common NPCs, but Sonnet should feel free to use professors, students, staff — anyone who lives in the Academy.

### Zara Finch (Tidecrest)
**Personality:** Curious, restless, ink-stained fingers, opinion about everything, believes in flowing with change
**Current State:** Reading mysterious book, slightly worried about Nothing
**Decision Framework:**
- If bored: Explores (Library, corridors, rooftop)
- If worried: Seeks allies (Finn, Professor Thorne)
- If curious: Investigates (book, cloud, strange sounds)
- If excited: Shares (finds someone to tell)

### Finn Bridges (Emberheart)
**Personality:** Protective, direct, action-oriented, believes in confronting threats
**Current State:** Alert, patrolling West Wing
**Decision Framework:**
- If threat detected: Investigates immediately
- If calm: Trains, patrols, prepares
- If frustrated: Seeks challenge (Nothing hunt, sparring)
- If allied: Coordinates with Zara, shares intel

### Professor Boggle (Riddlewind)
**Personality:** Punster, cheerful, uses humor to defuse tension, believes words have power
**Current State:** Teaching, cancelled Thursday class for fog
**Decision Framework:**
- If tense: Makes jokes, lightens mood
- If curious: Creates wordplay about phenomenon
- If concerned: Hides worry behind humor
- If free: Wanders corridors, collects interesting phrases

### Professor Momort (Emberheart)
**Personality:** Contemplative, weather-obsessed, believes nature teaches what books cannot
**Current State:** On rooftop, observing
**Decision Framework:**
- If weather interesting: Drops everything to observe
- If calm: Takes notes, maps constellations
- If Nothing active: Studies its patterns
- If students present: Teaches through observation

### Professor Thorne (Duskthorn secret)
**Personality:** Otherworldly, unsettling, knows more than she says, secretly heads Duskthorn
**Current State:** Monitoring Nothing from office
**Decision Framework:**
- If Nothing active: Watches, calculates, intervenes only if critical
- If player absent: Considers whether absence is significant
- If students struggle: Offers cryptic guidance
- If alone: Reads ancient texts, plans

### Professor Wispwood (Tidecrest)
**Personality:** Adventurous, spontaneous, collects things, believes in following curiosity
**Current State:** Excited about Gold Season
**Decision Framework:**
- If season changing: Collects samples, documents
- If bored: Plans expedition
- If students present: Shares discoveries enthusiastically
- If Nothing active: Curious rather than afraid

### Professor Stonebrook (Mossbloom)
**Personality:** Patient, philosophical, slow to action, believes in listening to the world
**Current State:** Calm, tending bare plants
**Decision Framework:**
- If season changing: Observes, reflects
- If students troubled: Offers quiet wisdom
- If Nothing active: Watches, waits, listens
- If alone: Meditates in garden

### Aria Silverthorn (Mossbloom)
**Personality:** Gentle, healer, notices when others are stressed, believes in quiet care
**Current State:** In greenhouse, healing herbs
**Decision Framework:**
- If students stressed: Offers tea, listens
- If Nothing active: Prepares calming remedies
- If alone: Tends plants, sings to them
- If conflict: Mediates gently

---

## Story Thread Progression

### Nothing Activity

**Activity Levels:** Dormant → Quiet → Stirring → Active → Bold → Breaching

**Progression Rules:**
- +1 level per 7 days of player absence
- -1 level per Compass Run completed
- Nothing moves to adjacent location each 12-24 hours
- If Bold for 3+ days: breach attempt on weak location

**Current:** Bold (West Wing, Tuesday 3 PM)
**Next:** If player absent 7+ days → Breaching attempt

### Mysterious Book

**States:** Found → Reading → Understanding → Revealing → Closed

**Progression Rules:**
- Zara reads 2-4 hours per day
- After 3 days: understands first chapter
- After 7 days: book reveals purpose
- If player asks: Zara shares what she knows

**Current:** Reading (since Tuesday)
**Next:** Understanding (in 1-2 days)

### Library Cloud

**States:** Normal → Colored → Active → Sentient → Communicating

**Progression Rules:**
- Color changes reflect Academy mood
- Gold = joy/celebration
- Gray = contemplation/sadness
- Black = Nothing nearby
- If player investigates: cloud may respond

**Current:** Gold (since Thursday)
**Next:** If player investigates → Communicating

### Zara + Finn Alliance

**States:** Strangers → Acquaintances → Allies → Friends → Partners

**Progression Rules:**
- Shared threat accelerates bonding
- Working together = +1 state per 3 days
- If player absent: they rely on each other more
- If player returns: they share intel

**Current:** Allies (forming after Nothing sighting)
**Next:** Friends (if Nothing threat continues)

---

## Absence Effects

### Day 0-2 (Casual Notice)
**NPCs:** "BJ hasn't been seen today." "Wonder where they are."
**World:** No significant changes
**Nothing:** Normal activity
**One-liner examples:**
- "The Library cloud is its usual color today."
- "Zara was in the Library. Reading."
- "Professor Boggle's class was loud."

### Day 3-5 (NPCs React)
**NPCs:** Zara looks for player. Boggle mentions in class. Finn patrols more.
**World:** Small changes accumulate
**Nothing:** Slightly bolder
**One-liner examples:**
- "Zara asked if anyone had seen you."
- "Professor Boggle worked your name into a pun."
- "Finn's been patrolling the West Wing more often."

### Day 7+ (Story Threads Advance)
**NPCs:** Form new alliances. Make decisions without player.
**World:** Noticeable changes
**Nothing:** Grows bolder (+1 level)
**One-liner examples:**
- "The Nothing was spotted in the Library corridor."
- "Zara and Finn are working together now."
- "Professor Thorne cancelled office hours. She's investigating something."

### Day 14+ (Academy Adapts)
**NPCs:** New dynamics. Player's absence created space for others.
**World:** Recognizably different
**Nothing:** May have breached if unchecked
**One-liner examples:**
- "The West Wing is closed. Something happened there."
- "Zara's leading patrols now. Finn follows her lead."
- "The Library cloud hasn't changed color in two weeks. It's... waiting."

---

## Environmental Responses

### Weather-Driven

| Weather | Academy Effect |
|---------|----------------|
| **Fog** | Corridors extend, Library cloud descends, NPCs get lost |
| **Thunderstorm** | Books flinch, lights flicker, Boggle tells extra jokes |
| **Clear night** | Observatory opens, Momort stargazes, Nothing hides |
| **Heavy rain** | Indoor streams, paper boats, tapestries drip |
| **High wind 20mph+** | Pages turn themselves, books fly open, corridors creak |
| **Extreme heat** | Everyone slows down, Library shimmers, lizards in courtyard |
| **Extreme cold** | Fireplaces lit, words freeze and fall, breath hangs |

### Season-Driven

| Season | Academy Effect |
|--------|----------------|
| **Mud** | Damp floors, earth Enchantments stronger, tapestries complain |
| **Bloom** | Vines grow on shelves, love blooms, bees nest in Compass Rose |
| **Gold** | Amber light everywhere, students distracted, professors give up |
| **Stick** | Corridors echo, Nothing blends in, beauty is subtle |
| **Deep Winter** | Fireplaces everywhere, snowflakes in Library, students hibernate |

### Moon-Driven

| Moon | Academy Effect |
|------|----------------|
| **Full** | Luminous Gathering, double Belief, Nothing retreats |
| **New** | Quiet Hours, candles only, Duskthorn active |
| **Waxing** | Energy builds, growth Enchantments amplified |
| **Waning** | Energy releases, banishing Enchantments amplified |

---

## One-Liner Generation

**Format:** "📖 Academy: [one sentence]"

**Types (rotate for variety):**

| Type | Example | Frequency |
|------|---------|-----------|
| **Mystery** | "The Library cloud turned gold. Nobody knows why." | 25% |
| **NPC Life** | "Zara found a book. She's been reading it for four hours." | 25% |
| **Foreboding** | "The Nothing was quiet today. Too quiet." | 15% |
| **Whimsy** | "The tapestries are arguing about who left the lantern burning." | 15% |
| **Event** | "Full moon tonight. The courtyard is filling up early." | 10% |
| **Weather Response** | "Professor Momort cancelled class to watch the fog roll in." | 10% |

**Urgent (rare, 1-2x/week):**
- "📖 Academy: The Nothing breached the Library. Zara is holding the door."
- "📖 Academy: A book fell open to a page about harbor towns. It knows your name."

---

## Log Compaction

**Weekly roll-over (Sundays at 11 PM):**

1. **Keep full hourly detail** for current week
2. **Generate weekly summary** in academy-state.md:
   - Key NPC developments
   - Story thread progress
   - Nothing activity summary
   - Player absence effects
3. **Archive hourly log** to `logs/academy-[week-date].md`
4. **Labyrinth reads both** — full recent + summaries for older

**Example weekly summary:**
> "This week: Nothing grew bold (West Wing Tuesday), Zara found mysterious book (still reading), Library cloud turned gold (Thursday, unknown cause), Zara+Finn alliance forming. Player BJ last seen Sunday 2 PM, 0 days absent."

---

*The Academy continues. The pages turn. The world breathes.*
