"""Contrôleurs (controllers/) testés seuls, sans la fenêtre : faux onglets,
faux graveur, boîtes de message interceptées."""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PIL import Image
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QInputDialog,
        QMessageBox,
    )
    from laser_studio.controllers import job_queue as jq
    from laser_studio.controllers.job_queue import Engraver, JobQueueController
    from laser_studio.controllers.materials import MaterialsController
    from laser_studio.controllers.matrix_image import MatrixImageController
    from laser_studio.controllers import project as project_module
    from laser_studio.controllers.png2svg import Png2SvgController
    from laser_studio.controllers.project import ProjectController
    from laser_studio.vector_layers import LayerManager
except ImportError:  # PyQt6, Pillow... manquants
    JobQueueController = None

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
    '<path d="M0 0 L50 0 L50 20 Z"/><rect x="60" y="5" width="20" '
    'height="10"/></svg>'
)


class _QtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.messages = []
        for name in ("information", "warning", "critical"):
            patcher = mock.patch.object(
                QMessageBox,
                name,
                side_effect=lambda *a, _n=name: self.messages.append(_n),
            )
            patcher.start()
            self.addCleanup(patcher.stop)


@unittest.skipIf(JobQueueController is None, "PyQt6 non importable ici")
class Png2SvgControllerTests(_QtTest):
    def make(self, layers=None):
        added = []
        controller = Png2SvgController(
            None,
            layers or LayerManager(),
            bed_height=lambda: 300.0,
            add_to_vector_editor=added.extend,
        )
        return controller, added

    def test_svg_objects_go_to_the_vector_editor(self):
        controller, added = self.make()
        controller.send_to_vector_editor(SVG)
        self.assertGreaterEqual(len(added), 1)
        self.assertEqual(self.messages, ["information"])  # succès

    def test_empty_svg_adds_nothing(self):
        controller, added = self.make()
        controller.send_to_vector_editor(
            '<svg xmlns="http://www.w3.org/2000/svg"/>'
        )
        self.assertEqual((added, self.messages), ([], ["information"]))

    def test_invalid_svg_is_reported(self):
        controller, added = self.make()
        controller.send_to_vector_editor("pas du SVG")
        self.assertEqual((added, self.messages), ([], ["critical"]))

    def test_without_layer_nothing_happens(self):
        layers = LayerManager()
        layers.layers = []
        controller, added = self.make(layers)
        controller.send_to_vector_editor(SVG)
        self.assertEqual((added, self.messages), ([], ["warning"]))


class FakeMatrixPage:
    def __init__(self):
        self.source_image = None
        self.source = None
        self.checked = False

    def set_source_image(self, image, name, width_mm):
        self.source_image = image
        self.source = (image.mode, name, width_mm)

    def set_image_test_checked(self, checked):
        self.checked = checked

    def tile_settings(self):
        return (100.0, 10.0, 10.0, 0.5, 0.5)


@unittest.skipIf(JobQueueController is None, "PyQt6 non importable ici")
class MatrixImageControllerTests(_QtTest):
    def make(self, loaded=None):
        page = FakeMatrixPage()
        settings = dict(
            bright=0,
            contrast=0,
            gamma=100,
            sharp=0,
            invert=False,
            algo="Floyd-Steinberg",
        )
        controller = MatrixImageController(
            page, loaded_image=lambda: loaded, image_settings=lambda: settings
        )
        return controller, page

    def test_loaded_image_is_used_at_its_width(self):
        controller, page = self.make((Image.new("RGB", (40, 20)), 120.0))
        controller.use_loaded_image()
        self.assertEqual(page.source[0], "L")
        self.assertEqual(page.source[2], 120.0)

    def test_without_loaded_image_a_message_is_shown(self):
        controller, page = self.make()
        controller.use_loaded_image()
        self.assertEqual((page.source, self.messages), (None, ["information"]))

    def test_checking_the_test_takes_the_loaded_image(self):
        controller, page = self.make((Image.new("L", (40, 20)), 80.0))
        controller.on_image_test_toggled(False)
        self.assertIsNone(page.source_image)
        controller.on_image_test_toggled(True)
        self.assertIsNotNone(page.source_image)

    def test_real_width_from_a_plausible_resolution(self):
        width = MatrixImageController._real_width_mm
        image = Image.new("L", (300, 10))
        self.assertAlmostEqual(width(image, (300, 300)), 25.4)
        self.assertIsNone(width(image, (5, 5)))  # résolution invraisemblable
        self.assertIsNone(width(image, None))

    def test_tile_is_an_engraving_of_the_image(self):
        controller, page = self.make((Image.new("L", (200, 200), 128), 100.0))
        tile = controller.build_tile(10.0)
        self.assertEqual(tile["arr"].shape, (100, 100))  # 10 mm à 10 l/mm
        self.assertFalse(tile["grayscale"])


class FakeQueueTab:
    def __init__(self):
        self.names, self.status, self.sent = [], "", []
        self.run_enabled, self.row = True, -1

    def add_job(self, name):
        self.names.append(name)

    def remove_job(self, row):
        del self.names[row]

    def set_jobs(self, names):
        self.names = list(names)

    def job_names(self):
        return list(self.names)

    def selected_row(self):
        return self.row

    def select_job(self, row):
        self.row = row

    def set_status(self, text):
        self.status = text

    def set_run_enabled(self, enabled):
        self.run_enabled = enabled

    # Fait aussi office de suivi du G-Code envoyé (SentGcodeLog).
    def clear_lines(self):
        self.sent = []

    def append_lines(self, lines):
        self.sent += lines


class FakeEngraver:
    """Envoi instantané : chaque job finit proprement, sauf ceux listés."""

    def __init__(self, connected=True, failing=()):
        self.calls, self.connected, self.failing = [], connected, failing

    def engraver(self):
        def record(name, result=None):
            return lambda *a: (self.calls.append((name,) + a[:1]), result)[1]

        return Engraver(
            is_connected=lambda: self.connected,
            last_state=lambda: "Idle",
            confirm_homed=lambda: True,
            start_stream=self.start_stream,
            stream_ended=record("stream_ended"),
            pause_status_poll=record("pause"),
            resume_status_poll=record("resume"),
            jobs_finished=record("jobs_finished"),
        )

    def start_stream(self, gcode, on_finished):
        self.calls.append(("start", gcode))
        on_finished(gcode not in self.failing)


@unittest.skipIf(JobQueueController is None, "PyQt6 non importable ici")
class JobQueueControllerTests(_QtTest):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        patcher = mock.patch.object(jq, "get_autosave_dir", lambda: self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Yes,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def make(self, gcodes=(), **engraver):
        tab, fake = FakeQueueTab(), FakeEngraver(**engraver)
        console = {"text": ""}
        queue = JobQueueController(
            tab,
            None,
            fake.engraver(),
            current_gcode=lambda: console["text"],
            log_to_console=lambda text: None,
            sent_log=tab,
        )
        for gcode in gcodes:
            console["text"] = gcode
            queue.add_current_gcode()
        return queue, tab, fake

    def test_jobs_are_added_with_unique_names(self):
        queue, tab, _ = self.make(["G1 X1", "G1 X2"])
        self.assertEqual(len(set(tab.names)), 2)
        self.assertEqual(
            [job["gcode"] for job in queue.jobs], ["G1 X1", "G1 X2"]
        )
        queue2, _, _ = self.make([""])
        self.assertEqual((queue2.jobs, self.messages), ([], ["warning"]))

    def test_reordering_follows_the_list(self):
        queue, tab, _ = self.make(["G1 X1", "G1 X2", "G1 X3"])
        tab.names = [tab.names[2], tab.names[0], tab.names[1]]
        queue.on_reordered()
        self.assertEqual(
            [job["gcode"] for job in queue.jobs], ["G1 X3", "G1 X1", "G1 X2"]
        )

    def test_queue_is_saved_and_restored(self):
        queue, tab, _ = self.make(["G1 X1", "G1 X2"])
        path = os.path.join(self.dir, jq.QUEUE_FILENAME)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(queue.jobs, f)
        restored, tab2, _ = self.make()
        restored.load()
        self.assertEqual(tab2.names, tab.names)
        self.assertEqual(
            [job["gcode"] for job in restored.jobs], ["G1 X1", "G1 X2"]
        )

    def test_jobs_are_sent_one_after_the_other(self):
        queue, tab, fake = self.make(["G1 X1", "G1 X2"])
        queue.run()
        starts = [c[1] for c in fake.calls if c[0] == "start"]
        self.assertEqual(starts, ["G1 X1", "G1 X2"])
        self.assertEqual(fake.calls[0], ("pause",))
        self.assertEqual(fake.calls[-2:], [("resume",), ("jobs_finished",)])
        self.assertEqual((queue.jobs, tab.names), ([], []))  # file vidée
        self.assertTrue(tab.run_enabled)
        self.assertEqual(self.messages, ["information"])

    def test_an_interrupted_job_stops_the_queue(self):
        queue, tab, fake = self.make(["G1 X1", "G1 X2"], failing=("G1 X1",))
        queue.run()
        self.assertEqual(
            [c[1] for c in fake.calls if c[0] == "start"], ["G1 X1"]
        )
        self.assertEqual(len(queue.jobs), 2)  # file gardée
        self.assertEqual(self.messages, ["warning"])

    def test_nothing_is_sent_when_disconnected(self):
        queue, _, fake = self.make(["G1 X1"], connected=False)
        queue.run()
        self.assertEqual((fake.calls, self.messages), ([], ["warning"]))


@unittest.skipIf(JobQueueController is None, "PyQt6 non importable ici")
class ProjectControllerTests(_QtTest):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        patcher = mock.patch.object(
            project_module, "get_autosave_dir", lambda: self.dir
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # Projets récents dans un fichier temporaire, jamais dans les
        # réglages de l'utilisateur.
        settings_path = os.path.join(self.dir, "UIConfig.ini")
        patcher = mock.patch.object(
            project_module,
            "QSettings",
            lambda *_a: QSettings(settings_path, QSettings.Format.IniFormat),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.state = {"bright": 12, "raw_image_b64": None}
        self.image = Image.new("L", (8, 4), 200)
        self.restored, self.recent = [], []
        self.project = ProjectController(
            None,
            capture=lambda: (dict(self.state), self.image),
            restore=lambda data, image: self.restored.append((data, image)),
            show_recent_projects=self.recent.append,
            log_to_console=lambda text: None,
        )

    def save_to(self, path):
        with mock.patch.object(
            project_module.QFileDialog,
            "getSaveFileName",
            return_value=(path, ""),
        ):
            return self.project.save()

    def test_saved_file_contains_the_state_and_the_image(self):
        path = os.path.join(self.dir, "p.lsp")
        self.assertTrue(self.save_to(path))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["bright"], 12)
        image = ProjectController.decode_image(data["raw_image_b64"])
        self.assertEqual((image.size, image.getpixel((0, 0))), ((8, 4), 200))
        self.assertEqual(self.recent[-1], [path])  # projets récents
        self.assertEqual(self.messages, ["information"])

    def test_cancelled_or_failed_save(self):
        self.assertFalse(self.save_to(""))
        self.assertFalse(self.save_to("/nexiste/pas/p.lsp"))
        self.assertEqual(self.messages, ["critical"])

    def test_opened_project_is_restored_with_its_image(self):
        path = os.path.join(self.dir, "p.lsp")
        self.save_to(path)
        self.project.open_path(path)
        data, image = self.restored[-1]
        self.assertEqual(data["bright"], 12)
        self.assertEqual(image.size, (8, 4))

    def test_a_broken_file_changes_nothing(self):
        path = os.path.join(self.dir, "casse.lsp")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{pas du json")
        self.project.open_path(path)
        self.assertEqual((self.restored, self.messages), ([], ["critical"]))

    def test_data_without_image(self):
        self.assertIsNone(
            self.project.data(encode_image=False)["raw_image_b64"]
        )
        self.image = None
        self.assertIsNone(self.project.data()["raw_image_b64"])


@unittest.skipIf(JobQueueController is None, "PyQt6 non importable ici")
class MaterialsControllerTests(_QtTest):
    def make(self):
        self.applied, self.current = [], {
            "sp_e": 1,
            "pw_e": 2,
            "sp_c": 3,
            "pw_c": 4,
            "pass_c": 5,
        }
        combo = QComboBox()
        self.addCleanup(combo.deleteLater)
        materials = {"Personnalisé": {"sp_e": 9}, "Bois": {"sp_e": 8}}
        combo.addItems(list(materials))
        controller = MaterialsController(
            None,
            combo,
            materials,
            current_settings=lambda: dict(self.current),
            apply_settings=self.applied.append,
        )
        return controller, combo

    def test_selected_material_is_applied_and_saved(self):
        controller, combo = self.make()
        combo.setCurrentText("Bois")
        controller.apply_selected()
        self.assertEqual(self.applied, [{"sp_e": 8}])
        controller.save_selected()
        self.assertEqual(controller.materials["Bois"], self.current)

    def test_new_and_deleted_materials(self):
        controller, combo = self.make()
        with mock.patch.object(
            QInputDialog, "getText", return_value=(" Verre ", True)
        ):
            controller.new_material()
        self.assertEqual(combo.currentText(), "Verre")
        self.assertIn("Verre", controller.materials)
        combo.setCurrentText("Personnalisé")
        controller.delete_selected()  # interdit
        self.assertIn("Personnalisé", controller.materials)
        with mock.patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            combo.setCurrentText("Verre")
            controller.delete_selected()
        self.assertNotIn("Verre", controller.materials)

    def test_replacing_the_list(self):
        controller, combo = self.make()
        controller.set_materials({"A": {}, "B": {}}, block_signals=True)
        self.assertEqual(
            [combo.itemText(i) for i in range(combo.count())], ["A", "B"]
        )


if __name__ == "__main__":
    unittest.main()
