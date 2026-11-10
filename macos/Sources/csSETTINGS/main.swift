// Point d'entrée : fenêtre AppKit unique (1100 × 680, redimensionnable) qui héberge l'interface SwiftUI.
//
// Essais : CSSETTINGS_QUIET=1 lance l'appli sans prendre le focus ; CSSETTINGS_TAB=<0…4> ouvre un onglet ;
// CSSETTINGS_SNAPSHOT=<fichier.png> enregistre la fenêtre après 3 s et quitte ; CSSETTINGS_CONFIG=<config.json> utilise
// d'autres réglages (essais sur une copie, sans toucher au jeu).

import AppKit
import CSCore
import SwiftUI

let WINDOW_SIZE = NSSize(width: 1100, height: 680)
let env = ProcessInfo.processInfo.environment

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    var model: AppModel!

    func applicationDidFinishLaunching(_ notification: Notification) {
        Socle.apply()
        Socle.brand(APP, color: BRAND_COLOR)
        var cfg = Config.load()
        if let t = env["CSSETTINGS_TAB"].flatMap(Int.init) { cfg.tab = t }
        if cfg.library.parent.isDir { try? FileManager.default.createDirectory(at: cfg.library, withIntermediateDirectories: true) }
        model = AppModel(cfg: cfg)
        buildMenu()

        window = NSWindow(contentRect: NSRect(origin: .zero, size: WINDOW_SIZE),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = APP
        let host = NSHostingView(rootView: ContentView(model: model))
        host.sizingOptions = []   // la fenêtre garde sa taille : le contenu ne l'agrandit pas
        window.contentView = host
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.backgroundColor = NSColor(Socle.C.bg)
        window.contentMinSize = NSSize(width: 980, height: 600)
        window.setContentSize(WINDOW_SIZE)
        window.setFrameAutosaveName("csSETTINGS.main")
        if window.frame.origin == .zero { window.socleCenter() }
        if env["CSSETTINGS_QUIET"] != nil {
            window.orderBack(nil)
        } else {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate()
        }

        UpdateEngine.shared.configure(repo: APP, lang: { I18n.lang }, brandName: APP)
        UpdateEngine.shared.autoInstall = { UpdateSettings.autoInstall }
        UpdateEngine.shared.canInstall = { [weak self] in Jobs.active == 0 && !(self?.model.sysBusy ?? false) }
        UpdateEngine.shared.start()   // nouvelle version ? (au plus une fois par jour)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { UpdateEngine.shared.installAppMenuItem() }

        if let script = env["CSSETTINGS_SCRIPT"] { runScript(script) }
        if let out = env["CSSETTINGS_SNAPSHOT"] {
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [self] in
                let view = window.contentView!
                if let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
                    view.cacheDisplay(in: view.bounds, to: rep)
                    try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: out))
                }
                NSApp.terminate(nil)
            }
        }
    }

    /// Essais scriptés : « import:<chemin>;select:<nom>;apply;restore;sys:CS;enb;tab:<n>;snap:<fichier>;quit », une étape
    /// toutes les 1,5 s, réponses automatiques aux dialogues.
    func runScript(_ script: String) {
        Dialog.auto = model
        var steps = script.split(separator: ";").map(String.init)
        func next() {
            guard !steps.isEmpty else { return }
            if model.sysBusy || Jobs.active > 0 {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { next() }
                return
            }
            let step = steps.removeFirst()
            let (cmd, arg) = step.firstIndex(of: ":").map { (String(step[..<$0]), String(step[step.index(after: $0)...])) } ?? (step, "")
            switch cmd {
            case "import": model.importFrom(URL.path(arg))
            case "select": model.selected = arg
            case "apply": model.apply()
            case "backup": model.backupSelected = Int(arg) ?? 0
            case "restore": model.restore()
            case "save": model.saveCurrentConfig()
            case "remove": model.removeCurrent()
            case "sys": model.sysGo(arg)
            case "sysoff": model.sysRemove()
            case "enb": model.applyEnb()
            case "enbsave": model.saveEnb()
            case "tab": model.tab = Int(arg) ?? 0
            case "settings": model.showSettings = true
            case "nexus": model.fromNexus(arg)
            case "about": About.show()
            case "snap":
                if let view = (window.attachedSheet ?? window).contentView, let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
                    view.cacheDisplay(in: view.bounds, to: rep)
                    try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: arg))
                }
            case "log": try? model.log.joined(separator: "\n").write(toFile: arg, atomically: true, encoding: .utf8)
            case "quit": NSApp.terminate(nil)
            default: model.say("? \(step)")
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { next() }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { next() }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if model.sysBusy {
            Dialog.warn(L("Opération en cours… ne fermez pas l'application ni le disque."))
            return .terminateCancel
        }
        model.saveOnQuit()
        return .terminateNow
    }

    @objc func showAbout(_ sender: Any?) { About.show() }
    @objc func showSettings(_ sender: Any?) { model.showSettings = true }

    private func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        // Pas de couleur dans les menus : le nom de l'appli y est en texte normal
        appMenu.addItem(withTitle: L("À propos de {app}", ["app": APP]), action: #selector(showAbout), keyEquivalent: "").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: L("Réglages…"), action: #selector(showSettings), keyEquivalent: ",").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: L("Masquer {app}", ["app": APP]), action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let others = appMenu.addItem(withTitle: L("Masquer les autres"), action: #selector(NSApplication.hideOtherApplications(_:)),
                                     keyEquivalent: "h")
        others.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(withTitle: L("Tout afficher"), action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: L("Quitter {app}", ["app": APP]), action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        main.addItem(appItem)

        // Édition : coller la clé d'API, copier le journal…
        let editItem = NSMenuItem()
        let editMenu = NSMenu(title: L("Édition"))
        editMenu.addItem(withTitle: L("Couper"), action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: L("Copier"), action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: L("Coller"), action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: L("Tout sélectionner"), action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = editMenu
        main.addItem(editItem)

        let winItem = NSMenuItem()
        let winMenu = NSMenu(title: L("Fenêtre"))
        winMenu.addItem(withTitle: L("Réduire"), action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        winItem.submenu = winMenu
        main.addItem(winItem)
        NSApp.mainMenu = main
        NSApp.windowsMenu = winMenu
    }
}

if let p = env["CSSETTINGS_CONFIG"] { Config.file = URL.path(p) }
let startCfg = Config.load()
I18n.setLang(startCfg["lang"] == "auto" || I18n.langs[startCfg["lang"]] == nil ? I18n.systemLang() : startCfg["lang"])

MainActor.assumeIsolated {
    let app = NSApplication.shared
    let delegate = AppDelegate()
    app.delegate = delegate
    app.setActivationPolicy(.regular)
    app.run()
}
