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
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pred_flat = predictions.view(-1)
        target_flat = targets.view(-1)
        scale = 1e15
        pred_scaled = pred_flat * scale
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
        loss_msre, loss_mare, loss_rmse = self._compute_losses(predictions, targets)
        batch_size = targets.numel() if targets.numel() > 0 else 1
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
        loss_msre, loss_mare, loss_rmse = self._compute_losses(predictions, targets)
        batch_size = targets.numel() if targets.numel() > 0 else 1
        self.log("val_loss", loss_msre, on_step=False, on_epoch=True, prog_bar=True, batch_size=batch_size)
        self.log("val_msre", loss_msre, on_step=False, on_epoch=True, batch_size=batch_size)
        self.log("val_mare", loss_mare, on_step=False, on_epoch=True, prog_bar=False, batch_size=batch_size)
        self.log("val_rmse", loss_rmse, on_step=False, on_epoch=True, prog_bar=False, batch_size=batch_size)
        return loss_msre

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=0.5,
            patience=5,
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
                "frequency": 1,
            },
        }


def create_trainer(
    max_epochs: int = 50,
    patience: int = 10,
    checkpoint_dir: str = "./checkpoints",
    log_dir: str = "./logs",
    run_name: str = "gnncap",
    **kwargs,
) -> pl.Trainer:
    """Create a minimal Lightning trainer with checkpointing and early stopping."""
    callbacks = [
        ModelCheckpoint(
            dirpath=checkpoint_dir,
            filename=f"{run_name}-{{epoch:02d}}-{{val_loss:.2f}}",
            monitor="val_loss",
            mode="min",
            save_top_k=3,
            save_last=True,
            verbose=True,
        ),
        EarlyStopping(
            monitor="val_loss",
            mode="min",
            patience=patience,
            min_delta=0.001,
            verbose=True,
        ),
    ]
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
