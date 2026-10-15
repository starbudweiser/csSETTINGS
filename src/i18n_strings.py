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
    "<b>⚠ Post-traitement du preset ignoré</b> : votre Community Shaders {v} rejettera sa chaîne de "
    "post-traitement ({why}) et la remplacera par une chaîne vide. Ni l'étalonnage ni les effets du preset ne seront "
    "rendus : refaites la chaîne en jeu ou prenez une version du preset faite pour CS {v}.": (
        "<b>⚠ Preset post-processing ignored</b>: your Community Shaders {v} will reject its post-processing chain "
        "({why}) and replace it with an empty chain. Neither the preset's grading nor its effects will be rendered: "
        "rebuild the chain in game or get a version of the preset made for CS {v}.",
        "<b>⚠ Post-elaborazione del preset ignorata</b>: il tuo Community Shaders {v} rifiuterà la sua catena di "
        "post-elaborazione ({why}) e la sostituirà con una catena vuota. Né la gradazione né gli effetti del preset "
        "saranno resi: ricostruisci la catena in gioco o usa una versione del preset fatta per CS {v}.",
        "<b>⚠ Posprocesado del preset ignorado</b>: su Community Shaders {v} rechazará su cadena de posprocesado "
        "({why}) y la sustituirá por una cadena vacía. Ni la gradación ni los efectos del preset se mostrarán: "
        "rehaga la cadena en el juego o use una versión del preset hecha para CS {v}."),
    "<b>⚠ Frame Generation forcée</b> : le preset l'active, et sous CrossOver elle fait planter le jeu au lancement. "
    "Désactivez-la en jeu (Upscaling) ou dans le SettingsUser.json du preset (frameGenerationForceEnable à 0).": (
        "<b>⚠ Forced Frame Generation</b>: the preset turns it on, and under CrossOver it crashes the game at launch. "
        "Turn it off in game (Upscaling) or in the preset's SettingsUser.json (frameGenerationForceEnable to 0).",
        "<b>⚠ Frame Generation forzata</b>: il preset la attiva, e con CrossOver fa crashare il gioco all'avvio. "
        "Disattivala nel gioco (Upscaling) o nel SettingsUser.json del preset (frameGenerationForceEnable a 0).",
        "<b>⚠ Frame Generation forzada</b>: el preset la activa, y con CrossOver hace que el juego se cierre al "
        "iniciar. Desactívela en el juego (Upscaling) o en el SettingsUser.json del preset "
        "(frameGenerationForceEnable a 0)."),
    "« {name} » force la Frame Generation de Community Shaders, qui fait planter le jeu sous CrossOver. Appliquer "
    "quand même ? La configuration en place est sauvegardée avant.": (
        "“{name}” forces Community Shaders' Frame Generation, which crashes the game under CrossOver. Apply anyway? "
        "The current configuration is backed up first.",
        "«{name}» forza la Frame Generation di Community Shaders, che fa crashare il gioco con CrossOver. Applicare "
        "comunque? La configurazione attuale viene salvata prima.",
        "«{name}» fuerza la Frame Generation de Community Shaders, que hace que el juego se cierre con CrossOver. "
        "¿Aplicar de todos modos? La configuración actual se guarda antes."),
    "⚠ « {name} » force la Frame Generation : le jeu plantera sous CrossOver.": (
        "⚠ “{name}” forces Frame Generation: the game will crash under CrossOver.",
        "⚠ «{name}» forza la Frame Generation: il gioco crasherà con CrossOver.",
        "⚠ «{name}» fuerza la Frame Generation: el juego se cerrará con CrossOver."),
    "étape Composite absente": ("Composite step missing", "passaggio Composite assente", "falta el paso Composite"),
    "effets inconnus : {list}": ("unknown effects: {list}", "effetti sconosciuti: {list}",
                                 "efectos desconocidos: {list}"),
    "preset fait pour CS {pv}": ("preset made for CS {pv}", "preset fatto per CS {pv}",
                                 "preset hecho para CS {pv}"),
    "Le post-traitement de « {name} » sera ignoré : votre Community Shaders {v} rejettera sa chaîne ({why}) et la "
    "remplacera par une chaîne vide. Appliquer quand même ? La configuration en place est sauvegardée avant.": (
        "The post-processing of “{name}” will be ignored: your Community Shaders {v} will reject its chain ({why}) "
        "and replace it with an empty chain. Apply anyway? The current configuration is backed up first.",
        "La post-elaborazione di «{name}» sarà ignorata: il tuo Community Shaders {v} rifiuterà la sua catena "
        "({why}) e la sostituirà con una catena vuota. Applicare comunque? La configurazione attuale viene salvata "
        "prima.",
        "El posprocesado de «{name}» se ignorará: su Community Shaders {v} rechazará su cadena ({why}) y la "
        "sustituirá por una cadena vacía. ¿Aplicar de todos modos? La configuración actual se guarda antes."),
    "⚠ « {name} » : post-traitement ignoré par votre Community Shaders ({why}).": (
        "⚠ “{name}”: post-processing ignored by your Community Shaders ({why}).",
        "⚠ «{name}»: post-elaborazione ignorata dal tuo Community Shaders ({why}).",
        "⚠ «{name}»: posprocesado ignorado por su Community Shaders ({why})."),
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
    # ------------------------------------------------------------ navigateur Nexus
    "Nexus": ("Nexus", "Nexus", "Nexus"),
    "Page précédente": ("Previous page", "Pagina precedente", "Página anterior"),
    "Page suivante": ("Next page", "Pagina successiva", "Página siguiente"),
    "Recharger": ("Reload", "Ricarica", "Recargar"),
    "Rechercher sur Nexus": ("Search Nexus", "Cerca su Nexus", "Buscar en Nexus"),
    "Ouvrir dans le navigateur": ("Open in browser", "Apri nel browser", "Abrir en el navegador"),
    "Choisir un fichier de ce mod…": ("Choose a file from this mod…", "Scegli un file di questa mod…",
                                      "Elegir un archivo de este mod…"),
    "Ouvrez la page d'un preset, puis cliquez sur « Mod manager download » ou sur un téléchargement manuel : "
    "le fichier est ajouté à la bibliothèque. Aucun réglage du jeu n'est modifié.": (
        "Open a preset's page, then click “Mod manager download” or a manual download: the file is added to the "
        "library. No game setting is changed.",
        "Apri la pagina di un preset, poi clicca su «Mod manager download» o su un download manuale: il file viene "
        "aggiunto alla libreria. Nessuna impostazione del gioco viene modificata.",
        "Abra la página de un preset y pulse «Mod manager download» o una descarga manual: el archivo se añade a la "
        "biblioteca. No se modifica ningún ajuste del juego."),
    "« {f} » n'est pas une archive .ZIP, .7Z ou .RAR : téléchargement ignoré.": (
        "“{f}” is not a .ZIP, .7Z or .RAR archive: download ignored.",
        "«{f}» non è un archivio .ZIP, .7Z o .RAR: download ignorato.",
        "«{f}» no es un archivo .ZIP, .7Z o .RAR: descarga ignorada."),
    "Téléchargement interrompu.": ("Download interrupted.", "Download interrotto.", "Descarga interrumpida."),
    "Lien de téléchargement non reconnu.": ("Download link not recognised.", "Link di download non riconosciuto.",
                                           "Enlace de descarga no reconocido."),
    "Ce fichier n'est pas pour Skyrim Special Edition.": ("This file is not for Skyrim Special Edition.",
                                                         "Questo file non è per Skyrim Special Edition.",
                                                         "Este archivo no es para Skyrim Special Edition."),
    "Téléchargement depuis Nexus…": ("Downloading from Nexus…", "Download da Nexus…", "Descargando desde Nexus…"),
    # ------------------------------------------------------------ partie ENB
    "<b>Preset ENB (Effects 11)</b> : remplace enbseries.ini et le dossier enbseries à la racine du jeu. "
    "Ceux en place sont déplacés dans la sauvegarde, rien n'est effacé.": (
        "<b>ENB preset (Effects 11)</b>: replaces enbseries.ini and the enbseries folder in the game folder. "
        "The current ones are moved into the backup; nothing is deleted.",
        "<b>Preset ENB (Effects 11)</b>: sostituisce enbseries.ini e la cartella enbseries nella cartella del gioco. "
        "Quelli attuali vengono spostati nel backup, nulla viene eliminato.",
        "<b>Preset ENB (Effects 11)</b>: reemplaza enbseries.ini y la carpeta enbseries en la carpeta del juego. "
        "Los actuales se mueven a la copia de seguridad; no se borra nada."),
    "+ ENB": ("+ ENB", "+ ENB", "+ ENB"),
    # ------------------------------------------------------------ systèmes de shaders (CS / ENB)
    'Presets ENB': (
        'ENB presets',
        'Preset ENB',
        'Presets ENB'),
    'Système': (
        'System',
        'Sistema',
        'Sistema'),
    ("Le système ENB est actif : les presets Community Shaders ne s'appliquent pas. Passez à Community Shaders "
     "dans l'onglet Système."): (
        'The ENB system is active: Community Shaders presets do not apply. Switch to Community Shaders in the System tab.',
        'Il sistema ENB è attivo: i preset di Community Shaders non si applicano. Passa a Community Shaders nella scheda Sistema.',
        'El sistema ENB está activo: los presets de Community Shaders no se aplican. Pase a Community Shaders en la pestaña Sistema.'),
    "Enregistrer l'ENB actuel…": (
        'Save current ENB…',
        "Salva l'ENB attuale…",
        'Guardar el ENB actual…'),
    "Le système ENB n'est pas actif : passez-y depuis l'onglet Système pour appliquer un preset ENB.": (
        'The ENB system is not active: switch to it from the System tab to apply an ENB preset.',
        'Il sistema ENB non è attivo: passa a ENB dalla scheda Sistema per applicare un preset ENB.',
        'El sistema ENB no está activo: pase a él desde la pestaña Sistema para aplicar un preset ENB.'),
    ('Avant chaque application, enbseries.ini et le dossier enbseries en place sont déplacés dans la sauvegarde, '
     "rien n'est effacé. Aucun fichier du preset n'est modifié."): (
        'Before each application, the enbseries.ini and enbseries folder in place are moved into the backup, nothing is deleted. No file of the preset is modified.',
        'Prima di ogni applicazione, enbseries.ini e la cartella enbseries in uso vengono spostati nel backup, nulla viene eliminato. Nessun file del preset viene modificato.',
        'Antes de cada aplicación, enbseries.ini y la carpeta enbseries en uso se mueven a la copia de seguridad, no se borra nada. Ningún archivo del preset se modifica.'),
    'Appliquer ce preset ENB': (
        'Apply this ENB preset',
        'Applica questo preset ENB',
        'Aplicar este preset ENB'),
    'Remplace enbseries.ini et le dossier enbseries à la racine du jeu ({n} effets).': (
        'Replaces enbseries.ini and the enbseries folder at the game root ({n} effects).',
        'Sostituisce enbseries.ini e la cartella enbseries nella radice del gioco ({n} effetti).',
        'Sustituye enbseries.ini y la carpeta enbseries en la raíz del juego ({n} efectos).'),
    'Preset ENB appliqué : {name}. Ancienne config sauvegardée dans {saved}': (
        'ENB preset applied: {name}. Previous config backed up in {saved}',
        'Preset ENB applicato: {name}. Configurazione precedente salvata in {saved}',
        'Preset ENB aplicado: {name}. Configuración anterior guardada en {saved}'),
    'Nom du preset ENB à enregistrer :': (
        'Name of the ENB preset to save:',
        'Nome del preset ENB da salvare:',
        'Nombre del preset ENB a guardar:'),
    'Preset ENB enregistré : {name}': (
        'ENB preset saved: {name}',
        'Preset ENB salvato: {name}',
        'Preset ENB guardado: {name}'),
    ('Un système de shaders à la fois : Community Shaders (Bottled) ou ENB. Chaque système a une base neutre ; '
     "passer de l'un à l'autre retire proprement l'ancien (ce que vous avez modifié est mis de côté, jamais "
     'perdu) et pose le nouveau. Les pièces communes (KiLoader…) restent.'): (
        'One shader system at a time: Community Shaders (Bottled) or ENB. Each system has a neutral base; switching from one to the other cleanly removes the old one (anything you changed is set aside, never lost) and installs the new one. Shared parts (KiLoader…) stay.',
        "Un solo sistema di shader alla volta: Community Shaders (Bottled) o ENB. Ogni sistema ha una base neutra; passare dall'uno all'altro rimuove con cura il vecchio (ciò che hai modificato viene messo da parte, mai perso) e installa il nuovo. Le parti comuni (KiLoader…) restano.",
        'Un solo sistema de shaders a la vez: Community Shaders (Bottled) o ENB. Cada sistema tiene una base neutra; pasar de uno a otro retira limpiamente el anterior (lo que haya modificado se aparta, nunca se pierde) e instala el nuevo. Las piezas comunes (KiLoader…) se quedan.'),
    'Retirer le système': (
        'Remove the system',
        'Rimuovi il sistema',
        'Retirar el sistema'),
    'Reconstruire les bases…': (
        'Rebuild the bases…',
        'Ricostruisci le basi…',
        'Reconstruir las bases…'),
    'Afficher les bases': (
        'Show the bases',
        'Mostra le basi',
        'Mostrar las bases'),
    'Historique des échanges': (
        'Swap history',
        'Cronologia degli scambi',
        'Historial de cambios'),
    'Afficher la sauvegarde dans le Finder': (
        'Show the backup in Finder',
        'Mostra il backup nel Finder',
        'Mostrar la copia en el Finder'),
    'Installation': (
        'Installation',
        'Installazione',
        'Instalación'),
    'Retrait': (
        'Removal',
        'Rimozione',
        'Retirada'),
    "Opération en cours… ne fermez pas l'application ni le disque.": (
        'Operation in progress… do not close the app or the disk.',
        "Operazione in corso… non chiudere l'app né il disco.",
        'Operación en curso… no cierre la aplicación ni el disco.'),
    'Système « {name} » retiré. Sauvegardes : {dir}': (
        'System “{name}” removed. Backups: {dir}',
        'Sistema «{name}» rimosso. Backup: {dir}',
        'Sistema «{name}» retirado. Copias: {dir}'),
    'Bibliothèque : {lib}': (
        'Library: {lib}',
        'Libreria: {lib}',
        'Biblioteca: {lib}'),
    'Bibliothèque de presets ENB': (
        'ENB presets library',
        'Libreria dei preset ENB',
        'Biblioteca de presets ENB'),
    'Dossier des bases de systèmes (CS / ENB)': (
        'Folder of the system bases (CS / ENB)',
        'Cartella delle basi dei sistemi (CS / ENB)',
        'Carpeta de las bases de los sistemas (CS / ENB)'),
    'Aucun preset ENB': (
        'No ENB preset',
        'Nessun preset ENB',
        'Ningún preset ENB'),
    'Rangez vos presets ENB (un dossier avec enbseries.ini et enbseries/) dans : {lib}': (
        'Put your ENB presets (a folder with enbseries.ini and enbseries/) in: {lib}',
        'Metti i tuoi preset ENB (una cartella con enbseries.ini e enbseries/) in: {lib}',
        'Guarde sus presets ENB (una carpeta con enbseries.ini y enbseries/) en: {lib}'),
    'enblocal.ini du preset non appliqué : il règle la machine, pas le rendu.': (
        "The preset's enblocal.ini is not applied: it tunes the machine, not the look.",
        "L'enblocal.ini del preset non viene applicato: regola la macchina, non la resa.",
        'El enblocal.ini del preset no se aplica: ajusta la máquina, no el aspecto.'),
    'Opération': (
        'Operation',
        'Operazione',
        'Operación'),
    'Couche': (
        'Layer',
        'Livello',
        'Capa'),
    'État': (
        'Status',
        'Stato',
        'Estado'),
    '<b>⚠ Dossier du jeu introuvable</b> : {path}. Vérifiez les réglages et que le disque est branché.': (
        '<b>⚠ Game folder not found</b>: {path}. Check the settings and that the disk is connected.',
        '<b>⚠ Cartella del gioco non trovata</b>: {path}. Controlla le impostazioni e che il disco sia collegato.',
        '<b>⚠ Carpeta del juego no encontrada</b>: {path}. Compruebe los ajustes y que el disco esté conectado.'),
    'Aucune base neutre construite : cliquez sur « Reconstruire les bases… ».': (
        'No neutral base built: click “Rebuild the bases…”.',
        'Nessuna base neutra costruita: fai clic su «Ricostruisci le basi…».',
        'Ninguna base neutra construida: pulse «Reconstruir las bases…».'),
    '✕ {err}': (
        '✕ {err}',
        '✕ {err}',
        '✕ {err}'),
    ("L'opération a échoué : {err}. Le jeu a été remis dans son état d'avant si l'échec est survenu en cours de "
     'route ; les sauvegardes sont dans {dir}.'): (
        'The operation failed: {err}. The game was put back as it was if the failure happened midway; backups are in {dir}.',
        "L'operazione è fallita: {err}. Il gioco è stato ripristinato com'era se l'errore è avvenuto a metà; i backup sono in {dir}.",
        'La operación falló: {err}. El juego se dejó como estaba si el fallo ocurrió a medias; las copias están en {dir}.'),
    ("Reprendre l'installation actuelle comme « {name} » : {n} fichiers identiques à la base seront suivis (rien "
     "n'est recopié ni modifié). Ils seront retirés avec ce système lors d'un échange."): (
        'Take over the current installation as “{name}”: {n} files identical to the base will be tracked (nothing is copied or changed). They will be removed with this system on a swap.',
        "Riprendere l'installazione attuale come «{name}»: {n} file identici alla base saranno tracciati (nulla viene copiato o modificato). Saranno rimossi con questo sistema in caso di scambio.",
        'Retomar la instalación actual como «{name}»: se seguirán {n} archivos idénticos a la base (no se copia ni se cambia nada). Se retirarán con este sistema en un cambio.'),
    ('Passer à « {name} » ?\n'
     '\n'
     "• {r} fichier(s) de l'ancien système retirés, dont {a} modifiés depuis la pose (mis de côté dans la "
     'sauvegarde)\n'
     '• {add} fichier(s) ajoutés, {rep} remplacés (originaux sauvegardés)\n'
     '\n'
     'Sauvegardes : {dir}'): (
        'Switch to “{name}”?\n\n• {r} file(s) of the old system removed, {a} of them modified since install (set aside in the backup)\n• {add} file(s) added, {rep} replaced (originals backed up)\n\nBackups: {dir}',
        "Passare a «{name}»?\n\n• {r} file del vecchio sistema rimossi, di cui {a} modificati dopo l'installazione (messi da parte nel backup)\n• {add} file aggiunti, {rep} sostituiti (originali salvati)\n\nBackup: {dir}",
        '¿Pasar a «{name}»?\n\n• {r} archivo(s) del sistema anterior retirados, {a} de ellos modificados desde la instalación (apartados en la copia)\n• {add} archivo(s) añadidos, {rep} sustituidos (originales guardados)\n\nCopias: {dir}'),
    'Système « {name} » en place. Sauvegardes : {dir}': (
        'System “{name}” in place. Backups: {dir}',
        'Sistema «{name}» installato. Backup: {dir}',
        'Sistema «{name}» en su sitio. Copias: {dir}'),
    ('Retirer le système « {name} » ? Ce que vous avez modifié est mis de côté dans la sauvegarde et les '
     "fichiers d'origine remplacés sont remis. Sans système, le jeu n'aura plus de shaders de rendu."): (
        'Remove the system “{name}”? Anything you changed is set aside in the backup and the original files that were replaced are put back. Without a system, the game will have no rendering shaders.',
        'Rimuovere il sistema «{name}»? Ciò che hai modificato viene messo da parte nel backup e i file originali sostituiti vengono rimessi. Senza sistema, il gioco non avrà shader di rendering.',
        '¿Retirar el sistema «{name}»? Lo que haya modificado se aparta en la copia y se devuelven los archivos originales sustituidos. Sin sistema, el juego no tendrá shaders de renderizado.'),
    ('Reconstruire les bases neutres à partir de {src} ? Les bases actuelles sont mises de côté (dossier '
     '_anciennes), jamais supprimées.'): (
        'Rebuild the neutral bases from {src}? The current bases are set aside (_anciennes folder), never deleted.',
        'Ricostruire le basi neutre da {src}? Le basi attuali vengono messe da parte (cartella _anciennes), mai eliminate.',
        '¿Reconstruir las bases neutras desde {src}? Las bases actuales se apartan (carpeta _anciennes), nunca se borran.'),
    "Impossible d'appliquer « {name} » ({err}).": (
        'Could not apply “{name}” ({err}).',
        'Impossibile applicare «{name}» ({err}).',
        'No se pudo aplicar «{name}» ({err}).'),
    'Un preset ENB porte déjà ce nom.': (
        'An ENB preset already has this name.',
        'Esiste già un preset ENB con questo nome.',
        'Ya existe un preset ENB con este nombre.'),
    'Aucun enbseries.ini à la racine du jeu : rien à enregistrer.': (
        'No enbseries.ini at the game root: nothing to save.',
        'Nessun enbseries.ini nella radice del gioco: niente da salvare.',
        'No hay enbseries.ini en la raíz del juego: nada que guardar.'),
    '<b>Système actif</b> : {name}': (
        '<b>Active system</b>: {name}',
        '<b>Sistema attivo</b>: {name}',
        '<b>Sistema activo</b>: {name}'),
    ("<b>Aucun système géré par csSETTINGS</b> : l'installation actuelle n'est pas encore suivie. Reprenez-la ou "
     'choisissez un système ci-dessous.'): (
        '<b>No system managed by csSETTINGS</b>: the current installation is not tracked yet. Take it over or choose a system below.',
        "<b>Nessun sistema gestito da csSETTINGS</b>: l'installazione attuale non è ancora tracciata. Riprendila o scegli un sistema qui sotto.",
        '<b>Ningún sistema gestionado por csSETTINGS</b>: la instalación actual aún no se sigue. Retómela o elija un sistema abajo.'),
    'Skyrim {v} détecté, SKSE présent.': (
        'Skyrim {v} detected, SKSE present.',
        'Skyrim {v} rilevato, SKSE presente.',
        'Skyrim {v} detectado, SKSE presente.'),
    'intact': (
        'intact',
        'intatto',
        'intacto'),
    '{m} modifié(s), {a} absent(s) depuis la pose': (
        '{m} modified, {a} missing since install',
        "{m} modificati, {a} mancanti dopo l'installazione",
        '{m} modificados, {a} ausentes desde la instalación'),
    '{name} : base absente': (
        '{name}: base missing',
        '{name}: base mancante',
        '{name}: base ausente'),
    '<b>{name}</b> : {n} fichiers, construite le {date}': (
        '<b>{name}</b>: {n} files, built on {date}',
        '<b>{name}</b>: {n} file, costruita il {date}',
        '<b>{name}</b>: {n} archivos, construida el {date}'),
    '✓ {name} (actif)': (
        '✓ {name} (active)',
        '✓ {name} (attivo)',
        '✓ {name} (activo)'),
    "Reprendre l'installation actuelle ({name})": (
        'Take over the current installation ({name})',
        "Riprendi l'installazione attuale ({name})",
        'Retomar la instalación actual ({name})'),
    'Paquet introuvable : {path}': (
        'Package not found: {path}',
        'Pacchetto non trovato: {path}',
        'Paquete no encontrado: {path}'),
    'Bases reconstruites : {list}': (
        'Bases rebuilt: {list}',
        'Basi ricostruite: {list}',
        'Bases reconstruidas: {list}'),
    'Passer à {name}': (
        'Switch to {name}',
        'Passa a {name}',
        'Pasar a {name}'),
    'Installer {name}': (
        'Install {name}',
        'Installa {name}',
        'Instalar {name}'),
    "Un processus ressemble au jeu : {proc}. Si Skyrim est bien fermé (seul CrossOver est ouvert), continuer quand "
    "même ?": (
        "A process looks like the game: {proc}. If Skyrim is really closed (only CrossOver is open), continue anyway?",
        "Un processo sembra il gioco: {proc}. Se Skyrim è davvero chiuso (è aperto solo CrossOver), continuare comunque?",
        "Un proceso parece el juego: {proc}. Si Skyrim está realmente cerrado (solo CrossOver está abierto), "
        "¿continuar de todos modos?"),
}
