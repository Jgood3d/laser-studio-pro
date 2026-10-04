## [2.2.0] — 2026-10-04

### Ajouté
- **Image / Filtres — sélecteur « Matière »** : liste placée juste au-dessus de « Inverser Couleurs ».
  « Fond noir » (aluminium anodisé, verre peint, ardoise, acrylique noir : le laser éclaircit ce qu'il brûle) active l'inversion ; « Fond clair » (bois, carton, cuir : le laser noircit ce qu'il brûle) la désactive.
  Le sélecteur ne fait que cocher/décocher « Inverser Couleurs » : la case reste modifiable à la main et le miroir reste indépendant.
  Le choix est enregistré dans le projet (un ancien projet le déduit de son inversion), pris en compte par Annuler/Rétablir, et remis sur « fond clair » par la réinitialisation des réglages image.
  L'alerte de confirmation avant gravure d'une image rappelle la matière, par exemple « Matière : fond noir (négatif activé) » ; elle reflète l'état réel de la case et signale donc une incohérence. Traduit en FR / EN / DE / ES.
- **Calques — réglages mémorisés par machine** : mode, puissance, vitesse, passes, pas de remplissage (et son lien à la focale) et état actif de chaque calque sont rangés dans le profil de la machine active.
  Enregistrement 0,6 s après chaque modification et à la fermeture (donc aussi après un plantage) ; restauration complète des calques au démarrage (noms, couleurs, calques ajoutés).
  En changeant de machine en cours de session, seuls les réglages de l'autre machine sont appliqués, aux calques existants (par identifiant puis par position) : aucun calque n'est ajouté, supprimé ni renommé, pour que les objets du canevas restent rattachés à leur calque. « Nouvelle machine » et « Mettre à jour » incluent les calques. Les anciens profils sans calques mémorisés ne changent rien.
- **Onglet « Séparation Couleur / Verre »** : à partir d'une image couleur, produit le calque noir à graver (tonalité envoyée à Image / Filtres, qui applique luminosité, contraste, gamma, tramage et résolution), le calque couleur à imprimer à la même taille physique, une simulation du rétro-éclairage, et un PDF A4 à l'échelle 1:1 avec repères de coin. Réglages : recadrage, gain de point, miroir à l'impression.
  À l'import, les réglages « verre » (matière fond noir, négatif, miroir horizontal) sont appliqués puis restitués au chargement d'une image classique.
- **Tests automatiques** (dossier `tests/`, `python -m unittest discover tests -v`) : génération du G-code d'image rejouée comme GRBL, écriture atomique, reset/référencement, mémorisation des calques par machine, contrôle des traductions.
- **Outil `tools/check_translations.py`** : rapport sur les clés jamais utilisées, les textes d'interface écrits en dur, les valeurs identiques entre langues et le mélange tutoiement/vouvoiement.

### Modifié
- **Éditeur vectoriel — vue** : la vue se cadre et se centre automatiquement sur le SVG importé (import SVG et PNG → SVG) ainsi qu'à l'entrée et à la sortie du plein écran. Le zoom s'ajuste à l'objet (plafonné pour les très petits objets).
- **Interface — panneau du bas** : le panneau Position machine / Jog / Commandes / Console GRBL n'est affiché que dans « Visualisation 2D G-Code », « Console / G-Code » et « File d'attente ». Il reste visible tant qu'un job est en cours, quel que soit l'onglet (Pause, Reset et Arrêt d'urgence toujours accessibles). Sa hauteur réglée est mémorisée.
- **RESET / ARRÊT D'URGENCE** : les deux boutons passent par une seule fonction commune.
- **Traductions** : message de fin de file d'attente et description de la fenêtre « À propos » désormais traduits ; deux clés définies en double dans `i18n.py` supprimées.

### Corrigé
- **Gravure d'image — puissance appliquée au mauvais segment** : à chaque changement de puissance, le G-code envoyait le déplacement jusqu'à la frontière avec la puissance du segment *suivant* (GRBL applique le `S` d'une ligne à son propre déplacement). Une ligne sur deux, les zones à conserver étaient gravées et celles à graver épargnées ; en balayage retour (droite → gauche), la frontière était en plus décalée d'un pixel (motif en peigne). Corrigé et couvert par un test qui rejoue le G-code.
- **Reset / Arrêt d'urgence en mouvement** : GRBL perd sa position lorsqu'il est réinitialisé alors que la machine bouge. Le statut « référencé » est maintenant retiré (un message l'indique dans la console) et un nouveau homing est demandé avant le job suivant. Un reset fait machine à l'arrêt ne change rien.
- **Sauvegardes** : l'autosave, la file d'attente et la sauvegarde manuelle du projet s'écrivent maintenant de façon atomique (fichier temporaire puis remplacement) ; un plantage, une coupure ou un disque plein en cours d'écriture ne laisse plus un fichier tronqué.
- **Chargement de projet** : l'état mémorisé par l'onglet Séparation est réinitialisé ; charger ensuite une image dans Images / Tramage ne remet plus à tort l'ancien négatif, miroir et matière par-dessus ceux du projet.
- **Homing (`$H`)** : la réponse n'est plus coupée au bout de 2 s pendant que la machine se déplace (délai porté à 90 s pour les commandes `$H…`).
- **File d'attente** : noms de jobs désormais uniques (deux jobs ajoutés dans la même seconde empêchaient de sauvegarder le nouvel ordre après un glisser-déposer) ; la barre de progression ne divise plus par zéro.
- **Console GRBL** : la flèche Bas n'efface plus ce que tu es en train de taper.
- **Interface** : un libellé à masquage automatique sans parent ne s'affiche plus comme une fenêtre isolée avant sa mise en page.
- **Aperçu 2D** : quand « Aperçu en négatif » est décoché, la gravure noire était illisible sur le fond sombre. Elle est maintenant simulée sur un fond clair (matériau), avec les découpes et contours toujours visibles par-dessus.

### Migration
- Aucun format n'est cassé : les projets, profils machine et files d'attente existants se chargent normalement (les clés ajoutées, `material_bg` et `layers`, ont une valeur de repli).
- Au premier lancement, les calques gardent leurs valeurs par défaut jusqu'à la première fermeture de l'application (les profils existants n'ont pas encore de calques mémorisés).
- Les G-codes d'image générés avec une version antérieure sont à régénérer (voir la correction de la puissance par segment).

Fichiers modifiés :
app_utils.py, workers.py, image_processing_mixin.py, ui_setup_mixin.py, project_io_mixin.py,
gcode_generation_mixin.py, laser_control_mixin.py, job_queue_mixin.py, machine_profiles_mixin.py,
usb_controller.py, widgets_extra.py, separation_mixin.py, i18n.py — nouveaux : tests/, tools/
