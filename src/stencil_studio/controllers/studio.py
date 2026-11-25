"""Stencil Studio dans Laser Studio Pro : ouverture de la fenêtre du Studio,
préchauffage en arrière-plan, repli dans un processus séparé ou dans le
navigateur, thème suivi à chaud.

    studio = StencilStudioController(window, theme=current_colors, language="fr", dialogs=dialogs)
    studio.export_ready.connect(vector_editor.import_stencil_export)
    action.triggered.connect(studio.open)
    QTimer.singleShot(3000, studio.preload)

Le contrôleur ne connaît rien de LSP : il reçoit ses couleurs
(`theme()` -> dict, voir ui/themes.py), sa langue et ses boîtes de
dialogue (`dialogs.info` / `dialogs.warning`), et annonce chaque export
SVG / DXF par `export_ready(chemin)`.
"""
import json
import os
import sys
import threading
import webbrowser

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ..timing import log, restart
from ..ui import dialog as dialog_module
from ..ui.dialog import StudioDialog
from ..ui.themes import loading_text
from ..ui.window import EXPORT_PREFIX

# True : après le préchauffage des imports, charge aussi la page du Studio dans une fenêtre INVISIBLE :
# « Outils > Stencil Studio » l'affiche ensuite déjà prête. False : la page ne se charge qu'au clic.
PRECREATE_VIEW = True
# Port fixe si libre : garde les réglages du navigateur intégré d'une session à l'autre.
PREFERRED_PORT = 8765
# Messages de Qt qui signalent un QtWebEngine importé trop tard (fenêtre séparée possible).
LATE_WEBENGINE_ERRORS = ("ShareOpenGLContexts", "QtWebEngineWidgets must be imported")


def _server():
    """Module du serveur, importé à la demande : il charge OpenCV, SciPy, NumPy... (plusieurs secondes) ;
    en différé, le démarrage de LSP ne les attend plus, preload() les charge en arrière-plan."""
    from .. import server
    return server


def _warm_imports():
    """Dans un THREAD : charge ce qui est lourd et sans interface (aucun widget Qt ici, ils exigent le thread principal)."""
    try:
        _server()                                         # cv2, numpy, scipy, core, i18n...
        from .. import subject_ai
        model = subject_ai.MODEL_FILE
        if subject_ai.has_runtime() and os.path.isfile(model) and os.path.getsize(model) > 1_000_000:
            subject_ai._session()                         # modèle déjà téléchargé : chargé maintenant (jamais de téléchargement ici)
    except Exception:
        pass                                              # l'ouverture normale réessaiera et affichera l'erreur


def diagnostic():
    """Informations pour un rapport de bug quand QtWebEngine ne se charge pas."""
    from .. import core
    main = getattr(sys.modules.get("__main__"), "__file__", "?")
    return (f"Studio {core.VERSION} | compilé : {bool(getattr(sys, 'frozen', False))} | Python {sys.version.split()[0]}\n"
            f"programme principal : {main}\n"
            f"QtWebEngineWidgets déjà importé : {'PyQt6.QtWebEngineWidgets' in sys.modules} | "
            f"QtWebEngineCore : {'PyQt6.QtWebEngineCore' in sys.modules}\n"
            f"dossier du Studio : {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")


class StencilStudioController(QObject):
    """`window` : fenêtre parente ; `theme()` : couleurs actuelles de la page ;
    `language` : langue du message de chargement ; `dialogs` : messages."""

    export_ready = pyqtSignal(str)
    _imports_done = pyqtSignal()          # thread de préchauffage -> thread principal

    def __init__(self, window, *, theme, language, dialogs, parent=None):
        super().__init__(parent)
        self.window = window
        self._theme = theme
        self.language = language
        self.dialogs = dialogs
        self.dialog = None
        self.qt_dialog = None             # version Qt (open_qt)
        self._process = None
        self._server = None               # (serveur, port)
        self._preload_started = False
        self._imports_done.connect(self._create_hidden)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    # -- serveur et fenêtre

    def _url(self):
        if self._server is None:
            log("serveur : démarrage")
            self._server = _server().start_server(PREFERRED_PORT)
            log(f"serveur local démarré (port {self._server[1]})")
        return f"http://127.0.0.1:{self._server[1]}/"

    def _new_dialog(self):
        dlg = StudioDialog(self.window, self._theme(), loading_text(self.language))
        dlg.export_downloaded.connect(self.export_ready)
        self.dialog = dlg
        return dlg

    def set_theme(self, colors):
        """LSP a changé de thème : la page suit."""
        if self.dialog is not None:
            self.dialog.set_theme(colors)

    def shutdown(self):
        if self._server is None:
            return
        srv, self._server = self._server[0], None
        srv.shutdown()
        srv.server_close()

    # -- préchauffage

    def preload(self):
        """Préchauffe le Studio, une fois la fenêtre de LSP affichée : un thread charge les modules lourds
        (OpenCV, SciPy, modèle IA), puis (PRECREATE_VIEW) la page est chargée dans une fenêtre invisible.
        Sans effet si déjà fait, si QtWebEngine manque, ou si le Studio a déjà été ouvert."""
        if not dialog_module.HAVE_WEBENGINE or self._preload_started:
            return
        self._preload_started = True

        def run():
            _warm_imports()
            self._imports_done.emit()

        threading.Thread(target=run, name="stencil-warmup", daemon=True).start()

    def _create_hidden(self):
        log("préchauffage : imports terminés")
        if not PRECREATE_VIEW or self.dialog is not None:
            return                                        # imports seulement, ou déjà ouvert entre-temps
        dlg = self._new_dialog()
        dlg.start_warm()                                  # page chargée dans une fenêtre invisible
        dlg.load(self._url())

    # -- ouverture

    def open_qt(self):
        """« Outils > Stencil Studio (Qt) » : la version en widgets Qt (expérimentale), à côté de la page web ;
        ses exports arrivent par le même signal export_ready. Créée au premier appel, puis réaffichée."""
        if self.qt_dialog is None:
            from ..ui.qt import QStencilDialog        # chargé à la demande : OpenCV, SciPy… (plusieurs secondes)
            self.qt_dialog = QStencilDialog(self.window, language=self.language)
            self.qt_dialog.export_ready.connect(self.export_ready)
        self.qt_dialog.show()
        self.qt_dialog.raise_()
        self.qt_dialog.activateWindow()

    def open(self):
        """« Outils > Stencil Studio » : crée la fenêtre au premier appel, puis la réaffiche."""
        if not dialog_module.HAVE_WEBENGINE:
            self._open_without_webengine()
            return
        restart()
        log("clic : ouverture demandée")
        dlg = self.dialog or self._new_dialog()        # coque légère, la partie lente vient après l'affichage
        dlg.set_theme(self._theme())
        if dlg.warming:                 # clic pendant le préchargement : on l'amène à l'écran, il se terminera là
            dlg.leave_warm()
        if not dlg.opened_once:
            dlg.opened_once = True
            dlg.setWindowOpacity(0.0)    # invisible : ni flash blanc, ni page dessinée à moitié pendant le chargement
            dlg.showMaximized()
            QApplication.processEvents()
            if dlg.revealed:             # page déjà prête (préchargée) : on la montre après un court délai de rendu
                QTimer.singleShot(120, lambda: dlg.setWindowOpacity(1.0))
            else:
                dlg.show_splash()        # sinon message de chargement ; la page rend la fenêtre visible
        else:
            dlg.showMaximized()          # réouvertures : toujours maximisé
        dlg.raise_()
        dlg.activateWindow()
        if not dlg.has_page():
            QApplication.processEvents()      # la fenêtre (fond au thème) s'affiche avant la création de la vue web
            log("fenêtre affichée")
            dlg.load(self._url())

    def _open_without_webengine(self):
        """QtWebEngine indisponible dans LSP : fenêtre séparée si Qt l'a seulement refusé (importé trop
        tard), sinon le navigateur, avec l'explication."""
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            return                    # déja ouverte
        err = dialog_module.WEBENGINE_ERROR or "?"
        late = any(text in err for text in LATE_WEBENGINE_ERRORS)
        if late and self._open_external():
            return
        webbrowser.open(self._url())
        if late:
            hint = ("PyQt6-WebEngine est bien installé, mais Qt l'exige AVANT la création de la fenêtre de LSP.\n"
                    "Dans le fichier principal de LSP, tout en haut (avant QApplication), ajoute :\n"
                    "    from PyQt6 import QtWebEngineWidgets  # noqa")
        else:
            hint = ("Installe-le avec CE Python (celui qui lance LSP) :\n"
                    f"    \"{sys.executable}\" -m pip install -U PyQt6 PyQt6-WebEngine\n"
                    "(les versions de PyQt6, PyQt6-Qt6, PyQt6-WebEngine et PyQt6-WebEngine-Qt6 doivent être les mêmes)")
        self.dialogs.info(
            "Stencil Studio",
            "Le moteur web de Qt n'a pas pu être chargé : le Studio s'ouvre dans le navigateur.\n"
            "Les fichiers exportés iront dans le dossier Téléchargements (à importer dans LSP).\n\n"
            f"Raison : {err}\n\n{hint}\n\n--- Diagnostic (à me transmettre) ---\n{diagnostic()}")

    def _open_external(self):
        """Le Studio dans son propre processus (sa propre fenêtre Qt) ; ses exports reviennent par export_ready."""
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proc = QProcess(self)
        proc.setWorkingDirectory(os.path.dirname(package_dir))
        proc.setProgram(sys.executable)
        args = ["--theme", json.dumps(self._theme()), "--lang", self.language]
        if getattr(sys, "frozen", False):      # LSP compilé : on relance l'exécutable avec un argument (voir main.py)
            proc.setArguments(["--stencil-studio", *args])
        else:
            proc.setArguments(["-m", f"{os.path.basename(package_dir)}.ui.window", *args])
        state = {"buf": b"", "got": False}

        def read():
            state["buf"] += bytes(proc.readAllStandardOutput())
            while b"\n" in state["buf"]:
                line, state["buf"] = state["buf"].split(b"\n", 1)
                line = line.decode("utf-8", "replace").strip()
                if line.startswith(EXPORT_PREFIX):
                    state["got"] = True
                    self.export_ready.emit(line[len(EXPORT_PREFIX):])

        def done(code, _status):
            if code != 0 and not state["got"]:
                err = bytes(proc.readAllStandardError()).decode("utf-8", "replace")[-600:]
                self.dialogs.warning("Stencil Studio", "La fenêtre séparée du Studio n'a pas pu démarrer.\n\n" + err)

        proc.readyReadStandardOutput.connect(read)
        proc.finished.connect(done)
        proc.start()
        self._process = proc
        return proc.waitForStarted(5000)
