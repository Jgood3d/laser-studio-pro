# Paquet RPM pour Fedora (Copr)

`laser-studio-pro.spec` installe Laser Studio Pro et Stencil Studio avec les
bibliothèques Python de Fedora (PyQt6, OpenCV, NumPy…), sans PyInstaller :
le paquet ne pèse que quelques Mo, et les bibliothèques sont mises à jour
par Fedora.

Il est publié sur [Copr](https://copr.fedorainfracloud.org/), le service de
dépôts RPM de Fedora : `sudo dnf copr enable <compte>/laser-studio-pro`, puis
`sudo dnf install laser-studio-pro`.

## Choix du paquet

- **OpenCV** : Fedora le fournit sous le nom `opencv` (`python3-opencv`), sans
  variante headless ; le spec remplace `opencv-python-headless` dans
  `pyproject.toml` au moment de la construction.
- **Police de Stencil Studio** : `fonts/DejaVuSans-Bold.ttf` devient un lien
  vers la police du système (`dejavu-sans-fonts`), comme le demandent les
  règles de Fedora pour les polices déjà empaquetées.
- **Modèle de détourage** (`models/u2netp.onnx`) : pas dans le paquet. Le
  dossier installé n'étant pas modifiable, Stencil Studio le télécharge de
  toute façon dans `~/.local/share/StencilStudio/models` au premier usage de
  la détection du sujet par IA.
- **Dépendances facultatives** : `python3-onnxruntime` est recommandé (détection
  du sujet par IA). `numba` (accélération du tramage) n'existe pas dans
  Fedora 44 ; l'application s'en passe.
- **Entrée de menu et fiche AppStream** : celles de `packaging/linux/`.

## Construire et vérifier en local

Prérequis : `sudo dnf install rpm-build rpmlint mock`.

```bash
# Paquet source depuis le commit courant (version 2.5.0-1.AAAAMMJJgit<commit>)
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

Une seule fois : créer le projet, puis un paquet construit depuis le dépôt
GitHub avec `.copr/Makefile` (méthode « make srpm ») :

```bash
copr-cli create laser-studio-pro \
    --chroot fedora-44-x86_64 --chroot fedora-rawhide-x86_64 \
    --description "Laser Studio Pro: prepare and engrave images and drawings on GRBL lasers"
copr-cli add-package-scm laser-studio-pro --name laser-studio-pro \
    --clone-url https://github.com/Jgood3d/laser-studio-pro --commit main \
    --method make_srpm --spec packaging/fedora/laser-studio-pro.spec \
    --webhook-rebuild on
copr-cli build-package laser-studio-pro --name laser-studio-pro
```

Pour une reconstruction automatique à chaque push, ajouter le webhook indiqué
par Copr (*Settings → Integrations*) dans *Settings → Webhooks* du dépôt
GitHub. Un second paquet, sur la branche `Dev`, peut servir de version de
développement.

## À chaque nouvelle version

Dans `laser-studio-pro.spec` : `Version:` égale à `APP_VERSION`, `Release:`
remise à `1%{?snapinfo}%{?dist}`, et une entrée en tête du `%changelog` (en
anglais). Le reste (archive, dépendances) suit tout seul.
