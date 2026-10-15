"""Systèmes de shaders : Community Shaders (CS) ou ENB, installés par couches réversibles sur un Skyrim SE 1.6.1170.

Une couche est un dossier qui reproduit la racine du jeu (là où se trouve SkyrimSE.exe) :
  commun/  pièces communes à tout rendu (KiLoader, Address Library, SSE Display Tweaks)
  CS/      Community Shaders (Bottled Shaders) et son pont DLSS/MetalFX (d3d11.dll)
  ENB/     ENBSeries et son d3d11.dll
Le d3d11.dll appartient au système (pont mDLSS d'un côté, ENBSeries de l'autre) : jamais à la couche commune.

Sûreté : le jeu garde un manifeste (empreinte de chaque fichier posé). Installer sauvegarde chaque fichier remplacé ;
retirer ne supprime que ce qui est resté identique à la base, déplace dans la sauvegarde ce que le joueur ou le jeu a
modifié, puis remet les fichiers d'origine. Une installation qui échoue est annulée. Rien n'est effacé sans copie.
Sans Qt, sans lien avec core.py.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

GAME_VERSION = "1.6.1170.0"
MANIFEST = ".csSETTINGS_systemes.json"
JOURNAL = "operation.json"
INFO = "systeme.json"
SKIP_NAMES = {".DS_Store", INFO}
FULL_HASH_MAX = 64 << 20      # au-delà : début et fin du fichier seulement (ShaderCache, BSA)
COMMUN, CS, ENB = "commun", "CS", "ENB"


class SystemError_(RuntimeError):
    """Refus ou échec expliqué à l'utilisateur ; l'état du jeu est resté sain ou a été remis."""


# ------------------------------------------------------------------ jeu

def game_version(game_dir: Path) -> str:
    """Version de SkyrimSE.exe (ressource VS_FIXEDFILEINFO), « » si illisible."""
    exe = Path(game_dir) / "SkyrimSE.exe"
    try:
        data = exe.read_bytes()
    except OSError:
        return ""
    i = data.find(b"\xbd\x04\xef\xfe")
    while i != -1:
        if data[i + 4:i + 8] == b"\x00\x00\x01\x00":          # structure version 1.0
            ms, ls = int.from_bytes(data[i + 8:i + 12], "little"), int.from_bytes(data[i + 12:i + 16], "little")
            return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        i = data.find(b"\xbd\x04\xef\xfe", i + 1)
    return ""


def prerequis(game_dir: Path) -> list[str]:
    """Ce qui manque pour accueillir un système (vide = prêt). SKSE n'est pas fourni : il doit être déjà installé."""
    game = Path(game_dir)
    out = []
    if not (game / "SkyrimSE.exe").is_file():
        return ["SkyrimSE.exe introuvable"]
    v = game_version(game)
    if v != GAME_VERSION:
        out.append(f"Skyrim {v or 'de version inconnue'} : seule la {GAME_VERSION[:-2]} est prise en charge")
    if not (game / "skse64_loader.exe").is_file():
        out.append("SKSE (skse64_loader.exe) n'est pas installé")
    return out


def fingerprint(path: Path) -> str:
    size = path.stat().st_size
    h = hashlib.sha256()
    with path.open("rb") as f:
        if size <= FULL_HASH_MAX:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        else:
            h.update(f.read(1 << 20))
            f.seek(size - (1 << 20))
            h.update(f.read(1 << 20))
    return f"{size}:{h.hexdigest()[:32]}"


def files_of(root: Path) -> dict[str, Path]:
    """Chemin relatif (avec /) → fichier, pour tout ce que contient une couche."""
    root = Path(root)
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*"))
            if p.is_file() and p.name not in SKIP_NAMES}


# ------------------------------------------------------------------ manifeste

def read_manifest(game_dir: Path) -> dict:
    try:
        data = json.loads((Path(game_dir) / MANIFEST).read_text(encoding="utf-8"))
        if isinstance(data.get("layers"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"layers": {}}


def _write_manifest(game_dir: Path, data: dict) -> None:
    target = Path(game_dir) / MANIFEST
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, target)


def installed(game_dir: Path) -> list[str]:
    return list(read_manifest(game_dir)["layers"])


def active_system(game_dir: Path) -> str | None:
    """CS ou ENB si l'un des deux est posé, sinon None."""
    return next((n for n in installed(game_dir) if n in (CS, ENB)), None)


# ------------------------------------------------------------------ copie sûre

def _safe_copy(src: Path, dst: Path) -> None:
    """Copie vérifiée : écrite sous un nom provisoire, contrôlée, puis posée d'un coup."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".csnew")
    shutil.copy2(src, tmp)
    if fingerprint(tmp) != fingerprint(src):
        tmp.unlink(missing_ok=True)
        raise SystemError_(f"Copie corrompue : {src.name}")
    os.replace(tmp, dst)


def _stash(game_file: Path, op_dir: Path, folder: str, rel: str) -> None:
    """Met un fichier du jeu à l'abri dans la sauvegarde (copie vérifiée), sans le supprimer."""
    _safe_copy(game_file, op_dir / folder / rel)


def _prune(game_dir: Path, rels: list[str]) -> None:
    """Retire les dossiers devenus vides après un retrait (jamais la racine du jeu ni Data)."""
    keep = {Path(game_dir), Path(game_dir) / "Data"}
    dirs = {(Path(game_dir) / r).parent for r in rels}
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        while d not in keep and d != d.parent and d.is_dir() and not any(d.iterdir()):
            d.rmdir()
            d = d.parent


# ------------------------------------------------------------------ plan

@dataclass
class Plan:
    layer: str
    add: list[str] = field(default_factory=list)          # absents du jeu
    replace: list[str] = field(default_factory=list)      # présents et différents : sauvegardés puis remplacés
    same: list[str] = field(default_factory=list)         # déjà identiques : laissés, jamais retirés ensuite
    conflicts: dict[str, str] = field(default_factory=dict)   # fichier → couche qui le possède déjà


def plan_install(game_dir: Path, layer: str, src: Path) -> Plan:
    game = Path(game_dir)
    manifest = read_manifest(game)
    owners = {rel: n for n, d in manifest["layers"].items() for rel in d["files"]}
    p = Plan(layer)
    for rel, s in files_of(src).items():
        if rel in owners and owners[rel] != layer:
            p.conflicts[rel] = owners[rel]
            continue
        d = game / rel
        if not d.is_file():
            p.add.append(rel)
        elif fingerprint(d) == fingerprint(s):
            p.same.append(rel)
        else:
            p.replace.append(rel)
    return p


def _new_op(backup_root: Path, kind: str, layer: str, extra: dict) -> Path:
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    op = Path(backup_root) / f"{stamp}_{kind}_{layer}"
    n = 2
    while op.exists():
        op = Path(backup_root) / f"{stamp}_{n}_{kind}_{layer}"
        n += 1
    op.mkdir(parents=True)
    _journal(op, {"type": kind, "layer": layer, "status": "en cours", **extra})
    return op


def _journal(op: Path, data: dict) -> None:
    path = op / JOURNAL
    try:
        data = {**json.loads(path.read_text(encoding="utf-8")), **data}
    except (OSError, ValueError):
        pass
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def _check_ready(game: Path, is_running: Callable[[], bool] | None, check_version: bool) -> None:
    if not game.is_dir():
        raise SystemError_(f"Dossier du jeu introuvable : {game}")
    if is_running and is_running():
        raise SystemError_("Le jeu est lancé : fermez-le avant de changer de système.")
    if check_version:
        problems = prerequis(game)
        if problems:
            raise SystemError_(" ; ".join(problems))


# ------------------------------------------------------------------ installer / retirer

def install(game_dir: Path, layer: str, src: Path, backup_root: Path, *, is_running=None,
            check_version: bool = True) -> Path:
    """Pose une couche. Renvoie le dossier de sauvegarde de l'opération. En cas d'échec, tout est remis."""
    game, src = Path(game_dir), Path(src)
    _check_ready(game, is_running, check_version)
    if not src.is_dir():
        raise SystemError_(f"Base introuvable : {src}")
    manifest = read_manifest(game)
    if layer in manifest["layers"]:
        raise SystemError_(f"« {layer} » est déjà installé : retirez-le d'abord.")
    if layer in (CS, ENB):
        other = active_system(game)
        if other:
            raise SystemError_(f"« {other} » est installé : utilisez l'échange de système.")
    plan = plan_install(game, layer, src)
    if plan.conflicts:
        n = next(iter(plan.conflicts.items()))
        raise SystemError_(f"{len(plan.conflicts)} fichier(s) appartiennent déjà à une autre couche (ex. {n[0]}).")
    op = _new_op(Path(backup_root), "install", layer, {"manifest_avant": manifest, "posés": [], "remplacés": []})
    files, replaced, laid = {}, [], []
    try:
        for rel, s in files_of(src).items():
            d = game / rel
            fp = fingerprint(s)
            if rel in plan.same:
                files[rel] = {"fp": fp, "pre": True}
                continue
            if rel in plan.replace:
                _stash(d, op, "remplaces", rel)
                replaced.append(rel)
            _safe_copy(s, d)
            laid.append(rel)
            files[rel] = {"fp": fp, "pre": False}
        manifest["layers"][layer] = {"files": files, "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                                     "operation": op.name, "remplacés": replaced}
        _write_manifest(game, manifest)
        _journal(op, {"status": "terminé", "posés": laid, "remplacés": replaced})
    except Exception as e:
        _undo_install(game, op, laid, replaced)
        _journal(op, {"status": "annulé", "erreur": str(e)})
        if isinstance(e, SystemError_):
            raise
        raise SystemError_(f"Installation de {layer} annulée, jeu remis en l'état : {e}") from e
    return op


def _undo_install(game: Path, op: Path, laid: list[str], replaced: list[str]) -> None:
    for rel in laid:
        (game / rel).unlink(missing_ok=True)
        (game / rel).with_name((game / rel).name + ".csnew").unlink(missing_ok=True)
    for rel in replaced:
        saved = op / "remplaces" / rel
        if saved.is_file():
            _safe_copy(saved, game / rel)
    _prune(game, laid)
    before = json.loads((op / JOURNAL).read_text(encoding="utf-8")).get("manifest_avant")
    if before is not None:
        _write_manifest(game, before)


def remove(game_dir: Path, layer: str, backup_root: Path, *, is_running=None) -> Path:
    """Retire une couche. Fichiers identiques à la base : supprimés. Modifiés depuis : mis dans la sauvegarde
    (« retires/ »). Fichiers d'origine remplacés à l'installation : remis en place."""
    game = Path(game_dir)
    _check_ready(game, is_running, check_version=False)
    manifest = read_manifest(game)
    entry = manifest["layers"].get(layer)
    if entry is None:
        raise SystemError_(f"« {layer} » n'est pas installé.")
    op = _new_op(Path(backup_root), "remove", layer, {"manifest_avant": manifest})
    removed, kept, missing = [], [], []
    install_op = Path(backup_root) / entry.get("operation", "")
    for rel, meta in entry["files"].items():
        d = game / rel
        if meta.get("pre"):
            continue
        if not d.is_file():
            missing.append(rel)
            continue
        if fingerprint(d) != meta["fp"]:
            _stash(d, op, "retires", rel)                     # copie vérifiée d'abord, suppression ensuite
            kept.append(rel)
        d.unlink()
        removed.append(rel)
    restored = []
    for rel in entry.get("remplacés", []):
        saved = install_op / "remplaces" / rel
        if saved.is_file():
            _safe_copy(saved, game / rel)
            restored.append(rel)
        else:
            missing.append(f"original de {rel}")
    _prune(game, removed)
    del manifest["layers"][layer]
    _write_manifest(game, manifest)
    _journal(op, {"status": "terminé", "supprimés": removed, "mis_de_côté": kept, "originaux_remis": restored,
                  "absents": missing})
    return op


def swap(game_dir: Path, current: str | None, target: str, bases: dict[str, Path], backup_root: Path, *,
         is_running=None, with_commun: bool = True) -> list[Path]:
    """Passe de `current` à `target` (CS ↔ ENB). La couche commune est posée si elle manque, jamais retirée.
    Si l'installation de `target` échoue, `current` est réinstallé depuis sa base."""
    game = Path(game_dir)
    _check_ready(game, is_running, True)
    if target not in bases or not Path(bases[target]).is_dir():
        raise SystemError_(f"Base « {target} » introuvable.")
    ops: list[Path] = []
    if with_commun and COMMUN in bases and COMMUN not in installed(game):
        ops.append(install(game, COMMUN, bases[COMMUN], backup_root, is_running=is_running))
    if current and current in installed(game):
        ops.append(remove(game, current, backup_root, is_running=is_running))
    try:
        ops.append(install(game, target, bases[target], backup_root, is_running=is_running))
    except SystemError_ as e:
        if current and current in bases:
            try:
                install(game, current, bases[current], backup_root, is_running=is_running)
            except SystemError_ as e2:
                raise SystemError_(f"{e} — et {current} n'a pas pu être remis : {e2}. "
                                   f"Sauvegardes : {backup_root}") from e
        raise
    return ops


def verify(game_dir: Path, layer: str) -> dict[str, list[str]]:
    """État d'une couche installée : fichiers absents, modifiés depuis la pose."""
    game = Path(game_dir)
    entry = read_manifest(game)["layers"].get(layer)
    if entry is None:
        raise SystemError_(f"« {layer} » n'est pas installé.")
    out = {"absents": [], "modifiés": []}
    for rel, meta in entry["files"].items():
        d = game / rel
        if not d.is_file():
            out["absents"].append(rel)
        elif fingerprint(d) != meta["fp"]:
            out["modifiés"].append(rel)
    return out


# ------------------------------------------------------------------ bases neutres

@dataclass
class Source:
    path: Path
    prefix: str = ""                      # ajouté devant chaque chemin (ex. « Data/ »)
    include: tuple[str, ...] = ()         # motifs fnmatch sur le chemin final ; vide = tout
    exclude: tuple[str, ...] = ()


def assemble(dest: Path, sources: list[Source], name: str, notes: str = "") -> int:
    """Construit une base neutre à partir de paquets (les suivants l'emportent). dest ne doit pas exister :
    la base est montée à côté puis renommée, pour ne jamais laisser une base à moitié faite."""
    dest = Path(dest)
    if dest.exists():
        raise SystemError_(f"{dest.name} existe déjà : supprimez-le pour reconstruire la base.")
    tmp = dest.with_name(dest.name + ".en_construction")
    if tmp.exists():
        shutil.rmtree(tmp)
    count = 0
    try:
        for s in sources:
            if not Path(s.path).is_dir():
                raise SystemError_(f"Paquet introuvable : {s.path}")
            for rel, f in files_of(s.path).items():
                final = (s.prefix + rel)
                if s.include and not any(fnmatch.fnmatch(final, m) for m in s.include):
                    continue
                if any(fnmatch.fnmatch(final, m) for m in s.exclude):
                    continue
                out = tmp / final
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, out)
                count += 1
        count = len(files_of(tmp))                  # fichiers distincts (un paquet suivant peut en écraser un autre)
        (tmp / INFO).write_text(json.dumps({
            "nom": name, "date": time.strftime("%Y-%m-%d %H:%M:%S"), "fichiers": count, "notes": notes,
            "sources": [str(s.path) for s in sources]}, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return count


# Réglages du joueur : jamais dans une base (une base est neutre, les presets les posent ensuite)
USER_SETTINGS = ("Data/SKSE/Plugins/CommunityShaders/SettingsUser.json", "Data/SKSE/Plugins/CommunityShaders/SettingsTest.json",
                 "Data/SKSE/Plugins/CommunityShaders/PostProcessing/*", "Data/Shaders/ShaderCache/*", "*.log", "*.pdb")
SHARED = ("Data/SKSE/Plugins/SSEDisplayTweaks.*", "Data/SKSE/Plugins/versionlib-*")
# Plugins ENB de KiLoader (ENB Helper, ENB Extender) : la variante Legacy 1.6.0 est la seule compatible 1.6.1170 et
# elle accompagne les presets ENB / Effects 11, pas le socle ; les poser ici risquerait d'écraser la bonne version.
KILOADER_ENB = ("Data/KiLoader/Plugins/ENB*", "Data/KiLoader/Plugins/KiENBExtender*")


def recettes(shaders_root: Path) -> dict[str, list[Source]]:
    """Recettes des trois couches à partir de la collection _SHADERS (vérifiées à l'assemblage)."""
    r = Path(shaders_root)
    mdlss = r / "mDLSS - DLSS METALFX" / "1 - DLSS METALFX (OBLIGATOIRE)"
    bottled = r / "COMMUNITY SHADERS AIO" / "BOTTLED SHADERS" / "BOTTLED SHADERS 1.0.13"
    return {
        COMMUN: [Source(r / "KILOADER", prefix="Data/", exclude=KILOADER_ENB), Source(mdlss, include=SHARED)],
        CS: [Source(mdlss, exclude=SHARED + USER_SETTINGS), Source(bottled, prefix="Data/", exclude=USER_SETTINGS)],
        ENB: [Source(r / "ENBSERIES" / "ENBSERIES 0.505 + DLSS", exclude=USER_SETTINGS)],
    }


def bases_dir(library: str | Path) -> Path:
    """Dossier des bases : _SYSTEMES, à côté des bibliothèques de presets."""
    return Path(library).parent / "_SYSTEMES"


def backup_root(backup_dir: str | Path) -> Path:
    return Path(backup_dir).parent / "Systemes_sauvegardes"


def available_bases(library: str | Path) -> dict[str, Path]:
    root = bases_dir(library)
    return {n: root / n for n in (COMMUN, CS, ENB) if (root / n / INFO).is_file()}
