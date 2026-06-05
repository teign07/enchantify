import XCTest
@testable import InsideCoverCore

final class BookArchiveExportTests: XCTestCase {
    func testArchiveExportNormalizesMetadataAndSortOrder() throws {
        let export = BookArchiveExport(
            generatedAt: date(day: 4, hour: 12),
            days: [
                day(id: "wrong-later", day: 3, pageIDs: ["c", "b"]),
                day(id: "wrong-earlier", day: 1, pageIDs: ["a"])
            ],
            calendar: calendar
        )

        XCTAssertEqual(export.schemaVersion, BookArchiveExport.schemaVersion)
        XCTAssertEqual(export.dayCount, 2)
        XCTAssertEqual(export.pageCount, 3)
        XCTAssertEqual(export.days.map(\.id), ["2026-06-01", "2026-06-03"])
        XCTAssertEqual(export.days[1].pages.map(\.id), ["b", "c"])
    }

    func testArchiveExportRoundTripsThroughJSON() throws {
        let export = BookArchiveExport(
            generatedAt: date(day: 4, hour: 12),
            days: [day(id: "wrong", day: 2, pageIDs: ["a", "b"])],
            calendar: calendar
        )

        let decoded = try BookArchiveExport.decoded(from: try export.encodedData())

        XCTAssertEqual(decoded, export)
    }

    func testArchiveExportMergesDuplicateCalendarDaysBeforeBackup() throws {
        let export = BookArchiveExport(
            generatedAt: date(day: 4, hour: 12),
            days: [
                day(id: "wrong-a", day: 2, pageIDs: ["a"]),
                day(id: "wrong-b", day: 2, pageIDs: ["b"]),
                day(id: "wrong-c", day: 1, pageIDs: ["c"])
            ],
            calendar: calendar
        )

        XCTAssertEqual(export.days.map(\.id), ["2026-06-01", "2026-06-02"])
        XCTAssertEqual(export.days[0].pages.map(\.id), ["c"])
        XCTAssertEqual(export.days[1].pages.map(\.id), ["a", "b"])
        XCTAssertEqual(export.pageCount, 3)
    }

    private var calendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0) ?? .gmt
        return calendar
    }

    private func day(id: String, day: Int, pageIDs: [String]) -> BookDay {
        BookDay(
            id: id,
            date: date(day: day, hour: 9),
            pages: pageIDs.enumerated().map { offset, id in
                BookPage(
                    id: id,
                    type: .souvenir,
                    createdAt: date(day: day, hour: 12 - offset),
                    promptText: "Prompt \(id)",
                    userInput: "Page \(id)",
                    tags: ["export"],
                    sourceID: "one-sentence-souvenir"
                )
            }
        )
    }

    private func date(day: Int, hour: Int) -> Date {
        calendar.date(from: DateComponents(
            timeZone: calendar.timeZone,
            year: 2026,
            month: 6,
            day: day,
            hour: hour
        )) ?? Date()
    }
}
