"""Fenêtre de comparaison des algorithmes de tramage."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

# Vignettes par ligne.
COLUMNS = 5


class DitherComparisonDialog(QDialog):
    """Grille de vignettes, une par algorithme de tramage.

    Elle ne calcule rien : elle reçoit les vignettes déjà tramées (tableaux
    numpy en niveaux de gris, uint8) et émet `algorithm_chosen` avec le nom
    de l'algorithme cliqué, puis se ferme :

        dialog = DitherComparisonDialog(self, [("Stucki", tableau), ...])
        dialog.algorithm_chosen.connect(self.combo_algo.setCurrentText)
        dialog.exec()
    """

    # Nom de l'algorithme choisi, tel qu'il apparaît dans la liste.
    algorithm_chosen = pyqtSignal(str)

    def __init__(self, parent, thumbnails):
        super().__init__(parent)
        self.setWindowTitle(tr("image.compare_dialog_title"))
        grid = QGridLayout(self)
        for index, (algorithm, array) in enumerate(thumbnails):
            grid.addWidget(
                self._cell(algorithm, array),
                index // COLUMNS,
                index % COLUMNS,
            )

    def _cell(self, algorithm, array):
        """Vignette tramée, et le bouton qui choisit cet algorithme."""
        cell = QWidget()
        layout = QVBoxLayout(cell)
        height, width = array.shape
        image = QImage(
            array.tobytes(),
            width,
            height,
            width,
            QImage.Format.Format_Grayscale8,
        )
        thumbnail = QLabel()
        thumbnail.setPixmap(QPixmap.fromImage(image))
        thumbnail.setStyleSheet("border: 1px solid #555;")
        button = QPushButton(algorithm)
        button.clicked.connect(lambda _checked: self._choose(algorithm))
        layout.addWidget(thumbnail)
        layout.addWidget(button)
        return cell

    def _choose(self, algorithm):
        self.algorithm_chosen.emit(algorithm)
        self.accept()
