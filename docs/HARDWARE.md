# Hardware

Target: an **NVIDIA GTX 1070** (8 GB, Pascal, compute capability **6.1 / sm_61**) for
training and inference. All tests are **CPU-only**.

## PyTorch and CUDA for Pascal (checked 2026-11-20)

- PyTorch's CUDA 12.8 and 12.9 builds dropped Maxwell and Pascal starting with 2.8.
  The CUDA 13 builds don't support them either.
- The **CUDA 12.6 (`cu126`) wheels** still include sm_50, sm_60 and sm_61.
- PyTorch has announced that **2.14 is the last release with `cu126` wheels**. From
  2.15, Pascal needs a source build.

So we pin **`torch==2.14.1` from the `cu126` index**, and `pyproject.toml` allows
`torch>=2.14,<2.15`.

Checked on this machine:
```
torch 2.14.1+cu126, cuda available: True, device capability (6, 1)
arch list: sm_50 sm_60 sm_61 sm_70 sm_75 sm_80 sm_86 sm_90
GPU: NVIDIA GeForce GTX 1070, driver 582.78
```

### Install

```bash
uv sync
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability(0))"
```

`pyproject.toml` (`[tool.uv.sources]` / `[[tool.uv.index]]`) takes `torch` from the
**cu126** index on Windows and from the **CPU** index on Linux (tests are CPU-only, and
it avoids the multi-GB CUDA wheels). `uv.lock` records both. Plain PyPI would give
CPU-only torch on Windows and cu128+ (no Pascal) on Linux. The NVIDIA driver must
support CUDA 12.6 (driver ≥ 560 on Windows; 582.78 is installed).

Without uv, install torch from the cu126 index **first**, then the project:
`pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126`, then
`pip install -e . --group dev` (pip ≥ 25.1).

Sources:
- [PyTorch dev-discuss: Maxwell and Pascal removed from CUDA 12.8/12.9 builds](https://dev-discuss.pytorch.org/t/cuda-toolkit-version-and-architecture-support-update-maxwell-and-pascal-architecture-support-removed-in-cuda-12-8-and-12-9-builds/3128)
- [PyTorch dev-discuss: CUDA 12.6 wheels no longer published from 2.15](https://dev-discuss.pytorch.org/t/notice-cuda-12-6-wheels-will-no-longer-be-published-from-pytorch-2-15-drops-maxwell-pascal-volta/3432)
- [pytorch/pytorch#157517](https://github.com/pytorch/pytorch/issues/157517) (sm_61 on CUDA 12.8 builds)
- the `https://download.pytorch.org/whl/cu126/torch/` index, which lists `2.14.1+cu126` for cp313 / win_amd64

## PyTorch Geometric

- `torch-geometric==2.8.1` is pure Python and needs no compiled extensions.
- `RGCNConv` works without `pyg-lib` or `torch-sparse`: it falls back to a per-relation
  loop, which is fine with 3 relations.
- We don't use PyG's `NeighborLoader`, which needs `pyg-lib` or `torch-sparse` and has
  fragile Windows / Python 3.13 wheels. Mini-batches are per-centre k-hop ego subgraphs
  built from a CSR adjacency (`graph/ego.py`, ADR 0003).

## Memory and time

Measured on the GTX 1070 with `dev_synthetic.yaml`: 42k people, 168k directed edges,
batch 256, 20k anchors per epoch, 3 epochs.

| | k=0 | k=1 | k=2 |
| --- | --- | --- | --- |
| time per epoch | ~5 s | ~21 s | ~61 s |
| peak GPU memory | < 100 MB for all |  |  |

- Family neighbourhoods are small, so a 256-centre batch at k=2 is a few thousand nodes.
- The **bottleneck is the CPU**: augmenting and featurising records in Python. The GPU
  is barely used.
- 150k people fit easily. Epoch time depends on `anchors_per_epoch`, not on the graph size.
- If training gets too slow on real data, cache base features and augment at the
  feature level, or use DataLoader workers. That's a performance change, not a modelling one.

## RQ2 local models (Ollama, 8 GB)

A 7–8B instruct model at 4-bit quantisation (e.g. `qwen2.5:7b-instruct`, about 5 GB)
fits in 8 GB VRAM with a 4–8k context. The k=2 contexts are a few hundred to a few
thousand tokens. Larger models go through the `openai_compat` backend (OpenRouter or
the cluster).
