import Foundation

enum LiterarySignalKind: String, Codable, Equatable, CaseIterable {
    case pattern
    case beliefLifecycle
    case absence
    case duration
}

struct LiteraryContinuitySignal: Identifiable, Codable, Equatable {
    var id: String
    var kind: LiterarySignalKind
    var subjectID: String
    var subjectName: String
    var line: String
    var evidencePageIDs: [String]
    var relatedEntityIDs: [String]
    var tags: [String]
    var firstSeenAt: Date
    var lastSeenAt: Date
    var strength: Int

    var promptLine: String {
        "\(subjectName): \(line)"
    }
}

struct BeliefLifecycleProfile: Identifiable, Codable, Equatable {
    var id: String
    var name: String
    var currentGlow: Int
    var firstSeenAt: Date
    var lastSeenAt: Date
    var pageCount: Int
    var eventCount: Int
    var characterCount: Int
    var evidencePageIDs: [String]
    var relatedEntityIDs: [String]

    var ageInDays: Int {
        max(1, Calendar.current.dateComponents([.day], from: Calendar.current.startOfDay(for: firstSeenAt), to: Calendar.current.startOfDay(for: Date())).day ?? 1)
    }
}

struct LiteraryContinuityDigest: Codable, Equatable {
    var signals: [LiteraryContinuitySignal]
    var beliefLifecycles: [BeliefLifecycleProfile]

    static let empty = LiteraryContinuityDigest(signals: [], beliefLifecycles: [])

    var strongestSignals: [LiteraryContinuitySignal] {
        signals.sorted { left, right in
            if left.strength == right.strength {
                return left.subjectName < right.subjectName
            }
            return left.strength > right.strength
        }
    }

    func signals(relatedTo page: BookPage, limit: Int = 3) -> [LiteraryContinuitySignal] {
        let pageWords = Self.meaningfulWords(in: "\(page.promptText) \(page.userInput) \(page.tags.joined(separator: " "))")
        return strongestSignals
            .filter { signal in
                !Set(signal.evidencePageIDs).isDisjoint(with: [page.id])
                    || !Set(signal.tags.map { $0.lowercased() }).isDisjoint(with: pageWords)
                    || pageWords.contains(signal.subjectName.lowercased())
            }
            .prefix(limit)
            .map(\.self)
    }

    private static func meaningfulWords(in text: String) -> Set<String> {
        LiteraryContinuityProjector.meaningfulWords(in: text)
    }
}

enum LiteraryContinuityProjector {
    static func digest(
        days: [BookDay],
        events: [NarrativeEvent],
        entityMemories: [NarrativeEntityMemory],
        entityBelief: [String: Int] = [:],
        pageBelief: [String: Int] = [:],
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> LiteraryContinuityDigest {
        let pages = days.flatMap(\.pages).sorted { $0.createdAt < $1.createdAt }
        guard !pages.isEmpty || !events.isEmpty || !entityMemories.isEmpty else {
            return .empty
        }
        let lifecycles = beliefLifecycles(
            pages: pages,
            events: events,
            entityMemories: entityMemories,
            entityBelief: entityBelief,
            pageBelief: pageBelief
        )
        let signals = patternSignals(pages: pages, events: events, now: now, calendar: calendar)
            + absenceSignals(pages: pages, events: events, now: now, calendar: calendar)
            + durationSignals(pages: pages, lifecycles: lifecycles, now: now, calendar: calendar)
            + lifecycles.prefix(4).map { lifecycleSignal($0, now: now, calendar: calendar) }

        return LiteraryContinuityDigest(
            signals: Array(signals.sorted { left, right in
                if left.strength == right.strength {
                    return left.subjectName < right.subjectName
                }
                return left.strength > right.strength
            }.prefix(16)),
            beliefLifecycles: lifecycles
        )
    }

    static func meaningfulWords(in text: String) -> Set<String> {
        return Set(text
            .lowercased()
            .split { !$0.isLetter && !$0.isNumber }
            .map(String.init)
            .filter(isLiteraryCandidate)
        )
    }

    static let stopWords: Set<String> = [
        "about", "after", "again", "almost", "already", "also", "always", "another",
        "around", "because", "been", "before", "being", "between", "book", "both", "came",
        "come", "could", "does", "doing", "done", "down", "during", "each", "even", "every",
        "feel", "feeling", "felt", "first", "from", "going", "gone", "good", "have", "here",
        "into", "just", "kept", "last", "like", "little", "made", "make", "many", "might",
        "more", "most", "much", "never", "next", "only", "other", "over", "page", "pages",
        "really", "same", "should", "small", "some", "something", "still",
        "than", "that", "their", "them", "then", "there", "these", "they", "thing", "things",
        "this", "those", "through", "time", "today", "tomorrow", "tonight", "under", "until",
        "very", "want", "wanted", "week", "well", "went", "were", "what", "when", "where",
        "which", "while", "will", "with", "without", "would", "year", "yesterday", "your", "you",
        "january", "february", "march", "april", "june", "july", "august", "september",
        "october", "november", "december", "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday", "morning", "evening", "night", "afternoon"
    ]

    /// Words can be meaningful to a parser while still being poor literary
    /// subjects. This list keeps the Book from naming scaffolding, generic
    /// motion, and emotional weather so vague it becomes accidental.
    static let weakLiterarySubjects: Set<String> = [
        "able", "above", "actually", "along", "anything", "away", "became", "begin",
        "began", "behind", "better", "blank", "called", "cannot", "change", "changed",
        "chapter", "class", "close", "closed", "climax", "coming", "current", "different",
        "early", "empty", "enough", "face", "fall", "fallen", "falling", "fell", "flat",
        "found", "front", "gave", "given", "gets", "getting", "half", "hard", "having",
        "held", "inside", "kind", "knew", "know", "later", "left", "less", "line",
        "lines", "long", "look", "looked", "looking", "lost", "maybe", "moment",
        "near", "needed", "open", "opened", "outside", "part", "past", "place",
        "point", "quietly", "read", "ready", "right", "room", "said", "saw", "scene",
        "second", "seen", "seems", "self", "side", "started", "story", "sure", "take",
        "taken", "takes", "tell", "thread", "told", "took", "toward", "trying", "turn",
        "turned", "used", "using", "voice", "whole", "work", "world"
    ]

    static func isLiteraryCandidate(_ word: String) -> Bool {
        word.count >= 4
            && !stopWords.contains(word)
            && !weakLiterarySubjects.contains(word)
            && !word.contains(where: \.isNumber)
    }

    /// Words that appear in a large share of all pages are the reader's
    /// ambient vocabulary, not a pattern - "academy" in a play archive,
    /// "meeting" in a work one. The damping is per-reader and automatic.
    /// Small archives skip it, so a young Book can still get excited about
    /// three mentions of the harbor in its first week.
    static let ubiquityMinimumPages = 12
    static let ubiquityCeiling = 0.34

    /// nil means the word is ambient vocabulary and should be no signal at
    /// all; otherwise the penalty scales with how common the word is.
    static func ubiquityPenalty(pageHits: Int, totalPages: Int) -> Int? {
        guard totalPages >= ubiquityMinimumPages else { return 0 }
        let ratio = Double(pageHits) / Double(totalPages)
        guard ratio <= ubiquityCeiling else { return nil }
        return Int(ratio * 60)
    }

    /// Diminishing returns past the first handful of pages, so strength
    /// discriminates between "appears sometimes" and "appears constantly"
    /// instead of every common word pinning the cap.
    static func patternStrength(pageCount: Int, eventBoost: Int, penalty: Int) -> Int {
        let early = 7 * min(pageCount, 5)
        let late = 2 * min(max(pageCount - 5, 0), 12)
        return min(94, max(1, 38 + early + late + eventBoost - penalty))
    }

    private static func patternSignals(
        pages: [BookPage],
        events: [NarrativeEvent],
        now: Date,
        calendar: Calendar
    ) -> [LiteraryContinuitySignal] {
        var buckets: [String: [BookPage]] = [:]
        for page in pages {
            let text = "\(page.promptText) \(page.userInput) \(page.tags.joined(separator: " "))"
            for word in meaningfulWords(in: text) {
                buckets[word, default: []].append(page)
            }
        }
        let eventText = events.prefix(80).map { "\($0.summary) \($0.tags.joined(separator: " "))" }.joined(separator: " ")
        let eventWords = meaningfulWords(in: eventText)
        let totalPages = pages.count
        return buckets.compactMap { word, matches in
            let uniquePages = unique(matches)
            guard uniquePages.count >= 3 else { return nil }
            guard let penalty = ubiquityPenalty(pageHits: uniquePages.count, totalPages: totalPages) else { return nil }
            let first = uniquePages.first?.createdAt ?? now
            let last = uniquePages.last?.createdAt ?? now
            let countLine = uniquePages.count == 3 ? "three kept pages" : "\(uniquePages.count) kept pages"
            let eventLine = eventWords.contains(word) ? " and it is still moving in recent events" : ""
            return LiteraryContinuitySignal(
                id: "pattern-\(word)",
                kind: .pattern,
                subjectID: word,
                subjectName: word.capitalized,
                line: "The word \(word) has gathered across \(countLine)\(eventLine).",
                evidencePageIDs: uniquePages.prefix(8).map(\.id),
                relatedEntityIDs: [],
                tags: [word, "pattern", "literary-continuity"],
                firstSeenAt: first,
                lastSeenAt: last,
                strength: patternStrength(pageCount: uniquePages.count, eventBoost: eventWords.contains(word) ? 10 : 0, penalty: penalty)
            )
        }
    }

    private static func absenceSignals(
        pages: [BookPage],
        events: [NarrativeEvent],
        now: Date,
        calendar: Calendar
    ) -> [LiteraryContinuitySignal] {
        let historyCutoff = calendar.date(byAdding: .day, value: -21, to: now) ?? now
        let olderPages = pages.filter { $0.createdAt < historyCutoff }
        guard olderPages.count >= 3 else { return [] }
        var buckets: [String: [BookPage]] = [:]
        for page in olderPages {
            let text = "\(page.promptText) \(page.userInput) \(page.tags.joined(separator: " "))"
            for word in meaningfulWords(in: text) {
                buckets[word, default: []].append(page)
            }
        }
        let recentText = pages
            .filter { $0.createdAt >= historyCutoff }
            .map { "\($0.promptText) \($0.userInput) \($0.tags.joined(separator: " "))" }
            .joined(separator: " ")
        let recentWords = meaningfulWords(in: recentText)
        return buckets.compactMap { word, matches in
            let uniquePages = unique(matches)
            guard uniquePages.count >= 3, !recentWords.contains(word), let last = uniquePages.last?.createdAt else {
                return nil
            }
            guard let penalty = ubiquityPenalty(pageHits: uniquePages.count, totalPages: olderPages.count) else { return nil }
            let quietDays = max(21, calendar.dateComponents([.day], from: calendar.startOfDay(for: last), to: calendar.startOfDay(for: now)).day ?? 21)
            return LiteraryContinuitySignal(
                id: "absence-\(word)",
                kind: .absence,
                subjectID: word,
                subjectName: word.capitalized,
                line: "\(word.capitalized) used to appear often; it has been quiet for \(quietDays) days.",
                evidencePageIDs: uniquePages.suffix(6).map(\.id),
                relatedEntityIDs: [],
                tags: [word, "absence", "literary-continuity"],
                firstSeenAt: uniquePages.first?.createdAt ?? last,
                lastSeenAt: last,
                strength: min(94, 34 + uniquePages.count * 7 + min(20, quietDays / 3) - penalty)
            )
        }
    }

    private static func durationSignals(
        pages: [BookPage],
        lifecycles: [BeliefLifecycleProfile],
        now: Date,
        calendar: Calendar
    ) -> [LiteraryContinuitySignal] {
        var signals: [LiteraryContinuitySignal] = []
        if let oldest = pages.first {
            let days = max(1, calendar.dateComponents([.day], from: calendar.startOfDay(for: oldest.createdAt), to: calendar.startOfDay(for: now)).day ?? 1)
            if days >= 30 {
                signals.append(LiteraryContinuitySignal(
                    id: "duration-book-\(oldest.id)",
                    kind: .duration,
                    subjectID: "book",
                    subjectName: "The Book",
                    line: "The oldest kept page has been in the Book for \(days) days.",
                    evidencePageIDs: [oldest.id],
                    relatedEntityIDs: [],
                    tags: ["duration", "archive", "literary-continuity"],
                    firstSeenAt: oldest.createdAt,
                    lastSeenAt: now,
                    strength: min(88, 40 + days / 14)
                ))
            }
        }
        for lifecycle in lifecycles.prefix(3) {
            let days = max(1, calendar.dateComponents([.day], from: calendar.startOfDay(for: lifecycle.firstSeenAt), to: calendar.startOfDay(for: now)).day ?? 1)
            guard days >= 14 else { continue }
            signals.append(LiteraryContinuitySignal(
                id: "duration-belief-\(lifecycle.id)",
                kind: .duration,
                subjectID: lifecycle.id,
                subjectName: lifecycle.name,
                line: "\(lifecycle.name) has been in the margins for \(days) days.",
                evidencePageIDs: lifecycle.evidencePageIDs,
                relatedEntityIDs: lifecycle.relatedEntityIDs,
                tags: ["duration", "belief", "literary-continuity", lifecycle.id],
                firstSeenAt: lifecycle.firstSeenAt,
                lastSeenAt: lifecycle.lastSeenAt,
                strength: min(90, 36 + days / 10 + lifecycle.pageCount * 3)
            ))
        }
        return signals
    }

    private static func beliefLifecycles(
        pages: [BookPage],
        events: [NarrativeEvent],
        entityMemories: [NarrativeEntityMemory],
        entityBelief: [String: Int],
        pageBelief: [String: Int]
    ) -> [BeliefLifecycleProfile] {
        let entities = NarrativePackRegistry.entities
        var profiles: [BeliefLifecycleProfile] = []

        for entity in entities where entity.kind == .character || entity.kind == .motif || entity.kind == .talisman {
            let pageHits = pages.filter { page in
                let text = "\(page.promptText) \(page.userInput) \(page.tags.joined(separator: " "))".lowercased()
                return text.contains(entity.id.lowercased()) || text.contains(entity.name.lowercased())
            }
            let eventHits = events.filter { event in
                event.effect.entityWeightDeltas.keys.contains(entity.id)
                    || event.summary.lowercased().contains(entity.name.lowercased())
                    || event.tags.contains(entity.id)
            }
            let memoryHits = entityMemories.filter { $0.entityID == entity.id }
            guard pageHits.count + eventHits.count + memoryHits.count > 0 else { continue }
            let dates = pageHits.map(\.createdAt) + eventHits.map(\.createdAt) + memoryHits.map(\.createdAt)
            profiles.append(BeliefLifecycleProfile(
                id: entity.id,
                name: entity.name,
                currentGlow: max(0, min(100, entity.belief + (entityBelief[entity.id] ?? 0))),
                firstSeenAt: dates.min() ?? Date(),
                lastSeenAt: dates.max() ?? Date(),
                pageCount: pageHits.count,
                eventCount: eventHits.count,
                characterCount: entity.kind == .character ? 1 : 0,
                evidencePageIDs: Array(pageHits.prefix(8).map(\.id)),
                relatedEntityIDs: [entity.id]
            ))
        }

        for profile in BookPageSourceRegistry.beliefProfiles(ledger: pageBelief) {
            let pageHits = pages.filter { $0.sourceID == profile.sourceID || $0.type == profile.type }
            let eventHits = events.filter { $0.sourcePageType == profile.type || $0.tags.contains(profile.sourceID) }
            guard pageHits.count + eventHits.count > 0 else { continue }
            let dates = pageHits.map(\.createdAt) + eventHits.map(\.createdAt)
            profiles.append(BeliefLifecycleProfile(
                id: profile.sourceID,
                name: profile.title,
                currentGlow: profile.belief,
                firstSeenAt: dates.min() ?? Date(),
                lastSeenAt: dates.max() ?? Date(),
                pageCount: pageHits.count,
                eventCount: eventHits.count,
                characterCount: 0,
                evidencePageIDs: Array(pageHits.prefix(8).map(\.id)),
                relatedEntityIDs: []
            ))
        }

        return profiles.sorted { left, right in
            let leftScore = left.pageCount * 8 + left.eventCount * 5 + left.currentGlow
            let rightScore = right.pageCount * 8 + right.eventCount * 5 + right.currentGlow
            if leftScore == rightScore {
                return left.name < right.name
            }
            return leftScore > rightScore
        }
    }

    private static func lifecycleSignal(
        _ lifecycle: BeliefLifecycleProfile,
        now: Date,
        calendar: Calendar
    ) -> LiteraryContinuitySignal {
        let appearances = lifecycle.pageCount == 1 ? "one kept page" : "\(lifecycle.pageCount) kept pages"
        return LiteraryContinuitySignal(
            id: "belief-lifecycle-\(lifecycle.id)",
            kind: .beliefLifecycle,
            subjectID: lifecycle.id,
            subjectName: lifecycle.name,
            line: "\(lifecycle.name) has become a living thread: \(appearances), \(lifecycle.eventCount) events, current Glow \(lifecycle.currentGlow).",
            evidencePageIDs: lifecycle.evidencePageIDs,
            relatedEntityIDs: lifecycle.relatedEntityIDs,
            tags: ["belief", "lifecycle", "literary-continuity", lifecycle.id],
            firstSeenAt: lifecycle.firstSeenAt,
            lastSeenAt: lifecycle.lastSeenAt,
            strength: min(96, 32 + lifecycle.currentGlow / 2 + lifecycle.pageCount * 4 + lifecycle.eventCount * 2)
        )
    }

    private static func unique(_ pages: [BookPage]) -> [BookPage] {
        var seen: Set<String> = []
        return pages.filter { page in
            if seen.contains(page.id) { return false }
            seen.insert(page.id)
            return true
        }
    }
}

// MARK: - Themes
//
// A theme is the month's weather system: two or three motifs that kept
// gathering until they deserve a shared name. Themes are discovered from
// kept pages and the continuity digest, remembered across months, and used
// as chapter subtitles, theme pages, and margin material. Like everything
// else in the Book, a theme is a literary observation, never a verdict.

struct BookTheme: Identifiable, Codable, Equatable {
    var id: String
    var monthKey: String
    var name: String
    var motifs: [String]
    var line: String
    var strength: Int
    var evidencePageIDs: [String]
    var excerptLines: [String]
    var discoveredAt: Date

    var promptLine: String {
        "This month's theme: \(name). \(line)"
    }
}

enum BookThemeEngine {
    /// Words too structural to be a theme, on top of the continuity stop list.
    private static let themeStop: Set<String> = [
        "today", "yesterday", "tomorrow", "morning", "evening", "night",
        "really", "very", "little", "small", "around", "still", "going",
        "started", "finished", "thing", "things", "while", "after", "before",
        "first", "last", "back", "down", "over", "made", "make", "want",
        "wanted", "good", "nice", "time", "felt", "feel", "feeling", "went"
    ]

    /// Discovers the theme of a span of days. Deterministic for the same
    /// pages, digest, and month key.
    static func theme(
        for pages: [BookPage],
        digest: LiteraryContinuityDigest,
        constellations: [Constellation] = [],
        monthKey: String,
        now: Date = Date()
    ) -> BookTheme? {
        var weights: [String: Int] = [:]
        var evidence: [String: [String]] = [:]

        for page in pages {
            let text = "\(page.promptText) \(page.userInput) \(page.tags.joined(separator: " "))"
            for word in LiteraryContinuityProjector.meaningfulWords(in: text) where !themeStop.contains(word) {
                weights[word, default: 0] += 2
                if evidence[word, default: []].count < 8, !evidence[word, default: []].contains(page.id) {
                    evidence[word, default: []].append(page.id)
                }
            }
        }
        // Ambient vocabulary makes a dull theme; drop words on most pages.
        for (word, hits) in evidence where LiteraryContinuityProjector.ubiquityPenalty(pageHits: hits.count, totalPages: pages.count) == nil {
            weights.removeValue(forKey: word)
        }
        for signal in digest.signals {
            let subject = signal.subjectID.lowercased()
            guard !themeStop.contains(subject), subject.count >= 4 else { continue }
            weights[subject, default: 0] += signal.strength / 10
        }
        for constellation in constellations where constellation.isAlive {
            let subject = constellation.subjectID.lowercased()
            guard !themeStop.contains(subject), subject.count >= 4 else { continue }
            weights[subject, default: 0] += 6
        }

        let ranked = weights
            .filter { $0.value >= 4 && evidence[$0.key, default: []].count >= 2 }
            .sorted { left, right in
                if left.value == right.value { return left.key < right.key }
                return left.value > right.value
            }
        guard ranked.count >= 2 else { return nil }

        let motifs = Array(ranked.prefix(3).map(\.key))
        let primary = motifs[0]
        let secondary = motifs[1]
        let name = themeName(primary: primary, secondary: secondary, seed: "\(monthKey)-\(primary)-\(secondary)")
        let strength = min(100, ranked[0].1 * 3 + ranked[1].1 * 2)
        let evidenceIDs = Array(Set(motifs.flatMap { evidence[$0] ?? [] })).sorted()
        let excerpts = excerptLines(for: motifs, in: pages)

        return BookTheme(
            id: "theme-\(monthKey)",
            monthKey: monthKey,
            name: name,
            motifs: motifs,
            line: themeLine(motifs: motifs, seed: "\(monthKey)-line"),
            strength: strength,
            evidencePageIDs: evidenceIDs,
            excerptLines: excerpts,
            discoveredAt: now
        )
    }

    /// Upserts the current month's theme into the remembered ledger. Old
    /// months keep their themes forever; only the live month is rewritten.
    static func remembered(
        _ existing: [BookTheme],
        observing current: BookTheme?,
        monthKey: String
    ) -> [BookTheme] {
        var kept = existing.filter { $0.monthKey != monthKey }
        if let current {
            kept.append(current)
        }
        return kept.sorted { $0.monthKey < $1.monthKey }
    }

    static func theme(forMonth monthKey: String, in themes: [BookTheme]) -> BookTheme? {
        themes.first { $0.monthKey == monthKey }
    }

    static func monthKey(for date: Date, calendar: Calendar = .current) -> String {
        let components = calendar.dateComponents([.year, .month], from: date)
        return String(format: "%04d-%02d", components.year ?? 0, components.month ?? 0)
    }

    /// "Secrets and Harbors" - two motifs joined by a deterministic pattern.
    static func themeName(primary: String, secondary: String, seed: String) -> String {
        let first = poeticized(primary)
        let second = poeticized(secondary)
        let patterns = [
            "%@ and %@",
            "%@ and %@",
            "Of %@ and %@",
            "%@, Then %@",
            "What %@ Said to %@"
        ]
        let pattern = patterns[ConstellationKeeper.stableIndex(for: "\(seed)-pattern", count: patterns.count)]
        return String(format: pattern, first, second)
    }

    private static func themeLine(motifs: [String], seed: String) -> String {
        let listed: String
        switch motifs.count {
        case 0, 1:
            listed = motifs.first.map(poeticized) ?? "the ordinary"
        case 2:
            listed = "\(poeticized(motifs[0])) and \(poeticized(motifs[1]))"
        default:
            listed = "\(poeticized(motifs[0])), \(poeticized(motifs[1])), and \(poeticized(motifs[2]))"
        }
        let templates = [
            "The pages kept returning to %@, the way a reader rereads a favorite paragraph without deciding to.",
            "%@ ran under the month like a watermark - visible whenever a page was held up to the light.",
            "If this month were a chapter, its running heads would say %@.",
            "The margins filled with %@ before anyone thought to call it a theme."
        ]
        let template = templates[ConstellationKeeper.stableIndex(for: seed, count: templates.count)]
        return String(format: template, listed)
    }

    private static func poeticized(_ word: String) -> String {
        word.prefix(1).uppercased() + word.dropFirst()
    }

    private static func excerptLines(for motifs: [String], in pages: [BookPage]) -> [String] {
        var excerpts: [String] = []
        for motif in motifs {
            guard let page = pages.first(where: { page in
                page.userInput.lowercased().contains(motif) && page.userInput.count >= 16
            }) else { continue }
            var line = page.userInput.bookPreviewSentenceLimit(1).trimmingCharacters(in: .whitespacesAndNewlines)
            if line.count > 110 {
                line = String(line.prefix(107)) + "..."
            }
            if !excerpts.contains(line) {
                excerpts.append(line)
            }
            if excerpts.count >= 3 { break }
        }
        return excerpts
    }
}
