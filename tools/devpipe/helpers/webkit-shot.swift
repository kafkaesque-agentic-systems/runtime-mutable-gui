// webkit-shot.swift: render one local HTML file to a PNG with the WebKit that ships with macOS.
//
// Purpose: `devpipe ui render` uses this when no Chrome-family browser or Firefox is installed,
// so mockups can be turned into pictures on a stock Mac.
// Usage: swift webkit-shot.swift <file.html | http address> <width> <height> <out.png> [scale]
// Dependencies: macOS with the Swift toolchain (Xcode or its command line tools).
// Side effects: writes <out.png>. Loads the given file and what it references beside it, or the given address.
import AppKit
import WebKit

func fail(_ message: String, _ code: Int32 = 1) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code)
}

final class Shooter: NSObject, WKNavigationDelegate {
    let view: WKWebView
    let size: NSSize
    let scale: Double
    let target: URL

    init(size: NSSize, scale: Double, target: URL) {
        self.size = size
        self.scale = scale
        self.target = target
        view = WKWebView(frame: NSRect(origin: .zero, size: size))
        super.init()
        view.navigationDelegate = self
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        // A short pause lets fonts and CSS transitions settle before the picture is taken.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            let configuration = WKSnapshotConfiguration()
            configuration.rect = NSRect(origin: .zero, size: self.size)
            configuration.snapshotWidth = NSNumber(value: Double(self.size.width) * self.scale)
            webView.takeSnapshot(with: configuration) { image, error in
                // Drawn into a bitmap of exactly width x height x scale pixels: the snapshot's own
                // pixel size depends on the display the process happens to be attached to.
                guard let image = image,
                      let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil,
                                                    pixelsWide: Int(Double(self.size.width) * self.scale),
                                                    pixelsHigh: Int(Double(self.size.height) * self.scale),
                                                    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                                    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0),
                      let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
                    fail("snapshot failed: \(String(describing: error))")
                }
                NSGraphicsContext.saveGraphicsState()
                NSGraphicsContext.current = context
                // The context counts in the bitmap's pixels, so the picture is drawn to fill them.
                image.draw(in: NSRect(x: 0, y: 0, width: bitmap.pixelsWide, height: bitmap.pixelsHigh))
                NSGraphicsContext.restoreGraphicsState()
                guard let png = bitmap.representation(using: .png, properties: [:]) else {
                    fail("cannot encode the picture as PNG")
                }
                do {
                    try png.write(to: self.target)
                } catch {
                    fail("cannot write \(self.target.path): \(error)")
                }
                exit(0)
            }
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        fail("load failed: \(error)")
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        fail("load failed: \(error)")
    }
}

let arguments = CommandLine.arguments
if arguments.count < 5 { fail("usage: webkit-shot.swift <file.html> <width> <height> <out.png> [scale]", 2) }
guard let width = Double(arguments[2]), let height = Double(arguments[3]), width > 0, height > 0 else {
    fail("width and height must be positive numbers", 2)
}
let scale = arguments.count > 5 ? (Double(arguments[5]) ?? 2) : 2

let application = NSApplication.shared
application.setActivationPolicy(.prohibited)   // no Dock icon, no window
let shooter = Shooter(size: NSSize(width: width, height: height), scale: scale, target: URL(fileURLWithPath: arguments[4]))
if arguments[1].hasPrefix("http://") || arguments[1].hasPrefix("https://"), let address = URL(string: arguments[1]) {
    shooter.view.load(URLRequest(url: address))
} else {
    let source = URL(fileURLWithPath: arguments[1])
    shooter.view.loadFileURL(source, allowingReadAccessTo: source.deletingLastPathComponent())
}
DispatchQueue.main.asyncAfter(deadline: .now() + 30) { fail("timed out after 30 s") }
application.run()
