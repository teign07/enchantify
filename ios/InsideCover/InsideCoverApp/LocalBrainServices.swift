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
#if canImport(MLXLLM)
import MLXLLM
#endif
#if canImport(MLXVLM)
import MLXVLM
#endif
#if canImport(MLXLMCommon)
import MLXLMCommon
#endif
#if canImport(MLXLMTokenizers)
import MLXLMTokenizers
#endif
#if canImport(MLXLMHFAPI)
import MLXLMHFAPI
#endif
#if canImport(MLX)
import MLX
#endif

#if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
enum LocalBrainGateError: LocalizedError {
    case busy

    var errorDescription: String? {
        "The Book is already writing. Let that ink dry first."
    }
}

actor LocalBrainInferenceGate {
    static let shared = LocalBrainInferenceGate()

    private let cacheLimit = 8 * 1024 * 1024
    private let memoryLimit = 1_850 * 1024 * 1024
    private var isRunning = false

    func run<T>(
        label: String,
        promptCharacters: Int,
        presentation: LocalBrainPresentation = .live,
        operation: () async throws -> T
    ) async throws -> T {
        try await enter(label: label, promptCharacters: promptCharacters)
        appLog.info("Local brain starting \(label, privacy: .public); prompt characters: \(promptCharacters)")
        if presentation == .readingRoom {
            NotificationCenter.default.post(name: .localBrainDidWake, object: nil)
        }
        AppMemoryLedger.record("\(label)-gate-enter")
        Memory.cacheLimit = cacheLimit
        Memory.memoryLimit = memoryLimit
        Memory.clearCache()
        let before = Memory.snapshot()
        defer {
            let after = Memory.snapshot()
            appLog.info("Local brain finished \(label, privacy: .public); active: \(after.activeMemory); cache: \(after.cacheMemory); peak: \(after.peakMemory); before active: \(before.activeMemory)")
            Memory.clearCache()
            AppMemoryLedger.record("\(label)-gate-exit")
            if presentation == .readingRoom {
                NotificationCenter.default.post(name: .localBrainDidRest, object: nil)
            }
            leave()
        }
        return try await operation()
    }

    private func enter(label: String, promptCharacters: Int) async throws {
        if isRunning {
            postWorkState(isWorking: true, label: "busy", promptCharacters: 0, queuedCount: 0)
            throw LocalBrainGateError.busy
        }
        isRunning = true
        postWorkState(isWorking: true, label: label, promptCharacters: promptCharacters, queuedCount: 0)
    }

    private func leave() {
        isRunning = false
        postWorkState(isWorking: false, label: nil, promptCharacters: 0, queuedCount: 0)
    }

    private nonisolated func postWorkState(
        isWorking: Bool,
        label: String?,
        promptCharacters: Int,
        queuedCount: Int
    ) {
        NotificationCenter.default.post(
            name: .localBrainWorkDidChange,
            object: LocalBrainWorkSnapshot(
                isWorking: isWorking,
                label: label,
                promptCharacters: promptCharacters,
                queuedCount: queuedCount
            )
        )
    }
}

enum MLXBookBraiderMode {
    case bookOfYou
    case task
}

struct MLXBookBraider: Braider {
    var maxTokens = 340
    var mode: MLXBookBraiderMode = .bookOfYou
    var instructions = Self.bookOfYouInstructions

    func braid(day: BookDay) async throws -> BookPage {
        guard let modelDirectory = LocalModelManager.activeModelDirectory else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        let prompt: String
        switch mode {
        case .bookOfYou:
            prompt = LocalModelManager.bookOfYouBraidPrompt(for: day)
        case .task:
            prompt = LocalModelManager.taskPrompt(for: day)
        }

        let response = try await LocalBrainInferenceGate.shared.run(label: "braid", promptCharacters: prompt.count) {
            try await Device.withDefaultDevice(.gpu) {
                let container = try await LLMModelFactory.shared.loadContainer(
                    from: modelDirectory,
                    using: TokenizersLoader()
                )
                let session = ChatSession(
                    container,
                    instructions: instructions,
                    generateParameters: GenerateParameters(
                        maxTokens: maxTokens,
                        maxKVSize: 2_048,
                        temperature: 0.68,
                        topP: 0.9,
                        prefillStepSize: 256
                    )
                )
                return try await session.respond(to: prompt)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        guard !response.isEmpty else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        return BookPage(
            type: .bookOfYou,
            promptText: "The local Book brain braided today.",
            userInput: response,
            tags: ["braid", "local-model", "mlx", "gemma"],
            usedInBookOfYou: true
        )
    }

    static let bookOfYouInstructions = """
    You are The Book inside ReEnchanted. You braid kept private real-life pages into a grounded, literary Book of You entry.
    Use only the supplied kept pages. Do not diagnose, moralize, invent completed actions, or speak as a generic assistant.
    Write a small narrative with a beginning, a turn, and a landing. Do not list. Do not copy long phrases back verbatim.
    Keep it warm, vivid, playful, and true.
    """

    static let weatherInstructions = """
    You are the Weather Page inside ReEnchanted.
    Follow the supplied weather task exactly. Write one enchanted sentence and one plain weather sentence.
    Keep real weather legible. Do not mention sensors, APIs, exact location, or generic assistant language.
    """

    static let photoIlluminationInstructions = """
    You are Penny Blackletter, field-note scribe for The Academy of Unlikely Arts.
    Follow the supplied photo-marginalia task exactly. Return strict JSON only.
    Use only the supplied local photo facts. Do not invent names, relationships, places, brands, events, or unseen details.
    """
}

struct MLXWonderCompassChooser: WonderCompassPassageChoosing {
    func chooseWonderCompassSnippet(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) async throws -> ReferenceSnippet {
        let prompt = LocalModelManager.wonderCompassSelectionPrompt(
            for: day,
            inputs: inputs,
            candidates: candidates
        )

        guard let modelDirectory = LocalModelManager.activeModelDirectory else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        let response = try await LocalBrainInferenceGate.shared.run(label: "wonder-compass", promptCharacters: prompt.count) {
            try await Device.withDefaultDevice(.gpu) {
                let container = try await LLMModelFactory.shared.loadContainer(
                    from: modelDirectory,
                    using: TokenizersLoader()
                )
                let session = ChatSession(
                    container,
                    instructions: """
                    You are the Wonder Compass librarian inside ReEnchanted.
                    Choose one supplied passage ID for the user's real day. Reply only with the exact ID.
                    """,
                    generateParameters: GenerateParameters(
                        maxTokens: 32,
                        maxKVSize: 2_048,
                        temperature: 0.2,
                        topP: 0.75,
                        prefillStepSize: 256
                    )
                )
                return try await session.respond(to: prompt)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        if let exact = candidates.first(where: { $0.id == response }) {
            return exact
        }

        let loweredResponse = response.lowercased()
        if let embedded = candidates.first(where: { loweredResponse.contains($0.id.lowercased()) }) {
            return embedded
        }

        return WonderCompassFallbackChooser.choose(day: day, inputs: inputs, candidates: candidates)
    }
}

struct MLXWeatherEnchanter: WeatherEnchanting {
    func enchantWeather(weather: WeatherSourceSignal, day: BookDay) async throws -> EnchantedWeatherSignal {
        var weatherDay = BookDay(id: day.id, date: day.date, pages: [])
        weatherDay.pages = [
            BookPage(
                type: .weather,
                promptText: "Write a Weather Page that keeps the real forecast legible.",
                userInput: [
                    "Weather source: \(weather.source)",
                    "Raw weather: \(weather.phrase)",
                    "Current temperature: \(weather.currentTemperature ?? "unknown")",
                    "Forecast: \(weather.forecast ?? "unknown")",
                    "Style: one enchanted sentence, then one plain weather sentence. No sensors, no exact location, no generic assistant voice."
                ].joined(separator: "\n"),
                tags: ["weather", "open-meteo", "gemma"],
                sourceID: "weather-page",
                origin: .imported,
                privacy: .publicReference
            )
        ]

        let page = try await MLXBookBraider(
            maxTokens: 72,
            mode: .task,
            instructions: MLXBookBraider.weatherInstructions
        ).braid(day: weatherDay)
        let response = page.userInput.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !response.isEmpty else {
            return WeatherEnchanter.fallback(weather: weather)
        }

        return EnchantedWeatherSignal(
            summary: weather.phrase,
            enchantified: response,
            selector: "gemma-braid",
            symbolName: weather.conditionSymbolName
        )
    }
}

struct MLXStoryPageWriter: StoryPageWriting {
    func write(surface: SurfacePage) async throws -> StoryPageProse {
        guard let modelDirectory = LocalModelManager.activeModelDirectory else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        let draft = StoryPageSceneDraft(surface: surface)
        let prompt = StoryPagePromptBuilder.prompt(for: draft)
        let response = try await LocalBrainInferenceGate.shared.run(label: "story-page", promptCharacters: prompt.count) {
            try await Device.withDefaultDevice(.gpu) {
                let container = try await LLMModelFactory.shared.loadContainer(
                    from: modelDirectory,
                    using: TokenizersLoader()
                )
                let session = ChatSession(
                    container,
                    instructions: StoryPagePromptBuilder.instructions,
                    generateParameters: GenerateParameters(
                        maxTokens: 360,
                        maxKVSize: 1_024,
                        temperature: 0.72,
                        topP: 0.9,
                        prefillStepSize: 128
                    )
                )
                return try await session.respond(to: prompt)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        return StoryPageProseParser.parse(response, fallback: draft)
    }
}

struct MLXStoryPageResultWriter: StoryPageResultWriting {
    func write(context: StoryPageResultContext) async throws -> String {
        guard let modelDirectory = LocalModelManager.activeModelDirectory else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        let prompt = StoryPageResultPromptBuilder.prompt(for: context)
        let response = try await LocalBrainInferenceGate.shared.run(label: "story-result", promptCharacters: prompt.count) {
            try await Device.withDefaultDevice(.gpu) {
                let container = try await LLMModelFactory.shared.loadContainer(
                    from: modelDirectory,
                    using: TokenizersLoader()
                )
                let session = ChatSession(
                    container,
                    instructions: StoryPageResultPromptBuilder.instructions,
                    generateParameters: GenerateParameters(
                        maxTokens: 240,
                        maxKVSize: 1_024,
                        temperature: 0.7,
                        topP: 0.9,
                        prefillStepSize: 128
                    )
                )
                return try await session.respond(to: prompt)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        let cleaned = StoryPageResultPromptBuilder.clean(response)
        return cleaned.nonEmpty ?? context.fallbackResult
    }
}

protocol GossipPageWriting {
    func write(surface: SurfacePage) async throws -> String
}

struct MLXGossipPageWriter: GossipPageWriting {
    func write(surface: SurfacePage) async throws -> String {
        guard let modelDirectory = LocalModelManager.activeModelDirectory else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        let prompt = GossipPagePromptBuilder.prompt(for: surface)
        let response = try await LocalBrainInferenceGate.shared.run(label: "gossip-page", promptCharacters: prompt.count) {
            try await Device.withDefaultDevice(.gpu) {
                let container = try await LLMModelFactory.shared.loadContainer(
                    from: modelDirectory,
                    using: TokenizersLoader()
                )
                let session = ChatSession(
                    container,
                    instructions: GossipPagePromptBuilder.instructions,
                    generateParameters: GenerateParameters(
                        maxTokens: 420,
                        maxKVSize: 2_048,
                        temperature: 0.76,
                        topP: 0.9,
                        prefillStepSize: 256
                    )
                )
                return try await session.respond(to: prompt)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        return GossipPagePromptBuilder.clean(response, fallback: surface.payload.body)
    }
}

struct FakeGossipPageWriter: GossipPageWriting {
    func write(surface: SurfacePage) async throws -> String {
        try await Task.sleep(nanoseconds: 250_000_000)
        guard let clippings = surface.payload.metadata["realInterestClippings"]?.nonEmpty else {
            return surface.payload.body
        }
        return """
        \(surface.payload.body)

        From the ordinary world:
        \(clippings)
        """
    }
}

protocol PhotoIlluminationAnalyzing {
    func analyze(photo: UIImage) async throws -> PhotoAnalysis
}

struct GemmaPhotoIlluminationAnalyzer: PhotoIlluminationAnalyzing {
    func analyze(photo: UIImage) async throws -> PhotoAnalysis {
        if LocalModelManager.canAttemptVisionPhotoIllumination {
            do {
                return try await VLMPhotoIlluminationAnalyzer().analyze(photo: photo)
            } catch {
                appLog.error("Vision Gemma photo illumination fell back to caption path: \(error.localizedDescription, privacy: .public)")
            }
        }

        return try await CaptionSeedPhotoIlluminationAnalyzer().analyze(photo: photo)
    }
}

struct CaptionSeedPhotoIlluminationAnalyzer: PhotoIlluminationAnalyzing {
    func analyze(photo: UIImage) async throws -> PhotoAnalysis {
        let seed = try await VisionPhotoCaptioner().caption(photo: photo.downsampledForLocalBrain(maxSide: 512))
        let fallback = PhotoAnalysis.fallback(for: seed)
        var day = BookDay(id: "photo-illumination-\(UUID().uuidString)", date: Date(), pages: [])
        day.pages = [
            BookPage(
                type: .souvenir,
                promptText: "Write Penny Blackletter marginalia JSON from local photo facts.",
                userInput: PhotoIlluminationPromptBuilder.prompt(for: seed),
                tags: ["photo", "illumination", "vision-caption", "gemma"],
                sourceID: "illuminated-photos",
                origin: .imported,
                privacy: .privateLocal
            )
        ]

        let page = try await MLXBookBraider(
            maxTokens: 220,
            mode: .task,
            instructions: MLXBookBraider.photoIlluminationInstructions
        ).braid(day: day)
        return PhotoAnalysisValidator.decodeAndValidate(page.userInput, fallback: fallback)
    }
}

enum PhotoIlluminationPromptBuilder {
    static func prompt(for seed: PhotoCaptionSeed) -> String {
        let labels = seed.labels.prefix(12).joined(separator: ", ")
        return """
        You are Penny Blackletter, field-note scribe for The Academy of Unlikely Arts.
        Write lively marginalia for an illuminated photo page using ONLY the local photo facts below.
        Do not mention anything outside these facts, except "The Book" in closing_line.
        Refer to people only as "the subject" or "good company." Never guess names, identities, relationships, exact locations, brands, or events.

        LOCAL PHOTO FACTS:
        - scene: \(seed.scene)
        - likely setting: \(seed.setting)
        - main subject: \(seed.primarySubject)
        - likely visible labels: \(labels)
        - people count: \(seed.peopleCount)
        - face count: \(seed.faceCount)
        - orientation: \(seed.orientation.rawValue)
        - light: \(seed.brightness)
        - color mood: \(seed.colorMood)
        - atmosphere: \(seed.atmosphere)
        - composition: \(seed.composition)
        - visible text: \(seed.visibleText.isEmpty ? "none detected" : seed.visibleText)
        - suggested_template: \(seed.suggestedTemplate.rawValue)

        PENNY'S VOICE:
        - observant, dry, affectionate, a little odd.
        - Make objects seem to have tiny jobs, opinions, or responsibilities.
        - Prefer concrete nouns plus small active verbs.
        - Good: "Blue light kept watch", "Grass, gossiping underfoot", "One chair held the treaty".
        - Bad: "Nice outdoor scene", "A pleasant memory", "Beautiful moment", "Photo looks warm".
        - No generic inspiration. No greeting-card wisdom. No assistant voice.

        RULES:
        - Every line names one visible fact from the list.
        - Use the atmosphere as tone, but keep details anchored to visible facts.
        - If visible text is present, you may quote one or two exact words from it.
        - Short, dry, affectionate, slightly odd, and specific.
        - If the facts are sparse, keep the caption simple.
        - Give at least three observation_list items a verb.
        - field_note under 8 words.
        - stamp_label 2-3 words, title-like, no names.
        - observation_list exactly 5 items, each under 6 words.
        - closing_line under 10 words and include "The Book kept".
        - souvenir_candidates exactly 2 items, each under 16 words.
        - suggested_template must be exactly "\(seed.suggestedTemplate.rawValue)".
        Return ONLY this JSON:
        {
          "scene": "one plain sentence: what is literally in the photo facts",
          "motifs": ["3-5 one-word tags"],
          "mood": "2-3 words",
          "suggested_template": "\(seed.suggestedTemplate.rawValue)",
          "marginalia": {
            "field_note": "under 8 words, odd and concrete",
            "stamp_label": "2-3 words, title-like, no names",
            "observation_list": ["5 items, each under 6 words, concrete and active"],
            "closing_line": "under 10 words, includes The Book kept"
          },
          "souvenir_candidates": ["two specific photo-fact lines under 16 words"]
        }

        EXAMPLE STYLE FROM SPARSE FACTS:
        Facts: labels water, boat, sky, bright light; people 0.
        {"scene":"A bright landscape photo with water, boat, and sky.","motifs":["water","boat","sky","light"],"mood":"salt and bright","suggested_template":"\(seed.suggestedTemplate.rawValue)","marginalia":{"field_note":"Boat, practicing patience.","stamp_label":"Dockside Census","observation_list":["Water held the minutes","Sky widened its pockets","Boat waited without complaint","Bright light kept watch","Edges smelled faintly of salt"],"closing_line":"The Book kept the page: tide listened."},"souvenir_candidates":["The water arranged its evidence in plain sight.","A boat waited there like patience had a hull."]}
        """
    }
}

struct VLMPhotoIlluminationAnalyzer: PhotoIlluminationAnalyzing {
    func analyze(photo: UIImage) async throws -> PhotoAnalysis {
        guard let modelDirectory = LocalModelManager.activeModelDirectory else {
            throw LocalModelError.missingModel(LocalModelManager.report())
        }

        let downsampled = photo.downsampledForLocalBrain(maxSide: 336)
        appLog.info("Photo illumination image downsampled from \(Int(photo.size.width))x\(Int(photo.size.height)) to \(Int(downsampled.size.width))x\(Int(downsampled.size.height))")
        let image = try UserInput.Image.ciImage(ciImage(from: downsampled))
        let prompt = LocalModelManager.photoIlluminationPrompt
        let response = try await LocalBrainInferenceGate.shared.run(label: "photo-illumination", promptCharacters: prompt.count) {
            try await Device.withDefaultDevice(.gpu) {
                let container = try await VLMModelFactory.shared.loadContainer(
                    from: modelDirectory,
                    using: TokenizersLoader()
                )
                let session = ChatSession(
                    container,
                    instructions: """
                    You are Penny Blackletter inside ReEnchanted.
                    Return only strict JSON. Do not include markdown, commentary, or names.
                    """,
                    generateParameters: GenerateParameters(
                        maxTokens: 180,
                        maxKVSize: 1_024,
                        temperature: 0.28,
                        topP: 0.82,
                        prefillStepSize: 128
                    ),
                    processing: UserInput.Processing(resize: CGSize(width: 224, height: 224))
                )
                return try await session.respond(
                    to: prompt,
                    image: image,
                    video: nil
                )
                .trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        return PhotoAnalysisValidator.decodeAndValidate(response, fallback: .academyFallback)
    }

    private func ciImage(from image: UIImage) throws -> CIImage {
        if let ciImage = image.ciImage {
            return ciImage
        }
        if let cgImage = image.cgImage {
            return CIImage(cgImage: cgImage)
        }
        throw LocalModelError.missingModel(LocalModelManager.report())
    }
}

struct PhotoCaptionSeed: Equatable {
    var labels: [String]
    var peopleCount: Int
    var faceCount: Int
    var orientation: PhotoOrientation
    var brightness: String
    var colorMood: String
    var setting: String
    var primarySubject: String
    var atmosphere: String
    var composition: String
    var visibleText: String
    var scene: String
    var suggestedTemplate: IlluminatedTemplateID

    var motifs: [String] {
        Array((labels + [setting, primarySubject, brightness, colorMood]).map { $0.lowercased() }.filter { !$0.isEmpty }.prefix(5))
    }
}

struct VisionPhotoCaptioner {
    func caption(photo: UIImage) async throws -> PhotoCaptionSeed {
        let image = photo.downsampledForLocalBrain(maxSide: 384)
        guard let cgImage = image.cgImage else {
            return Self.seed(from: [], peopleCount: 0, faceCount: 0, image: image, visibleText: "")
        }

        #if canImport(Vision)
        return try await Task.detached(priority: .userInitiated) {
            let classifications = try classify(cgImage: cgImage)
            async let people = countPeople(cgImage: cgImage)
            async let faces = countFaces(cgImage: cgImage)
            async let visibleText = recognizeText(cgImage: cgImage)
            return Self.seed(
                from: classifications,
                peopleCount: await people,
                faceCount: await faces,
                image: image,
                visibleText: await visibleText
            )
        }.value
        #else
        return Self.seed(from: [], peopleCount: 0, faceCount: 0, image: image, visibleText: "")
        #endif
    }

    #if canImport(Vision)
    private func classify(cgImage: CGImage) throws -> [String] {
        var labels: [String] = []
        let request = VNClassifyImageRequest { request, _ in
            let observations = (request.results as? [VNClassificationObservation]) ?? []
            labels = observations
                .filter { $0.confidence >= 0.16 }
                .prefix(8)
                .flatMap { observation in
                    observation.identifier
                        .replacingOccurrences(of: "_", with: " ")
                        .split(separator: ",")
                        .map { String($0).trimmingCharacters(in: .whitespacesAndNewlines) }
                }
        }
        try VNImageRequestHandler(cgImage: cgImage).perform([request])
        return labels
    }

    private func countPeople(cgImage: CGImage) async -> Int {
        await withCheckedContinuation { continuation in
            let request = VNDetectHumanRectanglesRequest { request, _ in
                continuation.resume(returning: (request.results as? [VNHumanObservation] ?? []).count)
            }
            try? VNImageRequestHandler(cgImage: cgImage).perform([request])
        }
    }

    private func countFaces(cgImage: CGImage) async -> Int {
        await withCheckedContinuation { continuation in
            let request = VNDetectFaceRectanglesRequest { request, _ in
                continuation.resume(returning: (request.results as? [VNFaceObservation] ?? []).count)
            }
            try? VNImageRequestHandler(cgImage: cgImage).perform([request])
        }
    }

    private func recognizeText(cgImage: CGImage) async -> String {
        await withCheckedContinuation { continuation in
            let request = VNRecognizeTextRequest { request, _ in
                let observations = (request.results as? [VNRecognizedTextObservation]) ?? []
                let words = observations
                    .compactMap { $0.topCandidates(1).first?.string }
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty }
                    .prefix(4)
                continuation.resume(returning: words.joined(separator: " | "))
            }
            request.recognitionLevel = .fast
            request.usesLanguageCorrection = false
            try? VNImageRequestHandler(cgImage: cgImage).perform([request])
        }
    }
    #endif

    private static func seed(from rawLabels: [String], peopleCount: Int, faceCount: Int, image: UIImage, visibleText: String = "") -> PhotoCaptionSeed {
        let labels = Array(NSOrderedSet(array: rawLabels.map(normalizedLabel)).compactMap { $0 as? String }.prefix(8))
        let orientation: PhotoOrientation = image.size.width > image.size.height * 1.12 ? .landscape : (image.size.height > image.size.width * 1.12 ? .portrait : .square)
        let brightness = image.averageBrightnessLabel
        let colorMood = image.dominantColorMood
        let template = template(for: labels, peopleCount: peopleCount, faceCount: faceCount, brightness: brightness)
        let setting = settingLine(for: labels, template: template)
        let primarySubject = subjectLine(for: labels, peopleCount: peopleCount, faceCount: faceCount, template: template)
        let atmosphere = atmosphereLine(labels: labels, brightness: brightness, colorMood: colorMood, template: template)
        let composition = compositionLine(orientation: orientation, peopleCount: peopleCount, faceCount: faceCount, labels: labels)
        let scene = sceneLine(labels: labels, peopleCount: peopleCount, faceCount: faceCount, brightness: brightness, colorMood: colorMood, orientation: orientation, setting: setting, primarySubject: primarySubject)
        return PhotoCaptionSeed(
            labels: labels.isEmpty ? ["ordinary", "detail", "light"] : labels,
            peopleCount: peopleCount,
            faceCount: faceCount,
            orientation: orientation,
            brightness: brightness,
            colorMood: colorMood,
            setting: setting,
            primarySubject: primarySubject,
            atmosphere: atmosphere,
            composition: composition,
            visibleText: visibleText,
            scene: scene,
            suggestedTemplate: template
        )
    }

    private static func normalizedLabel(_ value: String) -> String {
        value
            .lowercased()
            .replacingOccurrences(of: " indoor", with: "")
            .replacingOccurrences(of: " outdoor", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func template(for labels: [String], peopleCount: Int, faceCount: Int, brightness: String) -> IlluminatedTemplateID {
        let joined = labels.joined(separator: " ")
        if joined.contains("cat") || joined.contains("dog") || joined.contains("pet") || joined.contains("animal") || joined.contains("rabbit") {
            return .creatureComfort
        }
        if joined.contains("boat") || joined.contains("water") || joined.contains("sea") || joined.contains("harbor") || joined.contains("dock") {
            return .harborFieldNote
        }
        if peopleCount > 0 || faceCount > 0 {
            return .goodCompany
        }
        if joined.contains("room") || joined.contains("furniture") || joined.contains("table") || joined.contains("kitchen") || joined.contains("house") {
            return .homeVessel
        }
        if brightness == "low light" || joined.contains("bed") || joined.contains("blanket") {
            return .restAndQuiet
        }
        return .academyFieldStudy
    }

    private static func settingLine(for labels: [String], template: IlluminatedTemplateID) -> String {
        let joined = labels.joined(separator: " ")
        switch template {
        case .harborFieldNote:
            return "water, sky, or dockside air"
        case .creatureComfort:
            return "close domestic comfort"
        case .goodCompany:
            return joined.contains("outdoor") || joined.contains("sky") ? "outside with good company" : "near good company"
        case .homeVessel:
            return "a lived-in room or household surface"
        case .restAndQuiet:
            return "a quiet place with softened edges"
        case .academyFieldStudy:
            if joined.contains("tree") || joined.contains("plant") || joined.contains("flower") || joined.contains("grass") {
                return "greenery or outdoor detail"
            }
            if joined.contains("food") || joined.contains("meal") || joined.contains("drink") {
                return "food, drink, or table evidence"
            }
            return "an ordinary scene with visible evidence"
        }
    }

    private static func subjectLine(for labels: [String], peopleCount: Int, faceCount: Int, template: IlluminatedTemplateID) -> String {
        let visiblePeople = max(peopleCount, faceCount)
        if visiblePeople > 1 {
            return "good company in the frame"
        }
        if visiblePeople == 1 {
            return "the subject in the frame"
        }
        let joined = labels.joined(separator: " ")
        let candidates = [
            "cat", "dog", "rabbit", "bird", "boat", "water", "sky", "flower", "plant",
            "tree", "table", "chair", "food", "cup", "book", "car", "building", "lamp"
        ]
        if let match = candidates.first(where: { joined.contains($0) }) {
            return match
        }
        switch template {
        case .harborFieldNote:
            return "the water or vessel"
        case .creatureComfort:
            return "the creature"
        case .homeVessel:
            return "the household evidence"
        case .restAndQuiet:
            return "the quiet detail"
        default:
            return labels.first ?? "the ordinary detail"
        }
    }

    private static func atmosphereLine(labels: [String], brightness: String, colorMood: String, template: IlluminatedTemplateID) -> String {
        let joined = labels.joined(separator: " ")
        if template == .goodCompany {
            return brightness == "bright light" ? "open, social, and bright" : "close, human, and held"
        }
        if template == .creatureComfort {
            return "soft, near, and trust-shaped"
        }
        if template == .harborFieldNote {
            if joined.contains("fog") || brightness == "low light" {
                return "salted, hushed, and watchful"
            }
            return "wide, weathered, and salt-bright"
        }
        if template == .homeVessel {
            return "busy, sheltered, and lived-in"
        }
        if template == .restAndQuiet {
            return "low, gentle, and unhurried"
        }
        if joined.contains("flower") || joined.contains("plant") || colorMood == "green" {
            return "green, patient, and quietly alive"
        }
        if brightness == "bright light" {
            return "clear, awake, and lightly insistent"
        }
        if brightness == "low light" {
            return "dim, close, and secretive"
        }
        return "ordinary, attentive, and waiting"
    }

    private static func compositionLine(orientation: PhotoOrientation, peopleCount: Int, faceCount: Int, labels: [String]) -> String {
        let visiblePeople = max(peopleCount, faceCount)
        if visiblePeople > 0 {
            return visiblePeople == 1 ? "the subject is a central anchor" : "good company anchors the frame"
        }
        let joined = labels.joined(separator: " ")
        if joined.contains("close-up") || joined.contains("macro") {
            return "close-up detail fills the frame"
        }
        switch orientation {
        case .landscape:
            return "wide frame with room for weather"
        case .portrait:
            return "upright frame with a clear focal point"
        case .square:
            return "balanced frame, centered and still"
        }
    }

    private static func sceneLine(
        labels: [String],
        peopleCount: Int,
        faceCount: Int,
        brightness: String,
        colorMood: String,
        orientation: PhotoOrientation,
        setting: String,
        primarySubject: String
    ) -> String {
        let visiblePeople = max(peopleCount, faceCount)
        let objectPhrase = labels.prefix(4).joined(separator: ", ")
        let peoplePhrase = visiblePeople > 0 ? "\(visiblePeople) \(visiblePeople == 1 ? "person" : "people")" : "no counted people"
        return "A \(orientation.rawValue) photo in \(setting), with \(peoplePhrase), \(primarySubject), \(objectPhrase.isEmpty ? "ordinary details" : objectPhrase), \(brightness), and \(colorMood) tones."
    }
}

private extension PhotoAnalysis {
    static func fallback(for seed: PhotoCaptionSeed) -> PhotoAnalysis {
        switch seed.suggestedTemplate {
        case .creatureComfort:
            return PhotoAnalysis(
                scene: seed.scene,
                motifs: seed.motifs.isEmpty ? ["creature", "rest", "soft"] : seed.motifs,
                mood: "soft and near",
                suggestedTemplate: .creatureComfort,
                marginalia: PhotoMarginalia(
                    fieldNote: "Small creature, official business.",
                    stampLabel: "Pawlogy 101",
                    observationList: [
                        "Fur keeping office",
                        "Soft light reporting",
                        "Rest, visibly employed",
                        "Small details holding still",
                        "The frame stayed gentle"
                    ],
                    closingLine: "The Book kept the page: rest reported."
                ),
                souvenirCandidates: [
                    "A small creature made rest look like important work.",
                    "The softest detail in the frame took charge."
                ]
            )
        case .goodCompany:
            return PhotoAnalysis(
                scene: seed.scene,
                motifs: seed.motifs.isEmpty ? ["company", "light", "kept"] : seed.motifs,
                mood: "warm and bright",
                suggestedTemplate: .goodCompany,
                marginalia: PhotoMarginalia(
                    fieldNote: "Good company, plainly present.",
                    stampLabel: "Joy Census",
                    observationList: [
                        "Good company in frame",
                        "Light doing friendly work",
                        "The subject stayed visible",
                        "Color holding its ground",
                        "The day leaned closer"
                    ],
                    closingLine: "The Book kept the page: company stayed."
                ),
                souvenirCandidates: [
                    "The frame held good company long enough to matter.",
                    "Light made a small record of the subject."
                ]
            )
        case .harborFieldNote:
            return .harborFallback
        case .restAndQuiet:
            return PhotoAnalysis(
                scene: seed.scene,
                motifs: seed.motifs.isEmpty ? ["rest", "quiet", "light"] : seed.motifs,
                mood: "low and gentle",
                suggestedTemplate: .restAndQuiet,
                marginalia: PhotoMarginalia(
                    fieldNote: "Quiet arrived and took notes.",
                    stampLabel: "Rest Office",
                    observationList: [
                        "Soft light, not hurrying",
                        "Edges going quiet",
                        "Texture doing calm work",
                        "Nothing urgent volunteered",
                        "The frame breathed low"
                    ],
                    closingLine: "The Book kept the page: quiet stayed."
                ),
                souvenirCandidates: [
                    "The quiet did not ask to be improved.",
                    "Soft light made a small treaty with the room."
                ]
            )
        case .homeVessel:
            return PhotoAnalysis(
                scene: seed.scene,
                motifs: seed.motifs.isEmpty ? ["home", "objects", "light"] : seed.motifs,
                mood: "busy and warm",
                suggestedTemplate: .homeVessel,
                marginalia: PhotoMarginalia(
                    fieldNote: "Home, conducting quiet experiments.",
                    stampLabel: "Vessel Study",
                    observationList: [
                        "Objects keeping stations",
                        "Light finding corners",
                        "Color doing household work",
                        "Surfaces holding history",
                        "The room stayed available"
                    ],
                    closingLine: "The Book kept the page: home answered."
                ),
                souvenirCandidates: [
                    "The room held its evidence like a practiced vessel.",
                    "Home made a small museum of ordinary things."
                ]
            )
        case .academyFieldStudy:
            var fallback = PhotoAnalysis.academyFallback
            fallback.scene = seed.scene
            fallback.motifs = seed.motifs.isEmpty ? fallback.motifs : seed.motifs
            return fallback
        }
    }
}

private extension UIImage {
    func downsampledForLocalBrain(maxSide: CGFloat) -> UIImage {
        let longestSide = max(size.width, size.height)
        guard longestSide > maxSide else { return self }
        let ratio = maxSide / longestSide
        let targetSize = CGSize(width: max(1, size.width * ratio), height: max(1, size.height * ratio))
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        return UIGraphicsImageRenderer(size: targetSize, format: format).image { _ in
            draw(in: CGRect(origin: .zero, size: targetSize))
        }
    }

    var averageBrightnessLabel: String {
        guard let cgImage else { return "soft light" }
        let extent = CGSize(width: 1, height: 1)
        let renderer = UIGraphicsImageRenderer(size: extent)
        let sample = renderer.image { context in
            UIColor.white.setFill()
            context.fill(CGRect(origin: .zero, size: extent))
            UIImage(cgImage: cgImage).draw(in: CGRect(origin: .zero, size: extent))
        }
        guard let pixel = sample.cgImage?.dataProvider?.data,
              let bytes = CFDataGetBytePtr(pixel) else {
            return "soft light"
        }
        let brightness = (Double(bytes[0]) + Double(bytes[1]) + Double(bytes[2])) / 3.0
        if brightness < 80 { return "low light" }
        if brightness > 185 { return "bright light" }
        return "soft light"
    }

    var dominantColorMood: String {
        guard let cgImage else { return "warm" }
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 1, height: 1))
        let sample = renderer.image { _ in
            UIImage(cgImage: cgImage).draw(in: CGRect(x: 0, y: 0, width: 1, height: 1))
        }
        guard let pixel = sample.cgImage?.dataProvider?.data,
              let bytes = CFDataGetBytePtr(pixel) else {
            return "warm"
        }
        let red = Int(bytes[0])
        let green = Int(bytes[1])
        let blue = Int(bytes[2])
        if blue > red + 20 && blue > green { return "blue" }
        if green > red && green > blue { return "green" }
        if red > blue + 18 { return "warm" }
        return "muted"
    }
}
#endif

#if canImport(Photos) && canImport(UIKit)
protocol PhotoLibraryServicing {
    func authorizationStatus() -> PHAuthorizationStatus
    func requestAuthorization() async -> PHAuthorizationStatus
    func fetchRecentPhotoAssets(lookbackHours: Int, favoritesOnly: Bool, includeScreenshots: Bool) async throws -> [PHAsset]
    func requestThumbnail(for asset: PHAsset, targetSize: CGSize) async throws -> UIImage
    func requestFullImage(for asset: PHAsset, targetSize: CGSize?) async throws -> UIImage
}

struct PhotoLibraryService: PhotoLibraryServicing {
    func authorizationStatus() -> PHAuthorizationStatus {
        PHPhotoLibrary.authorizationStatus(for: .readWrite)
    }

    func requestAuthorization() async -> PHAuthorizationStatus {
        await PHPhotoLibrary.requestAuthorization(for: .readWrite)
    }

    func fetchRecentPhotoAssets(lookbackHours: Int, favoritesOnly: Bool, includeScreenshots: Bool) async throws -> [PHAsset] {
        let status = authorizationStatus()
        guard status == .authorized || status == .limited else { return [] }

        let options = PHFetchOptions()
        let cutoff = Date().addingTimeInterval(-Double(max(1, lookbackHours)) * 3600)
        var predicates: [NSPredicate] = [
            NSPredicate(format: "mediaType == %d", PHAssetMediaType.image.rawValue),
            NSPredicate(format: "creationDate >= %@", cutoff as NSDate)
        ]
        if favoritesOnly {
            predicates.append(NSPredicate(format: "favorite == YES"))
        }
        options.predicate = NSCompoundPredicate(andPredicateWithSubpredicates: predicates)
        options.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
        options.fetchLimit = 80

        let fetched = PHAsset.fetchAssets(with: options)
        var assets: [PHAsset] = []
        fetched.enumerateObjects { asset, _, _ in
            if !includeScreenshots && asset.mediaSubtypes.contains(.photoScreenshot) {
                return
            }
            let shortestSide = min(asset.pixelWidth, asset.pixelHeight)
            guard shortestSide >= 800 else { return }
            assets.append(asset)
        }
        return assets
    }

    func requestThumbnail(for asset: PHAsset, targetSize: CGSize) async throws -> UIImage {
        try await requestImage(for: asset, targetSize: targetSize, deliveryMode: .opportunistic)
    }

    func requestFullImage(for asset: PHAsset, targetSize: CGSize?) async throws -> UIImage {
        try await requestImage(
            for: asset,
            targetSize: targetSize ?? CGSize(width: asset.pixelWidth, height: asset.pixelHeight),
            deliveryMode: .highQualityFormat
        )
    }

    private func requestImage(for asset: PHAsset, targetSize: CGSize, deliveryMode: PHImageRequestOptionsDeliveryMode) async throws -> UIImage {
        try await withCheckedThrowingContinuation { continuation in
            let options = PHImageRequestOptions()
            options.deliveryMode = deliveryMode
            options.resizeMode = .fast
            options.isNetworkAccessAllowed = false
            options.isSynchronous = false

            PHImageManager.default().requestImage(
                for: asset,
                targetSize: targetSize,
                contentMode: .aspectFill,
                options: options
            ) { image, info in
                if let error = info?[PHImageErrorKey] as? Error {
                    continuation.resume(throwing: error)
                    return
                }
                guard let image else {
                    continuation.resume(throwing: LocalModelError.missingModel(LocalModelManager.report()))
                    return
                }
                continuation.resume(returning: image)
            }
        }
    }
}

protocol PhotoCandidateScoring {
    func scoreAssets(_ assets: [PHAsset], history: IlluminatedPhotoHistory) -> [PhotoCandidate]
}

struct PhotoCandidateScorer: PhotoCandidateScoring {
    func scoreAssets(_ assets: [PHAsset], history: IlluminatedPhotoHistory) -> [PhotoCandidate] {
        let now = Date()
        return assets.map { asset in
            var score = 0.0
            var reasons: [String] = []

            if asset.isFavorite {
                score += 5
                reasons.append("favorite")
            }
            if let creationDate = asset.creationDate {
                let age = now.timeIntervalSince(creationDate)
                if age <= 24 * 3600 {
                    score += 4
                    reasons.append("last 24 hours")
                } else if age <= 72 * 3600 {
                    score += 3
                    reasons.append("last 72 hours")
                }
            }
            if min(asset.pixelWidth, asset.pixelHeight) >= 1000 {
                score += 2
                reasons.append("good dimensions")
            }
            let aspect = Double(max(asset.pixelWidth, asset.pixelHeight)) / Double(max(1, min(asset.pixelWidth, asset.pixelHeight)))
            if aspect <= 2.2 {
                score += 2
                reasons.append("usable aspect")
            }
            if asset.location != nil {
                score += 1
                reasons.append("has place")
            }
            if asset.mediaSubtypes.contains(.photoScreenshot) {
                score -= 10
                reasons.append("screenshot")
            }
            if history.keptAssetIdentifiers.contains(asset.localIdentifier) {
                score -= 8
                reasons.append("already kept")
            }
            if history.dismissedAssetIdentifiers.contains(asset.localIdentifier) {
                score -= 7
                reasons.append("recently dismissed")
            }
            if history.proposedAssetIdentifiers.contains(asset.localIdentifier) {
                score -= 6
                reasons.append("already proposed")
            }
            if let lastSuggestedAt = history.lastSuggestedAtByAsset[asset.localIdentifier] {
                let age = now.timeIntervalSince(lastSuggestedAt)
                if age <= 7 * 24 * 3600 {
                    score -= 12
                    reasons.append("suggested this week")
                } else if age <= 30 * 24 * 3600 {
                    score -= 4
                    reasons.append("suggested this month")
                }
            }
            if min(asset.pixelWidth, asset.pixelHeight) < 800 {
                score -= 4
                reasons.append("small")
            }

            return PhotoCandidate(
                id: UUID(),
                assetLocalIdentifier: asset.localIdentifier,
                creationDate: asset.creationDate,
                pixelWidth: asset.pixelWidth,
                pixelHeight: asset.pixelHeight,
                isFavorite: asset.isFavorite,
                score: score,
                reasons: reasons,
                discoveredAt: now
            )
        }
        .sorted { $0.score > $1.score }
    }
}

func preferredIlluminatedPhotoCandidate(
    from candidates: [PhotoCandidate],
    history: IlluminatedPhotoHistory,
    now: Date = Date(),
    allowStaleFallback: Bool = false
) -> PhotoCandidate? {
    let fresh = candidates.first { candidate in
        if history.keptAssetIdentifiers.contains(candidate.assetLocalIdentifier) { return false }
        if history.dismissedAssetIdentifiers.contains(candidate.assetLocalIdentifier) { return false }
        if history.proposedAssetIdentifiers.contains(candidate.assetLocalIdentifier) { return false }
        if let lastSuggestedAt = history.lastSuggestedAtByAsset[candidate.assetLocalIdentifier],
           now.timeIntervalSince(lastSuggestedAt) <= 7 * 24 * 3600 {
            return false
        }
        return true
    }
    guard fresh == nil, allowStaleFallback else {
        return fresh
    }
    return candidates.first { candidate in
        !history.keptAssetIdentifiers.contains(candidate.assetLocalIdentifier)
            && !history.dismissedAssetIdentifiers.contains(candidate.assetLocalIdentifier)
    }
}
#endif

struct AppBraider: Braider {
    let local: Braider
    private let fallback = FakeBraider()

    func braid(day: BookDay) async throws -> BookPage {
        do {
            return try await local.braid(day: day)
        } catch {
            appLog.error("Local braid fell back: \(error.localizedDescription, privacy: .public)")
            var page = try await fallback.braid(day: day)
            page.promptText = "The local brain dropped its pencil. The Book kept the page safe."
            page.tags.append("local-model-fallback")
            return page
        }
    }
}

struct AppWonderCompassChooser: WonderCompassPassageChoosing {
    let local: WonderCompassPassageChoosing
    private let fallback = FakeWonderCompassChooser()

    func chooseWonderCompassSnippet(
        day: BookDay,
        inputs: BookSourceInputs,
        candidates: [ReferenceSnippet]
    ) async throws -> ReferenceSnippet {
        do {
            return try await local.chooseWonderCompassSnippet(day: day, inputs: inputs, candidates: candidates)
        } catch {
            appLog.error("Wonder Compass selection fell back: \(error.localizedDescription, privacy: .public)")
            return try await fallback.chooseWonderCompassSnippet(day: day, inputs: inputs, candidates: candidates)
        }
    }
}

struct AppWeatherEnchanter: WeatherEnchanting {
    let local: WeatherEnchanting
    private let fallback = FakeWeatherEnchanter()

    func enchantWeather(weather: WeatherSourceSignal, day: BookDay) async throws -> EnchantedWeatherSignal {
        do {
            return try await local.enchantWeather(weather: weather, day: day)
        } catch {
            return try await fallback.enchantWeather(weather: weather, day: day)
        }
    }
}

struct RealInterestGossipClipping: Equatable {
    var interest: String
    var fact: String
    var sourceName: String
    var sourceURL: String

    var promptLine: String {
        "\(interest): \(fact) [\(sourceName)]"
    }
}

struct RealInterestGossipSearcher {
    private struct DuckDuckGoResponse: Decodable {
        var abstractText: String?
        var abstractURL: String?
        var heading: String?
        var relatedTopics: [RelatedTopic]?

        enum CodingKeys: String, CodingKey {
            case abstractText = "AbstractText"
            case abstractURL = "AbstractURL"
            case heading = "Heading"
            case relatedTopics = "RelatedTopics"
        }
    }

    private struct RelatedTopic: Decodable {
        var text: String?
        var firstURL: String?
        var topics: [RelatedTopic]?

        enum CodingKeys: String, CodingKey {
            case text = "Text"
            case firstURL = "FirstURL"
            case topics = "Topics"
        }
    }

    func clippings(from facts: [SelfFact], dayID: String, slotID: String) async -> [RealInterestGossipClipping] {
        let interests = selectedInterests(from: facts, dayID: dayID, slotID: slotID)
        var clippings: [RealInterestGossipClipping] = []
        for interest in interests {
            guard let clipping = try? await search(interest: interest) else { continue }
            clippings.append(clipping)
            if clippings.count >= 2 { break }
        }
        return clippings
    }

    private func selectedInterests(from facts: [SelfFact], dayID: String, slotID: String) -> [String] {
        let candidates = facts
            .filter { fact in
                fact.questionID.hasPrefix("interest-")
                    && fact.usePermission != .doNotUse
                    && !fact.answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            }
            .flatMap { fact in
                splitInterests(fact.answer)
            }
            .reduce(into: [String]()) { unique, interest in
                if !unique.contains(where: { $0.localizedCaseInsensitiveCompare(interest) == .orderedSame }) {
                    unique.append(interest)
                }
            }
        guard !candidates.isEmpty else { return [] }
        return candidates
            .sorted { left, right in
                stableIndex(for: "\(dayID)-\(slotID)-\(left)", count: 10_000)
                    < stableIndex(for: "\(dayID)-\(slotID)-\(right)", count: 10_000)
            }
            .prefix(4)
            .map(\.self)
    }

    private func splitInterests(_ answer: String) -> [String] {
        let separators = CharacterSet(charactersIn: ",;\n")
        return answer
            .components(separatedBy: separators)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty && $0.count >= 3 && $0.count <= 80 }
    }

    private func search(interest: String) async throws -> RealInterestGossipClipping? {
        var components = URLComponents(string: "https://api.duckduckgo.com/")!
        components.queryItems = [
            URLQueryItem(name: "q", value: interest),
            URLQueryItem(name: "format", value: "json"),
            URLQueryItem(name: "no_redirect", value: "1"),
            URLQueryItem(name: "no_html", value: "1"),
            URLQueryItem(name: "skip_disambig", value: "1")
        ]
        guard let url = components.url else { return nil }
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        request.setValue("ReEnchanted/1.0", forHTTPHeaderField: "User-Agent")
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { return nil }
        let decoded = try JSONDecoder().decode(DuckDuckGoResponse.self, from: data)
        let sourceURL = decoded.abstractURL?.nonEmpty
            ?? decoded.relatedTopics?.compactMap(\.firstURL).first?.nonEmpty
            ?? "https://duckduckgo.com/?q=\(interest.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? interest)"
        let sourceName = decoded.heading?.nonEmpty ?? "DuckDuckGo"
        let fact = decoded.abstractText?.nonEmpty
            ?? decoded.relatedTopics?.flatMap { flatten($0) }.compactMap(\.text).first?.nonEmpty
        guard let fact else { return nil }
        return RealInterestGossipClipping(
            interest: interest,
            fact: fact.bookPreviewSentenceLimit(2),
            sourceName: sourceName,
            sourceURL: sourceURL
        )
    }

    private func flatten(_ topic: RelatedTopic) -> [RelatedTopic] {
        [topic] + (topic.topics ?? []).flatMap(flatten)
    }

    private func stableIndex(for key: String, count: Int) -> Int {
        guard count > 0 else { return 0 }
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in key.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return Int(hash % UInt64(count))
    }
}

extension SurfacePage {
    func withRealInterestGossip(_ clippings: [RealInterestGossipClipping]) -> SurfacePage {
        guard !clippings.isEmpty else { return self }
        let clippingLines = clippings.map { clipping in
            "- \(clipping.promptLine)"
        }.joined(separator: "\n")
        let sourceLines = clippings.map { clipping in
            "\(clipping.interest): \(clipping.sourceURL)"
        }.joined(separator: "\n")
        var metadata = payload.metadata
        metadata["realInterestClippings"] = clippingLines
        metadata["realInterestSources"] = sourceLines
        metadata["realInterestCount"] = "\(clippings.count)"
        return SurfacePage(
            id: id,
            type: type,
            sourceID: sourceID,
            intent: intent,
            renderStyle: renderStyle,
            score: min(score + clippings.count * 4, 96),
            reason: reason,
            prompt: prompt,
            detail: detail,
            payload: BookPagePayload(
                headline: payload.headline,
                body: payload.body,
                metadata: metadata
            )
        )
    }

    func preparedStoryPageCopy(prose: StoryPageProse, slotID: String) -> SurfacePage {
        var metadata = payload.metadata
        metadata["slotID"] = slotID
        metadata["storyScene"] = prose.scene
        metadata["storyResultSliceOfLife"] = prose.results["sliceoflife"] ?? ""
        metadata["storyResultProgressArc"] = prose.results["progressarc"] ?? ""
        metadata["storyResultSurprise"] = prose.results["surprise"] ?? ""
        for choice in prose.choices {
            let prefix: String
            switch choice.id {
            case "sliceoflife":
                prefix = "storyChoiceSliceOfLife"
            case "progressarc":
                prefix = "storyChoiceProgressArc"
            case "surprise":
                prefix = "storyChoiceSurprise"
            default:
                continue
            }
            metadata["\(prefix)Title"] = choice.title
            metadata["\(prefix)Prompt"] = choice.prompt
            metadata["\(prefix)Effect"] = choice.effectLine
        }
        metadata["proseStatus"] = "generated"
        return SurfacePage(
            id: id,
            type: type,
            sourceID: sourceID,
            intent: intent,
            renderStyle: renderStyle,
            score: score,
            reason: reason,
            prompt: prompt,
            detail: detail,
            payload: BookPagePayload(
                headline: payload.headline,
                body: prose.scene.bookPreviewSentenceLimit(2),
                metadata: metadata
            )
        )
    }

    func preparedGossipPageCopy(prose: String, slotID: String) -> SurfacePage {
        var metadata = payload.metadata
        metadata["slotID"] = slotID
        metadata["gossipProse"] = prose
        metadata["proseStatus"] = "generated"
        return SurfacePage(
            id: id,
            type: type,
            sourceID: sourceID,
            intent: intent,
            renderStyle: renderStyle,
            score: score,
            reason: reason,
            prompt: prompt,
            detail: detail,
            payload: BookPagePayload(
                headline: payload.headline,
                body: prose,
                metadata: metadata
            )
        )
    }

    func enchantedWeatherCopy(_ signal: EnchantedWeatherSignal, weather: WeatherSourceSignal) -> SurfacePage {
        let rawParts = [
            weather.currentTemperature.map { "Now: \($0)" },
            weather.forecast.map { "Forecast: \($0)" }
        ].compactMap(\.self)
        let rawLine = rawParts.isEmpty ? weather.phrase : rawParts.joined(separator: " | ")
        var metadata = payload.metadata
        metadata["selector"] = signal.selector
        metadata["symbol"] = signal.symbolName
        metadata["rawWeather"] = weather.phrase
        return SurfacePage(
            type: type,
            sourceID: sourceID,
            intent: intent,
            renderStyle: renderStyle,
            score: score,
            reason: reason,
            prompt: prompt,
            detail: rawLine,
            payload: BookPagePayload(
                headline: payload.headline,
                body: "\(signal.enchantified)\n\nWeather: \(rawLine)",
                metadata: metadata
            )
        )
    }

    func storyContinuationCopy(context: StoryPageContinuationContext) -> SurfacePage {
        var metadata = payload.metadata
        metadata["storyContinuationContext"] = context.promptContext
        metadata["storyTurnCount"] = "\(context.turns.count + 1)"
        metadata.removeValue(forKey: "storyScene")
        metadata.removeValue(forKey: "storyResultSliceOfLife")
        metadata.removeValue(forKey: "storyResultProgressArc")
        metadata.removeValue(forKey: "storyResultSurprise")
        metadata["proseStatus"] = "continuing"
        return SurfacePage(
            id: "\(id)-continued-\(context.turns.count + 1)",
            type: type,
            sourceID: sourceID,
            intent: intent,
            renderStyle: renderStyle,
            score: score,
            reason: reason,
            prompt: prompt,
            detail: detail,
            payload: BookPagePayload(
                headline: payload.headline,
                body: payload.body,
                metadata: metadata
            )
        )
    }
}
