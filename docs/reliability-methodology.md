# CellForge reliability methodology

## Published definition

CellForge's validation uses the method described by Wang, Kuipers, Hugi, Platt,
and Beerenwinkel, *Reliable single-cell perturbations explain and improve model
performance* (bioRxiv, 2026):

1. Treat each perturbation-context pair as one unit.
2. Use the processed expression matrix as supplied; the reference implementation
   assumes log1p(CP10K) data and does not normalize again.
3. For a perturbation with `N_p` cells and `N_c` controls, set
   `n_half = min(floor(N_p/2), floor(N_c/2))`.
4. Repeatedly permute perturbation and control cells independently. Form two
   deltas, each from `n_half` perturbation cells minus `n_half` control cells.
5. Compute Pearson correlation between the two delta vectors. The reported
   reliability is the Spearman–Brown correction of the median repeated
   correlation:

   ```text
   rho = max(0, 2 * median(r) / (1 + median(r)))
   ```

6. A perturbation is reliable when `rho >= 0.5`. For reliable perturbations,
   compute the cosine with the mean response vector across reliable
   perturbations in the same context. The shared variance fraction is
   `phi = cosine**2`; `cosine >= 1/sqrt(2)` (`phi >= 0.5`) is `SHARED`, and
   otherwise the perturbation is `SPECIFIC`.

The primary implementation uses the top 1,000 genes by control-cell mean
expression, selected once per context from controls only. All thresholds and
seeds are explicit. The source paper reports the same thresholds as a 1:1
reproducible-variance criterion and a 1:1 shared-axis variance criterion.

Source: [bioRxiv preprint](https://www.biorxiv.org/content/10.64898/2026.08.11.744177v1),
published implementation: [cbg-ethz/scReliability_paper](https://github.com/cbg-ethz/scReliability_paper).

## Original CellForge implementation

The historical first GEARS run used `similarity_and_signal_v1`:

- input: the supplied `AnnData.X` scale, with no implicit normalization;
- response: perturbation mean minus same-context control mean;
- signal: mean absolute delta across genes;
- noise: square root of the mean per-gene variance across control cells;
- reliability gate: `signal / noise >= 1.5`;
- shared gate: fraction of peer perturbations with cosine similarity `>= 0.8`
  greater than `0.8`;
- minimums: 20 perturbation cells and 20 controls.

This is a transparent heuristic, but it is not the published split-half
reliability estimator. It mixes a pooled effect-size statistic with a control
dispersion statistic and does not estimate repeatability of the perturbation
measurement. It remains available for historical reproducibility and is not
used as evidence that the new validation method is correct.

## Norman representation

The GEARS Norman artifact is sparse `float32` data with values approximately
`0..8.6`, median zero, and a long right tail. It is a processed GEARS matrix,
not raw UMI counts. The validation therefore does not log-normalize it again.
The first run's ten labels were produced by the legacy heuristic and must not
be compared directly to split-half labels as if they were the same quantity.
The derived comparison is in
`docs/experiments/norman-gears-first-run-reliability-reanalysis.md`.

## Differences and limitations

- The reference paper uses curated scPerturBench matrices; this validation uses
  the public GEARS Norman matrix and records that representation explicitly.
- The first CellForge implementation used one pooled delta and is therefore a
  method mismatch, not a failed replication of the paper.
- The current validation uses a top-expression gene mode and does not claim to
  reproduce every paper benchmark metric.
- Shared/specific labels depend on the context-level reliable pool. A context
  with few reliable perturbations should be interpreted cautiously.
- This report is a method validation; it does not retune thresholds using GEARS
  scores, candidate rankings, or held-out labels.
