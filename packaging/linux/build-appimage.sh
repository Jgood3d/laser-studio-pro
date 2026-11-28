#!/usr/bin/env bash
# Emballe Laser Studio Pro en AppImage, à partir du dossier PyInstaller.
#
# Utilisation, depuis n'importe quel dossier :
#   packaging/linux/build-linux.sh --onedir     # 1. dossier dist/LaserStudioPro/
#   packaging/linux/build-appimage.sh [VERSION] # 2. dist/LaserStudioPro-VERSION-x86_64.AppImage
#
# VERSION : par défaut, APP_VERSION de src/laser_studio/core/version.py.
#
# Pourquoi une AppImage plutôt que l'exécutable unique (--onefile) : un seul
# fichier aussi, mais rien n'est décompressé dans /tmp à chaque lancement
# (démarrage bien plus rapide pour ~400 Mo), et l'icône et l'entrée de menu
# sont fournies (packaging/linux/$APP_ID.desktop).
#
# appimagetool est téléchargé dans build/ s'il n'est pas fourni par la
# variable APPIMAGETOOL. Il tourne sans FUSE (APPIMAGE_EXTRACT_AND_RUN),
# comme sur les machines de GitHub Actions.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' src/laser_studio/core/version.py)}"
ARCH="x86_64"
APP="LaserStudioPro"
APP_ID="io.github.jgood3d.LaserStudioPro"     # = APP_ID de src/laser_studio/core/version.py
DESKTOP="packaging/linux/$APP_ID.desktop"
DIST="dist/$APP"
APPDIR="build/AppDir"
OUTPUT="dist/$APP-$VERSION-$ARCH.AppImage"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"

if [ ! -x "$DIST/$APP" ]; then
    echo "$DIST/$APP introuvable : lance d'abord packaging/linux/build-linux.sh --onedir" >&2
    exit 1
fi

# Bibliothèques xcb dont a besoin le module d'affichage X11 de Qt (libqxcb).
# PyInstaller les embarque seulement si elles sont installées sur la machine
# de compilation : sans elles, l'AppImage ne démarre pas chez un utilisateur
# qui ne les a pas. Sous Debian / Ubuntu :
#   sudo apt install libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
#     libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
#     libxcb-xkb1 libxkbcommon-x11-0
missing=""
for lib in libxcb-cursor.so.0 libxcb-icccm.so.4 libxcb-image.so.0 \
        libxcb-keysyms.so.1 libxcb-randr.so.0 libxcb-render-util.so.0 \
        libxcb-shape.so.0 libxcb-xkb.so.1 libxkbcommon-x11.so.0; do
    if [ -z "$(find "$DIST" -name "$lib" -print -quit)" ]; then
        missing="$missing $lib"
    fi
done
if [ -n "$missing" ]; then
    echo "Bibliothèques xcb absentes de $DIST :$missing" >&2
    echo "Installe-les (voir le commentaire de ce script) puis recompile avec build-linux.sh." >&2
    exit 1
fi

echo "=========================================="
echo "AppDir..."
echo "=========================================="
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/metainfo" \
    "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -a "$DIST/." "$APPDIR/usr/bin/"

ICON="src/laser_studio/resources/laser_studio_pro_512.png"
cp "$ICON" "$APPDIR/$APP_ID.png"
cp "$ICON" "$APPDIR/usr/share/icons/hicolor/512x512/apps/$APP_ID.png"

# Fichier .desktop commun aux paquets Linux ; ici, Exec lance l'exécutable
# PyInstaller au lieu de la commande installée par pip (laser-studio-pro).
sed "s/^Exec=laser-studio-pro/Exec=$APP/" "$DESKTOP" > "$APPDIR/$APP_ID.desktop"
cp "$APPDIR/$APP_ID.desktop" "$APPDIR/usr/share/applications/"
# Fiche AppStream (description, captures, versions) pour les logithèques.
cp "packaging/linux/$APP_ID.metainfo.xml" "$APPDIR/usr/share/metainfo/"

cat > "$APPDIR/AppRun" <<EOF
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
exec "\$HERE/usr/bin/$APP" "\$@"
EOF
chmod +x "$APPDIR/AppRun"

echo "=========================================="
echo "appimagetool..."
echo "=========================================="
TOOL="${APPIMAGETOOL:-build/appimagetool-$ARCH.AppImage}"
if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" "$TOOL_URL"
    chmod +x "$TOOL"
fi
rm -f "$OUTPUT"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$TOOL" --no-appstream "$APPDIR" "$OUTPUT"

echo "=========================================="
echo "Terminé ! $OUTPUT est prêt ($(du -h "$OUTPUT" | cut -f1))."
echo "=========================================="
