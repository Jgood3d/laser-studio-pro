"""Pages de réglages (MachineParamsPage, MachineProfilesPage) : signaux et état."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtGui import QStandardItemModel, QStandardItem
    from PyQt6.QtWidgets import QApplication, QPushButton, QScrollArea
    from i18n import tr
    from ui.settings.machine_params import MachineParamsPage
    from ui.settings.machine_profiles import MachineProfilesPage
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


if __name__ == "__main__":
    unittest.main()
