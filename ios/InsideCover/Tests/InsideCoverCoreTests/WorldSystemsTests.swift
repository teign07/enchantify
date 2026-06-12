import XCTest
@testable import InsideCoverCore

final class WorldSystemsTests: XCTestCase {
    private var utcCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC")!
        return calendar
    }

    private func date(_ year: Int, _ month: Int, _ day: Int, hour: Int, calendar: Calendar) -> Date {
        calendar.date(from: DateComponents(year: year, month: month, day: day, hour: hour))!
    }

    // MARK: Moon

    func testMoonPhaseAtReferenceNewMoonIsNew() {
        var components = DateComponents(year: 2000, month: 1, day: 6, hour: 18, minute: 14)
        components.timeZone = TimeZone(identifier: "UTC")
        let reference = Calendar(identifier: .gregorian).date(from: components)!
        let phase = MoonPhaseCalendar.phase(on: reference)
        XCTAssertEqual(phase.name, "New Moon")
        XCTAssertLessThan(phase.illuminatedFraction, 0.02)
    }

    func testMoonPhaseHalfCycleLaterIsFull() {
        var components = DateComponents(year: 2000, month: 1, day: 6, hour: 18, minute: 14)
        components.timeZone = TimeZone(identifier: "UTC")
        let reference = Calendar(identifier: .gregorian).date(from: components)!
        let halfCycle = reference.addingTimeInterval(MoonPhaseCalendar.synodicMonthDays / 2 * 86_400)
        let phase = MoonPhaseCalendar.phase(on: halfCycle)
        XCTAssertEqual(phase.name, "Full Moon")
        XCTAssertGreaterThan(phase.illuminatedFraction, 0.98)
    }

    // MARK: Academy schedule

    func testMondayMorningIsArtOfTheGlint() {
        let calendar = utcCalendar
        // 2026-06-08 is a Monday.
        let monday = date(2026, 6, 8, hour: 9, calendar: calendar)
        let session = AcademyScheduleRegistry.sessionInProgress(at: monday, calendar: calendar)
        XCTAssertEqual(session?.session.id, "art-of-the-glint")
        XCTAssertEqual(session?.block, "morning")
    }

    func testMondayEveningIsInkwrightSociety() {
        let calendar = utcCalendar
        let monday = date(2026, 6, 8, hour: 19, calendar: calendar)
        let session = AcademyScheduleRegistry.sessionInProgress(at: monday, calendar: calendar)
        XCTAssertEqual(session?.session.id, "inkwright-society")
        XCTAssertEqual(session?.session.kind, .club)
    }

    func testSundayAfternoonHasNoSession() {
        let calendar = utcCalendar
        // 2026-06-07 is a Sunday; no afternoon class on Sundays.
        let sunday = date(2026, 6, 7, hour: 13, calendar: calendar)
        XCTAssertNil(AcademyScheduleRegistry.sessionInProgress(at: sunday, calendar: calendar))
    }

    func testWednesdayHasNoClub() {
        let calendar = utcCalendar
        // 2026-06-10 is a Wednesday.
        let wednesday = date(2026, 6, 10, hour: 20, calendar: calendar)
        XCTAssertNil(AcademyScheduleRegistry.sessionInProgress(at: wednesday, calendar: calendar))
    }

    func testEveryScheduledSessionExists() {
        for (_, plan) in AcademyScheduleRegistry.week {
            if let id = plan.morning {
                XCTAssertNotNil(AcademyScheduleRegistry.classes[id], "missing class \(id)")
            }
            if let id = plan.afternoon {
                XCTAssertNotNil(AcademyScheduleRegistry.classes[id], "missing class \(id)")
            }
            if let id = plan.club {
                XCTAssertNotNil(AcademyScheduleRegistry.clubs[id], "missing club \(id)")
            }
        }
    }

    // MARK: Page pack templates

    func testTemplateRendererSubstitutesSignals() {
        var inputs = BookSourceInputs.empty
        inputs.weather = WeatherSourceSignal(phrase: "light rain, 54F", source: "test")
        inputs.selfFacts = [
            SelfFact(
                id: "f1",
                questionID: "onboarding-name",
                question: "What should the Book call you?",
                answer: "Avery",
                bookTranslation: "Avery",
                sensitivity: .delight,
                usePermission: .privateContext,
                tags: ["name"],
                createdAt: Date(),
                updatedAt: Date()
            )
        ]
        let day = BookDay.today()
        let rendered = PageTemplateRenderer.render(
            "Hello {playerName}: {weather} under a {moon}.",
            day: day,
            inputs: inputs
        )
        XCTAssertTrue(rendered.contains("Avery"))
        XCTAssertTrue(rendered.contains("light rain, 54F"))
        XCTAssertFalse(rendered.contains("{moon}"))
        XCTAssertFalse(rendered.contains("{playerName}"))
    }

    func testBundledPackArchetypesAreWellFormed() {
        let archetypes = PageArchetypePackRegistry.bundledPacks.flatMap(\.archetypes)
        XCTAssertFalse(archetypes.isEmpty)
        for archetype in archetypes {
            XCTAssertFalse(archetype.id.isEmpty)
            XCTAssertFalse(archetype.bodyTemplate.isEmpty)
            XCTAssertGreaterThan(archetype.cadenceHours, 0)
            if let hours = archetype.activeHours {
                XCTAssertTrue(hours.allSatisfy { (0..<24).contains($0) })
            }
        }
    }

    // MARK: Margin tutor

    func testMarginTutorLedgerRoundTrips() {
        let seen: Set<String> = ["glow-menu", "seal-body"]
        let decoded = MarginTutorLedger.seenIDs(from: MarginTutorLedger.encode(seen))
        XCTAssertEqual(decoded, seen)
        XCTAssertEqual(MarginTutorLedger.seenIDs(from: "not json"), [])
    }

    func testMarginTutorCatalogCoversCoreTouches() {
        for id in ["glow-menu", "seal-body", "seal-weather", "seal-location", "keep-page", "story-page", "flyleaf"] {
            XCTAssertNotNil(MarginTutorCatalog.note(for: id), "missing tutor note \(id)")
        }
    }

    // MARK: Stable hashing

    func testStableHashIsDeterministic() {
        XCTAssertEqual("wonder".stableHash, "wonder".stableHash)
        XCTAssertNotEqual("wonder".stableHash, "wander".stableHash)
        XCTAssertEqual(42.stableScramble, 42.stableScramble)
        XCTAssertNotEqual(42.stableScramble, 43.stableScramble)
    }

    // MARK: Memory consolidation

    func testConsolidatorMergesNearDuplicates() {
        func memory(_ id: String, _ summary: String, daysAgo: Double, weight: Int = 2) -> NarrativeEntityMemory {
            NarrativeEntityMemory(
                id: id,
                entityID: "penny-blackletter",
                sourceEventID: "e-\(id)",
                sourcePageID: nil,
                summary: summary,
                tags: [],
                narrativeWeight: weight,
                createdAt: Date().addingTimeInterval(-daysAgo * 86_400)
            )
        }
        let memories = [
            memory("a", "Penny Blackletter remembers: you mentioned the harbor lights", daysAgo: 6),
            memory("b", "Penny Blackletter remembers: you mentioned the harbor lights again", daysAgo: 2),
            memory("c", "Penny Blackletter remembers: the photograph of the kettle", daysAgo: 1)
        ]
        let consolidated = NarrativeEntityMemoryConsolidator.consolidate(memories)
        XCTAssertEqual(consolidated.count, 2)
        let harbor = consolidated.first { $0.summary.contains("harbor") }
        XCTAssertNotNil(harbor)
        XCTAssertGreaterThan(harbor?.narrativeWeight ?? 0, 2)
    }

    func testConsolidatorKeepsDistinctMemoriesApart() {
        func memory(_ id: String, entity: String, _ summary: String) -> NarrativeEntityMemory {
            NarrativeEntityMemory(
                id: id,
                entityID: entity,
                sourceEventID: "e-\(id)",
                sourcePageID: nil,
                summary: summary,
                tags: [],
                narrativeWeight: 2,
                createdAt: Date()
            )
        }
        let memories = [
            memory("a", entity: "penny-blackletter", "Penny remembers: the harbor lights"),
            memory("b", entity: "dr-inkrest", "Inkrest remembers: the harbor lights")
        ]
        XCTAssertEqual(NarrativeEntityMemoryConsolidator.consolidate(memories).count, 2)
    }

    // MARK: The knock

    func testKnockNotesKnowThings() {
        // Persistence gets dry treatment.
        XCTAssertTrue(BannerKnockNotes.note(greyLevel: 0, ascendantChapterName: nil, hour: 12, moonName: "New Moon", knocksThisSession: 7, roll: 0).contains("whole shelf"))
        // Grey days get kindness first.
        XCTAssertTrue(BannerKnockNotes.note(greyLevel: 2, ascendantChapterName: nil, hour: 12, moonName: "New Moon", knocksThisSession: 1, roll: 0).contains("knock helps"))
        // Deep night knows about the Nocturne.
        XCTAssertTrue(BannerKnockNotes.note(greyLevel: 0, ascendantChapterName: nil, hour: 2, moonName: "New Moon", knocksThisSession: 1, roll: 1).contains("Nocturne"))
        // Daytime pool rotates by roll.
        let a = BannerKnockNotes.note(greyLevel: 0, ascendantChapterName: nil, hour: 12, moonName: "New Moon", knocksThisSession: 1, roll: 1)
        let b = BannerKnockNotes.note(greyLevel: 0, ascendantChapterName: nil, hour: 12, moonName: "New Moon", knocksThisSession: 1, roll: 2)
        XCTAssertNotEqual(a, b)
    }

    // MARK: Fuel arithmetic

    func testFuelParserSplitsAndQuantifies() {
        let items = FuelParser.items(from: "Two eggs, toast with butter and coffee")
        XCTAssertEqual(items.count, 4)
        XCTAssertEqual(items[0], FuelItem(name: "eggs", quantity: 2))
        XCTAssertEqual(items[1].name, "toast")
        XCTAssertEqual(items[2].name, "butter")
        XCTAssertEqual(items[3].name, "coffee")
    }

    func testFuelParserHandlesNumberWordsAndFiller() {
        let items = FuelParser.items(from: "a bowl of oatmeal, half banana")
        XCTAssertEqual(items.first?.name, "oatmeal")
        XCTAssertEqual(items.first?.quantity, 1)
        XCTAssertEqual(items.last, FuelItem(name: "banana", quantity: 0.5))
    }

    func testPortionScalingUsesCommonPortions() {
        // Eggs: 50g portion, so two eggs = 100g = exactly the per-100g values.
        let per100g = NutritionEstimate(kilocalories: 143, protein: 12.4, carbohydrates: 0.96, fat: 9.96)
        let scaled = FuelParser.scale(per100g: per100g, item: FuelItem(name: "eggs", quantity: 2))
        XCTAssertEqual(scaled.kilocalories, 143, accuracy: 0.1)
        // Unknown food defaults to 100g.
        let unknown = FuelParser.scale(per100g: per100g, item: FuelItem(name: "mystery casserole", quantity: 1))
        XCTAssertEqual(unknown.kilocalories, 143, accuracy: 0.1)
    }

    func testEstimateChartLineIsHonestAboutRoughness() {
        let estimate = NutritionEstimate(kilocalories: 412.4, protein: 21.6, carbohydrates: 38.2, fat: 17.8)
        XCTAssertTrue(estimate.chartLine.contains("412 kcal"))
        XCTAssertTrue(estimate.chartLine.contains("rough"))
    }

    // MARK: Nocturne Folio

    func testNocturneFolioUnlocksContentAndSparks() {
        defer { PackEntitlements.ownedPackIDs = [] }
        PackEntitlements.ownedPackIDs = []
        XCTAssertFalse(PageArchetypePackRegistry.archetypes().contains { $0.id == "last-light" })
        let baseCount = WonderSparkRegistry.sparks.count
        PackEntitlements.ownedPackIDs = ["nocturne-folio"]
        XCTAssertTrue(PageArchetypePackRegistry.archetypes().contains { $0.id == "last-light" })
        XCTAssertEqual(WonderSparkRegistry.sparks.count, baseCount + WonderSparkRegistry.nocturneSparks.count)
    }

    // MARK: The Nothing

    func testGreyLevelRespectsTheKindnessRules() {
        XCTAssertEqual(NothingTide.greyLevel(quietDays: 5, narrativeHeat: 0, distressActive: true), 0, "distress silences the Nothing absolutely")
        XCTAssertEqual(NothingTide.greyLevel(quietDays: 0, narrativeHeat: 0, distressActive: false), 0)
        XCTAssertEqual(NothingTide.greyLevel(quietDays: 1, narrativeHeat: 0, distressActive: false), 1)
        XCTAssertEqual(NothingTide.greyLevel(quietDays: 3, narrativeHeat: 0, distressActive: false), 2)
        XCTAssertEqual(NothingTide.greyLevel(quietDays: 5, narrativeHeat: 0, distressActive: false), 3)
        XCTAssertEqual(NothingTide.greyLevel(quietDays: 3, narrativeHeat: 8, distressActive: false), 1, "a hot story field pushes the grey back")
    }

    func testGreyStorySignalsExistOnlyWhenGreyIsUp() {
        XCTAssertNil(NothingTide.storySignal(forGreyLevel: 0))
        XCTAssertNil(NothingTide.storySignal(forGreyLevel: 1))
        XCTAssertNotNil(NothingTide.storySignal(forGreyLevel: 2))
        XCTAssertNotNil(NothingTide.returnLine(forGreyLevel: 2))
        XCTAssertNil(NothingTide.returnLine(forGreyLevel: 0))
    }

    // MARK: Story Arcs

    private func threadEvent(_ threadID: String, hoursAgo: Double) -> NarrativeEvent {
        NarrativeEvent(
            id: "arc-test-\(threadID)-\(hoursAgo)",
            kind: .pageKept,
            sourcePageType: .diary,
            sourcePageID: nil,
            createdAt: Date().addingTimeInterval(-hoursAgo * 3600),
            summary: "test",
            tags: [],
            effect: NarrativeEventEffect(threadWeightDeltas: [threadID: 2])
        )
    }

    func testArcPromotionNeedsSustainedHeat() {
        let threadID = NarrativePackRegistry.threads.first { !ArcKeeper.ambientThreadIDs.contains($0.id) }!.id
        let cold = ArcKeeper.evaluate(current: nil, events: [threadEvent(threadID, hoursAgo: 2)], lastCompletedThreadID: nil)
        XCTAssertNil(cold.arc)
        let hotEvents = [threadEvent(threadID, hoursAgo: 2), threadEvent(threadID, hoursAgo: 20), threadEvent(threadID, hoursAgo: 40)]
        let hot = ArcKeeper.evaluate(current: nil, events: hotEvents, lastCompletedThreadID: nil)
        XCTAssertEqual(hot.arc?.threadID, threadID)
        XCTAssertEqual(hot.arc?.phase, .rising)
        XCTAssertNotNil(hot.announcement)
        let cooled = ArcKeeper.evaluate(current: nil, events: hotEvents, lastCompletedThreadID: threadID)
        XCTAssertNil(cooled.arc, "the just-completed arc thread is on cooldown")
    }

    func testArcAdvancesOnlyWithTimeAndActivity() {
        let threadID = NarrativePackRegistry.threads.first { !ArcKeeper.ambientThreadIDs.contains($0.id) }!.id
        let now = Date()
        var arc = StoryArc(threadID: threadID, title: "T", phase: .rising, startedAt: now.addingTimeInterval(-5 * 86_400), phaseAdvancedAt: now.addingTimeInterval(-3 * 86_400))
        // Time but no activity: holds.
        let held = ArcKeeper.evaluate(current: arc, events: [], lastCompletedThreadID: nil, now: now)
        XCTAssertEqual(held.arc?.phase, .rising)
        // Time and activity: climax.
        let active = [threadEvent(threadID, hoursAgo: 10), threadEvent(threadID, hoursAgo: 30)]
        let advanced = ArcKeeper.evaluate(current: arc, events: active, lastCompletedThreadID: nil, now: now)
        XCTAssertEqual(advanced.arc?.phase, .climax)
        // Fading completes by time alone.
        arc.phase = .fading
        arc.phaseAdvancedAt = now.addingTimeInterval(-3 * 86_400)
        let done = ArcKeeper.evaluate(current: arc, events: [], lastCompletedThreadID: nil, now: now)
        XCTAssertNil(done.arc)
        XCTAssertNotNil(done.announcement)
    }

    func testPacketCarriesTheCurrentArc() {
        let threadID = NarrativePackRegistry.threads.first { !ArcKeeper.ambientThreadIDs.contains($0.id) }!.id
        var inputs = BookSourceInputs.empty
        inputs.currentArc = StoryArc(threadID: threadID, title: "Test Arc", phase: .climax, startedAt: Date(), phaseAdvancedAt: Date())
        let packet = StoryScenePacketBuilder.packet(for: BookDay.today(), inputs: inputs)
        XCTAssertEqual(packet.selectedThreads.first?.id, threadID, "the arc thread leads the scene")
        XCTAssertTrue(packet.realSignals.contains { $0.contains("CURRENT ARC") && $0.contains("CLIMAX") })
    }

    // MARK: The BookShop

    func testCatalogListingsAreWellFormed() {
        var seenProducts = Set<String>()
        for listing in BookShopCatalog.listings {
            XCTAssertTrue(listing.productID.hasPrefix("com.openclaw.enchantify.insidecover.pack."), listing.id)
            XCTAssertTrue(seenProducts.insert(listing.productID).inserted, "duplicate product \(listing.productID)")
            XCTAssertFalse(listing.goblinPitch.isEmpty)
            XCTAssertFalse(listing.contents.isEmpty)
        }
    }

    func testEntitlementsUnlockLockedPacks() {
        defer { PackEntitlements.ownedPackIDs = [] }
        let locked = StoryFormPack(
            id: "test-locked-looms", displayName: "Test", version: 1, author: "t",
            availability: "locked", forms: [], genres: []
        )
        XCTAssertTrue(locked.isLocked)
        PackEntitlements.ownedPackIDs = []
        XCTAssertFalse(PackEntitlements.isUnlocked(locked.id))
        PackEntitlements.ownedPackIDs.insert(locked.id)
        XCTAssertTrue(PackEntitlements.isUnlocked(locked.id))
    }

    func testVaultCarriesOwnedPacks() throws {
        var data = PlayerVaultData()
        data.ownedPacks = ["nocturne-folio"]
        let decoded = try JSONDecoder().decode(PlayerVaultData.self, from: JSONEncoder().encode(data))
        XCTAssertEqual(decoded.ownedPacks, ["nocturne-folio"])
    }

    // MARK: Wonder sparks

    func testSparkPoolIsLargeAndWellFormed() {
        XCTAssertGreaterThanOrEqual(WonderSparkRegistry.sparks.count, 60)
        var seen = Set<String>()
        for spark in WonderSparkRegistry.sparks {
            XCTAssertTrue(spark.text.lowercased().hasPrefix("i wonder"), spark.id)
            XCTAssertTrue(spark.text.hasSuffix("?"), spark.id)
            XCTAssertFalse(spark.modes.isEmpty, spark.id)
            XCTAssertTrue(seen.insert(spark.id).inserted, "duplicate spark id \(spark.id)")
        }
        // Every concierge mode has a real pool to draw from.
        for mode in WonderConciergeMode.allCases {
            let pool = WonderSparkRegistry.sparks.filter { $0.modes.contains(mode) }
            XCTAssertGreaterThanOrEqual(pool.count, 8, "mode \(mode) pool too small")
        }
    }

    func testSparksRotateAcrossSlots() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC")!
        let morning = calendar.date(from: DateComponents(year: 2026, month: 6, day: 11, hour: 8))!
        var picks = Set<String>()
        for dayOffset in 0..<5 {
            let when = calendar.date(byAdding: .day, value: dayOffset, to: morning)!
            picks.insert(WonderSparkRegistry.spark(for: .closeToHome, inputs: .empty, now: when, dayID: "day-\(dayOffset)"))
        }
        XCTAssertGreaterThanOrEqual(picks.count, 3, "five days should yield several different sparks")
    }

    func testRainLeansTowardRainSparks() {
        var inputs = BookSourceInputs.empty
        inputs.weather = WeatherSourceSignal(phrase: "steady rain, 52F", source: "test")
        // Across several days, rain context should surface a rain-tagged
        // spark at least once for the modes that carry them.
        var sawRainSpark = false
        for day in 0..<8 {
            let text = WonderSparkRegistry.spark(for: .vibe, inputs: inputs, dayID: "rain-day-\(day)")
            if text.contains("rain") || text.contains("percussion") {
                sawRainSpark = true
            }
        }
        XCTAssertTrue(sawRainSpark)
    }

    // MARK: Compass venture reading

    func testDepletedEnergyStaysHome() {
        XCTAssertEqual(
            CompassVenture.decide(energyText: "10% - exhausted", considerations: "", timeLimit: "2 hours", hasPlaces: true, roll: 0.99),
            .homebound
        )
        XCTAssertEqual(
            CompassVenture.decide(energyText: "completely wiped", considerations: "", timeLimit: "an hour", hasPlaces: true, roll: 0.01),
            .homebound
        )
    }

    func testConsiderationsForceHomeRegardlessOfEnergy() {
        XCTAssertEqual(
            CompassVenture.decide(energyText: "90% - great", considerations: "kids napping, can't leave", timeLimit: "2 hours", hasPlaces: true, roll: 0.01),
            .homebound
        )
    }

    func testSteadyEnergySometimesVenturesSometimesNot() {
        let out = CompassVenture.decide(energyText: "60% - okay", considerations: "", timeLimit: "an hour", hasPlaces: true, roll: 0.2)
        let home = CompassVenture.decide(energyText: "60% - okay", considerations: "", timeLimit: "an hour", hasPlaces: true, roll: 0.9)
        XCTAssertEqual(out, .destination)
        XCTAssertEqual(home, .neighborhood)
    }

    func testShortTimeLimitCapsTheVenture() {
        XCTAssertEqual(
            CompassVenture.decide(energyText: "85% - energized", considerations: "", timeLimit: "10 minutes", hasPlaces: true, roll: 0.01),
            .neighborhood
        )
    }

    func testNoPlacesMeansNoNamedDestination() {
        XCTAssertEqual(
            CompassVenture.decide(energyText: "85% - energized", considerations: "", timeLimit: "2 hours", hasPlaces: false, roll: 0.01),
            .neighborhood
        )
    }

    // MARK: Story forms

    func testStoryFormRegistryIsWellFormed() {
        XCTAssertGreaterThanOrEqual(StoryFormRegistry.forms.count, 6)
        XCTAssertGreaterThanOrEqual(StoryFormRegistry.genres.count, 8)
        for form in StoryFormRegistry.forms {
            XCTAssertGreaterThanOrEqual(form.beats.count, 3, "\(form.id) needs at least 3 beats")
        }
        for genre in StoryFormRegistry.genres {
            XCTAssertFalse(genre.lens.isEmpty)
        }
    }

    func testStoryFormSelectionAvoidsRecentForm() {
        let now = Date()
        let first = StoryFormRegistry.select(
            tags: [], surfaceHistory: [:], ascendantChapterID: nil,
            dayID: "2026-06-11", slot: "slot-a", now: now
        )
        var history: [String: SurfaceHistoryRecord] = [:]
        history["form:\(first.form.id)"] = SurfaceHistoryRecord(lastShownAt: now, recentShowCount: 2)
        let second = StoryFormRegistry.select(
            tags: [], surfaceHistory: history, ascendantChapterID: nil,
            dayID: "2026-06-11", slot: "slot-a", now: now
        )
        XCTAssertNotEqual(first.form.id, second.form.id, "the just-used form should step back")
    }

    func testPacketCarriesFormAndGenre() {
        let packet = StoryScenePacketBuilder.packet(for: BookDay.today(), inputs: .empty)
        XCTAssertNotNil(packet.storyFormID)
        XCTAssertFalse(packet.storyFormBeats?.isEmpty ?? true)
        XCTAssertNotNil(packet.storyGenreLens)
    }

    func testGenreSelectionFollowsMoodTags() {
        let pick = StoryFormRegistry.select(
            tags: ["rain", "evening", "tea"], surfaceHistory: [:],
            ascendantChapterID: nil, dayID: "d", slot: "s"
        )
        XCTAssertEqual(pick.genre.id, "cozy-mystery", "rainy evening tea should brew a cozy mystery")
    }

    // MARK: Real-place electives

    func testOfferSurfaceCarriesNearbyPlaces() {
        let adapter = ElectivePageSourceAdapter()
        var inputs = BookSourceInputs.empty
        inputs.nearbyPlaces = [
            LocalPlaceSignal(id: "p1", name: "Tom's Diner", category: "diner", distanceLabel: "1.2 km", locality: "Riverside")
        ]
        inputs.selfFacts = []
        let day = BookDay.today()
        let noon = Calendar.current.date(bySettingHour: 12, minute: 0, second: 0, of: Date())!
        let pages = adapter.candidates(for: day, context: CuratorContext.make(for: day), inputs: inputs, now: noon)
        if let offer = pages.first(where: { $0.payload.metadata["electiveOffer"] == "true" }) {
            XCTAssertTrue(offer.payload.metadata["nearbyPlaces"]?.contains("Tom's Diner") == true)
        }
        // Either an offer surfaced carrying the place, or none surfaced
        // (cadence-gated) — but never an offer without the places line.
        for offer in pages where offer.payload.metadata["electiveOffer"] == "true" {
            XCTAssertNotNil(offer.payload.metadata["nearbyPlaces"])
        }
    }

    func testCharacterLetterUsesOnboardingPlayerName() {
        var inputs = BookSourceInputs.empty
        inputs.selfFacts = [
            SelfFact(
                id: "onboarding:onboarding-name",
                questionID: "onboarding-name",
                question: "What should the Book call you?",
                answer: "Beej",
                bookTranslation: "Beej",
                sensitivity: .delight,
                usePermission: .privateContext,
                tags: ["name", "identity", "onboarding"],
                createdAt: Date(),
                updatedAt: Date()
            ),
            SelfFact(
                id: "core-self-knowledge:called",
                questionID: "called",
                question: "What do you like to be called?",
                answer: "The Later Name",
                bookTranslation: "The Book may call you The Later Name.",
                sensitivity: .identity,
                usePermission: .quoteAllowed,
                tags: ["name", "identity"],
                createdAt: Date(),
                updatedAt: Date()
            )
        ]
        let entity = NarrativePackRegistry.entities.first { $0.id == "penny-blackletter" }!
        let surface = CharacterLetterPageGenerator.draftCandidate(
            for: entity,
            source: BookPageSourceRegistry.source(for: .letter),
            day: BookDay.today(),
            inputs: inputs,
            now: Date()
        )

        XCTAssertEqual(surface.payload.metadata["playerName"], "Beej")
        XCTAssertTrue(surface.payload.body.contains("Address the player as: Beej"))
        XCTAssertFalse(surface.payload.body.contains("[Player Name]"))
    }

    func testChapterTalismanBeliefMovesTargetOwnAndRivalTalismans() {
        let penny = NarrativePackRegistry.entities.first { $0.id == "penny-blackletter" }!
        let give = ChapterTalismanBeliefMoves.giveMove(for: penny)
        XCTAssertEqual(give?.targetTalismanID, "wind-cipher")
        XCTAssertEqual(give?.ledgerDelta, 1)
        XCTAssertEqual(give?.ledgerToken, "wind-cipher:1")

        let take = ChapterTalismanBeliefMoves.takeMove(for: penny, seed: 42)
        XCTAssertNotNil(take)
        XCTAssertNotEqual(take?.targetTalismanID, "wind-cipher")
        if take?.succeeded == true {
            XCTAssertEqual(take?.ledgerDelta, -1)
            XCTAssertTrue(take?.ledgerToken?.hasSuffix(":-1") == true)
        } else {
            XCTAssertEqual(take?.ledgerDelta, 0)
            XCTAssertNil(take?.ledgerToken)
        }
    }

    func testCharacterLetterCanCarryCountingChapterTalismanDelta() throws {
        let entity = NarrativePackRegistry.entities.first { $0.id == "penny-blackletter" }!
        let source = BookPageSourceRegistry.source(for: .letter)
        let candidate = (0..<80).compactMap { index -> SurfacePage? in
            let now = Calendar(identifier: .gregorian).date(
                from: DateComponents(year: 2026, month: 6, day: 11, hour: 9)
            )!
            let day = BookDay(id: "test-day-\(index)", date: now, pages: [])
            let surface = CharacterLetterPageGenerator.draftCandidate(
                for: entity,
                source: source,
                day: day,
                inputs: .empty,
                now: now
            )
            return surface.payload.metadata["chapterTalismanDeltas"]?.isEmpty == false ? surface : nil
        }.first

        let surface = try XCTUnwrap(candidate)
        XCTAssertTrue(surface.payload.body.contains("Chapter talisman move:"))
        XCTAssertFalse(surface.payload.metadata["chapterTalismanMoves"]?.isEmpty ?? true)
        XCTAssertFalse(surface.payload.metadata["chapterTalismanDeltas"]?.isEmpty ?? true)
    }

    func testAttentionMissionsJoinPlayfulMissionRegistry() {
        XCTAssertGreaterThanOrEqual(PlayfulMissionRegistry.attentionMissions.count, 40)
        XCTAssertTrue(PlayfulMissionRegistry.missions.contains { $0.id == "body-heartbeat-location" })
        XCTAssertTrue(PlayfulMissionRegistry.missions.contains { $0.id == "light-route" })
        XCTAssertTrue(PlayfulMissionRegistry.missions.contains { $0.id == "strange-technical-miracle" })
    }

    func testPlayfulMissionRegistryStillReturnsSenseMission() {
        let mission = PlayfulMissionRegistry.mission(
            for: BookDay.today(),
            inputs: .empty,
            now: Date(timeIntervalSinceReferenceDate: 123_456)
        )

        XCTAssertFalse(mission.id.isEmpty)
        XCTAssertFalse(mission.prompt.isEmpty)
        XCTAssertFalse(mission.proofPrompt.isEmpty)
    }

    func testFallbackOfferUsesRealPlaceWhenAvailable() {
        let surface = SurfacePage(
            id: "offer", type: .elective, sourceID: "unwritten-elective",
            prompt: "p", detail: "d",
            payload: BookPagePayload(headline: "h", body: "b", metadata: [
                "senderName": "Penny Blackletter",
                "senderInterest": "household loyalty",
                "nearbyPlaces": "Tom's Diner (diner, 1.2 km, Riverside)\nMarigold's Bakery (bakery, 800 m, Riverside)"
            ])
        )
        let offer = ElectiveOfferFallback.offer(surface: surface)
        XCTAssertTrue(offer.ask.contains("Tom's Diner"), offer.ask)
        XCTAssertTrue(offer.title.contains("Tom's Diner"))
    }

    func testFallbackOfferStaysGenericWithoutPlaces() {
        let surface = SurfacePage(
            id: "offer", type: .elective, sourceID: "unwritten-elective",
            prompt: "p", detail: "d",
            payload: BookPagePayload(headline: "h", body: "b", metadata: ["senderName": "Zara Finch"])
        )
        let offer = ElectiveOfferFallback.offer(surface: surface)
        XCTAssertFalse(offer.ask.contains("(")) // no leaked formatting
        XCTAssertTrue(offer.ask.contains("your town"))
    }

    // MARK: Curator awareness

    func testFatiguePenaltyDecaysOverTime() {
        let now = Date()
        var history: [String: SurfaceHistoryRecord] = [:]
        history["cast:compassion"] = SurfaceHistoryRecord(lastShownAt: now.addingTimeInterval(-3600), recentShowCount: 1)
        let fresh = CuratorVarietyGovernor.fatiguePenalty(forKey: "cast:compassion", history: history, now: now)
        history["cast:compassion"] = SurfaceHistoryRecord(lastShownAt: now.addingTimeInterval(-5 * 86_400), recentShowCount: 1)
        let stale = CuratorVarietyGovernor.fatiguePenalty(forKey: "cast:compassion", history: history, now: now)
        XCTAssertGreaterThan(fresh, 25)
        XCTAssertLessThan(stale, 8)
        XCTAssertEqual(CuratorVarietyGovernor.fatiguePenalty(forKey: "never-shown", history: history, now: now), 0)
    }

    func testRepeatedlyShownContentLosesToFreshContent() {
        let now = Date()
        func candidate(_ id: String, entityID: String, score: Int) -> SurfacePage {
            SurfacePage(
                id: id, type: .castMember, sourceID: "cast-member-page",
                score: score, prompt: id, detail: "",
                payload: BookPagePayload(headline: id, body: "", metadata: ["entityID": entityID])
            )
        }
        let tired = candidate("a", entityID: "compassion", score: 70)
        let fresh = candidate("b", entityID: "serenity-brown", score: 60)
        var mood = CuratorMood.neutral
        mood.surfaceHistory = ["cast:compassion": SurfaceHistoryRecord(lastShownAt: now.addingTimeInterval(-3600), recentShowCount: 4)]
        let ranked = BookCurator.rankedPages(from: [tired, fresh], limit: 2, mood: mood, now: now)
        XCTAssertEqual(ranked.first?.page.id, "b", "fatigued content should yield to fresh content")
    }

    func testFinalPickPrefersTypeDiversity() {
        func page(_ id: String, _ type: BookPageType, score: Int) -> SurfacePage {
            SurfacePage(id: id, type: type, sourceID: nil, score: score, prompt: id, detail: "",
                        payload: BookPagePayload(headline: id, body: ""))
        }
        let ranked = BookCurator.rankedPages(
            from: [page("q1", .quip, score: 90), page("q2", .quip, score: 88), page("d1", .diary, score: 60)],
            limit: 2
        )
        XCTAssertEqual(Set(ranked.map(\.page.type)).count, 2, "two card slots should hold two kinds")
    }

    func testCastRotationExcludesRecentlySeenMember() {
        let adapter = CastMemberPageSourceAdapter()
        var inputs = BookSourceInputs.empty
        func member(_ id: String, belief: Int) -> CustomCastMember {
            CustomCastMember(
                id: id, name: id, kind: .motif, meaning: "m", description: "d",
                traits: [], beliefs: [], goals: [], tags: [],
                baseBelief: belief, narrativeWeight: 20,
                createdAt: Date(), updatedAt: Date(), imageAsset: nil
            )
        }
        inputs.customCastMembers = [member("compassion", belief: 90), member("quiet-shelf", belief: 10)]
        inputs.surfaceHistory = ["cast:compassion": SurfaceHistoryRecord(lastShownAt: Date().addingTimeInterval(-3600), recentShowCount: 2)]
        let day = BookDay.today()
        let pages = adapter.candidates(for: day, context: CuratorContext.make(for: day), inputs: inputs, now: Date())
        XCTAssertEqual(pages.first?.payload.metadata["entityID"], "quiet-shelf", "the favorite steps back after being seen")
    }

    func testInkedHourSurfacesBeforeEvent() {
        let adapter = CalendarPageSourceAdapter()
        var inputs = BookSourceInputs.empty
        let now = Date()
        inputs.calendarEvents = [
            CalendarEventSignal(id: "e1", title: "Dentist", startsAt: now.addingTimeInterval(30 * 60), isAllDay: false),
            CalendarEventSignal(id: "e2", title: "Far away", startsAt: now.addingTimeInterval(5 * 3600), isAllDay: false)
        ]
        let day = BookDay.today()
        let pages = adapter.candidates(for: day, context: CuratorContext.make(for: day), inputs: inputs, now: now)
        XCTAssertTrue(pages.contains { $0.payload.metadata["eventTitle"] == "Dentist" })
        XCTAssertFalse(pages.contains { $0.payload.metadata["eventTitle"] == "Far away" })
    }

    func testCalendarPressureQuietsHeavyPages() {
        var mood = CuratorMood.neutral
        mood.minutesToNextCalendarEvent = 20
        let story = SurfacePage(id: "s", type: .narrativeOS, sourceID: nil, score: 80, prompt: "s", detail: "",
                                payload: BookPagePayload(headline: "s", body: ""))
        XCTAssertLessThan(mood.adjustment(for: story), 0)
    }

    // MARK: Search the Stacks

    private func searchDay(id: String, pages: [BookPage]) -> BookDay {
        var day = BookDay.today()
        day = BookDay(id: id, date: Date().addingTimeInterval(-86_400), pages: pages)
        return day
    }

    func testGlowTierQueryFindsMatchingCast() {
        var dataset = StacksSearchDataset()
        dataset.entities = NarrativePackRegistry.entities
        let results = StacksSearchEngine.search("Show me everything with Small Glow", in: dataset)
        XCTAssertFalse(results.isEmpty)
        for result in results where result.kind == .castMember {
            XCTAssertTrue(result.snippet.contains("Small Glow"), result.snippet)
        }
    }

    func testTiredCorrelationFindsCoKeptPages() {
        let moodPage = BookPage(
            type: .mood,
            promptText: "What is the weather inside?",
            userInput: "Completely exhausted, heavy fog",
            tags: ["heavy"]
        )
        let souvenirPage = BookPage(
            type: .souvenir,
            promptText: "One sentence",
            userInput: "The porch light buzzed like a patient wasp.",
            tags: ["porch"]
        )
        var dataset = StacksSearchDataset()
        dataset.days = [searchDay(id: "2026-06-10", pages: [moodPage, souvenirPage])]
        let results = StacksSearchEngine.search("What did I keep when I was tired?", in: dataset)
        XCTAssertTrue(results.contains { $0.referenceID == souvenirPage.id }, "co-kept page should surface")
    }

    func testNameQueryFindsPagesAndMemories() {
        let page = BookPage(
            type: .diary,
            promptText: "Right now",
            userInput: "Morgan laughed at the crooked shelf again.",
            tags: []
        )
        var dataset = StacksSearchDataset()
        dataset.days = [searchDay(id: "2026-06-10", pages: [page])]
        dataset.memories = [
            NarrativeEntityMemory(
                id: "m1", entityID: "penny-blackletter", sourceEventID: "e1", sourcePageID: nil,
                summary: "Penny remembers: Morgan's shelf joke", tags: [], narrativeWeight: 3, createdAt: Date()
            )
        ]
        let results = StacksSearchEngine.search("pages about Morgan", in: dataset)
        XCTAssertTrue(results.contains { $0.kind == .keptPage })
        XCTAssertTrue(results.contains { $0.kind == .memory })
    }

    func testTypeWordFiltersToFamily() {
        let photo = BookPage(type: .illuminatedPhoto, promptText: "Found in the margins", userInput: "kettle", tags: [])
        let diary = BookPage(type: .diary, promptText: "Now", userInput: "kettle", tags: [])
        var dataset = StacksSearchDataset()
        dataset.days = [searchDay(id: "2026-06-10", pages: [photo, diary])]
        let results = StacksSearchEngine.search("photos of kettle", in: dataset)
        let pageResults = results.filter { $0.kind == .keptPage }
        XCTAssertEqual(pageResults.count, 1)
        XCTAssertEqual(pageResults.first?.referenceID, photo.id)
    }

    // MARK: Player vault

    func testPlayerVaultDataRoundTrips() throws {
        var data = PlayerVaultData()
        data.entityBelief = ["tide-glass": 12]
        data.tutorSeen = ["glow-menu"]
        let decoded = try JSONDecoder().decode(PlayerVaultData.self, from: JSONEncoder().encode(data))
        XCTAssertEqual(decoded, data)
        XCTAssertEqual(decoded.version, PlayerVaultData.currentVersion)
    }

    // MARK: Chapters and Talismans

    func testEveryChapterHasItsTalismanInThePack() {
        XCTAssertEqual(AcademyChapterRegistry.chapters.count, 5)
        XCTAssertEqual(AcademyChapterRegistry.publicChapters.count, 4)
        for chapter in AcademyChapterRegistry.chapters {
            let talisman = NarrativePackRegistry.entities.first { $0.id == chapter.talismanID }
            XCTAssertNotNil(talisman, "missing talisman \(chapter.talismanID)")
            XCTAssertEqual(talisman?.kind, .talisman)
            XCTAssertEqual(talisman?.chapter, chapter.name)
        }
    }

    func testEveryCharacterHasAChapter() {
        let chapterNames = Set(AcademyChapterRegistry.chapters.map(\.name))
        for entity in NarrativePackRegistry.entities where entity.kind == .character {
            let chapter = entity.chapter ?? ""
            XCTAssertTrue(chapterNames.contains(chapter), "\(entity.id) has no valid chapter (\(chapter))")
        }
    }

    func testAscendancyFollowsBelief() {
        let entities = NarrativePackRegistry.entities
        let unmoved = TalismanAscendancy.ascendant(entities: entities, beliefOffsets: [:])
        XCTAssertEqual(unmoved?.id, "dusk-thorn", "Dusk Thorn ships with the most Belief")
        let talismanBelief = Dictionary(
            uniqueKeysWithValues: entities
                .filter { $0.kind == .talisman }
                .map { ($0.id, $0.belief) }
        )
        XCTAssertEqual(talismanBelief["dusk-thorn"], 11)
        XCTAssertEqual(talismanBelief["ember-seal"], 10)
        XCTAssertEqual(talismanBelief["wind-cipher"], 10)
        XCTAssertEqual(talismanBelief["tide-glass"], 10)
        XCTAssertEqual(talismanBelief["moss-clasp"], 10)

        let flipped = TalismanAscendancy.ascendant(
            entities: entities,
            beliefOffsets: ["moss-clasp": 90]
        )
        XCTAssertEqual(flipped?.id, "moss-clasp", "player Belief can flip ascendancy")
    }

    func testBindingPageSurfacesUntilBound() {
        let adapter = AboutYouPageSourceAdapter()
        let day = BookDay.today()
        var inputs = BookSourceInputs.empty
        func fact(_ questionID: String, tags: [String]) -> SelfFact {
            SelfFact(
                id: questionID, questionID: questionID, question: "q", answer: "a",
                bookTranslation: "a", sensitivity: .delight, usePermission: .privateContext,
                tags: tags, createdAt: Date(), updatedAt: Date()
            )
        }
        inputs.selfFacts = [fact("onboarding-name", tags: ["name"])]
        let unbound = adapter.candidates(for: day, context: CuratorContext.make(for: day), inputs: inputs, now: Date())
        let binding = unbound.first { $0.payload.metadata["chapterBinding"] == "true" }
        XCTAssertNotNil(binding)
        XCTAssertLessThan(binding?.score ?? 100, 60)

        inputs.selfFacts.append(fact("chapter-binding", tags: ["chapter"]))
        let bound = adapter.candidates(for: day, context: CuratorContext.make(for: day), inputs: inputs, now: Date())
        XCTAssertFalse(bound.contains { $0.payload.metadata["chapterBinding"] == "true" })
    }

    func testWelcomePageGreetsNamedReaderBeforeChapterBinding() {
        let day = BookDay.today()
        var inputs = BookSourceInputs.empty
        inputs.selfFacts = [
            SelfFact(
                id: "onboarding-name",
                questionID: "onboarding-name",
                question: "What should the Book call you?",
                answer: "Beej",
                bookTranslation: "Beej",
                sensitivity: .delight,
                usePermission: .privateContext,
                tags: ["name", "identity", "onboarding"],
                createdAt: Date(),
                updatedAt: Date()
            )
        ]

        let welcome = LabyrinthWelcomePageSourceAdapter().candidates(
            for: day,
            context: CuratorContext.make(for: day),
            inputs: inputs,
            now: Date()
        ).first

        XCTAssertEqual(welcome?.type, .welcome)
        XCTAssertEqual(welcome?.payload.metadata["playerName"], "Beej")
        XCTAssertTrue(welcome?.payload.body.contains("Hello, Beej") == true)
        XCTAssertTrue(welcome?.payload.body.contains("Pages will surface") == true)
        XCTAssertTrue(welcome?.payload.body.contains("Chapter Binding can wait") == true)
        XCTAssertGreaterThan(welcome?.score ?? 0, 80)
    }

    func testWelcomePageDoesNotRepeatAfterBeingServed() {
        let day = BookDay.today()
        var inputs = BookSourceInputs.empty
        inputs.selfFacts = [
            SelfFact(
                id: "onboarding-name",
                questionID: "onboarding-name",
                question: "What should the Book call you?",
                answer: "Beej",
                bookTranslation: "Beej",
                sensitivity: .delight,
                usePermission: .privateContext,
                tags: ["name", "identity", "onboarding"],
                createdAt: Date(),
                updatedAt: Date()
            )
        ]
        inputs.surfaceHistory = [
            "source:labyrinth-welcome": SurfaceHistoryRecord(lastShownAt: Date(), recentShowCount: 1)
        ]

        let pages = LabyrinthWelcomePageSourceAdapter().candidates(
            for: day,
            context: CuratorContext.make(for: day),
            inputs: inputs,
            now: Date()
        )

        XCTAssertTrue(pages.isEmpty)
    }

    // MARK: Save file

    func testSaveFileRoundTrips() throws {
        let save = ReEnchantedSaveFile(
            exportedAt: Date(),
            days: [BookDay.today()],
            selfFacts: [],
            narrativeEvents: [],
            entityMemories: [],
            facultyEntries: [],
            customCastMembers: [],
            anchors: [],
            electives: [],
            beliefScore: 42,
            entityBeliefLedger: ["penny-blackletter": 3],
            pageBeliefLedger: ["inner-weather": -3],
            marginTutorSeen: ["glow-menu"],
            didCompleteStoryOnboarding: true,
            sourcePreferences: ["quip-page": false]
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let decoded = try decoder.decode(ReEnchantedSaveFile.self, from: encoder.encode(save))
        XCTAssertEqual(decoded.version, ReEnchantedSaveFile.currentVersion)
        XCTAssertEqual(decoded.beliefScore, 42)
        XCTAssertEqual(decoded.entityBeliefLedger["penny-blackletter"], 3)
        XCTAssertEqual(decoded.marginTutorSeen, ["glow-menu"])
        XCTAssertEqual(decoded.days.count, 1)
    }

    func testDefaultAnchorsShipEmpty() {
        XCTAssertTrue(AnchorRegistry.defaultAnchors.isEmpty, "Anchors are save data, never binary data")
    }

    // MARK: Margins Atlas

    func testMarginsAtlasLayoutIsDeterministicAndBounded() {
        let graph = NarrativeGraphData.loom(
            entities: NarrativePackRegistry.entities,
            relationships: NarrativePackRegistry.relationships,
            beliefOffsets: [:]
        )

        let first = GraphLayoutEngine.layout(data: graph, width: 320, height: 390, seed: "test-atlas")
        let second = GraphLayoutEngine.layout(data: graph, width: 320, height: 390, seed: "test-atlas")

        XCTAssertEqual(first, second)
        XCTAssertFalse(first.isEmpty)
        for point in first.values {
            XCTAssertGreaterThanOrEqual(point.x, 40)
            XCTAssertLessThanOrEqual(point.x, 280)
            XCTAssertGreaterThanOrEqual(point.y, 40)
            XCTAssertLessThanOrEqual(point.y, 350)
        }
    }

    func testMarginsAtlasAdapterBuildsConstellationFromBeliefLedgerEvents() {
        var inputs = BookSourceInputs.empty
        inputs.recentNarrativeEvents = [
            NarrativeEvent(
                id: "belief-penny",
                kind: .beliefInvested,
                sourcePageType: nil,
                sourcePageID: nil,
                createdAt: Date(),
                summary: "The reader gave Penny Belief.",
                tags: ["belief"],
                effect: NarrativeEventEffect(entityWeightDeltas: ["penny-blackletter": 3])
            )
        ]
        inputs.narrative = NarrativeSourceSnapshotBuilder.snapshot(from: inputs.recentNarrativeEvents, beliefWeight: 40)

        let pages = MarginsAtlasPageSourceAdapter().candidates(
            for: BookDay.today(),
            context: CuratorContext.make(for: BookDay.today()),
            inputs: inputs,
            now: Date()
        )
        let constellation = pages.first { $0.payload.metadata["graphVariant"] == MarginsAtlasVariant.constellation.rawValue }

        XCTAssertNotNil(constellation)
        XCTAssertTrue(constellation?.payload.metadata["graphNodes"]?.contains("the-reader") == true)
        XCTAssertTrue(constellation?.payload.metadata["graphEdges"]?.contains("flow-penny-blackletter") == true)
    }

    // MARK: Electives

    func testElectiveOfferRespectsFiveActiveCap() {
        let adapter = ElectivePageSourceAdapter()
        var inputs = BookSourceInputs.empty
        var calendar = utcCalendar
        calendar.timeZone = TimeZone.current
        let noon = Calendar.current.date(bySettingHour: 12, minute: 0, second: 0, of: Date().addingTimeInterval(-86_400))!
        inputs.electives = (0..<5).map { index in
            UnwrittenElective(
                id: "e\(index)",
                characterID: "char-\(index)",
                characterName: "Character \(index)",
                title: "Favor \(index)",
                ask: "Do the thing",
                whyItMatters: "It matters",
                practiceShape: "One sentence",
                createdAt: noon.addingTimeInterval(Double(index) * -3600)
            )
        }
        let day = BookDay.today()
        let pages = adapter.candidates(
            for: day,
            context: CuratorContext.make(for: day),
            inputs: inputs,
            now: Calendar.current.date(bySettingHour: 12, minute: 0, second: 0, of: Date())!
        )
        XCTAssertFalse(pages.contains { $0.payload.metadata["electiveOffer"] == "true" })
        XCTAssertTrue(pages.contains { $0.payload.metadata["electiveFlyleaf"] == "true" })
    }
}
