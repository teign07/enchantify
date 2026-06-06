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

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase

    @State private var days: [BookDay]
    @State private var selectedSurface: SurfacePage?
    @State private var isBraiding = false
    @State private var isInstallingModel = false
    @State private var didRunSmokeBraid = false
    @State private var statusMessage = ""
    @State private var installMessage = ""
    @State private var installProgress: Double?
    @State private var modelReport = LocalModelManager.report()
    @State private var storeReport: BookStore.Report
    @State private var databaseReport: BookDatabase.Report
    @State private var resurfacedPages: [BookPage]
    @State private var selfFacts: [SelfFact]
    @State private var narrativeEvents: [NarrativeEvent]
    @State private var entityMemories: [NarrativeEntityMemory]
    @State private var facultyEntries: [FacultyEntry]
    @State private var bodySignal: BodySourceSignal?
    @State private var weatherSignal: WeatherSourceSignal?
    @State private var enchantedWeather: EnchantedWeatherSignal?
    @State private var weatherPageSignal: WeatherSourceSignal?
    @State private var isRequestingWeather = false
    @State private var selectedWonderCompassSnippet: ReferenceSnippet?
    @State private var selectedWonderCompassSelector: String?
    @State private var isChoosingWonderCompassPassage = false
    @State private var isRequestingHealthKit = false
    @State private var isSourceSettingsPresented = false
    @State private var didAutoBraidTodayID: String?
    @State private var surfaceRefreshDate = Date()
    @State private var undoSurface: SurfacePage?
    @State private var undoDayID: String?
    @State private var automaticIlluminatedSurface: SurfacePage?
    @State private var isPreparingAutomaticIllumination = false
    @State private var preparedStoryPageSurface: SurfacePage?
    @State private var isPreparingStoryPage = false
    @State private var lastStoryPagePreparationFailure: Date?
    @State private var preparedGossipPageSurface: SurfacePage?
    @State private var isPreparingGossipPage = false
    @State private var preparedFacultyResearchSurface: SurfacePage?
    @State private var isPreparingFacultyResearchPage = false
    @State private var userPhotoIlluminationFallbackAllowed = false
    @AppStorage("didRequestHealthKitBodySignal") private var didRequestHealthKitBodySignal = false
    @AppStorage("didRequestWeatherLocation") private var didRequestWeatherLocation = false
    @AppStorage("dismissedSurfaceLedgerV2") private var dismissedSurfaceLedgerV2 = "{}"
    @AppStorage("sourcePreferenceLedger") private var sourcePreferenceLedger = "{}"
    @AppStorage("illuminatedPhotoHistory") private var illuminatedPhotoHistoryData = "{}"
    @AppStorage("lastAutomaticBodySourceRefreshSlot") private var lastAutomaticBodySourceRefreshSlot = ""
    @AppStorage("lastAutomaticWeatherSourceRefreshSlot") private var lastAutomaticWeatherSourceRefreshSlot = ""
    @AppStorage("beliefScore") private var beliefScore = 30
    @AppStorage("isDoorwaysExpanded") private var isDoorwaysExpanded = false
    @AppStorage("isTodaysMarginsExpanded") private var isTodaysMarginsExpanded = false
    @AppStorage("isReturnedStacksExpanded") private var isReturnedStacksExpanded = false
    @AppStorage("isBookOfYouShelfExpanded") private var isBookOfYouShelfExpanded = false
    @AppStorage("isQuietMechanicsExpanded") private var isQuietMechanicsExpanded = false
    @State private var healthKitMessage = HealthKitBodyReader.isAvailable
        ? "If you open the door, the Book can listen for the body's weather without showing the numbers."
        : "This room has no HealthKit doorway."
    @State private var weatherMessage = WeatherLocationReader.isAvailable
        ? "If you lend the Book your place, it can translate the sky without naming the watcher."
        : "This room cannot hear the local sky yet."
    @State private var braidingQuipIndex = 0
    @State private var braidingStartedAt: Date?
    @State private var lastBraidDuration: TimeInterval?
    @State private var isLocalBrainReading = false
    @State private var isLocalBrainWorking = false
    @State private var localBrainWorkLabel = "the Book"
    @State private var localBrainPromptCharacters = 0
    @State private var localBrainQueuedCount = 0
    @State private var localBrainQuipIndex = 0
    @State private var localBrainStartedAt: Date?
    @State private var isOpeningMovieVisible = true

    private let braider: Braider
    private let wonderCompassChooser: WonderCompassPassageChoosing
    private let weatherEnchanter: WeatherEnchanting
    private let surfaceDismissalTTL: TimeInterval = 90 * 60
    private let surfaceRefreshCadence: Duration = .seconds(20 * 60)
    private let launchGeneratedPageDelay: Duration = .seconds(180)
    private let braidingQuipCadence: Duration = .seconds(3)
    private let localBrainQuipCadence: Duration = .seconds(7)

    private var today: BookDay {
        BookStore.today(from: days)
    }

    private var shouldPrepareGeneratedPagesAutomatically: Bool {
        #if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
        false
        #else
        true
        #endif
    }

    private var sourceInputs: BookSourceInputs {
        var inputs = BookSourceInputs.from(insideCover: InsideCoverStore.load())
        inputs.body = bodySignal
        if let weatherPageSignal {
            inputs.weather = weatherPageSignal
        }
        inputs.enchantedWeather = enchantedWeather
        inputs.selectedWonderCompass = selectedWonderCompassSnippet
        inputs.selectedWonderCompassSelector = selectedWonderCompassSelector
        inputs.preparedIlluminatedPhotoSurface = automaticIlluminatedSurface
        inputs.preparedStoryPageSurface = preparedStoryPageSurface
        inputs.preparedGossipPageSurface = preparedGossipPageSurface
        inputs.preparedFacultyResearchSurface = preparedFacultyResearchSurface
        inputs.userPhotoIlluminationFallbackAllowed = userPhotoIlluminationFallbackAllowed
        inputs.selfFacts = selfFacts
        inputs.facultyEntries = facultyEntries
        inputs.narrative = NarrativeSourceSnapshotBuilder.snapshot(
            from: narrativeEvents,
            memories: entityMemories,
            beliefWeight: beliefScore
        )
        return inputs
    }

    private var wonderCompassSelectionSignature: String {
        let pageBits = today.capturedPages
            .map { "\($0.id):\($0.userInput):\($0.tags.joined(separator: ","))" }
            .joined(separator: "|")
        return [
            today.id,
            SurfaceCadence.slotID(for: surfaceRefreshDate),
            pageBits,
            bodySignal?.status ?? "",
            bodySignal?.phrase ?? "",
            sourceInputs.weather?.phrase ?? ""
        ].joined(separator: "::")
    }

    private var surfaces: [SurfacePage] {
        BookCurator.surfacedPages(
            for: today,
            inputs: sourceInputs,
            now: surfaceRefreshDate,
            limit: 3,
            preferences: CuratorSurfacePreferences(
                dismissedSurfaceIDs: dismissedSurfaceIDs(for: today.id, now: surfaceRefreshDate),
                disabledSourceIDs: disabledSourceIDs()
            )
        )
    }

    private var enabledActiveSourceCount: Int {
        BookPageSourceRegistry.activeSources.filter { isSourceEnabled(sourceID: $0.id) }.count
    }

    init() {
        let legacyDays = BookStore.loadDays()
        let initialDays = BookDatabase.loadDays(migratingFrom: legacyDays)
        _days = State(initialValue: initialDays)
        _storeReport = State(initialValue: BookStore.report(for: initialDays))
        _databaseReport = State(initialValue: BookDatabase.report(for: initialDays))
        _resurfacedPages = State(initialValue: (try? BookDatabase.resurfacingCandidates(limit: 3)) ?? [])
        _selfFacts = State(initialValue: (try? BookDatabase.selfFacts()) ?? [])
        _narrativeEvents = State(initialValue: (try? BookDatabase.narrativeEvents(limit: 100)) ?? [])
        _entityMemories = State(initialValue: (try? BookDatabase.entityMemories(limit: 120)) ?? [])
        _facultyEntries = State(initialValue: (try? BookDatabase.facultyEntries(limit: 160)) ?? [])

        #if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
        braider = AppBraider(local: MLXBookBraider())
        wonderCompassChooser = AppWonderCompassChooser(local: MLXWonderCompassChooser())
        weatherEnchanter = AppWeatherEnchanter(local: MLXWeatherEnchanter())
        #else
        braider = ResilientBraider()
        wonderCompassChooser = ResilientWonderCompassChooser()
        weatherEnchanter = ResilientWeatherEnchanter()
        #endif
    }

    var body: some View {
        NavigationStack {
            ZStack {
                if isLocalBrainReading {
                    LocalBrainReadingRoom()
                } else {
                    BookBackground()

                    ScrollView {
                        VStack(alignment: .leading, spacing: 26) {
                            topBanner
                            hero
                            LabStatusCard(
                                report: modelReport,
                                storeReport: storeReport,
                                databaseReport: databaseReport,
                                lastBraidDuration: lastBraidDuration
                            )
                            localBrainWorkShelf
                            surfaceShelf
                            pageSourceShelf
                            todayFragments
                            resurfacedShelf
                            archiveShelf
                            sourceControlsShelf
                        }
                        .padding(.horizontal, 20)
                        .padding(.vertical, 18)
                        .frame(maxWidth: 920)
                        .frame(maxWidth: .infinity)
                    }
                }

                if isOpeningMovieVisible {
                    OpeningMovieView {
                        withAnimation(.easeInOut(duration: 0.28)) {
                            isOpeningMovieVisible = false
                        }
                    }
                    .transition(.opacity)
                    .zIndex(20)
                }
            }
            .navigationTitle("ReEnchanted")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                surfaceRefreshDate = Date()
                modelReport = LocalModelManager.report()
                storeReport = BookStore.report(for: days)
                databaseReport = BookDatabase.report(for: days)
                refreshResurfacedPages()
                AppMemoryLedger.record("app-launch-idle")
                await refreshDynamicSourcesIfNeeded()
                await runLaunchSmokeTestIfRequested()
                await autoBraidIfNeeded()
            }
            .task {
                try? await Task.sleep(for: launchGeneratedPageDelay)
                guard !Task.isCancelled else { return }
                guard shouldPrepareGeneratedPagesAutomatically else { return }
                await prepareOneGeneratedPageIfPossible()
            }
            .task {
                while !Task.isCancelled {
                    try? await Task.sleep(for: surfaceRefreshCadence)
                    guard !Task.isCancelled else { return }
                    await refreshDynamicSourcesIfNeeded()
                    surfaceRefreshDate = Date()
                    await autoBraidIfNeeded()
                    if shouldPrepareGeneratedPagesAutomatically {
                        await prepareOneGeneratedPageIfPossible()
                    }
                }
            }
            .task(id: wonderCompassSelectionSignature) {
                await refreshWonderCompassSelection()
            }
            .task(id: isBraiding) {
                guard isBraiding else { return }
                while !Task.isCancelled && isBraiding {
                    try? await Task.sleep(for: braidingQuipCadence)
                    guard !Task.isCancelled && isBraiding else { return }
                    withAnimation(.easeInOut(duration: 0.32)) {
                        braidingQuipIndex = (braidingQuipIndex + 1) % BraidingQuips.lines.count
                    }
                }
            }
            .task(id: isLocalBrainWorking) {
                guard isLocalBrainWorking else { return }
                while !Task.isCancelled && isLocalBrainWorking {
                    try? await Task.sleep(for: localBrainQuipCadence)
                    guard !Task.isCancelled && isLocalBrainWorking else { return }
                    withAnimation(.easeInOut(duration: 0.45)) {
                        localBrainQuipIndex = (localBrainQuipIndex + 1) % LocalBrainQuips.lines.count
                    }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .localBrainDidWake)) { _ in
                isLocalBrainReading = true
                AppMemoryLedger.record("reading-room-enter")
            }
            .onReceive(NotificationCenter.default.publisher(for: .localBrainDidRest)) { _ in
                isLocalBrainReading = false
                AppMemoryLedger.record("reading-room-exit")
            }
            .onReceive(NotificationCenter.default.publisher(for: .localBrainWorkDidChange)) { notification in
                guard let snapshot = notification.object as? LocalBrainWorkSnapshot else { return }
                if snapshot.isWorking {
                    if !isLocalBrainWorking {
                        localBrainStartedAt = Date()
                        localBrainQuipIndex = Int.random(in: 0..<LocalBrainQuips.lines.count)
                    }
                    isLocalBrainWorking = true
                    localBrainWorkLabel = snapshot.label ?? "the Book"
                    localBrainPromptCharacters = snapshot.promptCharacters
                    localBrainQueuedCount = snapshot.queuedCount
                } else {
                    isLocalBrainWorking = false
                    localBrainStartedAt = nil
                    localBrainQueuedCount = 0
                    localBrainPromptCharacters = 0
                }
            }
            .onChange(of: scenePhase) { _, newPhase in
                guard newPhase != .active else { return }
                resetTransientWorkStateForBackgrounding()
            }
            .sheet(item: $selectedSurface) { surface in
                CapturePageSheet(
                    surface: surface,
                    isLocalBrainWorking: isLocalBrainWorking,
                    onReplaceIlluminatedSurface: { replacement in
                        automaticIlluminatedSurface = replacement
                        surfaceRefreshDate = Date()
                    }
                ) { savedSurface, input, tags in
                    savePage(surface: savedSurface, input: input, tags: tags)
                }
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $isSourceSettingsPresented) {
                SourceSettingsSheet(
                    sources: BookPageSourceRegistry.sources,
                    preferences: decodedSourcePreferenceLedger()
                ) { sourceID, isEnabled in
                    setSourceEnabled(sourceID: sourceID, isEnabled: isEnabled)
                }
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    BeliefScoreBadge(score: beliefScore)
                }
            }
        }
    }

    private func resetTransientWorkStateForBackgrounding() {
        isLocalBrainReading = false
        isLocalBrainWorking = false
        localBrainStartedAt = nil
        localBrainQueuedCount = 0
        localBrainPromptCharacters = 0
        isBraiding = false
        braidingStartedAt = nil
        isPreparingStoryPage = false
        isPreparingGossipPage = false
        isPreparingFacultyResearchPage = false
        isPreparingAutomaticIllumination = false
    }

    @ViewBuilder
    private var localBrainWorkShelf: some View {
        if isLocalBrainWorking {
            LocalBrainWorkingStatusCard(
                label: localBrainWorkLabel,
                quip: LocalBrainQuips.lines[localBrainQuipIndex],
                startedAt: localBrainStartedAt,
                queuedCount: localBrainQueuedCount
            )
            .transition(.opacity.combined(with: .move(edge: .top)))
        } else if isBraiding {
            BraidingStatusCard(
                quip: BraidingQuips.lines[braidingQuipIndex],
                startedAt: braidingStartedAt
            )
            .transition(.opacity.combined(with: .move(edge: .top)))
        }
    }

    private var topBanner: some View {
        Image("ReEnchantedTopBanner")
            .resizable()
            .scaledToFill()
            .frame(maxWidth: .infinity)
            .frame(height: 142)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(BookPalette.lampGold.opacity(0.28), lineWidth: 1)
            }
            .overlay(alignment: .bottom) {
                LinearGradient(
                    colors: [
                        .clear,
                        BookPalette.nightPanel.opacity(0.42)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .frame(height: 58)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .allowsHitTesting(false)
            }
            .shadow(color: .black.opacity(0.3), radius: 18, x: 0, y: 12)
            .accessibilityLabel("An open enchanted book surrounded by field notes, ink, compass art, and marginalia.")
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: 20) {
            ZStack(alignment: .topTrailing) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Real Life,\nReEnchanted")
                        .font(.system(size: 40, weight: .semibold, design: .serif))
                        .lineLimit(2)
                        .minimumScaleFactor(0.54)
                        .frame(maxWidth: 330, alignment: .leading)
                        .padding(.trailing, 86)

                    Text("Play with Pages. Keep Some. Read Your Story.")
                        .font(.system(.callout, design: .serif, weight: .semibold))
                        .foregroundStyle(BookPalette.nightText.opacity(0.78))
                        .lineSpacing(2)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: 280, alignment: .leading)
                        .padding(.top, 10)
                }
                .foregroundStyle(BookPalette.lampGold)
                .shadow(color: BookPalette.lampGold.opacity(0.18), radius: 10, x: 0, y: 3)
                .frame(maxWidth: .infinity, alignment: .leading)

                LivingMarginaliaImage(name: "MarginaliaCompass", width: 42, opacity: 0.42, glow: false)
                    .frame(width: 58, height: 58)
                    .padding(.top, 8)
                    .padding(.trailing, 8)
                    .accessibilityHidden(true)
            }

            if let bookPage = today.bookOfYou {
                BookOfYouCard(page: bookPage)
            } else {
                HStack(spacing: 10) {
                    Label("\(today.capturedPages.count) fragment\(today.capturedPages.count == 1 ? "" : "s") in the margins", systemImage: "tray.full")
                    Spacer()
                    Text("The Book is listening.")
                }
                .font(.footnote.weight(.semibold))
                .foregroundStyle(BookPalette.ink.opacity(0.68))
                .padding(14)
                .background(BookPalette.paper.opacity(0.82), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(BookPalette.nightPanel.opacity(0.44))
                .shadow(color: .black.opacity(0.28), radius: 18, x: 0, y: 10)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(BookPalette.lampGold.opacity(0.22), lineWidth: 1)
        }
        .overlay(alignment: .bottomLeading) {
            MarginaliaImage(name: "MarginaliaFeather", width: 46, opacity: 0.46)
                .rotationEffect(.degrees(-10))
                .offset(x: -4, y: 16)
                .allowsHitTesting(false)
        }
        .overlay(alignment: .topTrailing) {
            LivingMarginaliaImage(name: "MarginaliaStamp", width: 70, opacity: 0.20, glow: false)
                .rotationEffect(.degrees(8))
                .offset(x: -2, y: 8)
                .allowsHitTesting(false)
        }
    }

    private var surfaceShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Pages Rising")
                    .sectionRuneLabel()

                Spacer()

                Text("\(surfaces.count)/3")
                    .font(.caption.monospacedDigit().weight(.bold))
                    .foregroundStyle(BookPalette.teal)
            }

            if surfaces.isEmpty {
                EmptyBookCard(
                    title: "The desk is clear",
                    message: "No page is tapping the glass just now."
                )
            }

            LazyVStack(spacing: 12) {
                ForEach(surfaces) { surface in
                    SwipeDismissSurfaceCard(surface: surface, isBusy: isBraiding && surface.type == .bookOfYou) {
                        BookFeedback.play(surface.type == .bookOfYou ? .tap : .openPage)
                        if isLocalBrainWorking, surfaceNeedsLocalBrainToOpen(surface) {
                            BookFeedback.play(.error)
                            statusMessage = "The Book is already writing. One moment, please."
                        } else if surface.type == .bookOfYou {
                            Task { await braidToday() }
                        } else {
                            selectedSurface = surface
                        }
                    } onDismiss: {
                        dismissSurface(surface)
                    }
                    .transition(.asymmetric(
                        insertion: .move(edge: .top).combined(with: .opacity),
                        removal: .move(edge: .trailing).combined(with: .opacity)
                    ))
                }
            }
            .animation(.spring(response: 0.55, dampingFraction: 0.82), value: surfaces.map(\.id))

            if !statusMessage.isEmpty {
                StatusBanner(
                    message: statusMessage,
                    actionTitle: undoSurface == nil ? nil : "Call it back",
                    action: undoSurface == nil ? nil : { undoLastSurfaceDismissal() }
                )
            }
        }
    }

    private func surfaceNeedsLocalBrainToOpen(_ surface: SurfacePage) -> Bool {
        switch surface.type {
        case .bookOfYou:
            return true
        case .illuminatedPhoto:
            return (surface.payload.metadata["renderedPreviewPath"] ?? "").isEmpty
        case .narrativeOS:
            return (surface.payload.metadata["storyScene"] ?? "").isEmpty
        case .facultyResearch:
            return (surface.payload.metadata["researchProse"] ?? "").isEmpty
        default:
            return false
        }
    }

    private func foldedShelf<Content: View>(
        title: String,
        status: String? = nil,
        accent: Color = BookPalette.gold,
        isExpanded: Binding<Bool>,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Button {
                BookFeedback.play(.tap)
                withAnimation(.spring(response: 0.42, dampingFraction: 0.86)) {
                    isExpanded.wrappedValue.toggle()
                }
            } label: {
                HStack(spacing: 10) {
                    Text(title)
                        .sectionRuneLabel()

                    Spacer()

                    if let status {
                        Text(status)
                            .font(.caption.monospacedDigit().weight(.bold))
                            .foregroundStyle(accent.opacity(0.95))
                    }

                    Text(isExpanded.wrappedValue ? "open" : "folded")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(BookPalette.gold.opacity(0.78))

                    Image(systemName: "chevron.down")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(accent)
                        .rotationEffect(.degrees(isExpanded.wrappedValue ? 180 : 0))
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isExpanded.wrappedValue ? "Hide \(title)" : "Show \(title)")

            if isExpanded.wrappedValue {
                VStack(alignment: .leading, spacing: 12) {
                    content()
                }
                .transition(
                    .asymmetric(
                        insertion: .move(edge: .top).combined(with: .opacity),
                        removal: .move(edge: .top).combined(with: .opacity)
                    )
                )
            }
        }
        .padding(14)
        .background(BookPalette.nightPanel.opacity(0.36), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(accent.opacity(isExpanded.wrappedValue ? 0.28 : 0.13), lineWidth: 1)
        )
    }

    private var pageSourceShelf: some View {
        foldedShelf(
            title: "Doorways",
            status: "\(enabledActiveSourceCount)/\(BookPageSourceRegistry.activeSources.count)",
            accent: BookPalette.teal,
            isExpanded: $isDoorwaysExpanded
        ) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text("The doors that may open today.")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(BookPalette.nightText.opacity(0.68))

                Spacer()

                Button {
                    BookFeedback.play(.openPage)
                    isSourceSettingsPresented = true
                } label: {
                    Label("Choose doors", systemImage: "slider.horizontal.3")
                        .labelStyle(.iconOnly)
                        .font(.caption.weight(.bold))
                        .frame(width: 30, height: 30)
                        .background(BookPalette.teal.opacity(0.12), in: Circle())
                }
                .buttonStyle(.plain)
                .foregroundStyle(BookPalette.teal)
                .accessibilityLabel("Page source settings")
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(BookPageSourceRegistry.sources) { source in
                        PageSourceCard(source: source, isEnabled: isSourceEnabled(sourceID: source.id))
                    }
                }
                .padding(.bottom, 2)
            }
        }
    }

    private var todayFragments: some View {
        foldedShelf(
            title: "Today's Margins",
            status: "\(today.capturedPages.count)",
            accent: BookPalette.gold,
            isExpanded: $isTodaysMarginsExpanded
        ) {
            if today.capturedPages.isEmpty {
                EmptyBookCard(
                    title: "No fragments yet",
                    message: "A tired day can give one word. The Book will take it."
                )
            } else {
                VStack(spacing: 10) {
                    ForEach(today.capturedPages.sorted { $0.createdAt > $1.createdAt }) { page in
                        FragmentRow(page: page)
                    }
                }
            }
        }
    }

    private var resurfacedShelf: some View {
        foldedShelf(
            title: "Returned From The Stacks",
            status: "\(resurfacedPages.count)",
            accent: BookPalette.gold,
            isExpanded: $isReturnedStacksExpanded
        ) {
            if resurfacedPages.isEmpty {
                EmptyBookCard(
                    title: "No old pages stirring yet",
                    message: "Once a few days are kept, the Book can invite a useful memory back into the room."
                )
            } else {
                VStack(spacing: 10) {
                    ForEach(resurfacedPages) { page in
                        ResurfacedPageRow(page: page)
                    }
                }
            }
        }
    }

    private var archiveShelf: some View {
        let keptPages = days
            .flatMap(\.pages)
            .filter { $0.type == .bookOfYou }
            .sorted { $0.createdAt > $1.createdAt }

        return foldedShelf(
            title: "The Book of You",
            status: "\(keptPages.count)",
            accent: BookPalette.teal,
            isExpanded: $isBookOfYouShelfExpanded
        ) {
            if keptPages.isEmpty {
                EmptyBookCard(
                    title: "The shelf is waiting",
                    message: "When the first braid dries, it will live here."
                )
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(keptPages.prefix(8)) { page in
                            ArchiveCard(page: page)
                        }
                    }
                    .padding(.bottom, 2)
                }
            }
        }
    }

    private var sourceControlsShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button {
                BookFeedback.play(.tap)
                withAnimation(.spring(response: 0.42, dampingFraction: 0.86)) {
                    isQuietMechanicsExpanded.toggle()
                }
            } label: {
                HStack(spacing: 10) {
                    Text("Quiet Mechanics")
                        .sectionRuneLabel()

                    Spacer()

                    Text(isQuietMechanicsExpanded ? "visible" : "folded")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(BookPalette.gold.opacity(0.82))

                    Image(systemName: "chevron.down")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(BookPalette.gold)
                        .rotationEffect(.degrees(isQuietMechanicsExpanded ? 180 : 0))
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isQuietMechanicsExpanded ? "Hide Quiet Mechanics" : "Show Quiet Mechanics")

            if isQuietMechanicsExpanded {
                VStack(alignment: .leading, spacing: 12) {
                    ModelStatusCard(
                        report: modelReport,
                        isInstalling: isInstallingModel,
                        installMessage: installMessage,
                        installProgress: installProgress
                    ) {
                        modelReport = LocalModelManager.report()
                    } onInstall: {
                        Task { await installModel() }
                    }

                    BodySourceCard(
                        bodySignal: bodySignal,
                        message: healthKitMessage,
                        isRequesting: isRequestingHealthKit,
                        hasRequested: didRequestHealthKitBodySignal,
                        isAvailable: HealthKitBodyReader.isAvailable
                    ) {
                        BookFeedback.play(.sourceRefresh)
                        Task { await requestHealthKitBodySignal() }
                    }

                    WeatherSourceCard(
                        weatherSignal: sourceInputs.weather,
                        message: weatherMessage,
                        isRequesting: isRequestingWeather || isLocalBrainWorking,
                        hasRequested: didRequestWeatherLocation,
                        isAvailable: WeatherLocationReader.isAvailable
                    ) {
                        guard !isLocalBrainWorking else {
                            weatherMessage = "The Book is already using the local brain. Let that ink dry first."
                            return
                        }
                        BookFeedback.play(.sourceRefresh)
                        Task { await requestWeatherSignal() }
                    }

                    StoryFieldStatusCard(
                        surface: preparedStoryPageSurface,
                        events: narrativeEvents,
                        isPreparing: isPreparingStoryPage
                    )
                }
                .transition(
                    .asymmetric(
                        insertion: .move(edge: .top).combined(with: .opacity),
                        removal: .move(edge: .top).combined(with: .opacity)
                    )
                )
            }
        }
        .padding(14)
        .background(BookPalette.nightPanel.opacity(0.46), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(BookPalette.gold.opacity(isQuietMechanicsExpanded ? 0.28 : 0.14), lineWidth: 1)
        )
    }

    private func savePage(surface: SurfacePage, input: String, tags: [String]) {
        BookFeedback.play(.keepPage)
        var day = today
        if surface.type == .illuminatedPhoto {
            markAutomaticIlluminatedSurfaceKept(surface)
        }
        if surface.type == .facultyResearch,
           preparedFacultyResearchSurface?.id == surface.id {
            preparedFacultyResearchSurface = nil
        }
        let page = BookPage(
            type: surface.type,
            promptText: surface.prompt,
            userInput: input,
            tags: tags,
            sourceID: surface.sourceID,
            origin: surface.origin,
            privacy: surface.privacy,
            mediaAssets: surface.mediaAssets
        )
        day.pages.append(page)
        recordNarrativeEvent(for: page)
        saveSelfFactIfNeeded(surface: surface, answer: input)
        saveFacultyEntryIfNeeded(surface: surface, page: page, answer: input, tags: tags, dayID: day.id)
        awardBelief(for: surface)
        persist(day: day, message: "The Book tucked the \(surface.type.shortTitle.lowercased()) page into the margin.")
    }

    private func recordNarrativeEvent(for page: BookPage) {
        do {
            let events = NarrativeEventResolver.events(forKept: page)
            for event in events {
                try BookDatabase.upsertNarrativeEvent(event)
                for memory in NarrativeEntityMemoryResolver.memories(for: event) {
                    try BookDatabase.upsertEntityMemory(memory)
                }
            }
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 100)
            entityMemories = try BookDatabase.entityMemories(limit: 120)
        } catch {
            statusMessage = "The page is kept, but one hidden margin note slipped: \(error.localizedDescription)"
        }
    }

    private func saveSelfFactIfNeeded(surface: SurfacePage, answer: String) {
        guard surface.type == .aboutYou else { return }
        let trimmed = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        let metadata = surface.payload.metadata
        let questionID = metadata["questionID"] ?? surface.id
        let question = SelfKnowledgePackRegistry.question(id: questionID) ?? AboutYouQuestion(
            id: questionID,
            packID: metadata["packID"] ?? SelfKnowledgePackRegistry.corePackID,
            prompt: surface.prompt,
            detail: surface.detail,
            placeholder: surface.payload.body,
            sensitivity: SelfFactSensitivity(rawValue: metadata["sensitivity"] ?? "") ?? .delight,
            defaultUsePermission: SelfFactUsePermission(rawValue: metadata["usePermission"] ?? "") ?? .privateContext,
            tags: metadata["tags"]?.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespacesAndNewlines) } ?? [],
            priority: 0
        )
        let now = Date()
        let existing = selfFacts.first { $0.questionID == questionID }
        let fact = SelfFact(
            id: existing?.id ?? "\(question.packID):\(question.id)",
            questionID: question.id,
            question: question.prompt,
            answer: trimmed,
            bookTranslation: SelfKnowledgePackRegistry.translation(for: question, answer: trimmed),
            sensitivity: question.sensitivity,
            usePermission: question.defaultUsePermission,
            tags: question.tags,
            createdAt: existing?.createdAt ?? now,
            updatedAt: now
        )

        do {
            try BookDatabase.upsertSelfFact(fact)
            selfFacts = (try? BookDatabase.selfFacts()) ?? (selfFacts.filter { $0.id != fact.id } + [fact])
        } catch {
            appLog.error("Self fact save failed: \(error.localizedDescription, privacy: .public)")
        }
    }

    private func saveFacultyEntryIfNeeded(
        surface: SurfacePage,
        page: BookPage,
        answer: String,
        tags: [String],
        dayID: String
    ) {
        let metadata = surface.payload.metadata
        let kind: FacultyEntryKind?
        if let metadataKind = metadata["facultyKind"].flatMap(FacultyEntryKind.init(rawValue:)) {
            kind = metadataKind
        } else if surface.type == .fuel || surface.sourceID == "fuel-log" {
            kind = .fuel
        } else if surface.type == .mood || surface.sourceID == "inner-weather" {
            kind = .innerWeather
        } else {
            kind = nil
        }
        guard let kind else { return }

        let trimmed = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        let window = FacultyLogCadence.currentWindow(for: page.createdAt)
        let entry = FacultyEntry(
            id: "faculty-entry-\(page.id)",
            kind: kind,
            facultyID: metadata["facultyID"],
            dayID: dayID,
            sourcePageID: page.id,
            createdAt: page.createdAt,
            windowID: metadata["facultyWindowID"] ?? window.id,
            windowName: metadata["facultyWindowName"] ?? window.name,
            rawText: trimmed,
            tags: Array(Set(tags + [
                "faculty-kind:\(kind.rawValue)",
                "faculty-window:\(metadata["facultyWindowID"] ?? window.id)",
                kind.facultyID
            ])).sorted()
        )

        do {
            try BookDatabase.upsertFacultyEntry(entry)
            facultyEntries = (try? BookDatabase.facultyEntries(limit: 160)) ?? (facultyEntries.filter { $0.id != entry.id } + [entry])
        } catch {
            appLog.error("Faculty entry save failed: \(error.localizedDescription, privacy: .public)")
        }
    }

    private func awardBelief(for surface: SurfacePage) {
        let newScore = min(100, max(0, beliefScore + 1))
        guard newScore != beliefScore else { return }
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = newScore
        }
    }

    @discardableResult
    private func prepareOneGeneratedPageIfPossible() async -> Bool {
        if await prepareStoryPageIfPossible() {
            return true
        }
        if await prepareGossipPageIfPossible() {
            return true
        }
        if await prepareFacultyResearchPageIfPossible() {
            return true
        }
        return await prepareAutomaticIlluminatedPageIfPossible()
    }

    @discardableResult
    private func prepareAutomaticIlluminatedPageIfPossible() async -> Bool {
        #if canImport(Photos) && canImport(UIKit)
        guard automaticIlluminatedSurface == nil,
              !isPreparingAutomaticIllumination,
              !isLocalBrainWorking,
              isSourceEnabled(sourceID: "illuminated-photos") else {
            return false
        }

        let library = PhotoLibraryService()
        let status = library.authorizationStatus()
        let finalStatus: PHAuthorizationStatus
        if status == .notDetermined {
            statusMessage = "The Book needs permission before Penny can find photos in the margins."
            finalStatus = await library.requestAuthorization()
        } else {
            finalStatus = status
        }

        guard finalStatus == .authorized || finalStatus == .limited else {
            if finalStatus == .denied || finalStatus == .restricted {
                statusMessage = "Penny cannot choose from Photos yet. Choose one by hand, or open Photos access in Settings."
                userPhotoIlluminationFallbackAllowed = true
            }
            return false
        }

        isPreparingAutomaticIllumination = true
        defer { isPreparingAutomaticIllumination = false }

        do {
            let history = decodedIlluminatedPhotoHistory()
            let assets = try await library.fetchRecentPhotoAssets(
                lookbackHours: PhotoSuggestionSettings.default.lookbackHours,
                favoritesOnly: PhotoSuggestionSettings.default.favoritesOnly,
                includeScreenshots: PhotoSuggestionSettings.default.includeScreenshots
            )
            let candidates = PhotoCandidateScorer().scoreAssets(assets, history: history)
            let candidate = preferredIlluminatedPhotoCandidate(from: candidates, history: history)
            guard let candidate,
                  let asset = PHAsset.fetchAssets(withLocalIdentifiers: [candidate.assetLocalIdentifier], options: nil).firstObject else {
                statusMessage = "Penny checked recent photos, but the margins were quiet."
                userPhotoIlluminationFallbackAllowed = true
                return false
            }

            let image = try await library.requestFullImage(for: asset, targetSize: CGSize(width: 1400, height: 1400))
            let analysis = await analyzeAutomaticIlluminatedPhoto(image)
            let draft = IlluminatedPageComposer.compose(
                analysis: analysis,
                sourceAssetName: "IlluminatedPhotoSource",
                seed: abs(candidate.assetLocalIdentifier.hashValue ^ today.id.hashValue),
                assetLocalIdentifier: candidate.assetLocalIdentifier
            )
            let renderedURL = IlluminatedPageRenderer.renderPreview(draft: draft, sourceImage: image)
            guard let renderedURL else {
                statusMessage = "Penny found a photo, but the illuminated plate did not finish drying."
                userPhotoIlluminationFallbackAllowed = true
                return false
            }
            guard let surface = SurfacePage.illuminatedPhotoSurface(
                draft: draft,
                renderedURL: renderedURL,
                idSuffix: SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 6)
            ) else {
                return false
            }

            var updatedHistory = history
            updatedHistory.proposedAssetIdentifiers.insert(candidate.assetLocalIdentifier)
            updatedHistory.lastSuggestedAtByAsset[candidate.assetLocalIdentifier] = Date()
            illuminatedPhotoHistoryData = encodedIlluminatedPhotoHistory(updatedHistory)
            automaticIlluminatedSurface = surface
            userPhotoIlluminationFallbackAllowed = false
            surfaceRefreshDate = Date()
            statusMessage = "Penny prepared an illuminated photo page. It is ready if the curator lets it rise."
            return true
        } catch {
            appLog.error("Automatic illuminated page preparation failed: \(error.localizedDescription, privacy: .public)")
            statusMessage = "Penny tried to prepare an illuminated photo page, but the press snagged: \(error.localizedDescription)"
            userPhotoIlluminationFallbackAllowed = true
            return false
        }
        #else
        return false
        #endif
    }

    private func analyzeAutomaticIlluminatedPhoto(_ image: UIImage) async -> PhotoAnalysis {
        #if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
        do {
            return try await GemmaPhotoIlluminationAnalyzer().analyze(photo: image)
        } catch {
            appLog.error("Automatic photo Gemma analysis fell back: \(error.localizedDescription, privacy: .public)")
            return PhotoAnalysis.academyFallback
        }
        #else
        return PhotoAnalysis.academyFallback
        #endif
    }

    @MainActor
    @discardableResult
    private func prepareStoryPageIfPossible() async -> Bool {
        guard !isPreparingStoryPage, !isLocalBrainWorking else { return false }
        if let lastStoryPagePreparationFailure,
           surfaceRefreshDate.timeIntervalSince(lastStoryPagePreparationFailure) < 20 * 60 {
            return false
        }
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 4)
        if let preparedStoryPageSurface,
           preparedStoryPageSurface.payload.metadata["slotID"] == slot,
           preparedStoryPageSurface.payload.metadata["storyScene"]?.isEmpty == false {
            return false
        }

        var draftInputs = sourceInputs
        draftInputs.preparedStoryPageSurface = nil
        let draft = NarrativeOSPageSourceAdapter.draftCandidate(
            for: today,
            inputs: draftInputs,
            now: surfaceRefreshDate
        )

        isPreparingStoryPage = true
        defer { isPreparingStoryPage = false }

        do {
            let prose: StoryPageProse
            #if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXStoryPageWriter().write(surface: draft)
            #else
            prose = try await FakeStoryPageWriter().write(surface: draft)
            #endif
            preparedStoryPageSurface = draft.preparedStoryPageCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            lastStoryPagePreparationFailure = nil
            statusMessage = "The Story Page has dried and is waiting for the curator."
            return true
        } catch {
            appLog.error("Prepared Story Page failed: \(error.localizedDescription, privacy: .public)")
            preparedStoryPageSurface = nil
            lastStoryPagePreparationFailure = Date()
            statusMessage = "The Story Page did not finish drying. The Book will try again later."
            return false
        }
    }

    @MainActor
    @discardableResult
    private func prepareGossipPageIfPossible() async -> Bool {
        guard !isPreparingGossipPage, !isLocalBrainWorking else { return false }
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 4)
        if let preparedGossipPageSurface,
           preparedGossipPageSurface.payload.metadata["slotID"] == slot,
           preparedGossipPageSurface.payload.metadata["gossipProse"]?.isEmpty == false {
            return false
        }

        var draftInputs = sourceInputs
        draftInputs.preparedGossipPageSurface = nil
        let hasStoryMaterial = !today.capturedPages.isEmpty
            || draftInputs.weather != nil
            || draftInputs.body != nil
            || draftInputs.narrative?.recentTags.isEmpty == false
        guard hasStoryMaterial else { return false }

        isPreparingGossipPage = true
        defer { isPreparingGossipPage = false }

        var draft = GossipPageSourceAdapter.draftCandidate(
            for: today,
            inputs: draftInputs,
            now: surfaceRefreshDate
        )
        let realInterestClippings = await RealInterestGossipSearcher().clippings(
            from: selfFacts,
            dayID: today.id,
            slotID: slot
        )
        draft = draft.withRealInterestGossip(realInterestClippings)

        do {
            let prose: String
            #if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXGossipPageWriter().write(surface: draft)
            #else
            prose = try await FakeGossipPageWriter().write(surface: draft)
            #endif
            preparedGossipPageSurface = draft.preparedGossipPageCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            statusMessage = "A Gossip Page has dried. The margins are pretending they did not gossip."
            return true
        } catch {
            appLog.error("Prepared Gossip Page failed: \(error.localizedDescription, privacy: .public)")
            preparedGossipPageSurface = nil
            statusMessage = "The Gossip Page lost its whisper. The Book will try again later."
            return false
        }
    }

    @MainActor
    @discardableResult
    private func prepareFacultyResearchPageIfPossible() async -> Bool {
        guard !isPreparingFacultyResearchPage, !isLocalBrainWorking else { return false }
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 12)
        if let preparedFacultyResearchSurface,
           preparedFacultyResearchSurface.payload.metadata["slotID"] == slot,
           preparedFacultyResearchSurface.payload.metadata["researchProse"]?.isEmpty == false {
            return false
        }

        var draftInputs = sourceInputs
        draftInputs.preparedFacultyResearchSurface = nil
        guard var draft = FacultyResearchNoteGenerator.draftCandidate(for: today, inputs: draftInputs, now: surfaceRefreshDate),
              isSourceEnabled(sourceID: draft.sourceID) else {
            return false
        }

        isPreparingFacultyResearchPage = true
        defer { isPreparingFacultyResearchPage = false }

        do {
            let facultyID = draft.payload.metadata["facultyID"] ?? ""
            let clippings = await ScholarlyFacultyResearcher().clippings(
                for: facultyResearchQueries(for: draft),
                facultyID: facultyID,
                limit: 3
            )
            draft = draft.withFacultyResearchClippings(clippings)
            let prose: String
            #if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXFacultyResearchWriter().write(surface: draft)
            #else
            prose = try await FallbackFacultyResearchWriter().write(surface: draft)
            #endif
            preparedFacultyResearchSurface = draft.preparedFacultyResearchCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            statusMessage = "\(draft.payload.metadata["facultyName"] ?? "The Support Guild") prepared a research folio for tonight."
            return true
        } catch {
            appLog.error("Prepared faculty research failed: \(error.localizedDescription, privacy: .public)")
            preparedFacultyResearchSurface = nil
            statusMessage = "The faculty research folio lost its place. The Book will try again later."
            return false
        }
    }

    private func facultyResearchQueries(for surface: SurfacePage) -> [String] {
        let facultyID = surface.payload.metadata["facultyID"] ?? ""
        if facultyID == "dr-vellum" {
            return [
                "longevity research sleep exercise nutrition 2026",
                "medication adherence health behavior research",
                "heart rate variability recovery longevity study"
            ]
        }
        return [
            "narrative psychology reauthoring self distancing research",
            "consciousness attention rumination self distancing study",
            "expressive writing narrative identity mental health research"
        ]
    }

    private func markAutomaticIlluminatedSurfaceKept(_ surface: SurfacePage) {
        guard let assetID = surface.payload.metadata["assetLocalIdentifier"] else {
            return
        }
        var history = decodedIlluminatedPhotoHistory()
        history.keptAssetIdentifiers.insert(assetID)
        illuminatedPhotoHistoryData = encodedIlluminatedPhotoHistory(history)
        if automaticIlluminatedSurface?.id == surface.id {
            automaticIlluminatedSurface = nil
        }
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

    private func dismissSurface(_ surface: SurfacePage) {
        BookFeedback.play(.dismissPage)
        var ledger = decodedDismissalLedger()
        let now = Date()
        ledger.dismiss(surfaceID: surface.id, dayID: today.id, at: now)
        ledger.prune(now: now, ttl: surfaceDismissalTTL)
        dismissedSurfaceLedgerV2 = encodedDismissalLedger(ledger)
        if surface.type == .illuminatedPhoto,
           let assetID = surface.payload.metadata["assetLocalIdentifier"] {
            var history = decodedIlluminatedPhotoHistory()
            history.dismissedAssetIdentifiers.insert(assetID)
            illuminatedPhotoHistoryData = encodedIlluminatedPhotoHistory(history)
            if automaticIlluminatedSurface?.id == surface.id {
                automaticIlluminatedSurface = nil
            }
        }
        if surface.type == .facultyResearch,
           preparedFacultyResearchSurface?.id == surface.id {
            preparedFacultyResearchSurface = nil
        }
        if selectedSurface?.id == surface.id {
            selectedSurface = nil
        }
        undoSurface = surface
        undoDayID = today.id
        surfaceRefreshDate = now
        statusMessage = "The \(surface.type.shortTitle.lowercased()) page slipped back into the stacks for a while."
    }

    private func undoLastSurfaceDismissal() {
        guard let surface = undoSurface,
              let dayID = undoDayID else {
            return
        }

        BookFeedback.play(.undo)
        var ledger = decodedDismissalLedger()
        ledger.restore(surfaceID: surface.id, dayID: dayID)
        dismissedSurfaceLedgerV2 = encodedDismissalLedger(ledger)
        undoSurface = nil
        undoDayID = nil
        surfaceRefreshDate = Date()
        statusMessage = "The \(surface.type.shortTitle.lowercased()) page found its way back."
    }

    private func dismissedSurfaceIDs(for dayID: String, now: Date) -> Set<String> {
        var ledger = decodedDismissalLedger()
        ledger.prune(now: now, ttl: surfaceDismissalTTL)
        return ledger.activeDismissedSurfaceIDs(for: dayID, now: now, ttl: surfaceDismissalTTL)
    }

    private func decodedDismissalLedger() -> SurfaceDismissalLedger {
        guard let data = dismissedSurfaceLedgerV2.data(using: .utf8),
              let ledger = try? JSONDecoder().decode(SurfaceDismissalLedger.self, from: data) else {
            return SurfaceDismissalLedger()
        }
        return ledger
    }

    private func encodedDismissalLedger(_ ledger: SurfaceDismissalLedger) -> String {
        guard let data = try? JSONEncoder().encode(ledger),
              let encoded = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return encoded
    }

    private func isSourceEnabled(sourceID: String) -> Bool {
        let defaultValue = BookPageSourceRegistry.sources.first { $0.id == sourceID }?.isActive ?? true
        return decodedSourcePreferenceLedger()[sourceID] ?? defaultValue
    }

    private func disabledSourceIDs() -> Set<String> {
        Set(BookPageSourceRegistry.sources.compactMap { source in
            isSourceEnabled(sourceID: source.id) ? nil : source.id
        })
    }

    private func setSourceEnabled(sourceID: String, isEnabled: Bool) {
        var ledger = decodedSourcePreferenceLedger()
        ledger[sourceID] = isEnabled
        sourcePreferenceLedger = encodedSourcePreferenceLedger(ledger)
        statusMessage = isEnabled ? "That doorway is open again." : "That doorway has been softened for now."
    }

    private func decodedSourcePreferenceLedger() -> [String: Bool] {
        guard let data = sourcePreferenceLedger.data(using: .utf8),
              let ledger = try? JSONDecoder().decode([String: Bool].self, from: data) else {
            return [:]
        }
        return ledger
    }

    private func encodedSourcePreferenceLedger(_ ledger: [String: Bool]) -> String {
        guard let data = try? JSONEncoder().encode(ledger),
              let encoded = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return encoded
    }

    private func braidToday() async {
        guard !isBraiding else { return }
        guard !isLocalBrainWorking else {
            BookFeedback.play(.error)
            statusMessage = "The Book is already writing one page. Let that ink dry first."
            return
        }
        guard !today.capturedPages.isEmpty else {
            BookFeedback.play(.error)
            statusMessage = "The Book needs one true fragment before it can braid tonight."
            return
        }
        BookFeedback.play(.braidStart)
        let start = Date()
        isBraiding = true
        braidingStartedAt = start
        braidingQuipIndex = Int.random(in: 0..<BraidingQuips.lines.count)
        statusMessage = "The Book is drawing today's fragments into thread..."
        defer {
            lastBraidDuration = Date().timeIntervalSince(start)
            braidingStartedAt = nil
            isBraiding = false
        }

        do {
            var day = today
            var braid = try await braider.braid(day: day)
            braid.mediaAssets = day.capturedPages.flatMap(\.mediaAssets)
            day.pages = day.pages.map { page in
                var updated = page
                if updated.type != .bookOfYou {
                    updated.usedInBookOfYou = true
                }
                return updated
            }
            day.pages.append(braid)
            if braid.tags.contains("local-model-missing") {
                persist(day: day, message: "The Book kept today's page in its fallback hand. The local brain is still waking.")
            } else if braid.tags.contains("mlx-hook") {
                persist(day: day, message: "The model doorway answered. On the phone, the braid will be local.")
            } else {
                persist(day: day, message: "The ink dried. Today's Book of You page is kept.")
            }
            BookFeedback.play(.braidComplete)
            modelReport = LocalModelManager.report()
        } catch {
            BookFeedback.play(.error)
            statusMessage = "The braid snagged, but nothing was lost. Let the page breathe, then try again. \(error.localizedDescription)"
        }
    }

    @MainActor
    private func autoBraidIfNeeded(now: Date = Date()) async {
        guard BookSchedule.shouldAutoBraid(now),
              didAutoBraidTodayID != today.id,
              today.bookOfYou == nil,
              !today.capturedPages.isEmpty,
              !isBraiding else {
            return
        }

        didAutoBraidTodayID = today.id
        statusMessage = "The hour has grown quiet; the Book is braiding today for you."
        await braidToday()
    }

    private func runLaunchSmokeTestIfRequested() async {
        guard !didRunSmokeBraid,
              ProcessInfo.processInfo.arguments.contains("--smoke-braid") else {
            return
        }

        didRunSmokeBraid = true
        var day = today
        if day.capturedPages.isEmpty {
            day.pages.append(
                BookPage(
                    type: .mood,
                    promptText: "What is the weather inside?",
                    userInput: "Bright: A little electric, but hopeful.",
                    tags: ["bright"]
                )
            )
            persist(day: day, message: "A test fragment was tucked into the margin.")
        }

        await braidToday()
    }

    private func persist(day: BookDay, message: String) {
        let updatedDays = BookStore.upsert(day, in: days)
        do {
            let databaseDays = try BookDatabase.upsert(day, fallbackDays: updatedDays)
            try BookStore.saveDays(databaseDays)
            days = databaseDays
            storeReport = BookStore.report(for: databaseDays)
            databaseReport = BookDatabase.report(for: databaseDays)
            refreshResurfacedPages()
            statusMessage = message
        } catch {
            do {
                try BookStore.saveDays(updatedDays)
                days = updatedDays
                storeReport = BookStore.report(for: updatedDays)
                databaseReport = BookDatabase.report(for: updatedDays)
                refreshResurfacedPages()
                statusMessage = "\(message) The shelves stumbled, so the Book kept a backup copy."
            } catch {
                storeReport = BookStore.report(for: days)
                databaseReport = BookDatabase.report(for: days)
                statusMessage = "The page would not settle yet: \(error.localizedDescription)"
            }
        }
    }

    private func refreshResurfacedPages() {
        resurfacedPages = (try? BookDatabase.resurfacingCandidates(limit: 3)) ?? []
    }

    @MainActor
    private func requestWeatherSignal() async {
        await refreshWeatherSignal(isUserInitiated: true, shouldEnchant: true)
    }

    @MainActor
    private func refreshDynamicSourcesIfNeeded(now: Date = Date()) async {
        let refreshSlot = SurfaceCadence.slotID(for: now, hours: 4)

        if didRequestHealthKitBodySignal,
           isSourceEnabled(sourceID: "body-page"),
           lastAutomaticBodySourceRefreshSlot != refreshSlot {
            if await refreshHealthKitBodySignal(isUserInitiated: false) {
                lastAutomaticBodySourceRefreshSlot = refreshSlot
            }
        }

        if didRequestWeatherLocation,
           isSourceEnabled(sourceID: "weather-page"),
           lastAutomaticWeatherSourceRefreshSlot != refreshSlot {
            if await refreshWeatherSignal(isUserInitiated: false, shouldEnchant: false) {
                lastAutomaticWeatherSourceRefreshSlot = refreshSlot
            }
        }
    }

    @discardableResult
    @MainActor
    private func refreshWeatherSignal(isUserInitiated: Bool, shouldEnchant: Bool) async -> Bool {
        guard !isRequestingWeather else { return false }
        isRequestingWeather = true
        if isUserInitiated {
            weatherMessage = "The Book is leaning toward the window..."
        }
        defer {
            isRequestingWeather = false
        }

        do {
            AppMemoryLedger.record("weather-before-location")
            let signal = try await WeatherLocationReader.requestWeatherSignal()
            AppMemoryLedger.record("weather-after-location")
            didRequestWeatherLocation = true
            weatherSignal = signal
            weatherPageSignal = signal
            if shouldEnchant {
                enchantedWeather = nil
                if isUserInitiated {
                    weatherMessage = "The sky has been read. The Book is finding its weather-words..."
                }
                AppMemoryLedger.record("weather-before-gemma")
                let enchanted = try await weatherEnchanter.enchantWeather(weather: signal, day: today)
                AppMemoryLedger.record("weather-after-gemma")
                enchantedWeather = enchanted
            } else if enchantedWeather?.summary != signal.phrase {
                enchantedWeather = nil
            }
            surfaceRefreshDate = Date()
            weatherMessage = shouldEnchant
                ? "The Weather Page is ready; the forecast remains plain enough to trust."
                : "The sky refreshed its note. The Weather Page has fresh air in it."
            if isUserInitiated {
                lastAutomaticWeatherSourceRefreshSlot = SurfaceCadence.slotID(for: Date(), hours: 4)
            }
            return true
        } catch is CancellationError {
            didRequestWeatherLocation = true
            if isUserInitiated {
                weatherMessage = "The window closed before the Book finished listening. Tap once more."
            }
            return false
        } catch {
            didRequestWeatherLocation = true
            if isUserInitiated {
                weatherPageSignal = nil
                enchantedWeather = nil
                weatherMessage = "The sky would not come through yet: \(error.localizedDescription)"
            }
            return false
        }
    }

    @MainActor
    private func refreshWonderCompassSelection() async {
        guard isSourceEnabled(sourceID: "wonder-compass"),
              !isChoosingWonderCompassPassage else {
            return
        }

        isChoosingWonderCompassPassage = true
        defer { isChoosingWonderCompassPassage = false }

        let inputsWithoutSelection: BookSourceInputs = {
            var inputs = sourceInputs
            inputs.selectedWonderCompass = nil
            return inputs
        }()
        let candidates = BookReferenceCatalog.relevantWonderCompassSnippets(
            for: today,
            inputs: inputsWithoutSelection,
            now: surfaceRefreshDate,
            limit: 8
        )
        guard !candidates.isEmpty else { return }

        selectedWonderCompassSnippet = WonderCompassFallbackChooser.choose(
            day: today,
            inputs: inputsWithoutSelection,
            candidates: candidates
        )
        selectedWonderCompassSelector = "local-relevance"
    }

    @MainActor
    private func requestHealthKitBodySignal() async {
        await refreshHealthKitBodySignal(isUserInitiated: true)
    }

    @discardableResult
    @MainActor
    private func refreshHealthKitBodySignal(isUserInitiated: Bool) async -> Bool {
        guard !isRequestingHealthKit else { return false }
        isRequestingHealthKit = true
        if isUserInitiated {
            healthKitMessage = "The Book is listening for the body's quiet weather..."
        }
        defer {
            isRequestingHealthKit = false
        }

        do {
            let signal = try await HealthKitBodyReader.requestBodySignal()
            didRequestHealthKitBodySignal = true
            bodySignal = signal
            surfaceRefreshDate = Date()
            healthKitMessage = "The Body Page is awake. The Book will name the response, not the source."
            if isUserInitiated {
                lastAutomaticBodySourceRefreshSlot = SurfaceCadence.slotID(for: Date(), hours: 4)
            }
            return true
        } catch is CancellationError {
            didRequestHealthKitBodySignal = true
            if isUserInitiated {
                bodySignal = nil
                healthKitMessage = "The health doorway closed before the Book finished listening. Tap once more."
            }
            return false
        } catch {
            didRequestHealthKitBodySignal = true
            if isUserInitiated {
                bodySignal = nil
                healthKitMessage = "Permission was given, but the body page stayed quiet: \(error.localizedDescription)"
            }
            return false
        }
    }

    private func installModel() async {
        guard !isInstallingModel else { return }
        isInstallingModel = true
        installMessage = "Preparing model download..."
        installProgress = nil
        appLog.info("Gemma install requested")

        let previousIdleTimerState = UIApplication.shared.isIdleTimerDisabled
        UIApplication.shared.isIdleTimerDisabled = true
        let backgroundTaskID = UIApplication.shared.beginBackgroundTask(withName: "Install Gemma") {
            appLog.error("Gemma install background task expired")
        }
        defer {
            UIApplication.shared.isIdleTimerDisabled = previousIdleTimerState
            if backgroundTaskID != .invalid {
                UIApplication.shared.endBackgroundTask(backgroundTaskID)
            }
            isInstallingModel = false
            modelReport = LocalModelManager.report()
        }

        #if canImport(MLXLMHFAPI)
        do {
            let model = LocalModelManager.preferredModel
            let modelID = model.modelID
            appLog.info("Starting Hugging Face download for \(modelID, privacy: .public)")
            let directory = try await Task.detached(priority: .userInitiated) {
                try await HubClient.default.download(
                    id: modelID,
                    revision: "main",
                    matching: ["*.safetensors", "*.json", "*.jinja", "*.model", "*.txt"],
                    useLatest: false
                ) { progress in
                    Task { @MainActor in
                        if progress.totalUnitCount > 0 {
                            let fraction = min(max(Double(progress.completedUnitCount) / Double(progress.totalUnitCount), 0), 1)
                            let percent = Int(fraction * 100)
                            installProgress = fraction
                            installMessage = "Downloading \(model.label)... \(percent)%"
                        } else {
                            installProgress = nil
                            installMessage = "Downloading \(model.label)... measuring the bundle"
                        }
                    }
                }
            }.value
            try LocalModelManager.activateModel(
                modelID: modelID,
                directory: directory
            )
            LocalModelManager.removeSupersededModels(for: modelID, preserving: directory)
            appLog.info("Gemma install completed at \(directory.path, privacy: .private)")
            installProgress = 1
            installMessage = "\(model.label) is installed. The old local model was cleared if it was still on the shelf."
        } catch {
            appLog.error("Gemma install failed: \(error.localizedDescription, privacy: .public)")
            installProgress = nil
            installMessage = "Model install failed: \(error.localizedDescription)"
        }
        #else
        installProgress = nil
        installMessage = "The Hugging Face downloader is not linked in this build."
        #endif
    }
}

private struct LocalBrainReadingRoom: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var glow = false

    var body: some View {
        ZStack {
            Color(red: 0.025, green: 0.027, blue: 0.060)
                .ignoresSafeArea()

            VStack(spacing: 18) {
                Image(systemName: "book.closed.fill")
                    .font(.system(size: 34))
                    .foregroundStyle(BookPalette.lampGold)
                    .shadow(color: BookPalette.lampGold.opacity(glow ? 0.46 : 0.16), radius: glow ? 18 : 6)

                Text("The Book is reading.")
                    .font(.system(.title2, design: .serif, weight: .semibold))
                    .foregroundStyle(BookPalette.nightText)

                Text("The shelves have gone quiet to make room for the ink.")
                    .font(.system(.callout, design: .serif))
                    .foregroundStyle(BookPalette.nightText.opacity(0.72))
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 280)
            }
        }
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.easeInOut(duration: 2.4).repeatForever(autoreverses: true)) {
                glow = true
            }
        }
    }
}

private struct FallbackFacultyResearchWriter {
    func write(surface: SurfacePage) async throws -> String {
        try await Task.sleep(nanoseconds: 250_000_000)
        let faculty = surface.payload.metadata["facultyName"] ?? "Support Faculty"
        let topic = surface.payload.metadata["researchTopic"] ?? "care research"
        return """
        Field finding: \(faculty) reviewed the chart through the Margin-Glass and found one useful question inside the noise.

        What it might mean: \(topic) matters most here when it becomes small enough to try today, not when it becomes an identity.

        Tiny experiment: Track one before/after signal around the next ordinary care action.

        Uncertainty: This is research for attention, not a diagnosis or treatment plan.
        """
    }
}
