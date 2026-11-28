"""Empêcher la mise en veille de l'ordinateur pendant une gravure.

    from laser_studio.core.power import inhibit_sleep

    handle = inhibit_sleep("Gravure en cours", keep_display=False)
    ...
    handle.release()

Une implémentation par système (Windows, macOS, Linux), choisie selon
`sys.platform`. Si rien n'est disponible, une implémentation vide : la
gravure continue, un message peut être journalisé.

Le blocage est toujours levé à la fin du processus (Windows le fait
automatiquement ; macOS avec `caffeinate -w <pid>` ; Linux en fermant le
descripteur ou en tuant `systemd-inhibit`).
"""
from __future__ import annotations

import os
import sys
from typing import Protocol


class SleepInhibitor(Protocol):
    def release(self) -> None: ...


class NullInhibitor:
    """Aucun moyen disponible : ne fait rien."""

    def release(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Windows : SetThreadExecutionState
# ---------------------------------------------------------------------------

class _WindowsInhibitor:
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002

    def __init__(self, keep_display: bool):
        import ctypes
        self._set = ctypes.windll.kernel32.SetThreadExecutionState
        flags = self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
        if keep_display:
            flags |= self.ES_DISPLAY_REQUIRED
        self._set(flags)

    def release(self) -> None:
        self._set(self.ES_CONTINUOUS)


# ---------------------------------------------------------------------------
# macOS : caffeinate -i [-d] -w <pid>
# ---------------------------------------------------------------------------

class _MacInhibitor:
    def __init__(self, keep_display: bool):
        import subprocess
        args = ["caffeinate", "-i", "-w", str(os.getpid())]
        if keep_display:
            args.insert(2, "-d")
        self._proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def release(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except Exception:  # timeout ou processus déjà mort : forcer kill
                self._proc.kill()


# ---------------------------------------------------------------------------
# Linux : logind Inhibit via D-Bus, sinon systemd-inhibit
# ---------------------------------------------------------------------------

class _LinuxDBusInhibitor:
    """Garde le descripteur renvoyé par login1.Manager.Inhibit ouvert."""

    def __init__(self, reason: str, keep_display: bool):
        from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage, QDBusUnixFileDescriptor

        bus = QDBusConnection.systemBus()
        if not bus.isConnected():
            raise RuntimeError("D-Bus system bus unavailable")

        iface = QDBusInterface(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            bus,
        )
        if not iface.isValid():
            raise RuntimeError("login1 Manager unavailable")

        what = "sleep:idle"
        reply = iface.call("Inhibit", what, "Laser Studio Pro", reason, "block")
        if reply.type() != QDBusMessage.MessageType.ReplyMessage:
            raise RuntimeError(reply.errorMessage() or "Inhibit failed")

        args = reply.arguments()
        if not args:
            raise RuntimeError("Inhibit returned no file descriptor")
        fd_obj = args[0]
        if isinstance(fd_obj, QDBusUnixFileDescriptor):
            self._fd = os.dup(fd_obj.fileDescriptor())
        else:
            self._fd = int(fd_obj)

        self._screensaver_cookie = None
        if keep_display:
            self._screensaver_cookie = self._inhibit_screensaver(bus, reason)

    def _inhibit_screensaver(self, bus, reason: str):
        try:
            from PyQt6.QtDBus import QDBusInterface, QDBusMessage
            iface = QDBusInterface(
                "org.freedesktop.ScreenSaver",
                "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver",
                bus,
            )
            if not iface.isValid():
                return None
            reply = iface.call("Inhibit", "Laser Studio Pro", reason)
            if reply.type() == QDBusMessage.MessageType.ReplyMessage and reply.arguments():
                return int(reply.arguments()[0])
        except Exception:  # ScreenSaver absent ou D-Bus en échec : pas d'inhibition écran
            return None
        return None

    def release(self) -> None:
        if getattr(self, "_fd", None) is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        if self._screensaver_cookie is not None:
            try:
                from PyQt6.QtDBus import QDBusConnection, QDBusInterface
                bus = QDBusConnection.systemBus()
                iface = QDBusInterface(
                    "org.freedesktop.ScreenSaver",
                    "/org/freedesktop/ScreenSaver",
                    "org.freedesktop.ScreenSaver",
                    bus,
                )
                if iface.isValid():
                    iface.call("UnInhibit", self._screensaver_cookie)
            except Exception:  # UnInhibit best-effort : le descripteur sleep est déjà fermé
                pass
            self._screensaver_cookie = None


class _LinuxSystemdInhibitor:
    """Fallback : systemd-inhibit --what=sleep:idle … tail --pid=<pid> -f /dev/null."""

    def __init__(self, reason: str, keep_display: bool):
        import subprocess
        what = "sleep:idle"
        if keep_display:
            what = "sleep:idle:handle-lid-switch"
        args = [
            "systemd-inhibit",
            f"--what={what}",
            "--who=Laser Studio Pro",
            f"--why={reason}",
            "--mode=block",
            "tail", f"--pid={os.getpid()}", "-f", "/dev/null",
        ]
        self._proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def release(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except Exception:  # timeout ou processus déjà mort : forcer kill
                self._proc.kill()


def _linux_inhibit(reason: str, keep_display: bool) -> SleepInhibitor:
    try:
        return _LinuxDBusInhibitor(reason, keep_display)
    except Exception:  # D-Bus / logind indisponible : essayer systemd-inhibit
        pass
    try:
        return _LinuxSystemdInhibitor(reason, keep_display)
    except Exception:  # systemd-inhibit absent ou échec : pas de blocage
        pass
    return NullInhibitor()


def inhibit_sleep(reason: str = "Gravure en cours", keep_display: bool = False) -> SleepInhibitor:
    """Bloque la mise en veille (et optionnellement l'extinction d'écran).

    Renvoie un objet avec `release()`. Toujours sûr : en cas d'échec,
    renvoie un `NullInhibitor` (la gravure n'est pas bloquée).
    """
    try:
        platform = sys.platform
        if platform == "win32":
            return _WindowsInhibitor(keep_display)
        if platform == "darwin":
            return _MacInhibitor(keep_display)
        if platform.startswith("linux"):
            return _linux_inhibit(reason, keep_display)
    except Exception:  # API système indisponible : la gravure continue sans blocage
        pass
    return NullInhibitor()


# Point d'extension pour les tests : remplacer la fabrique.
_factory = inhibit_sleep


def set_inhibit_factory(factory) -> None:
    """Remplace `inhibit_sleep` (tests). Passer `None` pour restaurer."""
    global _factory
    _factory = factory if factory is not None else inhibit_sleep


def create_inhibitor(reason: str = "Gravure en cours", keep_display: bool = False) -> SleepInhibitor:
    """Comme `inhibit_sleep`, mais passe par la fabrique (surchargeable en tests)."""
    return _factory(reason, keep_display)
