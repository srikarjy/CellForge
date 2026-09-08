# Planned biological metrics

No metrics are implemented and no benchmark values are reported. Choose a complementary suite after the task and dataset are defined; no single metric establishes overall model quality.

All definitions must specify expression scale, gene universe, control matching, cell versus condition aggregation, missing-output treatment, and weighting. Evaluate absolute expression and perturbation-induced changes distinctly: high agreement on constitutively expressed genes can conceal a missed treatment response.

## Pearson / Spearman

Pearson measures linear agreement in expression patterns; Spearman measures agreement in rank order. These can assess whether a model recovers the pattern of a cellular response. Neither alone establishes calibrated response magnitude, and correlations on absolute expression can be dominated by baseline cell identity. Specify the correlation axis and grouping. Constant vectors, too few features, ties, and nonfinite inputs need explicit handling; undefined correlations must not silently become zero or perfect scores.

## MSE / MAE

Mean squared error and mean absolute error measure numerical discrepancies on a declared scale. They help assess magnitude and calibration; MSE emphasizes large errors. Abundant genes, library size, and normalization can dominate them. Averaging over many unchanged genes may reward a model that misses biological responses. Report whether calculations use counts, transformed expression, or changes from controls and ensure predictions and observations share that scale.

## Differential-expression recovery

Compare predicted response genes with an observed differential-expression reference relative to matched controls. Precision asks how many predicted response genes match the reference; recall asks how many reference genes are recovered. This assesses biological response recovery beyond global expression agreement.

Observed DEGs are an assay- and analysis-dependent reference, not perfect ground truth. Specify the differential-expression method, biological replication, effect-size criteria, multiple-testing adjustment, thresholds, and eligible gene set. Predicted condition means alone do not support cell-level significance testing. Define a justified predicted ranking or response rule rather than inventing pseudo-replicates. Held-out reference DEGs are for evaluation only, never feature selection or tuning.

## Top-k DEG overlap

Measure agreement between predicted and reference top-k response-gene sets under a declared ranking, such as absolute response effect. This tests whether the strongest response genes are recovered without relying only on a significance threshold. Specify k, tie handling, overlap denominator, background gene universe, and behavior when fewer than k eligible genes exist. Overlap can miss magnitude and direction errors, and its chance level depends on gene-universe size.

## Direction-of-effect accuracy

Assess whether predicted up/down changes agree with observed effects relative to controls. Correct direction matters when a response would otherwise be interpreted as activation versus repression. Define an evaluation gene set and a neutral-effect threshold to avoid scoring noisy near-zero effects as robust changes. Report eligible counts and treatment of neutral predictions; direction alone does not establish correct magnitude.

## Perturbation ranking

Assess whether predictions order perturbations according to a predefined quantity, such as response magnitude or similarity to a target response. The biological interpretation depends on that ranking target, distance measure, control reference, and eligible candidate set. Declare all of these before inspecting results. Unequal sampling and noisy small effects can destabilize ranks; rank agreement does not prove full expression recovery.

Response magnitude agreement can separately compare norms or another justified summary of predicted and observed changes. Its scale, gene set, and normalization must be explicit.

## OOD performance degradation

Compare each metric between the reference and a supported OOD condition, alongside the raw scores. Define the direction of degradation for higher-is-better metrics versus lower-is-better errors. Relative changes may be undefined or misleading when reference values are near zero or signed, especially for correlations; use an appropriate absolute comparison or report the limitation.

Different OOD cohorts may differ in inherent difficulty and composition. Report perturbation and subgroup coverage so degradation is not automatically attributed to distribution shift. Include variability or uncertainty only when justified by replication and sampling design.

## Reporting and verification

Report per-perturbation and supported donor/cell-type/context breakdowns, eligible sample counts, undefined values, failures, and declared aggregation weights. Use complementary expression, DE, and response-level views rather than a single composite winner. During implementation, test definitions with small known examples covering perfect agreement, reversed effects, constant vectors, empty DEG sets, ties, missing genes, and invalid inputs. No benchmark-logic tests are added in Stage 1.
