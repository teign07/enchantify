import SwiftUI

@main
struct InsideCoverApp: App {
    @Environment(\.scenePhase) private var scenePhase

    init() {
        OvernightScribe.register()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background {
                OvernightScribe.scheduleNext()
            }
        }
    }
}
