# 0007 — "Attribute-only" (k=0) means the person's own facts

**Context.** A `Personne` carries copies of its relatives' names and birth years
(`Proche`) and of spouses' names (`Mariage.conjoint`). If those were used at k=0, the
"attribute-only" methods would already see the family, and the k=0 vs k=1/2 contrast
would be muddied.

**Decision.**
- The k=0 view (R-GCN features, the text baselines' `record_text`, and RQ2's k=0
  context) uses only the person's own facts:
  - names, including alternative and dit names;
  - sex;
  - dates and places of their events;
  - marriage dates and places.
- It does **not** use relatives' names, spouse names, or the number of relatives.
- Family information enters only through graph edges (R-GCN) or the 2-hop context (RQ2).
- `exact_name` is the exception: it is the old method as-is, and its `comparer` uses
  parents' and children's names.

**Consequences.**
- Clean ablations, enforced by `tests/test_graph.py::test_features_ignore_relatives`
  and `tests/test_baselines_and_metrics.py::test_record_text_is_attribute_only`.
- The k=0 methods are somewhat weaker than "the record as a genealogist sees it"; this
  is stated in RESEARCH_DESIGN.md.
