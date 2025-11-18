"""
GNN-Cap Model Architecture

Implements the Graph Neural Network architecture from:
"GNN-Cap: Chip-Scale Interconnect Capacitance Extraction Using Graph Neural Network"
IEEE TCAD 2024

Based on Algorithm 1 and Section III-D of the paper.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import MessagePassing, GATConv, GATv2Conv
from typing import Optional, Tuple, List

from .attention_pool import build_net_aggregator


# Create a compatibility wrapper for PyG's MLP that matches our interface
class MLP(nn.Module):
    """Custom MLP implementation without BatchNorm for batch_size=1 compatibility"""

    def __init__(self, input_dim: int, hidden_dims: List[int], output_dim: int, activation='relu'):
        super(MLP, self).__init__()

        self.layers = nn.ModuleList()
        self.activation = activation

        # Build layer list
        layer_dims = [input_dim] + hidden_dims + [output_dim]

        for i in range(len(layer_dims) - 1):
            self.layers.append(nn.Linear(layer_dims[i], layer_dims[i + 1]))

    def forward(self, x):
        for i, layer in enumerate(self.layers):
            x = layer(x)
            # Apply activation to all layers except the last one
            if i < len(self.layers) - 1:
                if self.activation == 'relu':
                    x = F.relu(x)
                elif self.activation == 'tanh':
                    x = torch.tanh(x)
        return x


class GNNCapConvLayer(MessagePassing):
    """
    Single GNN-Cap convolutional layer implementing Algorithm 1

    From paper Section III-B:
    - Aggregates information from neighbors (nodes and edges)
    - Updates node and edge embeddings
    - Uses MEAN aggregation
    """

    def __init__(
        self,
        node_in_dim: int,
        edge_in_dim: int,
        hidden_dims: List[int],
        node_out_dim: int,
        activation='relu',
        use_attention: bool = False,
        heads: int = 4,
        attention_type: str = 'gat'
    ):
        # Choose aggregation method based on attention flag
        if use_attention:
            # GAT will handle attention-weighted aggregation internally
            super(GNNCapConvLayer, self).__init__(aggr='add')
        else:
            super(GNNCapConvLayer, self).__init__(aggr='mean')  # MEAN aggregation

        self.node_in_dim = node_in_dim
        self.edge_in_dim = edge_in_dim
        self.node_out_dim = node_out_dim
        self.use_attention = use_attention
        self.heads = heads
        self.attention_type = attention_type

        if use_attention:
            # Choose attention type: GAT or GATv2
            if attention_type == 'gatv2':
                # Improved GAT with dynamic attention
                self.gat_conv = GATv2Conv(
                    in_channels=node_in_dim,
                    out_channels=hidden_dims[0] // heads,  # Split across heads
                    heads=heads,
                    edge_dim=edge_in_dim,  # Your 7D edge features
                    dropout=0.1,
                    concat=True  # Concatenate heads
                )
            else:
                # Standard GAT attention (default)
                self.gat_conv = GATConv(
                    in_channels=node_in_dim,
                    out_channels=hidden_dims[0] // heads,  # Split across heads
                    heads=heads,
                    edge_dim=edge_in_dim,  # Your 7D edge features
                    dropout=0.1,
                    concat=True  # Concatenate heads
                )

            # Calculate actual GAT output dimension to fix MLP input dimension
            # GAT with concat=True outputs (hidden_dims[0] // heads) * heads features, not hidden_dims[0]
            # This handles cases where hidden_dims[0] is not divisible by heads
            gat_output_dim = (hidden_dims[0] // heads) * heads  # Actual output from GAT with concat=True

            # Validate dimension calculation
            if gat_output_dim <= 0:
                raise ValueError(f"GAT output dimension {gat_output_dim} is invalid. "
                               f"hidden_dims[0]={hidden_dims[0]}, heads={heads}")

            # MLP for node update: h_vi = MLP(CONCAT(h_vi, attention_output))
            self.mlp_node_update = MLP(
                input_dim=node_in_dim + gat_output_dim,  # Original + actual GAT output
                hidden_dims=hidden_dims[1:-1],  # Middle dimensions
                output_dim=node_out_dim,
                activation=activation
            )
        else:
            # Original implementation without attention
            # MLP for neighbor aggregation: nij = MLP(CONCAT(h_vj, h_eij))
            # Input: node_in_dim + edge_in_dim
            # Output: hidden_dims[0]
            self.mlp_neighbor = MLP(
                input_dim=node_in_dim + edge_in_dim,
                hidden_dims=[],
                output_dim=hidden_dims[0],
                activation=activation
            )

            # MLP for node update: h_vi = MLP(CONCAT(h_vi, ni))
            # Input: node_in_dim + hidden_dims[0] (original node + aggregated)
            # Output: node_out_dim
            self.mlp_node_update = MLP(
                input_dim=node_in_dim + hidden_dims[0],
                hidden_dims=hidden_dims[1:-1],  # Middle dimensions
                output_dim=node_out_dim,
                activation=activation
            )

        # MLP for edge dimension transform: h_eij = MLP(h_eij)
        self.mlp_edge_dim = MLP(
            input_dim=edge_in_dim,
            hidden_dims=[],
            output_dim=node_out_dim,  # Transform to same dim as nodes
            activation=activation
        )

        # MLP for edge update: h_eij = MLP(CONCAT(h_vi, h_vj, h_eij))
        # Input: node_out_dim + node_out_dim + node_out_dim
        # Output: node_out_dim
        self.mlp_edge_update = MLP(
            input_dim=3 * node_out_dim,
            hidden_dims=[],
            output_dim=node_out_dim,
            activation=activation
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        edge_is_virtual: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass implementing one message passing layer

        Args:
            x: Node features [num_nodes, node_in_dim]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_in_dim]
            edge_is_virtual: Boolean mask for virtual edges [num_edges]

        Returns:
            updated_x: Updated node features [num_nodes, node_out_dim]
            updated_edge_attr: Updated edge features [num_edges, node_out_dim]
        """
        # Filter out virtual edges for message passing (they don't participate)
        if edge_is_virtual is not None:
            regular_edge_mask = ~edge_is_virtual
            edge_index_regular = edge_index[:, regular_edge_mask]
            edge_attr_regular = edge_attr[regular_edge_mask]
        else:
            edge_index_regular = edge_index
            edge_attr_regular = edge_attr

        # Node aggregation and update (Algorithm 1, lines 7-8)
        if self.use_attention:
            # Use GAT for attention-weighted aggregation
            attention_output = self.gat_conv(x, edge_index_regular, edge_attr_regular)

            # Concatenate original features with attention output
            combined = torch.cat([x, attention_output], dim=1)

            # Apply MLP for final node update
            updated_x = self.mlp_node_update(combined)
        else:
            # Original mean aggregation
            updated_x = self.propagate(
                edge_index_regular,
                x=x,
                edge_attr=edge_attr_regular,
                original_x=x
            )

        # Edge dimension transformation (Algorithm 1, lines 10-12)
        # Transform all edges (including virtual ones) to same dimension as nodes
        edge_attr_transformed = self.mlp_edge_dim(edge_attr)

        # Edge update (Algorithm 1, lines 13-15)
        # Concatenate source node, target node, and edge features
        row, col = edge_index
        edge_features_concat = torch.cat([
            updated_x[row],  # Source node embedding
            updated_x[col],  # Target node embedding
            edge_attr_transformed  # Edge embedding
        ], dim=1)

        updated_edge_attr = self.mlp_edge_update(edge_features_concat)

        return updated_x, updated_edge_attr

    def message(self, x_j: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
        """
        Construct messages from neighbors

        Algorithm 1, line 2: nij = MLP(CONCAT(h_vj, h_eij))

        Args:
            x_j: Features of neighboring nodes [num_edges, node_in_dim]
            edge_attr: Edge features [num_edges, edge_in_dim]

        Returns:
            messages: Neighbor vectors [num_edges, hidden_dim]
        """
        # Concatenate neighbor node features with edge features
        neighbor_features = torch.cat([x_j, edge_attr], dim=1)

        # Pass through MLP to get neighbor vector
        messages = self.mlp_neighbor(neighbor_features)

        return messages

    def update(self, aggr_out: torch.Tensor, original_x: torch.Tensor) -> torch.Tensor:
        """
        Update node embeddings

        Algorithm 1, lines 4-5:
        - ni = MEAN(nij, ∀vj ∈ N(vi))  # Done by aggregation
        - h_vi = MLP(CONCAT(h_vi, ni))

        Args:
            aggr_out: Aggregated neighbor information [num_nodes, hidden_dim]
            original_x: Original node features [num_nodes, node_in_dim]

        Returns:
            updated_x: Updated node embeddings [num_nodes, node_out_dim]
        """
        # Concatenate original node features with aggregated neighbor info
        combined = torch.cat([original_x, aggr_out], dim=1)

        # Pass through MLP for final node update
        updated_x = self.mlp_node_update(combined)

        return updated_x


class GNNCapModel(nn.Module):
    """
    Complete GNN-Cap model for capacitance prediction

    From paper:
    - 2 message passing layers (L=2)
    - Separate models for total and coupling capacitance
    - Virtual edges processed differently (skip message passing)
    """

    def __init__(
        self,
        node_feature_dim: int = 3,
        edge_feature_dim: int = 7,
        layer_1_dims: List[int] = [42, 83, 71, 128],
        layer_2_dims: List[int] = [112, 184, 80, 264],
        virtual_edge_dim_transform: int = 135,  # Ignored in simplified training
        virtual_edge_embedding: int = 368,      # Ignored in simplified training
        num_layers: int = 2,                     # Number of graph convolution layers
        prediction_type: str = 'total',         # 'total' or 'coupling'
        use_virtual_edges: bool = False,       # Disabled for simplified training
        activation: str = 'relu',
        use_attention: bool = False,           # Use GAT attention mechanism
        heads: int = 4,                        # Number of attention heads
        attention_type: str = 'gat',           # 'gat' or 'gatv2'
        aggregation: str = 'none',             # Net aggregation method
        aggregation_hidden_dim: int = 128,     # Hidden dim for attention pooling
    ):
        """
        Initialize GNN-Cap model

        Args:
            node_feature_dim: Dimension of node features (3 in paper: x_len, y_len, z_len)
            edge_feature_dim: Dimension of edge features (7 in paper)
            layer_1_dims: MLP dimensions for first message passing layer
            layer_2_dims: MLP dimensions for second message passing layer
            virtual_edge_dim_transform: Neurons for virtual edge dimension transform
            virtual_edge_embedding: Neurons for virtual edge embedding generation
            prediction_type: 'total' for total capacitance, 'coupling' for coupling
            use_virtual_edges: Whether model handles virtual edges
            activation: Activation function
        """
        super(GNNCapModel, self).__init__()

        self.node_feature_dim = node_feature_dim
        self.edge_feature_dim = edge_feature_dim
        self.prediction_type = prediction_type
        self.use_virtual_edges = use_virtual_edges
        self.num_layers = num_layers
        self.use_attention = use_attention
        self.heads = heads
        self.attention_type = attention_type
        self.aggregation = (aggregation or 'none').lower()
        self.aggregation_hidden_dim = aggregation_hidden_dim

        # Store layer dimensions for easy access
        self.layer_dims = [layer_1_dims, layer_2_dims]

        # Create layers dynamically based on num_layers
        self.convs = nn.ModuleList()

        # First layer
        self.convs.append(
            GNNCapConvLayer(
                node_in_dim=node_feature_dim,
                edge_in_dim=edge_feature_dim,
                hidden_dims=self.layer_dims[0],
                node_out_dim=self.layer_dims[0][-1],
                activation=activation,
                use_attention=use_attention,
                heads=heads,
                attention_type=attention_type
            )
        )

        # Additional layers (if num_layers > 2)
        for i in range(1, num_layers):
            in_dim = self.layer_dims[i-1][-1]  # Output dim of previous layer
            if i < len(self.layer_dims):
                # Use predefined dimensions
                hidden_dims = self.layer_dims[i]
            else:
                # Reuse last layer dimensions
                hidden_dims = self.layer_dims[-1]

            self.convs.append(
                GNNCapConvLayer(
                    node_in_dim=in_dim,
                    edge_in_dim=in_dim,
                    hidden_dims=hidden_dims,
                    node_out_dim=hidden_dims[-1],
                    activation=activation,
                    use_attention=use_attention,
                    heads=heads,
                    attention_type=attention_type
                )
            )

        # Virtual edge processing (Fig. 11 in paper)
        if use_virtual_edges:
            # Dimension transformation MLP
            self.virtual_edge_dim_mlp = MLP(
                input_dim=edge_feature_dim,
                hidden_dims=[],
                output_dim=virtual_edge_dim_transform,
                activation=activation
            )

            # Virtual edge embedding generation MLP
            # Input: 2 * node_out_dim (from final layer) + virtual_edge_dim_transform
            self.virtual_edge_embed_mlp = MLP(
                input_dim=2 * layer_2_dims[-1] + virtual_edge_dim_transform,
                hidden_dims=[],
                output_dim=virtual_edge_embedding,
                activation=activation
            )

        # Prediction heads
        if prediction_type == 'total':
            # Total capacitance: node-level prediction
            # Input: layer_2_dims[-1] (final node embedding dimension)
            # Output: 1 (capacitance value)
            self.fc_predict = nn.Linear(layer_2_dims[-1], 1)
            self.net_aggregator = build_net_aggregator(
                layer_2_dims[-1],
                method=self.aggregation,
                hidden_dim=self.aggregation_hidden_dim,
            )
        else:  # coupling
            # Coupling capacitance: edge-level prediction
            # Regular edges: layer_2_dims[-1] (final edge embedding dimension)
            # Virtual edges: virtual_edge_embedding
            self.fc_predict_regular = nn.Linear(layer_2_dims[-1], 1)
            if use_virtual_edges:
                self.fc_predict_virtual = nn.Linear(virtual_edge_embedding, 1)
            self.net_aggregator = None

        # Apply proper weight initialization to prevent explosion
        self._initialize_weights()

    def _encode_graph(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        edge_is_virtual: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Run message passing layers and return node and edge embeddings."""
        node_embeddings = x
        edge_embeddings = edge_attr
        for conv in self.convs:
            node_embeddings, edge_embeddings = conv(
                node_embeddings,
                edge_index,
                edge_embeddings,
                edge_is_virtual=edge_is_virtual,
            )
        return node_embeddings, edge_embeddings

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        edge_is_virtual: Optional[torch.Tensor] = None,  # Ignored in simplified training
        net_attention_mask: Optional[torch.Tensor] = None,
        return_embeddings: bool = False,
    ) -> torch.Tensor:
        """
        Forward pass through GNN-Cap model

        Args:
            x: Node features [num_nodes, 3]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, 7]
            edge_is_virtual: Boolean mask for virtual edges [num_edges]

        Returns:
            predictions: Capacitance predictions
                - For total: [num_nodes, 1] without aggregation or [num_nets, 1]
                - For coupling: [num_edges, 1]
        """
        node_embeddings, edge_embeddings = self._encode_graph(
            x,
            edge_index,
            edge_attr,
            edge_is_virtual=edge_is_virtual,
        )

        if return_embeddings:
            return node_embeddings, edge_embeddings

        if self.prediction_type == 'total':
            if self.net_aggregator is not None:
                if net_attention_mask is None:
                    raise ValueError(
                        "net_attention_mask must be provided when using net aggregation"
                    )
                aggregated = self.net_aggregator(node_embeddings, net_attention_mask)
                predictions = self.fc_predict(aggregated)
            else:
                predictions = self.fc_predict(node_embeddings)
        else:  # coupling
            predictions = self.fc_predict_regular(edge_embeddings)

        return predictions

    def _initialize_weights(self):
        """Initialize weights to prevent gradient explosion"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                # Xavier/Glorot initialization for Linear layers
                nn.init.xavier_uniform_(module.weight, gain=nn.init.calculate_gain('relu'))
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0.0)


class GNNCapTotal(nn.Module):
    """GNN-Cap model for total capacitance prediction"""

    def __init__(self, **kwargs):
        super(GNNCapTotal, self).__init__()
        self.model = GNNCapModel(prediction_type='total', **kwargs)

    def forward(
        self,
        x,
        edge_index,
        edge_attr,
        edge_is_virtual=None,
        net_attention_mask: Optional[torch.Tensor] = None,
    ):
        return self.model(
            x,
            edge_index,
            edge_attr,
            edge_is_virtual=edge_is_virtual,
            net_attention_mask=net_attention_mask,
        )


class GNNCapCoupling(nn.Module):
    """GNN-Cap model for coupling capacitance prediction"""

    def __init__(self, **kwargs):
        super(GNNCapCoupling, self).__init__()
        self.model = GNNCapModel(prediction_type='coupling', **kwargs)

    def forward(self, x, edge_index, edge_attr, edge_is_virtual=None):
        return self.model(x, edge_index, edge_attr, edge_is_virtual)


def create_gnncap_models(
    use_virtual_edges: bool = True,
    device: str = 'cuda',
    aggregation: str = 'none',
    aggregation_hidden_dim: int = 128,
) -> Tuple[GNNCapTotal, GNNCapCoupling]:
    """
    Create both GNN-Cap models with paper's architecture

    Returns:
        total_model: Model for total capacitance prediction
        coupling_model: Model for coupling capacitance prediction
    """
    # Common parameters from paper
    model_kwargs = {
        'node_feature_dim': 3,
        'edge_feature_dim': 7,
        'layer_1_dims': [42, 83, 71, 128],
        'layer_2_dims': [112, 184, 80, 264],
        'virtual_edge_dim_transform': 135,
        'virtual_edge_embedding': 368,
        'use_virtual_edges': use_virtual_edges,
        'activation': 'relu',
        'aggregation': aggregation,
        'aggregation_hidden_dim': aggregation_hidden_dim,
    }

    total_model = GNNCapTotal(**model_kwargs).to(device)
    coupling_model = GNNCapCoupling(**model_kwargs).to(device)

    return total_model, coupling_model


if __name__ == '__main__':
    # Test model creation
    print("Creating GNN-Cap models...")

    total_model, coupling_model = create_gnncap_models(device='cpu')

    print(f"GNNCapTotal parameters: {sum(p.numel() for p in total_model.parameters()):,}")
    print(f"GNNCapCoupling parameters: {sum(p.numel() for p in coupling_model.parameters()):,}")

    # Test forward pass
    num_nodes = 100
    num_edges = 500

    x = torch.randn(num_nodes, 3)
    edge_index = torch.randint(0, num_nodes, (2, num_edges))
    edge_attr = torch.randn(num_edges, 7)
    edge_is_virtual = torch.rand(num_edges) > 0.9  # 10% virtual edges

    print("\nTesting forward pass...")
    with torch.no_grad():
        total_pred = total_model(x, edge_index, edge_attr, edge_is_virtual)
        coupling_pred = coupling_model(x, edge_index, edge_attr, edge_is_virtual)

    print(f"Total capacitance predictions shape: {total_pred.shape}")
    print(f"Coupling capacitance predictions shape: {coupling_pred.shape}")
    print("\nModels created successfully!")
