import Foundation
import SwiftUI
import UIKit
import WidgetKit

enum InsideCoverStore {
    static let appGroup = "group.com.openclaw.enchantify.insidecover"
    static let stateKey = "insideCoverState"
    static let imageName = "widget-image.png"

    static var defaults: UserDefaults {
        UserDefaults(suiteName: appGroup) ?? .standard
    }

    static var containerURL: URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroup)
    }

    static var imageURL: URL? {
        containerURL?.appendingPathComponent(imageName)
    }

    static func load() -> InsideCoverState {
        guard let data = defaults.data(forKey: stateKey) else {
            return loadBundledSample() ?? .fallback
        }
        do {
            return try JSONDecoder().decode(InsideCoverState.self, from: data)
        } catch {
            return loadBundledSample() ?? .fallback
        }
    }

    static func save(_ state: InsideCoverState) throws {
        var storedState = state
        storedState.imageData = nil
        let data = try JSONEncoder().encode(storedState)
        defaults.set(data, forKey: stateKey)
        if let encoded = state.imageData,
           let bytes = Data(base64Encoded: encoded),
           let url = imageURL {
            try bytes.write(to: url, options: [.atomic])
        }
        WidgetCenter.shared.reloadAllTimelines()
    }

    static func importJSON(from url: URL) throws -> InsideCoverState {
        let shouldStop = url.startAccessingSecurityScopedResource()
        defer {
            if shouldStop {
                url.stopAccessingSecurityScopedResource()
            }
        }
        let data = try Data(contentsOf: url)
        let state = try JSONDecoder().decode(InsideCoverState.self, from: data)
        try save(state)
        return state
    }

    static func loadBundledSample() -> InsideCoverState? {
        guard let url = Bundle.main.url(forResource: "widget-state", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let state = try? JSONDecoder().decode(InsideCoverState.self, from: data) else {
            return nil
        }
        return state
    }

    static func loadImage() -> UIImage? {
        if let url = imageURL,
           let data = try? Data(contentsOf: url),
           let image = UIImage(data: data) {
            return image
        }
        if let encoded = load().imageData,
           let data = Data(base64Encoded: encoded) {
            return UIImage(data: data)
        }
        return nil
    }
}

struct EnchantedPageBackground: View {
    var body: some View {
        LinearGradient(
            colors: [
                Color(red: 0.09, green: 0.07, blue: 0.13),
                Color(red: 0.20, green: 0.12, blue: 0.24),
                Color(red: 0.06, green: 0.12, blue: 0.15)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .overlay(alignment: .bottomTrailing) {
            Text("✦")
                .font(.system(size: 92, weight: .thin))
                .foregroundStyle(.white.opacity(0.12))
                .padding(-4)
        }
    }
}
