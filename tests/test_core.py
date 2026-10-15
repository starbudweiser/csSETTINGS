import json, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import core  # noqa: E402

def _cfg(tmp):
    cs = tmp / "CommunityShaders"; (cs / "PostProcessing").mkdir(parents=True)
    (cs / "SettingsUser.json").write_text(json.dumps({"Version": "1-9-0-0", "x": 1}))
    (cs / "PostProcessing" / "mine.json").write_text("{}")
    (cs / "Weathers").mkdir(); (cs / "Weathers" / "old.json").write_text("{}")
    return {"library": str(tmp / "lib"), "cs_dir": str(cs), "backup_dir": str(tmp / "bk")}

def test_import_zip_mo2_et_apply(tmp_path):
    cfg = _cfg(tmp_path)
    z = tmp_path / "p.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("SKSE/Plugins/CommunityShaders/SettingsUser.json", json.dumps({"Version": "1-8-0-0", "x": 2}))
        f.writestr("SKSE/Plugins/CommunityShaders/PostProcessing/theirs.json", "{}")
        f.writestr("SKSE/Plugins/CommunityShaders/UnifiedWaterCache/cache.bin", "x")
    made = core.import_source(cfg, z, "Test")
    assert [p.name for p in made] == ["Test"]
    p = core.read_preset(made[0])
    assert p.has_settings and p.version == "1.8.0.0" and p.pp_files == ["theirs.json"]
    assert not (made[0] / "UnifiedWaterCache").exists()
    saved = core.apply_preset(cfg, made[0], "Test")
    cs = Path(cfg["cs_dir"])
    assert json.loads((cs / "SettingsUser.json").read_text())["x"] == 2
    assert (cs / "PostProcessing" / "mine.json").exists() and (cs / "PostProcessing" / "theirs.json").exists()
    assert not (cs / "Weathers").exists()                     # données d'éditeur du preset précédent retirées
    assert json.loads((saved / "SettingsUser.json").read_text())["x"] == 1   # sauvegarde avant application
    assert (saved / "Weathers" / "old.json").exists()
    assert core.active_preset(cfg["library"]) == "Test"

def test_preset_post_traitement_seul(tmp_path):
    cfg = _cfg(tmp_path)
    d = tmp_path / "src" / "PostProcessing"; d.mkdir(parents=True); (d / "pp.json").write_text("{}")
    made = core.import_source(cfg, tmp_path / "src", "PP")
    core.apply_preset(cfg, made[0], "PP")
    cs = Path(cfg["cs_dir"])
    assert json.loads((cs / "SettingsUser.json").read_text())["x"] == 1   # réglages inchangés
    assert (cs / "PostProcessing" / "pp.json").exists() and (cs / "Weathers").exists()

def test_archive_sans_preset(tmp_path):
    cfg = _cfg(tmp_path)
    z = tmp_path / "r.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("reshade-presets/x.ini", "[x]")
    try:
        core.import_source(cfg, z, "R"); assert False
    except LookupError:
        pass

def _game(tmp):
    """Arborescence Data minimale : CS installé avec deux features."""
    cs = tmp / "Data" / "SKSE" / "Plugins" / "CommunityShaders"; cs.mkdir(parents=True)
    feats = tmp / "Data" / "Shaders" / "Features"; feats.mkdir(parents=True)
    for f in ("ScreenSpaceGI", "Skin", "PostProcessing"):
        (feats / f"{f}.ini").write_text("[Info]\nVersion = 1-0-0\n")
    (cs / "SettingsDefault.json").write_text(json.dumps({
        "Version": "1-9-0-0", "General": {"Enable Shaders": True},
        "Screen Space GI": {"AOPower": 1}, "Advanced Skin": {"F0": 1}, "Post Processing": {"ppsettings": {}}}))
    # SettingsUser du jeu « pollué » par un preset incompatible : la section inconnue ne doit pas compter
    (cs / "SettingsUser.json").write_text(json.dumps({
        "Version": "1-9-0-0", "Physical Sky": {"x": 1}, "Post Processing": {"Vignette": {}, "LUT": {}}}))
    return cs

def test_compatibilite(tmp_path):
    cs = _game(tmp_path)
    ref = core.game_reference(str(cs), tmp_path / "ref.json")
    assert ref["version"] == "1.9.0.0" and "Physical Sky" not in ref["sections"]
    ok = tmp_path / "ok"; ok.mkdir()
    (ok / "SettingsUser.json").write_text(json.dumps({"Version": "1-9-0-0", "Screen Space GI": {"AOPower": 2},
                                                      "Advanced Skin": {"F0": 1}, "Post Processing": {}}))
    assert core.check_preset(ok, ref).level == "ok"
    bad = tmp_path / "bad"; (bad / "PostProcessing").mkdir(parents=True)
    (bad / "SettingsUser.json").write_text(json.dumps({
        "Version": "1-8-0-0", "Physical Sky": {}, "Screen Space GI": {"AOPower": 2, "EnableREBLUR": True},
        "Disable at Boot": {"ScreenSpaceGI": False, "XeGTAO": False}}))
    (bad / "PostProcessing" / "p.json").write_text(json.dumps({"Vignette": {}, "Film Grain": {}, "preset_name": "p"}))
    c = core.check_preset(bad, ref)
    assert c.level == "warning"
    assert c.unknown_features == ["Physical Sky"]       # « Disable at Boot » : XeGTAO ignoré
    assert c.missing_features == ["Advanced Skin", "Post Processing"] and c.unknown_options == 1 and c.unknown_pp == ["Film Grain"]
    # la référence en cache sert tant que la version de CS ne change pas
    (cs / "SettingsUser.json").write_text(json.dumps({"Post Processing": {"Film Grain": {}}}))
    assert "Film Grain" not in core.game_reference(str(cs), tmp_path / "ref.json")["pp"]

def test_post_traitement_rejete(tmp_path):
    """Chaîne sans Composite (preset CS 1.4.6, comme Yogurt's 0.3) : Bottled la remplace par une chaîne vide."""
    ref = {"version": "1.9.0.0", "features": ["postprocessing"], "sections": {"Post Processing": ["ppsettings"]},
           "pp": ["COD Bloom", "Composite", "LUT", "Vignette", "ppsettings", "preset_name"]}
    def preset(name, version, pp):
        d = tmp_path / name; d.mkdir()
        (d / "SettingsUser.json").write_text(json.dumps({"Version": version, "Post Processing": pp}))
        return core.check_preset(d, ref)
    c = preset("sans_composite", "1-9-0-0", {"COD Bloom": {}, "LUT": {}, "ppsettings": {}})
    assert c.level == "warning" and c.pp_rejected == ["composite"]
    c = preset("yogurt", "1-4-6-0", {"COD Bloom": {}, "PotatoFX Camera": {}, "ppsettings": {}})
    assert c.pp_rejected == ["composite", "unknown", "version"] and c.unknown_pp == ["PotatoFX Camera"]
    assert c.preset_version == "1.4.6.0"
    # chaîne complète, ou vide (rien à perdre) : pas de rejet
    assert preset("complet", "1-8-0-0", {"COD Bloom": {}, "Composite": {}, "ppsettings": {}}).level == "ok"
    assert preset("vide", "1-4-6-0", {"ppsettings": {}}).pp_rejected == []

def test_nexus_liens():
    import nexus
    i = nexus.parse_nxm("nxm://SkyrimSpecialEdition/mods/165803/files/700123?key=abc&expires=1760000000&user_id=1")
    assert i == {"game": "skyrimspecialedition", "mod_id": 165803, "file_id": 700123, "key": "abc",
                 "expires": "1760000000"}
    for bad in ("https://www.nexusmods.com/x", "nxm://skyrimspecialedition/mods/1"):
        try:
            nexus.parse_nxm(bad); assert False
        except ValueError:
            pass
    assert nexus.search_url("Community Shaders preset") == (
        "https://www.nexusmods.com/games/skyrimspecialedition/mods?keyword=Community%20Shaders%20preset"
        "&sort=endorsements")
    assert nexus.parse_mod_id("https://www.nexusmods.com/skyrimspecialedition/mods/165803?tab=files") == 165803

def test_preset_avec_enb(tmp_path):
    cs = _game(tmp_path)
    root = tmp_path                                     # racine du jeu : Data/SKSE/Plugins/CommunityShaders → 4 niveaux
    (root / "enbseries").mkdir(); (root / "enbseries" / "enbeffect.fx").write_text("ancien")
    (root / "enbseries" / "KiLoaderSatelliteENB.dllplugin").write_text("module")
    (root / "enbseries.ini").write_text("[GLOBAL]\nUseEffect=true\n")
    cfg = {"library": str(tmp_path / "lib"), "cs_dir": str(cs), "backup_dir": str(tmp_path / "bk")}
    pr = tmp_path / "lib" / "Cine"; (pr / "ENB" / "enbseries").mkdir(parents=True)
    (pr / "SettingsUser.json").write_text(json.dumps({"Version": "1-9-0-0", "x": 3}))
    (pr / "ENB" / "enbseries.ini").write_text("[GLOBAL]\nUseEffect=true\n; neuf\n")
    (pr / "ENB" / "enbseries" / "enbeffect.fx").write_text("neuf")
    (pr / "LISEZMOI.md").write_text("notes"); (pr / "Apercus").mkdir(); (pr / "Apercus" / "a.png").write_text("x")
    assert core.read_preset(pr).has_enb
    saved = core.apply_preset(cfg, pr, "Cine")
    assert (root / "enbseries" / "enbeffect.fx").read_text() == "neuf"
    assert "neuf" in (root / "enbseries.ini").read_text()
    assert (root / "enbseries" / "KiLoaderSatelliteENB.dllplugin").read_text() == "module"   # module KiLoader gardé
    assert not (cs / "ENB").exists() and not (cs / "LISEZMOI.md").exists() and not (cs / "Apercus").exists()
    assert (saved / "ENB" / "enbseries" / "enbeffect.fx").read_text() == "ancien"
    assert core.read_preset(saved).has_enb
    second = core.apply_preset(cfg, saved, None)                        # restauration, dans la même seconde
    assert second != saved
    assert (root / "enbseries" / "enbeffect.fx").read_text() == "ancien"
    assert (saved / "ENB" / "enbseries" / "enbeffect.fx").read_text() == "ancien"   # sauvegarde intacte
    assert (second / "ENB" / "enbseries" / "enbeffect.fx").read_text() == "neuf"

def test_frame_generation_forcee(tmp_path):
    """frameGenerationForceEnable fait planter le jeu sous CrossOver (proxy D3D12, E_NOINTERFACE)."""
    ref = {"version": "1.9.0.0", "features": ["upscaling"], "sections": {"Upscaling": ["frameGenerationForceEnable"]},
           "pp": []}
    for force, attendu in ((1, True), (0, False)):
        d = tmp_path / str(force); d.mkdir()
        (d / "SettingsUser.json").write_text(json.dumps({"Version": "1-9-0-0",
                                                         "Upscaling": {"frameGenerationForceEnable": force}}))
        c = core.check_preset(d, ref)
        assert c.frame_gen is attendu and (c.level == "warning") is attendu

def test_preferences_joueur_gardees(tmp_path):
    """Un preset (Cabbage) ne remplace pas les raccourcis du menu CS ni les threads de compilation du joueur."""
    cs = tmp_path / "Data" / "SKSE" / "Plugins" / "CommunityShaders"; cs.mkdir(parents=True)
    (cs / "SettingsUser.json").write_text(json.dumps({"Version": "1-9-0-0", "Menu": {"ToggleKey": 99},
                                                      "Advanced": {"Compiler Threads": 16}, "Vignette": {"x": 0}}))
    cfg = {"library": str(tmp_path / "lib"), "cs_dir": str(cs), "backup_dir": str(tmp_path / "bk")}
    pr = tmp_path / "lib" / "Cabbage"; pr.mkdir(parents=True)
    (pr / "SettingsUser.json").write_text(json.dumps({"Version": "1-8-0-0", "Menu": {"ToggleKey": 35},
                                                      "Advanced": {"Compiler Threads": 18}, "Vignette": {"x": 1}}))
    saved = core.apply_preset(cfg, pr, "Cabbage")
    d = json.loads((cs / "SettingsUser.json").read_text())
    assert d["Menu"] == {"ToggleKey": 99} and d["Advanced"] == {"Compiler Threads": 16} and d["Vignette"] == {"x": 1}
    assert json.loads((pr / "SettingsUser.json").read_text())["Menu"]["ToggleKey"] == 35    # preset intact
    core.apply_preset(cfg, saved, None)                                  # restauration : tout tel quel
    assert json.loads((cs / "SettingsUser.json").read_text())["Vignette"] == {"x": 0}
