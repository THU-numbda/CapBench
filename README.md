# CapBench: A Multi-PDK Dataset for ML-Based Capacitance Extraction

CapBench is a pip-first Python library for cached layout datasets, standardized
dataloaders, visualization, and maintained CNN, point-cloud-transformer (PCT),
and graph-neural-network (GNN) baselines. It accompanies the
[DAC 2026 paper](https://arxiv.org/abs/2604.11202).

## Quick Start

1. Install the library into the current Python environment:

```bash
python -m pip install -e .
```

To include visualization extras and repository-local developer tools, install
the full dependency set instead:

```bash
python -m pip install -e ".[all]"
```

Using `python -m pip` ensures that the install targets the active interpreter.
The commands work in a conda environment, a standard Python virtual environment,
or a container.

2. Inspect the registered datasets:

```bash
python -m capbench datasets list
```

3. Install a dataset:

```bash
python -m capbench datasets install nangate45
```

This downloads and extracts the complete PDK archive into the shared cache, then
reports which artifacts are present for each available split (`small`, `medium`,
and `large`). The command does not generate missing artifacts.

4. Open a visualization:

```bash
python -m capbench visualize cap3d --dataset nangate45/small --window W0
```

## Supported Workflows

The supported user-facing interface provides:

- Cached dataset download and inspection
- Standardized dataloaders for CAP3D-backed density maps and density-map ID maps
- CAP3D visualization
- Paper-like CNN, PCT, GCN, GAT, and GATv2 training configurations

Runnable baselines live under `models/` and use the public `capbench.*` data
interfaces. Development scripts, historical baseline snapshots, and upstream
flow snapshots live under `reference/` and are not part of the installable
package.

Dataset-authoring and maintenance workflows—including window metadata
generation, CAP3D generation and partitioning, artifact repair, density
exploration, and RWCap helpers—remain available as developer tooling rather than
as part of the default user workflow.

## Dataset Access

```bash
python -m capbench datasets list
python -m capbench datasets info nangate45
python -m capbench datasets info nangate45/small
python -m capbench datasets install nangate45
```

`install` is the only public download and setup command. It downloads the PDK
archive into the shared cache, extracts it, cleans partial temporary
directories, and reports artifact presence for every registered split.

Loaders and visualization commands do not generate or download artifacts
implicitly. Run `python -m capbench datasets install <pdk>` first, then use an
exact split ID such as `nangate45/small`. If an archive is incomplete, the
missing artifacts appear in `datasets info` and in the status table shown after
`install`.

### Registered Data Sources

The built-in registry includes:

- `nangate45`
- `sky130hd`
- `asap7`

Each PDK archive exposes `small`, `medium`, and `large` dataset splits. If an
archive's contents change, update `src/capbench/data/datasets.json` so the
cached dataset metadata remains consistent with the bundle.

### Cache Layout

CapBench stores downloaded and cached data in a shared user cache:

```text
~/.cache/capbench/
  downloads/
  datasets/
  registry/
```

Useful environment variables:

- `CAPBENCH_CACHE_DIR`: Override the shared cache root
- `CAPBENCH_DATASET_ROOT`: Override the legacy default dataset root for older
  scripts

The cache is the source of truth. CapBench operates on cached dataset paths
rather than repository-local workspaces.

## Train the Baselines

Install the training dependencies and download either validated dataset:

```bash
python -m pip install -e ".[baselines]"
python -m capbench datasets install nangate45
# or: python -m capbench datasets install sky130hd
```

The Nangate45 and Sky130HD downloads include the CNN density-map inputs, PCT
point clouds, and GNN graphs together with their labels. No separate
preprocessing step is required before training.

The launcher reads the paper-like settings from `recipes/paper.yaml`. Run a
model by selecting its PDK and model name:

```bash
python scripts/train.py --pdk nangate45 --model cnn --gpu 0
python scripts/train.py --pdk nangate45 --model pct --gpu 0
python scripts/train.py --pdk nangate45 --model gcn --gpu 0
python scripts/train.py --pdk nangate45 --model gat --gpu 0
python scripts/train.py --pdk nangate45 --model gatv2 --gpu 0
```

Replace `nangate45` with `sky130hd` to train on Sky130HD. The default
configuration uses the small split, a seeded 80/20 window split, MSRE, Adam at
`1e-4`, and 50 epochs. Override trainer settings with repeated `--set KEY=VALUE`
arguments.

## Python API

The supported public namespace is `capbench.*`:

```python
from capbench.datasets import install_dataset, resolve_dataset_path
from capbench.dataloaders import load_density_window_dataset, load_density_id_window_dataset

root = install_dataset("nangate45")
dataset = load_density_id_window_dataset("nangate45/small", goal="self")
```

Legacy top-level modules such as `common`, `window_tools`, `spef_tools`, and
`viewers` are no longer packaged. Supported code should import only
`capbench.*`.

## Developer Tooling

Developer-only flows live under the repository-local `tools/` namespace and are
not part of the public `capbench` package:

```bash
python -m tools.preprocess.window_processing_pipeline --windows-file /abs/path/windows.yaml --dataset-path /abs/path/dataset --pipeline cnn pct gnn
python -m tools.maintenance.rwcap --rwcap-bin /abs/path/to/rwcap --process-nodes nangate45 --sizes small --jobs 8
python -m tools.maintenance.window_metadata --help
python -m tools.maintenance.density_explorer --cap3d /abs/path/window.cap3d
```

Run these commands from the repository root. `tools.maintenance.rwcap` scans the
shared CapBench cache by default and writes `out_rwcap/` under each cached
dataset split.

## Repository Layout

- `src/capbench/`: The only installable Python package
- `models/`: Maintained CNN, PCT, and GNN model and training entry points
- `recipes/paper.yaml`: Nangate45 and Sky130HD baseline configurations
- `tools/`: Repository-local dataset-authoring and maintenance tools
- `reference/`: Development scripts, historical baselines, and flow snapshots
  retained for provenance

## Reproduce the Paper Baselines

Install the baseline dependencies, install one of the validated datasets, and
run the commands in [Train the Baselines](#train-the-baselines). The paper-like
configurations are defined in `recipes/paper.yaml`; use repeated
`--set KEY=VALUE` arguments only when intentionally overriding those settings.

## Citation

If you use the CapBench dataset, library, or baselines in academic work, please
cite the [DAC 2026 paper](https://arxiv.org/abs/2604.11202):

```bibtex
@inproceedings{rodriguez2026capbench,
  title         = {CapBench: A Multi-PDK Dataset for Machine-Learning-Based Post-Layout Capacitance Extraction},
  author        = {Rodriguez, Hector R. and Huang, Jiechen and Yu, Wenjian},
  booktitle     = {Proceedings of the 63rd ACM/IEEE Design Automation Conference (DAC)},
  year          = {2026},
  eprint        = {2604.11202},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AR},
  url           = {https://arxiv.org/abs/2604.11202}
}
```
