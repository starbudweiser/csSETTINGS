// État de la fenêtre et actions (presets CS, presets ENB, système, sauvegardes), comme la classe Main de la version Python.

import AppKit
import CSCore
import SwiftUI

let SYS_NAMES = [Systems.CS: "Community Shaders", Systems.ENB: "ENB"]

@MainActor
final class AppModel: ObservableObject {
    @Published var cfg: Config
    @Published var tab: Int

    // presets CS
    @Published var presets: [Preset] = []
    @Published var active = ""
    @Published var ref: Reference?
    @Published var compats: [String: Compat] = [:]
    @Published var selected: String?

    // presets ENB
    @Published var enbPresets: [Preset] = []
    @Published var enbActive = ""
    @Published var enbSelected: String?

    // système
    @Published var sysname: String?   // système de shaders actif : CS, ENB ou nil (non géré)
    @Published var bases: [String: URL] = [:]
    @Published var sysModes: [String: String] = [:]
    @Published var sysOps: [Systems.Operation] = []
    @Published var sysSelected: Int?
    @Published var sysStatus = ""
    @Published var sysTone: Tone = .info
    @Published var basesInfo = ""
    @Published var sysBusy = false

    // sauvegardes
    @Published var backups: [Preset] = []
    @Published var backupSelected: Int?

    @Published var log: [String] = []
    @Published var running = false
    @Published var showSettings = false
    @Published var nexusDialog: NexusDialogModel?

    lazy var browser = NexusBrowser(model: self)
    private var timer: Timer?

    init(cfg: Config) {
        self.cfg = cfg
        tab = ((cfg.tab % 5) + 5) % 5
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.pollGame() }
        }
    }

    var current: Preset? { presets.first { $0.name == selected } }
    var enbCurrent: Preset? { enbPresets.first { $0.name == enbSelected } }
    var backupCurrent: Preset? { backupSelected.flatMap { $0 < backups.count ? backups[$0] : nil } }
    var gameRoot: URL { gameDir(cfg.csDir) }
    var broot: URL { Systems.backupRoot(cfg.backupDir) }

    func say(_ text: String) { log.append(strftime("HH:mm:ss") + "  " + text) }

    // MARK: Données

    func refresh(select: String? = nil) {
        let keep = select ?? selected
        presets = listPresets(cfg.library)
        active = activePreset(cfg.library)
        ref = gameReference(cfg.csDir)
        if let ref {
            compats = Dictionary(presets.map { ($0.name, checkPreset($0.path, ref)) }, uniquingKeysWith: { a, _ in a })
        } else {
            compats = [:]
        }
        selected = presets.contains { $0.name == keep } ? keep : presets.first?.name
        refreshEnb()
        refreshSystem()
        backups = listBackups(cfg)
        if let b = backupSelected, b >= backups.count { backupSelected = nil }
        if backupSelected == nil, !backups.isEmpty { backupSelected = 0 }
        running = gameRunning()
    }

    func refreshEnb() {
        let keep = enbSelected
        enbPresets = listEnbPresets(cfg.enbLibrary)
        enbActive = activePreset(cfg.enbLibrary)
        enbSelected = enbPresets.contains { $0.name == keep } ? keep : enbPresets.first?.name
    }

    func refreshSystem() {
        let game = gameRoot
        sysname = game.isDir ? Systems.activeSystem(game) : nil
        bases = Systems.availableBases(cfg.systemsDir)
        var lines: [String] = []
        var tone = Tone.info
        if !game.isDir {
            lines.append(L("<b>⚠ Dossier du jeu introuvable</b> : {path}. Vérifiez les réglages et que le disque est branché.",
                           ["path": esc(game.path)]))
            tone = .warning
        } else {
            if let s = sysname {
                lines.append(L("<b>Système actif</b> : {name}", ["name": SYS_NAMES[s] ?? s]))
                tone = .success
            } else {
                lines.append(L("<b>Aucun système géré par csSETTINGS</b> : l'installation actuelle n'est pas encore suivie. "
                               + "Reprenez-la ou choisissez un système ci-dessous."))
            }
            let problems = Systems.prerequis(game)
            if !problems.isEmpty {
                tone = .warning
                lines.append("<b>⚠</b> " + problems.joined(separator: " ; "))
            } else {
                lines.append(L("Skyrim {v} détecté, SKSE présent.", ["v": Systems.gameVersion(game)]))
            }
            let backend = bottleBackend(game)
            if !backend.isEmpty, let want = BACKEND_FOR[sysname ?? ""], backend != want {
                tone = .warning
                if sysname == Systems.ENB {
                    lines.append(L("<b>⚠ Backend graphique : {b}</b>. ENB rend correctement sous DXVK ; sous DXMT, la teinte est "
                                   + "faussée (dominante verte). Dans CrossOver : bouteille › Réglages avancés › Graphismes › DXVK.",
                                   ["b": backend.uppercased()]))
                } else {
                    lines.append(L("<b>⚠ Backend graphique : {b}</b>. Community Shaders (Bottled) a besoin de DXMT : sans lui, pas "
                                   + "de pont DLSS → MetalFX. Dans CrossOver : bouteille › Réglages avancés › Graphismes › DXMT.",
                                   ["b": backend.uppercased()]))
                }
            } else if !backend.isEmpty {
                lines.append(L("Backend graphique : {b}.", ["b": backend.uppercased()]))
            }
            for layer in Systems.installed(game) {
                guard let v = try? Systems.verify(game, layer) else { continue }
                let state = v.absents.isEmpty && v.modified.isEmpty ? L("intact")
                    : L("{m} modifié(s), {a} absent(s) depuis la pose", ["m": v.modified.count, "a": v.absents.count])
                lines.append("• \(layer) : \(state)")
            }
        }
        sysStatus = lines.joined(separator: "<br>")
        sysTone = tone

        var modes: [String: String] = [:]
        for name in [Systems.CS, Systems.ENB] {
            if bases[name] == nil { modes[name] = "absent" }
            else if sysname == name { modes[name] = "actif" }
            else if sysname == nil, game.isDir, Systems.adoptable(game, bases[name]!) { modes[name] = "adopt" }
            else { modes[name] = "swap" }
        }
        sysModes = modes
        if bases.isEmpty {
            basesInfo = L("Aucune base neutre construite : cliquez sur « Reconstruire les bases… ».")
        } else {
            basesInfo = [Systems.COMMUN, Systems.CS, Systems.ENB].compactMap { n in
                bases[n].map { d in
                    let j = JSON.readObject(d.sub(Systems.INFO))
                    return L("<b>{name}</b> : {n} fichiers, construite le {date}",
                             ["name": n, "n": j["fichiers"]?.pyStr ?? "?", "date": j["date"]?.pyStr ?? "?"])
                }
            }.joined(separator: "<br>")
        }
        sysOps = Systems.listOperations(broot)
        if let s = sysSelected, s >= sysOps.count { sysSelected = nil }
    }

    func sysLabel(_ name: String) -> String {
        let n = SYS_NAMES[name] ?? name
        switch sysModes[name] {
        case "absent": return L("{name} : base absente", ["name": n])
        case "actif": return L("✓ {name} (actif)", ["name": n])
        case "adopt": return L("Reprendre l'installation actuelle ({name})", ["name": n])
        default: return sysname != nil ? L("Passer à {name}", ["name": n]) : L("Installer {name}", ["name": n])
        }
    }

    /// Jeu lancé ? Vérifié toutes les 3 secondes, hors du fil de l'interface.
    func pollGame() {
        DispatchQueue.global(qos: .utility).async {
            let r = gameRunning()
            DispatchQueue.main.async { MainActor.assumeIsolated { if self.running != r { self.running = r } } }
        }
    }

    @discardableResult
    func gameState() -> Bool {
        running = gameRunning()
        return running
    }

    // MARK: Presets CS

    func ppWhy(_ c: Compat) -> String {
        c.ppRejected.map { r -> String in
            switch r {
            case "composite": return L("étape Composite absente")
            case "unknown": return L("effets inconnus : {list}", ["list": c.unknownPP.joined(separator: ", ")])
            default: return L("preset fait pour CS {pv}", ["pv": c.presetVersion])
            }
        }.joined(separator: " ; ")
    }

    func apply() {
        guard let p = current, !gameState(), sysname != Systems.ENB, !sysBusy else { return }
        let c = compats[p.name]
        let v = ref?.version ?? ""
        if let c, c.frameGen, !Dialog.yes(L("« {name} » force la Frame Generation de Community Shaders, qui fait planter le jeu sous "
                                            + "CrossOver. Appliquer quand même ? La configuration en place est sauvegardée avant.",
                                            ["name": p.name])) { return }
        if let c, !c.ppRejected.isEmpty, !Dialog.yes(L("Le post-traitement de « {name} » sera ignoré : votre Community Shaders {v} "
                                                      + "rejettera sa chaîne ({why}) et la remplacera par une chaîne vide. Appliquer "
                                                      + "quand même ? La configuration en place est sauvegardée avant.",
                                                      ["name": p.name, "v": v, "why": ppWhy(c)])) { return }
        if let c, !c.unknownFeatures.isEmpty || (!c.unknownPP.isEmpty && c.ppRejected.isEmpty),
           !Dialog.yes(L("« {name} » utilise des réglages que votre Community Shaders ne connaît pas ({list}). Ils seront ignorés. "
                         + "Appliquer quand même ? La configuration en place est sauvegardée avant.",
                         ["name": p.name, "list": (c.unknownFeatures + c.unknownPP).joined(separator: ", ")])) { return }
        do {
            let saved = try applyPreset(cfg, p.path, label: p.name)
            say(L("Preset « {name} » appliqué. Sauvegarde de l'ancienne configuration : {path}", ["name": p.name, "path": saved.path]))
        } catch CoreError.notFound {
            Dialog.warn(L("Dossier Community Shaders introuvable : {path}. Vérifiez les réglages et que le disque est branché.",
                          ["path": cfg["cs_dir"]]))
            return
        } catch {
            Dialog.warn(L("Impossible d'appliquer « {name} » ({err}).", ["name": p.name, "err": errText(error)]))
            return
        }
        refresh(select: p.name)
    }

    func restore() {
        guard let b = backupCurrent, !gameState() else { return }
        do {
            let saved = try applyPreset(cfg, b.path, label: nil)
            try? Data(L("sauvegarde {name}", ["name": b.name]).utf8).write(to: cfg.library.sub(STATE))
            say(L("Sauvegarde {name} restaurée (configuration remplacée sauvegardée dans {path}).", ["name": b.name, "path": saved.path]))
        } catch CoreError.notFound {
            Dialog.warn(L("Dossier Community Shaders introuvable : {path}. Vérifiez les réglages et que le disque est branché.",
                          ["path": cfg["cs_dir"]]))
        } catch {
            Dialog.warn(L("Échec : {err}", ["err": errText(error)]))
        }
        refresh()
    }

    func saveCurrentConfig() {
        guard let name = Dialog.ask(L("Nom du nouveau preset :"), L("Mon réglage %Y-%m-%d").replacingOccurrences(of: "%Y-%m-%d", with: strftime("yyyy-MM-dd"))) else { return }
        do {
            let dest = try saveCurrent(cfg, name: name)
            say(L("Configuration actuelle enregistrée : {path}", ["path": dest.path]))
            refresh(select: dest.name)
        } catch CoreError.exists {
            Dialog.warn(L("Un preset porte déjà ce nom."))
        } catch {
            Dialog.warn(L("Échec : {err}", ["err": errText(error)]))
        }
    }

    func removeCurrent() {
        guard let p = current,
              Dialog.yes(L("Retirer « {name} » de la bibliothèque ? Il est déplacé dans le dossier des sauvegardes, pas effacé.",
                           ["name": p.name])) else { return }
        do {
            let dest = try removePreset(cfg, p.path)
            say(L("« {name} » déplacé dans {path}", ["name": p.name, "path": dest.path]))
        } catch {
            Dialog.warn(L("Échec : {err}", ["err": errText(error)]))
        }
        refresh()
    }

    func importFrom(_ source: URL) {
        guard let name = Dialog.ask(L("Nom du preset :"), source.isDir ? source.name : source.stem) else { return }
        let cfg = cfg
        say(L("Import de {src}…", ["src": source.name]))
        Jobs.run({ _ in try importSource(cfg, source, name: name) }, done: { [self] made in
            say(L("Importé : {names}", ["names": made.map(\.name).joined(separator: ", ")]))
            refresh(select: made.first?.name)
            warnImported(made)
        }, failed: { e in
            if isLookup(e) {
                Dialog.warn(L("Aucun preset Community Shaders trouvé dans « {src} » : il faut un SettingsUser.json ou un dossier "
                              + "PostProcessing.", ["src": source.name]))
            } else {
                Dialog.warn(L("Impossible de lire « {src} » ({err}). Vérifiez que l'archive n'est pas protégée par un mot de passe.",
                              ["src": source.name, "err": errText(e)]))
            }
        })
    }

    func importArchive() { if let f = Dialog.archive(L("Choisir une archive")) { importFrom(f) } }

    func importFolder() {
        if let d = Dialog.folder(L("Choisir un dossier"), NSHomeDirectory() + "/Downloads") { importFrom(d) }
    }

    func drop(_ urls: [URL]) {
        for u in urls where u.isDir || isArchive(u) { importFrom(u) }
    }

    func warnImported(_ made: [URL]) {
        for path in made {
            guard let c = compats[path.name] else { continue }
            if c.frameGen { say(L("⚠ « {name} » force la Frame Generation : le jeu plantera sous CrossOver.", ["name": path.name])) }
            if !c.ppRejected.isEmpty {
                say(L("⚠ « {name} » : post-traitement ignoré par votre Community Shaders ({why}).", ["name": path.name, "why": ppWhy(c)]))
            }
            if !c.unknownFeatures.isEmpty || (!c.unknownPP.isEmpty && c.ppRejected.isEmpty) {
                say(L("⚠ « {name} » : features inconnues de votre Community Shaders, elles seront ignorées ({list}).",
                      ["name": path.name, "list": (c.unknownFeatures + c.unknownPP).joined(separator: ", ")]))
            }
        }
    }

    func webImported(_ made: [URL]) {
        say(L("Ajouté depuis Nexus : {names}", ["names": made.map(\.name).joined(separator: ", ")]))
        refresh(select: made.last?.name)
        warnImported(made)
    }

    func fromNexus(_ url: String = "") { nexusDialog = NexusDialogModel(model: self, url: url) }

    func nexusDialogClosed(_ d: NexusDialogModel) {
        nexusDialog = nil
        if !d.created.isEmpty { webImported(d.created) }
    }

    // MARK: Presets ENB

    func applyEnb() {
        guard let p = enbCurrent, !gameState(), sysname == Systems.ENB, !sysBusy else { return }
        do {
            let saved = try applyEnbPreset(cfg, p.path, label: p.name)
            say(L("Preset ENB appliqué : {name}. Ancienne config sauvegardée dans {saved}", ["name": p.name, "saved": saved.name]))
        } catch {
            Dialog.warn(L("Impossible d'appliquer « {name} » ({err}).", ["name": p.name, "err": errText(error)]))
            return
        }
        refresh()
    }

    func saveEnb() {
        guard let name = Dialog.ask(L("Nom du preset ENB à enregistrer :")) else { return }
        do {
            let dest = try saveCurrentEnb(cfg, name: name)
            say(L("Preset ENB enregistré : {name}", ["name": dest.name]))
            refresh()
        } catch CoreError.exists {
            Dialog.warn(L("Un preset ENB porte déjà ce nom."))
        } catch {
            Dialog.warn(L("Aucun enbseries.ini à la racine du jeu : rien à enregistrer."))
        }
    }

    // MARK: Système

    /// Lance une opération longue hors du fil de l'interface, une seule à la fois.
    func sysRun<T>(_ work: @escaping @Sendable () throws -> T, then: @escaping (T) -> Void) {
        sysBusy = true
        say(L("Opération en cours… ne fermez pas l'application ni le disque."))
        Jobs.run({ _ in try work() }, done: { [self] v in
            sysBusy = false
            then(v)
        }, failed: { [self] e in
            sysBusy = false
            say(L("✕ {err}", ["err": errText(e)]))
            Dialog.warn(L("L'opération a échoué : {err}. Le jeu a été remis dans son état d'avant si l'échec est survenu en cours de "
                          + "route ; les sauvegardes sont dans {dir}.", ["err": errText(e), "dir": broot.path]))
            refresh()
        })
    }

    /// Fonction « le jeu tourne-t-il ? » à donner au moteur, ou nil si l'utilisateur annule. Si un processus ressemble au jeu,
    /// il est montré et l'utilisateur peut affirmer que le jeu est fermé (seul CrossOver ouvert).
    func sysGuard() -> (@Sendable () -> Bool)? {
        let procs = gameProcesses()
        guard let first = procs.first else { return { gameRunning() } }
        guard Dialog.yes(L("Un processus ressemble au jeu : {proc}. Si Skyrim est bien fermé (seul CrossOver est ouvert), continuer "
                           + "quand même ?", ["proc": first.args])) else { return nil }
        return { false }
    }

    func sysGo(_ target: String) {
        let mode = sysModes[target]
        guard mode == "swap" || mode == "adopt", !sysBusy, let running = sysGuard(), let base = bases[target] else { return }
        let game = gameRoot, bases = bases, cur = sysname, broot = broot
        let name = SYS_NAMES[target] ?? target
        sysRun({ Systems.planSwap(game, current: cur, target: target, base: base) }, then: { [self] pl in
            let text: String
            if mode == "adopt" {
                text = L("Reprendre l'installation actuelle comme « {name} » : {n} fichiers identiques à la base seront suivis (rien "
                         + "n'est recopié ni modifié). Ils seront retirés avec ce système lors d'un échange.",
                         ["name": name, "n": pl.identical])
            } else {
                text = L("Passer à « {name} » ?\n\n• {r} fichier(s) de l'ancien système retirés, dont {a} modifiés depuis la pose "
                         + "(mis de côté dans la sauvegarde)\n• {add} fichier(s) ajoutés, {rep} remplacés (originaux sauvegardés)"
                         + "\n\nSauvegardes : {dir}",
                         ["name": name, "r": pl.remove, "a": pl.aside.count, "add": pl.add, "rep": pl.replace, "dir": broot.path])
            }
            guard Dialog.yes(text) else { return }
            sysRun({ () -> [URL] in
                if mode == "adopt" {
                    var ops: [URL] = []
                    if let commun = bases[Systems.COMMUN], !Systems.installed(game).contains(Systems.COMMUN) {
                        ops.append(try Systems.install(game, Systems.COMMUN, commun, broot, isRunning: running, adopt: true))
                    }
                    ops.append(try Systems.install(game, target, base, broot, isRunning: running, adopt: true))
                    return ops
                }
                return try Systems.swap(game, current: cur, target: target, bases: bases, broot, isRunning: running)
            }, then: { [self] _ in
                say(L("Système « {name} » en place. Sauvegardes : {dir}", ["name": name, "dir": broot.path]))
                refresh()
            })
        })
    }

    func sysRemove() {
        guard let cur = sysname, !sysBusy, let running = sysGuard() else { return }
        guard Dialog.yes(L("Retirer le système « {name} » ? Ce que vous avez modifié est mis de côté dans la sauvegarde et les "
                           + "fichiers d'origine remplacés sont remis. Sans système, le jeu n'aura plus de shaders de rendu.",
                           ["name": cur])) else { return }
        let game = gameRoot, broot = broot
        sysRun({ try Systems.remove(game, cur, broot, isRunning: running) }, then: { [self] _ in
            say(L("Système « {name} » retiré. Sauvegardes : {dir}", ["name": cur, "dir": broot.path]))
            refresh()
        })
    }

    func sysRebuild() {
        guard !sysBusy else { return }
        let root = cfg.systemsDir
        let shaders = root.parent
        guard Dialog.yes(L("Reconstruire les bases neutres à partir de {src} ? Les bases actuelles sont mises de côté (dossier "
                           + "_anciennes), jamais supprimées.", ["src": shaders.path])) else { return }
        sysRun({ () -> [(String, Int)] in
            let stamp = strftime("yyyy-MM-dd_HHmmss")
            let recipes = Systems.recettes(shaders)
            for (_, srcs) in recipes {   // tout vérifier avant de déplacer quoi que ce soit
                for s in srcs where !s.path.isDir {
                    throw Systems.Failure(L("Paquet introuvable : {path}", ["path": s.path.path]))
                }
            }
            let fm = FileManager.default
            try fm.createDirectory(at: root, withIntermediateDirectories: true)
            var made: [(String, Int)] = []
            for (n, srcs) in recipes {
                if root.sub(n).exists {
                    try fm.createDirectory(at: root.sub("_anciennes"), withIntermediateDirectories: true)
                    try fm.moveItem(at: root.sub(n), to: root.sub("_anciennes").sub("\(stamp)_\(n)"))
                }
                made.append((n, try Systems.assemble(root.sub(n), srcs, name: n)))
            }
            return made
        }, then: { [self] made in
            say(L("Bases reconstruites : {list}", ["list": made.map { "\($0.0) (\($0.1))" }.joined(separator: ", ")]))
            refresh()
        })
    }

    func opLabel(_ type: String) -> String {
        ["install": L("Installation"), "remove": L("Retrait"), "drop": L("Retrait de fichiers")][type] ?? type
    }

    func statusLabel(_ s: String) -> String {
        ["en cours": L("en cours"), "terminé": L("terminé"), "annulé": L("annulé")][s] ?? s
    }

    // MARK: Réglages

    func saveSettings(_ new: Config) {
        let langChanged = new["lang"] != cfg["lang"]
        cfg = new
        cfg.tab = tab
        try? cfg.save()
        try? FileManager.default.createDirectory(at: cfg.library, withIntermediateDirectories: true)
        refresh()
        if langChanged { Dialog.info(L("La nouvelle langue s'appliquera au prochain lancement.")) }
    }

    func saveOnQuit() {
        cfg.tab = tab
        try? cfg.save()
    }
}
