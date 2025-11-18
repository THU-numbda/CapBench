"""
PyTorch Lightning Module for GNN-Cap Training

Replaces the complex custom GNNCapTrainer with a simplified, battle-tested
Lightning implementation that handles device management, gradient tracking,
validation, checkpointing, and logging automatically.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from typing import Dict, Any, Optional
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping

from models.gnncap_model import GNNCapModel
from models.attention_pool import build_attention_mask
from utils.simple_metrics import MARELoss, MSRELoss, compute_all_metrics


class GNNCapLightningModule(pl.LightningModule):
    """
    PyTorch Lightning module for GNN-Cap capacitance prediction.

    Handles:
    - Automatic device management
    - Training/validation loops
    - Gradient computation
    - Checkpointing
    - Logging
    - Optimizer configuration
    """

    def __init__(
        self,
        model_type: str = 'total',  # 'total' or 'coupling'
        learning_rate: float = 0.005,
        node_feature_dim: int = 3,
        edge_feature_dim: int = 7,
        layer_1_dims: list = None,
        layer_2_dims: list = None,
        virtual_edge_dim_transform: int = 135,
        virtual_edge_embedding: int = 368,
        use_virtual_edges: bool = True,
        num_layers: int = 2,
        use_attention: bool = False,
        heads: int = 4,
        attention_type: str = 'gat',
        aggregation: str = 'none',
        aggregation_hidden_dim: int = 128,
        **kwargs
    ):
        super().__init__()
        self.save_hyperparameters()

        # Model configuration
        self.model_type = model_type
        self.learning_rate = learning_rate
        self.aggregation = (aggregation or 'none').lower()
        self.requires_net_attention = (self.model_type == 'total' and self.aggregation != 'none')

        # Initialize model (virtual edges disabled for simplified training)
        self.model = GNNCapModel(
            node_feature_dim=node_feature_dim,
            edge_feature_dim=edge_feature_dim,
            layer_1_dims=layer_1_dims or [42, 83, 71, 128],
            layer_2_dims=layer_2_dims or [112, 184, 80, 264],
            virtual_edge_dim_transform=virtual_edge_dim_transform,  # Ignored
            virtual_edge_embedding=virtual_edge_embedding,          # Ignored
            prediction_type=model_type,
            use_virtual_edges=False,  # Always False for simplified training
            num_layers=num_layers,
            use_attention=use_attention,
            heads=heads,
            attention_type=attention_type,
             aggregation=self.aggregation if self.requires_net_attention else 'none',
             aggregation_hidden_dim=aggregation_hidden_dim,
            **kwargs
        )

        # Loss functions
        self.criterion_msre = MSRELoss()  # Use MSRE for training (same as CNN)
        self.criterion_mare = MARELoss()  # Use MARE for reporting
        self.criterion_rmse = self._rmse_loss

        # Simple metrics tracking
        self.train_losses = []
        self.val_losses = []
        self._log_count = 0

    def forward(self, data: Data):
        """Forward pass through the model"""
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
        return self.model(
            data.x,
            data.edge_index,
            data.edge_attr,
            edge_is_virtual=None,
            net_attention_mask=net_mask,
        )

    def training_step(self, batch, batch_idx):
        """Training step with automatic gradient handling"""
        data, labels = batch
        data = data.to(self.device)
        labels = labels.to(self.device)

        # Forward pass (no virtual edges in simplified training)
        predictions = self(data)

        # Initialize with dummy loss to ensure training always continues
        dummy_loss = torch.tensor(0.0, device=self.device, requires_grad=True)

        # Select supervised subset (handle variable batch sizes)
        target_labels = None
        if self.model_type == 'total':
            if self.requires_net_attention:
                target_labels = getattr(data, 'net_y', getattr(data, 'y', labels))
            else:
                target_labels = getattr(data, 'node_y', getattr(data, 'y', labels))
        else:  # coupling
            target_labels = getattr(data, 'edge_y', labels)

        # Compute losses only if we have valid data, otherwise use dummy loss
        if target_labels is not None and target_labels.numel() > 0:
            predictions_flat = predictions.view(-1)
            targets_flat = target_labels.view(-1)

            if self.model_type == 'total':
                threshold = 1e-12
            else:
                threshold = 1e-8

            valid_mask = targets_flat > threshold
            if valid_mask.any():
                predictions_flat = predictions_flat[valid_mask]
                targets_flat = targets_flat[valid_mask]

            # Scale targets to femtofarads for better numerical range
            scaled_targets = targets_flat * 1e15  # Convert to femtofarads

            # Use MSRE for training (same as CNN), MARE for reporting
            loss_msre = self.criterion_msre(predictions_flat, scaled_targets)  # Training loss
            loss_mare = self.criterion_mare(predictions_flat, scaled_targets)  # Reporting metric
            loss_rmse = self.criterion_rmse(predictions_flat, scaled_targets)
            self.train_losses.append(loss_mare.item())
        else:
            # Use dummy loss when no valid data
            loss_msre = dummy_loss
            loss_mare = dummy_loss
            loss_rmse = dummy_loss

        # Log losses with better names
        batch_size = (
            target_labels.numel() if (target_labels is not None and target_labels.numel() > 0) else 1
        )
        # Log MSRE loss for training (same as CNN), MARE for reporting consistency
        self.log('train_msre_loss', loss_msre, on_step=True, on_epoch=True, prog_bar=False, batch_size=batch_size)
        self.log('train_mape_loss', loss_mare, on_step=True, on_epoch=True, prog_bar=True, batch_size=batch_size)  # MAPE for train reporting
        self.log('train_rmse_loss', loss_rmse, on_step=True, on_epoch=True, batch_size=batch_size)
        self.log('train_loss', loss_msre, on_step=True, on_epoch=True, prog_bar=True, batch_size=batch_size)  # MSRE as main training loss

        # Log additional info for debugging
        if hasattr(self, '_log_count'):
            self._log_count += 1
        else:
            self._log_count = 1

        if self._log_count % 100 == 0:  # Log every 100 steps
            if target_labels is not None and target_labels.numel() > 0:
                preds_for_log = predictions.view(-1)
                targets_for_log = target_labels.view(-1)
                mean_target = targets_for_log.mean().item()
                mean_pred = preds_for_log.mean().item()
                self.log('train_target_raw', mean_target, on_step=True, on_epoch=False, batch_size=1)
                self.log('train_pred_raw', mean_pred, on_step=True, on_epoch=False, batch_size=1)

        return loss_msre  # Return MSRE loss for optimization (not MARE)

    def validation_step(self, batch, batch_idx):
        """Validation step"""
        data, labels = batch
        data = data.to(self.device)
        labels = labels.to(self.device)

        # Forward pass (no virtual edges in simplified training)
        predictions = self(data)

        # Initialize with dummy loss to ensure val_loss is always logged
        dummy_loss = torch.tensor(0.0, device=self.device, requires_grad=True)

        # Select supervised subset (same logic as training)
        target_labels = None
        if self.model_type == 'total':
            if self.requires_net_attention:
                target_labels = getattr(data, 'net_y', getattr(data, 'y', labels))
            else:
                target_labels = getattr(data, 'node_y', getattr(data, 'y', labels))
        else:  # coupling
            target_labels = getattr(data, 'edge_y', labels)

        # Compute losses only if we have valid data, otherwise use dummy loss
        if target_labels is not None and target_labels.numel() > 0:
            # Scale targets to femtofarads for better numerical range
            predictions_flat = predictions.view(-1)
            targets_flat = target_labels.view(-1)
            if self.model_type == 'total':
                threshold = 1e-12
            else:
                threshold = 1e-8

            valid_mask = targets_flat > threshold
            if valid_mask.any():
                predictions_flat = predictions_flat[valid_mask]
                targets_flat = targets_flat[valid_mask]

            scaled_targets = targets_flat * 1e15  # Convert to femtofarads

            # Use MSRE for training (same as CNN), MARE for reporting
            loss_msre = self.criterion_msre(predictions_flat, scaled_targets)  # Training loss
            loss_mare = self.criterion_mare(predictions_flat, scaled_targets)  # Reporting metric
            loss_rmse = self.criterion_rmse(predictions_flat, scaled_targets)
            self.val_losses.append(loss_mare.item())
        else:
            # Use dummy loss when no valid data
            loss_msre = dummy_loss
            loss_mare = dummy_loss
            loss_rmse = dummy_loss

        # Always log losses to ensure val_loss is available for early stopping
        batch_size = (
            target_labels.numel() if (target_labels is not None and target_labels.numel() > 0) else 1
        )
        # Log MSRE loss for training (same as CNN), MARE for reporting consistency
        self.log('val_msre_loss', loss_msre, on_step=False, on_epoch=True, prog_bar=False, batch_size=batch_size)
        self.log('val_mape_loss', loss_mare, on_step=False, on_epoch=True, prog_bar=True, batch_size=batch_size)  # MAPE for val reporting
        self.log('val_rmse_loss', loss_rmse, on_step=False, on_epoch=True, batch_size=batch_size)
        self.log('val_loss', loss_msre, on_step=False, on_epoch=True, prog_bar=True, batch_size=batch_size)  # MSRE as main validation loss

        # Log validation debugging info
        if target_labels is not None and target_labels.numel() > 0:
            preds_for_log = predictions.view(-1)
            targets_for_log = target_labels.view(-1)
            mean_target = targets_for_log.mean().item()
            mean_pred = preds_for_log.mean().item()
            self.log('val_target_raw', mean_target, on_step=False, on_epoch=True, batch_size=1)
            self.log('val_pred_raw', mean_pred, on_step=False, on_epoch=True, batch_size=1)

            # Store examples for display and overall statistics
            if not hasattr(self, '_val_examples'):
                self._val_examples = []
                self._overall_errors = []  # Track all errors for overall stats

            # Get net names and window_id
            net_names = getattr(data, 'net_names', None)
            if not net_names:
                net_names = getattr(data, 'node_net_names', [])

            # Handle window_id - ensure it's a string
            window_id = getattr(data, 'window_id', f'batch_{batch_idx}')
            if isinstance(window_id, list):
                window_id = str(window_id[0]) if window_id else f'batch_{batch_idx}'
            else:
                window_id = str(window_id)

            # Store errors for overall statistics (collect all, not just first batch)
            for i in range(len(preds_for_log)):
                target_fF = targets_for_log[i].item() * 1e15  # Convert to femtofarads
                pred_fF = preds_for_log[i].item()  # Model should predict in femtofarads

                rel_error = abs((pred_fF - target_fF) / (target_fF + 1e-12))
                rel_error_pct = rel_error * 100
                self._overall_errors.append(rel_error_pct)

            # Only store detailed examples for first batch and limit to 10
            if batch_idx == 0 and len(self._val_examples) < 10:
                for i in range(min(len(preds_for_log), 10)):  # Limit to 10 examples
                    target_fF = targets_for_log[i].item() * 1e15  # Convert to femtofarads
                    pred_fF = preds_for_log[i].item()  # Model should predict in femtofarads

                    # Handle net_name - it could be a list or string
                    if i < len(net_names):
                        net_name = net_names[i]
                        if isinstance(net_name, list):
                            net_name = str(net_name[0]) if net_name else f"net_{i}"
                        else:
                            net_name = str(net_name)
                    else:
                        net_name = f"net_{i}"

                    rel_error = abs((pred_fF - target_fF) / (target_fF + 1e-12))
                    self._val_examples.append({
                        'window_id': window_id,
                        'net_name': net_name,
                        'target': target_fF,
                        'pred': pred_fF,
                        'rel_error': rel_error,
                        'rel_error_pct': rel_error * 100  # Convert to percentage
                    })

        return loss_mare

    def on_train_epoch_end(self):
        """Called at the end of training epoch"""
        # Reset losses for next epoch
        self.train_losses = []

    def on_validation_epoch_end(self):
        """Called at the end of each validation epoch."""
        # Show example predictions vs targets
        self._log_prediction_examples()

        # Reset losses and examples for next epoch
        self.val_losses = []
        if hasattr(self, '_val_examples'):
            self._val_examples = []
        if hasattr(self, '_overall_errors'):
            self._overall_errors = []

    def _log_prediction_examples(self):
        """Log example predictions vs targets at epoch end"""
        if hasattr(self, '_val_examples') and self._val_examples and hasattr(self, '_overall_errors'):
            # Get the window ID from first example (all from first batch)
            window_id = self._val_examples[0]['window_id']

            # Calculate overall statistics from all validation batches
            overall_errors = self._overall_errors
            mean_error = sum(overall_errors) / len(overall_errors)
            max_error = max(overall_errors)
            min_error = min(overall_errors)

            print(f"\n{'='*105}")
            print(f"VALIDATION EXAMPLES - Epoch {self.current_epoch} (Window: {window_id}, showing {len(self._val_examples)} of {len(overall_errors)} total nets)")
            print(f"{'='*105}")
            print(f"{'Window ID':>12} {'Net Name':>20} {'Target (fF)':>15} {'Pred (fF)':>15} {'Error %':>10} {'Abs Error':>12}")
            print(f"{'-'*90}")

            # Sort examples by target value (descending) for better readability
            examples_sorted = sorted(self._val_examples, key=lambda x: x['target'], reverse=True)

            for example in examples_sorted:
                # Truncate long net names for display
                net_name = example['net_name']
                if len(net_name) > 18:
                    net_name = net_name[:15] + "..."

                print(f"{window_id:>12} {net_name:>20} {example['target']:>15.3f} {example['pred']:>15.3f} {example['rel_error_pct']:>10.1f} {example['rel_error']:>12.3f}")

            print(f"\n{'='*105}")
            print(f"Overall Summary (all {len(overall_errors)} nets):")
            print(f"Mean Error: {mean_error:.1f}%, Min: {min_error:.1f}%, Max: {max_error:.1f}%")
            print(f"{'='*105}")
        else:
            print(f"\n[Epoch {self.current_epoch}] No validation examples collected")

    def _rmse_loss(self, pred, target):
        """RMSE loss - no scaling to prevent explosion"""
        # Handle both 1D and 2D tensors
        if target.dim() > 1:
            target = target.squeeze(-1)
        if pred.dim() > 1:
            pred = pred.squeeze(-1)

        # Ensure both tensors have the same shape
        if pred.shape != target.shape:
            pred = pred.flatten()
            target = target.flatten()

        # No scaling - use raw values to prevent numerical issues
        return torch.sqrt(F.mse_loss(pred, target))


    def configure_optimizers(self):
        """Configure optimizer and learning rate scheduler"""
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)

        # Optional: Add learning rate scheduler
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=5
            # verbose=True removed - deprecated in PyTorch 2.0+
        )

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
                "frequency": 1
            }
        }


def create_trainer(
    max_epochs: int = 50,
    patience: int = 10,
    checkpoint_dir: str = "./checkpoints",
    log_dir: str = "./logs",
    model_type: str = "model",
    **kwargs
) -> pl.Trainer:
    """
    Create a PyTorch Lightning trainer with sensible defaults.

    Args:
        max_epochs: Maximum number of training epochs
        patience: Early stopping patience
        checkpoint_dir: Directory to save checkpoints
        log_dir: Directory for logs
        model_type: Type of model for checkpoint filename
        **kwargs: Additional trainer arguments

    Returns:
        Configured PyTorch Lightning trainer
    """
    # Callbacks
    callbacks = [
        ModelCheckpoint(
            dirpath=checkpoint_dir,
            filename=f'{model_type}-{{epoch:02d}}-{{val_loss:.2f}}',
            monitor='val_loss',
            mode='min',
            save_top_k=3,
            save_last=True,
            verbose=True
        ),
        EarlyStopping(
            monitor='val_loss',
            mode='min',
            patience=patience,
            min_delta=0.01,  # Require 0.01% improvement
            verbose=True
        )
    ]

    # Create trainer (filter out any invalid trainer args)
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        callbacks=callbacks,
        default_root_dir=log_dir,
        enable_progress_bar=True,
        enable_model_summary=True,
        gradient_clip_val=1.0,  # Clip gradients to prevent explosion
        gradient_clip_algorithm="norm",
        **kwargs
    )

    return trainer
