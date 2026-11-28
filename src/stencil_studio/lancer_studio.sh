#!/bin/sh
# Stencil Studio seul, dans le navigateur : lancé depuis le dossier qui contient stencil_studio/.
cd "$(dirname "$0")/.."
python3 -m pip install -r stencil_studio/requirements-linux.txt
python3 -m stencil_studio
