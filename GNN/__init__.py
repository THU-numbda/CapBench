"""
GNN-Cap: Graph Neural Network for Chip-Scale Capacitance Extraction

Implementation of the IEEE TCAD 2024 paper by Liu et al.
"""

__version__ = '1.0.0'
__author__ = 'Implementation based on Liu et al. IEEE TCAD 2024'

from . import config
from .models import gnncap_model
from .data_utils import dataloader

__all__ = ['config', 'gnncap_model', 'dataloader']
