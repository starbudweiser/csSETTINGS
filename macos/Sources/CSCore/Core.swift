// Bibliothèque de presets Community Shaders : lister, appliquer, sauvegarder, restaurer, importer.
//
// Un preset est un dossier de la bibliothèque qui reproduit le contenu de Data/SKSE/Plugins/CommunityShaders :
// SettingsUser.json et/ou des fichiers PostProcessing, plus les dossiers de l'éditeur CS (Weathers, ImageSpaces…).
// Un fichier preset.json facultatif décrit sa source. Sans interface.

import Foundation

public enum CoreError: Error, CustomStringConvertible {
    case notFound(String)   // FileNotFoundError
    case exists(String)     // FileExistsError
    case lookup(String)     // LookupError : pas de preset dans la source
    case value(String)      // ValueError
    case runtime(String)    // RuntimeError

    public var description: String {
        switch self {
        case .notFound(let s), .exists(let s), .lookup(let s), .value(let s), .runtime(let s): return s
        }
    }
}

// MARK: - Réglages

public struct Config: Equatable {
    public static var file = URL.path(NSHomeDirectory()).sub("Library/Application Support/csSETTINGS/config.json")

    public static let defaults: [(String, String)] = [
        ("library", "/Volumes/SKYRIM/MODS COLLECTION/_SHADERS/_SHADER PRESETS/CS PRESETS"),
        ("cs_dir", "/Volumes/SAMSUNG T7/VIRTUAL MACHINES/Crossover/Skyrim-MetalFX/drive_c/Games/"
            + "Skyrim Special Edition/Data/SKSE/Plugins/CommunityShaders"),
        ("backup_dir", "/Volumes/SAMSUNG T7/VIRTUAL MACHINES/Crossover/_RETIRES_Skyrim-MetalFX/CS_presets_sauvegardes"),
        ("enb_library", "/Volumes/SKYRIM/MODS COLLECTION/_SHADERS/_SHADER PRESETS/ENB PRESETS"),
        ("systems_dir", "/Volumes/SKYRIM/MODS COLLECTION/_SHADERS/_SYSTEMES"),   // bases neutres CS / ENB / commun
        ("lang", "auto"),
    ]
    public static func defaultValue(_ key: String) -> String { defaults.first { $0.0 == key }?.1 ?? "" }

    public var values: JObject

    public init(_ values: [String: String] = [:]) {
        var o = JObject()
        for (k, v) in Config.defaults { o[k] = .string(v) }
        for (k, v) in values { o[k] = .string(v) }
        self.values = o
    }

    public subscript(key: String) -> String {
        get { values[key]?.string ?? (values[key].map(\.pyStr) ?? Config.defaultValue(key)) }
        set { values[key] = .string(newValue) }
    }

    /// cfg.get(key) or DEFAULTS[key]
    public func orDefault(_ key: String) -> String {
        let v = self[key]
        return v.isEmpty ? Config.defaultValue(key) : v
    }

    public var library: URL { .path(self["library"]) }
    public var csDir: URL { .path(self["cs_dir"]) }
    public var backupDir: URL { .path(self["backup_dir"]) }
    public var enbLibrary: URL { .path(orDefault("enb_library")) }
    public var systemsDir: URL { .path(orDefault("systems_dir")) }
    public var tab: Int {
        get { values["tab"]?.int ?? 0 }
        set { values["tab"] = .int(newValue) }
    }

    public static func load() -> Config {
        var c = Config()
        if let o = JSON.read(file)?.object { c.values.update(o) }
        return c
    }

    public func save() throws {
        try mkdirs(Config.file.parent)
        try JSON.object(values).write(to: Config.file, indent: 2)
    }
}

// MARK: - Presets

public let SETTINGS = "SettingsUser.json"
public let PP = "PostProcessing"
public let EDITOR = ["Weathers", "ImageSpaces", "SceneSettings", "Volumetric Lighting", "EditorSettings.json"]
public let META = "preset.json"
/// Partie ENB facultative d'un preset (Effects 11) : ENB/enbseries.ini et ENB/enbseries/, posés à la racine du jeu
public let ENB_DIR = "ENB"
let ENB_ITEMS = ["enbseries.ini", "enbseries"]
let ENB_CACHE = "enbcache"   // à la racine du jeu, supprimé à chaque nouveau preset ENB (recréé au lancement)
public let STATE = ".preset_actif"
/// Caches propres à une machine : jamais copiés depuis une archive
public let SKIP = ["UnifiedWaterCache", "UWLoadOrder.hash", "ShaderCache", ".DS_Store"]
public let ARCHIVES = ["zip", "7z", "rar"]

public func isArchive(_ url: URL) -> Bool { ARCHIVES.contains(url.pathExtension.lowercased()) }

public struct Preset: Equatable, Identifiable {
    public var id: String { path.path }
    public var name: String
    public var path: URL
    public var version = ""
    public var hasSettings = false
    public var ppFiles: [String] = []
    public var editor: [String] = []
    public var meta = JObject()
    public var hasEnb = false

    public func metaText(_ key: String) -> String {
        guard let v = meta[key], v != .null else { return "" }
        return v.pyStr
    }
}

func settingsVersion(_ settings: URL) -> String {
    guard let v = JSON.read(settings)?["Version"] else { return "" }
    return v.pyStr.replacingOccurrences(of: "-", with: ".")
}

public func readPreset(_ path: URL) -> Preset {
    var p = Preset(name: path.name, path: path)
    let s = path.sub(SETTINGS)
    p.hasSettings = s.isFile
    p.version = p.hasSettings ? settingsVersion(s) : ""
    let pp = path.sub(PP)
    p.ppFiles = pp.isDir ? pySorted(children(pp).filter { $0.name.hasSuffix(".json") }.map(\.name)) : []
    p.editor = EDITOR.filter { path.sub($0).exists }
    p.hasEnb = path.sub(ENB_DIR).sub("enbseries.ini").isFile
    p.meta = JSON.read(path.sub(META))?.object ?? JObject()
    return p
}

func sortedByLowerName(_ dirs: [URL]) -> [URL] {
    dirs.sorted { $0.name.lowercased().unicodeScalars.lexicographicallyPrecedes($1.name.lowercased().unicodeScalars) }
}

public func listPresets(_ library: URL) -> [Preset] {
    guard library.isDir else { return [] }
    return sortedByLowerName(children(library)).filter {
        $0.isDir && !$0.name.hasPrefix(".") && ($0.sub(SETTINGS).isFile || $0.sub(PP).isDir)
    }.map(readPreset)
}

public func activePreset(_ library: URL) -> String {
    (readText(library.sub(STATE)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
}

// MARK: - Jeu

/// Processus du jeu (pid, ligne de commande) dans une sortie de « ps -axo pid=,args= ». Compte seulement un processus
/// dont l'exécutable lancé est SkyrimSE.exe (chemin Windows de Wine, ou Wine suivi de ce chemin) : un shell, un script
/// ou un outil qui cite « SkyrimSE.exe » dans ses arguments, ou un simple CrossOver ouvert, ne comptent pas.
public func parseGameProcesses(_ ps: String, ownPid: Int32 = getpid()) -> [(pid: Int, args: String)] {
    var out: [(Int, String)] = []
    for raw in ps.split(separator: "\n", omittingEmptySubsequences: false) {
        let line = raw.drop { $0 == " " || $0 == "\t" }
        guard let sp = line.firstIndex(where: { $0 == " " || $0 == "\t" }), let pid = Int(line[..<sp]), pid != Int(ownPid) else { continue }
        let args = String(line[sp...].drop { $0 == " " || $0 == "\t" })
        let low = args.lowercased()
        guard let r = low.range(of: ".exe") else { continue }
        let exe = low[..<r.upperBound].split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? ""
        guard exe == "skyrimse.exe" else { continue }
        let firstToken = args.split(whereSeparator: { $0.isWhitespace }).first.map(String.init) ?? ""
        let first = (firstToken.replacingOccurrences(of: "\\", with: "/").split(separator: "/", omittingEmptySubsequences: false).last
            .map(String.init) ?? "").lowercased()
        let drive = args.range(of: #"^[a-zA-Z]:[\\/]"#, options: .regularExpression) != nil
        if drive || first.contains("wine") || first == "skyrimse.exe" { out.append((pid, String(args.prefix(120)))) }
    }
    return out
}

public func gameProcesses() -> [(pid: Int, args: String)] {
    let r = run("/bin/ps", ["-axo", "pid=,args="], timeout: 5)
    return r.code == 0 ? parseGameProcesses(r.out) : []
}

/// Vrai si SkyrimSE.exe tourne (dans CrossOver, c'est un processus Wine dont les arguments nomment l'exécutable).
public func gameRunning() -> Bool { !gameProcesses().isEmpty }

/// Racine du jeu : CommunityShaders → Plugins → SKSE → Data → jeu.
public func gameDir(_ csDir: URL) -> URL {
    let p = csDir.standardizedFileURL.parents
    return p.count > 3 ? p[3] : URL.path("/")
}

/// Backend graphique de la bouteille CrossOver (dxmt, dxvk, d3dmetal…), lu dans cxbottle.conf sans rien modifier ;
/// « » si le fichier est introuvable ou muet. cxbottle.conf se trouve dans un dossier parent du jeu.
public func bottleBackend(_ game: URL) -> String {
    for parent in game.parents {
        let conf = parent.sub("cxbottle.conf")
        guard conf.isFile else { continue }
        guard let d = try? Data(contentsOf: conf) else { return "" }
        let text = String(decoding: d, as: UTF8.self)
        let re = try! NSRegularExpression(pattern: #"^\s*"CX_GRAPHICS_BACKEND"\s*=\s*"([^"]*)""#, options: .anchorsMatchLines)
        guard let m = re.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
              let r = Range(m.range(at: 1), in: text) else { return "" }
        return text[r].trimmingCharacters(in: .whitespaces).lowercased()
    }
    return ""
}

/// Backend attendu par système : ENB suit DXVK (rendu fidèle à Windows) ; CS (Bottled) a besoin du pont DLSS → MetalFX de DXMT
public let BACKEND_FOR = ["ENB": "dxvk", "CS": "dxmt"]

// MARK: - Appliquer, sauvegarder

func copyItem(_ src: URL, _ dst: URL) throws {
    if src.isDir { try copyTree(src, dst, ignore: SKIP) } else { try copyFile(src, dst) }
}

/// Copie la configuration CS actuelle (réglages, éditeur, post-traitement) dans dest.
@discardableResult
public func snapshot(_ csDir: URL, _ dest: URL) throws -> URL {
    try mkdirs(dest)
    for name in [SETTINGS, PP] + EDITOR where csDir.sub(name).exists {
        try copyItem(csDir.sub(name), dest.sub(name))
    }
    return dest
}

func writeMeta(_ dest: URL, _ meta: JObject) throws {
    try JSON.object(meta).write(to: dest.sub(META), indent: 2)
}

public func backup(_ cfg: Config, reason: String) throws -> URL {
    let stamp = strftime("yyyy-MM-dd_HHmmss")
    var dest = cfg.backupDir.sub(stamp), n = 2
    while dest.exists {   // deux opérations dans la même seconde : ne jamais écrire dans une sauvegarde
        dest = cfg.backupDir.sub("\(stamp)_\(n)")
        n += 1
    }
    try snapshot(cfg.csDir, dest)
    try writeMeta(dest, JObject([("reason", .string(reason)), ("date", .string(stamp))]))
    return dest
}

/// Sauvegardes, la plus récente d'abord (le dossier _presets_retires n'en est pas une).
public func listBackups(_ cfg: Config) -> [Preset] {
    guard cfg.backupDir.isDir else { return [] }
    return children(cfg.backupDir).reversed().filter { $0.isDir && !$0.name.hasPrefix("_") && !$0.name.hasPrefix(".") }.map(readPreset)
}

/// Sections de SettingsUser.json propres au joueur et à sa machine, pas au rendu d'un preset
public let USER_SECTIONS = ["Menu", "Advanced"]

/// Applique un preset. Sauvegarde d'abord la configuration actuelle ; renvoie le dossier de sauvegarde.
///
/// Un preset avec SettingsUser.json remplace les réglages et les données de l'éditeur CS.
/// Un preset de post-traitement seul ajoute ses fichiers sans toucher aux réglages.
/// Les préférences du joueur (USER_SECTIONS : raccourcis du menu CS, threads de compilation) sont gardées,
/// sauf pour une restauration de sauvegarde (label nil), qui remet tout tel quel.
@discardableResult
public func applyPreset(_ cfg: Config, _ presetPath: URL, label: String?) throws -> URL {
    let cs = cfg.csDir
    guard cs.isDir else { throw CoreError.notFound(cs.path) }
    let saved = try backup(cfg, reason: "avant \(label ?? presetPath.name)")
    if presetPath.sub(ENB_DIR).sub("enbseries.ini").isFile {
        try applyEnb(cfg, presetPath.sub(ENB_DIR), saved.sub(ENB_DIR))
    }
    if presetPath.sub(SETTINGS).isFile {
        for e in EDITOR { try rmItem(cs.sub(e)) }
        for item in children(presetPath) {
            // seulement ce que Community Shaders lit : pas de notes, d'aperçus ni de partie ENB
            guard ([SETTINGS, "Overrides"] + EDITOR).contains(item.name) else { continue }
            let t = cs.sub(item.name)
            if t.isDir { try rmItem(t) }
            try copyItem(item, t)
        }
        if label != nil { try keepUserSections(cs.sub(SETTINGS), saved.sub(SETTINGS)) }
    }
    if presetPath.sub(PP).isDir {
        try mkdirs(cs.sub(PP))
        for f in children(presetPath.sub(PP)) where f.isFile && !f.name.hasPrefix(".") {
            try copyFile(f, cs.sub(PP).sub(f.name))
        }
    }
    if let label { try writeText(label, cfg.library.sub(STATE)) }
    return saved
}

/// Remet dans le SettingsUser.json appliqué les sections USER_SECTIONS de la configuration d'avant.
func keepUserSections(_ settings: URL, _ previous: URL) throws {
    let old = JSON.readObject(previous)
    var new = JSON.readObject(settings)
    var kept = JObject()
    for k in USER_SECTIONS { if let v = old[k], v.object != nil { kept[k] = v } }
    guard !new.isEmpty, !kept.isEmpty else { return }
    new.update(kept)
    try JSON.object(new).write(to: settings, indent: 1)
}

/// Remplace le preset ENB du jeu. L'actuel (enbseries.ini, enbseries/) est déplacé dans la sauvegarde, rien n'est
/// effacé ; restaurer cette sauvegarde le remet en place. Seul le cache enbcache/ est supprimé.
func applyEnb(_ cfg: Config, _ enbSrc: URL, _ enbSaved: URL) throws {
    let root = gameDir(cfg.csDir)
    try mkdirs(enbSaved)
    // le cache d'ENB (shaders compilés avec l'ancien preset) doit être refait : sans cela, l'ancien rendu persiste
    try? rmItem(root.sub(ENB_CACHE))
    for name in ENB_ITEMS where root.sub(name).exists { try moveItem(root.sub(name), enbSaved.sub(name)) }
    for name in ENB_ITEMS where enbSrc.sub(name).exists { try copyItem(enbSrc.sub(name), root.sub(name)) }
    // modules de KiLoader (enbseries/*.dllplugin) : ils appartiennent à l'installation, pas au preset
    let old = enbSaved.sub("enbseries")
    if old.isDir {
        try mkdirs(root.sub("enbseries"))
        for f in children(old) where f.name.hasSuffix(".dllplugin") && !root.sub("enbseries").sub(f.name).exists {
            try copyFile(f, root.sub("enbseries").sub(f.name))
        }
    }
}

public func saveCurrent(_ cfg: Config, name: String) throws -> URL {
    let dest = cfg.library.sub(safeName(name))
    if dest.exists { throw CoreError.exists(dest.path) }
    try snapshot(cfg.csDir, dest)
    try writeMeta(dest, JObject([("source", "config actuelle"), ("date", .string(strftime("yyyy-MM-dd HH:mm")))]))
    try writeText(dest.name, cfg.library.sub(STATE))
    return dest
}

// MARK: - Presets ENB (système ENB)

/// Dossier qui contient enbseries.ini : le preset lui-même, ou son sous-dossier ENB/.
public func enbSource(_ path: URL) -> URL {
    path.sub(ENB_DIR).sub("enbseries.ini").isFile ? path.sub(ENB_DIR) : path
}

public func listEnbPresets(_ library: URL) -> [Preset] {
    guard library.isDir else { return [] }
    return sortedByLowerName(children(library)).compactMap { d in
        guard d.isDir, !d.name.hasPrefix("."), enbSource(d).sub("enbseries.ini").isFile else { return nil }
        var p = Preset(name: d.name, path: d, hasEnb: true)
        p.meta = JSON.read(d.sub(META))?.object ?? JObject()
        let fx = enbSource(d).sub("enbseries")
        p.ppFiles = fx.isDir ? pySorted(children(fx).map(\.name).filter { fnmatch($0, "*.fx*") }) : []
        return p
    }
}

/// Applique un preset ENB (enbseries.ini + enbseries/). La configuration en place est sauvegardée d'abord ;
/// les modules de KiLoader (enbseries/*.dllplugin) sont gardés. Renvoie le dossier de sauvegarde.
@discardableResult
public func applyEnbPreset(_ cfg: Config, _ presetPath: URL, label: String?) throws -> URL {
    let src = enbSource(presetPath)
    guard src.sub("enbseries.ini").isFile else { throw CoreError.value("\(presetPath.path): pas de enbseries.ini") }
    let saved = try backup(cfg, reason: "avant ENB \(label ?? presetPath.name)")
    try applyEnb(cfg, src, saved.sub(ENB_DIR))
    if let label {
        try mkdirs(cfg.enbLibrary)
        try writeText(label, cfg.enbLibrary.sub(STATE))
    }
    return saved
}

/// Range le preset ENB en place (enbseries.ini + enbseries/, sans les modules .dllplugin de l'installation)
/// dans la bibliothèque ENB.
public func saveCurrentEnb(_ cfg: Config, name: String) throws -> URL {
    let lib = cfg.enbLibrary
    let dest = lib.sub(safeName(name))
    if dest.exists { throw CoreError.exists(dest.path) }
    let root = gameDir(cfg.csDir)
    guard root.sub("enbseries.ini").isFile else { throw CoreError.notFound(root.sub("enbseries.ini").path) }
    try mkdirs(dest)
    try copyFile(root.sub("enbseries.ini"), dest.sub("enbseries.ini"))
    if root.sub("enbseries").isDir { try copyTree(root.sub("enbseries"), dest.sub("enbseries"), ignore: SKIP + ["*.dllplugin"]) }
    try writeMeta(dest, JObject([("source", "config ENB actuelle"), ("date", .string(strftime("yyyy-MM-dd HH:mm")))]))
    try writeText(dest.name, lib.sub(STATE))
    return dest
}

/// Retire un preset de la bibliothèque en le déplaçant dans le dossier des sauvegardes (rien n'est effacé).
public func removePreset(_ cfg: Config, _ presetPath: URL) throws -> URL {
    let dest = cfg.backupDir.sub("_presets_retires").sub("\(strftime("yyyy-MM-dd_HHmmss"))_\(presetPath.name)")
    try mkdirs(dest.parent)
    try moveItem(presetPath, dest)
    return dest
}

public func safeName(_ name: String) -> String {
    let bad = Set("/\\:*?\"<>|")
    let keep = String(name.map { bad.contains($0) ? "-" : $0 })
        .trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "."))
    return keep.isEmpty ? "Preset" : keep
}

// MARK: - Compatibilité

public var REFERENCE_FILE: URL { Config.file.parent.sub("reference.json") }
let DEFAULTS_FILE = "SettingsDefault.json"
/// Sections de SettingsUser.json qui ne sont pas des features (toujours présentes)
let CORE_SECTIONS: Set<String> = ["Version", "Advanced", "General", "Menu", "Disable at Boot", "Replace Original Shaders"]

func squash(_ name: String) -> String { String(name.lowercased().filter { $0.isLetter || $0.isNumber }) }

/// Une section (« HiZ Occlusion Culling ») correspond à un fichier de feature (« HiZOcclusion.ini ») si son nom compacté
/// commence ou finit par celui du fichier (« Advanced Skin » ↔ « Skin.ini »).
func featureKnown(_ section: String, _ features: Set<String>) -> Bool {
    let s = squash(section)
    return features.contains { f in s == f || (f.count >= 4 && (s.hasPrefix(f) || s.hasSuffix(f))) }
}

/// Ce que connaît le Community Shaders installé.
public struct Reference: Equatable {
    public var version: String
    public var features: [String]
    public var sections: [(String, [String])]
    public var pp: [String]
    public var csDir: String?

    public static func == (a: Reference, b: Reference) -> Bool {
        a.version == b.version && a.features == b.features && a.pp == b.pp && a.csDir == b.csDir
            && a.sections.map(\.0) == b.sections.map(\.0) && a.sections.map(\.1) == b.sections.map(\.1)
    }

    public func sectionNames() -> [String] { sections.map(\.0) }

    var json: JSON {
        var o = JObject()
        o["version"] = .string(version)
        o["features"] = .strings(features)
        o["sections"] = .object(JObject(sections.map { ($0.0, JSON.strings($0.1)) }))
        o["pp"] = .strings(pp)
        if let csDir { o["cs_dir"] = .string(csDir) }
        return .object(o)
    }

    init(version: String, features: [String], sections: [(String, [String])], pp: [String], csDir: String? = nil) {
        self.version = version; self.features = features; self.sections = sections; self.pp = pp; self.csDir = csDir
    }

    init?(_ j: JObject) {
        guard !j.isEmpty else { return nil }
        version = j["version"]?.pyStr ?? ""
        features = j["features"]?.strings ?? []
        sections = (j["sections"]?.object).map { o in o.map { ($0.0, $0.1.strings) } } ?? []
        pp = j["pp"]?.strings ?? []
        csDir = j["cs_dir"]?.string
    }
}

/// Ce que connaît le Community Shaders installé : features (Data/Shaders/Features/*.ini), sections et options de
/// réglages, effets de post-traitement. nil si le dossier du jeu est introuvable.
///
/// Les sections de SettingsUser.json du jeu ne comptent que si une feature installée leur correspond :
/// un preset incompatible appliqué juste avant ne fausse donc pas la référence.
public func buildReference(_ csDir: URL) -> Reference? {
    let def = JSON.readObject(csDir.sub(DEFAULTS_FILE))
    guard !def.isEmpty else { return nil }
    let parents = csDir.parents
    let featDir = (parents.count > 2 ? parents[2] : csDir).sub("Shaders/Features")   // CommunityShaders → Plugins → SKSE → Data
    let features = Set(children(featDir).filter { $0.name.hasSuffix(".ini") }.map { $0.stem.lowercased() })
    let user = JSON.readObject(csDir.sub(SETTINGS))
    var order: [String] = []
    var sections: [String: Set<String>] = [:]
    for (src, trusted) in [(def, true), (user, false)] {
        for (k, v) in src where trusted || sections[k] != nil || featureKnown(k, features) {
            if sections[k] == nil { order.append(k); sections[k] = [] }
            if let o = v.object { sections[k]!.formUnion(o.keys) }
        }
    }
    let pp = (sections["Post Processing"] ?? []).union(["ppsettings", "preset_name"])
    return Reference(version: (def["Version"]?.pyStr ?? "").replacingOccurrences(of: "-", with: "."),
                     features: pySorted(features), sections: order.map { ($0, pySorted(sections[$0]!)) }, pp: pySorted(pp))
}

/// Référence du jeu, mise en cache par version de CS : elle est relevée une fois, quand la configuration du jeu est
/// saine, puis réutilisée tant que la version de SettingsDefault.json ne change pas.
public func gameReference(_ csDir: URL, cache: URL? = nil) -> Reference? {
    let cache = cache ?? REFERENCE_FILE
    guard var fresh = buildReference(csDir) else { return nil }
    let key = csDir.path
    if var old = Reference(JSON.readObject(cache)), old.version == fresh.version, old.csDir == key {
        // n'ajoute que des features réellement installées depuis (mise à jour partielle de CS)
        old.features = pySorted(Set(old.features).union(fresh.features))
        return old
    }
    fresh.csDir = key
    try? mkdirs(cache.parent)
    try? fresh.json.write(to: cache, indent: 1)
    return fresh
}

public struct Compat: Equatable {
    public enum Level: String { case ok, info, warning }
    public var level: Level = .ok
    public var unknownFeatures: [String] = []   // ignorées par le CS installé
    public var missingFeatures: [String] = []   // absentes du preset : valeurs par défaut
    public var unknownOptions = 0               // options inconnues dans des features connues
    public var unknownPP: [String] = []         // effets de post-traitement inconnus
    /// chaîne « Post Processing » de SettingsUser.json que le CS installé rejettera en entier (il la remplace par une
    /// chaîne vide au lancement) : raisons parmi composite (étape absente), unknown (effets), version
    public var ppRejected: [String] = []
    public var presetVersion = ""
    public var frameGen = false                 // force la Frame Generation : son proxy D3D12 plante le jeu sous CrossOver
}

let PP_META: Set<String> = ["ppsettings", "preset_name"]   // réglages globaux du bloc, pas des étapes de la chaîne
let PP_VERSION_GAP = 4                                     // écart de version mineure jugé « nettement plus ancien »

func versionTuple(_ v: String) -> [Int] {
    let parts = v.replacingOccurrences(of: "-", with: ".").split(separator: ".", omittingEmptySubsequences: false)
    let n = parts.map { Int($0.trimmingCharacters(in: .whitespaces)) }
    return n.contains(nil) ? [] : n.compactMap { $0 }
}

/// Compare un preset au Community Shaders installé (voir gameReference).
public func checkPreset(_ presetPath: URL, _ ref: Reference) -> Compat {
    var sections: [String: Set<String>] = [:]
    for (k, v) in ref.sections { sections[k] = Set(v) }
    let features = Set(ref.features)
    let ppKnown = Set(ref.pp)
    var c = Compat()
    let settings = JSON.readObject(presetPath.sub(SETTINGS))
    if !settings.isEmpty {
        for (k, v) in settings {
            if let known = sections[k] {
                if let o = v.object, k != "Disable at Boot", k != "Post Processing" {
                    c.unknownOptions += Set(o.keys).subtracting(known).count
                }
            } else if !CORE_SECTIONS.contains(k) && !featureKnown(k, features) {
                c.unknownFeatures.append(k)
            }
        }
        // « Disable at Boot » garde les noms de features d'anciens presets (XeGTAO, PhysicalSky…) : un nom inconnu n'y a
        // aucun effet, ce n'est pas une feature manquante du Community Shaders installé.
        c.missingFeatures = ref.sectionNames().filter {
            !settings.contains($0) && !CORE_SECTIONS.contains($0) && featureKnown($0, features)
        }
        c.presetVersion = (settings["Version"]?.pyStr ?? "").replacingOccurrences(of: "-", with: ".")
        if let up = settings["Upscaling"]?.object { c.frameGen = up["frameGenerationForceEnable"]?.truthy ?? false }
        if let pp = settings["Post Processing"]?.object {
            c.unknownPP += pp.keys.filter { !ppKnown.contains($0) }
            if !Set(pp.keys).subtracting(PP_META).isEmpty {
                if ppKnown.contains("Composite") && !pp.contains("Composite") { c.ppRejected.append("composite") }
                if !c.unknownPP.isEmpty { c.ppRejected.append("unknown") }
                let pv = versionTuple(c.presetVersion), rv = versionTuple(ref.version)
                if pv.count >= 2, rv.count >= 2, pv[0] < rv[0] || (pv[0] == rv[0] && rv[1] - pv[1] >= PP_VERSION_GAP) {
                    c.ppRejected.append("version")
                }
            }
        }
    }
    let ppDir = presetPath.sub(PP)
    if ppDir.isDir {
        for f in children(ppDir) where f.name.hasSuffix(".json") {
            let before = c.unknownPP
            c.unknownPP += JSON.readObject(f).keys.filter { !ppKnown.contains($0) && !before.contains($0) }
        }
    }
    if !c.unknownFeatures.isEmpty || !c.unknownPP.isEmpty || !c.ppRejected.isEmpty || c.frameGen {
        c.level = .warning
    } else if !c.missingFeatures.isEmpty || c.unknownOptions > 0 {
        c.level = .info
    }
    return c
}

// MARK: - Import

/// Décompresse .ZIP, .7Z ou .RAR avec bsdtar (libarchive, fourni avec macOS).
public func extract(_ archive: URL, _ dest: URL) throws {
    let r = run("/usr/bin/bsdtar", ["-xf", archive.path, "-C", dest.path], timeout: 1800)
    if r.code != 0 {
        let e = r.err.trimmingCharacters(in: .whitespacesAndNewlines)
        throw CoreError.runtime(e.isEmpty ? "bsdtar" : e)
    }
}

/// Dossiers qui ressemblent à un dossier CommunityShaders : SettingsUser.json ou PostProcessing/*.json.
public func findRoots(_ tree: URL) -> [URL] {
    var roots: [URL] = []
    func walk(_ d: URL) {
        let items = children(d)
        let files = items.filter { !$0.isDir }.map(\.name)
        if files.contains(SETTINGS) || (d.name == PP && files.contains { $0.hasSuffix(".json") }) {
            let root = files.contains(SETTINGS) ? d : d.parent
            if !roots.contains(where: { $0.same(root) }) && !roots.contains(where: { root.inside($0) }) { roots.append(root) }
        }
        for sub in items where sub.isDir && !SKIP.contains(sub.name) { walk(sub) }
    }
    walk(tree.standardizedFileURL)
    return roots
}

/// Ajoute un ou plusieurs presets depuis une archive ou un dossier. Renvoie les dossiers créés.
public func importSource(_ cfg: Config, _ source: URL, name: String, meta: JObject? = nil) throws -> [URL] {
    let tmp = fm.temporaryDirectory.appendingPathComponent("cssettings_" + UUID().uuidString)
    defer { try? fm.removeItem(at: tmp) }
    let tree = tmp.sub("x")
    try mkdirs(tree)
    if source.isFile && isArchive(source) {
        try extract(source, tree)
    } else if source.isDir {
        try copyTree(source, tree.sub(source.name), ignore: SKIP)
    } else {
        throw CoreError.value(source.path)
    }
    let roots = findRoots(tree)
    guard !roots.isEmpty else { throw CoreError.lookup(source.path) }
    var made: [URL] = []
    for (i, root) in roots.enumerated() {
        let sub = roots.count == 1 ? "" : " - " + ([PP, "CommunityShaders"].contains(root.name) ? String(i + 1) : root.name)
        var dest = cfg.library.sub(safeName(name + sub)), n = 2
        while dest.exists {
            dest = cfg.library.sub(safeName("\(name)\(sub) (\(n))"))
            n += 1
        }
        try mkdirs(dest)
        for item in children(root) {
            if SKIP.contains(item.name) || item.name.hasPrefix(".") { continue }
            if ([SETTINGS, PP, "EditorSettings.json"] + EDITOR).contains(item.name) { try copyItem(item, dest.sub(item.name)) }
        }
        var info = meta ?? JObject()
        if info["source"] == nil { info["source"] = .string(source.path) }
        if info["date"] == nil { info["date"] = .string(strftime("yyyy-MM-dd HH:mm")) }
        try writeMeta(dest, info)
        made.append(dest)
    }
    return made
}
