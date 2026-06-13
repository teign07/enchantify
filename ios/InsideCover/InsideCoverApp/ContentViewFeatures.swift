import SwiftUI

// MARK: - ContentView feature cluster: seals, anchors, generated-page
// adoption, onboarding completion, and Unwritten Electives.
//
// Split from ContentView.swift to start paying down the monolith; new
// feature clusters should land here (or in sibling extension files), not
// in the main view file.

extension ContentView {
    var marginaliaSealsRow: some View {
        HStack(alignment: .top, spacing: 14) {
            MarginaliaSealButton(
                title: "Body",
                systemImage: "figure.walk",
                wax: Color(red: 0.58, green: 0.16, blue: 0.18),
                seed: 3,
                isBusy: busySealID == "body",
                action: { Task { await pressBodySeal() } }
            )
            MarginaliaSealButton(
                title: "Weather",
                systemImage: "cloud.sun.fill",
                wax: BookPalette.teal,
                seed: 11,
                isBusy: busySealID == "weather",
                action: { Task { await pressWeatherSeal() } }
            )
            MarginaliaSealButton(
                title: "Location",
                systemImage: "mappin.and.ellipse",
                wax: Color(red: 0.36, green: 0.28, blue: 0.55),
                seed: 23,
                isBusy: busySealID == "location" || isAnchoringPlace,
                action: { Task { await pressLocationSeal() } }
            )
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 4)
    }

    @MainActor
    func pressBodySeal() async {
        guard busySealID == nil else { return }
        busySealID = "body"
        defer { busySealID = nil }
        BookFeedback.play(.sourceRefresh)
        tutorTouch("seal-body")
        _ = await refreshHealthKitBodySignal(isUserInitiated: true)
        await openManualPage(.body)
    }

    @MainActor
    func pressWeatherSeal() async {
        guard busySealID == nil else { return }
        busySealID = "weather"
        defer { busySealID = nil }
        BookFeedback.play(.sourceRefresh)
        tutorTouch("seal-weather")
        await openManualPage(.weather)
    }

    @MainActor
    func pressLocationSeal() async {
        guard busySealID == nil, !isAnchoringPlace else { return }
        busySealID = "location"
        defer { busySealID = nil }
        BookFeedback.play(.sourceRefresh)
        tutorTouch("seal-location")
        let succeeded = await refreshAnchorProximity(isUserInitiated: true)
        if let proximity = nearbyAnchor {
            await openAnchorVisitPage(proximity)
        } else if succeeded,
                  let latitude = lastAnchorReadingLatitude,
                  let longitude = lastAnchorReadingLongitude {
            selectedSurface = anchorOfferSurface(latitude: latitude, longitude: longitude)
        }
    }

    func anchorOfferSurface(latitude: Double, longitude: Double) -> SurfacePage {
        let source = BookPageSourceRegistry.source(for: .anchor)
        return SurfacePage(
            id: "anchor-offer-\(Int(Date().timeIntervalSince1970))",
            type: .anchor,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .promptCard,
            score: 88,
            reason: "No Anchor is lit within two hundred meters. This place could become one.",
            prompt: "Anchor this place?",
            detail: "The Book can grow an Outer Stacks room from where you are standing.",
            payload: BookPagePayload(
                headline: "An Unanchored Place",
                body: "No Anchor is lit within two hundred meters of where you stand. Name this place and tell the Book what it holds for you. Your exact words become the room.",
                metadata: [
                    "source": source.id,
                    "anchorOffer": "true",
                    "latitude": "\(latitude)",
                    "longitude": "\(longitude)",
                    "privacy": "location stays on device",
                    "tags": "anchor,outer-stacks,offer,location"
                ]
            )
        )
    }

    @MainActor
    func openAnchorVisitPage(_ proximity: AnchorProximity) async {
        statusMessage = "The Outer Stacks door is opening..."
        let base = preparedAnchorSurface ?? OuterStacksAnchorPageSourceAdapter().manualSurface(
            for: today,
            context: CuratorContext.make(for: today),
            inputs: sourceInputs,
            now: Date()
        )
        var body = base.payload.body
        var metadata = base.payload.metadata
        if let scene = try? await makeOuterStacksRoomWriter().visitScene(
            anchor: proximity.anchor,
            visitCount: proximity.nextVisitCount,
            day: today
        ) {
            body = "\(scene)\n\nKeeping this page checks in at the Anchor and adds \(AnchorRegistry.checkInBeliefReward) Belief to the place."
            metadata["visitScene"] = scene
        }
        statusMessage = ""
        selectedSurface = SurfacePage(
            id: base.id,
            type: base.type,
            sourceID: base.sourceID,
            intent: base.intent,
            renderStyle: base.renderStyle,
            score: base.score,
            reason: base.reason,
            prompt: base.prompt,
            detail: base.detail,
            payload: BookPagePayload(
                headline: base.payload.headline,
                body: body,
                metadata: metadata
            )
        )
    }



    @MainActor
    func completeOnboarding(_ result: OnboardingFlowView.Result) {
        withAnimation(.easeInOut(duration: 0.4)) {
            didCompleteStoryOnboarding = true
        }
        saveOnboardingFact(
            questionID: "onboarding-snack",
            question: "What is your favorite snack to eat while reading?",
            answer: result.snack,
            tags: ["snack", "delight", "onboarding"]
        )
        saveOnboardingFact(
            questionID: "onboarding-name",
            question: "What should the Book call you?",
            answer: result.name,
            tags: ["name", "identity", "onboarding"]
        )
        saveOnboardingFact(
            questionID: "onboarding-belief",
            question: "What do you believe in?",
            answer: result.belief,
            tags: ["belief", "core", "onboarding"]
        )
        if result.investedBelief, !result.belief.isEmpty {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
                beliefScore = max(0, beliefScore - 3)
            }
            saveCustomCastMember(CustomCastMemberDraft(
                name: result.belief,
                kind: .motif,
                meaning: "The player's stated core belief, planted with 3 Belief on their first day in the Labyrinth.",
                description: "Spoken aloud to Zara Finch at the threshold: \"\(result.belief)\"",
                traits: ["planted", "core"],
                beliefs: [result.belief],
                goals: ["shape what finds the player here"],
                tags: ["core-belief", "onboarding"],
                imageData: nil
            ))
        }
        statusMessage = result.name.isEmpty
            ? "The Academy doors are open."
            : "The Academy doors are open, \(result.name)."
        BookFeedback.play(.braidComplete)
    }

    func saveOnboardingFact(questionID: String, question: String, answer: String, tags: [String]) {
        let trimmed = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let now = Date()
        let fact = SelfFact(
            id: "onboarding:\(questionID)",
            questionID: questionID,
            question: question,
            answer: trimmed,
            bookTranslation: trimmed,
            sensitivity: .delight,
            usePermission: .privateContext,
            tags: tags,
            createdAt: now,
            updatedAt: now
        )
        do {
            try BookDatabase.upsertSelfFact(fact)
            selfFacts = (try? BookDatabase.selfFacts()) ?? (selfFacts.filter { $0.id != fact.id } + [fact])
        } catch {
            appLog.error("Onboarding fact save failed: \(error.localizedDescription, privacy: .public)")
        }
    }

    var electives: [UnwrittenElective] {
        guard let data = electiveLedgerData.data(using: .utf8),
              let decoded = try? JSONDecoder().decode([UnwrittenElective].self, from: data) else {
            return []
        }
        return decoded
    }

    func saveElectives(_ list: [UnwrittenElective]) {
        guard let data = try? JSONEncoder().encode(list),
              let encoded = String(data: data, encoding: .utf8) else {
            return
        }
        electiveLedgerData = encoded
        surfaceRefreshDate = Date()
        rebuildSurfaceCache()
        BookWhispers.refreshSchedule(enabled: bookWhispersEnabled, electives: list)
    }


    func acceptElectiveIfNeeded(surface: SurfacePage) {
        guard surface.type == .elective,
              surface.payload.metadata["electiveOffer"] == "true",
              let ask = surface.payload.metadata["electiveAsk"]?.nonEmpty else {
            return
        }
        var list = electives
        guard list.filter(\.isActive).count < UnwrittenElective.maxActive else {
            statusMessage = "The flyleaf is full. Complete a favor before accepting another."
            return
        }
        let senderID = surface.payload.metadata["senderID"] ?? "the-book"
        guard !list.contains(where: { $0.characterID == senderID && $0.isActive }) else { return }
        let elective = UnwrittenElective(
            id: "elective-\(senderID)-\(UUID().uuidString.prefix(8))",
            characterID: senderID,
            characterName: surface.payload.metadata["senderName"] ?? "A character",
            title: surface.payload.metadata["electiveTitle"] ?? "An Unwritten Elective",
            ask: ask,
            whyItMatters: surface.payload.metadata["electiveWhy"] ?? "",
            practiceShape: surface.payload.metadata["electivePractice"] ?? "One sentence of proof.",
            createdAt: Date()
        )
        list.append(elective)
        saveElectives(list)
        statusMessage = "\(elective.characterName)'s favor is tucked into the flyleaf."
    }

    @MainActor
    func completeElective(id: String, proof: String) {
        var list = electives
        guard let index = list.firstIndex(where: { $0.id == id && $0.isActive }) else { return }
        list[index].completedAt = Date()
        list[index].proof = proof.trimmingCharacters(in: .whitespacesAndNewlines)
        saveElectives(list)
        let elective = list[index]

        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = min(100, beliefScore + UnwrittenElective.completionBeliefReward)
        }
        let event = NarrativeEvent(
            id: "elective-complete-\(elective.id)",
            kind: .pageAnswered,
            sourcePageType: .elective,
            sourcePageID: nil,
            createdAt: Date(),
            summary: "The reader completed \(elective.characterName)'s favor \"\(elective.title)\": \(elective.proof ?? "")",
            tags: ["elective", "completed", "entity:\(elective.characterID)"],
            effect: NarrativeEventEffect(
                beliefDelta: UnwrittenElective.completionBeliefReward,
                entityWeightDeltas: [elective.characterID: 3]
            )
        )
        do {
            try BookDatabase.upsertNarrativeEvent(event)
            for memory in NarrativeEntityMemoryResolver.memories(for: event) {
                try BookDatabase.upsertEntityMemory(memory)
            }
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 160)
            entityMemories = NarrativeEntityMemoryConsolidator.consolidate(try BookDatabase.entityMemories(limit: 240))
        } catch {
            statusMessage = "The favor is complete, but a hidden margin note slipped: \(error.localizedDescription)"
            return
        }
        statusMessage = "\(elective.characterName) will remember this. +\(UnwrittenElective.completionBeliefReward) Belief."
        BookFeedback.play(.braidComplete)
    }



    @MainActor
    func anchorPlace(from draft: AnchorPlaceDraft) async {
        guard !isAnchoringPlace else { return }
        isAnchoringPlace = true
        defer { isAnchoringPlace = false }
        statusMessage = "The Labyrinth is growing a room from your words..."

        let now = Date()
        let moon = MoonPhaseCalendar.phase(on: now)
        let season = AnchorRegistry.currentSeason(for: now)
        let weatherPhrase = sourceInputs.weather?.phrase ?? "unrecorded weather"
        let startingBelief = 10

        let fallbackWriter = FakeOuterStacksRoomWriter()
        let spec: OuterStacksRoomSpec
        if let written = try? await makeOuterStacksRoomWriter().room(
            anchorName: draft.name,
            playerWords: draft.words,
            kind: draft.kind,
            weather: weatherPhrase,
            moon: moon.name,
            season: season,
            belief: startingBelief
        ) {
            spec = written
        } else if let offline = try? await fallbackWriter.room(
            anchorName: draft.name,
            playerWords: draft.words,
            kind: draft.kind,
            weather: weatherPhrase,
            moon: moon.name,
            season: season,
            belief: startingBelief
        ) {
            spec = offline
        } else {
            statusMessage = "The room would not take shape yet. Try anchoring once more."
            return
        }

        let record = AnchorRecord(
            id: "user-anchor-\(slug(for: draft.name))-\(UUID().uuidString.prefix(8))",
            name: draft.name,
            latitude: draft.latitude,
            longitude: draft.longitude,
            radiusMeters: AnchorRegistry.proximityRadiusMeters,
            kind: draft.kind,
            belief: startingBelief,
            created: AnchorRegistry.visitDateFormatter.string(from: now),
            weather: weatherPhrase,
            moon: moon.name,
            season: season,
            playerWords: draft.words,
            academyEcho: spec.academyEcho,
            outerStacksRoom: spec.roomDescription,
            fae: spec.fae,
            miniStory: spec.miniStory,
            localRule: spec.localRule,
            visitCount: 0,
            lastVisited: "none"
        )
        anchorLedger.append(record)
        saveAnchorLedger()

        let proximity = AnchorProximity(anchor: record, distanceMeters: 0)
        nearbyAnchor = proximity
        var draftInputs = sourceInputs
        draftInputs.nearbyAnchor = proximity
        preparedAnchorSurface = OuterStacksAnchorPageSourceAdapter().manualSurface(
            for: today,
            context: CuratorContext.make(for: today),
            inputs: draftInputs,
            now: Date()
        )
        surfaceRefreshDate = Date()
        anchorMessage = "\(record.name) is anchored. Its room in the Outer Stacks is waiting."
        statusMessage = "\(record.name) is anchored. The door is already open."
        BookFeedback.play(.braidComplete)
        await openAnchorVisitPage(proximity)
    }

    // MARK: - Save file: the player's world, portable

    @MainActor
    func buildSaveFile() -> ReEnchantedSaveFile {
        let archiveEvents = (try? BookDatabase.narrativeEvents(limit: 5000)) ?? narrativeEvents
        let archiveMemories = (try? BookDatabase.entityMemories(limit: 5000)) ?? entityMemories
        let continuity = LiteraryContinuityProjector.digest(
            days: days,
            events: archiveEvents,
            entityMemories: archiveMemories,
            entityBelief: entityBeliefLedger,
            pageBelief: pageBeliefLedger
        )
        let clusters = BookMotifClusterEngine.clusters(
            from: continuity,
            constellations: vault.data.constellations ?? [],
            themes: vault.data.themes ?? []
        )
        return ReEnchantedSaveFile(
            exportedAt: Date(),
            days: days,
            selfFacts: (try? BookDatabase.selfFacts()) ?? selfFacts,
            narrativeEvents: archiveEvents,
            entityMemories: archiveMemories,
            facultyEntries: (try? BookDatabase.facultyEntries(limit: 5000)) ?? facultyEntries,
            customCastMembers: customCastMembers,
            anchors: anchorLedger,
            electives: electives,
            beliefScore: beliefScore,
            entityBeliefLedger: entityBeliefLedger,
            pageBeliefLedger: pageBeliefLedger,
            marginTutorSeen: Array(MarginTutorLedger.seenIDs(from: marginTutorSeenData)),
            didCompleteStoryOnboarding: didCompleteStoryOnboarding,
            sourcePreferences: decodedSourcePreferenceLedger(),
            constellations: vault.data.constellations,
            wagers: vault.data.wagers,
            themes: vault.data.themes,
            clusters: clusters,
            continuity: continuity
        )
    }

    @MainActor
    func exportSaveFile() {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(buildSaveFile())
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("ReEnchanted-\(formatter.string(from: Date())).\(ReEnchantedSaveFile.fileExtension)")
            try data.write(to: url, options: [.atomic])
            preparedSaveFileURL = url
            statusMessage = "The save file is bound and ready to share."
            BookFeedback.play(.braidComplete)
        } catch {
            statusMessage = "The save file would not bind: \(error.localizedDescription)"
            BookFeedback.play(.error)
        }
    }

    @MainActor
    func exportContinuityFile() {
        do {
            let archiveEvents = (try? BookDatabase.narrativeEvents(limit: 5000)) ?? narrativeEvents
            let archiveMemories = (try? BookDatabase.entityMemories(limit: 5000)) ?? entityMemories
            let digest = LiteraryContinuityProjector.digest(
                days: days,
                events: archiveEvents,
                entityMemories: archiveMemories,
                entityBelief: entityBeliefLedger,
                pageBelief: pageBeliefLedger
            )
            let export = BookArchiveExport(
                days: [],
                continuity: LiteraryContinuityDigest(
                    signals: Array(digest.strongestSignals.prefix(16)),
                    beliefLifecycles: Array(digest.beliefLifecycles.prefix(12))
                ),
                constellations: Array((vault.data.constellations ?? []).prefix(16)),
                wagers: Array((vault.data.wagers ?? []).prefix(12)),
                themes: Array((vault.data.themes ?? []).suffix(12)),
                clusters: Array(BookMotifClusterEngine.clusters(
                    from: digest,
                    constellations: vault.data.constellations ?? [],
                    themes: vault.data.themes ?? []
                ).prefix(12))
            )
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("insidecover-continuity.json")
            try export.encodedData().write(to: url, options: [.atomic])
            preparedContinuityURL = url
            statusMessage = "The Book's continuity is bound and ready to share."
            BookFeedback.play(.braidComplete)
        } catch {
            statusMessage = "The continuity file would not bind: \(error.localizedDescription)"
            BookFeedback.play(.error)
        }
    }

    /// The keeper of constellations and sealed margins: recomputes the
    /// continuity digest, advances the durable constellation ledger, opens
    /// any wagers whose date has come, and seals new ones. Runs alongside
    /// tendArc so the Book's long memory moves whenever the field does.
    @MainActor
    func tendConstellations(now: Date = Date()) {
        let digest = LiteraryContinuityProjector.digest(
            days: days,
            events: narrativeEvents,
            entityMemories: entityMemories,
            entityBelief: entityBeliefLedger,
            pageBelief: pageBeliefLedger,
            now: now
        )
        let advanced = ConstellationKeeper.advanced(
            vault.data.constellations ?? [],
            observing: digest,
            now: now
        )
        var wagers = SealedMarginEngine.resolved(vault.data.wagers ?? [], against: days, now: now)
        wagers += SealedMarginEngine.mintWagers(from: digest, existing: wagers, now: now)

        let calendar = Calendar.current
        let monthKey = BookThemeEngine.monthKey(for: now, calendar: calendar)
        let monthStart = calendar.date(from: calendar.dateComponents([.year, .month], from: now)) ?? now
        let monthPages = days
            .filter { $0.date >= calendar.startOfDay(for: monthStart) }
            .flatMap(\.pages)
        let currentTheme = BookThemeEngine.theme(
            for: monthPages,
            digest: digest,
            constellations: advanced,
            monthKey: monthKey,
            now: now
        )
        let themes = BookThemeEngine.remembered(vault.data.themes ?? [], observing: currentTheme, monthKey: monthKey)

        let changed = advanced != (vault.data.constellations ?? [])
            || wagers != (vault.data.wagers ?? [])
            || themes != (vault.data.themes ?? [])
        guard changed else { return }
        vault.data.constellations = advanced
        vault.data.wagers = wagers
        vault.data.themes = themes
        vault.save()
        surfaceRefreshDate = now
    }

    // MARK: - The Bleed press run

    /// Sets the presses running: live interest research, then one local-brain
    /// call per written column, composited into a single edition page.
    @MainActor
    @discardableResult
    func prepareBleedEditionIfPossible(from announcement: SurfacePage? = nil) async -> Bool {
        guard !generation.isPreparingBleedEdition, !localBrainTelemetry.isWorking else { return false }
        let surface: SurfacePage
        if let announcement, announcement.payload.metadata["bleedBriefs"]?.isEmpty == false {
            surface = announcement
        } else if let built = TheBleedEditionBuilder.announcementSurface(for: today, inputs: sourceInputs, now: Date()) {
            surface = built
        } else {
            statusMessage = "The presses rest in the afternoon. The next edition sets at four."
            return false
        }

        if let prepared = generation.preparedBleedEditionSurface,
           prepared.payload.metadata["bleedSlotID"] == surface.payload.metadata["bleedSlotID"] {
            return true
        }

        generation.isPreparingBleedEdition = true
        defer { generation.isPreparingBleedEdition = false }

        let briefs = TheBleedEditionBuilder.decodedBriefs(surface.payload.metadata["bleedBriefs"] ?? "")
        guard !briefs.isEmpty else {
            statusMessage = "The type tray came up empty. Penny is re-sorting the briefs."
            return false
        }

        let interest = surface.payload.metadata["bleedInterest"]?.nonEmpty
        var clippings = ""
        var clippingSources = ""
        if let interest {
            statusMessage = "Penny is interviewing the wider world about \(interest)..."
            let research = await BleedInterestSearcher().clippings(for: interest)
            clippings = research.text
            clippingSources = research.sources
        }

        let writer = BleedColumnWriter()
        var columns: [(brief: BleedColumnBrief, body: String)] = []
        for brief in briefs {
            if brief.needsLocalBrain {
                statusMessage = "Setting type: \(brief.title)..."
            }
            let body = await writer.write(brief: brief, clippings: clippings)
            columns.append((brief, body))
        }

        let kind = BleedEditionKind(rawValue: surface.payload.metadata["bleedEditionKind"] ?? "") ?? .morning
        let issueNumber = Int(surface.payload.metadata["bleedIssueNumber"] ?? "") ?? 1
        let body = TheBleedEditionBuilder.compositedBody(
            kind: kind,
            issueNumber: issueNumber,
            columns: columns,
            now: Date()
        )
        generation.preparedBleedEditionSurface = TheBleedEditionBuilder.preparedCopy(
            of: surface,
            body: body,
            interestSources: clippingSources
        )
        surfaceRefreshDate = Date()
        statusMessage = "Issue #\(issueNumber) is off the press."
        BookFeedback.play(.braidComplete)
        return true
    }

    /// Binds the most recent edition (prepared or kept today) as a PDF.
    @MainActor
    func exportBleedPDF() {
        let candidate: (headline: String, body: String)? = {
            if let prepared = generation.preparedBleedEditionSurface,
               let prose = prepared.payload.metadata["bleedProse"]?.nonEmpty {
                return (prepared.payload.headline, prose)
            }
            if let kept = today.pages.last(where: { $0.type == .theBleed && !$0.userInput.isEmpty }) {
                return (kept.promptText.nonEmpty ?? "The Bleed", kept.userInput)
            }
            return nil
        }()
        guard let candidate else {
            statusMessage = "No edition has been printed yet today."
            BookFeedback.play(.error)
            return
        }
        do {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd-HHmm"
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("TheBleed-\(formatter.string(from: Date())).pdf")
            try BleedPDFWriter.write(headline: candidate.headline, body: candidate.body, to: url)
            preparedBleedPDFURL = url
            statusMessage = "The Bleed is bound for sharing."
            BookFeedback.play(.braidComplete)
        } catch {
            statusMessage = "The edition would not bind: \(error.localizedDescription)"
            BookFeedback.play(.error)
        }
    }

    @MainActor
    func exportMonthlyEdition() {
        do {
            let archiveEvents = (try? BookDatabase.narrativeEvents(limit: 5000)) ?? narrativeEvents
            let archiveMemories = (try? BookDatabase.entityMemories(limit: 5000)) ?? entityMemories
            let edition = MonthlyEditionBuilder.previousMonth(
                from: days,
                events: archiveEvents,
                entityMemories: archiveMemories,
                entityBelief: entityBeliefLedger,
                pageBelief: pageBeliefLedger,
                constellations: vault.data.constellations ?? [],
                wagers: vault.data.wagers ?? [],
                themes: vault.data.themes ?? [],
                readerName: CharacterLetterPageGenerator.preferredPlayerName(inputs: sourceInputs),
                now: Date()
            )
            guard !edition.isEmpty else {
                statusMessage = "The previous month has no kept pages to bind yet."
                BookFeedback.play(.error)
                return
            }
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM"
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("ReEnchanted-Monthly-\(formatter.string(from: edition.startDate)).pdf")
            try MonthlyEditionPDFWriter.write(edition, to: url)
            preparedMonthlyEditionURL = url
            statusMessage = "The monthly edition is bound and ready to share."
            BookFeedback.play(.braidComplete)
        } catch {
            statusMessage = "The monthly edition would not bind: \(error.localizedDescription)"
            BookFeedback.play(.error)
        }
    }

    /// Imports by merge-upsert: nothing on the device is deleted; the save's
    /// pages, facts, memories, cast, and ledgers land on top.
    @MainActor
    func importSaveFile(from url: URL) {
        let shouldStop = url.startAccessingSecurityScopedResource()
        defer {
            if shouldStop {
                url.stopAccessingSecurityScopedResource()
            }
        }
        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let save = try decoder.decode(ReEnchantedSaveFile.self, from: Data(contentsOf: url))

            for day in save.days {
                days = (try? BookDatabase.upsert(day, fallbackDays: days)) ?? days
            }
            for fact in save.selfFacts {
                try? BookDatabase.upsertSelfFact(fact)
            }
            for event in save.narrativeEvents {
                try? BookDatabase.upsertNarrativeEvent(event)
            }
            for memory in save.entityMemories {
                try? BookDatabase.upsertEntityMemory(memory)
            }
            for entry in save.facultyEntries {
                try? BookDatabase.upsertFacultyEntry(entry)
            }
            for member in save.customCastMembers {
                try? BookDatabase.upsertCustomCastMember(member)
            }

            let importedAnchors = save.anchors.filter { anchor in
                !AnchorRegistry.retiredAnchorIDs.contains(anchor.id) &&
                !anchorLedger.contains { $0.id == anchor.id }
            }
            anchorLedger.append(contentsOf: importedAnchors)
            saveAnchorLedger()

            var mergedElectives = electives
            for elective in save.electives where !mergedElectives.contains(where: { $0.id == elective.id }) {
                mergedElectives.append(elective)
            }
            saveElectives(mergedElectives)

            beliefScore = max(beliefScore, save.beliefScore)
            if let data = try? JSONEncoder().encode(save.entityBeliefLedger),
               let encoded = String(data: data, encoding: .utf8) {
                entityBeliefLedgerData = encoded
            }
            if let data = try? JSONEncoder().encode(save.pageBeliefLedger),
               let encoded = String(data: data, encoding: .utf8) {
                pageBeliefLedgerData = encoded
            }
            if let importedConstellations = save.constellations, !importedConstellations.isEmpty {
                var merged = vault.data.constellations ?? []
                for constellation in importedConstellations where !merged.contains(where: { $0.id == constellation.id }) {
                    merged.append(constellation)
                }
                vault.data.constellations = merged
            }
            if let importedWagers = save.wagers, !importedWagers.isEmpty {
                var merged = vault.data.wagers ?? []
                for wager in importedWagers where !merged.contains(where: { $0.id == wager.id }) {
                    merged.append(wager)
                }
                vault.data.wagers = merged
            }
            if let importedThemes = save.themes, !importedThemes.isEmpty {
                var merged = vault.data.themes ?? []
                for theme in importedThemes {
                    merged.removeAll { $0.monthKey == theme.monthKey }
                    merged.append(theme)
                }
                vault.data.themes = merged.sorted { $0.monthKey < $1.monthKey }
            }
            vault.save()
            marginTutorSeenData = MarginTutorLedger.encode(Set(save.marginTutorSeen))
            if save.didCompleteStoryOnboarding {
                didCompleteStoryOnboarding = true
            }
            if let data = try? JSONEncoder().encode(save.sourcePreferences),
               let encoded = String(data: data, encoding: .utf8) {
                sourcePreferenceLedger = encoded
            }

            selfFacts = (try? BookDatabase.selfFacts()) ?? selfFacts
            narrativeEvents = (try? BookDatabase.narrativeEvents(limit: 160)) ?? narrativeEvents
            entityMemories = NarrativeEntityMemoryConsolidator.consolidate((try? BookDatabase.entityMemories(limit: 240)) ?? entityMemories)
            customCastMembers = (try? BookDatabase.customCastMembers(limit: 200)) ?? customCastMembers
            facultyEntries = (try? BookDatabase.facultyEntries(limit: 160)) ?? facultyEntries
            PersonalNameGuard.update(from: selfFacts)
            surfaceRefreshDate = Date()
            rebuildSurfaceCache()
            statusMessage = "The save file has been read back into the Book: \(save.days.count) days, \(save.selfFacts.count) facts, \(save.anchors.count) anchors."
            BookFeedback.play(.braidComplete)
        } catch {
            statusMessage = "That save file would not open: \(error.localizedDescription)"
            BookFeedback.play(.error)
        }
    }

    // MARK: - Chapters and Talismans

    var ascendantTalisman: NarrativeWorldEntity? {
        TalismanAscendancy.ascendant(
            entities: NarrativePackRegistry.entities + customCastMembers.map(\.entity),
            beliefOffsets: entityBeliefLedger
        )
    }

    @MainActor
    func bindChapter(id chapterID: String) {
        guard let chapter = AcademyChapterRegistry.chapter(id: chapterID) else { return }
        saveOnboardingFact(
            questionID: "chapter-binding",
            question: "Which Chapter holds your way of believing?",
            answer: chapter.name,
            tags: ["chapter", "identity", "binding", chapter.id]
        )
        // The binding itself is an act of Belief: the chapter's talisman warms.
        let talisman = GlowEntityMenuItem(
            id: chapter.talismanID,
            name: chapter.talismanName,
            kind: "talisman",
            glow: 0,
            line: chapter.philosophy
        )
        adjustEntityBelief(talisman, delta: 2, kind: .beliefInvested)
        surfaceRefreshDate = Date()
        rebuildSurfaceCache()
        statusMessage = "The binding holds. Chapter \(chapter.name) claims your margins, and \(chapter.talismanName) warms by two points."
        BookFeedback.play(.braidComplete)
    }

    // MARK: - Unified generated-page adoption

    /// One path for every "tap to generate" page: ask the engine, stamp the
    /// prose into the page, fall back to the template body when the brain
    /// is unavailable. The per-type functions below are thin orderings.
    @MainActor
    func generatedProseSurface(
        from base: SurfacePage,
        proseKey: String,
        prompt: String,
        instructions: String,
        maxTokens: Int = 520,
        sourceID: String,
        tags: [String],
        fallbackBody: String? = nil
    ) async -> SurfacePage {
        var metadata = base.payload.metadata
        let body: String
        if let prose = await LocalBrainProse.write(
            prompt: prompt,
            instructions: instructions,
            maxTokens: maxTokens,
            sourceID: sourceID,
            tags: tags
        ), !prose.hasPrefix("{") {
            metadata[proseKey] = prose
            body = prose
        } else {
            metadata[proseKey] = "fallback"
            body = fallbackBody ?? base.payload.body
        }
        return SurfacePage(
            id: base.id,
            type: base.type,
            sourceID: base.sourceID,
            intent: base.intent,
            renderStyle: base.renderStyle,
            score: base.score,
            reason: base.reason,
            prompt: base.prompt,
            detail: base.detail,
            payload: BookPagePayload(headline: base.payload.headline, body: body, metadata: metadata)
        )
    }

    @MainActor
    func supportGuildSurfaceWithProse(from base: SurfacePage) async -> SurfacePage {
        await generatedProseSurface(
            from: base,
            proseKey: "guildProse",
            prompt: LocalModelManager.supportGuildPrompt(surface: base),
            instructions: """
            You are the Support Guild scribe inside ReEnchanted. Write the meeting scene in character, prose only, no headings; experiment lines start with "Try: ".
            """,
            maxTokens: 680,
            sourceID: "support-guild",
            tags: ["support-guild", "dr-vellum", "dr-inkrest"]
        )
    }

    @MainActor
    func academyClassSurfaceWithProse(from base: SurfacePage) async -> SurfacePage {
        let teaches = base.payload.metadata["sessionTeaches"] ?? "the day's lesson"
        let leader = base.payload.metadata["sessionLeader"] ?? "The professor"
        return await generatedProseSurface(
            from: base,
            proseKey: "classProse",
            prompt: LocalModelManager.academyClassPrompt(surface: base, day: today),
            instructions: """
            You are the Labyrinth of Stories narrating Academy classes and clubs. Write the scene in prose only, no headings or lists.
            """,
            sourceID: "academy-class",
            tags: ["academy", "class", "club"],
            fallbackBody: "\(base.payload.body)\n\n\(leader) is teaching: \(teaches)\n\nThe local brain could not write the full scene this time; the lesson itself still stands."
        )
    }

    @MainActor
    func packPageSurfaceWithProse(from base: SurfacePage) async -> SurfacePage {
        await generatedProseSurface(
            from: base,
            proseKey: "packProse",
            prompt: base.payload.metadata["packPrompt"] ?? "",
            instructions: base.payload.metadata["packInstructions"] ?? "You are the Book inside ReEnchanted. Write the requested page in prose only.",
            maxTokens: Int(base.payload.metadata["packMaxTokens"] ?? "") ?? 420,
            sourceID: "pack-page",
            tags: ["pack-page", base.payload.metadata["packArchetypeID"] ?? "unknown"]
        )
    }

    @MainActor
    func electiveOfferSurfaceWithAsk(from base: SurfacePage) async -> SurfacePage {
        let offer = await ElectiveOfferWriter().offer(surface: base)
        var metadata = base.payload.metadata
        metadata["electiveTitle"] = offer.title
        metadata["electiveAsk"] = offer.ask
        metadata["electiveWhy"] = offer.whyItMatters
        metadata["electivePractice"] = offer.practiceShape
        let body = """
        \(offer.ask)

        Why it matters to them: \(offer.whyItMatters)

        What counts as done: \(offer.practiceShape)

        Keep this page to accept. The note will be tucked into the flyleaf — \(electives.filter(\.isActive).count)/\(UnwrittenElective.maxActive) slots used.
        """
        return SurfacePage(
            id: base.id,
            type: base.type,
            sourceID: base.sourceID,
            intent: base.intent,
            renderStyle: base.renderStyle,
            score: base.score,
            reason: base.reason,
            prompt: "\(offer.title) — \(base.payload.metadata["senderName"] ?? "a character")",
            detail: base.detail,
            payload: BookPagePayload(headline: "An Unwritten Elective", body: body, metadata: metadata)
        )
    }

    func makeOuterStacksRoomWriter() -> OuterStacksRoomWriting {
        OuterStacksRoomEngine()
    }

    // MARK: - Search the Stacks

    var stacksSearchDataset: StacksSearchDataset {
        StacksSearchDataset(
            days: days,
            entities: NarrativePackRegistry.entities + customCastMembers.map(\.entity),
            entityBeliefOffsets: entityBeliefLedger,
            pageBeliefOffsets: pageBeliefLedger,
            anchors: anchorLedger,
            memories: entityMemories,
            electives: electives,
            references: BookReferenceCatalog.wonderCompass
                + BookReferenceCatalog.lorePacks.flatMap(\.snippets)
        )
    }

    @MainActor
    func openSearchResult(_ result: StacksSearchResult) {
        switch result.kind {
        case .keptPage:
            if let page = days.flatMap(\.pages).first(where: { $0.id == result.referenceID }) {
                openKeptPage(page)
            }
        case .reference:
            if result.referenceID.hasPrefix("wonder-compass") {
                selectedSurface = readingSurface(forWonderCompassSectionID: result.referenceID)
            } else if let snippet = BookReferenceCatalog.lorePacks.flatMap(\.snippets).first(where: { $0.id == result.referenceID }) {
                selectedSurface = searchInfoSurface(
                    title: snippet.title,
                    headline: "From the Lore Shelves",
                    body: snippet.body,
                    tags: "lore,search"
                )
            }
        case .anchor:
            if let anchor = anchorLedger.first(where: { $0.id == result.referenceID }) {
                selectedSurface = searchInfoSurface(
                    title: anchor.name,
                    headline: "Outer Stacks: \(anchor.name)",
                    body: "\(anchor.kind.title) Anchor, anchored \(anchor.created). Visits: \(anchor.visitCount).\n\nYour words: \(anchor.playerWords)\n\nRoom: \(anchor.outerStacksRoom)\n\nFae: \(anchor.fae)\n\nLocal rule: \(anchor.localRule)\n\nStand within two hundred meters and press the Location seal to step inside.",
                    tags: "anchor,search"
                )
            }
        case .castMember:
            let pool = NarrativePackRegistry.entities + customCastMembers.map(\.entity)
            if let entity = pool.first(where: { $0.id == result.referenceID }) {
                let glow = BeliefLexicon.glowName(for: max(0, min(100, entity.belief + (entityBeliefLedger[entity.id] ?? 0))))
                let lines = [
                    entity.chapter.map { "Chapter \($0)" },
                    "Glow: \(glow)",
                    entity.traits.isEmpty ? nil : "Traits: \(entity.traits.joined(separator: ", "))",
                    entity.beliefs.first.map { "Believes: \($0)" },
                    entity.goals.first.map { "Wants: \($0)" },
                    entity.unwrittenInterest.map { "Privately studies: \($0)" }
                ].compactMap { $0 }
                selectedSurface = searchInfoSurface(
                    title: entity.name,
                    headline: entity.name,
                    body: lines.joined(separator: "\n\n"),
                    tags: "cast,search,entity:\(entity.id)"
                )
            }
        case .memory, .elective, .pageFamily:
            selectedSurface = searchInfoSurface(
                title: result.title,
                headline: result.title,
                body: result.snippet,
                tags: "search"
            )
        }
    }

    private func searchInfoSurface(title: String, headline: String, body: String, tags: String) -> SurfacePage {
        SurfacePage(
            id: "search-\(title.lowercased().replacingOccurrences(of: " ", with: "-"))-\(Int(Date().timeIntervalSince1970))",
            type: .lore,
            sourceID: "labyrinth-lore",
            intent: .importReference,
            renderStyle: .loreLetter,
            score: 70,
            reason: "Pulled from the Stacks by your own question.",
            prompt: title,
            detail: "Found in the Stacks.",
            payload: BookPagePayload(
                headline: headline,
                body: body,
                metadata: ["source": "labyrinth-lore", "tags": tags, "keptPage": "true"]
            )
        )
    }

    // MARK: - The BookShop

    @MainActor
    func unlockPack(_ packID: String) {
        guard !PackEntitlements.isUnlocked(packID) else { return }
        PackEntitlements.ownedPackIDs.insert(packID)
        vault.data.ownedPacks = Array(PackEntitlements.ownedPackIDs).sorted()
        vault.save()
        surfaceRefreshDate = Date()
        rebuildSurfaceCache()
        let title = BookShopCatalog.listing(forPackID: packID)?.title ?? packID
        statusMessage = "\(title) is bound to your save. New pages will find their way to the desk."
        BookFeedback.play(.braidComplete)
    }

    // MARK: - Fuel arithmetic

    /// Fire-and-forget: the page is already kept; Vellum's assistant adds
    /// the numbers to the chart when the ledger answers.
    func enrichFuelEntry(_ entry: FacultyEntry) {
        Task { @MainActor in
            guard let estimate = await VellumNutritionist.estimate(for: entry.rawText) else { return }
            var amended = entry
            amended.rawText = "\(entry.rawText)\n\(estimate.chartLine)"
            do {
                try BookDatabase.upsertFacultyEntry(amended)
                facultyEntries = (try? BookDatabase.facultyEntries(limit: 160)) ?? facultyEntries
                statusMessage = "Vellum's assistant pencils in the numbers: \(estimate.chartLine)"
                BookFeedback.play(.select)
            } catch {
                appLog.error("Fuel enrichment save failed: \(error.localizedDescription, privacy: .public)")
            }
        }
    }

    // MARK: - The knock

    /// Tap the banner: a knock on the cover. Knock twice within a breath
    /// and something inside answers — usually with knocks, sometimes with
    /// a note slid under the door.
    @MainActor
    func knockOnTheCover() {
        BookFeedback.play(.knock)
        let now = Date()
        defer { lastKnockAt = now }

        guard let last = lastKnockAt, now.timeIntervalSince(last) < 1.2 else {
            return
        }
        knocksThisSession += 1
        lastKnockAt = nil
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(Int.random(in: 650...1_400)))

            let passesNote = knocksThisSession == 1 ? Int.random(in: 0..<4) == 0 : Int.random(in: 0..<3) == 0
            if passesNote || knocksThisSession >= 4 {
                let note = BannerKnockNotes.note(
                    greyLevel: NothingTide.greyLevel(
                        quietDays: NothingTide.quietDays(in: days, today: today.id),
                        narrativeHeat: narrativeEvents.prefix(24).count,
                        distressActive: false
                    ),
                    ascendantChapterName: ascendantTalisman.flatMap { AcademyChapterRegistry.chapter(forTalismanID: $0.id)?.name },
                    hour: Calendar.current.component(.hour, from: now),
                    moonName: MoonPhaseCalendar.phase().name,
                    knocksThisSession: knocksThisSession,
                    roll: Int.random(in: 0..<1_000)
                )
                BookFeedback.play(.select)
                withAnimation(.spring(response: 0.5, dampingFraction: 0.78)) {
                    bookKnockNote = note
                }
                try? await Task.sleep(for: .seconds(6))
                withAnimation(.easeIn(duration: 0.45)) {
                    bookKnockNote = nil
                }
            } else {
                BookFeedback.play(.knockReply)
                withAnimation(.interpolatingSpring(stiffness: 320, damping: 6)) {
                    bannerShudder = true
                }
                try? await Task.sleep(for: .milliseconds(140))
                withAnimation(.interpolatingSpring(stiffness: 320, damping: 8)) {
                    bannerShudder = false
                }
            }
        }
    }
}
