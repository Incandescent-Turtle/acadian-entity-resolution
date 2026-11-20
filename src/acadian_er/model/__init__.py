"""R-GCN encoder (k = 0 / 1 / 2 hops), contrastive training and embedding."""

from .rgcn import RGCNEncoder
from .train import TrainedEncoder, embed, load_encoder, train_encoder

__all__ = ["RGCNEncoder", "TrainedEncoder", "embed", "load_encoder", "train_encoder"]
