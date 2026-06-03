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
            url: "https://github.com/HumanInterfaceDesign/WebRTC/releases/download/149.0.0/WebRTC-M149.xcframework.zip",
            checksum: "c921d90702ff358d27c6c62965b9617b047ed3620a3a137f30a31e2967eea46c"
        ),
    ]
)
