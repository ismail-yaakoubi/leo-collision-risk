"""Tests du calcul des objets équivalents (src/comparaison.py).

Lancer depuis la racine du projet :
    python -m pytest
"""

import numpy as np

from src.comparaison import categorie, objets_equivalents

BORDS = np.arange(0, 2050, 50)          # tranches de 50 km, de 0 à 2000 km


def test_categories():
    assert categorie("active") == "Satellites actifs"
    assert categorie("fengyun-1c-debris") == "Débris suivis"
    assert categorie("visual") is None          # sélection d'objets brillants, ignorée


def test_un_objet_circulaire_compte_pour_un():
    # 60 échantillons tous dans la même tranche : l'objet vaut 1 dans cette tranche
    resultat = objets_equivalents(np.full(60, 525.0), 60, BORDS)
    assert resultat.sum() == 1
    assert resultat[10] == 1                    # tranche 500–550 km


def test_un_objet_elliptique_est_reparti():
    # moitié du temps vers 420 km, moitié vers 780 km : 0,5 dans chaque tranche
    altitudes = np.concatenate([np.full(30, 420.0), np.full(30, 780.0)])
    resultat = objets_equivalents(altitudes, 60, BORDS)
    assert resultat[8] == 0.5 and resultat[15] == 0.5
    assert resultat.sum() == 1                  # un objet reste un objet
