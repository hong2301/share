import Foundation
import Vision
import AppKit

// 用法: swift ocr.swift <图片路径> 
// 输出识别文本到 stdout

guard CommandLine.arguments.count > 1 else {
    print("need image path")
    exit(1)
}
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("cannot load image")
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([request])

guard let observations = request.results else {
    print("no results")
    exit(1)
}
// 按从上到下排序
let sorted = observations.sorted { $0.boundingBox.maxY > $1.boundingBox.maxY }
for obs in sorted {
    if let candidate = obs.topCandidates(1).first {
        print(candidate.string)
    }
}
