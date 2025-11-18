"""
Standard PyTorch Lightning Module for GNN-Cap with basic training features.

This module provides:
- Standard loss functions (MSRE for training, MARE for reporting)
- Basic regularization (optional)
- Monitoring and logging
- Parameter profiling integration
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from typing import Dict, Any, Optional, List, Tuple
import pytorch_lightning as pl
import numpy as np
from pathlib import Path

# Import standard modules
from models.gnncap_model import GNNCapModel
from models.attention_pool import build_attention_mask
from utils.simple_metrics import MARELoss, MSRELoss, compute_all_metrics
from utils.parameter_utils import ParameterProfiler


class AdaptiveLossWeighting(nn.Module):
    """
    Adaptive loss weighting based on prediction difficulty or capacitance magnitude.
    """

    def __init__(self,
                 weighting_strategy: str = 'magnitude_based',
                 min_weight: float = 0.1,
                 max_weight: float = 3.0,
                 temperature: float = 1.0):
        """
        Initialize adaptive loss weighting.

        Args:
            weighting_strategy: Strategy for weight computation ('magnitude_based', 'uncertainty_based', 'learned')
            min_weight: Minimum weight value
            max_weight: Maximum weight value
            temperature: Temperature for softmax-like weighting
        """
        super().__init__()
        self.weighting_strategy = weighting_strategy
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.temperature = temperature

        if weighting_strategy == 'learned':
            self.weight_network = nn.Sequential(
                nn.Linear(1, 16),  # Input: target value
                nn.ReLU(),
                nn.Linear(16, 8),
                nn.ReLU(),
                nn.Linear(8, 1),
                nn.Sigmoid()
            )

    def forward(self, targets: torch.Tensor) -> torch.Tensor:
        """
        Compute adaptive weights for each target.

        Args:
            targets: Target values [batch_size]

        Returns:
            Loss weights [batch_size]
        """
        if self.weighting_strategy == 'magnitude_based':
            # Higher weights for smaller capacitance values (harder to predict)
            # Scale targets to log space for better dynamic range
            log_targets = torch.log(targets + 1e-12)
            weights = 1.0 / (log_targets.abs() + 1e-8)

        elif self.weighting_strategy == 'uncertainty_based':
            # Weight inversely proportional to target magnitude
            weights = 1.0 / (targets + 1e-8)

        elif self.weighting_strategy == 'learned':
            # Learn weights from target values
            weights = self.weight_network(targets.unsqueeze(-1)).squeeze(-1)

        else:
            # Uniform weighting
            weights = torch.ones_like(targets)

        # Normalize and apply bounds
        weights = torch.clamp(weights, self.min_weight, self.max_weight)
        weights = weights / weights.mean()  # Normalize to mean=1

        return weights


class MultiScaleLoss(nn.Module):
    """
    Multi-scale loss combining different loss functions and scales.
    """

    def __init__(self,
                 loss_types: List[str] = ['msre', 'mae', 'huber'],
                 loss_weights: Optional[List[float]] = None,
                 adaptive_weighting: Optional[Dict[str, Any]] = None):
        """
        Initialize multi-scale loss.

        Args:
            loss_types: List of loss function types
            loss_weights: Weights for each loss type
            adaptive_weighting: Configuration for adaptive weighting
        """
        super().__init__()
        self.loss_types = loss_types

        if loss_weights is None:
            self.loss_weights = [1.0 / len(loss_types)] * len(loss_types)
        else:
            self.loss_weights = loss_weights

        # Initialize loss functions
        self.loss_functions = {}
        for loss_type in loss_types:
            if loss_type == 'msre':
                self.loss_functions[loss_type] = MSRELoss()
            elif loss_type == 'mae':
                self.loss_functions[loss_type] = nn.L1Loss()
            elif loss_type == 'mse':
                self.loss_functions[loss_type] = nn.MSELoss()
            elif loss_type == 'huber':
                self.loss_functions[loss_type] = nn.HuberLoss(delta=1.0)
            elif loss_type == 'log_cosh':
                self.loss_functions[loss_type] = self._log_cosh_loss
            elif loss_type == 'mape':
                self.loss_functions[loss_type] = MARELoss()

        # Adaptive weighting
        if adaptive_weighting:
            self.adaptive_weighting = AdaptiveLossWeighting(**adaptive_weighting)
        else:
            self.adaptive_weighting = None

    def _log_cosh_loss(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """Log-cosh loss function."""
        return torch.mean(torch.log(torch.cosh(pred - target)))

    def forward(self,
                predictions: torch.Tensor,
                targets: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute multi-scale loss.

        Args:
            predictions: Predicted values
            targets: Target values

        Returns:
            Tuple of (total_loss, loss_breakdown)
        """
        # Apply adaptive weighting if enabled
        if self.adaptive_weighting:
            weights = self.adaptive_weighting(targets)
        else:
            weights = torch.ones_like(targets)

        total_loss = 0.0
        loss_breakdown = {}

        for i, (loss_type, loss_fn) in enumerate(self.loss_functions.items()):
            # Compute individual loss
            if loss_type in ['mse', 'mae', 'huber', 'log_cosh']:
                loss = loss_fn(predictions, targets)
            else:
                # For MSRE and MAPE which expect scaled inputs
                scaled_targets = targets * 1e15  # Convert to femtofarads
                scaled_predictions = predictions * 1e15
                loss = loss_fn(scaled_predictions, scaled_targets)

            # Apply adaptive weighting
            if self.adaptive_weighting:
                weighted_loss = (weights * loss_fn(predictions, targets) if loss_type in ['mse', 'mae', 'huber', 'log_cosh']
                               else weights * loss_fn(scaled_predictions, scaled_targets))
                loss = weighted_loss.mean()

            total_loss += self.loss_weights[i] * loss
            loss_breakdown[loss_type] = loss.item()

        return total_loss, loss_breakdown


class DropEdgeTransform:
    """
    Random edge dropping for regularization.
    """

    def __init__(self, drop_prob: float = 0.1):
        """
        Initialize DropEdge transformation.

        Args:
            drop_prob: Probability of dropping each edge
        """
        self.drop_prob = drop_prob

    def __call__(self,
                  edge_index: torch.Tensor,
                  edge_attr: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Apply DropEdge transformation.

        Args:
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge attributes [num_edges, edge_dim]

        Returns:
            Tuple of (transformed_edge_index, transformed_edge_attr)
        """
        if self.training and self.drop_prob > 0:
            num_edges = edge_index.size(1)
            mask = torch.rand(num_edges, device=edge_index.device) > self.drop_prob

            if mask.any():
                edge_index = edge_index[:, mask]
                if edge_attr is not None:
                    edge_attr = edge_attr[mask]
            else:
                # Ensure at least one edge remains
                keep_idx = torch.randint(0, num_edges, (1,), device=edge_index.device)
                edge_index = edge_index[:, keep_idx]
                if edge_attr is not None:
                    edge_attr = edge_attr[keep_idx]

        return edge_index, edge_attr


class FeatureMasking:
    """
    Random feature masking for regularization.
    """

    def __init__(self, mask_prob: float = 0.1):
        """
        Initialize feature masking.

        Args:
            mask_prob: Probability of masking each feature
        """
        self.mask_prob = mask_prob

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply feature masking.

        Args:
            x: Input features [num_nodes, feature_dim]

        Returns:
            Masked features
        """
        if self.training and self.mask_prob > 0:
            mask = torch.rand_like(x) > self.mask_prob
            x = x * mask.float()
        return x


class EnhancedGNNCapLightningModule(pl.LightningModule):
    """
    Enhanced PyTorch Lightning module for GNN-Cap with advanced features.
    """

    def __init__(
        self,
        model_type: str = 'total',
        learning_rate: float = 1e-4,
        node_feature_dim: int = 3,
        edge_feature_dim: int = 7,

        # Standard model parameters
        num_layers: int = 2,
        use_attention: bool = False,
        heads: int = 4,
        attention_type: str = 'gat',

        # Standard parameters
        aggregation: str = 'self_attention',
        aggregation_hidden_dim: int = 128,

        # Profiling
        enable_profiling: bool = True,
        profiling_frequency: int = 100,

        **kwargs
    ):
        """
        Initialize enhanced Lightning module.

        Args:
            model_type: 'total' or 'coupling'
            architecture_type: Type of model architecture
            learning_rate: Learning rate
            node_feature_dim: Node feature dimension
            edge_feature_dim: Edge feature dimension
            num_layers: Number of GNN layers
            use_progressive_dims: Whether to use progressive dimensions
            attention_type: Type of attention mechanism
            num_heads: Number of attention heads
            use_advanced_attention: Whether to use advanced attention
            use_multi_scale_loss: Whether to use multi-scale loss
            loss_types: Types of loss functions to use
            adaptive_weighting: Configuration for adaptive weighting
            drop_edge_prob: DropEdge probability
            feature_mask_prob: Feature masking probability
            layer_dropout_prob: Layer dropout probability
            aggregation: Net aggregation method
            aggregation_hidden_dim: Hidden dimension for aggregation
            enable_profiling: Whether to enable model profiling
            profiling_frequency: Frequency of profiling (in epochs)
            **kwargs: Additional parameters
        """
        super().__init__()
        self.save_hyperparameters()

        # Model configuration
        self.model_type = model_type
        self.learning_rate = learning_rate
        self.aggregation = (aggregation or 'none').lower()
        self.requires_net_attention = (self.model_type == 'total' and self.aggregation != 'none')

        # Initialize standard model
        self.model = GNNCapModel(
            node_feature_dim=node_feature_dim,
            edge_feature_dim=edge_feature_dim,
            prediction_type=model_type,
            num_layers=num_layers,
            use_attention=use_attention,
            heads=heads,
            attention_type=attention_type,
            aggregation=self.aggregation if self.requires_net_attention else 'none',
            aggregation_hidden_dim=aggregation_hidden_dim,
            **kwargs
        )

        # Standard loss functions
        self.criterion_msre = MSRELoss()
        self.criterion_mare = MARELoss()
        self.criterion_rmse = self._rmse_loss

        # Profiling
        self.enable_profiling = enable_profiling
        self.profiling_frequency = profiling_frequency
        self.parameter_profiler = ParameterProfiler(self.model) if enable_profiling else None

        # Training tracking
        self.train_losses = []
        self.val_losses = []
        self.loss_breakdown_history = []

        # Layer-wise dropout schedule (progressive)
        self.layer_dropout_schedule = self._create_dropout_schedule(num_layers)

    def _create_dropout_schedule(self, num_layers: int) -> List[float]:
        """Create progressive dropout schedule for layers."""
        base_prob = 0.05
        max_prob = 0.2
        return np.linspace(base_prob, max_prob, num_layers).tolist()

    def forward(self, data: Data) -> torch.Tensor:
        """Standard forward pass."""
        # Build attention mask if needed
        net_mask = None
        if self.requires_net_attention:
            net_mask = build_attention_mask(
                getattr(data, 'node_net_index', None),
                getattr(data, 'num_nets', None),
            )
            if net_mask is None:
                raise ValueError(
                    "Net aggregation requires node_net_index and num_nets metadata."
                )

        # Forward through model
        return self.model(
            data.x,
            data.edge_index,
            data.edge_attr,
            net_attention_mask=net_mask,
        )

    def training_step(self, batch, batch_idx):
        """Standard training step."""
        data, labels = batch
        data = data.to(self.device)
        labels = labels.to(self.device)

        # Forward pass
        predictions = self(data)

        # Get target labels
        target_labels = self._get_target_labels(data, labels)

        if target_labels is not None and target_labels.numel() > 0:
            predictions_flat = predictions.view(-1)
            targets_flat = target_labels.view(-1)

            # Filter valid targets
            valid_mask = self._get_valid_mask(targets_flat)
            if valid_mask.any():
                predictions_flat = predictions_flat[valid_mask]
                targets_flat = targets_flat[valid_mask]

            # Scale targets
            scaled_targets = targets_flat * 1e15

            # Compute loss
            loss = self.criterion_msre(predictions_flat, scaled_targets)

            # Additional losses for reporting
            loss_mare = self.criterion_mare(predictions_flat, scaled_targets)
            loss_rmse = self.criterion_rmse(predictions_flat, scaled_targets)

            self.train_losses.append(loss_mare.item())
        else:
            # Dummy loss
            loss = torch.tensor(0.0, device=self.device, requires_grad=True)
            loss_mare = loss
            loss_rmse = loss

        # Log metrics
        batch_size = len(target_labels) if target_labels is not None else 1
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log('train_mape_loss', loss_mare, on_step=True, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log('train_rmse_loss', loss_rmse, on_step=True, on_epoch=True, batch_size=batch_size)

        return loss

    def validation_step(self, batch, batch_idx):
        """Standard validation step."""
        data, labels = batch
        data = data.to(self.device)
        labels = labels.to(self.device)

        # Forward pass
        predictions = self(data)

        # Get target labels
        target_labels = self._get_target_labels(data, labels)

        if target_labels is not None and target_labels.numel() > 0:
            predictions_flat = predictions.view(-1)
            targets_flat = target_labels.view(-1)

            # Filter valid targets
            valid_mask = self._get_valid_mask(targets_flat)
            if valid_mask.any():
                predictions_flat = predictions_flat[valid_mask]
                targets_flat = targets_flat[valid_mask]

            # Scale targets
            scaled_targets = targets_flat * 1e15

            # Compute losses
            if hasattr(self, 'criterion') and isinstance(self.criterion, MultiScaleLoss):
                loss, loss_breakdown = self.criterion(predictions_flat, scaled_targets)

                # Log loss breakdown
                for loss_type, loss_value in loss_breakdown.items():
                    self.log(f'val_{loss_type}_loss', loss_value,
                           on_step=False, on_epoch=True, prog_bar=False, batch_size=len(targets_flat))
            else:
                loss = self.criterion_msre(predictions_flat, scaled_targets)

            loss_mare = self.criterion_mare(predictions_flat, scaled_targets)
            loss_rmse = self.criterion_rmse(predictions_flat, scaled_targets)

            # Store validation examples (same as original)
            self._store_validation_examples(data, predictions_flat, targets_flat, batch_idx)

            self.val_losses.append(loss_mare.item())
        else:
            loss = torch.tensor(0.0, device=self.device, requires_grad=True)
            loss_mare = loss
            loss_rmse = loss

        # Log metrics
        batch_size = len(target_labels) if target_labels is not None else 1
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log('val_mape_loss', loss_mare, on_step=False, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log('val_rmse_loss', loss_rmse, on_step=False, on_epoch=True, batch_size=batch_size)

        return loss

    def _get_target_labels(self, data: Data, labels: torch.Tensor) -> torch.Tensor:
        """Extract target labels based on model type."""
        if self.model_type == 'total':
            if self.requires_net_attention:
                return getattr(data, 'net_y', getattr(data, 'y', labels))
            else:
                return getattr(data, 'node_y', getattr(data, 'y', labels))
        else:  # coupling
            return getattr(data, 'edge_y', labels)

    def _get_valid_mask(self, targets: torch.Tensor) -> torch.Tensor:
        """Get mask for valid targets based on threshold."""
        if self.model_type == 'total':
            threshold = 1e-12
        else:
            threshold = 1e-8
        return targets > threshold

    def _store_validation_examples(self, data: Data, predictions: torch.Tensor,
                                 targets: torch.Tensor, batch_idx: int):
        """Store validation examples for display (from original implementation)."""
        if not hasattr(self, '_val_examples'):
            self._val_examples = []
            self._overall_errors = []

        # Get net names and window_id
        net_names = getattr(data, 'net_names', getattr(data, 'node_net_names', []))
        window_id = getattr(data, 'window_id', f'batch_{batch_idx}')
        if isinstance(window_id, list):
            window_id = str(window_id[0]) if window_id else f'batch_{batch_idx}'
        else:
            window_id = str(window_id)

        # Store examples
        for i in range(min(len(predictions), 10)):  # Limit to 10 examples
            target_fF = targets[i].item() * 1e15
            pred_fF = predictions[i].item()

            net_name = str(net_names[i]) if i < len(net_names) else f"node_{i}"

            rel_error = abs((pred_fF - target_fF) / (target_fF + 1e-12))

            self._val_examples.append({
                'window_id': window_id,
                'net_name': net_name,
                'target': target_fF,
                'pred': pred_fF,
                'rel_error': rel_error,
                'rel_error_pct': rel_error * 100
            })

            self._overall_errors.append(rel_error * 100)

    def on_train_epoch_end(self):
        """Called at the end of training epoch."""
        self.train_losses = []

    def on_validation_epoch_end(self):
        """Called at the end of validation epoch with enhanced profiling."""
        # Show example predictions
        self._log_prediction_examples()

        # Enhanced profiling
        if self.enable_profiling and self.current_epoch % self.profiling_frequency == 0:
            self._run_parameter_profiling()

        # Reset tracking
        self.val_losses = []
        if hasattr(self, '_val_examples'):
            self._val_examples = []
        if hasattr(self, '_overall_errors'):
            self._overall_errors = []

    def _run_parameter_profiling(self):
        """Run parameter profiling and log results."""
        if self.parameter_profiler:
            # Generate comprehensive report
            report = self.parameter_profiler.generate_comprehensive_report()

            # Log key metrics
            self.log('model/total_parameters', report['parameter_analysis']['total_parameters'], on_step=False, on_epoch=True)
            self.log('model/trainable_parameters', report['parameter_analysis']['trainable_parameters'], on_step=False, on_epoch=True)
            self.log('model/parameter_memory_mb', report['parameter_analysis']['parameter_memory_mb'], on_step=False, on_epoch=True)
            self.log('model/total_gflops', report['flop_analysis']['total_gflops'], on_step=False, on_epoch=True)
            self.log('model/total_memory_mb', report['memory_analysis']['total_memory_mb'], on_step=False, on_epoch=True)

            # Print summary
            print(f"\n{'='*80}")
            print(f"MODEL PROFILING - Epoch {self.current_epoch}")
            print(f"{'='*80}")
            print(f"Total Parameters: {report['parameter_analysis']['total_parameters']:,}")
            print(f"Trainable Parameters: {report['parameter_analysis']['trainable_parameters']:,}")
            print(f"Parameter Memory: {report['parameter_analysis']['parameter_memory_mb']:.2f} MB")
            print(f"Total GFLOPs: {report['flop_analysis']['total_gflops']:.4f}")
            print(f"Estimated Memory Usage: {report['memory_analysis']['total_memory_mb']:.2f} MB")

            # Model info
            model_info = self.model.get_model_info()
            print(f"Architecture: {model_info['model_type']}")
            print(f"Layers: {model_info['num_layers']}")
            print(f"Attention: {model_info['attention_type']}")
            print(f"Heads: {model_info['num_heads']}")
            print(f"Features: {', '.join(model_info['architecture_features'])}")
            print(f"{'='*80}")

    def _log_prediction_examples(self):
        """Log validation examples (from original implementation)."""
        if hasattr(self, '_val_examples') and self._val_examples and hasattr(self, '_overall_errors'):
            # Calculate overall statistics
            overall_errors = self._overall_errors
            mean_error = sum(overall_errors) / len(overall_errors)
            max_error = max(overall_errors)
            min_error = min(overall_errors)

            window_id = self._val_examples[0]['window_id']

            print(f"\n{'='*105}")
            print(f"ENHANCED VALIDATION - Epoch {self.current_epoch} (Window: {window_id}, showing {len(self._val_examples)} examples)")
            print(f"{'='*105}")
            print(f"{'Window ID':>12} {'Net Name':>20} {'Target (fF)':>15} {'Pred (fF)':>15} {'Error %':>10} {'Abs Error':>12}")
            print(f"{'-'*90}")

            examples_sorted = sorted(self._val_examples, key=lambda x: x['target'], reverse=True)

            for example in examples_sorted:
                net_name = example['net_name']
                if len(net_name) > 18:
                    net_name = net_name[:15] + "..."

                print(f"{window_id:>12} {net_name:>20} {example['target']:>15.3f} {example['pred']:>15.3f} "
                      f"{example['rel_error_pct']:>10.1f} {example['rel_error']:>12.3f}")

            print(f"\n{'='*105}")
            print(f"Enhanced Summary (all {len(overall_errors)} predictions):")
            print(f"Mean Error: {mean_error:.1f}%, Min: {min_error:.1f}%, Max: {max_error:.1f}%")

            # Add loss breakdown information if available
            if self.loss_breakdown_history:
                recent_losses = self.loss_breakdown_history[-10:]  # Last 10 batches
                avg_breakdown = {}
                for key in recent_losses[0].keys():
                    avg_breakdown[key] = np.mean([batch[key] for batch in recent_losses])

                print(f"Recent Loss Breakdown:")
                for loss_type, avg_loss in avg_breakdown.items():
                    print(f"  {loss_type}: {avg_loss:.6f}")

            print(f"{'='*105}")

    def _rmse_loss(self, pred, target):
        """RMSE loss function."""
        if target.dim() > 1:
            target = target.squeeze(-1)
        if pred.dim() > 1:
            pred = pred.squeeze(-1)

        if pred.shape != target.shape:
            pred = pred.flatten()
            target = target.flatten()

        return torch.sqrt(F.mse_loss(pred, target))

    def configure_optimizers(self):
        """Standard optimizer configuration."""
        optimizer = torch.optim.Adam(
            self.parameters(),
            lr=self.learning_rate,
            weight_decay=1e-4  # Standard weight decay
        )

        # Cosine annealing scheduler with warmup
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer,
            T_0=10,  # Initial restart period
            T_mult=2,  # Multiplicative factor for restart periods
            eta_min=self.learning_rate * 0.01  # Minimum learning rate
        )

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
                "frequency": 1
            }
        }