#!/usr/bin/env python3
"""
Minimal entry point for training the 2-layer GNN models.

Example:
    python train.py --conv-type gatv2 --epochs 100 --lr 5e-4
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
