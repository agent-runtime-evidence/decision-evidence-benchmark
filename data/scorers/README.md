# Scorer Outputs

This directory holds candidate scorer output JSONL files used for property-level
evaluation. Draft scorer outputs are mechanics fixtures only and must keep a
blocking `fixture_status` until replaced by reviewed non-fixture scorer runs.

Run `decision-evidence-benchmark validate-scorer-predictions` before using a
scorer output file in a result package. The validation requires the configured
candidate scorer to cover every case and provide one prediction for every
Decision Event Schema property.

For the default no-human manuscript output, first run:

```bash
make write-manuscript-deterministic-scorer
```

This writes `data/scorers/decision_trace_reconstructor_outputs.jsonl` from the
redacted scorer input and private case-id map. The deterministic scorer uses
visible redacted fields only and does not read oracle labels or degradation
conditions.

For an external or manually reviewed scorer run, first run:

```bash
make export-manuscript-scorer-workbook
```

Fill and review `data/results/manuscript_scorer_workbook.reviewed.csv`, then
run:

```bash
make import-manuscript-scorer-workbook
```

The import writes `data/scorers/decision_trace_reconstructor_outputs.jsonl`
only when every row has `prediction_status=reviewed`, a valid verdict, a valid
property category, and non-fixture run metadata.
