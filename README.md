# CapBench: A Multi-PDK Dataset for Machine-Learning-Based Post-Layout Capacitance Extraction

A complete pipeline for producing parasitic-capacitance datasets from OpenROAD layouts and training the three reference models (CNN‑Cap, PCT‑Cap, and GNN). This document focuses on the concrete steps needed to reproduce the paper results and highlights the auxiliary tooling that ships with the repository.

## Basic Reproduction Tasks

### 1. Prepare the environment
1. Create the Conda environment (PyTorch 2.0, PyG, VTK, KLayout, gmsh, etc.):
   ```bash
   conda env create -f environment.yml
   conda activate cap3d-ml
   ```
2. From the repository root, source the helper script so every CLI tool can `import common.*`:
   ```bash
   source scripts/setup_env.sh
   ```
   `scripts/setup_env.sh` only appends the repository root to `PYTHONPATH`, so it is safe to re‑source inside terminals, tmux panes, and batch jobs.
3. (Optional) verify the toolchain:
   ```bash
   python -c "import torch, torch_geometric, klayout"
   ```

### 2. Download & unpack the datasets (Zenodo DOI: 10.5281/zenodo.17636283)
1. Visit https://doi.org/10.5281/zenodo.17636283 and download the archives you need (`nangate45.zip`, `sky130hd.zip`, `asap7.zip`, plus any auxiliary tarballs listed on the record). Every archive mirrors the directory structure expected by the scripts.
2. Extract each archive straight under `datasets/`:
   ```bash
   mkdir -p datasets
   cd datasets

   # Example: download and unpack Nangate45 and Sky130HD
   curl -L "https://zenodo.org/records/17636283/files/nangate45.zip?download=1" -o nangate45.zip
   curl -L "https://zenodo.org/records/17636283/files/sky130hd.zip?download=1" -o sky130hd.zip

   unzip nangate45.zip
   unzip sky130hd.zip
   ```
3. After extraction you should see:
   ```
   datasets/
     nangate45/
       small|medium|large/
         cap3d/  def/  gds/  density_maps/  point_clouds/  graphs/
         labels_rwcap/  labels_raphael/  labels_openrcx/
         windows.yaml
     sky130hd/
     asap7/
   ```
4. Keep the compressed files if you plan to rsync to other machines; otherwise delete them to save space.

### 3. Train the reference models
All three models read the standardized directory layout produced by the window pipeline: CAP3D windows in `cap3d/`, derived features in either `density_maps/`, `point_clouds/`, or `graphs/`, and solver labels in `labels_*`. If you need to regenerate those artifacts, use `window_tools/window_processing_pipeline.py` (see “Advanced workflow reference”).

#### CNN‑Cap (density maps)
```bash
python CNN-Cap/train.py \
  --tech tech/nangate45/nangate45_stack.yaml \
  --dataset-path datasets/nangate45/small \
  --window-dir datasets/nangate45/small/density_maps \
  --spef-dir datasets/nangate45/small/labels_rwcap \
  --epoch 50 --batch_size 64 --lr 1e-4 \
  --labels-solver rwcap \
  --savename nangate45_small_total.pth
```
* `--goal total|env` switches between total and coupling tasks.
* The script automatically builds window-level splits (`common/window_splitting.py`) to avoid leakage.

#### PCT‑Cap (point clouds)
```bash
python PCT-Cap/train.py \
  --dataset-path datasets/nangate45/small \
  --point-cloud-dir datasets/nangate45/small/point_clouds \
  --spef-dir datasets/nangate45/small/labels_rwcap \
  --goal self \
  --npoints 1024 --batch-size 64 --epochs 50 \
  --lr 1e-4 \
  --output-dir pct_runs/nangate45_small_self
```
* Use `--goal coupling` to regress only inter-net capacitances.
* `--val-split` defines the window-level split; `--num-sa-layers`, `--num-workers`, and `--gpu` expose model/runtime knobs.

#### GNN (graph representations)
```bash
python GNN/train.py \
  --dataset-path datasets/nangate45/small \
  --data-dir datasets/nangate45/small/graphs \
  --spef-dir datasets/nangate45/small/labels_rwcap \
  --model-type both \
  --num-layers 2 --use-attention --heads 4 \
  --epochs 50 --lr 1e-4
```
* `--model-type total|coupling|both` decides which Lightning module(s) to run; training “both” runs two passes back-to-back and stores checkpoints under `checkpoints/{total,coupling}`.

## Visualization utilities

The `viewers/` package contains lightweight VTK front-ends that help debug training samples. Run them from the repository root after activating `cap3d-ml` (they rely on `scripts/setup_env.sh`).

| Viewer | What it shows | Example command |
| --- | --- | --- |
| `viewers/viewer_cap3d.py` | 3D CAP3D solids with per-layer coloring | `python viewers/viewer_cap3d.py windows/cap3d/W0.cap3d --start-angle 30` |
| `viewers/viewer_cap3d_cross_section.py` | Orthogonal cross-sections through CAP3D | `python viewers/viewer_cap3d_cross_section.py windows/cap3d/W0.cap3d --plane z=0.5` |
| `viewers/viewer_density_maps.py` | Stack of CNN‑Cap density maps, optional CAP3D overlay | `python viewers/viewer_density_maps.py datasets/nangate45/small/density_maps/W0.npz --cap3d windows/cap3d/W0.cap3d` |
| `viewers/viewer_point_cloud.py` | Colored point clouds plus layer legend for PCT‑Cap | `python viewers/viewer_point_cloud.py datasets/nangate45/small/point_clouds/W0.npz --tech tech/nangate45/nangate45_stack.yaml` |
| `viewers/viewer_graph.py` | Cuboids/edges produced for GNN | `python viewers/viewer_graph.py datasets/nangate45/small/graphs/W0_graph.pt --tech tech/nangate45/nangate45_stack.yaml` |

Each viewer supports `--screenshot <png>` to capture the first frame and optional camera presets (`--start-angle`).

## Advanced workflow reference

Use these steps to regenerate designs from RTL, extend the dataset, or evaluate alternative label sources. All commands assume the environment has been prepared as described earlier.

### 1. OpenROAD design generation flow
1. Clone the official OpenROAD Flow Scripts (ORFS) somewhere with sufficient disk space:
   ```bash
   git clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git ~/orfs
   cd ~/orfs
   make build
   ```
2. Copy this repository’s design overlays (`nangate45/`, `sky130hd/`, `asap7/`, `src/`, `tools/`) into the ORFS `flow/designs/` tree. The recommended approach is an rsync from the model pipeline root:
   ```bash
   rsync -av /path/to/model_pipeline/OpenROAD-flow-scripts/ ~/orfs/flow/designs/
   ```
3. Launch the flow for any provided config (e.g., Nangate45 CVA6):
   ```bash
   cd ~/orfs
   make DESIGN_CONFIG=flow/designs/nangate45/cva6/config.mk
   ```
4. When the run completes, copy the resulting `*.def`, `*.gds`, and technology files back into this repository (`designs/def/`, `designs/gds/`, `designs/tech/`). The layout file names are the inputs consumed by the window pipeline and RWCap/OpenRCX scripts.

### 2. Window metadata generation (`scripts/window_metadata_generation.py`)
The enhanced “generate_windows” script enumerates every DEF/GDS pair under `designs/` and emits size-specific manifests and PNG previews.
```bash
python scripts/window_metadata_generation.py \
  --windows-per-design 120 \
  --seed 2024 \
  --output datasets
```
* Produces `datasets/<tech>/<size>/windows.yaml` plus overview plots (`scripts/*.png`).
* Each YAML file stores snapped coordinates, layer stack references, and metadata consumed by `window_processing_pipeline.py`.

### 3. CAP3D window and dataset generation (`window_tools/window_processing_pipeline.py`)
This replaces the legacy `window_tools/generate_windows.py` entry point; the logic now lives in `window_processing_pipeline.py`. Given a `windows.yaml`, the script slices CAP3D windows and (optionally) generates density maps, graphs, and point clouds in one pass.
```bash
python window_tools/window_processing_pipeline.py \
  --windows-file datasets/nangate45/small/windows.yaml \
  --dataset-path datasets/nangate45/small \
  --pipeline cap3d cnn gnn pct
```
* Requires KLayout inside the `cap3d-ml` environment (invoked via `pya`).
* Outputs land under `cap3d/`, `def/`, `gds/`, `density_maps/`, `graphs/`, and `point_clouds/`, with manifests updated in `datasets/manifests/`.
* Use `--pipeline gnn` (etc.) to rerun just one converter on existing CAP3D files.

### 4. Label windows with RWCap (`scripts/run_rwcap.py`)
1. Obtain the official RWCap binaries from your EDA vendor install and export the location:
   ```bash
   export RWCAP_BIN=/eda/rwcap/bin/rwcap
   ```
2. Run the batch script to process every CAP3D file that lacks an RWCap report:
   ```bash
   python scripts/run_rwcap.py \
     --datasets-root datasets \
     --process-nodes nangate45 \
     --sizes small,medium \
     --jobs 8
   ```
3. RWCap logs land under `datasets/<tech>/<size>/log_rwcap/`, raw `.out` files under `out_rwcap/`. The script skips anything that already has an output, so reruns are cheap.

### 5. Convert RWCap/Raphael outputs to SPEF and compare solvers
1. Convert solver outputs into the standardized SPEF labels used by every model:
   ```bash
   python spef_tools/rwcap_to_spef.py \
     datasets/nangate45/small/out_rwcap \
     datasets/nangate45/small/labels_rwcap

   python spef_tools/raphael_to_spef.py \
     datasets/nangate45/small/out_raphael \
     datasets/nangate45/small/labels_raphael
   ```
2. Once multiple label sources exist, quantify deltas with the comparison tool:
   ```bash
   python scripts/capacitance_comparison.py \
     --type all \
     --tech nangate45 \
     --tools rwcap_openrcx
   ```
   The script parses the SPEFs for self and coupling capacitance, aligns common nets, and prints error statistics per technology/size bucket.
3. `spef_tools/openrcx_to_simple_spef.py` performs the same normalization for OpenRCX output if you need to ingest external decks.

### 6. Run OpenRCX on the windows (`scripts/run_openrcx.py`)
`run_openrcx.py` discovers DEF windows under `datasets/` and launches OpenROAD/OpenRCX to generate SPEF ground truth.
```bash
export OPENROAD_LAUNCH_SCRIPT=$(pwd)/scripts/_openrcx_launcher.sh
python scripts/run_openrcx.py \
  --datasets-root datasets \
  --process-nodes nangate45 \
  --sizes small \
  --rcx-script openrcx/nangate45/setRC.tcl \
  --jobs 4
```
* The first invocation auto-generates `scripts/_openrcx_launcher.sh`, which calls `openroad` unless you override it via `OPENROAD_BIN` or wrap it in Docker (`--use-docker`).
* Results go to `datasets/<tech>/<size>/out_openrcx/` and can be compared with RWCap/Raphael using the same SPEF utilities above.
* Per-node collateral (LEFs, RC tech files, TCL decks) lives in `openrcx/<tech>/`. Adjust those files if you sweep corners or experiment with new nodes.

---

With the environment prepared, datasets restored from Zenodo, and the reference flows documented above, you can reproduce every experiment from the paper as well as extend the benchmark with new layouts, solvers, or ML models.
