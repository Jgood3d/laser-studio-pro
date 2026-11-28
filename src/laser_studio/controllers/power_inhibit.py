"""Contrôleur : empêche la mise en veille selon le mode choisi dans les préférences.

Modes (`ui_preferences` clé `power/inhibit_mode`) :
- ``during_job`` (défaut) : de stream_starting jusqu'à stream_ended (file comprise) ;
- ``while_connected`` : tant que le graveur est connecté ;
- ``never`` : aucun blocage.

Case ``power/keep_display`` (défaut False) : garder aussi l'écran allumé.

    controller = PowerInhibitController(engraver, connection, log=window.log_message)
    # plus tard, à la fermeture :
    controller.shutdown()
"""
from __future__ import annotations

from PyQt6.QtCore import QObject

from laser_studio.core.power import NullInhibitor, create_inhibitor
from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import tr

MODE_DURING_JOB = "during_job"
MODE_WHILE_CONNECTED = "while_connected"
MODE_NEVER = "never"
MODE_KEY = "power/inhibit_mode"
DISPLAY_KEY = "power/keep_display"


class PowerInhibitController(QObject):
    """Écoute les signaux du graveur et de la connexion, gère un seul inhibiteur."""

    def __init__(self, engraver, connection, log=None, parent=None):
        super().__init__(parent)
        self._engraver = engraver
        self._connection = connection
        self._log = log or (lambda _msg: None)
        self._inhibitor = None
        self._streaming = False
        self._connected = bool(getattr(connection, "is_connected", lambda: False)())

        engraver.stream_starting.connect(self._on_stream_starting)
        engraver.stream_ended.connect(self._on_stream_ended)
        connection.connection_changed.connect(self._on_connection_changed)

        # Appliquer l'état initial (ex. reconnexion au démarrage).
        self._sync()

    def mode(self) -> str:
        value = ui_preferences().get(MODE_KEY, MODE_DURING_JOB)
        if value not in (MODE_DURING_JOB, MODE_WHILE_CONNECTED, MODE_NEVER):
            return MODE_DURING_JOB
        return value

    def keep_display(self) -> bool:
        return ui_preferences().get_bool(DISPLAY_KEY, False)

    def set_mode(self, mode: str) -> None:
        if mode not in (MODE_DURING_JOB, MODE_WHILE_CONNECTED, MODE_NEVER):
            mode = MODE_DURING_JOB
        ui_preferences().set(MODE_KEY, mode)
        self._sync()

    def set_keep_display(self, keep: bool) -> None:
        ui_preferences().set(DISPLAY_KEY, bool(keep))
        self._sync()

    def _on_stream_starting(self, _gcode=None):
        self._streaming = True
        self._sync()

    def _on_stream_ended(self, _clean=None):
        self._streaming = False
        self._sync()

    def _on_connection_changed(self, connected: bool):
        self._connected = bool(connected)
        self._sync()

    def _should_inhibit(self) -> bool:
        mode = self.mode()
        if mode == MODE_NEVER:
            return False
        if mode == MODE_WHILE_CONNECTED:
            return self._connected
        # during_job
        return self._streaming

    def _sync(self) -> None:
        want = self._should_inhibit()
        if want and self._inhibitor is None:
            self._acquire()
        elif not want and self._inhibitor is not None:
            self._release()

    def _acquire(self) -> None:
        reason = tr("power.inhibit_reason")
        keep = self.keep_display()
        try:
            inhibitor = create_inhibitor(reason, keep_display=keep)
        except Exception as exc:
            self._log(tr("power.inhibit_failed").format(error=exc))
            self._inhibitor = None
            return
        if isinstance(inhibitor, NullInhibitor) or type(inhibitor).__name__ == "NullInhibitor":
            # NullInhibitor : moyen indisponible. On le mémorise pour ne pas
            # spammer la console à chaque synchro, et on prévient une fois.
            self._inhibitor = inhibitor
            self._log(tr("power.inhibit_unavailable"))
            return
        self._inhibitor = inhibitor
        self._log(tr("power.inhibit_active"))

    def _release(self) -> None:
        if self._inhibitor is None:
            return
        try:
            self._inhibitor.release()
        except Exception as exc:
            self._log(tr("power.release_failed").format(error=exc))
        self._inhibitor = None

    def shutdown(self) -> None:
        """À appeler à la fermeture de l'application : lève toujours le blocage."""
        self._streaming = False
        self._connected = False
        self._release()
