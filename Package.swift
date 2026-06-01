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
            url: "https://github.com/stasel/WebRTC/releases/download/148.0.0/WebRTC-M148.xcframework.zip",
            checksum: "0946db4556dc9d43d1073aada2f0fb69c16db7717632f664e67090a682ee5213"
        ),
    ]
)
