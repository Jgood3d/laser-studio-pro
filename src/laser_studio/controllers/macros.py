"""Macros de l'utilisateur : les envoyer au graveur et les modifier.

    macros = MacroController(model, engraver, dialogs, profile_name=machines.current_name,
                             edit=lambda macros, profiles, read, write: MacroEditorDialog(...).run())
    panel.macro_requested.connect(macros.run)

Une macro part par EngraverController.send_direct (comme le zéro ou le retour au zéro), seulement si l'état
du graveur le permet (models/machine_state.py : prêt, ni job, ni homing, ni alarme). Une macro qui allume le laser est toujours confirmée (Non par défaut) ; les
autres seulement si la case « Confirmer » est cochée.
"""
from laser_studio.grbl.macros import MacroError, dump_macros, load_macros
from laser_studio.i18n import tr
from laser_studio.i18n.errors import generator_error_text
from laser_studio.models import machine_state as ms


def macro_error_text(error):
    """Message traduit d'une MacroError (clé `macros.err.<code>`)."""
    return generator_error_text("macros", error)


class MacroController:
    """`model` : MacrosModel ; `engraver` : EngraverController ; `dialogs` : UserDialogs. `profile_name()` : profil machine affiché ; `profiles()` : noms des
    profils (filtre des macros). L'éditeur est la page « Macros » de la fenêtre Paramètres : il est rempli par
    editor_args() et sa liste validée passe par save()."""

    def __init__(self, model, engraver, dialogs, *, profile_name=lambda: None, profiles=lambda: []):
        self.model = model
        self.engraver = engraver
        self.dialogs = dialogs
        self._profile_name = profile_name
        self._profiles = profiles

    def visible(self):
        """(rang, macro) des macros du profil machine affiché."""
        return self.model.visible_for(self._profile_name())

    def run(self, index):
        """Envoie la macro de rang `index` (rang dans la liste complète)."""
        if not 0 <= index < len(self.model.macros):
            return False
        macro = self.model.macros[index]
        if not self.engraver.allowed(ms.MACRO, "laser.connect_via_usb"):
            return False
        gcode = "\n".join(macro.gcode)
        if macro.fires_laser:
            if not self.dialogs.confirm_default_no(tr("macros.title"),
                                                   tr("macros.confirm_laser").format(name=macro.name, gcode=gcode)):
                return False
        elif macro.confirm:
            if not self.dialogs.confirm(tr("macros.title"), tr("macros.confirm").format(name=macro.name, gcode=gcode)):
                return False
        self.engraver.send_direct(list(macro.gcode))
        return True

    # -- modifier

    def editor_args(self):
        """(macros, profils, read_file, write_file) pour remplir l'éditeur ; prévient d'abord si le fichier des
        macros était illisible (il n'est remplacé qu'à l'enregistrement)."""
        if self.model.load_error is not None:
            self.dialogs.warning(tr("macros.title"), tr("macros.load_error").format(
                path=self.model.path, error=macro_error_text(self.model.load_error)))
        return list(self.model.macros), list(self._profiles()), self.read_file, self.write_file

    def save(self, macros):
        """La liste validée dans l'éditeur remplace l'ancienne et est enregistrée ; False en cas d'échec."""
        try:
            self.model.set_macros(macros)
        except OSError as error:
            self.dialogs.error(tr("macros.title"), tr("macros.save_error").format(path=self.model.path, error=error))
            return False
        return True

    @staticmethod
    def read_file(path):
        """Macros d'un fichier à importer ; lève MacroError (message par macro_error_text) ou OSError."""
        with open(path, encoding="utf-8") as f:
            return load_macros(f.read())

    @staticmethod
    def write_file(path, macros):
        """Exporte `macros` dans `path` (OSError en cas d'échec)."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(dump_macros(macros))


__all__ = ["MacroController", "MacroError", "macro_error_text"]
