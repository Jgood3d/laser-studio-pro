"""Bannière de l'application, affichée dans « À propos »."""

import os

from PyQt6.QtGui import QPixmap

from app_constants import BANNER_FILENAME
from app_utils import find_resource, get_app_dir, get_bundle_dir
from i18n import tr
from widgets_extra import scaled_to_width_hidpi


class AboutBannerPixmap(QPixmap):
    """Bannière de l'application, réduite à `width` pixels logiques.

    L'image est cherchée à côté de l'exécutable, puis dans le bundle
    PyInstaller (voir find_resource). `ratio` est l'échelle de l'écran,
    pour qu'elle reste nette en haute résolution.
    """

    FILENAME = BANNER_FILENAME

    def __init__(self, width, ratio):
        path = find_resource(self.FILENAME)
        super().__init__(path or "")
        self.path = path
        if not self.isNull():
            self.swap(scaled_to_width_hidpi(self, width, ratio))

    def error_message(self):
        """Message d'erreur à la place de la bannière, ou None si chargée."""
        if self.path is None:
            searched = {
                os.path.join(get_app_dir(), self.FILENAME),
                os.path.join(get_bundle_dir(), self.FILENAME),
            }
            return tr("ui.banner_missing").format(
                paths="\n".join(sorted(searched))
            )
        if self.isNull():
            return tr("ui.banner_unreadable").format(path=self.path)
        return None
