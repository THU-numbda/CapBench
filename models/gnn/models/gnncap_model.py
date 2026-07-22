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
        node_feature_mean: Optional[Sequence[float]] = None,
        node_feature_std: Optional[Sequence[float]] = None,
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

        if (node_feature_mean is None) != (node_feature_std is None):
            raise ValueError("node_feature_mean and node_feature_std must be set together")
        if node_feature_mean is None:
            feature_mean = torch.zeros(node_feature_dim, dtype=torch.float32)
            feature_std = torch.ones(node_feature_dim, dtype=torch.float32)
        else:
            feature_mean = torch.as_tensor(node_feature_mean, dtype=torch.float32)
            feature_std = torch.as_tensor(node_feature_std, dtype=torch.float32)
            if feature_mean.numel() != node_feature_dim or feature_std.numel() != node_feature_dim:
                raise ValueError(
                    "node_feature_mean and node_feature_std must match node_feature_dim"
                )
            if torch.any(feature_std <= 0.0):
                raise ValueError("node_feature_std values must be positive")
        self.register_buffer("node_feature_mean", feature_mean.reshape(1, -1))
        self.register_buffer("node_feature_std", feature_std.reshape(1, -1))

        dims = [node_feature_dim] + list(hidden_dims)
        self.convs = nn.ModuleList()
        self.gcn_residuals = nn.ModuleList()
        self.gat_residuals = nn.ModuleList()
        for in_dim, out_dim in zip(dims[:-1], dims[1:]):
            self.convs.append(self._build_conv_layer(in_dim, out_dim))
            if self.conv_type == "gcn":
                # Dense physical graphs can make the normalized neighborhood
                # term dominate the self-loop.  A learned root projection is
                # the standard residual remedy and preserves each cuboid's
                # own geometry alongside its neighborhood aggregate.
                self.gcn_residuals.append(
                    nn.Linear(in_dim, out_dim, bias=False)
                )
            elif self.conv_type == "gat":
                self.gat_residuals.append(
                    nn.Linear(in_dim, out_dim, bias=False)
                )

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

    def _normalize_node_features(self, features: torch.Tensor) -> torch.Tensor:
        return (features - self.node_feature_mean) / self.node_feature_std

    def _load_from_state_dict(
        self,
        state_dict,
        prefix,
        local_metadata,
        strict,
        missing_keys,
        unexpected_keys,
        error_msgs,
    ):
        # Checkpoints created before optional feature standardization do not
        # contain these buffers. Inject the constructor defaults (or the
        # train-split statistics restored from Lightning hyperparameters) so
        # strict loading remains backward-compatible.
        for name in ("node_feature_mean", "node_feature_std"):
            key = prefix + name
            if key not in state_dict:
                state_dict[key] = getattr(self, name)
        super()._load_from_state_dict(
            state_dict,
            prefix,
            local_metadata,
            strict,
            missing_keys,
            unexpected_keys,
            error_msgs,
        )

    def reset_parameters(self):
        for module in self.modules():
            if module is not self and hasattr(module, "reset_parameters"):
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

        node_embeddings = self._normalize_node_features(x)
        for layer_index, conv in enumerate(self.convs):
            layer_input = node_embeddings
            if self.conv_type == "gcn":
                # GCNConv accepts one scalar weight per edge.  Use the graph's
                # center-to-center distance (edge feature 0) so the GCN does
                # not collapse a dense physical graph into an unweighted
                # neighborhood average.  ``1 / (1 + d)`` is positive,
                # bounded, and keeps self-loop weights on the same scale.
                edge_weight = torch.reciprocal(
                    1.0 + edge_attr[:, 0].clamp_min(0.0)
                )
                neighborhood_embeddings = conv(
                    node_embeddings,
                    edge_index,
                    edge_weight=edge_weight,
                )
                node_embeddings = (
                    neighborhood_embeddings
                    + self.gcn_residuals[layer_index](layer_input)
                )
            else:
                node_embeddings = conv(layer_input, edge_index, edge_attr)
                if self.conv_type == "gat":
                    node_embeddings = (
                        node_embeddings
                        + self.gat_residuals[layer_index](layer_input)
                    )
            node_embeddings = F.relu(node_embeddings)

        net_embeddings = self.net_aggregator(node_embeddings, net_attention_mask)
        return self.predictor(net_embeddings)


__all__ = ["GNNCapModel"]
