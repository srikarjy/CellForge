# Norman reliability validation

This is a new validation run. It does not modify the historical first GEARS
result in `norman-gears-first-run.md` or its DecisionPackage.

## Method

The legacy CellForge rule used by the first run computes one pooled mean delta,
divides mean absolute effect by control-cell variance, and applies `SNR >= 1.5`.
That is not the published perturbation-reliability method. The validation uses
the source-aligned split-half implementation described in
[`docs/reliability-methodology.md`](../reliability-methodology.md): 100 seeded
split-half repetitions, top 1,000 control-expressed genes, Spearman–Brown
reliability threshold `rho >= 0.5`, and shared-axis threshold
`cos(theta) >= 1/sqrt(2)`.

No threshold was chosen from GEARS scores, candidate rankings, or held-out
labels.

## Datasets

Both datasets come from the official GEARS Norman `perturb_processed.h5ad`
artifact and are prepared by `scripts/prepare_norman_real.py` with seed 17,
minimum 50 cells per condition, all controls retained, and no model-based
selection.

| run | cells | genes | canonical single-gene perturbations | controls |
|---|---:|---:|---:|---:|
| small validation | 19,977 | 5,045 | 38 | 7,353 |
| larger validation | 55,760 | 5,045 | 105 | 7,353 |

The historical “41 perturbations” refers to source condition labels; after
canonicalizing `GENE+ctrl` and `ctrl+GENE`, the small matrix contains 38 unique
single-gene targets.

## Distribution

| class | small | larger |
|---|---:|---:|
| SPECIFIC | 30 (78.9%) | 76 (72.4%) |
| SHARED | 7 (18.4%) | 27 (25.7%) |
| UNRELIABLE | 1 (2.6%) | 2 (1.9%) |
| INSUFFICIENT_DATA | 0 | 0 |

The source-aligned method therefore does **not** reproduce the first run's
`10/10 UNRELIABLE` result. The discrepancy is methodological: the first run's
legacy pooled SNR rule is not the split-half estimator.

For the ten historical held-out targets, the source-aligned results are:

| perturbation | cells | response magnitude | median split r | rho | shared cosine | class |
|---|---:|---:|---:|---:|---:|---|
| CDKN1B | 145 | 0.0925 | 0.6328 | 0.7751 | 0.7229 | SHARED |
| CEBPA | 322 | 0.4360 | 0.9836 | 0.9917 | 0.5472 | SPECIFIC |
| CNNM4 | 376 | 0.0973 | 0.8464 | 0.9168 | 0.4521 | SPECIFIC |
| FOXF1 | 267 | 0.0540 | 0.4993 | 0.6660 | 0.5663 | SPECIFIC |
| HNF4A | 202 | 0.1487 | 0.8624 | 0.9261 | 0.6971 | SPECIFIC |
| MEIS1 | 682 | 0.0535 | 0.7323 | 0.8455 | 0.6167 | SPECIFIC |
| SAMD1 | 252 | 0.1207 | 0.8330 | 0.9089 | 0.8214 | SHARED |
| ZBTB1 | 287 | 0.1363 | 0.8869 | 0.9401 | 0.6813 | SPECIFIC |
| ZBTB10 | 145 | 0.1845 | 0.8560 | 0.9224 | 0.6711 | SPECIFIC |
| ZBTB25 | 590 | 0.0894 | 0.8846 | 0.9388 | 0.5234 | SPECIFIC |

## Stability

For the 38 targets present in both preparations:

- class agreement: **92.1%**;
- Pearson correlation of reliability statistics: **0.868**;
- class changes: `TGFBR2` unreliable → specific, `IGDCC3` specific → shared,
  and `STIL` specific → shared.

This indicates meaningful but not perfect dependence on sampling depth. The
larger run contains more source targets, so the shared-axis pool also changes;
this is a biological-context effect, not a post-hoc threshold adjustment.

## Bootstrap stability

The bootstrap diagnostic resampled cells within each selected perturbation and
control pool. It estimates stability of the split-half reliability gate only;
the shared-axis class is not assigned from a one-perturbation bootstrap.

| perturbation | repeats | mean rho | rho SD | modal class | stability |
|---|---:|---:|---:|---|---:|
| CEBPA | 30 | 0.9918 | 0.0003 | SPECIFIC gate | 100% |
| SAMD1 | 30 | 0.9121 | 0.0061 | SPECIFIC gate | 100% |
| FOXF1 | 30 | 0.7147 | 0.0305 | SPECIFIC gate | 100% |
| CDKN1B | 30 | 0.7956 | 0.0280 | SPECIFIC gate | 100% |

“SPECIFIC gate” here means `rho >= 0.5` before the context-level shared-axis
test. It is deliberately not presented as a probability of biological truth.

## Preprocessing sensitivity

The GEARS matrix is sparse float32 processed data with values approximately
`0..8.6`, median zero, and a long right tail. The validation treats it as
already processed, matching the published method's log1p-CP10K contract, and
does not apply a second log normalization. The small and larger preparations
use the same representation and show the sample-size sensitivity above.

The legacy SNR rule is representation-sensitive because its numerator and
denominator are calculated directly on `AnnData.X`. That is a limitation of the
legacy rule, not evidence against split-half reliability.

## Known biological programs

The downloaded GEARS Norman artifact does not include a machine-readable set of
published program labels or a canonical per-target annotation table. This run
therefore does not claim an external program-label validation. CEBPA is a useful
qualitative sanity check because it has a large measured response and receives
high split-half reliability, but that observation is not treated as a formal
ground-truth label.

## Conclusion

**VALID WITH LIMITATIONS.** The split-half method is scientifically grounded and
stable enough to replace the legacy SNR heuristic for future Norman analyses:
it gives interpretable reliability values, is stable for the selected bootstrap
diagnostics, and agrees across sample sizes for 92.1% of shared canonical
targets. The historical `UNRELIABLE` labels were artifacts of a mismatched
heuristic, not a defensible replication of the published method.

The remaining limitations are the single processed representation, the
context-level shared-axis dependence, lack of formal program labels in the
artifact, and the fact that the larger run was prepared for reliability
validation rather than a new GEARS benchmark.

## Artifacts

The generated validation artifacts are intentionally outside Git at:

```text
/tmp/cellforge-gears-data/norman-reliability-validation/
```

They include small/large record tables, sample-size comparison, bootstrap
diagnostics, control-noise distribution, PNG diagnostics, and `summary.json`.
