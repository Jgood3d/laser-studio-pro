#!/bin/sh
cd "$(dirname "$0")"
python3 -m pip install -r requirements-linux.txt
python3 studio.py
