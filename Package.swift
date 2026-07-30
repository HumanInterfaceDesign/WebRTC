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
            url: "https://github.com/HumanInterfaceDesign/WebRTC/releases/download/151.0.0/WebRTC-M151.xcframework.zip",
            checksum: "a1c3f8af83f38f4c30f807451ae64cbff41c04db6afae485bc6e8a07777a36e9"
        ),
    ]
)
