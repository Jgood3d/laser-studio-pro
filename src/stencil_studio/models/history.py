"""Annuler / refaire des réglages, du cadre et du sujet, comme la page web (histSnap, histCommit, undo, redo) :
chaque état est un instantané (texte JSON) ; un état identique au précédent n'est pas empilé ; 100 étapes au plus.

    history = History()
    history.reset(snapshot)                 # nouvelle image : historique vidé
    history.commit(snapshot)                # après une série de changements (la fenêtre regroupe sur 450 ms)
    previous = history.undo(snapshot)       # état à restaurer, ou None
"""
import json

MAX_STEPS = 100


def snapshot(state, frame, subject_box=None):
    """Instantané des réglages, du cadre et du rectangle du sujet."""
    return json.dumps({"S": state, "F": frame, "B": subject_box}, sort_keys=True)


class History:
    def __init__(self):
        self.reset(None)

    def reset(self, current):
        self.undo_stack, self.redo_stack, self.current = [], [], current

    def commit(self, state):
        """Nouvel état : empilé s'il diffère du précédent ; « refaire » est alors vidé."""
        if self.current is None:
            self.current = state
            return
        if state == self.current:
            return
        self.undo_stack.append(self.current)
        del self.undo_stack[:-MAX_STEPS]
        self.redo_stack.clear()
        self.current = state

    def undo(self, state):
        """État précédent à restaurer (après avoir enregistré `state`), ou None."""
        self.commit(state)
        if not self.undo_stack:
            return None
        self.redo_stack.append(self.current)
        self.current = self.undo_stack.pop()
        return self.current

    def redo(self, state):
        self.commit(state)
        if not self.redo_stack:
            return None
        self.undo_stack.append(self.current)
        self.current = self.redo_stack.pop()
        return self.current

    def can_undo(self):
        return bool(self.undo_stack)

    def can_redo(self):
        return bool(self.redo_stack)
