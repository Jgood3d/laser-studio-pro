"""Stencil Studio en widgets Qt (expérimental, ui/qt/) : parcours principal de la fenêtre et entrée du menu
Outils, à côté de la version web."""
import os
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))


try:
    import cv2  # noqa: F401
    from PyQt6.QtWidgets import QApplication
    from stencil_studio.controllers.service import StudioService
except ImportError:          # OpenCV ou PyQt6 absents
    StudioService = None

IMAGE = os.path.join(REPO, "src", "stencil_studio", "exemple", "girl1.png")


@unittest.skipIf(StudioService is None, "OpenCV ou PyQt6 non importables ici")
class QtDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tempfile.TemporaryDirectory()
        os.environ["XDG_DATA_HOME"] = cls.data.name
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.data.cleanup()

    def wait(self, condition, timeout=120):
        end = time.time() + timeout
        while time.time() < end and not condition():
            self.app.processEvents()
            time.sleep(0.02)
        self.assertTrue(condition())

    def test_main_path_open_preview_mode_export(self):
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        exported = []
        dialog.export_ready.connect(exported.append)
        dialog.open_path(IMAGE)
        dialog.form.widgets["exp_preview"].setChecked(False)             # sans aperçu avant export
        self.wait(lambda: dialog.result_view._pixmap is not None)
        self.assertIn("Contours :", dialog.status.text())              # statistiques complètes, comme la page
        self.assertIn("Ponts :", dialog.status.text())
        halftone = next(b for b in dialog.mode_buttons.buttons() if b.property("mode") == "halftone")
        halftone.click()
        self.assertEqual(dialog.state["output"], "halftone")
        self.assertFalse(dialog.form.boxes["Halftone dots"].isHidden())
        self.assertTrue(dialog.form.boxes["Cleanup and bridges"].isHidden())
        dialog.export_svg()
        self.wait(lambda: exported)
        with open(exported[0], encoding="utf-8") as f:
            self.assertIn("<svg", f.read())

    def test_frame_wheel_drag_rotation_preset_and_exports(self):
        from unittest import mock
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent, QWheelEvent
        from PyQt6.QtWidgets import QFileDialog
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.resize(1400, 900)
        dialog.show()
        dialog.open_path(IMAGE)
        view = dialog.source_view

        def wheel(dy, modifiers=Qt.KeyboardModifier.NoModifier):
            view.wheelEvent(QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, dy),
                                        Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.NoScrollPhase, False))
        wheel(600)                                                     # molette : cadre plus petit
        self.assertLess(view.frame()["w"], 1.0)
        self.assertEqual(dialog.state["zoom"], round(view.frame()["w"], 2))
        start, centre = view.frame()["cx"], view.rect().center()
        for handler, point in ((view.mousePressEvent, centre), (view.mouseMoveEvent, centre + QPoint(40, 0)),
                               (view.mouseReleaseEvent, centre + QPoint(40, 0))):
            handler(QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(point), QPointF(point), Qt.MouseButton.LeftButton,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.assertGreater(view.frame()["cx"], start)                  # glissé vers la droite
        wheel(-120, Qt.KeyboardModifier.AltModifier)                   # Alt + molette : rotation
        self.assertEqual((dialog.state["rot"], dialog.form.value("rot")), (1.0, 1.0))
        preset = dialog.form.widgets["preset"]
        preset.setCurrentIndex(preset.findData("silhouette"))           # style prédéfini
        self.assertEqual(dialog.state["preset"], "")
        for key, value in dialog.spec.presets["silhouette"].items():
            self.assertEqual(dialog.state[key], value, key)
        exported = []
        dialog.export_ready.connect(exported.append)
        previews = []
        # Aperçu avant export : accepté pour le DXF et le caisson, refusé ensuite (« Retour aux réglages »).
        dialog.confirm_export = lambda name, picture, out: previews.append(picture) or not previews[2:]
        dialog.export("dxf")                                            # DXF : vers Laser Studio
        self.wait(lambda: exported)
        self.assertTrue(exported[0].endswith("_cut.dxf"))
        saved = os.path.join(tempfile.mkdtemp(), "box.svg")
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(saved, "")):
            dialog.export("boxsvg")                                     # caisson : enregistré sur le disque
            self.wait(lambda: os.path.exists(saved))
        self.assertEqual(len(exported), 1)
        self.assertTrue(previews[0].lstrip().startswith("<"))          # DXF montré par son SVG avant l'export
        dialog.export("svg")                                            # « Retour aux réglages » : pas d'export
        self.wait(lambda: len(previews) == 3)
        self.app.processEvents()
        self.assertEqual(len(exported), 1)
        self.assertFalse(dialog.export_actions["png"].isEnabled())      # gravure PNG : mode Gravure seulement

    def test_subject_box_and_painted_hints(self):
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.resize(1400, 900)
        dialog.show()
        dialog.open_path(IMAGE)
        view = dialog.source_view
        scale, ox, oy = view._view()

        def drag(a, b):
            for handler, (fx, fy) in ((view.mousePressEvent, a), (view.mouseMoveEvent, b), (view.mouseReleaseEvent, b)):
                point = QPointF(ox + fx * view.iw * scale, oy + fy * view.ih * scale)
                handler(QMouseEvent(QMouseEvent.Type.MouseMove, point, point, Qt.MouseButton.LeftButton,
                                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        paint = [b for b in dialog.tool_buttons.buttons() if b.property("tool") in ("fg", "bg", "erase")]
        self.assertTrue(all(b.isHidden() for b in paint))              # repères : seulement en isolant le sujet
        next(b for b in dialog.tool_buttons.buttons() if b.property("tool") == "box").click()
        drag((0.30, 0.15), (0.70, 0.60))
        self.assertTrue(dialog.state["isolate"])                       # le rectangle isole le sujet
        self.assertEqual(round(view.frame()["cx"], 3), 0.5)            # cadre réglé sur le rectangle
        self.assertEqual(dialog.request(300)["box"], view.subject_box)
        self.assertFalse(any(b.isHidden() for b in paint))
        next(b for b in dialog.tool_buttons.buttons() if b.property("tool") == "fg").click()
        drag((0.48, 0.30), (0.52, 0.45))                                # trait vert sur le sujet
        self.wait(lambda: dialog.service.session.has_hints())

    def test_undo_resize_handles_and_image_width(self):
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.resize(1400, 900)
        dialog.show()
        dialog.open_path(IMAGE)
        dialog.form.widgets["size_mm"].setValue(150)
        dialog._commit_history()                                        # fin d'une série de changements
        self.assertTrue(dialog.undo_button.isEnabled())
        dialog.undo()
        self.assertEqual((dialog.state["size_mm"], dialog.form.value("size_mm")), (100, 100))
        dialog.redo()
        self.assertEqual(dialog.state["size_mm"], 150)
        dialog.form.widgets["shape"].setCurrentIndex(dialog.form.widgets["shape"].findData("rect"))
        dialog.form.widgets["aspect"].setCurrentIndex(dialog.form.widgets["aspect"].findData("custom"))
        view = dialog.source_view
        scale, ox, oy = view._view()
        f = view.frame()
        fw, fh = __import__("stencil_studio.models.frame", fromlist=["dims"]).dims(dialog.state, view.iw, view.ih, f)
        corner = QPointF(ox + (f["cx"] * view.iw + fw / 2) * scale, oy + (f["cy"] * view.ih + fh / 2) * scale)
        inside = QPointF(corner.x() - 40, corner.y() - 40)
        width_before = dialog.state["custom_w"]
        for handler, point in ((view.mousePressEvent, corner), (view.mouseMoveEvent, inside),
                               (view.mouseReleaseEvent, inside)):
            handler(QMouseEvent(QMouseEvent.Type.MouseMove, point, point, Qt.MouseButton.LeftButton,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.assertLess(dialog.state["custom_w"], width_before)        # coin tiré vers l'intérieur
        self.assertEqual(dialog.form.value("custom_w"), dialog.state["custom_w"])
        dialog.form.widgets["img_mm"].setValue(dialog.state["img_mm"] / 3)   # photo plus petite que le cadre
        self.assertTrue(dialog.state["free"])                          # placement libre, marges vides

    def test_search_advanced_settings_and_saved_settings(self):
        from unittest import mock
        from PyQt6.QtWidgets import QInputDialog
        from stencil_studio.models.presets import PresetsStore
        from stencil_studio.ui.qt import QStencilDialog
        store = PresetsStore(os.path.join(tempfile.mkdtemp(), "presets.json"))
        dialog = QStencilDialog(language="fr", presets=store)
        self.addCleanup(dialog.deleteLater)
        dialog.show()
        form = dialog.form
        advanced = next(k for k in dialog.spec.advanced if k in form.widgets
                        and dialog.spec.row_shown(k, "stencil") and k not in dialog.spec.row_states(dialog.state)[1])
        row_hidden = lambda key: form._rows[key][0].isHidden()   # noqa: E731
        self.assertTrue(row_hidden(advanced))                            # réglage avancé masqué par défaut
        dialog.advanced_check.setChecked(True)
        self.assertFalse(row_hidden(advanced))
        dialog.search.setText("ponts")                                   # recherche (sans tenir compte des accents)
        self.assertFalse(row_hidden("bridge_mm"))
        self.assertTrue(row_hidden("blur"))
        dialog.search.clear()
        form.widgets["size_mm"].setValue(120)
        with mock.patch.object(QInputDialog, "getText", return_value=("Mes plaques", True)):
            dialog.save_user_preset()
        self.assertEqual(store.load()["Mes plaques"]["size_mm"], 120)   # même fichier que la page
        self.assertNotIn("zoom", store.load()["Mes plaques"])          # réglage que la page ne garde pas
        form.widgets["size_mm"].setValue(80)
        dialog.apply_user_preset("Mes plaques")
        self.assertEqual((dialog.state["size_mm"], form.value("size_mm")), (120, 120))

    def test_header_file_menu_and_export_sections(self):
        """Deux barres comme la page : menu Exporter en sections, réglages d'un fichier de la page, réinitialiser."""
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        sections = [a.text() for a in dialog.export_menu.actions() if a.isSeparator()]
        self.assertEqual(sections, ["Plaque", "Caisson lumineux", "Outils"])
        self.assertEqual(len(dialog.export_actions), 9)
        dialog.apply_settings({"format": "laser-stencil-studio", "S": {"output": "halftone", "dot_gamma": 1.8,
                                                                         "inconnu": 3}})
        self.assertEqual(dialog.state["output"], "halftone")
        self.assertEqual(dialog.form.value("dot_gamma"), 1.8)
        self.assertNotIn("inconnu", dialog.state)
        dialog.reset_settings()
        self.assertEqual(dialog.state, dialog.spec.defaults())
        self.assertEqual(dialog.form.value("dot_gamma"), dialog.spec.defaults()["dot_gamma"])

    def test_groups_fold_like_the_page(self):
        """Groupes repliables : ouverts ou fermés au départ comme la page (DEF_OPEN), la recherche ouvre ceux où
        elle trouve un réglage et rend l'état d'avant quand on la vide."""
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="en")
        self.addCleanup(dialog.deleteLater)
        boxes = dialog.form.boxes
        self.assertTrue(boxes["Frame"].is_open())
        closed = next(name for name in boxes if name not in dialog.spec.default_open)
        self.assertFalse(boxes[closed].is_open())
        self.assertTrue(boxes[closed].body.isHidden())
        boxes["Frame"].header.click()
        self.assertFalse(boxes["Frame"].is_open())
        dialog.form.set_filter("rotation")
        self.assertTrue(boxes["Frame"].is_open())
        dialog.form.set_filter("")
        self.assertFalse(boxes["Frame"].is_open())

    def test_slider_field_like_the_page(self):
        """Curseur des réglages « range » : pourcentages saisis × 100, unité de la page, curseur et champ d'accord."""
        from stencil_studio.ui.qt.controls import SliderField
        pct = SliderField({"k": "x", "t": "range", "min": 0, "max": 1, "step": 0.05, "def": 0.5, "fmt": "pct"})
        self.assertEqual((pct.spin.value(), pct.spin.suffix(), pct.slider.value()), (50, " %", 10))
        seen = []
        pct.valueChanged.connect(seen.append)
        pct.spin.setValue(75)
        self.assertEqual((pct.value(), pct.slider.value(), seen), (0.75, 15, [0.75]))
        rot = SliderField({"k": "rot", "t": "range", "min": -180, "max": 180, "step": 1, "def": 0, "unit": "°"})
        rot.slider.setValue(rot.slider.maximum())
        self.assertEqual((rot.value(), rot.spin.suffix()), (180, " °"))

    def test_view_bar_backlight_and_legend(self):
        """Barre du résultat comme la page : vues en boutons, rétroéclairage relié au réglage, légende de la vue."""
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="en")
        self.addCleanup(dialog.deleteLater)
        self.assertTrue(dialog.view_buttons["result"].isChecked())
        self.assertIn("material kept", dialog.legend.text())
        dialog.view_buttons["render"].click()
        self.assertEqual(dialog.view, "render")
        self.assertIn("Simulated look", dialog.legend.text())
        on = bool(dialog.state["backlight"])
        dialog.light_button.click()
        self.assertEqual((dialog.state["backlight"], dialog.form.value("backlight")), (not on, not on))
        dialog.reset_settings()
        self.assertEqual(dialog.light_button.isChecked(), bool(dialog.spec.defaults()["backlight"]))

    def test_stats_like_the_page(self):
        from stencil_studio.ui.qt.stats import stats_message
        tr = lambda text, **kw: text.format(**kw)                       # noqa: E731
        warnings, parts = stats_message({"holes": 12, "dots_across": 40, "length_mm": 980.4, "w_mm": 100, "h_mm": 80,
                                         "subject_pct": 20.0, "text_scaled": True}, {}, None, {}, tr, "1")
        self.assertEqual(parts, ["Holes: 12", "Grid: 40 dots across", "Subject: 20.0 %", "Cut length: 980 mm",
                                 "Size: 100.0 x 80.0 mm", "v1"])
        self.assertEqual(len(warnings), 2)                              # texte réduit, masque trop petit

    def test_colour_helpers_like_the_page(self):
        import numpy as np
        from stencil_studio.ui.qt.layer_colors import merge_picks, pick_color, picks_list
        self.assertEqual(merge_picks(["#ff0000", "#fe0101", "#00ff00", "bad"]), ["#ff0000", "#00ff00"])   # trop proches
        self.assertEqual(len(merge_picks([f"#{i:02x}0000" for i in range(0, 250, 40)] * 2)), 7)
        rgb = np.zeros((20, 20, 3), np.uint8)
        rgb[:, :10] = (200, 10, 10)
        self.assertEqual(pick_color(rgb, 4, 10), "#c80a0a")              # médiane 7 × 7
        self.assertIsNone(pick_color(rgb, 30, 10))                       # hors de la photo
        self.assertEqual(picks_list("#ff0000, oups,#00FF00"), ["#ff0000", "#00FF00"])

    def test_colour_picker_bridges_and_guides(self):
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.resize(1400, 900)
        dialog.show()
        dialog.open_path(IMAGE)

        def press(view, points, rect):
            for handler, (fx, fy) in zip((view.mousePressEvent, view.mouseMoveEvent, view.mouseReleaseEvent), points):
                x, y, w, h = rect()
                p = QPointF(x + fx * w, y + fy * h)
                handler(QMouseEvent(QMouseEvent.Type.MouseMove, p, p, Qt.MouseButton.LeftButton,
                                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        source = dialog.source_view

        def source_rect():
            scale, ox, oy = source._view()
            return ox, oy, source.iw * scale, source.ih * scale
        self.assertTrue(dialog.colors_panel.isHidden())                  # seulement en couches par couleur
        next(b for b in dialog.mode_buttons.buttons() if b.property("mode") == "layers").click()
        dialog.form.widgets["ml_sep"].setCurrentIndex(dialog.form.widgets["ml_sep"].findData("color"))
        self.assertFalse(dialog.colors_panel.isHidden())
        dialog.colors_panel.request_picker(True, None)
        press(source, [(0.5, 0.4)] * 3, source_rect)                    # clic à la pipette
        self.assertRegex(dialog.state["ml_picks"], r"^#[0-9a-f]{6}$")
        self.assertEqual(dialog.form.value("ml_picks"), dialog.state["ml_picks"])
        result = dialog.result_view
        self.wait(lambda: result.image_rect() is not None)

        def result_rect():
            r = result.image_rect()
            return r.x(), r.y(), r.width(), r.height()
        next(b for b in dialog.mode_buttons.buttons() if b.property("mode") == "stencil").click()
        dialog.set_overlay_mode("bridge")                                # pont manuel
        press(result, [(0.4, 0.4), (0.5, 0.45), (0.5, 0.45)], result_rect)
        self.assertEqual(result.bridges, [[0.4, 0.4, 0.5, 0.45]])
        self.assertEqual(dialog.request(300)["mbr"], result.bridges)
        dialog._commit_history()
        press(result, [(0.45, 0.425)] * 3, result_rect)                  # un clic sur le pont le retire
        self.assertEqual(result.bridges, [])
        dialog.undo()                                                    # l'historique garde les ponts
        self.assertEqual(result.bridges, [[0.4, 0.4, 0.5, 0.45]])
        next(b for b in dialog.mode_buttons.buttons() if b.property("mode") == "lowpoly").click()
        dialog.set_overlay_mode("guide")                                 # guides du low poly
        press(result, [(0.3, 0.3)] * 3, result_rect)
        press(result, [(0.2, 0.2), (0.6, 0.2), (0.6, 0.2)], result_rect)
        self.assertEqual(result.guides, {"pts": [[0.3, 0.3]], "edges": [[0.2, 0.2, 0.6, 0.2]]})
        self.assertEqual(dialog.request(300)["lpg"], result.guides)

    def test_menu_entry_opens_the_qt_version_next_to_the_web_one(self):
        from unittest import mock
        from PyQt6.QtWidgets import QWidget
        from stencil_studio.controllers.studio import StencilStudioController
        window = QWidget()
        self.addCleanup(window.deleteLater)
        controller = StencilStudioController(window, theme=dict, language="fr", dialogs=mock.Mock())
        forwarded = []
        controller.export_ready.connect(forwarded.append)
        controller.open_qt()
        self.addCleanup(controller.qt_dialog.deleteLater)
        controller.qt_dialog.export_ready.emit("/tmp/x.svg")
        self.assertEqual(forwarded, ["/tmp/x.svg"])               # même chemin vers Laser Studio que la page
        self.assertIsNone(controller.dialog)                       # la page web n'a pas été ouverte



    def test_qr_button_on_the_empty_window_starts_a_qr_code(self):
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.show()
        self.assertTrue(dialog.qr_button.isVisible())
        self.assertEqual(dialog.qr_button.text(), "Ou créer un code QR")
        dialog.qr_button.click()
        self.assertEqual(dialog.state["output"], "qr")
        self.assertTrue(dialog.service.session.has_image())                # page blanche
        self.assertFalse(dialog.qr_button.isVisible())

@unittest.skipIf(StudioService is None, "OpenCV ou PyQt6 non importables ici")
class LayerColorsPanelTests(unittest.TestCase):
    """Plaques du relief en couches : pastilles avec leurs flèches dessous, sur des rangées qui passent à la
    ligne, comme la page (une rangée unique élargissait le volet et cachait les champs de valeur à droite)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        from stencil_studio.ui.qt.layer_colors import LayerColorsPanel
        panel = LayerColorsPanel(lambda text, **kw: text.format(**kw) if kw else text)
        self.addCleanup(panel.deleteLater)
        palette = ["#000000", "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#00ffff", "#ff00ff"]
        panel.show_colors(["#123456"] * 8, 7, palette, list(range(7)))
        return panel

    def test_seven_plates_fit_in_the_settings_pane(self):
        self.assertLess(self.make().minimumSizeHint().width(), 300)       # volet de 330 px

    def test_an_arrow_moves_its_own_plate_once_per_preview(self):
        panel = self.make()
        orders = []
        panel.order_changed.connect(orders.append)
        right_of_first = panel.arrows[1]                                   # ▶ sous la plaque 1
        right_of_first.click()
        self.assertEqual(orders, ["1,0,2,3,4,5,6"])
        self.assertFalse(any(arrow.isEnabled() for arrow in panel.arrows))  # jusqu'à la palette suivante


@unittest.skipIf(StudioService is None, "OpenCV ou PyQt6 non importables ici")
class ResetButtonTests(unittest.TestCase):
    """↺ d'un réglage modifié et « • » de son groupe, comme la page (markModified)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_modified_setting_shows_reset_and_goes_back_to_default(self):
        from stencil_studio import spec as spec_module
        from stencil_studio.ui.qt.controls import SettingsForm
        spec = spec_module.load()
        form = SettingsForm(spec, lambda text, **kw: text)
        self.addCleanup(form.deleteLater)
        state = spec.defaults()
        changes = []
        form.changed.connect(lambda key, value: (changes.append((key, value)), state.__setitem__(key, value),
                                                 form.show_mode("stencil", state)))
        form.show_mode("stencil", state)
        self.assertFalse(form._resets["rot"].isVisibleTo(form))
        group = next(name for name, box in form.boxes.items() if box.isAncestorOf(form.widgets["rot"]))
        form.widgets["rot"].setValue(15)
        self.assertTrue(form._resets["rot"].isVisibleTo(form))
        self.assertTrue(form.boxes[group].header.text().endswith("•"))
        form._resets["rot"].click()
        self.assertEqual((form.value("rot"), changes[-1]), (0, ("rot", 0)))
        self.assertFalse(form._resets["rot"].isVisibleTo(form))
        self.assertNotIn("img_mm", form._resets)                   # NO_RESET, comme la page

if __name__ == "__main__":
    unittest.main()
