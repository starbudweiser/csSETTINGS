// Opérations de fichiers, équivalents de pathlib / shutil de la version Python.

import Darwin
import Foundation

let fm = FileManager.default

public extension URL {
    static func path(_ p: String) -> URL { URL(fileURLWithPath: p).standardizedFileURL }
    func sub(_ rel: String) -> URL { appendingPathComponent(rel) }
    var name: String { lastPathComponent }
    /// Nom sans la dernière extension (Path.stem).
    var stem: String { deletingPathExtension().lastPathComponent }
    var parent: URL { deletingLastPathComponent() }
    var exists: Bool { fm.fileExists(atPath: path) }
    var isDir: Bool { var d: ObjCBool = false; return fm.fileExists(atPath: path, isDirectory: &d) && d.boolValue }
    var isFile: Bool { var d: ObjCBool = false; return fm.fileExists(atPath: path, isDirectory: &d) && !d.boolValue }
    /// Dossiers parents, du plus proche à la racine (Path.parents).
    var parents: [URL] {
        var out: [URL] = []
        var u = standardizedFileURL
        while u.path != "/" {
            u = u.deletingLastPathComponent()
            out.append(u)
        }
        return out
    }
    func same(_ other: URL) -> Bool { standardizedFileURL.path == other.standardizedFileURL.path }
    /// Vrai si self est dans `root` ou égal à lui (Path.is_relative_to).
    func inside(_ root: URL) -> Bool {
        let a = standardizedFileURL.pathComponents, b = root.standardizedFileURL.pathComponents
        return a.count >= b.count && Array(a.prefix(b.count)) == b
    }
}

/// fnmatch.fnmatch de Python (sensible à la casse ; « * » traverse aussi les « / »).
public func fnmatch(_ name: String, _ pattern: String) -> Bool {
    Darwin.fnmatch(pattern, name, 0) == 0
}

/// Tri de Python (ordre des points de code).
func pySorted(_ a: some Sequence<String>) -> [String] {
    a.sorted { $0.unicodeScalars.lexicographicallyPrecedes($1.unicodeScalars) }
}

func children(_ dir: URL) -> [URL] {
    ((try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? [])
        .map(\.standardizedFileURL)
        .sorted { $0.name.unicodeScalars.lexicographicallyPrecedes($1.name.unicodeScalars) }
}

func mkdirs(_ dir: URL) throws { try fm.createDirectory(at: dir, withIntermediateDirectories: true) }

func rmItem(_ url: URL) throws {
    var st = stat()
    if lstat(url.path, &st) == 0 { try fm.removeItem(at: url) }
}

/// shutil.copy2 : copie en écrasant, dates gardées.
func copyFile(_ src: URL, _ dst: URL) throws {
    try rmItem(dst)
    try fm.copyItem(at: src, to: dst)
}

/// shutil.copytree(src, dst, ignore=ignore_patterns(...)) : dst ne doit pas exister.
func copyTree(_ src: URL, _ dst: URL, ignore: [String] = []) throws {
    if dst.exists { throw CoreError.exists(dst.path) }
    try mkdirs(dst)
    for item in children(src) {
        if ignore.contains(where: { fnmatch(item.name, $0) }) { continue }
        let t = dst.sub(item.name)
        if item.isDir { try copyTree(item, t, ignore: ignore) } else { try copyFile(item, t) }
    }
}

func moveItem(_ src: URL, _ dst: URL) throws { try fm.moveItem(at: src, to: dst) }

/// os.replace : renommage atomique, la cible est remplacée.
func replace(_ src: URL, _ dst: URL) throws {
    if rename(src.path, dst.path) != 0 {
        throw CoreError.runtime(String(cString: strerror(errno)) + " : \(dst.path)")
    }
}

func writeText(_ text: String, _ url: URL) throws { try Data(text.utf8).write(to: url) }

func readText(_ url: URL) -> String? {
    guard let d = try? Data(contentsOf: url) else { return nil }
    return String(data: d, encoding: .utf8)
}

/// time.strftime en heure locale.
public func strftime(_ format: String, _ date: Date = Date()) -> String {
    let f = DateFormatter()
    f.locale = Locale(identifier: "en_US_POSIX")
    f.dateFormat = format
    return f.string(from: date)
}

/// Fichiers d'une arborescence (rglob), chemins relatifs avec « / », triés.
func walkFiles(_ root: URL) -> [(rel: String, url: URL)] {
    let base = root.standardizedFileURL
    guard let e = fm.enumerator(at: base, includingPropertiesForKeys: [.isRegularFileKey]) else { return [] }
    var out: [(String, URL)] = []
    let prefix = base.pathComponents.count
    for case let u as URL in e {
        let s = u.standardizedFileURL
        guard s.isFile else { continue }
        out.append((s.pathComponents.dropFirst(prefix).joined(separator: "/"), s))
    }
    return out.sorted { a, b in
        let x = a.0.split(separator: "/").map(String.init), y = b.0.split(separator: "/").map(String.init)
        return x.lexicographicallyPrecedes(y) { $0.unicodeScalars.lexicographicallyPrecedes($1.unicodeScalars) }
    }
}

/// Lance un programme et renvoie (code, sortie, erreurs).
@discardableResult
public func run(_ exe: String, _ args: [String], input: String? = nil, timeout: TimeInterval = 120) -> (code: Int32, out: String, err: String) {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: exe)
    p.arguments = args
    let out = Pipe(), err = Pipe()
    p.standardOutput = out
    p.standardError = err
    let inp = Pipe()
    p.standardInput = input == nil ? FileHandle.nullDevice : inp
    do { try p.run() } catch { return (-1, "", error.localizedDescription) }
    if let input { inp.fileHandleForWriting.write(Data(input.utf8)); try? inp.fileHandleForWriting.close() }
    var o = Data(), e = Data()
    let g = DispatchGroup()
    g.enter(); DispatchQueue.global().async { o = out.fileHandleForReading.readDataToEndOfFile(); g.leave() }
    g.enter(); DispatchQueue.global().async { e = err.fileHandleForReading.readDataToEndOfFile(); g.leave() }
    if g.wait(timeout: .now() + timeout) == .timedOut { p.terminate() }
    p.waitUntilExit()
    return (p.terminationStatus, String(decoding: o, as: UTF8.self), String(decoding: e, as: UTF8.self))
}
