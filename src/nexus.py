"""Accès à l'API Nexus Mods (v1) : clé personnelle dans le trousseau macOS, liste des fichiers, téléchargement.

Le téléchargement direct par l'API est réservé aux comptes Premium. Module sans dépendance Qt.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.nexusmods.com/v1"
GAME = "skyrimspecialedition"
APP_NAME = "csSETTINGS"
APP_VERSION = "1.0.0"
KEYCHAIN_SERVICE = "cSPRESETS Nexus API"  # nom d'origine conservé : la clé déjà rangée reste lisible
KEYCHAIN_ACCOUNT = "apikey"


class NexusError(Exception):
    pass


# ------------------------------------------------------------------ clé (trousseau macOS)

def get_key() -> str:
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def set_key(key: str) -> None:
    # -U met à jour l'entrée existante
    r = subprocess.run(["security", "add-generic-password", "-U", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT,
                        "-w", key], capture_output=True, text=True)
    if r.returncode != 0:
        raise NexusError(r.stderr.strip())


def delete_key() -> None:
    subprocess.run(["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT],
                   capture_output=True)


# ------------------------------------------------------------------ requêtes

def _get(path: str, key: str):
    req = urllib.request.Request(API + path, headers={
        "apikey": key, "Accept": "application/json",
        "Application-Name": APP_NAME, "Application-Version": APP_VERSION,
        "User-Agent": f"{APP_NAME}/{APP_VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("message", "")
        except (ValueError, OSError):
            msg = ""
        raise NexusError(f"HTTP {e.code} {msg}".strip()) from e
    except urllib.error.URLError as e:
        raise NexusError(str(e.reason)) from e


def validate(key: str) -> dict:
    """{'name':…, 'is_premium':…} pour la clé donnée."""
    return _get("/users/validate.json", key)


def parse_mod_id(text: str) -> int:
    """Accepte un numéro ou une adresse nexusmods.com/skyrimspecialedition/mods/<id>."""
    text = text.strip()
    m = re.search(r"/mods/(\d+)", text) or re.fullmatch(r"(\d+)", text)
    if not m:
        raise ValueError(text)
    return int(m.group(1))


def mod_info(mod_id: int, key: str) -> dict:
    return _get(f"/games/{GAME}/mods/{mod_id}.json", key)


def mod_files(mod_id: int, key: str) -> list[dict]:
    files = _get(f"/games/{GAME}/mods/{mod_id}/files.json", key).get("files", [])
    order = {"MAIN": 0, "OPTIONAL": 1, "UPDATE": 2, "MISCELLANEOUS": 3, "OLD_VERSION": 4}
    files = [f for f in files if f.get("category_name") not in ("ARCHIVED", "DELETED", None)]
    return sorted(files, key=lambda f: (order.get(f.get("category_name"), 9), -(f.get("uploaded_timestamp") or 0)))


def download(mod_id: int, file: dict, key: str, dest_dir: Path, progress=None) -> Path:
    """Télécharge le fichier dans dest_dir et renvoie son chemin. progress(reçus, total) est appelé en cours."""
    links = _get(f"/games/{GAME}/mods/{mod_id}/files/{file['file_id']}/download_link.json", key)
    if not links:
        raise NexusError("no link")
    url = links[0]["URI"]
    name = file.get("file_name") or Path(urllib.parse.urlparse(url).path).name
    out = Path(dest_dir) / name
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=60) as r, open(out, "wb") as fh:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
            got += len(chunk)
            if progress:
                progress(got, total)
    return out
