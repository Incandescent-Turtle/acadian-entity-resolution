# 0004 — Self-supervised contrastive training

**Context.** We have no labelled duplicates for training. The real labels (RQ2) are
few and reserved for evaluation, and the clone benchmark is for testing. The encoder
must still learn that two noisy versions of the same person (and their family) belong
together.

**Decision.** Use symmetric **InfoNCE with in-batch negatives**:
- Each anchor person gets two views.
- In each view, every node in the anchor's k-hop ego graph gets an independently
  augmented record, and family links are dropped at random. The augmentations:
  - drop the first given name;
  - swap a given-name variant;
  - drop dated facts and shift years;
  - drop places;
  - drop links (p = 0.3).
- Settings: temperature 0.1, AdamW (lr 1e-3, weight decay 1e-4), 10 epochs of 20k
  anchors, batch 256.
- Benchmark anchors are never training anchors.
- One encoder is trained per k with the same seed and settings.

Alternatives considered:
- A supervised loss on synthetic duplicates: rejected, because it learns the
  generator's noise, not the data.
- Link prediction: rejected, because it learns kinship, not identity.
- A triplet loss with mined negatives: possible later, once a baseline exists.

**Consequences.**
- No labels are needed, so the same procedure runs on the real snapshot.
- **Leakage risk:** the augmentations overlap tiers 1 (given name), 2 (dates) and 4
  (dropped neighbours), which may favour the R-GCN on those tiers.
  - Mitigation: dit-name swaps, blanked parents' names (t3) and line removal (t5) are
    *not* augmentations.
  - k=0 gets the same training, so the k-comparison is fair.
  - The attribute baselines are untrained; this is reported as a threat to validity.
- In-batch negatives are mostly easy (random people). Hard negatives, such as same-name
  candidates, could sharpen the ranking but would need care to avoid false negatives
  (true duplicates across trees).
