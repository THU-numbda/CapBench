# CapBench

CapBench is a pip-first Python library for cached layout datasets, standardized dataloaders, and visualization.

The supported user-facing surface is:

- cached dataset download and inspection
- standardized dataloader access for CAP3D-backed density maps and density-map ID maps
- visualization for CAP3D

The following flows remain in the repository, but are considered developer-only tooling rather than the default product:

- window metadata generation
- CAP3D generation and partitioning
- artifact authoring and repair workflows
- density exploration
- OpenRCX / RWCap maintenance helpers

Reference material such as development scripts, baseline projects, and upstream flow snapshots now lives under `reference/` and is not part of the installable package.

> [!WARNING]
> **Repository Status**: This repository is being mirrored by a different repository that is currently under review for a conference. Please **do not push any changes directly to the main branch**. Use feature branches or forks for development work.

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
- `tools/`: repo-local developer tools for dataset authoring and maintenance
- `reference/`: development scripts, historical baselines, and flow snapshots kept for provenance

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
python -m tools.preprocess.window_processing_pipeline --windows-file /abs/path/windows.yaml --dataset-path /abs/path/dataset --pipeline cnn
python -m tools.maintenance.partition_cap3d --dataset-path /abs/path/dataset
python -m tools.maintenance.openrcx --process-nodes nangate45 --sizes small
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

## Notes On Scope

- CapBench focuses on reusable data, loaders, and visualization.
- Dataset-authoring and repair tooling stays in the repository under `tools/`, outside the installable package.
- Downstream research projects, model training, MONAI/TensorRT pipelines, and experiment-heavy workflows should live outside this repository, for example in `CNNCap-flash`.
