import XCTest
@testable import InsideCoverCore

final class BookCuratorTests: XCTestCase {
    func testCuratorReturnsExactlyThreeWhenEnoughCandidatesExist() {
        let pages = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 3
        )

        XCTAssertEqual(pages.count, 3)
        XCTAssertEqual(Set(pages.map(\.id)).count, 3)
        XCTAssertTrue(pages.contains { $0.type == .bookOfYou } == false)
    }

    func testDismissingTopSurfaceRefillsFromNextRankedCandidate() throws {
        let day = emptyDay()
        let firstPass = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 3
        )
        let dismissedID = try XCTUnwrap(firstPass.first?.id)

        let secondPass = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 3,
            preferences: CuratorSurfacePreferences(dismissedSurfaceIDs: [dismissedID])
        )

        XCTAssertEqual(secondPass.count, 3)
        XCTAssertFalse(secondPass.contains { $0.id == dismissedID })
        XCTAssertNotEqual(firstPass.map(\.id), secondPass.map(\.id))
    }

    func testMutedSourceIsExcludedInsideCurator() {
        let pages = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 8,
            preferences: CuratorSurfacePreferences(disabledSourceIDs: ["wonder-compass"])
        )

        XCTAssertFalse(pages.contains { $0.sourceID == "wonder-compass" })
    }

    func testPreparedIlluminatedPhotoRisesIntoVisibleShelf() {
        let prepared = SurfacePage(
            id: "illuminated-photos-prepared-test",
            type: .illuminatedPhoto,
            sourceID: "illuminated-photos",
            intent: .resurface,
            renderStyle: .illuminatedPhoto,
            score: 96,
            reason: "Penny found a photo with ink on it.",
            prompt: "Found in the Margins",
            detail: "The page is already rendered.",
            payload: BookPagePayload(
                headline: "Field Study",
                body: "The Book kept the page: detail spoke.",
                metadata: [
                    "renderedPreviewPath": "/tmp/reenchanted-prepared-illumination.jpg",
                    "assetLocalIdentifier": "test-photo-asset",
                    "sourceAssetName": "IlluminatedPhotoSource"
                ]
            )
        )
        var inputs = richInputs()
        inputs.preparedIlluminatedPhotoSurface = prepared

        let pages = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: inputs,
            now: localDate(hour: 14),
            limit: 3
        )

        XCTAssertTrue(pages.contains { $0.id == prepared.id })
    }

    func testEveryActiveSourceHasACuratorAdapter() {
        let adapterSourceIDs = Set(BookPageSourceAdapters.active.map(\.source.id))
        let activeSourceIDs = Set(BookPageSourceRegistry.activeSources.map(\.id))

        XCTAssertTrue(activeSourceIDs.isSubset(of: adapterSourceIDs))
    }

    func testSurfacePageSourceMetadataResolvesFromSourceID() {
        let page = SurfacePage(
            type: .weather,
            sourceID: "body-page",
            prompt: "The Body Page is listening quietly.",
            detail: "A soft translation is waiting."
        )

        XCTAssertEqual(page.source.id, "body-page")
        XCTAssertEqual(page.origin, .generated)
        XCTAssertEqual(page.privacy, .localSensitive)
    }

    func testIllustrationSurfaceExposesBundledMediaAsset() throws {
        let pages = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 16
        )
        let illustration = try XCTUnwrap(pages.first { $0.type == .illustration })
        let media = try XCTUnwrap(illustration.mediaAssets.first)

        XCTAssertEqual(media.kind, .bundledImage)
        XCTAssertEqual(media.reference, illustration.payload.metadata["assetName"])
        XCTAssertEqual(media.sourceID, illustration.sourceID)
        XCTAssertFalse(media.caption.isEmpty)
    }

    func testIlluminatedPhotoSurfaceExposesRenderedMediaAsset() {
        let surface = SurfacePage(
            type: .illuminatedPhoto,
            sourceID: "illuminated-photos",
            renderStyle: .illuminatedPhoto,
            prompt: "Found in the Margins",
            detail: "The page is already rendered.",
            payload: BookPagePayload(
                headline: "Lamp Study",
                body: "The Book kept the page: lamp-light gathered in the corner.",
                metadata: [
                    "renderedPreviewPath": "/tmp/reenchanted-illumination.png",
                    "assetLocalIdentifier": "photo-asset-1"
                ]
            )
        )

        XCTAssertTrue(surface.mediaAssets.contains {
            $0.kind == .renderedImageFile && $0.reference == "/tmp/reenchanted-illumination.png"
        })
        XCTAssertTrue(surface.mediaAssets.contains {
            $0.kind == .photoLibraryAsset && $0.reference == "photo-asset-1"
        })
    }

    func testCuratorCandidatesUseRegisteredSourceMetadata() {
        let pages = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 16
        )

        XCTAssertFalse(pages.isEmpty)
        for page in pages {
            let source = BookPageSourceRegistry.source(id: page.sourceID, fallbackType: page.type)
            XCTAssertEqual(page.source, source)
            XCTAssertEqual(page.origin, source.origin)
            XCTAssertEqual(page.privacy, source.privacy)
        }
    }

    func testBodyAndWeatherPagesRotateOnFourHourCadence() throws {
        let morning = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 9),
            limit: 20
        )
        let sameWindow = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 11),
            limit: 20
        )
        let nextWindow = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 13),
            limit: 20
        )

        let morningBody = try XCTUnwrap(morning.first { $0.type == .body })
        let morningWeather = try XCTUnwrap(morning.first { $0.type == .weather })
        let sameWindowBody = try XCTUnwrap(sameWindow.first { $0.type == .body })
        let sameWindowWeather = try XCTUnwrap(sameWindow.first { $0.type == .weather })
        let nextWindowBody = try XCTUnwrap(nextWindow.first { $0.type == .body })
        let nextWindowWeather = try XCTUnwrap(nextWindow.first { $0.type == .weather })

        XCTAssertEqual(morningBody.id, sameWindowBody.id)
        XCTAssertEqual(morningWeather.id, sameWindowWeather.id)
        XCTAssertNotEqual(morningBody.id, nextWindowBody.id)
        XCTAssertNotEqual(morningWeather.id, nextWindowWeather.id)
    }

    func testDismissalLedgerLetsPagesReturnAfterRestWindow() {
        let now = localDate(hour: 12)
        var ledger = SurfaceDismissalLedger()
        ledger.dismiss(surfaceID: "lore-labyrinth-rooms", dayID: "2026-06-01", at: now)

        XCTAssertEqual(
            ledger.activeDismissedSurfaceIDs(
                for: "2026-06-01",
                now: now.addingTimeInterval(30 * 60),
                ttl: 90 * 60
            ),
            ["lore-labyrinth-rooms"]
        )
        XCTAssertTrue(
            ledger.activeDismissedSurfaceIDs(
                for: "2026-06-01",
                now: now.addingTimeInterval(100 * 60),
                ttl: 90 * 60
            ).isEmpty
        )
    }

    func testRepeatableReferenceCardsUseSnippetIdentity() throws {
        let morning = BookCurator.surfacedPages(
            for: emptyDay(),
            inputs: richInputs(),
            now: localDate(hour: 9),
            limit: 8
        )
        let lore = try XCTUnwrap(morning.first { $0.type == .lore })
        let wonder = try XCTUnwrap(morning.first { $0.type == .wonderCompass })

        XCTAssertTrue(lore.id.hasPrefix("labyrinth-lore-"))
        XCTAssertTrue(wonder.id.hasPrefix("wonder-compass-"))
        XCTAssertNotEqual(lore.id, "labyrinth-lore-importReference")
        XCTAssertNotEqual(wonder.id, "wonder-compass-importReference")
    }

    func testLabyrinthLoreAvoidsProductAndMechanicsCopy() throws {
        let forbiddenTerms = [
            "enchantify",
            "simulation",
            "mechanic",
            "gameplay",
            "belief investment",
            "belief combat",
            "npc decision",
            "read this file",
            "telegram"
        ]

        for snippet in BookReferenceCatalog.enchantifyLore {
            let searchable = "\(snippet.title) \(snippet.prompt) \(snippet.body) \(snippet.tags.joined(separator: " "))"
                .lowercased()
            for term in forbiddenTerms {
                XCTAssertFalse(searchable.contains(term), "\(snippet.id) contains forbidden lore term: \(term)")
            }
            XCTAssertGreaterThan(snippet.body.count, 320, "\(snippet.id) should be long enough to carry story texture.")
            XCTAssertEqual(snippet.sourceID, "labyrinth-lore")
        }
    }

    func testLabyrinthLoreLoadsThroughContentPacks() throws {
        let packs = BookReferenceCatalog.lorePacks
        let corePack = try XCTUnwrap(packs.first { $0.id == LorePackRegistry.corePackID })

        XCTAssertEqual(corePack.displayName, "Core Labyrinth Lore Pack")
        XCTAssertEqual(corePack.availability, .bundledFree)
        XCTAssertGreaterThan(corePack.snippets.count, 10)
        XCTAssertTrue(corePack.themes.contains("characters"))
        XCTAssertTrue(corePack.themes.contains("rooms"))
    }

    func testStoryScenePacketUsesThreeChoiceGrammar() {
        let packet = StoryScenePacketBuilder.packet(
            for: dayWithMusicSouvenir(),
            inputs: richInputs(),
            now: localDate(hour: 16)
        )

        XCTAssertEqual(packet.choices.map(\.role), [.sliceOfLife, .progressArc, .surprise])
        XCTAssertEqual(packet.choices.map(\.role.title), ["Slice of Life", "Progress Arc", "Something Surprising"])
        XCTAssertEqual(Set(packet.choices.map(\.id)).count, 3)
        XCTAssertTrue(packet.choices.allSatisfy { !$0.hiddenEffect.isEmpty })
    }

    func testStoryScenePacketSelectsWeightedThreadsAndEntitiesFromPacks() throws {
        let packet = StoryScenePacketBuilder.packet(
            for: dayWithMusicSouvenir(),
            inputs: richInputs(),
            now: localDate(hour: 16)
        )

        XCTAssertEqual(packet.packID, NarrativePackRegistry.corePackID)
        XCTAssertFalse(packet.selectedEntities.isEmpty)
        XCTAssertFalse(packet.selectedThreads.isEmpty)
        XCTAssertTrue(packet.selectedThreads.contains { $0.id == "music-as-shelter" })
        XCTAssertTrue(packet.realSignals.contains { $0.contains("Spotify") || $0.contains("headphones") })
    }

    func testCoreNarrativePackIncludesRelationshipGraphEdges() throws {
        let corePack = try XCTUnwrap(NarrativePackRegistry.enabledPacks.first { $0.id == NarrativePackRegistry.corePackID })

        XCTAssertFalse(corePack.relationships.isEmpty)
        XCTAssertTrue(corePack.relationships.contains { $0.id == "weather-bleeds-book" })
        XCTAssertTrue(corePack.relationships.contains { $0.id == "penny-files-book" })
    }

    func testCoreNarrativePackIncludesAcademyRosterAndThreads() throws {
        let corePack = try XCTUnwrap(NarrativePackRegistry.enabledPacks.first { $0.id == NarrativePackRegistry.corePackID })

        XCTAssertTrue(corePack.entities.contains { $0.id == "headmistress-thorne" })
        XCTAssertTrue(corePack.entities.contains { $0.id == "zara-finch" })
        XCTAssertTrue(corePack.entities.contains { $0.id == "wicker-eddies" })
        XCTAssertTrue(corePack.entities.contains { $0.id == "gwendolyn-mythwright" })
        XCTAssertTrue(corePack.entities.contains { $0.id == "dr-inkrest" })
        XCTAssertTrue(corePack.entities.contains { $0.id == "dr-vellum" })
        XCTAssertTrue(corePack.threads.contains { $0.id == "duskthorn-investigation" })
        XCTAssertTrue(corePack.threads.contains { $0.id == "margin-glass-letters" })
        XCTAssertTrue(corePack.threads.contains { $0.id == "inkrest-difficult-pages" })
        XCTAssertTrue(corePack.threads.contains { $0.id == "elowen-refectory-experiments" })
        XCTAssertTrue(corePack.relationships.contains { $0.id == "wicker-tests-belief" })
        XCTAssertTrue(corePack.relationships.contains { $0.id == "gwendolyn-files-letters" })
        XCTAssertTrue(corePack.relationships.contains { $0.id == "inkrest-vellum-compare-charts" })
    }

    func testCoreNPCsCarryUnwrittenInterests() throws {
        let corePack = try XCTUnwrap(NarrativePackRegistry.enabledPacks.first { $0.id == NarrativePackRegistry.corePackID })
        let characterEntities = corePack.entities.filter { $0.kind == .character }

        XCTAssertFalse(characterEntities.isEmpty)
        XCTAssertTrue(characterEntities.allSatisfy {
            ($0.unwrittenInterest ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
        })
        XCTAssertTrue(corePack.entities.first { $0.id == "dr-inkrest" }?.unwrittenInterest?.contains("Consciousness") == true)
        XCTAssertTrue(corePack.entities.first { $0.id == "penny-blackletter" }?.unwrittenInterest?.contains("ethical marketing") == true)
    }

    func testCoreNarrativeCharactersAllHaveChapters() throws {
        let corePack = try XCTUnwrap(NarrativePackRegistry.enabledPacks.first { $0.id == NarrativePackRegistry.corePackID })
        let characterEntities = corePack.entities.filter { $0.kind == .character }
        let missingChapters = characterEntities.filter {
            ($0.chapter ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }

        XCTAssertTrue(missingChapters.isEmpty, "Missing chapters: \(missingChapters.map(\.name).joined(separator: ", "))")
        XCTAssertEqual(corePack.entities.first { $0.id == "dr-inkrest" }?.chapter, "Riddlewind")
        XCTAssertEqual(corePack.entities.first { $0.id == "dr-vellum" }?.chapter, "Mossbloom")
        XCTAssertEqual(corePack.entities.first { $0.id == "wicker-eddies" }?.chapter, "Duskthorn")
    }

    func testCharacterIllustrationsAllHaveChapters() {
        let missingChapters = BookReferenceCatalog.characterIllustrations.filter {
            ($0.chapter ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }

        XCTAssertTrue(missingChapters.isEmpty, "Missing chapters: \(missingChapters.map(\.characterName).joined(separator: ", "))")
    }

    func testLabyrinthIllustrationsOnlyUseBundledCharacterAssets() {
        let missingAssetPlates = BookReferenceCatalog.labyrinthIllustrations.filter {
            !BookReferenceCatalog.bundledCharacterIllustrationAssetNames.contains($0.assetName)
        }

        XCTAssertFalse(BookReferenceCatalog.labyrinthIllustrations.isEmpty)
        XCTAssertTrue(missingAssetPlates.isEmpty, "Missing bundled assets: \(missingAssetPlates.map(\.assetName).joined(separator: ", "))")
    }

    func testSupportFacultyPackIncludesInkrestAndVellumCharts() throws {
        let corePack = try XCTUnwrap(SupportFacultyPackRegistry.enabledPacks.first { $0.id == SupportFacultyPackRegistry.corePackID })

        let inkrest = try XCTUnwrap(corePack.charts.first { $0.id == "inkrest-difficult-page-chart" })
        let vellum = try XCTUnwrap(corePack.charts.first { $0.id == "vellum-body-marginalia-chart" })

        XCTAssertEqual(inkrest.facultyEntityID, "dr-inkrest")
        XCTAssertEqual(inkrest.kind, .difficultPage)
        XCTAssertTrue(inkrest.forbiddenUses.contains("diagnosis"))
        XCTAssertTrue(inkrest.safetyLine.contains("feeling is not a verdict"))

        XCTAssertEqual(vellum.facultyEntityID, "dr-vellum")
        XCTAssertEqual(vellum.kind, .bodyMarginalia)
        XCTAssertTrue(vellum.forbiddenUses.contains("food shame"))
        XCTAssertTrue(vellum.reads.contains("HealthKit body signals"))
    }

    func testSupportFacultyChartsCanBeResolvedFromStoryTags() throws {
        let charts = SupportFacultyPackRegistry.charts(matching: ["body", "therapy-chart", "care"])

        XCTAssertTrue(charts.contains { $0.id == "inkrest-difficult-page-chart" })
        XCTAssertTrue(charts.contains { $0.id == "vellum-body-marginalia-chart" })
    }

    func testStoryScenePacketCarriesSelectedRelationships() {
        let packet = StoryScenePacketBuilder.packet(
            for: dayWithMusicSouvenir(),
            inputs: richInputs(),
            now: localDate(hour: 16)
        )

        XCTAssertFalse(packet.selectedRelationships.isEmpty)
        XCTAssertTrue(packet.relationshipPressures.contains { $0.contains("->") })
    }

    func testNarrativeSnapshotBiasesNextStoryPacketFromKeptEvents() {
        let photoEvent = NarrativeEventResolver.event(forKept: BookPage(
            id: "illuminated-kept",
            type: .illuminatedPhoto,
            createdAt: localDate(hour: 13),
            promptText: "Found in the Margins",
            userInput: "The Book kept the page: the cup glittered.",
            tags: ["photo", "marginalia"]
        ))
        let weatherEvent = NarrativeEventResolver.event(forKept: BookPage(
            id: "weather-kept",
            type: .weather,
            createdAt: localDate(hour: 14),
            promptText: "Weather Page",
            userInput: "The sky stayed bright.",
            tags: ["weather"]
        ))
        var inputs = richInputs()
        inputs.narrative = NarrativeSourceSnapshotBuilder.snapshot(
            from: [photoEvent, weatherEvent],
            beliefWeight: 51
        )

        let packet = StoryScenePacketBuilder.packet(
            for: emptyDay(),
            inputs: inputs,
            now: localDate(hour: 16)
        )

        XCTAssertTrue(packet.selectedEntities.contains { $0.id == "penny-blackletter" || $0.id == "weather-page" })
        XCTAssertTrue(packet.selectedThreads.contains { $0.id == "weather-in-the-stacks" || $0.id == "ordinary-magic" })
        XCTAssertTrue(packet.selectedRelationships.contains { $0.id == "penny-files-book" || $0.id == "weather-bleeds-book" })
    }

    func testStoryPageSurfaceCarriesScenePacketMetadata() throws {
        var inputs = richInputs()
        let draft = NarrativeOSPageSourceAdapter.draftCandidate(
            for: dayWithMusicSouvenir(),
            inputs: inputs,
            now: localDate(hour: 16)
        )
        var metadata = draft.payload.metadata
        metadata["storyScene"] = "The headphones entered the margins as a minor talisman."
        metadata["storyResultSliceOfLife"] = "The ordinary detail gained weight."
        metadata["storyResultProgressArc"] = "The current thread advanced one line."
        metadata["storyResultSurprise"] = "A related side door opened."
        inputs.preparedStoryPageSurface = SurfacePage(
            id: draft.id,
            type: draft.type,
            sourceID: draft.sourceID,
            intent: draft.intent,
            renderStyle: draft.renderStyle,
            score: draft.score,
            reason: draft.reason,
            prompt: draft.prompt,
            detail: draft.detail,
            payload: BookPagePayload(
                headline: draft.payload.headline,
                body: metadata["storyScene"] ?? draft.payload.body,
                metadata: metadata
            )
        )

        let pages = BookCurator.surfacedPages(
            for: dayWithMusicSouvenir(),
            inputs: inputs,
            now: localDate(hour: 16),
            limit: 12
        )

        let storyPage = try XCTUnwrap(pages.first { $0.type == .narrativeOS })

        XCTAssertEqual(storyPage.payload.metadata["choiceRoles"], "Slice of Life | Progress Arc | Something Surprising")
        XCTAssertNotNil(storyPage.payload.metadata["packetID"])
        XCTAssertNotNil(storyPage.payload.metadata["selectedThreads"])
        XCTAssertNotNil(storyPage.payload.metadata["selectedEntities"])
        XCTAssertNotNil(storyPage.payload.metadata["selectedRelationships"])
        XCTAssertNotNil(storyPage.payload.metadata["storyScene"])
    }

    func testWeatherPageKeptCreatesNarrativeEventForWeatherThread() {
        let page = BookPage(
            id: "weather-kept",
            type: .weather,
            createdAt: localDate(hour: 14),
            promptText: "The Weather Page has opened.",
            userInput: "The sky stayed clear and silver.",
            tags: ["weather"]
        )

        let event = NarrativeEventResolver.event(forKept: page)

        XCTAssertEqual(event.kind, .pageAnswered)
        XCTAssertEqual(event.effect.beliefDelta, 1)
        XCTAssertGreaterThan(event.effect.entityWeightDeltas["weather-page"] ?? 0, 0)
        XCTAssertGreaterThan(event.effect.threadWeightDeltas["weather-in-the-stacks"] ?? 0, 0)
        XCTAssertGreaterThan(event.effect.relationshipWeightDeltas["weather-bleeds-book"] ?? 0, 0)
    }

    func testIlluminatedPhotoKeptCreatesPennyEventAndTalismanHint() {
        let page = BookPage(
            id: "photo-kept",
            type: .illuminatedPhoto,
            createdAt: localDate(hour: 15),
            promptText: "Found in the Margins",
            userInput: "The Book kept the page: the lamp won.",
            tags: ["photo", "marginalia"]
        )

        let event = NarrativeEventResolver.event(forKept: page)

        XCTAssertGreaterThan(event.effect.entityWeightDeltas["penny-blackletter"] ?? 0, 0)
        XCTAssertGreaterThan(event.effect.relationshipWeightDeltas["penny-files-book"] ?? 0, 0)
        XCTAssertNotNil(event.effect.createdEntityHint)
    }

    func testStoryChoiceCreatesNarrativeEventWithChoiceEffect() throws {
        let packet = StoryScenePacketBuilder.packet(
            for: dayWithMusicSouvenir(),
            inputs: richInputs(),
            now: localDate(hour: 16)
        )
        let choice = try XCTUnwrap(packet.choices.first { $0.role == .progressArc })

        let event = NarrativeEventResolver.event(for: choice, packet: packet, at: localDate(hour: 16))

        XCTAssertEqual(event.kind, .choiceSelected)
        XCTAssertEqual(event.sourcePageType, .narrativeOS)
        XCTAssertEqual(event.effect.beliefDelta, choice.beliefDelta)
        XCTAssertFalse(event.effect.threadWeightDeltas.isEmpty)
    }

    func testKeptStoryPageCreatesChoiceEventsForEachTurn() {
        let page = BookPage(
            id: "story-kept",
            type: .narrativeOS,
            createdAt: localDate(hour: 17),
            promptText: "The Story Page is stirring.",
            userInput: """
            Turn 1

            The weather opened a small silver door.

            Chosen path: Slice of Life

            The ordinary detail gained weight.

            ---

            Turn 2

            The thread found the headphones again.

            Chosen path: Progress Arc

            The current thread advanced one line.

            ---

            Turn 3

            Penny found an extra note under the page.

            Chosen path: Something Surprising

            A related side door opened.
            """,
            tags: ["narrative-os", "weather", "music", "choice:sliceoflife", "choice:progressarc", "choice:surprise"]
        )

        let events = NarrativeEventResolver.events(forKept: page)

        XCTAssertEqual(events.count, 4)
        XCTAssertEqual(events.first?.kind, .pageAnswered)
        XCTAssertEqual(events.dropFirst().map(\.kind), [.choiceSelected, .choiceSelected, .choiceSelected])
        XCTAssertTrue(events.contains { $0.id.contains("sliceoflife") })
        XCTAssertTrue(events.contains { $0.id.contains("progressarc") })
        XCTAssertTrue(events.contains { $0.id.contains("surprise") })
        XCTAssertTrue(events.dropFirst().contains { ($0.effect.threadWeightDeltas["music-as-shelter"] ?? 0) > 0 })
    }

    func testNarrativeStoryFieldProjectionAccumulatesEvents() throws {
        let photoEvent = NarrativeEventResolver.event(forKept: BookPage(
            id: "photo-event",
            type: .illuminatedPhoto,
            createdAt: localDate(hour: 12),
            promptText: "Found in the Margins",
            userInput: "The Book kept the page: the chair waited.",
            tags: ["photo"]
        ))
        let packet = StoryScenePacketBuilder.packet(
            for: dayWithMusicSouvenir(),
            inputs: richInputs(),
            now: localDate(hour: 16)
        )
        let surprise = try XCTUnwrap(packet.choices.first { $0.role == .surprise })
        let choiceEvent = NarrativeEventResolver.event(for: surprise, packet: packet, at: localDate(hour: 16))

        let projection = NarrativeStoryFieldProjector.projection(events: [photoEvent, choiceEvent], baseBelief: 30)

        XCTAssertEqual(projection.belief, 32)
        XCTAssertTrue(projection.topEntityIDs.contains("penny-blackletter"))
        XCTAssertTrue(projection.topThreadIDs.contains("ordinary-magic"))
        XCTAssertTrue(projection.topRelationshipIDs.contains("penny-files-book"))
    }

    func testAboutYouSkipsAnsweredQuestionsFromEnabledPacks() throws {
        let day = emptyDay()
        let firstPass = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(selfFacts: []),
            now: localDate(hour: 10),
            limit: 12
        )
        let firstQuestion = try XCTUnwrap(firstPass.first { $0.type == .aboutYou })
        let questionID = try XCTUnwrap(firstQuestion.payload.metadata["questionID"])
        let packID = try XCTUnwrap(firstQuestion.payload.metadata["packID"])

        let answered = SelfFact(
            id: "\(packID):\(questionID)",
            questionID: questionID,
            question: firstQuestion.prompt,
            answer: "BJ",
            bookTranslation: "The Book knows this now.",
            sensitivity: .identity,
            usePermission: .privateContext,
            tags: ["identity"],
            createdAt: localDate(hour: 10),
            updatedAt: localDate(hour: 10)
        )
        let immediateSecondPass = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(selfFacts: [answered]),
            now: localDate(hour: 10),
            limit: 12
        )
        let laterSecondPass = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(selfFacts: [answered]),
            now: localDate(hour: 14),
            limit: 12
        )

        XCTAssertFalse(immediateSecondPass.contains { $0.type == .aboutYou })
        XCTAssertFalse(laterSecondPass.contains { $0.id == firstQuestion.id })
        XCTAssertTrue(laterSecondPass.contains { $0.type == .aboutYou })
    }

    func testBraidPageOnlySurfacesAtNightWithCapturedFragments() {
        let day = BookDay(
            id: "2026-06-01",
            date: localDate(hour: 0),
            pages: [
                BookPage(
                    id: "souvenir-1",
                    type: .souvenir,
                    createdAt: localDate(hour: 12),
                    promptText: "Catch one bright particular.",
                    userInput: "The coffee smelled like toasted sugar.",
                    tags: ["souvenir"]
                )
            ]
        )

        let afternoon = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(),
            now: localDate(hour: 15),
            limit: 8
        )
        let night = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(),
            now: localDate(hour: 21),
            limit: 8
        )

        XCTAssertFalse(afternoon.contains { $0.type == .bookOfYou })
        XCTAssertTrue(night.contains { $0.type == .bookOfYou })
    }

    func testDistressBiasesGentleRestFirst() {
        let day = BookDay(
            id: "2026-06-01",
            date: localDate(hour: 0),
            pages: [
                BookPage(
                    id: "hard-1",
                    type: .souvenir,
                    createdAt: localDate(hour: 8),
                    promptText: "One sentence.",
                    userInput: "A hard low morning.",
                    tags: ["low"]
                )
            ]
        )

        let pages = BookCurator.surfacedPages(
            for: day,
            inputs: richInputs(),
            now: localDate(hour: 10),
            limit: 3
        )

        XCTAssertEqual(pages.first?.type, .rest)
    }

    func testPageBeliefRaisesEligiblePageInCuratorRanking() throws {
        let diary = SurfacePage(
            id: "diary-test",
            type: .diary,
            sourceID: "diary-page",
            intent: .capture,
            renderStyle: .promptCard,
            score: 60,
            reason: "Diary is nearby.",
            prompt: "Diary",
            detail: "Diary",
            payload: BookPagePayload(headline: "Diary", body: "Diary")
        )
        let lore = SurfacePage(
            id: "lore-test",
            type: .lore,
            sourceID: "labyrinth-lore",
            intent: .importReference,
            renderStyle: .loreLetter,
            score: 62,
            reason: "Lore is nearby.",
            prompt: "Lore",
            detail: "Lore",
            payload: BookPagePayload(headline: "Lore", body: "Lore")
        )
        let profiles = BookPageSourceRegistry.beliefProfiles(ledger: ["diary-page": 50])
        let preferences = CuratorSurfacePreferences(
            pageBeliefProfiles: Dictionary(uniqueKeysWithValues: profiles.map { ($0.sourceID, $0) })
        )

        let ranked = BookCurator.rankedPages(
            from: [lore, diary],
            limit: 2,
            preferences: preferences
        )

        XCTAssertEqual(ranked.first?.page.sourceID, "diary-page")
    }

    func testAutomagicPageKeepsFloorWhenBeliefIsLow() {
        let fuel = SurfacePage(
            id: "fuel-test",
            type: .fuel,
            sourceID: "fuel-log",
            intent: .capture,
            renderStyle: .promptCard,
            score: 52,
            reason: "Fuel window.",
            prompt: "Fuel",
            detail: "Fuel",
            payload: BookPagePayload(headline: "Fuel", body: "Fuel")
        )
        let profiles = BookPageSourceRegistry.beliefProfiles(ledger: ["fuel-log": -36])
        let preferences = CuratorSurfacePreferences(
            pageBeliefProfiles: Dictionary(uniqueKeysWithValues: profiles.map { ($0.sourceID, $0) })
        )

        XCTAssertGreaterThanOrEqual(preferences.adjustedScore(for: fuel), 68)
    }

    private func emptyDay() -> BookDay {
        BookDay(id: "2026-06-01", date: localDate(hour: 0), pages: [])
    }

    private func dayWithMusicSouvenir() -> BookDay {
        BookDay(
            id: "2026-06-01",
            date: localDate(hour: 0),
            pages: [
                BookPage(
                    id: "music-souvenir",
                    type: .souvenir,
                    createdAt: localDate(hour: 12),
                    promptText: "Catch one bright particular.",
                    userInput: "The sound of Spotify is bopping me along through the headphones.",
                    tags: ["souvenir", "music"]
                )
            ]
        )
    }

    private func richInputs(selfFacts: [SelfFact] = []) -> BookSourceInputs {
        BookSourceInputs(
            body: BodySourceSignal(
                status: "LOW",
                score: 24,
                phrase: "The lamps are low in the stacks. This is a day for small thresholds."
            ),
            weather: WeatherSourceSignal(
                phrase: "Now: 64 F. Forecast: rain later.",
                source: "Open-Meteo",
                currentTemperature: "64 F",
                forecast: "rain later",
                conditionSymbolName: "cloud.rain"
            ),
            enchantedWeather: EnchantedWeatherSignal(
                summary: "64 F, rain later",
                enchantified: "Rain is tapping at the margins.",
                selector: "test-weather",
                symbolName: "cloud.rain"
            ),
            narrative: NarrativeSourceSnapshot(activeThreadCount: 2, relationshipCount: 1, beliefWeight: 42),
            selfFacts: selfFacts,
            selectedWonderCompass: nil,
            selectedWonderCompassSelector: nil
        )
    }

    private func localDate(hour: Int, minute: Int = 0) -> Date {
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = hour
        components.minute = minute
        components.second = 0
        return Calendar.current.date(from: components) ?? Date()
    }
}
