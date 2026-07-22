# Baseline validation results

These are single-seed validation measurements from the maintained recipes and
closely matched precursor configurations. They are approximate reproductions, not
claims that the original private implementation or every unpublished paper choice
has been recovered.

All runs used seed 42, an exact 80/20 window split, MSRE training, fixed Adam at
`1e-4`, and 50 epochs. CNN and PCT used zero weight decay. “Best” is the lowest
validation MAPE across the run; “final” is the epoch-50 value.

| PDK | Model | Paper MAPE | Best MAPE | Final MAPE |
| --- | --- | ---: | ---: | ---: |
| Nangate45 | standardized residual GCN | 21.40 | 19.922 | 20.207 |
| Nangate45 | residual GAT | 18.00 | 14.700 | 15.743 |
| Nangate45 | paper-scale GATv2 | 14.70 | 15.480 | 20.597 |
| Sky130HD | standardized residual GCN | 13.90 | 15.985 | 16.213 |
| Sky130HD | residual GAT | 12.10 | 10.305 | 10.305 |
| Sky130HD | standard GATv2 | 10.20 | 8.899 | 9.151 |
| Nangate45 | ResNet34 | 4.93 | 3.505 | 77.146 |
| Sky130HD | ResNet34 | 1.99 | 1.256 | 1.256 |
| Nangate45 | PCT4 | 9.12 | 7.946 | 7.946 |
| Sky130HD | PCT4 | 7.98 | 6.499 | 6.499 |

Eight of ten best-checkpoint comparisons met or beat the paper target. The two
remaining gaps were Nangate45 GATv2 (+0.78 percentage points) and Sky130HD GCN
(+2.09 points). These differences are small enough for a useful public baseline
but should not be presented as exact reproduction.

The Nangate45 CNN is the clear stability exception: it reached 3.505% and then
degraded to 77.146% at epoch 50. Both checkpoints must be retained and reported.
The Nangate45 GATv2 run also showed late-epoch variance, finishing at 20.597% after
a 15.480% best checkpoint.

## Deliberate implementation choices

- GCN uses inverse-distance edge weights, a learned root residual, and node-feature
  statistics fitted only on training graphs and stored in the checkpoint.
- GAT uses a learned root residual. Five-epoch A/B trials improved both PDKs before
  this change was retained.
- GATv2 keeps the standard non-residual architecture. The maintained 248/256 recipe
  has 167,290 trainable parameters, matching the paper's reported 167.3K scale.
- CNN pins the PDK's small-window layer range so out-of-range geometry cannot alter
  the input channel count.
- PCT uses four self-attention layers, 1,024 sampled points, and stable float64
  sampling probabilities.

The GCN and GAT maintained recipes have more parameters than the paper reports
(99,970 versus 20.9K for GCN; 137,666 versus 84.4K for GAT) because the validated
public widths and retained residuals were not changed simultaneously. That tradeoff
is explicit in each recipe rather than being hidden as an exact architecture match.
