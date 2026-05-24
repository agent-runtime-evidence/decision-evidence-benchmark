# Baseline Output Artifacts

This directory is for pinned external or model-run baseline outputs.

The default manuscript package uses five deterministic baselines and does not
require a file in this directory. To include the optional `llm_judge` baseline,
supply JSONL with one row per case:

```json
{"case_id":"case-id","scorer":"llm_judge","verdict":"insufficient","metadata":{"implementation_status":"documented_prompt_run"}}
```

Use `--llm-judge-predictions` with `decision-evidence-benchmark run` or
`decision-evidence-benchmark build-result-package`, and include `llm_judge` in
the selected baseline list. Do not use smoke or draft LLM-judge fixture outputs
as manuscript evidence.

Run `decision-evidence-benchmark validate-baseline-predictions` before using an
imported baseline file. The validation requires the selected baseline to cover
every case exactly once and rejects unknown case identifiers or scorer/baseline
name mismatches.

For manuscript-scale LLM-judge outputs, first run:

```bash
make export-manuscript-llm-judge-workbook
```

Fill and review `data/results/manuscript_llm_judge_workbook.reviewed.csv`, then
run:

```bash
make import-manuscript-llm-judge-workbook
```

The import writes `data/baselines/llm_judge_outputs.jsonl` only when every case
has `prediction_status=reviewed`, a valid verdict, and non-fixture documented
prompt-run metadata.
