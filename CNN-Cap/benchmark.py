#!/usr/bin/env python3
"""
CNN-Cap Benchmark Script

Tests performance across different batch sizes for various ResNet architectures.
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

# Import CNN-Cap specific modules
import resnet_custom


def get_model(typ: str, num_input_channels: int):
    """
    Get model with specified number of input channels
    Args:
        typ: Model type (resnet18, resnet34, resnet50, resnet50_no_avgpool)
        num_input_channels: Number of input channels
    Returns:
        Model instance
    """
    if typ == "resnet34":
        return resnet_custom.resnet34(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet50":
        return resnet_custom.resnet50(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet101":
        return resnet_custom.resnet101(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet18":
        return resnet_custom.resnet18(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet50_no_avgpool":
        return resnet_custom.resnet50_no_avgpool(num_classes=1, num_input_channels=num_input_channels)
    else:
        raise NotImplementedError(f"Model type {typ} not implemented")


class CNNBenchmark:
    def __init__(self, device: str = 'auto'):
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"Using device: {self.device}")
        if self.device.type == 'cuda':
            print(f"GPU: {torch.cuda.get_device_name()}")
            print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    def generate_synthetic_data(self, batch_size: int, num_channels: int = 8,
                              height: int = 224, width: int = 224) -> Tuple[torch.Tensor, torch.Tensor]:
        """Generate synthetic density map data for testing."""
        # Create realistic density maps with some structure
        x = torch.randn(batch_size, num_channels, height, width)

        # Add some structured patterns to make it more realistic
        for i in range(batch_size):
            for ch in range(num_channels):
                # Add a few random rectangular regions with higher density
                for _ in range(np.random.randint(1, 4)):
                    y1, y2 = sorted(np.random.randint(0, height, 2))
                    x1, x2 = sorted(np.random.randint(0, width, 2))
                    x[i, ch, y1:y2, x1:x2] += np.random.uniform(0.5, 2.0)

        # Clamp to reasonable density values
        x = torch.clamp(x, 0.0, 5.0)

        # Generate targets (capacitance values)
        y = torch.randn(batch_size, 1) * 0.1 + 0.5  # Reasonable capacitance range

        x = x.to(self.device)
        y = y.to(self.device)

        return x, y

    def benchmark_batch_size(self, model: nn.Module, batch_size: int, num_channels: int,
                           warmup_iters: int = 5, timed_iters: int = 100) -> Dict[str, float]:
        """Benchmark a specific batch size with warmup and timing."""
        model.eval()

        try:
            # Warmup iterations
            for _ in range(warmup_iters):
                with torch.no_grad():
                    x, y = self.generate_synthetic_data(batch_size, num_channels)
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
                    x, y = self.generate_synthetic_data(batch_size, num_channels)

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

    def find_max_batch_size(self, model: nn.Module, num_channels: int,
                          max_batch_size: int = 1024) -> int:
        """Find maximum batch size that fits in memory using binary search."""
        min_batch = 1
        max_batch = max_batch_size

        # First find an upper bound that causes OOM
        while max_batch <= max_batch_size:
            result = self.benchmark_batch_size(model, max_batch, num_channels,
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
            result = self.benchmark_batch_size(model, mid_batch, num_channels,
                                             warmup_iters=1, timed_iters=1)

            if result['status'] == 'success':
                best_batch = mid_batch
                min_batch = mid_batch + 1
            else:
                max_batch = mid_batch - 1

        return best_batch

    def run_benchmark(self, model_types: List[str], num_channels: int = 8,
                     batch_sizes: Optional[List[int]] = None) -> Dict[str, List[Dict]]:
        """Run comprehensive benchmark for specified models."""
        results = {}

        for model_type in model_types:
            print(f"\n{'='*80}")
            print(f"Benchmarking {model_type.upper()}")
            print(f"{'='*80}")

            try:
                # Create model
                model = get_model(model_type, num_channels)
                model = model.to(self.device)

                print(f"Model created with {sum(p.numel() for p in model.parameters()):,} parameters")

                # Find batch sizes to test
                if batch_sizes is None:
                    max_batch = self.find_max_batch_size(model, num_channels)
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

                    result = self.benchmark_batch_size(model, batch_size, num_channels)
                    model_results.append(result)

                    if result['status'] == 'success':
                        print(f"✓ {result['time_per_sample']:.2f} ms/sample, "
                              f"{result['throughput']:.1f} samples/s, "
                              f"{result['peak_memory_mb']:.0f} MB")
                    else:
                        print(f"✗ {result['status']}")

                results[model_type] = model_results

                # Clean up
                del model
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()

            except Exception as e:
                print(f"Error creating model {model_type}: {e}")
                results[model_type] = []

        return results

    def print_results_table(self, results: Dict[str, List[Dict]]):
        """Print results as nicely formatted tables."""
        for model_type, model_results in results.items():
            if not model_results:
                continue

            print(f"\n{model_type.upper()} Benchmark Results")
            print("=" * (len(model_type) + 17))
            print("-" * (len(model_type) + 17))

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
            fieldnames = ['model_type', 'batch_size', 'time_per_sample_ms',
                         'throughput_samples_per_sec', 'peak_memory_mb',
                         'valid_iterations', 'status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for model_type, model_results in results.items():
                for result in model_results:
                    writer.writerow({
                        'model_type': model_type,
                        'batch_size': result['batch_size'],
                        'time_per_sample_ms': f"{result['time_per_sample']:.4f}" if result['status'] == 'success' else '',
                        'throughput_samples_per_sec': f"{result['throughput']:.2f}" if result['status'] == 'success' else '',
                        'peak_memory_mb': f"{result['peak_memory_mb']:.1f}" if result['status'] == 'success' else '',
                        'valid_iterations': result['valid_iterations'],
                        'status': result['status']
                    })

        print(f"Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description='CNN-Cap Performance Benchmark')
    parser.add_argument('--model-types', type=str, default='resnet34',
                       help='Comma-separated list of model types (resnet18,resnet34,resnet50,resnet101,resnet50_no_avgpool)')
    parser.add_argument('--num-channels', type=int, default=8,
                       help='Number of input channels (default: 8)')
    parser.add_argument('--batch-sizes', type=str, default=None,
                       help='Comma-separated list of batch sizes to test (default: auto-detect)')
    parser.add_argument('--device', type=str, default='auto',
                       choices=['auto', 'cuda', 'cpu'],
                       help='Device to use (default: auto)')
    parser.add_argument('--output', type=str, default='benchmark_results.csv',
                       help='Output CSV file (default: benchmark_results.csv)')

    args = parser.parse_args()

    # Parse arguments
    model_types = [mt.strip() for mt in args.model_types.split(',')]

    if args.batch_sizes:
        batch_sizes = [int(bs.strip()) for bs in args.batch_sizes.split(',')]
    else:
        batch_sizes = None

    # Run benchmark
    benchmark = CNNBenchmark(device=args.device)
    results = benchmark.run_benchmark(model_types, args.num_channels, batch_sizes)

    # Display results
    benchmark.print_results_table(results)

    # Save results
    benchmark.save_results_csv(results, args.output)


if __name__ == '__main__':
    main()