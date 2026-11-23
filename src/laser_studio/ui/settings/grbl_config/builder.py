"""Page « Configuration GRBL », reliée au graveur, au job et aux profils machine.

    page = build_grbl_config_page(grbl, job, engraver, machines)
"""
from laser_studio.ui.settings.grbl_config.page import GrblConfigPage


def build_grbl_config_page(grbl, job, engraver, machines):
    """Page liée à `grbl` (GrblConfig) ; motif aller/retour par `job`, réglages $$ par `engraver`,
    mémorisation dans le profil actif par `machines` (MachineProfilesController)."""
    page = GrblConfigPage()
    page.bidir_test_requested.connect(job.generate_bidir_test)
    # Décalage aller/retour : mémorisé dans le profil de la machine.
    page.scan_offset_changed.connect(machines.schedule_persist)
    # « Inclure $H » : mémorisé aussi (décoché d'office pour un graveur
    # sans homing, il le reste aux démarrages suivants).
    page.homing_changed.connect(machines.schedule_persist)
    page.read_settings_requested.connect(engraver.read_settings)
    page.send_settings_requested.connect(engraver.send_settings)
    page.export_settings_requested.connect(engraver.export_settings)
    page.import_settings_requested.connect(engraver.import_settings)
    page.link_settings_to_profile_requested.connect(machines.update_profile)
    page.bind_settings(grbl)
    return page
