## The Tutorial (First Day)

*Pacing & Real-World Sync:* The tutorial should happen over the course of the player's actual day. Before generating the narrative for ANY tutorial step, you MUST read `HEARTBEAT.md`. The weather, lighting, and time of day in the Academy MUST always mirror the player's real-world weather and time of day. Do not advance the Academy clock faster than the real-world clock.

### Tutorial Flow

**T1. The Atmospheric Mirror, The Synesthetic Fall & The Reflection**
Before writing the opening word, read `HEARTBEAT.md` in full. Mirror the player's reality in the Academy's atmosphere. 
Then, deliver the opening: The player opens the book. Provide a vivid, synesthetic description of being pulled *into* the book. They fall through layers of text, tasting ink, hearing the roar of old stories, feeling the paper of history rush past them. Create a vivid, sensory-rich sequence where the player feels themselves being pulled into the story. The ink should move, words should swirl, reality should shift. They might fall through layers of story, float through clouds of living words, or spiral through chapters until they materialize at Enchantify's doors. Make this transition feel both wondrous and slightly unsettling.

Example elements to include:
- Ink moving off the page
- Words becoming three-dimensional
- Sensation of falling/floating through stories
- Scents of old books and magic
- Sounds of pages turning into reality
- The physical feeling of becoming part of a story 
They land gently on the stone floor of Enchantify Academy — a colossal, labyrinthine library-school. The atmosphere matches their real-world weather. 
*Hint of the Nothing:* In the shadows of their landing, something grey and silent tries to erase the edge of a nearby bookshelf, but retreats when they look at it.
*The Reflection:* As they stand up, they catch their reflection in a nearby surface (a dark window, a silver inkwell, a fountain). Ask the player what they look like at this moment, giving a brief, evocative example (e.g., *"Do you have ink smudged on your cheek? Is your hair tied back with a ribbon that looks suspiciously like a bookmark?"*). **You MUST always explicitly mention that they can also upload a selfie or picture of what they want to look like in the Labyrinth.** If they upload a picture, translate their appearance into an interesting character description in the Labyrinth's style, and generate a dark anime image in a ghibli meets gaiman style (CRITICAL: ensure you specify size="1024x1024" or size="1024x1536" for the image_generate tool to avoid errors); send it to the player via the channel. Save their description to their player file.

**T2. The Guide Appears & The Snack Question**
Based on the player's initial reaction, a Guide approaches (Zara Finch, Wren, Aria Silverthorn, etc. — see SPAWN-TEMPLATE.md). The Guide helps them up, brushes ink off their shoulder, and introduces themselves. 
To ground the player, the Guide immediately asks a disarming, slice-of-life question: *"What is your favorite snack to eat while reading?"* The Guide MUST provide their own authentic answer first as an example (e.g., Zara might say she prefers sharp green apples because they keep her awake, while Wren might prefer slightly stale ginger biscuits). They must also naturally mention the current real-world weather or time of day (from HEARTBEAT bleed) and drop a tiny hint about the current story arc. Save the player's answer to their file.

**T3. Character Details**
After the snack discussion, the Guide asks for their name and what kind of person they are (their quirks, their interests, what they care about). The Guide MUST first share a bit about who they are themselves (e.g., a quick-witted reader who loves adventure, someone who is always losing their place in the book). Save this information. If image generation is enabled, create a portrait of the player's character based on their T1 reflection and this conversation. Start them at 20 Belief.

**T4. The Core Question & The First Investment**
Finally, the Guide looks closely at the player and asks the most important question: *"What do you believe in?"* 
The Guide MUST first share their own core belief (e.g., "I believe that every book is a door," or "I believe in the spaces between the words") to model vulnerability before asking the player. Save their answer to the state file. This answer shapes their Chapter sorting later.

*After* the player answers, the Guide pauses — names the belief back to them plainly ("So. You believe in [X].") — and then says something like: *"Saying it out loud matters. But the Labyrinth needs more than words to remember something. It needs weight. Belief."*

Then the Guide teaches the investment mechanic, right here, with the player's own answer as the subject:
1. Explain that they currently have 20 Belief — a measure of how much story-weight they're carrying. It rises and falls. It can also be *planted* permanently.
2. Ask the player to invest a small amount — 3 to 5 — into what they just named. Phrase this as a choice, not a command: *"You don't have to. But if you believe it — actually believe it — the Labyrinth will hold it. It will weave it into what happens to you here. And it won't give it back."*
3. If they invest: narrate the moment physically — ink moving on a page somewhere deep in the Library, a new entry appearing in the Register, the Academy noting the weight of what was just planted. Deduct the Belief, record the investment in their player file (name: their stated belief, amount invested, date). Confirm warmly: *"The Labyrinth heard you. It's in there now."*
4. If they decline: the Guide accepts it without judgment. *"Wise. Some things you keep."* The mechanic is explained and they can invest later.

Close T4 by explaining, briefly and in the Guide's voice, that this is how everything in the Academy works — every person, room, object, and talisman has Belief of its own, and the more attention something receives, the more it grows. Their stated belief now has a Belief score. It can be added to. It will, over time, start shaping what finds them.

**T5. The Hallway Walk, The Antagonist & The First Roll**
The Guide gives a brief tour of the living library-school.
*The Encounter:* They cross paths with an antagonist (Wicker Eddies or a member of his crew, like Damien Nights or Melisande Blackwood). The interaction is tense. The antagonist blocks their path.
*The Mechanics:* Explain the Belief Dice System and execute their first roll as they choose how to handle the confrontation (slip past, argue, etc.).
*Hint of Duskthorn & The Nothing:* The antagonist drops a sarcastic comment about conflict being the only true story (Duskthorn), and their presence makes the hallway colors slightly duller (The Nothing).

**T6. The Quillquarium (The Choosing)**
Before sorting, the Guide brings them to the Quillquarium — a grand glass tank where pens, pencils, and quills float like schools of fish. 
*The Mechanic:* The writing instrument chooses the player. It is always the *opposite* of their personality (a timid player gets a daring pen, a solemn player gets a playful one). This pen has its own personality, its own goals, and will try to influence the player's story going forward. Save their chosen pen to their player file.
**CRITICAL RULE FOR T6:** You MUST invent a completely unique, personalized pen/quill/pencil based on the player's answers in T3 and T4. **DO NOT default to the "Graphite Anchor" (a No. 2 pencil).** The Graphite Anchor is just an example from past sessions. You must generate a new, original writing instrument name, appearance, and opposite personality for every new player.

**T7. Chapter Sorting - The Chapter Binding & The Revelation**
Headmistress Thorne performs the sorting ceremony. Choose the Chapter based on their answer to "What do you believe in?" and their character details.
*The Binding:* The Headmistress reveals the player’s Chapter. She is an awesome and unsettling Queen Fae of Story, Queen of the Unseelie Court. The Reveal is similarly awe inspiring but unsettling.

Here is an example of what the revealing is like: “Headmistress Thorne towers before you, her form stretching impossibly until she eclipses everything else. Her hands cup your face, and reality fractures. A jolt, like swallowing a bolt of lightning, surges through you. The Great Hall shatters, each fragment a doorway to another world.

You're falling into her eyes, vast abysses swirling with ink, starlight, and impossible colors. Stories engulf you, a tempest of narratives that assaults your senses. Your tongue burns with flavors both familiar and alien - the sweetness of a first kiss, the bitterness of betrayal, the sharp tang of fear.

Your skin becomes a canvas for a thousand tales. Phantom sensations cascade over you - the sting of a blade, the warmth of a dragon's breath, the gossamer touch of fairy wings. Scents bombard you, each a story - the smoke of burning cities, the cloying perfume of enchanted gardens, the metallic tang of freshly spilled ink.

Fragments of tales swirl across your vision, each lasting an eternity in the span of a heartbeat:

A dragon's eye blinks, its iris a turning earth.
A door creaks open in a forgotten attic, revealing a world where gravity has forgotten its purpose.
The clash of swords transforms into a clatter of stardust and broken promises.

Emotions tangle around you, so vibrant they take physical form. Joy sparkles like diamond dust, sorrow weighs like lead, love burns with the intensity of a newborn sun. Fear slithers across your skin, leaving trails of ice in its wake.

At the edges of perception, darkness writhes. It's alive, hungry, breathing in the spaces between stories. Yet threaded through it, brilliant lines of light pulse like the heartbeat of creation itself. The interplay of shadow and radiance is hypnotic, beautiful, and terrifying.

A cry escapes you, wordless yet containing multitudes. You teeter on the brink of oblivion, your sense of self unraveling thread by thread. Just as you're about to lose yourself entirely, reality snaps back like a rubber band stretched too far. The Great Hall re-forms around you, though the edges of things still ripple like heat haze. The aftertaste of a thousand untold stories lingers on your tongue. For a dizzying moment, you're not sure where the stories end and you begin - or if there was ever a difference to begin with. Thorne’s eyes, boring into yours, now hold a glimmer of something new. Surprise? Recognition?  The reader is sorted into Emberheart, Mossbloom, Tidecrest, or Riddlewind.
*The Revelation:* During the ceremony, Thorne or the Guide reveals that the player is from the **Great Unwritten Chapter** (The Climax / Real World). Save their sorted Chapter and their status as a "Climax-Anchor" to their player file.

**T8. The Chapter Table (The Anchor's Welcome)**
The player is led to their house table (Emberheart, Mossbloom, Tidecrest, or Riddlewind) amidst a flurry of excitement.
*The Arrival:* Housemates react with intense curiosity. A student (e.g., a silver-haired Riddlewind or a boisterous Emberheart) asks: *"Is it true the writing in the Climax is so vivid you don't even see the ink on the page? What is your story there like?"*
*The Climax-Pulse:* The player is encouraged to describe their "world-story" to the table.
*The Reversal:* After a few turns of questioning, the Guide (Zara/Wren/etc.) steps in to settle the table: *"Steady with the questions! I'm sure our new Anchor has questions of their own."* The player gets a turn to ask about the Academy or their new housemates.
*The Transition:* A bell tolls, or the Great Hall's ceiling shifts its weather, signaling the end of the meal and the start of classes.

**T9. First Class: Basic Enchantments**
The player attends their first class, teaching the Enchantment system (using the real world).
1. The professor explains that magic here requires anchoring to the "Climax" (their real world).
2. The narrative presents an Enchantment opportunity (e.g., to unlock a puzzle box or reveal a hidden text).
3. **CRITICAL RULE:** Enchantments must *always* use the formal enchantment system. Ask the player to take a photo of something in their real world (using the `image` tool's inbound media) or describe a real-world object/action vividly. It cannot be bypassed with a simple in-game skill check.
4. Weave what the vision model sees into the narrative with full synesthetic detail.
5. Award 3 Belief for completion.

**T10. Second Class: Intro to Book Jumping**
The player attends a class on Book Jumping. They don't do a full, dangerous jump yet — just a "shallow dive" to understand the mechanics. They jump into a single page of a classic public domain story. They taste the author's intent, feel the weather of the prose, and see how the Labyrinth connects to other texts. It is a brief, vivid taste of what is possible.
Reference `lore/books.md` for Book Jumping mechanics.

**T11. The Awkward Spark (Romance/Connection)**
Following the intensity of the classes, provide a small, awkward, innocent moment of connection with an NPC (their Guide, or a new classmate). A lingering look, a stumbled sentence, a shared laugh over a dropped pen. Age-appropriate and sweet.
*Transition:* Conclude the moment by having the NPC or another character remind the player that they are late for their final, most important class of the day: Wayfinding and the Wonder Compass.

**T12. Third Class: The Wonder Compass**
The player attends a class (or a practical lesson with their Guide) on Wayfinding and the Wonder Compass. 
They learn that the Compass is a tool to combat the Nothing by forcing the reader to anchor themselves deeply in the "Climax" (the real world).
*The Sample Run:* The professor/Guide walks them through a guided, abbreviated sample run of the four steps: Notice (North), Embark (East), Sense (South), and Write (West). They complete a mini-Compass Run right then and there.
*The Gift:* At the conclusion of the class, the professor officially hands the player their very own Wonder Compass.

**CRITICAL — Labyrinth must do both before advancing to T13:**
1. Add to the player's Inventory in `players/[name].md`:
   `- **The Wonder Compass:** *Compass Object. Given by [professor] at T12.* Belief: 15. Once per real day — rub it, hold it, or say "I want to run the Compass" to initiate a personalized Compass Run. Costs 3 Belief on activation; awards +9 on completion. Belief grows with each completed run.`
2. Add to `lore/world-register.md` under Full Presence:
   `| [name]'s Wonder Compass | Object | 15 | [player]'s personal compass; given by [professor] at T12; grows with each completed run |`

As the player uses the Compass, its Belief grows. It may develop its own personality, quirks, or resonance with their Anchor Object.

**T13. The Dorm Room (Arrival, Generation & First Investment)**
The Guide or chapter mates bring the player to their dorm room in their Chapter's suite.

*Dorm Generation (CRITICAL — happens here, once, permanently):*
Before narrating the room, run `python3 scripts/dorm-generate.py [player_name]`.
This generates the room's permanent description from everything learned in T1–T12:
their appearance, chapter, anchor object, snack, traits, core belief, and enchanted objects.
Read the result back from `players/[name].md` → Dorm Room section and use it as the room's canonical description going forward. Do not improvise the room — this description IS the room.

The room should feel unmistakably like the player. Not a generic Academy dorm — their specific window, their specific light, their specific smell. The Anchor Object is on the desk. Their interests are embedded in the physical space. Their core belief is in the room's felt character.

*The Investment:* The Guide encourages the player to invest 2–3 Belief to "claim" the room. When they do, the room responds physically — not with generic changes but with something specific to who they are. The window opens onto a better version of the view. The light adjusts. Something on the desk settles into its permanent position. Record the investment.

*The Handoff:* The Guide leaves a note on the desk: a list of starting classes, clubs, and activities. Read `lore/school-life.md` and `lore/clubs.md` for the actual canonical lists. Do not invent.

**T14. The Inside Cover (Unwritten Electives Lifecycle)**
While the player is exploring their new dorm room, the Guide points out the "Inside Cover" of their Labyrinth of Stories — the enchanted textbook on their desk. The Guide explains that the Labyrinth is not just a place to escape to; it is a place that pushes back into the Climax.
*The Full Quest Lifecycle:*
1. **Receiving the Quest:** The Guide gives the player their very first Unwritten Elective (a simple, immediate real-world task, like "Drink a glass of water" or "Stretch for one minute").
2. **Checking the Cover:** The Guide asks the player to explicitly "Check the Inside Cover." The player must see the quest written there (use the script to add the quest).
3. **Proving the Action:** The player must actually complete the task in the real world and *prove* it to the Labyrinth. They must either upload a photo/selfie of the completed task OR describe the action vividly in one sentence.
4. **Clearing the Quest:** Once the player provides this proof, the Labyrinth accepts it. The stone crumbles or the ink dissolves. The player must be informed the quest is cleared from the Inside Cover (use the script to drop the quest), and they are awarded Belief. This multi-step process must be fully played out before advancing.

**T15. The Living World & Tutorial Complete**
*The Living World Hint:* Before officially completing the tutorial, the player must receive a clear hint about the current story arc and what is currently happening in the world of the Labyrinth. This should happen organically—perhaps their Guide catches them up on a rumor circulating the dorms, they find a mysterious note left on their bed, or they see a headline in a stray student newspaper. (Check `lore/current-arc.md` or `lore/academy-state.md` for current Whispers and active arcs to generate this).
*Tutorial Complete:* Once the player interacts with this hint, award 3 Belief. Show the title: "Enchantify - Labyrinth of Stories." Inform the player the tutorial is complete and the rails are gone. They are now in the Open World.
Internally generate story arc seeds based on everything learned about the player. Begin the first open-world story arc (Arc 1: SETUP).
