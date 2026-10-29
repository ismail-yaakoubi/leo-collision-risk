"""Risque de collision par tranche d'altitude, avec son incertitude (Monte-Carlo).

Modèle (théorie cinétique des gaz) : un satellite qui traverse un nuage d'objets de densité
spatiale rho subit en moyenne  rho × v_rel × sigma  collisions par seconde, où v_rel est la
vitesse relative moyenne et sigma la section de collision, pi × (r_cible + r_objet)².
La probabilité d'au moins une collision en un an vaut alors 1 − exp(−taux × 1 an).

Deux risques sont calculés séparément :
- collision avec un objet suivi (satellite actif ou débris suivi) : destruction probable ;
- impact d'un petit débris non suivi (1 à 10 cm), estimé à partir des chiffres de l'ESA :
  souvent fatal pour la mission, et impossible à éviter puisqu'il n'est pas suivi.

Les paramètres mal connus sont tirés au hasard (Monte-Carlo) : on obtient pour chaque tranche
une médiane et un intervalle à 90 % (5e et 95e percentiles), pas un chiffre unique.

Les résultats sont enregistrés dans data/processed/risque_monte_carlo.csv ; la figure est tracée
par src/figures.py.

Utilisation, depuis la racine du projet (après src/comparaison.py) :
    python src/monte_carlo.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

DOSSIER_PROCESSED = Path("data/processed")
R_TERRE_KM = 6378.137
LARGEUR_TRANCHE_KM = 50
SECONDES_PAR_AN = 365.25 * 86400
N_TIRAGES = 100_000
GRAINE = 42                        # graine fixe : mêmes tirages à chaque exécution (reproductible)
ZONE_KM = (250, 1500)              # tranches affichées (et tracées par src/figures.py)

# Satellite à placer (choix de l'utilisateur, fixe)
RAYON_CIBLE_M = 1.0                # section d'environ 3 m²

# Paramètres incertains : (minimum, maximum) d'une loi uniforme
V_REL_KMS = (7.0, 13.0)            # vitesse relative moyenne en orbite basse, ordre de grandeur 10 km/s
RAYON_ACTIFS_M = (1.0, 3.0)        # satellites actifs, panneaux solaires compris
RAYON_DEBRIS_M = (0.05, 0.5)       # débris suivis (plus de 10 cm)
EVITEMENT_ACTIFS = (0.90, 0.99)    # part des collisions avec un satellite actif évitée par manœuvre
PETITS_PAR_DEBRIS = (15.0, 30.0)   # débris de 1 à 10 cm par débris suivi (ESA : environ 22)
RAYON_PETITS_M = 0.03              # taille typique d'un débris de 1 à 10 cm


def volume_tranche(altitude_bas_km, largeur_km=LARGEUR_TRANCHE_KM):
    """Volume (km³) de la coquille sphérique entre deux altitudes."""
    r1 = R_TERRE_KM + np.asarray(altitude_bas_km, dtype=float)
    r2 = r1 + largeur_km
    return 4 / 3 * np.pi * (r2**3 - r1**3)


def probabilite_annuelle(densite_km3, v_rel_kms, rayon_cible_m, rayon_objet_m):
    """Probabilité d'au moins une collision en un an (modèle de la théorie cinétique des gaz)."""
    sigma_km2 = np.pi * ((rayon_cible_m + rayon_objet_m) / 1000) ** 2
    taux_par_an = densite_km3 * v_rel_kms * sigma_km2 * SECONDES_PAR_AN
    return 1 - np.exp(-taux_par_an)


def tirer_parametres(n, generateur):
    """Tire n jeux de paramètres incertains (une ligne par tirage)."""
    def uniforme(bornes):
        return generateur.uniform(bornes[0], bornes[1], size=(n, 1))   # (n, 1) : s'applique à toutes les tranches
    return {
        "v_rel": uniforme(V_REL_KMS),
        "rayon_actifs": uniforme(RAYON_ACTIFS_M),
        "rayon_debris": uniforme(RAYON_DEBRIS_M),
        "evitement": uniforme(EVITEMENT_ACTIFS),
        "petits_par_debris": uniforme(PETITS_PAR_DEBRIS),
    }


def simuler(tableau, n=N_TIRAGES, graine=GRAINE):
    """Renvoie les tirages (n × tranches) des deux risques : objets suivis et petits débris."""
    generateur = np.random.default_rng(graine)
    p = tirer_parametres(n, generateur)
    volume = volume_tranche(tableau["TRANCHE_KM"].to_numpy())
    rho_actifs = tableau["Satellites actifs"].to_numpy() / volume
    rho_debris = tableau["Débris suivis"].to_numpy() / volume

    p_actifs = probabilite_annuelle(rho_actifs, p["v_rel"], RAYON_CIBLE_M, p["rayon_actifs"]) * (1 - p["evitement"])
    p_debris = probabilite_annuelle(rho_debris, p["v_rel"], RAYON_CIBLE_M, p["rayon_debris"])
    p_suivis = 1 - (1 - p_actifs) * (1 - p_debris)          # au moins une des deux collisions

    rho_petits = rho_debris * p["petits_par_debris"]        # hypothèse : même répartition que les débris suivis
    p_petits = probabilite_annuelle(rho_petits, p["v_rel"], RAYON_CIBLE_M, RAYON_PETITS_M)
    return p_suivis, p_petits


def resumer(tableau, tirages, nom):
    """Médiane et intervalle à 90 % de chaque tranche."""
    return pd.DataFrame({
        "TRANCHE_KM": tableau["TRANCHE_KM"],
        f"{nom}_P05": np.percentile(tirages, 5, axis=0),
        f"{nom}_MEDIANE": np.median(tirages, axis=0),
        f"{nom}_P95": np.percentile(tirages, 95, axis=0),
    })


def main():
    chemin = DOSSIER_PROCESSED / "comparaison_debris.csv"
    if not chemin.exists():
        raise FileNotFoundError("Lancer d'abord src/comparaison.py.")
    tableau = pd.read_csv(chemin)

    p_suivis, p_petits = simuler(tableau)
    resultats = resumer(tableau, p_suivis, "SUIVIS").merge(resumer(tableau, p_petits, "PETITS"), on="TRANCHE_KM")
    resultats.to_csv(DOSSIER_PROCESSED / "risque_monte_carlo.csv", index=False)

    zone = resultats[(resultats["TRANCHE_KM"] >= ZONE_KM[0]) & (resultats["TRANCHE_KM"] < ZONE_KM[1])]
    print("Probabilité annuelle de collision (médiane [intervalle à 90 %]) :")
    for _, l in zone.iterrows():
        print(f"  {l['TRANCHE_KM']:4.0f}–{l['TRANCHE_KM'] + LARGEUR_TRANCHE_KM:4.0f} km   "
              f"objets suivis {l['SUIVIS_MEDIANE']:.1e} [{l['SUIVIS_P05']:.1e} – {l['SUIVIS_P95']:.1e}]   "
              f"petits débris {l['PETITS_MEDIANE']:.1e} [{l['PETITS_P05']:.1e} – {l['PETITS_P95']:.1e}]")
    print("\nRésultats enregistrés dans", DOSSIER_PROCESSED / "risque_monte_carlo.csv")


if __name__ == "__main__":
    main()
