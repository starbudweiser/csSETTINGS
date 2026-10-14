"""Bibliothèque de presets Community Shaders : lister, appliquer, sauvegarder, restaurer, importer.

Module sans dépendance Qt. Un preset est un dossier de la bibliothèque qui reproduit le contenu de
Data/SKSE/Plugins/CommunityShaders : SettingsUser.json et/ou des fichiers PostProcessing, plus les
dossiers de l'éditeur CS (Weathers, ImageSpaces…). Un fichier preset.json facultatif décrit sa source.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = Path.home() / "Library" / "Application Support" / "csPRESETS" / "config.json"
DEFAULTS = {
    "library": "/Volumes/SKYRIM/MODS COLLECTION/_SHADERS/CS PRESETS",
    "cs_dir": "/Volumes/SAMSUNG T7/VIRTUAL MACHINES/Crossover/Skyrim-MetalFX/drive_c/Games/"
              "Skyrim Special Edition/Data/SKSE/Plugins/CommunityShaders",
    "backup_dir": "/Volumes/SAMSUNG T7/VIRTUAL MACHINES/Crossover/_RETIRES_Skyrim-MetalFX/CS_presets_sauvegardes",
    "lang": "auto",
}
SETTINGS = "SettingsUser.json"
PP = "PostProcessing"
EDITOR = ["Weathers", "ImageSpaces", "SceneSettings", "Volumetric Lighting", "EditorSettings.json"]
META = "preset.json"
STATE = ".preset_actif"
# Caches propres à une machine : jamais copiés depuis une archive
SKIP = {"UnifiedWaterCache", "UWLoadOrder.hash", "ShaderCache", ".DS_Store"}
ARCHIVES = (".zip", ".7z", ".rar")


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


@dataclass
class Preset:
    name: str
    path: Path
    version: str = ""
    has_settings: bool = False
    pp_files: list[str] = field(default_factory=list)
    editor: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _version(settings: Path) -> str:
    try:
        return str(json.loads(settings.read_text(encoding="utf-8")).get("Version", "")).replace("-", ".")
    except (OSError, ValueError):
        return ""


def read_preset(path: Path) -> Preset:
    p = Preset(path.name, path)
    s = path / SETTINGS
    p.has_settings = s.is_file()
    p.version = _version(s) if p.has_settings else ""
    pp = path / PP
    p.pp_files = sorted(f.name for f in pp.glob("*.json")) if pp.is_dir() else []
    p.editor = [e for e in EDITOR if (path / e).exists()]
    try:
        p.meta = json.loads((path / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        p.meta = {}
    return p


def list_presets(library: str) -> list[Preset]:
    lib = Path(library)
    if not lib.is_dir():
        return []
    out = []
    for d in sorted(lib.iterdir(), key=lambda x: x.name.lower()):
        if d.is_dir() and not d.name.startswith(".") and ((d / SETTINGS).is_file() or (d / PP).is_dir()):
            out.append(read_preset(d))
    return out


def active_preset(library: str) -> str:
    try:
        return (Path(library) / STATE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def game_running() -> bool:
    """Vrai si SkyrimSE.exe tourne (dans CrossOver, le processus Wine garde le nom de l'exécutable)."""
    try:
        r = subprocess.run(["pgrep", "-if", "SkyrimSE.exe"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _copy(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKIP))
    else:
        shutil.copy2(src, dst)


def snapshot(cs_dir: str, dest: Path) -> Path:
    """Copie la configuration CS actuelle (réglages, éditeur, post-traitement) dans dest."""
    cs = Path(cs_dir)
    dest.mkdir(parents=True, exist_ok=True)
    for name in [SETTINGS, PP] + EDITOR:
        if (cs / name).exists():
            _copy(cs / name, dest / name)
    return dest


def backup(cfg: dict, reason: str) -> Path:
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    dest = snapshot(cfg["cs_dir"], Path(cfg["backup_dir"]) / stamp)
    (dest / META).write_text(json.dumps({"reason": reason, "date": stamp}, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return dest


def list_backups(cfg: dict) -> list[Preset]:
    root = Path(cfg["backup_dir"])
    if not root.is_dir():
        return []
    return [read_preset(d) for d in sorted(root.iterdir(), reverse=True) if d.is_dir()]


def apply_preset(cfg: dict, preset_path: Path, label: str | None = None) -> Path:
    """Applique un preset. Sauvegarde d'abord la configuration actuelle ; renvoie le dossier de sauvegarde.

    Un preset avec SettingsUser.json remplace les réglages et les données de l'éditeur CS.
    Un preset de post-traitement seul ajoute ses fichiers sans toucher aux réglages.
    """
    cs = Path(cfg["cs_dir"])
    if not cs.is_dir():
        raise FileNotFoundError(str(cs))
    preset_path = Path(preset_path)
    saved = backup(cfg, f"avant {label or preset_path.name}")
    if (preset_path / SETTINGS).is_file():
        for e in EDITOR:
            t = cs / e
            if t.is_dir():
                shutil.rmtree(t)
            elif t.exists():
                t.unlink()
        for item in preset_path.iterdir():
            if item.name in SKIP or item.name.startswith(".") or item.name in (PP, META):
                continue
            t = cs / item.name
            if t.is_dir():
                shutil.rmtree(t)
            _copy(item, t)
    if (preset_path / PP).is_dir():
        (cs / PP).mkdir(exist_ok=True)
        for f in (preset_path / PP).iterdir():
            if f.is_file() and not f.name.startswith("."):
                shutil.copy2(f, cs / PP / f.name)
    if label is not None:
        (Path(cfg["library"]) / STATE).write_text(label, encoding="utf-8")
    return saved


def save_current(cfg: dict, name: str) -> Path:
    dest = Path(cfg["library"]) / safe_name(name)
    if dest.exists():
        raise FileExistsError(str(dest))
    snapshot(cfg["cs_dir"], dest)
    (dest / META).write_text(json.dumps({"source": "config actuelle", "date": time.strftime("%Y-%m-%d %H:%M")},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(cfg["library"]) / STATE).write_text(dest.name, encoding="utf-8")
    return dest


def remove_preset(cfg: dict, preset_path: Path) -> Path:
    """Retire un preset de la bibliothèque en le déplaçant dans le dossier des sauvegardes (rien n'est effacé)."""
    dest = Path(cfg["backup_dir"]) / "_presets_retires" / f"{time.strftime('%Y-%m-%d_%H%M%S')}_{preset_path.name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(preset_path), str(dest))
    return dest


def safe_name(name: str) -> str:
    keep = "".join(ch if ch not in '/\\:*?"<>|' else "-" for ch in name).strip().strip(".")
    return keep or "Preset"


# ------------------------------------------------------------------ compatibilité

REFERENCE_FILE = CONFIG_FILE.parent / "reference.json"
DEFAULTS_FILE = "SettingsDefault.json"
# Sections de SettingsUser.json qui ne sont pas des features (toujours présentes)
CORE_SECTIONS = {"Version", "Advanced", "General", "Menu", "Disable at Boot", "Replace Original Shaders"}


def _squash(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _feature_known(section: str, features: set[str]) -> bool:
    """Une section (« HiZ Occlusion Culling ») correspond à un fichier de feature (« HiZOcclusion.ini »)
    si son nom compacté commence ou finit par celui du fichier (« Advanced Skin » ↔ « Skin.ini »)."""
    s = _squash(section)
    return any(s == f or (len(f) >= 4 and (s.startswith(f) or s.endswith(f))) for f in features)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def build_reference(cs_dir: str) -> dict | None:
    """Ce que connaît le Community Shaders installé : features (Data/Shaders/Features/*.ini), sections et
    options de réglages, effets de post-traitement. None si le dossier du jeu est introuvable.

    Les sections de SettingsUser.json du jeu ne comptent que si une feature installée leur correspond :
    un preset incompatible appliqué juste avant ne fausse donc pas la référence.
    """
    cs = Path(cs_dir)
    default = _read_json(cs / DEFAULTS_FILE)
    if not default:
        return None
    feat_dir = cs.parents[2] / "Shaders" / "Features"     # CommunityShaders → Plugins → SKSE → Data
    features = {p.stem.lower() for p in feat_dir.glob("*.ini")} if feat_dir.is_dir() else set()
    user = _read_json(cs / SETTINGS)
    sections: dict[str, set[str]] = {}
    for src, trusted in ((default, True), (user, False)):
        for k, v in src.items():
            if trusted or k in sections or _feature_known(k, features):
                sections.setdefault(k, set()).update(v.keys() if isinstance(v, dict) else [])
    pp = set(sections.get("Post Processing", set())) | {"ppsettings", "preset_name"}
    return {"version": str(default.get("Version", "")).replace("-", "."), "features": sorted(features),
            "sections": {k: sorted(v) for k, v in sections.items()}, "pp": sorted(pp)}


def game_reference(cs_dir: str, cache: Path | None = None) -> dict | None:
    """Référence du jeu, mise en cache par version de CS : elle est relevée une fois, quand la configuration
    du jeu est saine, puis réutilisée tant que la version de SettingsDefault.json ne change pas."""
    cache = cache or REFERENCE_FILE
    fresh = build_reference(cs_dir)
    if fresh is None:
        return None
    old = _read_json(cache)
    if old.get("version") == fresh["version"] and old.get("cs_dir") == cs_dir:
        # n'ajoute que des features réellement installées depuis (mise à jour partielle de CS)
        old["features"] = sorted(set(old.get("features", [])) | set(fresh["features"]))
        return old
    fresh["cs_dir"] = cs_dir
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(fresh, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return fresh


@dataclass
class Compat:
    level: str                       # ok | info | warning
    unknown_features: list[str] = field(default_factory=list)   # ignorées par le CS installé
    missing_features: list[str] = field(default_factory=list)   # absentes du preset : valeurs par défaut
    unknown_options: int = 0                                     # options inconnues dans des features connues
    unknown_pp: list[str] = field(default_factory=list)          # effets de post-traitement inconnus


def check_preset(preset_path: Path, ref: dict) -> Compat:
    """Compare un preset au Community Shaders installé (voir game_reference)."""
    preset_path = Path(preset_path)
    sections = {k: set(v) for k, v in ref.get("sections", {}).items()}
    features = set(ref.get("features", []))
    pp_known = set(ref.get("pp", []))
    c = Compat("ok")
    settings = _read_json(preset_path / SETTINGS)
    if settings:
        for k, v in settings.items():
            if k in sections:
                if isinstance(v, dict) and k not in ("Disable at Boot", "Post Processing"):
                    c.unknown_options += len(set(v) - sections[k])
            elif k not in CORE_SECTIONS and not _feature_known(k, features):
                c.unknown_features.append(k)
        boot = settings.get("Disable at Boot")
        if isinstance(boot, dict):
            known = features | {_squash(s) for s in sections}
            c.unknown_features += [k for k in boot if _squash(k) not in known
                                   and not any(_squash(k) == _squash(u) for u in c.unknown_features)]
        c.missing_features = [k for k in sections if k not in settings and k not in CORE_SECTIONS
                              and _feature_known(k, features)]
        pp = settings.get("Post Processing")
        if isinstance(pp, dict):
            c.unknown_pp += [k for k in pp if k not in pp_known]
    pp_dir = preset_path / PP
    if pp_dir.is_dir():
        for f in sorted(pp_dir.glob("*.json")):
            c.unknown_pp += [k for k in _read_json(f) if k not in pp_known and k not in c.unknown_pp]
    if c.unknown_features or c.unknown_pp:
        c.level = "warning"
    elif c.missing_features or c.unknown_options:
        c.level = "info"
    return c


# ------------------------------------------------------------------ import

def extract(archive: Path, dest: Path) -> None:
    """Décompresse .ZIP, .7Z ou .RAR avec bsdtar (libarchive, fourni avec macOS)."""
    r = subprocess.run(["/usr/bin/bsdtar", "-xf", str(archive), "-C", str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "bsdtar")


def find_roots(tree: Path) -> list[Path]:
    """Dossiers qui ressemblent à un dossier CommunityShaders : SettingsUser.json ou PostProcessing/*.json."""
    roots = []
    for dirpath, dirs, files in os.walk(tree):
        d = Path(dirpath)
        if SETTINGS in files or (d.name == PP and any(f.endswith(".json") for f in files)):
            root = d if SETTINGS in files else d.parent
            if root not in roots and not any(root.is_relative_to(r) for r in roots):
                roots.append(root)
        dirs[:] = [x for x in dirs if x not in SKIP]
    return roots


def import_source(cfg: dict, source: Path, name: str, meta: dict | None = None) -> list[Path]:
    """Ajoute un ou plusieurs presets depuis une archive ou un dossier. Renvoie les dossiers créés."""
    source = Path(source)
    with tempfile.TemporaryDirectory(prefix="cspresets_") as tmp:
        tree = Path(tmp) / "x"
        tree.mkdir()
        if source.is_file() and source.suffix.lower() in ARCHIVES:
            extract(source, tree)
        elif source.is_dir():
            shutil.copytree(source, tree / source.name, ignore=shutil.ignore_patterns(*SKIP))
        else:
            raise ValueError(str(source))
        roots = find_roots(tree)
        if not roots:
            raise LookupError(str(source))
        made = []
        for i, root in enumerate(roots):
            sub = "" if len(roots) == 1 else f" - {root.name if root.name not in (PP, 'CommunityShaders') else i + 1}"
            dest = Path(cfg["library"]) / safe_name(name + sub)
            n = 2
            while dest.exists():
                dest = Path(cfg["library"]) / safe_name(f"{name}{sub} ({n})")
                n += 1
            dest.mkdir(parents=True)
            for item in root.iterdir():
                if item.name in SKIP or item.name.startswith("."):
                    continue
                if item.name in [SETTINGS, PP, "EditorSettings.json"] + EDITOR:
                    _copy(item, dest / item.name)
            info = dict(meta or {})
            info.setdefault("source", str(source))
            info.setdefault("date", time.strftime("%Y-%m-%d %H:%M"))
            (dest / META).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
            made.append(dest)
        return made
