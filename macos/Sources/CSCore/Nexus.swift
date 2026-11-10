// Accès à l'API Nexus Mods (v1) : clé personnelle dans le trousseau macOS, liste des fichiers, téléchargement.
// Le téléchargement direct par l'API est réservé aux comptes Premium ; un lien nxm:// (« Mod manager download »)
// porte une clé et une échéance qui permettent le téléchargement sans Premium.

import Foundation

public enum Nexus {
    public static let api = "https://api.nexusmods.com/v1"
    public static let game = "skyrimspecialedition"
    public static let appName = "csSETTINGS"
    public static var appVersion: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "2.0.0" }
    static let keychainService = "cSPRESETS Nexus API"   // nom d'origine conservé : la clé déjà rangée reste lisible
    static let keychainAccount = "apikey"
    public static let site = "https://www.nexusmods.com/games/\(game)/mods"
    /// Recherches proposées dans le navigateur intégré (la première s'ouvre par défaut). Nexus cherche le mot-clé tel
    /// quel : « preset » au singulier (20 résultats) et non « presets » (1) ou « settings » (0).
    public static let searches = ["Community Shaders preset", "CS preset", "Community Shaders", "Bottled Shaders"]

    public struct Failure: Error, CustomStringConvertible {
        public let message: String
        public var description: String { message }
    }

    // MARK: Clé (trousseau macOS, par l'outil security comme la version Python : la clé existante reste lisible sans demande)

    public static func getKey() -> String {
        let r = run("/usr/bin/security", ["find-generic-password", "-s", keychainService, "-a", keychainAccount, "-w"], timeout: 10)
        return r.code == 0 ? r.out.trimmingCharacters(in: .whitespacesAndNewlines) : ""
    }

    public static func setKey(_ key: String) throws {
        // -U met à jour l'entrée existante
        let r = run("/usr/bin/security", ["add-generic-password", "-U", "-s", keychainService, "-a", keychainAccount, "-w", key],
                    timeout: 10)
        if r.code != 0 { throw Failure(message: r.err.trimmingCharacters(in: .whitespacesAndNewlines)) }
    }

    public static func deleteKey() {
        run("/usr/bin/security", ["delete-generic-password", "-s", keychainService, "-a", keychainAccount], timeout: 10)
    }

    // MARK: Requêtes

    static func headers(_ key: String) -> [String: String] {
        ["apikey": key, "Accept": "application/json", "Application-Name": appName, "Application-Version": appVersion,
         "User-Agent": "\(appName)/\(appVersion)"]
    }

    /// Requête synchrone (à appeler hors du fil de l'interface).
    static func fetch(_ request: URLRequest) throws -> (Data, HTTPURLResponse) {
        let sem = DispatchSemaphore(value: 0)
        nonisolated(unsafe) var result: Result<(Data, HTTPURLResponse), Error> = .failure(Failure(message: "?"))
        URLSession.shared.dataTask(with: request) { d, r, e in
            if let e { result = .failure(Failure(message: e.localizedDescription)) } else if let r = r as? HTTPURLResponse {
                result = .success((d ?? Data(), r))
            }
            sem.signal()
        }.resume()
        sem.wait()
        return try result.get()
    }

    static func get(_ path: String, key: String) throws -> JSON {
        var req = URLRequest(url: URL(string: api + path)!, timeoutInterval: 30)
        for (k, v) in headers(key) { req.setValue(v, forHTTPHeaderField: k) }
        let (data, resp) = try fetch(req)
        guard (200..<300).contains(resp.statusCode) else {
            let msg = (try? JSON.parse(data))?["message"]?.string ?? ""
            throw Failure(message: "HTTP \(resp.statusCode) \(msg)".trimmingCharacters(in: .whitespaces))
        }
        do { return try JSON.parse(data) } catch { throw Failure(message: "JSON") }
    }

    /// {name, is_premium…} pour la clé donnée.
    public static func validate(_ key: String) throws -> JObject { try get("/users/validate.json", key: key).object ?? JObject() }

    /// Accepte un numéro ou une adresse nexusmods.com/skyrimspecialedition/mods/<id>.
    public static func parseModId(_ text: String) throws -> Int {
        let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if let r = t.range(of: #"/mods/(\d+)"#, options: .regularExpression) {
            return Int(t[r].dropFirst(6))!
        }
        if !t.isEmpty, t.allSatisfy(\.isASCII), t.allSatisfy(\.isNumber), let n = Int(t) { return n }
        throw CoreError.value(text)
    }

    /// quote(s, safe='') de Python.
    static func quote(_ s: String) -> String {
        s.addingPercentEncoding(withAllowedCharacters: CharacterSet(charactersIn:
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~")) ?? s
    }

    /// Page de résultats Nexus pour un mot-clé, triée par recommandations.
    public static func searchURL(_ keyword: String, sort: String = "endorsements") -> String {
        "\(site)?keyword=\(quote(keyword.trimmingCharacters(in: .whitespacesAndNewlines)))&sort=\(quote(sort))"
    }

    public struct NxmLink: Equatable {
        public var game: String
        public var modId: Int
        public var fileId: Int
        public var key: String
        public var expires: String
    }

    /// nxm://skyrimspecialedition/mods/<mod>/files/<fichier>?key=…&expires=… (bouton « Mod manager download »).
    public static func parseNxm(_ url: String) throws -> NxmLink {
        guard let c = URLComponents(string: url), c.scheme?.lowercased() == "nxm",
              let m = try? Regex(#"/mods/(\d+)/files/(\d+)"#).wholeMatch(in: c.path), let mod = m[1].substring.flatMap({ Int($0) }), let file = m[2].substring.flatMap({ Int($0) }) else {
            throw CoreError.value(url)
        }
        func q(_ n: String) -> String { c.queryItems?.first { $0.name == n && !($0.value ?? "").isEmpty }?.value ?? "" }
        return NxmLink(game: (c.host ?? "").lowercased(), modId: mod, fileId: file, key: q("key"), expires: q("expires"))
    }

    public static func fileInfo(_ mod: Int, _ file: Int, key: String) throws -> JObject {
        try get("/games/\(game)/mods/\(mod)/files/\(file).json", key: key).object ?? JObject()
    }

    public static func modInfo(_ mod: Int, key: String) throws -> JObject {
        try get("/games/\(game)/mods/\(mod).json", key: key).object ?? JObject()
    }

    public static func modFiles(_ mod: Int, key: String) throws -> [JObject] {
        let files = (try get("/games/\(game)/mods/\(mod)/files.json", key: key)["files"]?.array ?? []).compactMap(\.object)
        let order = ["MAIN": 0, "OPTIONAL": 1, "UPDATE": 2, "MISCELLANEOUS": 3, "OLD_VERSION": 4]
        let kept = files.filter { f in
            guard let c = f["category_name"], c != .null else { return false }
            return !["ARCHIVED", "DELETED"].contains(c.pyStr)
        }
        func k(_ f: JObject) -> (Int, Int) {
            (order[f["category_name"]?.pyStr ?? ""] ?? 9, -(f["uploaded_timestamp"]?.int ?? 0))
        }
        return kept.enumerated().sorted { a, b in
            let x = k(a.element), y = k(b.element)
            return x != y ? x < y : a.offset < b.offset
        }.map(\.element)
    }

    /// Télécharge le fichier dans destDir et renvoie son chemin. progress(reçus, total) est appelé en cours.
    /// nxm : lien du site (clé et échéance), sinon téléchargement direct (Premium).
    public static func download(_ mod: Int, file: JObject, key: String, to destDir: URL, nxm: NxmLink? = nil,
                                progress: ((Int64, Int64) -> Void)? = nil) throws -> URL {
        var path = "/games/\(game)/mods/\(mod)/files/\(file["file_id"]?.pyStr ?? "")/download_link.json"
        if let nxm, !nxm.key.isEmpty { path += "?key=\(quote(nxm.key))&expires=\(quote(nxm.expires))" }
        guard let link = try get(path, key: key).array?.first?["URI"]?.string, let url = URL(string: link) else {
            throw Failure(message: "no link")
        }
        let fileName = file["file_name"]?.string.flatMap { $0.isEmpty ? nil : $0 } ?? url.lastPathComponent
        let out = destDir.sub((fileName as NSString).lastPathComponent)
        var req = URLRequest(url: url, timeoutInterval: 60)
        req.setValue("\(appName)/\(appVersion)", forHTTPHeaderField: "User-Agent")
        let loader = Loader(progress: progress)
        try loader.load(req, to: out)
        return out
    }

    /// Téléchargement synchrone avec suivi de la progression.
    final class Loader: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
        let progress: ((Int64, Int64) -> Void)?
        let done = DispatchSemaphore(value: 0)
        var dest: URL!
        var error: Error?

        init(progress: ((Int64, Int64) -> Void)?) { self.progress = progress }

        func load(_ req: URLRequest, to dest: URL) throws {
            self.dest = dest
            let session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
            session.downloadTask(with: req).resume()
            done.wait()
            session.finishTasksAndInvalidate()
            if let error { throw error }
        }

        func urlSession(_ s: URLSession, downloadTask: URLSessionDownloadTask, didWriteData _: Int64, totalBytesWritten: Int64,
                        totalBytesExpectedToWrite: Int64) {
            progress?(totalBytesWritten, max(totalBytesExpectedToWrite, 0))
        }

        func urlSession(_ s: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo location: URL) {
            if let r = downloadTask.response as? HTTPURLResponse, !(200..<300).contains(r.statusCode) {
                error = Failure(message: "HTTP \(r.statusCode)")
                return
            }
            do {
                try? FileManager.default.removeItem(at: dest)
                try FileManager.default.moveItem(at: location, to: dest)
            } catch { self.error = error }
        }

        func urlSession(_ s: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
            if let error, self.error == nil { self.error = Failure(message: error.localizedDescription) }
            done.signal()
        }
    }
}
