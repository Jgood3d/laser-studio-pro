"""Fenêtre « Stencil Studio » intégrée à Laser Studio Pro (PyQt6 + QtWebEngine).

Branchement dans la fenêtre principale de LSP (une action de menu) :

    from stencil_studio.studio_dialog import open_stencil_studio
    action.triggered.connect(lambda: open_stencil_studio(self))

Par défaut les couleurs sont celles de LSP (LSP_THEME ci-dessous). Pour en imposer d'autres :
    open_stencil_studio(self, theme={"bg": "#1e1e1e", "panel": "#2b2b2b", "panel2": "#3a3a3a", "line": "#4a4a4a",
                                     "fg": "#e0e0e0", "mut": "#9a9a9a", "acc": "#4a90d9", "acc2": "#7ab4f0", "onacc": "#ffffff"}

Le dossier du Studio doit s'appeler `stencil_studio` et se trouver dans le dossier de LSP.
Prérequis supplémentaire : pip install PyQt6-WebEngine
Les exports SVG / DXF sont interceptés et importés directement dans l'éditeur vectoriel (DXF : calques
Découpe / Cadrage rangés automatiquement) ; les autres fichiers (PDF, PNG...) ouvrent « Enregistrer sous ».
"""
import os
import tempfile
import webbrowser

from PyQt6.QtCore import QUrl, Qt, QStandardPaths
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QFileDialog, QApplication

from . import studio as _studio
from .lsp_bridge import import_exported_file

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest
    HAVE_WEBENGINE = True
except ImportError:  # pragma: no cover
    HAVE_WEBENGINE = False

# Couleurs de Laser Studio Pro (relevées sur l'interface : fond #232323, panneaux #303030, boutons #3b3b3b,
# champs #2e2e2e, bouton d'action bleu, curseurs / coches #6dbef9).
LSP_THEME = {"bg": "#232323", "panel": "#303030", "panel2": "#3b3b3b", "line": "#4d4d4d",
             "fg": "#f2f2f2", "mut": "#a8a8a8", "acc": "#3a5b89", "acc2": "#6dbef9", "onacc": "#ffffff"}


def theme_from_palette(pal=None):
    """Couleurs de la page Studio déduites de la palette Qt de LSP (fenêtre, texte, accent...)."""
    from PyQt6.QtGui import QPalette, QColor
    pal = pal or QApplication.instance().palette()
    R = QPalette.ColorRole

    def hx(c):
        return c.name()

    def mix(a, b, t):
        return QColor(int(a.red() * (1 - t) + b.red() * t), int(a.green() * (1 - t) + b.green() * t),
                      int(a.blue() * (1 - t) + b.blue() * t))
    win, base, btn = pal.color(R.Window), pal.color(R.Base), pal.color(R.Button)
    fg, acc = pal.color(R.WindowText), pal.color(R.Highlight)
    lum = 0.299 * acc.red() + 0.587 * acc.green() + 0.114 * acc.blue()
    return {"bg": hx(base if base.lightness() <= win.lightness() else win.darker(115)),
            "panel": hx(win), "panel2": hx(btn), "line": hx(mix(win, fg, 0.18)),
            "fg": hx(fg), "mut": hx(mix(win, fg, 0.58)),
            "acc": hx(acc), "acc2": hx(acc.lighter(130)),
            "onacc": "#111111" if lum > 140 else "#ffffff"}


PREFERRED_PORT = 8765   # port fixe si libre : garde les réglages du navigateur intégré d'une session à l'autre


class StudioDialog(QDialog):
    def __init__(self, window, theme=None):
        super().__init__(window)
        self._theme = theme
        self.lsp = window
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("Stencil Studio")
        self.resize(1500, 900)
        self._tmp = tempfile.mkdtemp(prefix="stencil_studio_")
        self._srv, self._port = _studio.start_server(PREFERRED_PORT)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        store = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
                             "StencilStudio")
        os.makedirs(store, exist_ok=True)
        self.profile = QWebEngineProfile("StencilStudio", self)
        self.profile.setPersistentStoragePath(store)
        self.profile.setCachePath(os.path.join(store, "cache"))
        self.profile.downloadRequested.connect(self._on_download)
        self.view = QWebEngineView(self)
        self.view.setPage(QWebEnginePage(self.profile, self.view))
        lay.addWidget(self.view)
        self.view.loadFinished.connect(self._apply_theme)
        self.view.load(QUrl(f"http://127.0.0.1:{self._port}/"))
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def _apply_theme(self, ok=True):
        """Reprend les couleurs de LSP (palette Qt, ou dictionnaire `theme` passé à open_stencil_studio)."""
        if not ok:
            return
        import json
        try:
            t = self._theme if self._theme is not None else LSP_THEME
            self.view.page().runJavaScript(f"window.setTheme && window.setTheme({json.dumps(t)})")
        except Exception:
            pass

    # -- téléchargements de la page -> import dans LSP
    def _on_download(self, req):
        name = req.downloadFileName() or "export"
        if os.path.splitext(name)[1].lower() in (".svg", ".dxf"):
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
        path = os.path.join(req.downloadDirectory(), req.downloadFileName())
        self.hide()                       # on revient à LSP ; le Studio garde son état (réouverture instantanée)
        import_exported_file(self.lsp, path)

    def shutdown(self):
        try:
            self._srv.shutdown()
            self._srv.server_close()
        except Exception:
            pass


def open_stencil_studio(window, theme=None):
    """À appeler depuis un menu de LSP. Crée la fenêtre au premier appel, puis la réaffiche."""
    if not HAVE_WEBENGINE:
        srv, port = _studio.start_server(PREFERRED_PORT)
        webbrowser.open(f"http://127.0.0.1:{port}/")
        QMessageBox.information(
            window, "Stencil Studio",
            "PyQt6-WebEngine n'est pas installé : le Studio s'ouvre dans le navigateur.\n"
            "Les fichiers exportés iront dans le dossier Téléchargements (à importer dans LSP).\n\n"
            "Pour l'intégration complète : pip install PyQt6-WebEngine")
        return None
    dlg = getattr(window, "_stencil_studio_dialog", None)
    if dlg is None:
        dlg = StudioDialog(window, theme)
        window._stencil_studio_dialog = dlg
    if theme is not None:
        dlg._theme = theme
        dlg._apply_theme()
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    return dlg
