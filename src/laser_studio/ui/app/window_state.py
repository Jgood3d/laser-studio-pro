"""État de la fenêtre qui s'enregistre et se restaure : réglages machine au
démarrage et à la fermeture, champs d'un profil machine, état d'un projet,
et recopie automatique des calques dans le matériau choisi.

    state = WindowState(window)
    project = ProjectController(window, capture=state.capture_project,
                                restore=state.restore_project, ...)
    state.load_machine_settings()

WindowState lit et réapplique les champs de la fenêtre ; ses méthodes sont
passées en fonctions aux contrôleurs qui décident quand enregistrer
(MachineProfilesController, ProjectController, MaterialsController).
"""
from contextlib import contextmanager

from PyQt6.QtCore import QObject

from laser_studio.controllers.layer_memory import apply_saved_layers
from laser_studio.controllers.materials import (DEFAULT_MATERIALS_DB, apply_material_to_layers,
                                                capture_material_layers)
from laser_studio.core.preferences import machine_preferences


class WindowState(QObject):
    """État enregistrable de la fenêtre `window`, qui en est le point
    d'assemblage : les modèles, contrôleurs et champs y sont lus à chaque
    usage (certains sont construits après WindowState)."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        # > 0 : les changements de calques ne sont pas recopiés dans le matériau choisi (profil
        # machine, projet ou matériau en cours d'application, voir store_layers_in_material).
        self._material_autosave_pause = 0

    # -- Matériau choisi : réglages en cours, recopie automatique des calques

    def job_settings(self):
        """Réglages en cours, au format d'un matériau (voir MaterialsController) : ceux de chaque
        calque, et les anciennes valeurs de gravure image et de découpe SVG."""
        w = self.window
        return {
            "sp_e": w.job.engrave_speed,
            "pw_e": w.job.engrave_power,
            "sp_c": w.job.cut_speed,
            "pw_c": w.job.cut_power,
            "pass_c": w.job.cut_passes,
            "layers": capture_material_layers(w.layer_manager),
        }

    def apply_job_settings(self, material, layers=True):
        """Applique un matériau : découpe de l'ancien mode SVG, puis (layers=True) les réglages
        des calques. La gravure image n'a plus de réglage à part : elle suit le calque de gravure
        (un ancien matériau sp_e / pw_e est repris dans ce calque, voir complete_material).
        layers=False : profil machine qui vient de restaurer ses propres calques, à ne pas
        écraser. Le tableau, le canevas et le profil suivent le modèle des calques."""
        w = self.window
        w.job.set_cut_settings(material["sp_c"], material["pw_c"], material["pass_c"])
        if layers:
            with self.material_autosave_paused():
                apply_material_to_layers(w.layer_manager, material)

    @contextmanager
    def material_autosave_paused(self):
        """Pendant le bloc, les changements de calques ne sont pas recopiés dans le matériau
        choisi : ils viennent d'un profil machine, d'un projet ou du matériau lui-même."""
        self._material_autosave_pause += 1
        try:
            yield
        finally:
            self._material_autosave_pause -= 1

    def store_layers_in_material(self):
        """Un calque a changé : le matériau choisi reprend les réglages en cours (une fois le
        démarrage terminé, et hors chargement d'un profil, d'un projet ou d'un matériau)."""
        w = self.window
        if self._material_autosave_pause or not w.machines.persist_ready:
            return
        w.materials.store_current_settings()

    # -- Réglages machine : démarrage et fermeture

    def save_machine_settings(self):
        """Mémorise les réglages machine (profils, dimensions, résolution de
        l'image) pour les retrouver au prochain lancement, sans recharger de
        projet. Les calques sont rangés dans le profil de la machine active."""
        w = self.window
        prefs = machine_preferences()
        for key, value in w.machine.to_preferences().items():
            prefs.set(key, value)
        w.machines.store_memory()
        prefs.set("machine_profiles_json", w.machines.to_json())
        name = w.machines.current_name()
        if name is not None:
            prefs.set("last_machine_profile", name)
        # Mode de saisie et DPI : état de la boîte de résolution ; lignes/mm : le placement du job.
        mode, dpi, _lmm = w.resolution_box.saved_state()
        prefs.set("lmm_mode_index", mode)
        prefs.set("lmm_dpi_value", dpi)
        prefs.set("lmm_value", w.placement.lines_mm)

    def load_machine_settings(self):
        """Restaure au démarrage les réglages mémorisés par
        save_machine_settings."""
        w = self.window
        prefs = machine_preferences()
        w.machine.load_preferences(prefs.get)
        # Comme à chaque validation de profil : les calques suivent la focale
        # dès le démarrage.
        w.layers_tab.link_all_to_focal()

        w.machines.load(
            prefs.get("machine_profiles_json", ""),
            prefs.get("last_machine_profile"),
            {"name": "Machine par défaut", "w": w.machine.bed_w,
             "h": w.machine.bed_h},
        )

        # Résolution mémorisée, puis recalcul dans tous les cas de l'écart lignes/mm et de la
        # pastille de qualité à partir de l'état chargé, quel que soit le mode.
        w.resolution_box.set_focal(w.machine.focal)
        w.resolution_box.restore_state(prefs.get("lmm_mode_index"), prefs.get("lmm_dpi_value"), prefs.get("lmm_value"))
        # À partir d'ici seulement, un changement de calque est mémorisé.
        w.machines.persist_ready = True

    # -- Profils machine : champs de la fenêtre (voir ProfileFields)

    def capture_machine_profile(self):
        """Champs d'un profil machine : pages Paramètres du graveur et
        Configuration GRBL, position du job, matériaux (une copie, pour que
        modifier ceux d'un profil n'affecte pas les autres) et calques."""
        w = self.window
        return {
            **w.machine.to_profile(),
            **w.placement.to_profile(),
            **w.grbl.profile_values(),
            "materials_db": dict(w.materials.materials),
            "material": w.materials.model.current or "",
            "layers": w.layer_manager.to_list(),
        }

    def apply_machine_profile(self, profile):
        """Réapplique les champs d'un profil (les calques à part)."""
        w = self.window
        with self.material_autosave_paused():
            w.machine.apply_profile(profile)
            w.placement.apply_profile(profile)
            w.grbl.apply_profile(profile)
            # Matériaux propres à cette machine (repli sur la base par défaut pour un profil
            # enregistré avant cette liaison), et matériau choisi à sa dernière utilisation
            # (sélectionné sans être appliqué).
            w.materials.model.set_materials(
                dict(profile.get("materials_db", DEFAULT_MATERIALS_DB)),
                current=profile.get("material"))
            # Calques : ceux mémorisés dans le profil, déjà appliqués ; le matériau ne les écrase pas.
            material = w.materials.model.current_material()
            if material is not None:
                self.apply_job_settings(material, layers=False)

    def machine_memory(self):
        """Mémorisé en continu dans le profil actif : calques, matériaux (avec les réglages de leurs
        calques) et matériau choisi, réglages mécaniques (décalage des lignes retour, surbalayage,
        homing)."""
        w = self.window
        return {"layers": w.layer_manager.to_list(),
                "materials_db": dict(w.materials.materials),
                "material": w.materials.model.current or "",
                **w.grbl.mechanical_values()}

    def apply_profile_layers(self, saved_layers, full=False):
        """Réapplique les calques mémorisés (voir apply_saved_layers), puis
        met l'onglet Calques à jour."""
        w = self.window
        with self.material_autosave_paused():
            if not apply_saved_layers(w.layer_manager, saved_layers, full):
                return
            # Les calques liés à la focale suivent la focale de CETTE machine.
            w.layers_tab.link_all_to_focal()

    def after_machine_profile_selected(self):
        """Après un changement de profil : lignes/mm et DPI suivent la focale
        (même si elle n'a pas changé, ou si le profil n'en a pas), et la
        qualité des calques est recalculée."""
        w = self.window
        w.resolution_box.set_focal(w.machine.focal)
        w.resolution_box.apply_focal()
        with self.material_autosave_paused():
            w.layers_tab.refresh_focal_quality()

    # -- Projet : état de la fenêtre

    def capture_project(self):
        """État du projet (pour ProjectController) : réglages de l'image,
        machine, gravure et découpe, matériaux, calques, objets vectoriels ;
        et l'image source (PIL), encodée par le contrôleur."""
        w = self.window
        # Chaque modèle donne sa partie (to_project).
        data = {key: value for model in self._project_models() for key, value in model.to_project().items()}
        data.update({
            "materials_db": w.materials.materials,
            "raw_image_b64": None,  # rempli par ProjectController
            "layers": w.layer_manager.to_list(),
            "vector_objects": w.vector_canvas.serialize_objects(),
        })
        return data, w.image.raw_image

    def _project_models(self):
        """Modèles enregistrés dans un projet, chacun par to_project / load_project."""
        w = self.window
        return (w.placement, w.machine, w.image_settings, w.grbl, w.job)

    def restore_project(self, data, image):
        """Réapplique un projet ouvert (voir _restore_project_state), sans recopier ses calques
        dans le matériau choisi."""
        with self.material_autosave_paused():
            self._restore_project_state(data, image)

    def _restore_project_state(self, data, image):
        """Réapplique un projet ouvert (voir capture_project). Les clés
        absentes (anciens projets) prennent leur valeur par défaut."""
        w = self.window
        # Le projet impose ses propres réglages matière / négatif / miroir :
        # l'état mémorisé par l'onglet Séparation est oublié, sinon un
        # chargement d'image ultérieur le « rendrait » par-dessus.
        w.separation.forget_glass_settings()

        # Chaque modèle relit sa partie (load_project) ; une clé absente (ancien projet) prend sa valeur
        # par défaut. Les calques sont rechargés plus bas : ils font foi sur la gravure d'image.
        for model in self._project_models():
            model.load_project(data)

        if "materials_db" in data:
            w.materials.set_materials(data["materials_db"])

        if image is not None:
            w.image.restore_image(image)

        if "layers" in data:
            w.layer_manager.load_list(data["layers"])
        w.vector_canvas.load_objects(data.get("vector_objects"))

        w.image.schedule_processing()
