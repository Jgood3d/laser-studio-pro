"""Textes de l'interface : fenêtre, menus, onglets, aide, projet, démarrage, Stencil Studio. Clé -> {langue: texte} ; voir i18n/translations.py."""

TEXTS = {
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
    "menu.view.bottom_panel": {"fr": "Panneau du bas", "en": "Bottom panel", "de": "Unteres Feld",
                               "es": "Panel inferior"},
    "menu.view.job_queue": {
        "fr": "File d'attente",
        "en": "Job queue",
        "de": "Warteschlange",
        "es": "Cola de trabajos",
    },
    "panel.machine": {"fr": "Graveur", "en": "Engraver", "de": "Graviergerät", "es": "Grabadora"},
    "panel.toggle_tip": {
        "fr": "Replier / déplier le panneau (Ctrl+J)",
        "en": "Collapse / expand the panel (Ctrl+J)",
        "de": "Feld ein-/ausklappen (Strg+J)",
        "es": "Plegar / desplegar el panel (Ctrl+J)",
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
    "menu.tools.puzzle": {
        "fr": "Générateur de puzzle…",
        "en": "Puzzle generator…",
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
    "theme.new_dusk": {
        "fr": "New Dusk (gris-bleu moderne)",
        "en": "New Dusk (modern blue-gray)",
        "de": "New Dusk (modernes Blaugrau)",
        "es": "New Dusk (gris azulado moderno)",
    },
    "theme.new_dusk_petrol": {
        "fr": "New Dusk Blue Petrol (bleu pétrole moderne)",
        "en": "New Dusk Blue Petrol (modern petrol blue)",
        "de": "New Dusk Blue Petrol (modernes Petrolblau)",
        "es": "New Dusk Blue Petrol (azul petróleo moderno)",
    },
    "theme.new_dawn": {
        "fr": "New Dawn (clair moderne)",
        "en": "New Dawn (modern light)",
        "de": "New Dawn (modern hell)",
        "es": "New Dawn (claro moderno)",
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
    "settings.appearance": {"fr": "Langue et thème", "en": "Language and theme", "de": "Sprache und Design",
                            "es": "Idioma y tema"},
    "settings.language_hint": {
        "fr": "Appliquée au prochain démarrage de l'application.",
        "en": "Applied the next time the application starts.",
        "de": "Wird beim nächsten Start der Anwendung übernommen.",
        "es": "Se aplica la próxima vez que se inicie la aplicación.",
    },
    "menu.file.settings": {"fr": "Paramètres…", "en": "Settings…", "de": "Einstellungen…", "es": "Ajustes…"},
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
    "menu.job": {"fr": "Job", "en": "Job", "de": "Job", "es": "Trabajo"},
    "menu.job.generate": {"fr": "Générer le G-Code", "en": "Generate G-Code", "de": "G-Code erzeugen",
                          "es": "Generar el G-Code"},
    "menu.job.frame": {"fr": "Cadrer", "en": "Frame", "de": "Umriss abfahren", "es": "Encuadrar"},
    "menu.job.frame_contour": {"fr": "Cadrer au plus près", "en": "Frame the outline",
                               "de": "Kontur abfahren", "es": "Encuadrar el contorno"},
    "menu.job.send": {"fr": "Envoyer au laser", "en": "Send to laser", "de": "An den Laser senden",
                      "es": "Enviar al láser"},
    "menu.job.pause": {"fr": "Pause", "en": "Pause", "de": "Pause", "es": "Pausa"},
    "menu.job.resume": {"fr": "Reprendre (après une pause ou un arrêt)", "en": "Resume (after a pause or a stop)",
                        "de": "Fortsetzen (nach Pause oder Halt)", "es": "Reanudar (tras una pausa o una parada)"},
    "menu.job.emergency_stop": {"fr": "Arrêt d'urgence", "en": "Emergency stop", "de": "Not-Halt",
                                "es": "Parada de emergencia"},
    "menu.job.emergency_stop_button": {"fr": "⛔ ARRÊT D'URGENCE", "en": "⛔ EMERGENCY STOP", "de": "⛔ NOT-HALT",
                                       "es": "⛔ PARADA DE EMERGENCIA"},
    "menu.job.emergency_stop_tip": {
        "fr": "Arrête tout de suite le graveur (F9) : le laser s'éteint et le travail est abandonné.",
        "en": "Stops the engraver immediately (F9): the laser turns off and the job is abandoned.",
        "de": "Hält den Gravierer sofort an (F9): Der Laser schaltet ab und der Auftrag wird abgebrochen.",
        "es": "Detiene el grabador de inmediato (F9): el láser se apaga y el trabajo se abandona.",
    },
    "status.gcode_stale": {"fr": "G-Code à régénérer", "en": "G-Code out of date", "de": "G-Code veraltet",
                           "es": "G-Code desactualizado"},
    "status.gcode_stale_tip": {
        "fr": "Des réglages ont changé depuis la génération : cliquez (ou F5) pour régénérer le G-Code.",
        "en": "Settings have changed since generation: click (or F5) to generate the G-Code again.",
        "de": "Seit der Erzeugung haben sich Einstellungen geändert: klicken (oder F5), um den G-Code neu zu erzeugen.",
        "es": "Los ajustes han cambiado desde la generación: haga clic (o F5) para volver a generar el G-Code.",
    },
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
        "fr": "Matrice de test", "en": "Test matrix",
        "de": "Testmatrix", "es": "Matriz de prueba",
    },
    "tab.grbl_config": {
        "fr": "Configuration GRBL", "en": "GRBL Configuration",
        "de": "GRBL-Konfiguration", "es": "Configuración GRBL",
    },
    "tab.layers": {
        "fr": "Calques", "en": "Layers",
        "de": "Ebenen (Layers)", "es": "Capas (Layers)",
    },
    "project.autosave_failed": {
        "fr": "Sauvegarde automatique impossible : {error}", "en": "Automatic save failed: {error}",
        "de": "Automatische Sicherung nicht möglich: {error}", "es": "No se pudo realizar el guardado automático: {error}",
    },
    "ui.bidir_test_btn": {
        "fr": "Générer le test aller/retour",
        "en": "Generate forward/return test",
        "de": "Hin-/Rücklauf-Test erzeugen",
        "es": "Generar prueba de ida y vuelta",
    },

    # --- Générateur de boules de Noël ---
    "menu.tools.ornament": {
        "fr": "Boule de Noël…",
        "en": "Christmas ornament…",
        "de": "Weihnachtskugel…",
        "es": "Bola de Navidad…",
    },
        # --- Interface principale ---
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
    # --- Projets ---
    "project.save_title": {
        "fr": "Enregistrer le projet laser",
        "en": "Save laser project",
        "de": "Laserprojekt speichern",
        "es": "Guardar proyecto láser",
    },
    "project.file_filter": {
        "fr": "Projet laser (*.json)",
        "en": "Laser project (*.json)",
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
        "fr": "Ouvrir un projet laser",
        "en": "Open a laser project",
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
    "project.image_too_large": {
        "fr": "image du projet trop grande ({width} x {height} pixels)",
        "en": "project image too large ({width} x {height} pixels)",
        "de": "Bild des Projekts zu groß ({width} x {height} Pixel)",
        "es": "imagen del proyecto demasiado grande ({width} x {height} píxeles)",
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
    "ui.window_title": {
        "fr": "Laser Studio Pro — contrôleur GRBL", "en": "Laser Studio Pro — GRBL controller",
        "de": "Laser Studio Pro — GRBL-Steuerung", "es": "Laser Studio Pro — controlador GRBL",
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
    "tab.vector_editor": {
        "fr": "Graver une image vectorielle",
        "en": "Engrave a Vector Image",
        "de": "Vektorbild gravieren",
        "es": "Grabar una imagen vectorial",
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
        "fr": "Visualisation 2D du G-Code",
        "en": "2D G-Code Preview",
        "de": "2D-G-Code-Vorschau",
        "es": "Vista previa 2D del G-Code",
    },
    "ui.source_image_box": {
        "fr": "Image originale (glisser pour déplacer, molette pour zoomer)",
        "en": "Original image (drag to move, mouse wheel to zoom)",
        "de": "Originalbild (ziehen zum Bewegen, Mausrad zum Zoomen)",
        "es": "Imagen original (arrastrar para mover, rueda del ratón para ampliar)",
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
    "menu.tools.library": {
        "fr": "Bibliothèque…",
        "en": "Library…",
        "de": "Bibliothek…",
        "es": "Biblioteca…",
    },
    "common.save": {"fr": "Enregistrer", "en": "Save", "de": "Speichern", "es": "Guardar"},
    "macros.discard": {
        "fr": "Annuler les modifications",
        "en": "Discard changes",
        "de": "Änderungen verwerfen",
        "es": "Descartar los cambios",
    },
    "common.cancel": {
        "fr": "Annuler",
        "en": "Cancel",
        "de": "Abbrechen",
        "es": "Cancelar",
    },
    "ui.unlock_alarm": {
        "fr": "🔓 Déverrouiller ($X)", "en": "🔓 Unlock ($X)",
        "de": "🔓 Entsperren ($X)", "es": "🔓 Desbloquear ($X)",
    },
    "ui.zero_work": {
        "fr": "Zéro de travail (G92 X0 Y0)",
        "en": "Work zero (G92 X0 Y0)",
        "de": "Arbeitsnull (G92 X0 Y0)",
        "es": "Cero de trabajo (G92 X0 Y0)",
    },
    "ui.go_zero": {
        "fr": "Aller au zéro (G0 X0 Y0)",
        "en": "Go to zero (G0 X0 Y0)",
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
        "fr": "Reprendre : après une pause (~), ou le job interrompu là où il s'est arrêté (F8)",
        "en": "Resume: after a pause (~), or the interrupted job where it stopped (F8)",
        "de": "Fortsetzen: nach einer Pause (~) oder den unterbrochenen Job dort, wo er angehalten hat (F8)",
        "es": "Reanudar: tras una pausa (~), o el trabajo interrumpido donde se detuvo (F8)",
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
        "fr": "Cadrer : rectangle autour du job, laser à 0,5 % pour voir le parcours (F6)",
        "en": "Frame: rectangle around the job, laser at 0.5% to see the path (F6)",
        "de": "Umriss: Rechteck um den Job, Laser auf 0,5 %, um den Weg zu sehen (F6)",
        "es": "Encuadrar: rectángulo alrededor del trabajo, láser al 0,5 % para ver el recorrido (F6)",
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
    "ui.frame_contour": {
        "fr": "Cadrer au plus près : le tour réel de la gravure et de la découpe, laser à 0,5 % (Maj+F6)",
        "en": "Frame the outline: the real outline of the engraving and cut, laser at 0.5% (Shift+F6)",
        "de": "Kontur abfahren: der echte Umriss von Gravur und Schnitt, Laser auf 0,5 % (Umschalt+F6)",
        "es": "Encuadrar el contorno: el contorno real del grabado y del corte, láser al 0,5 % (Mayús+F6)",
    },
    "frame.title": {"fr": "Cadrage", "en": "Framing", "de": "Umriss", "es": "Encuadre"},
    "frame.need_gcode": {
        "fr": "Générez d'abord le G-Code : le cadrage au plus près fait le tour de ce qui sera vraiment gravé.",
        "en": "Generate the G-Code first: framing the outline goes round what will really be engraved.",
        "de": "Zuerst den G-Code erzeugen: Die Kontur folgt dem, was wirklich graviert wird.",
        "es": "Genere primero el G-Code: el encuadre del contorno recorre lo que realmente se grabará.",
    },
    "ui.resume_job": {
        "fr": "⏩ Reprendre le job interrompu là où il s'est arrêté",
        "en": "⏩ Resume the interrupted job where it stopped",
        "de": "⏩ Unterbrochenen Job dort fortsetzen, wo er angehalten hat",
        "es": "⏩ Reanudar el trabajo interrumpido donde se detuvo",
    },
    "ui.burn_progress": {
        "fr": "Gravure : {pct}%",
        "en": "Engraving: {pct}%",
        "de": "Gravur: {pct}%",
        "es": "Grabado: {pct}%",
    },
    "ui.generated_console_label": {
        "fr": "Console / G-Code généré :",
        "en": "Console / generated G-Code:",
        "de": "Konsole / generierter G-Code:",
        "es": "Consola / G-Code generado:",
    },
    "ui.tab_console_gcode": {
        "fr": "Console / G-Code",
        "en": "Console / G-Code",
        "de": "Konsole / G-Code",
        "es": "Consola / G-Code",
    },
    "ui.tab_job_queue": {
        "fr": "File d'attente",
        "en": "Job Queue",
        "de": "Warteschlange",
        "es": "Cola de trabajos",
    },
    "ui.gen_test_matrix": {
        "fr": "GÉNÉRER MATRICE DE TEST",
        "en": "GENERATE TEST MATRIX",
        "de": "TESTMATRIX GENERIEREN",
        "es": "GENERAR MATRIZ DE PRUEBA",
    },
    "ui.test_mode": {
        "fr": "Mode de test :",
        "en": "Test mode:",
        "de": "Testmodus:",
        "es": "Modo de prueba:",
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
    "ui.support_button_tooltip": {
        "fr": "Soutenir le développement ☕",
        "en": "Support development ☕",
        "de": "Entwicklung unterstützen ☕",
        "es": "Apoyar el desarrollo ☕",
    },
    "splash.initializing": {
        "fr": "Initialisation de Laser Studio Pro…",
        "en": "Initializing Laser Studio Pro…",
        "de": "Laser Studio Pro wird initialisiert…",
        "es": "Inicializando Laser Studio Pro…",
    },
    "splash.ready": {
        "fr": "Prêt !",
        "en": "Ready!",
        "de": "Bereit!",
        "es": "¡Listo!",
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
    "menu.tools.keychain": {
        "fr": "Générateur de porte-clés...",
        "en": "Keychain generator...",
        "de": "Schlüsselanhänger-Generator...",
        "es": "Generador de llaveros...",
    },
    "ui.zoom_in_tip": {"fr": "Zoom avant (Ctrl++)", "en": "Zoom in (Ctrl++)", "de": "Vergrößern (Strg++)",
                       "es": "Acercar (Ctrl++)"},
    "ui.zoom_out_tip": {"fr": "Zoom arrière (Ctrl+-)", "en": "Zoom out (Ctrl+-)", "de": "Verkleinern (Strg+-)",
                        "es": "Alejar (Ctrl+-)"},
    # --- Durées (i18n/durations.py) ---
    "time.seconds": {"fr": "{s} s", "en": "{s} s", "de": "{s} s", "es": "{s} s"},
    "time.minutes": {"fr": "{m} min {s:02d} s", "en": "{m} min {s:02d} s", "de": "{m} min {s:02d} s",
                     "es": "{m} min {s:02d} s"},
    "time.hours": {"fr": "{h} h {m:02d} min", "en": "{h} h {m:02d} min", "de": "{h} Std. {m:02d} min",
                   "es": "{h} h {m:02d} min"},
    "view.move": {
        "fr": "Déplacer",
        "en": "Move",
        "de": "Verschieben",
        "es": "Mover",
    },
    "view.reset": {
        "fr": "Réinitialiser la vue",
        "en": "Reset view",
        "de": "Ansicht zurücksetzen",
        "es": "Restablecer la vista",
    },
    "png2svg.no_svg_widget": {
        "fr": "Aperçu SVG indisponible (module PyQt6.QtSvgWidgets absent)",
        "en": "SVG preview unavailable (PyQt6.QtSvgWidgets module missing)",
        "de": "SVG-Vorschau nicht verfügbar (Modul PyQt6.QtSvgWidgets fehlt)",
        "es": "Vista previa SVG no disponible (falta el módulo PyQt6.QtSvgWidgets)",
    },
}
