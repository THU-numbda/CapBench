# Maintained training baselines

This directory contains the runnable model implementations used by the checked-in
recipes under `recipes/paper/`:

- `cnn/`: variable-channel ResNet models and the shard-backed density-window trainer;
- `pct/`: PCT-Cap, point-cloud sampling, and training code;
- `gnn/`: two-layer GCN, GAT, and GATv2 models, graph loading, and Lightning training.

The model entrypoints deliberately live outside the installable `capbench` package.
They consume the package's public cache, SPEF, dataloader, metric, and window-split
interfaces, while keeping experimental model code separate from the stable library
API.

The CNN ResNet implementation is adapted from `torchvision.models.resnet` and is
distributed under the BSD 3-Clause license in `cnn/LICENSE`. The PCT implementation
retains its upstream Mulan PSL v2 notices and license in `pct/LICENSE`.

These baselines approximate the CapBench paper protocol. The original private
training implementation and every unpublished hyperparameter are not available, so
the repository reports both the pinned choices and measured deviations explicitly.
See `docs/training-baselines.md` and `docs/baseline-results.md`.
