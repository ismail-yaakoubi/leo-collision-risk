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
  
  ## D2 – Date de référence commune (28/10/2026)

**Contexte :** chaque objet a sa propre date de mesure (`EPOCH`), de quelques heures à
quelques jours avant le téléchargement. Pour compter les objets par tranche d'altitude,
il faut les placer tous au même instant.

**Options envisagées :**
- Option 1 : la date de lancement du script (« maintenant »). Le résultat change à chaque
  lancement, et la précision se dégrade si on relance le calcul longtemps après le
  téléchargement (le freinage atmosphérique fait dériver SGP4 de quelques km par jour).
- Option 2 : l'`EPOCH` de chaque objet. Précision maximale, mais les objets ne sont pas au
  même instant : impossible de compter l'encombrement d'une tranche à un moment donné.
- Option 3 : la date du téléchargement, lue dans le nom du fichier.

**Décision :** option 3, la date du téléchargement, commune à tous les objets d'un fichier.

**Justification :**
- reproductible : le même fichier donne toujours le même résultat ;
- précise : c'est la date commune la plus proche de toutes les mesures (en général moins
  d'un jour d'écart en orbite basse).

**Conséquences :**
- les objets à la mesure ancienne et très bas sont les moins bien placés (jusqu'à
  27 km d'écart avec Kepler pour un objet mesuré 3,6 jours avant) ; la colonne
  `AGE_EPOCH_JOURS` permet de les repérer ;
- un objet que SGP4 ne peut pas propager jusqu'à cette date (par exemple YAOGAN-35 02B,
  vers 180 km) est exclu, avec son motif dans le résumé ;
- deux fichiers téléchargés à des dates différentes ne sont pas au même instant :
  pour les comparer, il faut utiliser des fichiers téléchargés au même moment.


  
## D3 – Mesure de l'encombrement par altitude (28/10/2026)

**Contexte :** un objet sur une orbite elliptique traverse plusieurs tranches
d'altitude. Le compter dans une seule tranche (par exemple à son altitude moyenne)
fausserait la répartition.

**Options envisagées :**
- Option 1 : une tranche par objet, selon son altitude moyenne.
- Option 2 : répartir chaque objet entre les tranches au prorata du temps qu'il y passe.

**Décision :** option 2. Chaque orbite est échantillonnée en 60 instants régulièrement
espacés dans le temps ; chaque échantillon vaut 1/60 d'objet. Tranches de 50 km.

**Justification :** le risque de collision dépend du temps passé dans une zone, pas de
l'altitude moyenne.

**Conséquences :**
- l'encombrement s'exprime en « objets équivalents » par tranche : un objet sur une orbite
  circulaire compte pour 1 dans une seule tranche, un objet sur une orbite elliptique est
  réparti entre plusieurs tranches ;
- la part des débris n'est calculée que pour les tranches d'au moins 50 objets équivalents,
  pour éviter des pourcentages extrêmes sans signification sur quelques objets.

## D4 – Prise en compte des débris (28/10/2026)

**Contexte :** le groupe `active` ne contient que les satellites en service. Les débris,
qui ne peuvent pas manœuvrer, sont pourtant une source majeure de risque.

**Options envisagées :**
- Option 1 : les groupes de débris publiés par CelesTrak, un par grand événement de
  fragmentation (Fengyun-1C, Cosmos 2251, Iridium 33, Cosmos 1408). Sans compte, même format.
- Option 2 : le catalogue complet de Space-Track.org (satellites morts, étages de fusée et
  tous les débris suivis). Plus complet, mais demande un compte et un autre format.

**Décision :** option 1 pour l'instant ; option 2 envisagée pour compléter.

**Justification :** l'option 1 s'intègre sans changer le code de calcul et couvre les plus
grands nuages de débris de l'orbite basse.

**Conséquences :**
- notre jeu de données (environ 19 500 objets) ne représente qu'environ 41 % des quelque
  47 220 objets suivis (ESA, octobre 2026) : l'encombrement et le risque calculés sont des minorants ;
- un objet présent dans deux groupes n'est compté qu'une fois (les satellites actifs sont
  traités en premier) ;
- les débris de moins de 10 cm, non suivis, seront estimés séparément à partir des chiffres
  publiés par l'ESA.

## D5 – Modèle de risque et Monte-Carlo (29/10/2026)

**Contexte :** passer de la densité d'objets par tranche à une probabilité de collision,
alors que plusieurs paramètres sont mal connus (vitesses relatives, tailles, manœuvres,
petits débris non suivis).

**Options envisagées :**
- Option 1 : un calcul unique avec des valeurs centrales. Simple, mais ne dit rien de la
  fiabilité du résultat.
- Option 2 : le même modèle, avec un Monte-Carlo sur les paramètres incertains.
- Option 3 : les modèles de référence des agences (MASTER pour l'ESA, ORDEM pour la NASA).
  Plus complets, mais accès sur inscription ou demande, et difficiles à brancher sur notre chaîne.

**Décision :** option 2. Modèle de la théorie cinétique des gaz (Kessler et Cour-Palais, 1978) :
taux = densité × vitesse relative × section de collision, probabilité annuelle
1 − exp(−taux × 1 an) (loi de Poisson). Monte-Carlo de 10 000 tirages, graine fixe (42) ;
résultat : médiane et intervalle à 90 % (5e et 95e percentiles).

**Hypothèses (lois uniformes, car seules des bornes plausibles sont connues) :**
- vitesse relative 7 à 13 km/s (environ 10 km/s en moyenne en orbite basse) ;
- rayon des satellites actifs 1 à 3 m, des débris suivis 5 à 50 cm ;
- 90 à 99 % des collisions avec un satellite actif évitées par manœuvre ; aucune pour les débris ;
- 15 à 30 débris de 1 à 10 cm par objet suivi (ESA : environ 1,5 million contre 68 450,
  soit environ 22), de rayon 3 cm, répartis en altitude comme les débris suivis ;
- satellite étudié : 1 m de rayon (choix fixe, pas une incertitude).

**Justification :** le Monte-Carlo donne une plage de résultats honnête plutôt qu'un chiffre
d'une précision illusoire ; le modèle est le modèle de base des études de débris.

**Conséquences :**
- deux risques sont donnés séparément : collision avec un objet suivi, impact d'un petit débris ;
- résultats stables à moins de 1 % en changeant la graine (vérifié avec 42, 1 et 2026) ;
- le paramètre le plus influent est l'efficacité des manœuvres (un facteur 10 sur le risque
  à 450–500 km) ;
- les objets suivis absents de nos données (environ 59 % du catalogue) ne sont pas inclus :
  le risque calculé est un minorant ;
- l'estimation des petits débris est la partie la moins solide : à valider contre les flux
  publiés par MASTER (amélioration envisagée), de même que des lois triangulaires pour la
  vitesse relative et le rapport petits/grands débris.
