"""Télécharge les éléments orbitaux publics de CelesTrak."""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://celestrak.org/NORAD/elements/gp.php"
DOSSIER_RAW = Path("data/raw")
GROUPE = "active"


def telecharger(groupe):
    """Télécharge un groupe CelesTrak et renvoie la liste des objets."""
    reponse = requests.get(URL, params={"GROUP": groupe, "FORMAT": "json"}, timeout=30)
    if reponse.status_code != 200:
        print("Message de CelesTrak :", reponse.text)
    reponse.raise_for_status()
    return reponse.json()


def sauvegarder(donnees, groupe):
    """Enregistre les données dans data/raw, avec la date dans le nom du fichier."""
    DOSSIER_RAW.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    chemin = DOSSIER_RAW / f"{groupe}_{date}.json"
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    return chemin


if __name__ == "__main__":
    donnees = telecharger(GROUPE)
    chemin = sauvegarder(donnees, GROUPE)
    print(f"{len(donnees)} objets enregistrés dans {chemin}")