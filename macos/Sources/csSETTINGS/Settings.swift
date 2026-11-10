// Réglages : dossiers, langue, clé d'API Nexus (trousseau macOS) et mises à jour.

import CSCore
import SwiftUI

struct SettingsView: View {
    @ObservedObject var model: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var cfg: Config
    @State private var key = ""
    @State private var savedKey = ""
    @State private var keyState = ""
    @State private var keyTone: Tone = .none

    init(model: AppModel) {
        self.model = model
        _cfg = State(initialValue: model.cfg)
    }

    private let fields: [(String, String)] = [
        ("library", "Bibliothèque de presets"), ("enb_library", "Bibliothèque de presets ENB"),
        ("systems_dir", "Dossier des bases de systèmes (CS / ENB)"), ("cs_dir", "Dossier Community Shaders du jeu"),
        ("backup_dir", "Dossier des sauvegardes"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: Socle.M.space4) {
            Text(L("Réglages")).socle(Socle.T.heading).foregroundStyle(Socle.C.textStrong)
            Grid(alignment: .leading, horizontalSpacing: Socle.M.space3, verticalSpacing: Socle.M.space2) {
                ForEach(fields, id: \.0) { k, label in
                    GridRow {
                        Text(L(label)).socle(Socle.T.label).foregroundStyle(Socle.C.text)
                        HStack(spacing: Socle.M.space2) {
                            TextField("", text: binding(k)).socle(Socle.T.monoSm).socleField()
                            Button(L("Choisir…")) {
                                if let d = Dialog.folder(L("Choisir un dossier"), cfg[k]) { cfg[k] = d.path }
                            }.socleButton()
                        }
                    }
                }
                GridRow {
                    Text(L("Langue")).socle(Socle.T.label).foregroundStyle(Socle.C.text)
                    Picker("", selection: binding("lang")) {
                        Text(L("Automatique ({lang})", ["lang": I18n.langs[I18n.systemLang()] ?? "English"])).tag("auto")
                        ForEach(["fr", "en", "it", "es"], id: \.self) { Text(I18n.langs[$0]!).tag($0) }
                    }
                    .labelsHidden().frame(width: 260)
                }
            }

            Text(L("Nexus Mods")).socle(Socle.T.title).foregroundStyle(Socle.C.textStrong)
            Text(L("Collez votre clé d'API personnelle (page « API Keys » de votre compte Nexus). Elle est rangée dans le trousseau macOS, "
                   + "jamais dans un fichier. Le téléchargement direct demande un compte Premium."))
                .socle(Socle.T.body).foregroundStyle(Socle.C.textMuted).fixedSize(horizontal: false, vertical: true)
            HStack(spacing: Socle.M.space2) {
                SecureField(L("Clé d'API"), text: $key).socleField()
                Button(L("Vérifier"), action: check).socleButton()
                Button(L("Ouvrir la page des clés")) { NSWorkspace.shared.open(URL(string: "https://www.nexusmods.com/settings/api-keys")!) }
                    .socleButton(.tertiary)
            }
            if !keyState.isEmpty { Text(keyState).socle(Socle.T.meta).foregroundStyle(keyTone.color) }

            UpdateSettings()

            HStack(spacing: Socle.M.space2) {
                Spacer()
                Button(L("Annuler")) { dismiss() }.socleButton().keyboardShortcut(.cancelAction)
                Button(L("ENREGISTRER"), action: save).socleButton(.primary).keyboardShortcut(.defaultAction)
            }
        }
        .padding(Socle.M.space6)
        .frame(width: 820)
        .background(Socle.C.bg)
        .onAppear {
            savedKey = Nexus.getKey()
            key = savedKey
        }
    }

    private func binding(_ k: String) -> Binding<String> { Binding(get: { cfg[k] }, set: { cfg[k] = $0 }) }

    private func check() {
        let k = key.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !k.isEmpty else { return }
        keyState = L("Recherche en cours…"); keyTone = .none
        Jobs.run({ _ in try Nexus.validate(k) }, done: { u in
            let premium = u["is_premium"]?.truthy ?? false
            let prem = premium ? L("Premium") : L("non Premium : téléchargement direct impossible")
            keyState = L("✓ Clé valide : {name} ({prem})", ["name": u["name"]?.pyStr ?? "?", "prem": prem])
            keyTone = premium ? .success : .warning
        }, failed: { e in
            keyState = L("✕ Clé refusée par Nexus ({err}).", ["err": errText(e)])
            keyTone = .danger
        })
    }

    private func save() {
        var new = cfg
        for (k, _) in fields { new[k] = new[k].trimmingCharacters(in: .whitespacesAndNewlines) }
        let k = key.trimmingCharacters(in: .whitespacesAndNewlines)
        do {
            if !k.isEmpty && k != savedKey { try Nexus.setKey(k) } else if k.isEmpty { Nexus.deleteKey() }
        } catch {
            Dialog.warn(L("Impossible d'enregistrer la clé dans le trousseau : {err}", ["err": errText(error)]))
            return
        }
        dismiss()
        model.saveSettings(new)
    }
}

/// Section « Mises à jour » : installation automatique et vérification manuelle (moteur commun UpdateEngine).
struct UpdateSettings: View {
    static var autoInstall: Bool { UserDefaults.standard.object(forKey: "updater.autoInstall") as? Bool ?? false }
    @ObservedObject private var engine = UpdateEngine.shared
    @State private var auto = UpdateSettings.autoInstall

    var body: some View {
        VStack(alignment: .leading, spacing: Socle.M.space2) {
            Text(L("Mises à jour")).socle(Socle.T.title).foregroundStyle(Socle.C.textStrong)
            Toggle(L("Installer automatiquement les mises à jour"), isOn: $auto).socle(Socle.T.body)
                .onChange(of: auto) { _, v in UserDefaults.standard.set(v, forKey: "updater.autoInstall") }
            HStack(spacing: Socle.M.space2) {
                Button(L("Rechercher maintenant")) { engine.checkNow() }.socleButton().disabled(engine.isBusy)
                Text(status).socle(Socle.T.meta).foregroundStyle(Socle.C.textMuted).lineLimit(1)
                Spacer()
            }
        }
    }

    private var status: String {
        switch engine.state {
        case .checking: return L("Recherche en cours…")
        case .upToDate: return L("Version {v} : à jour.", ["v": engine.currentVersion])
        case .available(let plan): return L("Version {v} disponible.", ["v": plan.target.version])
        case .downloading, .verifying, .installing: return L("Installation de la mise à jour…")
        case .failed(let key): return engine.message(for: key)
        case .idle: return engine.currentVersion.isEmpty ? "" : L("Version {v}", ["v": engine.currentVersion])
        }
    }
}
