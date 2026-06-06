import XCTest
@testable import InsideCoverCore

final class BraidRecoveryStateTests: XCTestCase {
    func testFailureWithCapturedFragmentsEnablesRetryAndRecordsError() {
        var recovery = BraidRecoveryState()

        recovery.recordFailure("model unavailable", day: dayWithCapturedFragments())

        XCTAssertTrue(recovery.canRetry)
        XCTAssertEqual(recovery.retryActionTitle, "Try again")
        XCTAssertEqual(recovery.lastError, "model unavailable")
    }

    func testFailureWithoutCapturedFragmentsDoesNotEnableRetry() {
        var recovery = BraidRecoveryState()

        recovery.recordFailure("model unavailable", day: BookDay(id: "empty-day", date: Date(), pages: []))

        XCTAssertFalse(recovery.canRetry)
        XCTAssertNil(recovery.retryActionTitle)
        XCTAssertNil(recovery.lastError)
    }

    func testFailureAfterBookOfYouAlreadyExistsDoesNotEnableRetry() {
        var recovery = BraidRecoveryState()
        var day = dayWithCapturedFragments()
        day.pages.append(bookOfYouPage())

        recovery.recordFailure("model unavailable", day: day)

        XCTAssertFalse(recovery.canRetry)
        XCTAssertNil(recovery.retryActionTitle)
        XCTAssertNil(recovery.lastError)
    }

    func testBeginAttemptClearsRetryButKeepsLastErrorVisible() {
        var recovery = BraidRecoveryState()
        recovery.recordFailure("model unavailable", day: dayWithCapturedFragments())

        recovery.beginAttempt()

        XCTAssertFalse(recovery.canRetry)
        XCTAssertNil(recovery.retryActionTitle)
        XCTAssertEqual(recovery.lastError, "model unavailable")
    }

    func testSuccessClearsRetryAndError() {
        var recovery = BraidRecoveryState()
        recovery.recordFailure("model unavailable", day: dayWithCapturedFragments())

        recovery.recordSuccess()

        XCTAssertFalse(recovery.canRetry)
        XCTAssertNil(recovery.retryActionTitle)
        XCTAssertNil(recovery.lastError)
    }

    func testDayByMarkingCapturedPagesUsedMarksOnlyCapturedPagesAndAppendsBraid() throws {
        let originalDay = BookDay(
            id: "2026-06-06",
            date: Date(),
            pages: [
                page(id: "souvenir", type: .souvenir, usedInBookOfYou: false),
                page(id: "already-braided", type: .mood, usedInBookOfYou: true),
                bookOfYouPage()
            ]
        )
        let braid = bookOfYouPage(id: "fresh-braid")

        let updatedDay = BraidRecoveryState.dayByMarkingCapturedPagesUsed(originalDay, braid: braid)

        XCTAssertEqual(updatedDay.pages.count, 4)
        XCTAssertTrue(try XCTUnwrap(updatedDay.pages.first { $0.id == "souvenir" }).usedInBookOfYou)
        XCTAssertTrue(try XCTUnwrap(updatedDay.pages.first { $0.id == "already-braided" }).usedInBookOfYou)
        XCTAssertFalse(try XCTUnwrap(updatedDay.pages.first { $0.id == "book-of-you" }).usedInBookOfYou)
        XCTAssertEqual(updatedDay.pages.last?.id, "fresh-braid")
    }

    private func dayWithCapturedFragments() -> BookDay {
        BookDay(
            id: "2026-06-06",
            date: Date(),
            pages: [
                page(id: "souvenir", type: .souvenir, usedInBookOfYou: false)
            ]
        )
    }

    private func page(id: String, type: BookPageType, usedInBookOfYou: Bool) -> BookPage {
        BookPage(
            id: id,
            type: type,
            createdAt: Date(),
            promptText: "Prompt",
            userInput: "A true fragment.",
            tags: [],
            usedInBookOfYou: usedInBookOfYou
        )
    }

    private func bookOfYouPage(id: String = "book-of-you") -> BookPage {
        page(id: id, type: .bookOfYou, usedInBookOfYou: false)
    }
}
