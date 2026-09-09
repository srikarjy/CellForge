# Phase 1 dataset candidate

Phase 1 needs one public perturbation dataset with enough metadata for a defensible first benchmark. The repository's current dataset is **GSE90063 (Dixit et al., 2016)**, a pooled Perturb-seq study of mouse bone-marrow-derived dendritic cells (BMDCs) with unstimulated and LPS-stimulated contexts.

This is a candidate, not a selected or downloaded dataset. Adoption requires verification of the source record, downloadable matrix, access terms, perturbation and control annotations, gene identifiers, donor coverage, cell-state/context metadata, and guide-level replication. Confounding between perturbation, donor, stimulation, batch, and sequencing run must be documented.

## Cellxgene role

Cellxgene Discover can provide targeted collection/dataset discovery and an AnnData retrieval path if this study is published there. The current source implementation uses the GEO supplementary files directly. A future Cellxgene path should persist the collection or dataset identifier, source URL, release or snapshot, retrieval timestamp, and local artifact fingerprint. It must then validate dimensions, stable identifiers, perturbation fields, controls, donors, cell types, and contexts.

Cellxgene metadata does not prove that a dataset supports every OOD split. For GSE90063, the available contexts support an unstimulated-to-LPS context comparison and unseen-perturbation evaluation. Donor and cell-type holdouts are not supported by the current BMDC source metadata and must not be claimed.

## Evo 2 boundary

Evo 2 models DNA sequence. It is not a direct predictor of post-perturbation single-cell expression. It may be considered later for a separately defined sequence-informed task only if the dataset supplies a defensible mapping from genomic sequence to the cellular question.

Any future Evo adapter must declare sequence provenance, genome build, perturbation-to-sequence mapping, model version, checkpoint, and the assumptions connecting genomic scores to cellular response. It must still use appropriate baselines and compatible biological splits. Phase 1 will not download, run, or benchmark Evo 2.

## Adoption decision

The dataset is considered adopted for the current foundation once its downloaded GEO files pass structural validation. The implementation records matrix/index alignment, gene and guide formats, controls, assignment coverage, shared perturbations, and supported OOD dimensions in a `ValidationReport`. Biological limitations remain documented, including the absence of donor and cell-type holdouts.

## Current validation snapshot

The downloaded source currently passes structural validation. The report records 33,063 cells and 17,515 genes for the unstimulated condition, and 32,777 cells and 17,775 genes for the LPS condition. Both contexts contain 24 target genes and share 16,564 expression features.

Validation also reports assignment barcodes that are absent from the corresponding expression matrix: 10 in the unstimulated source and 3,078 in the LPS source. These are warnings rather than proof of invalid expression data, but the benchmark must document how such assignments are handled and must not silently treat them as evaluated cells.
