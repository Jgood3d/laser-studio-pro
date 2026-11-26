# Comprendre les calques et les matériaux

[‹ Retour au sommaire](index.md)

Dans Laser Studio Pro, deux notions travaillent ensemble :

- les **calques** (*layers*) disent **quoi faire** :
  graver, découper ou marquer ;
- les **matériaux** disent **avec quelle force** : la même découpe ne
  demande pas la même puissance dans du contreplaqué de 3 mm et dans du
  cuir.

Les deux se règlent dans l'onglet **Calques**.

## Les calques

Un calque regroupe les éléments traités de la même façon. Trois calques de
base sont toujours là : **Gravure**, **Découpe** et **Marquage**. Ils ne
peuvent pas être supprimés ; décochez *Actif* si l'un d'eux ne sert pas.

Vous pouvez ajouter vos propres calques avec **+ Calque**, par exemple :

- une « Gravure légère » pour un ombrage, à côté de la gravure normale ;
- une « Découpe intérieure » à faire avant le contour ;
- un « Marquage fin » pour des lignes de pliage.

Les boutons **Monter** et **Descendre** changent l'ordre des calques : ils
sont exécutés de haut en bas.

La colonne **Air** allume le soufflage (air assist, commande M8) pendant le
calque et l'éteint (M9) ensuite : utile en découpe, pour moins de flammes et
une coupe plus nette.

Un calque a deux sortes de réglages :

- **les mêmes pour tous les matériaux** : nom, couleur, mode (gravure
  remplie, découpe, marquage), surbalayage, commande laser (M3 / M4),
  air assist, actif ;
- **propres à chaque matériau** : puissance, vitesse, nombre de passes, pas
  de remplissage.

## Les matériaux

Un **profil matériau** enregistre, pour chaque calque, sa **puissance**, sa
**vitesse**, son **nombre de passes** et son **pas de remplissage**.

**Chaque calque existe dans chaque matériau, avec des réglages
éventuellement différents.** Le calque *Découpe* est le même partout, mais
il peut être réglé à 95 % et 2 passes pour le contreplaqué, et à 70 % et
1 passe pour le cuir.

Quand vous changez de matériau dans la liste **Profil matériau**, tous les
calques prennent les réglages de ce matériau. Le dessin, lui, ne change
pas : le même fichier peut être découpé dans du bois ou de l'acrylique en
changeant seulement de matériau.

Quelques profils sont fournis au départ : *Personnalisé* (le profil par
défaut), *Contreplaqué 3mm*, *MDF 4mm*, *Acrylique 3mm*, *Ardoise /
Carrelage* et *Cuir 2mm*. Ce sont des points de départ : chaque laser est
différent, vérifiez-les avec une matrice de test.

> ⚠ Les valeurs fournies ne remplacent pas un essai. Une puissance trop
> forte peut enflammer la matière : surveillez toujours la machine.

## Créer un matériau

1. Choisissez le matériau le plus proche du vôtre.
2. Cliquez sur **Nouveau profil…** et donnez-lui un nom (« Bambou 4mm »,
   « Cuir végétal »…). Il démarre avec les réglages actuels.
3. Réglez la puissance, la vitesse, les passes et le pas de chaque calque.

Les modifications sont enregistrées **automatiquement** dans le matériau
choisi : pas besoin de bouton « Enregistrer ».

**Supprimer le profil** retire le matériau choisi (sauf *Personnalisé*, le
profil par défaut).

## Partager ses matériaux

**Exporter les profils (.json)…** enregistre tous vos matériaux dans un
fichier, à garder en sauvegarde ou à partager avec d'autres utilisateurs.
**Importer des profils (.json)…** les ajoute ; un matériau du même nom est
mis à jour.

Les matériaux sont propres à chaque **profil de machine** (menu
*Fichier › Paramètres › Paramètres du graveur*) : deux graveurs de puissances
différentes gardent chacun leurs réglages.

Pour créer le profil d'un graveur du commerce (Elegoo Phecda, Ortur Laser
Master 3, Sculpfun, Creality Falcon, Longer Ray5, xTool D1 Pro…), cliquez
sur **Depuis le catalogue…** : choisissez la marque et le modèle, puis
**Créer le profil**. La surface de travail, la taille du point et la
vitesse maximale publiées par le constructeur sont reprises, avec les liens
vers ses documents. L'accélération n'est pas publiée : une fois connecté,
**Lire la config** (*Fichier › Paramètres › Configuration GRBL*) lit les réglages
réels de la machine, dont se sert la durée estimée des gravures. Le
catalogue n'envoie rien au graveur.

## Trouver les bons réglages

**Outils › Matrice de Test** grave une grille de carrés, chacun avec une
puissance et une vitesse différentes. Gravez-la sur une chute de votre
matériau, repérez le carré le plus réussi, et reportez ses valeurs dans le
calque correspondant.

Pour la découpe : cherchez la vitesse la plus rapide qui traverse
proprement la matière, en une passe ou plus. Pour le marquage : la
puissance la plus faible qui laisse un trait bien visible.

Voir aussi [Comprendre les différents modes de gravure](modes-de-gravure.md).
