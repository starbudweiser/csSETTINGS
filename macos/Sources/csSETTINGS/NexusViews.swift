// Onglet Nexus (petit navigateur WebKit ouvert sur une recherche de presets) et dialogue « Choisir un fichier de ce mod ».
// Un téléchargement lancé depuis le site (manuel ou « Mod manager download », lien nxm://) est importé dans la bibliothèque.

import CSCore
import SwiftUI
import WebKit

@MainActor
final class NexusBrowser: NSObject, ObservableObject, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    weak var model: AppModel?
    let web: WKWebView
    @Published var address = ""
    @Published var canBack = false
    @Published var canForward = false
    @Published var search = Nexus.searches[0]
    @Published var state = L("Ouvrez la page d'un preset, puis cliquez sur « Mod manager download » ou sur un téléchargement manuel : "
                             + "le fichier est ajouté à la bibliothèque. Aucun réglage du jeu n'est modifié.")
    @Published var tone: Tone = .none
    @Published var progress: Double?   // nil : masquée ; < 0 : indéterminée
    @Published var isModPage = false
    private var loaded = false
    private var observers: [NSKeyValueObservation] = []
    private var pending: [ObjectIdentifier: (dest: URL, mod: String, page: String)] = [:]
    private let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("cssettings_web_" + UUID().uuidString)

    init(model: AppModel) {
        self.model = model
        let conf = WKWebViewConfiguration()
        conf.websiteDataStore = .default()   // cookies et cache gardés : la connexion à Nexus est conservée
        web = WKWebView(frame: .zero, configuration: conf)
        super.init()
        // agent Safari standard : un agent inconnu fait parfois bloquer la page par Cloudflare
        web.customUserAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            + "Version/18.0 Safari/605.1.15"
        web.pageZoom = Socle.scale   // même échelle que l'interface (Socle, 110 %)
        web.navigationDelegate = self
        web.uiDelegate = self
        observers = [
            web.observe(\.url) { [weak self] w, _ in MainActor.assumeIsolated { self?.urlChanged(w.url) } },
            web.observe(\.canGoBack) { [weak self] w, _ in MainActor.assumeIsolated { self?.canBack = w.canGoBack } },
            web.observe(\.canGoForward) { [weak self] w, _ in MainActor.assumeIsolated { self?.canForward = w.canGoForward } },
        ]
    }

    /// La page ne se charge qu'à la première ouverture de l'onglet.
    func appeared() {
        guard !loaded else { return }
        loaded = true
        goSearch()
    }

    func goSearch() {
        let text = search.trimmingCharacters(in: .whitespacesAndNewlines)
        let target = text.isEmpty ? Nexus.searches[0] : text
        let url = target.hasPrefix("http://") || target.hasPrefix("https://") ? URL(string: target) : URL(string: Nexus.searchURL(target))
        if let url { web.load(URLRequest(url: url)) }
    }

    private func urlChanged(_ url: URL?) {
        address = url?.absoluteString ?? ""
        // page d'un mod (…/mods/<numéro>) : on propose de choisir un de ses fichiers
        isModPage = (url?.path ?? "").range(of: #"/mods/\d+"#, options: .regularExpression) != nil
    }

    private func say(_ text: String, _ t: Tone = .none) { state = text; tone = t }

    private var modName: String {
        var title = web.title ?? ""
        for sep in [" at Skyrim", " - Nexus", " | Nexus"] { title = title.components(separatedBy: sep)[0] }
        title = title.trimmingCharacters(in: .whitespaces)
        return title.isEmpty ? "Nexus" : title
    }

    // MARK: Navigation : liens nxm:// détournés, fenêtres surgissantes gardées dans la même vue

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping @MainActor (WKNavigationActionPolicy) -> Void) {
        if let u = action.request.url, u.scheme?.lowercased() == "nxm" {
            decisionHandler(.cancel)
            nxm(u.absoluteString)
            return
        }
        decisionHandler(action.shouldPerformDownload ? .download : .allow)
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping @MainActor (WKNavigationResponsePolicy) -> Void) {
        let disposition = (response.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        decisionHandler(!response.canShowMIMEType || disposition.lowercased().hasPrefix("attachment") ? .download : .allow)
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction,
                 windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let u = action.request.url {
            if u.scheme?.lowercased() == "nxm" { nxm(u.absoluteString) } else { webView.load(action.request) }
        }
        return nil
    }

    // MARK: Téléchargement manuel depuis le site

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String,
                  completionHandler: @escaping @MainActor (URL?) -> Void) {
        guard isArchive(URL(fileURLWithPath: suggestedFilename)) else {
            completionHandler(nil)
            say(L("« {f} » n'est pas une archive .ZIP, .7Z ou .RAR : téléchargement ignoré.", ["f": suggestedFilename]), .warning)
            return
        }
        let dir = tmp.appendingPathComponent(UUID().uuidString)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = dir.appendingPathComponent((suggestedFilename as NSString).lastPathComponent)
        pending[ObjectIdentifier(download)] = (dest, modName, web.url?.absoluteString ?? "")
        observers.append(download.progress.observe(\.fractionCompleted) { [weak self] p, _ in
            let f = p.totalUnitCount > 0 ? p.fractionCompleted : -1
            DispatchQueue.main.async { MainActor.assumeIsolated { self?.progress = f } }
        })
        progress = -1
        say(L("Téléchargement de {f}…", ["f": suggestedFilename]))
        completionHandler(dest)
    }

    func downloadDidFinish(_ download: WKDownload) {
        guard let info = pending.removeValue(forKey: ObjectIdentifier(download)), let model else { return }
        var meta = JObject([("source", "Nexus Mods"), ("mod", .string(info.mod)), ("file", .string(info.dest.name)),
                            ("url", .string(info.page))])
        if let id = try? Nexus.parseModId(info.page) { meta["nexus_id"] = .int(id) }
        let name = String(safeName("\(info.mod) - \(info.dest.stem)").prefix(90))
        let cfg = model.cfg
        runImport { _ in try importSource(cfg, info.dest, name: name, meta: meta) }
    }

    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        pending[ObjectIdentifier(download)] = nil
        progress = nil
        say(L("Téléchargement interrompu."), .danger)
    }

    // MARK: « Mod manager download » : lien nxm:// traité par l'API

    func nxm(_ link: String) {
        guard let info = try? Nexus.parseNxm(link) else { return say(L("Lien de téléchargement non reconnu."), .danger) }
        guard info.game == Nexus.game else { return say(L("Ce fichier n'est pas pour Skyrim Special Edition."), .warning) }
        let key = Nexus.getKey()
        guard !key.isEmpty else { return say(L("Ajoutez d'abord votre clé d'API Nexus dans les réglages."), .warning) }
        guard let cfg = model?.cfg else { return }
        progress = -1
        say(L("Téléchargement depuis Nexus…"))
        let tmp = tmp
        runImport { progress in
            let mod = try Nexus.modInfo(info.modId, key: key)
            var f = try Nexus.fileInfo(info.modId, info.fileId, key: key)
            if f["file_id"] == nil { f["file_id"] = .int(info.fileId) }
            let name = String(safeName("\(mod["name"]?.pyStr ?? "Nexus") - \(f["name"]?.pyStr ?? "")").prefix(90))
            let meta = nexusMeta(info.modId, mod, f)
            let dir = tmp.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            defer { try? FileManager.default.removeItem(at: dir) }
            let path = try Nexus.download(info.modId, file: f, key: key, to: dir, nxm: info, progress: progress)
            return try importSource(cfg, path, name: name, meta: meta)
        }
    }

    private func runImport(_ work: @escaping @Sendable (@escaping Jobs.Progress) throws -> [URL]) {
        Jobs.run(work, progress: { [weak self] got, total in if total > 0 { self?.progress = Double(got) / Double(total) } },
                 done: { [weak self] made in
                     self?.progress = nil
                     self?.say(L("✓ Ajouté à la bibliothèque : {names}", ["names": made.map(\.name).joined(separator: ", ")]), .success)
                     self?.model?.webImported(made)
                 }, failed: { [weak self] e in
                     self?.progress = nil
                     self?.say(isLookup(e) ? L("L'archive ne contient ni SettingsUser.json ni fichier PostProcessing : ce n'est pas un "
                                               + "preset Community Shaders (preset ReShade ou ENB ?).")
                                           : L("Échec : {err}", ["err": errText(e)]), .danger)
                 })
    }
}

/// Description d'un preset venu de Nexus (preset.json).
func nexusMeta(_ modId: Int, _ mod: JObject, _ f: JObject) -> JObject {
    JObject([("source", "Nexus Mods"), ("nexus_id", .int(modId)), ("mod", mod["name"] ?? .null), ("author", mod["author"] ?? .null),
             ("file", f["name"] ?? .null), ("version", f["version"] ?? .null),
             ("url", .string("https://www.nexusmods.com/\(Nexus.game)/mods/\(modId)"))])
}

struct WebView: NSViewRepresentable {
    let web: WKWebView
    func makeNSView(context: Context) -> WKWebView { web }
    func updateNSView(_ nsView: WKWebView, context: Context) {}
}

struct NexusBrowserView: View {
    @ObservedObject var browser: NexusBrowser

    var body: some View {
        VStack(spacing: Socle.M.space2) {
            HStack(spacing: Socle.M.space2) {
                nav("chevron.left", L("Page précédente"), browser.canBack) { browser.web.goBack() }
                nav("chevron.right", L("Page suivante"), browser.canForward) { browser.web.goForward() }
                nav("arrow.clockwise", L("Recharger"), true) { browser.web.reload() }
                HStack(spacing: 0) {
                    TextField(L("Rechercher sur Nexus"), text: $browser.search).textFieldStyle(.plain)
                        .onSubmit(browser.goSearch)
                    Menu {
                        ForEach(Nexus.searches, id: \.self) { s in Button(s) { browser.search = s; browser.goSearch() } }
                    } label: { EmptyView() }
                        .menuStyle(.borderlessButton).fixedSize()
                }
                .socleField()
                .frame(width: 280)
                Button(L("Rechercher"), action: browser.goSearch).socleButton()
                Text(browser.address).socle(Socle.T.monoSm).foregroundStyle(Socle.C.textMuted).lineLimit(1).truncationMode(.middle)
                    .frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
                Button(L("Ouvrir dans le navigateur")) { if let u = browser.web.url { NSWorkspace.shared.open(u) } }.socleButton(.tertiary)
            }
            WebView(web: browser.web)
                .overlay(Rectangle().stroke(Socle.C.border, lineWidth: 1))
            HStack(spacing: Socle.M.space2) {
                Text(browser.state).socle(Socle.T.meta).foregroundStyle(browser.tone.color)
                    .frame(maxWidth: .infinity, alignment: .leading).fixedSize(horizontal: false, vertical: true)
                if let p = browser.progress {
                    Group { if p < 0 { ProgressView().progressViewStyle(.linear) } else { ProgressView(value: p) } }.frame(width: 180)
                }
                if browser.isModPage {
                    Button(L("Choisir un fichier de ce mod…")) { browser.model?.fromNexus(browser.address) }.socleButton(.primary)
                }
            }
        }
        .onAppear(perform: browser.appeared)
    }

    private func nav(_ icon: String, _ help: String, _ on: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) { Image(systemName: icon).font(.system(size: 14, weight: .semibold)) }
            .buttonStyle(SocleButtonStyle(.tertiary, height: Socle.M.sizeControl)).frame(width: Socle.M.sizeControl)
            .help(help).disabled(!on)
    }
}

// MARK: Dialogue « Télécharger depuis Nexus Mods » (un fichier d'un mod, par l'API)

@MainActor
final class NexusDialogModel: ObservableObject, Identifiable {
    weak var model: AppModel?
    @Published var url: String
    @Published var title = ""
    @Published var files: [JObject] = []
    @Published var selected: Int?
    @Published var state = L("Le fichier téléchargé est ajouté à la bibliothèque. Aucun réglage du jeu n'est modifié.")
    @Published var tone: Tone = .none
    @Published var progress: Double?
    @Published var busy = false
    var modId = 0
    var mod = JObject()
    var created: [URL] = []

    init(model: AppModel, url: String) {
        self.model = model
        self.url = url
        if !url.isEmpty { DispatchQueue.main.async { MainActor.assumeIsolated { self.search() } } }
    }

    private func key() -> String? {
        let k = Nexus.getKey()
        if k.isEmpty { Dialog.info(L("Ajoutez d'abord votre clé d'API Nexus dans les réglages.")); return nil }
        return k
    }

    func search() {
        guard let key = key() else { return }
        guard let mid = try? Nexus.parseModId(url) else {
            state = L("Adresse non reconnue. Collez l'adresse de la page du mod ou son numéro."); tone = .warning
            return
        }
        modId = mid
        state = L("Recherche en cours…"); tone = .none
        files = []; selected = nil; busy = true
        Jobs.run({ _ in (try Nexus.modInfo(mid, key: key), try Nexus.modFiles(mid, key: key)) }, done: { [self] r in
            busy = false
            mod = r.0; files = r.1
            title = "\(mod["name"]?.pyStr ?? "?") — \(mod["author"]?.pyStr ?? "")"
            state = L("{n} fichier(s). Choisissez celui à télécharger.", ["n": files.count])
            selected = files.isEmpty ? nil : 0
        }, failed: fail)
    }

    var description: String {
        guard let i = selected, i < files.count else { return "" }
        return String((files[i]["description"]?.string ?? "").replacingOccurrences(of: "<br />", with: " ").prefix(400))
    }

    func download() {
        guard let key = key(), let i = selected, i < files.count, let cfg = model?.cfg else { return }
        let f = files[i], mid = modId, mod = mod
        let name = String(safeName("\(mod["name"]?.pyStr ?? "Nexus") - \(f["name"]?.pyStr ?? "")").prefix(90))
        let meta = nexusMeta(mid, mod, f)
        progress = -1; busy = true
        state = L("Téléchargement de {f}…", ["f": f["file_name"]?.pyStr ?? ""]); tone = .none
        Jobs.run({ progress in
            let dir = FileManager.default.temporaryDirectory.appendingPathComponent("cssettings_dl_" + UUID().uuidString)
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            defer { try? FileManager.default.removeItem(at: dir) }
            let path = try Nexus.download(mid, file: f, key: key, to: dir, progress: progress)
            return try importSource(cfg, path, name: name, meta: meta)
        }, progress: { [self] got, total in if total > 0 { progress = Double(got) / Double(total) } },
        done: { [self] made in
            progress = nil; busy = false
            created += made
            state = L("✓ Ajouté à la bibliothèque : {names}", ["names": made.map(\.name).joined(separator: ", ")]); tone = .success
        }, failed: fail)
    }

    private func fail(_ e: Error) {
        progress = nil; busy = false
        let err = errText(e)
        if isLookup(e) {
            state = L("L'archive ne contient ni SettingsUser.json ni fichier PostProcessing : ce n'est pas un preset Community Shaders "
                      + "(preset ReShade ou ENB ?).")
        } else if err.contains("HTTP 403") {
            state = L("Nexus refuse le téléchargement direct : il faut un compte Premium (ou téléchargez le fichier à la main puis "
                      + "utilisez « Importer »).")
        } else {
            state = L("Échec : {err}", ["err": err])
        }
        tone = .danger
    }
}

struct NexusDialogView: View {
    @ObservedObject var dialog: NexusDialogModel

    var body: some View {
        VStack(alignment: .leading, spacing: Socle.M.space3) {
            Text(L("Télécharger depuis Nexus Mods")).socle(Socle.T.heading).foregroundStyle(Socle.C.textStrong)
            HStack(spacing: Socle.M.space2) {
                TextField(L("Adresse de la page du mod ou numéro (ex. 165803)"), text: $dialog.url).socleField().onSubmit(dialog.search)
                Button(L("Rechercher"), action: dialog.search).socleButton().disabled(dialog.busy)
            }
            if !dialog.title.isEmpty { Text(dialog.title).socle(Socle.T.title).foregroundStyle(Socle.C.textStrong) }
            SimpleTable(columns: [Column(title: L("Fichier")), Column(title: L("Catégorie"), width: 120), Column(title: L("Version"), width: 80),
                                  Column(title: L("Taille"), width: 80), Column(title: L("Date"), width: 90)],
                        rows: dialog.files.map { f in
                            let date = Date(timeIntervalSince1970: TimeInterval(f["uploaded_timestamp"]?.int ?? 0))
                            return [f["name"]?.pyStr ?? "", f["category_name"]?.pyStr ?? "", f["version"]?.pyStr ?? "",
                                    humanSize(f["size_kb"]), strftime("yyyy-MM-dd", date)]
                        }, selection: $dialog.selected, onDouble: dialog.download)
            Text(dialog.description).socle(Socle.T.meta).foregroundStyle(Socle.C.textMuted).fixedSize(horizontal: false, vertical: true)
            if let p = dialog.progress { if p < 0 { ProgressView().progressViewStyle(.linear) } else { ProgressView(value: p) } }
            Text(dialog.state).socle(Socle.T.meta).foregroundStyle(dialog.tone.color).fixedSize(horizontal: false, vertical: true)
            HStack(spacing: Socle.M.space2) {
                Spacer()
                Button(L("Fermer")) { dialog.model?.nexusDialogClosed(dialog) }.socleButton().keyboardShortcut(.cancelAction)
                Button(L("TÉLÉCHARGER ET IMPORTER"), action: dialog.download).socleButton(.primary)
                    .disabled(dialog.selected == nil || dialog.busy)
            }
        }
        .padding(Socle.M.space6)
        .frame(width: 820, height: 560)
        .background(Socle.C.bg)
    }
}
