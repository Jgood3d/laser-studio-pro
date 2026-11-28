"""Fenêtres de saisie de l'éditeur vectoriel, vues par les contrôleurs : chaque méthode ouvre une fenêtre
(texte, forme, médaille, générateurs, bibliothèque, imbrication, série, gabarit) et renvoie ce que l'utilisateur a choisi,
en valeurs simples, ou None s'il a annulé.

Les contrôleurs (controllers/vector_editor.py, generators.py, layout.py) ne construisent aucune fenêtre :
ils reçoivent un EditorForms, comme ils reçoivent UserDialogs pour les messages. Dans les tests, on leur
passe un objet qui a les mêmes méthodes et répond à la place de l'utilisateur.

    forms = EditorForms(window)
    picked = forms.generators("box", {"box": (layers.layers, bed_w, bed_h, saved), ...})
    if picked is not None:
        kind, choice = picked
"""
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication, QDialog

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
from laser_studio.i18n import tr
from laser_studio.ui.utils import palette_icon


def _without_emoji(label):
    """Libellé sans son emoji de tête (📦, 🧩), qui ferait doublon avec l'icône."""
    return label.split(" ", 1)[-1] if label and not label[0].isalnum() else label


# Générateurs de la fenêtre unique, dans l'ordre de sa liste : (clé, clé du titre, icône).
GENERATORS = (
    ("library", "ui.vector_library", "view-app-grid"),
    ("box", "ui.vector_box_generator", "draw-cuboid"),
    ("puzzle", "ui.vector_puzzle_generator", "games-config-board"),
    ("ornament", "ui.vector_ornament_generator", "draw-ellipse"),
    ("keychain", "ui.vector_keychain_generator", "keychain"),
)


def _keychain_dialog(parent, layers, saved):
    # Importé ici : la fenêtre du porte-clés charge ses polices à la première ouverture.
    from laser_studio.ui.dialogs.keychain import KeychainGeneratorDialog
    return KeychainGeneratorDialog(parent=parent, layers=layers, saved_settings=saved)


def _library_dialog(parent, categories, icon_size, on_icon_size):
    # Importé ici : la fenêtre (et ses vignettes) n'est chargée qu'à la première ouverture.
    from laser_studio.ui.dialogs.library import LibraryDialog
    dialog = LibraryDialog(parent, categories, icon_size)
    dialog.icon_size_changed.connect(on_icon_size)
    return dialog


# Fenêtre de chaque générateur, à partir des arguments décrits dans EditorForms.generators.
GENERATOR_DIALOGS = {
    "library": _library_dialog,
    "box": lambda parent, layers, bed_w, bed_h, saved: BoxGeneratorDialog(parent, layers, bed_w, bed_h, saved),
    "puzzle": lambda parent, layers, bed_w, bed_h, saved, target: PuzzleGeneratorDialog(
        parent=parent, layers=layers, bed_w=bed_w, bed_h=bed_h, saved_settings=saved, target_image_rect=target),
    "ornament": lambda parent, layers, saved, sheet: OrnamentGeneratorDialog(
        parent=parent, layers=layers, saved_settings=saved, sheet=sheet),
    "keychain": _keychain_dialog,
}


def _ornament_choice(dialog):
    names = dialog.names() or [""]
    return SimpleNamespace(balls=[(name, dialog.params(name)) for name in names], font=dialog.font_options(),
                           sheet=dialog.sheet(), cut_layer=dialog.cut_layer_id(),
                           engrave_layer=dialog.engrave_layer_id(), settings=dialog.settings())


# Ce que chaque fenêtre de générateur validée renvoie au contrôleur (voir EditorForms.generators).
GENERATOR_CHOICES = {
    "library": lambda d: d.chosen(),
    "box": lambda d: SimpleNamespace(params=d.params(), cut_layer=d.cut_layer_id(),
                                     engrave_layer=d.engrave_layer_id(), decors=d.decors(), settings=d.settings()),
    "puzzle": lambda d: SimpleNamespace(params=d.params(), cut_layer=d.cut_layer_id(), settings=d.settings()),
    "ornament": _ornament_choice,
    "keychain": lambda d: SimpleNamespace(params=d.params(), font=d.font_options(), cut_layer=d.cut_layer_id(),
                                          engrave_layer=d.engrave_layer_id(), settings=d.settings()),
}


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

    def generators(self, start, requests):
        """Fenêtre unique des générateurs, ouverte sur `start` (« library », « box », « puzzle », « ornament »,
        « keychain »). `requests` : arguments de chaque générateur, par clé (un générateur absent n'a pas de
        page) :

        - library : (catégories, taille des vignettes, rappel de la taille choisie) ;
        - box : (layers, bed_w, bed_h, saved) ;
        - puzzle : (layers, bed_w, bed_h, saved, target_image_rect) ;
        - ornament : (layers, saved, sheet) ;
        - keychain : (layers, saved).

        Renvoie (clé, choix) pour le générateur validé, ou None si annulé :

        - library : (modèle, variantes, textes) ;
        - box : params, cut_layer, engrave_layer, decors, settings ;
        - puzzle : params (position comprise), cut_layer, settings ;
        - ornament : balls (liste de (prénom, params), au moins une), font (famille, gras, italique),
          sheet (largeur, hauteur), cut_layer, engrave_layer, settings ;
        - keychain : params, font, cut_layer, engrave_layer, settings."""
        # Importé ici : la fenêtre (et celle du porte-clés, qui charge ses polices) n'est chargée qu'à l'usage.
        from laser_studio.ui.dialogs.generators import GeneratorsDialog

        pages = [(kind, _without_emoji(tr(title_key)), palette_icon(icon, QApplication.palette()),
                  lambda parent, kind=kind: GENERATOR_DIALOGS[kind](parent, *requests[kind]))
                 for kind, title_key, icon in GENERATORS if kind in requests]
        dialog = GeneratorsDialog(self.parent, pages, start)
        if not _accepted(dialog) or dialog.chosen is None:
            return None
        return dialog.chosen, GENERATOR_CHOICES[dialog.chosen](dialog.page(dialog.chosen))

    def jig(self, layers, obj_w, obj_h, has_selection, bed_w, bed_h, saved):
        """Gabarit : params, position_mode, position_xy, with_base, cut_layer, settings."""
        dialog = JigDialog(self.parent, layers, obj_w, obj_h, has_selection, bed_w, bed_h, saved)
        if not _accepted(dialog):
            return None
        return SimpleNamespace(params=dialog.jig_params(), position_mode=dialog.position_mode(),
                               position_xy=dialog.position_xy(), with_base=dialog.with_base(),
                               cut_layer=dialog.cut_layer_id(), settings=dialog.settings())

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
