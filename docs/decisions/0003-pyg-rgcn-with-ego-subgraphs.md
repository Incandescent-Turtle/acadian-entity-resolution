# 0003 — PyG `RGCNConv` with per-centre k-hop ego subgraphs

**Context.**
- We need an R-GCN over typed family edges (parent_of, child_of, spouse_of) at k=0, 1
  and 2, trained in mini-batches on up to 150k nodes on an 8 GB GPU.
- PyG's `NeighborLoader` needs `pyg-lib` or `torch-sparse`, whose Windows / Python 3.13
  wheels are unreliable.
- With full-graph or shared-neighbourhood batches, a centre's receptive field depends
  on what else is in the batch.

**Decision.**
- Use PyTorch Geometric's `RGCNConv` (mean aggregation, root weight, optional basis
  decomposition), with **one layer per hop**.
- Each batch is the disjoint union of each centre's **own** k-hop ego subgraph, built in
  NumPy from a CSR adjacency (`graph/ego.py`).
- k=0 is the same model with no convolution.

**Consequences.**
- A centre's embedding depends exactly on its k-hop family, which is what RQ1 compares.
- Pure-Python PyG is enough; we need no compiled extensions.
- Batches are small: family neighbourhoods are tens of nodes at k=2, and peak GPU memory
  is under 100 MB on 42k nodes.
- Nodes shared by several centres are computed more than once. That's acceptable for
  family-sized neighbourhoods; full-graph inference would be faster if it ever matters.
- Neighbours are not sampled: every neighbour within k hops is used. Families are small
  enough that this is fine. Very large families (e.g. 15 children) are taken in full.
