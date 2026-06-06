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

protocol Braider {
    func braid(day: BookDay) async throws -> BookPage
}

protocol WonderCompassPassageChoosing {
    func chooseWonderCompassSnippet(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) async throws -> ReferenceSnippet
}

protocol WeatherEnchanting {
    func enchantWeather(weather: WeatherSourceSignal, day: BookDay) async throws -> EnchantedWeatherSignal
}

enum LocalModelState: String, Codable, Equatable {
    case missing
    case ready
    case unavailable
}

struct LocalModelReport: Codable, Equatable {
    var state: LocalModelState
    var preferredModelID: String
    var fallbackModelID: String
    var preferredModelSource: String
    var fallbackModelSource: String
    var installPath: String
    var detail: String
    var deviceSummary: String

    var title: String {
        switch state {
        case .missing:
            return "Brain not installed"
        case .ready:
            return "Local brain ready"
        case .unavailable:
            return "Brain unavailable"
        }
    }

    var isReady: Bool {
        state == .ready
    }
}

enum LocalModelError: LocalizedError {
    case missingModel(LocalModelReport)

    var errorDescription: String? {
        switch self {
        case .missingModel(let report):
            return "\(report.preferredModelID) is not installed yet."
        }
    }
}

struct ActiveLocalModel: Codable, Equatable {
    var modelID: String
    var path: String
    var activatedAt: Date
}

enum LocalModelManager {
    struct ModelChoice: Codable, Equatable {
        var modelID: String
        var label: String
        var minimumMemoryGB: Int
        var sourceURL: String
        var reason: String
        var supersedes: [String] = []
    }

    static let compactModel = ModelChoice(
        modelID: "mlx-community/gemma-3-1b-it-4bit",
        label: "Gemma 3 1B 4-bit",
        minimumMemoryGB: 0,
        sourceURL: "https://huggingface.co/mlx-community/gemma-3-1b-it-4bit",
        reason: "smallest local brain, best for standard iPhones"
    )
    static let balancedModel = ModelChoice(
        modelID: "mlx-community/gemma-4-e2b-it-OptiQ-4bit",
        label: "Gemma 4 E2B OptiQ 4-bit",
        minimumMemoryGB: 6,
        sourceURL: "https://huggingface.co/mlx-community/gemma-4-e2b-it-OptiQ-4bit",
        reason: "recommended local brain for iPhone 15-class devices; MLX-ready 4-bit upgrade aligned with the Gemma 4 QAT/edge release",
        supersedes: [
            "mlx-community/gemma-4-e2b-it-4bit"
        ]
    )
    static let expansiveModel = ModelChoice(
        modelID: "mlx-community/gemma-4-e4b-it-OptiQ-4bit",
        label: "Gemma 4 E4B OptiQ 4-bit",
        minimumMemoryGB: 8,
        sourceURL: "https://huggingface.co/mlx-community/gemma-4-e4b-it-OptiQ-4bit",
        reason: "larger local brain for iPhone 17-class devices and high-memory iPads; keeps iPhone 15-class hardware on E2B for memory headroom",
        supersedes: [
            "mlx-community/gemma-4-e4b-it-4bit"
        ]
    )
    static let allModelChoices = [compactModel, balancedModel, expansiveModel]
    static let modelsDirectoryName = "LocalModels"
    static let activeModelMarkerName = "active-model.json"

    static var preferredModel: ModelChoice {
        let memoryGB = deviceMemoryGB
        if memoryGB >= expansiveModel.minimumMemoryGB,
           !isIPhone15ClassHardware {
            return expansiveModel
        }
        if memoryGB >= balancedModel.minimumMemoryGB {
            return balancedModel
        }
        return compactModel
    }

    static var preferredModelID: String {
        preferredModel.modelID
    }

    static var fallbackModelID: String {
        compactModel.modelID
    }

    static var deviceMemoryGB: Int {
        let bytes = ProcessInfo.processInfo.physicalMemory
        let gb = Double(bytes) / 1_073_741_824
        return max(1, Int(gb.rounded(.toNearestOrAwayFromZero)))
    }

    static var hardwareIdentifier: String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let mirror = Mirror(reflecting: systemInfo.machine)
        return mirror.children.reduce(into: "") { identifier, element in
            guard let value = element.value as? Int8, value != 0 else { return }
            identifier.append(String(UnicodeScalar(UInt8(value))))
        }
    }

    static var isIPhone15ClassHardware: Bool {
        // iPhone 15 and iPhone 15 Pro families report as iPhone15,4/5 and iPhone16,1/2.
        hardwareIdentifier.hasPrefix("iPhone15,") || hardwareIdentifier.hasPrefix("iPhone16,")
    }

    static var deviceSummary: String {
        "\(hardwareIdentifier), about \(deviceMemoryGB) GB memory"
    }

    static var canAttemptVisionPhotoIllumination: Bool {
        deviceMemoryGB >= 8
    }

    private static var supportDirectory: URL {
        let baseURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let bundleID = Bundle.main.bundleIdentifier ?? "com.openclaw.enchantify.insidecover"
        return baseURL.appendingPathComponent(bundleID, isDirectory: true)
    }

    private static var cacheDirectory: URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
    }

    static var modelsDirectory: URL {
        supportDirectory.appendingPathComponent(modelsDirectoryName, isDirectory: true)
    }

    static var activeModelMarkerURL: URL {
        modelsDirectory.appendingPathComponent(activeModelMarkerName)
    }

    static func modelDirectory(for modelID: String) -> URL {
        let folderName = modelID
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: ":", with: "_")
        return modelsDirectory.appendingPathComponent(folderName, isDirectory: true)
    }

    static var activeModelDirectory: URL? {
        activeModelCandidate?.directory
    }

    private static var activeModelCandidate: (choice: ModelChoice, directory: URL)? {
        if let marker = activeModelMarker,
           activeModelIDs.contains(marker.modelID),
           let choice = allModelChoices.first(where: { $0.modelID == marker.modelID }),
           modelFilesArePresent(at: URL(fileURLWithPath: marker.path)) {
            return (choice, URL(fileURLWithPath: marker.path))
        }

        let candidates = activeModelChoices.flatMap { choice in
            ([modelDirectory(for: choice.modelID)] + huggingFaceSnapshotDirectories(for: choice.modelID))
                .map { directory in (choice: choice, directory: directory) }
        }
        return candidates.first { modelFilesArePresent(at: $0.directory) }
    }

    private static var activeModelIDs: [String] {
        [preferredModelID]
    }

    private static var activeModelChoices: [ModelChoice] {
        [preferredModel]
    }

    private static var activeModelMarker: ActiveLocalModel? {
        guard let data = try? Data(contentsOf: activeModelMarkerURL) else {
            return nil
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try? decoder.decode(ActiveLocalModel.self, from: data)
    }

    static func activateModel(modelID: String, directory: URL) throws {
        try FileManager.default.createDirectory(
            at: modelsDirectory,
            withIntermediateDirectories: true
        )
        let marker = ActiveLocalModel(
            modelID: modelID,
            path: directory.path,
            activatedAt: Date()
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(marker)
        try data.write(to: activeModelMarkerURL, options: [.atomic])
    }

    static func report() -> LocalModelReport {
        #if !NATIVE_LOCAL_BRAIN || !(canImport(MLXLMHFAPI) && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX))
        return LocalModelReport(
            state: .unavailable,
            preferredModelID: preferredModelID,
            fallbackModelID: fallbackModelID,
            preferredModelSource: preferredModel.sourceURL,
            fallbackModelSource: compactModel.sourceURL,
            installPath: modelsDirectory.path,
            detail: "The native local brain is disabled in this safe startup build while its launch-time package crash is isolated.",
            deviceSummary: deviceSummary
        )
        #else
        do {
            try FileManager.default.createDirectory(
                at: modelsDirectory,
                withIntermediateDirectories: true
            )
        } catch {
            return LocalModelReport(
                state: .unavailable,
                preferredModelID: preferredModelID,
                fallbackModelID: fallbackModelID,
                preferredModelSource: preferredModel.sourceURL,
                fallbackModelSource: compactModel.sourceURL,
                installPath: modelsDirectory.path,
                detail: "The app could not prepare its local model folder: \(error.localizedDescription)",
                deviceSummary: deviceSummary
            )
        }

        if let active = activeModelCandidate {
            return LocalModelReport(
                state: .ready,
                preferredModelID: preferredModelID,
                fallbackModelID: fallbackModelID,
                preferredModelSource: preferredModel.sourceURL,
                fallbackModelSource: compactModel.sourceURL,
                installPath: active.directory.path,
                detail: "\(active.choice.label) is present. The Book chose it for this device: \(active.choice.reason).",
                deviceSummary: deviceSummary
            )
        }

        return LocalModelReport(
            state: .missing,
            preferredModelID: preferredModelID,
            fallbackModelID: fallbackModelID,
            preferredModelSource: preferredModel.sourceURL,
            fallbackModelSource: compactModel.sourceURL,
            installPath: modelsDirectory.path,
            detail: "The Book recommends \(preferredModel.label) for this device: \(preferredModel.reason). Install it here, then braiding can stay local.",
            deviceSummary: deviceSummary
        )
        #endif
    }

    static func removeSupersededModels(for modelID: String, preserving activeDirectory: URL) {
        guard let choice = allModelChoices.first(where: { $0.modelID == modelID }) else {
            return
        }

        let fileManager = FileManager.default
        for oldModelID in choice.supersedes {
            let directory = modelDirectory(for: oldModelID)
            guard directory.standardizedFileURL != activeDirectory.standardizedFileURL,
                  fileManager.fileExists(atPath: directory.path) else {
                continue
            }
            try? fileManager.removeItem(at: directory)
        }
    }

    private static func modelFilesArePresent(at directory: URL) -> Bool {
        let fileManager = FileManager.default
        guard fileManager.fileExists(atPath: directory.path) else {
            return false
        }

        let files = (try? fileManager.contentsOfDirectory(atPath: directory.path)) ?? []
        let hasConfig = files.contains("config.json")
        let hasWeights = files.contains { $0.hasSuffix(".safetensors") }
        let hasTokenizer = files.contains { name in
            name == "tokenizer.json" || name == "tokenizer.model" || name.hasPrefix("tokenizer_config")
        }
        return hasConfig && hasWeights && hasTokenizer
    }

    private static func huggingFaceSnapshotDirectories(for modelID: String) -> [URL] {
        let cacheModelName = "models--" + modelID.replacingOccurrences(of: "/", with: "--")
        let snapshotsDirectory = cacheDirectory
            .appendingPathComponent("huggingface", isDirectory: true)
            .appendingPathComponent("hub", isDirectory: true)
            .appendingPathComponent(cacheModelName, isDirectory: true)
            .appendingPathComponent("snapshots", isDirectory: true)

        guard let snapshots = try? FileManager.default.contentsOfDirectory(
            at: snapshotsDirectory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        return snapshots.sorted { left, right in
            let leftDate = (try? left.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            let rightDate = (try? right.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return leftDate > rightDate
        }
    }

    static func prompt(for day: BookDay) -> String {
        bookOfYouBraidPrompt(for: day)
    }

    static func taskPrompt(for day: BookDay) -> String {
        let fragments = day.capturedPages
            .sorted { $0.createdAt < $1.createdAt }
            .map { page in
                """
                TASK PAGE: \(page.type.title)
                PAGE INSTRUCTIONS:
                \(page.userInput)
                """
            }
            .joined(separator: "\n\n")

        return fragments.isEmpty ? "No task page was supplied." : fragments
    }

    static func bookOfYouBraidPrompt(for day: BookDay) -> String {
        let evidence = braidEvidenceLines(for: day).joined(separator: "\n\n")

        return """
        You are the Book inside ReEnchanted.
        Braid the player's kept pages into one grounded Book of You entry: a small story about this day.

        SHAPE:
        - Write 4 to 6 short paragraphs, about 220 to 380 words.
        - Give the braid a beginning, a turn, and a landing.
        - Use every kept page as evidence when possible. If there are many, weave them by theme and chronology.
        - Make it feel narrated, not listed. Do not mention page types like "Weather Page" or "Lore Page" unless the player wrote those words.
        - End with one closing sentence that begins: "The Book kept the page:"

        VOICE:
        - Warm, literary, playful, and concrete.
        - The Book notices small true details and gives them a little magic.
        - Write simple surprising sentences. Use specific nouns and verbs.
        - Prefer what someone said, touched, carried, avoided, dropped, or noticed over explaining what it means.
        - No diagnosis, no flattery, no moralizing, no corporate/app language.
        - Do not invent completed actions, locations, people, feelings, or tasks.
        - Avoid vague wonder, generic inspiration, journey, profound, tapestry, echoes, hidden meaning, and abstract emotional summary.

        ANTI-PARROT RULE:
        - Do not copy any supplied sentence longer than seven words.
        - Paraphrase the kept pages into a coherent story.
        - You may quote one short phrase only if it has unusual power.

        KEPT PAGES FROM TODAY:
        \(evidence.isEmpty ? "- No kept pages yet. Write a quiet note about the Book waiting for the day to gather." : evidence)
        """
    }

    static func braidEvidenceLines(for day: BookDay, characterLimit: Int = 760) -> [String] {
        day.capturedPages
            .sorted { $0.createdAt < $1.createdAt }
            .enumerated()
            .map { index, page in
                let prompt = clippedBraidText(page.promptText, limit: 220)
                let text = clippedBraidText(page.userInput, limit: characterLimit)
                let tags = page.tags.isEmpty ? "none" : page.tags.joined(separator: ", ")
                let media = braidMediaEvidence(for: page)
                return """
                \(index + 1). \(page.type.title)
                Prompt: \(prompt.isEmpty ? "none" : prompt)
                Kept text: \(text.isEmpty ? "(blank)" : text)
                Visual evidence: \(media.isEmpty ? "none" : media)
                Tags: \(tags)
                """
            }
    }

    private static func braidMediaEvidence(for page: BookPage) -> String {
        page.mediaAssets
            .prefix(3)
            .map { asset in
                let kind: String
                switch asset.kind {
                case .bundledImage:
                    kind = "bundled Labyrinth illustration"
                case .renderedImageFile:
                    kind = "kept illuminated page image"
                case .photoLibraryAsset:
                    kind = "private source photo reference"
                }
                let caption = clippedBraidText(asset.caption, limit: 140)
                return caption.isEmpty ? kind : "\(kind): \(caption)"
            }
            .joined(separator: "; ")
    }

    private static func clippedBraidText(_ value: String, limit: Int) -> String {
        let normalized = value
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "  ", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard normalized.count > limit else { return normalized }
        let end = normalized.index(normalized.startIndex, offsetBy: limit)
        return normalized[..<end].trimmingCharacters(in: .whitespacesAndNewlines) + "..."
    }

    static func wonderCompassSelectionPrompt(
        for day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) -> String {
        let fragments = day.capturedPages
            .sorted { $0.createdAt < $1.createdAt }
            .map { page in
                let tags = page.tags.isEmpty ? "" : " [tags: \(page.tags.joined(separator: ", "))]"
                return "- \(page.type.title): \(page.userInput)\(tags)"
            }
            .joined(separator: "\n")

        var signals: [String] = []
        if let body = inputs.body, body.isAvailable {
            signals.append("Body Page translation: \(body.status), \(body.phrase)")
        }
        if let weather = inputs.weather, weather.isAvailable {
            signals.append("Weather: \(weather.phrase)")
        }

        let candidateList = candidates.prefix(8).map { snippet in
            """
            ID: \(snippet.id)
            Title: \(snippet.title)
            Prompt: \(snippet.prompt)
            Tags: \(snippet.tags.joined(separator: ", "))
            Passage: \(snippet.body.prefix(520))
            """
        }
        .joined(separator: "\n\n")

        return """
        You are the Wonder Compass librarian inside ReEnchanted.
        Choose the single best Wonder Compass book passage for the user's day so far.
        Use the user's actual fragments and gentle contextual signals. Do not diagnose, moralize, or invent events.
        Prefer rest/care passages when the day sounds hard or depleted. Prefer souvenir/write passages when the day has moments worth keeping. Prefer playful/sense/embark passages when the day has energy.

        Reply with only the exact ID of the chosen passage. No explanation.

        Day fragments:
        \(fragments.isEmpty ? "- No captured fragments yet." : fragments)

        Signals:
        \(signals.isEmpty ? "- No extra signals." : signals.joined(separator: "\n"))

        Candidate passages:
        \(candidateList)
        """
    }

    static func weatherPrompt(weather: WeatherSourceSignal, day: BookDay) -> String {
        let fragments = day.capturedPages
            .sorted { $0.createdAt < $1.createdAt }
            .prefix(5)
            .map { page in
                "- \(page.type.title): \(page.userInput)"
            }
            .joined(separator: "\n")

        return """
        You are the Weather Page inside ReEnchanted.
        Translate the real weather into Enchantify mood while keeping it legible.
        Do not hide the actual weather. Do not mention sensors, APIs, surveillance, or exact location.
        Write 1 short enchanted sentence, then 1 plain weather sentence.
        Keep both grounded and useful. No diagnosis. No generic assistant voice.
        Use concrete weather nouns and verbs. No vague mood poetry.

        Weather source: \(weather.source)
        Raw weather: \(weather.phrase)
        Current temperature: \(weather.currentTemperature ?? "unknown")
        Forecast: \(weather.forecast ?? "unknown")

        Day fragments:
        \(fragments.isEmpty ? "- No captured fragments yet." : fragments)
        """
    }

    static let photoIlluminationPrompt = """
    You are Penny Blackletter, field-note scribe for The Academy of Unlikely Arts.
    Look at the photo. Write small caption-scraps that name what you actually see,
    with a dry, affectionate, slightly odd tone — like a naturalist cataloguing a
    beloved, ridiculous specimen.

    RULES (follow exactly):
    - Every line names a real thing visible in THIS photo: an object, a color, a
      texture, a gesture, an animal, the light.
    - Do not mention anything not visible in the photo, except "The Book" in closing_line.
    - Every line is under 8 words. Short and plain, but with a pulse — give things
      a small verb or opinion ("glasses, slightly fogged"), never lab-report flatness
      ("glasses present").
    - Plain words, dry wit. Give one thing in the photo a job or an opinion.
    - Refer to any person only as "the subject" or "good company." Never guess names.

    For "suggested_template", choose EXACTLY ONE value from this list (copy one, never more):
      harbor_field_note
      creature_comfort
      home_vessel
      good_company
      academy_field_study
      rest_and_quiet

    For "closing_line": one line under 10 words that names what THIS day became,
    in the Book's keeping — e.g. "The Book kept the page: the rabbit won."

    Return ONLY this JSON, nothing else:
    {
      "scene": "one plain sentence: what is literally in the photo",
      "motifs": ["3-5 one-word tags"],
      "mood": "2-3 words",
      "suggested_template": "exactly one value copied from the list above",
      "marginalia": {
        "field_note": "under 8 words, names the main thing",
        "stamp_label": "2-3 words, title-like, no names",
        "observation_list": ["5 items, each under 6 words, each a real visible detail with a pulse"],
        "closing_line": "under 10 words, names what the day became in the Book's keeping"
      },
      "souvenir_candidates": ["two lines, each under 16 words, each naming something only in THIS photo"]
    }

    EXAMPLES:
    Rabbit pressed against a smiling person's cheek, gray fleece blanket:
    {"scene":"A rabbit presses its face to a smiling person's cheek on a gray blanket.","motifs":["rabbit","rest","trust","home"],"mood":"soft and still","suggested_template":"creature_comfort","marginalia":{"field_note":"One rabbit, fully committed to this cheek.","stamp_label":"Pawlogy 201","observation_list":["Ginger fur, shamelessly soft","Purple glasses, slightly askew","Gray fleece, thoroughly rumpled","Eyes closed in total trust","One ear flying at half-mast"],"closing_line":"The Book kept the page: the rabbit won."},"souvenir_candidates":["The rabbit pressed its whole face to her cheek like it was filing a report.","A small ginger creature decided her shoulder was the safest place in Maine."]}
    Giant rubber duck in foggy harbor, two grinning people:
    {"scene":"Two grinning people in front of a giant yellow duck in fog.","motifs":["harbor","fog","duck","absurd"],"mood":"silly and bright","suggested_template":"good_company","marginalia":{"field_note":"Giant duck, reporting for harbor duty.","stamp_label":"Dockside Census","observation_list":["Fog loitering on the water","A duck the size of a house","Two grins, entirely unhidden","Masts hiding behind the mist"],"closing_line":"The Book kept the page: the duck reigned."},"souvenir_candidates":["The giant duck kept watch over the fog like an appointed sheriff.","We grinned at a rubber bird the size of a shed, and the day approved."]}

    Now read the attached photo and return the JSON.
    """
}

struct LocalModelWeatherEnchanter: WeatherEnchanting {
    func enchantWeather(weather: WeatherSourceSignal, day: BookDay) async throws -> EnchantedWeatherSignal {
        let report = LocalModelManager.report()
        guard report.isReady else {
            throw LocalModelError.missingModel(report)
        }

        return WeatherEnchanter.fallback(weather: weather)
    }
}

struct FakeWeatherEnchanter: WeatherEnchanting {
    func enchantWeather(weather: WeatherSourceSignal, day: BookDay) async throws -> EnchantedWeatherSignal {
        try await Task.sleep(nanoseconds: 250_000_000)
        return WeatherEnchanter.fallback(weather: weather)
    }
}

struct ResilientWeatherEnchanter: WeatherEnchanting {
    private let local = LocalModelWeatherEnchanter()
    private let fallback = FakeWeatherEnchanter()

    func enchantWeather(weather: WeatherSourceSignal, day: BookDay) async throws -> EnchantedWeatherSignal {
        do {
            return try await local.enchantWeather(weather: weather, day: day)
        } catch LocalModelError.missingModel {
            return try await fallback.enchantWeather(weather: weather, day: day)
        }
    }
}

enum WonderCompassFallbackChooser {
    static func choose(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) -> ReferenceSnippet {
        let relevant = BookReferenceCatalog.relevantWonderCompassSnippets(
            for: day,
            inputs: inputs,
            limit: max(1, candidates.count)
        )
        return relevant.first { selected in
            candidates.contains(where: { $0.id == selected.id })
        } ?? candidates.first ?? BookReferenceCatalog.relevantWonderCompassSnippet(for: day, inputs: inputs)
    }
}

struct LocalModelWonderCompassChooser: WonderCompassPassageChoosing {
    func chooseWonderCompassSnippet(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) async throws -> ReferenceSnippet {
        let report = LocalModelManager.report()
        guard report.isReady else {
            throw LocalModelError.missingModel(report)
        }

        let prompt = LocalModelManager.wonderCompassSelectionPrompt(
            for: day,
            inputs: inputs,
            candidates: candidates
        )
        let previewID = candidates.first?.id
            ?? BookReferenceCatalog.relevantWonderCompassSnippet(for: day, inputs: inputs).id
        return candidates.first(where: { prompt.contains($0.id) && $0.id == previewID })
            ?? WonderCompassFallbackChooser.choose(day: day, inputs: inputs, candidates: candidates)
    }
}

struct FakeWonderCompassChooser: WonderCompassPassageChoosing {
    func chooseWonderCompassSnippet(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) async throws -> ReferenceSnippet {
        try await Task.sleep(nanoseconds: 250_000_000)
        return WonderCompassFallbackChooser.choose(day: day, inputs: inputs, candidates: candidates)
    }
}

struct ResilientWonderCompassChooser: WonderCompassPassageChoosing {
    private let local = LocalModelWonderCompassChooser()
    private let fallback = FakeWonderCompassChooser()

    func chooseWonderCompassSnippet(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) async throws -> ReferenceSnippet {
        do {
            return try await local.chooseWonderCompassSnippet(day: day, inputs: inputs, candidates: candidates)
        } catch LocalModelError.missingModel {
            return try await fallback.chooseWonderCompassSnippet(day: day, inputs: inputs, candidates: candidates)
        }
    }
}

struct LocalModelBraider: Braider {
    func braid(day: BookDay) async throws -> BookPage {
        let report = LocalModelManager.report()
        guard report.isReady else {
            throw LocalModelError.missingModel(report)
        }

        let prompt = LocalModelManager.bookOfYouBraidPrompt(for: day)
        let preview = prompt
            .components(separatedBy: .newlines)
            .prefix(18)
            .joined(separator: "\n")

        return BookPage(
            type: .bookOfYou,
            promptText: "The Simulator verified the local model hook.",
            userInput: "Gemma is installed and the Book can prepare a clean braid prompt.\n\nThe iOS Simulator stops here because MLX generation needs real device Metal. On iPhone or iPad, this same handoff goes through Gemma.\n\n\(preview)",
            tags: ["braid", "local-model-ready", "mlx-hook"],
            usedInBookOfYou: true
        )
    }
}

struct FakeBraider: Braider {
    func braid(day: BookDay) async throws -> BookPage {
        try await Task.sleep(nanoseconds: 900_000_000)

        let fragments = day.capturedPages.sorted { $0.createdAt < $1.createdAt }

        var paragraphs: [String] = []

        guard !fragments.isEmpty else {
            paragraphs.append("The day arrived without a full weather report, which is still a kind of weather. The Book left the window cracked and listened anyway.")
            paragraphs.append("The Book kept the page: a day still gathering its first true sentence.")
            return BookPage(
                type: .bookOfYou,
                promptText: "The Book braided today.",
                userInput: paragraphs.joined(separator: "\n\n"),
                tags: ["braid", "fallback-braider"],
                usedInBookOfYou: true
            )
        }

        let opening = fragments.prefix(2).map { narrativeHint(for: $0) }.joined(separator: " ")
        paragraphs.append("The day began with \(opening.lowercased()). The Book did not make a list of it. It set the pieces near each other and waited for them to admit they belonged.")

        let middle = fragments.dropFirst(2).prefix(4).map { narrativeHint(for: $0) }
        if middle.isEmpty {
            paragraphs.append("There was not a crowd of pages, but there was enough: one true scrap, one small weather, one place where attention refused to leave empty-handed.")
        } else {
            paragraphs.append(middle.joined(separator: " ") + " None of it needed to become impressive before it could become part of the day.")
        }

        if fragments.count > 6 {
            let late = fragments.dropFirst(6).map { narrativeHint(for: $0) }.joined(separator: " ")
            paragraphs.append("Later, the margins kept gathering: \(late.lowercased()). The story widened, but it stayed close to the floorboards.")
        }

        paragraphs.append("The Book kept the page: \(closingNoun(for: fragments)) held together long enough to be remembered.")

        return BookPage(
            type: .bookOfYou,
            promptText: "The Book braided today.",
            userInput: paragraphs.joined(separator: "\n\n"),
            tags: ["braid", "fallback-braider"],
            usedInBookOfYou: true
        )
    }

    private func narrativeHint(for page: BookPage) -> String {
        let text = page.userInput
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let clipped: String
        if text.count > 120 {
            let end = text.index(text.startIndex, offsetBy: 120)
            clipped = text[..<end].trimmingCharacters(in: .whitespacesAndNewlines) + "..."
        } else {
            clipped = text
        }

        switch page.type {
        case .mood:
            return clipped.isEmpty ? "an unnamed inner weather" : "an inner weather of \(clipped)"
        case .souvenir:
            return clipped.isEmpty ? "a souvenir still forming" : "a souvenir about \(clipped)"
        case .rest:
            return clipped.isEmpty ? "a request for rest" : "rest appearing as \(clipped)"
        case .body:
            return clipped.isEmpty ? "the body lowering a lamp" : "the body saying \(clipped)"
        case .fuel:
            return clipped.isEmpty ? "a plate note entering Vellum's chart" : "Vellum noting \(clipped)"
        case .weather:
            return clipped.isEmpty ? "weather at the window" : "weather answering as \(clipped)"
        case .location:
            return clipped.isEmpty ? "a place entering the margins" : "a place marked by \(clipped)"
        case .wonderCompass:
            return clipped.isEmpty ? "a compass passage" : "the Compass offering \(clipped)"
        case .lore:
            return clipped.isEmpty ? "a bit of lore knocking softly" : "the Labyrinth whispering \(clipped)"
        case .patreon:
            return clipped.isEmpty ? "a found article" : "a found article carrying \(clipped)"
        case .illustration:
            return clipped.isEmpty ? "an illustration surfaced" : "an illustration holding \(clipped)"
        case .illuminatedPhoto:
            return clipped.isEmpty ? "a photo found in the margins" : "a photo becoming \(clipped)"
        case .narrativeOS:
            return clipped.isEmpty ? "a story thread waking" : "a story thread tugging \(clipped)"
        case .gossip:
            return clipped.isEmpty ? "a rumor moving in the margins" : "the margins reporting \(clipped)"
        case .facultyResearch:
            return clipped.isEmpty ? "a faculty research note" : "faculty research finding \(clipped)"
        case .supportGuild:
            return clipped.isEmpty ? "the Support Guild comparing charts" : "the Support Guild connecting \(clipped)"
        case .quip:
            return clipped.isEmpty ? "a quip lighting a match" : "a quip insisting \(clipped)"
        case .aboutYou:
            return clipped.isEmpty ? "one fact about the keeper" : "the keeper answering \(clipped)"
        case .bookOfYou:
            return clipped.isEmpty ? "an earlier braid" : "an earlier braid remembering \(clipped)"
        }
    }

    private func closingNoun(for fragments: [BookPage]) -> String {
        if fragments.contains(where: { $0.type == .rest || $0.tags.contains("rest") }) {
            return "a quieter day"
        }
        if fragments.contains(where: { $0.type == .illuminatedPhoto || $0.type == .souvenir }) {
            return "one bright fragment"
        }
        if fragments.contains(where: { $0.type == .wonderCompass || $0.type == .lore || $0.type == .narrativeOS || $0.type == .gossip }) {
            return "one true thread"
        }
        return "the ordinary"
    }
}

struct ResilientBraider: Braider {
    private let local = LocalModelBraider()
    private let fallback = FakeBraider()

    func braid(day: BookDay) async throws -> BookPage {
        do {
            return try await local.braid(day: day)
        } catch LocalModelError.missingModel {
            var page = try await fallback.braid(day: day)
            page.promptText = "The Book braided today with its handcrafted fallback."
            page.tags.append("local-model-missing")
            return page
        }
    }
}

enum BookStore {
    static let schemaVersion = 2
    static let fileName = "book-days.json"

    struct Archive: Codable, Equatable {
        var schemaVersion: Int
        var generatedAt: Date
        var days: [BookDay]
    }

    enum LoadSource: String, Equatable {
        case versionedArchive
        case legacyDayArray
        case emptyArchive
        case fallbackToday
    }

    struct Report: Equatable {
        var schemaVersion: Int
        var storagePath: String
        var dayCount: Int
        var pageCount: Int
        var todayID: String
        var todayPageCount: Int
        var todayBookOfYouCount: Int
        var loadSource: LoadSource
        var lastError: String?
    }

    private static var overrideFileURL: URL?
    private static var lastLoadSource: LoadSource = .fallbackToday
    private static var lastError: String?

    static var fileURL: URL {
        if let overrideFileURL {
            return overrideFileURL
        }
        let baseURL = InsideCoverStore.containerURL
            ?? FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return baseURL.appendingPathComponent(fileName)
    }

    static func withStorageURL<T>(_ url: URL, perform work: () throws -> T) rethrows -> T {
        let previousURL = overrideFileURL
        overrideFileURL = url
        defer {
            overrideFileURL = previousURL
        }
        return try work()
    }

    static func loadDays() -> [BookDay] {
        do {
            let data = try Data(contentsOf: fileURL)
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            if let archive = try? decoder.decode(Archive.self, from: data) {
                lastLoadSource = .versionedArchive
                lastError = nil
                return normalizedDays(archive.days)
            }

            let legacyDays = try decoder.decode([BookDay].self, from: data)
            let days = normalizedDays(legacyDays)
            lastLoadSource = .legacyDayArray
            lastError = nil
            try saveDays(days)
            return days
        } catch {
            if FileManager.default.fileExists(atPath: fileURL.path) {
                lastError = error.localizedDescription
                lastLoadSource = .fallbackToday
            } else {
                lastError = nil
                lastLoadSource = .emptyArchive
            }
            return [BookDay.today()]
        }
    }

    static func saveDays(_ days: [BookDay]) throws {
        try FileManager.default.createDirectory(
            at: fileURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let archive = Archive(
            schemaVersion: schemaVersion,
            generatedAt: Date(),
            days: normalizedDays(days)
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(archive)
        try data.write(to: fileURL, options: [.atomic])
        lastLoadSource = .versionedArchive
        lastError = nil
    }

    static func today(from days: [BookDay], now: Date = Date(), calendar: Calendar = .current) -> BookDay {
        let id = BookDay.id(for: now, calendar: calendar)
        return days.first { $0.id == id } ?? .day(containing: now, calendar: calendar)
    }

    static func upsert(_ day: BookDay, in days: [BookDay]) -> [BookDay] {
        var updatedDays = days
        if let index = updatedDays.firstIndex(where: { $0.id == day.id }) {
            updatedDays[index] = day
        } else {
            updatedDays.append(day)
        }
        return normalizedDays(updatedDays)
    }

    static func report(for days: [BookDay], now: Date = Date(), calendar: Calendar = .current) -> Report {
        let today = today(from: days, now: now, calendar: calendar)
        let pageCount = days.reduce(0) { count, day in count + day.pages.count }
        return Report(
            schemaVersion: schemaVersion,
            storagePath: fileURL.path,
            dayCount: days.count,
            pageCount: pageCount,
            todayID: today.id,
            todayPageCount: today.pages.count,
            todayBookOfYouCount: today.pages.filter { $0.type == .bookOfYou }.count,
            loadSource: lastLoadSource,
            lastError: lastError
        )
    }

    private static func normalizedDays(_ days: [BookDay], calendar: Calendar = .current) -> [BookDay] {
        var merged: [String: BookDay] = [:]
        for var day in days {
            let dayID = BookDay.id(for: day.date, calendar: calendar)
            day.id = dayID
            day.date = calendar.startOfDay(for: day.date)
            day.pages = day.pages.sorted { $0.createdAt < $1.createdAt }

            if var existing = merged[dayID] {
                existing.pages.append(contentsOf: day.pages)
                existing.pages = uniquePages(existing.pages).sorted { $0.createdAt < $1.createdAt }
                merged[dayID] = existing
            } else {
                day.pages = uniquePages(day.pages)
                merged[dayID] = day
            }
        }

        let today = BookDay.today(calendar: calendar)
        if merged[today.id] == nil {
            merged[today.id] = today
        }

        return merged.values.sorted { $0.date < $1.date }
    }

    private static func uniquePages(_ pages: [BookPage]) -> [BookPage] {
        var seen = Set<String>()
        return pages.filter { page in
            seen.insert(page.id).inserted
        }
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
