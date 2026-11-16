"""Liaison d'un champ de l'interface à un réglage d'un modèle
(models/settings.py), dans les deux sens.

    bind(page.focal_spin, machine, "focal")

- saisie dans le champ -> `model.update(focal=...)` ;
- réglage modifié dans le modèle (profil, projet, code) -> champ mis à jour.

Pas de boucle sans fin : le modèle n'émet que si la valeur change vraiment,
et le champ n'est réécrit que s'il affiche autre chose. Les signaux propres
du champ (valueChanged, toggled…) restent émis, pour ceux qui y sont
abonnés.
"""
from PyQt6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox, QDoubleSpinBox,
                             QPlainTextEdit, QSpinBox, QTextEdit)


def _accessors(widget):
    """(lire, écrire, signal de changement) selon le type du champ."""
    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        return widget.value, widget.setValue, widget.valueChanged
    if isinstance(widget, QCheckBox):
        return widget.isChecked, widget.setChecked, widget.toggled
    if isinstance(widget, QComboBox):
        return widget.currentIndex, widget.setCurrentIndex, widget.currentIndexChanged
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        return widget.toPlainText, widget.setPlainText, widget.textChanged
    raise TypeError(f"Champ non pris en charge : {type(widget).__name__}")


def bind(widget, model, field, to_widget=None, from_widget=None):
    """Lie `widget` au réglage `field` de `model`.

    `to_widget(valeur du modèle)` / `from_widget(valeur du champ)` :
    conversions facultatives (ex. code "M4" <-> index de la liste).
    Le champ prend aussitôt la valeur du modèle."""
    read, write, signal = _accessors(widget)
    to_widget = to_widget or (lambda v: v)
    from_widget = from_widget or (lambda v: v)

    def push_to_model(*_args):
        model.update(**{field: from_widget(read())})

    def pull_from_model(changes):
        if field in changes:
            value = to_widget(changes[field])
            if read() != value:
                write(value)

    signal.connect(push_to_model)
    model.changed.connect(pull_from_model)
    value = to_widget(model.get(field))
    if read() != value:
        write(value)
    # Une valeur que le champ ne peut pas afficher (hors bornes, trop de
    # décimales) : le modèle reprend celle que le champ affiche vraiment.
    if isinstance(widget, QAbstractSpinBox) and from_widget(read()) != model.get(field):
        push_to_model()
