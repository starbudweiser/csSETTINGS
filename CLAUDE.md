# csSETTINGS

Sélecteur de presets Community Shaders (Bottled Shaders) pour la bouteille CrossOver Skyrim-MetalFX :
bibliothèque de presets, application avec sauvegarde automatique, restauration, import d'archives/dossiers,
téléchargement Nexus Mods (clé d'API dans le trousseau macOS, compte Premium).

- Interface : suivre le design system Socle (https://claude.ai/artifact/TkNj2Y6SQGZwT6EyME92Ah).
  `src/socle_qt.py` est régénéré par `/Volumes/SKYRIM/TOOLS/DESIGN/Socle/sync_apps.sh` : ne pas l'éditer.
- Code : `src/core.py` (logique, sans Qt), `src/systems.py` (échange de système de shaders CS ↔ ENB : couches commun/CS/ENB, manifeste dans le jeu, sauvegardes vérifiées ; bases neutres dans `_SHADERS/_SYSTEMES`, recettes dans `systems.recettes`), `src/nexus.py` (API Nexus), `src/csSETTINGS.py` (interface PyQt6, dont l'onglet
  navigateur Nexus en QtWebEngine : profil persistant dans Application Support/csSETTINGS/web, liens nxm:// et
  téléchargements interceptés puis importés),
  `src/i18n.py` + `src/i18n_strings.py` (fr source, en/it/es).
- Build : `./build_app.sh` (ou `_tools/build_all.sh csSETTINGS`), identifiant `local.stephan.cspresets` (ancien nom conservé : ne pas le changer, sinon macOS redemande les autorisations).
- Tests : `tests/` (pytest).
