"""csPRESETS : sélecteur de presets Community Shaders pour Skyrim (bouteille CrossOver).

Choisir un preset, l'appliquer en un clic (la configuration en place est sauvegardée avant),
restaurer une sauvegarde, importer une archive ou un dossier, télécharger depuis Nexus Mods.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import QLocale, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem,
                             QTabWidget, QVBoxLayout, QWidget)

import core
import i18n
import nexus
import socle_qt as S
from i18n import L

APP = "csPRESETS"


# ------------------------------------------------------------------ utilitaires

class Worker(QThread):
    """Exécute fn(progress) hors du fil de l'interface."""
    progress = pyqtSignal(int, int)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(lambda a, b: self.progress.emit(int(a), int(b))))
        except Exception as e:  # noqa: BLE001 — l'erreur est montrée à l'utilisateur
            self.failed.emit(f"{type(e).__name__}: {e}")


def reveal(path) -> None:
    subprocess.run(["open", "-R", str(path)])


def human_size(kb) -> str:
    try:
        kb = float(kb)
    except (TypeError, ValueError):
        return ""
    return f"{kb / 1024:.1f} Mo" if kb >= 1024 else f"{kb:.0f} Ko"


# ------------------------------------------------------------------ réglages

class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(L("Réglages"))
        self.cfg = dict(cfg)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*[int(S.m("space-6"))] * 4)
        lay.setSpacing(int(S.m("space-4")))

        form = QFormLayout()
        form.setSpacing(int(S.m("space-2")))
        self.fields = {}
        for key, label in (("library", L("Bibliothèque de presets")), ("cs_dir", L("Dossier Community Shaders du jeu")),
                           ("backup_dir", L("Dossier des sauvegardes"))):
            row = QHBoxLayout()
            ed = QLineEdit(self.cfg[key])
            S.role(ed, "path")
            btn = QPushButton(L("Choisir…"))
            btn.clicked.connect(lambda _=False, e=ed: self._pick(e))
            row.addWidget(ed, 1)
            row.addWidget(btn)
            form.addRow(label, row)
            self.fields[key] = ed

        self.lang = QComboBox()
        sys_lang = i18n.system_lang(QLocale.system().uiLanguages(), "fr")
        self.lang.addItem(L("Automatique ({lang})", lang=i18n.LANGS[sys_lang]), "auto")
        for code, name in i18n.LANGS.items():
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.cfg.get("lang", "auto"))))
        form.addRow(L("Langue"), self.lang)
        lay.addLayout(form)

        title = QLabel(L("Nexus Mods"))
        S.role(title, "title")
        lay.addWidget(title)
        info = QLabel(L("Collez votre clé d'API personnelle (page « API Keys » de votre compte Nexus). "
                        "Elle est rangée dans le trousseau macOS, jamais dans un fichier. "
                        "Le téléchargement direct demande un compte Premium."))
        info.setWordWrap(True)
        S.role(info, "muted")
        lay.addWidget(info)
        krow = QHBoxLayout()
        self.key = QLineEdit(nexus.get_key())
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText(L("Clé d'API"))
        check = QPushButton(L("Vérifier"))
        check.clicked.connect(self._check)
        page = QPushButton(L("Ouvrir la page des clés"))
        S.variant(page, "tertiary")
        page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.nexusmods.com/settings/api-keys")))
        krow.addWidget(self.key, 1)
        krow.addWidget(check)
        krow.addWidget(page)
        lay.addLayout(krow)
        self.key_state = QLabel("")
        S.role(self.key_state, "meta")
        lay.addWidget(self.key_state)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton(L("Annuler"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(L("ENREGISTRER"))
        S.variant(ok, "primary")
        ok.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)
        self.resize(760, 0)
        S.fit_height(self)

    def _pick(self, ed: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, L("Choisir un dossier"), ed.text())
        if d:
            ed.setText(d)

    def _check(self):
        key = self.key.text().strip()
        if not key:
            return
        try:
            u = nexus.validate(key)
            prem = L("Premium") if u.get("is_premium") else L("non Premium : téléchargement direct impossible")
            self.key_state.setText(L("✓ Clé valide : {name} ({prem})", name=u.get("name", "?"), prem=prem))
            S.status(self.key_state, "success" if u.get("is_premium") else "warning")
        except nexus.NexusError as e:
            self.key_state.setText(L("✕ Clé refusée par Nexus ({err}).", err=e))
            S.status(self.key_state, "danger")

    def _save(self):
        for k, ed in self.fields.items():
            self.cfg[k] = ed.text().strip()
        self.cfg["lang"] = self.lang.currentData()
        key = self.key.text().strip()
        try:
            if key and key != nexus.get_key():
                nexus.set_key(key)
            elif not key:
                nexus.delete_key()
        except nexus.NexusError as e:
            QMessageBox.warning(self, APP, L("Impossible d'enregistrer la clé dans le trousseau : {err}", err=e))
            return
        self.accept()


# ------------------------------------------------------------------ Nexus

class NexusDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.mod_id = 0
        self.mod = {}
        self.files = []
        self.worker = None
        self.created = []
        self.setWindowTitle(L("Télécharger depuis Nexus Mods"))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*[int(S.m("space-6"))] * 4)
        lay.setSpacing(int(S.m("space-3")))

        row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText(L("Adresse de la page du mod ou numéro (ex. 165803)"))
        self.url.returnPressed.connect(self._search)
        go = QPushButton(L("Rechercher"))
        go.clicked.connect(self._search)
        row.addWidget(self.url, 1)
        row.addWidget(go)
        lay.addLayout(row)

        self.title = QLabel("")
        S.role(self.title, "title")
        self.title.setWordWrap(True)
        lay.addWidget(self.title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([L("Fichier"), L("Catégorie"), L("Version"), L("Taille"), L("Date")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._sel)
        lay.addWidget(self.table, 1)

        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        S.role(self.desc, "muted")
        lay.addWidget(self.desc)

        self.bar = QProgressBar()
        self.bar.setVisible(False)
        lay.addWidget(self.bar)
        self.state = QLabel(L("Le fichier téléchargé est ajouté à la bibliothèque. Aucun réglage du jeu n'est modifié."))
        S.role(self.state, "meta")
        self.state.setWordWrap(True)
        lay.addWidget(self.state)

        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton(L("Fermer"))
        close.clicked.connect(self.reject)
        self.dl = QPushButton(L("TÉLÉCHARGER ET IMPORTER"))
        S.variant(self.dl, "primary")
        self.dl.setEnabled(False)
        self.dl.clicked.connect(self._download)
        btns.addWidget(close)
        btns.addWidget(self.dl)
        lay.addLayout(btns)
        self.resize(820, 560)

    def _key(self) -> str:
        key = nexus.get_key()
        if not key:
            QMessageBox.information(self, APP, L("Ajoutez d'abord votre clé d'API Nexus dans les réglages."))
        return key

    def _search(self):
        key = self._key()
        if not key:
            return
        try:
            self.mod_id = nexus.parse_mod_id(self.url.text())
        except ValueError:
            self.state.setText(L("Adresse non reconnue. Collez l'adresse de la page du mod ou son numéro."))
            S.status(self.state, "warning")
            return
        self.state.setText(L("Recherche en cours…"))
        S.status(self.state, "none")
        self.table.setRowCount(0)
        mid = self.mod_id
        self._run(lambda p: (nexus.mod_info(mid, key), nexus.mod_files(mid, key)), self._found)

    def _found(self, res):
        self.mod, self.files = res
        self.title.setText(f"{self.mod.get('name', '?')} — {self.mod.get('author', '')}")
        self.table.setRowCount(len(self.files))
        for r, f in enumerate(self.files):
            date = time.strftime("%Y-%m-%d", time.localtime(f.get("uploaded_timestamp") or 0))
            for c, v in enumerate((f.get("name", ""), f.get("category_name", ""), f.get("version", ""),
                                   human_size(f.get("size_kb")), date)):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
        self.state.setText(L("{n} fichier(s). Choisissez celui à télécharger.", n=len(self.files)))
        if self.files:
            self.table.selectRow(0)

    def _sel(self):
        r = self.table.currentRow()
        ok = 0 <= r < len(self.files)
        self.dl.setEnabled(ok)
        if ok:
            self.desc.setText((self.files[r].get("description") or "").replace("<br />", " ")[:400])

    def _download(self):
        key = self._key()
        r = self.table.currentRow()
        if not key or not (0 <= r < len(self.files)):
            return
        f = self.files[r]
        mid, mod = self.mod_id, self.mod
        name = core.safe_name(f"{mod.get('name', 'Nexus')} - {f.get('name', '')}")[:90]
        meta = {"source": "Nexus Mods", "nexus_id": mid, "mod": mod.get("name"), "author": mod.get("author"),
                "file": f.get("name"), "version": f.get("version"),
                "url": f"https://www.nexusmods.com/{nexus.GAME}/mods/{mid}"}
        cfg = self.cfg

        def job(progress):
            with tempfile.TemporaryDirectory(prefix="cspresets_dl_") as tmp:
                path = nexus.download(mid, f, key, Path(tmp), progress)
                return core.import_source(cfg, path, name, meta)

        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self.dl.setEnabled(False)
        self.state.setText(L("Téléchargement de {f}…", f=f.get("file_name", "")))
        self._run(job, self._imported)

    def _imported(self, made):
        self.bar.setVisible(False)
        self.created += made
        self.state.setText(L("✓ Ajouté à la bibliothèque : {names}", names=", ".join(p.name for p in made)))
        S.status(self.state, "success")
        self.dl.setEnabled(True)

    def _run(self, fn, ok):
        self.worker = Worker(fn)
        self.worker.progress.connect(self._prog)
        self.worker.done.connect(ok)
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _prog(self, got, total):
        if total:
            self.bar.setRange(0, total)
            self.bar.setValue(got)

    def _fail(self, err):
        self.bar.setVisible(False)
        self.dl.setEnabled(bool(self.files))
        if "LookupError" in err:
            msg = L("L'archive ne contient ni SettingsUser.json ni fichier PostProcessing : ce n'est pas un preset "
                    "Community Shaders (preset ReShade ou ENB ?).")
        elif "HTTP 403" in err:
            msg = L("Nexus refuse le téléchargement direct : il faut un compte Premium (ou téléchargez le fichier "
                    "à la main puis utilisez « Importer »).")
        else:
            msg = L("Échec : {err}", err=err)
        self.state.setText(msg)
        S.status(self.state, "danger")


# ------------------------------------------------------------------ fenêtre principale

class Main(QWidget):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(APP)
        self.setAcceptDrops(True)
        self.resize(1100, 680)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # en-tête
        bar = QWidget()
        bar.setObjectName("header")
        bar.setFixedHeight(int(S.m("size-bar")))
        bar.setStyleSheet(f"#header {{ background: {S.c('surface-raised')}; border-bottom: 1px solid {S.c('border')}; }}")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(int(S.m("space-3")), 0, int(S.m("space-3")), 0)
        t = QLabel(APP)
        S.role(t, "title")
        sub = QLabel(L("Presets Community Shaders"))
        S.role(sub, "subtle")
        self.game = QLabel("")
        S.role(self.game, "meta")
        gear = QPushButton(L("Réglages"))
        S.variant(gear, "tertiary")
        gear.clicked.connect(self.settings)
        hb.addWidget(t)
        hb.addWidget(sub)
        hb.addStretch(1)
        hb.addWidget(self.game)
        hb.addWidget(gear)
        root.addWidget(bar)

        body = QWidget()
        bl = QVBoxLayout(body)
        m = int(S.m("space-3"))
        bl.setContentsMargins(m, m, m, m)
        bl.setSpacing(m)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._presets_tab(), L("Presets"))
        self.tabs.addTab(self._backups_tab(), L("Sauvegardes"))
        bl.addWidget(self.tabs, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(90)
        S.role(self.log, "mono")
        bl.addWidget(self.log)
        root.addWidget(body, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._game_state)
        self.timer.start(3000)
        self.refresh()

    # ---------------------------------------------------------- onglet presets
    def _presets_tab(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, int(S.m("space-3")), 0, 0)
        split = QSplitter()
        split.setHandleWidth(8)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(int(S.m("space-2")))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._show)
        self.list.itemDoubleClicked.connect(lambda _i: self.apply())
        ll.addWidget(self.list, 1)
        row = QHBoxLayout()
        imp = QPushButton(L("Importer…"))
        menu = QMenu(imp)
        menu.addAction(L("Une archive (.ZIP, .7Z, .RAR)…"), self.import_archive)
        menu.addAction(L("Un dossier…"), self.import_folder)
        imp.setMenu(menu)
        nx = QPushButton(L("Depuis Nexus…"))
        nx.clicked.connect(self.from_nexus)
        save = QPushButton(L("Enregistrer la config actuelle…"))
        save.clicked.connect(self.save_current)
        row.addWidget(imp)
        row.addWidget(nx)
        row.addWidget(save)
        ll.addLayout(row)
        hint = QLabel(L("Vous pouvez aussi glisser-déposer une archive ou un dossier sur la fenêtre."))
        S.role(hint, "subtle")
        hint.setWordWrap(True)
        ll.addWidget(hint)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(int(S.m("space-3")), 0, 0, 0)
        rl.setSpacing(int(S.m("space-3")))
        self.name = QLabel("")
        S.role(self.name, "heading")
        self.name.setWordWrap(True)
        self.badges = QLabel("")
        self.badges.setTextFormat(Qt.TextFormat.RichText)
        S.role(self.badges, "meta")
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setOpenExternalLinks(True)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.compat = QLabel("")
        self.compat.setWordWrap(True)
        self.compat.setTextFormat(Qt.TextFormat.RichText)
        self.compat.setVisible(False)
        rl.addWidget(self.name)
        rl.addWidget(self.badges)
        rl.addWidget(self.compat)
        rl.addWidget(self.details, 1)
        reassure = QLabel(L("Avant chaque application, la configuration en place est sauvegardée "
                            "(onglet Sauvegardes). Aucun fichier du preset n'est modifié."))
        reassure.setWordWrap(True)
        S.role(reassure, "subtle")
        rl.addWidget(reassure)
        brow = QHBoxLayout()
        self.btn_reveal = QPushButton(L("Afficher dans le Finder"))
        S.variant(self.btn_reveal, "tertiary")
        self.btn_reveal.clicked.connect(lambda: self._cur() and reveal(self._cur().path))
        self.btn_remove = QPushButton(L("Retirer de la bibliothèque"))
        S.variant(self.btn_remove, "tertiary")
        self.btn_remove.clicked.connect(self.remove)
        self.btn_apply = QPushButton(L("Appliquer ce preset"))
        S.variant(self.btn_apply, "action")
        self.btn_apply.setMinimumHeight(int(S.m("size-control-lg")))
        self.btn_apply.clicked.connect(self.apply)
        brow.addWidget(self.btn_reveal)
        brow.addWidget(self.btn_remove)
        brow.addStretch(1)
        brow.addWidget(self.btn_apply)
        rl.addLayout(brow)

        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([380, 700])
        lay.addWidget(split)
        return w

    # ---------------------------------------------------------- onglet sauvegardes
    def _backups_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, int(S.m("space-3")), 0, 0)
        lay.setSpacing(int(S.m("space-2")))
        self.btable = QTableWidget(0, 4)
        self.btable.setHorizontalHeaderLabels([L("Date"), L("Motif"), L("Réglages CS"), L("Contenu")])
        self.btable.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.btable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.btable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.btable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.btable.verticalHeader().setVisible(False)
        lay.addWidget(self.btable, 1)
        row = QHBoxLayout()
        op = QPushButton(L("Afficher dans le Finder"))
        op.clicked.connect(lambda: self._bcur() and reveal(self._bcur().path))
        rs = QPushButton(L("Restaurer cette sauvegarde"))
        S.variant(rs, "primary")
        rs.clicked.connect(self.restore)
        row.addWidget(op)
        row.addStretch(1)
        row.addWidget(rs)
        lay.addLayout(row)
        return w

    # ---------------------------------------------------------- données
    def refresh(self, select: str | None = None):
        cur = select or (self._cur().name if self._cur() else None)
        self.presets = core.list_presets(self.cfg["library"])
        self.active = core.active_preset(self.cfg["library"])
        self.ref = core.game_reference(self.cfg["cs_dir"])
        self.compats = {p.name: core.check_preset(p.path, self.ref) for p in self.presets} if self.ref else {}
        self.list.clear()
        for p in self.presets:
            kind = f"CS {p.version}" if p.has_settings else L("post-traitement seul")
            if self.compats.get(p.name) and self.compats[p.name].level == "warning":
                kind += "  ·  " + L("⚠ incompatible en partie")
            it = QListWidgetItem(f"{'● ' if p.name == self.active else '   '}{p.name}\n      {kind}")
            self.list.addItem(it)
        idx = next((i for i, p in enumerate(self.presets) if p.name == cur), 0 if self.presets else -1)
        self.list.setCurrentRow(idx)
        if not self.presets:
            self._show(-1)
        self.backups = core.list_backups(self.cfg)
        self.btable.setRowCount(len(self.backups))
        for r, b in enumerate(self.backups):
            vals = (b.name.replace("_", " "), b.meta.get("reason", ""), b.version,
                    ", ".join(([L("réglages")] if b.has_settings else []) + b.editor +
                              ([f"{len(b.pp_files)} PP"] if b.pp_files else [])))
            for c, v in enumerate(vals):
                self.btable.setItem(r, c, QTableWidgetItem(v))
        self._game_state()

    def _cur(self):
        r = self.list.currentRow()
        return self.presets[r] if 0 <= r < len(getattr(self, "presets", [])) else None

    def _bcur(self):
        r = self.btable.currentRow()
        return self.backups[r] if 0 <= r < len(self.backups) else None

    def _show(self, _row):
        p = self._cur()
        for b in (self.btn_apply, self.btn_remove, self.btn_reveal):
            b.setEnabled(p is not None)
        self._show_compat(p)
        if not p:
            self.badges.setText("")
            self.name.setText(L("Aucun preset"))
            self.details.setText(L("Importez une archive, un dossier, ou téléchargez un preset depuis Nexus pour "
                                   "commencer. Bibliothèque : {lib}", lib=self.cfg["library"]))
            return
        self.name.setText(p.name)
        tags = []
        if p.name == self.active:
            tags.append((L("✓ Chargé"), "success"))
        tags.append((f"CS {p.version}" if p.has_settings else L("Post-traitement seul"), "accent-text"))
        if p.has_settings and p.version and not p.version.startswith("1.9"):
            tags.append((L("⚠ Réglages d'une autre version de CS"), "warning"))
        self.badges.setText("&nbsp;&nbsp;&nbsp;".join(f"<span style='color:{S.c(st)}'>{t}</span>" for t, st in tags))
        lines = []
        meta = p.meta
        if meta.get("url"):
            lines.append(f"<b>{L('Source')}</b> : <a href='{meta['url']}'>{meta.get('mod', 'Nexus')}</a>"
                         f" — {meta.get('file', '')} {meta.get('version', '')}")
        elif meta.get("source"):
            lines.append(f"<b>{L('Source')}</b> : {meta['source']}")
        if meta.get("date"):
            lines.append(f"<b>{L('Ajouté le')}</b> : {meta['date']}")
        if p.has_settings:
            lines.append(L("Remplace les réglages de Community Shaders (SettingsUser.json)."))
        if p.editor:
            lines.append(L("Données de l'éditeur CS : {list}", list=", ".join(p.editor)))
        if p.pp_files:
            lines.append(L("Post-traitement ajouté au menu CS : {list}", list=", ".join(p.pp_files)))
        self.details.setText("<br><br>".join(lines))

    def _show_compat(self, p):
        """Encart Socle (Callout) : ce que le Community Shaders installé ignorera ou complétera."""
        c = self.compats.get(p.name) if p else None
        if p is None or (c is None and self.ref is not None):
            self.compat.setVisible(False)
            return
        if c is None:
            level = "info"
            text = L("Compatibilité non vérifiée : SettingsDefault.json introuvable dans le dossier Community "
                     "Shaders du jeu. Vérifiez les réglages et que le disque est branché.")
        else:
            level = c.level
            parts = []
            if c.unknown_features:
                parts.append(L("<b>⚠ Features inconnues de votre Community Shaders {v}</b> : {list}. Elles seront "
                               "ignorées ; le rendu peut différer des captures du preset (autre variante de CS, "
                               "comme Jiaye AIO ou Open Shader ?).", v=self.ref.get("version", ""),
                               list=", ".join(c.unknown_features)))
            if c.unknown_pp:
                parts.append(L("<b>⚠ Effets de post-traitement inconnus</b> : {list}. Ils seront ignorés.",
                               list=", ".join(c.unknown_pp)))
            if c.missing_features:
                parts.append(L("<b>ⓘ Features absentes du preset</b> : {list}. Elles garderont leurs valeurs "
                               "par défaut.", list=", ".join(c.missing_features)))
            if c.unknown_options:
                parts.append(L("ⓘ {n} option(s) inconnue(s) dans des features connues : renommées ou retirées "
                               "depuis la version du preset, elles seront ignorées.", n=c.unknown_options))
            if not parts:
                parts.append(L("<b>✓ Compatible</b> : toutes les features du preset existent dans votre Community "
                               "Shaders {v}.", v=self.ref.get("version", "")))
            text = "<br>".join(parts)
        tone = {"ok": "success", "info": "info", "warning": "warning"}[level]
        r, pad = int(S.m("radius")), int(S.m("space-2"))
        self.compat.setStyleSheet(f"QLabel {{ background: {S.c(tone + '-bg')}; color: {S.c(tone + '-soft')}; "
                                  f"border: 1px solid {S.c(tone + '-border')}; border-radius: {r}px; "
                                  f"padding: {pad}px; }}")
        self.compat.setText(text)
        self.compat.setVisible(True)

    def _game_state(self):
        running = core.game_running()
        self.game.setText(L("⚠ Jeu lancé : fermez-le avant d'appliquer") if running else L("Jeu fermé"))
        S.status(self.game, "warning" if running else "success")
        self.btn_apply.setEnabled(self._cur() is not None and not running)
        return running

    def say(self, text: str):
        self.log.appendPlainText(time.strftime("%H:%M:%S  ") + text)

    # ---------------------------------------------------------- actions
    def apply(self):
        p = self._cur()
        if not p or self._game_state():
            return
        c = self.compats.get(p.name)
        if c and c.level == "warning" and QMessageBox.question(
                self, APP, L("« {name} » utilise des réglages que votre Community Shaders ne connaît pas ({list}). "
                             "Ils seront ignorés. Appliquer quand même ? La configuration en place est sauvegardée "
                             "avant.", name=p.name, list=", ".join(c.unknown_features + c.unknown_pp))) != \
                QMessageBox.StandardButton.Yes:
            return
        try:
            saved = core.apply_preset(self.cfg, p.path, p.name)
        except FileNotFoundError:
            QMessageBox.warning(self, APP, L("Dossier Community Shaders introuvable : {path}. Vérifiez les réglages "
                                             "et que le disque est branché.", path=self.cfg["cs_dir"]))
            return
        self.say(L("Preset « {name} » appliqué. Sauvegarde de l'ancienne configuration : {path}",
                   name=p.name, path=saved))
        self.refresh(p.name)

    def restore(self):
        b = self._bcur()
        if not b or self._game_state():
            return
        saved = core.apply_preset(self.cfg, b.path, None)
        (Path(self.cfg["library"]) / core.STATE).write_text(L("sauvegarde {name}", name=b.name), encoding="utf-8")
        self.say(L("Sauvegarde {name} restaurée (configuration remplacée sauvegardée dans {path}).",
                   name=b.name, path=saved))
        self.refresh()

    def save_current(self):
        name, ok = QInputDialog.getText(self, APP, L("Nom du nouveau preset :"),
                                        text=time.strftime(L("Mon réglage %Y-%m-%d")))
        if not ok or not name.strip():
            return
        try:
            dest = core.save_current(self.cfg, name.strip())
        except FileExistsError:
            QMessageBox.warning(self, APP, L("Un preset porte déjà ce nom."))
            return
        self.say(L("Configuration actuelle enregistrée : {path}", path=dest))
        self.refresh(dest.name)

    def remove(self):
        p = self._cur()
        if not p:
            return
        if QMessageBox.question(self, APP, L("Retirer « {name} » de la bibliothèque ? Il est déplacé dans le dossier "
                                             "des sauvegardes, pas effacé.", name=p.name)) != \
                QMessageBox.StandardButton.Yes:
            return
        dest = core.remove_preset(self.cfg, p.path)
        self.say(L("« {name} » déplacé dans {path}", name=p.name, path=dest))
        self.refresh()

    def _import(self, source: Path):
        name, ok = QInputDialog.getText(self, APP, L("Nom du preset :"), text=source.stem)
        if not ok or not name.strip():
            return
        try:
            made = core.import_source(self.cfg, source, name.strip())
        except LookupError:
            QMessageBox.warning(self, APP, L("Aucun preset Community Shaders trouvé dans « {src} » : il faut un "
                                             "SettingsUser.json ou un dossier PostProcessing.", src=source.name))
            return
        except (RuntimeError, ValueError) as e:
            QMessageBox.warning(self, APP, L("Impossible de lire « {src} » ({err}). Vérifiez que l'archive n'est "
                                             "pas protégée par un mot de passe.", src=source.name, err=e))
            return
        self.say(L("Importé : {names}", names=", ".join(p.name for p in made)))
        self.refresh(made[0].name)
        self._warn_imported(made)

    def _warn_imported(self, made):
        for path in made:
            c = self.compats.get(path.name)
            if c and c.level == "warning":
                self.say(L("⚠ « {name} » : features inconnues de votre Community Shaders, elles seront ignorées "
                           "({list}).", name=path.name, list=", ".join(c.unknown_features + c.unknown_pp)))

    def import_archive(self):
        f, _ = QFileDialog.getOpenFileName(self, L("Choisir une archive"), str(Path.home() / "Downloads"),
                                           "Archives (*.zip *.7z *.rar)")
        if f:
            self._import(Path(f))

    def import_folder(self):
        d = QFileDialog.getExistingDirectory(self, L("Choisir un dossier"), str(Path.home() / "Downloads"))
        if d:
            self._import(Path(d))

    def from_nexus(self):
        dlg = NexusDialog(self.cfg, self)
        dlg.exec()
        if dlg.created:
            self.say(L("Ajouté depuis Nexus : {names}", names=", ".join(p.name for p in dlg.created)))
            self.refresh(dlg.created[-1].name)
            self._warn_imported(dlg.created)

    def settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            lang_changed = dlg.cfg.get("lang") != self.cfg.get("lang")
            self.cfg = dlg.cfg
            core.save_config(self.cfg)
            Path(self.cfg["library"]).mkdir(parents=True, exist_ok=True)
            self.refresh()
            if lang_changed:
                QMessageBox.information(self, APP, L("La nouvelle langue s'appliquera au prochain lancement."))

    # glisser-déposer
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir() or p.suffix.lower() in core.ARCHIVES:
                self._import(p)


def main():
    cfg = core.load_config()
    lang = cfg.get("lang", "auto")
    i18n.set_lang(i18n.system_lang(QLocale.system().uiLanguages(), "fr") if lang == "auto" else lang)
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    S.apply(app, "dark")
    Path(cfg["library"]).mkdir(parents=True, exist_ok=True) if os.path.isdir(os.path.dirname(cfg["library"])) else None
    w = Main(cfg)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
