#!/usr/bin/env python3
"""
PCT-Cap training script with window-level splitting and process node filtering.

This script uses the updated PcCapNpzDataset with mandatory SPEF validation
and window-level splitting to prevent data leakage.
"""

import argparse
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

# Ensure we can import the updated dataset
from data_utils.PcCapNpzDataset import PcCapNpzDataset
from common.window_splitting import create_window_level_splits, verify_no_data_leakage
from common.datasets import find_tech_stack_for_process_node
from common.loss_metrics import compute_all_metrics

# TensorBoard import with fallback
try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:
    class SummaryWriter:  # type: ignore
        def __init__(self, *args, **kwargs):
            print("WARNING: tensorboard not available; proceeding without logging.")

        def add_scalar(self, *args, **kwargs):
            return None

        def close(self):
            return None

# Import PCT model (adjust import as needed)
try:
    from models.PCT_Cap import PCT_Cap, CalLoss
except ImportError:
    print("Warning: PCT_Cap model not found. Using a simple MLP placeholder.")

    class SimpleMLP(torch.nn.Module):
        def __init__(self, input_dim=8, hidden_dim=256, output_dim=1):
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Linear(input_dim * 1024, hidden_dim),  # Assuming 1024 points
                torch.nn.ReLU(),
                torch.nn.Linear(hidden_dim, hidden_dim),
                torch.nn.ReLU(),
                torch.nn.Linear(hidden_dim, output_dim)
            )

        def forward(self, x):
            # x shape: (batch, N, features)
            batch_size = x.shape[0]
            x = x.view(batch_size, -1)  # Flatten
            return self.net(x)

    def CalLoss():
        return torch.nn.MSELoss()

    PCT_Cap = SimpleMLP


def set_seed(seed: int):
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_epoch(model, train_loader, optimizer, criterion, device, epoch):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    num_batches = len(train_loader)

    progress_bar = tqdm(train_loader, desc=f"Training Epoch {epoch}")

    for batch_idx, (data, target, *rest) in enumerate(progress_bar):
        # Handle both cases where dataset returns 2 or 3 items
        if rest and isinstance(rest[0], dict):
            metadata = rest[0]
        else:
            metadata = {}

        data, target = data.to(device), target.to(device)

        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        # Update progress bar
        progress_bar.set_postfix({
            'Loss': f'{loss.item():.6f}',
            'AvgLoss': f'{total_loss/(batch_idx+1):.6f}'
        })

    avg_loss = total_loss / num_batches
    return avg_loss


def validate_epoch(model, val_loader, criterion, device):
    """Validate for one epoch."""
    model.eval()
    total_loss = 0.0
    num_batches = len(val_loader)

    # Storage for comprehensive loss metrics
    all_predictions = []
    all_targets = []
    sample_pairs = []

    with torch.no_grad():
        progress_bar = tqdm(val_loader, desc="Validation")

        for batch_idx, (data, target, *rest) in enumerate(progress_bar):
            if rest and isinstance(rest[0], dict):
                metadata = rest[0]
            else:
                metadata = {}

            data, target = data.to(device), target.to(device)

            output = model(data)
            loss = criterion(output, target)

            total_loss += loss.item()

            # Store predictions and targets for comprehensive loss calculation
            preds_cpu = output.detach().cpu()
            targets_cpu = target.detach().cpu()
            all_predictions.append(preds_cpu)
            all_targets.append(targets_cpu)

            if len(sample_pairs) < 5:
                preds_flat = preds_cpu.view(-1)
                targets_flat = targets_cpu.view(-1)
                for pred_val, target_val in zip(preds_flat, targets_flat):
                    sample_pairs.append((float(target_val), float(pred_val)))
                    if len(sample_pairs) >= 5:
                        break

            progress_bar.set_postfix({'ValLoss': f'{loss.item():.6f}'})

    avg_loss = total_loss / num_batches

    # Compute comprehensive loss metrics
    if all_predictions and all_targets:
        all_predictions_tensor = torch.cat(all_predictions, dim=0)
        all_targets_tensor = torch.cat(all_targets, dim=0)
        comprehensive_metrics = compute_all_metrics(all_predictions_tensor, all_targets_tensor)
    else:
        comprehensive_metrics = {'mse': 0.0, 'msre': 0.0, 'mare': 0.0, 'rmse': 0.0}

    return avg_loss, comprehensive_metrics, sample_pairs


def main():
    parser = argparse.ArgumentParser(description='PCT-Cap Training with Window-Level Splitting')
    parser.add_argument('--dataset-path', type=str, default='datasets',
                        help='Dataset directory path containing all subdirectories')
    parser.add_argument('--point-cloud-dir', type=str, default=None,
                        help='Directory containing point cloud NPZ files (default: <dataset-path>/point_clouds)')
    parser.add_argument('--spef-dir', type=str, default=None,
                        help='Directory containing SPEF files (default: <dataset-path>/labels_rwcap or labels_raphael)')
    parser.add_argument('--goal', type=str, choices=['self', 'coupling'], default='self',
                        help='Training goal: self or coupling capacitance')
    parser.add_argument('--npoints', type=int, default=1024,
                        help='Number of points per sample')
    parser.add_argument('--num-sa-layers', type=int, default=6,
                        help='Number of set abstraction layers in PCT-Cap backbone')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='Batch size for training')
    parser.add_argument('--epochs', type=int, default=100,
                        help='Number of training epochs')
    parser.add_argument('--lr', type=float, default=1e-4,
                        help='Learning rate')
    parser.add_argument('--val-split', type=float, default=0.2,
                        help='Validation split ratio')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('--gpu', type=int, default=0,
                        help='GPU index (-1 for CPU)')
    parser.add_argument('--num-workers', type=int, default=4,
                        help='Number of data loader workers')
    parser.add_argument('--output-dir', type=str, default='./pct_cap_results',
                        help='Output directory for checkpoints and logs')
    parser.add_argument('--save-every', type=int, default=10,
                        help='Save checkpoint every N epochs')

    args = parser.parse_args()

    # Handle dataset path - derive directories from dataset path if not explicitly provided
    dataset_path = Path(args.dataset_path)

    # Process node handling removed; datasets may contain mixed technologies
    process_node = None
    tech_file = None

    point_cloud_dir = Path(args.point_cloud_dir) if args.point_cloud_dir is not None else dataset_path / "point_clouds"

    if args.spef_dir is not None:
        spef_dir = Path(args.spef_dir).resolve()
    else:
        # Auto-select SPEF labels directory (prefer RWCap, fall back to Raphael)
        preferred_labels = ["labels_rwcap", "labels_raphael"]
        spef_dir = None
        for label_name in preferred_labels:
            candidate = dataset_path / label_name
            if candidate.exists():
                spef_dir = candidate.resolve()
                break
        if spef_dir is None:
            raise FileNotFoundError(
                f"No SPEF directory specified and default locations {preferred_labels} not found under {dataset_path}"
            )
        else:
            print(f"Auto-detected SPEF directory: {spef_dir}")

    # Set up device
    if args.gpu >= 0 and torch.cuda.is_available():
        device = torch.device(f'cuda:{args.gpu}')
        print(f"Using GPU: {args.gpu}")
    else:
        device = torch.device('cpu')
        print("Using CPU")

    # Set random seed
    set_seed(args.seed)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset from {point_cloud_dir}")
    print("Process node filtering disabled")
    print(f"Goal: {args.goal}")

    # Load full dataset
    full_dataset = PcCapNpzDataset(
        point_cloud_dir=point_cloud_dir,
        spef_dir=spef_dir,
        goal=args.goal,
        npoints=args.npoints,
        return_metadata=True,
    )

    print(f"Full dataset loaded: {len(full_dataset)} samples")

    # Create window-level splits
    train_ratio = 1.0 - args.val_split
    val_ratio = args.val_split

    train_dataset, val_dataset, test_dataset = create_window_level_splits(
        full_dataset,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=0.0,  # No test set for now
        random_seed=args.seed
    )

    # Verify no data leakage
    verify_no_data_leakage(train_dataset, val_dataset, test_dataset)

    print(f"Train dataset: {len(train_dataset)} samples")
    print(f"Validation dataset: {len(val_dataset)} samples")

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == 'cuda'
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == 'cuda'
    )

    # Initialize model
    print("Initializing model...")
    model = PCT_Cap(channels=8, num_sa=args.num_sa_layers, npoints=args.npoints)  # configurable SA blocks
    model = model.to(device)

    # Initialize optimizer and loss function
    criterion = CalLoss()
    if hasattr(criterion, 'to'):
        criterion = criterion.to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=args.lr,
        weight_decay=1e-6
    )

    # Learning rate scheduler
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=20, T_mult=2
    )

    # Initialize TensorBoard writer
    log_dir = output_dir / 'tensorboard'
    log_dir.mkdir(exist_ok=True)
    writer = SummaryWriter(log_dir=str(log_dir))
    print(f"TensorBoard logs will be saved to: {log_dir}")

    # Training loop
    print("Starting training...")
    best_val_loss = float('inf')
    train_losses = []
    val_losses = []

    for epoch in range(1, args.epochs + 1):
        print(f"\nEpoch {epoch}/{args.epochs}")
        print("-" * 50)

        # Train
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device, epoch)
        train_losses.append(train_loss)

        # Validate
        val_loss, comprehensive_metrics, sample_examples = validate_epoch(model, val_loader, criterion, device)
        val_losses.append(val_loss)

        # Update learning rate
        scheduler.step()

        print(f"Train Loss: {train_loss:.6f}")
        print(f"Val Loss: {val_loss:.6f}")
        print(f"Comprehensive Metrics - MSE: {comprehensive_metrics['mse']:.6f}, "
              f"MSRE: {comprehensive_metrics['msre']:.6f}, MARE: {comprehensive_metrics['mare']:.6f}, "
              f"RMSE: {comprehensive_metrics['rmse']:.6f}")
        print(f"Learning Rate: {optimizer.param_groups[0]['lr']:.6f}")

        if sample_examples:
            print("  Sample Predictions (Target → Predicted) [fF]:")
            for idx, (target_val, pred_val) in enumerate(sample_examples, start=1):
                error_pct = abs(pred_val - target_val) / (abs(target_val) + 1e-9) * 100.0
                print(f"    {idx}. {target_val:.6f} → {pred_val:.6f} fF (error: {error_pct:.1f}%)")

        # Log to TensorBoard
        writer.add_scalar('Loss/Train', train_loss, epoch)
        writer.add_scalar('Loss/Validation', val_loss, epoch)
        writer.add_scalar('Learning_Rate', optimizer.param_groups[0]['lr'], epoch)

        # Add comprehensive loss metrics to TensorBoard
        writer.add_scalar('Comprehensive/MSE', comprehensive_metrics['mse'], epoch)
        writer.add_scalar('Comprehensive/MSRE', comprehensive_metrics['msre'], epoch)
        writer.add_scalar('Comprehensive/MARE', comprehensive_metrics['mare'], epoch)
        writer.add_scalar('Comprehensive/RMSE', comprehensive_metrics['rmse'], epoch)

        # Save checkpoint
        if epoch % args.save_every == 0 or val_loss < best_val_loss:
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                is_best = True
            else:
                is_best = False

            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
                'args': args
            }

            # Save latest checkpoint
            checkpoint_path = output_dir / 'latest_checkpoint.pth'
            torch.save(checkpoint, checkpoint_path)

            # Save best checkpoint
            if is_best:
                best_path = output_dir / 'best_checkpoint.pth'
                torch.save(checkpoint, best_path)
                print(f"New best model saved with val_loss: {val_loss:.6f}")

            # Save epoch checkpoint
            epoch_path = output_dir / f'checkpoint_epoch_{epoch}.pth'
            torch.save(checkpoint, epoch_path)

        # Log progress
        log_entry = {
            'epoch': epoch,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'lr': optimizer.param_groups[0]['lr']
        }

        print(f"Epoch {epoch} completed. Train: {train_loss:.6f}, Val: {val_loss:.6f}")

    # Close TensorBoard writer
    writer.close()

    print("\nTraining completed!")
    print(f"Best validation loss: {best_val_loss:.6f}")
    print(f"Results saved to: {output_dir}")
    print(f"TensorBoard logs available at: {log_dir}")


if __name__ == '__main__':
    main()
