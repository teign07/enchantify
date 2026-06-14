import XCTest
@testable import InsideCoverCore

final class FaeBargainTests: XCTestCase {
    private let slot = "2026-06-13-fae"

    func testOfferFrontsAWorkingGiftAndOwedDebt() {
        var state = FaePlayerState()
        let now = Date()
        let bargain = FaeEconomy.offerBargain(into: &state, kind: .sentenceSalamander, slot: slot, now: now)
        XCTAssertEqual(bargain.status, .owed)
        XCTAssertEqual(state.bargains.count, 1)
        XCTAssertEqual(state.gifts.count, 1)
        let gift = state.gifts.first
        XCTAssertEqual(gift?.isCold, false)
        XCTAssertEqual(gift?.isActive, true, "a fronted gift works immediately")
        XCTAssertNotNil(state.lastBargainOfferedAt)
        XCTAssertEqual(bargain.deadline.timeIntervalSince(now),
                       Double(FaeEconomy.paymentWindowHours) * 3_600,
                       accuracy: 1)
    }

    func testOnlyOneOpenBargainAtATime() {
        var state = FaePlayerState()
        FaeEconomy.offerBargain(into: &state, kind: .goblin, slot: slot, now: Date())
        XCTAssertFalse(FaeEconomy.canOfferBargain(state: state, now: Date()))
    }

    func testLapseColdsGiftAndClosesMarket() {
        var state = FaePlayerState()
        let offered = Date().addingTimeInterval(-Double(FaeEconomy.paymentWindowHours + 1) * 3_600)
        FaeEconomy.offerBargain(into: &state, kind: .punctuationPixie, slot: slot, now: offered)
        let lapsed = FaeEconomy.sweepLapses(into: &state, now: Date())
        XCTAssertEqual(lapsed.count, 1)
        XCTAssertEqual(state.bargains.first?.status, .lapsed)
        XCTAssertEqual(state.gifts.first?.isCold, true)
        XCTAssertFalse(state.gifts.first?.isActive ?? true, "a cold gift stops working — real stakes")
        XCTAssertTrue(state.marketIsClosed(for: .punctuationPixie))
        XCTAssertEqual(state.warmth(for: .punctuationPixie), -FaeEconomy.warmthPerLapse)
    }

    func testDeliveryPaysWarmthAndAttention() {
        var state = FaePlayerState()
        let bargain = FaeEconomy.offerBargain(into: &state, kind: .literaryElf, slot: slot, now: Date())
        FaeEconomy.deliver(
            bargainID: bargain.id,
            report: "The brass tap over the sink, worn pale where a thousand thumbs have pushed it, still drips at a count of nine.",
            faeResponse: "Again— no. Kept.",
            reward: "A word that means the pause before a true sentence.",
            into: &state
        )
        XCTAssertEqual(state.bargains.first?.status, .delivered)
        XCTAssertEqual(state.warmth(for: .literaryElf), FaeEconomy.warmthPerDelivery)
        XCTAssertGreaterThan(state.attention, 0)
        XCTAssertEqual(state.openBargains.count, 0)
    }

    func testRepairThawsGiftAndReopensMarket() {
        var state = FaePlayerState()
        let offered = Date().addingTimeInterval(-Double(FaeEconomy.paymentWindowHours + 1) * 3_600)
        let bargain = FaeEconomy.offerBargain(into: &state, kind: .deepLoreDwarf, slot: slot, now: offered)
        FaeEconomy.sweepLapses(into: &state, now: Date())
        XCTAssertTrue(state.marketIsClosed(for: .deepLoreDwarf))

        FaeEconomy.deliver(
            bargainID: bargain.id,
            report: "The grey stone under the porch step that the whole stair leans on, never named.",
            faeResponse: "Good. The weight is acknowledged.",
            reward: "The stone warms in your pocket again.",
            into: &state
        )
        XCTAssertEqual(state.bargains.first?.status, .delivered)
        XCTAssertEqual(state.gifts.first?.isCold, false, "repair thaws the cold gift")
        XCTAssertFalse(state.marketIsClosed(for: .deepLoreDwarf), "repaired debt reopens the market")
    }

    func testChooseFaeAvoidsClosedMarkets() {
        var state = FaePlayerState()
        // Lapse every species except the goblin, then the only open market is the goblin.
        for kind in FaeKind.allCases where kind != .goblin {
            var s = state
            let offered = Date().addingTimeInterval(-Double(FaeEconomy.paymentWindowHours + 1) * 3_600)
            FaeEconomy.offerBargain(into: &s, kind: kind, slot: "\(slot)-\(kind.rawValue)", now: offered)
            FaeEconomy.sweepLapses(into: &s, now: Date())
            state.bargains.append(contentsOf: s.bargains)
            state.gifts.append(contentsOf: s.gifts)
        }
        for kind in FaeKind.allCases where kind != .goblin {
            XCTAssertTrue(state.marketIsClosed(for: kind))
        }
        XCTAssertEqual(FaeEconomy.chooseFae(state: state, slot: slot), .goblin)
    }

    func testSeasonMoodMapping() {
        func date(month: Int) -> Date {
            Calendar.current.date(from: DateComponents(year: 2026, month: month, day: 15)) ?? Date()
        }
        XCTAssertEqual(FaeEconomy.mood(for: date(month: 7)), .generous)
        XCTAssertEqual(FaeEconomy.mood(for: date(month: 10)), .business)
        XCTAssertEqual(FaeEconomy.mood(for: date(month: 4)), .feverish)
        XCTAssertEqual(FaeEconomy.mood(for: date(month: 1)), .serious)
    }

    // MARK: Adapter

    func testAdapterSurfacesAnOwedBargain() {
        var state = FaePlayerState()
        FaeEconomy.offerBargain(into: &state, kind: .bookSprite, slot: slot, now: Date())
        var inputs = BookSourceInputs.empty
        inputs.faeState = state
        let day = BookDay.today()
        let pages = FaeBargainPageSourceAdapter().candidates(
            for: day, context: CuratorContext.make(for: day), inputs: inputs, now: Date()
        )
        XCTAssertEqual(pages.count, 1)
        XCTAssertEqual(pages.first?.type, .faeBargain)
        XCTAssertEqual(pages.first?.payload.metadata["status"], "owed")
        XCTAssertEqual(pages.first?.payload.metadata["faeKind"], "bookSprite")
        XCTAssertFalse(pages.first?.payload.metadata["terms"]?.isEmpty ?? true)
    }

    func testAdapterSurfacesARepairWhenLapsed() {
        var state = FaePlayerState()
        let offered = Date().addingTimeInterval(-Double(FaeEconomy.paymentWindowHours + 1) * 3_600)
        FaeEconomy.offerBargain(into: &state, kind: .goblin, slot: slot, now: offered)
        FaeEconomy.sweepLapses(into: &state, now: Date())
        var inputs = BookSourceInputs.empty
        inputs.faeState = state
        let day = BookDay.today()
        let pages = FaeBargainPageSourceAdapter().candidates(
            for: day, context: CuratorContext.make(for: day), inputs: inputs, now: Date()
        )
        XCTAssertEqual(pages.first?.payload.metadata["status"], "lapsed")
        XCTAssertEqual(pages.first?.payload.metadata["isRepair"], "true")
    }

    // MARK: Gift effects & market

    private func julyDate() -> Date {
        Calendar.current.date(from: DateComponents(year: 2026, month: 7, day: 15)) ?? Date()
    }

    func testReshelvingLiftsARestedSourceOnlyWhenGiftIsWarm() {
        var state = FaePlayerState()
        // No reshelving gift yet.
        XCTAssertTrue(FaeGiftEffects.reshelvedSourceIDs(state: state, surfaceHistory: [:]).isEmpty)

        FaeEconomy.offerBargain(into: &state, kind: .punctuationPixie, slot: slot, now: Date())
        let lifted = FaeGiftEffects.reshelvedSourceIDs(state: state, surfaceHistory: [:])
        XCTAssertEqual(lifted.count, 1, "a warm Reshelving gift lifts exactly one rested source")

        // Cold it by lapsing, and the lift stops.
        var lapsing = state
        let offered = Date().addingTimeInterval(-Double(FaeEconomy.paymentWindowHours + 1) * 3_600)
        lapsing.bargains = []
        lapsing.gifts = []
        FaeEconomy.offerBargain(into: &lapsing, kind: .punctuationPixie, slot: slot, now: offered)
        FaeEconomy.sweepLapses(into: &lapsing, now: Date())
        XCTAssertTrue(FaeGiftEffects.reshelvedSourceIDs(state: lapsing, surfaceHistory: [:]).isEmpty,
                      "a cold Reshelving gift lifts nothing")
    }

    func testReshelvingHonorsAnExplicitBoundSource() {
        var state = FaePlayerState()
        FaeEconomy.offerBargain(into: &state, kind: .deepLoreDwarf, slot: slot, now: Date())
        let giftIndex = try? XCTUnwrap(state.gifts.firstIndex { $0.effect == .reshelving })
        if let giftIndex = giftIndex.flatMap({ $0 }) {
            state.gifts[giftIndex].boundSourceID = "diary-page"
        }
        XCTAssertEqual(FaeGiftEffects.reshelvedSourceIDs(state: state, surfaceHistory: [:]), ["diary-page"])
    }

    func testCuratorBoostsAReshelvedSource() {
        var state = FaePlayerState()
        FaeEconomy.offerBargain(into: &state, kind: .punctuationPixie, slot: slot, now: Date())
        var inputs = BookSourceInputs.empty
        inputs.faeState = state
        let mood = CuratorMood.make(inputs: inputs)
        XCTAssertFalse(mood.reshelvedSourceIDs.isEmpty)
        let liftedID = try? XCTUnwrap(mood.reshelvedSourceIDs.first)
        guard let liftedID = liftedID.flatMap({ $0 }) else { return XCTFail("no lifted source") }
        let page = SurfacePage(
            id: "p", type: .diary, sourceID: liftedID, intent: .capture,
            renderStyle: .promptCard, score: 50, reason: "", prompt: "", detail: "",
            payload: BookPagePayload(headline: "", body: "")
        )
        XCTAssertGreaterThan(mood.adjustment(for: page), 0, "a reshelved source gets a real curator lift")
    }

    func testMarketPurchaseSpendsAttention() {
        var state = FaePlayerState()
        state.attention = 10
        let now = julyDate() // Gold Season → generous → loose page costs 3
        let bought = FaeEconomy.purchase(offerID: "market-loose-page", into: &state, now: now)
        XCTAssertNotNil(bought)
        XCTAssertEqual(state.attention, 7)
        XCTAssertEqual(state.gifts.count, 1)
        XCTAssertEqual(state.gifts.first?.effect, .loosePage)
    }

    func testMarketPurchaseFailsWhenBroke() {
        var state = FaePlayerState()
        state.attention = 1
        let bought = FaeEconomy.purchase(offerID: "market-silver-quill", into: &state, now: julyDate())
        XCTAssertNil(bought)
        XCTAssertEqual(state.attention, 1)
        XCTAssertTrue(state.gifts.isEmpty)
    }

    func testCallingCardOpensMarket() {
        var state = FaePlayerState()
        XCTAssertEqual(FaeEconomy.canEnterMarket(state: state, now: julyDate()) ,
                       FaeEconomy.marketWindowIsOpen(on: julyDate()))
        // Front a goblin bargain → calling card → market is enterable.
        FaeEconomy.offerBargain(into: &state, kind: .goblin, slot: slot, now: julyDate())
        XCTAssertTrue(FaeEconomy.canEnterMarket(state: state, now: julyDate()))
    }

    func testLoosePageReadsSomething() {
        var state = FaePlayerState()
        FaeEconomy.offerBargain(into: &state, kind: .bookSprite, slot: slot, now: Date())
        let gift = try? XCTUnwrap(state.gifts.first { $0.effect == .loosePage })
        guard let gift = gift.flatMap({ $0 }) else { return XCTFail("no loose page") }
        let text = LoosePageReader.text(for: gift)
        XCTAssertFalse(text.isEmpty)
        XCTAssertTrue(LoosePageReader.fragments.contains(text))
    }

    func testLongMemoryPinsAPageForReturn() {
        var state = FaePlayerState()
        FaeEconomy.offerBargain(into: &state, kind: .literaryElf, slot: slot, now: Date())
        let giftIndex = state.gifts.firstIndex { $0.effect == .longMemory }!
        state.gifts[giftIndex].boundSourceID = "kept-page-123"
        XCTAssertEqual(FaeGiftEffects.pinnedPageIDs(state: state), ["kept-page-123"])
    }

    func testGoblinMarginaliaIsOccasionalAndStable() {
        // Short text never gets a note.
        XCTAssertNil(GoblinMarginalia.note(forID: "p1", text: "too short"))
        // A note, when present, is stable across calls for the same id.
        let longText = "The brass tap over the sink, worn pale where a thousand thumbs have pushed it."
        var withNote = 0
        for i in 0..<60 {
            let id = "kept-page-\(i)"
            let first = GoblinMarginalia.note(forID: id, text: longText)
            let second = GoblinMarginalia.note(forID: id, text: longText)
            XCTAssertEqual(first, second, "marginalia must be stable per page id")
            if first != nil { withNote += 1 }
        }
        // Roughly a third get annotated — rare, not every page.
        XCTAssertGreaterThan(withNote, 5)
        XCTAssertLessThan(withNote, 40)
    }

    func testAdapterStaysSilentWithNoBargains() {
        var inputs = BookSourceInputs.empty
        inputs.faeState = FaePlayerState()
        let day = BookDay.today()
        let pages = FaeBargainPageSourceAdapter().candidates(
            for: day, context: CuratorContext.make(for: day), inputs: inputs, now: Date()
        )
        XCTAssertTrue(pages.isEmpty)
    }
}
