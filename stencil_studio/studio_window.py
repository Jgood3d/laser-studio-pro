"""Fenêtre Stencil Studio dans un processus séparé (repli quand Qt refuse QtWebEngine dans LSP).

Lancé par studio_dialog.open_stencil_studio :  python -m stencil_studio.studio_window
(LSP compilé : LaserStudioPro.exe --stencil-studio, géré en tête de main.py :
    import sys
    if "--stencil-studio" in sys.argv:
        from stencil_studio.studio_window import main as _stencil_main
        sys.exit(_stencil_main())  )
Ce processus a son propre QApplication, créé dans le bon ordre (QtWebEngineWidgets importé avant).
Quand un export SVG / DXF est terminé, il écrit « STENCIL_EXPORT:<chemin> » sur sa sortie standard
(LSP l'importe) puis se ferme.
"""
import sys


def main():
    from PyQt6.QtCore import Qt, QCoreApplication
    from PyQt6 import QtWebEngineWidgets  # noqa: F401  (avant la création de QApplication)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from . import studio_dialog as sd

    class Win(sd.StudioDialog):
        def _finished(self, req):
            if not req.isFinished():
                return
            if req.state() != sd.QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                return
            import os
            path = os.path.join(req.downloadDirectory(), req.downloadFileName())
            print("STENCIL_EXPORT:" + path, flush=True)
            self.close()
            app.quit()

    win = Win(None)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
