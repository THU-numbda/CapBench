#!/usr/bin/env python3
"""
Window Statistics Analysis for CAP3D Datasets

This script analyzes CAP3D files across all datasets to count blocks and conductors
in each window file, providing comprehensive statistics for each technology node.

Usage:
    python scripts/analyze_window_statistics.py
    python scripts/analyze_window_statistics.py --output-dir results/
    python scripts/analyze_window_statistics.py --csv-export
"""

import sys
import os
from pathlib import Path
import argparse
import json
import csv
from typing import Dict, List, Tuple, NamedTuple
from dataclasses import dataclass
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import time
from tqdm import tqdm

# Add project root to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from window_tools.cap3d_parser import StreamingCap3DParser


@dataclass
class WindowStats:
    """Statistics for a single window file"""
    file_path: str
    dataset_name: str
    block_count: int
    conductor_count: int
    has_error: bool = False
    error_message: str = ""


@dataclass
class DatasetStats:
    """Aggregated statistics for a dataset"""
    name: str
    total_files: int
    successful_files: int
    failed_files: int
    block_stats: Dict[str, float]
    conductor_stats: Dict[str, float]
    total_blocks: int
    total_conductors: int


class WindowStatisticsAnalyzer:
    """Analyzes window statistics across CAP3D datasets"""

    def __init__(self, datasets_dir: Path = None):
        if datasets_dir is None:
            # Default to datasets directory in repo root
            self.datasets_dir = repo_root / 'datasets'
        else:
            self.datasets_dir = Path(datasets_dir)

        self.results: Dict[str, List[WindowStats]] = defaultdict(list)

    def discover_datasets(self) -> Dict[str, Path]:
        """Discover all CAP3D datasets"""
        datasets = {}

        if not self.datasets_dir.exists():
            print(f"ERROR: Datasets directory not found: {self.datasets_dir}")
            return datasets

        print(f"Scanning for datasets in: {self.datasets_dir}")

        # Look for technology directories (asap7, nangate45, sky130hd, etc.)
        for tech_dir in self.datasets_dir.iterdir():
            if not tech_dir.is_dir():
                continue

            # Look for size subdirectories (small, large, etc.)
            for size_dir in tech_dir.iterdir():
                if not size_dir.is_dir():
                    continue

                # Look for cap3d subdirectory
                cap3d_dir = size_dir / 'cap3d'
                if cap3d_dir.exists() and cap3d_dir.is_dir():
                    dataset_name = f"{tech_dir.name}_{size_dir.name}"
                    datasets[dataset_name] = cap3d_dir
                    print(f"  Found dataset: {dataset_name} -> {cap3d_dir}")

        return datasets

    def analyze_single_file(self, file_path: Path, dataset_name: str) -> WindowStats:
        """Analyze a single CAP3D file for block and conductor counts"""
        try:
            block_count = 0
            conductor_count = 0

            parser = StreamingCap3DParser(str(file_path))
            for element in parser.parse_blocks_streaming():
                if element.type == 'block':
                    block_count += 1
                elif element.type == 'conductor':
                    conductor_count += 1

            return WindowStats(
                file_path=str(file_path),
                dataset_name=dataset_name,
                block_count=block_count,
                conductor_count=conductor_count,
                has_error=False
            )

        except Exception as e:
            return WindowStats(
                file_path=str(file_path),
                dataset_name=dataset_name,
                block_count=0,
                conductor_count=0,
                has_error=True,
                error_message=str(e)
            )

    def analyze_dataset(self, dataset_name: str, cap3d_dir: Path,
                       parallel: bool = True, show_progress: bool = True) -> List[WindowStats]:
        """Analyze all CAP3D files in a dataset"""
        print(f"\nAnalyzing dataset: {dataset_name}")
        print(f"Directory: {cap3d_dir}")

        # Find all .cap3d files
        cap3d_files = list(cap3d_dir.glob("*.cap3d"))
        cap3d_files.extend(cap3d_dir.glob("*.cap3d.gz"))  # Handle compressed files

        if not cap3d_files:
            print(f"  No CAP3D files found in {cap3d_dir}")
            return []

        print(f"  Found {len(cap3d_files)} CAP3D files")

        # Analyze files
        results = []

        if parallel and len(cap3d_files) > 1:
            # Parallel processing for large datasets
            max_workers = min(cpu_count(), 8)  # Limit to 8 workers

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.analyze_single_file, file_path, dataset_name): file_path
                    for file_path in cap3d_files
                }

                # Collect results with progress bar
                if show_progress:
                    pbar = tqdm(total=len(cap3d_files), desc=f"  Processing {dataset_name}")

                for future in as_completed(future_to_file):
                    result = future.result()
                    results.append(result)

                    if show_progress:
                        pbar.update(1)

                if show_progress:
                    pbar.close()
        else:
            # Sequential processing
            if show_progress:
                for file_path in tqdm(cap3d_files, desc=f"  Processing {dataset_name}"):
                    result = self.analyze_single_file(file_path, dataset_name)
                    results.append(result)
            else:
                for file_path in cap3d_files:
                    result = self.analyze_single_file(file_path, dataset_name)
                    results.append(result)

        # Report results
        successful = [r for r in results if not r.has_error]
        failed = [r for r in results if r.has_error]

        print(f"  Successfully processed: {len(successful)}/{len(results)} files")
        if failed:
            print(f"  Failed files: {len(failed)}")
            for result in failed[:5]:  # Show first 5 errors
                print(f"    ERROR: {Path(result.file_path).name} - {result.error_message}")
            if len(failed) > 5:
                print(f"    ... and {len(failed) - 5} more errors")

        self.results[dataset_name] = results
        return results

    def calculate_statistics(self, values: List[int]) -> Dict[str, float]:
        """Calculate basic statistics for a list of values"""
        if not values:
            return {'mean': 0, 'min': 0, 'max': 0, 'median': 0, 'std': 0, 'count': 0}

        values_sorted = sorted(values)
        n = len(values)

        mean = sum(values) / n
        median = values_sorted[n // 2] if n % 2 == 1 else (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2

        # Calculate standard deviation
        variance = sum((x - mean) ** 2 for x in values) / n
        std = variance ** 0.5

        return {
            'mean': mean,
            'min': min(values),
            'max': max(values),
            'median': median,
            'std': std,
            'count': n
        }

    def generate_dataset_summary(self, dataset_name: str) -> DatasetStats:
        """Generate summary statistics for a dataset"""
        results = self.results.get(dataset_name, [])
        if not results:
            return DatasetStats(
                name=dataset_name,
                total_files=0,
                successful_files=0,
                failed_files=0,
                block_stats=self.calculate_statistics([]),
                conductor_stats=self.calculate_statistics([]),
                total_blocks=0,
                total_conductors=0
            )

        successful = [r for r in results if not r.has_error]
        failed = [r for r in results if r.has_error]

        block_values = [r.block_count for r in successful]
        conductor_values = [r.conductor_count for r in successful]

        return DatasetStats(
            name=dataset_name,
            total_files=len(results),
            successful_files=len(successful),
            failed_files=len(failed),
            block_stats=self.calculate_statistics(block_values),
            conductor_stats=self.calculate_statistics(conductor_values),
            total_blocks=sum(block_values),
            total_conductors=sum(conductor_values)
        )

    def print_summary_table(self, dataset_summaries: List[DatasetStats]):
        """Print a formatted summary table"""
        print("\n" + "="*120)
        print("WINDOW STATISTICS SUMMARY TABLE")
        print("="*120)

        # Table header
        header = f"{'Dataset':<25} {'Files':<8} {'Success':<8} {'Blocks':<45} {'Conductors':<45}"
        print(header)
        print("-" * 120)

        subheader = f"{'':<25} {'Total':<8} {'Rate':<8} {'Mean±Std (Min-Max)':<45} {'Mean±Std (Min-Max)':<45}"
        print(subheader)
        print("-" * 120)

        # Table rows
        for summary in dataset_summaries:
            success_rate = (summary.successful_files / summary.total_files * 100) if summary.total_files > 0 else 0

            blocks_info = f"{summary.block_stats['mean']:.1f}±{summary.block_stats['std']:.1f} ({summary.block_stats['min']}-{summary.block_stats['max']})"
            conductors_info = f"{summary.conductor_stats['mean']:.1f}±{summary.conductor_stats['std']:.1f} ({summary.conductor_stats['min']}-{summary.conductor_stats['max']})"

            row = f"{summary.name:<25} {summary.total_files:<8} {success_rate:<7.1f}% {blocks_info:<45} {conductors_info:<45}"
            print(row)

        print("-" * 120)

        # Overall totals
        total_files = sum(s.total_files for s in dataset_summaries)
        total_successful = sum(s.successful_files for s in dataset_summaries)
        total_blocks = sum(s.total_blocks for s in dataset_summaries)
        total_conductors = sum(s.total_conductors for s in dataset_summaries)

        overall_success = (total_successful / total_files * 100) if total_files > 0 else 0

        print(f"{'OVERALL TOTAL':<25} {total_files:<8} {overall_success:<7.1f}% {total_blocks:<45} {total_conductors:<45}")
        print("="*120)

    def export_to_csv(self, dataset_summaries: List[DatasetStats], output_path: str):
        """Export summary statistics to CSV"""
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = [
                'dataset', 'total_files', 'successful_files', 'failed_files', 'success_rate',
                'blocks_mean', 'blocks_std', 'blocks_min', 'blocks_max', 'blocks_median', 'total_blocks',
                'conductors_mean', 'conductors_std', 'conductors_min', 'conductors_max', 'conductors_median', 'total_conductors'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for summary in dataset_summaries:
                success_rate = (summary.successful_files / summary.total_files * 100) if summary.total_files > 0 else 0

                writer.writerow({
                    'dataset': summary.name,
                    'total_files': summary.total_files,
                    'successful_files': summary.successful_files,
                    'failed_files': summary.failed_files,
                    'success_rate': success_rate,
                    'blocks_mean': summary.block_stats['mean'],
                    'blocks_std': summary.block_stats['std'],
                    'blocks_min': summary.block_stats['min'],
                    'blocks_max': summary.block_stats['max'],
                    'blocks_median': summary.block_stats['median'],
                    'total_blocks': summary.total_blocks,
                    'conductors_mean': summary.conductor_stats['mean'],
                    'conductors_std': summary.conductor_stats['std'],
                    'conductors_min': summary.conductor_stats['min'],
                    'conductors_max': summary.conductor_stats['max'],
                    'conductors_median': summary.conductor_stats['median'],
                    'total_conductors': summary.total_conductors
                })

        print(f"\nSummary statistics exported to: {output_path}")

    def export_detailed_json(self, output_path: str):
        """Export detailed results to JSON"""
        detailed_results = {}

        for dataset_name, window_results in self.results.items():
            detailed_results[dataset_name] = [
                {
                    'file_path': result.file_path,
                    'block_count': result.block_count,
                    'conductor_count': result.conductor_count,
                    'has_error': result.has_error,
                    'error_message': result.error_message
                }
                for result in window_results
            ]

        with open(output_path, 'w') as jsonfile:
            json.dump(detailed_results, jsonfile, indent=2)

        print(f"Detailed results exported to: {output_path}")

    def run_analysis(self, output_dir: str = None, csv_export: bool = False,
                    json_export: bool = False, parallel: bool = True) -> List[DatasetStats]:
        """Run complete analysis across all datasets"""
        print("Starting Window Statistics Analysis")
        print("="*50)

        start_time = time.time()

        # Discover datasets
        datasets = self.discover_datasets()

        if not datasets:
            print("ERROR: No datasets found!")
            return []

        print(f"Found {len(datasets)} datasets to analyze")

        # Analyze each dataset
        for dataset_name, cap3d_dir in datasets.items():
            self.analyze_dataset(dataset_name, cap3d_dir, parallel=parallel)

        # Generate summaries
        dataset_summaries = []
        for dataset_name in datasets.keys():
            summary = self.generate_dataset_summary(dataset_name)
            dataset_summaries.append(summary)

        # Sort by total blocks (descending)
        dataset_summaries.sort(key=lambda x: x.total_blocks, reverse=True)

        # Print summary table
        self.print_summary_table(dataset_summaries)

        # Export results if requested
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            if csv_export:
                csv_path = output_path / "window_statistics_summary.csv"
                self.export_to_csv(dataset_summaries, str(csv_path))

            if json_export:
                json_path = output_path / "window_statistics_detailed.json"
                self.export_detailed_json(str(json_path))

        # Report timing
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\nAnalysis completed in {elapsed:.1f} seconds")

        return dataset_summaries


def main():
    parser = argparse.ArgumentParser(
        description='Analyze window statistics across CAP3D datasets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all datasets with default settings
  python scripts/analyze_window_statistics.py

  # Export results to CSV and JSON
  python scripts/analyze_window_statistics.py --csv-export --json-export --output-dir results/

  # Use sequential processing (disable parallel)
  python scripts/analyze_window_statistics.py --no-parallel
        """
    )

    parser.add_argument('--datasets-dir',
                       help='Path to datasets directory (default: datasets/ in repo root)')
    parser.add_argument('--output-dir',
                       help='Output directory for exported results')
    parser.add_argument('--csv-export', action='store_true',
                       help='Export summary statistics to CSV')
    parser.add_argument('--json-export', action='store_true',
                       help='Export detailed results to JSON')
    parser.add_argument('--no-parallel', action='store_true',
                       help='Disable parallel processing (use sequential)')

    args = parser.parse_args()

    # Create analyzer and run analysis
    analyzer = WindowStatisticsAnalyzer(datasets_dir=args.datasets_dir)

    dataset_summaries = analyzer.run_analysis(
        output_dir=args.output_dir,
        csv_export=args.csv_export,
        json_export=args.json_export,
        parallel=not args.no_parallel
    )

    if not dataset_summaries:
        print("No datasets were successfully analyzed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
