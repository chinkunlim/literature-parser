import Foundation
import Vision
import AppKit

// Apple Vision OCR Bridge
// =======================
// Uses macOS native Vision Framework (VNRecognizeTextRequest) to perform
// highly accurate, Neural-Engine-accelerated optical character recognition
// and bounding-box extraction from rendered EPUB and PDF page images.

struct TextObservationResult: Codable {
    let text: String
    let confidence: Float
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct VisionBridgeOutput: Codable {
    let success: Bool
    let image_path: String
    let line_count: Int
    let full_text: String
    let lines: [TextObservationResult]
    let error: String?
}

func performOcr(on imagePath: String) {
    let fileUrl = URL(fileURLWithPath: imagePath)
    guard FileManager.default.fileExists(atPath: imagePath) else {
        let errOutput = VisionBridgeOutput(
            success: false,
            image_path: imagePath,
            line_count: 0,
            full_text: "",
            lines: [],
            error: "File does not exist: \(imagePath)"
        )
        outputJson(errOutput)
        return
    }

    guard let nsImage = NSImage(contentsOf: fileUrl),
          let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        let errOutput = VisionBridgeOutput(
            success: false,
            image_path: imagePath,
            line_count: 0,
            full_text: "",
            lines: [],
            error: "Failed creating CGImage from: \(imagePath)"
        )
        outputJson(errOutput)
        return
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    do {
        try handler.perform([request])
        guard let observations = request.results else {
            let emptyOutput = VisionBridgeOutput(
                success: true,
                image_path: imagePath,
                line_count: 0,
                full_text: "",
                lines: [],
                error: nil
            )
            outputJson(emptyOutput)
            return
        }

        var results: [TextObservationResult] = []
        var fullTextLines: [String] = []

        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let text = candidate.string
            let conf = candidate.confidence
            let box = obs.boundingBox
            results.append(
                TextObservationResult(
                    text: text,
                    confidence: conf,
                    x: Double(box.origin.x),
                    y: Double(box.origin.y),
                    width: Double(box.size.width),
                    height: Double(box.size.height)
                )
            )
            fullTextLines.append(text)
        }

        let output = VisionBridgeOutput(
            success: true,
            image_path: imagePath,
            line_count: results.count,
            full_text: fullTextLines.joined(separator: "\n"),
            lines: results,
            error: nil
        )
        outputJson(output)
    } catch {
        let errOutput = VisionBridgeOutput(
            success: false,
            image_path: imagePath,
            line_count: 0,
            full_text: "",
            lines: [],
            error: error.localizedDescription
        )
        outputJson(errOutput)
    }
}

func outputJson<T: Encodable>(_ object: T) {
    let encoder = JSONEncoder()
    encoder.outputFormatting = .sortedKeys
    if let data = try? encoder.encode(object),
       let jsonStr = String(data: data, encoding: .utf8) {
        print(jsonStr)
    } else {
        print("{\"success\": false, \"error\": \"Failed encoding JSON\"}")
    }
}

let args = CommandLine.arguments
if args.count < 2 {
    let usage = VisionBridgeOutput(
        success: false,
        image_path: "",
        line_count: 0,
        full_text: "",
        lines: [],
        error: "Usage: swift apple_vision_bridge.swift <image_path>"
    )
    outputJson(usage)
    exit(1)
}

let targetPath = args[1]
performOcr(on: targetPath)
