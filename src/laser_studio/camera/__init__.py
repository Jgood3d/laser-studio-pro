"""Caméra fixe (plafond / cadre) : capture, calibration optique et alignement
workspace pour superposer l'image du plateau dans le repère machine.

Modules :
- capture          ouverture d'une webcam, frames BGR
- lens_calibration correction de distorsion (damier ou AprilTag)
- workspace_alignment  homographie pixel → mm via AprilTags gravés
- storage          profils caméra (JSON par appareil)
- overlay          image corrigée + warpée prête pour l'aperçu 2D
"""
from laser_studio.camera.capture import list_cameras, open_camera, CameraCapture
from laser_studio.camera.lens_calibration import (
    LensCalibration,
    calibrate_lens_from_images,
    undistort,
)
from laser_studio.camera.workspace_alignment import (
    WorkspaceAlignment,
    AlignmentTarget,
    generate_apriltag_targets,
    detect_apriltags,
    detect_apriltag_corners,
    compute_alignment,
    merge_detections,
    compute_homography,
    pixel_to_mm,
    mm_to_pixel,
)
from laser_studio.camera.storage import CameraProfile, load_profile, save_profile, list_profiles

__all__ = [
    "list_cameras",
    "open_camera",
    "CameraCapture",
    "LensCalibration",
    "calibrate_lens_from_images",
    "undistort",
    "WorkspaceAlignment",
    "AlignmentTarget",
    "generate_apriltag_targets",
    "detect_apriltags",
    "detect_apriltag_corners",
    "compute_alignment",
    "merge_detections",
    "compute_homography",
    "pixel_to_mm",
    "mm_to_pixel",
    "CameraProfile",
    "load_profile",
    "save_profile",
    "list_profiles",
]
