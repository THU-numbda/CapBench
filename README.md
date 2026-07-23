# CapBench

CapBench is a pip-first Python library for cached layout datasets, standardized
dataloaders, visualization, and maintained CNN/PCT/GNN training baselines.

The supported user-facing surface is:

- cached dataset download and inspection
- standardized dataloader access for CAP3D-backed density maps and density-map ID maps
- visualization for CAP3D
- paper-like CNN, PCT, GCN, GAT, and GATv2 training configurations

The following flows remain in the repository, but are considered developer-only tooling rather than the default product:

- window metadata generation
- CAP3D generation and partitioning
- artifact authoring and repair workflows
- density exploration
- RWCap maintenance helpers

Reference material such as development scripts, historical baseline snapshots,
and upstream flow snapshots lives under `reference/` and is not part of the
installable package. Runnable baselines live under `models/` and use the public
`capbench.*` data interfaces.

## Quickstart After Clone

1. Install the library into the current Python environment:

```bash
python -m pip install -e .
```

If you also want visualization extras and the repo-local developer tools available, install the full dependency set instead:

```bash
python -m pip install -e ".[all]"
```

Using `python -m pip` ensures the install targets the active interpreter. This works the same way in a conda environment, a standard Python virtual environment, or directly inside your container.

2. Inspect the registered datasets:

```bash
python -m capbench datasets list
```

3. Install a dataset in one step:

```bash
python -m capbench datasets install nangate45
```

This downloads and extracts the whole PDK archive into the shared cache, then reports which artifacts are present for each available split (`small`, `medium`, `large`). `install` does not generate missing artifacts.

4. Open a visualization:

```bash
python -m capbench visualize cap3d --dataset nangate45/small --window W0
```

## Repository Layout

- `src/capbench/`: the only installable Python package
- `models/`: maintained CNN, PCT, and GNN model/training entrypoints
- `recipes/paper.yaml`: Nangate45 and Sky130HD baseline configurations
- `tools/`: repo-local developer tools for dataset authoring and maintenance
- `reference/`: development scripts, historical baselines, and flow snapshots kept for provenance

## Train the CNN, PCT, and GNN models

Install the training dependencies and download either validated dataset:

```bash
python -m pip install -e ".[baselines]"
python -m capbench datasets install nangate45
# or: python -m capbench datasets install sky130hd
```

The Nangate45 and Sky130HD downloads already include the CNN density-map inputs,
PCT point clouds, and GNN graphs, together with the corresponding labels. No
separate preprocessing step is required before training.

The launcher reads the paper-like settings from the single
`recipes/paper.yaml` file. Run any model by selecting its PDK and model name:

```bash
python scripts/train.py --pdk nangate45 --model cnn --gpu 0
python scripts/train.py --pdk nangate45 --model pct --gpu 0
python scripts/train.py --pdk nangate45 --model gcn --gpu 0
python scripts/train.py --pdk nangate45 --model gat --gpu 0
python scripts/train.py --pdk nangate45 --model gatv2 --gpu 0
```

Replace `nangate45` with `sky130hd` to train on Sky130HD. The default
configuration uses the small split, a seeded 80/20 window split, MSRE, Adam at
`1e-4`, and 50 epochs. Trainer settings can be changed with repeated
`--set KEY=VALUE` arguments.

## Cache Model

CapBench stores downloaded and cached data in a shared user cache:

```text
~/.cache/capbench/
  downloads/
  datasets/
  registry/
```

Useful environment variables:

- `CAPBENCH_CACHE_DIR`: override the shared cache root
- `CAPBENCH_DATASET_ROOT`: override the legacy default dataset root for older scripts

The cache is the source of truth. CapBench operates on cached dataset paths rather than repo-local workspaces.

## Standard CLI

### Datasets

```bash
python -m capbench datasets list
python -m capbench datasets info nangate45
python -m capbench datasets info nangate45/small
python -m capbench datasets install nangate45
```

`install` is the only public download/setup command. It downloads the PDK archive into the shared cache, extracts it, cleans partial temporary directories, and reports artifact presence for every registered split of that PDK.

Loaders and visualization commands do not generate or download artifacts implicitly. Run `python -m capbench datasets install <pdk>` first, then use exact split ids such as `nangate45/small` with the cached dataset normally. If an archive is incomplete, the missing artifacts are reported in `datasets info` and the status table shown after `install`.

### Visualization

```bash
python -m capbench visualize cap3d --dataset nangate45/small --window W0
```

### Developer Tooling

Developer-only flows live under the repo-local `tools/` namespace and are not part of the public `capbench` package:

```bash
python -m tools.preprocess.window_processing_pipeline --windows-file /abs/path/windows.yaml --dataset-path /abs/path/dataset --pipeline cnn pct gnn
python -m tools.maintenance.rwcap --rwcap-bin /abs/path/to/rwcap --process-nodes nangate45 --sizes small --jobs 8
python -m tools.maintenance.window_metadata --help
python -m tools.maintenance.density_explorer --cap3d /abs/path/window.cap3d
```

These tools remain available for dataset authoring and maintenance, but they are not the default user workflow. Run them from the repository root.
`tools.maintenance.rwcap` scans the shared CapBench dataset cache by default and writes `out_rwcap/` under each cached dataset split.

## Python API

The supported public namespace is `capbench.*`.

```python
from capbench.datasets import install_dataset, resolve_dataset_path
from capbench.dataloaders import load_density_window_dataset, load_density_id_window_dataset

root = install_dataset("nangate45")
dataset = load_density_id_window_dataset("nangate45/small", goal="self")
```

Legacy top-level modules such as `common`, `window_tools`, `spef_tools`, and `viewers` are no longer packaged. Supported code should import only `capbench.*`.

## Registered Data Sources

The built-in registry currently includes:

- `nangate45`
- `sky130hd`
- `asap7`

Each PDK archive currently exposes the `small`, `medium`, and `large` dataset splits.

If you change what an archive contains, update `src/capbench/data/datasets.json` so the cached dataset metadata matches what is actually bundled.
