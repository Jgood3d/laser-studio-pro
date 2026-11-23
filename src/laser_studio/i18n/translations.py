"""Textes de l'interface, dans chaque langue (dictionnaire TRANSLATIONS).

Pour ajouter un texte : une clé, et sa traduction dans chaque langue de
SUPPORTED_LANGUAGES (le français au minimum).

Note sur la qualité des traductions : le français et l'anglais sont
soigneusement relus. L'allemand et l'espagnol sont une première passe
raisonnable mais n'ont pas été relus par une personne native — une
relecture est bienvenue avant de les considérer définitifs.
"""

SUPPORTED_LANGUAGES = {"fr": "Français", "en": "English", "de": "Deutsch", "es": "Español"}
DEFAULT_LANGUAGE = "fr"

# Clé -> { code_langue: texte }. Une clé absente ou une langue manquante
# retombe automatiquement sur le français, puis sur la clé elle-même :
# jamais de plantage ni de texte vide à cause d'une traduction manquante.
TRANSLATIONS = {
    # --- Menu Fichier ---
    "menu.file": {"fr": "Fichier", "en": "File", "de": "Datei", "es": "Archivo"},
    "menu.file.save_project": {
        "fr": "Enregistrer le projet", "en": "Save Project",
        "de": "Projekt speichern", "es": "Guardar proyecto",
    },
    "menu.file.open_project": {
        "fr": "Ouvrir un projet", "en": "Open Project",
        "de": "Projekt öffnen", "es": "Abrir proyecto",
    },
    "menu.file.recent_projects": {
        "fr": "Projets récents", "en": "Recent Projects",
        "de": "Zuletzt verwendete Projekte", "es": "Proyectos recientes",
    },
    "menu.file.quit": {"fr": "Quitter", "en": "Quit", "de": "Beenden", "es": "Salir"},
    "menu.file.save_gcode": {
        "fr": "Enregistrer le G-Code", "en": "Save G-Code",
        "de": "G-Code speichern", "es": "Guardar G-Code",
    },

    # --- Menu Affichage ---
    "menu.view": {"fr": "Affichage", "en": "View", "de": "Ansicht", "es": "Ver"},
    "menu.view.job_queue": {
        "fr": "Afficher/Masquer la file d'attente",
        "en": "Show/Hide the job queue",
        "de": "Warteschlange ein-/ausblenden",
        "es": "Mostrar/Ocultar la cola de trabajos",
    },
    "menu.view.gcode_console": {
        "fr": "Afficher/Masquer la console G-Code",
        "en": "Show/Hide the G-Code console",
        "de": "G-Code-Konsole ein-/ausblenden",
        "es": "Mostrar/Ocultar la consola G-Code",
    },

    # --- Menus Paramètres et Outils ---
    "menu.settings": {"fr": "Paramètres", "en": "Settings", "de": "Einstellungen", "es": "Ajustes"},
    "menu.tools": {"fr": "Outils", "en": "Tools", "de": "Werkzeuge", "es": "Herramientas"},
    # --- Import des exports de Stencil Studio (controllers/stencil_import.py) ---
    "stencil.imported": {
        "fr": "Stencil Studio : « {name} » importé.", "en": "Stencil Studio: “{name}” imported.",
        "de": "Stencil Studio: „{name}“ importiert.", "es": "Stencil Studio: «{name}» importado.",
    },
    "stencil.imported_detail": {
        "fr": "Stencil Studio : {detail} importés depuis « {name} ».",
        "en": "Stencil Studio: {detail} imported from “{name}”.",
        "de": "Stencil Studio: {detail} aus „{name}“ importiert.",
        "es": "Stencil Studio: {detail} importados desde «{name}».",
    },
    "stencil.count_cut": {"fr": "découpe {n}", "en": "cut {n}", "de": "Schnitt {n}", "es": "corte {n}"},
    "stencil.count_mark": {"fr": "cadrage {n}", "en": "frame {n}", "de": "Rahmen {n}", "es": "marco {n}"},
    "stencil.count_engrave": {"fr": "gravure {n}", "en": "engraving {n}", "de": "Gravur {n}", "es": "grabado {n}"},
    "stencil.count_multi": {"fr": "plaques {n}", "en": "plates {n}", "de": "Platten {n}", "es": "placas {n}"},
    "stencil.objects": {"fr": "objets", "en": "objects", "de": "Objekte", "es": "objetos"},
    "stencil.missing_layers": {
        "fr": " — Attention : aucun calque {modes} (objets sur le calque par défaut).",
        "en": " — Warning: no {modes} layer (objects put on the default layer).",
        "de": " — Achtung: keine Ebene {modes} (Objekte auf der Standardebene).",
        "es": " — Atención: ninguna capa {modes} (objetos en la capa predeterminada).",
    },
    "stencil.created_layers": {
        "fr": " Calques créés : {names}.", "en": " Layers created: {names}.",
        "de": " Erstellte Ebenen: {names}.", "es": " Capas creadas: {names}.",
    },
    "stencil.import_fallback": {
        "fr": "Stencil Studio : import impossible ({error}), import standard à la place.",
        "en": "Stencil Studio: import failed ({error}), using the standard import instead.",
        "de": "Stencil Studio: Import fehlgeschlagen ({error}), stattdessen Standardimport.",
        "es": "Stencil Studio: importación imposible ({error}), se usa la importación estándar.",
    },
    "menu.tools.stencil_studio": {"fr": "Stencil Studio", "en": "Stencil Studio",
                                  "de": "Stencil Studio", "es": "Stencil Studio"},
    "menu.tools.import_vector": {
        "fr": "Importer SVG / DXF…",
        "en": "Import SVG / DXF…",
        "de": "SVG / DXF importieren…",
        "es": "Importar SVG / DXF…",
    },
    "menu.tools.box": {
        "fr": "Générateur de boîte…",
        "en": "Box Generator…",
        "de": "Box-Generator…",
        "es": "Generador de cajas…",
    },
    "ui.close_tab": {
        "fr": "Fermer l'onglet",
        "en": "Close tab",
        "de": "Tab schließen",
        "es": "Cerrar pestaña",
    },
    "ui.connection_box": {
        "fr": "Connexion",
        "en": "Connection",
        "de": "Verbindung",
        "es": "Conexión",
    },
    "menu.tools.puzzle": {
        "fr": "Générateur de Puzzle…",
        "en": "Puzzle Generator…",
        "de": "Puzzle-Generator…",
        "es": "Generador de puzzle…",
    },

    "menu.theme": {
        "fr": "Thème de l'interface",
        "en": "Interface theme",
        "de": "Oberflächenthema",
        "es": "Tema de la interfaz",
    },
    "theme.dark": {
        "fr": "Sombre",
        "en": "Dark",
        "de": "Dunkel",
        "es": "Oscuro",
    },
    "theme.light": {
        "fr": "Clair",
        "en": "Light",
        "de": "Hell",
        "es": "Claro",
    },
    "theme.dusk": {
        "fr": "Dusk (gris-bleu doux)",
        "en": "Dusk (soft blue-gray)",
        "de": "Dusk (weiches Blaugrau)",
        "es": "Dusk (gris azulado suave)",
    },
    "theme.warm": {
        "fr": "Warm dim (gris chaud)",
        "en": "Warm dim (warm gray)",
        "de": "Warm dim (warmes Grau)",
        "es": "Warm dim (gris cálido)",
    },
    "theme.neon": {
        "fr": "Neon laser",
        "en": "Neon laser",
        "de": "Neon-Laser",
        "es": "Neón láser",
    },
    "theme.retro80": {
        "fr": "Rétro 80 (synthwave)",
        "en": "Retro 80s (synthwave)",
        "de": "Retro 80er (Synthwave)",
        "es": "Retro 80 (synthwave)",
    },
    "theme.jarvis": {
        "fr": "Jarvis (HUD cyan)",
        "en": "Jarvis (cyan HUD)",
        "de": "Jarvis (Cyan-HUD)",
        "es": "Jarvis (HUD cian)",
    },


    "toolbar.main": {"fr": "Barre d'outils", "en": "Toolbar", "de": "Werkzeugleiste", "es": "Barra de herramientas"},

    # --- Menu Langue ---
    "menu.language": {"fr": "Langue", "en": "Language", "de": "Sprache", "es": "Idioma"},
    "menu.language.restart_title": {
        "fr": "Redémarrage nécessaire", "en": "Restart required",
        "de": "Neustart erforderlich", "es": "Reinicio necesario",
    },
    "menu.language.restart_body": {
        "fr": "La langue a été changée. Redémarre l'application pour que ce "
              "changement soit appliqué à l'ensemble de l'interface.",
        "en": "The language has been changed. Restart the application for "
              "this change to apply to the whole interface.",
        "de": "Die Sprache wurde geändert. Starte die Anwendung neu, damit "
              "diese Änderung auf die gesamte Oberfläche angewendet wird.",
        "es": "Se ha cambiado el idioma. Reinicia la aplicación para que "
              "este cambio se aplique a toda la interfaz.",
    },

    # --- Menu Aide ---
    "menu.help": {"fr": "Aide", "en": "Help", "de": "Hilfe", "es": "Ayuda"},
    "menu.help.version": {"fr": "Version", "en": "Version", "de": "Version", "es": "Versión"},
    "menu.help.documentation": {"fr": "Documentation", "en": "Documentation",
                                 "de": "Dokumentation", "es": "Documentación"},
    "help.title": {"fr": "Documentation de Laser Studio Pro",
                   "en": "Laser Studio Pro documentation",
                   "de": "Laser Studio Pro Dokumentation",
                   "es": "Documentación de Laser Studio Pro"},
    "help.back": {"fr": "Précédent", "en": "Back", "de": "Zurück", "es": "Atrás"},
    "help.forward": {"fr": "Suivant", "en": "Forward", "de": "Vor", "es": "Adelante"},
    "help.home": {"fr": "Sommaire", "en": "Contents", "de": "Inhalt", "es": "Índice"},
    "help.not_found": {"fr": "Documentation introuvable (dossier resources/doc/ absent).",
                       "en": "Documentation not found (resources/doc/ folder missing).",
                       "de": "Dokumentation nicht gefunden (Ordner resources/doc/ fehlt).",
                       "es": "Documentación no encontrada (falta la carpeta resources/doc/)."},
    "menu.help.about": {"fr": "À propos", "en": "About", "de": "Über", "es": "Acerca de"},
    "menu.help.support": {"fr": "Support", "en": "Support", "de": "Support", "es": "Soporte"},
    "menu.help.coffee": {"fr": "Buy me a coffee", "en": "Buy me a coffee",
                          "de": "Buy me a coffee", "es": "Buy me a coffee"},

    # --- Onglets du panneau de réglages ---
    "tab.machine_params": {
        "fr": "Paramètres du graveur", "en": "Engraver Settings",
        "de": "Gravierer-Einstellungen", "es": "Ajustes del grabador",
    },
    "tab.test_matrix": {
        "fr": "Matrice de Test", "en": "Test Matrix",
        "de": "Testmatrix", "es": "Matriz de prueba",
    },
    "tab.grbl_config": {
        "fr": "Configuration GRBL", "en": "GRBL Configuration",
        "de": "GRBL-Konfiguration", "es": "Configuración GRBL",
    },
    "tab.layers": {
        "fr": "Calques (Layers)", "en": "Layers",
        "de": "Ebenen (Layers)", "es": "Capas (Layers)",
    },

    # --- Onglet Paramètres Machine ---
    "mach.profiles_box": {
        "fr": "Profils de Machine", "en": "Machine Profiles",
        "de": "Maschinenprofile", "es": "Perfiles de máquina",
    },
    "mach.new_machine": {
        "fr": "+ Nouvelle Machine", "en": "+ New Machine",
        "de": "+ Neue Maschine", "es": "+ Nueva máquina",
    },
    "mach.update": {"fr": "Mettre à jour", "en": "Update", "de": "Aktualisieren", "es": "Actualizar"},
    "mach.delete": {"fr": "Supprimer", "en": "Delete", "de": "Löschen", "es": "Eliminar"},
    "mach.profile_info": {
        "fr": "Choisis une machine dans la liste pour charger ses dimensions, ou\n"
              "crée-en une nouvelle à partir des dimensions actuelles ci-dessous.",
        "en": "Choose a machine from the list to load its dimensions, or\n"
              "create a new one from the current dimensions below.",
        "de": "Wähle eine Maschine aus der Liste, um ihre Abmessungen zu laden,\n"
              "oder erstelle eine neue aus den aktuellen Abmessungen unten.",
        "es": "Elige una máquina de la lista para cargar sus dimensiones, o\n"
              "crea una nueva a partir de las dimensiones actuales de abajo.",
    },
    "mach.bed_box": {
        "fr": "Dimensions du Graveur (Zone de Travail Physique)",
        "en": "Engraver Dimensions (Physical Work Area)",
        "de": "Abmessungen des Gravierers (Physischer Arbeitsbereich)",
        "es": "Dimensiones del grabador (Área de trabajo física)",
    },
    "mach.bed_w": {
        "fr": "Largeur du lit (X) :", "en": "Bed Width (X):",
        "de": "Bettbreite (X):", "es": "Ancho de la mesa (X):",
    },
    "mach.bed_h": {
        "fr": "Profondeur du lit (Y) :", "en": "Bed Depth (Y):",
        "de": "Betttiefe (Y):", "es": "Profundidad de la mesa (Y):",
    },
    "mach.bed_info": {
        "fr": "Ces dimensions décrivent la surface physique maximale de ta machine.\n"
              "Elles définissent la zone visible dans l'Éditeur Vectoriel (quadrillage)\n"
              "et servent de repère — elles sont indépendantes des dimensions du job\n"
              "en cours (onglet 'Dimensions & Origine', qui peut être plus petit).",
        "en": "These dimensions describe the maximum physical surface of your machine.\n"
              "They define the visible area in the Vector Editor (grid) and act as a\n"
              "reference — they are independent from the current job's dimensions\n"
              "(the 'Dimensions & Origin' tab, which can be smaller).",
        "de": "Diese Abmessungen beschreiben die maximale physische Fläche deiner\n"
              "Maschine. Sie legen den sichtbaren Bereich im Vektor-Editor (Raster)\n"
              "fest und dienen als Referenz — sie sind unabhängig von den Abmessungen\n"
              "des aktuellen Jobs (Reiter 'Abmessungen & Ursprung', der kleiner sein kann).",
        "es": "Estas dimensiones describen la superficie física máxima de tu máquina.\n"
              "Definen el área visible en el Editor Vectorial (cuadrícula) y sirven de\n"
              "referencia — son independientes de las dimensiones del trabajo actual\n"
              "(pestaña 'Dimensiones y Origen', que puede ser más pequeño).",
    },
    "mach.laser_box": {
        "fr": "Caractéristiques du Laser", "en": "Laser Characteristics",
        "de": "Lasereigenschaften", "es": "Características del láser",
    },
    "mach.focal_size": {
        "fr": "Taille du spot (focale) :", "en": "Spot Size (focal):",
        "de": "Spotgröße (Fokus):", "es": "Tamaño del punto (focal):",
    },
    "mach.focal_help": {
        "fr": "Diamètre du point focal de ton laser (ex: 0.06 mm pour un module\n"
              "type Phecda). Utilisé dans les réglages de l'onglet « Graver une image »\n"
              "pour proposer un intervalle de lignes calé sur cette taille de spot.",
        "en": "Diameter of your laser's focal point (e.g. 0.06 mm for a Phecda-type\n"
              "module). Used in the settings of the \"Engrave an Image\" tab to suggest\n"
              "a line interval matched to this spot size.",
        "de": "Durchmesser des Laser-Brennpunkts (z. B. 0,06 mm bei einem Phecda-Modul).\n"
              "Wird in den Einstellungen des Tabs „Bild gravieren“ genutzt, um einen\n"
              "zu dieser Spotgröße passenden Zeilenabstand vorzuschlagen.",
        "es": "Diámetro del punto focal de tu láser (ej.: 0,06 mm para un módulo tipo\n"
              "Phecda). Se usa en los ajustes de la pestaña «Grabar una imagen» para\n"
              "proponer un intervalo de líneas ajustado a ese tamaño de punto.",
    },
    "mach.limits_box": {
        "fr": "Limites de la Machine (informatif)", "en": "Machine Limits (informational)",
        "de": "Maschinengrenzen (informativ)", "es": "Límites de la máquina (informativo)",
    },
    "mach.max_speed": {
        "fr": "Vitesse Max :", "en": "Max Speed:",
        "de": "Max. Geschwindigkeit:", "es": "Velocidad máx.:",
    },
    "mach.accel": {
        "fr": "Accélération :", "en": "Acceleration:",
        "de": "Beschleunigung:", "es": "Aceleración:",
    },
    "mach.limits_info": {
        "fr": "Ces valeurs servent à t'avertir si une vitesse configurée dépasse\n"
              "les capacités de la machine active — elles ne modifient pas les\n"
              "réglages GRBL eux-mêmes ($110/$120 etc.).",
        "en": "These values are used to warn you if a configured speed exceeds\n"
              "the active machine's capabilities — they do not change the GRBL\n"
              "settings themselves ($110/$120 etc.).",
        "de": "Diese Werte dienen dazu, dich zu warnen, wenn eine eingestellte\n"
              "Geschwindigkeit die Fähigkeiten der aktiven Maschine übersteigt —\n"
              "sie ändern nicht die GRBL-Einstellungen selbst ($110/$120 usw.).",
        "es": "Estos valores sirven para avisarte si una velocidad configurada\n"
              "supera las capacidades de la máquina activa — no modifican los\n"
              "ajustes de GRBL en sí ($110/$120, etc.).",
    },

    # --- Onglet Image & Filtres ---
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
    "gen.material_dark": {
        "fr": "fond noir", "en": "dark background",
        "de": "dunkler Untergrund", "es": "fondo negro",
    },
    "gen.material_light": {
        "fr": "fond clair", "en": "light background",
        "de": "heller Untergrund", "es": "fondo claro",
    },
    "gen.negative_on": {
        "fr": "négatif activé", "en": "negative on",
        "de": "Negativ aktiv", "es": "negativo activado",
    },
    "gen.negative_off": {
        "fr": "négatif désactivé", "en": "negative off",
        "de": "Negativ inaktiv", "es": "negativo desactivado",
    },
    "gen.material_summary": {
        "fr": "Matière : {bg} ({negative})", "en": "Material: {bg} ({negative})",
        "de": "Material: {bg} ({negative})", "es": "Material: {bg} ({negative})",
    },
    # --- Boîtes de dialogue de l'éditeur vectoriel / erreurs de sauvegarde ---
    "vector.dlg.resize_title": {
        "fr": "Redimensionner la sélection (groupe)", "en": "Resize selection (group)",
        "de": "Auswahl skalieren (Gruppe)", "es": "Redimensionar la selección (grupo)",
    },
    "vector.dlg.group_size": {
        "fr": "Taille actuelle du groupe : {w:.2f} x {h:.2f} mm", "en": "Current group size: {w:.2f} x {h:.2f} mm",
        "de": "Aktuelle Gruppengröße: {w:.2f} x {h:.2f} mm", "es": "Tamaño actual del grupo: {w:.2f} x {h:.2f} mm",
    },
    "vector.dlg.keep_ratio": {
        "fr": "Conserver le ratio largeur/hauteur", "en": "Keep width/height ratio",
        "de": "Seitenverhältnis beibehalten", "es": "Mantener la proporción ancho/alto",
    },
    "vector.dlg.new_width": {
        "fr": "Nouvelle largeur :", "en": "New width:",
        "de": "Neue Breite:", "es": "Nuevo ancho:",
    },
    "vector.dlg.new_height": {
        "fr": "Nouvelle hauteur :", "en": "New height:",
        "de": "Neue Höhe:", "es": "Nuevo alto:",
    },
    "vector.dlg.text_title_new": {
        "fr": "Texte", "en": "Text",
        "de": "Text", "es": "Texto",
    },
    "vector.dlg.text_title_edit": {
        "fr": "Modifier le texte", "en": "Edit text",
        "de": "Text bearbeiten", "es": "Editar texto",
    },
    "vector.dlg.text_default": {
        "fr": "TEXTE", "en": "TEXT",
        "de": "TEXT", "es": "TEXTO",
    },
    "vector.dlg.text_label": {
        "fr": "Texte :", "en": "Text:",
        "de": "Text:", "es": "Texto:",
    },
    "vector.dlg.font": {
        "fr": "Police :", "en": "Font:",
        "de": "Schriftart:", "es": "Fuente:",
    },
    "vector.dlg.bold": {
        "fr": "Gras", "en": "Bold",
        "de": "Fett", "es": "Negrita",
    },
    "vector.dlg.italic": {
        "fr": "Italique", "en": "Italic",
        "de": "Kursiv", "es": "Cursiva",
    },
    "vector.dlg.style": {
        "fr": "Style :", "en": "Style:",
        "de": "Stil:", "es": "Estilo:",
    },
    "vector.dlg.size_height": {
        "fr": "Taille (hauteur) :", "en": "Size (height):",
        "de": "Größe (Höhe):", "es": "Tamaño (altura):",
    },
    "vector.dlg.letter_spacing": {
        "fr": "Espacement des lettres :", "en": "Letter spacing:",
        "de": "Buchstabenabstand:", "es": "Espaciado entre letras:",
    },
    "vector.dlg.arc_radius": {
        "fr": "Texte sur un cercle, rayon :", "en": "Text on a circle, radius:",
        "de": "Text auf einem Kreis, Radius:", "es": "Texto sobre un círculo, radio:",
    },
    "vector.dlg.arc_off": {
        "fr": "Texte droit", "en": "Straight text",
        "de": "Gerader Text", "es": "Texto recto",
    },
    "vector.dlg.arc_side": {
        "fr": "Côté du cercle :", "en": "Side of the circle:",
        "de": "Seite des Kreises:", "es": "Lado del círculo:",
    },
    "vector.dlg.arc_outside": {
        "fr": "Extérieur (lettres vers l'extérieur)", "en": "Outside (letters pointing out)",
        "de": "Außen (Buchstaben nach außen)", "es": "Exterior (letras hacia fuera)",
    },
    "vector.dlg.arc_inside": {
        "fr": "Intérieur (lettres vers le centre)", "en": "Inside (letters pointing in)",
        "de": "Innen (Buchstaben zur Mitte)", "es": "Interior (letras hacia el centro)",
    },
    "vector.dlg.arc_angle": {
        "fr": "Position sur le cercle (90° = haut, 270° = bas) :",
        "en": "Position on the circle (90° = top, 270° = bottom):",
        "de": "Position auf dem Kreis (90° = oben, 270° = unten):",
        "es": "Posición en el círculo (90° = arriba, 270° = abajo):",
    },
    "vector.dlg.horizontal": {
        "fr": "Horizontal", "en": "Horizontal",
        "de": "Horizontal", "es": "Horizontal",
    },
    "vector.dlg.vertical": {
        "fr": "Vertical", "en": "Vertical",
        "de": "Vertikal", "es": "Vertical",
    },
    "vector.dlg.orientation": {
        "fr": "Orientation :", "en": "Orientation:",
        "de": "Ausrichtung:", "es": "Orientación:",
    },
    "vector.dlg.mirror": {
        "fr": "Miroir :", "en": "Mirror:",
        "de": "Spiegeln:", "es": "Espejo:",
    },
    "vector.dlg.corner_pos": {
        "fr": "Coin bas-gauche de l'objet à (mm) :", "en": "Object's bottom-left corner at (mm):",
        "de": "Untere linke Ecke des Objekts bei (mm):", "es": "Esquina inferior izquierda del objeto en (mm):",
    },
    "vector.dlg.width": {
        "fr": "Largeur :", "en": "Width:",
        "de": "Breite:", "es": "Ancho:",
    },
    "vector.dlg.height": {
        "fr": "Hauteur :", "en": "Height:",
        "de": "Höhe:", "es": "Alto:",
    },
    "vector.dlg.shape_title_new": {
        "fr": "Insérer une forme", "en": "Insert a shape",
        "de": "Form einfügen", "es": "Insertar una forma",
    },
    "vector.dlg.shape_title_edit": {
        "fr": "Modifier la forme", "en": "Edit shape",
        "de": "Form bearbeiten", "es": "Editar forma",
    },
    "vector.dlg.shape_type": {
        "fr": "Type :", "en": "Type:",
        "de": "Typ:", "es": "Tipo:",
    },
    "vector.dlg.sides": {
        "fr": "Côtés (polygone) :", "en": "Sides (polygon):",
        "de": "Seiten (Polygon):", "es": "Lados (polígono):",
    },
    "project.autosave_failed": {
        "fr": "Sauvegarde automatique impossible : {error}", "en": "Automatic save failed: {error}",
        "de": "Automatische Sicherung nicht möglich: {error}", "es": "No se pudo realizar el guardado automático: {error}",
    },
    "queue.save_failed": {
        "fr": "Sauvegarde de la file d'attente impossible : {error}", "en": "Could not save the job queue: {error}",
        "de": "Die Warteschlange konnte nicht gespeichert werden: {error}", "es": "No se pudo guardar la cola de trabajos: {error}",
    },
    # --- Nouvelles options : décalage aller/retour et test du gain de point ---
    "ui.scan_offset_label": {
        "fr": "Décalage lignes retour :",
        "en": "Return-line offset:",
        "de": "Versatz der Rücklauf-Zeilen:",
        "es": "Desplazamiento de líneas de retorno:",
    },
    "ui.scan_offset_tip": {
        "fr": "Décale les lignes gravées en balayage retour (droite → gauche) par rapport à l'aller, pour corriger le jeu mécanique et le délai d'allumage du laser. Positif = vers la droite. Pour trouver la bonne valeur, grave le motif de test et choisis la colonne au bord le plus droit.",
        "en": "Shifts the lines engraved on the return pass (right → left) relative to the forward pass, to compensate for mechanical play and the laser's turn-on delay. Positive = to the right. To find the right value, engrave the test pattern and pick the column with the straightest edge.",
        "de": "Verschiebt die im Rücklauf (rechts → links) gravierten Zeilen gegenüber dem Hinlauf, um mechanisches Spiel und die Einschaltverzögerung des Lasers auszugleichen. Positiv = nach rechts. Um den richtigen Wert zu finden, graviere das Testmuster und wähle die Spalte mit der geradesten Kante.",
        "es": "Desplaza las líneas grabadas en la pasada de retorno (derecha → izquierda) respecto a la de ida, para compensar el juego mecánico y el retardo de encendido del láser. Positivo = hacia la derecha. Para encontrar el valor correcto, graba el patrón de prueba y elige la columna con el borde más recto.",
    },
    "ui.bidir_test_btn": {
        "fr": "Générer le test aller/retour",
        "en": "Generate forward/return test",
        "de": "Hin-/Rücklauf-Test erzeugen",
        "es": "Generar prueba de ida y vuelta",
    },
    "gen.bidir_test_title": {
        "fr": "Test aller/retour",
        "en": "Forward/return test",
        "de": "Hin-/Rücklauf-Test",
        "es": "Prueba de ida y vuelta",
    },
    "gen.bidir_test_body": {
        "fr": "Le motif est prêt (aperçu 2D et console).\n\nGrave-le avec la vitesse et la puissance habituelles. Repère ensuite le numéro de la colonne dont le bord vertical est le plus droit, sans dents de scie : la colonne 9 correspond à 0,00 mm, et chaque colonne décale de 0,05 mm (colonne 1 = -0,40 mm, colonne 17 = +0,40 mm).\n\nSaisis cette valeur dans « Décalage lignes retour ».",
        "en": "The pattern is ready (2D preview and console).\n\nEngrave it with your usual speed and power. Then find the number of the column whose vertical edge is the straightest, without a saw-tooth look: column 9 is 0.00 mm, and each column shifts by 0.05 mm (column 1 = -0.40 mm, column 17 = +0.40 mm).\n\nEnter that value in “Return-line offset”.",
        "de": "Das Muster ist fertig (2D-Vorschau und Konsole).\n\nGraviere es mit deiner üblichen Geschwindigkeit und Leistung. Suche dann die Nummer der Spalte, deren senkrechte Kante am geradesten ist, ohne Sägezahn: Spalte 9 entspricht 0,00 mm, jede Spalte verschiebt um 0,05 mm (Spalte 1 = -0,40 mm, Spalte 17 = +0,40 mm).\n\nTrage diesen Wert bei „Versatz der Rücklauf-Zeilen“ ein.",
        "es": "El patrón está listo (vista previa 2D y consola).\n\nGrábalo con tu velocidad y potencia habituales. Después busca el número de la columna cuyo borde vertical sea el más recto, sin efecto de sierra: la columna 9 equivale a 0,00 mm y cada columna desplaza 0,05 mm (columna 1 = -0,40 mm, columna 17 = +0,40 mm).\n\nIntroduce ese valor en «Desplazamiento de líneas de retorno».",
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
    # --- Import DXF et générateur de boîte ---
    "ui.vector_box_generator": {
        "fr": "📦 Générateur de boîte",
        "en": "📦 Box generator",
        "de": "📦 Box-Generator",
        "es": "📦 Generador de cajas",
    },
    "ui.vector_box_generator_tip": {
        "fr": "Crée une boîte à encoches de dimensions X, Y, Z, avec un décor texte ou SVG sur les faces.",
        "en": "Creates a finger-joint box with the X, Y, Z dimensions you choose, with text or SVG decoration on its faces.",
        "de": "Erstellt eine Fingerzinken-Box mit frei wählbaren Maßen X, Y, Z und Text- oder SVG-Dekor auf den Seiten.",
        "es": "Crea una caja con encastres de dimensiones X, Y, Z, con decoración de texto o SVG en las caras.",
    },
    "ui.vector_puzzle_generator": {
        "fr": "🧩 Puzzle",
        "en": "🧩 Puzzle",
        "de": "🧩 Puzzle",
        "es": "🧩 Puzzle",
    },
    "ui.vector_puzzle_generator_tip": {
        "fr": "Créer une grille de puzzle découpée (tenons / mortaises)",
        "en": "Create a cut jigsaw puzzle grid (tabs / slots)",
        "de": "Ausgeschnittenes Puzzle-Gitter erzeugen (Zapfen / Nuten)",
        "es": "Crear una rejilla de puzzle recortada (lengüetas / ranuras)",
    },
    "vector.import_filter": {
        "fr": "Vectoriel SVG / DXF (*.svg *.dxf);;SVG (*.svg);;DXF (*.dxf)",
        "en": "Vector SVG / DXF (*.svg *.dxf);;SVG (*.svg);;DXF (*.dxf)",
        "de": "Vektor SVG / DXF (*.svg *.dxf);;SVG (*.svg);;DXF (*.dxf)",
        "es": "Vectorial SVG / DXF (*.svg *.dxf);;SVG (*.svg);;DXF (*.dxf)",
    },
    "vector.dxf_title": {
        "fr": "Import DXF",
        "en": "DXF import",
        "de": "DXF-Import",
        "es": "Importación DXF",
    },
    "vector.dxf_err.binary": {
        "fr": "Ce DXF est au format binaire, non pris en charge. Dans ton logiciel de CAO, enregistre-le au format DXF ASCII (texte).",
        "en": "This DXF is in binary format, which is not supported. In your CAD software, save it as ASCII (text) DXF.",
        "de": "Diese DXF-Datei hat das Binärformat, das nicht unterstützt wird. Speichere sie in deiner CAD-Software als ASCII-DXF (Text).",
        "es": "Este DXF está en formato binario, que no es compatible. En tu programa de CAD, guárdalo como DXF ASCII (texto).",
    },
    "vector.dxf_err.not_dxf": {
        "fr": "Ce fichier ne ressemble pas à un DXF texte (problème à la ligne {line}).",
        "en": "This file does not look like a text DXF (problem at line {line}).",
        "de": "Diese Datei sieht nicht wie eine Text-DXF aus (Problem in Zeile {line}).",
        "es": "Este archivo no parece un DXF de texto (problema en la línea {line}).",
    },
    "vector.dxf_err.no_entities": {
        "fr": "Ce DXF ne contient aucune section d'entités (ENTITIES).",
        "en": "This DXF contains no entities section (ENTITIES).",
        "de": "Diese DXF enthält keinen Entitätenabschnitt (ENTITIES).",
        "es": "Este DXF no contiene ninguna sección de entidades (ENTITIES).",
    },
    "vector.dxf_error": {
        "fr": "Impossible de lire le DXF : {error}",
        "en": "Could not read the DXF: {error}",
        "de": "Die DXF-Datei konnte nicht gelesen werden: {error}",
        "es": "No se pudo leer el DXF: {error}",
    },
    "vector.dxf_empty": {
        "fr": "Aucune ligne, courbe ou polyligne exploitable n'a été trouvée dans ce DXF.",
        "en": "No usable line, curve or polyline was found in this DXF.",
        "de": "In dieser DXF wurde keine verwendbare Linie, Kurve oder Polylinie gefunden.",
        "es": "No se encontró ninguna línea, curva o polilínea utilizable en este DXF.",
    },
    "vector.dxf_skipped": {
        "fr": "Éléments non gérés et ignorés : {skipped}.\nAstuce : convertis les textes en courbes dans ton logiciel de CAO avant l'export.",
        "en": "Unsupported elements that were ignored: {skipped}.\nTip: convert text to curves in your CAD software before exporting.",
        "de": "Nicht unterstützte, ignorierte Elemente: {skipped}.\nTipp: Wandle Texte in deiner CAD-Software vor dem Export in Kurven um.",
        "es": "Elementos no compatibles que se ignoraron: {skipped}.\nConsejo: convierte los textos en curvas en tu programa de CAD antes de exportar.",
    },
    "vector.dxf_success": {
        "fr": "{count} objet(s) importé(s) (groupés par calque DXF) dans l'éditeur vectoriel (unité : {unit}), assigné(s) au calque « {layer} ».\nPour séparer les tracés : clic droit → Dégrouper.",
        "en": "{count} object(s) imported (grouped by DXF layer) into the vector editor (unit: {unit}), assigned to layer \"{layer}\".\nTo split paths: right-click → Ungroup.",
        "de": "{count} Objekt(e) importiert (nach DXF-Ebene gruppiert) in den Vektoreditor (Einheit: {unit}), Ebene „{layer}“.\nZum Trennen: Rechtsklick → Gruppierung aufheben.",
        "es": "{count} objeto(s) importado(s) (agrupados por capa DXF) en el editor vectorial (unidad: {unit}), asignado(s) a la capa «{layer}».\nPara separar: clic derecho → Desagrupar.",
    },
    "box.title": {
        "fr": "Générateur de boîte à encoches",
        "en": "Finger-joint box generator",
        "de": "Box-Generator mit Fingerzinken",
        "es": "Generador de cajas con encastres",
    },
    "box.group_dimensions": {
        "fr": "Dimensions et matériau",
        "en": "Dimensions and material",
        "de": "Abmessungen und Material",
        "es": "Dimensiones y material",
    },
    "box.dimensions_are": {
        "fr": "Les dimensions saisies sont :",
        "en": "The entered dimensions are:",
        "de": "Die eingegebenen Maße sind:",
        "es": "Las dimensiones introducidas son:",
    },
    "box.mode_outer": {
        "fr": "extérieures",
        "en": "outer",
        "de": "außen",
        "es": "exteriores",
    },
    "box.mode_inner": {
        "fr": "intérieures",
        "en": "inner",
        "de": "innen",
        "es": "interiores",
    },
    "box.width_x": {
        "fr": "Largeur (X) :",
        "en": "Width (X):",
        "de": "Breite (X):",
        "es": "Ancho (X):",
    },
    "box.depth_y": {
        "fr": "Profondeur (Y) :",
        "en": "Depth (Y):",
        "de": "Tiefe (Y):",
        "es": "Profundidad (Y):",
    },
    "box.height_z": {
        "fr": "Hauteur (Z) :",
        "en": "Height (Z):",
        "de": "Höhe (Z):",
        "es": "Altura (Z):",
    },
    "box.thickness": {
        "fr": "Épaisseur du matériau :",
        "en": "Material thickness:",
        "de": "Materialstärke:",
        "es": "Grosor del material:",
    },
    "box.kerf": {
        "fr": "Compensation du trait (kerf) :",
        "en": "Kerf compensation:",
        "de": "Schnittfugen-Kompensation (Kerf):",
        "es": "Compensación del corte (kerf):",
    },
    "box.kerf_tip": {
        "fr": "Largeur de matière retirée par le laser (souvent 0,1 à 0,2 mm). Les contours sont décalés de la moitié de cette valeur pour que les pièces s'emboîtent sans jeu. Mesure-la sur un essai : trop grande, les assemblages sont serrés ; trop petite, ils sont lâches.",
        "en": "Width of material removed by the laser (often 0.1 to 0.2 mm). Outlines are offset by half this value so that parts fit without play. Measure it on a test piece: too large and the joints are tight; too small and they are loose.",
        "de": "Breite des vom Laser entfernten Materials (oft 0,1 bis 0,2 mm). Die Konturen werden um die Hälfte dieses Werts versetzt, damit die Teile spielfrei passen. Miss sie an einem Test: zu groß, und die Verbindungen sitzen stramm; zu klein, und sie sind locker.",
        "es": "Anchura de material que retira el láser (a menudo 0,1 a 0,2 mm). Los contornos se desplazan la mitad de este valor para que las piezas encajen sin holgura. Mídela con una prueba: si es demasiado grande, los ensambles quedan apretados; si es demasiado pequeña, quedan flojos.",
    },
    "box.finger": {
        "fr": "Largeur des doigts :",
        "en": "Finger width:",
        "de": "Fingerbreite:",
        "es": "Ancho de los dedos:",
    },
    "box.finger_auto": {
        "fr": "Auto (3 × épaisseur)",
        "en": "Auto (3 × thickness)",
        "de": "Auto (3 × Stärke)",
        "es": "Auto (3 × grosor)",
    },
    "box.finger_tip": {
        "fr": "Largeur visée des doigts. Elle est ajustée pour obtenir, sur chaque arête, un nombre impair de doigts de même largeur, jamais inférieure à l'épaisseur du matériau.",
        "en": "Target finger width. It is adjusted so that each edge gets an odd number of equal fingers, never narrower than the material thickness.",
        "de": "Gewünschte Fingerbreite, die so angepasst wird, dass jede Kante eine ungerade Anzahl gleich breiter Finger erhält (nie schmaler als die Materialstärke).",
        "es": "Ancho deseado de los dedos. Se ajusta para que cada arista tenga un número impar de dedos iguales, nunca más estrechos que el grosor del material.",
    },
    "box.lid_type": {
        "fr": "Couvercle :",
        "en": "Lid:",
        "de": "Deckel:",
        "es": "Tapa:",
    },
    "box.lid_none": {
        "fr": "Aucun (boîte ouverte)",
        "en": "None (open box)",
        "de": "Keiner (offene Box)",
        "es": "Ninguna (caja abierta)",
    },
    "box.lid_finger": {
        "fr": "À doigts (dessus assemblé)",
        "en": "Finger joints (top panel)",
        "de": "Mit Fingerzinken (Oberseite)",
        "es": "Con dedos (parte superior ensamblada)",
    },
    "box.lid_lip": {
        "fr": "Posé, avec rebord",
        "en": "Lay-on, with inner lip",
        "de": "Aufgelegt, mit Innenrand",
        "es": "Apoyada, con reborde interior",
    },
    "box.lid_sliding": {
        "fr": "Coulissant",
        "en": "Sliding",
        "de": "Schiebedeckel",
        "es": "Corredera",
    },
    "box.lid_tip": {
        "fr": "À doigts : le dessus s'assemble comme les autres faces.\nPosé : plaque de la taille de la boîte + petit rebord à coller dessous, qui la centre.\nCoulissant : la plaque glisse par l'avant dans une rainure des parois gauche et droite ; la façade est plus basse. Réglable avec le jeu d'ajustement.\nCharnière vivante : la paroi arrière se prolonge par une zone à fentes qui fléchit, puis par le couvercle, d'une seule pièce.\nCharnière à axe : plaques percées empilées autour d'une tige (à fournir), une sur deux collée dans la paroi arrière, les autres dans le couvercle.",
        "en": "Finger joints: the top is assembled like the other faces.\nLay-on: a box-sized plate plus a small lip to glue underneath, which centres it.\nSliding: the plate slides in from the front through a groove in the left and right walls; the front wall is lower. Adjustable with the clearance.\nLiving hinge: the back wall continues into a slitted zone that flexes, then into the lid, all in one piece.\nPinned hinge: drilled plates stacked around a rod (not included), every other one glued into the back wall, the rest into the lid.",
        "de": "Fingerzinken: Die Oberseite wird wie die anderen Seiten verbunden.\nAufgelegt: Platte in Boxgröße plus ein kleiner Innenrand zum Daruntersetzen, der sie zentriert.\nSchiebedeckel: Die Platte gleitet von vorn durch eine Nut in der linken und rechten Wand; die Vorderwand ist niedriger. Einstellbar über das Spiel.\nFilmscharnier: Die Rückwand setzt sich in eine geschlitzte, biegsame Zone und dann in den Deckel fort, alles aus einem Stück.\nAchsscharnier: gelochte Platten, um einen Stab (selbst beschaffen) gestapelt; jede zweite in die Rückwand geklebt, die übrigen in den Deckel.",
        "es": "Con dedos: la parte superior se ensambla como las demás caras.\nApoyada: placa del tamaño de la caja y un pequeño reborde para pegar debajo, que la centra.\nCorredera: la placa se desliza desde delante por una ranura de las paredes izquierda y derecha; la parte frontal es más baja. Se ajusta con la holgura.\nBisagra viva: la pared trasera continúa en una zona con ranuras que se flexiona y luego en la tapa, todo en una pieza.\nBisagra con eje: placas perforadas apiladas alrededor de una varilla (no incluida), una de cada dos pegada en la pared trasera y las demás en la tapa.",
    },
    "box.clearance": {
        "fr": "Jeu d'ajustement",
        "en": "Fit clearance",
        "de": "Passungsspiel",
        "es": "Holgura de ajuste",
    },
    "box.clearance_tip": {
        "fr": "Jeu ajouté aux assemblages libres : rainure et plaque du couvercle, fentes et encoches des cloisons. Les doigts des angles ne sont pas concernés (ils restent serrés ; voir le kerf). 0,1 mm convient à la plupart des matériaux.",
        "en": "Clearance added to the loose joints: lid groove and plate, divider slots and notches. Corner fingers are not affected (they stay tight; see the kerf). 0.1 mm suits most materials.",
        "de": "Spiel für die losen Verbindungen: Deckelnut und -platte, Schlitze und Aussparungen der Trennwände. Die Eckfinger bleiben unberührt (sie sitzen fest; siehe Schnittfuge). 0,1 mm passt für die meisten Materialien.",
        "es": "Holgura añadida a los ensambles libres: ranura y placa de la tapa, ranuras y muescas de los tabiques. Los dedos de las esquinas no se ven afectados (quedan ajustados; véase el kerf). 0,1 mm sirve para la mayoría de materiales.",
    },
    "box.group_dividers": {
        "fr": "Cloisons (compartiments)",
        "en": "Dividers (compartments)",
        "de": "Trennwände (Fächer)",
        "es": "Tabiques (compartimentos)",
    },
    "box.dividers_x": {
        "fr": "Cloisons dans la largeur (X)",
        "en": "Dividers across the width (X)",
        "de": "Trennwände in der Breite (X)",
        "es": "Tabiques a lo ancho (X)",
    },
    "box.dividers_y": {
        "fr": "Cloisons dans la profondeur (Y)",
        "en": "Dividers across the depth (Y)",
        "de": "Trennwände in der Tiefe (Y)",
        "es": "Tabiques a lo largo (Y)",
    },
    "box.dividers_tip": {
        "fr": "Plaques verticales qui partagent l'intérieur en compartiments égaux. Leurs languettes passent dans des fentes découpées dans les parois et le fond ; croisées, elles s'emboîtent à mi-hauteur.",
        "en": "Vertical plates that split the inside into equal compartments. Their tabs go through slots cut in the walls and the bottom; when they cross, they interlock at mid-height.",
        "de": "Senkrechte Platten, die den Innenraum in gleich große Fächer teilen. Ihre Laschen stecken in Schlitzen der Wände und des Bodens; wo sie sich kreuzen, greifen sie auf halber Höhe ineinander.",
        "es": "Placas verticales que dividen el interior en compartimentos iguales. Sus lengüetas pasan por ranuras cortadas en las paredes y el fondo; al cruzarse, encajan a media altura.",
    },
    "box.summary_dividers": {
        "fr": "{count} compartiment(s) de {cw:.1f} x {cd:.1f} mm (intérieur).",
        "en": "{count} compartment(s) of {cw:.1f} x {cd:.1f} mm (inside).",
        "de": "{count} Fach/Fächer von {cw:.1f} x {cd:.1f} mm (innen).",
        "es": "{count} compartimento(s) de {cw:.1f} x {cd:.1f} mm (interior).",
    },
    "box.group_preview": {
        "fr": "Aperçu",
        "en": "Preview",
        "de": "Vorschau",
        "es": "Vista previa",
    },
    "box.preview_footprint": {
        "fr": "Emprise : {fw:.0f} x {fh:.0f} mm",
        "en": "Footprint: {fw:.0f} x {fh:.0f} mm",
        "de": "Fläche: {fw:.0f} x {fh:.0f} mm",
        "es": "Superficie: {fw:.0f} x {fh:.0f} mm",
    },
    "box.panel_lip": {
        "fr": "Rebord",
        "en": "Lip",
        "de": "Innenrand",
        "es": "Reborde",
    },
    "box.panel_divider_x": {
        "fr": "Cloison X{n}",
        "en": "Divider X{n}",
        "de": "Trennwand X{n}",
        "es": "Tabique X{n}",
    },
    "box.panel_divider_y": {
        "fr": "Cloison Y{n}",
        "en": "Divider Y{n}",
        "de": "Trennwand Y{n}",
        "es": "Tabique Y{n}",
    },
    "box.gap": {
        "fr": "Espace entre les pièces :",
        "en": "Spacing between parts:",
        "de": "Abstand zwischen den Teilen:",
        "es": "Separación entre piezas:",
    },
    "box.group_layers": {
        "fr": "Calques",
        "en": "Layers",
        "de": "Ebenen",
        "es": "Capas",
    },
    "box.cut_layer": {
        "fr": "Calque de découpe :",
        "en": "Cut layer:",
        "de": "Schneide-Ebene:",
        "es": "Capa de corte:",
    },
    "box.engrave_layer": {
        "fr": "Calque de gravure (décor) :",
        "en": "Engraving layer (decoration):",
        "de": "Gravur-Ebene (Dekor):",
        "es": "Capa de grabado (decoración):",
    },
    "box.group_decor": {
        "fr": "Décor à graver sur une face",
        "en": "Decoration to engrave on a face",
        "de": "Dekor zum Gravieren auf einer Seite",
        "es": "Decoración para grabar en una cara",
    },
    "box.face_front": {
        "fr": "Avant",
        "en": "Front",
        "de": "Vorderseite",
        "es": "Frente",
    },
    "box.face_back": {
        "fr": "Arrière",
        "en": "Back",
        "de": "Rückseite",
        "es": "Trasera",
    },
    "box.face_left": {
        "fr": "Gauche",
        "en": "Left",
        "de": "Links",
        "es": "Izquierda",
    },
    "box.face_right": {
        "fr": "Droite",
        "en": "Right",
        "de": "Rechts",
        "es": "Derecha",
    },
    "box.face_top": {
        "fr": "Dessus",
        "en": "Top",
        "de": "Oben",
        "es": "Superior",
    },
    "box.face_bottom": {
        "fr": "Dessous",
        "en": "Bottom",
        "de": "Unten",
        "es": "Inferior",
    },
    "box.decor_face": {
        "fr": "Face :",
        "en": "Face:",
        "de": "Seite:",
        "es": "Cara:",
    },
    "box.decor_kind": {
        "fr": "Type :",
        "en": "Type:",
        "de": "Art:",
        "es": "Tipo:",
    },
    "box.decor_text": {
        "fr": "Texte",
        "en": "Text",
        "de": "Text",
        "es": "Texto",
    },
    "box.decor_svg": {
        "fr": "Fichier SVG",
        "en": "SVG file",
        "de": "SVG-Datei",
        "es": "Archivo SVG",
    },
    "box.decor_text_placeholder": {
        "fr": "Le texte à graver",
        "en": "Text to engrave",
        "de": "Zu gravierender Text",
        "es": "Texto a grabar",
    },
    "box.decor_browse": {
        "fr": "Parcourir…",
        "en": "Browse…",
        "de": "Durchsuchen…",
        "es": "Examinar…",
    },
    "box.decor_svg_file": {
        "fr": "Fichier SVG :",
        "en": "SVG file:",
        "de": "SVG-Datei:",
        "es": "Archivo SVG:",
    },
    "box.decor_width": {
        "fr": "Largeur du dessin :",
        "en": "Drawing width:",
        "de": "Breite der Zeichnung:",
        "es": "Ancho del dibujo:",
    },
    "box.decor_width_original": {
        "fr": "Taille d'origine",
        "en": "Original size",
        "de": "Originalgröße",
        "es": "Tamaño original",
    },
    "box.decor_dx": {
        "fr": "Décalage X :",
        "en": "Offset X:",
        "de": "Versatz X:",
        "es": "Desplazamiento X:",
    },
    "box.decor_dy": {
        "fr": "Décalage Y :",
        "en": "Offset Y:",
        "de": "Versatz Y:",
        "es": "Desplazamiento Y:",
    },
    "box.decor_add": {
        "fr": "Ajouter ce décor",
        "en": "Add this decoration",
        "de": "Dekor hinzufügen",
        "es": "Añadir esta decoración",
    },
    "box.decor_remove": {
        "fr": "Retirer le décor sélectionné",
        "en": "Remove selected decoration",
        "de": "Ausgewähltes Dekor entfernen",
        "es": "Quitar la decoración seleccionada",
    },
    "box.svg_filter": {
        "fr": "Vectoriel SVG (*.svg)",
        "en": "SVG Vector (*.svg)",
        "de": "SVG-Vektor (*.svg)",
        "es": "Vectorial SVG (*.svg)",
    },
    "box.summary": {
        "fr": "{n} panneaux, boîte de {w:.1f} x {d:.1f} x {h:.1f} mm (extérieur). Doigts par arête : X {fx}, Y {fy}, Z {fz}. Emprise de la découpe : {fw:.0f} x {fh:.0f} mm.",
        "en": "{n} panels, box of {w:.1f} x {d:.1f} x {h:.1f} mm (outer). Fingers per edge: X {fx}, Y {fy}, Z {fz}. Cutting footprint: {fw:.0f} x {fh:.0f} mm.",
        "de": "{n} Teile, Box von {w:.1f} x {d:.1f} x {h:.1f} mm (außen). Finger pro Kante: X {fx}, Y {fy}, Z {fz}. Schnittfläche: {fw:.0f} x {fh:.0f} mm.",
        "es": "{n} paneles, caja de {w:.1f} x {d:.1f} x {h:.1f} mm (exterior). Dedos por arista: X {fx}, Y {fy}, Z {fz}. Superficie de corte: {fw:.0f} x {fh:.0f} mm.",
    },
    "box.too_big": {
        "fr": "Les pièces dépassent la zone de travail de la machine ({bed_w:.0f} x {bed_h:.0f} mm) : réduis la boîte ou découpe en plusieurs fois.",
        "en": "The parts exceed the machine's work area ({bed_w:.0f} x {bed_h:.0f} mm): make the box smaller or cut it in several runs.",
        "de": "Die Teile überschreiten den Arbeitsbereich der Maschine ({bed_w:.0f} x {bed_h:.0f} mm): Verkleinere die Box oder schneide in mehreren Durchgängen.",
        "es": "Las piezas superan la zona de trabajo de la máquina ({bed_w:.0f} x {bed_h:.0f} mm): reduce la caja o córtala en varias tandas.",
    },
    "box.done": {
        "fr": "{count} panneau(x) créé(s) dans le calque de découpe, {decor} élément(s) de décor dans le calque de gravure. Emprise : {w:.0f} x {h:.0f} mm.\n\nTu peux déplacer chaque pièce, et annuler avec Ctrl+Z.",
        "en": "{count} panel(s) created on the cut layer, {decor} decoration element(s) on the engraving layer. Footprint: {w:.0f} x {h:.0f} mm.\n\nYou can move each part, and undo with Ctrl+Z.",
        "de": "{count} Teil(e) auf der Schneide-Ebene erstellt, {decor} Dekor-Element(e) auf der Gravur-Ebene. Fläche: {w:.0f} x {h:.0f} mm.\n\nDu kannst jedes Teil verschieben und mit Strg+Z rückgängig machen.",
        "es": "{count} panel(es) creado(s) en la capa de corte, {decor} elemento(s) de decoración en la capa de grabado. Superficie: {w:.0f} x {h:.0f} mm.\n\nPuedes mover cada pieza y deshacer con Ctrl+Z.",
    },
    "box.decor_error": {
        "fr": "Décor ignoré : {error}",
        "en": "Decoration skipped: {error}",
        "de": "Dekor übersprungen: {error}",
        "es": "Decoración omitida: {error}",
    },
    "box.err.generic": {
        "fr": "Paramètres de boîte invalides.",
        "en": "Invalid box parameters.",
        "de": "Ungültige Box-Parameter.",
        "es": "Parámetros de caja no válidos.",
    },
    "box.err.thickness": {
        "fr": "L'épaisseur du matériau doit être supérieure à 0.",
        "en": "The material thickness must be greater than 0.",
        "de": "Die Materialstärke muss größer als 0 sein.",
        "es": "El grosor del material debe ser mayor que 0.",
    },
    "box.err.kerf": {
        "fr": "La compensation du trait doit être comprise entre 0 et l'épaisseur du matériau (exclue).",
        "en": "The kerf compensation must be between 0 and the material thickness (excluded).",
        "de": "Die Schnittfugen-Kompensation muss zwischen 0 und der Materialstärke (ausschließlich) liegen.",
        "es": "La compensación del corte debe estar entre 0 y el grosor del material (excluido).",
    },
    "box.err.dimensions_mode": {
        "fr": "Mode de dimensions inconnu.",
        "en": "Unknown dimensions mode.",
        "de": "Unbekannter Maßmodus.",
        "es": "Modo de dimensiones desconocido.",
    },
    "box.err.priority": {
        "fr": "L'ordre de priorité des faces est invalide.",
        "en": "The face priority order is invalid.",
        "de": "Die Prioritätsreihenfolge der Seiten ist ungültig.",
        "es": "El orden de prioridad de las caras no es válido.",
    },
    "box.err.finger_width": {
        "fr": "La largeur des doigts ne peut pas être négative.",
        "en": "The finger width cannot be negative.",
        "de": "Die Fingerbreite darf nicht negativ sein.",
        "es": "El ancho de los dedos no puede ser negativo.",
    },
    "box.err.too_small": {
        "fr": "La dimension {axis} ({value:.1f} mm) est trop petite : il faut au moins {minimum:.1f} mm en extérieur (3 × l'épaisseur du matériau).",
        "en": "The {axis} dimension ({value:.1f} mm) is too small: at least {minimum:.1f} mm outer is required (3 × material thickness).",
        "de": "Das Maß {axis} ({value:.1f} mm) ist zu klein: außen sind mindestens {minimum:.1f} mm nötig (3 × Materialstärke).",
        "es": "La dimensión {axis} ({value:.1f} mm) es demasiado pequeña: se necesitan al menos {minimum:.1f} mm exteriores (3 × grosor del material).",
    },
    "box.err.finger_too_small": {
        "fr": "La largeur des doigts ({value:.1f} mm) doit être au moins égale à l'épaisseur du matériau ({minimum:.1f} mm).",
        "en": "The finger width ({value:.1f} mm) must be at least the material thickness ({minimum:.1f} mm).",
        "de": "Die Fingerbreite ({value:.1f} mm) muss mindestens der Materialstärke ({minimum:.1f} mm) entsprechen.",
        "es": "El ancho de los dedos ({value:.1f} mm) debe ser al menos igual al grosor del material ({minimum:.1f} mm).",
    },
    "box.err.empty_panel": {
        "fr": "Le contour d'un panneau n'a pas pu être calculé avec ces dimensions : modifie légèrement les dimensions ou la largeur des doigts.",
        "en": "The outline of a panel could not be computed with these dimensions: change the dimensions or the finger width slightly.",
        "de": "Die Kontur eines Teils konnte mit diesen Maßen nicht berechnet werden: Ändere die Maße oder die Fingerbreite leicht.",
        "es": "No se pudo calcular el contorno de un panel con estas dimensiones: modifica un poco las dimensiones o el ancho de los dedos.",
    },
    "box.err.pinched_panel": {
        "fr": "Le contour d'un panneau n'a pas pu être calculé avec ces dimensions : modifie légèrement les dimensions ou la largeur des doigts.",
        "en": "The outline of a panel could not be computed with these dimensions: change the dimensions or the finger width slightly.",
        "de": "Die Kontur eines Teils konnte mit diesen Maßen nicht berechnet werden: Ändere die Maße oder die Fingerbreite leicht.",
        "es": "No se pudo calcular el contorno de un panel con estas dimensiones: modifica un poco las dimensiones o el ancho de los dedos.",
    },
    "box.err.open_outline": {
        "fr": "Le contour d'un panneau n'a pas pu être calculé avec ces dimensions : modifie légèrement les dimensions ou la largeur des doigts.",
        "en": "The outline of a panel could not be computed with these dimensions: change the dimensions or the finger width slightly.",
        "de": "Die Kontur eines Teils konnte mit diesen Maßen nicht berechnet werden: Ändere die Maße oder die Fingerbreite leicht.",
        "es": "No se pudo calcular el contorno de un panel con estas dimensiones: modifica un poco las dimensiones o el ancho de los dedos.",
    },
    "box.err.lid_type": {
        "fr": "Type de couvercle inconnu : {value}.",
        "en": "Unknown lid type: {value}.",
        "de": "Unbekannter Deckeltyp: {value}.",
        "es": "Tipo de tapa desconocido: {value}.",
    },
    "box.err.clearance": {
        "fr": "Le jeu d'ajustement ({value:.2f} mm) doit être positif et inférieur à l'épaisseur du matériau.",
        "en": "The fit clearance ({value:.2f} mm) must be positive and smaller than the material thickness.",
        "de": "Das Passungsspiel ({value:.2f} mm) muss positiv und kleiner als die Materialstärke sein.",
        "es": "La holgura de ajuste ({value:.2f} mm) debe ser positiva y menor que el grosor del material.",
    },
    "box.err.dividers": {
        "fr": "Nombre de cloisons invalide ({value}) : entre 0 et {maximum}.",
        "en": "Invalid number of dividers ({value}): between 0 and {maximum}.",
        "de": "Ungültige Anzahl Trennwände ({value}): zwischen 0 und {maximum}.",
        "es": "Número de tabiques no válido ({value}): entre 0 y {maximum}.",
    },
    "box.err.compartment_too_small": {
        "fr": "Les compartiments en {axis} seraient trop étroits ({value:.1f} mm, minimum {minimum:.1f} mm) : réduis le nombre de cloisons ou agrandis la boîte.",
        "en": "The compartments along {axis} would be too narrow ({value:.1f} mm, minimum {minimum:.1f} mm): use fewer dividers or a bigger box.",
        "de": "Die Fächer in {axis} wären zu schmal ({value:.1f} mm, mindestens {minimum:.1f} mm): weniger Trennwände oder eine größere Box wählen.",
        "es": "Los compartimentos en {axis} serían demasiado estrechos ({value:.1f} mm, mínimo {minimum:.1f} mm): usa menos tabiques o una caja más grande.",
    },
    "box.err.dividers_too_low": {
        "fr": "Les cloisons seraient trop basses ({value:.1f} mm, minimum {minimum:.1f} mm) : augmente la hauteur ou choisis un autre couvercle.",
        "en": "The dividers would be too low ({value:.1f} mm, minimum {minimum:.1f} mm): increase the height or choose another lid.",
        "de": "Die Trennwände wären zu niedrig ({value:.1f} mm, mindestens {minimum:.1f} mm): Höhe erhöhen oder einen anderen Deckel wählen.",
        "es": "Los tabiques serían demasiado bajos ({value:.1f} mm, mínimo {minimum:.1f} mm): aumenta la altura o elige otra tapa.",
    },
    "box.err.several_outlines": {
        "fr": "Le contour d'un panneau n'a pas pu être calculé avec ces dimensions : modifie légèrement les dimensions ou la largeur des doigts.",
        "en": "The outline of a panel could not be computed with these dimensions: change the dimensions or the finger width slightly.",
        "de": "Die Kontur eines Teils konnte mit diesen Maßen nicht berechnet werden: Ändere die Maße oder die Fingerbreite leicht.",
        "es": "No se pudo calcular el contorno de un panel con estas dimensiones: modifica un poco las dimensiones o el ancho de los dedos.",
    },
    "box.lid_hinged": {
        "fr": "Charnière vivante",
        "en": "Living hinge",
        "de": "Filmscharnier",
        "es": "Bisagra viva",
    },
    "box.hinge_length": {
        "fr": "Longueur de la charnière",
        "en": "Hinge length",
        "de": "Länge des Scharniers",
        "es": "Longitud de la bisagra",
    },
    "box.hinge_length_tip": {
        "fr": "Longueur de la zone à fentes une fois dépliée. Plus elle est longue, plus le couvercle s'ouvre facilement (et plus il s'écarte de l'arrière). 20 mm convient pour du contreplaqué de 3 mm ; teste sur une chute. Réservé au couvercle à charnière vivante.",
        "en": "Length of the slitted zone when unfolded. The longer it is, the easier the lid opens (and the further it sits from the back). 20 mm suits 3 mm plywood; test on an offcut. Only for the living-hinge lid.",
        "de": "Länge der geschlitzten Zone im flachen Zustand. Je länger, desto leichter öffnet sich der Deckel (und desto weiter steht er von der Rückseite ab). 20 mm passt für 3-mm-Sperrholz; an einem Reststück testen. Nur für den Deckel mit Filmscharnier.",
        "es": "Longitud de la zona con ranuras desplegada. Cuanto más larga, más fácil se abre la tapa (y más se separa de la parte trasera). 20 mm sirve para contrachapado de 3 mm; prueba con un recorte. Solo para la tapa con bisagra viva.",
    },
    "box.err.hinge_length": {
        "fr": "La longueur de charnière ({value:.1f} mm) doit être comprise entre {minimum:.1f} et {maximum:.0f} mm.",
        "en": "The hinge length ({value:.1f} mm) must be between {minimum:.1f} and {maximum:.0f} mm.",
        "de": "Die Scharnierlänge ({value:.1f} mm) muss zwischen {minimum:.1f} und {maximum:.0f} mm liegen.",
        "es": "La longitud de la bisagra ({value:.1f} mm) debe estar entre {minimum:.1f} y {maximum:.0f} mm.",
    },
    "box.err.hinge_too_long": {
        "fr": "Avec cette charnière, le couvercle ne ferait que {value:.1f} mm de profondeur (minimum {minimum:.1f} mm) : raccourcis la charnière ou agrandis la boîte.",
        "en": "With this hinge the lid would only be {value:.1f} mm deep (minimum {minimum:.1f} mm): shorten the hinge or enlarge the box.",
        "de": "Mit diesem Scharnier wäre der Deckel nur {value:.1f} mm tief (mindestens {minimum:.1f} mm): Scharnier kürzen oder Box vergrößern.",
        "es": "Con esta bisagra la tapa tendría solo {value:.1f} mm de fondo (mínimo {minimum:.1f} mm): acorta la bisagra o agranda la caja.",
    },
    "box.lid_pinned": {
        "fr": "Charnière à axe (tige)",
        "en": "Pinned hinge (rod)",
        "de": "Achsscharnier (Stab)",
        "es": "Bisagra con eje (varilla)",
    },
    "box.hinge_count": {
        "fr": "Nombre de charnières",
        "en": "Number of hinges",
        "de": "Anzahl Scharniere",
        "es": "Número de bisagras",
    },
    "box.hinge_plates": {
        "fr": "Plaques par charnière",
        "en": "Plates per hinge",
        "de": "Platten pro Scharnier",
        "es": "Placas por bisagra",
    },
    "box.hinge_plates_tip": {
        "fr": "Toujours impair : la première et la dernière plaque se collent dans la paroi arrière, celles du milieu alternent avec elles dans le couvercle. Plus il y a de plaques, plus la charnière est solide et large. Pour le type « Charnière à axe » uniquement.",
        "en": "Always odd: the first and last plates are glued into the back wall, the ones between alternate with them in the lid. More plates make a stronger, wider hinge. Only for the pinned-hinge lid.",
        "de": "Immer ungerade: Die erste und die letzte Platte werden in die Rückwand geklebt, die dazwischen wechseln sich mit ihnen im Deckel ab. Mehr Platten ergeben ein stabileres, breiteres Scharnier. Nur für den Achsscharnier-Deckel.",
        "es": "Siempre impar: la primera y la última placa se pegan en la pared trasera; las del medio se alternan con ellas en la tapa. Más placas dan una bisagra más fuerte y ancha. Solo para la tapa con bisagra de eje.",
    },
    "box.pin_diameter": {
        "fr": "Diamètre de la tige",
        "en": "Rod diameter",
        "de": "Stabdurchmesser",
        "es": "Diámetro de la varilla",
    },
    "box.pin_diameter_tip": {
        "fr": "Diamètre de la tige qui traverse les plaques (tourillon en bois, tige métallique, trombone…). Le trou ajoute le jeu d'ajustement. Pour le type « Charnière à axe » uniquement.",
        "en": "Diameter of the rod through the plates (wooden dowel, metal rod, paper clip…). The hole adds the fit clearance. Only for the pinned-hinge lid.",
        "de": "Durchmesser des Stabs durch die Platten (Holzdübel, Metallstift, Büroklammer…). Das Loch erhält zusätzlich das Passungsspiel. Nur für den Achsscharnier-Deckel.",
        "es": "Diámetro de la varilla que atraviesa las placas (espiga de madera, varilla metálica, clip…). El agujero añade la holgura de ajuste. Solo para la tapa con bisagra de eje.",
    },
    "box.hinge_style": {
        "fr": "Forme des plaques",
        "en": "Plate shape",
        "de": "Plattenform",
        "es": "Forma de las placas",
    },
    "box.hinge_style_round": {
        "fr": "Rondes",
        "en": "Round",
        "de": "Rund",
        "es": "Redondas",
    },
    "box.hinge_style_butterfly": {
        "fr": "Papillon",
        "en": "Butterfly",
        "de": "Schmetterling",
        "es": "Mariposa",
    },
    "box.hinge_style_tip": {
        "fr": "Contour décoratif des plaques de la charnière à axe : la partie qui dépasse du couvercle et de l'arrière de la boîte. Pour le type « Charnière à axe » uniquement.",
        "en": "Decorative outline of the pinned-hinge plates: the part that sticks out of the lid and the back of the box. Only for the pinned-hinge lid.",
        "de": "Dekorative Kontur der Achsscharnier-Platten: der Teil, der über Deckel und Rückseite hinausragt. Nur für den Achsscharnier-Deckel.",
        "es": "Contorno decorativo de las placas de la bisagra de eje: la parte que sobresale de la tapa y de la parte trasera. Solo para la tapa con bisagra de eje.",
    },
    "box.plate_radius": {
        "fr": "Rayon des plaques",
        "en": "Plate radius",
        "de": "Plattenradius",
        "es": "Radio de las placas",
    },
    "box.plate_auto": {
        "fr": "Automatique",
        "en": "Automatic",
        "de": "Automatisch",
        "es": "Automático",
    },
    "box.plate_radius_tip": {
        "fr": "Rayon des plaques autour de la tige. Automatique = tige + une épaisseur de matériau. Un rayon plus grand donne un papillon plus visible (la paroi arrière et le couvercle sont creusés en conséquence).",
        "en": "Radius of the plates around the rod. Automatic = rod + one material thickness. A larger radius gives a more visible butterfly (the back wall and the lid are cut out accordingly).",
        "de": "Radius der Platten um den Stab. Automatisch = Stab + eine Materialstärke. Ein größerer Radius ergibt einen sichtbareren Schmetterling (Rückwand und Deckel werden entsprechend ausgespart).",
        "es": "Radio de las placas alrededor de la varilla. Automático = varilla + un grosor de material. Un radio mayor da una mariposa más visible (la pared trasera y la tapa se vacían en consecuencia).",
    },
    "box.pin_through": {
        "fr": "Tige traversante",
        "en": "Through rod",
        "de": "Durchgehender Stab",
        "es": "Varilla pasante",
    },
    "box.pin_through_tip": {
        "fr": "La tige passe dans des trous des parois gauche et droite, sur toute la largeur de la boîte : elle ne peut plus sortir et retient les plaques sans colle. Le diamètre de la tige est alors limité à l'épaisseur du matériau.",
        "en": "The rod passes through holes in the left and right walls, across the full width of the box: it can no longer slip out and holds the plates without glue. The rod diameter is then limited to the material thickness.",
        "de": "Der Stab geht durch Löcher in der linken und rechten Wand über die ganze Breite der Box: Er kann nicht mehr herausrutschen und hält die Platten ohne Kleber. Der Stabdurchmesser ist dann auf die Materialstärke begrenzt.",
        "es": "La varilla pasa por agujeros de las paredes izquierda y derecha, a todo lo ancho de la caja: ya no puede salirse y sujeta las placas sin pegamento. El diámetro de la varilla queda limitado al grosor del material.",
    },
    "box.pin_fit": {
        "fr": "Serrage",
        "en": "Press fit",
        "de": "Presspassung",
        "es": "Ajuste a presión",
    },
    "box.pin_fit_tip": {
        "fr": "Interférence (mm, au total) des pieds et des bras des plaques dans leurs encoches, et de la tige dans les parois : les pièces se montent légèrement serrées. 0 = ajustement juste, sans serrage. Pour le type « Charnière à axe » uniquement.",
        "en": "Interference (mm, in total) of the plate feet and arms in their slots, and of the rod in the walls: parts go together slightly tight. 0 = exact fit, no pressing. Only for the pinned-hinge lid.",
        "de": "Übermaß (mm, insgesamt) der Plattenfüße und -arme in ihren Aussparungen und des Stabs in den Wänden: Die Teile sitzen leicht stramm. 0 = genaue Passung ohne Pressung. Nur für den Achsscharnier-Deckel.",
        "es": "Interferencia (mm, en total) de los pies y brazos de las placas en sus ranuras y de la varilla en las paredes: las piezas encajan ligeramente apretadas. 0 = ajuste justo, sin presión. Solo para la tapa con bisagra de eje.",
    },
    "box.handle": {
        "fr": "Encoche d'ouverture",
        "en": "Opening notch",
        "de": "Öffnungskerbe",
        "es": "Muesca de apertura",
    },
    "box.handle_tip": {
        "fr": "Demi-cercle découpé au bord avant du couvercle pour y glisser un doigt. Impossible avec le couvercle à doigts, dont le bord avant est assemblé.",
        "en": "Half-circle cut into the front edge of the lid to slip a finger in. Not possible with the finger-jointed lid, whose front edge is joined.",
        "de": "Halbkreis am vorderen Deckelrand, um einen Finger hineinzustecken. Beim Fingerzinken-Deckel nicht möglich, da dessen Vorderkante verbunden ist.",
        "es": "Semicírculo recortado en el borde delantero de la tapa para meter un dedo. No es posible con la tapa de dedos, cuyo borde delantero está ensamblado.",
    },
    "box.handle_radius": {
        "fr": "Rayon de l'encoche",
        "en": "Notch radius",
        "de": "Kerbenradius",
        "es": "Radio de la muesca",
    },
    "box.summary_pin_through": {
        "fr": "Charnière : 1 tige Ø {d:.1f} mm × {l:.0f} mm (toute la largeur, à fournir).",
        "en": "Hinge: 1 rod Ø {d:.1f} mm × {l:.0f} mm (full width, not included).",
        "de": "Scharnier: 1 Stab Ø {d:.1f} mm × {l:.0f} mm (volle Breite, selbst beschaffen).",
        "es": "Bisagra: 1 varilla Ø {d:.1f} mm × {l:.0f} mm (todo el ancho, no incluida).",
    },
    "box.err.hinge_style": {
        "fr": "Forme de plaque inconnue : {value}.",
        "en": "Unknown plate shape: {value}.",
        "de": "Unbekannte Plattenform: {value}.",
        "es": "Forma de placa desconocida: {value}.",
    },
    "box.err.pin_fit": {
        "fr": "Le serrage ({value:.2f} mm) doit être compris entre 0 et {maximum:.2f} mm.",
        "en": "The press fit ({value:.2f} mm) must be between 0 and {maximum:.2f} mm.",
        "de": "Das Übermaß ({value:.2f} mm) muss zwischen 0 und {maximum:.2f} mm liegen.",
        "es": "El ajuste a presión ({value:.2f} mm) debe estar entre 0 y {maximum:.2f} mm.",
    },
    "box.err.plate_radius": {
        "fr": "Le rayon des plaques ({value:.1f} mm) doit être 0 (automatique) ou compris entre {minimum:.1f} et {maximum:.0f} mm.",
        "en": "The plate radius ({value:.1f} mm) must be 0 (automatic) or between {minimum:.1f} and {maximum:.0f} mm.",
        "de": "Der Plattenradius ({value:.1f} mm) muss 0 (automatisch) sein oder zwischen {minimum:.1f} und {maximum:.0f} mm liegen.",
        "es": "El radio de las placas ({value:.1f} mm) debe ser 0 (automático) o estar entre {minimum:.1f} y {maximum:.0f} mm.",
    },
    "box.err.handle_finger": {
        "fr": "L'encoche d'ouverture est impossible avec le couvercle à doigts (son bord avant est assemblé) : choisis un autre couvercle.",
        "en": "The opening notch is not possible with the finger-jointed lid (its front edge is joined): choose another lid.",
        "de": "Die Öffnungskerbe ist beim Fingerzinken-Deckel nicht möglich (die Vorderkante ist verbunden): anderen Deckel wählen.",
        "es": "La muesca de apertura no es posible con la tapa de dedos (su borde delantero está ensamblado): elige otra tapa.",
    },
    "box.err.handle_radius": {
        "fr": "Le rayon de l'encoche ({value:.1f} mm) doit être compris entre {minimum:.1f} et {maximum:.1f} mm pour cette boîte.",
        "en": "The notch radius ({value:.1f} mm) must be between {minimum:.1f} and {maximum:.1f} mm for this box.",
        "de": "Der Kerbenradius ({value:.1f} mm) muss bei dieser Box zwischen {minimum:.1f} und {maximum:.1f} mm liegen.",
        "es": "El radio de la muesca ({value:.1f} mm) debe estar entre {minimum:.1f} y {maximum:.1f} mm para esta caja.",
    },
    "box.err.handle_no_edge": {
        "fr": "L'encoche ne trouve pas de bord droit où se placer.",
        "en": "The notch can't find a straight edge to sit on.",
        "de": "Die Kerbe findet keine gerade Kante.",
        "es": "La muesca no encuentra un borde recto donde colocarse.",
    },
    "box.err.ear_corner": {
        "fr": "Le coin arrière des parois est introuvable pour y fixer l'oreille de la tige.",
        "en": "The rear corner of the walls could not be found to attach the rod ear.",
        "de": "Die hintere Wandecke für die Stabösen wurde nicht gefunden.",
        "es": "No se encuentra la esquina trasera de las paredes para fijar la oreja de la varilla.",
    },
    "box.motif": {
        "fr": "Graver un motif sur le dessus",
        "en": "Engrave a motif on the lid",
        "de": "Motiv auf den Deckel gravieren",
        "es": "Grabar un motivo en la tapa",
    },
    "box.motif_tip": {
        "fr": "Grave le contour d'un papillon au centre du dessus, assorti aux plaques de la charnière. Il part sur le calque de gravure.",
        "en": "Engraves a butterfly outline at the centre of the lid, matching the hinge plates. It goes on the engraving layer.",
        "de": "Graviert den Umriss eines Schmetterlings in die Mitte des Deckels, passend zu den Scharnierplatten. Er landet auf der Gravurebene.",
        "es": "Graba el contorno de una mariposa en el centro de la tapa, a juego con las placas de la bisagra. Va a la capa de grabado.",
    },
    "box.motif_size": {
        "fr": "Envergure du papillon",
        "en": "Butterfly wingspan",
        "de": "Flügelspannweite",
        "es": "Envergadura de la mariposa",
    },
    "box.index": {
        "fr": "Graver le numéro de chaque pièce",
        "en": "Engrave each part's number",
        "de": "Teilenummer eingravieren",
        "es": "Grabar el número de cada pieza",
    },
    "box.index_tip": {
        "fr": "Grave un numéro sur chaque panneau (à un endroit libre) pour s'y retrouver à l'assemblage. Il part sur le calque de gravure : décoche l'option une fois la boîte maîtrisée.",
        "en": "Engraves a number on each panel (in a free spot) to help assembly. It goes on the engraving layer: untick once you know the box.",
        "de": "Graviert eine Nummer auf jedes Teil (an einer freien Stelle) als Montagehilfe. Sie landet auf der Gravurebene: abwählen, sobald die Box bekannt ist.",
        "es": "Graba un número en cada panel (en un sitio libre) para el montaje. Va a la capa de grabado: desmárcalo cuando ya conozcas la caja.",
    },
    "box.index_size": {
        "fr": "Hauteur des chiffres",
        "en": "Digit height",
        "de": "Ziffernhöhe",
        "es": "Altura de los números",
    },
    "box.magnets": {
        "fr": "Fermeture par aimants",
        "en": "Magnet closure",
        "de": "Magnetverschluss",
        "es": "Cierre con imanes",
    },
    "box.magnets_tip": {
        "fr": "Deux petites plaques à trou par aimant : l'une se colle sous le couvercle, l'autre sur la face intérieure de la façade, juste dessous. Les aimants se collent dans les trous, face à face. Pour les couvercles à charnière vivante et à charnière à axe.",
        "en": "Two small plates with a hole per magnet: one is glued under the lid, the other on the inside of the front wall, just below. The magnets are glued into the holes, facing each other. For the living-hinge and pinned-hinge lids.",
        "de": "Zwei kleine Platten mit Loch pro Magnet: eine wird unter den Deckel geklebt, die andere innen an die Vorderwand, direkt darunter. Die Magnete werden einander gegenüber in die Löcher geklebt. Für Deckel mit Filmscharnier und Achsscharnier.",
        "es": "Dos pequeñas placas con agujero por imán: una se pega bajo la tapa y la otra en la cara interior del frente, justo debajo. Los imanes se pegan en los agujeros, cara a cara. Para las tapas con bisagra viva y con bisagra de eje.",
    },
    "box.magnet_diameter": {
        "fr": "Diamètre des aimants",
        "en": "Magnet diameter",
        "de": "Magnetdurchmesser",
        "es": "Diámetro de los imanes",
    },
    "box.magnet_count": {
        "fr": "Paires d'aimants",
        "en": "Magnet pairs",
        "de": "Magnetpaare",
        "es": "Pares de imanes",
    },
    "box.panel_magnet_lid": {
        "fr": "Aimant {n} (couvercle)",
        "en": "Magnet {n} (lid)",
        "de": "Magnet {n} (Deckel)",
        "es": "Imán {n} (tapa)",
    },
    "box.panel_magnet_wall": {
        "fr": "Aimant {n} (façade)",
        "en": "Magnet {n} (front)",
        "de": "Magnet {n} (Front)",
        "es": "Imán {n} (frente)",
    },
    "box.summary_magnets": {
        "fr": "Aimants : {n} paire(s) Ø {d:.1f} mm (à fournir, à coller).",
        "en": "Magnets: {n} pair(s) Ø {d:.1f} mm (not included, to be glued).",
        "de": "Magnete: {n} Paar(e) Ø {d:.1f} mm (selbst beschaffen, einzukleben).",
        "es": "Imanes: {n} par(es) Ø {d:.1f} mm (no incluidos, para pegar).",
    },
    "box.err.motif_size": {
        "fr": "La largeur du motif ({value:.1f} mm) doit être comprise entre {minimum:.0f} et {maximum:.1f} mm pour ce dessus (il reste à distance de l'encoche et de la charnière).",
        "en": "The motif width ({value:.1f} mm) must be between {minimum:.0f} and {maximum:.1f} mm for this lid (it stays clear of the notch and the hinge).",
        "de": "Die Motivbreite ({value:.1f} mm) muss bei diesem Deckel zwischen {minimum:.0f} und {maximum:.1f} mm liegen (Abstand zu Kerbe und Scharnier).",
        "es": "El ancho del motivo ({value:.1f} mm) debe estar entre {minimum:.0f} y {maximum:.1f} mm para esta tapa (se mantiene lejos de la muesca y la bisagra).",
    },
    "box.err.index_size": {
        "fr": "La hauteur des chiffres ({value:.1f} mm) doit être comprise entre {minimum:.0f} et {maximum:.0f} mm.",
        "en": "The digit height ({value:.1f} mm) must be between {minimum:.0f} and {maximum:.0f} mm.",
        "de": "Die Ziffernhöhe ({value:.1f} mm) muss zwischen {minimum:.0f} und {maximum:.0f} mm liegen.",
        "es": "La altura de los números ({value:.1f} mm) debe estar entre {minimum:.0f} y {maximum:.0f} mm.",
    },
    "box.err.magnet_lid": {
        "fr": "Les aimants ne se posent que sur un couvercle à charnière vivante ou à charnière à axe.",
        "en": "Magnets only fit on a living-hinge or pinned-hinge lid.",
        "de": "Magnete passen nur an Deckel mit Filmscharnier oder Achsscharnier.",
        "es": "Los imanes solo van en tapas con bisagra viva o bisagra de eje.",
    },
    "box.err.magnet_size": {
        "fr": "Aimants : diamètre entre {minimum:.0f} et {maximum:.0f} mm, de 1 à {count} paire(s).",
        "en": "Magnets: diameter between {minimum:.0f} and {maximum:.0f} mm, 1 to {count} pair(s).",
        "de": "Magnete: Durchmesser zwischen {minimum:.0f} und {maximum:.0f} mm, 1 bis {count} Paar(e).",
        "es": "Imanes: diámetro entre {minimum:.0f} y {maximum:.0f} mm, de 1 a {count} par(es).",
    },
    "box.err.magnet_room": {
        "fr": "Les plaques d'aimant ({size:.1f} mm de côté) ne tiennent pas dans l'espace disponible de la façade : réduis le diamètre ou le nombre d'aimants, ou agrandis la boîte.",
        "en": "The magnet plates ({size:.1f} mm square) don't fit in the space along the front: use smaller or fewer magnets, or a bigger box.",
        "de": "Die Magnetplatten ({size:.1f} mm Kantenlänge) passen nicht an die Vorderwand: kleinere oder weniger Magnete wählen oder die Box vergrößern.",
        "es": "Las placas de imán ({size:.1f} mm de lado) no caben a lo largo del frente: usa imanes más pequeños o menos, o una caja más grande.",
    },
    "box.err.magnet_dividers": {
        "fr": "Une cloison croise une plaque d'aimant : change le nombre d'aimants ou de cloisons.",
        "en": "A divider crosses a magnet plate: change the number of magnets or dividers.",
        "de": "Eine Trennwand kreuzt eine Magnetplatte: Anzahl der Magnete oder Trennwände ändern.",
        "es": "Un tabique cruza una placa de imán: cambia el número de imanes o de tabiques.",
    },
    "box.err.magnet_handle": {
        "fr": "Un aimant tombe sous l'encoche d'ouverture : réduis l'encoche, ou choisis 2 paires d'aimants plus écartées.",
        "en": "A magnet sits under the opening notch: make the notch smaller, or use two magnet pairs further apart.",
        "de": "Ein Magnet liegt unter der Öffnungskerbe: Kerbe verkleinern oder zwei weiter auseinanderliegende Magnetpaare wählen.",
        "es": "Un imán queda bajo la muesca de apertura: reduce la muesca o usa dos pares de imanes más separados.",
    },
    "box.group_lid": {
        "fr": "Couvercle et fermeture",
        "en": "Lid and closure",
        "de": "Deckel und Verschluss",
        "es": "Tapa y cierre",
    },
    "box.group_engrave": {
        "fr": "Gravure automatique",
        "en": "Automatic engraving",
        "de": "Automatische Gravur",
        "es": "Grabado automático",
    },
    "box.magnets_hint": {
        "fr": "Aimants : choisis un couvercle à charnière vivante ou à charnière à axe.",
        "en": "Magnets: choose a living-hinge or pinned-hinge lid.",
        "de": "Magnete: Deckel mit Filmscharnier oder Achsscharnier wählen.",
        "es": "Imanes: elige una tapa con bisagra viva o de eje.",
    },
    "box.handle_hint": {
        "fr": "Encoche d'ouverture : impossible avec le couvercle à doigts ou sans couvercle.",
        "en": "Opening notch: not possible with the finger-jointed lid or without a lid.",
        "de": "Öffnungskerbe: nicht möglich beim Fingerzinken-Deckel oder ohne Deckel.",
        "es": "Muesca de apertura: no es posible con la tapa de dedos ni sin tapa.",
    },
    "box.tab_plan": {
        "fr": "Plan",
        "en": "Flat layout",
        "de": "Zuschnitt",
        "es": "Plano",
    },
    "box.explode": {
        "fr": "Éclaté",
        "en": "Exploded",
        "de": "Explosion",
        "es": "Despiece",
    },
    "box.explode_tip": {
        "fr": "Écarte les pièces pour vérifier l'assemblage avant de découper.",
        "en": "Spreads the parts apart to check the assembly before cutting.",
        "de": "Zieht die Teile auseinander, um den Zusammenbau vor dem Schneiden zu prüfen.",
        "es": "Separa las piezas para comprobar el montaje antes de cortar.",
    },
    "box.material": {
        "fr": "Matériau",
        "en": "Material",
        "de": "Material",
        "es": "Material",
    },
    "box.material_plywood": {
        "fr": "Contreplaqué",
        "en": "Plywood",
        "de": "Sperrholz",
        "es": "Contrachapado",
    },
    "box.material_birch": {
        "fr": "Bouleau clair",
        "en": "Light birch",
        "de": "Helle Birke",
        "es": "Abedul claro",
    },
    "box.material_oak": {
        "fr": "Chêne",
        "en": "Oak",
        "de": "Eiche",
        "es": "Roble",
    },
    "box.material_walnut": {
        "fr": "Noyer",
        "en": "Walnut",
        "de": "Nussbaum",
        "es": "Nogal",
    },
    "box.material_mdf": {
        "fr": "MDF",
        "en": "MDF",
        "de": "MDF",
        "es": "MDF",
    },
    "box.material_acrylic_black": {
        "fr": "Acrylique noir",
        "en": "Black acrylic",
        "de": "Acryl schwarz",
        "es": "Acrílico negro",
    },
    "box.material_acrylic_clear": {
        "fr": "Acrylique transparent",
        "en": "Clear acrylic",
        "de": "Acryl transparent",
        "es": "Acrílico transparente",
    },
    "box.export_png": {
        "fr": "Exporter en PNG",
        "en": "Export as PNG",
        "de": "Als PNG exportieren",
        "es": "Exportar como PNG",
    },
    "box.png_filter": {
        "fr": "Image PNG (*.png)",
        "en": "PNG image (*.png)",
        "de": "PNG-Bild (*.png)",
        "es": "Imagen PNG (*.png)",
    },
    "box.motif_shape": {
        "fr": "Motif",
        "en": "Motif",
        "de": "Motiv",
        "es": "Motivo",
    },
    "box.motif_butterfly": {
        "fr": "Papillon",
        "en": "Butterfly",
        "de": "Schmetterling",
        "es": "Mariposa",
    },
    "box.motif_leaf": {
        "fr": "Feuille",
        "en": "Leaf",
        "de": "Blatt",
        "es": "Hoja",
    },
    "box.motif_star": {
        "fr": "Étoile",
        "en": "Star",
        "de": "Stern",
        "es": "Estrella",
    },
    "box.motif_mandala": {
        "fr": "Mandala",
        "en": "Mandala",
        "de": "Mandala",
        "es": "Mandala",
    },
    "box.group_presets": {
        "fr": "Préréglages",
        "en": "Presets",
        "de": "Voreinstellungen",
        "es": "Preajustes",
    },
    "box.preset_name_placeholder": {
        "fr": "Nom du préréglage",
        "en": "Preset name",
        "de": "Name der Voreinstellung",
        "es": "Nombre del preajuste",
    },
    "box.preset_load": {
        "fr": "Charger",
        "en": "Load",
        "de": "Laden",
        "es": "Cargar",
    },
    "box.preset_save": {
        "fr": "Enregistrer",
        "en": "Save",
        "de": "Speichern",
        "es": "Guardar",
    },
    "box.preset_delete": {
        "fr": "Supprimer",
        "en": "Delete",
        "de": "Löschen",
        "es": "Eliminar",
    },
    "box.preset_jewelry": {
        "fr": "Boîte à bijoux",
        "en": "Jewellery box",
        "de": "Schmuckkästchen",
        "es": "Joyero",
    },
    "box.preset_tea": {
        "fr": "Boîte à thé",
        "en": "Tea box",
        "de": "Teebox",
        "es": "Caja de té",
    },
    "box.err.motif_shape": {
        "fr": "Motif inconnu : {value}.",
        "en": "Unknown motif: {value}.",
        "de": "Unbekanntes Motiv: {value}.",
        "es": "Motivo desconocido: {value}.",
    },
    "box.ratios_x": {
        "fr": "Largeurs des compartiments en X",
        "en": "Compartment widths along X",
        "de": "Fachbreiten in X",
        "es": "Anchos de compartimentos en X",
    },
    "box.ratios_y": {
        "fr": "Largeurs des compartiments en Y",
        "en": "Compartment widths along Y",
        "de": "Fachbreiten in Y",
        "es": "Anchos de compartimentos en Y",
    },
    "box.ratios_placeholder": {
        "fr": "égaux (ex. 1:2:1)",
        "en": "equal (e.g. 1:2:1)",
        "de": "gleich (z. B. 1:2:1)",
        "es": "iguales (p. ej. 1:2:1)",
    },
    "box.ratios_tip": {
        "fr": "Proportions des compartiments, séparées par « : » : il en faut une de plus que de cloisons (2 cloisons → 1:2:1). Vide = compartiments égaux.",
        "en": "Compartment proportions separated by “:”, one more than there are dividers (2 dividers → 1:2:1). Empty = equal compartments.",
        "de": "Verhältnisse der Fächer, durch „:“ getrennt, eines mehr als Trennwände (2 Trennwände → 1:2:1). Leer = gleiche Fächer.",
        "es": "Proporciones de los compartimentos separadas por «:», una más que tabiques (2 tabiques → 1:2:1). Vacío = iguales.",
    },
    "box.err.divider_ratios": {
        "fr": "Largeurs des compartiments en {axis} : il faut {count} nombres positifs, par exemple 1:2:1.",
        "en": "Compartment widths along {axis}: {count} positive numbers are needed, for example 1:2:1.",
        "de": "Fachbreiten in {axis}: Es sind {count} positive Zahlen nötig, zum Beispiel 1:2:1.",
        "es": "Anchos de compartimentos en {axis}: hacen falta {count} números positivos, por ejemplo 1:2:1.",
    },
    "box.group_feet": {
        "fr": "Pieds",
        "en": "Feet",
        "de": "Füße",
        "es": "Pies",
    },
    "box.feet": {
        "fr": "Ajouter 4 pieds sous la boîte",
        "en": "Add 4 feet under the box",
        "de": "4 Füße unter die Box setzen",
        "es": "Añadir 4 pies bajo la caja",
    },
    "box.feet_tip": {
        "fr": "Chaque pied est une pile de plaques carrées à coller sous le fond, près des coins.",
        "en": "Each foot is a stack of square plates glued under the floor, near the corners.",
        "de": "Jeder Fuß ist ein Stapel quadratischer Platten, die unter den Boden geklebt werden, nahe den Ecken.",
        "es": "Cada pie es una pila de placas cuadradas que se pega bajo el fondo, cerca de las esquinas.",
    },
    "box.foot_size": {
        "fr": "Côté d'un pied",
        "en": "Foot side",
        "de": "Seitenlänge eines Fußes",
        "es": "Lado de un pie",
    },
    "box.foot_layers": {
        "fr": "Plaques par pied",
        "en": "Plates per foot",
        "de": "Platten pro Fuß",
        "es": "Placas por pie",
    },
    "box.panel_foot": {
        "fr": "Pied {n} (plaque {j})",
        "en": "Foot {n} (plate {j})",
        "de": "Fuß {n} (Platte {j})",
        "es": "Pie {n} (placa {j})",
    },
    "box.err.foot_size": {
        "fr": "Le côté d'un pied ({value:.1f} mm) doit être compris entre {minimum:.0f} et {maximum:.1f} mm pour cette boîte.",
        "en": "The foot side ({value:.1f} mm) must be between {minimum:.0f} and {maximum:.1f} mm for this box.",
        "de": "Die Fußseite ({value:.1f} mm) muss bei dieser Box zwischen {minimum:.0f} und {maximum:.1f} mm liegen.",
        "es": "El lado del pie ({value:.1f} mm) debe estar entre {minimum:.0f} y {maximum:.1f} mm para esta caja.",
    },
    "box.err.foot_layers": {
        "fr": "Le nombre de plaques par pied doit être un entier de {minimum} à {maximum}.",
        "en": "The number of plates per foot must be a whole number from {minimum} to {maximum}.",
        "de": "Die Plattenzahl pro Fuß muss eine ganze Zahl von {minimum} bis {maximum} sein.",
        "es": "El número de placas por pie debe ser un entero de {minimum} a {maximum}.",
    },
    "box.tab_3d": {
        "fr": "3D",
        "en": "3D",
        "de": "3D",
        "es": "3D",
    },
    "box.open_angle": {
        "fr": "Ouverture du couvercle",
        "en": "Lid opening",
        "de": "Deckelöffnung",
        "es": "Apertura de la tapa",
    },
    "box.view3d_hint": {
        "fr": "Glisser : tourner · Molette : zoom · Double-clic : vue de départ",
        "en": "Drag: rotate · Wheel: zoom · Double-click: reset view",
        "de": "Ziehen: drehen · Mausrad: Zoom · Doppelklick: Ausgangsansicht",
        "es": "Arrastrar: girar · Rueda: zoom · Doble clic: vista inicial",
    },
    "box.summary_pin": {
        "fr": "Charnière : {n} tige(s) Ø {d:.1f} mm, longueur {l:.0f} mm minimum (à fournir).",
        "en": "Hinge: {n} rod(s) Ø {d:.1f} mm, at least {l:.0f} mm long (not included).",
        "de": "Scharnier: {n} Stab/Stäbe Ø {d:.1f} mm, mindestens {l:.0f} mm lang (selbst beschaffen).",
        "es": "Bisagra: {n} varilla(s) Ø {d:.1f} mm, de al menos {l:.0f} mm (no incluida).",
    },
    "box.panel_hinge": {
        "fr": "Charnière {n}.{j}",
        "en": "Hinge {n}.{j}",
        "de": "Scharnier {n}.{j}",
        "es": "Bisagra {n}.{j}",
    },
    "box.err.pin_diameter": {
        "fr": "Le diamètre de la tige ({value:.1f} mm) doit être compris entre {minimum:.1f} et {maximum:.0f} mm.",
        "en": "The rod diameter ({value:.1f} mm) must be between {minimum:.1f} and {maximum:.0f} mm.",
        "de": "Der Stabdurchmesser ({value:.1f} mm) muss zwischen {minimum:.1f} und {maximum:.0f} mm liegen.",
        "es": "El diámetro de la varilla ({value:.1f} mm) debe estar entre {minimum:.1f} y {maximum:.0f} mm.",
    },
    "box.err.hinge_count": {
        "fr": "Nombre de charnières invalide ({value}) : entre 1 et {maximum}.",
        "en": "Invalid number of hinges ({value}): between 1 and {maximum}.",
        "de": "Ungültige Anzahl Scharniere ({value}): zwischen 1 und {maximum}.",
        "es": "Número de bisagras no válido ({value}): entre 1 y {maximum}.",
    },
    "box.err.hinge_plates": {
        "fr": "Le nombre de plaques par charnière ({value}) doit être impair, entre 3 et 9.",
        "en": "The number of plates per hinge ({value}) must be odd, between 3 and 9.",
        "de": "Die Anzahl Platten pro Scharnier ({value}) muss ungerade sein, zwischen 3 und 9.",
        "es": "El número de placas por bisagra ({value}) debe ser impar, entre 3 y 9.",
    },
    "box.err.hinges_dont_fit": {
        "fr": "Les charnières ne tiennent pas dans la largeur ({value:.1f} mm, minimum {minimum:.1f} mm) : réduis leur nombre ou le nombre de plaques, ou élargis la boîte.",
        "en": "The hinges don't fit across the width ({value:.1f} mm, minimum {minimum:.1f} mm): use fewer hinges or plates, or a wider box.",
        "de": "Die Scharniere passen nicht in die Breite ({value:.1f} mm, mindestens {minimum:.1f} mm): weniger Scharniere oder Platten wählen oder die Box verbreitern.",
        "es": "Las bisagras no caben a lo ancho ({value:.1f} mm, mínimo {minimum:.1f} mm): usa menos bisagras o placas, o una caja más ancha.",
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
    # --- Ordre de découpe sûr ---
    "ui.safe_cut_order": {
        "fr": "Ordre de découpe sûr (graver avant, intérieur avant extérieur)",
        "en": "Safe cutting order (engrave first, inside before outside)",
        "de": "Sichere Schneidreihenfolge (erst gravieren, innen vor außen)",
        "es": "Orden de corte seguro (grabar primero, interior antes que exterior)",
    },
    "ui.safe_cut_order_tip": {
        "fr": "Les calques de gravure et de marquage passent avant les calques de découpe, et dans un calque de découpe les contours intérieurs (trous, détails) sont coupés avant ceux qui les contiennent : la pièce ne bouge ni ne bascule avant que ses détails soient faits. Décoche pour suivre strictement l'ordre de la liste des calques.",
        "en": "Engraving and marking layers run before cutting layers, and within a cutting layer inner outlines (holes, details) are cut before the outlines containing them: the part does not move or tip over before its details are done. Uncheck to follow the layer list order strictly.",
        "de": "Gravur- und Markierungsebenen laufen vor den Schneideebenen, und innerhalb einer Schneideebene werden innere Konturen (Löcher, Details) vor den umgebenden geschnitten: das Teil verrutscht oder kippt nicht, bevor seine Details fertig sind. Deaktiviere es, um die Ebenenreihenfolge strikt einzuhalten.",
        "es": "Las capas de grabado y marcado se ejecutan antes que las de corte, y dentro de una capa de corte los contornos interiores (agujeros, detalles) se cortan antes que los que los contienen: la pieza no se mueve ni se vuelca antes de terminar sus detalles. Desmarca para seguir estrictamente el orden de la lista de capas.",
    },
    # --- Générateur de Puzzle ---
    "puzzle.title": {
        "fr": "Générateur de Puzzle",
        "en": "Puzzle Generator",
        "de": "Puzzle-Generator",
        "es": "Generador de puzzle",
    },
    "puzzle.error": {
        "fr": "Erreur puzzle",
        "en": "Puzzle error",
        "de": "Puzzle-Fehler",
        "es": "Error de puzzle",
    },
    "puzzle.empty": {
        "fr": "Aucune pièce générée.",
        "en": "No pieces generated.",
        "de": "Keine Teile erzeugt.",
        "es": "No se generaron piezas.",
    },
    "puzzle.done": {
        "fr": "Puzzle {nx}×{ny} — {count} pièces ({w:.1f}×{h:.1f} mm) généré sur le calque de découpe.",
        "en": "Puzzle {nx}×{ny} — {count} pieces ({w:.1f}×{h:.1f} mm) generated on the cut layer.",
        "de": "Puzzle {nx}×{ny} — {count} Teile ({w:.1f}×{h:.1f} mm) auf der Schnittebene erzeugt.",
        "es": "Puzzle {nx}×{ny} — {count} piezas ({w:.1f}×{h:.1f} mm) generado en la capa de corte.",
    },
    "puzzle.err.piece_too_small": {
        "fr": "Pièces trop petites ({side:.1f} mm). Réduis le nombre de colonnes/lignes (minimum ~3 mm par pièce).",
        "en": "Pieces too small ({side:.1f} mm). Reduce columns/rows (about 3 mm minimum per piece).",
        "de": "Teile zu klein ({side:.1f} mm). Weniger Spalten/Zeilen (mind. ca. 3 mm pro Teil).",
        "es": "Piezas demasiado pequeñas ({side:.1f} mm). Reduce columnas/filas (mín. ~3 mm por pieza).",
    },
    "puzzle.err.tab_too_deep": {
        "fr": "Tenons trop profonds (ratio {value:.2f}). Maximum 0,40.",
        "en": "Tabs too deep (ratio {value:.2f}). Maximum 0.40.",
        "de": "Zapfen zu tief (Ratio {value:.2f}). Maximum 0,40.",
        "es": "Lengüetas demasiado profundas (ratio {value:.2f}). Máximo 0,40.",
    },
    "puzzle.err.kerf_too_large": {
        "fr": "Kerf trop grand ({value:.2f} mm) pour des pièces de {side:.1f} mm.",
        "en": "Kerf too large ({value:.2f} mm) for {side:.1f} mm pieces.",
        "de": "Kerf zu groß ({value:.2f} mm) für Teile von {side:.1f} mm.",
        "es": "Kerf demasiado grande ({value:.2f} mm) para piezas de {side:.1f} mm.",
    },
    "puzzle.err.grid": {
        "fr": "Grille invalide ({nx}×{ny}).",
        "en": "Invalid grid ({nx}×{ny}).",
        "de": "Ungültiges Raster ({nx}×{ny}).",
        "es": "Rejilla no válida ({nx}×{ny}).",
    },

    # --- Générateur de boules de Noël ---
    "menu.tools.ornament": {
        "fr": "Boule de Noël…",
        "en": "Christmas ornament…",
        "de": "Weihnachtskugel…",
        "es": "Bola de Navidad…",
    },
    "menu.tools.library": {
        "fr": "Bibliothèque…",
        "en": "Library…",
        "de": "Bibliothek…",
        "es": "Biblioteca…",
    },
    "ui.vector_library": {
        "fr": "Bibliothèque",
        "en": "Library",
        "de": "Bibliothek",
        "es": "Biblioteca",
    },
    "ui.vector_library_tip": {
        "fr": "Bibliothèque de modèles prêts à graver ou découper (trophées, médailles…), à importer dans l'éditeur.",
        "en": "Ready-to-engrave or cut designs (trophies, medals…), to import into the editor.",
        "de": "Fertige Vorlagen zum Gravieren oder Schneiden (Trophäen, Medaillen…), zum Import in den Editor.",
        "es": "Modelos listos para grabar o cortar (trofeos, medallas…), para importar al editor.",
    },
    "library.title": {
        "fr": "Bibliothèque de modèles",
        "en": "Design library",
        "de": "Vorlagenbibliothek",
        "es": "Biblioteca de modelos",
    },
    "library.search": {
        "fr": "Rechercher un modèle…",
        "en": "Search for a design…",
        "de": "Vorlage suchen…",
        "es": "Buscar un modelo…",
    },
    "library.icon_size": {
        "fr": "Taille des aperçus :",
        "en": "Preview size:",
        "de": "Vorschaugröße:",
        "es": "Tamaño de las vistas:",
    },
    "library.all": {
        "fr": "Toutes",
        "en": "All",
        "de": "Alle",
        "es": "Todas",
    },
    "library.count": {
        "fr": "{count} modèle(s)",
        "en": "{count} design(s)",
        "de": "{count} Vorlage(n)",
        "es": "{count} modelo(s)",
    },
    "library.details": {
        "fr": "Détails…",
        "en": "Details…",
        "de": "Details…",
        "es": "Detalles…",
    },
    "library.import": {
        "fr": "Importer",
        "en": "Import",
        "de": "Importieren",
        "es": "Importar",
    },
    "library.import_to_vector": {
        "fr": "Importer dans l'éditeur vectoriel",
        "en": "Import into the vector editor",
        "de": "In den Vektoreditor importieren",
        "es": "Importar al editor vectorial",
    },
    "library.preview_tab": {
        "fr": "Aperçu",
        "en": "Preview",
        "de": "Vorschau",
        "es": "Vista previa",
    },
    "library.photo_tab": {
        "fr": "Photo",
        "en": "Photo",
        "de": "Foto",
        "es": "Foto",
    },
    "library.drawing_tab": {
        "fr": "Fichier SVG",
        "en": "SVG file",
        "de": "SVG-Datei",
        "es": "Archivo SVG",
    },
    "library.size": {
        "fr": "Taille :",
        "en": "Size:",
        "de": "Größe:",
        "es": "Tamaño:",
    },
    "library.size_value": {
        "fr": "{w:.1f} × {h:.1f} mm",
        "en": "{w:.1f} × {h:.1f} mm",
        "de": "{w:.1f} × {h:.1f} mm",
        "es": "{w:.1f} × {h:.1f} mm",
    },
    "library.author": {
        "fr": "Auteur :",
        "en": "Author:",
        "de": "Autor:",
        "es": "Autor:",
    },
    "library.license": {
        "fr": "Licence :",
        "en": "License:",
        "de": "Lizenz:",
        "es": "Licencia:",
    },
    "library.texts": {
        "fr": "Textes",
        "en": "Texts",
        "de": "Texte",
        "es": "Textos",
    },
    "library.text_font": {
        "fr": "Police du texte",
        "en": "Text font",
        "de": "Schriftart des Textes",
        "es": "Fuente del texto",
    },
    "library.text_size": {
        "fr": "Taille de la police, en mm",
        "en": "Font size, in mm",
        "de": "Schriftgröße in mm",
        "es": "Tamaño de la fuente, en mm",
    },
    "library.close": {
        "fr": "Fermer",
        "en": "Close",
        "de": "Schließen",
        "es": "Cerrar",
    },
    "library.empty": {
        "fr": "Aucun modèle dans la bibliothèque.",
        "en": "The library has no designs.",
        "de": "Die Bibliothek enthält keine Vorlagen.",
        "es": "La biblioteca no tiene modelos.",
    },
    "ui.vector_ornament_generator": {
        "fr": "🎄 Boule de Noël",
        "en": "🎄 Ornament",
        "de": "🎄 Weihnachtskugel",
        "es": "🎄 Bola de Navidad",
    },
    "ui.vector_ornament_generator_tip": {
        "fr": "Créer une boule de Noël découpée avec un prénom et des flocons",
        "en": "Create a cut Christmas ornament with a name and snowflakes",
        "de": "Ausgeschnittene Weihnachtskugel mit Namen und Schneeflocken erzeugen",
        "es": "Crear una bola de Navidad recortada con un nombre y copos de nieve",
    },
    "ornament.title": {
        "fr": "Boule de Noël",
        "en": "Christmas ornament",
        "de": "Weihnachtskugel",
        "es": "Bola de Navidad",
    },
    "ornament.error": {
        "fr": "Erreur boule de Noël",
        "en": "Ornament error",
        "de": "Fehler Weihnachtskugel",
        "es": "Error de bola de Navidad",
    },
    "ornament.empty": {
        "fr": "Aucun contour généré.",
        "en": "No outline generated.",
        "de": "Keine Kontur erzeugt.",
        "es": "No se generó ningún contorno.",
    },
    "ornament.done": {
        "fr": "Boule de Noël {w:.1f}×{h:.1f} mm ({count} contours) générée sur le calque de découpe.",
        "en": "Christmas ornament {w:.1f}×{h:.1f} mm ({count} outlines) generated on the cut layer.",
        "de": "Weihnachtskugel {w:.1f}×{h:.1f} mm ({count} Konturen) auf der Schnittebene erzeugt.",
        "es": "Bola de Navidad {w:.1f}×{h:.1f} mm ({count} contornos) generada en la capa de corte.",
    },
    "ornament.name_placeholder": {
        "fr": "Un prénom par ligne = une boule par ligne\n(ex. Emma\nLéa\nNoah)",
        "en": "One name per line = one ornament per line\n(e.g. Emma\nLéa\nNoah)",
        "de": "Ein Name pro Zeile = eine Kugel pro Zeile\n(z.B. Emma\nLéa\nNoah)",
        "es": "Un nombre por línea = una bola por línea\n(ej. Emma\nLéa\nNoah)",
    },
    "ornament.batch_preview": {
        "fr": "{n} boules seront générées au clic sur OK (aperçu : « {name} »).",
        "en": "{n} ornaments will be generated when you click OK (preview: \"{name}\").",
        "de": "{n} Kugeln werden beim Klick auf OK erzeugt (Vorschau: „{name}“).",
        "es": "Se generarán {n} bolas al pulsar Aceptar (vista previa: «{name}»).",
    },
    "ornament.done_batch": {
        "fr": "{n} boules de Noël générées, rangées en grille ({w:.0f}×{h:.0f} mm).",
        "en": "{n} Christmas ornaments generated, laid out in a grid ({w:.0f}×{h:.0f} mm).",
        "de": "{n} Weihnachtskugeln erzeugt, im Raster angeordnet ({w:.0f}×{h:.0f} mm).",
        "es": "{n} bolas de Navidad generadas, dispuestas en cuadrícula ({w:.0f}×{h:.0f} mm).",
    },
    "ornament.batch_failed": {
        "fr": "Non générées (paramètres incompatibles) : {names}",
        "en": "Not generated (incompatible settings): {names}",
        "de": "Nicht erzeugt (inkompatible Einstellungen): {names}",
        "es": "No generadas (parámetros incompatibles): {names}",
    },
    "ornament.batch_nest_ask": {
        "fr": "Lancer l'imbrication automatique maintenant pour optimiser la place sur la feuille ?",
        "en": "Run automatic nesting now to make the best use of the sheet?",
        "de": "Automatische Anordnung jetzt starten, um das Material optimal zu nutzen?",
        "es": "¿Iniciar ahora el anidado automático para aprovechar mejor la plancha?",
    },
    "ornament.sheet_tip": {
        "fr": "Dimensions du matériau : elles décident du nombre de boules par rangée et sont reprises par l'imbrication.",
        "en": "Material size: it sets how many ornaments fit per row and is reused by nesting.",
        "de": "Materialgröße: bestimmt, wie viele Kugeln pro Reihe passen, und wird von der Anordnung übernommen.",
        "es": "Tamaño del material: decide cuántas bolas caben por fila y lo reutiliza el anidado.",
    },
    "ornament.batch_grid": {
        "fr": "Rangement prévu : {cols} colonne(s) × {rows} rangée(s).",
        "en": "Planned layout: {cols} column(s) × {rows} row(s).",
        "de": "Geplantes Raster: {cols} Spalte(n) × {rows} Reihe(n).",
        "es": "Disposición prevista: {cols} columna(s) × {rows} fila(s).",
    },
    "ornament.batch_too_big_preview": {
        "fr": "Attention : les boules ne tiennent pas toutes sur ce matériau.",
        "en": "Warning: the ornaments do not all fit on this material.",
        "de": "Achtung: Nicht alle Kugeln passen auf dieses Material.",
        "es": "Atención: las bolas no caben todas en este material.",
    },
    "ornament.batch_overflow": {
        "fr": "Attention : l'ensemble dépasse le matériau ({w:.0f}×{h:.0f} mm). L'imbrication placera ce qui tient, le reste sera à découper sur une autre feuille.",
        "en": "Warning: the layout exceeds the material ({w:.0f}×{h:.0f} mm). Nesting will place what fits; the rest goes on another sheet.",
        "de": "Achtung: Die Anordnung überschreitet das Material ({w:.0f}×{h:.0f} mm). Die Anordnung platziert, was passt; der Rest kommt auf ein weiteres Blatt.",
        "es": "Atención: el conjunto supera el material ({w:.0f}×{h:.0f} mm). El anidado colocará lo que quepa; el resto irá en otra plancha.",
    },
    "ornament.name": {
        "fr": "Prénom :",
        "en": "Name:",
        "de": "Name:",
        "es": "Nombre:",
    },
    "ornament.font": {
        "fr": "Police :",
        "en": "Font:",
        "de": "Schrift:",
        "es": "Fuente:",
    },
    "ornament.bold": {
        "fr": "Gras",
        "en": "Bold",
        "de": "Fett",
        "es": "Negrita",
    },
    "ornament.italic": {
        "fr": "Italique",
        "en": "Italic",
        "de": "Kursiv",
        "es": "Cursiva",
    },
    "ornament.diameter": {
        "fr": "Diamètre :",
        "en": "Diameter:",
        "de": "Durchmesser:",
        "es": "Diámetro:",
    },
    "ornament.ring_width": {
        "fr": "Largeur de l'anneau :",
        "en": "Ring width:",
        "de": "Ringbreite:",
        "es": "Ancho del aro:",
    },
    "ornament.hanger": {
        "fr": "Accroche :",
        "en": "Hanger:",
        "de": "Aufhänger:",
        "es": "Colgador:",
    },
    "ornament.hole": {
        "fr": "Trou de la ficelle :",
        "en": "String hole:",
        "de": "Fadenloch:",
        "es": "Agujero del hilo:",
    },
    "ornament.motif": {
        "fr": "Motif :",
        "en": "Motif:",
        "de": "Motiv:",
        "es": "Motivo:",
    },
    "ornament.layout": {
        "fr": "Disposition :",
        "en": "Layout:",
        "de": "Anordnung:",
        "es": "Disposición:",
    },
    "ornament.style": {
        "fr": "Style :",
        "en": "Style:",
        "de": "Stil:",
        "es": "Estilo:",
    },
    "ornament.count": {
        "fr": "Nombre de motifs :",
        "en": "Number of motifs:",
        "de": "Anzahl Motive:",
        "es": "Número de motivos:",
    },
    "ornament.flake_size": {
        "fr": "Taille des motifs :",
        "en": "Motif size:",
        "de": "Motivgröße:",
        "es": "Tamaño de los motivos:",
    },
    "ornament.stem": {
        "fr": "Largeur de la suspente :",
        "en": "Hanging stem width:",
        "de": "Breite des Aufhängers:",
        "es": "Ancho del colgante:",
    },
    "ornament.stem_auto": {
        "fr": "Auto",
        "en": "Auto",
        "de": "Auto",
        "es": "Auto",
    },
    "ornament.stem_tip": {
        "fr": "Largeur du fil qui relie le motif à l'anneau. Auto : proportionnelle à la taille du motif (2 mm au minimum). Le pied de la suspente s'évase du côté de l'anneau.",
        "en": "Width of the stem linking the motif to the ring. Auto: proportional to the motif size (2 mm minimum). The stem flares out at the ring end.",
        "de": "Breite des Stegs zwischen Motiv und Ring. Auto: proportional zur Motivgröße (mindestens 2 mm). Der Steg verbreitert sich am Ring.",
        "es": "Ancho del hilo que une el motivo con el aro. Auto: proporcional al tamaño del motivo (mínimo 2 mm). El pie se ensancha junto al aro.",
    },
    "ornament.drop": {
        "fr": "Descendre le motif :",
        "en": "Lower the motif:",
        "de": "Motiv absenken:",
        "es": "Bajar el motivo:",
    },
    "ornament.drop_tip": {
        "fr": "Écarte le motif de l'anneau, vers le centre de la boule : les motifs du haut ou suspendus descendent "
              "(la suspente s'allonge, on voit le haut du motif, par exemple le nœud d'un cadeau), ceux du bas montent. "
              "Une tige garde le contact avec l'anneau. Une valeur négative rapproche le motif de l'anneau.",
        "en": "Moves the motif away from the ring, towards the centre of the ornament: top or hanging motifs go down "
              "(the stem gets longer, so the top of the motif shows, such as a gift's bow), bottom ones go up. "
              "A stem keeps the motif joined to the ring. A negative value brings it closer to the ring.",
        "de": "Rückt das Motiv vom Ring weg zur Mitte der Kugel: obere oder hängende Motive gehen nach unten "
              "(der Steg wird länger, die Oberseite des Motivs, etwa die Schleife eines Geschenks, bleibt sichtbar), "
              "untere gehen nach oben. Ein Steg hält die Verbindung zum Ring. Ein negativer Wert rückt es näher an den Ring.",
        "es": "Aleja el motivo del anillo, hacia el centro de la bola: los de arriba o colgantes bajan "
              "(el hilo se alarga y se ve la parte superior del motivo, por ejemplo el lazo de un regalo), los de abajo suben. "
              "Un tallo mantiene el contacto con el anillo. Un valor negativo lo acerca al anillo.",
    },
    "ornament.name_offset": {
        "fr": "Hauteur du prénom :",
        "en": "Name height offset:",
        "de": "Namenshöhe (Versatz):",
        "es": "Altura del nombre:",
    },
    "ornament.name_size": {
        "fr": "Taille du prénom :",
        "en": "Name size:",
        "de": "Namensgröße:",
        "es": "Tamaño del nombre:",
    },
    "ornament.auto": {
        "fr": "Auto",
        "en": "Auto",
        "de": "Auto",
        "es": "Auto",
    },
    "ornament.support": {
        "fr": "Soutien du prénom :",
        "en": "Name support:",
        "de": "Namensstütze:",
        "es": "Soporte del nombre:",
    },
    "ornament.support_tip": {
        "fr": "La barre relie le prénom à l'anneau pour qu'il ne tombe pas à la découpe. Sans barre, le prénom doit toucher l'anneau des deux côtés (polices cursives larges).",
        "en": "The bar joins the name to the ring so it does not fall out when cut. Without a bar, the name must touch the ring on both sides (wide script fonts).",
        "de": "Der Steg verbindet den Namen mit dem Ring, damit er beim Schneiden nicht herausfällt. Ohne Steg muss der Name den Ring auf beiden Seiten berühren (breite Schreibschriften).",
        "es": "La barra une el nombre al aro para que no se caiga al cortar. Sin barra, el nombre debe tocar el aro por ambos lados (fuentes cursivas anchas).",
    },
    "ornament.layer": {
        "fr": "Calque de découpe :",
        "en": "Cut layer:",
        "de": "Schnittebene:",
        "es": "Capa de corte:",
    },
    "ornament.preview": {
        "fr": "Aperçu (rouge : découpe, bleu : gravure) :",
        "en": "Preview (red: cut, blue: engraving):",
        "de": "Vorschau (rot: Schnitt, blau: Gravur):",
        "es": "Vista previa (rojo: corte, azul: grabado):",
    },
    "ornament.hint": {
        "fr": "Les lettres, les flocons et l'anneau sont soudés en une seule pièce : chaque contour n'est découpé qu'une fois. Attention aux lettres avec un point (i, j) ou un accent : ils sont détachés du reste et tomberont.",
        "en": "Letters, snowflakes and ring are welded into one piece: each outline is cut only once. Beware of letters with a dot (i, j) or an accent: they are detached from the rest and will fall out.",
        "de": "Buchstaben, Schneeflocken und Ring werden zu einem Teil verschmolzen: jede Kontur wird nur einmal geschnitten. Vorsicht bei Buchstaben mit Punkt (i, j) oder Akzent: sie sind losgelöst und fallen heraus.",
        "es": "Las letras, los copos y el aro se sueldan en una sola pieza: cada contorno se corta una sola vez. Cuidado con las letras con punto (i, j) o acento: quedan sueltas y se caerán.",
    },
    "ornament.warn.floating": {
        "fr": "Le prénom ne touche pas l'anneau : il tomberait à la découpe. Choisis le soutien « Barre » ou agrandis le prénom.",
        "en": "The name does not touch the ring: it would fall out when cut. Choose the “Bar” support or enlarge the name.",
        "de": "Der Name berührt den Ring nicht: er würde beim Schneiden herausfallen. Wähle die Stütze „Steg“ oder vergrößere den Namen.",
        "es": "El nombre no toca el aro: se caería al cortar. Elige el soporte «Barra» o agranda el nombre.",
    },
    "ornament.hanger.Anneau": {
        "fr": "Anneau",
        "en": "Ring",
        "de": "Ring",
        "es": "Anillo",
    },
    "ornament.hanger.Bouchon": {
        "fr": "Bouchon + anneau",
        "en": "Cap + ring",
        "de": "Kappe + Ring",
        "es": "Tapón + anillo",
    },
    "ornament.hanger.Aucun": {
        "fr": "Aucune",
        "en": "None",
        "de": "Keiner",
        "es": "Ninguno",
    },
    "ornament.motif.Flocons": {
        "fr": "Flocons",
        "en": "Snowflakes",
        "de": "Schneeflocken",
        "es": "Copos de nieve",
    },
    "ornament.motif.Aucun": {
        "fr": "Aucun",
        "en": "None",
        "de": "Keines",
        "es": "Ninguno",
    },
    "ornament.layout.Suspendus": {
        "fr": "Suspendus",
        "en": "Hanging",
        "de": "Hängend",
        "es": "Colgantes",
    },
    "ornament.layout.Haut et bas": {
        "fr": "Haut et bas",
        "en": "Top and bottom",
        "de": "Oben und unten",
        "es": "Arriba y abajo",
    },
    "ornament.layout.Haut": {
        "fr": "Haut",
        "en": "Top",
        "de": "Oben",
        "es": "Arriba",
    },
    "ornament.layout.Bas": {
        "fr": "Bas",
        "en": "Bottom",
        "de": "Unten",
        "es": "Abajo",
    },
    "ornament.style.Classique": {
        "fr": "Classique",
        "en": "Classic",
        "de": "Klassisch",
        "es": "Clásico",
    },
    "ornament.style.Dentelle": {
        "fr": "Dentelle",
        "en": "Lace",
        "de": "Spitze",
        "es": "Encaje",
    },
    "ornament.style.Étoile": {
        "fr": "Étoile",
        "en": "Star",
        "de": "Stern",
        "es": "Estrella",
    },
    "ornament.motif.Étoiles": {
        "fr": "Étoiles",
        "en": "Stars",
        "de": "Sterne",
        "es": "Estrellas",
    },
    "ornament.motif.Sapins": {
        "fr": "Sapins",
        "en": "Fir trees",
        "de": "Tannenbäume",
        "es": "Abetos",
    },
    "ornament.motif.Père Noël": {
        "fr": "Père Noël",
        "en": "Santa Claus",
        "de": "Weihnachtsmann",
        "es": "Papá Noel",
    },
    "ornament.motif.Bonhomme de neige": {
        "fr": "Bonhomme de neige",
        "en": "Snowman",
        "de": "Schneemann",
        "es": "Muñeco de nieve",
    },
    "ornament.motif.Cadeaux": {
        "fr": "Cadeaux",
        "en": "Gifts",
        "de": "Geschenke",
        "es": "Regalos",
    },
    "ornament.style.5 branches": {
        "fr": "5 branches",
        "en": "5 points",
        "de": "5 Zacken",
        "es": "5 puntas",
    },
    "ornament.style.4 branches": {
        "fr": "4 branches (scintillante)",
        "en": "4 points (twinkle)",
        "de": "4 Zacken (funkelnd)",
        "es": "4 puntas (centelleante)",
    },
    "ornament.style.8 branches": {
        "fr": "8 branches",
        "en": "8 points",
        "de": "8 Zacken",
        "es": "8 puntas",
    },
    "ornament.style.Mixte": {
        "fr": "Mixte",
        "en": "Mixed",
        "de": "Gemischt",
        "es": "Mixto",
    },
    "ornament.style.Simple": {
        "fr": "Simple",
        "en": "Simple",
        "de": "Einfach",
        "es": "Simple",
    },
    "ornament.style.Fin": {
        "fr": "Fin (5 étages)",
        "en": "Slim (5 tiers)",
        "de": "Schlank (5 Etagen)",
        "es": "Fino (5 pisos)",
    },
    "ornament.support.Barre": {
        "fr": "Barre",
        "en": "Bar",
        "de": "Steg",
        "es": "Barra",
    },
    "ornament.support.Aucun": {
        "fr": "Aucun",
        "en": "None",
        "de": "Keiner",
        "es": "Ninguno",
    },
    "ornament.err.diameter": {
        "fr": "Diamètre invalide ({value:.1f} mm) : entre 30 et 400 mm.",
        "en": "Invalid diameter ({value:.1f} mm): between 30 and 400 mm.",
        "de": "Ungültiger Durchmesser ({value:.1f} mm): 30 bis 400 mm.",
        "es": "Diámetro no válido ({value:.1f} mm): entre 30 y 400 mm.",
    },
    "ornament.err.ring_width": {
        "fr": "Largeur d'anneau invalide ({value:.1f} mm) : entre {lo:.1f} et {hi:.1f} mm.",
        "en": "Invalid ring width ({value:.1f} mm): between {lo:.1f} and {hi:.1f} mm.",
        "de": "Ungültige Ringbreite ({value:.1f} mm): {lo:.1f} bis {hi:.1f} mm.",
        "es": "Ancho de aro no válido ({value:.1f} mm): entre {lo:.1f} y {hi:.1f} mm.",
    },
    "ornament.err.hole": {
        "fr": "Trou invalide ({value:.1f} mm) : entre 1,5 et 10 mm.",
        "en": "Invalid hole ({value:.1f} mm): between 1.5 and 10 mm.",
        "de": "Ungültiges Loch ({value:.1f} mm): 1,5 bis 10 mm.",
        "es": "Agujero no válido ({value:.1f} mm): entre 1,5 y 10 mm.",
    },
    "ornament.err.flake_count": {
        "fr": "Nombre de flocons invalide : entre 1 et 7.",
        "en": "Invalid number of snowflakes: between 1 and 7.",
        "de": "Ungültige Anzahl Schneeflocken: 1 bis 7.",
        "es": "Número de copos no válido: entre 1 y 7.",
    },
    "ornament.err.flake_size": {
        "fr": "Taille de flocon invalide ({value:.1f} mm) : entre {lo:.1f} et {hi:.1f} mm.",
        "en": "Invalid snowflake size ({value:.1f} mm): between {lo:.1f} and {hi:.1f} mm.",
        "de": "Ungültige Schneeflockengröße ({value:.1f} mm): {lo:.1f} bis {hi:.1f} mm.",
        "es": "Tamaño de copo no válido ({value:.1f} mm): entre {lo:.1f} y {hi:.1f} mm.",
    },
    "ornament.err.bar": {
        "fr": "Épaisseur de barre invalide ({value:.1f} mm) : entre 1 et 6 mm.",
        "en": "Invalid bar thickness ({value:.1f} mm): between 1 and 6 mm.",
        "de": "Ungültige Stegdicke ({value:.1f} mm): 1 bis 6 mm.",
        "es": "Grosor de barra no válido ({value:.1f} mm): entre 1 y 6 mm.",
    },
    "ornament.err.name_too_long": {
        "fr": "Prénom trop long ({value} caractères) : 40 au maximum.",
        "en": "Name too long ({value} characters): 40 maximum.",
        "de": "Name zu lang ({value} Zeichen): höchstens 40.",
        "es": "Nombre demasiado largo ({value} caracteres): máximo 40.",
    },

    # --- Imbrication automatique ---
    "ui.vector_nesting": {
        "fr": "🧩 Imbrication auto",
        "en": "🧩 Auto-nesting",
        "de": "🧩 Auto-Anordnung",
        "es": "🧩 Anidado automático",
    },
    "ui.vector_nesting_tip": {
        "fr": "Range automatiquement les pièces sur la feuille pour gaspiller le moins de matière possible.",
        "en": "Automatically arranges the parts on the sheet to waste as little material as possible.",
        "de": "Ordnet die Teile automatisch auf dem Blatt an, damit möglichst wenig Material verschwendet wird.",
        "es": "Coloca automáticamente las piezas en la hoja para desperdiciar el mínimo de material.",
    },
    "ui.vector_serial_duplicate": {
        "fr": "Dupliquer en série…",
        "en": "Duplicate in series…",
        "de": "In Serie duplizieren…",
        "es": "Duplicar en serie…",
    },
    "serial.title": {
        "fr": "Dupliquer en série",
        "en": "Duplicate in series",
        "de": "In Serie duplizieren",
        "es": "Duplicar en serie",
    },
    "serial.no_selection": {
        "fr": "Sélectionne d'abord les objets à dupliquer (clic, Ctrl+clic ou rectangle de sélection) : contour de découpe, gravure et texte forment ensemble un exemplaire.",
        "en": "First select the objects to duplicate (click, Ctrl+click or selection rectangle): the cut outline, engraving and text together make one copy.",
        "de": "Wähle zuerst die zu duplizierenden Objekte aus (Klick, Strg+Klick oder Auswahlrechteck): Schnittkontur, Gravur und Text bilden zusammen ein Exemplar.",
        "es": "Selecciona primero los objetos que quieres duplicar (clic, Ctrl+clic o rectángulo de selección): el contorno de corte, el grabado y el texto forman juntos un ejemplar.",
    },
    "serial.selection_info": {
        "fr": "{count} objet(s) sélectionné(s) : ils forment un exemplaire. L'original devient le premier exemplaire.",
        "en": "{count} object(s) selected: they make up one copy. The original becomes the first copy.",
        "de": "{count} Objekt(e) ausgewählt: Sie bilden zusammen ein Exemplar. Das Original wird zum ersten Exemplar.",
        "es": "{count} objeto(s) seleccionado(s): forman un ejemplar. El original pasa a ser el primer ejemplar.",
    },
    "serial.count": {
        "fr": "Nombre d'exemplaires",
        "en": "Number of copies",
        "de": "Anzahl der Exemplare",
        "es": "Número de ejemplares",
    },
    "serial.count_tip": {
        "fr": "Ignoré quand une liste de textes est saisie : il y a alors un exemplaire par ligne.",
        "en": "Ignored when a list of texts is entered: there is then one copy per line.",
        "de": "Wird ignoriert, wenn eine Liste von Texten eingegeben ist: Dann gibt es ein Exemplar pro Zeile.",
        "es": "Se ignora cuando se introduce una lista de textos: entonces hay un ejemplar por línea.",
    },
    "serial.text_target": {
        "fr": "Texte à personnaliser",
        "en": "Text to customize",
        "de": "Zu individualisierender Text",
        "es": "Texto a personalizar",
    },
    "serial.names": {
        "fr": "Un texte par exemplaire (un par ligne)",
        "en": "One text per copy (one per line)",
        "de": "Ein Text pro Exemplar (einer pro Zeile)",
        "es": "Un texto por ejemplar (uno por línea)",
    },
    "serial.names_placeholder": {
        "fr": "Léa\nTom\nAnna",
        "en": "Lea\nTom\nAnna",
        "de": "Lea\nTom\nAnna",
        "es": "Lea\nTom\nAnna",
    },
    "serial.keep_center": {
        "fr": "Garder chaque texte centré sur l'emplacement d'origine",
        "en": "Keep each text centered on the original position",
        "de": "Jeden Text auf der ursprünglichen Position zentriert halten",
        "es": "Mantener cada texto centrado en la posición original",
    },
    "serial.no_text": {
        "fr": "Aucun texte dans la sélection. Pour mettre un prénom différent sur chaque exemplaire, sélectionne aussi le texte du modèle.",
        "en": "There is no text in the selection. To put a different name on each copy, also select the text of the template.",
        "de": "Die Auswahl enthält keinen Text. Um auf jedes Exemplar einen anderen Namen zu setzen, wähle auch den Text der Vorlage aus.",
        "es": "No hay ningún texto en la selección. Para poner un nombre distinto en cada ejemplar, selecciona también el texto de la plantilla.",
    },
    "serial.layout": {
        "fr": "Disposition",
        "en": "Layout",
        "de": "Anordnung",
        "es": "Disposición",
    },
    "serial.layout_grid": {
        "fr": "Grille",
        "en": "Grid",
        "de": "Raster",
        "es": "Cuadrícula",
    },
    "serial.layout_nest": {
        "fr": "Organisation automatique (imbrication)",
        "en": "Automatic arrangement (nesting)",
        "de": "Automatische Anordnung (Nesting)",
        "es": "Organización automática (anidado)",
    },
    "serial.columns": {
        "fr": "Colonnes",
        "en": "Columns",
        "de": "Spalten",
        "es": "Columnas",
    },
    "serial.gap_x": {
        "fr": "Espacement horizontal",
        "en": "Horizontal spacing",
        "de": "Horizontaler Abstand",
        "es": "Separación horizontal",
    },
    "serial.gap_y": {
        "fr": "Espacement vertical",
        "en": "Vertical spacing",
        "de": "Vertikaler Abstand",
        "es": "Separación vertical",
    },
    "serial.direction": {
        "fr": "Rangées suivantes",
        "en": "Following rows",
        "de": "Folgende Reihen",
        "es": "Filas siguientes",
    },
    "serial.dir_up": {
        "fr": "Vers le haut",
        "en": "Upwards",
        "de": "Nach oben",
        "es": "Hacia arriba",
    },
    "serial.dir_down": {
        "fr": "Vers le bas",
        "en": "Downwards",
        "de": "Nach unten",
        "es": "Hacia abajo",
    },
    "serial.avoid_existing": {
        "fr": "Éviter les objets déjà présents",
        "en": "Avoid objects already present",
        "de": "Bereits vorhandene Objekte aussparen",
        "es": "Evitar los objetos ya presentes",
    },
    "serial.avoid_existing_tip": {
        "fr": "Les objets du canevas qui ne sont pas dans la sélection (par exemple un lot dupliqué juste avant) ne sont pas recouverts. À décocher si un cadre ou un fond bloque toute la feuille.",
        "en": "Objects on the canvas that are not in the selection (for example a batch duplicated just before) are not covered. Untick if a frame or background blocks the whole sheet.",
        "de": "Objekte auf der Zeichenfläche, die nicht zur Auswahl gehören (zum Beispiel eine gerade zuvor duplizierte Serie), werden nicht überdeckt. Deaktiviere dies, wenn ein Rahmen oder Hintergrund das ganze Blatt blockiert.",
        "es": "Los objetos del lienzo que no están en la selección (por ejemplo un lote duplicado justo antes) no se cubren. Desmárcalo si un marco o un fondo bloquea toda la hoja.",
    },
    "serial.nest_hint": {
        "fr": "Chaque exemplaire (découpe, gravure et texte) est placé comme un bloc. Les rotations sont désactivées par défaut pour que les textes restent dans le bon sens.",
        "en": "Each copy (cut, engraving and text) is placed as one block. Rotations are off by default so that texts keep their direction.",
        "de": "Jedes Exemplar (Schnitt, Gravur und Text) wird als ein Block platziert. Drehungen sind standardmäßig ausgeschaltet, damit die Texte ihre Richtung behalten.",
        "es": "Cada ejemplar (corte, grabado y texto) se coloca como un bloque. Las rotaciones están desactivadas por defecto para que los textos conserven su sentido.",
    },
    "serial.count_info": {
        "fr": "{count} exemplaire(s) seront placés sur la feuille.",
        "en": "{count} copy(ies) will be placed on the sheet.",
        "de": "{count} Exemplar(e) werden auf dem Blatt platziert.",
        "es": "{count} ejemplar(es) se colocarán en la hoja.",
    },
    "serial.extent": {
        "fr": "{count} exemplaire(s), emprise {w} x {h} mm.",
        "en": "{count} copy(ies), footprint {w} x {h} mm.",
        "de": "{count} Exemplar(e), Fläche {w} x {h} mm.",
        "es": "{count} ejemplar(es), superficie {w} x {h} mm.",
    },
    "serial.extent_too_big": {
        "fr": "Cela dépasse la zone de travail de la machine ({bed_w} x {bed_h} mm).",
        "en": "This exceeds the machine work area ({bed_w} x {bed_h} mm).",
        "de": "Das überschreitet den Arbeitsbereich der Maschine ({bed_w} x {bed_h} mm).",
        "es": "Esto supera el área de trabajo de la máquina ({bed_w} x {bed_h} mm).",
    },
    "serial.done": {
        "fr": "{count} exemplaire(s) au total, emprise {w} x {h} mm.\n\nAnnulable avec Ctrl+Z.",
        "en": "{count} copy(ies) in total, footprint {w} x {h} mm.\n\nCan be undone with Ctrl+Z.",
        "de": "Insgesamt {count} Exemplar(e), Fläche {w} x {h} mm.\n\nMit Strg+Z rückgängig zu machen.",
        "es": "{count} ejemplar(es) en total, superficie {w} x {h} mm.\n\nSe puede deshacer con Ctrl+Z.",
    },
    "serial.unplaced": {
        "fr": "{count} exemplaire(s) n'ont pas trouvé de place sur la feuille et n'ont pas été créés : agrandis la feuille ou réduis l'écart.",
        "en": "{count} copy(ies) found no room on the sheet and were not created: enlarge the sheet or reduce the spacing.",
        "de": "{count} Exemplar(e) haben auf dem Blatt keinen Platz gefunden und wurden nicht erstellt: Vergrößere das Blatt oder verringere den Abstand.",
        "es": "{count} ejemplar(es) no encontraron sitio en la hoja y no se crearon: agranda la hoja o reduce la separación.",
    },
    "serial.overflow": {
        "fr": "Attention : le texte dépasse du motif pour : {names}.",
        "en": "Warning: the text extends beyond the design for: {names}.",
        "de": "Achtung: Der Text ragt über das Motiv hinaus bei: {names}.",
        "es": "Atención: el texto sobresale del motivo en: {names}.",
    },
    "serial.error": {
        "fr": "Impossible de dupliquer : {error}",
        "en": "Unable to duplicate: {error}",
        "de": "Duplizieren nicht möglich: {error}",
        "es": "No se puede duplicar: {error}",
    },
    "ui.vector_jig": {
        "fr": "Gabarit de placement…",
        "en": "Placement jig…",
        "de": "Platzierungsschablone…",
        "es": "Plantilla de colocación…",
    },
    "jig.title": {
        "fr": "Gabarit de placement",
        "en": "Placement jig",
        "de": "Platzierungsschablone",
        "es": "Plantilla de colocación",
    },
    "jig.selection_info": {
        "fr": "Dimensions prises sur la sélection : {w} x {h} mm. Tu peux les corriger ci-dessous.",
        "en": "Dimensions taken from the selection: {w} x {h} mm. You can adjust them below.",
        "de": "Maße aus der Auswahl übernommen: {w} x {h} mm. Du kannst sie unten anpassen.",
        "es": "Dimensiones tomadas de la selección: {w} x {h} mm. Puedes corregirlas abajo.",
    },
    "jig.no_selection_info": {
        "fr": "Aucune sélection : entre les dimensions de l'objet à loger dans les poches.",
        "en": "Nothing selected: enter the dimensions of the object that goes in the pockets.",
        "de": "Keine Auswahl: Gib die Maße des Objekts ein, das in die Taschen kommt.",
        "es": "No hay selección: introduce las dimensiones del objeto que irá en los huecos.",
    },
    "jig.obj_w": {
        "fr": "Largeur de l'objet",
        "en": "Object width",
        "de": "Breite des Objekts",
        "es": "Ancho del objeto",
    },
    "jig.obj_h": {
        "fr": "Hauteur de l'objet",
        "en": "Object height",
        "de": "Höhe des Objekts",
        "es": "Alto del objeto",
    },
    "jig.clearance": {
        "fr": "Jeu autour de l'objet",
        "en": "Clearance around the object",
        "de": "Spiel um das Objekt",
        "es": "Holgura alrededor del objeto",
    },
    "jig.clearance_tip": {
        "fr": "Espace laissé de chaque côté de l'objet pour qu'il se pose et se retire facilement (0,2 à 0,5 mm en général, à ajuster selon le laser et le matériau).",
        "en": "Space left on each side of the object so that it can be placed and removed easily (usually 0.2 to 0.5 mm, to adjust to the laser and the material).",
        "de": "Platz auf jeder Seite des Objekts, damit es sich leicht einlegen und entnehmen lässt (meist 0,2 bis 0,5 mm, je nach Laser und Material anzupassen).",
        "es": "Espacio que se deja a cada lado del objeto para colocarlo y retirarlo con facilidad (normalmente de 0,2 a 0,5 mm, a ajustar según el láser y el material).",
    },
    "jig.shape": {
        "fr": "Forme des poches",
        "en": "Pocket shape",
        "de": "Form der Taschen",
        "es": "Forma de los huecos",
    },
    "jig.shape_rect": {
        "fr": "Rectangle",
        "en": "Rectangle",
        "de": "Rechteck",
        "es": "Rectángulo",
    },
    "jig.shape_ellipse": {
        "fr": "Ellipse / cercle",
        "en": "Ellipse / circle",
        "de": "Ellipse / Kreis",
        "es": "Elipse / círculo",
    },
    "jig.pocket_radius": {
        "fr": "Rayon des coins des poches",
        "en": "Pocket corner radius",
        "de": "Eckenradius der Taschen",
        "es": "Radio de las esquinas de los huecos",
    },
    "jig.cols": {
        "fr": "Poches en largeur",
        "en": "Pockets across",
        "de": "Taschen in der Breite",
        "es": "Huecos a lo ancho",
    },
    "jig.rows": {
        "fr": "Poches en hauteur",
        "en": "Pockets down",
        "de": "Taschen in der Höhe",
        "es": "Huecos a lo alto",
    },
    "jig.gap_x": {
        "fr": "Espacement horizontal entre objets",
        "en": "Horizontal spacing between objects",
        "de": "Horizontaler Abstand zwischen Objekten",
        "es": "Separación horizontal entre objetos",
    },
    "jig.gap_y": {
        "fr": "Espacement vertical entre objets",
        "en": "Vertical spacing between objects",
        "de": "Vertikaler Abstand zwischen Objekten",
        "es": "Separación vertical entre objetos",
    },
    "jig.gap_tip": {
        "fr": "Distance entre deux objets voisins, bord à bord (la même notion que dans « Dupliquer en série »).",
        "en": "Distance between two neighbouring objects, edge to edge (the same notion as in “Duplicate in series”).",
        "de": "Abstand zwischen zwei benachbarten Objekten, Kante zu Kante (derselbe Begriff wie bei „In Serie duplizieren“).",
        "es": "Distancia entre dos objetos vecinos, de borde a borde (la misma noción que en «Duplicar en serie»).",
    },
    "jig.sync_hint": {
        "fr": "Pour que les exemplaires de « Dupliquer en série » tombent chacun dans leur poche, utilise les mêmes colonnes, les mêmes espacements et le même sens des rangées, puis place la plaque « Autour de la sélection ».",
        "en": "For the copies made by “Duplicate in series” to each land in their pocket, use the same columns, spacings and row direction, then place the plate “Around the selection”.",
        "de": "Damit die mit „In Serie duplizieren“ erzeugten Exemplare jeweils in ihrer Tasche landen, verwende dieselben Spalten, Abstände und dieselbe Reihenrichtung und platziere die Platte „Um die Auswahl“.",
        "es": "Para que los ejemplares de «Duplicar en serie» caigan cada uno en su hueco, usa las mismas columnas, separaciones y sentido de las filas, y coloca la placa «Alrededor de la selección».",
    },
    "jig.margin": {
        "fr": "Bordure de la plaque",
        "en": "Plate border",
        "de": "Plattenrand",
        "es": "Borde de la placa",
    },
    "jig.plate_radius": {
        "fr": "Rayon des coins de la plaque",
        "en": "Plate corner radius",
        "de": "Eckenradius der Platte",
        "es": "Radio de las esquinas de la placa",
    },
    "jig.base": {
        "fr": "Ajouter une plaque de fond pleine (même contour)",
        "en": "Add a solid base plate (same outline)",
        "de": "Vollständige Bodenplatte hinzufügen (gleiche Kontur)",
        "es": "Añadir una placa de fondo maciza (mismo contorno)",
    },
    "jig.position": {
        "fr": "Position de la plaque",
        "en": "Plate position",
        "de": "Position der Platte",
        "es": "Posición de la placa",
    },
    "jig.pos_beside": {
        "fr": "À côté de la sélection",
        "en": "Beside the selection",
        "de": "Neben der Auswahl",
        "es": "Junto a la selección",
    },
    "jig.pos_around": {
        "fr": "Autour de la sélection (la 1re poche entoure l'objet)",
        "en": "Around the selection (the 1st pocket surrounds the object)",
        "de": "Um die Auswahl (die 1. Tasche umschließt das Objekt)",
        "es": "Alrededor de la selección (el 1.er hueco rodea el objeto)",
    },
    "jig.pos_manual": {
        "fr": "Position X / Y",
        "en": "X / Y position",
        "de": "Position X / Y",
        "es": "Posición X / Y",
    },
    "jig.x": {
        "fr": "Position X",
        "en": "X position",
        "de": "Position X",
        "es": "Posición X",
    },
    "jig.y": {
        "fr": "Position Y",
        "en": "Y position",
        "de": "Position Y",
        "es": "Posición Y",
    },
    "jig.cut_layer": {
        "fr": "Calque de découpe",
        "en": "Cut layer",
        "de": "Schnittebene",
        "es": "Capa de corte",
    },
    "jig.info": {
        "fr": "Poche {pw} x {ph} mm, plaque {w} x {h} mm, pas entre poches {px} x {py} mm.",
        "en": "Pocket {pw} x {ph} mm, plate {w} x {h} mm, pocket pitch {px} x {py} mm.",
        "de": "Tasche {pw} x {ph} mm, Platte {w} x {h} mm, Taschenabstand {px} x {py} mm.",
        "es": "Hueco {pw} x {ph} mm, placa {w} x {h} mm, paso entre huecos {px} x {py} mm.",
    },
    "jig.wall": {
        "fr": "Paroi entre deux poches : {wall} mm.",
        "en": "Wall between two pockets: {wall} mm.",
        "de": "Steg zwischen zwei Taschen: {wall} mm.",
        "es": "Pared entre dos huecos: {wall} mm.",
    },
    "jig.wall_thin": {
        "fr": "Paroi fragile (moins de {min} mm) : augmente l'espacement ou réduis le jeu.",
        "en": "Fragile wall (less than {min} mm): increase the spacing or reduce the clearance.",
        "de": "Zerbrechlicher Steg (weniger als {min} mm): Vergrößere den Abstand oder verringere das Spiel.",
        "es": "Pared frágil (menos de {min} mm): aumenta la separación o reduce la holgura.",
    },
    "jig.too_big": {
        "fr": "La plaque dépasse la zone de travail de la machine ({bed_w} x {bed_h} mm).",
        "en": "The plate exceeds the machine work area ({bed_w} x {bed_h} mm).",
        "de": "Die Platte überschreitet den Arbeitsbereich der Maschine ({bed_w} x {bed_h} mm).",
        "es": "La placa supera el área de trabajo de la máquina ({bed_w} x {bed_h} mm).",
    },
    "jig.err.size": {
        "fr": "Les dimensions de l'objet doivent être supérieures à zéro.",
        "en": "The object dimensions must be greater than zero.",
        "de": "Die Maße des Objekts müssen größer als null sein.",
        "es": "Las dimensiones del objeto deben ser mayores que cero.",
    },
    "jig.err.count": {
        "fr": "Trop de poches (maximum {max}).",
        "en": "Too many pockets (maximum {max}).",
        "de": "Zu viele Taschen (maximal {max}).",
        "es": "Demasiados huecos (máximo {max}).",
    },
    "jig.err.overlap": {
        "fr": "L'espacement entre objets doit être supérieur au double du jeu ({min} mm), sinon les poches se chevauchent.",
        "en": "The spacing between objects must be greater than twice the clearance ({min} mm), otherwise the pockets overlap.",
        "de": "Der Abstand zwischen Objekten muss größer sein als das Doppelte des Spiels ({min} mm), sonst überlappen sich die Taschen.",
        "es": "La separación entre objetos debe ser mayor que el doble de la holgura ({min} mm); si no, los huecos se solapan.",
    },
    "jig.done": {
        "fr": "Gabarit créé : {count} poche(s) de {pw} x {ph} mm sur une plaque de {w} x {h} mm.\n\nAnnulable avec Ctrl+Z.",
        "en": "Jig created: {count} pocket(s) of {pw} x {ph} mm on a {w} x {h} mm plate.\n\nCan be undone with Ctrl+Z.",
        "de": "Schablone erstellt: {count} Tasche(n) von {pw} x {ph} mm auf einer Platte von {w} x {h} mm.\n\nMit Strg+Z rückgängig zu machen.",
        "es": "Plantilla creada: {count} hueco(s) de {pw} x {ph} mm en una placa de {w} x {h} mm.\n\nSe puede deshacer con Ctrl+Z.",
    },
    "jig.out_of_bed": {
        "fr": "Attention : la plaque sort de la zone de travail de la machine ({bed_w} x {bed_h} mm).",
        "en": "Warning: the plate extends outside the machine work area ({bed_w} x {bed_h} mm).",
        "de": "Achtung: Die Platte ragt aus dem Arbeitsbereich der Maschine heraus ({bed_w} x {bed_h} mm).",
        "es": "Atención: la placa sale del área de trabajo de la máquina ({bed_w} x {bed_h} mm).",
    },
    "nest.title": {
        "fr": "Imbrication automatique",
        "en": "Automatic nesting",
        "de": "Automatische Anordnung (Nesting)",
        "es": "Anidado automático",
    },
    "nest.count_info": {
        "fr": "{selected} objet(s) sélectionné(s), {total} objet(s) sur des calques actifs.",
        "en": "{selected} object(s) selected, {total} object(s) on active layers.",
        "de": "{selected} Objekt(e) ausgewählt, {total} Objekt(e) auf aktiven Ebenen.",
        "es": "{selected} objeto(s) seleccionado(s), {total} objeto(s) en capas activas.",
    },
    "nest.scope": {
        "fr": "Pièces à placer :",
        "en": "Parts to place:",
        "de": "Zu platzierende Teile:",
        "es": "Piezas a colocar:",
    },
    "nest.scope_selection": {
        "fr": "La sélection",
        "en": "The selection",
        "de": "Die Auswahl",
        "es": "La selección",
    },
    "nest.scope_all": {
        "fr": "Tous les objets",
        "en": "All objects",
        "de": "Alle Objekte",
        "es": "Todos los objetos",
    },
    "nest.sheet_w": {
        "fr": "Largeur de la feuille :",
        "en": "Sheet width:",
        "de": "Blattbreite:",
        "es": "Ancho de la hoja:",
    },
    "nest.sheet_h": {
        "fr": "Hauteur de la feuille :",
        "en": "Sheet height:",
        "de": "Blatthöhe:",
        "es": "Alto de la hoja:",
    },
    "nest.origin_x": {
        "fr": "Coin bas-gauche de la feuille, X :",
        "en": "Sheet bottom-left corner, X:",
        "de": "Untere linke Blattecke, X:",
        "es": "Esquina inferior izquierda de la hoja, X:",
    },
    "nest.origin_y": {
        "fr": "Coin bas-gauche de la feuille, Y :",
        "en": "Sheet bottom-left corner, Y:",
        "de": "Untere linke Blattecke, Y:",
        "es": "Esquina inferior izquierda de la hoja, Y:",
    },
    "nest.spacing": {
        "fr": "Écart entre les pièces :",
        "en": "Spacing between parts:",
        "de": "Abstand zwischen den Teilen:",
        "es": "Separación entre piezas:",
    },
    "nest.margin": {
        "fr": "Marge au bord de la feuille :",
        "en": "Margin at the sheet edge:",
        "de": "Rand am Blattrand:",
        "es": "Margen en el borde de la hoja:",
    },
    "nest.rotations": {
        "fr": "Rotations autorisées :",
        "en": "Allowed rotations:",
        "de": "Erlaubte Drehungen:",
        "es": "Rotaciones permitidas:",
    },
    "nest.rot_none": {
        "fr": "Aucune",
        "en": "None",
        "de": "Keine",
        "es": "Ninguna",
    },
    "nest.rot_flip": {
        "fr": "0° et 90°",
        "en": "0° and 90°",
        "de": "0° und 90°",
        "es": "0° y 90°",
    },
    "nest.rot_quarters": {
        "fr": "0°, 90°, 180°, 270°",
        "en": "0°, 90°, 180°, 270°",
        "de": "0°, 90°, 180°, 270°",
        "es": "0°, 90°, 180°, 270°",
    },
    "nest.rot_eighths": {
        "fr": "Tous les 45°",
        "en": "Every 45°",
        "de": "Alle 45°",
        "es": "Cada 45°",
    },
    "nest.precision": {
        "fr": "Précision de la grille :",
        "en": "Grid precision:",
        "de": "Rasterfeinheit:",
        "es": "Precisión de la cuadrícula:",
    },
    "nest.prec_fast": {
        "fr": "Rapide (2 mm)",
        "en": "Fast (2 mm)",
        "de": "Schnell (2 mm)",
        "es": "Rápida (2 mm)",
    },
    "nest.prec_normal": {
        "fr": "Normale (1 mm)",
        "en": "Normal (1 mm)",
        "de": "Normal (1 mm)",
        "es": "Normal (1 mm)",
    },
    "nest.prec_precise": {
        "fr": "Précise (0,5 mm, plus lent)",
        "en": "Precise (0.5 mm, slower)",
        "de": "Genau (0,5 mm, langsamer)",
        "es": "Precisa (0,5 mm, más lenta)",
    },
    "nest.hint": {
        "fr": "Les contours qui sont à l'intérieur d'une pièce (trous, détails gravés) restent avec elle et tournent avec elle. Les pièces sont placées de la plus grande à la plus petite, en bas à gauche d'abord, et peuvent se glisser dans les creux des autres. L'opération s'annule avec Ctrl+Z.",
        "en": "Outlines inside a part (holes, engraved details) stay with it and rotate with it. Parts are placed from the largest to the smallest, bottom-left first, and can slip into the hollows of others. The operation can be undone with Ctrl+Z.",
        "de": "Konturen innerhalb eines Teils (Löcher, gravierte Details) bleiben bei ihm und drehen sich mit. Die Teile werden vom größten zum kleinsten platziert, zuerst unten links, und können in Aussparungen anderer rutschen. Mit Strg+Z lässt sich der Vorgang rückgängig machen.",
        "es": "Los contornos dentro de una pieza (agujeros, detalles grabados) se quedan con ella y giran con ella. Las piezas se colocan de la más grande a la más pequeña, primero abajo a la izquierda, y pueden entrar en los huecos de otras. La operación se deshace con Ctrl+Z.",
    },
    "nest.no_objects": {
        "fr": "Aucun objet sur un calque actif à placer.",
        "en": "There is no object on an active layer to place.",
        "de": "Es gibt kein Objekt auf einer aktiven Ebene zum Platzieren.",
        "es": "No hay ningún objeto en una capa activa que colocar.",
    },
    "nest.nothing_placed": {
        "fr": "Aucune pièce n'a pu être placée : la feuille est trop petite, ou la marge et l'écart sont trop grands.",
        "en": "No part could be placed: the sheet is too small, or the margin and spacing are too large.",
        "de": "Kein Teil konnte platziert werden: Das Blatt ist zu klein, oder Rand und Abstand sind zu groß.",
        "es": "No se pudo colocar ninguna pieza: la hoja es demasiado pequeña, o el margen y la separación son demasiado grandes.",
    },
    "nest.done": {
        "fr": "{placed} pièce(s) placée(s) sur la feuille de {sheet_w:.0f} x {sheet_h:.0f} mm. Zone utilisée : {ext_w:.0f} x {ext_h:.0f} mm, occupée à {percent:.0f} %.\n\nAnnulable avec Ctrl+Z.",
        "en": "{placed} part(s) placed on the {sheet_w:.0f} x {sheet_h:.0f} mm sheet. Area used: {ext_w:.0f} x {ext_h:.0f} mm, {percent:.0f} % filled.\n\nCan be undone with Ctrl+Z.",
        "de": "{placed} Teil(e) auf dem Blatt von {sheet_w:.0f} x {sheet_h:.0f} mm platziert. Genutzte Fläche: {ext_w:.0f} x {ext_h:.0f} mm, zu {percent:.0f} % belegt.\n\nMit Strg+Z rückgängig zu machen.",
        "es": "{placed} pieza(s) colocada(s) en la hoja de {sheet_w:.0f} x {sheet_h:.0f} mm. Zona usada: {ext_w:.0f} x {ext_h:.0f} mm, ocupada al {percent:.0f} %.\n\nSe puede deshacer con Ctrl+Z.",
    },
    "nest.unplaced": {
        "fr": "{count} pièce(s) n'ont pas trouvé de place et sont restées où elles étaient : agrandis la feuille, réduis l'écart ou autorise plus de rotations.",
        "en": "{count} part(s) found no room and stayed where they were: enlarge the sheet, reduce the spacing or allow more rotations.",
        "de": "{count} Teil(e) haben keinen Platz gefunden und blieben, wo sie waren: Vergrößere das Blatt, verringere den Abstand oder erlaube mehr Drehungen.",
        "es": "{count} pieza(s) no encontraron sitio y se quedaron donde estaban: agranda la hoja, reduce la separación o permite más rotaciones.",
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
    "ui.job_position_box": {
        "fr": "Position du job sur le plateau", "en": "Job Position on the Bed",
        "de": "Position des Jobs auf der Arbeitsfläche", "es": "Posición del trabajo en la mesa",
    },
    "ui.job_offset_in_image_tab": {
        "fr": "Le décalage (Offset X / Y) se règle dans l'onglet « Graver une image ».",
        "en": "The offset (Offset X / Y) is set in the \"Engrave an Image\" tab.",
        "de": "Der Versatz (Offset X / Y) wird im Reiter „Bild gravieren“ eingestellt.",
        "es": "El desplazamiento (Offset X / Y) se ajusta en la pestaña «Grabar una imagen».",
    },
    "queue.sent_log_title": {
        "fr": "G-Code envoyé", "en": "Sent G-Code", "de": "Gesendeter G-Code", "es": "G-Code enviado",
    },
    "queue.sent_log_placeholder": {
        "fr": "Les lignes de G-Code s'afficheront ici au fur et à mesure de leur envoi au graveur.",
        "en": "G-Code lines will appear here as they are sent to the engraver.",
        "de": "Die G-Code-Zeilen erscheinen hier, sobald sie an den Gravierer gesendet werden.",
        "es": "Las líneas de G-Code aparecerán aquí a medida que se envíen al grabador.",
    },
    "queue.sent_log_job": {
        "fr": "; ===== Job {index}/{total} : {name} =====",
        "en": "; ===== Job {index}/{total}: {name} =====",
        "de": "; ===== Job {index}/{total}: {name} =====",
        "es": "; ===== Trabajo {index}/{total}: {name} =====",
    },
    "queue.sent_log_direct": {
        "fr": "; ===== Envoi au laser =====", "en": "; ===== Send to laser =====",
        "de": "; ===== An den Laser senden =====", "es": "; ===== Envío al láser =====",
    },
    "queue.sent_log_done": {
        "fr": "; ----- Terminé -----", "en": "; ----- Done -----",
        "de": "; ----- Fertig -----", "es": "; ----- Terminado -----",
    },
    "queue.sent_log_stopped": {
        "fr": "; ----- Interrompu -----", "en": "; ----- Stopped -----",
        "de": "; ----- Abgebrochen -----", "es": "; ----- Interrumpido -----",
    },
    "img.show_original": {
        "fr": "Afficher l'originale", "en": "Show Original",
        "de": "Original anzeigen", "es": "Mostrar el original",
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
        # --- Interface principale ---
    "dialog.about.title": {
        "fr": "À propos de Laser Studio Pro",
        "en": "About Laser Studio Pro",
        "de": "Über Laser Studio Pro",
        "es": "Acerca de Laser Studio Pro",
    },
    "dialog.about.description": {
        "fr": "Logiciel de pilotage GRBL pour graveur/découpeuse laser<br>"
              "Gravure image, découpe/gravure vectorielle, calques multi-usages.",
        "en": "GRBL control software for laser engravers/cutters<br>"
              "Image engraving, vector cutting/engraving, multi-purpose layers.",
        "de": "GRBL-Steuerungssoftware für Lasergravierer und -schneider<br>"
              "Bildgravur, Vektorschneiden/-gravieren, vielseitige Ebenen.",
        "es": "Software de control GRBL para grabadoras/cortadoras láser<br>"
              "Grabado de imágenes, corte/grabado vectorial y capas multiuso.",
    },
    "dialog.support.title": {
        "fr": "Support",
        "en": "Support",
        "de": "Support",
        "es": "Soporte",
    },
    "dialog.support.body": {
        "fr": "Suggestion, problème rencontré... Contacte-nous à l'adresse "
              "suivante :<br><br>",
        "en": "Suggestion or problem... Contact us at the following address:"
              "<br><br>",
        "de": "Vorschlag oder Problem? Kontaktiere uns unter:"
              "<br><br>",
        "es": "¿Sugerencia o problema? Contáctanos en la siguiente dirección:"
              "<br><br>",
    },
    "dialog.coffee.title": {
        "fr": "Offrir un café",
        "en": "Buy me a coffee",
        "de": "Kauf mir einen Kaffee",
        "es": "Invítame a un café",
    },
    "dialog.coffee.body": {
        "fr": "Si ce logiciel t'est utile et que tu veux soutenir son développement,"
              "<br>tu peux m'offrir un café ici :<br><br>",
        "en": "If this software is useful to you and you want to support its "
              "development,<br>you can buy me a coffee here:<br><br>",
        "de": "Wenn diese Software für dich nützlich ist und du die Entwicklung "
              "unterstützen möchtest,<br>kannst du mir hier einen Kaffee kaufen:"
              "<br><br>",
        "es": "Si este software te resulta útil y quieres apoyar su desarrollo,"
              "<br>puedes invitarme a un café aquí:<br><br>",
    },

    "dim.keep_ratio": {
        "fr": "Conserver le ratio",
        "en": "Keep aspect ratio",
        "de": "Seitenverhältnis beibehalten",
        "es": "Mantener la proporción",
    },
    "dim.width": {
        "fr": "Largeur (mm):",
        "en": "Width (mm):",
        "de": "Breite (mm):",
        "es": "Ancho (mm):",
    },
    "dim.height": {
        "fr": "Hauteur (mm):",
        "en": "Height (mm):",
        "de": "Höhe (mm):",
        "es": "Alto (mm):",
    },
    "dim.origin": {
        "fr": "Ancrage Origine:",
        "en": "Origin Anchor:",
        "de": "Ursprungsanker:",
        "es": "Anclaje del origen:",
    },
    "dim.offset_x": {
        "fr": "Offset X (mm):",
        "en": "X Offset (mm):",
        "de": "X-Versatz (mm):",
        "es": "Desplazamiento X (mm):",
    },
    "dim.offset_y": {
        "fr": "Offset Y (mm):",
        "en": "Y Offset (mm):",
        "de": "Y-Versatz (mm):",
        "es": "Desplazamiento Y (mm):",
    },

    "usb.simulated_port": {
        "fr": "Graveur simulé (LASER_STUDIO_SIMULATION)",
        "en": "Simulated engraver (LASER_STUDIO_SIMULATION)",
        "de": "Simulierter Gravierer (LASER_STUDIO_SIMULATION)",
        "es": "Grabador simulado (LASER_STUDIO_SIMULATION)",
    },
    "usb.refresh_ports": {
        "fr": "Rafraîchir les ports",
        "en": "Refresh Ports",
        "de": "Ports aktualisieren",
        "es": "Actualizar puertos",
    },
    "usb.port": {
        "fr": "Port COM:",
        "en": "COM Port:",
        "de": "COM-Port:",
        "es": "Puerto COM:",
    },

    "material.box_title": {
        "fr": "Profils Matériaux",
        "en": "Material Profiles",
        "de": "Materialprofile",
        "es": "Perfiles de materiales",
    },
    "material.select": {
        "fr": "Profil matériau :",
        "en": "Material profile:",
        "de": "Materialprofil:",
        "es": "Perfil de material:",
    },
    "material.save": {
        "fr": "Sauvegarder les modifications",
        "en": "Save Profile Changes",
        "de": "Profiländerungen speichern",
        "es": "Guardar cambios del perfil",
    },
    "material.new": {
        "fr": "Nouveau profil...",
        "en": "New Profile...",
        "de": "Neues Profil...",
        "es": "Nuevo perfil...",
    },
    "material.delete": {
        "fr": "Supprimer le profil",
        "en": "Delete Profile",
        "de": "Profil löschen",
        "es": "Eliminar perfil",
    },
    "material.export": {
        "fr": "Exporter les profils (.json)...",
        "en": "Export Profiles (.json)...",
        "de": "Profile exportieren (.json)...",
        "es": "Exportar perfiles (.json)...",
    },
    "material.import": {
        "fr": "Importer des profils (.json)...",
        "en": "Import Profiles (.json)...",
        "de": "Profile importieren (.json)...",
        "es": "Importar perfiles (.json)...",
    },

    "gcode.estimate": {
        "fr": "Estimer le temps de gravure (rapide, sans générer)",
        "en": "Estimate engraving time (quick, without generating)",
        "de": "Gravurzeit schätzen (schnell, ohne Generierung)",
        "es": "Estimar el tiempo de grabado (rápido, sin generar)",
    },
    "gcode.generate": {
        "fr": "GÉNÉRER LE G-CODE",
        "en": "GENERATE G-CODE",
        "de": "G-CODE GENERIEREN",
        "es": "GENERAR G-CODE",
    },
    "gcode.import": {
        "fr": "Importer un G-Code existant (.gcode/.nc/.txt)",
        "en": "Import Existing G-Code (.gcode/.nc/.txt)",
        "de": "Vorhandenen G-Code importieren (.gcode/.nc/.txt)",
        "es": "Importar G-Code existente (.gcode/.nc/.txt)",
    },
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
    "ui.optimize_path": {
        "fr": "Optimiser le chemin", "en": "Optimize Path",
        "de": "Weg optimieren", "es": "Optimizar el recorrido",
    },
    "ui.optimize_path_tip": {
        "fr": "Optimiser l'ordre du tracé pour réduire les déplacements G0. "
              "S'applique à la prochaine génération du G-Code.",
        "en": "Optimize the drawing order to reduce G0 travel. Applies to the next G-Code generation.",
        "de": "Zeichenreihenfolge optimieren, um G0-Fahrten zu reduzieren. "
              "Gilt für die nächste G-Code-Generierung.",
        "es": "Optimizar el orden del trazado para reducir los desplazamientos G0. "
              "Se aplica a la próxima generación del G-Code.",
    },
    # --- Contrôle laser / USB / GRBL ---
    "laser.connect": {
        "fr": "Connecter GRBL",
        "en": "Connect GRBL",
        "de": "GRBL verbinden",
        "es": "Conectar GRBL",
    },
    "laser.disconnect": {
        "fr": "Déconnecter",
        "en": "Disconnect",
        "de": "Trennen",
        "es": "Desconectar",
    },
    "laser.connected": {
        "fr": "Connecté à {port} avec succès.",
        "en": "Successfully connected to {port}.",
        "de": "Erfolgreich mit {port} verbunden.",
        "es": "Conectado correctamente a {port}.",
    },
    "laser.disconnected": {
        "fr": "Déconnecté du port COM.",
        "en": "Disconnected from the COM port.",
        "de": "Vom COM-Port getrennt.",
        "es": "Desconectado del puerto COM.",
    },
        "laser.error": {
        "fr": "Erreur",
        "en": "Error",
        "de": "Fehler",
        "es": "Error",
    },
    "laser.connection_error": {
        "fr": "Échec de connexion sur {port}.",
        "en": "Connection failed on {port}.",
        "de": "Verbindung zu {port} fehlgeschlagen.",
        "es": "Error de conexión en {port}.",
    },
    "laser.usb_not_connected_title": {
        "fr": "USB non connecté",
        "en": "USB not connected",
        "de": "USB nicht verbunden",
        "es": "USB no conectado",
    },
    "laser.no_homing_title": {
        "fr": "Machine non référencée", "en": "Machine not homed",
        "de": "Maschine nicht referenziert", "es": "Máquina no referenciada",
    },
    "laser.no_homing_body": {
        "fr": "Aucun homing ($H) n'a été fait depuis la connexion à la machine.\n\nSans référence fiable, la position de la pièce gravée peut être décalée.\n\nContinuer quand même ?",
        "en": "No homing ($H) has been done since connecting to the machine.\n\nWithout a reliable reference, the engraved piece's position may be off.\n\nContinue anyway?",
        "de": "Seit der Verbindung mit der Maschine wurde kein Homing ($H) durchgeführt.\n\nOhne zuverlässige Referenz kann die Position des gravierten Teils verschoben sein.\n\nTrotzdem fortfahren?",
        "es": "No se ha realizado ningún homing ($H) desde la conexión con la máquina.\n\nSin una referencia fiable, la posición de la pieza grabada puede estar desplazada.\n\n¿Continuar de todos modos?",
    },
    "laser.reconnecting": {
        "fr": ">>> Connexion USB perdue — tentative de reconnexion automatique...",
        "en": ">>> USB connection lost — attempting automatic reconnection...",
        "de": ">>> USB-Verbindung verloren — automatischer Wiederverbindungsversuch...",
        "es": ">>> Conexión USB perdida — intentando reconectar automáticamente...",
    },
    "laser.reconnect_success": {
        "fr": ">>> Reconnexion USB réussie.",
        "en": ">>> USB reconnection successful.",
        "de": ">>> USB-Wiederverbindung erfolgreich.",
        "es": ">>> Reconexión USB exitosa.",
    },
    "laser.reconnect_success_title": {
        "fr": "Connexion rétablie", "en": "Connection restored",
        "de": "Verbindung wiederhergestellt", "es": "Conexión restablecida",
    },
    "laser.reconnect_success_body": {
        "fr": "La liaison USB a été rétablie automatiquement.\n\nLe job a été arrêté par sécurité : la position de la machine n'est plus fiable après une coupure. Vérifie la position et refais un homing ($H) avant de relancer.",
        "en": "The USB link was automatically restored.\n\nThe job was stopped for safety: the machine's position is no longer reliable after a disconnection. Check the position and re-home ($H) before restarting.",
        "de": "Die USB-Verbindung wurde automatisch wiederhergestellt.\n\nDer Job wurde aus Sicherheitsgründen gestoppt: Die Maschinenposition ist nach einer Unterbrechung nicht mehr zuverlässig. Position prüfen und vor dem Neustart erneut referenzieren ($H).",
        "es": "El enlace USB se restableció automáticamente.\n\nEl trabajo se detuvo por seguridad: la posición de la máquina ya no es fiable tras una desconexión. Verifica la posición y vuelve a hacer homing ($H) antes de reiniciar.",
    },
    "laser.reconnect_failed": {
        "fr": ">>> Échec de la reconnexion USB automatique.",
        "en": ">>> Automatic USB reconnection failed.",
        "de": ">>> Automatische USB-Wiederverbindung fehlgeschlagen.",
        "es": ">>> Falló la reconexión USB automática.",
    },
    "laser.reconnect_failed_title": {
        "fr": "Reconnexion impossible", "en": "Reconnection failed",
        "de": "Wiederverbindung nicht möglich", "es": "Reconexión imposible",
    },
    "laser.reconnect_failed_body": {
        "fr": "Impossible de rétablir la connexion USB après plusieurs tentatives.\n\nVérifie le câble, le port, et reconnecte-toi manuellement.",
        "en": "Could not restore the USB connection after several attempts.\n\nCheck the cable, the port, and reconnect manually.",
        "de": "Die USB-Verbindung konnte nach mehreren Versuchen nicht wiederhergestellt werden.\n\nKabel und Port prüfen und manuell erneut verbinden.",
        "es": "No se pudo restablecer la conexión USB tras varios intentos.\n\nRevisa el cable, el puerto, y reconéctate manualmente.",
    },
    "laser.connect_first": {
        "fr": "Connecte d'abord le laser.",
        "en": "Connect the laser first.",
        "de": "Verbinde zuerst den Laser.",
        "es": "Conecta primero el láser.",
    },
    "laser.connect_via_usb": {
        "fr": "Connecte le laser via USB.",
        "en": "Connect the laser via USB.",
        "de": "Verbinde den Laser über USB.",
        "es": "Conecta el láser mediante USB.",
    },
    "laser.no_port_title": {
        "fr": "Erreur",
        "en": "Error",
        "de": "Fehler",
        "es": "Error",
    },
    "laser.no_port": {
        "fr": "Aucun port COM sélectionné.",
        "en": "No COM port selected.",
        "de": "Kein COM-Port ausgewählt.",
        "es": "No hay ningún puerto COM seleccionado.",
    },
    "laser.usb_error_title": {
        "fr": "Erreur USB",
        "en": "USB Error",
        "de": "USB-Fehler",
        "es": "Error USB",
    },
    "laser.no_gcode": {
        "fr": "Aucun G-Code à envoyer.",
        "en": "No G-Code to send.",
        "de": "Kein G-Code zum Senden vorhanden.",
        "es": "No hay G-Code para enviar.",
    },
    "laser.confirm_title": {
        "fr": "Confirmer le lancement",
        "en": "Confirm Start",
        "de": "Start bestätigen",
        "es": "Confirmar inicio",
    },
    "laser.confirm_body": {
        "fr": "Le laser va démarrer.\n\nVérifie que :\n- la zone de travail est dégagée,\n- le capot/protection est en place,\n- tu portes une protection oculaire adaptée.\n\nLancer le job maintenant ?",
        "en": "The laser is about to start.\n\nMake sure that:\n"
              "- the work area is clear,\n"
              "- the cover/protection is in place,\n"
              "- you are wearing suitable eye protection.\n\n"
              "Start the job now?",
        "de": "Der Laser wird gestartet.\n\nStelle sicher, dass:\n"
              "- der Arbeitsbereich frei ist,\n"
              "- die Abdeckung/Schutzvorrichtung angebracht ist,\n"
              "- du geeigneten Augenschutz trägst.\n\n"
              "Job jetzt starten?",
        "es": "El láser va a iniciarse.\n\nComprueba que:\n"
              "- el área de trabajo está despejada,\n"
              "- la cubierta/protección está colocada,\n"
              "- llevas protección ocular adecuada.\n\n"
              "¿Iniciar el trabajo ahora?",
    },
    "laser.finished_title": {
        "fr": "Terminé",
        "en": "Finished",
        "de": "Fertig",
        "es": "Terminado",
    },
    "laser.finished": {
        "fr": "Envoi du G-Code au laser terminé avec succès.",
        "en": "G-Code successfully sent to the laser.",
        "de": "G-Code erfolgreich an den Laser gesendet.",
        "es": "G-Code enviado correctamente al láser.",
    },
    "laser.interrupted_title": {
        "fr": "Job interrompu",
        "en": "Job Interrupted",
        "de": "Job unterbrochen",
        "es": "Trabajo interrumpido",
    },
    "laser.interrupted": {
        "fr": "L'envoi du G-Code a été interrompu (erreur GRBL, alarme, perte de connexion ou arrêt manuel). Consulte la console avant de relancer.",
        "en": "G-Code transmission was interrupted (GRBL error, alarm, lost "
              "connection, or manual stop). Check the console before restarting.",
        "de": "Die G-Code-Übertragung wurde unterbrochen (GRBL-Fehler, Alarm, "
              "Verbindungsverlust oder manueller Stopp). Prüfe die Konsole vor "
              "einem Neustart.",
        "es": "El envío del G-Code se interrumpió (error GRBL, alarma, pérdida "
              "de conexión o parada manual). Consulta la consola antes de reiniciar.",
    },
    "laser.grbl_dynamic_off_title": {
        "fr": "Mode laser GRBL désactivé",
        "en": "GRBL Laser Mode Disabled",
        "de": "GRBL-Lasermodus deaktiviert",
        "es": "Modo láser GRBL desactivado",
    },
    "laser.grbl_dynamic_off": {
        "fr": "Le paramètre GRBL $32 (mode laser) n'est pas activé sur cette "
              "machine (valeur actuelle : {value}).\n\n"
              "Ce logiciel suppose ce mode activé : sans lui, le laser peut "
              "rester actif pendant les déplacements rapides (G0) dans certains "
              "G-Codes générés (mode M4), ce qui peut créer des marques de "
              "brûlure indésirables.\n\n"
              "Pour l'activer, envoie la commande $32=1 dans la console "
              "ci-dessous, puis $$ pour vérifier.",
        "en": "GRBL setting $32 (laser mode) is not enabled on this machine "
              "(current value: {value}).\n\n"
              "This software assumes that this mode is enabled. Without it, "
              "the laser may remain active during rapid moves (G0) in some "
              "generated G-Code files (M4 mode), causing unwanted burn marks.\n\n"
              "To enable it, send the $32=1 command in the console below, "
              "then send $$ to verify.",
        "de": "Die GRBL-Einstellung $32 (Lasermodus) ist auf dieser Maschine "
              "nicht aktiviert (aktueller Wert: {value}).\n\n"
              "Diese Software setzt voraus, dass dieser Modus aktiviert ist. "
              "Andernfalls kann der Laser bei schnellen Bewegungen (G0) in "
              "bestimmten G-Code-Dateien (M4-Modus) aktiv bleiben und "
              "unerwünschte Brandspuren verursachen.\n\n"
              "Sende zum Aktivieren den Befehl $32=1 in der Konsole und danach "
              "$$, um die Einstellung zu prüfen.",
        "es": "El ajuste GRBL $32 (modo láser) no está activado en esta máquina "
              "(valor actual: {value}).\n\n"
              "Este software supone que este modo está activado. Sin él, el "
              "láser puede permanecer activo durante los movimientos rápidos "
              "(G0) en algunos G-Codes generados (modo M4), causando marcas de "
              "quemado no deseadas.\n\n"
              "Para activarlo, envía el comando $32=1 en la consola y después "
              "$$ para comprobarlo.",
    },
    "laser.grbl_mode_unknown": {
        "fr": ">>> Impossible de vérifier le mode laser GRBL ($32) : "
              "réglage non trouvé dans la réponse de la machine.",
        "en": ">>> Unable to check GRBL laser mode ($32): setting not found "
              "in the machine response.",
        "de": ">>> GRBL-Lasermodus ($32) konnte nicht geprüft werden: Einstellung "
              "in der Maschinenantwort nicht gefunden.",
        "es": ">>> No se puede comprobar el modo láser GRBL ($32): ajuste no "
              "encontrado en la respuesta de la máquina.",
    },
    "laser.grbl_homing_disabled": {
        "fr": ">>> Homing désactivé sur la machine ($22=0) : « Inclure $H » a été décoché et grisé.",
        "en": ">>> Homing disabled on the machine ($22=0): \"Include $H\" has been unchecked and disabled.",
        "de": ">>> Homing an der Maschine deaktiviert ($22=0): „$H einbeziehen“ wurde abgewählt und gesperrt.",
        "es": ">>> Homing desactivado en la máquina ($22=0): «Incluir $H» se ha desmarcado y desactivado.",
    },
    "ui.homing_unavailable_tip": {
        "fr": "Le homing est désactivé sur la machine connectée ($22=0) : elle refuserait $H.",
        "en": "Homing is disabled on the connected machine ($22=0): it would reject $H.",
        "de": "Homing ist an der verbundenen Maschine deaktiviert ($22=0): sie würde $H ablehnen.",
        "es": "El homing está desactivado en la máquina conectada ($22=0): rechazaría $H.",
    },
    "ui.homing_unsupported_tip": {
        "fr": "Le graveur connecté ne renvoie pas le réglage de homing ($22) : homing non supporté.",
        "en": "The connected engraver does not report the homing setting ($22): homing not supported.",
        "de": "Der verbundene Graveur meldet die Homing-Einstellung ($22) nicht: Homing nicht unterstützt.",
        "es": "El grabador conectado no devuelve el ajuste de homing ($22): homing no compatible.",
    },
    "laser.homing_unsupported_title": {
        "fr": "Homing non supporté",
        "en": "Homing not supported",
        "de": "Homing nicht unterstützt",
        "es": "Homing no compatible",
    },
    "laser.homing_unsupported": {
        "fr": "Le homing n'est pas supporté par ce graveur : il est désactivé ($22=0) "
              "ou absent de sa configuration ($$). Il refuserait la commande $H.\n\n"
              "« Inclure $H » a été désactivé par défaut, et ce choix est enregistré "
              "dans le profil de la machine.",
        "en": "Homing is not supported by this engraver: it is disabled ($22=0) "
              "or missing from its configuration ($$). It would reject the $H command.\n\n"
              "\"Include $H\" has been disabled by default, and this choice is saved "
              "in the machine profile.",
        "de": "Homing wird von diesem Graveur nicht unterstützt: Es ist deaktiviert ($22=0) "
              "oder fehlt in seiner Konfiguration ($$). Er würde den Befehl $H ablehnen.\n\n"
              "„$H einbeziehen“ wurde standardmäßig deaktiviert, und diese Wahl ist "
              "im Maschinenprofil gespeichert.",
        "es": "Este grabador no admite el homing: está desactivado ($22=0) "
              "o no figura en su configuración ($$). Rechazaría el comando $H.\n\n"
              "«Incluir $H» se ha desactivado por defecto y esta elección se guarda "
              "en el perfil de la máquina.",
    },
    "laser.grbl_mode_missing_title": {
        "fr": "Mode laser inconnu",
        "en": "Unknown laser mode",
        "de": "Lasermodus unbekannt",
        "es": "Modo láser desconocido",
    },
    "laser.grbl_mode_missing": {
        "fr": "Le graveur ne renvoie pas le réglage $32 : impossible de vérifier que le "
              "mode laser est actif.\n\n"
              "Sans ce mode, en M4, le laser peut rester allumé pendant les déplacements "
              "rapides (G0) et laisser des traces de brûlure. Vérifie la documentation "
              "de ton graveur avant de lancer un job.",
        "en": "The engraver does not report the $32 setting: unable to check that "
              "laser mode is on.\n\n"
              "Without this mode, in M4, the laser may stay on during rapid moves (G0) "
              "and leave burn marks. Check your engraver's documentation before "
              "starting a job.",
        "de": "Der Graveur meldet die Einstellung $32 nicht: Es lässt sich nicht prüfen, "
              "ob der Lasermodus aktiv ist.\n\n"
              "Ohne diesen Modus kann der Laser in M4 bei Eilbewegungen (G0) eingeschaltet "
              "bleiben und Brandspuren hinterlassen. Prüfe die Dokumentation deines "
              "Graveurs, bevor du einen Auftrag startest.",
        "es": "El grabador no devuelve el ajuste $32: no se puede comprobar que el "
              "modo láser esté activo.\n\n"
              "Sin este modo, en M4, el láser puede quedar encendido durante los "
              "desplazamientos rápidos (G0) y dejar marcas de quemado. Consulta la "
              "documentación de tu grabador antes de lanzar un trabajo.",
    },
    "laser.grbl_no_answer_title": {
        "fr": "Le graveur ne répond pas",
        "en": "The engraver does not answer",
        "de": "Der Graveur antwortet nicht",
        "es": "El grabador no responde",
    },
    "laser.grbl_no_answer": {
        "fr": "Le port {port} est ouvert, mais aucun graveur GRBL n'y répond.\n\n"
              "Vérifie que le graveur est allumé et branché, et que le bon port est "
              "choisi dans la liste (en général /dev/ttyUSB… ou /dev/ttyACM… sous "
              "Linux, COM… sous Windows). Rien ne sera gravé tant qu'il ne répond pas.",
        "en": "Port {port} is open, but no GRBL engraver answers on it.\n\n"
              "Check that the engraver is switched on and plugged in, and that the right "
              "port is selected in the list (usually /dev/ttyUSB… or /dev/ttyACM… on "
              "Linux, COM… on Windows). Nothing will be engraved until it answers.",
        "de": "Der Port {port} ist geöffnet, aber kein GRBL-Graveur antwortet.\n\n"
              "Prüfe, ob der Graveur eingeschaltet und angeschlossen ist und der richtige "
              "Port in der Liste gewählt ist (meist /dev/ttyUSB… oder /dev/ttyACM… unter "
              "Linux, COM… unter Windows). Solange er nicht antwortet, wird nichts graviert.",
        "es": "El puerto {port} está abierto, pero ningún grabador GRBL responde.\n\n"
              "Comprueba que el grabador está encendido y conectado, y que el puerto "
              "elegido en la lista es el correcto (normalmente /dev/ttyUSB… o /dev/ttyACM… "
              "en Linux, COM… en Windows). No se grabará nada mientras no responda.",
    },
    "laser.grbl_mode_status": {
        "fr": ">>> Mode laser GRBL ($32) : {value}",
        "en": ">>> GRBL laser mode ($32): {value}",
        "de": ">>> GRBL-Lasermodus ($32): {value}",
        "es": ">>> Modo láser GRBL ($32): {value}",
    },
    "laser.pause_log": {
        "fr": ">>> Commande Temps Réel: PAUSE (!)",
        "en": ">>> Real-Time Command: PAUSE (!)",
        "de": ">>> Echtzeitbefehl: PAUSE (!)",
        "es": ">>> Comando en tiempo real: PAUSA (!)",
    },
    "laser.unlock_log": {
        "fr": ">>> Déverrouillage ($X) envoyé",
        "en": ">>> Unlock ($X) sent",
        "de": ">>> Entsperren ($X) gesendet",
        "es": ">>> Desbloqueo ($X) enviado",
    },
    "laser.resume_log": {
        "fr": ">>> Commande Temps Réel: REPRISE (~)",
        "en": ">>> Real-Time Command: RESUME (~)",
        "de": ">>> Echtzeitbefehl: FORTSETZEN (~)",
        "es": ">>> Comando en tiempo real: REANUDAR (~)",
    },
    "laser.reset_log": {
        "fr": ">>> Commande Temps Réel: RESET (Ctrl+X)",
        "en": ">>> Real-Time Command: RESET (Ctrl+X)",
        "de": ">>> Echtzeitbefehl: RESET (Strg+X)",
        "es": ">>> Comando en tiempo real: RESET (Ctrl+X)",
    },
    "laser.kill_log": {
        "fr": ">>> ARRÊT D'URGENCE (KILL / RESET envoyé)",
        "en": ">>> EMERGENCY STOP (KILL / RESET sent)",
        "de": ">>> NOT-AUS (KILL / RESET gesendet)",
        "es": ">>> PARADA DE EMERGENCIA (KILL / RESET enviado)",
    },
    "laser.error_stop_log": {
        "fr": ">>> Erreur GRBL : machine arrêtée (pause puis reset) pour ne pas exécuter la suite déjà envoyée.",
        "en": ">>> GRBL error: machine stopped (hold then reset) so the lines already sent are not executed.",
        "de": ">>> GRBL-Fehler: Maschine gestoppt (Halt, dann Reset), damit die bereits gesendeten Zeilen nicht ausgeführt werden.",
        "es": ">>> Error de GRBL: máquina detenida (pausa y luego reset) para no ejecutar las líneas ya enviadas.",
    },
    "laser.position_lost_log": {
        "fr": ">>> Reset en dehors de l'arrêt complet : position machine probablement perdue, un nouveau homing sera proposé avant le prochain job.",
        "en": ">>> Reset while not fully stopped: machine position probably lost, a new homing will be offered before the next job.",
        "de": ">>> Reset ohne vollständigen Stillstand: Maschinenposition wahrscheinlich verloren, vor dem nächsten Job wird ein neues Homing angeboten.",
        "es": ">>> Reset sin parada completa: posición de la máquina probablemente perdida, se propondrá un nuevo homing antes del próximo trabajo.",
    },
    # --- Profils machine et matériaux ---
    "machine.new_title": {
        "fr": "Nouvelle Machine",
        "en": "New Machine",
        "de": "Neue Maschine",
        "es": "Nueva máquina",
    },
    "machine.new_prompt": {
        "fr": "Nom de la machine :",
        "en": "Machine name:",
        "de": "Name der Maschine:",
        "es": "Nombre de la máquina:",
    },
    "machine.updated_title": {
        "fr": "Profil mis à jour",
        "en": "Profile Updated",
        "de": "Profil aktualisiert",
        "es": "Perfil actualizado",
    },
    "machine.updated_body": {
        "fr": "Le profil « {name} » a été mis à jour avec les réglages actuels "
              "(dimensions, origine, limites, G-Code début/fin).",
        "en": "Profile “{name}” has been updated with the current settings "
              "(dimensions, origin, limits, start/end G-Code).",
        "de": "Das Profil „{name}“ wurde mit den aktuellen Einstellungen "
              "(Abmessungen, Ursprung, Grenzen, Start-/End-G-Code) aktualisiert.",
        "es": "El perfil «{name}» se ha actualizado con los ajustes actuales "
              "(dimensiones, origen, límites y G-Code inicial/final).",
    },
    "machine.cannot_delete_title": {
        "fr": "Impossible",
        "en": "Not Possible",
        "de": "Nicht möglich",
        "es": "No es posible",
    },
    "machine.cannot_delete_body": {
        "fr": "Il doit rester au moins un profil de machine.",
        "en": "At least one machine profile must remain.",
        "de": "Mindestens ein Maschinenprofil muss erhalten bleiben.",
        "es": "Debe quedar al menos un perfil de máquina.",
    },
    "machine.delete_title": {
        "fr": "Supprimer le profil",
        "en": "Delete Profile",
        "de": "Profil löschen",
        "es": "Eliminar perfil",
    },
    "machine.delete_body": {
        "fr": "Supprimer le profil « {name} » ?",
        "en": "Delete profile “{name}”?",
        "de": "Profil „{name}“ löschen?",
        "es": "¿Eliminar el perfil «{name}»?",
    },

    "material.export_title": {
        "fr": "Exporter les profils matériaux",
        "en": "Export Material Profiles",
        "de": "Materialprofile exportieren",
        "es": "Exportar perfiles de materiales",
    },
    "material.import_title": {
        "fr": "Importer des profils matériaux",
        "en": "Import Material Profiles",
        "de": "Materialprofile importieren",
        "es": "Importar perfiles de materiales",
    },
    "material.export_success_title": {
        "fr": "Export réussi",
        "en": "Export Successful",
        "de": "Export erfolgreich",
        "es": "Exportación correcta",
    },
    "material.export_success_body": {
        "fr": "{count} profil(s) exporté(s) vers :\n{path}",
        "en": "{count} profile(s) exported to:\n{path}",
        "de": "{count} Profil(e) exportiert nach:\n{path}",
        "es": "{count} perfil(es) exportado(s) a:\n{path}",
    },
    "material.import_success_title": {
        "fr": "Import réussi",
        "en": "Import Successful",
        "de": "Import erfolgreich",
        "es": "Importación correcta",
    },
    "material.import_success_body": {
        "fr": "{added} profil(s) ajouté(s), {updated} mis à jour.",
        "en": "{added} profile(s) added, {updated} updated.",
        "de": "{added} Profil(e) hinzugefügt, {updated} aktualisiert.",
        "es": "{added} perfil(es) añadido(s), {updated} actualizado(s).",
    },
    "material.saved_title": {
        "fr": "Profil enregistré",
        "en": "Profile Saved",
        "de": "Profil gespeichert",
        "es": "Perfil guardado",
    },
    "material.saved_body": {
        "fr": "Les paramètres pour « {name} » ont été sauvegardés.",
        "en": "The settings for “{name}” have been saved.",
        "de": "Die Einstellungen für „{name}“ wurden gespeichert.",
        "es": "Los ajustes de «{name}» se han guardado.",
    },
    "material.new_profile_title": {
        "fr": "Nouveau profil",
        "en": "New Profile",
        "de": "Neues Profil",
        "es": "Nuevo perfil",
    },
    "material.new_profile_prompt": {
        "fr": "Nom du matériau :",
        "en": "Material name:",
        "de": "Materialname:",
        "es": "Nombre del material:",
    },
    "material.delete_forbidden_title": {
        "fr": "Action interdite",
        "en": "Action Not Allowed",
        "de": "Aktion nicht erlaubt",
        "es": "Acción no permitida",
    },
    "material.delete_forbidden_body": {
        "fr": "Le profil par défaut ne peut pas être supprimé.",
        "en": "The default profile cannot be deleted.",
        "de": "Das Standardprofil kann nicht gelöscht werden.",
        "es": "El perfil predeterminado no se puede eliminar.",
    },
    "material.delete_title": {
        "fr": "Suppression",
        "en": "Delete",
        "de": "Löschen",
        "es": "Eliminar",
    },
    "material.delete_body": {
        "fr": "Supprimer le profil « {name} » ?",
        "en": "Delete profile “{name}”?",
        "de": "Profil „{name}“ löschen?",
        "es": "¿Eliminar el perfil «{name}»?",
    },
    "material.invalid_file": {
        "fr": "Le fichier ne contient pas un dictionnaire de profils valide.",
        "en": "The file does not contain a valid profile dictionary.",
        "de": "Die Datei enthält kein gültiges Profilwörterbuch.",
        "es": "El archivo no contiene un diccionario válido de perfiles.",
    },
    "material.error_export": {
        "fr": "Impossible d'exporter les profils :\n{error}",
        "en": "Unable to export profiles:\n{error}",
        "de": "Profile konnten nicht exportiert werden:\n{error}",
        "es": "No se pueden exportar los perfiles:\n{error}",
    },
    "material.error_import": {
        "fr": "Impossible d'importer ce fichier :\n{error}",
        "en": "Unable to import this file:\n{error}",
        "de": "Diese Datei konnte nicht importiert werden:\n{error}",
        "es": "No se puede importar este archivo:\n{error}",
    },
    # --- Projets ---
    "project.save_title": {
        "fr": "Sauvegarder Projet Laser",
        "en": "Save Laser Project",
        "de": "Laserprojekt speichern",
        "es": "Guardar proyecto láser",
    },
    "project.file_filter": {
        "fr": "Projet Laser (*.json)",
        "en": "Laser Project (*.json)",
        "de": "Laserprojekt (*.json)",
        "es": "Proyecto láser (*.json)",
    },
    "project.save_success_title": {
        "fr": "Sauvegarde",
        "en": "Save",
        "de": "Speichern",
        "es": "Guardado",
    },
    "project.save_success": {
        "fr": "Projet sauvegardé avec succès.",
        "en": "Project saved successfully.",
        "de": "Projekt erfolgreich gespeichert.",
        "es": "Proyecto guardado correctamente.",
    },
    "project.save_error": {
        "fr": "Impossible de sauvegarder le projet :\n{error}",
        "en": "Unable to save the project:\n{error}",
        "de": "Das Projekt konnte nicht gespeichert werden:\n{error}",
        "es": "No se puede guardar el proyecto:\n{error}",
    },
    "project.open_title": {
        "fr": "Ouvrir Projet Laser",
        "en": "Open Laser Project",
        "de": "Laserprojekt öffnen",
        "es": "Abrir proyecto láser",
    },
    "project.load_success_title": {
        "fr": "Succès",
        "en": "Success",
        "de": "Erfolg",
        "es": "Éxito",
    },
    "project.load_success": {
        "fr": "Projet chargé avec succès.",
        "en": "Project loaded successfully.",
        "de": "Projekt erfolgreich geladen.",
        "es": "Proyecto cargado correctamente.",
    },
    "project.load_error": {
        "fr": "Échec du chargement du projet :\n{error}",
        "en": "Failed to load the project:\n{error}",
        "de": "Das Projekt konnte nicht geladen werden:\n{error}",
        "es": "Error al cargar el proyecto:\n{error}",
    },
    "project.no_recent": {
        "fr": "(aucun)",
        "en": "(none)",
        "de": "(keine)",
        "es": "(ninguno)",
    },
    "project.autosave_recovery_title": {
        "fr": "Récupération de session",
        "en": "Session Recovery",
        "de": "Sitzungswiederherstellung",
        "es": "Recuperación de sesión",
    },
    "project.autosave_recovery_body": {
        "fr": "Une sauvegarde automatique d'une session précédente a été trouvée "
              "(probablement suite à une fermeture inattendue).\n\n"
              "Veux-tu la récupérer ?",
        "en": "An automatic save from a previous session was found "
              "(probably after an unexpected shutdown).\n\n"
              "Would you like to recover it?",
        "de": "Eine automatische Sicherung einer vorherigen Sitzung wurde gefunden "
              "(wahrscheinlich nach einem unerwarteten Beenden).\n\n"
              "Möchtest du sie wiederherstellen?",
        "es": "Se encontró un guardado automático de una sesión anterior "
              "(probablemente después de un cierre inesperado).\n\n"
              "¿Quieres recuperarlo?",
    },
    # --- File d'attente ---
    "queue.no_gcode": {
        "fr": "Aucun G-Code à ajouter (génère d'abord un job).",
        "en": "No G-Code to add (generate a job first).",
        "de": "Kein G-Code zum Hinzufügen (erst einen Job erzeugen).",
        "es": "No hay G-Code para añadir (primero genera un trabajo).",
    },
    "queue.empty_title": {
        "fr": "File d'attente",
        "en": "Job Queue",
        "de": "Auftragswarteschlange",
        "es": "Cola de trabajos",
    },
    "queue.empty_body": {
        "fr": "La file est vide.",
        "en": "The queue is empty.",
        "de": "Die Warteschlange ist leer.",
        "es": "La cola está vacía.",
    },
    "queue.usb_error": {
        "fr": "Erreur USB",
        "en": "USB Error",
        "de": "USB-Fehler",
        "es": "Error USB",
    },
    "queue.usb_connect": {
        "fr": "Connecte le laser en USB.",
        "en": "Please connect the laser via USB.",
        "de": "Bitte verbinde den Laser per USB.",
        "es": "Por favor, conecta el láser por USB.",
    },
    "queue.confirm_title": {
        "fr": "Lancer la file d'attente",
        "en": "Start Job Queue",
        "de": "Warteschlange starten",
        "es": "Iniciar cola de trabajos",
    },
    "queue.confirm_body": {
        "fr": "{count} job(s) vont être envoyés l'un après l'autre.\n\n"
              "Vérifie que :\n"
              "- la zone de travail est dégagée entre chaque pièce,\n"
              "- le capot/protection est en place,\n"
              "- tu portes une protection oculaire adaptée.\n\n"
              "Lancer la file maintenant ?",
        "en": "{count} job(s) will be sent one after another.\n\n"
              "Make sure that:\n"
              "- the work area is clear between each piece,\n"
              "- the cover/protection is in place,\n"
              "- you are wearing suitable eye protection.\n\n"
              "Start the queue now?",
        "de": "{count} Job(s) werden nacheinander gesendet.\n\n"
              "Vergewissere dich, dass:\n"
              "- der Arbeitsbereich zwischen den einzelnen Teilen frei ist,\n"
              "- die Abdeckung/Schutzvorrichtung sitzt,\n"
              "- du geeigneten Augenschutz trägst.\n\n"
              "Warteschlange jetzt starten?",
        "es": "Se enviarán {count} trabajo(s) uno tras otro.\n\n"
              "Comprueba que:\n"
              "- el área de trabajo está despejada entre cada pieza,\n"
              "- la cubierta/protección está colocada,\n"
              "- llevas protección ocular adecuada.\n\n"
              "¿Iniciar la cola ahora?",
    },
    "queue.done_title": {
        "fr": "File d'attente terminée",
        "en": "Queue Finished",
        "de": "Warteschlange beendet",
        "es": "Cola finalizada",
    },
    "queue.done_body": {
        "fr": "Tous les jobs de la file ont été envoyés.",
        "en": "All jobs in the queue have been sent.",
        "de": "Alle Jobs in der Warteschlange wurden gesendet.",
        "es": "Todos los trabajos de la cola han sido enviados.",
    },
    "queue.finished_log": {
        "fr": ">>> File d'attente terminée.",
        "en": ">>> Queue finished.",
        "de": ">>> Warteschlange beendet.",
        "es": ">>> Cola finalizada.",
    },
    "queue.job_log": {
        "fr": ">>> File d'attente : envoi de « {name} » ({index}/{total})",
        "en": ">>> Queue: sending “{name}” ({index}/{total})",
        "de": ">>> Warteschlange: Senden von „{name}“ ({index}/{total})",
        "es": ">>> Cola: enviando «{name}» ({index}/{total})",
    },
    "queue.status_empty": {
        "fr": "File vide.",
        "en": "Queue empty.",
        "de": "Warteschlange leer.",
        "es": "Cola vacía.",
    },
    "queue.status_count": {
        "fr": "{count} job(s) en file.",
        "en": "{count} job(s) in queue.",
        "de": "{count} Job(s) in der Warteschlange.",
        "es": "{count} trabajo(s) en cola.",
    },
    "queue.in_progress": {
        "fr": "Envoi en cours : {name} ({index}/{total})",
        "en": "Sending: {name} ({index}/{total})",
        "de": "Senden: {name} ({index}/{total})",
        "es": "Enviando: {name} ({index}/{total})",
    },
    "queue.stopped_title": {
        "fr": "File d'attente interrompue",
        "en": "Queue Interrupted",
        "de": "Warteschlange unterbrochen",
        "es": "Cola interrumpida",
    },
    "queue.stopped_body": {
        "fr": "Un job de la file a été interrompu (erreur GRBL, alarme, perte de "
              "connexion ou arrêt manuel). La file est arrêtée — consulte la "
              "console avant de relancer.",
        "en": "A queued job was interrupted (GRBL error, alarm, lost connection, "
              "or manual stop). The queue has stopped — check the console before "
              "restarting.",
        "de": "Ein Job in der Warteschlange wurde unterbrochen (GRBL-Fehler, Alarm, "
              "Verbindungsabbruch oder manueller Stopp). Die Warteschlange wurde "
              "gestoppt — prüfe die Konsole, bevor du erneut startest.",
        "es": "Un trabajo de la cola fue interrumpido (error GRBL, alarma, pérdida "
              "de conexión o parada manual). La cola se ha detenido — consulta la "
              "consola antes de reiniciar.",
    },
    "ui.window_title": {
        "fr": "Laser Studio Pro - Contrôleur GRBL", "en": "Laser Studio Pro - GRBL Controller",
        "de": "Laser Studio Pro - GRBL-Steuerung", "es": "Laser Studio Pro - Controlador GRBL",
    },
    "ui.quit_title": {
        "fr": "Quitter",
        "en": "Exit",
        "de": "Beenden",
        "es": "Salir",
    },
    "ui.quit_save_prompt": {
        "fr": "Veux-tu sauvegarder le projet avant de fermer ?",
        "en": "Do you want to save the project before closing?",
        "de": "Möchtest du das Projekt vor dem Schließen speichern?",
        "es": "¿Quieres guardar el proyecto antes de cerrar?",
    },
    "ui.about_title": {
        "fr": "À propos de Laser Studio Pro",
        "en": "About Laser Studio Pro",
        "de": "Über Laser Studio Pro",
        "es": "Acerca de Laser Studio Pro",
    },
    "ui.support_title": {
        "fr": "Support",
        "en": "Support",
        "de": "Support",
        "es": "Soporte",
    },
    "ui.coffee_title": {
        "fr": "Buy me a coffee",
        "en": "Buy me a coffee",
        "de": "Buy me a coffee",
        "es": "Buy me a coffee",
    },
    "ui.banner_unreadable": {
        "fr": "(Image trouvée mais illisible : {path})",
        "en": "(Image found but unreadable: {path})",
        "de": "(Bild gefunden, aber nicht lesbar: {path})",
        "es": "(Se encontró la imagen pero no se pudo leer: {path})",
    },
    "ui.banner_missing": {
        "fr": "(Bannière introuvable, cherchée ici :\n{paths})",
        "en": "(Banner not found, searched here:\n{paths})",
        "de": "(Banner nicht gefunden, gesucht in:\n{paths})",
        "es": "(No se encontró el banner, buscado aquí:\n{paths})",
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
    # --- Éditeur vectoriel ---
    "vector.no_layer_title": {
        "fr": "Aucun calque",
        "en": "No Layer",
        "de": "Keine Ebene",
        "es": "Ninguna capa",
    },
    "vector.no_layer_body": {
        "fr": "Crée d'abord un calque dans l'onglet 'Calques (Layers)'.",
        "en": "Create a layer first in the 'Layers' tab.",
        "de": "Erstelle zuerst eine Ebene im Reiter „Ebenen“.",
        "es": "Crea primero una capa en la pestaña «Capas».",
    },
    "vector.selection_title": {
        "fr": "Sélection",
        "en": "Selection",
        "de": "Auswahl",
        "es": "Selección",
    },
    "vector.no_selection": {
        "fr": "Sélectionne d'abord un objet dans le canevas.",
        "en": "Select an object in the canvas first.",
        "de": "Wähle zuerst ein Objekt auf der Zeichenfläche aus.",
        "es": "Selecciona primero un objeto en el lienzo.",
    },
    "vector.no_selection_label": {
        "fr": "Aucune sélection",
        "en": "No selection",
        "de": "Keine Auswahl",
        "es": "Ninguna selección",
    },
    "vector.svg_properties": {
        "fr": "Propriétés de l'élément SVG (calque, taille)",
        "en": "SVG Element Properties (layer, size)",
        "de": "Eigenschaften des SVG-Elements (Ebene, Größe)",
        "es": "Propiedades del elemento SVG (capa, tamaño)",
    },
    "vector.fullscreen_title": {
        "fr": "Graver une image vectorielle — Plein écran",
        "en": "Engrave a Vector Image — Full Screen",
        "de": "Vektorbild gravieren — Vollbild",
        "es": "Grabar una imagen vectorial — Pantalla completa",
    },
    "vector.close_fullscreen": {
        "fr": "✕ Fermer le plein écran (retour à la fenêtre normale)",
        "en": "✕ Exit full screen (return to normal window)",
        "de": "✕ Vollbild schließen (zum normalen Fenster zurückkehren)",
        "es": "✕ Cerrar pantalla completa (volver a la ventana normal)",
    },
    "vector.import_title": {
        "fr": "Importer un SVG ou un DXF (multi-calques)",
        "en": "Import SVG or DXF (multi-layer)",
        "de": "SVG oder DXF importieren (mehrere Ebenen)",
        "es": "Importar SVG o DXF (multicapa)",
    },
    "vector.svg_error_title": {
        "fr": "Erreur d'import SVG",
        "en": "SVG Import Error",
        "de": "SVG-Importfehler",
        "es": "Error de importación SVG",
    },
    "vector.svg_error": {
        "fr": "Impossible d'importer ce fichier :\n{error}",
        "en": "Unable to import this file:\n{error}",
        "de": "Diese Datei konnte nicht importiert werden:\n{error}",
        "es": "No se puede importar este archivo:\n{error}",
    },
    "vector.svg_empty_title": {
        "fr": "Import SVG",
        "en": "SVG Import",
        "de": "SVG-Import",
        "es": "Importación SVG",
    },
    "vector.svg_empty": {
        "fr": "Aucun élément exploitable n'a été trouvé dans ce fichier.",
        "en": "No usable element was found in this file.",
        "de": "In dieser Datei wurde kein verwendbares Element gefunden.",
        "es": "No se encontró ningún elemento utilizable en este archivo.",
    },
    "vector.svg_success_title": {
        "fr": "Import SVG réussi",
        "en": "SVG Import Successful",
        "de": "SVG-Import erfolgreich",
        "es": "Importación SVG correcta",
    },
    "vector.svg_success": {
        "fr": "{count} objet(s) importé(s) dans l'éditeur vectoriel (groupé), "
              "assigné(s) au calque « {layer} ».\n\n"
              "Pour séparer les tracés : clic droit → Dégrouper, puis assigne "
              "chaque partie au calque souhaité.",
        "en": "{count} object(s) imported into the vector editor (grouped), "
              "assigned to layer “{layer}”.\n\n"
              "To split the paths: right-click → Ungroup, then assign each "
              "part to the desired layer.",
        "de": "{count} Objekt(e) in den Vektor-Editor importiert (gruppiert) und "
              "der Ebene „{layer}“ zugewiesen.\n\n"
              "Zum Trennen der Pfade: Rechtsklick → Gruppierung aufheben, dann "
              "jede Teilform einer Ebene zuweisen.",
        "es": "{count} objeto(s) importado(s) en el editor vectorial (agrupado) y "
              "asignado(s) a la capa «{layer}».\n\n"
              "Para separar los trazos: clic derecho → Desagrupar, luego asigna "
              "cada parte a la capa deseada.",
    },
    "vector.no_engrave_layer": {
        "fr": "Aucun calque en mode Gravure : l'image utilisera les réglages du calque sélectionné.",
        "en": "No layer in Engrave mode: the image will use the settings of the selected layer.",
        "de": "Keine Ebene im Gravurmodus: Das Bild verwendet die Einstellungen der ausgewählten Ebene.",
        "es": "Ninguna capa en modo Grabado: la imagen usará los ajustes de la capa seleccionada.",
    },
    "vector.engrave_layer_auto": {
        "fr": "Image : calque de gravure « {name} » sélectionné automatiquement.",
        "en": "Image: engraving layer \"{name}\" selected automatically.",
        "de": "Bild: Gravurebene „{name}“ automatisch ausgewählt.",
        "es": "Imagen: capa de grabado «{name}» seleccionada automáticamente.",
    },
    "tab.vector_editor": {
        "fr": "Graver une image vectorielle",
        "en": "Engrave a Vector Image",
        "de": "Vektorbild gravieren",
        "es": "Grabar una imagen vectorial",
    },
    # --- Génération et export G-Code ---
    "gcode.empty_title": {
        "fr": "G-Code vide",
        "en": "Empty G-Code",
        "de": "Leerer G-Code",
        "es": "G-Code vacío",
    },
    "gcode.empty_export": {
        "fr": "Génère d'abord le job G-Code avant de l'exporter.",
        "en": "Generate the G-Code job before exporting it.",
        "de": "Generiere zuerst den G-Code-Job, bevor du ihn exportierst.",
        "es": "Genera primero el trabajo G-Code antes de exportarlo.",
    },
    "gcode.export_title": {
        "fr": "Exporter au format {extension}",
        "en": "Export as {extension}",
        "de": "Als {extension} exportieren",
        "es": "Exportar como {extension}",
    },
    "gcode.file_filter": {
        "fr": "Fichier (*{extension})",
        "en": "File (*{extension})",
        "de": "Datei (*{extension})",
        "es": "Archivo (*{extension})",
    },
    "gcode.export_success_title": {
        "fr": "Exportation réussie",
        "en": "Export Successful",
        "de": "Export erfolgreich",
        "es": "Exportación correcta",
    },
    "gcode.export_success": {
        "fr": "Le fichier a été enregistré :\n{path}",
        "en": "The file was saved:\n{path}",
        "de": "Die Datei wurde gespeichert:\n{path}",
        "es": "El archivo se guardó en:\n{path}",
    },
    "gcode.export_error_title": {
        "fr": "Erreur d'exportation",
        "en": "Export Error",
        "de": "Exportfehler",
        "es": "Error de exportación",
    },
    "gcode.export_error": {
        "fr": "Impossible de sauvegarder le fichier :\n{error}",
        "en": "Unable to save the file:\n{error}",
        "de": "Die Datei konnte nicht gespeichert werden:\n{error}",
        "es": "No se puede guardar el archivo:\n{error}",
    },
    "gcode.estimate_title": {
        "fr": "Estimation",
        "en": "Estimate",
        "de": "Schätzung",
        "es": "Estimación",
    },
    "gcode.nothing_to_estimate": {
        "fr": "Rien à estimer : charge une image, un SVG ou ajoute des objets vectoriels.",
        "en": "Nothing to estimate: load an image or SVG, or add vector objects.",
        "de": "Nichts zu schätzen: Lade ein Bild oder SVG oder füge Vektorobjekte hinzu.",
        "es": "Nada que estimar: carga una imagen o SVG, o añade objetos vectoriales.",
    },
    "gcode.estimate_title_full": {
        "fr": "Estimation du temps de gravure",
        "en": "Engraving Time Estimate",
        "de": "Schätzung der Gravurzeit",
        "es": "Estimación del tiempo de grabado",
    },
    "gcode.image_details": {
        "fr": "Gravure image : {duration}",
        "en": "Image engraving: {duration}",
        "de": "Bildgravur: {duration}",
        "es": "Grabado de imagen: {duration}",
    },
    "gcode.svg_details": {
        "fr": "Découpe SVG importée : {duration}",
        "en": "Imported SVG cutting: {duration}",
        "de": "Importierter SVG-Schnitt: {duration}",
        "es": "Corte SVG importado: {duration}",
    },
    "gcode.layer_details": {
        "fr": "Calque « {name} » : {duration}",
        "en": "Layer “{name}”: {duration}",
        "de": "Ebene „{name}“: {duration}",
        "es": "Capa «{name}»: {duration}",
    },
    "gcode.estimate_details": {
        "fr": "Estimation RAPIDE (approximative, sans générer le G-Code complet) :\n\n{details}\n\n"
              "TOTAL estimé : {total}\n\n"
              "(Ignore les accélérations/décélérations et les déplacements rapides G0 — "
              "le temps réel sera généralement un peu supérieur à cette estimation.)",
        "en": "QUICK estimate (approximate, without generating the complete G-Code):\n\n{details}\n\n"
              "Estimated TOTAL: {total}\n\n"
              "(Acceleration/deceleration and rapid G0 moves are ignored — the actual time "
              "will generally be slightly longer.)",
        "de": "SCHNELLE Schätzung (ungefähr, ohne vollständige G-Code-Erzeugung):\n\n{details}\n\n"
              "Geschätzte GESAMTZEIT: {total}\n\n"
              "(Beschleunigungen/Verzögerungen und schnelle G0-Bewegungen werden ignoriert.)",
        "es": "Estimación RÁPIDA (aproximada, sin generar el G-Code completo):\n\n{details}\n\n"
              "TOTAL estimado: {total}\n\n"
              "(Ignora aceleraciones/desaceleraciones y movimientos rápidos G0.)",
    },
    "gcode.import_title": {
        "fr": "Importer un G-Code",
        "en": "Import G-Code",
        "de": "G-Code importieren",
        "es": "Importar G-Code",
    },
    "gcode.import_filter": {
        "fr": "Fichiers G-Code (*.gcode *.nc *.ngc *.txt *.tap);;Tous les fichiers (*.*)",
        "en": "G-Code Files (*.gcode *.nc *.ngc *.txt *.tap);;All files (*.*)",
        "de": "G-Code-Dateien (*.gcode *.nc *.ngc *.txt *.tap);;Alle Dateien (*.*)",
        "es": "Archivos G-Code (*.gcode *.nc *.ngc *.txt *.tap);;Todos los archivos (*.*)",
    },
    "gcode.import_error": {
        "fr": "Impossible de lire le fichier :\n{error}",
        "en": "Unable to read the file:\n{error}",
        "de": "Die Datei konnte nicht gelesen werden:\n{error}",
        "es": "No se puede leer el archivo:\n{error}",
    },
    "gcode.imported_from": {
        "fr": "\n; --- Importé depuis : {path} ---",
        "en": "\n; --- Imported from: {path} ---",
        "de": "\n; --- Importiert aus: {path} ---",
        "es": "\n; --- Importado desde: {path} ---",
    },
    "ui.tab_image_tracing": {
        "fr": "Graver une image",
        "en": "Engrave an Image",
        "de": "Bild gravieren",
        "es": "Grabar una imagen",
    },
    "ui.tab_vector_editor": {
        "fr": "Graver une image vectorielle",
        "en": "Engrave a Vector Image",
        "de": "Vektorbild gravieren",
        "es": "Grabar una imagen vectorial",
    },
    "ui.tab_2d_preview": {
        "fr": "Visualisation 2D G-Code",
        "en": "2D G-Code Preview",
        "de": "2D-G-Code-Vorschau",
        "es": "Vista previa 2D del G-Code",
    },
    "ui.source_image_box": {
        "fr": "Image Originale (Glisse pour déplacer, molette pour zoomer)",
        "en": "Original Image (Drag to move, mouse wheel to zoom)",
        "de": "Originalbild (ziehen zum Bewegen, Mausrad zum Zoomen)",
        "es": "Imagen original (arrastra para mover, rueda del ratón para ampliar)",
    },
    "ui.final_raster_box": {
        "fr": "Rendu Tramé Final (Glisse pour déplacer, molette pour zoomer)",
        "en": "Final Rasterized Output (Drag to move, mouse wheel to zoom)",
        "de": "Finales gerastertes Ergebnis (ziehen zum Bewegen, Mausrad zum Zoomen)",
        "es": "Salida raster final (arrastra para mover, rueda del ratón para ampliar)",
    },
    "ui.selection_props_box": {
        "fr": "Propriétés de l'objet sélectionné",
        "en": "Selected Object Properties",
        "de": "Eigenschaften des ausgewählten Objekts",
        "es": "Propiedades del objeto seleccionado",
    },
    "ui.no_selection_label": {
        "fr": "Aucune sélection",
        "en": "No selection",
        "de": "Keine Auswahl",
        "es": "Ninguna selección",
    },
    "ui.vector_add_text": {
        "fr": "+ Texte",
        "en": "+ Text",
        "de": "+ Text",
        "es": "+ Texto",
    },
    "ui.vector_add_shape": {
        "fr": "+ Forme",
        "en": "+ Shape",
        "de": "+ Form",
        "es": "+ Forma",
    },
    "ui.vector_tool_select": {
        "fr": "Sélection",
        "en": "Select",
        "de": "Auswahl",
        "es": "Selección",
    },
    "ui.vector_tool_select_tip": {
        "fr": "Outil sélection (déplacer, sélection multiple)",
        "en": "Selection tool (move, multi-select)",
        "de": "Auswahlwerkzeug (verschieben, Mehrfachauswahl)",
        "es": "Herramienta de selección (mover, selección múltiple)",
    },
    "ui.vector_tool_line": {
        "fr": "Ligne",
        "en": "Line",
        "de": "Linie",
        "es": "Línea",
    },
    "ui.vector_tool_line_tip": {
        "fr": "Tracer une ligne : clic-glisser sur le canevas (Échap pour annuler)",
        "en": "Draw a line: click-drag on the canvas (Esc to cancel)",
        "de": "Linie zeichnen: Klicken und ziehen (Esc zum Abbrechen)",
        "es": "Dibujar una línea: clic y arrastrar (Esc para cancelar)",
    },
    "ui.vector_tool_rect": {
        "fr": "Rectangle",
        "en": "Rectangle",
        "de": "Rechteck",
        "es": "Rectángulo",
    },
    "ui.vector_tool_rect_tip": {
        "fr": "Tracer un rectangle en 3 points : 2 clics pour un côté, puis tirer pour l'autre dimension (Échap pour annuler)",
        "en": "Draw a rectangle in 3 points: 2 clicks for one side, then drag for the other dimension (Esc to cancel)",
        "de": "Rechteck in 3 Punkten zeichnen: 2 Klicks für eine Seite, dann ziehen für die andere Abmessung (Esc zum Abbrechen)",
        "es": "Dibujar un rectángulo en 3 puntos: 2 clics para un lado, luego arrastrar para la otra dimensión (Esc para cancelar)",
    },
    "ui.vector_tool_ellipse": {
        "fr": "Ellipse",
        "en": "Ellipse",
        "de": "Ellipse",
        "es": "Elipse",
    },
    "ui.vector_tool_ellipse_tip": {
        "fr": "Tracer une ellipse d'un seul geste : clic-glisser d'un coin du cadre à l'autre (Échap pour annuler)",
        "en": "Draw an ellipse in one go: click-drag from one corner of its frame to the opposite one (Esc to cancel)",
        "de": "Ellipse in einem Zug zeichnen: von einer Ecke des Rahmens zur gegenüberliegenden ziehen (Esc zum Abbrechen)",
        "es": "Dibujar una elipse de un solo gesto: clic y arrastrar de una esquina del marco a la opuesta (Esc para cancelar)",
    },
    "ui.vector_tool_circle": {
        "fr": "Cercle",
        "en": "Circle",
        "de": "Kreis",
        "es": "Círculo",
    },
    "ui.vector_tool_circle_tip": {
        "fr": "Tracer un cercle d'un seul geste : clic-glisser du centre vers le bord (Échap pour annuler)",
        "en": "Draw a circle in one go: click-drag from the centre to the edge (Esc to cancel)",
        "de": "Kreis in einem Zug zeichnen: vom Mittelpunkt zum Rand ziehen (Esc zum Abbrechen)",
        "es": "Dibujar un círculo de un solo gesto: clic y arrastrar del centro al borde (Esc para cancelar)",
    },
    "vector.dlg.anchor": {
        "fr": "Lettres par rapport au trait :",
        "en": "Letters relative to the line:",
        "de": "Buchstaben zur Linie:",
        "es": "Letras respecto a la línea:",
    },
    "vector.dlg.anchor_above": {
        "fr": "Posées sur le trait (au-dessus)",
        "en": "Sitting on the line (above)",
        "de": "Auf der Linie (darüber)",
        "es": "Sobre la línea (encima)",
    },
    "vector.dlg.anchor_center": {
        "fr": "Centrées sur le trait",
        "en": "Centered on the line",
        "de": "Auf der Linie zentriert",
        "es": "Centradas en la línea",
    },
    "vector.dlg.anchor_below": {
        "fr": "Accrochées sous le trait (à l'intérieur, lisible)",
        "en": "Hanging under the line (inside, readable)",
        "de": "Unter der Linie hängend (innen, lesbar)",
        "es": "Colgadas bajo la línea (dentro, legible)",
    },
    "vector.dlg.spread": {
        "fr": "Étaler le texte sur :",
        "en": "Spread the text over:",
        "de": "Text verteilen auf:",
        "es": "Extender el texto sobre:",
    },
    "vector.dlg.spread_btn": {
        "fr": "Étaler",
        "en": "Spread",
        "de": "Verteilen",
        "es": "Extender",
    },
    "vector.dlg.spread_tip": {
        "fr": "Règle l'espacement des lettres pour que le texte couvre cette part du cercle ou du contour (100 % = tout le tour).",
        "en": "Sets the letter spacing so the text covers this share of the circle or outline (100 % = all the way round).",
        "de": "Stellt den Buchstabenabstand so ein, dass der Text diesen Anteil des Kreises oder der Kontur abdeckt (100 % = ganz herum).",
        "es": "Ajusta el espaciado para que el texto cubra esta parte del círculo o del contorno (100 % = toda la vuelta).",
    },
    "vector.dlg.preset": {
        "fr": "Préréglage :",
        "en": "Preset:",
        "de": "Voreinstellung:",
        "es": "Preajuste:",
    },
    "vector.dlg.preset_none": {
        "fr": "— aucun —",
        "en": "— none —",
        "de": "— keine —",
        "es": "— ninguno —",
    },
    "vector.dlg.preset_save": {
        "fr": "Enregistrer…",
        "en": "Save…",
        "de": "Speichern…",
        "es": "Guardar…",
    },
    "vector.dlg.preset_delete": {
        "fr": "Supprimer",
        "en": "Delete",
        "de": "Löschen",
        "es": "Eliminar",
    },
    "vector.dlg.preset_name_title": {
        "fr": "Préréglage de texte",
        "en": "Text preset",
        "de": "Text-Voreinstellung",
        "es": "Preajuste de texto",
    },
    "vector.dlg.preset_name_label": {
        "fr": "Nom du préréglage :",
        "en": "Preset name:",
        "de": "Name der Voreinstellung:",
        "es": "Nombre del preajuste:",
    },
    "vector.medal": {
        "fr": "Texte de médaille (haut + bas)…",
        "en": "Medal text (top + bottom)…",
        "de": "Medaillentext (oben + unten)…",
        "es": "Texto de medalla (arriba + abajo)…",
    },
    "vector.medal_title": {
        "fr": "Texte de médaille",
        "en": "Medal text",
        "de": "Medaillentext",
        "es": "Texto de medalla",
    },
    "vector.medal.top": {
        "fr": "Texte du haut :",
        "en": "Top text:",
        "de": "Text oben:",
        "es": "Texto de arriba:",
    },
    "vector.medal.bottom": {
        "fr": "Texte du bas :",
        "en": "Bottom text:",
        "de": "Text unten:",
        "es": "Texto de abajo:",
    },
    "vector.medal.margin": {
        "fr": "Distance au bord :",
        "en": "Distance from the edge:",
        "de": "Abstand zum Rand:",
        "es": "Distancia al borde:",
    },
    "vector.medal_need_guide": {
        "fr": "Sélectionnez un seul objet à contour fermé (cercle, ellipse, rectangle...).",
        "en": "Select a single object with a closed outline (circle, ellipse, rectangle...).",
        "de": "Wählen Sie ein einzelnes Objekt mit geschlossener Kontur (Kreis, Ellipse, Rechteck ...).",
        "es": "Seleccione un solo objeto con contorno cerrado (círculo, elipse, rectángulo...).",
    },
    "vector.text_resync": {
        "fr": "Resynchroniser le texte avec son objet",
        "en": "Resync the text with its object",
        "de": "Text mit seinem Objekt neu abgleichen",
        "es": "Resincronizar el texto con su objeto",
    },
    "vector.text_resynced": {
        "fr": "Texte resynchronisé avec son objet.",
        "en": "Text resynced with its object.",
        "de": "Text mit seinem Objekt abgeglichen.",
        "es": "Texto resincronizado con su objeto.",
    },
    "vector.follow_handle_tip": {
        "fr": "Glisser pour déplacer le texte le long du contour",
        "en": "Drag to move the text along the outline",
        "de": "Ziehen, um den Text entlang der Kontur zu verschieben",
        "es": "Arrastre para mover el texto a lo largo del contorno",
    },
    "vector.text_follow": {
        "fr": "Courber le texte sur le tracé",
        "en": "Bend text along the curve",
        "de": "Text entlang der Kurve biegen",
        "es": "Curvar el texto sobre el trazado",
    },
    "vector.text_follow_title": {
        "fr": "Texte le long d'un objet",
        "en": "Text along an object",
        "de": "Text entlang eines Objekts",
        "es": "Texto a lo largo de un objeto",
    },
    "vector.text_follow_need_two": {
        "fr": "Sélectionnez un texte ET l'objet dont il doit suivre le contour (cercle, ellipse, courbe, forme importée...) : cliquez sur l'un, puis Maj + clic sur l'autre.",
        "en": "Select a text AND the object whose outline it must follow (circle, ellipse, curve, imported shape...): click one, then Shift + click the other.",
        "de": "Wählen Sie einen Text UND das Objekt, dessen Kontur er folgen soll (Kreis, Ellipse, Kurve, importierte Form ...): erst eines anklicken, dann Umschalt + Klick auf das andere.",
        "es": "Seleccione un texto Y el objeto cuyo contorno debe seguir (círculo, elipse, curva, forma importada...): haga clic en uno y luego Mayús + clic en el otro.",
    },
    "vector.dlg.follow_place": {
        "fr": "Placer le texte :",
        "en": "Place the text:",
        "de": "Text platzieren:",
        "es": "Colocar el texto:",
    },
    "vector.dlg.follow_place_custom": {
        "fr": "Position libre (voir ci-dessous)",
        "en": "Free position (see below)",
        "de": "Freie Position (siehe unten)",
        "es": "Posición libre (ver abajo)",
    },
    "vector.dlg.follow_place_top": {
        "fr": "En haut", "en": "At the top", "de": "Oben", "es": "Arriba",
    },
    "vector.dlg.follow_place_bottom": {
        "fr": "En bas", "en": "At the bottom", "de": "Unten", "es": "Abajo",
    },
    "vector.dlg.follow_place_left": {
        "fr": "À gauche", "en": "On the left", "de": "Links", "es": "A la izquierda",
    },
    "vector.dlg.follow_place_right": {
        "fr": "À droite", "en": "On the right", "de": "Rechts", "es": "A la derecha",
    },
    "vector.dlg.follow_pos": {
        "fr": "Position sur le tracé :",
        "en": "Position along the outline:",
        "de": "Position auf der Kontur:",
        "es": "Posición en el contorno:",
    },
    "vector.dlg.follow_reverse": {
        "fr": "Texte à l'intérieur / de l'autre côté du trait (inverse le sens de lecture)",
        "en": "Text inside / on the other side of the line (reverses the reading direction)",
        "de": "Text innen / auf der anderen Seite der Linie (kehrt die Leserichtung um)",
        "es": "Texto por dentro / al otro lado de la línea (invierte el sentido de lectura)",
    },
    "vector.dlg.follow_gap": {
        "fr": "Distance au tracé :",
        "en": "Distance from the outline:",
        "de": "Abstand zur Kontur:",
        "es": "Distancia al contorno:",
    },
    "vector.dlg.follow_detach": {
        "fr": "Détacher du tracé (redevient un texte droit)",
        "en": "Detach from the outline (back to straight text)",
        "de": "Von der Kontur lösen (wieder gerader Text)",
        "es": "Separar del contorno (vuelve a ser texto recto)",
    },
    "ui.vector_import_svg": {
        "fr": "📥 Importer SVG / DXF (multi-calques)",
        "en": "📥 Import SVG / DXF (multi-layer)",
        "de": "📥 SVG / DXF importieren (Mehrfach-Ebenen)",
        "es": "📥 Importar SVG / DXF (multicapa)",
    },
    "ui.vector_edit_selection": {
        "fr": "Modifier Sélection",
        "en": "Edit Selection",
        "de": "Auswahl bearbeiten",
        "es": "Editar selección",
    },
    "ui.vector_rotate_90": {
        "fr": "↻ Pivoter 90°",
        "en": "↻ Rotate 90°",
        "de": "↻ 90° drehen",
        "es": "↻ Girar 90°",
    },
    "ui.vector_duplicate": {
        "fr": "Dupliquer",
        "en": "Duplicate",
        "de": "Duplizieren",
        "es": "Duplicar",
    },
    "ui.vector_delete": {
        "fr": "Supprimer",
        "en": "Delete",
        "de": "Löschen",
        "es": "Eliminar",
    },
    "ui.vector_delete_all": {
        "fr": "Tout supprimer",
        "en": "Delete all",
        "de": "Alles löschen",
        "es": "Eliminar todo",
    },
    "vector.delete_all_title": {
        "fr": "Tout supprimer",
        "en": "Delete all",
        "de": "Alles löschen",
        "es": "Eliminar todo",
    },
    "vector.delete_all_question": {
        "fr": "Supprimer les {count} objets de l'éditeur vectoriel ?\n\nCtrl+Z (Annuler) les fait revenir.",
        "en": "Delete the {count} objects of the vector editor?\n\nCtrl+Z (Undo) brings them back.",
        "de": "Die {count} Objekte des Vektoreditors löschen?\n\nStrg+Z (Rückgängig) holt sie zurück.",
        "es": "¿Eliminar los {count} objetos del editor vectorial?\n\nCtrl+Z (Deshacer) los recupera.",
    },
    "vector.place_title": {
        "fr": "Ajouter le dessin",
        "en": "Add the drawing",
        "de": "Zeichnung hinzufügen",
        "es": "Añadir el dibujo",
    },
    "vector.place_question": {
        "fr": "L'éditeur vectoriel contient déjà {count} objet(s). Que faire du nouveau dessin ?\n\nCtrl+Z (Annuler) revient en arrière.",
        "en": "The vector editor already holds {count} object(s). What should be done with the new drawing?\n\nCtrl+Z (Undo) goes back.",
        "de": "Der Vektoreditor enthält bereits {count} Objekt(e). Was soll mit der neuen Zeichnung geschehen?\n\nStrg+Z (Rückgängig) macht es rückgängig.",
        "es": "El editor vectorial ya contiene {count} objeto(s). ¿Qué hacer con el nuevo dibujo?\n\nCtrl+Z (Deshacer) vuelve atrás.",
    },
    "vector.place_add": {
        "fr": "Ajouter sans toucher aux objets",
        "en": "Add, keep the objects",
        "de": "Hinzufügen, Objekte behalten",
        "es": "Añadir sin tocar los objetos",
    },
    "vector.place_replace": {
        "fr": "Supprimer les objets présents",
        "en": "Delete the existing objects",
        "de": "Vorhandene Objekte löschen",
        "es": "Eliminar los objetos presentes",
    },
    "vector.place_right": {
        "fr": "Ajouter à droite",
        "en": "Add to the right",
        "de": "Rechts hinzufügen",
        "es": "Añadir a la derecha",
    },
    "vector.place_above": {
        "fr": "Ajouter au-dessus",
        "en": "Add above",
        "de": "Oben hinzufügen",
        "es": "Añadir encima",
    },
    "ui.vector_undo": {
        "fr": "↶ Annuler (Ctrl+Z)",
        "en": "↶ Undo (Ctrl+Z)",
        "de": "↶ Rückgängig (Ctrl+Z)",
        "es": "↶ Deshacer (Ctrl+Z)",
    },
    "ui.vector_redo": {
        "fr": "↷ Refaire (Ctrl+Y)",
        "en": "↷ Redo (Ctrl+Y)",
        "de": "↷ Wiederholen (Ctrl+Y)",
        "es": "↷ Rehacer (Ctrl+Y)",
    },
    "ui.vector_zoom_in": {
        "fr": "Zoom avant (Ctrl++)",
        "en": "Zoom in (Ctrl++)",
        "de": "Vergrößern (Ctrl++)",
        "es": "Acercar (Ctrl++)",
    },
    "ui.vector_zoom_out": {
        "fr": "Zoom arrière (Ctrl+-)",
        "en": "Zoom out (Ctrl+-)",
        "de": "Verkleinern (Ctrl+-)",
        "es": "Alejar (Ctrl+-)",
    },
    "ui.vector_align_box": {
        "fr": "Alignement / Distribution",
        "en": "Alignment / Distribution",
        "de": "Ausrichtung / Verteilung",
        "es": "Alineación / Distribución",
    },
    # Infobulles de la barre d'alignement (boutons à pictogramme seul).
    "ui.vector_align_left_tip": {
        "fr": "Aligner à gauche", "en": "Align left",
        "de": "Links ausrichten", "es": "Alinear a la izquierda",
    },
    "ui.vector_align_center_h_tip": {
        "fr": "Centrer horizontalement", "en": "Center horizontally",
        "de": "Horizontal zentrieren", "es": "Centrar horizontalmente",
    },
    "ui.vector_align_right_tip": {
        "fr": "Aligner à droite", "en": "Align right",
        "de": "Rechts ausrichten", "es": "Alinear a la derecha",
    },
    "ui.vector_align_top_tip": {
        "fr": "Aligner en haut", "en": "Align top",
        "de": "Oben ausrichten", "es": "Alinear arriba",
    },
    "ui.vector_align_middle_v_tip": {
        "fr": "Centrer verticalement", "en": "Center vertically",
        "de": "Vertikal zentrieren", "es": "Centrar verticalmente",
    },
    "ui.vector_align_bottom_tip": {
        "fr": "Aligner en bas", "en": "Align bottom",
        "de": "Unten ausrichten", "es": "Alinear abajo",
    },
    "ui.vector_distribute_h_tip": {
        "fr": "Répartir horizontalement", "en": "Distribute horizontally",
        "de": "Horizontal verteilen", "es": "Distribuir horizontalmente",
    },
    "ui.vector_distribute_v_tip": {
        "fr": "Répartir verticalement", "en": "Distribute vertically",
        "de": "Vertikal verteilen", "es": "Distribuir verticalmente",
    },
    "ui.vector_align_left": {
        "fr": "⊢ Gauche", "en": "⊢ Left", "de": "⊢ Links", "es": "⊢ Izquierda",
    },
    "ui.vector_align_center_h": {
        "fr": "⊟ Centre H", "en": "⊟ Center H", "de": "⊟ Mitte H", "es": "⊟ Centro H",
    },
    "ui.vector_align_right": {
        "fr": "⊣ Droite", "en": "⊣ Right", "de": "⊣ Rechts", "es": "⊣ Derecha",
    },
    "ui.vector_align_top": {
        "fr": "⊤ Haut", "en": "⊤ Top", "de": "⊤ Oben", "es": "⊤ Arriba",
    },
    "ui.vector_align_middle_v": {
        "fr": "⊞ Milieu V", "en": "⊞ Middle V", "de": "⊞ Mitte V", "es": "⊞ Centro V",
    },
    "ui.vector_align_bottom": {
        "fr": "⊥ Bas", "en": "⊥ Bottom", "de": "⊥ Unten", "es": "⊥ Abajo",
    },
    "ui.vector_distribute_h": {
        "fr": "⇹ Répartir H", "en": "⇹ Distribute H",
        "de": "⇹ Verteilen H", "es": "⇹ Distribuir H",
    },
    "ui.vector_distribute_v": {
        "fr": "⇳ Répartir V", "en": "⇳ Distribute V",
        "de": "⇳ Verteilen V", "es": "⇳ Distribuir V",
    },
    "ui.vector_snap_enable": {
        "fr": "🧲 Accroche à la grille", "en": "🧲 Snap to grid",
        "de": "🧲 Am Raster einrasten", "es": "🧲 Ajustar a la cuadrícula",
    },
    "ui.vector_fullscreen": {
        "fr": "Plein écran",
        "en": "Full Screen",
        "de": "Vollbild",
        "es": "Pantalla completa",
    },
    "ui.vector_x_mm": {
        "fr": "X (mm) :",
        "en": "X (mm):",
        "de": "X (mm):",
        "es": "X (mm):",
    },
    "ui.vector_y_mm": {
        "fr": "Y (mm) :",
        "en": "Y (mm):",
        "de": "Y (mm):",
        "es": "Y (mm):",
    },
    "ui.vector_rotation_deg": {
        "fr": "Rotation (°) :",
        "en": "Rotation (°):",
        "de": "Drehung (°):",
        "es": "Rotación (°):",
    },
    "ui.vector_layer": {
        "fr": "Calque :",
        "en": "Layer:",
        "de": "Ebene:",
        "es": "Capa:",
    },
    "ui.dro_state": {
        "fr": "État : {value}", "en": "State: {value}",
        "de": "Status: {value}", "es": "Estado: {value}",
    },
    "ui.dro_x": {
        "fr": "X : {value} mm", "en": "X: {value} mm",
        "de": "X: {value} mm", "es": "X: {value} mm",
    },
    "ui.dro_y": {
        "fr": "Y : {value} mm", "en": "Y: {value} mm",
        "de": "Y: {value} mm", "es": "Y: {value} mm",
    },
    "ui.dro_z": {
        "fr": "Z : {value} mm", "en": "Z: {value} mm",
        "de": "Z: {value} mm", "es": "Z: {value} mm",
    },
    "ui.unlock_alarm": {
        "fr": "🔓 Déverrouiller ($X)", "en": "🔓 Unlock ($X)",
        "de": "🔓 Entsperren ($X)", "es": "🔓 Desbloquear ($X)",
    },
    "ui.jog_speed_range": {
        "fr": "Vitesse du jog : {min} à {max} mm/min (maximum : vitesse max du graveur)",
        "en": "Jog speed: {min} to {max} mm/min (maximum: engraver max speed)",
        "de": "Jog-Geschwindigkeit: {min} bis {max} mm/min (Maximum: Höchstgeschwindigkeit des Gravierers)",
        "es": "Velocidad del jog: {min} a {max} mm/min (máximo: velocidad máx. del grabador)",
    },
    "ui.job_actions_box": {
        "fr": "Jobs",
        "en": "Jobs",
        "de": "Aufträge",
        "es": "Trabajos",
    },
    "ui.jog_box": {
        "fr": "Commandes et mouvements manuels",
        "en": "Commands and Manual Moves",
        "de": "Befehle und manuelle Bewegungen",
        "es": "Comandos y movimientos manuales",
    },
    "ui.homing_cmd": {
        "fr": "HOMING ($H)",
        "en": "HOMING ($H)",
        "de": "HOMING ($H)",
        "es": "HOMING ($H)",
    },
    "ui.zero_work": {
        "fr": "Zéro Travail (G92 X0 Y0)",
        "en": "Work Zero (G92 X0 Y0)",
        "de": "Arbeitsnull (G92 X0 Y0)",
        "es": "Cero de trabajo (G92 X0 Y0)",
    },
    "ui.go_zero": {
        "fr": "Go Zéro (G0 X0 Y0)",
        "en": "Go Zero (G0 X0 Y0)",
        "de": "Zu Null (G0 X0 Y0)",
        "es": "Ir a cero (G0 X0 Y0)",
    },
    "ui.pause": {
        "fr": "PAUSE (!)",
        "en": "PAUSE (!)",
        "de": "PAUSE (!)",
        "es": "PAUSA (!)",
    },
    "ui.resume": {
        "fr": "REPRISE (~)",
        "en": "RESUME (~)",
        "de": "FORTSETZEN (~)",
        "es": "REANUDAR (~)",
    },
    "ui.reset": {
        "fr": "RESET GRBL (Ctrl+X)",
        "en": "RESET GRBL (Ctrl+X)",
        "de": "RESET GRBL (Ctrl+X)",
        "es": "RESET GRBL (Ctrl+X)",
    },
    "ui.kill": {
        "fr": "ARRÊT URGENCE (KILL)",
        "en": "EMERGENCY STOP (KILL)",
        "de": "NOT-AUS (KILL)",
        "es": "PARADA DE EMERGENCIA (KILL)",
    },
    "ui.frame": {
        "fr": "Cadrage (Frame)",
        "en": "Frame",
        "de": "Rahmen",
        "es": "Marco",
    },
    "ui.send_to_laser": {
        "fr": "ENVOYER AU LASER (USB)",
        "en": "SEND TO LASER (USB)",
        "de": "AN DEN LASER SENDEN (USB)",
        "es": "ENVIAR AL LÁSER (USB)",
    },
    "ui.repeat_last_job": {
        "fr": "🔁 Répéter le dernier job", "en": "🔁 Repeat last job",
        "de": "🔁 Letzten Job wiederholen", "es": "🔁 Repetir el último trabajo",
    },
    "ui.burn_progress": {
        "fr": "Gravure : {pct}%",
        "en": "Engraving: {pct}%",
        "de": "Gravur: {pct}%",
        "es": "Grabado: {pct}%",
    },
    "ui.manual_grbl_placeholder": {
        "fr": "Tape une commande GRBL ($$, $I, $H, $X, G0 X10 Y10)... (↑/↓ pour l'historique)",
        "en": "Type a GRBL command ($$, $I, $H, $X, G0 X10 Y10)... (↑/↓ for history)",
        "de": "Gib einen GRBL-Befehl ein ($$, $I, $H, $X, G0 X10 Y10)... (↑/↓ für Verlauf)",
        "es": "Escribe un comando GRBL ($$, $I, $H, $X, G0 X10 Y10)... (↑/↓ para historial)",
    },
    "ui.manual_send": {
        "fr": "Envoyer",
        "en": "Send",
        "de": "Senden",
        "es": "Enviar",
    },
    "ui.job_stats_box": {
        "fr": "Statistiques du Job",
        "en": "Job Statistics",
        "de": "Job-Statistiken",
        "es": "Estadísticas del trabajo",
    },
    "ui.job_lines": {
        "fr": "Lignes: 0",
        "en": "Lines: 0",
        "de": "Zeilen: 0",
        "es": "Líneas: 0",
    },
    "ui.job_avg_power": {
        "fr": "Puissance Moyenne: 0 %",
        "en": "Average Power: 0 %",
        "de": "Durchschnittliche Leistung: 0 %",
        "es": "Potencia media: 0 %",
    },
    "ui.job_estimated_time": {
        "fr": "Temps Estimé: 00:00",
        "en": "Estimated Time: 00:00",
        "de": "Geschätzte Zeit: 00:00",
        "es": "Tiempo estimado: 00:00",
    },
    "ui.gcode_export_box": {
        "fr": "Export G-Code (3 Formats au choix)",
        "en": "G-Code Export (3 formats available)",
        "de": "G-Code-Export (3 Formate verfügbar)",
        "es": "Exportación G-Code (3 formatos disponibles)",
    },
    "ui.generated_console_label": {
        "fr": "Console / G-Code Généré :",
        "en": "Console / Generated G-Code:",
        "de": "Konsole / Generierter G-Code:",
        "es": "Consola / G-Code generado:",
    },
    "ui.tab_console_gcode": {
        "fr": "Console / G-Code",
        "en": "Console / G-Code",
        "de": "Konsole / G-Code",
        "es": "Consola / G-Code",
    },
    "ui.queue_add_current": {
        "fr": "+ Ajouter le G-Code actuel",
        "en": "+ Add current G-Code",
        "de": "+ Aktuellen G-Code hinzufügen",
        "es": "+ Añadir G-Code actual",
    },
    "ui.queue_remove_selected": {
        "fr": "Retirer la sélection",
        "en": "Remove selection",
        "de": "Auswahl entfernen",
        "es": "Quitar selección",
    },
    "ui.queue_clear": {
        "fr": "Vider la file",
        "en": "Clear queue",
        "de": "Warteschlange leeren",
        "es": "Vaciar cola",
    },
    "ui.queue_run": {
        "fr": "▶ Lancer la file (l'un après l'autre)",
        "en": "▶ Run queue (one after another)",
        "de": "▶ Warteschlange starten (nacheinander)",
        "es": "▶ Ejecutar cola (una tras otra)",
    },
    "ui.queue_empty": {
        "fr": "File vide.",
        "en": "Queue empty.",
        "de": "Warteschlange leer.",
        "es": "Cola vacía.",
    },
    "ui.tab_job_queue": {
        "fr": "File d'attente",
        "en": "Job Queue",
        "de": "Warteschlange",
        "es": "Cola de trabajos",
    },
    "ui.origin_bottom_left": {
        "fr": "Bas-Gauche (0,0)",
        "en": "Bottom-Left (0,0)",
        "de": "Unten links (0,0)",
        "es": "Abajo-izquierda (0,0)",
    },
    "ui.origin_center": {
        "fr": "Centre",
        "en": "Center",
        "de": "Mitte",
        "es": "Centro",
    },
    "ui.mat_min_power": {
        "fr": "Puissance Min (%):",
        "en": "Min Power (%):",
        "de": "Min. Leistung (%):",
        "es": "Potencia mín. (%):",
    },
    "ui.mat_unique_power": {
        "fr": "Puissance Unique (%):",
        "en": "Single Power (%):",
        "de": "Einzelleistung (%):",
        "es": "Potencia única (%):",
    },
    "ui.mat_max_power": {
        "fr": "Puissance Max (%):",
        "en": "Max Power (%):",
        "de": "Max. Leistung (%):",
        "es": "Potencia máx. (%):",
    },
    "ui.mat_power_step": {
        "fr": "Pas de Puissance:",
        "en": "Power Step:",
        "de": "Leistungs-Schritt:",
        "es": "Paso de potencia:",
    },
    "ui.mat_min_passes": {
        "fr": "Passes Min:",
        "en": "Min Passes:",
        "de": "Min. Durchgänge:",
        "es": "Pasadas mín.:",
    },
    "ui.mat_max_passes": {
        "fr": "Passes Max:",
        "en": "Max Passes:",
        "de": "Max. Durchgänge:",
        "es": "Pasadas máx.:",
    },
    "ui.mat_passes_step": {
        "fr": "Pas de Passes:",
        "en": "Passes Step:",
        "de": "Durchgangs-Schritt:",
        "es": "Paso de pasadas:",
    },
    "ui.mat_min_speed": {
        "fr": "Vitesse Min (mm/min):",
        "en": "Min Speed (mm/min):",
        "de": "Min. Geschwindigkeit (mm/min):",
        "es": "Velocidad mín. (mm/min):",
    },
    "ui.mat_max_speed": {
        "fr": "Vitesse Max (mm/min):",
        "en": "Max Speed (mm/min):",
        "de": "Max. Geschwindigkeit (mm/min):",
        "es": "Velocidad máx. (mm/min):",
    },
    "ui.mat_speed_step": {
        "fr": "Pas de Vitesse:",
        "en": "Speed Step:",
        "de": "Geschwindigkeits-Schritt:",
        "es": "Paso de velocidad:",
    },
    "ui.mat_square_size": {
        "fr": "Taille Carré (mm):",
        "en": "Square Size (mm):",
        "de": "Quadratgröße (mm):",
        "es": "Tamaño del cuadrado (mm):",
    },
    "ui.mat_spacing": {
        "fr": "Espacement (mm):",
        "en": "Spacing (mm):",
        "de": "Abstand (mm):",
        "es": "Espaciado (mm):",
    },
    "ui.mat_lmm": {
        "fr": "Lignes / mm (Gravure):",
        "en": "Lines / mm (Engraving):",
        "de": "Linien / mm (Gravur):",
        "es": "Líneas / mm (Grabado):",
    },
    "ui.mat_laser_cmd": {
        "fr": "Commande Laser:",
        "en": "Laser Command:",
        "de": "Laserbefehl:",
        "es": "Comando láser:",
    },
    "ui.mat_homing": {
        "fr": "Inclure $H (Auto Homing au départ)",
        "en": "Include $H (Auto Homing at start)",
        "de": "$H einbeziehen (Auto-Homing am Start)",
        "es": "Incluir $H (homing automático al inicio)",
    },
    "ui.gen_test_matrix": {
        "fr": "GÉNÉRER MATRICE DE TEST",
        "en": "GENERATE TEST MATRIX",
        "de": "TESTMATRIX GENERIEREN",
        "es": "GENERAR MATRIZ DE PRUEBA",
    },
    "ui.test_mode": {
        "fr": "Mode de Test:",
        "en": "Test Mode:",
        "de": "Testmodus:",
        "es": "Modo de prueba:",
    },
    "ui.mat_offset_x": {
        "fr": "Matrice Offset X (mm):",
        "en": "Matrix Offset X (mm):",
        "de": "Matrix-Offset X (mm):",
        "es": "Offset X de la matriz (mm):",
    },
    "ui.mat_offset_y": {
        "fr": "Matrice Offset Y (mm):",
        "en": "Matrix Offset Y (mm):",
        "de": "Matrix-Offset Y (mm):",
        "es": "Offset Y de la matriz (mm):",
    },
    "ui.grbl_homing": {
        "fr": "Inclure $H (Auto Homing au départ)",
        "en": "Include $H (Auto Homing at start)",
        "de": "$H einbeziehen (Auto-Homing am Start)",
        "es": "Incluir $H (homing automático al inicio)",
    },
    "ui.overscan_enabled": {
        "fr": "Activer le Surbalayage (Overscan)",
        "en": "Enable Overscan",
        "de": "Overscan aktivieren",
        "es": "Activar sobremuestreo",
    },
    "ui.overscan_mode_fixed": {
        "fr": "Distance Fixe (mm)",
        "en": "Fixed Distance (mm)",
        "de": "Feste Distanz (mm)",
        "es": "Distancia fija (mm)",
    },
    "ui.overscan_mode_pct": {
        "fr": "Pourcentage (%)",
        "en": "Percentage (%)",
        "de": "Prozent (%)",
        "es": "Porcentaje (%)",
    },
    "ui.gcode_laser_cmd": {
        "fr": "Commande Laser:",
        "en": "Laser Command:",
        "de": "Laserbefehl:",
        "es": "Comando láser:",
    },
    "ui.gcode_smax": {
        "fr": "S-Max Value ($30):",
        "en": "S-Max Value ($30):",
        "de": "S-Max-Wert ($30):",
        "es": "Valor S-Max ($30):",
    },
    "ui.overscan_mode_label": {
        "fr": "Mode Surbalayage:",
        "en": "Overscan Mode:",
        "de": "Overscan-Modus:",
        "es": "Modo de sobremuestreo:",
    },
    "ui.overscan_value_label": {
        "fr": "Valeur Surbalayage:",
        "en": "Overscan Value:",
        "de": "Overscan-Wert:",
        "es": "Valor de sobremuestreo:",
    },
    "ui.gcode_start": {
        "fr": "G-Code Début:",
        "en": "Start G-Code:",
        "de": "G-Code Beginn:",
        "es": "G-Code de inicio:",
    },
    "ui.gcode_end": {
        "fr": "G-Code Fin:",
        "en": "End G-Code:",
        "de": "G-Code Ende:",
        "es": "G-Code final:",
    },
    "ui.grbl_settings_box": {
        "fr": "Réglages GRBL complets ($$)", "en": "Full GRBL settings ($$)",
        "de": "Vollständige GRBL-Einstellungen ($$)", "es": "Ajustes completos de GRBL ($$)",
    },
    "ui.grbl_settings_placeholder": {
        "fr": "Clique sur « Lire depuis la machine » pour récupérer tous les réglages $0 à $132...",
        "en": "Click \"Read from machine\" to retrieve all $0 to $132 settings...",
        "de": "Klicke auf „Von Maschine lesen“, um alle Einstellungen $0 bis $132 abzurufen...",
        "es": "Haz clic en «Leer desde la máquina» para obtener todos los ajustes $0 a $132...",
    },
    "ui.grbl_read": {
        "fr": "📥 Lire depuis la machine", "en": "📥 Read from machine",
        "de": "📥 Von Maschine lesen", "es": "📥 Leer desde la máquina",
    },
    "ui.grbl_send": {
        "fr": "⬆️ Envoyer à la machine", "en": "⬆️ Send to machine",
        "de": "⬆️ An Maschine senden", "es": "⬆️ Enviar a la máquina",
    },
    "ui.grbl_export": {
        "fr": "💾 Exporter...", "en": "💾 Export...",
        "de": "💾 Exportieren...", "es": "💾 Exportar...",
    },
    "ui.grbl_import": {
        "fr": "📂 Importer...", "en": "📂 Import...",
        "de": "📂 Importieren...", "es": "📂 Importar...",
    },
    "ui.grbl_link_profile": {
        "fr": "🔗 Lier au profil machine actif", "en": "🔗 Link to active machine profile",
        "de": "🔗 Mit aktivem Maschinenprofil verknüpfen", "es": "🔗 Vincular al perfil de máquina activo",
    },
    "ui.grbl_read_empty": {
        "fr": "Aucun réglage $ reçu de la machine.", "en": "No $ setting received from the machine.",
        "de": "Keine $-Einstellung von der Maschine erhalten.", "es": "No se recibió ningún ajuste $ de la máquina.",
    },
    "ui.grbl_read_success": {
        "fr": ">>> {count} réglage(s) GRBL lus depuis la machine.",
        "en": ">>> {count} GRBL setting(s) read from the machine.",
        "de": ">>> {count} GRBL-Einstellung(en) von der Maschine gelesen.",
        "es": ">>> {count} ajuste(s) GRBL leídos desde la máquina.",
    },
    "ui.grbl_send_empty": {
        "fr": "Aucun réglage $ à envoyer (champ vide ou format incorrect).",
        "en": "No $ setting to send (empty field or wrong format).",
        "de": "Keine $-Einstellung zu senden (Feld leer oder falsches Format).",
        "es": "No hay ningún ajuste $ que enviar (campo vacío o formato incorrecto).",
    },
    "ui.grbl_send_confirm_title": {
        "fr": "Envoyer les réglages GRBL ?", "en": "Send GRBL settings?",
        "de": "GRBL-Einstellungen senden?", "es": "¿Enviar los ajustes GRBL?",
    },
    "ui.grbl_send_confirm_body": {
        "fr": "{count} réglage(s) vont être envoyés à la machine et écrits dans sa mémoire EEPROM.\n\nCette action modifie durablement la configuration de la machine. Continuer ?",
        "en": "{count} setting(s) will be sent to the machine and written to its EEPROM memory.\n\nThis permanently changes the machine's configuration. Continue?",
        "de": "{count} Einstellung(en) werden an die Maschine gesendet und in ihren EEPROM-Speicher geschrieben.\n\nDies ändert die Maschinenkonfiguration dauerhaft. Fortfahren?",
        "es": "Se enviarán {count} ajuste(s) a la máquina y se escribirán en su memoria EEPROM.\n\nEsto modifica permanentemente la configuración de la máquina. ¿Continuar?",
    },
    "ui.grbl_send_errors": {
        "fr": ">>> Erreurs lors de l'envoi des réglages GRBL :\n{errors}",
        "en": ">>> Errors while sending GRBL settings:\n{errors}",
        "de": ">>> Fehler beim Senden der GRBL-Einstellungen:\n{errors}",
        "es": ">>> Errores al enviar los ajustes GRBL:\n{errors}",
    },
    "ui.grbl_send_partial": {
        "fr": "{count}/{total} réglage(s) envoyés avec succès, le reste a échoué (voir la console).",
        "en": "{count}/{total} setting(s) sent successfully, the rest failed (see console).",
        "de": "{count}/{total} Einstellung(en) erfolgreich gesendet, der Rest ist fehlgeschlagen (siehe Konsole).",
        "es": "{count}/{total} ajuste(s) enviados con éxito, el resto falló (ver consola).",
    },
    "ui.grbl_send_success": {
        "fr": ">>> {count} réglage(s) GRBL envoyés avec succès.",
        "en": ">>> {count} GRBL setting(s) sent successfully.",
        "de": ">>> {count} GRBL-Einstellung(en) erfolgreich gesendet.",
        "es": ">>> {count} ajuste(s) GRBL enviados con éxito.",
    },
    "ui.grbl_send_all_success": {
        "fr": "Les {count} réglage(s) ont été envoyés avec succès à la machine.",
        "en": "All {count} setting(s) were sent successfully to the machine.",
        "de": "Alle {count} Einstellung(en) wurden erfolgreich an die Maschine gesendet.",
        "es": "Los {count} ajuste(s) se enviaron con éxito a la máquina.",
    },
    "ui.plot_title": {
        "fr": "Visualisation 2D du Parcours Laser",
        "en": "2D Laser Path Visualization",
        "de": "2D-Laserpfadvisualisierung",
        "es": "Visualización 2D del recorrido láser",
    },
    "ui.plot_x": {
        "fr": "Axe X (mm)",
        "en": "X Axis (mm)",
        "de": "X-Achse (mm)",
        "es": "Eje X (mm)",
    },
    "ui.plot_y": {
        "fr": "Axe Y (mm)",
        "en": "Y Axis (mm)",
        "de": "Y-Achse (mm)",
        "es": "Eje Y (mm)",
    },
    "ui.plot_empty_state": {
        "fr": "Génère un job pour voir l'aperçu ici.",
        "en": "Generate a job to see the preview here.",
        "de": "Erzeuge einen Job, um hier die Vorschau zu sehen.",
        "es": "Genera un trabajo para ver la vista previa aquí.",
    },
    "ui.jog_step_label": {
        "fr": "Pas (mm):",
        "en": "Step (mm):",
        "de": "Schritt (mm):",
        "es": "Paso (mm):",
    },
    "ui.jog_speed_label": {
        "fr": "Vitesse:",
        "en": "Speed:",
        "de": "Geschwindigkeit:",
        "es": "Velocidad:",
    },
    "ui.material_mode_engraving": {
        "fr": "Gravure",
        "en": "Engraving",
        "de": "Gravur",
        "es": "Grabado",
    },
    "ui.material_mode_cutting": {
        "fr": "Découpe",
        "en": "Cutting",
        "de": "Schneiden",
        "es": "Corte",
    },
    "ui.support_body": {
        "fr": (
            "Suggestion, problème rencontré... Contacte-nous à l'adresse "
            "suivante :<br><br>"
            "<a href=\"mailto:laserstudiopro.support@proton.me\">"
            "laserstudiopro.support@proton.me</a>"
        ),
        "en": (
            "Suggestion or problem encountered... Contact us at:"
            "<br><br>"
            "<a href=\"mailto:laserstudiopro.support@proton.me\">"
            "laserstudiopro.support@proton.me</a>"
        ),
        "de": (
            "Vorschlag oder Problem... Kontaktiere uns unter:"
            "<br><br>"
            "<a href=\"mailto:laserstudiopro.support@proton.me\">"
            "laserstudiopro.support@proton.me</a>"
        ),
        "es": (
            "Sugerencia o problema encontrado... Contáctanos en:"
            "<br><br>"
            "<a href=\"mailto:laserstudiopro.support@proton.me\">"
            "laserstudiopro.support@proton.me</a>"
        ),
    },
    "ui.coffee_body": {
        "fr": (
            "Si ce logiciel t'est utile et que tu veux soutenir son développement,"
            "<br>tu peux m'offrir un café ici :<br><br>"
            "{link}<br><br>"
            "Merci !"
        ),
        "en": (
            "If this software is useful to you and you want to support its "
            "development,<br>you can buy me a coffee here:<br><br>"
            "{link}<br><br>"
            "Thank you!"
        ),
        "de": (
            "Wenn diese Software für dich nützlich ist und du die Entwicklung "
            "unterstützen möchtest,<br>kannst du mir hier einen Kaffee kaufen:"
            "<br><br>{link}<br><br>"
            "Danke!"
        ),
        "es": (
            "Si este software te resulta útil y quieres apoyar su desarrollo,"
            "<br>puedes invitarme a un café aquí:<br><br>"
            "{link}<br><br>"
            "¡Gracias!"
        ),
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
    "layers.add_tip": {
        "fr": "Ajouter un calque", "en": "Add a layer",
        "de": "Ebene hinzufügen", "es": "Añadir una capa",
    },
    "layers.remove_tip": {
        "fr": "Supprimer le calque sélectionné", "en": "Delete the selected layer",
        "de": "Ausgewählte Ebene löschen", "es": "Eliminar la capa seleccionada",
    },
    "layers.add": {
        "fr": "+ Calque",
        "en": "+ Layer",
        "de": "+ Ebene",
        "es": "+ Capa",
    },
    "layers.remove": {
        "fr": "Supprimer Calque",
        "en": "Delete Layer",
        "de": "Ebene löschen",
        "es": "Eliminar capa",
    },
    "layers.move_up": {
        "fr": "▲ Monter",
        "en": "▲ Move Up",
        "de": "▲ Nach oben",
        "es": "▲ Subir",
    },
    "layers.move_down": {
        "fr": "▼ Descendre",
        "en": "▼ Move Down",
        "de": "▼ Nach unten",
        "es": "▼ Bajar",
    },
    "layers.move_up_tip": {
        "fr": "Monter le calque sélectionné (exécuté plus tôt dans le G-Code)",
        "en": "Move the selected layer up (runs earlier in the G-code)",
        "de": "Ausgewählte Ebene nach oben (wird im G-Code früher ausgeführt)",
        "es": "Subir la capa seleccionada (se ejecuta antes en el G-code)",
    },
    "layers.move_down_tip": {
        "fr": "Descendre le calque sélectionné (exécuté plus tard dans le G-Code)",
        "en": "Move the selected layer down (runs later in the G-code)",
        "de": "Ausgewählte Ebene nach unten (wird im G-Code später ausgeführt)",
        "es": "Bajar la capa seleccionada (se ejecuta después en el G-code)",
    },
    "layers.col.color": {
        "fr": "Couleur",
        "en": "Color",
        "de": "Farbe",
        "es": "Color",
    },
    "layers.col.name": {
        "fr": "Nom",
        "en": "Name",
        "de": "Name",
        "es": "Nombre",
    },
    "layers.col.mode": {
        "fr": "Mode",
        "en": "Mode",
        "de": "Modus",
        "es": "Modo",
    },
    "layers.col.power": {
        "fr": "Puissance (%)",
        "en": "Power (%)",
        "de": "Leistung (%)",
        "es": "Potencia (%)",
    },
    "layers.col.speed": {
        "fr": "Vitesse (mm/min)",
        "en": "Speed (mm/min)",
        "de": "Geschwindigkeit (mm/min)",
        "es": "Velocidad (mm/min)",
    },
    "layers.col.passes": {
        "fr": "Passes",
        "en": "Passes",
        "de": "Durchgänge",
        "es": "Pasadas",
    },
    "layers.col.fill_step": {
        "fr": "Pas remplissage (mm)",
        "en": "Fill step (mm)",
        "de": "Füllabstand (mm)",
        "es": "Paso de relleno (mm)",
    },
    "layers.col.active": {
        "fr": "Actif",
        "en": "Active",
        "de": "Aktiv",
        "es": "Activo",
    },
    "layers.col.overscan": {
        "fr": "Surbalayage",
        "en": "Overscan",
        "de": "Overscan",
        "es": "Overscan",
    },
    "layers.col.laser": {
        "fr": "Laser",
        "en": "Laser",
        "de": "Laser",
        "es": "Láser",
    },
    "layers.overscan_tip": {
        "fr": "Surbalayage de ce calque (gravure remplie). Actif seulement si le surbalayage est activé dans Configuration GRBL, qui en donne le mode et la distance.",
        "en": "Overscan for this layer (fill engraving). Only applies if overscan is enabled in GRBL Configuration, which sets its mode and distance.",
        "de": "Overscan für diese Ebene (gefüllte Gravur). Gilt nur, wenn Overscan in der GRBL-Konfiguration aktiviert ist; dort werden Modus und Abstand festgelegt.",
        "es": "Overscan de esta capa (grabado relleno). Solo se aplica si el overscan está activado en la Configuración GRBL, que fija su modo y distancia.",
    },
    "layers.laser_auto": {
        "fr": "Auto (global)",
        "en": "Auto (global)",
        "de": "Auto (global)",
        "es": "Auto (global)",
    },
    "layers.laser_m4": {
        "fr": "M4 dynamique",
        "en": "M4 dynamic",
        "de": "M4 dynamisch",
        "es": "M4 dinámico",
    },
    "layers.laser_m3": {
        "fr": "M3 fixe",
        "en": "M3 constant",
        "de": "M3 konstant",
        "es": "M3 constante",
    },
    "layers.laser_tip": {
        "fr": "Commande laser de ce calque : Auto suit la Configuration GRBL ; M4 ajuste la puissance à la vitesse réelle (dynamique) ; M3 garde une puissance constante.",
        "en": "Laser command for this layer: Auto follows GRBL Configuration; M4 scales power with the actual speed (dynamic); M3 keeps constant power.",
        "de": "Laserbefehl dieser Ebene: Auto folgt der GRBL-Konfiguration; M4 passt die Leistung der tatsächlichen Geschwindigkeit an (dynamisch); M3 hält die Leistung konstant.",
        "es": "Comando láser de esta capa: Auto sigue la Configuración GRBL; M4 ajusta la potencia a la velocidad real (dinámico); M3 mantiene la potencia constante.",
    },
    "layers.mode.cut": {
        "fr": "Découpe",
        "en": "Cut",
        "de": "Schneiden",
        "es": "Corte",
    },
    "layers.default_name_mark": {
        "fr": "Marquage", "en": "Marking", "de": "Markierung", "es": "Marcado",
    },
    "layers.default_name_cut": {
        "fr": "Découpe", "en": "Cut", "de": "Schneiden", "es": "Corte",
    },
    "layers.default_name_engrave": {
        "fr": "Gravure", "en": "Engraving", "de": "Gravur", "es": "Grabado",
    },
    "layers.base_title": {
        "fr": "Calque de base", "en": "Base layer", "de": "Basisebene", "es": "Capa base",
    },
    "layers.base_name_tip": {
        "fr": "Calque de base : nom fixe, présent dans chaque profil matériau.",
        "en": "Base layer: fixed name, present in every material profile.",
        "de": "Basisebene: fester Name, in jedem Materialprofil vorhanden.",
        "es": "Capa base: nombre fijo, presente en cada perfil de material.",
    },
    "layers.base_cannot_delete": {
        "fr": "« {name} » est un calque de base (gravure, découpe, marquage) : il ne peut pas être supprimé. Désactivez-le s'il ne sert pas.",
        "en": "\"{name}\" is a base layer (engraving, cut, marking): it cannot be deleted. Disable it if you don't need it.",
        "de": "„{name}“ ist eine Basisebene (Gravur, Schneiden, Markierung): Sie kann nicht gelöscht werden. Deaktiviere sie, wenn du sie nicht brauchst.",
        "es": "«{name}» es una capa base (grabado, corte, marcado): no se puede eliminar. Desactívala si no la necesitas.",
    },
    "vector.n_objects": {
        "fr": " ({n} objets)", "en": " ({n} objects)",
        "de": " ({n} Objekte)", "es": " ({n} objetos)",
    },
    "vector.assign_to_layer": {
        "fr": "Assigner au calque", "en": "Assign to layer",
        "de": "Ebene zuweisen", "es": "Asignar a la capa",
    },
    "vector.resize_ellipsis": {
        "fr": "Redimensionner…", "en": "Resize…",
        "de": "Größe ändern…", "es": "Redimensionar…",
    },
    "vector.group_objects": {
        "fr": "Regrouper en un seul objet ({n} objets)",
        "en": "Group into one object ({n} objects)",
        "de": "Zu einem Objekt gruppieren ({n} Objekte)",
        "es": "Agrupar en un solo objeto ({n} objetos)",
    },
    "vector.ungroup_objects": {
        "fr": "Dégrouper",
        "en": "Ungroup",
        "de": "Gruppierung aufheben",
        "es": "Desagrupar",
    },

    "vector.ctx_add_shape": {
        "fr": "Ajouter une forme",
        "en": "Add shape",
        "de": "Form hinzufügen",
        "es": "Añadir forma",
    },
    "vector.ctx_text": {
        "fr": "Texte",
        "en": "Text",
        "de": "Text",
        "es": "Texto",
    },
    "vector.ctx_line": {
        "fr": "Ligne",
        "en": "Line",
        "de": "Linie",
        "es": "Línea",
    },
    "vector.ctx_square": {
        "fr": "Carré",
        "en": "Square",
        "de": "Quadrat",
        "es": "Cuadrado",
    },
    "vector.ctx_circle": {
        "fr": "Cercle",
        "en": "Circle",
        "de": "Kreis",
        "es": "Círculo",
    },
    "vector.explode_path": {
        "fr": "Exploser en segments",
        "en": "Explode into segments",
        "de": "In Segmente zerlegen",
        "es": "Explotar en segmentos",
    },
    "vector.edit_nodes": {
        "fr": "Éditer les nœuds",
        "en": "Edit nodes",
        "de": "Knoten bearbeiten",
        "es": "Editar nodos",
    },
    "vector.exit_nodes": {
        "fr": "Quitter l'édition de nœuds",
        "en": "Exit node editing",
        "de": "Knotenbearbeitung beenden",
        "es": "Salir de edición de nodos",
    },
    "vector.delete_node": {
        "fr": "Supprimer le nœud",
        "en": "Delete node",
        "de": "Knoten löschen",
        "es": "Eliminar nodo",
    },

    "ui.mat_image_group": {
        "fr": "Test à partir d'une image",
        "en": "Test from an image",
        "de": "Test mit einem Bild",
        "es": "Prueba a partir de una imagen",
    },
    "ui.mat_image_hint": {
        "fr": "Chaque case de la matrice grave la même zone d'une image, à l'échelle réelle, avec les réglages d'image (luminosité, contraste, tramage…) de « Graver une image ». Le négatif se règle ci-dessous. Clique ou glisse sur l'aperçu pour placer la zone.",
        "en": "Every cell of the matrix engraves the same area of an image at real scale, using the image settings (brightness, contrast, dithering…) of “Engrave an image”. Negative is set below. Click or drag on the preview to place the area.",
        "de": "Jede Zelle der Matrix graviert denselben Bildausschnitt in Originalgröße, mit den Bildeinstellungen (Helligkeit, Kontrast, Rasterung …) von „Bild gravieren“. Das Negativ wird unten eingestellt. Klicke oder ziehe in der Vorschau, um den Ausschnitt zu platzieren.",
        "es": "Cada casilla de la matriz graba la misma zona de una imagen a escala real, con los ajustes de imagen (brillo, contraste, tramado…) de «Grabar una imagen». El negativo se elige abajo. Haz clic o arrastra en la vista previa para colocar la zona.",
    },
    "ui.mat_image_invert": {
        "fr": "Négatif (inverser les couleurs)",
        "en": "Negative (invert colors)",
        "de": "Negativ (Farben invertieren)",
        "es": "Negativo (invertir colores)",
    },
    "ui.mat_image_invert_tip": {
        "fr": "Inverse les tons de la zone d'image pour ce test uniquement. Indépendant de la case « Inverser Couleurs » de l'onglet Graver une image. Utile pour les matières qui s'éclaircissent sous le laser.",
        "en": "Inverts the tones of the image area for this test only. Independent of the “Invert Colors” checkbox on the Engrave an image tab. Useful for materials that lighten under the laser.",
        "de": "Kehrt die Töne des Bildausschnitts nur für diesen Test um. Unabhängig von „Farben invertieren“ im Reiter Bild gravieren. Nützlich bei Materialien, die unter dem Laser heller werden.",
        "es": "Invierte los tonos de la zona de imagen solo para esta prueba. Independiente de «Invertir colores» en la pestaña Grabar una imagen. Útil en materiales que se aclaran con el láser.",
    },
    "ui.mat_image_choose": {
        "fr": "Choisir une image…",
        "en": "Choose an image…",
        "de": "Bild auswählen …",
        "es": "Elegir una imagen…",
    },
    "ui.mat_image_use_loaded": {
        "fr": "Image chargée",
        "en": "Loaded image",
        "de": "Geladenes Bild",
        "es": "Imagen cargada",
    },
    "ui.mat_image_use_loaded_tip": {
        "fr": "Utilise l'image de « Graver une image », à la taille qui lui est donnée là-bas.",
        "en": "Uses the image of “Engrave an image”, at the size set there.",
        "de": "Verwendet das Bild aus „Bild gravieren“ in der dort eingestellten Größe.",
        "es": "Usa la imagen de «Grabar una imagen», con el tamaño indicado allí.",
    },
    "ui.mat_image_none": {
        "fr": "Aucune image",
        "en": "No image",
        "de": "Kein Bild",
        "es": "Ninguna imagen",
    },
    "ui.mat_image_width": {
        "fr": "Largeur réelle de l'image :",
        "en": "Real width of the image:",
        "de": "Reale Bildbreite:",
        "es": "Ancho real de la imagen:",
    },
    "ui.mat_image_width_tip": {
        "fr": "Largeur de l'image entière une fois gravée. Elle fixe l'échelle : une zone de 15 mm montre exactement 15 mm de l'image.",
        "en": "Width of the whole image once engraved. It sets the scale: a 15 mm area shows exactly 15 mm of the image.",
        "de": "Breite des gesamten Bildes nach dem Gravieren. Sie legt den Maßstab fest: Ein 15-mm-Ausschnitt zeigt genau 15 mm des Bildes.",
        "es": "Ancho de la imagen completa una vez grabada. Fija la escala: una zona de 15 mm muestra exactamente 15 mm de la imagen.",
    },
    "ui.mat_tile_width": {
        "fr": "Zone : largeur :",
        "en": "Area: width:",
        "de": "Ausschnitt: Breite:",
        "es": "Zona: ancho:",
    },
    "ui.mat_tile_height": {
        "fr": "Zone : hauteur :",
        "en": "Area: height:",
        "de": "Ausschnitt: Höhe:",
        "es": "Zona: alto:",
    },
    "ui.mat_tile_info": {
        "fr": "Zone gravée : {w:.1f} × {h:.1f} mm ({pct:.0f} % de la largeur de l'image).",
        "en": "Engraved area: {w:.1f} × {h:.1f} mm ({pct:.0f}% of the image width).",
        "de": "Gravierter Ausschnitt: {w:.1f} × {h:.1f} mm ({pct:.0f} % der Bildbreite).",
        "es": "Zona grabada: {w:.1f} × {h:.1f} mm ({pct:.0f} % del ancho de la imagen).",
    },
    "ui.mat_tile_clipped": {
        "fr": "La zone dépasse l'image : elle est réduite à {w:.1f} × {h:.1f} mm.",
        "en": "The area is larger than the image: it is reduced to {w:.1f} × {h:.1f} mm.",
        "de": "Der Ausschnitt ist größer als das Bild: Er wird auf {w:.1f} × {h:.1f} mm verkleinert.",
        "es": "La zona es mayor que la imagen: se reduce a {w:.1f} × {h:.1f} mm.",
    },
    "ui.mat_tile_too_small": {
        "fr": "La zone est trop petite pour la résolution choisie (moins d'une ligne). Agrandis la zone ou augmente les lignes/mm.",
        "en": "The area is too small for the chosen resolution (less than one line). Enlarge the area or increase lines/mm.",
        "de": "Der Ausschnitt ist für die gewählte Auflösung zu klein (weniger als eine Zeile). Vergrößere den Ausschnitt oder erhöhe die Zeilen/mm.",
        "es": "La zona es demasiado pequeña para la resolución elegida (menos de una línea). Agranda la zona o aumenta las líneas/mm.",
    },
    "ui.mat_size_from_image_tip": {
        "fr": "Avec un test à partir d'une image, la taille des cases est celle de la zone choisie.",
        "en": "With an image test, the cell size is the size of the chosen area.",
        "de": "Bei einem Bildtest entspricht die Zellengröße dem gewählten Ausschnitt.",
        "es": "Con una prueba a partir de una imagen, el tamaño de las casillas es el de la zona elegida.",
    },
    "ui.mat_image_file_title": {
        "fr": "Choisir une image",
        "en": "Choose an image",
        "de": "Bild auswählen",
        "es": "Elegir una imagen",
    },
    "ui.mat_image_file_filter": {
        "fr": "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Tous les fichiers (*)",
        "en": "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All files (*)",
        "de": "Bilder (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Alle Dateien (*)",
        "es": "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Todos los archivos (*)",
    },
    "ui.mat_image_open_error": {
        "fr": "Impossible d'ouvrir l'image : {error}",
        "en": "Could not open the image: {error}",
        "de": "Das Bild konnte nicht geöffnet werden: {error}",
        "es": "No se pudo abrir la imagen: {error}",
    },
    "ui.mat_image_missing_title": {
        "fr": "Aucune image",
        "en": "No image",
        "de": "Kein Bild",
        "es": "Ninguna imagen",
    },
    "ui.mat_image_missing_body": {
        "fr": "Choisis d'abord une image, ou charge-en une dans « Graver une image », pour faire un test à partir d'une image.",
        "en": "First choose an image, or load one in “Engrave an image”, to run an image test.",
        "de": "Wähle zuerst ein Bild oder lade eines unter „Bild gravieren“, um einen Bildtest durchzuführen.",
        "es": "Primero elige una imagen, o carga una en «Grabar una imagen», para hacer una prueba a partir de una imagen.",
    },
    "ui.mat_image_loaded_none": {
        "fr": "Aucune image n'est chargée dans « Graver une image ».",
        "en": "No image is loaded in “Engrave an image”.",
        "de": "Unter „Bild gravieren“ ist kein Bild geladen.",
        "es": "No hay ninguna imagen cargada en «Grabar una imagen».",
    },

    "layers.mode.fill": {
        "fr": "Gravure Remplie",
        "en": "Fill Engraving",
        "de": "Gefüllte Gravur",
        "es": "Grabado relleno",
    },
    "layers.mode.mark": {
        "fr": "Marquage (Contour)",
        "en": "Marking (Outline)",
        "de": "Markierung (Kontur)",
        "es": "Marcado (contorno)",
    },
    "layers.color_dialog_title": {
        "fr": "Couleur du calque",
        "en": "Layer color",
        "de": "Ebenenfarbe",
        "es": "Color de la capa",
    },
    "layers.link_tip_linked": {
        "fr": "Pas remplissage lié à la taille du spot : se met à jour automatiquement à chaque changement de focale. Cliquer pour déverrouiller et régler manuellement.",
        "en": "Fill step linked to the spot size: updates automatically whenever the focal spot changes. Click to unlock and set it manually.",
        "de": "Füllabstand an die Spotgröße gekoppelt: wird bei jeder Änderung der Brennweite automatisch aktualisiert. Klicken zum Entsperren und manuellen Einstellen.",
        "es": "Paso de relleno vinculado al tamaño del punto: se actualiza automáticamente al cambiar la focal. Haz clic para desbloquear y ajustar manualmente.",
    },
    "layers.link_tip_unlinked": {
        "fr": "Cliquer pour lier ce pas de remplissage à la taille du spot (mise à jour automatique à chaque changement de focale)",
        "en": "Click to link this fill step to the spot size (updates automatically whenever the focal spot changes)",
        "de": "Klicken, um diesen Füllabstand an die Spotgröße zu koppeln (automatische Aktualisierung bei Änderung der Brennweite)",
        "es": "Haz clic para vincular este paso de relleno al tamaño del punto (actualización automática al cambiar la focal)",
    },
    "gen.start_failed": {
        "fr": "Impossible de démarrer la génération :\n\n{error}",
        "en": "Unable to start the generation:\n\n{error}",
        "de": "Die Generierung konnte nicht gestartet werden:\n\n{error}",
        "es": "No se pudo iniciar la generación:\n\n{error}",
    },
    "gen.too_big_title": {
        "fr": "Dimensions trop grandes",
        "en": "Dimensions too large",
        "de": "Abmessungen zu groß",
        "es": "Dimensiones demasiado grandes",
    },
    "gen.too_big_body": {
        "fr": "La zone de gravure configurée ({job_w:.1f} x {job_h:.1f} mm) dépasse la surface de travail de la machine ({bed_w:.1f} x {bed_h:.1f} mm, définie dans l'menu '{tab_machine}').\n\nCe n'est pas possible avec ces réglages : réduis les dimensions du job (onglet '{tab_dims}') ou agrandis la zone machine avant de continuer.",
        "en": "The configured engraving area ({job_w:.1f} x {job_h:.1f} mm) exceeds the machine's work area ({bed_w:.1f} x {bed_h:.1f} mm, set in the '{tab_machine}' menu).\n\nThis is not possible with these settings: reduce the job dimensions ('{tab_dims}' tab) or enlarge the machine area before continuing.",
        "de": "Der eingestellte Gravurbereich ({job_w:.1f} x {job_h:.1f} mm) überschreitet die Arbeitsfläche der Maschine ({bed_w:.1f} x {bed_h:.1f} mm, festgelegt im Menü '{tab_machine}').\n\nMit diesen Einstellungen ist das nicht möglich: Verkleinere die Job-Abmessungen (Tab '{tab_dims}') oder vergrößere den Maschinenbereich, bevor du fortfährst.",
        "es": "El área de grabado configurada ({job_w:.1f} x {job_h:.1f} mm) supera la superficie de trabajo de la máquina ({bed_w:.1f} x {bed_h:.1f} mm, definida en la menú '{tab_machine}').\n\nNo es posible con estos ajustes: reduce las dimensiones del trabajo (pestaña '{tab_dims}') o amplía el área de la máquina antes de continuar.",
    },
    "gen.speed_limit_title": {
        "fr": "Vitesse au-delà des limites machine",
        "en": "Speed exceeds machine limits",
        "de": "Geschwindigkeit über den Maschinengrenzen",
        "es": "Velocidad por encima de los límites de la máquina",
    },
    "gen.speed_limit_body": {
        "fr": "La machine active a une vitesse max de {limit:.0f} mm/min (menu '{tab_machine}'), mais ces réglages la dépassent :\n\n{details}\n\nContinuer quand même ?",
        "en": "The active machine has a maximum speed of {limit:.0f} mm/min ('{tab_machine}' menu), but these settings exceed it:\n\n{details}\n\nContinue anyway?",
        "de": "Die aktive Maschine hat eine Höchstgeschwindigkeit von {limit:.0f} mm/min (Menü '{tab_machine}'), aber diese Einstellungen überschreiten sie:\n\n{details}\n\nTrotzdem fortfahren?",
        "es": "La máquina activa tiene una velocidad máxima de {limit:.0f} mm/min (menú '{tab_machine}'), pero estos ajustes la superan:\n\n{details}\n\n¿Continuar de todos modos?",
    },
    "gen.speed_row_engrave": {
        "fr": "Vitesse Gravure",
        "en": "Engraving speed",
        "de": "Gravurgeschwindigkeit",
        "es": "Velocidad de grabado",
    },
    "gen.speed_row_cut_old": {
        "fr": "Vitesse Découpe (ancien mode)",
        "en": "Cutting speed (legacy mode)",
        "de": "Schneidgeschwindigkeit (alter Modus)",
        "es": "Velocidad de corte (modo antiguo)",
    },
    "gen.speed_row_layer": {
        "fr": "Calque « {name} »",
        "en": "Layer “{name}”",
        "de": "Ebene „{name}“",
        "es": "Capa «{name}»",
    },
    "gen.confirm_title": {
        "fr": "Confirmer la génération",
        "en": "Confirm generation",
        "de": "Generierung bestätigen",
        "es": "Confirmar la generación",
    },
    "gen.confirm_body": {
        "fr": "Ce job va combiner :\n\n{summary}\n\nConfirmer et générer le G-Code, ou annuler pour modifier d'abord ?",
        "en": "This job will combine:\n\n{summary}\n\nConfirm and generate the G-code, or cancel to make changes first?",
        "de": "Dieser Job kombiniert:\n\n{summary}\n\nBestätigen und G-Code generieren, oder abbrechen, um zuerst Änderungen vorzunehmen?",
        "es": "Este trabajo combinará:\n\n{summary}\n\n¿Confirmar y generar el G-code, o cancelar para modificar antes?",
    },
    "gen.confirm_image": {
        "fr": "• Gravure de l'image chargée",
        "en": "• Engraving of the loaded image",
        "de": "• Gravur des geladenen Bildes",
        "es": "• Grabado de la imagen cargada",
    },
    "gen.confirm_vectors": {
        "fr": "• {count} objet(s) vectoriel(s) sur {layers} calque(s) : {names}",
        "en": "• {count} vector object(s) on {layers} layer(s): {names}",
        "de": "• {count} Vektorobjekt(e) auf {layers} Ebene(n): {names}",
        "es": "• {count} objeto(s) vectorial(es) en {layers} capa(s): {names}",
    },
    "gen.engrave_confirm_title": {
        "fr": "Vérifier les réglages de gravure",
        "en": "Check engraving settings",
        "de": "Gravureinstellungen prüfen",
        "es": "Comprobar los ajustes de grabado",
    },
    "gen.engrave_confirm_body": {
        "fr": "Avant de générer la gravure de l'image, vérifie les réglages :\n\n• Calque : {layer}\n• Puissance : {power:.0f} %\n• Vitesse : {speed:.0f} mm/min\n• Dimensions : {width:.1f} x {height:.1f} mm\n• {material}\n\nCes valeurs te conviennent pour ce matériau ? Confirmer et générer le G-Code, ou annuler pour les modifier d'abord.",
        "en": "Before generating the image engraving, check the settings:\n\n• Layer: {layer}\n• Power: {power:.0f} %\n• Speed: {speed:.0f} mm/min\n• Size: {width:.1f} x {height:.1f} mm\n• {material}\n\nAre these values right for this material? Confirm and generate the G-code, or cancel to change them first.",
        "de": "Prüfe vor dem Generieren der Bildgravur die Einstellungen:\n\n• Ebene: {layer}\n• Leistung: {power:.0f} %\n• Geschwindigkeit: {speed:.0f} mm/min\n• Abmessungen: {width:.1f} x {height:.1f} mm\n• {material}\n\nPassen diese Werte für dieses Material? Bestätigen und G-Code generieren, oder abbrechen, um sie zuerst zu ändern.",
        "es": "Antes de generar el grabado de la imagen, comprueba los ajustes:\n\n• Capa: {layer}\n• Potencia: {power:.0f} %\n• Velocidad: {speed:.0f} mm/min\n• Dimensiones: {width:.1f} x {height:.1f} mm\n• {material}\n\n¿Son correctos estos valores para este material? Confirma y genera el G-code, o cancela para modificarlos antes.",
    },
    "gen.overscan_title": {
        "fr": "Position invalide (Surbalayage)",
        "en": "Invalid position (Overscan)",
        "de": "Ungültige Position (Overscan)",
        "es": "Posición no válida (Sobrebarrido)",
    },
    "gen.overscan_body": {
        "fr": "Avec le surbalayage actuel ({overscan:.2f} mm) et le décalage X configuré ({offset:.2f} mm), le point de départ calculé serait à X={start:.2f} mm — une position NÉGATIVE, impossible pour la machine.\n\nAugmente le décalage X (onglet '{tab_dims}') ou réduis la distance de surbalayage (menu '{tab_grbl}') avant de générer.",
        "en": "With the current overscan ({overscan:.2f} mm) and the configured X offset ({offset:.2f} mm), the calculated start point would be at X={start:.2f} mm — a NEGATIVE position, impossible for the machine.\n\nIncrease the X offset ('{tab_dims}' tab) or reduce the overscan distance ('{tab_grbl}' menu) before generating.",
        "de": "Mit dem aktuellen Overscan ({overscan:.2f} mm) und dem eingestellten X-Versatz ({offset:.2f} mm) läge der berechnete Startpunkt bei X={start:.2f} mm — eine NEGATIVE Position, für die Maschine unmöglich.\n\nErhöhe den X-Versatz (Tab '{tab_dims}') oder verringere den Overscan-Abstand (Menü '{tab_grbl}'), bevor du generierst.",
        "es": "Con el sobrebarrido actual ({overscan:.2f} mm) y el desplazamiento X configurado ({offset:.2f} mm), el punto de inicio calculado estaría en X={start:.2f} mm — una posición NEGATIVA, imposible para la máquina.\n\nAumenta el desplazamiento X (pestaña '{tab_dims}') o reduce la distancia de sobrebarrido (menú '{tab_grbl}') antes de generar.",
    },
    "gen.overscan_vec_title": {
        "fr": "Position invalide (Surbalayage — calque vectoriel)",
        "en": "Invalid position (Overscan — vector layer)",
        "de": "Ungültige Position (Overscan — Vektorebene)",
        "es": "Posición no válida (Sobrebarrido — capa vectorial)",
    },
    "gen.overscan_vec_body": {
        "fr": "Le calque « {name} » (Gravure Remplie) commence trop près du bord gauche pour le surbalayage configuré ({overscan:.2f} mm) : le point de départ serait à X={start:.2f} mm — une position NÉGATIVE, impossible pour la machine.\n\nDéplace cet objet vers la droite dans l'éditeur vectoriel, ou réduis la distance de surbalayage (menu '{tab_grbl}') avant de générer.",
        "en": "Layer “{name}” (Fill Engraving) starts too close to the left edge for the configured overscan ({overscan:.2f} mm): the start point would be at X={start:.2f} mm — a NEGATIVE position, impossible for the machine.\n\nMove this object to the right in the vector editor, or reduce the overscan distance ('{tab_grbl}' menu) before generating.",
        "de": "Die Ebene „{name}“ (Gefüllte Gravur) beginnt zu nah am linken Rand für den eingestellten Overscan ({overscan:.2f} mm): Der Startpunkt läge bei X={start:.2f} mm — eine NEGATIVE Position, für die Maschine unmöglich.\n\nVerschiebe dieses Objekt im Vektor-Editor nach rechts oder verringere den Overscan-Abstand (Menü '{tab_grbl}'), bevor du generierst.",
        "es": "La capa «{name}» (Grabado relleno) empieza demasiado cerca del borde izquierdo para el sobrebarrido configurado ({overscan:.2f} mm): el punto de inicio estaría en X={start:.2f} mm — una posición NEGATIVA, imposible para la máquina.\n\nMueve este objeto hacia la derecha en el editor vectorial, o reduce la distancia de sobrebarrido (menú '{tab_grbl}') antes de generar.",
    },
    "gen.failed_title": {
        "fr": "Erreur de génération",
        "en": "Generation error",
        "de": "Generierungsfehler",
        "es": "Error de generación",
    },
    "gen.failed_body": {
        "fr": "La génération du G-Code a échoué :\n\n{error}",
        "en": "G-code generation failed:\n\n{error}",
        "de": "Die G-Code-Generierung ist fehlgeschlagen:\n\n{error}",
        "es": "La generación del G-code falló:\n\n{error}",
    },
    "gen.in_progress": {
        "fr": "Génération en cours…",
        "en": "Generating…",
        "de": "Generierung läuft…",
        "es": "Generando…",
    },
    "gen.in_progress_pct": {
        "fr": "Génération en cours… {pct}%",
        "en": "Generating… {pct}%",
        "de": "Generierung läuft… {pct}%",
        "es": "Generando… {pct}%",
    },
    "gen.done": {
        "fr": "Terminé ✓",
        "en": "Done ✓",
        "de": "Fertig ✓",
        "es": "Listo ✓",
    },
    "gen.preview_error_title": {
        "fr": "Aperçu 2D",
        "en": "2D Preview",
        "de": "2D-Vorschau",
        "es": "Vista previa 2D",
    },
    "gen.preview_error_body": {
        "fr": "L'aperçu 2D n'a pas pu être généré pour ce G-Code :\n{error}",
        "en": "The 2D preview could not be generated for this G-code:\n{error}",
        "de": "Die 2D-Vorschau konnte für diesen G-Code nicht erzeugt werden:\n{error}",
        "es": "No se pudo generar la vista previa 2D para este G-code:\n{error}",
    },
    "gen.stat_lines": {
        "fr": "Lignes: {n}",
        "en": "Lines: {n}",
        "de": "Zeilen: {n}",
        "es": "Líneas: {n}",
    },
    "gen.stat_power": {
        "fr": "Puissance Moyenne: {value} %",
        "en": "Average Power: {value} %",
        "de": "Durchschnittliche Leistung: {value} %",
        "es": "Potencia media: {value} %",
    },
    "gen.stat_time": {
        "fr": "Temps Estimé: {value}",
        "en": "Estimated Time: {value}",
        "de": "Geschätzte Zeit: {value}",
        "es": "Tiempo estimado: {value}",
    },
    "gen.stat_power_imported": {
        "fr": "Puissance Moyenne: — (fichier importé)",
        "en": "Average Power: — (imported file)",
        "de": "Durchschnittliche Leistung: — (importierte Datei)",
        "es": "Potencia media: — (archivo importado)",
    },
    "gen.stat_time_imported": {
        "fr": "Temps Estimé: — (fichier importé)",
        "en": "Estimated Time: — (imported file)",
        "de": "Geschätzte Zeit: — (importierte Datei)",
        "es": "Tiempo estimado: — (archivo importado)",
    },
    "gen.legend_raster": {
        "fr": "Gravure Image (Raster)",
        "en": "Image Engraving (Raster)",
        "de": "Bildgravur (Raster)",
        "es": "Grabado de imagen (Raster)",
    },
    "gen.legend_unknown": {
        "fr": "G-Code (import ou sans calque identifié)",
        "en": "G-code (imported or no identified layer)",
        "de": "G-Code (importiert oder keine erkannte Ebene)",
        "es": "G-code (importado o sin capa identificada)",
    },
    "gen.legend_svg_cut": {
        "fr": "Découpe SVG (import)",
        "en": "SVG Cut (import)",
        "de": "SVG-Schnitt (Import)",
        "es": "Corte SVG (importación)",
    },
    "gen.legend_test_matrix": {
        "fr": "Matrice de test",
        "en": "Test matrix",
        "de": "Testmatrix",
        "es": "Matriz de prueba",
    },
    "gen.legend_layer": {
        "fr": "Calque « {name} »",
        "en": "Layer “{name}”",
        "de": "Ebene „{name}“",
        "es": "Capa «{name}»",
    },
    "gen.legend_g0": {
        "fr": "G0 Rapide ({n} segments)",
        "en": "G0 Rapid ({n} segments)",
        "de": "G0 Eilgang ({n} Segmente)",
        "es": "G0 Rápido ({n} segmentos)",
    },
    "gen.legend_burned": {
        "fr": "Déjà gravé (pendant l'envoi)", "en": "Already engraved (while sending)",
        "de": "Bereits graviert (während des Sendens)", "es": "Ya grabado (durante el envío)",
    },
    "gen.legend_overscan": {
        "fr": "Overscan ({n} segments)",
        "en": "Overscan ({n} segments)",
        "de": "Overscan ({n} Segmente)",
        "es": "Sobrebarrido ({n} segmentos)",
    },
    "gen.legend_g1_travel": {
        "fr": "Déplacement G1 sans gravure ({n} segments)",
        "en": "G1 travel without engraving ({n} segments)",
        "de": "G1-Verfahrweg ohne Gravur ({n} Segmente)",
        "es": "Desplazamiento G1 sin grabado ({n} segmentos)",
    },
    "gen.legend_layer_raster_note": {
        "fr": "{label} ({n} segments — rendu en image ci-dessous)",
        "en": "{label} ({n} segments — rendered as image below)",
        "de": "{label} ({n} Segmente — unten als Bild dargestellt)",
        "es": "{label} ({n} segmentos — mostrado como imagen abajo)",
    },
    "gen.legend_layer_segments": {
        "fr": "{label} ({n} segments)",
        "en": "{label} ({n} segments)",
        "de": "{label} ({n} Segmente)",
        "es": "{label} ({n} segmentos)",
    },
    "usb.help_title": {
        "fr": "Port introuvable ?", "en": "Port not showing up?",
        "de": "Port nicht gefunden?", "es": "¿No aparece el puerto?",
    },
    "usb.driver_hint": {
        "fr": "Port introuvable ? Installe le driver USB de ton contrôleur (le plus courant : CH340) : <a href='https://www.wch-ic.com/downloads/CH341SER_EXE.html'>CH340</a> · <a href='https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers'>CP210x</a> · <a href='https://ftdichip.com/drivers/vcp-drivers/'>FTDI</a>. Sous Linux, aucun driver à installer, mais ton utilisateur doit être dans le groupe « dialout ».",
        "en": "Port not showing up? Install your controller's USB driver (most common: CH340): <a href='https://www.wch-ic.com/downloads/CH341SER_EXE.html'>CH340</a> · <a href='https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers'>CP210x</a> · <a href='https://ftdichip.com/drivers/vcp-drivers/'>FTDI</a>. On Linux no driver is needed, but your user must be in the \"dialout\" group.",
        "de": "Port nicht gefunden? Installiere den USB-Treiber deines Controllers (am häufigsten: CH340): <a href='https://www.wch-ic.com/downloads/CH341SER_EXE.html'>CH340</a> · <a href='https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers'>CP210x</a> · <a href='https://ftdichip.com/drivers/vcp-drivers/'>FTDI</a>. Unter Linux ist kein Treiber nötig, aber dein Benutzer muss in der Gruppe „dialout“ sein.",
        "es": "¿No aparece el puerto? Instala el driver USB de tu controlador (el más común: CH340): <a href='https://www.wch-ic.com/downloads/CH341SER_EXE.html'>CH340</a> · <a href='https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers'>CP210x</a> · <a href='https://ftdichip.com/drivers/vcp-drivers/'>FTDI</a>. En Linux no hace falta driver, pero tu usuario debe estar en el grupo «dialout».",
    },
    "ui.mat_lmm_auto_tooltip": {
        "fr": "Repris automatiquement des réglages de l'onglet « Graver une image »",
        "en": "Automatically taken from the settings of the \"Engrave an Image\" tab",
        "de": "Automatisch aus den Einstellungen des Tabs „Bild gravieren“ übernommen",
        "es": "Tomado automáticamente de los ajustes de la pestaña «Grabar una imagen»",
    },
    "ui.support_button_tooltip": {
        "fr": "Soutenir le développement ☕",
        "en": "Support development ☕",
        "de": "Entwicklung unterstützen ☕",
        "es": "Apoyar el desarrollo ☕",
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
    "sep.black_is_engraved": {
        "fr": "Le noir est la zone gravée", "en": "Black is engraved area",
        "de": "Schwarz ist gravierter Bereich", "es": "El negro es la zona grabada",
    },
    "sep.mirror_engraving": {
        "fr": "Miroir horizontal (gravure)", "en": "Horizontal mirror (engraving)",
        "de": "Horizontal spiegeln (Gravur)", "es": "Espejo horizontal (grabado)",
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
    "sep.choose_format_prompt": {
        "fr": "Choisis le format de fichier pour le calque couleur :",
        "en": "Choose the file format for the color layer:",
        "de": "Wähle das Dateiformat für die Farbebene:",
        "es": "Elige el formato de archivo para la capa de color:",
    },
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
    "splash.initializing": {
        "fr": "Initialisation de Laser Studio Pro...",
        "en": "Initializing Laser Studio Pro...",
        "de": "Laser Studio Pro wird initialisiert...",
        "es": "Inicializando Laser Studio Pro...",
    },
    "splash.ready": {
        "fr": "Prêt !",
        "en": "Ready!",
        "de": "Bereit!",
        "es": "¡Listo!",
    },
    "ui.vector_width_mm": {
        "fr": "Largeur :",
        "en": "Width:",
        "de": "Breite:",
        "es": "Ancho:",
    },
    "ui.vector_height_mm": {
        "fr": "Hauteur :",
        "en": "Height:",
        "de": "Höhe:",
        "es": "Alto:",
    },
    "ui.vector_anchor": {
        "fr": "Ancrage :",
        "en": "Anchor:",
        "de": "Anker:",
        "es": "Anclaje:",
    },
    "ui.vector_anchor_lock": {
        "fr": "Verrouiller l'ancrage",
        "en": "Lock anchor",
        "de": "Anker sperren",
        "es": "Bloquear anclaje",
    },
    "ui.vector_anchor_lock_tip": {
        "fr": "Garde le point d'ancrage choisi fixe quand la taille change.",
        "en": "Keeps the chosen anchor point fixed when the size changes.",
        "de": "Hält den gewählten Ankerpunkt bei Größenänderung fest.",
        "es": "Mantiene fijo el punto de anclaje elegido al cambiar el tamaño.",
    },
    "ui.vector_anchor_tip": {
        "fr": "Point de l'objet qui reste en place lors d'un redimensionnement.",
        "en": "Point of the object that stays in place when resizing.",
        "de": "Punkt des Objekts, der beim Skalieren an Ort und Stelle bleibt.",
        "es": "Punto del objeto que permanece en su sitio al redimensionar.",
    },
    "ui.vector_anchor_origin": {
        "fr": "Origine (0,0)",
        "en": "Origin (0,0)",
        "de": "Ursprung (0,0)",
        "es": "Origen (0,0)",
    },
    "ui.vector_anchor_bl": {
        "fr": "Bas-gauche",
        "en": "Bottom-left",
        "de": "Unten links",
        "es": "Abajo a la izquierda",
    },
    "ui.vector_anchor_br": {
        "fr": "Bas-droite",
        "en": "Bottom-right",
        "de": "Unten rechts",
        "es": "Abajo a la derecha",
    },
    "ui.vector_anchor_tl": {
        "fr": "Haut-gauche",
        "en": "Top-left",
        "de": "Oben links",
        "es": "Arriba a la izquierda",
    },
    "ui.vector_anchor_tr": {
        "fr": "Haut-droite",
        "en": "Top-right",
        "de": "Oben rechts",
        "es": "Arriba a la derecha",
    },
    "ui.vector_tool_measure": {
        "fr": "Mesure",
        "en": "Measure",
        "de": "Messen",
        "es": "Medir",
    },
    "ui.vector_tool_measure_tip": {
        "fr": "Mesurer une distance : clic-glisser sur le canevas.",
        "en": "Measure a distance: click and drag on the canvas.",
        "de": "Abstand messen: auf der Zeichenfläche klicken und ziehen.",
        "es": "Medir una distancia: haga clic y arrastre en el lienzo.",
    },

    "startup.safety.title": {
        "fr": "Avertissement de sécurité",
        "en": "Safety warning",
        "de": "Sicherheitshinweis",
        "es": "Advertencia de seguridad",
    },
    "startup.safety.body": {
        "fr": "Un graveur laser est une machine dangereuse qui ne doit jamais fonctionner sans surveillance.",
        "en": "A laser engraver is a dangerous machine and must never run unattended.",
        "de": "Ein Lasergravierer ist eine gefährliche Maschine und darf niemals unbeaufsichtigt laufen.",
        "es": "Un grabador láser es una máquina peligrosa y nunca debe funcionar sin supervisión.",
    },
    "startup.safety.detail": {
        "fr": "L'utilisateur reste seul responsable des fichiers envoyés à sa machine.",
        "en": "You remain solely responsible for the files sent to your machine.",
        "de": "Du bleibst allein verantwortlich für die Dateien, die an deine Maschine gesendet werden.",
        "es": "El usuario es el único responsable de los archivos enviados a su máquina.",
    },
    "startup.safety.dont_show": {
        "fr": "Ne plus afficher à chaque démarrage (rappel tous les {n} démarrages)",
        "en": "Don't show at every startup (reminder every {n} startups)",
        "de": "Nicht bei jedem Start anzeigen (Erinnerung alle {n} Starts)",
        "es": "No mostrar en cada inicio (recordatorio cada {n} inicios)",
    },
    "startup.safety.ok": {
        "fr": "OK",
        "en": "OK",
        "de": "OK",
        "es": "Aceptar",
    },
    "startup.safety.cancel": {
        "fr": "Annuler",
        "en": "Cancel",
        "de": "Abbrechen",
        "es": "Cancelar",
    },

    # --- Caméra (alignement plateau) ---
    "menu.tools.camera": {
        "fr": "Caméra…",
        "en": "Camera…",
        "de": "Kamera…",
        "es": "Cámara…",
    },
    "camera.dialog_title": {
        "fr": "Caméra",
        "en": "Camera",
        "de": "Kamera",
        "es": "Cámara",
    },
    "camera.group.device": {
        "fr": "Appareil",
        "en": "Device",
        "de": "Gerät",
        "es": "Dispositivo",
    },
    "camera.group.status": {
        "fr": "État",
        "en": "Status",
        "de": "Status",
        "es": "Estado",
    },
    "camera.label.device": {
        "fr": "Webcam",
        "en": "Webcam",
        "de": "Webcam",
        "es": "Webcam",
    },
    "camera.btn.refresh_devices": {
        "fr": "Actualiser la liste",
        "en": "Refresh list",
        "de": "Liste aktualisieren",
        "es": "Actualizar lista",
    },
    "camera.btn.calibrate_lens": {
        "fr": "Calibrer l'objectif…",
        "en": "Calibrate lens…",
        "de": "Objektiv kalibrieren…",
        "es": "Calibrar objetivo…",
    },
    "camera.btn.align_workspace": {
        "fr": "Aligner sur le plateau…",
        "en": "Align to workspace…",
        "de": "Auf Arbeitsfläche ausrichten…",
        "es": "Alinear al área de trabajo…",
    },
    "camera.btn.refresh_overlay": {
        "fr": "Afficher la caméra dans l'éditeur",
        "en": "Show camera in the editor",
        "de": "Kamera im Editor anzeigen",
        "es": "Mostrar la cámara en el editor",
    },
    "camera.no_device": {
        "fr": "Aucune webcam détectée",
        "en": "No webcam detected",
        "de": "Keine Webcam erkannt",
        "es": "Ninguna webcam detectada",
    },
    "camera.status.none": {
        "fr": "Aucune caméra sélectionnée.",
        "en": "No camera selected.",
        "de": "Keine Kamera ausgewählt.",
        "es": "Ninguna cámara seleccionada.",
    },
    "camera.status.summary": {
        "fr": "Caméra : {name}\nCalibration optique : {lens}\nAlignement plateau : {align}",
        "en": "Camera: {name}\nLens calibration: {lens}\nWorkspace alignment: {align}",
        "de": "Kamera: {name}\nObjektivkalibrierung: {lens}\nArbeitsflächen-Ausrichtung: {align}",
        "es": "Cámara: {name}\nCalibración óptica: {lens}\nAlineación del área: {align}",
    },
    "camera.status.yes": {"fr": "oui", "en": "yes", "de": "ja", "es": "sí"},
    "camera.status.no": {"fr": "non", "en": "no", "de": "nein", "es": "no"},
    "camera.status.active": {
        "fr": "Caméra active : {name}",
        "en": "Active camera: {name}",
        "de": "Aktive Kamera: {name}",
        "es": "Cámara activa: {name}",
    },
    "camera.status.overlay_ok": {
        "fr": "Image de la caméra mise à jour dans l'éditeur vectoriel (sous la grille).",
        "en": "Camera image updated in the vector editor (under the grid).",
        "de": "Kamerabild im Vektoreditor aktualisiert (unter dem Raster).",
        "es": "Imagen de la cámara actualizada en el editor vectorial (bajo la cuadrícula).",
    },
    "camera.overlay_opacity": {
        "fr": "Opacité de l'image :",
        "en": "Image opacity:",
        "de": "Bilddeckkraft:",
        "es": "Opacidad de la imagen:",
    },
    "camera.btn.clear_overlay": {
        "fr": "Retirer l'image",
        "en": "Remove image",
        "de": "Bild entfernen",
        "es": "Quitar imagen",
    },
    "camera.status.lens_ok": {
        "fr": "Calibration optique enregistrée (erreur {error} px).",
        "en": "Lens calibration saved (error {error} px).",
        "de": "Objektivkalibrierung gespeichert (Fehler {error} px).",
        "es": "Calibración óptica guardada (error {error} px).",
    },
    "camera.status.align_ok": {
        "fr": "Alignement enregistré ({tags} tags, erreur {error} mm).",
        "en": "Alignment saved ({tags} tags, error {error} mm).",
        "de": "Ausrichtung gespeichert ({tags} Tags, Fehler {error} mm).",
        "es": "Alineación guardada ({tags} etiquetas, error {error} mm).",
    },
    "camera.err.no_device": {
        "fr": "Choisissez d'abord une webcam.",
        "en": "Select a webcam first.",
        "de": "Bitte zuerst eine Webcam wählen.",
        "es": "Seleccione primero una webcam.",
    },
    "camera.err.not_ready": {
        "fr": "Calibration optique et alignement requis avant l'overlay.",
        "en": "Lens calibration and workspace alignment are required before overlay.",
        "de": "Objektivkalibrierung und Ausrichtung sind vor dem Overlay erforderlich.",
        "es": "Se requieren calibración óptica y alineación antes de la superposición.",
    },
    "camera.err.capture": {
        "fr": "Échec de la capture : {error}",
        "en": "Capture failed: {error}",
        "de": "Aufnahme fehlgeschlagen: {error}",
        "es": "Fallo de captura: {error}",
    },
    "camera.err.need_lens_first": {
        "fr": "Calibrez d'abord l'objectif.",
        "en": "Calibrate the lens first.",
        "de": "Bitte zuerst das Objektiv kalibrieren.",
        "es": "Calibre primero el objetivo.",
    },
    "camera.wizard.next": {
        "fr": "Suivant",
        "en": "Next",
        "de": "Weiter",
        "es": "Siguiente",
    },
    "camera.wizard.close": {
        "fr": "Fermer",
        "en": "Close",
        "de": "Schließen",
        "es": "Cerrar",
    },

    # --- Wizard calibration optique ---
    "camera.lens_wizard.title": {
        "fr": "Calibration de l'objectif",
        "en": "Lens calibration",
        "de": "Objektivkalibrierung",
        "es": "Calibración del objetivo",
    },
    "camera.lens_wizard.intro": {
        "fr": "Imprimez un damier 9×6 (coins intérieurs), collez-le sur une surface plane, puis capturez au moins 8 vues sous des angles et distances variés. L'éclairage doit être uniforme, sans reflets.",
        "en": "Print a 9×6 chessboard (inner corners), place it on a flat surface, then capture at least 8 views from varied angles and distances. Use even lighting without glare.",
        "de": "Drucken Sie ein 9×6-Schachbrett (innere Ecken), legen Sie es flach hin und nehmen Sie mindestens 8 Ansichten aus unterschiedlichen Winkeln und Abständen auf. Gleichmäßige Beleuchtung ohne Reflexe.",
        "es": "Imprima un tablero 9×6 (esquinas interiores), colóquelo plano y capture al menos 8 vistas desde ángulos y distancias variados. Iluminación uniforme sin reflejos.",
    },
    "camera.lens_wizard.save_board": {
        "fr": "Enregistrer le damier à imprimer…",
        "en": "Save chessboard image…",
        "de": "Schachbrett zum Drucken speichern…",
        "es": "Guardar tablero para imprimir…",
    },
    "camera.group.prepare": {
        "fr": "Préparer la calibration",
        "en": "Prepare the calibration",
        "de": "Kalibrierung vorbereiten",
        "es": "Preparar la calibración",
    },
    "camera.prepare.hint": {
        "fr": "1. Imprimez le damier et les AprilTags (ou enregistrez-les en PDF). 2. Ajoutez le gabarit à l'éditeur et marquez-le au laser : les cadres et numéros indiquent où coller chaque tag. 3. Collez les tags imprimés dans leurs cadres, puis lancez la calibration.",
        "en": "1. Print the chessboard and the AprilTags (or save them as PDF). 2. Add the template to the editor and mark it with the laser: the frames and numbers show where to stick each tag. 3. Stick the printed tags in their frames, then start the calibration.",
        "de": "1. Schachbrett und AprilTags drucken (oder als PDF speichern). 2. Die Schablone in den Editor einfügen und mit dem Laser markieren: Rahmen und Nummern zeigen, wo jeder Tag aufgeklebt wird. 3. Die gedruckten Tags in die Rahmen kleben und die Kalibrierung starten.",
        "es": "1. Imprima el tablero y los AprilTags (o guárdelos en PDF). 2. Añada la plantilla al editor y márquela con el láser: los marcos y números indican dónde pegar cada tag. 3. Pegue los tags impresos en sus marcos y inicie la calibración.",
    },
    "camera.prepare.board": {
        "fr": "Damier (calibration optique)",
        "en": "Chessboard (lens calibration)",
        "de": "Schachbrett (Objektivkalibrierung)",
        "es": "Tablero (calibración óptica)",
    },
    "camera.prepare.tags": {
        "fr": "AprilTags (alignement du plateau)",
        "en": "AprilTags (bed alignment)",
        "de": "AprilTags (Bettausrichtung)",
        "es": "AprilTags (alineación de la mesa)",
    },
    "camera.prepare.print": {
        "fr": "Imprimer…",
        "en": "Print…",
        "de": "Drucken…",
        "es": "Imprimir…",
    },
    "camera.prepare.pdf": {
        "fr": "PDF…",
        "en": "PDF…",
        "de": "PDF…",
        "es": "PDF…",
    },
    "camera.prepare.template": {
        "fr": "Ajouter le gabarit des tags à l'éditeur vectoriel (cadres + numéros)",
        "en": "Add the tag template to the vector editor (frames + numbers)",
        "de": "Tag-Schablone in den Vektoreditor einfügen (Rahmen + Nummern)",
        "es": "Añadir la plantilla de tags al editor vectorial (marcos + números)",
    },
    "camera.template.title": {
        "fr": "Gabarit des AprilTags",
        "en": "AprilTag template",
        "de": "AprilTag-Schablone",
        "es": "Plantilla de AprilTags",
    },
    "camera.template.added": {
        "fr": "Gabarit ajouté sur le calque « {layer} » : {n} cadres de {size} mm, aux positions exactes du plateau, avec leur numéro.\n\nMarquez-le au laser (faible puissance) sur le plateau sans bouger la pièce, puis collez chaque tag imprimé dans son cadre, sous le bon numéro.",
        "en": "Template added on layer \"{layer}\": {n} frames of {size} mm at the exact bed positions, with their numbers.\n\nMark it with the laser (low power) on the bed without moving the piece, then stick each printed tag in its frame, under the right number.",
        "de": "Schablone auf Ebene „{layer}“ hinzugefügt: {n} Rahmen von {size} mm an den exakten Positionen der Fläche, mit ihren Nummern.\n\nMit dem Laser (niedrige Leistung) auf der Fläche markieren, ohne das Werkstück zu bewegen, dann jeden gedruckten Tag in seinen Rahmen unter der richtigen Nummer kleben.",
        "es": "Plantilla añadida en la capa «{layer}»: {n} marcos de {size} mm en las posiciones exactas del área, con su número.\n\nMárquela con el láser (baja potencia) sin mover la pieza y pegue cada tag impreso en su marco, bajo el número correcto.",
    },
    "camera.print.pdf_saved": {
        "fr": "PDF enregistré :\n{path}\n\nImprimez-le à 100 % (taille réelle).",
        "en": "PDF saved:\n{path}\n\nPrint it at 100% (actual size).",
        "de": "PDF gespeichert:\n{path}\n\nMit 100 % (Originalgröße) drucken.",
        "es": "PDF guardado:\n{path}\n\nImprímalo al 100 % (tamaño real).",
    },
    "camera.print.board_button": {
        "fr": "Imprimer le damier…",
        "en": "Print the chessboard…",
        "de": "Schachbrett drucken…",
        "es": "Imprimir el tablero…",
    },
    "camera.print.board_title": {
        "fr": "Imprimer le damier de calibration",
        "en": "Print the calibration chessboard",
        "de": "Kalibrier-Schachbrett drucken",
        "es": "Imprimir el tablero de calibración",
    },
    "camera.print.board_caption": {
        "fr": "Damier {cols}×{rows} coins intérieurs — case de {square} mm. Imprimer à 100 % (taille réelle), sans « Ajuster à la page ».",
        "en": "Chessboard {cols}×{rows} inner corners — {square} mm squares. Print at 100% (actual size), without “Fit to page”.",
        "de": "Schachbrett {cols}×{rows} innere Ecken — Felder von {square} mm. Mit 100 % (Originalgröße) drucken, ohne „An Seite anpassen“.",
        "es": "Tablero {cols}×{rows} esquinas interiores — casillas de {square} mm. Imprimir al 100 % (tamaño real), sin «Ajustar a la página».",
    },
    "camera.print.tags_button": {
        "fr": "Imprimer les AprilTags (taille réelle)…",
        "en": "Print the AprilTags (actual size)…",
        "de": "AprilTags drucken (Originalgröße)…",
        "es": "Imprimir los AprilTags (tamaño real)…",
    },
    "camera.print.tags_title": {
        "fr": "Imprimer les AprilTags d'alignement",
        "en": "Print the alignment AprilTags",
        "de": "Ausrichtungs-AprilTags drucken",
        "es": "Imprimir los AprilTags de alineación",
    },
    "camera.print.tag_label": {
        "fr": "Tag {id} — centre X {x} mm, Y {y} mm",
        "en": "Tag {id} — centre X {x} mm, Y {y} mm",
        "de": "Tag {id} — Mitte X {x} mm, Y {y} mm",
        "es": "Tag {id} — centro X {x} mm, Y {y} mm",
    },
    "camera.print.tags_footer": {
        "fr": "Imprimer à 100 % (taille réelle). Découper chaque tag ({size} mm) avec sa zone claire, puis le poser à plat, centre sur la position indiquée (origine en bas à gauche du plateau).",
        "en": "Print at 100% (actual size). Cut out each tag ({size} mm) with its white border, then lay it flat with its centre on the position shown (origin at the bottom-left of the bed).",
        "de": "Mit 100 % (Originalgröße) drucken. Jeden Tag ({size} mm) mit weißem Rand ausschneiden und flach mit der Mitte auf die angegebene Position legen (Ursprung unten links am Bett).",
        "es": "Imprimir al 100 % (tamaño real). Recorte cada tag ({size} mm) con su margen blanco y colóquelo plano, con el centro en la posición indicada (origen abajo a la izquierda de la mesa).",
    },
    "camera.print.error": {
        "fr": "Impossible de lancer l'impression.",
        "en": "Could not start printing.",
        "de": "Der Druck konnte nicht gestartet werden.",
        "es": "No se pudo iniciar la impresión.",
    },
    "camera.lens_wizard.board_saved": {
        "fr": "Damier enregistré :\n{path}",
        "en": "Chessboard saved:\n{path}",
        "de": "Schachbrett gespeichert:\n{path}",
        "es": "Tablero guardado:\n{path}",
    },
    "camera.lens_wizard.capture_help": {
        "fr": "Présentez le damier devant la caméra. Quand les coins verts apparaissent, cliquez sur Capturer. Variez l'angle et la distance.",
        "en": "Show the chessboard to the camera. When green corners appear, click Capture. Vary angle and distance.",
        "de": "Zeigen Sie das Schachbrett der Kamera. Wenn grüne Ecken erscheinen, auf Aufnehmen klicken. Winkel und Abstand variieren.",
        "es": "Muestre el tablero a la cámara. Cuando aparezcan esquinas verdes, pulse Capturar. Varíe ángulo y distancia.",
    },
    "camera.lens_wizard.snap": {
        "fr": "Capturer cette vue",
        "en": "Capture this view",
        "de": "Diese Ansicht aufnehmen",
        "es": "Capturar esta vista",
    },
    "camera.lens_wizard.clear": {
        "fr": "Effacer les vues",
        "en": "Clear views",
        "de": "Ansichten löschen",
        "es": "Borrar vistas",
    },
    "camera.lens_wizard.compute": {
        "fr": "Calculer la calibration",
        "en": "Compute calibration",
        "de": "Kalibrierung berechnen",
        "es": "Calcular calibración",
    },
    "camera.lens_wizard.need_more": {
        "fr": "Il faut au moins {n} vues (actuellement {have}).",
        "en": "At least {n} views are required (currently {have}).",
        "de": "Mindestens {n} Ansichten erforderlich (aktuell {have}).",
        "es": "Se necesitan al menos {n} vistas (ahora {have}).",
    },
    "camera.lens_wizard.board_not_found": {
        "fr": "Damier non détecté dans cette image. Améliorez le contraste ou l'angle.",
        "en": "Chessboard not detected in this frame. Improve contrast or angle.",
        "de": "Schachbrett in diesem Bild nicht erkannt. Kontrast oder Winkel verbessern.",
        "es": "Tablero no detectado en esta imagen. Mejore el contraste o el ángulo.",
    },
    "camera.lens_wizard.enough": {
        "fr": "Assez de vues capturées. Vous pouvez calculer la calibration.",
        "en": "Enough views captured. You can compute the calibration.",
        "de": "Genug Ansichten aufgenommen. Kalibrierung kann berechnet werden.",
        "es": "Suficientes vistas capturadas. Puede calcular la calibración.",
    },
    "camera.lens_wizard.success": {
        "fr": "Calibration optique enregistrée.\n\nVues utilisées : {views}\nErreur de reprojection : {error} px\nRésolution : {size}\n\nVous pouvez maintenant aligner la caméra sur le plateau.",
        "en": "Lens calibration saved.\n\nViews used: {views}\nReprojection error: {error} px\nResolution: {size}\n\nYou can now align the camera to the workspace.",
        "de": "Objektivkalibrierung gespeichert.\n\nAnsichten: {views}\nReprojektionsfehler: {error} px\nAuflösung: {size}\n\nSie können die Kamera nun auf die Arbeitsfläche ausrichten.",
        "es": "Calibración óptica guardada.\n\nVistas: {views}\nError de reproyección: {error} px\nResolución: {size}\n\nYa puede alinear la cámara al área de trabajo.",
    },
    "camera.lens_wizard.failed": {
        "fr": "Échec de la calibration :\n{error}",
        "en": "Calibration failed:\n{error}",
        "de": "Kalibrierung fehlgeschlagen:\n{error}",
        "es": "Falló la calibración:\n{error}",
    },

    # --- Wizard alignement plateau ---
    "camera.align_wizard.title": {
        "fr": "Alignement sur le plateau",
        "en": "Workspace alignment",
        "de": "Ausrichtung auf die Arbeitsfläche",
        "es": "Alineación al área de trabajo",
    },
    "camera.align_wizard.intro": {
        "fr": "Des AprilTags seront placés sur le plateau (positions en mm). Gravez-les (ou collez des tags imprimés aux mêmes emplacements), puis capturez une vue où la caméra les voit tous.",
        "en": "AprilTags will be placed on the bed (positions in mm). Engrave them (or stick printed tags at the same locations), then capture a view where the camera sees them all.",
        "de": "AprilTags werden auf der Fläche platziert (Positionen in mm). Gravieren Sie sie (oder kleben Sie gedruckte Tags an denselben Stellen) und nehmen Sie eine Ansicht auf, in der die Kamera alle sieht.",
        "es": "Se colocarán AprilTags en el área (posiciones en mm). Grábelos (o pegue etiquetas impresas en las mismas posiciones) y capture una vista donde la cámara los vea todos.",
    },
    "camera.align_wizard.margin": {
        "fr": "Marge depuis le bord",
        "en": "Margin from edge",
        "de": "Randabstand",
        "es": "Margen desde el borde",
    },
    "camera.align_wizard.tag_size": {
        "fr": "Taille d'un tag",
        "en": "Tag size",
        "de": "Tag-Größe",
        "es": "Tamaño de etiqueta",
    },
    "camera.align_wizard.cols": {
        "fr": "Colonnes",
        "en": "Columns",
        "de": "Spalten",
        "es": "Columnas",
    },
    "camera.align_wizard.rows": {
        "fr": "Lignes",
        "en": "Rows",
        "de": "Zeilen",
        "es": "Filas",
    },
    "camera.align_wizard.targets_ok": {
        "fr": "{n} tags sur un plateau {bed} mm.",
        "en": "{n} tags on a {bed} mm bed.",
        "de": "{n} Tags auf einer {bed}-mm-Fläche.",
        "es": "{n} etiquetas en un área de {bed} mm.",
    },
    "camera.align_wizard.engrave_hint": {
        "fr": "Cliquez sur « Ajouter les AprilTags à l'éditeur vectoriel » : ils sont créés en gravure, aux bons emplacements du plateau. Fermez ensuite la caméra, gravez-les sur un matériau clair et mat (carton, contreplaqué clair), sans bouger la pièce, puis rouvrez cet assistant (mêmes réglages) et capturez.",
        "en": "Click \"Add AprilTags to the vector editor\": they are created as engraving at the right places on the bed. Then close the camera window, engrave them on a light, matte material (cardboard, light plywood) without moving the piece, then reopen this wizard (same settings) and capture.",
        "de": "Klicken Sie auf „AprilTags in den Vektoreditor einfügen“: Sie werden als Gravur an den richtigen Stellen der Fläche erzeugt. Schließen Sie danach das Kamerafenster, gravieren Sie sie auf hellem, mattem Material (Karton, helles Sperrholz), ohne das Werkstück zu bewegen, öffnen Sie diesen Assistenten erneut (gleiche Einstellungen) und nehmen Sie auf.",
        "es": "Pulse «Añadir AprilTags al editor vectorial»: se crean como grabado en las posiciones correctas del área. Cierre la ventana de la cámara, grábelos en un material claro y mate (cartón, contrachapado claro) sin mover la pieza, vuelva a abrir este asistente (mismos ajustes) y capture.",
    },
    "camera.align_wizard.add_tags": {
        "fr": "Ajouter les AprilTags à l'éditeur vectoriel (à graver)",
        "en": "Add AprilTags to the vector editor (to engrave)",
        "de": "AprilTags in den Vektoreditor einfügen (zum Gravieren)",
        "es": "Añadir AprilTags al editor vectorial (para grabar)",
    },
    "camera.align_wizard.tags_added": {
        "fr": "{n} AprilTags de {size} mm ajoutés en gravure sur le calque « {layer} », aux positions exactes du plateau.\n\nFermez la caméra, gravez-les sur un matériau clair et mat sans bouger la pièce, puis rouvrez l'assistant : les réglages sont conservés.",
        "en": "{n} AprilTags of {size} mm added as engraving on layer \"{layer}\", at the exact bed positions.\n\nClose the camera window, engrave them on a light, matte material without moving the piece, then reopen the wizard: the settings are kept.",
        "de": "{n} AprilTags mit {size} mm wurden als Gravur auf Ebene „{layer}“ an den exakten Positionen der Fläche hinzugefügt.\n\nSchließen Sie das Kamerafenster, gravieren Sie sie auf hellem, mattem Material, ohne das Werkstück zu bewegen, und öffnen Sie den Assistenten erneut: die Einstellungen bleiben erhalten.",
        "es": "Se añadieron {n} AprilTags de {size} mm como grabado en la capa «{layer}», en las posiciones exactas del área.\n\nCierre la cámara, grábelos en un material claro y mate sin mover la pieza y vuelva a abrir el asistente: los ajustes se conservan.",
    },
    "camera.align_wizard.tags_unavailable": {
        "fr": "L'éditeur vectoriel n'est pas disponible depuis cette fenêtre.",
        "en": "The vector editor is not available from this window.",
        "de": "Der Vektoreditor ist von diesem Fenster aus nicht verfügbar.",
        "es": "El editor vectorial no está disponible desde esta ventana.",
    },
    "camera.align_wizard.capture_help": {
        "fr": "Placez les tags dans le champ de la caméra. Les centres détectés s'affichent en vert. Capturez quand assez de tags sont vus (≥ 4).",
        "en": "Place the tags in the camera field of view. Detected centres show in green. Capture when enough tags are seen (≥ 4).",
        "de": "Tags im Kamerabild platzieren. Erkannte Zentren erscheinen grün. Aufnehmen, wenn genug Tags sichtbar sind (≥ 4).",
        "es": "Coloque las etiquetas en el campo de la cámara. Los centros detectados se muestran en verde. Capture cuando se vean suficientes (≥ 4).",
    },
    "camera.align_wizard.snap": {
        "fr": "Capturer pour l'alignement",
        "en": "Capture for alignment",
        "de": "Für Ausrichtung aufnehmen",
        "es": "Capturar para alineación",
    },
    "camera.align_wizard.compute": {
        "fr": "Calculer l'alignement",
        "en": "Compute alignment",
        "de": "Ausrichtung berechnen",
        "es": "Calcular alineación",
    },
    "camera.align_wizard.detected": {
        "fr": "Tags détectés : {found} / {total}",
        "en": "Tags detected: {found} / {total}",
        "de": "Tags erkannt: {found} / {total}",
        "es": "Etiquetas detectadas: {found} / {total}",
    },
    "camera.align_wizard.need_snap": {
        "fr": "Capturez d'abord une image.",
        "en": "Capture an image first.",
        "de": "Bitte zuerst ein Bild aufnehmen.",
        "es": "Capture primero una imagen.",
    },
    "camera.align_wizard.bad_grid": {
        "fr": "Grille invalide (il faut au moins 4 tags sur le plateau).",
        "en": "Invalid grid (at least 4 tags required on the bed).",
        "de": "Ungültiges Raster (mindestens 4 Tags auf der Fläche).",
        "es": "Cuadrícula no válida (se necesitan al menos 4 etiquetas).",
    },
    "camera.align_wizard.success": {
        "fr": "Alignement enregistré.\n\nTags utilisés : {tags}\nErreur de reprojection : {error} mm\nImage : {size}\n\nVous pouvez actualiser l'overlay depuis le dialogue Caméra.",
        "en": "Alignment saved.\n\nTags used: {tags}\nReprojection error: {error} mm\nImage: {size}\n\nYou can refresh the overlay from the Camera dialog.",
        "de": "Ausrichtung gespeichert.\n\nTags: {tags}\nReprojektionsfehler: {error} mm\nBild: {size}\n\nOverlay kann im Kamera-Dialog aktualisiert werden.",
        "es": "Alineación guardada.\n\nEtiquetas: {tags}\nError de reproyección: {error} mm\nImagen: {size}\n\nPuede actualizar la superposición desde el diálogo Cámara.",
    },
    "camera.align_wizard.failed": {
        "fr": "Échec de l'alignement :\n{error}",
        "en": "Alignment failed:\n{error}",
        "de": "Ausrichtung fehlgeschlagen:\n{error}",
        "es": "Falló la alineación:\n{error}",
    },
    "menu.tools.keychain": {
        "fr": "Générateur de porte-clés...",
        "en": "Keychain generator...",
        "de": "Schlüsselanhänger-Generator...",
        "es": "Generador de llaveros...",
    },
    "ui.vector_keychain_generator": {
        "fr": "Porte-clés",
        "en": "Keychain",
        "de": "Anhänger",
        "es": "Llavero",
    },
    "ui.vector_keychain_generator_tip": {
        "fr": "Générer un porte-clés prénom personnalisé (base découpée + texte gravé)",
        "en": "Generate a custom name keychain (cut base + engraved text)",
        "de": "Personalisierten Namens-Schlüsselanhänger erstellen (Schnittbasis + gravierter Text)",
        "es": "Generar un llavero con nombre personalizado (base cortada + texto grabado)",
    },
    "keychain.title": {
        "fr": "Générateur de porte-clés",
        "en": "Keychain generator",
        "de": "Schlüsselanhänger-Generator",
        "es": "Generador de llaveros",
    },
    "keychain.error": {
        "fr": "Erreur porte-clés",
        "en": "Keychain error",
        "de": "Schlüsselanhänger-Fehler",
        "es": "Error de llavero",
    },
    "keychain.done": {
        "fr": "Porte-clés {w:.1f}×{h:.1f} mm généré.",
        "en": "Keychain {w:.1f}×{h:.1f} mm generated.",
        "de": "Schlüsselanhänger {w:.1f}×{h:.1f} mm erzeugt.",
        "es": "Llavero {w:.1f}×{h:.1f} mm generado.",
    },
    "keychain.done_two_layers": {
        "fr": "Porte-clés 2 couches {w:.1f}×{h:.1f} mm généré (fond + lettres + guide de collage).",
        "en": "2-layer keychain {w:.1f}×{h:.1f} mm generated (base + letters + glue guide).",
        "de": "2-Schicht-Schlüsselanhänger {w:.1f}×{h:.1f} mm erzeugt (Basis + Buchstaben + Klebehilfe).",
        "es": "Llavero de 2 capas {w:.1f}×{h:.1f} mm generado (fondo + letras + guía de pegado).",
    },
    "keychain.text": {
        "fr": "Texte / Prénom(s) :",
        "en": "Text / Name(s):",
        "de": "Text / Name(n):",
        "es": "Texto / Nombre(s):",
    },
    "keychain.text_placeholder": {
        "fr": "Un prénom par ligne\n(ex: Emma\nLéa\nNoah)",
        "en": "One name per line\n(e.g. Emma\nLéa\nNoah)",
        "de": "Ein Name pro Zeile\n(z.B. Emma\nLéa\nNoah)",
        "es": "Un nombre por línea\n(ej. Emma\nLéa\nNoah)",
    },
    "keychain.batch_preview": {
        "fr": "{n} porte-clés seront générés au clic sur OK.\n(aperçu désactivé pour les lots)",
        "en": "{n} keychains will be generated when you click OK.\n(preview disabled for batches)",
        "de": "{n} Schlüsselanhänger werden beim Klick auf OK erzeugt.\n(Vorschau für Serien deaktiviert)",
        "es": "Se generarán {n} llaveros al pulsar Aceptar.\n(vista previa desactivada para lotes)",
    },
    "keychain.text_height": {
        "fr": "Hauteur du texte :",
        "en": "Text height:",
        "de": "Texthöhe:",
        "es": "Altura del texto:",
    },
    "keychain.letter_spacing": {
        "fr": "Espacement lettres :",
        "en": "Letter spacing:",
        "de": "Zeichenabstand:",
        "es": "Espaciado de letras:",
    },
    "keychain.margin": {
        "fr": "Bordure autour du texte :",
        "en": "Border around text:",
        "de": "Rand um den Text:",
        "es": "Borde alrededor del texto:",
    },
    "keychain.bridge_isolated": {
        "fr": "Relier les points isolés (i, accents)",
        "en": "Bridge isolated dots/accents",
        "de": "Isolierte Punkte/Akzente verbinden",
        "es": "Unir puntos y acentos aislados",
    },
    "keychain.two_layers": {
        "fr": "2 couches (fond + lettres à coller)",
        "en": "2 layers (base + letters to glue)",
        "de": "2 Schichten (Grund + Buchstaben zum Kleben)",
        "es": "2 capas (fondo + letras para pegar)",
    },
    "keychain.two_layers_tip": {
        "fr": "Génère 2 porte-clés côte à côte :\n• Gauche = fond + contour du prénom (guide de collage)\n• Droite = fond + prénom plein découpé (à coller)",
        "en": "Generates 2 keychains side by side:\n• Left = base + name outline (glue guide)\n• Right = base + solid cut letters (to glue)",
        "de": "Erzeugt 2 Schlüsselanhänger nebeneinander:\n• Links = Basis + Namensumriss (Klebehilfe)\n• Rechts = Basis + ausgeschnittene Buchstaben (zum Kleben)",
        "es": "Genera 2 llaveros uno al lado del otro:\n• Izquierda = fondo + contorno del nombre (guía de pegado)\n• Derecha = fondo + letras macizas cortadas (para pegar)",
    },
    "keychain.ring_position": {
        "fr": "Position de l'anneau :",
        "en": "Ring position:",
        "de": "Ringposition:",
        "es": "Posición del aro:",
    },
    "keychain.ring.Gauche": {"fr": "Gauche", "en": "Left", "de": "Links", "es": "Izquierda"},
    "keychain.ring.Droite": {"fr": "Droite", "en": "Right", "de": "Rechts", "es": "Derecha"},
    "keychain.ring.Haut": {"fr": "Haut", "en": "Top", "de": "Oben", "es": "Arriba"},
    "keychain.ring.Aucun": {"fr": "Aucun", "en": "None", "de": "Keiner", "es": "Ninguno"},
    "keychain.ring_outer": {
        "fr": "Diamètre extérieur anneau :",
        "en": "Ring outer diameter:",
        "de": "Ring-Außendurchmesser:",
        "es": "Diámetro exterior del aro:",
    },
    "keychain.ring_hole": {
        "fr": "Diamètre du trou :",
        "en": "Hole diameter:",
        "de": "Lochdurchmesser:",
        "es": "Diámetro del agujero:",
    },
    "keychain.ring_overlap": {
        "fr": "Chevauchement anneau :",
        "en": "Ring overlap:",
        "de": "Ringüberlappung:",
        "es": "Solapamiento del aro:",
    },
    "keychain.cut_layer": {
        "fr": "Calque de découpe (base) :",
        "en": "Cut layer (base):",
        "de": "Schnittebene (Basis):",
        "es": "Capa de corte (base):",
    },
    "keychain.engrave_layer": {
        "fr": "Calque de gravure (texte) :",
        "en": "Engrave layer (text):",
        "de": "Gravierebene (Text):",
        "es": "Capa de grabado (texto):",
    },
    "keychain.preview": {
        "fr": "Aperçu (rouge = découpe, bleu = gravure/contour, vert = lettres 2e couche) :",
        "en": "Preview (red = cut, blue = engrave/outline, green = 2nd layer letters):",
        "de": "Vorschau (rot = Schnitt, blau = Gravur/Umriss, grün = 2. Schicht Buchstaben):",
        "es": "Vista previa (rojo = corte, azul = grabado/contorno, verde = letras 2ª capa):",
    },
    "keychain.hint": {
        "fr": "Astuce : un prénom par ligne pour un lot. Puis « Dupliquer en série » si besoin.",
        "en": "Tip: one name per line for a batch. Then use 'Serial duplicate' if needed.",
        "de": "Tipp: Ein Name pro Zeile für eine Serie. Danach ggf. 'Serienduplizieren'.",
        "es": "Consejo: un nombre por línea para un lote. Luego 'Duplicar en serie' si hace falta.",
    },
    "keychain.err.empty_text": {
        "fr": "Veuillez saisir un texte ou un prénom.",
        "en": "Please enter a text or name.",
        "de": "Bitte geben Sie einen Text oder Namen ein.",
        "es": "Introduzca un texto o nombre.",
    },
    "keychain.err.text_height": {
        "fr": "La hauteur du texte doit être comprise entre 4 et 150 mm.",
        "en": "Text height must be between 4 and 150 mm.",
        "de": "Texthöhe muss zwischen 4 und 150 mm liegen.",
        "es": "La altura del texto debe estar entre 4 y 150 mm.",
    },
    "keychain.err.margin": {
        "fr": "La bordure doit être comprise entre 1 et 30 mm.",
        "en": "Border must be between 1 and 30 mm.",
        "de": "Der Rand muss zwischen 1 und 30 mm liegen.",
        "es": "El borde debe estar entre 1 y 30 mm.",
    },
    "keychain.err.ring_outer": {
        "fr": "Le diamètre extérieur de l'anneau doit être entre 4 et 40 mm.",
        "en": "Ring outer diameter must be between 4 and 40 mm.",
        "de": "Ring-Außendurchmesser muss zwischen 4 und 40 mm liegen.",
        "es": "El diámetro exterior del aro debe estar entre 4 y 40 mm.",
    },
    "keychain.err.ring_hole": {
        "fr": "Le trou doit être d'au moins 1,5 mm et laisser 1 mm de matière autour.",
        "en": "Hole must be at least 1.5 mm leaving 1 mm wall thickness.",
        "de": "Das Loch muss mindestens 1,5 mm groß sein und 1 mm Rand lassen.",
        "es": "El agujero debe ser de al menos 1,5 mm dejando 1 mm de borde.",
    },
        "ornament.motif.Lune": {
        "fr": "Lune",
        "en": "Moon",
        "de": "Mond",
        "es": "Luna",
    },
        "ornament.motif.Houx": {
        "fr": "Houx",
        "en": "Holly",
        "de": "Stechpalme",
        "es": "Acebo",
    },
        "ornament.motif.Sapin": {
        "fr": "Sapin",
        "en": "Fir tree",
        "de": "Tannenbaum",
        "es": "Abeto",
    },
        "ornament.motif.Cadeau": {
        "fr": "Cadeau",
        "en": "Gift",
        "de": "Geschenk",
        "es": "Regalo",
    },
        "ornament.motif.Bougie": {
        "fr": "Bougie",
        "en": "Candle",
        "de": "Kerze",
        "es": "Vela",
    },
        "ornament.motif.Cloche": {
        "fr": "Cloche",
        "en": "Bell",
        "de": "Glocke",
        "es": "Campana",
    },
        "ornament.motif.Couronne": {
        "fr": "Couronne",
        "en": "Wreath",
        "de": "Kranz",
        "es": "Corona",
    },
        "ornament.motif.Guirlande": {
        "fr": "Guirlande",
        "en": "Garland",
        "de": "Girlande",
        "es": "Guirnalda",
    },
        "ornament.style.Duo": {
        "fr": "Duo",
        "en": "Duo",
        "de": "Duo",
        "es": "Dúo",
    },
        "ornament.style.Contour": {
        "fr": "Contour",
        "en": "Outline",
        "de": "Kontur",
        "es": "Contorno",
    },
        "ornament.style.Plein": {
        "fr": "Plein",
        "en": "Solid",
        "de": "Voll",
        "es": "Sólido",
    },
        "ornament.style.Trio": {
        "fr": "Trio",
        "en": "Trio",
        "de": "Trio",
        "es": "Trío",
    },
        "ornament.support.Bandeau": {
        "fr": "Bandeau",
        "en": "Banner",
        "de": "Banner",
        "es": "Banda",
    },
    "ornament.hanger.Capuchon": {
        "fr": "Capuchon nervuré + anneau",
        "en": "Ribbed cap + ring",
        "de": "Gerippte Kappe + Ring",
        "es": "Capuchón con nervios + anillo",
    },
    "ornament.name_mode": {
        "fr": "Prénom :",
        "en": "Name:",
        "de": "Name:",
        "es": "Nombre:",
    },
    "ornament.name_mode_tip": {
        "fr": "Découpé : les lettres sont soudées à l'anneau et tiennent par la barre. Gravé : le prénom est gravé sur une bande pleine qui traverse la boule.",
        "en": "Cut out: the letters are welded to the ring and held by the bar. Engraved: the name is engraved on a solid band across the ornament.",
        "de": "Ausgeschnitten: Die Buchstaben sind mit dem Ring verschmolzen und halten durch den Steg. Graviert: Der Name wird auf ein durchgehendes Band graviert.",
        "es": "Calado: las letras se sueldan al aro y se sujetan con la barra. Grabado: el nombre se graba en una banda llena que cruza la bola.",
    },
    "ornament.name_mode.Découpé": {
        "fr": "Découpé et lié à l'anneau",
        "en": "Cut out, joined to the ring",
        "de": "Ausgeschnitten, mit dem Ring verbunden",
        "es": "Calado y unido al aro",
    },
    "ornament.name_mode.Gravé": {
        "fr": "Gravé sur la bande",
        "en": "Engraved on the band",
        "de": "Auf das Band graviert",
        "es": "Grabado en la banda",
    },
    "ornament.crown": {
        "fr": "Silhouette :",
        "en": "Silhouette:",
        "de": "Silhouette:",
        "es": "Silueta:",
    },
    "ornament.crown.Aucune": {
        "fr": "Boule seule",
        "en": "Plain ball",
        "de": "Nur Kugel",
        "es": "Solo la bola",
    },
    "ornament.crown.Bois de renne": {
        "fr": "Bois de renne",
        "en": "Reindeer antlers",
        "de": "Rentiergeweih",
        "es": "Cuernos de reno",
    },
    "ornament.fill": {
        "fr": "Remplissage :",
        "en": "Pattern fill:",
        "de": "Musterfüllung:",
        "es": "Relleno:",
    },
    "ornament.fill.Aucun": {
        "fr": "Aucun",
        "en": "None",
        "de": "Keine",
        "es": "Ninguno",
    },
    "ornament.fill.Rayures": {
        "fr": "Rayures",
        "en": "Stripes",
        "de": "Streifen",
        "es": "Rayas",
    },
    "ornament.fill.Treillis": {
        "fr": "Treillis",
        "en": "Lattice",
        "de": "Gitter",
        "es": "Celosía",
    },
    "ornament.fill.Tricot": {
        "fr": "Tricot",
        "en": "Knit",
        "de": "Strickmuster",
        "es": "Punto",
    },
    "ornament.fill.Vagues": {
        "fr": "Vagues",
        "en": "Waves",
        "de": "Wellen",
        "es": "Ondas",
    },
    "ornament.fill.Feuilles": {
        "fr": "Feuilles",
        "en": "Leaves",
        "de": "Blätter",
        "es": "Hojas",
    },
    "ornament.fill_zone": {
        "fr": "Zone du remplissage :",
        "en": "Fill area:",
        "de": "Füllbereich:",
        "es": "Zona del relleno:",
    },
    "ornament.fill_zone.Haut et bas": {
        "fr": "Haut et bas",
        "en": "Top and bottom",
        "de": "Oben und unten",
        "es": "Arriba y abajo",
    },
    "ornament.fill_zone.Haut": {
        "fr": "Haut",
        "en": "Top",
        "de": "Oben",
        "es": "Arriba",
    },
    "ornament.fill_zone.Bas": {
        "fr": "Bas",
        "en": "Bottom",
        "de": "Unten",
        "es": "Abajo",
    },
    "ornament.fill_pitch": {
        "fr": "Pas du motif :",
        "en": "Pattern spacing:",
        "de": "Musterabstand:",
        "es": "Paso del motivo:",
    },
    "ornament.band_height": {
        "fr": "Hauteur de la bande :",
        "en": "Band height:",
        "de": "Bandhöhe:",
        "es": "Altura de la banda:",
    },
    "ornament.band_frame": {
        "fr": "Filet gravé autour du prénom",
        "en": "Engraved line around the name",
        "de": "Gravierte Linie um den Namen",
        "es": "Filete grabado alrededor del nombre",
    },
    "ornament.engrave_layer": {
        "fr": "Calque de gravure :",
        "en": "Engraving layer:",
        "de": "Gravurebene:",
        "es": "Capa de grabado:",
    },
    "ornament.gallery.title": {
        "fr": "Modèles de boules",
        "en": "Ornament templates",
        "de": "Kugelvorlagen",
        "es": "Modelos de bolas",
    },
    "ornament.gallery.button": {
        "fr": "Modèles…",
        "en": "Templates…",
        "de": "Vorlagen…",
        "es": "Modelos…",
    },
    "ornament.gallery.tip": {
        "fr": "Choisir un modèle prédéfini : il règle les motifs, la bande et le remplissage, le reste du formulaire reste modifiable.",
        "en": "Pick a ready-made template: it sets the motifs, band and fill; the rest of the form stays editable.",
        "de": "Eine fertige Vorlage wählen: Sie stellt Motive, Band und Füllung ein; der Rest bleibt änderbar.",
        "es": "Elegir un modelo: ajusta los motivos, la banda y el relleno; el resto del formulario sigue siendo editable.",
    },
    "ornament.gallery.hint": {
        "fr": "Les vignettes utilisent votre prénom, votre police et vos dimensions. Rouge : découpe. Bleu : gravure. Double-clic pour choisir.",
        "en": "Thumbnails use your name, font and dimensions. Red: cut. Blue: engraving. Double-click to choose.",
        "de": "Die Vorschaubilder verwenden Ihren Namen, Ihre Schrift und Ihre Maße. Rot: Schnitt. Blau: Gravur. Doppelklick zum Wählen.",
        "es": "Las miniaturas usan tu nombre, tu fuente y tus medidas. Rojo: corte. Azul: grabado. Doble clic para elegir.",
    },
    "ornament.preset.flakes_opposed": {
        "fr": "Flocons opposés et bande",
        "en": "Opposite snowflakes and band",
        "de": "Gegenüberliegende Flocken mit Band",
        "es": "Copos opuestos y banda",
    },
    "ornament.preset.flake_below": {
        "fr": "Flocon du bas et bande",
        "en": "Bottom snowflake and band",
        "de": "Flocke unten mit Band",
        "es": "Copo inferior con banda",
    },
    "ornament.preset.flake_below_lace": {
        "fr": "Flocon dentelle du bas et bande",
        "en": "Lace snowflake below and band",
        "de": "Spitzenflocke unten mit Band",
        "es": "Copo de encaje inferior con banda",
    },
    "ornament.preset.flake_above": {
        "fr": "Flocon du haut et bande",
        "en": "Top snowflake and band",
        "de": "Flocke oben mit Band",
        "es": "Copo superior con banda",
    },
    "ornament.preset.flakes_hanging": {
        "fr": "Flocons suspendus et bande",
        "en": "Hanging snowflakes and band",
        "de": "Hängende Flocken mit Band",
        "es": "Copos colgantes y banda",
    },
    "ornament.preset.stars_band": {
        "fr": "Étoiles et bande",
        "en": "Stars and band",
        "de": "Sterne mit Band",
        "es": "Estrellas y banda",
    },
    "ornament.preset.tree_band": {
        "fr": "Sapin et bande",
        "en": "Tree and band",
        "de": "Tannenbaum mit Band",
        "es": "Árbol y banda",
    },
    "ornament.preset.santa_band": {
        "fr": "Père Noël et bande",
        "en": "Santa and band",
        "de": "Weihnachtsmann mit Band",
        "es": "Santa con banda",
    },
    "ornament.preset.snowman_band": {
        "fr": "Bonhomme de neige et bande",
        "en": "Snowman and band",
        "de": "Schneemann mit Band",
        "es": "Muñeco de nieve y banda",
    },
    "ornament.preset.holly_band": {
        "fr": "Houx et bande",
        "en": "Holly and band",
        "de": "Stechpalme mit Band",
        "es": "Acebo y banda",
    },
    "ornament.preset.bells_band": {
        "fr": "Cloches et bande",
        "en": "Bells and band",
        "de": "Glocken mit Band",
        "es": "Campanas y banda",
    },
    "ornament.preset.gifts_band": {
        "fr": "Cadeaux et bande",
        "en": "Gifts and band",
        "de": "Geschenke mit Band",
        "es": "Regalos y banda",
    },
    "ornament.preset.candles_band": {
        "fr": "Bougies et bande",
        "en": "Candles and band",
        "de": "Kerzen mit Band",
        "es": "Velas y banda",
    },
    "ornament.preset.moon_band": {
        "fr": "Lune et bande",
        "en": "Moon and band",
        "de": "Mond mit Band",
        "es": "Luna y banda",
    },
    "ornament.preset.garland_band": {
        "fr": "Guirlande et bande",
        "en": "Garland and band",
        "de": "Girlande mit Band",
        "es": "Guirnalda y banda",
    },
    "ornament.preset.stripes_band": {
        "fr": "Rayures et bande",
        "en": "Stripes and band",
        "de": "Streifen mit Band",
        "es": "Rayas y banda",
    },
    "ornament.preset.lattice_band": {
        "fr": "Treillis et bande",
        "en": "Lattice and band",
        "de": "Gitter mit Band",
        "es": "Celosía y banda",
    },
    "ornament.preset.knit_band": {
        "fr": "Tricot et bande",
        "en": "Knit and band",
        "de": "Strickmuster mit Band",
        "es": "Punto y banda",
    },
    "ornament.preset.waves_band": {
        "fr": "Vagues et bande",
        "en": "Waves and band",
        "de": "Wellen mit Band",
        "es": "Ondas y banda",
    },
    "ornament.preset.leaves_band": {
        "fr": "Feuilles et bande",
        "en": "Leaves and band",
        "de": "Blätter mit Band",
        "es": "Hojas y banda",
    },
    "ornament.preset.leaves_top": {
        "fr": "Feuilles en haut et bande",
        "en": "Leaves on top and band",
        "de": "Blätter oben mit Band",
        "es": "Hojas arriba y banda",
    },
    "ornament.preset.reindeer_band": {
        "fr": "Renne et bande",
        "en": "Reindeer and band",
        "de": "Rentier mit Band",
        "es": "Reno y banda",
    },
    "ornament.preset.cut_flakes": {
        "fr": "Prénom découpé, flocons suspendus",
        "en": "Cut-out name, hanging snowflakes",
        "de": "Ausgeschnittener Name, hängende Flocken",
        "es": "Nombre calado, copos colgantes",
    },
    "ornament.preset.cut_name_bar": {
        "fr": "Prénom découpé sur barre",
        "en": "Cut-out name on bar",
        "de": "Ausgeschnittener Name auf Steg",
        "es": "Nombre calado sobre barra",
    },
    "ornament.preset.cut_tree_bandeau": {
        "fr": "Prénom découpé, sapin et bandeau",
        "en": "Cut-out name, tree and banner",
        "de": "Ausgeschnittener Name, Tannenbaum und Banner",
        "es": "Nombre calado, árbol y banda",
    },
    "ornament.err.fill_pitch": {
        "fr": "Le pas du remplissage doit être entre {lo:.1f} et {hi:.0f} mm.",
        "en": "Pattern spacing must be between {lo:.1f} and {hi:.0f} mm.",
        "de": "Der Musterabstand muss zwischen {lo:.1f} und {hi:.0f} mm liegen.",
        "es": "El paso del relleno debe estar entre {lo:.1f} y {hi:.0f} mm.",
    },
    "ornament.err.band_height": {
        "fr": "La hauteur de la bande doit être entre {lo:.0f} et {hi:.0f} mm.",
        "en": "Band height must be between {lo:.0f} and {hi:.0f} mm.",
        "de": "Die Bandhöhe muss zwischen {lo:.0f} und {hi:.0f} mm liegen.",
        "es": "La altura de la banda debe estar entre {lo:.0f} y {hi:.0f} mm.",
    },
}


