"""
Training entry point for the minimal two-layer GNN models.
"""

import argparse
import os
import sys
from pathlib import Path

import torch
from pytorch_lightning import seed_everything

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils.dataloader import (
    create_data_splits,
    create_filtered_dataset,
    get_data_loader,
)
from lightning_module import GNNCapLightningModule, create_trainer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train 2-layer GNN-Cap models.")
    parser.add_argument("--dataset-path", default="datasets", help="Dataset root directory.")
    parser.add_argument("--data-dir", default=None, help="Directory containing .pt graphs.")
    parser.add_argument("--spef-dir", default=None, help="Directory containing SPEF label files.")
    parser.add_argument("--spef-files", nargs="*", default=None, help="Explicit SPEF file list.")
    parser.add_argument(
        "--labels-solver",
        choices=["auto", "rwcap", "raphael"],
        default="auto",
        help="Preferred SPEF solver for labels.",
    )
    parser.add_argument(
        "--conv-type",
        choices=["gcn", "gat", "gatv2"],
        default="gat",
        help="Graph convolution type to use for both layers.",
    )
    parser.add_argument(
        "--hidden-dims",
        nargs=2,
        type=int,
        default=[128, 256],
        metavar=("L1", "L2"),
        help="Hidden dimensions for the two message passing layers.",
    )
    parser.add_argument(
        "--heads",
        type=int,
        default=4,
        help="Attention heads for GAT/GATv2 layers (ignored for GCN).",
    )
    parser.add_argument(
        "--aggregation-hidden",
        type=int,
        default=128,
        help="Hidden dimension inside the self-attention aggregator.",
    )
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs.")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate.")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience.")
    parser.add_argument("--gpus", type=int, default=1, help="Number of GPUs to use.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--checkpoint-dir", default="./checkpoints", help="Checkpoint directory.")
    parser.add_argument("--log-dir", default="./logs", help="PyTorch Lightning log directory.")
    return parser.parse_args()


def main():
    args = parse_args()
    seed_everything(args.seed, workers=True)

    if torch.cuda.is_available():
        torch.set_float32_matmul_precision("high")

    data_dir = Path(args.data_dir) if args.data_dir else Path(args.dataset_path) / "graphs"
    print("=" * 60)
    print(f"Training two-layer model with {args.conv_type.upper()} layers")
    print(f"Graph directory : {data_dir}")
    print(f"Hidden dims     : {args.hidden_dims}")
    print(f"Attention heads : {args.heads if args.conv_type != 'gcn' else 'N/A (GCN)'}")
    print(f"Aggregation dim : {args.aggregation_hidden}")
    print(f"Learning rate   : {args.lr}")
    print("=" * 60)

    dataset = create_filtered_dataset(
        data_dir=data_dir,
        label_type="total",
        spef_dir=args.spef_dir,
        spef_files=args.spef_files,
        solver_preference=args.labels_solver,
    )
    train_data, val_data, _ = create_data_splits(dataset)
    train_loader = get_data_loader(train_data, shuffle=True)
    val_loader = get_data_loader(val_data, shuffle=False)

    model = GNNCapLightningModule(
        learning_rate=args.lr,
        hidden_dims=tuple(args.hidden_dims),
        conv_type=args.conv_type,
        heads=args.heads,
        aggregation_hidden_dim=args.aggregation_hidden,
    )

    trainer = create_trainer(
        max_epochs=args.epochs,
        patience=args.patience,
        checkpoint_dir=args.checkpoint_dir,
        log_dir=args.log_dir,
        run_name=args.conv_type,
        accelerator="gpu" if args.gpus > 0 else "cpu",
        devices=args.gpus if args.gpus > 0 else 1,
    )
    trainer.fit(model, train_loader, val_loader)
    print("\nTraining complete.")
    print(f"Best validation loss: {trainer.callback_metrics.get('val_loss', 'N/A')}")


if __name__ == "__main__":
    main()
