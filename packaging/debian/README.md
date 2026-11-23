# Paquet Debian (.deb)

`build-deb.sh` construit un paquet `.deb` qui installe Laser Studio Pro et Stencil Studio avec les
bibliothèques Python de Debian (PyQt6, OpenCV, NumPy…), sans PyInstaller : le paquet ne pèse que
quelques Mo, et les bibliothèques sont mises à jour par le système.

**Systèmes pris en charge** : Debian 13 (trixie) et plus récentes, Ubuntu 25.04 et plus récentes.
Ubuntu 24.04 n'a que PyQt6 6.6 alors que l'application demande la 6.7 : apt refuse l'installation
(dépendance non satisfaite) ; utiliser l'AppImage.

```bash
sudo apt install ./laser-studio-pro_2.5.0_all.deb
```

## Construire

```bash
packaging/debian/build-deb.sh                  # → dist/deb/laser-studio-pro_<version>_all.deb
packaging/debian/build-deb.sh --test           # puis installe et teste le paquet
packaging/debian/build-deb.sh --no-build --test --test-image docker.io/library/ubuntu:25.10
```

- Sur Debian ou Ubuntu avec `dpkg-buildpackage`, la construction se fait sur place (installer d'abord
  `build-essential debhelper dh-python pybuild-plugin-pyproject python3-all python3-setuptools
  desktop-file-utils appstream`). Ailleurs (Fedora…), dans un conteneur `debian:trixie` (podman, sinon
  docker).
- `--test` installe le paquet dans un conteneur propre, vérifie que l'application démarre (utilisateur
  normal, sans écran) et lance la suite de tests du dépôt avec les versions Debian des bibliothèques.
- **Version** : celle de `src/laser_studio/core/version.py` sur un tag `v<version>` ; sinon une version
  de développement `<version>~git<AAAAMMJJ>.<nombre de commits>.<commit>`, classée avant la version
  publiée et dans l'ordre des commits.

Le workflow de release (`.github/workflows/release.yml`, job `debian`) construit le paquet dans
Debian 13, l'installe, vérifie qu'il démarre et le joint à la release.

## Choix du paquet

- **Fichiers** : `debian/` (control, rules, copyright, source/format) ; le `changelog` est écrit par
  `build-deb.sh` à chaque construction.
- **Dépendances** : écrites à la main dans `debian/control` avec les noms Debian (`python3-opencv` pour
  `opencv-python-headless`, `python3-yaml` pour PyYAML…). `python3-numba` (accélération du tramage) est
  recommandé, `python3-onnxruntime` (détection du sujet par IA dans Stencil Studio) suggéré.
- **Polices** : Debian n'a pas Rubik ; les polices embarquées (licence OFL) restent dans le paquet.
- **Modèle de détourage** (`u2netp.onnx`) : retiré, comme dans le paquet Fedora. Stencil Studio le
  télécharge dans `~/.local/share/StencilStudio/models` au premier usage de la détection par IA.
- **Tests pendant la construction** : seulement une compilation du code (`compileall`) ; les vrais tests
  demandent un affichage et toutes les dépendances, voir `--test`.
