#!/bin/bash
# Construit csSETTINGS.app à la racine du projet, signé avec le certificat stable, sans fichiers temporaires.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/src/csSETTINGS.py"
APP_NAME="csSETTINGS"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/cssettings_build.XXXXXX")"

cleanup() { rm -rf "$TMP" "$ROOT/build" "$ROOT/$APP_NAME.spec" "$ROOT/src/__pycache__"; }
trap cleanup EXIT

command -v pyinstaller >/dev/null 2>&1 || { echo "Erreur : pyinstaller absent (pip install pyinstaller)." >&2; exit 1; }
[ -f "$ROOT/assets/icon.icns" ] || python3 "$ROOT/assets/make_icon.py"

rm -rf "$ROOT/$APP_NAME.app"
pyinstaller --noconfirm --clean --windowed --name "$APP_NAME" \
  --icon "$ROOT/assets/icon.icns" \
  --osx-bundle-identifier "local.stephan.cspresets" \
  --paths "$ROOT/src" \
  --distpath "$TMP/dist" --workpath "$TMP/work" --specpath "$TMP/spec" \
  "$SRC"

[ -d "$TMP/dist/$APP_NAME.app" ] || { echo "Erreur : app non générée." >&2; exit 1; }
mv "$TMP/dist/$APP_NAME.app" "$ROOT/$APP_NAME.app"
"$(cd "$ROOT/.." && pwd)/_tools/sign_app.sh" "$ROOT/$APP_NAME.app"  # signature stable (_tools)
echo "OK : $ROOT/$APP_NAME.app"
