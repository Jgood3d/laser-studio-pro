# Audit portage macOS — Laser Studio Pro

Audit en lecture seule, aucune modification de code. Machine de test : Apple Silicon (arm64), macOS 26 (Darwin 25.6.0).

## Résumé

Le code est globalement propre pour un portage macOS : pas de filtrage `COM*` en dur, pas de séparateurs de chemin Windows codés en dur, `QSettings`/`QThread`/`QKeySequence.StandardKey` déjà utilisés de façon portable, `numba` déjà optionnel avec repli. Les points bloquants concernent surtout le **packaging** (PyInstaller/.spec/.iss actuels sont Windows/Linux uniquement) et un détail d'emplacement de fichier autosave qui deviendra un problème une fois l'app empaquetée en `.app` signé/lecture-seule.

---

## 🔴 Bloquant

### 1. Pas de spec PyInstaller ni de script de build pour macOS
**Fichiers : `BUILD.md`, absence de `LaserStudioPro.spec`, absence de `build_macos.sh`**
`BUILD.md` ne documente que Windows et Linux ; la commande PyInstaller utilisée (`--add-data "...;."` / `"...:."`) doit être adaptée. À traiter en Phase 3 (spec + script macOS), pas un bug de code mais bloque la production d'un `.app`/`.dmg`.

### 2. Pas de `requirements-macos.txt`
**Fichier : absent (seulement `requirements-windows.txt`, `requirements-linux.txt`)**
Aucun bloqueur de code, mais rien n'existe pour installer proprement sur Mac. `numpy<2`, `opencv-python`, `scikit-image`, `numba` doivent être vérifiés pour la disponibilité de wheels arm64 (numba en particulier n'a pas toujours de wheel dispo immédiatement pour les toutes dernières versions de Python — déjà anticipé dans le commentaire du fichier Windows, donc pas un problème nouveau). À traiter en Phase 2.

### 3. Icône `.ico`/`.png` non convertie en `.icns`
**Fichiers : `laser_studio_pro.ico`, `laser_studio_pro_512.png`**
`laser_studio_pro.ico` est en réalité un PNG 256×256 (renommé), et `laser_studio_pro_512.png` fait 1024×1024. Aucun `.icns` n'existe. `main.py:17-19` (`find_resource("laser_studio_pro.ico")` puis repli PNG) fonctionnera pour l'icône de fenêtre au runtime (Qt gère les PNG nativement), mais **l'icône du bundle `.app`** (Finder, Dock) nécessite un `.icns` généré via `iconutil` à partir d'un jeu d'images (16 à 1024 px) — à faire en Phase 3, à partir de `laser_studio_pro_512.png` (1024×1024, bonne résolution source).

---

## 🟠 Dégradé (fonctionne mais imparfait)

### 4. `get_app_dir()` suppose un exécutable à plat, incompatible avec la structure d'un bundle `.app`
**Fichier : `app_utils.py:8-15`**
```python
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
```
Dans un `.app` PyInstaller (`--windowed` sur macOS produit un vrai bundle, pas un exécutable nu), `sys.executable` pointe vers `MonApp.app/Contents/MacOS/LaserStudioPro`. `get_app_dir()` renverra donc `Contents/MacOS/`, un dossier **en lecture seule une fois l'app dans `/Applications` ou signée**. Cela affecte :
- **`project_io_mixin.py:208,216,226`** — le fichier autosave (`AUTOSAVE_FILENAME`) est écrit via `os.path.join(get_app_dir(), AUTOSAVE_FILENAME)`. Sur Windows/Linux (exécutable à plat, dossier utilisateur), ça marche. Sur macOS packagé, l'écriture échouera silencieusement selon l'emplacement d'installation (permission refusée dans `.app/Contents/MacOS`).
- `find_resource()` (`app_utils.py:27-39`) reste correcte pour la *lecture* des ressources embarquées (cherche aussi dans `get_bundle_dir()` = `_MEIPASS` équivalent macOS), donc l'icône/bannière chargeront bien.

**Recommandation Phase 2** : introduire un chemin d'écriture séparé (ex. `QStandardPaths.writableLocation(AppDataLocation)` ou `~/Library/Application Support/LaserStudioPro/`) pour l'autosave uniquement, sans toucher au comportement Windows/Linux existant (garder `get_app_dir()` en repli sur ces OS si c'est le comportement voulu, ou généraliser proprement — à valider avec toi avant modification puisque ça touche un mécanisme de sécurité de données utilisateur, pas la logique laser).

### 5. `os.startfile` absent — bon point, mais à vérifier s'il y a un "ouvrir le dossier export" ailleurs
Aucun usage trouvé (`grep os.startfile` → vide). Pas de bouton "ouvrir le dossier" identifié dans les mixins. Rien à corriger, noté pour mémoire.

---

## 🟡 Cosmétique / à surveiller, pas bloquant

### 6. Police par défaut "Arial" pour le texte vectoriel
**Fichier : `vector_layers.py:315,328`**
```python
def __init__(self, text="TEXTE", font_family="Arial", size_mm=10.0, ...):
    ...
    font = QFont(self.font_family)
```
Arial n'est pas installée nativement sur macOS récent (Apple fournit Helvetica/Helvetica Neue ; Arial est présent seulement si Office ou équivalent est installé). Qt fera un repli automatique vers une police similaire (pas de crash), mais le rendu visuel du texte gravé pourra légèrement différer entre Windows et macOS pour les projets existants qui utilisent "Arial" par défaut. Non bloquant, aucune action requise sauf si tu veux un rendu identique pixel-près.

### 7. Raccourcis clavier : déjà portables
**Fichier : `vector_layers.py:1008-1022`**
Utilise `QKeySequence.StandardKey.SelectAll/Undo/Copy/Paste` → Qt les traduit automatiquement en Cmd+A/Z/C/V sur macOS. Les mentions "Ctrl+X"/"Ctrl+Z" dans `i18n.py` (ex. lignes 663-666, 1571-1574, 1663-1666) sont du **texte affiché à l'utilisateur** (libellés de boutons/logs), pas des raccourcis Qt réels — ils resteront affichés "Ctrl+Z" même sur Mac où le raccourci réel serait Cmd+Z. Cosmétique, à corriger seulement si tu veux un affichage cohérent (nécessiterait une détection de plateforme dans `i18n.py`, hors scope "correction bloquante").

### 8. Pas de gestion explicite du DPI/Retina
Aucun `AA_EnableHighDpiScaling` ni équivalent trouvé — non nécessaire avec PyQt6 (le high-DPI est activé par défaut depuis Qt 6, contrairement à Qt 5). Rien à faire.

---

## ✅ Points déjà portables (vérifiés, aucune action requise)

- **Ports série** (`laser_control_mixin.py:10-14`) : `serial.tools.list_ports.comports()` sans filtre `COM*`, affichage générique `f"{p.device} - {p.description}"`. Sur macOS, `p.device` remontera nativement `/dev/cu.usbserial-*`, `/dev/cu.wchusbserial*` ou `/dev/cu.usbmodem*` (pyserial utilise déjà `cu`, pas `tty`, dans son énumération macOS). Aucune modification nécessaire.
- **`usb_controller.py`** : `serial.Serial(port, baudrate, timeout=1)` sans `exclusive=True` — comportement par défaut correct sur les trois OS. `time.sleep(2)` après connexion (reset DTR implicite du bootloader) est un délai générique compatible CH340/CP210x/FTDI, pas spécifique Windows. Pas de risque connu de verrouillage exclusif macOS avec pyserial récent.
- **Threads/Qt** (`workers.py`) : tous les workers héritent de `QThread` et communiquent via `pyqtSignal`, aucun accès direct à un widget depuis un thread non-GUI détecté. C'est justement le point le plus strict sur macOS (Qt/Cocoa exige que l'UI ne soit touchée que depuis le thread principal) — déjà respecté.
- **Config/paramètres** (`QSettings("LaserStudioPro", ...)` dans `project_io_mixin.py`, `machine_profiles_mixin.py`, `ui_setup_mixin.py`, `png2svg_widget.py`) : `QSettings` est nativement portable (stockage `~/Library/Preferences/` en `.plist` sur macOS). Aucune modification requise.
- **`numba`** (`workers.py:15-19`) déjà en `try/except ImportError` avec repli fonctionnel (`_HAS_NUMBA`) — comportement déjà pensé multiplateforme, cohérent avec la demande de ne pas l'inclure par défaut sur macOS.
- **Pas de chemins Windows en dur** (`\\`, `%APPDATA%`) trouvés dans le code Python (seul `BUILD.md` en mentionne, dans la doc de build Windows — normal).
- **`app_utils.get_bundle_dir()`** gère déjà `sys._MEIPASS` avec repli propre, compatible PyInstaller macOS (le mode `--onefile` sur Mac utilise aussi un dossier d'extraction temporaire analogue).

---

## Aucun sujet trouvé concernant

- Filtrage/tri de ports au format `COMx` numérique (aucun tri par numéro de port trouvé).
- Appels `os.startfile` ou équivalents Windows-only.
- Icône embarquée dans l'exécutable via ressource Windows native (`.ico` utilisé comme simple fichier image, pas comme ressource RC — donc pas de bloqueur de compilation).

---

## Prochaines étapes (attente feu vert avant Phase 2)

1. Point 4 (autosave path) est le seul changement de **comportement** proposé — à valider avec toi avant patch, car il touche à l'emplacement de sauvegarde des données utilisateur (pas la sécurité laser, mais je préfère confirmer avant de toucher `project_io_mixin.py`).
2. Les points 1-3 sont des ajouts (nouveaux fichiers `requirements-macos.txt`, `run_macos.sh`, section README, `.icns`, `.spec`, `build_macos.sh`) plutôt que des modifications de code existant — faible risque.
3. Rien dans cet audit ne touche à la logique de sécurité (arrêt d'urgence, feed hold, reset, alarmes) — aucun diff à te montrer sur ce sujet à ce stade.
