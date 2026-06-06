import SwiftUI
import OSLog
import Darwin.Mach
#if canImport(AudioToolbox)
import AudioToolbox
#endif
#if canImport(UIKit)
import UIKit
#endif
#if canImport(Photos)
import Photos
#endif
#if canImport(PhotosUI)
import PhotosUI
#endif
#if canImport(CoreLocation)
import CoreLocation
#endif
#if canImport(HealthKit)
import HealthKit
#endif
#if canImport(Vision)
import Vision
#endif
#if NATIVE_LOCAL_BRAIN && canImport(MLXLLM)
import MLXLLM
#endif
#if NATIVE_LOCAL_BRAIN && canImport(MLXVLM)
import MLXVLM
#endif
#if NATIVE_LOCAL_BRAIN && canImport(MLXLMCommon)
import MLXLMCommon
#endif
#if NATIVE_LOCAL_BRAIN && canImport(MLXLMTokenizers)
import MLXLMTokenizers
#endif
#if NATIVE_LOCAL_BRAIN && canImport(MLXLMHFAPI)
import MLXLMHFAPI
#endif
#if NATIVE_LOCAL_BRAIN && canImport(MLX)
import MLX
#endif

struct LabStatusCard: View {
    let report: LocalModelReport
    let storeReport: BookStore.Report
    let databaseReport: BookDatabase.Report
    let lastBraidDuration: TimeInterval?

    private var durationText: String {
        guard let lastBraidDuration else {
            return "no dry ink yet"
        }
        return "\(Int(lastBraidDuration.rounded()))s to dry"
    }

    private var archiveText: String {
        "\(storeReport.dayCount)d / \(storeReport.pageCount)p kept"
    }

    private var shelfStatusText: String {
        let backupText = databaseReport.backupCount > 0 ? " · \(databaseReport.backupCount) backup\(databaseReport.backupCount == 1 ? "" : "s")" : ""
        return "the shelves are holding · v\(databaseReport.schemaVersion) · \(databaseReport.loadSource.rawValue)\(backupText)"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Label(report.state == .ready ? "local brain awake" : "local brain dreaming", systemImage: report.state == .ready ? "checkmark.circle" : "hourglass")
                Spacer(minLength: 8)
                Label(durationText, systemImage: "timer")
            }

            HStack(spacing: 10) {
                Label(archiveText, systemImage: "archivebox")
                Spacer(minLength: 8)
                Label("today \(storeReport.todayPageCount)p", systemImage: "calendar")
            }

            if let lastError = databaseReport.lastError ?? storeReport.lastError {
                Text(lastError)
                    .lineLimit(2)
                    .foregroundStyle(.red.opacity(0.88))
            } else {
                Text(shelfStatusText)
                    .lineLimit(1)
                    .foregroundStyle(.white.opacity(0.62))
            }
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.white.opacity(0.82))
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.12), lineWidth: 1)
        }
    }
}


struct BodySourceCard: View {
    let bodySignal: BodySourceSignal?
    let message: String
    let isRequesting: Bool
    let hasRequested: Bool
    let isAvailable: Bool
    let onRequest: () -> Void

    private var title: String {
        bodySignal == nil ? "Body Doorway" : "Body Page awake"
    }

    private var statusText: String {
        if let bodySignal {
            return bodySignal.status.capitalized
        }
        if !isAvailable {
            return "no doorway"
        }
        if isRequesting {
            return "listening"
        }
        return hasRequested ? "tap to listen again" : "door unopened"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: bodySignal == nil ? "heart.text.square" : "checkmark.seal")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(BookPalette.teal)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(BookPalette.ink)
                    Text(statusText)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(BookPalette.ink.opacity(0.56))
                }

                Spacer()

                if isRequesting {
                    ProgressView()
                        .tint(BookPalette.teal)
                } else {
                    Button {
                        onRequest()
                    } label: {
                        Image(systemName: bodySignal == nil ? "heart.circle" : "arrow.clockwise.circle")
                            .font(.title3.weight(.semibold))
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(BookPalette.teal)
                    .disabled(!isAvailable)
                    .accessibilityLabel(bodySignal == nil ? "Open the body doorway" : "Listen again")
                }
            }

            if let bodySignal {
                Text(bodySignal.phrase)
                    .font(.system(.body, design: .serif))
                    .foregroundStyle(BookPalette.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Text(message)
                .font(.caption)
                .foregroundStyle(BookPalette.ink.opacity(0.62))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .parchmentSurface(accent: BookPalette.teal, isActive: bodySignal != nil)
    }
}

struct WeatherSourceCard: View {
    let weatherSignal: WeatherSourceSignal?
    let message: String
    let isRequesting: Bool
    let hasRequested: Bool
    let isAvailable: Bool
    let onRequest: () -> Void

    private var title: String {
        weatherSignal == nil ? "Weather Doorway" : "Weather Page awake"
    }

    private var statusText: String {
        if let weatherSignal {
            return weatherSignal.currentTemperature ?? "sky read"
        }
        if !isAvailable {
            return "no window"
        }
        if isRequesting {
            return "listening"
        }
        return hasRequested ? "tap to listen again" : "door unopened"
    }

    private var iconName: String {
        weatherSignal?.conditionSymbolName ?? "cloud.sun"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: iconName)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(BookPalette.gold)
                    .frame(width: 28)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(BookPalette.ink)
                    Text(statusText)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(BookPalette.ink.opacity(0.56))
                }

                Spacer()

                if isRequesting {
                    ProgressView()
                        .tint(BookPalette.teal)
                } else {
                    Button {
                        onRequest()
                    } label: {
                        Image(systemName: weatherSignal == nil ? "location.circle" : "arrow.clockwise.circle")
                            .font(.title3.weight(.semibold))
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(BookPalette.teal)
                    .disabled(!isAvailable)
                    .accessibilityLabel(weatherSignal == nil ? "Open the weather doorway" : "Listen to the sky again")
                }
            }

            if let weatherSignal {
                Text(weatherSignal.phrase)
                    .font(.system(.body, design: .serif))
                    .foregroundStyle(BookPalette.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Text(message)
                .font(.caption)
                .foregroundStyle(BookPalette.ink.opacity(0.62))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .parchmentSurface(accent: BookPalette.gold, isActive: weatherSignal != nil)
    }
}

struct StoryFieldStatusCard: View {
    let surface: SurfacePage?
    let events: [NarrativeEvent]
    let isPreparing: Bool

    private var metadata: [String: String] {
        surface?.payload.metadata ?? [:]
    }

    private var title: String {
        surface == nil ? "Story Field" : "Story Page ready"
    }

    private var statusText: String {
        if isPreparing {
            return "ink moving"
        }
        if surface != nil {
            return "page waiting"
        }
        return "listening"
    }

    private var packetText: String {
        guard let packetID = metadata["packetID"]?.nonEmpty else {
            return "no packet chosen yet"
        }
        return "packet \(String(packetID.prefix(8)))"
    }

    private var bookGlowText: String {
        let glow = metadata["bookGlow"]?.nonEmpty ?? metadata["playerBelief"]?.nonEmpty
        return glow.map { "glow \($0)" } ?? "glow unread"
    }

    private var threads: [String] {
        metadataList("selectedThreads")
    }

    private var entities: [String] {
        metadataList("selectedEntities")
    }

    private var relationships: [String] {
        metadataList("selectedRelationships")
    }

    private var signals: [String] {
        metadataLines("realSignals")
    }

    private var pressures: [String] {
        metadataLines("relationshipPressures")
    }

    private var recentChoiceEvents: [NarrativeEvent] {
        Array(events
            .filter { $0.kind == .choiceSelected || $0.sourcePageType == .narrativeOS }
            .sorted { $0.createdAt > $1.createdAt }
            .prefix(3))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: "point.3.connected.trianglepath.dotted")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(BookPalette.violet)
                    .frame(width: 28)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(BookPalette.ink)
                    Text(statusText)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(BookPalette.ink.opacity(0.56))
                }

                Spacer()

                if isPreparing {
                    ProgressView()
                        .tint(BookPalette.violet)
                } else {
                    Text(bookGlowText)
                        .font(.caption.monospacedDigit().weight(.bold))
                        .foregroundStyle(BookPalette.violet)
                }
            }

            Text(surface == nil
                 ? "The Book has not laid a Story Page in the margin yet."
                 : "The next Story Page has enough weight to open.")
                .font(.system(.body, design: .serif))
                .foregroundStyle(BookPalette.ink)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 8) {
                StoryFieldDebugLine(icon: "number", label: "packet", value: packetText)
                if let proseStatus = metadata["proseStatus"]?.nonEmpty {
                    StoryFieldDebugLine(icon: "pencil.and.scribble", label: "ink", value: proseStatus)
                }
                if !threads.isEmpty {
                    StoryFieldDebugLine(icon: "point.3.connected.trianglepath.dotted", label: "thread", value: threads.prefix(2).joined(separator: " / "))
                }
                if !entities.isEmpty {
                    StoryFieldDebugLine(icon: "person.text.rectangle", label: "entities", value: entities.prefix(3).joined(separator: ", "))
                }
                if !relationships.isEmpty {
                    StoryFieldDebugLine(icon: "arrow.triangle.branch", label: "ties", value: relationships.prefix(2).joined(separator: ", "))
                }
            }

            if !signals.isEmpty || !pressures.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(Array(signals.prefix(2).enumerated()), id: \.offset) { _, signal in
                        Text(signal)
                            .storyFieldSmallText()
                    }
                    ForEach(Array(pressures.prefix(1).enumerated()), id: \.offset) { _, pressure in
                        Text(pressure)
                            .storyFieldSmallText()
                    }
                }
            }

            if !recentChoiceEvents.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("recent turns")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(BookPalette.ink.opacity(0.54))
                    ForEach(recentChoiceEvents, id: \.id) { event in
                        Text(event.summary)
                            .storyFieldSmallText()
                    }
                }
            }
        }
        .padding(16)
        .parchmentSurface(accent: BookPalette.violet, isActive: surface != nil || isPreparing)
    }

    private func metadataList(_ key: String) -> [String] {
        metadata[key]?
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty } ?? []
    }

    private func metadataLines(_ key: String) -> [String] {
        metadata[key]?
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty } ?? []
    }
}

private struct StoryFieldDebugLine: View {
    let icon: String
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Image(systemName: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(BookPalette.ink.opacity(0.5))
                .frame(width: 18)
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(BookPalette.ink.opacity(0.52))
                .frame(width: 54, alignment: .leading)
            Text(value)
                .font(.caption.weight(.semibold))
                .foregroundStyle(BookPalette.ink.opacity(0.72))
                .lineLimit(2)
        }
    }
}

struct StatusBanner: View {
    let message: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(message)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(.white.opacity(0.86))
                .fixedSize(horizontal: false, vertical: true)

            Spacer(minLength: 8)

            if let actionTitle, let action {
                Button(actionTitle) {
                    action()
                }
                .font(.footnote.weight(.bold))
                .buttonStyle(.plain)
                .foregroundStyle(BookPalette.teal)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(.white.opacity(0.12), lineWidth: 1)
        }
    }
}

struct BeliefScoreBadge: View {
    let score: Int
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isBreathing = false

    private var clampedScore: Int {
        min(100, max(0, score))
    }

    private var normalized: Double {
        Double(clampedScore) / 100
    }

    private var tierName: String {
        BeliefLexicon.glowName(for: clampedScore)
    }

    private var glowRadius: CGFloat {
        4 + normalized * 18
    }

    private var glowOpacity: Double {
        0.22 + normalized * 0.48
    }

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "sparkle")
                .font(.caption.weight(.bold))
                .symbolEffect(.pulse, options: .speed(0.55), value: isBreathing)

            Text(tierName)
                .font(.caption.weight(.black))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .foregroundStyle(BookPalette.lampGold)
        .padding(.horizontal, 11)
        .padding(.vertical, 7)
        .frame(minWidth: 86, maxWidth: 132)
        .background(
            Capsule(style: .continuous)
                .fill(BookPalette.nightPanel.opacity(0.72))
        )
        .overlay {
            Capsule(style: .continuous)
                .stroke(BookPalette.lampGold.opacity(0.34 + normalized * 0.38), lineWidth: 1)
        }
        .shadow(
            color: BookPalette.lampGold.opacity(glowOpacity * (isBreathing ? 1.0 : 0.62)),
            radius: glowRadius * (isBreathing ? 1.08 : 0.78),
            x: 0,
            y: 0
        )
        .scaleEffect(isBreathing && !reduceMotion ? 1.025 : 1.0)
        .animation(
            reduceMotion ? nil : .easeInOut(duration: 2.4 - normalized * 0.7).repeatForever(autoreverses: true),
            value: isBreathing
        )
        .onAppear {
            guard !reduceMotion else { return }
            isBreathing = true
        }
        .accessibilityLabel("Belief \(tierName), \(clampedScore) out of 100")
        .help("Belief \(clampedScore) out of 100")
    }
}

struct BraidingStatusCard: View {
    let quip: String
    let startedAt: Date?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                ProgressView()
                    .tint(BookPalette.teal)
                Text("The braid is taking ink")
                    .font(.headline)
                    .foregroundStyle(BookPalette.ink)
                Spacer()
                if let startedAt {
                    Text(startedAt, style: .timer)
                        .font(.caption.monospacedDigit().weight(.bold))
                        .foregroundStyle(BookPalette.teal)
                }
            }

            Text(quip)
                .font(.system(.body, design: .serif, weight: .semibold))
                .lineSpacing(3)
                .foregroundStyle(BookPalette.ink.opacity(0.82))
                .id(quip)
                .transition(.opacity)

            Text("You may leave the page open. The Book will keep its place and finish the line.")
                .font(.caption)
                .foregroundStyle(BookPalette.ink.opacity(0.62))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .parchmentSurface(accent: BookPalette.teal, isActive: true)
    }
}

struct LocalBrainWorkingStatusCard: View {
    let label: String
    let quip: String
    let startedAt: Date?
    let queuedCount: Int

    private var title: String {
        switch label {
        case "braid":
            return "The braid is taking ink"
        case "weather", "weather-page":
            return "The Weather Page is finding its words"
        case "story-page":
            return "The Story Page is being written"
        case "photo-illumination":
            return "Penny is illuminating the photograph"
        case "wonder-compass":
            return "The Compass is choosing a passage"
        default:
            return "The local brain is writing"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                ProgressView()
                    .tint(BookPalette.violet)
                Text(title)
                    .font(.headline)
                    .foregroundStyle(BookPalette.ink)
                Spacer()
                if queuedCount > 0 {
                    Text("\(queuedCount) waiting")
                        .font(.caption.monospacedDigit().weight(.bold))
                        .foregroundStyle(BookPalette.violet)
                } else if let startedAt {
                    Text(startedAt, style: .timer)
                        .font(.caption.monospacedDigit().weight(.bold))
                        .foregroundStyle(BookPalette.violet)
                }
            }

            Text(quip)
                .font(.system(.body, design: .serif, weight: .semibold))
                .lineSpacing(3)
                .foregroundStyle(BookPalette.ink.opacity(0.82))
                .id(quip)
                .transition(.opacity)

            Text("Only one local-brain page can write at a time. The Book is keeping the shelf steady.")
                .font(.caption)
                .foregroundStyle(BookPalette.ink.opacity(0.62))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .parchmentSurface(accent: BookPalette.violet, isActive: true)
    }
}

struct ModelStatusCard: View {
    let report: LocalModelReport
    let isInstalling: Bool
    let installMessage: String
    let installProgress: Double?
    let onRefresh: () -> Void
    let onInstall: () -> Void

    private var statusColor: Color {
        switch report.state {
        case .missing:
            return BookPalette.gold
        case .ready:
            return BookPalette.teal
        case .unavailable:
            return .red.opacity(0.78)
        }
    }

    private var iconName: String {
        switch report.state {
        case .missing:
            return "brain.head.profile"
        case .ready:
            return "checkmark.seal"
        case .unavailable:
            return "exclamationmark.triangle"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: iconName)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(statusColor)
                    .frame(width: 34, height: 34)
                    .background(statusColor.opacity(0.14), in: Circle())

                VStack(alignment: .leading, spacing: 5) {
                    Text("Book Brain")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(BookPalette.ink.opacity(0.52))
                    Text(report.title)
                        .font(.headline)
                        .foregroundStyle(BookPalette.ink)
                }

                Spacer(minLength: 12)

                Button {
                    onRefresh()
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.body.weight(.bold))
                        .frame(width: 34, height: 34)
                }
                .buttonStyle(.plain)
                .foregroundStyle(BookPalette.teal)
                .accessibilityLabel("Ask whether the local brain is awake")
            }

            Text(report.detail)
                .font(.callout)
                .foregroundStyle(BookPalette.ink.opacity(0.70))
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 4) {
                Label(mlxRuntimeLinked ? "the model shelf is reachable" : "the model shelf is missing", systemImage: "cpu")
                Label("this device: \(report.deviceSummary)", systemImage: "iphone")
                Label("the Book chose: \(report.preferredModelID)", systemImage: "sparkles")
                Label("small fallback: \(report.fallbackModelID)", systemImage: "arrow.triangle.2.circlepath")
                Link(destination: URL(string: report.preferredModelSource) ?? URL(string: "https://huggingface.co/mlx-community")!) {
                    Label("model source", systemImage: "link")
                }
            }
            .font(.caption)
            .foregroundStyle(BookPalette.ink.opacity(0.58))
            .lineLimit(2)
            .minimumScaleFactor(0.82)

            if report.state == .missing {
                Button {
                    onInstall()
                } label: {
                    Label(isInstalling ? "The Book is fetching its brain..." : "Fetch the local brain", systemImage: "arrow.down.circle")
                        .font(.subheadline.weight(.bold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(isInstalling || !mlxRuntimeLinked)
            }

            if isInstalling {
                VStack(alignment: .leading, spacing: 6) {
                    if let installProgress {
                        ProgressView(value: installProgress)
                            .tint(BookPalette.teal)
                        Text("\(Int(installProgress * 100))%")
                            .font(.caption.monospacedDigit().weight(.semibold))
                            .foregroundStyle(BookPalette.teal)
                    } else {
                        ProgressView()
                            .tint(BookPalette.teal)
                        Text("Opening the model shelf")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(BookPalette.teal)
                    }
                }
            }

            if !installMessage.isEmpty {
                Text(installMessage)
                    .font(.caption)
                    .foregroundStyle(BookPalette.ink.opacity(0.64))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .parchmentSurface(accent: statusColor, isActive: report.state == .ready)
    }
}
