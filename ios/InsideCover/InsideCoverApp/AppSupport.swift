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

#if canImport(MLXLLM) && canImport(MLXVLM) && canImport(MLXLMCommon) && canImport(MLXLMTokenizers) && canImport(MLXLMHFAPI) && canImport(MLX)
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

        #if canImport(AudioToolbox)
        var soundID: SystemSoundID {
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
            }
        }
        #endif
    }

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
        }
        #endif

        #if canImport(AudioToolbox)
        AudioServicesPlaySystemSound(cue.soundID)
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
        #if canImport(MLX)
        let mlx = Memory.snapshot()
        let message = "Memory checkpoint \(checkpoint); resident: \(resident); MLX active: \(mlx.activeMemory); MLX cache: \(mlx.cacheMemory); MLX peak: \(mlx.peakMemory)"
        appLog.info("\(message, privacy: .public)")
        print(message)
        #else
        let message = "Memory checkpoint \(checkpoint); resident: \(resident)"
        appLog.info("\(message, privacy: .public)")
        print(message)
        #endif
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
        let optionalClinicalTypes: [HKClinicalType] = [
            .clinicalType(forIdentifier: .medicationRecord),
            .clinicalType(forIdentifier: .allergyRecord),
            .clinicalType(forIdentifier: .conditionRecord),
            .clinicalType(forIdentifier: .labResultRecord),
            .clinicalType(forIdentifier: .immunizationRecord),
            .clinicalType(forIdentifier: .vitalSignRecord)
        ].compactMap(\.self)
        let readTypes = Set<HKObjectType>([stepType, distanceType, activeEnergyType, sleepType] + optionalQuantityTypes + optionalClinicalTypes)
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

            func addClinicalCount(_ identifier: HKClinicalTypeIdentifier, label: String) {
                guard let type = HKClinicalType.clinicalType(forIdentifier: identifier) else { return }
                group.addTask {
                    let count = await optionalSampleCount(for: type, store: store, daysBack: 365)
                    guard count > 0 else { return nil }
                    return BodySourceSignal.Metric(id: identifier.rawValue, label: label, value: "\(count)", unit: "records", kind: "clinical")
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
            addClinicalCount(.medicationRecord, label: "Medication")
            addClinicalCount(.allergyRecord, label: "Allergy")
            addClinicalCount(.conditionRecord, label: "Condition")
            addClinicalCount(.labResultRecord, label: "Lab")
            addClinicalCount(.immunizationRecord, label: "Immunization")
            addClinicalCount(.vitalSignRecord, label: "Vital sign")

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

    private static func optionalSampleCount(for type: HKSampleType, store: HKHealthStore, daysBack: Int) async -> Int {
        (try? await sampleCount(for: type, store: store, daysBack: daysBack)) ?? 0
    }

    private static func sampleCount(for type: HKSampleType, store: HKHealthStore, daysBack: Int) async throws -> Int {
        let start = Calendar.current.date(byAdding: .day, value: -daysBack, to: Date()) ?? Date()
        let predicate = HKQuery.predicateForSamples(withStart: start, end: Date())
        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(sampleType: type, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: samples?.count ?? 0)
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
                return "Location permission is needed to read local weather."
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

        let location = try await OneShotLocationReader.requestLocation()
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

    static func requestLocation() async throws -> CLLocation {
        let reader = OneShotLocationReader()
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
