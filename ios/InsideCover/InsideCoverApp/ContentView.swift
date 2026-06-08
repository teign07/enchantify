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

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase

    @State private var days: [BookDay] = [BookDay.today()]
    @State private var selectedSurface: SurfacePage?
    @State private var isBraiding = false
    @State private var isInstallingModel = false
    @State private var didRunSmokeBraid = false
    @State private var statusMessage = ""
    @State private var installMessage = ""
    @State private var installProgress: Double?
    @State private var modelReport = Self.placeholderModelReport
    @State private var storeReport = Self.placeholderStoreReport
    @State private var databaseReport = Self.placeholderDatabaseReport
    @State private var resurfacedPages: [BookPage] = []
    @State private var surfacedPages: [SurfacePage] = []
    @State private var selfFacts: [SelfFact] = []
    @State private var narrativeEvents: [NarrativeEvent] = []
    @State private var entityMemories: [NarrativeEntityMemory] = []
    @State private var facultyEntries: [FacultyEntry] = []
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
    @State private var undoRemovedPage: BookPage?
    @State private var undoRemovedPageDayID: String?
    @State private var braidRecovery = BraidRecoveryState()
    @State private var automaticIlluminatedSurface: SurfacePage?
    @State private var isPreparingAutomaticIllumination = false
    @State private var preparedStoryPageSurface: SurfacePage?
    @State private var isPreparingStoryPage = false
    @State private var storyPageRecovery = PreparedPageRecoveryState()
    @State private var preparedGossipPageSurface: SurfacePage?
    @State private var isPreparingGossipPage = false
    @State private var gossipPageRecovery = PreparedPageRecoveryState()
    @State private var preparedFacultyResearchSurface: SurfacePage?
    @State private var isPreparingFacultyResearchPage = false
    @State private var facultyResearchRecovery = PreparedPageRecoveryState()
    @State private var userPhotoIlluminationFallbackAllowed = false
    @AppStorage("didRequestHealthKitBodySignal") private var didRequestHealthKitBodySignal = false
    @AppStorage("didRequestWeatherLocation") private var didRequestWeatherLocation = false
    @AppStorage("dismissedSurfaceLedgerV2") private var dismissedSurfaceLedgerV2 = "{}"
    @AppStorage("sourcePreferenceLedger") private var sourcePreferenceLedger = "{}"
    @AppStorage("illuminatedPhotoHistory") private var illuminatedPhotoHistoryData = "{}"
    @AppStorage("lastAutomaticBodySourceRefreshSlot") private var lastAutomaticBodySourceRefreshSlot = ""
    @AppStorage("lastAutomaticWeatherSourceRefreshSlot") private var lastAutomaticWeatherSourceRefreshSlot = ""
    @AppStorage("beliefScore") private var beliefScore = 30
    @AppStorage("completedCompassRunLedger") private var completedCompassRunLedger = ""
    @AppStorage("entityBeliefLedger") private var entityBeliefLedgerData = "{}"
    @AppStorage("pageBeliefLedger") private var pageBeliefLedgerData = "{}"
    @AppStorage("isDoorwaysExpanded") private var isDoorwaysExpanded = false
    @AppStorage("isTodaysMarginsExpanded") private var isTodaysMarginsExpanded = false
    @AppStorage("isReturnedStacksExpanded") private var isReturnedStacksExpanded = false
    @AppStorage("isBookOfYouShelfExpanded") private var isBookOfYouShelfExpanded = false
    @AppStorage("isQuietMechanicsExpanded") private var isQuietMechanicsExpanded = false
    @AppStorage("isLabPanelExpanded") private var isLabPanelExpanded = false
    @State private var healthKitMessage = HealthKitBodyReader.isAvailable
        ? "If you open the door, the Book can listen for the body's weather without showing the numbers."
        : "This room has no HealthKit doorway."
    @State private var weatherMessage = WeatherLocationReader.isAvailable
        ? "If you lend the Book your place, it can translate the sky without naming the watcher."
        : "This room cannot hear the local sky yet."
    @State private var braidingQuipIndex = 0
    @State private var braidingStartedAt: Date?
    @State private var lastBraidDuration: TimeInterval?
    @State private var localBrainTelemetry = LocalBrainTelemetryState()
    @State private var localBrainQuipIndex = 0
    @State private var isOpeningMovieVisible = true
    @State private var isGlowMenuPresented = false
    @State private var didHydrateLaunchState = false
    @State private var didRunPostLaunchTasks = false

    private let braider: Braider
    private let wonderCompassChooser: WonderCompassPassageChoosing
    private let weatherEnchanter: WeatherEnchanting
    private let surfaceDismissalTTL: TimeInterval = 90 * 60
    private let surfaceRefreshCadence: Duration = .seconds(20 * 60)
    private let braidingQuipCadence: Duration = .seconds(3)
    private let localBrainQuipCadence: Duration = .seconds(7)

    private static var placeholderModelReport: LocalModelReport {
        LocalModelReport(
            state: .unavailable,
            preferredModelID: LocalModelManager.preferredModelID,
            fallbackModelID: LocalModelManager.fallbackModelID,
            preferredModelSource: LocalModelManager.preferredModel.sourceURL,
            fallbackModelSource: LocalModelManager.compactModel.sourceURL,
            installPath: LocalModelManager.modelsDirectory.path,
            detail: "ReEnchanted is opening the cover before checking the local brain.",
            deviceSummary: LocalModelManager.deviceSummary
        )
    }

    private static var placeholderStoreReport: BookStore.Report {
        let today = BookDay.today()
        return BookStore.Report(
            schemaVersion: BookStore.schemaVersion,
            storagePath: BookStore.fileURL.path,
            dayCount: 1,
            pageCount: 0,
            todayID: today.id,
            todayPageCount: 0,
            todayBookOfYouCount: 0,
            loadSource: .fallbackToday,
            lastError: nil
        )
    }

    private static var placeholderDatabaseReport: BookDatabase.Report {
        BookDatabase.Report(
            schemaVersion: BookDatabase.schemaVersion,
            storagePath: BookDatabase.storeURL.path,
            dayCount: 1,
            pageCount: 0,
            loadSource: .fallbackJSON,
            lastError: nil,
            backupCount: 0,
            lastBackupPath: nil
        )
    }

    private var today: BookDay {
        BookStore.today(from: days)
    }

    private var workBlockingState: WorkBlockingState {
        WorkBlockingState(
            isLocalBrainWorking: localBrainTelemetry.isWorking,
            localBrainStatus: localBrainTelemetry.currentWorkStatus,
            isBraiding: isBraiding,
            isPreparingAutomaticIllumination: isPreparingAutomaticIllumination,
            isPreparingStoryPage: isPreparingStoryPage,
            isPreparingGossipPage: isPreparingGossipPage,
            isPreparingFacultyResearchPage: isPreparingFacultyResearchPage,
            isRequestingWeather: isRequestingWeather
        )
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

    private var selectedCuratorSurfaces: [SurfacePage] {
        buildCuratorSurfaces(now: surfaceRefreshDate)
    }

    private var surfaces: [SurfacePage] {
        surfacedPages
    }

    private func buildCuratorSurfaces(now: Date) -> [SurfacePage] {
        BookCurator.surfacedPages(
            for: today,
            inputs: sourceInputs,
            now: now,
            limit: 3,
            preferences: CuratorSurfacePreferences(
                dismissedSurfaceIDs: dismissedSurfaceIDs(for: today.id, now: now),
                disabledSourceIDs: disabledSourceIDs(),
                pageBeliefProfiles: Dictionary(
                    uniqueKeysWithValues: pageBeliefProfiles.map { ($0.sourceID, $0) }
                )
            )
        )
    }

    private var enabledActiveSourceCount: Int {
        BookPageSourceRegistry.activeSources.filter { isSourceEnabled(sourceID: $0.id) }.count
    }

    private var entityBeliefLedger: [String: Int] {
        (try? JSONDecoder().decode([String: Int].self, from: Data(entityBeliefLedgerData.utf8))) ?? [:]
    }

    private var pageBeliefLedger: [String: Int] {
        (try? JSONDecoder().decode([String: Int].self, from: Data(pageBeliefLedgerData.utf8))) ?? [:]
    }

    private var pageBeliefProfiles: [PageBeliefProfile] {
        BookPageSourceRegistry.beliefProfiles(ledger: pageBeliefLedger)
    }

    private var glowEntityMenuItems: [GlowEntityMenuItem] {
        let ledger = entityBeliefLedger
        return NarrativePackRegistry.entities
            .map { entity in
                let glow = max(0, min(100, entity.belief + (ledger[entity.id] ?? 0)))
                return GlowEntityMenuItem(
                    id: entity.id,
                    name: entity.name,
                    kind: entity.kind.rawValue,
                    glow: glow,
                    line: glowLine(for: entity)
                )
            }
            .sorted { left, right in
                if left.glow == right.glow {
                    return left.name < right.name
                }
                return left.glow > right.glow
            }
    }

    private var glowPageMenuItems: [GlowPageMenuItem] {
        pageBeliefProfiles.map { profile in
            let source = BookPageSourceRegistry.source(id: profile.sourceID, fallbackType: profile.type)
            return GlowPageMenuItem(
                id: profile.sourceID,
                type: profile.type,
                sourceID: profile.sourceID,
                title: profile.title,
                detail: "\(profile.cadence). \(profile.note)",
                symbolName: source.symbolName,
                glow: profile.belief,
                narrativeWeight: profile.narrativeWeight
            )
        }
        .sorted { left, right in
            if left.curationWeight == right.curationWeight {
                return left.title < right.title
            }
            return left.curationWeight > right.curationWeight
        }
    }

    private var glowBookSectionMenuItems: [GlowBookSectionMenuItem] {
        BookReferenceCatalog.wonderCompass.map { snippet in
            GlowBookSectionMenuItem(
                id: snippet.id,
                title: snippet.title,
                detail: snippet.prompt
            )
        }
    }

    private var glowEnchantmentMenuItems: [GlowEnchantmentMenuItem] {
        StoryEnchantmentCatalog.spells.map {
            GlowEnchantmentMenuItem(id: $0.id, title: $0.title, detail: $0.detail)
        }
    }

    init() {
        #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
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
                if localBrainTelemetry.isReading {
                    LocalBrainReadingRoom()
                } else {
                    BookBackground()

                    if didHydrateLaunchState {
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
                                labPanelShelf
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
                }

                if isOpeningMovieVisible {
                    OpeningMovieView {
                        Task {
                            await waitForLaunchStateHydration()
                            withAnimation(.easeInOut(duration: 0.28)) {
                                isOpeningMovieVisible = false
                            }
                        }
                    }
                    .task {
                        await hydrateLaunchStateIfNeeded()
                    }
                    .transition(.opacity)
                    .zIndex(20)
                }

                if isGlowMenuPresented {
                    GlowCommandMenu(
                        score: beliefScore,
                        surfaceCount: surfaces.count,
                        capturedPageCount: today.capturedPages.count,
                        entities: glowEntityMenuItems,
                        pageTypes: glowPageMenuItems,
                        bookSections: glowBookSectionMenuItems,
                        enchantments: glowEnchantmentMenuItems,
                        onClose: closeGlowMenu,
                        onSelectAction: handleGlowMenuAction
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .ignoresSafeArea()
                    .transition(.asymmetric(
                        insertion: .scale(scale: 0.82, anchor: .topTrailing)
                            .combined(with: .move(edge: .trailing))
                            .combined(with: .opacity),
                        removal: .scale(scale: 0.96, anchor: .topTrailing)
                            .combined(with: .opacity)
                    ))
                    .zIndex(15)
                }
            }
            .navigationTitle("ReEnchanted")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(isGlowMenuPresented ? .hidden : .visible, for: .navigationBar)
            .task {
                await runPostLaunchTasksIfNeeded()
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
            .task(id: localBrainTelemetry.isWorking) {
                guard localBrainTelemetry.isWorking else { return }
                while !Task.isCancelled && localBrainTelemetry.isWorking {
                    try? await Task.sleep(for: localBrainQuipCadence)
                    guard !Task.isCancelled && localBrainTelemetry.isWorking else { return }
                    withAnimation(.easeInOut(duration: 0.45)) {
                        localBrainQuipIndex = (localBrainQuipIndex + 1) % LocalBrainQuips.lines.count
                    }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .localBrainDidWake)) { _ in
                localBrainTelemetry.wake()
                AppMemoryLedger.record("reading-room-enter")
            }
            .onReceive(NotificationCenter.default.publisher(for: .localBrainDidRest)) { _ in
                localBrainTelemetry.rest()
                AppMemoryLedger.record("reading-room-exit")
            }
            .onReceive(NotificationCenter.default.publisher(for: .localBrainWorkDidChange)) { notification in
                guard let snapshot = notification.object as? LocalBrainWorkSnapshot else { return }
                if snapshot.isWorking {
                    if localBrainTelemetry.beginOrUpdateWork(
                        label: snapshot.label,
                        promptCharacters: snapshot.promptCharacters,
                        queuedCount: snapshot.queuedCount
                    ) {
                        localBrainQuipIndex = Int.random(in: 0..<LocalBrainQuips.lines.count)
                    }
                } else {
                    localBrainTelemetry.finishWork()
                }
            }
            .onChange(of: scenePhase) { _, newPhase in
                guard newPhase != .active else { return }
                resetTransientWorkStateForBackgrounding()
            }
            .onChange(of: didHydrateLaunchState) { _, _ in
                rebuildSurfaceCache()
            }
            .onChange(of: surfaceRefreshDate) { _, _ in
                rebuildSurfaceCache()
            }
            .sheet(item: $selectedSurface) { surface in
                CapturePageSheet(
                    surface: surface,
                    day: today,
                    isLocalBrainWorking: localBrainTelemetry.isWorking,
                    onReplaceIlluminatedSurface: { replacement in
                        automaticIlluminatedSurface = replacement
                        surfaceRefreshDate = Date()
                    },
                    onNavigateToSurface: { nextSurface in
                        selectedSurface = nextSurface
                    },
                    onCompleteCompassRun: { completedSurface in
                        completeCompassRunIfNeeded(completedSurface)
                    },
                    onStoryMechanicCompleted: { completedSurface, outcome in
                        openStoryMechanicReturnPage(from: completedSurface, outcome: outcome)
                    }
                ) { savedSurface, input, tags in
                    savePage(surface: savedSurface, input: input, tags: tags)
                }
                .id(surface.id)
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
                    Button {
                        toggleGlowMenu()
                    } label: {
                        BeliefScoreBadge(score: beliefScore)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(isGlowMenuPresented ? "Close Glow menu" : "Open Glow menu")
                }
            }
        }
    }

    @MainActor
    private func hydrateLaunchStateIfNeeded() async {
        guard !didHydrateLaunchState else { return }

        await Task.yield()
        try? await Task.sleep(for: .milliseconds(700))

        let initialDays = BookDatabase.loadDays(migratingFrom: BookStore.loadDays())
        await Task.yield()

        surfaceRefreshDate = Date()
        days = initialDays
        storeReport = BookStore.report(for: initialDays)
        await Task.yield()
        databaseReport = BookDatabase.report(for: initialDays)
        await Task.yield()
        resurfacedPages = (try? BookDatabase.resurfacingCandidates(limit: 3)) ?? []
        await Task.yield()
        selfFacts = (try? BookDatabase.selfFacts()) ?? []
        await Task.yield()
        narrativeEvents = (try? BookDatabase.narrativeEvents(limit: 100)) ?? []
        await Task.yield()
        entityMemories = (try? BookDatabase.entityMemories(limit: 120)) ?? []
        await Task.yield()
        facultyEntries = (try? BookDatabase.facultyEntries(limit: 160)) ?? []
        await Task.yield()
        modelReport = LocalModelManager.report()
        didHydrateLaunchState = true
    }

    @MainActor
    private func waitForLaunchStateHydration() async {
        while !didHydrateLaunchState && !Task.isCancelled {
            try? await Task.sleep(for: .milliseconds(100))
        }
    }

    @MainActor
    private func runPostLaunchTasksIfNeeded() async {
        guard !didRunPostLaunchTasks else { return }
        await waitForLaunchStateHydration()
        guard !Task.isCancelled, !didRunPostLaunchTasks else { return }

        didRunPostLaunchTasks = true
        AppMemoryLedger.record("app-launch-idle")
        await runLaunchSmokeTestIfRequested()
    }

    @MainActor
    private func rebuildSurfaceCache() {
        guard didHydrateLaunchState else {
            surfacedPages = []
            return
        }
        surfacedPages = buildCuratorSurfaces(now: surfaceRefreshDate)
    }

    private func toggleGlowMenu() {
        BookFeedback.play(isGlowMenuPresented ? .dismissPage : .sourceRefresh)
        withAnimation(.spring(response: 0.48, dampingFraction: 0.78)) {
            isGlowMenuPresented.toggle()
        }
    }

    private func closeGlowMenu() {
        BookFeedback.play(.dismissPage)
        withAnimation(.spring(response: 0.38, dampingFraction: 0.86)) {
            isGlowMenuPresented = false
        }
    }

    private func handleGlowMenuAction(_ action: GlowMenuAction) {
        switch action {
        case let .giveBelief(entity):
            adjustEntityBelief(entity, delta: 3, kind: .beliefInvested)
            statusMessage = "\(entity.name) takes on three brighter points of Glow."
        case let .takeBelief(entity):
            takeBelief(from: entity)
        case let .givePageBelief(page):
            adjustPageBelief(page, delta: 3)
            statusMessage = "\(page.title) takes on three brighter points of Glow."
        case let .takePageBelief(page):
            adjustPageBelief(page, delta: -3)
            statusMessage = "\(page.title) dims by three points. The Book will still remember it can surface."
        case .spellCompass:
            selectedSurface = compassRunSurface()
            closeGlowMenu()
        case let .openEnchantment(enchantment):
            selectedSurface = enchantmentSurface(enchantment)
            closeGlowMenu()
        case let .openPage(type):
            Task { await openManualPage(type) }
            closeGlowMenu()
        case let .openBookSection(sectionID):
            selectedSurface = readingSurface(forWonderCompassSectionID: sectionID)
            closeGlowMenu()
        }
    }

    private func glowLine(for entity: NarrativeWorldEntity) -> String {
        if let descriptor = compactCastDescriptor(for: entity.id) {
            return descriptor
        }

        let source: String
        if !entity.traits.isEmpty {
            source = entity.traits.prefix(2).joined(separator: ", ")
        } else if let interest = entity.unwrittenInterest?.trimmingCharacters(in: .whitespacesAndNewlines), !interest.isEmpty {
            source = interest
        } else if let goal = entity.goals.first {
            source = goal
        } else if let belief = entity.beliefs.first {
            source = belief
        } else {
            source = entity.kind.rawValue
        }
        return compactGlowLine(source)
    }

    private func compactCastDescriptor(for id: String) -> String? {
        switch id {
        case "the-book":
            return "Attentive living book"
        case "penny-blackletter":
            return "Sharp student editor"
        case "dr-inkrest":
            return "Gentle narrative therapist"
        case "dr-vellum":
            return "Precise longevity physician"
        case "headmistress-thorne":
            return "Watchful headmistress"
        case "orion-blackthorn":
            return "Stern impossible architect"
        case "zara-finch":
            return "Loyal house guide"
        case "wicker-eddies":
            return "Sharp belief challenger"
        case "gwendolyn-mythwright":
            return "Steadfast cryptid scholar"
        case "lydia-boggle":
            return "Wry glint professor"
        case "soren-ng":
            return "Quiet riddle cartographer"
        case "weather-page":
            return "Atmospheric weather page"
        case "body-page":
            return "Humane body pacing"
        default:
            return nil
        }
    }

    private func compactGlowLine(_ source: String) -> String {
        let separators = CharacterSet(charactersIn: ",;.-")
        let fragments = source
            .components(separatedBy: separators)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let phrase = fragments.first ?? source.trimmingCharacters(in: .whitespacesAndNewlines)
        let words = phrase.split(separator: " ")
        if words.count <= 4 {
            return phrase
        }
        return words.prefix(4).joined(separator: " ")
    }

    private func takeBelief(from entity: GlowEntityMenuItem) {
        let attack = BeliefCombatResolver.resolve(
            attackerName: "The reader",
            attackerKind: .player,
            attackerBelief: beliefScore,
            targetName: entity.name,
            targetKind: .entity,
            targetBelief: entity.glow,
            spend: 3,
            difficulty: BeliefCombatResolver.difficulty(forTargetBelief: entity.glow)
        )
        let playerDelta = attack.attackerBeliefAfter - attack.attackerBeliefBefore
        let entityDelta = attack.targetBeliefAfter - attack.targetBeliefBefore
        if entityDelta != 0 {
            adjustEntityBelief(entity, delta: entityDelta, kind: .beliefAttacked, playerBeliefDelta: playerDelta)
        } else {
            recordGlowBeliefEvent(entity: entity, delta: 0, kind: .beliefAttacked, playerBeliefDelta: playerDelta)
        }
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = min(100, max(0, attack.attackerBeliefAfter))
        }
        if attack.backlash > 0 {
            statusMessage = "\(entity.name)'s Glow snaps back. \(attack.summaryLine)"
        } else if attack.dealt > 0 {
            statusMessage = "The attack lands. \(attack.summaryLine)"
        } else {
            statusMessage = "\(entity.name)'s Glow holds. \(attack.summaryLine)"
        }
    }

    private func adjustEntityBelief(
        _ entity: GlowEntityMenuItem,
        delta: Int,
        kind: NarrativeEventKind,
        playerBeliefDelta: Int = 0
    ) {
        var ledger = entityBeliefLedger
        ledger[entity.id, default: 0] += delta
        if let data = try? JSONEncoder().encode(ledger),
           let encoded = String(data: data, encoding: .utf8) {
            entityBeliefLedgerData = encoded
        }
        recordGlowBeliefEvent(entity: entity, delta: delta, kind: kind, playerBeliefDelta: playerBeliefDelta)
    }

    private func recordGlowBeliefEvent(
        entity: GlowEntityMenuItem,
        delta: Int,
        kind: NarrativeEventKind,
        playerBeliefDelta: Int = 0
    ) {
        let event = NarrativeEvent(
            id: "glow-\(kind.rawValue)-\(entity.id)-\(UUID().uuidString)",
            kind: kind,
            sourcePageType: nil,
            sourcePageID: nil,
            createdAt: Date(),
            summary: delta > 0
                ? "The reader gave \(entity.name) \(delta) Belief through the Glow menu."
                : (delta < 0 ? "The reader took \(abs(delta)) Belief from \(entity.name) through the Glow menu." : "The reader tested \(entity.name)'s Belief through the Glow menu."),
            tags: ["glow", "belief", "entity:\(entity.id)"],
            effect: NarrativeEventEffect(
                beliefDelta: playerBeliefDelta,
                entityWeightDeltas: [entity.id: delta]
            )
        )
        do {
            try BookDatabase.upsertNarrativeEvent(event)
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 100)
        } catch {
            statusMessage = "The Glow moved, but the hidden ledger missed a line: \(error.localizedDescription)"
        }
    }

    private func adjustPageBelief(_ page: GlowPageMenuItem, delta: Int) {
        var ledger = pageBeliefLedger
        let source = BookPageSourceRegistry.source(id: page.sourceID, fallbackType: page.type)
        let defaultBelief = BookPageSourceRegistry.defaultBelief(for: source)
        let currentDelta = ledger[page.sourceID] ?? 0
        let nextBelief = max(0, min(100, defaultBelief + currentDelta + delta))
        ledger[page.sourceID] = nextBelief - defaultBelief
        if ledger[page.sourceID] == 0 {
            ledger[page.sourceID] = nil
        }
        if let data = try? JSONEncoder().encode(ledger),
           let encoded = String(data: data, encoding: .utf8) {
            pageBeliefLedgerData = encoded
        }
        recordGlowPageBeliefEvent(page: page, delta: nextBelief - page.glow)
        surfaceRefreshDate = Date()
        rebuildSurfaceCache()
    }

    private func recordGlowPageBeliefEvent(page: GlowPageMenuItem, delta: Int) {
        let event = NarrativeEvent(
            id: "glow-page-belief-\(page.sourceID)-\(UUID().uuidString)",
            kind: delta >= 0 ? .beliefInvested : .beliefAttacked,
            sourcePageType: page.type,
            sourcePageID: nil,
            createdAt: Date(),
            summary: delta >= 0
                ? "The reader gave \(page.title) \(delta) Page Belief through the Glow menu."
                : "The reader took \(abs(delta)) Page Belief from \(page.title) through the Glow menu.",
            tags: ["glow", "belief", "page:\(page.sourceID)", "page-type:\(page.type.rawValue)"],
            effect: NarrativeEventEffect()
        )
        do {
            try BookDatabase.upsertNarrativeEvent(event)
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 100)
        } catch {
            statusMessage = "The Page Glow moved, but the hidden ledger missed a line: \(error.localizedDescription)"
        }
    }

    private func compassRunSurface() -> SurfacePage {
        BookPageSourceAdapters.manualSurface(
            for: .wonderCompass,
            day: today,
            context: CuratorContext.make(for: today),
            inputs: sourceInputs,
            now: Date()
        )
    }

    private func enchantmentSurface(_ enchantment: GlowEnchantmentMenuItem) -> SurfacePage {
        SurfacePage(
            id: "manual-enchantment-\(enchantment.id)-\(today.id)-\(Int(Date().timeIntervalSince1970))",
            type: .lore,
            sourceID: BookPageSourceRegistry.source(for: .lore).id,
            intent: .capture,
            renderStyle: .promptCard,
            score: 64,
            reason: "An Enchantment needs a chosen working and real proof before the Book counts it.",
            prompt: enchantment.title,
            detail: enchantment.detail,
            payload: BookPagePayload(
                headline: "Enchantment Page: \(enchantment.title)",
                body: "\(enchantment.detail)\n\nDo the real working, then keep the proof here. The Book will not count magic that only happened in prose.",
                metadata: [
                    "source": "enchantment",
                    "enchantmentID": enchantment.id,
                    "enchantmentName": enchantment.title,
                    "placeholder": "Add the proof: what changed, what you did, or what image shows \(enchantment.title) touched the real world.",
                    "tags": "enchantment,proof,real-world-magic,\(enchantment.id)"
                ]
            )
        )
    }

    private func surface(forManualPageType type: BookPageType) -> SurfacePage {
        if let existing = surfaces.first(where: { $0.type == type }) {
            return existing
        }
        return freshManualSurface(for: type)
    }

    private func freshManualSurface(for type: BookPageType) -> SurfacePage {
        BookPageSourceAdapters.manualSurface(
            for: type,
            day: today,
            context: CuratorContext.make(for: today),
            inputs: sourceInputs,
            now: Date()
        )
    }

    @MainActor
    private func openManualPage(_ type: BookPageType) async {
        switch type {
        case .narrativeOS:
            if preparedStoryPageSurface == nil {
                statusMessage = "The Story Page is calling the local Book brain..."
                _ = await prepareStoryPageIfPossible(force: true)
            }
            selectedSurface = preparedStoryPageSurface ?? localBrainIssueSurface(
                type: type,
                title: "Story Page",
                action: "write a Story Page"
            )
        case .gossip:
            if preparedGossipPageSurface == nil {
                statusMessage = "The Gossip Page is waking the whisper engine..."
                _ = await prepareGossipPageIfPossible(force: true)
            }
            selectedSurface = preparedGossipPageSurface ?? localBrainIssueSurface(
                type: type,
                title: "Gossip Page",
                action: "write a Gossip Page"
            )
        case .facultyResearch:
            if preparedFacultyResearchSurface == nil {
                statusMessage = "The faculty folio is asking Gemma to read the clippings..."
                _ = await prepareFacultyResearchPageIfPossible(force: true)
            }
            selectedSurface = preparedFacultyResearchSurface ?? localBrainIssueSurface(
                type: type,
                title: "Faculty Research",
                action: "write a Faculty Research Page"
            )
        case .weather:
            if weatherPageSignal == nil || enchantedWeather == nil {
                statusMessage = "The Weather Page is asking the sky, then Gemma."
                _ = await refreshWeatherSignal(isUserInitiated: true, shouldEnchant: true)
            }
            if weatherPageSignal != nil, enchantedWeather != nil {
                selectedSurface = freshManualSurface(for: type)
            } else {
                selectedSurface = localBrainIssueSurface(
                    type: type,
                    title: "Weather Page",
                    action: "translate the weather"
                )
            }
        default:
            selectedSurface = surface(forManualPageType: type)
        }
    }

    private func localBrainIssueSurface(type: BookPageType, title: String, action: String) -> SurfacePage {
        let detail = localBrainTelemetry.lastError ?? localBrainTelemetry.currentWorkStatus ?? "The local model did not return a page."
        return SurfacePage(
            id: "local-brain-issue-\(type.rawValue)-\(Int(Date().timeIntervalSince1970))",
            type: type,
            sourceID: "local-brain",
            intent: .reflect,
            renderStyle: .promptCard,
            score: 1,
            reason: "The local model did not finish this generated Page.",
            prompt: "\(title) could not be generated yet.",
            detail: detail,
            payload: BookPagePayload(
                headline: "\(title) Still Waking",
                body: "Gemma tried to \(action), but did not finish.\n\n\(detail)",
                metadata: [
                    "source": "local-brain",
                    "status": "failed",
                    "pageType": type.rawValue
                ]
            )
        )
    }

    private func readingSurface(forWonderCompassSectionID sectionID: String) -> SurfacePage {
        let snippet = BookReferenceCatalog.wonderCompass.first { $0.id == sectionID }
            ?? BookReferenceCatalog.wonderCompass.first
            ?? ReferenceSnippet(
                id: "wonder-compass-empty",
                sourceID: "wonder-compass",
                title: "The Wonder Compass",
                prompt: "Read the source text.",
                body: "The Wonder Compass text is not bundled in this build.",
                tags: ["wonder-compass"]
            )
        let source = BookPageSourceRegistry.source(for: .wonderCompass)
        return SurfacePage(
            id: "\(source.id)-reading-\(snippet.id)",
            type: .wonderCompass,
            sourceID: source.id,
            intent: .importReference,
            renderStyle: .quoteCard,
            score: 70,
            reason: "Opened from the Wonder Compass table of contents.",
            prompt: "Reading Page",
            detail: snippet.title,
            payload: BookPagePayload(
                headline: snippet.title,
                body: snippet.body,
                metadata: [
                    "source": source.id,
                    "snippetID": snippet.id,
                    "tags": snippet.tags.joined(separator: ","),
                    "readingPage": "true"
                ]
            )
        )
    }

    private func resetTransientWorkStateForBackgrounding() {
        localBrainTelemetry.resetTransientWork()
        isBraiding = false
        braidingStartedAt = nil
        isPreparingStoryPage = false
        isPreparingGossipPage = false
        isPreparingFacultyResearchPage = false
        isPreparingAutomaticIllumination = false
    }

    @ViewBuilder
    private var localBrainWorkShelf: some View {
        if localBrainTelemetry.isWorking {
            LocalBrainWorkingStatusCard(
                label: localBrainTelemetry.currentLabel,
                quip: LocalBrainQuips.lines[localBrainQuipIndex],
                startedAt: localBrainTelemetry.startedAt,
                queuedCount: localBrainTelemetry.currentQueuedCount
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
                    SwipeDismissSurfaceCard(surface: surface, isBusy: workBlockingState.surfaceBusyIndicator(for: surface.type)) {
                        BookFeedback.play(surface.type == .bookOfYou ? .tap : .openPage)
                        switch SurfaceActionRouter(workState: workBlockingState).decision(
                            for: surface.type,
                            readiness: SurfaceReadinessState(surface: surface)
                        ) {
                        case .blocked(let message):
                            BookFeedback.play(.error)
                            statusMessage = message
                        case .braid:
                            Task { await braidToday() }
                        case .open:
                            if SurfaceReadinessState(surface: surface).needsLocalBrainToOpen {
                                Task { await generateAndOpenSurface(surface) }
                            } else {
                                selectedSurface = surface
                            }
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
                    actionTitle: statusActionTitle,
                    action: statusAction
                )
            }
        }
    }

    private var statusActionTitle: String? {
        if undoRemovedPage != nil {
            return "Put it back"
        }
        if undoSurface != nil {
            return "Call it back"
        }
        return braidRecovery.retryActionTitle
    }

    private var statusAction: (() -> Void)? {
        if undoRemovedPage != nil {
            return { restoreLastRemovedPage() }
        }
        if undoSurface != nil {
            return { undoLastSurfaceDismissal() }
        }
        if braidRecovery.canRetry {
            return {
                Task { await braidToday() }
            }
        }
        return nil
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

    private var labPanelShelf: some View {
        let eligibleBraidCount = today.capturedPages.filter { !$0.usedInBookOfYou }.count
        let queuedGeneratedPages = [
            preparedStoryPageSurface,
            preparedGossipPageSurface,
            preparedFacultyResearchSurface,
            automaticIlluminatedSurface
        ].compactMap(\.self)

        return foldedShelf(
            title: "Lab Panel",
            status: databaseReport.loadSource.rawValue,
            accent: BookPalette.teal,
            isExpanded: $isLabPanelExpanded
        ) {
            VStack(alignment: .leading, spacing: 10) {
                diagnosticRow("model", modelReport.title)
                diagnosticRow("preferred", modelReport.preferredModelID)
                diagnosticRow("device", modelReport.deviceSummary)
                diagnosticRow("store", "\(storeReport.loadSource.rawValue) · \(storeReport.dayCount)d · \(storeReport.pageCount)p")
                diagnosticRow("database", "v\(databaseReport.schemaVersion) · \(databaseReport.loadSource.rawValue) · \(databaseReport.backupCount) backups")
                diagnosticRow("today", "\(today.pages.count)p · \(today.capturedPages.count) captured · \(eligibleBraidCount) eligible")
                diagnosticRow("book of you", today.bookOfYou == nil ? "not kept today" : "kept today")
                diagnosticRow("surfaces", surfaces.map(\.id).joined(separator: " | "))
                diagnosticRow("sources", "\(enabledActiveSourceCount)/\(BookPageSourceRegistry.activeSources.count) active")
                diagnosticRow("faculty", "\(facultyEntries.count) entries")
                diagnosticRow("resurfacing", "\(resurfacedPages.count) candidates")
                diagnosticRow("queued", queuedGeneratedPages.map(\.type.shortTitle).joined(separator: " | "))
                diagnosticRow("work", labWorkStatus)
                diagnosticRow("last brain", labLastBrainStatus)
                diagnosticRow("last braid", lastBraidDuration.map { "\(Int($0.rounded()))s" } ?? "none")

                if let lastError = localBrainTelemetry.lastError {
                    diagnosticRow("brain error", lastError, isWarning: true)
                }
                if let lastError = databaseReport.lastError ?? storeReport.lastError {
                    diagnosticRow("shelf error", lastError, isWarning: true)
                }
                if let lastBackupPath = databaseReport.lastBackupPath {
                    diagnosticRow("last backup", lastBackupPath)
                }
            }
        }
    }

    private var labWorkStatus: String {
        workBlockingState.labWorkStatus
    }

    private var labLastBrainStatus: String {
        localBrainTelemetry.lastWorkStatus { Self.labTimestampFormatter.string(from: $0) }
    }

    private static let labTimestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter
    }()

    private func diagnosticRow(_ label: String, _ value: String, isWarning: Bool = false) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(label)
                .font(.caption2.monospaced().weight(.bold))
                .foregroundStyle(BookPalette.gold.opacity(0.78))
                .frame(width: 82, alignment: .leading)

            Text(value.isEmpty ? "none" : value)
                .font(.caption.monospaced())
                .foregroundStyle(isWarning ? .red.opacity(0.86) : BookPalette.nightText.opacity(0.76))
                .lineLimit(3)
                .minimumScaleFactor(0.82)
                .frame(maxWidth: .infinity, alignment: .leading)
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
                        FragmentRow(page: page) {
                            removeKeptPage(page)
                        }
                        .transition(.asymmetric(
                            insertion: .move(edge: .top).combined(with: .opacity),
                            removal: .move(edge: .trailing).combined(with: .opacity)
                        ))
                    }
                }
                .animation(.spring(response: 0.48, dampingFraction: 0.84), value: today.capturedPages.map(\.id))
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
                        isRequesting: isRequestingWeather || !workBlockingState.canRequestWeather,
                        hasRequested: didRequestWeatherLocation,
                        isAvailable: WeatherLocationReader.isAvailable
                    ) {
                        guard workBlockingState.canRequestWeather else {
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
        let delta: Int
        if surface.type == .wonderCompass, surface.payload.metadata["runID"] != nil {
            delta = surface.payload.metadata["compassStep"] == "rest" ? 6 : 0
        } else {
            delta = 1
        }
        guard delta != 0 else { return }
        let newScore = min(100, max(0, beliefScore + delta))
        guard newScore != beliefScore else { return }
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = newScore
        }
    }

    private func completeCompassRunIfNeeded(_ surface: SurfacePage) {
        guard surface.type == .wonderCompass,
              surface.payload.metadata["compassStep"] == "rest",
              let runID = surface.payload.metadata["runID"] else {
            return
        }
        var completed = Set(completedCompassRunLedger
            .split(separator: ",")
            .map { String($0).trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty })
        guard !completed.contains(runID) else { return }
        completed.insert(runID)
        completedCompassRunLedger = completed.sorted().joined(separator: ",")
        let newScore = min(100, max(0, beliefScore + 6))
        guard newScore != beliefScore else { return }
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = newScore
        }
    }

    private func openStoryMechanicReturnPage(from completedSurface: SurfacePage, outcome: String) {
        guard completedSurface.payload.metadata["storyMechanicReturn"] == "true" else { return }
        Task { await prepareAndOpenStoryMechanicReturnPage(from: completedSurface, outcome: outcome) }
    }

    @MainActor
    private func prepareAndOpenStoryMechanicReturnPage(from completedSurface: SurfacePage, outcome: String) async {
        guard !localBrainTelemetry.isWorking else {
            statusMessage = "The Story Page heard the result. Let the current ink dry, then continue the thread."
            return
        }

        let returnSurface = storyMechanicReturnSurface(from: completedSurface, outcome: outcome)
        statusMessage = "The Story Page is folding the \(completedSurface.prompt) result back into the thread..."

        do {
            let prose: StoryPageProse
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXStoryPageWriter().write(surface: returnSurface)
            #else
            prose = try await FakeStoryPageWriter().write(surface: returnSurface)
            #endif
            let prepared = returnSurface.preparedStoryPageCopy(
                prose: prose,
                slotID: "mechanic-return-\(Int(Date().timeIntervalSince1970))"
            )
            selectedSurface = prepared
            statusMessage = "The mechanic result has become the next Story Page."
        } catch {
            selectedSurface = localBrainIssueSurface(
                type: .narrativeOS,
                title: "Story Page",
                action: "fold the mechanic result back into the story"
            )
            statusMessage = "The Story Page could not fold the mechanic result yet."
        }
    }

    private func storyMechanicReturnSurface(from completedSurface: SurfacePage, outcome: String) -> SurfacePage {
        let metadata = completedSurface.payload.metadata
        let mechanic = metadata["storyMechanicKind"] ?? "story-mechanic"
        let thread = metadata["storyThread"] ?? "Ordinary Magic"
        let choiceTitle = metadata["storyChoiceTitle"] ?? completedSurface.prompt
        let choicePrompt = metadata["storyChoicePrompt"] ?? completedSurface.detail
        let choiceEffect = metadata["storyChoiceEffect"] ?? "The mechanic result changes what the thread can do next."
        let priorScene = metadata["storyScene"] ?? "A previous Story Page asked for a real mechanic before the thread moved on."
        let outcomeText = outcome.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? completedSurface.payload.body
        let source = BookPageSourceRegistry.source(for: .narrativeOS)
        let continuation = """
        A Story Page choice asked for \(mechanic).

        Previous scene:
        \(priorScene)

        Chosen story action:
        \(choiceTitle) — \(choicePrompt)

        Intended movement:
        \(choiceEffect)

        Completed mechanic page:
        \(completedSurface.prompt)

        Player-kept result:
        \(outcomeText)

        Continue the thread from the real completed mechanic. Do not claim any extra real-world action beyond this result.
        """

        return SurfacePage(
            id: "story-mechanic-return-\(completedSurface.id)-\(Int(Date().timeIntervalSince1970))",
            type: .narrativeOS,
            sourceID: source.id,
            intent: .reflect,
            renderStyle: .promptCard,
            score: max(completedSurface.score, 74),
            reason: "A completed mechanic is ready to become the next Story Page beat.",
            prompt: "Story Page Return",
            detail: "The thread continues from \(completedSurface.prompt).",
            payload: BookPagePayload(
                headline: "Story Page Return",
                body: continuation.bookPreviewSentenceLimit(2),
                metadata: [
                    "source": source.id,
                    "selectedThreads": thread,
                    "selectedEntities": "the-book",
                    "realSignals": "A completed \(mechanic) page is feeding back into the story.",
                    "relationshipPressures": "The Story Page must honor the mechanic result before offering the next choice.",
                    "storyContinuationContext": continuation,
                    "tags": "story-mechanic-return,\(mechanic)"
                ]
            )
        )
    }

    @MainActor
    private func generateAndOpenSurface(_ surface: SurfacePage) async {
        guard scenePhase == .active else {
            statusMessage = "The Book can only write while ReEnchanted is open on screen."
            return
        }

        switch surface.type {
        case .narrativeOS:
            statusMessage = "The Story Page is calling the local Book brain..."
            _ = await prepareStoryPageIfPossible(force: true)
            selectedSurface = preparedStoryPageSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Story Page",
                action: "write a Story Page"
            )
        case .gossip:
            statusMessage = "The Gossip Page is waking the whisper engine..."
            _ = await prepareGossipPageIfPossible(force: true)
            selectedSurface = preparedGossipPageSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Gossip Page",
                action: "write a Gossip Page"
            )
        case .facultyResearch:
            statusMessage = "The faculty folio is asking Gemma to read the clippings..."
            _ = await prepareFacultyResearchPageIfPossible(force: true)
            selectedSurface = preparedFacultyResearchSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Faculty Research",
                action: "write a Faculty Research Page"
            )
        case .weather:
            statusMessage = "The Weather Page is asking the sky, then Gemma."
            if weatherPageSignal == nil {
                _ = await refreshWeatherSignal(isUserInitiated: true, shouldEnchant: true)
            } else if enchantedWeather == nil {
                _ = await prepareWeatherPageIfPossible()
            }
            selectedSurface = enchantedWeather == nil
                ? localBrainIssueSurface(type: surface.type, title: "Weather Page", action: "translate the weather")
                : freshManualSurface(for: .weather)
        case .wonderCompass:
            statusMessage = "The Compass is asking Gemma which passage belongs here."
            _ = await prepareWonderCompassSelectionIfPossible(force: true)
            selectedSurface = selectedCuratorSurfaces.first {
                $0.type == .wonderCompass && $0.payload.metadata["selector"] == "gemma"
            } ?? surface
        case .illuminatedPhoto:
            statusMessage = "Penny is asking Gemma to illuminate a photo."
            _ = await prepareAutomaticIlluminatedPageIfPossible()
            selectedSurface = automaticIlluminatedSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Illuminated Photo",
                action: "illuminate a photo"
            )
        default:
            selectedSurface = surface
        }
    }

    @discardableResult
    private func prepareAutomaticIlluminatedPageIfPossible() async -> Bool {
        #if canImport(Photos) && canImport(UIKit)
        guard automaticIlluminatedSurface == nil,
              !isPreparingAutomaticIllumination,
              !localBrainTelemetry.isWorking,
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
            localBrainTelemetry.clearError()
            statusMessage = "Penny prepared an illuminated photo page. It is ready if the curator lets it rise."
            return true
        } catch {
            appLog.error("Automatic illuminated page preparation failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("illumination: \(error.localizedDescription)")
            statusMessage = "Penny tried to prepare an illuminated photo page, but the press snagged: \(error.localizedDescription)"
            userPhotoIlluminationFallbackAllowed = true
            return false
        }
        #else
        return false
        #endif
    }

    private func analyzeAutomaticIlluminatedPhoto(_ image: UIImage) async -> PhotoAnalysis {
        #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
        do {
            return try await GemmaPhotoIlluminationAnalyzer().analyze(photo: image)
        } catch {
            appLog.error("Automatic photo Gemma analysis fell back: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("photo analysis fallback: \(error.localizedDescription)")
            return PhotoAnalysis.academyFallback
        }
        #else
        return PhotoAnalysis.academyFallback
        #endif
    }

    @MainActor
    @discardableResult
    private func prepareStoryPageIfPossible(force: Bool = false) async -> Bool {
        guard scenePhase == .active else {
            localBrainTelemetry.recordError("story page: Gemma can only write while ReEnchanted is open on screen.")
            return false
        }
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 4)
        if force {
            guard !isPreparingStoryPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard storyPageRecovery.shouldBegin(
                isPreparing: isPreparingStoryPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: preparedStoryPageSurface,
                slotID: slot,
                requiredMetadataKey: "storyScene",
                now: surfaceRefreshDate
            ) else {
                return false
            }
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
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXStoryPageWriter().write(surface: draft)
            #else
            prose = try await FakeStoryPageWriter().write(surface: draft)
            #endif
            preparedStoryPageSurface = draft.preparedStoryPageCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            storyPageRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "The Story Page has dried and is waiting for the curator."
            return true
        } catch {
            appLog.error("Prepared Story Page failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("story page: \(error.localizedDescription)")
            preparedStoryPageSurface = nil
            storyPageRecovery.recordFailure()
            statusMessage = "The Story Page did not finish drying. The Book will try again later."
            return false
        }
    }

    @MainActor
    @discardableResult
    private func prepareGossipPageIfPossible(force: Bool = false) async -> Bool {
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 4)
        if force {
            guard !isPreparingGossipPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard gossipPageRecovery.shouldBegin(
                isPreparing: isPreparingGossipPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: preparedGossipPageSurface,
                slotID: slot,
                requiredMetadataKey: "gossipProse",
                now: surfaceRefreshDate
            ) else {
                return false
            }
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
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXGossipPageWriter().write(surface: draft)
            #else
            prose = try await FakeGossipPageWriter().write(surface: draft)
            #endif
            preparedGossipPageSurface = draft.preparedGossipPageCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            gossipPageRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "A Gossip Page has dried. The margins are pretending they did not gossip."
            return true
        } catch {
            appLog.error("Prepared Gossip Page failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("gossip page: \(error.localizedDescription)")
            preparedGossipPageSurface = nil
            gossipPageRecovery.recordFailure()
            statusMessage = "The Gossip Page lost its whisper. The Book will try again later."
            return false
        }
    }

    @MainActor
    @discardableResult
    private func prepareFacultyResearchPageIfPossible(force: Bool = false) async -> Bool {
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 12)
        if force {
            guard !isPreparingFacultyResearchPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard facultyResearchRecovery.shouldBegin(
                isPreparing: isPreparingFacultyResearchPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: preparedFacultyResearchSurface,
                slotID: slot,
                requiredMetadataKey: "researchProse",
                now: surfaceRefreshDate
            ) else {
                return false
            }
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
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXFacultyResearchWriter().write(surface: draft)
            #else
            prose = try await FallbackFacultyResearchWriter().write(surface: draft)
            #endif
            preparedFacultyResearchSurface = draft.preparedFacultyResearchCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            facultyResearchRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "\(draft.payload.metadata["facultyName"] ?? "The Support Guild") prepared a research folio for tonight."
            return true
        } catch {
            appLog.error("Prepared faculty research failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("faculty research: \(error.localizedDescription)")
            preparedFacultyResearchSurface = nil
            facultyResearchRecovery.recordFailure()
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

    private func removeKeptPage(_ page: BookPage) {
        BookFeedback.play(.dismissPage)
        var day = today
        guard let index = day.pages.firstIndex(where: { $0.id == page.id }) else {
            statusMessage = "That page has already left the margin."
            return
        }

        let removedPage = day.pages.remove(at: index)
        undoRemovedPage = removedPage
        undoRemovedPageDayID = day.id
        undoSurface = nil
        undoDayID = nil
        persist(day: day, message: "The \(removedPage.type.shortTitle.lowercased()) page left Today's Margins.")
    }

    private func restoreLastRemovedPage() {
        guard let page = undoRemovedPage,
              let dayID = undoRemovedPageDayID,
              var day = days.first(where: { $0.id == dayID }) ?? (dayID == today.id ? today : nil) else {
            undoRemovedPage = nil
            undoRemovedPageDayID = nil
            return
        }

        BookFeedback.play(.undo)
        guard !day.pages.contains(where: { $0.id == page.id }) else {
            undoRemovedPage = nil
            undoRemovedPageDayID = nil
            statusMessage = "That page is already back in the margins."
            return
        }

        day.pages.append(page)
        day.pages.sort { $0.createdAt < $1.createdAt }
        undoRemovedPage = nil
        undoRemovedPageDayID = nil
        persist(day: day, message: "The \(page.type.shortTitle.lowercased()) page returned to Today's Margins.")
    }

    private func dismissSurface(_ surface: SurfacePage) {
        BookFeedback.play(.dismissPage)
        undoRemovedPage = nil
        undoRemovedPageDayID = nil
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
        guard workBlockingState.canStartBraid else {
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
        braidRecovery.beginAttempt()
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
            var braid = try await braider.braid(day: today)
            braid.mediaAssets = today.capturedPages.flatMap(\.mediaAssets)
            let day = BraidRecoveryState.dayByMarkingCapturedPagesUsed(today, braid: braid)
            if braid.tags.contains("local-model-missing") {
                persist(day: day, message: "The Book kept today's page in its fallback hand. The local brain is still waking.")
            } else if braid.tags.contains("mlx-hook") {
                persist(day: day, message: "The model doorway answered. On the phone, the braid will be local.")
            } else {
                persist(day: day, message: "The ink dried. Today's Book of You page is kept.")
            }
            BookFeedback.play(.braidComplete)
            modelReport = LocalModelManager.report()
            localBrainTelemetry.clearError()
            braidRecovery.recordSuccess()
        } catch {
            BookFeedback.play(.error)
            localBrainTelemetry.recordError("braid: \(error.localizedDescription)")
            braidRecovery.recordFailure(error.localizedDescription, day: today)
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
    private func refreshDynamicSourcesIfNeeded(
        now: Date = Date(),
        allowsGeneratedWork: Bool = true
    ) async {
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
            if await refreshWeatherSignal(isUserInitiated: false, shouldEnchant: allowsGeneratedWork) {
                lastAutomaticWeatherSourceRefreshSlot = refreshSlot
            }
        }
    }

    @discardableResult
    @MainActor
    private func refreshWeatherSignal(isUserInitiated: Bool, shouldEnchant: Bool) async -> Bool {
        guard !isRequestingWeather else { return false }
        guard !shouldEnchant || workBlockingState.canRequestWeather else {
            if isUserInitiated {
                weatherMessage = "The Book is already writing. Let that ink dry, then ask the sky again."
            }
            return false
        }
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
    @discardableResult
    private func prepareWeatherPageIfPossible() async -> Bool {
        guard let signal = sourceInputs.weather,
              signal.isAvailable,
              enchantedWeather == nil,
              workBlockingState.canRequestWeather else {
            return false
        }

        do {
            AppMemoryLedger.record("weather-before-curator-gemma")
            let enchanted = try await weatherEnchanter.enchantWeather(weather: signal, day: today)
            AppMemoryLedger.record("weather-after-curator-gemma")
            weatherPageSignal = signal
            enchantedWeather = enchanted
            surfaceRefreshDate = Date()
            localBrainTelemetry.clearError()
            statusMessage = "The Weather Page has dried. The curator can let it rise."
            return true
        } catch {
            localBrainTelemetry.recordError("weather page: \(error.localizedDescription)")
            statusMessage = "The Weather Page could not finish translating yet."
            return false
        }
    }

    @MainActor
    private func refreshWonderCompassSelection() async {
        _ = await prepareWonderCompassSelectionIfPossible(force: true)
    }

    @MainActor
    @discardableResult
    private func prepareWonderCompassSelectionIfPossible(force: Bool = false) async -> Bool {
        guard isSourceEnabled(sourceID: "wonder-compass"),
              !isChoosingWonderCompassPassage else {
            return false
        }
        if !force, selectedWonderCompassSnippet != nil, selectedWonderCompassSelector == "gemma" {
            return false
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
        guard !candidates.isEmpty else { return false }

        do {
            selectedWonderCompassSnippet = try await wonderCompassChooser.chooseWonderCompassSnippet(
                day: today,
                inputs: inputsWithoutSelection,
                candidates: candidates
            )
            selectedWonderCompassSelector = "gemma"
            surfaceRefreshDate = Date()
            localBrainTelemetry.clearError()
            return true
        } catch {
            localBrainTelemetry.recordError("wonder compass: \(error.localizedDescription)")
            selectedWonderCompassSnippet = nil
            selectedWonderCompassSelector = nil
            return false
        }
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

        #if NATIVE_LOCAL_BRAIN && canImport(MLXLMHFAPI)
        do {
            let model = LocalModelManager.preferredModel
            let modelID = model.modelID
            appLog.info("Starting streaming Hugging Face download for \(modelID, privacy: .public)")
            let directory = LocalModelManager.modelDirectory(for: modelID)
            installMessage = "Clearing old local models before downloading \(model.label)..."
            LocalModelManager.removeKnownLocalModels()
            try await LocalModelStreamingInstaller.download(
                modelID: modelID,
                revision: model.revision,
                to: directory
            ) { progress in
                let percent = Int(progress.fraction * 100)
                installProgress = progress.fraction
                installMessage = "Downloading \(model.label)... \(percent)%"
            }
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

private struct LocalModelDownloadProgress: Sendable {
    var completedBytes: Int64
    var totalBytes: Int64

    var fraction: Double {
        guard totalBytes > 0 else { return 0 }
        return min(max(Double(completedBytes) / Double(totalBytes), 0), 1)
    }
}

private enum LocalModelStreamingInstaller {
    private struct RepoInfo: Decodable {
        var siblings: [Sibling]
    }

    private struct Sibling: Decodable {
        var rfilename: String
        var size: Int64?
    }

    static func download(
        modelID: String,
        revision: String,
        to directory: URL,
        progressHandler: @MainActor @Sendable @escaping (LocalModelDownloadProgress) -> Void
    ) async throws {
        let files = try await filesToDownload(modelID: modelID, revision: revision)
        let totalBytes = files.reduce(Int64(0)) { $0 + ($1.size ?? 1) }
        var completedBytes = Int64(0)
        let fileManager = FileManager.default

        try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)

        for file in files {
            try Task.checkCancellation()
            let destination = directory.appendingPathComponent(file.rfilename)
            try fileManager.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)

            let expectedSize = file.size
            if let expectedSize,
               let currentSize = existingFileSize(at: destination),
               currentSize == expectedSize {
                completedBytes += expectedSize
                await progressHandler(LocalModelDownloadProgress(completedBytes: completedBytes, totalBytes: totalBytes))
                continue
            }

            let temporaryURL = destination
                .deletingLastPathComponent()
                .appendingPathComponent(".\(destination.lastPathComponent).download")
            try? fileManager.removeItem(at: temporaryURL)

            let startingBytes = completedBytes
            let downloader = LocalModelFileDownloader(destination: temporaryURL) { bytesWritten, expectedBytes in
                let fileBytes = expectedSize ?? expectedBytes
                let downloadTotal = max(totalBytes - (expectedSize ?? 1) + fileBytes, 1)
                let downloadProgress = LocalModelDownloadProgress(
                    completedBytes: startingBytes + min(bytesWritten, fileBytes),
                    totalBytes: downloadTotal
                )
                Task { @MainActor in
                    progressHandler(downloadProgress)
                }
            }
            try await downloader.download(from: resolveURL(modelID: modelID, revision: revision, path: file.rfilename))

            if let expectedSize {
                let actualSize = fileSize(from: try fileManager.attributesOfItem(atPath: temporaryURL.path)[.size])
                guard actualSize == expectedSize else {
                    try? fileManager.removeItem(at: temporaryURL)
                    throw CocoaError(.fileReadCorruptFile)
                }
            }

            try? fileManager.removeItem(at: destination)
            try fileManager.moveItem(at: temporaryURL, to: destination)
            completedBytes += expectedSize ?? (existingFileSize(at: destination) ?? 1)
            await progressHandler(LocalModelDownloadProgress(completedBytes: completedBytes, totalBytes: totalBytes))
        }
    }

    private static func filesToDownload(modelID: String, revision: String) async throws -> [Sibling] {
        let infoURL = apiURL(modelID: modelID, revision: revision)
        let (data, response) = try await URLSession.shared.data(from: infoURL)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        let repoInfo = try JSONDecoder().decode(RepoInfo.self, from: data)
        return repoInfo.siblings
            .filter { shouldInstall(path: $0.rfilename) }
            .sorted { left, right in
                let leftWeight = left.rfilename.hasSuffix(".safetensors") ? 1 : 0
                let rightWeight = right.rfilename.hasSuffix(".safetensors") ? 1 : 0
                if leftWeight != rightWeight {
                    return leftWeight < rightWeight
                }
                return left.rfilename < right.rfilename
            }
    }

    private static func shouldInstall(path: String) -> Bool {
        let allowedSuffixes = [".safetensors", ".json", ".jinja", ".model", ".txt"]
        return allowedSuffixes.contains { path.hasSuffix($0) }
    }

    private static func existingFileSize(at url: URL) -> Int64? {
        guard let size = try? FileManager.default.attributesOfItem(atPath: url.path)[.size] else {
            return nil
        }
        return fileSize(from: size)
    }

    private static func fileSize(from value: Any?) -> Int64? {
        if let size = value as? Int64 {
            return size
        }
        if let number = value as? NSNumber {
            return number.int64Value
        }
        return nil
    }

    private static func apiURL(modelID: String, revision: String) -> URL {
        var components = URLComponents()
        components.scheme = "https"
        components.host = "huggingface.co"
        components.path = "/api/models/\(modelID)/revision/\(revision)"
        return components.url!
    }

    private static func resolveURL(modelID: String, revision: String, path: String) -> URL {
        var components = URLComponents()
        components.scheme = "https"
        components.host = "huggingface.co"
        components.path = "/\(modelID)/resolve/\(revision)/\(path)"
        components.queryItems = [URLQueryItem(name: "download", value: "true")]
        return components.url!
    }
}

private final class LocalModelFileDownloader: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
    private let destination: URL
    private let progressHandler: @Sendable (Int64, Int64) -> Void
    private let lock = NSLock()
    private var continuation: CheckedContinuation<Void, Error>?
    private var session: URLSession?

    init(destination: URL, progressHandler: @escaping @Sendable (Int64, Int64) -> Void) {
        self.destination = destination
        self.progressHandler = progressHandler
    }

    func download(from url: URL) async throws {
        try await withCheckedThrowingContinuation { continuation in
            lock.withLock {
                self.continuation = continuation
                let configuration = URLSessionConfiguration.default
                configuration.timeoutIntervalForRequest = 120
                configuration.timeoutIntervalForResource = 3600
                let session = URLSession(configuration: configuration, delegate: self, delegateQueue: nil)
                self.session = session
                session.downloadTask(with: url).resume()
            }
        }
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didWriteData bytesWritten: Int64,
        totalBytesWritten: Int64,
        totalBytesExpectedToWrite: Int64
    ) {
        progressHandler(totalBytesWritten, max(totalBytesExpectedToWrite, totalBytesWritten))
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        do {
            guard let response = downloadTask.response as? HTTPURLResponse,
                  (200..<300).contains(response.statusCode) else {
                throw URLError(.badServerResponse)
            }
            try FileManager.default.moveItem(at: location, to: destination)
            finish(with: .success(()))
        } catch {
            finish(with: .failure(error))
        }
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: Error?
    ) {
        if let error {
            finish(with: .failure(error))
        }
    }

    private func finish(with result: Result<Void, Error>) {
        let continuation = lock.withLock {
            let continuation = self.continuation
            self.continuation = nil
            self.session?.invalidateAndCancel()
            self.session = nil
            return continuation
        }
        switch result {
        case .success:
            continuation?.resume()
        case let .failure(error):
            continuation?.resume(throwing: error)
        }
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
