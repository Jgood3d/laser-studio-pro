## [2.4.0] — 2026-10-20

### Ajouté
- **Imbrication automatique (nesting)** : le bouton « 🧩 Imbrication auto » de l'éditeur vectoriel range les pièces sélectionnées (ou tous les objets des calques actifs) sur une feuille aux dimensions voulues pour gaspiller le moins de matière possible. Les pièces sont placées de la plus grande à la plus petite, en bas à gauche d'abord, avec la forme réelle des contours (une petite pièce se glisse dans le creux d'un « L ») ; rotations au choix (aucune, 0°/90°, par quarts de tour, tous les 45°), écart entre pièces, marge au bord de la feuille et précision de la grille réglables. Un trou ou un détail gravé reste avec sa pièce et tourne avec elle (regroupement par inclusion). Les pièces qui n'ont pas trouvé de place restent où elles sont et sont comptées. Annulable avec Ctrl+Z. Mesuré : 40 pièces sur 400 x 400 mm en moins d'une seconde à la précision normale.
- **Ordre de découpe sûr** (réglage « Configuration GRBL », activé par défaut, enregistré dans le projet) : les calques de gravure et de marquage passent avant les calques de découpe, et dans un calque de découpe les contours intérieurs (trous, détails) sont coupés avant ceux qui les contiennent. La pièce ne bouge ni ne bascule avant que ses détails soient faits. Décoché, le G-Code reste strictement identique à celui des versions précédentes.
- **Netteté dans les réglages photo** (Image / Filtres, après le gamma) : accentuation des contours avant le tramage (0 à 100), proportionnelle à la résolution de gravure, prise en compte par l'annulation, le projet, la comparaison des algorithmes de tramage et l'onglet Séparation. À 0, le résultat est identique à avant.
- **Tests** : ordre de découpe, imbrication (aucune collision, espacement et marges, rotations, emboîtement dans les creux, groupes rigides), netteté, et un contrôle qui détecte tout nom utilisé sans être importé. La suite compte 294 tests.

### Migration
- Aucun format n'est cassé : la netteté vaut 0 et l'ordre de découpe sûr est activé par défaut pour les anciens projets (voir la note ci-dessus : décoche-le pour retrouver l'ancien ordre exact).

Fichiers modifiés :
app_utils.py, workers.py, image_processing_mixin.py, ui_setup_mixin.py, project_io_mixin.py, gcode_generation_mixin.py,
vector_layers.py, vector_editing_mixin.py, i18n.py — nouveaux modules : image_filters.py, vector_order.py, nesting.py,
nesting_apply.py, nesting_dialog.py — nouveaux tests : tests/
