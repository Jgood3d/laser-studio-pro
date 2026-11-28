"""Textes de l'interface : aperçu 3D des pièces plates (porte-clés, boules de Noël). Clé -> {langue: texte} ; voir
i18n/translations.py. La matière, l'export PNG et l'aide à la souris sont ceux de la boîte (clés « box.* »)."""

TEXTS = {
    "plate3d.thickness": {
        "fr": "Épaisseur",
        "en": "Thickness",
        "de": "Dicke",
        "es": "Grosor",
    },
    "plate3d.thickness_tip": {
        "fr": "Épaisseur de la plaque, pour l'aperçu seulement : elle ne change ni les contours ni le G-Code.",
        "en": "Sheet thickness, for the preview only: it changes neither the outlines nor the G-code.",
        "de": "Plattendicke, nur für die Vorschau: sie ändert weder die Konturen noch den G-Code.",
        "es": "Grosor de la plancha, solo para la vista previa: no cambia ni los contornos ni el G-code.",
    },
    "plate3d.default_png": {
        "fr": "apercu-3d.png",
        "en": "preview-3d.png",
        "de": "vorschau-3d.png",
        "es": "vista-previa-3d.png",
    },
    "plate3d.batch_first": {
        "fr": "Lot : l'aperçu 3D montre le premier prénom ({name}).",
        "en": "Batch: the 3D preview shows the first name ({name}).",
        "de": "Serie: Die 3D-Vorschau zeigt den ersten Namen ({name}).",
        "es": "Lote: la vista previa 3D muestra el primer nombre ({name}).",
    },
    "plate3d.empty": {
        "fr": "Rien à afficher en 3D.",
        "en": "Nothing to show in 3D.",
        "de": "Nichts in 3D anzuzeigen.",
        "es": "Nada que mostrar en 3D.",
    },
}
