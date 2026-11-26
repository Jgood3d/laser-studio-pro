"""Texte qui suit le contour d'un autre objet, et texte de médaille (un en haut, un en bas d'un contour fermé),
côté éditeur : sélection, étape d'annulation, recalage quand le guide bouge. Le calcul est dans
vector/text_follow.py.

    text_follow = TextFollowActions(editor)      # editor.text_follow
    text_follow.follow_selection()               # texte + objet sélectionnés (Maj + clic)
    text_follow.resync_linked(moved_objects)     # signal objects_moved du canevas
"""
from laser_studio.i18n import tr
from laser_studio.models.vector_objects import TextObject
from laser_studio.vector import text_follow


class TextFollowActions:
    """`editor` : VectorEditorController (sélection, document, canevas, boîtes de saisie, signaux)."""

    def __init__(self, editor):
        self.editor = editor

    def follow_selection(self):
        """Commande « Texte sur contour » : fait suivre au texte sélectionné le contour de l'autre objet
        sélectionné, puis ouvre ses réglages (position, côté, distance) ; un texte qui suivait déjà un contour
        est seulement recalé."""
        editor = self.editor
        pair = text_follow.text_follow_pair(editor.selected_objects())
        resync = bool(pair and getattr(pair[0], "follow_points", None))
        text = self.follow()
        if text is None:
            editor.dialogs.info(tr("vector.text_follow_title"), tr("vector.text_follow_need_two"))
            return
        editor.properties_changed.emit(text)
        if resync:
            editor.status.emit(tr("vector.text_resynced"))
        else:
            editor.edit_dialog(editor.canvas.item_for(text), text)

    def follow(self):
        """Fait suivre au texte sélectionné le contour de l'autre objet sélectionné. Le contour est COPIÉ dans
        le texte : le guide n'est pas modifié (on peut le garder pour la découpe ou le supprimer). Si le texte
        suivait déjà un contour, ses réglages sont conservés. Renvoie le texte, ou None si la sélection ne
        convient pas."""
        editor = self.editor
        pair = text_follow.text_follow_pair(editor.selected_objects())
        if pair is None:
            return None
        text, guide = pair
        points = text_follow.follow_path(guide)
        if points is None:
            return None
        editor.canvas.push_undo_snapshot()
        text_follow.apply_follow(text, guide, points, keep_settings=text_follow.follows_a_path(text))
        editor.document.notify_changed([text])
        editor.canvas.select_objects([text])
        return text

    def resync(self, text, push_undo=True):
        """Recopie le contour du guide dans le texte (le guide a bougé ou changé de taille), en gardant la
        position, le côté et la distance. False si le guide n'existe plus."""
        editor = self.editor
        guide = text_follow.linked_guide(text, editor.document.objects)
        points = text_follow.follow_path(guide) if guide is not None else None
        if points is None:
            return False
        if push_undo:
            editor.canvas.push_undo_snapshot()
        text_follow.apply_follow(text, guide, points, keep_settings=True)
        editor.document.notify_changed([text])
        return True

    def resync_linked(self, guides):
        """Recale, sans nouvelle étape d'annulation, les textes liés aux objets `guides` (déplacés ou modifiés à
        la souris). Renvoie le nombre de textes recalés."""
        ids = {obj.id for obj in guides if not isinstance(obj, TextObject)}
        texts = [obj for obj in self.editor.document.objects
                 if isinstance(obj, TextObject) and getattr(obj, "follow_guide_id", None) in ids]
        return sum(1 for text in texts if self.resync(text, push_undo=False))

    def medal(self):
        """Texte de médaille : un texte en haut et un en bas, à l'intérieur du contour fermé sélectionné."""
        editor = self.editor
        guide = text_follow.medal_guide(editor.selected_objects())
        if guide is None:
            editor.dialogs.info(tr("vector.medal_title"), tr("vector.medal_need_guide"))
            return
        values = editor.forms.medal(editor.layers)
        if values is None:
            return
        points = text_follow.closed_follow_path(guide)
        editor.canvas.push_undo_snapshot()
        created = text_follow.medal_texts(guide, points, **values)
        for obj in created:
            editor.document.add(obj)
        if created:
            editor.canvas.select_objects(created)
