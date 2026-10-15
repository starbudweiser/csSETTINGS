import sys, json
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import systems as sy


def put(root, files):
    for rel, txt in files.items():
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt)


def fake_exe(game, version=(1, 6, 1170, 0)):
    ms = (version[0] << 16) | version[1]; ls = (version[2] << 16) | version[3]
    blob = b"MZ" + b"\0" * 64 + b"\xbd\x04\xef\xfe" + b"\x00\x00\x01\x00" + ms.to_bytes(4, "little") + ls.to_bytes(4, "little")
    (game / "SkyrimSE.exe").write_bytes(blob + b"\0" * 64)
    (game / "skse64_loader.exe").write_text("skse")


@pytest.fixture
def world(tmp_path):
    game = tmp_path / "Skyrim"; game.mkdir(); fake_exe(game)
    put(game, {"Data/Skyrim.esm": "vanille", "d3d11.dll": "mon pont"})
    bases = tmp_path / "bases"
    put(bases / "CS", {"d3d11.dll": "pont mDLSS", "Data/SKSE/Plugins/CommunityShaders.dll": "cs",
                       "Data/Shaders/Features/a.ini": "a", "systeme.json": "{}"})
    put(bases / "ENB", {"d3d11.dll": "enb", "enbseries.ini": "[GLOBAL]", "Data/Shaders/Upscaling/u.dll": "u"})
    put(bases / "commun", {"Data/KiLoader/KiLoader.dll": "ki"})
    return game, {n: bases / n for n in ("CS", "ENB", "commun")}, tmp_path / "sauv"


def test_version_et_prerequis(world, tmp_path):
    game, _, _ = world
    assert sy.game_version(game) == "1.6.1170.0" and sy.prerequis(game) == []
    fake_exe(game, (1, 5, 97, 0))
    assert "1.5.97.0" in sy.prerequis(game)[0]
    (game / "skse64_loader.exe").unlink(); fake_exe(game); (game / "skse64_loader.exe").unlink()
    assert "SKSE" in sy.prerequis(game)[0]


def test_plan_sans_ecriture(world):
    game, bases, sauv = world
    p = sy.plan_install(game, "CS", bases["CS"])
    assert p.replace == ["d3d11.dll"] and sorted(p.add) == ["Data/SKSE/Plugins/CommunityShaders.dll", "Data/Shaders/Features/a.ini"]
    assert not (game / sy.MANIFEST).exists() and not sauv.exists()


def test_installer_retirer_remet_loriginal(world):
    game, bases, sauv = world
    sy.install(game, "CS", bases["CS"], sauv)
    assert (game / "d3d11.dll").read_text() == "pont mDLSS" and sy.active_system(game) == "CS"
    assert sy.verify(game, "CS") == {"absents": [], "modifiés": []}
    (game / "Data/Shaders/Features/a.ini").write_text("modifié par le joueur")
    assert sy.verify(game, "CS")["modifiés"] == ["Data/Shaders/Features/a.ini"]
    op = sy.remove(game, "CS", sauv)
    assert (game / "d3d11.dll").read_text() == "mon pont"                       # original remis
    assert not (game / "Data/SKSE").exists() and not (game / "Data/Shaders").exists()   # dossiers vides retirés
    assert (game / "Data/Skyrim.esm").read_text() == "vanille"
    assert (op / "retires/Data/Shaders/Features/a.ini").read_text() == "modifié par le joueur"   # rien de perdu
    assert sy.installed(game) == []


def test_swap_cs_enb_et_retour(world):
    game, bases, sauv = world
    sy.swap(game, None, "CS", bases, sauv)
    assert sy.installed(game) == ["commun", "CS"]
    sy.swap(game, "CS", "ENB", bases, sauv)
    assert sy.installed(game) == ["commun", "ENB"] and (game / "d3d11.dll").read_text() == "enb"
    assert not (game / "Data/SKSE/Plugins/CommunityShaders.dll").exists()
    assert (game / "Data/KiLoader/KiLoader.dll").exists()                         # commun jamais retiré
    sy.swap(game, "ENB", "CS", bases, sauv)
    assert (game / "d3d11.dll").read_text() == "pont mDLSS" and not (game / "enbseries.ini").exists()
    sy.remove(game, "CS", sauv); sy.remove(game, "commun", sauv)
    assert (game / "d3d11.dll").read_text() == "mon pont"                          # retour complet à l'origine


def test_fichier_deja_identique_jamais_retire(world):
    game, bases, sauv = world
    put(game, {"enbseries.ini": "[GLOBAL]"})                                       # déjà là, identique à la base
    sy.install(game, "ENB", bases["ENB"], sauv); sy.remove(game, "ENB", sauv)
    assert (game / "enbseries.ini").read_text() == "[GLOBAL]"


def test_echec_installation_annulee(world, monkeypatch):
    game, bases, sauv = world
    real, n = sy._safe_copy, {"i": 0}
    def flaky(src, dst):
        n["i"] += 1
        if src.name == "a.ini":
            raise OSError("disque plein")
        real(src, dst)
    monkeypatch.setattr(sy, "_safe_copy", flaky)
    with pytest.raises(sy.SystemError_):
        sy.install(game, "CS", bases["CS"], sauv)
    monkeypatch.undo()
    assert (game / "d3d11.dll").read_text() == "mon pont" and sy.installed(game) == []
    assert not (game / "Data/SKSE").exists() and not list(game.rglob("*.csnew"))


def test_swap_echec_remet_le_systeme_precedent(world, monkeypatch):
    game, bases, sauv = world
    sy.swap(game, None, "CS", bases, sauv)
    real = sy._safe_copy
    def flaky(src, dst):
        if src.name == "u.dll":
            raise OSError("boom")
        real(src, dst)
    monkeypatch.setattr(sy, "_safe_copy", flaky)
    with pytest.raises(sy.SystemError_):
        sy.swap(game, "CS", "ENB", bases, sauv)
    assert sy.active_system(game) == "CS" and (game / "d3d11.dll").read_text() == "pont mDLSS"


def test_refus(world):
    game, bases, sauv = world
    with pytest.raises(sy.SystemError_, match="lancé"):
        sy.install(game, "CS", bases["CS"], sauv, is_running=lambda: True)
    fake_exe(game, (1, 5, 97, 0))
    with pytest.raises(sy.SystemError_, match="1.5.97"):
        sy.install(game, "CS", bases["CS"], sauv)
    fake_exe(game)
    sy.install(game, "CS", bases["CS"], sauv)
    with pytest.raises(sy.SystemError_, match="échange"):
        sy.install(game, "ENB", bases["ENB"], sauv)


def test_assemble_filtres_et_atomique(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    put(a, {"Data/x.dll": "A", "Data/SKSE/Plugins/SettingsUser.json": "perso", "Data/SKSE/Plugins/Tweaks.ini": "t"})
    put(b, {"x.dll": "B"})
    dest = tmp_path / "CS"
    n = sy.assemble(dest, [sy.Source(a, exclude=("*SettingsUser.json",)), sy.Source(b, prefix="Data/")], "CS")
    assert n == 2 and (dest / "Data/x.dll").read_text() == "B" and not (dest / "Data/SKSE/Plugins/SettingsUser.json").exists()
    assert json.loads((dest / sy.INFO).read_text())["fichiers"] == 2
    with pytest.raises(sy.SystemError_):
        sy.assemble(dest, [sy.Source(a)], "CS")                                    # jamais d'écrasement
    with pytest.raises(sy.SystemError_):
        sy.assemble(tmp_path / "X", [sy.Source(tmp_path / "absent")], "X")
    assert not (tmp_path / "X").exists() and not (tmp_path / "X.en_construction").exists()


def test_plan_swap_adopt_et_historique(world):
    game, bases, sauv = world
    put(game, {"Data/Shaders/Features/a.ini": "a", "Data/SKSE/Plugins/CommunityShaders.dll": "cs", "d3d11.dll": "pont mDLSS"})
    assert sy.adoptable(game, bases["CS"]) and not sy.adoptable(game, bases["ENB"])
    sy.install(game, "CS", bases["CS"], sauv, adopt=True)                         # reprend l'installation faite à la main
    assert all(not m["pre"] for m in sy.read_manifest(game)["layers"]["CS"]["files"].values())
    (game / "Data/Shaders/Features/a.ini").write_text("réglé par le joueur")
    pl = sy.plan_swap(game, "CS", "ENB", bases["ENB"])
    assert pl["retire"] == 3 and pl["mis_de_côté"] == ["Data/Shaders/Features/a.ini"] and pl["ajoute"] == 3
    sy.swap(game, "CS", "ENB", bases, sauv)                                       # le CS adopté est bien retiré
    assert not (game / "Data/SKSE/Plugins/CommunityShaders.dll").exists() and (game / "d3d11.dll").read_text() == "enb"
    ops = sy.list_operations(sauv)
    assert {(o["type"], o["layer"], o["status"]) for o in ops} >= {("remove", "CS", "terminé"), ("install", "ENB", "terminé")}


def test_adopt_ne_copie_rien(world):
    game, bases, sauv = world
    put(game, {"Data/Shaders/Features/a.ini": "a"})                          # le reste de la base manque dans le jeu
    before = {p.relative_to(game).as_posix(): p.read_bytes() for p in game.rglob("*") if p.is_file()}
    sy.install(game, "CS", bases["CS"], sauv, adopt=True)
    after = {p.relative_to(game).as_posix(): p.read_bytes() for p in game.rglob("*") if p.is_file()}
    assert {k: v for k, v in after.items() if k != sy.MANIFEST} == before
    assert list(sy.read_manifest(game)["layers"]["CS"]["files"]) == ["Data/Shaders/Features/a.ini"]


def test_drop_files_et_helpers_exclus(world, tmp_path):
    game, bases, sauv = world
    put(game, {"Data/SKSE/plugins/ENBHelperPlus.dll": "h"})
    put(bases["ENB"], {"Data/SKSE/plugins/ENBHelperPlus.dll": "h"})
    sy.install(game, "ENB", bases["ENB"], sauv, adopt=True)
    op = sy.drop_files(game, "ENB", ["Data/SKSE/plugins/ENBHelperPlus.dll"], sauv)
    assert not (game / "Data/SKSE/plugins/ENBHelperPlus.dll").exists()
    assert (op / "retires/Data/SKSE/plugins/ENBHelperPlus.dll").read_text() == "h"          # copie gardée
    assert "Data/SKSE/plugins/ENBHelperPlus.dll" not in sy.read_manifest(game)["layers"]["ENB"]["files"]
    assert sy.verify(game, "ENB") == {"absents": [], "modifiés": []}
    src = tmp_path / "pkg"; put(src, {"Data/SKSE/plugins/ENBHelperSE.dll": "x", "Data/SKSE/plugins/Autre.dll": "y"})
    dest = tmp_path / "base"
    sy.assemble(dest, [sy.Source(src, exclude=sy.ENB_HELPERS)], "ENB")
    assert (dest / "Data/SKSE/plugins/Autre.dll").exists() and not (dest / "Data/SKSE/plugins/ENBHelperSE.dll").exists()


def test_assemble_correctifs(tmp_path):
    src = tmp_path / "pkg"; put(src, {"Data/x.ini": "[A]\nFrameGeneration=1\n"})
    dest = tmp_path / "base"
    sy.assemble(dest, [sy.Source(src, patches=(("Data/x.ini", "FrameGeneration=1", "FrameGeneration=0"),))], "ENB")
    assert (dest / "Data/x.ini").read_text() == "[A]\nFrameGeneration=0\n" and "=1" in (src / "Data/x.ini").read_text()
    with pytest.raises(sy.SystemError_, match="Correctif"):
        sy.assemble(tmp_path / "b2", [sy.Source(src, patches=(("Data/x.ini", "absent", "x"),))], "ENB")
    assert not (tmp_path / "b2").exists() and not (tmp_path / "b2.en_construction").exists()
