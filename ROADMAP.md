# CellForge roadmap

Implementation phases have completion criteria rather than arbitrary deadlines. **Phase 0 corresponds to the current Stage 1 repository/documentation foundation.** All subsequent phases are planned. No dataset, scientific implementation, or measured benchmark result is included in Stage 1.

## Phase 0 — Repository Foundation

Establish architecture, scope, README, roadmap, benchmark design, reproducibility contract, metric rationale, MIT license, Python 3.10+ package metadata, ignore rules, editor conventions, data policy, and experiment organization. Reserve a small source/test layout without implementation modules.

**Completion:** documentation consistently distinguishes planned work from available functionality; no scientific code, fake results, or executable placeholders are introduced.

## Phase 1 — Dataset Foundation

Select one public perturbation dataset, favoring an immune-cell setting where feasible. Document provenance, release or snapshot, source links, access conditions, assay semantics, and limitations. Load AnnData or an equivalent structure; validate dimensions, expected metadata, perturbation labels, control assignments, and gene identifiers. Inspect donor, cell-type, and context annotations, canonicalize relevant labels, and identify missingness and confounding. Establish deterministic preprocessing with training-fitted transformations clearly separated from fixed operations.

**Completion:** one documented dataset can be ingested repeatably; validation checks detect malformed identifiers, missing required metadata, invalid perturbation/control assignments, and alignment problems. Actual metadata supports a written feasibility assessment for unseen perturbations and additional OOD settings. No donor or context capabilities are assumed from dataset branding.

## Phase 2 — Reproducible Split Engine

Implement a standard reference and unseen-perturbation train/validation/test split. Add at least one additional unseen-donor, unseen-cell-type, or unseen-context split if genuinely supported. If none is defensible, document the limitation and revisit dataset/scope before claiming broader OOD coverage.

Preserve deterministic seeds, exact membership manifests, sample and perturbation counts, relevant metadata distributions, overlap checks, and leakage checks. Define intervention grouping, validation holdouts, and the permitted control policy. Ensure learned preprocessing respects split boundaries.

**Completion:** the same dataset version and configuration reconstruct exact split membership; automated checks establish the declared holdouts and expose unsupported or confounded conditions.

## Phase 3 — Strong Baselines

Implement appropriate control-state/mean-response, linear, or nearest-neighbor methods; add a simple neural baseline only with a clear reason. Define how each handles perturbations absent from training and what biological information it receives. Tune fairly on validation data and prohibit held-out target access.

Use a shared prediction/evaluation contract that advanced models will also follow. Initial verification can use small known examples; the standardized biological suite is developed in Phase 6, before benchmark claims.

**Completion:** meaningful baselines produce aligned predictions for the supported task and splits, have documented information access, and can be evaluated through the same contract as advanced models. No weak straw-man comparison is accepted.

## Phase 4 — Model Adapter Interface

Define a small common interface around preparation, fit/load, prediction, and metadata. Normalize gene and condition identifiers, expression scale, and output shape. Capture adapter/model versions, checkpoints, external information, and fitting/inference settings. Determine exact API signatures from real baseline and first-model requirements.

**Completion:** a documented contract supports current methods, detects incompatible outputs, and isolates model dependencies without speculative abstraction.

## Phase 5 — First Advanced Model

Assess candidate task compatibility and integrate one appropriate perturbation-response model. Use identical dataset versions, splits, standardized result conventions, and equivalent evaluation criteria. Document model-specific input transformations, pretrained resources, tuning, and compute requirements. Validate output alignment, finiteness, scales, and coverage carefully.

**Completion:** one compatible model produces valid predictions beside baselines under the same evaluation contract, with known limitations and reproducible fitting/loading instructions. Integration alone establishes no performance advantage.

## Phase 6 — Biological Metrics

Implement the standardized suite: Pearson/Spearman, MAE/MSE where meaningful, differential-expression recovery, top-k DEG overlap, direction-of-effect accuracy, response magnitude agreement, and perturbation ranking as justified by the task. Document mathematical definitions, scales, controls, aggregation, thresholds, and undefined cases.

**Completion:** metrics pass small known-example tests, including constant vectors, empty response sets, ties, and mismatched identifiers; the same evaluator consumes baseline and advanced-model predictions and reports per-condition coverage.

## Phase 7 — Benchmark Runner

Build a straightforward local execution layer combining dataset, task, split, model, resolved configuration, seed, and metrics. Add typed configuration and real Typer commands only for implemented operations. Produce predictions, metrics, a basic run manifest, logs, and artifacts; preserve environment and source revision. Record failures and avoid overwriting completed runs.

**Completion:** one documented local invocation produces traceable artifacts, and its metrics can be recomputed from preserved predictions. No microservices, Kubernetes, distributed orchestration, or message queues are needed.

## Phase 8 — Generalization Benchmark

Run strong simple baselines versus the first advanced perturbation model across standard evaluation, unseen perturbations, and an additional supported OOD condition. Break results down by perturbation and meaningful biological subgroups. Report eligible counts, variability, failures, and uncertainty where justified.

**Completion:** a rerunnable comparison supports bounded conclusions about the tested dataset and shifts. Unsupported OOD conditions are explicitly omitted with justification. Null results, negative findings, and baseline wins are valid; the objective is not to prove the advanced model wins.

## Phase 9 — Additional Model Families

Only after the core benchmark works reliably, assess further GEARS, scGPT, Geneformer, STATE, or other appropriate integrations. Require task compatibility and a justified prediction mechanism, not resume keyword coverage. Preserve a common evaluation contract and document unequal pretraining or external information access.

**Completion:** each added model has validated predictions, versioned metadata, reproducible execution, and a scientifically defensible comparison to existing baselines.

## Phase 10 — Reproducibility + Artifact System

Harden the basic provenance required in Phase 7: immutable run manifests, dataset/split/preprocessing fingerprints, model/checkpoint identifiers, environment capture, machine-readable results, comparable experiment directories, and deterministic cached preprocessing. Cache identity must incorporate data, configuration, relevant split membership, fitted transformations, and software versions.

**Completion:** an experiment can be rerun without guessing hidden settings; stale or mismatched caches are detected, artifact integrity is checked, and derived metrics can be reconstructed. This phase strengthens existing run tracking rather than deferring provenance until after comparisons.

## Phase 11 — Benchmark Reports

Generate benchmark tables, model comparisons, performance by perturbation, OOD degradation plots, DEG-recovery analyses, model-versus-baseline views, and failure-case summaries. Include methodological limitations and reproducibility metadata. Prefer static HTML, Markdown, and publication-style figures over an unnecessary frontend application.

**Completion:** reports consume persisted machine-readable results, link back to runs, and expose subgroup failures and exclusions as well as aggregate performance.

## Phase 12 — Portfolio / Research Release

Prepare reproducible commands, benchmark methodology, architecture diagram, actual measured results, dataset provenance, limitations, failure cases, comparison tables, scientific interpretation, and rerun instructions. Review whether documented claims follow from the evaluation design.

**Completion:** a reader can trace every reported number to an actual run and reproduce the comparison using documented artifacts and settings. Only now should measured results become prominent in the README. Never invent metrics, dataset sizes, runtimes, or speedups.

## Principles across phases

Benchmark before scaling. Prioritize generalization over leaderboard chasing, require strong baselines, use complementary biological metrics, and preserve the evidence needed to reconstruct published results. Avoid unrelated backend/cloud infrastructure and LLM-agent architecture. CellForge remains evaluation infrastructure for perturbation models, not a new foundation model or autonomous research system.
