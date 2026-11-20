# 0002 — PyTorch 2.14 from the CUDA 12.6 index

**Context.** The training GPU is a GTX 1070 (sm_61). PyTorch's CUDA 12.8+ and 13.x
wheels no longer include Pascal kernels. The cu126 wheels still do, and 2.14 is the last
release that publishes them. Python is 3.13, because the library requires it.

**Decision.** Pin `torch==2.14.1+cu126`; `pyproject.toml` requires `torch>=2.14,<2.15`.
Document "install torch from the cu126 index first" (README, HARDWARE.md). Pin
`torch-geometric==2.8.1`.

**Consequences.**
- Working CUDA on the 1070, verified with `torch.cuda.get_device_capability() == (6, 1)`.
- We're on the last Pascal-capable line, so a later PyTorch upgrade means a source
  build or another GPU.
- CI and other machines must also use the cu126 index (or CPU wheels) to get the same
  version.
