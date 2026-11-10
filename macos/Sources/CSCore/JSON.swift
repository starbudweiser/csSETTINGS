// JSON qui garde l'ordre des clés et le texte exact des nombres, écrit comme json.dumps de Python
// (indent, ensure_ascii=False) : les fichiers de Community Shaders, les manifestes et les journaux écrits par
// la version Python restent identiques une fois relus et réécrits.

import Foundation

public struct JObject: Equatable, Sequence {
    public private(set) var keys: [String] = []
    private var values: [String: JSON] = [:]

    public init() {}
    public init(_ pairs: [(String, JSON)]) { for (k, v) in pairs { self[k] = v } }

    public subscript(key: String) -> JSON? {
        get { values[key] }
        set {
            if let v = newValue {
                if values[key] == nil { keys.append(key) }
                values[key] = v
            } else if values.removeValue(forKey: key) != nil {
                keys.removeAll { $0 == key }
            }
        }
    }

    public var count: Int { keys.count }
    public var isEmpty: Bool { keys.isEmpty }
    public func contains(_ key: String) -> Bool { values[key] != nil }

    /// dict.update de Python : clés existantes remplacées sur place, nouvelles ajoutées à la fin.
    public mutating func update(_ other: JObject) { for (k, v) in other { self[k] = v } }

    public func makeIterator() -> AnyIterator<(String, JSON)> {
        var i = 0
        return AnyIterator {
            guard i < keys.count else { return nil }
            defer { i += 1 }
            return (keys[i], values[keys[i]]!)
        }
    }
}

public indirect enum JSON: Equatable {
    case null
    case bool(Bool)
    case number(String)   // texte d'origine (1, 1.0, 2e-3…)
    case string(String)
    case array([JSON])
    case object(JObject)

    public static func int(_ n: Int) -> JSON { .number(String(n)) }

    public subscript(key: String) -> JSON? { if case .object(let o) = self { return o[key] }; return nil }

    public var object: JObject? { if case .object(let o) = self { return o }; return nil }
    public var array: [JSON]? { if case .array(let a) = self { return a }; return nil }
    public var string: String? { if case .string(let s) = self { return s }; return nil }
    public var bool: Bool? { if case .bool(let b) = self { return b }; return nil }
    public var int: Int? {
        switch self {
        case .number(let s): return Int(s) ?? Double(s).flatMap { $0.isFinite ? Int($0) : nil }
        case .bool(let b): return b ? 1 : 0
        default: return nil
        }
    }
    public var double: Double? { if case .number(let s) = self { return Double(s) }; return nil }

    /// bool(x) de Python.
    public var truthy: Bool {
        switch self {
        case .null: return false
        case .bool(let b): return b
        case .number(let s): return (Double(s) ?? 1) != 0
        case .string(let s): return !s.isEmpty
        case .array(let a): return !a.isEmpty
        case .object(let o): return !o.isEmpty
        }
    }

    /// str(x) de Python, pour les valeurs affichées ou comparées (Version…).
    public var pyStr: String {
        switch self {
        case .null: return "None"
        case .bool(let b): return b ? "True" : "False"
        case .number(let s): return s
        case .string(let s): return s
        default: return serialized(indent: nil)
        }
    }

    // MARK: Lecture

    public enum ParseError: Error { case invalid(Int) }

    public static func parse(_ data: Data) throws -> JSON {
        var bytes = [UInt8](data)
        if bytes.starts(with: [0xEF, 0xBB, 0xBF]) { bytes.removeFirst(3) }
        var p = Parser(b: bytes)
        p.ws()
        let v = try p.value()
        p.ws()
        guard p.i == bytes.count else { throw ParseError.invalid(p.i) }
        return v
    }

    public static func parse(_ text: String) throws -> JSON { try parse(Data(text.utf8)) }

    /// Fichier JSON lu, ou nil s'il est absent ou illisible.
    public static func read(_ url: URL) -> JSON? {
        guard let d = try? Data(contentsOf: url) else { return nil }
        return try? parse(d)
    }

    /// _read_json de Python : l'objet du fichier, vide s'il manque, est illisible ou n'est pas un objet.
    public static func readObject(_ url: URL) -> JObject { read(url)?.object ?? JObject() }

    private struct Parser {
        let b: [UInt8]
        var i = 0

        mutating func ws() { while i < b.count, [0x20, 0x09, 0x0A, 0x0D].contains(b[i]) { i += 1 } }

        mutating func lit(_ s: String) -> Bool {
            let u = Array(s.utf8)
            guard i + u.count <= b.count, Array(b[i..<i + u.count]) == u else { return false }
            i += u.count
            return true
        }

        mutating func value() throws -> JSON {
            guard i < b.count else { throw ParseError.invalid(i) }
            switch b[i] {
            case UInt8(ascii: "{"):
                i += 1
                var o = JObject()
                ws()
                if i < b.count, b[i] == UInt8(ascii: "}") { i += 1; return .object(o) }
                while true {
                    ws()
                    guard i < b.count, b[i] == UInt8(ascii: "\"") else { throw ParseError.invalid(i) }
                    let k = try str()
                    ws()
                    guard i < b.count, b[i] == UInt8(ascii: ":") else { throw ParseError.invalid(i) }
                    i += 1
                    ws()
                    o[k] = try value()
                    ws()
                    guard i < b.count else { throw ParseError.invalid(i) }
                    if b[i] == UInt8(ascii: ",") { i += 1; continue }
                    if b[i] == UInt8(ascii: "}") { i += 1; return .object(o) }
                    throw ParseError.invalid(i)
                }
            case UInt8(ascii: "["):
                i += 1
                var a: [JSON] = []
                ws()
                if i < b.count, b[i] == UInt8(ascii: "]") { i += 1; return .array(a) }
                while true {
                    ws()
                    a.append(try value())
                    ws()
                    guard i < b.count else { throw ParseError.invalid(i) }
                    if b[i] == UInt8(ascii: ",") { i += 1; continue }
                    if b[i] == UInt8(ascii: "]") { i += 1; return .array(a) }
                    throw ParseError.invalid(i)
                }
            case UInt8(ascii: "\""):
                return .string(try str())
            default:
                if lit("true") { return .bool(true) }
                if lit("false") { return .bool(false) }
                if lit("null") { return .null }
                if lit("NaN") { return .number("NaN") }
                if lit("Infinity") { return .number("Infinity") }
                if lit("-Infinity") { return .number("-Infinity") }
                let start = i
                while i < b.count, "+-0123456789.eE".utf8.contains(b[i]) { i += 1 }
                guard i > start, let s = String(bytes: b[start..<i], encoding: .utf8), Double(s) != nil else {
                    throw ParseError.invalid(start)
                }
                return .number(s)
            }
        }

        mutating func hex4() throws -> UInt32 {
            guard i + 4 <= b.count, let s = String(bytes: b[i..<i + 4], encoding: .ascii), let v = UInt32(s, radix: 16) else {
                throw ParseError.invalid(i)
            }
            i += 4
            return v
        }

        mutating func str() throws -> String {
            i += 1
            var out = [UInt8]()
            while true {
                guard i < b.count else { throw ParseError.invalid(i) }
                let c = b[i]
                if c == UInt8(ascii: "\"") { i += 1; break }
                if c == UInt8(ascii: "\\") {
                    i += 1
                    guard i < b.count else { throw ParseError.invalid(i) }
                    let e = b[i]
                    i += 1
                    switch e {
                    case UInt8(ascii: "\""): out.append(0x22)
                    case UInt8(ascii: "\\"): out.append(0x5C)
                    case UInt8(ascii: "/"): out.append(0x2F)
                    case UInt8(ascii: "b"): out.append(0x08)
                    case UInt8(ascii: "f"): out.append(0x0C)
                    case UInt8(ascii: "n"): out.append(0x0A)
                    case UInt8(ascii: "r"): out.append(0x0D)
                    case UInt8(ascii: "t"): out.append(0x09)
                    case UInt8(ascii: "u"):
                        var cp = try hex4()
                        if (0xD800..<0xDC00).contains(cp), i + 6 <= b.count, b[i] == 0x5C, b[i + 1] == UInt8(ascii: "u") {
                            let save = i
                            i += 2
                            let lo = try hex4()
                            if (0xDC00..<0xE000).contains(lo) { cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00) } else { i = save }
                        }
                        out += Array(String(Character(Unicode.Scalar(cp) ?? "\u{FFFD}")).utf8)
                    default: throw ParseError.invalid(i)
                    }
                } else {
                    out.append(c)
                    i += 1
                }
            }
            guard let s = String(bytes: out, encoding: .utf8) else { throw ParseError.invalid(i) }
            return s
        }
    }

    // MARK: Écriture (json.dumps de Python)

    public func serialized(indent: Int? = 2) -> String {
        var out = ""
        write(&out, indent: indent, level: 0)
        return out
    }

    private static func quote(_ s: String) -> String {
        var r = "\""
        for u in s.unicodeScalars {
            switch u {
            case "\"": r += "\\\""
            case "\\": r += "\\\\"
            case "\n": r += "\\n"
            case "\r": r += "\\r"
            case "\t": r += "\\t"
            case "\u{08}": r += "\\b"
            case "\u{0C}": r += "\\f"
            default:
                if u.value < 0x20 { r += String(format: "\\u%04x", u.value) } else { r.unicodeScalars.append(u) }
            }
        }
        return r + "\""
    }

    private func write(_ out: inout String, indent: Int?, level: Int) {
        let pad = { (n: Int) -> String in indent.map { String(repeating: " ", count: $0 * n) } ?? "" }
        let sep = indent == nil ? ", " : ","
        switch self {
        case .null: out += "null"
        case .bool(let b): out += b ? "true" : "false"
        case .number(let s): out += s
        case .string(let s): out += JSON.quote(s)
        case .array(let a):
            if a.isEmpty { out += "[]"; return }
            out += "["
            for (n, v) in a.enumerated() {
                if n > 0 { out += sep }
                if indent != nil { out += "\n" + pad(level + 1) }
                v.write(&out, indent: indent, level: level + 1)
            }
            if indent != nil { out += "\n" + pad(level) }
            out += "]"
        case .object(let o):
            if o.isEmpty { out += "{}"; return }
            out += "{"
            for (n, (k, v)) in o.enumerated() {
                if n > 0 { out += sep }
                if indent != nil { out += "\n" + pad(level + 1) }
                out += JSON.quote(k) + ": "
                v.write(&out, indent: indent, level: level + 1)
            }
            if indent != nil { out += "\n" + pad(level) }
            out += "}"
        }
    }

    public func write(to url: URL, indent: Int? = 2) throws {
        try Data(serialized(indent: indent).utf8).write(to: url)
    }
}

extension JSON: ExpressibleByStringLiteral, ExpressibleByBooleanLiteral, ExpressibleByIntegerLiteral {
    public init(stringLiteral value: String) { self = .string(value) }
    public init(booleanLiteral value: Bool) { self = .bool(value) }
    public init(integerLiteral value: Int) { self = .number(String(value)) }
}

public extension JSON {
    static func strings(_ a: [String]) -> JSON { .array(a.map { .string($0) }) }
    var strings: [String] { array?.compactMap(\.string) ?? [] }
}
