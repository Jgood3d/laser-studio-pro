"""Impression des feuilles de calibration de la caméra, à l'échelle réelle.

    print_sheets(self, tr("camera.print.board_title"), build_pages, landscape=True)

`build_pages(largeur_mm, hauteur_mm)` reçoit la taille de la zone imprimable
de l'imprimante choisie et renvoie les pages (camera/print_layout.py). Les
motifs sont dessinés en vectoriel, en millimètres : aucune mise à l'échelle,
à condition d'imprimer à 100 % (taille réelle). « Imprimer dans un fichier
PDF » est proposé par la boîte d'impression du système.
"""
from __future__ import annotations

from typing import Callable, List

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPageLayout, QPageSize, QPainter, QPen
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

from laser_studio.camera.print_layout import Page
from laser_studio.i18n import tr


def _new_printer(title: str, landscape: bool) -> QPrinter:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(
        QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait
    )
    printer.setDocName(title)
    return printer


def print_sheets(
    parent,
    title: str,
    build_pages: Callable[[float, float], List[Page]],
    landscape: bool = False,
) -> bool:
    """Ouvre la boîte d'impression puis imprime les pages. Renvoie True si
    l'impression a été lancée."""
    printer = _new_printer(title, landscape)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(title)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    return _render(parent, title, printer, build_pages)


def save_sheets_pdf(
    parent,
    title: str,
    build_pages: Callable[[float, float], List[Page]],
    default_name: str,
    landscape: bool = False,
) -> bool:
    """Enregistre les pages dans un PDF A4 à l'échelle réelle (à imprimer
    plus tard à 100 %). Renvoie True si le fichier a été écrit."""
    path, _ = QFileDialog.getSaveFileName(parent, title, default_name, "PDF (*.pdf)")
    if not path:
        return False
    printer = _new_printer(title, landscape)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    if not _render(parent, title, printer, build_pages):
        return False
    QMessageBox.information(parent, title, tr("camera.print.pdf_saved").format(path=path))
    return True


def _render(parent, title: str, printer: QPrinter, build_pages) -> bool:
    """Dessine les pages sur `printer` (imprimante ou fichier PDF)."""
    # Zone imprimable de l'imprimante choisie (papier et marges ont pu changer).
    area = printer.pageRect(QPrinter.Unit.Millimeter)
    try:
        pages = build_pages(area.width(), area.height())
    except ValueError as error:
        QMessageBox.warning(parent, title, str(error))
        return False
    if not pages:
        return False

    painter = QPainter()
    if not painter.begin(printer):
        QMessageBox.warning(parent, title, tr("camera.print.error"))
        return False
    try:
        px_per_mm = printer.resolution() / 25.4
        for index, page in enumerate(pages):
            if index:
                printer.newPage()
            _draw_page(painter, page, px_per_mm)
    finally:
        painter.end()
    return True


def _draw_page(painter: QPainter, page: Page, px_per_mm: float) -> None:
    """Dessine les éléments d'une page (mm → pixels de l'imprimante)."""
    def px(value):
        return value * px_per_mm

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    for item in page.items:
        kind = item[0]
        if kind == "rect":
            _, x, y, w, h = item
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("black")))
            painter.drawRect(QRectF(px(x), px(y), px(w), px(h)))
        elif kind == "frame":
            _, x, y, w, h = item
            pen = QPen(QColor(110, 110, 110), max(1.0, px(0.15)), Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(px(x), px(y), px(w), px(h)))
        elif kind == "line":
            _, x1, y1, x2, y2 = item
            painter.setPen(QPen(QColor("black"), max(1.0, px(0.2))))
            painter.drawLine(int(px(x1)), int(px(y1)), int(px(x2)), int(px(y2)))
        elif kind == "text":
            _, x, y, w, text, size_pt = item
            painter.setPen(QPen(QColor("black")))
            font = QFont(painter.font())
            font.setPointSizeF(size_pt)
            painter.setFont(font)
            painter.drawText(
                QRectF(px(x), px(y), px(w), px(14.0)),
                int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.AlignmentFlag.AlignTop) | int(Qt.TextFlag.TextWordWrap),
                text,
            )
