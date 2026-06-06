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

struct CapturePageSheet: View {
    let surface: SurfacePage
    let isLocalBrainWorking: Bool
    let onReplaceIlluminatedSurface: (SurfacePage) -> Void
    let onSave: (SurfacePage, String, [String]) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selectedWeather = ""
    @State private var text = ""
    @State private var manualPhotoImage: UIImage?
    @State private var manualPhotoDraft: IlluminatedPhotoDraft?
    @State private var isLoadingManualPhoto = false
    @State private var isChoosingBookPhoto = false
    @State private var isSavingIlluminatedArtifact = false
    @State private var illuminationMessage = "Penny can choose from recent photos, or you can hand her one yourself."
    @State private var renderedIlluminatedPageURL: URL?
    @State private var selectedStoryChoice: StoryPageChoiceDraft?
    @State private var storyTurns: [StoryPageSessionTurn] = []
    @State private var isContinuingStoryPage = false
    @State private var isGeneratingStoryResult = false
    @State private var generatingStoryResultChoiceID: String?
    @State private var storyContinuationMessage = ""
    @State private var proofPhotoImage: UIImage?
    @State private var proofPhotoURL: URL?
    @State private var proofPhotoMessage = ""
    @AppStorage("illuminatedPhotoHistory") private var illuminatedPhotoHistoryData = "{}"
    #if canImport(PhotosUI)
    @State private var selectedPhotoItem: PhotosPickerItem?
    #endif

    private let weatherOptions = ["Fog", "Rain", "Static", "Heavy", "Bright", "Restless", "Soft", "Numb", "Stormy", "Clearing"]

    private var isPreparedPage: Bool {
        surface.intent == .importReference ||
            surface.renderStyle == .illuminatedPhoto ||
            surface.type == .narrativeOS ||
            surface.type == .gossip ||
            surface.renderStyle == .gentleTranslation ||
            surface.origin == .imported
    }

    private var isCompassPracticePage: Bool {
        surface.type == .wonderCompass && surface.payload.metadata["compassStep"] != nil
    }

    private var allowsCompassPhotoProof: Bool {
        surface.type == .wonderCompass && surface.payload.metadata["proofKind"] == "sentence-or-photo"
    }

    private var preparedPageLabel: String {
        if surface.renderStyle == .gentleTranslation {
            return "Private translation"
        }
        return surface.payload.headline
    }

    private var externalURL: URL? {
        guard let value = surface.payload.metadata["url"] else {
            return nil
        }
        return URL(string: value)
    }

    private var weatherSymbolName: String? {
        guard surface.type == .weather else { return nil }
        return surface.payload.metadata["symbol"]
    }

    private var illustrationAssetName: String? {
        guard surface.type == .illustration else { return nil }
        let value = surface.payload.metadata["assetName"] ?? ""
        return value.isEmpty ? nil : value
    }

    private var illuminatedDraft: IlluminatedPhotoDraft? {
        if let manualPhotoDraft {
            return manualPhotoDraft
        }
        guard surface.type == .illuminatedPhoto,
              let sourceAssetName = surface.payload.metadata["sourceAssetName"] else {
            return nil
        }
        let fallback = FakePhotoIlluminationAnalyzer.analyze(assetName: sourceAssetName)
        let analysis = PhotoAnalysis.fromSurfaceMetadata(surface.payload.metadata, fallback: fallback)
        return IlluminatedPageComposer.compose(
            analysis: analysis,
            sourceAssetName: sourceAssetName,
            seed: abs(surface.id.hashValue),
            assetLocalIdentifier: surface.payload.metadata["assetLocalIdentifier"]
        )
    }

    private var illuminatedArtifactURL: URL? {
        if let renderedIlluminatedPageURL,
           FileManager.default.fileExists(atPath: renderedIlluminatedPageURL.path) {
            return renderedIlluminatedPageURL
        }
        if let renderedPath = surface.payload.metadata["renderedPreviewPath"],
           FileManager.default.fileExists(atPath: renderedPath) {
            return URL(fileURLWithPath: renderedPath)
        }
        return nil
    }

    private var effectiveSurface: SurfacePage {
        currentIlluminatedSurface ?? surface
    }

    private var effectiveProofSurface: SurfacePage {
        guard surface.type == .wonderCompass,
              let proofPhotoURL else {
            return effectiveSurface
        }
        var metadata = surface.payload.metadata
        metadata["proofImagePath"] = proofPhotoURL.path
        metadata["proofCaption"] = surface.payload.metadata["playfulMissionTitle"] ?? surface.payload.headline
        return SurfacePage(
            id: surface.id,
            type: surface.type,
            sourceID: surface.sourceID,
            intent: surface.intent,
            renderStyle: surface.renderStyle,
            score: surface.score,
            reason: surface.reason,
            prompt: surface.prompt,
            detail: surface.detail,
            payload: BookPagePayload(
                headline: surface.payload.headline,
                body: surface.payload.body,
                metadata: metadata
            )
        )
    }

    private var currentIlluminatedSurface: SurfacePage? {
        guard surface.type == .illuminatedPhoto,
              let illuminatedDraft else {
            return nil
        }
        return SurfacePage.illuminatedPhotoSurface(
            draft: illuminatedDraft,
            renderedURL: illuminatedArtifactURL,
            idSuffix: "active-\(illuminatedDraft.id.uuidString)"
        )
    }

    private var articlePreviews: [(title: String, url: URL, publishedAt: String, preview: String)] {
        guard surface.type == .patreon,
              let previews = surface.payload.metadata["articlePreviews"]?.nonEmpty else {
            return []
        }

        return previews
            .split(separator: "\n")
            .compactMap { line -> (title: String, url: URL, publishedAt: String, preview: String)? in
                let parts = line.components(separatedBy: "||")
                guard parts.count >= 2,
                      let url = URL(string: parts[1].trimmingCharacters(in: .whitespacesAndNewlines)) else {
                    return nil
                }
                let title = parts[0].trimmingCharacters(in: .whitespacesAndNewlines)
                let publishedAt = parts.count > 2 ? parts[2].trimmingCharacters(in: .whitespacesAndNewlines) : ""
                let preview = parts.count > 3 ? parts[3...].joined(separator: "||").trimmingCharacters(in: .whitespacesAndNewlines) : ""
                return title.isEmpty ? nil : (title, url, publishedAt, preview)
            }
    }

    private var articleLinks: [(title: String, url: URL)] {
        guard surface.type == .patreon,
              let links = surface.payload.metadata["links"] else {
            return []
        }

        return links
            .split(separator: "\n")
            .compactMap { line -> (title: String, url: URL)? in
                let parts = line.components(separatedBy: "||")
                guard parts.count == 2,
                      let url = URL(string: parts[1].trimmingCharacters(in: .whitespacesAndNewlines)) else {
                    return nil
                }
                let title = parts[0].trimmingCharacters(in: .whitespacesAndNewlines)
                return title.isEmpty ? nil : (title, url)
            }
    }

    private var storySceneDraft: StoryPageSceneDraft? {
        guard surface.type == .narrativeOS else { return nil }
        return StoryPageSceneDraft(surface: surface)
    }

    private var activeStoryTurn: StoryPageSessionTurn? {
        storyTurns.last ?? storySceneDraft.map { StoryPageSessionTurn(draft: $0) }
    }

    private var sheetHasLocalBrainActions: Bool {
        switch surface.type {
        case .illuminatedPhoto, .narrativeOS:
            return true
        default:
            return false
        }
    }

    private var openPagePrimaryText: Color {
        BookPalette.lampGold
    }

    private var openPageSecondaryText: Color {
        BookPalette.nightText.opacity(0.86)
    }

    private var sharePageText: String {
        let marginNote = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let body: String

        if surface.type == .narrativeOS, let activeStoryTurn {
            let choiceLines = activeStoryTurn.draft.choices.map { "• \($0.kindLabel): \($0.title)" }.joined(separator: "\n")
            let selectedResult = activeStoryTurn.selectedChoice.map { choice in
                "\n\nChosen path: \(choice.title)\n\n\(activeStoryTurn.result(for: choice))"
            } ?? ""
            body = [
                activeStoryTurn.draft.scene,
                choiceLines.isEmpty ? nil : "Choices:\n\(choiceLines)",
                selectedResult.nonEmpty
            ].compactMap { $0 }.joined(separator: "\n\n")
        } else if isPreparedPage {
            body = surface.payload.body
        } else {
            body = [surface.detail, preparedInput]
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
                .joined(separator: "\n\n")
        }

        let note = marginNote.isEmpty ? "" : "\n\nMargin note: \(marginNote)"
        let source = externalURL.map { "\n\nPublic shelf: \($0.absoluteString)" } ?? ""
        return [
            surface.prompt,
            body.trimmingCharacters(in: .whitespacesAndNewlines)
        ]
            .filter { !$0.isEmpty }
            .joined(separator: "\n\n")
            + note
            + source
            + "\n\n— ReEnchanted"
    }

    @ViewBuilder
    private var pageShareControl: some View {
        if let artifactURL = illuminatedArtifactURL {
            ShareLink(item: artifactURL) {
                Label("Share page", systemImage: "square.and.arrow.up")
                    .font(.subheadline.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(BookPalette.lampGold.opacity(0.16), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(BookPalette.lampGold.opacity(0.38), lineWidth: 1)
                    }
            }
            .foregroundStyle(BookPalette.lampGold)
        } else {
            ShareLink(item: sharePageText) {
                Label("Share page", systemImage: "square.and.arrow.up")
                    .font(.subheadline.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(BookPalette.lampGold.opacity(0.16), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(BookPalette.lampGold.opacity(0.38), lineWidth: 1)
                    }
            }
            .foregroundStyle(BookPalette.lampGold)
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                BookBackground()

                ScrollView {
                    pageSheetContent
                        .padding(.horizontal, 20)
                        .padding(.top, 18)
                        .padding(.bottom, 44)
                }
                .scrollIndicators(.visible)
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Let it wait") {
                        BookFeedback.play(.dismissPage)
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Keep this page") {
                        let input = preparedInput
                        markIlluminatedDraftKept()
                        onSave(effectiveProofSurface, input, preparedTags)
                        dismiss()
                    }
                    .disabled(!canKeep)
                }
            }
            #if canImport(PhotosUI)
            .onChange(of: selectedPhotoItem) { _, newValue in
                guard let newValue else { return }
                Task {
                    if allowsCompassPhotoProof {
                        await loadCompassProofPhoto(from: newValue)
                    } else {
                        await loadManualPhoto(from: newValue)
                    }
                }
            }
            #endif
            .task {
                if surface.type == .illuminatedPhoto {
                    await prepareIlluminatedArtifactIfNeeded()
                }
                if surface.type == .narrativeOS, storyTurns.isEmpty, let storySceneDraft {
                    storyTurns = [StoryPageSessionTurn(draft: storySceneDraft)]
                }
            }
        }
    }

    @ViewBuilder
    private var pageSheetContent: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label(surface.type.title, systemImage: surface.type.symbolName)
                .font(.headline)
                .foregroundStyle(openPagePrimaryText)

            Text(surface.prompt)
                .font(.system(.title, design: .serif, weight: .semibold))
                .foregroundStyle(openPagePrimaryText)
                .shadow(color: BookPalette.lampGold.opacity(0.14), radius: 6, x: 0, y: 2)
                .fixedSize(horizontal: false, vertical: true)

            Text(surface.detail)
                .font(.body)
                .foregroundStyle(openPageSecondaryText)
                .fixedSize(horizontal: false, vertical: true)

            pageShareControl

            if isLocalBrainWorking, sheetHasLocalBrainActions {
                LocalBrainWorkingStatusCard(
                    label: "this page",
                    quip: LocalBrainQuips.lines[0],
                    startedAt: nil,
                    queuedCount: 0
                )
            }

            if isPreparedPage || isCompassPracticePage {
                preparedPageContent
            }

            if surface.type == .mood {
                moodOptions
            }

            if let externalURL {
                externalPageLink(externalURL)
            }

            if !articlePreviews.isEmpty || !articleLinks.isEmpty {
                articleLinkList
            }

            if surface.type != .narrativeOS {
                marginNoteEditor(minHeight: isPreparedPage ? 92 : (surface.type == .souvenir ? 120 : 150))
            } else {
                storyMarginNoteField
            }
        }
    }

    @ViewBuilder
    private var preparedPageContent: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let illustrationAssetName {
                Image(illustrationAssetName)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: 260)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                    }
                    .accessibilityLabel(surface.payload.headline)
            }

            if let illuminatedDraft {
                illuminatedPreview(draft: illuminatedDraft, height: 360)
            }

            if surface.type == .illuminatedPhoto {
                illuminatedPhotoActions
            }

            if let activeStoryTurn {
                storySceneView(activeStoryTurn)
            }

            if isCompassPracticePage {
                compassPracticeView
            }

            if surface.type == .supportGuild {
                supportGuildPageView
            }

            if allowsCompassPhotoProof {
                compassProofPhotoPicker
            }

            HStack(spacing: 8) {
                if let weatherSymbolName {
                    Image(systemName: weatherSymbolName)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(BookPalette.gold)
                }
                Text(preparedPageLabel)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(BookPalette.teal)
            }

            if surface.type != .narrativeOS && !isCompassPracticePage && surface.type != .supportGuild {
                Text(surface.payload.body)
                    .font(.system(.body, design: .serif))
                    .foregroundStyle(BookPalette.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(14)
        .background(BookPalette.page, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(BookPalette.ink.opacity(0.14), lineWidth: 1)
        }
    }

    private var supportGuildPageView: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(surface.payload.body)
                .font(.system(.callout, design: .serif))
                .foregroundStyle(BookPalette.ink.opacity(0.82))
                .fixedSize(horizontal: false, vertical: true)

            supportGuildDisclosure("Dr. Vellum", systemImage: "heart.text.square", value: surface.payload.metadata["vellumSection"])
            supportGuildDisclosure("Dr. Inkrest", systemImage: "cloud.sun", value: surface.payload.metadata["inkrestSection"])
            supportGuildDisclosure("Connections", systemImage: "point.3.connected.trianglepath.dotted", value: surface.payload.metadata["connectionsSection"])
            supportGuildDisclosure("Experiment", systemImage: "checklist", value: surface.payload.metadata["experimentSection"])
            supportGuildDisclosure("Safety", systemImage: "lock.shield", value: surface.payload.metadata["safetySection"])
        }
    }

    @ViewBuilder
    private func supportGuildDisclosure(_ title: String, systemImage: String, value: String?) -> some View {
        if let value = value?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty {
            DisclosureGroup {
                Text(value)
                    .font(.caption)
                    .foregroundStyle(BookPalette.ink.opacity(0.76))
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 6)
            } label: {
                Label(title, systemImage: systemImage)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(BookPalette.teal)
            }
            .padding(10)
            .background(BookPalette.paper.opacity(0.74), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(BookPalette.ink.opacity(0.12), lineWidth: 1)
            }
        }
    }

    private var compassPracticeView: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let step = surface.payload.metadata["compassStep"], step == "run" {
                compassRail("Mode", surface.payload.metadata["conciergeMode"])
                compassRail("Time", surface.payload.metadata["timeBox"])
                compassRail("Budget", surface.payload.metadata["budget"])
                compassRail("Place", surface.payload.metadata["place"])
                compassRail("Energy", surface.payload.metadata["energy"])
                compassRail("With", surface.payload.metadata["companions"])
                compassRail("Considerations", surface.payload.metadata["considerations"])
            }

            compassRail("Notice", surface.payload.metadata["spark"])
            compassRail("Destination", surface.payload.metadata["destination"])
            compassRail("Delight", surface.payload.metadata["delight"])
            compassRail("Definition", surface.payload.metadata["definition"])
            compassRail("Mission", surface.payload.metadata["mission"])
            compassRail("Souvenir", surface.payload.metadata["souvenirPrompt"])
            compassRail("Rest", surface.payload.metadata["restPrompt"])

            Text(surface.payload.body)
                .font(.system(.callout, design: .serif))
                .foregroundStyle(BookPalette.ink.opacity(0.76))
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 4)
        }
    }

    @ViewBuilder
    private func compassRail(_ title: String, _ value: String?) -> some View {
        if let value = value?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                Text(title.uppercased())
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(BookPalette.teal.opacity(0.82))
                Text(value)
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(BookPalette.ink)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(BookPalette.paper.opacity(0.74), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
    }

    private var moodOptions: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 92), spacing: 8)], spacing: 8) {
            ForEach(weatherOptions, id: \.self) { option in
                Button {
                    BookFeedback.play(.select)
                    selectedWeather = option
                } label: {
                    Text(option)
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            selectedWeather == option ? BookPalette.teal.opacity(0.18) : BookPalette.paper,
                            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
                        )
                        .overlay {
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .stroke(selectedWeather == option ? BookPalette.teal : BookPalette.ink.opacity(0.12), lineWidth: 1)
                        }
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func externalPageLink(_ url: URL) -> some View {
        Link(destination: url) {
            Label("Open the public shelf", systemImage: "arrow.up.right.square")
                .font(.subheadline.weight(.bold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(BookPalette.teal.opacity(0.14), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.teal.opacity(0.34), lineWidth: 1)
                }
        }
        .foregroundStyle(BookPalette.teal)
    }

    private var articleLinkList: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Letters on the public shelf")
                .font(.caption.weight(.bold))
                .foregroundStyle(openPageSecondaryText)

            ForEach(articlePreviews.isEmpty ? articleLinks.map { (title: $0.title, url: $0.url, publishedAt: "", preview: "") } : articlePreviews, id: \.url) { article in
                Link(destination: article.url) {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: "doc.text")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(BookPalette.gold)
                            .frame(width: 22)
                        VStack(alignment: .leading, spacing: 5) {
                            Text(article.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(BookPalette.ink)
                                .multilineTextAlignment(.leading)
                                .lineLimit(3)
                            if !article.publishedAt.isEmpty {
                                Text(article.publishedAt)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(openPageSecondaryText)
                            }
                            if !article.preview.isEmpty {
                                Text(article.preview)
                                    .font(.caption)
                                    .foregroundStyle(BookPalette.ink.opacity(0.72))
                                    .multilineTextAlignment(.leading)
                                    .lineLimit(4)
                            }
                        }
                        Spacer(minLength: 8)
                        Image(systemName: "arrow.up.right")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(BookPalette.teal)
                    }
                    .padding(12)
                    .background(BookPalette.paper.opacity(0.72), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(BookPalette.ink.opacity(0.12), lineWidth: 1)
                    }
                }
            }
        }
    }

    private func marginNoteEditor(minHeight: CGFloat) -> some View {
        TextEditor(text: $text)
            .font(.body)
            .foregroundStyle(BookPalette.ink)
            .scrollContentBackground(.hidden)
            .padding(10)
            .frame(minHeight: minHeight)
            .background(BookPalette.page, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(BookPalette.ink.opacity(0.14), lineWidth: 1)
            }
    }

    private var storyMarginNoteField: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Optional margin note")
                .font(.caption.weight(.bold))
                .foregroundStyle(openPageSecondaryText)
            TextField("Add one private note before keeping.", text: $text, axis: .vertical)
                .font(.callout)
                .foregroundStyle(BookPalette.ink)
                .lineLimit(2...4)
                .padding(12)
                .background(BookPalette.page.opacity(0.86), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.ink.opacity(0.14), lineWidth: 1)
                }
        }
    }

    @ViewBuilder
    private var compassProofPhotoPicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Proof can be one sentence, one photo, or both.")
                .font(.caption.weight(.semibold))
                .foregroundStyle(openPageSecondaryText)

            if let proofPhotoImage {
                Image(uiImage: proofPhotoImage)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: 190)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                    }
                    .accessibilityLabel("Playful mission proof photo")
            }

            #if canImport(PhotosUI)
            PhotosPicker(selection: $selectedPhotoItem, matching: .images, photoLibrary: .shared()) {
                Label(proofPhotoImage == nil ? "Add proof photo" : "Replace proof photo", systemImage: "camera")
                    .font(.subheadline.weight(.bold))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .tint(BookPalette.teal)
            #endif

            if !proofPhotoMessage.isEmpty {
                Text(proofPhotoMessage)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(BookPalette.ink.opacity(0.58))
            }
        }
        .padding(12)
        .background(BookPalette.page.opacity(0.82), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(BookPalette.ink.opacity(0.12), lineWidth: 1)
        }
    }

    @ViewBuilder
    private func illuminatedPreview(draft: IlluminatedPhotoDraft, height: CGFloat) -> some View {
        if manualPhotoDraft != nil,
           let renderedIlluminatedPageURL,
           let image = UIImage(contentsOfFile: renderedIlluminatedPageURL.path) {
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: .infinity)
                .frame(height: height)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                }
                .accessibilityLabel("Illuminated photo page draft")
        } else if let renderedPath = surface.payload.metadata["renderedPreviewPath"],
           let image = UIImage(contentsOfFile: renderedPath) {
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: .infinity)
                .frame(height: height)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                }
                .accessibilityLabel("Illuminated photo page draft")
        } else {
            IlluminatedArtifactPreview(draft: draft, sourceImage: manualPhotoImage)
                .frame(maxWidth: .infinity)
                .frame(height: height)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                }
                .accessibilityLabel("Illuminated photo page draft")
        }
    }

    @ViewBuilder
    private func storySceneView(_ turn: StoryPageSessionTurn) -> some View {
        let draft = turn.draft
        let turnNumber = storyTurns.firstIndex(where: { $0.id == turn.id }).map { $0 + 1 } ?? storyTurns.count
        VStack(alignment: .leading, spacing: 14) {
            if storyTurns.count > 1 {
                Text("Turn \(turnNumber) of \(storyTurns.count)")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(BookPalette.gold)
            }

            Text(draft.scene)
                .font(.system(.body, design: .serif))
                .foregroundStyle(BookPalette.ink)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 10) {
                Text("Choose how the page turns")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(BookPalette.ink.opacity(0.56))

                ForEach(draft.choices) { choice in
                    Button {
                        BookFeedback.play(.select)
                        withAnimation(.easeInOut(duration: 0.22)) {
                            selectedStoryChoice = choice
                            updateActiveStoryTurn(choice: choice)
                        }
                        Task { await generateStoryResultForActiveTurn(choiceID: choice.id) }
                    } label: {
                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: choice.symbolName)
                                .font(.headline.weight(.semibold))
                                .foregroundStyle(choice.tint)
                                .frame(width: 26)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(choice.kindLabel)
                                    .font(.caption2.weight(.bold))
                                    .textCase(.uppercase)
                                    .foregroundStyle(choice.tint.opacity(0.82))
                                Text(choice.title)
                                    .font(.subheadline.weight(.bold))
                                    .foregroundStyle(BookPalette.ink)
                                Text(choice.prompt)
                                    .font(.caption)
                                    .foregroundStyle(BookPalette.ink.opacity(0.66))
                            }
                            Spacer(minLength: 8)
                            if selectedStoryChoice?.id == choice.id {
                                Image(systemName: "checkmark.seal.fill")
                                    .foregroundStyle(BookPalette.teal)
                            }
                        }
                        .padding(12)
                        .background(
                            selectedStoryChoice?.id == choice.id ? choice.tint.opacity(0.16) : BookPalette.paper.opacity(0.72),
                            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
                        )
                        .overlay {
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .stroke(selectedStoryChoice?.id == choice.id ? choice.tint.opacity(0.52) : BookPalette.ink.opacity(0.12), lineWidth: 1)
                        }
                    }
                    .buttonStyle(.plain)
                    .disabled(isGeneratingStoryResult || isLocalBrainWorking)
                }
            }

            if let selectedStoryChoice {
                VStack(alignment: .leading, spacing: 8) {
                    Label("The page answers", systemImage: "sparkles")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(BookPalette.teal)
                    if isGeneratingStoryResult && generatingStoryResultChoiceID == selectedStoryChoice.id {
                        HStack(spacing: 10) {
                            ProgressView()
                                .tint(BookPalette.teal)
                            Text("The Book is answering this path in wet ink.")
                                .font(.callout.weight(.semibold))
                                .foregroundStyle(BookPalette.ink.opacity(0.72))
                        }
                    } else {
                        Text(turn.result(for: selectedStoryChoice))
                            .font(.system(.callout, design: .serif))
                            .foregroundStyle(BookPalette.ink)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .padding(12)
                .background(BookPalette.gold.opacity(0.14), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.gold.opacity(0.28), lineWidth: 1)
                }
                .transition(.opacity.combined(with: .move(edge: .bottom)))

                HStack(spacing: 10) {
                    Button {
                        BookFeedback.play(.braidStart)
                        Task { await continueStoryPage(from: draft, choice: selectedStoryChoice) }
                    } label: {
                        Label(isContinuingStoryPage ? "Ink drying..." : "Continue the scene", systemImage: "arrow.turn.down.right")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(isContinuingStoryPage || isGeneratingStoryResult || isLocalBrainWorking)

                    Button {
                        BookFeedback.play(.select)
                        text = "The Book should keep this thread here."
                    } label: {
                        Label("Keep here", systemImage: "bookmark")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }
                .font(.caption.weight(.bold))
                .tint(BookPalette.teal)
            }

            if !storyContinuationMessage.isEmpty {
                Text(storyContinuationMessage)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(BookPalette.ink.opacity(0.58))
            }
        }
    }

    @ViewBuilder
    private var illuminatedPhotoActions: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(illuminationMessage)
                .font(.caption.weight(.semibold))
                .foregroundStyle(BookPalette.ink.opacity(0.58))

            HStack(spacing: 10) {
                Button {
                    BookFeedback.play(.sourceRefresh)
                    loadSampleIllumination()
                } label: {
                    Label("Try another", systemImage: "shuffle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button {
                    BookFeedback.play(.sourceRefresh)
                    Task { await letTheBookChoosePhoto() }
                } label: {
                    Label(isChoosingBookPhoto ? "Looking..." : "Let Book choose", systemImage: "sparkle.magnifyingglass")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(isChoosingBookPhoto || isLoadingManualPhoto || isLocalBrainWorking)
            }
            .font(.caption.weight(.bold))

            HStack(spacing: 10) {
                #if canImport(PhotosUI)
                PhotosPicker(selection: $selectedPhotoItem, matching: .images, photoLibrary: .shared()) {
                    Label(isLoadingManualPhoto ? "Reading..." : "Choose myself", systemImage: "photo")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(isLoadingManualPhoto || isChoosingBookPhoto || isLocalBrainWorking)
                #endif

                Button {
                    BookFeedback.play(.openPage)
                    text = illuminatedDraft?.analysis.marginalia.observationList.joined(separator: "\n") ?? text
                } label: {
                    Label("Edit margins", systemImage: "pencil.line")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
            .font(.caption.weight(.bold))

            HStack(spacing: 10) {
                Button {
                    BookFeedback.play(.sourceRefresh)
                    Task { await saveIlluminatedArtifactToPhotos() }
                } label: {
                    Label(isSavingIlluminatedArtifact ? "Saving..." : "Save artifact", systemImage: "square.and.arrow.down")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(isSavingIlluminatedArtifact || illuminatedDraft == nil)

                if let artifactURL = illuminatedArtifactURL {
                    ShareLink(item: artifactURL) {
                        Label("Share artifact", systemImage: "square.and.arrow.up")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                } else {
                    Button {
                        BookFeedback.play(.sourceRefresh)
                        Task { await prepareIlluminatedArtifactIfNeeded(force: true) }
                    } label: {
                        Label("Prepare share", systemImage: "wand.and.sparkles")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(illuminatedDraft == nil || isLocalBrainWorking)
                }
            }
            .font(.caption.weight(.bold))
        }
        .tint(BookPalette.teal)
    }

    private func loadSampleIllumination() {
        let plate = BookReferenceCatalog.labyrinthIllustrations.randomElement()
            ?? BookReferenceCatalog.labyrinthIllustration(for: BookDay.today())
        let next = plate.assetName
        manualPhotoImage = nil
        let draft = IlluminatedPageComposer.compose(
            analysis: FakePhotoIlluminationAnalyzer.analyze(illustration: plate),
            sourceAssetName: next,
            seed: Int.random(in: 1...Int.max / 2),
            assetLocalIdentifier: "bundled-illustration:\(plate.id)"
        )
        manualPhotoDraft = draft
        renderedIlluminatedPageURL = IlluminatedPageRenderer.renderPreview(draft: draft, sourceImage: nil)
        illuminationMessage = renderedIlluminatedPageURL == nil
            ? "Penny pulled a Labyrinth illustration through the press. The plate can be prepared again."
            : "Penny pulled a Labyrinth illustration through the press."
        publishCurrentIlluminatedSurfaceIfReady()
    }

    #if canImport(PhotosUI)
    private func loadCompassProofPhoto(from item: PhotosPickerItem) async {
        proofPhotoMessage = "The Book is tucking the proof into the margin."
        guard let data = try? await item.loadTransferable(type: Data.self),
              let image = UIImage(data: data) else {
            BookFeedback.play(.error)
            proofPhotoMessage = "That photo would not open. A sentence still counts."
            return
        }
        do {
            let url = try saveCompassProofPhotoData(data)
            await MainActor.run {
                proofPhotoImage = image
                proofPhotoURL = url
                proofPhotoMessage = "Proof photo ready."
                BookFeedback.play(.select)
            }
        } catch {
            await MainActor.run {
                BookFeedback.play(.error)
                proofPhotoMessage = "The photo could not be saved. A sentence still counts."
            }
        }
    }

    private func loadManualPhoto(from item: PhotosPickerItem) async {
        guard !isLocalBrainWorking else {
            illuminationMessage = "The local brain is already writing. Let that ink dry first."
            return
        }
        isLoadingManualPhoto = true
        illuminationMessage = "Penny is reading the photograph without letting it leave the room."
        defer {
            isLoadingManualPhoto = false
        }
        guard let data = try? await item.loadTransferable(type: Data.self),
              let image = UIImage(data: data) else {
            BookFeedback.play(.error)
            illuminationMessage = "The photograph would not open. The margins stayed quiet."
            return
        }
        AppMemoryLedger.record("photo-manual-decoded")
        let analysis = await analyzeIlluminatedPhoto(image)
        AppMemoryLedger.record("photo-manual-after-gemma")
        let draft = IlluminatedPageComposer.compose(
            analysis: analysis,
            sourceAssetName: "IlluminatedPhotoSource",
            seed: data.count ^ Int(Date().timeIntervalSince1970),
            assetLocalIdentifier: "manual:\(UUID().uuidString)"
        )
        AppMemoryLedger.record("photo-manual-before-render")
        let renderedURL = IlluminatedPageRenderer.renderPreview(draft: draft, sourceImage: image)
        AppMemoryLedger.record("photo-manual-after-render")
        await MainActor.run {
            manualPhotoImage = image
            manualPhotoDraft = draft
            renderedIlluminatedPageURL = renderedURL
            illuminationMessage = renderedURL == nil
                ? "Penny wrote the margins. The rendered plate can be made again from the kept page."
                : "Penny wrote the margins. The plate is ready to keep."
            publishCurrentIlluminatedSurfaceIfReady()
            BookFeedback.play(.braidComplete)
        }
    }
    #endif

    private func saveCompassProofPhotoData(_ data: Data) throws -> URL {
        let baseURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let bundleID = Bundle.main.bundleIdentifier ?? "com.openclaw.enchantify.insidecover"
        let directory = baseURL
            .appendingPathComponent(bundleID, isDirectory: true)
            .appendingPathComponent("CompassProofs", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let filename = "compass-proof-\(UUID().uuidString).jpg"
        let url = directory.appendingPathComponent(filename)
        try data.write(to: url, options: [.atomic])
        return url
    }

    private func letTheBookChoosePhoto() async {
        #if canImport(Photos) && canImport(UIKit)
        guard !isLocalBrainWorking else {
            illuminationMessage = "The local brain is already writing. Let that ink dry first."
            return
        }
        isChoosingBookPhoto = true
        illuminationMessage = "The Book is asking the camera roll for one recent page worth keeping."
        defer { isChoosingBookPhoto = false }

        let library = PhotoLibraryService()
        let status = library.authorizationStatus()
        let finalStatus = (status == .notDetermined) ? await library.requestAuthorization() : status
        guard finalStatus == .authorized || finalStatus == .limited else {
            BookFeedback.play(.error)
            illuminationMessage = "The Book cannot see the camera roll yet. You can still choose a photo yourself."
            return
        }

        do {
            let history = decodedIlluminatedPhotoHistory()
            let assets = try await library.fetchRecentPhotoAssets(
                lookbackHours: PhotoSuggestionSettings.default.lookbackHours,
                favoritesOnly: PhotoSuggestionSettings.default.favoritesOnly,
                includeScreenshots: PhotoSuggestionSettings.default.includeScreenshots
            )
            let candidates = PhotoCandidateScorer().scoreAssets(assets, history: history)
            guard let candidate = preferredIlluminatedPhotoCandidate(from: candidates, history: history) else {
                BookFeedback.play(.error)
                illuminationMessage = "The margins are quiet. Try choosing a photo by hand."
                return
            }
            guard let asset = PHAsset.fetchAssets(withLocalIdentifiers: [candidate.assetLocalIdentifier], options: nil).firstObject else {
                BookFeedback.play(.error)
                illuminationMessage = "That photo slipped behind a shelf. Try another."
                return
            }

            let image = try await library.requestFullImage(for: asset, targetSize: CGSize(width: 1400, height: 1400))
            let analysis = await analyzeIlluminatedPhoto(image)
            let draft = IlluminatedPageComposer.compose(
                analysis: analysis,
                sourceAssetName: "IlluminatedPhotoSource",
                seed: abs(candidate.assetLocalIdentifier.hashValue ^ Int(Date().timeIntervalSince1970)),
                assetLocalIdentifier: candidate.assetLocalIdentifier
            )
            let renderedURL = IlluminatedPageRenderer.renderPreview(draft: draft, sourceImage: image)

            await MainActor.run {
                var updatedHistory = history
                updatedHistory.proposedAssetIdentifiers.insert(candidate.assetLocalIdentifier)
                updatedHistory.lastSuggestedAtByAsset[candidate.assetLocalIdentifier] = Date()
                illuminatedPhotoHistoryData = encodedIlluminatedPhotoHistory(updatedHistory)
                manualPhotoImage = image
                manualPhotoDraft = draft
                renderedIlluminatedPageURL = renderedURL
                illuminationMessage = "Penny found a recent photograph and gave it margins."
                publishCurrentIlluminatedSurfaceIfReady()
                BookFeedback.play(.braidComplete)
            }
        } catch {
            BookFeedback.play(.error)
            illuminationMessage = "The page tore while being assembled. Try again, or choose one by hand."
        }
        #else
        illuminationMessage = "This build cannot open the camera roll, but Labyrinth illustration plates still work."
        #endif
    }

    private func analyzeIlluminatedPhoto(_ image: UIImage) async -> PhotoAnalysis {
        #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
        do {
            return try await GemmaPhotoIlluminationAnalyzer().analyze(photo: image)
        } catch {
            appLog.error("Photo illumination Gemma analysis fell back: \(error.localizedDescription, privacy: .public)")
            return PhotoAnalysis.academyFallback
        }
        #else
        return PhotoAnalysis.academyFallback
        #endif
    }

    private func decodedIlluminatedPhotoHistory() -> IlluminatedPhotoHistory {
        guard let data = illuminatedPhotoHistoryData.data(using: .utf8),
              let history = try? JSONDecoder().decode(IlluminatedPhotoHistory.self, from: data) else {
            return IlluminatedPhotoHistory()
        }
        return history
    }

    private func encodedIlluminatedPhotoHistory(_ history: IlluminatedPhotoHistory) -> String {
        guard let data = try? JSONEncoder().encode(history),
              let encoded = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return encoded
    }

    @MainActor
    private func publishCurrentIlluminatedSurfaceIfReady() {
        guard let currentIlluminatedSurface,
              currentIlluminatedSurface.payload.metadata["renderedPreviewPath"]?.isEmpty == false else {
            return
        }
        onReplaceIlluminatedSurface(currentIlluminatedSurface)
    }

    @MainActor
    private func prepareIlluminatedArtifactIfNeeded(force: Bool = false) async {
        guard force || illuminatedArtifactURL == nil else {
            return
        }
        guard let illuminatedDraft else {
            return
        }
        let renderedURL = IlluminatedPageRenderer.renderPreview(draft: illuminatedDraft, sourceImage: manualPhotoImage)
        renderedIlluminatedPageURL = renderedURL
        if renderedURL == nil {
            BookFeedback.play(.error)
            illuminationMessage = "The artifact did not finish drying. Try preparing it again."
        } else if force {
            BookFeedback.play(.braidComplete)
        }
        publishCurrentIlluminatedSurfaceIfReady()
    }

    @MainActor
    private func saveIlluminatedArtifactToPhotos() async {
        isSavingIlluminatedArtifact = true
        defer { isSavingIlluminatedArtifact = false }

        await prepareIlluminatedArtifactIfNeeded()
        guard let artifactURL = illuminatedArtifactURL else {
            BookFeedback.play(.error)
            illuminationMessage = "The artifact is not ready to save yet."
            return
        }

        #if canImport(Photos)
        do {
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetCreationRequest.creationRequestForAssetFromImage(atFileURL: artifactURL)
            }
            BookFeedback.play(.keepPage)
            illuminationMessage = "The artifact is tucked into Photos."
        } catch {
            BookFeedback.play(.error)
            illuminationMessage = "Photos would not take the artifact yet. Check photo permissions, then try again."
        }
        #else
        illuminationMessage = "This build cannot save to Photos, but the artifact is prepared."
        #endif
    }

    private func markIlluminatedDraftKept() {
        guard surface.type == .illuminatedPhoto,
              let illuminatedDraft else {
            return
        }
        var history = decodedIlluminatedPhotoHistory()
        history.keptAssetIdentifiers.insert(illuminatedDraft.assetLocalIdentifier)
        illuminatedPhotoHistoryData = encodedIlluminatedPhotoHistory(history)
    }

    private func updateActiveStoryTurn(choice: StoryPageChoiceDraft) {
        guard surface.type == .narrativeOS else { return }
        if storyTurns.isEmpty, let storySceneDraft {
            storyTurns = [StoryPageSessionTurn(draft: storySceneDraft, selectedChoice: choice)]
            return
        }
        guard let lastIndex = storyTurns.indices.last else { return }
        storyTurns[lastIndex].selectedChoice = choice
    }

    @MainActor
    private func generateStoryResultForActiveTurn(choiceID: String) async {
        guard surface.type == .narrativeOS else { return }
        guard !isGeneratingStoryResult else {
            storyContinuationMessage = "The Book is already answering one path. Let that ink dry first."
            return
        }
        guard !isLocalBrainWorking else {
            storyContinuationMessage = "The local brain is already writing. Let that ink dry first."
            return
        }
        guard let turnIndex = storyTurns.indices.last,
              let choice = storyTurns[turnIndex].selectedChoice,
              choice.id == choiceID else {
            return
        }
        if storyTurns[turnIndex].generatedResults[choiceID]?.nonEmpty != nil ||
            storyTurns[turnIndex].draft.preparedResults[choiceID]?.nonEmpty != nil {
            return
        }

        isGeneratingStoryResult = true
        generatingStoryResultChoiceID = choiceID
        storyContinuationMessage = "The Book is answering the path you chose."
        defer {
            isGeneratingStoryResult = false
            generatingStoryResultChoiceID = nil
        }

        let context = StoryPageResultContext(
            previousTurns: Array(storyTurns.prefix(turnIndex)),
            draft: storyTurns[turnIndex].draft,
            selectedChoice: choice
        )

        do {
            let result: String
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            result = try await MLXStoryPageResultWriter().write(context: context)
            #else
            result = try await FakeStoryPageResultWriter().write(context: context)
            #endif
            guard storyTurns.indices.contains(turnIndex) else { return }
            storyTurns[turnIndex].generatedResults[choiceID] = result
            storyContinuationMessage = "The path has answered. You can continue, or keep the page here."
            BookFeedback.play(.braidComplete)
        } catch {
            guard storyTurns.indices.contains(turnIndex) else { return }
            storyTurns[turnIndex].generatedResults[choiceID] = context.fallbackResult
            storyContinuationMessage = "The chosen path answered softly, without waking the full local brain."
            BookFeedback.play(.error)
        }
    }

    @MainActor
    private func continueStoryPage(from draft: StoryPageSceneDraft, choice: StoryPageChoiceDraft) async {
        guard !isContinuingStoryPage, !isGeneratingStoryResult, !isLocalBrainWorking else {
            storyContinuationMessage = "The local brain is already writing. Let that ink dry first."
            return
        }
        isContinuingStoryPage = true
        storyContinuationMessage = "The Book is turning the same thread over in wet ink."
        defer { isContinuingStoryPage = false }

        let context = StoryPageContinuationContext(turns: storyTurns, currentDraft: draft, selectedChoice: choice)
        let continuationSurface = surface.storyContinuationCopy(context: context)

        do {
            let prose: StoryPageProse
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXStoryPageWriter().write(surface: continuationSurface)
            #else
            prose = try await FakeStoryPageWriter().write(surface: continuationSurface)
            #endif
            let nextSurface = continuationSurface.preparedStoryPageCopy(prose: prose, slotID: "continued-\(storyTurns.count + 1)")
            let nextDraft = StoryPageSceneDraft(surface: nextSurface)
            storyTurns.append(StoryPageSessionTurn(draft: nextDraft))
            selectedStoryChoice = nil
            storyContinuationMessage = "A new turn has surfaced from the choice you made."
            BookFeedback.play(.braidComplete)
        } catch {
            storyContinuationMessage = "The ink did not finish the next turn. The current page is still safe to keep."
            BookFeedback.play(.error)
        }
    }

    private var canKeep: Bool {
        if surface.type == .narrativeOS {
            guard !isGeneratingStoryResult else { return false }
            return storyTurns.contains { $0.selectedChoice != nil } || selectedStoryChoice != nil
        }
        if allowsCompassPhotoProof, proofPhotoURL != nil {
            return true
        }
        return isPreparedPage || !preparedInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var preparedInput: String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if surface.type == .narrativeOS {
            let turns = storyTurns.isEmpty
                ? [storySceneDraft.map { StoryPageSessionTurn(draft: $0, selectedChoice: selectedStoryChoice) }].compactMap { $0 }
                : storyTurns
            let threadText = turns.enumerated().map { index, turn in
                let choice = turn.selectedChoice
                return [
                    "Turn \(index + 1)",
                    turn.draft.scene,
                    choice.map { "Chosen path: \($0.title)" } ?? "Chosen path: unresolved",
                    choice.map { turn.result(for: $0) } ?? "The page was kept before this turn chose a path."
                ].compactMap { $0 }.joined(separator: "\n\n")
            }.joined(separator: "\n\n---\n\n")
            let marginNote = trimmed.isEmpty ? "" : "\n\nMargin note: \(trimmed)"
            return threadText + marginNote
        }
        if isPreparedPage {
            if isCompassPracticePage {
                let marginNote = trimmed.isEmpty ? "" : "\n\nMargin note: \(trimmed)"
                return compassPreparedInput + marginNote
            }
            if surface.type == .illuminatedPhoto, let illuminatedDraft {
                let manualNote = trimmed.isEmpty ? "" : "\n\nMargin note: \(trimmed)"
                let renderLine = renderedIlluminatedPageURL.map { "\n\nRendered plate: \($0.lastPathComponent)" } ?? ""
                return [
                    illuminatedDraft.analysis.scene,
                    illuminatedDraft.analysis.marginalia.fieldNote,
                    illuminatedDraft.analysis.marginalia.observationList.joined(separator: "\n"),
                    illuminatedDraft.analysis.marginalia.closingLine
                ].joined(separator: "\n\n") + renderLine + manualNote
            }
            guard !trimmed.isEmpty else {
                return surface.payload.body
            }
            return "\(surface.payload.body)\n\nMargin note: \(trimmed)"
        }
        guard surface.type == .mood, !selectedWeather.isEmpty else {
            return trimmed
        }
        if trimmed.isEmpty {
            return selectedWeather
        }
        return "\(selectedWeather): \(trimmed)"
    }

    private var compassPreparedInput: String {
        let metadata = surface.payload.metadata
        let step = metadata["compassStep"] ?? "run"
        if step == "run" {
            return [
                "Wonder Compass Run",
                "Location: \(metadata["place"] ?? "unknown")",
                "Time Limit: \(metadata["timeBox"] ?? "unknown")",
                "Energy: \(metadata["energy"] ?? "unknown")",
                "Who is with me: \(metadata["companions"] ?? "unknown")",
                "Budget: \(metadata["budget"] ?? "unknown")",
                "Special Needs/Considerations: \(metadata["considerations"] ?? "unknown")",
                "",
                "NORTH (NOTICE)",
                metadata["spark"],
                "",
                "EAST (EMBARK)",
                "Destination: \(metadata["destination"] ?? "")",
                "Delight: \(metadata["delight"] ?? "")",
                "Definition: \(metadata["definition"] ?? "")",
                "",
                "SOUTH (SENSE)",
                metadata["mission"],
                "",
                "WEST (WRITE)",
                metadata["souvenirPrompt"],
                "",
                "CENTER (REST)",
                metadata["restPrompt"]
            ]
            .compactMap { $0 }
            .joined(separator: "\n")
        }
        if !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return text.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        return surface.payload.metadata["placeholder"] ?? surface.payload.body
    }

    private var preparedTags: [String] {
        let metadataTags = surface.payload.metadata["tags"]?
                .split(separator: ",")
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
            ?? []

        var tags = metadataTags
        if let source = surface.payload.metadata["source"], !source.isEmpty {
            tags.append(source)
        }
        if let status = surface.payload.metadata["status"], !status.isEmpty {
            tags.append(status.lowercased())
        }
        if let facultyID = surface.payload.metadata["facultyID"], !facultyID.isEmpty {
            tags.append(facultyID)
        }
        if let facultyKind = surface.payload.metadata["facultyKind"], !facultyKind.isEmpty {
            tags.append("faculty-kind:\(facultyKind)")
        }
        if let facultyWindowID = surface.payload.metadata["facultyWindowID"], !facultyWindowID.isEmpty {
            tags.append("faculty-window:\(facultyWindowID)")
        }
        if surface.type == .illuminatedPhoto {
            tags.append("illuminated-photo")
            tags.append(manualPhotoImage == nil ? "book-chosen" : "manual-photo")
            if let template = illuminatedDraft?.compositionPlan.templateId.rawValue {
                tags.append(template)
            }
            if renderedIlluminatedPageURL != nil {
                tags.append("rendered")
            }
        }
        if surface.type == .narrativeOS {
            tags.append("narrative-os")
            if let selectedStoryChoice {
                tags.append("choice:\(selectedStoryChoice.id)")
            }
            for turn in storyTurns {
                if let choice = turn.selectedChoice {
                    tags.append("choice:\(choice.id)")
                }
            }
            tags.append("story-turns:\(max(storyTurns.count, 1))")
        }
        if surface.type == .gossip {
            tags.append("gossip-page")
        }
        if surface.type == .wonderCompass, let runID = surface.payload.metadata["runID"] {
            tags.append("wonder-compass")
            tags.append("wonder-compass-run")
            tags.append("compass-run:\(runID)")
            if let step = surface.payload.metadata["compassStep"], step != "run" {
                tags.append("compass-step:\(step)")
            }
            if let mode = surface.payload.metadata["conciergeMode"] {
                tags.append("concierge:\(mode)")
            }
        }
        if surface.type == .mood, !selectedWeather.isEmpty {
            tags.append(selectedWeather.lowercased())
        }
        return Array(Set(tags)).sorted()
    }
}

struct StoryPageChoiceDraft: Identifiable, Equatable {
    var id: String
    var title: String
    var prompt: String
    var effectLine: String
    var symbolName: String
    var tint: Color

    var kindLabel: String {
        switch id {
        case "sliceoflife":
            return "Slice of Life"
        case "progressarc":
            return "Arc"
        case "surprise":
            return "Surprise"
        default:
            return "Path"
        }
    }
}

struct StoryPageChoiceText: Equatable {
    var title: String
    var prompt: String
    var effectLine: String

    var isEmpty: Bool {
        title.nonEmpty == nil && prompt.nonEmpty == nil && effectLine.nonEmpty == nil
    }
}

struct StoryPageSessionTurn: Identifiable, Equatable {
    var id = UUID()
    var draft: StoryPageSceneDraft
    var selectedChoice: StoryPageChoiceDraft?
    var generatedResults: [String: String] = [:]

    func result(for choice: StoryPageChoiceDraft) -> String {
        generatedResults[choice.id]?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
            ?? draft.result(for: choice)
    }
}

struct StoryPageContinuationContext: Equatable {
    var turns: [StoryPageSessionTurn]
    var currentDraft: StoryPageSceneDraft
    var selectedChoice: StoryPageChoiceDraft

    var promptContext: String {
        let resolvedTurns = turns.isEmpty
            ? [StoryPageSessionTurn(draft: currentDraft, selectedChoice: selectedChoice)]
            : turns.map { turn in
                var copy = turn
                if copy.id == turns.last?.id, copy.selectedChoice == nil {
                    copy.selectedChoice = selectedChoice
                }
                return copy
            }

        let rendered = resolvedTurns.enumerated().map { index, turn in
            let choice = turn.selectedChoice ?? selectedChoice
            return """
            TURN \(index + 1):
            Scene: \(turn.draft.scene)
            Chosen path type: \(choice.kindLabel)
            Chosen action: \(choice.title) — \(choice.prompt)
            Consequence: \(turn.result(for: choice))
            Hidden movement: \(choice.effectLine)
            """
        }.joined(separator: "\n\n")

        return """
        The reader pressed Continue. Do not restart the Story Page.
        Continue from the previous consequence and let the thread remember what already happened.
        Keep the same real material, but let the chosen path change what matters next.

        \(rendered)
        """
    }
}

struct StoryPageProse: Equatable {
    var scene: String
    var choices: [StoryPageChoiceDraft]
    var results: [String: String]

    init(scene: String, choices: [StoryPageChoiceDraft], results: [String: String]) {
        self.scene = scene
        self.choices = choices
        self.results = results
    }

    init(fallback draft: StoryPageSceneDraft) {
        self.scene = draft.scene
        self.choices = draft.choices
        self.results = Dictionary(uniqueKeysWithValues: draft.choices.map { ($0.id, draft.result(for: $0)) })
    }

    func result(for choice: StoryPageChoiceDraft) -> String {
        results[choice.id]?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
            ?? choice.effectLine + " The Book records the change without making a fuss."
    }
}

protocol StoryPageWriting {
    func write(surface: SurfacePage) async throws -> StoryPageProse
}

struct StoryPageResultContext: Equatable {
    var previousTurns: [StoryPageSessionTurn]
    var draft: StoryPageSceneDraft
    var selectedChoice: StoryPageChoiceDraft

    var fallbackResult: String {
        draft.result(for: selectedChoice)
    }
}

protocol StoryPageResultWriting {
    func write(context: StoryPageResultContext) async throws -> String
}

private struct AppStoryPageWriter: StoryPageWriting {
    let local: StoryPageWriting
    private let fallback = FakeStoryPageWriter()

    func write(surface: SurfacePage) async throws -> StoryPageProse {
        do {
            return try await local.write(surface: surface)
        } catch {
            appLog.error("Local Story Page prose fell back: \(error.localizedDescription, privacy: .public)")
            return try await fallback.write(surface: surface)
        }
    }
}

struct FakeStoryPageWriter: StoryPageWriting {
    func write(surface: SurfacePage) async throws -> StoryPageProse {
        try await Task.sleep(nanoseconds: 450_000_000)
        return StoryPageProse(fallback: StoryPageSceneDraft(surface: surface))
    }
}

private struct FakeStoryPageResultWriter: StoryPageResultWriting {
    func write(context: StoryPageResultContext) async throws -> String {
        try await Task.sleep(nanoseconds: 350_000_000)
        return context.fallbackResult
    }
}

enum GossipPagePromptBuilder {
    static let instructions = """
    You are The Book inside ReEnchanted, writing a Gossip Page.
    The app has already decided the simulation mechanics and supplied any real-world interest clippings. You may only polish those supplied materials into warm, strange, readable margin-gossip.
    Do not add new actors, threads, actions, outcomes, rewards, quests, user actions, or real-world facts.
    Do not mention sensors, APIs, code, prompts, JSON, searches, or simulation machinery.
    Write in the Book's voice: plain, literary, playful, intimate, never corporate.
    Prose standard: simple concrete sentences; one exact object, gesture, or spoken line per entry; no vague wonder, hidden meaning, tapestry of, echoes of, quiet magic, profound, journey, or generic inspiration.
    """

    static func prompt(for surface: SurfacePage) -> String {
        let metadata = surface.payload.metadata
        return """
        Rewrite the following deterministic Gossip Page draft as a finished page for the user.

        Requirements:
        - Keep every actor and thread from the draft.
        - Preserve the meaning of each consequence.
        - Write 3-5 short entries total.
        - Include 2-3 Academy gossip entries.
        - If real-world interest clippings are supplied, include 1-2 of them as ordinary-world margin gossip.
        - Each entry must show what someone said, touched, carried, hid, dropped, overheard, or did.
        - Prefer dialogue, tiny betrayals, social pressure, and visible character action over explanation.
        - Use short, specific sentences. Let concrete nouns and verbs carry the joke.
        - Keep fictional Academy consequences and real-world facts distinct while letting them sit on the same page.
        - Include one brief "What changed" section in-world.
        - Keep it under 320 words.
        - Do not expose hidden mechanics as game math.
        - Do not invent anything not present in the draft packet.
        - Do not imply the user researched, visited, played, read, bought, or completed anything.

        Actors: \(metadata["actorNames"] ?? metadata["actorName"] ?? "unknown")
        Threads: \(metadata["threadTitles"] ?? metadata["threadTitle"] ?? "unknown")
        Actions: \(metadata["actionKinds"] ?? metadata["actionKind"] ?? "unknown")
        Hidden effects to preserve without naming as mechanics:
        \(metadata["hiddenEffect"] ?? "none")

        Draft:
        \(metadata["gossipDraft"] ?? surface.payload.body)

        Real-world interest clippings:
        \(metadata["realInterestClippings"] ?? "none")

        Real-world sources, for grounding only:
        \(metadata["realInterestSources"] ?? "none")

        Return only the finished Gossip Page text.
        """
    }

    static func clean(_ response: String, fallback: String) -> String {
        let cleaned = response
            .replacingOccurrences(of: "```", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty else { return fallback }
        return cleaned
    }
}

#if !NATIVE_LOCAL_BRAIN || !(canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator))
protocol GossipPageWriting {
    func write(surface: SurfacePage) async throws -> String
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
#endif

enum StoryPageResultPromptBuilder {
    static let instructions = """
    You are The Book inside ReEnchanted.
    Write only the consequence of the selected Story Page action. The app owns the mechanics; you write the ink.
    Do not invent completed real-world actions, exact locations, diagnoses, private facts, identities, or surveillance details.
    Keep it grounded, strange, concrete, and warm. No headings. No labels. No choices.
    Prose standard: simple surprising sentences; specific nouns and verbs; character action before explanation; no generic wisdom, no abstract emotional summary, no mist, echoes, tapestry, journey, profound, or quiet magic.
    """

    static func prompt(for context: StoryPageResultContext) -> String {
        let prior = context.previousTurns.suffix(2).enumerated().map { index, turn in
            let chosen = turn.selectedChoice.map { choice in
                "Chosen: \(choice.kindLabel) — \(choice.title). Result: \(turn.result(for: choice).bookPreviewSentenceLimit(2))"
            } ?? "Chosen: unresolved."
            return """
            PRIOR TURN \(index + 1):
            \(turn.draft.scene.bookPreviewSentenceLimit(2))
            \(chosen)
            """
        }.joined(separator: "\n\n")

        return """
        Write the result for this selected Story Page action.

        THREAD:
        \(context.draft.thread)

        CURRENT SCENE:
        \(context.draft.scene)

        SELECTED PATH TYPE:
        \(context.selectedChoice.kindLabel)

        BESPOKE BUTTON:
        \(context.selectedChoice.title)

        ACTION PROMPT:
        \(context.selectedChoice.prompt)

        HIDDEN MOVEMENT TO DRAMATIZE WITHOUT NAMING AS MECHANICS:
        \(context.selectedChoice.effectLine)

        RECENT THREAD MEMORY:
        \(prior.isEmpty ? "No prior turns." : prior)

        REQUIREMENTS:
        - Return only the result prose.
        - 90-150 words.
        - 4-7 sentences.
        - Make the consequence specific to the selected action, not generic.
        - Include at least two visible actions or interactions.
        - Include one exact object, surface, sound, or small physical detail.
        - If a character is present, let them reveal themselves by speech or behavior, not summary.
        - Let one entity, object, or motif gain weight.
        - If this is Progress Arc, let the thread move one step.
        - If this is Slice of Life, let an ordinary detail deepen.
        - If this is Surprise, reveal a strange related angle that still belongs here.
        - Do not include headings, button titles, labels, JSON, markdown, or additional choices.
        """
    }

    static func clean(_ response: String) -> String {
        response
            .replacingOccurrences(of: "```", with: "")
            .replacingOccurrences(of: "RESULT:", with: "")
            .replacingOccurrences(of: "Result:", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

enum StoryPagePromptBuilder {
    static let instructions = """
    You are The Book inside ReEnchanted.
    Write a living storybook vignette from the supplied scene packet. The app owns the mechanics; you write the ink.
    Do not invent completed real-world actions, exact locations, diagnoses, private facts, identities, or surveillance details.
    Keep the real and fictional braided together: warm, strange, grounded, concrete, never corporate.
    Prose standard: write like a sharp story, not an assistant. Simple surprising sentences. Specific nouns and verbs. Characters show themselves by dialogue, choices, gestures, and interruptions. Do not explain the theme.
    Ban filler: no generic inspiration, no vague wonder, no abstract emotional summary, no tapestry, echoes, journey, profound, quiet magic, hidden meaning, or "as if the world itself".
    """

    static func prompt(for draft: StoryPageSceneDraft) -> String {
        let entities = draft.entities.isEmpty ? "The Book" : draft.entities.joined(separator: ", ")
        let signals = draft.signals.isEmpty ? "- No strong outside signal; use quiet ordinary evidence." : draft.signals.prefix(8).map { "- \($0)" }.joined(separator: "\n")
        let pressures = draft.pressures.isEmpty ? "- The margins have enough weight to turn." : draft.pressures.prefix(5).map { "- \($0)" }.joined(separator: "\n")
        let memories = draft.memories.isEmpty ? "- No entity memory has been written yet." : draft.memories.prefix(5).map { "- \($0)" }.joined(separator: "\n")
        let continuation = draft.continuationContext.map {
            """

            CONTINUATION MEMORY:
            \($0)
            """
        } ?? ""
        return """
        Write one ReEnchanted Story Page.

        THREAD:
        \(draft.thread)

        ENTITIES:
        \(entities)

        REAL MATERIAL:
        \(signals)

        RELATIONSHIP / STORY PRESSURE:
        \(pressures)

        ENTITY MEMORY:
        \(memories)
        \(continuation)

        OUTPUT FORMAT, EXACTLY:
        SCENE:
        170-240 words. A vignette with a beginning, a turn, and a landing. Address the reader as "you" only when it feels natural. Make it feel like real life becoming a fantasy story, not like a quest log.
        The vignette must include at least one spoken line or overheard line when any entity is present.
        The vignette must include at least three concrete physical details from this packet: objects, surfaces, sounds, weather, posture, clothing, tools, mess, or light.
        The main movement must happen through character action and interaction, not narration about feelings or significance.
        If CONTINUATION MEMORY is present, this scene must be the next beat of that same thread. Do not recap everything; let the previous consequence alter the first paragraph.
        The SCENE must contain only the vignette. Do not include any choices, prompts, results, button titles, labels, or mechanics inside SCENE.

        SLICE_OF_LIFE_CHOICE:
        A bespoke button title, 2-5 words, for staying with one concrete ordinary detail from this exact scene. Do not write "Slice of Life" here.

        SLICE_OF_LIFE_PROMPT:
        One specific sentence under 16 words describing the action the reader would take.

        PROGRESS_ARC_CHOICE:
        A bespoke button title, 2-5 words, for moving \(draft.thread) one step forward. Do not write "Progress Arc" here.

        PROGRESS_ARC_PROMPT:
        One specific sentence under 16 words describing the action the reader would take.

        SURPRISE_CHOICE:
        A bespoke button title, 2-5 words, for a strange related move. Do not write "Something Surprising" here.

        SURPRISE_PROMPT:
        One specific sentence under 16 words describing the action the reader would take.

        Choice design rule:
        The three choices must be bespoke to this vignette, not generic. They are internally typed as Slice of Life, Progress Arc, and Surprise, but the visible titles and prompts should read like natural story actions.
        Do not write any result or consequence sections. The Book will write the chosen result after the reader chooses.
        """
    }
}

enum StoryPageProseParser {
    static func parse(_ response: String, fallback draft: StoryPageSceneDraft) -> StoryPageProse {
        let fallbackProse = StoryPageProse(fallback: draft)
        let scene = section(.scene, in: response)
            .nonEmpty
            .map(cleanSceneText)
            ?? fallbackProse.scene
        var choices = fallbackProse.choices
        choices = choices.map { choice in
            var updated = choice
            switch choice.id {
            case "sliceoflife":
                updated.title = bestTitle(for: .sliceChoice, promptMarker: .slicePrompt, in: response, fallback: choice.title)
                updated.prompt = section(.slicePrompt, in: response).singleLine(maxLength: 120) ?? section(.sliceChoice, in: response).singleLine(maxLength: 120) ?? choice.prompt
                updated.effectLine = updated.prompt
            case "progressarc":
                updated.title = bestTitle(for: .progressChoice, promptMarker: .progressPrompt, in: response, fallback: choice.title)
                updated.prompt = section(.progressPrompt, in: response).singleLine(maxLength: 120) ?? section(.progressChoice, in: response).singleLine(maxLength: 120) ?? choice.prompt
                updated.effectLine = updated.prompt
            case "surprise":
                updated.title = bestTitle(for: .surpriseChoice, promptMarker: .surprisePrompt, in: response, fallback: choice.title)
                updated.prompt = section(.surprisePrompt, in: response).singleLine(maxLength: 120) ?? section(.surpriseChoice, in: response).singleLine(maxLength: 120) ?? choice.prompt
                updated.effectLine = updated.prompt
            default:
                break
            }
            return updated
        }
        var results: [String: String] = [:]
        if let value = section(.sliceResult, in: response).nonEmpty {
            results["sliceoflife"] = value
        }
        if let value = section(.progressResult, in: response).nonEmpty {
            results["progressarc"] = value
        }
        if let value = section(.surpriseResult, in: response).nonEmpty {
            results["surprise"] = value
        }
        return StoryPageProse(scene: scene, choices: choices, results: results)
    }

    static func cleanSceneText(_ text: String) -> String {
        let normalized = text.replacingOccurrences(of: "\r\n", with: "\n")
        let firstMarker = StoryPageSectionMarker.allCases
            .flatMap(\.aliases)
            .filter { !$0.lowercased().hasPrefix("scene") }
            .compactMap { alias -> String.Index? in
                normalized.range(of: "\n\(alias):", options: [.caseInsensitive])?.lowerBound
            }
            .min()
        let slice = firstMarker.map { normalized[..<$0] } ?? Substring(normalized)
        return String(slice).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func section(_ marker: StoryPageSectionMarker, in response: String) -> String {
        let normalized = response.replacingOccurrences(of: "\r\n", with: "\n")
        guard let match = marker.aliases
            .compactMap({ alias -> Range<String.Index>? in
                normalized.range(of: "\(alias):", options: [.caseInsensitive])
            })
            .min(by: { $0.lowerBound < $1.lowerBound })
        else { return "" }
        let remainder = normalized[match.upperBound...]
        let next = StoryPageSectionMarker.allCases
            .flatMap(\.aliases)
            .compactMap { alias in
                remainder.range(of: "\n\(alias):", options: [.caseInsensitive])?.lowerBound
            }
            .min()
        let slice = next.map { remainder[..<$0] } ?? Substring(remainder)
        return String(slice).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func bestTitle(
        for marker: StoryPageSectionMarker,
        promptMarker: StoryPageSectionMarker,
        in response: String,
        fallback: String
    ) -> String {
        let explicit = titleFromButtonBlock(before: promptMarker, in: response)
        let roleTitle = section(marker, in: response).singleLine(maxLength: 42)
        return explicit ?? roleTitle?.withoutTrailingSentencePunctuation ?? fallback
    }

    private static func titleFromButtonBlock(before promptMarker: StoryPageSectionMarker, in response: String) -> String? {
        let normalized = response.replacingOccurrences(of: "\r\n", with: "\n")
        guard let promptRange = promptMarker.aliases
            .compactMap({ normalized.range(of: "\($0):", options: [.caseInsensitive]) })
            .min(by: { $0.lowerBound < $1.lowerBound })
        else { return nil }
        let prefix = normalized[..<promptRange.lowerBound]
        guard let titleRange = prefix.range(of: "button title:", options: [.caseInsensitive, .backwards]) else { return nil }
        let titleSlice = prefix[titleRange.upperBound...]
        return String(titleSlice).singleLine(maxLength: 42)?.withoutTrailingSentencePunctuation
    }

    private enum StoryPageSectionMarker: CaseIterable {
        case scene
        case sliceChoice
        case slicePrompt
        case sliceResult
        case progressChoice
        case progressPrompt
        case progressResult
        case surpriseChoice
        case surprisePrompt
        case surpriseResult

        var aliases: [String] {
            switch self {
            case .scene:
                ["SCENE", "Scene"]
            case .sliceChoice:
                ["SLICE_OF_LIFE_CHOICE", "Slice of Life Choice", "Slice of Life"]
            case .slicePrompt:
                ["SLICE_OF_LIFE_PROMPT", "Slice of Life Prompt"]
            case .sliceResult:
                ["SLICE_OF_LIFE_RESULT", "Slice of Life Result"]
            case .progressChoice:
                ["PROGRESS_ARC_CHOICE", "Progress Arc Choice", "Progress Arc"]
            case .progressPrompt:
                ["PROGRESS_ARC_PROMPT", "Progress Arc Prompt"]
            case .progressResult:
                ["PROGRESS_ARC_RESULT", "Progress Arc Result"]
            case .surpriseChoice:
                ["SURPRISE_CHOICE", "Surprise Choice", "Something Surprising", "Surprise"]
            case .surprisePrompt:
                ["SURPRISE_PROMPT", "Surprise Prompt"]
            case .surpriseResult:
                ["SURPRISE_RESULT", "Surprise Result"]
            }
        }
    }
}

private extension String {
    func singleLine(maxLength: Int) -> String? {
        let cleaned = components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
            .trimmingCharacters(in: CharacterSet(charactersIn: "\"' "))
        guard !cleaned.isEmpty else { return nil }
        if cleaned.count <= maxLength {
            return cleaned
        }
        let end = cleaned.index(cleaned.startIndex, offsetBy: maxLength)
        return String(cleaned[..<end]).trimmingCharacters(in: .whitespacesAndNewlines) + "..."
    }

    var withoutTrailingSentencePunctuation: String {
        trimmingCharacters(in: CharacterSet(charactersIn: ".!? "))
    }
}

struct StoryPageSceneDraft: Equatable {
    var surface: SurfacePage
    var thread: String
    var entities: [String]
    var signals: [String]
    var pressures: [String]
    var memories: [String]
    var preparedScene: String?
    var preparedChoices: [String: StoryPageChoiceText]
    var preparedResults: [String: String]
    var continuationContext: String?

    init(surface: SurfacePage) {
        self.surface = surface
        let metadata = surface.payload.metadata
        thread = metadata["selectedThreads"]?
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .first ?? "Ordinary Magic"
        entities = metadata["selectedEntities"]?
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty } ?? ["The Book"]
        signals = metadata["realSignals"]?
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty } ?? []
        pressures = metadata["relationshipPressures"]?
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty } ?? []
        memories = metadata["entityMemories"]?
            .split(separator: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty } ?? []
        preparedScene = metadata["storyScene"].map(StoryPageProseParser.cleanSceneText)?.nonEmpty
        var choicesByID: [String: StoryPageChoiceText] = [:]
        let sliceChoice = StoryPageChoiceText(
            title: metadata["storyChoiceSliceOfLifeTitle"] ?? "",
            prompt: metadata["storyChoiceSliceOfLifePrompt"] ?? "",
            effectLine: metadata["storyChoiceSliceOfLifeEffect"] ?? ""
        )
        let arcChoice = StoryPageChoiceText(
            title: metadata["storyChoiceProgressArcTitle"] ?? "",
            prompt: metadata["storyChoiceProgressArcPrompt"] ?? "",
            effectLine: metadata["storyChoiceProgressArcEffect"] ?? ""
        )
        let surpriseChoice = StoryPageChoiceText(
            title: metadata["storyChoiceSurpriseTitle"] ?? "",
            prompt: metadata["storyChoiceSurprisePrompt"] ?? "",
            effectLine: metadata["storyChoiceSurpriseEffect"] ?? ""
        )
        if !sliceChoice.isEmpty {
            choicesByID["sliceoflife"] = sliceChoice
        }
        if !arcChoice.isEmpty {
            choicesByID["progressarc"] = arcChoice
        }
        if !surpriseChoice.isEmpty {
            choicesByID["surprise"] = surpriseChoice
        }
        preparedChoices = choicesByID
        preparedResults = [
            "sliceoflife": metadata["storyResultSliceOfLife"] ?? "",
            "progressarc": metadata["storyResultProgressArc"] ?? "",
            "surprise": metadata["storyResultSurprise"] ?? ""
        ].compactMapValues(\.nonEmpty)
        continuationContext = metadata["storyContinuationContext"]?.nonEmpty
    }

    var scene: String {
        if let preparedScene {
            return preparedScene
        }
        let entity = entities.first ?? "The Book"
        let signalLine = signals.prefix(2).joined(separator: " ")
        let pressureLine = pressures.first ?? "The margins have found enough weight to turn."
        return """
        \(entity) stands near the edge of \(thread), not as an assignment, but as a door left slightly open.

        \(signalLine.isEmpty ? "The day has offered a few small pieces of evidence." : signalLine)

        \(pressureLine) The Book does not ask the reader to leave real life. It asks which part of real life is ready to become story.
        """
    }

    private var defaultChoices: [StoryPageChoiceDraft] {
        [
            StoryPageChoiceDraft(
                id: "sliceoflife",
                title: "Slice of Life",
                prompt: "Stay with the ordinary detail already glowing.",
                effectLine: "The Book gives the small thing more weight. Nothing dramatic is required.",
                symbolName: "leaf",
                tint: BookPalette.violet
            ),
            StoryPageChoiceDraft(
                id: "progressarc",
                title: "Progress Arc",
                prompt: "Let the current thread take one real step forward.",
                effectLine: "\(thread) darkens one line of ink and moves from possibility toward consequence.",
                symbolName: "point.3.connected.trianglepath.dotted",
                tint: BookPalette.teal
            ),
            StoryPageChoiceDraft(
                id: "surprise",
                title: "Something Surprising",
                prompt: "Open the side door, but keep one hand on the scene.",
                effectLine: "A related detail steps out of the margins and asks to be remembered later.",
                symbolName: "sparkles",
                tint: BookPalette.gold
            )
        ]
    }

    var choices: [StoryPageChoiceDraft] {
        defaultChoices.map { choice in
            guard let prepared = preparedChoices[choice.id] else {
                return choice
            }
            return StoryPageChoiceDraft(
                id: choice.id,
                title: prepared.title.nonEmpty ?? choice.title,
                prompt: prepared.prompt.nonEmpty ?? choice.prompt,
                effectLine: prepared.effectLine.nonEmpty ?? prepared.prompt.nonEmpty ?? choice.effectLine,
                symbolName: choice.symbolName,
                tint: choice.tint
            )
        }
    }

    func result(for choice: StoryPageChoiceDraft) -> String {
        if let prepared = preparedResults[choice.id] {
            return prepared
        }
        let entity = entities.first ?? "The Book"
        return "\(choice.effectLine) \(entity) keeps the page warm, and the story field changes quietly underneath."
    }
}
