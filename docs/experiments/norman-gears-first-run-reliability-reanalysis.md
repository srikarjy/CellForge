# Norman GEARS first-run reliability reanalysis

This is a derived analysis of the immutable first real GEARS run. It does not
modify `norman-gears-first-run.md`, the original artifacts, or the original
DecisionPackage hash.

Historical artifact:

```text
/tmp/cellforge-gears-data/norman-gears-first-run-v4/
DecisionPackage SHA: 33239317eb45065a8bb641ef54a68b6ed37ea7f897966a0217c71f53ea77eff2
```

## Method

The original GEARS predictions and baseline metrics are reused exactly. Only
the reliability and derived model-trust interpretation are recomputed using
`published_split_half_spearman_brown_v1` with 100 repetitions, 1,000
control-expressed genes, `rho >= 0.5`, and `cos(theta) >= 1/sqrt(2)`.

## Comparison

| target | old class | new class | rho | shared cosine | GEARS | ridge | train mean | old trust | new trust |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| CDKN1B | UNRELIABLE | SHARED | 0.7751 | 0.7229 | 0.3530 | 0.7423 | 0.7116 | LIMITED | LIMITED |
| CEBPA | UNRELIABLE | SPECIFIC | 0.9917 | 0.5472 | 0.4661 | 0.4185 | 0.4125 | LIMITED | TRUSTED |
| CNNM4 | UNRELIABLE | SPECIFIC | 0.9168 | 0.4521 | 0.1016 | 0.4350 | 0.4291 | LIMITED | LIMITED |
| FOXF1 | UNRELIABLE | SPECIFIC | 0.6660 | 0.5663 | 0.0481 | 0.5087 | 0.5105 | LIMITED | LIMITED |
| HNF4A | UNRELIABLE | SPECIFIC | 0.9261 | 0.6971 | 0.2173 | 0.6516 | 0.6412 | LIMITED | LIMITED |
| MEIS1 | UNRELIABLE | SPECIFIC | 0.8455 | 0.6167 | 0.4751 | 0.6145 | 0.6205 | LIMITED | LIMITED |
| SAMD1 | UNRELIABLE | SHARED | 0.9089 | 0.8214 | 0.5157 | 0.7672 | 0.8138 | LIMITED | LIMITED |
| ZBTB1 | UNRELIABLE | SPECIFIC | 0.9401 | 0.6813 | 0.4045 | 0.6973 | 0.6837 | LIMITED | LIMITED |
| ZBTB10 | UNRELIABLE | SPECIFIC | 0.9224 | 0.6711 | 0.2543 | 0.5686 | 0.6032 | LIMITED | LIMITED |
| ZBTB25 | UNRELIABLE | SPECIFIC | 0.9388 | 0.5234 | 0.4503 | 0.6274 | 0.5705 | LIMITED | LIMITED |

## Interpretation

- Reliability changed for all ten targets because the historical heuristic and
  split-half estimator measure different quantities.
- Trust changed for one target: **CEBPA** became `TRUSTED` because it is
  `SPECIFIC` under the validated method and GEARS beats both non-control
  baselines on the matched target.
- CDKN1B and SAMD1 remain limited because their responses are classified as
  `SHARED`, even though their measured/model scores are nontrivial.
- The other seven targets remain limited because GEARS loses to ridge or the
  training-mean baseline.

The derived result is evidence that reliability should condition trust, not
simply suppress all candidates under a mismatched SNR heuristic. It does not
prove GEARS is generally trustworthy: this is a ten-target CPU verification
run, and the model still loses to simple baselines overall.

The comparison table is committed at
`docs/experiments/data/norman-gears-reliability-reanalysis.csv` (transcribed
from the table above, 4-decimal precision; it omits the per-target trust reason
and median split correlation). The full-precision outputs of
`scripts/reanalyze_norman_gears_reliability.py` were written to
`/tmp/cellforge-gears-data/norman-gears-reliability-reanalysis/`, which is not
preserved; rerun the script against the original dataset and historical
artifact to regenerate them.
