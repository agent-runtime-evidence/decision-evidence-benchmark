# Manuscript Source Roots

This directory holds authoring inputs for manuscript-scale evidence sources.
Files here are not result artifacts. A source root becomes manuscript-promotable
only after its rows are reviewed, non-fixture, and accepted by
`make audit-manuscript-source-roots`.

Initialize the Paper24 source root with:

```bash
make init-manuscript-evidence-source
```

The generated `manuscript_corpus` root starts as a skeleton. Do not copy its
rows into `data/cases/manuscript_case_sources.reviewed.jsonl` until every row
has concrete source refs, provenance notes, reviewer metadata, and container
flags.

For the deterministic manuscript benchmark source materialization path, run:

```bash
make materialize-manuscript-source-review
```

This writes reviewed source rows and aggregate native/evidence-plane/review
records for the benchmark corpus. It closes source review only; property
annotations, adjudication, scorer outputs, baselines, and result claims remain
separate gated artifacts.
