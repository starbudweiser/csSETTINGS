"""Traductions : {texte français: (anglais, italien, espagnol)}.

Les placeholders {x} doivent rester identiques dans toutes les langues (vérifié par tests/test_i18n.py).
"""

TR = {
    # ------------------------------------------------------------ fenêtre principale
    "Presets Community Shaders": ("Community Shaders presets", "Preset di Community Shaders", "Presets de Community Shaders"),
    "Réglages": ("Settings", "Impostazioni", "Ajustes"),
    "Presets": ("Presets", "Preset", "Presets"),
    "Sauvegardes": ("Backups", "Backup", "Copias de seguridad"),
    "Importer…": ("Import…", "Importa…", "Importar…"),
    "Une archive (.ZIP, .7Z, .RAR)…": ("An archive (.ZIP, .7Z, .RAR)…", "Un archivio (.ZIP, .7Z, .RAR)…",
                                       "Un archivo (.ZIP, .7Z, .RAR)…"),
    "Un dossier…": ("A folder…", "Una cartella…", "Una carpeta…"),
    "Depuis Nexus…": ("From Nexus…", "Da Nexus…", "Desde Nexus…"),
    "Enregistrer la config actuelle…": ("Save current config…", "Salva la configurazione attuale…",
                                        "Guardar la configuración actual…"),
    "Vous pouvez aussi glisser-déposer une archive ou un dossier sur la fenêtre.": (
        "You can also drag and drop an archive or a folder onto the window.",
        "Puoi anche trascinare un archivio o una cartella sulla finestra.",
        "También puede arrastrar y soltar un archivo o una carpeta en la ventana."),
    "Avant chaque application, la configuration en place est sauvegardée (onglet Sauvegardes). "
    "Aucun fichier du preset n'est modifié.": (
        "Before each apply, the current configuration is backed up (Backups tab). No preset file is modified.",
        "Prima di ogni applicazione la configurazione attuale viene salvata (scheda Backup). "
        "Nessun file del preset viene modificato.",
        "Antes de cada aplicación se guarda la configuración actual (pestaña Copias de seguridad). "
        "No se modifica ningún archivo del preset."),
    "Afficher dans le Finder": ("Show in Finder", "Mostra nel Finder", "Mostrar en el Finder"),
    "Retirer de la bibliothèque": ("Remove from library", "Rimuovi dalla libreria", "Quitar de la biblioteca"),
    "Appliquer ce preset": ("Apply this preset", "Applica questo preset", "Aplicar este preset"),
    "Restaurer cette sauvegarde": ("Restore this backup", "Ripristina questo backup", "Restaurar esta copia"),
    "Date": ("Date", "Data", "Fecha"),
    "Motif": ("Reason", "Motivo", "Motivo"),
    "Réglages CS": ("CS settings", "Impostazioni CS", "Ajustes CS"),
    "Contenu": ("Contents", "Contenuto", "Contenido"),
    "réglages": ("settings", "impostazioni", "ajustes"),
    "post-traitement seul": ("post-processing only", "solo post-elaborazione", "solo posprocesado"),
    "Post-traitement seul": ("Post-processing only", "Solo post-elaborazione", "Solo posprocesado"),
    "Aucun preset": ("No preset", "Nessun preset", "Ningún preset"),
    "Importez une archive, un dossier, ou téléchargez un preset depuis Nexus pour commencer. Bibliothèque : {lib}": (
        "Import an archive or a folder, or download a preset from Nexus to get started. Library: {lib}",
        "Importa un archivio o una cartella, o scarica un preset da Nexus per iniziare. Libreria: {lib}",
        "Importe un archivo o una carpeta, o descargue un preset desde Nexus para empezar. Biblioteca: {lib}"),
    "✓ Chargé": ("✓ Loaded", "✓ Caricato", "✓ Cargado"),
    "⚠ Réglages d'une autre version de CS": ("⚠ Settings from another CS version",
                                             "⚠ Impostazioni di un'altra versione di CS",
                                             "⚠ Ajustes de otra versión de CS"),
    "Source": ("Source", "Fonte", "Origen"),
    "Ajouté le": ("Added on", "Aggiunto il", "Añadido el"),
    "Remplace les réglages de Community Shaders (SettingsUser.json).": (
        "Replaces the Community Shaders settings (SettingsUser.json).",
        "Sostituisce le impostazioni di Community Shaders (SettingsUser.json).",
        "Reemplaza los ajustes de Community Shaders (SettingsUser.json)."),
    "Données de l'éditeur CS : {list}": ("CS editor data: {list}", "Dati dell'editor CS: {list}",
                                         "Datos del editor CS: {list}"),
    "Post-traitement ajouté au menu CS : {list}": ("Post-processing added to the CS menu: {list}",
                                                   "Post-elaborazione aggiunta al menu CS: {list}",
                                                   "Posprocesado añadido al menú CS: {list}"),
    "⚠ Jeu lancé : fermez-le avant d'appliquer": ("⚠ Game running: close it before applying",
                                                  "⚠ Gioco avviato: chiudilo prima di applicare",
                                                  "⚠ Juego en marcha: ciérrelo antes de aplicar"),
    "Jeu fermé": ("Game closed", "Gioco chiuso", "Juego cerrado"),
    "Preset « {name} » appliqué. Sauvegarde de l'ancienne configuration : {path}": (
        "Preset “{name}” applied. Previous configuration saved to: {path}",
        "Preset «{name}» applicato. Configurazione precedente salvata in: {path}",
        "Preset «{name}» aplicado. Configuración anterior guardada en: {path}"),
    "sauvegarde {name}": ("backup {name}", "backup {name}", "copia {name}"),
    "Sauvegarde {name} restaurée (configuration remplacée sauvegardée dans {path}).": (
        "Backup {name} restored (replaced configuration saved to {path}).",
        "Backup {name} ripristinato (configurazione sostituita salvata in {path}).",
        "Copia {name} restaurada (configuración reemplazada guardada en {path})."),
    "Nom du nouveau preset :": ("New preset name:", "Nome del nuovo preset:", "Nombre del nuevo preset:"),
    "Mon réglage %Y-%m-%d": ("My setup %Y-%m-%d", "Mia configurazione %Y-%m-%d", "Mi ajuste %Y-%m-%d"),
    "Un preset porte déjà ce nom.": ("A preset already has this name.", "Esiste già un preset con questo nome.",
                                     "Ya existe un preset con ese nombre."),
    "Configuration actuelle enregistrée : {path}": ("Current configuration saved: {path}",
                                                    "Configurazione attuale salvata: {path}",
                                                    "Configuración actual guardada: {path}"),
    "Retirer « {name} » de la bibliothèque ? Il est déplacé dans le dossier des sauvegardes, pas effacé.": (
        "Remove “{name}” from the library? It is moved to the backup folder, not deleted.",
        "Rimuovere «{name}» dalla libreria? Viene spostato nella cartella dei backup, non eliminato.",
        "¿Quitar «{name}» de la biblioteca? Se mueve a la carpeta de copias, no se borra."),
    "« {name} » déplacé dans {path}": ("“{name}” moved to {path}", "«{name}» spostato in {path}",
                                       "«{name}» movido a {path}"),
    "Nom du preset :": ("Preset name:", "Nome del preset:", "Nombre del preset:"),
    "Importé : {names}": ("Imported: {names}", "Importato: {names}", "Importado: {names}"),
    "Choisir une archive": ("Choose an archive", "Scegli un archivio", "Elegir un archivo"),
    "Choisir un dossier": ("Choose a folder", "Scegli una cartella", "Elegir una carpeta"),
    "Aucun preset Community Shaders trouvé dans « {src} » : il faut un SettingsUser.json ou un dossier PostProcessing.": (
        "No Community Shaders preset found in “{src}”: a SettingsUser.json or a PostProcessing folder is required.",
        "Nessun preset Community Shaders in «{src}»: serve un SettingsUser.json o una cartella PostProcessing.",
        "No se encontró ningún preset de Community Shaders en «{src}»: hace falta un SettingsUser.json "
        "o una carpeta PostProcessing."),
    "Impossible de lire « {src} » ({err}). Vérifiez que l'archive n'est pas protégée par un mot de passe.": (
        "Cannot read “{src}” ({err}). Check that the archive is not password-protected.",
        "Impossibile leggere «{src}» ({err}). Verifica che l'archivio non sia protetto da password.",
        "No se puede leer «{src}» ({err}). Compruebe que el archivo no esté protegido con contraseña."),
    "Dossier Community Shaders introuvable : {path}. Vérifiez les réglages et que le disque est branché.": (
        "Community Shaders folder not found: {path}. Check the settings and that the drive is connected.",
        "Cartella Community Shaders non trovata: {path}. Controlla le impostazioni e che il disco sia collegato.",
        "No se encuentra la carpeta de Community Shaders: {path}. Revise los ajustes y que el disco esté conectado."),
    "Ajouté depuis Nexus : {names}": ("Added from Nexus: {names}", "Aggiunto da Nexus: {names}",
                                      "Añadido desde Nexus: {names}"),
    "La nouvelle langue s'appliquera au prochain lancement.": (
        "The new language will apply at next launch.", "La nuova lingua verrà applicata al prossimo avvio.",
        "El nuevo idioma se aplicará en el próximo inicio."),

    # ------------------------------------------------------------ réglages
    "Bibliothèque de presets": ("Preset library", "Libreria dei preset", "Biblioteca de presets"),
    "Dossier Community Shaders du jeu": ("Game's Community Shaders folder", "Cartella Community Shaders del gioco",
                                         "Carpeta de Community Shaders del juego"),
    "Dossier des sauvegardes": ("Backup folder", "Cartella dei backup", "Carpeta de copias"),
    "Choisir…": ("Choose…", "Scegli…", "Elegir…"),
    "Automatique ({lang})": ("Automatic ({lang})", "Automatica ({lang})", "Automático ({lang})"),
    "Langue": ("Language", "Lingua", "Idioma"),
    "Nexus Mods": ("Nexus Mods", "Nexus Mods", "Nexus Mods"),
    "Collez votre clé d'API personnelle (page « API Keys » de votre compte Nexus). Elle est rangée dans le "
    "trousseau macOS, jamais dans un fichier. Le téléchargement direct demande un compte Premium.": (
        "Paste your personal API key (“API Keys” page of your Nexus account). It is stored in the macOS keychain, "
        "never in a file. Direct download requires a Premium account.",
        "Incolla la tua chiave API personale (pagina «API Keys» del tuo account Nexus). È conservata nel portachiavi "
        "di macOS, mai in un file. Il download diretto richiede un account Premium.",
        "Pegue su clave de API personal (página «API Keys» de su cuenta de Nexus). Se guarda en el llavero de macOS, "
        "nunca en un archivo. La descarga directa requiere una cuenta Premium."),
    "Clé d'API": ("API key", "Chiave API", "Clave de API"),
    "Vérifier": ("Check", "Verifica", "Comprobar"),
    "Ouvrir la page des clés": ("Open the keys page", "Apri la pagina delle chiavi", "Abrir la página de claves"),
    "Annuler": ("Cancel", "Annulla", "Cancelar"),
    "ENREGISTRER": ("SAVE", "SALVA", "GUARDAR"),
    "Premium": ("Premium", "Premium", "Premium"),
    "non Premium : téléchargement direct impossible": ("not Premium: direct download unavailable",
                                                        "non Premium: download diretto non disponibile",
                                                        "no Premium: descarga directa no disponible"),
    "✓ Clé valide : {name} ({prem})": ("✓ Valid key: {name} ({prem})", "✓ Chiave valida: {name} ({prem})",
                                       "✓ Clave válida: {name} ({prem})"),
    "✕ Clé refusée par Nexus ({err}).": ("✕ Key rejected by Nexus ({err}).", "✕ Chiave rifiutata da Nexus ({err}).",
                                         "✕ Clave rechazada por Nexus ({err})."),
    "Impossible d'enregistrer la clé dans le trousseau : {err}": (
        "Cannot save the key to the keychain: {err}", "Impossibile salvare la chiave nel portachiavi: {err}",
        "No se puede guardar la clave en el llavero: {err}"),

    # ------------------------------------------------------------ Nexus
    "Télécharger depuis Nexus Mods": ("Download from Nexus Mods", "Scarica da Nexus Mods", "Descargar desde Nexus Mods"),
    "Adresse de la page du mod ou numéro (ex. 165803)": ("Mod page address or number (e.g. 165803)",
                                                          "Indirizzo della pagina della mod o numero (es. 165803)",
                                                          "Dirección de la página del mod o número (p. ej. 165803)"),
    "Rechercher": ("Search", "Cerca", "Buscar"),
    "Fichier": ("File", "File", "Archivo"),
    "Catégorie": ("Category", "Categoria", "Categoría"),
    "Version": ("Version", "Versione", "Versión"),
    "Taille": ("Size", "Dimensione", "Tamaño"),
    "Le fichier téléchargé est ajouté à la bibliothèque. Aucun réglage du jeu n'est modifié.": (
        "The downloaded file is added to the library. No game setting is changed.",
        "Il file scaricato viene aggiunto alla libreria. Nessuna impostazione del gioco viene modificata.",
        "El archivo descargado se añade a la biblioteca. No se cambia ningún ajuste del juego."),
    "Fermer": ("Close", "Chiudi", "Cerrar"),
    "TÉLÉCHARGER ET IMPORTER": ("DOWNLOAD AND IMPORT", "SCARICA E IMPORTA", "DESCARGAR E IMPORTAR"),
    "Ajoutez d'abord votre clé d'API Nexus dans les réglages.": ("First add your Nexus API key in the settings.",
                                                                  "Aggiungi prima la tua chiave API Nexus nelle impostazioni.",
                                                                  "Añada primero su clave de API de Nexus en los ajustes."),
    "Adresse non reconnue. Collez l'adresse de la page du mod ou son numéro.": (
        "Address not recognized. Paste the mod page address or its number.",
        "Indirizzo non riconosciuto. Incolla l'indirizzo della pagina della mod o il suo numero.",
        "Dirección no reconocida. Pegue la dirección de la página del mod o su número."),
    "Recherche en cours…": ("Searching…", "Ricerca in corso…", "Buscando…"),
    "{n} fichier(s). Choisissez celui à télécharger.": ("{n} file(s). Choose the one to download.",
                                                        "{n} file. Scegli quello da scaricare.",
                                                        "{n} archivo(s). Elija el que desea descargar."),
    "Téléchargement de {f}…": ("Downloading {f}…", "Download di {f}…", "Descargando {f}…"),
    "✓ Ajouté à la bibliothèque : {names}": ("✓ Added to the library: {names}", "✓ Aggiunto alla libreria: {names}",
                                             "✓ Añadido a la biblioteca: {names}"),
    "L'archive ne contient ni SettingsUser.json ni fichier PostProcessing : ce n'est pas un preset Community "
    "Shaders (preset ReShade ou ENB ?).": (
        "The archive contains neither SettingsUser.json nor a PostProcessing file: it is not a Community Shaders "
        "preset (ReShade or ENB preset?).",
        "L'archivio non contiene né SettingsUser.json né file PostProcessing: non è un preset Community Shaders "
        "(preset ReShade o ENB?).",
        "El archivo no contiene SettingsUser.json ni ningún archivo PostProcessing: no es un preset de Community "
        "Shaders (¿preset de ReShade o ENB?)."),
    "Nexus refuse le téléchargement direct : il faut un compte Premium (ou téléchargez le fichier à la main puis "
    "utilisez « Importer »).": (
        "Nexus refuses direct download: a Premium account is required (or download the file manually, then use "
        "“Import”).",
        "Nexus rifiuta il download diretto: serve un account Premium (oppure scarica il file a mano e usa «Importa»).",
        "Nexus rechaza la descarga directa: se necesita una cuenta Premium (o descargue el archivo a mano y use "
        "«Importar»)."),
    "Échec : {err}": ("Failed: {err}", "Errore: {err}", "Error: {err}"),
    # ------------------------------------------------------------ compatibilité
    "⚠ incompatible en partie": ("⚠ partly incompatible", "⚠ in parte incompatibile", "⚠ incompatible en parte"),
    "Compatibilité non vérifiée : SettingsDefault.json introuvable dans le dossier Community Shaders du jeu. "
    "Vérifiez les réglages et que le disque est branché.": (
        "Compatibility not checked: SettingsDefault.json not found in the game's Community Shaders folder. "
        "Check the settings and that the drive is connected.",
        "Compatibilità non verificata: SettingsDefault.json non trovato nella cartella Community Shaders del gioco. "
        "Controlla le impostazioni e che il disco sia collegato.",
        "Compatibilidad no comprobada: no se encuentra SettingsDefault.json en la carpeta Community Shaders del "
        "juego. Compruebe los ajustes y que el disco esté conectado."),
    "<b>⚠ Features inconnues de votre Community Shaders {v}</b> : {list}. Elles seront ignorées ; le rendu peut "
    "différer des captures du preset (autre variante de CS, comme Jiaye AIO ou Open Shader ?).": (
        "<b>⚠ Features unknown to your Community Shaders {v}</b>: {list}. They will be ignored; the result may "
        "differ from the preset's screenshots (another CS variant, such as Jiaye AIO or Open Shader?).",
        "<b>⚠ Feature sconosciute al tuo Community Shaders {v}</b>: {list}. Saranno ignorate; la resa può "
        "differire dalle immagini del preset (un'altra variante di CS, come Jiaye AIO o Open Shader?).",
        "<b>⚠ Features desconocidas para su Community Shaders {v}</b>: {list}. Se ignorarán; el resultado puede "
        "diferir de las capturas del preset (¿otra variante de CS, como Jiaye AIO u Open Shader?)."),
    "<b>⚠ Effets de post-traitement inconnus</b> : {list}. Ils seront ignorés.": (
        "<b>⚠ Unknown post-processing effects</b>: {list}. They will be ignored.",
        "<b>⚠ Effetti di post-elaborazione sconosciuti</b>: {list}. Saranno ignorati.",
        "<b>⚠ Efectos de posprocesado desconocidos</b>: {list}. Se ignorarán."),
    "<b>ⓘ Features absentes du preset</b> : {list}. Elles garderont leurs valeurs par défaut.": (
        "<b>ⓘ Features missing from the preset</b>: {list}. They will keep their default values.",
        "<b>ⓘ Feature assenti dal preset</b>: {list}. Manterranno i valori predefiniti.",
        "<b>ⓘ Features ausentes del preset</b>: {list}. Conservarán sus valores por defecto."),
    "ⓘ {n} option(s) inconnue(s) dans des features connues : renommées ou retirées depuis la version du preset, "
    "elles seront ignorées.": (
        "ⓘ {n} unknown option(s) in known features: renamed or removed since the preset's version, they will be "
        "ignored.",
        "ⓘ {n} opzione/i sconosciuta/e in feature note: rinominate o rimosse dalla versione del preset, saranno "
        "ignorate.",
        "ⓘ {n} opción(es) desconocida(s) en features conocidas: renombradas o retiradas desde la versión del "
        "preset, se ignorarán."),
    "<b>✓ Compatible</b> : toutes les features du preset existent dans votre Community Shaders {v}.": (
        "<b>✓ Compatible</b>: every feature in the preset exists in your Community Shaders {v}.",
        "<b>✓ Compatibile</b>: tutte le feature del preset esistono nel tuo Community Shaders {v}.",
        "<b>✓ Compatible</b>: todas las features del preset existen en su Community Shaders {v}."),
    "« {name} » utilise des réglages que votre Community Shaders ne connaît pas ({list}). Ils seront ignorés. "
    "Appliquer quand même ? La configuration en place est sauvegardée avant.": (
        "“{name}” uses settings your Community Shaders does not know ({list}). They will be ignored. Apply anyway? "
        "The current configuration is backed up first.",
        "«{name}» usa impostazioni che il tuo Community Shaders non conosce ({list}). Saranno ignorate. Applicare "
        "comunque? La configurazione attuale viene salvata prima.",
        "«{name}» usa ajustes que su Community Shaders no conoce ({list}). Se ignorarán. ¿Aplicar de todos modos? "
        "La configuración actual se guarda antes."),
    "⚠ « {name} » : features inconnues de votre Community Shaders, elles seront ignorées ({list}).": (
        "⚠ “{name}”: features unknown to your Community Shaders, they will be ignored ({list}).",
        "⚠ «{name}»: feature sconosciute al tuo Community Shaders, saranno ignorate ({list}).",
        "⚠ «{name}»: features desconocidas para su Community Shaders, se ignorarán ({list})."),
}
