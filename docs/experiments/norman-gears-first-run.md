# Norman GEARS first run

## Experiment

- Dataset: official GEARS Norman `perturb_processed.h5ad`, Norman et al. 2019 / GSE133344.
- Prepared data: 19,977 cells, 5,045 genes, 7,353 controls, 41 single-target perturbations.
- Selection: conditions with exactly one non-control target (`GENE+ctrl` or `ctrl+GENE`), minimum 50 cells, seeded perturbation sampling (seed 17), 20,000-cell budget. No model metric was used for selection.
- Split: CellForge `unseen_perturbation`, seed 17; 22 train, 6 validation, 10 test perturbations.
- Model: GEARS / `cell-gears==0.1.2`, CPU, one epoch, hidden size 16, batch size 64.
- Environment: Python 3.12.2, PyTorch 2.4.1 CPU, torch-geometric 2.8.0.post1, Scanpy 1.11.5, AnnData 0.12.19, NumPy 1.26.4, pandas 2.1.4.
- Training plus inference wall time: approximately 100.2 seconds on the local CPU environment (including checkpoint persistence).

The real experiment artifact is outside Git at `/tmp/cellforge-gears-data/norman-gears-first-run-v4/` and includes manifests, metrics, prediction/observed-delta Parquet tables, figures, contradictions, prioritization, a hashed GEARS checkpoint, and a DecisionPackage. External evidence is explicitly fixture-only.

## Results

| Model | Mean Pearson on expression delta | Mean delta MSE |
|---|---:|---:|
| GEARS | 0.3286 | 0.00650 |
| Training-mean baseline | 0.5997 | 0.00536 |
| Embedding ridge baseline | 0.6031 | 0.00538 |
| Control mean | undefined Pearson (constant no-change prediction) | 0.00664 |

GEARS did not beat either non-trivial baseline on this run. The control Pearson is undefined by construction; CellForge treats it as a non-informative comparison rather than inventing a correlation.

Per-test GEARS Pearson scores were:

| Perturbation | GEARS | Ridge | Training mean | Trust |
|---|---:|---:|---:|---|
| CDKN1B | 0.3530 | 0.7423 | 0.7116 | LIMITED |
| CEBPA | 0.4661 | 0.4185 | 0.4125 | LIMITED |
| CNNM4 | 0.1016 | 0.4350 | 0.4291 | LIMITED |
| FOXF1 | 0.0481 | 0.5087 | 0.5105 | LIMITED |
| HNF4A | 0.2173 | 0.6516 | 0.6412 | LIMITED |
| MEIS1 | 0.4751 | 0.6145 | 0.6205 | LIMITED |
| SAMD1 | 0.5157 | 0.7672 | 0.8138 | LIMITED |
| ZBTB1 | 0.4045 | 0.6973 | 0.6837 | LIMITED |
| ZBTB10 | 0.2543 | 0.5686 | 0.6032 | LIMITED |
| ZBTB25 | 0.4503 | 0.6274 | 0.5705 | LIMITED |

## Trust and reliability

All ten held-out perturbations were classified `UNRELIABLE` by the current configured signal-to-control-noise rule. Consequently, all ten GEARS model-trust records were `LIMITED`; none were `TRUSTED`.

This is a scientifically important result, not a reason to hide the reliability layer. The current run uses the processed GEARS matrix and the existing reliability thresholds without post-hoc tuning. A follow-up should determine whether the threshold is inappropriate for this normalized data scale or whether the held-out responses are genuinely weak.

## Important wins and failures

GEARS was closest to the simple baselines on CEBPA and exceeded both non-control baselines there, but this did not produce trusted evidence because measurement reliability was `UNRELIABLE`. SAMD1 had the highest GEARS score (0.5157) but remained below ridge (0.7672). FOXF1 was the largest relative failure; GEARS was below ridge on 9 of 10 held-out perturbations.

The failure-analysis figure and model-reality figure are generated from the real records. The trust map shows real response magnitudes, cell counts, and reliability classes.

## Prioritization

Adding GEARS evidence changed the trust-aware ordering relative to a ranking with `UNKNOWN` model trust: the top three remained CEBPA, ZBTB10, and HNF4A, while ZBTB1 moved upward and SAMD1 moved downward. No candidate was promoted to trusted evidence.

## Scientific interpretation

This run supports the CellForge trust-layer thesis more strongly than a showcase result would: on this subset and one-epoch CPU configuration, GEARS did not add predictive value beyond simple baselines, and no model output deserved `TRUSTED` status because the measured responses were unreliable under the declared rule.

## Limitations

- This is a one-epoch CPU run intended to verify the full scientific/software path, not a tuned GEARS benchmark.
- Only single-target perturbations were evaluated; Norman combinations are deferred.
- The control baseline has undefined Pearson correlation and is compared using MSE plus explicit non-informative status.
- No live Open Targets, DepMap, Reactome, or literature retrieval was used.
- The reliability threshold was not recalibrated after inspecting results.
- Predictions are represented in the GEARS metrics/trust artifacts; a future artifact revision should additionally persist full gene-by-perturbation prediction matrices.
