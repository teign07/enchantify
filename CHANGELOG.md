# Changelog

## Unreleased

### InsideCover iOS: Living Book Build

- Added **The Book Remembered**, a quiet archive-return Page that resurfaces an old kept sentence when today rhymes with it through weather, time, season, calendar/place context, or story-field language. Each visitation includes why the page returned and one tiny real-world action.
- Added **The Margins Atlas**, with Loom and Constellation variants for relationship and Belief graphs drawn from the shared core and rendered in SwiftUI Canvas.
- Added a staggered daily check-in cadence so **Fuel Log**, **Inner Weather**, and **One-Sentence Souvenir** can appear morning, midday, and early evening without clumping.
- Added a Photos save action for composited **Enchantment** result pages.
- Expanded the living archive surface with Stacks search, Returned From the Stacks behavior, Book shop/pack support, custom cast, sound effects, and stronger page-source curation.
- Expanded local generation and narrative memory plumbing for Story Pages, Gossip, Letters, Faculty Research, Support Guild synthesis, Chapter/Talisman moves, custom cast members, and remembered-page events.
- Added tests for remembered-page visitations, non-clumping daily check-ins, Margins Atlas layout and graph data, Book of You polishing, archive behavior, and broader world systems.

### Validation

- `swift test` in `ios/InsideCover`: 173 tests, 0 failures.
- `xcodebuild -project EnchantifyInsideCover.xcodeproj -scheme InsideCoverApp -destination 'generic/platform=iOS' build`: succeeded.
- Physical iPhone install was attempted, but CoreDevice could not currently locate Rabbit.
