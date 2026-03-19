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

Reference-only material such as baseline projects, archived scripts, and upstream flow snapshots now lives under `reference/` and is not part of the installable package.

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

If you are entering the container from a host shell that has Conda active, use a clean shell so host Python does not override the container Python:

```bash
singularity exec --cleanenv --nv /path/to/pytorch_26.02-py3.sif /bin/bash --noprofile --norc -i
```

This uses `--cleanenv` plus `bash --noprofile --norc`, which prevents inherited host `PATH` entries such as `~/miniconda3/bin` from taking precedence inside the container.

If you want the host shell itself to stop auto-entering Conda `base`, run this once on the host:

```bash
conda config --set auto_activate_base false
```

2. Inspect the registered datasets:

```bash
python -m capbench datasets list
```

3. Install a dataset in one step:

```bash
python -m capbench datasets install nangate45/small
```

This downloads the dataset into the shared cache, cleans partial preprocessing leftovers, and generates all configured derivable artifacts up front.

4. Open a visualization:

```bash
python -m capbench visualize density --dataset nangate45/small --window W0
python -m capbench visualize point-cloud --dataset nangate45/small --window W0
python -m capbench visualize cap3d --dataset nangate45/small --window W0
```

## Repository Layout

- `src/capbench/`: the only installable Python package
- `reference/`: non-supported historical baselines, archived scripts, and flow snapshots kept for provenance

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
- `CAPBENCH_DATASET_ROOT`: override the legacy default dataset root for older scripts

The cache is the source of truth. CapBench now operates directly on cached dataset paths rather than creating repo-local symlink workspaces.

## Standard CLI

### Datasets

```bash
python -m capbench datasets list
python -m capbench datasets info nangate45/small
python -m capbench datasets install nangate45/small
python -m capbench datasets ensure nangate45/small --artifact density_maps binary-masks
python -m capbench datasets preprocess nangate45/small --artifact point_clouds
```

`install` is the recommended one-shot setup command. It downloads the dataset into the shared cache and generates all configured derivable artifacts up front.

Loaders and visualization commands no longer generate or download artifacts implicitly. Run `python -m capbench datasets install <dataset>` first, then use the cached dataset normally.

`ensure` and `preprocess` remain available for incremental or developer workflows when you only want part of the dataset state.

### Visualization

```bash
python -m capbench visualize density --dataset nangate45/small --window W0
python -m capbench visualize point-cloud --dataset nangate45/small --window W0
python -m capbench visualize cap3d --dataset nangate45/small --window W0
```

### Developer Tooling

Developer-only flows are grouped under `python -m capbench dev`:

```bash
python -m capbench dev list
python -m capbench dev window-pipeline -- --windows-file /abs/path/windows.yaml --dataset-path /abs/path/dataset --pipeline binary_masks
python -m capbench dev partition-cap3d -- --dataset-path /abs/path/dataset
python -m capbench dev openrcx -- --process-nodes nangate45 --sizes small
python -m capbench dev rwcap -- --process-nodes nangate45 --sizes small
python -m capbench dev window-metadata -- --help
```

These tools remain available for dataset authoring and maintenance, but they are not the default user workflow.

## Python API

The supported public namespace is `capbench.*`.

```python
from capbench.datasets import install_dataset, resolve_dataset_path
from capbench.dataloaders import load_density_window_dataset, load_binary_mask_window_dataset

root = install_dataset("nangate45/small")
dataset = load_binary_mask_window_dataset("nangate45/small", goal="self")
```

Legacy top-level modules such as `common`, `window_tools`, `spef_tools`, and `viewers` are no longer packaged. Supported code should import only `capbench.*`.

## Registered Data Sources

The built-in registry currently includes:

- `nangate45/small`
  Uses the Zenodo archive as the canonical source.

If you expand the Zenodo upload with more preprocessed artifacts, update `src/capbench/data/datasets.json` so the cached dataset metadata matches what is actually bundled.

## Notes On Scope

- CapBench focuses on reusable data, loaders, visualization, and preprocessing/dev utilities.
- Downstream research projects, model training, MONAI/TensorRT pipelines, and experiment-heavy workflows should live outside this repository, for example in `CNNCap-flash`.
