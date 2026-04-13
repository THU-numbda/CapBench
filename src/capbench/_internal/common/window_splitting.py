"""
Window-level splitting utilities for capacitance extraction training.
Prevents data leakage by ensuring all samples from the same window
are assigned to the same train/validation/test split.
"""

import random
from typing import Dict, List, Set, Tuple
from torch.utils.data import Dataset
import torch


def create_window_level_splits(
    dataset,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42
) -> Tuple[Dataset, Dataset, Dataset]:
    """
    Split dataset at window level to prevent data leakage.

    Args:
        dataset: Dataset with get_window_ids() method
        train_ratio: Fraction of windows for training
        val_ratio: Fraction of windows for validation
        test_ratio: Fraction of windows for testing
        random_seed: Random seed for reproducible splits

    Returns:
        Tuple of (train_dataset, val_dataset, test_dataset)
    """
    # Get all window IDs
    all_window_ids = sorted(dataset.get_window_ids())
    print(f"Total windows available: {len(all_window_ids)}")

    # Validate ratios sum to approximately 1
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 1e-6:
        raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")

    # Deterministic window shuffling
    rng = random.Random(random_seed)
    shuffled_windows = all_window_ids.copy()
    rng.shuffle(shuffled_windows)

    # Calculate split points
    n_total = len(shuffled_windows)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    n_test = n_total - n_train - n_val  # Ensure all windows are used

    # Split windows
    train_windows = shuffled_windows[:n_train]
    val_windows = shuffled_windows[n_train:n_train + n_val]
    test_windows = shuffled_windows[n_train + n_val:]

    # Create subset datasets
    train_dataset = dataset.create_window_subset(train_windows)
    val_dataset = dataset.create_window_subset(val_windows)

    # Handle empty test set gracefully
    if test_windows:
        test_dataset = dataset.create_window_subset(test_windows)
    else:
        print("Warning: No windows allocated for test set (split ratios resulted in empty test set)")
        test_dataset = None

    # Report split statistics
    print(f"\n=== Window-Level Split Statistics ===")
    print(f"Train: {len(train_windows)} windows, {len(train_dataset)} samples")
    print(f"Validation: {len(val_windows)} windows, {len(val_dataset)} samples")
    if test_dataset:
        print(f"Test: {len(test_windows)} windows, {len(test_dataset)} samples")
    else:
        print("Test: 0 windows, 0 samples (empty test set)")

    return train_dataset, val_dataset, test_dataset


def verify_no_data_leakage(train_dataset, val_dataset, test_dataset) -> None:
    """
    Verify that no window appears in multiple splits.

    Args:
        train_dataset: Training dataset
        val_dataset: Validation dataset
        test_dataset: Test dataset

    Raises:
        AssertionError: If data leakage is detected
    """
    print("\n=== Verifying No Data Leakage ===")

    # Get window IDs from each dataset
    train_windows = set(train_dataset.get_window_ids())
    val_windows = set(val_dataset.get_window_ids())
    test_windows = set(test_dataset.get_window_ids()) if test_dataset is not None else set()

    print(f"Train windows: {len(train_windows)}")
    print(f"Validation windows: {len(val_windows)}")
    print(f"Test windows: {len(test_windows)}")

    # Check for overlaps
    train_val_overlap = train_windows & val_windows
    train_test_overlap = train_windows & test_windows
    val_test_overlap = val_windows & test_windows

    # Report any overlaps
    if train_val_overlap:
        print(f"❌ Data leakage detected: {len(train_val_overlap)} windows in both train and val")
        print(f"   Overlapping windows: {sorted(list(train_val_overlap))[:5]}...")
        raise AssertionError(f"Data leakage: {len(train_val_overlap)} windows in both train and val")

    if train_test_overlap:
        print(f"❌ Data leakage detected: {len(train_test_overlap)} windows in both train and test")
        print(f"   Overlapping windows: {sorted(list(train_test_overlap))[:5]}...")
        raise AssertionError(f"Data leakage: {len(train_test_overlap)} windows in both train and test")

    if val_test_overlap:
        print(f"❌ Data leakage detected: {len(val_test_overlap)} windows in both val and test")
        print(f"   Overlapping windows: {sorted(list(val_test_overlap))[:5]}...")
        raise AssertionError(f"Data leakage: {len(val_test_overlap)} windows in both val and test")

    print("✓ No data leakage detected - all splits are window-disjoint")


class WindowSubsetDataset(Dataset):
    """
    Dataset subset that maintains window-level structure.
    Used by create_window_level_splits to create proper subsets.
    """

    def __init__(self, base_dataset, window_ids):
        """
        Create subset containing only specified windows.

        Args:
            base_dataset: Original dataset with window-level structure
            window_ids: List of window IDs to include in subset
        """
        self.base_dataset = base_dataset
        self.window_ids = window_ids

        # Build mapping from global sample index to window-local indices
        self._build_sample_mapping()

    def _build_sample_mapping(self):
        """Build mapping for efficient sample access."""
        self.sample_mapping = []
        self._window_sample_ranges = []

        # Map window IDs to indices in base dataset
        window_to_index = {wid: i for i, wid in enumerate(self.base_dataset.get_window_ids())}

        for window_id in self.window_ids:
            if window_id not in window_to_index:
                raise ValueError(f"Window {window_id} not found in base dataset")

            window_idx = window_to_index[window_id]

            # Get samples for this window from base dataset
            if hasattr(self.base_dataset, '_window_samples'):
                # CNN-Cap style
                window_samples = self.base_dataset._window_samples[window_idx]
                start = len(self.sample_mapping)
                for sample_idx in range(len(window_samples)):
                    self.sample_mapping.append((window_idx, sample_idx))
                self._window_sample_ranges.append((start, len(self.sample_mapping)))
            else:
                # Fallback for other dataset types
                # This would need to be implemented based on specific dataset structure
                raise NotImplementedError("WindowSubsetDataset needs custom implementation for this dataset type")

    def __len__(self):
        """Total number of samples across all windows in subset."""
        return len(self.sample_mapping)

    def __getitem__(self, idx):
        """Get sample by index using window-local mapping."""
        if idx >= len(self.sample_mapping):
            raise IndexError(f"Index {idx} out of range for dataset with {len(self)} samples")

        window_idx, sample_idx = self.sample_mapping[idx]

        # Use base dataset's __getitem__ with window-local indexing
        if hasattr(self.base_dataset, '_get_item_window_level'):
            return self.base_dataset._get_item_window_level(window_idx, sample_idx)
        else:
            # Fallback - may need custom implementation
            raise NotImplementedError("Base dataset needs _get_item_window_level method")

    def get_window_ids(self):
        """Return window IDs for this subset."""
        return self.window_ids.copy()

    def get_window_sample_ranges(self):
        """Return contiguous sample ranges for each window in subset order."""
        return list(self._window_sample_ranges)
