"""csSETTINGS : sélecteur de presets Community Shaders pour Skyrim (bouteille CrossOver).

Choisir un preset, l'appliquer en un clic (la configuration en place est sauvegardée avant),
restaurer une sauvegarde, importer une archive ou un dossier, télécharger depuis Nexus Mods.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import QLocale, QPoint, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QPixmap
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMenuBar, QMessageBox,
                             QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem,
                             QTabWidget, QVBoxLayout, QWidget)

import core
import i18n
import nexus
import socle_qt as S
import systems
import updater
from i18n import L

APP = "csSETTINGS"
WEB_DIR = core.CONFIG_FILE.parent / "web"     # cookies et cache du navigateur Nexus (la connexion est gardée)


# ------------------------------------------------------------------ utilitaires

class Worker(QThread):
    """Exécute fn(progress) hors du fil de l'interface."""
    progress = pyqtSignal(int, int)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    active = 0  # traitements en cours : la mise à jour automatique attend qu'ils finissent

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        Worker.active += 1
        try:
            self.done.emit(self.fn(lambda a, b: self.progress.emit(int(a), int(b))))
        except Exception as e:  # noqa: BLE001 — l'erreur est montrée à l'utilisateur
            self.failed.emit(f"{type(e).__name__}: {e}")
        finally:
            Worker.active -= 1


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
        for key, label in (("library", L("Bibliothèque de presets")), ("enb_library", L("Bibliothèque de presets ENB")),
                           ("systems_dir", L("Dossier des bases de systèmes (CS / ENB)")),
                           ("cs_dir", L("Dossier Community Shaders du jeu")),
                           ("backup_dir", L("Dossier des sauvegardes"))):
            row = QHBoxLayout()
            ed = QLineEdit(self.cfg.get(key, core.DEFAULTS.get(key, "")))
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

        ctl = getattr(parent, "_updater", None)
        if ctl is not None:  # section « Mises à jour » : installation automatique et vérification manuelle
            lay.addWidget(ctl.settings_widget())

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


# ------------------------------------------------------------------ À propos (modèle Socle : AboutWindow de mDESK)

class AboutDialog(QDialog):
    """Fenêtre « À propos » : icône, nom, version lue dans l'appli, description, auteurs, licence, avertissement."""
    _instance = None

    @classmethod
    def show_for(cls, parent):
        if cls._instance is None:
            cls._instance = cls(parent)
        dlg = cls._instance
        dlg.show()
        S.centrer(dlg, parent)
        dlg.raise_()
        dlg.activateWindow()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(L("À propos de {app}", app=APP))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
                            | Qt.WindowType.WindowCloseButtonHint)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(12)
        center = Qt.AlignmentFlag.AlignHCenter

        icon = QLabel()
        pix = QPixmap(str(Path(__file__).resolve().parent.parent / "assets" / "icon.png"))
        if pix.isNull():
            pix = QPixmap(str(Path(sys.executable).resolve().parent.parent / "Resources" / "icon.icns"))
        if not pix.isNull():
            icon.setPixmap(pix.scaled(84, 84, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.setAlignment(center)
        lay.addWidget(icon)

        info = updater.bundle_info(updater.app_path())
        ver, build = info.get("CFBundleShortVersionString"), info.get("CFBundleVersion")
        name = QLabel(APP)
        name.setStyleSheet("font-size: 17px; font-weight: 700;")
        version = QLabel(L("Version {v} ({b})", v=ver, b=build) if ver else L("Version de développement"))
        S.role(version, "muted")
        head = QVBoxLayout()
        head.setSpacing(6)
        for w in (name, version):
            w.setAlignment(center)
            head.addWidget(w)
        lay.addLayout(head)
        lay.addSpacing(6)  # 18 px entre la version et la description

        texts = [(L("Sélecteur de presets Community Shaders pour Skyrim sur Mac (CrossOver) : parcourir, appliquer, "
                    "sauvegarder et restaurer."), None),
                 ("Starbudweiser & Claude Code (Anthropic)", "bold"),
                 (L("Licence MIT. © 2026 Starbudweiser."), None),
                 (L("Fourni en l'état, sans garantie. Sans lien avec les auteurs de Community Shaders ni avec Nexus Mods."),
                  "muted")]
        for text, kind in texts:
            lab = QLabel(text)
            lab.setWordWrap(True)
            lab.setFixedWidth(300)
            lab.setAlignment(center)
            if kind == "bold":
                lab.setStyleSheet("font-weight: 700;")
            elif kind == "muted":
                S.role(lab, "muted")
            lay.addWidget(lab, 0, center)
        self.setFixedWidth(356)
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())


# ------------------------------------------------------------------ Nexus

class NexusDialog(QDialog):
    def __init__(self, cfg: dict, parent=None, url: str = ""):
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
        if url:
            self.url.setText(url)
            QTimer.singleShot(0, self._search)

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
            with tempfile.TemporaryDirectory(prefix="cssettings_dl_") as tmp:
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


# ------------------------------------------------------------------ navigateur Nexus

class NexusPage(QWebEnginePage):
    """Page qui détourne les liens nxm:// (bouton « Mod manager download ») et garde les fenêtres
    surgissantes (connexion) dans la même vue."""
    nxm = pyqtSignal(str)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.scheme() == "nxm":
            self.nxm.emit(url.toString())
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def createWindow(self, _type):
        return self

    def javaScriptConsoleMessage(self, *_args):    # messages des scripts du site : sans intérêt ici
        pass


class NexusBrowser(QWidget):
    """Onglet Nexus : un petit navigateur ouvert sur une recherche de presets. Un téléchargement lancé
    depuis le site (manuel ou « Mod manager download ») est importé dans la bibliothèque."""
    imported = pyqtSignal(list)

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.worker = None
        self.loaded = False
        self.tmp = tempfile.TemporaryDirectory(prefix="cssettings_web_")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, int(S.m("space-3")), 0, 0)
        lay.setSpacing(int(S.m("space-2")))

        bar = QHBoxLayout()
        bar.setSpacing(int(S.m("space-2")))
        self.back, self.fwd, self.reload = (QPushButton(t) for t in ("←", "→", "⟳"))
        for b, tip in ((self.back, L("Page précédente")), (self.fwd, L("Page suivante")),
                       (self.reload, L("Recharger"))):
            S.variant(b, "tertiary")
            b.setStyleSheet("font-size: 16px;")       # la feuille Socle impose 12px : flèches illisibles
            b.setToolTip(tip)
            b.setFixedWidth(int(S.m("size-control")))
            bar.addWidget(b)
        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.addItems(nexus.SEARCHES)
        self.search.setMinimumWidth(260)
        self.search.lineEdit().setPlaceholderText(L("Rechercher sur Nexus"))
        self.search.lineEdit().returnPressed.connect(self.go_search)
        self.search.activated.connect(lambda _i: self.go_search())
        go = QPushButton(L("Rechercher"))
        go.clicked.connect(self.go_search)
        self.addr = QLabel("")
        S.role(self.addr, "path")
        self.addr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        ext = QPushButton(L("Ouvrir dans le navigateur"))
        S.variant(ext, "tertiary")
        ext.clicked.connect(lambda: QDesktopServices.openUrl(self.view.url()))
        bar.addWidget(self.search)
        bar.addWidget(go)
        bar.addWidget(self.addr, 1)
        bar.addWidget(ext)
        lay.addLayout(bar)

        WEB_DIR.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile("csSETTINGS", self)
        self.profile.setPersistentStoragePath(str(WEB_DIR))
        self.profile.setCachePath(str(WEB_DIR / "cache"))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        # agent Chrome standard : la mention QtWebEngine fait parfois bloquer la page par Cloudflare
        ua = self.profile.httpUserAgent()
        self.profile.setHttpUserAgent(" ".join(w for w in ua.split() if not w.startswith("QtWebEngine")))
        self.profile.downloadRequested.connect(self._download)
        self.page = NexusPage(self.profile, self)
        self.page.nxm.connect(self._nxm)
        self.view = QWebEngineView()
        self.view.setPage(self.page)
        self.view.setZoomFactor(S.scale())      # même échelle que l'interface (Socle, 110 %)
        self.view.urlChanged.connect(self._url)
        self.view.loadFinished.connect(lambda _ok: self._nav_state())
        self.back.clicked.connect(self.view.back)
        self.fwd.clicked.connect(self.view.forward)
        self.reload.clicked.connect(self.view.reload)
        lay.addWidget(self.view, 1)

        # barre contextuelle : ce qui se passe et l'action possible sur la page en cours
        foot = QHBoxLayout()
        foot.setSpacing(int(S.m("space-2")))
        self.state = QLabel(L("Ouvrez la page d'un preset, puis cliquez sur « Mod manager download » ou sur un "
                              "téléchargement manuel : le fichier est ajouté à la bibliothèque. Aucun réglage du jeu "
                              "n'est modifié."))
        self.state.setWordWrap(True)
        S.role(self.state, "meta")
        self.bar = QProgressBar()
        self.bar.setVisible(False)
        self.bar.setFixedWidth(180)
        self.pick = QPushButton(L("Choisir un fichier de ce mod…"))
        S.variant(self.pick, "primary")
        self.pick.setVisible(False)
        self.pick.clicked.connect(lambda: self.main.from_nexus(self.view.url().toString()))
        foot.addWidget(self.state, 1)
        foot.addWidget(self.bar)
        foot.addWidget(self.pick)
        lay.addLayout(foot)

    def shutdown(self):
        """Libère la page avant son profil (sinon Qt WebEngine se plaint à la fermeture)."""
        self.view.setPage(None)
        self.page.setParent(None)
        self.page.deleteLater()

    def showEvent(self, e):
        super().showEvent(e)
        if not self.loaded:            # la page ne se charge qu'à la première ouverture de l'onglet
            self.loaded = True
            self.go_search()

    def go_search(self):
        text = self.search.currentText().strip() or nexus.SEARCHES[0]
        if text.startswith(("http://", "https://")):
            self.view.load(QUrl(text))
        else:
            self.view.load(QUrl(nexus.search_url(text)))

    def _url(self, url: QUrl):
        self.addr.setText(url.toString())
        # page d'un mod (…/mods/<numéro>) : on propose de choisir un de ses fichiers
        self.pick.setVisible(bool(re.search(r"/mods/\d+", url.path())))
        self._nav_state()

    def _nav_state(self):
        h = self.view.history()
        self.back.setEnabled(h.canGoBack())
        self.fwd.setEnabled(h.canGoForward())

    def _mod_name(self) -> str:
        title = self.view.title()
        for sep in (" at Skyrim", " - Nexus", " | Nexus"):
            title = title.split(sep)[0]
        return title.strip() or "Nexus"

    def _say(self, text: str, status: str = "none"):
        self.state.setText(text)
        S.status(self.state, status)

    # téléchargement manuel depuis le site
    def _download(self, req: QWebEngineDownloadRequest):
        name = req.downloadFileName()
        if Path(name).suffix.lower() not in core.ARCHIVES:
            req.cancel()
            self._say(L("« {f} » n'est pas une archive .ZIP, .7Z ou .RAR : téléchargement ignoré.", f=name), "warning")
            return
        req.setDownloadDirectory(self.tmp.name)
        page_url, mod = self.view.url().toString(), self._mod_name()
        req.receivedBytesChanged.connect(lambda: self._progress(req.receivedBytes(), req.totalBytes()))
        req.isFinishedChanged.connect(lambda: self._downloaded(req, mod, page_url))
        req.accept()
        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self._say(L("Téléchargement de {f}…", f=name))

    def _progress(self, got, total):
        if total > 0:
            self.bar.setRange(0, total)
            self.bar.setValue(got)

    def _downloaded(self, req, mod, page_url):
        if req.state() != QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.bar.setVisible(False)
            self._say(L("Téléchargement interrompu."), "danger")
            return
        path = Path(req.downloadDirectory()) / req.downloadFileName()
        meta = {"source": "Nexus Mods", "mod": mod, "file": path.name, "url": page_url}
        try:
            meta["nexus_id"] = nexus.parse_mod_id(page_url)
        except ValueError:
            pass
        name = core.safe_name(f"{mod} - {path.stem}")[:90]
        cfg = self.main.cfg
        self._run(lambda _p: core.import_source(cfg, path, name, meta))

    # « Mod manager download » : lien nxm:// traité par l'API
    def _nxm(self, link: str):
        try:
            info = nexus.parse_nxm(link)
        except ValueError:
            self._say(L("Lien de téléchargement non reconnu."), "danger")
            return
        if info["game"] != nexus.GAME:
            self._say(L("Ce fichier n'est pas pour Skyrim Special Edition."), "warning")
            return
        key = nexus.get_key()
        if not key:
            self._say(L("Ajoutez d'abord votre clé d'API Nexus dans les réglages."), "warning")
            return
        mid, fid, cfg = info["mod_id"], info["file_id"], self.main.cfg

        def job(progress):
            mod, f = nexus.mod_info(mid, key), nexus.file_info(mid, fid, key)
            f.setdefault("file_id", fid)
            name = core.safe_name(f"{mod.get('name', 'Nexus')} - {f.get('name', '')}")[:90]
            meta = {"source": "Nexus Mods", "nexus_id": mid, "mod": mod.get("name"), "author": mod.get("author"),
                    "file": f.get("name"), "version": f.get("version"),
                    "url": f"https://www.nexusmods.com/{nexus.GAME}/mods/{mid}"}
            with tempfile.TemporaryDirectory(prefix="cssettings_dl_") as tmp:
                path = nexus.download(mid, f, key, Path(tmp), progress, nxm=info)
                return core.import_source(cfg, path, name, meta)

        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self._say(L("Téléchargement depuis Nexus…"))
        self._run(job)

    def _run(self, fn):
        self.worker = Worker(fn)
        self.worker.progress.connect(self._progress)
        self.worker.done.connect(self._imported)
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _imported(self, made):
        self.bar.setVisible(False)
        self._say(L("✓ Ajouté à la bibliothèque : {names}", names=", ".join(p.name for p in made)), "success")
        self.imported.emit(made)

    def _fail(self, err):
        self.bar.setVisible(False)
        if "LookupError" in err:
            msg = L("L'archive ne contient ni SettingsUser.json ni fichier PostProcessing : ce n'est pas un preset "
                    "Community Shaders (preset ReShade ou ENB ?).")
        else:
            msg = L("Échec : {err}", err=err)
        self._say(msg, "danger")


# ------------------------------------------------------------------ fenêtre principale

class Main(QWidget):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.sysname = None                 # système de shaders actif : CS, ENB ou None (non géré)
        self.sys_modes, self.bases, self.sys_ops = {}, {}, []
        self.enb_presets, self.enb_active = [], ""
        self.setWindowTitle(APP)
        self.setAcceptDrops(True)
        self.resize(1100, 680)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # en-tête
        bar = QWidget()
        bar.setObjectName("header")
        bar.setMinimumHeight(int(S.m("size-bar")))
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
        self.tabs.addTab(self._enb_tab(), L("Presets ENB"))
        self.tabs.addTab(self._system_tab(), L("Système"))
        self.tabs.addTab(self._backups_tab(), L("Sauvegardes"))
        self.browser = NexusBrowser(self)
        self.browser.imported.connect(self._web_imported)
        self.tabs.addTab(self.browser, L("Nexus"))
        self.tabs.setCurrentIndex(int(cfg.get("tab", 0)) % self.tabs.count())   # dernier onglet ouvert
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
        hint = QLabel(L("Vous pouvez aussi glisser-déposer une archive ou un dossier sur la fenêtre."))
        S.role(hint, "subtle")
        hint.setWordWrap(True)
        ll.addWidget(hint)
        row = QHBoxLayout()
        row.setSpacing(int(S.m("space-2")))
        imp = QPushButton(L("Importer…"))
        menu = QMenu(imp)
        menu.addAction(L("Une archive (.ZIP, .7Z, .RAR)…"), self.import_archive)
        menu.addAction(L("Un dossier…"), self.import_folder)
        # menu ouvert à la main : pas d'indicateur de menu Qt, qui décentrait le libellé
        imp.clicked.connect(lambda: menu.exec(imp.mapToGlobal(QPoint(0, imp.height() + 2))))
        nx = QPushButton(L("Depuis Nexus…"))
        nx.clicked.connect(lambda: self.tabs.setCurrentWidget(self.browser))
        save = QPushButton(L("Enregistrer la config actuelle…"))
        save.clicked.connect(self.save_current)
        row.addWidget(imp)
        row.addWidget(nx)
        row.addWidget(save)
        row.addStretch(1)
        ll.addLayout(row)

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
        self.cs_note = QLabel(L("Le système ENB est actif : les presets Community Shaders ne s'appliquent pas. "
                                "Passez à Community Shaders dans l'onglet Système."))
        self.cs_note.setWordWrap(True)
        self._tone(self.cs_note, "warning")
        self.cs_note.setVisible(False)
        rl.addWidget(self.name)
        rl.addWidget(self.badges)
        rl.addWidget(self.cs_note)
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
        self.btn_apply.clicked.connect(self.apply)
        brow.setSpacing(int(S.m("space-2")))
        # les deux rangées du bas ont la même hauteur (size-control-lg) et finissent à la même ligne ;
        # le bouton ambre reste le seul en couleur, sans la hauteur « barre latérale » (size-cta) de Socle
        h = int(S.m("size-control-lg")) - 2
        for b in (imp, nx, save, self.btn_reveal, self.btn_remove, self.btn_apply):
            b.setStyleSheet(f"QPushButton {{ min-height: {h}px; max-height: {h}px; }}")
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

    # ---------------------------------------------------------- onglet presets ENB
    def _tone(self, label: QLabel, tone: str):
        """Encart Socle (Callout) sur un QLabel : success, info ou warning."""
        r, pad = int(S.m("radius")), int(S.m("space-2"))
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet(f"QLabel {{ background: {S.c('surface-raised' if tone == 'info' else tone + '-bg')}; color: {S.c(tone + '-soft')}; "
                            f"border: 1px solid {S.c(tone + '-border')}; border-radius: {r}px; padding: {pad}px; }}")

    def _enb_tab(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, int(S.m("space-3")), 0, 0)
        split = QSplitter()
        split.setHandleWidth(8)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(int(S.m("space-2")))
        self.enb_list = QListWidget()
        self.enb_list.currentRowChanged.connect(self._enb_show)
        self.enb_list.itemDoubleClicked.connect(lambda _i: self.apply_enb())
        ll.addWidget(self.enb_list, 1)
        self.enb_hint = QLabel("")
        S.role(self.enb_hint, "subtle")
        self.enb_hint.setWordWrap(True)
        ll.addWidget(self.enb_hint)
        save = QPushButton(L("Enregistrer l'ENB actuel…"))
        save.clicked.connect(self.save_enb)
        ll.addWidget(save, 0, Qt.AlignmentFlag.AlignLeft)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(int(S.m("space-3")), 0, 0, 0)
        rl.setSpacing(int(S.m("space-3")))
        self.enb_name = QLabel("")
        S.role(self.enb_name, "heading")
        self.enb_name.setWordWrap(True)
        self.enb_note = QLabel(L("Le système ENB n'est pas actif : passez-y depuis l'onglet Système pour appliquer "
                                 "un preset ENB."))
        self.enb_note.setWordWrap(True)
        self._tone(self.enb_note, "warning")
        self.enb_details = QLabel("")
        self.enb_details.setWordWrap(True)
        self.enb_details.setTextFormat(Qt.TextFormat.RichText)
        self.enb_details.setAlignment(Qt.AlignmentFlag.AlignTop)
        reassure = QLabel(L("Avant chaque application, enbseries.ini et le dossier enbseries en place sont déplacés "
                            "dans la sauvegarde, rien n'est effacé, sauf le cache enbcache de la racine du jeu, "
                            "supprimé pour que le nouveau preset soit recompilé. Aucun fichier du preset n'est modifié."))
        reassure.setWordWrap(True)
        S.role(reassure, "subtle")
        rl.addWidget(self.enb_name)
        rl.addWidget(self.enb_note)
        rl.addWidget(self.enb_details, 1)
        rl.addWidget(reassure)
        brow = QHBoxLayout()
        self.btn_enb_reveal = QPushButton(L("Afficher dans le Finder"))
        S.variant(self.btn_enb_reveal, "tertiary")
        self.btn_enb_reveal.clicked.connect(lambda: self._enb_cur() and reveal(self._enb_cur().path))
        self.btn_enb_apply = QPushButton(L("Appliquer ce preset ENB"))
        S.variant(self.btn_enb_apply, "action")
        self.btn_enb_apply.clicked.connect(self.apply_enb)
        h = int(S.m("size-control-lg")) - 2
        for b in (save, self.btn_enb_reveal, self.btn_enb_apply):
            b.setStyleSheet(f"QPushButton {{ min-height: {h}px; max-height: {h}px; }}")
        brow.addWidget(self.btn_enb_reveal)
        brow.addStretch(1)
        brow.addWidget(self.btn_enb_apply)
        rl.addLayout(brow)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([380, 700])
        lay.addWidget(split)
        return w

    def _enb_cur(self):
        r = self.enb_list.currentRow()
        return self.enb_presets[r] if 0 <= r < len(getattr(self, "enb_presets", [])) else None

    def _enb_show(self, _row):
        p = self._enb_cur()
        self.btn_enb_reveal.setEnabled(p is not None)
        if not p:
            self.enb_name.setText(L("Aucun preset ENB"))
            self.enb_details.setText(L("Rangez vos presets ENB (un dossier avec enbseries.ini et enbseries/) dans : "
                                       "{lib}", lib=self.cfg.get("enb_library", "")))
            self._update_buttons()
            return
        self.enb_name.setText(p.name)
        lines = []
        if p.name == self.enb_active:
            lines.append(f"<span style='color:{S.c('success')}'>{L('✓ Chargé')}</span>")
        if p.meta.get("source"):
            lines.append(f"<b>{L('Source')}</b> : {p.meta['source']}")
        if p.meta.get("date"):
            lines.append(f"<b>{L('Ajouté le')}</b> : {p.meta['date']}")
        src = core.enb_source(p.path)
        lines.append(L("Remplace enbseries.ini et le dossier enbseries à la racine du jeu ({n} effets).",
                       n=len(p.pp_files)))
        if (src / "enblocal.ini").is_file():
            lines.append(L("enblocal.ini du preset non appliqué : il règle la machine, pas le rendu."))
        self.enb_details.setText("<br><br>".join(lines))
        self._update_buttons()

    def apply_enb(self):
        p = self._enb_cur()
        if not p or self._game_state() or self.sysname != systems.ENB:
            return
        try:
            saved = core.apply_enb_preset(self.cfg, p.path, p.name)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, APP, L("Impossible d'appliquer « {name} » ({err}).", name=p.name, err=e))
            return
        self.say(L("Preset ENB appliqué : {name}. Ancienne config sauvegardée dans {saved}", name=p.name,
                   saved=saved.name))
        self.refresh()

    def save_enb(self):
        name, ok = QInputDialog.getText(self, APP, L("Nom du preset ENB à enregistrer :"))
        if not ok or not name.strip():
            return
        try:
            dest = core.save_current_enb(self.cfg, name.strip())
        except FileExistsError:
            QMessageBox.warning(self, APP, L("Un preset ENB porte déjà ce nom."))
            return
        except OSError:
            QMessageBox.warning(self, APP, L("Aucun enbseries.ini à la racine du jeu : rien à enregistrer."))
            return
        self.say(L("Preset ENB enregistré : {name}", name=dest.name))
        self.refresh()

    # ---------------------------------------------------------- onglet système
    def _system_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, int(S.m("space-3")), 0, 0)
        lay.setSpacing(int(S.m("space-3")))
        self.sys_status = QLabel("")
        self.sys_status.setWordWrap(True)
        self.sys_status.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.sys_status)
        intro = QLabel(L("Un système de shaders à la fois : Community Shaders (Bottled) ou ENB. Chaque système a une "
                         "base neutre ; passer de l'un à l'autre retire proprement l'ancien (ce que vous avez modifié "
                         "est mis de côté, jamais perdu) et pose le nouveau. Les pièces communes (KiLoader…) restent."))
        intro.setWordWrap(True)
        S.role(intro, "subtle")
        lay.addWidget(intro)
        row = QHBoxLayout()
        row.setSpacing(int(S.m("space-2")))
        self.btn_sys = {}
        for name, label in ((systems.CS, "Community Shaders"), (systems.ENB, "ENB")):
            b = QPushButton(label)
            S.variant(b, "primary")
            b.clicked.connect(lambda _=False, n=name: self._sys_go(n))
            self.btn_sys[name] = b
            row.addWidget(b)
        self.btn_sys_off = QPushButton(L("Retirer le système"))
        S.variant(self.btn_sys_off, "tertiary")
        self.btn_sys_off.clicked.connect(self._sys_remove)
        row.addWidget(self.btn_sys_off)
        row.addStretch(1)
        lay.addLayout(row)
        self.sys_bases = QLabel("")
        self.sys_bases.setWordWrap(True)
        self.sys_bases.setTextFormat(Qt.TextFormat.RichText)
        S.role(self.sys_bases, "meta")
        lay.addWidget(self.sys_bases)
        brow = QHBoxLayout()
        rebuild = QPushButton(L("Reconstruire les bases…"))
        S.variant(rebuild, "tertiary")
        rebuild.clicked.connect(self._sys_rebuild)
        self.btn_rebuild = rebuild
        bases = QPushButton(L("Afficher les bases"))
        S.variant(bases, "tertiary")
        bases.clicked.connect(lambda: reveal(self.cfg.get("systems_dir", core.DEFAULTS["systems_dir"])))
        brow.addWidget(rebuild)
        brow.addWidget(bases)
        brow.addStretch(1)
        lay.addLayout(brow)
        title = QLabel(L("Historique des échanges"))
        S.role(title, "heading")
        lay.addWidget(title)
        self.sys_table = QTableWidget(0, 4)
        self.sys_table.setHorizontalHeaderLabels([L("Date"), L("Opération"), L("Couche"), L("État")])
        self.sys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sys_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sys_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.sys_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.sys_table.verticalHeader().setVisible(False)
        lay.addWidget(self.sys_table, 1)
        orow = QHBoxLayout()
        reveal_op = QPushButton(L("Afficher la sauvegarde dans le Finder"))
        reveal_op.clicked.connect(self._sys_reveal)
        orow.addWidget(reveal_op)
        orow.addStretch(1)
        lay.addLayout(orow)
        self._sys_busy = False
        self._sys_worker = None
        return w

    @property
    def game_root(self) -> Path:
        return core.game_dir(self.cfg["cs_dir"])

    @property
    def broot(self) -> Path:
        return systems.backup_root(self.cfg["backup_dir"])

    def refresh_system(self):
        game = self.game_root
        self.sysname = systems.active_system(game) if game.is_dir() else None
        self.bases = systems.available_bases(self.cfg.get("systems_dir", core.DEFAULTS["systems_dir"]))
        names = {systems.CS: "Community Shaders", systems.ENB: "ENB"}
        lines, tone = [], "info"
        if not game.is_dir():
            lines.append(L("<b>⚠ Dossier du jeu introuvable</b> : {path}. Vérifiez les réglages et que le disque est "
                           "branché.", path=game))
            tone = "warning"
        else:
            if self.sysname:
                lines.append(L("<b>Système actif</b> : {name}", name=names[self.sysname]))
                tone = "success"
            else:
                lines.append(L("<b>Aucun système géré par csSETTINGS</b> : l'installation actuelle n'est pas encore "
                               "suivie. Reprenez-la ou choisissez un système ci-dessous."))
            problems = systems.prerequis(game)
            if problems:
                tone = "warning"
                lines.append("<b>⚠</b> " + " ; ".join(problems))
            else:
                lines.append(L("Skyrim {v} détecté, SKSE présent.", v=systems.game_version(game)))
            backend = core.bottle_backend(game)
            want = core.BACKEND_FOR.get(self.sysname or "")
            if backend and want and backend != want:
                tone = "warning"
                if self.sysname == systems.ENB:
                    lines.append(L("<b>⚠ Backend graphique : {b}</b>. ENB rend correctement sous DXVK ; sous DXMT, "
                                   "la teinte est faussée (dominante verte). Dans CrossOver : bouteille › Réglages "
                                   "avancés › Graphismes › DXVK.", b=backend.upper()))
                else:
                    lines.append(L("<b>⚠ Backend graphique : {b}</b>. Community Shaders (Bottled) a besoin de DXMT : "
                                   "sans lui, pas de pont DLSS → MetalFX. Dans CrossOver : bouteille › Réglages "
                                   "avancés › Graphismes › DXMT.", b=backend.upper()))
            elif backend:
                lines.append(L("Backend graphique : {b}.", b=backend.upper()))
            for layer in systems.installed(game):
                try:
                    v = systems.verify(game, layer)
                except systems.SystemError_:
                    continue
                state = L("intact") if not (v["absents"] or v["modifiés"]) else \
                    L("{m} modifié(s), {a} absent(s) depuis la pose", m=len(v["modifiés"]), a=len(v["absents"]))
                lines.append(f"• {layer} : {state}")
        self.sys_status.setText("<br>".join(lines))
        self._tone(self.sys_status, tone)

        self.sys_modes = {}
        for name, b in self.btn_sys.items():
            if name not in self.bases:
                self.sys_modes[name] = "absent"
                b.setText(L("{name} : base absente", name=names[name]))
            elif self.sysname == name:
                self.sys_modes[name] = "actif"
                b.setText(L("✓ {name} (actif)", name=names[name]))
            elif self.sysname is None and game.is_dir() and systems.adoptable(game, self.bases[name]):
                self.sys_modes[name] = "adopt"
                b.setText(L("Reprendre l'installation actuelle ({name})", name=names[name]))
            else:
                self.sys_modes[name] = "swap"
                b.setText(L("Passer à {name}", name=names[name]) if self.sysname
                          else L("Installer {name}", name=names[name]))
        if self.bases:
            info = []
            for n, d in self.bases.items():
                try:
                    j = json.loads((d / systems.INFO).read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    j = {}
                info.append(L("<b>{name}</b> : {n} fichiers, construite le {date}", name=n, n=j.get("fichiers", "?"),
                              date=j.get("date", "?")))
            self.sys_bases.setText("<br>".join(info))
        else:
            self.sys_bases.setText(L("Aucune base neutre construite : cliquez sur « Reconstruire les bases… »."))

        ops = systems.list_operations(self.broot)
        kinds = {"install": L("Installation"), "remove": L("Retrait")}
        self.sys_ops = ops
        self.sys_table.setRowCount(len(ops))
        for r, o in enumerate(ops):
            vals = (o["name"].split("_install_")[0].split("_remove_")[0].replace("_", " "),
                    kinds.get(o["type"], o["type"]), o["layer"], o["status"])
            for c, v in enumerate(vals):
                self.sys_table.setItem(r, c, QTableWidgetItem(v))

    def _update_buttons(self):
        """Active ou grise les boutons selon le jeu (lancé ?), le système actif et l'opération en cours."""
        running = core.game_running()
        busy = getattr(self, "_sys_busy", False)
        sysname = getattr(self, "sysname", None)
        self.btn_apply.setEnabled(self._cur() is not None and not running and sysname != systems.ENB and not busy)
        self.cs_note.setVisible(sysname == systems.ENB)
        self.btn_enb_apply.setEnabled(self._enb_cur() is not None and not running and sysname == systems.ENB
                                      and not busy)
        self.enb_note.setVisible(sysname != systems.ENB)
        for name, b in self.btn_sys.items():
            b.setEnabled(self.sys_modes.get(name) in ("swap", "adopt") and not busy)
        self.btn_sys_off.setEnabled(sysname is not None and not busy)
        self.btn_rebuild.setEnabled(not busy)

    def _sys_run(self, fn, done_text, then=None):
        """Lance une opération longue hors du fil de l'interface, une seule à la fois."""
        self._sys_busy = True
        self._update_buttons()
        self.say(L("Opération en cours… ne fermez pas l'application ni le disque."))
        wk = Worker(fn)
        self._sys_worker = wk

        def finished(res):
            self._sys_busy = False
            if then:
                then(res)
            else:
                self.say(done_text)
                self.refresh()
            self._update_buttons()

        def failed(err):
            self._sys_busy = False
            self.say(L("✕ {err}", err=err))
            QMessageBox.warning(self, APP, L("L'opération a échoué : {err}. Le jeu a été remis dans son état d'avant "
                                             "si l'échec est survenu en cours de route ; les sauvegardes sont dans "
                                             "{dir}.", err=err, dir=self.broot))
            self.refresh()
            self._update_buttons()

        wk.done.connect(finished)
        wk.failed.connect(failed)
        wk.start()

    def _sys_guard(self):
        """Fonction « le jeu tourne-t-il ? » à donner au moteur, ou None si l'utilisateur annule. Si un processus
        ressemble au jeu, il est montré et l'utilisateur peut affirmer que le jeu est fermé (seul CrossOver ouvert)."""
        procs = core.game_processes()
        if not procs:
            return core.game_running
        if QMessageBox.question(self, APP, L("Un processus ressemble au jeu : {proc}. Si Skyrim est bien fermé (seul "
                                             "CrossOver est ouvert), continuer quand même ?",
                                             proc=procs[0][1])) != QMessageBox.StandardButton.Yes:
            return None
        return lambda: False

    def _sys_go(self, target: str):
        mode = self.sys_modes.get(target)
        if mode not in ("swap", "adopt") or self._sys_busy:
            return
        running = self._sys_guard()
        if running is None:
            return
        game, bases, cur, broot = self.game_root, self.bases, self.sysname, self.broot
        names = {systems.CS: "Community Shaders", systems.ENB: "ENB"}

        def plan(_p):
            return systems.plan_swap(game, cur, target, bases[target])

        def confirm(pl):
            if mode == "adopt":
                text = L("Reprendre l'installation actuelle comme « {name} » : {n} fichiers identiques à la base seront "
                         "suivis (rien n'est recopié ni modifié). Ils seront retirés avec ce système lors d'un échange.",
                         name=names[target], n=pl["identiques"])
            else:
                text = L("Passer à « {name} » ?\n\n• {r} fichier(s) de l'ancien système retirés, dont {a} modifiés "
                         "depuis la pose (mis de côté dans la sauvegarde)\n• {add} fichier(s) ajoutés, {rep} remplacés "
                         "(originaux sauvegardés)\n\nSauvegardes : {dir}", name=names[target], r=pl["retire"],
                         a=len(pl["mis_de_côté"]), add=pl["ajoute"], rep=pl["remplace"], dir=broot)
            if QMessageBox.question(self, APP, text) != QMessageBox.StandardButton.Yes:
                self._update_buttons()
                return

            def job(_p):
                if mode == "adopt":
                    ops = []
                    if systems.COMMUN in bases and systems.COMMUN not in systems.installed(game):
                        ops.append(systems.install(game, systems.COMMUN, bases[systems.COMMUN], broot,
                                                   is_running=running, adopt=True))
                    ops.append(systems.install(game, target, bases[target], broot, is_running=running, adopt=True))
                    return ops
                return systems.swap(game, cur, target, bases, broot, is_running=running)

            self._sys_run(job, L("Système « {name} » en place. Sauvegardes : {dir}", name=names[target], dir=broot))

        self._sys_run(plan, "", then=confirm)

    def _sys_remove(self):
        cur = self.sysname
        if not cur or self._sys_busy:
            return
        running = self._sys_guard()
        if running is None:
            return
        if QMessageBox.question(self, APP, L("Retirer le système « {name} » ? Ce que vous avez modifié est mis de côté "
                                             "dans la sauvegarde et les fichiers d'origine remplacés sont remis. Sans "
                                             "système, le jeu n'aura plus de shaders de rendu.", name=cur)) != \
                QMessageBox.StandardButton.Yes:
            return
        game, broot = self.game_root, self.broot
        self._sys_run(lambda _p: systems.remove(game, cur, broot, is_running=running),
                      L("Système « {name} » retiré. Sauvegardes : {dir}", name=cur, dir=broot))

    def _sys_rebuild(self):
        if self._sys_busy:
            return
        root = Path(self.cfg.get("systems_dir", core.DEFAULTS["systems_dir"]))
        shaders = root.parent
        if QMessageBox.question(self, APP, L("Reconstruire les bases neutres à partir de {src} ? Les bases actuelles "
                                             "sont mises de côté (dossier _anciennes), jamais supprimées.",
                                             src=shaders)) != QMessageBox.StandardButton.Yes:
            return

        def job(_p):
            stamp = time.strftime("%Y-%m-%d_%H%M%S")
            made = {}
            recipes = systems.recettes(shaders)
            for n, srcs in recipes.items():                      # tout vérifier avant de déplacer quoi que ce soit
                for s in srcs:
                    if not s.path.is_dir():
                        raise systems.SystemError_(L("Paquet introuvable : {path}", path=s.path))
            root.mkdir(parents=True, exist_ok=True)
            for n, srcs in recipes.items():
                if (root / n).exists():
                    (root / "_anciennes").mkdir(exist_ok=True)
                    (root / n).rename(root / "_anciennes" / f"{stamp}_{n}")
                made[n] = systems.assemble(root / n, srcs, n)
            return made

        self._sys_run(job, "", then=lambda made: (self.say(L("Bases reconstruites : {list}", list=", ".join(
            f"{n} ({c})" for n, c in made.items()))), self.refresh()))

    def _sys_reveal(self):
        r = self.sys_table.currentRow()
        if 0 <= r < len(self.sys_ops):
            reveal(self.sys_ops[r]["path"])

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
        self.refresh_enb()
        self.refresh_system()
        self.backups = core.list_backups(self.cfg)
        self.btable.setRowCount(len(self.backups))
        for r, b in enumerate(self.backups):
            vals = (b.name.replace("_", " "), b.meta.get("reason", ""), b.version,
                    ", ".join(([L("réglages")] if b.has_settings else []) + b.editor +
                              ([f"{len(b.pp_files)} PP"] if b.pp_files else []) + (["ENB"] if b.has_enb else [])))
            for c, v in enumerate(vals):
                self.btable.setItem(r, c, QTableWidgetItem(v))
        self._game_state()

    def refresh_enb(self):
        cur = self._enb_cur().name if self._enb_cur() else None
        lib = self.cfg.get("enb_library", core.DEFAULTS["enb_library"])
        self.enb_presets = core.list_enb_presets(lib)
        self.enb_active = core.active_preset(lib)
        self.enb_list.clear()
        for p in self.enb_presets:
            self.enb_list.addItem(QListWidgetItem(f"{'● ' if p.name == self.enb_active else '   '}{p.name}"))
        self.enb_hint.setText(L("Bibliothèque : {lib}", lib=lib))
        idx = next((i for i, p in enumerate(self.enb_presets) if p.name == cur), 0 if self.enb_presets else -1)
        self.enb_list.setCurrentRow(idx)
        if not self.enb_presets:
            self._enb_show(-1)

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
        self._update_buttons()
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
        if p.has_enb:
            tags.append((L("+ ENB"), "accent-text"))
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
        if p.has_enb:
            lines.append(L("<b>Preset ENB (Effects 11)</b> : remplace enbseries.ini et le dossier enbseries à la "
                           "racine du jeu. Ceux en place sont déplacés dans la sauvegarde, rien n'est effacé."))
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
            if c.frame_gen:
                parts.append(L("<b>⚠ Frame Generation forcée</b> : le preset l'active, et sous CrossOver elle fait "
                               "planter le jeu au lancement. Désactivez-la en jeu (Upscaling) ou dans le "
                               "SettingsUser.json du preset (frameGenerationForceEnable à 0)."))
            if c.pp_rejected:
                parts.append(L("<b>⚠ Post-traitement du preset ignoré</b> : votre Community Shaders {v} rejettera "
                               "sa chaîne de post-traitement ({why}) et la remplacera par une chaîne vide. Ni "
                               "l'étalonnage ni les effets du preset ne seront rendus : refaites la chaîne en jeu "
                               "ou prenez une version du preset faite pour CS {v}.", v=self.ref.get("version", ""),
                               why=self._pp_why(c)))
            elif c.unknown_pp:
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
        self.compat.setStyleSheet(f"QLabel {{ background: {S.c('surface-raised' if tone == 'info' else tone + '-bg')}; color: {S.c(tone + '-soft')}; "
                                  f"border: 1px solid {S.c(tone + '-border')}; border-radius: {r}px; "
                                  f"padding: {pad}px; }}")
        self.compat.setText(text)
        self.compat.setVisible(True)

    @staticmethod
    def _pp_why(c) -> str:
        """Raisons du rejet de la chaîne de post-traitement (core.Compat.pp_rejected), en clair."""
        why = {"composite": L("étape Composite absente"),
               "unknown": L("effets inconnus : {list}", list=", ".join(c.unknown_pp)),
               "version": L("preset fait pour CS {pv}", pv=c.preset_version)}
        return " ; ".join(why[r] for r in c.pp_rejected)

    def _game_state(self):
        running = core.game_running()
        self.game.setText(L("⚠ Jeu lancé : fermez-le avant d'appliquer") if running else L("Jeu fermé"))
        S.status(self.game, "warning" if running else "success")
        self._update_buttons()
        return running

    def say(self, text: str):
        self.log.appendPlainText(time.strftime("%H:%M:%S  ") + text)

    # ---------------------------------------------------------- actions
    def apply(self):
        p = self._cur()
        if not p or self._game_state() or self.sysname == systems.ENB:
            return
        c = self.compats.get(p.name)
        if c and c.frame_gen and QMessageBox.question(
                self, APP, L("« {name} » force la Frame Generation de Community Shaders, qui fait planter le jeu "
                             "sous CrossOver. Appliquer quand même ? La configuration en place est sauvegardée "
                             "avant.", name=p.name)) != QMessageBox.StandardButton.Yes:
            return
        if c and c.pp_rejected and QMessageBox.question(
                self, APP, L("Le post-traitement de « {name} » sera ignoré : votre Community Shaders {v} rejettera "
                             "sa chaîne ({why}) et la remplacera par une chaîne vide. Appliquer quand même ? La "
                             "configuration en place est sauvegardée avant.", name=p.name,
                             v=self.ref.get("version", ""), why=self._pp_why(c))) != \
                QMessageBox.StandardButton.Yes:
            return
        if c and (c.unknown_features or (c.unknown_pp and not c.pp_rejected)) and QMessageBox.question(
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
            if c and c.frame_gen:
                self.say(L("⚠ « {name} » force la Frame Generation : le jeu plantera sous CrossOver.",
                           name=path.name))
            if c and c.pp_rejected:
                self.say(L("⚠ « {name} » : post-traitement ignoré par votre Community Shaders ({why}).",
                           name=path.name, why=self._pp_why(c)))
            if c and (c.unknown_features or (c.unknown_pp and not c.pp_rejected)):
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

    def _web_imported(self, made):
        self.say(L("Ajouté depuis Nexus : {names}", names=", ".join(p.name for p in made)))
        self.refresh(made[-1].name)
        self._warn_imported(made)

    def from_nexus(self, url: str = ""):
        dlg = NexusDialog(self.cfg, self, url)
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

    def closeEvent(self, e):
        self.cfg["tab"] = self.tabs.currentIndex()
        core.save_config(self.cfg)
        self.browser.shutdown()
        super().closeEvent(e)

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
    S.brand(app, "csSETTINGS", "#14a5e6")  # « cs » dans le bleu du curseur du logo
    Path(cfg["library"]).mkdir(parents=True, exist_ok=True) if os.path.isdir(os.path.dirname(cfg["library"])) else None
    w = Main(cfg)
    w.show()
    # menu de l'appli : « À propos de csSETTINGS » (texte normal dans le menu) et « Rechercher les mises à jour… »
    about = QAction(L("À propos de {app}", app=APP), w)
    about.setMenuRole(QAction.MenuRole.AboutRole)
    about.triggered.connect(lambda: AboutDialog.show_for(w))
    w.menu_bar = QMenuBar()  # barre de menus macOS (sans parent : commune à toutes les fenêtres), reprise par l'updater
    w.menu_bar.addMenu(APP).addAction(about)
    updater.start_qt(w, "csSETTINGS", lang=i18n.get_lang,
                     busy=lambda: Worker.active > 0 or getattr(w, "_sys_busy", False))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
