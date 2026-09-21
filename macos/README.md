# Laser Studio Pro — macOS

Ce dossier regroupe tout ce qui est nécessaire pour lancer et compiler
Laser Studio Pro sur macOS, séparément des chaînes de build Windows
(`requirements-windows.txt`, `LaserStudioPro_Setup.iss`) et Linux
(`requirements-linux.txt`) qui restent à la racine du dépôt, inchangées.

Voir aussi le [rapport d'audit du portage macOS](../MACOS_AUDIT.md).

## Installation (lancer depuis les sources)

Depuis la racine du dépôt :

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r macos/requirements-macos.txt
python main.py
```

Ou plus simplement, via le script fourni (crée le venv, installe les
dépendances et lance l'appli en une seule commande) :

```bash
./macos/run_macos.sh
```

`numba` (accélération optionnelle du tramage d'image) n'est pas installé
par défaut sur macOS — voir `requirements-macos.txt` pour l'activer si ta
version de Python dispose d'une wheel compatible.

## Permissions et pilote série

- À la première connexion d'une carte GRBL en USB, macOS peut demander
  d'autoriser l'accès à l'accessoire — accepter la demande système.
- La plupart des cartes GRBL basées sur des puces **CH340/CH341** (clones
  Arduino Nano, etc.) nécessitent l'installation d'un pilote série, par
  exemple le [pilote CH340 pour macOS](https://github.com/WCHSoftGroup/ch34xser_macos)
  (ou celui fourni par le fabricant de la carte). Après installation,
  redémarrer le Mac.
- Les cartes basées sur **FTDI** ou **CP210x** fonctionnent en général
  sans pilote supplémentaire sur macOS récent (pilote inclus dans le
  système), ou nécessitent le pilote du fabricant (Silicon Labs pour
  CP210x) le cas échéant.

## Dépannage port série

- Si le port GRBL n'apparaît pas dans la liste des ports : vérifier le
  câble USB (certains câbles ne transportent que l'alimentation, pas les
  données), puis vérifier dans **Réglages Système → Confidentialité et
  sécurité** qu'aucune autorisation liée aux accessoires USB n'est en
  attente.
- Le port apparaît sous la forme `/dev/cu.usbserial-XXXX`,
  `/dev/cu.wchusbserial-XXXX` ou `/dev/cu.usbmodemXXXX` selon la puce USB
  de la carte — c'est normal, l'équivalent macOS des `COMx` Windows.
- Si la connexion échoue avec une erreur de type « port occupé » ou
  « Resource busy » : un autre programme (ex. moniteur série d'un IDE
  Arduino resté ouvert) utilise probablement déjà le port ; le fermer
  avant de relancer Laser Studio Pro.

## Compiler en .app / .dmg

Depuis la racine du dépôt :

```bash
./macos/build_macos.sh
```

Ça crée un environnement de build isolé (`build_venv/`), compile avec
PyInstaller (`macos/LaserStudioPro.spec`), génère l'icône `.icns` si besoin,
puis produit `dist/LaserStudioPro.app` et `dist/LaserStudioPro_<version>_macos_<arch>.dmg`.

Cible l'architecture de la machine qui compile (arm64 ou x86_64) — pas de
build universal2 (numba/opencv-python n'ont pas toujours de wheels
universal2 à jour). Pour couvrir les deux architectures, compiler une fois
sur une machine Apple Silicon et une fois sur une machine Intel (ou via la
CI, voir `.github/workflows/macos-build.yml`).

L'app n'est pas signée par un compte développeur Apple. Pour l'ouvrir
malgré Gatekeeper au premier lancement :
- clic droit sur l'app > Ouvrir, ou
- `xattr -dr com.apple.quarantine dist/LaserStudioPro.app`
