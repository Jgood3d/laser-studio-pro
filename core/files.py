"""Écriture sûre des fichiers de données (autosave, file d'attente...) :
atomique, et en arrière-plan pour ne pas figer l'interface."""
import collections
import json
import os
import threading


def atomic_write_text(path, text, encoding="utf-8"):
    """Écrit `text` dans `path` de façon atomique : le contenu est d'abord
    écrit et vidé sur disque dans un fichier voisin « .tmp », puis ce fichier
    REMPLACE l'ancien d'un seul coup (os.replace). Un plantage, une coupure de
    courant ou un disque plein en cours d'écriture laisse donc l'ancien
    fichier intact au lieu d'un fichier tronqué — précieux pour l'autosave et
    la file d'attente, qui servent justement à se remettre d'un incident."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path, data, **dump_kwargs):
    """Sérialise `data` en JSON puis l'écrit de façon atomique (voir
    atomic_write_text). La sérialisation se fait AVANT toute écriture : une
    donnée non sérialisable ne touche donc jamais au fichier existant."""
    atomic_write_text(path, json.dumps(data, **dump_kwargs))


class BackgroundFileWriter:
    """Écrit des fichiers de données (autosave, file d'attente...) dans un
    thread à part, un à la fois, pour ne jamais figer l'interface : la mise en
    forme du contenu (encodage PNG, JSON) ET l'écriture disque se font hors du
    fil de l'interface. Mesuré : ~0,6 s pour une image de 3000 px, ~1,3 s à
    5000 px, jusqu'à ~0,4 s à chaque modification d'une file de 60 Mo.

    - submit(path, produce) : `produce()` (appelée DANS le thread) renvoie le
      texte à écrire. Si plusieurs demandes arrivent pour un même chemin avant
      que la première ne démarre, seule la dernière est écrite.
    - L'écriture est atomique (fichier « .tmp » puis os.replace).
    - discard(path) : annule l'écriture en attente, invalide celle en cours et
      supprime le fichier (ex. autosave devenu inutile après un enregistrement).
    - wait_idle(timeout) : attend la fin des écritures (à appeler à la fermeture).
    - pop_error(path) : renvoie (une fois) la dernière erreur d'écriture."""

    def __init__(self):
        self._cond = threading.Condition()
        self._pending = collections.OrderedDict()   # chemin -> (produce, génération)
        self._generation = {}                       # chemin -> compteur d'annulations
        self._errors = {}
        self._busy = False
        self._running = False

    def submit(self, path, produce):
        with self._cond:
            self._pending[path] = (produce, self._generation.get(path, 0))
            if not self._running:
                self._running = True
                threading.Thread(target=self._run, daemon=True, name="BackgroundFileWriter").start()
            self._cond.notify_all()

    def discard(self, path):
        with self._cond:
            self._generation[path] = self._generation.get(path, 0) + 1
            self._pending.pop(path, None)
            self._errors.pop(path, None)
            # Sous le verrou : l'écrivain ne remplace le fichier que sous ce même
            # verrou, donc aucune écriture annulée ne peut le recréer après coup.
            try:
                os.remove(path)
            except OSError:
                pass

    def wait_idle(self, timeout=None):
        with self._cond:
            return self._cond.wait_for(lambda: not self._pending and not self._busy, timeout)

    def pop_error(self, path):
        with self._cond:
            return self._errors.pop(path, None)

    def _run(self):
        while True:
            with self._cond:
                if not self._pending:
                    self._running = False
                    self._busy = False
                    self._cond.notify_all()
                    return
                path, (produce, generation) = self._pending.popitem(last=False)
                self._busy = True
            tmp_path = path + ".tmp"
            try:
                text = produce()
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(text)
                    f.flush()
                    os.fsync(f.fileno())
                with self._cond:
                    if self._generation.get(path, 0) == generation:
                        os.replace(tmp_path, path)
                    else:
                        os.remove(tmp_path)   # annulé pendant l'écriture
            except BaseException as exc:  # ne jamais tuer le thread : la sauvegarde suivante doit rester possible
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                with self._cond:
                    self._errors[path] = exc
            finally:
                with self._cond:
                    self._busy = False
                    self._cond.notify_all()


_BACKGROUND_WRITER = BackgroundFileWriter()


def get_background_writer():
    """Écrivain de fichiers en arrière-plan partagé par toute l'application."""
    return _BACKGROUND_WRITER
