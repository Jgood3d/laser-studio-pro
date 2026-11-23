"""Séparation couleur / verre : image source, tonalité envoyée à « Graver une
image », aperçus (original, gravure, impression, simulation) et export. Sans
boîte de dialogue : la fenêtre s'abonne aux signaux et affiche.

Principe : l'image couleur est chargée ici ; sa tonalité (canal V, cadrée
sur la plaque, gain de point compensé) est envoyée à « Graver une image »
(signal tone_ready), qui applique luminosité / contraste / gamma / tramage /
résolution et produit le calque noir (processed_array, 0 = gravé). Le calque
couleur est calculé ici à la MÊME taille physique ; le DPI de gravure est
celui de « Graver une image » (lignes/mm × 25,4).

    separation = SeparationController(settings, image_settings,
                                      frame_args=tab.frame_args,
                                      engrave_lmm=lambda: spin_lmm.value(),
                                      dialogs=window.dialogs, engraved=lambda: window.processed_array,
                                      current_preview=tab.preview_tabs.currentIndex,
                                      is_visible=tab.isVisible)
    separation.tone_ready.connect(window.on_separation_tone)
    separation.preview_ready.connect(tab.show_preview)
    separation.load_path("vitrail.jpg")
"""
import os
import time
from contextlib import nullcontext

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from laser_studio.i18n import tr
from laser_studio.image import separation as engine
from laser_studio.image.dithering import HAS_NUMBA
from laser_studio.image.resolution import lmm_to_dpi

# Aperçus, dans l'ordre des onglets de SeparationTab.
PREVIEW_ORIGINAL, PREVIEW_ENGRAVE, PREVIEW_PRINT, PREVIEW_SIMULATION = range(4)
PREVIEWS = (PREVIEW_ORIGINAL, PREVIEW_ENGRAVE, PREVIEW_PRINT, PREVIEW_SIMULATION)
# Taille maxi (px) des aperçus : au-delà, inutile et lent.
PREVIEW_MAX = 1200
# Image source réduite pour les aperçus.
SOURCE_PREVIEW_MAX = 2500
# Réglages du verre peint (gravure côté peinture, vue à travers le verre) :
# on retire la peinture sur les zones claires (fond noir => négatif) et on
# grave en miroir.
GLASS_IMAGE_SETTINGS = {"material_bg": "dark", "invert": True, "mirror_h": True}


def open_color_image(path):
    """Image couleur (RGB), orientée d'après l'EXIF ; la transparence est
    aplatie sur du blanc. Lève une exception si le fichier est illisible."""
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        background = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(background, im)
    return im.convert("RGB")


class SeparationController(QObject):
    """État et logique de l'onglet Séparation.

    `settings` : SeparationSettings (plaque, gain, couleur, simulation).
    `image_settings` : ImageSettings de « Graver une image » (réglages du
    verre appliqués au chargement, miroirs et algorithme lus).
    `frame_args()` : cadrage de l'onglet (SeparationTab.frame_args).
    `engrave_lmm()` : résolution de gravure de « Graver une image ».
    `dialogs` : UserDialogs (choix du fichier et du dossier, messages).

    État de l'interface, lu à chaque usage :
    - engraved() : calque noir produit par « Graver une image » (tableau
      numpy, 0 = gravé) ou None ;
    - image_busy() : vrai pendant un traitement de « Graver une image » (le
      calque noir n'est pas encore à jour) ;
    - current_preview() : aperçu affiché (voir PREVIEWS) ;
    - is_visible() : l'onglet est affiché (sinon les aperçus attendent) ;
    - busy() : gestionnaire de contexte pendant l'export (curseur d'attente).

    Signaux :
    - tone_ready(image L, largeur_mm, hauteur_mm) : tonalité à graver ;
    - source_changed(proportions ou None, nom du fichier) : image chargée,
      pivotée ou retirée ;
    - image_loaded() : nouvelle image (la plaque prend ses proportions) ;
    - image_rotated() : image pivotée (largeur et hauteur de la plaque échangées) ;
    - previews_invalidated() : les aperçus sont à recalculer (réglage de
      couleur ou de simulation changé) ;
    - preview_ready(index, image PIL) : aperçu à afficher ;
    - engrave_dpi_changed(dpi) : résolution de gravure de « Graver une image ».
    """

    tone_ready = pyqtSignal(object, float, float)
    source_changed = pyqtSignal(object, str)
    image_loaded = pyqtSignal()
    image_rotated = pyqtSignal()
    previews_invalidated = pyqtSignal()
    preview_ready = pyqtSignal(int, object)
    engrave_dpi_changed = pyqtSignal(int)

    # Diagnostic de lenteur (durées dans la console) : à passer à False une
    # fois terminé.
    DEBUG_TIMING = True

    def __init__(self, settings, image_settings, frame_args, engrave_lmm, *, dialogs,
                 engraved=lambda: None, image_busy=lambda: False, current_preview=lambda: PREVIEW_SIMULATION,
                 is_visible=lambda: True, busy=nullcontext, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.image_settings = image_settings
        self.dialogs = dialogs
        self._frame_args = frame_args
        self._engrave_lmm = engrave_lmm
        self._engraved = engraved
        self._image_busy = image_busy
        self._current_preview = current_preview
        self._is_visible = is_visible
        self._busy = busy
        self._dirty = False          # aperçu à recalculer quand l'onglet sera affiché
        self.source = None           # image couleur complète (RGB)
        self.source_small = None     # réduite, pour les aperçus
        self.path = ""
        self._version = 0            # change à chaque nouvelle image (invalide le cache)
        self._color_cache = None
        self._stale = set()          # aperçus à recalculer
        # Réglages de « Graver une image » d'avant l'application des réglages
        # du verre (rendus quand une image est chargée là-bas).
        self._image_settings_before = None
        self._t0 = None
        self.timing = {}
        image_settings.changed.connect(
            lambda changes: "algorithm" in changes and self._mark_t0())

        self._push_timer = self._timer(300, self.push_tone)
        self._preview_timer = self._timer(250, self.previews_invalidated.emit)

    @staticmethod
    def _timer(interval_ms, slot):
        timer = QTimer()
        timer.setSingleShot(True)
        timer.setInterval(interval_ms)
        timer.timeout.connect(slot)
        return timer

    # -- image source

    def has_image(self):
        return self.source is not None

    def _set_source(self, image):
        self.source = image
        small = image.copy()
        small.thumbnail((SOURCE_PREVIEW_MAX, SOURCE_PREVIEW_MAX))
        self.source_small = small
        self._version += 1

    def load(self, path):
        """Charge l'image couleur `path` et applique les réglages du verre à
        « Graver une image ». Lève une exception si le fichier est illisible
        (rien n'est alors changé). La tonalité est envoyée par l'appelant
        (push_tone), une fois la plaque ajustée aux proportions."""
        image = open_color_image(path)
        self._set_source(image)
        self.path = path
        self.apply_glass_settings()
        self.source_changed.emit(image.width / image.height, os.path.basename(path))

    def rotate(self, angle):
        """Pivote l'image de `angle` degrés (positif = antihoraire, comme PIL).
        Faux s'il n'y a pas d'image."""
        if self.source is None:
            return False
        self._set_source(self.source.rotate(angle, expand=True))
        self.source_changed.emit(self.source.width / self.source.height, os.path.basename(self.path))
        return True

    def open_image(self):
        """Demande une image couleur et la charge (load_path)."""
        path = self.dialogs.open_file(tr("image.open_title"), tr("image.file_filter"))
        if path:
            self.load_path(path)

    def load_path(self, path):
        """Charge `path` (message si le fichier est illisible), ajuste la
        plaque à ses proportions (image_loaded) et envoie la tonalité.
        Renvoie True si l'image est chargée."""
        try:
            self.load(path)
        except Exception as e:
            self.dialogs.error(tr("image.error_title"), tr("image.load_error").format(error=e))
            return False
        self.image_loaded.emit()
        self.push_tone()
        return True

    def rotate_image(self, angle):
        """Pivote l'image de `angle` degrés (positif = antihoraire, comme PIL),
        échange la largeur et la hauteur de la plaque (image_rotated) et
        renvoie la tonalité."""
        if self.rotate(angle):
            self.image_rotated.emit()
            self.push_tone()

    def clear(self):
        """Retire l'image source. L'image déjà envoyée à « Graver une image »
        y reste (elle se supprime depuis cet onglet)."""
        self._push_timer.stop()
        self._preview_timer.stop()
        self.source = None
        self.source_small = None
        self.path = ""
        self._version += 1
        self._color_cache = None
        self._stale = set()
        self._dirty = False
        self.source_changed.emit(None, "")

    # -- réglages partagés avec « Graver une image »

    def apply_glass_settings(self):
        """Matière fond noir, négatif et miroir horizontal dans « Graver une
        image ». L'état d'avant est mémorisé (une seule fois) pour être rendu
        par release_glass_settings."""
        if self._image_settings_before is None:
            self._image_settings_before = {
                name: self.image_settings.get(name) for name in GLASS_IMAGE_SETTINGS}
        self.image_settings.update(**GLASS_IMAGE_SETTINGS)

    def release_glass_settings(self):
        """Une image est chargée dans « Graver une image » : rend les réglages
        (matière, négatif, miroir) d'avant le passage par la Séparation."""
        before, self._image_settings_before = self._image_settings_before, None
        if before:
            self.image_settings.update(**before)

    def forget_glass_settings(self):
        """Réinitialisation ou projet ouvert : plus rien à rendre."""
        self._image_settings_before = None

    # -- tonalité envoyée à « Graver une image »

    def schedule_push(self, *_args):
        """Plaque, cadrage ou gain changé : tonalité renvoyée peu après."""
        if self.source is not None:
            self._push_timer.start()

    def schedule_previews(self, *_args):
        """Réglage de couleur ou de simulation changé : aperçus recalculés peu après."""
        self._preview_timer.start()

    def engrave_dpi(self):
        return round(lmm_to_dpi(self._engrave_lmm()))

    def resolution_changed(self):
        """La résolution de gravure de « Graver une image » a changé : elle est
        réaffichée, et la tonalité renvoyée si une image est chargée (sa
        densité de pixels en dépend)."""
        self.engrave_dpi_changed.emit(self.engrave_dpi())
        self.schedule_push()

    def push_tone(self):
        """Envoie la tonalité (canal V, cadrée sur la plaque, gain de point
        compensé) : signal tone_ready."""
        if self.source is None:
            return
        w_mm, h_mm = self.settings.plate_w, self.settings.plate_h
        longest = max(w_mm, h_mm)
        # px/mm : au moins la résolution de gravure, ~2000 px minimum, 6000 px maximum
        scale = min(max(self._engrave_lmm(), 2000.0 / longest), 6000.0 / longest)
        framed = engine.cadrer(self.source, round(w_mm * scale), round(h_mm * scale),
                               *self._frame_args())
        tone = engine.tonalite_v(np.asarray(framed))
        tone = engine.compenser_gain_point(tone, self.settings.gain / 100.0)
        self.tone_ready.emit(Image.fromarray((tone * 255 + 0.5).astype(np.uint8)), w_mm, h_mm)

    # -- aperçus

    def engraved_changed(self):
        """« Graver une image » vient de recalculer le calque noir : résolution
        réaffichée, aperçus recalculés, durées dans la console (diagnostic)."""
        t_hook = time.perf_counter()
        self.engrave_dpi_changed.emit(self.engrave_dpi())
        self.timing = {}
        if self.has_image():
            self.refresh_previews()
        report = self.timing_report(self._engraved(), t_hook, time.perf_counter())
        if report:
            print(report)

    def refresh_previews(self, *_args):
        """Invalide les aperçus ; seul l'aperçu affiché est recalculé tout de
        suite, les autres le seront quand on les ouvrira."""
        if self.source_small is None or self._engraved() is None:
            return
        self.invalidate_previews()
        self.render_current()

    def render_current(self, *_args):
        """Recalcule l'aperçu affiché s'il est à refaire (preview_ready). Onglet
        masqué : attend qu'il soit affiché (refresh_if_dirty)."""
        engraved = self._engraved()
        if self.source_small is None or engraved is None:
            return
        if not self._is_visible():
            self._dirty = True
            return
        self._dirty = False
        index = self._current_preview()
        if not self.needs_render(index):
            return
        image = self.render_preview(index, engraved)
        if image is not None:
            t_c = time.perf_counter()
            self.preview_ready.emit(index, image)
            self.timing["affichage"] = (time.perf_counter() - t_c) * 1000

    def refresh_if_dirty(self):
        """L'onglet vient d'être affiché : aperçu recalculé s'il a été invalidé
        pendant qu'il était masqué."""
        if self._dirty:
            self.render_current()

    def invalidate_previews(self):
        """Le calque noir a changé : tous les aperçus sont à recalculer."""
        self._stale = set(PREVIEWS)

    def needs_render(self, index):
        return index in self._stale

    def render_preview(self, index, engraved):
        """Image de l'aperçu `index` (voir PREVIEWS) d'après le calque noir
        `engraved` (0 = gravé), ou None s'il n'y a rien à montrer. L'aperçu
        n'est plus « à recalculer » ensuite."""
        if self.source_small is None or engraved is None:
            return None
        self._stale.discard(index)
        h, w = engraved.shape
        f = min(1.0, PREVIEW_MAX / max(w, h))
        pw, ph = max(1, round(w * f)), max(1, round(h * f))

        if index == PREVIEW_ENGRAVE:  # fichier gravure : tel que reçu par le laser
            image = Image.fromarray(engraved)
            return image if f == 1.0 else image.resize((pw, ph), Image.NEAREST)
        if index == PREVIEW_ORIGINAL:
            return self._original_with_crop()

        t_a = time.perf_counter()
        color = self._color_data(pw, ph)
        self.timing["couleur"] = (time.perf_counter() - t_a) * 1000
        if index == PREVIEW_PRINT:
            image = engine.array_vers_image(color["couleur"])
            return ImageOps.mirror(image) if self.settings.mirror_print else image
        return self._simulation(engraved, color, pw, ph)

    def _simulation(self, engraved, color, pw, ph):
        """Rétro-éclairage : fraction de verre dégagé (0 = gravé = la lumière
        passe), dans le sens de lecture."""
        t_b = time.perf_counter()
        grav = Image.fromarray(engraved).resize((pw, ph), Image.BOX)
        lum = (255.0 - np.asarray(grav, dtype=np.float32)) / 255.0
        if self.image_settings.mirror_h:
            lum = lum[:, ::-1]
        if self.image_settings.mirror_v:
            lum = lum[::-1, :]
        lum = np.ascontiguousarray(lum)
        dpi_prev = pw / (self.settings.plate_w / 25.4)
        radius = self.settings.diffusion / 100.0 / 25.4 * dpi_prev
        if radius > 0.3:
            blurred = Image.fromarray((lum * 255 + 0.5).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(radius))
            lum = np.asarray(blurred, dtype=np.float32) / 255.0
        sim = engine.simuler_vers_image(lum[..., None], color["lin"], self.settings.intensity / 100.0)
        self.timing["simulation"] = (time.perf_counter() - t_b) * 1000
        return sim

    def _original_with_crop(self):
        """Image source entière ; hors de la zone gravée, elle est assombrie
        et la zone est cernée d'un cadre rouge."""
        prev = self.source_small.copy()
        prev.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
        framing, zoom, ox, oy = self._frame_args()
        if framing != 0:
            return prev
        box = engine.boite_recadrage(prev.width, prev.height,
                                     self.settings.plate_w / self.settings.plate_h, zoom, ox, oy)
        b = tuple(int(round(v)) for v in box)
        if b[2] - b[0] >= prev.width - 1 and b[3] - b[1] >= prev.height - 1:
            return prev  # toute l'image est utilisée
        dark = Image.blend(prev, Image.new("RGB", prev.size, (0, 0, 0)), 0.6)
        dark.paste(prev.crop(b), b[:2])
        ImageDraw.Draw(dark).rectangle([b[0], b[1], b[2] - 1, b[3] - 1], outline=(255, 60, 60), width=2)
        return dark

    def _color_data(self, pw, ph):
        """Calque couleur de l'aperçu, mis en cache : il ne dépend ni du
        tramage ni des réglages de « Graver une image », seulement de
        l'image, du cadrage, de la saturation et de la clarté."""
        key = (self._version, pw, ph, self._frame_args(),
               self.settings.saturation, self.settings.lightness)
        cache = self._color_cache
        if cache is None or cache["key"] != key:
            img = engine.cadrer(self.source_small, pw, ph, *self._frame_args())
            color = engine.calculer_calque_couleur(
                np.asarray(img), self.settings.saturation / 100.0, self.settings.lightness / 100.0)
            cache = {"key": key, "img": img, "couleur": color, "lin": engine.vers_lineaire(color)}
            self._color_cache = cache
        return cache

    # -- export

    def export_files(self):
        """Demande un dossier et y exporte les calques (export), avec un
        message à la fin. Rien n'est fait tant que le calque noir n'est pas
        prêt."""
        engraved = self._engraved()
        if not self.has_image() or engraved is None:
            self.dialogs.info(tr("sep.tab_title"), tr("sep.no_image_loaded"))
            return
        if self._image_busy():
            self.dialogs.info(tr("sep.tab_title"), tr("sep.not_ready"))
            return
        folder = self.dialogs.open_folder(tr("sep.export_folder"))
        if not folder:
            return
        try:
            with self._busy():
                files, pdf_ok = self.export(folder, engraved)
        except Exception as e:
            self.dialogs.error(tr("laser.error"), str(e))
            return
        msg = tr("sep.files_created") + "\n" + "\n".join(os.path.basename(p) for p in files)
        if not pdf_ok:
            msg += "\n\n" + tr("sep.pdf_too_large")
        self.dialogs.info(tr("sep.export_complete"), msg)

    def export(self, folder, engraved):
        """Écrit dans `folder` le calque noir (tel que reçu par le laser), le
        calque couleur (PNG à la résolution d'impression) et son PDF à
        l'échelle 1:1. Renvoie (fichiers écrits, PDF écrit ?). Lève une
        exception en cas d'erreur d'écriture."""
        base = os.path.join(folder, os.path.splitext(os.path.basename(self.path))[0])
        w_mm, h_mm = self.settings.plate_w, self.settings.plate_h
        dpi_engrave = self.engrave_dpi()
        dpi_print = self.settings.print_dpi

        f_engrave = f"{base}_gravure.png"
        engrave = Image.fromarray(engraved)
        if self.image_settings.algorithm != "Niveaux de Gris":
            engrave = engrave.point(lambda x: 255 if x > 127 else 0, mode="1")
        engrave.save(f_engrave, dpi=(dpi_engrave, dpi_engrave))

        # Calque couleur : même taille physique, à la résolution d'impression.
        img = engine.cadrer(self.source, round(w_mm / 25.4 * dpi_print), round(h_mm / 25.4 * dpi_print),
                            *self._frame_args())
        color = engine.array_vers_image(engine.calculer_calque_couleur(
            np.asarray(img), self.settings.saturation / 100.0, self.settings.lightness / 100.0))
        if self.settings.mirror_print:
            color = ImageOps.mirror(color)
        f_color = f"{base}_couleur.png"
        color.save(f_color, dpi=(dpi_print, dpi_print))
        f_pdf = f"{base}_couleur.pdf"
        pdf_ok = engine.generer_pdf_impression(color, dpi_print, f_pdf, w_mm, h_mm)
        return [f_engrave, f_color] + ([f_pdf] if pdf_ok else []), pdf_ok

    # -- diagnostic de durée

    def _mark_t0(self):
        self._t0 = time.perf_counter()

    def timing_report(self, engraved, t_hook, t_end):
        """Ligne de diagnostic (durées du traitement et des aperçus), puis
        remise à zéro ; None si le diagnostic est coupé."""
        if not self.DEBUG_TIMING or self.source is None or engraved is None:
            return None
        h, w = engraved.shape
        tm = self.timing
        before = f"{(t_hook - self._t0) * 1000:.0f} ms" if self._t0 else "?"
        self._t0 = None
        return (f"[Séparation] {self.image_settings.algorithm} | numba actif : {HAS_NUMBA} | "
                f"tableau {w}x{h} px ({w * h / 1e6:.1f} Mpx) | "
                f"attente+traitement Image&Filtres : {before} | "
                f"aperçu : {(t_end - t_hook) * 1000:.0f} ms "
                f"(couleur {tm.get('couleur', 0):.0f}, simulation {tm.get('simulation', 0):.0f}, "
                f"affichage {tm.get('affichage', 0):.0f})")
