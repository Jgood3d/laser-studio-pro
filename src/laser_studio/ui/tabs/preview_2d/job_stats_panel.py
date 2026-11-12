"""Statistiques du job généré : lignes, puissance moyenne, temps estimé."""

from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from laser_studio.i18n import tr


class JobStatsPanel(QGroupBox):
    """Nombre de lignes, puissance moyenne et temps estimé du job.

    Simple affichage, à droite de l'aperçu 2D : la fenêtre lui transmet les
    textes à chaque génération ou import de G-Code :

        panel = JobStatsPanel()
        panel.set_stats("Lignes : 4", "Puissance : 12 %", "Temps : 1 min")
    """

    def __init__(self, parent=None):
        super().__init__(tr("ui.job_stats_box"), parent)
        self.lines_label = QLabel(tr("ui.job_lines"))
        self.power_label = QLabel(tr("ui.job_avg_power"))
        self.time_label = QLabel(tr("ui.job_estimated_time"))
        layout = QVBoxLayout(self)
        layout.addWidget(self.lines_label)
        layout.addWidget(self.power_label)
        layout.addWidget(self.time_label)
        layout.addStretch()

    def set_stats(self, lines, power, time):
        """Textes des statistiques du job : lignes, puissance, temps."""
        self.lines_label.setText(lines)
        self.power_label.setText(power)
        self.time_label.setText(time)
