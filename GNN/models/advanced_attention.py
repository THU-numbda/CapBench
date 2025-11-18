"""
Advanced attention mechanisms for GNN-Cap with relative positional encoding
and cross-modal attention between node and edge features.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, GATv2Conv
from torch_geometric.utils import softmax
from typing import Optional, Tuple, Dict, Any
import math


class RelativePositionalAttention(nn.Module):
    """
    Attention mechanism with relative positional encoding for spatial awareness.
    """

    def __init__(self,
                 embed_dim: int,
                 num_heads: int = 8,
                 max_distance: int = 100,
                 dropout: float = 0.1):
        """
        Initialize relative positional attention.

        Args:
            embed_dim: Embedding dimension
            num_heads: Number of attention heads
            max_distance: Maximum distance for positional encoding
            dropout: Dropout rate
        """
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.max_distance = max_distance
        self.scale = self.head_dim ** -0.5

        assert self.head_dim * num_heads == embed_dim, "embed_dim must be divisible by num_heads"

        # Linear projections for query, key, value
        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)

        # Relative positional encoding
        self.relative_pos_k = nn.Parameter(torch.randn(max_distance * 2 + 1, num_heads, self.head_dim))
        self.relative_pos_v = nn.Parameter(torch.randn(max_distance * 2 + 1, num_heads, self.head_dim))

        # Output projection
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        self.dropout = nn.Dropout(dropout)

        self._init_weights()

    def _init_weights(self):
        """Initialize weights."""
        for module in [self.q_proj, self.k_proj, self.v_proj, self.out_proj]:
            nn.init.xavier_uniform_(module.weight)
            nn.init.constant_(module.bias, 0)

        nn.init.xavier_uniform_(self.relative_pos_k)
        nn.init.xavier_uniform_(self.relative_pos_v)

    def forward(self,
                x: torch.Tensor,
                edge_index: torch.Tensor,
                edge_attr: Optional[torch.Tensor] = None,
                node_pos: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass with relative positional attention.

        Args:
            x: Node features [num_nodes, embed_dim]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge attributes [num_edges, edge_dim]
            node_pos: Node positions [num_nodes, 3] for distance computation

        Returns:
            Updated node features [num_nodes, embed_dim]
        """
        num_nodes = x.size(0)

        # Linear projections
        q = self.q_proj(x).view(num_nodes, self.num_heads, self.head_dim)
        k = self.k_proj(x).view(num_nodes, self.num_heads, self.head_dim)
        v = self.v_proj(x).view(num_nodes, self.num_heads, self.head_dim)

        # Compute relative positions if node positions are provided
        if node_pos is not None:
            row, col = edge_index
            rel_pos = node_pos[row] - node_pos[col]  # [num_edges, 3]
            distances = torch.norm(rel_pos, dim=-1, keepdim=True)  # [num_edges, 1]

            # Convert distances to discrete bins for positional encoding
            distance_bins = torch.clamp(
                (distances * 10).long(),  # Scale and convert to indices
                -self.max_distance,
                self.max_distance
            ).squeeze(-1) + self.max_distance  # Shift to [0, 2*max_distance]

            # Get relative positional encodings
            rel_pos_k = self.relative_pos_k[distance_bins]  # [num_edges, num_heads, head_dim]
            rel_pos_v = self.relative_pos_v[distance_bins]  # [num_edges, num_heads, head_dim]
        else:
            # Default positional encoding (zeros)
            num_edges = edge_index.size(1)
            rel_pos_k = torch.zeros(num_edges, self.num_heads, self.head_dim, device=x.device)
            rel_pos_v = torch.zeros(num_edges, self.num_heads, self.head_dim, device=x.device)

        # Compute attention scores
        row, col = edge_index

        # Standard attention: q_i · k_j
        attn_scores = (q[row] * k[col]).sum(dim=-1) * self.scale  # [num_edges, num_heads]

        # Add relative positional attention: q_i · k_(j-i)
        rel_attn_scores = (q[row] * rel_pos_k).sum(dim=-1) * self.scale  # [num_edges, num_heads]
        attn_scores = attn_scores + rel_attn_scores

        # Apply edge attributes if provided
        if edge_attr is not None:
            # Project edge attributes to match head dimension
            if hasattr(self, 'edge_proj'):
                edge_proj = self.edge_proj(edge_attr)  # [num_edges, embed_dim]
            else:
                edge_dim = edge_attr.size(-1)
                self.edge_proj = nn.Linear(edge_dim, embed_dim).to(x.device)
                edge_proj = self.edge_proj(edge_attr)

            edge_proj = edge_proj.view(-1, self.num_heads, self.head_dim)
            edge_attn = (q[row] * edge_proj).sum(dim=-1) * self.scale
            attn_scores = attn_scores + edge_attn

        # Softmax attention weights
        attn_weights = softmax(attn_scores, row, num_nodes=num_nodes)  # [num_edges, num_heads]
        attn_weights = self.dropout(attn_weights)

        # Apply attention to values
        out = torch.zeros_like(v)  # [num_nodes, num_heads, head_dim]

        # Standard value contribution
        out.index_add_(0, row, attn_weights.unsqueeze(-1) * v[col])

        # Relative positional value contribution
        out.index_add_(0, row, attn_weights.unsqueeze(-1) * rel_pos_v)

        # Concatenate heads and output projection
        out = out.view(num_nodes, self.embed_dim)
        out = self.out_proj(out)

        return out


class CrossModalAttention(nn.Module):
    """
    Cross-modal attention between node and edge features.
    """

    def __init__(self,
                 node_dim: int,
                 edge_dim: int,
                 hidden_dim: int = 64,
                 num_heads: int = 4,
                 dropout: float = 0.1):
        """
        Initialize cross-modal attention.

        Args:
            node_dim: Node feature dimension
            edge_dim: Edge feature dimension
            hidden_dim: Hidden dimension for attention computation
            num_heads: Number of attention heads
            dropout: Dropout rate
        """
        super().__init__()
        self.node_dim = node_dim
        self.edge_dim = edge_dim
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        # Node-to-edge attention projections
        self.node_to_edge_q = nn.Linear(node_dim, hidden_dim)
        self.node_to_edge_k = nn.Linear(node_dim, hidden_dim)
        self.node_to_edge_v = nn.Linear(node_dim, hidden_dim)

        # Edge-to-node attention projections
        self.edge_to_node_q = nn.Linear(edge_dim, hidden_dim)
        self.edge_to_node_k = nn.Linear(edge_dim, hidden_dim)
        self.edge_to_node_v = nn.Linear(edge_dim, hidden_dim)

        # Output projections
        self.node_output = nn.Linear(hidden_dim, node_dim)
        self.edge_output = nn.Linear(hidden_dim, edge_dim)

        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5

        self._init_weights()

    def _init_weights(self):
        """Initialize weights."""
        modules = [self.node_to_edge_q, self.node_to_edge_k, self.node_to_edge_v,
                  self.edge_to_node_q, self.edge_to_node_k, self.edge_to_node_v,
                  self.node_output, self.edge_output]

        for module in modules:
            nn.init.xavier_uniform_(module.weight)
            nn.init.constant_(module.bias, 0)

    def forward(self,
                x: torch.Tensor,
                edge_attr: torch.Tensor,
                edge_index: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass with cross-modal attention.

        Args:
            x: Node features [num_nodes, node_dim]
            edge_attr: Edge features [num_edges, edge_dim]
            edge_index: Edge connectivity [2, num_edges]

        Returns:
            Tuple of (updated_node_features, updated_edge_features)
        """
        num_nodes, num_edges = x.size(0), edge_attr.size(0)

        # Node-to-edge attention
        # Query: edge features, Key/Value: node features
        edge_q = self.edge_to_node_q(edge_attr).view(num_edges, self.num_heads, self.head_dim)
        node_k = self.node_to_edge_k(x).view(num_nodes, self.num_heads, self.head_dim)
        node_v = self.node_to_edge_v(x).view(num_nodes, self.num_heads, self.head_dim)

        row, col = edge_index

        # Compute attention scores for edge updates
        edge_attn_scores = (edge_q.unsqueeze(1) * torch.stack([node_k[row], node_k[col]], dim=1)).sum(-1) * self.scale
        edge_attn_scores = edge_attn_scores.view(num_edges * 2, self.num_heads)  # [2*num_edges, num_heads]

        # Softmax over connected nodes for each edge
        edge_attn_weights = F.softmax(edge_attn_scores, dim=0)
        edge_attn_weights = self.dropout(edge_attn_weights)

        # Apply attention to node values
        edge_values = torch.stack([node_v[row], node_v[col]], dim=1)  # [num_edges, 2, num_heads, head_dim]
        edge_values = edge_values.view(num_edges * 2, self.num_heads, self.head_dim)

        edge_attention_out = (edge_attn_weights.unsqueeze(-1) * edge_values).sum(0)  # [num_heads, head_dim]
        edge_attention_out = edge_attention_out.view(1, self.num_heads * self.head_dim).expand(num_edges, -1)

        # Update edge features
        updated_edge_attr = self.edge_output(edge_attention_out) + edge_attr

        # Edge-to-node attention
        # Query: node features, Key/Value: edge features
        node_q = self.node_to_edge_q(x).view(num_nodes, self.num_heads, self.head_dim)
        edge_k = self.edge_to_node_k(edge_attr).view(num_edges, self.num_heads, self.head_dim)
        edge_v = self.edge_to_node_v(edge_attr).view(num_edges, self.num_heads, self.head_dim)

        # Collect edge information for each node
        node_attn_scores = []
        node_attn_values = []

        for node_idx in range(num_nodes):
            # Find edges connected to this node
            connected_edges = (row == node_idx) | (col == node_idx)
            if connected_edges.sum() > 0:
                connected_edge_k = edge_k[connected_edges]  # [num_connected, num_heads, head_dim]
                connected_edge_v = edge_v[connected_edges]  # [num_connected, num_heads, head_dim]
                node_q_expanded = node_q[node_idx].unsqueeze(0)  # [1, num_heads, head_dim]

                # Attention scores
                attn_scores = (node_q_expanded * connected_edge_k).sum(-1) * self.scale  # [num_connected, num_heads]
                attn_weights = F.softmax(attn_scores, dim=0)
                attn_weights = self.dropout(attn_weights)

                # Apply attention
                attn_out = (attn_weights.unsqueeze(-1) * connected_edge_v).sum(0)  # [num_heads, head_dim]

                node_attn_scores.append(attn_weights)
                node_attn_values.append(attn_out)
            else:
                # No connected edges
                node_attn_scores.append(torch.zeros(1, self.num_heads, device=x.device))
                node_attn_values.append(torch.zeros(self.num_heads, self.head_dim, device=x.device))

        # Stack node attention outputs
        node_attention_out = torch.stack(node_attn_values, dim=0)  # [num_nodes, num_heads, head_dim]
        node_attention_out = node_attention_out.view(num_nodes, self.num_heads * self.head_dim)

        # Update node features
        updated_x = self.node_output(node_attention_out) + x

        return updated_x, updated_edge_attr


class EnhancedGATConv(nn.Module):
    """
    Enhanced GAT convolution with advanced attention mechanisms.
    """

    def __init__(self,
                 in_channels: int,
                 out_channels: int,
                 heads: int = 8,
                 concat: bool = True,
                 dropout: float = 0.1,
                 edge_dim: Optional[int] = None,
                 use_relative_pos: bool = True,
                 use_cross_modal: bool = True,
                 max_distance: int = 100):
        """
        Initialize enhanced GAT convolution.

        Args:
            in_channels: Input channels
            out_channels: Output channels per head
            heads: Number of attention heads
            concat: Whether to concatenate heads
            dropout: Dropout rate
            edge_dim: Edge feature dimension
            use_relative_pos: Whether to use relative positional attention
            use_cross_modal: Whether to use cross-modal attention
            max_distance: Maximum distance for relative positional encoding
        """
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.heads = heads
        self.concat = concat
        self.dropout = dropout
        self.edge_dim = edge_dim
        self.use_relative_pos = use_relative_pos
        self.use_cross_modal = use_cross_modal

        # Output dimension after concatenation or mean
        if concat:
            self.output_dim = out_channels * heads
        else:
            self.output_dim = out_channels

        # Base GATv2 convolution for standard attention
        self.gat_conv = GATv2Conv(
            in_channels=in_channels,
            out_channels=out_channels,
            heads=heads,
            concat=concat,
            dropout=dropout,
            edge_dim=edge_dim
        )

        # Advanced attention mechanisms
        if use_relative_pos:
            self.relative_attention = RelativePositionalAttention(
                embed_dim=self.output_dim,
                num_heads=heads if not concat else heads,
                max_distance=max_distance,
                dropout=dropout
            )

        if use_cross_modal and edge_dim is not None:
            self.cross_attention = CrossModalAttention(
                node_dim=self.output_dim,
                edge_dim=edge_dim,
                hidden_dim=min(self.output_dim, edge_dim),
                num_heads=min(heads, 4),
                dropout=dropout
            )

        # Layer normalization
        self.layer_norm = nn.LayerNorm(self.output_dim)

        # Residual connection projection if needed
        if in_channels != self.output_dim:
            self.residual_proj = nn.Linear(in_channels, self.output_dim)
        else:
            self.residual_proj = nn.Identity()

    def forward(self,
                x: torch.Tensor,
                edge_index: torch.Tensor,
                edge_attr: Optional[torch.Tensor] = None,
                node_pos: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass with enhanced attention.

        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge attributes [num_edges, edge_dim]
            node_pos: Node positions [num_nodes, 3]

        Returns:
            Updated node features [num_nodes, output_dim]
        """
        # Store input for residual connection
        residual = self.residual_proj(x)

        # Base GAT convolution
        out = self.gat_conv(x, edge_index, edge_attr)

        # Apply relative positional attention
        if self.use_relative_pos and node_pos is not None:
            out = self.relative_attention(out, edge_index, edge_attr, node_pos)

        # Apply cross-modal attention
        if self.use_cross_modal and edge_attr is not None:
            out, edge_attr = self.cross_attention(out, edge_attr, edge_index)

        # Add residual connection
        out = out + residual

        # Apply layer normalization
        out = self.layer_norm(out)

        return out


def create_enhanced_attention_layer(layer_type: str, **kwargs) -> nn.Module:
    """
    Factory function to create enhanced attention layers.

    Args:
        layer_type: Type of attention layer ('relative_pos', 'cross_modal', 'enhanced_gat')
        **kwargs: Additional arguments for layer initialization

    Returns:
        Initialized attention layer
    """
    if layer_type == 'relative_pos':
        return RelativePositionalAttention(**kwargs)
    elif layer_type == 'cross_modal':
        return CrossModalAttention(**kwargs)
    elif layer_type == 'enhanced_gat':
        return EnhancedGATConv(**kwargs)
    else:
        raise ValueError(f"Unknown layer type: {layer_type}")


# Utility functions for attention analysis
def analyze_attention_weights(model: nn.Module,
                            x: torch.Tensor,
                            edge_index: torch.Tensor,
                            edge_attr: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
    """
    Analyze attention weights in the model for interpretability.

    Args:
        model: GNN model with attention mechanisms
        x: Node features
        edge_index: Edge connectivity
        edge_attr: Edge attributes

    Returns:
        Dictionary containing attention weights from different layers
    """
    attention_weights = {}
    hooks = []

    def hook_fn(name):
        def hook(module, input, output):
            if hasattr(module, 'attention_weights'):
                attention_weights[name] = module.attention_weights.detach()
        return hook

    # Register hooks for attention layers
    for name, module in model.named_modules():
        if isinstance(module, (RelativePositionalAttention, CrossModalAttention)):
            hooks.append(module.register_forward_hook(hook_fn(name)))

    # Forward pass
    with torch.no_grad():
        model(x, edge_index, edge_attr)

    # Remove hooks
    for hook in hooks:
        hook.remove()

    return attention_weights


def visualize_attention_importance(attention_weights: Dict[str, torch.Tensor],
                                 edge_index: torch.Tensor,
                                 save_path: Optional[str] = None):
    """
    Visualize attention importance for model interpretability.

    Args:
        attention_weights: Dictionary of attention weights
        edge_index: Edge connectivity
        save_path: Optional path to save visualization
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Attention Weights Analysis', fontsize=16)

        for i, (layer_name, weights) in enumerate(attention_weights.items()):
            if i >= 4:  # Limit to 4 subplots
                break

            ax = axes[i // 2, i % 2]

            # Average attention across heads
            if weights.dim() > 1:
                avg_weights = weights.mean(dim=-1).cpu().numpy()
            else:
                avg_weights = weights.cpu().numpy()

            # Plot histogram of attention weights
            ax.hist(avg_weights.flatten(), bins=50, alpha=0.7, edgecolor='black')
            ax.set_title(f'{layer_name} - Attention Distribution')
            ax.set_xlabel('Attention Weight')
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.show()

    except ImportError:
        print("Matplotlib and seaborn required for visualization. Install with: pip install matplotlib seaborn")