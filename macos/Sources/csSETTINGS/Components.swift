// Composants d'interface Socle propres à csSETTINGS : encarts, listes, tableaux, texte enrichi, dialogues, travaux de fond.

import AppKit
import CSCore
import SwiftUI

let APP = "csSETTINGS"
/// « cs » dans le bleu du curseur du logo
let BRAND_COLOR = Color(red: 0x14 / 255, green: 0xa5 / 255, blue: 0xe6 / 255)

enum Tone { case none, success, info, warning, danger

    var color: Color {
        switch self {
        case .none: Socle.C.textMuted
        case .success: Socle.C.success
        case .info: Socle.C.textMuted
        case .warning: Socle.C.warning
        case .danger: Socle.C.danger
        }
    }
}

// MARK: Texte enrichi (<b>, <br>, <a href='…'>) des traductions

func rich(_ s: String) -> AttributedString {
    var out = AttributedString()
    var bold = false
    var link: URL?
    var rest = Substring(s)
    func add(_ t: Substring) {
        guard !t.isEmpty else { return }
        var a = AttributedString(String(t))
        if bold { a.inlinePresentationIntent = .stronglyEmphasized }
        if let link { a.link = link; a.foregroundColor = Socle.C.accentText }
        out += a
    }
    while let lt = rest.firstIndex(of: "<") {
        add(rest[..<lt])
        guard let gt = rest[lt...].firstIndex(of: ">") else { add(rest[lt...]); return Socle.branded(out) }
        let tag = rest[rest.index(after: lt)..<gt].lowercased()
        switch tag {
        case "b": bold = true
        case "/b": bold = false
        case "br", "br/", "br /": out += AttributedString("\n")
        case "/a": link = nil
        default:
            if tag.hasPrefix("a href="), let q = tag.dropFirst(7).first {
                let raw = rest[rest.index(after: lt)..<gt].dropFirst(8)
                link = URL(string: String(raw.prefix { $0 != q }))
            } else {
                add(rest[lt...gt])
            }
        }
        rest = rest[rest.index(after: gt)...]
    }
    add(rest)
    return Socle.branded(out)
}

/// Échappe un texte inséré dans un message enrichi (nom de fichier, chemin…).
func esc(_ s: String) -> String { s.replacingOccurrences(of: "<", with: "‹").replacingOccurrences(of: ">", with: "›") }

// MARK: Encart (Callout Socle)

struct Callout: View {
    let text: AttributedString
    let tone: Tone

    init(_ text: String, tone: Tone) { self.text = rich(text); self.tone = tone }

    var body: some View {
        Text(text)
            .socle(Socle.T.body)
            .foregroundStyle(fg)
            .frame(maxWidth: .infinity, alignment: .leading)
            .fixedSize(horizontal: false, vertical: true)
            .textSelection(.enabled)
            .padding(Socle.M.space2)
            .background(bg, in: RoundedRectangle(cornerRadius: Socle.M.radius))
            .overlay(RoundedRectangle(cornerRadius: Socle.M.radius).stroke(border, lineWidth: 1))
    }

    private var bg: Color {
        switch tone {
        case .success: Socle.C.successBg
        case .warning: Socle.C.warningBg
        case .danger: Socle.C.dangerBg
        default: Socle.C.surfaceRaised
        }
    }
    private var fg: Color {
        switch tone {
        case .success: Socle.C.successSoft
        case .warning: Socle.C.warningSoft
        case .danger: Socle.C.dangerSoft
        default: Socle.C.infoSoft
        }
    }
    private var border: Color {
        switch tone {
        case .success: Socle.C.successBorder
        case .warning: Socle.C.warningBorder
        case .danger: Socle.C.dangerBorder
        default: Socle.C.infoBorder
        }
    }
}

// MARK: Liste à sélection (flèches, double clic)

struct ListRow: Identifiable {
    let id: String
    let title: String
    var subtitle = ""
    var marked = false
    var warn = false
}

struct SelectList: View {
    let rows: [ListRow]
    @Binding var selection: String?
    var onDouble: () -> Void = {}
    @FocusState private var focused: Bool

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(rows) { r in
                        HStack(alignment: .firstTextBaseline, spacing: Socle.M.space2) {
                            Text(r.marked ? "●" : " ").socle(Socle.T.meta).foregroundStyle(Socle.C.success).frame(width: 12)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(r.title).socle(Socle.T.body).foregroundStyle(Socle.C.textStrong).lineLimit(2)
                                if !r.subtitle.isEmpty {
                                    Text(r.subtitle).socle(Socle.T.meta).foregroundStyle(r.warn ? Socle.C.warning : Socle.C.textMuted)
                                }
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, Socle.M.space2).padding(.vertical, Socle.M.space1_5)
                        .background(selection == r.id ? Socle.C.surfaceSelected : Color.clear)
                        .contentShape(Rectangle())
                        .onTapGesture(count: 2) { selection = r.id; onDouble() }
                        .simultaneousGesture(TapGesture().onEnded { selection = r.id; focused = true })
                        .id(r.id)
                    }
                }
            }
            .onChange(of: selection) { _, v in if let v { proxy.scrollTo(v) } }
        }
        .background(Socle.C.bgSunken)
        .overlay(Rectangle().stroke(focused ? Socle.C.focusRing : Socle.C.border, lineWidth: 1))
        .focusable()
        .focusEffectDisabled()
        .focused($focused)
        .onKeyPress(.upArrow) { move(-1); return .handled }
        .onKeyPress(.downArrow) { move(1); return .handled }
        .onKeyPress(.return) { onDouble(); return .handled }
    }

    private func move(_ d: Int) {
        guard !rows.isEmpty else { return }
        let i = rows.firstIndex { $0.id == selection } ?? (d > 0 ? -1 : rows.count)
        selection = rows[max(0, min(rows.count - 1, i + d))].id
    }
}

// MARK: Tableau simple (en-tête, lignes sélectionnables)

struct Column {
    let title: String
    var width: CGFloat? = nil   // nil : colonne qui prend la place restante
}

struct SimpleTable: View {
    let columns: [Column]
    let rows: [[String]]
    @Binding var selection: Int?
    var onDouble: () -> Void = {}

    var body: some View {
        VStack(spacing: 0) {
            line(columns.map(\.title), header: true)
                .background(Socle.C.surfaceRaised)
            Rectangle().fill(Socle.C.border).frame(height: 1)
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(rows.indices, id: \.self) { i in
                        line(rows[i], header: false)
                            .background(selection == i ? Socle.C.surfaceSelected : Color.clear)
                            .contentShape(Rectangle())
                            .onTapGesture(count: 2) { selection = i; onDouble() }
                            .simultaneousGesture(TapGesture().onEnded { selection = i })
                    }
                }
            }
        }
        .background(Socle.C.bgSunken)
        .overlay(Rectangle().stroke(Socle.C.border, lineWidth: 1))
    }

    private func line(_ cells: [String], header: Bool) -> some View {
        HStack(spacing: Socle.M.space3) {
            ForEach(columns.indices, id: \.self) { c in
                let t = c < cells.count ? cells[c] : ""
                Group {
                    if header {
                        Text(t).socle(Socle.T.labelStrong).foregroundStyle(Socle.C.textMuted)
                    } else {
                        Text(t).socle(Socle.T.body).foregroundStyle(Socle.C.text)
                    }
                }
                .lineLimit(1).truncationMode(.middle)
                .frame(minWidth: columns[c].width, maxWidth: columns[c].width ?? .infinity, alignment: .leading)
            }
        }
        .padding(.horizontal, Socle.M.space2).padding(.vertical, Socle.M.space1_5)
    }
}

// MARK: Boutons

extension View {
    func socleButton(_ v: SocleButtonStyle.Variant = .secondary) -> some View {
        buttonStyle(SocleButtonStyle(v, height: Socle.M.sizeControlLg - 2)).fixedSize()
    }
}

/// Ouvre un menu sous le pointeur (menu « Importer… »).
@MainActor func popMenu(_ items: [(String, () -> Void)]) {
    let menu = NSMenu()
    for (title, action) in items {
        let it = NSMenuItem(title: title, action: #selector(MenuAction.fire(_:)), keyEquivalent: "")
        let target = MenuAction(action)
        it.target = target
        it.representedObject = target
        menu.addItem(it)
    }
    menu.popUp(positioning: nil, at: NSEvent.mouseLocation, in: nil)
}

final class MenuAction: NSObject {
    let action: () -> Void
    init(_ a: @escaping () -> Void) { action = a }
    @objc func fire(_ sender: Any?) { action() }
}

// MARK: Dialogues (QMessageBox / QInputDialog de la version Python)

@MainActor enum Dialog {
    /// Essais scriptés (CSSETTINGS_SCRIPT) : réponses automatiques, messages consignés dans le journal.
    static var auto: AppModel?

    private static func alert(_ text: String, style: NSAlert.Style) -> NSAlert {
        let a = NSAlert()
        a.messageText = APP
        a.informativeText = text
        a.alertStyle = style
        return a
    }

    static func yes(_ text: String) -> Bool {
        if let m = auto { m.say("[oui] " + text.prefix(80)); return true }
        let a = alert(text, style: .informational)
        a.addButton(withTitle: L("Oui"))
        a.addButton(withTitle: L("Non"))
        return a.runModal() == .alertFirstButtonReturn
    }

    static func warn(_ text: String) {
        if let m = auto { m.say("[alerte] " + text); return }
        let a = alert(text, style: .warning)
        a.addButton(withTitle: L("OK"))
        a.runModal()
    }

    static func info(_ text: String) {
        if let m = auto { m.say("[info] " + text); return }
        let a = alert(text, style: .informational)
        a.addButton(withTitle: L("OK"))
        a.runModal()
    }

    static func ask(_ prompt: String, _ value: String = "") -> String? {
        if auto != nil { return value.isEmpty ? "Essai" : value }
        let a = alert(prompt, style: .informational)
        a.addButton(withTitle: L("OK"))
        a.addButton(withTitle: L("Annuler"))
        let field = NSTextField(string: value)
        field.frame = NSRect(x: 0, y: 0, width: 320, height: 24)
        a.accessoryView = field
        a.window.initialFirstResponder = field
        guard a.runModal() == .alertFirstButtonReturn else { return nil }
        let s = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        return s.isEmpty ? nil : s
    }

    static func folder(_ title: String, _ start: String) -> URL? {
        let p = NSOpenPanel()
        p.title = title
        p.canChooseDirectories = true
        p.canChooseFiles = false
        p.directoryURL = URL(fileURLWithPath: start)
        return p.runModal() == .OK ? p.url : nil
    }

    static func archive(_ title: String) -> URL? {
        let p = NSOpenPanel()
        p.title = title
        p.allowedContentTypes = ARCHIVES.compactMap { .init(filenameExtension: $0) }
        p.directoryURL = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads")
        return p.runModal() == .OK ? p.url : nil
    }
}

func reveal(_ url: URL) { NSWorkspace.shared.activateFileViewerSelecting([url]) }

// MARK: Travaux hors du fil de l'interface

@MainActor enum Jobs {
    /// Traitements en cours : la mise à jour automatique attend qu'ils finissent.
    static var active = 0

    typealias Progress = @Sendable (Int64, Int64) -> Void

    static func run<T>(_ work: @escaping @Sendable (_ progress: @escaping Progress) throws -> T,
                       progress: ((Int64, Int64) -> Void)? = nil,
                       done: @escaping (T) -> Void, failed: @escaping (Error) -> Void) {
        active += 1
        let report: Progress = { a, b in DispatchQueue.main.async { MainActor.assumeIsolated { progress?(a, b) } } }
        DispatchQueue.global(qos: .userInitiated).async {
            let r = Result { try work(report) }
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    active -= 1
                    switch r {
                    case .success(let v): done(v)
                    case .failure(let e): failed(e)
                    }
                }
            }
        }
    }
}

/// Message d'erreur lisible (et la catégorie, comme « LookupError » côté Python).
func errText(_ e: Error) -> String {
    if let c = e as? CoreError { return c.description }
    if let s = e as? Systems.Failure { return s.message }
    if let n = e as? Nexus.Failure { return n.message }
    return (e as NSError).localizedDescription
}

func isLookup(_ e: Error) -> Bool { if case CoreError.lookup = e { return true }; return false }

func humanSize(_ kb: JSON?) -> String {
    guard let kb = kb?.double else { return "" }
    let unit = { (fr: String, other: String) in I18n.lang == "fr" ? fr : other }
    return kb >= 1024 ? String(format: "%.1f ", kb / 1024) + unit("Mo", "MB") : String(format: "%.0f ", kb) + unit("Ko", "KB")
}
