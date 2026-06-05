// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "InsideCoverCore",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(name: "InsideCoverCore", targets: ["InsideCoverCore"])
    ],
    targets: [
        .target(
            name: "InsideCoverCore",
            path: "Shared",
            exclude: [
                "BookReferenceLibrary.json",
                "InsideCoverStore.swift"
            ],
            sources: [
                "InsideCoverState.swift",
                "BookArchiveDatabase.swift"
            ]
        ),
        .testTarget(
            name: "InsideCoverCoreTests",
            dependencies: ["InsideCoverCore"],
            path: "Tests/InsideCoverCoreTests"
        )
    ]
)
