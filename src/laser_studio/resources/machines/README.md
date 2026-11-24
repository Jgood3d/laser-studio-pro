# Catalogue des machines

Un fichier YAML par marque. Chaque modèle donne ce que **le constructeur publie** (fiche produit, manuel,
FAQ), avec ses sources et la date de vérification. Un champ absent veut dire « non publié » : on ne
devine pas. Les réglages GRBL d'usine (`$110`, `$120`…) ne sont pas dans le catalogue : les constructeurs
ne les publient pas, et ils se lisent sur la machine avec « Lire la config ».

Seulement des machines pilotables en GRBL (USB, compatible LaserGRBL / LightBurn mode GRBL).

```yaml
brand: Elegoo
machines:
  - model: Phecda 10W
    work_area_mm: [400, 400]          # largeur (X) × profondeur (Y)
    spot_mm: [0.06, 0.06]             # taille du point laser (X × Y)
    max_speed_mm_min: {x: 25000, y: 18000}
    laser: {power_w: 10, wavelength_nm: 455}
    sources: [https://…]
    checked: 2026-11-24
    notes: texte libre (variantes, précautions)
```

Ajouter une machine : un fichier dans ce dossier (ou dans `machines/` du dossier des données de
l'application, pour soi seulement), avec au moins `model`, `work_area_mm` et une source.
