"""Fenêtres de saisie de l'éditeur vectoriel, vues par les contrôleurs : chaque méthode ouvre une fenêtre
(texte, forme, médaille, générateurs, bibliothèque, imbrication, série, gabarit) et renvoie ce que l'utilisateur a choisi,
en valeurs simples, ou None s'il a annulé.

Les contrôleurs (controllers/vector_editor.py, generators.py, layout.py) ne construisent aucune fenêtre :
ils reçoivent un EditorForms, comme ils reçoivent UserDialogs pour les messages. Dans les tests, on leur
passe un objet qui a les mêmes méthodes et répond à la place de l'utilisateur.

    forms = EditorForms(window)
    choice = forms.box(layers.layers, bed_w, bed_h, saved)
    if choice is not None:
        result = box_generator.build_box(choice.params)
"""
from types import SimpleNamespace

from PyQt6.QtWidgets import QDialog

from laser_studio.ui.dialogs.box_generator import BoxGeneratorDialog
from laser_studio.ui.dialogs.jig import JigDialog
from laser_studio.ui.dialogs.nesting import NestingDialog
from laser_studio.ui.dialogs.ornament import OrnamentGeneratorDialog
from laser_studio.ui.dialogs.puzzle import PuzzleGeneratorDialog
from laser_studio.ui.dialogs.serial_duplicate import SerialDuplicateDialog
from laser_studio.ui.vector_editor.assign_layer_dialog import AssignLayerDialog
from laser_studio.ui.vector_editor.medal_dialog import MedalTextDialog
from laser_studio.ui.vector_editor.resize_dialog import GroupResizeDialog
from laser_studio.ui.vector_editor.shape_dialog import ShapeInsertDialog
from laser_studio.ui.vector_editor.text_dialog import TextInsertDialog


def _accepted(dialog):
    return dialog.exec() == QDialog.DialogCode.Accepted


class EditorForms:
    """Fenêtres modales, centrées sur `parent`."""

    def __init__(self, parent=None):
        self.parent = parent

    # -- objets du canevas

    # `before_apply()` : appelé une fois la fenêtre validée, avant que ses réglages soient appliqués à l'objet
    # (la fenêtre l'a remis dans son état d'origine) : c'est là que l'appelant prend l'étape d'annulation.

    def text(self, layers, obj, on_preview, is_new=False, before_apply=lambda: None):
        """Réglages du texte `obj`, avec aperçu en direct (`on_preview()`). Validé : les réglages sont
        appliqués à `obj` et renvoie True ; annulé : `obj` revient à son état d'origine, renvoie False."""
        dialog = TextInsertDialog(layers, text_obj=obj, parent=self.parent, is_new=is_new, on_preview=on_preview)
        if not dialog.exec():
            return False
        before_apply()
        dialog.get_object()
        return True

    def shape(self, layers, obj=None, before_apply=lambda: None):
        """Nouvelle forme (`obj` None) ou modification de `obj`. Renvoie la forme, ou None si annulé."""
        dialog = ShapeInsertDialog(layers, shape_obj=obj, parent=self.parent)
        if not dialog.exec():
            return None
        before_apply()
        return dialog.get_object()

    def svg_properties(self, layers, obj, title, before_apply=lambda: None):
        """Calque d'un tracé importé : appliqué à `obj` si validé (renvoie True)."""
        dialog = AssignLayerDialog(layers, svg_obj=obj, title=title, parent=self.parent)
        if not dialog.exec():
            return False
        before_apply()
        dialog.apply_to(obj)
        return True

    def medal(self, layers):
        """Textes de médaille : arguments de text_follow.medal_texts (textes, police, taille, marge, calque),
        ou None."""
        dialog = MedalTextDialog(layers, parent=self.parent)
        return dialog.values() if dialog.exec() else None

    def group_resize(self, width_mm, height_mm):
        """Nouvelle taille (largeur, hauteur) en mm de la sélection, à partir de sa taille actuelle, ou None."""
        dialog = GroupResizeDialog(width_mm, height_mm, self.parent)
        return dialog.size_mm() if _accepted(dialog) else None

    # -- générateurs

    def box(self, layers, bed_w, bed_h, saved):
        """Boîte à encoches : params, cut_layer, engrave_layer, decors, settings."""
        dialog = BoxGeneratorDialog(self.parent, layers, bed_w, bed_h, saved)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(params=dialog.params(), cut_layer=dialog.cut_layer_id(),
                               engrave_layer=dialog.engrave_layer_id(), decors=dialog.decors(),
                               settings=dialog.settings())

    def puzzle(self, layers, bed_w, bed_h, saved, target_image_rect):
        """Puzzle : params (position comprise), cut_layer, settings."""
        dialog = PuzzleGeneratorDialog(parent=self.parent, layers=layers, bed_w=bed_w, bed_h=bed_h,
                                       saved_settings=saved, target_image_rect=target_image_rect)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(params=dialog.params(), cut_layer=dialog.cut_layer_id(), settings=dialog.settings())

    def ornament(self, layers, saved, sheet):
        """Boules de Noël : balls (liste de (prénom, params), au moins une), font (famille, gras, italique),
        sheet (largeur, hauteur), cut_layer, engrave_layer, settings."""
        dialog = OrnamentGeneratorDialog(parent=self.parent, layers=layers, saved_settings=saved, sheet=sheet)
        if not _accepted(dialog):
            return None
        names = dialog.names() or [""]
        return SimpleNamespace(balls=[(name, dialog.params(name)) for name in names], font=dialog.font_options(),
                               sheet=dialog.sheet(), cut_layer=dialog.cut_layer_id(),
                               engrave_layer=dialog.engrave_layer_id(), settings=dialog.settings())

    def keychain(self, layers, saved):
        """Porte-clés : params, font, cut_layer, engrave_layer, settings."""
        # Importé ici, comme avant : la fenêtre du porte-clés charge ses polices à la première ouverture.
        from laser_studio.ui.dialogs.keychain import KeychainGeneratorDialog

        dialog = KeychainGeneratorDialog(parent=self.parent, layers=layers, saved_settings=saved)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(params=dialog.params(), font=dialog.font_options(), cut_layer=dialog.cut_layer_id(),
                               engrave_layer=dialog.engrave_layer_id(), settings=dialog.settings())

    def jig(self, layers, obj_w, obj_h, has_selection, bed_w, bed_h, saved):
        """Gabarit : params, position_mode, position_xy, with_base, cut_layer, settings."""
        dialog = JigDialog(self.parent, layers, obj_w, obj_h, has_selection, bed_w, bed_h, saved)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(params=dialog.jig_params(), position_mode=dialog.position_mode(),
                               position_xy=dialog.position_xy(), with_base=dialog.with_base(),
                               cut_layer=dialog.cut_layer_id(), settings=dialog.settings())

    # -- bibliothèque

    def library(self, categories, icon_size, on_icon_size=lambda size: None):
        """Bibliothèque de modèles : (modèle, variantes, textes) choisis, ou None. `on_icon_size(px)` :
        taille des vignettes changée par l'utilisateur (à mémoriser)."""
        # Importé ici : la fenêtre (et ses vignettes) n'est chargée qu'à la première ouverture.
        from laser_studio.ui.dialogs.library import LibraryDialog

        dialog = LibraryDialog(self.parent, categories, icon_size)
        dialog.icon_size_changed.connect(on_icon_size)
        if not _accepted(dialog):
            return None
        return dialog.chosen()

    # -- mise en page

    def nesting(self, bed_w, bed_h, n_selected, n_candidates, saved):
        """Imbrication : scope ("selection" ou "all"), options (feuille, marges, angles…), settings."""
        dialog = NestingDialog(self.parent, bed_w, bed_h, n_selected, n_candidates, saved)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(scope=dialog.scope(), options=dialog.options(), settings=dialog.settings())

    def serial(self, texts, n_objects, width, height, bed_w, bed_h, saved):
        """Duplication en série : params, settings."""
        dialog = SerialDuplicateDialog(self.parent, texts, n_objects, width, height, bed_w, bed_h, saved)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(params=dialog.params(), settings=dialog.settings())
