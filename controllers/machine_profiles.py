"""Profils machine : liste, choix, création, mise à jour, suppression, et
mémoire continue des calques et réglages mécaniques de la machine active."""

import copy
import json
from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from i18n import tr

# Délai avant l'écriture sur disque après un changement de calque (ms) :
# regroupe les rafales de changements (saisie d'un nombre...).
PERSIST_DELAY_MS = 600


@dataclass
class ProfileFields:
    """Ce que les profils machine lisent et réappliquent dans la fenêtre."""

    # Tous les champs d'un profil, tels qu'affichés (pages, matériaux,
    # calques).
    capture: Callable[[], dict]
    # Réapplique les champs d'un profil (sauf les calques).
    apply: Callable[[dict], None]
    # Réapplique les calques mémorisés : (calques, en_entier).
    apply_layers: Callable[[list, bool], None]
    # Ce qui est mémorisé en continu dans le profil actif : calques et
    # réglages mécaniques (décalage, surbalayage).
    memory: Callable[[], dict]
    # Après un changement de profil : résolution et qualité suivent la
    # focale.
    profile_selected: Callable[[], None]
    # Les calques liés suivent la focale validée.
    link_layers_to_focal: Callable[[], None]


class MachineProfilesController:
    """Liste des profils machine (`profiles`) et ses actions.

        machines = MachineProfilesController(
            self, page.profile_combo, fields,
            save_settings=self.save_machine_settings,
        )
        page.profile_selected.connect(machines.on_selected)

    `combo` : la liste des profils (page Paramètres du graveur). `fields` :
    voir ProfileFields. `save_settings()` : écrit les réglages machine sur
    disque (après un changement de calque).

    Les calques et réglages mécaniques de la machine active sont rangés dans
    son profil à chaque changement (schedule_persist), une fois le
    démarrage terminé (persist_ready).
    """

    def __init__(self, parent, combo, fields, save_settings):
        self._parent = parent
        self._combo = combo
        self._fields = fields
        self._save_settings = save_settings
        self.profiles = []
        # Faux tant que le démarrage n'est pas terminé : avant, on
        # écraserait les calques enregistrés par ceux, par défaut, du
        # démarrage.
        self.persist_ready = False
        self._applying = False
        self._persist_timer = None

    # -- liste

    def load(self, raw_json, last_name, default_profile):
        """Liste enregistrée (JSON), profil sélectionné la dernière fois, et
        profil créé si la liste est vide. Applique en entier le profil
        sélectionné (calques compris : aucun objet n'est encore sur le
        canevas au démarrage)."""
        try:
            self.profiles = json.loads(raw_json) if raw_json else []
        except (TypeError, ValueError):
            self.profiles = []
        if not self.profiles:
            self.profiles = [default_profile]
        self.refresh_combo(select_name=last_name)
        # refresh_combo sélectionne avec les signaux bloqués : on applique
        # donc nous-mêmes le profil sélectionné.
        index = self._combo.currentIndex()
        if 0 <= index < len(self.profiles):
            self.apply(self.profiles[index], full=True)

    def to_json(self):
        return json.dumps(self.profiles)

    def current_name(self):
        """Nom du profil sélectionné, ou None."""
        if self._combo.currentIndex() < 0:
            return None
        return self._combo.currentText()

    def refresh_combo(self, select_name=None):
        """Remplit la liste (signaux bloqués), et sélectionne `select_name`
        s'il existe."""
        self._combo.blockSignals(True)
        self._combo.clear()
        for profile in self.profiles:
            self._combo.addItem(profile["name"])
        if select_name:
            index = self._combo.findText(select_name)
            if index >= 0:
                self._combo.setCurrentIndex(index)
        self._combo.blockSignals(False)

    def _current_index(self):
        index = self._combo.currentIndex()
        return index if 0 <= index < len(self.profiles) else None

    # -- application

    def apply(self, profile, full=False):
        """Applique un profil : champs, puis calques.

        Les calques mémorisés sont lus AVANT de toucher au moindre champ, et
        la mémoire continue est suspendue pendant l'opération : changer la
        focale ou le décalage émet des signaux qui auraient sinon écrit les
        calques de l'ANCIENNE machine dans le profil de la NOUVELLE.
        """
        saved_layers = copy.deepcopy(profile.get("layers"))
        self._applying = True
        try:
            self._fields.apply(profile)
        finally:
            self._applying = False
        self._fields.apply_layers(saved_layers, full)

    def on_selected(self, index):
        """Profil choisi dans la liste."""
        if index < 0 or index >= len(self.profiles):
            return
        self.apply(self.profiles[index])
        self._fields.profile_selected()

    # -- actions

    def new_profile(self):
        """Nouveau profil, avec les réglages affichés."""
        name, ok = QInputDialog.getText(
            self._parent, tr("machine.new_title"), tr("machine.new_prompt")
        )
        if not ok or not name.strip():
            return
        profile = {"name": name.strip()}
        profile.update(self._fields.capture())
        self.profiles.append(profile)
        self.refresh_combo(select_name=profile["name"])

    def update_profile(self):
        """Enregistre les réglages affichés dans le profil sélectionné."""
        index = self._current_index()
        if index is None:
            return
        name = self.profiles[index]["name"]
        updated = self._fields.capture()
        updated["name"] = name
        self.profiles[index] = updated
        # Le pas de remplissage des calques suit la focale validée : plus
        # besoin de lier chaque calque à la main.
        self._fields.link_layers_to_focal()
        QMessageBox.information(
            self._parent,
            tr("machine.updated_title"),
            tr("machine.updated_body").format(name=name),
        )

    def delete_profile(self):
        """Supprime le profil sélectionné (jamais le dernier)."""
        index = self._current_index()
        if index is None:
            return
        if len(self.profiles) <= 1:
            QMessageBox.warning(
                self._parent,
                tr("machine.cannot_delete_title"),
                tr("machine.cannot_delete_body"),
            )
            return
        name = self.profiles[index]["name"]
        reply = QMessageBox.question(
            self._parent,
            tr("machine.delete_title"),
            tr("machine.delete_body").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.profiles.pop(index)
            self.refresh_combo()

    # -- mémoire continue

    def store_memory(self):
        """Range les calques et réglages mécaniques affichés dans le profil
        actif (en mémoire ; écrits sur disque par save_settings)."""
        if self._applying:
            return
        index = self._current_index()
        if index is not None:
            self.profiles[index].update(self._fields.memory())

    def schedule_persist(self, *_args):
        """Un calque ou un réglage mécanique a changé : rangé tout de suite
        dans le profil actif (si on change de machine juste après, il est
        déjà dans SON profil), écrit sur disque peu après."""
        if not self.persist_ready or self._applying:
            return
        self.store_memory()
        if self._persist_timer is None:
            self._persist_timer = QTimer()
            self._persist_timer.setSingleShot(True)
            self._persist_timer.setInterval(PERSIST_DELAY_MS)
            self._persist_timer.timeout.connect(self._save_settings)
        self._persist_timer.start()
