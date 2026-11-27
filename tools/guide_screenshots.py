#!/usr/bin/env python3
"""Captures d'écran du guide utilisateur (docs/guide/), sur un parcours réel avec le graveur simulé.

    python tools/guide_screenshots.py               # sur l'écran (rendu exact)
    python tools/guide_screenshots.py --offscreen   # sans écran

Comme tools/screenshots.py : vraie fenêtre, configuration temporaire (réglages de l'utilisateur intacts), thème
Dusk. En plus, le parcours des exemples du guide est rejoué : catalogue des machines, connexion au graveur
SIMULÉ (jamais à une vraie machine, même branchée), homing, médaille de la bibliothèque jusqu'à la gravure,
photo, porte-clés. Les fenêtres qui attendent une réponse (bibliothèque, fiche du modèle, confirmation) sont
capturées puis validées automatiquement. Ne pas toucher aux fenêtres pendant la capture.
"""

import argparse
import os
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
OUTPUT = os.path.join(REPO, "docs", "guide", "images")
PHOTO = os.path.join(REPO, "docs", "gravure-test-original.jpg")
WINDOW_SIZE = (1600, 980)
MEDAL = "medaille-sportive-modele-1"
COMPETITION = "Régate de printemps 2026"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offscreen", action="store_true", help="capture sans écran")
    parser.add_argument("--output", default=OUTPUT, help="dossier (défaut : %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()
    config = tempfile.mkdtemp(prefix="lsp-guide-")
    # Graveur simulé, 20 fois plus rapide : la connexion et la gravure se font sans machine.
    os.environ.update(XDG_CONFIG_HOME=config, XDG_DATA_HOME=config, LASER_STUDIO_SIMULATION="20")
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland.textinput=false")
    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, os.path.dirname(ROOT))
    os.makedirs(args.output, exist_ok=True)

    from unittest import mock

    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

    app = QApplication([])
    from laser_studio.core.paths import find_resource
    from laser_studio.core.preferences import ui_preferences
    from laser_studio.ui.app.theme import apply_saved_theme, install_breeze_icon_theme

    install_breeze_icon_theme()
    ui_preferences().set("app_theme", "dusk")
    apply_saved_theme(app)
    app.setWindowIcon(QIcon(find_resource("laser_studio_pro_512.png")))
    from laser_studio.grbl.simulator import SIMULATED_PORT
    from laser_studio.i18n import tr
    from laser_studio.ui.app import main_window
    from laser_studio.ui.dialogs.countdown import CountdownDialog
    from laser_studio.ui.dialogs.first_steps import FirstStepsDialog
    from laser_studio.ui.dialogs.generators import GeneratorsDialog
    from laser_studio.ui.dialogs.library.dialog import LibraryItemDialog
    from laser_studio.ui.dialogs.machine_catalog import MachineCatalogDialog

    window = main_window.FullLaserStudio()
    apply_saved_theme(app)
    window.resize(*WINDOW_SIZE)
    window.show()

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def wait(condition, timeout=60.0):
        end = time.time() + timeout
        while not condition() and time.time() < end:
            pump(0.1)
        return condition()

    def shot(widget, name):
        pump(0.5)
        image = widget.grab().toImage()
        # Une fenêtre peut être capturée plus haute que son contenu (bande noire en bas) : on la retire.
        bottom = image.height()
        while bottom > 1 and all(image.pixelColor(x, bottom - 1).value() == 0
                                 for x in range(0, image.width(), max(1, image.width() // 40))):
            bottom -= 1
        image.copy(0, 0, image.width(), bottom).save(os.path.join(args.output, name + ".png"))
        print("  ", name)

    # Questions Oui / Non (confirmation d'envoi, suppression…) : la fenêtre est capturée si un nom est prévu,
    # puis « Oui ». Les simples messages répondent tout seuls.
    question_names = []

    def question(parent, title, text, buttons=QMessageBox.StandardButton.Yes, default=None):
        if question_names:
            box = QMessageBox(QMessageBox.Icon.Question, title, text, buttons, parent)
            box.show()
            shot(box, question_names.pop(0))
            box.close()
        return QMessageBox.StandardButton.Yes

    mock.patch.object(QMessageBox, "question", question).start()
    for name in ("information", "warning", "critical"):
        mock.patch.object(QMessageBox, name, return_value=QMessageBox.StandardButton.Yes).start()

    # Fenêtres modales : un « scénario » par type de fenêtre, qui la remplit, la capture et la valide.
    scenarios = {}

    def exec_dialog(dialog):
        dialog.show()
        pump(0.6)
        for kind, scenario in list(scenarios.items()):
            if isinstance(dialog, kind):
                accepted = scenario(dialog)
                dialog.close()
                return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
        dialog.close()
        return QDialog.DialogCode.Rejected

    mock.patch.object(QDialog, "exec", exec_dialog).start()
    panel = window.machine_panel

    print("Premier réglage")
    first_steps = FirstStepsDialog(True, window)
    first_steps.show()
    shot(first_steps, "01-premiers-pas")
    first_steps.close()
    window.tab_machine_params.catalog_requested.emit()
    pump(1.0)
    catalog = next(w for w in QApplication.topLevelWidgets() if isinstance(w, MachineCatalogDialog) and w.isVisible())
    shot(catalog, "02-catalogue-des-machines")
    catalog.close()
    controller = window.window_controller
    controller.show_settings_window("machine_params")
    settings = controller.forms._settings_windows["settings"]
    shot(settings, "03-parametres-du-graveur")
    controller.show_settings_window("grbl")
    shot(settings, "04-configuration-grbl")
    settings.close()

    # Connexion au graveur simulé : le port simulé est choisi d'office, jamais un vrai port.
    window.engraver.refresh_ports()
    combo = panel.connection_panel.ports_combo
    combo.setCurrentIndex(next(i for i in range(combo.count()) if combo.itemText(i).startswith(SIMULATED_PORT)))
    window.engraver.toggle_connection()
    wait(window.connection.is_connected)
    window.bottom_panel.show_page("machine")
    window.engraver.home()
    wait(lambda: window.connection.homed and not window.connection.is_busy())
    window.tabs.show(window.tab_vector_editor)
    shot(window, "05-graveur-connecte")

    print("Calques, matériaux, matrice de test")
    window.tabs.show(window.layers_tab)
    shot(window, "06-calques-et-materiaux")
    controller.show_settings_window("test_matrix")
    matrix = controller.forms._settings_windows["test_matrix"]
    shot(matrix, "07-matrice-de-test")
    matrix.close()

    print("Médaille : de la bibliothèque à la gravure")

    def library_scenario(dialog):
        page = dialog.page("library")
        dialog.list.setCurrentRow(dialog._keys.index("library"))
        grid = page.grid
        row = next(r for r in range(grid.count()) if MEDAL in str(grid.item(r).data(256)))
        grid.setCurrentRow(row)
        shot(dialog, "08-bibliotheque")
        item = page.current_item()
        details = LibraryItemDialog(page, item, page._icon(item))
        details.show()
        pump(1.0)
        field = next(iter(details._text_edits.values()))[0]
        field.setText(COMPETITION)
        pump(1.5)
        shot(details, "09-fiche-du-modele")
        page._import(item, details.variants(), details.texts())
        details.close()
        return True

    scenarios[GeneratorsDialog] = library_scenario

    def countdown_scenario(dialog):
        """Compte à rebours avant la gravure : capturé à mi-chemin (sans attendre la fin), puis validé."""
        dialog._timer.stop()
        dialog.ring.set_remaining(3.4)
        dialog.detail.setText(tr("countdown.detail").format(seconds=4))
        shot(dialog, "12b-compte-a-rebours")
        return True

    scenarios[CountdownDialog] = countdown_scenario
    window.tabs.show(window.tab_vector_editor)
    window.vector_generators.open_generators("library")
    pump(1.0)
    shot(window, "10-medaille-dans-l-editeur")
    generated = []
    window.job.generated.connect(lambda *_result: generated.append(True))
    window.job.generate()
    wait(lambda: generated, 120)
    window.tabs.show(window.tab_vector_2d)
    shot(window, "11-medaille-apercu-2d")
    question_names.append("12-confirmation-avant-gravure")
    window.engraver.send_job()
    wait(lambda: window.engraver._acked > 300, 60)
    shot(window, "13-gravure-en-cours")
    window.engraver.emergency_stop()
    wait(lambda: not window.connection.is_streaming(), 20)
    pump(1.0)

    print("Photo")
    window.engraver.unlock()                 # alarme laissée par l'arrêt d'urgence de la médaille
    wait(lambda: not window.connection.is_busy(), 10)
    window.vector_editor.delete_all()
    window.image.load_path(PHOTO)
    pump(2.0)
    window.tabs.show(window.tab_previews)
    shot(window, "14-photo-reglages")
    del generated[:]
    window.job.generate()
    wait(lambda: generated, 180)
    window.tabs.show(window.tab_vector_2d)
    shot(window, "15-photo-apercu-2d")

    print("Porte-clés")
    window.image_actions.delete()
    pump(0.5)

    def keychain_scenario(dialog):
        dialog.list.setCurrentRow(dialog._keys.index("keychain"))
        pump(1.5)
        shot(dialog, "16-generateur-porte-cles")
        return False

    scenarios[GeneratorsDialog] = keychain_scenario
    window.tabs.show(window.tab_vector_editor)
    window.vector_generators.open_generators("keychain")

    print(f"Terminé : {args.output}")
    window.connection.shutdown()
    os._exit(0)          # pas de question « Enregistrer avant de quitter ? »


if __name__ == "__main__":
    main()
