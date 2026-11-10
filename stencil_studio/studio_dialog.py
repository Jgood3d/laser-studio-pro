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
import sys
import tempfile
import webbrowser

from PyQt6.QtCore import QUrl, Qt, QStandardPaths, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QFileDialog, QApplication

from . import studio as _studio
from .lsp_bridge import import_exported_file

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest
    HAVE_WEBENGINE = True
    WEBENGINE_ERROR = ""
except Exception as _e:  # pragma: no cover  (ImportError, mais aussi erreurs de DLL / de version)
    HAVE_WEBENGINE = False
    WEBENGINE_ERROR = f"{type(_e).__name__}: {_e}"

# Thèmes Stencil Studio alignés sur ceux de Laser Studio Pro (ui/app/theme.py).
LSP_THEME_DARK = {
    "bg": "#232323", "panel": "#303030", "panel2": "#3b3b3b", "line": "#4d4d4d",
    "fg": "#f2f2f2", "mut": "#a8a8a8", "acc": "#3a5b89", "acc2": "#6dbef9", "onacc": "#ffffff",
}
LSP_THEME_LIGHT = {
    "bg": "#f3f3f3", "panel": "#ffffff", "panel2": "#f0f0f0", "line": "#d0d0d0",
    "fg": "#1a1a1a", "mut": "#666666", "acc": "#0078d4", "acc2": "#4aa3e8", "onacc": "#ffffff",
}
# Dusk — gris-bleu doux
LSP_THEME_DUSK = {
    "bg": "#232831", "panel": "#2b303b", "panel2": "#353b4a", "line": "#4f5666",
    "fg": "#d8dee9", "mut": "#9aa3b5", "acc": "#88c0d0", "acc2": "#8fbcbb", "onacc": "#2b303b",
}
# Warm dim — gris chaud ambré
LSP_THEME_WARM = {
    "bg": "#241f1c", "panel": "#2c2825", "panel2": "#3a3530", "line": "#5a524a",
    "fg": "#e8e0d5", "mut": "#a89c8e", "acc": "#d4a574", "acc2": "#e0b88a", "onacc": "#2c2825",
}
# Neon laser — cyan + magenta
LSP_THEME_NEON = {
    "bg": "#120f1c", "panel": "#0d0b14", "panel2": "#1a1628", "line": "#3d3560",
    "fg": "#e8e6f2", "mut": "#9b93b8", "acc": "#00e5c3", "acc2": "#ff4ecd", "onacc": "#0d0b14",
}
# Rétro 80s — synthwave
LSP_THEME_RETRO80 = {
    "bg": "#12061f", "panel": "#1a0a2e", "panel2": "#2a1450", "line": "#7b2cbf",
    "fg": "#f0e6ff", "mut": "#b8a0d0", "acc": "#ff2a6d", "acc2": "#05d9e8", "onacc": "#1a0a2e",
}
# Alias rétrocompat : l'ancien LSP_THEME était toujours sombre.
LSP_THEME = LSP_THEME_DARK

_STUDIO_THEMES = {
    "dark": LSP_THEME_DARK,
    "sombre": LSP_THEME_DARK,
    "light": LSP_THEME_LIGHT,
    "clair": LSP_THEME_LIGHT,
    "dusk": LSP_THEME_DUSK,
    "warm": LSP_THEME_WARM,
    "neon": LSP_THEME_NEON,
    "laser": LSP_THEME_NEON,
    "retro80": LSP_THEME_RETRO80,
    "retro": LSP_THEME_RETRO80,
    "synthwave": LSP_THEME_RETRO80,
    "80s": LSP_THEME_RETRO80,
}


def theme_from_palette(pal=None):
    """Couleurs de la page Studio déduites de la palette Qt de LSP (fenêtre, texte, accent...)."""
    from PyQt6.QtGui import QPalette, QColor
    app = QApplication.instance()
    pal = pal or (app.palette() if app else None)
    if pal is None:
        return dict(LSP_THEME_DARK)
    R = QPalette.ColorRole

    def hx(c):
        return c.name()

    def mix(a, b, t):
        return QColor(
            int(a.red() * (1 - t) + b.red() * t),
            int(a.green() * (1 - t) + b.green() * t),
            int(a.blue() * (1 - t) + b.blue() * t),
        )

    win, base, btn = pal.color(R.Window), pal.color(R.Base), pal.color(R.Button)
    fg, acc = pal.color(R.WindowText), pal.color(R.Highlight)
    if win.lightness() > 140:
        return dict(LSP_THEME_LIGHT)
    lum = 0.299 * acc.red() + 0.587 * acc.green() + 0.114 * acc.blue()
    return {
        "bg": hx(base if base.lightness() <= win.lightness() else win.darker(115)),
        "panel": hx(win),
        "panel2": hx(btn),
        "line": hx(mix(win, fg, 0.18)),
        "fg": hx(fg),
        "mut": hx(mix(win, fg, 0.58)),
        "acc": hx(acc),
        "acc2": hx(acc.lighter(130)),
        "onacc": "#111111" if lum > 140 else "#ffffff",
    }


def theme_for_lsp(theme_name=None):
    """Thème Studio aligné sur LSP (source privilégiée : ui.app.theme.THEMES)."""
    if theme_name is None:
        try:
            from PyQt6.QtCore import QSettings
            theme_name = QSettings("LaserStudioPro", "UIConfig").value("app_theme", "dark")
        except Exception:
            theme_name = "dark"
    try:
        from ui.app.theme import THEMES, normalize_theme_name
        key = normalize_theme_name(theme_name)
        c = THEMES[key]
        return {
            "bg": c["base"],
            "panel": c["window"],
            "panel2": c["alt"],
            "line": c["border"],
            "fg": c["text"],
            "mut": c["muted"],
            "acc": c["accent"],
            "acc2": c["accent_hover"],
            "onacc": c["on_accent"],
        }
    except Exception:
        pass
    key = str(theme_name).lower()
    if key in _STUDIO_THEMES:
        return dict(_STUDIO_THEMES[key])
    return theme_from_palette()


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
        # Évite le « flash » du thème d'origine du Studio : la fenêtre et le fond de la page
        # prennent tout de suite la couleur du thème LSP, et la page reste masquée jusqu'à ce
        # que le thème lui ait été appliqué (voir _apply_theme / _reveal_view).
        self._loaded = False
        self._paint_background()
        self.view.hide()
        QTimer.singleShot(4000, self._reveal_view)   # filet de sécurité si le thème ne répond pas
        self.view.loadFinished.connect(self._on_load_finished)
        self.view.load(QUrl(f"http://127.0.0.1:{self._port}/"))
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def _current_theme(self):
        return self._theme if self._theme is not None else theme_for_lsp()

    def _paint_background(self):
        """Fond de la fenêtre et de la page aux couleurs du thème LSP (avant tout rendu de la page)."""
        try:
            bg = self._current_theme().get("bg", "#232323")
            self.setStyleSheet(f"QDialog {{ background-color: {bg}; }}")
            self.view.page().setBackgroundColor(QColor(bg))
        except Exception:
            pass

    def _reveal_view(self):
        if not self.view.isVisible():
            self.view.show()

    def _on_load_finished(self, ok=True):
        """Page chargée : on applique le thème LSP, puis on la rend visible."""
        if ok is False:
            self._reveal_view()
            return
        self._loaded = True
        self._apply_theme(True, reveal=True)

    def _apply_theme(self, ok=True, reveal=False):
        """Reprend les couleurs de LSP (palette Qt, ou dictionnaire `theme` passé à open_stencil_studio)."""
        if ok is False:
            return
        import json
        try:
            self._paint_background()
            if not self._loaded:
                return                      # page pas encore chargée : appliqué par _on_load_finished
            t = self._current_theme()
            js = f"window.setTheme && window.setTheme({json.dumps(t)})"
            if reveal:
                # Page affichée seulement une fois le thème appliqué (petit délai pour laisser le repaint).
                self.view.page().runJavaScript(js, lambda _r: QTimer.singleShot(80, self._reveal_view))
            else:
                self.view.page().runJavaScript(js)
        except Exception:
            self._reveal_view()

    def sync_theme_from_lsp(self, theme_name=None):
        """Met à jour le thème Studio quand LSP change de thème (clair / sombre)."""
        self._theme = theme_for_lsp(theme_name)
        self._apply_theme(True)

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


def _diagnostic():
    import sys as _s
    try:
        from . import core as _c
        ver = _c.VERSION
    except Exception:
        ver = "?"
    main = getattr(_s.modules.get("__main__"), "__file__", "?")
    return (f"Studio {ver} | compilé : {bool(getattr(_s, 'frozen', False))} | Python {_s.version.split()[0]}\n"
            f"programme principal : {main}\n"
            f"QtWebEngineWidgets déjà importé : {'PyQt6.QtWebEngineWidgets' in _s.modules} | "
            f"QtWebEngineCore : {'PyQt6.QtWebEngineCore' in _s.modules}\n"
            f"dossier du Studio : {os.path.dirname(os.path.abspath(__file__))}")


def _open_external(window):
    """Repli : le Studio dans son propre processus (sa propre fenêtre Qt) ; les exports reviennent dans LSP."""
    from PyQt6.QtCore import QProcess
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    proc = QProcess(window)
    proc.setWorkingDirectory(os.path.dirname(pkg_dir))
    proc.setProgram(sys.executable)
    if getattr(sys, "frozen", False):      # LSP compilé : on relance l'exécutable avec un argument (voir main.py)
        proc.setArguments(["--stencil-studio"])
    else:
        proc.setArguments(["-m", f"{os.path.basename(pkg_dir)}.studio_window"])
    state = {"buf": b"", "got": False}

    def _read():
        state["buf"] += bytes(proc.readAllStandardOutput())
        while b"\n" in state["buf"]:
            line, state["buf"] = state["buf"].split(b"\n", 1)
            line = line.decode("utf-8", "replace").strip()
            if line.startswith("STENCIL_EXPORT:"):
                state["got"] = True
                import_exported_file(window, line.split(":", 1)[1])

    def _done(code, _status):
        if code != 0 and not state["got"]:
            err = bytes(proc.readAllStandardError()).decode("utf-8", "replace")[-600:]
            QMessageBox.warning(window, "Stencil Studio", "La fenêtre séparée du Studio n'a pas pu démarrer.\n\n" + err)
    proc.readyReadStandardOutput.connect(_read)
    proc.finished.connect(_done)
    proc.start()
    window._stencil_studio_proc = proc
    return proc.waitForStarted(5000)


def open_stencil_studio(window, theme=None):
    """À appeler depuis un menu de LSP. Crée la fenêtre au premier appel, puis la réaffiche.

    Si `theme` est None, le thème suit le réglage clair/sombre de Laser Studio Pro.
    """
    if theme is None:
        theme = theme_for_lsp()
    if not HAVE_WEBENGINE:
        prev = getattr(window, "_stencil_studio_proc", None)
        if prev is not None and prev.state() != prev.ProcessState.NotRunning:
            return None            # déjà ouvert
        if "ShareOpenGLContexts" in WEBENGINE_ERROR or "QtWebEngineWidgets must be imported" in WEBENGINE_ERROR:
            if _open_external(window):
                return None
        srv, port = _studio.start_server(PREFERRED_PORT)
        webbrowser.open(f"http://127.0.0.1:{port}/")
        import sys as _sys
        err = WEBENGINE_ERROR or "?"
        if "ShareOpenGLContexts" in err or "QtWebEngineWidgets must be imported" in err:
            hint = ("PyQt6-WebEngine est bien installé, mais Qt l'exige AVANT la création de la fenêtre de LSP.\n"
                    "Dans le fichier principal de LSP, tout en haut (avant QApplication), ajoute :\n"
                    "    from PyQt6 import QtWebEngineWidgets  # noqa")
        else:
            hint = ("Installe-le avec CE Python (celui qui lance LSP) :\n"
                    f"    \"{_sys.executable}\" -m pip install -U PyQt6 PyQt6-WebEngine\n"
                    "(les versions de PyQt6, PyQt6-Qt6, PyQt6-WebEngine et PyQt6-WebEngine-Qt6 doivent être les mêmes)")
        QMessageBox.information(
            window, "Stencil Studio",
            "Le moteur web de Qt n'a pas pu être chargé : le Studio s'ouvre dans le navigateur.\n"
            "Les fichiers exportés iront dans le dossier Téléchargements (à importer dans LSP).\n\n"
            f"Raison : {err}\n\n{hint}\n\n--- Diagnostic (à me transmettre) ---\n{_diagnostic()}")
        return None
    dlg = getattr(window, "_stencil_studio_dialog", None)
    first_open = dlg is None
    if first_open:
        dlg = StudioDialog(window, theme)
        window._stencil_studio_dialog = dlg
    if theme is not None:
        dlg._theme = theme
        dlg._apply_theme()
    if first_open:
        dlg.showMaximized()      # première ouverture : plein écran (fenêtre maximisée)
    else:
        dlg.show()               # réouvertures : on garde l'état choisi par l'utilisateur
    dlg.raise_()
    dlg.activateWindow()
    return dlg
