// Mêmes essais que tests/test_systems.py de la version Python.

@testable import CSCore
import XCTest

typealias Sy = Systems

func fakeExe(_ game: URL, _ v: (UInt32, UInt32, UInt32, UInt32) = (1, 6, 1170, 0)) {
    let ms = (v.0 << 16) | v.1, ls = (v.2 << 16) | v.3
    func le(_ x: UInt32) -> [UInt8] { (0..<4).map { UInt8((x >> (8 * $0)) & 0xFF) } }
    let blob: [UInt8] = Array("MZ".utf8) + [UInt8](repeating: 0, count: 64) + [0xBD, 0x04, 0xEF, 0xFE, 0, 0, 1, 0] + le(ms) + le(ls)
        + [UInt8](repeating: 0, count: 64)
    try! Data(blob).write(to: game.sub("SkyrimSE.exe"))
    put(game, ["skse64_loader.exe": "skse"])
}

final class SystemsTests: XCTestCase {
    var game: URL!, bases: [String: URL]!, sauv: URL!, tmp: URL!

    override func setUp() {
        I18n.setLang("fr")
        Sy.safeCopyHook = nil
        tmp = tmpDir()
        game = tmp.sub("Skyrim")
        mkdir(game)
        fakeExe(game)
        put(game, ["Data/Skyrim.esm": "vanille", "d3d11.dll": "mon pont"])
        let b = tmp.sub("bases")
        put(b.sub("CS"), ["d3d11.dll": "pont mDLSS", "Data/SKSE/Plugins/CommunityShaders.dll": "cs",
                          "Data/Shaders/Features/a.ini": "a", "systeme.json": "{}"])
        put(b.sub("ENB"), ["d3d11.dll": "enb", "enbseries.ini": "[GLOBAL]", "Data/Shaders/Upscaling/u.dll": "u"])
        put(b.sub("commun"), ["Data/KiLoader/KiLoader.dll": "ki"])
        bases = ["CS": b.sub("CS"), "ENB": b.sub("ENB"), "commun": b.sub("commun")]
        sauv = tmp.sub("sauv")
    }

    override func tearDown() { Sy.safeCopyHook = nil }

    func files(_ root: URL) -> [String: Data] {
        Dictionary(uniqueKeysWithValues: walkFiles(root).map { ($0.rel, try! Data(contentsOf: $0.url)) })
    }

    func testVersionEtPrerequis() {
        XCTAssertEqual(Sy.gameVersion(game), "1.6.1170.0")
        XCTAssertEqual(Sy.prerequis(game), [])
        fakeExe(game, (1, 5, 97, 0))
        XCTAssertTrue(Sy.prerequis(game)[0].contains("1.5.97.0"))
        fakeExe(game)
        try! FileManager.default.removeItem(at: game.sub("skse64_loader.exe"))
        XCTAssertTrue(Sy.prerequis(game)[0].contains("SKSE"))
    }

    func testPlanSansEcriture() {
        let p = Sy.planInstall(game, "CS", bases["CS"]!)
        XCTAssertEqual(p.replace, ["d3d11.dll"])
        XCTAssertEqual(p.add.sorted(), ["Data/SKSE/Plugins/CommunityShaders.dll", "Data/Shaders/Features/a.ini"])
        XCTAssertFalse(game.sub(Sy.MANIFEST).exists || sauv.exists)
    }

    func testInstallerRetirerRemetLOriginal() throws {
        try Sy.install(game, "CS", bases["CS"]!, sauv)
        XCTAssertEqual(text(game.sub("d3d11.dll")), "pont mDLSS")
        XCTAssertEqual(Sy.activeSystem(game), "CS")
        XCTAssertEqual(try Sy.verify(game, "CS"), Sy.Verification())
        put(game, ["Data/Shaders/Features/a.ini": "modifié par le joueur"])
        XCTAssertEqual(try Sy.verify(game, "CS").modified, ["Data/Shaders/Features/a.ini"])
        let op = try Sy.remove(game, "CS", sauv)
        XCTAssertEqual(text(game.sub("d3d11.dll")), "mon pont")   // original remis
        XCTAssertFalse(game.sub("Data/SKSE").exists || game.sub("Data/Shaders").exists)   // dossiers vides retirés
        XCTAssertEqual(text(game.sub("Data/Skyrim.esm")), "vanille")
        XCTAssertEqual(text(op.sub("retires/Data/Shaders/Features/a.ini")), "modifié par le joueur")   // rien de perdu
        XCTAssertEqual(Sy.installed(game), [])
    }

    func testSwapCsEnbEtRetour() throws {
        try Sy.swap(game, current: nil, target: "CS", bases: bases, sauv)
        XCTAssertEqual(Sy.installed(game), ["commun", "CS"])
        try Sy.swap(game, current: "CS", target: "ENB", bases: bases, sauv)
        XCTAssertEqual(Sy.installed(game), ["commun", "ENB"])
        XCTAssertEqual(text(game.sub("d3d11.dll")), "enb")
        XCTAssertFalse(game.sub("Data/SKSE/Plugins/CommunityShaders.dll").exists)
        XCTAssertTrue(game.sub("Data/KiLoader/KiLoader.dll").exists)   // commun jamais retiré
        try Sy.swap(game, current: "ENB", target: "CS", bases: bases, sauv)
        XCTAssertEqual(text(game.sub("d3d11.dll")), "pont mDLSS")
        XCTAssertFalse(game.sub("enbseries.ini").exists)
        try Sy.remove(game, "CS", sauv)
        try Sy.remove(game, "commun", sauv)
        XCTAssertEqual(text(game.sub("d3d11.dll")), "mon pont")   // retour complet à l'origine
    }

    func testFichierDejaIdentiqueJamaisRetire() throws {
        put(game, ["enbseries.ini": "[GLOBAL]"])   // déjà là, identique à la base
        try Sy.install(game, "ENB", bases["ENB"]!, sauv)
        try Sy.remove(game, "ENB", sauv)
        XCTAssertEqual(text(game.sub("enbseries.ini")), "[GLOBAL]")
    }

    func testEchecInstallationAnnulee() throws {
        Sy.safeCopyHook = { src, dst in
            if src.name == "a.ini" { throw CoreError.runtime("disque plein") }
            try Sy.realSafeCopy(src, dst)
        }
        XCTAssertThrowsError(try Sy.install(game, "CS", bases["CS"]!, sauv)) { XCTAssertTrue($0 is Sy.Failure) }
        Sy.safeCopyHook = nil
        XCTAssertEqual(text(game.sub("d3d11.dll")), "mon pont")
        XCTAssertEqual(Sy.installed(game), [])
        XCTAssertFalse(game.sub("Data/SKSE").exists)
        XCTAssertFalse(walkFiles(game).contains { $0.rel.hasSuffix(".csnew") })
        XCTAssertEqual(Sy.listOperations(sauv).first?.status, "annulé")
    }

    func testSwapEchecRemetLeSystemePrecedent() throws {
        try Sy.swap(game, current: nil, target: "CS", bases: bases, sauv)
        Sy.safeCopyHook = { src, dst in
            if src.name == "u.dll" { throw CoreError.runtime("boom") }
            try Sy.realSafeCopy(src, dst)
        }
        XCTAssertThrowsError(try Sy.swap(game, current: "CS", target: "ENB", bases: bases, sauv))
        XCTAssertEqual(Sy.activeSystem(game), "CS")
        XCTAssertEqual(text(game.sub("d3d11.dll")), "pont mDLSS")
    }

    func testRefus() throws {
        XCTAssertThrowsError(try Sy.install(game, "CS", bases["CS"]!, sauv, isRunning: { true })) {
            XCTAssertTrue("\($0)".contains("lancé"))
        }
        fakeExe(game, (1, 5, 97, 0))
        XCTAssertThrowsError(try Sy.install(game, "CS", bases["CS"]!, sauv)) { XCTAssertTrue("\($0)".contains("1.5.97")) }
        fakeExe(game)
        try Sy.install(game, "CS", bases["CS"]!, sauv)
        XCTAssertThrowsError(try Sy.install(game, "ENB", bases["ENB"]!, sauv)) { XCTAssertTrue("\($0)".contains("échange")) }
    }

    func testAssembleFiltresEtAtomique() throws {
        let a = tmp.sub("a"), b = tmp.sub("b")
        put(a, ["Data/x.dll": "A", "Data/SKSE/Plugins/SettingsUser.json": "perso", "Data/SKSE/Plugins/Tweaks.ini": "t"])
        put(b, ["x.dll": "B"])
        let dest = tmp.sub("CS")
        let n = try Sy.assemble(dest, [Sy.Source(a, exclude: ["*SettingsUser.json"]), Sy.Source(b, prefix: "Data/")], name: "CS")
        XCTAssertEqual(n, 2)
        XCTAssertEqual(text(dest.sub("Data/x.dll")), "B")
        XCTAssertFalse(dest.sub("Data/SKSE/Plugins/SettingsUser.json").exists)
        XCTAssertEqual(json(dest.sub(Sy.INFO))["fichiers"], 2)
        XCTAssertThrowsError(try Sy.assemble(dest, [Sy.Source(a)], name: "CS"))   // jamais d'écrasement
        XCTAssertThrowsError(try Sy.assemble(tmp.sub("X"), [Sy.Source(tmp.sub("absent"))], name: "X"))
        XCTAssertFalse(tmp.sub("X").exists || tmp.sub("X.en_construction").exists)
        XCTAssertEqual(Sy.availableBases(tmp).keys.sorted(), ["CS"])
    }

    func testPlanSwapAdoptEtHistorique() throws {
        put(game, ["Data/Shaders/Features/a.ini": "a", "Data/SKSE/Plugins/CommunityShaders.dll": "cs", "d3d11.dll": "pont mDLSS"])
        XCTAssertTrue(Sy.adoptable(game, bases["CS"]!))
        XCTAssertFalse(Sy.adoptable(game, bases["ENB"]!))
        try Sy.install(game, "CS", bases["CS"]!, sauv, adopt: true)   // reprend l'installation faite à la main
        XCTAssertTrue(Sy.readManifest(game)["CS"]!.files.allSatisfy { !$0.1.pre })
        put(game, ["Data/Shaders/Features/a.ini": "réglé par le joueur"])
        let pl = Sy.planSwap(game, current: "CS", target: "ENB", base: bases["ENB"]!)
        XCTAssertEqual(pl.remove, 3)
        XCTAssertEqual(pl.aside, ["Data/Shaders/Features/a.ini"])
        XCTAssertEqual(pl.add, 3)
        try Sy.swap(game, current: "CS", target: "ENB", bases: bases, sauv)   // le CS adopté est bien retiré
        XCTAssertFalse(game.sub("Data/SKSE/Plugins/CommunityShaders.dll").exists)
        XCTAssertEqual(text(game.sub("d3d11.dll")), "enb")
        let ops = Set(Sy.listOperations(sauv).map { "\($0.type)|\($0.layer)|\($0.status)" })
        XCTAssertTrue(ops.isSuperset(of: ["remove|CS|terminé", "install|ENB|terminé"]))
    }

    func testAdoptNeCopieRien() throws {
        put(game, ["Data/Shaders/Features/a.ini": "a"])   // le reste de la base manque dans le jeu
        let before = files(game)
        try Sy.install(game, "CS", bases["CS"]!, sauv, adopt: true)
        var after = files(game)
        after[Sy.MANIFEST] = nil
        XCTAssertEqual(after, before)
        XCTAssertEqual(Sy.readManifest(game)["CS"]!.files.map(\.0), ["Data/Shaders/Features/a.ini"])
    }

    func testDropFilesEtHelpersExclus() throws {
        put(game, ["Data/SKSE/plugins/ENBHelperPlus.dll": "h"])
        put(bases["ENB"]!, ["Data/SKSE/plugins/ENBHelperPlus.dll": "h"])
        try Sy.install(game, "ENB", bases["ENB"]!, sauv, adopt: true)
        let op = try Sy.dropFiles(game, "ENB", ["Data/SKSE/plugins/ENBHelperPlus.dll"], sauv)
        XCTAssertFalse(game.sub("Data/SKSE/plugins/ENBHelperPlus.dll").exists)
        XCTAssertEqual(text(op.sub("retires/Data/SKSE/plugins/ENBHelperPlus.dll")), "h")   // copie gardée
        XCTAssertNil(Sy.readManifest(game)["ENB"]!.meta("Data/SKSE/plugins/ENBHelperPlus.dll"))
        XCTAssertEqual(try Sy.verify(game, "ENB"), Sy.Verification())
        let src = tmp.sub("pkg")
        put(src, ["Data/SKSE/plugins/ENBHelperSE.dll": "x", "Data/SKSE/plugins/Autre.dll": "y"])
        let dest = tmp.sub("base")
        try Sy.assemble(dest, [Sy.Source(src, exclude: Sy.ENB_INCOMPATIBLES)], name: "ENB")
        XCTAssertTrue(dest.sub("Data/SKSE/plugins/Autre.dll").exists)
        XCTAssertFalse(dest.sub("Data/SKSE/plugins/ENBHelperSE.dll").exists)
    }

    func testAssembleCorrectifs() throws {
        let src = tmp.sub("pkg")
        put(src, ["Data/x.ini": "[A]\nFrameGeneration=1\n"])
        let dest = tmp.sub("base")
        try Sy.assemble(dest, [Sy.Source(src, patches: [("Data/x.ini", "FrameGeneration=1", "FrameGeneration=0")])], name: "ENB")
        XCTAssertEqual(text(dest.sub("Data/x.ini")), "[A]\nFrameGeneration=0\n")
        XCTAssertTrue(text(src.sub("Data/x.ini")).contains("=1"))
        XCTAssertThrowsError(try Sy.assemble(tmp.sub("b2"), [Sy.Source(src, patches: [("Data/x.ini", "absent", "x")])], name: "ENB")) {
            XCTAssertTrue("\($0)".contains("Correctif"))
        }
        XCTAssertFalse(tmp.sub("b2").exists || tmp.sub("b2.en_construction").exists)
    }

    func testManifesteDeLaVersionPythonRelu() throws {
        // Manifeste écrit par la version Python : relu à l'identique (ordre des couches compris).
        let py = """
        {
         "layers": {
          "commun": {"files": {"Data/KiLoader/KiLoader.dll": {"fp": "2:x", "pre": false}}, "date": "d", "operation": "op1", "remplacés": []},
          "CS": {"files": {}, "date": "d", "operation": "op2", "remplacés": ["d3d11.dll"]}
         }
        }
        """
        put(game, [Sy.MANIFEST: py])
        XCTAssertEqual(Sy.installed(game), ["commun", "CS"])
        XCTAssertEqual(Sy.activeSystem(game), "CS")
        XCTAssertEqual(Sy.readManifest(game)["CS"]?.replaced, ["d3d11.dll"])
        XCTAssertEqual(try Sy.fingerprint(game.sub("d3d11.dll")), "8:012637dd55957c8b905b71277f47f998")   // même empreinte que Python
    }
}
