# Benchmark design

This document defines planned scientific safeguards, not completed experiments. No public dataset has yet been selected.

## Research question

Do sophisticated virtual-cell and perturbation-response models generalize better than strong simple baselines to unseen perturbations and biological contexts?

Start with one public dataset, one task, mandatory baselines, and one compatible advanced model. Prefer an immune-cell setting. Dataset provenance and actual metadata determine which OOD claims are possible.

## Evaluation units

- **Cells:** measured observations; cells from the same donor or experimental replicate are not automatically independent biological replicates.
- **Perturbations:** interventions, including declared genetic targets or chemical treatments and relevant doses/combinations.
- **Genes:** aligned response features with documented identifiers and selection rules.
- **Donors:** individuals, only where reliable donor annotations exist.
- **Cell types:** annotated cellular identities with a documented annotation source.
- **Biological contexts:** explicitly defined combinations of variables such as cell type, treatment timing, or experimental setting.

Define whether predictions represent individual cells, response distributions, or condition-level expression before evaluation. Do not assume unpaired single-cell assays provide matched before/after trajectories. Specify aggregation and control matching accordingly.

## Independent and dependent variables

Independent variables include model, split condition, perturbation, and supported biological context. Seeds and tuning budgets are design factors that should be recorded. Dependent variables are complementary expression, differential-expression, perturbation-level, and generalization metrics. Avoid selecting a favorable metric after inspecting test performance.

## Controls

Biological controls establish the reference state for measuring perturbation effects. Validate control labels and matching by donor, cell type, batch, or other relevant covariates; unmatched controls can confound treatment effects. Define in advance whether inference can access controls from a held-out context and label this setting clearly.

Computational baselines test whether advanced models improve on simple predictions. Include appropriate control/mean and stronger trainable methods where justified. A training-derived response mean must never include held-out treatment outcomes. Apply the same control policy and evaluation criteria to all participants.

## Generalization conditions

A standard seen-context reference provides a comparison point, with its overlap explicitly documented. An unseen-perturbation test excludes test perturbations from training and tuning; validation needs a separate holdout consistent with that question. Define whether a held-out combination contains previously seen individual targets, since this differs from unseen-target prediction.

Unseen-donor evaluation excludes held-out donor outcomes from fitting and tuning. Unseen-cell-type or context evaluation holds out the named biological unit. Cross-tabulate metadata to check that shifts are not inseparable from batch or perturbation availability. If independent conditions lack coverage or replication, narrow the claim or defer the split. Additional OOD support is contingent on genuine dataset capabilities.

## Leakage risks

- **Perturbation overlap:** aliases, multiple guides, doses, or combinations can disguise related interventions across splits. Define grouping rules explicitly.
- **Donor leakage:** related samples from an individual must respect the donor holdout boundary.
- **Cell-state overlap:** near-duplicate observations and shared experimental samples may inflate cell-level holdout performance.
- **Preprocessing leakage:** gene selection, embeddings, imputation, feature scaling, and other learned transformations must not use test outcomes.
- **Normalization leakage:** distinguish fixed per-cell transformations from population-fitted quantities; learn the latter only from permitted training inputs.
- **Pretraining exposure:** document known overlap between model pretraining and benchmark sources. Unknown exposure limits claims of complete biological novelty.

Persist membership and overlap checks. Test targets may be used to compute locked evaluation metrics or reference DEGs, never to select models, tune settings, or choose predictive features. Report any admissible target-context inputs separately from held-out outcomes.

## Benchmark fairness

Use identical dataset versions, split membership, task targets, common evaluation gene space, and metric settings. Share preprocessing where scientifically compatible. If a model requires a distinct input representation, document it and map its predictions to the same evaluation scale; do not silently change targets or discard difficult genes.

Give baselines reasonable tuning under a declared budget. Select hyperparameters on validation data. Record pretrained resources, external biological information, compute constraints, missing predictions, and failures. Models using different information access should be distinguished in reports. Task compatibility is required; popularity alone does not justify inclusion.

## Statistical considerations

Report per-perturbation metrics and biological subgroup breakdowns with eligible counts, failures, and missing values. Declare macro versus cell-weighted aggregation so abundant conditions do not silently dominate. Use repeated seeds when stochastic fitting or split sampling warrants them, distinguishing these sources of variation.

Confidence intervals should use defensible independent units such as donors or experimental replicates when available; resampling cells alone does not establish biological replication. Paired model comparisons should use matched evaluation conditions. Record small group sizes and unstable estimates; plan multiplicity handling for inferential comparisons if those are introduced. Do not claim significance or causal generalization unsupported by the design.

Null results, baseline wins, and failure cases are valid outputs. Generalization under defined shifts is the priority, not a single leaderboard average.
