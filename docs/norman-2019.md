# Norman 2019 dataset contract

CellForge's first end-to-end dataset is the Norman et al. 2019 CRISPRa
Perturb-seq experiment, GEO accession `GSE133344`, DOI
`10.1126/science.aax4438`. The maintained `pertpy` dataset loader is the
acquisition path; CellForge runs should persist the resulting `.h5ad` and its
SHA-256 before analysis.

The experiment contains single-gene and combinatorial overexpression
perturbations in K562 cells. Combination labels such as `GENE1+GENE2` remain
explicit and are not silently treated as single-target interventions.

The adapter normalizes `perturbation_name`/`guide_identity` into
`target_genes`, creates `is_control` and `assignment_class`, supplies a
`context` column when the source has no explicit context, and records the
dataset accession and source DOI in `AnnData.uns`.

Norman supports an unseen-perturbation split. The current source contract does
not justify unseen-donor, unseen-cell-type, or unseen-context claims. Those
conditions must be introduced only with a dataset that carries the relevant
metadata and coverage.

Useful source paths:

- `pertpy.data.norman_2019()` for maintained acquisition;
- GEO `GSE133344` for source provenance;
- `cellforge.datasets.load_norman_2019(path)` for a pinned local artifact.

The first workflow should run on a small persisted Norman subset in CI and on
the full artifact only in an explicitly configured local/Colab run.
