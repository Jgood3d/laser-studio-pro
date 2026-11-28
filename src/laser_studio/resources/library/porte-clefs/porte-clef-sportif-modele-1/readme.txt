================================================================================
  PORTE-CLEF SPORTIF - MODÈLE 1
  Modèle de la bibliothèque Laser Studio Pro
================================================================================

Technique    : Gravure + découpe laser
Licence      : Libre d'utilisation pour usage personnel et associatif

--------------------------------------------------------------------------------
  PRÉSENTATION
--------------------------------------------------------------------------------

Ce porte-clefs porte un motif sportif dans un cadre gravé, avec un trou pour
l'anneau. Le motif se choisit dans cette fiche (liste « Motif ») :

  Aviron (diagonal)         →  bateau d'aviron en style losanges, en diagonale
                               (par défaut)
  Aviron (horizontal)       →  le même bateau, à l'horizontale
  Basket-ball (1 contre 1)  →  deux joueurs en 1 contre 1
  Kayak, Surf, Natation, Course, Vélo, Ballon de basket, Handball,
  Volley-ball, Gymnastique, Arts martiaux  →  pictogrammes sportifs


--------------------------------------------------------------------------------
  GRAVER ET DÉCOUPER AVEC LASER STUDIO PRO
--------------------------------------------------------------------------------

  1. Dans cette fiche, choisir le motif. L'onglet « Aperçu » montre le
     porte-clefs tel qu'il sera importé.

  2. Cliquer sur « Importer dans l'éditeur vectoriel ». Le porte-clefs
     (50 × 50 mm) arrive sur deux calques :
       - Gravure : le cadre et le motif (gravure remplie) ;
       - Découpe : le contour du porte-clefs et le trou de l'anneau.

  3. Dans l'onglet « Calques », choisir le profil matériau de votre
     planche (ou régler vitesse, puissance et passes de chaque calque).
     Exemples pour du contreplaqué de 3 mm (à tester sur une chute) :
       - Gravure : 2000–3000 mm/min, 30–50 %
       - Découpe : 500–800 mm/min, 80–100 %, passes selon l'épaisseur

  4. Vérifier que « Ordre de découpe sûr » est coché (Paramètres →
     Configuration GRBL) : la gravure est faite avant la découpe, et le
     trou de l'anneau avant le contour. Ainsi, la pièce ne bouge pas avant
     la fin.

  5. Cliquer sur « GÉNÉRER LE G-CODE », contrôler le parcours dans l'onglet
     « Visualisation 2D G-Code », positionner la planche (« Cadrage »), puis
     « ENVOYER AU LASER ».

  Pour une série (club, compétition) : importer le porte-clefs une fois,
  puis le dupliquer (« Dupliquer en série… » ou « Imbrication auto » dans
  l'éditeur vectoriel) pour remplir la planche.

  /!\ Effectuez toujours un test sur une chute de matériau avant la pièce
  finale.


--------------------------------------------------------------------------------
  CONSEILS MATÉRIAUX
--------------------------------------------------------------------------------

  Ce porte-clefs est adapté à plusieurs matériaux :

  Contreplaqué tilleul ou peuplier (3-4 mm)
    → Rendu chaleureux, gravure contrastée, découpe facile
    → Idéal pour un résultat artisanal et naturel

  Acrylique (2–3 mm)
    → Rendu plus moderne et brillant
    → La gravure sera plus claire (effet dépoli) sur fond coloré

  Cuir (2 mm)
    → Rendu premium, très apprécié pour les souvenirs de club
    → Réduire la puissance de gravure pour éviter de brûler


--------------------------------------------------------------------------------
  LICENCE DES PICTOGRAMMES
--------------------------------------------------------------------------------

  Les pictogrammes sportifs (kayak, surf, natation, course, vélo, ballon de
  basket, handball, volley-ball, gymnastique, arts martiaux) viennent de
  Material Symbols, de Google, sous licence Apache 2.0 (texte complet dans
  LICENCE-material-symbols.txt). Ils ont été mis à l'échelle du porte-clefs.
  https://github.com/google/material-design-icons


--------------------------------------------------------------------------------
  CONTACT & PARTAGE
--------------------------------------------------------------------------------

  Si vous réalisez ce porte-clefs pour votre club, vos sportifs ou une
  compétition, n'hésitez pas à partager vos résultats !
  Tout retour sur les paramètres laser utilisés est le bienvenu.
