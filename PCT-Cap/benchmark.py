#!/usr/bin/env python3
"""
PCT-Cap Benchmark Script

Tests performance across different batch sizes for Point Cloud Transformer models
with configurable numbers of self-attention layers.
Includes warmup, statistical timing measurements, and memory monitoring.
"""

import argparse
import time
import csv
import os
import sys
from typing import Dict, List, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import PCT-Cap specific modules
try:
    from models.PCT_Cap import PCT_Cap
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
    from PCT_Cap import PCT_Cap


class PCTBenchmark:
    def __init__(self, device: str = 'auto'):
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"Using device: {self.device}")
        if self.device.type == 'cuda':
            print(f"GPU: {torch.cuda.get_device_name()}")
            print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    def generate_synthetic_data(self, batch_size: int, num_points: int = 1024,
                              num_features: int = 8) -> Tuple[torch.Tensor, torch.Tensor]:
        """Generate synthetic point cloud data for testing."""
        # Generate point coordinates (normalized to [-1, 1])
        points = torch.rand(batch_size, num_points, 3) * 2 - 1

        # Generate features (conductor type, density, etc.)
        features = torch.randn(batch_size, num_points, num_features - 3)

        # Concatenate coordinates and features
        x = torch.cat([points, features], dim=-1)  # (batch_size, num_points, num_features)

        # Generate targets (capacitance values)
        y = torch.randn(batch_size, 1) * 0.1 + 0.5  # Reasonable capacitance range

        x = x.to(self.device)
        y = y.to(self.device)

        return x, y

    def create_model(self, num_channels: int, num_sa_layers: int, num_points: int = 1024) -> nn.Module:
        """Create PCT-Cap model with specified parameters."""
        model = PCT_Cap(num_channels, num_sa_layers, num_points)
        model = model.to(self.device)
        return model

    def benchmark_batch_size(self, model: nn.Module, batch_size: int,
                           warmup_iters: int = 5, timed_iters: int = 100) -> Dict[str, float]:
        """Benchmark a specific batch size with warmup and timing."""
        model.eval()

        try:
            # Warmup iterations
            for _ in range(warmup_iters):
                with torch.no_grad():
                    x, y = self.generate_synthetic_data(batch_size)
                    _ = model(x)

                    if self.device.type == 'cuda':
                        torch.cuda.synchronize()

            # Reset memory tracking
            if self.device.type == 'cuda':
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.empty_cache()

            # Timed iterations
            times = []
            for _ in range(timed_iters):
                with torch.no_grad():
                    x, y = self.generate_synthetic_data(batch_size)

                    if self.device.type == 'cuda':
                        torch.cuda.synchronize()

                    start_time = time.perf_counter()
                    output = model(x)
                    loss = nn.MSELoss()(output, y)

                    if self.device.type == 'cuda':
                        torch.cuda.synchronize()

                    end_time = time.perf_counter()
                    times.append((end_time - start_time) * 1000)  # Convert to ms

            # Calculate statistics
            times = np.array(times)
            mean_time = np.mean(times)
            std_time = np.std(times)

            # Remove outliers (±2σ)
            valid_times = times[(times >= mean_time - 2*std_time) & (times <= mean_time + 2*std_time)]
            if len(valid_times) > 0:
                final_mean_time = np.mean(valid_times)
                final_std_time = np.std(valid_times)
                valid_count = len(valid_times)
            else:
                final_mean_time = mean_time
                final_std_time = std_time
                valid_count = len(times)

            # Calculate metrics
            time_per_sample = final_mean_time / batch_size
            throughput = batch_size / (final_mean_time / 1000)  # samples per second

            peak_memory = 0
            if self.device.type == 'cuda':
                peak_memory = torch.cuda.max_memory_allocated() / (1024**2)  # MB

            return {
                'batch_size': batch_size,
                'time_per_batch': final_mean_time,
                'time_per_batch_std': final_std_time,
                'time_per_sample': time_per_sample,
                'throughput': throughput,
                'peak_memory_mb': peak_memory,
                'valid_iterations': valid_count,
                'status': 'success'
            }

        except torch.cuda.OutOfMemoryError:
            return {
                'batch_size': batch_size,
                'time_per_batch': 0,
                'time_per_batch_std': 0,
                'time_per_sample': 0,
                'throughput': 0,
                'peak_memory_mb': 0,
                'valid_iterations': 0,
                'status': 'oom'
            }
        except Exception as e:
            return {
                'batch_size': batch_size,
                'time_per_batch': 0,
                'time_per_batch_std': 0,
                'time_per_sample': 0,
                'throughput': 0,
                'peak_memory_mb': 0,
                'valid_iterations': 0,
                'status': f'error: {str(e)}'
            }

    def find_max_batch_size(self, model: nn.Module, max_batch_size: int = 512) -> int:
        """Find maximum batch size that fits in memory using binary search."""
        min_batch = 1
        max_batch = max_batch_size

        # First find an upper bound that causes OOM
        while max_batch <= max_batch_size:
            result = self.benchmark_batch_size(model, max_batch,
                                             warmup_iters=1, timed_iters=1)
            if result['status'] == 'oom':
                break
            max_batch *= 2
            if max_batch > max_batch_size:
                max_batch = max_batch_size
                break

        # Binary search for the maximum working batch size
        best_batch = min_batch
        while min_batch <= max_batch:
            mid_batch = (min_batch + max_batch) // 2
            result = self.benchmark_batch_size(model, mid_batch,
                                             warmup_iters=1, timed_iters=1)

            if result['status'] == 'success':
                best_batch = mid_batch
                min_batch = mid_batch + 1
            else:
                max_batch = mid_batch - 1

        return best_batch

    def run_benchmark(self, num_sa_layers_list: List[int], num_channels: int = 8,
                     num_points: int = 1024, batch_sizes: Optional[List[int]] = None) -> Dict[str, List[Dict]]:
        """Run comprehensive benchmark for specified layer counts."""
        results = {}

        for num_sa_layers in num_sa_layers_list:
            config_name = f"pct_{num_sa_layers}layers"
            print(f"\n{'='*80}")
            print(f"Benchmarking PCT-Cap with {num_sa_layers} self-attention layers")
            print(f"{'='*80}")

            try:
                # Create model
                model = self.create_model(num_channels, num_sa_layers, num_points)

                num_params = sum(p.numel() for p in model.parameters())
                print(f"Model created with {num_params:,} parameters")

                # Find batch sizes to test
                if batch_sizes is None:
                    max_batch = self.find_max_batch_size(model)
                    # Test powers of 2 up to max_batch
                    test_sizes = []
                    size = 1
                    while size <= max_batch:
                        test_sizes.append(size)
                        size *= 2
                    if test_sizes[-1] != max_batch:
                        test_sizes.append(max_batch)
                else:
                    test_sizes = [bs for bs in batch_sizes if bs > 0]

                print(f"Testing batch sizes: {test_sizes}")

                # Run benchmarks
                model_results = []
                for batch_size in test_sizes:
                    print(f"  Testing batch size {batch_size:4d} ... ", end='', flush=True)

                    result = self.benchmark_batch_size(model, batch_size)
                    model_results.append(result)

                    if result['status'] == 'success':
                        print(f"✓ {result['time_per_sample']:.2f} ms/sample, "
                              f"{result['throughput']:.1f} samples/s, "
                              f"{result['peak_memory_mb']:.0f} MB")
                    else:
                        print(f"✗ {result['status']}")

                results[config_name] = model_results

                # Clean up
                del model
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()

            except Exception as e:
                print(f"Error creating model with {num_sa_layers} layers: {e}")
                results[config_name] = []

        return results

    def print_results_table(self, results: Dict[str, List[Dict]]):
        """Print results as nicely formatted tables."""
        for config_name, model_results in results.items():
            if not model_results:
                continue

            print(f"\n{config_name.upper()} Benchmark Results")
            print("=" * (len(config_name) + 17))
            print("-" * (len(config_name) + 17))

            # Table header
            header = f"{'Batch Size':>10} | {'Time/Sample (ms)':>16} | {'Throughput (samples/s)':>21} | {'Memory (MB)':>11} | {'Iterations':>11}"
            print(header)
            print("-" * len(header))

            # Table rows
            for result in model_results:
                if result['status'] == 'success':
                    row = f"{result['batch_size']:10d} | {result['time_per_sample']:16.2f} | {result['throughput']:21.1f} | {result['peak_memory_mb']:11.0f} | {result['valid_iterations']:11d}"
                else:
                    row = f"{result['batch_size']:10d} | {'-':>16} | {'-':>21} | {'-':>11} | {'-':>11}"
                print(row)

            print()

    def save_results_csv(self, results: Dict[str, List[Dict]], filename: str):
        """Save results to CSV file."""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['config_name', 'num_layers', 'batch_size', 'time_per_sample_ms',
                         'throughput_samples_per_sec', 'peak_memory_mb',
                         'valid_iterations', 'status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for config_name, model_results in results.items():
                num_layers = int(config_name.split('_')[1].replace('layers', ''))
                for result in model_results:
                    writer.writerow({
                        'config_name': config_name,
                        'num_layers': num_layers,
                        'batch_size': result['batch_size'],
                        'time_per_sample_ms': f"{result['time_per_sample']:.4f}" if result['status'] == 'success' else '',
                        'throughput_samples_per_sec': f"{result['throughput']:.2f}" if result['status'] == 'success' else '',
                        'peak_memory_mb': f"{result['peak_memory_mb']:.1f}" if result['status'] == 'success' else '',
                        'valid_iterations': result['valid_iterations'],
                        'status': result['status']
                    })

        print(f"Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description='PCT-Cap Performance Benchmark')
    parser.add_argument('--num-layers', type=str, default='6',
                       help='Comma-separated list of self-attention layer counts (default: 6)')
    parser.add_argument('--num-channels', type=int, default=8,
                       help='Number of input channels (default: 8)')
    parser.add_argument('--num-points', type=int, default=1024,
                       help='Number of points per point cloud (default: 1024)')
    parser.add_argument('--batch-sizes', type=str, default=None,
                       help='Comma-separated list of batch sizes to test (default: auto-detect)')
    parser.add_argument('--device', type=str, default='auto',
                       choices=['auto', 'cuda', 'cpu'],
                       help='Device to use (default: auto)')
    parser.add_argument('--output', type=str, default='pct_benchmark_results.csv',
                       help='Output CSV file (default: pct_benchmark_results.csv)')

    args = parser.parse_args()

    # Parse arguments
    num_layers_list = [int(nl.strip()) for nl in args.num_layers.split(',')]

    if args.batch_sizes:
        batch_sizes = [int(bs.strip()) for bs in args.batch_sizes.split(',')]
    else:
        batch_sizes = None

    # Run benchmark
    benchmark = PCTBenchmark(device=args.device)
    results = benchmark.run_benchmark(num_layers_list, args.num_channels,
                                    args.num_points, batch_sizes)

    # Display results
    benchmark.print_results_table(results)

    # Save results
    benchmark.save_results_csv(results, args.output)


if __name__ == '__main__':
    main()