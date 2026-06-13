# InsideCover / ReEnchanted - Project Overview

InsideCover is the iOS/iPadOS app for **ReEnchanted**, the living-book surface
inside the broader Enchantify project. The app turns ordinary daily material -
kept notes, moods, weather, body/fuel logs, photos, locations, choices,
character letters, and generated story fragments - into a private illustrated
book that remembers and returns.

The product thesis is simple:

> Do not keep adding isolated page types. Make the Book a better reader.

The app is not a generic journal, chatbot, habit tracker, or game UI. It is a
storybook interface for attention. The reader keeps pages that matter; those
kept pages become durable memory; the Book later notices patterns, absences,
durations, relationships, recurring Beliefs, and seasonal shape.

## Project Facts

- Bundle ID: `com.openclaw.enchantify.insidecover`
- Xcode project: `EnchantifyInsideCover.xcodeproj`
- App target: `InsideCoverApp`
- Shared SwiftPM package: `InsideCoverCore`
- Supported runtime target: iOS 17+
- Shared-core test target: `Tests/InsideCoverCoreTests`
- Current verified shared suite: 176 tests
- Widget status: removed from this project. The old widget source has been
  moved out to `../DetachedInsideCoverWidget/` and is intentionally not part of
  the app target.

## Repository Layout

```text
InsideCover/
├── EnchantifyInsideCover.xcodeproj     Xcode project for the iOS app
├── Package.swift                       SwiftPM wrapper for shared core tests
├── PROJECT_OVERVIEW.md                 This architecture and product guide
├── README.md                           Setup-focused readme
├── SETUP.txt                           Local setup notes
├── InsideCoverApp/                     SwiftUI app, sheets, services, PDF export
├── Shared/                             Codable models, curation, story systems
├── Tests/InsideCoverCoreTests/         Unit tests for shared policy and systems
├── Sample/                             Sample payloads
├── scripts/                            Local validation/generation helpers
└── RemotionPromo/                      Separate promo-video project, not app core
```

## Philosophy

ReEnchanted treats ordinary life as material worthy of literary attention. Its
job is not to diagnose, optimize, or score the reader. It observes like a
careful book:

- "This person appears when safety is described."
- "Harbors, rain, fog, and shorelines are gathering."
- "This Belief has been in the margins for months."
- "A person, place, or motif used to appear often and has gone quiet."

The important distinction is that these are literary observations, not clinical
claims. The Book speaks in character, but the machinery underneath stays local,
structured, and explicit.

Design principles:

- **Memory over novelty:** new systems should deepen existing memory before
  adding more disconnected page types.
- **Kept pages are canonical:** dismissed pages can influence fatigue, but kept
  pages are what the Book treats as real archive material.
- **The Book is a reader:** it should surface patterns, durations, absences,
  returns, relationships, and Belief life cycles.
- **Local first:** private material stays on device unless a specific external
  lookup is knowingly used.
- **Structured before generated:** the app stores typed events, ledgers,
  memories, page metadata, and source IDs so generated prose has rails.
- **In-world, not dashboard:** data appears as pages, letters, margins, and
  editions rather than charts for their own sake.
- **Gentle agency:** the reader keeps, dismisses, gives Belief, asks, answers,
  casts, binds, searches, and exports. The Book suggests; it does not pretend
  the reader completed real-world actions.

## The Core Loop

1. The reader opens the app and the Book refreshes a small set of candidate
   surfaces.
2. Source adapters inspect today, archive history, local signals, preferences,
   Belief ledgers, nearby places, calendar pressure, and prepared generated
   pages.
3. The curator ranks candidates by score, source weight, fatigue, time affinity,
   distress/gentleness, type diversity, source settings, and page Belief.
4. The reader opens, keeps, dismisses, answers, or continues a page.
5. Kept pages are persisted into the archive and can mint narrative events,
   entity memories, faculty entries, resurfacing records, talisman deltas, and
   search index material.
6. Generated systems use the archive and story field to write braids, letters,
   story pages, gossip, research, enchantments, and Ask the Book replies.
7. The Book later returns old pages, notices patterns, and can bind a monthly
   edition as a PDF.

The daily loop is therefore not "generate a page and forget it." It is:

```text
surface -> keep/dismiss -> archive -> event/memory -> curation -> return
```

## First Run And Onboarding

The onboarding flow lives in `BookSurfaceViews.swift` and asks what the reader
wants to be called. That preferred name flows into Welcome pages, letters, and
generated text.

First-run behavior:

- The **Welcome Page** is intentionally early and plain-spoken in character.
- **Chapter Binding** exists, but is not forced as the first thing a new reader
  must do.
- The Book explains itself as a living book of kept pages, not as a productivity
  app.

Relevant files:

- `InsideCoverApp/BookSurfaceViews.swift`
- `InsideCoverApp/ContentView.swift`
- `Shared/SourceAdapters.swift`
- `Shared/PageModel.swift`

## Page Model

`BookPageType` is a closed enum in `Shared/PageModel.swift`. Each page type has
title, short title, SF Symbol, source metadata, visual handling, default intent,
default Belief, and narrative weight.

Current page types:

```text
mood, diary, souvenir, rest, body, fuel, weather, location, quip,
aboutYou, wonderCompass, lore, patreon, illustration, illuminatedPhoto,
narrativeOS, gossip, facultyResearch, letter, supportGuild, castMember,
bookOfYou, askTheBook, enchantment, anchor, academyClass, elective,
packPage, calendar, helpTips, welcome, marginsAtlas, bookRemembered,
bookNotices
```

Important model types:

- `BookPage` - durable kept page.
- `BookDay` - archive day containing kept pages.
- `SurfacePage` - candidate/live page in the feed or sheet.
- `BookPagePayload` - headline, body, and metadata.
- `BookPageMediaAsset` - bundled image, rendered image file, or photo-library
  reference.
- `BookPageSource` - source identity, privacy, cadence, symbol, and note.
- `BookPageSourceRegistry` - source catalog for page types.

## Source Adapters

The feed is produced by `BookPageSourceAdapters.active` in
`Shared/SourceAdapters.swift`. Each adapter receives:

- current `BookDay`,
- `CuratorContext`,
- `BookSourceInputs`,
- current time.

It returns zero or more `SurfacePage` candidates. The active adapter order is:

```text
Rest, Mood, Diary, Souvenir, Book of You, Book Remembered, Book Notices,
Ask the Book, Body, Fuel, Faculty Research, Character Letter, Support Guild,
Weather, Enchantment, Welcome, Academy Class, Elective, Pack Page, Calendar,
Quip, About You, Wonder Compass, Lore, Help Tips, Patreon, Illustration,
Illuminated Photo, Story Page, Margins Atlas, Gossip, Cast Member,
Outer Stacks Anchor, Location
```

`BookSourceInputs` is the central context bundle. It carries body/weather
signals, enchanted weather, anchors, nearby places, self facts, faculty entries,
custom cast members, electives, entity/page Belief offsets, surface history,
calendar events, resurfacing candidates, quiet days, current arc, recent
narrative events, and the current literary-continuity digest.

## Curation

`Shared/SurfaceAndCurator.swift` owns curation policy.

Key pieces:

- `BookCurator` - gathers candidates and chooses the visible set.
- `CuratorContext` - hour, weekday, distress/gentleness state, source settings.
- `CuratorVarietyGovernor` - source fatigue, disabled sources, low-Belief
  surprise boosts, and source preference effects.
- `CuratorTimeAffinity` - time-of-day fit.
- `SurfaceDismissalLedger` - rest windows after dismissal.
- `SurfaceHistoryRecord` - what was shown recently.
- `SurfaceReadinessState` - whether a page can open immediately or needs local
  brain work first.
- `SurfaceActionRouter` - turns readiness and work state into open/block/start
  decisions.
- `WorkBlockingState` - central policy for concurrent local-brain work.
- `PreparedPageRecoveryState` and `BraidRecoveryState` - recovery after
  generation failures or interrupted work.

Curation is intentionally not pure randomness. It blends authorial source
scores with reader preference, memory, fatigue, time, and current context.

## Major Page Families

### Daily Capture Pages

Core capture pages include Inner Weather, Diary, One-Sentence Souvenir, Center
Page, Body Page, Fuel Log, Weather Page, Location Page, About You, and Calendar.

These are the low-friction material that later becomes the Book's archive.
Faculty-flavored capture windows, such as Dr. Inkrest for inner weather and Dr.
Vellum for fuel/body notes, use structured `FacultyEntry` records so the app
can tell whether a window has already been logged.

### Book Of You

The Book of You is the nightly braid. It gathers kept pages from the day and
asks the local brain to compose them into a coherent personal page.

Related pieces:

- `BookOfYouPageSourceAdapter`
- `Braider`, `AppBraider`, `MLXBookBraider`, `FakeBraider`, `ResilientBraider`
- `BraidTextPolisher`
- `BraidRecoveryState`

The polisher removes repeated sentences, repeated ideas, motif echoes, and
overlong output. The braid only becomes canonical after it is successfully kept
and captured in the archive.

### The Book Remembered

The Book Remembered resurfaces older kept pages when today rhymes with them.
It uses resurfacing candidates, page text, tags, and now literary-continuity
signals to explain why something returned.

This is one of the app's central "memory acting on memory" features. A returned
page is not just a search result; it is the Book saying, "This matters again."

### The Book Notices

The Book Notices is the dedicated page where the Book surfaces its own literary
observations. It is powered by `LiteraryContinuityProjector`.

It looks for:

- repeated patterns across kept pages,
- absences after previously repeated motifs,
- durations, such as how long a page or Belief has lived in the margins,
- Belief life cycles, including current glow, page count, event count, and
  related character count.

The page deliberately uses careful language:

```text
I am not certain yet. Books should be careful with certainty.
I have noticed...
```

It should feel like a living book forming opinions about the reader's story,
not like analytics.

The same page type also carries the rarer continuity moments: constellation
namings, sealed wagers, and opened seals (see Constellations And Sealed
Margins below).

### Constellations And Sealed Margins

`Shared/Constellations.swift` makes noticing consequential over time.

**Constellations.** A continuity signal that keeps surviving gets promoted into
a durable `Constellation` with a lifecycle:

```text
noticed -> watched -> named -> woven -> faded (and back, on return)
```

`ConstellationKeeper.advanced(...)` runs the promotions deterministically:
strength >= 58 creates `noticed`; three sighting days make it `watched`; five
sightings plus fourteen days of age earn it a Book-given name (`named`); nine
sightings make it `woven`; twenty-eight quiet days fade it. A faded
constellation that returns keeps its name and increments `returnCount`.

Names are deterministic per constellation and template-built by signal kind:
"The Harbor Thread", "What Shoreline Left Quiet", "The Long Archive",
"The Living Lamp". When a constellation crosses into `named`, the Book
surfaces a naming page ("The Book Names: ...").

**Sealed margins.** `SealedMarginEngine` lets the Book risk being wrong. A
strong pattern or absence signal can mint a dated, sealed `BookWager`
(maximum two sealed at once, with a 45-day per-subject cooldown). When the
open date arrives, the wager is judged against the pages actually kept since
sealing, and the Book surfaces an "opened seal" page owning the result either
way - being graciously wrong is part of the design.

Both ledgers persist in `PlayerVaultData` and are advanced by
`ContentView.tendConstellations()`, which runs alongside `tendArc()` at launch
and after narrative events. They flow into letters, gossip, monthly edition
forewords, and the save file/archive exports.

### Themes

`BookThemeEngine` (in `Shared/LiteraryContinuity.swift`) finds the month's
weather system: two or three motifs that kept gathering across kept pages,
continuity signals, and living constellations, joined into a deterministic
name like "Secrets and Harbors" or "Of Rain and Lamps". Each `BookTheme`
carries its motifs, a one-line description, evidence page IDs, and short
excerpt quotes pulled from the reader's own pages.

Themes are remembered per month in `PlayerVaultData.themes` (tended by
`tendConstellations()`); old months keep their themes forever. The live theme
flows into the Book Notices body ("The month itself is gathering into a
theme..."), character letter packets, and the monthly edition - where it
becomes the chapter subtitle and its own Themes page.

### Monthly Editions

Monthly editions are the first step toward annual bound volumes.

Each edition is a numbered chapter of a continuing book:
`chapterHeading` reads "The Book of You - bj - Chapter 3 - June 2026", where
the chapter number is the month's position among all months with kept pages,
and the subtitle is the month's theme name.

`Shared/MonthlyEdition.swift` builds a `MonthlyEdition` for the previous
calendar month. It curates:

- "What The Book Noticed"
- "Daily Braids"
- "One-Sentence Souvenirs"
- "Letters And Voices"
- "Images And Illuminations"
- "Other Kept Pages"

Every edition opens with a **foreword written by the Book**
(`BookForewordWriter`): what the month left in its keeping, what it noticed,
which constellations it named, and how its wagers went. The foreword is
deterministic - the same month always gets the same foreword.

`MonthlyEditionBuilder.year(...)` binds a whole year into an annual
("Book of You: The 2026 Annual") using the same machinery.

`InsideCoverApp/MonthlyEditionPDF.swift` writes the edition to a PDF using
`UIGraphicsPDFRenderer`, and every month binds differently on purpose.
`EditionStyle.style(for:)` deterministically picks, from the month key and
theme:

- one of six palettes (Harbor, Lamplight, Violet Dusk, Forest Margin,
  Rose Vellum, Slate Nocturne),
- a procedural cover motif (constellation chart, moon-and-waves, lamp,
  sprig, key-and-door) - theme motifs can pull the choice (water words get
  waves, light words get the lamp),
- an ornament style (diamonds, stars, waves, leaves) used on rules
  throughout.

The bound volume contains, in order: a full-bleed illustrated cover with the
chapter heading and theme subtitle; the Book's foreword with a drop cap;
a Themes page (theme name, line, excerpt quotes, motif chips); "The Reader's
Sky" - a dark star-chart page drawing the living constellations with labels
and a legend; a contents page; the curated sections with running heads,
section opener bands, date chips, and the Book's own marginalia in the left
margin (drawn from continuity signals, named constellations, and theme
motifs); framed image plates (including Photos-library assets resolved at
binding time when access is already granted); and a colophon.

The lab/export area in `ContentView` exposes `Bind monthly edition`; once
generated, the control becomes a `ShareLink`.

This system is intentionally archive-driven. It does not generate a whole book
from scratch. It binds accumulated artifacts into a coherent monthly volume.

### Ask The Book

Ask the Book is a conversational surface. It can answer from local context,
archive material, and enchantment follow-up state. The prompt contract keeps
answers in the Book's voice but bans pretending the reader completed real-world
actions.

Related pieces:

- `AskTheBookPageSourceAdapter`
- `AskTheBookTurn`
- `AskTheBookAnswering`
- `MLXAskTheBookAnswerer`
- `FakeAskTheBookAnswerer`

### Story Pages

Story Pages are generated narrative scenes built from the story field. They can
include selected entities, threads, relationships, memories, recent real-world
signals, and a three-choice grammar.

Related pieces:

- `StoryScenePacketBuilder`
- `StoryPagePromptBuilder`
- `StoryPageResultPromptBuilder`
- `StoryPageSceneDraft`
- `MLXStoryPageWriter`
- `MLXStoryPageResultWriter`
- `NarrativeEventResolver`

Keeping or continuing story pages can record choice events and move the
narrative field.

### Gossip Pages

Gossip Pages simulate offscreen world motion. They show what characters,
threads, and entities are doing when the reader is not directly interacting.

Gossip is deliberately juicy and specific, not generic margin-muck. Each turn
carries:

- a quoted overheard line attributed to a named witness from the cast,
- a concrete detail drawn from the actor's quirks, faults, beliefs, or
  unwritten interest,
- stakes ("If it works... If it curdles, that fault becomes the story
  everyone tells at breakfast"),
- a callback to one of the reader's own kept pages from that day,
- a whisper about any named constellation the Book keeps, when one touches
  the actors or thread involved.

Gossip can create narrative events and occasionally Chapter Talisman Belief
moves. It is a way for the world to keep living between direct scenes.

### The Bleed (Pocket Edition)

`Shared/TheBleed.swift` brings the Academy's student newspaper to the phone
as a distilled twice-daily edition in Penny Blackletter's voice (Records
Clerk, Department of Attestation - dry, precise, suspicious of the word
"resolution"). The full broadsheet still lives on the Mac.

Two editions a day, by the clock: the **Morning Edition** (4:00-12:59)
focuses on the day ahead; the **Evening Edition** (from 16:00) on tomorrow.
Each carries:

- **Casement Weather** - deterministic clerk-voice weather column.
- **Today at the Academy / Tomorrow, Posted Early** - the reader's real
  calendar events, posted as the corridor noticeboard.
- **The Morning/Evening Ledger** - Penny's lead column, written by the local
  brain from a packet of continuity signals, named constellations, sealed
  wagers, the month's theme, the current arc, and today's kept pages.
- **Corridor Whispers** - the gossip simulation turns rewritten as signed
  whispers, mechanics preserved.
- **The Reader's Shelf** - a researched column on one of the reader's About
  You interests, built from live web clippings (Reddit's public search API
  first, open-web abstract as fallback; the source registry note discloses
  the lookup). Morning and evening pick *different* interests on the same
  day.

Delivery is two-stage and in character: the curator surfaces an announcement
("The newest edition of The Bleed is here - Open it"); opening it runs the
presses (`prepareBleedEditionIfPossible`): interest research, one local-brain
call per written column, then deterministic compositing into a single page
with masthead and colophon ("Set in type by P. Blackletter, who attests every
word and regrets several"). Issue numbers count kept editions forever.
Keeping an edition feeds Belief to `penny-blackletter`. A lab control binds
the latest edition as a broadsheet-style PDF (`BleedPDFWriter`).

### Character Letters

Letter Pages are character-authored correspondence. Sender selection considers
Belief, narrative weight, memories, recent story field presence, custom cast,
and stable jitter.

Letters can include:

- preferred reader name,
- sender voice profile,
- memories and recent events,
- unwritten interest,
- home/context material,
- continuity packet from the Book's observations,
- occasional Chapter Talisman deltas.

Related pieces:

- `CharacterLetterPageSourceAdapter`
- `CharacterLetterPromptBuilder`
- `MLXCharacterLetterWriter`
- `FakeCharacterLetterWriter`
- `CharacterLetterWriter`

### Margins Atlas

The Margins Atlas is the relationship/constellation surface. It has two
variants:

- **The Loom** - threads, warmth, tension, and relationship crossings.
- **The Constellation** - Belief stars and attention lines.

It is the app's knowledge graph disguised as magic.

### Wonder Compass And Playful Missions

Wonder Compass pages draw from reference snippets and mission registries. They
can offer Playful Missions, including South = Sense style sensory errands, and
can ask the local brain to generate a fresh custom mission.

Related pieces:

- `WonderCompassPageSourceAdapter`
- `PlayfulMissionRegistry`
- `PlayfulMissionWriter`
- `MLXWonderCompassChooser`
- `WonderCompassFallbackChooser`

### Enchantments And Illuminated Photos

Enchantments are camera/photo spells. A photo or object becomes material for a
spell such as poetic translation, connection, haiku, roasting, mirror, and
other modes defined by `StoryEnchantmentCatalog`.

The photo stack includes:

- Photos and Vision integration for candidate discovery/captioning,
- `PhotoLibraryService`,
- `PhotoCandidateScorer`,
- `VisionPhotoCaptioner`,
- `GemmaPhotoIlluminationAnalyzer`,
- `VLMPhotoIlluminationAnalyzer`,
- `IlluminatedPageComposer`,
- `MLXEnchantmentWriter`.

Illuminated Photos render manuscript-style image pages using bundled marginalia,
scraps, stamps, texture overlays, and layout templates.

### Weather, Body, Fuel, And Local Signals

The app can translate real signals into book pages:

- HealthKit/body data through `HealthKitBodyReader`.
- Weather through `WeatherLocationReader` and `WeatherSourceSignal`.
- Fuel logs through `VellumNutritionist` and USDA lookup when a key is present.
- Moon phase through local astronomy in `MoonPhaseCalendar`.
- Calendar pressure through `CalendarEventSignal`.
- Nearby places through `LocalPlacesScout`.

The design rule is that signals become atmosphere and pages, not exposed raw
telemetry dashboards.

### Anchors And Outer Stacks

Anchors turn real places into story rooms. Default anchors ship empty; anchors
belong to the reader's save.

Key pieces:

- `AnchorRecord`, `AnchorKind`, `AnchorRegistry`, `AnchorMath`
- `AnchorLocationReader`
- `AnchorOfferFormView`
- `OuterStacksAnchorPageSourceAdapter`
- `OuterStacksRoomEngine`
- `OuterStacksRoomSpec`

Known anchors can light within roughly 200 meters. Unanchored real places can
be offered as future anchors. Check-ins update the anchor ledger and can reward
Belief.

### Classes, Clubs, And Electives

Academy classes and clubs come from schedule registries and surface at relevant
times. Unwritten Electives let characters ask for small real-world favors tied
to their interests and, when available, nearby real places.

Related pieces:

- `AcademyScheduleRegistry`
- `AcademyClassPageSourceAdapter`
- `ElectivePageSourceAdapter`
- `UnwrittenElective`
- `ElectiveOfferWriter`
- `ElectiveFlyleafListView`

### Help, Tips, Lore, Quips, Patreon, And Packs

Reference-style content is sourced from registries and packs:

- `HelpTipsCatalog`
- `BookReferenceCatalog`
- `BookReferenceLibrary.json`
- `QuipPackRegistry`
- `PageArchetypePackRegistry`
- `BookShopCatalog`
- `PackEntitlements`

Help and Tips is practical user guidance in the Book's UI. Lore and quips are
public-reference material. Pack pages are a bridge toward more data-driven
content.

## Belief

Belief is a 0-100 attention and world-energy value used at multiple levels:

- reader/book Belief,
- entity Belief,
- page-source Belief,
- Chapter Talisman Belief,
- custom cast starting Belief.

Belief does not just change copy. It influences curation, story-field weights,
Glow menus, entity prominence, Chapter ascendance, and event effects.

Important types:

- `PageBeliefProfile`
- `GlowCommandMenu`
- `GlowEntityMenuItem`
- `GlowPageMenuItem`
- `NarrativeEventEffect`
- `ChapterTalismanMove`
- `PlayerVaultData.entityBelief`
- `PlayerVaultData.pageBelief`

The Glow menu lets the reader give or take Belief from page sources and world
entities. Those changes become ledgers and narrative events, not invisible
settings.

## Chapters And Talismans

Chapters are represented as talisman entities in the narrative pack. Talisman
Belief can move when story pages, gossip, or letters carry talisman deltas.

Behavior:

- Entities can give Belief to their own Chapter's talisman.
- Entities can attempt to take Belief from a rival talisman.
- Generated pages carry structured move metadata.
- Keeping the page applies the resulting ledger deltas in `ContentView`.

This makes world politics and attention mechanically persistent without turning
the app into a combat system.

## Characters And World Entities

Characters are not just names in prompts. The app treats them as structured
world entities with enough internal shape to stay consistent across letters,
gossip, story scenes, illustrations, search, memory, Belief, and page curation.

The central type is `NarrativeWorldEntity`. It represents characters, objects,
locations, threads, classrooms, talismans, real-world anchors, and motifs.
Every entity can carry:

- stable `id`, `packID`, display `name`, and `kind`,
- Belief and narrative weight,
- optional Chapter affiliation,
- optional `unwrittenInterest`,
- traits,
- quirks,
- faults,
- beliefs,
- goals,
- tags,
- optional `WritingVoiceProfile`.

That makes the cast deliberately well-rounded. A character is not only "warm"
or "mysterious"; they can have a worldview, a want, a blind spot, a habit, a
topic they care about, a Chapter alignment, and a mechanical weight in the
story field.

Examples from the bundled core cast:

- **The Book** is an attentive object/entity that believes attention is a kind
  of care and wants to turn real days into pages worth keeping.
- **Penny Blackletter** is dry, warm, and observant; she cares about marginalia,
  photos, indie publishing, and honest details.
- **Dr. Selene Inkrest** is gentle, precise, therapeutic, and
  narrative-minded; she tends difficult pages without rushing them.
- **Dr. Elowen Vellum** is warmly clinical and experiment-minded; she translates
  fuel, body, recovery, and health signals into low-shame field notes.
- **Headmistress Seraphina Thorne** carries authority, thresholds, secrecy, and
  institutional coherence.
- **Orion Blackthorn** pulls toward architecture, innovation, ambition, and the
  cost of making impossible structures work.
- **Zara Finch** is loyal, quick, practical, and vigilant about trust and safe
  paths.
- **Wicker Eddies** tests weak premises, doubt, and false magic.
- **Gwendolyn Mythwright** holds archives, impossible zoology, maritime
  mysteries, and evidence that makes wonder less lonely.

### What Entities Know

Entities know their own structured identity:

- what kind of being or thing they are,
- what Chapter or story pressure they lean toward,
- what they believe,
- what they want,
- what they are good at noticing,
- what they tend to get wrong,
- what topics naturally draw them into letters or electives,
- what tags connect them to pages, memories, places, motifs, and threads.

They also know world context through the packets passed into generation:

- recent kept pages,
- current day signals,
- weather/body/fuel/location context when available,
- story-field weights,
- entity memories,
- relationship edges,
- literary-continuity signals,
- current arc/thread context,
- recent narrative events,
- custom cast entities added by the reader.

Generated prose should not ask a character to "just improvise." The app hands
the character a structured packet of what they are, what has happened, what the
Book has noticed, and what the current surface needs.

### What Entities Remember

Entity memory is handled through `NarrativeEntityMemory`. These are durable,
entity-specific recollections created from narrative events. A memory records:

- the entity it belongs to,
- source event ID,
- optional source page ID,
- summary,
- tags,
- narrative weight,
- creation date.

`NarrativeEntityMemoryResolver` mints memories from events. For example, a kept
page, letter, story choice, gossip turn, or Belief action can become something a
character or entity later remembers. `NarrativeEntityMemoryConsolidator` merges
near-duplicates and caps runaway weight so memories remain useful instead of
becoming noise.

Characters can then use memory in several places:

- Letters include an entity memory packet for the sender.
- Story packets select relevant entity memories for scene context.
- Gossip can draw actors from story/memory pressure.
- Search can find entity memories directly.
- Book Notices and literary-continuity signals can be offered back into letters.

This means a character can develop a relationship to the reader over time
without that relationship living only in generated prose.

### Voice, Appearance, And Continuity

Characters have multiple identity layers:

- `WritingVoiceProfile` defines register, rhythm, diction, habits, and things
  to avoid. Letters and generated prose use this to keep character voice stable.
- `CharacterIllustrationProfile` defines palette, silhouette, signature object,
  continuity notes, prompt, negative prompt, marginalia tags, and asset
  references.
- `NarrativeRelationshipEdge` defines how entities relate: warmth, tension,
  trust, kind, note, tags, and narrative weight.
- `NarrativeWorldEntity` defines the mechanical/story identity.

These records let the same character behave consistently as:

- a letter writer,
- a story-scene participant,
- a gossip actor,
- a search result,
- a Belief target,
- an illustration subject,
- a memory owner,
- a source of electives,
- a Chapter-aligned participant.

### What Characters Can Do

Characters and world entities can act through several systems:

- **Appear in Story Pages:** `StoryScenePacketBuilder` selects entities based on
  tags, story-field weights, memories, custom cast, and current context.
- **Send Letters:** `CharacterLetterPageGenerator` chooses senders by Belief,
  narrative weight, memory hits, story-field presence, recent senders, and
  stable jitter.
- **Generate correspondence in voice:** letter prompts include sender identity,
  preferred reader name, unwritten interest, home context, research query, voice
  profile, memory packet, continuity packet, and talisman moves.
- **Participate in Gossip:** `GossipSimulationBuilder` selects actors and
  threads, creates offscreen turns, visible traces, overheard lines,
  consequences, hidden effects, Belief combat summaries, and optional talisman
  moves.
- **Ask for Unwritten Electives:** character interests can become small
  real-world favors, with nearby places used when available.
- **Move Chapter Talismans:** story pages, gossip, and letters can carry
  structured `ChapterTalismanBeliefMove` metadata. Keeping those pages applies
  ledger deltas.
- **Receive or lose Belief:** the Glow menu can adjust entity Belief. Those
  changes persist and affect future selection.
- **Become searchable:** entities, custom cast members, memories, tags, and
  Glow tiers can surface in Search the Stacks.
- **Anchor page meaning:** entity tags and memories help old pages return, help
  the Book notice patterns, and help the Margins Atlas draw relationship shape.

### Relationships And Disagreement

Relationships are typed, weighted edges rather than loose prose. A
`NarrativeRelationshipEdge` can carry warmth, tension, trust, kind, note, tags,
and narrative weight. These edges feed story packets and the Margins Atlas.

The current architecture is ready for deeper character disagreement because
characters already have different:

- beliefs,
- goals,
- faults,
- interests,
- Chapter alignments,
- relationship weights,
- memories,
- writing voices,
- tags.

For example, Dr. Vellum and Dr. Inkrest can plausibly interpret the same month
differently because one is biased toward body/fuel/recovery and the other
toward narrative repair and emotional weather. Penny can notice evidence and
publication/marginalia shape that neither doctor would foreground. Wicker can
test whether a pattern is real or theatrical. The Book can hold the whole set
as careful literary observation.

### Custom Cast Members

Custom Cast Members are first-class world entities. The reader can create one
in `CustomCastMemberSheet` with:

- name,
- kind,
- meaning,
- description,
- traits,
- beliefs,
- goals,
- tags,
- base Belief,
- narrative weight,
- optional image asset.

The saved member is converted into a `NarrativeWorldEntity` with pack ID
`user-cast`. From there it can participate in story selection, letters, memory,
Belief, search, curation, cast pages, and visual surfaces alongside bundled
characters.

This matters philosophically: the cast is not closed. People, places, objects,
and motifs that matter to the reader can enter the Book's world model and
become part of its future attention.

### Current Limits

The character system is strong structurally, but there are still useful places
to deepen it:

- Characters do not yet run a full multi-party debate engine.
- Relationship changes are present but could become more visible in letters and
  Margins Atlas pages.
- Long-term seasonal character arcs are not yet fully bound into monthly or
  annual editions.
- The Book Notices layer can offer continuity to characters, but characters do
  not yet consistently argue with those observations.

The important foundation is already there: characters know who they are, what
they care about, what they remember, how they sound, where they fit in the
world, what they can affect, and how the reader's kept pages can change their
future behavior.

## Narrative Story Field

The story field is the app's structured continuity layer.

Core types:

- `NarrativeEvent`
- `NarrativeEventKind`
- `NarrativeEventEffect`
- `NarrativeStoryFieldProjection`
- `NarrativeStoryFieldProjector`
- `NarrativeEventResolver`
- `NarrativeEntityMemoryResolver`
- `NarrativeEntityMemoryConsolidator`

Events come from kept pages, answers, selected choices, Belief actions,
letters, gossip, simulation turns, enchantments, compass runs, and talisman
moves. The projector folds events into weights for entities, threads,
relationships, and overall Belief.

Generated pages read that projection so the world reflects what the reader has
actually kept and done.

## Literary Continuity

`Shared/LiteraryContinuity.swift` is the newest deepening layer. It is separate
from ordinary memory:

- Memory remembers facts and events.
- Continuity notices patterns, absences, durations, and life cycles.

`LiteraryContinuityProjector.digest(...)` reads archive days, narrative events,
entity memories, entity Belief, and page Belief. It emits a
`LiteraryContinuityDigest` containing:

- `LiteraryContinuitySignal` records,
- `BeliefLifecycleProfile` records.

Signals feed:

- The Book Notices page.
- Book Remembered scoring/reasons.
- Character Letter memory packets - and a strong absence signal becomes the
  letter's *occasion*: the sender writes because something went quiet, asking
  after it warmly without alarm.
- Monthly edition opening sections and the Book's foreword.
- Constellation promotion and sealed-margin wagers
  (`Shared/Constellations.swift`).
- The portable save file and archive export carry the digest, constellations,
  and wagers (`ReEnchantedSaveFile.continuity`, `BookArchiveExport` schema 2),
  so the wider Labyrinth - scene engine, NPC dialogue - can reference the same
  threads by name.

This is the foundation for the Book forming careful opinions about the reader's
story.

## Memory Model

The app has several kinds of memory, each with a different job:

- `SelfFact` - reader-provided identity, preferences, home/place context, and
  About You answers, with sensitivity and use-permission.
- `BookPage` - durable kept artifact.
- `NarrativeEvent` - mechanical consequence.
- `NarrativeEntityMemory` - entity-specific recollection.
- `FacultyEntry` - structured body/fuel/mood support logs.
- `SurfaceHistoryRecord` - what surfaced recently.
- `BookArchiveResurfacing` records - return history.
- `PlayerVaultData` - anchors, electives, Belief ledgers, tutor progress, owned
  packs, surface history, and current arc.
- `ReEnchantedSaveFile` - complete portable export/import container.

Memory is intentionally typed. Generated prose should be an expression of these
records, not the only place continuity exists.

## Persistence, Export, And Import

`Shared/BookArchiveDatabase.swift` is the SwiftData-backed persistence layer.
`InsideCoverApp/BookDatabase.swift` is the app-facing wrapper.

Persisted data includes:

- archive days and kept pages,
- resurfacing records,
- self facts,
- narrative events,
- entity memories,
- faculty entries,
- custom cast members.

`BookStore` and `PlayerVaultData` handle the companion save/vault material.

Export/import:

- `ReEnchantedSaveFile` exports the reader's save as
  `.reenchanted-save.json`.
- Import merge-upserts material and does not delete local data.
- `BookArchiveExport` normalizes archive days for backup/export.
- `MonthlyEditionPDFWriter` creates shareable monthly PDF editions.

## Search The Stacks

Search is local and structured first.

Key pieces:

- `StacksSearchDataset`
- `StacksQuery`
- `StacksSearchEngine`
- `SearchTheStacksSheet`
- optional local-brain interpretation for unusual queries

Search can find:

- kept pages,
- prompts and user text,
- tags and page types,
- self facts where appropriate,
- entity memories,
- custom cast members,
- page family/type words,
- Glow tier language,
- co-kept correlations such as tiredness.

Kept pages reopen through the same surface sheet used by live pages, so archive
items are not inert rows.

## Local Brain

The local brain is the on-device generation layer, mostly implemented through
Gemma/MLX when `NATIVE_LOCAL_BRAIN` is available. Access is serialized by
`LocalBrainInferenceGate`.

Core files:

- `InsideCoverApp/LocalBrainServices.swift`
- `Shared/InsideCoverStore.swift`
- `InsideCoverApp/ContentView.swift`

Generation services include:

- Book of You braiding,
- Ask the Book,
- Wonder Compass choice and mission generation,
- Weather enchantment,
- Story Page prose and result prose,
- Gossip,
- Faculty Research,
- Character Letters,
- Enchantments,
- Photo illumination analysis,
- Playful Mission generation,
- Elective offers,
- Outer Stacks room writing.

Most generated features have fake or resilient fallbacks. The app should stay
usable when the model is missing, busy, unavailable, or returns malformed JSON.
`JSONSalvage` exists to recover small-model JSON output without exposing raw
braces to the reader.

## Media And Visual Design

The visual system aims to make every screen feel like a usable book, not a
generic card feed.

Key pieces:

- `BookPalette`
- `BookBackground`
- `PageVisualStyle`
- `SurfaceCard`
- `PageSourceCard`
- `BookOfYouCard`
- `ArchiveCard`
- `OpeningMovieView`
- `FairyScribe`
- `WrittenGoldText`
- `ParchmentSurface`
- `IlluminatedPageRenderer`

Illustration and illumination are data-driven:

- `IlluminationTemplate`
- `IlluminationAssetPack`
- `IlluminationTemplateLibrary`
- `IlluminationPackRegistry`
- `IlluminationMarginaliaLibrary`
- `IlluminatedPageComposer`

Assets include parchment textures, marginalia marks, illumination scraps,
sample photos, app icons, character portraits, and sound effects.

## Sound, Haptics, And Small Interactions

`InsideCoverApp/BookSounds/` contains short interface sounds for page opening,
keep/dismiss, source refresh, braiding, selection, knock, errors, and undo.

`BookFeedback` and the support code in `AppSupport.swift` coordinate haptics and
sounds. The banner knock interaction can return state-aware notes through
`BannerKnockNotes`.

## BookShop And Packs

The pack system is partly data-driven and partly enum-backed.

Current pack/listing concepts:

- page packs,
- story forms,
- spark packs,
- lore packs,
- marginalia packs,
- sound packs.

`BookShopCatalog` lists available or coming-soon packs. `PackEntitlements`
tracks owned pack IDs in save data. `PageArchetypePackRegistry` and related
registries expose content once unlocked.

Useful rule:

- New content inside an existing family can often be a registry or pack change.
- A truly new page family still needs a `BookPageType`, source registry entry,
  adapter, visual style, default intent, route handling, persistence handling as
  needed, and tests.

## Privacy And Data Boundaries

The app distinguishes privacy at the page-source level:

- `privateLocal`
- `localSensitive`
- `publicReference`

Self facts also carry sensitivity and use-permission. Generated prompts should
use the smallest relevant context packet, not dump the entire archive.

Network-facing or external data paths are specific:

- optional USDA FoodData lookup for fuel estimates,
- optional web/API research paths in faculty/research helpers,
- package resolution/build tooling during development,
- StoreKit or dev unlock paths for packs when implemented.

The product posture is local-first. The archive, memories, Belief ledgers, and
custom cast are the reader's save.

## App Target Files

Important app files:

- `InsideCoverApp/InsideCoverApp.swift` - `@main` entry point.
- `InsideCoverApp/ContentView.swift` - main orchestrator: feed, sheets,
  hydration, curation refresh, local-brain tasks, Glow actions, persistence,
  prepared pages, monthly edition share state, and generated talisman deltas.
- `InsideCoverApp/ContentViewFeatures.swift` - extracted feature helpers,
  export/import, monthly edition binding, page actions, and support operations.
- `InsideCoverApp/BookSurfaceViews.swift` - surface cards, page rendering,
  visual style, backgrounds, onboarding, archive cards, animation.
- `InsideCoverApp/CapturePageSheet.swift` - page opening/capture/generation UI
  for capture, story, gossip, Ask, Compass, mission, enchantment, and photo
  flows.
- `InsideCoverApp/CapturePageSections.swift` - extracted sheet sections such as
  Chapter Binding, Anchor offers, electives, and support guild.
- `InsideCoverApp/BookStatusCards.swift` - status cards, Glow menu, Belief UI,
  lab/status displays.
- `InsideCoverApp/LocalBrainServices.swift` - MLX/Gemma services, prompt
  builders, photo/Vision helpers, web/research helpers, and fallbacks.
- `InsideCoverApp/BookDatabase.swift` - app wrapper over the shared archive.
- `InsideCoverApp/SearchTheStacksSheet.swift` - local archive search UI.
- `InsideCoverApp/CustomCastMemberSheet.swift` - custom cast creation UI.
- `InsideCoverApp/BookShopSheet.swift` - pack/shop UI.
- `InsideCoverApp/AppSupport.swift` - haptics, quips, location/weather/body
  readers, nutrition support, and cross-cutting helpers.
- `InsideCoverApp/MonthlyEditionPDF.swift` - PDF rendering for monthly editions.

## Shared Core Files

Important shared files:

- `Shared/PageModel.swift` - page types, page/source metadata, media assets,
  durable page/day models, page Belief.
- `Shared/SourceAdapters.swift` - page source adapters and source input bundle.
- `Shared/SurfaceAndCurator.swift` - curation, readiness, action routing,
  work-blocking, surface history, and recovery state.
- `Shared/NarrativeCore.swift` - entities, threads, relationships, story field,
  events, memories, talismans, arcs, story packets, letters, gossip.
- `Shared/StoryEngine.swift` - story-generation contracts, scene/result
  packets, mission logic, writer protocols.
- `Shared/WorldSystems.swift` - body/weather signals, moon phase, anchors,
  location math, scheduling/world helpers.
- `Shared/InsideCoverState.swift` - remaining app state models and archive
  export structures.
- `Shared/InsideCoverStore.swift` - store/load, local model management,
  resilient/fake generation seams, archive store helpers.
- `Shared/BookArchiveDatabase.swift` - SwiftData archive and persistence.
- `Shared/ReferenceLibrary.swift` - reference snippets, quip packs,
  self-knowledge packs, illustration profiles.
- `Shared/PagePacks.swift` - page archetypes, save file, vault data, BookShop,
  margin tutor, JSON salvage.
- `Shared/Illumination.swift` - photo illumination templates, packs, composer,
  queue/source adapter.
- `Shared/StacksSearch.swift` - local search engine.
- `Shared/LiteraryContinuity.swift` - patterns, absences, durations, Belief life
  cycles.
- `Shared/MonthlyEdition.swift` - monthly edition curation model.

## Tests

The shared test suite is in `Tests/InsideCoverCoreTests`.

Coverage areas include:

- archive database persistence and migration,
- archive export and monthly-edition curation,
- archive indexing and search,
- curator behavior and source metadata,
- surface readiness and action routing,
- local-brain telemetry state,
- work-blocking policy,
- prepared-page and braid recovery,
- Book of You polish,
- story field, entities, relationships, Chapter Talismans,
- letters, gossip, story choices, class schedules,
- margins atlas layout,
- literary continuity and Book Notices,
- packs, entitlements, welcome/help behavior,
- weather, moon, body/fuel helpers, anchors, playful missions.

Common test command:

```sh
CLANG_MODULE_CACHE_PATH=/private/tmp/insidecover-module-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/private/tmp/insidecover-spm-module-cache \
swift test
```

Common simulator build command from this directory:

```sh
xcodebuild \
  -project EnchantifyInsideCover.xcodeproj \
  -scheme InsideCoverApp \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /private/tmp/InsideCoverDerivedData \
  build
```

## Development Guidance

When adding a new feature, start by deciding what kind of thing it is:

- **New content inside an existing page family:** prefer a registry, catalog,
  pack, or source-adapter change.
- **New generated prose for an existing page:** add a narrow writer protocol or
  prompt builder, a fake/fallback implementation, and recovery behavior.
- **New memory consequence:** add a typed event, effect, or memory resolver path
  before relying on generated prose.
- **New page family:** add the enum case, source metadata, adapter, visual
  style/default intent, capture/open behavior, persistence effects, and tests.
- **New export/binding format:** build from archive structures rather than
  scraping UI.

Practical rules:

- Keep generated systems structured at the boundaries.
- Use metadata keys deliberately; they become routing, search, and future
  continuity.
- Test curation and policy in shared core, not only in SwiftUI.
- Do not make real-world task completion happen in prose. The reader must
  actually keep, answer, cast, visit, or bind.
- Prefer making existing memory systems talk to each other over adding another
  isolated surface.

## Current Direction

The app has enough page families. The next high-value work is deepening:

- stronger Book Notices,
- better Belief life-cycle pages,
- richer Book Remembered returns,
- character disagreement and cross-letter memory,
- more useful Margins Atlas constellations,
- monthly edition layout polish,
- annual Volume I built from accumulated monthly/archive artifacts,
- seasonal mythology over longer histories.

The destination is a reader-held volume: a year of ordinary life bound into a
fairy story that was not generated in one shot, but accumulated page by page.
