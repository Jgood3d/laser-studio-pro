"""Images des modèles de la bibliothèque : l'aperçu fourni, sinon le SVG
dessiné sur fond blanc."""
from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

# Taille maxi (px) des vignettes calculées : au-delà, inutile pour la grille.
THUMBNAIL_MAX = 480


def render_svg(svg_data, max_px):
    """Image du SVG (chemin ou octets), dans un carré de `max_px` pixels au
    plus, proportions gardées, sur fond blanc. Image nulle si illisible."""
    renderer = QSvgRenderer(QByteArray(svg_data)) if isinstance(svg_data, (bytes, bytearray)) \
        else QSvgRenderer(svg_data)
    if not renderer.isValid():
        return QImage()
    size = renderer.defaultSize()
    w, h = max(size.width(), 1), max(size.height(), 1)
    scale = max_px / max(w, h)
    image = QImage(max(1, round(w * scale)), max(1, round(h * scale)), QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, image.width(), image.height()))
    painter.end()
    return image


def item_image(item, max_px=THUMBNAIL_MAX):
    """Image d'un modèle (LibraryItem) : son aperçu, réduit à `max_px` au plus,
    sinon le SVG dessiné."""
    if item.preview_path:
        image = QImage(item.preview_path)
        if not image.isNull():
            if max(image.width(), image.height()) > max_px:
                image = image.scaled(max_px, max_px, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
            return image
    return render_svg(item.svg_path, max_px)
