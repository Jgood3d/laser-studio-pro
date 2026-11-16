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
class BaseLayersTests(unittest.TestCase):
    """Trois calques de base (gravure, découpe, marquage) : toujours présents, nom fixe."""

    def test_new_manager_has_the_three_base_layers(self):
        manager = LayerManager()
        self.assertEqual([(l.role, l.name, l.mode) for l in manager.layers],
                         [("engrave", tr("layers.default_name_engrave"), "Gravure Remplie"),
                          ("cut", tr("layers.default_name_cut"), "Découpe"),
                          ("mark", tr("layers.default_name_mark"), "Marquage (Contour)")])

    def test_old_saved_layers_are_adopted_or_completed(self):
        manager = LayerManager()
        # Calques enregistrés avant les rôles : une gravure renommée, un calque libre.
        manager.load_list([{"id": "a1", "name": "Gravure Texte", "mode": "Gravure Remplie", "power": 20.0},
                           {"id": "b2", "name": "Logo", "mode": "Gravure Remplie"}])
        roles = {l.role: l for l in manager.layers}
        self.assertEqual(sorted(r for r in roles if r), ["cut", "engrave", "mark"])
        self.assertEqual((roles["engrave"].id, roles["engrave"].name, roles["engrave"].power),
                         ("a1", tr("layers.default_name_engrave"), 20.0))     # repris, renommé
        logo = next(l for l in manager.layers if l.id == "b2")
        self.assertEqual((logo.role, logo.name), (None, "Logo"))              # calque libre inchangé
        self.assertEqual(len(manager.layers), 4)                             # découpe et marquage ajoutés

    def test_base_layer_name_is_read_only_and_cannot_be_deleted(self):
        from unittest import mock
        from PyQt6.QtWidgets import QMessageBox
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from laser_studio.vector_layers import LayerManagerWidget
        manager = LayerManager()
        manager.add_layer()
        widget = LayerManagerWidget(manager)
        self.addCleanup(widget.deleteLater)
        table = widget.table
        self.assertTrue(table.cellWidget(0, 1).isReadOnly())
        self.assertFalse(table.cellWidget(3, 1).isReadOnly())                 # calque ajouté
        table.setCurrentCell(0, 1)
        with mock.patch.object(QMessageBox, "information") as info:
            widget.on_remove()
        info.assert_called_once()
        self.assertEqual(len(manager.layers), 4)
        table.setCurrentCell(3, 1)
        widget.on_remove()
        self.assertEqual(len(manager.layers), 3)


@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class LayerTableColumnsTests(unittest.TestCase):
    """Colonnes du tableau des calques assez larges pour leur contenu (bug : largeur par défaut
    de 100 px, en-têtes coupés et champs qui débordaient sur la colonne voisine)."""

    def test_every_column_fits_its_header_and_widgets(self):
        app = QApplication.instance() or QApplication([])
        from laser_studio.vector_layers import LayerManagerWidget
        widget = LayerManagerWidget(LayerManager(), focal_getter=lambda: 0.1)
        self.addCleanup(widget.deleteLater)
        widget.resize(1500, 300)
        widget.show()
        app.processEvents()
        table, header = widget.table, widget.table.horizontalHeader()
        for col in range(table.columnCount()):
            title = table.horizontalHeaderItem(col).text()
            need = max([header.fontMetrics().horizontalAdvance(title)] +
                       [table.cellWidget(r, col).sizeHint().width() for r in range(table.rowCount())])
            self.assertGreaterEqual(table.columnWidth(col), need, title)


@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class MaterialCompletionTests(unittest.TestCase):
    def test_old_material_gets_the_three_base_entries(self):
        from laser_studio.controllers.materials import complete_material
        mdf = DEFAULT_MATERIALS_DB["MDF 4mm"]
        done = complete_material(mdf)
        entries = {d["role"]: d for d in done["layers"]}
        self.assertEqual(sorted(entries), ["cut", "engrave", "mark"])
        self.assertEqual((entries["engrave"]["power"], entries["engrave"]["speed"]), (float(mdf["pw_e"]), mdf["sp_e"]))
        self.assertEqual((entries["cut"]["speed"], entries["cut"]["passes"]), (mdf["sp_c"], mdf["pass_c"]))
        self.assertEqual((entries["mark"]["power"], entries["mark"]["line_interval"]), (75.0, 0.06))
        self.assertNotIn("layers", mdf)                                       # l'original n'est pas modifié

    def test_material_without_cut_gets_default_cut(self):
        from laser_studio.controllers.materials import complete_material
        entries = {d["role"]: d for d in complete_material(DEFAULT_MATERIALS_DB["Ardoise / Carrelage"])["layers"]}
        self.assertEqual((entries["cut"]["power"], entries["cut"]["passes"]), (90.0, 2))

    def test_missing_base_entry_is_added_and_others_kept(self):
        from laser_studio.controllers.materials import complete_material
        material = {"layers": [{"role": "engrave", "power": 11.0, "speed": 900},
                               {"id": "libre", "power": 5.0}]}
        done = complete_material(material)
        self.assertEqual(len(done["layers"]), 4)
        self.assertEqual(done["layers"][0]["power"], 11.0)
        self.assertEqual(sorted(d.get("role") or "-" for d in done["layers"]), ["-", "cut", "engrave", "mark"])

    def test_controller_completes_every_material(self):
        from laser_studio.controllers.materials import MaterialsController
        from PyQt6.QtWidgets import QComboBox
        app = QApplication.instance() or QApplication([])  # noqa: F841
        combo = QComboBox()
        controller = MaterialsController(None, combo, dict(DEFAULT_MATERIALS_DB), dict, lambda m: None)
        for name, material in controller.materials.items():
            self.assertEqual(sorted(d["role"] for d in material["layers"] if d.get("role")),
                             ["cut", "engrave", "mark"], name)


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

@unittest.skipIf(LayerManager is None, "PyQt6 non importable ici")
class MaterialPersistenceTests(unittest.TestCase):
    """Matériau choisi et réglages enregistrés (« Enregistrer ») retrouvés au démarrage suivant.
    Deux fenêtres successives dans un processus à part, avec une configuration temporaire."""

    SCRIPT = """
import os, sys, tempfile
os.environ["XDG_CONFIG_HOME"] = os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, {src!r})
from unittest import mock
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtTest import QTest
app = QApplication([])
mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
from laser_studio.main_window import FullLaserStudio
w = FullLaserStudio(); tab = w.layers_tab; combo = tab.material_combo
combo.setCurrentText("Acrylique 3mm"); combo.activated.emit(combo.currentIndex())
w.layer_manager.layers[2].power = 42.0
with mock.patch.object(QMessageBox, "information"):
    tab.material_actions["save_material_requested"].trigger()
QTest.qWait(1500)
w.deleteLater(); app.processEvents()
w2 = FullLaserStudio()
mark = next(d for d in w2.materials.materials["Acrylique 3mm"]["layers"] if d.get("role") == "mark")
print("RÉSULTAT", w2.layers_tab.material_combo.currentText().replace(" ", "_"), mark["power"], flush=True)
w2.deleteLater(); app.processEvents()
"""

    def test_selected_material_and_saved_settings_survive_a_restart(self):
        import subprocess
        script = self.SCRIPT.format(src=os.path.join(REPO, "src"))
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                env=env, timeout=180)
        line = next((l for l in result.stdout.splitlines() if l.startswith("RÉSULTAT")), None)
        self.assertIsNotNone(line, result.stderr[-2000:])
        self.assertEqual(line.split()[1:], ["Acrylique_3mm", "42.0"])


class TableHeaderThemeTests(unittest.TestCase):
    def test_tables_and_headers_have_no_inner_padding(self):
        with open(os.path.join(REPO, "src", "laser_studio", "ui", "app", "theme.py"), encoding="utf-8") as f:
            theme = f.read()
        for selector in ("QTableView, QTreeView {{", "QHeaderView {{"):
            block = theme[theme.index(selector):]
            self.assertIn("padding: 0px;", block[:block.index("}}")], selector)


if __name__ == "__main__":
    unittest.main()
