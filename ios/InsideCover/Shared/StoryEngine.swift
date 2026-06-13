import Foundation


enum BeliefCombatParticipantKind: String, Codable, Equatable {
    case player
    case entity
    case npc
    case talisman
    case nothing
    case location
    case object
    case thread

    var floor: Int {
        switch self {
        case .player, .nothing:
            return 0
        case .entity, .npc, .talisman, .location, .object, .thread:
            return 5
        }
    }
}

enum BeliefCombatDifficulty: String, Codable, Equatable, CaseIterable {
    case routine
    case standard
    case dramatic
    case desperate

    var modifier: Int {
        switch self {
        case .routine:
            return 15
        case .standard:
            return 0
        case .dramatic:
            return -15
        case .desperate:
            return -25
        }
    }
}

enum BeliefCombatOutcome: String, Codable, Equatable {
    case criticalSuccess
    case success
    case nearMiss
    case failure
    case criticalFailure

    var title: String {
        switch self {
        case .criticalSuccess:
            return "critical success"
        case .success:
            return "success"
        case .nearMiss:
            return "near miss"
        case .failure:
            return "failure"
        case .criticalFailure:
            return "critical failure"
        }
    }
}

struct BeliefCombatResult: Codable, Equatable {
    var attackerName: String
    var attackerKind: BeliefCombatParticipantKind
    var targetName: String
    var targetKind: BeliefCombatParticipantKind
    var attackerBeliefBefore: Int
    var attackerBeliefAfter: Int
    var targetBeliefBefore: Int
    var targetBeliefAfter: Int
    var requestedSpend: Int
    var actualSpend: Int
    var dealt: Int
    var backlash: Int
    var roll: Int
    var threshold: Int
    var difficulty: BeliefCombatDifficulty
    var outcome: BeliefCombatOutcome

    var landed: Bool {
        dealt > 0
    }

    var summaryLine: String {
        let rollText = "rolled \(roll) against \(threshold)"
        if backlash > 0 {
            return "\(attackerName) \(rollText): \(outcome.title); the attack backfired for \(backlash) Belief."
        }
        if dealt > 0 {
            return "\(attackerName) \(rollText): \(outcome.title); \(targetName) lost \(dealt) Belief."
        }
        return "\(attackerName) \(rollText): \(outcome.title); nothing landed."
    }
}

enum BeliefCombatResolver {
    static func difficulty(forTargetBelief belief: Int) -> BeliefCombatDifficulty {
        switch belief {
        case ..<25:
            return .routine
        case ..<55:
            return .standard
        case ..<80:
            return .dramatic
        default:
            return .desperate
        }
    }

    static func baseThreshold(for belief: Int) -> Int {
        min(85, Int(40 + Double(max(0, min(100, belief))) * 0.45))
    }

    static func finalThreshold(for belief: Int, difficulty: BeliefCombatDifficulty) -> Int {
        max(20, min(90, baseThreshold(for: belief) + difficulty.modifier))
    }

    static func resolve(
        attackerName: String,
        attackerKind: BeliefCombatParticipantKind,
        attackerBelief: Int,
        targetName: String,
        targetKind: BeliefCombatParticipantKind,
        targetBelief: Int,
        spend requestedSpend: Int,
        difficulty: BeliefCombatDifficulty,
        roll: Int? = nil
    ) -> BeliefCombatResult {
        let attackerBelief = max(0, min(100, attackerBelief))
        let targetBelief = max(0, min(100, targetBelief))
        let spend = max(0, requestedSpend)
        let threshold = finalThreshold(for: attackerBelief, difficulty: difficulty)
        let roll = roll ?? Int.random(in: 1...100)
        let margin = roll - threshold
        let outcome: BeliefCombatOutcome
        if roll <= 5 {
            outcome = .criticalSuccess
        } else if roll >= 96 {
            outcome = .criticalFailure
        } else if roll <= threshold {
            outcome = margin >= -10 ? .nearMiss : .success
        } else {
            outcome = margin <= 10 ? .nearMiss : .failure
        }

        let rawDeal: Int
        switch outcome {
        case .criticalSuccess:
            rawDeal = max(1, Int((Double(spend) * 1.5).rounded()))
        case .success:
            rawDeal = spend
        case .nearMiss:
            rawDeal = max(1, Int((Double(spend) * 0.5).rounded()))
        case .failure:
            rawDeal = 0
        case .criticalFailure:
            rawDeal = -spend
        }

        let attackerFloor = attackerKind.floor
        let targetFloor = targetKind.floor
        let actualSpend = min(spend, max(0, attackerBelief - attackerFloor))
        let backfired = rawDeal < 0
        let backlash = backfired ? min(abs(rawDeal), max(0, attackerBelief - actualSpend - attackerFloor)) : 0
        let actualDeal = backfired ? 0 : min(rawDeal, max(0, targetBelief - targetFloor))
        let attackerAfter = max(attackerFloor, attackerBelief - actualSpend - backlash)
        let targetAfter = backfired ? targetBelief : max(targetFloor, targetBelief - actualDeal)

        return BeliefCombatResult(
            attackerName: attackerName,
            attackerKind: attackerKind,
            targetName: targetName,
            targetKind: targetKind,
            attackerBeliefBefore: attackerBelief,
            attackerBeliefAfter: attackerAfter,
            targetBeliefBefore: targetBelief,
            targetBeliefAfter: targetAfter,
            requestedSpend: spend,
            actualSpend: actualSpend,
            dealt: actualDeal,
            backlash: backlash,
            roll: roll,
            threshold: threshold,
            difficulty: difficulty,
            outcome: outcome
        )
    }
}

enum StoryChoiceRole: String, Codable, Equatable, CaseIterable {
    case sliceOfLife
    case progressArc
    case surprise

    var title: String {
        switch self {
        case .sliceOfLife:
            return "Slice of Life"
        case .progressArc:
            return "Progress Arc"
        case .surprise:
            return "Something Surprising"
        }
    }

    var directorInstruction: String {
        switch self {
        case .sliceOfLife:
            return "A grounded, ordinary choice that tends the day without forcing plot."
        case .progressArc:
            return "A choice that advances the selected story thread or current arc."
        case .surprise:
            return "A sideways choice that still belongs to this scene and reveals an unexpected connection."
        }
    }
}

struct StorySceneChoice: Identifiable, Codable, Equatable {
    var id: String
    var role: StoryChoiceRole
    var title: String
    var prompt: String
    var hiddenEffect: String
    var beliefDelta: Int
    var targetEntityIDs: [String]
    var targetThreadIDs: [String]
}

struct StoryScenePacket: Identifiable, Codable, Equatable {
    var id: String
    var packID: String
    var title: String
    var directorIntent: String
    var playerBelief: Int
    var bookGlow: String
    var realSignals: [String]
    var selectedEntities: [NarrativeWorldEntity]
    var selectedThreads: [NarrativeStoryThread]
    var selectedRelationships: [NarrativeRelationshipEdge]
    var selectedEntityMemories: [NarrativeEntityMemory]
    var relationshipPressures: [String]
    var chapterTalismanMoves: [ChapterTalismanBeliefMove]
    var choices: [StorySceneChoice]
    var storyFormID: String?
    var storyFormName: String?
    var storyFormBeats: [String]?
    var storyGenreID: String?
    var storyGenreName: String?
    var storyGenreLens: String?
}

enum StoryScenePacketBuilder {
    static func packet(for day: BookDay, inputs: BookSourceInputs, now: Date = Date()) -> StoryScenePacket {
        let tags = contextTags(for: day, inputs: inputs, now: now)
        let selectedEntities = rankedEntities(tags: tags, inputs: inputs, limit: 3)
        var selectedThreads = rankedThreads(tags: tags, inputs: inputs, limit: 2)
        if let arc = inputs.currentArc,
           let arcThread = NarrativePackRegistry.threads.first(where: { $0.id == arc.threadID }) {
            selectedThreads.removeAll { $0.id == arc.threadID }
            selectedThreads.insert(arcThread, at: 0)
            selectedThreads = Array(selectedThreads.prefix(2))
        }
        let primaryThread = selectedThreads.first
        let primaryEntity = selectedEntities.first
        let selectedRelationships = rankedRelationships(
            tags: tags,
            entities: selectedEntities,
            threads: selectedThreads,
            inputs: inputs,
            limit: 3
        )
        let selectedEntityMemories = rankedEntityMemories(
            entities: selectedEntities,
            inputs: inputs,
            limit: 5
        )
        let belief = inputs.narrative?.beliefWeight ?? 30
        var realSignals = realSignals(for: day, inputs: inputs)
        let talismanPool = NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity)
        if let ascendant = TalismanAscendancy.ascendant(entities: talismanPool, beliefOffsets: inputs.entityBeliefOffsets) {
            realSignals.append(TalismanAscendancy.influenceLine(for: ascendant))
        }
        if let arc = inputs.currentArc {
            realSignals.append("CURRENT ARC: \u{201C}\(arc.title)\u{201D} is in its \(arc.phase.rawValue) phase. \(ArcKeeper.directive(for: arc.phase))")
        }
        let greyLevel = NothingTide.greyLevel(
            quietDays: inputs.quietDays,
            narrativeHeat: inputs.narrative?.recentEventCount ?? 0,
            distressActive: false
        )
        if let greySignal = NothingTide.storySignal(forGreyLevel: greyLevel) {
            realSignals.append(greySignal)
        }
        if let chapterFact = inputs.selfFacts.first(where: { $0.questionID == "chapter-binding" }),
           let chapter = AcademyChapterRegistry.chapter(named: chapterFact.answer) {
            realSignals.append("The player is bound to Chapter \(chapter.name): \(chapter.philosophy) Let their chapter's way of seeing tint how the scene meets them.")
        }
        let relationships = relationshipPressures(
            entities: selectedEntities,
            threads: selectedThreads,
            selectedRelationships: selectedRelationships,
            day: day,
            inputs: inputs
        )
        let talismanMoves = ChapterTalismanBeliefMoves.moves(
            for: selectedEntities,
            seed: packetStableIndex(for: "\(day.id)-\(SurfaceCadence.slotID(for: now, hours: 4))-story-talisman-options", count: 10_000)
        )
        let title = primaryThread.map { "Story Page: \($0.title)" } ?? "Story Page"
        let intent = directorIntent(primaryThread: primaryThread, primaryEntity: primaryEntity, tags: tags)

        let ascendantChapterID = TalismanAscendancy.ascendant(
            entities: NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity),
            beliefOffsets: inputs.entityBeliefOffsets
        ).flatMap { AcademyChapterRegistry.chapter(forTalismanID: $0.id)?.id }
        let (storyForm, storyGenre) = StoryFormRegistry.select(
            tags: tags,
            surfaceHistory: inputs.surfaceHistory,
            ascendantChapterID: ascendantChapterID,
            dayID: day.id,
            slot: SurfaceCadence.slotID(for: now, hours: 4),
            now: now
        )

        return StoryScenePacket(
            id: "story-packet-\(day.id)-\(SurfaceCadence.slotID(for: now, hours: 4))",
            packID: NarrativePackRegistry.corePackID,
            title: title,
            directorIntent: intent,
            playerBelief: belief,
            bookGlow: BeliefLexicon.glowName(for: belief),
            realSignals: realSignals,
            selectedEntities: selectedEntities,
            selectedThreads: selectedThreads,
            selectedRelationships: selectedRelationships,
            selectedEntityMemories: selectedEntityMemories,
            relationshipPressures: relationships,
            chapterTalismanMoves: talismanMoves,
            choices: choices(primaryThread: primaryThread, primaryEntity: primaryEntity),
            storyFormID: storyForm.id,
            storyFormName: storyForm.name,
            storyFormBeats: storyForm.beats,
            storyGenreID: storyGenre.id,
            storyGenreName: storyGenre.name,
            storyGenreLens: storyGenre.lens
        )
    }

    private static func availableEntities(inputs: BookSourceInputs) -> [NarrativeWorldEntity] {
        NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity)
    }

    private static func rankedEntities(tags: Set<String>, inputs: BookSourceInputs, limit: Int) -> [NarrativeWorldEntity] {
        availableEntities(inputs: inputs)
            // Talismans influence the scene's tone through ascendancy; they
            // do not compete with people and places for scene slots.
            .filter { $0.kind != .talisman }
            .map { entity in
                let overlap = tags.intersection(Set(entity.tags)).count
                let narrativeBoost = entity.name == "The Book" ? 4 : 0
                let eventBoost = inputs.narrative?.weightedEntityIDs.contains(entity.id) == true ? 18 : 0
                return (entity, entity.narrativeWeight + entity.belief / 4 + overlap * 8 + narrativeBoost + eventBoost)
            }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.id < right.0.id
                }
                return left.1 > right.1
            }
            .prefix(limit)
            .map(\.0)
    }

    private static func rankedEntityMemories(
        entities: [NarrativeWorldEntity],
        inputs: BookSourceInputs,
        limit: Int,
        now: Date = Date()
    ) -> [NarrativeEntityMemory] {
        let entityIDs = Set(entities.map(\.id))
        let candidates = (inputs.narrative?.entityMemories ?? [])
            .filter { entityIDs.contains($0.entityID) }

        // Blend recency tiers so a character can mention both this morning
        // and two weeks ago: fresh memories get a boost, but mid-range ones
        // stay competitive, and one deliberately older memory is reserved a
        // slot when available.
        func recencyBoost(_ memory: NarrativeEntityMemory) -> Int {
            let age = now.timeIntervalSince(memory.createdAt)
            if age < 24 * 3600 { return 8 }
            if age < 3 * 24 * 3600 { return 5 }
            if age < 14 * 24 * 3600 { return 2 }
            return 0
        }
        let ranked = candidates.sorted { left, right in
            let leftScore = left.narrativeWeight + recencyBoost(left)
            let rightScore = right.narrativeWeight + recencyBoost(right)
            if leftScore == rightScore {
                return left.createdAt > right.createdAt
            }
            return leftScore > rightScore
        }
        var selected = Array(ranked.prefix(limit))

        // Reserve the final slot for the strongest memory older than three
        // days, so long continuity survives a week of busy fresh pages.
        let hasOlder = selected.contains { now.timeIntervalSince($0.createdAt) > 3 * 24 * 3600 }
        if !hasOlder,
           let older = ranked.first(where: { now.timeIntervalSince($0.createdAt) > 3 * 24 * 3600 }),
           !selected.isEmpty {
            selected[selected.count - 1] = older
        }
        return selected
    }

    private static func rankedThreads(tags: Set<String>, inputs: BookSourceInputs, limit: Int) -> [NarrativeStoryThread] {
        NarrativePackRegistry.threads
            .map { thread in
                let overlap = tags.intersection(Set(thread.tags)).count
                let eventBoost = inputs.narrative?.weightedThreadIDs.contains(thread.id) == true ? 18 : 0
                return (thread, thread.narrativeWeight + thread.belief / 3 + overlap * 10 + eventBoost)
            }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.id < right.0.id
                }
                return left.1 > right.1
            }
            .prefix(limit)
            .map(\.0)
    }

    private static func rankedRelationships(
        tags: Set<String>,
        entities: [NarrativeWorldEntity],
        threads: [NarrativeStoryThread],
        inputs: BookSourceInputs,
        limit: Int
    ) -> [NarrativeRelationshipEdge] {
        let selectedNodeIDs = Set(entities.map(\.id) + threads.map(\.id))
        return NarrativePackRegistry.relationships
            .map { relationship in
                let overlap = tags.intersection(Set(relationship.tags)).count
                let sourceMatches = selectedNodeIDs.contains(relationship.sourceEntityID) ? 6 : 0
                let targetMatches = selectedNodeIDs.contains(relationship.targetEntityID) ? 6 : 0
                let trustBias = relationship.trust / 4
                let eventBoost = inputs.narrative?.weightedRelationshipIDs.contains(relationship.id) == true ? 18 : 0
                return (relationship, relationship.narrativeWeight + overlap * 8 + sourceMatches + targetMatches + trustBias + eventBoost)
            }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.id < right.0.id
                }
                return left.1 > right.1
            }
            .prefix(limit)
            .map(\.0)
    }

    private static func contextTags(for day: BookDay, inputs: BookSourceInputs, now: Date) -> Set<String> {
        var tags = Set<String>()
        for page in day.capturedPages {
            tags.formUnion(page.tags.map { $0.lowercased() })
            let lowered = "\(page.promptText) \(page.userInput)".lowercased()
            if lowered.contains("music") || lowered.contains("spotify") || lowered.contains("headphone") {
                tags.formUnion(["music", "shelter", "mood"])
            }
            if lowered.contains("weather") || lowered.contains("rain") || lowered.contains("sun") || lowered.contains("sky") {
                tags.formUnion(["weather", "atmosphere"])
            }
            if lowered.contains("tired") || lowered.contains("rest") || lowered.contains("body") || lowered.contains("fuel") {
                tags.formUnion(["body", "rest", "care"])
            }
            if lowered.contains("object") || lowered.contains("coffee") || lowered.contains("lamp") {
                tags.formUnion(["objects", "daily", "wonder"])
            }
        }
        if inputs.weather != nil {
            tags.formUnion(["weather", "atmosphere", "bleed"])
        }
        if inputs.body != nil {
            tags.formUnion(["body", "care"])
        }
        for fact in inputs.selfFacts where fact.usePermission != .doNotUse {
            tags.formUnion(fact.tags.map { $0.lowercased() })
        }
        if let narrative = inputs.narrative {
            tags.formUnion(narrative.recentTags.map { $0.lowercased() })
        }
        if tags.isEmpty {
            tags.formUnion(["daily", "wonder", "belief"])
        }
        return tags
    }

    private static func realSignals(for day: BookDay, inputs: BookSourceInputs) -> [String] {
        var signals: [String] = []
        if let weather = inputs.weather {
            signals.append("Weather: \(weather.currentTemperature ?? weather.phrase)")
            if let forecast = weather.forecast {
                signals.append("Forecast: \(forecast)")
            }
        }
        if let body = inputs.body {
            signals.append("Body Page: \(body.status.lowercased())")
        }
        for page in day.capturedPages.suffix(3) {
            let text = page.userInput.isEmpty ? page.promptText : page.userInput
            signals.append("\(page.type.shortTitle): \(text)")
        }
        return signals
    }

    private static func relationshipPressures(
        entities: [NarrativeWorldEntity],
        threads: [NarrativeStoryThread],
        selectedRelationships: [NarrativeRelationshipEdge],
        day: BookDay,
        inputs: BookSourceInputs
    ) -> [String] {
        var pressures = selectedRelationships.map { edge in
            "\(label(for: edge.sourceEntityID)) -> \(label(for: edge.targetEntityID)): \(edge.note)"
        }
        pressures.append(contentsOf: threads.prefix(2).map { "The reader and \($0.title) have a returning thread." })
        if entities.contains(where: { $0.id == "weather-page" }), inputs.weather != nil {
            pressures.append("The Weather Page is already tinting the day.")
        }
        if entities.contains(where: { $0.id == "body-page" }), inputs.body != nil {
            pressures.append("The Body Page asks for humane pacing.")
        }
        if day.capturedPages.contains(where: { $0.tags.contains("souvenir") }) {
            pressures.append("A kept souvenir can become evidence in the scene.")
        }
        return pressures
    }

    private static func label(for nodeID: String) -> String {
        if let entity = NarrativePackRegistry.entities.first(where: { $0.id == nodeID }) {
            return entity.name
        }
        if let thread = NarrativePackRegistry.threads.first(where: { $0.id == nodeID }) {
            return thread.title
        }
        return nodeID
    }

    private static func packetStableIndex(for key: String, count: Int) -> Int {
        guard count > 0 else { return 0 }
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in key.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return Int(hash % UInt64(count))
    }

    private static func directorIntent(
        primaryThread: NarrativeStoryThread?,
        primaryEntity: NarrativeWorldEntity?,
        tags: Set<String>
    ) -> String {
        if let primaryThread, let primaryEntity {
            return "Write a grounded, magical vignette where \(primaryEntity.name) helps \(primaryThread.title) press gently on the reader's real day."
        }
        if tags.contains("rest") || tags.contains("care") {
            return "Write a low-pressure vignette where the Book protects the reader from turning care into homework."
        }
        return "Write a grounded, magical vignette where ordinary evidence becomes story without leaving real life."
    }

    private static func choices(
        primaryThread: NarrativeStoryThread?,
        primaryEntity: NarrativeWorldEntity?
    ) -> [StorySceneChoice] {
        let entityID = primaryEntity?.id ?? "the-book"
        let entityName = primaryEntity?.name ?? "The Book"
        let threadID = primaryThread?.id ?? "ordinary-magic"
        let threadTitle = primaryThread?.title ?? "Ordinary Magic"

        return [
            StorySceneChoice(
                id: "slice-of-life",
                role: .sliceOfLife,
                title: "Stay With The Small Thing",
                prompt: "Choose the ordinary detail that still feels alive.",
                hiddenEffect: "Deepen attention without forcing the plot; add narrative weight to \(entityName).",
                beliefDelta: 1,
                targetEntityIDs: [entityID],
                targetThreadIDs: []
            ),
            StorySceneChoice(
                id: "progress-arc",
                role: .progressArc,
                title: "Follow The Thread",
                prompt: "Let \(threadTitle) take one real step forward.",
                hiddenEffect: "Advance the selected story thread and prepare a future consequence page.",
                beliefDelta: 1,
                targetEntityIDs: [],
                targetThreadIDs: [threadID]
            ),
            StorySceneChoice(
                id: "surprise",
                role: .surprise,
                title: "Open The Side Door",
                prompt: "Ask what unexpected thing in this scene has been waiting to matter.",
                hiddenEffect: "Create or connect a motif; the surprise must still be anchored to the scene packet.",
                beliefDelta: 1,
                targetEntityIDs: [entityID],
                targetThreadIDs: [threadID]
            )
        ]
    }
}

enum GossipSimulationBuilder {
    static func surface(for day: BookDay, inputs: BookSourceInputs, now: Date = Date()) -> SurfacePage {
        let turns = simulationTurns(for: day, inputs: inputs, now: now)
        let primary = turns.first ?? simulationTurn(for: day, inputs: inputs, now: now, offset: 0)
        let source = BookPageSourceRegistry.source(for: .gossip)
        let body = [
            turns.map { turn in
                [
                    turn.overheardLine,
                    turn.visibleTrace,
                    turn.consequenceLines.map { "• \($0)" }.joined(separator: "\n")
                ].joined(separator: "\n")
            }.joined(separator: "\n\n"),
            "What changed:",
            turns.flatMap(\.consequenceLines).map { "• \($0)" }.joined(separator: "\n")
        ]
            .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            .joined(separator: "\n\n")
        let tags = Array(Set(turns.flatMap(\.tags))).sorted()
        let talismanMoves = turns.compactMap(\.chapterTalismanMove)
        let talismanDeltaTokens = talismanMoves.compactMap(\.ledgerToken)
        let simulationPacket = turns.enumerated().map { index, turn in
            let talismanMove = turn.chapterTalismanMove.map { "\nChapter talisman move: \($0.summaryLine)" } ?? ""
            return """
            TURN \(index + 1)
            Actor: \(turn.actorName) [\(turn.actorID)]
            Thread: \(turn.threadTitle) [\(turn.threadID)]
            Simulation action: \(turn.actionKind.rawValue)
            Overheard line: \(turn.overheardLine)
            Visible trace: \(turn.visibleTrace)
            \(talismanMove)
            Hidden effect to preserve: \(turn.hiddenEffect)
            Consequences:
            \(turn.consequenceLines.map { "- \($0)" }.joined(separator: "\n"))
            """
        }.joined(separator: "\n\n")

        return SurfacePage(
            id: "\(source.id)-\(primary.id)",
            type: .gossip,
            sourceID: source.id,
            intent: .simulate,
            renderStyle: .graphEvent,
            score: score(for: day, inputs: inputs),
            reason: "The story field moved while the Book was half-open.",
            prompt: "Gossip from the Margins",
            detail: primary.overheardLine,
            payload: BookPagePayload(
                headline: turns.count == 1 ? "The margins carried a rumor." : "The margins carried \(turns.count) rumors.",
                body: body,
                metadata: [
                    "source": source.id,
                    "turnID": primary.id,
                    "turnIDs": turns.map(\.id).joined(separator: ","),
                    "actorID": primary.actorID,
                    "actorIDs": turns.map(\.actorID).joined(separator: ","),
                    "actorName": primary.actorName,
                    "actorNames": turns.map(\.actorName).joined(separator: ", "),
                    "threadID": primary.threadID,
                    "threadIDs": turns.map(\.threadID).joined(separator: ","),
                    "threadTitle": primary.threadTitle,
                    "threadTitles": turns.map(\.threadTitle).joined(separator: ", "),
                    "actionKind": primary.actionKind.rawValue,
                    "actionKinds": turns.map { $0.actionKind.rawValue }.joined(separator: ","),
                    "beliefCombat": turns.compactMap { $0.beliefCombat?.summaryLine }.joined(separator: " | "),
                    "beliefCombatDeals": turns.compactMap { turn in
                        guard let combat = turn.beliefCombat else { return nil }
                        return "\(turn.actorID)->\(turn.threadID):spend=\(combat.actualSpend),deal=\(combat.dealt),backlash=\(combat.backlash),roll=\(combat.roll),threshold=\(combat.threshold)"
                    }.joined(separator: " | "),
                    "chapterTalismanMoves": talismanMoves.map(\.summaryLine).joined(separator: " | "),
                    "chapterTalismanDeltas": talismanDeltaTokens.joined(separator: ","),
                    "hiddenEffect": turns.map(\.hiddenEffect).joined(separator: " | "),
                    "consequences": turns.flatMap(\.consequenceLines).joined(separator: " | "),
                    "simulationPacket": simulationPacket,
                    "gossipDraft": body,
                    "tags": tags.joined(separator: ",")
                ]
            )
        )
    }

    private static func simulationTurns(for day: BookDay, inputs: BookSourceInputs, now: Date) -> [GossipSimulationTurn] {
        let count = min(3, max(2, 1 + day.capturedPages.count / 3))
        return (0..<count).map { offset in
            simulationTurn(for: day, inputs: inputs, now: now, offset: offset)
        }
    }

    private static func simulationTurn(for day: BookDay, inputs: BookSourceInputs, now: Date, offset: Int) -> GossipSimulationTurn {
        let slotID = SurfaceCadence.slotID(for: now, hours: 4)
        let seed = stableIndex(for: "\(day.id)-\(slotID)-gossip-\(offset)", count: 10_000)
        let tags = contextTags(for: day, inputs: inputs)
        let actors = rankedActors(tags: tags, inputs: inputs, seed: seed)
        let threads = rankedThreads(tags: tags, inputs: inputs, seed: seed)
        let actor = pick(actors, offset: offset) ?? fallbackActor
        let thread = pick(threads, offset: offset) ?? fallbackThread
        let witness = witnessActor(among: actors, excluding: actor, offset: offset)
        let actionKind = actionKind(for: actor, thread: thread, tags: tags, seed: seed)
        let combat = beliefCombat(actor: actor, thread: thread, actionKind: actionKind, seed: seed)
        let talismanMove = ChapterTalismanBeliefMoves.move(for: actor, actionKind: actionKind, seed: seed)
        let readerEcho = readerEchoSnippet(for: day, seed: seed)
        let constellationHook = constellationHook(for: actor, thread: thread, inputs: inputs)
        let trace = visibleTrace(actor: actor, witness: witness, thread: thread, actionKind: actionKind, tags: tags, seed: seed, talismanMove: talismanMove)
        let overheard = overheardLine(actor: actor, witness: witness, thread: thread, actionKind: actionKind, seed: seed)
        var consequences = consequenceLines(actor: actor, thread: thread, actionKind: actionKind, beliefCombat: combat, talismanMove: talismanMove)
        if let readerEcho {
            consequences.append("The margins matched it to one of the reader's own kept pages: \"\(readerEcho)\"")
        }
        if let constellationHook {
            consequences.append(constellationHook)
        }
        let turnTags = Array(Set(tags)
            .union(actor.tags)
            .union(thread.tags)
            .union([
                "gossip",
                "simulation",
                actionKind.rawValue,
                "actor:\(actor.id)",
                "thread:\(thread.id)",
                "action:\(actionKind.rawValue)"
            ])
            .union(witness.map { ["witness:\($0.id)"] } ?? [])
            .union(talismanMove.map { ["chapter-talisman", "talisman:\($0.targetTalismanID)", "chapter:\($0.targetChapter.lowercased())", "talisman-move:\($0.kind.rawValue)"] } ?? [])
        ).sorted()

        return GossipSimulationTurn(
            id: "gossip-turn-\(day.id)-\(slotID)-\(offset + 1)",
            actorID: actor.id,
            actorName: actor.name,
            threadID: thread.id,
            threadTitle: thread.title,
            actionKind: actionKind,
            overheardLine: overheard,
            visibleTrace: trace,
            hiddenEffect: hiddenEffect(actor: actor, thread: thread, actionKind: actionKind),
            consequenceLines: consequences,
            tags: turnTags,
            beliefCombat: combat,
            chapterTalismanMove: talismanMove
        )
    }

    private static func score(for day: BookDay, inputs: BookSourceInputs) -> Int {
        var score = 62
        score += min(day.capturedPages.count * 4, 16)
        if inputs.weather != nil { score += 6 }
        if inputs.body != nil { score += 5 }
        if inputs.narrative?.recentTags.isEmpty == false { score += 8 }
        return min(score, 88)
    }

    private static func rankedActors(tags: Set<String>, inputs: BookSourceInputs, seed: Int) -> [NarrativeWorldEntity] {
        (NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity))
            .filter { entity in
                entity.kind == .character || entity.kind == .motif || entity.kind == .object || entity.kind == .talisman || entity.kind == .classRoom
            }
            .map { entity in
                let overlap = tags.intersection(Set(entity.tags)).count
                let eventBoost = inputs.narrative?.weightedEntityIDs.contains(entity.id) == true ? 16 : 0
                let jitter = stableIndex(for: "\(entity.id)-\(seed)", count: 7)
                return (entity, entity.narrativeWeight + entity.belief / 4 + overlap * 9 + eventBoost + jitter)
            }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.id < right.0.id
                }
                return left.1 > right.1
            }
            .map(\.0)
    }

    private static func rankedThreads(tags: Set<String>, inputs: BookSourceInputs, seed: Int) -> [NarrativeStoryThread] {
        NarrativePackRegistry.threads
            .map { thread in
                let overlap = tags.intersection(Set(thread.tags)).count
                let eventBoost = inputs.narrative?.weightedThreadIDs.contains(thread.id) == true ? 16 : 0
                let phaseBoost = thread.phase == .rising || thread.phase == .returning ? 6 : 0
                let jitter = stableIndex(for: "\(thread.id)-\(seed)", count: 7)
                return (thread, thread.narrativeWeight + thread.belief / 3 + overlap * 10 + eventBoost + phaseBoost + jitter)
            }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.id < right.0.id
                }
                return left.1 > right.1
            }
            .map(\.0)
    }

    private static func contextTags(for day: BookDay, inputs: BookSourceInputs) -> Set<String> {
        var tags = Set<String>()
        for page in day.capturedPages.suffix(8) {
            tags.formUnion(page.tags.map { $0.lowercased() })
            let text = "\(page.promptText) \(page.userInput)".lowercased()
            if text.contains("weather") || text.contains("sky") || text.contains("rain") || text.contains("sun") {
                tags.formUnion(["weather", "atmosphere", "bleed"])
            }
            if text.contains("body") || text.contains("rest") || text.contains("fuel") || text.contains("tired") {
                tags.formUnion(["body", "rest", "care"])
            }
            if text.contains("music") || text.contains("spotify") || text.contains("headphone") {
                tags.formUnion(["music", "shelter"])
            }
        }
        if inputs.weather != nil {
            tags.formUnion(["weather", "atmosphere", "bleed"])
        }
        if inputs.body != nil {
            tags.formUnion(["body", "care"])
        }
        if let narrative = inputs.narrative {
            tags.formUnion(narrative.recentTags.map { $0.lowercased() })
        }
        if tags.isEmpty {
            tags.formUnion(["ordinary", "belief", "wonder"])
        }
        return tags
    }

    private static func actionKind(
        for actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        tags: Set<String>,
        seed: Int
    ) -> GossipSimulationActionKind {
        if actor.tags.contains("nothing") || actor.faults.contains(where: { $0.localizedCaseInsensitiveContains("attack") }) || thread.tags.contains("tension") {
            return .attackBelief
        }
        if tags.contains("care") || tags.contains("body") || actor.traits.contains(where: { $0.localizedCaseInsensitiveContains("care") }) {
            return .takeAction
        }
        return seed % 3 == 0 ? .takeAction : .investBelief
    }

    private static func witnessActor(
        among actors: [NarrativeWorldEntity],
        excluding actor: NarrativeWorldEntity,
        offset: Int
    ) -> NarrativeWorldEntity? {
        let characters = actors.filter { $0.kind == .character && $0.id != actor.id }
        guard !characters.isEmpty else { return nil }
        return characters[(offset + 1) % characters.count]
    }

    /// A short fragment of the reader's own day, so the rumor lands close
    /// to home instead of floating in generic margin-space.
    private static func readerEchoSnippet(for day: BookDay, seed: Int) -> String? {
        let candidates = day.capturedPages.suffix(8).compactMap { page -> String? in
            let text = page.userInput.trimmingCharacters(in: .whitespacesAndNewlines)
            guard text.count >= 12 else { return nil }
            return text.bookPreviewSentenceLimit(1)
        }
        guard !candidates.isEmpty else { return nil }
        let snippet = candidates[stableIndex(for: "reader-echo-\(seed)", count: candidates.count)]
        return snippet.count > 90 ? String(snippet.prefix(87)) + "..." : snippet
    }

    /// If the Book keeps a named constellation that touches this turn, the
    /// rumor knows about it. The world reading the Book's own marginalia is
    /// the juiciest gossip there is.
    private static func constellationHook(
        for actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        inputs: BookSourceInputs
    ) -> String? {
        let named = ConstellationKeeper.namedConstellations(inputs.constellations)
        guard let match = named.first(where: { constellation in
            constellation.relatedEntityIDs.contains(actor.id)
                || constellation.tags.contains(where: { thread.tags.contains($0) || actor.tags.contains($0) })
        }) ?? named.first else {
            return nil
        }
        return "Some in the stacks whisper that this touches \(match.displayName), the constellation the Book keeps about the reader."
    }

    private static func juicyDetail(for actor: NarrativeWorldEntity, seed: Int) -> String {
        var details: [String] = []
        if let quirk = actor.quirks.first {
            details.append("everyone pretends not to know that \(actor.name) \(quirk)")
        }
        if let fault = actor.faults.first {
            details.append("the unkind version says it is just \(actor.name) being \(fault) again")
        }
        if let belief = actor.beliefs.first {
            details.append("\(actor.name) has always insisted that \(belief), and this looks like acting on it")
        }
        if let interest = actor.unwrittenInterest {
            details.append("those who know \(actor.name) say the real question underneath is: \(interest)")
        }
        guard !details.isEmpty else {
            return "no one can agree on why, which is how you know it matters"
        }
        return details[stableIndex(for: "\(actor.id)-\(seed)-juice", count: details.count)]
    }

    private static func visibleTrace(
        actor: NarrativeWorldEntity,
        witness: NarrativeWorldEntity?,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind,
        tags: Set<String>,
        seed: Int,
        talismanMove: ChapterTalismanBeliefMove?
    ) -> String {
        let stakes: String
        if let goal = actor.goals.first, let fault = actor.faults.first {
            stakes = " If it works: \(goal) If it curdles, \"\(fault)\" becomes the story everyone tells at breakfast."
        } else if let goal = actor.goals.first {
            stakes = " What is at stake, plainly: \(goal)"
        } else {
            stakes = " No one called it important. The margins disagreed."
        }

        let witnessLine: String
        if let witness {
            let reactions = [
                "\(witness.name) saw it happen and has been conspicuously silent, which from \(witness.name) is practically a public statement.",
                "\(witness.name) claims not to have been watching. \(witness.name) was absolutely watching.",
                "\(witness.name) reported it to exactly three people, each sworn to secrecy, which is how the whole Academy knows by now."
            ]
            witnessLine = " " + reactions[stableIndex(for: "\(witness.id)-\(seed)-reaction", count: reactions.count)]
        } else {
            witnessLine = ""
        }

        let talismanTrace: String
        if let talismanMove {
            switch talismanMove.kind {
            case .giveBelief:
                talismanTrace = " A chapter talisman warmed: \(talismanMove.summaryLine)"
            case .takeBelief:
                talismanTrace = " A rival talisman answered: \(talismanMove.summaryLine)"
            }
        } else {
            talismanTrace = ""
        }

        let move: String
        switch actionKind {
        case .takeAction:
            move = "\(actor.name) made a real move inside \(thread.title) - \(juicyDetail(for: actor, seed: seed))."
        case .investBelief:
            move = "\(actor.name) tucked Belief into \(thread.title) when it thought no one was looking - \(juicyDetail(for: actor, seed: seed))."
        case .attackBelief:
            move = "\(actor.name) went after a brittle edge of \(thread.title), in the open, where everyone could see - \(juicyDetail(for: actor, seed: seed))."
        }
        return move + stakes + witnessLine + talismanTrace
    }

    private static func overheardLine(
        actor: NarrativeWorldEntity,
        witness: NarrativeWorldEntity?,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind,
        seed: Int
    ) -> String {
        let attribution = witness.map { "Overheard by \($0.name)" } ?? "Overheard in the stacks"
        let quirkAside = actor.quirks.first.map { " - and yes, \($0), as always" } ?? ""
        let templates: [String]
        switch actionKind {
        case .takeAction:
            templates = [
                "\"\(actor.name) was at \(thread.title) again before the lamps were lit\(quirkAside). The ink was still wet when I passed.\"",
                "\"Don't quote me, but \(actor.name) just moved something inside \(thread.title), and it was not a small something.\"",
                "\"Third time I've caught \(actor.name) near \(thread.title) this chapter. Once is errand, twice is habit, three times is plot.\""
            ]
        case .investBelief:
            templates = [
                "\"\(actor.name) is pouring Belief into \(thread.title) and won't say why. When \(actor.name) goes quiet about money, watch the money.\"",
                "\"I saw the glow myself - \(actor.name) fed \(thread.title) like it owed the thread an apology.\"",
                "\"\(actor.name) swears it's nothing. \(actor.name) only ever says 'it's nothing' about the things that are something.\""
            ]
        case .attackBelief:
            templates = [
                "\"\(actor.name) finally said out loud what it's been thinking about \(thread.title), and the shelves are still rattling.\"",
                "\"It wasn't an argument, exactly. \(actor.name) just asked \(thread.title) one question, and the question had teeth.\"",
                "\"Someone had to test whether \(thread.title) is still real or just well-rehearsed. Trust \(actor.name) to do it in front of everyone.\""
            ]
        }
        let line = templates[stableIndex(for: "\(actor.id)-\(thread.id)-\(seed)-overheard", count: templates.count)]
        return "\(attribution): \(line)"
    }

    private static func stableIndex(for key: String, count: Int) -> Int {
        guard count > 0 else { return 0 }
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in key.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return Int(hash % UInt64(count))
    }

    private static func pick<T>(_ values: [T], offset: Int) -> T? {
        guard !values.isEmpty else { return nil }
        return values[offset % values.count]
    }

    private static func hiddenEffect(
        actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind
    ) -> String {
        switch actionKind {
        case .takeAction:
            return "\(actor.name) gained a memory trace; \(thread.title) stayed active."
        case .investBelief:
            return "\(thread.title) gained narrative weight from \(actor.name)."
        case .attackBelief:
            return "\(thread.title) lost brittle certainty but gained tension."
        }
    }

    private static func participantKind(for actor: NarrativeWorldEntity) -> BeliefCombatParticipantKind {
        switch actor.kind {
        case .character:
            return .npc
        case .talisman:
            return .talisman
        case .location, .classRoom, .realWorldAnchor:
            return .location
        case .object:
            return .object
        case .motif, .thread:
            return .entity
        }
    }

    private static func beliefCombat(
        actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind,
        seed: Int
    ) -> BeliefCombatResult? {
        guard actionKind == .attackBelief else { return nil }
        let spend = actor.tags.contains("nothing") ? 0 : max(1, min(4, actor.belief / 18 + 1))
        let roll = stableIndex(for: "\(actor.id)-\(thread.id)-\(seed)-belief-combat-roll", count: 100) + 1
        let difficulty: BeliefCombatDifficulty
        if actor.tags.contains("nothing") || thread.phase == .climax {
            difficulty = .dramatic
        } else {
            difficulty = BeliefCombatResolver.difficulty(forTargetBelief: thread.belief)
        }
        return BeliefCombatResolver.resolve(
            attackerName: actor.name,
            attackerKind: participantKind(for: actor),
            attackerBelief: actor.belief,
            targetName: thread.title,
            targetKind: .thread,
            targetBelief: thread.belief,
            spend: spend,
            difficulty: difficulty,
            roll: roll
        )
    }

    private static func consequenceLines(
        actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind,
        beliefCombat: BeliefCombatResult?,
        talismanMove: ChapterTalismanBeliefMove?
    ) -> [String] {
        let talismanLines: [String] = talismanMove.map { move in
            let delta = move.ledgerDelta
            if delta == 0 {
                return "\(move.summaryLine) No talisman Belief changed."
            }
            return "\(move.summaryLine) \(move.targetTalismanName) \(delta > 0 ? "gained" : "lost") \(abs(delta)) Belief."
        }.map { [$0] } ?? []

        switch actionKind {
        case .takeAction:
            return [
                "\(actor.name) left a fresh memory in the margins.",
                "\(thread.title) remains available for a future Story Page."
            ] + talismanLines
        case .investBelief:
            return [
                "\(actor.name) spent one quiet Belief.",
                "\(thread.title) grew warmer by one line."
            ] + talismanLines
        case .attackBelief:
            if let beliefCombat {
                var lines = [
                    "\(actor.name) spent \(beliefCombat.actualSpend) Belief against \(thread.title).",
                    beliefCombat.summaryLine
                ]
                if beliefCombat.dealt > 0 {
                    lines.append("\(thread.title) dimmed from Glow \(beliefCombat.targetBeliefBefore) to \(beliefCombat.targetBeliefAfter).")
                } else if beliefCombat.backlash > 0 {
                    lines.append("\(actor.name)'s own Glow fell from \(beliefCombat.attackerBeliefBefore) to \(beliefCombat.attackerBeliefAfter).")
                } else {
                    lines.append("\(thread.title) held its Glow at \(beliefCombat.targetBeliefBefore).")
                }
                return lines + talismanLines
            }
            return [
                "\(actor.name) pressed on a weak place in the thread.",
                "\(thread.title) gained tension, not certainty."
            ] + talismanLines
        }
    }

    private static var fallbackActor: NarrativeWorldEntity {
        NarrativePackRegistry.entities.first { $0.id == "the-book" } ?? NarrativeWorldEntity(
            id: "the-book",
            packID: NarrativePackRegistry.corePackID,
            name: "The Book",
            kind: .object,
            belief: 30,
            narrativeWeight: 30,
            chapter: nil,
            unwrittenInterest: "Whether ordinary life can become literature without lying.",
            traits: ["attentive"],
            quirks: ["keeps receipts in the margins"],
            faults: ["too fond of symbols"],
            beliefs: ["attention makes things real"],
            goals: ["keep the reader's day from vanishing"],
            tags: ["book", "belief", "ordinary"]
        )
    }

    private static var fallbackThread: NarrativeStoryThread {
        NarrativePackRegistry.threads.first { $0.id == "ordinary-magic" } ?? NarrativeStoryThread(
            id: "ordinary-magic",
            packID: NarrativePackRegistry.corePackID,
            title: "Ordinary Magic",
            phase: .returning,
            belief: 30,
            narrativeWeight: 30,
            summary: "Small true things keep asking to matter.",
            tags: ["ordinary", "wonder", "daily"]
        )
    }
}

enum BeliefLexicon {
    static func glowName(for score: Int) -> String {
        switch min(100, max(0, score)) {
        case ..<10:
            return "Glow Barely There"
        case 10..<20:
            return "Meager Glow"
        case 20..<30:
            return "Faint Glow"
        case 30..<40:
            return "Small Glow"
        case 40..<50:
            return "Warming Glow"
        case 50..<60:
            return "Steady Glow"
        case 60..<70:
            return "Clear Glow"
        case 70..<80:
            return "Bright Glow"
        case 80..<90:
            return "Radiant Glow"
        default:
            return "Glow Too Full"
        }
    }
}

enum FacultyEntryKind: String, Codable, CaseIterable, Identifiable {
    case fuel
    case innerWeather

    var id: String { rawValue }

    var facultyID: String {
        switch self {
        case .fuel:
            return "dr-vellum"
        case .innerWeather:
            return "dr-inkrest"
        }
    }

    var chartTitle: String {
        switch self {
        case .fuel:
            return "Dr. Vellum's Chart"
        case .innerWeather:
            return "Dr. Inkrest's Chart"
        }
    }
}

struct FacultyEntry: Codable, Identifiable, Equatable {
    var id: String
    var kind: FacultyEntryKind
    var facultyID: String
    var dayID: String
    var sourcePageID: String?
    var createdAt: Date
    var windowID: String
    var windowName: String
    var rawText: String
    var tags: [String]

    init(
        id: String = UUID().uuidString,
        kind: FacultyEntryKind,
        facultyID: String? = nil,
        dayID: String,
        sourcePageID: String? = nil,
        createdAt: Date = Date(),
        windowID: String,
        windowName: String,
        rawText: String,
        tags: [String] = []
    ) {
        self.id = id
        self.kind = kind
        self.facultyID = facultyID ?? kind.facultyID
        self.dayID = dayID
        self.sourcePageID = sourcePageID
        self.createdAt = createdAt
        self.windowID = windowID
        self.windowName = windowName
        self.rawText = rawText
        self.tags = tags
    }
}

enum SupportGuildSynthesisGenerator {
    static func surface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date = Date()) -> SurfacePage? {
        let source = BookPageSourceRegistry.source(for: .supportGuild)
        guard Self.isGuildTime(now) else { return nil }
        let slot = SurfaceCadence.slotID(for: now, hours: 8)
        let alreadyKept = day.pages.contains { $0.type == .supportGuild && $0.tags.contains("support-guild:\(slot)") }
        guard !alreadyKept else { return nil }

        let recentEntries = inputs.facultyEntries
            .filter { $0.dayID == day.id || $0.createdAt > Calendar.current.date(byAdding: .day, value: -3, to: now) ?? now }
            .sorted { $0.createdAt > $1.createdAt }
        guard recentEntries.count >= 2 || inputs.body?.metrics.isEmpty == false || context.distress.isActive else {
            return nil
        }

        let fuelEntries = recentEntries.filter { $0.kind == .fuel }
        let weatherEntries = recentEntries.filter { $0.kind == .innerWeather }
        let researchNotes = day.pages
            .filter { $0.type == .facultyResearch }
            .sorted { $0.createdAt < $1.createdAt }
        let metrics = inputs.body?.metrics ?? []
        let vellum = NarrativePackRegistry.entities.first { $0.id == "dr-vellum" }
        let inkrest = NarrativePackRegistry.entities.first { $0.id == "dr-inkrest" }
        let connection = connectionLine(fuelEntries: fuelEntries, weatherEntries: weatherEntries, metrics: metrics, distressActive: context.distress.isActive)
        let experiment = experimentLine(fuelEntries: fuelEntries, weatherEntries: weatherEntries, metrics: metrics, distressActive: context.distress.isActive)
        let safety = "This is not diagnosis or treatment. It is a low-shame pattern note for deciding what to observe next."
        let sections: [String: String] = [
            "vellum": [
                "Vellum reads: \(summaryList(for: fuelEntries, fallback: "no fuel notes yet"))",
                "HealthKit margin: \(metricSummary(metrics))",
                "Research note: \(researchSummary(for: "dr-vellum", pages: researchNotes))",
                "Research docket: \(vellum?.unwrittenInterest ?? "longevity, fuel, recovery, and humane experiments")"
            ].joined(separator: "\n"),
            "inkrest": [
                "Inkrest reads: \(summaryList(for: weatherEntries, fallback: "no inner-weather notes yet"))",
                "Narrative pressure: \(context.distress.isActive ? "the page asks for gentleness before interpretation" : "patterns can be held lightly")",
                "Research note: \(researchSummary(for: "dr-inkrest", pages: researchNotes))",
                "Research docket: \(inkrest?.unwrittenInterest ?? "consciousness, narrative psychology, and reauthoring")"
            ].joined(separator: "\n"),
            "connections": connection,
            "experiment": experiment,
            "safety": safety
        ]
        let body = [
            "Dr. Vellum and Dr. Inkrest compared the chart without making it a verdict.",
            "",
            "Connection: \(connection)",
            "",
            "Small experiment: \(experiment)",
            "",
            safety
        ].joined(separator: "\n")

        let timeFormatter = DateFormatter()
        timeFormatter.dateFormat = "h:mm a"
        let keptToday = day.capturedPages
            .sorted { $0.createdAt < $1.createdAt }
            .suffix(10)
            .map { page in
                let text = page.userInput.isEmpty ? page.promptText : page.userInput
                return "\(timeFormatter.string(from: page.createdAt)) — \(page.type.shortTitle): \(String(text.replacingOccurrences(of: "\n", with: " ").prefix(110)))"
            }
            .joined(separator: "\n")
        let fullMetrics = metrics.prefix(12).map(\.displayText).joined(separator: " | ")
        let moonPhase = MoonPhaseCalendar.phase(on: now)
        let skyLine = [
            inputs.weather?.phrase,
            inputs.enchantedWeather?.enchantified
        ].compactMap { $0 }.joined(separator: " · ")

        return SurfacePage(
            id: "\(source.id)-\(day.id)-\(slot)",
            type: .supportGuild,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .gentleTranslation,
            score: context.distress.isActive ? 94 : 78,
            reason: "The Support Guild has enough chart ink to compare patterns.",
            prompt: "The Support Guild has opened a joint page.",
            detail: "Vellum and Inkrest compare fuel, inner weather, body signals, and research dockets into one humane experiment.",
            payload: BookPagePayload(
                headline: "Support Guild Page",
                body: body,
                metadata: [
                    "source": source.id,
                    "slot": slot,
                    "vellumSection": sections["vellum"] ?? "",
                    "inkrestSection": sections["inkrest"] ?? "",
                    "bodyStatus": inputs.body.map { "\($0.status): \($0.phrase)" } ?? "",
                    "bodyMetrics": fullMetrics,
                    "outerWeather": skyLine,
                    "moonSeason": "\(moonPhase.name), \(AnchorRegistry.currentSeason(for: now))",
                    "keptToday": keptToday,
                    "connectionsSection": sections["connections"] ?? "",
                    "experimentSection": sections["experiment"] ?? "",
                    "safetySection": sections["safety"] ?? "",
                    "researchTopics": [
                        vellum?.unwrittenInterest ?? "longevity, fuel, recovery, supplements, movement",
                        inkrest?.unwrittenInterest ?? "consciousness, narrative psychology, brain studies"
                    ].joined(separator: "\n"),
                    "tags": "support-guild,support-guild:\(slot),dr-vellum,dr-inkrest,vellum-chart,therapy-chart,research,experiment"
                ]
            )
        )
    }

    static func isGuildTime(_ date: Date = Date(), calendar: Calendar = .current) -> Bool {
        let components = calendar.dateComponents([.hour, .minute], from: date)
        return ((components.hour ?? 0) * 60 + (components.minute ?? 0)) >= 19 * 60
    }

    private static func summaryList(for entries: [FacultyEntry], fallback: String) -> String {
        let snippets = entries.prefix(3).map { entry in
            let text = entry.rawText.replacingOccurrences(of: "\n", with: " ")
            return "\(entry.windowName): \(String(text.prefix(90)))"
        }
        return snippets.isEmpty ? fallback : snippets.joined(separator: " | ")
    }

    private static func metricSummary(_ metrics: [BodySourceSignal.Metric]) -> String {
        let wanted = ["Sleep", "Steps", "Active energy", "Heart rate", "Resting heart rate", "HRV", "Blood pressure systolic", "Blood glucose", "Medication"]
        let selected = wanted.compactMap { label in metrics.first { $0.label == label } }.prefix(6)
        guard !selected.isEmpty else { return "no additional HealthKit metrics available" }
        return selected.map(\.displayText).joined(separator: " | ")
    }

    private static func researchSummary(for facultyID: String, pages: [BookPage]) -> String {
        guard let page = pages.last(where: { $0.tags.contains("faculty:\(facultyID)") }) else {
            return "no saved research note yet"
        }
        return page.userInput
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .prefix(220)
            .description
    }

    private static func connectionLine(
        fuelEntries: [FacultyEntry],
        weatherEntries: [FacultyEntry],
        metrics: [BodySourceSignal.Metric],
        distressActive: Bool
    ) -> String {
        let fuelText = fuelEntries.map(\.rawText).joined(separator: " ").lowercased()
        let weatherText = weatherEntries.map(\.rawText).joined(separator: " ").lowercased()
        let sleep = metrics.first { $0.label == "Sleep" }.flatMap { Double($0.value) } ?? 0
        if distressActive || weatherText.contains("anx") || weatherText.contains("storm") || weatherText.contains("low") {
            return "Inner weather is asking to be treated as context before it is treated as a problem; Vellum should keep the next body experiment smaller than ambition wants."
        }
        if sleep > 0 && sleep < 6 {
            return "Short sleep changes the meaning of fuel, mood, and motivation. The Guild reads today through recovery first."
        }
        if fuelText.contains("coffee") && weatherText.contains("tired") {
            return "Caffeine and tiredness are sharing a margin; the useful question is timing, not virtue."
        }
        if !fuelEntries.isEmpty && !weatherEntries.isEmpty {
            return "Fuel notes and inner weather are now close enough on the page to compare timing, texture, and aftermath."
        }
        return "The chart has begun; the strongest current signal is that missing data should become a question, not a conclusion."
    }

    private static func experimentLine(
        fuelEntries: [FacultyEntry],
        weatherEntries: [FacultyEntry],
        metrics: [BodySourceSignal.Metric],
        distressActive: Bool
    ) -> String {
        let steps = metrics.first { $0.label == "Steps" }.flatMap { Double($0.value) } ?? 0
        let sleep = metrics.first { $0.label == "Sleep" }.flatMap { Double($0.value) } ?? 0
        if distressActive {
            return "For one bell window, log fuel and inner weather without fixing either. Add one grounding sentence before any plan."
        }
        if sleep > 0 && sleep < 6 {
            return "Run a recovery-first day: warm fuel, water, no heroic errands, and a one-line note about mood after the next meal."
        }
        if steps < 1_500 && !fuelEntries.isEmpty {
            return "After the next fuel note, try five gentle minutes of movement and log whether the inner weather changes by one word."
        }
        if weatherEntries.isEmpty {
            return "Pair the next Fuel Log with one Inner Weather word so Vellum and Inkrest can compare timing."
        }
        return "Choose one repeatable observation for today: what happened to energy and mood one hour after the most ordinary meal or drink?"
    }
}

enum CharacterLetterPageGenerator {
    static func draftCandidate(for day: BookDay, inputs: BookSourceInputs, now: Date = Date()) -> SurfacePage? {
        let source = BookPageSourceRegistry.source(for: .letter)
        guard let entity = selectedEntity(for: day, inputs: inputs, now: now) else { return nil }
        return draftCandidate(for: entity, source: source, day: day, inputs: inputs, now: now)
    }

    static func draftCandidate(
        for entity: NarrativeWorldEntity,
        source: BookPageSource,
        day: BookDay,
        inputs: BookSourceInputs,
        now: Date
    ) -> SurfacePage {
        let slot = SurfaceCadence.slotID(for: now, hours: 12)
        let interest = entity.unwrittenInterest?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
            ?? entity.beliefs.first
            ?? entity.traits.first
            ?? "ordinary wonder"
        let homeContext = homeContextLine(inputs: inputs, day: day)
        let playerName = preferredPlayerName(inputs: inputs)
        let voice = voiceProfile(for: entity)
        let memoryPacket = memoryPacket(for: entity, day: day, inputs: inputs)
        let talismanMoves = ChapterTalismanBeliefMoves.moves(
            for: [entity],
            seed: stableIndex(for: "\(day.id)-\(slot)-\(entity.id)-letter-talisman", count: 10_000)
        )
        let talismanMoveLines = talismanMoves.map(\.promptLine).joined(separator: "\n")
        let talismanDeltaTokens = talismanMoves.compactMap(\.ledgerToken).joined(separator: ",")
        let query = researchQuery(for: interest, homeContext: homeContext)
        let occasion = letterOccasion(inputs: inputs)
        let body = """
        Sender: \(entity.name)
        Address the player as: \(playerName)
        Unwritten Interest: \(interest)
        Home Context: \(homeContext)
        Research Query: \(query)

        Letter occasion:
        \(occasion ?? "No special occasion. Write because the sender wanted to.")

        Writing Voice:
        \(voice.promptDescription)

        Memory and narrative packet:
        \(memoryPacket)

        Chapter talisman move:
        \(talismanMoveLines.isEmpty ? "No chapter talisman move is being made in this letter." : talismanMoveLines)

        Write a real letter to the player. If a letter occasion is given, it is the reason this letter exists - open from it and let it carry the letter, gently and without diagnosing. Use live web research if clippings are supplied. If no clippings are supplied, fall back to the model's own general knowledge without pretending it browsed.
        """
        return SurfacePage(
            id: "\(source.id)-\(day.id)-\(slot)-\(entity.id)",
            type: .letter,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .loreLetter,
            score: min(84, 54 + entity.belief / 4 + entity.narrativeWeight / 4),
            reason: "\(entity.name) has a researched letter gathering in the margins.",
            prompt: "A letter from \(entity.name)",
            detail: "A researched note about \(interest) and home.",
            payload: BookPagePayload(
                headline: "Letter from \(entity.name)",
                body: body,
                metadata: [
                    "source": source.id,
                    "senderID": entity.id,
                    "senderName": entity.name,
                    "playerName": playerName,
                    "unwrittenInterest": interest,
                    "homeContext": homeContext,
                    "letterOccasion": occasion ?? "",
                    "researchQuery": query,
                    "writingVoice": voice.promptDescription,
                    "chapterTalismanMoves": talismanMoveLines,
                    "chapterTalismanDeltas": talismanDeltaTokens,
                    "slotID": slot,
                    "placeholder": "A researched letter is being written through the Margin-Glass.",
                    "tags": "letter,letters,research,sender:\(entity.id),\(entity.tags.prefix(4).joined(separator: ","))"
                ]
            )
        )
    }

    static func preferredPlayerName(inputs: BookSourceInputs) -> String {
        let usableFacts = inputs.selfFacts.filter { $0.usePermission != .doNotUse }
        let preferred = usableFacts.first { $0.questionID == "onboarding-name" }?.answer
            ?? usableFacts.first { $0.questionID == "called" }?.answer
            ?? usableFacts.first { $0.tags.contains("name") || $0.tags.contains("identity") }?.answer
        let trimmed = preferred?.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed?.nonEmpty ?? "friend"
    }

    static func voiceProfile(for entity: NarrativeWorldEntity) -> WritingVoiceProfile {
        if let writingVoice = entity.writingVoice {
            return writingVoice
        }
        let traitLine = entity.traits.prefix(3).joined(separator: ", ")
        let quirkLine = entity.quirks.prefix(2).joined(separator: "; ")
        return WritingVoiceProfile(
            register: entity.kind == .character ? "personal, direct, and specific" : "observant and quietly animate",
            rhythm: "varied sentence lengths; one intimate turn near the end",
            diction: Array((entity.traits + entity.tags).prefix(5)),
            habits: [
                traitLine.isEmpty ? "write from what the character notices first" : "let these traits guide the hand: \(traitLine)",
                quirkLine.isEmpty ? "include one small concrete observation" : "one habit may surface: \(quirkLine)"
            ],
            avoid: [
                "generic assistant voice",
                "fake citations",
                "claiming the player did things not present in memory"
            ]
        )
    }

    private static func selectedEntity(for day: BookDay, inputs: BookSourceInputs, now: Date) -> NarrativeWorldEntity? {
        let recentSenders = Set(day.pages.filter { $0.type == .letter }.compactMap { $0.tags.first(where: { $0.hasPrefix("sender:") })?.dropFirst("sender:".count) }.map(String.init))
        let candidates = (NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity))
            .filter { $0.kind == .character }
            .filter { !($0.unwrittenInterest ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            .filter { !recentSenders.contains($0.id) }
        guard !candidates.isEmpty else { return nil }
        let slot = SurfaceCadence.slotID(for: now, hours: 12)
        return candidates.max { left, right in
            let leftScore = entityScore(left, day: day, inputs: inputs, slot: slot)
            let rightScore = entityScore(right, day: day, inputs: inputs, slot: slot)
            if leftScore == rightScore { return left.name > right.name }
            return leftScore < rightScore
        }
    }

    private static func entityScore(_ entity: NarrativeWorldEntity, day: BookDay, inputs: BookSourceInputs, slot: String) -> Int {
        let recentText = day.pages.suffix(8).map { "\($0.promptText) \($0.userInput) \($0.tags.joined(separator: " "))" }.joined(separator: " ").lowercased()
        let memoryHit = recentText.contains(entity.id.lowercased()) || recentText.contains(entity.name.lowercased()) ? 18 : 0
        let narrativeHit = inputs.narrative?.weightedEntityIDs.contains(entity.id) == true ? 14 : 0
        let jitter = stableIndex(for: "\(slot)-\(entity.id)", count: 12)
        return entity.belief + entity.narrativeWeight + memoryHit + narrativeHit + jitter
    }

    private static func homeContextLine(inputs: BookSourceInputs, day: BookDay) -> String {
        let facts = inputs.selfFacts
            .filter { $0.usePermission != .doNotUse && ($0.tags.contains("home") || $0.tags.contains("place")) }
            .prefix(3)
            .map(\.answer)
        if !facts.isEmpty {
            return facts.joined(separator: " | ")
        }
        if let weather = inputs.weather?.phrase.nonEmpty {
            return "the player's present weather: \(weather)"
        }
        let pageHint = day.pages.reversed().first { $0.tags.contains("home") || $0.type == .location }?.userInput.nonEmpty
        return pageHint ?? "the player's actual home region, inferred only from supplied context"
    }

    private static func researchQuery(for interest: String, homeContext: String) -> String {
        "\(interest) \(homeContext) local history ecology culture"
            .split(separator: " ")
            .prefix(18)
            .joined(separator: " ")
    }

    private static func memoryPacket(for entity: NarrativeWorldEntity, day: BookDay, inputs: BookSourceInputs) -> String {
        let pages = day.pages.suffix(6).map { "- \($0.promptText): \($0.userInput.bookPreviewSentenceLimit(1))" }.joined(separator: "\n")
        let memories = inputs.narrative?.entityMemories
            .filter { $0.entityID == entity.id }
            .prefix(4)
            .map { "- \($0.summary)" }
            .joined(separator: "\n") ?? ""
        let continuity = continuityPacket(for: entity, inputs: inputs)
        return """
        Recent pages:
        \(pages.isEmpty ? "No kept pages yet today." : pages)

        Entity memories:
        \(memories.isEmpty ? "No explicit memory packet for this sender." : memories)

        What the Book has begun to notice:
        \(continuity.isEmpty ? "No stable literary pattern has been offered to this sender." : continuity)
        """
    }

    private static func continuityPacket(for entity: NarrativeWorldEntity, inputs: BookSourceInputs) -> String {
        let related = inputs.continuity.strongestSignals.filter { signal in
            signal.relatedEntityIDs.contains(entity.id)
                || signal.tags.contains(entity.id)
                || entity.tags.contains(where: { signal.tags.contains($0) })
        }
        let selected = related.isEmpty ? inputs.continuity.strongestSignals.prefix(3).map(\.self) : Array(related.prefix(4))
        var lines = selected.map { "- \($0.line)" }
        for constellation in ConstellationKeeper.namedConstellations(inputs.constellations).prefix(3) {
            lines.append("- The Book has named a constellation it keeps about the reader: \(constellation.displayName). \(constellation.latestLine) Characters may refer to it by name, as something the Book keeps.")
        }
        for wager in inputs.wagers.filter(\.isSealed).prefix(2) {
            lines.append("- The Book has a sealed wager pending: \(wager.prediction) Characters may know the Book wagers but not the outcome.")
        }
        if let theme = inputs.themes.max(by: { $0.monthKey < $1.monthKey }) {
            lines.append("- \(theme.promptLine) Characters may allude to the theme without naming the app or sounding clinical.")
        }
        return lines.joined(separator: "\n")
    }

    /// When something the reader used to write about has gone properly quiet,
    /// that absence becomes the reason a letter exists - the sender writes
    /// because of it, not merely mentioning it.
    private static func letterOccasion(inputs: BookSourceInputs) -> String? {
        guard let absence = inputs.continuity.strongestSignals.first(where: { $0.kind == .absence && $0.strength >= 60 }) else {
            return nil
        }
        return "\(absence.line) The sender writes because of this quiet: ask after \(absence.subjectName) the way a friend asks after someone who stopped coming to the cafe - warmly, without alarm, leaving room for the answer to be ordinary. Do not demand a reply; let the margin hold the question."
    }

    private static func stableIndex(for key: String, count: Int) -> Int {
        guard count > 0 else { return 0 }
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in key.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return Int(hash % UInt64(count))
    }
}

enum CompassRunStep: String, CaseIterable, Identifiable {
    case notice
    case embark
    case sense
    case write
    case rest

    var id: String { rawValue }

    var title: String {
        switch self {
        case .notice:
            return "Notice"
        case .embark:
            return "Embark"
        case .sense:
            return "Sense"
        case .write:
            return "Write"
        case .rest:
            return "Rest"
        }
    }

    var compassPoint: String {
        switch self {
        case .notice:
            return "North"
        case .embark:
            return "East"
        case .sense:
            return "South"
        case .write:
            return "West"
        case .rest:
            return "Center"
        }
    }

    var prompt: String {
        switch self {
        case .notice:
            return "I wonder..."
        case .embark:
            return "Plan so badly it cannot fail."
        case .sense:
            return "Give your senses a tiny game."
        case .write:
            return "Keep one sentence from time."
        case .rest:
            return "Let the center hold."
        }
    }

    var standaloneDetail: String {
        switch self {
        case .notice:
            return "Choose a spark: a question, object, place, oddity, color, sound, or tiny curiosity."
        case .embark:
            return "Name the 3 D's: Destination, Delight, and Definition."
        case .sense:
            return "Pick a playful mission: find, count, compare, collect, touch, listen, taste, or photograph."
        case .write:
            return "Save the single best sensory detail. Specific is terrific."
        case .rest:
            return "Set the phone down for one quiet minute. Rest is the pin, not the prize."
        }
    }

    var capturePlaceholder: String {
        switch self {
        case .notice:
            return "Keep the exact Spark that starts the run."
        case .embark:
            return "Write when you have crossed the threshold."
        case .sense:
            return "Write what the mission made you notice, or keep a photo."
        case .write:
            return "Write your One-Sentence Souvenir here."
        case .rest:
            return "After one quiet minute, the needle feels..."
        }
    }

    var scoreBoost: Int {
        switch self {
        case .notice:
            return 8
        case .embark:
            return 11
        case .sense:
            return 12
        case .write:
            return 14
        case .rest:
            return 9
        }
    }

    var missionBody: String {
        switch self {
        case .notice:
            return "North sets the bearing. Start with the Spark and let it become the goal of the run."
        case .embark:
            return "East crosses the threshold with the 3 D's: Destination, Delight, Definition. Specificity lowers the activation energy."
        case .sense:
            return "South breaks the museum gaze. Use a playful sensory mission so the phone becomes a field kit, then the eyes come up."
        case .write:
            return "West is the save button. One specific sentence is enough to keep the memory from dissolving."
        case .rest:
            return "The Center keeps the compass from becoming homework. Sixty seconds of no input is a valid completion."
        }
    }
}

struct CompassRunProgress: Equatable {
    var completedSteps: Set<CompassRunStep>
    var latestRunID: String?
    var latestSpark: String?

    var nextStep: CompassRunStep {
        CompassRunStep.allCases.first { !completedSteps.contains($0) } ?? .notice
    }

    var isComplete: Bool {
        CompassRunStep.allCases.allSatisfy { completedSteps.contains($0) }
    }

    static func progress(for day: BookDay) -> CompassRunProgress {
        let compassPages = day.capturedPages.filter { page in
            page.tags.contains("wonder-compass-run") || page.tags.contains("wonder-compass")
        }
        let completed = Set(compassPages.compactMap { page -> CompassRunStep? in
            for tag in page.tags {
                if tag.hasPrefix("compass-step:") {
                    return CompassRunStep(rawValue: String(tag.dropFirst("compass-step:".count)))
                }
            }
            return nil
        })
        let runID = compassPages
            .flatMap(\.tags)
            .first { $0.hasPrefix("compass-run:") }
            .map { String($0.dropFirst("compass-run:".count)) }
        let spark = compassPages
            .last { $0.tags.contains("compass-step:notice") }?
            .userInput
            .split(separator: "\n")
            .first
            .map(String.init)

        return CompassRunProgress(
            completedSteps: completed,
            latestRunID: runID,
            latestSpark: spark
        )
    }
}

struct WonderCompassRunSeed: Equatable {
    var id: String
    var mode: WonderConciergeMode
    var timeBox: String
    var budget: String
    var place: String
    var energy: String
    var companions: String
    var considerations: String
    var circumstance: String
    var spark: String
    var destination: String
    var delight: String
    var definition: String
    var mission: String
    var souvenirPrompt: String
    var restPrompt: String
    var tags: [String]

    var fullPrompt: String {
        [
            "Mode: \(mode.title)",
            "Time: \(timeBox)",
            "Budget: \(budget)",
            "Place: \(place)",
            "Energy: \(energy)",
            "With: \(companions)",
            "Considerations: \(considerations)",
            "Circumstance: \(circumstance)",
            "North: \(spark)",
            "East: Destination: \(destination); Delight: \(delight); Definition: \(definition)",
            "South: \(mission)",
            "West: \(souvenirPrompt)",
            "Center: \(restPrompt)"
        ].joined(separator: "\n")
    }

    func body(for step: CompassRunStep) -> String {
        switch step {
        case .notice:
            return """
            Ask this Spark out loud or in your head:

            \(spark)

            Keep the page when you are ready to let this question become the goal of the run.
            """
        case .embark:
            return """
            Destination: \(destination)

            Delight: \(delight)

            Definition: \(definition)

            Cross one real threshold. The run begins when your body moves into the recipe.
            """
        case .sense:
            return """
            Playful Mission:

            \(mission)

            Let your senses do the work. Keep a sentence or photo when something specific appears.
            """
        case .write:
            return """
            One-Sentence Souvenir:

            \(souvenirPrompt)

            One sentence is enough. Make it sensory enough that tomorrow can find it again.
            """
        case .rest:
            return """
            \(restPrompt)

            Rest is the center of the Compass. Keep this page after the quiet minute, and the completed run adds 6 Belief.
            """
        }
    }
}

struct PlayfulMission: Identifiable, Equatable {
    var id: String
    var title: String
    var prompt: String
    var proofPrompt: String
    var tags: [String]
    var allowsPhoto: Bool = true
}

enum PlayfulMissionRegistry {
    static func mission(for day: BookDay, inputs: BookSourceInputs, now: Date = Date()) -> PlayfulMission {
        let missions = rankedMissions(for: day, inputs: inputs, now: now)
        let slot = SurfaceCadence.slotID(for: now, hours: 2)
        let seed = abs("\(day.id)-\(slot)-playful-mission".stableHash)
        return missions[seed % missions.count]
    }

    private static func rankedMissions(for day: BookDay, inputs: BookSourceInputs, now: Date) -> [PlayfulMission] {
        let text = [
            inputs.weather?.phrase,
            inputs.body?.status,
            day.capturedPages.suffix(6).map { "\($0.promptText) \($0.userInput) \($0.tags.joined(separator: " "))" }.joined(separator: " ")
        ]
        .compactMap(\.self)
        .joined(separator: " ")
        .lowercased()

        let preferredTags: Set<String>
        if text.contains("rain") || text.contains("storm") || text.contains("fog") {
            preferredTags = ["weather", "sound", "scent", "inside"]
        } else if text.contains("low") || text.contains("tired") || text.contains("rest") {
            preferredTags = ["low-energy", "touch", "inside"]
        } else if text.contains("work") || text.contains("errand") || text.contains("store") {
            preferredTags = ["public", "visual", "errand"]
        } else {
            preferredTags = ["touch", "visual", "scent", "sound"]
        }

        return missions.sorted { left, right in
            let leftScore = Set(left.tags).intersection(preferredTags).count
            let rightScore = Set(right.tags).intersection(preferredTags).count
            if leftScore == rightScore {
                return left.id < right.id
            }
            return leftScore > rightScore
        }
    }

    static let missions: [PlayfulMission] = coreMissions + attentionMissions

    static let coreMissions: [PlayfulMission] = [
        mission("oldest-smell", "The Oldest Thing", "Find the oldest thing near you and smell it. What does age smell like here?", "Complete this: The oldest thing near me smelled like...", ["scent", "touch", "inside", "low-energy"]),
        mission("coldest-touch", "The Coldest Touch", "Find the coldest thing you are allowed to touch. Hold it for five seconds.", "Write one sentence about where the cold seemed to come from.", ["touch", "temperature", "inside", "low-energy"]),
        mission("quietest-sound", "The Quietest Sound", "Stand still and hunt the quietest sound in the room. Not the loudest. The shyest.", "Complete this: Under everything else, I heard...", ["sound", "inside", "low-energy"]),
        mission("three-rough", "Texture Thief", "Find three rough textures within ten steps. Rank them from friendly to suspicious.", "Write one sentence naming the strangest texture.", ["touch", "inside", "public"]),
        mission("blue-count", "Blue Census", "Count every blue thing you can see without moving your feet.", "Write the blue thing that surprised you most.", ["visual", "color", "inside", "public"]),
        mission("tiny-door", "Tiny Door", "Find the smallest opening nearby: a crack, keyhole, drawer gap, vent, bottle mouth, or shadow under a door.", "Write what might live on the other side.", ["visual", "imagination", "inside"]),
        mission("weather-scent", "Weather Has A Smell", "Step near a door or window and compare the air on both sides. Which side has more weather in it?", "Write one sentence about the smell or weight of the air.", ["weather", "scent", "inside"]),
        mission("object-portrait", "Object Portrait", "Choose one ordinary object and photograph it like it is the main character.", "Write its first line of dialogue.", ["photo", "visual", "character", "inside"]),
        mission("five-shadows", "Shadow Hunt", "Find five shadows. Pick the one that looks least like the thing casting it.", "Write what the shadow is pretending to be.", ["visual", "photo", "inside", "public"]),
        mission("softest-edge", "The Softest Edge", "Find the softest edge nearby. A sleeve, paper, light, bread crust, blanket, voice, or dust counts.", "Write one sentence about what made it soft.", ["touch", "visual", "low-energy"]),
        mission("smell-map", "Smell Map", "Move through three nearby spots and notice how the smell changes. Make a tiny map in your head.", "Write the border where the smell changed.", ["scent", "movement", "inside"]),
        mission("tiny-kindness", "Evidence Of Kindness", "Find one tiny sign that someone made life easier for someone else.", "Write the evidence, no moral required.", ["visual", "public", "errand"]),
        mission("weirdest-label", "The Weirdest Label", "Find the strangest label, warning, sticker, sign, or package text nearby.", "Write what makes it strange.", ["visual", "public", "errand"]),
        mission("sound-layer", "Sound Layer", "Listen for three layers: machine, body, world. Name one sound in each layer.", "Write the layer that felt most alive.", ["sound", "inside", "public"]),
        mission("weight-guess", "Weight Oracle", "Pick up a safe object. Guess its exact weight, then decide if your hand agrees.", "Write whether it was heavier or lighter than its face suggested.", ["touch", "weight", "inside"]),
        mission("one-inch-kingdom", "One-Inch Kingdom", "Look closely at one square inch of something: fabric, bark, carpet, table, wall, sidewalk.", "Write what lives in that tiny kingdom.", ["visual", "touch", "photo", "low-energy"]),
        mission("borrowed-color", "Borrowed Color", "Find an object borrowing color from something else: reflected light, stained glass, screen glow, sunset, shade.", "Write who lent the color.", ["visual", "color", "photo"]),
        mission("old-date", "Date Hunter", "Find the oldest visible date nearby: on a coin, receipt, book, sign, package, building, or file.", "Write what that date has been waiting through.", ["visual", "public", "history"]),
        mission("chair-held", "The Chair Holds", "Sit down and let the chair do all the work for sixty seconds. Notice where it pushes back.", "Complete this: The chair held me by...", ["touch", "rest", "low-energy", "inside"], allowsPhoto: false),
        mission("brightest-small", "Small Bright Thing", "Find the brightest small thing nearby. Not the biggest bright thing. The small one.", "Write why it caught the light.", ["visual", "low-energy", "inside", "public"])
    ]

    static let attentionMissions: [PlayfulMission] = [
        mission("body-heartbeat-location", "The Body Reports In", "Stand completely still until you can feel your heartbeat somewhere other than your chest. Report the location.", "Write the place where the heartbeat answered.", ["body", "touch", "low-energy", "inside"], allowsPhoto: false),
        mission("body-quiet-steps", "Quiet Step Audit", "Walk ten steps as quietly as you possibly can. What gave you away?", "Write the sound or movement that betrayed you.", ["body", "sound", "movement", "inside"], allowsPhoto: false),
        mission("body-warmer-hand", "Hand Weather", "Find out which of your hands is warmer right now. Form a theory about why.", "Write which hand was warmer and your best theory.", ["body", "touch", "temperature", "low-energy"], allowsPhoto: false),
        mission("body-unclench-report", "The Muscle Confesses", "Unclench everything. Report which muscle was holding on and refused to admit it.", "Name the muscle that was still holding on.", ["body", "touch", "rest", "low-energy"], allowsPhoto: false),
        mission("body-tongue-watch", "Tongue Watch", "Notice what your tongue is doing right now. It was doing something.", "Write the tongue report in one exact phrase.", ["body", "taste", "low-energy"], allowsPhoto: false),
        mission("body-wall-palm", "Building Report", "Press your palm flat against the nearest wall for ten seconds. Decide what the building is doing today.", "Write what the building is doing today.", ["body", "touch", "inside", "place"], allowsPhoto: false),
        mission("body-chair-border", "Chair Border", "Find the exact place where your body ends and the chair begins. It is blurrier than you would think.", "Write one sentence about the blurriest border.", ["body", "touch", "rest", "inside"], allowsPhoto: false),
        mission("body-purposeful-yawn", "Yawn Route", "Yawn on purpose. Track where it travels: jaw, ears, eyes, spine. File a route map.", "Write the route the yawn took.", ["body", "rest", "low-energy"], allowsPhoto: false),
        mission("body-suspicious-breath", "Suspicious Breath", "Take one breath so slow it feels suspicious. What did you smell at the very bottom of it?", "Write the bottom-of-the-breath smell.", ["body", "scent", "low-energy"], allowsPhoto: false),
        mission("body-ankle-save", "Ankle Rescue", "Stand on one foot while you wait for something today. Report what your ankle did to save you.", "Write what the ankle did.", ["body", "balance", "movement"], allowsPhoto: false),
        mission("body-engine-count", "The Engine", "Find your pulse with two fingers. Count to ten beats. That is the engine. It never gets thanked.", "Write where you found the engine.", ["body", "touch", "low-energy"], allowsPhoto: false),
        mission("sound-newcomer", "Name The Newcomer", "Count the sounds you can hear right now. Then wait, perfectly still, for the next one to arrive. Name the newcomer.", "Write the newest sound by name.", ["sound", "inside", "low-energy"], allowsPhoto: false),
        mission("sound-lowest-room", "Lowest Sound", "Find the lowest sound in the room. It has probably been running this whole time.", "Write the lowest sound and where it might live.", ["sound", "inside", "low-energy"], allowsPhoto: false),
        mission("sound-farthest-away", "Farthest Sound", "Listen for the farthest-away sound you can detect. Estimate the distance in honest units.", "Write the sound and its honest distance.", ["sound", "inside", "outside"], allowsPhoto: false),
        mission("sound-three-objects", "Best Voice", "Tap three safe objects within reach. Which one has the best voice?", "Write which object had the best voice.", ["sound", "touch", "inside"], allowsPhoto: false),
        mission("sound-appliance-duet", "Appliance Duet", "Hum one low note and hold it. Somewhere, an appliance is humming back. Find your duet partner.", "Write the duet partner.", ["sound", "inside", "low-energy"], allowsPhoto: false),
        mission("sound-daily-unmentioned", "Unmentioned Sound", "Identify one sound you hear every single day but have never once mentioned to anyone. Mention it now.", "Write the daily sound.", ["sound", "inside", "low-energy"], allowsPhoto: false),
        mission("sound-ear-cups", "Borrowed Ears", "Cup your hands behind your ears for ten seconds. Report what got louder.", "Write what changed when your ears borrowed walls.", ["sound", "body", "inside"], allowsPhoto: false),
        mission("sound-room-pulse", "Room Pulse", "Find the room's pulse: something that ticks, blinks, drips, or hums in rhythm. Take its tempo.", "Write the pulse and its tempo.", ["sound", "rhythm", "inside"], allowsPhoto: false),
        mission("object-oldest-story", "Oldest Witness", "Find the oldest object in the room and ask what it has seen. Record its best story in one line.", "Write the oldest object's best story.", ["object", "history", "inside"]),
        mission("object-no-credit", "No-Credit Object", "Pick the object nearest you that gets no credit. Thank it specifically for the exact job it does.", "Write the object and the job it does.", ["object", "visual", "inside", "low-energy"]),
        mission("object-tired", "Object Rest", "Find one object that is tired. What would rest look like for it?", "Write what rest would look like for that object.", ["object", "visual", "imagination", "inside"]),
        mission("object-face", "Object Face", "Choose any object and find its face. Most of them have one. Describe the expression.", "Write the object's expression.", ["object", "visual", "imagination", "inside"]),
        mission("object-waiting", "Waiting Object", "Locate an object that is waiting. For what?", "Write what the object is waiting for.", ["object", "visual", "inside"]),
        mission("object-most-loyal", "Most Loyal", "Find the most loyal object you own: longest service, still working. Note its years.", "Write the object and its years of service.", ["object", "history", "inside"]),
        mission("object-repair", "Worth Saving", "Find a repair: tape, glue, a stitch, a weld. Someone decided this thing was worth saving. Guess why.", "Write the repair and the reason it survived.", ["object", "visual", "history", "inside"]),
        mission("object-traveled-farther", "Farther Traveled", "Find something in this room that has traveled farther than you ever have. Name its homeland.", "Write the object and its homeland.", ["object", "history", "inside"]),
        mission("object-in-charge", "Room Politics", "Decide which object in this room is actually in charge. Then decide which one merely thinks it is.", "Write the ruler and the pretender.", ["object", "imagination", "inside"]),
        mission("object-drawer-greeting", "Drawer Greeting", "Open a drawer you have not opened in a month. Greet one thing inside it by name.", "Write the thing's name.", ["object", "inside", "low-energy"]),
        mission("object-pocket-story", "Pocket Story", "Find one thing in your pocket or bag with a story you have never told anyone. Tell the Book the short version.", "Write the pocket thing and the short version.", ["object", "memory", "inside", "public"]),
        mission("object-remembered-color", "Remembered Color", "Find something that is a different color than you remembered it being. Record both colors: the remembered and the real.", "Write the remembered color and the real one.", ["object", "visual", "color"]),
        mission("nature-small-commute", "Tiny Commute", "Find one living thing smaller than your thumbnail. Watch its commute for thirty seconds. Report its errand.", "Write the living thing and its errand.", ["nature", "visual", "outside", "movement"]),
        mission("nature-plant-reaching", "Plant Wants", "Find the nearest plant and check what it is reaching toward. Plants always want something.", "Write what the plant wants.", ["nature", "visual", "inside", "outside"]),
        mission("nature-bird-business", "Bird Business", "Spot a bird and track it until it lands or vanishes. What business was it on?", "Write the bird's business.", ["nature", "visual", "outside", "movement"]),
        mission("nature-unseen-animal", "Unseen Suspect", "Find evidence of an animal you cannot currently see: tracks, sounds, leavings, damage. Name your suspect.", "Write the evidence and the suspect.", ["nature", "visual", "outside", "public"]),
        mission("nature-weed-winning", "Weed Winning", "Find a weed winning, growing somewhere it was never invited. Salute it. Note the territory claimed.", "Write the territory the weed claimed.", ["nature", "visual", "outside", "public"]),
        mission("nature-tree-scar", "Tree Scar", "Locate the nearest tree and find its oldest scar. Estimate the year of the wound.", "Write the scar and your estimated year.", ["nature", "visual", "history", "outside"]),
        mission("nature-moss-project", "Moss Project", "Find moss or lichen. It has been working on that exact spot longer than you have been alive. Acknowledge the project.", "Write the project site.", ["nature", "visual", "outside", "low-energy"]),
        mission("nature-compressed-forest", "Compressed Forest", "Find one seed anywhere: in food, in the air, on the ground. You are holding a compressed forest. Note where it was headed.", "Write the seed and its destination.", ["nature", "visual", "food", "outside"]),
        mission("sky-plain-forecast", "Sky Desk", "Step outside, or to a window. What is the sky deciding right now? File the forecast in plain words.", "Write the sky's plain-word forecast.", ["sky", "weather", "visual", "inside", "outside"]),
        mission("sky-find-wind", "Find The Wind", "Find the wind, not by feeling it, but by seeing it. What is it moving?", "Write what the wind moved.", ["sky", "weather", "visual", "movement", "outside"]),
        mission("sky-cloud-fleet", "Cloud Fleet", "Name today's clouds like ships in a harbor. Where is the fleet headed?", "Write one ship-name and where the fleet is headed.", ["sky", "weather", "visual", "imagination"]),
        mission("sky-real-color", "Real Sky Color", "Catch the exact color of the sky directly overhead. Not blue, not grey: the real one. Mix it in words.", "Write the true color in your own words.", ["sky", "weather", "visual", "color"]),
        mission("sky-rain-stage", "Rain Journey", "Find where the rain goes after it lands. Follow it one stage of its journey.", "Write the rain's next stage.", ["sky", "weather", "water", "outside"]),
        mission("sky-watchkeeper", "Watchkeeper Sighting", "Find the moon in daytime, or the first star at night. Log the sighting like a watchkeeper.", "Write the sighting log.", ["sky", "night", "visual", "outside"]),
        mission("sky-cloud-before-after", "Cloud Before After", "Watch one cloud until it changes shape. Record the before and after.", "Write the cloud before and after.", ["sky", "weather", "visual", "outside"]),
        mission("light-route", "Light Route", "Find where the light enters this room, and trace where it finally dies. Map the route.", "Write the route the light took.", ["light", "visual", "inside"]),
        mission("light-shadow-performer", "Shadow Performer", "Locate one shadow doing something interesting. Shadows are usually understated performers.", "Write what the shadow was doing.", ["light", "shadow", "visual", "inside", "photo"]),
        mission("light-reflection-secret", "Unknowing Reflection", "Find a reflection of something that does not know it is being reflected.", "Write what was reflected.", ["light", "visual", "inside", "photo"]),
        mission("light-non-screen-bright", "Not A Screen", "Find the brightest thing in the room that is not a screen.", "Write the brightest non-screen thing.", ["light", "visual", "inside", "low-energy"]),
        mission("light-sun-delivery", "Sun Delivery", "Find a patch of sunlight and put your hand in it. Report the delivery; it left the sun eight minutes ago.", "Write what the delivery felt like.", ["light", "touch", "inside", "outside"], allowsPhoto: false),
        mission("light-room-rearrange", "Dark Rearrangement", "Turn off one light you would normally leave on. Watch the room rearrange itself. What stepped forward in the dark?", "Write what stepped forward.", ["light", "night", "inside", "low-energy"]),
        mission("threshold-doorway-between", "Doorway Between", "Stand in a doorway for ten full seconds. Doorways are thresholds. Decide what you are between.", "Write what the doorway held you between.", ["threshold", "place", "inside", "low-energy"], allowsPhoto: false),
        mission("threshold-temperature-border", "Temperature Border", "Find the spot in your home where the temperature changes. That is a border. Borders have guards; identify yours.", "Write the border and its guard.", ["threshold", "temperature", "inside", "place"]),
        mission("threshold-quiet-corner", "Corner View", "Find the quietest corner of the room and stand in it. Describe the room from its point of view.", "Write the corner's view.", ["threshold", "sound", "inside", "low-energy"], allowsPhoto: false),
        mission("threshold-unstood-spot", "New Footprint", "Stand somewhere in your own home you have never stood before. There is at least one spot. Claim it.", "Write the claimed spot.", ["threshold", "place", "inside", "low-energy"]),
        mission("threshold-previous-message", "Previous Message", "Find evidence of whoever was in this space before you: a nail hole, a paint line, a scuff, a worn patch. Read the message they left.", "Write the message you read.", ["threshold", "history", "inside", "visual"]),
        mission("threshold-mouse-door", "Mouse-Sized Door", "Find the room's secret door: the place a mouse-sized visitor would enter and exit. Note it on the map.", "Write where the secret door is.", ["threshold", "visual", "inside", "imagination"]),
        mission("threshold-wall-perimeter", "Wall Report", "Walk the perimeter of one room slowly, trailing a hand along the wall. Report the one thing the wall told you.", "Write what the wall told you.", ["threshold", "touch", "inside", "movement"], allowsPhoto: false),
        mission("motion-long-way", "The Long Way", "Take the long way to wherever you are going next. Report what the shortcut was hiding from you.", "Write what the shortcut was hiding.", ["movement", "public", "errand"]),
        mission("motion-half-speed", "Half Speed", "Walk at half speed for exactly one minute. Report what caught up with you.", "Write what caught up.", ["movement", "body", "low-energy"]),
        mission("motion-ankle-height", "Ankle-Height Treasure", "Take twenty steps and find one thing at ankle height worth keeping.", "Write the ankle-height thing.", ["movement", "visual", "outside", "public"]),
        mission("motion-three-circles", "Circle Collection", "On your next walk, collect three circles. Any size. Report your haul.", "Write the three circles.", ["movement", "visual", "shape", "outside", "public"]),
        mission("motion-five-color", "Color Before Noon", "Find five of one color before noon. The Book accepts photographs and testimony.", "Write the color and your five witnesses.", ["movement", "visual", "color", "public"]),
        mission("motion-halfway-point", "Invisible Halfway", "Cross any street or hallway and notice the exact moment you are halfway. Halfway points are invisible until you look.", "Write where halfway appeared.", ["movement", "threshold", "public"], allowsPhoto: false),
        mission("motion-unwatched-moving", "Watch It For Them", "Next time you are a passenger or waiting in line, find the one moving thing nobody else is watching. Watch it for them.", "Write the unwatched moving thing.", ["movement", "public", "visual"]),
        mission("work-building-voice", "Workplace Voice", "Find the one sound your workplace makes that no other building on Earth makes. That is its voice.", "Write the workplace voice.", ["work", "sound", "public"], allowsPhoto: false),
        mission("work-ignored-object-title", "Gallery Title", "Locate the most ignored object at work and give it a title, like a painting in a gallery.", "Write the object's gallery title.", ["work", "object", "visual", "public"]),
        mission("work-machine-mood", "Machine Mood", "Your machine has moods. What is today's?", "Write the machine and today's mood.", ["work", "object", "public"]),
        mission("work-boring-minute-moving", "Boring Minute Motion", "During the most boring minute of your day, find one thing that is moving. Something always is.", "Write the moving thing.", ["work", "movement", "visual", "public"]),
        mission("work-small-tending", "Small Tending", "Find one coworker's small act of tending: a watered plant, a straightened stack, a propped door. Witness it for the record.", "Write the tending you witnessed.", ["work", "kindness", "public", "visual"]),
        mission("work-senior-staff", "Senior Staff", "Find the oldest thing in your workplace that still does its job every day. Senior staff. Note its tenure.", "Write the senior staff member and tenure.", ["work", "history", "object", "public"]),
        mission("work-route-new-thing", "Route River", "On your commute, find one thing that was not there last week. The route is not the same river twice.", "Write what changed on the route.", ["work", "commute", "public", "visual"]),
        mission("fuel-first-sip", "First Sip Report", "Hold the first sip of your next drink for five full seconds before swallowing. Report what is actually in there.", "Write what the sip contained.", ["taste", "fuel", "body", "low-energy"], allowsPhoto: false),
        mission("fuel-closed-eyes-bite", "Three Things In It", "Eat one bite with your eyes closed and name three things in it, not one.", "Write the three things.", ["taste", "fuel", "body"], allowsPhoto: false),
        mission("fuel-oldest-ingredient", "Oldest Ingredient", "Find the oldest ingredient in your next meal: the one that took longest to grow, age, or travel. Credit it.", "Write the ingredient and what it endured.", ["taste", "fuel", "history"], allowsPhoto: false),
        mission("fuel-smell-prediction", "Prediction Before Taste", "Smell something before you taste it and write down your prediction. Grade the prediction after.", "Write the prediction and the grade.", ["taste", "scent", "fuel"], allowsPhoto: false),
        mission("night-still-awake", "Still Awake", "Step outside after dark for thirty seconds. Count what is still awake.", "Write the count and one thing still awake.", ["night", "sound", "visual", "outside"]),
        mission("night-guard-light", "Last Light Guard", "Find the last light on in your house tonight and ask what it is guarding.", "Write what the light is guarding.", ["night", "light", "inside", "low-energy"]),
        mission("night-second-voice", "Second Voice", "Find one sound that only exists at night in your home. The house has a second voice it saves for after hours.", "Write the night-only sound.", ["night", "sound", "inside"], allowsPhoto: false),
        mission("night-farthest-light", "Farthest Light", "Look out a dark window and find the farthest light you can see. Someone or something is there. Wish them well.", "Write the farthest light.", ["night", "light", "visual", "inside"]),
        mission("strange-visual-rhyme", "Visual Rhyme", "Find something that visually rhymes with something else in the room: two shapes that did not know they matched. Introduce them.", "Write the two matching shapes.", ["visual", "shape", "inside", "imagination"]),
        mission("strange-street-new-old", "Street Introduction", "Find the newest thing on your street and the oldest. Introduce them to each other. Imagine the conversation.", "Write the introduction.", ["visual", "history", "outside", "imagination"]),
        mission("strange-outlive-you", "Outliving Object", "Touch something that will outlive you. Be polite about it.", "Write the object and the politeness.", ["touch", "object", "history", "inside"], allowsPhoto: false),
        mission("strange-new-thing", "New Thing", "Find something that did not exist a year ago, anywhere in view.", "Write the new thing.", ["visual", "history", "inside", "public"]),
        mission("strange-growth-decay", "Exchange Rate", "Find something mid-decay and something mid-growth within ten feet of each other. Note the exchange rate.", "Write the exchange rate.", ["visual", "nature", "history", "outside"]),
        mission("strange-age-gap", "Age Gap", "Estimate the age of one thing you can see, then find out if you can. Record the gap between guess and truth.", "Write the guess, the truth, or the mystery.", ["visual", "history", "object"]),
        mission("strange-stranger-decision", "A Stranger Chose That", "Pick up the nearest human-made object and find one decision a stranger made about it: a curve, a color, a button, a corner. Agree or disagree with them.", "Write the decision and your verdict.", ["object", "touch", "design", "inside"], allowsPhoto: false),
        mission("strange-technical-miracle", "Furniture Miracle", "Find one thing in arm's reach that is technically a miracle and is being treated like furniture. Restore its title for one minute.", "Write the restored title.", ["object", "wonder", "inside", "low-energy"])
    ]

    private static func mission(
        _ id: String,
        _ title: String,
        _ prompt: String,
        _ proofPrompt: String,
        _ tags: [String],
        allowsPhoto: Bool = true
    ) -> PlayfulMission {
        PlayfulMission(id: id, title: title, prompt: prompt, proofPrompt: proofPrompt, tags: tags, allowsPhoto: allowsPhoto)
    }
}

enum WonderCompassRunGenerator {
    static func seed(for day: BookDay, inputs: BookSourceInputs, progress: CompassRunProgress, now: Date = Date()) -> WonderCompassRunSeed {
        let mode = mode(for: day, inputs: inputs, now: now)
        let timeBox = timeBox(for: mode, inputs: inputs, now: now)
        let budget = mode == .budget ? "$0-$10" : "Use what is already available."
        let place = place(for: mode, inputs: inputs)
        let energy = energy(for: mode, inputs: inputs)
        let companions = companions(for: day)
        let considerations = considerations(for: mode, inputs: inputs)
        let circumstance = circumstance(for: inputs, now: now)
        let spark = progress.latestSpark ?? spark(for: mode, inputs: inputs, now: now)
        let destination = destination(for: mode, spark: spark, place: place)
        let delight = delight(for: mode, inputs: inputs, now: now)
        let definition = definition(for: mode, timeBox: timeBox)
        let mission = mission(for: mode, inputs: inputs)
        let souvenir = souvenirPrompt(for: mode)
        let rest = restPrompt(for: inputs)
        let slot = SurfaceCadence.slotID(for: now, hours: 6)

        return WonderCompassRunSeed(
            id: "run-\(day.id)-\(slot)-\(mode.rawValue)",
            mode: mode,
            timeBox: timeBox,
            budget: budget,
            place: place,
            energy: energy,
            companions: companions,
            considerations: considerations,
            circumstance: circumstance,
            spark: spark,
            destination: destination,
            delight: delight,
            definition: definition,
            mission: mission,
            souvenirPrompt: souvenir,
            restPrompt: rest,
            tags: ["wonder-compass", "wonder-compass-run", "concierge:\(mode.rawValue)"]
        )
    }

    private static func mode(for day: BookDay, inputs: BookSourceInputs, now: Date) -> WonderConciergeMode {
        let hour = Calendar.current.component(.hour, from: now)
        let capturedText = day.capturedPages.suffix(4).map { "\($0.promptText) \($0.userInput) \($0.tags.joined(separator: " "))" }.joined(separator: " ").lowercased()
        let bodyStatus = inputs.body?.status.lowercased() ?? ""
        if bodyStatus.contains("watch") || bodyStatus.contains("low") || capturedText.contains("tired") || capturedText.contains("rest") {
            return .recovery
        }
        if hour >= 19 || hour < 8 {
            return .closeToHome
        }
        if let weather = inputs.weather?.phrase.lowercased(),
           weather.contains("rain") || weather.contains("storm") || weather.contains("snow") || weather.contains("fog") {
            return .vibe
        }
        if capturedText.contains("cheap") || capturedText.contains("budget") || capturedText.contains("money") {
            return .budget
        }
        if capturedText.contains("weird") || capturedText.contains("old") || capturedText.contains("history") {
            return .obscure
        }
        if capturedText.contains("errand") || capturedText.contains("work") || capturedText.contains("store") {
            return .scavenger
        }
        return day.capturedPages.isEmpty ? .closeToHome : .vibe
    }

    private static func timeBox(for mode: WonderConciergeMode, inputs: BookSourceInputs, now: Date) -> String {
        switch mode {
        case .recovery:
            return "1-10 minutes"
        case .closeToHome:
            return "10-20 minutes"
        case .budget, .vibe, .scavenger:
            return "20-45 minutes"
        case .obscure:
            return "45-90 minutes"
        }
    }

    private static func place(for mode: WonderConciergeMode, inputs: BookSourceInputs) -> String {
        switch mode {
        case .closeToHome, .recovery:
            return "where the user already is"
        case .budget:
            return "nearby and cheap"
        case .obscure:
            return "within a reasonable local radius"
        case .vibe:
            if let weather = inputs.weather?.phrase {
                return "somewhere that fits this weather: \(weather)"
            }
            return "somewhere that fits the current mood"
        case .scavenger:
            return "the place the user already has to go"
        }
    }

    private static func energy(for mode: WonderConciergeMode, inputs: BookSourceInputs) -> String {
        if let body = inputs.body, body.isAvailable {
            return "\(body.status): \(body.phrase)"
        }
        switch mode {
        case .recovery:
            return "low; shrink the run"
        case .obscure:
            return "curious enough for a slightly larger loop"
        default:
            return "ordinary tired adult"
        }
    }

    private static func companions(for day: BookDay) -> String {
        let text = day.capturedPages.suffix(6).map { "\($0.promptText) \($0.userInput)" }.joined(separator: " ").lowercased()
        if text.contains("kid") || text.contains("child") || text.contains("children") {
            return "with kids"
        }
        if text.contains("partner") || text.contains("wife") || text.contains("husband") || text.contains("friend") {
            return "with someone trusted"
        }
        return "solo unless the user says otherwise"
    }

    private static func considerations(for mode: WonderConciergeMode, inputs: BookSourceInputs) -> String {
        var notes: [String] = []
        if mode == .recovery {
            notes.append("low energy")
        }
        if let weather = inputs.weather?.phrase.lowercased(),
           weather.contains("rain") || weather.contains("storm") || weather.contains("snow") || weather.contains("heat") {
            notes.append("weather-aware")
        }
        if inputs.body != nil {
            notes.append("body signals outrank the plan")
        }
        if notes.isEmpty {
            notes.append("no special constraints known")
        }
        return notes.joined(separator: ", ")
    }

    private static func circumstance(for inputs: BookSourceInputs, now: Date) -> String {
        var pieces: [String] = []
        if let weather = inputs.weather?.phrase {
            pieces.append("weather: \(weather)")
        }
        if let body = inputs.body?.phrase {
            pieces.append("body: \(body)")
        }
        let hour = Calendar.current.component(.hour, from: now)
        pieces.append(hour >= 18 ? "evening" : "daylight")
        return pieces.joined(separator: "; ")
    }

    private static func spark(for mode: WonderConciergeMode, inputs: BookSourceInputs, now: Date) -> String {
        WonderSparkRegistry.spark(for: mode, inputs: inputs, now: now)
    }

    private static func destination(for mode: WonderConciergeMode, spark: String, place: String) -> String {
        switch mode {
        case .closeToHome:
            return "one threshold nearby: a door, window, porch, kitchen table, or mailbox"
        case .budget:
            return "one free or cheap local stop tied to the spark"
        case .obscure:
            return "one odd sign, old building, marker, bridge, shop, or overlooked corner"
        case .vibe:
            return "one place or object that matches the mood"
        case .scavenger:
            return place
        case .recovery:
            return "the nearest chair, window, glass of water, blanket, or patch of light"
        }
    }

    private static func delight(for mode: WonderConciergeMode, inputs: BookSourceInputs, now: Date) -> String {
        switch mode {
        case .closeToHome:
            return "one song, warm drink, favorite hoodie, or good socks"
        case .budget:
            return "a cheap snack, road drink, playlist, or saved podcast"
        case .obscure:
            return "a camera-only phone, a playlist, and permission to leave if the place is dull"
        case .vibe:
            return "music, weather-appropriate clothes, or a drink that matches the atmosphere"
        case .scavenger:
            return "turn the errand into a game; the prize is the souvenir"
        case .recovery:
            return "comfort first: water, blanket, soft light, or silence"
        }
    }

    private static func definition(for mode: WonderConciergeMode, timeBox: String) -> String {
        switch mode {
        case .recovery:
            return "stop as soon as the body says stop"
        case .scavenger:
            return "finish after three finds or \(timeBox)"
        default:
            return "finish after \(timeBox)"
        }
    }

    private static func mission(for mode: WonderConciergeMode, inputs: BookSourceInputs) -> String {
        switch mode {
        case .closeToHome:
            return "Find the oldest, brightest, coldest, or most neglected thing within ten steps."
        case .budget:
            return "Find three details that make the cheap thing feel specific: smell, texture, sound."
        case .obscure:
            return "Photograph one overlooked detail and ask what story it is trying to keep."
        case .vibe:
            return "Compare the mood inside your body with the mood of the place. Name one match and one contrast."
        case .scavenger:
            return "Find five non-obvious things: a strange sign, a hidden color, an old date, a texture, and a tiny kindness."
        case .recovery:
            return "Feel one support: chair, floor, blanket, wall, breath. No improving."
        }
    }

    private static func souvenirPrompt(for mode: WonderConciergeMode) -> String {
        switch mode {
        case .recovery:
            return "Write proof of survival: I was here, and one thing held."
        default:
            return "Write one specific sensory sentence. Let the object do something if you can."
        }
    }

    private static func restPrompt(for inputs: BookSourceInputs) -> String {
        if inputs.body != nil {
            return "Take the 60-second reset or stop completely; body signals outrank the plan."
        }
        return "Put the phone face down for 60 seconds and let the run land."
    }

    static func body(for seed: WonderCompassRunSeed) -> String {
        """
        Answer the questions below. The Book will turn them into one custom Compass Run, then guide you through Notice, Embark, Sense, Write, and Rest one Page at a time.

        Location:
        Time limit:
        Energy:
        Who is with me:
        Budget:
        Special needs or considerations:
        """
    }
}

struct CharacterLetterPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .letter)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        if let prepared = inputs.preparedLetterSurface {
            return [prepared]
        }
        guard let draft = CharacterLetterPageGenerator.draftCandidate(for: day, inputs: inputs, now: now) else {
            return []
        }
        return [draft]
    }
}

// MARK: - Story forms and genres: the shapes stories arrive in.
//
// Expandable like every other content family: a bundled pack plus any
// *.storyforms.json dropped into Documents. The packet builder picks one
// form and one genre per page; continuations walk the form's beats.

struct StoryForm: Identifiable, Codable, Equatable {
    var id: String
    var name: String
    var directorNote: String
    var beats: [String]
}

struct StoryGenre: Identifiable, Codable, Equatable {
    var id: String
    var name: String
    var lens: String
    var moodTags: [String]
}

struct StoryFormPack: Codable, Identifiable, Equatable {
    var id: String
    var displayName: String
    var version: Int
    var author: String
    var availability: String
    var forms: [StoryForm]
    var genres: [StoryGenre]

    var isLocked: Bool { availability == "locked" }
}

enum StoryFormRegistry {
    static let userPackFileSuffix = ".storyforms.json"

    static let bundledPacks: [StoryFormPack] = [
        StoryFormPack(
            id: "core-story-forms",
            displayName: "Core Story Forms",
            version: 1,
            author: "The Book",
            availability: "bundledFree",
            forms: [
                StoryForm(
                    id: "threshold-crossing",
                    name: "The Threshold",
                    directorNote: "An ordinary boundary becomes a real one.",
                    beats: [
                        "Arrive: ground the scene in one real signal; everything is normal except one small thing.",
                        "Disturb: the small thing asks something of the reader; a character notices too.",
                        "Cross: a line is stepped over — physical, social, or spoken; it costs a little.",
                        "Settle: the new normal, one shade different; name what came through the door."
                    ]
                ),
                StoryForm(
                    id: "small-mystery",
                    name: "The Small Mystery",
                    directorNote: "Something doesn't add up, at kitchen scale.",
                    beats: [
                        "Notice: one specific oddity, stated plainly, no spookiness.",
                        "Investigate: a character and the reader each find one clue; the clues disagree.",
                        "Reveal: part of the answer, which makes the rest stranger.",
                        "Leave the thread: the mystery is smaller but not gone; someone keeps a souvenir of it."
                    ]
                ),
                StoryForm(
                    id: "visitation",
                    name: "The Visitation",
                    directorNote: "Someone arrives mid-task with their own agenda.",
                    beats: [
                        "Interrupt: a character arrives while something real is half-done; they need something.",
                        "Agenda: what they actually want surfaces sideways, through behavior not announcement.",
                        "Exchange: a gift, a favor, or a truth changes hands; the half-done task participates.",
                        "Residue: they leave; something of theirs remains, physical and slightly wrong."
                    ]
                ),
                StoryForm(
                    id: "quiet-epic",
                    name: "The Quiet Epic",
                    directorNote: "Tiny stakes carried with mythic seriousness.",
                    beats: [
                        "The quest is declared: something domestic and small, treated as if kingdoms depend on it.",
                        "The attempt: real effort, real obstacles, the world resists in petty believable ways.",
                        "The setback: comic or tender, never humiliating; an ally appears from the cast.",
                        "The modest triumph: the small thing is done; the scale of feeling stays epic."
                    ]
                ),
                StoryForm(
                    id: "correspondence",
                    name: "The Correspondence",
                    directorNote: "The scene happens around a piece of writing.",
                    beats: [
                        "Found: a note, letter, label, or margin scrawl turns up where it shouldn't be.",
                        "Read: its contents, quoted; what it asks for is not quite what it says.",
                        "Answer: the reader or a character writes back, in real ink, with one true line.",
                        "Sealed: the reply leaves by an odd route; what was unsaid stays behind, named."
                    ]
                ),
                StoryForm(
                    id: "nocturne",
                    name: "The Nocturne",
                    directorNote: "Night logic; the Nothing tests the edges.",
                    beats: [
                        "Lamp: the scene begins in low light with one warm source and one sound.",
                        "Fray: at the edge of attention, something has gone grey — a detail half-erased.",
                        "Hold: the reader and one character keep the detail lit by naming it precisely.",
                        "Ledger: dawn or sleep approaches; what was kept is written down, what was lost is admitted."
                    ]
                )
            ],
            genres: [
                StoryGenre(id: "cozy-mystery", name: "Cozy Mystery", lens: "Warm rooms, sharp questions. Tea is involved. Suspicion lands on objects, never cruelty on people.", moodTags: ["rain", "evening", "quiet", "tea"]),
                StoryGenre(id: "gentle-horror", name: "Gentle Horror", lens: "The hair-raising kept kind: wrongness in familiar things, dread that resolves into tenderness. The Nothing's territory.", moodTags: ["night", "fog", "tired", "grey"]),
                StoryGenre(id: "screwball", name: "Screwball Comedy", lens: "Fast, fond, and slightly unhinged. Characters talk over each other. Objects misbehave with comic timing.", moodTags: ["bright", "morning", "energy"]),
                StoryGenre(id: "field-naturalist", name: "Field Naturalist", lens: "Mary Oliver attention: exact observation, unforced wonder, the world examined like it matters because it does.", moodTags: ["walk", "outside", "weather", "calm"]),
                StoryGenre(id: "tiny-heist", name: "Tiny Heist", lens: "A caper at household scale — reclaiming a teacup, liberating a parking spot. Planning montage energy, zero crime.", moodTags: ["energy", "afternoon", "mission"]),
                StoryGenre(id: "pastoral", name: "Pastoral", lens: "Slow gold light, work done with the hands, conversation that breathes. Time moves like weather.", moodTags: ["calm", "garden", "season", "rest"]),
                StoryGenre(id: "kindly-ghost", name: "Kindly Ghost Story", lens: "Someone or something lingers because it loved this place. Memory made gently visible. Never menacing.", moodTags: ["memory", "old", "evening", "anchor"]),
                StoryGenre(id: "serial-adventure", name: "Adventure Serial", lens: "Chapter-of-a-larger-tale energy: momentum, a cliff's edge of curiosity at the end, callbacks to earlier episodes.", moodTags: ["thread", "arc", "momentum"])
            ]
        )
    ]

    static func userPacks(fileManager: FileManager = .default) -> [StoryFormPack] {
        guard let documents = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first,
              let contents = try? fileManager.contentsOfDirectory(at: documents, includingPropertiesForKeys: nil) else {
            return []
        }
        let decoder = JSONDecoder()
        return contents
            .filter { $0.lastPathComponent.hasSuffix(userPackFileSuffix) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
            .compactMap { url in
                guard let data = try? Data(contentsOf: url) else { return nil }
                return try? decoder.decode(StoryFormPack.self, from: data)
            }
            .filter { !$0.isLocked }
    }

    static func enabledPacks() -> [StoryFormPack] {
        bundledPacks.filter { !$0.isLocked || PackEntitlements.isUnlocked($0.id) } + userPacks()
    }

    static var forms: [StoryForm] {
        var seen = Set<String>()
        return enabledPacks().flatMap(\.forms).filter { seen.insert($0.id).inserted }
    }

    static var genres: [StoryGenre] {
        var seen = Set<String>()
        return enabledPacks().flatMap(\.genres).filter { seen.insert($0.id).inserted }
    }

    /// Picks a form and genre for this page: tag affinity chooses among
    /// genres, the ascendant chapter leans on the lens, and the variety
    /// history keeps consecutive pages from wearing the same shape.
    static func select(
        tags: Set<String>,
        surfaceHistory: [String: SurfaceHistoryRecord],
        ascendantChapterID: String?,
        dayID: String,
        slot: String,
        now: Date = Date()
    ) -> (form: StoryForm, genre: StoryGenre) {
        let allForms = forms
        let allGenres = genres

        func recencyPenalty(_ key: String) -> Int {
            guard let record = surfaceHistory[key] else { return 0 }
            let hours = now.timeIntervalSince(record.lastShownAt) / 3600
            if hours < 12 { return 8 }
            if hours < 48 { return 4 }
            return 0
        }

        let chapterGenreBias: [String: String] = [
            "duskthorn": "gentle-horror",
            "tidecrest": "serial-adventure",
            "mossbloom": "field-naturalist",
            "riddlewind": "cozy-mystery",
            "emberheart": "tiny-heist"
        ]

        let scoredGenres = allGenres.map { genre -> (StoryGenre, Int) in
            var score = tags.intersection(Set(genre.moodTags)).count * 4
            if let chapterID = ascendantChapterID, chapterGenreBias[chapterID] == genre.id {
                score += 3
            }
            score -= recencyPenalty("genre:\(genre.id)")
            score += abs("\(dayID)-\(slot)-\(genre.id)-genre".stableHash % 5)
            return (genre, score)
        }
        let genre = scoredGenres.max { $0.1 < $1.1 }?.0 ?? allGenres[0]

        let scoredForms = allForms.map { form -> (StoryForm, Int) in
            var score = abs("\(dayID)-\(slot)-\(form.id)-form".stableHash % 7)
            score -= recencyPenalty("form:\(form.id)")
            // The Nocturne belongs to the night.
            let hour = Calendar.current.component(.hour, from: now)
            if form.id == "nocturne" {
                score += (hour >= 21 || hour < 5) ? 4 : -4
            }
            return (form, score)
        }
        let form = scoredForms.max { $0.1 < $1.1 }?.0 ?? allForms[0]
        return (form, genre)
    }
}

// MARK: - Compass venture reading
//
// Custom Compass Runs read the player's stated energy before deciding how
// far to send them: depleted days stay home, steadier days sometimes earn a
// real named destination — sometimes, not always.

enum CompassVentureMode: String, Equatable {
    case homebound
    case neighborhood
    case destination
}

enum CompassVenture {
    /// 0 = depleted, 1 = low, 2 = steady, 3 = bright.
    static func energyTier(from text: String) -> Int {
        let lowered = text.lowercased()
        if let match = lowered.range(of: #"\d{1,3}"#, options: .regularExpression),
           let value = Int(lowered[match]) {
            switch value {
            case ..<25: return 0
            case ..<45: return 1
            case ..<70: return 2
            default: return 3
            }
        }
        let depleted = ["exhaust", "wiped", "drained", "empty", "sick", "crash", "depleted", "running on fumes", "dead"]
        let low = ["tired", "low", "meh", "fog", "heavy", "sleepy", "weary", "worn"]
        let bright = ["great", "good", "energized", "fresh", "restless", "bouncy", "high", "excited", "alive"]
        if depleted.contains(where: lowered.contains) { return 0 }
        if low.contains(where: lowered.contains) { return 1 }
        if bright.contains(where: lowered.contains) { return 3 }
        return 2
    }

    static func minutesAvailable(from timeLimit: String) -> Int? {
        let lowered = timeLimit.lowercased()
        guard let match = lowered.range(of: #"\d{1,3}"#, options: .regularExpression),
              let value = Int(lowered[match]) else {
            return nil
        }
        if lowered.contains("hour") || lowered.contains("hr") || lowered.contains("day") {
            return value * 60
        }
        return value
    }

    static func decide(
        energyText: String,
        considerations: String,
        timeLimit: String,
        hasPlaces: Bool,
        roll: Double
    ) -> CompassVentureMode {
        let lowered = considerations.lowercased()
        let homeboundWords = ["indoors only", "can't leave", "cannot leave", "housebound", "stuck home", "in bed", "no car", "staying in", "homebound", "kids asleep", "kids napping", "baby is asleep"]
        if homeboundWords.contains(where: lowered.contains) {
            return .homebound
        }

        let tier = energyTier(from: energyText)
        if tier <= 0 {
            return .homebound
        }
        if tier == 1 {
            // Low energy: the door stays optional; never a named trip.
            return roll < 0.7 ? .homebound : .neighborhood
        }
        // A real destination needs real time.
        if let minutes = minutesAvailable(from: timeLimit), minutes <= 15 {
            return .neighborhood
        }
        guard hasPlaces else { return .neighborhood }
        let threshold = tier == 2 ? 0.5 : 0.78
        return roll < threshold ? .destination : .neighborhood
    }
}

// MARK: - The Wonder Spark Registry
//
// North = Notice begins with an "I wonder..." A large tagged pool keeps the
// question surprising: selection favors sparks that fit the concierge mode,
// the hour, and the weather, with slot rotation so consecutive runs differ.

struct WonderSpark: Identifiable, Equatable {
    var id: String
    var text: String
    var modes: [WonderConciergeMode]
    var tags: [String]
}

enum WonderSparkRegistry {
    static func spark(
        for mode: WonderConciergeMode,
        inputs: BookSourceInputs,
        now: Date = Date(),
        dayID: String = BookDay.today().id
    ) -> String {
        let pool = sparks.filter { $0.modes.contains(mode) }
        guard !pool.isEmpty else { return "I wonder what is asking for attention nearby?" }

        let hour = Calendar.current.component(.hour, from: now)
        var contextTags: Set<String> = []
        switch hour {
        case 5..<11: contextTags.insert("morning")
        case 17..<21: contextTags.insert("evening")
        case 21..<24, 0..<5: contextTags.insert("night")
        default: break
        }
        let weather = (inputs.weather?.phrase ?? "").lowercased()
        if weather.contains("rain") || weather.contains("drizzle") { contextTags.insert("rain") }
        if weather.contains("snow") || weather.contains("ice") { contextTags.insert("cold") }
        if weather.contains("sun") || weather.contains("clear") { contextTags.insert("bright") }
        if weather.contains("wind") { contextTags.insert("wind") }
        let body = (inputs.body?.phrase ?? "").lowercased()
        if body.contains("low") || body.contains("tired") || body.contains("rest") { contextTags.insert("gentle") }

        let slot = SurfaceCadence.slotID(for: now, hours: 2)
        let scored = pool.map { spark -> (WonderSpark, Int) in
            let affinity = contextTags.intersection(Set(spark.tags)).count * 6
            let jitter = abs("\(dayID)-\(slot)-\(spark.id)-spark".stableHash % 11)
            return (spark, affinity + jitter)
        }
        return scored.max { $0.1 < $1.1 }?.0.text ?? pool[0].text
    }

    private static func spark(_ id: String, _ text: String, _ modes: [WonderConciergeMode], _ tags: [String] = []) -> WonderSpark {
        WonderSpark(id: id, text: text, modes: modes, tags: tags)
    }

    /// Night-tuned sparks bound into the Nocturne Folio; they join the pool
    /// when the folio is bound to the save.
    static let nocturneSparks: [WonderSpark] = [
        spark("nf-window-lit", "I wonder which window on my street is lit right now, and what honest errand the light is running?", [.obscure, .vibe], ["night"]),
        spark("nf-night-smell", "I wonder what the night smells like tonight that the day didn't?", [.recovery, .vibe], ["night"]),
        spark("nf-house-settle", "I wonder which part of the house settles first when everyone stops moving?", [.closeToHome, .recovery], ["night", "gentle"]),
        spark("nf-moon-furniture", "I wonder what the moon is rearranging in the yard while nobody supervises?", [.obscure, .scavenger], ["night"]),
        spark("nf-last-car", "I wonder where the last car I can hear is going, and whether they know?", [.vibe, .obscure], ["night"]),
        spark("nf-dark-rooms", "I wonder what the unlit rooms of my home do differently when I'm not in them?", [.closeToHome, .obscure], ["night"])
    ]

    static var sparks: [WonderSpark] {
        PackEntitlements.isUnlocked("nocturne-folio") ? baseSparks + nocturneSparks : baseSparks
    }

    static let baseSparks: [WonderSpark] = [
        // Close to home: the room is stranger than it admits.
        spark("oldest-object", "I wonder what the oldest thing within ten steps of me is, and how it got here?", [.closeToHome, .recovery]),
        spark("room-archaeology", "I wonder what a careful stranger could deduce about this week from this room alone?", [.closeToHome, .obscure]),
        spark("drawer-stranger", "I wonder what the strangest thing in the nearest drawer is doing with its life?", [.closeToHome, .scavenger]),
        spark("wall-history", "I wonder which mark on these walls has a story nobody remembers?", [.closeToHome, .obscure]),
        spark("window-theater", "I wonder what the nearest window is showing right now that it will never show again?", [.closeToHome, .recovery], ["morning", "evening"]),
        spark("light-landing", "I wonder where the light lands first in this room, and what it chooses to touch?", [.closeToHome], ["morning", "bright"]),
        spark("gravity-objects", "I wonder which object in this room would be hardest to explain to the year 1900?", [.closeToHome, .vibe]),
        spark("home-sounds", "I wonder how many different sounds this building makes when I hold completely still?", [.closeToHome, .recovery], ["night", "gentle"]),
        spark("borrowed-things", "I wonder how many things in this room I never actually chose?", [.closeToHome, .obscure]),
        spark("repair-marks", "I wonder what has been mended around here, and whether the mend shows?", [.closeToHome], ["gentle"]),
        spark("door-census", "I wonder which door in my home opens most often, and which has almost given up hope?", [.closeToHome, .scavenger]),
        spark("ceiling-country", "I wonder what lives in the parts of this room above eye level that I never visit?", [.closeToHome]),

        // Budget: rich on pocket change.
        spark("two-dollar-luxury", "I wonder what the most luxurious thing I can do for under two dollars actually is?", [.budget, .vibe]),
        spark("free-museum", "I wonder what the best free exhibit within walking distance is — a window, a tree, a bulletin board?", [.budget, .obscure], ["bright"]),
        spark("expensive-smell", "I wonder where the most expensive-smelling free air in town is?", [.budget, .scavenger]),
        spark("penny-bright", "I wonder what the shiniest thing I can find without spending anything is?", [.budget], ["bright"]),
        spark("library-oracle", "I wonder what the library would hand me today if I let shelf chance decide?", [.budget, .obscure]),
        spark("sample-day", "I wonder which place nearby gives something small away free, and who decided that?", [.budget]),
        spark("quarter-tour", "I wonder how grand a tour I could give of this neighborhood using only things that cost nothing to see?", [.budget, .obscure], ["bright"]),
        spark("best-bench", "I wonder which free seat in town has the best view nobody pays for?", [.budget, .vibe], ["bright", "evening"]),

        // Obscure: strange little stories.
        spark("oldest-sign", "I wonder what the oldest sign in town still says, and to whom?", [.obscure, .scavenger]),
        spark("ghost-paint", "I wonder where a painted-over word or picture is still faintly visible nearby?", [.obscure]),
        spark("desire-path", "I wonder where people have voted with their feet — a worn shortcut the planners never drew?", [.obscure], ["bright"]),
        spark("lost-glove", "I wonder where the nearest lost glove, sock, or key is waiting, and what its other half is doing?", [.obscure, .scavenger], ["cold"]),
        spark("plaque-nobody", "I wonder what the nearest plaque or memorial actually commemorates — and who last read it?", [.obscure]),
        spark("name-origin", "I wonder why the street I use most is named what it's named?", [.obscure]),
        spark("oldest-tree", "I wonder which tree in this neighborhood was here before any of the houses?", [.obscure, .recovery], ["bright", "wind"]),
        spark("back-of-things", "I wonder what the backs of buildings on my usual route look like — the side they don't dress up?", [.obscure]),
        spark("water-route", "I wonder where the rain that lands on my roof eventually ends up?", [.obscure], ["rain"]),
        spark("midnight-business", "I wonder what is open right now that has no obvious reason to be?", [.obscure], ["night"]),

        // Vibe: mood as compass needle.
        spark("mood-color", "I wonder what color today's mood is, and where that color is hiding nearby?", [.vibe, .recovery]),
        spark("weather-twin", "I wonder what in my house feels exactly like today's weather?", [.vibe], ["rain", "cold", "bright", "wind"]),
        spark("soundtrack-street", "I wonder what song this hour would choose for itself if I let it?", [.vibe], ["evening"]),
        spark("temperature-feelings", "I wonder where the warmest and coldest spots within reach are, and which one today needs?", [.vibe, .closeToHome], ["cold", "gentle"]),
        spark("borrowed-calm", "I wonder which nearby thing is the calmest, and whether it's contagious?", [.vibe, .recovery], ["gentle"]),
        spark("hour-flavor", "I wonder what this exact hour tastes like, and what snack would agree with it?", [.vibe, .budget]),

        // Scavenger: collectible reality.
        spark("triangle-hunt", "I wonder how many accidental triangles are hiding in plain sight here?", [.scavenger, .closeToHome]),
        spark("alphabet-walk", "I wonder how far through the alphabet I can get, finding things that start with each letter?", [.scavenger], ["bright"]),
        spark("face-pareidolia", "I wonder where the nearest accidental face is — in a socket, a car grill, a knot of wood?", [.scavenger, .closeToHome]),
        spark("seven-greens", "I wonder how many different greens exist within a hundred steps of my door?", [.scavenger], ["bright"]),
        spark("texture-trio", "I wonder what the roughest, smoothest, and softest things within arm's reach are?", [.scavenger, .recovery], ["gentle"]),
        spark("number-hunt", "I wonder where today's date is hiding in the wild — on signs, receipts, license plates?", [.scavenger]),
        spark("shadow-collection", "I wonder which shadow nearby is the most elaborate, and what's casting it?", [.scavenger], ["bright", "evening"]),
        spark("circle-census", "I wonder what the roundest thing in this room is, and whether anything is perfectly round at all?", [.scavenger, .closeToHome]),
        spark("oldest-newest", "I wonder what the oldest and newest things I can see right now are, side by side?", [.scavenger, .closeToHome]),
        spark("tiny-doors", "I wonder where the smallest door, hatch, or opening in this building is, and what uses it?", [.scavenger, .obscure]),

        // Recovery: noticing without pushing.
        spark("breath-weather", "I wonder what my breath would report about this exact minute if I let it speak?", [.recovery], ["gentle", "night"]),
        spark("soft-inventory", "I wonder what the softest thing I can see from here is, without moving?", [.recovery], ["gentle"]),
        spark("holding-things", "I wonder what is quietly holding weight for me right now — chair, floor, wall, cup?", [.recovery], ["gentle"]),
        spark("slow-clock", "I wonder what the slowest-moving thing in my field of view is?", [.recovery], ["night", "gentle"]),
        spark("kind-light", "I wonder which light in this room is the kindest, and what it's being kind to?", [.recovery], ["evening", "night"]),
        spark("one-good-sound", "I wonder what the single most comforting sound within earshot is right now?", [.recovery], ["gentle", "rain"]),
        spark("blanket-geology", "I wonder what landscape the folds of the nearest cloth would be, if I were very small?", [.recovery, .closeToHome], ["gentle"]),

        // Wide-mode wonders: fit nearly anywhere.
        spark("almost-said", "I wonder what the last thing this room almost heard somebody say was?", [.closeToHome, .vibe, .obscure]),
        spark("future-fossil", "I wonder which object near me would make the best fossil for future archaeologists?", [.closeToHome, .scavenger, .obscure]),
        spark("secret-effort", "I wonder what nearby is working hard while looking effortless — a hinge, a stem, a seam?", [.closeToHome, .recovery, .scavenger]),
        spark("first-visitor", "I wonder what visited my street this morning before anyone was awake?", [.obscure, .vibe], ["morning"]),
        spark("rain-instruments", "I wonder which surfaces outside play the rain best — what's the percussion section?", [.vibe, .obscure], ["rain"]),
        spark("wind-errands", "I wonder what the wind is moving around the neighborhood right now, and where it's taking it?", [.vibe, .obscure], ["wind"]),
        spark("snow-ledger", "I wonder what tracks the cold has recorded since last night, and who wrote them?", [.obscure, .scavenger], ["cold"]),
        spark("dusk-handover", "I wonder what changes hands in the neighborhood at dusk — which lights take over from the sun?", [.vibe, .obscure], ["evening"]),
        spark("night-shift", "I wonder what is awake on my street right now besides me?", [.recovery, .obscure], ["night"]),
        spark("morning-rehearsal", "I wonder what the day is rehearsing outside before it fully begins?", [.vibe, .recovery], ["morning"]),
        spark("forgotten-pocket", "I wonder what the pockets of my least-worn coat have been keeping for me?", [.closeToHome, .scavenger], ["cold"]),
        spark("appliance-choir", "I wonder which appliance hums the lowest note in the house choir?", [.closeToHome, .scavenger], ["night"]),
        spark("plant-opinion", "I wonder which plant nearby is having the best week, and what its secret is?", [.recovery, .obscure], ["bright"]),
        spark("step-counter", "I wonder exactly how many steps it takes to cross my home at its longest, walked like it matters?", [.closeToHome, .scavenger], ["gentle"]),
        spark("handwriting-wild", "I wonder where the nearest handwriting in the wild is — not printed, actually written by a hand?", [.obscure, .scavenger]),
        spark("blue-hour", "I wonder which blue, of all the blues I can find right now, is the bluest?", [.scavenger, .vibe], ["evening", "bright"]),
        spark("usefulness-retired", "I wonder what near me used to be essential and is now purely decorative?", [.closeToHome, .obscure]),
        spark("smallest-kindness", "I wonder what the smallest act of kindness visible from here is — a coaster, a propped door, a refilled bowl?", [.recovery, .vibe], ["gentle"]),
        spark("echo-spots", "I wonder where the best echo within a hundred steps lives?", [.scavenger, .obscure], ["bright"]),
        spark("crooked-true", "I wonder what nearby is charmingly crooked, and whether anyone ever tried to straighten it?", [.closeToHome, .obscure]),
        spark("paper-trail", "I wonder what the oldest piece of paper in this room says?", [.closeToHome, .obscure], ["night", "gentle"]),
        spark("threshold-count", "I wonder how many thresholds I cross on an ordinary day without noticing a single one?", [.vibe, .recovery], ["morning"]),
        spark("borrowed-light", "I wonder which rooms in my home never get their own light, only borrowed light?", [.closeToHome, .obscure], ["evening"]),
        spark("season-leak", "I wonder where the current season is leaking into the house — a smell, a draft, a quality of light?", [.closeToHome, .vibe], ["cold", "bright", "rain"]),
        spark("instruction-art", "I wonder where the most beautiful purely functional thing nearby is — a fire escape, a gutter, a knot?", [.obscure, .vibe]),
        spark("waiting-things", "I wonder what near me has been waiting the longest — for use, for repair, for someone to notice?", [.closeToHome, .recovery], ["gentle"])
    ]
}

// MARK: - Story Arcs
//
// The season-scale spine: when one thread runs hot for days, it becomes the
// current arc and walks the phases — rising, climax, resolution, fading —
// bending Story Pages toward it until it settles into the past.

struct StoryArc: Codable, Equatable {
    var threadID: String
    var title: String
    var phase: StoryThreadPhase
    var startedAt: Date
    var phaseAdvancedAt: Date
}

enum ArcKeeper {
    static let promotionEventThreshold = 3
    static let promotionWindow: TimeInterval = 72 * 3600
    static let minimumPhaseDuration: TimeInterval = 2 * 86_400
    static let phaseEventThreshold = 2
    /// Threads that touch nearly every page never get to be "the" arc.
    static let ambientThreadIDs: Set<String> = ["ordinary-magic"]

    static func threadEventCount(threadID: String, events: [NarrativeEvent], since: Date) -> Int {
        events.filter { $0.createdAt >= since && ($0.effect.threadWeightDeltas[threadID] ?? 0) > 0 }.count
    }

    static func evaluate(
        current: StoryArc?,
        events: [NarrativeEvent],
        lastCompletedThreadID: String?,
        now: Date = Date()
    ) -> (arc: StoryArc?, announcement: String?) {
        if var arc = current {
            let phaseAge = now.timeIntervalSince(arc.phaseAdvancedAt)
            let eventsThisPhase = threadEventCount(threadID: arc.threadID, events: events, since: arc.phaseAdvancedAt)

            switch arc.phase {
            case .fading:
                if phaseAge >= minimumPhaseDuration {
                    return (nil, "The arc \u{201C}\(arc.title)\u{201D} settles into the past. The Stacks shelve it gently; its echoes remain.")
                }
            case .rising, .climax, .resolution:
                if phaseAge >= minimumPhaseDuration, eventsThisPhase >= phaseEventThreshold {
                    let next: StoryThreadPhase = arc.phase == .rising ? .climax : (arc.phase == .climax ? .resolution : .fading)
                    arc.phase = next
                    arc.phaseAdvancedAt = now
                    let line: String
                    switch next {
                    case .climax:
                        line = "The arc \u{201C}\(arc.title)\u{201D} turns toward its climax. The Stacks hold their breath."
                    case .resolution:
                        line = "The arc \u{201C}\(arc.title)\u{201D} begins to resolve. Debts come due, gently."
                    default:
                        line = "The arc \u{201C}\(arc.title)\u{201D} is fading into echoes."
                    }
                    return (arc, line)
                }
            default:
                break
            }
            return (arc, nil)
        }

        // No arc: promote the hottest non-ambient thread, with a cooldown on
        // the one that just finished.
        let since = now.addingTimeInterval(-promotionWindow)
        var counts: [String: Int] = [:]
        for event in events where event.createdAt >= since {
            for (threadID, delta) in event.effect.threadWeightDeltas where delta > 0 {
                guard !ambientThreadIDs.contains(threadID), threadID != lastCompletedThreadID else { continue }
                counts[threadID, default: 0] += 1
            }
        }
        guard let (threadID, count) = counts.max(by: { $0.value == $1.value ? $0.key > $1.key : $0.value < $1.value }),
              count >= promotionEventThreshold,
              let thread = NarrativePackRegistry.threads.first(where: { $0.id == threadID }) else {
            return (nil, nil)
        }
        let arc = StoryArc(
            threadID: threadID,
            title: thread.title,
            phase: .rising,
            startedAt: now,
            phaseAdvancedAt: now
        )
        return (arc, "A story is rising in the Stacks: \u{201C}\(thread.title)\u{201D} has become the current arc.")
    }

    static func directive(for phase: StoryThreadPhase) -> String {
        switch phase {
        case .rising:
            return "The arc is RISING: gather allies, obstacles, and small omens around this thread. Raise the stakes one honest notch; promise more than you pay."
        case .climax:
            return "The arc is at its CLIMAX: this scene should burn the thread's central tension at full flame — something small but irreversible happens, at household scale. No cliffhanger-dodging."
        case .resolution:
            return "The arc is RESOLVING: pay one debt the arc created. Let a consequence land and a character change their behavior because of it."
        case .fading:
            return "The arc is FADING: it appears only as echoes now — a reference, a leftover object, a changed habit. Do not reignite it."
        default:
            return "Let the arc thread breathe in the background."
        }
    }
}
