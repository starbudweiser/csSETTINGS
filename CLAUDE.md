# cSPRESETS

Sélecteur de presets Community Shaders (Bottled Shaders) pour la bouteille CrossOver Skyrim-MetalFX :
bibliothèque de presets, application avec sauvegarde automatique, restauration, import d'archives/dossiers,
téléchargement Nexus Mods (clé d'API dans le trousseau macOS, compte Premium).

- Interface : suivre le design system Socle (https://claude.ai/artifact/TkNj2Y6SQGZwT6EyME92Ah).
  `src/socle_qt.py` est régénéré par `/Volumes/SKYRIM/TOOLS/DESIGN/Socle/sync_apps.sh` : ne pas l'éditer.
- Code : `src/core.py` (logique, sans Qt), `src/nexus.py` (API Nexus), `src/cSPRESETS.py` (interface PyQt6),
  `src/i18n.py` + `src/i18n_strings.py` (fr source, en/it/es).
- Build : `./build_app.sh` (ou `_tools/build_all.sh cSPRESETS`), identifiant `local.stephan.cspresets`.
- Tests : `tests/` (pytest).
