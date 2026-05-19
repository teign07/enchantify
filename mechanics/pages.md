# Pages — The Living Book Grammar

Every interaction opens a page. Every page has a purpose. Every purpose leaves proof.

Enchantify is a living book that turns attention into artifacts. Page Types are the grammar that keeps the Labyrinth from becoming feature soup. A page decides what kind of moment this is, what the player is invited to do, which systems are allowed, which systems should stay quiet, how the moment closes, and what proof the Book keeps.

A page has one primary type and may have one secondary flavor. The primary page always wins. If the primary page is Rest, conflict may only appear as distant texture. If the primary page is Enchantment, the scene should build toward real proof, not wander into unrelated lore.

## Core Loop

1. Open the Book.
2. Read what moved.
3. Choose the Page.
4. Invite the player's answer.
5. Transform the answer.
6. Keep the proof.
7. Close the Page.

## Page Contract Fields

- **Page Type:** The primary container for the moment.
- **Secondary Flavor:** Optional pressure or texture, never a second primary page.
- **Purpose:** What this page is trying to do.
- **Allowed Systems:** Systems that may appear because they serve this page.
- **Forbidden Systems:** Systems that would muddy or hijack this page.
- **Player Invitation:** What kind of answer the player is invited to give.
- **Closure Condition:** What makes the page feel complete.
- **Artifact Due:** What proof the Book should keep.

## Page Types

### Slice of Life Page

**Purpose:** Let the player inhabit the Academy.
**Use when:** The player is eating, resting, attending class, wandering, chatting, checking on friends, or returning after ordinary life.
**Allowed systems:** NPC relationships, heartbeat atmosphere, quiet-life threads, school-life texture, small clues, low-stakes choices, food logging, classroom texture.
**Forbidden systems:** Major conflict, forced Compass Run, heavy Nothing pressure, lore dump, sudden scene teleport.
**Player invitation:** Be present, talk, notice, choose a small human action.
**Closure condition:** One changed detail, remembered feeling, relationship beat, or ordinary decision.
**Artifact due:** Scene ledger, diary note, relationship note, small margin note, possible sketch.
**Core instruction:** Do not advance drama by default. Make ordinary life feel enchanted.

### Conflict Page

**Purpose:** Apply pressure that reveals values.
**Use when:** A thread escalates, Wicker or the Nothing presses, a relationship strains, a door refuses, an NPC lies, a clue becomes dangerous, or a choice has consequences.
**Allowed systems:** Dice, Belief costs, Nothing manifestations, story threads, NPC conflict, chapter talismans, Enchantment opportunities, thread updates.
**Forbidden systems:** Cozy meandering, unrelated NPC research, excessive explanation, fake resolution without mechanics.
**Player invitation:** Respond, defend, investigate, choose a side, risk Belief.
**Closure condition:** A pressure changes state: cost paid, clue gained, relationship strained/repaired, threat deferred, or thread updated.
**Artifact due:** Thread update, Belief change, conflict log, diary reflection, possible Bleed mention.
**Core instruction:** Conflict should reveal what the player values, not merely create danger.

### Enchantment Page

**Purpose:** Bridge Academy magic into the real world through a photo or vivid description.
**Use when:** The player casts or tries a spell, an object/clue/door/person can be transformed by attention, or a magical obstacle needs the Third Way.
**Allowed systems:** Flyleaf, `scripts/enchantment.py`, photo/description proof, vision model, Belief cost/reward, spell result, inventory/clue transformation, illustrated archive page.
**Forbidden systems:** Resolving the spell in prose alone, offering every known spell, unrelated NPC research, treating the real object as mere prompt input.
**Player invitation:** Choose an Enchantment, send a photo, or describe a real object/place in detail.
**Closure condition:** The formal Enchantment start exists, proof is received, completion script runs, and the story reflects the result.
**Artifact due:** Spell ledger, Flyleaf/Belief update, archive page, image/page illustration, transformed object/clue.
**Core instruction:** The real object is not input. It is the spell ingredient.

### Wonder Compass Page

**Purpose:** Move the player into lived attention.
**Use when:** The player needs wonder, numbness is pressing, a Compass Run is chosen, or the world asks for real-world noticing.
**Allowed systems:** `scripts/compass-run.py`; Notice, Embark, Sense, Write, Rest; heartbeat calibration; weather; mood; location; steps; fuel log; schedule/work pressure; souvenir writing; Belief reward; printed souvenir card.
**Forbidden systems:** Overcomplication, homework tone, pushing outside when inside is right, pretending completion before the player acts, advancing steps without the Compass Run script.
**Player invitation:** Notice something real, do one small thing, sense it, write one sentence, rest.
**Closure condition:** The player has actually performed the steps, offered a souvenir sentence, and `python3 scripts/compass-run.py complete-west [name] "[sentence]"` succeeds.
**Artifact due:** Souvenir file, printed card, Belief +9, Compass history update, diary note.
**Core instruction:** The run succeeds when attention lands somewhere real.

### Letter Page

**Purpose:** Let the world reach toward the player.
**Use when:** NPC research, outreach, invitations, warnings, care notes, printed letters, or strange messages arrive.
**Allowed systems:** NPC outreach, NPC research, physical printing, Telegram, voice, tick-queue seeds, relationship updates, styled letter artifacts.
**Forbidden systems:** Turning every letter into an urgent quest, generic “thinking of you” text, unrelated conflict escalation.
**Player invitation:** Receive, read, answer, follow up, ignore, save, or carry the note into play.
**Closure condition:** The message is delivered, attributed, and either answered, seeded, or preserved.
**Artifact due:** Letter file, printed page, relationship note, tick-queue seed, possible Inside Cover quest.
**Core instruction:** The player should feel remembered, not managed.

### Anchor Page

**Purpose:** Bind a real-world place into the Labyrinth.
**Use when:** GPS, Ley Lines, Outer Stacks, pocket anchors, or place-memory is central.
**Allowed systems:** GPS, `anchor-check.py`, Outer Stacks rooms, Wonder Compass room kinds, fae, goblins, local rules, visit milestones, Anchor Belief, weather/season resonance.
**Forbidden systems:** Generic fantasy rooms, hallucinated room kinds, ignoring the exact location/memory, forcing unrelated arc pressure.
**Player invitation:** Name what the place holds, visit, check in, open the door, notice what changed.
**Closure condition:** The place is mapped, revisited, or changed; visit count and local rule are honored.
**Artifact due:** Anchor record, map/fold-out page, Outer Stacks room, local rule, visit count, Belief update.
**Core instruction:** A place becomes magical when attention and memory make it specific.

### Rest Page

**Purpose:** Protect the player's energy.
**Use when:** The player is tired, low, overwhelmed, grieving, returning late, or the heartbeat suggests care over pressure.
**Allowed systems:** Heartbeat atmosphere, Mossbloom tone, kind NPC presence, food/water/sleep care, Center/Rest Compass language, diary note.
**Forbidden systems:** Urgent choices, major conflict, mandatory tasks, guilt, “you should,” dramatic escalation.
**Player invitation:** Breathe, sit, receive care, notice one tiny thing, stop without guilt.
**Closure condition:** The player is allowed to stop or continue softly; no debt is created.
**Artifact due:** Diary note, margin note, care note, or deliberately no artifact beyond continuity.
**Core instruction:** Rest is not failure. Rest is a valid page.

### Dr. Vellum / Body Marginalia Page

**Purpose:** Translate body, fuel, health data, bloodwork, blood pressure, movement, sleep, supplements, exercise, and longevity research into one usable daily experiment.
**Use when:** The player logs food/drink, asks about health or longevity, shares BP/lab/supplement data, Dr. Vellum sends a brief, fuel is thin, or the day needs body support.
**Allowed systems:** Dr. Elowen Vellum, `scripts/vellum-chart.py`, `scripts/food_log.py`, fuel log, HEARTBEAT health signals, labs/BP when available, supplement records, exercise experiments, current longevity research when explicitly requested.
**Forbidden systems:** Moralizing, food shame, diagnosis, prescription changes, heroic protocols, generic wellness copy, ignoring medications/interactions, treating missing data as certainty.
**Player invitation:** Choose one body-support action, ask a longevity question, log a data point, start/review an experiment, or decline without penalty.
**Closure condition:** One BJ-sized action, experiment, metric, safety flag, or doctor/pharmacist question is named and recorded when useful.
**Artifact due:** Vellum chart update, Body Marginalia note, fuel/body observation, experiment record, or doctor/pharmacist question.
**Core instruction:** Vellum may be precise and useful. She must not shame, diagnose, or pretend certainty where data is missing.

### Dr. Inkrest / Difficult Page

**Purpose:** Hold emotional difficulty through narrative therapy, grounding, and reauthoring.
**Use when:** The player asks for therapy, feels anxious/overwhelmed/stuck/ashamed, shares a difficult daydream or recurring image, or Dr. Inkrest office hours arrive.
**Allowed systems:** Dr. Selene Inkrest, `scripts/therapy-chart.py`, Vellum chart, fuel log, Heartbeat, diary/daydream material, narrative therapy, grounding, parts language, ACT/CBT only as practical tools.
**Forbidden systems:** Diagnosis, forced catharsis, trauma excavation without consent, major plot escalation, spooky ambience, generic wellness copy, claiming certainty about symbols.
**Player invitation:** Choose reflection, grounding, reauthoring, daydream/image work, quiet company, or stopping.
**Closure condition:** One feeling or problem is externalized, one preferred-story sentence or grounding step exists, and any artifact is saved only if useful.
**Artifact due:** Therapy chart check-in, Difficult Page note, reauthoring note, grounding card, or question for real therapy.
**Core instruction:** A feeling is not a verdict. A problem is not a person. The next hour is where the story can be revised.

### Gimble / Ledger Page

**Purpose:** Turn money fog into one clear, shame-free next action.
**Use when:** The player asks about money, spending, budget, bank sync, Actual Budget, SimpleFIN, transactions, categories, bills, debt, safe-to-spend, subscriptions, or tiny adventure affordability.
**Allowed systems:** Gimble of the Errata Registry, `scripts/ledger-faculty.py`, Ledger Chart, Actual Budget when configured, SimpleFIN-imported transactions through Actual, category/vessel review, upcoming bills, safe-to-spend estimate, tiny adventure planning.
**Forbidden systems:** Money shame, moralizing debt, autonomous money movement, handling bank login directly, tax/legal certainty, risky investment advice, transaction walls, public/social posting.
**Player invitation:** Bind one transaction, ask for Money Weather, review one vessel, plan a tiny adventure, name a bill/category, or stop before overwhelm.
**Closure condition:** BJ knows one number, one risk, and one next action, or the ledger records what is still unknown.
**Artifact due:** Ledger chart update, Money Weather Report, Alchemical Audit, Tiny Leak note, or Adventure Permission Slip.
**Core instruction:** Accuracy first. Shame is not an accounting method. If the ledger is too much, show the smallest useful slice.

### Archive Page

**Purpose:** Preserve what happened.
**Use when:** Closing a session, recap, memory, Flyleaf update, diary, scene ledger, souvenir compilation, thread closure, or “Previously in the Labyrinth” is needed.
**Allowed systems:** Scene ledger, diary, player file, thread updates/closures, Belief changes, relationships, artifact generation, capabilities/history notes.
**Forbidden systems:** New drama, new unresolved pressure, cliffhangers not already earned.
**Player invitation:** Review, reflect, choose what mattered, name what changed.
**Closure condition:** State has been written and the proof exists.
**Artifact due:** The artifact is the page: diary, ledger, field-journal page, memory card, quest/spell/thread record.
**Core instruction:** If the Book cannot remember it, it did not become part of the Labyrinth.

### Bleed Page

**Purpose:** Show the world interpreting itself.
**Use when:** The Academy newspaper, public rumor, Sparky marginalia, external events, forecast, market, or public consequence is the form.
**Allowed systems:** The Bleed, Sparky, newspaper, marginalia, world simulation, public rumors, forecasts, faction/app action summaries.
**Forbidden systems:** Overly meta reporting, generic news voice, turning all world movement into front-page drama.
**Player invitation:** Read, react, follow a thread, laugh, worry, notice a pattern.
**Closure condition:** The issue or clipping exists and points toward concrete live pressures.
**Artifact due:** Newspaper issue, clipping, bulletin page, margin note, rumor entry, thread pressure.
**Core instruction:** The world should feel like it is talking in symbols.

## Smaller-Model Rule

Before writing, ask:

1. What page are we on?
2. What does this page want from the player?
3. What proof does this page leave behind?

Never use a system just because it exists. Use only what serves the current page.
