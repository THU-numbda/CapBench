#!/usr/bin/env python3
"""
Minimal self-attention pooling utilities used by the slimmed-down trainer.

Only the functionality required to aggregate node embeddings to per-net
representations is retained.
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class SelfAttentionNetAggregator(nn.Module):
    """Self-attention pooling where each node receives a learned importance score."""

    def __init__(self, node_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.node_dim = node_dim
        self.score_network = nn.Sequential(
            nn.Linear(node_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(
        self,
        node_embeddings: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        if attention_mask.dtype != torch.bool:
            raise ValueError("attention_mask must be a boolean tensor")
        scores = self.score_network(node_embeddings).squeeze(-1)
        num_nets = attention_mask.shape[0]
        aggregated = node_embeddings.new_zeros((num_nets, self.node_dim))
        for net_idx in range(num_nets):
            net_mask = attention_mask[net_idx]
            if not torch.any(net_mask):
                continue
            net_scores = scores[net_mask]
            attn = F.softmax(net_scores, dim=0)
            weighted_nodes = node_embeddings[net_mask] * attn.unsqueeze(-1)
            aggregated[net_idx] = weighted_nodes.sum(dim=0)
        return aggregated


def build_attention_mask(
    node_net_index: Optional[torch.Tensor],
    num_nets: Optional[int],
) -> Optional[torch.Tensor]:
    """
    Construct a boolean mask relating each net to the nodes it owns.

    Args:
        node_net_index: Tensor [num_nodes] with net index per node (-1 for
            nodes without a valid net).
        num_nets: Total number of nets represented in the graph.

    Returns:
        Boolean tensor [num_nets, num_nodes] or ``None`` if metadata is missing.
    """
    if node_net_index is None or num_nets is None or num_nets <= 0:
        return None

    num_nodes = node_net_index.shape[0]
    device = node_net_index.device
    mask = torch.zeros((num_nets, num_nodes), dtype=torch.bool, device=device)

    valid = node_net_index >= 0
    if torch.any(valid):
        node_ids = torch.arange(num_nodes, device=device)[valid]
        nets = node_net_index[valid]
        mask[nets, node_ids] = True

    return mask
