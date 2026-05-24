# Data Layout

- `fixtures/` contains tiny smoke cases for testing runner mechanics only.
- `cases/` holds benchmark case manifests and draft generated case scaffolds.
- `corpus/` holds corpus manifests that bind case files to label contracts.
- `annotations/` holds per-annotator property-label records.
- `baselines/` holds pinned external/model-run baseline outputs, including
  manuscript-scale LLM-judge JSONL artifacts.
- `scorers/` holds candidate scorer output JSONL files.
- `labels/` will hold calibration labels, adjudication notes, and synthetic
  label provenance.
- `results/` is ignored by git by default because runner outputs are
  regenerable. Promote result artifacts to a checksummed release manifest before
  using them in a manuscript, report, or release package.
