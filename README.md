# Decision Evidence Benchmark

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20408699.svg)](https://doi.org/10.5281/zenodo.20408699)
[![CI](https://github.com/agent-runtime-evidence/decision-evidence-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/agent-runtime-evidence/decision-evidence-benchmark/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Executable backend scaffold for the Decision Evidence Maturity Model
cross-regime benchmark.

This repository is separate from:

- `operational-evidence-plane`, which is a reference implementation substrate.
- `anchor-level-reconstructability-pilot`, which is a frozen anchor-level
  reproducibility artifact.

The purpose here is narrower and more demanding: generate reproducible
benchmark result artifacts for a cross-regime decision-evidence sufficiency
study.

## Current Status

The repository currently includes:

- a case manifest schema in Python dataclasses;
- native AER, MAT, IEEC, DCC/HDP, PROV, LLM Audit Trails, AEGIS-NTC, and
  Dynamic Capabilities fixture adapters for exercising the manifest boundary;
- deterministic implementations for the five non-LLM container-presence
  baselines;
- optional imported pinned-output support for adding an LLM-judge
  external/model-run artifact;
- imported baseline output validation for case coverage before metric use;
- Overclaim Rate and Property Sufficiency Accuracy helpers;
- candidate scorer output import and property-level evaluation;
- candidate scorer output validation for case and property coverage;
- summary slices by regime, degradation condition, and question family;
- corpus inventory counts by regime, question family, degradation condition,
  property category, and strict sufficiency;
- a balanced 64-case draft corpus generator for exercising manuscript-scale
  mechanics without promoting synthetic outputs as evidence;
- a deterministic construction-derived oracle for manuscript property labels
  based on explicit degradation-condition rules stored in
  `data/oracle/construction_oracle_v1.yaml`;
- a Cohen kappa helper for mechanical paired-oracle self-consistency
  diagnostics;
- smoke label calibration for mechanics checks;
- row-level label review exports for adjudication workflow checks;
- fill-in adjudication override templates for disagreement rows;
- adjudicated label promotion into case manifests;
- one-command result package assembly for corpus validation, label calibration,
  label review, adjudication, scorer evaluation, baselines, run manifest, and
  readiness report;
- result package artifact checksum validation;
- a result-readiness report that distinguishes mechanics from manuscript-ready
  evidence;
- an actionable readiness-gap report that maps blockers to artifact areas and
  next steps;
- manuscript-facing CSV exports for gate status, readiness blockers, and
  package artifact inventory;
- a smoke corpus manifest and corpus validator;
- a manuscript result runbook and corpus manifest template;
- a label-leakage audit for scorer-facing manuscript artifacts;
- a deterministic redacted-input candidate scorer writer for no-human
  manuscript package assembly;
- a smoke fixture and tests.

The default manuscript package path is no-human and no-LLM: construction labels
come from the executable oracle, the candidate scorer output is generated from
redacted scorer-facing fields, and the package uses five deterministic
baselines. LLM-judge can still be added as an optional pinned artifact by
setting `MANUSCRIPT_BASELINES="trace_present ledger_present schema_present
container_checklist source_specific_validator llm_judge"` and supplying
`data/baselines/llm_judge_outputs.jsonl`.

## Target Benchmark Contract

The benchmark requires:

1. Eight regime adapters: AER, MAT, IEEC, DCC/HDP, PROV, LLM Audit Trails,
   AEGIS-NTC, and Dynamic Capabilities.
2. Five deterministic default baselines: trace-present, ledger-present,
   schema-present, container-checklist, and source-specific validator.
   LLM-judge is an optional pinned external/model-run baseline.
3. One property-level candidate scorer interface for Decision Trace
   Reconstructor outputs.
4. Labels over Decision Event Schema properties: actor identity, principal
   authority, action boundary, policy basis, decision basis, data/resource
   touch, lifecycle context, and verification strength.
5. Metrics: Property Sufficiency Accuracy and Overclaim Rate, followed by the
   secondary metrics defined by the benchmark protocol.

## Compute Requirements

DEMM-Bench is intentionally lightweight and **deterministic** (no stochastic
component, no LLM call on the critical path, no GPU). The reference 64-case
manuscript package runs end-to-end in **under 60 seconds per case on a
consumer laptop** (adapter translation + degradation + scoring + readiness
gate). The full 178-test suite completes in approximately seven seconds.

- Python: 3.11, 3.12, 3.13, or 3.14 (verified)
- RAM: under 512 MB working set
- Disk: under 250 MB including dependencies, tracked data, and reference results
- GPU: not required
- Network: not required after the initial `pip install`
- Determinism: bit-exact reproducible (`mean PSA = 0.5625`, `kappa = 1.0`,
  baseline overclaim rates `0.75 / 0.50 / 0.00`) across runs, platforms, and
  supported Python versions

If you intend to enable the optional LLM-judge baseline (`--baseline llm_judge`),
expect cost and latency commensurate with the model family chosen; see paper
§4.3 and the LLM-judge workbook export/import flow under `scripts/`.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
make verify
```

Run the smoke benchmark:

```bash
decision-evidence-benchmark run \
  --cases data/fixtures/smoke_cases.jsonl \
  --out data/results/smoke_results.jsonl \
  --summary data/results/smoke_summary.json \
  --supporting-input data/results/smoke_corpus_validation.json \
  --supporting-input data/results/smoke_label_calibration.json \
  --supporting-input data/results/smoke_scorer_summary.json \
  --run-manifest data/results/smoke_run_manifest.json
```

For manuscript-scale runs, the default strict package uses five deterministic
baselines and treats `llm_judge` as optional. To include `llm_judge`, supply a
pinned JSONL artifact:

```bash
make export-manuscript-llm-judge-workbook
make import-manuscript-llm-judge-workbook
```

The import target expects a reviewed
`data/results/manuscript_llm_judge_workbook.reviewed.csv` and writes
`data/baselines/llm_judge_outputs.jsonl` only after coverage and metadata
validation pass.

```bash
decision-evidence-benchmark validate-baseline-predictions \
  --cases data/cases/manuscript_cases.jsonl \
  --baseline llm_judge \
  --predictions data/baselines/llm_judge_outputs.jsonl \
  --out data/results/manuscript_llm_judge_validation.json
```

```bash
decision-evidence-benchmark run \
  --cases data/cases/manuscript_cases.jsonl \
  --llm-judge-predictions data/baselines/llm_judge_outputs.jsonl \
  --out data/results/manuscript_baseline_results.jsonl \
  --summary data/results/manuscript_baseline_summary.json
```

Validate the smoke corpus manifest:

```bash
decision-evidence-benchmark validate-corpus \
  --manifest data/corpus/smoke_corpus.yaml \
  --out data/results/smoke_corpus_validation.json
```

Validate and evaluate the smoke candidate scorer fixture:

For the default no-human manuscript candidate scorer output, generate redacted
scorer inputs and deterministic scorer predictions:

```bash
make write-manuscript-deterministic-scorer
```

For an externally reviewed scorer run instead, use the redacted scorer-input
path and guarded workbook import before running validation:

```bash
make write-manuscript-scorer-input
make export-manuscript-scorer-workbook
make import-manuscript-scorer-workbook
```

The redaction target writes
`data/cases/manuscript_scorer_input_cases.jsonl`,
`data/cases/manuscript_scorer_input_case_id_map.jsonl`, and
`data/results/manuscript_scorer_input_redaction.json`. Exported scorer-facing
workbooks use opaque `case-000001` style IDs and omit degradation conditions,
labels, and source refs. The private case-id map is used only by the import
targets to map reviewed predictions back to original evaluation case IDs.

Inspect manuscript authoring progress and Section 7 gate blockers:

```bash
make manuscript-authoring-status
```

This writes `data/results/manuscript_authoring_status.json`. The report is
diagnostic only; it does not import reviewed workbooks or create result
artifacts.

After construction-oracle annotations, adjudicated cases, and candidate scorer
outputs exist, promote the corpus manifest template:

```bash
make write-manuscript-corpus-manifest
```

The target refuses to write `data/corpus/manuscript_corpus.yaml` until required
gate inputs exist.

```bash
decision-evidence-benchmark validate-scorer-predictions \
  --cases data/fixtures/smoke_cases.jsonl \
  --predictions data/fixtures/smoke_scorer_outputs.jsonl \
  --out data/results/smoke_scorer_validation.json
```

```bash
decision-evidence-benchmark evaluate-scorer \
  --cases data/fixtures/smoke_cases.jsonl \
  --predictions data/fixtures/smoke_scorer_outputs.jsonl \
  --out data/results/smoke_scorer_results.jsonl \
  --summary data/results/smoke_scorer_summary.json
```

Compute smoke label calibration diagnostics:

```bash
decision-evidence-benchmark calibrate-labels \
  --cases data/fixtures/smoke_cases.jsonl \
  --annotations data/annotations/smoke_annotations.jsonl \
  --summary data/results/smoke_label_calibration.json
```

Export row-level smoke label review details:

```bash
decision-evidence-benchmark review-labels \
  --cases data/fixtures/smoke_cases.jsonl \
  --annotations data/annotations/smoke_annotations.jsonl \
  --out data/results/smoke_label_review.json \
  --csv-out data/results/smoke_label_review.csv
```

Write a fill-in override template when review rows contain disagreements:

```bash
decision-evidence-benchmark write-adjudication-overrides-template \
  --cases data/fixtures/smoke_cases.jsonl \
  --annotations data/annotations/smoke_annotations.jsonl \
  --out data/results/smoke_adjudication_overrides.template.jsonl \
  --adjudicator-id reviewer_1
```

Promote smoke labels into adjudicated case manifests:

```bash
decision-evidence-benchmark adjudicate-labels \
  --cases data/fixtures/smoke_cases.jsonl \
  --annotations data/annotations/smoke_annotations.jsonl \
  --out-cases data/results/smoke_adjudicated_cases.jsonl \
  --report data/results/smoke_label_adjudication.json
```

Generate the balanced 64-case draft corpus scaffold:

```bash
decision-evidence-benchmark generate-draft-corpus
```

The generated draft corpus is for pipeline exercise only. Its corpus,
annotation, and candidate-scorer statuses are readiness blockers by default.

Exercise the generated 64-case draft package mechanics:

```bash
make verify-draft-package
```

This writes draft package, validation, readiness-gap, and table-export outputs
under `data/results/`. These outputs are still blocked from manuscript use by
their fixture statuses.

Use `docs/manuscript_artifact_plan.md` for the concrete replacement sequence
from the 64-case draft package to manuscript-candidate inputs.

Start case authoring from the 64-cell source template:

```bash
make write-manuscript-case-source-template
```

Create the dedicated manuscript-corpus evidence source root:

```bash
make init-manuscript-evidence-source
```

This writes `data/sources/manuscript_corpus/source_manifest.json` and
`data/sources/manuscript_corpus/case_evidence_sources.jsonl` as a 64-row
source-review skeleton. The rows are not reviewed evidence until their source
refs, provenance notes, reviewer metadata, and container flags are filled and
the source manifest is explicitly promoted from template scope.

Export that source root as a spreadsheet-friendly review workbook:

```bash
make export-manuscript-source-review-workbook
```

After filling and reviewing
`data/results/manuscript_source_review_workbook.reviewed.csv`, import it back
into the source root:

```bash
make import-manuscript-source-review-workbook
```

The importer updates `data/sources/manuscript_corpus` only if all 64 rows have
reviewed status, non-placeholder source refs, provenance notes, reviewer
metadata, and concrete container flags.

Audit the local OEP and pilot source roots before marking rows reviewed:

```bash
make audit-manuscript-source-roots
```

Export the audited source-root refs as a review candidate inventory:

```bash
make export-manuscript-source-candidates
```

This writes `data/results/manuscript_source_candidates.csv` and `.jsonl`.
Rows whose source roots remain scoped as demo or anchor artifacts are labelled
as reference context only; they must not be copied into reviewed case rows until
a manuscript-corpus evidence source exists.

Generate one source-review packet per case when filling the workbook:

```bash
make export-manuscript-source-review-packets
```

This writes `data/results/manuscript_source_review_packets/` plus an index CSV
and summary JSON. Packets repeat the case taxonomy, missing source-review
fields, required manuscript source-root refs, and advisory OEP / pilot refs, but
they do not update the source root or promote evidence.

Generate the guarded 8-case review slice before filling the full workbook:

```bash
make export-manuscript-source-review-slice
```

This writes `data/results/manuscript_source_review_slice.csv` and `.json`.
The default slice selects one case per regime and leaves review cells empty on
purpose. It is not a complete 64-row workbook and cannot promote evidence by
itself.

After filling the slice, save it as
`data/results/manuscript_source_review_slice.reviewed.csv` and validate it:

```bash
make validate-manuscript-source-review-slice
```

To merge a valid reviewed slice into a full workbook scaffold, run:

```bash
make merge-manuscript-source-review-slice
```

This writes `data/results/manuscript_source_review_workbook.merged_from_slice.csv`.
It still does not import `data/sources/manuscript_corpus`; the full 64-row
workbook must pass the stricter source-root importer before evidence promotion.

Build a row-level evidence intake report from the template and source audit:

```bash
make build-manuscript-evidence-intake
```

Export the intake rows as a CSV/JSONL authoring queue:

```bash
make export-manuscript-evidence-workqueue
```

After filling and reviewing `data/results/manuscript_evidence_workqueue.reviewed.csv`,
import it into reviewed source rows:

```bash
make import-manuscript-evidence-workqueue
```

After reviewed source rows are saved as
`data/cases/manuscript_case_sources.reviewed.jsonl`, convert them into
unadjudicated case manifests:

```bash
make convert-manuscript-case-sources
```

Write deterministic construction-derived labels and adjudicated manuscript cases:

```bash
make write-manuscript-construction-oracle
```

This writes `data/annotations/manuscript_annotations.jsonl` and
`data/cases/manuscript_cases.jsonl` from explicit
degradation-condition-to-property rules in
`data/oracle/construction_oracle_v1.yaml`. The report records the oracle spec
SHA-256 plus input/output artifact hashes. It refuses to overwrite existing
outputs unless run with `MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE=1`. The output is
ground-truth label construction only; it is not human annotation, not a Gemini
or LLM judgment, and not a Decision Trace Reconstructor run.

Audit scorer-facing artifacts for obvious label leakage:

```bash
make audit-manuscript-label-leakage
```

The audit fails when a scorer or optional LLM-judge artifact exposes
`degradation_condition`, embedded property labels, or case IDs/source refs that
encode degradation-condition tokens. A passing audit is not proof of semantic
independence, but a failing audit is a concrete reproducibility blocker.

After those deterministic artifacts exist, run the strict manuscript package
gate:

```bash
make verify-manuscript-package
```

The target generates the deterministic scorer output, runs the label-leakage
audit, promotes the corpus manifest, then starts `check-manuscript-inputs`.
The preflight writes `data/results/manuscript_input_preflight.json` and fails
before package assembly if required manuscript inputs are missing. LLM-judge
inputs are optional unless `llm_judge` is added to `MANUSCRIPT_BASELINES`.

Assemble the smoke result-readiness report:

```bash
decision-evidence-benchmark readiness-report \
  --corpus-validation data/results/smoke_corpus_validation.json \
  --label-calibration data/results/smoke_label_calibration.json \
  --label-review data/results/smoke_label_review.json \
  --scorer-summary data/results/smoke_scorer_summary.json \
  --baseline-summary data/results/smoke_summary.json \
  --run-manifest data/results/smoke_run_manifest.json \
  --out data/results/smoke_readiness_report.json
```

Explain readiness blockers as artifact-level gaps:

```bash
decision-evidence-benchmark readiness-gaps \
  --readiness-report data/results/smoke_readiness_report.json \
  --out data/results/smoke_readiness_gaps.json
```

Build a full smoke result package:

```bash
decision-evidence-benchmark build-result-package \
  --corpus-manifest data/corpus/smoke_corpus.yaml \
  --cases data/fixtures/smoke_cases.jsonl \
  --annotations data/annotations/smoke_annotations.jsonl \
  --scorer-predictions data/fixtures/smoke_scorer_outputs.jsonl \
  --out-dir data/results \
  --prefix smoke_package
```

The package command writes `*_label_adjudication.json`,
`*_adjudicated_cases.jsonl`, `*_adjudicated_corpus.yaml`, and
`*_readiness_gaps.json` automatically. Add `--adjudication-overrides` when
annotation disagreements have explicit adjudication rows. Omit
`--llm-judge-predictions` only when including a pinned optional LLM-judge
artifact.

Validate the package manifest and referenced artifact checksums:

```bash
decision-evidence-benchmark validate-result-package \
  --manifest data/results/smoke_package_package_manifest.json \
  --out data/results/smoke_package_validation.json
```

Export manuscript-facing tables from the package:

```bash
decision-evidence-benchmark export-manuscript-tables \
  --package-manifest data/results/smoke_package_package_manifest.json \
  --out-dir data/results \
  --prefix smoke_package
```

Convert the native DCC/HDP smoke fixture into a case manifest:

```bash
decision-evidence-benchmark adapt \
  --regime dcc_hdp \
  --input data/cases/dcc_hdp/missing_policy_001.native.json \
  --out data/results/dcc_hdp_case.jsonl
```

## Result Honesty

Do not use smoke output as empirical evidence. It exists only to prove that the
benchmark mechanics run end to end. Publication-ready results require the full
case set, labels, scorer outputs, slice summaries, and aggregation manifest.

Use `docs/manuscript_runbook.md` for the manuscript-scale execution sequence and
`data/corpus/manuscript_corpus.template.yaml` as the starting corpus manifest.

## Citation

If you use DEMM-Bench in your research, please cite both the software artifact
and the accompanying paper. The concept DOI
[10.5281/zenodo.20408699](https://doi.org/10.5281/zenodo.20408699) resolves to
the latest version; cite the specific version DOI for reproducibility.

```bibtex
@software{solozobov_demm_bench_2026,
  author       = {Solozobov, Oleg},
  title        = {{DEMM-Bench: A Decision Evidence Maturity Benchmark
                   for Agent-Runtime Decisions Across Eight Evidence Regimes}},
  year         = 2026,
  publisher    = {Zenodo},
  version      = {v0.1.0},
  doi          = {10.5281/zenodo.20408700},
  url          = {https://doi.org/10.5281/zenodo.20408700}
}
```

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.
