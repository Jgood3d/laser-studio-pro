"""Historique des gravures : une ligne par job envoyé au graveur (date, durée réelle et estimée, issue,
statistiques du G-Code, réglages de la machine), dans un fichier JSON Lines du dossier des données.
Sert à garder des traces utiles et à comparer la durée estimée à la durée réelle.

    history = JobHistory()                 # historique-gravures.jsonl
    history.append({...})
    history.entries()                      # du plus ancien au plus récent
"""
import csv
import json
import os

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger
from laser_studio.core.paths import get_autosave_dir

log = get_logger()

FILE_NAME = "historique-gravures.jsonl"

# Colonnes de l'export CSV, dans l'ordre (clés d'une entrée).
CSV_FIELDS = ("started_at", "result", "duration_s", "estimated_s", "lines", "acked_lines", "burn_mm",
              "travel_mm", "max_feed", "max_power", "bounds", "profile", "max_speed", "accel", "s_max", "laser_cmd")


def default_path():
    return os.path.join(get_autosave_dir(), FILE_NAME)


class JobHistory(QObject):
    """`path` : fichier de l'historique. Une ligne illisible (fichier modifié à la main) est ignorée."""

    changed = pyqtSignal()

    def __init__(self, path=None, parent=None):
        super().__init__(parent)
        self.path = path or default_path()

    def append(self, entry):
        """Ajoute une gravure à la fin du fichier (jamais réécrit en entier : rien ne se perd)."""
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            log.warning("Historique des gravures : écriture impossible dans %s", self.path, exc_info=True)
            return False
        self.changed.emit()
        return True

    def entries(self):
        """Gravures enregistrées, de la plus ancienne à la plus récente."""
        try:
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []
        except OSError:
            log.warning("Historique des gravures : lecture impossible de %s", self.path, exc_info=True)
            return []
        out = []
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
        return out

    def clear(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        self.changed.emit()

    def export_csv(self, path):
        """Écrit l'historique en CSV (séparateur « ; », lisible par un tableur français). OSError si échec."""
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";", extrasaction="ignore")
            writer.writeheader()
            for entry in self.entries():
                row = dict(entry)
                if isinstance(row.get("bounds"), list):
                    row["bounds"] = " ".join(str(v) for v in row["bounds"])
                writer.writerow(row)
