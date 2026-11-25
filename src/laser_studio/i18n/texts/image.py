"""Textes de l'interface : graver une image, séparation des couleurs, vectorisation PNG → SVG, visualisation 2D. Clé -> {langue: texte} ; voir i18n/translations.py."""

TEXTS = {

    # --- Onglet Image & Filtres ---
    "img.properties_box": {"fr": "Propriétés de l'image", "en": "Image properties", "de": "Bildeigenschaften",
                           "es": "Propiedades de la imagen"},
    "img.load": {
        "fr": "Charger Image\n(ou glisser-déposer)", "en": "Load Image\n(or drag & drop)",
        "de": "Bild laden\n(oder per Drag & Drop)", "es": "Cargar imagen\n(o arrastrar y soltar)",
    },
    "img.delete": {
        "fr": "Supprimer l'image", "en": "Delete Image",
        "de": "Bild löschen", "es": "Eliminar imagen",
    },
    "img.rotate_left": {
        "fr": "Pivoter l'image de 90° vers la gauche", "en": "Rotate Image 90° Left",
        "de": "Bild um 90° nach links drehen", "es": "Girar la imagen 90° a la izquierda",
    },
    "img.rotate_right": {
        "fr": "Pivoter l'image de 90° vers la droite", "en": "Rotate Image 90° Right",
        "de": "Bild um 90° nach rechts drehen", "es": "Girar la imagen 90° a la derecha",
    },
    "img.mirror_h": {
        "fr": "Miroir horizontal", "en": "Horizontal Mirror",
        "de": "Horizontal spiegeln", "es": "Espejo horizontal",
    },
    "img.mirror_v": {
        "fr": "Miroir vertical", "en": "Vertical Mirror",
        "de": "Vertikal spiegeln", "es": "Espejo vertical",
    },
    "img.invert": {
        "fr": "Inverser Couleurs (Négatif)", "en": "Invert Colors (Negative)",
        "de": "Farben invertieren (Negativ)", "es": "Invertir colores (Negativo)",
    },
    "img.material_bg": {
        "fr": "Matière :", "en": "Material:",
        "de": "Material:", "es": "Material:",
    },
    "img.engrave_layer": {
        "fr": "Calque de gravure :", "en": "Engraving layer:",
        "de": "Gravurebene:", "es": "Capa de grabado:",
    },
    "img.engrave_layer_tip": {
        "fr": "Calque dont la vitesse et la puissance servent à graver l'image. Seuls les calques en mode « Gravure Remplie » sont proposés ; ses réglages se modifient dans l'onglet Calques.",
        "en": "Layer whose speed and power are used to engrave the image. Only layers in \"Fill Engraving\" mode are listed; edit its settings in the Layers tab.",
        "de": "Ebene, deren Geschwindigkeit und Leistung zum Gravieren des Bildes dienen. Nur Ebenen im Modus „Gefüllte Gravur“ werden angeboten; ihre Einstellungen ändern Sie im Reiter Ebenen.",
        "es": "Capa cuya velocidad y potencia se usan para grabar la imagen. Solo se ofrecen las capas en modo «Grabado relleno»; sus ajustes se cambian en la pestaña Capas.",
    },
    "img.engrave_layer_none": {
        "fr": "(aucun calque de gravure)", "en": "(no engraving layer)",
        "de": "(keine Gravurebene)", "es": "(ninguna capa de grabado)",
    },
    "img.bg_dark": {
        "fr": "Fond noir (alu anodisé, verre peint, ardoise, acrylique noir)",
        "en": "Dark background (anodized aluminium, painted glass, slate, black acrylic)",
        "de": "Dunkler Untergrund (eloxiertes Aluminium, lackiertes Glas, Schiefer, schwarzes Acryl)",
        "es": "Fondo negro (aluminio anodizado, vidrio pintado, pizarra, acrílico negro)",
    },
    "img.bg_light": {
        "fr": "Fond clair (bois, carton, cuir)",
        "en": "Light background (wood, cardboard, leather)",
        "de": "Heller Untergrund (Holz, Karton, Leder)",
        "es": "Fondo claro (madera, cartón, cuero)",
    },
    "img.material_bg_tooltip": {
        "fr": "Coche ou décoche « Inverser Couleurs » à ta place.\nFond noir : le laser éclaircit ce qu'il brûle (négatif activé, les zones claires sont gravées).\nFond clair : le laser noircit ce qu'il brûle (négatif désactivé, les zones sombres sont gravées).\nTu peux toujours modifier la case à la main. Le miroir n'est pas modifié.",
        "en": "Checks or unchecks \"Invert Colors\" for you.\nDark background: the laser lightens what it burns (negative on, light areas are engraved).\nLight background: the laser darkens what it burns (negative off, dark areas are engraved).\nYou can still change the checkbox by hand. Mirror is not changed.",
        "de": "Aktiviert oder deaktiviert \"Farben invertieren\" für dich.\nDunkler Untergrund: Der Laser hellt auf, was er brennt (Negativ aktiv, helle Bereiche werden graviert).\nHeller Untergrund: Der Laser dunkelt ab, was er brennt (Negativ inaktiv, dunkle Bereiche werden graviert).\nDu kannst das Kontrollkästchen weiterhin manuell ändern. Die Spiegelung bleibt unverändert.",
        "es": "Marca o desmarca \"Invertir colores\" por ti.\nFondo negro: el láser aclara lo que quema (negativo activado, se graban las zonas claras).\nFondo claro: el láser oscurece lo que quema (negativo desactivado, se graban las zonas oscuras).\nSiempre puedes cambiar la casilla a mano. El espejo no se modifica.",
    },
    "sep.gain_test_btn": {
        "fr": "Tester le gain de point…",
        "en": "Test the dot gain…",
        "de": "Punktzuwachs testen…",
        "es": "Probar la ganancia de punto…",
    },
    "sep.gain_test_tip": {
        "fr": "Génère une grille de test à graver sur ton verre pour trouver la bonne valeur du gain de point.",
        "en": "Generates a test grid to engrave on your glass to find the right dot gain value.",
        "de": "Erzeugt ein Testraster zum Gravieren auf deinem Glas, um den richtigen Punktzuwachs zu finden.",
        "es": "Genera una cuadrícula de prueba para grabar en tu vidrio y encontrar el valor correcto de ganancia de punto.",
    },
    "sep.gain_test_title": {
        "fr": "Test du gain de point",
        "en": "Dot gain test",
        "de": "Punktzuwachs-Test",
        "es": "Prueba de ganancia de punto",
    },
    "sep.gain_test_too_big": {
        "fr": "La grille de test ({w:.0f} x {h:.0f} mm) dépasse la surface de travail de la machine ({bed_w:.0f} x {bed_h:.0f} mm).",
        "en": "The test grid ({w:.0f} x {h:.0f} mm) is larger than the machine's work area ({bed_w:.0f} x {bed_h:.0f} mm).",
        "de": "Das Testraster ({w:.0f} x {h:.0f} mm) ist größer als die Arbeitsfläche der Maschine ({bed_w:.0f} x {bed_h:.0f} mm).",
        "es": "La cuadrícula de prueba ({w:.0f} x {h:.0f} mm) supera la superficie de trabajo de la máquina ({bed_w:.0f} x {bed_h:.0f} mm).",
    },
    "sep.gain_test_done": {
        "fr": "La grille est prête (aperçu 2D et console).\n\nGrave-la sur ton verre avec la résolution, la vitesse et la puissance habituelles. Elle comporte une ligne par valeur du gain (0, 5, 10, 15 et 20, écrites à gauche) et 11 colonnes, de 0 % (peinture intacte) à 100 % (verre dégagé).\n\nPlace le verre devant la lumière et choisis la ligne dont les cases passent régulièrement du noir au clair (la case à 50 % doit paraître à mi-chemin). Règle ensuite le curseur « Gain de point » sur la valeur de cette ligne.",
        "en": "The grid is ready (2D preview and console).\n\nEngrave it on your glass with your usual resolution, speed and power. It has one row per gain value (0, 5, 10, 15 and 20, written on the left) and 11 columns, from 0 % (paint untouched) to 100 % (glass fully cleared).\n\nHold the glass in front of a light and pick the row whose cells go evenly from black to light (the 50 % cell should look halfway). Then set the “Dot gain” slider to that row's value.",
        "de": "Das Raster ist fertig (2D-Vorschau und Konsole).\n\nGraviere es mit deiner üblichen Auflösung, Geschwindigkeit und Leistung auf dein Glas. Es hat eine Zeile pro Gain-Wert (0, 5, 10, 15 und 20, links geschrieben) und 11 Spalten, von 0 % (Farbe unberührt) bis 100 % (Glas vollständig freigelegt).\n\nHalte das Glas vor eine Lichtquelle und wähle die Zeile, deren Felder gleichmäßig von Schwarz zu Hell übergehen (das 50-%-Feld sollte genau in der Mitte wirken). Stelle dann den Regler „Punktzuwachs“ auf den Wert dieser Zeile ein.",
        "es": "La cuadrícula está lista (vista previa 2D y consola).\n\nGrábala en tu vidrio con tu resolución, velocidad y potencia habituales. Tiene una fila por valor de ganancia (0, 5, 10, 15 y 20, escritos a la izquierda) y 11 columnas, de 0 % (pintura intacta) a 100 % (vidrio totalmente despejado).\n\nColoca el vidrio frente a la luz y elige la fila cuyas casillas pasan de forma uniforme del negro al claro (la casilla del 50 % debe verse a medio camino). Después ajusta el control «Ganancia de punto» al valor de esa fila.",
    },
    # --- Netteté ---
    "img.sharpness": {
        "fr": "Netteté :",
        "en": "Sharpness:",
        "de": "Schärfe:",
        "es": "Nitidez:",
    },
    "img.sharpness_tip": {
        "fr": "Accentue les contours avant le tramage (masque flou) : les petits détails, visages et textes ressortent mieux à la gravure. 0 = aucun effet. Au-delà de 60, des halos peuvent apparaître : vérifie dans l'aperçu.",
        "en": "Sharpens edges before dithering (unsharp mask): small details, faces and text stand out better when engraved. 0 = no effect. Above 60, halos may appear: check the preview.",
        "de": "Verstärkt die Kanten vor der Rasterung (Unscharf-Maskierung): feine Details, Gesichter und Texte treten beim Gravieren besser hervor. 0 = keine Wirkung. Über 60 können Lichthöfe entstehen: prüfe die Vorschau.",
        "es": "Realza los bordes antes del tramado (máscara de enfoque): los detalles pequeños, rostros y textos destacan mejor al grabar. 0 = sin efecto. Por encima de 60 pueden aparecer halos: comprueba la vista previa.",
    },
    # --- Recadrer ---
    "img.crop_tip": {
        "fr": "Recadrer l'image", "en": "Crop the image", "de": "Bild zuschneiden", "es": "Recortar la imagen",
    },
    "img.crop_title": {
        "fr": "Recadrer l'image", "en": "Crop the image", "de": "Bild zuschneiden", "es": "Recortar la imagen",
    },
    "img.crop_hint": {
        "fr": "Tracez le cadre à garder. Glissez dans le cadre pour le déplacer, sur un coin ou un bord pour le redimensionner. La taille gravée suit le cadre, à la même échelle.",
        "en": "Draw the frame to keep. Drag inside the frame to move it, on a corner or edge to resize it. The engraved size follows the frame, at the same scale.",
        "de": "Zeichnen Sie den zu behaltenden Rahmen. Im Rahmen ziehen zum Verschieben, an einer Ecke oder Kante zum Ändern der Größe. Die Gravurgröße folgt dem Rahmen im gleichen Maßstab.",
        "es": "Dibuje el marco que se conserva. Arrastre dentro del marco para moverlo, en una esquina o un borde para cambiar su tamaño. El tamaño grabado sigue al marco, a la misma escala.",
    },
    "img.crop_keep_ratio": {
        "fr": "Garder les proportions", "en": "Keep proportions", "de": "Seitenverhältnis beibehalten",
        "es": "Mantener las proporciones",
    },
    "img.crop_whole": {
        "fr": "Toute l'image", "en": "Whole image", "de": "Ganzes Bild", "es": "Toda la imagen",
    },
    "img.crop_size": {
        "fr": "{w} × {h} px", "en": "{w} × {h} px", "de": "{w} × {h} px", "es": "{w} × {h} px",
    },
    # --- Filtres : effet bande dessinée ---
    "img.filter": {
        "fr": "Appliquer un filtre :", "en": "Apply a filter:", "de": "Filter anwenden:", "es": "Aplicar un filtro:",
    },
    "img.filter_none": {
        "fr": "Aucun", "en": "None", "de": "Keiner", "es": "Ninguno",
    },
    "img.filter_cartoon": {
        "fr": "Effet BD", "en": "Comic effect", "de": "Comic-Effekt", "es": "Efecto cómic",
    },
    "img.filter_tip": {
        "fr": "Filtre appliqué à l'image avant le tramage. « Effet BD » ouvre ses réglages ; choisir « Effet BD » à nouveau permet de les modifier.",
        "en": "Filter applied to the image before dithering. \"Comic effect\" opens its settings; choosing it again lets you change them.",
        "de": "Filter, der vor der Rasterung auf das Bild angewendet wird. „Comic-Effekt“ öffnet seine Einstellungen; erneut wählen, um sie zu ändern.",
        "es": "Filtro aplicado a la imagen antes del tramado. «Efecto cómic» abre sus ajustes; elegirlo de nuevo permite cambiarlos.",
    },
    "img.cartoon_title": {
        "fr": "Effet BD", "en": "Comic effect", "de": "Comic-Effekt", "es": "Efecto cómic",
    },
    "img.cartoon_intro": {
        "fr": "Noircit le bord des traits pour donner un effet Bande Dessinée.",
        "en": "Darkens the edges of lines to give a comic book effect.",
        "de": "Schwärzt die Ränder der Linien für einen Comic-Effekt.",
        "es": "Oscurece el borde de los trazos para dar un efecto de cómic.",
    },
    "img.cartoon_radius": {
        "fr": "Rayon du masque", "en": "Mask radius", "de": "Maskenradius", "es": "Radio de la máscara",
    },
    "img.cartoon_black": {
        "fr": "Pourcentage de noir", "en": "Percent black", "de": "Schwarzanteil", "es": "Porcentaje de negro",
    },
    "img.cartoon_radius_tip": {
        "fr": "Effet bande dessinée : noircit le bord des traits. Rayon du masque, en mm sur la pièce : la zone à laquelle chaque point est comparé. Petit rayon : traits fins ; grand rayon : traits épais et aplats noirs.",
        "en": "Comic effect: darkens the edges of lines. Mask radius, in mm on the piece: the area each point is compared with. Small radius: thin lines; large radius: thick lines and black areas.",
        "de": "Comic-Effekt: schwärzt die Ränder der Linien. Maskenradius in mm auf dem Werkstück: der Bereich, mit dem jeder Punkt verglichen wird. Kleiner Radius: feine Linien; großer Radius: dicke Linien und schwarze Flächen.",
        "es": "Efecto cómic: oscurece el borde de los trazos. Radio de la máscara, en mm sobre la pieza: la zona con la que se compara cada punto. Radio pequeño: trazos finos; radio grande: trazos gruesos y zonas negras.",
    },
    "img.cartoon_black_tip": {
        "fr": "Effet bande dessinée : part de l'image qui devient noire (les points les plus sombres par rapport à leur voisinage). Plus haut : plus de noir autour des traits.",
        "en": "Comic effect: share of the image that turns black (the points darkest compared with their surroundings). Higher: more black around the lines.",
        "de": "Comic-Effekt: Anteil des Bildes, der schwarz wird (die im Vergleich zur Umgebung dunkelsten Punkte). Höher: mehr Schwarz um die Linien.",
        "es": "Efecto cómic: parte de la imagen que se vuelve negra (los puntos más oscuros respecto a su entorno). Más alto: más negro alrededor de los trazos.",
    },
    # --- Taille d'origine de l'image ---
    "image.natural_size": {
        "fr": "Image insérée à sa taille d'origine : {w:.1f} x {h:.1f} mm ({dpi:.0f} DPI).",
        "en": "Image inserted at its original size: {w:.1f} x {h:.1f} mm ({dpi:.0f} DPI).",
        "de": "Bild in Originalgröße eingefügt: {w:.1f} x {h:.1f} mm ({dpi:.0f} DPI).",
        "es": "Imagen insertada a su tamaño original: {w:.1f} x {h:.1f} mm ({dpi:.0f} DPI).",
    },
    "image.natural_size_fit": {
        "fr": "Image réduite pour tenir dans la zone de travail : {w:.1f} x {h:.1f} mm (taille d'origine : {ow:.0f} x {oh:.0f} mm, {dpi:.0f} DPI).",
        "en": "Image reduced to fit the work area: {w:.1f} x {h:.1f} mm (original size: {ow:.0f} x {oh:.0f} mm, {dpi:.0f} DPI).",
        "de": "Bild verkleinert, um in den Arbeitsbereich zu passen: {w:.1f} x {h:.1f} mm (Originalgröße: {ow:.0f} x {oh:.0f} mm, {dpi:.0f} DPI).",
        "es": "Imagen reducida para caber en la zona de trabajo: {w:.1f} x {h:.1f} mm (tamaño original: {ow:.0f} x {oh:.0f} mm, {dpi:.0f} DPI).",
    },
    "img.reset": {
        "fr": "Réinitialiser Réglages Image", "en": "Reset Image Settings",
        "de": "Bildeinstellungen zurücksetzen", "es": "Restablecer ajustes de imagen",
    },
    "ui.img_undo": {
        "fr": "Annuler un réglage image (Ctrl+Z)", "en": "Undo Image Setting (Ctrl+Z)",
        "de": "Bildeinstellung rückgängig (Strg+Z)", "es": "Deshacer ajuste de imagen (Ctrl+Z)",
    },
    "ui.img_redo": {
        "fr": "Refaire un réglage image (Ctrl+Y)", "en": "Redo Image Setting (Ctrl+Y)",
        "de": "Bildeinstellung wiederholen (Strg+Y)", "es": "Rehacer ajuste de imagen (Ctrl+Y)",
    },
    "img.brightness": {"fr": "Luminosité:", "en": "Brightness:", "de": "Helligkeit:", "es": "Brillo:"},
    "img.contrast": {"fr": "Contraste:", "en": "Contrast:", "de": "Kontrast:", "es": "Contraste:"},
    "img.gamma": {"fr": "Gamma:", "en": "Gamma:", "de": "Gamma:", "es": "Gamma:"},
    "img.algorithm": {"fr": "Algorithme:", "en": "Algorithm:", "de": "Algorithmus:", "es": "Algoritmo:"},
    "img.resolution": {"fr": "Résolution :", "en": "Resolution:", "de": "Auflösung:", "es": "Resolución:"},
    "img.mode_lmm": {
        "fr": "Lignes / mm", "en": "Lines / mm", "de": "Linien / mm", "es": "Líneas / mm",
    },
    "img.mode_focal": {
        "fr": "Focale laser (spot)", "en": "Laser Focal (spot)",
        "de": "Laserfokus (Spot)", "es": "Focal láser (spot)",
    },
    "img.configure_focal": {
        "fr": "Configurer la focale du laser >", "en": "Configure laser focal >",
        "de": "Laserfokus konfigurieren >", "es": "Configurar focal del láser >",
    },
    "img.compare_algos": {
        "fr": "Algorithme de tramage",
        "en": "Dithering Algorithm",
        "de": "Rasteralgorithmus",
        "es": "Algoritmo de tramado",
    },
    "img.show_original": {
        "fr": "Afficher l'originale", "en": "Show Original",
        "de": "Original anzeigen", "es": "Mostrar el original",
    },
    "img.as_is": {
        "fr": "Image déjà tramée (graver telle quelle)",
        "en": "Already dithered image (engrave as is)",
        "de": "Bereits gerastertes Bild (unverändert gravieren)",
        "es": "Imagen ya tramada (grabar tal cual)",
    },
    "img.as_is_tip": {
        "fr": "Pour une image déjà tramée par Image-R ou un autre logiciel : pas de tons, de netteté ni de nouveau tramage ; l'image est mise à l'échelle au plus proche voisin puis seuillée. À l'activation, la résolution est calée sur les pixels de l'image (1 pixel = 1 ligne de gravure), d'après la taille issue des DPI du fichier.",
        "en": "For an image already dithered by Image-R or other software: no tones, sharpness or new dithering; the image is scaled with nearest neighbour then thresholded. When enabled, the resolution is matched to the image pixels (1 pixel = 1 engraving line), from the size given by the file's DPI.",
        "de": "Für ein bereits mit Image-R oder anderer Software gerastertes Bild: keine Tonwerte, Schärfe oder erneute Rasterung; das Bild wird per Nearest-Neighbor skaliert und dann binarisiert. Beim Aktivieren wird die Auflösung an die Bildpixel angepasst (1 Pixel = 1 Gravurlinie), ausgehend von der Größe aus den DPI der Datei.",
        "es": "Para una imagen ya tramada con Image-R u otro programa: sin tonos, nitidez ni nuevo tramado; la imagen se escala por vecino más próximo y se umbraliza. Al activarlo, la resolución se ajusta a los píxeles de la imagen (1 píxel = 1 línea de grabado), según el tamaño dado por los DPI del archivo.",
    },
    "image.as_is_not_binary": {
        "fr": "Cette image n'est pas en noir et blanc : gravée telle quelle, elle sera seuillée (gris clair → blanc, gris foncé → noir). Décochez « Image déjà tramée » pour la tramer.",
        "en": "This image is not black and white: engraved as is, it will be thresholded (light grey → white, dark grey → black). Uncheck \"Already dithered image\" to dither it.",
        "de": "Dieses Bild ist nicht schwarzweiß: unverändert graviert wird es binarisiert (helles Grau → Weiß, dunkles Grau → Schwarz). Deaktivieren Sie \"Bereits gerastertes Bild\", um es zu rastern.",
        "es": "Esta imagen no es en blanco y negro: grabada tal cual se umbralizará (gris claro → blanco, gris oscuro → negro). Desmarque \"Imagen ya tramada\" para tramarla.",
    },
    "img.preview_tones": {
        "fr": "Aperçu avec les réglages",
        "en": "Preview with adjustments",
        "de": "Vorschau mit Einstellungen",
        "es": "Vista previa con ajustes",
    },
    "img.preview_invert": {
        "fr": "Inverser l'aperçu",
        "en": "Invert preview",
        "de": "Vorschau invertieren",
        "es": "Invertir vista previa",
    },
    "img.preview_invert_tip": {
        "fr": "Affiche l'image originale en négatif, pour la comparer au rendu. Aperçu seulement : indépendant de « Inverser Couleurs » et sans effet sur la gravure.",
        "en": "Shows the original image as a negative, to compare it with the result. Preview only: independent of \"Invert colours\" and without effect on the engraving.",
        "de": "Zeigt das Originalbild als Negativ, zum Vergleich mit dem Ergebnis. Nur Vorschau: unabhängig von \"Farben invertieren\" und ohne Einfluss auf die Gravur.",
        "es": "Muestra la imagen original en negativo, para compararla con el resultado. Solo vista previa: independiente de \"Invertir colores\" y sin efecto en el grabado.",
    },
    "img.preview_tones_tip": {
        "fr": "Applique à l'image originale la luminosité, le contraste, le gamma et la netteté, pour voir l'effet des réglages avant le tramage. N'affecte pas la gravure.",
        "en": "Applies brightness, contrast, gamma and sharpness to the original image to see the effect of the settings before dithering. Does not affect the engraving.",
        "de": "Wendet Helligkeit, Kontrast, Gamma und Schärfe auf das Originalbild an, um die Wirkung der Einstellungen vor der Rasterung zu sehen. Hat keinen Einfluss auf die Gravur.",
        "es": "Aplica brillo, contraste, gamma y nitidez a la imagen original para ver el efecto de los ajustes antes del tramado. No afecta al grabado.",
    },
    "img.show_original_tip": {
        "fr": "Afficher l'image originale à côté du rendu tramé.",
        "en": "Show the original image next to the dithered result.",
        "de": "Das Originalbild neben dem gerasterten Ergebnis anzeigen.",
        "es": "Mostrar la imagen original junto al resultado tramado.",
    },
    "img.compare_algos_tip": {
        "fr": "Comparer les algorithmes de tramage : une vignette de l'image chargée par algorithme, "
              "avec les réglages actuels (luminosité, contraste, gamma, netteté, négatif). "
              "Cliquer sur une vignette choisit cet algorithme.",
        "en": "Compare dithering algorithms: one thumbnail of the loaded image per algorithm, "
              "with the current settings (brightness, contrast, gamma, sharpness, negative). "
              "Click a thumbnail to select that algorithm.",
        "de": "Rasteralgorithmen vergleichen: eine Miniatur des geladenen Bildes pro Algorithmus, "
              "mit den aktuellen Einstellungen (Helligkeit, Kontrast, Gamma, Schärfe, Negativ). "
              "Ein Klick auf eine Miniatur wählt diesen Algorithmus.",
        "es": "Comparar algoritmos de tramado: una miniatura de la imagen cargada por algoritmo, "
              "con los ajustes actuales (brillo, contraste, gamma, nitidez, negativo). "
              "Hacer clic en una miniatura selecciona ese algoritmo.",
    },
    "preview.display_box": {"fr": "Affichage", "en": "Display", "de": "Anzeige", "es": "Visualización"},
    "preview.material_label": {
        "fr": "Matière :",
        "en": "Material:",
        "de": "Material:",
        "es": "Material:",
    },
    "preview.material_tip": {
        "fr": "Simule le rendu de la gravure sur différentes matières dans l'aperçu 2D (tons seulement, pas une simulation physique).",
        "en": "Simulates how the engraving looks on different materials in the 2D preview (tones only, not a physical simulation).",
        "de": "Simuliert die Gravur auf verschiedenen Materialien in der 2D-Vorschau (nur Töne, keine physikalische Simulation).",
        "es": "Simula el aspecto del grabado sobre distintos materiales en la vista 2D (solo tonos, no es una simulación física).",
    },
    "preview.material.light": {
        "fr": "Clair (papier / acrylique)",
        "en": "Light (paper / acrylic)",
        "de": "Hell (Papier / Acryl)",
        "es": "Claro (papel / acrílico)",
    },
    "preview.material.wood": {
        "fr": "Bois",
        "en": "Wood",
        "de": "Holz",
        "es": "Madera",
    },
    "preview.material.bamboo": {
        "fr": "Bambou",
        "en": "Bamboo",
        "de": "Bambus",
        "es": "Bambú",
    },
    "preview.material.slate": {
        "fr": "Ardoise",
        "en": "Slate",
        "de": "Schiefer",
        "es": "Pizarra",
    },
    "preview.material.acrylic_black": {
        "fr": "Acrylique noir",
        "en": "Black acrylic",
        "de": "Schwarzes Acryl",
        "es": "Acrílico negro",
    },
    "preview.flip": {
        "fr": "Inverser l'aperçu", "en": "Flip Preview",
        "de": "Vorschau spiegeln", "es": "Invertir vista previa",
    },
    "preview.flip_tip": {
        "fr": "Inverser l'aperçu de l'image (si l'image gravée apparaît retournée).",
        "en": "Flip the image preview (if the engraved image appears reversed).",
        "de": "Bildvorschau spiegeln (wenn das Bild beim Gravieren falsch herum erscheint).",
        "es": "Invertir la vista previa de la imagen (si la imagen grabada aparece invertida).",
    },
    "preview.negative": {
        "fr": "Aperçu en négatif", "en": "Negative Preview",
        "de": "Negative Vorschau", "es": "Vista previa negativa",
    },
    "preview.negative_tip": {
        "fr": "Inverse l'aperçu : les zones gravées apparaissent claires, les zones non gravées foncées. Décochée, l'aperçu montre la pièce telle qu'elle sortira (brûlure de la matière choisie).",
        "en": "Inverts the preview: engraved areas appear light, non-engraved areas dark. Unchecked, the preview shows the piece as it will come out (burn of the chosen material).",
        "de": "Kehrt die Vorschau um: gravierte Bereiche erscheinen hell, nicht gravierte dunkel. Ohne Haken zeigt die Vorschau das Werkstück so, wie es herauskommt (Brandfarbe des gewählten Materials).",
        "es": "Invierte la vista previa: las zonas grabadas aparecen claras y las no grabadas oscuras. Sin marcar, la vista previa muestra la pieza tal como saldrá (quemado del material elegido).",
    },
    "preview.hide_rapid": {
        "fr": "Masquer les déplacements rapides", "en": "Hide Rapid Moves",
        "de": "Eilgänge ausblenden", "es": "Ocultar movimientos rápidos",
    },
    "preview.hide_rapid_tip": {
        "fr": "Masquer les déplacements rapides G0 (laser éteint) dans l'aperçu.",
        "en": "Hide rapid G0 moves (laser off) in the preview.",
        "de": "Schnelle G0-Bewegungen (Laser aus) in der Vorschau ausblenden.",
        "es": "Ocultar los movimientos rápidos G0 (láser apagado) en la vista previa.",
    },
    # --- Traitement d'image ---
    "image.focal_info": {
        "fr": "Focale : {focal:.3f} mm  →  {lmm:.2f} lignes/mm  (≈ {dpi:.0f} DPI)",
        "en": "Focal length: {focal:.3f} mm  →  {lmm:.2f} lines/mm  (≈ {dpi:.0f} DPI)",
        "de": "Fokus: {focal:.3f} mm  →  {lmm:.2f} Linien/mm  (≈ {dpi:.0f} DPI)",
        "es": "Focal: {focal:.3f} mm  →  {lmm:.2f} líneas/mm  (≈ {dpi:.0f} DPI)",
    },
    "image.quality_too_fine": {
        "fr": "trop fin (risque de surgravure)",
        "en": "too fine (risk of overburning)",
        "de": "zu fein (Risiko von Überbrennen)",
        "es": "demasiado fino (riesgo de sobregrabado)",
    },
    "image.quality_fine": {
        "fr": "fin (surgravure probable)",
        "en": "fine (overburning likely)",
        "de": "fein (Überbrennen wahrscheinlich)",
        "es": "fino (probable sobregrabado)",
    },
    "image.quality_fine_ok": {
        "fr": "fin mais correct",
        "en": "fine but acceptable",
        "de": "fein, aber akzeptabel",
        "es": "fino pero correcto",
    },
    "image.quality_recommended": {
        "fr": "zone recommandée",
        "en": "recommended range",
        "de": "empfohlener Bereich",
        "es": "zona recomendada",
    },
    "image.quality_coarse": {
        "fr": "grossier mais correct",
        "en": "coarse but acceptable",
        "de": "grob, aber akzeptabel",
        "es": "grueso pero correcto",
    },
    "image.quality_result": {
        "fr": "Écart : {spacing:.3f} mm ({ratio:.1f}× la focale) — {quality}",
        "en": "Spacing: {spacing:.3f} mm ({ratio:.1f}× focal length) — {quality}",
        "de": "Abstand: {spacing:.3f} mm ({ratio:.1f}× Fokus) — {quality}",
        "es": "Separación: {spacing:.3f} mm ({ratio:.1f}× el focal) — {quality}",
    },
    "image.open_title": {
        "fr": "Ouvrir une image",
        "en": "Open Image",
        "de": "Bild öffnen",
        "es": "Abrir imagen",
    },
    "image.file_filter": {
        "fr": "Images (*.png *.jpg *.jpeg *.bmp)",
        "en": "Images (*.png *.jpg *.jpeg *.bmp)",
        "de": "Bilder (*.png *.jpg *.jpeg *.bmp)",
        "es": "Imágenes (*.png *.jpg *.jpeg *.bmp)",
    },
    "image.delete_title": {
        "fr": "Supprimer l'image",
        "en": "Delete Image",
        "de": "Bild löschen",
        "es": "Eliminar imagen",
    },
    "image.delete_question": {
        "fr": "Supprimer l'image chargée ? Cette action est irréversible "
              "(il faudra la recharger).",
        "en": "Delete the loaded image? This action cannot be undone "
              "(you will have to load it again).",
        "de": "Geladenes Bild löschen? Dieser Vorgang kann nicht rückgängig "
              "gemacht werden (du musst es erneut laden).",
        "es": "¿Eliminar la imagen cargada? Esta acción no se puede deshacer "
              "(tendrás que cargarla de nuevo).",
    },
    "image.deleted": {
        "fr": "Image supprimée.",
        "en": "Image deleted.",
        "de": "Bild gelöscht.",
        "es": "Imagen eliminada.",
    },
    "image.loaded": {
        "fr": "Image chargée : {path}",
        "en": "Image loaded: {path}",
        "de": "Bild geladen: {path}",
        "es": "Imagen cargada: {path}",
    },
    "image.error_title": {
        "fr": "Erreur",
        "en": "Error",
        "de": "Fehler",
        "es": "Error",
    },
    "image.load_error": {
        "fr": "Impossible de charger l'image :\n{error}",
        "en": "Unable to load the image:\n{error}",
        "de": "Das Bild konnte nicht geladen werden:\n{error}",
        "es": "No se puede cargar la imagen:\n{error}",
    },
    "image.compare_title": {
        "fr": "Comparer les algorithmes",
        "en": "Compare Algorithms",
        "de": "Algorithmen vergleichen",
        "es": "Comparar algoritmos",
    },
    "image.compare_empty": {
        "fr": "Charge d'abord une image.",
        "en": "Load an image first.",
        "de": "Lade zuerst ein Bild.",
        "es": "Primero carga una imagen.",
    },
    "image.compare_dialog_title": {
        "fr": "Comparaison des algorithmes de tramage",
        "en": "Dithering Algorithm Comparison",
        "de": "Vergleich der Rasteralgorithmen",
        "es": "Comparación de algoritmos de tramado",
    },

    # --- Onglet « Vectorisation d'image » (convertisseur PNG/JPEG → SVG intégré) ---
    "png2svg.tab_title": {
        "fr": "Vectorisation d'image", "en": "Image Vectorization",
        "de": "Bildvektorisierung", "es": "Vectorización de imagen",
    },
    "png2svg.open_image": {
        "fr": "Ouvrir une image…", "en": "Open image…",
        "de": "Bild öffnen…", "es": "Abrir imagen…",
    },
    "png2svg.export_svg": {
        "fr": "Exporter en SVG…", "en": "Export as SVG…",
        "de": "Als SVG exportieren…", "es": "Exportar como SVG…",
    },
    "png2svg.send_to_vector": {
        "fr": "Envoyer vers l'Éditeur Vectoriel", "en": "Send to Vector Editor",
        "de": "An Vektor-Editor senden", "es": "Enviar al Editor Vectorial",
    },
    "png2svg.settings": {
        "fr": "Réglages", "en": "Settings", "de": "Einstellungen", "es": "Ajustes",
    },
    "png2svg.mode": {
        "fr": "Mode", "en": "Mode", "de": "Modus", "es": "Modo",
    },
    "png2svg.mode_bw": {
        "fr": "Noir & blanc", "en": "Black & white",
        "de": "Schwarz-weiß", "es": "Blanco y negro",
    },
    "png2svg.mode_color": {
        "fr": "Couleur", "en": "Color", "de": "Farbe", "es": "Color",
    },
    "png2svg.render_mode": {
        "fr": "Rendu", "en": "Render", "de": "Darstellung", "es": "Render",
    },
    "png2svg.render_fill": {
        "fr": "Remplissage (gravure)", "en": "Fill (engraving)",
        "de": "Füllung (Gravur)", "es": "Relleno (grabado)",
    },
    "png2svg.render_outline": {
        "fr": "Contour (découpe)", "en": "Outline (cutting)",
        "de": "Kontur (Schneiden)", "es": "Contorno (corte)",
    },
    "png2svg.centerline": {
        "fr": "Ligne centrale (évite le doublage des traits)",
        "en": "Centerline (avoids doubled lines)",
        "de": "Mittellinie (vermeidet doppelte Linien)",
        "es": "Línea central (evita líneas duplicadas)",
    },
    "png2svg.stroke_width": {
        "fr": "Épaisseur de trait", "en": "Stroke width",
        "de": "Strichstärke", "es": "Grosor de línea",
    },
    "png2svg.fill_threshold": {
        "fr": "Seuil remplissage plein (px)", "en": "Solid-fill threshold (px)",
        "de": "Schwelle für Vollfüllung (px)", "es": "Umbral de relleno sólido (px)",
    },
    "png2svg.threshold": {
        "fr": "Seuil", "en": "Threshold", "de": "Schwellenwert", "es": "Umbral",
    },
    "png2svg.auto_threshold": {
        "fr": "Seuil automatique", "en": "Auto threshold",
        "de": "Automatischer Schwellenwert", "es": "Umbral automático",
    },
    "png2svg.invert": {
        "fr": "Inverser", "en": "Invert", "de": "Invertieren", "es": "Invertir",
    },
    "png2svg.smoothing": {
        "fr": "Lissage", "en": "Smoothing", "de": "Glättung", "es": "Suavizado",
    },
    "png2svg.simplify": {
        "fr": "Simplification", "en": "Simplify",
        "de": "Vereinfachung", "es": "Simplificación",
    },
    "png2svg.min_area": {
        "fr": "Aire minimale", "en": "Minimum area",
        "de": "Mindestfläche", "es": "Área mínima",
    },
    "png2svg.n_colors": {
        "fr": "Nombre de couleurs", "en": "Number of colors",
        "de": "Anzahl Farben", "es": "Número de colores",
    },
    "png2svg.output_size": {
        "fr": "Dimension de sortie", "en": "Output size",
        "de": "Ausgabegröße", "es": "Tamaño de salida",
    },
    "png2svg.width": {
        "fr": "Largeur", "en": "Width", "de": "Breite", "es": "Ancho",
    },
    "png2svg.height": {
        "fr": "Hauteur", "en": "Height", "de": "Höhe", "es": "Alto",
    },
    "png2svg.unit": {
        "fr": "Unité", "en": "Unit", "de": "Einheit", "es": "Unidad",
    },
    "png2svg.keep_aspect_ratio": {
        "fr": "Conserver les proportions", "en": "Keep aspect ratio",
        "de": "Seitenverhältnis beibehalten", "es": "Mantener proporciones",
    },
    "png2svg.original": {
        "fr": "Image originale", "en": "Original image",
        "de": "Originalbild", "es": "Imagen original",
    },
    "png2svg.svg_preview": {
        "fr": "Aperçu SVG", "en": "SVG preview",
        "de": "SVG-Vorschau", "es": "Vista previa SVG",
    },
    "png2svg.paths_count": {
        "fr": "{n} chemin(s) généré(s)", "en": "{n} path(s) generated",
        "de": "{n} Pfad(e) erzeugt", "es": "{n} trayecto(s) generado(s)",
    },
    "png2svg.no_image": {
        "fr": "Aucune image chargée", "en": "No image loaded",
        "de": "Kein Bild geladen", "es": "Ninguna imagen cargada",
    },
    "png2svg.no_image_clipboard": {
        "fr": "Aucune image dans le presse-papiers",
        "en": "No image in clipboard",
        "de": "Kein Bild in der Zwischenablage",
        "es": "No hay ninguna imagen en el portapapeles",
    },
    "png2svg.export_success": {
        "fr": "SVG exporté avec succès", "en": "SVG exported successfully",
        "de": "SVG erfolgreich exportiert", "es": "SVG exportado con éxito",
    },
    "png2svg.zoom_in": {
        "fr": "Zoom +", "en": "Zoom in", "de": "Vergrößern", "es": "Acercar",
    },
    "png2svg.zoom_out": {
        "fr": "Zoom −", "en": "Zoom out", "de": "Verkleinern", "es": "Alejar",
    },
    "png2svg.zoom_fit": {
        "fr": "Ajuster", "en": "Fit", "de": "Einpassen", "es": "Ajustar",
    },
    "png2svg.fullscreen_title": {
        "fr": "Vectorisation d'image — Plein écran", "en": "Image Vectorization — Full Screen",
        "de": "Bildvektorisierung — Vollbild", "es": "Vectorización de imagen — Pantalla completa",
    },
    "png2svg.close_fullscreen": {
        "fr": "✕ Fermer le plein écran (retour à la fenêtre normale)",
        "en": "✕ Exit full screen (return to normal window)",
        "de": "✕ Vollbild schließen (zum normalen Fenster zurückkehren)",
        "es": "✕ Cerrar pantalla completa (volver a la ventana normal)",
    },
# --- Séparation Couleur ---
    "sep.tab_title": {
        "fr": "Séparation Couleur / Verre", "en": "Color / Glass Separation",
        "de": "Farbtrennung / Glas", "es": "Separación de color / vidrio",
    },
    "sep.plate_title": {
        "fr": "Plaque de verre", "en": "Glass plate",
        "de": "Glasplatte", "es": "Placa de vidrio",
    },
    "sep.width": {"fr": "Largeur (mm):", "en": "Width (mm):", "de": "Breite (mm):", "es": "Ancho (mm):"},
    "sep.height": {"fr": "Hauteur (mm):", "en": "Height (mm):", "de": "Höhe (mm):", "es": "Alto (mm):"},
    "sep.print_dpi": {"fr": "DPI Impression:", "en": "Print DPI:", "de": "Druck-DPI:", "es": "DPI de impresión:"},
    "sep.framing": {"fr": "Cadrage:", "en": "Framing:", "de": "Ausschnitt:", "es": "Encuadre:"},
    "sep.crop_fit": {"fr": "Recadrer", "en": "Crop to fit", "de": "Zuschneiden", "es": "Recortar"},
    "sep.stretch": {"fr": "Étirer", "en": "Stretch", "de": "Strecken", "es": "Estirar"},
    "sep.black_layer_title": {
        "fr": "Calque Noir (gravure)", "en": "Black Layer (engraving)",
        "de": "Schwarze Ebene (Gravur)", "es": "Capa negra (grabado)",
    },
    "sep.color_layer_title": {
        "fr": "Calque Couleur (impression)", "en": "Color Layer (print)",
        "de": "Farbebene (Druck)", "es": "Capa de color (impresión)",
    },
    "sep.support_medium": {"fr": "Support:", "en": "Medium:", "de": "Medium:", "es": "Soporte:"},
    "sep.transparent_film": {"fr": "Film transparent", "en": "Transparent film", "de": "Klarsichtfolie", "es": "Película transparente"},
    "sep.tracing_paper": {"fr": "Papier calque", "en": "Tracing paper", "de": "Transparentpapier", "es": "Papel vegetal"},
    "sep.custom": {"fr": "Personnalisé", "en": "Custom", "de": "Benutzerdefiniert", "es": "Personalizado"},
    "sep.saturation": {"fr": "Saturation:", "en": "Saturation:", "de": "Sättigung:", "es": "Saturación:"},
    "sep.lightness": {"fr": "Clarté du calque:", "en": "Layer lightness:", "de": "Ebenenhelligkeit:", "es": "Claridad de la capa:"},
    "sep.mirror_print": {
        "fr": "Miroir horizontal (impression)", "en": "Horizontal mirror (print)",
        "de": "Horizontal spiegeln (Druck)", "es": "Espejo horizontal (impresión)",
    },
    "sep.backlight_title": {
        "fr": "Simulation rétro-éclairage", "en": "Backlight simulation",
        "de": "Hintergrundbeleuchtung simulieren", "es": "Simulación de retroiluminación",
    },
    "sep.light_diffusion": {"fr": "Diffusion lumière (mm):", "en": "Light diffusion (mm):", "de": "Lichtstreuung (mm):", "es": "Difusión de luz (mm):"},
    "sep.backlight_intensity": {"fr": "Intensité rétro-éclairage:", "en": "Backlight intensity:", "de": "Hintergrundintensität:", "es": "Intensidad de retroiluminación:"},
    "sep.export_btn": {"fr": "Exporter la séparation…", "en": "Export separation…", "de": "Trennung exportieren…", "es": "Exportar separación…"},
    "sep.tab_original": {"fr": "Original", "en": "Original", "de": "Original", "es": "Original"},
    "sep.tab_engraving": {"fr": "Fichier Gravure", "en": "Engraving File", "de": "Gravurdatei", "es": "Archivo de grabado"},
    "sep.tab_print": {"fr": "Fichier Impression", "en": "Print File", "de": "Druckdatei", "es": "Archivo de impresión"},
    "sep.tab_simulation": {"fr": "Simulation", "en": "Simulation", "de": "Simulation", "es": "Simulación"},
    "sep.no_image_loaded": {"fr": "Ouvre d'abord une image.", "en": "Open an image first.", "de": "Öffne zuerst ein Bild.", "es": "Abre primero una imagen."},
    "sep.export_folder": {"fr": "Dossier d'exportation", "en": "Export Folder", "de": "Exportordner", "es": "Carpeta de exportación"},
    "sep.files_created": {"fr": "Fichiers créés :", "en": "Files created:", "de": "Erstellte Dateien:", "es": "Archivos creados:"},
    "sep.pdf_too_large": {
        "fr": "Le PDF n'a pas été créé : la plaque ne tient pas sur une feuille A4.",
        "en": "The PDF was not created: the plate does not fit on an A4 sheet.",
        "de": "Das PDF wurde nicht erstellt: Die Platte passt nicht auf ein A4-Blatt.",
        "es": "No se creó el PDF: la placa no cabe en una hoja A4.",
    },
    "sep.export_complete": {
        "fr": "Exportation terminée", 
        "en": "Export Complete", 
        "de": "Export abgeschlossen", 
        "es": "Exportación terminada",
    },
    "sep.load_image_btn": {
        "fr": "📂 Charger une image", 
        "en": "📂 Load Image", 
        "de": "📂 Bild laden", 
        "es": "📂 Cargar imagen",
    },
    "sep.drag_drop_hint": {
        "fr": "💡 Glisse-dépose une image ici",
        "en": "💡 Drag & drop an image here", 
        "de": "💡 Bild hierher ziehen", 
        "es": "💡 Arrastra y suelta una imagen aquí",
    },
    # --- Séparation Couleur : clés ajoutées pour la version PyQt (à coller avant le "}" final de TRANSLATIONS) ---
    "sep.black_info": {
        "fr": "Luminosité, contraste, gamma, tramage, négatif, miroir et résolution (spot laser) se règlent à gauche de l'onglet « Graver une image ».",
        "en": "Brightness, contrast, gamma, dithering, negative, mirror and resolution (laser spot) are set on the left of the \"Engrave an Image\" tab.",
        "de": "Helligkeit, Kontrast, Gamma, Rasterung, Negativ, Spiegelung und Auflösung (Laser-Spot) werden links im Tab „Bild gravieren“ eingestellt.",
        "es": "El brillo, contraste, gamma, tramado, negativo, espejo y resolución (punto láser) se ajustan a la izquierda de la pestaña «Grabar una imagen».",
    },
    "sep.engrave_dpi": {
        "fr": "Résolution de gravure : {dpi} DPI (réglée dans l'onglet « Graver une image »)",
        "en": "Engraving resolution: {dpi} DPI (set in the \"Engrave an Image\" tab)",
        "de": "Gravurauflösung: {dpi} DPI (im Tab „Bild gravieren“ eingestellt)",
        "es": "Resolución de grabado: {dpi} DPI (ajustada en la pestaña «Grabar una imagen»)",
    },
    "sep.gain": {
        "fr": "Gain de point (%):", "en": "Dot gain (%):",
        "de": "Punktzuwachs (%):", "es": "Ganancia de punto (%):",
    },
    "sep.gain_tip": {
        "fr": "Augmente si les tons moyens sortent trop clairs après gravure (points brûlés qui débordent). 0 = aucune correction.",
        "en": "Increase if midtones come out too light after engraving (burned dots spreading). 0 = no correction.",
        "de": "Erhöhen, wenn die Mitteltöne nach dem Gravieren zu hell werden (verbrannte Punkte laufen aus). 0 = keine Korrektur.",
        "es": "Aumenta si los tonos medios salen demasiado claros tras el grabado (los puntos quemados se expanden). 0 = sin corrección.",
    },
    "sep.mirror_print_tip": {
        "fr": "Coche si le film est collé avec l'encre vers l'extérieur (image vue à travers le film).",
        "en": "Tick if the film is glued with the ink facing away from the glass (image seen through the film).",
        "de": "Aktivieren, wenn die Folie mit der Tintenseite vom Glas abgewandt aufgeklebt wird (Bild wird durch die Folie betrachtet).",
        "es": "Marca si la película se pega con la tinta hacia fuera del vidrio (imagen vista a través de la película).",
    },
    "sep.sync_note": {
        "fr": "Les dimensions de la plaque sont reportées dans la taille de l'image (onglet « Graver une image ») : les calques noir et couleur ont ainsi exactement la même taille.",
        "en": "The plate size is copied to the image size (\"Engrave an Image\" tab), so the black and colour layers have exactly the same size.",
        "de": "Die Plattengröße wird in die Bildgröße übernommen (Tab „Bild gravieren“), damit schwarze und Farbebene exakt gleich groß sind.",
        "es": "Las dimensiones de la placa se copian al tamaño de la imagen (pestaña «Grabar una imagen»), así las capas negra y de color tienen exactamente el mismo tamaño.",
    },
    "sep.not_ready": {
        "fr": "Le calque noir est en cours de calcul, réessaie dans un instant.",
        "en": "The black layer is still being computed, try again in a moment.",
        "de": "Die schwarze Ebene wird noch berechnet, versuche es gleich noch einmal.",
        "es": "La capa negra aún se está calculando, inténtalo de nuevo en un momento.",
    },
    "sep.tip": {
        "fr": "Astuce : imprime le PDF à 100 % (sans mise à l'échelle) sur film transparent imprimable, puis colle-le à l'arrière du verre en alignant soigneusement avec la gravure.",
        "en": "Tip: print the PDF at 100 % (no scaling) on printable transparent film, then glue it to the back of the glass, aligning it carefully with the engraving.",
        "de": "Tipp: Drucke das PDF zu 100 % (ohne Skalierung) auf bedruckbare Klarsichtfolie und klebe es sorgfältig ausgerichtet auf die Rückseite des Glases.",
        "es": "Consejo: imprime el PDF al 100 % (sin escalar) en película transparente imprimible y pégalo en la parte trasera del vidrio, alineándolo con cuidado con el grabado.",
    },
    # --- Séparation Couleur : proportions et recadrage (à coller avant le "}" final de TRANSLATIONS) ---
    "sep.keep_ratio": {
        "fr": "Garder les proportions de l'image",
        "en": "Keep the image proportions",
        "de": "Bildproportionen beibehalten",
        "es": "Mantener las proporciones de la imagen",
    },
    "sep.crop_title": {
        "fr": "Recadrage de l'image",
        "en": "Image crop",
        "de": "Bildausschnitt",
        "es": "Recorte de la imagen",
    },
    "sep.crop_hint": {
        "fr": "Actif quand les proportions ne sont pas conservées et que le cadrage est « Recadrer ». Le cadre rouge de l'onglet Original montre la zone gravée.",
        "en": "Active when proportions are not kept and framing is set to crop. The red frame in the Original tab shows the engraved area.",
        "de": "Aktiv, wenn die Proportionen nicht beibehalten werden und der Ausschnitt auf Zuschneiden steht. Der rote Rahmen im Tab Original zeigt den gravierten Bereich.",
        "es": "Activo cuando no se mantienen las proporciones y el encuadre está en recortar. El marco rojo de la pestaña Original muestra la zona grabada.",
    },
    "sep.crop_zoom": {
        "fr": "Zoom du recadrage:", "en": "Crop zoom:",
        "de": "Zoom des Ausschnitts:", "es": "Zoom del recorte:",
    },
    "sep.crop_x": {
        "fr": "Position horizontale:", "en": "Horizontal position:",
        "de": "Horizontale Position:", "es": "Posición horizontal:",
    },
    "sep.crop_y": {
        "fr": "Position verticale:", "en": "Vertical position:",
        "de": "Vertikale Position:", "es": "Posición vertical:",
    },
    "sep.crop_reset": {
        "fr": "Réinitialiser le recadrage", "en": "Reset crop",
        "de": "Ausschnitt zurücksetzen", "es": "Restablecer recorte",
    },
}
