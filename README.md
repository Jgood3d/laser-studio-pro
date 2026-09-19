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

## [1.5.0]

### Ajouté
- **Utilitaire de conversion PNG vers SVG (Vectorisation)** :
  - Outil intégré permettant de transformer directement des images matricielles (PNG) en tracés vectoriels SVG.
  - Réglages fins de vectorisation : ajustement du seuil de tolérance (Noir/Blanc), simplification et lissage des contours, et filtrage du bruit.
  - Aperçu instantané du rendu vectoriel avant insertion dans le projet de découpe ou gravure.

<img width="752" height="347" alt="Pngtosvg" src="https://github.com/user-attachments/assets/d0ba31f9-e33a-4533-8a87-b722a30fc6ec" />

## 🚀 Release v1.4.1

### ✨ Améliorations & Ergonomie

* **Positionnement dynamique à la souris :** Possibilité de sélectionner et de déplacer l'intégralité d'un fichier SVG directement sur le plan de travail.
* **Ajustement de précision (Offset X / Y) :** Ajout des contrôles de décalage X et Y pour affiner la position exacte de vos éléments vectoriels au millimètre près.

---
*Cette version apporte plus de souplesse dans la manipulation des calques vectoriels et accélère la préparation de vos projets.*

## [1.4.0]
Ajouté
Traduction quasi complète de l'application (Français, Anglais, Allemand, Espagnol) : quasiment toutes les boîtes de dialogue, messages d'erreur/confirmation et libellés de boutons de l'ensemble des onglets utilisent désormais le système i18n.py — 319 chaînes traduites au total, vérifiées une à une contre le dictionnaire (aucune clé manquante).
Corrigé
## 1.3.1 + : corrections du rendu 2D pour les calques vectoriels/texte/SVG (voir détails ci-dessous) et adresse e-mail Support mise à jour (laserstudiopro.support@proton.me).
Coquille QQMessageBox (au lieu de QMessageBox) dans laser_control_mixin.py, qui aurait fait planter l'appli au clic sur "Connecter" sans port COM sélectionné.
UnboundLocalError au démarrage : legacy_svg_box était utilisé avant sa création dans ui_setup_mixin.py (ordre des blocs corrigé).
Rendu 2D des calques vectoriels/texte/SVG : plusieurs calques classés à tort comme "balayage raster" étaient fusionnés dans une seule image, produisant un rendu incohérent. Chaque calque raster est maintenant reconstruit séparément, teinté avec sa propre couleur.

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
