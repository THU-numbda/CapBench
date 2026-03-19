# CapBench

CapBench is now a pip-first Python library for cached layout datasets, standardized dataloaders, visualization tools, and developer-oriented preprocessing utilities.

The supported user-facing surface is:

- cached dataset download and preprocessing
- standardized dataloader access for density maps and binary masks
- visualization for CAP3D, density maps, and point clouds

The following flows remain in the repository, but are considered developer-only tooling rather than the default product:

- window metadata generation
- CAP3D generation and partitioning
- preprocessing pipeline authoring workflows
- OpenRCX / RWCap maintenance helpers

> [!WARNING]
> **Repository Status**: This repository is being mirrored by a different repository that is currently under review for a conference. Please **do not push any changes directly to the main branch**. Use feature branches or forks for development work.

## Quickstart After Clone

1. Install CapBench into the current Python environment:

```bash
python -m pip install -e ".[all]"
```

This works the same way in a conda environment, a standard Python virtual environment, or directly inside your container. Using `python -m pip` ensures the install targets the active interpreter.

If you want an isolated virtual environment first:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[all]"
```

If you are already inside your PyTorch container, just run the same `python -m pip install -e ".[all]"` command there.

2. Inspect the registered datasets:

```bash
capbench datasets list
```

3. Download a dataset into the shared cache:

```bash
capbench datasets ensure nangate45/small
```

4. Materialize a workspace symlink into the current clone if you want a local `datasets/` tree:

```bash
capbench datasets materialize nangate45/small
```

By default this creates:

```text
./datasets/nangate45/small -> ~/.cache/capbench/datasets/nangate45/small/<version>/workspace
```

5. Open a visualization:

```bash
capbench visualize density --dataset nangate45/small --window W0
capbench visualize point-cloud --dataset nangate45/small --window W0
capbench visualize cap3d --dataset nangate45/small --window W0
```

## Cache Model

CapBench stores downloaded and generated data in a shared user cache:

```text
~/.cache/capbench/
  downloads/
  datasets/
  registry/
```

Useful environment variables:

- `CAPBENCH_CACHE_DIR`: override the shared cache root
- `CAPBENCH_WORKSPACE_ROOT`: override where `materialize` creates symlinks
- `CAPBENCH_DATASET_ROOT`: override the legacy default dataset root for older scripts

The cache is the source of truth. Repo-local `datasets/` paths are optional symlinks created for convenience.

## Standard CLI

### Datasets

```bash
capbench datasets list
capbench datasets info nangate45/small
capbench datasets ensure nangate45/small --artifact density_maps binary-masks
capbench datasets materialize nangate45/small
capbench datasets preprocess nangate45/small --artifact point_clouds
```

`ensure` downloads the dataset into the shared cache. If requested artifacts are missing and derivable, CapBench generates them into the cached workspace.

### Visualization

```bash
capbench visualize density --dataset nangate45/small --window W0
capbench visualize point-cloud --dataset nangate45/small --window W0
capbench visualize cap3d --dataset nangate45/small --window W0
```

### Developer Tooling

Developer-only flows are grouped under `capbench dev`:

```bash
capbench dev list
capbench dev window-pipeline -- --windows-file /abs/path/windows.yaml --dataset-path /abs/path/dataset --pipeline binary_masks
capbench dev partition-cap3d -- --dataset-path /abs/path/dataset
capbench dev openrcx -- --process-nodes nangate45 --sizes small
capbench dev rwcap -- --process-nodes nangate45 --sizes small
capbench dev window-metadata -- --help
```

These tools remain available for dataset authoring and maintenance, but they are not the default user workflow.

## Python API

The supported public namespace is `capbench.*`.

```python
from capbench.datasets import ensure_dataset, resolve_dataset_path
from capbench.dataloaders import load_density_window_dataset, load_binary_mask_window_dataset

root = ensure_dataset("nangate45/small", artifacts=["binary-masks"])
dataset = load_binary_mask_window_dataset("nangate45/small", goal="self")
```

The current top-level modules like `common`, `window_tools`, and `spef_tools` still exist for compatibility with the legacy codebase, but new code should prefer `capbench.*`.

## Registered Data Sources

The built-in registry currently includes:

- `nangate45/small`
  Uses the Zenodo archive as the canonical source.

If you expand the Zenodo upload with more preprocessed artifacts, update `capbench/data/datasets.json` so the cached dataset metadata matches what is actually bundled.

## Notes On Scope

- CapBench focuses on reusable data, loaders, visualization, and preprocessing/dev utilities.
- Downstream research projects, model training, MONAI/TensorRT pipelines, and experiment-heavy workflows should live outside this repository, for example in `CNNCap-flash`.
