#!/bin/bash
# Compile Laser Studio Pro en .app puis en .dmg sur macOS.
# Cible l'architecture de LA MACHINE qui exécute ce script (pas de
# cross-compilation, pas d'universal2 — voir LaserStudioPro.spec).
set -e

cd "$(dirname "$0")"

APP_NAME="LaserStudioPro"
VERSION="1.6.0"
ARCH="$(uname -m)"
DMG_NAME="${APP_NAME}_${VERSION}_macos_${ARCH}.dmg"

echo "=== Laser Studio Pro — build macOS (${ARCH}) ==="

# 1. Environnement de build propre et isolé (séparé du venv de développement
#    run_macos.sh, pour ne pas embarquer d'éventuels paquets de dev en trop).
PYTHON_BIN="python3"
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
fi

if [ -d "build_venv" ]; then
    echo "Suppression de l'ancien environnement de build..."
    rm -rf build_venv
fi
echo "Création de l'environnement de build (${PYTHON_BIN})..."
"$PYTHON_BIN" -m venv build_venv
source build_venv/bin/activate

echo "Installation des dépendances..."
pip install --upgrade pip -q
pip install -r requirements-macos.txt -q
pip install pyinstaller -q

# 2. Génération de l'icône .icns si absente ou si la source a changé.
if [ ! -f "laser_studio_pro.icns" ] || [ "laser_studio_pro_512.png" -nt "laser_studio_pro.icns" ]; then
    echo "Génération de l'icône .icns..."
    ICONSET_DIR="$(mktemp -d)/laser_studio_pro.iconset"
    mkdir -p "$ICONSET_DIR"
    for size in 16 32 64 128 256 512; do
        sips -z "$size" "$size" laser_studio_pro_512.png --out "${ICONSET_DIR}/icon_${size}x${size}.png" >/dev/null
        double=$((size * 2))
        sips -z "$double" "$double" laser_studio_pro_512.png --out "${ICONSET_DIR}/icon_${size}x${size}@2x.png" >/dev/null
    done
    sips -z 1024 1024 laser_studio_pro_512.png --out "${ICONSET_DIR}/icon_512x512@2x.png" >/dev/null
    iconutil -c icns "$ICONSET_DIR" -o laser_studio_pro.icns
    rm -rf "$(dirname "$ICONSET_DIR")"
fi

# 3. Nettoyage des builds précédents.
echo "Nettoyage des builds précédents..."
rm -rf build dist

# 4. Compilation.
echo "Compilation avec PyInstaller..."
pyinstaller --noconfirm LaserStudioPro.spec

if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "ERREUR : dist/${APP_NAME}.app n'a pas été généré."
    exit 1
fi

# 5. Création du .dmg.
echo "Création du .dmg..."
rm -f "dist/${DMG_NAME}"
if command -v create-dmg >/dev/null 2>&1; then
    create-dmg \
        --volname "${APP_NAME}" \
        --app-drop-link 600 185 \
        --icon "${APP_NAME}.app" 200 185 \
        --window-size 800 400 \
        "dist/${DMG_NAME}" \
        "dist/${APP_NAME}.app" || true
fi
if [ ! -f "dist/${DMG_NAME}" ]; then
    # Repli sans create-dmg (non installé) : hdiutil suffit pour un .dmg
    # simple, sans mise en page personnalisée du Finder.
    hdiutil create -volname "${APP_NAME}" -srcfolder "dist/${APP_NAME}.app" \
        -ov -format UDZO "dist/${DMG_NAME}"
fi

echo ""
echo "=== Terminé ==="
echo "App    : dist/${APP_NAME}.app"
echo "DMG    : dist/${DMG_NAME}"
echo ""
echo "L'app n'est pas signée. Pour l'ouvrir malgré Gatekeeper :"
echo "  - clic droit sur l'app > Ouvrir (une seule fois), ou"
echo "  - xattr -dr com.apple.quarantine \"dist/${APP_NAME}.app\""
