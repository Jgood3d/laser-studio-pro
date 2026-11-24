"""Catalogue des machines : fichiers livrés (resources/machines), lecture (library/machine_catalog.py),
profil créé d'après un modèle (controllers/machine_profiles.py) et fenêtre (ui/dialogs/machine_catalog)."""
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
MACHINES_DIR = os.path.join(REPO, "src", "laser_studio", "resources", "machines")

try:
    import yaml  # noqa: F401
    from laser_studio.library.machine_catalog import MachineModel, load_machine_catalog, parse_machine_file
except ImportError:  # PyYAML manquant
    load_machine_catalog = None

try:
    from PyQt6.QtWidgets import QApplication, QComboBox
    from laser_studio.controllers.machine_profiles import MachineProfilesController, ProfileFields
    from laser_studio.ui.dialogs.machine_catalog import MachineCatalogDialog
except ImportError:
    MachineProfilesController = None

BRAND = """brand: Exemple
machines:
  - model: L1 10W
    work_area_mm: [400, 380]
    spot_mm: [0.06, 0.1]
    max_speed_mm_min: {x: 20000, y: 15000}
    laser: {power_w: 10, wavelength_nm: 455}
    sources: [https://exemple.test/manuel.pdf]
    checked: 2026-11-24
  - model: Sans surface
    spot_mm: [0.1, 0.1]
  - model: L2
    work_area_mm: [300, 300]
"""


@unittest.skipIf(load_machine_catalog is None, "PyYAML non installé")
class MachineCatalogTests(unittest.TestCase):
    def test_parse(self):
        models = parse_machine_file(BRAND, "x.yaml")
        self.assertEqual([m.title for m in models], ["Exemple L1 10W", "Exemple L2"])
        first = models[0]
        self.assertEqual(first.focal, 0.08)
        self.assertEqual(first.max_speed, 15000.0)       # l'axe le plus lent
        self.assertEqual(first.profile_values(), {"w": 400.0, "h": 380.0, "focal": 0.08, "max_speed": 15000.0})
        self.assertEqual(first.power_w, 10)
        self.assertEqual(first.sources, ["https://exemple.test/manuel.pdf"])

    def test_missing_values_are_not_guessed(self):
        model = parse_machine_file(BRAND)[1]
        self.assertIsNone(model.focal)
        self.assertIsNone(model.max_speed)
        self.assertEqual(model.profile_values(), {"w": 300.0, "h": 300.0})

    def test_invalid_text(self):
        self.assertEqual(parse_machine_file("- juste une liste"), [])
        self.assertEqual(parse_machine_file(""), [])

    def test_user_folder_overrides_and_bad_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as shipped, tempfile.TemporaryDirectory() as user:
            with open(os.path.join(shipped, "exemple.yaml"), "w", encoding="utf-8") as f:
                f.write(BRAND)
            with open(os.path.join(shipped, "casse.yaml"), "w", encoding="utf-8") as f:
                f.write("brand: [\n")
            with open(os.path.join(user, "perso.yaml"), "w", encoding="utf-8") as f:
                f.write("brand: exemple\nmachines:\n  - model: l2\n    work_area_mm: [500, 500]\n")
            models = load_machine_catalog([shipped, user, os.path.join(user, "absent")])
        self.assertEqual(len(models), 2)
        self.assertEqual(models[1].work_area_mm, (500.0, 500.0))

    def test_shipped_files(self):
        """Fichiers livrés : chacun lisible, chaque modèle avec une source et une date de vérification,
        des valeurs plausibles."""
        names = [n for n in os.listdir(MACHINES_DIR) if n.endswith(".yaml")]
        self.assertTrue(names)
        for name in names:
            with open(os.path.join(MACHINES_DIR, name), encoding="utf-8") as f:
                text = f.read()
            models = parse_machine_file(text, name)
            self.assertEqual(len(models), len(yaml.safe_load(text)["machines"]), name)
            for model in models:
                self.assertTrue(model.sources, model.title)
                self.assertTrue(model.checked, model.title)
                self.assertTrue(all(100 <= v <= 2000 for v in model.work_area_mm), model.title)
                if model.focal:
                    self.assertTrue(0.01 <= model.focal <= 0.5, model.title)
                if model.max_speed:
                    self.assertTrue(1000 <= model.max_speed <= 100000, model.title)
        titles = [m.title for m in load_machine_catalog([MACHINES_DIR])]
        self.assertIn("Elegoo Phecda 10W", titles)


class _Fields:
    def __init__(self):
        self.applied = []
        self.selected = 0

    def capture(self):
        return {"w": 300.0, "h": 200.0, "focal": 0.1, "max_speed": 6000.0, "accel": 800.0}

    def apply(self, profile):
        self.applied.append(dict(profile))

    def apply_layers(self, layers, full):
        pass

    def profile_selected(self):
        self.selected += 1


@unittest.skipIf(load_machine_catalog is None or MachineProfilesController is None, "PyQt6 ou PyYAML absent")
class CatalogProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _controller(self):
        fields = _Fields()
        combo = QComboBox()
        controller = MachineProfilesController(
            None, combo,
            ProfileFields(capture=fields.capture, apply=fields.apply, apply_layers=fields.apply_layers,
                          memory=lambda: None, profile_selected=fields.profile_selected,
                          link_layers_to_focal=lambda: None),
            save_settings=lambda: None, dialogs=object())
        controller.profiles = [{"name": "Atelier"}]
        controller.refresh_combo("Atelier")
        return controller, fields, combo

    def test_new_profile_from_catalog(self):
        controller, fields, combo = self._controller()
        model = parse_machine_file(BRAND)[0]
        profile = controller.new_profile_from_catalog(model)
        self.assertEqual(profile["name"], "Exemple L1 10W")
        self.assertEqual((profile["w"], profile["h"], profile["focal"], profile["max_speed"]),
                         (400.0, 380.0, 0.08, 15000.0))
        self.assertEqual(profile["accel"], 800.0)            # non publié : la valeur affichée reste
        self.assertEqual(combo.currentText(), "Exemple L1 10W")
        self.assertEqual(fields.applied[-1]["w"], 400.0)
        self.assertEqual(fields.selected, 1)

    def test_same_model_twice_gets_a_number(self):
        controller, _fields, _combo = self._controller()
        model = parse_machine_file(BRAND)[1]
        controller.new_profile_from_catalog(model)
        controller.new_profile_from_catalog(model)
        controller.new_profile_from_catalog(model)
        self.assertEqual(controller.names(), ["Atelier", "Exemple L2", "Exemple L2 (2)", "Exemple L2 (3)"])

    def test_dialog(self):
        models = parse_machine_file(BRAND) + [MachineModel("Autre", "X", work_area_mm=(100.0, 100.0))]
        dialog = MachineCatalogDialog(models)
        try:
            self.assertEqual(dialog.chosen().title, "Exemple L1 10W")      # premier modèle donné
            self.assertEqual(dialog.tree.topLevelItemCount(), 2)
            dialog.search.setText("l2")
            self.assertEqual(dialog.chosen().title, "Exemple L2")
            self.assertIn("Exemple L2", dialog.details.text())
            dialog.search.setText("introuvable")
            self.assertIsNone(dialog.chosen())
            dialog.search.setText("l1")
            self.assertIn("455 nm", dialog.details.text())
            self.assertIn("https://exemple.test/manuel.pdf", dialog.details.text())
        finally:
            dialog.deleteLater()

    def test_page_button_opens_one_catalog_and_creates_the_profile(self):
        from laser_studio.ui.settings.machine_params.builder import open_machine_catalog
        from laser_studio.ui.settings.machine_params.page import MachineParamsPage
        controller, _fields, _combo = self._controller()
        page = MachineParamsPage()
        dialog = open_machine_catalog(page, controller, roots=[MACHINES_DIR])
        try:
            self.assertIs(open_machine_catalog(page, controller, roots=[MACHINES_DIR]), dialog)
            dialog.search.setText("phecda 10")
            dialog.accept()
            self.assertEqual(controller.current_name(), "Elegoo Phecda 10W")
        finally:
            dialog.deleteLater()
            page.deleteLater()


if __name__ == "__main__":
    unittest.main()
