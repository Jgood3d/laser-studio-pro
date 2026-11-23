"""Image à graver de l'onglet « Graver une image » : chargement, rotation,
retrait, taille, traitement (tramage) dans un thread, comparaison des
algorithmes. Sans widget : l'onglet (ImageTab) émet des signaux, le
contrôleur agit et prévient par les siens.

    image = ImageController(image_settings, machine, dialogs,
                            size_mm=panel.size_mm, set_size=panel.set_size,
                            keep_ratio=panel.keep_ratio_check.isChecked,
                            lines_mm=resolution_box.lines_per_mm)
    image.source_changed.connect(tab.show_source)
    image.processed.connect(tab.show_processed)
    image.load_path("photo.jpg")

Le calcul du tramage est dans image.dithering (sans Qt), lancé dans un
thread par workers.ImageProcessingWorker.
"""
import os

from PIL import Image
from PyQt6.QtCore import QObject, QSettings, QTimer, pyqtSignal

from laser_studio.i18n import tr
from laser_studio.image.dithering import ALGORITHMS, comparison_thumbnails
from laser_studio.image.size import natural_size_mm, read_dpi
from laser_studio.workers import ImageProcessingWorker

# Clé de UIConfig : dernier algorithme de tramage choisi par l'utilisateur.
ALGORITHM_SETTING = "image_algorithm"
# Délai (ms) avant le traitement : plusieurs changements rapprochés, un seul traitement.
PROCESSING_DELAY_MS = 150


def open_grayscale_image(path):
    """(image en niveaux de gris, DPI enregistrés ou None) de `path`. Les PNG avec
    transparence (RGBA, LA, ou palette avec canal alpha) sont aplatis sur un fond
    blanc avant la conversion : sinon PIL garde les valeurs RGB brutes des pixels
    transparents (souvent noires), qui se retrouveraient gravées comme si elles
    étaient opaques. Lève une exception si le fichier est illisible."""
    img = Image.open(path)
    file_dpi = read_dpi(img.info)          # lu avant les conversions, qui perdent les métadonnées
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img)
    return img.convert("L"), file_dpi


class ImageController(QObject):
    """Image source (`raw_image`, PIL en niveaux de gris) et résultat du
    tramage (`processed_array`, uint8 : 0 = brûlé), lu par la génération du
    job et par la Séparation.

    `image_settings` : ImageSettings (réglages du tramage) ; tout changement
    relance le traitement. `machine` : MachineConfig (taille du plateau).
    `dialogs` : UserDialogs.

    État de l'interface, lu ou écrit à chaque usage :
    - size_mm() / set_size(l, h) : taille de l'image (mm) ;
    - keep_ratio() : proportions conservées quand on change une dimension ;
    - lines_mm() : résolution de gravure (lignes/mm).

    Signaux :
    - source_changed(image ou None) : image chargée, pivotée, reçue de la
      Séparation ou d'un projet, ou retirée ;
    - processed(tableau, image PIL) : nouveau rendu tramé ;
    - status(texte, infobulle) : message pour la barre d'état ;
    - loading_file() : un fichier va être chargé (la Séparation rend les
      réglages du verre) ;
    - resetting() : réglages remis à zéro (la Séparation n'a plus rien à rendre).
    """

    source_changed = pyqtSignal(object)
    processed = pyqtSignal(object, object)
    status = pyqtSignal(str, str)
    loading_file = pyqtSignal()
    resetting = pyqtSignal()

    def __init__(self, image_settings, machine, dialogs, *, size_mm, set_size, keep_ratio, lines_mm,
                 parent=None):
        super().__init__(parent)
        self.image_settings = image_settings
        self.machine = machine
        self.dialogs = dialogs
        self._size_mm = size_mm
        self._set_size = set_size
        self._keep_ratio = keep_ratio
        self._lines_mm = lines_mm
        self.raw_image = None
        self.processed_array = None
        self.worker = None
        self.pending_reprocess = False
        # Vrai pendant que le contrôleur pose lui-même la taille : la règle des
        # proportions (dimension_changed) ne doit pas la corriger.
        self._applying_size = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(PROCESSING_DELAY_MS)
        self.timer.timeout.connect(self._process)
        image_settings.changed.connect(self.schedule_processing)

    # -- état

    def has_image(self):
        return self.raw_image is not None

    def is_busy(self):
        """Vrai tant qu'un traitement est prévu ou en cours (processed_array pas à jour)."""
        return bool(self.timer.isActive() or (self.worker and self.worker.isRunning()))

    def _apply_size(self, w_mm, h_mm):
        self._applying_size = True
        try:
            self._set_size(w_mm, h_mm)
        finally:
            self._applying_size = False

    def _set_source(self, image, size_mm=None):
        """Nouvelle image (ou None), puis sa taille si `size_mm` est donnée :
        l'image est déjà en place quand les champs de taille changent."""
        self.raw_image = image
        if size_mm is not None:
            self._apply_size(*size_mm)
        self.source_changed.emit(image)

    # -- image source

    def open_image(self):
        """Demande une image et la charge (load_path)."""
        path = self.dialogs.open_file(tr("image.open_title"), tr("image.file_filter"))
        if path:
            self.load_path(path)

    def load_path(self, path):
        """Charge `path` à sa taille d'origine (d'après sa résolution enregistrée,
        96 DPI à défaut), réduite si besoin pour tenir sur le plateau, et le dit
        dans la barre d'état. Message d'erreur si le fichier est illisible.
        Renvoie True si l'image est chargée."""
        # Image classique : les réglages miroir / négatif / matière posés par un
        # import de l'onglet Séparation sont rendus.
        self.loading_file.emit()
        try:
            image, file_dpi = open_grayscale_image(path)
        except Exception as e:
            self.dialogs.error(tr("image.error_title"), tr("image.load_error").format(error=e))
            return False
        w, h = image.size
        w_mm, h_mm, used_dpi, shrunk = natural_size_mm(w, h, file_dpi, self.machine.bed_w, self.machine.bed_h)
        self._set_source(image, (w_mm, h_mm))
        self.schedule_processing()
        if shrunk:
            full_w, full_h, _, _ = natural_size_mm(w, h, file_dpi)
            size_msg = tr("image.natural_size_fit").format(w=w_mm, h=h_mm, ow=full_w, oh=full_h, dpi=used_dpi)
        else:
            size_msg = tr("image.natural_size").format(w=w_mm, h=h_mm, dpi=used_dpi)
        # Barre d'état : nom du fichier seul ; chemin complet dans l'infobulle.
        self.status.emit(f"{tr('image.loaded').format(path=os.path.basename(path))} — {size_msg}",
                         f"{tr('image.loaded').format(path=path)}\n{size_msg}")
        return True

    def rotate_left(self):
        self._rotate(90)

    def rotate_right(self):
        self._rotate(270)

    def _rotate(self, angle):
        """Pivote l'image de `angle` degrés (positif = antihoraire, comme PIL) ;
        la taille repart de 100 mm de large, aux nouvelles proportions."""
        if not self.raw_image:
            return
        image = self.raw_image.rotate(angle, expand=True)
        w, h = image.size
        self._set_source(image, (100.0, 100.0 * (h / w)))
        self.schedule_processing()

    def clear(self):
        """Retire l'image, après confirmation : l'onglet revient à vide, sans
        toucher aux calques ni aux objets vectoriels."""
        if not self.raw_image and self.processed_array is None:
            return
        if not self.dialogs.confirm_yes_no(tr("image.delete_title"), tr("image.delete_question")):
            return
        self.processed_array = None
        self._set_source(None)
        self.status.emit(tr("image.deleted"), "")

    def set_image(self, image, w_mm, h_mm):
        """Image fournie par un autre onglet (tonalité de la Séparation), à la
        taille donnée."""
        self._set_source(image, (w_mm, h_mm))
        self.schedule_processing()

    def restore_image(self, image):
        """Image d'un projet ouvert : sa taille est restaurée à part, et le
        traitement relancé une fois tout le projet réappliqué."""
        self._set_source(image)

    def dimension_changed(self, axis, value):
        """Largeur (`axis` "w") ou hauteur ("h") saisie : l'autre dimension suit
        les proportions de l'image si elles sont conservées."""
        if self._applying_size or not self._keep_ratio() or not self.raw_image:
            return
        w, h = self.raw_image.size
        aspect = h / w
        if axis == "w":
            self._apply_size(value, value * aspect)
        else:
            self._apply_size(value / aspect, value)
        self.schedule_processing()

    # -- traitement

    def schedule_processing(self, *_args):
        """Retraite l'image peu après le dernier changement (plusieurs
        changements rapprochés : un seul traitement)."""
        self.timer.start(PROCESSING_DELAY_MS)

    def _process(self):
        if not self.raw_image:
            return
        if self.worker and self.worker.isRunning():
            # Un traitement (potentiellement lent : Stucki/Jarvis) est déjà en
            # cours. Au lieu d'ignorer cette demande (ce qui perdait des
            # changements comme le négatif ou l'algorithme choisi), on la
            # mémorise pour la relancer dès que le thread actuel se termine,
            # avec les réglages les plus récents.
            self.pending_reprocess = True
            return
        w_mm, h_mm = self._size_mm()
        params = {'w_mm': w_mm, 'h_mm': h_mm, 'lmm': self._lines_mm(),
                  **self.image_settings.processing_params()}
        self.worker = ImageProcessingWorker(self.raw_image, params)
        self.worker.finished.connect(self._on_processed)
        self.worker.start()

    def _on_processed(self, out_arr, dither_img):
        self.processed_array = out_arr
        self.processed.emit(out_arr, dither_img)
        if self.pending_reprocess:
            # Des réglages ont changé pendant ce traitement : relancé tout de
            # suite avec l'état actuel, sans attendre une nouvelle action.
            self.pending_reprocess = False
            self._process()

    # -- réglages du tramage

    def comparison(self):
        """[(algorithme, tableau tramé)] : une vignette par algorithme avec les
        réglages actuels, ou None (message) s'il n'y a pas d'image."""
        if not self.raw_image:
            self.dialogs.info(tr("image.compare_title"), tr("image.compare_empty"))
            return None
        s = self.image_settings
        return comparison_thumbnails(self.raw_image, s.brightness, s.contrast, s.gamma, s.sharpness, s.invert)

    def choose_algorithm(self, algorithm):
        """Algorithme choisi par l'utilisateur (comparaison) : appliqué et mémorisé."""
        self.image_settings.update(algorithm=algorithm)
        self.remember_algorithm(algorithm)

    def remember_algorithm(self, algorithm):
        """Mémorise l'algorithme de tramage choisi par l'utilisateur (liste « Algorithme » ou
        comparaison des algorithmes) : il est resélectionné au prochain démarrage, donc pour
        les images chargées ensuite. Les changements faits par programme (ouverture d'un projet,
        séparation couleur) ne passent pas par ici."""
        if not algorithm:
            return
        settings = QSettings("LaserStudioPro", "UIConfig")
        settings.setValue(ALGORITHM_SETTING, algorithm)
        settings.sync()  # écriture immédiate sous Windows

    def restore_remembered_algorithm(self):
        """Resélectionne le dernier algorithme choisi, s'il existe encore."""
        algorithm = QSettings("LaserStudioPro", "UIConfig").value(ALGORITHM_SETTING, "")
        if algorithm in ALGORITHMS:
            self.image_settings.update(algorithm=algorithm)

    def reset_settings(self):
        """Réinitialisation explicite des réglages du tramage."""
        self.resetting.emit()
        self.image_settings.reset()

    def material_summary(self):
        """Ex. « Matière : fond noir (négatif activé) » — reflète l'état RÉEL du
        négatif, donc signale une incohérence s'il a été modifié à la main."""
        s = self.image_settings
        bg_key = "gen.material_dark" if s.material_bg == "dark" else "gen.material_light"
        neg_key = "gen.negative_on" if s.invert else "gen.negative_off"
        return tr("gen.material_summary").format(bg=tr(bg_key), negative=tr(neg_key))
