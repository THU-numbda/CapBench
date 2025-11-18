#!/usr/bin/env python3
"""Benchmark two-layer PyG models.

This script measures the samples-per-second throughput for simple two-layer
GCN, GAT, and GATv2 models using randomly generated graphs.  Each benchmark
reports both the throughput and the total parameter count so different
architectures can be compared apples-to-apples.  The script only relies on
synthetic data and is intended to be run manually; nothing executes on import.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Iterator, List, Tuple

import torch
from torch import nn
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GATConv, GATv2Conv, GCNConv, global_mean_pool


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

def _random_edge_index(num_nodes: int, num_edges: int) -> torch.Tensor:
    src = torch.randint(0, num_nodes, (num_edges,))
    dst = torch.randint(0, num_nodes, (num_edges,))
    return torch.stack([src, dst], dim=0)


def generate_random_graph(
    num_nodes: int,
    num_edges: int,
    in_channels: int,
) -> Data:
    """Create a single random graph sample."""

    x = torch.randn(num_nodes, in_channels)
    edge_index = _random_edge_index(num_nodes, num_edges)
    return Data(x=x, edge_index=edge_index)


def create_dataset(
    num_graphs: int,
    num_nodes: int,
    num_edges: int,
    in_channels: int,
) -> List[Data]:
    return [generate_random_graph(num_nodes, num_edges, in_channels) for _ in range(num_graphs)]


def infinite_loader(loader: DataLoader) -> Iterator:
    while True:
        for batch in loader:
            yield batch


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------


class TwoLayerGNN(nn.Module):
    """Minimal two-layer message passing network with global mean pooling."""

    def __init__(self, conv1: nn.Module, conv2: nn.Module, out_channels: int) -> None:
        super().__init__()
        self.conv1 = conv1
        self.conv2 = conv2
        self.activation = nn.ReLU()
        self.head = nn.Linear(out_channels, 1)

    def forward(self, batch: Data) -> torch.Tensor:
        x, edge_index = batch.x, batch.edge_index
        x = self.activation(self.conv1(x, edge_index))
        x = self.activation(self.conv2(x, edge_index))
        graph_emb = global_mean_pool(x, batch.batch)
        return self.head(graph_emb)


def build_model(
    model_name: str,
    in_channels: int,
    hidden_channels: int,
    out_channels: int,
    heads: int,
) -> TwoLayerGNN:
    model_name = model_name.lower()
    if model_name == "gcn":
        conv1 = GCNConv(in_channels, hidden_channels, add_self_loops=True)
        conv2 = GCNConv(hidden_channels, out_channels, add_self_loops=True)
    elif model_name == "gat":
        conv1 = GATConv(
            in_channels,
            hidden_channels,
            heads=heads,
            concat=False,
            dropout=0.0,
        )
        conv2 = GATConv(
            hidden_channels,
            out_channels,
            heads=heads,
            concat=False,
            dropout=0.0,
        )
    elif model_name == "gatv2":
        conv1 = GATv2Conv(
            in_channels,
            hidden_channels,
            heads=heads,
            concat=False,
            dropout=0.0,
        )
        conv2 = GATv2Conv(
            hidden_channels,
            out_channels,
            heads=heads,
            concat=False,
            dropout=0.0,
        )
    else:
        raise ValueError(f"Unsupported model '{model_name}'.")

    return TwoLayerGNN(conv1, conv2, out_channels)


# ---------------------------------------------------------------------------
# Benchmarking helpers
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    name: str
    samples_per_second: float
    param_count: int


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def benchmark(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    warmup_steps: int,
    timed_steps: int,
) -> Tuple[float, int]:
    model.to(device)
    model.eval()
    cyclic_loader = infinite_loader(loader)

    def next_batch() -> Data:
        return next(cyclic_loader).to(device)

    if device.type == "cuda":
        torch.cuda.synchronize()

    with torch.no_grad():
        for _ in range(warmup_steps):
            _ = model(next_batch())
            if device.type == "cuda":
                torch.cuda.synchronize()

        measured_samples = 0
        start_time = time.perf_counter()
        for _ in range(timed_steps):
            batch = next_batch()
            if device.type == "cuda":
                torch.cuda.synchronize()
            _ = model(batch)
            if device.type == "cuda":
                torch.cuda.synchronize()
            measured_samples += batch.num_graphs
        total_time = time.perf_counter() - start_time

    samples_per_second = measured_samples / total_time if total_time > 0 else 0.0
    return samples_per_second, count_parameters(model)


def format_results(results: List[BenchmarkResult]) -> str:
    header = f"{'Model':<10}{'Params':>15}{'Samples/s':>15}"
    lines = [header, "-" * len(header)]
    for result in results:
        lines.append(
            f"{result.name:<10}{result.param_count:>15,}{result.samples_per_second:>15.2f}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark simple 2-layer GNNs")
    parser.add_argument("--num-graphs", type=int, default=512)
    parser.add_argument("--num-nodes", type=int, default=200)
    parser.add_argument("--num-edges", type=int, default=800)
    parser.add_argument("--in-channels", type=int, default=32)
    parser.add_argument("--hidden-channels", type=int, default=128)
    parser.add_argument("--out-channels", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--warmup-steps", type=int, default=10)
    parser.add_argument("--timed-steps", type=int, default=50)
    parser.add_argument("--heads", type=int, default=4, help="Attention heads for GAT variants")
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device selection. 'auto' uses CUDA when available.",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=0,
        help="DataLoader worker processes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.manual_seed(0)

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    dataset = create_dataset(args.num_graphs, args.num_nodes, args.num_edges, args.in_channels)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        drop_last=False,
        num_workers=args.num_workers,
    )

    results: List[BenchmarkResult] = []
    for name in ("GCN", "GAT", "GATv2"):
        model = build_model(name, args.in_channels, args.hidden_channels, args.out_channels, args.heads)
        throughput, params = benchmark(
            model=model,
            loader=loader,
            device=device,
            warmup_steps=args.warmup_steps,
            timed_steps=args.timed_steps,
        )
        results.append(BenchmarkResult(name=name, samples_per_second=throughput, param_count=params))

    print(format_results(results))


if __name__ == "__main__":
    main()
