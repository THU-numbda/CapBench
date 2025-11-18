"""
Simple loss functions for GNN-Cap training

Minimal implementation with no external dependencies beyond PyTorch.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Union
import numpy as np


class MARELoss(nn.Module):
    """Mean Absolute Relative Error Loss - no scaling to prevent explosion"""

    def __init__(self, epsilon: float = 1e-8):
        super().__init__()
        self.epsilon = epsilon

    def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Handle both 1D and 2D targets
        if targets.dim() > 1:
            targets = targets.squeeze(-1)  # Remove last dimension if it's size 1
        if predictions.dim() > 1:
            predictions = predictions.squeeze(-1)  # Remove last dimension if it's size 1

        # Ensure both tensors have the same shape
        if predictions.shape != targets.shape:
            # If still mismatched, flatten both
            predictions = predictions.flatten()
            targets = targets.flatten()

        # Use absolute relative error on raw values (no scaling)
        relative_error = torch.abs((predictions - targets) / (targets + self.epsilon))
        return torch.mean(relative_error)


class MSRELoss(nn.Module):
    """Mean Squared Relative Error Loss - same formula as CNN training"""

    def __init__(self, epsilon: float = 1e-8):
        super().__init__()
        self.epsilon = epsilon

    def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Handle both 1D and 2D targets
        if targets.dim() > 1:
            targets = targets.squeeze(-1)  # Remove last dimension if it's size 1
        if predictions.dim() > 1:
            predictions = predictions.squeeze(-1)  # Remove last dimension if it's size 1

        # Ensure both tensors have the same shape
        if predictions.shape != targets.shape:
            # If still mismatched, flatten both
            predictions = predictions.flatten()
            targets = targets.flatten()

        # Use squared relative error on raw values (same as CNN training)
        relative_error = (predictions - targets) / (targets + self.epsilon)
        return torch.mean(relative_error ** 2)


def compute_all_metrics(predictions: Union[torch.Tensor, np.ndarray],
                       targets: Union[torch.Tensor, np.ndarray],
                       scale_to_femtofarads: bool = True) -> Dict[str, float]:
    """Compute basic metrics optimized for femtofarad capacitance values"""
    if isinstance(predictions, np.ndarray):
        predictions = torch.tensor(predictions, dtype=torch.float32)
    if isinstance(targets, np.ndarray):
        targets = torch.tensor(targets, dtype=torch.float32)

    epsilon = 1e-12
    scale_factor = 1e15 if scale_to_femtofarads else 1.0

    # Handle both 1D and 2D tensors
    if targets.dim() > 1:
        targets = targets.squeeze(-1)
    if predictions.dim() > 1:
        predictions = predictions.squeeze(-1)

    # Ensure both tensors have the same shape
    if predictions.shape != targets.shape:
        predictions = predictions.flatten()
        targets = targets.flatten()

    # Scale to femtofarads for better numerical stability
    if scale_to_femtofarads:
        predictions = predictions * scale_factor
        targets = targets * scale_factor
        epsilon = epsilon * scale_factor

    mse = torch.mean((predictions - targets) ** 2).item()
    rmse = torch.sqrt(mse)
    mae = torch.mean(torch.abs(predictions - targets)).item()

    # Use absolute relative error instead of (1.0 - pred/target)
    relative_error = torch.abs((predictions - targets) / (targets + epsilon))
    mare = torch.mean(relative_error).item()
    msre = torch.mean(relative_error ** 2).item()

    return {
        'mse': mse,
        'mae': mae,
        'mare': mare,
        'msre': msre,
        'rmse': rmse
    }