# CRISPR exploration scope

CellForge may include a bounded CRISPR exploration workflow alongside its perturbation benchmark. The workflow connects an observed guide assignment to its target, sequence context, optional Cas9/guide RNA/target DNA structure, measured cellular response, and a human review record.

## Included workflow

```text
target gene
    → guide selection
    → guide/PAM/cut-site mapping
    → optional PDB/mmCIF complex view
    → observed perturbation response
    → deterministic checks
    → human review linked to run and artifact hashes
```

The first implementation should use guides and target labels already present in the validated GSE90063 source. It must distinguish single-target, multi-target, non-targeting-control, and unassigned cells. Structure files are optional evidence artifacts; a structure does not prove guide efficacy or cellular response.

## 3D structure contract

The viewer may color and toggle Cas protein, guide RNA, target DNA, PAM, and predicted cut-site annotations when those entities are represented and mapped with evidence. The mapping must preserve structure accession, chain or residue identifiers, sequence coordinates, genome/build information where relevant, and the method used to derive annotations. Missing or ambiguous mappings become review findings.

## Review contract

A review links the exploration to a `run_id`, an exact artifact SHA-256, reviewer identity, decision, comments, checker version, and timestamp. Approved artifacts may enter a report only when the run ID and hash match. Pending, rejected, or needs-revision records remain blocked from final reporting.

## Explicit exclusions

This scope does not include autonomous guide design, free-form biological advice, clinical recommendations, or claims that a visual structure predicts editing efficiency. A future sequence model or physics-informed analysis may contribute bounded evidence, but its assumptions and outputs must remain separate from measured single-cell response metrics and pass human review.
