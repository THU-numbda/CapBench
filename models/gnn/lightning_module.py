"""
Simplified PyTorch Lightning module for the 2-layer GNN trainer.
"""

from typing import Optional, Sequence, Tuple

import torch
import torch.nn.functional as F
from torch_geometric.data import Data
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint

from models.gnncap_model import GNNCapModel
from models.attention_pool import build_attention_mask
from utils.simple_metrics import MARELoss, MSRELoss


class GNNCapLightningModule(pl.LightningModule):
    """Lightning module that trains the simplified two-layer GNN."""

    def __init__(
        self,
        learning_rate: float = 1e-4,
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
        self.save_hyperparameters()
        self.learning_rate = learning_rate
        self.model = GNNCapModel(
            node_feature_dim=node_feature_dim,
            edge_feature_dim=edge_feature_dim,
            hidden_dims=hidden_dims,
            conv_type=conv_type,
            heads=heads,
            aggregation_hidden_dim=aggregation_hidden_dim,
            node_feature_mean=node_feature_mean,
            node_feature_std=node_feature_std,
        )
        self.criterion_msre = MSRELoss()
        self.criterion_mare = MARELoss()

    def forward(self, data: Data) -> torch.Tensor:
        mask = build_attention_mask(
            getattr(data, "node_net_index", None),
            getattr(data, "num_nets", None),
        )
        if mask is None:
            raise ValueError("Net metadata (node_net_index/num_nets) is required for training.")
        return self.model(data.x, data.edge_index, data.edge_attr, mask)

    def _extract_targets(self, data: Data, labels: Optional[torch.Tensor]) -> torch.Tensor:
        targets = getattr(data, "net_y", labels)
        if targets is None:
            raise ValueError("Net-level labels are required for training.")
        return targets

    def _compute_losses(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
        label_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pred_flat = predictions.view(-1)
        target_flat = targets.view(-1)
        if label_mask is not None:
            mask_flat = label_mask.view(-1).bool()
            if mask_flat.shape != target_flat.shape:
                raise ValueError("Net label mask must have the same shape as the targets.")
            if not torch.any(mask_flat):
                raise ValueError("The batch does not contain any supervised net targets.")
            pred_flat = pred_flat[mask_flat]
            target_flat = target_flat[mask_flat]
        scale = 1e15
        pred_scaled = pred_flat
        target_scaled = target_flat * scale
        loss_msre = self.criterion_msre(pred_scaled, target_scaled)
        loss_mare = self.criterion_mare(pred_scaled, target_scaled)
        loss_rmse = torch.sqrt(F.mse_loss(pred_scaled, target_scaled))
        return loss_msre, loss_mare, loss_rmse

    def training_step(self, batch, batch_idx):
        data, labels = batch
        data = data.to(self.device)
        labels = labels.to(self.device) if labels is not None else None
        predictions = self(data)
        targets = self._extract_targets(data, labels).to(self.device)
        label_mask = getattr(data, "net_label_mask", None)
        loss_msre, loss_mare, loss_rmse = self._compute_losses(predictions, targets, label_mask)
        batch_size = int(label_mask.sum()) if label_mask is not None else targets.numel()
        batch_size = batch_size if batch_size > 0 else 1
        self.log("train_loss", loss_msre, on_step=True, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log("train_msre", loss_msre, on_step=True, on_epoch=True, batch_size=batch_size)
        self.log("train_mare", loss_mare, on_step=True, on_epoch=True, prog_bar=False, batch_size=batch_size)
        self.log("train_rmse", loss_rmse, on_step=True, on_epoch=True, prog_bar=False, batch_size=batch_size)
        return loss_msre

    def validation_step(self, batch, batch_idx):
        data, labels = batch
        data = data.to(self.device)
        labels = labels.to(self.device) if labels is not None else None
        predictions = self(data)
        targets = self._extract_targets(data, labels).to(self.device)
        label_mask = getattr(data, "net_label_mask", None)
        loss_msre, loss_mare, loss_rmse = self._compute_losses(predictions, targets, label_mask)
        batch_size = int(label_mask.sum()) if label_mask is not None else targets.numel()
        batch_size = batch_size if batch_size > 0 else 1
        self.log("val_loss", loss_msre, on_step=False, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log("val_msre", loss_msre, on_step=False, on_epoch=True, batch_size=batch_size)
        self.log("val_mare", loss_mare, on_step=False, on_epoch=True, prog_bar=False, batch_size=batch_size)
        self.log("val_rmse", loss_rmse, on_step=False, on_epoch=True, prog_bar=False, batch_size=batch_size)
        return loss_msre

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.learning_rate)


def create_trainer(
    max_epochs: int = 50,
    patience: Optional[int] = None,
    checkpoint_dir: str = "./checkpoints",
    log_dir: str = "./logs",
    run_name: str = "gnncap",
    **kwargs,
) -> pl.Trainer:
    """Create a minimal Lightning trainer with checkpointing and early stopping."""
    callbacks = [
        ModelCheckpoint(
            dirpath=checkpoint_dir,
            filename=f"{run_name}-{{epoch:02d}}-{{val_mare:.4f}}",
            monitor="val_mare",
            mode="min",
            save_top_k=1,
            save_last=True,
            verbose=True,
        ),
    ]
    if patience is not None and patience > 0:
        callbacks.append(
            EarlyStopping(
                monitor="val_loss",
                mode="min",
                patience=patience,
                min_delta=0.001,
                verbose=True,
            )
        )
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        callbacks=callbacks,
        default_root_dir=log_dir,
        enable_progress_bar=True,
        enable_model_summary=True,
        gradient_clip_val=1.0,
        gradient_clip_algorithm="norm",
        **kwargs,
    )
    return trainer
