"""Catalogue des machines (resources/machines/*.yaml, voir son README) : graveurs GRBL courants avec ce que
leur constructeur publie (surface, taille du point, vitesse maximale, laser) et les sources. Sans Qt.

    models = load_machine_catalog(machine_catalog_roots())
    profile = models[0].profile_values()       # {"w": 400, "h": 400, "focal": 0.06, "max_speed": 18000}

Un champ absent n'est pas deviné : le profil créé garde alors la valeur affichée (ou celle par défaut).
"""
import os
from dataclasses import dataclass, field

import yaml

MACHINES_DIRNAME = "machines"


@dataclass
class MachineModel:
    brand: str
    model: str
    work_area_mm: tuple = None            # (largeur X, profondeur Y)
    spot_mm: tuple = None                 # taille du point (X, Y)
    max_speed_mm_min: dict = None         # {"x": …, "y": …}
    power_w: float = None
    wavelength_nm: float = None
    sources: list = field(default_factory=list)
    checked: str = ""
    notes: str = ""
    path: str = ""                        # fichier d'origine

    @property
    def title(self):
        return f"{self.brand} {self.model}"

    @property
    def focal(self):
        """Taille du point retenue pour le profil (mm) : moyenne de ses deux dimensions."""
        if not self.spot_mm:
            return None
        return round(sum(self.spot_mm) / len(self.spot_mm), 3)

    @property
    def max_speed(self):
        """Vitesse maximale retenue (mm/min) : celle de l'axe le plus lent, pour ne jamais la dépasser."""
        speeds = [v for v in (self.max_speed_mm_min or {}).values() if v]
        return float(min(speeds)) if speeds else None

    def profile_values(self):
        """Champs d'un profil machine (clés de MachineConfig.to_profile) publiés par le constructeur."""
        values = {}
        if self.work_area_mm:
            values["w"], values["h"] = float(self.work_area_mm[0]), float(self.work_area_mm[1])
        if self.focal:
            values["focal"] = self.focal
        if self.max_speed:
            values["max_speed"] = self.max_speed
        return values


def _pair(value):
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
        return (float(value[0]), float(value[1]))
    return None


def parse_machine_file(text, path=""):
    """Modèles d'un fichier de marque (YAML). Les modèles sans nom ou sans surface sont ignorés."""
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        return []
    brand = str(data.get("brand") or "").strip()
    models = []
    for entry in data.get("machines") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("model") or "").strip()
        area = _pair(entry.get("work_area_mm"))
        if not brand or not name or area is None:
            continue
        speeds = entry.get("max_speed_mm_min")
        speeds = {k: float(v) for k, v in speeds.items() if isinstance(v, (int, float))} \
            if isinstance(speeds, dict) else None
        laser = entry.get("laser") if isinstance(entry.get("laser"), dict) else {}
        sources = [str(s) for s in entry.get("sources") or [] if isinstance(s, str)]
        models.append(MachineModel(
            brand=brand, model=name, work_area_mm=area, spot_mm=_pair(entry.get("spot_mm")),
            max_speed_mm_min=speeds or None, power_w=laser.get("power_w"), wavelength_nm=laser.get("wavelength_nm"),
            sources=sources, checked=str(entry.get("checked") or ""), notes=str(entry.get("notes") or ""),
            path=path))
    return models


def load_machine_catalog(roots):
    """Modèles de tous les fichiers *.yaml des dossiers `roots`, triés par marque puis modèle. Un modèle
    de même marque et même nom dans un dossier suivant (celui de l'utilisateur) remplace le précédent.
    Un fichier illisible est ignoré."""
    by_title = {}
    for root in roots:
        try:
            names = sorted(os.listdir(root))
        except OSError:
            continue
        for name in names:
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8") as f:
                    models = parse_machine_file(f.read(), path)
            except (OSError, yaml.YAMLError):
                continue
            for model in models:
                by_title[model.title.casefold()] = model
    return sorted(by_title.values(), key=lambda m: (m.brand.casefold(), m.model.casefold()))


def machine_catalog_roots():
    """resources/machines/ (livré avec l'application), puis machines/ du dossier des données (modèles
    ajoutés par l'utilisateur, prioritaires)."""
    from laser_studio.core.paths import RESOURCES_DIRNAME, get_autosave_dir, resource_candidates
    roots = []
    for path in resource_candidates(MACHINES_DIRNAME):
        if os.path.basename(os.path.dirname(path)) == RESOURCES_DIRNAME and os.path.isdir(path):
            real = os.path.realpath(path)
            if real not in roots:
                roots.append(real)
    roots.append(os.path.join(get_autosave_dir(), MACHINES_DIRNAME))
    return roots
