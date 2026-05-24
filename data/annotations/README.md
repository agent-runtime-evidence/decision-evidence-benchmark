# Annotation Fixtures

Annotation files store per-annotator property labels before adjudication or
promotion into case manifests.

The smoke and draft annotation files are mechanics fixtures only. Full benchmark
annotation files should preserve label provenance, calibration scope, and
adjudication status before any aggregate metric is used as evidence.

The default manuscript path uses deterministic construction-derived labels:

```bash
make write-manuscript-construction-oracle
```

This writes `data/annotations/manuscript_annotations.jsonl` from explicit
degradation-condition rules in `data/oracle/construction_oracle_v1.yaml`. It
keeps two mechanical oracle records per case so the existing calibration and
adjudication tools can run, but the metadata marks the records as
`construction_oracle_v1` and stores the oracle spec SHA-256. Do not describe
those rows as human annotation or LLM judgement.

Use `decision-evidence-benchmark review-labels` to export row-level agreement
details before adjudication.

Use `decision-evidence-benchmark write-adjudication-overrides-template` to
create a fill-in JSONL template for disagreement rows. The template is not a
valid override file until each `__SELECT_CATEGORY__` placeholder is replaced by
a valid property category.

Use `decision-evidence-benchmark adjudicate-labels` to promote agreed labels,
plus any explicit adjudication overrides, into case manifests.

If the manuscript label policy is intentionally changed away from construction
rules, start annotation authoring with:

```bash
make export-manuscript-annotation-workbook
```

Fill both annotator passes, save the completed CSV as
`data/results/manuscript_annotation_workbook.reviewed.csv`, then run:

```bash
make import-manuscript-annotation-workbook
```

The importer rejects placeholder categories, non-`annotated` rows, missing
case/property coverage, duplicate rows, and any workbook that does not contain
exactly two annotators.

For incremental review, export a one-case-per-regime slice:

```bash
make export-manuscript-annotation-slice
```

Fill the slice, save it as
`data/results/manuscript_annotation_slice.reviewed.csv`, validate or merge it
with:

```bash
make validate-manuscript-annotation-slice
make merge-manuscript-annotation-slice
```

The merge output is a full workbook authoring aid at
`data/results/manuscript_annotation_workbook.merged_from_slice.csv`; it is not
imported automatically.
