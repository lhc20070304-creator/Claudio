import AppKit
import Foundation

let project = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Desktop/Claudio")
let launcher = project.appendingPathComponent("启动Claudio.command")
if CommandLine.arguments.contains("--check") {
    let ready = FileManager.default.isExecutableFile(atPath: launcher.path)
    print(ready ? "Launcher target exists and is executable" : "Launcher target missing")
    exit(ready ? 0 : 1)
}
func fail(_ message: String) -> Never {
    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)
    app.activate(ignoringOtherApps: true)
    let alert = NSAlert()
    alert.messageText = "Claudio 启动失败"
    alert.informativeText = message
    alert.addButton(withTitle: "好")
    alert.runModal()
    exit(1)
}
guard FileManager.default.isExecutableFile(atPath: launcher.path) else {
    fail("找不到桌面 Claudio 文件夹中的启动Claudio.command。请保留项目文件夹，或将它移回桌面。")
}
let logDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/Claudio")
do {
    try FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)
    let logURL = logDir.appendingPathComponent("launcher.log")
    if !FileManager.default.fileExists(atPath: logURL.path) {
        FileManager.default.createFile(atPath: logURL.path, contents: nil, attributes: [.posixPermissions: 0o600])
    }
    let log = try FileHandle(forWritingTo: logURL)
    defer { try? log.close() }
    try log.seekToEnd()
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/bin/bash")
    task.arguments = [launcher.path]
    var environment = ProcessInfo.processInfo.environment
    environment["CLAUDIO_APP_PYTHON"] = Bundle.main.bundleURL
        .appendingPathComponent("Contents/MacOS/Claudio").path
    task.environment = environment
    task.currentDirectoryURL = project
    task.standardOutput = log
    task.standardError = log
    task.standardInput = FileHandle.nullDevice
    try task.run()
    task.waitUntilExit()
    if task.terminationStatus != 0 {
        fail("启动程序已退出（状态 \(task.terminationStatus)）。详细原因见：\(logURL.path)")
    }
} catch {
    fail(error.localizedDescription)
}
