#!/usr/bin/env python3
"""Captures d'écran de tous les onglets, pages de réglages et boîtes.

    python tools/screenshots.py               # sur l'écran (rendu exact)
    python tools/screenshots.py --offscreen   # sans écran (CI, SSH...)

Lance la vraie fenêtre (1600 x 980), charge des images d'exemple de docs/
(gravure, vectorisation, séparation), génère le G-Code, puis enregistre
une image par onglet, par page du menu Paramètres et par boîte de
dialogue dans docs/screenshots/. Les fenêtres s'ouvrent quelques secondes
à l'écran : ne pas y toucher pendant la capture.

Les réglages de l'application (thème, langue, profils...) ne sont pas
ceux de l'utilisateur : la capture travaille dans un dossier de
configuration temporaire, avec les valeurs par défaut.

Sans écran (--offscreen), les emojis et les icônes du thème du système
peuvent manquer.
"""

import argparse
import os
import re
import sys
import tempfile
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "screenshots")
SAMPLE_IMAGE = os.path.join(ROOT, "docs", "gravure-test-original.jpg")
SEPARATION_IMAGE = os.path.join(ROOT, "docs", "result-color-layer.jpg")
WINDOW_SIZE = (1600, 980)
# Pages du menu Paramètres (clés de show_settings_window).
SETTINGS_PAGES = ("machine_params", "machine", "grbl", "test_matrix")


def slug(text):
    """« Visualisation 2D G-Code » -> "visualisation-2d-g-code"."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--offscreen", action="store_true", help="capture sans écran"
    )
    parser.add_argument(
        "--output", default=OUTPUT, help="dossier (défaut : %(default)s)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = tempfile.mkdtemp(prefix="lsp-screenshots-")
    os.environ.update(XDG_CONFIG_HOME=config, XDG_DATA_HOME=config)
    # Avertissements de Qt sans conséquence sous Wayland (focus des champs).
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland.textinput=false")
    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, ROOT)
    os.makedirs(args.output, exist_ok=True)

    from unittest import mock

    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QMessageBox

    app = QApplication([])
    from app_utils import find_resource
    from ui.app.theme import apply_saved_theme, install_breeze_icon_theme

    install_breeze_icon_theme()
    apply_saved_theme(app)
    app.setWindowIcon(QIcon(find_resource("laser_studio_pro_512.png")))
    import main_window

    window = main_window.FullLaserStudio()
    apply_saved_theme(app)
    window.resize(*WINDOW_SIZE)
    window.show()

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def shot(widget, name):
        pump(0.4)
        widget.grab().save(os.path.join(args.output, name + ".png"))
        print("  ", name)

    # Les boîtes de message (confirmations, alertes) répondent « Oui »
    # toutes seules : la capture ne doit jamais attendre un clic.
    for name in ("information", "warning", "question", "critical"):
        mock.patch.object(
            QMessageBox, name, return_value=QMessageBox.StandardButton.Yes
        ).start()

    pump(0.5)
    print("Préparation : image d'exemple, G-Code, vectorisation, séparation")
    window.load_image_from_path(SAMPLE_IMAGE)
    pump(1.5)
    window.generate_job()
    end = time.time() + 120
    while window._last_gcode_text is None and time.time() < end:
        pump(0.2)
    pump(1.0)
    window.png2svg_widget._load_image_path(SAMPLE_IMAGE)
    pump(1.5)
    window.separation_load_path(SEPARATION_IMAGE)
    pump(1.5)

    print("Onglets")
    tabs = window.main_tabs_view
    for index in range(tabs.count()):
        tabs.setTabVisible(index, True)
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        name = f"{index + 1:02d}-onglet-{slug(tabs.tabText(index))}"
        shot(window, name)

    print("Pages de réglages")
    for number, kind in enumerate(SETTINGS_PAGES, start=10):
        window.show_settings_window(kind)
        settings = window._settings_windows[kind]
        shot(settings, f"{number}-page-{slug(settings.windowTitle())}")
        settings.close()

    print("Boîtes de dialogue")
    from ui.about import AboutDialog
    from ui.buy_me_a_coffee import BuyMeACoffeeDialog
    from ui.dialogs.box_generator import BoxGeneratorDialog
    from ui.dialogs.nesting import NestingDialog
    from ui.support import SupportDialog

    bed = (window.spin_machine_w.value(), window.spin_machine_h.value())
    dialogs = (
        AboutDialog(window),
        SupportDialog(window),
        BuyMeACoffeeDialog(window),
        BoxGeneratorDialog(window, window.layer_manager.layers, *bed, None),
        NestingDialog(window, *bed, 0, 0),
    )
    for number, dialog in enumerate(dialogs, start=20):
        dialog.show()
        shot(dialog, f"{number}-boite-{slug(dialog.windowTitle())}")
        dialog.close()

    print(f"Terminé : {args.output}")
    # Sortie directe : pas de question « Enregistrer avant de quitter ? ».
    os._exit(0)


if __name__ == "__main__":
    main()
