"""Fenêtre de documentation : pages Markdown de resources/doc/ affichées par
un QTextBrowser.

Qt lit le Markdown nativement (CommonMark + tableaux GitHub) : les fichiers
.md sont embarqués tels quels, sans conversion en HTML ni moteur web. Les
liens entre pages (`[Calques](calques.md)`) et les images relatives
(`![](images/calques.png)`) fonctionnent ; les liens http(s) s'ouvrent dans
le navigateur du système.
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QStyle, QTextBrowser, QToolBar,
    QVBoxLayout,
)

from laser_studio.core.paths import find_doc_page
from laser_studio.i18n import get_current_language, tr


def _icon(theme_icon, fallback):
    icon = QIcon.fromTheme(theme_icon)
    if icon.isNull():
        icon = QApplication.style().standardIcon(fallback)
    return icon


class HelpDialog(QDialog):
    """Fenêtre non modale : on peut lire la doc en gardant la main sur
    l'application. Une seule instance, réaffichée par show_page()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("help.title"))
        self.resize(820, 640)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.document().setDocumentMargin(16)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toolbar())
        layout.addWidget(self.browser)

    def _toolbar(self):
        bar = QToolBar()
        back = bar.addAction(
            _icon(QIcon.ThemeIcon.GoPrevious, QStyle.StandardPixmap.SP_ArrowBack),
            tr("help.back"), self.browser.backward,
        )
        back.setShortcut(QKeySequence.StandardKey.Back)
        self.browser.backwardAvailable.connect(back.setEnabled)
        back.setEnabled(False)
        forward = bar.addAction(
            _icon(QIcon.ThemeIcon.GoNext, QStyle.StandardPixmap.SP_ArrowForward),
            tr("help.forward"), self.browser.forward,
        )
        forward.setShortcut(QKeySequence.StandardKey.Forward)
        self.browser.forwardAvailable.connect(forward.setEnabled)
        forward.setEnabled(False)
        bar.addAction(
            _icon(QIcon.ThemeIcon.GoHome, QStyle.StandardPixmap.SP_DirHomeIcon),
            tr("help.home"), self.browser.home,
        )
        return bar

    def show_page(self, page="index.md"):
        """Affiche `page` (dans la langue de l'interface, sinon en français)
        et met la fenêtre au premier plan."""
        path = find_doc_page(get_current_language(), page)
        if path is None:
            self.browser.setHtml(
                f"<p style='color:#cc6666'>{tr('help.not_found')}</p>"
            )
        else:
            self.browser.setSource(QUrl.fromLocalFile(path))
        self.show()
        self.raise_()
        self.activateWindow()
