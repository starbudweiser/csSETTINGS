#!/bin/bash
# Compile la version Swift (macos/build_app.sh) : csSETTINGS.app à la racine du projet.
# _tools/build_all.sh csSETTINGS l'installe ensuite dans ~/Applications/Skyrim Tools.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/macos/build_app.sh" "$@"
