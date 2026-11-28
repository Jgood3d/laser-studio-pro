"""Onglet « Calques » et ses profils matériaux, reliés au modèle des calques et aux profils machine.

    tab, materials = build_layers_tab(layers, machine, machines, state, dialogs, parent)
"""
from laser_studio.controllers.materials import DEFAULT_MATERIALS_DB, MaterialsController
from laser_studio.ui.tabs.layers.tab import LayersTab


def build_layers_tab(layers, machine, machines, state, dialogs, parent):
    """Tableau de `layers` (LayersModel) ; pas de remplissage d'après la focale de `machine`.
    Un matériau mémorise les réglages des calques (lus et appliqués par `state`, WindowState) ;
    matériaux et calques sont rangés dans le profil de la machine active (`machines`).
    Renvoie (LayersTab, MaterialsController)."""
    materials_db = dict(DEFAULT_MATERIALS_DB)
    tab = LayersTab(layers, materials_db.keys(), focal_getter=lambda: machine.focal)
    # Profils matériaux (barre d'outils de l'onglet) : un matériau mémorise les réglages des
    # calques ; le choisir dans la liste met le tableau à jour (WindowState.apply_job_settings).
    materials = MaterialsController(
        parent,
        tab.material_combo,
        materials_db,
        current_settings=state.job_settings,
        apply_settings=state.apply_job_settings,
        dialogs=dialogs,
    )
    tab.material_selected.connect(materials.apply_selected)
    tab.new_material_requested.connect(materials.new_material)
    tab.delete_material_requested.connect(materials.delete_selected)
    tab.export_materials_requested.connect(materials.export_materials)
    tab.import_materials_requested.connect(materials.import_materials)
    # Matériaux et matériau choisi : rangés dans le profil de la machine active et écrits sur
    # disque (voir WindowState.machine_memory), pour les retrouver au prochain démarrage. Connecté après
    # le contrôleur : enregistré une fois la liste à jour.
    for signal in (tab.material_selected, tab.new_material_requested,
                   tab.delete_material_requested, tab.import_materials_requested):
        signal.connect(machines.schedule_persist)
    # Chaque changement de calque est aussitôt recopié dans le matériau choisi (plus de bouton
    # « Enregistrer »), PUIS les calques et les matériaux sont rangés dans le profil de la
    # machine active.
    layers.changed.connect(state.store_layers_in_material)
    layers.changed.connect(machines.schedule_persist)
    return tab, materials
