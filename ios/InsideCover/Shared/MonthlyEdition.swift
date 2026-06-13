import Foundation

struct MonthlyEdition: Codable, Equatable {
    var title: String
    var subtitle: String
    var generatedAt: Date
    var startDate: Date
    var endDate: Date
    var dayCount: Int
    var pageCount: Int
    var readerName: String
    var chapterNumber: Int
    var monthName: String
    var theme: BookTheme?
    var constellations: [Constellation]
    var foreword: String
    var sections: [MonthlyEditionSection]
    var continuity: LiteraryContinuityDigest

    /// "The Book of You - bj - Chapter 3 - June"
    var chapterHeading: String {
        "The Book of You - \(readerName) - Chapter \(chapterNumber) - \(monthName)"
    }

    var isEmpty: Bool {
        pageCount == 0 && sections.allSatisfy(\.items.isEmpty)
    }
}

struct MonthlyEditionSection: Identifiable, Codable, Equatable {
    var id: String
    var title: String
    var note: String
    var items: [MonthlyEditionItem]
}

struct MonthlyEditionItem: Identifiable, Codable, Equatable {
    enum Kind: String, Codable, Equatable {
        case page
        case image
        case continuity
    }

    var id: String
    var kind: Kind
    var title: String
    var body: String
    var date: Date?
    var pageType: BookPageType?
    var sourceID: String?
    var mediaAssets: [BookPageMediaAsset]
    var tags: [String]
}

enum MonthlyEditionBuilder {
    static func previousMonth(
        from days: [BookDay],
        events: [NarrativeEvent] = [],
        entityMemories: [NarrativeEntityMemory] = [],
        entityBelief: [String: Int] = [:],
        pageBelief: [String: Int] = [:],
        constellations: [Constellation] = [],
        wagers: [BookWager] = [],
        themes: [BookTheme] = [],
        readerName: String = "friend",
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> MonthlyEdition {
        let currentMonthStart = calendar.date(from: calendar.dateComponents([.year, .month], from: now)) ?? calendar.startOfDay(for: now)
        let start = calendar.date(byAdding: .month, value: -1, to: currentMonthStart) ?? currentMonthStart
        let end = calendar.date(byAdding: .second, value: -1, to: currentMonthStart) ?? now
        return edition(
            from: days,
            events: events,
            entityMemories: entityMemories,
            entityBelief: entityBelief,
            pageBelief: pageBelief,
            constellations: constellations,
            wagers: wagers,
            themes: themes,
            readerName: readerName,
            startDate: start,
            endDate: end,
            generatedAt: now,
            calendar: calendar
        )
    }

    /// The annual: a whole year bound in one edition, foreword and all.
    static func year(
        _ year: Int,
        from days: [BookDay],
        events: [NarrativeEvent] = [],
        entityMemories: [NarrativeEntityMemory] = [],
        entityBelief: [String: Int] = [:],
        pageBelief: [String: Int] = [:],
        constellations: [Constellation] = [],
        wagers: [BookWager] = [],
        themes: [BookTheme] = [],
        readerName: String = "friend",
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> MonthlyEdition {
        let start = calendar.date(from: DateComponents(year: year, month: 1, day: 1)) ?? now
        let nextYear = calendar.date(from: DateComponents(year: year + 1, month: 1, day: 1)) ?? now
        let end = calendar.date(byAdding: .second, value: -1, to: nextYear) ?? now
        var annual = edition(
            from: days,
            events: events,
            entityMemories: entityMemories,
            entityBelief: entityBelief,
            pageBelief: pageBelief,
            constellations: constellations,
            wagers: wagers,
            themes: themes,
            readerName: readerName,
            startDate: start,
            endDate: end,
            generatedAt: now,
            calendar: calendar
        )
        annual.title = "Book of You: The \(year) Annual"
        return annual
    }

    static func edition(
        from days: [BookDay],
        events: [NarrativeEvent] = [],
        entityMemories: [NarrativeEntityMemory] = [],
        entityBelief: [String: Int] = [:],
        pageBelief: [String: Int] = [:],
        constellations: [Constellation] = [],
        wagers: [BookWager] = [],
        themes: [BookTheme] = [],
        readerName: String = "friend",
        startDate: Date,
        endDate: Date,
        generatedAt: Date = Date(),
        calendar: Calendar = .current
    ) -> MonthlyEdition {
        let monthDays = BookArchiveExport(days: days, calendar: calendar).days.filter { day in
            day.date >= calendar.startOfDay(for: startDate) && day.date <= calendar.startOfDay(for: endDate)
        }
        let pages = monthDays.flatMap(\.pages).sorted { $0.createdAt < $1.createdAt }
        let monthEvents = events.filter { $0.createdAt >= startDate && $0.createdAt <= endDate }
        let monthMemories = entityMemories.filter { $0.createdAt >= startDate && $0.createdAt <= endDate }
        let continuity = LiteraryContinuityProjector.digest(
            days: monthDays,
            events: monthEvents,
            entityMemories: monthMemories,
            entityBelief: entityBelief,
            pageBelief: pageBelief,
            now: generatedAt,
            calendar: calendar
        )

        let monthKey = BookThemeEngine.monthKey(for: startDate, calendar: calendar)
        let theme = BookThemeEngine.theme(forMonth: monthKey, in: themes)
            ?? BookThemeEngine.theme(
                for: pages,
                digest: continuity,
                constellations: constellations,
                monthKey: monthKey,
                now: generatedAt
            )
        let chapterNumber = chapterNumber(forMonthStarting: startDate, in: days, calendar: calendar)

        let title = "Book of You: \(monthTitle(for: startDate, calendar: calendar))"
        let subtitle = theme?.name ?? "\(dateLine(startDate, calendar: calendar)) - \(dateLine(endDate, calendar: calendar))"
        let sections = [
            themeSection(theme, pages: pages),
            openingSection(from: pages, continuity: continuity),
            pageSection(
                id: "daily-braids",
                title: "Daily Braids",
                note: "The Book of You pages that gathered the month into nightly thread.",
                pages: pages.filter { $0.type == .bookOfYou },
                limit: 31
            ),
            pageSection(
                id: "souvenirs",
                title: "One-Sentence Souvenirs",
                note: "Small bright fragments, preserved before the month could blur them.",
                pages: pages.filter { $0.type == .souvenir },
                limit: 40
            ),
            pageSection(
                id: "letters",
                title: "Letters And Voices",
                note: "Correspondence, gossip, story pages, and faculty notes that spoke back.",
                pages: pages.filter { [.letter, .narrativeOS, .bookConnections, .gossip, .facultyResearch, .supportGuild, .bookNotices].contains($0.type) },
                limit: 36
            ),
            imageSection(from: pages),
            pageSection(
                id: "other-kept-pages",
                title: "Other Kept Pages",
                note: "Weather, anchors, enchantments, classes, questions, and other margins worth binding.",
                pages: pages.filter { page in
                    ![.bookOfYou, .souvenir, .letter, .narrativeOS, .bookConnections, .gossip, .facultyResearch, .supportGuild, .bookNotices, .illuminatedPhoto, .illustration, .enchantment].contains(page.type)
                },
                limit: 48
            )
        ].filter { !$0.items.isEmpty }

        return MonthlyEdition(
            title: title,
            subtitle: subtitle,
            generatedAt: generatedAt,
            startDate: startDate,
            endDate: endDate,
            dayCount: monthDays.count,
            pageCount: pages.count,
            readerName: readerName,
            chapterNumber: chapterNumber,
            monthName: monthTitle(for: startDate, calendar: calendar),
            theme: theme,
            constellations: constellations,
            foreword: BookForewordWriter.foreword(
                monthTitle: monthTitle(for: startDate, calendar: calendar),
                pages: pages,
                dayCount: monthDays.count,
                continuity: continuity,
                constellations: constellations,
                wagers: wagers.filter { wager in
                    wager.sealedAt <= endDate && (wager.resolvedAt.map { $0 >= startDate } ?? true)
                },
                calendar: calendar
            ),
            sections: sections,
            continuity: continuity
        )
    }

    /// Chapter N = this month's position among all months that have kept
    /// pages, so the bound volumes read as a continuing book.
    private static func chapterNumber(forMonthStarting startDate: Date, in days: [BookDay], calendar: Calendar) -> Int {
        let editionKey = BookThemeEngine.monthKey(for: startDate, calendar: calendar)
        let monthKeys = Set(
            days.filter { !$0.pages.isEmpty }
                .map { BookThemeEngine.monthKey(for: $0.date, calendar: calendar) }
        )
        .union([editionKey])
        .sorted()
        return (monthKeys.firstIndex(of: editionKey) ?? 0) + 1
    }

    private static func themeSection(_ theme: BookTheme?, pages: [BookPage]) -> MonthlyEditionSection {
        guard let theme else {
            return MonthlyEditionSection(id: "the-months-theme", title: "The Month's Theme", note: "", items: [])
        }
        var items: [MonthlyEditionItem] = [
            MonthlyEditionItem(
                id: theme.id,
                kind: .continuity,
                title: theme.name,
                body: theme.line,
                date: nil,
                pageType: nil,
                sourceID: nil,
                mediaAssets: [],
                tags: ["theme"] + theme.motifs
            )
        ]
        for (index, excerpt) in theme.excerptLines.enumerated() {
            items.append(MonthlyEditionItem(
                id: "\(theme.id)-excerpt-\(index)",
                kind: .continuity,
                title: "From the pages",
                body: "\u{201C}\(excerpt)\u{201D}",
                date: nil,
                pageType: nil,
                sourceID: nil,
                mediaAssets: [],
                tags: ["theme-excerpt"]
            ))
        }
        return MonthlyEditionSection(
            id: "the-months-theme",
            title: "The Month's Theme",
            note: "One current the Book found running under the month, named and held up to the light.",
            items: items
        )
    }

    private static func openingSection(from pages: [BookPage], continuity: LiteraryContinuityDigest) -> MonthlyEditionSection {
        var items: [MonthlyEditionItem] = []
        let typeCounts = Dictionary(grouping: pages, by: \.type).mapValues(\.count)
        let strongest = typeCounts.sorted { left, right in
            if left.value == right.value { return left.key.title < right.key.title }
            return left.value > right.value
        }.prefix(5)
        if !strongest.isEmpty {
            items.append(MonthlyEditionItem(
                id: "month-shape",
                kind: .continuity,
                title: "Shape Of The Month",
                body: strongest.map { "\($0.key.title): \($0.value)" }.joined(separator: "\n"),
                date: nil,
                pageType: nil,
                sourceID: nil,
                mediaAssets: [],
                tags: ["monthly-edition", "shape"]
            ))
        }
        for signal in continuity.strongestSignals.prefix(8) {
            items.append(MonthlyEditionItem(
                id: signal.id,
                kind: .continuity,
                title: signal.subjectName,
                body: signal.line,
                date: signal.lastSeenAt,
                pageType: nil,
                sourceID: nil,
                mediaAssets: [],
                tags: signal.tags
            ))
        }
        return MonthlyEditionSection(
            id: "the-book-notices",
            title: "What The Book Noticed",
            note: "Connections, absences, durations, and living Beliefs gathered from the month.",
            items: items
        )
    }

    private static func pageSection(
        id: String,
        title: String,
        note: String,
        pages: [BookPage],
        limit: Int
    ) -> MonthlyEditionSection {
        MonthlyEditionSection(
            id: id,
            title: title,
            note: note,
            items: pages.prefix(limit).map(pageItem)
        )
    }

    private static func imageSection(from pages: [BookPage]) -> MonthlyEditionSection {
        let imagePages = pages.filter { page in
            page.type == .illuminatedPhoto || page.type == .illustration || page.type == .enchantment || !page.mediaAssets.isEmpty
        }
        return MonthlyEditionSection(
            id: "images",
            title: "Images And Illuminations",
            note: "Saved plates, enchantments, and image-bearing pages.",
            items: imagePages.prefix(28).map { page in
                var item = pageItem(page)
                item.kind = .image
                return item
            }
        )
    }

    private static func pageItem(_ page: BookPage) -> MonthlyEditionItem {
        MonthlyEditionItem(
            id: page.id,
            kind: page.mediaAssets.isEmpty ? .page : .image,
            title: page.type.title,
            body: pageBody(page),
            date: page.createdAt,
            pageType: page.type,
            sourceID: page.sourceID,
            mediaAssets: page.mediaAssets,
            tags: page.tags
        )
    }

    private static func pageBody(_ page: BookPage) -> String {
        let userInput = page.userInput.trimmingCharacters(in: .whitespacesAndNewlines)
        if !userInput.isEmpty { return userInput }
        return page.promptText.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func monthTitle(for date: Date, calendar: Calendar) -> String {
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "LLLL yyyy"
        return formatter.string(from: date)
    }

    private static func dateLine(_ date: Date, calendar: Calendar) -> String {
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.timeZone = calendar.timeZone
        formatter.dateStyle = .medium
        formatter.timeStyle = .none
        return formatter.string(from: date)
    }
}

/// The Book writes its own foreword: what it noticed, what it named, what it
/// wagered and how those wagers went. Deterministic prose - the same month
/// always gets the same foreword.
enum BookForewordWriter {
    static func foreword(
        monthTitle: String,
        pages: [BookPage],
        dayCount: Int,
        continuity: LiteraryContinuityDigest,
        constellations: [Constellation],
        wagers: [BookWager],
        calendar: Calendar = .current
    ) -> String {
        var paragraphs: [String] = []

        let pageLine = pages.count == 1 ? "one page" : "\(pages.count) pages"
        let dayLine = dayCount == 1 ? "a single day" : "\(dayCount) days"
        paragraphs.append("This is what \(monthTitle) left in my keeping: \(pageLine) across \(dayLine), each one kept on purpose. I do not bind months to flatter them. I bind them so they cannot quietly unhappen.")

        let signals = continuity.strongestSignals.prefix(3)
        if !signals.isEmpty {
            let lines = signals.map { signal in
                signal.line.hasSuffix(".") ? String(signal.line.dropLast()) : signal.line
            }
            paragraphs.append("Reading it back, I noticed things I did not notice at the time. \(lines.joined(separator: ". ")). None of this is a verdict; it is the shape attention left behind.")
        }

        let named = ConstellationKeeper.namedConstellations(constellations)
        if !named.isEmpty {
            let names = named.prefix(3).map(\.displayName)
            let nameLine: String
            switch names.count {
            case 1:
                nameLine = names[0]
            case 2:
                nameLine = "\(names[0]) and \(names[1])"
            default:
                nameLine = "\(names.dropLast().joined(separator: ", ")), and \(names.last ?? "")"
            }
            paragraphs.append("Some threads have been with us long enough that I have given them names: \(nameLine). A named constellation is a promise that I will keep watching, which is the only kind of promise a book can make.")
        }

        let opened = wagers.filter { !$0.isSealed }
        let sealed = wagers.filter(\.isSealed)
        if !opened.isEmpty {
            let right = opened.filter { $0.status == .right }.count
            let wrong = opened.count - right
            let scoreLine: String
            if wrong == 0 {
                scoreLine = "Every wager I opened this month came true, which I will try not to let go to my spine."
            } else if right == 0 {
                scoreLine = "Every wager I opened this month was wrong. I have written each one down anyway. Being wrong in writing is how a book learns."
            } else {
                scoreLine = "Of the wagers I opened this month, \(right) came true and \(wrong) did not. I record both with the same ink."
            }
            paragraphs.append(scoreLine)
        }
        if !sealed.isEmpty {
            paragraphs.append(sealed.count == 1
                ? "One wager is still sealed in the margins. We will both find out."
                : "\(sealed.count) wagers are still sealed in the margins. We will both find out.")
        }

        paragraphs.append("Whatever else this month was, it was read. - The Book")

        return paragraphs.joined(separator: "\n\n")
    }
}
