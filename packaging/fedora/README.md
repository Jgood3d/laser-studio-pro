# Paquet RPM pour Fedora (Copr)

`laser-studio-pro.spec` installe Laser Studio Pro et Stencil Studio avec les
bibliothèques Python de Fedora (PyQt6, OpenCV, NumPy…), sans PyInstaller :
le paquet ne pèse que quelques Mo, et les bibliothèques sont mises à jour
par Fedora.

Il est publié sur Copr, le service de dépôts RPM de Fedora, dans le projet
[alemorvan/laser-studio-pro](https://copr.fedorainfracloud.org/coprs/alemorvan/laser-studio-pro/) :

```bash
sudo dnf copr enable alemorvan/laser-studio-pro
sudo dnf install laser-studio-pro
```

## Choix du paquet

- **OpenCV** : Fedora le fournit sous le nom `opencv` (`python3-opencv`), sans
  variante headless ; le spec remplace `opencv-python-headless` dans
  `pyproject.toml` au moment de la construction.
- **Polices** : les règles de Fedora interdisent d'embarquer une police déjà
  empaquetée. Le dossier `resources/fonts/` (Rubik, Dancing Script, pour les
  modèles de la bibliothèque) est retiré au profit de `google-rubik-fonts` et
  `impallari-dancing-script-fonts`, que Qt trouve sous le même nom. Le
  `fonts/DejaVuSans-Bold.ttf` de Stencil Studio devient un lien vers la police
  de `dejavu-sans-fonts`.
- **Modèle de détourage** (`models/u2netp.onnx`) : pas dans le paquet. Le
  dossier installé n'étant pas modifiable, Stencil Studio le télécharge de
  toute façon dans `~/.local/share/StencilStudio/models` au premier usage de
  la détection du sujet par IA.
- **Dépendances facultatives** : `python3-onnxruntime` (détection du sujet par
  IA dans Stencil Studio) est seulement suggéré : il exige `sympy`, qui
  recommande LaTeX et matplotlib, soit plus de 200 paquets et environ 1 Go.
  Pour l'avoir : `sudo dnf install --setopt=install_weak_deps=False
  python3-onnxruntime` (sans LaTeX). `numba` (accélération du tramage)
  n'existe pas dans Fedora 44 ; l'application s'en passe.
- **Poids restant** : le `python3-opencv` de Fedora dépend de tous les modules
  d'OpenCV, y compris `opencv-viz` (affichage 3D, inutilisé ici) qui entraîne
  VTK, OpenCASCADE, PDAL et Qt 5. `python3-pyqtgraph` exige aussi PyQt5. Ce
  sont des choix des paquets Fedora : le spec ne peut pas les éviter.
- **Entrée de menu et fiche AppStream** : celles de `packaging/linux/`.

## Construire et vérifier en local

Prérequis : `sudo dnf install rpm-build rpmlint mock`.

```bash
# Paquet source depuis le commit courant (version 3.0.0-1.AAAAMMJJ.<nombre de commits>git<commit>)
make -f .copr/Makefile srpm outdir=dist/srpm

# Construction dans un Fedora 44 propre, comme sur Copr (tests compris)
mock -r fedora-44-x86_64 --resultdir=dist/rpm --rebuild dist/srpm/*.src.rpm

# Vérification des règles Fedora
rpmlint packaging/fedora/laser-studio-pro.spec dist/rpm/*.rpm

# Installation pour essayer
sudo dnf install dist/rpm/laser-studio-pro-*.noarch.rpm
```

`--without tests` (à `rpmbuild` ou `mock`) saute les tests, pour aller plus
vite pendant la mise au point.

## Publier sur Copr

Le projet a été créé une fois pour toutes, avec un paquet construit depuis la
branche `Dev` du dépôt GitHub par `.copr/Makefile` (méthode « make srpm ») :

```bash
copr-cli create laser-studio-pro \
    --chroot fedora-43-x86_64 --chroot fedora-44-x86_64 --chroot fedora-45-x86_64 \
    --chroot fedora-43-aarch64 --chroot fedora-44-aarch64 --chroot fedora-45-aarch64 \
    --description "Laser Studio Pro: prepare and engrave images and drawings on GRBL lasers"
copr-cli add-package-scm laser-studio-pro --name laser-studio-pro \
    --clone-url https://github.com/Jgood3d/laser-studio-pro --commit Dev \
    --method make_srpm --spec packaging/fedora/laser-studio-pro.spec \
    --webhook-rebuild on
```

Construire la dernière version de `Dev` :

```bash
copr-cli build-package laser-studio-pro --name laser-studio-pro
```

Essayer une autre branche sans changer le paquet (par exemple celle d'une pull
request) :

```bash
copr-cli buildscm laser-studio-pro --clone-url <dépôt> --commit <branche> \
    --method make_srpm --spec packaging/fedora/laser-studio-pro.spec
```

Pour une reconstruction automatique à chaque push sur `Dev`, ajouter le webhook
indiqué par Copr (*Settings → Integrations*) dans *Settings → Webhooks* du
dépôt GitHub. Le paquet est noarch, mais `dnf copr enable` cherche la version
correspondant à l'architecture de la machine : d'où les chroots aarch64
(Raspberry Pi, Mac Apple Silicon sous Asahi).

Pas de chroot rawhide : la version en développement de Fedora casse
régulièrement des dépendances qui ne sont pas les nôtres (OpenCV, VTK), et
l'échec bloquait le statut de chaque construction. Les versions stables
suffisent ; on ajoutera la suivante (`copr-cli modify --chroot …`, en
redonnant toute la liste) à sa sortie.

## À chaque nouvelle version

Dans `laser-studio-pro.spec` : `Version:` égale à `APP_VERSION`, `Release:`
remise à `1%{?snapinfo}%{?dist}`, et une entrée en tête du `%changelog` (en
anglais). Le reste (archive, dépendances) suit tout seul.
