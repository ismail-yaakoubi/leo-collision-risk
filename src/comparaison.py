"""Compare l'encombrement par altitude des satellites actifs et des débris suivis.

Lit les derniers résultats de src/altitudes.py pour chaque groupe, classe les groupes en
« satellites actifs » (groupe active) et « débris suivis » (groupes *-debris), puis calcule,
par tranche de 50 km, les objets équivalents de chaque catégorie (décision D3) et la part
des débris. Le tableau est enregistré dans data/processed/comparaison_debris.csv.

Utilisation, depuis la racine du projet (après src/fetch_data.py et src/altitudes.py) :
    python src/comparaison.py
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

DOSSIER_PROCESSED = Path("data/processed")
LARGEUR_TRANCHE_KM = 50
ALTITUDE_MAX_KM = 2000
SEUIL_TRANCHE = 50      # objets équivalents minimum pour calculer une part (évite les 100 % sur 1 objet)


def categorie(groupe):
    """Classe un groupe CelesTrak : satellites actifs, débris suivis, ou ignoré (None)."""
    if groupe == "active":
        return "Satellites actifs"
    if groupe.endswith("-debris"):
        return "Débris suivis"
    return None


def derniers_resultats():
    """Pour chaque groupe, le dernier fichier d'échantillons produit par src/altitudes.py."""
    derniers = {}
    for chemin in sorted(DOSSIER_PROCESSED.glob("echantillons_*.csv")):
        trouve = re.match(r"echantillons_(.+)_(\d{8}T\d{4}Z)\.csv$", chemin.name)
        if trouve:
            derniers[trouve.group(1)] = chemin      # trié par nom : le dernier écrase les anciens
    return derniers


def objets_equivalents(altitudes_km, n_points, bords):
    """Objets équivalents par tranche : chaque échantillon vaut 1/n_points d'objet (décision D3)."""
    comptes, _ = np.histogram(altitudes_km, bins=bords)
    return comptes / n_points


def construire_tableau():
    """Tableau par tranche : objets équivalents actifs, débris, total et part des débris."""
    bords = np.arange(0, ALTITUDE_MAX_KM + LARGEUR_TRANCHE_KM, LARGEUR_TRANCHE_KM)
    tableau = pd.DataFrame({"TRANCHE_KM": bords[:-1]})
    deja_vus = set()
    bilan = []

    # Les satellites actifs d'abord : si un objet apparaît dans deux groupes, on ne le compte qu'une fois
    groupes = sorted(derniers_resultats().items(), key=lambda item: item[0] != "active")
    for groupe, chemin in groupes:
        cat = categorie(groupe)
        if cat is None:
            continue
        echantillons = pd.read_csv(chemin)
        doublons = echantillons["NORAD_CAT_ID"].isin(deja_vus)
        echantillons = echantillons[~doublons]
        ids = set(echantillons["NORAD_CAT_ID"])
        deja_vus |= ids
        if echantillons.empty:
            continue
        n_points = echantillons.groupby("NORAD_CAT_ID").size().iloc[0]
        valeurs = objets_equivalents(echantillons["ALT_KM"], n_points, bords)
        tableau[cat] = tableau.get(cat, 0) + valeurs
        bilan.append((groupe, cat, len(ids), chemin.name))

    for cat in ("Satellites actifs", "Débris suivis"):
        if cat not in tableau:
            tableau[cat] = 0.0
    tableau["TOTAL"] = tableau["Satellites actifs"] + tableau["Débris suivis"]
    tableau["PART_DEBRIS"] = np.where(tableau["TOTAL"] >= SEUIL_TRANCHE,
                                      tableau["Débris suivis"] / tableau["TOTAL"].where(tableau["TOTAL"] > 0),
                                      np.nan)
    return tableau, bilan


def main():
    tableau, bilan = construire_tableau()
    for groupe, cat, nombre, fichier in bilan:
        print(f"{groupe:20s} {cat:18s} {nombre:6d} objets  ({fichier})")
    nb_debris = sum(n for _, cat, n, _ in bilan if cat == "Débris suivis")
    if nb_debris == 0:
        print("Aucun débris : lancer d'abord src/fetch_data.py puis src/altitudes.py.")
        return

    DOSSIER_PROCESSED.mkdir(parents=True, exist_ok=True)
    tableau.to_csv(DOSSIER_PROCESSED / "comparaison_debris.csv", index=False)

    total_actifs = tableau["Satellites actifs"].sum()
    total_debris = tableau["Débris suivis"].sum()
    print(f"\nSous {ALTITUDE_MAX_KM} km : {total_actifs:.0f} satellites actifs équivalents, "
          f"{total_debris:.0f} débris équivalents ({total_debris / (total_actifs + total_debris):.1%} du total)")
    print("\nTranches où la part des débris est la plus forte :")
    top = tableau.dropna(subset=["PART_DEBRIS"]).nlargest(5, "PART_DEBRIS")
    for _, ligne in top.iterrows():
        print(f"  {ligne['TRANCHE_KM']:4.0f}–{ligne['TRANCHE_KM'] + LARGEUR_TRANCHE_KM:4.0f} km : "
              f"{ligne['PART_DEBRIS']:5.1%} de débris ({ligne['Débris suivis']:.0f} sur {ligne['TOTAL']:.0f})")
    print("\nTableau enregistré dans", DOSSIER_PROCESSED / "comparaison_debris.csv")


if __name__ == "__main__":
    main()
