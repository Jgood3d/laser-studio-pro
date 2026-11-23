#!/bin/bash
# Paquet Debian (.deb) de Laser Studio Pro, avec les bibliothèques Python de Debian.
#
#   packaging/debian/build-deb.sh [--image IMAGE] [--test [--test-image IMAGE]] [--no-build]
#
# Construit dist/deb/laser-studio-pro_<version>_all.deb. Sur une machine Debian ou Ubuntu qui a
# dpkg-buildpackage, la construction se fait sur place (dépendances de construction déjà installées) ;
# ailleurs, dans un conteneur IMAGE (podman, sinon docker ; debian:trixie par défaut).
# --test : installe ensuite le paquet dans un conteneur propre (--test-image, IMAGE par défaut) et y
# lance les tests de l'application contre le paquet installé. --no-build : teste le paquet déjà construit.
#
# Version : celle de src/laser_studio/core/version.py. Hors d'un tag v<version>, une version de
# développement <version>~git<AAAAMMJJ>.<nombre de commits>.<commit>, qui se classe avant la version
# publiée et dans l'ordre des commits.
set -euo pipefail

TOP=$(cd "$(dirname "$0")/../.." && pwd)
OUT="$TOP/dist/deb"
IMAGE=docker.io/library/debian:trixie
TEST_IMAGE=
TEST=0
INSIDE=0
BUILD=1
while [ $# -gt 0 ]; do
    case "$1" in
        --image) IMAGE=$2; shift 2 ;;
        --test) TEST=1; shift ;;
        --test-image) TEST_IMAGE=$2; shift 2 ;;
        --no-build) BUILD=0; shift ;;
        --inside) INSIDE=1; shift ;;          # appel interne, dans le conteneur
        *) echo "option inconnue : $1" >&2; exit 2 ;;
    esac
done
TEST_IMAGE=${TEST_IMAGE:-$IMAGE}

engine() {
    if command -v podman >/dev/null; then echo podman
    elif command -v docker >/dev/null; then echo docker
    else echo "Ni podman ni docker : installez l'un des deux, ou lancez ce script sur Debian / Ubuntu." >&2; exit 1
    fi
}

deb_version() {
    local version git_version
    version=$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' "$TOP/src/laser_studio/core/version.py")
    if git -C "$TOP" rev-parse --git-dir >/dev/null 2>&1 \
            && [ "$(git -C "$TOP" describe --tags --exact-match 2>/dev/null)" != "v$version" ]; then
        git_version="~git$(git -C "$TOP" log -1 --format=%cd --date=format:%Y%m%d)"
        git_version="$git_version.$(git -C "$TOP" rev-list --count HEAD).$(git -C "$TOP" rev-parse --short=7 HEAD)"
        if [ -n "$(git -C "$TOP" status --porcelain --untracked-files=no)" ]; then
            git_version="$git_version.modifie"      # arbre de travail modifié : version jamais publiée
        fi
        version="$version$git_version"
    fi
    echo "$version"
}

build_here() {
    local version=$1 work src
    work=$(mktemp -d)
    src="$work/laser-studio-pro-$version"
    mkdir -p "$src"
    # Fichiers suivis et nouveaux fichiers non ignorés (pas .venv, dist/, caches).
    (cd "$TOP" && { git ls-files -co --exclude-standard 2>/dev/null || find . -path ./.git -prune -o -type f -print; } \
        | grep -v '^packaging/debian/debian/' | tar -cf - -T -) | tar -xf - -C "$src"
    cp -r "$TOP/packaging/debian/debian" "$src/debian"
    # Modèle de détourage de Stencil Studio : téléchargé au premier usage dans le profil de l'utilisateur
    # (le dossier installé n'est pas modifiable), comme dans le paquet Fedora.
    rm -f "$src/src/stencil_studio/resources/models/u2netp.onnx"
    cat > "$src/debian/changelog" <<EOF
laser-studio-pro ($version) unstable; urgency=medium

  * Paquet construit depuis le dépôt (packaging/debian/build-deb.sh).

 -- $(sed -n 's/^Maintainer: //p' "$src/debian/control")  $(date -R)
EOF
    (cd "$src" && dpkg-buildpackage -us -uc -b)
    mkdir -p "$OUT"
    cp "$work"/laser-studio-pro_"$version"_all.deb "$OUT"/
    rm -rf "$work"
    echo "Paquet : $OUT/laser-studio-pro_${version}_all.deb"
}

BUILD_DEPS="build-essential debhelper dh-python pybuild-plugin-pyproject python3-all python3-setuptools \
desktop-file-utils appstream git"

version=${DEB_VERSION:-$(deb_version)}

if [ "$BUILD" = 0 ]; then
    :
elif [ "$INSIDE" = 1 ] || command -v dpkg-buildpackage >/dev/null; then
    build_here "$version"
else
    "$(engine)" run --rm -e DEB_VERSION="$version" -v "$TOP":/src:Z -w /src "$IMAGE" bash -c "
        set -e
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq && apt-get install -y -qq --no-install-recommends $BUILD_DEPS >/dev/null
        git config --global --add safe.directory /src
        packaging/debian/build-deb.sh --inside"
fi

if [ "$TEST" = 1 ]; then
    deb="dist/deb/laser-studio-pro_${version}_all.deb"
    # 1. Le paquet installe ses dépendances Debian et l'application démarre (utilisateur normal : le moteur
    #    web de Stencil Studio refuse root). Toujours ouverte au bout de 25 s = démarrage réussi.
    # 2. La suite de tests du dépôt, avec ces versions Debian des bibliothèques (PyQt6, numpy, OpenCV…).
    "$(engine)" run --rm -v "$TOP":/src:ro,Z "$TEST_IMAGE" bash -c "
        set -e
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq && apt-get install -y -qq /src/$deb fonts-dejavu-core >/dev/null
        useradd -m essai && cp -r /src /home/essai/depot && chown -R essai /home/essai/depot
        su essai -c 'cd /tmp && QT_QPA_PLATFORM=offscreen NOWARNING=1 timeout 25 laser-studio-pro >/tmp/lancement.log 2>&1' \
            && code=0 || code=\$?
        if [ \$code -eq 124 ]; then echo 'Lancement : OK (toujours ouverte après 25 s)'
        else echo \"Lancement : ÉCHEC (code \$code)\"; tail -20 /tmp/lancement.log; exit 1; fi
        su essai -c 'cd /home/essai/depot && rm -rf .venv && QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests 2>&1 | tail -4'"
fi
