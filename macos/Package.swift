// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "csSETTINGS",
    platforms: [.macOS(.v15)],
    targets: [
        // Presets, systèmes de shaders, Nexus et traductions, sans interface (testable seul)
        .target(name: "CSCore"),
        .executableTarget(name: "csSETTINGS", dependencies: ["CSCore"]),
        .testTarget(name: "CSCoreTests", dependencies: ["CSCore"]),
    ],
    swiftLanguageModes: [.v5]
)
