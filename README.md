# Laser Studio Pro

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jb3dlaser)

Laser Studio Pro est un logiciel de pilotage GRBL pour graveur et découpeuse laser, avec :
- gravure d’images,
- découpe/gravure vectorielle,
- gestion de calques,
- génération de G-Code,
- export/import de projets,
- support multilingue (Français, English, Deutsch, Español).

## Lancer l’application

Lancez `main.py` depuis le dossier du projet.

```bash
python main.py
```

## Structure du projet

### Point d’entrée
- `main.py` — lance l’application
- `app_utils.py` — version de l’application et chemins de ressources

### Composants autonomes
- `graphics_view.py` — `ZoomableGraphicsView`
- `vector_font.py` — `VectorFont`
- `usb_controller.py` — `LaserUSBController`
- `workers.py` — threads et fonctions de traitement image / G-Code
- `i18n.py` — système de traduction multilingue

### Fenêtre principale découpée en mixins
- `main_window.py` — assemblage de la fenêtre principale
- `ui_setup_mixin.py` — interface utilisateur, menus, onglets, dialogues
- `machine_profiles_mixin.py` — profils machine / matériaux
- `image_processing_mixin.py` — chargement et traitement d’image
- `vector_editing_mixin.py` — éditeur vectoriel et SVG
- `gcode_generation_mixin.py` — génération, aperçu et export G-Code
- `laser_control_mixin.py` — USB / GRBL / commandes temps réel
- `project_io_mixin.py` — sauvegarde et ouverture de projet

## Fonctionnalités récentes

### 1.3.1
- finalisation du support multilingue sur les libellés restants de l’interface,
- traduction des onglets, panneaux, matrices de test, dialogues, messages GRBL,
- localisation des éléments de la console et du système d’édition vectorielle,
- texte de support et bouton “Buy me a coffee” maintenant traduits,
- amélioration de la cohérence de l’interface entre les langues supportées.

## Développement / validation

Pour vérifier la syntaxe Python :

```bash
py -m py_compile i18n.py ui_setup_mixin.py main_window.py
```

## Remerciements

Merci à toutes les personnes qui contribuent au projet, testent les fonctionnalités et signalent les bugs.

## Licence

Voir le fichier `LICENSE` associé au dépôt si présent.
