# Baseline scope

The publication integration is additive. Existing public CapBench library,
preprocessing, maintenance, reference, and visualization paths remain in place.
Maintained training code lives under `models/`, recipes under `recipes/paper/`, and
generated datasets, logs, and checkpoints remain outside version control.

Included:

- public CNN, PCT, GCN, GAT, and GATv2 training entrypoints;
- registered cache resolution for density maps, point clouds, graphs, and labels;
- exact seeded window splitting, MSRE training, MAPE reporting, and best/latest
  checkpoint preservation;
- CNN/PCT/GNN artifact generation from CAP3D windows;
- strict graph/SPEF label alignment and consistent farad/femtofarad handling;
- executable Nangate45 and Sky130HD recipes and measured result documentation.

Not claimed:

- byte-for-byte recovery of the paper's private implementation;
- multi-seed confidence intervals or validated medium/large/ASAP7 recipes;
- committed datasets, checkpoints, or TensorBoard logs;
- one unified prediction/export API across all model families;
- full multi-hour GPU training in CI.

CI should cover imports, converter schemas, split behavior, objectives, model forward
passes, recipe construction, and small smoke tests. Paper-scale metrics remain a
documented offline validation workload.
