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
        title: "The Inside Cover",
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
