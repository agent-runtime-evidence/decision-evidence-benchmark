# Manuscript Result Runbook

This runbook defines the path from the executable scaffold to manuscript-ready
result artifacts. Smoke fixtures prove that mechanics work; they are not
empirical evidence and must not be promoted by renaming files or editing JSON by
hand.

## Required Artifact Set

A manuscript result package requires all of the following artifacts:

- a corpus manifest with `claim_status: manuscript_result_candidate`;
- adapted case-manifest JSONL files covering all eight regimes;
- construction-derived oracle annotation records and a self-consistency
  calibration summary;
- row-level label review exports for disagreement inspection and adjudication;
- an adjudication report and adjudicated case manifests when labels are
  maintained separately from adapted evidence;
- candidate scorer outputs, a scorer validation report, and a property-level
  evaluation summary;
- pinned LLM-judge baseline outputs and a baseline validation report only if
  the optional LLM-judge baseline is included;
- baseline outputs, aggregate baseline summary, and run manifest;
- a readiness report produced with `--fail-on-blockers`;
- a readiness-gap report that maps any remaining blockers to the artifact area
  that must be fixed before Section 7 use;
- manuscript-facing gate, blocker, and artifact inventory tables exported from
  the result package.

The run manifest should list the corpus validation, label calibration, label
review, label adjudication, and candidate scorer summary as supporting input
artifacts so downstream reviewers can verify what evidence the result package
depended on.

## Readiness Defaults

The default readiness policy requires:

- `required_corpus_claim_status: manuscript_result_candidate`;
- `run_claim_status: manuscript_result_candidate`;
- at least 64 cases;
- all eight regimes, degradation conditions, and question families;
- at least eight cases per regime, degradation condition, and question family;
- at least eight strictly sufficient and eight strictly insufficient cases;
- at least one complete and one non-complete label for each decision property;
- overall and per-property paired-oracle self-consistency kappa of at least
  0.6;
- the five deterministic baselines plus the Decision Trace Reconstructor
  candidate scorer;
- no `fixture_placeholder`, `draft_synthetic_oracle`, `smoke_only`,
  `draft_two_annotator_fixture`, or `smoke_two_annotator_fixture` status in
  manuscript-gated inputs.

The default manuscript label path is deterministic construction-derived
labelling: property categories are computed from the case
`degradation_condition` by the machine-readable rule spec at
`data/oracle/construction_oracle_v1.yaml`. The annotation JSONL keeps two
mechanical oracle passes only to preserve the existing calibration and
adjudication mechanics; it must not be described as human annotation.

The built-in `llm_judge` baseline is excluded from the no-human default. Include
it only when `MANUSCRIPT_BASELINES` includes `llm_judge` and
`--llm-judge-predictions` points to a pinned JSONL artifact with one
`llm_judge` verdict per case.

A balanced 64-case design is acceptable when it satisfies these slice and label
balance constraints. The benchmark does not require a full Cartesian expansion
of every regime, degradation condition, and question family.

## Draft Balanced Corpus Scaffold

To exercise manuscript-scale mechanics before real labels and scorer outputs
exist, generate the draft 64-case scaffold:

```bash
decision-evidence-benchmark generate-draft-corpus
```

This writes:

- `data/cases/draft_balanced_64_cases.jsonl`;
- `data/annotations/draft_balanced_64_annotations.jsonl`;
- `data/scorers/draft_balanced_64_scorer_outputs.jsonl`;
- `data/corpus/draft_balanced_64_corpus.yaml`.

These files are synthetic mechanics fixtures. They are deliberately marked with
`mechanical_draft_not_empirical_evidence`, `draft_two_annotator_fixture`, and
`draft_synthetic_oracle` statuses so the default readiness gate blocks them from
manuscript promotion.

To exercise the 64-case package path without promoting the draft corpus, run:

```bash
make verify-draft-package
```

This target builds `data/results/draft_package_package_manifest.json`,
validates its artifact checksums, and exports draft gate/blocker/inventory
tables. It intentionally does not pass `--fail-on-blockers`; the expected
outcome is a mechanically valid package with manuscript-readiness blockers.
See `docs/manuscript_artifact_plan.md` for the concrete artifact replacement
sequence from this draft package to a manuscript-candidate package.
Start the manuscript case-authoring pass with:

```bash
make write-manuscript-case-source-template
```

Initialize the dedicated manuscript-corpus evidence source root:

```bash
make init-manuscript-evidence-source
```

This writes `data/sources/manuscript_corpus/source_manifest.json` and
`data/sources/manuscript_corpus/case_evidence_sources.jsonl`. The initialized
rows are a source-review skeleton only. They are deliberately left at
`template_status=requires_non_fixture_evidence` until source refs, provenance
notes, reviewer metadata, and container flags are filled.
Export those rows as a spreadsheet-friendly review workbook:

```bash
make export-manuscript-source-review-workbook
```

After filling the workbook, save the reviewed CSV as
`data/results/manuscript_source_review_workbook.reviewed.csv` and import it:

```bash
make import-manuscript-source-review-workbook
```

The importer updates `data/sources/manuscript_corpus/source_manifest.json` and
`data/sources/manuscript_corpus/case_evidence_sources.jsonl` only if every row
has reviewed status, non-placeholder source refs, provenance notes, reviewer
metadata, and concrete container flags. A rejected workbook leaves the source
root unchanged.

For deterministic manuscript benchmark source construction, the workbook can be
materialized without using the advisory OEP or anchor pilot roots:

```bash
make materialize-manuscript-source-review
```

This writes aggregate native, evidence-plane, and review records under
`data/sources/manuscript_corpus`, fills
`data/cases/manuscript_case_sources.reviewed.jsonl`, and emits reviewed
source-review/evidence-workqueue CSVs. It is still source-review only:
property labels, adjudication, scorer outputs, baseline outputs, and the
strict manuscript result package remain blocked until separately produced.
Audit local source roots before marking any row reviewed:

```bash
make audit-manuscript-source-roots
```

The audit writes `data/results/manuscript_source_root_audit.json` and keeps
advisory source-root scope issues separate from required manuscript-corpus
source-root blockers. A row should not be marked `reviewed_non_fixture_evidence`
solely because the audit found a local file path; the row still needs source
review and provenance notes.
Export the audited source-root refs as review candidates:

```bash
make export-manuscript-source-candidates
```

This writes `data/results/manuscript_source_candidates.csv` and
`data/results/manuscript_source_candidates.jsonl`. The export preserves
promotion blockers and labels demo / anchor source roots as reference context
until a manuscript-corpus evidence source exists.

Generate per-case review packets while filling the source workbook:

```bash
make export-manuscript-source-review-packets
```

This writes `data/results/manuscript_source_review_packets/`,
`data/results/manuscript_source_review_packets.csv`, and
`data/results/manuscript_source_review_packets.json`. The packets are
authoring aids: they show each case row, missing review fields, required source
root refs, and advisory local refs without promoting evidence.

Generate the initial guarded source-review slice:

```bash
make export-manuscript-source-review-slice
```

This writes `data/results/manuscript_source_review_slice.csv` and
`data/results/manuscript_source_review_slice.json`. The default slice contains
one case per regime, leaves review fields empty, and is not importable as a
complete reviewed workbook.

After filling the slice, save it as
`data/results/manuscript_source_review_slice.reviewed.csv` and run:

```bash
make validate-manuscript-source-review-slice
```

The validator applies the same row-level source-review rules as the full
workbook importer. If it passes, merge the slice into the full workbook scaffold:

```bash
make merge-manuscript-source-review-slice
```

The merge writes
`data/results/manuscript_source_review_workbook.merged_from_slice.csv` only. It
does not update the manuscript source root.

Build the row-level authoring queue:

```bash
make build-manuscript-evidence-intake
```

The intake report writes `data/results/manuscript_evidence_intake.json` with
`ready`, `blocked`, `needs_source`, and `needs_annotation` counts plus a
per-case next action. This is the bridge from the 64-row template to a reviewed
case-source file; it is not a manuscript result artifact.
When `data/cases/manuscript_case_sources.reviewed.jsonl` exists, the Make
target uses it as the intake source and should report `needs_annotation` rather
than `needs_source`.
Export a spreadsheet-friendly authoring queue from the intake report:

```bash
make export-manuscript-evidence-workqueue
```

This writes `data/results/manuscript_evidence_workqueue.csv` and
`data/results/manuscript_evidence_workqueue.jsonl`. Use the CSV/JSONL to track
source refs, reviewer identity, review timestamp, notes, and the
`review_packet_path` for each case. It remains an authoring artifact; the
converter still reads only
`data/cases/manuscript_case_sources.reviewed.jsonl`.
After filling the queue, save the reviewed CSV as
`data/results/manuscript_evidence_workqueue.reviewed.csv` and import it:

```bash
make import-manuscript-evidence-workqueue
```

The importer rejects rows with `todo` / `blocked` review status, placeholder
refs, placeholder container flags, empty reviewer metadata, taxonomy mismatch,
or missing case IDs. It writes `data/cases/manuscript_case_sources.reviewed.jsonl`
only when the reviewed workqueue passes validation.

The generated `data/cases/manuscript_case_sources.template.jsonl` is a source
collection template only. It is not a case manifest and cannot satisfy the
strict manuscript package gate until its rows are replaced by reviewed
non-fixture case manifests, annotations, scorer outputs, and baseline outputs.
After source review, save the filled rows as
`data/cases/manuscript_case_sources.reviewed.jsonl` and run:

```bash
make convert-manuscript-case-sources
```

The converter writes `data/cases/manuscript_cases.unadjudicated.jsonl` only
when all rows are marked as reviewed non-fixture evidence and required source
references plus concrete container flags are present.

## Claim Promotion Rules

Set `claim_status: manuscript_result_candidate` only after the referenced
source artifacts are complete, reviewed, and non-fixture. For run manifests, use
`--run-claim-status manuscript_result_candidate` only for the audited
manuscript-scale run. The smoke corpus and smoke output should remain marked as
mechanical or smoke-only artifacts.

The template at `data/corpus/manuscript_corpus.template.yaml` is a starting
point for the final corpus manifest. Copy it to a non-template manifest only
after the referenced case and annotation files exist.

## Execution Sequence

The full sequence can be assembled with one command:

```bash
make verify-manuscript-package
```

The target writes deterministic scorer outputs from the redacted scorer inputs,
runs the label-leakage audit, promotes the corpus manifest, then starts
`check-manuscript-inputs`. The preflight writes
`data/results/manuscript_input_preflight.json` and stops before package
assembly if required manuscript inputs are missing. It then builds the strict
package with `--fail-on-blockers`, validates the package manifest, and exports
manuscript-facing tables. It includes
`data/annotations/manuscript_adjudication_overrides.jsonl` automatically when
that file exists; otherwise it omits the override argument. Omit adjudication
overrides only when the mechanical oracle passes, or any intentionally selected
annotation policy, agree on every property.
The package command writes `manuscript_label_adjudication.json`,
`manuscript_adjudicated_cases.jsonl`, and
`manuscript_adjudicated_corpus.yaml`, evaluates scorer outputs and baselines
against the adjudicated cases, validates the adjudicated corpus manifest, and
records these artifacts in the package manifest. It also writes
`manuscript_readiness_gaps.json` next to the readiness report.

Validate the assembled package manifest and artifact checksums:

```bash
decision-evidence-benchmark validate-result-package \
  --manifest data/results/manuscript_package_manifest.json \
  --out data/results/manuscript_package_validation.json
```

Export the package tables used to populate the manuscript result narrative:

```bash
decision-evidence-benchmark export-manuscript-tables \
  --package-manifest data/results/manuscript_package_manifest.json \
  --out-dir data/results \
  --prefix manuscript
```

The exporter writes `manuscript_gate_status.csv`,
`manuscript_readiness_blockers.csv`, `manuscript_artifact_inventory.csv`, and
`manuscript_table_export_summary.json`. These files summarize gate state and
artifact provenance; they do not convert blocked smoke or draft outputs into
empirical Section 7 results.

The individual steps below are equivalent and useful for inspecting failures.

At any point, inspect current authoring progress and Section 7 gate blockers:

```bash
make manuscript-authoring-status
```

This writes `data/results/manuscript_authoring_status.json`, including
per-stage artifact presence, reviewed-workbook gaps, missing gate inputs, and
next actions. It is read-only with respect to manuscript labels, scorer outputs,
baseline outputs, and result packages.

After required gate JSONL artifacts exist, promote the corpus manifest template:

```bash
make write-manuscript-corpus-manifest
```

The target writes `data/corpus/manuscript_corpus.yaml` from
`data/corpus/manuscript_corpus.template.yaml` only after the adjudicated case
manifest, annotation JSONL, and candidate scorer JSONL are present. It requires
LLM-judge JSONL only when `llm_judge` is included in `MANUSCRIPT_BASELINES`. It
writes `data/results/manuscript_corpus_manifest_promotion.json` for audit and
refuses to overwrite a different existing corpus manifest.

Validate the manuscript corpus:

```bash
decision-evidence-benchmark validate-corpus \
  --manifest data/corpus/manuscript_corpus.yaml \
  --out data/results/manuscript_corpus_validation.json
```

Compute label calibration:

For the default deterministic manuscript path, write construction-derived
oracle labels after `data/cases/manuscript_cases.unadjudicated.jsonl` exists:

```bash
make write-manuscript-construction-oracle
```

This target writes `data/annotations/manuscript_annotations.jsonl`,
`data/cases/manuscript_cases.jsonl`, and
`data/results/manuscript_construction_oracle.json`. It refuses to overwrite
existing annotation or case outputs unless run with:

```bash
MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE=1 make write-manuscript-construction-oracle
```

The output is a construction-derived ground-truth oracle. It is not human
annotation, not LLM judgement, and not candidate scorer output.
The report includes the oracle spec SHA-256 plus input/output artifact hashes,
so the label construction can be reproduced and checked against the exact rule
file.

The older guarded two-annotator workbook remains available only if the label
policy is intentionally changed away from construction rules:

```bash
make export-manuscript-annotation-workbook
```

This writes `data/results/manuscript_annotation_workbook.csv` and `.jsonl`.
The workbook has one row per case, property, and annotator. Rows start with
`annotation_status=todo` and `category=__SELECT_CATEGORY__`; they are authoring
placeholders, not labels.

For incremental annotation review, export a guarded one-case-per-regime slice:

```bash
make export-manuscript-annotation-slice
```

This writes `data/results/manuscript_annotation_slice.csv` and `.json`. The
default slice includes both annotators and all eight properties for each
selected case. After filling it, save it as
`data/results/manuscript_annotation_slice.reviewed.csv` and run:

```bash
make validate-manuscript-annotation-slice
make merge-manuscript-annotation-slice
```

The merge command writes
`data/results/manuscript_annotation_workbook.merged_from_slice.csv` only. It
does not update `data/annotations/manuscript_annotations.jsonl`.

After both annotation passes are filled, save the completed CSV as
`data/results/manuscript_annotation_workbook.reviewed.csv` and import it:

```bash
make import-manuscript-annotation-workbook
```

The importer writes `data/annotations/manuscript_annotations.jsonl` only when
the workbook covers all 64 cases, 8 properties, and exactly two annotators with
valid categories and `annotation_status=annotated`.

```bash
make calibrate-manuscript-labels
```

Export label review rows for adjudication:

```bash
make review-manuscript-labels
```

Write a fill-in override template from the disagreement rows:

```bash
make write-manuscript-adjudication-overrides-template
```

The template uses `__SELECT_CATEGORY__` as a non-valid placeholder. Replace it
with a valid property category before saving the edited file as
`data/annotations/manuscript_adjudication_overrides.jsonl`.

Promote adjudicated labels into case manifests:

```bash
make adjudicate-manuscript-labels
```

If the two label passes agree on every property, `--overrides` can be omitted.
When any disagreement lacks an override, the command exits nonzero and does not
write promoted cases unless `--allow-unresolved` is explicitly set.

Validate and evaluate candidate scorer outputs:

For the default no-human path, write
`data/scorers/decision_trace_reconstructor_outputs.jsonl` from redacted
scorer-facing fields:

```bash
make write-manuscript-deterministic-scorer
```

This target writes the redacted scorer input, applies deterministic property
rules to visible redacted fields only, maps predictions back to internal case
IDs through the private map, and writes
`data/results/manuscript_scorer_import.json`. It does not read degradation
conditions or oracle labels.

If using an external scorer run instead, write the redacted scorer input and
export the guarded candidate-scorer workbook:

```bash
make write-manuscript-scorer-input
make export-manuscript-scorer-workbook
```

The redaction target writes `data/cases/manuscript_scorer_input_cases.jsonl`,
`data/cases/manuscript_scorer_input_case_id_map.jsonl`, and
`data/results/manuscript_scorer_input_redaction.json`. The exported workbook
uses opaque `case-000001` style IDs, omits degradation conditions, labels, and
source refs, and starts with `prediction_status=todo`,
`verdict=__SELECT_VERDICT__`, and `category=__SELECT_CATEGORY__`. After running
and reviewing the candidate scorer, save the completed CSV as
`data/results/manuscript_scorer_workbook.reviewed.csv` and import it:

If local reviewed workbooks predate the redacted scorer-input path, archive
them first:

```bash
make clean-manuscript-stale-reviewed-workbooks
```

The target moves only non-redacted reviewed CSV files into
`data/results/manuscript_stale_reviewed_workbook_archive/` and writes a report;
it does not create replacement reviewed predictions.

```bash
make import-manuscript-scorer-workbook
```

The importer writes `data/scorers/decision_trace_reconstructor_outputs.jsonl`
only when every case and every Decision Event Schema property has a reviewed
prediction row with non-fixture metadata. The importer uses the private
redacted case-id map to restore original evaluation case IDs in the internal
output JSONL.

Before using scorer or LLM-judge outputs in a manuscript package, run the label
leakage audit:

```bash
make audit-manuscript-label-leakage
```

This writes `data/results/manuscript_label_leakage_audit.json`. A valid audit
means the configured scorer-facing artifacts do not expose
`degradation_condition`, embedded property labels, or degradation-condition
tokens in scorer-facing IDs/source refs. It does not prove semantic
independence; it is an executable guard against obvious oracle leakage.

```bash
decision-evidence-benchmark validate-scorer-predictions \
  --cases data/cases/manuscript_cases.jsonl \
  --predictions data/scorers/decision_trace_reconstructor_outputs.jsonl \
  --out data/results/manuscript_scorer_validation.json
```

```bash
decision-evidence-benchmark evaluate-scorer \
  --cases data/cases/manuscript_cases.jsonl \
  --predictions data/scorers/decision_trace_reconstructor_outputs.jsonl \
  --out data/results/manuscript_scorer_results.jsonl \
  --summary data/results/manuscript_scorer_summary.json
```

Run the deterministic baselines and write a manuscript candidate run manifest:

The default manuscript package omits `llm_judge`. Before intentionally adding
`data/baselines/llm_judge_outputs.jsonl`, export the guarded LLM-judge
workbook:

```bash
make export-manuscript-llm-judge-workbook
```

This writes `data/results/manuscript_llm_judge_workbook.csv` and `.jsonl`.
Rows start with placeholder verdict and metadata fields. After the documented
prompt run is reviewed, save the completed CSV as
`data/results/manuscript_llm_judge_workbook.reviewed.csv` and import it:

```bash
make import-manuscript-llm-judge-workbook
```

The importer writes `data/baselines/llm_judge_outputs.jsonl` only when every
case has a reviewed verdict and non-fixture implementation metadata.

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
  --out data/results/manuscript_baseline_results.jsonl \
  --summary data/results/manuscript_baseline_summary.json \
  --baseline trace_present \
  --baseline ledger_present \
  --baseline schema_present \
  --baseline container_checklist \
  --baseline source_specific_validator \
  --supporting-input data/results/manuscript_corpus_validation.json \
  --supporting-input data/results/manuscript_label_calibration.json \
  --supporting-input data/results/manuscript_label_review.json \
  --supporting-input data/results/manuscript_label_adjudication.json \
  --supporting-input data/results/manuscript_scorer_validation.json \
  --supporting-input data/results/manuscript_scorer_summary.json \
  --run-manifest data/results/manuscript_run_manifest.json \
  --run-claim-status manuscript_result_candidate
```

Assemble and gate the readiness report:

```bash
decision-evidence-benchmark readiness-report \
  --corpus-validation data/results/manuscript_corpus_validation.json \
  --label-calibration data/results/manuscript_label_calibration.json \
  --label-review data/results/manuscript_label_review.json \
  --label-adjudication data/results/manuscript_label_adjudication.json \
  --scorer-validation data/results/manuscript_scorer_validation.json \
  --scorer-summary data/results/manuscript_scorer_summary.json \
  --baseline-summary data/results/manuscript_baseline_summary.json \
  --run-manifest data/results/manuscript_run_manifest.json \
  --required-baseline trace_present \
  --required-baseline ledger_present \
  --required-baseline schema_present \
  --required-baseline container_checklist \
  --required-baseline source_specific_validator \
  --out data/results/manuscript_readiness_report.json \
  --fail-on-blockers
```

If the readiness gate blocks publication use, write the gap report:

```bash
decision-evidence-benchmark readiness-gaps \
  --readiness-report data/results/manuscript_readiness_report.json \
  --out data/results/manuscript_readiness_gaps.json
```

Only the final command passing without blockers indicates that the selected
result package has crossed the repository's manuscript-readiness gate.
