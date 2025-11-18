# Dataset Overview
This repository contains the generated windows accross Nangate45, ASAP7, and SKY130HD technology nodes, each split into `small`, `medium`, and `large` buckets. Additionally, this directory contains the compressed original assets from the `synth_designs`.

## Data
Every PDK bucket exposes consistent subdirectories (`gds`, `def`, `density_maps`, `point_clouds`, `cap3d`, `graphs`) to keep geometry, derived features, and metadata aligned per block.

## Labels
Labels live beside each block under `labels_rwcap`, `labels_raphael`, and, where available, `labels_openrcx`, reflecting capacitance ground-truth extracted by the respective field solvers.

> **Warning:** The full uncompressed datasets occupy dozens of gigabytes; ensure you have adequate local disk space before copying or repackaging them.
