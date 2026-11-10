// Mêmes essais que tests/test_core.py de la version Python.

@testable import CSCore
import XCTest

func tmpDir() -> URL {
    let d = FileManager.default.temporaryDirectory.appendingPathComponent("cstest_" + UUID().uuidString).standardizedFileURL
    try! FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
    return d
}

func put(_ root: URL, _ files: [String: String]) {
    for (rel, txt) in files {
        let p = root.sub(rel)
        try! FileManager.default.createDirectory(at: p.parent, withIntermediateDirectories: true)
        try! Data(txt.utf8).write(to: p)
    }
}

func text(_ u: URL) -> String { (try? String(contentsOf: u, encoding: .utf8)) ?? "<absent>" }
func json(_ u: URL) -> JObject { JSON.readObject(u) }
func j(_ s: String) -> JSON { try! JSON.parse(s) }
func mkdir(_ u: URL) { try! FileManager.default.createDirectory(at: u, withIntermediateDirectories: true) }

func zip(_ out: URL, _ files: [String: String]) {
    let src = tmpDir()
    put(src, files)
    let p = Process()
    p.executableURL = URL(fileURLWithPath: "/usr/bin/zip")
    p.arguments = ["-qr", out.path, "."]
    p.currentDirectoryURL = src
    try! p.run()
    p.waitUntilExit()
}

final class CoreTests: XCTestCase {
    override func setUp() { I18n.setLang("fr") }

    func cfg(_ tmp: URL) -> Config {
        let cs = tmp.sub("CommunityShaders")
        put(cs, ["SettingsUser.json": #"{"Version": "1-9-0-0", "x": 1}"#, "PostProcessing/mine.json": "{}", "Weathers/old.json": "{}"])
        return Config(["library": tmp.sub("lib").path, "cs_dir": cs.path, "backup_dir": tmp.sub("bk").path])
    }

    func testJSONGardeOrdreEtNombres() throws {
        let s = #"{"b": 1.0, "a": [1, 2e-3, "é\n"], "c": {}, "d": [], "e": null, "f": true}"#
        let v = try JSON.parse(s)
        XCTAssertEqual(v.object?.keys, ["b", "a", "c", "d", "e", "f"])
        XCTAssertEqual(v.serialized(indent: nil), #"{"b": 1.0, "a": [1, 2e-3, "é\n"], "c": {}, "d": [], "e": null, "f": true}"#)
        XCTAssertEqual(try JSON.parse(#"{"x": [1]}"#).serialized(indent: 1), "{\n \"x\": [\n  1\n ]\n}")
        XCTAssertEqual(try JSON.parse(#""\ud83d\ude00""#).string, "😀")
    }

    func testImportZipMO2EtApply() throws {
        let tmp = tmpDir(), cfg = cfg(tmp)
        let z = tmp.sub("p.zip")
        zip(z, ["SKSE/Plugins/CommunityShaders/SettingsUser.json": #"{"Version": "1-8-0-0", "x": 2}"#,
                "SKSE/Plugins/CommunityShaders/PostProcessing/theirs.json": "{}",
                "SKSE/Plugins/CommunityShaders/UnifiedWaterCache/cache.bin": "x"])
        let made = try importSource(cfg, z, name: "Test")
        XCTAssertEqual(made.map(\.name), ["Test"])
        let p = readPreset(made[0])
        XCTAssertTrue(p.hasSettings)
        XCTAssertEqual(p.version, "1.8.0.0")
        XCTAssertEqual(p.ppFiles, ["theirs.json"])
        XCTAssertFalse(made[0].sub("UnifiedWaterCache").exists)
        let saved = try applyPreset(cfg, made[0], label: "Test")
        let cs = cfg.csDir
        XCTAssertEqual(json(cs.sub("SettingsUser.json"))["x"], 2)
        XCTAssertTrue(cs.sub("PostProcessing/mine.json").exists && cs.sub("PostProcessing/theirs.json").exists)
        XCTAssertFalse(cs.sub("Weathers").exists)                             // éditeur du preset précédent retiré
        XCTAssertEqual(json(saved.sub("SettingsUser.json"))["x"], 1)          // sauvegarde avant application
        XCTAssertTrue(saved.sub("Weathers/old.json").exists)
        XCTAssertEqual(activePreset(cfg.library), "Test")
        XCTAssertEqual(listBackups(cfg).count, 1)
    }

    func testPresetPostTraitementSeul() throws {
        let tmp = tmpDir(), cfg = cfg(tmp)
        put(tmp.sub("src"), ["PostProcessing/pp.json": "{}"])
        let made = try importSource(cfg, tmp.sub("src"), name: "PP")
        try applyPreset(cfg, made[0], label: "PP")
        let cs = cfg.csDir
        XCTAssertEqual(json(cs.sub("SettingsUser.json"))["x"], 1)    // réglages inchangés
        XCTAssertTrue(cs.sub("PostProcessing/pp.json").exists && cs.sub("Weathers").exists)
    }

    func testArchiveSansPreset() {
        let tmp = tmpDir(), cfg = cfg(tmp)
        let z = tmp.sub("r.zip")
        zip(z, ["reshade-presets/x.ini": "[x]"])
        XCTAssertThrowsError(try importSource(cfg, z, name: "R")) { e in
            guard case CoreError.lookup = e else { return XCTFail("\(e)") }
        }
    }

    func game(_ tmp: URL) -> URL {
        let cs = tmp.sub("Data/SKSE/Plugins/CommunityShaders")
        for f in ["ScreenSpaceGI", "Skin", "PostProcessing"] { put(tmp, ["Data/Shaders/Features/\(f).ini": "[Info]\nVersion = 1-0-0\n"]) }
        put(cs, ["SettingsDefault.json": #"{"Version": "1-9-0-0", "General": {"Enable Shaders": true}, "Screen Space GI": {"AOPower": 1}, "Advanced Skin": {"F0": 1}, "Post Processing": {"ppsettings": {}}}"#,
                 // SettingsUser du jeu « pollué » par un preset incompatible : la section inconnue ne doit pas compter
                 "SettingsUser.json": #"{"Version": "1-9-0-0", "Physical Sky": {"x": 1}, "Post Processing": {"Vignette": {}, "LUT": {}}}"#])
        return cs
    }

    func testCompatibilite() throws {
        let tmp = tmpDir(), cs = game(tmp)
        let ref = try XCTUnwrap(gameReference(cs, cache: tmp.sub("ref.json")))
        XCTAssertEqual(ref.version, "1.9.0.0")
        XCTAssertFalse(ref.sectionNames().contains("Physical Sky"))
        put(tmp.sub("ok"), ["SettingsUser.json": #"{"Version": "1-9-0-0", "Screen Space GI": {"AOPower": 2}, "Advanced Skin": {"F0": 1}, "Post Processing": {}}"#])
        XCTAssertEqual(checkPreset(tmp.sub("ok"), ref).level, .ok)
        put(tmp.sub("bad"), ["SettingsUser.json": #"{"Version": "1-8-0-0", "Physical Sky": {}, "Screen Space GI": {"AOPower": 2, "EnableREBLUR": true}, "Disable at Boot": {"ScreenSpaceGI": false, "XeGTAO": false}}"#,
                             "PostProcessing/p.json": #"{"Vignette": {}, "Film Grain": {}, "preset_name": "p"}"#])
        let c = checkPreset(tmp.sub("bad"), ref)
        XCTAssertEqual(c.level, .warning)
        XCTAssertEqual(c.unknownFeatures, ["Physical Sky"])   // « Disable at Boot » : XeGTAO ignoré
        XCTAssertEqual(c.missingFeatures, ["Advanced Skin", "Post Processing"])
        XCTAssertEqual(c.unknownOptions, 1)
        XCTAssertEqual(c.unknownPP, ["Film Grain"])
        // la référence en cache sert tant que la version de CS ne change pas
        put(cs, ["SettingsUser.json": #"{"Post Processing": {"Film Grain": {}}}"#])
        XCTAssertFalse(try XCTUnwrap(gameReference(cs, cache: tmp.sub("ref.json"))).pp.contains("Film Grain"))
    }

    func testPostTraitementRejete() {
        // Chaîne sans Composite (preset CS 1.4.6, comme Yogurt's 0.3) : Bottled la remplace par une chaîne vide.
        let tmp = tmpDir()
        let ref = Reference(version: "1.9.0.0", features: ["postprocessing"], sections: [("Post Processing", ["ppsettings"])],
                            pp: ["COD Bloom", "Composite", "LUT", "Vignette", "ppsettings", "preset_name"])
        func preset(_ name: String, _ version: String, _ pp: String) -> Compat {
            put(tmp.sub(name), ["SettingsUser.json": #"{"Version": "\#(version)", "Post Processing": \#(pp)}"#])
            return checkPreset(tmp.sub(name), ref)
        }
        var c = preset("sans_composite", "1-9-0-0", #"{"COD Bloom": {}, "LUT": {}, "ppsettings": {}}"#)
        XCTAssertEqual(c.level, .warning)
        XCTAssertEqual(c.ppRejected, ["composite"])
        c = preset("yogurt", "1-4-6-0", #"{"COD Bloom": {}, "PotatoFX Camera": {}, "ppsettings": {}}"#)
        XCTAssertEqual(c.ppRejected, ["composite", "unknown", "version"])
        XCTAssertEqual(c.unknownPP, ["PotatoFX Camera"])
        XCTAssertEqual(c.presetVersion, "1.4.6.0")
        // chaîne complète, ou vide (rien à perdre) : pas de rejet
        XCTAssertEqual(preset("complet", "1-8-0-0", #"{"COD Bloom": {}, "Composite": {}, "ppsettings": {}}"#).level, .ok)
        XCTAssertEqual(preset("vide", "1-4-6-0", #"{"ppsettings": {}}"#).ppRejected, [])
    }

    func testNexusLiens() throws {
        let i = try Nexus.parseNxm("nxm://SkyrimSpecialEdition/mods/165803/files/700123?key=abc&expires=1760000000&user_id=1")
        XCTAssertEqual(i, Nexus.NxmLink(game: "skyrimspecialedition", modId: 165803, fileId: 700123, key: "abc", expires: "1760000000"))
        for bad in ["https://www.nexusmods.com/x", "nxm://skyrimspecialedition/mods/1"] {
            XCTAssertThrowsError(try Nexus.parseNxm(bad))
        }
        XCTAssertEqual(Nexus.searchURL("Community Shaders preset"),
                       "https://www.nexusmods.com/games/skyrimspecialedition/mods?keyword=Community%20Shaders%20preset&sort=endorsements")
        XCTAssertEqual(try Nexus.parseModId("https://www.nexusmods.com/skyrimspecialedition/mods/165803?tab=files"), 165803)
        XCTAssertEqual(try Nexus.parseModId(" 42 "), 42)
        XCTAssertThrowsError(try Nexus.parseModId("abc"))
    }

    func testPresetAvecEnb() throws {
        let tmp = tmpDir(), cs = game(tmp)
        let root = tmp   // racine du jeu : Data/SKSE/Plugins/CommunityShaders → 4 niveaux
        put(root, ["enbseries/enbeffect.fx": "ancien", "enbseries/KiLoaderSatelliteENB.dllplugin": "module",
                   "enbseries.ini": "[GLOBAL]\nUseEffect=true\n"])
        let cfg = Config(["library": tmp.sub("lib").path, "cs_dir": cs.path, "backup_dir": tmp.sub("bk").path])
        let pr = tmp.sub("lib/Cine")
        put(pr, ["SettingsUser.json": #"{"Version": "1-9-0-0", "x": 3}"#, "ENB/enbseries.ini": "[GLOBAL]\nUseEffect=true\n; neuf\n",
                 "ENB/enbseries/enbeffect.fx": "neuf", "LISEZMOI.md": "notes", "Apercus/a.png": "x"])
        XCTAssertTrue(readPreset(pr).hasEnb)
        let saved = try applyPreset(cfg, pr, label: "Cine")
        XCTAssertEqual(text(root.sub("enbseries/enbeffect.fx")), "neuf")
        XCTAssertTrue(text(root.sub("enbseries.ini")).contains("neuf"))
        XCTAssertEqual(text(root.sub("enbseries/KiLoaderSatelliteENB.dllplugin")), "module")   // module KiLoader gardé
        XCTAssertFalse(cs.sub("ENB").exists || cs.sub("LISEZMOI.md").exists || cs.sub("Apercus").exists)
        XCTAssertEqual(text(saved.sub("ENB/enbseries/enbeffect.fx")), "ancien")
        XCTAssertTrue(readPreset(saved).hasEnb)
        let second = try applyPreset(cfg, saved, label: nil)   // restauration, dans la même seconde
        XCTAssertNotEqual(second, saved)
        XCTAssertEqual(text(root.sub("enbseries/enbeffect.fx")), "ancien")
        XCTAssertEqual(text(saved.sub("ENB/enbseries/enbeffect.fx")), "ancien")   // sauvegarde intacte
        XCTAssertEqual(text(second.sub("ENB/enbseries/enbeffect.fx")), "neuf")
    }

    func testFrameGenerationForcee() {
        // frameGenerationForceEnable fait planter le jeu sous CrossOver (proxy D3D12, E_NOINTERFACE).
        let tmp = tmpDir()
        let ref = Reference(version: "1.9.0.0", features: ["upscaling"], sections: [("Upscaling", ["frameGenerationForceEnable"])], pp: [])
        for (force, expected) in [(1, true), (0, false)] {
            put(tmp.sub("\(force)"), ["SettingsUser.json": #"{"Version": "1-9-0-0", "Upscaling": {"frameGenerationForceEnable": \#(force)}}"#])
            let c = checkPreset(tmp.sub("\(force)"), ref)
            XCTAssertEqual(c.frameGen, expected)
            XCTAssertEqual(c.level == .warning, expected)
        }
    }

    func testPreferencesJoueurGardees() throws {
        // Un preset (Cabbage) ne remplace pas les raccourcis du menu CS ni les threads de compilation du joueur.
        let tmp = tmpDir()
        let cs = tmp.sub("Data/SKSE/Plugins/CommunityShaders")
        put(cs, ["SettingsUser.json": #"{"Version": "1-9-0-0", "Menu": {"ToggleKey": 99}, "Advanced": {"Compiler Threads": 16}, "Vignette": {"x": 0}}"#])
        let cfg = Config(["library": tmp.sub("lib").path, "cs_dir": cs.path, "backup_dir": tmp.sub("bk").path])
        let pr = tmp.sub("lib/Cabbage")
        put(pr, ["SettingsUser.json": #"{"Version": "1-8-0-0", "Menu": {"ToggleKey": 35}, "Advanced": {"Compiler Threads": 18}, "Vignette": {"x": 1}}"#])
        let saved = try applyPreset(cfg, pr, label: "Cabbage")
        let d = json(cs.sub("SettingsUser.json"))
        XCTAssertEqual(d["Menu"], j(#"{"ToggleKey": 99}"#))
        XCTAssertEqual(d["Advanced"], j(#"{"Compiler Threads": 16}"#))
        XCTAssertEqual(d["Vignette"], j(#"{"x": 1}"#))
        XCTAssertEqual(d.keys, ["Version", "Menu", "Advanced", "Vignette"])   // ordre des sections gardé
        XCTAssertEqual(json(pr.sub("SettingsUser.json"))["Menu"]?["ToggleKey"], 35)   // preset intact
        try applyPreset(cfg, saved, label: nil)   // restauration : tout tel quel
        XCTAssertEqual(json(cs.sub("SettingsUser.json"))["Vignette"], j(#"{"x": 0}"#))
    }

    func testPresetsEnb() throws {
        // Preset ENB : liste, application avec sauvegarde, modules KiLoader gardés, enregistrement de l'ENB en place.
        let tmp = tmpDir()
        let cs = tmp.sub("jeu/Data/SKSE/Plugins/CommunityShaders")
        mkdir(cs)
        let root = tmp.sub("jeu")
        put(root, ["enbseries.ini": "ancien", "enbseries/enbeffect.fx": "ancien", "enbseries/Sat.dllplugin": "module",
                   "enbcache/datavs.enbc": "cache de l'ancien preset"])
        let lib = tmp.sub("enb")
        put(lib, ["Doux/enbseries.ini": "neuf", "Doux/enbseries/enbeffect.fx": "neuf"])
        mkdir(lib.sub("Pack/KiLoader"))   // paquet, pas un preset
        let cfg = Config(["library": tmp.sub("cs").path, "enb_library": lib.path, "cs_dir": cs.path, "backup_dir": tmp.sub("bk").path])
        XCTAssertEqual(listEnbPresets(lib).map(\.name), ["Doux"])
        XCTAssertEqual(listEnbPresets(lib)[0].ppFiles, ["enbeffect.fx"])
        let saved = try applyEnbPreset(cfg, lib.sub("Doux"), label: "Doux")
        XCTAssertEqual(text(root.sub("enbseries.ini")), "neuf")
        XCTAssertEqual(text(root.sub("enbseries/enbeffect.fx")), "neuf")
        XCTAssertEqual(text(root.sub("enbseries/Sat.dllplugin")), "module")   // module d'installation gardé
        XCTAssertEqual(text(saved.sub("ENB/enbseries.ini")), "ancien")         // rien d'effacé
        XCTAssertFalse(root.sub("enbcache").exists)                            // cache d'ENB supprimé
        XCTAssertEqual(activePreset(lib), "Doux")
        let dest = try saveCurrentEnb(cfg, name: "Mon ENB")
        XCTAssertEqual(text(dest.sub("enbseries.ini")), "neuf")
        XCTAssertFalse(dest.sub("enbseries/Sat.dllplugin").exists)
        XCTAssertThrowsError(try saveCurrentEnb(cfg, name: "Mon ENB")) { e in
            guard case CoreError.exists = e else { return XCTFail("\(e)") }
        }
    }

    func testDetectionDuJeu() {
        // Seul un processus qui lance SkyrimSE.exe compte : ni un outil qui le cite, ni CrossOver seul.
        let bruit = "  501 /bin/zsh -c pgrep -if SkyrimSE.exe\n"
            + "  502 /opt/homebrew/bin/node server.js --watch SkyrimSE.exe\n"
            + "  503 /usr/bin/python3 check.py C:\\Games\\SkyrimSE.exe\n"
            + "  504 C:\\windows\\system32\\winedevice.exe\n"
            + "  505 /Applications/CrossOver Preview.app/Contents/MacOS/CrossOver Preview\n"
        XCTAssertTrue(parseGameProcesses(bruit).isEmpty)
        XCTAssertEqual(parseGameProcesses(bruit + "  777 /x/wine64-preloader C:\\Games\\Skyrim Special Edition\\SkyrimSE.exe\n").map(\.pid), [777])
        XCTAssertEqual(parseGameProcesses("  778 C:\\Games\\Skyrim Special Edition\\SkyrimSE.exe\n").map(\.pid), [778])
        XCTAssertTrue(parseGameProcesses("  779 C:\\Games\\SkyrimSE.exe\n", ownPid: 779).isEmpty)
    }

    func testBackendBouteille() throws {
        // Le backend est lu dans cxbottle.conf, jamais modifié ; vide si le fichier manque.
        let tmp = tmpDir()
        let bottle = tmp.sub("Bouteille"), g = bottle.sub("drive_c/Games/Skyrim")
        mkdir(g)
        XCTAssertEqual(bottleBackend(g), "")
        let conf = bottle.sub("cxbottle.conf")
        put(bottle, ["cxbottle.conf": "[Bottle]\n[EnvironmentVariables]\n\"CX_GRAPHICS_BACKEND\" = \"DXVK\"\n\"WINEMSYNC\" = \"1\"\n"])
        let before = try Data(contentsOf: conf)
        XCTAssertEqual(bottleBackend(g), "dxvk")
        XCTAssertEqual(try Data(contentsOf: conf), before)
        put(bottle, ["cxbottle.conf": "[EnvironmentVariables]\n;;\"CX_GRAPHICS_BACKEND\" = \"dxmt\"\n"])
        XCTAssertEqual(bottleBackend(g), "")
        XCTAssertEqual(BACKEND_FOR, ["ENB": "dxvk", "CS": "dxmt"])
        XCTAssertEqual(gameDir(URL.path("/a/b/Data/SKSE/Plugins/CommunityShaders")).path, "/a/b")
    }

    func testSafeNameEtRetrait() throws {
        XCTAssertEqual(safeName(" a/b:c? "), "a-b-c-")
        XCTAssertEqual(safeName(" .. "), "Preset")
        let tmp = tmpDir(), cfg = cfg(tmp)
        put(cfg.library, ["P/SettingsUser.json": "{}"])
        XCTAssertEqual(listPresets(cfg.library).map(\.name), ["P"])
        let dest = try removePreset(cfg, cfg.library.sub("P"))
        XCTAssertTrue(dest.sub("SettingsUser.json").exists)
        XCTAssertTrue(listPresets(cfg.library).isEmpty)
        XCTAssertTrue(listBackups(cfg).isEmpty)   // _presets_retires n'est pas une sauvegarde
    }

    func testConfigEtTraductions() throws {
        Config.file = tmpDir().sub("config.json")
        var c = Config.load()
        XCTAssertEqual(c["lang"], "auto")
        c["library"] = "/x"
        c.tab = 3
        try c.save()
        let d = Config.load()
        XCTAssertEqual(d["library"], "/x")
        XCTAssertEqual(d.tab, 3)
        // placeholders identiques dans toutes les langues
        let re = try NSRegularExpression(pattern: #"\{\w+\}"#)
        func ph(_ s: String) -> [String] {
            re.matches(in: s, range: NSRange(s.startIndex..., in: s)).map { String(s[Range($0.range, in: s)!]) }.sorted()
        }
        for (fr, tr) in translations {
            XCTAssertEqual(tr.count, 3, fr)
            for t in tr { XCTAssertEqual(ph(t), ph(fr), "\(fr) → \(t)") }
        }
        I18n.setLang("en")
        XCTAssertEqual(L("Réglages"), "Settings")
        XCTAssertEqual(I18n.systemLang(["de-DE", "ja"]), "en")
        XCTAssertEqual(I18n.systemLang(["it-IT"]), "it")
    }
}
