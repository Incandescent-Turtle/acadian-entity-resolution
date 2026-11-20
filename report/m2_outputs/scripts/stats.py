import sys, collections, pandas as pd
from genealogie_acadienne.donnees.instantane import lire_instantane
from genealogie_acadienne import alias_dit
from genealogie_acadienne.commun.variantes import nom_famille_probable
S, T = sys.argv[1], sys.argv[2]
ps = list({(p.tree_id, p.person_id): p for p in lire_instantane(S + "/snapshot")}.values())
n = len(ps); per = pd.Series(collections.Counter(p.tree_id for p in ps))
print("people", n, "trees", len(per), "per tree min/med/mean/max", per.min(), per.median(), round(per.mean()), per.max())
print("trees >=1000:", (per>=1000).sum(), "top5 share", round(per.nlargest(5).sum()/n,3))
yrs = pd.Series([p.faits.get("BIRT") for p in ps if p.faits.get("BIRT")])
print("birth year", len(yrs), round(len(yrs)/n,3), "place", sum(1 for p in ps if p.lieux.get("BIRT")), round(sum(1 for p in ps if p.lieux.get("BIRT"))/n,3))
print("year quantiles", yrs.quantile([0,.05,.25,.5,.75,.95,1]).tolist())
print("by century", (yrs//100*100).value_counts().sort_index().to_dict())
approx = sum(1 for p in ps if (p.dates.get("BIRT") or "").split()[:1] and (p.dates.get("BIRT") or "").split()[0] in ("ABT","BEF","AFT","EST","CAL","BET"))
print("approx-qualified birth dates", approx, round(approx/max(len(yrs),1),3))
print("empty names", sum(1 for p in ps if not p.nom_norm))
print("dit names", sum(1 for p in ps if alias_dit(p.nom_complet)))
print("distinct normalised names", len({p.nom_norm for p in ps}))
sur = collections.Counter(nom_famille_probable(p.nom_complet, p.nom_famille).lower() for p in ps)
sur.pop("", None)
print("distinct surnames", len(sur), "top10", sur.most_common(10), "top10 share", round(sum(c for _,c in sur.most_common(10))/n,3))
np_ = pd.read_csv(T+"/noms_partages.csv"); pr = pd.read_csv(T+"/partages_resume.csv")
print("people in shared-name groups", len(np_), "groups", len(pr), "max group", pr.n_personnes.max(), "median", pr.n_personnes.median())
pe = pd.read_csv(T+"/paires_exact.csv"); p2 = pd.read_csv(T+"/paires_partage2.csv")
print("paires_exact", len(pe), pe.exact.value_counts().to_dict(), "paires_partage2", len(p2), p2.exact.value_counts().to_dict())
