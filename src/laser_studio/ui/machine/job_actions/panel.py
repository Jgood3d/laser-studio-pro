"""Panneau des actions de job : cadrage, zéro, aller au zéro, répétition, puis les macros de l'utilisateur."""

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPen, QPolygonF
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QPushButton, QStyle, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.utils import painted_icon, themed_icon, tool_button


class JobActionsPanel(QGroupBox):
    """Actions sur le job courant, à droite du panneau de pilotage.

    Comme JogControlPanel, il ne pilote pas la machine : chaque bouton émet
    un signal, auquel la fenêtre (plus tard un contrôleur) s'abonne.

        panel = JobActionsPanel()
        panel.frame_requested.connect(engraver.frame)

    Les boutons sont construits à partir d'une liste d'actions (voir
    _actions). Dessous, un bouton par macro de l'utilisateur (set_macros) :
    un clic émet macro_requested(rang) ; le bouton « Macros… » émet
    manage_macros_requested.
    """

    frame_requested = pyqtSignal()
    set_work_zero_requested = pyqtSignal()
    go_to_work_zero_requested = pyqtSignal()
    repeat_job_requested = pyqtSignal()
    macro_requested = pyqtSignal(int)
    manage_macros_requested = pyqtSignal()

    # Boutons de macros par ligne, et leur largeur maximale (px).
    MACRO_COLUMNS = 2
    MACRO_BUTTON_MAX_WIDTH = 140

    def __init__(self, parent=None):
        super().__init__(tr("ui.job_actions_box"), parent)
        self.buttons = {}
        self._connected = True
        self._repeat_allowed = False
        grid = QGridLayout(self)
        grid.setSpacing(4)
        for col, (name, icon, key, signal) in enumerate(self._actions()):
            button = tool_button(icon, tr(key))
            button.clicked.connect(signal)
            self.buttons[name] = button
            grid.addWidget(button, 0, col)
        manage = tool_button(themed_icon(self, QIcon.ThemeIcon.DocumentProperties,
                                         QStyle.StandardPixmap.SP_FileDialogDetailedView), tr("macros.manage_tip"))
        manage.clicked.connect(self.manage_macros_requested)
        self.buttons["macros"] = manage
        grid.addWidget(manage, 0, len(self.buttons) - 1)
        # Macros de l'utilisateur sous les actions, puis place libre.
        self.macro_area = QWidget()
        self._macro_grid = QGridLayout(self.macro_area)
        self._macro_grid.setContentsMargins(0, 0, 0, 0)
        self._macro_grid.setSpacing(4)
        self.macro_buttons = []
        grid.addWidget(self.macro_area, 1, 0, 1, len(self.buttons))
        grid.setRowStretch(2, 1)
        # Rien à répéter tant qu'aucun job n'a été envoyé.
        self.set_repeat_enabled(False)

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Déverrouille les actions et les boutons des macros si le graveur est connecté. Le bouton
        « Macros… » reste toujours actif : on prépare ses macros sans graveur branché."""
        self._connected = connected
        for name, button in self.buttons.items():
            if name not in ("macros", "repeat"):
                button.setEnabled(connected)
        self.macro_area.setEnabled(connected)
        self._update_repeat()

    def set_repeat_enabled(self, enabled):
        """Active « Répéter le dernier job » une fois un job envoyé (et le graveur connecté)."""
        self._repeat_allowed = enabled
        self._update_repeat()

    def is_connected(self):
        return self._connected

    def _update_repeat(self):
        self.buttons["repeat"].setEnabled(self._connected and self._repeat_allowed)

    def set_macros(self, entries):
        """Boutons des macros : `entries` = (rang, nom, infobulle, allume le laser). Le rang est renvoyé par
        macro_requested. Une macro qui allume le laser est marquée d'un ⚠ ."""
        for button in self.macro_buttons:
            self._macro_grid.removeWidget(button)
            button.deleteLater()
        self.macro_buttons = []
        for position, (index, name, tooltip, laser) in enumerate(entries):
            label = ("⚠ " if laser else "") + name
            button = QPushButton()
            # Nom long : coupé (« … ») pour ne pas élargir le panneau ; le nom entier est dans l'infobulle.
            button.setMaximumWidth(self.MACRO_BUTTON_MAX_WIDTH)
            button.setText(button.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight,
                                                           self.MACRO_BUTTON_MAX_WIDTH - 16))
            button.setToolTip(f"{name}\n{tooltip}" if tooltip and tooltip != name else name)
            if laser:
                button.setToolTip(button.toolTip() + "\n" + tr("macros.laser_tip"))
            button.clicked.connect(lambda _checked=False, i=index: self.macro_requested.emit(i))
            self._macro_grid.addWidget(button, position // self.MACRO_COLUMNS, position % self.MACRO_COLUMNS)
            self.macro_buttons.append(button)
        self.macro_area.setVisible(bool(entries))

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
