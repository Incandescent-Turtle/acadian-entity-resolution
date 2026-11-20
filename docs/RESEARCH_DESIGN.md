# Research design

**Underlying question:** when does the family-graph structure around a person help find
their duplicate, compared with that person's record alone?

The database: ~150,000 people in ~60 interconnected WebTrees family trees. The same
real person often appears in several trees with:
- spelling variants (Comeau/Comeaux, Marie/Mary);
- dropped first given names ("Marie Louise Comeaux" vs "Louise Comeaux");
- *dit* names (aliases, often alternative surnames: "Jean Doucet dit Laverdure");
- approximate or missing dates and places.

## RQ1 — retrieval

> Do R-GCN neighbourhood embeddings rank the true duplicate higher than attribute-only methods?

**Ground truth by cloning.** An *anchor* is a well-documented person: at least
`min_fields` filled attribute fields and at least `min_family` relatives in the tree.
The anchor and their immediate family (parents, spouses, children; `clone_depth: 1`)
are copied into a dummy tree. The clone and the original are a known match.

**Tiers.** The same anchors are cloned once per tier, and one perturbation is applied
to each clone:

| Tier | Perturbation | What it tests |
| --- | --- | --- |
| t0_clean | none (control) | upper bound; sanity check for every method |
| t1_name | dropped first given name; else the dit name used as the surname; else a given-name variant (Marie → Mary) | name variation |
| t2_dates | each of the anchor's dates removed (p = 0.5) or shifted by 1–5 years; marriage date removed | missing or wrong attributes |
| t3_parent_names | the anchor's parents' names blanked | neighbourhood present but unnamed |
| t4_neighbourhood | most relatives dropped (25% kept) | little graph to use |
| t5_one_line | only the paternal or only the maternal line kept | asymmetric neighbourhood |

**Expectations** (hypotheses, not results):
- Graph methods should help most where the attributes are weakened but the family is
  intact (t1, t2, t3).
- They should help least, or hurt, where the family is removed (t4, t5).
- k=0 against k=1/2 isolates the effect of the neighbourhood: same model, features
  and training.

**Candidates.** All methods rank the same relaxed-name candidate list
(`genealogie_acadienne.commun.candidats`). A candidate must share a surname key (spelling variants and
dit aliases included) and at least one canonical given name (Marie = Mary; dropped
given names allowed). Clone trees are excluded and people of the opposite known sex are
excluded. Candidate-list recall is reported separately: a target missing from the list
is a miss for every method.

**Methods.**

| Method | Information used |
| --- | --- |
| `exact_name` | the old repo's method: exact normalised-name pool first, then the number of concordant criteria from `comparer` (birth, baptism, death, burial, marriage, parents, children). Uses relatives' names, as the old method does |
| `tfidf` | attribute-only: char 2–4-gram TF-IDF of the record written out as text |
| `sentence_transformer` | attribute-only: a pretrained multilingual sentence model on the same text |
| `rgcn_k0` | the R-GCN with zero hops: attribute features only (same model and training as k=1/2) |
| `rgcn_k1`, `rgcn_k2` | R-GCN over the 1- and 2-hop typed family graph |

**Metrics, per tier and overall:** Recall@5, Recall@10, MRR. Ties are broken by a
seeded hash, never by list order. We also report candidate recall and the mean
candidate-list size.

## RQ2 — verification

> Given a candidate pair, does an LLM answer match / not_match / insufficient better,
> and more faithfully, with the 2-hop neighbourhood (k=2) than with the two records alone (k=0)?

- **Pairs:** 150–200 real pairs, hand-labelled (`match`, `not_match`, `unsure`), kept
  separate from the clones. They are proposed from RQ1 rankers' top results on real
  data (`acadian-er rq2-candidates`), so they are hard, realistic candidates rather
  than random pairs.
- **Context:** each fact has an ID (`A.birth.date`, `B.father.name`,
  `A.spouse1.mother.name`, …).
  - k=0 has only the two records' own facts.
  - k=2 adds every relative within two hops, addressed by role path.
- **Output:** JSON with the verdict, cited evidence (fact ID and value) and a short
  rationale. Parsing is tolerant; unparseable replies count as `invalid`.
- **Metrics per k:**
  - precision, recall and F1 for `match` (an `insufficient` on a true match counts as a
    miss);
  - decided rate, accuracy on decided pairs, invalid rate;
  - faithfulness: the share of citations whose ID exists in the context with a matching
    value, and the share of replies whose citations are all faithful.
  - `unsure` pairs are excluded from precision and recall.
- **Backends:** a local model through Ollama, an OpenAI-compatible API (OpenRouter or a
  cluster server), and a deterministic fake for tests. Temperature is 0 and a seed is
  sent where supported.

## How RQ1 and RQ2 connect

- RQ1 asks whether the family graph helps **find** the duplicate among many candidates.
  RQ2 asks whether it helps **decide** on one pair and justify the decision.
- RQ1's rankers produce RQ2's candidate pairs, so RQ2 evaluates the pairs a real
  workflow would surface.
- Both use the same k=0 vs k=2 contrast and the same definition of "attribute-only":
  the person's own facts, no relative's name. That keeps the two answers comparable.

## Threats to validity

- **Clones are not real duplicates.** A clone is a copy of the same record plus
  controlled noise. Real duplicates differ in ways we don't model (different sources,
  transcription errors, conflicting facts, partial merges). The tiers are stress tests,
  not a sample of real variation. RQ2 on real labelled pairs partly addresses this.
- **Synthetic development data.** Every current number comes from our own generator,
  so it reflects our assumptions (see DATA_MODEL.md). No conclusions should be drawn
  before real data.
- **Augmentation–tier overlap.** The R-GCN is trained with record noise (dropped given
  name, dropped or shifted dates, name variants, dropped links) that overlaps tiers 1, 2
  and 4. This can favour the R-GCN on those tiers. The augmentations deliberately leave
  out dit-name swaps, blanked parent names and line removal (tiers 3 and 5). The
  attribute baselines get no training at all. See ADR 0004.
- **Clone neighbourhood depth.** With only the immediate family cloned, the clone's
  2-hop neighbourhood is thinner than the original's: grandparents, siblings and in-laws
  are missing. This works against k=2. **Mitigation (agreed): RQ1 is run with
  `clone_depth: 1` (as specified) and `clone_depth: 2` side by side** and both are
  reported (ADR 0009).
- **Candidate generation bounds recall.** All methods share one candidate list, so a
  blocking miss is everyone's miss. This is reported but can hide differences.
- **Anchor selection bias.** Anchors are well-documented people by construction. Results
  may not transfer to sparse records, which are the common case.
- **The `exact_name` baseline is not attribute-only.** It compares parents' and
  children's names, as the old method does. It's the practical baseline, not the k=0 ablation.
- **Leakage between clone and original.** The original stays in the graph, and the
  clone's relatives are copies of the original's relatives. A method could match
  relatives rather than the person. That is the intended signal, but tiers 3–5 control
  how much of it survives.
- **LLM non-determinism and contamination.** Even at temperature 0, outputs can vary
  between runs and server versions. Model and server versions are recorded in the config
  and the raw replies are saved. Public genealogies could appear in a model's
  pretraining data.
- **Label quality.** One labeller, and some hard pairs are inherently uncertain. Pairs
  are marked `unsure` rather than forced, and the labeller and notes are recorded.
