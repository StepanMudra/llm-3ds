// Render SVG files to PNG at a given scale using AppKit (macOS 14+ reads SVG via NSImage).
import AppKit
let args = CommandLine.arguments
let scale = CGFloat(Double(args[1]) ?? 2)
for path in args.dropFirst(2) {
    guard let img = NSImage(contentsOfFile: path) else { print("cannot read \(path)"); continue }
    let w = Int(img.size.width * scale), h = Int(img.size.height * scale)
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    img.draw(in: NSRect(x: 0, y: 0, width: w, height: h))
    NSGraphicsContext.restoreGraphicsState()
    let out = (path as NSString).deletingPathExtension + ".png"
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: out))
    print("\(out) \(w)x\(h)")
}
