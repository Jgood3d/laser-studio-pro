# -*- coding: utf-8 -*-
"""Ancien emplacement de l'éditeur vectoriel, gardé pour le code existant.

Tout ce qui s'importait d'ici s'importe toujours d'ici, mais le code vit
maintenant dans des modules séparés :

- models/vector_objects.py : objets du dessin (VectorObject, TextObject,
  ShapeObject, SvgPathObject) ;
- vector/svg_extract.py : import SVG classique (extract_svg_objects) ;
- vector/layer_data.py : objets -> polygones par calque pour le G-Code
  (extract_vector_layer_data) ;
- ui/vector_editor/ : canevas (VectorCanvasView), élément graphique
  (VectorGraphicsItem) et boîtes de saisie (texte, médaille, forme, calque) ;
- ui/tabs/layers/layer_table.py : tableau des calques (LayerManagerWidget) ;
- models/layers.py : modèle des calques (LayersModel ; LayerManager est son
  ancien nom).

Pour du code neuf, importer directement depuis ces modules.
"""
from laser_studio.models.layers import (  # noqa: F401
    BASE_LAYER_DEFAULTS, BASE_LAYER_ROLES, CONTOUR_MODES, DEFAULT_LAYER_COLORS, ENGRAVE_MODE,
    LAYER_LASER_CMDS, LAYER_MODE_TR_KEYS, LAYER_MODES, LaserLayer, LayersModel, base_layer_name, layer_label,
    layer_laser_cmd, layer_overscan_enabled,
)
from laser_studio.models.vector_objects import VectorObject, TextObject, ShapeObject, SvgPathObject  # noqa: F401
from laser_studio.vector.svg_extract import (  # noqa: F401
    _merge_path_objects, _qpainterpath_to_subpaths, _svg_path_element_to_single, _svg_path_element_to_subpaths,
    extract_svg_objects,
)
from laser_studio.vector.layer_data import (  # noqa: F401
    MAX_POLYGONS_FOR_PATH_OPTIMIZATION, _optimize_polygon_order, extract_vector_layer_data,
)
from laser_studio.ui.tabs.layers.layer_table import LayerManagerWidget  # noqa: F401
from laser_studio.ui.vector_editor.item import VectorGraphicsItem  # noqa: F401
from laser_studio.ui.vector_editor.canvas import VectorCanvasView  # noqa: F401
from laser_studio.ui.vector_editor.text_dialog import TextInsertDialog  # noqa: F401
from laser_studio.ui.vector_editor.medal_dialog import MedalTextDialog  # noqa: F401
from laser_studio.ui.vector_editor.assign_layer_dialog import AssignLayerDialog  # noqa: F401
from laser_studio.ui.vector_editor.shape_dialog import ShapeInsertDialog  # noqa: F401

LayerManager = LayersModel
