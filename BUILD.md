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
| Linux | `packaging/linux/build-linux.sh` (`--onedir` pour un dossier) | `dist/LaserStudioPro` |
| macOS | `packaging/macos/build_macos.sh` (voir `packaging/macos/README.md`) | `dist/LaserStudioPro.app` |

Ils se lancent depuis n'importe quel dossier et travaillent à la racine du
dépôt. Les commandes détaillées ci-dessous restent utiles pour comprendre
ce qu'ils font, ou compiler à la main.

---

## Windows

### 1. Installer Python
Télécharger Python 3.11 ou 3.12 depuis [python.org](https://www.python.org/downloads/)
et cocher **"Add Python to PATH"** pendant l'installation.

### 2. Créer un environnement virtuel (recommandé)
```powershell
python -m venv venv
venv\Scripts\activate

---

## Windows

### 1. Installer Python
Télécharger Python 3.11 ou 3.12 depuis [python.org](https://www.python.org/downloads/)
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
À la main, depuis le dossier du projet (tous les fichiers `.py` du découpage doivent
être présents), avec le dossier `resources/` (icône, bannière, logo,
image « Buy me a coffee », pack d'icônes Breeze dans `resources/icons/`) :
```powershell
pyinstaller --onefile --windowed --name LaserStudioPro --icon=resources\laser_studio_pro.ico --add-data "resources;resources" main.py
Avec Stencil Studio :

pyinstaller --onefile --windowed --name LaserStudioPro --icon=resources\laser_studio_pro.ico --add-data "resources;resources" --add-data "stencil_studio;stencil_studio" main.py

```
Sous Windows, `--add-data` sépare source et destination par `;`. Le code
(`app_utils.find_resource`) cherche ces images dans `resources/` à côté de
l'exécutable, puis dans le bundle PyInstaller, donc `--add-data` suffit — pas
besoin de copier les images manuellement dans `dist\` après coup.

> Une image absente de `resources/` n'empêche pas la compilation : pour
> l'icône, le code passe au suivant dans sa liste de repli (`.ico` →
> `_256.png` → `_512.png`) et n'affiche une image manquante que si aucune
> n'est trouvée du tout.

### 5. Résultat
L'exécutable `LaserStudioPro.exe` se trouve dans le dossier `dist\`.

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
Le plus simple : `packaging/linux/build-linux.sh` (Stencil Studio compris).
À la main :
```bash
pyinstaller --onefile --windowed --name LaserStudioPro --icon=resources/laser_studio_pro.ico --add-data "resources:resources" main.py

Avec Stencil studio

pyinstaller --onefile --windowed --name LaserStudioPro --icon=resources/laser_studio_pro.ico --add-data "resources:resources" --add-data "stencil_studio:stencil_studio" --collect-submodules serial --hidden-import=serial main.py
```
Sous Linux, `--add-data` sépare source et destination par `:` (au lieu de `;`).
Comme sous Windows, `app_utils.find_resource` retrouve ces images aussi bien
embarquées via `--add-data` que placées à côté de l'exécutable.

### 5. Résultat
L'exécutable se trouve dans le dossier `dist/` sous le nom `LaserStudioPro`
(à rendre exécutable si besoin : `chmod +x dist/LaserStudioPro`).

---

## Notes communes aux deux OS

- **Avant de recompiler après une modification du code**, supprimer le cache
  de la compilation précédente pour être sûr que PyInstaller reparte propre :
  ```powershell
  rmdir /s /q build dist
  del LaserStudioPro.spec
  ```
  (sous Linux : `rm -rf build dist LaserStudioPro.spec`)
- Le fichier `--onefile` génère un exécutable unique mais plus lent à
  démarrer (extraction dans un dossier temporaire à chaque lancement).
  Retirer cette option pour obtenir un dossier avec l'exécutable et ses
  dépendances à côté (démarrage plus rapide, mais moins pratique à distribuer).
- Un fichier `LaserStudioPro.spec` est généré à la première compilation :
  le conserver et relancer `pyinstaller LaserStudioPro.spec` (au lieu de la
  commande complète) accélère les recompilations suivantes.
- Si `numba` (optionnel) échoue à l'installation ou pendant la compilation,
  le retirer de `requirements-*.txt` : l'application fonctionne sans, avec un
  tramage d'image simplement plus lent.
- **Bannière/icône introuvable dans la boîte "À propos"** : vérifier que
  `--add-data` a bien été utilisé à la compilation (voir ci-dessus), *ou* que
  le fichier image est copié directement dans le dossier `dist/` à côté de
  l'exécutable (les deux méthodes fonctionnent). Attention à l'extension
  réelle du fichier : Windows masque les extensions connues par défaut, donc
  un fichier qui *semble* s'appeler `laser_studio_pro_banner.png` dans
  l'Explorateur peut en réalité être `laser_studio_pro_banner.png.png`.
  Vérifier avec `dir laser_studio_pro_banner*` dans une invite de commandes.
