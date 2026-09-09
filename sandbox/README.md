# CellForge Artifact Sandbox

This is a small browser-based artifact review tool. Open `index.html` locally in a browser, select a FASTA, PDB, or mmCIF file, and review the deterministic findings. PDB/mmCIF files are rendered with the 3Dmol.js browser library loaded from its public CDN. Compressed files are not currently supported by the browser UI.

The sandbox supports:

- FASTA alphabet and record checks
- PDB/mmCIF coordinate, chain, and model checks
- interactive 3D rendering for structures
- reviewer name, decision, and notes
- downloadable JSON review records
- benchmark run ID and SHA-256 artifact identity

It intentionally does not run Evo 2, predict perturbation responses, or make autonomous scientific decisions. A future model adapter can add predictions to the same review record after the benchmark core defines its input/output contract.

## Use

Open `index.html` in a browser, choose an artifact, inspect the rendered structure or sequence summary, run checks, enter a decision, and choose **Save review JSON**. The file is processed in the browser; no upload service is included.

The sandbox rejects files larger than 25 MiB to bound in-browser resource use. It also applies a restrictive Content Security Policy that blocks page network connections and object embeds while allowing the 3Dmol.js renderer. Production deployments should pin and self-host that dependency with integrity-controlled builds.

Enter the benchmark `run_id` before saving a review. The sandbox computes an artifact SHA-256 with the browser Web Crypto API. The Python review gate can then require an approved decision, a reviewer, the expected run ID, and a matching artifact hash before a report consumes the artifact.

This is an exploratory local sandbox. It is not a replacement for validated structural biology software or a publication-grade geometry checker.
