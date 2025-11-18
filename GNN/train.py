#!/usr/bin/env python3
"""
GNN-Cap Training - Main Entry Point

This is the main training script for GNN-Cap capacitance prediction models.
It uses PyTorch Lightning for simplified, robust training with automatic
device management, gradient tracking, and logging.

Usage:
    # Train total capacitance model
    python train.py --model-type total --epochs 50

    # Train both models
    python train.py --model-type both --epochs 50

    # Advanced configuration
    python train.py --model-type total --epochs 100 --lr 0.001 --batch-size 2
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modern training implementation
from train_lightning import main

if __name__ == "__main__":
    main()