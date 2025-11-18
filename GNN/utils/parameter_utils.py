"""
Enhanced parameter counting and profiling utilities for GNN-Cap models.
Provides comprehensive analysis of model complexity, FLOPs, and memory usage.
"""

import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import json
from collections import defaultdict
import time
from pathlib import Path


class ParameterProfiler:
    """Comprehensive parameter analysis and profiling for neural networks."""

    def __init__(self, model: nn.Module):
        self.model = model
        self.parameter_stats = {}
        self.flop_stats = {}
        self.memory_stats = {}

    def count_parameters(self, detailed: bool = True) -> Dict[str, Any]:
        """
        Count parameters in the model with optional detailed breakdown.

        Args:
            detailed: If True, provide detailed breakdown by layer type

        Returns:
            Dictionary containing parameter statistics
        """
        total_params = 0
        trainable_params = 0
        layer_stats = defaultdict(lambda: {'count': 0, 'params': 0, 'trainable': 0})

        for name, param in self.model.named_parameters():
            param_count = param.numel()
            total_params += param_count
            if param.requires_grad:
                trainable_params += param_count

            if detailed:
                # Extract layer type from parameter name
                layer_type = name.split('.')[0]
                if any(x in name for x in ['attention', 'attn', 'gat']):
                    layer_type = 'attention'
                elif any(x in name for x in ['mlp', 'linear', 'fc']):
                    layer_type = 'linear'
                elif any(x in name for x in ['norm', 'batch', 'layer']):
                    layer_type = 'normalization'
                elif any(x in name for x in ['pool', 'aggregate']):
                    layer_type = 'pooling'
                elif any(x in name for x in ['embed', 'pos']):
                    layer_type = 'embedding'

                layer_stats[layer_type]['count'] += 1
                layer_stats[layer_type]['params'] += param_count
                if param.requires_grad:
                    layer_stats[layer_type]['trainable'] += param_count

        # Convert defaultdict to regular dict for JSON serialization
        layer_stats = dict(layer_stats)

        # Calculate parameter memory usage (assuming float32 = 4 bytes)
        param_memory_mb = (total_params * 4) / (1024 * 1024)
        trainable_memory_mb = (trainable_params * 4) / (1024 * 1024)

        stats = {
            'total_parameters': total_params,
            'trainable_parameters': trainable_params,
            'non_trainable_parameters': total_params - trainable_params,
            'parameter_memory_mb': param_memory_mb,
            'trainable_memory_mb': trainable_memory_mb,
            'trainable_ratio': trainable_params / total_params if total_params > 0 else 0,
        }

        if detailed:
            stats['layer_breakdown'] = {}
            for layer_type, data in layer_stats.items():
                stats['layer_breakdown'][layer_type] = {
                    'parameter_count': data['params'],
                    'trainable_parameters': data['trainable'],
                    'num_layers': data['count'],
                    'percentage_of_total': (data['params'] / total_params * 100) if total_params > 0 else 0,
                    'memory_mb': (data['params'] * 4) / (1024 * 1024)
                }

        self.parameter_stats = stats
        return stats

    def estimate_flops(self, input_shape: Tuple[int, ...] = None) -> Dict[str, Any]:
        """
        Estimate FLOPs for the model.

        Args:
            input_shape: Shape of input tensor (num_nodes, num_node_features)

        Returns:
            Dictionary containing FLOP estimates
        """
        if input_shape is None:
            # Default assumptions for GNN
            input_shape = (1000, 10)  # 1000 nodes, 10 features

        total_flops = 0
        layer_flops = defaultdict(int)

        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                # FLOPs for linear layer: 2 * input_features * output_features (multiply + add)
                in_features = module.in_features
                out_features = module.out_features
                flops = 2 * in_features * out_features
                total_flops += flops
                layer_flops['linear'] += flops

            elif isinstance(module, nn.MultiheadAttention):
                # FLOPs for multi-head attention
                embed_dim = module.embed_dim
                num_heads = module.num_heads
                head_dim = embed_dim // num_heads

                # Scaled dot-product attention FLOPs
                # Q, K, V projections: 3 * 2 * embed_dim * embed_dim
                # Attention scores: seq_len^2 * embed_dim
                # Output projection: 2 * embed_dim * embed_dim
                seq_len = input_shape[0]  # number of nodes
                attention_flops = (
                    6 * embed_dim * embed_dim +  # Q, K, V projections
                    seq_len * seq_len * embed_dim +  # attention scores
                    2 * embed_dim * embed_dim  # output projection
                )
                total_flops += attention_flops
                layer_flops['attention'] += attention_flops

            elif isinstance(module, nn.LayerNorm):
                # FLOPs for layer normalization: 2 * num_features (mean + std + normalization)
                total_flops += 2 * module.normalized_shape[0] * input_shape[0]
                layer_flops['normalization'] += 2 * module.normalized_shape[0] * input_shape[0]

            elif isinstance(module, nn.Dropout):
                # Minimal FLOPs for dropout
                total_flops += input_shape[0] * input_shape[1]
                layer_flops['dropout'] += input_shape[0] * input_shape[1]

        # Convert to GFLOPs
        gflops = total_flops / 1e9

        flop_stats = {
            'total_flops': total_flops,
            'total_gflops': gflops,
            'layer_breakdown': dict(layer_flops),
            'flops_per_parameter': total_flops / self.parameter_stats.get('total_parameters', 1)
        }

        self.flop_stats = flop_stats
        return flop_stats

    def profile_memory_usage(self, batch_size: int = 1, seq_len: int = 1000) -> Dict[str, Any]:
        """
        Profile memory usage during training/inference.

        Args:
            batch_size: Batch size for memory estimation
            seq_len: Sequence length (number of nodes)

        Returns:
            Dictionary containing memory usage estimates
        """
        # Parameter memory
        param_memory = self.parameter_stats.get('parameter_memory_mb', 0)

        # Gradient memory (same as parameter memory during training)
        gradient_memory = param_memory if self.model.training else 0

        # Activation memory estimation (rough heuristic)
        # For GNNs: activations ~ 2x parameter memory for moderate sizes
        activation_memory = param_memory * 2 * batch_size

        # Input/output memory
        input_features = 10  # Estimated based on current implementation
        input_memory = (batch_size * seq_len * input_features * 4) / (1024 * 1024)
        output_memory = (batch_size * seq_len * 4) / (1024 * 1024)  # Assuming float32 output

        total_memory = param_memory + gradient_memory + activation_memory + input_memory + output_memory

        memory_stats = {
            'parameter_memory_mb': param_memory,
            'gradient_memory_mb': gradient_memory,
            'activation_memory_mb': activation_memory,
            'input_memory_mb': input_memory,
            'output_memory_mb': output_memory,
            'total_memory_mb': total_memory,
            'memory_per_sample_mb': total_memory / batch_size
        }

        self.memory_stats = memory_stats
        return memory_stats

    def generate_comprehensive_report(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive profiling report.

        Args:
            save_path: Path to save the report as JSON

        Returns:
            Comprehensive profiling report
        """
        # Run all analyses
        param_stats = self.count_parameters(detailed=True)
        flop_stats = self.estimate_flops()
        memory_stats = self.profile_memory_usage()

        # Create comprehensive report
        report = {
            'model_name': self.model.__class__.__name__,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'parameter_analysis': param_stats,
            'flop_analysis': flop_stats,
            'memory_analysis': memory_stats,
            'efficiency_metrics': {
                'params_per_gflop': param_stats['total_parameters'] / max(flop_stats['total_gflops'], 1e-9),
                'memory_per_parameter_mb': memory_stats['parameter_memory_mb'] / max(param_stats['total_parameters'], 1),
                'flops_per_mb_total': flop_stats['total_flops'] / max(memory_stats['total_memory_mb'], 1)
            }
        }

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump(report, f, indent=2)

        return report

    def print_summary(self, report: Dict[str, Any] = None):
        """Print a formatted summary of the profiling results."""
        if report is None:
            report = self.generate_comprehensive_report()

        print("=" * 80)
        print("GNN-Cap MODEL PROFILING REPORT")
        print("=" * 80)

        # Parameter summary
        param_stats = report['parameter_analysis']
        print(f"\nPARAMETER ANALYSIS:")
        print(f"  Total Parameters: {param_stats['total_parameters']:,}")
        print(f"  Trainable Parameters: {param_stats['trainable_parameters']:,}")
        print(f"  Parameter Memory: {param_stats['parameter_memory_mb']:.2f} MB")
        print(f"  Trainable Ratio: {param_stats['trainable_ratio']:.2%}")

        if 'layer_breakdown' in param_stats:
            print(f"\n  Layer Breakdown:")
            for layer_type, data in param_stats['layer_breakdown'].items():
                print(f"    {layer_type.capitalize():15s}: {data['parameter_count']:8,} params "
                      f"({data['percentage_of_total']:5.1f}%)")

        # FLOP summary
        flop_stats = report['flop_analysis']
        print(f"\nCOMPUTATIONAL ANALYSIS:")
        print(f"  Total FLOPs: {flop_stats['total_flops']:,}")
        print(f"  Total GFLOPs: {flop_stats['total_gflops']:.4f}")
        print(f"  FLOPs per Parameter: {flop_stats['flops_per_parameter']:.2f}")

        # Memory summary
        memory_stats = report['memory_analysis']
        print(f"\nMEMORY ANALYSIS:")
        print(f"  Total Memory: {memory_stats['total_memory_mb']:.2f} MB")
        print(f"    Parameters: {memory_stats['parameter_memory_mb']:.2f} MB")
        print(f"    Gradients: {memory_stats['gradient_memory_mb']:.2f} MB")
        print(f"    Activations: {memory_stats['activation_memory_mb']:.2f} MB")
        print(f"    Input/Output: {memory_stats['input_memory_mb'] + memory_stats['output_memory_mb']:.2f} MB")

        # Efficiency metrics
        efficiency = report['efficiency_metrics']
        print(f"\nEFFICIENCY METRICS:")
        print(f"  Params per GFLOP: {efficiency['params_per_gflop']:,.0f}")
        print(f"  Memory per Parameter: {efficiency['memory_per_parameter_mb']*1024:.2f} KB")
        print(f"  FLOPs per MB Total: {efficiency['flops_per_mb']:,.0f}")

        print("=" * 80)


def compare_models(models: Dict[str, nn.Module], save_dir: str = None) -> Dict[str, Any]:
    """
    Compare multiple models side-by-side.

    Args:
        models: Dictionary mapping model names to model instances
        save_dir: Directory to save comparison results

    Returns:
        Comparison report
    """
    comparison = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'models': {}
    }

    for model_name, model in models.items():
        profiler = ParameterProfiler(model)
        report = profiler.generate_comprehensive_report()
        comparison['models'][model_name] = report

    # Create summary comparison
    comparison['summary'] = {
        'parameter_comparison': {},
        'flop_comparison': {},
        'memory_comparison': {}
    }

    for model_name in models.keys():
        report = comparison['models'][model_name]
        comparison['summary']['parameter_comparison'][model_name] = report['parameter_analysis']['total_parameters']
        comparison['summary']['flop_comparison'][model_name] = report['flop_analysis']['total_flops']
        comparison['summary']['memory_comparison'][model_name] = report['memory_analysis']['total_memory_mb']

    if save_dir:
        save_path = Path(save_dir) / 'model_comparison.json'
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w') as f:
            json.dump(comparison, f, indent=2)

    return comparison


def print_model_comparison(comparison: Dict[str, Any]):
    """Print a formatted model comparison."""
    print("=" * 100)
    print("MODEL COMPARISON REPORT")
    print("=" * 100)

    models = list(comparison['models'].keys())

    # Parameter comparison
    print(f"\nPARAMETER COMPARISON:")
    print(f"{'Model':<20} {'Total Params':<15} {'Trainable':<15} {'Memory (MB)':<15}")
    print("-" * 65)
    for model_name in models:
        param_stats = comparison['models'][model_name]['parameter_analysis']
        print(f"{model_name:<20} {param_stats['total_parameters']:<15,} "
              f"{param_stats['trainable_parameters']:<15,} {param_stats['parameter_memory_mb']:<15.2f}")

    # FLOP comparison
    print(f"\nCOMPUTATIONAL COMPARISON:")
    print(f"{'Model':<20} {'Total FLOPs':<15} {'GFLOPs':<12} {'FLOPs/Param':<12}")
    print("-" * 60)
    for model_name in models:
        flop_stats = comparison['models'][model_name]['flop_analysis']
        print(f"{model_name:<20} {flop_stats['total_flops']:<15,} "
              f"{flop_stats['total_gflop']:<12.4f} {flop_stats['flops_per_parameter']:<12.2f}")

    # Memory comparison
    print(f"\nMEMORY COMPARISON:")
    print(f"{'Model':<20} {'Total (MB)':<12} {'Params (MB)':<12} {'Activation (MB)':<15}")
    print("-" * 60)
    for model_name in models:
        mem_stats = comparison['models'][model_name]['memory_analysis']
        print(f"{model_name:<20} {mem_stats['total_memory_mb']:<12.2f} "
              f"{mem_stats['parameter_memory_mb']:<12.2f} {mem_stats['activation_memory_mb']:<15.2f}")

    print("=" * 100)