# 0001 — Fix `Personne` gaps in the library itself

**Context.** `genealogie_acadienne`'s `Personne` lacked what this project needs:
- relatives had no IDs, so the family graph could not be built;
- there was no given-name/surname split, no alternative names, no full dates and no
  places.

The options were sidecar tables in this repo, or changing the library. The user owns
the library and agreed to change it.

**Decision.** The library was extended on `package-module` (`f860afa`..`93a34cf`):
- `Proche.person_id` and `Mariage.conjoint_id`;
- `prenoms`, `nom_famille` and `noms_alternatifs`;
- `dates`, `lieux` and `Mariage.date`/`lieu` from the raw GEDCOM;
- dit-name and given-name matching taken from `appariement-prenoms`.

New fields are optional or have defaults, and `comparer` is unchanged. This repo pins
that commit and uses `Personne` everywhere; it defines no person model of its own.

**Consequences.**
- One model, so there is no conversion layer to keep in sync.
- The RQ1 baseline is exactly the old method.
- Future gaps are also fixed upstream: bump the pin after each change.
- The loader SQL is tested against an SQLite stand-in, not the real MariaDB. The first
  real snapshot is the real test.
