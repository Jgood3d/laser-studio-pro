================================================================================
  MÉDAILLE SKIFFEUR
  Modèle de la bibliothèque Laser Studio Pro
================================================================================

Auteur       : Antoine Le Morvan
Technique    : Gravure + découpe laser
Licence      : Libre d'utilisation pour usage personnel et associatif


--------------------------------------------------------------------------------
  PRÉSENTATION
--------------------------------------------------------------------------------

Cette médaille est conçue pour récompenser les compétiteurs lors de régates
d'aviron. Elle représente un skiffeur et se décline en plusieurs variantes,
au choix dans cette fiche (liste « Résultat ») :

  1ère place  →  podium compétition
  2e place    →  podium compétition
  3e place    →  podium compétition
  Étoile      →  récompense spéciale Challenge Jeune

Le nom de la régate se modifie dans cette fiche (champ « Régate de XXXX »),
avant l'import.

La médaille est une pièce unique découpée au laser, percée d'un trou pour
y passer un ruban ou un cordon.


--------------------------------------------------------------------------------
  GRAVER ET DÉCOUPER AVEC LASER STUDIO PRO
--------------------------------------------------------------------------------

  1. Dans cette fiche :
       - choisir le résultat (1ère, 2e ou 3e place, ou Étoile) ;
       - remplacer « Régate de XXXX » par le nom de votre régate.
     L'onglet « Dessin à graver » montre la médaille telle qu'elle sera
     importée.

  2. Cliquer sur « Importer dans l'éditeur vectoriel ». La médaille arrive
     sur deux calques :
       - Gravure : le fond noir, le skiffeur, les rameaux et le numéro ;
       - Découpe : le contour de la médaille et le trou du ruban.

     Le nom de la régate est en réserve (non gravé) dans le bandeau noir :
     il est donc importé comme un tracé, et non comme un texte modifiable.
     Pour le changer, revenir à cette fiche et importer à nouveau. Le
     numéro, lui, reste un texte modifiable dans l'éditeur vectoriel.

  3. Dans l'onglet « Calques (Layers) », choisir le profil matériau de votre
     planche (ou régler vitesse, puissance et passes de chaque calque).
     Exemples pour du contreplaqué de 3 mm (à tester sur une chute) :
       - Gravure : 2000–3000 mm/min, 30–50 %
       - Découpe : 500–800 mm/min, 80–100 %, passes selon l'épaisseur

  4. Vérifier que « Ordre de découpe sûr » est coché (Paramètres →
     Configuration GRBL) : la gravure est faite avant la découpe, et le
     trou du ruban avant le contour. Ainsi, la médaille ne bouge pas avant
     la fin.

  5. Cliquer sur « GÉNÉRER LE G-CODE », contrôler le parcours dans l'onglet
     « Visualisation 2D G-Code », positionner la planche (« Cadrage »), puis
     « ENVOYER AU LASER ».

  Pour une série (1ère, 2ème, 3ème place) : importer la médaille plusieurs
  fois, une par variante, et les répartir sur la planche (« Imbrication
  auto » dans l'éditeur vectoriel).


--------------------------------------------------------------------------------
  FINITION
--------------------------------------------------------------------------------

  Ruban / cordon :
    - Ruban satin (15 mm de largeur) pour un rendu soigné
    - Cordon ciré ou paracorde pour un style plus sportif
    - Couleur à adapter aux couleurs du club ou de la régate

  Optionnel :
    - Poncer légèrement à l'aide d'une dremel les bords après découpe
      pour un toucher plus doux
    - Appliquer une couche de vernis ou d'huile pour protéger le bois
      et faire ressortir la gravure


--------------------------------------------------------------------------------
  CONSEILS MATÉRIAUX
--------------------------------------------------------------------------------

  Contreplaqué tilleul ou peuplier (3 mm)
    → Rendu chaud et naturel, gravure très contrastée
    → Idéal pour un rendu artisanal et authentique

  Contreplaqué bouleau (3 mm)
    → Surface plus lisse, aspect légèrement plus premium
    → Très bon compromis qualité / prix pour des séries


--------------------------------------------------------------------------------
  CONTACT & PARTAGE
--------------------------------------------------------------------------------

  Si vous utilisez ces médailles lors de vos régates, n'hésitez pas à
  partager vos résultats et vos paramètres laser !
  Tout retour sur les matériaux utilisés ou les finitions est le bienvenu.


================================================================================
  Bon découpage, et belles régates !
================================================================================
