import SwiftUI
import UniformTypeIdentifiers
import WidgetKit

struct ContentView: View {
    @State private var state = InsideCoverStore.load()
    @State private var showingImporter = false
    @State private var importMessage = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    previewCard

                    statusGrid

                    Button {
                        showingImporter = true
                    } label: {
                        Label("Import State", systemImage: "square.and.arrow.down")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)

                    Button {
                        if let sample = InsideCoverStore.loadBundledSample() {
                            try? InsideCoverStore.save(sample)
                            state = sample
                            importMessage = "Loaded bundled sample."
                        }
                    } label: {
                        Label("Sample Page", systemImage: "sparkles")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)

                    if !importMessage.isEmpty {
                        Text(importMessage)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding()
            }
            .navigationTitle("Enchantify")
            .fileImporter(
                isPresented: $showingImporter,
                allowedContentTypes: [.json],
                allowsMultipleSelection: false
            ) { result in
                switch result {
                case .success(let urls):
                    guard let url = urls.first else { return }
                    do {
                        state = try InsideCoverStore.importJSON(from: url)
                        importMessage = "Imported \(url.lastPathComponent). Add or refresh the widget."
                    } catch {
                        importMessage = "Import failed: \(error.localizedDescription)"
                    }
                case .failure(let error):
                    importMessage = "Import failed: \(error.localizedDescription)"
                }
            }
        }
    }

    private var previewCard: some View {
        ZStack(alignment: .bottomLeading) {
            if let image = InsideCoverStore.loadImage() {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
            } else {
                EnchantedPageBackground()
            }

            LinearGradient(colors: [.clear, .black.opacity(0.72)], startPoint: .center, endPoint: .bottom)

            VStack(alignment: .leading, spacing: 8) {
                Text(state.title.uppercased())
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.white.opacity(0.74))
                Text(state.day)
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundStyle(.white)
                Text(state.note)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.9))
                if !state.practice.isEmpty {
                    Label(state.practice, systemImage: "wand.and.stars")
                        .font(.footnote)
                        .foregroundStyle(.white.opacity(0.9))
                }
            }
            .padding()
        }
        .frame(height: 300)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private var statusGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
            InfoTile(
                title: "Now",
                value: state.now,
                systemImage: state.classroom?.active == true ? "person.wave.2" : "moon.stars"
            )
            InfoTile(
                title: "Next",
                value: state.next,
                systemImage: "calendar.badge.clock"
            )
            InfoTile(
                title: "Practice",
                value: state.practice.isEmpty ? "Open the Book" : state.practice,
                systemImage: "wand.and.stars"
            )
            InfoTile(
                title: "Vitality",
                value: state.health.map { "\($0.status) · \($0.score)" } ?? "Unknown",
                systemImage: "heart.text.square"
            )
        }
    }
}

struct InfoTile: View {
    let title: String
    let value: String
    let systemImage: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: systemImage)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)
                .lineLimit(1)

            Text(value.isEmpty ? "—" : value)
                .font(.callout)
                .fontWeight(.medium)
                .foregroundStyle(.primary)
                .lineLimit(3)
                .minimumScaleFactor(0.78)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(12)
        .frame(minHeight: 104, alignment: .topLeading)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
