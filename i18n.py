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

    "dim.box_title": {
        "fr": "Dimensions & Origine Machine",
        "en": "Machine Dimensions & Origin",
        "de": "Maschinenabmessungen & Ursprung",
        "es": "Dimensiones y origen de la máquina",
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

    "usb.box_title": {
        "fr": "Connexion USB Laser",
        "en": "Laser USB Connection",
        "de": "USB-Laserverbindung",
        "es": "Conexión USB del láser",
    },
    "usb.refresh_ports": {
        "fr": "Rafraîchir les ports",
        "en": "Refresh Ports",
        "de": "Ports aktualisieren",
        "es": "Actualizar puertos",
    },
    "usb.connect": {
        "fr": "Connecter GRBL",
        "en": "Connect GRBL",
        "de": "GRBL verbinden",
        "es": "Conectar GRBL",
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
        "fr": "Sélection Profil:",
        "en": "Select Profile:",
        "de": "Profil auswählen:",
        "es": "Seleccionar perfil:",
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
        "fr": "⏱ Estimer le temps de gravure (rapide, sans générer)",
        "en": "⏱ Estimate engraving time (quick, without generating)",
        "de": "⏱ Gravurzeit schätzen (schnell, ohne Generierung)",
        "es": "⏱ Estimar el tiempo de grabado (rápido, sin generar)",
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
    "preview.flip": {
        "fr": "Inverser l'aperçu image (si l'image gravée apparaît retournée)",
        "en": "Flip image preview (if the engraved image appears reversed)",
        "de": "Bildvorschau spiegeln (wenn das Bild beim Gravieren falsch herum erscheint)",
        "es": "Invertir vista previa (si la imagen grabada aparece invertida)",
    },
    "preview.negative": {
        "fr": "Aperçu en négatif (voir ce qui sera réellement gravé)",
        "en": "Negative preview (see what will actually be engraved)",
        "de": "Negative Vorschau (tatsächliches Gravurergebnis anzeigen)",
        "es": "Vista previa negativa (ver lo que se grabará realmente)",
    },
    "preview.hide_rapid": {
        "fr": "Masquer les déplacements rapides G0 dans l'aperçu",
        "en": "Hide rapid G0 moves in preview",
        "de": "Schnelle G0-Bewegungen in der Vorschau ausblenden",
        "es": "Ocultar movimientos rápidos G0 en la vista previa",
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
    "laser.connect_first": {
        "fr": "Connectez d'abord le laser.",
        "en": "Connect the laser first.",
        "de": "Verbinde zuerst den Laser.",
        "es": "Conecta primero el láser.",
    },
    "laser.connect_via_usb": {
        "fr": "Connectez le laser via USB.",
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
        "fr": "Le laser va démarrer.\n\nVérifiez que :\n"
              "- la zone de travail est dégagée,\n"
              "- le capot/protection est en place,\n"
              "- vous portez une protection oculaire adaptée.\n\n"
              "Lancer le job maintenant ?",
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
        "fr": "L'envoi du G-Code a été interrompu (erreur GRBL, alarme, perte de "
              "connexion ou arrêt manuel). Consultez la console avant de relancer.",
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
        "fr": "Veuillez connecter le laser en USB.",
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
    "ui.quit_title": {
        "fr": "Quitter",
        "en": "Exit",
        "de": "Beenden",
        "es": "Salir",
    },
    "ui.quit_save_prompt": {
        "fr": "Voulez-vous sauvegarder le projet avant de fermer ?",
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
    "image.save_focal_title": {
        "fr": "Enregistrer la focale machine",
        "en": "Save Machine Focal Length",
        "de": "Maschinenfokus speichern",
        "es": "Guardar focal de la máquina",
    },
    "image.save_focal_question": {
        "fr": "Mettre à jour la focale du laser (Paramètres Machine) :\n"
              "{current:.3f} mm  →  {new:.3f} mm\n\n"
              "et sauvegarder ce réglage machine maintenant ?",
        "en": "Update the laser focal length (Machine Settings):\n"
              "{current:.3f} mm  →  {new:.3f} mm\n\n"
              "and save this machine setting now?",
        "de": "Lasfokus aktualisieren (Maschineneinstellungen):\n"
              "{current:.3f} mm  →  {new:.3f} mm\n\n"
              "und diese Maschineneinstellung jetzt speichern?",
        "es": "¿Actualizar la focal del láser (Parámetros de máquina):\n"
              "{current:.3f} mm  →  {new:.3f} mm\n\n"
              "y guardar ahora este ajuste?",
    },
    "image.focal_saved_title": {
        "fr": "Focale enregistrée",
        "en": "Focal Length Saved",
        "de": "Fokus gespeichert",
        "es": "Focal guardado",
    },
    "image.focal_saved": {
        "fr": "La focale machine a été mise à jour à {focal:.3f} mm et sauvegardée.",
        "en": "The machine focal length was updated to {focal:.3f} mm and saved.",
        "de": "Der Maschinenfokus wurde auf {focal:.3f} mm aktualisiert und gespeichert.",
        "es": "La focal de la máquina se actualizó a {focal:.3f} mm y se guardó.",
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
        "fr": "Créez d'abord un calque dans l'onglet 'Calques (Layers)'.",
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
        "fr": "Sélectionnez d'abord un objet dans le canevas.",
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
        "fr": "Éditeur Vectoriel — Plein Écran",
        "en": "Vector Editor — Full Screen",
        "de": "Vektor-Editor — Vollbild",
        "es": "Editor vectorial — Pantalla completa",
    },
    "vector.close_fullscreen": {
        "fr": "✕ Fermer le plein écran (retour à la fenêtre normale)",
        "en": "✕ Exit full screen (return to normal window)",
        "de": "✕ Vollbild schließen (zum normalen Fenster zurückkehren)",
        "es": "✕ Cerrar pantalla completa (volver a la ventana normal)",
    },
    "vector.import_title": {
        "fr": "Importer un SVG (multi-calques)",
        "en": "Import SVG (multi-layer)",
        "de": "SVG importieren (mehrere Ebenen)",
        "es": "Importar SVG (multicapa)",
    },
    "vector.svg_filter": {
        "fr": "Vectoriel SVG (*.svg)",
        "en": "SVG Vector (*.svg)",
        "de": "SVG-Vektor (*.svg)",
        "es": "Vectorial SVG (*.svg)",
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
        "fr": "{count} élément(s) importé(s) dans l'éditeur vectoriel, tous assignés "
              "par défaut au calque « {layer} ».\n\n"
              "Sélectionne un élément puis double-clique dessus (ou 'Modifier Sélection') "
              "pour lui assigner un autre calque.",
        "en": "{count} element(s) imported into the vector editor, all assigned by "
              "default to layer “{layer}”.\n\n"
              "Select an element and double-click it (or use 'Edit Selection') "
              "to assign it to another layer.",
        "de": "{count} Element(e) in den Vektor-Editor importiert und standardmäßig "
              "der Ebene „{layer}“ zugewiesen.\n\n"
              "Wähle ein Element aus und doppelklicke darauf, um eine andere Ebene "
              "zuzuweisen.",
        "es": "{count} elemento(s) importado(s) en el editor vectorial y asignado(s) "
              "por defecto a la capa «{layer}».\n\n"
              "Selecciona un elemento y haz doble clic para asignarlo a otra capa.",
    },
    "vector.open_svg_title": {
        "fr": "Ouvrir SVG Découpe",
        "en": "Open Cutting SVG",
        "de": "Schneide-SVG öffnen",
        "es": "Abrir SVG de corte",
    },
    "vector.svg_loaded": {
        "fr": "Fichier SVG chargé : {path}",
        "en": "SVG file loaded: {path}",
        "de": "SVG-Datei geladen: {path}",
        "es": "Archivo SVG cargado: {path}",
    },
    "tab.vector_editor": {
        "fr": "Éditeur Vectoriel (Texte & Formes)",
        "en": "Vector Editor (Text & Shapes)",
        "de": "Vektor-Editor (Text & Formen)",
        "es": "Editor vectorial (texto y formas)",
    },
    # --- Génération et export G-Code ---
    "gcode.empty_title": {
        "fr": "G-Code vide",
        "en": "Empty G-Code",
        "de": "Leerer G-Code",
        "es": "G-Code vacío",
    },
    "gcode.empty_export": {
        "fr": "Générez d'abord le job G-Code avant de l'exporter.",
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
    "ui.quit_title": {
        "fr": "Quitter",
        "en": "Exit",
        "de": "Beenden",
        "es": "Salir",
    },
    "ui.quit_save_prompt": {
        "fr": "Voulez-vous sauvegarder le projet avant de fermer ?",
        "en": "Do you want to save the project before closing?",
        "de": "Möchtest du das Projekt vor dem Schließen speichern?",
        "es": "¿Quieres guardar el proyecto antes de cerrar?",
    },
    "ui.tab_image_tracing": {
        "fr": "Images & Tramage",
        "en": "Images & Dithering",
        "de": "Bilder & Rasterung",
        "es": "Imágenes y tramado",
    },
    "ui.tab_vector_editor": {
        "fr": "Éditeur Vectoriel (Texte & Formes)",
        "en": "Vector Editor (Text & Shapes)",
        "de": "Vektor-Editor (Text & Formen)",
        "es": "Editor vectorial (texto y formas)",
    },
    "ui.tab_2d_preview": {
        "fr": "Visualisation 2D G-Code",
        "en": "2D G-Code Preview",
        "de": "2D-G-Code-Vorschau",
        "es": "Vista previa 2D del G-Code",
    },
    "ui.source_image_box": {
        "fr": "Image Originale (Glissez pour déplacer, molette pour zoomer)",
        "en": "Original Image (Drag to move, mouse wheel to zoom)",
        "de": "Originalbild (ziehen zum Bewegen, Mausrad zum Zoomen)",
        "es": "Imagen original (arrastra para mover, rueda del ratón para ampliar)",
    },
    "ui.final_raster_box": {
        "fr": "Rendu Tramé Final (Glissez pour déplacer, molette pour zoomer)",
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
    "ui.vector_import_svg": {
        "fr": "📥 Importer SVG (multi-calques)",
        "en": "📥 Import SVG (multi-layer)",
        "de": "📥 SVG importieren (Mehrfach-Ebenen)",
        "es": "📥 Importar SVG (multicapa)",
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
    "ui.vector_undo": {
        "fr": "↶ Annuler (Ctrl+Z)",
        "en": "↶ Undo (Ctrl+Z)",
        "de": "↶ Rückgängig (Ctrl+Z)",
        "es": "↶ Deshacer (Ctrl+Z)",
    },
    "ui.vector_fullscreen": {
        "fr": "⛶ Plein Écran",
        "en": "⛶ Full Screen",
        "de": "⛶ Vollbild",
        "es": "⛶ Pantalla completa",
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
    "ui.jog_box": {
        "fr": "Mouvements Manuel Laser (Jog) & Commandes",
        "en": "Manual Laser Moves (Jog) & Commands",
        "de": "Manuelle Laserbewegungen (Jog) & Befehle",
        "es": "Movimientos manuales del láser (jog) y comandos",
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
    "ui.direct_console_box": {
        "fr": "Console de Commandes Directes GRBL",
        "en": "GRBL Direct Commands Console",
        "de": "GRBL-Direktbefehls-Konsole",
        "es": "Consola de comandos directos GRBL",
    },
    "ui.manual_grbl_placeholder": {
        "fr": "Tapez une commande GRBL ($$, $I, $H, $X, G0 X10 Y10)... (↑/↓ pour l'historique)",
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
    "ui.laser_exec_box": {
        "fr": "Paramètres d'Exécution Laser — Gravure Image",
        "en": "Laser Execution Settings — Image Engraving",
        "de": "Laser-Ausführungsparameter — Bildgravur",
        "es": "Parámetros de ejecución láser — Grabado de imagen",
    },
    "ui.image_layer_label": {
        "fr": "Calque pour la gravure image :",
        "en": "Layer for image engraving:",
        "de": "Ebene für Bildgravur:",
        "es": "Capa para grabado de imagen:",
    },
    "ui.svg_legacy_title": {
        "fr": "[Ancien mode, déprécié] Découpe SVG globale",
        "en": "[Legacy mode, deprecated] Global SVG Cutting",
        "de": "[Altmodus, veraltet] Globale SVG-Schneideoption",
        "es": "[Modo antiguo, obsoleto] Corte SVG global",
    },
    "ui.load_svg_legacy": {
        "fr": "Charger SVG (ancien mode)",
        "en": "Load SVG (legacy mode)",
        "de": "SVG laden (Altmodus)",
        "es": "Cargar SVG (modo antiguo)",
    },
    "ui.enable_cut": {
        "fr": "Activer Passe de Découpe",
        "en": "Enable Cutting Pass",
        "de": "Schnittdurchgang aktivieren",
        "es": "Activar pasada de corte",
    },
    "ui.cut_speed": {
        "fr": "Vitesse Découpe (mm/min):",
        "en": "Cut Speed (mm/min):",
        "de": "Schnittgeschwindigkeit (mm/min):",
        "es": "Velocidad de corte (mm/min):",
    },
    "ui.cut_power": {
        "fr": "Puissance Découpe (%):",
        "en": "Cut Power (%):",
        "de": "Schnittleistung (%):",
        "es": "Potencia de corte (%):",
    },
    "ui.cut_passes": {
        "fr": "Passes Découpe:",
        "en": "Cut Passes:",
        "de": "Schnittdurchgänge:",
        "es": "Pasadas de corte:",
    },
    "ui.vector_file_label": {
        "fr": "Fichier Vectoriel:",
        "en": "Vector File:",
        "de": "Vektordatei:",
        "es": "Archivo vectorial:",
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
