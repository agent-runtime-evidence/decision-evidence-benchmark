# Benchmark Backend Scope

This repository implements the backend workstream for a cross-regime
decision-evidence sufficiency benchmark.

## In Scope

- Normalize eight evidence regimes into a shared case manifest.
- Run the five deterministic default baselines on the same manifests, with
  optional pinned LLM-judge output support.
- Import or run a property-level candidate scorer such as Decision Trace
  Reconstructor.
- Store property-level labels and label provenance.
- Aggregate Overclaim Rate and Property Sufficiency Accuracy.
- Emit reproducible result artifacts suitable for manuscript tables.

## Out of Scope

- Legal adequacy certification.
- Production monitoring claims.
- Vendor ranking.
- Replacing Operational Evidence Plane or Decision Trace Reconstructor.
- Publishing release artifacts before explicit approval.

## Section 7 Readiness Test

Section 7 is ready only when the repository can produce, from committed inputs
or pinned external artifacts:

- per-baseline Overclaim Rate;
- per-scorer Property Sufficiency Accuracy;
- degradation sensitivity slices;
- cross-regime slices;
- question-family slices;
- deterministic label construction and paired-oracle self-consistency
  diagnostics;
- annotation provenance for labels promoted into case manifests;
- a corpus manifest that passes strict validation;
- a result-readiness report separating mechanical validity from manuscript-ready
  result status;
- checksums for result artifacts used in the manuscript.

## Artifact Integrity

Tracked source files and fixtures are listed in `manifest.yaml`. Their current
SHA-256 pins are stored in `checksums.txt` and verified by `make verify`.
Whenever a tracked file is intentionally changed, run `make update-checksums`
and include the checksum update in the same commit.
