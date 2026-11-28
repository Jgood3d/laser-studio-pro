"""Image de travail de Stencil Studio : photo chargée, version réduite pour
l'affichage, repères peints par l'utilisateur (sujet / fond).

    session = StudioSession()
    session.load_image(open("photo.jpg", "rb").read(), "photo.jpg")
    session.set_hints(png_bytes)            # repères peints dans la page

Les numéros `img_id` et `hints_ver` changent à chaque nouvelle image ou
nouveaux repères : le contrôleur (controllers/api.py) s'en sert pour savoir
si un résultat en cache est encore valable.
"""
import io

import numpy as np
from PIL import Image

from .. import core

# Taille maxi (px) de l'image affichée et des repères peints.
DISPLAY_MAX = 1600


class StudioSession:
    def __init__(self):
        self.img = None              # photo d'origine (PIL, RGB)
        self.name = "image"          # nom du fichier, pour les exports
        self.disp_jpeg = b""         # version réduite envoyée à la page
        self.disp_size = (1, 1)
        self.disp_rgb = None         # version réduite (numpy) : détourage, visage
        self.hints = None            # repères peints (codes, à la taille affichée)
        self.hints_ver = 0
        self.img_id = 0

    def has_image(self):
        return self.img is not None

    def load_image(self, data, name):
        """Nouvelle photo (octets du fichier) : version d'affichage, repères effacés."""
        img = core.to_rgb(Image.open(io.BytesIO(data)))
        img.load()
        disp = img.copy()
        disp.thumbnail((DISPLAY_MAX, DISPLAY_MAX), Image.LANCZOS)
        buf = io.BytesIO()
        disp.save(buf, "JPEG", quality=90)
        self.img, self.name = img, name
        self.disp_jpeg, self.disp_size = buf.getvalue(), disp.size
        self.disp_rgb = np.array(disp)
        self.hints = np.zeros((disp.height, disp.width), np.uint8)
        self.hints_ver += 1
        self.img_id += 1

    def set_hints(self, png_bytes):
        """Repères peints dans la page (PNG à la taille d'affichage)."""
        im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        dw, dh = self.disp_size
        if im.size != (dw, dh):
            im = im.resize((dw, dh), Image.NEAREST)
        arr = np.array(im)
        self.hints = core.codes_from_rgb(arr[..., :3], arr[..., 3])
        self.hints_ver += 1

    def has_hints(self):
        return self.hints is not None and bool(self.hints.any())
