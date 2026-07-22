# Maintained training baselines

This directory contains the runnable model implementations configured by
`recipes/paper.yaml` and launched through `scripts/train.py`:

- `cnn/`: variable-channel ResNet models and the shard-backed density-window trainer;
- `pct/`: PCT-Cap, point-cloud sampling, and training code;
- `gnn/`: two-layer GCN, GAT, and GATv2 models, graph loading, and Lightning training.

The model entrypoints deliberately live outside the installable `capbench` package.
They consume the package's public cache, SPEF, dataloader, metric, and window-split
interfaces, while keeping experimental model code separate from the stable library
API.

These baselines approximate the CapBench paper protocol. The original private
training implementation and every unpublished hyperparameter are not available, so
the single configuration file records the public, reproducible choices explicitly.
