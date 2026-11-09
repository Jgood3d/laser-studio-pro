"""Actions de job : cadrage, zéro, aller au zéro, répétition du dernier job.

Version provisoire : ces boutons deviendront JobActionsPanel
(ui/machine/job_actions/), construit à partir d'une liste d'actions.
"""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QIcon, QPen, QPolygonF
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QStyle

from i18n import tr
from ui_utils import painted_icon, themed_icon, tool_button


class JobActionsMixin:
    def _build_job_actions_box(self):
        """Cadre des actions de job, à droite du panneau de pilotage."""
        box = QGroupBox(tr("ui.job_actions_box"))
        btn_frame = tool_button(self._frame_icon(), tr("ui.frame"))
        btn_frame.clicked.connect(self.run_frame)
        btn_zero_xy = tool_button(self._crosshair_icon(), tr("ui.zero_work"))
        btn_zero_xy.clicked.connect(
            lambda: self.send_manual_direct_cmd("G92 X0 Y0")
        )
        btn_go_zero = tool_button(
            self._crosshair_icon(with_arrow=True), tr("ui.go_zero")
        )
        btn_go_zero.clicked.connect(
            lambda: self.send_manual_direct_cmd("G0 X0 Y0")
        )
        self.btn_repeat_last_job = tool_button(
            themed_icon(
                self,
                QIcon.ThemeIcon.MediaPlaylistRepeat,
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("ui.repeat_last_job"),
        )
        self.btn_repeat_last_job.clicked.connect(self.repeat_last_job)
        self.btn_repeat_last_job.setEnabled(False)

        grid = QGridLayout(box)
        grid.setSpacing(4)
        for col, button in enumerate(
            (
                btn_frame,
                btn_zero_xy,
                btn_go_zero,
                self.btn_repeat_last_job,
            )
        ):
            grid.addWidget(button, 0, col)
        # Boutons en haut, place libre en dessous.
        grid.setRowStretch(1, 1)
        return box

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
