# Decision log

Short architecture decision records. Each one gives the context, the decision and its
consequences. Status is *accepted* unless marked otherwise.

| # | Decision |
| --- | --- |
| [0001](0001-extend-the-library-model.md) | Fix `Personne` gaps in `genealogie_acadienne` itself; no competing model |
| [0002](0002-pytorch-cu126-for-pascal.md) | Pin PyTorch 2.14 from the CUDA 12.6 index for the GTX 1070 |
| [0003](0003-pyg-rgcn-with-ego-subgraphs.md) | PyG `RGCNConv`, with per-centre k-hop ego subgraphs as mini-batches |
| [0004](0004-contrastive-training.md) | Self-supervised contrastive training (InfoNCE on augmented views) |
| [0005](0005-text-embedding-baselines.md) | Two attribute-only text baselines: TF-IDF and a sentence-transformer |
| [0006](0006-shared-candidates-and-ties.md) | One relaxed-name candidate list for all methods; seeded tie-breaking |
| [0007](0007-attribute-only-means-own-facts.md) | "Attribute-only" (k=0) means the person's own facts, no relative's name |
| [0008](0008-rq2-fact-ids-and-backends.md) | RQ2: fact IDs for evidence, faithfulness by ID + value, OpenAI-compatible backend |
| [0009](0009-clone-immediate-family.md) | Clone only the immediate family (*proposed*: to confirm) |
