"""Système de traduction simple par dictionnaire, sans dépendance externe
(pas de fichiers .ts/.qm Qt Linguist à compiler). Le changement de langue
est mémorisé et appliqué au prochain lancement de l'application — pas de
rafraîchissement « à chaud » de l'interface déjà construite, ce qui évite
d'avoir à retenir et reconstruire chaque widget affiché un par un.

Utilisation : from i18n import tr
              menu_bar.addMenu(tr("menu.file"))

Note sur la qualité des traductions : le français et l'anglais sont
soigneusement relus. L'allemand et l'espagnol sont une première passe
raisonnable mais n'ont pas été relus par une personne native — une
relecture est bienvenue avant de les considérer définitifs.
"""
from PyQt6.QtCore import QSettings

SUPPORTED_LANGUAGES = {"fr": "Français", "en": "English", "de": "Deutsch", "es": "Español"}
DEFAULT_LANGUAGE = "fr"

# Clé -> { code_langue: texte }. Une clé absente ou une langue manquante
# retombe automatiquement sur le français, puis sur la clé elle-même :
# jamais de plantage ni de texte vide à cause d'une traduction manquante.
TRANSLATIONS = {
    # --- Menu Fichier ---
    "menu.file": {"fr": "Fichier", "en": "File", "de": "Datei", "es": "Archivo"},
    "menu.file.save_project": {
        "fr": "Enregistrer Projet", "en": "Save Project",
        "de": "Projekt speichern", "es": "Guardar proyecto",
    },
    "menu.file.open_project": {
        "fr": "Ouvrir Projet", "en": "Open Project",
        "de": "Projekt öffnen", "es": "Abrir proyecto",
    },
    "menu.file.recent_projects": {
        "fr": "Projets récents", "en": "Recent Projects",
        "de": "Zuletzt verwendete Projekte", "es": "Proyectos recientes",
    },
    "menu.file.quit": {"fr": "Quitter", "en": "Quit", "de": "Beenden", "es": "Salir"},

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
    "menu.help.about": {"fr": "À propos", "en": "About", "de": "Über", "es": "Acerca de"},
    "menu.help.support": {"fr": "Support", "en": "Support", "de": "Support", "es": "Soporte"},
    "menu.help.coffee": {"fr": "Buy me a coffee", "en": "Buy me a coffee",
                          "de": "Buy me a coffee", "es": "Buy me a coffee"},

    # --- Onglets du panneau de réglages ---
    "tab.machine_params": {
        "fr": "Paramètres Machine", "en": "Machine Settings",
        "de": "Maschineneinstellungen", "es": "Ajustes de la máquina",
    },
    "tab.image_filters": {
        "fr": "Image & Filtres", "en": "Image & Filters",
        "de": "Bild & Filter", "es": "Imagen y Filtros",
    },
    "tab.dimensions": {
        "fr": "Dimensions & Origine", "en": "Dimensions & Origin",
        "de": "Abmessungen & Ursprung", "es": "Dimensiones y Origen",
    },
    "tab.machine_profiles": {
        "fr": "Machine & Profils", "en": "Machine & Profiles",
        "de": "Maschine & Profile", "es": "Máquina y Perfiles",
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
              "type Phecda). Utilisé dans l'onglet 'Image & Filtres' pour proposer\n"
              "un intervalle de lignes calé sur cette taille de spot.",
        "en": "Diameter of your laser's focal point (e.g. 0.06 mm for a Phecda-type\n"
              "module). Used in the 'Image & Filters' tab to suggest a line spacing\n"
              "matched to this spot size.",
        "de": "Durchmesser des Fokuspunkts deines Lasers (z. B. 0,06 mm für ein\n"
              "Modul vom Typ Phecda). Wird im Reiter 'Bild & Filter' verwendet, um\n"
              "einen an diese Spotgröße angepassten Linienabstand vorzuschlagen.",
        "es": "Diámetro del punto focal de tu láser (ej.: 0.06 mm para un módulo\n"
              "tipo Phecda). Se usa en la pestaña 'Imagen y Filtros' para proponer\n"
              "un intervalo de líneas ajustado a este tamaño de punto.",
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
        "fr": "Charger Image (ou glisser-déposer)", "en": "Load Image (or drag & drop)",
        "de": "Bild laden (oder per Drag & Drop)", "es": "Cargar imagen (o arrastrar y soltar)",
    },
    "img.delete": {
        "fr": "🗑 Supprimer l'image", "en": "🗑 Delete Image",
        "de": "🗑 Bild löschen", "es": "🗑 Eliminar imagen",
    },
    "img.rotation": {"fr": "Rotation:", "en": "Rotation:", "de": "Drehung:", "es": "Rotación:"},
    "img.rotate_left": {
        "fr": "↶ Pivoter 90°", "en": "↶ Rotate 90°",
        "de": "↶ Um 90° drehen", "es": "↶ Girar 90°",
    },
    "img.rotate_right": {
        "fr": "Pivoter 90° ↷", "en": "Rotate 90° ↷",
        "de": "Um 90° drehen ↷", "es": "Girar 90° ↷",
    },
    "img.mirror_h": {
        "fr": "Miroir Horizontal", "en": "Horizontal Mirror",
        "de": "Horizontal spiegeln", "es": "Espejo horizontal",
    },
    "img.mirror_v": {
        "fr": "Miroir Vertical", "en": "Vertical Mirror",
        "de": "Vertikal spiegeln", "es": "Espejo vertical",
    },
    "img.mirror_mode": {
        "fr": "Mode Miroir:", "en": "Mirror Mode:",
        "de": "Spiegelmodus:", "es": "Modo espejo:",
    },
    "img.invert": {
        "fr": "Inverser Couleurs (Négatif)", "en": "Invert Colors (Negative)",
        "de": "Farben invertieren (Negativ)", "es": "Invertir colores (Negativo)",
    },
    "img.reset": {
        "fr": "Réinitialiser Réglages Image", "en": "Reset Image Settings",
        "de": "Bildeinstellungen zurücksetzen", "es": "Restablecer ajustes de imagen",
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
    "img.save_as_focal": {
        "fr": "→ Enregistrer comme focale machine", "en": "→ Save as machine focal",
        "de": "→ Als Maschinenfokus speichern", "es": "→ Guardar como focal de la máquina",
    },
    "img.configure_focal": {
        "fr": "Configurer la focale du laser >", "en": "Configure laser focal >",
        "de": "Laserfokus konfigurieren >", "es": "Configurar focal del láser >",
    },
    "img.compare_algos": {
        "fr": "Comparer les algorithmes de tramage (vignettes)",
        "en": "Compare dithering algorithms (thumbnails)",
        "de": "Rasteralgorithmen vergleichen (Miniaturansichten)",
        "es": "Comparar algoritmos de tramado (miniaturas)",
    },
}

_current_lang = None


def get_current_language():
    """Langue actuellement sélectionnée (mémorisée entre sessions)."""
    global _current_lang
    if _current_lang is None:
        settings = QSettings("LaserStudioPro", "UIConfig")
        stored = settings.value("language", DEFAULT_LANGUAGE)
        _current_lang = stored if stored in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return _current_lang


def set_language(lang_code):
    """Change la langue mémorisée. Prend effet au prochain lancement."""
    global _current_lang
    if lang_code not in SUPPORTED_LANGUAGES:
        return
    _current_lang = lang_code
    settings = QSettings("LaserStudioPro", "UIConfig")
    settings.setValue("language", lang_code)


def tr(key):
    """Renvoie le texte traduit pour la clé donnée, dans la langue
    actuellement sélectionnée."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    lang = get_current_language()
    return entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
