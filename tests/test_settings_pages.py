"""Pages de réglages (MachineParamsPage, MachineProfilesPage, TestMatrixPage, GrblConfigPage) : signaux et état."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtGui import QStandardItemModel, QStandardItem
    from PyQt6.QtWidgets import QApplication, QPushButton, QScrollArea
    from i18n import tr
    from ui.settings.grbl_config import GrblConfigPage
    from ui.settings.machine_params import MachineParamsPage
    from ui.settings.machine_profiles import MachineProfilesPage
    from ui.settings.test_matrix import TestMatrixPage
    from ui.settings.test_matrix.tile_picker import TilePicker
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest
    from PIL import Image
except ImportError:  # PyQt6 manquant
    MachineParamsPage = None


class _Recorder:
    def __init__(self, test):
        self.test = test

    def record(self, signal):
        received = []
        signal.connect(lambda *args: received.append(args))
        return received


@unittest.skipIf(MachineParamsPage is None, "PyQt6 non importable ici")
class MachineParamsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        page = MachineParamsPage()
        self.addCleanup(page.deleteLater)
        return page

    def record(self, signal):
        return _Recorder(self).record(signal)

    def button(self, page, key):
        return next(b for b in page.findChildren(QPushButton) if b.text() == tr(key))

    def test_page_scrolls_by_itself(self):
        self.assertIsInstance(self.make(), QScrollArea)    # pas de double ascenseur dans la fenêtre

    def test_profile_buttons_emit_their_signal(self):
        page = self.make()
        for key, signal in (("mach.new_machine", page.new_profile_requested),
                            ("mach.update", page.update_profile_requested),
                            ("mach.delete", page.delete_profile_requested)):
            received = self.record(signal)
            self.button(page, key).click()
            self.assertEqual(received, [()], key)

    def test_fields_emit_business_values(self):
        page = self.make()
        bed, focal, speed = (self.record(page.bed_size_changed), self.record(page.focal_changed),
                             self.record(page.max_speed_changed))
        page.bed_width_spin.setValue(400.0)
        page.bed_height_spin.setValue(250.0)
        page.focal_spin.setValue(0.08)
        page.max_speed_spin.setValue(3000.0)
        self.assertEqual(bed, [(400.0, 200.0), (400.0, 250.0)])
        self.assertEqual(focal, [(0.08,)])
        self.assertEqual(speed, [(3000.0,)])

    def test_selecting_a_profile_emits_its_index(self):
        page = self.make()
        page.profile_combo.addItems(["A", "B"])
        received = self.record(page.profile_selected)
        page.profile_combo.setCurrentIndex(1)
        self.assertEqual(received, [(1,)])


@unittest.skipIf(MachineParamsPage is None, "PyQt6 non importable ici")
class MachineProfilesPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        model = QStandardItemModel()
        for port in ("COM1", "COM2"):
            model.appendRow(QStandardItem(port))
        page = MachineProfilesPage(model, ["MDF 4mm", "Cuir 2mm"])
        self.addCleanup(page.deleteLater)
        return page

    def record(self, signal):
        return _Recorder(self).record(signal)

    def button(self, page, key):
        return next(b for b in page.findChildren(QPushButton) if b.text() == tr(key))

    def test_buttons_emit_their_signal(self):
        page = self.make()
        for key, signal in (("usb.refresh_ports", page.refresh_ports_requested),
                            ("usb.connect", page.connect_requested),
                            ("material.save", page.save_material_requested),
                            ("material.new", page.new_material_requested),
                            ("material.delete", page.delete_material_requested),
                            ("material.export", page.export_materials_requested),
                            ("material.import", page.import_materials_requested)):
            received = self.record(signal)
            self.button(page, key).click()
            self.assertEqual(received, [()], key)

    def test_lists_emit_the_selected_index(self):
        page = self.make()
        ports, materials = self.record(page.port_selected), self.record(page.material_selected)
        page.ports_combo.setCurrentIndex(1)
        page.material_combo.setCurrentIndex(1)
        self.assertEqual((ports, materials), ([(1,)], [(1,)]))
        page.set_port_index(0)
        self.assertEqual(page.ports_combo.currentText(), "COM1")

    def test_connect_button_follows_the_connection(self):
        page = self.make()
        page.set_connected(True)
        self.assertEqual(page.connect_button.text(), tr("laser.disconnect"))
        self.assertIn("#27ae60", page.connect_button.styleSheet())
        page.set_connected(False)
        self.assertEqual((page.connect_button.text(), page.connect_button.styleSheet()),
                         (tr("laser.connect"), ""))


@unittest.skipIf(MachineParamsPage is None, "PyQt6 non importable ici")
class TestMatrixPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        page = TestMatrixPage(lines_mm=10.0)
        self.addCleanup(page.deleteLater)
        return page

    def record(self, signal):
        return _Recorder(self).record(signal)

    def button(self, page, key):
        return next(b for b in page.findChildren(QPushButton) if b.text() == tr(key))

    def test_buttons_emit_their_signal(self):
        page = self.make()
        page.set_image_test_checked(True)          # boutons d'image grisés tant que le cadre est décoché
        for key, signal in (("ui.gen_test_matrix", page.generate_requested),
                            ("ui.mat_image_choose", page.choose_image_requested),
                            ("ui.mat_image_use_loaded", page.use_loaded_image_requested)):
            received = self.record(signal)
            self.button(page, key).click()
            self.assertEqual(received, [()], key)

    def test_params_are_business_values(self):
        page = self.make()
        page.set_lines_mm(12.0)
        params = page.matrix_params()
        self.assertEqual((params["min_power"], params["max_power"], params["lines_mm"], params["laser_cmd"]),
                         (10, 80, 12.0, "M4"))
        self.assertEqual(params["single_power"], params["min_power"])

    def test_cutting_mode_shows_passes_instead_of_power_range(self):
        page = self.make()
        page.show()
        self.assertTrue(page.is_engraving())
        self.assertTrue(page.max_power_spin.isVisible() and not page.min_passes_spin.isVisible())
        page.mode_combo.setCurrentIndex(1)
        self.assertFalse(page.is_engraving())
        self.assertTrue(page.min_passes_spin.isVisible() and not page.max_power_spin.isVisible())
        self.assertFalse(page.lines_mm_spin.isVisible())

    def test_image_test_only_exists_in_engraving(self):
        page = self.make()
        toggles = self.record(page.image_test_toggled)
        page.set_image_test_checked(True)
        self.assertEqual(toggles, [(True,)])
        self.assertTrue(page.image_test_enabled())
        self.assertFalse(page.square_size_spin.isEnabled())   # taille des cases : celle de la zone d'image
        page.mode_combo.setCurrentIndex(1)
        self.assertFalse(page.image_test_enabled())

    def test_source_image_sets_the_real_width_and_the_tile_info(self):
        page = self.make()
        page.set_source_image(Image.new("L", (600, 400), 128), "photo.png", width_mm=60.0)
        self.assertEqual(page.image_name_label.text(), "photo.png")
        self.assertEqual(page.tile_settings()[:3], (60.0, 15.0, 15.0))
        self.assertTrue(page.tile_info_label.text())


@unittest.skipIf(MachineParamsPage is None, "PyQt6 non importable ici")
class TilePickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        picker = TilePicker()
        picker.resize(300, 200)
        picker.set_image(Image.new("L", (300, 200), 128))
        self.addCleanup(picker.deleteLater)
        return picker

    def test_frame_always_stays_inside_the_image(self):
        picker = self.make()
        picker.set_frame_fraction(0.5, 0.5)
        self.assertEqual(picker.center(), (0.5, 0.5))
        QTest.mouseClick(picker, Qt.MouseButton.LeftButton, pos=QPoint(3, 3))
        cx, cy = picker.center()
        self.assertEqual((cx, cy), (0.25, 0.25))           # coin haut-gauche : cadre collé au bord

    def test_whole_image_frame_is_centred(self):
        picker = self.make()
        picker.set_frame_fraction(1.0, 1.0)
        self.assertEqual(picker.center(), (0.5, 0.5))


@unittest.skipIf(MachineParamsPage is None, "PyQt6 non importable ici")
class GrblConfigPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        page = GrblConfigPage()
        self.addCleanup(page.deleteLater)
        return page

    def record(self, signal):
        return _Recorder(self).record(signal)

    def test_buttons_emit_their_signal(self):
        page = self.make()
        for key, signal in (("ui.bidir_test_btn", page.bidir_test_requested),
                            ("ui.grbl_read", page.read_settings_requested),
                            ("ui.grbl_send", page.send_settings_requested),
                            ("ui.grbl_export", page.export_settings_requested),
                            ("ui.grbl_import", page.import_settings_requested),
                            ("ui.grbl_link_profile", page.link_settings_to_profile_requested)):
            received = self.record(signal)
            next(b for b in page.findChildren(QPushButton) if b.text() == tr(key)).click()
            self.assertEqual(received, [()], key)

    def test_scan_offset_emits_its_value_in_mm(self):
        page = self.make()
        received = self.record(page.scan_offset_changed)
        page.scan_offset_spin.setValue(0.25)
        self.assertEqual(received, [(0.25,)])

    def test_overscan_value_follows_the_mode(self):
        page = self.make()
        page.show()
        self.assertTrue(page.overscan_dist_spin.isVisible())
        self.assertFalse(page.overscan_pct_spin.isVisible())
        page.overscan_mode_combo.setCurrentIndex(1)            # pourcentage
        self.assertFalse(page.overscan_dist_spin.isVisible())
        self.assertTrue(page.overscan_pct_spin.isVisible())

    def test_defaults(self):
        page = self.make()
        self.assertTrue(page.homing_check.isChecked())          # homing automatique activé d'office
        self.assertTrue(page.overscan_check.isChecked())
        self.assertTrue(page.safe_cut_order_check.isChecked())
        self.assertEqual(page.laser_cmd_combo.currentText().split()[0], "M4")
        self.assertEqual(page.smax_spin.value(), 1000)


if __name__ == "__main__":
    unittest.main()
