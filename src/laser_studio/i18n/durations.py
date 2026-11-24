"""Durée affichée à l'utilisateur, la même partout (G-Code généré, matrice de test, motif aller/retour,
estimation rapide) : « 46 s », « 3 min 12 s », « 2 h 05 min », unités traduites.

    duration_text(192)      # « 3 min 12 s »
"""
from laser_studio.gcode.common import duration_parts
from laser_studio.i18n import tr


def duration_text(seconds):
    hours, minutes, secs = duration_parts(seconds)
    if hours:
        return tr("time.hours").format(h=hours, m=minutes)
    if minutes:
        return tr("time.minutes").format(m=minutes, s=secs)
    return tr("time.seconds").format(s=secs)
