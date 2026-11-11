"""Déplacement de la sélection aux flèches du clavier (sans Qt) : pas selon les touches maintenues."""
NUDGE_STEP_MM = 1.0          # flèche seule
NUDGE_COARSE_MM = 10.0       # avec Maj
NUDGE_FINE_MM = 0.1          # avec Alt (prioritaire si Maj est aussi enfoncée)
NUDGE_UNDO_WINDOW_S = 0.8    # pressions plus rapprochées que cela : un seul « Annuler » pour la série


def nudge_step(shift=False, alt=False):
    if alt:
        return NUDGE_FINE_MM
    return NUDGE_COARSE_MM if shift else NUDGE_STEP_MM
