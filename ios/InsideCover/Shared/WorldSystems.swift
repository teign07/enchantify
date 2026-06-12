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
            talismanName: "The Dusk Thorn",
            isHidden: true
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
