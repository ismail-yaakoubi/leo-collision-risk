# Journal des décisions

## D1 – Méthode de calcul de l'altitude (22/10/2026)

**Contexte :** CelesTrak ne donne pas l'altitude des objets, seulement
leurs éléments orbitaux moyens (mouvement moyen, excentricité…), mesurés
à des dates différentes selon les objets. Il faut calculer l'altitude
de chaque objet pour compter les objets par tranche d'altitude.

**Options envisagées :**
- Option 1 : formule de Kepler à partir du mouvement moyen et de
  l'excentricité. Très rapide, mais elle ignore l'aplatissement de la
  Terre, l'effet de J2 et la traînée : erreur de quelques km.
- Option 2 : propagation SGP4 de chaque objet jusqu'à une date commune,
  puis calcul de l'altitude sur l'ellipsoïde WGS84. Plus précise et
  synchronisée, mais plus complexe à mettre en œuvre.

**Décision :** SGP4 comme méthode principale, Kepler comme vérification.

**Justification :**
- SGP4 donne l'altitude réelle de chaque objet et ramène tous les objets
  à la même date, alors que les mesures de CelesTrak ne sont pas
  synchronisées.
- Le même calcul resservira pour détecter les rapprochements entre
  satellites, où une erreur de quelques km rendrait le résultat faux.
- Comparer les deux méthodes permet de valider le code : si SGP4 et
  Kepler donnent des altitudes proches (par exemple pour l'ISS,
  environ 415 km au périgée), le calcul est cohérent.

**Conséquences :**
- Le jeu de données final contiendra les deux altitudes, pour pouvoir
  mesurer l'écart entre les deux méthodes.
- Le temps de calcul augmente, mais reste de quelques secondes avec la
  bibliothèque sgp4, qui traite les objets par lots.
- Le code d'erreur renvoyé par SGP4 est vérifié à chaque propagation :
  une position en erreur est signalée et exclue du calcul d'altitude.
  