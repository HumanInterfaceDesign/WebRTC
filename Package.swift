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
            url: "https://github.com/HumanInterfaceDesign/WebRTC/releases/download/155.0.0/WebRTC-M155.xcframework.zip",
            checksum: "2535c260844d1f99d80d5b4fc5d3055c71c3ea7896fd7340f134a1c2d40f471c"
        ),
    ]
)
