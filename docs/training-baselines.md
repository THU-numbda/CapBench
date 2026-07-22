# Training the CNN, PCT, and GNN baselines

The maintained recipes cover the paper's Nangate45 and Sky130HD small-window
total-capacitance experiments. They use a deterministic 80/20 split by window,
MSRE optimization, fixed Adam at `1e-4`, 50 epochs, and seed 42. MAPE is the
reported comparison metric.

## Install

Use a CUDA-compatible PyTorch environment, then install the baseline extras from
the repository root:

```bash
python -m pip install -e ".[baselines]"
python -c "import torch, torch_geometric, pytorch_lightning; print(torch.cuda.is_available())"
```

PyTorch and PyTorch Geometric wheel selection depends on the local CUDA runtime.
If your platform needs a vendor-specific wheel index, install those packages first
and then run the editable install.

## Install and inspect data

```bash
python -m capbench datasets install nangate45
python -m capbench datasets install sky130hd
python -m capbench datasets info nangate45/small
python -m capbench datasets info sky130hd/small
```

Each trainer accepts either a registered id such as `nangate45/small` or an
explicit dataset directory. A training-ready split contains the relevant generated
representation plus SPEF labels:

```text
<dataset>/
  windows.yaml
  cap3d/
  labels_rwcap/        # or labels_raphael/
  density_maps/       # CNN shard index and shards
  point_clouds/       # PCT .npz files
  graphs/             # GNN .pt files
```

Downloaded archives may omit one or more generated representations. To create
missing CNN, PCT, and GNN artifacts from existing CAP3D windows, first print the
cached workspace path:

```bash
python -m capbench datasets info nangate45/small
```

Then run the converter pipeline with that absolute path:

```bash
python -m tools.preprocess.window_processing_pipeline \
  --windows-file /absolute/cache/path/nangate45/small/windows.yaml \
  --dataset-path /absolute/cache/path/nangate45/small \
  --pipeline cnn pct gnn
```

The pipeline skips complete PCT/GNN outputs. CNN density shards are written
atomically; an existing complete bundle is reused, while a partial or unrelated
bundle is rejected rather than overwritten. Generate into a fresh dataset path if
you need a second representation.

## Run a checked-in recipe

Inspect the exact command without starting training:

```bash
python scripts/run_training_recipe.py \
  recipes/paper/nangate45/gnn-gatv2.yaml --gpu 0 --dry-run
```

Run it on one physical GPU:

```bash
python scripts/run_training_recipe.py \
  recipes/paper/nangate45/gnn-gatv2.yaml --gpu 0
```

The runner sets `CUDA_VISIBLE_DEVICES`, so the selected physical GPU is exposed to
the model process as device zero. Use explicit, auditable overrides for smoke tests
or local resource limits:

```bash
python scripts/run_training_recipe.py \
  recipes/paper/sky130hd/pct4.yaml --gpu 0 \
  --set epochs=1 --set max-windows=16 \
  --set output-dir=diagnostics/pct-smoke
```

`--set` keys are the trainer's long-option names without the leading `--`. The
checked-in recipes should remain unchanged when doing local experiments.

## Outputs and checkpoint selection

CNN and PCT write `best_checkpoint.pth`, `latest_checkpoint.pth`, and TensorBoard
events below their configured output directory. The GNN Lightning trainer writes
the lowest-validation-MAPE checkpoint and `last.ckpt`. Always report both best and
final MAPE; the best checkpoint is the paper comparison, while the latest checkpoint
exposes late-epoch instability.

Summarize TensorBoard events with:

```bash
python scripts/summarize_training_events.py diagnostics/my-run/tensorboard logs/my-gnn-run
```

## Maintained scope

The recipes cover ResNet34, four-layer/1,024-point PCT, and two-layer GCN/GAT/GATv2
on the two validated small-window PDK splits. ASAP7, coupling capacitance,
medium/large windows, multi-seed statistics, and a unified inference/export API are
outside the validated scope.
