# InsideCover ("ReEnchanted") — Project Overview

InsideCover is a SwiftUI iOS/iPadOS companion app for the broader
**Enchantify** project. It turns a reader's real day, their saved pages, and
the Labyrinth of Stories' simulated world into a living illustrated book. In
the UI, "the Book," "the Labyrinth of Stories," and "the app" are intentionally
the same doorway: pages surface, the reader keeps what matters, and the kept
pages become memory for later story, letters, search, and the end-of-day
**Book of You**.

- Bundle ID: `com.openclaw.enchantify.insidecover`
- Platforms: iOS 17+ / macOS 14+ shared core via SwiftPM
- Xcode project: `EnchantifyInsideCover.xcodeproj`
- SwiftPM package: `InsideCoverCore`
- Current verified suite: 173 shared-core tests

## High-Level Structure

```text
InsideCover/
├── EnchantifyInsideCover.xcodeproj   Xcode project for the iOS app
├── Package.swift                     SwiftPM wrapper for shared core tests
├── InsideCoverApp/                   SwiftUI app, sheets, services, local brain
├── Shared/                           Codable models, curation, story systems
├── Tests/InsideCoverCoreTests/       Unit tests for shared policy and systems
├── PersonalSeed/                     Local seed/readme material
└── Sample/                           Sample state payloads if present locally
```

The domain code used to be described as living mostly in
`Shared/InsideCoverState.swift`; it has since been split into smaller shared
files. The important ones are:

- `Shared/PageModel.swift` — page types, page/source metadata, page Belief.
- `Shared/SourceAdapters.swift` — the source adapter layer that turns context
  into candidate pages.
- `Shared/SurfaceAndCurator.swift` — candidate ranking, variety, readiness, and
  curation policy.
- `Shared/StoryEngine.swift` — story packets, gossip, playful missions,
  character letters, talisman Belief moves.
- `Shared/PagePacks.swift` — installed page/archetype pack support.
- `Shared/InsideCoverState.swift` — remaining core state models and registries.
- `Shared/BookArchiveDatabase.swift` — SwiftData archive, memories, self facts,
  narrative events, and custom cast members.
- `Shared/InsideCoverStore.swift` — store/load, local model management, fake and
  resilient generation seams.

## The Daily Loop

The app's central loop is now explicit in code and copy:

1. The tutorial/onboarding asks what the reader wants to be called.
2. On first run after that name exists, the **Welcome Page** surfaces before
   Chapter Binding. It greets the reader by name and explains the Book in
   accessible, in-character language.
3. Pages surface through the curator: prompts, story scenes, letters, missions,
   tips, calendar hinges, photos, enchantments, gossip, research, and more.
4. The reader keeps the pages that matter and dismisses what does not fit.
5. Kept pages become durable archive entries, search material, entity memory,
   story-field events, and local context for future generation.
6. At night, the Book braids kept material into a **Book of You** page, polished
   to avoid repetitive prose.

Chapter Binding is still present, but it is deliberately de-emphasized on first
run. It now behaves like an optional Academy ceremony rather than the first
thing the Book asks from a new reader.

## Page Types

`BookPageType` is still a closed Swift enum, but it has grown substantially.
Current cases:

```text
mood, diary, souvenir, rest, body, fuel, weather, location, quip,
aboutYou, wonderCompass, lore, patreon, illustration, illuminatedPhoto,
narrativeOS, gossip, facultyResearch, letter, supportGuild, castMember,
bookOfYou, askTheBook, enchantment, anchor, academyClass, elective,
packPage, calendar, helpTips, welcome, marginsAtlas, bookRemembered
```

Each page type has a title, short title, SF Symbol, visual treatment, default
intent, default Belief, and narrative weight. The active source catalog lives in
`BookPageSourceRegistry`; source adapters then decide when and how each source
produces a `SurfacePage`.

Recent page families worth knowing:

- **Welcome Page** — first-run, in-character explanation of the Book/Labyrinth
  loop, using the reader's onboarding name.
- **The Book Remembered** — old kept pages return when today rhymes with them,
  with a reason and one tiny grounded action.
- **The Margins Atlas** — Loom and Constellation graph pages for relationships,
  Belief, and attention flow.
- **Help and Tips** — a rotating, practical guidance catalog with tips, tricks,
  and ideas for using the app well.
- **Calendar / The Inked Hour** — real calendar events folded into the margins
  before they happen.
- **Classes & Clubs** — Academy class/club pages from the schedule registry.
- **Unwritten Electives** — characters ask small real-world favors tied to
  their private interests and nearby real places.
- **Pack Page** — installed page packs and archetype-driven pages.
- **Outer Stacks / Anchor** — real-world anchor/location pages.
- **Enchantments** — camera/photo-based spells powered by Gemma when available.
- **Letters** — character correspondence addressed to the reader by their
  stored preferred/tutorial name.

## Source Adapters And Curation

The page feed is assembled by `BookPageSourceAdapters.active`, a list of
`BookPageSourceAdapter` implementations. Adapters inspect a `BookDay`,
`CuratorContext`, `BookSourceInputs`, and the current time, then return
candidate `SurfacePage`s. The curator ranks those candidates using:

- base score from the adapter,
- page source Belief and narrative weight,
- source fatigue and recent surface history,
- type diversity,
- time-of-day affinity,
- calendar pressure,
- distress/gentleness bias,
- active/inactive source settings,
- hard floors for automagic sources such as Inner Weather and Fuel.

This makes "what appears next" a blend of authored intent, reader preference,
recent history, and real-world context.

## Belief, Pages, And The Story Field

Belief is a 0-100 score used at several levels:

- the reader/book has Belief,
- narrative entities have Belief,
- Chapter Talismans have Belief,
- page sources have Belief,
- custom cast members enter the world with starting Belief.

`PageBeliefProfile` gives every page source a default Belief and narrative
weight. The Glow menu lets the reader give/take Belief from page sources and
cast members. Those changes are persisted as ledgers and also recorded as
events, so curation preference becomes part of the Book's memory instead of a
silent setting.

`NarrativeEventResolver` turns kept pages, choices, gossip, letters, and other
actions into `NarrativeEvent`s. `NarrativeStoryFieldProjector` folds those
events into current entity/thread/relationship weights. Story pages, gossip,
letters, and status cards all read from that live field.

## Chapters And Talismans

Chapters are now represented by talisman entities in the narrative pack. Their
starting Belief has been tuned so **Dusk Thorn starts at 11**, while **Ember
Seal, Wind Cipher, Tide Glass, and Moss Clasp start at 10**. This keeps Dusk
Thorn slightly ascendant at baseline without making the other Chapters feel
irrelevant.

Characters and world entities can now sometimes act on Chapter Talismans during
generated content:

- Story Pages can include talisman give/take moves.
- Gossip simulation turns can include talisman give/take moves.
- Character Letters can include talisman give/take moves.

These are not just atmospheric lines. Generated pages may carry
`chapterTalismanMoves` / `chapterTalismanDeltas` metadata. When such a page is
kept, `ContentView.applyGeneratedChapterTalismanDeltas` applies the resulting
ledger changes so Chapter Belief actually moves.

The moves are intentionally occasional. Entities may give Belief to their own
Chapter's talisman or attempt to take Belief from another Chapter's talisman,
with success/failure and ledger effects resolved in shared code.

## Characters, Cast, And Memory

Narrative entities include characters, locations, objects, threads, classrooms,
talismans, real-world anchors, and motifs. A `NarrativeWorldEntity` can carry:

- Belief and narrative weight,
- Chapter affiliation,
- traits, quirks, faults, beliefs, goals, and tags,
- an `unwrittenInterest`,
- an optional writing voice profile,
- relationships to other entities,
- accumulated `NarrativeEntityMemory`.

Characters can:

- appear in Story Pages,
- participate in Gossip simulation,
- send Letters,
- ask for Unwritten Electives,
- receive and lose Belief through Glow,
- sometimes move Chapter Talisman Belief,
- gain memories from kept pages and events,
- be illustrated through stable character illustration profiles.

Custom Cast Members are first-class. The reader can create one through
`CustomCastMemberSheet`, including kind, meaning, description, traits, beliefs,
goals, tags, and optional image. The saved member is persisted in SwiftData and
converted into a `NarrativeWorldEntity`, which lets it join story selection,
memory, Belief, and Cast Member pages alongside bundled characters.

### Character Records And Voice

A character is not just prose in this app. The current model spreads character
identity across several cooperating records:

- `NarrativeWorldEntity` holds the mechanical/story identity: kind, Belief,
  narrative weight, Chapter, traits, quirks, faults, beliefs, goals, tags,
  unwritten interest, and optional `WritingVoiceProfile`.
- `WritingVoiceProfile` gives letters and generated prose a reusable voice
  block: register, rhythm, diction, habits, and avoid-list.
- `CharacterIllustrationProfile` holds the visual identity used by illustration
  plates: palette, silhouette, signature object, continuity notes, prompt,
  negative prompt, marginalia tags, and asset references.
- `NarrativeRelationshipEdge` gives relationships typed connective tissue:
  authorship, attention, stewardship, care, correspondence, reality bleed,
  companionship, tension, warmth, trust, and narrative weight.

Those records let the same person behave consistently across story scenes,
letters, gossip, illustrations, Belief moves, search, and memory.

## Locations, Anchors, And Nearby Places

Locations are first-class narrative material. They appear as ordinary Location
Pages, as real-world anchors, as nearby places for electives, and as story-field
entities.

The location stack includes:

- `LocalPlaceSignal` — a nearby real place scouted from the device's location,
  with name, category, distance label, and locality.
- `LocalPlacesScout` — caches and refreshes nearby place signals, then feeds
  them into `BookSourceInputs`.
- `LocationPageSourceAdapter` — creates ordinary place/location pages.
- `OuterStacksAnchorPageSourceAdapter` — creates Anchor/Outer Stacks pages when
  a known anchor is nearby.
- `AnchorRecord`, `AnchorKind`, `AnchorRegistry`, and `AnchorMath` — durable
  anchor data, proximity checks, check-in reward logic, season helpers, and
  distance math.
- `AnchorOfferFormView` — lets the reader anchor a real place when the Book is
  standing somewhere unanchored.
- `OuterStacksRoomEngine` / `OuterStacksRoomWriting` — turns anchored real
  places into Outer Stacks room specs and visit scenes.

Important behavior:

- Built-in default anchors ship empty. Anchors belong to a reader's save, not
  to the app globally.
- Known anchors light when the reader is within roughly 200 meters.
- Checking in at an Anchor can reward Belief and updates the anchor ledger.
- If no anchor is nearby, the app can offer to make the current real place into
  a new anchored room.
- Nearby real places are also used by Unwritten Electives so character favors
  can name a real place when the scout has one.

## Reference Catalogs, Lore, And Illustration

Reference content is still partly generated from Enchantify-side lore and
partly bundled in Swift/JSON. The main runtime entry is
`BookReferenceCatalog`, backed by `Shared/BookReferenceLibrary.json` and
fallback registries.

It supplies:

- Wonder Compass snippets and relevant passage selection.
- Labyrinth/world lore snippets.
- Character illustration plates.
- Character visual profiles and bundled asset allow-lists.
- Reference text used by Lore, Illustration, Wonder Compass, and related pages.

The illustration system is data-driven around templates and packs:

- `IlluminationTemplate` describes text slots and decoration slots.
- `IlluminationAssetPack` supplies backgrounds, scraps, stamps, doodles, tape,
  overlays, and fallback phrases.
- `IlluminatedPageComposer` chooses placements and renders structured
  manuscript-like page plans.
- `PageVisualStyle` gives each page family its own parchment, accent, marginalia
  set, watermark, and decorative proportions.

That means character art, photo illuminations, letter pages, help pages, welcome
pages, and source cards all share a visual grammar while keeping distinct page
identities.

## Story Pages, Gossip, And Letters

**Story Pages** use `StoryScenePacketBuilder` to select entities, threads,
relationships, memories, and real-world signals. Generated scenes use a
three-choice grammar and can record choice events when kept or continued.

**Gossip Pages** simulate offscreen world activity. They are windows into what
characters and entities are doing when the reader is not looking. They can move
story-field weights and, sometimes, Chapter Talisman Belief.

**Letter Pages** are character-authored correspondence. The generator selects a
sender based on Belief, narrative weight, recent memories, story-field presence,
and stable jitter. Letters now address the reader using the stored onboarding
name/preferred name rather than placeholder text. They can incorporate the
sender's voice profile, unwritten interest, home context, memories, research
clippings, and occasional talisman moves.

## Memory And Continuity

There are several kinds of memory, and they do different jobs:

- **Self facts** (`SelfFact`) are things the reader has explicitly told the
  Book: name, home/place context, preferences, identity notes, and About You
  answers. Each carries sensitivity and use-permission.
- **Narrative events** (`NarrativeEvent`) are mechanical consequences from kept
  pages, Glow actions, story choices, gossip, letters, talisman moves, and other
  interactions.
- **Entity memories** (`NarrativeEntityMemory`) are character/entity-specific
  recollections minted from events by `NarrativeEntityMemoryResolver`.
- **Consolidated memories** are cleaned by
  `NarrativeEntityMemoryConsolidator`, which merges near-duplicates and caps
  runaway weight.
- **Surface history** tracks what has been shown recently, so curation can avoid
  repeating the same page/source too aggressively.
- **Prepared/recovery state** remembers in-progress generated pages and failed
  attempts so the UI can recover gracefully.

These memories feed back into story selection, letters, gossip, search, curation
fatigue, and the Book of You. This is the main reason the app can gradually
stop sounding generic: kept pages and choices become durable structure.

`BraidTextPolisher` is part of continuity too. Before a generated Book of You
page is saved, it removes exact repeats, repeated ideas, motif echoes, and
overlong braid output so the daily page reads like a composed piece rather than
model drift.

## Wonder Compass, Playful Missions, And Gemma

The Wonder Compass source now includes a large set of **Playful Mission /
South = Sense** missions imported from the attention mission pack. These sit
beside the original core missions in `PlayfulMissionRegistry`.

Wonder Compass pages can offer a mission selected from the registry, and every
Playful Mission / South = Sense page has an option to ask Gemma for a fresh
custom mission. The generation path is:

- `CapturePageSheet` exposes "Generate new mission" on standalone playful
  mission pages.
- `ContentView.generatePlayfulMissionFromSheet` starts the local-brain task.
- `PlayfulMissionWriter` asks Gemma for one sensory errand with title, prompt,
  proof prompt, tags, and photo allowance.
- A fallback mission is produced locally if Gemma cannot finish.

Custom Compass Runs can also be generated from user constraints, again with a
Gemma path and local fallback.

## Help And Tips

`HelpTipsCatalog` is a rotating library of practical guidance pages. It covers:

- what kinds of pages exist,
- how keeping and dismissing affect the Book,
- how Glow changes page/entity attention,
- how the Book of You works,
- how to use Playful Missions,
- how Gemma-generated pages behave,
- privacy and local context expectations,
- ways to get better results from prompts, photos, and kept pages.

The Help and Tips page type has its own source, visual style, menu entry, and
curator behavior. It is public-reference content, not private generated prose.

## Enchantments And Photos

Enchantments are camera/photo spells. `StoryEnchantmentCatalog` defines named
spells such as Everything Speaks, Everything's Poetry, Everything's Magic,
Everything's a Haiku, Mirror Mirror, Everything's Connected, Everything's
Roasted, and more.

The photo pipeline includes:

- Photos/Vision integration for candidate discovery and captions,
- `GemmaPhotoIlluminationAnalyzer` for local visual analysis,
- `IlluminatedPageComposer` for manuscript-style rendered pages,
- `MLXEnchantmentWriter` for spell prose,
- fallbacks when Gemma or vision analysis is unavailable.

Generated enchantments can seed Ask the Book conversations so the reader can
continue talking with the enchanted subject.

## Local Brain

The "Local Brain" is the app's on-device generation layer, currently centered
on Gemma/MLX when built with `NATIVE_LOCAL_BRAIN`. Access is serialized through
`LocalBrainInferenceGate` so model work does not stampede the device.

MLX-backed services include:

- Book of You braiding,
- Ask the Book answers,
- Wonder Compass choice/generation,
- Weather enchantment,
- Story Page prose and results,
- Gossip prose,
- Faculty Research,
- Character Letters,
- Enchantments,
- Photo illumination analysis,
- Playful Mission generation.

Most generated systems have `Fake*` or fallback implementations so the app
keeps working when the model is missing, busy, or unavailable.

## Search, Archive, And Persistence

`BookArchiveDatabase` persists:

- archive days and kept pages,
- resurfacing events,
- self facts,
- narrative events,
- entity memories,
- faculty entries,
- custom cast members.

`BookArchiveIndex` and `StacksSearchEngine` support Search the Stacks. Search
can find kept pages, memories, cast members, page families, glow tiers, and
correlations such as "what did I keep when I was tired?"

Search is intentionally local and structured first. It indexes:

- kept page text, prompts, tags, metadata, dates, and page types,
- self facts where appropriate,
- entity memories,
- custom cast members,
- page family/type words,
- Glow tier language,
- co-kept page correlations.

`SearchTheStacksSheet` is the app UI for this. It can answer direct queries
through the local index immediately, and the Book/Gemma can optionally interpret
stranger questions when that path is available.

Kept pages now reopen as full pages through the same surface sheet used by live
pages, rather than as inert row previews.

## Refactored Policy And Recovery Layer

Recent refactoring pulled a lot of UI-adjacent decision logic out of views and
into small shared structs with unit tests. This is one of the healthiest parts
of the codebase now:

- `SurfaceReadinessState` decides whether a surface is ready to open or still
  needs local-brain work.
- `SurfaceActionRouter` turns readiness plus work state into an open/block/start
  decision.
- `WorkBlockingState` centralizes which kinds of work block which page actions.
- `LocalBrainTelemetryState` tracks active work, reading-room state, last
  summary, and user-facing model status.
- `PreparedPageRecoveryState` handles generated-page cooldowns, current
  prepared surfaces, retries, and failed attempts.
- `BraidRecoveryState` handles Book of You retry/error behavior and the marking
  of captured pages as used once a braid succeeds.
- `CuratorVarietyGovernor` and `CuratorSurfacePreferences` handle fatigue,
  low-Belief surprise boosts, disabled/muted sources, and page Belief influence.

The tests around these pieces are the reason the big SwiftUI views can keep
moving while the underlying behavior stays legible.

## App Target

Key app files:

- `InsideCoverApp/InsideCoverApp.swift` — `@main` entry point.
- `InsideCoverApp/ContentView.swift` — main orchestrator: feed, sheets,
  curation refresh, local-brain tasks, Glow actions, persistence calls,
  generated talisman delta application.
- `InsideCoverApp/ContentViewFeatures.swift` — extracted feature helpers.
- `InsideCoverApp/BookSurfaceViews.swift` — page cards, illuminated surfaces,
  visual styles, page background/marginalia, animation.
- `InsideCoverApp/BookStatusCards.swift` — status cards, Glow menu, Belief UI.
- `InsideCoverApp/CapturePageSheet.swift` — page opening/capture/generation UI,
  story/gossip/Ask/Compass/mission/photo flows.
- `InsideCoverApp/LocalBrainServices.swift` — MLX/Gemma-backed generation
  services and fallbacks.
- `InsideCoverApp/CustomCastMemberSheet.swift` — custom cast creation.
- `InsideCoverApp/SearchTheStacksSheet.swift` — local archive search UI.
- `InsideCoverApp/AppSupport.swift` — haptics, quips, HealthKit, weather, and
  other cross-cutting helpers.
- `InsideCoverApp/BookDatabase.swift` — app-facing wrapper over shared archive.

## Extensibility

The content layer is increasingly pack-shaped:

- lore packs,
- narrative packs,
- quip packs,
- self-knowledge packs,
- support faculty packs,
- illumination asset packs,
- page archetype packs,
- installed Page Packs.

Availability enums already contain concepts such as bundled, patron, paid,
user-imported, and locked content. The current implementation still ships most
new page kinds through Swift enum cases and switch statements, so true
third-party page archetypes are not data-only yet. But content within existing
archetypes is moving toward a pack/registry/adapter pattern.

The current useful rule of thumb:

- New content inside an existing page family can often be added through a
  registry, catalog, or pack.
- A brand-new page family still needs a `BookPageType` case, source registry
  entry, adapter, visual style, routing/default intent handling, and tests.

## Testing And Build Notes

The shared test suite lives in `Tests/InsideCoverCoreTests/`. It covers archive
persistence/export/indexing, curator behavior, recovery state machines,
readiness/work blocking, page/source systems, story-field systems, Playful
Missions, Chapter Talismans, letters, Help/Welcome behavior, and more.

Common commands:

```sh
CLANG_MODULE_CACHE_PATH=/private/tmp/insidecover-module-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/private/tmp/insidecover-spm-module-cache \
swift test
```

```sh
xcodebuild \
  -project ios/InsideCover/EnchantifyInsideCover.xcodeproj \
  -scheme InsideCoverApp \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /private/tmp/InsideCoverDerivedData \
  build
```

The simulator build does not require a connected phone. Physical-device builds
require the developer to select their own Apple team and, if needed, unique
bundle identifiers.
