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
            url: "https://github.com/HumanInterfaceDesign/WebRTC/releases/download/152.0.0/WebRTC-M152.xcframework.zip",
            checksum: "bbbe0673e7da59a2bb3951babec7b7bd23b03b977fbdd08dd4f2ea7bfd0cc5d1"
        ),
    ]
)
