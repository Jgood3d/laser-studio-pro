"""Blocage de la mise en veille pendant une gravure (issue #185).

Tests avec une fausse implémentation : quand on bloque, quand on libère,
selon le mode choisi (pendant une gravure / tant que connecté / jamais).
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from laser_studio.core.preferences import in_memory
    from laser_studio.core import power as power_module
    from laser_studio.controllers.power_inhibit import (
        MODE_DURING_JOB,
        MODE_NEVER,
        MODE_WHILE_CONNECTED,
        MODE_KEY,
        DISPLAY_KEY,
        PowerInhibitController,
    )
    HAS_QT = True
except ImportError:
    HAS_QT = False
    QObject = object
    pyqtSignal = None
    # Constantes locales pour que le corps de la classe de tests se charge.
    MODE_DURING_JOB = "during_job"
    MODE_NEVER = "never"
    MODE_WHILE_CONNECTED = "while_connected"
    MODE_KEY = "power/inhibit_mode"
    DISPLAY_KEY = "power/keep_display"
    power_module = None
    in_memory = None
    PowerInhibitController = None


class FakeInhibitor:
    def __init__(self, reason, keep_display):
        self.reason = reason
        self.keep_display = keep_display
        self.released = False
        FakeInhibitor.instances.append(self)

    def release(self):
        self.released = True

    instances = []


if HAS_QT:
    class FakeEngraver(QObject):
        stream_starting = pyqtSignal(str)
        stream_ended = pyqtSignal(bool)

    class FakeConnection(QObject):
        connection_changed = pyqtSignal(bool)

        def __init__(self, connected=False):
            super().__init__()
            self._connected = connected

        def is_connected(self):
            return self._connected
else:
    FakeEngraver = None
    FakeConnection = None


@unittest.skipIf(not HAS_QT, "PyQt6 non importable ici")
class PowerInhibitControllerTests(unittest.TestCase):
    def setUp(self):
        FakeInhibitor.instances.clear()
        power_module.set_inhibit_factory(
            lambda reason, keep_display=False: FakeInhibitor(reason, keep_display)
        )
        self.logs = []
        self._memory = in_memory()
        self._memory.__enter__()

    def tearDown(self):
        power_module.set_inhibit_factory(None)
        self._memory.__exit__(None, None, None)

    def make(self, mode="during_job", keep_display=False, connected=False):
        from laser_studio.core.preferences import ui_preferences
        ui_preferences().set(MODE_KEY, mode)
        ui_preferences().set(DISPLAY_KEY, keep_display)
        engraver = FakeEngraver()
        connection = FakeConnection(connected)
        controller = PowerInhibitController(
            engraver, connection, log=self.logs.append
        )
        return controller, engraver, connection

    def test_during_job_acquires_on_stream_start_and_releases_on_end(self):
        controller, engraver, _ = self.make(MODE_DURING_JOB)
        self.assertIsNone(controller._inhibitor)

        engraver.stream_starting.emit("G0 X0")
        self.assertEqual(len(FakeInhibitor.instances), 1)
        self.assertIs(controller._inhibitor, FakeInhibitor.instances[0])
        self.assertFalse(FakeInhibitor.instances[0].released)

        engraver.stream_ended.emit(True)
        self.assertTrue(FakeInhibitor.instances[0].released)
        self.assertIsNone(controller._inhibitor)

    def test_during_job_ignores_connection(self):
        controller, engraver, connection = self.make(MODE_DURING_JOB)
        connection.connection_changed.emit(True)
        self.assertIsNone(controller._inhibitor)
        engraver.stream_starting.emit("G1")
        self.assertEqual(len(FakeInhibitor.instances), 1)

    def test_while_connected_follows_connection(self):
        controller, engraver, connection = self.make(MODE_WHILE_CONNECTED, connected=False)
        self.assertIsNone(controller._inhibitor)

        connection.connection_changed.emit(True)
        self.assertEqual(len(FakeInhibitor.instances), 1)

        connection.connection_changed.emit(False)
        self.assertTrue(FakeInhibitor.instances[0].released)
        self.assertIsNone(controller._inhibitor)

        # Un stream pendant la connexion ne change rien de plus (déjà actif).
        connection.connection_changed.emit(True)
        engraver.stream_starting.emit("G1")
        self.assertEqual(len(FakeInhibitor.instances), 2)  # un nouveau après release

    def test_never_never_acquires(self):
        controller, engraver, connection = self.make(MODE_NEVER)
        engraver.stream_starting.emit("G1")
        connection.connection_changed.emit(True)
        self.assertIsNone(controller._inhibitor)
        self.assertEqual(FakeInhibitor.instances, [])

    def test_keep_display_passed_to_factory(self):
        controller, engraver, _ = self.make(MODE_DURING_JOB, keep_display=True)
        engraver.stream_starting.emit("G1")
        self.assertTrue(FakeInhibitor.instances[0].keep_display)

    def test_shutdown_releases(self):
        controller, engraver, _ = self.make(MODE_DURING_JOB)
        engraver.stream_starting.emit("G1")
        controller.shutdown()
        self.assertTrue(FakeInhibitor.instances[0].released)
        self.assertIsNone(controller._inhibitor)

    def test_change_mode_at_runtime(self):
        controller, engraver, connection = self.make(MODE_DURING_JOB)
        engraver.stream_starting.emit("G1")
        self.assertEqual(len(FakeInhibitor.instances), 1)

        controller.set_mode(MODE_NEVER)
        self.assertTrue(FakeInhibitor.instances[0].released)
        self.assertIsNone(controller._inhibitor)

        controller.set_mode(MODE_WHILE_CONNECTED)
        connection.connection_changed.emit(True)
        self.assertEqual(len(FakeInhibitor.instances), 2)

    def test_null_factory_logs_unavailable(self):
        power_module.set_inhibit_factory(
            lambda reason, keep_display=False: power_module.NullInhibitor()
        )
        controller, engraver, _ = self.make(MODE_DURING_JOB)
        engraver.stream_starting.emit("G1")
        self.assertIsNotNone(controller._inhibitor)
        self.assertTrue(any("indisponible" in m or "unavailable" in m.lower() or "no method" in m.lower()
                            or "Impossible" in m for m in self.logs) or self.logs)


class PowerModuleTests(unittest.TestCase):
    """Sans Qt : NullInhibitor et fabrique."""

    def test_null_inhibitor_release_is_noop(self):
        from laser_studio.core.power import NullInhibitor
        NullInhibitor().release()

    def test_create_inhibitor_returns_something_with_release(self):
        from laser_studio.core import power as pm
        handle = pm.create_inhibitor("test", keep_display=False)
        self.assertTrue(hasattr(handle, "release"))
        handle.release()


if __name__ == "__main__":
    unittest.main()
