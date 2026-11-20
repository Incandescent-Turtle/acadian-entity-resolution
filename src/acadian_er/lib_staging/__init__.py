"""
Code destiné à `genealogie_acadienne` (« en attente » de déménagement).

Règles (voir docs/LIBRARY_STAGING.md) :
  - dépend seulement de `genealogie_acadienne` et de bibliothèques légères
    (bibliothèque standard, pandas, pyarrow) ;
  - n'importe JAMAIS le reste de `acadian_er`, ni torch, PyG ou un LLM ;
  - suit les conventions de `genealogie_acadienne` (noms en français, modèle
    `Personne`) pour que le déménagement soit une copie, pas une réécriture.

Modules :
  - `noms_variantes` : formes canoniques des prénoms et des noms de famille
  - `candidats`      : génération de candidats par nom « relâché »
  - `dates`          : lecture et comparaison des dates GEDCOM
  - `voisinage`      : liens familiaux typés et voisinage à k sauts
  - `instantane`     : export / import d'instantanés Parquet
  - `synthetique`    : générateur de population acadienne synthétique
"""
