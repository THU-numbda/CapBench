"""
Enhanced GNN-Cap model with deep residual architectures and advanced attention mechanisms.

This module implements highly expressive GNN architectures with:
- Residual connections for deeper networks
- Progressive dimension expansion/contraction
- Advanced attention mechanisms
- Layer normalization and gated message passing
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import MessagePassing
from torch_geometric.utils import add_self_loops, degree
from typing import Optional, List, Dict, Any, Union
import math

from models.attention_pool import NetAggregationBase, build_net_aggregator
from models.advanced_attention import EnhancedGATConv, create_enhanced_attention_layer


class GatedMessagePassing(MessagePassing):
    """
    Gated message passing mechanism for adaptive information flow.
    Similar to Gated Graph Convolutional Networks.
    """

    def __init__(self,
                 in_channels: int,
                 out_channels: int,
                 edge_dim: int = 7,
                 dropout: float = 0.1,
                 use_layer_norm: bool = True):
        """
        Initialize gated message passing.

        Args:
            in_channels: Input feature dimension
            out_channels: Output feature dimension
            edge_dim: Edge feature dimension
            dropout: Dropout rate
            use_layer_norm: Whether to use layer normalization
        """
        super().__init__(aggr='add')  # Use sum aggregation

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.edge_dim = edge_dim
        self.dropout = dropout
        self.use_layer_norm = use_layer_norm

        # Message computation networks
        self.msg_net = nn.Sequential(
            nn.Linear(in_channels * 2 + edge_dim, out_channels),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(out_channels, out_channels)
        )

        # Update network (GRU-style)
        self.update_net = nn.GRUCell(out_channels, in_channels)

        # Gating mechanism
        self.gate_net = nn.Sequential(
            nn.Linear(in_channels * 2 + out_channels, out_channels),
            nn.Sigmoid()
        )

        # Layer normalization
        if use_layer_norm:
            self.layer_norm = nn.LayerNorm(in_channels)

        self._init_weights()

    def _init_weights(self):
        """Initialize weights."""
        for module in [self.msg_net, self.gate_net]:
            for layer in module:
                if isinstance(layer, nn.Linear):
                    nn.init.xavier_uniform_(layer.weight)
                    nn.init.constant_(layer.bias, 0)

    def forward(self,
                x: torch.Tensor,
                edge_index: torch.Tensor,
                edge_attr: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass with gated message passing.

        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_dim]

        Returns:
            Updated node features [num_nodes, in_channels]
        """
        # Store input for residual connection
        residual = x

        # Propagate messages
        out = self.propagate(edge_index, x=x, edge_attr=edge_attr, size=(x.size(0), x.size(0)))

        # Apply gated update
        if self.use_layer_norm:
            out = self.layer_norm(out)

        return out

    def message(self, x_j: torch.Tensor, x_i: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
        """
        Compute messages between connected nodes.

        Args:
            x_j: Source node features
            x_i: Target node features
            edge_attr: Edge features

        Returns:
            Message tensor
        """
        # Concatenate node and edge features
        if edge_attr is not None:
            msg_input = torch.cat([x_i, x_j, edge_attr], dim=-1)
        else:
            # If no edge features, use zero padding
            edge_padding = torch.zeros(x_j.size(0), self.edge_dim, device=x_j.device)
            msg_input = torch.cat([x_i, x_j, edge_padding], dim=-1)

        # Compute message
        msg = self.msg_net(msg_input)
        return F.dropout(msg, p=self.dropout, training=self.training)

    def update(self, aggr_out: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """
        Update node features with gated mechanism.

        Args:
            aggr_out: Aggregated messages
            x: Original node features

        Returns:
            Updated node features
        """
        # Compute gate
        gate_input = torch.cat([x, aggr_out, x], dim=-1)  # Include x twice for compatibility
        gate = self.gate_net(gate_input)

        # Apply gated update using GRU cell
        updated = self.update_net(aggr_out, x)

        # Apply gate
        out = gate * updated + (1 - gate) * x

        return out


class ResidualGNNBlock(nn.Module):
    """
    Residual GNN block with optional dimension transformation.
    """

    def __init__(self,
                 in_channels: int,
                 out_channels: int,
                 edge_dim: int = 7,
                 dropout: float = 0.1,
                 use_layer_norm: bool = True,
                 attention_type: str = 'enhanced_gat',
                 num_heads: int = 8,
                 use_gated: bool = False):
        """
        Initialize residual GNN block.

        Args:
            in_channels: Input channels
            out_channels: Output channels
            edge_dim: Edge feature dimension
            dropout: Dropout rate
            use_layer_norm: Whether to use layer normalization
            attention_type: Type of attention mechanism
            num_heads: Number of attention heads
            use_gated: Whether to use gated message passing
        """
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.dropout = dropout
        self.use_layer_norm = use_layer_norm

        # Main message passing layer
        if attention_type == 'enhanced_gat':
            self.conv = EnhancedGATConv(
                in_channels=in_channels,
                out_channels=out_channels,
                heads=num_heads,
                concat=False,  # We handle concatenation manually if needed
                dropout=dropout,
                edge_dim=edge_dim,
                use_relative_pos=True,
                use_cross_modal=True
            )
        elif attention_type == 'gated':
            self.conv = GatedMessagePassing(
                in_channels=in_channels,
                out_channels=out_channels,
                edge_dim=edge_dim,
                dropout=dropout,
                use_layer_norm=use_layer_norm
            )
        else:
            # Default to standard linear transformation for simplicity
            self.conv = nn.Sequential(
                nn.Linear(in_channels + edge_dim, out_channels),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(out_channels, out_channels)
            )

        # Residual connection projection if dimensions don't match
        if in_channels != out_channels:
            self.residual_proj = nn.Linear(in_channels, out_channels)
        else:
            self.residual_proj = nn.Identity()

        # Layer normalization after block
        if use_layer_norm:
            self.layer_norm = nn.LayerNorm(out_channels)

        # Dropout for block output
        self.dropout_layer = nn.Dropout(dropout)

    def forward(self,
                x: torch.Tensor,
                edge_index: torch.Tensor,
                edge_attr: Optional[torch.Tensor] = None,
                node_pos: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass with residual connection.

        Args:
            x: Node features
            edge_index: Edge connectivity
            edge_attr: Edge features
            node_pos: Node positions

        Returns:
            Updated node features
        """
        # Store input for residual connection
        residual = self.residual_proj(x)

        # Apply main transformation
        if hasattr(self.conv, '__call__'):  # Check if it's a proper module
            if hasattr(self.conv, 'forward'):
                # Enhanced GAT with positional encoding
                if hasattr(self.conv, 'relative_attention'):
                    out = self.conv(x, edge_index, edge_attr, node_pos)
                else:
                    out = self.conv(x, edge_index, edge_attr)
            else:
                # Simple forward pass
                out = self.conv(x)
        else:
            out = self.conv

        # Add residual connection
        out = out + residual

        # Apply layer normalization
        if self.use_layer_norm:
            out = self.layer_norm(out)

        # Apply dropout
        out = self.dropout_layer(out)

        return out


class ProgressiveDimBlock(nn.Module):
    """
    Block with progressive dimension expansion and contraction.
    """

    def __init__(self,
                 in_channels: int,
                 expanded_channels: int,
                 out_channels: int,
                 edge_dim: int = 7,
                 dropout: float = 0.1):
        """
        Initialize progressive dimension block.

        Args:
            in_channels: Input channels
            expanded_channels: Intermediate expanded channels
            out_channels: Output channels
            edge_dim: Edge feature dimension
            dropout: Dropout rate
        """
        super().__init__()

        # Expansion phase
        self.expand = nn.Sequential(
            nn.Linear(in_channels, expanded_channels),
            nn.ReLU(),
            nn.BatchNorm1d(expanded_channels),
            nn.Dropout(dropout)
        )

        # Bottleneck with attention
        self.bottleneck = ResidualGNNBlock(
            in_channels=expanded_channels,
            out_channels=expanded_channels,
            edge_dim=edge_dim,
            dropout=dropout
        )

        # Contraction phase
        self.contract = nn.Sequential(
            nn.Linear(expanded_channels, out_channels),
            nn.ReLU(),
            nn.BatchNorm1d(out_channels),
            nn.Dropout(dropout)
        )

    def forward(self,
                x: torch.Tensor,
                edge_index: torch.Tensor,
                edge_attr: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass with progressive dimension transformation.

        Args:
            x: Node features
            edge_index: Edge connectivity
            edge_attr: Edge features

        Returns:
            Updated node features
        """
        # Expansion
        x_expanded = self.expand(x)

        # Bottleneck processing
        x_processed = self.bottleneck(x_expanded, edge_index, edge_attr)

        # Contraction
        out = self.contract(x_processed)

        return out


class EnhancedGNNCapModel(nn.Module):
    """
    Enhanced GNN-Cap model with deep residual architecture and advanced attention.

    Supports multiple architectural configurations:
    - Progressive dimension expansion/contraction
    - Residual connections for stability
    - Advanced attention mechanisms
    - Variable depth (2, 3, or 5 layers)
    """

    def __init__(self,
                 node_feature_dim: int = 3,
                 edge_feature_dim: int = 7,
                 layer_dims: List[int] = None,
                 prediction_type: str = 'total',
                 num_layers: int = 3,
                 use_progressive_dims: bool = True,
                 dropout: float = 0.1,
                 attention_type: str = 'enhanced_gat',
                 num_heads: int = 8,
                 use_gated_message_passing: bool = False,
                 aggregation: str = 'none',
                 aggregation_hidden_dim: int = 128,
                 # Enhanced parameters
                 max_depth: int = 3,
                 expansion_factor: float = 2.0,
                 use_advanced_attention: bool = True,
                 **kwargs):
        """
        Initialize enhanced GNN-Cap model.

        Args:
            node_feature_dim: Node feature dimension
            edge_feature_dim: Edge feature dimension
            layer_dims: Custom layer dimensions
            prediction_type: 'total' or 'coupling'
            num_layers: Number of GNN layers (2, 3, or 5)
            use_progressive_dims: Whether to use progressive dimension expansion
            dropout: Dropout rate
            attention_type: Type of attention mechanism
            num_heads: Number of attention heads
            use_gated_message_passing: Whether to use gated message passing
            aggregation: Net aggregation method
            aggregation_hidden_dim: Hidden dimension for aggregation
            max_depth: Maximum depth for architecture
            expansion_factor: Factor for dimension expansion
            use_advanced_attention: Whether to use advanced attention
            **kwargs: Additional parameters
        """
        super().__init__()

        self.node_feature_dim = node_feature_dim
        self.edge_feature_dim = edge_feature_dim
        self.prediction_type = prediction_type
        self.num_layers = min(num_layers, max_depth)
        self.use_progressive_dims = use_progressive_dims
        self.dropout = dropout
        self.attention_type = attention_type
        self.num_heads = num_heads
        self.use_gated_message_passing = use_gated_message_passing
        self.use_advanced_attention = use_advanced_attention

        # Validate architecture
        if self.num_layers not in [2, 3]:
            raise ValueError(f"num_layers must be 2 or 3, got {self.num_layers}")

        # Set layer dimensions
        if layer_dims is None:
            if self.num_layers == 2:
                layer_dims = [64, 128]  # Simple 2-layer architecture
            elif self.num_layers == 3:
                layer_dims = [64, 128, 256]  # 3-layer progressive expansion

        self.layer_dims = layer_dims
        assert len(layer_dims) == self.num_layers, f"layer_dims length {len(layer_dims)} must match num_layers {self.num_layers}"

        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(node_feature_dim, layer_dims[0]),
            nn.ReLU(),
            nn.BatchNorm1d(layer_dims[0]),
            nn.Dropout(dropout * 0.5)  # Lower dropout for input
        )

        # Build GNN layers
        self.gnn_layers = nn.ModuleList()
        self.layer_norms = nn.ModuleList()

        for i in range(self.num_layers):
            in_dim = layer_dims[i]
            out_dim = layer_dims[i]

            if use_progressive_dims and i < self.num_layers - 1:
                next_dim = layer_dims[i + 1]
                # Create progressive dimension block
                expanded_dim = int(max(in_dim, next_dim) * expansion_factor)
                layer = ProgressiveDimBlock(
                    in_channels=in_dim,
                    expanded_channels=expanded_dim,
                    out_channels=out_dim,
                    edge_dim=edge_feature_dim,
                    dropout=dropout
                )
            else:
                # Standard residual block
                layer = ResidualGNNBlock(
                    in_channels=in_dim,
                    out_channels=out_dim,
                    edge_dim=edge_feature_dim,
                    dropout=dropout,
                    attention_type=attention_type,
                    num_heads=num_heads,
                    use_gated=use_gated_message_passing
                )

            self.gnn_layers.append(layer)

            # Add layer normalization after each block
            self.layer_norms.append(nn.LayerNorm(out_dim))

        # Edge processing network (for coupling predictions)
        if prediction_type == 'coupling':
            self.edge_processor = nn.Sequential(
                nn.Linear(edge_feature_dim, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 32)
            )
            final_dim = layer_dims[-1] + 32  # Combine node and edge features
        else:
            final_dim = layer_dims[-1]

        # Output prediction heads
        if prediction_type == 'total':
            # Multi-scale prediction heads
            self.prediction_heads = nn.ModuleDict({
                'primary': nn.Sequential(
                    nn.Linear(final_dim, final_dim // 2),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(final_dim // 2, 1)
                ),
                'auxiliary': nn.Sequential(
                    nn.Linear(final_dim, final_dim // 4),
                    nn.ReLU(),
                    nn.Linear(final_dim // 4, 1)
                )
            })
        else:  # coupling
            self.edge_prediction = nn.Sequential(
                nn.Linear(final_dim, final_dim // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(final_dim // 2, 1)
            )

        # Net aggregation for total capacitance predictions
        if prediction_type == 'total' and aggregation != 'none':
            self.net_aggregator = build_net_aggregator(
                node_dim=layer_dims[-1],
                method=aggregation,
                hidden_dim=aggregation_hidden_dim
            )
        else:
            self.net_aggregator = None

        # Global features for context
        if use_advanced_attention:
            self.global_context = nn.Sequential(
                nn.Linear(layer_dims[-1], layer_dims[-1] // 2),
                nn.ReLU(),
                nn.Linear(layer_dims[-1] // 2, layer_dims[-1])
            )

        self._init_weights()

    def _init_weights(self):
        """Initialize model weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.BatchNorm1d):
                nn.init.constant_(module.weight, 1)
                nn.init.constant_(module.bias, 0)

    def forward(self,
                x: torch.Tensor,
                edge_index: torch.Tensor,
                edge_attr: torch.Tensor,
                edge_is_virtual: Optional[torch.Tensor] = None,
                net_attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through the enhanced GNN-Cap model.

        Args:
            x: Node features [num_nodes, node_feature_dim]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_feature_dim]
            edge_is_virtual: Virtual edge mask (unused in enhanced model)
            net_attention_mask: Net attention mask for aggregation

        Returns:
            Capacitance predictions
        """
        # Input projection
        x = self.input_proj(x)

        # Store intermediate representations for multi-scale features
        intermediate_features = []

        # Process through GNN layers
        for i, gnn_layer in enumerate(self.gnn_layers):
            # Store input for multi-scale features
            if i in [self.num_layers // 2, self.num_layers - 1]:
                intermediate_features.append(x)

            # Forward through GNN layer
            x = gnn_layer(x, edge_index, edge_attr)

            # Apply layer normalization
            x = self.layer_norms[i](x)

        # Global context enhancement
        if hasattr(self, 'global_context'):
            global_features = self.global_context(x.mean(dim=0, keepdim=True))
            x = x + global_features  # Add global context

        # Make predictions
        if self.prediction_type == 'total':
            # Node-level predictions
            if self.net_aggregator is not None:
                # Aggregate to net-level
                if net_attention_mask is not None:
                    x = self.net_aggregator(x, net_attention_mask)
                else:
                    # Fallback to mean pooling if no mask provided
                    x = x.mean(dim=0, keepdim=True)

            # Primary prediction
            primary_pred = self.prediction_heads['primary'](x)

            # Auxiliary prediction (for multi-task learning)
            if self.training:
                aux_pred = self.prediction_heads['auxiliary'](x)
                # Combine predictions during training
                predictions = primary_pred + 0.1 * aux_pred
            else:
                predictions = primary_pred

        else:  # coupling
            # Process edge features
            edge_features = self.edge_processor(edge_attr)

            # Gather node features for each edge
            row, col = edge_index
            node_features_for_edges = torch.cat([x[row], x[col]], dim=-1)

            # Combine node and edge features
            combined_features = torch.cat([node_features_for_edges, edge_features], dim=-1)

            # Edge-level predictions
            predictions = self.edge_prediction(combined_features)

        return predictions.squeeze(-1)

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive model information.

        Returns:
            Dictionary with model architecture details
        """
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)

        info = {
            'model_type': 'Enhanced GNN-Cap',
            'prediction_type': self.prediction_type,
            'num_layers': self.num_layers,
            'layer_dims': self.layer_dims,
            'attention_type': self.attention_type,
            'num_heads': self.num_heads,
            'use_progressive_dims': self.use_progressive_dims,
            'use_gated_message_passing': self.use_gated_message_passing,
            'use_advanced_attention': self.use_advanced_attention,
            'total_parameters': total_params,
            'trainable_parameters': trainable_params,
            'parameter_efficiency': trainable_params / total_params if total_params > 0 else 0,
            'architecture_features': [
                'Residual connections' if self.num_layers > 2 else None,
                'Progressive dimensions' if self.use_progressive_dims else None,
                'Advanced attention' if self.use_advanced_attention else None,
                'Gated message passing' if self.use_gated_message_passing else None,
                'Layer normalization',
                'Multi-scale features' if self.prediction_type == 'total' else None
            ]
        }

        # Remove None values
        info['architecture_features'] = [f for f in info['architecture_features'] if f is not None]

        return info


def create_enhanced_model(**kwargs) -> EnhancedGNNCapModel:
    """
    Factory function to create enhanced models with residual connections and advanced attention.

    Args:
        **kwargs: Additional model parameters (including num_layers, use_progressive_dims, etc.)

    Returns:
        Configured enhanced GNN-Cap model
    """
    # Set sensible defaults for enhanced model if not provided
    defaults = {
        'use_progressive_dims': True,
        'use_advanced_attention': True,
        'attention_type': 'enhanced_gat',
        'num_heads': 8,
        'use_gated_message_passing': False,
    }

    # Override defaults with user-provided kwargs
    for key, value in defaults.items():
        if key not in kwargs:
            kwargs[key] = value

    return EnhancedGNNCapModel(**kwargs)


# Compatibility wrapper for existing code
class GNNCapModel(EnhancedGNNCapModel):
    """
    Compatibility wrapper that extends EnhancedGNNCapModel for existing code.
    """

    def __init__(self,
                 node_feature_dim: int = 3,
                 edge_feature_dim: int = 7,
                 layer_1_dims: list = None,
                 layer_2_dims: list = None,
                 virtual_edge_dim_transform: int = 135,
                 virtual_edge_embedding: int = 368,
                 prediction_type: str = 'total',
                 use_virtual_edges: bool = True,
                 num_layers: int = 2,
                 use_attention: bool = False,
                 heads: int = 4,
                 attention_type: str = 'gat',
                 aggregation: str = 'none',
                 aggregation_hidden_dim: int = 128,
                 **kwargs):
        """
        Initialize with backward-compatible interface.
        """
        # Convert old parameters to new format
        enhanced_kwargs = kwargs.copy()

        # Handle attention type conversion
        if use_attention and attention_type == 'gat':
            enhanced_kwargs['attention_type'] = 'enhanced_gat'
            enhanced_kwargs['use_advanced_attention'] = True

        # Set num_heads
        enhanced_kwargs['num_heads'] = heads

        # Handle layer dimensions (convert old format)
        if layer_1_dims and layer_2_dims:
            # This is the old format with separate layer dimensions
            enhanced_kwargs['layer_dims'] = layer_1_dims[:num_layers]
        elif layer_1_dims:
            enhanced_kwargs['layer_dims'] = layer_1_dims[:num_layers]

        # Set progressive dimensions based on complexity
        if num_layers >= 3:
            enhanced_kwargs['use_progressive_dims'] = True

        # Initialize enhanced model
        super().__init__(
            node_feature_dim=node_feature_dim,
            edge_feature_dim=edge_feature_dim,
            prediction_type=prediction_type,
            num_layers=num_layers,
            aggregation=aggregation,
            aggregation_hidden_dim=aggregation_hidden_dim,
            **enhanced_kwargs
        )