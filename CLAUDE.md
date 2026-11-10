# csSETTINGS

Sélecteur de presets Community Shaders (Bottled Shaders) pour la bouteille CrossOver Skyrim-MetalFX :
bibliothèque de presets, application avec sauvegarde automatique, restauration, import d'archives/dossiers,
téléchargement Nexus Mods (clé d'API dans le trousseau macOS), presets ENB, échange de système CS ↔ ENB.
Appli Swift native depuis la 2.0.0 (l'ancienne version Python/PyQt6 est dans l'historique git, jusqu'à 1.1.0).

- Interface : design system Socle (https://claude.ai/artifact/TkNj2Y6SQGZwT6EyME92Ah). `Socle.swift` est régénéré par
  `/Volumes/SKYRIM/TOOLS/DESIGN/Socle/sync_apps.sh`, `Updater.swift` / `UpdaterView.swift` par `_tools/sync_shared.sh` :
  ne pas les éditer ici. « cs » du nom dans le bleu du logo (#14a5e6).
- Code (`macos/`, paquet SwiftPM) :
  - `Sources/CSCore` (sans interface, testé) : `Core.swift` (réglages config.json, presets, sauvegardes, ENB, compatibilité,
    import par bsdtar), `Systems.swift` (couches commun/CS/ENB, manifeste `.csSETTINGS_systemes.json` dans le jeu, sauvegardes
    vérifiées, bases neutres et recettes), `Nexus.swift` (API v1, liens nxm://, clé par l'outil `security`, service
    « cSPRESETS Nexus API »), `JSON.swift` (JSON ordonné écrit comme json.dumps de Python : mêmes fichiers que la 1.x),
    `I18n.swift` + `Strings.swift` (clé = texte français, [en, it, es] ; anglais si la langue du Mac n'est pas prise en charge).
  - `Sources/csSETTINGS` : interface SwiftUI dans une fenêtre AppKit (`main.swift`, `Model.swift`, `Views.swift`,
    `NexusViews.swift` — navigateur WebKit, téléchargements et nxm:// interceptés puis importés —, `Settings.swift`, `About.swift`).
- Essais sans focus : `CSSETTINGS_QUIET=1`, `CSSETTINGS_CONFIG=<config.json>` (bac à sable), `CSSETTINGS_TAB=<n>`,
  `CSSETTINGS_SNAPSHOT=<png>`, `CSSETTINGS_SCRIPT="import:…;apply;restore;sys:CS;enb;snap:…;log:…;quit"` (voir `runScript`).
- Build : `./build_app.sh` (ou `_tools/build_all.sh csSETTINGS`, qui installe dans ~/Applications/Skyrim Tools), identifiant
  `local.stephan.cspresets` (ancien nom conservé : ne pas le changer). Notarisation : `_tools/notarize_app.sh csSETTINGS.app`.
- Tests : `swift test --package-path macos` (reprise des tests pytest de la 1.x).
