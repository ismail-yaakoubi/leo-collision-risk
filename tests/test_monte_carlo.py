"""Tests du modèle de risque (src/monte_carlo.py).

Lancer depuis la racine du projet :
    python -m pytest
"""

import numpy as np
import pandas as pd

from src.monte_carlo import R_TERRE_KM, probabilite_annuelle, simuler, volume_tranche


def test_volume_tranche():
    # Une coquille fine a pour volume environ 4 pi r² × épaisseur (r au milieu de la coquille)
    r = R_TERRE_KM + 525
    assert abs(volume_tranche(500) / (4 * np.pi * r**2 * 50) - 1) < 1e-3


def test_modele_cinetique():
    # Densité 1e-7 objet/km³, 10 km/s, cible et objet de 1 m : taux = rho × v × pi × (2 m)² × 1 an
    attendu = 1 - np.exp(-1e-7 * 10 * np.pi * 0.002**2 * 365.25 * 86400)
    assert abs(probabilite_annuelle(1e-7, 10, 1.0, 1.0) - attendu) < 1e-15


def test_probabilite_bornee():
    # Même avec une densité absurde, la probabilité ne dépasse jamais 1 ; densité nulle : risque nul
    assert probabilite_annuelle(1e3, 10, 1.0, 1.0) <= 1
    assert probabilite_annuelle(0.0, 10, 1.0, 1.0) == 0


def test_simulation_reproductible():
    # Même graine : exactement les mêmes tirages
    tableau = pd.DataFrame({"TRANCHE_KM": [500, 800], "Satellites actifs": [1000.0, 50.0],
                            "Débris suivis": [10.0, 400.0]})
    a, _ = simuler(tableau, n=100, graine=42)
    b, _ = simuler(tableau, n=100, graine=42)
    assert np.array_equal(a, b)
    assert a.shape == (100, 2)                  # une ligne par tirage, une colonne par tranche
