"""
Zone d'attente pour du code destiné à `genealogie_acadienne`.

Actuellement VIDE : les premiers modules (variantes, candidats, dates,
voisinage, clonage, synthétique, instantanés) ont déménagé dans la
bibliothèque le 2026-11-20 (`package-module` @ 58f6445).

Règles pour un nouveau module (voir docs/LIBRARY_STAGING.md) :
  - dépend seulement de `genealogie_acadienne` et de bibliothèques légères
    (bibliothèque standard, pandas, pyarrow, numpy) ;
  - n'importe JAMAIS le reste de `acadian_er`, ni torch, PyG ou un LLM ;
  - suit les conventions de `genealogie_acadienne` (noms en français, modèle
    `Personne`), pour que le déménagement soit une copie, pas une réécriture ;
  - ses tests vont dans tests/lib_staging/, sans base ni code du projet.
"""
