"""Actions de la barre d'outils sur l'image de l'onglet affiché.

    image_actions = ImageToolbarActions(app_actions, current_tab=tabs.currentWidget, dialogs=dialogs)
    image_actions.add(separation_tab, has_image=separation.has_image,
                      rotate=..., clear=separation.clear)
    tabs.currentChanged.connect(image_actions.update_state)

« Pivoter », « Supprimer » et les miroirs sont partagés par la barre d'outils
et les barres flottantes des onglets d'image (Graver une image, Séparation,
PNG ⇒ SVG) : ils agissent sur l'image de l'onglet affiché, et sont grisés
quand cet onglet n'a pas d'image.
"""
from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QObject

from laser_studio.i18n import tr


@dataclass
class ImageTarget:
    """Ce que les actions font de l'image d'un onglet.

    has_image() : une image est chargée ; rotate(clockwise) : la pivote d'un
    quart de tour ; clear() : la retire. `confirm_clear` : demander
    confirmation avant clear() (False si clear() la demande elle-même) ;
    `mirrors` : les miroirs de gravure s'appliquent à cette image."""
    has_image: Callable[[], bool]
    rotate: Callable[[bool], None]
    clear: Callable[[], None]
    confirm_clear: bool = True
    mirrors: bool = True


class ImageToolbarActions(QObject):
    """`actions` : AppActions ; current_tab() : onglet affiché ; `dialogs` :
    UserDialogs (confirmation de la suppression)."""

    def __init__(self, actions, *, current_tab, dialogs, parent=None):
        super().__init__(parent)
        self.actions = actions
        self._current_tab = current_tab
        self.dialogs = dialogs
        self._targets = {}

    def add(self, tab, **target):
        """Onglet `tab` dont les actions transforment l'image (voir ImageTarget)."""
        self._targets[tab] = ImageTarget(**target)

    def current(self):
        """ImageTarget de l'onglet affiché, ou None pour un onglet sans image."""
        return self._targets.get(self._current_tab())

    def update_state(self, *_args):
        """Actions actives seulement si l'onglet affiché a une image chargée ;
        miroirs grisés là où ils ne servent pas (PNG ⇒ SVG). Appelée au
        changement d'onglet, au chargement et à la suppression d'une image."""
        target = self.current()
        enabled = bool(target and target.has_image())
        self.actions.set_image_actions_enabled(enabled)
        self.actions.set_mirrors_enabled(enabled and target.mirrors)

    def rotate(self, clockwise):
        target = self.current()
        if target is not None:
            target.rotate(clockwise)

    def delete(self):
        """Retire l'image de l'onglet affiché, après confirmation."""
        target = self.current()
        if target is None:
            return
        if target.confirm_clear and not self.dialogs.confirm_yes_no(tr("image.delete_title"),
                                                                    tr("image.delete_question")):
            return
        target.clear()
