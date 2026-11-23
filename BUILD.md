# Compiler Laser Studio Pro

Ce guide explique comment installer les dépendances et compiler l'application
en exécutable autonome, sur Windows et sur Linux, en évitant les pièges de
modules manquants ou de conflits de bibliothèques (DLL).

> **Important** : PyInstaller ne fait pas de cross-compilation. Un exécutable
> compilé sur Linux ne fonctionne que sur Linux, un exécutable compilé sur
> Windows ne fonctionne que sur Windows. Il faut lancer la compilation
> **sur chaque OS cible** (ou dans une VM / conteneur de cet OS).

Les scripts de compilation sont rangés dans `packaging/`, un dossier par
système :

| Système | Script | Résultat |
|---|---|---|
| Windows | `packaging\windows\build.bat`, puis `packaging\windows\setup.iss` (Inno Setup) pour l'installateur | `dist\LaserStudioPro\` |
| Linux | `packaging/linux/build-linux.sh` (`--onedir` pour un dossier), puis `packaging/linux/build-appimage.sh` pour l'AppImage | `dist/LaserStudioPro`, `dist/LaserStudioPro-VERSION-x86_64.AppImage` |
| Windows et Linux | `packaging/pyinstaller/LaserStudioPro.spec` (réglages communs, utilisés par les deux scripts) | |
| macOS | `packaging/macos/build_macos.sh` (voir `packaging/macos/README.md`) | `dist/LaserStudioPro.app` |

Ils se lancent depuis n'importe quel dossier et travaillent à la racine du
dépôt. Windows et Linux partagent les mêmes réglages de compilation,
dans `packaging/pyinstaller/LaserStudioPro.spec` : fichiers embarqués
(`src/laser_studio/resources/`, Stencil Studio), modules déclarés, et filtre
des fichiers inutiles (`packaging/pyinstaller/bundle_filter.py`, utilisé
aussi par le `.spec` macOS). Voir [Taille de l'exécutable](#taille-de-lexécutable).

---

## Publier une version (GitHub Actions)

Les binaires des versions sont compilés par GitHub, pas à la main :

- `.github/workflows/tests.yml` : tests sur chaque MR et chaque push vers
  `Dev` et `main` ;
- `.github/workflows/release.yml` : sur un tag `vX.Y.Z`, tests, puis
  compilation Linux (AppImage), Windows (installeur Inno Setup) et macOS
  (`.dmg` arm64 et x86_64), et **release en brouillon** avec ces fichiers.
  Lancé à la main (onglet Actions), il compile sans publier : les fichiers
  sont dans les artefacts du run ;
- `.github/workflows/macos-build.yml` : compilation macOS de contrôle sur
  les MR vers `main`.

Pour sortir la version X.Y.Z :

1. fusionner `Dev` dans `main` ;
2. sur `main`, mettre la version partout (les tests vérifient qu'elles
   concordent) : `APP_VERSION` dans `src/laser_studio/core/version.py`,
   section `## [X.Y.Z] — date` en tête de `CHANGELOG.md`,
   `## Nouveautés de la version X.Y.Z` dans `README.md`,
   `RELEASE_NOTES_X.Y.Z.md` (texte de la release), et une ligne
   `<release version="X.Y.Z" date="…">` en tête de `<releases>` dans
   `packaging/linux/io.github.jgood3d.LaserStudioPro.metainfo.xml` ;
3. poser et pousser le tag : `git tag -a vX.Y.Z -m "Version X.Y.Z"` puis
   `git push origin vX.Y.Z` (le tag doit être égal à `APP_VERSION`) ;
4. attendre la fin du workflow Release, relire le brouillon dans
   *Releases*, puis cliquer sur **Publish release**.

L'AppImage est compilée sur Ubuntu 22.04 : elle tourne sur les
distributions dont la glibc est au moins 2.35 (Ubuntu 22.04+, Debian 12,
Fedora 36+). L'utilisateur doit être dans le groupe `dialout` pour accéder
au port série.

---

## Windows

### 1. Installer Python
Télécharger Python 3.12 (ou plus récent, jusqu'à 3.14) depuis [python.org](https://www.python.org/downloads/)
et cocher **"Add Python to PATH"** pendant l'installation.

### 2. Créer un environnement virtuel (recommandé)
```powershell
python -m venv venv
venv\Scripts\activate

---

## Windows

### 1. Installer Python
Télécharger Python 3.12 (ou plus récent, jusqu'à 3.14) depuis [python.org](https://www.python.org/downloads/)
et cocher "Add Python to PATH" pendant l'installation.

### 2. Créer un environnement virtuel (recommandé)
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Installer les dépendances
```powershell
pip install -r requirements-windows.txt
pip install pyinstaller
```

### 4. Compiler
Le plus simple : `packaging\windows\build.bat` (Stencil Studio compris).
À la main, depuis la racine du projet :
```powershell
pyinstaller --noconfirm packaging\pyinstaller\LaserStudioPro.spec
```
Le code (`core.paths.find_resource`) cherche les images dans `resources/` à
côté de l'exécutable, puis dans le bundle PyInstaller, où le `.spec` les a
embarquées : pas besoin de les copier dans `dist\` après coup.

> Une image absente de `resources/` n'empêche pas la compilation : pour
> l'icône, le code passe au suivant dans sa liste de repli (`.ico` →
> `_256.png` → `_512.png`) et n'affiche une image manquante que si aucune
> n'est trouvée du tout.

### 5. Résultat
Le dossier `dist\LaserStudioPro\`, avec `LaserStudioPro.exe` (base de
l'installeur Inno Setup).

---

## Linux

### 1. Installer Python et les dépendances système
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```
PyQt6 a besoin de quelques bibliothèques système graphiques. Si l'appli ne
se lance pas après installation avec une erreur `libEGL` ou `xcb`, installer :
```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0 libgl1
```

### 2. Créer un environnement virtuel (recommandé)
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements-linux.txt
pip install pyinstaller
```

### 4. Compiler
Le plus simple : `packaging/linux/build-linux.sh` (Stencil Studio compris ;
`--onedir` pour un dossier). À la main, depuis la racine du projet :
```bash
pyinstaller --noconfirm packaging/pyinstaller/LaserStudioPro.spec               # dossier
LSP_ONEFILE=1 pyinstaller --noconfirm packaging/pyinstaller/LaserStudioPro.spec # exécutable unique
```

### 5. Résultat
L'exécutable se trouve dans le dossier `dist/` sous le nom `LaserStudioPro`
(à rendre exécutable si besoin : `chmod +x dist/LaserStudioPro`).

### 6. AppImage (recommandé pour distribuer)
```bash
packaging/linux/build-linux.sh --onedir
packaging/linux/build-appimage.sh            # version : APP_VERSION
```
Résultat : `dist/LaserStudioPro-VERSION-x86_64.AppImage`, un seul fichier,
qui démarre sans décompression dans `/tmp`. Le script télécharge
`appimagetool` dans `build/` (ou utilise celui indiqué par la variable
`APPIMAGETOOL`).

L'entrée de menu vient de `packaging/linux/io.github.jgood3d.LaserStudioPro.desktop`,
commune aux paquets Linux : son nom suit l'identifiant `APP_ID` de
`src/laser_studio/core/version.py`, et le script remplace seulement la
commande (`Exec`) par l'exécutable `LaserStudioPro`. La fiche AppStream
`packaging/linux/io.github.jgood3d.LaserStudioPro.metainfo.xml` (description,
captures de `docs/`, versions) est copiée dans `usr/share/metainfo/`.
Après une modification de l'un ou de l'autre :
```bash
desktop-file-validate packaging/linux/io.github.jgood3d.LaserStudioPro.desktop
appstreamcli validate --no-net packaging/linux/io.github.jgood3d.LaserStudioPro.metainfo.xml
```

### 7. Paquet RPM (Fedora, Copr)
Le spec `packaging/fedora/laser-studio-pro.spec` installe l'application avec
les bibliothèques de Fedora (pas de PyInstaller). Construction, vérification
et publication sur Copr : `packaging/fedora/README.md`.

---

## Taille de l'exécutable

Mesures du 2026-11-15, compilation Linux en dossier : **1 065 Mo → 894 Mo**
décompressés (environ 464 → 395 Mo compressés). Notre code et nos images
pèsent moins de 10 Mo : tout le reste vient des bibliothèques.

Ce qui est retiré :

- **les fichiers inutilisés** (`bundle_filter.py`) : les modules Qt QML
  (Quick 3D, styles QML, multimédia, synthèse vocale… ; l'application
  n'utilise que des widgets), le dossier `qml/`, les outils de développement
  de Chromium, et les traductions de Qt et de QtWebEngine autres que
  français, anglais, allemand et espagnol ;
- **`opencv-python-headless`** au lieu d'`opencv-python` : le même OpenCV,
  sans ses fenêtres (`cv2.imshow`…), que le code n'utilise pas. Il évite
  d'embarquer une deuxième copie de Qt (Qt5) avec OpenCV.

Ce qui reste, et pourquoi :

- **numba** (llvmlite, ~170 Mo décompressés) : sans lui, le tramage d'une
  image de 100 × 100 mm passe de 5–8 ms à 0,5–1,1 s, et de 12–20 ms à
  1–2,4 s pour 150 × 150 mm. Il se recalcule à chaque réglage de l'onglet
  « Graver une image » : on le garde ;
- **QtWebEngine** (~200 Mo décompressés), un navigateur Chromium complet,
  qui ne sert qu'à l'interface HTML de Stencil Studio ;
- **OpenCV**, scipy, numpy, scikit-image, et Qt lui-même.

**À éviter : UPX**, souvent proposé pour compresser les exécutables : il
casse régulièrement les bibliothèques Qt et déclenche de fausses alertes
d'antivirus.

---

## Notes communes aux deux OS

- **Avant de recompiler après une modification du code**, supprimer le cache
  de la compilation précédente pour être sûr que PyInstaller reparte propre :
  ```powershell
  rmdir /s /q build dist
  ```
  (sous Linux : `rm -rf build dist` ; les scripts le font eux-mêmes)
- L'exécutable unique (`LSP_ONEFILE=1`) est plus lent à démarrer : il se
  décompresse dans un dossier temporaire à chaque lancement. Le dossier
  (par défaut) démarre bien plus vite.
- Si `numba` (optionnel) échoue à l'installation ou pendant la compilation,
  le retirer de `requirements-*.txt` : l'application fonctionne sans, mais le
  tramage devient environ cent fois plus lent (voir ci-dessous).
- **Bannière/icône introuvable dans la boîte "À propos"** : vérifier que
  `--add-data` a bien été utilisé à la compilation (voir ci-dessus), *ou* que
  le fichier image est copié directement dans le dossier `dist/` à côté de
  l'exécutable (les deux méthodes fonctionnent). Attention à l'extension
  réelle du fichier : Windows masque les extensions connues par défaut, donc
  un fichier qui *semble* s'appeler `laser_studio_pro_banner.png` dans
  l'Explorateur peut en réalité être `laser_studio_pro_banner.png.png`.
  Vérifier avec `dir laser_studio_pro_banner*` dans une invite de commandes.
