"""
Comprehensive model profiler for analysis and benchmarking of GNN-Cap models.

This module provides tools for:
- Comparing different model architectures
- Analyzing training dynamics
- Benchmarking performance metrics
- Generating detailed reports and visualizations
"""

import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
from collections import defaultdict

# Import our modules
from models.enhanced_gnncap_model import EnhancedGNNCapModel, create_enhanced_model
from models.gnncap_model import GNNCapModel
from utils.parameter_utils import ParameterProfiler, compare_models, print_model_comparison


class ModelBenchmark:
    """
    Comprehensive benchmarking suite for GNN-Cap models.
    """

    def __init__(self,
                 save_dir: str = "./benchmark_results",
                 device: str = "auto"):
        """
        Initialize model benchmark.

        Args:
            save_dir: Directory to save benchmark results
            device: Device for computations ('auto', 'cpu', 'cuda')
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Setup device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Setup logging
        self.logger = self._setup_logger()

        # Results storage
        self.results = {}
        self.model_registry = {}

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the benchmark."""
        logger = logging.getLogger("ModelBenchmark")
        logger.setLevel(logging.INFO)

        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Create file handler
        fh = logging.FileHandler(self.save_dir / "benchmark.log")
        fh.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # Add handlers to logger
        if not logger.handlers:
            logger.addHandler(ch)
            logger.addHandler(fh)

        return logger

    def register_model(self,
                      name: str,
                      model: nn.Module,
                      description: str = ""):
        """
        Register a model for benchmarking.

        Args:
            name: Model identifier
            model: PyTorch model
            description: Optional description
        """
        self.model_registry[name] = {
            'model': model,
            'description': description,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.logger.info(f"Registered model: {name}")

    def benchmark_architectures(self,
                               model_configs: List[Dict[str, Any]],
                               input_shapes: List[Tuple[int, ...]] = None) -> Dict[str, Any]:
        """
        Benchmark multiple model architectures.

        Args:
            model_configs: List of model configurations
            input_shapes: List of input shapes to test

        Returns:
            Benchmark results
        """
        if input_shapes is None:
            input_shapes = [(1000, 3, 7)]  # (num_nodes, node_features, edge_features)

        results = {
            'architectures': {},
            'comparison': {},
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'device': str(self.device)
        }

        models_to_compare = {}

        for config in model_configs:
            arch_name = config.get('name', f"arch_{len(results['architectures'])}")
            self.logger.info(f"Benchmarking architecture: {arch_name}")

            try:
                # Create model
                if config.get('enhanced', False):
                    model = create_enhanced_model(
                        architecture_type=config.get('architecture_type', 'deep_3layer'),
                        **config.get('model_kwargs', {})
                    )
                else:
                    model = GNNCapModel(
                        prediction_type=config.get('prediction_type', 'total'),
                        num_layers=config.get('num_layers', 2),
                        **config.get('model_kwargs', {})
                    )

                model.to(self.device)
                model.eval()

                # Register model
                self.register_model(arch_name, model, config.get('description', ''))
                models_to_compare[arch_name] = model

                # Analyze model
                profiler = ParameterProfiler(model)
                param_stats = profiler.count_parameters(detailed=True)
                flop_stats = profiler.estimate_flops()
                memory_stats = profiler.profile_memory_usage()

                # Store results
                results['architectures'][arch_name] = {
                    'config': config,
                    'parameter_analysis': param_stats,
                    'flop_analysis': flop_stats,
                    'memory_analysis': memory_stats,
                    'model_info': self._get_model_info(model, config)
                }

                # Benchmark inference time
                inference_results = self._benchmark_inference_time(model, input_shapes)
                results['architectures'][arch_name]['inference'] = inference_results

                self.logger.info(f"Completed benchmark for {arch_name}")

            except Exception as e:
                self.logger.error(f"Failed to benchmark {arch_name}: {str(e)}")
                results['architectures'][arch_name] = {'error': str(e)}

        # Generate comparison
        if len(models_to_compare) > 1:
            comparison = compare_models(models_to_compare, save_dir=str(self.save_dir))
            results['comparison'] = comparison

        # Save results
        self._save_benchmark_results(results, "architecture_benchmark.json")

        return results

    def benchmark_training_dynamics(self,
                                   model: nn.Module,
                                   train_loader: torch.utils.data.DataLoader,
                                   val_loader: torch.utils.data.DataLoader,
                                   num_epochs: int = 10,
                                   optimizer_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Benchmark training dynamics of a model.

        Args:
            model: Model to benchmark
            train_loader: Training data loader
            val_loader: Validation data loader
            num_epochs: Number of epochs to run
            optimizer_config: Optimizer configuration

        Returns:
            Training dynamics results
        """
        self.logger.info(f"Benchmarking training dynamics for {num_epochs} epochs")

        model.to(self.device)

        # Setup optimizer
        if optimizer_config is None:
            optimizer_config = {'type': 'Adam', 'lr': 1e-4}

        if optimizer_config['type'] == 'Adam':
            optimizer = torch.optim.Adam(
                model.parameters(),
                lr=optimizer_config.get('lr', 0.005),
                weight_decay=optimizer_config.get('weight_decay', 0)
            )
        elif optimizer_config['type'] == 'AdamW':
            optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=optimizer_config.get('lr', 0.005),
                weight_decay=optimizer_config.get('weight_decay', 1e-4)
            )
        else:
            raise ValueError(f"Unknown optimizer type: {optimizer_config['type']}")

        # Setup loss function
        criterion = nn.MSELoss()

        # Training tracking
        results = {
            'epochs': [],
            'train_losses': [],
            'val_losses': [],
            'learning_rates': [],
            'gradient_norms': [],
            'parameter_evolution': [],
            'training_time': [],
            'memory_usage': []
        }

        model.train()

        for epoch in range(num_epochs):
            epoch_start_time = time.time()
            epoch_train_loss = 0.0
            epoch_grad_norm = 0.0
            num_batches = 0

            # Training phase
            for batch_idx, batch in enumerate(train_loader):
                if batch_idx >= 50:  # Limit batches for faster benchmarking
                    break

                optimizer.zero_grad()

                # Prepare batch
                if isinstance(batch, (tuple, list)):
                    data, labels = batch
                else:
                    data = batch
                    labels = getattr(data, 'y', None)

                if hasattr(data, 'to'):
                    data = data.to(self.device)
                if labels is not None:
                    labels = labels.to(self.device)

                # Forward pass
                try:
                    outputs = model(data)
                    if labels is not None:
                        loss = criterion(outputs.view(-1), labels.view(-1))
                    else:
                        # Dummy loss for benchmarking
                        loss = torch.tensor(0.0, device=self.device, requires_grad=True)

                    # Backward pass
                    loss.backward()

                    # Track gradient norms
                    total_norm = 0
                    for p in model.parameters():
                        if p.grad is not None:
                            param_norm = p.grad.data.norm(2)
                            total_norm += param_norm.item() ** 2
                    epoch_grad_norm += total_norm ** (1. / 2)

                    optimizer.step()

                    epoch_train_loss += loss.item()
                    num_batches += 1

                except Exception as e:
                    self.logger.warning(f"Error in batch {batch_idx}: {str(e)}")
                    continue

            # Calculate epoch metrics
            if num_batches > 0:
                avg_train_loss = epoch_train_loss / num_batches
                avg_grad_norm = epoch_grad_norm / num_batches
            else:
                avg_train_loss = 0.0
                avg_grad_norm = 0.0

            # Validation phase
            model.eval()
            epoch_val_loss = 0.0
            val_batches = 0

            with torch.no_grad():
                for batch_idx, batch in enumerate(val_loader):
                    if batch_idx >= 20:  # Limit validation batches
                        break

                    if isinstance(batch, (tuple, list)):
                        data, labels = batch
                    else:
                        data = batch
                        labels = getattr(data, 'y', None)

                    if hasattr(data, 'to'):
                        data = data.to(self.device)
                    if labels is not None:
                        labels = labels.to(self.device)

                    try:
                        outputs = model(data)
                        if labels is not None:
                            loss = criterion(outputs.view(-1), labels.view(-1))
                            epoch_val_loss += loss.item()
                            val_batches += 1
                    except Exception as e:
                        self.logger.warning(f"Error in validation batch {batch_idx}: {str(e)}")
                        continue

            if val_batches > 0:
                avg_val_loss = epoch_val_loss / val_batches
            else:
                avg_val_loss = 0.0

            # Track epoch results
            epoch_time = time.time() - epoch_start_time
            current_lr = optimizer.param_groups[0]['lr']

            results['epochs'].append(epoch)
            results['train_losses'].append(avg_train_loss)
            results['val_losses'].append(avg_val_loss)
            results['learning_rates'].append(current_lr)
            results['gradient_norms'].append(avg_grad_norm)
            results['training_time'].append(epoch_time)

            # Track memory usage
            if torch.cuda.is_available():
                memory_used = torch.cuda.memory_allocated() / 1024**3  # GB
                results['memory_usage'].append(memory_used)

            # Track parameter evolution (sum of parameters)
            param_sum = sum(p.data.abs().sum().item() for p in model.parameters())
            results['parameter_evolution'].append(param_sum)

            # Log progress
            self.logger.info(
                f"Epoch {epoch+1}/{num_epochs} - "
                f"Train Loss: {avg_train_loss:.6f}, "
                f"Val Loss: {avg_val_loss:.6f}, "
                f"Grad Norm: {avg_grad_norm:.6f}, "
                f"Time: {epoch_time:.2f}s"
            )

            model.train()

        # Save training dynamics results
        self._save_benchmark_results(results, "training_dynamics.json")

        return results

    def _benchmark_inference_time(self,
                                 model: nn.Module,
                                 input_shapes: List[Tuple[int, ...]],
                                 num_runs: int = 100) -> Dict[str, float]:
        """
        Benchmark inference time for different input sizes.

        Args:
            model: Model to benchmark
            input_shapes: List of input shapes
            num_runs: Number of runs for averaging

        Returns:
            Inference time results
        """
        results = {}

        model.eval()

        for i, shape in enumerate(input_shapes):
            num_nodes, node_features, edge_features = shape

            # Create dummy input
            x = torch.randn(num_nodes, node_features, device=self.device)
            edge_index = torch.randint(0, num_nodes, (2, num_nodes * 4), device=self.device)
            edge_attr = torch.randn(edge_index.size(1), edge_features, device=self.device)

            # Create dummy data object
            from torch_geometric.data import Data
            dummy_data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)

            # Warmup
            with torch.no_grad():
                for _ in range(10):
                    _ = model(dummy_data)

            # Benchmark
            torch.cuda.synchronize() if torch.cuda.is_available() else None
            start_time = time.time()

            with torch.no_grad():
                for _ in range(num_runs):
                    _ = model(dummy_data)

            torch.cuda.synchronize() if torch.cuda.is_available() else None
            end_time = time.time()

            avg_time = (end_time - start_time) / num_runs * 1000  # Convert to ms
            throughput = num_nodes / avg_time * 1000  # nodes per second

            shape_key = f"shape_{i}_{num_nodes}nodes"
            results[shape_key] = {
                'avg_time_ms': avg_time,
                'throughput_nodes_per_sec': throughput,
                'num_nodes': num_nodes
            }

        return results

    def _get_model_info(self, model: nn.Module, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract model information."""
        info = {
            'model_type': config.get('model_type', 'unknown'),
            'num_parameters': sum(p.numel() for p in model.parameters()),
            'num_trainable': sum(p.numel() for p in model.parameters() if p.requires_grad),
            'model_class': model.__class__.__name__
        }

        # Add enhanced model info if available
        if hasattr(model, 'get_model_info'):
            enhanced_info = model.get_model_info()
            info.update(enhanced_info)

        return info

    def _save_benchmark_results(self, results: Dict[str, Any], filename: str):
        """Save benchmark results to file."""
        save_path = self.save_dir / filename

        # Convert numpy arrays and tensors for JSON serialization
        def convert_for_json(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, torch.Tensor):
                return obj.cpu().numpy().tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            else:
                return obj

        json_results = convert_for_json(results)

        with open(save_path, 'w') as f:
            json.dump(json_results, f, indent=2)

        self.logger.info(f"Saved benchmark results to {save_path}")

    def generate_report(self, benchmark_results: Dict[str, Any] = None) -> str:
        """
        Generate a comprehensive benchmark report.

        Args:
            benchmark_results: Results to report (uses latest if None)

        Returns:
            Path to generated report
        """
        if benchmark_results is None:
            # Load latest benchmark results
            result_files = list(self.save_dir.glob("*benchmark.json"))
            if not result_files:
                raise ValueError("No benchmark results found")

            latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
            with open(latest_file, 'r') as f:
                benchmark_results = json.load(f)

        # Generate report
        report_path = self.save_dir / "benchmark_report.md"

        with open(report_path, 'w') as f:
            self._write_markdown_report(f, benchmark_results)

        self.logger.info(f"Generated benchmark report: {report_path}")
        return str(report_path)

    def _write_markdown_report(self, f, results: Dict[str, Any]):
        """Write markdown report."""
        f.write("# GNN-Cap Model Benchmark Report\n\n")
        f.write(f"Generated on: {results.get('timestamp', 'Unknown')}\n")
        f.write(f"Device: {results.get('device', 'Unknown')}\n\n")

        # Architecture comparison
        if 'architectures' in results:
            f.write("## Architecture Comparison\n\n")

            # Create comparison table
            if len(results['architectures']) > 1:
                f.write("| Architecture | Parameters | Memory (MB) | GFLOPs | Inference Time (ms) |\n")
                f.write("|---------------|------------|-------------|--------|---------------------|\n")

                for name, arch_results in results['architectures'].items():
                    if 'error' in arch_results:
                        f.write(f"| {name} | ERROR | - | - | - |\n")
                    else:
                        params = arch_results.get('parameter_analysis', {}).get('total_parameters', 0)
                        memory = arch_results.get('memory_analysis', {}).get('total_memory_mb', 0)
                        gflops = arch_results.get('flop_analysis', {}).get('total_gflops', 0)

                        # Get average inference time
                        inference_times = []
                        for inf_key, inf_val in arch_results.get('inference', {}).items():
                            if isinstance(inf_val, dict) and 'avg_time_ms' in inf_val:
                                inference_times.append(inf_val['avg_time_ms'])

                        avg_time = np.mean(inference_times) if inference_times else 0

                        f.write(f"| {name} | {params:,} | {memory:.1f} | {gflops:.2f} | {avg_time:.2f} |\n")

                f.write("\n")

            # Detailed architecture breakdowns
            for name, arch_results in results['architectures'].items():
                f.write(f"### {name}\n\n")

                if 'error' in arch_results:
                    f.write(f"**Error:** {arch_results['error']}\n\n")
                else:
                    # Parameter breakdown
                    param_stats = arch_results.get('parameter_analysis', {})
                    f.write(f"**Parameters:**\n")
                    f.write(f"- Total: {param_stats.get('total_parameters', 0):,}\n")
                    f.write(f"- Trainable: {param_stats.get('trainable_parameters', 0):,}\n")
                    f.write(f"- Memory: {param_stats.get('parameter_memory_mb', 0):.2f} MB\n\n")

                    # Performance metrics
                    flop_stats = arch_results.get('flop_analysis', {})
                    f.write(f"**Performance:**\n")
                    f.write(f"- GFLOPs: {flop_stats.get('total_gflops', 0):.4f}\n")
                    f.write(f"- FLOPs per Parameter: {flop_stats.get('flops_per_parameter', 0):.2f}\n\n")

                    # Layer breakdown
                    if 'layer_breakdown' in param_stats:
                        f.write("**Layer Breakdown:**\n")
                        for layer_type, data in param_stats['layer_breakdown'].items():
                            f.write(f"- {layer_type}: {data['parameter_count']:,} params "
                                   f"({data['percentage_of_total']:.1f}%)\n")
                        f.write("\n")

                    # Inference results
                    if 'inference' in arch_results:
                        f.write("**Inference Performance:**\n")
                        for shape_key, inf_data in arch_results['inference'].items():
                            if isinstance(inf_data, dict):
                                f.write(f"- {shape_key}: {inf_data.get('avg_time_ms', 0):.2f} ms "
                                       f"({inf_data.get('throughput_nodes_per_sec', 0):.0f} nodes/s)\n")
                        f.write("\n")

        # Training dynamics
        if 'epochs' in results:
            f.write("## Training Dynamics\n\n")
            f.write(f"- Epochs benchmarked: {len(results['epochs'])}\n")
            f.write(f"- Final train loss: {results['train_losses'][-1]:.6f}\n")
            f.write(f"- Final validation loss: {results['val_losses'][-1]:.6f}\n")
            f.write(f"- Average gradient norm: {np.mean(results['gradient_norms']):.6f}\n")

            if 'memory_usage' in results and results['memory_usage']:
                f.write(f"- Peak GPU memory: {max(results['memory_usage']):.2f} GB\n")

            f.write("\n")

    def create_visualizations(self, benchmark_results: Dict[str, Any] = None):
        """
        Create visualization plots for benchmark results.

        Args:
            benchmark_results: Results to visualize (uses latest if None)
        """
        if benchmark_results is None:
            # Load latest benchmark results
            result_files = list(self.save_dir.glob("*benchmark.json"))
            if not result_files:
                raise ValueError("No benchmark results found")

            latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
            with open(latest_file, 'r') as f:
                benchmark_results = json.load(f)

        # Set plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

        # Create architecture comparison plots
        if 'architectures' in benchmark_results:
            self._plot_architecture_comparison(benchmark_results['architectures'])

        # Create training dynamics plots
        if 'epochs' in benchmark_results:
            self._plot_training_dynamics(benchmark_results)

        self.logger.info(f"Created visualizations in {self.save_dir}")

    def _plot_architecture_comparison(self, architectures: Dict[str, Any]):
        """Create architecture comparison plots."""
        valid_archs = {k: v for k, v in architectures.items() if 'error' not in v}

        if len(valid_archs) < 2:
            return

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Model Architecture Comparison', fontsize=16)

        names = list(valid_archs.keys())

        # Parameters comparison
        params = [arch['parameter_analysis']['total_parameters'] for arch in valid_archs.values()]
        axes[0, 0].bar(names, params)
        axes[0, 0].set_title('Total Parameters')
        axes[0, 0].set_ylabel('Number of Parameters')
        axes[0, 0].tick_params(axis='x', rotation=45)

        # Memory usage comparison
        memory = [arch['memory_analysis']['total_memory_mb'] for arch in valid_archs.values()]
        axes[0, 1].bar(names, memory)
        axes[0, 1].set_title('Memory Usage')
        axes[0, 1].set_ylabel('Memory (MB)')
        axes[0, 1].tick_params(axis='x', rotation=45)

        # FLOPs comparison
        gflops = [arch['flop_analysis']['total_gflops'] for arch in valid_archs.values()]
        axes[1, 0].bar(names, gflops)
        axes[1, 0].set_title('Computational Complexity')
        axes[1, 0].set_ylabel('GFLOPs')
        axes[1, 0].tick_params(axis='x', rotation=45)

        # Inference time comparison
        inference_times = []
        for arch in valid_archs.values():
            times = []
            for inf_data in arch.get('inference', {}).values():
                if isinstance(inf_data, dict) and 'avg_time_ms' in inf_data:
                    times.append(inf_data['avg_time_ms'])
            inference_times.append(np.mean(times) if times else 0)

        axes[1, 1].bar(names, inference_times)
        axes[1, 1].set_title('Inference Time (average)')
        axes[1, 1].set_ylabel('Time (ms)')
        axes[1, 1].tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(self.save_dir / 'architecture_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_training_dynamics(self, results: Dict[str, Any]):
        """Create training dynamics plots."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Training Dynamics', fontsize=16)

        epochs = results['epochs']

        # Loss curves
        axes[0, 0].plot(epochs, results['train_losses'], label='Training Loss', marker='o')
        axes[0, 0].plot(epochs, results['val_losses'], label='Validation Loss', marker='s')
        axes[0, 0].set_title('Loss Curves')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True)

        # Learning rate
        axes[0, 1].plot(epochs, results['learning_rates'], marker='o', color='orange')
        axes[0, 1].set_title('Learning Rate Schedule')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Learning Rate')
        axes[0, 1].set_yscale('log')
        axes[0, 1].grid(True)

        # Gradient norms
        axes[1, 0].plot(epochs, results['gradient_norms'], marker='o', color='green')
        axes[1, 0].set_title('Gradient Norms')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Gradient Norm')
        axes[1, 0].grid(True)

        # Memory usage (if available)
        if 'memory_usage' in results and results['memory_usage']:
            axes[1, 1].plot(epochs, results['memory_usage'], marker='o', color='red')
            axes[1, 1].set_title('GPU Memory Usage')
            axes[1, 1].set_xlabel('Epoch')
            axes[1, 1].set_ylabel('Memory (GB)')
            axes[1, 1].grid(True)
        else:
            # Training time instead
            axes[1, 1].plot(epochs, results['training_time'], marker='o', color='red')
            axes[1, 1].set_title('Training Time per Epoch')
            axes[1, 1].set_xlabel('Epoch')
            axes[1, 1].set_ylabel('Time (seconds)')
            axes[1, 1].grid(True)

        plt.tight_layout()
        plt.savefig(self.save_dir / 'training_dynamics.png', dpi=300, bbox_inches='tight')
        plt.close()


# Utility function for quick benchmarking
def quick_benchmark(save_dir: str = "./benchmark_results") -> ModelBenchmark:
    """
    Create a quick benchmark with standard model configurations.

    Args:
        save_dir: Directory to save results

    Returns:
        Configured benchmark instance
    """
    benchmark = ModelBenchmark(save_dir=save_dir)

    # Standard model configurations to test
    model_configs = [
        {
            'name': 'standard_2layer',
            'enhanced': False,
            'prediction_type': 'total',
            'num_layers': 2,
            'description': 'Standard 2-layer GNN-Cap'
        },
        {
            'name': 'enhanced_2layer',
            'enhanced': True,
            'num_layers': 2,
            'description': 'Enhanced 2-layer with residual connections and advanced attention'
        },
        {
            'name': 'enhanced_3layer',
            'enhanced': True,
            'num_layers': 3,
            'description': 'Enhanced 3-layer with progressive dimensions and advanced attention'
        }
    ]

    # Run benchmark
    results = benchmark.benchmark_architectures(model_configs)

    # Generate report and visualizations
    benchmark.generate_report(results)
    benchmark.create_visualizations(results)

    return benchmark


if __name__ == "__main__":
    # Example usage
    benchmark = quick_benchmark("./example_benchmark")
    print(f"Benchmark completed. Results saved to: {benchmark.save_dir}")
    print(f"Report: {benchmark.save_dir / 'benchmark_report.md'}")