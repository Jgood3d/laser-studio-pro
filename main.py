"""Lance Laser Studio Pro depuis le dépôt, sans installation : python main.py

Sert aussi de point d'entrée à PyInstaller. Le code est dans src/ (voir
pyproject.toml) ; une fois installé (pip install -e .), on peut aussi lancer
python -m laser_studio.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from laser_studio.main import main  # noqa: E402

if __name__ == "__main__":
    main()
