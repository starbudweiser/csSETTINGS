// Systèmes de shaders : Community Shaders (CS) ou ENB, installés par couches réversibles sur un Skyrim SE 1.6.1170.
//
// Une couche est un dossier qui reproduit la racine du jeu (là où se trouve SkyrimSE.exe) :
//   commun/  pièces communes à tout rendu (KiLoader, Address Library, SSE Display Tweaks)
//   CS/      Community Shaders (Bottled Shaders) et son pont DLSS/MetalFX (d3d11.dll)
//   ENB/     ENBSeries et son d3d11.dll
// Le d3d11.dll appartient au système (pont mDLSS d'un côté, ENBSeries de l'autre) : jamais à la couche commune.
//
// Sûreté : le jeu garde un manifeste (empreinte de chaque fichier posé). Installer sauvegarde chaque fichier remplacé ;
// retirer ne supprime que ce qui est resté identique à la base, déplace dans la sauvegarde ce que le joueur ou le jeu a
// modifié, puis remet les fichiers d'origine. Une installation qui échoue est annulée. Rien n'est effacé sans copie.
// Mêmes fichiers (manifeste, journaux, bases) que la version Python.

import CryptoKit
import Foundation

public enum Systems {
    public static let gameVersionRequired = "1.6.1170.0"
    public static let MANIFEST = ".csSETTINGS_systemes.json"
    static let JOURNAL = "operation.json"
    public static let INFO = "systeme.json"
    static let SKIP_NAMES: Set<String> = [".DS_Store", INFO]
    static let FULL_HASH_MAX = 64 << 20   // au-delà : début et fin du fichier seulement (ShaderCache, BSA)
    public static let COMMUN = "commun", CS = "CS", ENB = "ENB"

    /// Copie vérifiée (remplaçable par les tests pour simuler une panne).
    nonisolated(unsafe) public static var safeCopyHook: ((URL, URL) throws -> Void)?

    /// Refus ou échec expliqué à l'utilisateur ; l'état du jeu est resté sain ou a été remis.
    public struct Failure: Error, CustomStringConvertible {
        public let message: String
        public init(_ m: String) { message = m }
        public var description: String { message }
    }

    // MARK: Jeu

    /// Version de SkyrimSE.exe (ressource VS_FIXEDFILEINFO), « » si illisible.
    public static func gameVersion(_ game: URL) -> String {
        guard let data = try? Data(contentsOf: game.sub("SkyrimSE.exe"), options: .alwaysMapped) else { return "" }
        let sig = Data([0xBD, 0x04, 0xEF, 0xFE]), v1 = Data([0x00, 0x00, 0x01, 0x00])
        var from = data.startIndex
        while let r = data.range(of: sig, in: from..<data.endIndex) {
            let i = r.lowerBound
            if i + 16 <= data.endIndex, data[(i + 4)..<(i + 8)] == v1 {   // structure version 1.0
                func le(_ o: Int) -> UInt32 { (0..<4).reduce(0) { $0 | UInt32(data[i + o + $1]) << (8 * $1) } }
                let ms = le(8), ls = le(12)
                return "\(ms >> 16).\(ms & 0xFFFF).\(ls >> 16).\(ls & 0xFFFF)"
            }
            from = i + 1
        }
        return ""
    }

    /// Ce qui manque pour accueillir un système (vide = prêt). SKSE n'est pas fourni : il doit être déjà installé.
    public static func prerequis(_ game: URL) -> [String] {
        guard game.sub("SkyrimSE.exe").isFile else { return [L("SkyrimSE.exe introuvable")] }
        var out: [String] = []
        let v = gameVersion(game)
        if v != gameVersionRequired {
            out.append(L("Skyrim {v} : seule la {req} est prise en charge",
                         ["v": v.isEmpty ? L("de version inconnue") : v, "req": String(gameVersionRequired.dropLast(2))]))
        }
        if !game.sub("skse64_loader.exe").isFile { out.append(L("SKSE (skse64_loader.exe) n'est pas installé")) }
        return out
    }

    public static func fingerprint(_ url: URL) throws -> String {
        let h = try FileHandle(forReadingFrom: url)
        defer { try? h.close() }
        let size = try h.seekToEnd()
        try h.seek(toOffset: 0)
        var sha = SHA256()
        let chunk = 1 << 20
        if size <= UInt64(FULL_HASH_MAX) {
            while let d = try h.read(upToCount: chunk), !d.isEmpty { sha.update(data: d) }
        } else {
            if let d = try h.read(upToCount: chunk) { sha.update(data: d) }
            try h.seek(toOffset: size - UInt64(chunk))
            if let d = try h.read(upToCount: chunk) { sha.update(data: d) }
        }
        let hex = sha.finalize().map { String(format: "%02x", $0) }.joined()
        return "\(size):\(hex.prefix(32))"
    }

    static func fp(_ url: URL) -> String { (try? fingerprint(url)) ?? "?" }

    /// Chemin relatif (avec /) → fichier, pour tout ce que contient une couche.
    public static func filesOf(_ root: URL) -> [(rel: String, url: URL)] {
        walkFiles(root).filter { !SKIP_NAMES.contains($0.url.name) }
    }

    // MARK: Manifeste

    public struct FileMeta: Equatable { public var fp: String; public var pre: Bool }

    public struct Layer: Equatable {
        public var files: [(String, FileMeta)] = []
        public var date = ""
        public var operation = ""
        public var replaced: [String] = []

        public static func == (a: Layer, b: Layer) -> Bool {
            a.files.map(\.0) == b.files.map(\.0) && a.files.map(\.1) == b.files.map(\.1)
                && a.date == b.date && a.operation == b.operation && a.replaced == b.replaced
        }

        public func meta(_ rel: String) -> FileMeta? { files.first { $0.0 == rel }?.1 }
    }

    public struct Manifest: Equatable {
        public var layers: [(String, Layer)] = []

        public static func == (a: Manifest, b: Manifest) -> Bool { a.layers.map(\.0) == b.layers.map(\.0) && a.layers.map(\.1) == b.layers.map(\.1) }

        public subscript(name: String) -> Layer? {
            get { layers.first { $0.0 == name }?.1 }
            set {
                if let i = layers.firstIndex(where: { $0.0 == name }) {
                    if let v = newValue { layers[i].1 = v } else { layers.remove(at: i) }
                } else if let v = newValue { layers.append((name, v)) }
            }
        }

        init() {}

        init?(_ j: JSON) {
            guard let ls = j["layers"]?.object else { return nil }
            for (name, v) in ls {
                var l = Layer()
                for (rel, m) in v["files"]?.object ?? JObject() {
                    l.files.append((rel, FileMeta(fp: m["fp"]?.string ?? "", pre: m["pre"]?.truthy ?? false)))
                }
                l.date = v["date"]?.string ?? ""
                l.operation = v["operation"]?.string ?? ""
                l.replaced = v["remplacés"]?.strings ?? []
                layers.append((name, l))
            }
        }

        var json: JSON {
            var ls = JObject()
            for (name, l) in layers {
                var files = JObject()
                for (rel, m) in l.files { files[rel] = .object(JObject([("fp", .string(m.fp)), ("pre", .bool(m.pre))])) }
                ls[name] = .object(JObject([("files", .object(files)), ("date", .string(l.date)),
                                            ("operation", .string(l.operation)), ("remplacés", .strings(l.replaced))]))
            }
            return .object(JObject([("layers", .object(ls))]))
        }
    }

    public static func readManifest(_ game: URL) -> Manifest {
        JSON.read(game.sub(MANIFEST)).flatMap { Manifest($0) } ?? Manifest()
    }

    static func writeManifest(_ game: URL, _ m: Manifest) throws {
        let target = game.sub(MANIFEST)
        let tmp = game.sub(MANIFEST + ".tmp")
        try m.json.write(to: tmp, indent: 1)
        try replace(tmp, target)
    }

    public static func installed(_ game: URL) -> [String] { readManifest(game).layers.map(\.0) }

    /// CS ou ENB si l'un des deux est posé, sinon nil.
    public static func activeSystem(_ game: URL) -> String? { installed(game).first { $0 == CS || $0 == ENB } }

    // MARK: Copie sûre

    /// Copie vérifiée : écrite sous un nom provisoire, contrôlée, puis posée d'un coup.
    static func safeCopy(_ src: URL, _ dst: URL) throws {
        if let hook = safeCopyHook { return try hook(src, dst) }
        try realSafeCopy(src, dst)
    }

    public static func realSafeCopy(_ src: URL, _ dst: URL) throws {
        try mkdirs(dst.parent)
        let tmp = dst.parent.sub(dst.name + ".csnew")
        try copyFile(src, tmp)
        if try fingerprint(tmp) != fingerprint(src) {
            try? rmItem(tmp)
            throw Failure(L("Copie corrompue : {name}", ["name": src.name]))
        }
        try replace(tmp, dst)
    }

    /// Met un fichier du jeu à l'abri dans la sauvegarde (copie vérifiée), sans le supprimer.
    static func stash(_ file: URL, _ op: URL, _ folder: String, _ rel: String) throws {
        try safeCopy(file, op.sub(folder).sub(rel))
    }

    /// Retire les dossiers devenus vides après un retrait (jamais la racine du jeu ni Data).
    static func prune(_ game: URL, _ rels: [String]) {
        let keep = [game.standardizedFileURL.path, game.sub("Data").standardizedFileURL.path]
        var dirs: [URL] = []
        for r in rels {
            let d = game.sub(r).parent.standardizedFileURL
            if !dirs.contains(where: { $0.same(d) }) { dirs.append(d) }
        }
        for start in dirs.sorted(by: { $0.pathComponents.count > $1.pathComponents.count }) {
            var d = start
            while !keep.contains(d.path), d.path != "/", d.isDir, children(d).isEmpty {
                try? fm.removeItem(at: d)
                d = d.parent.standardizedFileURL
            }
        }
    }

    // MARK: Plan

    public struct Plan: Equatable {
        public var layer: String
        public var add: [String] = []                 // absents du jeu
        public var replace: [String] = []             // présents et différents : sauvegardés puis remplacés
        public var same: [String] = []                // déjà identiques : laissés, jamais retirés ensuite
        public var conflicts: [(String, String)] = [] // fichier → couche qui le possède déjà

        public static func == (a: Plan, b: Plan) -> Bool {
            a.layer == b.layer && a.add == b.add && a.replace == b.replace && a.same == b.same
                && a.conflicts.map(\.0) == b.conflicts.map(\.0)
        }
    }

    public static func planInstall(_ game: URL, _ layer: String, _ src: URL) -> Plan {
        var owners: [String: String] = [:]
        for (n, l) in readManifest(game).layers { for (rel, _) in l.files { owners[rel] = n } }
        var p = Plan(layer: layer)
        for (rel, s) in filesOf(src) {
            if let o = owners[rel], o != layer { p.conflicts.append((rel, o)); continue }
            let d = game.sub(rel)
            if !d.isFile { p.add.append(rel) } else if fp(d) == fp(s) { p.same.append(rel) } else { p.replace.append(rel) }
        }
        return p
    }

    static func newOp(_ backupRoot: URL, _ kind: String, _ layer: String, _ extra: JObject) throws -> URL {
        let stamp = strftime("yyyy-MM-dd_HHmmss")
        var op = backupRoot.sub("\(stamp)_\(kind)_\(layer)"), n = 2
        while op.exists {
            op = backupRoot.sub("\(stamp)_\(n)_\(kind)_\(layer)")
            n += 1
        }
        try mkdirs(op)
        var data = JObject([("type", .string(kind)), ("layer", .string(layer)), ("status", "en cours")])
        data.update(extra)
        try journal(op, data)
        return op
    }

    static func journal(_ op: URL, _ data: JObject) throws {
        let path = op.sub(JOURNAL)
        var all = JSON.read(path)?.object ?? JObject()
        all.update(data)
        try JSON.object(all).write(to: path, indent: 1)
    }

    static func checkReady(_ game: URL, _ isRunning: (() -> Bool)?, checkVersion: Bool) throws {
        guard game.isDir else { throw Failure(L("Dossier du jeu introuvable : {path}", ["path": game.path])) }
        if let isRunning, isRunning() { throw Failure(L("Le jeu est lancé : fermez-le avant de changer de système.")) }
        if checkVersion {
            let problems = prerequis(game)
            if !problems.isEmpty { throw Failure(problems.joined(separator: " ; ")) }
        }
    }

    // MARK: Installer / retirer

    /// Pose une couche. Renvoie le dossier de sauvegarde de l'opération. En cas d'échec, tout est remis.
    ///
    /// adopt : les fichiers déjà identiques à la base sont pris en charge (retirés avec la couche) au lieu d'être
    /// laissés ; sert à reprendre une installation faite à la main, sans rien recopier.
    @discardableResult
    public static func install(_ game: URL, _ layer: String, _ src: URL, _ backupRoot: URL, isRunning: (() -> Bool)? = nil,
                               checkVersion: Bool = true, adopt: Bool = false) throws -> URL {
        try checkReady(game, isRunning, checkVersion: checkVersion)
        guard src.isDir else { throw Failure(L("Base introuvable : {path}", ["path": src.path])) }
        var manifest = readManifest(game)
        if manifest[layer] != nil { throw Failure(L("« {name} » est déjà installé : retirez-le d'abord.", ["name": layer])) }
        if layer == CS || layer == ENB, let other = activeSystem(game) {
            throw Failure(L("« {name} » est installé : utilisez l'échange de système.", ["name": other]))
        }
        let plan = planInstall(game, layer, src)
        if let first = plan.conflicts.first {
            throw Failure(L("{n} fichier(s) appartiennent déjà à une autre couche (ex. {file}).",
                            ["n": plan.conflicts.count, "file": first.0]))
        }
        let op = try newOp(backupRoot, "install", layer, JObject([("manifest_avant", manifest.json), ("posés", .array([])),
                                                                 ("remplacés", .array([]))]))
        var files: [(String, FileMeta)] = [], replaced: [String] = [], laid: [String] = []
        let same = Set(plan.same), toReplace = Set(plan.replace)
        do {
            for (rel, s) in filesOf(src) {
                let d = game.sub(rel)
                let f = try fingerprint(s)
                if same.contains(rel) { files.append((rel, FileMeta(fp: f, pre: !adopt))); continue }
                if adopt { continue }   // reprise : on ne suit que ce qui est déjà identique
                if toReplace.contains(rel) {
                    try stash(d, op, "remplaces", rel)
                    replaced.append(rel)
                }
                try safeCopy(s, d)
                laid.append(rel)
                files.append((rel, FileMeta(fp: f, pre: false)))
            }
            manifest[layer] = Layer(files: files, date: strftime("yyyy-MM-dd HH:mm:ss"), operation: op.name, replaced: replaced)
            try writeManifest(game, manifest)
            try journal(op, JObject([("status", "terminé"), ("posés", .strings(laid)), ("remplacés", .strings(replaced))]))
        } catch {
            undoInstall(game, op, laid, replaced)
            try? journal(op, JObject([("status", "annulé"), ("erreur", .string("\(error)"))]))
            if error is Failure { throw error }
            throw Failure(L("Installation de {layer} annulée, jeu remis en l'état : {err}", ["layer": layer, "err": "\(error)"]))
        }
        return op
    }

    static func undoInstall(_ game: URL, _ op: URL, _ laid: [String], _ replaced: [String]) {
        for rel in laid {
            try? rmItem(game.sub(rel))
            try? rmItem(game.sub(rel).parent.sub(game.sub(rel).name + ".csnew"))
        }
        for rel in replaced {
            let saved = op.sub("remplaces").sub(rel)
            if saved.isFile { try? safeCopy(saved, game.sub(rel)) }
        }
        prune(game, laid)
        if let before = JSON.read(op.sub(JOURNAL))?["manifest_avant"], let m = Manifest(before) {
            try? writeManifest(game, m)
        }
    }

    /// Retire une couche. Fichiers identiques à la base : supprimés. Modifiés depuis : mis dans la sauvegarde
    /// (« retires/ »). Fichiers d'origine remplacés à l'installation : remis en place.
    @discardableResult
    public static func remove(_ game: URL, _ layer: String, _ backupRoot: URL, isRunning: (() -> Bool)? = nil) throws -> URL {
        try checkReady(game, isRunning, checkVersion: false)
        var manifest = readManifest(game)
        guard let entry = manifest[layer] else { throw Failure(L("« {name} » n'est pas installé.", ["name": layer])) }
        let op = try newOp(backupRoot, "remove", layer, JObject([("manifest_avant", manifest.json)]))
        var removed: [String] = [], kept: [String] = [], missing: [String] = []
        let installOp = backupRoot.sub(entry.operation)
        for (rel, meta) in entry.files {
            let d = game.sub(rel)
            if meta.pre { continue }
            guard d.isFile else { missing.append(rel); continue }
            if try fingerprint(d) != meta.fp {
                try stash(d, op, "retires", rel)   // copie vérifiée d'abord, suppression ensuite
                kept.append(rel)
            }
            try fm.removeItem(at: d)
            removed.append(rel)
        }
        var restored: [String] = []
        for rel in entry.replaced {
            let saved = installOp.sub("remplaces").sub(rel)
            if !entry.operation.isEmpty, saved.isFile {
                try safeCopy(saved, game.sub(rel))
                restored.append(rel)
            } else {
                missing.append("original de \(rel)")
            }
        }
        prune(game, removed)
        manifest[layer] = nil
        try writeManifest(game, manifest)
        try journal(op, JObject([("status", "terminé"), ("supprimés", .strings(removed)), ("mis_de_côté", .strings(kept)),
                                 ("originaux_remis", .strings(restored)), ("absents", .strings(missing))]))
        return op
    }

    /// Passe de `current` à `target` (CS ↔ ENB). La couche commune est posée si elle manque, jamais retirée.
    /// Si l'installation de `target` échoue, `current` est réinstallé depuis sa base.
    @discardableResult
    public static func swap(_ game: URL, current: String?, target: String, bases: [String: URL], _ backupRoot: URL,
                            isRunning: (() -> Bool)? = nil, withCommun: Bool = true) throws -> [URL] {
        try checkReady(game, isRunning, checkVersion: true)
        guard let base = bases[target], base.isDir else { throw Failure(L("Base « {name} » introuvable.", ["name": target])) }
        var ops: [URL] = []
        if withCommun, let commun = bases[COMMUN], !installed(game).contains(COMMUN) {
            ops.append(try install(game, COMMUN, commun, backupRoot, isRunning: isRunning))
        }
        if let current, installed(game).contains(current) {
            ops.append(try remove(game, current, backupRoot, isRunning: isRunning))
        }
        do {
            ops.append(try install(game, target, base, backupRoot, isRunning: isRunning))
        } catch let e as Failure {
            if let current, let back = bases[current] {
                do {
                    try install(game, current, back, backupRoot, isRunning: isRunning)
                } catch let e2 as Failure {
                    throw Failure(L("{err} — et {name} n'a pas pu être remis : {err2}. Sauvegardes : {dir}",
                                    ["err": e.message, "name": current, "err2": e2.message, "dir": backupRoot.path]))
                }
            }
            throw e
        }
        return ops
    }

    /// Retire de la couche installée des fichiers précis (ex. un plugin devenu indésirable) : copie vérifiée dans la
    /// sauvegarde (« retires/ »), suppression dans le jeu, retrait du manifeste. Les autres fichiers ne bougent pas.
    @discardableResult
    public static func dropFiles(_ game: URL, _ layer: String, _ rels: [String], _ backupRoot: URL) throws -> URL {
        var manifest = readManifest(game)
        guard var entry = manifest[layer] else { throw Failure(L("« {name} » n'est pas installé.", ["name": layer])) }
        let op = try newOp(backupRoot, "drop", layer, JObject([("manifest_avant", manifest.json)]))
        var done: [String] = []
        for rel in rels {
            let d = game.sub(rel)
            if d.isFile {
                try stash(d, op, "retires", rel)
                try fm.removeItem(at: d)
            }
            entry.files.removeAll { $0.0 == rel }
            done.append(rel)
        }
        manifest[layer] = entry
        prune(game, done)
        try writeManifest(game, manifest)
        try journal(op, JObject([("status", "terminé"), ("supprimés", .strings(done))]))
        return op
    }

    public struct Verification: Equatable {
        public var absents: [String] = []
        public var modified: [String] = []
    }

    /// État d'une couche installée : fichiers absents, modifiés depuis la pose.
    public static func verify(_ game: URL, _ layer: String) throws -> Verification {
        guard let entry = readManifest(game)[layer] else { throw Failure(L("« {name} » n'est pas installé.", ["name": layer])) }
        var out = Verification()
        for (rel, meta) in entry.files {
            let d = game.sub(rel)
            if !d.isFile { out.absents.append(rel) } else if fp(d) != meta.fp { out.modified.append(rel) }
        }
        return out
    }

    public struct SwapPlan: Equatable {
        public var remove = 0
        public var aside: [String] = []   // modifiés depuis la pose : mis de côté
        public var add = 0
        public var replace = 0
        public var identical = 0
    }

    /// Ce que fera un échange, sans rien écrire : fichiers retirés, mis de côté (modifiés depuis la pose), ajoutés,
    /// remplacés (sauvegardés) et déjà identiques.
    public static func planSwap(_ game: URL, current: String?, target: String, base: URL) -> SwapPlan {
        let entry = readManifest(game)[current ?? ""]?.files ?? []
        let owned = entry.filter { !$0.1.pre }
        let ownedSet = Set(owned.map(\.0))
        var out = SwapPlan(remove: owned.count)
        out.aside = pySorted(ownedSet).filter { rel in
            game.sub(rel).isFile && fp(game.sub(rel)) != entry.first { $0.0 == rel }!.1.fp
        }
        for (rel, s) in filesOf(base) {
            let d = game.sub(rel)
            if ownedSet.contains(rel) || !d.isFile { out.add += 1 } else if fp(d) == fp(s) { out.identical += 1 } else { out.replace += 1 }
        }
        return out
    }

    /// Vrai si le jeu contient déjà (au moins `threshold`) cette base : installation faite à la main à reprendre.
    public static func adoptable(_ game: URL, _ base: URL, threshold: Double = 0.8) -> Bool {
        let p = planInstall(game, "?", base)
        let total = p.add.count + p.replace.count + p.same.count
        return total > 0 && Double(p.same.count) / Double(total) >= threshold
    }

    public struct Operation: Equatable {
        public var path: URL
        public var name: String
        public var type: String
        public var layer: String
        public var status: String
    }

    /// Opérations d'installation et de retrait déjà faites (dossiers de sauvegarde), la plus récente d'abord.
    public static func listOperations(_ root: URL) -> [Operation] {
        children(root).reversed().compactMap { d in
            guard d.isDir, let j = JSON.read(d.sub(JOURNAL))?.object else { return nil }
            return Operation(path: d, name: d.name, type: j["type"]?.pyStr ?? "", layer: j["layer"]?.pyStr ?? "",
                             status: j["status"]?.pyStr ?? "")
        }
    }

    // MARK: Bases neutres

    public struct Source {
        public var path: URL
        public var prefix = ""                    // ajouté devant chaque chemin (ex. « Data/ »)
        public var include: [String] = []         // motifs fnmatch sur le chemin final ; vide = tout
        public var exclude: [String] = []
        public var patches: [(String, String, String)] = []   // (chemin final, texte à remplacer, remplacement) après copie

        public init(_ path: URL, prefix: String = "", include: [String] = [], exclude: [String] = [],
                    patches: [(String, String, String)] = []) {
            self.path = path; self.prefix = prefix; self.include = include; self.exclude = exclude; self.patches = patches
        }
    }

    /// Construit une base neutre à partir de paquets (les suivants l'emportent). dest ne doit pas exister :
    /// la base est montée à côté puis renommée, pour ne jamais laisser une base à moitié faite.
    @discardableResult
    public static func assemble(_ dest: URL, _ sources: [Source], name: String, notes: String = "") throws -> Int {
        if dest.exists { throw Failure(L("{name} existe déjà : supprimez-le pour reconstruire la base.", ["name": dest.name])) }
        let tmp = dest.parent.sub(dest.name + ".en_construction")
        try? rmItem(tmp)
        do {
            for s in sources {
                guard s.path.isDir else { throw Failure(L("Paquet introuvable : {path}", ["path": s.path.path])) }
                for (rel, f) in filesOf(s.path) {
                    let final = s.prefix + rel
                    if !s.include.isEmpty && !s.include.contains(where: { fnmatch(final, $0) }) { continue }
                    if s.exclude.contains(where: { fnmatch(final, $0) }) { continue }
                    let out = tmp.sub(final)
                    try mkdirs(out.parent)
                    try copyFile(f, out)
                    for (target, old, new) in s.patches where final == target {
                        let text = readText(out) ?? ""
                        guard text.contains(old) else {
                            throw Failure(L("Correctif impossible : « {old} » absent de {file}", ["old": old, "file": final]))
                        }
                        try writeText(text.replacingOccurrences(of: old, with: new), out)
                    }
                }
            }
            let count = filesOf(tmp).count   // fichiers distincts (un paquet suivant peut en écraser un autre)
            try mkdirs(tmp)
            try JSON.object(JObject([("nom", .string(name)), ("date", .string(strftime("yyyy-MM-dd HH:mm:ss"))),
                                     ("fichiers", .int(count)), ("notes", .string(notes)),
                                     ("sources", .strings(sources.map(\.path.path)))])).write(to: tmp.sub(INFO), indent: 1)
            try replace(tmp, dest)
            return count
        } catch {
            try? fm.removeItem(at: tmp)
            throw error
        }
    }

    /// Réglages du joueur : jamais dans une base (une base est neutre, les presets les posent ensuite)
    public static let USER_SETTINGS = ["Data/SKSE/Plugins/CommunityShaders/SettingsUser.json",
                                       "Data/SKSE/Plugins/CommunityShaders/SettingsTest.json",
                                       "Data/SKSE/Plugins/CommunityShaders/PostProcessing/*", "Data/Shaders/ShaderCache/*",
                                       "*.log", "*.pdb"]
    public static let SHARED = ["Data/SKSE/Plugins/SSEDisplayTweaks.*", "Data/SKSE/Plugins/versionlib-*"]
    /// Fournis avec ENBSeries 0.505 + DLSS mais inutilisables ici :
    /// - ENB Helper : refuse tout autre helper que celui d'ENB Extender (Legacy 1.6.0, dans Data/KiLoader/Plugins) et
    ///   propose de quitter le jeu (« Incompatible ENB Helper detected ») ;
    /// - DynamicShaderFrameGen : crée toujours un proxy D3D12, absent de DXMT (CrossOver) → plantage E_NOINTERFACE, même
    ///   avec FrameGeneration=0.
    public static let ENB_INCOMPATIBLES = ["Data/SKSE/plugins/ENBHelper*", "Data/SKSE/plugins/DynamicShaderFrameGen.*"]
    static let ENB_PATCHES: [(String, String, String)] = []
    /// Plugins ENB de KiLoader (ENB Helper, ENB Extender) : la variante Legacy 1.6.0 est la seule compatible 1.6.1170 et
    /// elle accompagne les presets ENB / Effects 11, pas le socle ; les poser ici risquerait d'écraser la bonne version.
    static let KILOADER_ENB = ["Data/KiLoader/Plugins/ENB*", "Data/KiLoader/Plugins/KiENBExtender*"]

    /// Recettes des trois couches à partir de la collection _SHADERS (vérifiées à l'assemblage).
    public static func recettes(_ shadersRoot: URL) -> [(String, [Source])] {
        let r = shadersRoot
        let mdlss = r.sub("mDLSS - DLSS METALFX").sub("1 - DLSS METALFX (OBLIGATOIRE)")
        let bottled = r.sub("COMMUNITY SHADERS AIO").sub("BOTTLED SHADERS").sub("BOTTLED SHADERS 1.0.13")
        return [
            (COMMUN, [Source(r.sub("KILOADER"), prefix: "Data/", exclude: KILOADER_ENB), Source(mdlss, include: SHARED)]),
            (CS, [Source(mdlss, exclude: SHARED + USER_SETTINGS), Source(bottled, prefix: "Data/", exclude: USER_SETTINGS)]),
            (ENB, [Source(r.sub("ENBSERIES").sub("ENBSERIES 0.505 + DLSS"), exclude: USER_SETTINGS + ENB_INCOMPATIBLES,
                          patches: ENB_PATCHES)]),
        ]
    }

    public static func backupRoot(_ backupDir: URL) -> URL { backupDir.parent.sub("Systemes_sauvegardes") }

    /// Bases construites (dossiers CS, ENB, commun avec leur systeme.json) dans le dossier des systèmes.
    public static func availableBases(_ systemsDir: URL) -> [String: URL] {
        var out: [String: URL] = [:]
        for n in [COMMUN, CS, ENB] where systemsDir.sub(n).sub(INFO).isFile { out[n] = systemsDir.sub(n) }
        return out
    }
}
