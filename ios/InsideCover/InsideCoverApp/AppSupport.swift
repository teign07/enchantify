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

#if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX)
let mlxRuntimeLinked = true
#else
let mlxRuntimeLinked = false
#endif

let appLog = Logger(subsystem: "com.openclaw.enchantify.insidecover", category: "InsideCoverApp")

enum BookFeedback {
    enum Cue {
        case tap
        case select
        case openPage
        case keepPage
        case dismissPage
        case undo
        case braidStart
        case braidComplete
        case sourceRefresh
        case error
        case knock
        case knockReply

        #if canImport(AudioToolbox)
        /// Generic iOS fallback if a bundled sound is ever missing.
        var systemSoundID: SystemSoundID {
            switch self {
            case .tap:
                return 1104
            case .select:
                return 1105
            case .openPage:
                return 1106
            case .keepPage:
                return 1113
            case .dismissPage:
                return 1107
            case .undo:
                return 1157
            case .braidStart:
                return 1114
            case .braidComplete:
                return 1117
            case .sourceRefresh:
                return 1108
            case .error:
                return 1053
            case .knock:
                return 1104
            case .knockReply:
                return 1105
            }
        }
        #endif

        /// Bundled bookish sound, synthesized by scripts/generate_book_sounds.py.
        var soundName: String {
            switch self {
            case .tap:
                return "tap"
            case .select:
                return "select"
            case .openPage:
                return "open-page"
            case .keepPage:
                return "keep-page"
            case .dismissPage:
                return "dismiss-page"
            case .undo:
                return "undo"
            case .braidStart:
                return "braid-start"
            case .braidComplete:
                return "braid-complete"
            case .sourceRefresh:
                return "source-refresh"
            case .error:
                return "error"
            case .knock:
                return "knock"
            case .knockReply:
                return "knock-reply"
            }
        }
    }

    #if canImport(AudioToolbox)
    private static var bookSoundIDs: [String: SystemSoundID] = [:]

    private static func bookSoundID(for cue: Cue) -> SystemSoundID? {
        if let cached = bookSoundIDs[cue.soundName] {
            return cached
        }
        guard let url = Bundle.main.url(
            forResource: cue.soundName,
            withExtension: "caf",
            subdirectory: "BookSounds"
        ) else {
            return nil
        }
        var soundID: SystemSoundID = 0
        guard AudioServicesCreateSystemSoundID(url as CFURL, &soundID) == kAudioServicesNoError else {
            return nil
        }
        bookSoundIDs[cue.soundName] = soundID
        return soundID
    }
    #endif

    static func play(_ cue: Cue) {
        #if canImport(UIKit)
        switch cue {
        case .tap:
            UIImpactFeedbackGenerator(style: .light).impactOccurred(intensity: 0.35)
        case .select:
            UISelectionFeedbackGenerator().selectionChanged()
        case .openPage, .sourceRefresh, .braidStart:
            UIImpactFeedbackGenerator(style: .soft).impactOccurred(intensity: 0.55)
        case .keepPage, .braidComplete:
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        case .dismissPage, .undo:
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred(intensity: 0.42)
        case .error:
            UINotificationFeedbackGenerator().notificationOccurred(.warning)
        case .knock:
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred(intensity: 0.85)
        case .knockReply:
            let generator = UIImpactFeedbackGenerator(style: .soft)
            generator.impactOccurred(intensity: 0.7)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.22) {
                generator.impactOccurred(intensity: 0.62)
            }
        }
        #endif

        #if canImport(AudioToolbox)
        AudioServicesPlaySystemSound(bookSoundID(for: cue) ?? cue.systemSoundID)
        #endif
    }
}

extension Notification.Name {
    static let localBrainDidWake = Notification.Name("localBrainDidWake")
    static let localBrainDidRest = Notification.Name("localBrainDidRest")
    static let localBrainWorkDidChange = Notification.Name("localBrainWorkDidChange")
}

enum LocalBrainPresentation {
    case live
    case readingRoom
}

struct LocalBrainWorkSnapshot {
    var isWorking: Bool
    var label: String?
    var promptCharacters: Int
    var queuedCount: Int
}

enum AppMemoryLedger {
    static func record(_ checkpoint: String) {
        let resident = residentBytes()
        let message = "Memory checkpoint \(checkpoint); resident: \(resident)"
        appLog.info("\(message, privacy: .public)")
        print(message)
    }

    private static func residentBytes() -> UInt64 {
        var info = mach_task_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info>.size) / 4
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }
        return result == KERN_SUCCESS ? UInt64(info.resident_size) : 0
    }
}

enum BraidingQuips {
    static let lines = [
        "The Book is checking the corners for meaning.",
        "A small clerk in the margins has found a useful comma.",
        "Sorting bright fragments from dramatic lint.",
        "The page is warming its hands before it speaks.",
        "Listening for the sentence that has been hiding in the day.",
        "A ribbon is being tied around the ordinary.",
        "The ink is asking one follow-up question very quietly.",
        "Cross-referencing tea stains, weather, and courage.",
        "The Book is refusing to hurry the delicate bit.",
        "A little wonder has been located under the floorboards.",
        "The margins are arguing over the best adjective.",
        "Almost there. The sentence has put on its shoes."
    ]
}

enum LocalBrainQuips {
    static let lines = [
        "The Book is making room for one thought at a time.",
        "A margin clerk is holding the queue with both hands.",
        "The ink is drying in the order it arrived.",
        "The local brain has lit one lamp and no more.",
        "One page is speaking. The others are waiting politely.",
        "The shelves are staying quiet so the sentence can land.",
        "The Book is checking the thread before turning the page.",
        "The model is awake; the room is being kept still.",
        "A small, stubborn paragraph is assembling itself.",
        "No hurry. The important ink dislikes being shoved."
    ]
}

enum HealthKitBodyReader {
    enum ReaderError: LocalizedError {
        case unavailable
        case missingTypes
        case deniedOrEmpty

        var errorDescription: String? {
            switch self {
            case .unavailable:
                return "HealthKit is not available on this device."
            case .missingTypes:
                return "This build could not prepare the requested HealthKit types."
            case .deniedOrEmpty:
                return "HealthKit did not return enough body signal yet."
            }
        }
    }

    static var isAvailable: Bool {
        #if canImport(HealthKit)
        HKHealthStore.isHealthDataAvailable()
        #else
        false
        #endif
    }

    static func requestBodySignal() async throws -> BodySourceSignal {
        #if canImport(HealthKit)
        guard HKHealthStore.isHealthDataAvailable() else {
            throw ReaderError.unavailable
        }
        guard let stepType = HKQuantityType.quantityType(forIdentifier: .stepCount),
              let distanceType = HKQuantityType.quantityType(forIdentifier: .distanceWalkingRunning),
              let activeEnergyType = HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned),
              let sleepType = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) else {
            throw ReaderError.missingTypes
        }

        let store = HKHealthStore()
        let optionalQuantityTypes: [HKQuantityType] = [
            .quantityType(forIdentifier: .heartRate),
            .quantityType(forIdentifier: .restingHeartRate),
            .quantityType(forIdentifier: .heartRateVariabilitySDNN),
            .quantityType(forIdentifier: .walkingHeartRateAverage),
            .quantityType(forIdentifier: .oxygenSaturation),
            .quantityType(forIdentifier: .respiratoryRate),
            .quantityType(forIdentifier: .bloodPressureSystolic),
            .quantityType(forIdentifier: .bloodPressureDiastolic),
            .quantityType(forIdentifier: .bloodGlucose),
            .quantityType(forIdentifier: .bodyMass),
            .quantityType(forIdentifier: .bodyMassIndex),
            .quantityType(forIdentifier: .dietaryEnergyConsumed),
            .quantityType(forIdentifier: .dietaryWater),
            .quantityType(forIdentifier: .dietaryProtein),
            .quantityType(forIdentifier: .dietaryCarbohydrates),
            .quantityType(forIdentifier: .dietaryFatTotal),
            .quantityType(forIdentifier: .dietaryFiber)
        ].compactMap(\.self)
        let readTypes = Set<HKObjectType>([stepType, distanceType, activeEnergyType, sleepType] + optionalQuantityTypes)
        try await store.requestAuthorization(toShare: [], read: readTypes)

        async let steps = optionalQuantitySum(for: stepType, unit: .count(), store: store, daysBack: 1)
        async let distance = optionalQuantitySum(for: distanceType, unit: .meter(), store: store, daysBack: 1)
        async let energy = optionalQuantitySum(for: activeEnergyType, unit: .kilocalorie(), store: store, daysBack: 1)
        async let sleep = optionalSleepHours(for: sleepType, store: store)
        async let richerMetrics = optionalDoctorMetrics(store: store)

        return translate(
            steps: await steps,
            distanceMeters: await distance,
            activeKilocalories: await energy,
            sleepHours: await sleep,
            metrics: await richerMetrics
        )
        #else
        throw ReaderError.unavailable
        #endif
    }

    #if canImport(HealthKit)
    private static func optionalQuantitySum(
        for type: HKQuantityType,
        unit: HKUnit,
        store: HKHealthStore,
        daysBack: Int
    ) async -> Double {
        (try? await quantitySum(for: type, unit: unit, store: store, daysBack: daysBack)) ?? 0
    }

    private static func quantitySum(
        for type: HKQuantityType,
        unit: HKUnit,
        store: HKHealthStore,
        daysBack: Int
    ) async throws -> Double {
        let start = Calendar.current.date(byAdding: .day, value: -daysBack, to: Date()) ?? Date()
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, result, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: result?.sumQuantity()?.doubleValue(for: unit) ?? 0)
            }
            store.execute(query)
        }
    }

    private static func optionalSleepHours(for type: HKCategoryType, store: HKHealthStore) async -> Double {
        (try? await sleepHours(for: type, store: store)) ?? 0
    }

    private static func optionalDoctorMetrics(store: HKHealthStore) async -> [BodySourceSignal.Metric] {
        await withTaskGroup(of: BodySourceSignal.Metric?.self) { group in
            func addLatest(_ identifier: HKQuantityTypeIdentifier, label: String, unit: HKUnit, displayUnit: String, decimals: Int = 0) {
                guard let type = HKQuantityType.quantityType(forIdentifier: identifier) else { return }
                group.addTask {
                    await optionalLatestMetric(for: type, label: label, unit: unit, displayUnit: displayUnit, decimals: decimals, store: store)
                }
            }

            func addSum(_ identifier: HKQuantityTypeIdentifier, label: String, unit: HKUnit, displayUnit: String, daysBack: Int = 1, decimals: Int = 0) {
                guard let type = HKQuantityType.quantityType(forIdentifier: identifier) else { return }
                group.addTask {
                    let value = await optionalQuantitySum(for: type, unit: unit, store: store, daysBack: daysBack)
                    guard value > 0 else { return nil }
                    return BodySourceSignal.Metric(
                        id: identifier.rawValue,
                        label: label,
                        value: formatted(value, decimals: decimals),
                        unit: displayUnit,
                        kind: "sum"
                    )
                }
            }

            addLatest(.heartRate, label: "Heart rate", unit: HKUnit.count().unitDivided(by: .minute()), displayUnit: "bpm")
            addLatest(.restingHeartRate, label: "Resting heart rate", unit: HKUnit.count().unitDivided(by: .minute()), displayUnit: "bpm")
            addLatest(.heartRateVariabilitySDNN, label: "HRV", unit: .secondUnit(with: .milli), displayUnit: "ms")
            addLatest(.walkingHeartRateAverage, label: "Walking heart rate", unit: HKUnit.count().unitDivided(by: .minute()), displayUnit: "bpm")
            addLatest(.oxygenSaturation, label: "Oxygen saturation", unit: .percent(), displayUnit: "%", decimals: 1)
            addLatest(.respiratoryRate, label: "Respiratory rate", unit: HKUnit.count().unitDivided(by: .minute()), displayUnit: "/min", decimals: 1)
            addLatest(.bloodPressureSystolic, label: "Blood pressure systolic", unit: .millimeterOfMercury(), displayUnit: "mmHg")
            addLatest(.bloodPressureDiastolic, label: "Blood pressure diastolic", unit: .millimeterOfMercury(), displayUnit: "mmHg")
            addLatest(.bloodGlucose, label: "Blood glucose", unit: HKUnit.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci)), displayUnit: "mg/dL")
            addLatest(.bodyMass, label: "Body mass", unit: .pound(), displayUnit: "lb", decimals: 1)
            addLatest(.bodyMassIndex, label: "BMI", unit: .count(), displayUnit: "", decimals: 1)
            addSum(.dietaryEnergyConsumed, label: "Dietary energy", unit: .kilocalorie(), displayUnit: "kcal")
            addSum(.dietaryWater, label: "Water", unit: .literUnit(with: .milli), displayUnit: "mL")
            addSum(.dietaryProtein, label: "Protein", unit: .gram(), displayUnit: "g")
            addSum(.dietaryCarbohydrates, label: "Carbohydrates", unit: .gram(), displayUnit: "g")
            addSum(.dietaryFatTotal, label: "Fat", unit: .gram(), displayUnit: "g")
            addSum(.dietaryFiber, label: "Fiber", unit: .gram(), displayUnit: "g")
            var metrics: [BodySourceSignal.Metric] = []
            for await metric in group {
                if let metric {
                    metrics.append(metric)
                }
            }
            return metrics.sorted { $0.label < $1.label }
        }
    }

    private static func optionalLatestMetric(
        for type: HKQuantityType,
        label: String,
        unit: HKUnit,
        displayUnit: String,
        decimals: Int,
        store: HKHealthStore
    ) async -> BodySourceSignal.Metric? {
        guard let sample = try? await latestQuantitySample(for: type, store: store),
              sample.quantity.doubleValue(for: unit) > 0 else {
            return nil
        }
        return BodySourceSignal.Metric(
            id: type.identifier,
            label: label,
            value: formatted(sample.quantity.doubleValue(for: unit), decimals: decimals),
            unit: displayUnit,
            kind: "latest",
            observedAt: sample.endDate
        )
    }

    private static func latestQuantitySample(for type: HKQuantityType, store: HKHealthStore) async throws -> HKQuantitySample? {
        let start = Calendar.current.date(byAdding: .day, value: -30, to: Date()) ?? Date()
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)
        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(sampleType: type, predicate: predicate, limit: 1, sortDescriptors: [sort]) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: (samples as? [HKQuantitySample])?.first)
            }
            store.execute(query)
        }
    }

    private static func formatted(_ value: Double, decimals: Int) -> String {
        String(format: "%.\(decimals)f", value)
    }

    private static func sleepHours(for type: HKCategoryType, store: HKHealthStore) async throws -> Double {
        let start = Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date()
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        let asleepValues: Set<Int> = [
            HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
            HKCategoryValueSleepAnalysis.asleepCore.rawValue,
            HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
            HKCategoryValueSleepAnalysis.asleepREM.rawValue
        ]

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: type,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: nil
            ) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let seconds = (samples as? [HKCategorySample] ?? [])
                    .filter { asleepValues.contains($0.value) }
                    .reduce(0) { $0 + $1.endDate.timeIntervalSince($1.startDate) }
                continuation.resume(returning: seconds / 3600)
            }
            store.execute(query)
        }
    }
    #endif

    private static func translate(
        steps: Double,
        distanceMeters: Double,
        activeKilocalories: Double,
        sleepHours: Double,
        metrics: [BodySourceSignal.Metric]
    ) -> BodySourceSignal {
        let status: String
        let score: Int
        let phrase: String

        if sleepHours > 0, sleepHours < 5 {
            status = "WATCH"
            score = 30
            phrase = "The Book has softened the room today; the body asked for fewer sharp edges and a slower kind of courage."
        } else if steps < 900 && activeKilocalories < 120 {
            status = "LOW"
            score = 34
            phrase = "The lamps are low in the stacks. This looks like a day for small thresholds, warm fuel, and no heroic errands."
        } else if steps > 5_500 || distanceMeters > 3_500 {
            status = "BRIGHT"
            score = 76
            phrase = "There is motion in the margins. The Book can feel the day has had footsteps in it."
        } else {
            status = "STEADY"
            score = 58
            phrase = "The body page is steady enough for ordinary magic: a little movement, a little rest, and one honest page."
        }

        let baseMetrics: [BodySourceSignal.Metric] = [
            BodySourceSignal.Metric(id: "stepCount", label: "Steps", value: formatted(steps, decimals: 0), kind: "sum"),
            BodySourceSignal.Metric(id: "distanceWalkingRunning", label: "Distance", value: formatted(distanceMeters / 1_609.344, decimals: 2), unit: "mi", kind: "sum"),
            BodySourceSignal.Metric(id: "activeEnergyBurned", label: "Active energy", value: formatted(activeKilocalories, decimals: 0), unit: "kcal", kind: "sum"),
            BodySourceSignal.Metric(id: "sleepAnalysis", label: "Sleep", value: formatted(sleepHours, decimals: 1), unit: "h", kind: "category")
        ].filter { Double($0.value) ?? 0 > 0 }

        return BodySourceSignal(status: status, score: score, phrase: phrase, metrics: baseMetrics + metrics)
    }
}

enum WeatherLocationReader {
    enum ReaderError: LocalizedError {
        case unavailable
        case denied
        case noLocation
        case badResponse

        var errorDescription: String? {
            switch self {
            case .unavailable:
                return "Location is not available in this build."
            case .denied:
                return "Location permission is needed to read local weather and nearby Anchors."
            case .noLocation:
                return "The device did not return a location yet."
            case .badResponse:
                return "Open-Meteo did not return a readable forecast."
            }
        }
    }

    static var isAvailable: Bool {
        #if canImport(CoreLocation)
        CLLocationManager.locationServicesEnabled()
        #else
        false
        #endif
    }

    static func requestWeatherSignal() async throws -> WeatherSourceSignal {
        #if canImport(CoreLocation)
        guard CLLocationManager.locationServicesEnabled() else {
            throw ReaderError.unavailable
        }

        let location = try await OneShotLocationReader.requestLocation(
            desiredAccuracy: kCLLocationAccuracyThreeKilometers
        )
        let weather = try await OpenMeteoClient.forecast(for: location.coordinate)
        let temperature = weather.currentTemperature
        let condition = WeatherCode.describe(weather.current.weatherCode)
        let forecast = weather.todayForecast.map { daily in
            "\(WeatherCode.describe(daily.weatherCode)), high \(daily.highTemperature), low \(daily.lowTemperature)"
        }
        let phrase = [
            "Current: \(condition), \(temperature)",
            forecast.map { "Forecast: \($0)" }
        ].compactMap(\.self).joined(separator: " | ")

        return WeatherSourceSignal(
            phrase: phrase,
            source: "Open-Meteo",
            currentTemperature: temperature,
            forecast: forecast,
            conditionSymbolName: WeatherCode.symbolName(weather.current.weatherCode)
        )
        #else
        throw ReaderError.unavailable
        #endif
    }
}

enum AnchorLocationReader {
    enum ReaderError: LocalizedError {
        case unavailable
        case denied
        case noLocation

        var errorDescription: String? {
            switch self {
            case .unavailable:
                return "Location is not available in this build."
            case .denied:
                return "Location permission is needed to check nearby Anchors."
            case .noLocation:
                return "The device did not return a location yet."
            }
        }
    }

    static var isAvailable: Bool {
        #if canImport(CoreLocation)
        CLLocationManager.locationServicesEnabled()
        #else
        false
        #endif
    }

    static func requestLocation() async throws -> (latitude: Double, longitude: Double) {
        #if canImport(CoreLocation)
        guard CLLocationManager.locationServicesEnabled() else {
            throw ReaderError.unavailable
        }
        let location = try await OneShotLocationReader.requestLocation(
            desiredAccuracy: kCLLocationAccuracyHundredMeters
        )
        return (location.coordinate.latitude, location.coordinate.longitude)
        #else
        throw ReaderError.unavailable
        #endif
    }
}

#if canImport(CoreLocation)
private enum OpenMeteoClient {
    struct Response: Decodable {
        var current: Current
        var daily: Daily?

        struct Current: Decodable {
            var temperature2m: Double
            var weatherCode: Int

            enum CodingKeys: String, CodingKey {
                case temperature2m = "temperature_2m"
                case weatherCode = "weather_code"
            }
        }

        struct Daily: Decodable {
            var weatherCode: [Int]
            var temperature2mMax: [Double]
            var temperature2mMin: [Double]

            enum CodingKeys: String, CodingKey {
                case weatherCode = "weather_code"
                case temperature2mMax = "temperature_2m_max"
                case temperature2mMin = "temperature_2m_min"
            }
        }

        struct DailyForecast {
            var weatherCode: Int
            var highTemperature: String
            var lowTemperature: String
        }

        var currentTemperature: String {
            Self.temperatureFormatter.string(from: Measurement(value: current.temperature2m, unit: UnitTemperature.fahrenheit))
        }

        var todayForecast: DailyForecast? {
            guard let daily,
                  let code = daily.weatherCode.first,
                  let high = daily.temperature2mMax.first,
                  let low = daily.temperature2mMin.first else {
                return nil
            }
            return DailyForecast(
                weatherCode: code,
                highTemperature: Self.temperatureFormatter.string(from: Measurement(value: high, unit: UnitTemperature.fahrenheit)),
                lowTemperature: Self.temperatureFormatter.string(from: Measurement(value: low, unit: UnitTemperature.fahrenheit))
            )
        }

        private static let temperatureFormatter: MeasurementFormatter = {
            let formatter = MeasurementFormatter()
            formatter.unitOptions = .providedUnit
            formatter.unitStyle = .short
            formatter.numberFormatter.maximumFractionDigits = 0
            return formatter
        }()
    }

    static func forecast(for coordinate: CLLocationCoordinate2D) async throws -> Response {
        var components = URLComponents(string: "https://api.open-meteo.com/v1/forecast")
        components?.queryItems = [
            URLQueryItem(name: "latitude", value: String(format: "%.4f", coordinate.latitude)),
            URLQueryItem(name: "longitude", value: String(format: "%.4f", coordinate.longitude)),
            URLQueryItem(name: "current", value: "temperature_2m,weather_code"),
            URLQueryItem(name: "daily", value: "weather_code,temperature_2m_max,temperature_2m_min"),
            URLQueryItem(name: "temperature_unit", value: "fahrenheit"),
            URLQueryItem(name: "timezone", value: "auto"),
            URLQueryItem(name: "forecast_days", value: "1")
        ]
        guard let url = components?.url else {
            throw WeatherLocationReader.ReaderError.badResponse
        }

        let (data, response) = try await URLSession.shared.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw WeatherLocationReader.ReaderError.badResponse
        }
        return try JSONDecoder().decode(Response.self, from: data)
    }
}

private enum WeatherCode {
    static func describe(_ code: Int) -> String {
        switch code {
        case 0:
            return "clear sky"
        case 1:
            return "mostly clear"
        case 2:
            return "partly cloudy"
        case 3:
            return "overcast"
        case 45, 48:
            return "fog"
        case 51, 53, 55:
            return "drizzle"
        case 56, 57:
            return "freezing drizzle"
        case 61, 63, 65:
            return "rain"
        case 66, 67:
            return "freezing rain"
        case 71, 73, 75, 77:
            return "snow"
        case 80, 81, 82:
            return "rain showers"
        case 85, 86:
            return "snow showers"
        case 95, 96, 99:
            return "thunderstorm"
        default:
            return "changing weather"
        }
    }

    static func symbolName(_ code: Int) -> String {
        switch code {
        case 0, 1:
            return "sun.max"
        case 2:
            return "cloud.sun"
        case 3:
            return "cloud"
        case 45, 48:
            return "cloud.fog"
        case 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82:
            return "cloud.rain"
        case 71, 73, 75, 77, 85, 86:
            return "snowflake"
        case 95, 96, 99:
            return "cloud.bolt.rain"
        default:
            return "cloud.sun"
        }
    }
}

@MainActor
private final class OneShotLocationReader: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private var continuation: CheckedContinuation<CLLocation, Error>?

    static func requestLocation(desiredAccuracy: CLLocationAccuracy) async throws -> CLLocation {
        let reader = OneShotLocationReader()
        reader.manager.desiredAccuracy = desiredAccuracy
        return try await reader.location()
    }

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyThreeKilometers
    }

    private func location() async throws -> CLLocation {
        try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            let status = manager.authorizationStatus
            switch status {
            case .notDetermined:
                manager.requestWhenInUseAuthorization()
            case .authorizedAlways, .authorizedWhenInUse:
                manager.requestLocation()
            case .denied, .restricted:
                finish(throwing: WeatherLocationReader.ReaderError.denied)
            @unknown default:
                finish(throwing: WeatherLocationReader.ReaderError.noLocation)
            }
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        Task { @MainActor in
            switch manager.authorizationStatus {
            case .authorizedAlways, .authorizedWhenInUse:
                manager.requestLocation()
            case .denied, .restricted:
                finish(throwing: WeatherLocationReader.ReaderError.denied)
            case .notDetermined:
                break
            @unknown default:
                finish(throwing: WeatherLocationReader.ReaderError.noLocation)
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        Task { @MainActor in
            if let location = locations.last {
                finish(returning: location)
            } else {
                finish(throwing: WeatherLocationReader.ReaderError.noLocation)
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in
            finish(throwing: error)
        }
    }

    private func finish(returning location: CLLocation) {
        continuation?.resume(returning: location)
        continuation = nil
    }

    private func finish(throwing error: Error) {
        continuation?.resume(throwing: error)
        continuation = nil
    }
}
#endif

extension Notification.Name {
    /// System memory pressure, abstracted so ContentView can observe it
    /// without platform conditionals in the view body.
    static var bookMemoryPressure: Notification.Name {
        #if canImport(UIKit)
        UIApplication.didReceiveMemoryWarningNotification
        #else
        Notification.Name("bookMemoryPressure")
        #endif
    }
}

#if canImport(UIKit)
/// Shared full-screen camera capture used by any page that can take a photo
/// instead of choosing one from the library.
struct BookCameraCaptureView: UIViewControllerRepresentable {
    let onImageData: (Data) -> Void
    @Environment(\.dismiss) private var dismiss

    static var isCameraAvailable: Bool {
        UIImagePickerController.isSourceTypeAvailable(.camera)
    }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraCaptureMode = .photo
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onImageData: onImageData) {
            dismiss()
        }
    }

    final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let onImageData: (Data) -> Void
        let dismiss: () -> Void

        init(onImageData: @escaping (Data) -> Void, dismiss: @escaping () -> Void) {
            self.onImageData = onImageData
            self.dismiss = dismiss
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            if let image = info[.originalImage] as? UIImage,
               let data = image.jpegData(compressionQuality: 0.86) {
                onImageData(data)
            }
            dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            dismiss()
        }
    }
}
#endif

#if canImport(UserNotifications)
import UserNotifications
#endif

/// The Book's voice outside the app: a few quiet, in-world local
/// notifications. Class bells, the evening braid whisper, and aging favors.
/// Everything is prefixed so a refresh can sweep ours without touching
/// anything else, and the whole channel has one switch in the Colophon.
enum BookWhispers {
    static let identifierPrefix = "book-whisper-"

    static func refreshSchedule(enabled: Bool, electives: [UnwrittenElective], now: Date = Date()) {
        #if canImport(UserNotifications)
        let center = UNUserNotificationCenter.current()
        center.getPendingNotificationRequests { pending in
            let ours = pending.map(\.identifier).filter { $0.hasPrefix(identifierPrefix) }
            center.removePendingNotificationRequests(withIdentifiers: ours)
            guard enabled else { return }
            center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
                guard granted else { return }
                schedule(center: center, electives: electives, now: now)
            }
        }
        #endif
    }

    #if canImport(UserNotifications)
    private static func schedule(center: UNUserNotificationCenter, electives: [UnwrittenElective], now: Date) {
        var requests: [UNNotificationRequest] = []
        let calendar = Calendar.current

        // Class and club bells for the next three days, only future ones.
        for dayOffset in 0..<3 {
            guard let day = calendar.date(byAdding: .day, value: dayOffset, to: now) else { continue }
            let weekday = calendar.component(.weekday, from: day)
            guard let plan = AcademyScheduleRegistry.week[weekday] else { continue }
            if let id = plan.morning,
               let session = AcademyScheduleRegistry.classes[id],
               let request = bellRequest(for: session, on: day, hour: 9, isClub: false, calendar: calendar, now: now) {
                requests.append(request)
            }
            if let id = plan.club,
               let session = AcademyScheduleRegistry.clubs[id],
               let request = bellRequest(for: session, on: day, hour: 19, isClub: true, calendar: calendar, now: now) {
                requests.append(request)
            }
        }

        // The evening braid whisper, repeating daily.
        let braidContent = UNMutableNotificationContent()
        braidContent.title = "The Book is ready to braid"
        braidContent.body = "Today's kept pages can become tonight's Book of You entry."
        braidContent.sound = .default
        var braidTime = DateComponents()
        braidTime.hour = 20
        braidTime.minute = 45
        requests.append(UNNotificationRequest(
            identifier: "\(identifierPrefix)braid",
            content: braidContent,
            trigger: UNCalendarNotificationTrigger(dateMatching: braidTime, repeats: true)
        ))

        // Favors that have waited three days.
        for elective in electives.filter(\.isActive) {
            let remindAt = elective.createdAt.addingTimeInterval(3 * 24 * 3600)
            guard remindAt > now else { continue }
            let content = UNMutableNotificationContent()
            content.title = "A favor is waiting in the flyleaf"
            content.body = "\(elective.characterName) is still hoping for \"\(elective.title)\". One sentence of proof completes it."
            content.sound = .default
            let components = calendar.dateComponents([.year, .month, .day, .hour, .minute], from: remindAt)
            requests.append(UNNotificationRequest(
                identifier: "\(identifierPrefix)elective-\(elective.id)",
                content: content,
                trigger: UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
            ))
        }

        for request in requests {
            center.add(request)
        }
    }

    private static func bellRequest(
        for session: AcademySession,
        on day: Date,
        hour: Int,
        isClub: Bool,
        calendar: Calendar,
        now: Date
    ) -> UNNotificationRequest? {
        var components = calendar.dateComponents([.year, .month, .day], from: day)
        components.hour = hour
        components.minute = 0
        guard let fireDate = calendar.date(from: components), fireDate > now else { return nil }
        let content = UNMutableNotificationContent()
        content.title = isClub ? "\(session.name) is gathering" : "The \(session.name) bell"
        content.body = isClub
            ? "\(session.room), seven bells. \(session.companions.first.map { "\($0) will be there." } ?? "The regulars are arriving.")"
            : "\(session.leader) is starting in \(session.room)."
        content.sound = .default
        let dayID = calendar.dateComponents([.year, .month, .day], from: day)
        return UNNotificationRequest(
            identifier: "\(identifierPrefix)bell-\(session.id)-\(dayID.year ?? 0)-\(dayID.month ?? 0)-\(dayID.day ?? 0)",
            content: content,
            trigger: UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
        )
    }
    #endif
}

#if canImport(BackgroundTasks)
import BackgroundTasks
#endif

/// The overnight scribe: while the phone charges, the Book pre-writes the
/// next Story Page so mornings open onto fresh ink instead of a spinner.
enum OvernightScribe {
    static let taskIdentifier = "com.openclaw.enchantify.insidecover.overnight-scribe"
    static let freshnessWindow: TimeInterval = 18 * 3600

    private struct Draft: Codable {
        var generatedAt: Date
        var surface: SurfacePage
    }

    static var draftURL: URL {
        let base = InsideCoverStore.containerURL
            ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("OvernightStoryPage.json")
    }

    static func register() {
        #if canImport(BackgroundTasks)
        BGTaskScheduler.shared.register(forTaskWithIdentifier: taskIdentifier, using: nil) { task in
            guard let task = task as? BGProcessingTask else { return }
            handle(task)
        }
        #endif
    }

    static func scheduleNext(now: Date = Date()) {
        #if canImport(BackgroundTasks)
        let request = BGProcessingTaskRequest(identifier: taskIdentifier)
        request.requiresExternalPower = true
        request.requiresNetworkConnectivity = false
        request.earliestBeginDate = Calendar.current.nextDate(
            after: now,
            matching: DateComponents(hour: 2),
            matchingPolicy: .nextTime
        )
        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            appLog.info("Overnight scribe could not be scheduled: \(error.localizedDescription, privacy: .public)")
        }
        #endif
    }

    #if canImport(BackgroundTasks)
    private static func handle(_ task: BGProcessingTask) {
        scheduleNext()
        let work = Task {
            let wrote = await writeDraft()
            AppMemoryLedger.record(wrote ? "overnight-scribe-wrote" : "overnight-scribe-skipped")
            task.setTaskCompleted(success: wrote)
        }
        task.expirationHandler = {
            work.cancel()
            AppMemoryLedger.record("overnight-scribe-expired")
            task.setTaskCompleted(success: false)
        }
    }
    #endif

    static func writeDraft(now: Date = Date()) async -> Bool {
        #if NATIVE_LOCAL_BRAIN && canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX) && !targetEnvironment(simulator)
        guard LocalModelManager.report().state == .ready else { return false }

        let draft: SurfacePage = await MainActor.run {
            let days = BookDatabase.loadDays(migratingFrom: BookStore.loadDays())
            let day = BookStore.today(from: days)
            var inputs = BookSourceInputs.from(insideCover: InsideCoverStore.load())
            inputs.selfFacts = (try? BookDatabase.selfFacts()) ?? []
            let events = (try? BookDatabase.narrativeEvents(limit: 160)) ?? []
            let memories = (try? BookDatabase.entityMemories(limit: 240)) ?? []
            inputs.narrative = NarrativeSourceSnapshotBuilder.snapshot(
                from: events,
                memories: memories,
                beliefWeight: nil
            )
            return NarrativeOSPageSourceAdapter.draftCandidate(for: day, inputs: inputs, now: now)
        }

        await LocalBrainInferenceGate.shared.setBackgroundAllowance(true)
        defer {
            Task { await LocalBrainInferenceGate.shared.setBackgroundAllowance(false) }
        }
        do {
            let prose = try await MLXStoryPageWriter().write(surface: draft)
            let prepared = draft.preparedStoryPageCopy(
                prose: prose,
                slotID: SurfaceCadence.slotID(for: now, hours: 4)
            )
            let data = try JSONEncoder().encode(Draft(generatedAt: now, surface: prepared))
            try data.write(to: draftURL, options: [.atomic])
            return true
        } catch {
            appLog.error("Overnight scribe failed: \(error.localizedDescription, privacy: .public)")
            return false
        }
        #else
        return false
        #endif
    }

    /// Returns the overnight draft if it is still fresh. The file is
    /// consumed either way so a stale draft never lingers.
    static func adoptDraft(now: Date = Date()) -> SurfacePage? {
        guard let data = try? Data(contentsOf: draftURL) else { return nil }
        try? FileManager.default.removeItem(at: draftURL)
        let decoder = JSONDecoder()
        guard let draft = try? decoder.decode(Draft.self, from: data),
              now.timeIntervalSince(draft.generatedAt) < freshnessWindow else {
            return nil
        }
        return draft.surface
    }
}

/// All transient "the Book is writing" state, extracted from ContentView:
/// prepared surfaces, in-flight flags, and retry/recovery bookkeeping for
/// every generated page family. Observable, so only views that read a given
/// property re-evaluate when it changes.
@Observable
final class GenerationCoordinator {
    var isBraiding = false
    var braidingStartedAt: Date?
    var lastBraidDuration: TimeInterval?
    var braidRecovery = BraidRecoveryState()
    var didAutoBraidTodayID: String?
    var automaticIlluminatedSurface: SurfacePage?
    var isPreparingAutomaticIllumination = false
    var preparedStoryPageSurface: SurfacePage?
    var isPreparingStoryPage = false
    var storyPageRecovery = PreparedPageRecoveryState()
    var preparedGossipPageSurface: SurfacePage?
    var isPreparingGossipPage = false
    var gossipPageRecovery = PreparedPageRecoveryState()
    var preparedFacultyResearchSurface: SurfacePage?
    var isPreparingFacultyResearchPage = false
    var facultyResearchRecovery = PreparedPageRecoveryState()
    var preparedLetterSurface: SurfacePage?
    var isPreparingLetterPage = false
    var letterPageRecovery = PreparedPageRecoveryState()
}

/// Owns PlayerVaultData on disk. Replaces five separate JSON-in-AppStorage
/// ledgers; migrates them once on first launch and then becomes the only
/// writer. Observable, so views tracking vault-backed values stay live.
@Observable
final class PlayerVault {
    static let shared = PlayerVault()

    var data: PlayerVaultData

    private static var fileURL: URL {
        let base = InsideCoverStore.containerURL
            ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("PlayerVault.json")
    }

    private init() {
        if let bytes = try? Data(contentsOf: Self.fileURL),
           let decoded = try? JSONDecoder().decode(PlayerVaultData.self, from: bytes) {
            data = decoded
            return
        }
        data = Self.migrateFromLegacyLedgers()
        persist()
    }

    func save() {
        persist()
    }

    private func persist() {
        guard let bytes = try? JSONEncoder().encode(data) else { return }
        try? bytes.write(to: Self.fileURL, options: [.atomic])
    }

    /// One-time migration from the old per-ledger AppStorage keys. The old
    /// keys are left in place (never written again) as a safety copy.
    private static func migrateFromLegacyLedgers() -> PlayerVaultData {
        let defaults = UserDefaults.standard
        var migrated = PlayerVaultData()
        let decoder = JSONDecoder()
        if let raw = defaults.string(forKey: "anchorLedgerV1")?.data(using: .utf8),
           let anchors = try? decoder.decode([AnchorRecord].self, from: raw) {
            migrated.anchors = anchors.filter { !AnchorRegistry.retiredAnchorIDs.contains($0.id) }
        }
        if let raw = defaults.string(forKey: "unwrittenElectivesV1")?.data(using: .utf8),
           let electives = try? decoder.decode([UnwrittenElective].self, from: raw) {
            migrated.electives = electives
        }
        if let raw = defaults.string(forKey: "entityBeliefLedger")?.data(using: .utf8),
           let ledger = try? decoder.decode([String: Int].self, from: raw) {
            migrated.entityBelief = ledger
        }
        if let raw = defaults.string(forKey: "pageBeliefLedger")?.data(using: .utf8),
           let ledger = try? decoder.decode([String: Int].self, from: raw) {
            migrated.pageBelief = ledger
        }
        if let raw = defaults.string(forKey: "marginTutorSeenV1")?.data(using: .utf8),
           let seen = try? decoder.decode([String].self, from: raw) {
            migrated.tutorSeen = seen
        }
        return migrated
    }
}


#if canImport(EventKit)
import EventKit
#endif

/// The Calendar Doorway: reads today's and tomorrow's real events so the
/// curator can feel the day's hinges. Nothing leaves the device.
enum CalendarDoorway {
    static var isAvailable: Bool {
        #if canImport(EventKit)
        return true
        #else
        return false
        #endif
    }

    static func upcomingEvents(now: Date = Date()) async -> [CalendarEventSignal] {
        #if canImport(EventKit)
        let store = EKEventStore()
        let granted: Bool
        if #available(iOS 17.0, *) {
            granted = (try? await store.requestFullAccessToEvents()) ?? false
        } else {
            granted = (try? await store.requestAccess(to: .event)) ?? false
        }
        guard granted else { return [] }
        let calendar = Calendar.current
        let start = now.addingTimeInterval(-3600)
        let end = calendar.date(byAdding: .day, value: 2, to: now) ?? now.addingTimeInterval(2 * 86_400)
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: nil)
        return store.events(matching: predicate)
            .filter { !$0.isAllDay || calendar.isDate($0.startDate, inSameDayAs: now) }
            .prefix(24)
            .map { event in
                CalendarEventSignal(
                    id: event.eventIdentifier ?? UUID().uuidString,
                    title: event.title ?? "an unnamed appointment",
                    startsAt: event.startDate,
                    isAllDay: event.isAllDay
                )
            }
        #else
        return []
        #endif
    }
}

#if canImport(MapKit)
import MapKit
#endif

/// Scouts real named places near the player via Apple Maps POI search, so
/// characters can send them to places that actually exist. Results are
/// cached for days and the category pool rotates weekly so favors vary.
enum LocalPlacesScout {
    struct Cache: Codable {
        var fetchedAt: Date
        var latitude: Double
        var longitude: Double
        var places: [LocalPlaceSignal]
    }

    static let cacheKey = "localPlacesCacheV1"
    static let staleAfter: TimeInterval = 5 * 86_400
    static let moveThresholdMeters = 12_000.0

    static let categoryPool = [
        "diner", "bakery", "coffee shop", "hardware store", "bookstore",
        "thrift store", "antiques", "farm stand", "library", "park",
        "ice cream", "pizza", "fish market", "garden center", "barber shop"
    ]

    static func cachedPlaces() -> [LocalPlaceSignal] {
        guard let raw = UserDefaults.standard.string(forKey: cacheKey)?.data(using: .utf8),
              let cache = try? JSONDecoder().decode(Cache.self, from: raw) else {
            return []
        }
        return cache.places
    }

    static func refreshIfNeeded(now: Date = Date()) async -> [LocalPlaceSignal] {
        #if canImport(MapKit)
        var existing: Cache?
        if let raw = UserDefaults.standard.string(forKey: cacheKey)?.data(using: .utf8) {
            existing = try? JSONDecoder().decode(Cache.self, from: raw)
        }
        guard let coordinate = try? await AnchorLocationReader.requestLocation() else {
            return existing?.places ?? []
        }
        if let existing,
           now.timeIntervalSince(existing.fetchedAt) < staleAfter,
           AnchorMath.distanceMeters(
               fromLatitude: existing.latitude, longitude: existing.longitude,
               toLatitude: coordinate.latitude, longitude: coordinate.longitude
           ) < moveThresholdMeters {
            return existing.places
        }

        // Rotate five categories per refresh so the pool changes weekly.
        let week = Calendar.current.component(.weekOfYear, from: now)
        let rotated = (0..<5).map { categoryPool[(week * 3 + $0 * 2) % categoryPool.count] }
        var found: [LocalPlaceSignal] = []
        let region = MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: coordinate.latitude, longitude: coordinate.longitude),
            latitudinalMeters: 24_000,
            longitudinalMeters: 24_000
        )
        for category in rotated {
            let request = MKLocalSearch.Request()
            request.naturalLanguageQuery = category
            request.region = region
            request.resultTypes = .pointOfInterest
            guard let response = try? await MKLocalSearch(request: request).start() else { continue }
            for item in response.mapItems.prefix(3) {
                guard let name = item.name, !name.isEmpty else { continue }
                let location = item.placemark.coordinate
                let meters = AnchorMath.distanceMeters(
                    fromLatitude: coordinate.latitude, longitude: coordinate.longitude,
                    toLatitude: location.latitude, longitude: location.longitude
                )
                guard meters < 25_000 else { continue }
                let distance = meters < 1_500
                    ? "\(Int(meters)) m"
                    : String(format: "%.1f km", meters / 1000)
                found.append(LocalPlaceSignal(
                    id: "place-\(name.stableHash)",
                    name: name,
                    category: category,
                    distanceLabel: distance,
                    locality: item.placemark.locality ?? ""
                ))
            }
        }
        var seen = Set<String>()
        let places = found.filter { seen.insert($0.name).inserted }
        guard !places.isEmpty else { return existing?.places ?? [] }
        let cache = Cache(fetchedAt: now, latitude: coordinate.latitude, longitude: coordinate.longitude, places: places)
        if let data = try? JSONEncoder().encode(cache), let encoded = String(data: data, encoding: .utf8) {
            UserDefaults.standard.set(encoded, forKey: cacheKey)
        }
        AppMemoryLedger.record("places-scouted-\(places.count)")
        return places
        #else
        return []
        #endif
    }
}

#if canImport(StoreKit)
import StoreKit
#endif

/// What the BookShop needs from a payment system. The Goblins do not care
/// which till the coins land in.
struct BookShopOffer: Identifiable, Equatable {
    var id: String          // productID
    var listing: BookShopListing
    var displayPrice: String
    var isPurchasable: Bool
}

enum BookShopPurchaseOutcome: Equatable {
    case bound          // owned, persist it
    case pending        // ask-to-buy etc.
    case cancelled
    case failed(String)
}

protocol BookShopMerchant {
    var tillName: String { get }
    func offers() async -> [BookShopOffer]
    func purchase(productID: String) async -> BookShopPurchaseOutcome
    func restorePurchases() async -> Set<String>   // owned pack IDs
}

/// The real till: StoreKit 2. Compiles today; comes alive the moment the
/// products exist in App Store Connect under a paid developer membership.
struct StoreKitMerchant: BookShopMerchant {
    let tillName = "App Store"

    func offers() async -> [BookShopOffer] {
        #if canImport(StoreKit)
        let listings = BookShopCatalog.listings.filter { !$0.comingSoon }
        guard let products = try? await Product.products(for: listings.map(\.productID)) else {
            return []
        }
        return products.compactMap { product in
            guard let listing = BookShopCatalog.listings.first(where: { $0.productID == product.id }) else {
                return nil
            }
            return BookShopOffer(
                id: product.id,
                listing: listing,
                displayPrice: product.displayPrice,
                isPurchasable: true
            )
        }
        #else
        return []
        #endif
    }

    func purchase(productID: String) async -> BookShopPurchaseOutcome {
        #if canImport(StoreKit)
        guard let product = try? await Product.products(for: [productID]).first else {
            return .failed("The Goblins cannot find that item in the till.")
        }
        do {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                guard case .verified(let transaction) = verification else {
                    return .failed("The receipt would not verify.")
                }
                await transaction.finish()
                return .bound
            case .pending:
                return .pending
            case .userCancelled:
                return .cancelled
            @unknown default:
                return .failed("The till made an unfamiliar noise.")
            }
        } catch {
            return .failed(error.localizedDescription)
        }
        #else
        return .failed("No till in this build.")
        #endif
    }

    func restorePurchases() async -> Set<String> {
        #if canImport(StoreKit)
        var owned: Set<String> = []
        for await entitlement in Transaction.currentEntitlements {
            if case .verified(let transaction) = entitlement,
               let listing = BookShopCatalog.listings.first(where: { $0.productID == transaction.productID }) {
                owned.insert(listing.packID)
            }
        }
        return owned
        #else
        return []
        #endif
    }
}

/// The dev counter: lets the whole shop flow be exercised before the paid
/// developer membership exists. Clearly labeled in the UI; binds instantly.
struct ScrivenersCounterMerchant: BookShopMerchant {
    let tillName = "Scrivener's Counter (dev)"

    func offers() async -> [BookShopOffer] {
        BookShopCatalog.listings.filter { !$0.comingSoon }.map { listing in
            BookShopOffer(
                id: listing.productID,
                listing: listing,
                displayPrice: "0 coins (dev)",
                isPurchasable: true
            )
        }
    }

    func purchase(productID: String) async -> BookShopPurchaseOutcome {
        .bound
    }

    func restorePurchases() async -> Set<String> {
        []
    }
}

enum BookShopTill {
    /// StoreKit when it has real offers; the dev counter otherwise. When
    /// the membership lands and products exist, the shop flips itself live.
    static func resolveMerchant() async -> BookShopMerchant {
        let storeKit = StoreKitMerchant()
        let live = await storeKit.offers()
        if !live.isEmpty {
            return storeKit
        }
        return ScrivenersCounterMerchant()
    }
}

/// Vellum's assistant: turns parsed fuel items into rough nutrition via the
/// USDA FoodData Central API. Always background, never blocks a keep; a
/// missing key or dead network simply means no numbers this time.
enum VellumNutritionist {
    static let keyStorageKey = "usdaFoodDataKey"

    private static var apiKey: String {
        let stored = UserDefaults.standard.string(forKey: keyStorageKey)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return stored.isEmpty ? "DEMO_KEY" : stored
    }

    static func estimate(for entry: String) async -> NutritionEstimate? {
        let items = FuelParser.items(from: entry)
        guard !items.isEmpty else { return nil }
        var total = NutritionEstimate.zero
        var matched = 0
        for item in items.prefix(6) {
            guard let per100g = await lookupPer100g(item.name) else { continue }
            total = total + FuelParser.scale(per100g: per100g, item: item)
            matched += 1
        }
        guard matched > 0, total.kilocalories > 0 else { return nil }
        return total
    }

    private static func lookupPer100g(_ food: String) async -> NutritionEstimate? {
        var components = URLComponents(string: "https://api.nal.usda.gov/fdc/v1/foods/search")
        components?.queryItems = [
            URLQueryItem(name: "api_key", value: apiKey),
            URLQueryItem(name: "query", value: food),
            URLQueryItem(name: "dataType", value: "Foundation,SR Legacy"),
            URLQueryItem(name: "pageSize", value: "1")
        ]
        guard let url = components?.url else { return nil }
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        guard let (data, response) = try? await URLSession.shared.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200,
              let parsed = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let foods = parsed["foods"] as? [[String: Any]],
              let first = foods.first,
              let nutrients = first["foodNutrients"] as? [[String: Any]] else {
            return nil
        }
        func value(_ names: [String]) -> Double {
            for nutrient in nutrients {
                guard let name = nutrient["nutrientName"] as? String,
                      names.contains(where: { name.hasPrefix($0) }),
                      let amount = nutrient["value"] as? Double else { continue }
                return amount
            }
            return 0
        }
        let estimate = NutritionEstimate(
            kilocalories: value(["Energy"]),
            protein: value(["Protein"]),
            carbohydrates: value(["Carbohydrate, by difference"]),
            fat: value(["Total lipid (fat)"])
        )
        return estimate.kilocalories > 0 ? estimate : nil
    }
}
