# Phase 1 dataset candidate

Phase 1 needs one public perturbation dataset with enough metadata for a defensible first benchmark. The current candidate is **GSE314342**, a primary human CD4+ T-cell Perturb-seq study described as a genome-scale CRISPR interference screen spanning approximately 22 million cells from four donors across resting and stimulated conditions.

This is a candidate, not a selected or downloaded dataset. Adoption requires verification of the source record, downloadable matrix, access terms, perturbation and control annotations, gene identifiers, donor coverage, cell-state/context metadata, and guide-level replication. Confounding between perturbation, donor, stimulation, batch, and sequencing run must be documented.

## Cellxgene role

Cellxgene Discover can provide targeted collection/dataset discovery and an AnnData retrieval path when the candidate is published there. A future adapter should persist the collection or dataset identifier, source URL, release or snapshot, retrieval timestamp, and local artifact fingerprint. It must then validate dimensions, stable identifiers, perturbation fields, controls, donors, cell types, and contexts.

Cellxgene metadata does not prove that a dataset supports every OOD split. The observations must establish whether unseen perturbation, donor, cell type, or context holdouts are identifiable and represented. If the candidate is not available through Cellxgene, the same provenance and validation contract applies to its primary archive source.

## Evo 2 boundary

Evo 2 models DNA sequence. It is not a direct predictor of post-perturbation single-cell expression. It may be considered later for a separately defined sequence-informed task only if the dataset supplies a defensible mapping from genomic sequence to the cellular question.

Any future Evo adapter must declare sequence provenance, genome build, perturbation-to-sequence mapping, model version, checkpoint, and the assumptions connecting genomic scores to cellular response. It must still use appropriate baselines and compatible biological splits. Phase 1 will not download, run, or benchmark Evo 2.

## Adoption decision

The dataset is adopted only after a validation report confirms provenance and annotations, documents missing metadata and confounding, defines the expression target and controls, and records which OOD conditions are supportable. Until then, GSE314342 remains a documented candidate.
