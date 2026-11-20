# 0005 — Two attribute-only text-embedding baselines

**Context.** RQ1 needs a strong attribute-only baseline to show what the graph adds.
One option is character n-grams (cheap, robust to spelling); the other is a pretrained
language model (may know Marie ≈ Mary, but is a black box and not trained on genealogy).

**Decision.** Implement both, chosen per config (decided with the user):
- `tfidf`: char 2–4-gram TF-IDF (`char_wb`, sublinear TF, accents stripped) over
  `record_text(p)`, fitted on all records in the benchmark's query and candidate lists.
  This is the default and the one tests use.
- `sentence_transformer`:
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingual, small
  enough for the 1070), with normalised embeddings.

Both rank by cosine similarity. The record text contains only the person's own facts
(ADR 0007).

**Consequences.**
- Tests stay offline and deterministic.
- The sentence-transformer needs a one-time ~470 MB download. Its version is set by
  `text_embedding.st_model`; pin a revision there for the final runs.
- Fitting TF-IDF on the evaluation records is transductive but unsupervised (no labels),
  and the same for every query.
