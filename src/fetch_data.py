"""Télécharge les éléments orbitaux publics de CelesTrak."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


URL = "https://celestrak.org/NORAD/elements/gp.php"
DOSSIER_RAW = Path("data/raw")
# Groupes téléchargés : les satellites en service, puis les débris suivis des quatre grands
# événements de fragmentation (tirs antisatellites et collision).
GROUPES = [
    "active",              # satellites en service
    "fengyun-1c-debris",   # tir antisatellite chinois, 2007
    "cosmos-2251-debris",  # collision avec Iridium 33, 2009
    "iridium-33-debris",   # même collision, 2009
    "cosmos-1408-debris",  # tir antisatellite russe, 2021
]


def telecharger(groupe):
    """Télécharge un groupe CelesTrak et renvoie la liste des objets."""
    reponse = requests.get(URL, params={"GROUP": groupe, "FORMAT": "json"}, timeout=30)
    if reponse.status_code != 200:
        print("Message de CelesTrak :", reponse.text)
    reponse.raise_for_status()
    donnees = reponse.json()          # ValueError si le site renvoie autre chose que du JSON
    if not isinstance(donnees, list) or not donnees:
        raise ValueError(f"réponse vide ou inattendue pour le groupe '{groupe}'")
    return donnees


def fichier_recent(groupe, heures=2):
    """Renvoie le dernier fichier du groupe s'il a moins de `heures` heures, sinon None."""
    fichiers = sorted(DOSSIER_RAW.glob(f"{groupe}_*.json"))
    if not fichiers:
        return None
    dernier = fichiers[-1]
    age_secondes = time.time() - dernier.stat().st_mtime
    if age_secondes < heures * 3600:
        return dernier
    return None


def sauvegarder(donnees, groupe):
    """Enregistre les données dans data/raw, avec la date dans le nom du fichier."""
    DOSSIER_RAW.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    chemin = DOSSIER_RAW / f"{groupe}_{date}.json"
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    return chemin


def collecter(groupe):
    """Télécharge un groupe, sauf si un fichier de moins de 2 h existe déjà."""
    recent = fichier_recent(groupe)
    if recent is not None:
        print(f"[cache]  {groupe} : fichier de moins de 2 h trouvé ({recent.name})")
        return
    donnees = telecharger(groupe)
    chemin = sauvegarder(donnees, groupe)
    print(f"[ok]     {groupe} : {len(donnees)} objets enregistrés dans {chemin}")


if __name__ == "__main__":
    echecs = []
    for groupe in GROUPES:
        try:
            collecter(groupe)
        except (requests.RequestException, ValueError) as erreur:
            # Un groupe en échec ne doit pas empêcher de récupérer les autres
            echecs.append(groupe)
            print(f"[échec]  {groupe} : {erreur}")
        time.sleep(1)  # une seconde entre deux requêtes, par politesse envers le serveur

    if echecs:
        print(f"Groupes non récupérés : {', '.join(echecs)}")
