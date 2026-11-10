"""Dialogue avec le graveur GRBL, sans interface graphique (pas de Qt).

- connection : connexion série au graveur (LaserUSBController) ;
- simulator : graveur GRBL simulé (SimulatedGrblSerial), pour tester
  l'application sans machine (variable LASER_STUDIO_SIMULATION).

Utilisation :

    from grbl.connection import LaserUSBController
    from grbl.simulator import SIMULATED_PORT, simulation_enabled
"""
