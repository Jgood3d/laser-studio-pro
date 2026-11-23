"""Fenêtre Qt de Stencil Studio : la page web du Studio dans un
QWebEngineView, aux couleurs de Laser Studio Pro.

    dialog = StudioDialog(parent, theme, loading_text("fr"))
    dialog.export_downloaded.connect(import_in_lsp)
    dialog.load("http://127.0.0.1:8765/")

C'est une vue : le serveur, le préchauffage et l'ouverture sont dans
controllers/studio.py. Les exports SVG / DXF de la page sont téléchargés
dans un dossier temporaire puis annoncés par `export_downloaded(chemin)` ;
les autres fichiers (PDF, PNG...) ouvrent « Enregistrer sous ».
"""
import json
import os
import tempfile

from PyQt6.QtCore import QStandardPaths, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QDialog, QFileDialog, QLabel, QStackedLayout

from ..timing import log

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile
    HAVE_WEBENGINE = True
    WEBENGINE_ERROR = ""
except Exception as _e:  # pragma: no cover  (ImportError, mais aussi erreurs de DLL / de version)
    HAVE_WEBENGINE = False
    WEBENGINE_ERROR = f"{type(_e).__name__}: {_e}"

# Délai maxi (ms) avant d'afficher la page même si le thème n'a pas répondu.
REVEAL_TIMEOUT_MS = 4000
# Extensions importées dans l'éditeur vectoriel au lieu d'être enregistrées.
IMPORTED_EXTENSIONS = (".svg", ".dxf")


class StudioDialog(QDialog):
    """`theme` : couleurs de la page (voir ui/themes.py) ; `loading` : texte
    affiché pendant le chargement de la page."""

    export_downloaded = pyqtSignal(str)

    def __init__(self, parent, theme, loading):
        super().__init__(parent)
        self.theme = theme
        self.opened_once = False      # première ouverture visible : fenêtre maximisée
        self.warming = False          # True : chargement invisible en arrière-plan (voir start_warm)
        self.revealed = False
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("Stencil Studio")
        self.resize(1500, 900)
        self._tmp = tempfile.mkdtemp(prefix="stencil_studio_")
        self._loading_text = loading
        self._splash = None
        self.view = None
        # Pile : message de chargement / page web. Le layout donne SA TAILLE FINALE à la vue même quand
        # elle n'est pas affichée : plus de page dessinée dans un petit rectangle avant l'agrandissement.
        self._lay = QStackedLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._loading = QLabel(loading, self)     # remplit la fenêtre tant que la page n'est pas prête
        self._loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lay.addWidget(self._loading)
        self.setAutoFillBackground(True)
        self._loaded = False
        self._paint_background()           # la fenêtre apparaît tout de suite aux couleurs du thème LSP

    def has_page(self):
        return self.view is not None

    def start_warm(self):
        """Fenêtre affichée mais INVISIBLE (opacité 0, très loin hors écran, sans activation), pour y charger la
        page en arrière-plan. Une fenêtre qui n'a jamais été affichée dessine mal sa page web (rectangle,
        barres de défilement, blanc...) : ici ça se passe là où personne ne regarde."""
        self.warming = True
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowOpacity(0.0)
        self.setGeometry(-30000, -30000, 1500, 900)
        self.show()

    def leave_warm(self):
        """Fin du chargement invisible (ou clic pendant celui-ci) : position et activation normales."""
        self.warming = False
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        parent = self.parentWidget()
        self.resize(1500, 900)
        if parent is not None:
            self.move(parent.x() + 60, parent.y() + 60)

    def load(self, url):
        """Crée la vue web et y charge `url` (la partie lente). Séparé de __init__ pour que la fenêtre puisse
        s'afficher AVANT, au lieu de laisser l'écran figé pendant la création."""
        if self.view is not None:
            return
        store = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
                             "StencilStudio")
        os.makedirs(store, exist_ok=True)
        self.profile = QWebEngineProfile("StencilStudio", self)
        self.profile.setPersistentStoragePath(store)
        self.profile.setCachePath(os.path.join(store, "cache"))
        self.profile.downloadRequested.connect(self._on_download)
        self.view = QWebEngineView(self)
        self.view.setPage(QWebEnginePage(self.profile, self.view))
        self._lay.addWidget(self.view)
        log("vue web créée")
        # Évite le « flash » du thème d'origine du Studio : la page reste masquée jusqu'à ce que le thème
        # LSP lui ait été appliqué (voir _apply_theme / _reveal_view).
        self._paint_background()
        QTimer.singleShot(REVEAL_TIMEOUT_MS, self._reveal_view)   # filet de sécurité si le thème ne répond pas
        self.view.loadFinished.connect(self._on_load_finished)
        self.view.load(QUrl(url))
        log("chargement de la page lancé")

    def set_theme(self, theme):
        """Nouvelles couleurs (LSP a changé de thème)."""
        self.theme = theme
        self._apply_theme(True)

    def _paint_background(self):
        """Fond de la fenêtre et de la page aux couleurs du thème LSP (avant tout rendu de la page)."""
        bg = self.theme.get("bg", "#232323")
        self.setStyleSheet(f"QDialog {{ background-color: {bg}; }}")
        pal = self.palette()                           # fond sombre dès le premier rendu (pas de blanc)
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        self.setPalette(pal)
        self._loading.setStyleSheet(f"color: {self.theme.get('mut', '#a8a8a8')}; font-size: 16px;")
        if self.view is not None:
            self.view.page().setBackgroundColor(QColor(bg))

    def show_splash(self):
        """Petit message « Chargement… » (fenêtre Qt simple, sans web) pendant que la fenêtre du Studio, encore
        invisible, charge sa page : rien du chargement (blanc, rectangle, barres...) n'est montré à l'écran."""
        t = self.theme
        lbl = QLabel(self._loading_text, None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        lbl.setStyleSheet(f"background-color: {t.get('panel', '#303030')}; color: {t.get('fg', '#f2f2f2')};"
                          f" border: 1px solid {t.get('line', '#4d4d4d')}; padding: 22px 44px; font-size: 16px;")
        lbl.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            c = parent.frameGeometry().center()
            lbl.move(c.x() - lbl.width() // 2, c.y() - lbl.height() // 2)
        lbl.show()
        self._splash = lbl

    def _hide_splash(self):
        lbl, self._splash = self._splash, None
        if lbl is not None:
            lbl.close()

    def _reveal_view(self):
        """Affiche la page web à la place du message de chargement (une seule fois)."""
        if self.view is not None and not self.revealed:
            self.revealed = True
            log("page affichée")
            self._lay.setCurrentWidget(self.view)
            self._hide_splash()
            if self.warming:                 # chargement en arrière-plan terminé : on range la fenêtre
                log("préchargement terminé")
                self.hide()
                self.leave_warm()            # (reste à l'opacité 0 : l'ouverture la montrera proprement)
            else:
                self.setWindowOpacity(1.0)   # la fenêtre était invisible pendant le chargement

    def _on_load_finished(self, ok=True):
        """Page chargée : on applique le thème LSP, puis on la rend visible."""
        if ok is False:
            self._reveal_view()
            return
        log("page chargée")
        self._loaded = True
        self._apply_theme(True, reveal=True)

    def _apply_theme(self, ok=True, reveal=False):
        """Couleurs du thème passées à la page (window.setTheme)."""
        if ok is False:
            return
        try:
            self._paint_background()
            if not self._loaded:
                return                      # page pas encore chargée : appliqué par _on_load_finished
            js = f"window.setTheme && window.setTheme({json.dumps(self.theme)})"
            if reveal:
                # Page affichée seulement une fois le thème appliqué (petit délai pour laisser le repaint).
                self.view.page().runJavaScript(js, lambda _r: QTimer.singleShot(80, self._reveal_view))
            else:
                self.view.page().runJavaScript(js)
        except RuntimeError:                # vue détruite pendant la fermeture
            self._reveal_view()

    # -- téléchargements de la page
    def _on_download(self, req):
        name = req.downloadFileName() or "export"
        if os.path.splitext(name)[1].lower() in IMPORTED_EXTENSIONS:
            req.setDownloadDirectory(self._tmp)
            req.setDownloadFileName(name)
            req.isFinishedChanged.connect(lambda r=req: self._finished(r))
            req.accept()
            return
        home = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer", os.path.join(home, name))
        if not path:
            req.cancel()
            return
        req.setDownloadDirectory(os.path.dirname(path))
        req.setDownloadFileName(os.path.basename(path))
        req.accept()

    def _finished(self, req):
        if not req.isFinished():
            return
        if req.state() != QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            return
        self.downloaded(os.path.join(req.downloadDirectory(), req.downloadFileName()))

    def downloaded(self, path):
        """Export SVG / DXF prêt : on revient à LSP (le Studio garde son état, réouverture instantanée)."""
        self.hide()
        self.export_downloaded.emit(path)
