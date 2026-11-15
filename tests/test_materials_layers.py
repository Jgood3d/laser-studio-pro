"""Profils matériaux dans l'onglet Calques : un matériau mémorise les
réglages des calques, et le choisir met le tableau à jour. Aide « Port
introuvable ? » du panneau Connexion."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtWidgets import QApplication, QPushButton
    from PyQt6.QtGui import QStandardItemModel
    from laser_studio.controllers.materials import (
        DEFAULT_MATERIALS_DB, apply_material_to_layers, capture_material_layers,
    )
    from laser_studio.i18n import tr
    from laser_studio.vector_layers import LayerManager
except ImportError:  # PyQt6 manquant
    LayerManager = None


@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class MaterialLayersTests(unittest.TestCase):
    def test_saved_material_restores_every_layer(self):
        manager = LayerManager()                       # gravure, découpe, marquage
        engrave, cut, mark = manager.layers
        engrave.power, engrave.speed, mark.line_interval = 12.0, 3456, 0.05
        material = {"layers": capture_material_layers(manager)}
        engrave.power, engrave.speed, mark.line_interval = 99.0, 100, 0.2
        engrave.mode = "Découpe"                       # le mode n'est pas un réglage de matériau
        self.assertTrue(apply_material_to_layers(manager, material))
        self.assertEqual((engrave.power, engrave.speed, mark.line_interval), (12.0, 3456, 0.05))
        self.assertEqual(engrave.mode, "Découpe")

    def test_layers_found_by_position_when_ids_differ(self):
        source, target = LayerManager(), LayerManager()
        source.layers[1].speed = 777
        material = {"layers": capture_material_layers(source)}
        apply_material_to_layers(target, material)      # autres identifiants : par position
        self.assertEqual(target.layers[1].speed, 777)
        self.assertEqual(len(target.layers), 3)         # ni ajout ni suppression

    def test_old_material_goes_to_engrave_and_cut_layers(self):
        manager = LayerManager()
        engrave, cut, mark = manager.layers
        mark_before = (mark.power, mark.speed, mark.passes)
        mdf = DEFAULT_MATERIALS_DB["MDF 4mm"]
        self.assertTrue(apply_material_to_layers(manager, mdf))
        self.assertEqual((engrave.speed, engrave.power), (mdf["sp_e"], float(mdf["pw_e"])))
        self.assertEqual((cut.speed, cut.power, cut.passes), (mdf["sp_c"], float(mdf["pw_c"]), mdf["pass_c"]))
        self.assertEqual((mark.power, mark.speed, mark.passes), mark_before)

    def test_old_material_without_cut_leaves_cut_layers(self):
        manager = LayerManager()
        cut = manager.layers[1]
        before = (cut.speed, cut.power, cut.passes)
        apply_material_to_layers(manager, DEFAULT_MATERIALS_DB["Ardoise / Carrelage"])   # 0 passe
        self.assertEqual((cut.speed, cut.power, cut.passes), before)


@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class LayersTabMaterialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        from laser_studio.ui.tabs.layers import LayersTab
        tab = LayersTab(LayerManager(), ["Personnalisé", "MDF 4mm"])
        self.addCleanup(tab.deleteLater)
        return tab

    def test_toolbar_actions_emit_their_signal(self):
        tab = self.make()
        for name in ("save_material_requested", "new_material_requested", "delete_material_requested",
                     "export_materials_requested", "import_materials_requested"):
            received = []
            getattr(tab, name).connect(lambda: received.append(True))
            tab.material_actions[name].trigger()
            self.assertEqual(received, [True], name)
            self.assertFalse(tab.material_actions[name].icon().isNull(), name)

    def test_only_a_user_choice_selects_a_material(self):
        tab = self.make()
        received = []
        tab.material_selected.connect(received.append)
        tab.material_combo.setCurrentIndex(1)          # par programme (projet, profil) : rien
        self.assertEqual(received, [])
        tab.material_combo.activated.emit(1)           # choix de l'utilisateur
        self.assertEqual(received, [1])


@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class PortHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_help_button_and_dialog(self):
        from laser_studio.ui.machine.connection import ConnectionPanel, port_help_dialog
        panel = ConnectionPanel(QStandardItemModel())
        self.addCleanup(panel.deleteLater)
        received = []
        panel.help_requested.connect(lambda: received.append(True))
        panel.help_button.click()
        self.assertEqual(received, [True])
        self.assertEqual(panel.help_button.toolTip(), tr("usb.help_title"))
        box = port_help_dialog()
        self.addCleanup(box.deleteLater)
        self.assertEqual(box.text(), tr("usb.driver_hint"))
        self.assertIn("CH340", box.text())


class WindowWiringTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, "src", "laser_studio", *parts), encoding="utf-8") as f:
            return f.read()

    def test_materials_live_in_the_layers_tab_and_the_window_is_gone(self):
        src = self.read("main_window.py")
        self.assertIn("self.layers_tab.material_combo,", src)
        self.assertIn("tab.material_selected.connect(self.materials.apply_selected)", src)
        self.assertIn("self.combo_ports = connection.ports_combo", src)
        self.assertIn("connection.help_requested.connect(lambda: port_help_dialog(self).exec())", src)
        self.assertNotIn("MachineProfilesPage", src)
        self.assertFalse(os.path.exists(os.path.join(REPO, "src", "laser_studio", "ui", "settings", "machine_profiles")))
        # Profil machine : le matériau ne réécrase pas les calques que le profil vient de restaurer.
        self.assertIn("self._apply_job_settings(material, layers=False)", src)


@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class MaterialChoiceRefreshesTheTableTests(unittest.TestCase):
    """Dans la vraie fenêtre : choisir un matériau redessine les cases du tableau (bug : les
    calques changeaient en mémoire, mais le tableau gardait les anciennes valeurs).

    Lancé dans un processus à part : le bug dépend de QObject.sender(), donc de ce que les
    autres tests ont émis avant dans le même processus."""

    SCRIPT = """
import os, sys, tempfile
os.environ["XDG_CONFIG_HOME"] = os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, {src!r})
from unittest import mock
from PyQt6.QtWidgets import QApplication, QAbstractSpinBox
app = QApplication([])
mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
from laser_studio.main_window import FullLaserStudio
win = FullLaserStudio()
combo = win.layers_tab.material_combo
combo.setCurrentText("MDF 4mm")
combo.activated.emit(combo.currentIndex())
table = win.layers_tab.layer_widget.table
values = []
for col in (3, 4):
    cell = table.cellWidget(0, col)
    spin = cell if isinstance(cell, QAbstractSpinBox) else cell.findChild(QAbstractSpinBox)
    values.append(spin.value())
print("AFFICHÉ", values[0], values[1], flush=True)
win.deleteLater(); app.processEvents()
"""

    def test_choosing_a_material_updates_the_displayed_table(self):
        import subprocess
        script = self.SCRIPT.format(src=os.path.join(REPO, "src"))
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                env=env, timeout=120)
        line = next((l for l in result.stdout.splitlines() if l.startswith("AFFICHÉ")), None)
        self.assertIsNotNone(line, result.stderr[-2000:])
        mdf = DEFAULT_MATERIALS_DB["MDF 4mm"]
        self.assertEqual(line.split()[1:], [str(float(mdf["pw_e"])), str(mdf["sp_e"])])

if __name__ == "__main__":
    unittest.main()
