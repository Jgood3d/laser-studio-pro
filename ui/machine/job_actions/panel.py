"""Panneau des actions de job : cadrage, zéro, aller au zéro, répétition."""

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPen, QPolygonF
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QStyle

from i18n import tr
from ui_utils import painted_icon, themed_icon, tool_button


class JobActionsPanel(QGroupBox):
    """Actions sur le job courant, à droite du panneau de pilotage.

    Comme JogControlPanel, il ne pilote pas la machine : chaque bouton émet
    un signal, auquel la fenêtre (plus tard un contrôleur) s'abonne.

        panel = JobActionsPanel()
        panel.frame_requested.connect(laser.run_frame)

    Les boutons sont construits à partir d'une liste d'actions (voir
    _actions) : les macros de l'utilisateur pourront s'y ajouter.
    """

    frame_requested = pyqtSignal()
    set_work_zero_requested = pyqtSignal()
    go_to_work_zero_requested = pyqtSignal()
    repeat_job_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(tr("ui.job_actions_box"), parent)
        self.buttons = {}
        grid = QGridLayout(self)
        grid.setSpacing(4)
        for col, (name, icon, key, signal) in enumerate(self._actions()):
            button = tool_button(icon, tr(key))
            button.clicked.connect(signal)
            self.buttons[name] = button
            grid.addWidget(button, 0, col)
        # Boutons en haut, place libre en dessous.
        grid.setRowStretch(1, 1)
        # Rien à répéter tant qu'aucun job n'a été envoyé.
        self.set_repeat_enabled(False)

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Déverrouille les actions si le graveur est connecté."""
        self.setEnabled(connected)

    def set_repeat_enabled(self, enabled):
        """Active « Répéter le dernier job » une fois un job envoyé."""
        self.buttons["repeat"].setEnabled(enabled)

    # -- construction

    def _actions(self):
        """Liste des actions : (nom, icône, clé de l'infobulle, signal)."""
        return (
            ("frame", self._frame_icon(), "ui.frame", self.frame_requested),
            (
                "set_work_zero",
                self._crosshair_icon(),
                "ui.zero_work",
                self.set_work_zero_requested,
            ),
            (
                "go_to_work_zero",
                self._crosshair_icon(with_arrow=True),
                "ui.go_zero",
                self.go_to_work_zero_requested,
            ),
            (
                "repeat",
                themed_icon(
                    self,
                    QIcon.ThemeIcon.MediaPlaylistRepeat,
                    QStyle.StandardPixmap.SP_BrowserReload,
                ),
                "ui.repeat_last_job",
                self.repeat_job_requested,
            ),
        )

    # -- icônes

    def _frame_icon(self):
        """Cadrage : rectangle en pointillés avec ses quatre coins marqués."""

        def draw(painter, color):
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawRect(6, 6, 20, 20)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for x, y in ((3, 3), (23, 3), (3, 23), (23, 23)):
                painter.drawRect(x, y, 6, 6)

        return painted_icon(self.palette(), draw)

    def _crosshair_icon(self, with_arrow=False):
        """Origine de travail : viseur.

        `with_arrow` : petite flèche qui y va (« Go zéro »).
        """

        def draw(painter, color):
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = 20 if with_arrow else 16
            painter.drawEllipse(QPointF(center, center), 7, 7)
            painter.drawLine(
                QPointF(center - 11, center), QPointF(center + 11, center)
            )
            painter.drawLine(
                QPointF(center, center - 11), QPointF(center, center + 11)
            )
            if with_arrow:
                painter.drawLine(QPointF(2, 2), QPointF(11, 11))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawPolygon(
                    QPolygonF(
                        [QPointF(13, 13), QPointF(5, 11), QPointF(11, 5)]
                    )
                )

        return painted_icon(self.palette(), draw)
