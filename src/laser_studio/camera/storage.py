"""Stockage des profils caméra (un fichier JSON par appareil).

Emplacement : <get_autosave_dir()>/cameras/<safe_id>.json
Le choix de la caméra active est mémorisé dans QSettings (clé camera/active_id).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from laser_studio.camera.lens_calibration import LensCalibration
from laser_studio.camera.workspace_alignment import WorkspaceAlignment
from laser_studio.core.paths import get_autosave_dir


def _cameras_dir() -> str:
    path = os.path.join(get_autosave_dir(), "cameras")
    os.makedirs(path, exist_ok=True)
    return path


def _safe_id(device_id: str) -> str:
    """Nom de fichier sûr à partir d'un identifiant d'appareil."""
    s = re.sub(r"[^\w.\-]+", "_", device_id.strip())[:80]
    return s or "camera"


@dataclass
class CameraProfile:
    """Tout ce qui est mémorisé pour une caméra donnée."""
    device_id: str                     # ex. "0" ou "Camera 0 (MSMF)"
    display_name: str = ""
    # Calibration optique (None = pas encore faite)
    lens: Optional[LensCalibration] = None
    # Alignement workspace (None = pas encore fait)
    alignment: Optional[WorkspaceAlignment] = None
    # Résolution préférée à l'ouverture (0 = défaut driver)
    preferred_width: int = 0
    preferred_height: int = 0
    # Métadonnées libres
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name or self.device_id,
            "lens": self.lens.to_dict() if self.lens else None,
            "alignment": self.alignment.to_dict() if self.alignment else None,
            "preferred_width": self.preferred_width,
            "preferred_height": self.preferred_height,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CameraProfile":
        lens = None
        if data.get("lens"):
            lens = LensCalibration.from_dict(data["lens"])
        alignment = None
        if data.get("alignment"):
            alignment = WorkspaceAlignment.from_dict(data["alignment"])
        return cls(
            device_id=str(data["device_id"]),
            display_name=str(data.get("display_name") or data["device_id"]),
            lens=lens,
            alignment=alignment,
            preferred_width=int(data.get("preferred_width") or 0),
            preferred_height=int(data.get("preferred_height") or 0),
            extra=dict(data.get("extra") or {}),
        )

    @property
    def is_ready(self) -> bool:
        """Prêt pour l'overlay : optique + alignement présents."""
        return self.lens is not None and self.alignment is not None


def profile_path(device_id: str) -> str:
    return os.path.join(_cameras_dir(), _safe_id(device_id) + ".json")


def load_profile(device_id: str) -> Optional[CameraProfile]:
    path = profile_path(device_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CameraProfile.from_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def save_profile(profile: CameraProfile) -> str:
    """Écrit le profil et renvoie le chemin du fichier."""
    path = profile_path(profile.device_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def list_profiles() -> List[CameraProfile]:
    """Tous les profils présents sur le disque."""
    result = []
    for name in sorted(os.listdir(_cameras_dir())):
        if not name.endswith(".json"):
            continue
        path = os.path.join(_cameras_dir(), name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result.append(CameraProfile.from_dict(data))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return result


def delete_profile(device_id: str) -> bool:
    path = profile_path(device_id)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False
