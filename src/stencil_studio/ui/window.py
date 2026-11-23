"""Stencil Studio dans un processus séparé (repli quand Qt refuse QtWebEngine dans LSP).

Lancé par controllers/studio.py :  python -m stencil_studio.ui.window --theme '{...}' --lang fr
(LSP compilé : LaserStudioPro --stencil-studio ..., géré en tête de laser_studio/main.py).
Ce processus a son propre QApplication, créé dans le bon ordre (QtWebEngineWidgets importé avant).
Quand un export SVG / DXF est terminé, il écrit « STENCIL_EXPORT:<chemin> » sur sa sortie standard
(LSP l'importe) puis se ferme.
"""
import argparse
import json
import sys

# Préfixe de la ligne qui annonce un export à LSP.
EXPORT_PREFIX = "STENCIL_EXPORT:"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stencil_studio.ui.window")
    ap.add_argument("--stencil-studio", action="store_true", help=argparse.SUPPRESS)   # LSP compilé
    ap.add_argument("--theme", default="", help="couleurs de la page (JSON)")
    ap.add_argument("--lang", default="fr")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    from PyQt6.QtCore import Qt, QCoreApplication
    from PyQt6 import QtWebEngineWidgets  # noqa: F401  (avant la création de QApplication)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])
    from ..server import DEFAULT_PORT, start_server
    from .dialog import StudioDialog
    from .themes import DEFAULT_THEME, loading_text

    theme = json.loads(args.theme) if args.theme else dict(DEFAULT_THEME)
    srv, port = start_server(DEFAULT_PORT)
    win = StudioDialog(None, theme, loading_text(args.lang))

    def exported(path):
        print(EXPORT_PREFIX + path, flush=True)
        win.close()
        app.quit()

    win.export_downloaded.connect(exported)
    win.showMaximized()  # ouverture en plein écran (fenêtre maximisée)
    win.load(f"http://127.0.0.1:{port}/")
    code = app.exec()
    srv.shutdown()
    srv.server_close()
    return code


if __name__ == "__main__":
    sys.exit(main())
