import SwiftUI
import OSLog
import Darwin.Mach
import CoreImage
import CoreImage.CIFilterBuiltins
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

struct IlluminatedArtifactPreview: View {
    let draft: IlluminatedPhotoDraft
    var sourceImage: UIImage? = nil
    private static let ciContext = CIContext(options: [.useSoftwareRenderer: false])

    private var plan: IlluminatedCompositionPlan {
        draft.compositionPlan
    }

    var body: some View {
        GeometryReader { proxy in
            let scale = min(
                proxy.size.width / plan.canvasSize.width,
                proxy.size.height / plan.canvasSize.height
            )
            let xOffset = (proxy.size.width - plan.canvasSize.width * scale) / 2
            let yOffset = (proxy.size.height - plan.canvasSize.height * scale) / 2

            ZStack {
                Image(plan.backgroundAssetName)
                    .resizable()
                    .scaledToFill()
                    .frame(width: plan.canvasSize.width * scale, height: plan.canvasSize.height * scale)
                    .clipped()
                    .position(x: proxy.size.width / 2, y: proxy.size.height / 2)

                textureOverlays(scale: scale, proxySize: proxy.size)

                illuminatedPhoto(scale: scale, xOffset: xOffset, yOffset: yOffset)

                ForEach(plan.decorations) { decoration in
                    illuminatedDecoration(decoration, scale: scale, xOffset: xOffset, yOffset: yOffset)
                }

                ForEach(plan.textSlots) { slot in
                    illuminatedTextSlot(slot, scale: scale, xOffset: xOffset, yOffset: yOffset)
                }

                Rectangle()
                    .fill(
                        RadialGradient(
                            colors: [.clear, BookPalette.ink.opacity(0.22)],
                            center: .center,
                            startRadius: 80 * scale,
                            endRadius: 840 * scale
                        )
                    )
                    .allowsHitTesting(false)
            }
            .frame(width: proxy.size.width, height: proxy.size.height)
            .background(BookPalette.nightPanel)
        }
    }

    private func illuminatedPhoto(scale: CGFloat, xOffset: CGFloat, yOffset: CGFloat) -> some View {
        let frame = plan.photoFrame
        let variation = OrganicPlacementVariation(seed: plan.randomSeed, key: "photo-frame")
        return photoImage
            .saturation(saturation(for: plan.photoTreatment))
            .contrast(contrast(for: plan.photoTreatment))
            .brightness(brightness(for: plan.photoTreatment))
            .frame(width: frame.size.width * scale, height: frame.size.height * scale)
            .clipShape(RoundedRectangle(cornerRadius: frame.cornerRadius * scale, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: frame.cornerRadius * scale, style: .continuous)
                    .stroke(BookPalette.paper.opacity(0.82), lineWidth: max(2, 8 * scale))
            }
            .shadow(color: .black.opacity(0.28), radius: 18 * scale, x: 0, y: 10 * scale)
            .rotationEffect(.degrees(frame.rotationDegrees + variation.rotationDegrees))
            .position(
                x: xOffset + (frame.position.x + frame.size.width / 2 + variation.xOffset) * scale,
                y: yOffset + (frame.position.y + frame.size.height / 2 + variation.yOffset) * scale
            )
    }

    @ViewBuilder
    private var photoImage: some View {
        if let sourceImage {
            Image(uiImage: sourceImage)
                .resizable()
                .scaledToFill()
        } else {
            Image(draft.sourceAssetName)
                .resizable()
                .scaledToFill()
        }
    }

    private func illuminatedTextSlot(_ slot: IlluminatedTextSlot, scale: CGFloat, xOffset: CGFloat, yOffset: CGFloat) -> some View {
        let variation = OrganicPlacementVariation(seed: plan.randomSeed, key: "text-\(slot.slotId)", maxOffset: 5, maxRotation: 2.2)
        return ZStack(alignment: .topLeading) {
            illuminatedPaperScrap(slot, scale: scale)

            VStack(alignment: .leading, spacing: 5 * scale) {
                if let title = slot.title, !title.isEmpty {
                    Text(title.uppercased())
                        .font(.system(size: max(7, 30 * scale), weight: .bold, design: .serif))
                        .foregroundStyle(BookPalette.ink.opacity(0.62))
                        .lineLimit(1)
                }
                Text(slot.body)
                    .font(font(for: slot.fontStyle, scale: scale))
                    .foregroundStyle(BookPalette.ink.opacity(0.82))
                    .lineSpacing(4 * scale)
                    .minimumScaleFactor(0.55)
                    .lineLimit(7)
            }
            .padding(EdgeInsets(top: 24 * scale, leading: 26 * scale, bottom: 18 * scale, trailing: 22 * scale))
        }
        .frame(width: slot.size.width * scale, height: slot.size.height * scale)
        .clipShape(RoundedRectangle(cornerRadius: 10 * scale, style: .continuous))
        .shadow(color: .black.opacity(0.18), radius: 10 * scale, x: 0, y: 6 * scale)
        .rotationEffect(.degrees(slot.rotationDegrees + variation.rotationDegrees))
        .position(
            x: xOffset + (slot.position.x + slot.size.width / 2 + variation.xOffset) * scale,
            y: yOffset + (slot.position.y + slot.size.height / 2 + variation.yOffset) * scale
        )
    }

    private func illuminatedPaperScrap(_ slot: IlluminatedTextSlot, scale: CGFloat) -> some View {
        let material = OrganicPlacementVariation(seed: plan.randomSeed, key: "paper-\(slot.slotId)", maxOffset: 1, maxRotation: 0.4)
        return ZStack {
            Image(slot.paperAssetName)
                .resizable()
                .scaledToFill()
                .opacity(slot.paperAssetName == "MarginaliaSeal" ? 0.18 + material.opacityLift * 0.06 : 0.80 + material.opacityLift * 0.12)
                .frame(width: slot.size.width * scale, height: slot.size.height * scale)
                .clipped()

            LinearGradient(
                colors: [
                    BookPalette.page.opacity(0.92),
                    BookPalette.paper.opacity(0.80),
                    BookPalette.gold.opacity(0.16)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            RoundedRectangle(cornerRadius: 9 * scale, style: .continuous)
                .stroke(BookPalette.ink.opacity(0.18), lineWidth: max(1, 2 * scale))

            VStack {
                HStack {
                    tapeStrip(scale: scale)
                        .rotationEffect(.degrees(-7))
                    Spacer()
                    if slot.slotId != "observation-list" {
                        tapeStrip(scale: scale)
                            .rotationEffect(.degrees(8))
                    }
                }
                Spacer()
            }
            .padding(EdgeInsets(top: -8 * scale, leading: 18 * scale, bottom: 0, trailing: 18 * scale))

            ForEach(0..<5, id: \.self) { index in
                Circle()
                    .fill(BookPalette.ink.opacity(0.08))
                    .frame(width: max(1.5, CGFloat(3 + index % 3) * scale), height: max(1.5, CGFloat(3 + index % 3) * scale))
                    .position(
                        x: CGFloat((index * 67 + abs(slot.slotId.stableHash % 43)) % max(1, Int(slot.size.width))) * scale,
                        y: CGFloat((index * 41 + abs(slot.slotId.stableHash % 71)) % max(1, Int(slot.size.height))) * scale
                    )
            }
        }
        .frame(width: slot.size.width * scale, height: slot.size.height * scale)
    }

    @ViewBuilder
    private func illuminatedDecoration(_ decoration: DecorationPlacement, scale: CGFloat, xOffset: CGFloat, yOffset: CGFloat) -> some View {
        let variation = OrganicPlacementVariation(seed: plan.randomSeed, key: "decoration-\(decoration.assetName)-\(decoration.position.x)-\(decoration.position.y)", maxOffset: 7, maxRotation: 3)
        let opacity = decoration.kind == .stamp
            ? max(0.12, min(0.62, decoration.opacity + variation.opacityLift * 0.16 - 0.08))
            : max(0.16, min(0.86, decoration.opacity + variation.opacityLift * 0.10 - 0.04))
        Group {
            if decoration.kind == .stamp,
               let stamp = distressedStampImage(assetName: decoration.assetName, variation: variation) {
                Image(uiImage: stamp)
                    .resizable()
                    .scaledToFit()
            } else {
                Image(decoration.assetName)
                    .resizable()
                    .scaledToFit()
            }
        }
        .opacity(opacity)
        .blendMode(decoration.kind == .stamp ? .multiply : .normal)
        .frame(width: decoration.size.width * scale, height: decoration.size.height * scale)
        .rotationEffect(.degrees(decoration.rotationDegrees + variation.rotationDegrees))
        .position(
            x: xOffset + (decoration.position.x + decoration.size.width / 2 + variation.xOffset) * scale,
            y: yOffset + (decoration.position.y + decoration.size.height / 2 + variation.yOffset) * scale
        )
    }

    @ViewBuilder
    private func textureOverlays(scale: CGFloat, proxySize: CGSize) -> some View {
        ForEach(Array(plan.textureOverlayNames.enumerated()), id: \.offset) { index, name in
            let variation = OrganicPlacementVariation(seed: plan.randomSeed, key: "texture-\(name)-\(index)", maxOffset: 10, maxRotation: 1.5)
            Image(name)
                .resizable()
                .scaledToFill()
                .frame(width: plan.canvasSize.width * scale, height: plan.canvasSize.height * scale)
                .clipped()
                .opacity(0.035 + variation.opacityLift * 0.045)
                .blendMode(index.isMultiple(of: 2) ? .multiply : .overlay)
                .rotationEffect(.degrees(variation.rotationDegrees))
                .position(
                    x: proxySize.width / 2 + variation.xOffset * scale,
                    y: proxySize.height / 2 + variation.yOffset * scale
                )
                .allowsHitTesting(false)
        }
    }

    private func distressedStampImage(assetName: String, variation: OrganicPlacementVariation) -> UIImage? {
        guard let image = UIImage(named: assetName),
              let input = CIImage(image: image) else {
            return nil
        }
        let controls = CIFilter.colorControls()
        controls.inputImage = input
        controls.saturation = 0.72 + Float(variation.opacityLift) * 0.18
        controls.contrast = 0.88 + Float(variation.distress) * 0.46
        controls.brightness = -0.04 - Float(variation.distress) * 0.08

        let blur = CIFilter.gaussianBlur()
        blur.inputImage = controls.outputImage
        blur.radius = Float(variation.distress * 0.45)

        guard let output = blur.outputImage?.cropped(to: input.extent),
              let cgImage = Self.ciContext.createCGImage(output, from: input.extent) else {
            return nil
        }
        return UIImage(cgImage: cgImage, scale: image.scale, orientation: image.imageOrientation)
    }

    private func tapeStrip(scale: CGFloat) -> some View {
        RoundedRectangle(cornerRadius: 2 * scale, style: .continuous)
            .fill(BookPalette.paper.opacity(0.58))
            .overlay {
                RoundedRectangle(cornerRadius: 2 * scale, style: .continuous)
                    .stroke(BookPalette.ink.opacity(0.08), lineWidth: max(0.5, scale))
            }
            .frame(width: 66 * scale, height: 22 * scale)
            .shadow(color: .black.opacity(0.08), radius: 3 * scale, x: 0, y: 2 * scale)
    }

    private func font(for style: IlluminatedFontStyle, scale: CGFloat) -> Font {
        let size = max(8, 34 * scale)
        switch style {
        case .serifTitle:
            return .system(size: size * 1.12, weight: .semibold, design: .serif)
        case .serifBody:
            return .system(size: size, weight: .regular, design: .serif)
        case .handwritten:
            return .system(size: size, weight: .regular, design: .serif)
        case .stamp:
            return .system(size: size * 0.9, weight: .bold, design: .serif)
        }
    }

    private func saturation(for treatment: PhotoTreatment) -> Double {
        switch treatment {
        case .naturalKept:
            return 1.04
        case .softArchive:
            return 0.88
        case .sepiaFieldNote:
            return 0.78
        case .hearthGlow:
            return 0.96
        case .quietMatte:
            return 0.72
        }
    }

    private func contrast(for treatment: PhotoTreatment) -> Double {
        switch treatment {
        case .naturalKept:
            return 1.04
        case .softArchive:
            return 0.96
        case .sepiaFieldNote:
            return 0.92
        case .hearthGlow:
            return 1.02
        case .quietMatte:
            return 0.9
        }
    }

    private func brightness(for treatment: PhotoTreatment) -> Double {
        switch treatment {
        case .naturalKept, .softArchive:
            return 0.01
        case .sepiaFieldNote:
            return 0.015
        case .hearthGlow:
            return 0.025
        case .quietMatte:
            return 0.0
        }
    }
}

private struct OrganicPlacementVariation {
    let xOffset: Double
    let yOffset: Double
    let rotationDegrees: Double
    let opacityLift: Double
    let distress: Double

    init(seed: Int, key: String, maxOffset: Double = 6, maxRotation: Double = 3) {
        xOffset = Self.signed(seed: seed, key: "\(key)-x", range: maxOffset)
        yOffset = Self.signed(seed: seed, key: "\(key)-y", range: maxOffset)
        rotationDegrees = Self.signed(seed: seed, key: "\(key)-r", range: maxRotation)
        opacityLift = Self.unit(seed: seed, key: "\(key)-o")
        distress = Self.unit(seed: seed, key: "\(key)-d")
    }

    private static func signed(seed: Int, key: String, range: Double) -> Double {
        (unit(seed: seed, key: key) * 2 - 1) * range
    }

    private static func unit(seed: Int, key: String) -> Double {
        var hash = UInt64(bitPattern: Int64(seed)) ^ 14_695_981_039_346_656_037
        for byte in key.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return Double(hash % 10_000) / 10_000
    }
}

@MainActor
enum IlluminatedPageRenderer {
    static func renderPreview(draft: IlluminatedPhotoDraft, sourceImage: UIImage?) -> URL? {
        AppMemoryLedger.record("illumination-render-enter")
        let plan = draft.compositionPlan
        let content = IlluminatedArtifactPreview(draft: draft, sourceImage: sourceImage)
            .frame(width: plan.canvasSize.width, height: plan.canvasSize.height)

        let renderer = ImageRenderer(content: content)
        renderer.scale = 1
        guard let image = renderer.uiImage,
              let data = image.jpegData(compressionQuality: 0.9) else {
            return nil
        }

        do {
            let directory = try renderedDirectory()
            let filename = "illuminated-\(draft.id.uuidString).jpg"
            let url = directory.appendingPathComponent(filename)
            try data.write(to: url, options: [.atomic])
            AppMemoryLedger.record("illumination-render-exit")
            return url
        } catch {
            appLog.error("Illuminated render failed: \(error.localizedDescription, privacy: .public)")
            return nil
        }
    }

    private static func renderedDirectory() throws -> URL {
        let baseURL = InsideCoverStore.containerURL
            ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let directory = baseURL.appendingPathComponent("IlluminatedPages", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory
    }
}

struct SurfaceCard: View {
    let surface: SurfacePage
    let isBusy: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hasSurfaced = false

    private var visualStyle: PageVisualStyle {
        PageVisualStyle.style(for: surface.type)
    }

    private var privacyNote: String? {
        guard let value = surface.payload.metadata["privacy"], !value.isEmpty else {
            return nil
        }
        return value.capitalized
    }

    private var symbolName: String {
        surface.payload.metadata["symbol"] ?? surface.type.symbolName
    }

    private var illustrationAssetName: String? {
        guard surface.type == .illustration else { return nil }
        let value = surface.payload.metadata["assetName"] ?? ""
        return value.isEmpty ? nil : value
    }

    private var illuminatedDraft: IlluminatedPhotoDraft? {
        guard surface.type == .illuminatedPhoto,
              let sourceAssetName = surface.payload.metadata["sourceAssetName"] else {
            return nil
        }
        let fallback = FakePhotoIlluminationAnalyzer.analyze(assetName: sourceAssetName)
        let analysis = PhotoAnalysis.fromSurfaceMetadata(surface.payload.metadata, fallback: fallback)
        let seed = abs(surface.id.stableHash)
        return IlluminatedPageComposer.compose(
            analysis: analysis,
            sourceAssetName: sourceAssetName,
            seed: seed,
            assetLocalIdentifier: surface.payload.metadata["assetLocalIdentifier"]
        )
    }

    private var marginaliaName: String {
        visualStyle.cornerMarginalia
    }

    private var sideMarginaliaName: String {
        visualStyle.sideMarginalia
    }

    private var isReadingCard: Bool {
        surface.type == .wonderCompass
            || surface.type == .patreon
            || surface.type == .illustration
            || surface.type == .illuminatedPhoto
            || surface.type == .quip
            || surface.type == .narrativeOS
            || surface.type == .marginsAtlas
            || surface.type == .bookRemembered
            || surface.type == .facultyResearch
            || surface.type == .supportGuild
            || surface.type == .castMember
            || surface.renderStyle == .quoteCard
    }

    private var previewText: String? {
        guard isReadingCard else { return nil }
        let body = surface.payload.body.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return nil }
        if surface.type == .wonderCompass || surface.type == .narrativeOS || surface.type == .marginsAtlas || surface.type == .bookRemembered || surface.type == .gossip || surface.type == .facultyResearch || surface.type == .supportGuild || surface.type == .castMember {
            return body.bookPreviewSentenceLimit(2)
        }
        return body
    }

    private var previewLineLimit: Int {
        switch surface.type {
        case .wonderCompass:
            return 3
        case .narrativeOS, .marginsAtlas, .bookRemembered:
            return 4
        case .gossip:
            return 4
        case .facultyResearch:
            return 4
        case .supportGuild, .castMember:
            return 4
        case .illustration, .illuminatedPhoto:
            return 4
        default:
            return 5
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: symbolName)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(visualStyle.symbolColor)
                    .frame(width: 28, alignment: .leading)

                Text(surface.type.shortTitle.uppercased())
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(visualStyle.accent.opacity(0.82))
                    .padding(.top, 3)

                Spacer()
            }
            .padding(.trailing, 38)

            Text(surface.prompt)
                .font(.system(.title3, design: .serif, weight: .semibold))
                .foregroundStyle(BookPalette.ink)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.trailing, 26)

            Text(surface.detail)
                .font(.footnote)
                .foregroundStyle(BookPalette.ink.opacity(0.66))
                .fixedSize(horizontal: false, vertical: true)

            if let illustrationAssetName {
                Image(illustrationAssetName)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: 170)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(BookPalette.ink.opacity(0.14), lineWidth: 1)
                    }
                    .accessibilityHidden(true)
            }

            if let illuminatedDraft {
                illuminatedCardPreview(draft: illuminatedDraft)
            }

            if let previewText {
                Text(previewText)
                    .font(.system(.callout, design: .serif))
                    .foregroundStyle(BookPalette.ink.opacity(0.82))
                    .lineSpacing(3)
                    .lineLimit(previewLineLimit)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 2)
            }

            Text(surface.reason)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(BookPalette.ink.opacity(0.48))
                .lineLimit(isReadingCard ? 1 : 2)
                .fixedSize(horizontal: false, vertical: true)

            if let privacyNote {
                Label(privacyNote, systemImage: "lock.shield")
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(visualStyle.accent.opacity(0.86))
                    .lineLimit(2)
            }

            Spacer(minLength: 0)

            HStack {
                Text(isBusy ? "Taking ink..." : "Open the page")
                    .font(.caption.weight(.bold))
                Spacer()
                Image(systemName: isBusy ? "circle.dotted" : "arrow.up.right")
                    .font(.caption.weight(.bold))
            }
            .foregroundStyle(visualStyle.accent)
        }
        .padding(16)
        .frame(minHeight: isReadingCard ? 330 : 212, alignment: .topLeading)
        .parchmentSurface(style: visualStyle, isActive: true)
        .overlay(alignment: .topTrailing) {
            PageCurl()
                .fill(visualStyle.accent.opacity(0.16))
                .frame(width: 34, height: 34)
                .opacity(0.72)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .topLeading) {
            CardScrapMark(seed: surface.id, style: visualStyle)
                .offset(x: 10, y: 8)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .leading) {
            MarginaliaImage(name: sideMarginaliaName, width: visualStyle.sideMarginaliaWidth, opacity: visualStyle.sideMarginaliaOpacity)
                .rotationEffect(.degrees(surface.id.stableHash.isMultiple(of: 2) ? -9 : 8))
                .offset(x: -10, y: isReadingCard ? 74 : 34)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .bottomTrailing) {
            MarginaliaImage(name: marginaliaName, width: isReadingCard ? visualStyle.cornerMarginaliaWidth + 12 : visualStyle.cornerMarginaliaWidth, opacity: visualStyle.cornerMarginaliaOpacity)
                .rotationEffect(.degrees(surface.id.stableHash.isMultiple(of: 2) ? 7 : -8))
                .offset(x: 12, y: 10)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .bottomLeading) {
            MarginaliaImage(name: visualStyle.smallMarginalia, width: 38, opacity: 0.30)
                .rotationEffect(.degrees(surface.id.stableHash.isMultiple(of: 3) ? 12 : -10))
                .offset(x: 14, y: -8)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .center) {
            MarginaliaImage(name: visualStyle.watermarkMarginalia, width: isReadingCard ? 150 : 118, opacity: visualStyle.watermarkOpacity)
                .rotationEffect(.degrees(surface.id.stableHash.isMultiple(of: 2) ? -13 : 11))
                .offset(x: isReadingCard ? 108 : 92, y: isReadingCard ? -34 : -16)
                .allowsHitTesting(false)
        }
        .rotationEffect(.degrees(surface.id.stableHash.isMultiple(of: 2) ? -0.6 : 0.5))
        .opacity(hasSurfaced ? 1 : 0)
        .offset(y: hasSurfaced ? 0 : (reduceMotion ? 0 : -18))
        .onAppear {
            guard !hasSurfaced else { return }
            withAnimation(reduceMotion ? .linear(duration: 0.01) : .spring(response: 0.72, dampingFraction: 0.84)) {
                hasSurfaced = true
            }
        }
    }

    @ViewBuilder
    private func illuminatedCardPreview(draft: IlluminatedPhotoDraft) -> some View {
        if let renderedPath = surface.payload.metadata["renderedPreviewPath"],
           let image = UIImage(contentsOfFile: renderedPath) {
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: .infinity)
                .frame(height: 300)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                }
                .accessibilityLabel("Proposed illuminated photo page")
        } else {
            IlluminatedArtifactPreview(draft: draft)
                .frame(maxWidth: .infinity)
                .frame(height: 300)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
                }
                .accessibilityLabel("Proposed illuminated photo page")
        }
    }
}

struct SwipeDismissSurfaceCard: View {
    let surface: SurfacePage
    let isBusy: Bool
    let onOpen: () -> Void
    let onDismiss: () -> Void

    @State private var dragOffset: CGFloat = 0

    private let dismissThreshold: CGFloat = 96
    private let horizontalDragRatio: CGFloat = 1.6

    var body: some View {
        ZStack(alignment: .trailing) {
            HStack {
                Spacer()
                Label("Let it pass", systemImage: "xmark.circle")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.92))
                    .padding(.trailing, 18)
            }
            .frame(maxWidth: .infinity, minHeight: 176)
            .background(.red.opacity(0.72), in: RoundedRectangle(cornerRadius: 8, style: .continuous))

            Button {
                onOpen()
            } label: {
                SurfaceCard(surface: surface, isBusy: isBusy)
            }
            .buttonStyle(.plain)
            .offset(x: dragOffset)
            .overlay(alignment: .topTrailing) {
                Button {
                    onDismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(BookPalette.ink.opacity(0.42))
                        .padding(12)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Let \(surface.type.title) pass for now")
            }
            .overlay(alignment: .trailing) {
                SwipeDismissHandle()
                    .padding(.trailing, 2)
                    .gesture(
                        DragGesture(minimumDistance: 26)
                            .onChanged(handleDragChanged)
                            .onEnded(handleDragEnded)
                    )
            }
        }
        .accessibilityHint("Tap to open. Use the small right-edge tab or close button to let this page pass.")
    }

    private func handleDragChanged(_ value: DragGesture.Value) {
        guard isDeliberateHorizontalDismiss(value) else {
            dragOffset = 0
            return
        }
        dragOffset = min(0, value.translation.width)
    }

    private func handleDragEnded(_ value: DragGesture.Value) {
        guard isDeliberateHorizontalDismiss(value) else {
            withAnimation(.spring(response: 0.28, dampingFraction: 0.78)) {
                dragOffset = 0
            }
            return
        }

        let shouldDismiss = value.translation.width < -dismissThreshold || value.predictedEndTranslation.width < -dismissThreshold * 1.4
        if shouldDismiss {
            withAnimation(.easeInOut(duration: 0.2)) {
                dragOffset = -500
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) {
                onDismiss()
                dragOffset = 0
            }
        } else {
            withAnimation(.spring(response: 0.28, dampingFraction: 0.78)) {
                dragOffset = 0
            }
        }
    }

    private func isDeliberateHorizontalDismiss(_ value: DragGesture.Value) -> Bool {
        let horizontal = abs(value.translation.width)
        let vertical = abs(value.translation.height)
        return value.translation.width < 0 && horizontal > vertical * horizontalDragRatio
    }
}

private struct SwipeDismissHandle: View {
    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: "chevron.left")
                .font(.caption2.weight(.black))
            Image(systemName: "xmark")
                .font(.caption2.weight(.black))
        }
        .foregroundStyle(BookPalette.ink.opacity(0.32))
        .frame(width: 34, height: 82)
        .background(
            Capsule(style: .continuous)
                .fill(BookPalette.paper.opacity(0.18))
        )
        .contentShape(Rectangle())
        .accessibilityHidden(true)
    }
}

struct PageSourceCard: View {
    let source: BookPageSource
    let isEnabled: Bool

    private var visualStyle: PageVisualStyle {
        PageVisualStyle.style(for: source.type)
    }

    private var isOpen: Bool {
        source.isActive && isEnabled
    }

    private var borderColor: Color {
        isOpen ? visualStyle.accent.opacity(0.36) : BookPalette.ink.opacity(0.12)
    }

    private var statusText: String {
        if !source.isActive {
            return "not yet"
        }
        return isEnabled ? "awake" : "quiet"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: source.symbolName)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(isOpen ? visualStyle.symbolColor : BookPalette.ink.opacity(0.46))
                    .frame(width: 30, height: 30)
                    .background(
                        (isOpen ? visualStyle.accent : BookPalette.ink)
                            .opacity(0.10),
                        in: Circle()
                    )

                Spacer(minLength: 8)

                Text(statusText)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(isOpen ? visualStyle.accent : BookPalette.ink.opacity(0.46))
            }

            Text(source.shortTitle)
                .font(.system(.headline, design: .serif, weight: .semibold))
                .foregroundStyle(BookPalette.ink.opacity(source.isActive ? 1 : 0.62))
                .lineLimit(1)

            Text(source.note)
                .font(.caption)
                .foregroundStyle(BookPalette.ink.opacity(0.62))
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            Spacer(minLength: 0)

            HStack(spacing: 6) {
                Text(source.cadence)
                Spacer(minLength: 8)
                Image(systemName: source.privacy == .localSensitive ? "lock.shield" : "lock")
            }
            .font(.caption2.weight(.semibold))
            .foregroundStyle(BookPalette.ink.opacity(0.50))
        }
        .padding(14)
        .frame(width: 158, height: 168, alignment: .topLeading)
        .parchmentSurface(style: visualStyle, isActive: isOpen)
        .overlay(alignment: .bottomTrailing) {
            MarginaliaImage(name: visualStyle.smallMarginalia, width: 38, opacity: isOpen ? 0.28 : 0.14)
                .rotationEffect(.degrees(8))
                .offset(x: 8, y: 8)
                .allowsHitTesting(false)
        }
    }
}

struct SourceSettingsSheet: View {
    let sources: [BookPageSource]
    let onSet: (String, Bool) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var preferences: [String: Bool]

    init(
        sources: [BookPageSource],
        preferences: [String: Bool],
        onSet: @escaping (String, Bool) -> Void
    ) {
        self.sources = sources
        self.onSet = onSet
        _preferences = State(initialValue: preferences)
    }

    var body: some View {
        NavigationStack {
            ZStack {
                BookBackground()

                ScrollView {
                    VStack(spacing: 12) {
                        ForEach(sources) { source in
                            SourceToggleRow(
                                source: source,
                                isEnabled: preferences[source.id] ?? source.isActive,
                                isEditable: source.isActive
                            ) { isEnabled in
                                BookFeedback.play(isEnabled ? .undo : .dismissPage)
                                preferences[source.id] = isEnabled
                                onSet(source.id, isEnabled)
                            }
                        }
                    }
                    .padding(20)
                    .frame(maxWidth: 720)
                    .frame(maxWidth: .infinity)
                }
            }
            .navigationTitle("Doorways")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Close")
                    {
                        BookFeedback.play(.tap)
                        dismiss()
                    }
                }
            }
        }
    }
}

struct SourceToggleRow: View {
    let source: BookPageSource
    let isEnabled: Bool
    let isEditable: Bool
    let onChange: (Bool) -> Void

    private var statusText: String {
        if !source.isActive {
            return "not yet"
        }
        return isEnabled ? "awake" : "quiet"
    }

    private var visualStyle: PageVisualStyle {
        PageVisualStyle.style(for: source.type)
    }

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: source.symbolName)
                .font(.headline.weight(.semibold))
                .foregroundStyle(isEnabled && source.isActive ? visualStyle.symbolColor : BookPalette.ink.opacity(0.46))
                .frame(width: 34, height: 34)
                .background(
                    (isEnabled && source.isActive ? visualStyle.accent : BookPalette.ink).opacity(0.10),
                    in: Circle()
                )

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text(source.title)
                        .font(.headline)
                        .foregroundStyle(BookPalette.ink)
                    Text(statusText)
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(isEnabled && source.isActive ? visualStyle.accent : BookPalette.ink.opacity(0.48))
                }

                Text(source.note)
                    .font(.caption)
                    .foregroundStyle(BookPalette.ink.opacity(0.62))
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 10)

            Toggle(
                "",
                isOn: Binding(
                    get: { isEnabled },
                    set: { onChange($0) }
                )
            )
            .labelsHidden()
            .disabled(!isEditable)
            .tint(visualStyle.accent)
        }
        .padding(14)
        .parchmentSurface(style: visualStyle, isActive: isEnabled && source.isActive)
    }
}

struct FragmentRow: View {
    let page: BookPage
    let onOpen: () -> Void
    let onRemove: () -> Void

    @State private var dragOffset: CGFloat = 0

    private let dismissThreshold: CGFloat = 82
    private let horizontalDragRatio: CGFloat = 1.6

    private var visualStyle: PageVisualStyle {
        PageVisualStyle.style(for: page.type)
    }

    var body: some View {
        ZStack(alignment: .trailing) {
            HStack {
                Spacer()
                Label("Remove", systemImage: "xmark.circle")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(BookPalette.ink.opacity(0.54))
                    .padding(.trailing, 18)
            }
            .frame(maxWidth: .infinity, minHeight: 92)
            .background(
                BookPalette.paper.opacity(0.42),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(visualStyle.accent.opacity(0.18), lineWidth: 1)
            }

            HStack(alignment: .top, spacing: 12) {
                if let mediaAsset = page.mediaAssets.first {
                    BookOfYouMediaThumbnail(asset: mediaAsset, width: 56, height: 48)
                } else {
                    Image(systemName: page.type.symbolName)
                        .foregroundStyle(visualStyle.symbolColor)
                        .frame(width: 28, height: 28)
                        .background(visualStyle.accent.opacity(0.12), in: Circle())
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(page.type.title)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(BookPalette.ink)
                    Text(fragmentText)
                        .font(.callout)
                        .foregroundStyle(BookPalette.ink.opacity(0.72))
                        .lineLimit(3)
                }
                .padding(.trailing, 30)

                Spacer(minLength: 0)
            }
            .padding(14)
            .parchmentSurface(style: visualStyle, isActive: false)
            .offset(x: dragOffset)
            .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .onTapGesture {
                onOpen()
            }
            .overlay(alignment: .topTrailing) {
                Button {
                    onRemove()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(BookPalette.ink.opacity(0.42))
                        .padding(10)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Remove \(page.type.title) from Today's Margins")
            }
            .overlay(alignment: .trailing) {
                SwipeDismissHandle()
                    .padding(.trailing, 2)
                    .gesture(
                        DragGesture(minimumDistance: 26)
                            .onChanged(handleDragChanged)
                            .onEnded(handleDragEnded)
                    )
            }
            .overlay(alignment: .bottomTrailing) {
                MarginaliaImage(name: visualStyle.cornerMarginalia, width: 46, opacity: 0.20)
                    .offset(x: 8, y: 8)
                    .allowsHitTesting(false)
            }
        }
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Opens this kept page. Use the close button or small right-edge tab to remove it.")
    }

    private var fragmentText: String {
        let text = page.userInput.trimmingCharacters(in: .whitespacesAndNewlines)
        return text.isEmpty ? page.promptText : text
    }

    private func handleDragChanged(_ value: DragGesture.Value) {
        guard isDeliberateHorizontalDismiss(value) else {
            dragOffset = 0
            return
        }
        dragOffset = min(0, value.translation.width)
    }

    private func handleDragEnded(_ value: DragGesture.Value) {
        guard isDeliberateHorizontalDismiss(value) else {
            withAnimation(.spring(response: 0.28, dampingFraction: 0.78)) {
                dragOffset = 0
            }
            return
        }

        let shouldDismiss = value.translation.width < -dismissThreshold || value.predictedEndTranslation.width < -dismissThreshold * 1.4
        if shouldDismiss {
            withAnimation(.easeInOut(duration: 0.2)) {
                dragOffset = -500
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) {
                onRemove()
                dragOffset = 0
            }
        } else {
            withAnimation(.spring(response: 0.28, dampingFraction: 0.78)) {
                dragOffset = 0
            }
        }
    }

    private func isDeliberateHorizontalDismiss(_ value: DragGesture.Value) -> Bool {
        let horizontal = abs(value.translation.width)
        let vertical = abs(value.translation.height)
        return value.translation.width < 0 && horizontal > vertical * horizontalDragRatio
    }
}

struct ResurfacedPageRow: View {
    let page: BookPage
    let onOpen: () -> Void

    private var visualStyle: PageVisualStyle {
        PageVisualStyle.style(for: page.type)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Label(page.type.title, systemImage: "sparkle.magnifyingglass")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(visualStyle.accent)

                Spacer(minLength: 8)

                Text(page.createdAt, style: .date)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(BookPalette.ink.opacity(0.48))
            }

            Text(page.userInput)
                .font(.system(.callout, design: .serif, weight: .semibold))
                .lineSpacing(3)
                .foregroundStyle(BookPalette.ink.opacity(0.78))
                .lineLimit(4)

            Text("The Book brought this back because old wonder sometimes knows the way.")
                .font(.caption)
                .foregroundStyle(BookPalette.ink.opacity(0.56))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .parchmentSurface(style: visualStyle, isActive: false)
        .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .onTapGesture {
            onOpen()
        }
        .overlay(alignment: .topTrailing) {
            MarginaliaImage(name: visualStyle.sideMarginalia, width: 62, opacity: 0.24)
                .rotationEffect(.degrees(4))
                .offset(x: 12, y: -10)
                .allowsHitTesting(false)
        }
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Opens this returned page.")
    }
}

private struct CardScrapMark: View {
    let seed: String
    var style: PageVisualStyle = .default

    private var angle: Angle {
        .degrees(seed.stableHash.isMultiple(of: 2) ? -4 : 5)
    }

    var body: some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 3, style: .continuous)
                .fill(style.scrapColor.opacity(0.50))
                .frame(width: style.scrapWidth, height: style.scrapHeight)
                .overlay {
                    Image("ParchmentFiber")
                        .resizable()
                        .scaledToFill()
                        .opacity(0.34)
                        .blendMode(.multiply)
                        .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                }
                .overlay {
                    RoundedRectangle(cornerRadius: 3, style: .continuous)
                        .stroke(style.accent.opacity(0.24), lineWidth: 1)
                }
                .rotationEffect(angle)

            Rectangle()
                .fill(style.accent.opacity(0.23))
                .frame(width: 36, height: 9)
                .rotationEffect(.degrees(seed.stableHash.isMultiple(of: 3) ? 12 : -10))
                .offset(x: 34, y: -4)
                .blendMode(.multiply)

            Rectangle()
                .fill(BookPalette.ink.opacity(0.26))
                .frame(width: style.scrapWidth * 0.42, height: 1)
                .offset(x: 10, y: 10)

            Rectangle()
                .fill(BookPalette.ink.opacity(0.20))
                .frame(width: style.scrapWidth * 0.62, height: 1)
                .offset(x: 10, y: 18)
        }
        .opacity(0.94)
    }
}

struct BookOfYouCard: View {
    let page: BookPage
    let onOpen: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var inkVisible = false

    private let visualStyle = PageVisualStyle.style(for: .bookOfYou)

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Book of You", systemImage: "book.closed")
                .font(.caption.weight(.bold))
                .foregroundStyle(visualStyle.accent)

            if !page.mediaAssets.isEmpty {
                BookOfYouMediaStrip(assets: page.mediaAssets)
            }

            Text(page.userInput)
                .font(.system(.body, design: .serif))
                .lineSpacing(5)
                .foregroundStyle(BookPalette.ink)
                .fixedSize(horizontal: false, vertical: true)
                .opacity(inkVisible ? 1 : 0.16)
                .blur(radius: inkVisible ? 0 : 2.5)
                .shadow(color: BookPalette.lampGold.opacity(inkVisible ? 0.12 : 0.36), radius: inkVisible ? 2 : 10)
        }
        .padding(18)
        .parchmentSurface(style: visualStyle, isActive: true)
        .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .onTapGesture {
            onOpen()
        }
        .overlay(alignment: .topTrailing) {
            Text("kept")
                .font(.caption2.weight(.bold))
                .foregroundStyle(visualStyle.accent)
                .padding(12)
        }
        .overlay(alignment: .leading) {
            MarginaliaImage(name: visualStyle.sideMarginalia, width: 72, opacity: 0.34)
                .rotationEffect(.degrees(-9))
                .offset(x: -14, y: 26)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .bottomTrailing) {
            MarginaliaImage(name: visualStyle.cornerMarginalia, width: 76, opacity: 0.28)
                .rotationEffect(.degrees(-8))
                .offset(x: 12, y: 12)
                .allowsHitTesting(false)
        }
        .onAppear {
            inkVisible = false
            withAnimation(reduceMotion ? .linear(duration: 0.01) : .easeOut(duration: 1.45).delay(0.16)) {
                inkVisible = true
            }
        }
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Opens today's Book of You page.")
    }
}

private struct BookOfYouMediaStrip: View {
    let assets: [BookPageMediaAsset]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                ForEach(assets.prefix(6)) { asset in
                    BookOfYouMediaThumbnail(asset: asset)
                }
            }
            .padding(.vertical, 2)
        }
    }
}

private struct BookOfYouMediaThumbnail: View {
    let asset: BookPageMediaAsset
    var width: CGFloat = 104
    var height: CGFloat = 82

    var body: some View {
        Group {
            if let image {
                image
                    .resizable()
                    .scaledToFill()
            } else {
                ZStack {
                    BookPalette.page.opacity(0.72)
                    Image(systemName: "photo")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(BookPalette.ink.opacity(0.42))
                }
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
        }
        .shadow(color: .black.opacity(0.12), radius: 5, x: 0, y: 3)
        .accessibilityLabel(accessibilityLabel)
    }

    private var image: Image? {
        switch asset.kind {
        case .bundledImage:
            return Image(asset.reference)
        case .renderedImageFile:
            #if canImport(UIKit)
            if let uiImage = UIImage(contentsOfFile: asset.reference) {
                return Image(uiImage: uiImage)
            }
            #endif
            return nil
        case .photoLibraryAsset:
            return nil
        }
    }

    private var accessibilityLabel: String {
        let caption = asset.caption.trimmingCharacters(in: .whitespacesAndNewlines)
        return caption.isEmpty ? "Kept visual fragment" : caption
    }
}

struct ArchiveCard: View {
    let page: BookPage
    let onOpen: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(page.createdAt, style: .date)
                .font(.caption.weight(.bold))
                .foregroundStyle(BookPalette.teal)
            Text(page.userInput)
                .font(.footnote)
                .foregroundStyle(BookPalette.ink.opacity(0.72))
                .lineLimit(6)
        }
        .padding(14)
        .frame(width: 240, height: 170, alignment: .topLeading)
        .parchmentSurface(accent: BookPalette.gold, isActive: false)
        .contentShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .onTapGesture {
            onOpen()
        }
        .overlay(alignment: .bottomTrailing) {
            MarginaliaImage(name: "MarginaliaShell", width: 42, opacity: 0.16)
                .offset(x: 6, y: 8)
                .allowsHitTesting(false)
        }
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Opens this Book of You page.")
    }
}

struct EmptyBookCard: View {
    let title: String
    let message: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.subheadline.weight(.bold))
            Text(message)
                .font(.callout)
                .foregroundStyle(BookPalette.ink.opacity(0.66))
        }
        .foregroundStyle(BookPalette.ink)
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .parchmentSurface(accent: BookPalette.gold.opacity(0.7), isActive: false)
    }
}

struct MarginaliaImage: View {
    let name: String
    let width: CGFloat
    var opacity: Double = 0.28

    var body: some View {
        Image(name)
            .resizable()
            .scaledToFit()
            .frame(width: width)
            .opacity(opacity)
            .saturation(0.95)
            .shadow(color: .black.opacity(0.16), radius: 3, x: 0, y: 2)
    }
}

struct LivingMarginaliaImage: View {
    let name: String
    let width: CGFloat
    var opacity: Double = 0.28
    var glow = false

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var breath = false

    var body: some View {
        Image(name)
            .resizable()
            .scaledToFit()
            .frame(width: width)
            .opacity(opacity)
            .scaleEffect(breath && !reduceMotion ? 1.025 : 0.995)
            .shadow(color: BookPalette.lampGold.opacity(glow ? (breath ? 0.45 : 0.22) : 0.12), radius: glow ? (breath ? 16 : 8) : 3)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 4.8).repeatForever(autoreverses: true)) {
                    breath = true
                }
            }
    }
}

private func openingProgress(_ value: Double, from start: Double, to end: Double) -> Double {
    guard end > start else { return value >= end ? 1 : 0 }
    return smoothstep(min(max((value - start) / (end - start), 0), 1))
}

private func smoothstep(_ value: Double) -> Double {
    value * value * (3 - 2 * value)
}

/// Accumulates animation time from clamped per-frame deltas instead of wall
/// clock, so a main-thread stall (launch work, first-frame layout) pauses the
/// opening movie instead of making it skip ahead.
private final class StallTolerantClock {
    private var lastTick: Date?
    private(set) var elapsed: TimeInterval = 0

    func tick(_ now: Date, maxDelta: TimeInterval) -> TimeInterval {
        defer { lastTick = now }
        guard let lastTick else { return elapsed }
        let delta = now.timeIntervalSince(lastTick)
        guard delta > 0 else { return elapsed }
        elapsed += min(delta, maxDelta)
        return elapsed
    }
}

struct OpeningMovieView: View {
    let onFinished: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var clock = StallTolerantClock()
    @State private var didFinish = false

    private var duration: TimeInterval {
        reduceMotion ? 2.2 : 6.2
    }

    var body: some View {
        TimelineView(.animation(minimumInterval: reduceMotion ? 1 / 12 : 1 / 24)) { timeline in
            let elapsed = clock.tick(timeline.date, maxDelta: 1 / 8)
            let progress = min(max(elapsed / duration, 0), 1)

            GeometryReader { proxy in
                let size = proxy.size
                let fairy = fairyPosition(progress: progress, size: size)
                let wipe = openingProgress(progress, from: 0.82, to: 1.0)

                ZStack {
                    BookBackground()
                        .overlay {
                            Rectangle()
                                .fill(BookPalette.nightPanel.opacity(0.34))
                        }

                    VStack(spacing: 18) {
                        Spacer(minLength: size.height * 0.20)

                        WrittenGoldText(
                            "Real Life...",
                            font: .system(size: min(size.width * 0.12, 48), weight: .medium, design: .serif),
                            progress: openingProgress(progress, from: 0.08, to: reduceMotion ? 0.18 : 0.34)
                        )
                        .frame(maxWidth: .infinity, alignment: .center)

                        WrittenGoldText(
                            "ReEnchanted",
                            font: .system(size: min(size.width * 0.132, 54), weight: .semibold, design: .serif),
                            progress: openingProgress(progress, from: reduceMotion ? 0.20 : 0.32, to: reduceMotion ? 0.42 : 0.60)
                        )
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                        .frame(maxWidth: max(1, size.width - 54), alignment: .center)
                        .shadow(color: BookPalette.lampGold.opacity(0.22), radius: 18, x: 0, y: 6)

                        WrittenGoldText(
                            "By The Doobaleedoos",
                            font: .system(size: min(size.width * 0.060, 24), weight: .semibold, design: .serif),
                            progress: openingProgress(progress, from: reduceMotion ? 0.42 : 0.58, to: reduceMotion ? 0.58 : 0.74)
                        )
                        .kerning(1.2)
                        .textCase(.uppercase)

                        Spacer()

                        Text("patreon.com/thedoobaleedoos")
                            .font(.system(.footnote, design: .serif, weight: .semibold))
                            .tracking(1.1)
                            .foregroundStyle(BookPalette.nightText.opacity(0.80))
                            .opacity(openingProgress(progress, from: reduceMotion ? 0.56 : 0.70, to: reduceMotion ? 0.70 : 0.84))
                            .padding(.bottom, max(28, proxy.safeAreaInsets.bottom + 20))
                    }
                    .padding(.horizontal, 30)
                    .opacity(1 - wipe * 0.75)

                    FairyScribe()
                        .frame(width: 38, height: 38)
                        .position(fairy)
                        .opacity(progress < 0.95 ? 1 : 1 - openingProgress(progress, from: 0.95, to: 1.0))
                        .accessibilityHidden(true)

                    SparkleTrail(progress: progress, fairyPosition: fairy)
                        .allowsHitTesting(false)

                    PageTurnWipe(progress: wipe)
                        .allowsHitTesting(false)
                }
                .contentShape(Rectangle())
                .onTapGesture {
                    finish()
                }
                .onChange(of: progress) { _, newValue in
                    guard newValue >= 1 else { return }
                    finish()
                }
            }
        }
        .ignoresSafeArea()
        .onAppear {
            BookFeedback.play(.openPage)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Opening animation. Real Life, ReEnchanted. By The Doobaleedoos.")
        .accessibilityAddTraits(.isButton)
    }

    private func finish() {
        guard !didFinish else { return }
        didFinish = true
        BookFeedback.play(.braidComplete)
        onFinished()
    }

    private func fairyPosition(progress: Double, size: CGSize) -> CGPoint {
        let settled = CGPoint(x: size.width * 0.74, y: size.height * 0.38)
        if reduceMotion {
            return settled
        }

        let points = [
            CGPoint(x: size.width * 0.18, y: size.height * 0.30),
            CGPoint(x: size.width * 0.76, y: size.height * 0.30),
            CGPoint(x: size.width * 0.18, y: size.height * 0.43),
            CGPoint(x: size.width * 0.80, y: size.height * 0.43),
            CGPoint(x: size.width * 0.30, y: size.height * 0.51),
            CGPoint(x: size.width * 0.70, y: size.height * 0.51),
            settled
        ]

        let routeProgress = openingProgress(progress, from: 0.04, to: 0.80)
        let scaled = routeProgress * Double(points.count - 1)
        let index = min(Int(scaled), points.count - 2)
        let local = scaled - Double(index)
        let eased = smoothstep(local)
        let start = points[index]
        let end = points[index + 1]
        let bob = CGFloat(sin(progress * .pi * 18) * 4)

        return CGPoint(
            x: start.x + (end.x - start.x) * eased,
            y: start.y + (end.y - start.y) * eased + bob
        )
    }
}

struct WrittenGoldText: View {
    let text: String
    let font: Font
    let progress: Double

    init(_ text: String, font: Font, progress: Double) {
        self.text = text
        self.font = font
        self.progress = progress
    }

    var body: some View {
        Text(text)
            .font(font)
            .foregroundStyle(
                LinearGradient(
                    colors: [BookPalette.nightText, BookPalette.lampGold, BookPalette.gold],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .shadow(color: BookPalette.lampGold.opacity(0.30), radius: 10, x: 0, y: 4)
            .mask(alignment: .leading) {
                GeometryReader { proxy in
                    Rectangle()
                        .frame(width: max(1, proxy.size.width * progress))
                }
            }
            .overlay(alignment: .trailing) {
                if progress > 0 && progress < 1 {
                    Circle()
                        .fill(BookPalette.lampGold.opacity(0.46))
                        .frame(width: 9, height: 9)
                        .blur(radius: 3)
                        .offset(x: 8)
                }
            }
    }
}

struct FairyScribe: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false

    var body: some View {
        ZStack {
            wing(rotation: -28)
                .offset(x: -16, y: -4)
            wing(rotation: 28)
                .offset(x: 16, y: -4)

            Circle()
                .fill(
                    RadialGradient(
                        colors: [
                            .white,
                            BookPalette.lampGold,
                            BookPalette.gold.opacity(0.82),
                            BookPalette.lampGold.opacity(0.30),
                            .clear
                        ],
                        center: .center,
                        startRadius: 1,
                        endRadius: 24
                    )
                )
                .frame(width: 34, height: 34)
                .shadow(color: BookPalette.lampGold.opacity(pulse ? 0.82 : 0.42), radius: pulse ? 24 : 12)

            Circle()
                .fill(.white.opacity(0.88))
                .frame(width: 7, height: 7)
                .blur(radius: 1)
        }
        .scaleEffect(pulse && !reduceMotion ? 1.08 : 0.96)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.easeInOut(duration: 0.82).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
    }

    private func wing(rotation: Double) -> some View {
        Capsule()
            .fill(
                LinearGradient(
                    colors: [
                        BookPalette.nightText.opacity(0.84),
                        BookPalette.lampGold.opacity(0.54),
                        BookPalette.gold.opacity(0.26)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .frame(width: 11, height: 25)
            .rotationEffect(.degrees(rotation))
            .shadow(color: BookPalette.lampGold.opacity(0.45), radius: 8)
    }
}

struct SparkleTrail: View {
    let progress: Double
    let fairyPosition: CGPoint

    var body: some View {
        ZStack {
            ForEach(0..<24, id: \.self) { index in
                let age = Double(index) / 24
                let opacity = max(0, 0.68 - age * 0.58) * (1 - openingProgress(progress, from: 0.82, to: 0.98))
                let angle = Double(index) * 1.37 + progress * 10
                let radius = CGFloat(6 + index * 2)

                Image(systemName: index % 3 == 0 ? "sparkle" : "plus")
                    .font(.system(size: index % 3 == 0 ? 9 : 5, weight: .bold))
                    .foregroundStyle((index % 4 == 0 ? BookPalette.nightText : BookPalette.lampGold).opacity(opacity))
                    .position(
                        x: fairyPosition.x - CGFloat(cos(angle)) * radius - CGFloat(index),
                        y: fairyPosition.y - CGFloat(sin(angle)) * radius + CGFloat(index) * 0.7
                    )
            }
        }
    }
}

struct PageTurnWipe: View {
    let progress: Double

    var body: some View {
        GeometryReader { proxy in
            let width = max(1, proxy.size.width)
            let height = max(1, proxy.size.height)
            let x = width * (1.12 - progress * 1.42)

            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(BookPalette.page.opacity(progress))
                    .frame(width: width * 1.4, height: height * 1.2)
                    .offset(x: x)
                    .shadow(color: .black.opacity(0.30 * progress), radius: 24, x: -16, y: 0)

                Path { path in
                    path.move(to: CGPoint(x: x, y: -20))
                    path.addCurve(
                        to: CGPoint(x: x + width * 0.10, y: height + 20),
                        control1: CGPoint(x: x + width * 0.16, y: height * 0.22),
                        control2: CGPoint(x: x - width * 0.08, y: height * 0.74)
                    )
                    path.addLine(to: CGPoint(x: x + width * 0.20, y: height + 20))
                    path.addLine(to: CGPoint(x: x + width * 0.20, y: -20))
                    path.closeSubpath()
                }
                .fill(
                    LinearGradient(
                        colors: [
                            BookPalette.nightText.opacity(0.35 * progress),
                            BookPalette.parchmentEdge.opacity(0.72 * progress),
                            .black.opacity(0.16 * progress)
                        ],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .blur(radius: 0.6)
            }
        }
        .opacity(progress)
    }
}

struct BookBackground: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        let date = Date()

        LinearGradient(
            colors: [
                Color(red: 0.025, green: 0.027, blue: 0.060),
                Color(red: 0.060, green: 0.055, blue: 0.105),
                Color(red: 0.115, green: 0.074, blue: 0.088)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .overlay {
            LinearGradient(
                colors: [.clear, BookPalette.nightPanel.opacity(0.14)],
                startPoint: .top,
                endPoint: .bottom
            )
        }
        .overlay {
            LabyrinthBackdrop()
                .stroke(BookPalette.lampGold.opacity(0.10), lineWidth: 1)
                .frame(width: 380, height: 380)
                .offset(x: 120 + ambientDrift(date, scale: 8), y: -260 + ambientDrift(date, scale: 5, phase: 1.8))
                .blendMode(.plusLighter)
        }
        .overlay {
            StarSpeckle()
                .fill(BookPalette.lampGold.opacity(0.14 + ambientOpacity(date) * 0.05))
                .offset(x: ambientDrift(date, scale: 5, phase: 0.8), y: ambientDrift(date, scale: 7, phase: 2.2))
                .blendMode(.plusLighter)
        }
        .overlay(alignment: .bottomLeading) {
            MarginaliaImage(name: "MarginaliaLavender", width: 130, opacity: 0.11)
                .rotationEffect(.degrees(-8))
                .offset(x: -20, y: 32)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .bottomTrailing) {
            MarginaliaImage(name: "MarginaliaStar", width: 150, opacity: 0.08)
                .rotationEffect(.degrees(11))
                .offset(x: 36, y: 24)
                .allowsHitTesting(false)
        }
        .overlay {
            Rectangle()
                .fill(.black.opacity(0.18))
                .blendMode(.multiply)
        }
        .ignoresSafeArea()
    }

    private func ambientDrift(_ date: Date, scale: Double, phase: Double = 0) -> CGFloat {
        guard !reduceMotion else { return 0 }
        return CGFloat(sin(date.timeIntervalSinceReferenceDate / 18 + phase) * scale)
    }

    private func ambientOpacity(_ date: Date) -> Double {
        guard !reduceMotion else { return 0.2 }
        return (sin(date.timeIntervalSinceReferenceDate / 12) + 1) / 2
    }
}

enum BookPalette {
    static let ink = Color(red: 0.18, green: 0.14, blue: 0.10)
    static let page = Color(red: 0.97, green: 0.91, blue: 0.78)
    static let paper = Color(red: 0.91, green: 0.82, blue: 0.64)
    static let teal = Color(red: 0.08, green: 0.42, blue: 0.45)
    static let gold = Color(red: 0.72, green: 0.43, blue: 0.16)
    static let lampGold = Color(red: 0.95, green: 0.73, blue: 0.43)
    static let nightText = Color(red: 0.94, green: 0.86, blue: 0.72)
    static let nightPanel = Color(red: 0.055, green: 0.063, blue: 0.120)
    static let parchmentEdge = Color(red: 0.50, green: 0.31, blue: 0.14)
    static let violet = Color(red: 0.36, green: 0.19, blue: 0.30)
}

struct PageVisualStyle {
    var accent: Color
    var symbolColor: Color
    var paperTop: Color
    var paperMiddle: Color
    var paperBottom: Color
    var scrapColor: Color
    var sideMarginalia: String
    var cornerMarginalia: String
    var smallMarginalia: String
    var watermarkMarginalia: String
    var sideMarginaliaWidth: CGFloat = 56
    var cornerMarginaliaWidth: CGFloat = 70
    var sideMarginaliaOpacity: Double = 0.38
    var cornerMarginaliaOpacity: Double = 0.34
    var watermarkOpacity: Double = 0.10
    var fiberOpacity: Double = 0.24
    var grainOpacity: Double = 0.09
    var scrapWidth: CGFloat = 74
    var scrapHeight: CGFloat = 30

    static let `default` = PageVisualStyle(
        accent: BookPalette.gold,
        symbolColor: BookPalette.gold,
        paperTop: BookPalette.page,
        paperMiddle: BookPalette.paper,
        paperBottom: Color(red: 0.80, green: 0.64, blue: 0.42),
        scrapColor: BookPalette.paper,
        sideMarginalia: "IlluminationScrapS01_15",
        cornerMarginalia: "IlluminationScrapS02_05",
        smallMarginalia: "IlluminationScrapS03_10",
        watermarkMarginalia: "IlluminationScrapS02_13"
    )

    static func style(for type: BookPageType) -> PageVisualStyle {
        switch type {
        case .calendar:
            return PageVisualStyle(
                accent: Color(red: 0.30, green: 0.34, blue: 0.58),
                symbolColor: Color(red: 0.30, green: 0.34, blue: 0.58),
                paperTop: Color(red: 0.94, green: 0.92, blue: 0.82),
                paperMiddle: Color(red: 0.84, green: 0.82, blue: 0.72),
                paperBottom: Color(red: 0.66, green: 0.65, blue: 0.58),
                scrapColor: Color(red: 0.86, green: 0.85, blue: 0.76),
                sideMarginalia: "IlluminationScrapS02_08",
                cornerMarginalia: "IlluminationScrapS03_24",
                smallMarginalia: "MarginaliaStamp",
                watermarkMarginalia: "MarginaliaCompass",
                watermarkOpacity: 0.10
            )
        case .packPage:
            return PageVisualStyle(
                accent: Color(red: 0.33, green: 0.36, blue: 0.52),
                symbolColor: Color(red: 0.33, green: 0.36, blue: 0.52),
                paperTop: Color(red: 0.94, green: 0.91, blue: 0.81),
                paperMiddle: Color(red: 0.84, green: 0.80, blue: 0.71),
                paperBottom: Color(red: 0.66, green: 0.62, blue: 0.56),
                scrapColor: Color(red: 0.87, green: 0.84, blue: 0.76),
                sideMarginalia: "IlluminationScrapS03_11",
                cornerMarginalia: "IlluminationScrapS02_19",
                smallMarginalia: "MarginaliaStar",
                watermarkMarginalia: "MarginaliaStar",
                watermarkOpacity: 0.10
            )
        case .helpTips:
            return PageVisualStyle(
                accent: Color(red: 0.20, green: 0.43, blue: 0.50),
                symbolColor: Color(red: 0.20, green: 0.43, blue: 0.50),
                paperTop: Color(red: 0.95, green: 0.91, blue: 0.78),
                paperMiddle: Color(red: 0.84, green: 0.80, blue: 0.66),
                paperBottom: Color(red: 0.66, green: 0.62, blue: 0.52),
                scrapColor: Color(red: 0.86, green: 0.83, blue: 0.70),
                sideMarginalia: "IlluminationScrapS01_08",
                cornerMarginalia: "IlluminationScrapS03_10",
                smallMarginalia: "MarginaliaCompass",
                watermarkMarginalia: "MarginaliaStamp",
                sideMarginaliaWidth: 62,
                cornerMarginaliaWidth: 78,
                sideMarginaliaOpacity: 0.38,
                cornerMarginaliaOpacity: 0.34,
                watermarkOpacity: 0.10,
                scrapWidth: 88,
                scrapHeight: 32
            )
        case .welcome:
            return PageVisualStyle(
                accent: Color(red: 0.40, green: 0.32, blue: 0.58),
                symbolColor: Color(red: 0.40, green: 0.32, blue: 0.58),
                paperTop: Color(red: 0.96, green: 0.91, blue: 0.76),
                paperMiddle: Color(red: 0.86, green: 0.78, blue: 0.64),
                paperBottom: Color(red: 0.66, green: 0.56, blue: 0.50),
                scrapColor: Color(red: 0.90, green: 0.82, blue: 0.68),
                sideMarginalia: "MarginaliaCompass",
                cornerMarginalia: "MarginaliaSeal",
                smallMarginalia: "MarginaliaStar",
                watermarkMarginalia: "MarginaliaCompass",
                sideMarginaliaWidth: 70,
                cornerMarginaliaWidth: 84,
                sideMarginaliaOpacity: 0.40,
                cornerMarginaliaOpacity: 0.36,
                watermarkOpacity: 0.13,
                scrapWidth: 94,
                scrapHeight: 34
            )
        case .elective:
            // Folded-note warmth: wine accent, feather marginalia, the feel
            // of a favor tucked into the binding.
            return PageVisualStyle(
                accent: Color(red: 0.52, green: 0.26, blue: 0.30),
                symbolColor: Color(red: 0.52, green: 0.26, blue: 0.30),
                paperTop: Color(red: 0.97, green: 0.91, blue: 0.78),
                paperMiddle: Color(red: 0.89, green: 0.79, blue: 0.64),
                paperBottom: Color(red: 0.72, green: 0.58, blue: 0.46),
                scrapColor: Color(red: 0.94, green: 0.84, blue: 0.68),
                sideMarginalia: "MarginaliaFeather",
                cornerMarginalia: "IlluminationScrapS03_12",
                smallMarginalia: "MarginaliaStamp",
                watermarkMarginalia: "MarginaliaSeal",
                watermarkOpacity: 0.12
            )
        case .academyClass:
            // Chalk-and-lamplight: slate-toned paper, gold accents, compass
            // watermark — the feel of a lesson under way.
            return PageVisualStyle(
                accent: Color(red: 0.27, green: 0.40, blue: 0.46),
                symbolColor: Color(red: 0.27, green: 0.40, blue: 0.46),
                paperTop: Color(red: 0.93, green: 0.90, blue: 0.79),
                paperMiddle: Color(red: 0.82, green: 0.80, blue: 0.70),
                paperBottom: Color(red: 0.62, green: 0.63, blue: 0.57),
                scrapColor: Color(red: 0.83, green: 0.84, blue: 0.74),
                sideMarginalia: "IlluminationScrapS02_08",
                cornerMarginalia: "IlluminationScrapS01_14",
                smallMarginalia: "IlluminationScrapS03_10",
                watermarkMarginalia: "MarginaliaCompass",
                watermarkOpacity: 0.11
            )
        case .mood:
            return PageVisualStyle(
                accent: Color(red: 0.36, green: 0.39, blue: 0.70),
                symbolColor: Color(red: 0.36, green: 0.39, blue: 0.70),
                paperTop: Color(red: 0.93, green: 0.90, blue: 0.77),
                paperMiddle: Color(red: 0.78, green: 0.80, blue: 0.68),
                paperBottom: Color(red: 0.65, green: 0.66, blue: 0.56),
                scrapColor: Color(red: 0.79, green: 0.82, blue: 0.72),
                sideMarginalia: "IlluminationScrapS03_11",
                cornerMarginalia: "IlluminationScrapS02_04",
                smallMarginalia: "IlluminationScrapS03_10",
                watermarkMarginalia: "MarginaliaCompass",
                watermarkOpacity: 0.13
            )
        case .diary:
            return PageVisualStyle(
                accent: Color(red: 0.42, green: 0.31, blue: 0.54),
                symbolColor: Color(red: 0.42, green: 0.31, blue: 0.54),
                paperTop: Color(red: 0.96, green: 0.91, blue: 0.78),
                paperMiddle: Color(red: 0.88, green: 0.80, blue: 0.66),
                paperBottom: Color(red: 0.70, green: 0.60, blue: 0.49),
                scrapColor: Color(red: 0.95, green: 0.86, blue: 0.70),
                sideMarginalia: "IlluminationScrapS02_08",
                cornerMarginalia: "IlluminationScrapS03_12",
                smallMarginalia: "IlluminationScrapS01_08",
                watermarkMarginalia: "IlluminationScrapS02_13",
                watermarkOpacity: 0.11
            )
        case .souvenir:
            return PageVisualStyle(
                accent: BookPalette.gold,
                symbolColor: BookPalette.gold,
                paperTop: Color(red: 0.98, green: 0.90, blue: 0.71),
                paperMiddle: Color(red: 0.92, green: 0.76, blue: 0.52),
                paperBottom: Color(red: 0.76, green: 0.56, blue: 0.35),
                scrapColor: Color(red: 0.98, green: 0.86, blue: 0.62),
                sideMarginalia: "IlluminationScrapS01_20",
                cornerMarginalia: "IlluminationScrapS03_24",
                smallMarginalia: "IlluminationScrapS01_21",
                watermarkMarginalia: "MarginaliaShell",
                sideMarginaliaWidth: 58,
                cornerMarginaliaWidth: 76,
                watermarkOpacity: 0.12
            )
        case .rest:
            return PageVisualStyle(
                accent: Color(red: 0.45, green: 0.36, blue: 0.58),
                symbolColor: Color(red: 0.45, green: 0.36, blue: 0.58),
                paperTop: Color(red: 0.92, green: 0.88, blue: 0.78),
                paperMiddle: Color(red: 0.81, green: 0.77, blue: 0.69),
                paperBottom: Color(red: 0.64, green: 0.58, blue: 0.53),
                scrapColor: Color(red: 0.84, green: 0.79, blue: 0.74),
                sideMarginalia: "IlluminationScrapS02_18",
                cornerMarginalia: "IlluminationScrapS02_19",
                smallMarginalia: "MarginaliaLavender",
                watermarkMarginalia: "MarginaliaLavender",
                sideMarginaliaWidth: 64,
                sideMarginaliaOpacity: 0.46,
                cornerMarginaliaOpacity: 0.28,
                watermarkOpacity: 0.09
            )
        case .body:
            return PageVisualStyle(
                accent: Color(red: 0.22, green: 0.48, blue: 0.38),
                symbolColor: Color(red: 0.22, green: 0.48, blue: 0.38),
                paperTop: Color(red: 0.91, green: 0.88, blue: 0.72),
                paperMiddle: Color(red: 0.78, green: 0.77, blue: 0.61),
                paperBottom: Color(red: 0.63, green: 0.62, blue: 0.50),
                scrapColor: Color(red: 0.77, green: 0.82, blue: 0.66),
                sideMarginalia: "IlluminationScrapS02_26",
                cornerMarginalia: "IlluminationScrapS01_14",
                smallMarginalia: "IlluminationScrapS03_25",
                watermarkMarginalia: "MarginaliaLavender",
                watermarkOpacity: 0.10
            )
        case .fuel:
            return PageVisualStyle(
                accent: Color(red: 0.42, green: 0.48, blue: 0.22),
                symbolColor: Color(red: 0.42, green: 0.48, blue: 0.22),
                paperTop: Color(red: 0.95, green: 0.89, blue: 0.70),
                paperMiddle: Color(red: 0.82, green: 0.78, blue: 0.57),
                paperBottom: Color(red: 0.66, green: 0.61, blue: 0.43),
                scrapColor: Color(red: 0.86, green: 0.80, blue: 0.58),
                sideMarginalia: "IlluminationScrapS01_14",
                cornerMarginalia: "IlluminationScrapS02_26",
                smallMarginalia: "IlluminationScrapS03_25",
                watermarkMarginalia: "MarginaliaShell",
                sideMarginaliaOpacity: 0.40,
                watermarkOpacity: 0.11
            )
        case .supportGuild:
            return PageVisualStyle(
                accent: Color(red: 0.36, green: 0.48, blue: 0.50),
                symbolColor: Color(red: 0.36, green: 0.48, blue: 0.50),
                paperTop: Color(red: 0.94, green: 0.88, blue: 0.74),
                paperMiddle: Color(red: 0.79, green: 0.74, blue: 0.62),
                paperBottom: Color(red: 0.61, green: 0.56, blue: 0.50),
                scrapColor: Color(red: 0.82, green: 0.78, blue: 0.66),
                sideMarginalia: "IlluminationScrapS02_26",
                cornerMarginalia: "IlluminationScrapS02_12",
                smallMarginalia: "MarginaliaSeal",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 70,
                cornerMarginaliaWidth: 84,
                sideMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.12,
                scrapWidth: 92
            )
        case .facultyResearch:
            return PageVisualStyle(
                accent: Color(red: 0.43, green: 0.34, blue: 0.58),
                symbolColor: Color(red: 0.43, green: 0.34, blue: 0.58),
                paperTop: Color(red: 0.93, green: 0.86, blue: 0.75),
                paperMiddle: Color(red: 0.78, green: 0.70, blue: 0.66),
                paperBottom: Color(red: 0.58, green: 0.50, blue: 0.54),
                scrapColor: Color(red: 0.82, green: 0.72, blue: 0.70),
                sideMarginalia: "IlluminationScrapS03_24",
                cornerMarginalia: "IlluminationScrapS02_13",
                smallMarginalia: "MarginaliaFeather",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 66,
                cornerMarginaliaWidth: 82,
                sideMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.12,
                scrapWidth: 92
            )
        case .letter:
            return PageVisualStyle(
                accent: Color(red: 0.48, green: 0.30, blue: 0.36),
                symbolColor: Color(red: 0.48, green: 0.30, blue: 0.36),
                paperTop: Color(red: 0.96, green: 0.89, blue: 0.76),
                paperMiddle: Color(red: 0.86, green: 0.76, blue: 0.64),
                paperBottom: Color(red: 0.68, green: 0.55, blue: 0.48),
                scrapColor: Color(red: 0.92, green: 0.80, blue: 0.66),
                sideMarginalia: "MarginaliaFeather",
                cornerMarginalia: "MarginaliaSeal",
                smallMarginalia: "IlluminationScrapS02_13",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 58,
                cornerMarginaliaWidth: 82,
                sideMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.11,
                scrapWidth: 88
            )
        case .weather, .location:
            return PageVisualStyle(
                accent: Color(red: 0.12, green: 0.45, blue: 0.54),
                symbolColor: Color(red: 0.12, green: 0.45, blue: 0.54),
                paperTop: Color(red: 0.88, green: 0.87, blue: 0.74),
                paperMiddle: Color(red: 0.70, green: 0.77, blue: 0.70),
                paperBottom: Color(red: 0.50, green: 0.61, blue: 0.58),
                scrapColor: Color(red: 0.77, green: 0.85, blue: 0.78),
                sideMarginalia: "IlluminationScrapS01_08",
                cornerMarginalia: "IlluminationScrapS01_09",
                smallMarginalia: "MarginaliaShell",
                watermarkMarginalia: "MarginaliaShell",
                sideMarginaliaWidth: 62,
                cornerMarginaliaWidth: 78,
                sideMarginaliaOpacity: 0.42,
                cornerMarginaliaOpacity: 0.34,
                watermarkOpacity: 0.13
            )
        case .quip:
            return PageVisualStyle(
                accent: Color(red: 0.70, green: 0.33, blue: 0.18),
                symbolColor: Color(red: 0.70, green: 0.33, blue: 0.18),
                paperTop: Color(red: 0.99, green: 0.87, blue: 0.62),
                paperMiddle: Color(red: 0.92, green: 0.70, blue: 0.44),
                paperBottom: Color(red: 0.72, green: 0.48, blue: 0.30),
                scrapColor: Color(red: 0.97, green: 0.78, blue: 0.50),
                sideMarginalia: "IlluminationScrapS03_10",
                cornerMarginalia: "IlluminationScrapS03_11",
                smallMarginalia: "MarginaliaStar",
                watermarkMarginalia: "MarginaliaStar",
                sideMarginaliaWidth: 54,
                watermarkOpacity: 0.16
            )
        case .aboutYou:
            return PageVisualStyle(
                accent: Color(red: 0.55, green: 0.28, blue: 0.39),
                symbolColor: Color(red: 0.55, green: 0.28, blue: 0.39),
                paperTop: Color(red: 0.96, green: 0.86, blue: 0.76),
                paperMiddle: Color(red: 0.88, green: 0.70, blue: 0.66),
                paperBottom: Color(red: 0.68, green: 0.50, blue: 0.52),
                scrapColor: Color(red: 0.92, green: 0.74, blue: 0.68),
                sideMarginalia: "IlluminationScrapS02_12",
                cornerMarginalia: "IlluminationScrapS02_13",
                smallMarginalia: "MarginaliaFeather",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaOpacity: 0.40,
                watermarkOpacity: 0.11
            )
        case .wonderCompass:
            return PageVisualStyle(
                accent: BookPalette.gold,
                symbolColor: BookPalette.gold,
                paperTop: Color(red: 0.99, green: 0.89, blue: 0.66),
                paperMiddle: Color(red: 0.91, green: 0.72, blue: 0.44),
                paperBottom: Color(red: 0.69, green: 0.46, blue: 0.24),
                scrapColor: Color(red: 0.98, green: 0.82, blue: 0.52),
                sideMarginalia: "IlluminationScrapS01_02",
                cornerMarginalia: "IlluminationScrapS01_03",
                smallMarginalia: "MarginaliaCompass",
                watermarkMarginalia: "MarginaliaCompass",
                sideMarginaliaWidth: 68,
                cornerMarginaliaWidth: 84,
                sideMarginaliaOpacity: 0.42,
                cornerMarginaliaOpacity: 0.40,
                watermarkOpacity: 0.15,
                scrapWidth: 86
            )
        case .lore, .narrativeOS, .marginsAtlas, .bookRemembered:
            return PageVisualStyle(
                accent: BookPalette.violet,
                symbolColor: BookPalette.violet,
                paperTop: Color(red: 0.92, green: 0.82, blue: 0.70),
                paperMiddle: Color(red: 0.76, green: 0.66, blue: 0.63),
                paperBottom: Color(red: 0.54, green: 0.44, blue: 0.48),
                scrapColor: Color(red: 0.80, green: 0.70, blue: 0.70),
                sideMarginalia: "IlluminationScrapS03_24",
                cornerMarginalia: "IlluminationScrapS03_25",
                smallMarginalia: "IlluminationScrapS03_10",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 66,
                cornerMarginaliaWidth: 82,
                sideMarginaliaOpacity: 0.44,
                cornerMarginaliaOpacity: 0.40,
                watermarkOpacity: 0.14,
                scrapWidth: 92,
                scrapHeight: 34
            )
        case .gossip:
            return PageVisualStyle(
                accent: Color(red: 0.78, green: 0.50, blue: 0.26),
                symbolColor: Color(red: 0.78, green: 0.50, blue: 0.26),
                paperTop: Color(red: 0.95, green: 0.84, blue: 0.67),
                paperMiddle: Color(red: 0.82, green: 0.66, blue: 0.54),
                paperBottom: Color(red: 0.58, green: 0.43, blue: 0.42),
                scrapColor: Color(red: 0.88, green: 0.72, blue: 0.57),
                sideMarginalia: "IlluminationScrapS02_21",
                cornerMarginalia: "IlluminationScrapS03_16",
                smallMarginalia: "IlluminationScrapS03_08",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 72,
                cornerMarginaliaWidth: 86,
                sideMarginaliaOpacity: 0.48,
                cornerMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.16,
                scrapWidth: 92,
                scrapHeight: 34
            )
        case .castMember:
            return PageVisualStyle(
                accent: Color(red: 0.34, green: 0.45, blue: 0.30),
                symbolColor: Color(red: 0.34, green: 0.45, blue: 0.30),
                paperTop: Color(red: 0.94, green: 0.88, blue: 0.70),
                paperMiddle: Color(red: 0.78, green: 0.74, blue: 0.58),
                paperBottom: Color(red: 0.56, green: 0.55, blue: 0.42),
                scrapColor: Color(red: 0.82, green: 0.78, blue: 0.60),
                sideMarginalia: "IlluminationScrapS02_08",
                cornerMarginalia: "IlluminationScrapS01_15",
                smallMarginalia: "MarginaliaStamp",
                watermarkMarginalia: "MarginaliaStamp",
                sideMarginaliaWidth: 68,
                cornerMarginaliaWidth: 82,
                sideMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.12,
                scrapWidth: 88,
                scrapHeight: 34
            )
        case .patreon:
            return PageVisualStyle(
                accent: Color(red: 0.60, green: 0.26, blue: 0.22),
                symbolColor: Color(red: 0.60, green: 0.26, blue: 0.22),
                paperTop: Color(red: 0.96, green: 0.83, blue: 0.67),
                paperMiddle: Color(red: 0.86, green: 0.62, blue: 0.50),
                paperBottom: Color(red: 0.62, green: 0.38, blue: 0.34),
                scrapColor: Color(red: 0.87, green: 0.62, blue: 0.55),
                sideMarginalia: "IlluminationScrapS02_05",
                cornerMarginalia: "IlluminationScrapS02_04",
                smallMarginalia: "IlluminationScrapS01_21",
                watermarkMarginalia: "MarginaliaSeal",
                cornerMarginaliaWidth: 86,
                cornerMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.14
            )
        case .illustration:
            return PageVisualStyle(
                accent: Color(red: 0.30, green: 0.44, blue: 0.54),
                symbolColor: Color(red: 0.30, green: 0.44, blue: 0.54),
                paperTop: Color(red: 0.92, green: 0.84, blue: 0.70),
                paperMiddle: Color(red: 0.75, green: 0.68, blue: 0.58),
                paperBottom: Color(red: 0.52, green: 0.48, blue: 0.44),
                scrapColor: Color(red: 0.80, green: 0.74, blue: 0.64),
                sideMarginalia: "IlluminationScrapS03_24",
                cornerMarginalia: "IlluminationScrapS01_15",
                smallMarginalia: "IlluminationScrapS03_11",
                watermarkMarginalia: "MarginaliaStamp",
                sideMarginaliaWidth: 68,
                watermarkOpacity: 0.13
            )
        case .illuminatedPhoto:
            return PageVisualStyle(
                accent: Color(red: 0.58, green: 0.31, blue: 0.17),
                symbolColor: Color(red: 0.58, green: 0.31, blue: 0.17),
                paperTop: Color(red: 0.96, green: 0.84, blue: 0.66),
                paperMiddle: Color(red: 0.82, green: 0.63, blue: 0.46),
                paperBottom: Color(red: 0.56, green: 0.39, blue: 0.30),
                scrapColor: Color(red: 0.91, green: 0.72, blue: 0.54),
                sideMarginalia: "IlluminationScrapS01_14",
                cornerMarginalia: "IlluminationScrapS02_27",
                smallMarginalia: "IlluminationScrapS03_25",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 76,
                cornerMarginaliaWidth: 90,
                sideMarginaliaOpacity: 0.46,
                cornerMarginaliaOpacity: 0.44,
                watermarkOpacity: 0.15,
                scrapWidth: 96,
                scrapHeight: 34
            )
        case .enchantment:
            return PageVisualStyle(
                accent: BookPalette.teal,
                symbolColor: BookPalette.lampGold,
                paperTop: Color(red: 0.96, green: 0.84, blue: 0.66),
                paperMiddle: Color(red: 0.82, green: 0.66, blue: 0.48),
                paperBottom: Color(red: 0.56, green: 0.42, blue: 0.31),
                scrapColor: Color(red: 0.91, green: 0.74, blue: 0.55),
                sideMarginalia: "IlluminationScrapS01_14",
                cornerMarginalia: "IlluminationScrapS02_27",
                smallMarginalia: "MarginaliaStar",
                watermarkMarginalia: "MarginaliaSeal",
                sideMarginaliaWidth: 76,
                cornerMarginaliaWidth: 90,
                sideMarginaliaOpacity: 0.46,
                cornerMarginaliaOpacity: 0.44,
                watermarkOpacity: 0.15,
                scrapWidth: 96,
                scrapHeight: 34
            )
        case .anchor:
            return PageVisualStyle(
                accent: Color(red: 0.18, green: 0.45, blue: 0.42),
                symbolColor: Color(red: 0.18, green: 0.45, blue: 0.42),
                paperTop: Color(red: 0.93, green: 0.86, blue: 0.67),
                paperMiddle: Color(red: 0.76, green: 0.70, blue: 0.53),
                paperBottom: Color(red: 0.48, green: 0.48, blue: 0.40),
                scrapColor: Color(red: 0.80, green: 0.75, blue: 0.57),
                sideMarginalia: "MarginaliaCompass",
                cornerMarginalia: "IlluminationScrapS02_13",
                smallMarginalia: "MarginaliaSeal",
                watermarkMarginalia: "MarginaliaCompass",
                sideMarginaliaWidth: 72,
                cornerMarginaliaWidth: 86,
                sideMarginaliaOpacity: 0.40,
                cornerMarginaliaOpacity: 0.36,
                watermarkOpacity: 0.14,
                scrapWidth: 92,
                scrapHeight: 34
            )
        case .bookOfYou:
            return PageVisualStyle(
                accent: BookPalette.teal,
                symbolColor: BookPalette.teal,
                paperTop: Color(red: 0.97, green: 0.91, blue: 0.76),
                paperMiddle: Color(red: 0.87, green: 0.75, blue: 0.56),
                paperBottom: Color(red: 0.66, green: 0.52, blue: 0.39),
                scrapColor: Color(red: 0.88, green: 0.78, blue: 0.60),
                sideMarginalia: "IlluminationScrapS01_20",
                cornerMarginalia: "IlluminationScrapS01_03",
                smallMarginalia: "MarginaliaStar",
                watermarkMarginalia: "MarginaliaStamp",
                sideMarginaliaWidth: 70,
                cornerMarginaliaWidth: 84,
                sideMarginaliaOpacity: 0.42,
                watermarkOpacity: 0.13
            )
        case .askTheBook:
            return PageVisualStyle(
                accent: Color(red: 0.18, green: 0.50, blue: 0.55),
                symbolColor: Color(red: 0.18, green: 0.50, blue: 0.55),
                paperTop: Color(red: 0.95, green: 0.88, blue: 0.72),
                paperMiddle: Color(red: 0.78, green: 0.75, blue: 0.62),
                paperBottom: Color(red: 0.55, green: 0.55, blue: 0.50),
                scrapColor: Color(red: 0.82, green: 0.79, blue: 0.66),
                sideMarginalia: "IlluminationScrapS03_10",
                cornerMarginalia: "IlluminationScrapS01_20",
                smallMarginalia: "MarginaliaCompass",
                watermarkMarginalia: "MarginaliaStamp",
                sideMarginaliaWidth: 66,
                cornerMarginaliaWidth: 82,
                sideMarginaliaOpacity: 0.40,
                watermarkOpacity: 0.12,
                scrapWidth: 90
            )
        }
    }
}

private struct ParchmentSurface: ViewModifier {
    let accent: Color
    var style: PageVisualStyle?
    let isActive: Bool

    private var resolved: PageVisualStyle {
        style ?? {
            var fallback = PageVisualStyle.default
            fallback.accent = accent
            fallback.symbolColor = accent
            return fallback
        }()
    }

    func body(content: Content) -> some View {
        content
            .background {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                resolved.paperTop,
                                resolved.paperMiddle,
                                resolved.paperBottom
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .shadow(color: .black.opacity(0.28), radius: 14, x: 0, y: 8)
            }
            .overlay {
                Image("ParchmentFiber")
                    .resizable()
                    .scaledToFill()
                    .opacity(isActive ? resolved.fiberOpacity : max(0.10, resolved.fiberOpacity * 0.62))
                    .blendMode(.multiply)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            .overlay {
                ParchmentGrain()
                    .fill(BookPalette.ink.opacity(resolved.grainOpacity))
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(BookPalette.parchmentEdge.opacity(0.38), lineWidth: 1)
            }
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(resolved.accent.opacity(isActive ? 0.48 : 0.22), lineWidth: 1)
                    .padding(2)
            }
    }
}

extension View {
    func storyFieldSmallText() -> some View {
        self
            .font(.caption.weight(.semibold))
            .foregroundStyle(BookPalette.ink.opacity(0.62))
            .fixedSize(horizontal: false, vertical: true)
    }

    func parchmentSurface(accent: Color = BookPalette.gold, isActive: Bool = false) -> some View {
        modifier(ParchmentSurface(accent: accent, style: nil, isActive: isActive))
    }

    func parchmentSurface(style: PageVisualStyle, isActive: Bool = false) -> some View {
        modifier(ParchmentSurface(accent: style.accent, style: style, isActive: isActive))
    }

    func sectionRuneLabel() -> some View {
        self
            .font(.system(.caption, design: .serif, weight: .semibold))
            .textCase(.uppercase)
            .kerning(2)
            .foregroundStyle(BookPalette.lampGold)
    }
}

/// A blobby, hand-pressed wax seal edge: a circle with small cosine wobbles so
/// no two seals (and no two presses) read as the same machine-cut disc.
struct WaxSealShape: Shape {
    var seed: Int = 0

    func path(in rect: CGRect) -> Path {
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let baseRadius = min(rect.width, rect.height) / 2
        var path = Path()
        let lobes = 9 + (abs(seed) % 3)
        let phase = Double(abs(seed) % 17) / 17 * 2 * .pi
        let secondPhase = Double(abs(seed) % 7) / 7 * 2 * .pi
        let steps = 96
        for step in 0...steps {
            let angle = Double(step) / Double(steps) * 2 * .pi
            let wobble = 1
                + 0.045 * cos(Double(lobes) * angle + phase)
                + 0.022 * cos(Double(lobes * 2 + 1) * angle + secondPhase)
            let radius = baseRadius * wobble
            let point = CGPoint(
                x: center.x + radius * cos(angle),
                y: center.y + radius * sin(angle)
            )
            if step == 0 {
                path.move(to: point)
            } else {
                path.addLine(to: point)
            }
        }
        path.closeSubpath()
        return path
    }
}

/// One of the three marginalia seals pressed into the page top: Body, Weather,
/// Location. Wax-toned, embossed, with a per-seal tilt and a breathing shimmer
/// while its doorway is working.
struct MarginaliaSealButton: View {
    let title: String
    let systemImage: String
    let wax: Color
    let seed: Int
    let isBusy: Bool
    let action: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isPressed = false

    private var tilt: Double {
        Double((abs(seed) % 7)) - 3
    }

    var body: some View {
        Button {
            guard !isBusy else { return }
            action()
        } label: {
            VStack(spacing: 7) {
                ZStack {
                    WaxSealShape(seed: seed)
                        .fill(
                            RadialGradient(
                                colors: [
                                    wax.opacity(0.98),
                                    wax.opacity(0.86),
                                    wax.opacity(0.62)
                                ],
                                center: .init(x: 0.38, y: 0.34),
                                startRadius: 2,
                                endRadius: 46
                            )
                        )
                        .overlay {
                            WaxSealShape(seed: seed)
                                .stroke(.black.opacity(0.22), lineWidth: 1)
                        }
                        .overlay {
                            WaxSealShape(seed: seed &+ 31)
                                .stroke(.white.opacity(0.30), lineWidth: 1.1)
                                .padding(7)
                        }
                        .shadow(color: .black.opacity(0.34), radius: 6, x: 0, y: 4)

                    Image(systemName: systemImage)
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(.black.opacity(0.32))
                        .offset(x: 0.8, y: 1.2)
                    Image(systemName: systemImage)
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(.white.opacity(0.88))
                        .shadow(color: wax.opacity(0.8), radius: 5)

                    if isBusy {
                        WaxSealShape(seed: seed)
                            .fill(.white.opacity(0.14))
                        ProgressView()
                            .tint(.white)
                            .scaleEffect(0.8)
                            .offset(y: 22)
                    }
                }
                .frame(width: 64, height: 64)
                .rotationEffect(.degrees(reduceMotion ? 0 : tilt))
                .scaleEffect(isPressed && !reduceMotion ? 0.92 : 1)

                Text(title)
                    .font(.system(.caption2, design: .serif, weight: .bold))
                    .textCase(.uppercase)
                    .kerning(1.1)
                    .foregroundStyle(BookPalette.nightText.opacity(0.82))
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(isBusy)
        .onLongPressGesture(minimumDuration: .infinity, pressing: { pressing in
            withAnimation(.spring(response: 0.28, dampingFraction: 0.6)) {
                isPressed = pressing
            }
        }, perform: {})
        .accessibilityLabel("\(title) seal")
        .accessibilityHint(isBusy ? "Working" : "Press to open")
    }
}

private struct ParchmentGrain: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let points: [(CGFloat, CGFloat, CGFloat)] = [
            (0.08, 0.14, 1.4), (0.18, 0.72, 1.0), (0.31, 0.24, 0.8),
            (0.46, 0.82, 1.2), (0.58, 0.38, 0.9), (0.72, 0.18, 1.1),
            (0.82, 0.64, 1.5), (0.92, 0.30, 0.7), (0.38, 0.55, 1.0)
        ]
        for point in points {
            let center = CGPoint(x: rect.minX + rect.width * point.0, y: rect.minY + rect.height * point.1)
            path.addEllipse(in: CGRect(x: center.x, y: center.y, width: point.2, height: point.2))
        }
        return path
    }
}

private struct PageCurl: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.maxX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.addQuadCurve(
            to: CGPoint(x: rect.minX, y: rect.minY),
            control: CGPoint(x: rect.maxX * 0.74, y: rect.maxY * 0.18)
        )
        path.closeSubpath()
        return path
    }
}

private struct StarSpeckle: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        for index in 0..<72 {
            let x = rect.minX + rect.width * CGFloat((index * 37) % 100) / 100
            let y = rect.minY + rect.height * CGFloat((index * 61) % 100) / 100
            let size = CGFloat((index % 3) + 1)
            path.addEllipse(in: CGRect(x: x, y: y, width: size, height: size))
        }
        return path
    }
}

private struct LabyrinthBackdrop: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let center = CGPoint(x: rect.midX, y: rect.midY)
        for index in 0..<7 {
            let inset = CGFloat(index) * rect.width * 0.065
            path.addArc(
                center: center,
                radius: rect.width * 0.46 - inset,
                startAngle: .degrees(Double(index) * 18 + 20),
                endAngle: .degrees(Double(index) * 18 + 300),
                clockwise: false
            )
        }
        return path
    }
}

/// First-run story onboarding, adapted from Enchantify's Academy tutorial:
/// the fall into the book, the guide, the snack question, the name, and the
/// core belief with its first planted investment.
struct OnboardingFlowView: View {
    struct Result {
        var snack: String
        var name: String
        var belief: String
        var investedBelief: Bool
    }

    let onFinished: (Result) -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var step = 0
    @State private var snack = ""
    @State private var name = ""
    @State private var belief = ""
    @State private var investedBelief = false

    private let stepCount = 5

    var body: some View {
        ZStack {
            BookBackground()
                .overlay {
                    Rectangle()
                        .fill(BookPalette.nightPanel.opacity(0.4))
                }
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer(minLength: 24)

                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        stepContent
                    }
                    .padding(22)
                }
                .frame(maxHeight: 540)
                .background {
                    ZStack {
                        Image("ParchmentTexture")
                            .resizable()
                            .scaledToFill()
                            .opacity(0.9)
                        BookPalette.page.opacity(0.6)
                    }
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
                .overlay {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .stroke(BookPalette.lampGold.opacity(0.4), lineWidth: 1)
                }
                .padding(.horizontal, 22)
                .shadow(color: .black.opacity(0.4), radius: 22, x: 0, y: 12)

                stepDots
                    .padding(.top, 16)

                Spacer(minLength: 30)
            }
        }
        .transition(.opacity)
    }

    private var stepDots: some View {
        HStack(spacing: 8) {
            ForEach(0..<stepCount, id: \.self) { index in
                Circle()
                    .fill(index == step ? BookPalette.lampGold : BookPalette.nightText.opacity(0.3))
                    .frame(width: index == step ? 9 : 6, height: index == step ? 9 : 6)
            }
        }
        .accessibilityHidden(true)
    }

    @ViewBuilder
    private var stepContent: some View {
        switch step {
        case 0:
            onboardingTitle("The Cover Opens")
            onboardingProse("""
            You open the book, and the ink does not stay still.

            Letters lift off the page like startled birds. You taste ink. You hear the low roar of old stories turning over in their sleep. The paper of history rushes past your ears — and then, gently, stone under your feet.

            You are standing in a colossal library-school. The light through the high windows matches the light outside your real window, exactly.

            In the shadow of a shelf, something grey and silent tries to erase the edge of a bookcase. It retreats the moment you look at it.
            """)
            continueButton("Stand up")
        case 1:
            guidePortrait
            onboardingTitle("The Guide")
            onboardingProse("""
            A student helps you up and brushes ink off your shoulder. Quick eyes, a compass on a cord around her neck.

            "Zara Finch. You fell well — most people land in the cookery section." She studies you, then asks the most important question first:

            "What's your favorite snack to eat while reading? I'm sharp green apples. They keep me awake when the footnotes get long."
            """)
            onboardingField("Your answer...", text: $snack)
            continueButton("Tell her", disabled: snack.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        case 2:
            onboardingTitle("The Name on the Flyleaf")
            onboardingProse("""
            Zara nods, satisfied, as if your answer told her more than it should have.

            "The Book will want to know what to call you. Not your full legal anything — just the name that feels like yours when someone says it kindly."
            """)
            onboardingField("What should the Book call you?", text: $name)
            continueButton("Write it in", disabled: name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        case 3:
            onboardingTitle("The Core Question")
            onboardingProse("""
            Zara goes quiet for a moment. When she speaks again, her voice is lower.

            "One more. The real one. I believe every book is a door — that's mine, I'll trade it to you for yours."

            "What do you believe in?"
            """)
            onboardingField("I believe...", text: $belief)
            if !belief.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                onboardingProse("""
                "Saying it out loud matters. But the Labyrinth needs more than words to remember something. It needs weight. Belief."

                "You can plant three points of your own Glow into what you just named. The Book will hold it, weave it into what finds you here — and it won't give it back."
                """)
                HStack(spacing: 10) {
                    Button {
                        BookFeedback.play(.braidStart)
                        investedBelief = true
                        advance()
                    } label: {
                        Label("Plant 3 Belief", systemImage: "leaf")
                            .font(.subheadline.weight(.bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(BookPalette.teal)

                    Button {
                        BookFeedback.play(.select)
                        investedBelief = false
                        advance()
                    } label: {
                        Text("Keep it for now")
                            .font(.subheadline.weight(.bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                    }
                    .buttonStyle(.bordered)
                    .tint(BookPalette.lampGold)
                }
            }
        default:
            onboardingTitle("The Academy Opens")
            onboardingProse(closingProse)
            continueButton("Step into your story")
        }
    }

    private var closingProse: String {
        let planted = investedBelief
            ? "Somewhere deep in the Register, ink moves. Your belief now has a Glow of its own. It will start shaping what finds you.\n\n"
            : "Zara nods. \"Wise. Some things you keep.\"\n\n"
        return """
        \(planted)"Here's how this place works," Zara says, walking you toward a desk where a book lies open to a blank page — your page.

        "Pages rise to meet your real day — keep the ones worth keeping. The three wax seals listen for your body, your sky, and your ground. Give Glow to whatever you want more of; the Book pays attention to attention."

        "And read your Book of You at the end of the day. That's where the magic compounds."

        She taps the cover once. "Real life, re-enchanted. Off you go."
        """
    }

    private var guidePortrait: some View {
        HStack {
            Spacer()
            Image("LabyrinthCharacterZaraFinch")
                .resizable()
                .scaledToFill()
                .frame(width: 96, height: 96)
                .clipShape(Circle())
                .overlay {
                    Circle()
                        .stroke(BookPalette.lampGold.opacity(0.7), lineWidth: 1.6)
                }
                .shadow(color: .black.opacity(0.35), radius: 8, x: 0, y: 5)
                .accessibilityLabel("Zara Finch, your guide")
            Spacer()
        }
    }

    private func onboardingTitle(_ text: String) -> some View {
        WrittenGoldText(
            text,
            font: .system(size: 30, weight: .semibold, design: .serif),
            progress: 1
        )
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func onboardingProse(_ text: String) -> some View {
        Text(text)
            .font(.system(.callout, design: .serif))
            .foregroundStyle(BookPalette.ink.opacity(0.86))
            .lineSpacing(3)
            .fixedSize(horizontal: false, vertical: true)
    }

    private func onboardingField(_ placeholder: String, text: Binding<String>) -> some View {
        TextField(placeholder, text: text, axis: .vertical)
            .font(.system(.body, design: .serif))
            .foregroundStyle(BookPalette.ink)
            .textFieldStyle(.plain)
            .lineLimit(1...3)
            .padding(12)
            .background(BookPalette.paper.opacity(0.8), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(BookPalette.ink.opacity(0.16), lineWidth: 1)
            }
    }

    private func continueButton(_ title: String, disabled: Bool = false) -> some View {
        Button {
            BookFeedback.play(.openPage)
            advance()
        } label: {
            Label(title, systemImage: "arrow.right")
                .font(.headline.weight(.bold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 13)
        }
        .buttonStyle(.borderedProminent)
        .tint(BookPalette.teal)
        .disabled(disabled)
    }

    private func advance() {
        if step >= stepCount - 1 {
            onFinished(Result(
                snack: snack.trimmingCharacters(in: .whitespacesAndNewlines),
                name: name.trimmingCharacters(in: .whitespacesAndNewlines),
                belief: belief.trimmingCharacters(in: .whitespacesAndNewlines),
                investedBelief: investedBelief
            ))
            return
        }
        withAnimation(reduceMotion ? .none : .easeInOut(duration: 0.34)) {
            step += 1
        }
    }
}

/// A small parchment note from Zara that slides in the first time the player
/// touches something new. Tap to dismiss; it also fades on its own.
struct MarginTutorNoteCard: View {
    let note: MarginTutorNote
    let onDismiss: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image("LabyrinthCharacterZaraFinch")
                .resizable()
                .scaledToFill()
                .frame(width: 38, height: 38)
                .clipShape(Circle())
                .overlay {
                    Circle()
                        .stroke(BookPalette.lampGold.opacity(0.7), lineWidth: 1.2)
                }
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text("ZARA'S MARGIN NOTE")
                        .font(.system(size: 9, weight: .black))
                        .kerning(1.1)
                        .foregroundStyle(BookPalette.teal)
                    Spacer()
                    Image(systemName: "xmark")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(BookPalette.ink.opacity(0.4))
                }
                Text(note.title)
                    .font(.system(.subheadline, design: .serif, weight: .bold))
                    .foregroundStyle(BookPalette.ink)
                Text(note.text)
                    .font(.caption)
                    .foregroundStyle(BookPalette.ink.opacity(0.78))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(12)
        .background {
            ZStack {
                Image("ParchmentFiber")
                    .resizable()
                    .scaledToFill()
                    .opacity(0.3)
                BookPalette.page.opacity(0.97)
            }
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .overlay {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(BookPalette.lampGold.opacity(0.45), lineWidth: 1)
        }
        .shadow(color: .black.opacity(0.35), radius: 14, x: 0, y: 8)
        .rotationEffect(.degrees(-0.6))
        .contentShape(Rectangle())
        .onTapGesture {
            BookFeedback.play(.dismissPage)
            onDismiss()
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Margin note from Zara. \(note.title). \(note.text)")
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Tap to dismiss")
    }
}
