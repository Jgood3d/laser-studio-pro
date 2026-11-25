"""Textes de l'interface : graveur : connexion, configuration GRBL, jog, job, G-Code, file d'attente, profils machine. Clé -> {langue: texte} ; voir i18n/translations.py."""

TEXTS = {
    "ui.connection_box": {
        "fr": "Connexion",
        "en": "Connection",
        "de": "Verbindung",
        "es": "Conexión",
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
              "les capacités de la machine active, et à estimer la durée des\n"
              "gravures (si la config GRBL n'a pas été lue). Elles ne modifient\n"
              "pas les réglages GRBL eux-mêmes ($110/$120 etc.).",
        "en": "These values are used to warn you if a configured speed exceeds\n"
              "the active machine's capabilities, and to estimate job durations\n"
              "(if the GRBL config has not been read). They do not change the\n"
              "GRBL settings themselves ($110/$120 etc.).",
        "de": "Diese Werte dienen dazu, dich zu warnen, wenn eine eingestellte Geschwindigkeit\n"
              "die Fähigkeiten der aktiven Maschine übersteigt, und um die Gravurdauer zu\n"
              "schätzen (wenn die GRBL-Konfiguration nicht gelesen wurde). Sie ändern nicht\n"
              "die GRBL-Einstellungen selbst ($110/$120 usw.).",
        "es": "Estos valores sirven para avisarte si una velocidad configurada\n"
              "supera las capacidades de la máquina activa, y para estimar la\n"
              "duración de los grabados (si no se ha leído la config GRBL). No\n"
              "modifican los ajustes de GRBL en sí ($110/$120, etc.).",
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
              "(Compte l'accélération à chaque ligne de l'image, pas les déplacements rapides G0 ni les "
              "virages : la durée affichée après « Générer » est plus précise.)",
        "en": "QUICK estimate (approximate, without generating the complete G-Code):\n\n{details}\n\n"
              "Estimated TOTAL: {total}\n\n"
              "(Counts the acceleration on each image line, not rapid G0 moves or corners: the duration "
              "shown after « Generate » is more accurate.)",
        "de": "SCHNELLE Schätzung (ungefähr, ohne vollständige G-Code-Erzeugung):\n\n{details}\n\n"
              "Geschätzte GESAMTZEIT: {total}\n\n"
              "(Berücksichtigt die Beschleunigung jeder Bildzeile, nicht G0-Eilgänge oder Kurven: die Dauer nach "
              "„Erzeugen“ ist genauer.)",
        "es": "Estimación RÁPIDA (aproximada, sin generar el G-Code completo):\n\n{details}\n\n"
              "TOTAL estimado: {total}\n\n"
              "(Cuenta la aceleración en cada línea de la imagen, no los movimientos rápidos G0 ni las curvas: "
              "la duración tras «Generar» es más precisa.)",
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
    "status.disconnected": {
        "fr": "Graveur déconnecté",
        "en": "Engraver disconnected",
        "de": "Graviergerät getrennt",
        "es": "Grabadora desconectada",
    },
    "status.machine_tip": {
        "fr": "État du graveur et position de la tête (mm) ; un clic ouvre le panneau du graveur",
        "en": "Engraver state and head position (mm); click to open the engraver panel",
        "de": "Zustand des Graviergeräts und Kopfposition (mm); Klick öffnet das Gerätefeld",
        "es": "Estado de la grabadora y posición del cabezal (mm); un clic abre el panel de la grabadora",
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
    # --- Catalogue des machines ---
    "mach.from_catalog": {
        "fr": "Depuis le catalogue…",
        "en": "From the catalog…",
        "de": "Aus dem Katalog…",
        "es": "Desde el catálogo…",
    },
    "catalog.title": {
        "fr": "Catalogue des machines",
        "en": "Machine catalog",
        "de": "Maschinenkatalog",
        "es": "Catálogo de máquinas",
    },
    "catalog.intro": {
        "fr": "Graveurs GRBL courants, avec ce que leur constructeur publie. « Créer le profil » remplit un nouveau profil machine (surface, taille du point, vitesse maximale) ; rien n'est envoyé au graveur.",
        "en": "Common GRBL engravers, with what their manufacturer publishes. « Create the profile » fills a new machine profile (work area, spot size, maximum speed); nothing is sent to the engraver.",
        "de": "Gängige GRBL-Graviergeräte mit den Angaben ihres Herstellers. „Profil erstellen“ füllt ein neues Maschinenprofil (Arbeitsfläche, Punktgröße, Höchstgeschwindigkeit); nichts wird an das Gerät gesendet.",
        "es": "Grabadoras GRBL habituales, con lo que publica su fabricante. «Crear el perfil» rellena un nuevo perfil de máquina (área, tamaño del punto, velocidad máxima); no se envía nada a la grabadora.",
    },
    "catalog.search": {
        "fr": "Rechercher une marque ou un modèle",
        "en": "Search a brand or a model",
        "de": "Marke oder Modell suchen",
        "es": "Buscar una marca o un modelo",
    },
    "catalog.create": {
        "fr": "Créer le profil",
        "en": "Create the profile",
        "de": "Profil erstellen",
        "es": "Crear el perfil",
    },
    "catalog.none": {
        "fr": "Aucun modèle ne correspond.",
        "en": "No model matches.",
        "de": "Kein passendes Modell.",
        "es": "Ningún modelo coincide.",
    },
    "catalog.unpublished": {
        "fr": "non publié par le constructeur",
        "en": "not published by the manufacturer",
        "de": "vom Hersteller nicht veröffentlicht",
        "es": "no publicado por el fabricante",
    },
    "catalog.area": {
        "fr": "Surface de travail",
        "en": "Work area",
        "de": "Arbeitsfläche",
        "es": "Área de trabajo",
    },
    "catalog.spot": {
        "fr": "Taille du point",
        "en": "Spot size",
        "de": "Punktgröße",
        "es": "Tamaño del punto",
    },
    "catalog.speed": {
        "fr": "Vitesse maximale",
        "en": "Maximum speed",
        "de": "Höchstgeschwindigkeit",
        "es": "Velocidad máxima",
    },
    "catalog.laser": {
        "fr": "Laser",
        "en": "Laser",
        "de": "Laser",
        "es": "Láser",
    },
    "catalog.after": {
        "fr": "Accélération et réglages GRBL : ils ne sont pas publiés. Après connexion, « Lire la config » (Configuration GRBL) les lit sur la machine ; la durée estimée des gravures s'en sert.",
        "en": "Acceleration and GRBL settings are not published. Once connected, « Read config » (GRBL configuration) reads them from the machine; the estimated job duration uses them.",
        "de": "Beschleunigung und GRBL-Einstellungen werden nicht veröffentlicht. Nach dem Verbinden liest „Konfiguration lesen“ (GRBL-Konfiguration) sie von der Maschine; die geschätzte Gravurdauer nutzt sie.",
        "es": "La aceleración y los ajustes GRBL no se publican. Una vez conectada, «Leer la config» (Configuración GRBL) los lee de la máquina; la duración estimada los utiliza.",
    },
    "catalog.sources": {
        "fr": "Sources",
        "en": "Sources",
        "de": "Quellen",
        "es": "Fuentes",
    },
    "catalog.checked": {
        "fr": "Vérifié le {date}",
        "en": "Checked on {date}",
        "de": "Geprüft am {date}",
        "es": "Verificado el {date}",
    },
    # --- Historique des gravures ---
    "menu.tools.history": {
        "fr": "Historique des gravures…",
        "en": "Engraving history…",
        "de": "Gravurverlauf…",
        "es": "Historial de grabados…",
    },
    "history.title": {
        "fr": "Historique des gravures",
        "en": "Engraving history",
        "de": "Gravurverlauf",
        "es": "Historial de grabados",
    },
    "history.intro": {
        "fr": "Chaque job envoyé au graveur est noté ici : durée réelle et durée estimée, issue, distance gravée. L'historique reste sur cet ordinateur ; l'export CSV s'ouvre dans un tableur.",
        "en": "Every job sent to the engraver is recorded here: real and estimated duration, outcome, engraved distance. The history stays on this computer; the CSV export opens in a spreadsheet.",
        "de": "Jeder an das Graviergerät gesendete Auftrag wird hier notiert: tatsächliche und geschätzte Dauer, Ergebnis, gravierte Strecke. Der Verlauf bleibt auf diesem Computer; der CSV-Export öffnet sich in einer Tabellenkalkulation.",
        "es": "Cada trabajo enviado a la grabadora se anota aquí: duración real y estimada, resultado, distancia grabada. El historial queda en este ordenador; la exportación CSV se abre en una hoja de cálculo.",
    },
    "history.col_date": {
        "fr": "Date",
        "en": "Date",
        "de": "Datum",
        "es": "Fecha",
    },
    "history.col_result": {
        "fr": "Issue",
        "en": "Outcome",
        "de": "Ergebnis",
        "es": "Resultado",
    },
    "history.col_duration": {
        "fr": "Durée réelle",
        "en": "Real duration",
        "de": "Tatsächliche Dauer",
        "es": "Duración real",
    },
    "history.col_estimate": {
        "fr": "Estimée",
        "en": "Estimated",
        "de": "Geschätzt",
        "es": "Estimada",
    },
    "history.col_gap": {
        "fr": "Écart",
        "en": "Gap",
        "de": "Abweichung",
        "es": "Desviación",
    },
    "history.col_burn": {
        "fr": "Gravé",
        "en": "Engraved",
        "de": "Graviert",
        "es": "Grabado",
    },
    "history.col_lines": {
        "fr": "Lignes",
        "en": "Lines",
        "de": "Zeilen",
        "es": "Líneas",
    },
    "history.col_profile": {
        "fr": "Machine",
        "en": "Machine",
        "de": "Maschine",
        "es": "Máquina",
    },
    "history.result.done": {
        "fr": "Terminée",
        "en": "Finished",
        "de": "Fertig",
        "es": "Terminado",
    },
    "history.result.stopped": {
        "fr": "Arrêtée",
        "en": "Stopped",
        "de": "Abgebrochen",
        "es": "Detenido",
    },
    "history.result.error": {
        "fr": "Erreur GRBL",
        "en": "GRBL error",
        "de": "GRBL-Fehler",
        "es": "Error GRBL",
    },
    "history.result.interrupted": {
        "fr": "Interrompue",
        "en": "Interrupted",
        "de": "Unterbrochen",
        "es": "Interrumpido",
    },
    "history.summary": {
        "fr": "{count} gravure(s), {total} de gravures terminées",
        "en": "{count} job(s), {total} of finished jobs",
        "de": "{count} Auftrag/Aufträge, {total} abgeschlossene Gravuren",
        "es": "{count} grabado(s), {total} de grabados terminados",
    },
    "history.export": {
        "fr": "Exporter (CSV)…",
        "en": "Export (CSV)…",
        "de": "Exportieren (CSV)…",
        "es": "Exportar (CSV)…",
    },
    "history.clear": {
        "fr": "Vider l'historique",
        "en": "Clear history",
        "de": "Verlauf leeren",
        "es": "Vaciar el historial",
    },
    "history.close": {
        "fr": "Fermer",
        "en": "Close",
        "de": "Schließen",
        "es": "Cerrar",
    },
    "history.clear_question": {
        "fr": "Effacer tout l'historique des gravures ? C'est définitif.",
        "en": "Delete the whole engraving history? This cannot be undone.",
        "de": "Den gesamten Gravurverlauf löschen? Das ist endgültig.",
        "es": "¿Borrar todo el historial de grabados? Es definitivo.",
    },
    "history.simulated": {
        "fr": "simulation ×{speed}", "en": "simulation ×{speed}",
        "de": "Simulation ×{speed}", "es": "simulación ×{speed}",
    },
    "history.csv_filter": {
        "fr": "Fichier CSV (*.csv)",
        "en": "CSV file (*.csv)",
        "de": "CSV-Datei (*.csv)",
        "es": "Archivo CSV (*.csv)",
    },
}
