"""
Comprehensive Loss Metrics for ML Training Validation

This module provides standardized loss functions for validation reporting across
all ML training pipelines in the CAP3D framework. All functions handle numerical
stability and work with both PyTorch tensors and numpy arrays.

Functions:
    - mse: Mean Squared Error
    - msre: Mean Squared Relative Error
    - mare: Mean Absolute Relative Error
    - rmse: Root Mean Squared Error
    - compute_all_metrics: Convenience function to compute all metrics at once
"""

import torch
import numpy as np
from typing import Dict, Union, Tuple

# Small epsilon to prevent division by zero
EPSILON = 1e-8


def _ensure_tensor(predictions: Union[torch.Tensor, np.ndarray],
                   targets: Union[torch.Tensor, np.ndarray]) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Convert inputs to PyTorch tensors if they aren't already.

    Args:
        predictions: Predicted values
        targets: Ground truth values

    Returns:
        Tuple of (predictions_tensor, targets_tensor)
    """
    if not isinstance(predictions, torch.Tensor):
        predictions = torch.tensor(predictions, dtype=torch.float32)
    if not isinstance(targets, torch.Tensor):
        targets = torch.tensor(targets, dtype=torch.float32)

    return predictions, targets


def mse(predictions: Union[torch.Tensor, np.ndarray],
        targets: Union[torch.Tensor, np.ndarray]) -> float:
    """
    Mean Squared Error (MSE)

    MSE = mean((predictions - targets)^2)

    Args:
        predictions: Predicted values
        targets: Ground truth values

    Returns:
        MSE value as float
    """
    predictions, targets = _ensure_tensor(predictions, targets)
    return torch.mean((predictions - targets) ** 2).item()


def msre(predictions: Union[torch.Tensor, np.ndarray],
         targets: Union[torch.Tensor, np.ndarray]) -> float:
    """
    Mean Squared Relative Error (MSRE)

    MSRE = mean((1 - predictions/targets)^2)

    Args:
        predictions: Predicted values
        targets: Ground truth values

    Returns:
        MSRE value as float
    """
    predictions, targets = _ensure_tensor(predictions, targets)
    relative_error = 1.0 - predictions / (targets + EPSILON)
    return torch.mean(relative_error ** 2).item()


def mare(predictions: Union[torch.Tensor, np.ndarray],
         targets: Union[torch.Tensor, np.ndarray]) -> float:
    """
    Mean Absolute Relative Error (MARE)

    MARE = mean(|1 - predictions/targets|)

    Args:
        predictions: Predicted values
        targets: Ground truth values

    Returns:
        MARE value as float
    """
    predictions, targets = _ensure_tensor(predictions, targets)
    relative_error = torch.abs(1.0 - predictions / (targets + EPSILON))
    return torch.mean(relative_error).item()


def rmse(predictions: Union[torch.Tensor, np.ndarray],
         targets: Union[torch.Tensor, np.ndarray]) -> float:
    """
    Root Mean Squared Error (RMSE)

    RMSE = sqrt(mean((predictions - targets)^2))

    Args:
        predictions: Predicted values
        targets: Ground truth values

    Returns:
        RMSE value as float
    """
    predictions, targets = _ensure_tensor(predictions, targets)
    mse_value = torch.mean((predictions - targets) ** 2)
    return torch.sqrt(mse_value).item()


def compute_all_metrics(predictions: Union[torch.Tensor, np.ndarray],
                       targets: Union[torch.Tensor, np.ndarray]) -> Dict[str, float]:
    """
    Compute all comprehensive loss metrics at once.

    Args:
        predictions: Predicted values
        targets: Ground truth values

    Returns:
        Dictionary containing all metrics:
            {
                'mse': float,
                'msre': float,
                'mare': float,
                'rmse': float
            }
    """
    metrics = {
        'mse': mse(predictions, targets),
        'msre': msre(predictions, targets),
        'mare': mare(predictions, targets),
        'rmse': rmse(predictions, targets)
    }
    return metrics


class LossMetricsTracker:
    """
    Utility class for tracking loss metrics across batches during validation.

    Attributes:
        metrics: Dictionary tracking cumulative sum of each metric
        count: Number of samples processed
    """

    def __init__(self):
        self.metrics = {
            'mse': 0.0,
            'msre': 0.0,
            'mare': 0.0,
            'rmse': 0.0
        }
        self.count = 0

    def update(self, predictions: Union[torch.Tensor, np.ndarray],
               targets: Union[torch.Tensor, np.ndarray]) -> None:
        """
        Update metrics with a new batch of predictions and targets.

        Args:
            predictions: Batch predictions
            targets: Batch targets
        """
        batch_metrics = compute_all_metrics(predictions, targets)
        batch_size = len(targets) if hasattr(targets, '__len__') else 1

        for metric_name in self.metrics:
            self.metrics[metric_name] += batch_metrics[metric_name] * batch_size

        self.count += batch_size

    def get_average_metrics(self) -> Dict[str, float]:
        """
        Get average metrics across all processed batches.

        Returns:
            Dictionary of average metrics
        """
        if self.count == 0:
            return {k: 0.0 for k in self.metrics}

        return {k: v / self.count for k, v in self.metrics.items()}

    def reset(self) -> None:
        """Reset all metrics and count."""
        for k in self.metrics:
            self.metrics[k] = 0.0
        self.count = 0


# Convenience function for backward compatibility
def calculate_comprehensive_losses(predictions: Union[torch.Tensor, np.ndarray],
                                  targets: Union[torch.Tensor, np.ndarray]) -> Dict[str, float]:
    """
    Alias for compute_all_metrics for backward compatibility.
    """
    return compute_all_metrics(predictions, targets)