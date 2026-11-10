// Fenêtre principale : en-tête, onglets (Presets, Presets ENB, Système, Sauvegardes, Nexus) et journal.

import CSCore
import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @ObservedObject var model: AppModel
    @State private var dropping = false

    private var tabs: [String] { [L("Presets"), L("Presets ENB"), L("Système"), L("Sauvegardes"), L("Nexus")] }

    var body: some View {
        VStack(spacing: 0) {
            header
            VStack(spacing: Socle.M.space3) {
                tabBar
                Group {
                    switch model.tab {
                    case 0: PresetsTab(model: model)
                    case 1: EnbTab(model: model)
                    case 2: SystemTab(model: model)
                    case 3: BackupsTab(model: model)
                    default: NexusBrowserView(browser: model.browser)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                LogView(lines: model.log)
            }
            .padding(Socle.M.space3)
        }
        .background(Socle.C.bg)
        .overlay(dropping ? Rectangle().stroke(Socle.C.accent, lineWidth: 2) : nil)
        .onDrop(of: [.fileURL], isTargeted: $dropping) { providers in
            for p in providers {
                _ = p.loadObject(ofClass: URL.self) { url, _ in
                    guard let url else { return }
                    DispatchQueue.main.async { MainActor.assumeIsolated { model.drop([url.standardizedFileURL]) } }
                }
            }
            return true
        }
        .sheet(isPresented: $model.showSettings) { SettingsView(model: model) }
        .sheet(item: $model.nexusDialog) { d in NexusDialogView(dialog: d) }
    }

    private var header: some View {
        HStack(spacing: Socle.M.space2) {
            Text(branded: APP).socle(Socle.T.title).foregroundStyle(Socle.C.textStrong)
            Text(L("Presets Community Shaders")).socle(Socle.T.body).foregroundStyle(Socle.C.textSubtle)
            Spacer()
            Text(model.running ? L("⚠ Jeu lancé : fermez-le avant d'appliquer") : L("Jeu fermé"))
                .socle(Socle.T.meta).foregroundStyle(model.running ? Socle.C.warning : Socle.C.success)
            Button(L("Réglages")) { model.showSettings = true }.socleButton(.tertiary)
        }
        .padding(.horizontal, Socle.M.space3)
        .frame(minHeight: Socle.M.sizeBar)
        .background(Socle.C.surfaceRaised)
        .overlay(alignment: .bottom) { Rectangle().fill(Socle.C.border).frame(height: 1) }
    }

    private var tabBar: some View {
        HStack(spacing: Socle.M.space4) {
            ForEach(tabs.indices, id: \.self) { i in
                Button { model.tab = i } label: {
                    VStack(spacing: Socle.M.space1_5) {
                        Text(tabs[i]).socle(Socle.T.labelStrong)
                            .foregroundStyle(model.tab == i ? Socle.C.textStrong : Socle.C.textMuted)
                        Rectangle().fill(model.tab == i ? Socle.C.accent : Color.clear).frame(height: 2)
                    }
                    .fixedSize()
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .overlay(alignment: .bottom) { Rectangle().fill(Socle.C.borderSubtle).frame(height: 1) }
    }
}

struct LogView: View {
    let lines: [String]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(lines.indices, id: \.self) { i in
                        Text(lines[i]).socle(Socle.T.monoSm).foregroundStyle(Socle.C.text).id(i)
                    }
                }
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(Socle.M.space2)
            }
            .onChange(of: lines.count) { _, n in if n > 0 { proxy.scrollTo(n - 1, anchor: .bottom) } }
        }
        .frame(height: 90)
        .background(Socle.C.bgSunken)
        .overlay(Rectangle().stroke(Socle.C.border, lineWidth: 1))
    }
}

/// Deux colonnes : liste à gauche, détail à droite. La colonne de gauche fait au moins 380 pt et s'élargit pour que
/// ses boutons (repérés par `.leftWidth()`) tiennent sans être tronqués, quelle que soit la langue.
struct Split<Left: View, Right: View>: View {
    @ViewBuilder let left: Left
    @ViewBuilder let right: Right
    @State private var width: CGFloat = 380

    var body: some View {
        HStack(alignment: .top, spacing: Socle.M.space4) {
            left.frame(width: width)
                .onPreferenceChange(LeftWidthKey.self) { w in width = max(380, ceil(w)) }
            right.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }
}

struct LeftWidthKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = max(value, nextValue()) }
}

extension View {
    /// Largeur naturelle de cette rangée, imposée comme minimum à la colonne de gauche de `Split`.
    func leftWidth() -> some View {
        fixedSize().background(GeometryReader { Color.clear.preference(key: LeftWidthKey.self, value: $0.size.width) })
    }
}

// MARK: Presets

struct PresetsTab: View {
    @ObservedObject var model: AppModel

    var body: some View {
        Split {
            VStack(alignment: .leading, spacing: Socle.M.space2) {
                SelectList(rows: model.presets.map { p in
                    var kind = p.hasSettings ? "CS \(p.version)" : L("post-traitement seul")
                    let warn = model.compats[p.name]?.level == .warning
                    if warn { kind += "  ·  " + L("⚠ incompatible en partie") }
                    return ListRow(id: p.name, title: p.name, subtitle: kind, marked: p.name == model.active, warn: warn)
                }, selection: $model.selected, onDouble: model.apply)
                Text(L("Vous pouvez aussi glisser-déposer une archive ou un dossier sur la fenêtre."))
                    .socle(Socle.T.meta).foregroundStyle(Socle.C.textSubtle).fixedSize(horizontal: false, vertical: true)
                HStack(spacing: Socle.M.space2) {
                    Button(L("Importer…")) {
                        popMenu([(L("Une archive (.ZIP, .7Z, .RAR)…"), model.importArchive), (L("Un dossier…"), model.importFolder)])
                    }.socleButton()
                    Button(L("Depuis Nexus…")) { model.tab = 4 }.socleButton()
                    Button(L("Enregistrer la config actuelle…"), action: model.saveCurrentConfig).socleButton()
                }
                .leftWidth()
            }
        } right: {
            PresetDetail(model: model)
        }
    }
}

struct PresetDetail: View {
    @ObservedObject var model: AppModel

    var body: some View {
        let p = model.current
        VStack(alignment: .leading, spacing: Socle.M.space3) {
            Text(p?.name ?? L("Aucun preset")).socle(Socle.T.heading).foregroundStyle(Socle.C.textStrong)
                .fixedSize(horizontal: false, vertical: true)
            if let p { badges(p) }
            if model.sysname == Systems.ENB {
                Callout(L("Le système ENB est actif : les presets Community Shaders ne s'appliquent pas. Passez à Community Shaders "
                          + "dans l'onglet Système."), tone: .warning)
            }
            if let (text, tone) = compat(p) { Callout(text, tone: tone) }
            ScrollView {
                Text(rich(details(p))).socle(Socle.T.body).foregroundStyle(Socle.C.text)
                    .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            }
            Text(L("Avant chaque application, la configuration en place est sauvegardée (onglet Sauvegardes). Aucun fichier du "
                   + "preset n'est modifié.")).socle(Socle.T.meta).foregroundStyle(Socle.C.textSubtle)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: Socle.M.space2) {
                Button(L("Afficher dans le Finder")) { if let p { reveal(p.path) } }.socleButton(.tertiary).disabled(p == nil)
                Button(L("Retirer de la bibliothèque"), action: model.removeCurrent).socleButton(.tertiary).disabled(p == nil)
                Spacer()
                Button(L("Appliquer ce preset"), action: model.apply).socleButton(.action)
                    .disabled(p == nil || model.running || model.sysname == Systems.ENB || model.sysBusy)
            }
        }
    }

    private func badges(_ p: Preset) -> some View {
        var tags: [(String, Color)] = []
        if p.name == model.active { tags.append((L("✓ Chargé"), Socle.C.success)) }
        tags.append((p.hasSettings ? "CS \(p.version)" : L("Post-traitement seul"), Socle.C.accentText))
        if p.hasEnb { tags.append((L("+ ENB"), Socle.C.accentText)) }
        if p.hasSettings, !p.version.isEmpty, !p.version.hasPrefix("1.9") { tags.append((L("⚠ Réglages d'une autre version de CS"), Socle.C.warning)) }
        return HStack(spacing: Socle.M.space4) {
            ForEach(tags.indices, id: \.self) { Text(tags[$0].0).socle(Socle.T.meta).foregroundStyle(tags[$0].1) }
        }
    }

    private func details(_ p: Preset?) -> String {
        guard let p else {
            return L("Importez une archive, un dossier, ou téléchargez un preset depuis Nexus pour commencer. Bibliothèque : {lib}",
                     ["lib": esc(model.cfg["library"])])
        }
        var lines: [String] = []
        let m = p.metaText
        if !m("url").isEmpty {
            let mod = m("mod").isEmpty ? "Nexus" : m("mod")
            lines.append("<b>\(L("Source"))</b> : <a href='\(m("url"))'>\(esc(mod))</a> — \(esc(m("file"))) \(esc(m("version")))")
        } else if !m("source").isEmpty {
            lines.append("<b>\(L("Source"))</b> : \(esc(m("source")))")
        }
        if !m("date").isEmpty { lines.append("<b>\(L("Ajouté le"))</b> : \(esc(m("date")))") }
        if p.hasSettings { lines.append(L("Remplace les réglages de Community Shaders (SettingsUser.json).")) }
        if !p.editor.isEmpty { lines.append(L("Données de l'éditeur CS : {list}", ["list": p.editor.joined(separator: ", ")])) }
        if !p.ppFiles.isEmpty { lines.append(L("Post-traitement ajouté au menu CS : {list}", ["list": esc(p.ppFiles.joined(separator: ", "))])) }
        if p.hasEnb {
            lines.append(L("<b>Preset ENB (Effects 11)</b> : remplace enbseries.ini et le dossier enbseries à la racine du jeu. Ceux en "
                           + "place sont déplacés dans la sauvegarde, rien n'est effacé."))
        }
        return lines.joined(separator: "<br><br>")
    }

    /// Encart Socle : ce que le Community Shaders installé ignorera ou complétera.
    private func compat(_ p: Preset?) -> (String, Tone)? {
        guard let p else { return nil }
        guard let ref = model.ref else {
            return (L("Compatibilité non vérifiée : SettingsDefault.json introuvable dans le dossier Community Shaders du jeu. Vérifiez "
                      + "les réglages et que le disque est branché."), .info)
        }
        guard let c = model.compats[p.name] else { return nil }
        let v = ref.version
        var parts: [String] = []
        if !c.unknownFeatures.isEmpty {
            parts.append(L("<b>⚠ Features inconnues de votre Community Shaders {v}</b> : {list}. Elles seront ignorées ; le rendu peut "
                           + "différer des captures du preset (autre variante de CS, comme Jiaye AIO ou Open Shader ?).",
                           ["v": v, "list": esc(c.unknownFeatures.joined(separator: ", "))]))
        }
        if c.frameGen {
            parts.append(L("<b>⚠ Frame Generation forcée</b> : le preset l'active, et sous CrossOver elle fait planter le jeu au lancement. "
                           + "Désactivez-la en jeu (Upscaling) ou dans le SettingsUser.json du preset (frameGenerationForceEnable à 0)."))
        }
        if !c.ppRejected.isEmpty {
            parts.append(L("<b>⚠ Post-traitement du preset ignoré</b> : votre Community Shaders {v} rejettera sa chaîne de "
                           + "post-traitement ({why}) et la remplacera par une chaîne vide. Ni l'étalonnage ni les effets du preset ne "
                           + "seront rendus : refaites la chaîne en jeu ou prenez une version du preset faite pour CS {v}.",
                           ["v": v, "why": esc(model.ppWhy(c))]))
        } else if !c.unknownPP.isEmpty {
            parts.append(L("<b>⚠ Effets de post-traitement inconnus</b> : {list}. Ils seront ignorés.",
                           ["list": esc(c.unknownPP.joined(separator: ", "))]))
        }
        if !c.missingFeatures.isEmpty {
            parts.append(L("<b>ⓘ Features absentes du preset</b> : {list}. Elles garderont leurs valeurs par défaut.",
                           ["list": esc(c.missingFeatures.joined(separator: ", "))]))
        }
        if c.unknownOptions > 0 {
            parts.append(L("ⓘ {n} option(s) inconnue(s) dans des features connues : renommées ou retirées depuis la version du preset, "
                           + "elles seront ignorées.", ["n": c.unknownOptions]))
        }
        if parts.isEmpty {
            parts.append(L("<b>✓ Compatible</b> : toutes les features du preset existent dans votre Community Shaders {v}.", ["v": v]))
        }
        let tone: Tone = c.level == .ok ? .success : c.level == .info ? .info : .warning
        return (parts.joined(separator: "<br>"), tone)
    }
}

// MARK: Presets ENB

struct EnbTab: View {
    @ObservedObject var model: AppModel

    var body: some View {
        Split {
            VStack(alignment: .leading, spacing: Socle.M.space2) {
                SelectList(rows: model.enbPresets.map { ListRow(id: $0.name, title: $0.name, marked: $0.name == model.enbActive) },
                           selection: $model.enbSelected, onDouble: model.applyEnb)
                Text(L("Bibliothèque : {lib}", ["lib": model.cfg.enbLibrary.path])).socle(Socle.T.meta)
                    .foregroundStyle(Socle.C.textSubtle).fixedSize(horizontal: false, vertical: true).textSelection(.enabled)
                Button(L("Enregistrer l'ENB actuel…"), action: model.saveEnb).socleButton()
            }
        } right: {
            let p = model.enbCurrent
            VStack(alignment: .leading, spacing: Socle.M.space3) {
                Text(p?.name ?? L("Aucun preset ENB")).socle(Socle.T.heading).foregroundStyle(Socle.C.textStrong)
                    .fixedSize(horizontal: false, vertical: true)
                if model.sysname != Systems.ENB {
                    Callout(L("Le système ENB n'est pas actif : passez-y depuis l'onglet Système pour appliquer un preset ENB."), tone: .warning)
                }
                ScrollView {
                    Text(rich(details(p))).socle(Socle.T.body).foregroundStyle(Socle.C.text)
                        .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }
                Text(L("Avant chaque application, enbseries.ini et le dossier enbseries en place sont déplacés dans la sauvegarde, rien "
                       + "n'est effacé, sauf le cache enbcache de la racine du jeu, supprimé pour que le nouveau preset soit recompilé. "
                       + "Aucun fichier du preset n'est modifié.")).socle(Socle.T.meta).foregroundStyle(Socle.C.textSubtle)
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: Socle.M.space2) {
                    Button(L("Afficher dans le Finder")) { if let p { reveal(p.path) } }.socleButton(.tertiary).disabled(p == nil)
                    Spacer()
                    Button(L("Appliquer ce preset ENB"), action: model.applyEnb).socleButton(.action)
                        .disabled(p == nil || model.running || model.sysname != Systems.ENB || model.sysBusy)
                }
            }
        }
    }

    private func details(_ p: Preset?) -> String {
        guard let p else {
            return L("Rangez vos presets ENB (un dossier avec enbseries.ini et enbseries/) dans : {lib}", ["lib": esc(model.cfg.enbLibrary.path)])
        }
        var lines: [String] = []
        if p.name == model.enbActive { lines.append(L("✓ Chargé")) }
        if !p.metaText("source").isEmpty { lines.append("<b>\(L("Source"))</b> : \(esc(p.metaText("source")))") }
        if !p.metaText("date").isEmpty { lines.append("<b>\(L("Ajouté le"))</b> : \(esc(p.metaText("date")))") }
        lines.append(L("Remplace enbseries.ini et le dossier enbseries à la racine du jeu ({n} effets).", ["n": p.ppFiles.count]))
        if enbSource(p.path).sub("enblocal.ini").isFile {
            lines.append(L("enblocal.ini du preset non appliqué : il règle la machine, pas le rendu."))
        }
        return lines.joined(separator: "<br><br>")
    }
}

// MARK: Système

struct SystemTab: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: Socle.M.space3) {
            Callout(model.sysStatus, tone: model.sysTone)
            Text(L("Un système de shaders à la fois : Community Shaders (Bottled) ou ENB. Chaque système a une base neutre ; passer de "
                   + "l'un à l'autre retire proprement l'ancien (ce que vous avez modifié est mis de côté, jamais perdu) et pose le "
                   + "nouveau. Les pièces communes (KiLoader…) restent.")).socle(Socle.T.meta).foregroundStyle(Socle.C.textSubtle)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: Socle.M.space2) {
                ForEach([Systems.CS, Systems.ENB], id: \.self) { n in
                    Button(model.sysLabel(n)) { model.sysGo(n) }.socleButton(.primary)
                        .disabled(!["swap", "adopt"].contains(model.sysModes[n] ?? "") || model.sysBusy)
                }
                Button(L("Retirer le système"), action: model.sysRemove).socleButton(.tertiary)
                    .disabled(model.sysname == nil || model.sysBusy)
                if model.sysBusy { ProgressView().controlSize(.small) }
                Spacer()
            }
            Text(rich(model.basesInfo)).socle(Socle.T.meta).foregroundStyle(Socle.C.textMuted).textSelection(.enabled)
            HStack(spacing: Socle.M.space2) {
                Button(L("Reconstruire les bases…"), action: model.sysRebuild).socleButton(.tertiary).disabled(model.sysBusy)
                Button(L("Afficher les bases")) { reveal(model.cfg.systemsDir) }.socleButton(.tertiary)
                Spacer()
            }
            Text(L("Historique des échanges")).socle(Socle.T.heading).foregroundStyle(Socle.C.textStrong)
            SimpleTable(columns: [Column(title: L("Date")), Column(title: L("Opération"), width: 150),
                                  Column(title: L("Couche"), width: 100), Column(title: L("État"), width: 110)],
                        rows: model.sysOps.map { o in
                            [o.name.components(separatedBy: "_install_")[0].components(separatedBy: "_remove_")[0]
                                .components(separatedBy: "_drop_")[0].replacingOccurrences(of: "_", with: " "),
                             model.opLabel(o.type), o.layer, model.statusLabel(o.status)]
                        }, selection: $model.sysSelected, onDouble: revealOp)
            HStack {
                Button(L("Afficher la sauvegarde dans le Finder"), action: revealOp).socleButton().disabled(model.sysSelected == nil)
                Spacer()
            }
        }
    }

    private func revealOp() {
        if let i = model.sysSelected, i < model.sysOps.count { reveal(model.sysOps[i].path) }
    }
}

// MARK: Sauvegardes

struct BackupsTab: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: Socle.M.space2) {
            SimpleTable(columns: [Column(title: L("Date"), width: 190), Column(title: L("Motif")),
                                  Column(title: L("Réglages CS"), width: 100), Column(title: L("Contenu"), width: 300)],
                        rows: model.backups.map { b in
                            let content = (b.hasSettings ? [L("réglages")] : []) + b.editor + (b.ppFiles.isEmpty ? [] : ["\(b.ppFiles.count) PP"])
                                + (b.hasEnb ? ["ENB"] : [])
                            return [b.name.replacingOccurrences(of: "_", with: " "), b.metaText("reason"), b.version,
                                    content.joined(separator: ", ")]
                        }, selection: $model.backupSelected)
            HStack(spacing: Socle.M.space2) {
                Button(L("Afficher dans le Finder")) { if let b = model.backupCurrent { reveal(b.path) } }.socleButton()
                    .disabled(model.backupCurrent == nil)
                Spacer()
                Button(L("Restaurer cette sauvegarde"), action: model.restore).socleButton(.primary)
                    .disabled(model.backupCurrent == nil || model.running)
            }
        }
    }
}
