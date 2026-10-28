"""Calcule l'altitude WGS84 de tous les objets téléchargés, avec SGP4."""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec, jday

MU = 398600.4418                   # constante gravitationnelle de la Terre (km³/s²)
A_WGS84 = 6378.137                 # rayon équatorial (km)
F_WGS84 = 1 / 298.257223563        # aplatissement
E2_WGS84 = F_WGS84 * (2 - F_WGS84) # excentricité au carré de l'ellipsoïde
DOSSIER_RAW = Path("data/raw")
DOSSIER_PROCESSED = Path("data/processed")
N_POINTS = 60                      # instants par révolution

# Codes d'erreur renvoyés par SGP4 (le code 5 n'est plus utilisé)
CODES_ERREUR_SGP4 = {
    1: "excentricité moyenne hors de [0, 1[",
    2: "mouvement moyen négatif",
    3: "excentricité perturbée hors de [0, 1]",
    4: "demi-latus rectum négatif",
    6: "objet rentré dans l'atmosphère",
}


def altitude_geodesique(positions):
    """Altitude (km) au-dessus de l'ellipsoïde WGS84.

    `positions` : une position (x, y, z) en km, ou un tableau de plusieurs positions
    de forme (n, 3). Renvoie une altitude, ou un tableau de n altitudes.
    """
    positions = np.array(positions, dtype=float)
    x, y, z = positions[..., 0], positions[..., 1], positions[..., 2]
    p = np.hypot(x, y)                         # distance à l'axe des pôles
    lat = np.arctan2(z, p * (1 - E2_WGS84))    # première estimation de la latitude
    for _ in range(5):                         # quelques itérations suffisent
        sin_lat = np.sin(lat)
        n = A_WGS84 / np.sqrt(1 - E2_WGS84 * sin_lat**2)
        h = p * np.cos(lat) + z * sin_lat - A_WGS84 * np.sqrt(1 - E2_WGS84 * sin_lat**2)
        lat = np.arctan2(z, p * (1 - E2_WGS84 * n / (n + h)))
    sin_lat = np.sin(lat)
    return p * np.cos(lat) + z * sin_lat - A_WGS84 * np.sqrt(1 - E2_WGS84 * sin_lat**2)


def altitudes_kepler(mean_motion, eccentricity):
    """Périgée et apogée (km) par la loi de Kepler, au-dessus d'une sphère de rayon A_WGS84.

    Accepte un nombre ou une colonne entière (tableau numpy, colonne pandas).
    """
    n = np.asarray(mean_motion) * 2 * np.pi / 86400     # tours/jour -> rad/s
    a = (MU / n**2) ** (1 / 3)                          # demi-grand axe (km)
    e = np.asarray(eccentricity)
    return a * (1 - e) - A_WGS84, a * (1 + e) - A_WGS84


def groupes_disponibles():
    """Liste les groupes pour lesquels au moins un fichier a été téléchargé."""
    groupes = set()
    for chemin in DOSSIER_RAW.glob("*_*.json"):
        trouve = re.match(r"(.+)_\d{8}T\d{4}Z\.json$", chemin.name)
        if trouve:
            groupes.add(trouve.group(1))
    return sorted(groupes)


def date_du_fichier(chemin):
    """Renvoie la date du fichier CelesTrak, à partir de son nom."""
    nom = Path(chemin).name
    resultat = re.search(r"_(\d{8}T\d{4}Z)\.json$", nom)
    if resultat is None:
        raise ValueError(f"Nom de fichier n'a pas le format attendu : {nom}")
    return pd.to_datetime(resultat.group(1), format="%Y%m%dT%H%MZ", utc=True)


def dernier_fichier(groupe):
    """Renvoie le dernier fichier CelesTrak du groupe."""
    fichiers = sorted(DOSSIER_RAW.glob(f"{groupe}_*.json"))
    if not fichiers:
        raise FileNotFoundError(
            f"Aucun fichier '{groupe}_*.json' dans {DOSSIER_RAW} : lancer d'abord src/fetch_data.py."
        )
    return fichiers[-1]


def propager(objet, date_ref, n_points=N_POINTS):
    """Propage un objet sur une révolution à partir de date_ref.

    Renvoie (code_erreur, positions) : 0 et un tableau (n_points, 3) en km si tout va bien,
    sinon le code de la première erreur SGP4 et None.
    """
    # 1. Créer le satellite et le remplir avec l'objet
    sat = Satrec()
    omm.initialize(sat, objet)

    # 2. Les n_points décalages, en jours, sur un tour (sans compter deux fois le départ)
    periode_min = 1440 / objet["MEAN_MOTION"]
    decalages_jours = np.linspace(0, periode_min, n_points, endpoint=False) / 1440

    # 3. Les n_points dates : le jour reste fixe, seule la fraction de jour avance
    jd0, fr0 = jday(date_ref.year, date_ref.month, date_ref.day,
                    date_ref.hour, date_ref.minute, date_ref.second + date_ref.microsecond / 1e6)
    jd = np.full(n_points, jd0)
    fr = fr0 + decalages_jours

    # 4. Les n_points propagations en un seul appel ; une seule erreur suffit à exclure l'objet
    erreurs, positions, _vitesses = sat.sgp4_array(jd, fr)
    if np.any(erreurs != 0):
        return int(erreurs[erreurs != 0][0]), None
    return 0, positions


def calculer(objets, date_ref, n_points=N_POINTS):
    """Calcule le résumé par objet et les échantillons d'altitude.

    Renvoie deux tableaux :
    - resume : une ligne par objet (identité, orbite, code d'erreur, altitudes min/moy/max) ;
    - echantillons : une ligne par position propagée (NORAD_CAT_ID, ALT_KM).
    """
    lignes = []
    echantillons = []

    for objet in objets:
        code, positions = propager(objet, date_ref, n_points)
        ligne = {
            "NORAD_CAT_ID": objet["NORAD_CAT_ID"],
            "OBJECT_NAME": objet["OBJECT_NAME"],
            "OBJECT_ID": objet.get("OBJECT_ID"),
            "EPOCH": objet["EPOCH"],
            "MEAN_MOTION": objet["MEAN_MOTION"],
            "ECCENTRICITY": objet["ECCENTRICITY"],
            "INCLINATION": objet["INCLINATION"],
            "CODE_ERREUR_SGP4": code,
            "MOTIF_EXCLUSION": CODES_ERREUR_SGP4.get(code, f"code {code}") if code else None,
        }
        if code == 0:
            alt = altitude_geodesique(positions)
            alt_sphere = np.linalg.norm(positions, axis=1) - A_WGS84   # pour la validation
            ligne.update({
                "ALT_MIN_KM": alt.min(),
                "ALT_MOY_KM": alt.mean(),
                "ALT_MAX_KM": alt.max(),
                "ALT_MIN_SPHERE_KM": alt_sphere.min(),
                "ALT_MOY_SPHERE_KM": alt_sphere.mean(),
                "ALT_MAX_SPHERE_KM": alt_sphere.max(),
            })
            echantillons.append(pd.DataFrame({"NORAD_CAT_ID": objet["NORAD_CAT_ID"], "ALT_KM": alt}))
        lignes.append(ligne)

    resume = pd.DataFrame(lignes)
    resume["EPOCH"] = pd.to_datetime(resume["EPOCH"], utc=True)
    resume["AGE_EPOCH_JOURS"] = (date_ref - resume["EPOCH"]).dt.total_seconds() / 86400
    perigee, apogee = altitudes_kepler(resume["MEAN_MOTION"], resume["ECCENTRICITY"])
    resume["PERIGEE_KEPLER_KM"] = perigee
    resume["APOGEE_KEPLER_KM"] = apogee
    # Moyenne dans le temps de la distance au centre sur une orbite de Kepler : a(1 + e²/2).
    # Ce n'est pas a : un objet sur une orbite elliptique passe plus de temps près de l'apogée.
    demi_grand_axe = (perigee + apogee) / 2 + A_WGS84
    resume["ALT_MOY_KEPLER_KM"] = demi_grand_axe * (1 + resume["ECCENTRICITY"] ** 2 / 2) - A_WGS84
    resume["EST_LEO"] = resume["MEAN_MOTION"] > 11.25    # période < 128 min

    echantillons = (pd.concat(echantillons, ignore_index=True) if echantillons
                    else pd.DataFrame(columns=["NORAD_CAT_ID", "ALT_KM"]))
    return resume, echantillons


def afficher_bilan(resume, date_ref, chemin):
    """Affiche les chiffres clés et la validation par Kepler."""
    exclus = resume[resume["CODE_ERREUR_SGP4"] != 0]
    valides = resume[resume["CODE_ERREUR_SGP4"] == 0]
    leo = valides[valides["EST_LEO"]]

    print(f"Fichier          : {chemin}")
    print(f"Date de référence: {date_ref:%Y-%m-%d %H:%M} UTC")
    print(f"Objets           : {len(resume)} ({len(valides)} propagés, {len(exclus)} exclus)")
    for motif, nombre in exclus["MOTIF_EXCLUSION"].value_counts().items():
        print(f"  exclus : {nombre} × {motif}")
    print(f"Objets en LEO    : {len(leo)}")

    if len(leo):
        # Validation : sur une même sphère, l'altitude moyenne SGP4 sur une révolution doit être
        # proche de l'altitude moyenne de Kepler (moyenne dans le temps). On compare des
        # moyennes : le minimum SGP4 descend sous le périgée de Kepler à cause des oscillations
        # courtes dues à J2, que les éléments moyens ne voient pas.
        ecart = leo["ALT_MOY_SPHERE_KM"] - leo["ALT_MOY_KEPLER_KM"]
        print(f"Écart SGP4 - Kepler (altitude moyenne, sphère) en LEO : moyen {ecart.mean():+.1f} km, "
              f"95 % des objets entre {ecart.quantile(0.025):+.1f} et {ecart.quantile(0.975):+.1f} km, "
              f"maximum en valeur absolue {ecart.abs().max():.1f} km")


def main(groupe):
    chemin = dernier_fichier(groupe)
    date_ref = date_du_fichier(chemin)
    objets = json.loads(chemin.read_text(encoding="utf-8"))

    resume, echantillons = calculer(objets, date_ref)

    DOSSIER_PROCESSED.mkdir(parents=True, exist_ok=True)
    suffixe = chemin.stem                       # par exemple active_20261024T1930Z
    resume.to_csv(DOSSIER_PROCESSED / f"altitudes_{suffixe}.csv", index=False)
    echantillons.to_csv(DOSSIER_PROCESSED / f"echantillons_{suffixe}.csv", index=False)

    afficher_bilan(resume, date_ref, chemin)
    print(f"Résultats enregistrés dans {DOSSIER_PROCESSED}/ (altitudes_{suffixe}.csv, "
          f"echantillons_{suffixe}.csv)")


if __name__ == "__main__":
    groupes = sys.argv[1:] or groupes_disponibles()   # sys.argv[1:] : les groupes tapés après le script
    for i, groupe in enumerate(groupes):
        if i:
            print()
        main(groupe)
