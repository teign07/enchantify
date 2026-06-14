import Foundation


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

struct MoonPhase: Equatable {
    var name: String
    var symbolName: String
    var illuminatedFraction: Double
    var ageDays: Double
    var enchantedLine: String
}

/// Pure local astronomy — close enough for a storybook (within a few hours
/// of the true phase), no network or location required.
enum MoonPhaseCalendar {
    static let synodicMonthDays = 29.530588853

    private static let referenceNewMoon: Date = {
        // 2000-01-06 18:14 UTC, a well-known new moon epoch.
        var components = DateComponents()
        components.year = 2000
        components.month = 1
        components.day = 6
        components.hour = 18
        components.minute = 14
        components.timeZone = TimeZone(identifier: "UTC")
        return Calendar(identifier: .gregorian).date(from: components) ?? Date(timeIntervalSince1970: 947182440)
    }()

    /// The next calendar day (after the given date) that reads as a New Moon —
    /// when the Goblin Market opens.
    static func nextNewMoon(after date: Date = Date(), calendar: Calendar = .current) -> Date {
        var probe = calendar.startOfDay(for: calendar.date(byAdding: .day, value: 1, to: date) ?? date)
        for _ in 0..<35 {
            if phase(on: probe).name == "New Moon" { return probe }
            probe = calendar.date(byAdding: .day, value: 1, to: probe) ?? probe
        }
        return probe
    }

    static func phase(on date: Date = Date()) -> MoonPhase {
        let elapsed = date.timeIntervalSince(referenceNewMoon) / 86_400
        let age = elapsed.truncatingRemainder(dividingBy: synodicMonthDays)
        let normalizedAge = age < 0 ? age + synodicMonthDays : age
        let cyclePosition = normalizedAge / synodicMonthDays
        let illumination = (1 - cos(2 * Double.pi * cyclePosition)) / 2
        let index = Int((cyclePosition * 8).rounded()) % 8

        let (name, symbolName, line): (String, String, String)
        switch index {
        case 0:
            (name, symbolName, line) = (
                "New Moon",
                "moonphase.new.moon",
                "The moon is a held breath tonight, a page before the first word."
            )
        case 1:
            (name, symbolName, line) = (
                "Waxing Crescent",
                "moonphase.waxing.crescent",
                "A thin silver paring of moon is just beginning to write itself."
            )
        case 2:
            (name, symbolName, line) = (
                "First Quarter",
                "moonphase.first.quarter",
                "Half the moon is lit tonight, like a door left ajar."
            )
        case 3:
            (name, symbolName, line) = (
                "Waxing Gibbous",
                "moonphase.waxing.gibbous",
                "The moon is fattening toward full, gathering light like gossip."
            )
        case 4:
            (name, symbolName, line) = (
                "Full Moon",
                "moonphase.full.moon",
                "The moon is full. Every margin of the night is annotated."
            )
        case 5:
            (name, symbolName, line) = (
                "Waning Gibbous",
                "moonphase.waning.gibbous",
                "The moon is giving its light back now, a little each night."
            )
        case 6:
            (name, symbolName, line) = (
                "Last Quarter",
                "moonphase.last.quarter",
                "Half-lit and leaving: the moon keeps only what matters."
            )
        default:
            (name, symbolName, line) = (
                "Waning Crescent",
                "moonphase.waning.crescent",
                "The last sliver of moon hangs like a closing parenthesis."
            )
        }

        return MoonPhase(
            name: name,
            symbolName: symbolName,
            illuminatedFraction: illumination,
            ageDays: normalizedAge,
            enchantedLine: line
        )
    }
}

enum AnchorKind: String, Codable, CaseIterable, Equatable {
    case notice = "NOTICE"
    case embark = "EMBARK"
    case sense = "SENSE"
    case write = "WRITE"
    case rest = "REST"

    var title: String {
        switch self {
        case .notice: return "Notice"
        case .embark: return "Embark"
        case .sense: return "Sense"
        case .write: return "Write"
        case .rest: return "Rest"
        }
    }
}

struct AnchorRecord: Identifiable, Codable, Equatable {
    var id: String
    var name: String
    var latitude: Double
    var longitude: Double
    var radiusMeters: Double
    var kind: AnchorKind
    var belief: Int
    var created: String
    var weather: String
    var moon: String
    var season: String
    var playerWords: String
    var academyEcho: String
    var outerStacksRoom: String
    var fae: String
    var miniStory: String
    var localRule: String
    var visitCount: Int
    var lastVisited: String

    func distanceMeters(to latitude: Double, longitude: Double) -> Double {
        AnchorMath.distanceMeters(
            fromLatitude: self.latitude,
            longitude: self.longitude,
            toLatitude: latitude,
            longitude: longitude
        )
    }

    func checkedIn(on date: Date, calendar: Calendar = .current) -> AnchorRecord {
        var updated = self
        updated.visitCount += 1
        updated.belief += AnchorRegistry.checkInBeliefReward
        updated.lastVisited = AnchorRegistry.visitDateFormatter.string(from: date)
        return updated
    }
}

struct AnchorPlaceDraft: Equatable {
    var name: String
    var words: String
    var kind: AnchorKind
    var latitude: Double
    var longitude: Double
}

struct AnchorProximity: Codable, Equatable {
    var anchor: AnchorRecord
    var distanceMeters: Double

    var isInsideRadius: Bool {
        distanceMeters <= anchor.radiusMeters
    }

    var nextVisitCount: Int {
        anchor.visitCount + 1
    }

    var visitMode: String {
        anchor.visitCount == 0 ? "FIRST_VISIT" : "RETURN_VISIT"
    }
}

enum AnchorRegistry {
    static let proximityRadiusMeters = 200.0
    static let checkInBeliefReward = 5

    /// Anchors that no longer exist in the player's world. Stored ledgers may
    /// still contain them, so they are filtered out on load.
    static let retiredAnchorIDs: Set<String> = ["archive-of-fermentation"]

    /// Ships empty: every Anchor belongs to a player's save, never to the
    /// binary. Local anchors arrive by anchoring places in the world or
    /// by dropping a local-anchors.json into the Documents folder.
    static let defaultAnchors: [AnchorRecord] = []


    static let visitDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    static func nearestAnchor(to latitude: Double, longitude: Double, anchors: [AnchorRecord]) -> AnchorProximity? {
        anchors
            .map { AnchorProximity(anchor: $0, distanceMeters: $0.distanceMeters(to: latitude, longitude: longitude)) }
            .filter(\.isInsideRadius)
            .min { $0.distanceMeters < $1.distanceMeters }
    }

    static func currentSeason(for date: Date, calendar: Calendar = .current) -> String {
        let month = calendar.component(.month, from: date)
        switch month {
        case 3...5: return "Mud Season"
        case 6...8: return "Gold Season"
        case 9...11: return "Stick Season"
        default: return "Deep Winter"
        }
    }
}

enum AnchorMath {
    static func distanceMeters(
        fromLatitude latitude1: Double,
        longitude longitude1: Double,
        toLatitude latitude2: Double,
        longitude longitude2: Double
    ) -> Double {
        let earthRadius = 6_371_000.0
        let phi1 = latitude1 * .pi / 180
        let phi2 = latitude2 * .pi / 180
        let deltaPhi = (latitude2 - latitude1) * .pi / 180
        let deltaLambda = (longitude2 - longitude1) * .pi / 180
        let a = sin(deltaPhi / 2) * sin(deltaPhi / 2)
            + cos(phi1) * cos(phi2) * sin(deltaLambda / 2) * sin(deltaLambda / 2)
        return earthRadius * 2 * atan2(sqrt(a), sqrt(1 - a))
    }
}

/// A favor a character has asked of the player, tucked into the Book's
/// flyleaf. Enchantify's Inside Cover rules: at most five active at a time;
/// completed by a real-world sense act or enchantment plus a sentence of proof.
struct UnwrittenElective: Codable, Identifiable, Equatable {
    var id: String
    var characterID: String
    var characterName: String
    var title: String
    var ask: String
    var whyItMatters: String
    var practiceShape: String
    var createdAt: Date
    var completedAt: Date?
    var proof: String?

    var isActive: Bool { completedAt == nil }

    static let maxActive = 5
    static let completionBeliefReward = 4
}

struct AcademySession: Equatable {
    enum Kind: String {
        case classSession = "class"
        case club
    }

    var id: String
    var kind: Kind
    var name: String
    var leader: String
    var room: String
    var companions: [String]
    var teaches: String
    var style: String
}

/// The Academy's canonical weekly rhythm, ported from Enchantify's
/// school-life schedule: morning class 9-11, afternoon class 1-3, clubs 7-10.
enum AcademyScheduleRegistry {
    static let classes: [String: AcademySession] = [
        "art-of-the-glint": AcademySession(
            id: "art-of-the-glint", kind: .classSession,
            name: "The Art of the Glint", leader: "Professor Lydia Boggle",
            room: "Wing 4 — The Glint Hall",
            companions: ["Zara Finch", "Aria Silverthorn", "Wilbur \"Wordplay\" Lexi"],
            teaches: "Notice (North): the Rut turns the world into wallpaper; one specific, odd detail rips the wallpaper down. Everything in the room is alive if you pay it the courtesy of noticing.",
            style: "playful, specific, concrete, with puns that conceal serious doctrine"
        ),
        "wayfinding-kineticism": AcademySession(
            id: "wayfinding-kineticism", kind: .classSession,
            name: "Wayfinding & Kineticism", leader: "Professor Kyle Momort",
            room: "Wing 2 — The Momentum Yard",
            companions: ["Finn Bridges", "Lara Rourck"],
            teaches: "Embark (East): breaking routine, micro-adventures, the Leap of Ink. Momort teaches it slightly corrupted — escape routes rather than arrivals; the true East is a threshold crossed with intention.",
            style: "brisk, charismatic, a little too fond of exits"
        ),
        "synesthetic-resonance": AcademySession(
            id: "synesthetic-resonance", kind: .classSession,
            name: "Synesthetic Resonance", leader: "Professor Eleanor Euphony",
            room: "Wing 3 — The Resonance Chamber",
            companions: ["Aria Silverthorn", "Elio"],
            teaches: "Sense (South): hearing colors, smelling the history of a room, the Heartbeat of the Stone. Full sensory presence as the solar moment of experience.",
            style: "lush, attentive, hears what the room is humming"
        ),
        "ink-binding": AcademySession(
            id: "ink-binding", kind: .classSession,
            name: "Ink-Binding", leader: "Professor Vivian Villanelle",
            room: "The Inkworks",
            companions: ["Zara Finch", "Ellie Moons"],
            teaches: "Write (West): distilling an entire experience into a single permanent magical sentence. What is written is kept; what is not written dissolves.",
            style: "exacting, lyrical, kind"
        ),
        "quiet-hours": AcademySession(
            id: "quiet-hours", kind: .classSession,
            name: "Quiet Hours", leader: "Professor Cedric Stonebrook",
            room: "The Still Room",
            companions: ["whoever needs it that day"],
            teaches: "Rest (Center): integration and the Permission to Stop. Not a direction — the ground from which all directions emerge.",
            style: "slow, grounded, speaks in almost-koans"
        ),
        "basic-enchantments": AcademySession(
            id: "basic-enchantments", kind: .classSession,
            name: "Basic Enchantments", leader: "Professor Wispwood",
            room: "The Spark Annex",
            companions: ["Finn Bridges", "Wilbur \"Wordplay\" Lexi"],
            teaches: "Casting text-based enchantments on ordinary subjects: Everything Speaks, Everything's Poetry, and how to let an object answer through close attention.",
            style: "scattered, sparking, delighted by accidents"
        ),
        "book-jumping": AcademySession(
            id: "book-jumping", kind: .classSession,
            name: "Book Jumping", leader: "Professor Permancer",
            room: "The Vault of Doors",
            companions: ["Zara Finch", "Orion Blackthorn"],
            teaches: "Entering and exiting stories safely: landing without tearing the page, reading the weather of a narrative before stepping in, and always knowing where your bookmark is.",
            style: "precise, adventurous, fiercely safety-minded"
        ),
        "compass-running": AcademySession(
            id: "compass-running", kind: .classSession,
            name: "Compass Running", leader: "Professor Cedric Stonebrook",
            room: "The Open Field Gate",
            companions: ["the whole motley Saturday crew"],
            teaches: "Full N-E-S-W compass runs in the field: constraints first, magic after, one small adventure with a souvenir sentence at the end.",
            style: "practical, weathered, quietly encouraging"
        )
    ]

    static let clubs: [String: AcademySession] = [
        "compass-society": AcademySession(
            id: "compass-society", kind: .club,
            name: "The Compass Society", leader: "Zara Finch (de facto anchor)",
            room: "The Secret Garden of Prose",
            companions: ["Zara Finch", "Lara Rourck", "Elio (47 Compass Runs, won't explain the 47th)"],
            teaches: "Members read their One-Sentence Souvenirs aloud with real reverence. No one mocks a sentence here. Sharing a souvenir makes it more real.",
            style: "warm, literary, slightly emotionally intense"
        ),
        "marginalia-guild": AcademySession(
            id: "marginalia-guild", kind: .club,
            name: "The Marginalia Guild", leader: "Professor Lydia Boggle (officially)",
            room: "The Corridor of Whispered Secrets",
            companions: ["Ellie Moons", "a second-year six months deep in one mythology volume"],
            teaches: "Annotating books together and leaving notes for future readers — the best conversations are held with someone who read the same book fifty years ago and wrote something true in the margin.",
            style: "playful, curious, surprisingly deep"
        ),
        "inkwright-society": AcademySession(
            id: "inkwright-society", kind: .club,
            name: "The Inkwright Society", leader: "Professor Maxwell Thorne (observing)",
            room: "The Bibliophonic Hall",
            companions: ["Finn Bridges", "Emberheart students with serious notebooks"],
            teaches: "Write, share, workshop — honest first, kind second. Each meeting ends with a burning: a piece read aloud, then ritually burned, its smoke becoming words absorbed into the library ceiling.",
            style: "intense, creative, committed — the writing here is meant"
        ),
        "book-jumpers": AcademySession(
            id: "book-jumpers", kind: .club,
            name: "The Book Jumpers", leader: "Professor Permancer",
            room: "The Vault of Doors",
            companions: ["Zara Finch", "Orion Blackthorn"],
            teaches: "Short, controlled jumps into well-mapped stories. Half the meeting is planning the landing; the other half is arguing about what counts as a door.",
            style: "adventurous, giddy, strictly rule-bound about exits"
        )
    ]

    /// weekday uses Calendar's convention: 1 = Sunday ... 7 = Saturday.
    static let week: [Int: (morning: String?, afternoon: String?, club: String?)] = [
        1: ("book-jumping", nil, "compass-society"),
        2: ("art-of-the-glint", "ink-binding", "inkwright-society"),
        3: ("wayfinding-kineticism", "synesthetic-resonance", "marginalia-guild"),
        4: ("art-of-the-glint", "quiet-hours", nil),
        5: ("wayfinding-kineticism", "ink-binding", "marginalia-guild"),
        6: ("synesthetic-resonance", "basic-enchantments", "book-jumpers"),
        7: ("compass-running", nil, nil)
    ]

    static func sessionInProgress(at date: Date, calendar: Calendar = .current) -> (session: AcademySession, block: String)? {
        let weekday = calendar.component(.weekday, from: date)
        let hour = calendar.component(.hour, from: date)
        guard let day = week[weekday] else { return nil }
        if (9..<11).contains(hour), let id = day.morning, let session = classes[id] {
            return (session, "morning")
        }
        if (13..<15).contains(hour), let id = day.afternoon, let session = classes[id] {
            return (session, "afternoon")
        }
        if (19..<22).contains(hour), let id = day.club, let session = clubs[id] {
            return (session, "club")
        }
        return nil
    }

    static func nextSessionDescription(after date: Date, calendar: Calendar = .current) -> String {
        let weekday = calendar.component(.weekday, from: date)
        let hour = calendar.component(.hour, from: date)
        guard let day = week[weekday] else { return "The halls are between bells." }
        if hour < 9, let id = day.morning, let session = classes[id] {
            return "\(session.name) with \(session.leader) begins at nine bells in \(session.room)."
        }
        if hour < 13, let id = day.afternoon, let session = classes[id] {
            return "\(session.name) with \(session.leader) begins at one bell in \(session.room)."
        }
        if hour < 19, let id = day.club, let session = clubs[id] {
            return "\(session.name) gathers at seven bells in \(session.room)."
        }
        return "The halls are between bells. Tomorrow's first class is already chalked on the board."
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

/// Real names the local model must never write onto pages or shareable
/// artifacts. Ships empty; the app fills it from the player's own About You
/// facts at launch, so privacy follows the save file, not the binary.
enum PersonalNameGuard {
    static var blockedNames: [String] = []

    static func update(from facts: [SelfFact]) {
        blockedNames = facts
            .filter { fact in
                fact.tags.contains { $0.contains("name") || $0.contains("people") || $0.contains("identity") }
            }
            .flatMap { $0.answer.split(separator: " ").map(String.init) }
            .filter { $0.count > 1 }
    }
}

// MARK: - Chapters and Talismans

/// One of the Academy's philosophical houses, from Enchantify canon.
struct AcademyChapter: Identifiable, Codable, Equatable {
    var id: String
    var name: String
    var philosophy: String
    var founder: String
    var traits: [String]
    var compassFlavor: String
    var writeFraming: String
    var storyBias: String
    var symbolName: String
    var talismanID: String
    var talismanName: String
    var isHidden: Bool = false
}

enum AcademyChapterRegistry {
    static let chapters: [AcademyChapter] = [
        AcademyChapter(
            id: "emberheart",
            name: "Emberheart",
            philosophy: "Life is a story you write yourself. You are the author, the protagonist, and the pen.",
            founder: "Ignatius Emberheart, whose flame never dwindled",
            traits: ["independence", "ambition", "creativity", "resilience"],
            compassFlavor: "What do you choose to see right now?",
            writeFraming: "Write the sentence that you need to read tomorrow morning.",
            storyBias: "Lean toward self-agency: let the scene offer the player a bold authored choice, an Embark opportunity, a door they could open themselves.",
            symbolName: "flame",
            talismanID: "ember-seal",
            talismanName: "The Ember Seal"
        ),
        AcademyChapter(
            id: "mossbloom",
            name: "Mossbloom",
            philosophy: "Life is a story written by something larger. Your role is to listen, understand, and play your part with grace.",
            founder: "Elowen Mossbloom, who unraveled the stories whispered by the wind",
            traits: ["reflectiveness", "wisdom", "patience", "sensitivity"],
            compassFlavor: "What is the world already trying to show you?",
            writeFraming: "Write the sentence the world wrote through you today.",
            storyBias: "Lean toward receptivity: slow the scene down, let something larger speak through small natural details, reward listening over acting.",
            symbolName: "leaf",
            talismanID: "moss-clasp",
            talismanName: "The Moss Clasp"
        ),
        AcademyChapter(
            id: "tidecrest",
            name: "Tidecrest",
            philosophy: "Life is not a story at all. It is a series of moments — beautiful, unpredictable, and complete in themselves.",
            founder: "Captain Orion Tidecrest, explorer of seas and stories",
            traits: ["spontaneity", "adaptability", "curiosity", "presence"],
            compassFlavor: "What's the first thing that catches you completely off guard?",
            writeFraming: "Write a sentence that surprises even you.",
            storyBias: "Lean toward spontaneity: let one genuinely unpredictable thing happen mid-scene, unannounced, and let the present moment matter more than any arc.",
            symbolName: "water.waves",
            talismanID: "tide-glass",
            talismanName: "The Tide Glass"
        ),
        AcademyChapter(
            id: "riddlewind",
            name: "Riddlewind",
            philosophy: "Life is a story we write together. Every person's choices contribute to a shared narrative.",
            founder: "Althea Riddlewind, who solved mysteries by asking for help",
            traits: ["unity", "empathy", "collaboration", "open-mindedness"],
            compassFlavor: "Ask someone nearby what they noticed today.",
            writeFraming: "Write a sentence that captures what you and someone else both noticed.",
            storyBias: "Lean toward co-authorship: put two characters in genuine dialogue, let the scene need more than one person to resolve, make collaboration the magic.",
            symbolName: "puzzlepiece",
            talismanID: "wind-cipher",
            talismanName: "The Wind Cipher"
        ),
        AcademyChapter(
            id: "duskthorn",
            name: "Duskthorn",
            philosophy: "There is no story without conflict. The only cure for the Nothing is a story so interesting it refuses to be erased.",
            founder: "Unrecorded. The Chapter does not appear in the sorting ledger.",
            traits: ["tension", "honesty", "necessary darkness", "narrative balance"],
            compassFlavor: "What are you avoiding looking at?",
            writeFraming: "Write the sentence you don't want to write.",
            storyBias: "Lean toward friction: introduce one honest complication, obstacle, or uncomfortable truth — not cruelty, but the tension that makes a story worth keeping.",
            symbolName: "theatermasks",
            talismanID: "dusk-thorn",
            talismanName: "The Dusk Thorn"
        )
    ]

    static let publicChapters = chapters.filter { !$0.isHidden }

    static func chapter(id: String) -> AcademyChapter? {
        chapters.first { $0.id == id }
    }

    static func chapter(named name: String?) -> AcademyChapter? {
        guard let name else { return nil }
        return chapters.first { $0.name.caseInsensitiveCompare(name) == .orderedSame }
    }

    static func chapter(forTalismanID talismanID: String) -> AcademyChapter? {
        chapters.first { $0.talismanID == talismanID }
    }
}

struct ChapterBindingReadiness: Equatable {
    var isReady: Bool
    var keptDayCount: Int
    var keptPageCount: Int
    var daysSinceFirstKeptPage: Int?
    var primerStage: Int
}

struct ChapterBindingChoice: Equatable {
    var chapter: AcademyChapter
    var scores: [String: Int]
    var evidenceLines: [String]
}

enum ChapterBindingOracle {
    static let minimumKeptDays = 3
    static let minimumKeptPages = 5
    static let minimumDaysSinceFirstKeptPage = 3
    static let matureDaysSinceFirstKeptPage = 7

    static func readiness(days: [BookDay], now: Date = Date(), calendar: Calendar = .current) -> ChapterBindingReadiness {
        let keptDays = days
            .map { day in (day, day.capturedPages) }
            .filter { !$0.1.isEmpty }
            .sorted { $0.0.date < $1.0.date }
        let keptPageCount = keptDays.reduce(0) { $0 + $1.1.count }
        let firstKeptAt = keptDays.flatMap { $0.1.map(\.createdAt) }.min()
        let daysSinceFirst = firstKeptAt.map {
            max(0, calendar.dateComponents([.day], from: calendar.startOfDay(for: $0), to: calendar.startOfDay(for: now)).day ?? 0)
        }
        let hasEnoughPages = keptDays.count >= minimumKeptDays && keptPageCount >= minimumKeptPages
        let hasEnoughTime = (daysSinceFirst ?? 0) >= minimumDaysSinceFirstKeptPage
        let isMature = (daysSinceFirst ?? 0) >= matureDaysSinceFirstKeptPage && keptPageCount >= 3
        let primerStage: Int
        if keptDays.count >= 2 || keptPageCount >= 2 {
            primerStage = min(3, max(1, keptDays.count))
        } else {
            primerStage = 0
        }
        return ChapterBindingReadiness(
            isReady: (hasEnoughPages && hasEnoughTime) || isMature,
            keptDayCount: keptDays.count,
            keptPageCount: keptPageCount,
            daysSinceFirstKeptPage: daysSinceFirst,
            primerStage: primerStage
        )
    }

    static func chooseChapter(
        days: [BookDay],
        selfFacts: [SelfFact],
        continuity: LiteraryContinuityDigest = .empty,
        entityBeliefOffsets: [String: Int] = [:]
    ) -> ChapterBindingChoice {
        let pages = days.flatMap(\.capturedPages)
        var scores = Dictionary(uniqueKeysWithValues: AcademyChapterRegistry.publicChapters.map { ($0.id, 0) })
        var evidence: [String: [String]] = Dictionary(uniqueKeysWithValues: AcademyChapterRegistry.publicChapters.map { ($0.id, []) })

        func add(_ chapterID: String, _ amount: Int, _ line: String) {
            scores[chapterID, default: 0] += amount
            if evidence[chapterID, default: []].count < 3 {
                evidence[chapterID, default: []].append(line)
            }
        }

        for page in pages {
            let text = ([page.promptText, page.userInput] + page.tags).joined(separator: " ").lowercased()
            switch page.type {
            case .diary:
                add("emberheart", 3, "Your diary pages keep reaching for authorship.")
                add("mossbloom", 1, "Your diary pages pause long enough to listen.")
            case .souvenir:
                add("tidecrest", 3, "Your souvenirs keep trusting the present moment.")
                add("mossbloom", 1, "Your souvenirs notice what the world is already saying.")
            case .mood, .rest, .body, .fuel:
                add("mossbloom", 3, "Your kept body and mood pages treat attention as care.")
            case .letter, .castMember:
                add("riddlewind", 3, "Your kept letters and people-pages lean toward co-authorship.")
            case .wonderCompass, .anchor, .weather, .illuminatedPhoto:
                add("tidecrest", 2, "Your kept field pages follow what catches you off guard.")
            case .narrativeOS, .bookConnections, .bookNotices, .bookRemembered, .marginsAtlas, .gossip:
                add("riddlewind", 2, "Your story pages keep finding relation between separate lives.")
            case .enchantment, .academyClass, .elective:
                add("emberheart", 2, "Your practice pages put a hand on the pen.")
            default:
                break
            }

            if text.containsAny(["choose", "make", "build", "start", "create", "try", "brave", "bold"]) {
                add("emberheart", 2, "The language of making and choosing appears in the margins.")
            }
            if text.containsAny(["listen", "quiet", "soft", "rest", "moss", "tree", "rain", "weather", "body", "slow"]) {
                add("mossbloom", 2, "The margins keep returning to quiet, body, weather, and listening.")
            }
            if text.containsAny(["surprise", "walk", "adventure", "moment", "now", "harbor", "water", "coffee", "light", "street"]) {
                add("tidecrest", 2, "The pages keep trusting small adventures and sudden particulars.")
            }
            if text.containsAny(["together", "amanda", "friend", "letter", "talk", "asked", "shared", "we ", "us "]) {
                add("riddlewind", 5, "The pages keep brightening when another person enters the sentence.")
            }
            if text.containsAny(["hard", "truth", "avoid", "afraid", "fear", "conflict", "nothing", "dark", "thorn", "boundary", "protect", "honest", "difficult"]) {
                add("duskthorn", 4, "The margins keep naming what is difficult instead of smoothing it away.")
            }
        }

        for fact in selfFacts where fact.usePermission != .doNotUse {
            let text = ([fact.question, fact.answer, fact.bookTranslation] + fact.tags).joined(separator: " ").lowercased()
            if text.containsAny(["write", "make", "create", "choose", "agency", "independent"]) {
                add("emberheart", 3, "What you told the Book about yourself values authorship.")
            }
            if text.containsAny(["listen", "wonder", "gentle", "patient", "nature", "world"]) {
                add("mossbloom", 3, "What you told the Book about yourself values receptive wonder.")
            }
            if text.containsAny(["curious", "adventure", "spontaneous", "present", "moment", "explore"]) {
                add("tidecrest", 3, "What you told the Book about yourself values curiosity in motion.")
            }
            if text.containsAny(["together", "people", "amanda", "community", "kind", "friend", "empathy"]) {
                add("riddlewind", 3, "What you told the Book about yourself values shared story.")
            }
            if text.containsAny(["honest", "boundary", "protect", "conflict", "shadow", "dark", "difficult", "avoid", "truth", "tension"]) {
                add("duskthorn", 3, "What you told the Book about yourself values difficult truth and protection.")
            }
        }

        for signal in continuity.signals.prefix(12) {
            let text = ([signal.subjectName, signal.line] + signal.tags).joined(separator: " ").lowercased()
            let amount = max(1, min(4, signal.strength / 25))
            if text.containsAny(["make", "start", "create", "courage", "author"]) {
                add("emberheart", amount, "The Book has noticed an authorship pattern: \(signal.subjectName).")
            }
            if text.containsAny(["weather", "body", "quiet", "rest", "tree", "rain", "listen"]) {
                add("mossbloom", amount, "The Book has noticed a listening pattern: \(signal.subjectName).")
            }
            if text.containsAny(["harbor", "water", "walk", "moment", "curiosity", "surprise", "coffee"]) {
                add("tidecrest", amount, "The Book has noticed a present-tense pattern: \(signal.subjectName).")
            }
            if text.containsAny(["amanda", "friend", "companionship", "together", "letter", "shared"]) {
                add("riddlewind", amount, "The Book has noticed a co-authored pattern: \(signal.subjectName).")
            }
            if text.containsAny(["conflict", "boundary", "nothing", "avoidance", "protection", "shadow", "truth", "tension"]) {
                add("duskthorn", amount, "The Book has noticed a thorned pattern: \(signal.subjectName).")
            }
        }

        for chapter in AcademyChapterRegistry.publicChapters {
            let offset = entityBeliefOffsets[chapter.talismanID] ?? 0
            if offset != 0 {
                add(chapter.id, max(-12, min(40, offset)), "\(chapter.talismanName) already holds \(offset) invested Belief.")
            }
        }

        let chosen = AcademyChapterRegistry.publicChapters.max { left, right in
            let leftScore = scores[left.id, default: 0]
            let rightScore = scores[right.id, default: 0]
            if leftScore == rightScore {
                return left.id > right.id
            }
            return leftScore < rightScore
        } ?? AcademyChapterRegistry.publicChapters[0]
        let lines = evidence[chosen.id, default: []].isEmpty
            ? ["The Book chose by the faintest pressure of the ink, not by a questionnaire."]
            : evidence[chosen.id, default: []]
        return ChapterBindingChoice(chapter: chosen, scores: scores, evidenceLines: lines)
    }
}

private extension String {
    func containsAny(_ needles: [String]) -> Bool {
        needles.contains { contains($0) }
    }
}

enum ChapterTalismanBeliefMoveKind: String, Codable, Equatable {
    case giveBelief
    case takeBelief

    var title: String {
        switch self {
        case .giveBelief:
            return "gave Belief"
        case .takeBelief:
            return "tried to take Belief"
        }
    }
}

struct ChapterTalismanBeliefMove: Codable, Equatable {
    var kind: ChapterTalismanBeliefMoveKind
    var actorID: String
    var actorName: String
    var actorChapter: String
    var targetTalismanID: String
    var targetTalismanName: String
    var targetChapter: String
    var amount: Int
    var succeeded: Bool

    var summaryLine: String {
        switch kind {
        case .giveBelief:
            return "\(actorName) gave \(amount) Belief to \(targetTalismanName) of Chapter \(targetChapter)."
        case .takeBelief:
            let result = succeeded ? "and the attempt caught" : "but the talisman held"
            return "\(actorName) tried to take \(amount) Belief from \(targetTalismanName) of Chapter \(targetChapter), \(result)."
        }
    }

    var promptLine: String {
        switch kind {
        case .giveBelief:
            return "\(actorName) may sometimes give \(amount) Belief to their own Chapter talisman, \(targetTalismanName), when it fits the scene; if used, it counts as \(targetTalismanID):+\(amount)."
        case .takeBelief:
            return "\(actorName) may sometimes try to take \(amount) Belief from rival Chapter \(targetChapter)'s talisman, \(targetTalismanName); if the attempt succeeds, it counts as \(targetTalismanID):-\(amount), and if it fails it counts as no delta."
        }
    }

    var ledgerDelta: Int {
        switch kind {
        case .giveBelief:
            return amount
        case .takeBelief:
            return succeeded ? -amount : 0
        }
    }

    var ledgerToken: String? {
        let delta = ledgerDelta
        guard delta != 0 else { return nil }
        return "\(targetTalismanID):\(delta)"
    }
}

enum ChapterTalismanBeliefMoves {
    static func move(
        for actor: NarrativeWorldEntity,
        actionKind: GossipSimulationActionKind,
        seed: Int
    ) -> ChapterTalismanBeliefMove? {
        guard actionKind == .investBelief || actionKind == .attackBelief else { return nil }
        guard shouldSurface(for: actor, seed: seed) else { return nil }
        switch actionKind {
        case .investBelief:
            return giveMove(for: actor)
        case .attackBelief:
            return takeMove(for: actor, seed: seed)
        case .takeAction:
            return nil
        }
    }

    static func moves(for actors: [NarrativeWorldEntity], seed: Int) -> [ChapterTalismanBeliefMove] {
        actors.enumerated().compactMap { offset, actor in
            let localSeed = seed + offset * 37
            if localSeed % 2 == 0, let move = giveMove(for: actor) {
                return shouldSurface(for: actor, seed: localSeed) ? move : nil
            }
            guard shouldSurface(for: actor, seed: localSeed) else { return nil }
            return takeMove(for: actor, seed: localSeed)
        }
    }

    static func promptLines(for actors: [NarrativeWorldEntity], seed: Int) -> [String] {
        moves(for: actors, seed: seed).map(\.promptLine)
    }

    static func giveMove(for actor: NarrativeWorldEntity) -> ChapterTalismanBeliefMove? {
        guard let chapter = AcademyChapterRegistry.chapter(named: actor.chapter) else { return nil }
        return ChapterTalismanBeliefMove(
            kind: .giveBelief,
            actorID: actor.id,
            actorName: actor.name,
            actorChapter: chapter.name,
            targetTalismanID: chapter.talismanID,
            targetTalismanName: chapter.talismanName,
            targetChapter: chapter.name,
            amount: 1,
            succeeded: true
        )
    }

    static func takeMove(for actor: NarrativeWorldEntity, seed: Int) -> ChapterTalismanBeliefMove? {
        guard let actorChapter = AcademyChapterRegistry.chapter(named: actor.chapter) else { return nil }
        let rivals = AcademyChapterRegistry.chapters.filter { $0.id != actorChapter.id }
        guard !rivals.isEmpty else { return nil }
        let target = rivals[stableIndex(for: "\(actor.id)-\(seed)-rival-talisman", count: rivals.count)]
        return ChapterTalismanBeliefMove(
            kind: .takeBelief,
            actorID: actor.id,
            actorName: actor.name,
            actorChapter: actorChapter.name,
            targetTalismanID: target.talismanID,
            targetTalismanName: target.talismanName,
            targetChapter: target.name,
            amount: 1,
            succeeded: stableIndex(for: "\(actor.id)-\(target.id)-\(seed)-take-result", count: 100) < 45
        )
    }

    private static func shouldSurface(for actor: NarrativeWorldEntity, seed: Int) -> Bool {
        if actor.tags.contains("nothing") || actor.faults.contains(where: { $0.localizedCaseInsensitiveContains("attack") }) {
            return seed % 2 == 0
        }
        return stableIndex(for: "\(actor.id)-\(seed)-chapter-talisman-sometimes", count: 100) < 34
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

/// Whichever Chapter talisman currently holds the most Belief sets the
/// Labyrinth's ambient philosophical tone — NPC investment moved them in
/// Enchantify; here the player's own Glow-giving moves them.
enum TalismanAscendancy {
    static func ascendant(
        entities: [NarrativeWorldEntity],
        beliefOffsets: [String: Int]
    ) -> NarrativeWorldEntity? {
        entities
            .filter { $0.kind == .talisman }
            .max { left, right in
                let leftBelief = left.belief + (beliefOffsets[left.id] ?? 0)
                let rightBelief = right.belief + (beliefOffsets[right.id] ?? 0)
                if leftBelief == rightBelief {
                    return left.id > right.id
                }
                return leftBelief < rightBelief
            }
    }

    static func influenceLine(for talisman: NarrativeWorldEntity) -> String {
        let chapter = AcademyChapterRegistry.chapter(forTalismanID: talisman.id)
        let bias = chapter?.storyBias ?? talisman.goals.first ?? "Let its philosophy color the scene."
        return "The \(chapter?.name ?? "ascendant") talisman \(talisman.name) holds the most Belief right now. \(bias)"
    }
}


/// One real place near the player, scouted from Apple Maps. Characters may
/// only name businesses from this list — never invented ones.
struct LocalPlaceSignal: Codable, Equatable, Identifiable {
    var id: String
    var name: String
    var category: String
    var distanceLabel: String
    var locality: String

    var promptLine: String {
        let town = locality.isEmpty ? "" : ", \(locality)"
        return "\(name) (\(category), \(distanceLabel)\(town))"
    }
}


struct ElectiveOfferDraft: Equatable {
    var title: String
    var ask: String
    var whyItMatters: String
    var practiceShape: String
}

enum ElectiveOfferFallback {
    static func offer(surface: SurfacePage) -> ElectiveOfferDraft {
        let sender = surface.payload.metadata["senderName"] ?? "A character"
        let interest = surface.payload.metadata["senderInterest"] ?? "the ordinary magic of where you live"
        if let firstPlace = surface.payload.metadata["nearbyPlaces"]?
            .split(separator: "\n").first.map(String.init),
           let placeName = firstPlace.split(separator: "(").first?.trimmingCharacters(in: .whitespaces),
           !placeName.isEmpty {
            return ElectiveOfferDraft(
                title: "A Visit to \(placeName)",
                ask: "\(sender) asks: go to \(placeName) this week. Find the thing they are quietly proudest of — it is usually near the register or on the most worn shelf — smell it if it can be smelled, and photograph it or bring back one sentence about it.",
                whyItMatters: "It feeds what \(sender) has been privately studying: \(interest).",
                practiceShape: "One photo or one specific sentence from inside \(placeName)."
            )
        }
        return ElectiveOfferDraft(
            title: "A Field Note for \(sender)",
            ask: "\(sender) asks: somewhere in your town today, find one small thing that connects to \(interest). Bring back a single sentence about exactly what you found and where it was.",
            whyItMatters: "It feeds what \(sender) has been privately studying.",
            practiceShape: "One specific sentence of proof, with a real detail in it."
        )
    }
}

// MARK: - Fuel arithmetic
//
// Free-text fuel entries ("two eggs, toast with butter, coffee") become
// rough nutrition estimates. Parsing and scaling are pure and tested; the
// network lookup lives app-side. Numbers are always presented as Vellum's
// rough arithmetic, never as gospel.

struct FuelItem: Equatable {
    var name: String
    var quantity: Double
}

struct NutritionEstimate: Equatable {
    var kilocalories: Double
    var protein: Double
    var carbohydrates: Double
    var fat: Double

    static let zero = NutritionEstimate(kilocalories: 0, protein: 0, carbohydrates: 0, fat: 0)

    static func + (left: NutritionEstimate, right: NutritionEstimate) -> NutritionEstimate {
        NutritionEstimate(
            kilocalories: left.kilocalories + right.kilocalories,
            protein: left.protein + right.protein,
            carbohydrates: left.carbohydrates + right.carbohydrates,
            fat: left.fat + right.fat
        )
    }

    var chartLine: String {
        "≈ \(Int(kilocalories.rounded())) kcal · P \(Int(protein.rounded()))g · C \(Int(carbohydrates.rounded()))g · F \(Int(fat.rounded()))g (Vellum's rough arithmetic)"
    }
}

enum FuelParser {
    private static let numberWords: [String: Double] = [
        "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "half": 0.5, "couple": 2, "few": 3, "some": 1, "double": 2
    ]

    /// Common-portion grams for staples, applied against per-100g data.
    /// Unknown foods default to 100g — a rough but honest middle.
    static let portionGrams: [String: Double] = [
        "egg": 50, "eggs": 50, "toast": 30, "bread": 30, "slice": 30,
        "banana": 118, "apple": 180, "orange": 130, "coffee": 240,
        "tea": 240, "milk": 244, "butter": 14, "cheese": 28, "yogurt": 170,
        "rice": 160, "pasta": 140, "oatmeal": 234, "cereal": 40,
        "chicken": 140, "salmon": 140, "fish": 140, "steak": 170, "beef": 140,
        "bacon": 12, "sausage": 50, "pizza": 110, "burger": 150, "sandwich": 150,
        "salad": 100, "soup": 245, "beer": 355, "wine": 150, "kombucha": 240,
        "cookie": 30, "chocolate": 40, "pie": 125, "avocado": 100, "potato": 170
    ]

    static func items(from entry: String) -> [FuelItem] {
        let lowered = entry.lowercased()
            .replacingOccurrences(of: " with ", with: ", ")
            .replacingOccurrences(of: " and ", with: ", ")
            .replacingOccurrences(of: " plus ", with: ", ")
            .replacingOccurrences(of: "&", with: ",")
        return lowered
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .compactMap { phrase in
                var words = phrase.split(separator: " ").map(String.init)
                var quantity = 1.0
                if let first = words.first {
                    if let numeric = Double(first) {
                        quantity = numeric
                        words.removeFirst()
                    } else if let worded = numberWords[first] {
                        quantity = worded
                        words.removeFirst()
                    }
                }
                // Strip leading filler like "of", "cups", "cup", "bowl of".
                while let first = words.first,
                      ["of", "cup", "cups", "bowl", "glass", "mug", "plate", "piece", "pieces", "slices"].contains(first) {
                    words.removeFirst()
                }
                let name = words.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
                guard !name.isEmpty, name.count > 1 else { return nil }
                return FuelItem(name: name, quantity: max(0.25, min(quantity, 12)))
            }
    }

    /// Scale per-100g nutrients to a portion of this item.
    static func scale(per100g: NutritionEstimate, item: FuelItem) -> NutritionEstimate {
        let nameWords = item.name.split(separator: " ").map(String.init)
        let grams = nameWords.compactMap { portionGrams[$0] }.first
            ?? portionGrams[item.name]
            ?? 100
        let factor = grams / 100 * item.quantity
        return NutritionEstimate(
            kilocalories: per100g.kilocalories * factor,
            protein: per100g.protein * factor,
            carbohydrates: per100g.carbohydrates * factor,
            fat: per100g.fat * factor
        )
    }
}

// MARK: - The Book Fae and their Bargains
//
// The Fae are born from the ink and have never touched the world they have read
// ten thousand descriptions of. A reader is their field agent in a world of
// matter. A bargain is not a quest: the fae gives first (unprompted), then the
// reader owes a sensory field report. Fae never trade in Belief. The stakes are
// a parallel economy — Warmth (per-species reputation), Attention (the goblins'
// currency), and functional Gifts that are fronted on credit and go cold if the
// debt is not paid. See lore/creatures.md and lore/outer-stacks.md.

enum FaeKind: String, Codable, CaseIterable, Identifiable, Equatable {
    case bookSprite
    case sentenceSalamander
    case punctuationPixie
    case literaryElf
    case deepLoreDwarf
    case goblin

    var id: String { rawValue }

    var name: String {
        switch self {
        case .bookSprite: return "Book Sprite"
        case .sentenceSalamander: return "Sentence Salamander"
        case .punctuationPixie: return "Punctuation Pixie"
        case .literaryElf: return "Literary Elf"
        case .deepLoreDwarf: return "Deep Lore Dwarf"
        case .goblin: return "Marginalia Goblin"
        }
    }

    var symbolName: String {
        switch self {
        case .bookSprite: return "sparkle"
        case .sentenceSalamander: return "flame"
        case .punctuationPixie: return "ellipsis.curlybraces"
        case .literaryElf: return "pencil.and.outline"
        case .deepLoreDwarf: return "mountain.2"
        case .goblin: return "tag"
        }
    }

    /// What this species hungers to be brought — the kind of noticing they buy.
    var appetite: String {
        switch self {
        case .bookSprite: return "the unfinished, the waiting, things that ended without ending"
        case .sentenceSalamander: return "the alive moment — what was warm, charged, more than it should have been"
        case .punctuationPixie: return "rhythm and pause — a place that feels like a comma, a thing that is an exclamation point"
        case .literaryElf: return "precision — one true thing, described exactly"
        case .deepLoreDwarf: return "the underlayer — the oldest, the overlooked, the thing holding something else up"
        case .goblin: return "the specific unchosen detail; the gap between what a thing is called and what it is"
        }
    }

    /// Voice directive handed to Gemma when the fae speaks.
    var voiceDirective: String {
        switch self {
        case .bookSprite:
            return "Melancholy, certain, airy. Speaks in past tense about things that have not happened yet. Never asks questions; makes observations."
        case .sentenceSalamander:
            return "Honest, warm, reactive. Cannot be fooled by performance. Does not criticize — simply glows or goes cold."
        case .punctuationPixie:
            return "Fragments. Mid-sentence pivots—. Never finishes a thought before starting a new one. Calls the reader a different name each time."
        case .literaryElf:
            return "Formal, exacting, ceremonial. Long evaluating pauses. Sends sloppiness away with a single word: 'Again.' Rewards precision with gravity."
        case .deepLoreDwarf:
            return "Slow, weighty, no wasted words. Considers everything before speaking. Remembers everything and will come to collect."
        case .goblin:
            return "Mercantile, precise, unpredictable. Every exchange is a transaction in attention. A performed observation insults them; a genuine one opens doors."
        }
    }

    /// The functional gift this species fronts on a bargain.
    var giftEffect: FaeGiftEffect {
        switch self {
        case .bookSprite: return .loosePage
        case .sentenceSalamander: return .quieting
        case .punctuationPixie: return .reshelving
        case .literaryElf: return .longMemory
        case .deepLoreDwarf: return .reshelving
        case .goblin: return .callingCard
        }
    }
}

/// What a fronted Gift actually does in the app. These are the real stakes:
/// each one changes the reader's experience, and each goes cold if the
/// bargain that fronted it is left unpaid.
enum FaeGiftEffect: String, Codable, Equatable {
    case reshelving   // force-surfaces a chosen dormant page source for a day
    case quieting     // lowers the Nothing's grey by one level for a day
    case longMemory   // pins a kept page to reliably resurface as Book Remembered
    case callingCard  // opens a Goblin Market window (consumable)
    case loosePage    // a collectible whose text regenerates each read

    var title: String {
        switch self {
        case .reshelving: return "Reshelving"
        case .quieting: return "Quieting"
        case .longMemory: return "Long Memory"
        case .callingCard: return "Calling Card"
        case .loosePage: return "Loose Page"
        }
    }

    var effectLine: String {
        switch self {
        case .reshelving: return "Pulls one resting kind of page back onto the shelf where you'll see it."
        case .quieting: return "Holds the grey of the Nothing back by one shade for a day."
        case .longMemory: return "Keeps one kept page from being forgotten; the Book will return it."
        case .callingCard: return "Opens the Goblin Market when you spend it."
        case .loosePage: return "A page that never reads the same way twice."
        }
    }
}

struct FaeGift: Identifiable, Codable, Equatable {
    var id: String
    var faeKind: FaeKind
    var name: String
    var descriptionText: String
    var effect: FaeGiftEffect
    var isCold: Bool
    var acquiredAt: Date
    var chargesRemaining: Int?
    var boundSourceID: String?

    var isActive: Bool {
        guard !isCold else { return false }
        if let chargesRemaining { return chargesRemaining > 0 }
        return true
    }
}

enum FaeBargainStatus: String, Codable, Equatable {
    case owed        // gift fronted, payment due
    case delivered   // paid and accepted
    case lapsed      // deadline passed; gift cold, market closed until repaired
}

struct FaeBargain: Identifiable, Codable, Equatable {
    var id: String
    var faeKind: FaeKind
    var slot: String
    var giftID: String
    var giftName: String
    var giftEffectLine: String
    var openingGesture: String   // what the fae already gave / did, unprompted
    var terms: String            // the noticing owed
    var offeredAt: Date
    var deadline: Date
    var status: FaeBargainStatus
    var fieldReport: String?
    var faeResponse: String?
    var rewardText: String?
    var deliveredAt: Date?

    var isOpen: Bool { status == .owed }
}

/// The reader's standing with the Fae. Optional on the vault for migration.
struct FaePlayerState: Codable, Equatable {
    var warmth: [String: Int] = [:]
    var attention: Int = 0
    var bargains: [FaeBargain] = []
    var gifts: [FaeGift] = []
    var lastBargainOfferedAt: Date?
    var lastMarketCardAt: Date?

    init() {}

    func warmth(for kind: FaeKind) -> Int { warmth[kind.rawValue] ?? 0 }

    var openBargains: [FaeBargain] { bargains.filter { $0.isOpen } }

    func hasOpenBargain(with kind: FaeKind) -> Bool {
        bargains.contains { $0.faeKind == kind && $0.status == .owed }
    }

    /// A species whose last bargain lapsed has its market closed until repaired.
    func marketIsClosed(for kind: FaeKind) -> Bool {
        bargains.contains { $0.faeKind == kind && $0.status == .lapsed }
    }

    var activeGifts: [FaeGift] { gifts.filter { $0.isActive } }
}

/// Goblin mood follows the season, shifting tone and generosity.
enum GoblinMood: String, Equatable {
    case generous     // Gold Season
    case business     // Stick Season
    case feverish     // Mud Season
    case serious      // Deep Winter

    var line: String {
        switch self {
        case .generous: return "Gold Season: the goblins are warm and a little generous."
        case .business: return "Stick Season: the goblins are strictly business."
        case .feverish: return "Mud Season: the goblins are unreliable and a little feverish."
        case .serious: return "Deep Winter: the goblins are serious and willing to deal at unusual rates."
        }
    }
}

struct FaeBargainTemplate: Equatable {
    let faeKind: FaeKind
    let openingGesture: String
    let terms: String
    let giftName: String
    let giftDescription: String
}

enum FaeEconomy {
    /// Minimum hours between unprompted bargain offers.
    static let offerGapHours = 20
    /// How long the reader has to pay before the gift goes cold.
    static let paymentWindowHours = 72
    /// Warmth gained for a genuine, accepted delivery.
    static let warmthPerDelivery = 3
    /// Warmth lost when a bargain lapses.
    static let warmthPerLapse = 4
    /// Attention earned per accepted delivery (scaled by report richness).
    static let baseAttention = 2

    static func mood(for date: Date, calendar: Calendar = .current) -> GoblinMood {
        switch AnchorRegistry.currentSeason(for: date, calendar: calendar) {
        case "Gold Season": return .generous
        case "Stick Season": return .business
        case "Mud Season": return .feverish
        default: return .serious
        }
    }

    /// The Goblin Market window opens around the new moon — the goblins issue
    /// their calling cards while the moon is a held breath.
    static func marketWindowIsOpen(on date: Date = Date()) -> Bool {
        let phase = MoonPhaseCalendar.phase(on: date).name
        return phase == "New Moon" || phase == "Waxing Crescent"
    }

    /// Attention awarded for a field report, rewarding specificity and length.
    static func attention(forReport report: String, mood: GoblinMood) -> Int {
        let words = report.split(whereSeparator: { $0 == " " || $0 == "\n" }).count
        let richness = min(4, words / 12)
        let moodBonus = mood == .generous ? 1 : (mood == .serious ? 1 : 0)
        return max(1, baseAttention + richness + moodBonus)
    }

    /// Can a fresh, unprompted bargain be offered right now?
    static func canOfferBargain(state: FaePlayerState, now: Date = Date()) -> Bool {
        // One open bargain at a time keeps the debt legible.
        guard state.openBargains.isEmpty else { return false }
        guard let last = state.lastBargainOfferedAt else { return true }
        return now.timeIntervalSince(last) >= Double(offerGapHours) * 3_600
    }

    /// Choose which fae offers, biased toward species the reader is warm with
    /// but never one whose market is currently closed (lapsed, unrepaired).
    static func chooseFae(state: FaePlayerState, slot: String) -> FaeKind {
        let open = FaeKind.allCases.filter { !state.marketIsClosed(for: $0) }
        let pool = open.isEmpty ? FaeKind.allCases : open
        let index = abs("\(slot)-fae-choice".stableHash) % pool.count
        return pool[index]
    }

    static func template(for kind: FaeKind, slot: String) -> FaeBargainTemplate {
        let options = templates.filter { $0.faeKind == kind }
        guard !options.isEmpty else {
            return FaeBargainTemplate(
                faeKind: kind,
                openingGesture: "The \(kind.name) left something on the page before you could refuse it.",
                terms: "Bring back one specific, unchosen detail you actually noticed.",
                giftName: "an unnamed gift",
                giftDescription: kind.giftEffect.effectLine
            )
        }
        let index = abs("\(slot)-\(kind.rawValue)-template".stableHash) % options.count
        return options[index]
    }

    static let templates: [FaeBargainTemplate] = [
        FaeBargainTemplate(
            faeKind: .bookSprite,
            openingGesture: "A Book Sprite has already whispered a single word from the last page of a book you haven't read. It hangs in the air, certain.",
            terms: "Find something you started and never finished. Don't finish it. Just notice it, and tell me where it is.",
            giftName: "the loose page",
            giftDescription: "A page torn from no book that reads a little differently every time you open it."
        ),
        FaeBargainTemplate(
            faeKind: .sentenceSalamander,
            openingGesture: "A Sentence Salamander curled against your hand and left a coal of borrowed warmth behind. The sentence down its spine is still glowing.",
            terms: "Bring me a moment from today that was more than it should have been. Not a thing — a moment, still warm.",
            giftName: "the borrowed coal",
            giftDescription: "A held warmth that can keep the grey of the Nothing back for a day."
        ),
        FaeBargainTemplate(
            faeKind: .punctuationPixie,
            openingGesture: "A Punctuation Pixie turned one of your periods into an ellipsis when you weren't looking— and grinned about it.",
            terms: "Find a place that feels like a comma — not ended, just paused. Tell me what made it pause.",
            giftName: "the wandering comma",
            giftDescription: "A mark that re-shelves a resting kind of page so it finds you again."
        ),
        FaeBargainTemplate(
            faeKind: .literaryElf,
            openingGesture: "A Literary Elf left a single, perfectly-formed silver quill on the page. It considers this a gift. It is.",
            terms: "Find me one true thing and describe it in exactly ten words. Not more, not less.",
            giftName: "the silver quill",
            giftDescription: "A quill that keeps one kept page from ever being forgotten."
        ),
        FaeBargainTemplate(
            faeKind: .deepLoreDwarf,
            openingGesture: "A Deep Lore Dwarf set down a small grey stone before you. It is older than the catalogue. It said nothing.",
            terms: "Find something that is holding something else up without being noticed. Bring me the fact of it.",
            giftName: "the foundation stone",
            giftDescription: "A weight that mines an overlooked kind of page back up to the shelf."
        ),
        FaeBargainTemplate(
            faeKind: .goblin,
            openingGesture: "A Marginalia Goblin slid a sealed card across the table before you sat down. The wax is already broken.",
            terms: "Notice something on your way today that has been there for years and you've never looked at. The detail, not the category.",
            giftName: "the broken-seal card",
            giftDescription: "A calling card that opens the Goblin Market when you spend it."
        )
    ]

    // MARK: Lifecycle (pure mutations on FaePlayerState)

    /// Front a new bargain: the fae gives a working gift first, the reader owes
    /// a field report by the deadline. Returns the created bargain.
    @discardableResult
    static func offerBargain(
        into state: inout FaePlayerState,
        kind: FaeKind,
        slot: String,
        now: Date = Date()
    ) -> FaeBargain {
        let template = template(for: kind, slot: slot)
        let giftID = "fae-gift-\(kind.rawValue)-\(slot)"
        let bargainID = "fae-bargain-\(kind.rawValue)-\(slot)"
        let gift = FaeGift(
            id: giftID,
            faeKind: kind,
            name: template.giftName,
            descriptionText: template.giftDescription,
            effect: kind.giftEffect,
            isCold: false,
            acquiredAt: now,
            chargesRemaining: kind.giftEffect == .callingCard ? 1 : nil,
            boundSourceID: nil
        )
        let bargain = FaeBargain(
            id: bargainID,
            faeKind: kind,
            slot: slot,
            giftID: giftID,
            giftName: template.giftName,
            giftEffectLine: kind.giftEffect.effectLine,
            openingGesture: template.openingGesture,
            terms: template.terms,
            offeredAt: now,
            deadline: now.addingTimeInterval(Double(paymentWindowHours) * 3_600),
            status: .owed,
            fieldReport: nil,
            faeResponse: nil,
            rewardText: nil,
            deliveredAt: nil
        )
        if !state.gifts.contains(where: { $0.id == giftID }) {
            state.gifts.append(gift)
        }
        if !state.bargains.contains(where: { $0.id == bargainID }) {
            state.bargains.append(bargain)
        }
        state.lastBargainOfferedAt = now
        return bargain
    }

    /// Mark any owed bargain past its deadline as lapsed: its fronted gift goes
    /// cold and that species' market closes until the debt is repaired. Faerie
    /// law made visible — never punishment. Returns the ids that just lapsed.
    @discardableResult
    static func sweepLapses(into state: inout FaePlayerState, now: Date = Date()) -> [String] {
        var lapsed: [String] = []
        for index in state.bargains.indices where state.bargains[index].status == .owed {
            guard now > state.bargains[index].deadline else { continue }
            state.bargains[index].status = .lapsed
            let giftID = state.bargains[index].giftID
            if let giftIndex = state.gifts.firstIndex(where: { $0.id == giftID }) {
                state.gifts[giftIndex].isCold = true
            }
            let kind = state.bargains[index].faeKind.rawValue
            state.warmth[kind] = (state.warmth[kind] ?? 0) - warmthPerLapse
            lapsed.append(state.bargains[index].id)
        }
        return lapsed
    }

    /// Pay a bargain with a genuine field report. Awards warmth and attention,
    /// stores the fae's response and reward, and closes the deal.
    static func deliver(
        bargainID: String,
        report: String,
        faeResponse: String,
        reward: String,
        into state: inout FaePlayerState,
        now: Date = Date()
    ) {
        guard let index = state.bargains.firstIndex(where: { $0.id == bargainID }) else { return }
        let wasLapsed = state.bargains[index].status == .lapsed
        state.bargains[index].status = .delivered
        state.bargains[index].fieldReport = report
        state.bargains[index].faeResponse = faeResponse
        state.bargains[index].rewardText = reward
        state.bargains[index].deliveredAt = now

        // A repaired debt thaws its cold gift; a fresh delivery keeps it warm.
        let giftID = state.bargains[index].giftID
        if let giftIndex = state.gifts.firstIndex(where: { $0.id == giftID }) {
            state.gifts[giftIndex].isCold = false
        }

        let kind = state.bargains[index].faeKind
        let mood = mood(for: now)
        // Repair restores half the warmth a lapse cost; a clean delivery pays full.
        let warmthGain = wasLapsed ? max(1, warmthPerLapse / 2) : warmthPerDelivery
        state.warmth[kind.rawValue] = (state.warmth[kind.rawValue] ?? 0) + warmthGain
        state.attention += attention(forReport: report, mood: mood)
    }

    /// Spend a consumable gift (e.g., a calling card). Returns true if spent.
    @discardableResult
    static func spendCharge(giftID: String, into state: inout FaePlayerState) -> Bool {
        guard let index = state.gifts.firstIndex(where: { $0.id == giftID }),
              state.gifts[index].isActive,
              let charges = state.gifts[index].chargesRemaining,
              charges > 0 else { return false }
        state.gifts[index].chargesRemaining = charges - 1
        return true
    }
}

// MARK: - Fae gift effects (pure, automatic, never a model call)

enum FaeGiftEffects {
    /// Sources a warm Reshelving gift lifts back to the front of the shelf.
    static let reshelfEligible: Set<BookPageType> = [
        .diary, .souvenir, .mood, .weather, .gossip, .askTheBook,
        .wonderCompass, .letter, .body, .fuel, .rest
    ]

    /// If the reader holds a warm Reshelving gift, choose the source to lift:
    /// an explicitly bound one, else the longest-rested eligible source.
    static func reshelvedSourceIDs(
        state: FaePlayerState,
        surfaceHistory: [String: SurfaceHistoryRecord],
        now: Date = Date()
    ) -> Set<String> {
        let reshelvers = state.activeGifts.filter { $0.effect == .reshelving }
        guard !reshelvers.isEmpty else { return [] }
        if let bound = reshelvers.compactMap(\.boundSourceID).first(where: { !$0.isEmpty }) {
            return [bound]
        }
        let eligible = BookPageSourceRegistry.sources.filter {
            $0.isActive && reshelfEligible.contains($0.type)
        }
        let chosen = eligible.min { left, right in
            lastShown(left, surfaceHistory) < lastShown(right, surfaceHistory)
        }
        return chosen.map { [$0.id] } ?? []
    }

    private static func lastShown(_ source: BookPageSource, _ history: [String: SurfaceHistoryRecord]) -> Date {
        history["source:\(source.id)"]?.lastShownAt ?? .distantPast
    }

    /// Kept-page IDs a warm Long Memory gift pins to reliably resurface.
    static func pinnedPageIDs(state: FaePlayerState) -> Set<String> {
        Set(state.activeGifts.filter { $0.effect == .longMemory }.compactMap(\.boundSourceID).filter { !$0.isEmpty })
    }
}

/// A Loose Page reads a little differently every time it is opened. Pure static
/// rotation — no model call — so it can be read freely without a Gemma turn.
enum LoosePageReader {
    static let fragments: [String] = [
        "The page is mostly margin. In the center, in a hand you almost recognize: \"You will mistake the exit for a wall three times before you trust it.\" The ink is still drying, though no one has been here.",
        "A pressed flower you have never seen, with a name written beneath it that means the smell of a room just after someone has left it. The petals turn toward you when you read.",
        "A list, half-erased: things to do before the snow. Only the last item survives — \"forgive the kettle\" — and you find you understand it completely.",
        "A map of a coastline that does not exist, with one harbor circled and the note: \"You have been here. You called it something else.\"",
        "Three sentences in a language of only vowels. You cannot read them, but reading them makes your shoulders drop an inch, the way a held breath finally goes.",
        "A receipt for one (1) afternoon, paid in full, no refunds. The cashier's signature is a small drawing of a sleeping cat.",
        "Someone began to describe the color of a particular hour and gave up halfway, leaving: \"it was the color of—\" The blank is the most honest part.",
        "A door, drawn in pencil, slightly ajar. If you tilt the page, light seems to come through the gap, though it is only paper."
    ]

    static func text(for gift: FaeGift, now: Date = Date()) -> String {
        guard !fragments.isEmpty else { return "" }
        // A coarse time slot makes the page shift between readings.
        let slot = Int(now.timeIntervalSince1970 / 1_800)
        let index = abs("\(gift.id)-\(slot)".stableHash) % fragments.count
        return fragments[index]
    }
}

// MARK: - The Goblin Market

struct FaeMarketOffer: Identifiable, Equatable {
    let id: String
    let faeKind: FaeKind
    let name: String
    let descriptionText: String
    let effect: FaeGiftEffect
    let baseCost: Int
}

enum FaeMarketCatalog {
    static let offers: [FaeMarketOffer] = [
        FaeMarketOffer(
            id: "market-quieting-coal",
            faeKind: .sentenceSalamander,
            name: "a second borrowed coal",
            descriptionText: "Holds the grey of the Nothing back by one shade for a day.",
            effect: .quieting,
            baseCost: 6
        ),
        FaeMarketOffer(
            id: "market-wandering-comma",
            faeKind: .punctuationPixie,
            name: "a wandering comma",
            descriptionText: "Re-shelves a resting kind of page so it finds you again.",
            effect: .reshelving,
            baseCost: 5
        ),
        FaeMarketOffer(
            id: "market-silver-quill",
            faeKind: .literaryElf,
            name: "a silver quill",
            descriptionText: "Keeps one kept page from ever being forgotten.",
            effect: .longMemory,
            baseCost: 7
        ),
        FaeMarketOffer(
            id: "market-loose-page",
            faeKind: .bookSprite,
            name: "a loose page",
            descriptionText: "A page that never reads the same way twice.",
            effect: .loosePage,
            baseCost: 4
        ),
        FaeMarketOffer(
            id: "market-broken-seal-card",
            faeKind: .goblin,
            name: "a broken-seal calling card",
            descriptionText: "Opens the Goblin Market again when you spend it.",
            effect: .callingCard,
            baseCost: 8
        )
    ]

    /// Goblin mood moves the price: generous shaves a little, serious deals at
    /// unusual (cheaper, rarer) rates, feverish marks things up.
    static func cost(of offer: FaeMarketOffer, mood: GoblinMood) -> Int {
        switch mood {
        case .generous: return max(1, offer.baseCost - 1)
        case .serious: return max(1, offer.baseCost - 2)
        case .feverish: return offer.baseCost + 2
        case .business: return offer.baseCost
        }
    }
}

extension FaeEconomy {
    /// True when the reader can shop: the new-moon window is open, or they hold
    /// a calling card to spend.
    static func canEnterMarket(state: FaePlayerState, now: Date = Date()) -> Bool {
        if marketWindowIsOpen(on: now) { return true }
        return state.activeGifts.contains { $0.effect == .callingCard }
    }

    /// Buy a market offer with Attention. Returns the acquired gift, or nil if
    /// the reader cannot afford it.
    @discardableResult
    static func purchase(
        offerID: String,
        into state: inout FaePlayerState,
        now: Date = Date()
    ) -> FaeGift? {
        guard let offer = FaeMarketCatalog.offers.first(where: { $0.id == offerID }) else { return nil }
        let price = FaeMarketCatalog.cost(of: offer, mood: mood(for: now))
        guard state.attention >= price else { return nil }
        // Spend a calling card first if the moon window is shut.
        if !marketWindowIsOpen(on: now),
           let card = state.gifts.firstIndex(where: { $0.effect == .callingCard && $0.isActive }) {
            if let charges = state.gifts[card].chargesRemaining {
                state.gifts[card].chargesRemaining = max(0, charges - 1)
            }
        }
        state.attention -= price
        let gift = FaeGift(
            id: "market-gift-\(offerID)-\(Int(now.timeIntervalSince1970))",
            faeKind: offer.faeKind,
            name: offer.name,
            descriptionText: offer.descriptionText,
            effect: offer.effect,
            isCold: false,
            acquiredAt: now,
            chargesRemaining: offer.effect == .callingCard ? 1 : nil,
            boundSourceID: nil
        )
        state.gifts.append(gift)
        return gift
    }
}

// MARK: - Goblin Marginalia
//
// Goblins are born from marginalia — the response to the story, not the story.
// Occasionally one annotates a page the reader has already kept. Pure static
// rotation; never a model call, so it can appear ambiently without a Gemma turn.

enum GoblinMarginalia {
    static let openers: [String] = [
        "A goblin has annotated this, in a small cramped hand:",
        "Noted in the margin, in ink that wasn't yours:",
        "Someone from the Appendix Provinces left a remark here:",
        "Marginalia, dog-eared at the corner:"
    ]

    static let remarks: [String] = [
        "\"The detail here is real. Filed under things-worth-keeping.\"",
        "\"You noticed this without being asked. We see that.\"",
        "\"This one is load-bearing. Do not let it go grey.\"",
        "\"Worth more than you traded for it. The Empire does not say that often.\"",
        "\"An honest noticing. Rare coin.\"",
        "\"We were here before this page. We will be here after. Good that you wrote it down.\"",
        "\"The category is dull; the particular is not. You chose the particular. Noted.\"",
        "\"Annotated and shelved by mood, not by number.\""
    ]

    /// An occasional goblin note for a kept page, deterministic by its id so it
    /// is stable across openings. Returns nil for most pages — it should feel rare.
    static func note(forID id: String, text: String) -> String? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 24, !openers.isEmpty, !remarks.isEmpty else { return nil }
        let hash = abs(id.stableHash)
        guard hash % 3 == 0 else { return nil }
        return "\(openers[hash % openers.count]) \(remarks[(hash / 7) % remarks.count])"
    }
}

// MARK: - The Pact War
//
// Each Talisman has a philosophy it wants to spread. The war is them contesting
// territory — measured in Control Belief, per talisman, per territory — across
// two fronts: the Book's own shelves (kinds of pages) and the real-world
// integrations the app touches. Pure local simulation; never a model call. It
// goes quiet under distress, like the Nothing. See lore/chapter-pacts.md.

enum PactFront: String, Codable, Equatable {
    case shelf
    case integration
}

struct PactTerritory: Identifiable, Equatable {
    let id: String
    let front: PactFront
    let name: String
    let blurb: String
    let pageTypes: [BookPageType]   // shelf front: which page kinds it governs
}

enum PactTerritoryRegistry {
    static let shelves: [PactTerritory] = [
        PactTerritory(id: "shelf-reflection", front: .shelf, name: "The Reflection Shelf",
                      blurb: "Diary, Inner Weather, Souvenirs, About You — where you write yourself down.",
                      pageTypes: [.diary, .mood, .souvenir, .aboutYou]),
        PactTerritory(id: "shelf-care", front: .shelf, name: "The Care Shelf",
                      blurb: "Body, Fuel, Center, Weather — where the Book tends the animal of you.",
                      pageTypes: [.body, .fuel, .rest, .weather]),
        PactTerritory(id: "shelf-story", front: .shelf, name: "The Story Shelf",
                      blurb: "Story Pages, Gossip, The Bleed, the Book's own noticing.",
                      pageTypes: [.narrativeOS, .gossip, .theBleed, .marginsAtlas, .bookConnections, .bookRemembered, .bookNotices]),
        PactTerritory(id: "shelf-connection", front: .shelf, name: "The Connection Shelf",
                      blurb: "Letters, Cast, the Support Guild, Office Hours, Fae Bargains — pages with another hand in them.",
                      pageTypes: [.letter, .castMember, .supportGuild, .inkrestOfficeHours, .faeBargain]),
        PactTerritory(id: "shelf-field", front: .shelf, name: "The Field Shelf",
                      blurb: "Wonder Compass, Outer Stacks, Illuminated Photos, Hour Pages — the world out the door.",
                      pageTypes: [.wonderCompass, .anchor, .illuminatedPhoto, .location, .calendar])
    ]

    static let integrations: [PactTerritory] = [
        PactTerritory(id: "integ-calendar", front: .integration, name: "The Calendar Door",
                      blurb: "The hinges of your real day — events the Book folds corners around.", pageTypes: []),
        PactTerritory(id: "integ-notifications", front: .integration, name: "The Whisper Channel",
                      blurb: "The Book's voice that reaches you when the app is closed.", pageTypes: []),
        PactTerritory(id: "integ-health", front: .integration, name: "The Body Margin",
                      blurb: "Sleep, steps, heartbeat — the signals the Book reads with care.", pageTypes: []),
        PactTerritory(id: "integ-photos", front: .integration, name: "The Illuminated Plate",
                      blurb: "Real photographs the Book turns to illuminated pages.", pageTypes: []),
        PactTerritory(id: "integ-weather", front: .integration, name: "The Window Sky",
                      blurb: "The real weather the Book enchants into the day.", pageTypes: [])
    ]

    static let all: [PactTerritory] = shelves + integrations

    static func territory(id: String) -> PactTerritory? {
        all.first { $0.id == id }
    }

    /// The shelf territory that governs a given page kind, if any.
    static func shelf(governing type: BookPageType) -> PactTerritory? {
        shelves.first { $0.pageTypes.contains(type) }
    }
}

enum PactTier: Int, Comparable, Equatable {
    case none = 0
    case contesting
    case influenced
    case controlled
    case dominated
    case sovereign

    static func < (lhs: PactTier, rhs: PactTier) -> Bool { lhs.rawValue < rhs.rawValue }

    static func tier(forControl control: Int) -> PactTier {
        switch control {
        case ..<1: return .none
        case ..<10: return .contesting
        case ..<25: return .influenced
        case ..<45: return .controlled
        case ..<70: return .dominated
        default: return .sovereign
        }
    }

    var label: String {
        switch self {
        case .none: return "Uncontested"
        case .contesting: return "Contesting"
        case .influenced: return "Influenced"
        case .controlled: return "Controlled"
        case .dominated: return "Dominated"
        case .sovereign: return "Sovereign"
        }
    }
}

struct PactActionRecord: Codable, Equatable, Identifiable {
    enum Kind: String, Codable, Equatable {
        case push, challenge, raid, consolidate
    }
    var id: String
    var talismanID: String
    var territoryID: String
    var kind: Kind
    var at: Date
    var line: String
}

/// A dramatic beat the war produced: a territory changed hands, or a Talisman
/// reached Sovereign. Surfaced as a keepable Pact Dispatch page.
struct PactDispatch: Codable, Equatable, Identifiable {
    enum Kind: String, Codable, Equatable {
        case seized       // a new Talisman took control
        case sovereign    // a Talisman crossed into Sovereign
    }
    var id: String
    var territoryID: String
    var talismanID: String
    var kind: Kind
    var line: String
    var at: Date
}

/// The war's save state. Optional on the vault for migration.
struct PactWarState: Codable, Equatable {
    var control: [String: Int] = [:]   // "talismanID|territoryID" -> control belief
    var lastTickAt: Date?
    var log: [PactActionRecord] = []
    var pendingDispatches: [PactDispatch] = []

    init() {}

    static func key(_ talismanID: String, _ territoryID: String) -> String { "\(talismanID)|\(territoryID)" }

    func control(_ talismanID: String, _ territoryID: String) -> Int {
        control[Self.key(talismanID, territoryID)] ?? 0
    }

    /// The talisman holding a territory: the clear leader, or nil on a tie/empty.
    func controller(of territoryID: String) -> String? {
        let scores = AcademyChapterRegistry.chapters.map { ($0.talismanID, control($0.talismanID, territoryID)) }
        let top = scores.max { $0.1 < $1.1 }
        guard let top, top.1 > 0 else { return nil }
        let tied = scores.filter { $0.1 == top.1 }.count > 1
        return tied ? nil : top.0
    }

    func tier(of territoryID: String) -> PactTier {
        guard let controller = controller(of: territoryID) else { return .none }
        return PactTier.tier(forControl: control(controller, territoryID))
    }
}

enum PactWarEngine {
    static let baseBelief = 30
    static let homeFieldBonus = 15
    static let tickGapHours = 20

    /// Natural alignment: which territories each Talisman pushes into easily.
    static let alignment: [String: Set<String>] = [
        "ember-seal": ["shelf-reflection", "shelf-story", "integ-notifications"],
        "moss-clasp": ["shelf-care", "shelf-field", "integ-health", "integ-weather"],
        "tide-glass": ["shelf-field", "shelf-story", "integ-photos"],
        "wind-cipher": ["shelf-connection", "integ-calendar", "integ-notifications"],
        "dusk-thorn": ["shelf-story", "shelf-connection", "integ-weather"]
    ]

    static func isAligned(_ talismanID: String, _ territoryID: String) -> Bool {
        alignment[talismanID]?.contains(territoryID) ?? false
    }

    /// A Talisman's overall Belief governs how aggressively it fights. Bound
    /// readers give their Chapter's Talisman a home-field bonus.
    static func overallBelief(
        talismanID: String,
        entityBeliefOffsets: [String: Int],
        boundTalismanID: String?
    ) -> Int {
        var value = baseBelief + (entityBeliefOffsets[talismanID] ?? 0)
        if talismanID == boundTalismanID { value += homeFieldBonus }
        return max(0, min(100, value))
    }

    static func canTick(state: PactWarState, now: Date = Date()) -> Bool {
        guard let last = state.lastTickAt else { return true }
        return now.timeIntervalSince(last) >= Double(tickGapHours) * 3_600
    }

    /// Advance the war by one stir per Talisman. Deterministic given the slot.
    /// Pure local logic; never a model call; silent under distress.
    @discardableResult
    static func tick(
        into state: inout PactWarState,
        entityBeliefOffsets: [String: Int],
        boundTalismanID: String?,
        now: Date = Date(),
        distressActive: Bool = false
    ) -> [PactActionRecord] {
        guard !distressActive, canTick(state: state, now: now) else { return [] }
        let slot = BookDay.id(for: now)
        let before = state   // value-type snapshot for crossing detection
        var records: [PactActionRecord] = []

        // Aggressive Talismans act first (more Belief = more initiative).
        let order = AcademyChapterRegistry.chapters
            .map { ($0.talismanID, overallBelief(talismanID: $0.talismanID, entityBeliefOffsets: entityBeliefOffsets, boundTalismanID: boundTalismanID)) }
            .sorted { $0.1 > $1.1 }

        for (talismanID, overall) in order {
            if let record = act(
                talismanID: talismanID,
                overall: overall,
                into: &state,
                entityBeliefOffsets: entityBeliefOffsets,
                boundTalismanID: boundTalismanID,
                slot: slot,
                now: now
            ) {
                records.append(record)
            }
        }

        // Detect dramatic crossings against the snapshot and queue dispatches.
        for territory in PactTerritoryRegistry.all {
            let beforeController = before.controller(of: territory.id)
            let afterController = state.controller(of: territory.id)
            let name = AcademyChapterRegistry.chapter(forTalismanID: afterController ?? "")?.talismanName ?? "A Talisman"
            if let after = afterController, after != beforeController {
                queueDispatch(.seized, territory: territory, talismanID: after,
                              line: "\(name) has taken \(territory.name).", into: &state, now: now)
            }
            if state.tier(of: territory.id) == .sovereign,
               before.tier(of: territory.id) != .sovereign,
               let after = afterController {
                queueDispatch(.sovereign, territory: territory, talismanID: after,
                              line: "\(name) now reigns Sovereign over \(territory.name).", into: &state, now: now)
            }
        }
        // Keep the dispatch queue small and fresh.
        state.pendingDispatches = state.pendingDispatches
            .filter { now.timeIntervalSince($0.at) < 4 * 86_400 }
            .suffix(6)
            .map { $0 }

        state.lastTickAt = now
        state.log = (records + state.log).prefix(24).map { $0 }
        return records
    }

    private static func queueDispatch(
        _ kind: PactDispatch.Kind,
        territory: PactTerritory,
        talismanID: String,
        line: String,
        into state: inout PactWarState,
        now: Date
    ) {
        let id = "pact-dispatch-\(territory.id)-\(talismanID)-\(kind.rawValue)-\(BookDay.id(for: now))"
        guard !state.pendingDispatches.contains(where: { $0.id == id }) else { return }
        state.pendingDispatches.append(
            PactDispatch(id: id, territoryID: territory.id, talismanID: talismanID, kind: kind, line: line, at: now)
        )
    }

    private static func act(
        talismanID: String,
        overall: Int,
        into state: inout PactWarState,
        entityBeliefOffsets: [String: Int],
        boundTalismanID: String?,
        slot: String,
        now: Date
    ) -> PactActionRecord? {
        let name = AcademyChapterRegistry.chapter(forTalismanID: talismanID)?.talismanName ?? talismanID
        let seed = abs("\(slot)-\(talismanID)-pact".stableHash)
        let aligned = PactTerritoryRegistry.all.filter { isAligned(talismanID, $0.id) }
        let pushPotential = max(1, overall / 25)   // 1...4 per push

        // RAID: overall >= 50 and a rival sits Dominated+ on a territory this
        // Talisman can out-belief.
        if overall >= 50 {
            let raidable = PactTerritoryRegistry.all.compactMap { territory -> (String, Int)? in
                guard let rival = state.controller(of: territory.id), rival != talismanID else { return nil }
                guard state.control(rival, territory.id) >= 45 else { return nil }
                let rivalOverall = overallBelief(talismanID: rival, entityBeliefOffsets: entityBeliefOffsets, boundTalismanID: boundTalismanID)
                guard overall >= rivalOverall else { return nil }
                return (territory.id, rivalOverall)
            }
            if !raidable.isEmpty {
                let target = raidable[seed % raidable.count]
                bump(&state, talismanID, target.0, by: pushPotential)
                if let rival = state.controller(of: target.0), rival != talismanID {
                    bump(&state, rival, target.0, by: -2)
                }
                return record(talismanID, target.0, .raid, now,
                              "\(name) raids \(PactTerritoryRegistry.territory(id: target.0)?.name ?? target.0).")
            }
        }

        // CHALLENGE: overall >= 30 and a rival leads by a thin margin here.
        if overall >= 30 {
            let contestable = PactTerritoryRegistry.all.compactMap { territory -> String? in
                guard let rival = state.controller(of: territory.id), rival != talismanID else { return nil }
                let gap = state.control(rival, territory.id) - state.control(talismanID, territory.id)
                return (gap > 0 && gap <= 8) ? territory.id : nil
            }
            if !contestable.isEmpty {
                let target = contestable[seed % contestable.count]
                bump(&state, talismanID, target, by: max(1, pushPotential - 1))
                if let rival = state.controller(of: target), rival != talismanID {
                    bump(&state, rival, target, by: -1)
                }
                return record(talismanID, target, .challenge, now,
                              "\(name) challenges for \(PactTerritoryRegistry.territory(id: target)?.name ?? target).")
            }
        }

        // CONSOLIDATE: hold a territory it already leads but hasn't yet made Sovereign.
        let held = PactTerritoryRegistry.all.filter {
            state.controller(of: $0.id) == talismanID && state.control(talismanID, $0.id) < 70
        }
        if !held.isEmpty, seed % 3 == 0 {
            let target = held[seed % held.count]
            bump(&state, talismanID, target.id, by: max(1, pushPotential - 1))
            return record(talismanID, target.id, .consolidate, now,
                          "\(name) consolidates its hold on \(target.name).")
        }

        // PUSH (always available): deepen an aligned territory not yet Sovereign.
        let pushable = (aligned.isEmpty ? PactTerritoryRegistry.all : aligned)
            .filter { state.control(talismanID, $0.id) < 70 }
        guard !pushable.isEmpty else { return nil }
        let target = pushable[seed % pushable.count]
        let amount = isAligned(talismanID, target.id) ? pushPotential : max(1, pushPotential - 1)
        bump(&state, talismanID, target.id, by: amount)
        return record(talismanID, target.id, .push, now,
                      "\(name) pushes into \(target.name).")
    }

    private static func bump(_ state: inout PactWarState, _ talismanID: String, _ territoryID: String, by amount: Int) {
        let key = PactWarState.key(talismanID, territoryID)
        state.control[key] = max(0, min(100, (state.control[key] ?? 0) + amount))
    }

    private static func record(_ talismanID: String, _ territoryID: String, _ kind: PactActionRecord.Kind, _ now: Date, _ line: String) -> PactActionRecord {
        PactActionRecord(
            id: "\(territoryID)-\(talismanID)-\(Int(now.timeIntervalSince1970))-\(kind.rawValue)",
            talismanID: talismanID, territoryID: territoryID, kind: kind, at: now, line: line
        )
    }
}

/// Live effect of the war on the Book's shelves: a Talisman that has reached
/// Controlled+ on a shelf gives that shelf's page kinds a surfacing nudge — its
/// philosophy "shapes timing." Pure curator math; quiet under distress.
enum PactWarEffects {
    static func shelfBoost(for type: BookPageType, state: PactWarState) -> Int {
        guard let shelf = PactTerritoryRegistry.shelf(governing: type),
              state.controller(of: shelf.id) != nil else { return 0 }
        switch state.tier(of: shelf.id) {
        case .controlled: return 4
        case .dominated: return 8
        case .sovereign: return 12
        default: return 0
        }
    }

    /// The Chapter writing-framing a controlled shelf currently speaks in, if any.
    static func framing(for type: BookPageType, state: PactWarState) -> String? {
        guard let shelf = PactTerritoryRegistry.shelf(governing: type),
              state.tier(of: shelf.id) >= .controlled,
              let controller = state.controller(of: shelf.id),
              let chapter = AcademyChapterRegistry.chapter(forTalismanID: controller) else { return nil }
        return chapter.writeFraming
    }

    /// Page kinds whose real-world door a Talisman speaks through.
    static let doorTerritory: [BookPageType: String] = [
        .body: "integ-health",
        .weather: "integ-weather",
        .illuminatedPhoto: "integ-photos"
    ]

    /// The epigraph the door's controller speaks over a Body/Weather/Photo page.
    static func doorEpigraph(for type: BookPageType, state: PactWarState) -> (line: String, talisman: String)? {
        guard let territoryID = doorTerritory[type],
              state.tier(of: territoryID) >= .controlled,
              let controller = state.controller(of: territoryID),
              let line = PactVoices.doorEpigraph(territoryID: territoryID, controller: controller),
              let chapter = AcademyChapterRegistry.chapter(forTalismanID: controller) else { return nil }
        return (line, chapter.talismanName)
    }

    /// Page kinds whose shelf a Talisman holds at Sovereign — these get a
    /// guaranteed slot in the surfaced set (the Talisman acts unasked).
    static func sovereignShelfPageTypes(state: PactWarState) -> Set<BookPageType> {
        var types = Set<BookPageType>()
        for shelf in PactTerritoryRegistry.shelves where state.tier(of: shelf.id) == .sovereign {
            types.formUnion(shelf.pageTypes)
        }
        return types
    }
}

// MARK: - Pact War voices (static per-Talisman flavor; never a model call)
//
// When a Talisman holds one of the real-world doors, it colors how the Book
// speaks through that channel. Pure static catalogs so the war can change the
// app's voice without a Gemma turn.

struct PactWhisper: Equatable {
    let title: String
    let body: String
}

enum PactVoices {
    /// The evening braid whisper, recolored by whoever holds the Whisper Channel.
    static func braidWhisper(controller talismanID: String?) -> PactWhisper {
        switch talismanID {
        case "ember-seal":
            return PactWhisper(title: "Write before you sleep",
                               body: "Today's kept pages are first drafts. The Ember Seal says: finish one sentence only you could write.")
        case "moss-clasp":
            return PactWhisper(title: "Let the day settle",
                               body: "The Moss Clasp keeps the lamp low. Re-read one kept page slowly before you braid.")
        case "tide-glass":
            return PactWhisper(title: "Catch it before it goes",
                               body: "The Tide Glass says the day is already leaving. Braid the one moment that's still warm.")
        case "wind-cipher":
            return PactWhisper(title: "Who was in today with you?",
                               body: "The Wind Cipher pulls a thread: braid the page where someone else's hand showed up.")
        case "dusk-thorn":
            return PactWhisper(title: "Name the hard part",
                               body: "The Dusk Thorn won't smooth it over: braid the page you'd rather skip.")
        default:
            return PactWhisper(title: "The Book is ready to braid",
                               body: "Today's kept pages can become tonight's Book of You entry.")
        }
    }

    /// A short epigraph for a real-world door (Health/Weather/Photos), in the
    /// voice of whoever holds it.
    static func doorEpigraph(territoryID: String, controller talismanID: String?) -> String? {
        guard let talismanID else { return nil }
        switch (territoryID, talismanID) {
        case ("integ-health", "ember-seal"): return "Your body is a first draft you get to revise. — the Ember Seal"
        case ("integ-health", "moss-clasp"): return "Listen to it before you instruct it. — the Moss Clasp"
        case ("integ-health", "tide-glass"): return "The body lives in this hour, not the plan. — the Tide Glass"
        case ("integ-health", "wind-cipher"): return "No one tends a body alone. — the Wind Cipher"
        case ("integ-health", "dusk-thorn"): return "Name the ache honestly; it is data, not defeat. — the Dusk Thorn"
        case ("integ-weather", "ember-seal"): return "The sky is yours to read as you choose. — the Ember Seal"
        case ("integ-weather", "moss-clasp"): return "The weather is speaking; be quiet enough to hear it. — the Moss Clasp"
        case ("integ-weather", "tide-glass"): return "This exact sky will never come again. — the Tide Glass"
        case ("integ-weather", "wind-cipher"): return "Everyone under this sky is in your story. — the Wind Cipher"
        case ("integ-weather", "dusk-thorn"): return "Storms are honest. Let this one be. — the Dusk Thorn"
        case ("integ-photos", "ember-seal"): return "You framed this. That choice is the art. — the Ember Seal"
        case ("integ-photos", "moss-clasp"): return "The picture noticed something through you. — the Moss Clasp"
        case ("integ-photos", "tide-glass"): return "A caught second, already gone. Keep it. — the Tide Glass"
        case ("integ-photos", "wind-cipher"): return "Who else is held in this frame? — the Wind Cipher"
        case ("integ-photos", "dusk-thorn"): return "Look at what you almost cropped out. — the Dusk Thorn"
        default: return nil
        }
    }

    /// An extra, unprompted whisper a Talisman sends when it reigns Sovereign
    /// over the Whisper Channel — it acts through the app without being asked.
    static func sovereignWhisper(controller talismanID: String?) -> PactWhisper? {
        switch talismanID {
        case "ember-seal":
            return PactWhisper(title: "Publish something today",
                               body: "The Ember Seal reigns over your whispers now. Make one thing only you would make.")
        case "moss-clasp":
            return PactWhisper(title: "Read before you write",
                               body: "The Moss Clasp holds the channel. Let one thing in before you put anything out.")
        case "tide-glass":
            return PactWhisper(title: "Now, or not at all",
                               body: "The Tide Glass owns the hour. The thing you keep meaning to do — do it in the next ten minutes.")
        case "wind-cipher":
            return PactWhisper(title: "Reach one person",
                               body: "The Wind Cipher rules the channel. Send the message you've been drafting in your head.")
        case "dusk-thorn":
            return PactWhisper(title: "The thing you're avoiding",
                               body: "The Dusk Thorn holds your whispers. You know the one. Look at it for a minute.")
        default:
            return nil
        }
    }

    /// Hour Page framing, recolored by whoever holds the Calendar Door.
    static func hourQuestion(controller talismanID: String?, phase: String) -> String? {
        let after = phase == "after"
        switch talismanID {
        case "ember-seal":
            return after ? "What did you author in that hour?" : "What will you make of this hour — your way?"
        case "moss-clasp":
            return after ? "What did that hour quietly show you?" : "What is this hour asking you to receive?"
        case "tide-glass":
            return after ? "What was the one alive moment in it?" : "What's the first true thing this hour offers?"
        case "wind-cipher":
            return after ? "Who shared that hour, and what did you notice together?" : "Who is this hour with — and what could you ask them?"
        case "dusk-thorn":
            return after ? "What honest thing did that hour surface?" : "What are you bracing for in this hour, really?"
        default:
            return nil
        }
    }
}

extension PactWarEffects {
    /// Annotate a surfaced capture page with the framing of the Talisman that
    /// holds its shelf, so the sheet can speak in that Chapter's hand.
    static func framed(_ page: SurfacePage, state: PactWarState) -> SurfacePage {
        var payload = page.payload
        var changed = false

        // Shelf framing: a controlled shelf rewrites its capture pages' prompt.
        if page.intent == .capture,
           let framing = framing(for: page.type, state: state),
           let shelf = PactTerritoryRegistry.shelf(governing: page.type),
           let controller = state.controller(of: shelf.id),
           let chapter = AcademyChapterRegistry.chapter(forTalismanID: controller) {
            payload.metadata["pactFraming"] = framing
            payload.metadata["pactController"] = chapter.name
            payload.metadata["pactTalisman"] = chapter.talismanName
            changed = true
        }

        // Door epigraph: a controlled real-world door speaks over its pages.
        if let epigraph = doorEpigraph(for: page.type, state: state) {
            payload.metadata["pactDoorEpigraph"] = epigraph.line
            payload.metadata["pactDoorTalisman"] = epigraph.talisman
            changed = true
        }

        guard changed else { return page }
        return SurfacePage(
            id: page.id,
            type: page.type,
            sourceID: page.sourceID,
            intent: page.intent,
            renderStyle: page.renderStyle,
            score: page.score,
            reason: page.reason,
            prompt: page.prompt,
            detail: page.detail,
            payload: payload
        )
    }
}

// MARK: - The Almanac (the living Wheel of the Year + lunar esbats)
//
// The Academy breathes with the real world. The Almanac knows, for a date and
// hemisphere, which celebrations are alive: the eight pagan Sabbats, the Full
// and New Moon esbats, and the year's meteor showers. Pure local astronomy and
// date logic — never a model call. Celebrations bend Belief, the Nothing, the
// Fae, and the Pact War, and the world works on the reader whether noticed or
// not. See lore/seasonal-calendar.md.

enum Hemisphere: String, Codable, Equatable {
    case northern, southern
    static func from(latitude: Double?) -> Hemisphere {
        (latitude ?? 45) < 0 ? .southern : .northern
    }
}

enum CelebrationKind: String, Codable, Equatable {
    case sabbat, esbat, shower, eclipse
}

struct Celebration: Identifiable, Equatable {
    let id: String
    let kind: CelebrationKind
    let commonName: String       // "Full Moon", "Samhain"
    let academyTitle: String     // "The Luminous Gathering"
    let blurb: String            // prose flavor for the page body
    let invitationTitle: String  // the special-event prompt heading
    let invitation: String       // what to notice / do
    let beliefBonus: Int
    let greyShift: Int           // effect on the Nothing (- light, + thinning veil)
    let symbolName: String
    let accent: String           // palette hint: amber/green/gold/violet/candle/slate
    let priority: Int            // higher wins when several are active
}

private struct SabbatDef {
    let id: String
    let commonName: String
    let academyTitle: String
    let blurb: String
    let invitationTitle: String
    let invitation: String
    let beliefBonus: Int
    let greyShift: Int
    let symbolName: String
    let accent: String
    // Inclusive calendar window in the NORTHERN hemisphere.
    let startMonth: Int; let startDay: Int
    let endMonth: Int; let endDay: Int
}

enum Almanac {
    // The eight sabbats in calendar order (northern hemisphere windows).
    private static let wheel: [SabbatDef] = [
        SabbatDef(id: "imbolc", commonName: "Imbolc", academyTitle: "The First Stir",
                  blurb: "Under the snow, something has decided to live. The Library's oldest seeds turn over in their drawers.",
                  invitationTitle: "The First Stir",
                  invitation: "Find the first small sign that the dark is turning — a longer evening, a bud, a thaw. Keep it in one sentence.",
                  beliefBonus: 3, greyShift: -1, symbolName: "snowflake", accent: "candle",
                  startMonth: 2, startDay: 1, endMonth: 2, endDay: 2),
        SabbatDef(id: "ostara", commonName: "Ostara", academyTitle: "The Rebalancing",
                  blurb: "The Library reorganizes itself overnight. Books migrate. Light and dark stand equal, and the whole school exhales.",
                  invitationTitle: "The Rebalancing",
                  invitation: "Name one thing coming into balance for you, and one still tipping. The Compass glows in all four directions today.",
                  beliefBonus: 2, greyShift: 0, symbolName: "circle.lefthalf.filled", accent: "green",
                  startMonth: 3, startDay: 19, endMonth: 3, endDay: 21),
        SabbatDef(id: "beltane", commonName: "Beltane", academyTitle: "The Greenfire",
                  blurb: "The courtyard is reckless with bloom. Vines climb the shelves with tiny books for leaves. The bees in the Compass Rose are helpful and a little drunk.",
                  invitationTitle: "The Greenfire",
                  invitation: "Find the most alive green thing near you and describe it as if it could hear you. (It can.)",
                  beliefBonus: 4, greyShift: -1, symbolName: "leaf.fill", accent: "green",
                  startMonth: 5, startDay: 1, endMonth: 5, endDay: 1),
        SabbatDef(id: "litha", commonName: "Litha", academyTitle: "The Longest Day",
                  blurb: "The Library stays open all night. Lanterns float. Sentences run long and golden and sun-drunk.",
                  invitationTitle: "The Longest Day",
                  invitation: "Stay up toward the light — dusk or dawn — and keep one sentence about what the long day left you.",
                  beliefBonus: 4, greyShift: -2, symbolName: "sun.max.fill", accent: "gold",
                  startMonth: 6, startDay: 20, endMonth: 6, endDay: 22),
        SabbatDef(id: "lughnasadh", commonName: "Lughnasadh", academyTitle: "The First Harvest",
                  blurb: "The first grain comes in. Professors look proud and tired. The kitchens smell of bread that wasn't there an hour ago.",
                  invitationTitle: "The First Harvest",
                  invitation: "Name one thing you made or gathered this season — however small. Keep it like a loaf set on a sill.",
                  beliefBonus: 3, greyShift: 0, symbolName: "leaf", accent: "gold",
                  startMonth: 8, startDay: 1, endMonth: 8, endDay: 2),
        SabbatDef(id: "mabon", commonName: "Mabon", academyTitle: "The Second Rebalancing",
                  blurb: "Balance again, but golden and grateful. Books settle into their winter homes. Students share what they've learned.",
                  invitationTitle: "The Second Rebalancing",
                  invitation: "Name one thing you're grateful you kept, and one you're ready to let settle into the dark.",
                  beliefBonus: 3, greyShift: 0, symbolName: "circle.righthalf.filled", accent: "amber",
                  startMonth: 9, startDay: 21, endMonth: 9, endDay: 23),
        SabbatDef(id: "samhain", commonName: "Samhain", academyTitle: "The Thinning",
                  blurb: "The door between the kept and the lost stands ajar. The Book remembers more than usual tonight, and is gentler about it.",
                  invitationTitle: "The Thinning",
                  invitation: "Name someone or something you've lost, and one thing it left in your keeping. The veil is thin; be honest, be kind.",
                  beliefBonus: 5, greyShift: 1, symbolName: "flame", accent: "amber",
                  startMonth: 10, startDay: 31, endMonth: 11, endDay: 1),
        SabbatDef(id: "yule", commonName: "Yule", academyTitle: "The Darkest Class",
                  blurb: "Held by candlelight. The longest night, taught honestly. Everyone speaks softly; the fireplaces are crowded.",
                  invitationTitle: "The Darkest Class",
                  invitation: "Name one small thing that survives the longest night with you. Keep it where the candle can reach it.",
                  beliefBonus: 4, greyShift: 1, symbolName: "moon.stars.fill", accent: "candle",
                  startMonth: 12, startDay: 20, endMonth: 12, endDay: 23)
    ]

    private static func dayOfYearOrdinal(month: Int, day: Int) -> Int { month * 100 + day }

    private static func northernSabbat(on date: Date, calendar: Calendar) -> SabbatDef? {
        let comps = calendar.dateComponents([.month, .day], from: date)
        guard let m = comps.month, let d = comps.day else { return nil }
        let value = dayOfYearOrdinal(month: m, day: d)
        return wheel.first { sabbat in
            let start = dayOfYearOrdinal(month: sabbat.startMonth, day: sabbat.startDay)
            let end = dayOfYearOrdinal(month: sabbat.endMonth, day: sabbat.endDay)
            return value >= start && value <= end
        }
    }

    /// The active sabbat for a date, mapped for hemisphere (southern observes the
    /// opposite point of the wheel on the same calendar date).
    static func activeSabbat(on date: Date = Date(), hemisphere: Hemisphere = .northern, calendar: Calendar = .current) -> Celebration? {
        guard let northern = northernSabbat(on: date, calendar: calendar),
              let index = wheel.firstIndex(where: { $0.id == northern.id }) else { return nil }
        let def = hemisphere == .southern ? wheel[(index + 4) % wheel.count] : northern
        return Celebration(
            id: "sabbat-\(def.id)",
            kind: .sabbat,
            commonName: def.commonName,
            academyTitle: def.academyTitle,
            blurb: def.blurb,
            invitationTitle: def.invitationTitle,
            invitation: def.invitation,
            beliefBonus: def.beliefBonus,
            greyShift: def.greyShift,
            symbolName: def.symbolName,
            accent: def.accent,
            priority: 100
        )
    }

    /// The active lunar esbat (Full or New Moon), if the moon is near either edge.
    static func activeEsbat(on date: Date = Date()) -> Celebration? {
        let phase = MoonPhaseCalendar.phase(on: date)
        if phase.illuminatedFraction >= 0.96 {
            return Celebration(
                id: "esbat-full", kind: .esbat, commonName: "Full Moon",
                academyTitle: "The Luminous Gathering",
                blurb: "Classes are cancelled after sunset. Everyone gathers in the courtyard to read by moonlight. Strangers talk to each other; the sentences glow.",
                invitationTitle: "Moonwrite",
                invitation: "Write your one-sentence souvenir by the light of the full moon. It will glow on the page.",
                beliefBonus: 5, greyShift: -2, symbolName: "moonphase.full.moon", accent: "violet", priority: 80
            )
        }
        if phase.illuminatedFraction <= 0.04 {
            return Celebration(
                id: "esbat-new", kind: .esbat, commonName: "New Moon",
                academyTitle: "The Quiet Hours",
                blurb: "The Academy goes contemplative-dark. Candles only. The words hold their breath.",
                invitationTitle: "The Listening",
                invitation: "Sit in real silence for two minutes, then keep one sentence about what you heard underneath it.",
                beliefBonus: 3, greyShift: 1, symbolName: "moonphase.new.moon", accent: "slate", priority: 70
            )
        }
        return nil
    }

    /// Meteor showers, by their real date windows.
    static func activeShower(on date: Date = Date(), calendar: Calendar = .current) -> Celebration? {
        let comps = calendar.dateComponents([.month, .day], from: date)
        guard let m = comps.month, let d = comps.day else { return nil }
        let value = m * 100 + d
        if (811...813).contains(value) {
            return Celebration(id: "shower-perseids", kind: .shower, commonName: "The Perseids",
                               academyTitle: "The Falling Letters",
                               blurb: "The ceiling of the Library goes briefly transparent. You can see real constellations through the stone.",
                               invitationTitle: "The Falling Letters",
                               invitation: "Catch one falling star — real or remembered — and keep the wish you made on it.",
                               beliefBonus: 3, greyShift: -1, symbolName: "sparkles", accent: "violet", priority: 50)
        }
        if (1213...1215).contains(value) {
            return Celebration(id: "shower-geminids", kind: .shower, commonName: "The Geminids",
                               academyTitle: "The Winter Stars",
                               blurb: "Like the Perseids but colder. Hot chocolate appears in everyone's hands, unasked.",
                               invitationTitle: "The Winter Stars",
                               invitation: "Find one bright thing in the cold dark and keep the wish it pulled out of you.",
                               beliefBonus: 3, greyShift: -1, symbolName: "sparkles", accent: "slate", priority: 50)
        }
        return nil
    }

    /// Everything alive on a date, strongest first.
    static func celebrations(on date: Date = Date(), hemisphere: Hemisphere = .northern, calendar: Calendar = .current) -> [Celebration] {
        [activeSabbat(on: date, hemisphere: hemisphere, calendar: calendar),
         activeEsbat(on: date),
         activeShower(on: date, calendar: calendar)]
            .compactMap { $0 }
            .sorted { $0.priority > $1.priority }
    }

    /// The single headline celebration for a date, if any.
    static func active(on date: Date = Date(), hemisphere: Hemisphere = .northern, calendar: Calendar = .current) -> Celebration? {
        celebrations(on: date, hemisphere: hemisphere, calendar: calendar).first
    }

    /// Combined effect of every active celebration on the Nothing's grey.
    static func greyShift(on date: Date = Date(), hemisphere: Hemisphere = .northern, calendar: Calendar = .current) -> Int {
        celebrations(on: date, hemisphere: hemisphere, calendar: calendar).reduce(0) { $0 + $1.greyShift }
    }

    /// Atmosphere: each celebration leans the feed toward thematically-fitting
    /// page kinds (a curator nudge, never a veto).
    static func surfaceBoosts(on date: Date = Date(), hemisphere: Hemisphere = .northern, calendar: Calendar = .current) -> [BookPageType: Int] {
        var boosts: [BookPageType: Int] = [:]
        func add(_ type: BookPageType, _ amount: Int) { boosts[type, default: 0] += amount }
        for celebration in celebrations(on: date, hemisphere: hemisphere, calendar: calendar) {
            switch celebration.id {
            case "esbat-full":
                add(.souvenir, 8); add(.diary, 4)            // Moonwrite
            case "esbat-new":
                add(.rest, 8); add(.mood, 4)                 // The Listening
            case "sabbat-samhain":
                add(.bookRemembered, 10); add(.inkrestOfficeHours, 4)  // the returning / the lost
            case "sabbat-beltane":
                add(.letter, 8); add(.castMember, 4); add(.wonderCompass, 4)  // connection
            case "sabbat-imbolc":
                add(.diary, 6); add(.mood, 4)                // first stirrings
            case "sabbat-litha":
                add(.wonderCompass, 8); add(.anchor, 6)      // out in the long day
            case "sabbat-lughnasadh", "sabbat-mabon":
                add(.bookOfYou, 6); add(.souvenir, 4)        // harvest / gratitude
            case "sabbat-ostara":
                add(.aboutYou, 4); add(.wonderCompass, 4)    // rebalancing
            case "sabbat-yule":
                add(.rest, 6); add(.diary, 4)                // the darkest, kept warm
            case "shower-perseids", "shower-geminids":
                add(.wonderCompass, 6); add(.souvenir, 4)    // make a wish
            default:
                break
            }
        }
        return boosts
    }
}

// MARK: - The Book's returning greeting
//
// Each time a returning reader opens the app (after the opening movie, not the
// first run), the Book greets them by name with a rotating opener and one
// dynamic line summarizing what's alive in the world right now. Pure, testable;
// the app animates it in as a temporary overlay.

struct BookGreetingContext: Equatable {
    var name: String
    var celebrationTitle: String?
    var openBargainFae: String?
    var pactLine: String?
    var keptYesterday: Int
    var greyLevel: Int
    var seed: Int

    init(name: String, celebrationTitle: String? = nil, openBargainFae: String? = nil,
         pactLine: String? = nil, keptYesterday: Int = 0, greyLevel: Int = 0, seed: Int = 0) {
        self.name = name
        self.celebrationTitle = celebrationTitle
        self.openBargainFae = openBargainFae
        self.pactLine = pactLine
        self.keptYesterday = keptYesterday
        self.greyLevel = greyLevel
        self.seed = seed
    }
}

struct BookGreeting: Equatable {
    var greeting: String   // "Hello, bj — I'm so glad you're back."
    var line: String       // the dynamic summary / call to magic
}

enum BookGreetingComposer {
    static let openers: [String] = [
        "Hello, {name} — I'm so glad you're back.",
        "Welcome back, {name}.",
        "There you are, {name}. The Book kept your place.",
        "{name}. The ink missed you.",
        "Back again, {name}? Good.",
        "Oh — {name}. Right on time."
    ]

    static func compose(_ context: BookGreetingContext) -> BookGreeting {
        let name = context.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "friend" : context.name
        let opener = openers[abs(context.seed) % openers.count]
            .replacingOccurrences(of: "{name}", with: name)

        let line: String
        if let title = context.celebrationTitle {
            line = "Tonight the Wheel keeps \(title). Ready to make some magic?"
        } else if let fae = context.openBargainFae {
            line = "A \(fae) is still waiting on a bargain. Ready to make some magic?"
        } else if let pact = context.pactLine, !pact.isEmpty {
            line = "\(pact) Ready to make some magic?"
        } else if context.keptYesterday > 0 {
            line = "You kept \(context.keptYesterday) page\(context.keptYesterday == 1 ? "" : "s") yesterday. Shall we add to them?"
        } else if context.greyLevel >= 2 {
            line = "It's been a little grey. One kept page can turn the light back up."
        } else {
            line = "Ready to make some magic?"
        }
        return BookGreeting(greeting: opener, line: line)
    }
}
