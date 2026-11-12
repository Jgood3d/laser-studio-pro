"""Panneau machine sous les onglets : connexion, pilotage, jobs, DRO,
statistiques du job, console."""

from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.machine.connection import ConnectionPanel
from laser_studio.ui.machine.console import DirectConsolePanel
from laser_studio.ui.machine.controls import JogControlPanel
from laser_studio.ui.machine.dro import DroPanel
from laser_studio.ui.machine.job_actions import JobActionsPanel
from laser_studio.ui.machine.job_stats import JobStatsPanel


class MachinePanel(QWidget):
    """Assemble les panneaux de la machine, sous les onglets.

    Une rangée de six cadres (position du job, connexion, pilotage, actions
    de job, DRO, statistiques du job), puis la progression de la gravure
    et la console directe.

    Il ne pilote pas la machine, et n'a pas de signaux à lui : chaque
    sous-panneau émet les siens, auxquels la fenêtre (plus tard un
    contrôleur) s'abonne directement :

        panel = MachinePanel(job_position_box, ports_model, max_speed=6000)
        panel.connection_panel.connect_requested.connect(laser.toggle)
        panel.jog_panel.jog_requested.connect(laser.jog_move)
        panel.dro_panel.unlock_requested.connect(laser.unlock_alarm)
        panel.set_connected(False)

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
        self.dro_panel = DroPanel()
        self.job_stats_panel = JobStatsPanel()
        self.progress_bar = self._progress_bar()
        self.console_panel = DirectConsolePanel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._machine_row())
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.console_panel)
        # Place libre en bas, pas dans les cadres
        layout.addStretch()

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Verrouille les commandes tant que le graveur n'est pas connecté.

        Le DRO et la position du job restent lisibles ; le bouton de
        connexion affiche l'état.
        """
        self.connection_panel.set_connected(connected)
        for panel in (
            self.jog_panel,
            self.job_actions_panel,
            self.console_panel,
        ):
            panel.set_connected(connected)

    # -- construction

    def _machine_row(self):
        """Six cadres côte à côte.

        Position du job à gauche, puis la connexion, le pilotage et les
        actions de job, et le DRO et les statistiques du job à droite. La
        connexion, le pilotage et les actions gardent leur taille naturelle
        (leurs boutons ne grandissent pas) ; la place libre est partagée
        entre la position du job, le DRO, qui sinon serait coupé, et les
        statistiques.
        """
        self._fit_box_width(
            self.dro_panel, self.dro_panel.minimum_content_width()
        )
        self._fit_box_width(self.job_position_box)
        self._fit_box_width(self.connection_panel)
        self._fit_box_width(self.jog_panel)
        self._fit_box_width(self.job_actions_panel)
        self._fit_box_width(self.job_stats_panel)
        machine_row = QHBoxLayout()
        machine_row.addWidget(self.job_position_box, 1)
        machine_row.addWidget(self.connection_panel, 0)
        machine_row.addWidget(self.jog_panel, 0)
        machine_row.addWidget(self.job_actions_panel, 0)
        machine_row.addWidget(self.dro_panel, 1)
        machine_row.addWidget(self.job_stats_panel, 1)
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
        sans cette largeur, un cadre étroit (le DRO) voit son titre coupé à
        droite.
        """
        font = QFont(box.font())
        font.setBold(True)
        title_px = QFontMetrics(font).horizontalAdvance(box.title()) + 44
        box.setMinimumWidth(
            max(box.minimumSizeHint().width(), title_px, content_px)
        )
