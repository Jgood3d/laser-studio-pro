"""Outils de la souris du canevas vectoriel (VectorCanvasView) : chacun garde son état et traite les
événements de son mode ; le canevas leur passe la main, dans l'ordre de priorité de ses gestionnaires
(mousePressEvent, mouseMoveEvent, mouseReleaseEvent, keyPressEvent).

- snapping.EndpointSnap : accroche aux extrémités et sommets des tracés, repère jaune ;
- drawing.DrawingTool : ligne, rectangle (3 points), cercle, ellipse, dimensions au clavier ;
- measure.MeasureTool : distance entre deux points, annotations ;
- node_edit.NodeEditor : sommets d'un tracé (déplacer, ajouter, supprimer) ;
- moving.MoveTool : déplacement groupé de la sélection (grille magnétique), panoramique.
"""
