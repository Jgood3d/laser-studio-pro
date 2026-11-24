"""Enregistrement de chaque gravure dans l'historique (models/job_history.py) : début et fin de l'envoi,
durée réelle, durée estimée quand le G-Code vient d'une génération, issue, statistiques du G-Code et
réglages de la machine.

    recorder = JobHistoryRecorder(history, connection, context=lambda: {...})
    engraver.stream_starting.connect(recorder.job_started)
    engraver.stream_ended.connect(recorder.job_ended)
    job.generated.connect(recorder.remember_estimate)
"""
import hashlib
import threading
import time

from laser_studio.gcode.stats import gcode_statistics

# Issue d'une gravure (champ « result »).
DONE = "done"            # tout envoyé, machine revenue à l'arrêt
STOPPED = "stopped"      # arrêtée par l'utilisateur (Reset, arrêt d'urgence)
ERROR = "error"          # GRBL a refusé une ligne : machine arrêtée
INTERRUPTED = "interrupted"   # autre fin non propre (liaison perdue…)


def _key(gcode_text):
    return hashlib.sha1(gcode_text.encode("utf-8", "replace")).hexdigest()


class JobHistoryRecorder:
    """`history` : JobHistory ; `connection` : MachineConnection (thread d'envoi : lignes acquittées, arrêt
    sur erreur ou par l'utilisateur) ; `context()` : réglages à noter (profil machine, vitesse maximale,
    accélération, S-Max, commande laser) ; `clock()` : heure (secondes), remplaçable pour les tests.

    Graveur simulé (connection.simulation_speed(), LASER_STUDIO_SIMULATION) : la durée mesurée est multipliée
    par le facteur de vitesse de la simulation, pour donner celle de la machine simulée, comparable à
    l'estimation ; le facteur est noté (« simulation »)."""

    def __init__(self, history, connection, context=lambda: {}, clock=time.time):
        self.history = history
        self.connection = connection
        self._context = context
        self._clock = clock
        self._estimates = {}         # empreinte du G-Code généré -> durée estimée (s)
        self._current = None

    def remember_estimate(self, gcode_text, _lines=0, _avg_power=0.0, seconds=0.0):
        """G-Code généré (signal JobController.generated) : sa durée estimée, retrouvée s'il est envoyé."""
        self._estimates = {_key(gcode_text): float(seconds)}

    def job_started(self, gcode_text):
        started = self._clock()
        entry = {"started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started)),
                 "estimated_s": self._estimates.get(_key(gcode_text))}
        entry.update(self._context())
        speed = getattr(self.connection, "simulation_speed", lambda: None)()
        if speed:
            entry["simulation"] = speed
        stats = {}
        # Statistiques calculées à côté : environ une seconde pour un gros G-Code d'image.
        worker = threading.Thread(target=lambda: stats.update(gcode_statistics(gcode_text)), daemon=True)
        worker.start()
        self._current = (started, entry, stats, worker)

    def job_ended(self, clean_finish):
        if self._current is None:
            return None
        started, entry, stats, worker = self._current
        self._current = None
        worker.join(timeout=10)
        streamer = getattr(self.connection, "streamer", None)
        if clean_finish:
            result = DONE
        elif getattr(streamer, "stopped_on_error", False):
            result = ERROR
        elif getattr(streamer, "stopped_by_user", False):
            result = STOPPED
        else:
            result = INTERRUPTED
        elapsed = (self._clock() - started) * (entry.get("simulation") or 1.0)
        entry.update(result=result, duration_s=round(elapsed, 1),
                     acked_lines=getattr(streamer, "acked", None))
        entry.update({k: stats.get(k) for k in ("lines", "burn_mm", "travel_mm", "max_feed", "max_power", "bounds")})
        self.history.append(entry)
        return entry
