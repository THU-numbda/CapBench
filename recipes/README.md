# Training recipes

`paper/` contains the maintained, single-seed baseline configurations used to
approximate Table 6 of the CapBench paper. They deliberately pin the 80/20
window split, MSRE objective, fixed Adam learning rate, 50 epochs, data
representation, and model dimensions. Measured results and any deviations from
the paper are recorded in `docs/baseline-results.md`.

Run a recipe from the repository root:

```bash
python scripts/run_training_recipe.py \
  recipes/paper/nangate45/gnn-gatv2.yaml --gpu 5
```

Inspect a command or make a controlled override without editing the recipe:

```bash
python scripts/run_training_recipe.py \
  recipes/paper/sky130hd/pct4.yaml --gpu 5 --dry-run \
  --set epochs=5 --set output-dir=diagnostics/pct-smoke
```

Dataset ids resolve through the shared CapBench cache. Use `--set dataset-path=...`
for an explicit dataset directory. Recipe results are validation measurements, not
claims of exact paper reproduction; hardware, generated artifacts, library
versions, and the paper's unpublished implementation details can differ.

Summarize one or more completed TensorBoard runs with the same best/final
convention used in `docs/baseline-results.md`:

```bash
python scripts/summarize_training_events.py logs/my-run another/output/tensorboard
```
