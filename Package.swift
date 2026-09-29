// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "WebRTC",
    platforms: [.iOS(.v10), .macOS(.v10_11)],
    products: [
        .library(
            name: "WebRTC",
            targets: ["WebRTC"]),
    ],
    dependencies: [ ],
    targets: [
        .binaryTarget(
            name: "WebRTC",
            url: "https://github.com/HumanInterfaceDesign/WebRTC/releases/download/154.0.0/WebRTC-M154.xcframework.zip",
            checksum: "679aa915dffc07d410a1395aa70cc09f88451079814429ed4e443a1d1d8dfe13"
        ),
    ]
)
