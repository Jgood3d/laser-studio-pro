"""Affichage des résultats du job et de l'état du graveur.

    display = JobDisplay(status_bar, console, preview, machine_panel, actions, dialogs, ...)
    job.generated.connect(display.show_generated)
    display.connect_machine(connection, engraver)

JobController produit le G-Code, MachineConnection et EngraverController
parlent au graveur ; JobDisplay ne fait que montrer ce qu'ils annoncent :
barre de progression et messages, console G-Code, statistiques et aperçu 2D,
état et position du graveur, suivi de l'envoi.
"""
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication

from laser_studio.gcode import MATRIX_ENGRAVE
from laser_studio.i18n import tr
from laser_studio.i18n.durations import duration_text


def set_homing_available(checkboxes, available, tip):
    """Cases « Inclure $H » (Configuration GRBL, matrice de test) : grisées et
    décochées si le graveur n'a pas de homing, infobulle `tip`. Renvoie True si
    une case cochée a été décochée (voir EngraverController)."""
    unchecked = False
    for checkbox in checkboxes:
        if not available and checkbox.isChecked():
            checkbox.setChecked(False)
            unchecked = True
        checkbox.setEnabled(available)
        checkbox.setToolTip(tip)
    return unchecked


def beep_job_done():
    """Signal sonore de fin de job (2 bips espacés), pour être prévenu même
    sans regarder l'écran (gravure longue, utilisateur dans une autre pièce)."""
    QTimer.singleShot(0, QApplication.beep)
    QTimer.singleShot(250, QApplication.beep)


class JobDisplay(QObject):
    """Résultats du job et état du graveur, montrés dans la fenêtre.

    `status_bar` : StatusBar ; `console` : onglet de la console G-Code (ConsoleTab) ;
    `preview` : Preview2DTab ; `machine_panel` : MachinePanel ; `actions` :
    AppActions (« Enregistrer le G-Code ») ; `dialogs` : UserDialogs.

    - layers : LayersModel (couleur de chaque calque dans l'aperçu) ;
    - test_matrix() : paramètres de la dernière matrice de test, ou None ;
    - show_preview() : affiche l'onglet de l'aperçu 2D ;
    - log(texte) : message pour la barre d'état et le journal ;
    - show_machine_panel() : déplie le panneau du bas sur l'onglet « Graveur » (gravure lancée, alarme).
    """

    def __init__(self, status_bar, console, preview, machine_panel, actions, dialogs, *,
                 layers, test_matrix, show_preview, log, show_machine_panel, duration_factor=lambda: None,
                 parent=None):
        super().__init__(parent)
        self.status_bar = status_bar
        self.console = console
        self.preview = preview
        self.machine_panel = machine_panel
        self.actions = actions
        self.dialogs = dialogs
        self.layers = layers
        self._test_matrix = test_matrix
        self._show_preview = show_preview
        self._log = log
        self._show_machine_panel = show_machine_panel
        # (facteur, nombre de gravures) qui recale l'estimation sur les durées réelles, ou None (job_history).
        self._duration_factor = duration_factor
        self._last_state = None                  # état GRBL précédent (alarme qui survient)
        self.connection = None
        # G-Code dessiné dans l'aperçu 2D (généré, importé ou envoyé).
        self.last_gcode_text = None

    # -- génération du G-Code (JobController)

    def generation_started(self):
        """Génération lancée : barre de progression, et l'aperçu 2D est montré
        aussitôt (il se remplit à la fin, voir show_generated)."""
        self.status_bar.show_progress(0, tr("gen.in_progress"))
        self._show_preview()

    def generation_progress(self, pct):
        self.status_bar.show_progress(pct, tr("gen.in_progress_pct").format(pct=pct))

    def generation_failed(self, error_text):
        self.status_bar.hide_progress()
        self._log(f"\n; ERREUR DE GÉNÉRATION :\n; {error_text}")
        self.dialogs.error(tr("gen.failed_title"), tr("gen.failed_body").format(error=error_text))

    def show_generated(self, gcode_str, num_lines, avg_power, seconds):
        """G-Code prêt : console, statistiques, aperçu 2D."""
        self.status_bar.show_progress(100, tr("gen.done"))
        self.status_bar.hide_progress(delay_ms=1500)
        self.console.set_gcode(gcode_str)
        correction = self._duration_factor()
        if correction is None:
            duration = tr("gen.stat_time").format(value=duration_text(seconds))
        else:
            factor, jobs = correction
            duration = tr("gen.stat_time_corrected").format(value=duration_text(seconds * factor), n=jobs)
        self.status_bar.set_duration(duration)
        self.preview.job_stats_panel.set_stats(tr("gen.stat_lines").format(n=num_lines),
                                               tr("gen.stat_power").format(value=f"{avg_power:.1f}"),
                                               duration)
        # « Fichier > Enregistrer le G-Code » : actif une fois le G-Code généré.
        self.actions.set_gcode_export_enabled(True)
        self.plot(gcode_str)
        self._show_preview()

    def show_imported(self, gcode_text, path):
        """Affiche un fichier G-Code importé (JobController.import_gcode) dans
        la console et l'aperçu 2D."""
        self.console.set_gcode(gcode_text)
        num_lines = len([line for line in gcode_text.split('\n') if line.strip()])
        self.preview.job_stats_panel.set_stats(tr("gen.stat_lines").format(n=num_lines),
                                               tr("gen.stat_power_imported"),
                                               tr("gen.stat_time_imported"))
        self.status_bar.set_duration(None)
        self.plot(gcode_text)
        # « Fichier > Enregistrer le G-Code » : le G-Code importé peut être réenregistré.
        self.actions.set_gcode_export_enabled(True)
        self._show_preview()
        self._log(tr("gcode.imported_from").format(path=path))

    def plot(self, gcode_text):
        """Dessine `gcode_text` dans l'aperçu 2D (Preview2DTab.show_gcode)."""
        self.last_gcode_text = gcode_text
        matrix = self._test_matrix() or {}
        try:
            self.preview.show_gcode(gcode_text, self.layers.colors_by_name(),
                                    matrix_engrave=matrix.get("mode") == MATRIX_ENGRAVE)
        except Exception as e:
            # Ne jamais laisser l'aperçu 2D silencieusement vide : si le G-Code
            # (notamment un fichier importé d'un autre outil) contient une
            # ligne inattendue qui fait planter l'analyse, on le signale.
            self._log(f"\n; ERREUR aperçu 2D : {e}")
            self.dialogs.warning(tr("gen.preview_error_title"), tr("gen.preview_error_body").format(error=e))

    def redraw(self, *_args):
        """Options d'affichage de l'aperçu 2D changées : aperçu redessiné."""
        if self.last_gcode_text:
            self.plot(self.last_gcode_text)

    # -- graveur (MachineConnection, EngraverController)

    def connect_machine(self, connection, engraver):
        """Abonne l'affichage aux signaux de la connexion au graveur et de son
        contrôleur."""
        self.connection = connection
        panel = self.machine_panel
        c = connection
        c.connection_changed.connect(lambda _connected: self.update_machine_state())
        c.state_changed.connect(lambda _state: self.update_machine_state())
        c.status_updated.connect(self.status_updated)
        c.log.connect(self._log)
        c.position_lost.connect(lambda: self._log(tr("laser.position_lost_log")))
        c.stream_progress.connect(
            lambda current, total: panel.progress_bar.setValue(int((current / total) * 100) if total else 0))
        c.stream_lines_sent.connect(panel.sent_gcode_log.append_lines)
        c.stream_lines_acked.connect(lambda acked: self.preview.set_lines_acked(acked))
        c.reconnecting.connect(lambda: self._log(tr("laser.reconnecting")))
        e = engraver
        e.log.connect(self._log)
        e.ports_changed.connect(panel.connection_panel.set_ports)
        e.disconnected.connect(lambda: self.show_machine_state(None, None, None, None))
        e.direct_job_started.connect(self._direct_job_started)
        e.stream_starting.connect(self._stream_starting)
        e.stream_ended.connect(self._stream_ended)
        e.gcode_restored.connect(self.console.set_gcode)
        e.job_done.connect(beep_job_done)
        self.update_machine_state()

    def update_machine_state(self):
        """Bouton de connexion, pilotage, actions de job, macros et console directe actifs d'après l'état
        du graveur (MachinePanel.set_machine_state, table de models/machine_state.py) : tout grisé
        déconnecté, seules les commandes temps réel pendant un job ou un homing. La position du job reste
        modifiable : elle sert aussi à générer le G-Code hors connexion."""
        self.machine_panel.set_machine_state(self.connection.is_connected(), self.connection.can)

    def status_updated(self, state, x, y, z):
        """État et position du graveur (sondage hors job, thread d'envoi
        pendant un job) : affichage, position de la tête sur l'aperçu 2D,
        traits déjà gravés en rouge pendant un job."""
        self.show_machine_state(state, x, y, z)
        self.preview.set_head_position(x, y)
        if self.connection.is_streaming():
            self.preview.update_burn(x, y)

    def show_machine_state(self, state, x, y, z):
        """État (cadre Connexion) et position (sous le pilotage) dans le
        panneau machine (MachinePanel.set_status)."""
        self.machine_panel.set_status(state, x, y, z)
        # Alarme qui survient : le panneau du graveur se déplie, avec son bouton « Déverrouiller ».
        if state == "Alarm" and self._last_state != "Alarm":
            self._show_machine_panel()
        self._last_state = state
        self.status_bar.set_machine(state, x, y)
        # Déconnecté : plus de position connue, le point de la tête disparaît de l'aperçu 2D.
        if state is None:
            self.preview.clear_head_position()

    def _direct_job_started(self):
        """« Envoyer au laser » : « Répéter » disponible (une fois le job fini, voir update_machine_state),
        suivi du G-Code envoyé remis à zéro."""
        panel = self.machine_panel
        panel.job_actions_panel.set_repeat_enabled(True)
        panel.sent_gcode_log.clear_lines()
        panel.sent_gcode_log.append_lines([tr("queue.sent_log_direct")])

    def _stream_starting(self, gcode_text):
        """Un envoi commence : barre de progression affichée, à zéro ; l'aperçu 2D doit
        montrer le G-Code envoyé (un job de la file n'est pas forcément celui
        affiché) et le tracé « déjà gravé » repart de zéro."""
        self.machine_panel.progress_bar.setValue(0)
        self.machine_panel.progress_bar.setVisible(True)
        self._show_machine_panel()           # gravure lancée : le panneau du graveur se déplie
        if gcode_text != self.last_gcode_text:
            self.plot(gcode_text)
        else:
            self.preview.reset_burn()

    def _stream_ended(self, clean_finish):
        """Un envoi se termine : repère de fin dans le suivi, aperçu 2D ; la barre de progression disparaît."""
        self.machine_panel.progress_bar.setVisible(False)
        self.machine_panel.sent_gcode_log.mark_end(clean_finish)
        self.preview.finish_burn(clean_finish)
