#!/usr/bin/env python3
"""
GNN-Cap Main CLI Entry Point

Command-line interface for the complete GNN-Cap pipeline:
- Preprocessing: Convert CAP3D to graphs
- Training: Train total and coupling capacitance models
- Inference: Extract capacitances for full chip
- Visualization: Inspect graph structures

Example usage:
    python main.py preprocess --input design.cap3d --output-dir data/processed
    python main.py train --data-dir data/processed --model both
    python main.py inference --input-dir data/processed --output results/caps.csv
    python main.py visualize --file data/processed/chunk_0.pt
"""

import argparse
import sys
from pathlib import Path
import subprocess

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

import config


def run_preprocess(args):
    """Run CAP3D to graph conversion"""
    print("=" * 80)
    print("PREPROCESSING: CAP3D TO GRAPH CONVERSION")
    print("=" * 80)

    # Build command
    cap3d_script = Path(__file__).parent.parent.parent / 'cap3d' / 'cap3d_to_gnncap.py'

    cmd = [
        'python', str(cap3d_script),
        args.input,
        '-o', args.output_dir,
        '--window-size', str(args.window_size),
    ]

    if args.cuboid_max_length is not None:
        cmd.extend(['--cuboid-max-length', str(args.cuboid_max_length)])
    if args.edge_threshold is not None:
        cmd.extend(['--edge-threshold', str(args.edge_threshold)])
    if args.virtual_edge_threshold is not None:
        cmd.extend(['--virtual-edge-threshold', str(args.virtual_edge_threshold)])

    # Virtual edges are disabled by default for simplified training

    if args.chunk_layout:
        cmd.append('--chunk-layout')

    if args.num_chunks:
        cmd.extend(['--num-chunks', str(args.num_chunks)])

    # Run
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def run_train(args):
    """Run model training with PyTorch Lightning"""
    print("=" * 80)
    print("TRAINING GNN-CAP MODELS")
    print("=" * 80)

    # Build command for Lightning training
    train_script = Path(__file__).parent / 'train_lightning.py'

    cmd = [
        'python', str(train_script),
        '--model-type', args.model,
        '--epochs', str(args.epochs),
        '--lr', str(args.lr),
    ]

    # Add data directory if specified
    if args.data_dir:
        cmd.extend(['--data-dir', args.data_dir])

    if getattr(args, 'net_aggregation', None):
        cmd.extend(['--net-aggregation', args.net_aggregation])
    if getattr(args, 'net_aggregation_hidden', None) is not None:
        cmd.extend(['--net-aggregation-hidden', str(args.net_aggregation_hidden)])

    # Model architecture options
    if args.use_attention:
        cmd.append('--use-attention')
    if args.attention_type != 'gat':
        cmd.extend(['--attention-type', args.attention_type])
    if args.num_heads != 4:
        cmd.extend(['--num-heads', str(args.num_heads)])
    if args.num_layers != 2:
        cmd.extend(['--num-layers', str(args.num_layers)])

    # Batch size is fixed at 1 for stable training of variable-sized graphs

    # Note: --no-cuda and --no-fp16 are handled automatically by Lightning

    # Virtual edges are disabled by default for simplified training

    # Run
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def run_inference(args):
    """Run inference"""
    print("=" * 80)
    print("INFERENCE: FULL-CHIP CAPACITANCE EXTRACTION")
    print("=" * 80)

    # Build command
    inference_script = Path(__file__).parent / 'inference.py'

    cmd = [
        'python', str(inference_script),
        '--input-dir', args.input_dir,
        '--total-model', args.total_model,
        '--coupling-model', args.coupling_model,
        '--output', args.output,
        '--batch-size', str(args.batch_size),
    ]

    if args.no_cuda:
        cmd.append('--no-cuda')

    if args.no_fp16:
        cmd.append('--no-fp16')

    if getattr(args, 'aggregation', None):
        cmd.extend(['--aggregation', args.aggregation])
    if getattr(args, 'aggregation_hidden_dim', None) is not None:
        cmd.extend(['--aggregation-hidden-dim', str(args.aggregation_hidden_dim)])

    # Virtual edges are disabled by default for simplified training

    # Run
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def run_visualize(args):
    """Run visualization"""
    print("=" * 80)
    print("VISUALIZATION: INTERACTIVE GRAPH")
    print("=" * 80)

    # Build command
    viz_script = Path(__file__).parent / 'utils' / 'visualize.py'

    cmd = [
        'python', str(viz_script),
        args.file,
    ]

    if args.output:
        cmd.extend(['-o', args.output])

    cmd.extend(['--color-by', args.color_by])

    if args.no_physics:
        cmd.append('--no-physics')

    # Run
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='GNN-Cap: Graph Neural Network for Chip-Scale Capacitance Extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preprocess CAP3D file into graph chunks
  python main.py preprocess --input design.cap3d --chunk-layout --num-chunks 400

  # Train both models
  python main.py train --data-dir data/processed --model both --epochs 50

  # Run inference
  python main.py inference --input-dir data/processed \\
      --total-model checkpoints/best_total.pth \\
      --coupling-model checkpoints/best_coupling.pth \\
      --output results/capacitances.csv

  # Visualize a graph
  python main.py visualize --file data/processed/chunk_0.pt --color-by net

For more information, see README.md
        """
    )

    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')

    # ========================================================================
    # PREPROCESS
    # ========================================================================
    preprocess_parser = subparsers.add_parser('preprocess', help='Convert CAP3D to graphs')
    preprocess_parser.add_argument('--input', required=True, help='Input .cap3d file')
    preprocess_parser.add_argument('--output-dir', default='./data/processed',
                                    help='Output directory for graphs')
    preprocess_parser.add_argument('--window-size', type=float, default=20.0,
                                    help='Window size in micrometers')
    preprocess_parser.add_argument('--cuboid-max-length', type=float, default=None,
                                    help='Override cuboid max length (μm); defaults to process-node preset')
    preprocess_parser.add_argument('--edge-threshold', type=float, default=None,
                                    help='Override edge distance threshold (μm); defaults to process-node preset')
    preprocess_parser.add_argument('--virtual-edge-threshold', type=float, default=None,
                                    help='Override virtual edge distance threshold (μm); defaults to process-node preset')
    preprocess_parser.add_argument('--no-virtual-edges', action='store_true',
                                    help='Disable virtual edges')
    preprocess_parser.add_argument('--chunk-layout', action='store_true',
                                    help='Chunk layout into windows for training')
    preprocess_parser.add_argument('--num-chunks', type=int, default=None,
                                    help='Number of chunks to generate')

    # ========================================================================
    # TRAIN
    # ========================================================================
    train_parser = subparsers.add_parser('train', help='Train GNN-Cap models')
    train_parser.add_argument('--data-dir', required=True, help='Directory with graph .pt files')
    train_parser.add_argument('--model', choices=['total', 'coupling', 'both'], default='both',
                              help='Which model to train')
    train_parser.add_argument('--epochs', type=int, default=50,
                              help='Number of epochs')
    train_parser.add_argument('--lr', type=float, default=1e-4,
                              help='Learning rate')
    train_parser.add_argument('--net-aggregation', choices=['none', 'mean', 'self_attention'],
                              default='self_attention',
                              help='Net aggregation method for total capacitance model')
    train_parser.add_argument('--net-aggregation-hidden', type=int, default=128,
                              help='Hidden dimension for net aggregation attention')

    # Model architecture options
    train_parser.add_argument('--num-layers', type=int, default=2,
                              help='Number of GNN layers')
    train_parser.add_argument('--use-attention', action='store_true',
                              help='Enable attention mechanism')
    train_parser.add_argument('--attention-type',
                              choices=['gat', 'gatv2'],
                              default='gat',
                              help='Type of attention mechanism')
    train_parser.add_argument('--num-heads', type=int, default=4,
                              help='Number of attention heads')

    # Note: CUDA, FP16, and virtual edges are handled automatically by Lightning
    # Virtual edges are disabled by default for simplified training

    # ========================================================================
    # INFERENCE
    # ========================================================================
    inference_parser = subparsers.add_parser('inference', help='Run inference for full chip')
    inference_parser.add_argument('--input-dir', required=True,
                                   help='Directory with graph .pt files')
    inference_parser.add_argument('--total-model', required=True,
                                   help='Path to total capacitance model checkpoint')
    inference_parser.add_argument('--coupling-model', required=True,
                                   help='Path to coupling capacitance model checkpoint')
    inference_parser.add_argument('--output', required=True,
                                   help='Output CSV file path')
    # Batch size is fixed at 1 for stable inference
    inference_parser.add_argument('--no-cuda', action='store_true', help='Disable CUDA')
    inference_parser.add_argument('--no-fp16', action='store_true', help='Disable FP16 inference')
    inference_parser.add_argument('--no-virtual-edges', action='store_true',
                                   help='Disable virtual edges')
    inference_parser.add_argument('--aggregation', choices=['none', 'mean', 'self_attention'],
                                   default='self_attention',
                                   help='Net aggregation method for the total model')
    inference_parser.add_argument('--aggregation-hidden-dim', type=int, default=128,
                                   help='Hidden dimension for attention-based aggregation')

    # ========================================================================
    # VISUALIZE
    # ========================================================================
    viz_parser = subparsers.add_parser('visualize', help='Visualize graph structure')
    viz_parser.add_argument('--file', required=True, help='Input .pt graph file')
    viz_parser.add_argument('--output', help='Output HTML file (default: auto)')
    viz_parser.add_argument('--color-by', choices=['net', 'layer', 'none'], default='net',
                            help='How to color nodes')
    viz_parser.add_argument('--no-physics', action='store_true',
                            help='Disable physics simulation')

    # Parse arguments
    args = parser.parse_args()

    if args.mode is None:
        parser.print_help()
        return 1

    # Route to appropriate handler
    if args.mode == 'preprocess':
        return run_preprocess(args)
    elif args.mode == 'train':
        return run_train(args)
    elif args.mode == 'inference':
        return run_inference(args)
    elif args.mode == 'visualize':
        return run_visualize(args)
    else:
        print(f"Unknown mode: {args.mode}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
