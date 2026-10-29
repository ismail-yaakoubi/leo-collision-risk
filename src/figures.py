"""Figures du projet, à partir des résultats de src/altitudes.py et src/comparaison.py.

Cinq figures, enregistrées dans figures/ :
- encombrement par altitude (satellites actifs et débris suivis) ;
- débris suivis par altitude ;
- part des débris par altitude ;
- validation : écart entre SGP4 et Kepler (groupe active) ;
- risque de collision par altitude (Monte-Carlo).

Utilisation, depuis la racine du projet (après src/altitudes.py, src/comparaison.py et
src/monte_carlo.py) :
    python src/figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")              # pas de fenêtre : on enregistre directement en PNG
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from monte_carlo import N_TIRAGES, RAYON_CIBLE_M, ZONE_KM   # mêmes réglages que le calcul

DOSSIER_PROCESSED = Path("data/processed")
DOSSIER_FIGURES = Path("figures")
LARGEUR_TRANCHE_KM = 50
ALTITUDE_MAX_KM = 2000
SEUIL_TRANCHE = 50                 # le même seuil que dans src/comparaison.py

# Une seule série par figure ; le texte reste en gris neutre, jamais dans la couleur de la série
BLEU = "#2a78d6"
ORANGE = "#eb6834"
TEXTE = "#0b0b0b"
TEXTE_SECONDAIRE = "#52514e"
GRILLE = "#e4e3df"


def dernier_resume(groupe="active"):
    """Charge le dernier fichier altitudes_* du groupe ; renvoie le tableau et son suffixe."""
    fichiers = sorted(DOSSIER_PROCESSED.glob(f"altitudes_{groupe}_*.csv"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun résultat pour '{groupe}' : lancer d'abord src/altitudes.py.")
    return pd.read_csv(fichiers[-1]), fichiers[-1].stem.removeprefix("altitudes_")


def charger_comparaison():
    chemin = DOSSIER_PROCESSED / "comparaison_debris.csv"
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} introuvable : lancer d'abord src/comparaison.py.")
    return pd.read_csv(chemin)


def nouvelle_figure():
    fig, ax = plt.subplots(figsize=(9, 4.8))
    fig.subplots_adjust(top=0.83, left=0.09, right=0.98, bottom=0.15)
    return fig, ax


def style_axes(ax):
    """Axes discrets : grille horizontale légère, pas de cadre en haut ni à droite."""
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        ax.spines[cote].set_color(GRILLE)
    ax.tick_params(colors=TEXTE_SECONDAIRE, labelsize=9)
    ax.yaxis.grid(True, color=GRILLE, linewidth=0.8)
    ax.set_axisbelow(True)


def axe_altitude(ax):
    ax.set_xlim(0, ALTITUDE_MAX_KM)
    ax.set_xlabel("Altitude au-dessus de l'ellipsoïde WGS84 (km), tranches de 50 km",
                  color=TEXTE_SECONDAIRE, fontsize=9.5)


def titre(fig, principal, secondaire, source):
    """Titre = le message de la figure, calculé à partir des données ; sous-titre = ce qu'on mesure."""
    fig.text(0.02, 0.95, principal, fontsize=12.5, fontweight="bold", color=TEXTE, ha="left")
    fig.text(0.02, 0.905, secondaire, fontsize=9.5, color=TEXTE_SECONDAIRE, ha="left")
    fig.text(0.98, 0.015, f"Source : {source}", fontsize=7.5, color=TEXTE_SECONDAIRE, ha="right")


def enregistrer(fig, nom):
    chemin = DOSSIER_FIGURES / nom
    fig.savefig(chemin, dpi=160)
    plt.close(fig)
    return chemin


def pourcent(x):
    """0.63 -> '63 %' (espace avant % en français)."""
    return f"{x:.0%}".replace("%", " %")


def figure_encombrement(tableau):
    """Objets équivalents par tranche : satellites actifs et débris suivis ensemble."""
    ligne_max = tableau.loc[tableau["TOTAL"].idxmax()]
    part_max = ligne_max["TOTAL"] / tableau["TOTAL"].sum()
    fig, ax = nouvelle_figure()
    ax.bar(tableau["TRANCHE_KM"], tableau["TOTAL"], width=LARGEUR_TRANCHE_KM - 6, align="edge", color=BLEU)
    style_axes(ax)
    axe_altitude(ax)
    ax.set_ylabel("Objets équivalents", color=TEXTE_SECONDAIRE, fontsize=9.5)
    titre(fig,
          f"La tranche {ligne_max['TRANCHE_KM']:.0f}–{ligne_max['TRANCHE_KM'] + LARGEUR_TRANCHE_KM:.0f} km "
          f"concentre {pourcent(part_max)} des objets suivis sous {ALTITUDE_MAX_KM} km",
          f"Temps passé par tranche d'altitude, en objets équivalents · "
          f"{tableau['TOTAL'].sum():.0f} objets (satellites actifs et débris suivis)",
          "CelesTrak (groupe active et quatre groupes de débris)")
    return enregistrer(fig, "encombrement_par_altitude.png")


def figure_debris(tableau):
    """Débris suivis par tranche d'altitude."""
    ligne_max = tableau.loc[tableau["Débris suivis"].idxmax()]
    fig, ax = nouvelle_figure()
    ax.bar(tableau["TRANCHE_KM"], tableau["Débris suivis"], width=LARGEUR_TRANCHE_KM - 6, align="edge",
           color=ORANGE)
    style_axes(ax)
    axe_altitude(ax)
    ax.set_ylabel("Objets équivalents", color=TEXTE_SECONDAIRE, fontsize=9.5)
    titre(fig,
          f"Les débris suivis sont les plus nombreux entre {ligne_max['TRANCHE_KM']:.0f} et "
          f"{ligne_max['TRANCHE_KM'] + LARGEUR_TRANCHE_KM:.0f} km",
          f"Temps passé par tranche d'altitude, en objets équivalents · "
          f"{tableau['Débris suivis'].sum():.0f} débris suivis (Fengyun-1C, Cosmos 2251, Iridium 33, Cosmos 1408)",
          "CelesTrak (groupes de débris)")
    return enregistrer(fig, "debris_par_altitude.png")


def figure_part_debris(tableau):
    """Part des débris dans les objets équivalents de chaque tranche assez peuplée."""
    part = tableau.dropna(subset=["PART_DEBRIS"])
    ligne_max = part.loc[part["PART_DEBRIS"].idxmax()]
    fig, ax = nouvelle_figure()
    ax.bar(part["TRANCHE_KM"], part["PART_DEBRIS"] * 100, width=LARGEUR_TRANCHE_KM - 6, align="edge",
           color=ORANGE)
    style_axes(ax)
    axe_altitude(ax)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Part des débris (%)", color=TEXTE_SECONDAIRE, fontsize=9.5)
    titre(fig,
          f"Les débris représentent jusqu'à {pourcent(ligne_max['PART_DEBRIS'])} des objets suivis, "
          f"entre {ligne_max['TRANCHE_KM']:.0f} et {ligne_max['TRANCHE_KM'] + LARGEUR_TRANCHE_KM:.0f} km",
          f"Part des débris suivis dans les objets équivalents de chaque tranche "
          f"(tranches d'au moins {SEUIL_TRANCHE} objets équivalents)",
          "CelesTrak (groupe active et quatre groupes de débris)")
    return enregistrer(fig, "part_debris_par_altitude.png")


def figure_validation(resume, suffixe):
    """Écart entre l'altitude moyenne SGP4 (sphère) et celle de Kepler, pour les objets en LEO."""
    leo = resume[(resume["CODE_ERREUR_SGP4"] == 0) & resume["EST_LEO"]]
    ecart = leo["ALT_MOY_SPHERE_KM"] - leo["ALT_MOY_KEPLER_KM"]
    seuil_95 = max(abs(ecart.quantile(0.025)), abs(ecart.quantile(0.975)))
    hors_cadre = int((ecart.abs() > 10).sum())

    fig, ax = nouvelle_figure()
    bords = np.arange(-10, 10.5, 0.5)                    # on montre la zone ±10 km
    ax.hist(ecart.clip(-10, 10), bins=bords, color=BLEU, rwidth=0.85)
    ax.axvline(0, color=TEXTE_SECONDAIRE, linewidth=1, linestyle="--")
    style_axes(ax)
    ax.set_xlim(-10, 10)
    ax.set_xlabel("Altitude moyenne SGP4 (sphère) − altitude moyenne de Kepler (km)",
                  color=TEXTE_SECONDAIRE, fontsize=9.5)
    ax.set_ylabel("Nombre d'objets", color=TEXTE_SECONDAIRE, fontsize=9.5)
    titre(fig,
          f"SGP4 et Kepler concordent : 95 % des objets à moins de {seuil_95:.1f} km",
          f"Écart moyen {ecart.mean():+.1f} km · {len(leo)} objets en orbite basse · "
          f"{hors_cadre} au-delà de ±10 km, regroupés aux bords",
          f"CelesTrak, fichier {suffixe}.json")
    return enregistrer(fig, "validation_kepler.png")


def figure_risque(resultats):
    """Risque annuel par tranche : médiane (point) et intervalle à 90 % (trait), deux séries."""
    zone = resultats[(resultats["TRANCHE_KM"] >= ZONE_KM[0]) & (resultats["TRANCHE_KM"] < ZONE_KM[1])]
    centre = zone["TRANCHE_KM"] + LARGEUR_TRANCHE_KM / 2
    series = [
        ("SUIVIS", "Collision avec un objet suivi", BLEU, -6),     # décalage de ±6 km :
        ("PETITS", "Impact d'un débris de 1 à 10 cm", ORANGE, 6),  # les points ne se cachent pas
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.subplots_adjust(top=0.82, left=0.1, right=0.98, bottom=0.14)
    for cle, libelle, couleur, decalage in series:
        mediane = zone[f"{cle}_MEDIANE"]
        ax.errorbar(centre + decalage, mediane,
                    yerr=[mediane - zone[f"{cle}_P05"], zone[f"{cle}_P95"] - mediane],
                    fmt="o", markersize=4, color=couleur, ecolor=couleur, elinewidth=1.2, capsize=0,
                    label=libelle)
    ax.set_yscale("log")           # les risques vont de 1e-6 à 1e-4 : échelle logarithmique
    style_axes(ax)
    ax.set_xlabel("Altitude (km), centre des tranches de 50 km", color=TEXTE_SECONDAIRE, fontsize=9.5)
    ax.set_ylabel("Probabilité par an (échelle logarithmique)", color=TEXTE_SECONDAIRE, fontsize=9.5)
    ax.legend(frameon=False, fontsize=9, loc="upper right")

    pic_suivis = zone.loc[zone["SUIVIS_MEDIANE"].idxmax(), "TRANCHE_KM"]
    pic_petits = zone.loc[zone["PETITS_MEDIANE"].idxmax(), "TRANCHE_KM"]
    titre(fig,
          f"Deux pics de risque : objets suivis à {pic_suivis:.0f}–{pic_suivis + LARGEUR_TRANCHE_KM:.0f} km, "
          f"petits débris à {pic_petits:.0f}–{pic_petits + LARGEUR_TRANCHE_KM:.0f} km",
          f"Satellite de {RAYON_CIBLE_M:.0f} m de rayon · point = médiane, trait = intervalle à 90 % · "
          f"{N_TIRAGES} tirages Monte-Carlo",
          "objets suivis : CelesTrak · petits débris : estimation calibrée sur l'ESA (MASTER)")
    return enregistrer(fig, "risque_par_altitude.png")


def main():
    DOSSIER_FIGURES.mkdir(parents=True, exist_ok=True)
    tableau = charger_comparaison()
    resume, suffixe = dernier_resume("active")
    for chemin in (figure_encombrement(tableau), figure_debris(tableau),
                   figure_part_debris(tableau), figure_validation(resume, suffixe)):
        print("Figure enregistrée :", chemin)

    chemin_risque = DOSSIER_PROCESSED / "risque_monte_carlo.csv"
    if chemin_risque.exists():
        print("Figure enregistrée :", figure_risque(pd.read_csv(chemin_risque)))
    else:
        print("Pas de figure du risque : lancer d'abord src/monte_carlo.py.")


if __name__ == "__main__":
    main()
