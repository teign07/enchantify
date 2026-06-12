import Foundation


struct BookSourceInputs: Equatable {
    var body: BodySourceSignal?
    var weather: WeatherSourceSignal?
    var enchantedWeather: EnchantedWeatherSignal?
    var anchors: [AnchorRecord] = AnchorRegistry.defaultAnchors
    var nearbyAnchor: AnchorProximity?
    var preparedAnchorSurface: SurfacePage?
    var narrative: NarrativeSourceSnapshot?
    var selfFacts: [SelfFact] = []
    var facultyEntries: [FacultyEntry] = []
    var customCastMembers: [CustomCastMember] = []
    var electives: [UnwrittenElective] = []
    var entityBeliefOffsets: [String: Int] = [:]
    var surfaceHistory: [String: SurfaceHistoryRecord] = [:]
    var calendarEvents: [CalendarEventSignal] = []
    var nearbyPlaces: [LocalPlaceSignal] = []
    var resurfacingCandidates: [BookPage] = []
    var quietDays: Int = 0
    var currentArc: StoryArc?
    var recentNarrativeEvents: [NarrativeEvent] = []

    func recentVarietyKeys(within seconds: TimeInterval = 48 * 3600, now: Date = Date()) -> Set<String> {
        Set(surfaceHistory.filter { now.timeIntervalSince($0.value.lastShownAt) < seconds }.keys)
    }
    var selectedWonderCompass: ReferenceSnippet?
    var selectedWonderCompassSelector: String?
    var preparedIlluminatedPhotoSurface: SurfacePage?
    var preparedStoryPageSurface: SurfacePage?
    var preparedGossipPageSurface: SurfacePage?
    var preparedFacultyResearchSurface: SurfacePage?
    var preparedLetterSurface: SurfacePage?
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
            anchors: AnchorRegistry.defaultAnchors,
            nearbyAnchor: nil,
            preparedAnchorSurface: nil,
            narrative: nil,
            selfFacts: [],
            facultyEntries: [],
            customCastMembers: [],
            resurfacingCandidates: [],
            recentNarrativeEvents: [],
            selectedWonderCompass: nil,
            selectedWonderCompassSelector: nil,
            preparedIlluminatedPhotoSurface: nil,
            preparedStoryPageSurface: nil,
            preparedGossipPageSurface: nil,
            preparedFacultyResearchSurface: nil,
            preparedLetterSurface: nil,
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

enum MarginsAtlasVariant: String, Codable, Equatable, CaseIterable {
    case loom
    case constellation

    var title: String {
        switch self {
        case .loom: return "The Loom"
        case .constellation: return "The Constellation"
        }
    }

    var detail: String {
        switch self {
        case .loom:
            return "Threads warm, tighten, and cross where the cast has begun to matter to one another."
        case .constellation:
            return "Stars brighten where Belief lives, with lines showing where your attention has flowed."
        }
    }
}

protocol BookPageSourceAdapter {
    var source: BookPageSource { get }
    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage]
    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage
}

extension BookPageSourceAdapter {
    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        candidates(for: day, context: context, inputs: inputs, now: now).first ?? SurfacePage(
            id: "manual-\(source.type.rawValue)-\(day.id)-\(Int(now.timeIntervalSince1970))",
            type: source.type,
            sourceID: source.id,
            intent: nil,
            renderStyle: .promptCard,
            score: 58,
            reason: "Opened directly from the Glow menu.",
            prompt: source.title,
            detail: source.note,
            payload: BookPagePayload(
                headline: source.title,
                body: source.note,
                metadata: [
                    "source": source.id,
                    "placeholder": "Write what this page needs to keep.",
                    "tags": "manual-page,\(source.type.rawValue)"
                ]
            )
        )
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

struct DiaryPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .diary)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        [
            SurfacePage(
                id: "\(source.id)-\(day.id)-\(SurfaceCadence.slotID(for: now, hours: 2))",
                type: .diary,
                sourceID: source.id,
                intent: .capture,
                renderStyle: .promptCard,
                score: context.distress.isActive ? 74 : 60,
                reason: context.distress.isActive ? "A private page can hold the present without fixing it." : "The Book has room for one honest present-tense note.",
                prompt: "What is happening right now?",
                detail: "Write what you are experiencing, thinking, or feeling in this moment. No polish required.",
                payload: BookPagePayload(
                    headline: "Diary Page",
                    body: "Write what you are experiencing, thinking, or feeling right now, in this moment.",
                    metadata: [
                        "source": source.id,
                        "placeholder": "Right now I am noticing...\nI am thinking...\nI am feeling...",
                        "tags": "diary,page,private,present-moment"
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
        guard let window = DailyCheckInCadence.activeWindow(for: now) else { return [] }
        guard !didCaptureSouvenir(in: window, day: day) else { return [] }
        let eveningPrompt = window.id == "evening"
        return [
            SurfacePage(
                id: "\(source.id)-\(day.id)-\(window.id)",
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
                    metadata: [
                        "source": source.id,
                        "checkInWindowID": window.id,
                        "checkInWindowName": window.name,
                        "tags": "souvenir,check-in-window:\(window.id)"
                    ]
                )
            )
        ]
    }

    private func didCaptureSouvenir(in window: DailyCheckInWindow, day: BookDay) -> Bool {
        let tag = "check-in-window:\(window.id)"
        return day.pages.contains { page in
            page.type == .souvenir && page.tags.contains(tag)
        }
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

struct BookRememberedPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .bookRemembered)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard !didRememberToday(day) else { return [] }
        guard let visitation = BookRememberedEngine.visitation(
            from: inputs.resurfacingCandidates,
            day: day,
            inputs: inputs,
            now: now
        ) else {
            return []
        }
        return [visitation.surface(source: source, day: day, now: now)]
    }

    private func didRememberToday(_ day: BookDay) -> Bool {
        day.pages.contains { page in
            page.type == .bookRemembered || page.tags.contains("book-remembered")
        }
    }
}

struct BookRememberedVisitation: Equatable {
    var page: BookPage
    var score: Int
    var reason: String
    var action: String

    func surface(source: BookPageSource, day: BookDay, now: Date) -> SurfacePage {
        let rememberedText = page.userInput.trimmingCharacters(in: .whitespacesAndNewlines)
        let ageLine = BookRememberedEngine.ageLine(from: page.createdAt, to: now)
        let body = """
        \(ageLine), you kept this:

        "\(rememberedText)"

        \(reason)

        \(action)
        """
        return SurfacePage(
            id: "\(source.id)-\(day.id)-\(page.id.stableHash)",
            type: .bookRemembered,
            sourceID: source.id,
            intent: .resurface,
            renderStyle: .archiveReturn,
            score: score,
            reason: "An old kept page rhymes with today.",
            prompt: "The Book remembered.",
            detail: "\(reason) \(action)",
            payload: BookPagePayload(
                headline: source.title,
                body: body,
                metadata: [
                    "source": source.id,
                    "rememberedPageID": page.id,
                    "rememberedPageType": page.type.rawValue,
                    "rememberedPageDate": ISO8601DateFormatter().string(from: page.createdAt),
                    "rememberedText": rememberedText,
                    "rhymeReason": reason,
                    "tinyAction": action,
                    "tags": "book-remembered,archive-return,visitation,remembered-page:\(page.id)"
                ]
            )
        )
    }
}

enum BookRememberedEngine {
    static func visitation(
        from candidates: [BookPage],
        day: BookDay,
        inputs: BookSourceInputs,
        now: Date,
        calendar: Calendar = .current
    ) -> BookRememberedVisitation? {
        let eligible = candidates
            .filter { isEligible($0, day: day, now: now, calendar: calendar) }
            .map { page in scored(page, inputs: inputs, now: now, calendar: calendar) }
            .filter { $0.score >= 62 }
            .sorted { left, right in
                if left.score == right.score {
                    return left.page.createdAt < right.page.createdAt
                }
                return left.score > right.score
            }
        guard let best = eligible.first else { return nil }
        return BookRememberedVisitation(
            page: best.page,
            score: best.score,
            reason: best.reason,
            action: tinyAction(for: best.page, reason: best.reason, inputs: inputs, now: now, calendar: calendar)
        )
    }

    static func ageLine(from past: Date, to now: Date, calendar: Calendar = .current) -> String {
        let days = max(1, calendar.dateComponents([.day], from: calendar.startOfDay(for: past), to: calendar.startOfDay(for: now)).day ?? 1)
        if days >= 365 {
            let years = max(1, days / 365)
            return years == 1 ? "About a year ago" : "About \(years) years ago"
        }
        if days >= 60 {
            return "About \(max(2, days / 30)) months ago"
        }
        if days >= 14 {
            return "About \(max(2, days / 7)) weeks ago"
        }
        if days == 1 {
            return "Yesterday"
        }
        return "\(days) days ago"
    }

    private static func isEligible(_ page: BookPage, day: BookDay, now: Date, calendar: Calendar) -> Bool {
        guard page.createdAt < calendar.startOfDay(for: now) else { return false }
        guard page.type != .bookOfYou, page.type != .bookRemembered else { return false }
        guard !page.userInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return false }
        return !day.pages.contains { todayPage in
            todayPage.tags.contains("remembered-page:\(page.id)")
        }
    }

    private static func scored(
        _ page: BookPage,
        inputs: BookSourceInputs,
        now: Date,
        calendar: Calendar
    ) -> (page: BookPage, score: Int, reason: String) {
        var score = 42
        var reasons: [String] = []
        let pageText = page.userInput.lowercased()
        let pageTags = Set(page.tags.map { $0.lowercased() })
        let currentWeather = [inputs.weather?.phrase, inputs.weather?.forecast, inputs.enchantedWeather?.summary]
            .compactMap { $0?.lowercased() }
            .joined(separator: " ")
        let weatherTokens = ["fog", "rain", "snow", "storm", "cloud", "sun", "wind", "cold", "warm", "humid", "clear", "gray", "grey"]
        let weatherMatches = weatherTokens.filter { token in
            currentWeather.contains(token) && (pageText.contains(token) || pageTags.contains(token))
        }
        if let first = weatherMatches.first {
            score += 28
            reasons.append("Today has \(first) in it again.")
        }

        let hour = calendar.component(.hour, from: now)
        let rememberedHour = calendar.component(.hour, from: page.createdAt)
        if abs(hour - rememberedHour) <= 1 {
            score += 9
            reasons.append("The hour is near the old hour.")
        }

        let month = calendar.component(.month, from: now)
        let rememberedMonth = calendar.component(.month, from: page.createdAt)
        if month == rememberedMonth {
            score += 10
            reasons.append("The season is leaning the same way.")
        }

        let currentText = [
            inputs.calendarEvents.prefix(4).map(\.title).joined(separator: " "),
            inputs.nearbyPlaces.prefix(4).map(\.name).joined(separator: " "),
            inputs.recentNarrativeEvents.prefix(6).map(\.summary).joined(separator: " ")
        ].joined(separator: " ").lowercased()
        let overlap = meaningfulWords(in: pageText).intersection(meaningfulWords(in: currentText))
        if let word = overlap.sorted().first {
            score += min(18, overlap.count * 6)
            reasons.append("The word \"\(word)\" has returned to the margin.")
        }

        if page.type == .souvenir {
            score += 8
        }
        if page.usedInBookOfYou {
            score += 6
        }

        if reasons.isEmpty {
            reasons.append("It came back softly, for no louder reason than timing.")
        }
        return (page, score, reasons[0])
    }

    private static func meaningfulWords(in text: String) -> Set<String> {
        let stop: Set<String> = ["the", "and", "with", "that", "this", "from", "into", "again", "today", "there", "their", "then", "than", "were", "was", "you", "your", "for", "but", "not"]
        return Set(text
            .lowercased()
            .split { !$0.isLetter && !$0.isNumber }
            .map(String.init)
            .filter { $0.count >= 4 && !stop.contains($0) }
        )
    }

    private static func tinyAction(for page: BookPage, reason: String, inputs: BookSourceInputs, now: Date, calendar: Calendar) -> String {
        let text = "\(page.userInput) \(page.tags.joined(separator: " "))".lowercased()
        if text.contains("walk") || text.contains("trail") || text.contains("outside") {
            return "Stand at the nearest threshold for ten seconds. Let the outside know you noticed."
        }
        if text.contains("hand") || text.contains("touch") || text.contains("window") {
            return "Touch a window or doorframe for ten seconds. Let the old weather recognize you."
        }
        if text.contains("coffee") || text.contains("tea") || text.contains("drink") {
            return "Before the next sip, pause long enough for the cup to become real in your hand."
        }
        if text.contains("amanda") || text.contains("kid") || text.contains("family") || text.contains("friend") {
            return "Send one small warmth toward the person in that memory, even if it is only silent."
        }
        if reason.lowercased().contains("rain") || reason.lowercased().contains("fog") || reason.lowercased().contains("snow") {
            return "Look at the nearest glass for ten seconds. Let the weather have a witness."
        }
        let hour = calendar.component(.hour, from: now)
        if hour >= 17 {
            return "Put one hand on the table or wall. Tell the day, quietly: I kept one thing."
        }
        return "Look up from the screen and name one physical thing that stayed with you."
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
        let moon = MoonPhaseCalendar.phase(on: now)
        let eveningBody = hour >= 17 || hour < 6
            ? "\(enchanted.enchantified)\n\n\(moon.enchantedLine)\n\nWeather: \(rawLine) · \(moon.name)"
            : "\(enchanted.enchantified)\n\nWeather: \(rawLine) · \(moon.name)"
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
                    body: eveningBody,
                    metadata: [
                        "source": source.id,
                        "uses": weather.source,
                        "privacy": "public reference",
                        "selector": enchanted.selector,
                        "symbol": enchanted.symbolName,
                        "rawWeather": weather.phrase,
                        "moonPhase": moon.name,
                        "moonSymbol": moon.symbolName,
                        "cadence": "four-hour"
                    ]
                )
            )
        ]
    }
}

struct AcademyClassPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .academyClass)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive,
              let (session, block) = AcademyScheduleRegistry.sessionInProgress(at: now) else {
            return []
        }
        return [surface(for: session, block: block, day: day, context: context, now: now)]
    }

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        if let (session, block) = AcademyScheduleRegistry.sessionInProgress(at: now) {
            return surface(for: session, block: block, day: day, context: context, now: now)
        }
        return SurfacePage(
            id: "\(source.id)-between-bells-\(Int(now.timeIntervalSince1970))",
            type: .academyClass,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .loreLetter,
            score: 40,
            reason: "No class or club is in session right now.",
            prompt: "Between Bells",
            detail: AcademyScheduleRegistry.nextSessionDescription(after: now),
            payload: BookPagePayload(
                headline: "The Halls Between Bells",
                body: "No class or club is in session. \(AcademyScheduleRegistry.nextSessionDescription(after: now))",
                metadata: [
                    "source": source.id,
                    "tags": "academy,class,between-bells"
                ]
            )
        )
    }

    private func surface(
        for session: AcademySession,
        block: String,
        day: BookDay,
        context: CuratorContext,
        now: Date
    ) -> SurfacePage {
        let isClub = session.kind == .club
        return SurfacePage(
            id: "\(source.id)-\(session.id)-\(day.id)-\(block)",
            type: .academyClass,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .loreLetter,
            score: context.distress.isActive ? 50 : (isClub ? 72 : 76),
            reason: isClub
                ? "\(session.name) is gathering right now in \(session.room)."
                : "\(session.name) is in session right now with \(session.leader).",
            prompt: session.name,
            detail: isClub
                ? "Meeting now in \(session.room). \(session.style.prefix(1).uppercased() + session.style.dropFirst())."
                : "In session now with \(session.leader), \(session.room).",
            payload: BookPagePayload(
                headline: isClub ? "Club: \(session.name)" : "Class: \(session.name)",
                body: "The door to \(session.room) is ajar. \(session.leader) is mid-\(isClub ? "gathering" : "lesson"). Open the page to step inside.",
                metadata: [
                    "source": source.id,
                    "sessionID": session.id,
                    "sessionKind": session.kind.rawValue,
                    "sessionName": session.name,
                    "sessionLeader": session.leader,
                    "sessionRoom": session.room,
                    "sessionCompanions": session.companions.joined(separator: ", "),
                    "sessionTeaches": session.teaches,
                    "sessionStyle": session.style,
                    "sessionBlock": block,
                    "tags": "academy,\(session.kind.rawValue),\(session.id)"
                ]
            )
        )
    }
}

struct ElectivePageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .elective)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        var pages: [SurfacePage] = []
        let active = inputs.electives.filter(\.isActive)

        if !active.isEmpty {
            pages.append(flyleafSurface(active: active, day: day, now: now))
        }

        let calendar = Calendar.current
        let hour = calendar.component(.hour, from: now)
        let offeredToday = inputs.electives.contains { calendar.isDate($0.createdAt, inSameDayAs: now) }
        if active.count < UnwrittenElective.maxActive,
           !offeredToday,
           (10..<21).contains(hour),
           !context.distress.isActive,
           let sender = offerSender(inputs: inputs, day: day, now: now) {
            pages.append(offerSurface(sender: sender, inputs: inputs, day: day, now: now))
        }
        return pages
    }

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        let active = inputs.electives.filter(\.isActive)
        if !active.isEmpty {
            return flyleafSurface(active: active, day: day, now: now)
        }
        if let sender = offerSender(inputs: inputs, day: day, now: now) {
            return offerSurface(sender: sender, inputs: inputs, day: day, now: now)
        }
        return flyleafSurface(active: [], day: day, now: now)
    }

    private func homeContext(inputs: BookSourceInputs) -> String {
        if let fact = inputs.selfFacts.first(where: { fact in
            fact.tags.contains(where: { $0.contains("home") || $0.contains("place") || $0.contains("town") })
        }) {
            return fact.answer
        }
        if let weather = inputs.weather, weather.isAvailable {
            return "wherever the weather is currently: \(weather.phrase)"
        }
        return "the player's home town (unnamed so far)"
    }

    private func offerSender(inputs: BookSourceInputs, day: BookDay, now: Date) -> NarrativeWorldEntity? {
        let pool = (NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity))
            .filter { $0.kind == .character }
            .filter { !($0.unwrittenInterest ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            .filter { entity in
                // One outstanding favor per character.
                !inputs.electives.contains { $0.characterID == entity.id && $0.isActive }
            }
        guard !pool.isEmpty else { return nil }
        let slot = SurfaceCadence.slotID(for: now, hours: 8)
        let scored = pool.map { entity -> (NarrativeWorldEntity, Int) in
            let jitter = abs("\(day.id)-\(slot)-\(entity.id)-elective".stableHash % 21)
            return (entity, entity.belief + entity.narrativeWeight + jitter)
        }
        return scored.max { $0.1 < $1.1 }?.0
    }

    private func offerSurface(sender: NarrativeWorldEntity, inputs: BookSourceInputs, day: BookDay, now: Date) -> SurfacePage {
        SurfacePage(
            id: "\(source.id)-offer-\(sender.id)-\(day.id)",
            type: .elective,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .loreLetter,
            score: 70,
            reason: "\(sender.name) has been working up the nerve to ask a favor.",
            prompt: "\(sender.name) has a favor to ask",
            detail: "A folded note, tucked into the flyleaf, waiting to be opened.",
            payload: BookPagePayload(
                headline: "An Unwritten Elective",
                body: "A note from \(sender.name) is tucked into the Book's flyleaf. Open the page to read what they are asking, then keep it to accept.",
                metadata: [
                    "source": source.id,
                    "electiveOffer": "true",
                    "senderID": sender.id,
                    "senderName": sender.name,
                    "senderInterest": sender.unwrittenInterest ?? "",
                    "senderTraits": sender.traits.joined(separator: ", "),
                    "senderQuirks": sender.quirks.joined(separator: "; "),
                    "senderBeliefs": sender.beliefs.joined(separator: "; "),
                    "senderGoals": sender.goals.joined(separator: "; "),
                    "senderChapter": sender.chapter ?? "",
                    "season": AnchorRegistry.currentSeason(for: now),
                    "nearbyPlaces": inputs.nearbyPlaces.prefix(10).map(\.promptLine).joined(separator: "\n"),
                    "homeContext": homeContext(inputs: inputs),
                    "tags": "elective,offer,entity:\(sender.id)"
                ]
            )
        )
    }

    private func flyleafSurface(active: [UnwrittenElective], day: BookDay, now: Date) -> SurfacePage {
        // The interactive flyleaf list in the page sheet carries the full
        // asks and proof fields; the body stays a short framing line.
        let lines = active.isEmpty
            ? "The flyleaf is bare. When a character asks a favor and you accept, the note gets tucked in here. Five fit at most."
            : "\(active.count) note\(active.count == 1 ? "" : "s") tucked into the binding, each waiting for its sentence of proof."
        return SurfacePage(
            id: "\(source.id)-flyleaf-\(day.id)-\(SurfaceCadence.slotID(for: now, hours: 8))",
            type: .elective,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .loreLetter,
            score: 55,
            reason: active.isEmpty
                ? "The flyleaf is waiting for its first favor."
                : "\(active.count) favor\(active.count == 1 ? "" : "s") are tucked into the flyleaf.",
            prompt: "The Flyleaf",
            detail: "\(active.count)/\(UnwrittenElective.maxActive) notes tucked into the binding.",
            payload: BookPagePayload(
                headline: "The Inside Cover",
                body: lines,
                metadata: [
                    "source": source.id,
                    "electiveFlyleaf": "true",
                    "activeCount": "\(active.count)",
                    "tags": "elective,flyleaf"
                ]
            )
        )
    }
}

struct EnchantmentPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .enchantment)

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        surface(spell: rotatingSpell(for: day, now: now, manual: true), context: context, now: now, manual: true)
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        return [surface(spell: rotatingSpell(for: day, now: now, manual: false), context: context, now: now, manual: false)]
    }

    private func rotatingSpell(for day: BookDay, now: Date, manual: Bool) -> EnchantmentSpell {
        let spells = StoryEnchantmentCatalog.spells
        if manual {
            return spells[Int.random(in: 0..<spells.count)]
        }
        let slot = SurfaceCadence.slotID(for: now, hours: 4)
        let seed = abs("\(day.id)-\(slot)-enchantment".stableHash)
        return spells[seed % spells.count]
    }

    private func surface(spell: EnchantmentSpell, context: CuratorContext, now: Date, manual: Bool) -> SurfacePage {
        let slotID = manual ? "\(Int(now.timeIntervalSince1970))" : SurfaceCadence.slotID(for: now, hours: 4)
        return SurfacePage(
            id: "\(source.id)-\(spell.id)-\(slotID)",
            type: .enchantment,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .promptCard,
            score: context.distress.isActive ? 38 : 56,
            reason: "An ordinary thing nearby is ready to be enchanted.",
            prompt: spell.title,
            detail: spell.detail,
            payload: BookPagePayload(
                headline: "Enchantment Page: \(spell.title)",
                body: "\(spell.detail)\n\nChoose a photo or take one. The spell will illuminate the real subject and write the result into the margins.",
                metadata: [
                    "source": source.id,
                    "enchantmentID": spell.id,
                    "enchantmentName": spell.title,
                    "symbol": spell.symbolName,
                    "placeholder": "Choose a photo to cast \(spell.title).",
                    "tags": "enchantment,proof,real-world-magic,\(spell.id)"
                ]
            )
        )
    }
}

struct LabyrinthWelcomePageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .welcome)

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        welcomeSurface(
            playerName: playerName(inputs: inputs),
            score: 70,
            reason: "The Book can always re-open its first page."
        )
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        guard let name = playerName(inputs: inputs) else { return [] }
        guard inputs.surfaceHistory["source:\(source.id)"] == nil else { return [] }
        guard !day.pages.contains(where: { $0.type == .welcome || $0.tags.contains("welcome-labyrinth") }) else { return [] }

        return [
            welcomeSurface(
                playerName: name,
                score: context.distress.isActive ? 72 : 92,
                reason: "The Labyrinth of Stories is introducing itself before asking for anything else."
            )
        ]
    }

    private func welcomeSurface(playerName: String?, score: Int, reason: String) -> SurfacePage {
        let name = playerName?.nonEmpty ?? "Reader"
        return SurfacePage(
            id: "\(source.id)-first-page",
            type: .welcome,
            sourceID: source.id,
            intent: .importReference,
            renderStyle: .loreLetter,
            score: score,
            reason: reason,
            prompt: "Welcome to the Labyrinth of Stories",
            detail: "The Book says hello, plainly and properly.",
            payload: BookPagePayload(
                headline: "Welcome, \(name)",
                body: """
                Hello, \(name). I am the Labyrinth of Stories.

                You can also call me the Book. You can call me the app. Those are all true enough. I am the same doorway in three shapes: a place to notice your real life, a book that remembers what you keep, and a small machine that helps pages find you at the right time.

                Here is the simple loop.

                Pages will surface. Some will ask for one sentence. Some will offer a story, a letter, a mission, a photo illumination, a body note, a bit of weather, or a useful tip.

                Open what feels alive. Keep the pages that matter. Dismiss the ones that do not fit today. You do not need to keep everything. A book that keeps everything becomes a closet.

                Kept pages become memory. They help future pages speak less generically. They can warm characters, threads, places, and talismans. They can also become part of your Book of You at the end of the day.

                At night, when enough of the day has gathered, read your Book of You. That is the day's braid: not a score, not a report card, but a page that says, "This happened. You were here. It counted."

                What to do next:

                1. Keep one small true page.
                2. Let the shelf change.
                3. Use Glow when you want more or less of something.
                4. Read the braid tonight.

                Chapter Binding can wait. The Academy will still be there. First, let the Book learn the sound of your footsteps.
                """,
                metadata: [
                    "source": source.id,
                    "welcomePage": "true",
                    "playerName": name,
                    "privacy": "public reference",
                    "symbol": source.symbolName,
                    "tags": "welcome,welcome-labyrinth,first-run,labyrinth,book-of-you,how-to-play"
                ]
            )
        )
    }

    private func playerName(inputs: BookSourceInputs) -> String? {
        let usableFacts = inputs.selfFacts.filter { $0.usePermission != .doNotUse }
        let preferred = usableFacts.first { $0.questionID == "onboarding-name" }?.answer
            ?? usableFacts.first { $0.questionID == "called" }?.answer
            ?? usableFacts.first { $0.tags.contains("name") || $0.tags.contains("identity") }?.answer
        return preferred?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }
}

struct AboutYouPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .aboutYou)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }

        let isBound = inputs.selfFacts.contains { $0.questionID == "chapter-binding" }
        let hasName = inputs.selfFacts.contains { $0.tags.contains("name") }
        let chapterBinding = (!isBound && hasName && !context.distress.isActive) ? SurfacePage(
            id: "\(source.id)-chapter-binding",
            type: .aboutYou,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .loreLetter,
            score: 48,
            reason: "Chapter Binding is available when the reader wants an Academy philosophy to claim the margins.",
            prompt: "The Chapter Binding",
            detail: "Optional for now. Choose a Chapter when the question feels interesting.",
            payload: BookPagePayload(
                headline: "The Chapter Binding",
                body: "The candles in the Binding Hall are lit, but no one is rushing you. Each Chapter is a way of reading a life: authored, received, improvised, or co-written. Open this page when you want to choose the philosophy that sounds most like the inside of your own head.",
                metadata: [
                    "source": source.id,
                    "chapterBinding": "true",
                    "tags": "chapter,binding,identity,ceremony,optional"
                ]
            )
        ) : nil

        var pages: [SurfacePage] = []

        if let question = SelfKnowledgePackRegistry.nextQuestion(knownFacts: inputs.selfFacts, day: day, now: now) {
            let isFirstQuestion = inputs.selfFacts.isEmpty
            let calendar = Calendar.current
            let factsAnsweredToday = inputs.selfFacts.filter { calendar.isDate($0.createdAt, inSameDayAs: now) }
            let isCadenceAllowed: Bool
            if isFirstQuestion {
                isCadenceAllowed = true
            } else if factsAnsweredToday.count >= SelfKnowledgePackRegistry.maxAboutYouFactsPerDay {
                isCadenceAllowed = false
            } else if let lastAnsweredAt = inputs.selfFacts.map(\.createdAt).max(),
                      let nextAllowedAt = calendar.date(
                        byAdding: .hour,
                        value: SelfKnowledgePackRegistry.minimumHoursBetweenAboutYouFacts,
                        to: lastAnsweredAt
                      ) {
                isCadenceAllowed = now >= nextAllowedAt
            } else {
                isCadenceAllowed = true
            }

            if isCadenceAllowed {
                let score = isFirstQuestion ? 83 : (context.distress.isActive ? 46 : 67)
                let packName = SelfKnowledgePackRegistry.packName(for: question.packID)
                pages.append(
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
                )
            }
        }

        if let chapterBinding {
            pages.append(chapterBinding)
        }
        return pages
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
            runSurface(seed: seed, progress: progress, context: context, inputs: inputs, now: now),
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

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        let progress = CompassRunProgress.progress(for: day)
        let seed = WonderCompassRunGenerator.seed(for: day, inputs: inputs, progress: progress, now: now)
        return runSurface(seed: seed, progress: progress, context: context, inputs: inputs, now: now)
    }

    private func playfulMissionSurface(
        _ mission: PlayfulMission,
        seed: WonderCompassRunSeed,
        context: CuratorContext,
        now: Date
    ) -> SurfacePage {
        var metadata = metadata(for: seed, step: .sense)
        metadata["compassStep"] = "sense"
        metadata["compassMode"] = "standalone"
        metadata.removeValue(forKey: "runID")
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
        inputs: BookSourceInputs = .empty,
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
        metadata["compassMode"] = "runStart"
        metadata["nearbyPlaces"] = inputs.nearbyPlaces.prefix(10).map(\.promptLine).joined(separator: "\n")
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
        metadata["compassMode"] = standalone ? "standalone" : "runStep"
        metadata["standalone"] = standalone ? "true" : "false"
        if standalone {
            metadata.removeValue(forKey: "runID")
        }
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
                body: seed.body(for: step),
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

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        loreSurface(
            snippet: BookReferenceCatalog.rotatingLoreSnippet(for: day, inputs: inputs, now: now, manual: true),
            context: context
        )
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else {
            return []
        }

        let snippet = BookReferenceCatalog.rotatingLoreSnippet(for: day, inputs: inputs, now: now)
        return [loreSurface(snippet: snippet, context: context)]
    }

    private func loreSurface(snippet: ReferenceSnippet, context: CuratorContext) -> SurfacePage {
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
    }
}

struct PatreonPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .patreon)
    private let patreonURL = "https://patreon.com/thedoobaleedoos"

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        patreonSurface(
            snippet: BookReferenceCatalog.rotatingPatreonShelfSnippet(for: day, now: now, manual: true),
            day: day,
            context: context,
            now: now
        )
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else {
            return []
        }

        let snippet = BookReferenceCatalog.rotatingPatreonShelfSnippet(for: day, now: now)
        return [patreonSurface(snippet: snippet, day: day, context: context, now: now)]
    }

    private func patreonSurface(snippet: ReferenceSnippet, day: BookDay, context: CuratorContext, now: Date) -> SurfacePage {
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
        return SurfacePage(
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
    }
}

struct LabyrinthIllustrationPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .illustration)

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        illustrationSurface(
            plate: BookReferenceCatalog.rotatingLabyrinthIllustration(for: day, now: now, manual: true),
            context: context,
            now: now,
            manual: true
        )
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        let plate = BookReferenceCatalog.rotatingLabyrinthIllustration(for: day, now: now)
        return [illustrationSurface(plate: plate, context: context, now: now, manual: false)]
    }

    private func illustrationSurface(
        plate: LabyrinthIllustrationPlate,
        context: CuratorContext,
        now: Date,
        manual: Bool
    ) -> SurfacePage {
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
        let slotID = manual ? "\(Int(now.timeIntervalSince1970))" : SurfaceCadence.minuteSlotID(for: now, minutes: 20)
        return SurfacePage(
            id: "\(source.id)-\(plate.id)-\(slotID)",
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
        let chapterTalismanMoves = packet.chapterTalismanMoves.map(\.promptLine).joined(separator: "\n")
        let chapterTalismanDeltas = packet.chapterTalismanMoves.compactMap(\.ledgerToken).joined(separator: ",")
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
                    "selectedEntityIDs": packet.selectedEntities.map(\.id).joined(separator: ","),
                    "storyFormID": packet.storyFormID ?? "",
                    "storyFormName": packet.storyFormName ?? "",
                    "storyBeats": (packet.storyFormBeats ?? []).joined(separator: "\n"),
                    "storyGenreID": packet.storyGenreID ?? "",
                    "storyGenreName": packet.storyGenreName ?? "",
                    "storyGenreLens": packet.storyGenreLens ?? "",
                    "selectedThreadIDs": packet.selectedThreads.map(\.id).joined(separator: ","),
                    "selectedRelationships": selectedRelationships,
                    "entityMemories": selectedEntityMemories,
                    "realSignals": packet.realSignals.joined(separator: "\n"),
                    "relationshipPressures": packet.relationshipPressures.joined(separator: "\n"),
                    "chapterTalismanMoves": chapterTalismanMoves,
                    "chapterTalismanDeltas": chapterTalismanDeltas,
                    "uses": "characters, belief, relationship graph, story threads",
                    "cadence": "four-hour simulation"
                ]
            )
        )
    }
}

struct MarginsAtlasPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .marginsAtlas)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        let entities = NarrativePackRegistry.entities + inputs.customCastMembers.map(\.entity)
        let relationships = NarrativePackRegistry.relationships
        let events = inputs.recentNarrativeEvents
        let loom = NarrativeGraphData.loom(
            entities: entities,
            relationships: relationships,
            beliefOffsets: inputs.entityBeliefOffsets
        )
        let constellation = NarrativeGraphData.constellation(
            entities: entities,
            beliefOffsets: inputs.entityBeliefOffsets,
            events: events,
            playerBelief: inputs.narrative?.beliefWeight ?? 30
        )
        var pages: [SurfacePage] = []
        if !loom.nodes.isEmpty && !loom.edges.isEmpty {
            pages.append(surface(variant: .loom, graph: loom, day: day, now: now, score: 57 + min(22, loom.edges.count)))
        }
        if constellation.nodes.count > 1 {
            pages.append(surface(variant: .constellation, graph: constellation, day: day, now: now, score: 60 + min(20, constellation.edges.count * 3)))
        }
        return pages
    }

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        candidates(for: day, context: context, inputs: inputs, now: now).first ?? SurfacePage(
            id: "\(source.id)-empty-\(day.id)-\(Int(now.timeIntervalSince1970))",
            type: .marginsAtlas,
            sourceID: source.id,
            intent: .simulate,
            renderStyle: .graphEvent,
            score: 52,
            reason: "Opened directly from the Glow menu.",
            prompt: "The Atlas has not found enough ink yet.",
            detail: "Keep pages, move Belief, and let the story field gather a few more true lines.",
            payload: BookPagePayload(
                headline: "The Margins Atlas",
                body: "The page is waiting for relationships, Belief, and attention to leave enough tracks to draw.",
                metadata: [
                    "source": source.id,
                    "graphVariant": MarginsAtlasVariant.loom.rawValue,
                    "graphNodes": "",
                    "graphEdges": "",
                    "tags": "margins-atlas,graph,empty"
                ]
            )
        )
    }

    private func surface(
        variant: MarginsAtlasVariant,
        graph: NarrativeGraphData,
        day: BookDay,
        now: Date,
        score: Int
    ) -> SurfacePage {
        SurfacePage(
            id: "\(source.id)-\(variant.rawValue)-\(day.id)-\(SurfaceCadence.slotID(for: now, hours: 6))",
            type: .marginsAtlas,
            sourceID: source.id,
            intent: .simulate,
            renderStyle: .graphEvent,
            score: score,
            reason: variant == .loom ? "The cast has visible threads to read." : "Belief has left a star map in the margins.",
            prompt: variant.title,
            detail: variant.detail,
            payload: BookPagePayload(
                headline: variant.title,
                body: variant.detail,
                metadata: [
                    "source": source.id,
                    "graphVariant": variant.rawValue,
                    "graphNodes": encode(nodes: graph.nodes),
                    "graphEdges": encode(edges: graph.edges),
                    "tags": "margins-atlas,\(variant.rawValue),graph"
                ]
            )
        )
    }

    private func encode(nodes: [GraphNode]) -> String {
        nodes.map { node in
            [
                node.id,
                node.label,
                String(format: "%.2f", node.weight),
                node.chapterID ?? "",
                node.kindLabel
            ].map(escape).joined(separator: "||")
        }.joined(separator: "\n")
    }

    private func encode(edges: [GraphEdge]) -> String {
        edges.map { edge in
            [
                edge.id,
                edge.sourceID,
                edge.targetID,
                String(format: "%.3f", edge.strength),
                String(format: "%.3f", edge.warmth),
                edge.label
            ].map(escape).joined(separator: "||")
        }.joined(separator: "\n")
    }

    private func escape(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\n", with: "\\n")
            .replacingOccurrences(of: "||", with: "\\p")
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

struct CastMemberPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .castMember)

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        guard let member = selectedMember(from: inputs.customCastMembers, excluding: inputs.recentVarietyKeys(now: now), now: now, manual: true) else {
            return emptySurface(day: day, now: now)
        }
        return surface(for: member, context: context, now: now, manual: true)
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive,
              let member = selectedMember(from: inputs.customCastMembers, excluding: inputs.recentVarietyKeys(now: now), now: now, manual: false) else {
            return []
        }
        return [surface(for: member, context: context, now: now, manual: false)]
    }

    private func selectedMember(from members: [CustomCastMember], excluding recentKeys: Set<String> = [], now: Date, manual: Bool) -> CustomCastMember? {
        guard !members.isEmpty else { return nil }
        // Anyone the reader met in the last two days steps back so the rest
        // of the cast gets the page; the pool reopens once everyone has had
        // a turn.
        let fresh = members.filter { !recentKeys.contains("cast:\($0.id)") }
        let pool = fresh.isEmpty ? members : fresh
        let slot = manual ? "\(Int(now.timeIntervalSince1970))-\(UUID().uuidString)" : SurfaceCadence.minuteSlotID(for: now, minutes: 20)
        return pool
            .map { member in
                let jitter = stableIndex(for: "\(member.id)-\(slot)", count: 18)
                let score = member.narrativeWeight + member.baseBelief / 2 + jitter
                return (member, score)
            }
            .sorted { left, right in
                if left.1 == right.1 {
                    return left.0.updatedAt > right.0.updatedAt
                }
                return left.1 > right.1
            }
            .first?
            .0
    }

    private func surface(for member: CustomCastMember, context: CuratorContext, now: Date, manual: Bool) -> SurfacePage {
        var metadata = [
            "source": source.id,
            "entityID": member.id,
            "entityName": member.name,
            "entityKind": member.kind.rawValue,
            "meaning": member.meaning,
            "description": member.description,
            "tags": (member.tags + ["entity:\(member.id)", "custom-cast"]).joined(separator: ","),
            "traits": member.traits.joined(separator: ","),
            "privacy": "private local cast"
        ]
        if let imageAsset = member.imageAsset {
            metadata["imageAssetKind"] = imageAsset.kind.rawValue
            metadata["imageAssetReference"] = imageAsset.reference
        }
        let description = member.description.trimmingCharacters(in: .whitespacesAndNewlines)
        let body = [
            description.isEmpty ? nil : description,
            member.meaning.isEmpty ? nil : "What it means: \(member.meaning)",
            member.beliefs.isEmpty ? nil : "Belief: \(member.beliefs.joined(separator: " "))",
            member.goals.isEmpty ? nil : "Wants: \(member.goals.joined(separator: " "))"
        ]
            .compactMap(\.self)
            .joined(separator: "\n\n")
        let slotID = manual ? "\(Int(now.timeIntervalSince1970))" : SurfaceCadence.minuteSlotID(for: now, minutes: 20)
        return SurfacePage(
            id: "\(source.id)-\(member.id)-\(slotID)",
            type: .castMember,
            sourceID: source.id,
            intent: .importReference,
            renderStyle: .quoteCard,
            score: context.distress.isActive ? 48 : min(88, 54 + member.baseBelief / 2 + member.narrativeWeight / 3),
            reason: "\(member.name) has enough Belief to step into the margins.",
            prompt: member.name,
            detail: member.meaning.isEmpty ? "A user-made cast member." : member.meaning,
            payload: BookPagePayload(
                headline: member.name,
                body: body.isEmpty ? "This cast member exists because you gave it Belief." : body,
                metadata: metadata
            )
        )
    }

    private func emptySurface(day: BookDay, now: Date) -> SurfacePage {
        SurfacePage(
            id: "\(source.id)-empty-\(day.id)-\(Int(now.timeIntervalSince1970))",
            type: .castMember,
            sourceID: source.id,
            intent: .capture,
            renderStyle: .promptCard,
            score: 40,
            reason: "No custom cast member exists yet.",
            prompt: "No custom cast member yet.",
            detail: "Use Belief to add one first.",
            payload: BookPagePayload(
                headline: "The cast shelf is waiting.",
                body: "Give Belief to a new Cast Member, then this Page can surface them.",
                metadata: ["source": source.id]
            )
        )
    }

    private func stableIndex(for key: String, count: Int) -> Int {
        guard count > 0 else { return 0 }
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in key.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return Int(hash % UInt64(count))
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

struct OuterStacksAnchorPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .anchor)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        if let prepared = inputs.preparedAnchorSurface {
            return [prepared]
        }
        guard let proximity = inputs.nearbyAnchor else { return [] }
        return [surface(for: proximity, day: day, now: now)]
    }

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        if let prepared = inputs.preparedAnchorSurface {
            return prepared
        }
        if let proximity = inputs.nearbyAnchor {
            return surface(for: proximity, day: day, now: now)
        }
        return SurfacePage(
            id: "manual-\(source.id)-\(day.id)-\(Int(now.timeIntervalSince1970))",
            type: .anchor,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .loreLetter,
            score: 58,
            reason: "Known Anchors can open local rooms when the phone is close enough.",
            prompt: "Check nearby Anchors",
            detail: "The Book can ask for one location reading and listen for an Outer Stacks door.",
            payload: BookPagePayload(
                headline: "Outer Stacks",
                body: "No Anchor is glowing yet. Ask the Book to check nearby places; if a known Anchor is within two hundred meters, its room can rise as a page.",
                metadata: [
                    "source": source.id,
                    "privacy": "location stays on device",
                    "tags": "anchor,outer-stacks,location,local"
                ]
            )
        )
    }

    private func surface(for proximity: AnchorProximity, day: BookDay, now: Date) -> SurfacePage {
        let anchor = proximity.anchor
        let season = AnchorRegistry.currentSeason(for: now)
        let visitPhrase = proximity.visitMode == "FIRST_VISIT"
            ? "First visit"
            : "Return visit \(proximity.nextVisitCount)"
        let room = nonEmpty(anchor.outerStacksRoom)
            ?? "The room has not fully written itself yet, but the threshold is present."
        let body = [
            "\(anchor.name) is close enough to light.",
            "\(visitPhrase). \(season).",
            "Room: \(room)",
            "Fae: \(nonEmpty(anchor.fae) ?? "unnamed")",
            "Local rule: \(nonEmpty(anchor.localRule) ?? "Notice before you take a step.")",
            nonEmpty(anchor.miniStory).map { "Mini-story: \($0)" },
            "Keeping this page checks in at the Anchor and adds \(AnchorRegistry.checkInBeliefReward) Belief to the place."
        ].compactMap { $0 }.joined(separator: "\n\n")

        return SurfacePage(
            id: "\(source.id)-\(anchor.id)-\(day.id)-\(Int(now.timeIntervalSince1970))",
            type: .anchor,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .loreLetter,
            score: min(96, 78 + max(0, 200 - Int(proximity.distanceMeters)) / 8 + anchor.visitCount),
            reason: "\(anchor.name) is within \(Int(proximity.distanceMeters.rounded()))m.",
            prompt: anchor.name,
            detail: "\(visitPhrase). \(anchor.kind.title) Anchor.",
            payload: BookPagePayload(
                headline: "Outer Stacks: \(anchor.name)",
                body: body,
                metadata: [
                    "source": source.id,
                    "anchorID": anchor.id,
                    "anchorName": anchor.name,
                    "anchorKind": anchor.kind.rawValue,
                    "distanceMeters": "\(Int(proximity.distanceMeters.rounded()))",
                    "radiusMeters": "\(Int(anchor.radiusMeters.rounded()))",
                    "visitMode": proximity.visitMode,
                    "nextVisitCount": "\(proximity.nextVisitCount)",
                    "seasonShift": season,
                    "beliefReward": "\(AnchorRegistry.checkInBeliefReward)",
                    "room": room,
                    "fae": anchor.fae,
                    "localRule": anchor.localRule,
                    "privacy": "location stays on device",
                    "tags": "anchor,outer-stacks,\(anchor.kind.rawValue.lowercased()),location"
                ]
            )
        )
    }

    private func nonEmpty(_ value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

struct AskTheBookPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .askTheBook)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        [
            SurfacePage(
                id: "\(source.id)-\(day.id)",
                type: .askTheBook,
                sourceID: source.id,
                intent: .reflect,
                renderStyle: .promptCard,
                score: 61,
                reason: "Ask plainly. The page will answer plainly.",
                prompt: "Ask the Book",
                detail: "Write one question. The Book will answer with a useful next step.",
                payload: BookPagePayload(
                    headline: "Ask the Book",
                    body: "Ask one real question. The answer should help you move.",
                    metadata: [
                        "source": source.id,
                        "privacy": "private local",
                        "tags": "ask-the-book,local-model,gemma,labyrinth"
                    ]
                )
            )
        ]
    }
}

struct HelpTipEntry: Equatable {
    var id: String
    var title: String
    var prompt: String
    var body: String
    var tags: [String]
}

enum HelpTipsCatalog {
    static let entries: [HelpTipEntry] = [
        HelpTipEntry(
            id: "first-five-minutes",
            title: "First Five Minutes",
            prompt: "Start small, keep one thing, then let the Book learn.",
            body: """
            Use the app like a living notebook, not a dashboard.

            1. Keep one tiny true thing. A Diary Page, Inner Weather note, Fuel Log, photo, or Souvenir all count.
            2. Do not wait for a grand moment. The Book is strongest when you feed it ordinary evidence.
            3. Open one rising page and answer only what feels finishable.
            4. If a page feels wrong today, dismiss it. Dismissed pages rest and may return later.
            5. Use the Glow menu when you want to steer what appears more often.

            Good first keeps:
            - "Coffee tasted burnt but useful."
            - "The window was blue before the room was."
            - "I am tired, but not erased."

            The trick: one kept page changes the day more than ten unopened perfect plans.
            """,
            tags: ["help", "onboarding", "basics", "keep-page"]
        ),
        HelpTipEntry(
            id: "glow-menu",
            title: "Using Glow",
            prompt: "Tune the Book by giving or taking Belief.",
            body: """
            Glow is the Book's attention budget.

            Give Belief when you want more of a page, character, source, or talisman. Take Belief when something is too loud, stale, or unhelpful. Low Glow does not delete anything; it just lowers its chance of surfacing.

            Good uses:
            - Give Belief to Story Pages when you want the world to move.
            - Give Belief to Body or Fuel when you want more care prompts.
            - Take Belief from Quips if you want fewer sparkle cards.
            - Give Belief to a Chapter Talisman if you want that Chapter's philosophy to tint the world.

            Tip: use Glow after you notice a pattern. If three pages in a row feel useful, warm that source. If three feel annoying, cool it.
            """,
            tags: ["help", "glow", "belief", "tuning"]
        ),
        HelpTipEntry(
            id: "story-gossip-letters",
            title: "Story, Gossip, and Letters",
            prompt: "Let the world move, then keep the pages that should count.",
            body: """
            Three page types move the Academy most visibly.

            Story Pages are playable scenes. They braid your day, current threads, characters, memories, and choices.

            Gossip Pages are simulation reports. They show what characters and entities did while you were elsewhere.

            Letter Pages are personal notes from characters. Some letters include research, memory, or a small world-state move.

            Important: when a generated page carries a real Belief delta, keeping the page commits it. This can include Chapter Talisman moves: a character may sometimes give Belief to their own talisman or try to take Belief from a rival Chapter's talisman.

            Tip: if a generated page matters, keep it. If it was only interesting, you can let it drift.
            """,
            tags: ["help", "story", "gossip", "letters", "talismans"]
        ),
        HelpTipEntry(
            id: "wonder-compass",
            title: "Wonder Compass Practice",
            prompt: "Use the compass directions as tiny real-world moves.",
            body: """
            The Compass is not homework. It is a tiny navigation tool.

            North = Notice. Look before you interpret.
            East = Embark. Take the smallest real step.
            South = Sense. Use your body and surroundings.
            West = Write. Keep one sentence or photo.
            Center = Rest. Stop before the practice becomes a burden.

            Playful Missions live mostly in South = Sense. They should be concrete, sensory, and finishable in under three minutes.

            Good mission rhythm:
            - Read the mission.
            - Do the smallest honest version.
            - Keep one proof sentence or photo.
            - Stop.

            Tip: a mission is successful when it makes you more present, not when it becomes impressive.
            """,
            tags: ["help", "wonder-compass", "missions", "sense"]
        ),
        HelpTipEntry(
            id: "photos-enchantments",
            title: "Photos and Enchantments",
            prompt: "Turn real images into illuminated evidence.",
            body: """
            Photos are proof that the world was there.

            Illuminated Photos let Penny and Gemma notice what is already inside an image: objects, light, mood, symbols, jokes, and possible souvenirs.

            Enchantments are more deliberate. Choose a spell, attach a real photo, and keep the result when the spell feels earned.

            Good photo subjects:
            - A room corner with personality.
            - A meal, mug, shoe, shelf, receipt, or doorway.
            - A weather detail.
            - A small object that keeps following you.

            Tip: blurry ordinary photos often work better than staged ones. The Book likes evidence more than performance.
            """,
            tags: ["help", "photos", "enchantments", "proof"]
        ),
        HelpTipEntry(
            id: "body-fuel-guild",
            title: "Body, Fuel, and the Support Guild",
            prompt: "Use care pages as context, not judgment.",
            body: """
            Body and Fuel pages are for patterns, not blame.

            Fuel Logs help Dr. Vellum notice timing, energy, and care. Inner Weather helps Dr. Inkrest compare mood, pressure, and context. Support Guild Pages synthesize the signals gently.

            Useful entries are plain:
            - "Bagel and coffee, 9 AM."
            - "Tired but less sharp after lunch."
            - "Foggy, not sad exactly."
            - "Headache, water helped a little."

            You do not need perfect tracking. A few honest notes are enough for better pages later.

            Tip: when a day is hard, choose the smallest care entry instead of a big explanation.
            """,
            tags: ["help", "body", "fuel", "support-guild", "care"]
        ),
        HelpTipEntry(
            id: "search-stacks",
            title: "Search the Stacks",
            prompt: "Ask the archive for pages, cast, memories, and references.",
            body: """
            Search is for finding your own continuity.

            Try searches like:
            - "pages about Morgan"
            - "photos of coffee"
            - "what did I keep when I was tired?"
            - "Small Glow characters"
            - "Wonder Compass rest"
            - "Penny letters"

            The Stacks can surface kept pages, cast members, anchors, memories, favors, and reference snippets.

            Tip: search works best with human words. Names, moods, page types, Glow tiers, places, and repeated objects are all good handles.
            """,
            tags: ["help", "search", "archive", "stacks"]
        ),
        HelpTipEntry(
            id: "anchors-outer-stacks",
            title: "Anchors and Outer Stacks",
            prompt: "Let real places become rooms when they earn it.",
            body: """
            Anchors are real places that the Labyrinth can recognize.

            When a known Anchor is nearby, an Outer Stacks page can open. The place stays real; the Book gives it a room-feeling, a rule, and a way to be entered through attention.

            Good anchors:
            - A porch, cafe, trailhead, library, parking lot, harbor, bench, or favorite aisle.
            - Somewhere repeatable.
            - Somewhere with a feeling you can name in a few words.

            Tip: name what the place holds, not just what it is. "The co-op" is useful. "The co-op, where errands become proof I still belong to town" is magic.
            """,
            tags: ["help", "anchors", "outer-stacks", "places"]
        ),
        HelpTipEntry(
            id: "page-packs-sources",
            title: "Sources, Packs, and Page Pressure",
            prompt: "Control what kinds of pages the Book offers.",
            body: """
            The Book chooses from active page sources.

            In the source and Glow menus, you can tune which pages appear more often. Installed Page Packs can add their own page types, rituals, games, utilities, and story materials.

            Practical tuning:
            - Want more story? Warm Story, Gossip, Letters, Cast, and Lore.
            - Want more grounding? Warm Body, Fuel, Weather, Rest, and Compass.
            - Want more reference? Warm Lore, Wonder Book, Help and Tips, and Packs.
            - Want a quieter shelf? Cool anything that feels noisy.

            Tip: the best shelf has variety. Do not max everything. Let the Book have a taste, then correct it when its taste gets annoying.
            """,
            tags: ["help", "sources", "packs", "curator", "glow"]
        ),
        HelpTipEntry(
            id: "privacy-local-brain",
            title: "Privacy and Local Brain",
            prompt: "Know what is private, generated, imported, or sensitive.",
            body: """
            Page sources carry privacy labels.

            Private Local pages belong on your device. Local Sensitive pages may include health, location, or personal context. Public Reference pages come from bundled or imported reference material.

            Gemma writes inside the local-brain flow when available. Some pages are templates, some are imported references, and some are generated from your kept context.

            Good habit:
            - Keep private pages honestly.
            - Use About You facts only when you are comfortable.
            - Treat health and location pages as context, not commands.
            - If a generated page overreaches, dismiss it and cool that source.

            Tip: the Book works better when it knows true things, but you decide which true things it gets to use.
            """,
            tags: ["help", "privacy", "local-brain", "gemma"]
        ),
        HelpTipEntry(
            id: "when-stuck",
            title: "When You Feel Stuck",
            prompt: "Use the smallest page that lowers friction.",
            body: """
            If the app feels like too much, shrink the move.

            Try one of these:
            - Keep an Inner Weather word.
            - Write one ordinary sentence.
            - Dismiss three pages without guilt.
            - Open Ask the Book and ask, "What is the smallest useful next step?"
            - Take a Center Page.
            - Keep a photo without explaining it.
            - Run one Playful Mission badly on purpose.

            The Book is not grading you. It is trying to keep you company while attention returns.

            Tip: a page can be useful even if it is not beautiful. Especially then.
            """,
            tags: ["help", "stuck", "rest", "small"]
        )
    ]

    static func entry(for day: BookDay, now: Date, manual: Bool = false) -> HelpTipEntry {
        let slot = SurfaceCadence.slotID(for: now, hours: manual ? 1 : 6)
        let index = stableIndex(for: "\(day.id)-help-tips-\(slot)-\(manual)", count: entries.count)
        return entries[index]
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

struct HelpTipsPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .helpTips)

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        helpSurface(entry: HelpTipsCatalog.entry(for: day, now: now, manual: true), context: context)
    }

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        return [helpSurface(entry: HelpTipsCatalog.entry(for: day, now: now), context: context)]
    }

    private func helpSurface(entry: HelpTipEntry, context: CuratorContext) -> SurfacePage {
        SurfacePage(
            id: "\(source.id)-\(entry.id)",
            type: .helpTips,
            sourceID: source.id,
            intent: .importReference,
            renderStyle: .loreLetter,
            score: context.distress.isActive ? 56 : 64,
            reason: context.distress.isActive ? "A practical tip can lower the shelf noise." : "The Book has a useful trick tucked into the help margin.",
            prompt: entry.prompt,
            detail: entry.title,
            payload: BookPagePayload(
                headline: entry.title,
                body: entry.body,
                metadata: [
                    "source": source.id,
                    "tipID": entry.id,
                    "privacy": "public reference",
                    "symbol": source.symbolName,
                    "tags": entry.tags.joined(separator: ",")
                ]
            )
        )
    }
}

enum BookPageSourceAdapters {
    static let active: [BookPageSourceAdapter] = [
        RestPageSourceAdapter(),
        MoodPageSourceAdapter(),
        DiaryPageSourceAdapter(),
        SouvenirPageSourceAdapter(),
        BookOfYouPageSourceAdapter(),
        BookRememberedPageSourceAdapter(),
        AskTheBookPageSourceAdapter(),
        BodyPageSourceAdapter(),
        FuelLogPageSourceAdapter(),
        FacultyResearchPageSourceAdapter(),
        CharacterLetterPageSourceAdapter(),
        SupportGuildPageSourceAdapter(),
        WeatherPageSourceAdapter(),
        EnchantmentPageSourceAdapter(),
        LabyrinthWelcomePageSourceAdapter(),
        AcademyClassPageSourceAdapter(),
        ElectivePageSourceAdapter(),
        PackPageSourceAdapter(),
        CalendarPageSourceAdapter(),
        QuipPageSourceAdapter(),
        AboutYouPageSourceAdapter(),
        WonderCompassPageSourceAdapter(),
        EnchantifyLorePageSourceAdapter(),
        HelpTipsPageSourceAdapter(),
        PatreonPageSourceAdapter(),
        LabyrinthIllustrationPageSourceAdapter(),
        IlluminatedPhotoPageSourceAdapter(),
        NarrativeOSPageSourceAdapter(),
        MarginsAtlasPageSourceAdapter(),
        GossipPageSourceAdapter(),
        CastMemberPageSourceAdapter(),
        OuterStacksAnchorPageSourceAdapter(),
        LocationPageSourceAdapter()
    ]

    static func adapter(for type: BookPageType) -> BookPageSourceAdapter? {
        active.first { $0.source.type == type }
    }

    static func manualSurface(
        for type: BookPageType,
        day: BookDay,
        context: CuratorContext,
        inputs: BookSourceInputs,
        now: Date
    ) -> SurfacePage {
        if let adapter = adapter(for: type) {
            return adapter.manualSurface(for: day, context: context, inputs: inputs, now: now)
        }
        let source = BookPageSourceRegistry.source(for: type)
        return SurfacePage(
            id: "manual-\(type.rawValue)-\(day.id)-\(Int(now.timeIntervalSince1970))",
            type: type,
            sourceID: source.id,
            intent: nil,
            renderStyle: .promptCard,
            score: 58,
            reason: "Opened directly from the Glow menu.",
            prompt: source.title,
            detail: source.note,
            payload: BookPagePayload(
                headline: source.title,
                body: source.note,
                metadata: [
                    "source": source.id,
                    "placeholder": "Write what this page needs to keep.",
                    "tags": "manual-page,\(type.rawValue)"
                ]
            )
        )
    }
}

struct PackPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .packPage)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive else { return [] }
        let hour = Calendar.current.component(.hour, from: now)
        return PageArchetypePackRegistry.archetypes().compactMap { archetype in
            if let activeHours = archetype.activeHours, !activeHours.contains(hour) {
                return nil
            }
            return surface(for: archetype, day: day, inputs: inputs, context: context, now: now)
        }
    }

    func manualSurface(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> SurfacePage {
        let archetypes = PageArchetypePackRegistry.archetypes()
        guard !archetypes.isEmpty else {
            return SurfacePage(
                id: "\(source.id)-empty-\(Int(now.timeIntervalSince1970))",
                type: .packPage,
                sourceID: source.id,
                prompt: "No Page Packs installed",
                detail: "Drop a \(PageArchetypePackRegistry.userPackFileSuffix) file into the app's Documents folder and its pages appear here.",
                payload: BookPagePayload(
                    headline: "Installed Page Packs",
                    body: "The shelf for installed Page Packs is empty beyond the bundled pages.",
                    metadata: ["source": source.id]
                )
            )
        }
        let slot = abs("\(day.id)-\(SurfaceCadence.slotID(for: now, hours: 2))-pack".stableHash)
        let archetype = archetypes[slot % archetypes.count]
        return surface(for: archetype, day: day, inputs: inputs, context: CuratorContext.make(for: day), now: now)
    }

    private func surface(
        for archetype: PageArchetype,
        day: BookDay,
        inputs: BookSourceInputs,
        context: CuratorContext,
        now: Date
    ) -> SurfacePage {
        var metadata: [String: String] = [
            "source": source.id,
            "packArchetypeID": archetype.id,
            "symbol": archetype.symbolName,
            "tags": (["pack-page", archetype.id] + archetype.tags).joined(separator: ",")
        ]
        if let generation = archetype.generation {
            metadata["packPrompt"] = PageTemplateRenderer.render(generation.promptTemplate, day: day, inputs: inputs, now: now)
            metadata["packInstructions"] = generation.instructions
            metadata["packMaxTokens"] = "\(generation.maxTokens)"
        }
        return SurfacePage(
            id: "\(source.id)-\(archetype.id)-\(SurfaceCadence.slotID(for: now, hours: archetype.cadenceHours))",
            type: .packPage,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: archetype.renderStyle,
            score: context.distress.isActive ? min(archetype.score, 44) : archetype.score,
            reason: archetype.reason,
            prompt: archetype.title,
            detail: archetype.detail,
            payload: BookPagePayload(
                headline: archetype.headline,
                body: PageTemplateRenderer.render(archetype.bodyTemplate, day: day, inputs: inputs, now: now),
                metadata: metadata
            )
        )
    }
}

struct CalendarPageSourceAdapter: BookPageSourceAdapter {
    let source = BookPageSourceRegistry.source(for: .calendar)

    func candidates(for day: BookDay, context: CuratorContext, inputs: BookSourceInputs, now: Date) -> [SurfacePage] {
        guard source.isActive, !inputs.calendarEvents.isEmpty else { return [] }
        var pages: [SurfacePage] = []
        let formatter = DateFormatter()
        formatter.timeStyle = .short

        // The Inked Hour: one folded corner per approaching event.
        for event in inputs.calendarEvents where !event.isAllDay {
            let minutes = Int(event.startsAt.timeIntervalSince(now) / 60)
            guard (0...45).contains(minutes) else { continue }
            let timeLabel = formatter.string(from: event.startsAt)
            pages.append(SurfacePage(
                id: "\(source.id)-hinge-\(event.id)",
                type: .calendar,
                sourceID: source.id,
                intent: .reflect,
                renderStyle: .promptCard,
                score: 86,
                reason: "A real hour is inked \(minutes) minute\(minutes == 1 ? "" : "s") from now.",
                prompt: "The Inked Hour: \(timeLabel)",
                detail: event.title,
                payload: BookPagePayload(
                    headline: "An Hour Approaches",
                    body: "Something is inked at \(timeLabel): \(event.title).\n\nThe Book folds a corner here so the hour doesn't ambush you. If there is one small thing to gather or set down before it arrives, this margin is for that.",
                    metadata: [
                        "source": source.id,
                        "eventTitle": event.title,
                        "eventTime": timeLabel,
                        "privacy": "calendar stays on device",
                        "tags": "calendar,hinge,real-day"
                    ]
                )
            ))
        }

        // Morning ledger of the day's hinges.
        let hour = Calendar.current.component(.hour, from: now)
        let todays = inputs.calendarEvents.filter {
            Calendar.current.isDate($0.startsAt, inSameDayAs: now) && !$0.isAllDay && $0.startsAt > now
        }
        if (6..<10).contains(hour), todays.count >= 1 {
            let lines = todays
                .sorted { $0.startsAt < $1.startsAt }
                .prefix(6)
                .map { "• \(formatter.string(from: $0.startsAt)) — \($0.title)" }
                .joined(separator: "\n")
            pages.append(SurfacePage(
                id: "\(source.id)-ledger-\(day.id)",
                type: .calendar,
                sourceID: source.id,
                intent: .reflect,
                renderStyle: .loreLetter,
                score: 70,
                reason: "The day already has \(todays.count) hinge\(todays.count == 1 ? "" : "s") inked.",
                prompt: "Today's Hinges",
                detail: "\(todays.count) inked hour\(todays.count == 1 ? "" : "s") ahead.",
                payload: BookPagePayload(
                    headline: "Today's Hinges",
                    body: "The day turns on these hours:\n\n\(lines)\n\nEverything between them is margin — yours.",
                    metadata: [
                        "source": source.id,
                        "privacy": "calendar stays on device",
                        "tags": "calendar,ledger,real-day"
                    ]
                )
            ))
        }
        return pages
    }
}
