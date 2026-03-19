# Dataset Workspace
This directory is the default local workspace root for datasets materialized from the CapBench cache. Running `capbench datasets install <dataset> --materialize` will place symlinks or local dataset directories under this tree.

## Expected Structure
Each dataset bucket exposes consistent subdirectories such as `gds`, `def`, `cap3d`, `density_maps`, `binary-masks`, `point_clouds`, and solver label directories so geometry, derived features, and metadata remain aligned per window.

## Notes
Versioned example data and historical datasets have been moved under `reference/` so this directory can remain focused on active workspaces and materialized cache content.

> **Warning:** Full uncompressed datasets occupy dozens of gigabytes; ensure you have adequate local disk space before materializing or copying them.
