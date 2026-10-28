"""Tests unitaires du calcul d'altitude.

Lancer depuis la racine du projet :
    python -m pytest
"""

import numpy as np
import pandas as pd

from src.altitudes import (
    A_WGS84,
    E2_WGS84,
    altitude_geodesique,
    altitudes_kepler,
    date_du_fichier,
)


def point_wgs84(latitude_deg, altitude_km):
    """Position (x, 0, z) d'un point à une latitude et une altitude données (formule directe)."""
    lat = np.radians(latitude_deg)
    n = A_WGS84 / np.sqrt(1 - E2_WGS84 * np.sin(lat) ** 2)
    return ((n + altitude_km) * np.cos(lat), 0.0, (n * (1 - E2_WGS84) + altitude_km) * np.sin(lat))


def test_equateur():
    assert abs(altitude_geodesique((A_WGS84 + 400, 0, 0)) - 400) < 1e-6


def test_pole():
    assert abs(altitude_geodesique(point_wgs84(90, 400)) - 400) < 1e-6


def test_latitude_iss():
    # À 51,6° de latitude, la formule doit retrouver l'altitude de départ...
    assert abs(altitude_geodesique(point_wgs84(51.6, 420)) - 420) < 1e-6
    # ...alors qu'une sphère sous-estime l'altitude d'environ 13 km
    rayon = np.linalg.norm(point_wgs84(51.6, 420))
    assert 12 < 420 - (rayon - A_WGS84) < 14


def test_plusieurs_points_a_la_fois():
    points = np.array([point_wgs84(lat, 550) for lat in (-80, -30, 0, 45, 89)])
    assert np.allclose(altitude_geodesique(points), 550, atol=1e-6)


def test_kepler_iss():
    perigee, apogee = altitudes_kepler(15.48967427, 0.00067597)
    assert abs(perigee - 415.15) < 0.1
    assert abs(apogee - 424.34) < 0.1


def test_date_du_fichier():
    from pathlib import Path
    date = date_du_fichier(Path("data/raw/active_20261023T0858Z.json"))
    assert date == pd.Timestamp("2026-10-23 08:58", tz="UTC")
