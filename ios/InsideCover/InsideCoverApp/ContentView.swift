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
    @Environment(\.scenePhase) var scenePhase

    @State var days: [BookDay] = [BookDay.today()]
    @State var generation = GenerationCoordinator()
    @State var selectedSurface: SurfacePage?
    @State var isInstallingModel = false
    @State var didRunSmokeBraid = false
    @State var statusMessage = ""
    @State var installMessage = ""
    @State var installProgress: Double?
    @State var modelReport = Self.placeholderModelReport
    @State var storeReport = Self.placeholderStoreReport
    @State var databaseReport = Self.placeholderDatabaseReport
    @State var resurfacedPages: [BookPage] = []
    @State var surfacedPages: [SurfacePage] = []
    @State var selfFacts: [SelfFact] = []
    @State var narrativeEvents: [NarrativeEvent] = []
    @State var entityMemories: [NarrativeEntityMemory] = []
    @State var customCastMembers: [CustomCastMember] = []
    @State var facultyEntries: [FacultyEntry] = []
    @State var bodySignal: BodySourceSignal?
    @State var weatherSignal: WeatherSourceSignal?
    @State var enchantedWeather: EnchantedWeatherSignal?
    @State var weatherPageSignal: WeatherSourceSignal?
    @State var isRequestingWeather = false
    @State var anchorLedger = AnchorRegistry.defaultAnchors
    @State var nearbyAnchor: AnchorProximity?
    @State var preparedAnchorSurface: SurfacePage?
    @State var isCheckingAnchors = false
    @State var selectedWonderCompassSnippet: ReferenceSnippet?
    @State var selectedWonderCompassSelector: String?
    @State var isChoosingWonderCompassPassage = false
    @State var isRequestingHealthKit = false
    @State var isSourceSettingsPresented = false
    @State var isCustomCastSheetPresented = false
    @State var surfaceRefreshDate = Date()
    @State var undoSurface: SurfacePage?
    @State var undoDayID: String?
    @State var undoRemovedPage: BookPage?
    @State var undoRemovedPageDayID: String?
    @State var userPhotoIlluminationFallbackAllowed = false
    @AppStorage("didRequestHealthKitBodySignal") var didRequestHealthKitBodySignal = false
    @AppStorage("didRequestWeatherLocation") var didRequestWeatherLocation = false
    @AppStorage("didRequestAnchorLocation") var didRequestAnchorLocation = false
    var vault: PlayerVault { PlayerVault.shared }
    var anchorLedgerData: String {
        get {
            guard let data = try? JSONEncoder().encode(vault.data.anchors),
                  let encoded = String(data: data, encoding: .utf8) else { return "" }
            return encoded
        }
        nonmutating set {
            guard let data = newValue.data(using: .utf8),
                  let decoded = try? JSONDecoder().decode([AnchorRecord].self, from: data) else { return }
            vault.data.anchors = decoded
            vault.save()
        }
    }
    @AppStorage("dismissedSurfaceLedgerV2") var dismissedSurfaceLedgerV2 = "{}"
    @AppStorage("sourcePreferenceLedger") var sourcePreferenceLedger = "{}"
    @AppStorage("illuminatedPhotoHistory") var illuminatedPhotoHistoryData = "{}"
    @AppStorage("lastAutomaticBodySourceRefreshSlot") var lastAutomaticBodySourceRefreshSlot = ""
    @AppStorage("lastAutomaticWeatherSourceRefreshSlot") var lastAutomaticWeatherSourceRefreshSlot = ""
    @AppStorage("beliefScore") var beliefScore = 30
    @AppStorage("completedCompassRunLedger") var completedCompassRunLedger = ""
    var entityBeliefLedgerData: String {
        get {
            guard let data = try? JSONEncoder().encode(vault.data.entityBelief),
                  let encoded = String(data: data, encoding: .utf8) else { return "{}" }
            return encoded
        }
        nonmutating set {
            guard let data = newValue.data(using: .utf8),
                  let decoded = try? JSONDecoder().decode([String: Int].self, from: data) else { return }
            vault.data.entityBelief = decoded
            vault.save()
        }
    }
    var pageBeliefLedgerData: String {
        get {
            guard let data = try? JSONEncoder().encode(vault.data.pageBelief),
                  let encoded = String(data: data, encoding: .utf8) else { return "{}" }
            return encoded
        }
        nonmutating set {
            guard let data = newValue.data(using: .utf8),
                  let decoded = try? JSONDecoder().decode([String: Int].self, from: data) else { return }
            vault.data.pageBelief = decoded
            vault.save()
        }
    }
    var electiveLedgerData: String {
        get {
            guard let data = try? JSONEncoder().encode(vault.data.electives),
                  let encoded = String(data: data, encoding: .utf8) else { return "[]" }
            return encoded
        }
        nonmutating set {
            guard let data = newValue.data(using: .utf8),
                  let decoded = try? JSONDecoder().decode([UnwrittenElective].self, from: data) else { return }
            vault.data.electives = decoded
            vault.save()
        }
    }
    @AppStorage("didCompleteStoryOnboarding") var didCompleteStoryOnboarding = false
    var marginTutorSeenData: String {
        get { MarginTutorLedger.encode(Set(vault.data.tutorSeen)) }
        nonmutating set {
            vault.data.tutorSeen = Array(MarginTutorLedger.seenIDs(from: newValue)).sorted()
            vault.save()
        }
    }
    @AppStorage("bookWhispersEnabled") var bookWhispersEnabled = true
    @AppStorage("bookCalendarEnabled") var bookCalendarEnabled = false
    @AppStorage(VellumNutritionist.keyStorageKey) var usdaKey = ""
    @State var calendarEvents: [CalendarEventSignal] = []
    @State var nearbyPlaces: [LocalPlaceSignal] = []
    @State var preparedSaveFileURL: URL?
    @State var isSaveImporterPresented = false
    @State var activeTutorNote: MarginTutorNote?
    @AppStorage("isTodaysMarginsExpanded") var isTodaysMarginsExpanded = false
    @AppStorage("isReturnedStacksExpanded") var isReturnedStacksExpanded = false
    @AppStorage("isBookOfYouShelfExpanded") var isBookOfYouShelfExpanded = false
    @AppStorage("isQuietMechanicsExpanded") var isQuietMechanicsExpanded = false
    @AppStorage("isLabPanelExpanded") var isLabPanelExpanded = false
    @State var healthKitMessage = HealthKitBodyReader.isAvailable
        ? "If you open the door, the Book can listen for the body's weather without showing the numbers."
        : "This room has no HealthKit doorway."
    @State var weatherMessage = WeatherLocationReader.isAvailable
        ? "If you lend the Book your place, it can translate the sky without naming the watcher."
        : "This room cannot hear the local sky yet."
    @State var anchorMessage = AnchorLocationReader.isAvailable
        ? "The Book can check nearby known Anchors and open the right Outer Stacks room."
        : "This room cannot hear the nearby ley line yet."
    @State var braidingQuipIndex = 0
    @State var localBrainTelemetry = LocalBrainTelemetryState()
    @State var localBrainQuipIndex = 0
    @State var isOpeningMovieVisible = true
    @State var isGlowMenuPresented = false
    @State var isStacksSearchPresented = false
    @State var isBookShopPresented = false
    @State var busySealID: String?
    @State var bannerSeed = Int.random(in: 0..<10_000)
    @State var lastKnockAt: Date?
    @State var knocksThisSession = 0
    @State var bookKnockNote: String?
    @State var bannerShudder = false
    @State var lastAnchorReadingLatitude: Double?
    @State var lastAnchorReadingLongitude: Double?
    @State var isAnchoringPlace = false
    @State var didHydrateLaunchState = false
    @State var didRunPostLaunchTasks = false

    let braider: Braider
    let wonderCompassChooser: WonderCompassPassageChoosing
    let weatherEnchanter: WeatherEnchanting
    let surfaceDismissalTTL: TimeInterval = 90 * 60
    let surfaceRefreshCadence: Duration = .seconds(20 * 60)
    let braidingQuipCadence: Duration = .seconds(3)
    let localBrainQuipCadence: Duration = .seconds(7)

    static var placeholderModelReport: LocalModelReport {
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

    static var placeholderStoreReport: BookStore.Report {
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

    static var placeholderDatabaseReport: BookDatabase.Report {
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

    var today: BookDay {
        BookStore.today(from: days)
    }

    var workBlockingState: WorkBlockingState {
        WorkBlockingState(
            isLocalBrainWorking: localBrainTelemetry.isWorking,
            localBrainStatus: localBrainTelemetry.currentWorkStatus,
            isBraiding: generation.isBraiding,
            isPreparingAutomaticIllumination: generation.isPreparingAutomaticIllumination,
            isPreparingStoryPage: generation.isPreparingStoryPage,
            isPreparingGossipPage: generation.isPreparingGossipPage,
            isPreparingFacultyResearchPage: generation.isPreparingFacultyResearchPage,
            isPreparingLetterPage: generation.isPreparingLetterPage,
            isRequestingWeather: isRequestingWeather
        )
    }

    var sourceInputs: BookSourceInputs {
        var inputs = BookSourceInputs.from(insideCover: InsideCoverStore.load())
        inputs.body = bodySignal
        if let weatherPageSignal {
            inputs.weather = weatherPageSignal
        }
        inputs.enchantedWeather = enchantedWeather
        inputs.anchors = anchorLedger
        inputs.nearbyAnchor = nearbyAnchor
        inputs.electives = electives
        inputs.entityBeliefOffsets = entityBeliefLedger
        inputs.surfaceHistory = vault.data.surfaceHistory ?? [:]
        inputs.calendarEvents = calendarEvents
        inputs.nearbyPlaces = nearbyPlaces
        inputs.resurfacingCandidates = resurfacedPages
        inputs.quietDays = NothingTide.quietDays(in: days, today: today.id)
        inputs.currentArc = vault.data.currentArc
        inputs.recentNarrativeEvents = narrativeEvents
        inputs.preparedAnchorSurface = preparedAnchorSurface
        inputs.selectedWonderCompass = selectedWonderCompassSnippet
        inputs.selectedWonderCompassSelector = selectedWonderCompassSelector
        inputs.preparedIlluminatedPhotoSurface = generation.automaticIlluminatedSurface
        inputs.preparedStoryPageSurface = generation.preparedStoryPageSurface
        inputs.preparedGossipPageSurface = generation.preparedGossipPageSurface
        inputs.preparedFacultyResearchSurface = generation.preparedFacultyResearchSurface
        inputs.preparedLetterSurface = generation.preparedLetterSurface
        inputs.userPhotoIlluminationFallbackAllowed = userPhotoIlluminationFallbackAllowed
        inputs.selfFacts = selfFacts
        inputs.facultyEntries = facultyEntries
        inputs.customCastMembers = customCastMembers.map { member in
            var adjusted = member
            let currentGlow = max(0, min(100, member.baseBelief + (entityBeliefLedger[member.id] ?? 0)))
            adjusted.baseBelief = currentGlow
            return adjusted
        }
        inputs.narrative = NarrativeSourceSnapshotBuilder.snapshot(
            from: narrativeEvents,
            memories: entityMemories,
            beliefWeight: beliefScore
        )
        return inputs
    }

    var selectedCuratorSurfaces: [SurfacePage] {
        buildCuratorSurfaces(now: surfaceRefreshDate)
    }

    var surfaces: [SurfacePage] {
        surfacedPages
    }

    func buildCuratorSurfaces(now: Date) -> [SurfacePage] {
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

    var enabledActiveSourceCount: Int {
        BookPageSourceRegistry.activeSources.filter { isSourceEnabled(sourceID: $0.id) }.count
    }

    var entityBeliefLedger: [String: Int] {
        (try? JSONDecoder().decode([String: Int].self, from: Data(entityBeliefLedgerData.utf8))) ?? [:]
    }

    var pageBeliefLedger: [String: Int] {
        (try? JSONDecoder().decode([String: Int].self, from: Data(pageBeliefLedgerData.utf8))) ?? [:]
    }

    var pageBeliefProfiles: [PageBeliefProfile] {
        BookPageSourceRegistry.beliefProfiles(ledger: pageBeliefLedger)
    }

    var glowEntityMenuItems: [GlowEntityMenuItem] {
        let ledger = entityBeliefLedger
        return (NarrativePackRegistry.entities + customCastMembers.map(\.entity))
            .filter { !Self.pageEntityIDsInPagesMenu.contains($0.id) }
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

    static let pageEntityIDsInPagesMenu: Set<String> = [
        "body-page",
        "weather-page"
    ]

    var glowPageMenuItems: [GlowPageMenuItem] {
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

    var glowBookSectionMenuItems: [GlowBookSectionMenuItem] {
        BookReferenceCatalog.wonderCompass.map { snippet in
            GlowBookSectionMenuItem(
                id: snippet.id,
                title: snippet.title,
                detail: snippet.prompt
            )
        }
    }

    var glowEnchantmentMenuItems: [GlowEnchantmentMenuItem] {
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
                                AnyView(topBanner)
                                AnyView(hero)
                                AnyView(localBrainWorkShelf)
                                AnyView(surfaceShelf)
                                AnyView(marginaliaSealsRow)
                                AnyView(todayFragments)
                                AnyView(resurfacedShelf)
                                AnyView(archiveShelf)
                                AnyView(sourceControlsShelf)
                            }
                            .padding(.horizontal, 20)
                            .padding(.vertical, 18)
                            .frame(maxWidth: 920)
                            .frame(maxWidth: .infinity)
                        }
                    }
                }

                if let activeTutorNote {
                    VStack {
                        Spacer()
                        MarginTutorNoteCard(note: activeTutorNote) {
                            withAnimation(.spring(response: 0.4, dampingFraction: 0.82)) {
                                self.activeTutorNote = nil
                            }
                        }
                        .padding(.horizontal, 18)
                        .padding(.bottom, 18)
                    }
                    .zIndex(17)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .task(id: activeTutorNote.id) {
                        try? await Task.sleep(for: .seconds(12))
                        guard !Task.isCancelled else { return }
                        withAnimation(.easeOut(duration: 0.5)) {
                            self.activeTutorNote = nil
                        }
                    }
                }

                if !didCompleteStoryOnboarding && !isOpeningMovieVisible {
                    OnboardingFlowView { result in
                        completeOnboarding(result)
                    }
                    .zIndex(18)
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
            onCreateCastMember: {
                BookFeedback.play(.openPage)
                isCustomCastSheetPresented = true
            },
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
            .task(id: generation.isBraiding) {
                guard generation.isBraiding else { return }
                while !Task.isCancelled && generation.isBraiding {
                    try? await Task.sleep(for: braidingQuipCadence)
                    guard !Task.isCancelled && generation.isBraiding else { return }
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
            .onReceive(NotificationCenter.default.publisher(for: .bookMemoryPressure)) { _ in
                AppMemoryLedger.record("memory-warning")
                #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLX) && !targetEnvironment(simulator)
                Task { await LocalBrainModelCache.shared.unload() }
                #endif
            }
            .onChange(of: didHydrateLaunchState) { _, _ in
                rebuildSurfaceCache()
            }
            .onChange(of: surfaceRefreshDate) { _, _ in
                rebuildSurfaceCache()
            }
            .onChange(of: isTodaysMarginsExpanded) { _, expanded in
                if expanded { tutorTouch("todays-margins") }
            }
            .onChange(of: isReturnedStacksExpanded) { _, expanded in
                if expanded { tutorTouch("returned-stacks") }
            }
            .onChange(of: isQuietMechanicsExpanded) { _, expanded in
                if expanded { tutorTouch("colophon") }
            }
            .sheet(item: $selectedSurface) { surface in
                CapturePageSheet(
                    surface: surface,
                    day: today,
                    isLocalBrainWorking: localBrainTelemetry.isWorking,
                    onReplaceIlluminatedSurface: { replacement in
                        generation.automaticIlluminatedSurface = replacement
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
                    },
                    onGenerateLetter: { draft in
                        Task { await generateLetterFromSheet(draft) }
                    },
                    onGeneratePlayfulMission: { draft in
                        Task { await generatePlayfulMissionFromSheet(draft) }
                    },
                    onAnchorPlace: { draft in
                        Task { await anchorPlace(from: draft) }
                    },
                    onBindChapter: { chapterID in
                        bindChapter(id: chapterID)
                    },
                    activeElectives: electives.filter(\.isActive),
                    onCompleteElective: { electiveID, proof in
                        completeElective(id: electiveID, proof: proof)
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
            .fileImporter(
                isPresented: $isSaveImporterPresented,
                allowedContentTypes: [.json],
                allowsMultipleSelection: false
            ) { result in
                if case let .success(urls) = result, let url = urls.first {
                    importSaveFile(from: url)
                }
            }
            .sheet(isPresented: $isBookShopPresented) {
                BookShopSheet { packID in
                    unlockPack(packID)
                }
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $isStacksSearchPresented) {
                SearchTheStacksSheet(
                    dataset: stacksSearchDataset,
                    isLocalBrainWorking: localBrainTelemetry.isWorking,
                    onOpen: { result in
                        isStacksSearchPresented = false
                        openSearchResult(result)
                    }
                )
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $isCustomCastSheetPresented) {
                CustomCastMemberSheet { draft in
                    saveCustomCastMember(draft)
                }
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        BookFeedback.play(.openPage)
                        tutorTouch("search-stacks")
                        isStacksSearchPresented = true
                    } label: {
                        Image(systemName: "sparkle.magnifyingglass")
                            .font(.subheadline.weight(.bold))
                            .foregroundStyle(BookPalette.lampGold)
                    }
                    .accessibilityLabel("Search the Stacks")
                }
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
    struct LaunchHydrationPayload: @unchecked Sendable {
        var days: [BookDay]
        var storeReport: BookStore.Report
        var databaseReport: BookDatabase.Report
        var resurfacedPages: [BookPage]
        var selfFacts: [SelfFact]
        var narrativeEvents: [NarrativeEvent]
        var entityMemories: [NarrativeEntityMemory]
        var customCastMembers: [CustomCastMember]
        var facultyEntries: [FacultyEntry]
        var modelReport: LocalModelReport
    }

    func hydrateLaunchStateIfNeeded() async {
        guard !didHydrateLaunchState else { return }

        // The archive loads run off the main actor so the opening animation
        // never stutters; nothing else reads the database until hydration
        // completes (post-launch tasks wait on didHydrateLaunchState).
        let payload = await Task.detached(priority: .userInitiated) { () -> LaunchHydrationPayload in
            let initialDays = BookDatabase.loadDays(migratingFrom: BookStore.loadDays())
            return LaunchHydrationPayload(
                days: initialDays,
                storeReport: BookStore.report(for: initialDays),
                databaseReport: BookDatabase.report(for: initialDays),
                resurfacedPages: (try? BookDatabase.resurfacingCandidates(limit: 3)) ?? [],
                selfFacts: (try? BookDatabase.selfFacts()) ?? [],
                narrativeEvents: (try? BookDatabase.narrativeEvents(limit: 160)) ?? [],
                entityMemories: NarrativeEntityMemoryConsolidator.consolidate((try? BookDatabase.entityMemories(limit: 240)) ?? []),
                customCastMembers: (try? BookDatabase.customCastMembers(limit: 200)) ?? [],
                facultyEntries: (try? BookDatabase.facultyEntries(limit: 160)) ?? [],
                modelReport: LocalModelManager.report()
            )
        }.value

        guard !didHydrateLaunchState else { return }
        surfaceRefreshDate = Date()
        days = payload.days
        storeReport = payload.storeReport
        databaseReport = payload.databaseReport
        resurfacedPages = payload.resurfacedPages
        selfFacts = payload.selfFacts
        PersonalNameGuard.update(from: payload.selfFacts)
        narrativeEvents = payload.narrativeEvents
        entityMemories = payload.entityMemories
        customCastMembers = payload.customCastMembers
        facultyEntries = payload.facultyEntries
        modelReport = payload.modelReport
        didHydrateLaunchState = true
    }

    @MainActor
    func waitForLaunchStateHydration() async {
        while !didHydrateLaunchState && !Task.isCancelled {
            try? await Task.sleep(for: .milliseconds(100))
        }
    }

    @MainActor
    func runPostLaunchTasksIfNeeded() async {
        guard !didRunPostLaunchTasks else { return }
        await waitForLaunchStateHydration()
        guard !Task.isCancelled, !didRunPostLaunchTasks else { return }

        didRunPostLaunchTasks = true
        AppMemoryLedger.record("app-launch-idle")
        if generation.preparedStoryPageSurface == nil,
           let overnight = OvernightScribe.adoptDraft() {
            generation.preparedStoryPageSurface = overnight
            surfaceRefreshDate = Date()
            statusMessage = "The Book wrote a Story Page while you slept."
        }
        loadAnchorLedger()
        if didCompleteStoryOnboarding {
            BookWhispers.refreshSchedule(enabled: bookWhispersEnabled, electives: electives)
        }
        if bookCalendarEnabled {
            calendarEvents = await CalendarDoorway.upcomingEvents()
            surfaceRefreshDate = Date()
        }
        PackEntitlements.ownedPackIDs = Set(vault.data.ownedPacks ?? [])
        tendArc()
        nearbyPlaces = LocalPlacesScout.cachedPlaces()
        if didRequestAnchorLocation || didRequestWeatherLocation {
            let scouted = await LocalPlacesScout.refreshIfNeeded()
            if scouted.count != nearbyPlaces.count {
                nearbyPlaces = scouted
            } else {
                nearbyPlaces = scouted
            }
        }
        await refreshAnchorProximity(isUserInitiated: false)
        await runLaunchSmokeTestIfRequested()
    }

    @MainActor
    func rebuildSurfaceCache() {
        guard didHydrateLaunchState else {
            surfacedPages = []
            return
        }
        surfacedPages = buildCuratorSurfaces(now: surfaceRefreshDate)
        recordServedSurfaces(surfacedPages)
    }

    /// The curator remembers what it put on the desk, so it stops repeating
    /// itself. Only newly-shown content keys are written (30-minute grace).
    func recordServedSurfaces(_ pages: [SurfacePage], now: Date = Date()) {
        let history = vault.data.surfaceHistory ?? [:]
        let newKeys = pages.map(\.varietyKey).filter { key in
            guard let record = history[key] else { return true }
            return now.timeIntervalSince(record.lastShownAt) > 30 * 60
        }
        guard !newKeys.isEmpty else { return }
        vault.data.surfaceHistory = CuratorVarietyGovernor.recordingServed(keys: newKeys, into: history, now: now)
        vault.save()
    }

    func toggleGlowMenu() {
        BookFeedback.play(isGlowMenuPresented ? .dismissPage : .sourceRefresh)
        withAnimation(.spring(response: 0.48, dampingFraction: 0.78)) {
            isGlowMenuPresented.toggle()
        }
        if isGlowMenuPresented {
            tutorTouch("glow-menu")
        }
    }

    /// First-touch margin notes: the exploratory tutorial that follows the
    /// story onboarding. Each explainable thing speaks up exactly once.
    func tutorTouch(_ id: String) {
        guard didCompleteStoryOnboarding else { return }
        var seen = MarginTutorLedger.seenIDs(from: marginTutorSeenData)
        guard !seen.contains(id), let note = MarginTutorCatalog.note(for: id) else { return }
        seen.insert(id)
        marginTutorSeenData = MarginTutorLedger.encode(seen)
        withAnimation(.spring(response: 0.45, dampingFraction: 0.8)) {
            activeTutorNote = note
        }
    }

    func closeGlowMenu() {
        BookFeedback.play(.dismissPage)
        withAnimation(.spring(response: 0.38, dampingFraction: 0.86)) {
            isGlowMenuPresented = false
        }
    }

    func handleGlowMenuAction(_ action: GlowMenuAction) {
        switch action {
        case let .giveBelief(entity):
            giveBelief(to: entity)
        case let .takeBelief(entity):
            takeBelief(from: entity)
        case let .givePageBelief(page):
            givePageBelief(to: page)
        case let .takePageBelief(page):
            takePageBelief(from: page)
        case .spellCompass:
            selectedSurface = compassRunSurface()
            closeGlowMenu()
        case let .openEnchantment(enchantment):
            selectedSurface = enchantmentSurface(enchantment)
            closeGlowMenu()
        case let .openPage(type):
            Task { await openManualPage(type) }
            closeGlowMenu()
        case .openBookShop:
            isBookShopPresented = true
            closeGlowMenu()
        case let .openBookSection(sectionID):
            selectedSurface = readingSurface(forWonderCompassSectionID: sectionID)
            closeGlowMenu()
        }
    }

    func glowLine(for entity: NarrativeWorldEntity) -> String {
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

    func compactCastDescriptor(for id: String) -> String? {
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

    func compactGlowLine(_ source: String) -> String {
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

    func giveBelief(to entity: GlowEntityMenuItem) {
        let spend = min(3, beliefScore)
        guard spend > 0 else {
            statusMessage = "Your own Glow is too dim to give right now. Keep a page or answer the Book to rekindle it."
            return
        }
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = max(0, beliefScore - spend)
        }
        adjustEntityBelief(entity, delta: spend, kind: .beliefInvested, playerBeliefDelta: -spend)
        statusMessage = spend == 3
            ? "\(entity.name) takes on three brighter points of Glow, passed from your own."
            : "\(entity.name) takes the last \(spend) point\(spend == 1 ? "" : "s") of Glow you could spare."
    }

    func givePageBelief(to page: GlowPageMenuItem) {
        let spend = min(3, beliefScore)
        guard spend > 0 else {
            statusMessage = "Your own Glow is too dim to give right now. Keep a page or answer the Book to rekindle it."
            return
        }
        let applied = adjustPageBelief(page, delta: spend)
        guard applied > 0 else {
            statusMessage = "\(page.title) already glows as bright as it can."
            return
        }
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = max(0, beliefScore - applied)
        }
        statusMessage = "\(page.title) takes on \(applied) brighter point\(applied == 1 ? "" : "s") of Glow, passed from your own."
    }

    func takePageBelief(from page: GlowPageMenuItem) {
        let applied = adjustPageBelief(page, delta: -3)
        guard applied < 0 else {
            statusMessage = "\(page.title) has no Glow left to take."
            return
        }
        let gained = -applied
        withAnimation(.spring(response: 0.45, dampingFraction: 0.72)) {
            beliefScore = min(100, beliefScore + gained)
        }
        statusMessage = "You draw \(gained) point\(gained == 1 ? "" : "s") of Glow back from \(page.title). The Book will still remember it can surface."
    }

    func takeBelief(from entity: GlowEntityMenuItem) {
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

    func adjustEntityBelief(
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

    func saveCustomCastMember(_ draft: CustomCastMemberDraft) {
        let now = Date()
        let id = "user-cast-\(slug(for: draft.name))-\(UUID().uuidString.prefix(8))"
        let imageAsset = saveCustomCastImage(data: draft.imageData, entityID: id, name: draft.name)
        let inferredTags = Array(Set(
            draft.tags +
            draft.traits.map { $0.lowercased() } +
            [draft.kind.rawValue, "custom-cast", "belief"]
        )).sorted()
        let member = CustomCastMember(
            id: id,
            name: draft.name,
            kind: draft.kind,
            meaning: draft.meaning,
            description: draft.description,
            traits: draft.traits,
            beliefs: draft.beliefs,
            goals: draft.goals,
            tags: inferredTags,
            baseBelief: 25,
            narrativeWeight: 22,
            createdAt: now,
            updatedAt: now,
            imageAsset: imageAsset
        )

        do {
            try BookDatabase.upsertCustomCastMember(member)
            customCastMembers = try BookDatabase.customCastMembers(limit: 200)
            let menuItem = GlowEntityMenuItem(
                id: member.id,
                name: member.name,
                kind: member.kind.rawValue,
                glow: member.baseBelief,
                line: member.meaning
            )
            adjustEntityBelief(menuItem, delta: 3, kind: .beliefInvested)
            statusMessage = "\(member.name) has entered the Cast."
            surfaceRefreshDate = Date()
            rebuildSurfaceCache()
            closeGlowMenu()
        } catch {
            statusMessage = "The new Cast Member would not settle yet: \(error.localizedDescription)"
        }
    }

    func saveCustomCastImage(data: Data?, entityID: String, name: String) -> BookPageMediaAsset? {
        guard let data else { return nil }
        do {
            let baseURL = InsideCoverStore.containerURL
                ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            let directory = baseURL.appendingPathComponent("CustomCastImages", isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let url = directory.appendingPathComponent("\(entityID).jpg")
            try data.write(to: url, options: [.atomic])
            return BookPageMediaAsset(
                kind: .renderedImageFile,
                reference: url.path,
                caption: name,
                sourceID: BookPageSourceRegistry.source(for: .castMember).id,
                metadata: ["entityID": entityID]
            )
        } catch {
            statusMessage = "The Cast Member was named, but the photo slipped: \(error.localizedDescription)"
            return nil
        }
    }

    func slug(for value: String) -> String {
        let words = value
            .lowercased()
            .split { !$0.isLetter && !$0.isNumber }
            .map(String.init)
        let slug = words.prefix(5).joined(separator: "-")
        return slug.isEmpty ? "entry" : slug
    }

    func recordGlowBeliefEvent(
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
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 160)
        } catch {
            statusMessage = "The Glow moved, but the hidden ledger missed a line: \(error.localizedDescription)"
        }
    }

    @discardableResult
    func adjustPageBelief(_ page: GlowPageMenuItem, delta: Int) -> Int {
        var ledger = pageBeliefLedger
        let source = BookPageSourceRegistry.source(id: page.sourceID, fallbackType: page.type)
        let defaultBelief = BookPageSourceRegistry.defaultBelief(for: source)
        let currentDelta = ledger[page.sourceID] ?? 0
        let currentBelief = max(0, min(100, defaultBelief + currentDelta))
        let nextBelief = max(0, min(100, currentBelief + delta))
        let applied = nextBelief - currentBelief
        ledger[page.sourceID] = nextBelief - defaultBelief
        if ledger[page.sourceID] == 0 {
            ledger[page.sourceID] = nil
        }
        if let data = try? JSONEncoder().encode(ledger),
           let encoded = String(data: data, encoding: .utf8) {
            pageBeliefLedgerData = encoded
        }
        recordGlowPageBeliefEvent(page: page, delta: applied, playerBeliefDelta: -applied)
        surfaceRefreshDate = Date()
        rebuildSurfaceCache()
        return applied
    }

    func recordGlowPageBeliefEvent(page: GlowPageMenuItem, delta: Int, playerBeliefDelta: Int = 0) {
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
            effect: NarrativeEventEffect(beliefDelta: playerBeliefDelta)
        )
        do {
            try BookDatabase.upsertNarrativeEvent(event)
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 160)
        } catch {
            statusMessage = "The Page Glow moved, but the hidden ledger missed a line: \(error.localizedDescription)"
        }
    }

    func compassRunSurface() -> SurfacePage {
        BookPageSourceAdapters.manualSurface(
            for: .wonderCompass,
            day: today,
            context: CuratorContext.make(for: today),
            inputs: sourceInputs,
            now: Date()
        )
    }

    func enchantmentSurface(_ enchantment: GlowEnchantmentMenuItem) -> SurfacePage {
        SurfacePage(
            id: "manual-enchantment-\(enchantment.id)-\(today.id)-\(Int(Date().timeIntervalSince1970))",
            type: .enchantment,
            sourceID: BookPageSourceRegistry.source(for: .enchantment).id,
            intent: .capture,
            renderStyle: .promptCard,
            score: 64,
            reason: "An Enchantment needs a chosen photo before the Book counts it.",
            prompt: enchantment.title,
            detail: enchantment.detail,
            payload: BookPagePayload(
                headline: "Enchantment Page: \(enchantment.title)",
                body: "\(enchantment.detail)\n\nChoose a photo. The spell will illuminate the real subject and write the result into the margins.",
                metadata: [
                    "source": "enchantment",
                    "enchantmentID": enchantment.id,
                    "enchantmentName": enchantment.title,
                    "placeholder": "Choose a photo to cast \(enchantment.title).",
                    "tags": "enchantment,proof,real-world-magic,\(enchantment.id)"
                ]
            )
        )
    }

    func surface(forManualPageType type: BookPageType) -> SurfacePage {
        return freshManualSurface(for: type)
    }

    func freshManualSurface(for type: BookPageType) -> SurfacePage {
        BookPageSourceAdapters.manualSurface(
            for: type,
            day: today,
            context: CuratorContext.make(for: today),
            inputs: sourceInputs,
            now: Date()
        )
    }

    @MainActor
    func openManualPage(_ type: BookPageType) async {
        switch type {
        case .narrativeOS:
            if generation.preparedStoryPageSurface == nil {
                statusMessage = "The Story Page is calling the local Book brain..."
                _ = await prepareStoryPageIfPossible(force: true)
            }
            selectedSurface = generation.preparedStoryPageSurface ?? localBrainIssueSurface(
                type: type,
                title: "Story Page",
                action: "write a Story Page"
            )
        case .gossip:
            if generation.preparedGossipPageSurface == nil {
                statusMessage = "The Gossip Page is waking the whisper engine..."
                _ = await prepareGossipPageIfPossible(force: true)
            }
            selectedSurface = generation.preparedGossipPageSurface ?? localBrainIssueSurface(
                type: type,
                title: "Gossip Page",
                action: "write a Gossip Page"
            )
        case .facultyResearch:
            if generation.preparedFacultyResearchSurface == nil {
                statusMessage = "The faculty folio is asking Gemma to read the clippings..."
                _ = await prepareFacultyResearchPageIfPossible(force: true)
            }
            selectedSurface = generation.preparedFacultyResearchSurface ?? localBrainIssueSurface(
                type: type,
                title: "Faculty Research",
                action: "write a Faculty Research Page"
            )
        case .letter:
            selectedSurface = freshManualSurface(for: .letter)
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

    func localBrainIssueSurface(type: BookPageType, title: String, action: String) -> SurfacePage {
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

    func readingSurface(forWonderCompassSectionID sectionID: String) -> SurfacePage {
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

    func openKeptPage(_ page: BookPage) {
        BookFeedback.play(.openPage)
        selectedSurface = keptSurface(for: page)
    }

    func keptSurface(for page: BookPage) -> SurfacePage {
        let text = page.userInput.trimmingCharacters(in: .whitespacesAndNewlines)
        let body = text.isEmpty ? page.promptText : text
        let source = BookPageSourceRegistry.source(id: page.sourceID, fallbackType: page.type)
        let title = page.type == .bookOfYou ? "Book of You" : page.type.title
        let prompt = page.promptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? title
            : page.promptText

        var metadata = [
            "source": source.id,
            "keptPageID": page.id,
            "keptPage": "true",
            "tags": page.tags.joined(separator: ",")
        ]
        metadata.merge(keptPageMediaMetadata(for: page), uniquingKeysWith: { current, _ in current })

        return SurfacePage(
            id: "kept-\(page.id)",
            type: page.type,
            sourceID: source.id,
            intent: .importReference,
            renderStyle: .quoteCard,
            score: 80,
            reason: "This Page is already kept in the Book.",
            prompt: prompt,
            detail: "Kept \(page.createdAt.formatted(date: .abbreviated, time: .omitted))",
            payload: BookPagePayload(
                headline: title,
                body: body,
                metadata: metadata
            )
        )
    }

    func keptPageMediaMetadata(for page: BookPage) -> [String: String] {
        var metadata: [String: String] = [:]
        for asset in page.mediaAssets {
            switch asset.kind {
            case .bundledImage:
                metadata["assetName"] = asset.reference
                metadata["imageAssetKind"] = asset.kind.rawValue
                metadata["imageAssetReference"] = asset.reference
            case .renderedImageFile:
                metadata["renderedPreviewPath"] = asset.reference
                metadata["proofImagePath"] = asset.reference
                metadata["proofCaption"] = asset.caption
            case .photoLibraryAsset:
                metadata["assetLocalIdentifier"] = asset.reference
            }
            if !asset.caption.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                metadata["imageCaption"] = asset.caption
            }
        }
        return metadata
    }

    func resetTransientWorkStateForBackgrounding() {
        localBrainTelemetry.resetTransientWork()
        generation.isBraiding = false
        generation.braidingStartedAt = nil
        generation.isPreparingStoryPage = false
        generation.isPreparingGossipPage = false
        generation.isPreparingFacultyResearchPage = false
        generation.isPreparingLetterPage = false
        generation.isPreparingAutomaticIllumination = false
    }

    @ViewBuilder
    var localBrainWorkShelf: some View {
        if localBrainTelemetry.isWorking {
            LocalBrainWorkingStatusCard(
                label: localBrainTelemetry.currentLabel,
                quip: LocalBrainQuips.lines[localBrainQuipIndex],
                startedAt: localBrainTelemetry.startedAt,
                queuedCount: localBrainTelemetry.currentQueuedCount
            )
            .transition(.opacity.combined(with: .move(edge: .top)))
        } else if generation.isBraiding {
            BraidingStatusCard(
                quip: BraidingQuips.lines[braidingQuipIndex],
                startedAt: generation.braidingStartedAt
            )
            .transition(.opacity.combined(with: .move(edge: .top)))
        }
    }

    static let bannerEpigraphs: [String] = [
        "Every shelf remembers who lingered.",
        "What you notice, notices back.",
        "A kept sentence outlives its weather.",
        "Doors prefer to be asked.",
        "The Book turns when you do.",
        "Small true things are load-bearing.",
        "Ink dries; the day doesn't have to.",
        "The compass points at whatever you love.",
        "Somewhere in the Stacks, your page is already breathing.",
        "The margins are listening, kindly.",
        "Attention is the only ink the Book accepts.",
        "Wonder is a practice, not a weather."
    ]

    static let bannerCameos: [(asset: String, name: String)] = [
        ("LabyrinthCharacterPennyBlackletter", "Penny Blackletter"),
        ("LabyrinthCharacterZaraFinch", "Zara Finch"),
        ("LabyrinthCharacterDrSeleneInkrest", "Dr. Selene Inkrest"),
        ("LabyrinthCharacterHeadmistressSeraphinaThorne", "Headmistress Thorne"),
        ("LabyrinthCharacterOrionBlackthorn", "Orion Blackthorn"),
        ("LabyrinthCharacterSerenityBrown", "Serenity Brown")
    ]

    var bannerTimeWash: LinearGradient {
        let hour = Calendar.current.component(.hour, from: Date())
        let colors: [Color]
        switch hour {
        case 5..<9:
            colors = [Color(red: 0.96, green: 0.62, blue: 0.46).opacity(0.16), .clear]
        case 9..<17:
            colors = [.clear, .clear]
        case 17..<21:
            colors = [Color(red: 0.82, green: 0.46, blue: 0.30).opacity(0.20), Color(red: 0.30, green: 0.22, blue: 0.46).opacity(0.14)]
        default:
            colors = [Color(red: 0.12, green: 0.14, blue: 0.32).opacity(0.30), Color(red: 0.10, green: 0.10, blue: 0.24).opacity(0.16)]
        }
        return LinearGradient(colors: colors, startPoint: .top, endPoint: .bottom)
    }

    /// A fresh variation every app open: rotating epigraph, time-of-day
    /// light wash, tonight's actual moon stamped in the corner, and sometimes
    /// a cast member visiting the margin.
    var topBanner: some View {
        let epigraph = Self.bannerEpigraphs[bannerSeed % Self.bannerEpigraphs.count]
        let cameo = bannerSeed % 5 < 2
            ? Self.bannerCameos[bannerSeed % Self.bannerCameos.count]
            : nil
        let moon = MoonPhaseCalendar.phase()

        return Image("ReEnchantedTopBanner")
            .resizable()
            .scaledToFill()
            .frame(maxWidth: .infinity)
            .frame(height: 142)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                bannerTimeWash
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .allowsHitTesting(false)
            }
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(BookPalette.lampGold.opacity(0.28), lineWidth: 1)
            }
            .overlay(alignment: .bottom) {
                LinearGradient(
                    colors: [
                        .clear,
                        BookPalette.nightPanel.opacity(0.56)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .frame(height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .allowsHitTesting(false)
            }
            .overlay(alignment: .bottomLeading) {
                Text("“\(epigraph)”")
                    .font(.system(.caption, design: .serif).italic().weight(.semibold))
                    .foregroundStyle(.white.opacity(0.92))
                    .shadow(color: .black.opacity(0.7), radius: 3, x: 0, y: 1)
                    .lineLimit(2)
                    .padding(.horizontal, 12)
                    .padding(.bottom, 10)
                    .padding(.trailing, cameo == nil ? 12 : 64)
            }
            .overlay(alignment: .topTrailing) {
                VStack(spacing: 6) {
                    Image(systemName: moon.symbolName)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(BookPalette.lampGold.opacity(0.85))
                        .shadow(color: .black.opacity(0.6), radius: 2)
                        .accessibilityLabel(moon.name)
                    if let ascendant = ascendantTalisman,
                       let chapter = AcademyChapterRegistry.chapter(forTalismanID: ascendant.id) {
                        Image(systemName: chapter.symbolName)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(BookPalette.teal.opacity(0.9))
                            .shadow(color: .black.opacity(0.6), radius: 2)
                            .accessibilityLabel("\(ascendant.name) is ascendant")
                    }
                }
                .padding(10)
            }
            .overlay(alignment: .bottomTrailing) {
                if let cameo {
                    Image(cameo.asset)
                        .resizable()
                        .scaledToFill()
                        .frame(width: 46, height: 46)
                        .clipShape(Circle())
                        .overlay {
                            Circle()
                                .stroke(BookPalette.lampGold.opacity(0.8), lineWidth: 1.4)
                        }
                        .shadow(color: .black.opacity(0.5), radius: 4, x: 0, y: 2)
                        .padding(8)
                        .accessibilityLabel("\(cameo.name) is visiting the margin today")
                }
            }
            .overlay(alignment: .bottom) {
                if let bookKnockNote {
                    Text(bookKnockNote)
                        .font(.system(.caption, design: .serif).italic().weight(.semibold))
                        .foregroundStyle(BookPalette.lampGold)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 7)
                        .background(BookPalette.nightPanel.opacity(0.96), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 6, style: .continuous)
                                .stroke(BookPalette.lampGold.opacity(0.5), lineWidth: 1)
                        }
                        .padding(.bottom, -16)
                        .transition(.move(edge: .top).combined(with: .opacity))
                        .zIndex(-1)
                        .accessibilityLabel("A note from inside the Book: \(bookKnockNote)")
                }
            }
            .rotationEffect(.degrees(bannerShudder ? 0.7 : 0))
            .contentShape(Rectangle())
            .onTapGesture {
                knockOnTheCover()
            }
            .shadow(color: .black.opacity(0.3), radius: 18, x: 0, y: 12)
            .accessibilityLabel("An open enchanted book surrounded by field notes, ink, compass art, and marginalia. \(epigraph)")
            .accessibilityHint("The cover can be knocked on.")
    }

    var hero: some View {
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
                BookOfYouCard(page: bookPage) {
                    openKeptPage(bookPage)
                }
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

    var surfaceShelf: some View {
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
                        removal: .move(edge: .leading).combined(with: .opacity)
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

    var statusActionTitle: String? {
        if undoRemovedPage != nil {
            return "Put it back"
        }
        if undoSurface != nil {
            return "Call it back"
        }
        return generation.braidRecovery.retryActionTitle
    }

    var statusAction: (() -> Void)? {
        if undoRemovedPage != nil {
            return { restoreLastRemovedPage() }
        }
        if undoSurface != nil {
            return { undoLastSurfaceDismissal() }
        }
        if generation.braidRecovery.canRetry {
            return {
                Task { await braidToday() }
            }
        }
        return nil
    }

    func foldedShelf<Content: View>(
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


    var labPanelShelf: some View {
        let eligibleBraidCount = today.capturedPages.filter { !$0.usedInBookOfYou }.count
        let queuedGeneratedPages = [
            generation.preparedStoryPageSurface,
            generation.preparedGossipPageSurface,
            generation.preparedFacultyResearchSurface,
            generation.preparedLetterSurface,
            generation.automaticIlluminatedSurface
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
                diagnosticRow("last braid", generation.lastBraidDuration.map { "\(Int($0.rounded()))s" } ?? "none")

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

    var labWorkStatus: String {
        workBlockingState.labWorkStatus
    }

    var labLastBrainStatus: String {
        localBrainTelemetry.lastWorkStatus { Self.labTimestampFormatter.string(from: $0) }
    }

    static let labTimestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter
    }()

    func diagnosticRow(_ label: String, _ value: String, isWarning: Bool = false) -> some View {
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

    var todayFragments: some View {
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
                            openKeptPage(page)
                        } onRemove: {
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

    var resurfacedShelf: some View {
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
                        ResurfacedPageRow(page: page) {
                            openKeptPage(page)
                        }
                    }
                }
            }
        }
    }

    var archiveShelf: some View {
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
                            ArchiveCard(page: page) {
                                openKeptPage(page)
                            }
                        }
                    }
                    .padding(.bottom, 2)
                }
            }
        }
    }

    var sourceControlsShelf: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button {
                BookFeedback.play(.tap)
                withAnimation(.spring(response: 0.42, dampingFraction: 0.86)) {
                    isQuietMechanicsExpanded.toggle()
                }
            } label: {
                HStack(spacing: 10) {
                    Text("Colophon")
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
            .accessibilityLabel(isQuietMechanicsExpanded ? "Hide Colophon" : "Show Colophon")

            if isQuietMechanicsExpanded {
                VStack(alignment: .leading, spacing: 12) {
                    LabStatusCard(
                        report: modelReport,
                        storeReport: storeReport,
                        databaseReport: databaseReport,
                        lastBraidDuration: generation.lastBraidDuration
                    )

                    HStack {
                        Text("Doorway settings live here now.")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(BookPalette.nightText.opacity(0.62))
                        Spacer()
                        Button {
                            BookFeedback.play(.openPage)
                            isSourceSettingsPresented = true
                        } label: {
                            Label("Doorways", systemImage: "slider.horizontal.3")
                                .font(.caption.weight(.bold))
                        }
                        .buttonStyle(.bordered)
                        .tint(BookPalette.teal)
                        .accessibilityLabel("Page source settings")

                        Button {
                            BookFeedback.play(.sourceRefresh)
                            marginTutorSeenData = "[]"
                            statusMessage = "Zara re-tucked her margin notes. She will reintroduce things as you touch them."
                        } label: {
                            Label("Re-tuck notes", systemImage: "arrow.counterclockwise")
                                .font(.caption.weight(.bold))
                        }
                        .buttonStyle(.bordered)
                        .tint(BookPalette.lampGold)
                        .accessibilityLabel("Reset first-touch margin notes")
                    }

                    Toggle(isOn: $bookWhispersEnabled) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Whispers from the Book")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(BookPalette.nightText.opacity(0.86))
                            Text("Class bells, the evening braid, and aging favors — as gentle notifications.")
                                .font(.caption2)
                                .foregroundStyle(BookPalette.nightText.opacity(0.58))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .tint(BookPalette.teal)
                    .onChange(of: bookWhispersEnabled) { _, enabled in
                        BookFeedback.play(enabled ? .sourceRefresh : .dismissPage)
                        BookWhispers.refreshSchedule(enabled: enabled, electives: electives)
                        statusMessage = enabled
                            ? "The Book may whisper now: bells, the evening braid, and waiting favors."
                            : "The Book will keep its voice inside the covers."
                    }

                    Toggle(isOn: $bookCalendarEnabled) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Calendar Doorway")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(BookPalette.nightText.opacity(0.86))
                            Text("The Book reads the day's hinges and folds a corner before each one. Events stay on this phone.")
                                .font(.caption2)
                                .foregroundStyle(BookPalette.nightText.opacity(0.58))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .tint(BookPalette.teal)
                    .onChange(of: bookCalendarEnabled) { _, enabled in
                        BookFeedback.play(enabled ? .sourceRefresh : .dismissPage)
                        if enabled {
                            Task {
                                calendarEvents = await CalendarDoorway.upcomingEvents()
                                surfaceRefreshDate = Date()
                                statusMessage = calendarEvents.isEmpty
                                    ? "The Calendar Doorway is open, but no hinges are inked yet."
                                    : "The Book can see \(calendarEvents.count) inked hour\(calendarEvents.count == 1 ? "" : "s") ahead."
                            }
                        } else {
                            calendarEvents = []
                            surfaceRefreshDate = Date()
                            statusMessage = "The Calendar Doorway is closed."
                        }
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Vellum's ledger key (USDA FoodData)")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(BookPalette.nightText.opacity(0.86))
                        TextField("DEMO_KEY (limited) — paste a free key from fdc.nal.usda.gov", text: $usdaKey)
                            .font(.caption)
                            .textFieldStyle(.roundedBorder)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                        Text("Fuel pages get rough calorie and macro estimates, penciled in moments after you keep them. Entries never leave the device except as anonymous food-name lookups.")
                            .font(.caption2)
                            .foregroundStyle(BookPalette.nightText.opacity(0.55))
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    HStack(spacing: 10) {
                        Text("Your save is yours.")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(BookPalette.nightText.opacity(0.62))
                        Spacer()
                        if let preparedSaveFileURL {
                            ShareLink(item: preparedSaveFileURL) {
                                Label("Share save", systemImage: "square.and.arrow.up")
                                    .font(.caption.weight(.bold))
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(BookPalette.teal)
                        } else {
                            Button {
                                BookFeedback.play(.sourceRefresh)
                                exportSaveFile()
                            } label: {
                                Label("Export save", systemImage: "book.closed")
                                    .font(.caption.weight(.bold))
                            }
                            .buttonStyle(.bordered)
                            .tint(BookPalette.teal)
                        }
                        Button {
                            BookFeedback.play(.openPage)
                            isSaveImporterPresented = true
                        } label: {
                            Label("Import", systemImage: "square.and.arrow.down")
                                .font(.caption.weight(.bold))
                        }
                        .buttonStyle(.bordered)
                        .tint(BookPalette.lampGold)
                    }

                    labPanelShelf

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

                    AnchorSourceCard(
                        proximity: nearbyAnchor,
                        message: anchorMessage,
                        isChecking: isCheckingAnchors,
                        hasRequested: didRequestAnchorLocation,
                        isAvailable: AnchorLocationReader.isAvailable
                    ) {
                        BookFeedback.play(.sourceRefresh)
                        Task { await refreshAnchorProximity(isUserInitiated: true) }
                    }

                    StoryFieldStatusCard(
                        surface: generation.preparedStoryPageSurface,
                        events: narrativeEvents,
                        isPreparing: generation.isPreparingStoryPage
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

    func savePage(surface: SurfacePage, input: String, tags: [String]) {
        BookFeedback.play(.keepPage)
        tutorTouch("keep-page")
        let greyBeforeKeeping = NothingTide.greyLevel(
            quietDays: NothingTide.quietDays(in: days, today: today.id),
            narrativeHeat: narrativeEvents.prefix(24).count,
            distressActive: false
        )
        var day = today
        if surface.type == .illuminatedPhoto {
            markAutomaticIlluminatedSurfaceKept(surface)
        }
        if surface.type == .anchor {
            checkInAnchorIfNeeded(surface)
        }
        acceptElectiveIfNeeded(surface: surface)
        clearPreparedSurfaceIfNeeded(surface)
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
        applyGeneratedChapterTalismanDeltas(from: surface)
        let keptMessage: String
        if today.capturedPages.isEmpty, let returnLine = NothingTide.returnLine(forGreyLevel: greyBeforeKeeping) {
            keptMessage = returnLine
        } else {
            keptMessage = "The Book tucked the \(surface.type.shortTitle.lowercased()) page into the margin."
        }
        persist(day: day, message: keptMessage)
        retireKeptSurfaceFromRising(surface)
    }

    func applyGeneratedChapterTalismanDeltas(from surface: SurfacePage) {
        guard [.gossip, .narrativeOS, .letter].contains(surface.type),
              let raw = surface.payload.metadata["chapterTalismanDeltas"]?.nonEmpty else { return }
        let deltas = raw
            .split(separator: ",")
            .compactMap { token -> (String, Int)? in
                let parts = token.split(separator: ":", maxSplits: 1).map(String.init)
                guard parts.count == 2, let delta = Int(parts[1]), delta != 0 else { return nil }
                return (parts[0], delta)
            }
        guard !deltas.isEmpty else { return }

        for (talismanID, delta) in deltas {
            guard let chapter = AcademyChapterRegistry.chapter(forTalismanID: talismanID) else { continue }
            let talisman = GlowEntityMenuItem(
                id: chapter.talismanID,
                name: chapter.talismanName,
                kind: "talisman",
                glow: 0,
                line: chapter.philosophy
            )
            adjustEntityBelief(
                talisman,
                delta: delta,
                kind: delta > 0 ? .beliefInvested : .beliefAttacked
            )
        }
    }

    func recordNarrativeEvent(for page: BookPage) {
        do {
            let events = NarrativeEventResolver.events(forKept: page)
            for event in events {
                try BookDatabase.upsertNarrativeEvent(event)
                for memory in NarrativeEntityMemoryResolver.memories(for: event) {
                    try BookDatabase.upsertEntityMemory(memory)
                }
            }
            narrativeEvents = try BookDatabase.narrativeEvents(limit: 160)
            entityMemories = NarrativeEntityMemoryConsolidator.consolidate(try BookDatabase.entityMemories(limit: 240))
        } catch {
            statusMessage = "The page is kept, but one hidden margin note slipped: \(error.localizedDescription)"
        }
        tendArc()
    }

    /// The ArcKeeper checks the field whenever events land: promotion,
    /// phase turns, and completion all announce themselves in-world.
    @MainActor
    func tendArc(now: Date = Date()) {
        let (arc, announcement) = ArcKeeper.evaluate(
            current: vault.data.currentArc,
            events: narrativeEvents,
            lastCompletedThreadID: vault.data.lastCompletedArcThreadID,
            now: now
        )
        let completed = vault.data.currentArc != nil && arc == nil
        if completed {
            vault.data.lastCompletedArcThreadID = vault.data.currentArc?.threadID
        }
        if arc != vault.data.currentArc {
            vault.data.currentArc = arc
            vault.save()
            surfaceRefreshDate = now
        }
        if let announcement {
            statusMessage = announcement
            BookFeedback.play(.sourceRefresh)
        }
    }

    func saveSelfFactIfNeeded(surface: SurfacePage, answer: String) {
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

    func saveFacultyEntryIfNeeded(
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

        if kind == .fuel {
            enrichFuelEntry(entry)
        }
    }

    func awardBelief(for surface: SurfacePage) {
        let delta: Int
        if surface.type == .wonderCompass, surface.payload.metadata["runID"] != nil {
            delta = surface.payload.metadata["compassStep"] == "rest" ? 6 : 0
        } else if surface.type == .enchantment || surface.payload.metadata["source"] == "enchantment" {
            delta = Int(surface.payload.metadata["enchantmentBeliefReward"] ?? "") ?? 3
        } else if surface.type == .anchor {
            delta = Int(surface.payload.metadata["beliefReward"] ?? "") ?? AnchorRegistry.checkInBeliefReward
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

    func completeCompassRunIfNeeded(_ surface: SurfacePage) {
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

    func openStoryMechanicReturnPage(from completedSurface: SurfacePage, outcome: String) {
        guard completedSurface.payload.metadata["storyMechanicReturn"] == "true" else { return }
        Task { await prepareAndOpenStoryMechanicReturnPage(from: completedSurface, outcome: outcome) }
    }

    @MainActor
    func prepareAndOpenStoryMechanicReturnPage(from completedSurface: SurfacePage, outcome: String) async {
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

    func storyMechanicReturnSurface(from completedSurface: SurfacePage, outcome: String) -> SurfacePage {
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
    func generateAndOpenSurface(_ surface: SurfacePage) async {
        guard scenePhase == .active else {
            statusMessage = "The Book can only write while ReEnchanted is open on screen."
            return
        }

        switch surface.type {
        case .narrativeOS:
            statusMessage = "The Story Page is calling the local Book brain..."
            _ = await prepareStoryPageIfPossible(force: true)
            selectedSurface = generation.preparedStoryPageSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Story Page",
                action: "write a Story Page"
            )
        case .gossip:
            statusMessage = "The Gossip Page is waking the whisper engine..."
            _ = await prepareGossipPageIfPossible(force: true)
            selectedSurface = generation.preparedGossipPageSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Gossip Page",
                action: "write a Gossip Page"
            )
        case .facultyResearch:
            statusMessage = "The faculty folio is asking Gemma to read the clippings..."
            _ = await prepareFacultyResearchPageIfPossible(force: true)
            selectedSurface = generation.preparedFacultyResearchSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Faculty Research",
                action: "write a Faculty Research Page"
            )
        case .letter:
            selectedSurface = surface
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
        case .supportGuild:
            statusMessage = "The Support Guild is convening over the charts..."
            selectedSurface = await supportGuildSurfaceWithProse(from: surface)
            statusMessage = ""
        case .academyClass:
            statusMessage = "The classroom door is opening..."
            selectedSurface = await academyClassSurfaceWithProse(from: surface)
            statusMessage = ""
        case .elective where surface.payload.metadata["electiveOffer"] == "true":
            statusMessage = "\(surface.payload.metadata["senderName"] ?? "Someone") is writing out the favor..."
            selectedSurface = await electiveOfferSurfaceWithAsk(from: surface)
            statusMessage = ""
        case .packPage where surface.payload.metadata["packPrompt"]?.isEmpty == false:
            statusMessage = "An installed page is asking the Book to write..."
            selectedSurface = await packPageSurfaceWithProse(from: surface)
            statusMessage = ""
        case .illuminatedPhoto:
            statusMessage = "Penny is asking Gemma to illuminate a photo."
            _ = await prepareAutomaticIlluminatedPageIfPossible()
            selectedSurface = generation.automaticIlluminatedSurface ?? localBrainIssueSurface(
                type: surface.type,
                title: "Illuminated Photo",
                action: "illuminate a photo"
            )
        default:
            selectedSurface = surface
        }
    }

    @MainActor
    func generateLetterFromSheet(_ draft: SurfacePage) async {
        statusMessage = "A Letter Page is opening through the public stacks..."
        _ = await prepareLetterPageIfPossible(force: true, draftOverride: draft)
        if let preparedLetterSurface = generation.preparedLetterSurface {
            selectedSurface = generation.preparedLetterSurface
        } else {
            selectedSurface = localBrainIssueSurface(
                type: .letter,
                title: "Letter Page",
                action: "open and read a researched Letter Page"
            )
        }
    }

    @MainActor
    func generatePlayfulMissionFromSheet(_ draft: SurfacePage) async {
        guard !localBrainTelemetry.isWorking else {
            statusMessage = "The Book is already writing. One moment, please."
            return
        }
        statusMessage = "Gemma is inventing a fresh South = Sense mission..."
        let mission = await PlayfulMissionWriter().mission(from: draft)
        selectedSurface = draft.withPlayfulMission(mission, slotID: SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 2))
        statusMessage = ""
    }

    @discardableResult
    func prepareAutomaticIlluminatedPageIfPossible() async -> Bool {
        #if canImport(Photos) && canImport(UIKit)
        guard generation.automaticIlluminatedSurface == nil,
              !generation.isPreparingAutomaticIllumination,
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

        generation.isPreparingAutomaticIllumination = true
        defer { generation.isPreparingAutomaticIllumination = false }

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
                seed: abs(candidate.assetLocalIdentifier.stableHash ^ today.id.stableHash ^ Int(Date().timeIntervalSinceReferenceDate * 1000)),
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
            generation.automaticIlluminatedSurface = surface
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

    func analyzeAutomaticIlluminatedPhoto(_ image: UIImage) async -> PhotoAnalysis {
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
    func prepareStoryPageIfPossible(force: Bool = false) async -> Bool {
        guard scenePhase == .active else {
            localBrainTelemetry.recordError("story page: Gemma can only write while ReEnchanted is open on screen.")
            return false
        }
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 4)
        if force {
            guard !generation.isPreparingStoryPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard generation.storyPageRecovery.shouldBegin(
                isPreparing: generation.isPreparingStoryPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: generation.preparedStoryPageSurface,
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

        generation.isPreparingStoryPage = true
        defer { generation.isPreparingStoryPage = false }

        do {
            let prose: StoryPageProse
            #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
            prose = try await MLXStoryPageWriter().write(surface: draft)
            #else
            prose = try await FakeStoryPageWriter().write(surface: draft)
            #endif
            generation.preparedStoryPageSurface = draft.preparedStoryPageCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            generation.storyPageRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "The Story Page has dried and is waiting for the curator."
            return true
        } catch {
            appLog.error("Prepared Story Page failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("story page: \(error.localizedDescription)")
            generation.preparedStoryPageSurface = nil
            generation.storyPageRecovery.recordFailure()
            statusMessage = "The Story Page did not finish drying. The Book will try again later."
            return false
        }
    }

    @MainActor
    @discardableResult
    func prepareGossipPageIfPossible(force: Bool = false) async -> Bool {
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 4)
        if force {
            guard !generation.isPreparingGossipPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard generation.gossipPageRecovery.shouldBegin(
                isPreparing: generation.isPreparingGossipPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: generation.preparedGossipPageSurface,
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

        generation.isPreparingGossipPage = true
        defer { generation.isPreparingGossipPage = false }

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
            generation.preparedGossipPageSurface = draft.preparedGossipPageCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            generation.gossipPageRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "A Gossip Page has dried. The margins are pretending they did not gossip."
            return true
        } catch {
            appLog.error("Prepared Gossip Page failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("gossip page: \(error.localizedDescription)")
            generation.preparedGossipPageSurface = nil
            generation.gossipPageRecovery.recordFailure()
            statusMessage = "The Gossip Page lost its whisper. The Book will try again later."
            return false
        }
    }

    @MainActor
    @discardableResult
    func prepareFacultyResearchPageIfPossible(force: Bool = false) async -> Bool {
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 12)
        if force {
            guard !generation.isPreparingFacultyResearchPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard generation.facultyResearchRecovery.shouldBegin(
                isPreparing: generation.isPreparingFacultyResearchPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: generation.preparedFacultyResearchSurface,
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

        generation.isPreparingFacultyResearchPage = true
        defer { generation.isPreparingFacultyResearchPage = false }

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
            generation.preparedFacultyResearchSurface = draft.preparedFacultyResearchCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            generation.facultyResearchRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "\(draft.payload.metadata["facultyName"] ?? "The Support Guild") prepared a research folio for tonight."
            return true
        } catch {
            appLog.error("Prepared faculty research failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("faculty research: \(error.localizedDescription)")
            generation.preparedFacultyResearchSurface = nil
            generation.facultyResearchRecovery.recordFailure()
            statusMessage = "The faculty research folio lost its place. The Book will try again later."
            return false
        }
    }

    func facultyResearchQueries(for surface: SurfacePage) -> [String] {
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

    @MainActor
    @discardableResult
    func prepareLetterPageIfPossible(force: Bool = false, draftOverride: SurfacePage? = nil) async -> Bool {
        let slot = SurfaceCadence.slotID(for: surfaceRefreshDate, hours: 12)
        if force {
            guard !generation.isPreparingLetterPage, !localBrainTelemetry.isWorking else {
                return false
            }
        } else {
            guard generation.letterPageRecovery.shouldBegin(
                isPreparing: generation.isPreparingLetterPage,
                isLocalBrainWorking: localBrainTelemetry.isWorking,
                preparedSurface: generation.preparedLetterSurface,
                slotID: slot,
                requiredMetadataKey: "letterProse",
                now: surfaceRefreshDate
            ) else {
                return false
            }
        }

        var draftInputs = sourceInputs
        draftInputs.preparedLetterSurface = nil
        guard var draft = draftOverride ?? CharacterLetterPageGenerator.draftCandidate(for: today, inputs: draftInputs, now: surfaceRefreshDate),
              draft.type == .letter,
              isSourceEnabled(sourceID: draft.sourceID) else {
            return false
        }

        generation.isPreparingLetterPage = true
        defer { generation.isPreparingLetterPage = false }

        do {
            let clippings = await RealInterestGossipSearcher().clippings(
                for: letterResearchQueries(for: draft),
                limit: 4
            )
            draft = draft.withLetterResearchClippings(clippings)
            let prose = await CharacterLetterWriter().write(surface: draft)
            generation.preparedLetterSurface = draft.preparedLetterCopy(prose: prose, slotID: slot)
            surfaceRefreshDate = Date()
            generation.letterPageRecovery.recordSuccess()
            localBrainTelemetry.clearError()
            statusMessage = "\(draft.payload.metadata["senderName"] ?? "Someone") sent a letter through the margins."
            return true
        } catch {
            appLog.error("Prepared letter page failed: \(error.localizedDescription, privacy: .public)")
            localBrainTelemetry.recordError("letter page: \(error.localizedDescription)")
            generation.preparedLetterSurface = nil
            generation.letterPageRecovery.recordFailure()
            statusMessage = "The letter lost its address. The Book will try again later."
            return false
        }
    }

    func letterResearchQueries(for surface: SurfacePage) -> [String] {
        let query = surface.payload.metadata["researchQuery"]?.nonEmpty
        let interest = surface.payload.metadata["unwrittenInterest"]?.nonEmpty ?? "ordinary wonder"
        let home = surface.payload.metadata["homeContext"]?.nonEmpty ?? "local home"
        return [
            query,
            "\(interest) \(home)",
            "\(interest) local history ecology culture",
            "\(home) local history folklore nature"
        ].compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty }
    }

    func markAutomaticIlluminatedSurfaceKept(_ surface: SurfacePage) {
        guard let assetID = surface.payload.metadata["assetLocalIdentifier"] else {
            return
        }
        var history = decodedIlluminatedPhotoHistory()
        history.keptAssetIdentifiers.insert(assetID)
        illuminatedPhotoHistoryData = encodedIlluminatedPhotoHistory(history)
        if generation.automaticIlluminatedSurface?.id == surface.id {
            generation.automaticIlluminatedSurface = nil
        }
    }

    func retireKeptSurfaceFromRising(_ surface: SurfacePage) {
        undoSurface = nil
        undoDayID = nil
        let now = Date()
        var ledger = decodedDismissalLedger()
        ledger.dismiss(surfaceID: surface.id, dayID: today.id, at: now)
        ledger.prune(now: now, ttl: surfaceDismissalTTL)
        dismissedSurfaceLedgerV2 = encodedDismissalLedger(ledger)
        surfaceRefreshDate = now
        withAnimation(.spring(response: 0.55, dampingFraction: 0.82)) {
            surfacedPages = buildCuratorSurfaces(now: now)
        }
    }

    func clearPreparedSurfaceIfNeeded(_ surface: SurfacePage) {
        if generation.automaticIlluminatedSurface?.id == surface.id {
            generation.automaticIlluminatedSurface = nil
        }
        if generation.preparedStoryPageSurface?.id == surface.id {
            generation.preparedStoryPageSurface = nil
        }
        if generation.preparedGossipPageSurface?.id == surface.id {
            generation.preparedGossipPageSurface = nil
        }
        if generation.preparedFacultyResearchSurface?.id == surface.id {
            generation.preparedFacultyResearchSurface = nil
        }
        if generation.preparedLetterSurface?.id == surface.id {
            generation.preparedLetterSurface = nil
        }
        if preparedAnchorSurface?.id == surface.id {
            preparedAnchorSurface = nil
            nearbyAnchor = nil
        }
    }

    func decodedIlluminatedPhotoHistory() -> IlluminatedPhotoHistory {
        guard let data = illuminatedPhotoHistoryData.data(using: .utf8),
              let history = try? JSONDecoder().decode(IlluminatedPhotoHistory.self, from: data) else {
            return IlluminatedPhotoHistory()
        }
        return history
    }

    func encodedIlluminatedPhotoHistory(_ history: IlluminatedPhotoHistory) -> String {
        guard let data = try? JSONEncoder().encode(history),
              let encoded = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return encoded
    }

    func removeKeptPage(_ page: BookPage) {
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

    func restoreLastRemovedPage() {
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

    func dismissSurface(_ surface: SurfacePage) {
        tutorTouch("dismiss-surface")
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
        }
        clearPreparedSurfaceIfNeeded(surface)
        if selectedSurface?.id == surface.id {
            selectedSurface = nil
        }
        undoSurface = surface
        undoDayID = today.id
        surfaceRefreshDate = now
        statusMessage = "The \(surface.type.shortTitle.lowercased()) page slipped back into the stacks for a while."
    }

    func undoLastSurfaceDismissal() {
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

    func dismissedSurfaceIDs(for dayID: String, now: Date) -> Set<String> {
        var ledger = decodedDismissalLedger()
        ledger.prune(now: now, ttl: surfaceDismissalTTL)
        return ledger.activeDismissedSurfaceIDs(for: dayID, now: now, ttl: surfaceDismissalTTL)
    }

    func decodedDismissalLedger() -> SurfaceDismissalLedger {
        guard let data = dismissedSurfaceLedgerV2.data(using: .utf8),
              let ledger = try? JSONDecoder().decode(SurfaceDismissalLedger.self, from: data) else {
            return SurfaceDismissalLedger()
        }
        return ledger
    }

    func encodedDismissalLedger(_ ledger: SurfaceDismissalLedger) -> String {
        guard let data = try? JSONEncoder().encode(ledger),
              let encoded = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return encoded
    }

    func isSourceEnabled(sourceID: String) -> Bool {
        let defaultValue = BookPageSourceRegistry.sources.first { $0.id == sourceID }?.isActive ?? true
        return decodedSourcePreferenceLedger()[sourceID] ?? defaultValue
    }

    func disabledSourceIDs() -> Set<String> {
        Set(BookPageSourceRegistry.sources.compactMap { source in
            isSourceEnabled(sourceID: source.id) ? nil : source.id
        })
    }

    func setSourceEnabled(sourceID: String, isEnabled: Bool) {
        var ledger = decodedSourcePreferenceLedger()
        ledger[sourceID] = isEnabled
        sourcePreferenceLedger = encodedSourcePreferenceLedger(ledger)
        statusMessage = isEnabled ? "That doorway is open again." : "That doorway has been softened for now."
    }

    func decodedSourcePreferenceLedger() -> [String: Bool] {
        guard let data = sourcePreferenceLedger.data(using: .utf8),
              let ledger = try? JSONDecoder().decode([String: Bool].self, from: data) else {
            return [:]
        }
        return ledger
    }

    func encodedSourcePreferenceLedger(_ ledger: [String: Bool]) -> String {
        guard let data = try? JSONEncoder().encode(ledger),
              let encoded = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return encoded
    }

    func braidToday() async {
        guard !generation.isBraiding else { return }
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
        generation.braidRecovery.beginAttempt()
        let start = Date()
        generation.isBraiding = true
        generation.braidingStartedAt = start
        braidingQuipIndex = Int.random(in: 0..<BraidingQuips.lines.count)
        statusMessage = "The Book is drawing today's fragments into thread..."
        defer {
            generation.lastBraidDuration = Date().timeIntervalSince(start)
            generation.braidingStartedAt = nil
            generation.isBraiding = false
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
            generation.braidRecovery.recordSuccess()
        } catch {
            BookFeedback.play(.error)
            localBrainTelemetry.recordError("braid: \(error.localizedDescription)")
            generation.braidRecovery.recordFailure(error.localizedDescription, day: today)
            statusMessage = "The braid snagged, but nothing was lost. Let the page breathe, then try again. \(error.localizedDescription)"
        }
    }

    @MainActor
    func autoBraidIfNeeded(now: Date = Date()) async {
        guard BookSchedule.shouldAutoBraid(now),
              generation.didAutoBraidTodayID != today.id,
              today.bookOfYou == nil,
              !today.capturedPages.isEmpty,
              !generation.isBraiding else {
            return
        }

        generation.didAutoBraidTodayID = today.id
        statusMessage = "The hour has grown quiet; the Book is braiding today for you."
        await braidToday()
    }

    func runLaunchSmokeTestIfRequested() async {
        if ProcessInfo.processInfo.arguments.contains("--smoke-open-book-section") {
            let sections = glowBookSectionMenuItems
            appLog.info("Smoke: \(sections.count) book sections; opening first")
            if let first = sections.first {
                handleGlowMenuAction(.openBookSection(first.id))
                appLog.info("Smoke: book section surface presented: \(self.selectedSurface?.id ?? "nil", privacy: .public)")
            }
        }

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

    func persist(day: BookDay, message: String) {
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

    func refreshResurfacedPages() {
        resurfacedPages = (try? BookDatabase.resurfacingCandidates(limit: 3)) ?? []
    }

    @MainActor
    func loadAnchorLedger() {
        guard let data = anchorLedgerData.data(using: .utf8),
              let decoded = try? JSONDecoder().decode([AnchorRecord].self, from: data),
              !decoded.isEmpty else {
            // A local-anchors.json in Documents seeds a fresh install
            // with the player's own places — save data, not binary data.
            if let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
               let seedData = try? Data(contentsOf: documents.appendingPathComponent("local-anchors.json")),
               let seeded = try? JSONDecoder().decode([AnchorRecord].self, from: seedData),
               !seeded.isEmpty {
                anchorLedger = seeded.filter { !AnchorRegistry.retiredAnchorIDs.contains($0.id) }
                saveAnchorLedger()
                return
            }
            anchorLedger = AnchorRegistry.defaultAnchors
            return
        }
        let active = decoded.filter { !AnchorRegistry.retiredAnchorIDs.contains($0.id) }
        anchorLedger = active.isEmpty ? AnchorRegistry.defaultAnchors : active
        if active.count != decoded.count {
            saveAnchorLedger()
        }
    }

    @MainActor
    func saveAnchorLedger() {
        guard let data = try? JSONEncoder().encode(anchorLedger),
              let encoded = String(data: data, encoding: .utf8) else {
            return
        }
        anchorLedgerData = encoded
    }

    @MainActor
    func checkInAnchorIfNeeded(_ surface: SurfacePage) {
        guard let anchorID = surface.payload.metadata["anchorID"],
              let index = anchorLedger.firstIndex(where: { $0.id == anchorID }) else {
            return
        }
        anchorLedger[index] = anchorLedger[index].checkedIn(on: Date())
        saveAnchorLedger()
        if nearbyAnchor?.anchor.id == anchorID {
            nearbyAnchor = nil
        }
    }

    @discardableResult
    @MainActor
    func refreshAnchorProximity(isUserInitiated: Bool) async -> Bool {
        guard !isCheckingAnchors else { return false }
        guard AnchorLocationReader.isAvailable else {
            if isUserInitiated {
                anchorMessage = "This device cannot check for nearby Anchors yet."
            }
            return false
        }

        isCheckingAnchors = true
        if isUserInitiated {
            anchorMessage = "The Book is listening for the nearest Anchor..."
        }
        defer {
            isCheckingAnchors = false
        }

        do {
            AppMemoryLedger.record("anchor-before-location")
            let coordinate = try await AnchorLocationReader.requestLocation()
            AppMemoryLedger.record("anchor-after-location")
            didRequestAnchorLocation = true
            lastAnchorReadingLatitude = coordinate.latitude
            lastAnchorReadingLongitude = coordinate.longitude
            if let proximity = AnchorRegistry.nearestAnchor(
                to: coordinate.latitude,
                longitude: coordinate.longitude,
                anchors: anchorLedger
            ) {
                nearbyAnchor = proximity
                let source = OuterStacksAnchorPageSourceAdapter()
                var draftInputs = sourceInputs
                draftInputs.nearbyAnchor = proximity
                preparedAnchorSurface = source.manualSurface(
                    for: today,
                    context: CuratorContext.make(for: today),
                    inputs: draftInputs,
                    now: Date()
                )
                anchorMessage = "\(proximity.anchor.name) is \(Int(proximity.distanceMeters.rounded()))m away. The Outer Stacks page is awake."
            } else {
                nearbyAnchor = nil
                preparedAnchorSurface = nil
                anchorMessage = "No known Anchor lit within two hundred meters. This may become a future Anchor site."
            }
            surfaceRefreshDate = Date()
            return true
        } catch is CancellationError {
            if isUserInitiated {
                anchorMessage = "The ley line went quiet before the reading finished. Tap once more."
            }
            return false
        } catch {
            didRequestAnchorLocation = true
            if isUserInitiated {
                anchorMessage = error.localizedDescription
            }
            return false
        }
    }

    @MainActor
    func requestWeatherSignal() async {
        await refreshWeatherSignal(isUserInitiated: true, shouldEnchant: true)
    }

    @MainActor
    func refreshDynamicSourcesIfNeeded(
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

        if bookCalendarEnabled {
            calendarEvents = await CalendarDoorway.upcomingEvents(now: now)
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
    func refreshWeatherSignal(isUserInitiated: Bool, shouldEnchant: Bool) async -> Bool {
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
    func prepareWeatherPageIfPossible() async -> Bool {
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
    func refreshWonderCompassSelection() async {
        _ = await prepareWonderCompassSelectionIfPossible(force: true)
    }

    @MainActor
    @discardableResult
    func prepareWonderCompassSelectionIfPossible(force: Bool = false) async -> Bool {
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
    func requestHealthKitBodySignal() async {
        await refreshHealthKitBodySignal(isUserInitiated: true)
    }

    @discardableResult
    @MainActor
    func refreshHealthKitBodySignal(isUserInitiated: Bool) async -> Bool {
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

    func installModel() async {
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
    struct RepoInfo: Decodable {
        var siblings: [Sibling]
    }

    struct Sibling: Decodable {
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

    static func filesToDownload(modelID: String, revision: String) async throws -> [Sibling] {
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

    static func shouldInstall(path: String) -> Bool {
        let allowedSuffixes = [".safetensors", ".json", ".jinja", ".model", ".txt"]
        return allowedSuffixes.contains { path.hasSuffix($0) }
    }

    static func existingFileSize(at url: URL) -> Int64? {
        guard let size = try? FileManager.default.attributesOfItem(atPath: url.path)[.size] else {
            return nil
        }
        return fileSize(from: size)
    }

    static func fileSize(from value: Any?) -> Int64? {
        if let size = value as? Int64 {
            return size
        }
        if let number = value as? NSNumber {
            return number.int64Value
        }
        return nil
    }

    static func apiURL(modelID: String, revision: String) -> URL {
        var components = URLComponents()
        components.scheme = "https"
        components.host = "huggingface.co"
        components.path = "/api/models/\(modelID)/revision/\(revision)"
        return components.url!
    }

    static func resolveURL(modelID: String, revision: String, path: String) -> URL {
        var components = URLComponents()
        components.scheme = "https"
        components.host = "huggingface.co"
        components.path = "/\(modelID)/resolve/\(revision)/\(path)"
        components.queryItems = [URLQueryItem(name: "download", value: "true")]
        return components.url!
    }
}

private final class LocalModelFileDownloader: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
    let destination: URL
    let progressHandler: @Sendable (Int64, Int64) -> Void
    let lock = NSLock()
    var continuation: CheckedContinuation<Void, Error>?
    var session: URLSession?

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

    func finish(with result: Result<Void, Error>) {
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
    @Environment(\.accessibilityReduceMotion) var reduceMotion
    @State var glow = false

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
