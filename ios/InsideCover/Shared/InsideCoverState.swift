import Foundation

struct InsideCoverState: Codable, Equatable {
    var generatedAt: String
    var player: String
    var title: String
    var day: String
    var block: String
    var now: String
    var next: String
    var club: String
    var practice: String
    var practicePrompt: String
    var classroom: ClassroomState?
    var health: HealthState?
    var note: String
    var image: String
    var imageData: String?
    var openURL: String

    static let fallback = InsideCoverState(
        generatedAt: "",
        player: "bj",
        title: "ReEnchanted",
        day: "The Academy is listening",
        block: "Between Pages",
        now: "No fresh state imported",
        next: "Import widget-state.json",
        club: "",
        practice: "Open the Book",
        practicePrompt: "Run scripts/widget-state.py, then import the JSON into this app.",
        classroom: nil,
        health: HealthState(status: "WATCH", score: 0, phrase: "The shelves are waiting for ink."),
        note: "The Book is awake behind the glass.",
        image: "",
        imageData: nil,
        openURL: "telegram://"
    )
}

struct ClassroomState: Codable, Equatable {
    var className: String
    var professor: String
    var lesson: String
    var segment: String
    var active: Bool
}

struct HealthState: Codable, Equatable {
    var status: String
    var score: Int
    var phrase: String
}

enum BookPageType: String, Codable, CaseIterable, Identifiable {
    case mood
    case souvenir
    case rest
    case body
    case fuel
    case weather
    case location
    case quip
    case aboutYou
    case wonderCompass
    case lore
    case patreon
    case illustration
    case illuminatedPhoto
    case narrativeOS
    case gossip
    case facultyResearch
    case supportGuild
    case bookOfYou

    var id: String { rawValue }

    var title: String {
        switch self {
        case .mood:
            return "Inner Weather"
        case .souvenir:
            return "One-Sentence Souvenir"
        case .rest:
            return "Center Page"
        case .body:
            return "Body Page"
        case .fuel:
            return "Fuel Log"
        case .weather:
            return "Weather Page"
        case .location:
            return "Location Page"
        case .quip:
            return "Quip Page"
        case .aboutYou:
            return "About You"
        case .wonderCompass:
            return "From the Wonder Compass Book"
        case .lore:
            return "Lore Page"
        case .patreon:
            return "Patreon Page"
        case .illustration:
            return "An Illustration from the Labyrinth of Stories"
        case .illuminatedPhoto:
            return "Found in the Margins"
        case .narrativeOS:
            return "Story Page"
        case .gossip:
            return "Gossip Page"
        case .facultyResearch:
            return "Faculty Research Note"
        case .supportGuild:
            return "Support Guild Page"
        case .bookOfYou:
            return "Book of You"
        }
    }

    var shortTitle: String {
        switch self {
        case .mood:
            return "Weather"
        case .souvenir:
            return "Souvenir"
        case .rest:
            return "Rest"
        case .body:
            return "Body"
        case .fuel:
            return "Fuel"
        case .weather:
            return "Weather"
        case .location:
            return "Place"
        case .quip:
            return "Quip"
        case .aboutYou:
            return "You"
        case .wonderCompass:
            return "Wonder Book"
        case .lore:
            return "Lore"
        case .patreon:
            return "Patreon"
        case .illustration:
            return "Illustration"
        case .illuminatedPhoto:
            return "Illuminated"
        case .narrativeOS:
            return "Story"
        case .gossip:
            return "Gossip"
        case .facultyResearch:
            return "Research"
        case .supportGuild:
            return "Guild"
        case .bookOfYou:
            return "Braid"
        }
    }

    var symbolName: String {
        switch self {
        case .mood:
            return "cloud.sun"
        case .souvenir:
            return "quote.opening"
        case .rest:
            return "moon.stars"
        case .body:
            return "figure.mind.and.body"
        case .fuel:
            return "fork.knife"
        case .weather:
            return "cloud.rain"
        case .location:
            return "map"
        case .quip:
            return "sparkles"
        case .aboutYou:
            return "person.text.rectangle"
        case .wonderCompass:
            return "safari"
        case .lore:
            return "books.vertical"
        case .patreon:
            return "shippingbox"
        case .illustration:
            return "photo.artframe"
        case .illuminatedPhoto:
            return "photo.on.rectangle.angled"
        case .narrativeOS:
            return "point.3.connected.trianglepath.dotted"
        case .gossip:
            return "bubble.left.and.text.bubble.right"
        case .facultyResearch:
            return "doc.text.magnifyingglass"
        case .supportGuild:
            return "cross.case"
        case .bookOfYou:
            return "book.closed"
        }
    }
}

enum BookPageOrigin: String, Codable, Equatable {
    case userAuthored
    case generated
    case imported
    case simulated
}

enum BookPagePrivacy: String, Codable, Equatable {
    case privateLocal
    case localSensitive
    case publicReference
}

enum BookPageIntent: String, Codable, Equatable {
    case capture
    case reflect
    case rest
    case braid
    case importReference
    case resurface
    case simulate
}

enum BookPageRenderStyle: String, Codable, Equatable {
    case promptCard
    case gentleTranslation
    case quoteCard
    case loreLetter
    case illustrationPlate
    case illuminatedPhoto
    case graphEvent
    case archiveReturn
}

struct BookPagePayload: Codable, Equatable {
    var headline: String
    var body: String
    var metadata: [String: String]

    init(headline: String, body: String, metadata: [String: String] = [:]) {
        self.headline = headline
        self.body = body
        self.metadata = metadata
    }
}

struct BookPageSource: Codable, Identifiable, Equatable {
    var id: String
    var type: BookPageType
    var title: String
    var shortTitle: String
    var symbolName: String
    var origin: BookPageOrigin
    var privacy: BookPagePrivacy
    var isActive: Bool
    var cadence: String
    var note: String
}

enum BookPageSourceRegistry {
    static let sources: [BookPageSource] = [
        BookPageSource(
            id: "inner-weather",
            type: .mood,
            title: "Inner Weather",
            shortTitle: "Mood",
            symbolName: "cloud.sun",
            origin: .userAuthored,
            privacy: .privateLocal,
            isActive: true,
            cadence: "daily",
            note: "Named by you."
        ),
        BookPageSource(
            id: "one-sentence-souvenir",
            type: .souvenir,
            title: "One-Sentence Souvenir",
            shortTitle: "Souvenir",
            symbolName: "quote.opening",
            origin: .userAuthored,
            privacy: .privateLocal,
            isActive: true,
            cadence: "evening",
            note: "A moment worth keeping."
        ),
        BookPageSource(
            id: "center-page",
            type: .rest,
            title: "Center Page",
            shortTitle: "Rest",
            symbolName: "moon.stars",
            origin: .userAuthored,
            privacy: .privateLocal,
            isActive: true,
            cadence: "as needed",
            note: "Low and gentle."
        ),
        BookPageSource(
            id: "book-of-you",
            type: .bookOfYou,
            title: "Book of You",
            shortTitle: "Braid",
            symbolName: "book.closed",
            origin: .generated,
            privacy: .privateLocal,
            isActive: true,
            cadence: "daily",
            note: "Today, braided."
        ),
        BookPageSource(
            id: "narrative-os",
            type: .narrativeOS,
            title: "Story Page",
            shortTitle: "Story",
            symbolName: "point.3.connected.trianglepath.dotted",
            origin: .simulated,
            privacy: .privateLocal,
            isActive: true,
            cadence: "simulation",
            note: "Characters, belief, threads."
        ),
        BookPageSource(
            id: "gossip-page",
            type: .gossip,
            title: "Gossip Page",
            shortTitle: "Gossip",
            symbolName: "bubble.left.and.text.bubble.right",
            origin: .simulated,
            privacy: .privateLocal,
            isActive: true,
            cadence: "four-hour turn",
            note: "What moved while you were elsewhere."
        ),
        BookPageSource(
            id: "support-guild",
            type: .supportGuild,
            title: "Support Guild Page",
            shortTitle: "Guild",
            symbolName: "cross.case",
            origin: .generated,
            privacy: .localSensitive,
            isActive: true,
            cadence: "daily synthesis",
            note: "Vellum and Inkrest compare charts."
        ),
        BookPageSource(
            id: "faculty-research",
            type: .facultyResearch,
            title: "Faculty Research Notes",
            shortTitle: "Research",
            symbolName: "doc.text.magnifyingglass",
            origin: .generated,
            privacy: .localSensitive,
            isActive: true,
            cadence: "before guild meeting",
            note: "Vellum and Inkrest prepare private research."
        ),
        BookPageSource(
            id: "body-page",
            type: .body,
            title: "Body Page",
            shortTitle: "Body",
            symbolName: "figure.mind.and.body",
            origin: .generated,
            privacy: .localSensitive,
            isActive: true,
            cadence: "responsive",
            note: "Care without naming sensors."
        ),
        BookPageSource(
            id: "fuel-log",
            type: .fuel,
            title: "Fuel Log",
            shortTitle: "Fuel",
            symbolName: "fork.knife",
            origin: .userAuthored,
            privacy: .localSensitive,
            isActive: true,
            cadence: "bell windows",
            note: "Dr. Vellum's plate notes."
        ),
        BookPageSource(
            id: "weather-page",
            type: .weather,
            title: "Weather Page",
            shortTitle: "Weather",
            symbolName: "cloud.rain",
            origin: .imported,
            privacy: .publicReference,
            isActive: true,
            cadence: "ambient",
            note: "The world outside."
        ),
        BookPageSource(
            id: "location-page",
            type: .location,
            title: "Location Page",
            shortTitle: "Place",
            symbolName: "map",
            origin: .generated,
            privacy: .localSensitive,
            isActive: false,
            cadence: "place",
            note: "Maps, anchors, Outer Stacks."
        ),
        BookPageSource(
            id: "quip-page",
            type: .quip,
            title: "Quip Page",
            shortTitle: "Quip",
            symbolName: "sparkles",
            origin: .imported,
            privacy: .publicReference,
            isActive: true,
            cadence: "throughout the day",
            note: "Odd facts and small perspective sparks."
        ),
        BookPageSource(
            id: "about-you",
            type: .aboutYou,
            title: "About You",
            shortTitle: "You",
            symbolName: "person.text.rectangle",
            origin: .userAuthored,
            privacy: .privateLocal,
            isActive: true,
            cadence: "gradual",
            note: "One question at a time, so the Book learns with consent."
        ),
        BookPageSource(
            id: "wonder-compass",
            type: .wonderCompass,
            title: "From the Wonder Compass Book",
            shortTitle: "Wonder Book",
            symbolName: "safari",
            origin: .imported,
            privacy: .publicReference,
            isActive: true,
            cadence: "practice",
            note: "Gemma-chosen book passages."
        ),
        BookPageSource(
            id: "labyrinth-lore",
            type: .lore,
            title: "Labyrinth Lore",
            shortTitle: "Lore",
            symbolName: "books.vertical",
            origin: .imported,
            privacy: .publicReference,
            isActive: true,
            cadence: "story",
            note: "Characters, rooms, classes, history, and living margins."
        ),
        BookPageSource(
            id: "patreon-packet",
            type: .patreon,
            title: "Patreon Packet",
            shortTitle: "Patreon",
            symbolName: "shippingbox",
            origin: .imported,
            privacy: .publicReference,
            isActive: true,
            cadence: "release",
            note: "Free downloads and Clubhouse doorway."
        ),
        BookPageSource(
            id: "labyrinth-illustrations",
            type: .illustration,
            title: "An Illustration from the Labyrinth of Stories",
            shortTitle: "Illustration",
            symbolName: "photo.artframe",
            origin: .imported,
            privacy: .publicReference,
            isActive: true,
            cadence: "hourly",
            note: "Bundled field-journal plates."
        ),
        BookPageSource(
            id: "illuminated-photos",
            type: .illuminatedPhoto,
            title: "Automatic Illuminated Photo Pages",
            shortTitle: "Illuminated",
            symbolName: "photo.on.rectangle.angled",
            origin: .generated,
            privacy: .privateLocal,
            isActive: true,
            cadence: "proposed",
            note: "Penny's local field-note press."
        )
    ]

    static let activeSources = sources.filter(\.isActive)
    static let plannedSources = sources.filter { !$0.isActive }

    static func source(for type: BookPageType) -> BookPageSource {
        sources.first { $0.type == type } ?? BookPageSource(
            id: type.rawValue,
            type: type,
            title: type.title,
            shortTitle: type.shortTitle,
            symbolName: type.symbolName,
            origin: type == .bookOfYou ? .generated : .userAuthored,
            privacy: .privateLocal,
            isActive: true,
            cadence: "manual",
            note: "Local page."
        )
    }

    static func source(id: String, fallbackType: BookPageType? = nil) -> BookPageSource {
        if let source = sources.first(where: { $0.id == id }) {
            return source
        }
        if let fallbackType {
            var source = Self.source(for: fallbackType)
            source.id = id
            return source
        }
        return BookPageSource(
            id: id,
            type: .souvenir,
            title: id,
            shortTitle: id,
            symbolName: "doc.text",
            origin: .userAuthored,
            privacy: .privateLocal,
            isActive: true,
            cadence: "manual",
            note: "Local page source."
        )
    }
}

struct ReferenceSnippet: Codable, Identifiable, Equatable {
    var id: String
    var sourceID: String
    var title: String
    var prompt: String
    var body: String
    var tags: [String]
    var url: String? = nil
    var publishedAt: String? = nil
    var preview: String? = nil
}

struct LorePack: Identifiable, Codable, Equatable {
    var id: String
    var displayName: String
    var version: String
    var author: String
    var availability: ContentPackAvailability
    var themes: [String]
    var snippets: [ReferenceSnippet]
}

enum NarrativeEntityKind: String, Codable, Equatable, CaseIterable {
    case character
    case location
    case object
    case thread
    case classRoom
    case talisman
    case realWorldAnchor
    case motif
}

struct NarrativeWorldEntity: Identifiable, Codable, Equatable {
    var id: String
    var packID: String
    var name: String
    var kind: NarrativeEntityKind
    var belief: Int
    var narrativeWeight: Int
    var chapter: String?
    var unwrittenInterest: String?
    var traits: [String]
    var quirks: [String]
    var faults: [String]
    var beliefs: [String]
    var goals: [String]
    var tags: [String]
}

enum StoryThreadPhase: String, Codable, Equatable, CaseIterable {
    case seed
    case returning
    case rising
    case climax
    case resolution
    case fading
}

struct NarrativeStoryThread: Identifiable, Codable, Equatable {
    var id: String
    var packID: String
    var title: String
    var phase: StoryThreadPhase
    var belief: Int
    var narrativeWeight: Int
    var summary: String
    var tags: [String]
}

enum NarrativeRelationshipKind: String, Codable, Equatable, CaseIterable {
    case authorship
    case attention
    case stewardship
    case care
    case correspondence
    case realityBleed
    case companionship
    case tension
}

struct NarrativeRelationshipEdge: Identifiable, Codable, Equatable {
    var id: String
    var packID: String
    var sourceEntityID: String
    var targetEntityID: String
    var kind: NarrativeRelationshipKind
    var warmth: Int
    var tension: Int
    var trust: Int
    var narrativeWeight: Int
    var note: String
    var tags: [String]
}

struct NarrativeEntityMemory: Identifiable, Codable, Equatable {
    var id: String
    var entityID: String
    var sourceEventID: String
    var sourcePageID: String?
    var summary: String
    var tags: [String]
    var narrativeWeight: Int
    var createdAt: Date
}

struct NarrativePack: Identifiable, Codable, Equatable {
    var id: String
    var displayName: String
    var version: String
    var author: String
    var availability: ContentPackAvailability
    var entities: [NarrativeWorldEntity]
    var threads: [NarrativeStoryThread]
    var relationships: [NarrativeRelationshipEdge]
}

enum SupportFacultyChartKind: String, Codable, Equatable, CaseIterable {
    case difficultPage
    case bodyMarginalia
}

struct SupportFacultyChart: Identifiable, Codable, Equatable {
    var id: String
    var packID: String
    var kind: SupportFacultyChartKind
    var facultyEntityID: String
    var facultyName: String
    var pageTitle: String
    var roleTitle: String
    var purpose: String
    var reads: [String]
    var allowedUses: [String]
    var forbiddenUses: [String]
    var invitations: [String]
    var closureConditions: [String]
    var artifactTypes: [String]
    var safetyLine: String
    var tags: [String]
}

struct SupportFacultyPack: Identifiable, Codable, Equatable {
    var id: String
    var displayName: String
    var version: String
    var author: String
    var availability: ContentPackAvailability
    var charts: [SupportFacultyChart]
}

enum NarrativeEventKind: String, Codable, Equatable, CaseIterable {
    case pageKept
    case pageAnswered
    case choiceSelected
    case beliefInvested
    case beliefAttacked
    case threadAdvanced
    case entityNoticed
    case letterReceived
    case compassRunCompleted
    case enchantmentCompleted
    case simulationTurn
}

struct NarrativeEventEffect: Codable, Equatable {
    var beliefDelta: Int
    var entityWeightDeltas: [String: Int]
    var threadWeightDeltas: [String: Int]
    var relationshipWeightDeltas: [String: Int]
    var createdEntityHint: String?

    init(
        beliefDelta: Int = 0,
        entityWeightDeltas: [String: Int] = [:],
        threadWeightDeltas: [String: Int] = [:],
        relationshipWeightDeltas: [String: Int] = [:],
        createdEntityHint: String? = nil
    ) {
        self.beliefDelta = beliefDelta
        self.entityWeightDeltas = entityWeightDeltas
        self.threadWeightDeltas = threadWeightDeltas
        self.relationshipWeightDeltas = relationshipWeightDeltas
        self.createdEntityHint = createdEntityHint
    }
}

struct NarrativeEvent: Identifiable, Codable, Equatable {
    var id: String
    var kind: NarrativeEventKind
    var sourcePageType: BookPageType?
    var sourcePageID: String?
    var createdAt: Date
    var summary: String
    var tags: [String]
    var effect: NarrativeEventEffect
}

struct NarrativeStoryFieldProjection: Equatable {
    var entityWeights: [String: Int]
    var threadWeights: [String: Int]
    var relationshipWeights: [String: Int]
    var belief: Int

    var topEntityIDs: [String] {
        ranked(entityWeights)
    }

    var topThreadIDs: [String] {
        ranked(threadWeights)
    }

    var topRelationshipIDs: [String] {
        ranked(relationshipWeights)
    }

    private func ranked(_ weights: [String: Int], limit: Int = 8) -> [String] {
        weights
            .sorted { left, right in
                if left.value == right.value {
                    return left.key < right.key
                }
                return left.value > right.value
            }
            .prefix(limit)
            .map(\.key)
    }
}

enum NarrativeStoryFieldProjector {
    static func projection(events: [NarrativeEvent], baseBelief: Int = 30) -> NarrativeStoryFieldProjection {
        var entityWeights = Dictionary(uniqueKeysWithValues: NarrativePackRegistry.entities.map {
            ($0.id, $0.narrativeWeight + $0.belief)
        })
        var threadWeights = Dictionary(uniqueKeysWithValues: NarrativePackRegistry.threads.map {
            ($0.id, $0.narrativeWeight + $0.belief)
        })
        var relationshipWeights = Dictionary(uniqueKeysWithValues: NarrativePackRegistry.relationships.map {
            ($0.id, $0.narrativeWeight + $0.warmth + $0.trust - $0.tension)
        })
        var belief = baseBelief

        for event in events {
            belief += event.effect.beliefDelta
            for (id, delta) in event.effect.entityWeightDeltas {
                entityWeights[id, default: 0] += delta
            }
            for (id, delta) in event.effect.threadWeightDeltas {
                threadWeights[id, default: 0] += delta
            }
            for (id, delta) in event.effect.relationshipWeightDeltas {
                relationshipWeights[id, default: 0] += delta
            }
        }

        return NarrativeStoryFieldProjection(
            entityWeights: entityWeights,
            threadWeights: threadWeights,
            relationshipWeights: relationshipWeights,
            belief: min(100, max(0, belief))
        )
    }
}

enum NarrativeEntityMemoryResolver {
    static func memories(for event: NarrativeEvent) -> [NarrativeEntityMemory] {
        let entityIDs = event.effect.entityWeightDeltas
            .filter { $0.value > 0 }
            .sorted { left, right in
                if left.value == right.value {
                    return left.key < right.key
                }
                return left.value > right.value
            }
            .prefix(5)
            .map(\.key)

        return entityIDs.map { entityID in
            NarrativeEntityMemory(
                id: "entity-memory-\(event.id)-\(entityID)",
                entityID: entityID,
                sourceEventID: event.id,
                sourcePageID: event.sourcePageID,
                summary: memorySummary(for: entityID, event: event),
                tags: event.tags,
                narrativeWeight: max(1, event.effect.entityWeightDeltas[entityID] ?? 1),
                createdAt: event.createdAt
            )
        }
    }

    private static func memorySummary(for entityID: String, event: NarrativeEvent) -> String {
        let entityName = NarrativePackRegistry.entities.first(where: { $0.id == entityID })?.name ?? entityID
        let pageName = event.sourcePageType?.shortTitle ?? "page"
        let trimmedSummary = event.summary.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedSummary.isEmpty {
            return "\(entityName) remembers that a \(pageName.lowercased()) page changed the margins."
        }
        return "\(entityName) remembers: \(trimmedSummary)"
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
    var choices: [StorySceneChoice]
}

enum NarrativePackRegistry {
    static let corePackID = "core-narrative-os"

    static let bundledPacks: [NarrativePack] = [
        NarrativePack(
            id: corePackID,
            displayName: "Core Story Field Pack",
            version: "0.1",
            author: "The Book",
            availability: .bundledFree,
            entities: coreEntities,
            threads: coreThreads,
            relationships: coreRelationships
        )
    ]

    static var enabledPacks: [NarrativePack] {
        bundledPacks.filter { $0.availability != .locked }
    }

    static var entities: [NarrativeWorldEntity] {
        enabledPacks.flatMap(\.entities)
    }

    static var threads: [NarrativeStoryThread] {
        enabledPacks.flatMap(\.threads)
    }

    static var relationships: [NarrativeRelationshipEdge] {
        enabledPacks.flatMap(\.relationships)
    }

    private static let coreEntities: [NarrativeWorldEntity] = [
        entity(
            "the-book",
            "The Book",
            .object,
            belief: 30,
            weight: 30,
            traits: ["attentive", "private", "patient"],
            quirks: ["speaks through margins", "keeps small proof"],
            faults: ["can become too subtle if not given a clear ritual"],
            beliefs: ["attention is a kind of care"],
            goals: ["turn real days into pages worth keeping"],
            tags: ["book", "private", "memory", "belief"]
        ),
        entity(
            "penny-blackletter",
            "Penny Blackletter",
            .character,
            belief: 24,
            weight: 18,
            chapter: "Riddlewind",
            unwrittenInterest: "Indie publishing, ethical marketing, Patreon, open-source storytelling, and the creator economy.",
            traits: ["dry", "warm", "observant"],
            quirks: ["files ridiculous evidence", "distrusts sentences that arrive too polished"],
            faults: ["can over-label a perfectly good mystery"],
            beliefs: ["one honest detail can save a day"],
            goals: ["recover what the margins nearly lost"],
            tags: ["character", "marginalia", "photos", "letters"]
        ),
        entity(
            "dr-inkrest",
            "Dr. Selene Inkrest",
            .character,
            belief: 34,
            weight: 18,
            chapter: "Riddlewind",
            unwrittenInterest: "Consciousness and brain studies as they relate to BJ.",
            traits: ["gentle", "precise", "therapeutic", "narrative-minded"],
            quirks: ["keeps office hours for difficult pages", "sets chairs out before feelings arrive"],
            faults: ["sometimes softens the knife too much", "can wait so patiently the room forgets to answer"],
            beliefs: ["a hard page deserves a chair and a lamp"],
            goals: ["help the reader reauthor without being rushed"],
            tags: ["character", "support-faculty", "care", "difficult-pages", "therapy-chart", "rest", "grounding", "reauthoring"]
        ),
        entity(
            "dr-vellum",
            "Dr. Elowen Vellum",
            .character,
            belief: 27,
            weight: 17,
            chapter: "Mossbloom",
            unwrittenInterest: "Longevity research, fuel, recovery, supplements, movement, and humane body experiments.",
            traits: ["precise", "warmly clinical", "experiment-minded", "low-shame"],
            quirks: ["turns breakfast into field notes", "can make a supplement interaction sound like etiquette"],
            faults: ["can become too fascinated by a tidy protocol"],
            beliefs: ["the body is not a problem to win against"],
            goals: ["translate fuel, movement, recovery, and health signals into one humane experiment"],
            tags: ["character", "support-faculty", "body", "fuel", "health", "vellum-chart", "longevity", "care"]
        ),
        entity(
            "headmistress-thorne",
            "Headmistress Seraphina Thorne",
            .character,
            belief: 26,
            weight: 20,
            chapter: "Duskthorn",
            unwrittenInterest: "Thresholds, hidden authority, institutional coherence, and the cost of keeping a living school safe.",
            traits: ["elegant", "watchful", "unseelie"],
            quirks: ["speaks as if buildings are listening", "keeps doors from admitting they are tests"],
            faults: ["can mistake secrecy for mercy"],
            beliefs: ["beauty is a form of governance"],
            goals: ["keep the Academy coherent while letting wonder stay dangerous enough to matter"],
            tags: ["character", "academy", "authority", "duskthorn", "threshold"]
        ),
        entity(
            "orion-blackthorn",
            "Orion Blackthorn",
            .character,
            belief: 18,
            weight: 14,
            chapter: "Emberheart",
            unwrittenInterest: "Architecture, innovation, ambitious systems, and the human cost of making impossible structures work.",
            traits: ["brilliant", "restless", "architectural"],
            quirks: ["turns problems into towers", "measures magic by what it can build"],
            faults: ["can optimize tenderness out of a room"],
            beliefs: ["new structures can rescue old failures"],
            goals: ["drag impossible ideas into usable form"],
            tags: ["character", "innovation", "architecture", "ambition", "academy"]
        ),
        entity(
            "zara-finch",
            "Zara Finch",
            .character,
            belief: 20,
            weight: 17,
            chapter: "Riddlewind",
            unwrittenInterest: "Trust, friendship, practical magic, hidden alcoves, and helping the reader find paths that hold.",
            traits: ["loyal", "quick", "ferociously observant"],
            quirks: ["notices exits before introductions", "keeps practical magic in her pockets"],
            faults: ["can confuse vigilance with care"],
            beliefs: ["trust is proven in small returns"],
            goals: ["help the reader find the path that does not collapse under them"],
            tags: ["character", "trust", "friendship", "threshold", "life"]
        ),
        entity(
            "wicker-eddies",
            "Wicker Eddies",
            .character,
            belief: 16,
            weight: 17,
            chapter: "Duskthorn",
            unwrittenInterest: "Testing belief, puncturing false magic, rumor pressure, and the places doubt can become useful or cruel.",
            traits: ["sharp", "funny", "dangerously persuasive"],
            quirks: ["attacks weak premises for sport", "can smell theatrical belief from across a room"],
            faults: ["sometimes wounds the thing he meant to test"],
            beliefs: ["false magic deserves to be punctured"],
            goals: ["make belief prove it can survive contact with doubt"],
            tags: ["character", "belief", "challenge", "tension", "nothing"]
        ),
        entity(
            "gwendolyn-mythwright",
            "Gwendolyn Mythwright",
            .character,
            belief: 19,
            weight: 15,
            chapter: "Mossbloom",
            unwrittenInterest: "Cryptids, impossible zoology, maritime mysteries, archives, and evidence that makes wonder less lonely.",
            traits: ["scholarly", "odd", "steadfast"],
            quirks: ["files impossible animals as if they are overdue forms", "writes letters to fog"],
            faults: ["may prefer evidence to comfort"],
            beliefs: ["the improbable becomes kinder when documented"],
            goals: ["catalog the impossible without frightening it away"],
            tags: ["character", "letters", "research", "impossible", "archive"]
        ),
        entity(
            "lydia-boggle",
            "Lydia Boggle",
            .character,
            belief: 17,
            weight: 13,
            chapter: "Riddlewind",
            unwrittenInterest: "Homes as vessels, domestic objects, tea, rooms, and the ordinary magic that survives chores.",
            traits: ["domestic", "wry", "practical"],
            quirks: ["can make tea sound like a tactical intervention", "labels chaos by room"],
            faults: ["can over-tidy a mystery"],
            beliefs: ["home is a spell with chores in it"],
            goals: ["teach ordinary rooms to hold extraordinary days"],
            tags: ["character", "home", "tea", "care", "objects"]
        ),
        entity(
            "soren-ng",
            "Soren Ng",
            .character,
            belief: 18,
            weight: 14,
            chapter: "Riddlewind",
            unwrittenInterest: "Maps, patterns, riddles, diagrams, hidden systems, and clues that become invitations.",
            traits: ["quiet", "precise", "pattern-minded"],
            quirks: ["leaves clues where only patient people look", "trusts diagrams more than declarations"],
            faults: ["can hide behind elegant systems"],
            beliefs: ["a map is an invitation, not an answer"],
            goals: ["help the reader notice the pattern without stealing the discovery"],
            tags: ["character", "map", "pattern", "thread", "attention"]
        ),
        entity(
            "weather-page",
            "The Weather Page",
            .motif,
            belief: 12,
            weight: 14,
            traits: ["legible", "atmospheric"],
            quirks: ["turns forecasts into room-light"],
            faults: ["must never name the sensor when naming the response"],
            beliefs: ["the sky can annotate without spying"],
            goals: ["make outer weather useful to inner story"],
            tags: ["weather", "atmosphere", "bleed"]
        ),
        entity(
            "body-page",
            "The Body Page",
            .motif,
            belief: 12,
            weight: 13,
            traits: ["careful", "low-pressure"],
            quirks: ["lowers lamps instead of making demands"],
            faults: ["can sound generic if it forgets the day"],
            beliefs: ["care should be responsive, not creepy"],
            goals: ["translate body signals into humane pacing"],
            tags: ["body", "care", "rest"]
        )
    ]

    private static let coreThreads: [NarrativeStoryThread] = [
        thread(
            "music-as-shelter",
            "Music as Shelter",
            .seed,
            belief: 8,
            weight: 12,
            summary: "Sounds, headphones, rhythm, and songs keep returning as small architecture for the day.",
            tags: ["music", "shelter", "souvenir", "mood"]
        ),
        thread(
            "ordinary-magic",
            "Ordinary Magic",
            .returning,
            belief: 14,
            weight: 16,
            summary: "The Book keeps finding evidence that ordinary objects become livelier under attention.",
            tags: ["wonder", "objects", "daily", "belief"]
        ),
        thread(
            "body-learns-trust",
            "The Body Learns Trust",
            .seed,
            belief: 11,
            weight: 13,
            summary: "Rest, fuel, movement, and low thresholds are becoming part of the story instead of interruptions to it.",
            tags: ["body", "rest", "care", "vellum-chart"]
        ),
        thread(
            "inkrest-difficult-pages",
            "Inkrest's Difficult Pages",
            .seed,
            belief: 10,
            weight: 12,
            summary: "Hard feelings are held as pages that can be named, seated near a lamp, and revised one hour at a time.",
            tags: ["care", "difficult-pages", "therapy-chart", "grounding", "reauthoring"]
        ),
        thread(
            "elowen-refectory-experiments",
            "Vellum's Refectory Experiments",
            .seed,
            belief: 9,
            weight: 12,
            summary: "Food, movement, recovery, and body evidence become small experiments instead of verdicts.",
            tags: ["body", "fuel", "health", "vellum-chart", "experiment", "care"]
        ),
        thread(
            "weather-in-the-stacks",
            "Weather in the Stacks",
            .returning,
            belief: 10,
            weight: 13,
            summary: "Weather keeps tinting the Book without turning the reader into a data report.",
            tags: ["weather", "bleed", "atmosphere"]
        ),
        thread(
            "duskthorn-investigation",
            "The Duskthorn Question",
            .seed,
            belief: 9,
            weight: 12,
            summary: "The Academy's oldest elegance may be hiding a thorned bargain under the floorboards.",
            tags: ["duskthorn", "academy", "secret", "threshold"]
        ),
        thread(
            "margin-glass-letters",
            "Letters Through the Margin-Glass",
            .returning,
            belief: 11,
            weight: 15,
            summary: "Research notes, NPC letters, and impossible little reports keep arriving with the ink still warm.",
            tags: ["letters", "research", "archive", "marginalia"]
        ),
        thread(
            "nothing-thins-the-page",
            "The Nothing Thins the Page",
            .seed,
            belief: 7,
            weight: 10,
            summary: "Flatness, forgetting, and false impossibility press at the edges of the Book.",
            tags: ["nothing", "belief", "tension", "care"]
        ),
        thread(
            "home-vessel",
            "Home as Vessel",
            .seed,
            belief: 9,
            weight: 12,
            summary: "Rooms, mugs, desks, laundry, lamps, and domestic weather become containers for the day's magic.",
            tags: ["home", "objects", "care", "daily"]
        )
    ]

    private static let coreRelationships: [NarrativeRelationshipEdge] = [
        relationship(
            "book-authors-reader",
            source: "the-book",
            target: "ordinary-magic",
            kind: .authorship,
            warmth: 18,
            tension: 2,
            trust: 18,
            weight: 22,
            note: "The Book treats ordinary evidence as the reader's authorship, not as content to harvest.",
            tags: ["book", "belief", "ordinary", "daily"]
        ),
        relationship(
            "penny-files-book",
            source: "penny-blackletter",
            target: "the-book",
            kind: .stewardship,
            warmth: 16,
            tension: 4,
            trust: 14,
            weight: 16,
            note: "Penny keeps finding proof and trying to make it charming before it vanishes.",
            tags: ["marginalia", "photos", "letters", "book"]
        ),
        relationship(
            "inkrest-tends-body",
            source: "dr-inkrest",
            target: "body-page",
            kind: .care,
            warmth: 17,
            tension: 3,
            trust: 15,
            weight: 15,
            note: "Inkrest keeps hard pages seated near a lamp before asking them to speak.",
            tags: ["care", "body", "rest", "difficult-pages"]
        ),
        relationship(
            "inkrest-holds-difficult-pages",
            source: "dr-inkrest",
            target: "inkrest-difficult-pages",
            kind: .stewardship,
            warmth: 18,
            tension: 3,
            trust: 17,
            weight: 17,
            note: "Inkrest treats a hard feeling as a page, not a verdict.",
            tags: ["care", "difficult-pages", "therapy-chart", "grounding"]
        ),
        relationship(
            "vellum-tends-body-page",
            source: "dr-vellum",
            target: "body-page",
            kind: .care,
            warmth: 16,
            tension: 4,
            trust: 16,
            weight: 17,
            note: "Vellum turns body evidence into one small experiment with no shame attached.",
            tags: ["body", "health", "fuel", "vellum-chart", "care"]
        ),
        relationship(
            "vellum-runs-refectory-experiments",
            source: "dr-vellum",
            target: "elowen-refectory-experiments",
            kind: .stewardship,
            warmth: 15,
            tension: 5,
            trust: 15,
            weight: 15,
            note: "Vellum keeps experiments small enough that the reader can actually live with them.",
            tags: ["body", "fuel", "experiment", "vellum-chart"]
        ),
        relationship(
            "inkrest-vellum-compare-charts",
            source: "dr-inkrest",
            target: "dr-vellum",
            kind: .correspondence,
            warmth: 15,
            tension: 4,
            trust: 17,
            weight: 14,
            note: "Inkrest and Vellum compare charts only to make care more precise, never more intrusive.",
            tags: ["support-faculty", "care", "therapy-chart", "vellum-chart", "body"]
        ),
        relationship(
            "weather-bleeds-book",
            source: "weather-page",
            target: "the-book",
            kind: .realityBleed,
            warmth: 12,
            tension: 1,
            trust: 12,
            weight: 17,
            note: "Outer weather may tint the Book, but the source stays unnamed.",
            tags: ["weather", "bleed", "atmosphere", "book"]
        ),
        relationship(
            "body-negotiates-weather",
            source: "body-page",
            target: "weather-page",
            kind: .attention,
            warmth: 11,
            tension: 5,
            trust: 11,
            weight: 12,
            note: "Body and weather sometimes agree on gentleness before the reader does.",
            tags: ["body", "weather", "care", "bleed"]
        ),
        relationship(
            "thorne-tests-thresholds",
            source: "headmistress-thorne",
            target: "duskthorn-investigation",
            kind: .tension,
            warmth: 8,
            tension: 16,
            trust: 9,
            weight: 16,
            note: "Thorne lets thresholds test the reader, but never without leaving one lamp burning.",
            tags: ["duskthorn", "academy", "threshold", "secret"]
        ),
        relationship(
            "zara-guards-reader",
            source: "zara-finch",
            target: "ordinary-magic",
            kind: .companionship,
            warmth: 18,
            tension: 5,
            trust: 17,
            weight: 15,
            note: "Zara trusts ordinary proof more than dramatic declarations.",
            tags: ["trust", "friendship", "life", "ordinary"]
        ),
        relationship(
            "wicker-tests-belief",
            source: "wicker-eddies",
            target: "the-book",
            kind: .tension,
            warmth: 6,
            tension: 18,
            trust: 7,
            weight: 16,
            note: "Wicker attacks brittle belief so the real kind has to stand up.",
            tags: ["belief", "challenge", "tension", "nothing"]
        ),
        relationship(
            "gwendolyn-files-letters",
            source: "gwendolyn-mythwright",
            target: "margin-glass-letters",
            kind: .authorship,
            warmth: 14,
            tension: 3,
            trust: 15,
            weight: 14,
            note: "Gwendolyn sends impossible research as if wonder were a library debt.",
            tags: ["letters", "research", "archive", "impossible"]
        ),
        relationship(
            "lydia-keeps-home-vessel",
            source: "lydia-boggle",
            target: "home-vessel",
            kind: .stewardship,
            warmth: 17,
            tension: 4,
            trust: 15,
            weight: 13,
            note: "Lydia believes the room has already started helping before anyone notices.",
            tags: ["home", "tea", "objects", "care"]
        ),
        relationship(
            "soren-maps-thread",
            source: "soren-ng",
            target: "margin-glass-letters",
            kind: .attention,
            warmth: 10,
            tension: 5,
            trust: 14,
            weight: 13,
            note: "Soren leaves the map unfinished so the reader can become part of it.",
            tags: ["map", "pattern", "thread", "attention"]
        )
    ]

    private static func entity(
        _ id: String,
        _ name: String,
        _ kind: NarrativeEntityKind,
        belief: Int,
        weight: Int,
        chapter: String? = nil,
        unwrittenInterest: String? = nil,
        traits: [String],
        quirks: [String],
        faults: [String],
        beliefs: [String],
        goals: [String],
        tags: [String]
    ) -> NarrativeWorldEntity {
        NarrativeWorldEntity(
            id: id,
            packID: corePackID,
            name: name,
            kind: kind,
            belief: belief,
            narrativeWeight: weight,
            chapter: chapter,
            unwrittenInterest: unwrittenInterest,
            traits: traits,
            quirks: quirks,
            faults: faults,
            beliefs: beliefs,
            goals: goals,
            tags: tags
        )
    }

    private static func thread(
        _ id: String,
        _ title: String,
        _ phase: StoryThreadPhase,
        belief: Int,
        weight: Int,
        summary: String,
        tags: [String]
    ) -> NarrativeStoryThread {
        NarrativeStoryThread(
            id: id,
            packID: corePackID,
            title: title,
            phase: phase,
            belief: belief,
            narrativeWeight: weight,
            summary: summary,
            tags: tags
        )
    }

    private static func relationship(
        _ id: String,
        source: String,
        target: String,
        kind: NarrativeRelationshipKind,
        warmth: Int,
        tension: Int,
        trust: Int,
        weight: Int,
        note: String,
        tags: [String]
    ) -> NarrativeRelationshipEdge {
        NarrativeRelationshipEdge(
            id: id,
            packID: corePackID,
            sourceEntityID: source,
            targetEntityID: target,
            kind: kind,
            warmth: warmth,
            tension: tension,
            trust: trust,
            narrativeWeight: weight,
            note: note,
            tags: tags
        )
    }
}

enum SupportFacultyPackRegistry {
    static let corePackID = "core-support-faculty"

    static let bundledPacks: [SupportFacultyPack] = [
        SupportFacultyPack(
            id: corePackID,
            displayName: "Core Support Faculty Pack",
            version: "0.1",
            author: "The Book",
            availability: .bundledFree,
            charts: coreCharts
        )
    ]

    static var enabledPacks: [SupportFacultyPack] {
        bundledPacks.filter { $0.availability != .locked }
    }

    static var charts: [SupportFacultyChart] {
        enabledPacks.flatMap(\.charts)
    }

    static func chart(id: String) -> SupportFacultyChart? {
        charts.first { $0.id == id }
    }

    static func charts(for entityIDs: [String]) -> [SupportFacultyChart] {
        let ids = Set(entityIDs)
        return charts.filter { ids.contains($0.facultyEntityID) }
    }

    static func charts(matching tags: Set<String>) -> [SupportFacultyChart] {
        charts
            .map { chart in
                let overlap = tags.intersection(Set(chart.tags)).count
                return (chart, overlap)
            }
            .filter { $0.1 > 0 }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.id < right.0.id
                }
                return left.1 > right.1
            }
            .map(\.0)
    }

    private static let coreCharts: [SupportFacultyChart] = [
        SupportFacultyChart(
            id: "inkrest-difficult-page-chart",
            packID: corePackID,
            kind: .difficultPage,
            facultyEntityID: "dr-inkrest",
            facultyName: "Dr. Selene Inkrest",
            pageTitle: "Difficult Page",
            roleTitle: "Academy Narrative Therapist",
            purpose: "Hold emotional difficulty through narrative therapy, grounding, and reauthoring without turning pain into plot fuel.",
            reads: [
                "therapy chart",
                "Vellum chart",
                "fuel and body context",
                "heartbeat and recent pages",
                "diary or daydream material when offered"
            ],
            allowedUses: [
                "externalize a problem without making it the person",
                "name one feeling or pressure gently",
                "offer grounding, parts language, ACT, or CBT as practical tools",
                "write a preferred-story sentence",
                "keep quiet company when words are too expensive"
            ],
            forbiddenUses: [
                "diagnosis",
                "forced catharsis",
                "trauma excavation without consent",
                "major plot escalation",
                "spooky ambience",
                "certainty about symbols"
            ],
            invitations: [
                "name the page",
                "sit with the feeling",
                "rewrite one sentence",
                "choose grounding",
                "let Inkrest wait with it"
            ],
            closureConditions: [
                "one feeling or problem is externalized",
                "one preferred-story sentence is written",
                "one grounding step is chosen",
                "nothing is saved unless it is useful"
            ],
            artifactTypes: [
                "Therapy Chart check-in",
                "Difficult Page note",
                "reauthoring note",
                "grounding card",
                "question for real therapy"
            ],
            safetyLine: "A feeling is not a verdict. A problem is not a person. The next hour is where the story can be revised.",
            tags: ["support-faculty", "inkrest", "difficult-pages", "therapy-chart", "grounding", "care", "reauthoring"]
        ),
        SupportFacultyChart(
            id: "vellum-body-marginalia-chart",
            packID: corePackID,
            kind: .bodyMarginalia,
            facultyEntityID: "dr-vellum",
            facultyName: "Dr. Elowen Vellum",
            pageTitle: "Body Marginalia Page",
            roleTitle: "Academy Longevity Physician",
            purpose: "Translate body, fuel, movement, recovery, and health signals into one useful daily experiment with no shame attached.",
            reads: [
                "fuel log",
                "HealthKit body signals",
                "sleep and recovery context",
                "blood pressure or labs when explicitly provided",
                "supplements and medication cautions when explicitly provided",
                "current longevity research only when requested"
            ],
            allowedUses: [
                "choose one body-support action",
                "review a small experiment",
                "log one data point",
                "turn missing data into uncertainty, not blame",
                "prepare a question for a doctor or pharmacist"
            ],
            forbiddenUses: [
                "food shame",
                "diagnosis",
                "prescription changes",
                "heroic protocols",
                "generic wellness copy",
                "treating missing data as certainty"
            ],
            invitations: [
                "choose one warm fuel action",
                "try a small movement experiment",
                "review rest without moralizing it",
                "ask a longevity question",
                "log one body clue"
            ],
            closureConditions: [
                "one BJ-sized action is named",
                "one experiment or metric is clarified",
                "one safety flag is preserved",
                "one doctor or pharmacist question is prepared when needed"
            ],
            artifactTypes: [
                "Vellum chart update",
                "Body Marginalia note",
                "fuel observation",
                "body experiment record",
                "doctor or pharmacist question"
            ],
            safetyLine: "The body is evidence, not an accusation. Useful beats heroic.",
            tags: ["support-faculty", "vellum", "body", "fuel", "health", "vellum-chart", "longevity", "care", "experiment"]
        )
    ]
}

enum StoryScenePacketBuilder {
    static func packet(for day: BookDay, inputs: BookSourceInputs, now: Date = Date()) -> StoryScenePacket {
        let tags = contextTags(for: day, inputs: inputs, now: now)
        let selectedEntities = rankedEntities(tags: tags, inputs: inputs, limit: 3)
        let selectedThreads = rankedThreads(tags: tags, inputs: inputs, limit: 2)
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
        let realSignals = realSignals(for: day, inputs: inputs)
        let relationships = relationshipPressures(
            entities: selectedEntities,
            threads: selectedThreads,
            selectedRelationships: selectedRelationships,
            day: day,
            inputs: inputs
        )
        let title = primaryThread.map { "Story Page: \($0.title)" } ?? "Story Page"
        let intent = directorIntent(primaryThread: primaryThread, primaryEntity: primaryEntity, tags: tags)

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
            choices: choices(primaryThread: primaryThread, primaryEntity: primaryEntity)
        )
    }

    private static func rankedEntities(tags: Set<String>, inputs: BookSourceInputs, limit: Int) -> [NarrativeWorldEntity] {
        NarrativePackRegistry.entities
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
        limit: Int
    ) -> [NarrativeEntityMemory] {
        let entityIDs = Set(entities.map(\.id))
        return (inputs.narrative?.entityMemories ?? [])
            .filter { entityIDs.contains($0.entityID) }
            .sorted { left, right in
                if left.narrativeWeight == right.narrativeWeight {
                    return left.createdAt > right.createdAt
                }
                return left.narrativeWeight > right.narrativeWeight
            }
            .prefix(limit)
            .map(\.self)
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

enum GossipSimulationActionKind: String, Codable, Equatable, CaseIterable {
    case takeAction
    case investBelief
    case attackBelief

    var title: String {
        switch self {
        case .takeAction:
            return "acted"
        case .investBelief:
            return "invested Belief"
        case .attackBelief:
            return "tested Belief"
        }
    }
}

struct GossipSimulationTurn: Codable, Equatable {
    var id: String
    var actorID: String
    var actorName: String
    var threadID: String
    var threadTitle: String
    var actionKind: GossipSimulationActionKind
    var overheardLine: String
    var visibleTrace: String
    var hiddenEffect: String
    var consequenceLines: [String]
    var tags: [String]
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
                    "hiddenEffect": turns.map(\.hiddenEffect).joined(separator: " | "),
                    "consequences": turns.flatMap(\.consequenceLines).joined(separator: " | "),
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
        let actionKind = actionKind(for: actor, thread: thread, tags: tags, seed: seed)
        let trace = visibleTrace(actor: actor, thread: thread, actionKind: actionKind, tags: tags, seed: seed)
        let overheard = overheardLine(actor: actor, thread: thread, actionKind: actionKind, seed: seed)
        let consequences = consequenceLines(actor: actor, thread: thread, actionKind: actionKind)
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
            tags: turnTags
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
        NarrativePackRegistry.entities
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

    private static func visibleTrace(
        actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind,
        tags: Set<String>,
        seed: Int
    ) -> String {
        let detail: String
        if let interest = actor.unwrittenInterest, seed % 2 == 0 {
            detail = "Its unwritten interest was visible in the ink: \(interest)"
        } else if let goal = actor.goals.first {
            detail = "The goal under it was plain enough for the Book to file: \(goal)"
        } else {
            detail = "No one called it important. The margins disagreed."
        }

        switch actionKind {
        case .takeAction:
            return "\(actor.name) made a small move inside \(thread.title). \(detail)"
        case .investBelief:
            return "\(actor.name) tucked one point of Belief into \(thread.title), where it warmed the thread instead of explaining itself. \(detail)"
        case .attackBelief:
            return "\(actor.name) worried at a brittle edge of \(thread.title), testing whether the thread was attention or only habit. \(detail)"
        }
    }

    private static func overheardLine(
        actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind,
        seed: Int
    ) -> String {
        let verbs: [GossipSimulationActionKind: [String]] = [
            .takeAction: ["left a trace in", "nudged", "quietly rearranged"],
            .investBelief: ["fed a lamp inside", "paid attention into", "warmed"],
            .attackBelief: ["tested the edge of", "picked at the lock of", "asked a sharp question of"]
        ]
        let options = verbs[actionKind] ?? ["stirred"]
        let verb = options[stableIndex(for: "\(actor.id)-\(thread.id)-\(seed)-verb", count: options.count)]
        return "Overheard in the stacks: \(actor.name) \(verb) \(thread.title)."
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

    private static func consequenceLines(
        actor: NarrativeWorldEntity,
        thread: NarrativeStoryThread,
        actionKind: GossipSimulationActionKind
    ) -> [String] {
        switch actionKind {
        case .takeAction:
            return [
                "\(actor.name) left a fresh memory in the margins.",
                "\(thread.title) remains available for a future Story Page."
            ]
        case .investBelief:
            return [
                "\(actor.name) spent one quiet Belief.",
                "\(thread.title) grew warmer by one line."
            ]
        case .attackBelief:
            return [
                "\(actor.name) pressed on a weak place in the thread.",
                "\(thread.title) gained tension, not certainty."
            ]
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

enum NarrativeEventResolver {
    static func events(forKept page: BookPage) -> [NarrativeEvent] {
        var events = [event(forKept: page)]
        guard page.type == .narrativeOS else {
            return events
        }

        let choices = storyChoiceSelections(in: page)
        events.append(contentsOf: choices.enumerated().map { offset, choice in
            event(forStoryChoice: choice, page: page, offset: offset)
        })
        return events
    }

    static func event(forKept page: BookPage) -> NarrativeEvent {
        if page.type == .gossip {
            return event(forGossipPage: page)
        }
        let tags = normalizedTags(for: page)
        let effect = effect(for: page.type, tags: tags)
        let summary = summary(for: page, effect: effect)
        return NarrativeEvent(
            id: "narrative-event-\(page.id)",
            kind: page.userInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .pageKept : .pageAnswered,
            sourcePageType: page.type,
            sourcePageID: page.id,
            createdAt: page.createdAt,
            summary: summary,
            tags: Array(tags).sorted(),
            effect: effect
        )
    }

    private static func event(forGossipPage page: BookPage) -> NarrativeEvent {
        let tags = normalizedTags(for: page).union(["gossip", "simulation"])
        let actorIDs = page.tags
            .filter { $0.hasPrefix("actor:") }
            .map { $0.replacingOccurrences(of: "actor:", with: "") }
        let threadIDs = page.tags
            .filter { $0.hasPrefix("thread:") }
            .map { $0.replacingOccurrences(of: "thread:", with: "") }
        let actionKinds = page.tags
            .filter { $0.hasPrefix("action:") }
            .map { $0.replacingOccurrences(of: "action:", with: "") }
        let includesAttack = actionKinds.contains("attackBelief")

        var entityDeltas: [String: Int] = ["the-book": 1]
        var threadDeltas: [String: Int] = ["ordinary-magic": 1]
        let relationshipDeltas: [String: Int] = ["book-authors-reader": 1]

        for actorID in Set(actorIDs) {
            entityDeltas[actorID, default: 0] += includesAttack ? 1 : 2
        }
        for threadID in Set(threadIDs) {
            threadDeltas[threadID, default: 0] += includesAttack ? 1 : 2
        }

        let createdHint = includesAttack
            ? "A thread may return with tension where certainty used to sit."
            : "A small offscreen action can become a future callback."

        return NarrativeEvent(
            id: "narrative-gossip-\(page.id)",
            kind: .simulationTurn,
            sourcePageType: .gossip,
            sourcePageID: page.id,
            createdAt: page.createdAt,
            summary: page.userInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                ? "A Gossip Page was kept."
                : clippedSummary(page.userInput, maxLength: 180),
            tags: Array(tags).sorted(),
            effect: NarrativeEventEffect(
                beliefDelta: 1,
                entityWeightDeltas: entityDeltas,
                threadWeightDeltas: threadDeltas,
                relationshipWeightDeltas: relationshipDeltas,
                createdEntityHint: createdHint
            )
        )
    }

    private static func clippedSummary(_ text: String, maxLength: Int) -> String {
        let normalized = text
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard normalized.count > maxLength else { return normalized }
        let end = normalized.index(normalized.startIndex, offsetBy: maxLength)
        return normalized[..<end].trimmingCharacters(in: .whitespacesAndNewlines) + "..."
    }

    static func event(for choice: StorySceneChoice, packet: StoryScenePacket, at date: Date = Date()) -> NarrativeEvent {
        NarrativeEvent(
            id: "narrative-choice-\(packet.id)-\(choice.id)",
            kind: .choiceSelected,
            sourcePageType: .narrativeOS,
            sourcePageID: packet.id,
            createdAt: date,
            summary: "\(choice.role.title): \(choice.hiddenEffect)",
            tags: [choice.role.rawValue, packet.packID],
            effect: NarrativeEventEffect(
                beliefDelta: choice.beliefDelta,
                entityWeightDeltas: Dictionary(uniqueKeysWithValues: choice.targetEntityIDs.map { ($0, 1) }),
                threadWeightDeltas: Dictionary(uniqueKeysWithValues: choice.targetThreadIDs.map { ($0, 1) }),
                relationshipWeightDeltas: relationshipDeltas(for: choice, packet: packet),
                createdEntityHint: choice.role == .surprise ? "A related motif may step out of the margins." : nil
            )
        )
    }

    private static func event(forStoryChoice choice: StoryChoiceSelection, page: BookPage, offset: Int) -> NarrativeEvent {
        let effect = effect(forStoryChoice: choice, page: page)
        return NarrativeEvent(
            id: "narrative-choice-\(page.id)-\(offset + 1)-\(choice.id)",
            kind: .choiceSelected,
            sourcePageType: .narrativeOS,
            sourcePageID: page.id,
            createdAt: page.createdAt.addingTimeInterval(Double(offset + 1)),
            summary: "\(choice.title): \(choice.summary)",
            tags: Array(normalizedTags(for: page).union(["choice:\(choice.id)", choice.id])).sorted(),
            effect: effect
        )
    }

    private static func normalizedTags(for page: BookPage) -> Set<String> {
        var tags = Set(page.tags.map { $0.lowercased() })
        let searchable = "\(page.promptText) \(page.userInput)".lowercased()
        if searchable.contains("weather") || searchable.contains("sky") || searchable.contains("rain") || searchable.contains("sun") {
            tags.formUnion(["weather", "bleed", "atmosphere"])
        }
        if searchable.contains("body") || searchable.contains("tired") || searchable.contains("rest") || searchable.contains("fuel") {
            tags.formUnion(["body", "care", "rest"])
        }
        if searchable.contains("music") || searchable.contains("spotify") || searchable.contains("headphone") {
            tags.formUnion(["music", "shelter"])
        }
        if searchable.contains("photo") || page.type == .illuminatedPhoto {
            tags.formUnion(["photos", "marginalia"])
        }
        return tags
    }

    private struct StoryChoiceSelection {
        var id: String
        var title: String
        var summary: String
    }

    private static func storyChoiceSelections(in page: BookPage) -> [StoryChoiceSelection] {
        let searchable = page.userInput.lowercased()
        let selections: [(String, String, String)] = [
            ("sliceoflife", "Slice of Life", "The ordinary detail gained narrative weight."),
            ("progressarc", "Progress Arc", "The active thread moved one step forward."),
            ("surprise", "Something Surprising", "A related side door opened in the margins.")
        ]

        var found: [StoryChoiceSelection] = []
        for (id, title, summary) in selections {
            let tagCount = page.tags.filter { $0.lowercased() == "choice:\(id)" }.count
            let textCount = searchable.components(separatedBy: "chosen path: \(title.lowercased())").count - 1
            let count = max(tagCount, textCount)
            for _ in 0..<count {
                found.append(StoryChoiceSelection(id: id, title: title, summary: summary))
            }
        }

        return found
    }

    private static func effect(for type: BookPageType, tags: Set<String>) -> NarrativeEventEffect {
        var entityDeltas: [String: Int] = ["the-book": 1]
        var threadDeltas: [String: Int] = ["ordinary-magic": 1]
        var relationshipDeltas: [String: Int] = ["book-authors-reader": 1]
        var createdHint: String?

        switch type {
        case .weather:
            entityDeltas["weather-page", default: 0] += 2
            threadDeltas["weather-in-the-stacks", default: 0] += 2
            relationshipDeltas["weather-bleeds-book", default: 0] += 2
        case .body, .rest:
            entityDeltas["body-page", default: 0] += 2
            entityDeltas["dr-inkrest", default: 0] += 1
            threadDeltas["body-learns-trust", default: 0] += 2
            relationshipDeltas["inkrest-tends-body", default: 0] += 2
        case .fuel:
            entityDeltas["body-page", default: 0] += 2
            entityDeltas["dr-vellum", default: 0] += 2
            threadDeltas["body-learns-trust", default: 0] += 2
            relationshipDeltas["vellum-tends-body-page", default: 0] += 2
        case .supportGuild:
            entityDeltas["dr-vellum", default: 0] += 2
            entityDeltas["dr-inkrest", default: 0] += 2
            threadDeltas["elowen-refectory-experiments", default: 0] += 2
            threadDeltas["inkrest-difficult-pages", default: 0] += 2
            relationshipDeltas["inkrest-vellum-compare-charts", default: 0] += 3
        case .facultyResearch:
            if tags.contains("faculty:dr-vellum") {
                entityDeltas["dr-vellum", default: 0] += 2
                threadDeltas["elowen-refectory-experiments", default: 0] += 2
                relationshipDeltas["vellum-runs-refectory-experiments", default: 0] += 2
            }
            if tags.contains("faculty:dr-inkrest") {
                entityDeltas["dr-inkrest", default: 0] += 2
                threadDeltas["inkrest-difficult-pages", default: 0] += 2
                relationshipDeltas["inkrest-holds-difficult-pages", default: 0] += 2
            }
        case .souvenir, .quip, .wonderCompass, .illustration:
            threadDeltas["ordinary-magic", default: 0] += 2
            relationshipDeltas["book-authors-reader", default: 0] += 1
        case .illuminatedPhoto:
            entityDeltas["penny-blackletter", default: 0] += 2
            relationshipDeltas["penny-files-book", default: 0] += 2
            createdHint = "A visible detail in the image can become a recurring talisman."
        case .aboutYou:
            entityDeltas["the-book", default: 0] += 2
            relationshipDeltas["book-authors-reader", default: 0] += 2
        case .narrativeOS:
            threadDeltas["ordinary-magic", default: 0] += 1
            if tags.contains("choice:sliceoflife") {
                entityDeltas["the-book", default: 0] += 2
                relationshipDeltas["book-authors-reader", default: 0] += 1
            }
            if tags.contains("choice:progressarc") {
                threadDeltas["ordinary-magic", default: 0] += 2
                relationshipDeltas["book-authors-reader", default: 0] += 1
            }
            if tags.contains("choice:surprise") {
                entityDeltas["penny-blackletter", default: 0] += 1
                threadDeltas["ordinary-magic", default: 0] += 1
                createdHint = "A surprising but related detail can become a future motif."
            }
        case .gossip:
            entityDeltas["the-book", default: 0] += 1
            threadDeltas["ordinary-magic", default: 0] += 1
            createdHint = "An offscreen action can become a future callback."
        case .mood:
            entityDeltas["body-page", default: 0] += tags.contains("weather") ? 0 : 1
            threadDeltas["body-learns-trust", default: 0] += 1
        case .location, .lore, .patreon, .bookOfYou:
            break
        }

        if tags.contains("music") {
            threadDeltas["music-as-shelter", default: 0] += 2
        }
        if tags.contains("weather") {
            entityDeltas["weather-page", default: 0] += 1
            threadDeltas["weather-in-the-stacks", default: 0] += 1
        }
        if tags.contains("body") || tags.contains("rest") || tags.contains("care") {
            entityDeltas["body-page", default: 0] += 1
            threadDeltas["body-learns-trust", default: 0] += 1
        }

        return NarrativeEventEffect(
            beliefDelta: 1,
            entityWeightDeltas: entityDeltas,
            threadWeightDeltas: threadDeltas,
            relationshipWeightDeltas: relationshipDeltas,
            createdEntityHint: createdHint
        )
    }

    private static func effect(forStoryChoice choice: StoryChoiceSelection, page: BookPage) -> NarrativeEventEffect {
        var entityDeltas: [String: Int] = ["the-book": 1]
        var threadDeltas: [String: Int] = ["ordinary-magic": 1]
        var relationshipDeltas: [String: Int] = ["book-authors-reader": 1]
        var createdHint: String?

        switch choice.id {
        case "sliceoflife":
            entityDeltas["the-book", default: 0] += 2
            relationshipDeltas["book-authors-reader", default: 0] += 1
        case "progressarc":
            threadDeltas["ordinary-magic", default: 0] += 3
            relationshipDeltas["book-authors-reader", default: 0] += 1
        case "surprise":
            entityDeltas["penny-blackletter", default: 0] += 1
            threadDeltas["margin-glass-letters", default: 0] += 1
            createdHint = "A surprising but related detail can become a future motif."
        default:
            break
        }

        let tags = normalizedTags(for: page)
        if tags.contains("music") {
            threadDeltas["music-as-shelter", default: 0] += 1
        }
        if tags.contains("weather") {
            entityDeltas["weather-page", default: 0] += 1
            threadDeltas["weather-in-the-stacks", default: 0] += 1
        }
        if tags.contains("body") || tags.contains("rest") || tags.contains("care") {
            entityDeltas["body-page", default: 0] += 1
            threadDeltas["body-learns-trust", default: 0] += 1
        }
        if tags.contains("letters") || tags.contains("research") {
            threadDeltas["margin-glass-letters", default: 0] += 1
            relationshipDeltas["gwendolyn-files-letters", default: 0] += 1
        }

        return NarrativeEventEffect(
            beliefDelta: 1,
            entityWeightDeltas: entityDeltas,
            threadWeightDeltas: threadDeltas,
            relationshipWeightDeltas: relationshipDeltas,
            createdEntityHint: createdHint
        )
    }

    private static func relationshipDeltas(for choice: StorySceneChoice, packet: StoryScenePacket) -> [String: Int] {
        var deltas: [String: Int] = [:]
        let targets = Set(choice.targetEntityIDs + choice.targetThreadIDs)
        for relationship in packet.selectedRelationships where targets.contains(relationship.sourceEntityID) || targets.contains(relationship.targetEntityID) {
            deltas[relationship.id, default: 0] += 1
        }
        if deltas.isEmpty, let first = packet.selectedRelationships.first {
            deltas[first.id] = 1
        }
        return deltas
    }

    private static func summary(for page: BookPage, effect: NarrativeEventEffect) -> String {
        let pageName = page.type.title
        let threadNames = effect.threadWeightDeltas.keys.sorted().joined(separator: ", ")
        guard !threadNames.isEmpty else {
            return "\(pageName) became a kept artifact in the Book."
        }
        return "\(pageName) became a kept artifact and tugged \(threadNames)."
    }
}

struct LabyrinthIllustrationPlate: Identifiable, Equatable {
    var id: String
    var assetName: String
    var title: String
    var caption: String
    var note: String
    var tags: [String]
    var characterID: String? = nil
}

struct CharacterIllustrationProfile: Identifiable, Codable, Equatable {
    var id: String
    var characterName: String
    var slug: String
    var status: String
    var chapter: String?
    var core: String
    var signature: String
    var palette: String
    var silhouette: String
    var continuity: String
    var avoid: String
    var assetName: String?
    var intendedAssetName: String
    var prompt: String
    var negativePrompt: String
    var marginalia: [String]
    var tags: [String]

    var hasBundledAsset: Bool {
        assetName?.isEmpty == false
    }
}

enum QuipPackAvailability: String, Codable, Equatable {
    case bundledFree
    case patron
    case paid
    case userImported
    case locked
}

struct QuipPack: Identifiable, Codable, Equatable {
    var id: String
    var displayName: String
    var version: String
    var author: String
    var availability: QuipPackAvailability
    var quips: [QuipEntry]
}

struct QuipEntry: Identifiable, Codable, Equatable {
    var id: String
    var text: String
    var title: String
    var tags: [String]
    var packID: String
    var weight: Int
}

enum ContentPackAvailability: String, Codable, Equatable {
    case bundledFree
    case patron
    case paid
    case userImported
    case locked
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

enum SelfFactSensitivity: String, Codable, Equatable, CaseIterable {
    case identity
    case comfort
    case delight
    case values
    case story
}

enum SelfFactUsePermission: String, Codable, Equatable, CaseIterable {
    case privateContext
    case quoteAllowed
    case storyOnly
    case doNotUse
}

struct SelfFact: Identifiable, Codable, Equatable {
    var id: String
    var questionID: String
    var question: String
    var answer: String
    var bookTranslation: String
    var sensitivity: SelfFactSensitivity
    var usePermission: SelfFactUsePermission
    var tags: [String]
    var createdAt: Date
    var updatedAt: Date
}

struct AboutYouQuestion: Identifiable, Codable, Equatable {
    var id: String
    var packID: String
    var prompt: String
    var detail: String
    var placeholder: String
    var sensitivity: SelfFactSensitivity
    var defaultUsePermission: SelfFactUsePermission
    var tags: [String]
    var priority: Int
}

struct SelfKnowledgePack: Identifiable, Codable, Equatable {
    var id: String
    var displayName: String
    var version: String
    var author: String
    var availability: ContentPackAvailability
    var questions: [AboutYouQuestion]
}

enum SelfKnowledgePackRegistry {
    static let corePackID = "core-self-knowledge"
    static let maxAboutYouFactsPerDay = 3
    static let minimumHoursBetweenAboutYouFacts = 3
    static let maxInterestFacts = 7

    static let bundledPacks: [SelfKnowledgePack] = [
        SelfKnowledgePack(
            id: corePackID,
            displayName: "Core Self-Knowledge Pack",
            version: "1.0",
            author: "The Book",
            availability: .bundledFree,
            questions: coreQuestions
        )
    ]

    static var enabledPacks: [SelfKnowledgePack] {
        bundledPacks.filter { $0.availability != .locked }
    }

    static var questions: [AboutYouQuestion] {
        enabledPacks.flatMap(\.questions)
    }

    static func question(id: String) -> AboutYouQuestion? {
        questions.first { $0.id == id }
    }

    static func packName(for packID: String) -> String {
        enabledPacks.first { $0.id == packID }?.displayName ?? "the shelf"
    }

    static func nextQuestion(knownFacts: [SelfFact], day: BookDay, now: Date) -> AboutYouQuestion? {
        let answered = Set(knownFacts.map(\.questionID))
        let answeredInterestCount = knownFacts.filter { $0.questionID.hasPrefix("interest-") }.count
        let available = questions.filter { question in
            if question.id.hasPrefix("interest-") {
                guard answeredInterestCount < maxInterestFacts else { return false }
                if question.id == "interest-01" {
                    return !answered.contains(question.id)
                }
                let expectedID = String(format: "interest-%02d", answeredInterestCount + 1)
                return question.id == expectedID && !answered.contains(question.id)
            }
            return !answered.contains(question.id)
        }
        guard !available.isEmpty else { return nil }
        let slot = SurfaceCadence.slotID(for: now, hours: 12)
        let seed = abs("\(day.id)-about-you-\(slot)".hashValue)
        return available.sorted { left, right in
            let leftScore = left.priority * 1000 + abs((seed ^ left.id.hashValue ^ left.packID.hashValue) % 997)
            let rightScore = right.priority * 1000 + abs((seed ^ right.id.hashValue ^ right.packID.hashValue) % 997)
            return leftScore > rightScore
        }.first
    }

    static func translation(for question: AboutYouQuestion, answer: String) -> String {
        let trimmed = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        switch question.sensitivity {
        case .identity:
            return "The Book may call you \(trimmed) when the page needs to remember who is holding it."
        case .comfort:
            return "The Book will treat this as a signal for comfort, shelter, and the shape of gentleness."
        case .delight:
            if question.tags.contains("interest") {
                return "The Book will keep this interest near the desk, ready to tint scenes, quips, and invitations."
            }
            return "The Book will let this tint future pages when wonder needs a familiar spark."
        case .values:
            return "The Book will give this belief weight when Story Pages choose what matters."
        case .story:
            return "The Book will carry this as story-shape, not a box: a pattern to notice, not a verdict."
        }
    }

    private static let coreQuestions: [AboutYouQuestion] = [
        question("called", "What do you like to be called?", "The Book would rather learn your name than guess at you.", "A name, nickname, or whatever feels like yours.", .identity, .quoteAllowed, ["name", "identity"], 100),
        question("home-place", "Where do you call home?", "A place can be true without being precise.", "A town, coast, room, region, or kind of place.", .comfort, .privateContext, ["home", "place"], 88),
        question("home-meaning", "What does home mean to you?", "Not the address. The feeling the Book should recognize.", "Safety, noise, chosen people, a porch light...", .comfort, .storyOnly, ["home", "meaning"], 84),
        question("favorite-color", "What color keeps finding you?", "The Book can tint future pages with a little more you in them.", "Blue, moss green, marigold, storm gray...", .delight, .privateContext, ["color", "delight"], 78),
        question("interest-01", "What's an interest of yours?", "The Book wants to know what lights your shelves from the inside.", "Sailing, cooking, weird history, cozy games, old maps...", .delight, .privateContext, ["interest", "delight", "story-seed"], 77),
        question("interest-02", "What's another interest of yours?", "Interests make excellent doors. The Book is collecting keys slowly.", "A hobby, subject, fandom, craft, place, creature, question...", .delight, .privateContext, ["interest", "delight", "story-seed"], 65),
        question("interest-03", "What's another interest of yours?", "A second shelf has opened. Put one bright thing on it.", "Something you read about, make, watch, collect, or chase...", .delight, .privateContext, ["interest", "delight", "story-seed"], 64),
        question("interest-04", "What's another interest of yours?", "The Book is learning what kinds of doors you notice first.", "A world, practice, problem, texture, tool, era, mystery...", .delight, .privateContext, ["interest", "delight", "story-seed"], 63),
        question("interest-05", "What's another interest of yours?", "Some interests are lanterns. Some are secret staircases.", "Tiny, grand, serious, silly. All of them count.", .delight, .privateContext, ["interest", "delight", "story-seed"], 62),
        question("interest-06", "What's another interest of yours?", "The Book is nearly done stocking this shelf for now.", "A thing you could talk about for ten minutes too long...", .delight, .privateContext, ["interest", "delight", "story-seed"], 61),
        question("interest-07", "What's one last interest for this shelf?", "Seven is plenty. The Book can make a map from here.", "One more spark the Story Pages should know about.", .delight, .privateContext, ["interest", "delight", "story-seed"], 60),
        question("small-delight", "What small thing reliably delights you?", "A tiny delight is a strong lantern.", "A food, sound, texture, joke, place, creature...", .delight, .privateContext, ["delight", "wonder"], 76),
        question("rest-shape", "What does real rest look like for you?", "The Book should learn the difference between rest and merely stopping.", "Quiet, movement, sleep, music, being left alone...", .comfort, .privateContext, ["rest", "care"], 72),
        question("belief", "What do you believe in, even on tired days?", "One sturdy sentence for the shelf.", "Kindness, curiosity, making things, second chances...", .values, .storyOnly, ["values", "belief"], 68),
        question("protect", "What do you protect?", "The Story Page will need to know what has weight.", "People, time, wonder, honesty, softness, the work...", .values, .storyOnly, ["values", "protection"], 62),
        question("becoming", "What kind of person are you trying to become?", "Not as homework. As a north star.", "Braver, gentler, more alive, less hidden...", .values, .storyOnly, ["growth", "values"], 58),
        question("story-role", "What role do you usually play in a group?", "Every story field has patterns. This one can learn yours gently.", "Guide, comic relief, caretaker, scout, skeptic...", .story, .storyOnly, ["story", "role"], 52)
    ]

    private static func question(
        _ id: String,
        _ prompt: String,
        _ detail: String,
        _ placeholder: String,
        _ sensitivity: SelfFactSensitivity,
        _ permission: SelfFactUsePermission,
        _ tags: [String],
        _ priority: Int
    ) -> AboutYouQuestion {
        AboutYouQuestion(
            id: id,
            packID: corePackID,
            prompt: prompt,
            detail: detail,
            placeholder: placeholder,
            sensitivity: sensitivity,
            defaultUsePermission: permission,
            tags: tags,
            priority: priority
        )
    }
}

struct BookReferenceLibraryPayload: Codable, Equatable {
    var version: Int
    var wonderCompass: [ReferenceSnippet]
    var enchantifyLore: [ReferenceSnippet]
    var patreon: [ReferenceSnippet]?
    var characterIllustrations: [CharacterIllustrationProfile]

    enum CodingKeys: String, CodingKey {
        case version
        case wonderCompass
        case enchantifyLore
        case patreon
        case characterIllustrations
    }

    init(
        version: Int,
        wonderCompass: [ReferenceSnippet],
        enchantifyLore: [ReferenceSnippet],
        patreon: [ReferenceSnippet]?,
        characterIllustrations: [CharacterIllustrationProfile] = []
    ) {
        self.version = version
        self.wonderCompass = wonderCompass
        self.enchantifyLore = enchantifyLore
        self.patreon = patreon
        self.characterIllustrations = characterIllustrations
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        version = try container.decode(Int.self, forKey: .version)
        wonderCompass = try container.decode([ReferenceSnippet].self, forKey: .wonderCompass)
        enchantifyLore = try container.decode([ReferenceSnippet].self, forKey: .enchantifyLore)
        patreon = try container.decodeIfPresent([ReferenceSnippet].self, forKey: .patreon)
        characterIllustrations = try container.decodeIfPresent([CharacterIllustrationProfile].self, forKey: .characterIllustrations) ?? []
    }

    static let empty = BookReferenceLibraryPayload(version: 0, wonderCompass: [], enchantifyLore: [], patreon: [], characterIllustrations: [])
}

enum QuipPackRegistry {
    static let corePackID = "core-oddities"

    static let bundledPacks: [QuipPack] = [
        QuipPack(
            id: corePackID,
            displayName: "Core Oddities Pack",
            version: "1.0",
            author: "The Book",
            availability: .bundledFree,
            quips: coreQuips
        )
    ]

    static var enabledPacks: [QuipPack] {
        bundledPacks.filter { $0.availability != .locked }
    }

    static func quip(for day: BookDay, now: Date, tags: [String] = []) -> QuipEntry {
        let quips = enabledPacks.flatMap(\.quips)
        guard !quips.isEmpty else {
            return QuipEntry(id: "fallback", text: "The Book found a small bright thing and kept it.", title: "Filed Under Wonder", tags: ["wonder"], packID: corePackID, weight: 1)
        }
        let slot = SurfaceCadence.slotID(for: now, hours: 3)
        let seed = abs("\(day.id)-\(slot)-\(tags.joined(separator: ","))".hashValue)
        let tagSet = Set(tags.map { $0.lowercased() })
        let ranked = quips.enumerated().map { index, quip in
            let overlap = tagSet.intersection(Set(quip.tags.map { $0.lowercased() })).count
            let jitter = abs((seed &+ index * 1543).hashValue % 1000)
            return (quip, overlap * 20 + quip.weight * 3 + jitter)
        }
        return ranked.sorted { $0.1 > $1.1 }.first?.0 ?? quips[seed % quips.count]
    }

    private static let coreQuips: [QuipEntry] = [
        quip("tree-squirrel", "Squirrels are the part of the tree that runs.", "Whimsical Observation", ["nature", "creature", "tree"]),
        quip("tiny-sun", "A candle is a tiny sun with manners.", "Small Light", ["light", "home", "night"]),
        quip("fog-forgetting", "Fog is the weather forgetting where it put things.", "Weather Oddity", ["weather", "fog"]),
        quip("sky-handwriting", "Rain is the sky practicing handwriting.", "Weather Oddity", ["weather", "rain", "ink"]),
        quip("forest-thought", "A mushroom is a thought the forest had overnight.", "Forest Note", ["nature", "forest", "fungus"]),
        quip("library-forest", "A library is a forest that learned alphabetical order.", "Bookish Oddity", ["book", "library", "forest"]),
        quip("bookmark-job", "A bookmark is a tiny pause with a job.", "Bookish Oddity", ["book", "reading"]),
        quip("liquid-ghost", "Ink is a liquid ghost.", "Ink Note", ["ink", "writing"]),
        quip("field-remember", "Paper is a field that agreed to remember.", "Paper Note", ["paper", "memory", "writing"]),
        quip("book-breathing", "Margins are where books breathe.", "Bookish Oddity", ["book", "margin"]),
        quip("tiny-midnight", "An inkwell is a tiny midnight.", "Ink Note", ["ink", "night"]),
        quip("borrow-lantern", "Reading is borrowing someone else's lantern.", "Reading Note", ["book", "light"]),
        quip("recipe-spell", "A recipe is a spell that ends in dishes.", "Kitchen Spell", ["home", "food", "magic"]),
        quip("keys-doors", "Keys are tiny arguments with doors.", "Object Note", ["home", "door"]),
        quip("teacup-thought", "A teacup is a bathtub for a thought.", "Tea Note", ["home", "tea"]),
        quip("seed-summer", "A seed is a locked room full of summer.", "Botanical Note", ["nature", "garden"]),
        quip("roots-writing", "Roots are trees writing underground.", "Botanical Note", ["nature", "tree"]),
        quip("year-editing", "Autumn is the year editing itself.", "Seasonal Note", ["weather", "season"]),
        quip("portable-courage", "A lantern is portable courage.", "Small Light", ["light", "night"]),
        quip("private-museum", "A pocket is a tiny private museum.", "Object Note", ["ordinary", "memory"]),
        quip("manicule", "A manicule is the little pointing hand drawn in old book margins. A tiny medieval cursor.", "Bookish Oddity", ["book", "margin", "history"], weight: 2),
        quip("palimpsest", "A palimpsest is a reused page where older writing still ghosts through. A haunted notebook.", "Bookish Oddity", ["book", "history", "ghost"], weight: 2),
        quip("fore-edge", "Some old books hide paintings on their page edges, visible only when fanned.", "Bookish Oddity", ["book", "art", "hidden"], weight: 2),
        quip("lapis-sky", "Some manuscripts used blue made from lapis lazuli, once more expensive than gold. Imagine budgeting for sky.", "Bookish Oddity", ["book", "color", "history"], weight: 2),
        quip("book-leaf", "A leaf has two pages. A page has one face. Books are secretly botanical.", "Bookish Oddity", ["book", "botanical"], weight: 2),
        quip("serif-feet", "Serifs are tiny feet on letters. Sans serif letters go barefoot.", "Type Note", ["book", "letter", "type"]),
        quip("old-book-smell", "The smell of old books often comes from lignin breaking down. Time has a vanilla-adjacent perfume.", "Bookish Oddity", ["book", "smell", "time"], weight: 2),
        quip("petrichor", "Rain does not just fall. It wakes the smell of the earth.", "Science Oddity", ["weather", "rain", "earth"], weight: 2),
        quip("sea-stars", "Bioluminescence is the sea inventing stars under pressure.", "Science Oddity", ["sea", "light", "science"], weight: 2),
        quip("stardust", "You are not metaphorically stardust. You are chemically, literally stardust.", "Science Oddity", ["space", "body", "science"], weight: 2),
        quip("glacier-blue", "A glacier is time moving slowly enough to become a landscape.", "Science Oddity", ["ice", "time", "weather"]),
        quip("fungus-apple", "The visible mushroom is the apple. The forest underground is the tree.", "Science Oddity", ["forest", "fungus", "nature"]),
        quip("pearl-wound", "A pearl is a wound that learned polish.", "Science Oddity", ["sea", "shell"]),
        quip("octopus-curiosity", "An octopus is what happens when curiosity gets eight hands.", "Science Oddity", ["sea", "creature"]),
        quip("whale-cathedral", "A whale song is a cathedral built out of breath.", "Science Oddity", ["sea", "creature", "sound"]),
        quip("bird-map", "A bird migration is a map written inside a body.", "Science Oddity", ["sky", "bird", "map"]),
        quip("bee-cartography", "A bee dance is cartography with an abdomen.", "Science Oddity", ["bee", "map", "creature"]),
        quip("spider-poem", "A spiderweb is a trap, a house, and a poem under tension.", "Science Oddity", ["web", "creature"]),
        quip("rust-memory", "Rust is iron remembering it used to be in the ground.", "Whimsical Observation", ["ordinary", "earth"]),
        quip("road-question", "A road is a question the town keeps asking the horizon.", "Whimsical Observation", ["place", "walk"]),
        quip("roots-walk", "Roots are the tree refusing to admit it can't walk.", "Whimsical Observation", ["tree", "nature"]),
        quip("library-quiet", "A library is the only building designed to be quieter than the people inside it.", "Bookish Oddity", ["book", "library"]),
        quip("book-breath", "An unread book is the most patient object in any house.", "Bookish Oddity", ["book", "home"]),
        quip("photo-key", "A photograph doesn't hold the memory. You do. The photo is just where you left the key.", "Memory Note", ["memory", "photo"]),
        quip("novelty-save", "Novelty is just the save button.", "Memory Note", ["memory", "attention"])
    ]

    private static func quip(_ id: String, _ text: String, _ title: String, _ tags: [String], weight: Int = 1) -> QuipEntry {
        QuipEntry(id: id, text: text, title: title, tags: tags, packID: corePackID, weight: weight)
    }
}

enum LorePackRegistry {
    static let corePackID = "core-labyrinth-lore"

    static func bundledPacks(coreSnippets: [ReferenceSnippet]) -> [LorePack] {
        [
            LorePack(
                id: corePackID,
                displayName: "Core Labyrinth Lore Pack",
                version: "1.0",
                author: "The Book",
                availability: .bundledFree,
                themes: ["academy", "characters", "classes", "history", "letters", "rooms"],
                snippets: coreSnippets
            )
        ]
    }

    static func enabledPacks(coreSnippets: [ReferenceSnippet]) -> [LorePack] {
        bundledPacks(coreSnippets: coreSnippets).filter { $0.availability != .locked }
    }

    static func snippets(coreSnippets: [ReferenceSnippet]) -> [ReferenceSnippet] {
        enabledPacks(coreSnippets: coreSnippets).flatMap(\.snippets)
    }
}

enum BookReferenceCatalog {
    static var wonderCompass: [ReferenceSnippet] {
        bundledLibrary.wonderCompass.isEmpty ? fallbackWonderCompass : bundledLibrary.wonderCompass
    }

    static var enchantifyLore: [ReferenceSnippet] {
        LorePackRegistry.snippets(
            coreSnippets: bundledLibrary.enchantifyLore.isEmpty ? fallbackEnchantifyLore : bundledLibrary.enchantifyLore
        )
    }

    static var lorePacks: [LorePack] {
        LorePackRegistry.enabledPacks(
            coreSnippets: bundledLibrary.enchantifyLore.isEmpty ? fallbackEnchantifyLore : bundledLibrary.enchantifyLore
        )
    }

    static var patreon: [ReferenceSnippet] {
        let snippets = bundledLibrary.patreon ?? []
        return snippets.isEmpty ? fallbackPatreon : snippets
    }

    static var characterIllustrations: [CharacterIllustrationProfile] {
        let profiles = bundledLibrary.characterIllustrations
        return profiles.isEmpty ? fallbackCharacterIllustrations : profiles
    }

    static var labyrinthIllustrations: [LabyrinthIllustrationPlate] {
        characterIllustrationPlates
    }

    static let bundledCharacterIllustrationAssetNames: Set<String> = [
        "LabyrinthCharacterDrSeleneInkrest",
        "LabyrinthCharacterHeadmistressSeraphinaThorne",
        "LabyrinthCharacterOrionBlackthorn",
        "LabyrinthCharacterPennyBlackletter",
        "LabyrinthCharacterSerenityBrown",
        "LabyrinthCharacterWickerEddies",
        "LabyrinthCharacterZaraFinch"
    ]

    private static var characterIllustrationPlates: [LabyrinthIllustrationPlate] {
        characterIllustrations.compactMap { profile in
            let assetName = profile.assetName?.isEmpty == false ? profile.assetName ?? profile.intendedAssetName : profile.intendedAssetName
            guard bundledCharacterIllustrationAssetNames.contains(assetName) else {
                return nil
            }
            return LabyrinthIllustrationPlate(
                id: "character-\(profile.slug)",
                assetName: assetName,
                title: profile.characterName,
                caption: profile.core,
                note: "Character dossier illustration. Signature: \(profile.signature). Marginalia: \(profile.marginalia.joined(separator: " | ")).",
                tags: Array((["illustration", "character", profile.slug] + profile.tags).prefix(8)),
                characterID: profile.id
            )
        }
    }

    private static let fallbackCharacterIllustrations = [
        CharacterIllustrationProfile(
            id: "headmistress-seraphina-thorne",
            characterName: "Headmistress Seraphina Thorne",
            slug: "headmistress-seraphina-thorne",
            status: "canonical",
            chapter: "Duskthorn",
            core: "Leads the Academy; sees the Unwritten; ageless literary-elf face; star-cold eyes; hair pinned like a dark crown.",
            signature: "an antique star-dark key and a crownlike hairpin",
            palette: "ink black, old silver, star-gold",
            silhouette: "regal stillness; one hand resting on an antique key",
            continuity: "Preserve these identifiers across images; clothes, pose, age-light, and mood may vary with the scene.",
            avoid: "generic anime face, room-first composition, inconsistent signature object, polished digital fantasy portrait",
            assetName: "LabyrinthCharacterHeadmistressSeraphinaThorne",
            intendedAssetName: "LabyrinthCharacterHeadmistressSeraphinaThorne",
            prompt: "Create an Enchantify Academy character dossier illustration in sparse graphite and ink, watercolor washes, jewel-color accents, and character-specific parchment marginalia.",
            negativePrompt: "Avoid generic fantasy pinup, glossy anime, polished digital fantasy portrait, and inconsistent signature object.",
            marginalia: [
                "file tab labeled Headmistress Seraphina Thorne",
                "signature evidence: an antique star-dark key and a crownlike hairpin",
                "jewel-color swatches: ink black, old silver, star-gold"
            ],
            tags: ["canonical", "character", "duskthorn", "illustration"]
        )
    ]

    private static let bundledLibrary: BookReferenceLibraryPayload = {
        guard let url = Bundle.main.url(forResource: "BookReferenceLibrary", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let payload = try? JSONDecoder().decode(BookReferenceLibraryPayload.self, from: data) else {
            return .empty
        }
        return payload
    }()

    static let fallbackWonderCompass: [ReferenceSnippet] = [
        ReferenceSnippet(
            id: "wonder-compass-core-loop",
            sourceID: "wonder-compass",
            title: "The Wonder Compass",
            prompt: "Try one small Compass loop.",
            body: "Notice a spark. Embark across one tiny threshold. Sense with a playful mission. Write one sentence before the moment blurs. Rest stays at the center.",
            tags: ["wonder-compass", "practice", "notice", "embark", "sense", "write", "rest"]
        ),
        ReferenceSnippet(
            id: "wonder-compass-one-sentence",
            sourceID: "wonder-compass",
            title: "One-Sentence Souvenir",
            prompt: "Keep one bright particular.",
            body: "A single specific sentence can hold the shape of an entire day. Capture a color, sound, texture, image, or tiny mercy before your brain files it under ordinary.",
            tags: ["wonder-compass", "souvenir", "write", "memory"]
        ),
        ReferenceSnippet(
            id: "wonder-compass-rest-center",
            sourceID: "wonder-compass",
            title: "Center Means Rest",
            prompt: "Let rest be part of the practice.",
            body: "Rest is not failure to adventure. Rest is the center of the Compass. Some days the most radical expedition is stopping before the day breaks you.",
            tags: ["wonder-compass", "rest", "center", "care"]
        ),
        ReferenceSnippet(
            id: "wonder-compass-dark-loop",
            sourceID: "wonder-compass",
            title: "The Compass In The Dark",
            prompt: "Use the smallest true thing.",
            body: "On hard days, the Compass gets smaller. Notice one object that is not dying. Embark by moving one inch. Sense without judging. Write evidence: I was here.",
            tags: ["wonder-compass", "hard-day", "rest", "survival"]
        ),
        ReferenceSnippet(
            id: "wonder-compass-playful-mission",
            sourceID: "wonder-compass",
            title: "Playful Mission",
            prompt: "Give your senses a tiny game.",
            body: "Pick an action, an adjective, and a sense: find three rough textures, listen for five tiny sounds, hunt one impossible shade of blue. Play makes attention easier to hold.",
            tags: ["wonder-compass", "sense", "play"]
        )
    ]

    static let fallbackEnchantifyLore: [ReferenceSnippet] = [
        ReferenceSnippet(
            id: "labyrinth-lore-book-of-you",
            sourceID: "labyrinth-lore",
            title: "The Book of You",
            prompt: "Let today become a page worth keeping.",
            body: "The Book of You is the private volume that waits closest to the reader. It does not demand grand adventures. It notices the cup left beside the bed, the weather at the window, the sentence that would have vanished if no one had written it down. When a page is kept, the Book does not announce a score. It simply grows warmer, as if one more lamp has been lit in a long room.",
            tags: ["book-of-you", "memory", "private", "rooms"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-academy",
            sourceID: "labyrinth-lore",
            title: "The Academy of Unlikely Arts",
            prompt: "Step through the school-shaped margin.",
            body: "The Academy is a school built inside a living library. Its corridors behave like chapters, its classrooms keep weather of their own, and its professors tend to believe ordinary life is already enchanted but poorly indexed. Students learn by paying attention, losing their way responsibly, and returning with evidence. The school is less interested in spectacle than in whether a person can notice a true thing and carry it home intact.",
            tags: ["academy", "school", "history", "classes"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-penny-blackletter",
            sourceID: "labyrinth-lore",
            title: "Penny Blackletter",
            prompt: "Let Penny file the ridiculous evidence.",
            body: "Penny Blackletter runs the margins as if every overlooked detail might become tomorrow's headline. She writes fast, loves a field note, distrusts any sentence that arrives too polished, and has never met a strange little scrap of paper she could not put to work. Penny is warm under the theatrical deadlines. She believes a day is not truly lost if one honest detail can still be recovered from it.",
            tags: ["characters", "penny", "marginalia", "letters"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-letters",
            sourceID: "labyrinth-lore",
            title: "Letters From The Margins",
            prompt: "A message can arrive from elsewhere.",
            body: "Letters in the Labyrinth do not arrive merely to explain things. They arrive with tea rings, crossed-out sentences, pressed flowers, bad timing, and the faint sense that someone hesitated before folding the page. A good letter carries relationship: what the sender wants, what they fear asking, what they noticed when the reader was elsewhere, and which door they are quietly hoping will open next.",
            tags: ["letters", "characters", "relationships", "margins"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-outer-stacks",
            sourceID: "labyrinth-lore",
            title: "The Outer Stacks",
            prompt: "Let a place become a room.",
            body: "Beyond the Academy's catalogued halls are the Outer Stacks, where real places gather room-feelings. A harbor may become a tidal reading room. A cafe may keep a tiny kingdom beneath the sugar packets. A parking lot may hold a door that only appears when the light hits the asphalt correctly. The Outer Stacks do not make places less real. They make them more themselves.",
            tags: ["outer-stacks", "location", "rooms", "place"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-rooms",
            sourceID: "labyrinth-lore",
            title: "Rooms That Behave Like Pages",
            prompt: "Open the door that has been waiting.",
            body: "Rooms in the Labyrinth are not neutral containers. A room has a mood, a history, a preferred volume, and sometimes a private grudge against certain shoes. The Quillquarium is full of writing instruments swimming through the air until the right one chooses the right student. The Peculiar Potions Parlor contains cauldrons with personalities and dramatic opinions about stirring. The Clockwork Conservatory plays music with or without permission. A Story Page can borrow any of these rooms when a day needs shape, shelter, or mischief.",
            tags: ["classes", "locations", "rooms", "story"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-classes",
            sourceID: "labyrinth-lore",
            title: "The Compass Core Classes",
            prompt: "Let the school turn attention into practice.",
            body: "Every student eventually meets the foundation classes. Professor Lydia Boggle teaches the Art of the Glint, where ordinary objects are treated as witnesses. Professor Kyle Momort teaches Wayfinding and Narrative Kineticism, and his students learn that motion has consequences even when it begins as one step. Professor Eleanor Euphony teaches Synesthetic Resonance, where rooms have temperature, colors have weight, and the senses are given serious academic standing. Professor Vivian Villanelle teaches Ink-Binding and Souvenir Craft, where a sentence becomes a small vessel for time.",
            tags: ["classes", "faculty", "school", "schedule"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-schedule",
            sourceID: "labyrinth-lore",
            title: "The Shape of a School Day",
            prompt: "Notice the bells beneath the ordinary day.",
            body: "A school day at the Academy has a rhythm, though the building enjoys bending it. Morning classes run when the corridors are bright enough to be optimistic. Afternoon classes take the settled hours, when the Library has formed opinions and students are less easily impressed. Clubs gather under lamps in rooms that pretend not to be listening. Between these formal hours are the true passages: breakfast gossip, corridor weather, the note slipped under a door, and the friend waiting outside the room with a question folded into silence.",
            tags: ["classes", "schedule", "school", "student-life"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-headmistress-thorne",
            sourceID: "labyrinth-lore",
            title: "Headmistress Seraphina Thorne",
            prompt: "Let authority enter with a hidden page.",
            body: "Headmistress Seraphina Thorne has the poise of someone who can silence a room by closing a book. Students see the elegant robes, the precise speech, the old authority of a person who knows which staircases lie. What they do not always see is the cost of keeping a school safe when the school itself is a living text with strong opinions and a long memory. Thorne is not soft, but she is not careless. Her office contains a legendary inkwell, officially for safekeeping. Unofficially, students suspect she uses it after midnight.",
            tags: ["characters", "faculty", "headmistress", "history"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-history",
            sourceID: "labyrinth-lore",
            title: "Unreliable Academy History",
            prompt: "Let the old stories misbehave politely.",
            body: "Academy history is full of incidents recorded with suspiciously careful handwriting. During the Day of the Living Literary Figures, Sherlock Holmes, Alice, and Dracula appeared in the cafeteria at the same time; Holmes deduced the menu, Alice critiqued the architecture, and Dracula objected to the lighting. The Pages of Laughter and Tears once made an entire class alternate between hysterics and sobbing until someone discovered the comedy and tragedy pages had been shelved out of order. These stories are told as warnings, but students mostly hear invitations.",
            tags: ["academy", "history", "school", "story"]
        ),
        ReferenceSnippet(
            id: "labyrinth-lore-weather",
            sourceID: "labyrinth-lore",
            title: "Weather in the Stacks",
            prompt: "Let the sky annotate the page.",
            body: "Weather at the Academy is never only meteorological, but it is never merely symbolic either. Fog makes professors cancel class to watch the harbor disappear by degrees. Rain turns corridors into quieter arguments. Bright cold sharpens the ink. Heat makes the paper curl and the students theatrical. The Library cloud above the great ceiling changes color when the building is thinking about something it does not intend to say aloud. A weather page should remain legible, but the Book may name the mood of the response. The reader should feel tended, not watched.",
            tags: ["atmosphere", "school", "weather", "world"]
        )
    ]

    static let fallbackPatreon: [ReferenceSnippet] = [
        ReferenceSnippet(
            id: "patreon-clubhouse-free-shelf",
            sourceID: "patreon-packet",
            title: "Patreon Clubhouse",
            prompt: "The free shelf is open.",
            body: "The Wonder Compass ebook, printable play-sheets, Spark menus, Playful Mission menus, and Clubhouse notes live at patreon.com/thedoobaleedoos. The practice is free; the attention is real.",
            tags: ["patreon", "clubhouse", "wonder-compass", "free"]
        )
    ]

    static func dailyWonderCompassSnippet(for day: BookDay, now: Date = Date()) -> ReferenceSnippet {
        snippet(from: wonderCompass, dayID: day.id, sourceID: "wonder-compass", now: now)
    }

    static func relevantWonderCompassSnippet(
        for day: BookDay,
        inputs: BookSourceInputs = .empty,
        now: Date = Date()
    ) -> ReferenceSnippet {
        relevantWonderCompassSnippets(for: day, inputs: inputs, now: now, limit: 1).first
            ?? dailyWonderCompassSnippet(for: day, now: now)
    }

    static func relevantWonderCompassSnippets(
        for day: BookDay,
        inputs: BookSourceInputs = .empty,
        now: Date = Date(),
        limit: Int = 8
    ) -> [ReferenceSnippet] {
        let snippets = wonderCompass
        guard !snippets.isEmpty else { return [] }

        let contextTerms = wonderCompassContextTerms(for: day, inputs: inputs, now: now)
        let rotationSlot = referenceRotationSlot(for: now)
        let scored = snippets.enumerated().map { offset, snippet in
            let haystack = ([snippet.title, snippet.prompt, snippet.body] + snippet.tags)
                .joined(separator: " ")
                .lowercased()
            let score = contextTerms.reduce(0) { partial, term in
                haystack.contains(term) ? partial + 1 : partial
            }
            return (offset: offset, snippet: snippet, score: score)
        }

        return scored
            .sorted { left, right in
                if left.score == right.score {
                    let daySeed = stableIndex(for: "\(day.id)-\(rotationSlot)-\(left.snippet.id)-wonder-compass-relevance", count: 10_000)
                    let otherSeed = stableIndex(for: "\(day.id)-\(rotationSlot)-\(right.snippet.id)-wonder-compass-relevance", count: 10_000)
                    if daySeed == otherSeed {
                        return left.offset < right.offset
                    }
                    return daySeed < otherSeed
                }
                return left.score > right.score
            }
            .prefix(max(1, limit))
            .map(\.snippet)
    }

    static func dailyEnchantifyLoreSnippet(for day: BookDay, now: Date = Date()) -> ReferenceSnippet {
        snippet(from: enchantifyLore, dayID: day.id, sourceID: "labyrinth-lore", now: now)
    }

    static func relevantLoreSnippet(
        for day: BookDay,
        inputs: BookSourceInputs = .empty,
        now: Date = Date()
    ) -> ReferenceSnippet {
        relevantLoreSnippets(for: day, inputs: inputs, now: now, limit: 1).first
            ?? dailyEnchantifyLoreSnippet(for: day, now: now)
    }

    static func relevantLoreSnippets(
        for day: BookDay,
        inputs: BookSourceInputs = .empty,
        now: Date = Date(),
        limit: Int = 6
    ) -> [ReferenceSnippet] {
        let snippets = enchantifyLore
        guard !snippets.isEmpty else { return [] }

        let contextTerms = loreContextTerms(for: day, inputs: inputs, now: now)
        let rotationSlot = referenceRotationSlot(for: now)
        let scored = snippets.enumerated().map { offset, snippet in
            let haystack = ([snippet.title, snippet.prompt, snippet.body] + snippet.tags)
                .joined(separator: " ")
                .lowercased()
            let score = contextTerms.reduce(0) { partial, term in
                haystack.contains(term) ? partial + 1 : partial
            }
            return (offset: offset, snippet: snippet, score: score)
        }

        return scored
            .sorted { left, right in
                if left.score == right.score {
                    let leftSeed = stableIndex(for: "\(day.id)-\(rotationSlot)-\(left.snippet.id)-labyrinth-lore-relevance", count: 10_000)
                    let rightSeed = stableIndex(for: "\(day.id)-\(rotationSlot)-\(right.snippet.id)-labyrinth-lore-relevance", count: 10_000)
                    if leftSeed == rightSeed {
                        return left.offset < right.offset
                    }
                    return leftSeed < rightSeed
                }
                return left.score > right.score
            }
            .prefix(max(1, limit))
            .map(\.snippet)
    }

    static func patreonShelfSnippet(now: Date = Date()) -> ReferenceSnippet {
        snippet(from: patreon, dayID: currentDayID(now), sourceID: "patreon-packet", now: now)
    }

    static func patreonPostSnippets(limit: Int = 6, now: Date = Date()) -> [ReferenceSnippet] {
        let posts = patreon
            .filter { snippet in
                snippet.url?.isEmpty == false
                    || snippet.body.range(of: "https://", options: [.caseInsensitive]) != nil
                    || snippet.body.range(of: "http://", options: [.caseInsensitive]) != nil
            }
            .sorted { left, right in
                let leftDate = left.publishedAt ?? ""
                let rightDate = right.publishedAt ?? ""
                if leftDate == rightDate {
                    return left.title.localizedCaseInsensitiveCompare(right.title) == .orderedAscending
                }
                return leftDate > rightDate
            }
        guard !posts.isEmpty else { return [] }
        return Array(posts.prefix(max(1, limit)))
    }

    static func labyrinthIllustration(for day: BookDay, now: Date = Date()) -> LabyrinthIllustrationPlate {
        guard !labyrinthIllustrations.isEmpty else {
            return LabyrinthIllustrationPlate(
                id: "empty",
                assetName: "",
                title: "Illustration",
                caption: "The illustration shelf is empty for now.",
                note: "Add character dossier assets to wake this page.",
                tags: ["illustration"]
            )
        }
        let seed = "\(day.id)-labyrinth-illustrations-\(referenceRotationSlot(for: now, hours: 1))"
        return labyrinthIllustrations[stableIndex(for: seed, count: labyrinthIllustrations.count)]
    }

    static func characterIllustrationProfile(id: String?) -> CharacterIllustrationProfile? {
        guard let id else { return nil }
        return characterIllustrations.first { $0.id == id }
    }

    static func firstURL(in snippet: ReferenceSnippet) -> String? {
        snippet.url?.isEmpty == false ? snippet.url : firstURL(in: snippet.body)
    }

    private static func firstURL(in text: String) -> String? {
        guard let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) else {
            return nil
        }
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        return detector.firstMatch(in: text, range: range)?.url?.absoluteString
    }

    private static func currentDayID(_ date: Date, calendar: Calendar = .current) -> String {
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        let year = components.year ?? 1970
        let month = components.month ?? 1
        let day = components.day ?? 1
        return String(format: "%04d-%02d-%02d", year, month, day)
    }

    private static func snippet(from snippets: [ReferenceSnippet], dayID: String, sourceID: String, now: Date) -> ReferenceSnippet {
        guard !snippets.isEmpty else {
            return ReferenceSnippet(
                id: "\(sourceID)-empty",
                sourceID: sourceID,
                title: "Reference Page",
                prompt: "A reference page is waiting.",
                body: "The Book knows this shelf exists, but no snippets have been loaded yet.",
                tags: [sourceID]
            )
        }

        let seed = "\(dayID)-\(sourceID)-\(referenceRotationSlot(for: now))"
        let index = stableIndex(for: seed, count: snippets.count)
        return snippets[index]
    }

    private static func referenceRotationSlot(for date: Date, hours: Int = 2, calendar: Calendar = .current) -> Int {
        let components = calendar.dateComponents([.hour], from: date)
        return (components.hour ?? 0) / max(1, hours)
    }

    private static func wonderCompassContextTerms(for day: BookDay, inputs: BookSourceInputs, now: Date) -> [String] {
        var terms: Set<String> = ["wonder", "notice"]
        let hour = Calendar.current.component(.hour, from: now)

        if hour >= 18 {
            terms.formUnion(["souvenir", "write", "memory", "sentence"])
        }
        if hour >= 20 {
            terms.formUnion(["rest", "center", "care"])
        }

        for page in day.capturedPages {
            terms.formUnion(page.tags.map { $0.lowercased() })
            let lowered = page.userInput.lowercased()
            if lowered.contains("tired") || lowered.contains("low") || lowered.contains("hard") || lowered.contains("heavy") {
                terms.formUnion(["rest", "care", "hard-day"])
            }
            if lowered.contains("walk") || lowered.contains("outside") || lowered.contains("errand") {
                terms.formUnion(["embark", "practice"])
            }
            if lowered.contains("saw") || lowered.contains("heard") || lowered.contains("felt") || lowered.contains("smell") {
                terms.formUnion(["sense", "notice"])
            }
            if lowered.contains("remember") || lowered.contains("moment") || lowered.contains("today") {
                terms.formUnion(["souvenir", "write", "memory"])
            }
            if lowered.contains("play") || lowered.contains("fun") || lowered.contains("silly") {
                terms.formUnion(["play", "mission"])
            }
        }

        if let body = inputs.body {
            let lowered = "\(body.status) \(body.phrase)".lowercased()
            if body.score > 0 && body.score <= 35 || lowered.contains("low") || lowered.contains("gentle") {
                terms.formUnion(["rest", "center", "care", "hard-day"])
            }
        }

        if let weather = inputs.weather {
            let lowered = weather.phrase.lowercased()
            if lowered.contains("rain") || lowered.contains("fog") || lowered.contains("storm") {
                terms.formUnion(["sense", "notice", "rest"])
            }
            if lowered.contains("sun") || lowered.contains("bright") || lowered.contains("clear") {
                terms.formUnion(["embark", "play", "notice"])
            }
        }

        for fact in inputs.selfFacts where fact.usePermission != .doNotUse {
            terms.formUnion(fact.tags.map { $0.lowercased() })
            let lowered = "\(fact.question) \(fact.answer)".lowercased()
            if lowered.contains("home") {
                terms.formUnion(["home", "rest", "care"])
            }
            if lowered.contains("color") || lowered.contains("delight") || lowered.contains("joy") {
                terms.formUnion(["play", "wonder", "notice"])
            }
            if lowered.contains("rest") || lowered.contains("quiet") || lowered.contains("sleep") {
                terms.formUnion(["rest", "center", "care"])
            }
            if lowered.contains("believe") || lowered.contains("protect") || lowered.contains("become") {
                terms.formUnion(["belief", "practice", "memory"])
            }
        }

        return Array(terms)
    }

    private static func loreContextTerms(for day: BookDay, inputs: BookSourceInputs, now: Date) -> [String] {
        var terms = Set(wonderCompassContextTerms(for: day, inputs: inputs, now: now))
        terms.formUnion(["academy", "book", "characters", "lore", "rooms", "school", "story"])

        let hour = Calendar.current.component(.hour, from: now)
        if hour < 11 {
            terms.formUnion(["schedule", "classes", "today"])
        } else if hour >= 18 {
            terms.formUnion(["letters", "dormitory", "student-life"])
        }

        if inputs.weather != nil {
            terms.formUnion(["weather", "atmosphere"])
        }
        if inputs.body != nil {
            terms.formUnion(["body", "care"])
        }
        if inputs.selfFacts.contains(where: { $0.usePermission != .doNotUse && $0.tags.contains("home") }) {
            terms.formUnion(["home", "dormitory", "rooms"])
        }

        return Array(terms)
    }

    private static func stableIndex(for seed: String, count: Int) -> Int {
        guard count > 0 else { return 0 }
        let value = seed.unicodeScalars.reduce(UInt64(14_695_981_039_346_656_037)) { partial, scalar in
            (partial ^ UInt64(scalar.value)).multipliedReportingOverflow(by: 1_099_511_628_211).partialValue
        }
        return Int(value % UInt64(count))
    }
}

struct BookPageMediaAsset: Codable, Identifiable, Equatable {
    enum Kind: String, Codable {
        case bundledImage
        case renderedImageFile
        case photoLibraryAsset
    }

    var id: String
    var kind: Kind
    var reference: String
    var caption: String
    var sourceID: String
    var metadata: [String: String]

    init(
        id: String = UUID().uuidString,
        kind: Kind,
        reference: String,
        caption: String = "",
        sourceID: String = "",
        metadata: [String: String] = [:]
    ) {
        self.id = id
        self.kind = kind
        self.reference = reference
        self.caption = caption
        self.sourceID = sourceID
        self.metadata = metadata
    }
}

struct BookPage: Codable, Identifiable, Equatable {
    var id: String
    var type: BookPageType
    var createdAt: Date
    var promptText: String
    var userInput: String
    var tags: [String]
    var usedInBookOfYou: Bool
    var sourceID: String
    var origin: BookPageOrigin
    var privacy: BookPagePrivacy
    var promptVersion: String?
    var mediaAssets: [BookPageMediaAsset]

    init(
        id: String = UUID().uuidString,
        type: BookPageType,
        createdAt: Date = Date(),
        promptText: String,
        userInput: String = "",
        tags: [String] = [],
        usedInBookOfYou: Bool = false,
        sourceID: String? = nil,
        origin: BookPageOrigin? = nil,
        privacy: BookPagePrivacy = .privateLocal,
        promptVersion: String? = nil,
        mediaAssets: [BookPageMediaAsset] = []
    ) {
        self.id = id
        self.type = type
        self.createdAt = createdAt
        self.promptText = promptText
        self.userInput = userInput
        self.tags = tags
        self.usedInBookOfYou = usedInBookOfYou
        self.sourceID = sourceID ?? type.rawValue
        self.origin = origin ?? (type == .bookOfYou ? .generated : .userAuthored)
        self.privacy = privacy
        self.promptVersion = promptVersion
        self.mediaAssets = mediaAssets
    }

    enum CodingKeys: String, CodingKey {
        case id
        case type
        case createdAt
        case promptText
        case userInput
        case tags
        case usedInBookOfYou
        case sourceID
        case origin
        case privacy
        case promptVersion
        case mediaAssets
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        type = try container.decode(BookPageType.self, forKey: .type)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        promptText = try container.decode(String.self, forKey: .promptText)
        userInput = try container.decodeIfPresent(String.self, forKey: .userInput) ?? ""
        tags = try container.decodeIfPresent([String].self, forKey: .tags) ?? []
        usedInBookOfYou = try container.decodeIfPresent(Bool.self, forKey: .usedInBookOfYou) ?? false
        sourceID = try container.decodeIfPresent(String.self, forKey: .sourceID) ?? type.rawValue
        origin = try container.decodeIfPresent(BookPageOrigin.self, forKey: .origin) ?? (type == .bookOfYou ? .generated : .userAuthored)
        privacy = try container.decodeIfPresent(BookPagePrivacy.self, forKey: .privacy) ?? .privateLocal
        promptVersion = try container.decodeIfPresent(String.self, forKey: .promptVersion)
        mediaAssets = try container.decodeIfPresent([BookPageMediaAsset].self, forKey: .mediaAssets) ?? []
    }
}

struct BookDay: Codable, Identifiable, Equatable {
    var id: String
    var date: Date
    var pages: [BookPage]

    var hasMood: Bool {
        pages.contains { $0.type == .mood }
    }

    var hasSouvenir: Bool {
        pages.contains { $0.type == .souvenir }
    }

    var hasRest: Bool {
        pages.contains { $0.type == .rest }
    }

    var bookOfYou: BookPage? {
        pages.last { $0.type == .bookOfYou }
    }

    var capturedPages: [BookPage] {
        pages.filter { $0.type != .bookOfYou }
    }

    static func today(calendar: Calendar = .current) -> BookDay {
        day(containing: Date(), calendar: calendar)
    }

    static func day(containing date: Date, calendar: Calendar = .current) -> BookDay {
        let start = calendar.startOfDay(for: date)
        return BookDay(id: Self.id(for: start), date: start, pages: [])
    }

    static func id(for date: Date, calendar: Calendar = .current) -> String {
        let comps = calendar.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", comps.year ?? 0, comps.month ?? 0, comps.day ?? 0)
    }
}

struct BraidRecoveryState: Codable, Equatable {
    private(set) var canRetry = false
    private(set) var lastError: String?

    var retryActionTitle: String? {
        canRetry ? "Try again" : nil
    }

    mutating func beginAttempt() {
        canRetry = false
    }

    mutating func recordFailure(_ error: String, day: BookDay) {
        guard day.bookOfYou == nil, !day.capturedPages.isEmpty else {
            canRetry = false
            lastError = nil
            return
        }
        canRetry = true
        lastError = error
    }

    mutating func recordSuccess() {
        canRetry = false
        lastError = nil
    }

    static func dayByMarkingCapturedPagesUsed(_ day: BookDay, braid: BookPage) -> BookDay {
        var updatedDay = day
        updatedDay.pages = updatedDay.pages.map { page in
            var updated = page
            if updated.type != .bookOfYou {
                updated.usedInBookOfYou = true
            }
            return updated
        }
        updatedDay.pages.append(braid)
        return updatedDay
    }
}

struct PreparedPageRecoveryState: Codable, Equatable {
    private(set) var lastFailureAt: Date?
    var cooldown: TimeInterval

    init(lastFailureAt: Date? = nil, cooldown: TimeInterval = 20 * 60) {
        self.lastFailureAt = lastFailureAt
        self.cooldown = cooldown
    }

    func shouldBegin(
        isPreparing: Bool,
        isLocalBrainWorking: Bool,
        preparedSurface: SurfacePage?,
        slotID: String,
        requiredMetadataKey: String,
        now: Date
    ) -> Bool {
        guard !isPreparing, !isLocalBrainWorking else { return false }
        guard !isCoolingDown(now: now) else { return false }
        return !Self.preparedSurfaceIsCurrent(
            preparedSurface,
            slotID: slotID,
            requiredMetadataKey: requiredMetadataKey
        )
    }

    func isCoolingDown(now: Date) -> Bool {
        guard let lastFailureAt else { return false }
        return now.timeIntervalSince(lastFailureAt) < cooldown
    }

    mutating func recordFailure(at date: Date = Date()) {
        lastFailureAt = date
    }

    mutating func recordSuccess() {
        lastFailureAt = nil
    }

    static func preparedSurfaceIsCurrent(
        _ surface: SurfacePage?,
        slotID: String,
        requiredMetadataKey: String
    ) -> Bool {
        guard let surface,
              surface.payload.metadata["slotID"] == slotID,
              surface.payload.metadata[requiredMetadataKey]?.isEmpty == false else {
            return false
        }
        return true
    }
}

struct LocalBrainTelemetryState: Codable, Equatable {
    private(set) var isReading = false
    private(set) var isWorking = false
    private(set) var currentLabel = "the Book"
    private(set) var currentPromptCharacters = 0
    private(set) var currentQueuedCount = 0
    private(set) var startedAt: Date?
    private(set) var lastLabel = "none"
    private(set) var lastPromptCharacters = 0
    private(set) var lastFinishedAt: Date?
    private(set) var lastError: String?

    var currentWorkStatus: String? {
        guard isWorking else { return nil }
        return "\(currentLabel) · \(currentPromptCharacters) chars · \(currentQueuedCount) queued"
    }

    func lastWorkStatus(formatDate: (Date) -> String) -> String {
        let finishedText = lastFinishedAt.map(formatDate) ?? "not finished"
        return "\(lastLabel) · \(lastPromptCharacters) chars · \(finishedText)"
    }

    mutating func wake() {
        isReading = true
    }

    mutating func rest() {
        isReading = false
    }

    mutating func beginOrUpdateWork(
        label: String?,
        promptCharacters: Int,
        queuedCount: Int,
        now: Date = Date()
    ) -> Bool {
        let didBegin = !isWorking
        if didBegin {
            startedAt = now
        }
        let displayLabel = label ?? "the Book"
        isWorking = true
        currentLabel = displayLabel
        currentPromptCharacters = promptCharacters
        currentQueuedCount = queuedCount
        lastLabel = displayLabel
        lastPromptCharacters = promptCharacters
        return didBegin
    }

    mutating func finishWork(now: Date = Date()) {
        isWorking = false
        startedAt = nil
        currentQueuedCount = 0
        currentPromptCharacters = 0
        lastFinishedAt = now
    }

    mutating func resetTransientWork() {
        isReading = false
        isWorking = false
        startedAt = nil
        currentQueuedCount = 0
        currentPromptCharacters = 0
    }

    mutating func recordError(_ error: String) {
        lastError = error
    }

    mutating func clearError() {
        lastError = nil
    }
}

struct BookArchiveExport: Codable, Equatable {
    static let schemaVersion = 1

    var schemaVersion: Int
    var generatedAt: Date
    var dayCount: Int
    var pageCount: Int
    var days: [BookDay]

    init(
        generatedAt: Date = Date(),
        days: [BookDay],
        calendar: Calendar = .current
    ) {
        let normalizedDays = Self.normalizedDays(days, calendar: calendar)
        self.schemaVersion = Self.schemaVersion
        self.generatedAt = generatedAt
        self.dayCount = normalizedDays.count
        self.pageCount = normalizedDays.reduce(0) { $0 + $1.pages.count }
        self.days = normalizedDays
    }

    func encodedData() throws -> Data {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }

    static func decoded(from data: Data) throws -> BookArchiveExport {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(BookArchiveExport.self, from: data)
    }

    private static func normalizedDays(_ days: [BookDay], calendar: Calendar) -> [BookDay] {
        var merged: [String: BookDay] = [:]
        for day in days {
            var normalized = day
            normalized.id = BookDay.id(for: day.date, calendar: calendar)
            normalized.date = calendar.startOfDay(for: day.date)
            normalized.pages = day.pages.sorted { $0.createdAt < $1.createdAt }
            if var existing = merged[normalized.id] {
                existing.pages.append(contentsOf: normalized.pages)
                existing.pages = uniquePages(existing.pages).sorted { $0.createdAt < $1.createdAt }
                merged[normalized.id] = existing
            } else {
                normalized.pages = uniquePages(normalized.pages)
                merged[normalized.id] = normalized
            }
        }
        return merged.values
            .sorted { $0.date < $1.date }
    }

    private static func uniquePages(_ pages: [BookPage]) -> [BookPage] {
        var seen = Set<String>()
        return pages.filter { page in
            seen.insert(page.id).inserted
        }
    }
}

struct BookPageQuery: Equatable {
    var type: BookPageType?
    var sourceID: String?
    var tag: String?
    var privacy: BookPagePrivacy?
    var usedInBookOfYou: Bool?
    var startDate: Date?
    var endDate: Date?
    var limit: Int

    init(
        type: BookPageType? = nil,
        sourceID: String? = nil,
        tag: String? = nil,
        privacy: BookPagePrivacy? = nil,
        usedInBookOfYou: Bool? = nil,
        startDate: Date? = nil,
        endDate: Date? = nil,
        limit: Int = 20
    ) {
        self.type = type
        self.sourceID = sourceID
        self.tag = tag
        self.privacy = privacy
        self.usedInBookOfYou = usedInBookOfYou
        self.startDate = startDate
        self.endDate = endDate
        self.limit = limit
    }
}

enum BookArchiveIndex {
    static func pages(in days: [BookDay], matching query: BookPageQuery) -> [BookPage] {
        days
            .flatMap(\.pages)
            .sorted { $0.createdAt > $1.createdAt }
            .lazy
            .filter { matches($0, query: query) }
            .prefix(max(query.limit, 0))
            .map { $0 }
    }

    static func resurfacingCandidates(
        in days: [BookDay],
        before date: Date = Date(),
        calendar: Calendar = .current,
        limit: Int = 12
    ) -> [BookPage] {
        let startOfDay = calendar.startOfDay(for: date)
        return pages(
            in: days,
            matching: BookPageQuery(
                type: .souvenir,
                usedInBookOfYou: true,
                endDate: startOfDay,
                limit: limit
            )
        )
    }

    static func matches(_ page: BookPage, query: BookPageQuery) -> Bool {
        if let type = query.type, page.type != type {
            return false
        }
        if let sourceID = query.sourceID, page.sourceID != sourceID {
            return false
        }
        if let tag = query.tag,
           !page.tags.contains(where: { $0.localizedCaseInsensitiveCompare(tag) == .orderedSame }) {
            return false
        }
        if let privacy = query.privacy, page.privacy != privacy {
            return false
        }
        if let usedInBookOfYou = query.usedInBookOfYou,
           page.usedInBookOfYou != usedInBookOfYou {
            return false
        }
        if let startDate = query.startDate, page.createdAt < startDate {
            return false
        }
        if let endDate = query.endDate, page.createdAt >= endDate {
            return false
        }
        return true
    }
}

struct SurfacePage: Identifiable, Equatable {
    let id: String
    let type: BookPageType
    let sourceID: String
    let intent: BookPageIntent
    let renderStyle: BookPageRenderStyle
    let score: Int
    let reason: String
    let prompt: String
    let detail: String
    let payload: BookPagePayload

    var source: BookPageSource {
        BookPageSourceRegistry.source(id: sourceID, fallbackType: type)
    }

    var origin: BookPageOrigin {
        source.origin
    }

    var privacy: BookPagePrivacy {
        source.privacy
    }

    var mediaAssets: [BookPageMediaAsset] {
        var assets: [BookPageMediaAsset] = []
        if type == .illustration,
           let assetName = nonEmptyMetadataValue("assetName") {
            assets.append(BookPageMediaAsset(
                kind: .bundledImage,
                reference: assetName,
                caption: payload.headline,
                sourceID: sourceID,
                metadata: payload.metadata
            ))
        }
        if type == .illuminatedPhoto {
            if let renderedPath = nonEmptyMetadataValue("renderedPreviewPath") {
                assets.append(BookPageMediaAsset(
                    kind: .renderedImageFile,
                    reference: renderedPath,
                    caption: payload.headline,
                    sourceID: sourceID,
                    metadata: payload.metadata
                ))
            }
            if let assetLocalIdentifier = nonEmptyMetadataValue("assetLocalIdentifier") {
                assets.append(BookPageMediaAsset(
                    kind: .photoLibraryAsset,
                    reference: assetLocalIdentifier,
                    caption: payload.headline,
                    sourceID: sourceID,
                    metadata: payload.metadata
                ))
            }
        }
        if let proofImagePath = nonEmptyMetadataValue("proofImagePath") {
            assets.append(BookPageMediaAsset(
                kind: .renderedImageFile,
                reference: proofImagePath,
                caption: payload.metadata["proofCaption"] ?? payload.headline,
                sourceID: sourceID,
                metadata: payload.metadata
            ))
        }
        return assets
    }

    init(
        id: String? = nil,
        type: BookPageType,
        sourceID: String? = nil,
        intent: BookPageIntent? = nil,
        renderStyle: BookPageRenderStyle = .promptCard,
        score: Int = 50,
        reason: String = "The Book has room for this page.",
        prompt: String,
        detail: String,
        payload: BookPagePayload? = nil
    ) {
        let source = BookPageSourceRegistry.source(for: type)
        self.type = type
        self.sourceID = sourceID ?? source.id
        self.intent = intent ?? Self.defaultIntent(for: type)
        self.id = id ?? "\(self.sourceID)-\(self.intent.rawValue)"
        self.renderStyle = renderStyle
        self.score = score
        self.reason = reason
        self.prompt = prompt
        self.detail = detail
        self.payload = payload ?? BookPagePayload(headline: prompt, body: detail)
    }

    private static func defaultIntent(for type: BookPageType) -> BookPageIntent {
        switch type {
        case .rest:
            return .rest
        case .bookOfYou:
            return .braid
        case .body, .fuel, .facultyResearch, .supportGuild, .weather:
            return .reflect
        case .wonderCompass, .lore, .patreon, .illustration, .quip:
            return .importReference
        case .illuminatedPhoto:
            return .resurface
        case .location:
            return .reflect
        case .narrativeOS:
            return .simulate
        case .gossip:
            return .simulate
        case .mood, .souvenir, .aboutYou:
            return .capture
        }
    }

    private func nonEmptyMetadataValue(_ key: String) -> String? {
        let value = payload.metadata[key]?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return value.isEmpty ? nil : value
    }
}

extension SurfacePage {
    static func illuminatedPhotoSurface(
        draft: IlluminatedPhotoDraft,
        renderedURL: URL?,
        idSuffix: String
    ) -> SurfacePage? {
        let source = BookPageSourceRegistry.source(for: .illuminatedPhoto)
        var metadata: [String: String] = [
            "source": source.id,
            "sourceAssetName": draft.sourceAssetName,
            "assetLocalIdentifier": draft.assetLocalIdentifier,
            "template": draft.compositionPlan.templateId.rawValue,
            "assetPack": draft.compositionPlan.assetPackId,
            "status": draft.status.rawValue,
            "privacy": "private local draft",
            "fieldNote": draft.analysis.marginalia.fieldNote,
            "stampLabel": draft.analysis.marginalia.stampLabel,
            "observations": draft.analysis.marginalia.observationList.joined(separator: " | "),
            "closingLine": draft.analysis.marginalia.closingLine,
            "scene": draft.analysis.scene,
            "motifs": draft.analysis.motifs.joined(separator: ","),
            "mood": draft.analysis.mood,
            "souvenirs": draft.analysis.souvenirCandidates.joined(separator: " | ")
        ]
        if let renderedURL {
            metadata["renderedPreviewPath"] = renderedURL.path
        }

        return SurfacePage(
            id: "\(source.id)-\(draft.assetLocalIdentifier.hashValue)-\(idSuffix)",
            type: .illuminatedPhoto,
            sourceID: source.id,
            intent: .resurface,
            renderStyle: .illuminatedPhoto,
            score: 96,
            reason: "Penny found a photo with ink on it.",
            prompt: "Found in the Margins",
            detail: "The Book found this in the camera roll and made it a page worth considering.",
            payload: BookPagePayload(
                headline: draft.analysis.marginalia.stampLabel,
                body: draft.analysis.marginalia.closingLine,
                metadata: metadata
            )
        )
    }
}

struct CodablePoint: Codable, Equatable {
    var x: Double
    var y: Double
}

struct CodableSize: Codable, Equatable {
    var width: Double
    var height: Double
}

struct ClosedDoubleRange: Codable, Equatable {
    var lowerBound: Double
    var upperBound: Double

    func value(seed: Int, salt: Int) -> Double {
        guard upperBound > lowerBound else { return lowerBound }
        let mixed = abs((seed &* 31) ^ (salt &* 997))
        let unit = Double(mixed % 10_000) / 10_000
        return lowerBound + (upperBound - lowerBound) * unit
    }
}

enum IlluminatedTemplateID: String, Codable, CaseIterable, Hashable {
    case harborFieldNote = "harbor_field_note"
    case creatureComfort = "creature_comfort"
    case homeVessel = "home_vessel"
    case goodCompany = "good_company"
    case academyFieldStudy = "academy_field_study"
    case restAndQuiet = "rest_and_quiet"
}

enum IlluminatedPageStatus: String, Codable, Equatable {
    case proposed
    case kept
    case dismissed
    case skipped
}

enum PhotoSuggestionMode: String, Codable, CaseIterable {
    case automatic
    case askFirst
    case manualOnly
    case off
}

struct PhotoSuggestionSettings: Codable, Equatable {
    var isEnabled: Bool
    var mode: PhotoSuggestionMode
    var lookbackHours: Int
    var includePeople: Bool
    var includePets: Bool
    var includeScreenshots: Bool
    var favoritesOnly: Bool
    var maxAutomaticSuggestionsPerDay: Int

    static let `default` = PhotoSuggestionSettings(
        isEnabled: true,
        mode: .askFirst,
        lookbackHours: 72,
        includePeople: true,
        includePets: true,
        includeScreenshots: false,
        favoritesOnly: false,
        maxAutomaticSuggestionsPerDay: 3
    )
}

struct PhotoCandidate: Identifiable, Codable, Equatable {
    var id: UUID
    var assetLocalIdentifier: String
    var creationDate: Date?
    var pixelWidth: Int
    var pixelHeight: Int
    var isFavorite: Bool
    var score: Double
    var reasons: [String]
    var discoveredAt: Date
}

struct IlluminatedPhotoHistory: Codable, Equatable {
    var keptAssetIdentifiers: Set<String> = []
    var dismissedAssetIdentifiers: Set<String> = []
    var proposedAssetIdentifiers: Set<String> = []
    var lastSuggestedAtByAsset: [String: Date] = [:]
}

struct PhotoMarginalia: Codable, Equatable {
    var fieldNote: String
    var stampLabel: String
    var observationList: [String]
    var closingLine: String
}

struct PhotoAnalysis: Codable, Equatable {
    var scene: String
    var motifs: [String]
    var mood: String
    var suggestedTemplate: IlluminatedTemplateID
    var marginalia: PhotoMarginalia
    var souvenirCandidates: [String]
}

enum PackAvailability: String, Codable, Equatable {
    case bundledFree
    case patron
    case paid
    case userImported
    case locked
}

enum IlluminationAssetKind: String, Codable, Equatable {
    case background
    case paperScrap
    case stamp
    case doodle
    case tape
    case overlay
}

struct IlluminationAsset: Identifiable, Codable, Equatable {
    var id: String
    var assetName: String
    var kind: IlluminationAssetKind
    var tags: [String]
    var supportedTemplates: [IlluminatedTemplateID]
    var defaultOpacity: Double
    var canTint: Bool
}

struct TemplateFallbackPhrases: Codable, Equatable {
    var fieldNotes: [String]
    var stampLabels: [String]
    var observations: [String]
    var closingLines: [String]
}

struct IlluminationAssetPack: Identifiable, Codable, Equatable {
    var id: String
    var displayName: String
    var version: String
    var author: String
    var availability: PackAvailability
    var supportedTemplates: [IlluminatedTemplateID]
    var backgrounds: [IlluminationAsset]
    var paperScraps: [IlluminationAsset]
    var stamps: [IlluminationAsset]
    var doodles: [IlluminationAsset]
    var tape: [IlluminationAsset]
    var overlays: [IlluminationAsset]
    var fallbackPhrases: [IlluminatedTemplateID: TemplateFallbackPhrases]

    var allAssets: [IlluminationAsset] {
        backgrounds + paperScraps + stamps + doodles + tape + overlays
    }
}

enum CanvasPreference: String, Codable, Equatable {
    case portrait
    case landscape
    case square
    case matchPhoto
}

enum PhotoOrientation: String, Codable, Equatable {
    case portrait
    case landscape
    case square
}

enum MarginaliaContentKey: String, Codable, Equatable {
    case fieldNote
    case stampLabel
    case observationList
    case closingLine
    case souvenirCandidate
    case fixedCompassReminder
    case fixedFrameLine
}

enum IlluminatedFontStyle: String, Codable, Equatable {
    case serifTitle
    case serifBody
    case handwritten
    case stamp
}

enum PhotoTreatment: String, Codable, Equatable {
    case naturalKept
    case softArchive
    case sepiaFieldNote
    case hearthGlow
    case quietMatte
}

struct TemplateTextSlotSpec: Identifiable, Codable, Equatable {
    var id: String
    var contentKey: MarginaliaContentKey
    var title: String?
    var position: CodablePoint
    var size: CodableSize
    var rotationRange: ClosedDoubleRange
    var paperTags: [String]
    var fontStyle: IlluminatedFontStyle
    var maxLines: Int
}

struct TemplateDecorationSlotSpec: Identifiable, Codable, Equatable {
    var id: String
    var kind: IlluminationAssetKind
    var tags: [String]
    var position: CodablePoint
    var size: CodableSize
    var rotationRange: ClosedDoubleRange
    var opacityRange: ClosedDoubleRange
    var required: Bool
}

struct IlluminationTemplate: Identifiable, Codable, Equatable {
    var id: IlluminatedTemplateID
    var displayName: String
    var preferredCanvas: CanvasPreference
    var supportedPhotoOrientations: [PhotoOrientation]
    var defaultPhotoTreatment: PhotoTreatment
    var requiredSlots: [TemplateTextSlotSpec]
    var optionalSlots: [TemplateTextSlotSpec]
    var decorationSlots: [TemplateDecorationSlotSpec]
    var backgroundTags: [String]
}

struct PhotoFrameSpec: Codable, Equatable {
    var position: CodablePoint
    var size: CodableSize
    var rotationDegrees: Double
    var cornerRadius: Double
}

struct IlluminatedTextSlot: Identifiable, Codable, Equatable {
    var id: UUID
    var slotId: String
    var paperAssetName: String
    var title: String?
    var body: String
    var position: CodablePoint
    var size: CodableSize
    var rotationDegrees: Double
    var fontStyle: IlluminatedFontStyle
}

struct DecorationPlacement: Identifiable, Codable, Equatable {
    var id: UUID
    var assetName: String
    var kind: IlluminationAssetKind
    var position: CodablePoint
    var size: CodableSize
    var rotationDegrees: Double
    var opacity: Double
}

struct IlluminatedCompositionPlan: Codable, Equatable {
    var templateId: IlluminatedTemplateID
    var assetPackId: String
    var randomSeed: Int
    var canvasSize: CodableSize
    var photoFrame: PhotoFrameSpec
    var photoTreatment: PhotoTreatment
    var textSlots: [IlluminatedTextSlot]
    var decorations: [DecorationPlacement]
    var backgroundAssetName: String
    var textureOverlayNames: [String]
}

struct IlluminatedPhotoDraft: Identifiable, Codable, Equatable {
    var id: UUID
    var assetLocalIdentifier: String
    var sourceAssetName: String
    var analysis: PhotoAnalysis
    var compositionPlan: IlluminatedCompositionPlan
    var renderedPreviewPath: String
    var status: IlluminatedPageStatus
    var createdAt: Date
    var updatedAt: Date
}

enum FakePhotoIlluminationAnalyzer {
    static func analyze(assetName: String) -> PhotoAnalysis {
        PhotoAnalysis.academyFallback
    }

    static func analyze(illustration plate: LabyrinthIllustrationPlate) -> PhotoAnalysis {
        let loweredTags = plate.tags.map { $0.lowercased() }
        let profile = BookReferenceCatalog.characterIllustrationProfile(id: plate.characterID)
        let template: IlluminatedTemplateID
        if profile != nil {
            template = .academyFieldStudy
        } else if loweredTags.contains("weather") || loweredTags.contains("harbor") {
            template = .harborFieldNote
        } else if loweredTags.contains("watch") || loweredTags.contains("witness") || loweredTags.contains("page-light") {
            template = .restAndQuiet
        } else {
            template = .academyFieldStudy
        }

        let motifs = Array((["illustration"] + (profile == nil ? [] : ["character"]) + loweredTags).prefix(6))
        let titleWords = plate.title
            .split(separator: " ")
            .prefix(3)
            .joined(separator: " ")
        let fieldNote = profile.map { "The Labyrinth filed \($0.characterName) as a living dossier." } ?? "The Labyrinth filed a witness."
        let closingLine = profile == nil
            ? "The Book kept the page: image listened."
            : "The Book kept the page: portrait, note, and name braided together."
        let souvenir = profile.map { "A character portrait of \($0.characterName) became reusable evidence for the Book of You." }
            ?? "A bundled illustration became evidence from the story side."

        return PhotoAnalysisValidator.validate(
            PhotoAnalysis(
                scene: plate.caption,
                motifs: motifs,
                mood: profile == nil
                    ? (loweredTags.contains("weather") ? "watchful weather" : "ink and quiet")
                    : "academy dossier",
                suggestedTemplate: template,
                marginalia: PhotoMarginalia(
                    fieldNote: fieldNote,
                    stampLabel: titleWords.isEmpty ? "Field Plate" : titleWords,
                    observationList: [
                        "Ink kept its post",
                        "Color held the doorway",
                        "Margins stayed awake",
                        "The plate watched back",
                        "Story light lingered"
                    ],
                    closingLine: closingLine
                ),
                souvenirCandidates: [
                    "The Labyrinth left a picture where the day could find it.",
                    souvenir
                ]
            ),
            fallback: .academyFallback
        )
    }
}

extension PhotoAnalysis {
    static func fromSurfaceMetadata(_ metadata: [String: String], fallback: PhotoAnalysis) -> PhotoAnalysis {
        let observations = metadata["observations"]?
            .components(separatedBy: " | ")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let souvenirs = metadata["souvenirs"]?
            .components(separatedBy: " | ")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let motifs = metadata["motifs"]?
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let template = metadata["template"].flatMap(IlluminatedTemplateID.init(rawValue:)) ?? fallback.suggestedTemplate

        return PhotoAnalysisValidator.validate(
            PhotoAnalysis(
                scene: metadata["scene"] ?? fallback.scene,
                motifs: motifs ?? fallback.motifs,
                mood: metadata["mood"] ?? fallback.mood,
                suggestedTemplate: template,
                marginalia: PhotoMarginalia(
                    fieldNote: metadata["fieldNote"] ?? fallback.marginalia.fieldNote,
                    stampLabel: metadata["stampLabel"] ?? metadata["headline"] ?? fallback.marginalia.stampLabel,
                    observationList: observations ?? fallback.marginalia.observationList,
                    closingLine: metadata["closingLine"] ?? fallback.marginalia.closingLine
                ),
                souvenirCandidates: souvenirs ?? fallback.souvenirCandidates
            ),
            fallback: fallback
        )
    }

    static let academyFallback = PhotoAnalysis(
        scene: "An ordinary scene waits to be catalogued.",
        motifs: ["ordinary", "detail", "field", "study"],
        mood: "curious and kept",
        suggestedTemplate: .academyFieldStudy,
        marginalia: PhotoMarginalia(
            fieldNote: "The ordinary requested documentation.",
            stampLabel: "Field Study",
            observationList: [
                "One detail, clearly volunteering",
                "Light making its argument",
                "Color holding its ground",
                "Texture refusing to vanish",
                "The scene, still available"
            ],
            closingLine: "The Book kept the page: detail spoke."
        ),
        souvenirCandidates: [
            "One ordinary detail stood up and became evidence.",
            "The scene waited patiently to be noticed."
        ]
    )

    static let goodCompanyFallback = PhotoAnalysis(
        scene: "Good company appears close to the camera.",
        motifs: ["company", "smile", "day", "kept"],
        mood: "warm and bright",
        suggestedTemplate: .goodCompany,
        marginalia: PhotoMarginalia(
            fieldNote: "Good company, plainly glowing.",
            stampLabel: "Joy Census",
            observationList: [
                "Two smiles, fully present",
                "Light doing friendly work",
                "Glasses catching the day",
                "Jackets keeping their post",
                "Background politely blurred"
            ],
            closingLine: "The Book kept the page: company stayed."
        ),
        souvenirCandidates: [
            "The day held still long enough for good company.",
            "Two smiles made the background less important."
        ]
    )

    static let harborFallback = PhotoAnalysis(
        scene: "A harbor scene sits under open sky.",
        motifs: ["harbor", "water", "sky", "dock"],
        mood: "salt and light",
        suggestedTemplate: .harborFieldNote,
        marginalia: PhotoMarginalia(
            fieldNote: "The harbor kept its minutes.",
            stampLabel: "Dockside Census",
            observationList: [
                "Water holding small weather",
                "Masts writing thin lines",
                "Dock boards keeping watch",
                "Sky spread wide open",
                "Boats waiting without complaint"
            ],
            closingLine: "The Book kept the page: tide waited."
        ),
        souvenirCandidates: [
            "The harbor arranged its small evidence in plain sight.",
            "The water held the day without asking why."
        ]
    )
}

enum PhotoAnalysisValidator {
    static func decodeAndValidate(_ raw: String, fallback: PhotoAnalysis = .academyFallback) -> PhotoAnalysis {
        guard let json = extractJSONObject(from: raw),
              let data = json.data(using: .utf8) else {
            return fallback
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        guard let decoded = try? decoder.decode(PhotoAnalysis.self, from: data) else {
            return fallback
        }

        return validate(decoded, fallback: fallback)
    }

    static func validate(_ analysis: PhotoAnalysis, fallback: PhotoAnalysis = .academyFallback) -> PhotoAnalysis {
        let scene = sanitizedSentence(analysis.scene, maxCharacters: 160, fallback: fallback.scene)
        let motifs = sanitizedMotifs(analysis.motifs, fallback: fallback.motifs)
        let mood = cappedWords(analysis.mood, maxWords: 3, maxCharacters: 32, fallback: fallback.mood)

        let fieldNote = cappedWords(analysis.marginalia.fieldNote, maxWords: 8, maxCharacters: 72, fallback: fallback.marginalia.fieldNote)
        let stampLabel = cappedWords(analysis.marginalia.stampLabel, maxWords: 3, maxCharacters: 24, fallback: fallback.marginalia.stampLabel)
        let observations = exactly(
            analysis.marginalia.observationList.map { cappedWords($0, maxWords: 6, maxCharacters: 54, fallback: "") },
            count: 5,
            fallback: fallback.marginalia.observationList
        )
        let closing = closingLine(analysis.marginalia.closingLine, fallback: fallback.marginalia.closingLine)
        let souvenirs = exactly(
            analysis.souvenirCandidates.map { cappedWords($0, maxWords: 16, maxCharacters: 120, fallback: "") },
            count: 2,
            fallback: fallback.souvenirCandidates
        )

        return PhotoAnalysis(
            scene: scrubNames(scene),
            motifs: motifs,
            mood: scrubNames(mood),
            suggestedTemplate: analysis.suggestedTemplate,
            marginalia: PhotoMarginalia(
                fieldNote: scrubNames(fieldNote),
                stampLabel: scrubNames(stampLabel),
                observationList: observations.map(scrubNames),
                closingLine: scrubNames(closing)
            ),
            souvenirCandidates: souvenirs.map(scrubNames)
        )
    }

    private static func extractJSONObject(from raw: String) -> String? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.hasPrefix("{"), trimmed.hasSuffix("}") {
            return trimmed
        }
        guard let start = trimmed.firstIndex(of: "{"),
              let end = trimmed.lastIndex(of: "}"),
              start <= end else {
            return nil
        }
        return String(trimmed[start...end])
    }

    private static func sanitizedSentence(_ value: String, maxCharacters: Int, fallback: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return fallback }
        return String(trimmed.prefix(maxCharacters))
    }

    private static func sanitizedMotifs(_ values: [String], fallback: [String]) -> [String] {
        var motifs = values
            .map { $0.lowercased().filter { $0.isLetter || $0.isNumber } }
            .filter { !$0.isEmpty }
        for item in fallback where motifs.count < 3 {
            if !motifs.contains(item) { motifs.append(item) }
        }
        return Array(motifs.prefix(5))
    }

    private static func cappedWords(_ value: String, maxWords: Int, maxCharacters: Int, fallback: String) -> String {
        let words = value
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .split(separator: " ")
            .prefix(maxWords)
            .joined(separator: " ")
        let capped = String(words.prefix(maxCharacters)).trimmingCharacters(in: .whitespacesAndNewlines)
        return capped.isEmpty ? fallback : capped
    }

    private static func closingLine(_ value: String, fallback: String) -> String {
        let capped = cappedWords(value, maxWords: 10, maxCharacters: 96, fallback: fallback)
        if capped.localizedCaseInsensitiveContains("The Book kept") {
            return capped
        }
        return fallback
    }

    private static func exactly(_ values: [String], count: Int, fallback: [String]) -> [String] {
        var output = values.filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        for item in fallback where output.count < count {
            output.append(item)
        }
        return Array(output.prefix(count))
    }

    private static func scrubNames(_ value: String) -> String {
        let blocked = ["Amanda", "BJ", "B.J.", "Brian", "Penny Blackletter"]
        return blocked.reduce(value) { partial, name in
            partial.replacingOccurrences(of: name, with: "the subject", options: [.caseInsensitive])
        }
    }
}

enum CoreMarginsPack {
    static let id = "core-margins"

    static let pack = IlluminationAssetPack(
        id: id,
        displayName: "Core Margins Pack",
        version: "1.0",
        author: "The Book",
        availability: .bundledFree,
        supportedTemplates: IlluminatedTemplateID.allCases,
        backgrounds: [
            asset("parchment_portrait_01", "ParchmentTexture", .background, ["parchment", "portrait", "generic"]),
            asset("parchment_landscape_01", "ParchmentTexture", .background, ["parchment", "landscape", "generic"])
        ],
        paperScraps: [
            asset("illumination_blank_summary", "IlluminationScrapS02_06", .paperScrap, ["scrap", "wide", "blank", "generic"]),
            asset("illumination_blank_date", "IlluminationScrapS02_08", .paperScrap, ["scrap", "wide", "blank", "field"]),
            asset("illumination_blank_field", "IlluminationScrapS03_04", .paperScrap, ["scrap", "wide", "blank", "field"]),
            asset("illumination_blank_torn", "IlluminationScrapS03_11", .paperScrap, ["scrap", "torn", "blank", "map"]),
            asset("illumination_blank_label", "IlluminationScrapS03_25", .paperScrap, ["label", "blank", "ticket"]),
            asset("scrap_note_torn_01", "ParchmentFiber", .paperScrap, ["scrap", "torn", "generic"]),
            asset("scrap_note_torn_02", "ParchmentTexture", .paperScrap, ["scrap", "torn", "generic"]),
            asset("scrap_note_wide_01", "ParchmentFiber", .paperScrap, ["scrap", "wide", "generic"]),
            asset("scrap_note_narrow_01", "ParchmentTexture", .paperScrap, ["scrap", "narrow", "generic"]),
            asset("scrap_label_01", "ParchmentFiber", .paperScrap, ["label", "generic"]),
            asset("scrap_label_pink_01", "MarginaliaSeal", .paperScrap, ["label", "pink", "stamp"])
        ],
        stamps: [
            asset("illumination_wonder_observatory", "IlluminationScrapS01_17", .stamp, ["bee", "wonder", "stamp", "round"]),
            asset("illumination_library_possibilities", "IlluminationScrapS01_24", .stamp, ["book", "library", "stamp", "round"]),
            asset("illumination_witness_ordinary", "IlluminationScrapS02_15", .stamp, ["bee", "ordinary", "stamp", "round"]),
            asset("illumination_library_acquired", "IlluminationScrapS02_18", .stamp, ["library", "archive", "stamp", "label"]),
            asset("illumination_keep_moment", "IlluminationScrapS02_24", .stamp, ["memory", "moment", "stamp", "label"]),
            asset("illumination_luna_moth", "IlluminationScrapS03_18", .stamp, ["moth", "night", "stamp", "postage"]),
            asset("illumination_passage_ticket", "IlluminationScrapS03_23", .stamp, ["ticket", "wonder", "stamp", "label"]),
            asset("illumination_astrolabe_stamp", "IlluminationScrapS03_24", .stamp, ["compass", "star", "stamp", "round"]),
            asset("stamp_academy_bee", "MarginaliaStamp", .stamp, ["bee", "academy", "generic"]),
            asset("stamp_margin_glass", "MarginaliaSeal", .stamp, ["margin", "glass", "generic"]),
            asset("stamp_field_note", "MarginaliaScrap", .stamp, ["field", "note", "generic"]),
            asset("stamp_pawlogy", "MarginaliaStamp", .stamp, ["paw", "creature"]),
            asset("stamp_west_write", "MarginaliaCompass", .stamp, ["compass", "west"])
        ],
        doodles: [
            asset("illumination_lighthouse_01", "IlluminationScrapS01_01", .doodle, ["lighthouse", "harbor", "light"]),
            asset("illumination_living_story", "IlluminationScrapS01_02", .doodle, ["story", "book", "marginalia"]),
            asset("illumination_field_note_harbor", "IlluminationScrapS01_03", .doodle, ["field", "harbor", "marginalia"]),
            asset("illumination_map_unseen", "IlluminationScrapS01_04", .doodle, ["map", "compass", "marginalia"]),
            asset("illumination_noticing_magic", "IlluminationScrapS01_05", .doodle, ["wonder", "notice", "botanical", "marginalia"]),
            asset("illumination_handle_curiosity", "IlluminationScrapS01_06", .doodle, ["tag", "curiosity", "marginalia"]),
            asset("illumination_field_tag", "IlluminationScrapS01_07", .doodle, ["tag", "botanical", "marginalia"]),
            asset("illumination_belief_margin", "IlluminationScrapS01_08", .doodle, ["belief", "feather", "marginalia"]),
            asset("illumination_observation_small", "IlluminationScrapS01_09", .doodle, ["observation", "water", "harbor", "marginalia"]),
            asset("illumination_inkwell", "IlluminationScrapS01_10", .doodle, ["ink", "write", "marginalia"]),
            asset("illumination_kept_tide", "IlluminationScrapS01_11", .doodle, ["book", "tide", "marginalia"]),
            asset("illumination_reported_small", "IlluminationScrapS01_12", .doodle, ["notice", "small", "marginalia"]),
            asset("illumination_memory_ink", "IlluminationScrapS01_13", .doodle, ["ink", "memory", "marginalia"]),
            asset("illumination_found_margins", "IlluminationScrapS01_14", .doodle, ["found", "margin", "marginalia"]),
            asset("illumination_letters_margins", "IlluminationScrapS01_15", .doodle, ["letter", "margin", "marginalia"]),
            asset("illumination_waiting_page", "IlluminationScrapS01_16", .doodle, ["page", "patient", "marginalia"]),
            asset("illumination_gathering_meaning", "IlluminationScrapS01_18", .doodle, ["quiet", "meaning", "marginalia"]),
            asset("illumination_lanterns_lit", "IlluminationScrapS01_19", .doodle, ["light", "story", "marginalia"]),
            asset("illumination_frame_attention", "IlluminationScrapS01_20", .doodle, ["photo", "attention", "marginalia"]),
            asset("illumination_lavender_stamp", "IlluminationScrapS01_21", .doodle, ["lavender", "botanical", "rest"]),
            asset("illumination_compass_reminder", "IlluminationScrapS01_22", .doodle, ["compass", "walk", "marginalia"]),
            asset("illumination_thyme_stamp", "IlluminationScrapS01_23", .doodle, ["botanical", "home"]),
            asset("illumination_map_fragment", "IlluminationScrapS01_25", .doodle, ["map", "compass"]),
            asset("illumination_moth_ticket", "IlluminationScrapS01_26", .doodle, ["moth", "ticket", "night"]),
            asset("illumination_interrupt_usual", "IlluminationScrapS01_27", .doodle, ["wonder", "ordinary", "marginalia"]),
            asset("illumination_quiet_pages", "IlluminationScrapS01_28", .doodle, ["quiet", "book", "marginalia"]),
            asset("illumination_lighthouse_02", "IlluminationScrapS02_01", .doodle, ["lighthouse", "harbor", "light"]),
            asset("illumination_pressed_fern", "IlluminationScrapS02_02", .doodle, ["botanical", "green", "tag"]),
            asset("illumination_small_astonishments", "IlluminationScrapS02_04", .doodle, ["small", "wonder", "marginalia"]),
            asset("illumination_lamp_remembered", "IlluminationScrapS02_05", .doodle, ["lamp", "light", "memory"]),
            asset("illumination_world_light", "IlluminationScrapS02_07", .doodle, ["light", "world", "marginalia"]),
            asset("illumination_observer_desk", "IlluminationScrapS02_09", .doodle, ["observer", "label", "marginalia"]),
            asset("illumination_curiosity_ticket", "IlluminationScrapS02_10", .doodle, ["ticket", "curiosity"]),
            asset("illumination_patient_day", "IlluminationScrapS02_11", .doodle, ["map", "day", "marginalia"]),
            asset("illumination_brown_feather", "IlluminationScrapS02_12", .doodle, ["feather", "brown"]),
            asset("illumination_ordinary_wonder", "IlluminationScrapS02_13", .doodle, ["ordinary", "wonder", "botanical"]),
            asset("illumination_moss_return", "IlluminationScrapS02_14", .doodle, ["moss", "green", "home"]),
            asset("illumination_daylight_missed", "IlluminationScrapS02_16", .doodle, ["light", "margin", "marginalia"]),
            asset("illumination_moon_strip", "IlluminationScrapS02_17", .doodle, ["moon", "night"]),
            asset("illumination_dreams_ticket", "IlluminationScrapS02_20", .doodle, ["dreams", "ticket"]),
            asset("illumination_weather_cabinet", "IlluminationScrapS02_26", .doodle, ["weather", "cabinet", "marginalia"]),
            asset("illumination_unannounced", "IlluminationScrapS02_27", .doodle, ["surprise", "arrival", "marginalia"]),
            asset("illumination_moon_row", "IlluminationScrapS03_01", .doodle, ["moon", "night"]),
            asset("illumination_clover_tag", "IlluminationScrapS03_02", .doodle, ["clover", "botanical", "tag"]),
            asset("illumination_library_card", "IlluminationScrapS03_03", .doodle, ["library", "book", "card"]),
            asset("illumination_pale_feather", "IlluminationScrapS03_05", .doodle, ["feather", "soft"]),
            asset("illumination_moon_marker", "IlluminationScrapS03_06", .doodle, ["moon", "night"]),
            asset("illumination_archive_quiet", "IlluminationScrapS03_07", .doodle, ["archive", "quiet", "marginalia"]),
            asset("illumination_flower_card", "IlluminationScrapS03_08", .doodle, ["flower", "botanical"]),
            asset("illumination_study_tag", "IlluminationScrapS03_09", .doodle, ["tag", "study", "moss"]),
            asset("illumination_moth_strip", "IlluminationScrapS03_10", .doodle, ["moth", "strip"]),
            asset("illumination_borrowed_hush", "IlluminationScrapS03_12", .doodle, ["quiet", "hush", "marginalia"]),
            asset("illumination_windy_tag", "IlluminationScrapS03_13", .doodle, ["wind", "tag"]),
            asset("illumination_observed_eye", "IlluminationScrapS03_14", .doodle, ["eye", "observed", "marginalia"]),
            asset("illumination_ink_proof", "IlluminationScrapS03_15", .doodle, ["ink", "attention", "marginalia"]),
            asset("illumination_script_strip", "IlluminationScrapS03_16", .doodle, ["script", "letter"]),
            asset("illumination_constellation", "IlluminationScrapS03_17", .doodle, ["star", "constellation"]),
            asset("illumination_wander_record", "IlluminationScrapS03_19", .doodle, ["wander", "record", "banner"]),
            asset("illumination_edge_remembers", "IlluminationScrapS03_20", .doodle, ["edge", "memory", "marginalia"]),
            asset("illumination_rain_collected", "IlluminationScrapS03_21", .doodle, ["rain", "weather", "botanical"]),
            asset("illumination_margins_speak", "IlluminationScrapS03_22", .doodle, ["margin", "speak", "marginalia"]),
            asset("illumination_field_note_dry", "IlluminationScrapS03_26", .doodle, ["field", "note", "label"]),
            asset("illumination_starlight", "IlluminationScrapS03_27", .doodle, ["star", "light", "marginalia"]),
            asset("illumination_spell_progress", "IlluminationScrapS03_28", .doodle, ["spell", "magic", "marginalia"]),
            asset("doodle_compass_01", "MarginaliaCompass", .doodle, ["compass", "generic"]),
            asset("doodle_feather_01", "MarginaliaFeather", .doodle, ["feather", "generic"]),
            asset("doodle_lavender_01", "MarginaliaLavender", .doodle, ["lavender", "rest"]),
            asset("doodle_shell_01", "MarginaliaShell", .doodle, ["shell", "harbor"]),
            asset("doodle_anchor_01", "MarginaliaCompass", .doodle, ["anchor", "harbor"]),
            asset("doodle_sailboat_01", "MarginaliaCompass", .doodle, ["sailboat", "harbor"]),
            asset("doodle_teacup_01", "MarginaliaScrap", .doodle, ["teacup", "home"]),
            asset("doodle_paw_01", "MarginaliaStar", .doodle, ["paw", "creature"]),
            asset("doodle_star_01", "MarginaliaStar", .doodle, ["star", "generic"]),
            asset("doodle_heart_01", "MarginaliaShell", .doodle, ["heart", "company"])
        ],
        tape: [
            asset("illumination_botanical_tape", "IlluminationScrapS02_03", .tape, ["tape", "botanical", "green"]),
            asset("illumination_fabric_tape", "IlluminationScrapS02_28", .tape, ["tape", "fabric", "generic"]),
            asset("tape_01", "ParchmentFiber", .tape, ["tape", "generic"]),
            asset("tape_02", "ParchmentTexture", .tape, ["tape", "generic"])
        ],
        overlays: [
            asset("overlay_paper_grain_01", "ParchmentFiber", .overlay, ["grain", "generic"], opacity: 0.18),
            asset("overlay_speckles_01", "ParchmentTexture", .overlay, ["speckles", "generic"], opacity: 0.12),
            asset("overlay_edge_vignette_01", "ParchmentTexture", .overlay, ["edge", "vignette", "generic"], opacity: 0.16)
        ],
        fallbackPhrases: [
            .academyFieldStudy: TemplateFallbackPhrases(
                fieldNotes: [PhotoAnalysis.academyFallback.marginalia.fieldNote],
                stampLabels: [PhotoAnalysis.academyFallback.marginalia.stampLabel],
                observations: PhotoAnalysis.academyFallback.marginalia.observationList,
                closingLines: [PhotoAnalysis.academyFallback.marginalia.closingLine]
            )
        ]
    )

    private static func asset(
        _ id: String,
        _ assetName: String,
        _ kind: IlluminationAssetKind,
        _ tags: [String],
        opacity: Double = 0.82
    ) -> IlluminationAsset {
        IlluminationAsset(
            id: id,
            assetName: assetName,
            kind: kind,
            tags: tags,
            supportedTemplates: IlluminatedTemplateID.allCases,
            defaultOpacity: opacity,
            canTint: false
        )
    }
}

struct IlluminationAssetResolver {
    func resolveAsset(
        kind: IlluminationAssetKind,
        tags: [String],
        template: IlluminatedTemplateID,
        installedPacks: [IlluminationAssetPack]
    ) -> IlluminationAsset? {
        let normalizedTags = Set(tags.map { $0.lowercased() })
        let candidates = installedPacks
            .flatMap(\.allAssets)
            .filter { $0.kind == kind && $0.supportedTemplates.contains(template) }

        return candidates.first { asset in
            !normalizedTags.isDisjoint(with: Set(asset.tags.map { $0.lowercased() }))
        } ?? candidates.first { asset in
            asset.tags.contains("generic")
        } ?? candidates.first
    }
}

enum IlluminationPackRegistry {
    static let installedPacks: [IlluminationAssetPack] = [CoreMarginsPack.pack]

    static func packsSupporting(_ template: IlluminatedTemplateID) -> [IlluminationAssetPack] {
        installedPacks.filter { $0.supportedTemplates.contains(template) }
    }

    static func preferredPack(for template: IlluminatedTemplateID, motifs: [String]) -> IlluminationAssetPack {
        packsSupporting(template).first ?? CoreMarginsPack.pack
    }
}

enum IlluminationTemplateLibrary {
    static let academyFieldStudy = IlluminationTemplate(
        id: .academyFieldStudy,
        displayName: "Academy Field Study",
        preferredCanvas: .portrait,
        supportedPhotoOrientations: [.portrait, .landscape, .square],
        defaultPhotoTreatment: .softArchive,
        requiredSlots: [
            TemplateTextSlotSpec(
                id: "field-note",
                contentKey: .fieldNote,
                title: "Field Note",
                position: CodablePoint(x: 120, y: 210),
                size: CodableSize(width: 390, height: 185),
                rotationRange: ClosedDoubleRange(lowerBound: -4, upperBound: 3),
                paperTags: ["scrap", "torn"],
                fontStyle: .handwritten,
                maxLines: 3
            ),
            TemplateTextSlotSpec(
                id: "observation-list",
                contentKey: .observationList,
                title: "Today's Observation",
                position: CodablePoint(x: 330, y: 1165),
                size: CodableSize(width: 520, height: 230),
                rotationRange: ClosedDoubleRange(lowerBound: -2, upperBound: 2),
                paperTags: ["scrap", "wide"],
                fontStyle: .handwritten,
                maxLines: 6
            ),
            TemplateTextSlotSpec(
                id: "closing-line",
                contentKey: .closingLine,
                title: nil,
                position: CodablePoint(x: 890, y: 1088),
                size: CodableSize(width: 280, height: 260),
                rotationRange: ClosedDoubleRange(lowerBound: -3, upperBound: 4),
                paperTags: ["scrap", "narrow"],
                fontStyle: .handwritten,
                maxLines: 5
            )
        ],
        optionalSlots: [
            TemplateTextSlotSpec(
                id: "frame-line",
                contentKey: .fixedFrameLine,
                title: nil,
                position: CodablePoint(x: 390, y: 178),
                size: CodableSize(width: 520, height: 150),
                rotationRange: ClosedDoubleRange(lowerBound: -2, upperBound: 2),
                paperTags: ["scrap", "wide"],
                fontStyle: .handwritten,
                maxLines: 2
            ),
            TemplateTextSlotSpec(
                id: "compass-reminder",
                contentKey: .fixedCompassReminder,
                title: "Compass Reminder",
                position: CodablePoint(x: 900, y: 700),
                size: CodableSize(width: 250, height: 250),
                rotationRange: ClosedDoubleRange(lowerBound: -3, upperBound: 4),
                paperTags: ["scrap", "narrow"],
                fontStyle: .handwritten,
                maxLines: 5
            ),
            TemplateTextSlotSpec(
                id: "souvenir-line",
                contentKey: .souvenirCandidate,
                title: nil,
                position: CodablePoint(x: 110, y: 1010),
                size: CodableSize(width: 310, height: 230),
                rotationRange: ClosedDoubleRange(lowerBound: -5, upperBound: 2),
                paperTags: ["scrap", "torn"],
                fontStyle: .handwritten,
                maxLines: 5
            )
        ],
        decorationSlots: [
            TemplateDecorationSlotSpec(id: "bee-stamp", kind: .stamp, tags: ["bee", "academy"], position: CodablePoint(x: 880, y: 210), size: CodableSize(width: 190, height: 190), rotationRange: ClosedDoubleRange(lowerBound: -5, upperBound: 5), opacityRange: ClosedDoubleRange(lowerBound: 0.24, upperBound: 0.34), required: true),
            TemplateDecorationSlotSpec(id: "compass", kind: .doodle, tags: ["compass"], position: CodablePoint(x: 910, y: 615), size: CodableSize(width: 155, height: 155), rotationRange: ClosedDoubleRange(lowerBound: -8, upperBound: 8), opacityRange: ClosedDoubleRange(lowerBound: 0.42, upperBound: 0.58), required: false),
            TemplateDecorationSlotSpec(id: "feather", kind: .doodle, tags: ["feather"], position: CodablePoint(x: 135, y: 570), size: CodableSize(width: 145, height: 360), rotationRange: ClosedDoubleRange(lowerBound: -10, upperBound: -4), opacityRange: ClosedDoubleRange(lowerBound: 0.34, upperBound: 0.46), required: false),
            TemplateDecorationSlotSpec(id: "star", kind: .doodle, tags: ["star"], position: CodablePoint(x: 1020, y: 1200), size: CodableSize(width: 90, height: 90), rotationRange: ClosedDoubleRange(lowerBound: -12, upperBound: 12), opacityRange: ClosedDoubleRange(lowerBound: 0.26, upperBound: 0.38), required: false),
            TemplateDecorationSlotSpec(id: "lower-stamp", kind: .stamp, tags: ["margin", "glass"], position: CodablePoint(x: 120, y: 1250), size: CodableSize(width: 230, height: 230), rotationRange: ClosedDoubleRange(lowerBound: -4, upperBound: 4), opacityRange: ClosedDoubleRange(lowerBound: 0.32, upperBound: 0.48), required: false),
            TemplateDecorationSlotSpec(id: "botanical", kind: .doodle, tags: ["lavender", "rest"], position: CodablePoint(x: 96, y: 360), size: CodableSize(width: 160, height: 360), rotationRange: ClosedDoubleRange(lowerBound: -4, upperBound: 3), opacityRange: ClosedDoubleRange(lowerBound: 0.28, upperBound: 0.42), required: false)
        ],
        backgroundTags: ["parchment", "portrait"]
    )

    static func template(for id: IlluminatedTemplateID) -> IlluminationTemplate {
        switch id {
        case .academyFieldStudy, .goodCompany, .creatureComfort, .harborFieldNote, .homeVessel, .restAndQuiet:
            return academyFieldStudy
        }
    }
}

struct IlluminationMarginaliaSnippet: Identifiable, Codable, Equatable {
    var id: String
    var text: String
    var title: String?
    var tags: [String]
    var packID: String
    var weight: Double
}

enum IlluminationMarginaliaLibrary {
    static let corePackID = CoreMarginsPack.id

    static let snippets: [IlluminationMarginaliaSnippet] = [
        snippet("living-story", "A living fantasy story woven with your days.", tags: ["story", "book", "ordinary"]),
        snippet("lanterns-lit", "Keep the lanterns lit.\nKeep the story alive.", tags: ["light", "story", "night"]),
        snippet("letters-margins", "Letters travel through the Margins.", tags: ["letter", "margin", "book"]),
        snippet("quiet-pages", "Some pages are quiet.\nThey are listening.", tags: ["quiet", "rest", "book"]),
        snippet("noticing-magic", "Noticing is a kind of magic.", tags: ["wonder", "notice", "ordinary"]),
        snippet("field-small", "Filed under small astonishments.", tags: ["field", "small", "wonder"]),
        snippet("observe-first", "Observe first.\nName later.", tags: ["field", "study", "notice"]),
        snippet("daylight-missed", "Margins hold what daylight missed.", tags: ["light", "margin", "memory"]),
        snippet("ordinary-wonder", "Specimen:\nordinary wonder.", tags: ["ordinary", "study", "wonder"]),
        snippet("small-page-returned", "A small page returned.", tags: ["book", "small", "memory"]),
        snippet("handle-curiosity", "Handle with curiosity.", tags: ["curiosity", "field", "wonder"]),
        snippet("silence-annotate", "Let silence annotate.", tags: ["quiet", "rest", "soft"]),
        snippet("moss-return", "Return to where the moss grows.", tags: ["home", "green", "rest"]),
        snippet("not-all-tracks", "Not all who wander leave tracks.", tags: ["walk", "wild", "story"]),
        snippet("found-margins", "Found in the Margins.", tags: ["margin", "found", "book"]),
        snippet("usual-interrupt", "Let wonder interrupt the usual.", tags: ["wonder", "ordinary", "play"]),
        snippet("waiting-page", "This page was waiting patiently.", tags: ["book", "patient", "memory"]),
        snippet("small-things-story", "Small things become story.", tags: ["small", "story", "ordinary"]),
        snippet("ink-memory", "Ink keeps what memory would forget.", tags: ["ink", "memory", "book"]),
        snippet("weather-cabinet", "For the cabinet of weather.", tags: ["weather", "sky", "soft"]),
        snippet("lamp-remembered", "The lamp remembered for you.", tags: ["light", "night", "home"]),
        snippet("future-note", "A note for future me.", tags: ["memory", "future", "book"]),
        snippet("page-arrived", "Some things arrive unannounced.", tags: ["surprise", "wonder", "story"]),
        snippet("edge-remembers", "This edge remembers.", tags: ["edge", "photo", "memory"]),
        snippet("starlight-noted", "Noted by starlight.", tags: ["night", "light", "quiet"]),
        snippet("paying-attention", "Ink stains are proof of paying attention.", tags: ["ink", "attention", "field"]),
        snippet("north-star", "Follow the north star.", tags: ["compass", "walk", "star"]),
        snippet("gentle-magic", "Handle gently.\nMagic inside.", tags: ["magic", "soft", "care"]),
        snippet("archive-quiet", "Archive of quiet things.", tags: ["quiet", "archive", "rest"]),
        snippet("kept-lantern", "Keep near the lantern.", tags: ["light", "lantern", "night"]),
        snippet("harbor-minutes", "The harbor kept its minutes.", tags: ["harbor", "water", "boat"]),
        snippet("water-weather", "Water holding small weather.", title: "Observation", tags: ["water", "weather", "harbor"]),
        snippet("masts-lines", "Masts writing thin lines.", title: "Observation", tags: ["boat", "harbor", "line"]),
        snippet("dock-watch", "Dock boards keeping watch.", title: "Observation", tags: ["dock", "harbor", "wood"]),
        snippet("soft-authority", "Soft things have authority.", tags: ["creature", "soft", "rest"]),
        snippet("pawlogy", "Pawlogy: rest demonstrated.", tags: ["paw", "creature", "rest"]),
        snippet("good-company", "Good company, plainly glowing.", tags: ["company", "smile", "warm"]),
        snippet("room-museum", "Home made a museum of ordinary things.", tags: ["home", "room", "ordinary"]),
        snippet("quiet-office", "Quiet arrived and took notes.", tags: ["quiet", "rest", "soft"])
    ]

    static func select(motifs: [String], seed: Int, count: Int) -> [IlluminationMarginaliaSnippet] {
        let wantedTags = Set(motifs.map { $0.lowercased() })
        let ranked = snippets.enumerated().map { index, snippet in
            let snippetTags = Set(snippet.tags.map { $0.lowercased() })
            let tagScore = wantedTags.intersection(snippetTags).count
            let jitter = abs((seed &+ index * 7919).hashValue % 1000)
            return (snippet, Double(tagScore) * 10 + snippet.weight + Double(jitter) / 10000)
        }
        return ranked
            .sorted { $0.1 > $1.1 }
            .prefix(count)
            .map(\.0)
    }

    private static func snippet(
        _ id: String,
        _ text: String,
        title: String? = nil,
        tags: [String],
        packID: String = corePackID,
        weight: Double = 1
    ) -> IlluminationMarginaliaSnippet {
        IlluminationMarginaliaSnippet(id: id, text: text, title: title, tags: tags, packID: packID, weight: weight)
    }
}

enum IlluminatedPageComposer {
    static func compose(
        analysis: PhotoAnalysis,
        sourceAssetName: String,
        seed: Int,
        assetLocalIdentifier: String? = nil
    ) -> IlluminatedPhotoDraft {
        let template = IlluminationTemplateLibrary.template(for: analysis.suggestedTemplate)
        let pack = IlluminationPackRegistry.preferredPack(for: template.id, motifs: analysis.motifs)
        let resolver = IlluminationAssetResolver()
        let background = resolver.resolveAsset(kind: .background, tags: template.backgroundTags, template: template.id, installedPacks: [pack])
        let overlays = pack.overlays.map(\.assetName)
        var textSlots = (template.requiredSlots + template.optionalSlots).enumerated().map { offset, spec in
            let body = body(for: spec.contentKey, analysis: analysis)
            let scrap = resolver.resolveAsset(kind: .paperScrap, tags: spec.paperTags, template: template.id, installedPacks: [pack])
            return IlluminatedTextSlot(
                id: UUID(),
                slotId: spec.id,
                paperAssetName: scrap?.assetName ?? "ParchmentFiber",
                title: spec.title,
                body: body,
                position: jittered(spec.position, seed: seed, salt: offset),
                size: spec.size,
                rotationDegrees: spec.rotationRange.value(seed: seed, salt: offset),
                fontStyle: spec.fontStyle
            )
        }
        textSlots.append(contentsOf: extraMarginaliaSlots(
            analysis: analysis,
            seed: seed,
            resolver: resolver,
            template: template.id,
            pack: pack
        ))
        var decorations = template.decorationSlots.enumerated().compactMap { offset, slot -> DecorationPlacement? in
            guard let asset = resolver.resolveAsset(kind: slot.kind, tags: slot.tags + analysis.motifs, template: template.id, installedPacks: [pack]) else {
                return slot.required ? DecorationPlacement(id: UUID(), assetName: "MarginaliaStar", kind: slot.kind, position: slot.position, size: slot.size, rotationDegrees: 0, opacity: 0.24) : nil
            }
            return DecorationPlacement(
                id: UUID(),
                assetName: asset.assetName,
                kind: slot.kind,
                position: jittered(slot.position, seed: seed, salt: offset + 41),
                size: slot.size,
                rotationDegrees: slot.rotationRange.value(seed: seed, salt: offset + 41),
                opacity: slot.opacityRange.value(seed: seed, salt: offset + 71)
            )
        }
        decorations.append(contentsOf: extraDecorationSlots(
            analysis: analysis,
            seed: seed,
            resolver: resolver,
            template: template.id,
            pack: pack
        ))
        let plan = IlluminatedCompositionPlan(
            templateId: template.id,
            assetPackId: pack.id,
            randomSeed: seed,
            canvasSize: CodableSize(width: 1290, height: 1800),
            photoFrame: PhotoFrameSpec(
                position: CodablePoint(x: 210, y: 280),
                size: CodableSize(width: 870, height: 1010),
                rotationDegrees: ClosedDoubleRange(lowerBound: -1.2, upperBound: 1.2).value(seed: seed, salt: 99),
                cornerRadius: 18
            ),
            photoTreatment: template.defaultPhotoTreatment,
            textSlots: textSlots,
            decorations: decorations,
            backgroundAssetName: background?.assetName ?? "ParchmentTexture",
            textureOverlayNames: overlays
        )
        let now = Date()
        return IlluminatedPhotoDraft(
            id: UUID(),
            assetLocalIdentifier: assetLocalIdentifier ?? "bundled:\(sourceAssetName)",
            sourceAssetName: sourceAssetName,
            analysis: analysis,
            compositionPlan: plan,
            renderedPreviewPath: "",
            status: .proposed,
            createdAt: now,
            updatedAt: now
        )
    }

    private static func body(for key: MarginaliaContentKey, analysis: PhotoAnalysis) -> String {
        switch key {
        case .fieldNote:
            return analysis.marginalia.fieldNote
        case .stampLabel:
            return analysis.marginalia.stampLabel
        case .observationList:
            return analysis.marginalia.observationList.enumerated().map { "\($0.offset + 1). \($0.element)" }.joined(separator: "\n")
        case .closingLine:
            return analysis.marginalia.closingLine
        case .souvenirCandidate:
            return analysis.souvenirCandidates.first ?? ""
        case .fixedCompassReminder:
            return "Walk. Notice. Record. Return. Repeat."
        case .fixedFrameLine:
            return "The frame is fictional.\nThe attention is real."
        }
    }

    private static func jittered(_ point: CodablePoint, seed: Int, salt: Int) -> CodablePoint {
        let dx = ClosedDoubleRange(lowerBound: -10, upperBound: 10).value(seed: seed, salt: salt)
        let dy = ClosedDoubleRange(lowerBound: -8, upperBound: 8).value(seed: seed, salt: salt + 13)
        return CodablePoint(x: point.x + dx, y: point.y + dy)
    }

    private static func extraMarginaliaSlots(
        analysis: PhotoAnalysis,
        seed: Int,
        resolver: IlluminationAssetResolver,
        template: IlluminatedTemplateID,
        pack: IlluminationAssetPack
    ) -> [IlluminatedTextSlot] {
        let anchors = [
            (CodablePoint(x: 95, y: 785), CodableSize(width: 280, height: 190), ClosedDoubleRange(lowerBound: -7, upperBound: -2)),
            (CodablePoint(x: 780, y: 130), CodableSize(width: 340, height: 150), ClosedDoubleRange(lowerBound: 1, upperBound: 5)),
            (CodablePoint(x: 940, y: 470), CodableSize(width: 230, height: 230), ClosedDoubleRange(lowerBound: -4, upperBound: 4)),
            (CodablePoint(x: 140, y: 1340), CodableSize(width: 300, height: 190), ClosedDoubleRange(lowerBound: -5, upperBound: 2)),
            (CodablePoint(x: 810, y: 1375), CodableSize(width: 310, height: 190), ClosedDoubleRange(lowerBound: 2, upperBound: 7)),
            (CodablePoint(x: 500, y: 1020), CodableSize(width: 320, height: 150), ClosedDoubleRange(lowerBound: -3, upperBound: 3))
        ]
        let snippets = IlluminationMarginaliaLibrary.select(motifs: analysis.motifs, seed: seed, count: 3)
        return snippets.enumerated().map { offset, snippet in
            let anchor = anchors[abs((seed + offset * 17).hashValue) % anchors.count]
            let scrap = resolver.resolveAsset(kind: .paperScrap, tags: ["scrap", offset.isMultiple(of: 2) ? "torn" : "wide"], template: template, installedPacks: [pack])
            return IlluminatedTextSlot(
                id: UUID(),
                slotId: "marginalia-\(snippet.id)",
                paperAssetName: scrap?.assetName ?? "ParchmentFiber",
                title: snippet.title,
                body: snippet.text,
                position: jittered(anchor.0, seed: seed, salt: 401 + offset * 29, x: 26, y: 22),
                size: anchor.1,
                rotationDegrees: anchor.2.value(seed: seed, salt: 511 + offset),
                fontStyle: .handwritten
            )
        }
    }

    private static func extraDecorationSlots(
        analysis: PhotoAnalysis,
        seed: Int,
        resolver: IlluminationAssetResolver,
        template: IlluminatedTemplateID,
        pack: IlluminationAssetPack
    ) -> [DecorationPlacement] {
        let slots = [
            (["tape"], IlluminationAssetKind.tape, CodablePoint(x: 235, y: 184), CodableSize(width: 150, height: 48), 0.32),
            (["tape"], IlluminationAssetKind.tape, CodablePoint(x: 940, y: 1230), CodableSize(width: 130, height: 44), 0.30),
            (["shell", "harbor"], IlluminationAssetKind.doodle, CodablePoint(x: 1000, y: 1415), CodableSize(width: 118, height: 118), 0.42),
            (["heart", "company"], IlluminationAssetKind.doodle, CodablePoint(x: 1040, y: 1040), CodableSize(width: 80, height: 80), 0.34),
            (["marginalia"], IlluminationAssetKind.doodle, CodablePoint(x: 95, y: 420), CodableSize(width: 245, height: 170), 0.76),
            (["marginalia"], IlluminationAssetKind.doodle, CodablePoint(x: 850, y: 330), CodableSize(width: 260, height: 175), 0.70),
            (["stamp"], IlluminationAssetKind.stamp, CodablePoint(x: 930, y: 150), CodableSize(width: 170, height: 170), 0.40),
            (["botanical"], IlluminationAssetKind.doodle, CodablePoint(x: 95, y: 1160), CodableSize(width: 130, height: 300), 0.48),
            (["tag"], IlluminationAssetKind.doodle, CodablePoint(x: 1010, y: 765), CodableSize(width: 150, height: 230), 0.66)
        ]
        return slots.enumerated().compactMap { offset, slot in
            guard let asset = pickAsset(
                kind: slot.1,
                tags: slot.0 + analysis.motifs,
                template: template,
                pack: pack,
                seed: seed,
                salt: 811 + offset * 37
            ) ?? resolver.resolveAsset(kind: slot.1, tags: slot.0 + analysis.motifs, template: template, installedPacks: [pack]) else {
                return nil
            }
            return DecorationPlacement(
                id: UUID(),
                assetName: asset.assetName,
                kind: slot.1,
                position: jittered(slot.2, seed: seed, salt: 701 + offset * 31, x: 22, y: 18),
                size: slot.3,
                rotationDegrees: ClosedDoubleRange(lowerBound: -12, upperBound: 12).value(seed: seed, salt: 733 + offset),
                opacity: slot.4
            )
        }
    }

    private static func pickAsset(
        kind: IlluminationAssetKind,
        tags: [String],
        template: IlluminatedTemplateID,
        pack: IlluminationAssetPack,
        seed: Int,
        salt: Int
    ) -> IlluminationAsset? {
        let normalizedTags = Set(tags.map { $0.lowercased() })
        let matches = pack.allAssets.filter { asset in
            asset.kind == kind
                && asset.supportedTemplates.contains(template)
                && !normalizedTags.isDisjoint(with: Set(asset.tags.map { $0.lowercased() }))
        }
        guard !matches.isEmpty else {
            return nil
        }
        let index = abs((seed &+ salt * 7919).hashValue) % matches.count
        return matches[index]
    }

    private static func jittered(_ point: CodablePoint, seed: Int, salt: Int, x: Double, y: Double) -> CodablePoint {
        let dx = ClosedDoubleRange(lowerBound: -x, upperBound: x).value(seed: seed, salt: salt)
        let dy = ClosedDoubleRange(lowerBound: -y, upperBound: y).value(seed: seed, salt: salt + 13)
        return CodablePoint(x: point.x + dx, y: point.y + dy)
    }
}

struct IlluminatedPhotoQueue {
    var candidates: [PhotoCandidate] = []
    var history = IlluminatedPhotoHistory()

    mutating func nextCandidate() -> PhotoCandidate? {
        candidates.first {
            !history.keptAssetIdentifiers.contains($0.assetLocalIdentifier)
                && !history.dismissedAssetIdentifiers.contains($0.assetLocalIdentifier)
        }
    }

    mutating func markProposed(_ candidate: PhotoCandidate, at date: Date = Date()) {
        history.proposedAssetIdentifiers.insert(candidate.assetLocalIdentifier)
        history.lastSuggestedAtByAsset[candidate.assetLocalIdentifier] = date
    }

    mutating func markKept(assetLocalIdentifier: String) {
        history.keptAssetIdentifiers.insert(assetLocalIdentifier)
    }

    mutating func markDismissed(assetLocalIdentifier: String) {
        history.dismissedAssetIdentifiers.insert(assetLocalIdentifier)
    }
}

struct IlluminatedPhotoPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .illuminatedPhoto)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard !context.distress.isActive else { return [] }
        if let prepared = inputs.preparedIlluminatedPhotoSurface,
           prepared.payload.metadata["renderedPreviewPath"]?.isEmpty == false {
            return [prepared]
        }
        guard inputs.userPhotoIlluminationFallbackAllowed else { return [] }
        let plate = BookReferenceCatalog.labyrinthIllustration(for: day, now: now)
        guard !plate.assetName.isEmpty else { return [] }
        let slot = SurfaceCadence.slotID(for: now, hours: 4)
        let analysis = FakePhotoIlluminationAnalyzer.analyze(illustration: plate)
        let draft = IlluminatedPageComposer.compose(
            analysis: analysis,
            sourceAssetName: plate.assetName,
            seed: abs("\(day.id)-\(plate.assetName)-illuminated-\(slot)".hashValue),
            assetLocalIdentifier: "bundled-illustration:\(plate.id)"
        )
        return [
            SurfacePage(
                id: "\(source.id)-illustration-\(plate.id)-\(slot)",
                type: .illuminatedPhoto,
                sourceID: source.id,
                intent: .resurface,
                renderStyle: .illuminatedPhoto,
                score: 70,
                reason: "The Labyrinth left an illustration with ink on it.",
                prompt: "Illuminated from the Labyrinth",
                detail: "A bundled illustration passed through Penny's press.",
                payload: BookPagePayload(
                    headline: draft.analysis.marginalia.stampLabel,
                    body: "\(plate.caption)\n\n\(draft.analysis.marginalia.closingLine)",
                    metadata: [
                        "source": source.id,
                        "sourceAssetName": draft.sourceAssetName,
                        "template": draft.compositionPlan.templateId.rawValue,
                        "assetPack": draft.compositionPlan.assetPackId,
                        "status": draft.status.rawValue,
                        "privacy": "bundled local illustration",
                        "fieldNote": draft.analysis.marginalia.fieldNote,
                        "observations": draft.analysis.marginalia.observationList.joined(separator: " | "),
                        "closingLine": draft.analysis.marginalia.closingLine,
                        "scene": draft.analysis.scene,
                        "motifs": draft.analysis.motifs.joined(separator: ","),
                        "souvenirs": draft.analysis.souvenirCandidates.joined(separator: " | "),
                        "plateID": plate.id,
                        "tags": plate.tags.joined(separator: ",")
                    ]
                )
            )
        ]
    }
}

struct DistressSignals: Equatable {
    var isActive: Bool
    var reasons: [String]

    static func evaluate(day: BookDay) -> DistressSignals {
        let distressTags: Set<String> = [
            "distress", "hard", "heavy", "low", "numb", "stormy", "depleted", "grief", "panic"
        ]
        var reasons: [String] = []

        for page in day.capturedPages {
            let loweredTags = Set(page.tags.map { $0.lowercased() })
            if !loweredTags.isDisjoint(with: distressTags) {
                reasons.append("\(page.type.shortTitle) carried a hard tag")
                continue
            }

            let loweredInput = page.userInput.lowercased()
            if loweredInput.contains("panic")
                || loweredInput.contains("depressed")
                || loweredInput.contains("hopeless")
                || loweredInput.contains("can't do this")
                || loweredInput.contains("cannot do this") {
                reasons.append("\(page.type.shortTitle) carried a hard phrase")
            }
        }

        return DistressSignals(isActive: !reasons.isEmpty, reasons: reasons)
    }
}

struct BleedTranslation: Equatable {
    var dayShape: String
    var pageBias: [BookPageType]
    var atmosphereLine: String
    var forbiddenOffers: [String]

    static let neutral = BleedTranslation(
        dayShape: "ordinary",
        pageBias: [.mood, .souvenir, .rest],
        atmosphereLine: "The margins are awake and listening.",
        forbiddenOffers: []
    )

    static let shelter = BleedTranslation(
        dayShape: "shelter",
        pageBias: [.rest, .mood, .souvenir],
        atmosphereLine: "The Book has lowered the lamps; the day asked for gentleness.",
        forbiddenOffers: ["long_embark", "high_energy_challenge", "step_back_offer"]
    )
}

enum BleedTranslator {
    static func translate(distress: DistressSignals) -> BleedTranslation {
        distress.isActive ? .shelter : .neutral
    }
}

struct StepBackEligibility: Equatable {
    var canOfferHalfOpenBook: Bool
    var reasons: [String]

    static func evaluate(recentDays: [BookDay], distress: DistressSignals) -> StepBackEligibility {
        guard !distress.isActive else {
            return StepBackEligibility(
                canOfferHalfOpenBook: false,
                reasons: ["The Book never offers stepping back from a hard or ambiguous place."]
            )
        }

        let recentCapturedPages = recentDays.flatMap(\.capturedPages)
        let unpromptedWonderCount = recentCapturedPages.filter { page in
            page.type == .souvenir && page.tags.contains { $0.lowercased() == "unprompted" }
        }.count

        guard unpromptedWonderCount >= 3 else {
            return StepBackEligibility(
                canOfferHalfOpenBook: false,
                reasons: ["The half-open-book ritual waits for sustained unprompted wonder."]
            )
        }

        return StepBackEligibility(
            canOfferHalfOpenBook: true,
            reasons: ["Sustained unprompted wonder is present and no distress signal is active."]
        )
    }
}

struct CuratorContext: Equatable {
    var distress: DistressSignals
    var bleed: BleedTranslation
    var stepBack: StepBackEligibility

    static func make(for day: BookDay, recentDays: [BookDay]? = nil) -> CuratorContext {
        let distress = DistressSignals.evaluate(day: day)
        return CuratorContext(
            distress: distress,
            bleed: BleedTranslator.translate(distress: distress),
            stepBack: StepBackEligibility.evaluate(
                recentDays: recentDays ?? [day],
                distress: distress
            )
        )
    }
}

struct BodySourceSignal: Equatable {
    struct Metric: Codable, Equatable, Identifiable {
        var id: String
        var label: String
        var value: String
        var unit: String
        var kind: String
        var observedAt: Date?

        init(id: String, label: String, value: String, unit: String = "", kind: String = "quantity", observedAt: Date? = nil) {
            self.id = id
            self.label = label
            self.value = value
            self.unit = unit
            self.kind = kind
            self.observedAt = observedAt
        }

        var displayText: String {
            [label, value, unit].filter { !$0.isEmpty }.joined(separator: " ")
        }
    }

    var status: String
    var score: Int
    var phrase: String
    var metrics: [Metric] = []

    var isAvailable: Bool {
        !phrase.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

struct WeatherSourceSignal: Equatable {
    var phrase: String
    var source: String
    var currentTemperature: String?
    var forecast: String?
    var conditionSymbolName: String

    var isAvailable: Bool {
        !phrase.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    init(
        phrase: String,
        source: String,
        currentTemperature: String? = nil,
        forecast: String? = nil,
        conditionSymbolName: String? = nil
    ) {
        self.phrase = phrase
        self.source = source
        self.currentTemperature = currentTemperature ?? Self.extractTemperature(from: phrase)
        self.forecast = forecast ?? Self.extractForecast(from: phrase)
        self.conditionSymbolName = conditionSymbolName ?? Self.symbolName(for: phrase)
    }

    private static func extractTemperature(from phrase: String) -> String? {
        guard let range = phrase.range(of: #"[-+]?\d{1,3}\s?°?\s?[FC]?"#, options: .regularExpression) else {
            return nil
        }
        let value = String(phrase[range]).trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty ? nil : value
    }

    private static func extractForecast(from phrase: String) -> String? {
        let lowered = phrase.lowercased()
        let markers = ["forecast:", "later:", "tonight:", "tomorrow:"]
        for marker in markers {
            guard let range = lowered.range(of: marker) else { continue }
            let start = phrase.index(phrase.startIndex, offsetBy: lowered.distance(from: lowered.startIndex, to: range.upperBound))
            let value = phrase[start...].trimmingCharacters(in: .whitespacesAndNewlines)
            return value.isEmpty ? nil : value
        }
        return nil
    }

    private static func symbolName(for phrase: String) -> String {
        let lowered = phrase.lowercased()
        if lowered.contains("storm") || lowered.contains("thunder") {
            return "cloud.bolt.rain"
        }
        if lowered.contains("snow") || lowered.contains("sleet") || lowered.contains("ice") {
            return "snowflake"
        }
        if lowered.contains("rain") || lowered.contains("drizzle") || lowered.contains("shower") {
            return "cloud.rain"
        }
        if lowered.contains("fog") || lowered.contains("mist") || lowered.contains("haze") {
            return "cloud.fog"
        }
        if lowered.contains("wind") || lowered.contains("gust") || lowered.contains("breez") {
            return "wind"
        }
        if lowered.contains("cloud") || lowered.contains("overcast") {
            return "cloud"
        }
        if lowered.contains("clear") || lowered.contains("sun") || lowered.contains("bright") {
            return "sun.max"
        }
        return "cloud.sun"
    }
}

struct EnchantedWeatherSignal: Equatable {
    var summary: String
    var enchantified: String
    var selector: String
    var symbolName: String
}

struct NarrativeSourceSnapshot: Equatable {
    var activeThreadCount: Int
    var relationshipCount: Int
    var beliefWeight: Int?
    var recentEventCount: Int = 0
    var recentTags: [String] = []
    var weightedEntityIDs: [String] = []
    var weightedThreadIDs: [String] = []
    var weightedRelationshipIDs: [String] = []
    var entityMemories: [NarrativeEntityMemory] = []

    var isAvailable: Bool {
        activeThreadCount > 0
            || relationshipCount > 0
            || beliefWeight != nil
            || recentEventCount > 0
            || !recentTags.isEmpty
            || !weightedEntityIDs.isEmpty
            || !weightedThreadIDs.isEmpty
            || !weightedRelationshipIDs.isEmpty
            || !entityMemories.isEmpty
    }
}

enum NarrativeSourceSnapshotBuilder {
    static func snapshot(
        from events: [NarrativeEvent],
        memories: [NarrativeEntityMemory] = [],
        beliefWeight: Int?
    ) -> NarrativeSourceSnapshot {
        let recentEvents = Array(events.prefix(24))
        let projection = NarrativeStoryFieldProjector.projection(events: recentEvents, baseBelief: beliefWeight ?? 30)
        let entityIDs = projection.topEntityIDs
        let threadIDs = projection.topThreadIDs
        let relationshipIDs = projection.topRelationshipIDs
        let tags = Array(Set(recentEvents.flatMap(\.tags))).sorted()
        let selectedMemories = memories
            .filter { entityIDs.contains($0.entityID) }
            .sorted { left, right in
                if left.narrativeWeight == right.narrativeWeight {
                    return left.createdAt > right.createdAt
                }
                return left.narrativeWeight > right.narrativeWeight
            }
            .prefix(12)
            .map(\.self)

        return NarrativeSourceSnapshot(
            activeThreadCount: threadIDs.count,
            relationshipCount: relationshipIDs.count,
            beliefWeight: projection.belief,
            recentEventCount: recentEvents.count,
            recentTags: tags,
            weightedEntityIDs: entityIDs,
            weightedThreadIDs: threadIDs,
            weightedRelationshipIDs: relationshipIDs,
            entityMemories: selectedMemories
        )
    }
}

struct BookSourceInputs: Equatable {
    var body: BodySourceSignal?
    var weather: WeatherSourceSignal?
    var enchantedWeather: EnchantedWeatherSignal?
    var narrative: NarrativeSourceSnapshot?
    var selfFacts: [SelfFact] = []
    var facultyEntries: [FacultyEntry] = []
    var selectedWonderCompass: ReferenceSnippet?
    var selectedWonderCompassSelector: String?
    var preparedIlluminatedPhotoSurface: SurfacePage?
    var preparedStoryPageSurface: SurfacePage?
    var preparedGossipPageSurface: SurfacePage?
    var preparedFacultyResearchSurface: SurfacePage?
    var userPhotoIlluminationFallbackAllowed = false

    static let empty = BookSourceInputs()

    static func from(insideCover state: InsideCoverState) -> BookSourceInputs {
        BookSourceInputs(
            body: state.health.map {
                BodySourceSignal(
                    status: $0.status,
                    score: $0.score,
                    phrase: $0.phrase
                )
            },
            weather: extractWeather(from: state),
            enchantedWeather: nil,
            narrative: nil,
            selfFacts: [],
            facultyEntries: [],
            selectedWonderCompass: nil,
            selectedWonderCompassSelector: nil,
            preparedIlluminatedPhotoSurface: nil,
            preparedGossipPageSurface: nil,
            preparedFacultyResearchSurface: nil,
            userPhotoIlluminationFallbackAllowed: false
        )
    }

    private static func extractWeather(from state: InsideCoverState) -> WeatherSourceSignal? {
        let fields = [state.now, state.next, state.note, state.practicePrompt]
        for field in fields {
            guard let range = field.range(of: "weather:", options: [.caseInsensitive]) else {
                continue
            }
            let tail = field[range.upperBound...]
            let phrase = tail
                .split(whereSeparator: { $0 == "," || $0 == "\n" || $0 == "·" })
                .first
                .map(String.init)?
                .trimmingCharacters(in: .whitespacesAndNewlines)
            if let phrase, !phrase.isEmpty {
                return WeatherSourceSignal(phrase: phrase, source: "inside-cover")
            }
        }
        return nil
    }
}

protocol BookPageSourceAdapter {
    var source: BookPageSource { get }
    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage]
}

enum SurfaceCadence {
    static func slotID(for date: Date, hours: Int = 2, calendar: Calendar = .current) -> String {
        let components = calendar.dateComponents([.year, .month, .day, .hour], from: date)
        let year = components.year ?? 1970
        let month = components.month ?? 1
        let day = components.day ?? 1
        let slot = (components.hour ?? 0) / max(1, hours)
        return String(format: "%04d-%02d-%02d-s%02d", year, month, day, slot)
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

struct FacultyLogWindow: Equatable {
    var id: String
    var name: String
    var startMinute: Int
    var endMinute: Int
}

enum FacultyLogCadence {
    static let windows: [FacultyLogWindow] = [
        FacultyLogWindow(id: "morning", name: "Morning Bell", startMinute: 5 * 60, endMinute: 11 * 60),
        FacultyLogWindow(id: "midday", name: "Midday Bell", startMinute: 11 * 60, endMinute: 16 * 60),
        FacultyLogWindow(id: "evening", name: "Evening Bell", startMinute: 16 * 60, endMinute: 21 * 60),
        FacultyLogWindow(id: "night", name: "Night Bell", startMinute: 21 * 60, endMinute: 29 * 60)
    ]

    static func currentWindow(for date: Date = Date(), calendar: Calendar = .current) -> FacultyLogWindow {
        let components = calendar.dateComponents([.hour, .minute], from: date)
        let minute = (components.hour ?? 0) * 60 + (components.minute ?? 0)
        let comparableMinute = minute < windows[0].startMinute ? minute + 24 * 60 : minute
        return windows.first { window in
            comparableMinute >= window.startMinute && comparableMinute < window.endMinute
        } ?? windows[0]
    }

    static func didLog(kind: FacultyEntryKind, day: BookDay, entries: [FacultyEntry], now: Date = Date()) -> Bool {
        let window = currentWindow(for: now)
        if entries.contains(where: { $0.kind == kind && $0.dayID == day.id && $0.windowID == window.id }) {
            return true
        }
        let kindTag = "faculty-kind:\(kind.rawValue)"
        let windowTag = "faculty-window:\(window.id)"
        return day.pages.contains { page in
            page.tags.contains(kindTag) && page.tags.contains(windowTag)
        }
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

enum FacultyResearchNoteGenerator {
    static func draftCandidate(for day: BookDay, inputs: BookSourceInputs, now: Date = Date()) -> SurfacePage? {
        let source = BookPageSourceRegistry.source(for: .facultyResearch)
        guard !SupportGuildSynthesisGenerator.isGuildTime(now) else { return nil }
        let dueFaculty = nextDueFaculty(for: day)
        guard let facultyID = dueFaculty else { return nil }
        return draftCandidate(for: facultyID, source: source, day: day, inputs: inputs, now: now)
    }

    static func nextDueFaculty(for day: BookDay) -> String? {
        let researched = Set(day.pages.filter { $0.type == .facultyResearch }.flatMap(\.tags).compactMap { tag -> String? in
            guard tag.hasPrefix("faculty:") else { return nil }
            return String(tag.dropFirst("faculty:".count))
        })
        if !researched.contains("dr-vellum") {
            return "dr-vellum"
        }
        if !researched.contains("dr-inkrest") {
            return "dr-inkrest"
        }
        return nil
    }

    static func draftCandidate(for facultyID: String, source: BookPageSource, day: BookDay, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        let entity = NarrativePackRegistry.entities.first { $0.id == facultyID }
        let facultyName = entity?.name ?? facultyID
        let chart = SupportFacultyPackRegistry.charts(for: [facultyID]).first
        let topic = entity?.unwrittenInterest ?? chart?.purpose ?? "care research"
        let slot = SurfaceCadence.slotID(for: now, hours: 12)
        let body = promptBody(for: facultyID, topic: topic, day: day, inputs: inputs)
        return SurfacePage(
            id: "\(source.id)-\(day.id)-\(slot)-\(facultyID)",
            type: .facultyResearch,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .gentleTranslation,
            score: facultyID == "dr-vellum" ? 59 : 57,
            reason: "\(facultyName) is preparing a private research note for the evening Guild page.",
            prompt: "\(facultyName) opens a research folio.",
            detail: "A local-brain research brief for tonight's Support Guild meeting.",
            payload: BookPagePayload(
                headline: "\(facultyName)'s Research Folio",
                body: body,
                metadata: [
                    "source": source.id,
                    "facultyID": facultyID,
                    "facultyName": facultyName,
                    "researchTopic": topic,
                    "slotID": slot,
                    "placeholder": "Keep this research note for tonight's Guild page.",
                    "tags": "faculty-research,faculty:\(facultyID),support-guild,research"
                ]
            )
        )
    }

    private static func promptBody(for facultyID: String, topic: String, day: BookDay, inputs: BookSourceInputs) -> String {
        let metrics = inputs.body?.metrics.prefix(8).map(\.displayText).joined(separator: " | ") ?? "no HealthKit metrics"
        let entries = inputs.facultyEntries.prefix(8).map { "\($0.windowName): \($0.rawText)" }.joined(separator: "\n")
        if facultyID == "dr-vellum" {
            return """
            Research focus: \(topic)

            Vellum should connect current body evidence to longevity, fuel, recovery, sleep, heart signals, medication cautions, and one humane experiment. Use uncertainty. No diagnosis. No protocol heroics.

            Body signals: \(metrics)
            Recent chart entries:
            \(entries.isEmpty ? "No chart entries yet." : entries)
            """
        }
        return """
        Research focus: \(topic)

        Inkrest should connect current inner weather to narrative psychology, consciousness, self-distancing, reauthoring, attention, and one gentle question. Use uncertainty. No diagnosis. No forced catharsis.

        Body signals: \(metrics)
        Recent chart entries:
        \(entries.isEmpty ? "No chart entries yet." : entries)
        """
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
            return "I wonder what would happen if..."
        case .embark:
            return "Destination: \nDelight: \nDefinition: "
        case .sense:
            return "Mission: Find three rough textures / Listen for the quietest sound / Photograph one strange angle..."
        case .write:
            return "The single detail I want to keep is..."
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
            return "North sets the bearing. Ask a real 'I wonder...' question and let it become the goal of the run."
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

enum WonderConciergeMode: String, CaseIterable {
    case closeToHome
    case budget
    case obscure
    case vibe
    case scavenger
    case recovery

    var title: String {
        switch self {
        case .closeToHome:
            return "Close to Home"
        case .budget:
            return "Budget Agent"
        case .obscure:
            return "Curator of the Obscure"
        case .vibe:
            return "Vibe Check"
        case .scavenger:
            return "Gamifier"
        case .recovery:
            return "Recovery Compass"
        }
    }

    var promptSeed: String {
        switch self {
        case .closeToHome:
            return "Make a tiny adventure from the room, porch, driveway, kitchen, or nearest walkable threshold."
        case .budget:
            return "Keep cost anxiety low. Use free or cheap options and name one simple treat."
        case .obscure:
            return "Look for overlooked oddities, strange local history, old signs, hidden corners, or story-rich places."
        case .vibe:
            return "Match the user's mood to a place, texture, sound, or tiny ritual."
        case .scavenger:
            return "Turn the situation into a sensory scavenger hunt with specific things to find or photograph."
        case .recovery:
            return "Shrink the Compass to the user's energy envelope. Movement can be one inch; rest can be the run."
        }
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
        let seed = abs("\(day.id)-\(slot)-playful-mission".hashValue)
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

    static let missions: [PlayfulMission] = [
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
        switch mode {
        case .closeToHome:
            return "I wonder what detail in this room has been invisible all week?"
        case .budget:
            return "I wonder what cheap, specific pleasure would make today feel less gray?"
        case .obscure:
            return "I wonder what strange little story is hiding nearby?"
        case .vibe:
            return "I wonder where today's mood would feel understood instead of fixed?"
        case .scavenger:
            return "I wonder what five oddly specific things I can find where I already have to be?"
        case .recovery:
            return "I wonder what is the smallest true thing I can notice without pushing?"
        }
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
        \(seed.mode.promptSeed)

        Deterministic rails for Gemma:
        \(seed.fullPrompt)

        Generate a custom Wonder Compass cycle from these constraints. Keep it sensory, specific, and non-generic. Use NORTH (NOTICE), EAST (EMBARK), SOUTH (SENSE), WEST (WRITE), and CENTER (REST). End with one useful hint.

        N -> E -> S -> W, then Center:
        Notice: \(seed.spark)
        Embark: Destination: \(seed.destination). Delight: \(seed.delight). Definition: \(seed.definition).
        Sense: \(seed.mission)
        Write: \(seed.souvenirPrompt)
        Rest: \(seed.restPrompt)
        """
    }
}

struct MoodPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .mood)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        let window = FacultyLogCadence.currentWindow(for: now)
        guard !FacultyLogCadence.didLog(kind: .innerWeather, day: day, entries: inputs.facultyEntries, now: now) else {
            return []
        }
        return [
            SurfacePage(
                id: "\(source.id)-\(day.id)-\(window.id)",
                type: .mood,
                sourceID: source.id,
                intent: .capture,
                renderStyle: .promptCard,
                score: context.distress.isActive ? 72 : 64,
                reason: context.distress.isActive ? "A hard signal asks for gentle naming." : "Dr. Inkrest has an open chart window.",
                prompt: "What is the weather inside?",
                detail: "\(window.name). Name the inner sky. One tap is enough.",
                payload: BookPagePayload(
                    headline: "Inner Weather",
                    body: "Name the inner sky. One tap is enough.",
                    metadata: [
                        "source": source.id,
                        "facultyID": FacultyEntryKind.innerWeather.facultyID,
                        "facultyKind": FacultyEntryKind.innerWeather.rawValue,
                        "facultyWindowID": window.id,
                        "facultyWindowName": window.name,
                        "chartTitle": FacultyEntryKind.innerWeather.chartTitle,
                        "tags": "inner-weather,faculty-kind:innerWeather,faculty-window:\(window.id),dr-inkrest,therapy-chart"
                    ]
                )
            )
        ]
    }
}

struct FuelLogPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .fuel)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        let window = FacultyLogCadence.currentWindow(for: now)
        guard !FacultyLogCadence.didLog(kind: .fuel, day: day, entries: inputs.facultyEntries, now: now) else {
            return []
        }

        let detail: String
        switch window.id {
        case "morning":
            detail = "What has crossed the threshold since waking: food, coffee, water, medicine, crumbs, anything."
        case "midday":
            detail = "What has kept the engine lit so far? Approximate is useful."
        case "evening":
            detail = "What did the body receive since the last bell? Meals, snacks, drinks, supplements, no ceremony required."
        default:
            detail = "A gentle closing note for the body: late drinks, bites, medicine, or simply nothing since the last bell."
        }

        return [
            SurfacePage(
                id: "\(source.id)-\(day.id)-\(window.id)",
                type: .fuel,
                sourceID: source.id,
                intent: .capture,
                renderStyle: .promptCard,
                score: context.distress.isActive ? 70 : 66,
                reason: "Dr. Vellum has an open plate-note window.",
                prompt: "Dr. Vellum's Plate Note",
                detail: "\(window.name). \(detail)",
                payload: BookPagePayload(
                    headline: "Fuel Log",
                    body: detail,
                    metadata: [
                        "source": source.id,
                        "facultyID": FacultyEntryKind.fuel.facultyID,
                        "facultyKind": FacultyEntryKind.fuel.rawValue,
                        "facultyWindowID": window.id,
                        "facultyWindowName": window.name,
                        "chartTitle": FacultyEntryKind.fuel.chartTitle,
                        "placeholder": "Breakfast: coffee, toast, water...\nLunch: leftovers, soda...\nMedicine/supplements: ...",
                        "tags": "fuel,faculty-kind:fuel,faculty-window:\(window.id),dr-vellum,vellum-chart,food,drink"
                    ]
                )
            )
        ]
    }
}

struct SupportGuildPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .supportGuild)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard let surface = SupportGuildSynthesisGenerator.surface(for: day, context: context, inputs: inputs, now: now) else {
            return []
        }
        return [surface]
    }
}

struct FacultyResearchPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .facultyResearch)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        if let prepared = inputs.preparedFacultyResearchSurface {
            return [prepared]
        }
        guard let draft = FacultyResearchNoteGenerator.draftCandidate(for: day, inputs: inputs, now: now) else {
            return []
        }
        return [draft]
    }
}

struct SouvenirPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .souvenir)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard !day.hasSouvenir else { return [] }
        let hour = Calendar.current.component(.hour, from: now)
        let eveningPrompt = hour >= 18
        return [
            SurfacePage(
                type: .souvenir,
                sourceID: source.id,
                intent: .capture,
                renderStyle: .quoteCard,
                score: eveningPrompt ? 78 : 58,
                reason: eveningPrompt ? "Evening is a good time to keep one moment." : "A small particular can anchor the day.",
                prompt: eveningPrompt ? "What moment should not blur?" : "Catch one bright particular.",
                detail: eveningPrompt ? "One specific sentence before the day edits itself." : "A color, a sound, a sentence, a small mercy.",
                payload: BookPagePayload(
                    headline: source.title,
                    body: "A small moment worth keeping.",
                    metadata: ["source": source.id]
                )
            )
        ]
    }
}

struct RestPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .rest)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        let hour = Calendar.current.component(.hour, from: now)
        guard context.distress.isActive || context.bleed.pageBias.first == .rest || day.capturedPages.isEmpty || hour >= 20 else {
            return []
        }
        return [
            SurfacePage(
                type: .rest,
                sourceID: source.id,
                intent: .rest,
                renderStyle: .gentleTranslation,
                score: context.distress.isActive ? 96 : (context.bleed.pageBias.first == .rest ? 88 : 62),
                reason: context.distress.isActive ? "The Book lowers the lamps before offering anything else." : "Rest belongs in the three when the day needs a center.",
                prompt: "The Center Page has opened.",
                detail: "No quest. No improvement. Just a small truthful landing.",
                payload: BookPagePayload(
                    headline: "Center Page",
                    body: "No quest. No improvement. Just a small truthful landing.",
                    metadata: ["source": source.id]
                )
            )
        ]
    }
}

struct BookOfYouPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .bookOfYou)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard BookSchedule.isBraidSurfaceTime(now),
              !day.capturedPages.isEmpty,
              day.bookOfYou == nil else {
            return []
        }
        return [
            SurfacePage(
                type: .bookOfYou,
                sourceID: source.id,
                intent: .braid,
                renderStyle: .loreLetter,
                score: day.capturedPages.count >= 3 ? 90 : 74,
                reason: day.capturedPages.count >= 3 ? "Enough fragments are gathered for a stronger braid." : "Today has fragments worth keeping together.",
                prompt: "The Book can braid today.",
                detail: "Gather the fragments into one page worth keeping.",
                payload: BookPagePayload(
                    headline: "Book of You",
                    body: "Gather the fragments into one page worth keeping.",
                    metadata: ["source": source.id]
                )
            )
        ]
    }
}

enum BookSchedule {
    static func isBraidSurfaceTime(_ date: Date = Date(), calendar: Calendar = .current) -> Bool {
        minutesSinceStartOfDay(for: date, calendar: calendar) >= 20 * 60
    }

    static func shouldAutoBraid(_ date: Date = Date(), calendar: Calendar = .current) -> Bool {
        minutesSinceStartOfDay(for: date, calendar: calendar) >= 21 * 60 + 30
    }

    private static func minutesSinceStartOfDay(for date: Date, calendar: Calendar) -> Int {
        let components = calendar.dateComponents([.hour, .minute], from: date)
        return (components.hour ?? 0) * 60 + (components.minute ?? 0)
    }
}

struct BodyPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .body)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive,
              let body = inputs.body,
              body.isAvailable else {
            return []
        }

        let isLow = body.score > 0 && body.score <= 35
        return [
            SurfacePage(
                id: "\(source.id)-\(body.status.lowercased())-\(SurfaceCadence.slotID(for: now, hours: 4))",
                type: .body,
                sourceID: source.id,
                intent: .reflect,
                renderStyle: .gentleTranslation,
                score: context.distress.isActive || isLow ? 92 : 60,
                reason: "The Book translated today's body signals privately.",
                prompt: isLow ? "The Body Page has lowered the lamps." : "The Body Page is listening quietly.",
                detail: "A soft translation, ready to keep as-is or annotate in the margin.",
                payload: BookPagePayload(
                    headline: "Body Page",
                    body: body.phrase,
                    metadata: [
                        "source": source.id,
                        "status": body.status,
                        "uses": "translated health, fuel, mood",
                        "privacy": "name response, not source"
                    ]
                )
            )
        ]
    }
}

struct WeatherPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .weather)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive,
              let weather = inputs.weather,
              weather.isAvailable else {
            return []
        }
        let hour = Calendar.current.component(.hour, from: now)
        let enchanted = inputs.enchantedWeather ?? WeatherEnchanter.fallback(weather: weather, now: now)
        let rawParts = [
            weather.currentTemperature.map { "Now: \($0)" },
            weather.forecast.map { "Forecast: \($0)" }
        ].compactMap(\.self)
        let rawLine = rawParts.isEmpty ? weather.phrase : rawParts.joined(separator: " | ")
        return [
            SurfacePage(
                id: "\(source.id)-\(enchanted.selector)-\(SurfaceCadence.slotID(for: now, hours: 4))",
                type: .weather,
                sourceID: source.id,
                intent: .reflect,
                renderStyle: .gentleTranslation,
                score: hour >= 17 ? 87 : 82,
                reason: "Outer weather is translated into story mood while keeping the actual forecast legible.",
                prompt: "The Weather Page has opened.",
                detail: rawLine,
                payload: BookPagePayload(
                    headline: "Weather Page",
                    body: "\(enchanted.enchantified)\n\nWeather: \(rawLine)",
                    metadata: [
                        "source": source.id,
                        "uses": weather.source,
                        "privacy": "public reference",
                        "selector": enchanted.selector,
                        "symbol": enchanted.symbolName,
                        "rawWeather": weather.phrase,
                        "cadence": "four-hour"
                    ]
                )
            )
        ]
    }
}

struct QuipPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .quip)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        let tags = [
            inputs.weather?.phrase,
            inputs.body?.status,
            inputs.selectedWonderCompass?.tags.joined(separator: ",")
        ]
            .compactMap(\.self)
            .flatMap { $0.lowercased().split { !$0.isLetter && !$0.isNumber }.map(String.init) }
        let quip = QuipPackRegistry.quip(for: day, now: now, tags: tags)
        let hour = Calendar.current.component(.hour, from: now)
        let score = context.distress.isActive ? 42 : (hour >= 12 && hour <= 18 ? 69 : 58)
        return [
            SurfacePage(
                id: "\(source.id)-\(quip.packID)-\(quip.id)-\(SurfaceCadence.slotID(for: now, hours: 3))",
                type: .quip,
                sourceID: source.id,
                intent: .importReference,
                renderStyle: .quoteCard,
                score: score,
                reason: "A small oddity can tilt the day toward wonder without asking for work.",
                prompt: quip.title,
                detail: "A little perspective-spark from \(QuipPackRegistry.enabledPacks.first { $0.id == quip.packID }?.displayName ?? "the shelf").",
                payload: BookPagePayload(
                    headline: quip.title,
                    body: quip.text,
                    metadata: [
                        "source": source.id,
                        "packID": quip.packID,
                        "quipID": quip.id,
                        "tags": quip.tags.joined(separator: ","),
                        "privacy": "bundled local text"
                    ]
                )
            )
        ]
    }
}

struct AboutYouPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .aboutYou)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive,
              let question = SelfKnowledgePackRegistry.nextQuestion(knownFacts: inputs.selfFacts, day: day, now: now) else {
            return []
        }

        let isFirstQuestion = inputs.selfFacts.isEmpty
        let calendar = Calendar.current
        let factsAnsweredToday = inputs.selfFacts.filter { calendar.isDate($0.createdAt, inSameDayAs: now) }
        if !isFirstQuestion,
           factsAnsweredToday.count >= SelfKnowledgePackRegistry.maxAboutYouFactsPerDay {
            return []
        }
        if !isFirstQuestion,
           let lastAnsweredAt = inputs.selfFacts.map(\.createdAt).max(),
           let nextAllowedAt = calendar.date(
                byAdding: .hour,
                value: SelfKnowledgePackRegistry.minimumHoursBetweenAboutYouFacts,
                to: lastAnsweredAt
           ),
           now < nextAllowedAt {
            return []
        }

        let score = isFirstQuestion ? 83 : (context.distress.isActive ? 46 : 67)
        let packName = SelfKnowledgePackRegistry.packName(for: question.packID)
        return [
            SurfacePage(
                id: "\(source.id)-\(question.packID)-\(question.id)",
                type: .aboutYou,
                sourceID: source.id,
                intent: .capture,
                renderStyle: .promptCard,
                score: score,
                reason: isFirstQuestion
                    ? "The Book should learn your name before it guesses."
                    : "One true thing lets future pages feel less generic.",
                prompt: question.prompt,
                detail: question.detail,
                payload: BookPagePayload(
                    headline: "The Book Learns",
                    body: question.placeholder,
                    metadata: [
                        "source": source.id,
                        "questionID": question.id,
                        "packID": question.packID,
                        "packName": packName,
                        "sensitivity": question.sensitivity.rawValue,
                        "usePermission": question.defaultUsePermission.rawValue,
                        "tags": question.tags.joined(separator: ","),
                        "privacy": "private local profile"
                    ]
                )
            )
        ]
    }
}

enum WeatherEnchanter {
    static func fallback(weather: WeatherSourceSignal, now: Date = Date()) -> EnchantedWeatherSignal {
        let lowered = weather.phrase.lowercased()
        let mood: String
        if lowered.contains("storm") || lowered.contains("thunder") {
            mood = "The stacks are keeping their lanterns low; the sky has teeth today."
        } else if lowered.contains("rain") || lowered.contains("drizzle") {
            mood = "Rain is tapping at the margins, turning the ordinary streets into ink-wet pages."
        } else if lowered.contains("fog") || lowered.contains("mist") {
            mood = "The air has gone soft at the edges; the world is speaking in pencil."
        } else if lowered.contains("snow") || lowered.contains("ice") {
            mood = "The weather has dusted the shelves in hush and silver."
        } else if lowered.contains("wind") || lowered.contains("gust") {
            mood = "A restless draft is moving through the corridors; loose pages may have opinions."
        } else if lowered.contains("clear") || lowered.contains("sun") || lowered.contains("bright") {
            mood = "The lamps are high today; even the dust looks ready for an expedition."
        } else {
            mood = "The weather has left a quiet mark on the day, enough for the Book to tint the page."
        }

        return EnchantedWeatherSignal(
            summary: weather.phrase,
            enchantified: mood,
            selector: "local-weather",
            symbolName: weather.conditionSymbolName
        )
    }
}

struct WonderCompassPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .wonderCompass)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else {
            return []
        }

        let progress = CompassRunProgress.progress(for: day)
        let seed = WonderCompassRunGenerator.seed(for: day, inputs: inputs, progress: progress, now: now)
        let playfulMission = PlayfulMissionRegistry.mission(for: day, inputs: inputs, now: now)
        let snippet = inputs.selectedWonderCompass
            ?? BookReferenceCatalog.relevantWonderCompassSnippet(for: day, inputs: inputs, now: now)
        let selector = inputs.selectedWonderCompassSelector ?? "local-relevance"
        let isGemmaSelected = selector == "gemma"
        var pages: [SurfacePage] = [
            runSurface(seed: seed, progress: progress, context: context, now: now),
            stepSurface(step: progress.nextStep, seed: seed, progress: progress, context: context, now: now),
            playfulMissionSurface(playfulMission, seed: seed, context: context, now: now),
            SurfacePage(
                id: "\(source.id)-\(snippet.id)",
                type: .wonderCompass,
                sourceID: source.id,
                intent: .importReference,
                renderStyle: .quoteCard,
                score: context.distress.isActive ? 52 : 66,
                reason: isGemmaSelected
                    ? "Gemma chose this passage from today's pages and the shape of the day."
                    : (context.distress.isActive ? "Only a small, low-pressure practice belongs here." : "A field-guide card can give the day one clean handle."),
                prompt: "From the Wonder Compass Book",
                detail: snippet.prompt,
                payload: BookPagePayload(
                    headline: "From the Wonder Compass Book: \(snippet.title)",
                    body: snippet.body,
                    metadata: [
                        "source": source.id,
                        "snippetID": snippet.id,
                        "tags": snippet.tags.joined(separator: ","),
                        "selector": selector
                    ]
                )
            )
        ]

        if progress.completedSteps.isEmpty {
            pages.append(stepSurface(step: .notice, seed: seed, progress: progress, context: context, now: now, standalone: true))
        }

        return pages
    }

    private func playfulMissionSurface(
        _ mission: PlayfulMission,
        seed: WonderCompassRunSeed,
        context: CuratorContext,
        now: Date
    ) -> SurfacePage {
        var metadata = metadata(for: seed, step: .sense)
        metadata["compassStep"] = "sense"
        metadata["playfulMissionID"] = mission.id
        metadata["playfulMissionTitle"] = mission.title
        metadata["mission"] = mission.prompt
        metadata["souvenirPrompt"] = mission.proofPrompt
        metadata["placeholder"] = mission.proofPrompt
        metadata["proofKind"] = mission.allowsPhoto ? "sentence-or-photo" : "sentence"
        metadata["tags"] = (seed.tags + ["compass-step:sense", "playful-mission"] + mission.tags.map { "mission:\($0)" }).joined(separator: ",")
        metadata["symbol"] = mission.allowsPhoto ? "camera.macro" : "hand.raised"

        return SurfacePage(
            id: "\(source.id)-playful-mission-\(mission.id)-\(SurfaceCadence.slotID(for: now, hours: 2))",
            type: .wonderCompass,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .promptCard,
            score: context.distress.isActive ? 54 : 64,
            reason: "A playful mission can turn South into something your senses can actually do.",
            prompt: "Playful Mission: \(mission.title)",
            detail: mission.prompt,
            payload: BookPagePayload(
                headline: "South = Sense",
                body: "\(mission.prompt)\n\nProof: \(mission.proofPrompt)\(mission.allowsPhoto ? " Or keep a photo." : "")",
                metadata: metadata
            )
        )
    }

    private func runSurface(
        seed: WonderCompassRunSeed,
        progress: CompassRunProgress,
        context: CuratorContext,
        now: Date
    ) -> SurfacePage {
        let completed = progress.completedSteps.count
        let isFresh = completed == 0
        let next = progress.isComplete ? CompassRunStep.rest : progress.nextStep
        let headline = isFresh ? "Compass Run" : (progress.isComplete ? "Compass Run Complete" : "Resume Compass Run")
        let detail = isFresh
            ? "A full N-E-S-W loop customized to now: constraints first, magic after."
            : "\(completed)/5 directions complete. Next: \(next.compassPoint) = \(next.title)."
        var metadata = metadata(for: seed, step: nil)
        metadata["compassStep"] = "run"
        metadata["completedSteps"] = "\(completed)"
        metadata["nextStep"] = next.rawValue

        return SurfacePage(
            id: "\(source.id)-run-\(seed.id)",
            type: .wonderCompass,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .quoteCard,
            score: context.distress.isActive ? 48 : (isFresh ? 60 : 62),
            reason: progress.isComplete
                ? "The wheel has turned; the center can hold the page."
                : "The Compass can turn the current constraints into one small adventure.",
            prompt: headline,
            detail: detail,
            payload: BookPagePayload(
                headline: headline,
                body: WonderCompassRunGenerator.body(for: seed),
                metadata: metadata
            )
        )
    }

    private func stepSurface(
        step: CompassRunStep,
        seed: WonderCompassRunSeed,
        progress: CompassRunProgress,
        context: CuratorContext,
        now: Date,
        standalone: Bool = false
    ) -> SurfacePage {
        var metadata = metadata(for: seed, step: step)
        metadata["compassStep"] = step.rawValue
        metadata["standalone"] = standalone ? "true" : "false"
        metadata["placeholder"] = step.capturePlaceholder

        let score = context.distress.isActive && step != .rest
            ? 50
            : (standalone ? 42 : 58 + min(step.scoreBoost, 4))

        return SurfacePage(
            id: "\(source.id)-\(standalone ? "solo" : "run")-\(seed.id)-\(step.rawValue)",
            type: .wonderCompass,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .promptCard,
            score: score,
            reason: standalone
                ? "\(step.title) can be used on its own without committing to a full run."
                : "The next Compass direction is ready.",
            prompt: "\(step.compassPoint): \(step.title)",
            detail: step.standaloneDetail,
            payload: BookPagePayload(
                headline: "\(step.compassPoint) = \(step.title)",
                body: step.missionBody,
                metadata: metadata
            )
        )
    }

    private func metadata(for seed: WonderCompassRunSeed, step: CompassRunStep?) -> [String: String] {
        let tags = seed.tags + (step.map { ["compass-step:\($0.rawValue)"] } ?? [])
        var metadata: [String: String] = [
            "source": source.id,
            "tags": tags.joined(separator: ","),
            "runID": seed.id,
            "conciergeMode": seed.mode.rawValue,
            "timeBox": seed.timeBox,
            "budget": seed.budget,
            "place": seed.place,
            "energy": seed.energy,
            "companions": seed.companions,
            "considerations": seed.considerations,
            "circumstance": seed.circumstance,
            "spark": seed.spark,
            "destination": seed.destination,
            "delight": seed.delight,
            "definition": seed.definition,
            "mission": seed.mission,
            "souvenirPrompt": seed.souvenirPrompt,
            "restPrompt": seed.restPrompt,
            "privacy": "private local practice"
        ]
        if let step {
            metadata["symbol"] = symbol(for: step)
        } else {
            metadata["symbol"] = "safari"
        }
        return metadata
    }

    private func symbol(for step: CompassRunStep) -> String {
        switch step {
        case .notice:
            return "sparkle.magnifyingglass"
        case .embark:
            return "figure.walk"
        case .sense:
            return "hand.draw"
        case .write:
            return "pencil.and.scribble"
        case .rest:
            return "moon.stars"
        }
    }
}

struct EnchantifyLorePageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .lore)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else {
            return []
        }

        let snippet = BookReferenceCatalog.relevantLoreSnippet(for: day, inputs: inputs, now: now)
        return [
            SurfacePage(
                id: "\(source.id)-\(snippet.id)",
                type: .lore,
                sourceID: source.id,
                intent: .importReference,
                renderStyle: .loreLetter,
                score: context.distress.isActive ? 44 : 68,
                reason: context.distress.isActive ? "Lore waits behind gentler pages when the day is hard." : "A lore card can bring the world closer without asking anything of you.",
                prompt: snippet.prompt,
                detail: snippet.title,
                payload: BookPagePayload(
                    headline: snippet.title,
                    body: snippet.body,
                    metadata: [
                        "source": source.id,
                        "snippetID": snippet.id,
                        "tags": snippet.tags.joined(separator: ",")
                    ]
                )
            )
        ]
    }
}

struct PatreonPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .patreon)
    private let patreonURL = "https://patreon.com/thedoobaleedoos"

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else {
            return []
        }

        let snippet = BookReferenceCatalog.patreonShelfSnippet(now: now)
        let posts = BookReferenceCatalog.patreonPostSnippets(limit: 6, now: now)
        let postLinks = posts.compactMap { post -> String? in
            guard let url = BookReferenceCatalog.firstURL(in: post) else { return nil }
            return "\(post.title)||\(url)"
        }
        let postPreviews = posts.compactMap { post -> String? in
            guard let url = BookReferenceCatalog.firstURL(in: post) else { return nil }
            let preview = post.preview?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
                ? post.preview ?? ""
                : post.body
            return [
                post.title,
                url,
                post.publishedAt ?? "",
                preview.replacingOccurrences(of: "\n", with: " ")
            ].joined(separator: "||")
        }
        let postList = posts.isEmpty
            ? ""
            : "\n\nNewest articles on the public shelf:\n" + posts.map { post in
                let published = post.publishedAt?.isEmpty == false ? " (\(post.publishedAt ?? ""))" : ""
                return "- \(post.title)\(published)"
            }.joined(separator: "\n")
        return [
            SurfacePage(
                id: "\(source.id)-\(snippet.id)",
                type: .patreon,
                sourceID: source.id,
                intent: .importReference,
                renderStyle: .quoteCard,
                score: context.distress.isActive ? 48 : 61,
                reason: "The public shelf should be easy to find without making the private Book less private.",
                prompt: "The public shelf is open.",
                detail: "Read free Wonder Compass and Clubhouse posts on Patreon.",
                payload: BookPagePayload(
                    headline: snippet.title,
                    body: snippet.body + postList,
                    metadata: [
                        "source": source.id,
                        "url": patreonURL,
                        "links": postLinks.joined(separator: "\n"),
                        "articlePreviews": postPreviews.joined(separator: "\n"),
                        "snippetID": snippet.id,
                        "tags": snippet.tags.joined(separator: ","),
                        "privacy": "public link"
                    ]
                )
            )
        ]
    }
}

struct LabyrinthIllustrationPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .illustration)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        let plate = BookReferenceCatalog.labyrinthIllustration(for: day, now: now)
        let profile = BookReferenceCatalog.characterIllustrationProfile(id: plate.characterID)
        let aboutText = profile.map { Self.characterAboutText(for: $0) } ?? plate.caption
        let bodyText = profile.map { Self.characterPageBody(for: $0, plate: plate) } ?? "\(plate.caption)\n\n\(plate.note)"
        var metadata = [
            "source": source.id,
            "assetName": plate.assetName,
            "plateID": plate.id,
            "tags": plate.tags.joined(separator: ","),
            "privacy": "bundled local image"
        ]
        if let profile {
            metadata["characterID"] = profile.id
            metadata["characterName"] = profile.characterName
            metadata["characterSlug"] = profile.slug
            metadata["characterStatus"] = profile.status
            metadata["characterChapter"] = profile.chapter ?? ""
            metadata["illustrationPrompt"] = profile.prompt
            metadata["negativePrompt"] = profile.negativePrompt
            metadata["intendedAssetName"] = profile.intendedAssetName
            metadata["signature"] = profile.signature
            metadata["palette"] = profile.palette
            metadata["silhouette"] = profile.silhouette
            metadata["continuity"] = profile.continuity
            metadata["marginalia"] = profile.marginalia.joined(separator: " | ")
            metadata["visualStyleReference"] = "antique parchment academy dossier portrait collage"
        }
        return [
            SurfacePage(
                id: "\(source.id)-\(plate.id)-\(SurfaceCadence.slotID(for: now, hours: 1))",
                type: .illustration,
                sourceID: source.id,
                intent: .importReference,
                renderStyle: .illustrationPlate,
                score: context.distress.isActive ? 50 : 65,
                reason: "A bundled illustration can surface without asking anything of you.",
                prompt: profile.map { "Character Illustration: \($0.characterName)" } ?? "An Illustration from the Labyrinth of Stories",
                detail: aboutText,
                payload: BookPagePayload(
                    headline: plate.title,
                    body: bodyText,
                    metadata: metadata
                )
            )
        ]
    }

    private static func characterAboutText(for profile: CharacterIllustrationProfile) -> String {
        let dossierKind: String
        if let chapter = profile.chapter?.trimmingCharacters(in: .whitespacesAndNewlines), !chapter.isEmpty {
            dossierKind = "\(chapter) dossier"
        } else {
            dossierKind = "Academy dossier"
        }
        return "\(dossierKind). \(compactCore(for: profile)) Signature: \(profile.signature)."
    }

    private static func characterPageBody(for profile: CharacterIllustrationProfile, plate: LabyrinthIllustrationPlate) -> String {
        let marginalia = profile.marginalia.prefix(3).joined(separator: " | ")
        return """
        \(characterAboutText(for: profile))

        Silhouette: \(profile.silhouette).

        Marginalia: \(marginalia).

        \(plate.note)
        """
    }

    private static func compactCore(for profile: CharacterIllustrationProfile) -> String {
        let clauses = profile.core
            .split(separator: ";")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let summary = clauses.prefix(2).joined(separator: "; ")
        return summary.isEmpty ? profile.core : "\(summary)."
    }
}

struct NarrativeOSPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .narrativeOS)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        guard let prepared = inputs.preparedStoryPageSurface else { return [] }
        return [prepared]
    }

    static func draftCandidate(for day: BookDay, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        let source = BookPageSourceRegistry.source(for: .narrativeOS)
        let packet = StoryScenePacketBuilder.packet(for: day, inputs: inputs, now: now)
        let choiceRoles = packet.choices.map { $0.role.title }.joined(separator: " | ")
        let selectedThreads = packet.selectedThreads.map(\.title).joined(separator: ", ")
        let selectedEntities = packet.selectedEntities.map(\.name).joined(separator: ", ")
        let selectedRelationships = packet.selectedRelationships.map(\.id).joined(separator: ", ")
        let selectedEntityMemories = packet.selectedEntityMemories
            .map { memory in
                let entityName = NarrativePackRegistry.entities.first(where: { $0.id == memory.entityID })?.name ?? memory.entityID
                return "\(entityName): \(memory.summary)"
            }
            .joined(separator: "\n")
        return SurfacePage(
            id: "\(source.id)-\(packet.id)",
            type: .narrativeOS,
            sourceID: source.id,
            intent: .simulate,
            renderStyle: .graphEvent,
            score: day.capturedPages.count >= 2 ? 86 : 68,
            reason: "The story field has enough weight for characters, beliefs, and threads to move.",
            prompt: "The Story Page is stirring.",
            detail: packet.directorIntent,
            payload: BookPagePayload(
                headline: packet.title,
                body: "A page is gathering around the day’s strongest thread. The first lines are still drying in the margin.",
                metadata: [
                    "source": source.id,
                    "packetID": packet.id,
                    "packID": packet.packID,
                    "bookGlow": packet.bookGlow,
                    "playerBelief": "\(packet.playerBelief)",
                    "choiceRoles": choiceRoles,
                    "selectedThreads": selectedThreads,
                    "selectedEntities": selectedEntities,
                    "selectedRelationships": selectedRelationships,
                    "entityMemories": selectedEntityMemories,
                    "realSignals": packet.realSignals.joined(separator: "\n"),
                    "relationshipPressures": packet.relationshipPressures.joined(separator: "\n"),
                    "uses": "characters, belief, relationship graph, story threads",
                    "cadence": "four-hour simulation"
                ]
            )
        )
    }
}

struct GossipPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .gossip)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        guard let prepared = inputs.preparedGossipPageSurface else { return [] }
        return [prepared]
    }

    static func draftCandidate(for day: BookDay, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        GossipSimulationBuilder.surface(for: day, inputs: inputs, now: now)
    }
}

struct LocationPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .location)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        return [
            SurfacePage(
                type: .location,
                sourceID: source.id,
                intent: .reflect,
                renderStyle: .gentleTranslation,
                score: 56,
                reason: "Place can change the story field without becoming surveillance.",
                prompt: "What place is the Book standing in?",
                detail: "A place can become a page without becoming a report.",
                payload: BookPagePayload(
                    headline: "Location Page",
                    body: "A place can become a page without becoming a report.",
                    metadata: ["source": source.id, "outerStacks": "possible"]
                )
            )
        ]
    }
}

enum BookPageSourceAdapters {
    static let active: [BookPageSourceAdapter] = [
        RestPageSourceAdapter(),
        MoodPageSourceAdapter(),
        SouvenirPageSourceAdapter(),
        BookOfYouPageSourceAdapter(),
        BodyPageSourceAdapter(),
        FuelLogPageSourceAdapter(),
        FacultyResearchPageSourceAdapter(),
        SupportGuildPageSourceAdapter(),
        WeatherPageSourceAdapter(),
        QuipPageSourceAdapter(),
        AboutYouPageSourceAdapter(),
        WonderCompassPageSourceAdapter(),
        EnchantifyLorePageSourceAdapter(),
        PatreonPageSourceAdapter(),
        LabyrinthIllustrationPageSourceAdapter(),
        IlluminatedPhotoPageSourceAdapter(),
        NarrativeOSPageSourceAdapter(),
        GossipPageSourceAdapter(),
        LocationPageSourceAdapter()
    ]
}

struct RankedSurfacePage: Equatable {
    var page: SurfacePage
    var rank: Int
}

struct CuratorSurfacePreferences: Equatable {
    var dismissedSurfaceIDs: Set<String>
    var disabledSourceIDs: Set<String>

    static let none = CuratorSurfacePreferences()

    init(
        dismissedSurfaceIDs: Set<String> = [],
        disabledSourceIDs: Set<String> = []
    ) {
        self.dismissedSurfaceIDs = dismissedSurfaceIDs
        self.disabledSourceIDs = disabledSourceIDs
    }

    func allows(_ page: SurfacePage) -> Bool {
        !dismissedSurfaceIDs.contains(page.id) && !disabledSourceIDs.contains(page.sourceID)
    }
}

struct SurfaceDismissalLedger: Codable, Equatable {
    var dismissedAtByDay: [String: [String: Date]]

    init(dismissedAtByDay: [String: [String: Date]] = [:]) {
        self.dismissedAtByDay = dismissedAtByDay
    }

    mutating func dismiss(surfaceID: String, dayID: String, at date: Date) {
        var dayDismissals = dismissedAtByDay[dayID] ?? [:]
        dayDismissals[surfaceID] = date
        dismissedAtByDay[dayID] = dayDismissals
    }

    mutating func restore(surfaceID: String, dayID: String) {
        dismissedAtByDay[dayID]?[surfaceID] = nil
        if dismissedAtByDay[dayID]?.isEmpty == true {
            dismissedAtByDay[dayID] = nil
        }
    }

    func activeDismissedSurfaceIDs(for dayID: String, now: Date, ttl: TimeInterval) -> Set<String> {
        let cutoff = now.addingTimeInterval(-ttl)
        return Set((dismissedAtByDay[dayID] ?? [:]).compactMap { surfaceID, dismissedAt in
            dismissedAt > cutoff ? surfaceID : nil
        })
    }

    mutating func prune(now: Date, ttl: TimeInterval) {
        let cutoff = now.addingTimeInterval(-ttl)
        dismissedAtByDay = dismissedAtByDay.reduce(into: [:]) { result, entry in
            let activeDismissals = entry.value.filter { $0.value > cutoff }
            if !activeDismissals.isEmpty {
                result[entry.key] = activeDismissals
            }
        }
    }
}

enum BookCurator {
    static func surfacedPages(for day: BookDay, now: Date = Date(), limit: Int = 3) -> [SurfacePage] {
        surfacedPages(for: day, context: .make(for: day), inputs: .empty, now: now, limit: limit)
    }

    static func surfacedPages(
        for day: BookDay,
        inputs: BookSourceInputs,
        now: Date = Date(),
        limit: Int = 3,
        preferences: CuratorSurfacePreferences = .none
    ) -> [SurfacePage] {
        surfacedPages(
            for: day,
            context: .make(for: day),
            inputs: inputs,
            now: now,
            limit: limit,
            preferences: preferences
        )
    }

    static func surfacedPages(
        for day: BookDay,
        context: CuratorContext,
        inputs: BookSourceInputs = .empty,
        now: Date = Date(),
        limit: Int = 3,
        preferences: CuratorSurfacePreferences = .none
    ) -> [SurfacePage] {
        let candidates = BookPageSourceAdapters.active.flatMap { adapter in
            adapter.candidates(for: day, context: context, inputs: inputs, now: now)
        }
        return rankedPages(from: candidates, limit: limit, preferences: preferences).map(\.page)
    }

    static func rankedPages(
        from candidates: [SurfacePage],
        limit: Int = 3,
        preferences: CuratorSurfacePreferences = .none
    ) -> [RankedSurfacePage] {
        let sortedPages = candidates
            .filter { preferences.allows($0) }
            .enumerated()
            .sorted { left, right in
                if left.element.score == right.element.score {
                    return left.offset < right.offset
                }
                return left.element.score > right.element.score
            }
            .map(\.element)
        return unique(sortedPages)
            .prefix(limit)
            .enumerated()
            .map { offset, page in RankedSurfacePage(page: page, rank: offset + 1) }
    }

    private static func unique(_ pages: [SurfacePage]) -> [SurfacePage] {
        var seen = Set<String>()
        return pages.filter { page in
            seen.insert(page.id).inserted
        }
    }
}
