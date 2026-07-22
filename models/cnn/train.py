#!/usr/bin/env python3
"""Train the maintained CNN-Cap ResNet baseline on cached density windows."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from capbench.dataloaders import make_window_grouped_batch_sampler
from capbench.datasets import resolve_dataset_path
from capbench.training import (
    compute_all_metrics,
    create_window_level_splits,
    verify_no_data_leakage,
)
from capbench.window_density_dataset import WindowCapDataset

import resnet_custom

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:  # pragma: no cover - optional logging dependency
    SummaryWriter = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-path",
        default="nangate45/small",
        help="Installed CapBench dataset id or explicit dataset directory.",
    )
    parser.add_argument("--window-dir", default=None, help="Override density_maps directory.")
    parser.add_argument("--spef-dir", default=None, help="Override SPEF label directory.")
    parser.add_argument(
        "--labels-solver",
        choices=("auto", "rwcap", "raphael"),
        default="auto",
    )
    parser.add_argument("--goal", choices=("self", "coupling"), default="self")
    parser.add_argument(
        "--model-type",
        choices=("resnet18", "resnet34", "resnet50", "resnet101"),
        default="resnet34",
    )
    parser.add_argument("--required-layers", nargs="+", default=None)
    parser.add_argument("--window-ids", nargs="*", default=None)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--build-workers", type=int, default=0)
    parser.add_argument("--window-cache-size", type=int, default=4)
    parser.add_argument("--output-dir", default="diagnostics/cnn")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def resolve_device(requested: str) -> torch.device:
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda was requested, but CUDA is unavailable")
    if requested == "auto":
        requested = "cuda" if torch.cuda.is_available() else "cpu"
    return torch.device(requested)


def resolve_label_dir(dataset_root: Path, requested: str | None, preference: str) -> Path:
    if requested is not None:
        path = Path(requested).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(path)
        return path
    names = ("labels_rwcap", "labels_raphael")
    if preference == "raphael":
        names = tuple(reversed(names))
    for name in names:
        path = dataset_root / name
        if path.is_dir():
            return path
    raise FileNotFoundError(f"No SPEF label directory found under {dataset_root}")


def build_model(model_type: str, channels: int) -> torch.nn.Module:
    constructor = getattr(resnet_custom, model_type)
    return constructor(num_classes=1, num_input_channels=channels)


def msre_loss(predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    denominator = targets.abs().clamp_min(1e-8)
    return (((predictions - targets) / denominator) ** 2).mean()


def unpack_batch(batch) -> tuple[torch.Tensor, torch.Tensor]:
    if not isinstance(batch, (tuple, list)) or len(batch) < 2:
        raise TypeError("CNN dataset batches must contain features and targets")
    return batch[0], batch[1]


def run_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    *,
    optimizer: torch.optim.Optimizer | None,
    description: str,
) -> tuple[float, dict[str, float]]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_samples = 0
    predictions: list[torch.Tensor] = []
    targets: list[torch.Tensor] = []

    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for batch in tqdm(loader, desc=description):
            features, target = unpack_batch(batch)
            features = features.to(device, non_blocking=True)
            target = target.to(device, non_blocking=True).view(-1, 1)
            prediction = model(features).view_as(target)
            loss = msre_loss(prediction, target)

            if training:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            batch_size = int(target.shape[0])
            total_loss += float(loss.detach()) * batch_size
            total_samples += batch_size
            predictions.append(prediction.detach().cpu())
            targets.append(target.detach().cpu())

    if total_samples == 0:
        raise RuntimeError(f"{description} loader produced no samples")
    metrics = compute_all_metrics(torch.cat(predictions), torch.cat(targets))
    return total_loss / total_samples, metrics


def save_checkpoint(
    path: Path,
    *,
    epoch: int,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    args: argparse.Namespace,
    metrics: dict[str, float],
) -> None:
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "arguments": vars(args),
            "validation_metrics": metrics,
        },
        path,
    )


def main() -> int:
    args = parse_args()
    if not 0.0 < args.val_split < 1.0:
        raise ValueError("--val-split must be between zero and one")
    set_seed(args.seed)
    device = resolve_device(args.device)

    dataset_root = resolve_dataset_path(
        args.dataset_path,
        artifacts=() if args.window_dir else ("density_maps",),
    )
    window_dir = (
        Path(args.window_dir).expanduser().resolve()
        if args.window_dir
        else dataset_root / "density_maps"
    )
    spef_dir = resolve_label_dir(dataset_root, args.spef_dir, args.labels_solver)
    selected_windows: Iterable[str] | None = args.window_ids
    if selected_windows is None and args.max_windows > 0:
        selected_windows = WindowCapDataset.discover_limited_windows(
            window_dir,
            args.max_windows,
            spef_dir,
        )

    dataset = WindowCapDataset(
        window_dir=window_dir,
        spef_dir=spef_dir,
        window_ids=selected_windows,
        goal=args.goal,
        solver_preference=args.labels_solver,
        required_layers=args.required_layers,
        build_workers=args.build_workers,
        window_cache_size=args.window_cache_size,
    )
    train_data, val_data, test_data = create_window_level_splits(
        dataset,
        train_ratio=1.0 - args.val_split,
        val_ratio=args.val_split,
        test_ratio=0.0,
        random_seed=args.seed,
    )
    verify_no_data_leakage(train_data, val_data, test_data)

    train_batches = make_window_grouped_batch_sampler(
        train_data,
        args.batch_size,
        shuffle=True,
        seed=args.seed,
    )
    val_batches = make_window_grouped_batch_sampler(
        val_data,
        args.batch_size,
        shuffle=False,
        seed=args.seed,
    )
    loader_kwargs = {
        "num_workers": args.num_workers,
        "pin_memory": device.type == "cuda",
        "persistent_workers": args.num_workers > 0,
    }
    train_loader = DataLoader(train_data, batch_sampler=train_batches, **loader_kwargs)
    val_loader = DataLoader(val_data, batch_sampler=val_batches, **loader_kwargs)

    model = build_model(args.model_type, dataset.num_layers).to(device)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(str(output_dir / "tensorboard")) if SummaryWriter else None

    print(f"Dataset: {dataset_root}")
    print(f"Layers: {dataset.active_layers}")
    print(f"Model: {args.model_type} ({sum(p.numel() for p in model.parameters()):,} parameters)")
    print(f"Device: {device}")

    best_mare = float("inf")
    for epoch in range(1, args.epochs + 1):
        train_loss, train_metrics = run_epoch(
            model,
            train_loader,
            device,
            optimizer=optimizer,
            description=f"train {epoch}/{args.epochs}",
        )
        val_loss, val_metrics = run_epoch(
            model,
            val_loader,
            device,
            optimizer=None,
            description=f"validation {epoch}/{args.epochs}",
        )
        print(
            f"epoch={epoch} train_msre={train_loss:.6f} "
            f"val_msre={val_loss:.6f} val_mape={100.0 * val_metrics['mare']:.4f}%"
        )
        if writer:
            writer.add_scalar("train/msre", train_metrics["msre"], epoch)
            writer.add_scalar("train/mare", train_metrics["mare"], epoch)
            writer.add_scalar("val/msre", val_metrics["msre"], epoch)
            writer.add_scalar("val/mare", val_metrics["mare"], epoch)

        save_checkpoint(
            output_dir / "latest_checkpoint.pth",
            epoch=epoch,
            model=model,
            optimizer=optimizer,
            args=args,
            metrics=val_metrics,
        )
        if val_metrics["mare"] < best_mare:
            best_mare = val_metrics["mare"]
            save_checkpoint(
                output_dir / "best_checkpoint.pth",
                epoch=epoch,
                model=model,
                optimizer=optimizer,
                args=args,
                metrics=val_metrics,
            )

    if writer:
        writer.close()
    print(f"Best validation MAPE: {100.0 * best_mare:.4f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
