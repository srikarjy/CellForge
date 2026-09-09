# Portfolio and resume points

Use the wording that matches the work you have actually demonstrated. Keep measured results out until experiments produce them.

## Resume bullets

- Designed CellForge, a reproducible benchmarking harness for single-cell CRISPR perturbation models, centered on unseen-perturbation and biological-context generalization rather than random-split leaderboard scores.
- Built a Phase 1 validation path for the public Dixit et al. GSE90063 mouse BMDC Perturb-seq source, checking matrix/index alignment, gene and guide identifiers, control presence, assignment coverage, shared features, and supported OOD dimensions.
- Developed a local artifact sandbox for FASTA, PDB, and mmCIF inspection with interactive 3D structure rendering, deterministic findings, human review decisions, and downloadable review records.
- Implemented content-linked review gates using benchmark run IDs and SHA-256 artifact hashes so approved artifacts can be traced to the exact file and run that produced them.
- Defined a typed, model-independent architecture for dataset validation, perturbation tasks, baseline comparisons, model adapters, biological metrics, provenance, and report generation.
- Established bounded integration policies for Cellxgene, Hugging Face, ARC Evo 2, and NVIDIA PhysicsNeMo, including credential isolation, resource limits, provenance requirements, and human-approval gates.
- Applied repository security review and regression checks covering browser file handling, upload boundaries, network behavior, credential exposure, and review-record integrity.

## Short portfolio description

CellForge is an open scientific software project for evaluating whether virtual-cell and single-cell perturbation models generalize to unseen biology. It links validated CRISPR perturbation data, optional molecular structure inspection, reproducible model runs, biological metrics, artifact provenance, and human review in one auditable workflow.

## Interview explanation

“Benchling helps design and manage CRISPR experiments, and Cellxgene helps discover and explore single-cell data. CellForge addresses the evaluation gap: after a guide or perturbation is defined, it measures what happened in cells, tests whether models transfer to unseen perturbations or contexts, and preserves the evidence needed to review and reproduce the result.”

## Claims to avoid until measured

Do not claim that CellForge improves model accuracy, predicts guide efficacy, validates off-target safety, simulates a whole cell physically, or replaces experimental CRISPR validation. Those require completed experiments and evidence.
