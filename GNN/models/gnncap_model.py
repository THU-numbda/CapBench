"""
Simplified two-layer GNN-Cap model.

Only the functionality required to train 2-layer models with self-attention
aggregation and selectable GCN/GAT/GATv2 layers is retained.
"""

from typing import Optional, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, GATv2Conv, GCNConv

from .attention_pool import SelfAttentionNetAggregator


class GNNCapModel(nn.Module):
    """Two-layer GNN with optional GCN, GAT, or GATv2 convolutions."""

    SUPPORTED_CONVS = ("gcn", "gat", "gatv2")

    def __init__(
        self,
        node_feature_dim: int = 3,
        edge_feature_dim: int = 7,
        hidden_dims: Sequence[int] = (128, 256),
        conv_type: str = "gat",
        heads: int = 4,
        aggregation_hidden_dim: int = 128,
    ):
        super().__init__()
        hidden_dims = tuple(hidden_dims)
        if len(hidden_dims) != 2:
            raise ValueError("Exactly two hidden dimensions are required for the 2-layer model.")
        conv_type = conv_type.lower()
        if conv_type not in self.SUPPORTED_CONVS:
            raise ValueError(f"Unsupported conv_type '{conv_type}'. Expected one of {self.SUPPORTED_CONVS}.")

        self.conv_type = conv_type
        self.edge_feature_dim = edge_feature_dim
        self.heads = heads if conv_type in {"gat", "gatv2"} else 1

        dims = [node_feature_dim] + list(hidden_dims)
        self.convs = nn.ModuleList()
        for in_dim, out_dim in zip(dims[:-1], dims[1:]):
            self.convs.append(self._build_conv_layer(in_dim, out_dim))

        self.net_aggregator = SelfAttentionNetAggregator(
            node_dim=hidden_dims[-1],
            hidden_dim=aggregation_hidden_dim,
        )
        self.predictor = nn.Linear(hidden_dims[-1], 1)
        self.reset_parameters()

    def _build_conv_layer(self, in_dim: int, out_dim: int):
        if self.conv_type == "gcn":
            return GCNConv(in_dim, out_dim, add_self_loops=True, normalize=True)

        self._validate_attention_heads(out_dim)
        out_per_head = out_dim // self.heads
        conv_args = dict(
            in_channels=in_dim,
            out_channels=out_per_head,
            heads=self.heads,
            concat=True,
            dropout=0.0,
            edge_dim=self.edge_feature_dim,
        )
        if self.conv_type == "gat":
            return GATConv(**conv_args)
        return GATv2Conv(**conv_args)

    def _validate_attention_heads(self, out_dim: int):
        if out_dim % self.heads != 0:
            raise ValueError(
                f"Hidden dimension {out_dim} must be divisible by the number of heads {self.heads}."
            )

    def reset_parameters(self):
        for module in self.modules():
            if hasattr(module, "reset_parameters"):
                module.reset_parameters()
        nn.init.xavier_uniform_(self.predictor.weight)
        if self.predictor.bias is not None:
            nn.init.zeros_(self.predictor.bias)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        net_attention_mask: Optional[torch.Tensor],
    ) -> torch.Tensor:
        if net_attention_mask is None:
            raise ValueError("net_attention_mask is required for self-attention aggregation.")

        node_embeddings = x
        for conv in self.convs:
            if self.conv_type == "gcn":
                node_embeddings = conv(node_embeddings, edge_index)
            else:
                node_embeddings = conv(node_embeddings, edge_index, edge_attr)
            node_embeddings = F.relu(node_embeddings)

        net_embeddings = self.net_aggregator(node_embeddings, net_attention_mask)
        return self.predictor(net_embeddings)


__all__ = ["GNNCapModel"]
