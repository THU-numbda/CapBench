"""
GNN-Cap Training Script using PyTorch Lightning

Simple, clean training with automatic device management, gradient handling,
and checkpointing. No complex configuration - just train your models.
"""

import sys
import os
from pathlib import Path
import argparse
from typing import Optional

import torch
import pytorch_lightning as pl
from pytorch_lightning import seed_everything

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils.dataloader import CapacitanceDataset, create_filtered_dataset, create_data_splits, get_data_loader
from lightning_module import GNNCapLightningModule, create_trainer


def main():
    """Main training function with PyTorch Lightning"""
    parser = argparse.ArgumentParser(description='Train GNN-Cap models with PyTorch Lightning')

    # Data arguments
    parser.add_argument('--dataset-path', default='datasets', help='Dataset directory path')
    parser.add_argument('--data-dir', default=None, help='Directory with graph .pt files')
    parser.add_argument('--spef-dir', default=None, help='Directory containing SPEF label files')
    parser.add_argument('--spef-files', nargs='*', default=None, help='Explicit SPEF files')
    parser.add_argument('--labels-solver', choices=['auto', 'rwcap', 'raphael'], default='auto',
                        help='Preferred SPEF solver')

    # Model arguments
    parser.add_argument('--model-type', choices=['total', 'coupling', 'both'], default='total',
                        help='Which model to train')
    parser.add_argument('--num-layers', type=int, default=2,
                        help='Number of graph convolution layers (default: 2)')
    parser.add_argument('--use-attention', action='store_true',
                        help='Enable attention mechanism')
    parser.add_argument('--attention-type', choices=['gat', 'gatv2'], default='gat',
                        help='Attention type: gat (standard) or gatv2 (improved)')
    parser.add_argument('--heads', type=int, default=4,
                        help='Number of attention heads (default: 4)')
    parser.add_argument('--net-aggregation', choices=['none', 'mean', 'self_attention'],
                        default='self_attention',
                        help='Net-level aggregation method for total capacitance')
    parser.add_argument('--net-aggregation-hidden', type=int, default=128,
                        help='Hidden dimension for self-attention aggregation')

    # Training arguments
    parser.add_argument('--epochs', type=int, default=50, help='Number of epochs')
    parser.add_argument('--lr', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--patience', type=int, default=10, help='Early stopping patience')

    # System arguments
    parser.add_argument('--gpus', type=int, default=1, help='Number of GPUs to use')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--checkpoint-dir', default='./checkpoints', help='Checkpoint directory')
    parser.add_argument('--log-dir', default='./logs', help='Log directory')

    args = parser.parse_args()

    # Set random seed for reproducibility
    seed_everything(args.seed, workers=True)

    # Configure CUDA for optimal Tensor Core usage on RTX 4090
    if torch.cuda.is_available():
        torch.set_float32_matmul_precision('high')
        print(f"CUDA Tensor Core precision set to 'high' for RTX 4090 optimization")

    # Determine data directory
    if args.data_dir is None:
        dataset_path = Path(args.dataset_path)
        data_dir = dataset_path / "graphs"
    else:
        data_dir = Path(args.data_dir)

    print(f"Loading data from: {data_dir}")
    print(f"Model type: {args.model_type}")
    print(f"Number of GNN layers: {args.num_layers}")
    print(f"Attention: {'Enabled' if args.use_attention else 'Disabled'}")
    if args.use_attention:
        print(f"Attention type: {args.attention_type.upper()}")
        print(f"Attention heads: {args.heads}")
    print(f"Net aggregation: {args.net_aggregation}")
    print(f"Batch size: 1 (fixed for stable training of variable-sized graphs)")
    print(f"Learning rate: {args.lr}")
    print("=" * 60)

    # Determine data directory for validation
    val_data_dir = args.data_dir or str(data_dir)

    # Train models
    if args.model_type in ['total', 'both']:
        print("\n" + "="*60)
        print("TRAINING TOTAL CAPACITANCE MODEL")
        print("="*60)

        # Create filtered dataset (only graphs with SPEF files)
        train_dataset = create_filtered_dataset(
            data_dir=data_dir,
            label_type='total',
            spef_dir=args.spef_dir,
            spef_files=args.spef_files,
            solver_preference=args.labels_solver,
        )

        # Create data splits
        train_data, val_data, test_data = create_data_splits(train_dataset)

        # Create data loaders (batch_size fixed at 1 for stable training)
        train_loader = get_data_loader(train_data, shuffle=True)
        val_loader = get_data_loader(val_data, shuffle=False)

        print(f"Training samples: {len(train_data)}")
        print(f"Validation samples: {len(val_data)}")

        # Create Lightning module
        model = GNNCapLightningModule(
            model_type='total',
            learning_rate=args.lr,
            use_virtual_edges=True,
            num_layers=args.num_layers,
            use_attention=args.use_attention,
            heads=args.heads,
            attention_type=args.attention_type,
            aggregation=args.net_aggregation,
            aggregation_hidden_dim=args.net_aggregation_hidden,
        )

        # Create trainer
        trainer = create_trainer(
            max_epochs=args.epochs,
            patience=args.patience,
            checkpoint_dir=f"{args.checkpoint_dir}/total",
            log_dir=f"{args.log_dir}/total",
            model_type='total',
            accelerator='gpu' if args.gpus > 0 else 'cpu',
            devices=args.gpus if args.gpus > 0 else 1,
        )

        # Train model
        trainer.fit(model, train_loader, val_loader)

        # Print final results
        print(f"\nTotal model training completed!")
        print(f"Best validation loss: {trainer.callback_metrics.get('val_loss', 'N/A')}")

    if args.model_type in ['coupling', 'both']:
        print("\n" + "="*60)
        print("TRAINING COUPLING CAPACITANCE MODEL")
        print("="*60)

        # Create filtered dataset (only graphs with SPEF files)
        train_dataset = create_filtered_dataset(
            data_dir=data_dir,
            label_type='coupling',
            spef_dir=args.spef_dir,
            spef_files=args.spef_files,
            solver_preference=args.labels_solver,
        )

        # Create data splits
        train_data, val_data, test_data = create_data_splits(train_dataset)

        # Create data loaders (batch_size fixed at 1 for stable training)
        train_loader = get_data_loader(train_data, shuffle=True)
        val_loader = get_data_loader(val_data, shuffle=False)

        print(f"Training samples: {len(train_data)}")
        print(f"Validation samples: {len(val_data)}")

        # Create Lightning module
        model = GNNCapLightningModule(
            model_type='coupling',
            learning_rate=args.lr,
            use_virtual_edges=True,
            num_layers=args.num_layers,
            use_attention=args.use_attention,
            heads=args.heads,
            attention_type=args.attention_type,
            aggregation='none',
            aggregation_hidden_dim=args.net_aggregation_hidden,
        )

        # Create trainer
        trainer = create_trainer(
            max_epochs=args.epochs,
            patience=args.patience,
            checkpoint_dir=f"{args.checkpoint_dir}/coupling",
            log_dir=f"{args.log_dir}/coupling",
            model_type='coupling',
            accelerator='gpu' if args.gpus > 0 else 'cpu',
            devices=args.gpus if args.gpus > 0 else 1,
        )

        # Train model
        trainer.fit(model, train_loader, val_loader)

        # Print final results
        print(f"\nCoupling model training completed!")
        print(f"Best validation loss: {trainer.callback_metrics.get('val_loss', 'N/A')}")

    print("\n" + "="*60)
    print("TRAINING COMPLETED SUCCESSFULLY!")
    print("="*60)


if __name__ == "__main__":
    main()
