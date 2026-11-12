"""Panneau machine sous les onglets : position du job, connexion,
pilotage, actions de job."""

from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.machine.connection import ConnectionPanel
from laser_studio.ui.machine.controls import JogControlPanel
from laser_studio.ui.machine.job_actions import JobActionsPanel


class MachinePanel(QWidget):
    """Assemble les panneaux de la machine, sous les onglets.

    Une rangée de quatre cadres (position du job, connexion, pilotage,
    actions de job), puis la progression de la gravure. L'état GRBL et la
    console directe sont dans le cadre « Connexion », la position X / Y / Z
    en bas du pilotage.

    Il ne pilote pas la machine : chaque sous-panneau émet ses signaux,
    auxquels la fenêtre (plus tard un contrôleur) s'abonne directement :

        panel = MachinePanel(job_position_box, ports_model, max_speed=6000)
        panel.connection_panel.connect_requested.connect(laser.toggle)
        panel.connection_panel.unlock_requested.connect(laser.unlock_alarm)
        panel.jog_panel.jog_requested.connect(laser.jog_move)
        panel.set_connected(False)
        panel.set_status("Idle", 12.5, 30.0, 0.0)

    `job_position_box` : cadre de la position du job, construit avec
    l'onglet image, placé à gauche de la rangée. `ports_model` : modèle
    de la liste des ports, partagé avec la page des matériaux.
    """

    def __init__(self, job_position_box, ports_model, max_speed, parent=None):
        super().__init__(parent)
        self.job_position_box = job_position_box
        self.connection_panel = ConnectionPanel(ports_model)
        self.jog_panel = JogControlPanel(max_speed)
        self.job_actions_panel = JobActionsPanel()
        self.progress_bar = self._progress_bar()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._machine_row())
        layout.addWidget(self.progress_bar)
        # Place libre en bas, pas dans les cadres
        layout.addStretch()

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Verrouille les commandes tant que le graveur n'est pas connecté.

        La position du job reste modifiable ; le bouton de connexion
        affiche l'état, la console directe suit la connexion.
        """
        for panel in (
            self.connection_panel,
            self.jog_panel,
            self.job_actions_panel,
        ):
            panel.set_connected(connected)

    def set_status(self, state, x=0.0, y=0.0, z=0.0):
        """État GRBL (cadre Connexion) et position en mm (sous le pilotage).

        `state` à None (graveur déconnecté) : plus d'état ni de position
        connus, des tirets s'affichent.
        """
        self.connection_panel.set_state(state)
        self.jog_panel.set_position(None if state is None else x, y, z)

    # -- construction

    def _machine_row(self):
        """Quatre cadres côte à côte.

        Position du job à gauche, puis la connexion, le pilotage et les
        actions de job. Le pilotage et les actions gardent leur taille
        naturelle (leurs boutons ne grandissent pas) ; la place libre est
        partagée entre la position du job et la connexion (champ de la
        console directe).
        """
        for box in (
            self.job_position_box,
            self.connection_panel,
            self.jog_panel,
            self.job_actions_panel,
        ):
            self._fit_box_width(box)
        machine_row = QHBoxLayout()
        machine_row.addWidget(self.job_position_box, 1)
        machine_row.addWidget(self.connection_panel, 1)
        machine_row.addWidget(self.jog_panel, 0)
        machine_row.addWidget(self.job_actions_panel, 0)
        return machine_row

    @staticmethod
    def _progress_bar():
        """Progression de la gravure en cours, ex. « Gravure : 42% ».

        La fenêtre la fait avancer au fil des lignes de G-Code acquittées par
        le graveur ; elle reste à 100 % une fois le job terminé.
        """
        bar = QProgressBar()
        # %p : pourcentage, remplacé par Qt.
        bar.setFormat(tr("ui.burn_progress").format(pct="%p"))
        bar.setValue(0)
        return bar

    @staticmethod
    def _fit_box_width(box, content_px=0):
        """Largeur minimale d'un cadre : son titre en entier, au moins.

        `content_px` : largeur demandée par le contenu. Le thème met les
        titres de cadre en gras et les décale (marge gauche + marges
        internes), ce que Qt ne compte pas dans la taille minimale du cadre :
        sans cette largeur, un cadre étroit voit son titre coupé à droite.
        """
        font = QFont(box.font())
        font.setBold(True)
        title_px = QFontMetrics(font).horizontalAdvance(box.title()) + 44
        box.setMinimumWidth(
            max(box.minimumSizeHint().width(), title_px, content_px)
        )
