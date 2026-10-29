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
