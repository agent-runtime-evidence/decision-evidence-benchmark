# Manuscript Artifact Plan

This plan starts from the manuscript-candidate deterministic package gate:

- `make verify-manuscript-package` passes mechanically and with no readiness
  blockers for the default no-human package.
- `data/results/manuscript_package_manifest.json` reports `case_count=64`.
- `data/results/manuscript_gate_status.csv` reports
  `manuscript_result_ready=True`.
- The default selected baselines are the five deterministic baselines; LLM-judge
  remains an optional pinned external/model-run artifact.

The older draft package must still not be promoted by editing status fields.
Each status transition below is achieved by regenerated, reviewed, or pinned
artifacts.

## Default Gate Inputs

| Artifact | Default status | Validation surface |
| --- | --- | --- |
| `data/corpus/manuscript_corpus.yaml` | `claim_status=manuscript_result_candidate` | `decision-evidence-benchmark validate-corpus` |
| `data/annotations/manuscript_annotations.jsonl` | deterministic construction-derived oracle labels | `make write-manuscript-construction-oracle`, package calibration/review |
| package run | `--run-claim-status manuscript_result_candidate` | package manifest and run manifest |
| `data/scorers/decision_trace_reconstructor_outputs.jsonl` | deterministic redacted-input property rule scorer | `validate-scorer-predictions`, `evaluate-scorer` |
| selected baselines | five deterministic container/evidence baselines | `validate-baseline-predictions`, package summary |
| scorer-facing label leakage | no oracle fields, labels, original IDs, or degradation-condition tokens exposed | `make audit-manuscript-label-leakage` |

Optional LLM-judge results require adding `llm_judge` to
`MANUSCRIPT_BASELINES` and supplying `data/baselines/llm_judge_outputs.jsonl`
with pinned non-fixture verdicts.

## Artifact Sequence

1. Start the case-authoring sheet from the 64-cell template:

   ```bash
   make write-manuscript-case-source-template
   ```

   This writes `data/cases/manuscript_case_sources.template.jsonl`. Each row
   is explicitly marked `template_status=requires_non_fixture_evidence` and
   contains empty source-reference slots. Fill those slots from reviewed
   non-fixture evidence before emitting any manuscript case manifest.
   Initialize the dedicated manuscript-corpus source root:

   ```bash
   make init-manuscript-evidence-source
   ```

   This writes `data/sources/manuscript_corpus/source_manifest.json` and
   `data/sources/manuscript_corpus/case_evidence_sources.jsonl`. The initialized
   rows are source-review skeletons in the same shape as the converter input;
   they remain non-promotable until every row has concrete refs, provenance
   notes, reviewer metadata, and container flags.
   Export the source root as a review workbook:

   ```bash
   make export-manuscript-source-review-workbook
   ```

   After filling it, save the reviewed workbook as
   `data/results/manuscript_source_review_workbook.reviewed.csv` and run:

   ```bash
   make import-manuscript-source-review-workbook
   ```

   The importer updates `data/sources/manuscript_corpus` only if all 64 rows
   validate; otherwise it writes a report and leaves the source root unchanged.
   For the deterministic manuscript benchmark source path, materialize the
   reviewed source layer directly:

   ```bash
   make materialize-manuscript-source-review
   ```

   This writes aggregate source records plus
   `data/cases/manuscript_case_sources.reviewed.jsonl`. Treat the output as
   source-reviewed authoring material only; it does not create labels, scorer
   outputs, baseline outputs, or manuscript results.
   Before marking rows reviewed, audit the local OEP and pilot source roots:

   ```bash
   make audit-manuscript-source-roots
   ```

   This writes `data/results/manuscript_source_root_audit.json`. The audit is
   an authoring preflight only; it can identify local reference artifacts,
   advisory scope blockers, and manuscript-corpus source-root blockers, but it
   does not by itself promote any row to `reviewed_non_fixture_evidence`.
   To export the audited refs as review candidates, run:

   ```bash
   make export-manuscript-source-candidates
   ```

   This writes `data/results/manuscript_source_candidates.csv` and `.jsonl`.
   Candidate rows preserve `promotion_ready`, source-root scope, blockers, and
   review instructions so reference/demo artifacts are not accidentally treated
   as manuscript-corpus case evidence.

   To generate one authoring packet per case, run:

   ```bash
   make export-manuscript-source-review-packets
   ```

   This writes `data/results/manuscript_source_review_packets/`, an index CSV,
   and a summary JSON. Packets combine the case taxonomy, missing workbook
   fields, required manuscript source-root refs, and advisory OEP / pilot refs;
   they are review aids only and do not mutate source rows.

   To start with a guarded one-case-per-regime source-review slice, run:

   ```bash
   make export-manuscript-source-review-slice
   ```

   This writes `data/results/manuscript_source_review_slice.csv` and `.json`.
   The slice is deliberately incomplete: it leaves fillable review fields empty
   and must be merged into the full 64-row reviewed workbook before import.

   After filling the slice, save it as
   `data/results/manuscript_source_review_slice.reviewed.csv` and run:

   ```bash
   make validate-manuscript-source-review-slice
   ```

   If validation passes, merge it into a full workbook scaffold:

   ```bash
   make merge-manuscript-source-review-slice
   ```

   This writes
   `data/results/manuscript_source_review_workbook.merged_from_slice.csv`.
   The merge output remains an authoring aid; source-root import still requires
   all 64 rows to pass the strict workbook importer.

   Then build the row-level intake report:

   ```bash
   make build-manuscript-evidence-intake
   ```

   This writes `data/results/manuscript_evidence_intake.json`, classifying each
   template row as `needs_source`, `needs_annotation`, `ready`, or `blocked`.
   Treat `needs_source` rows as the authoring queue; do not create a reviewed
   source file until row-level source refs, provenance notes, and container
   flags are complete.
   Once `data/cases/manuscript_case_sources.reviewed.jsonl` exists, the Make
   target switches intake to the reviewed source rows and should show
   `needs_annotation` for all source-reviewed but unlabelled rows.
   To export that queue in a human-editable form, run:

   ```bash
   make export-manuscript-evidence-workqueue
   ```

   This writes `data/results/manuscript_evidence_workqueue.csv` and
   `data/results/manuscript_evidence_workqueue.jsonl`. These files are
   authoring aids for source review; each row includes `review_packet_path`
   linking to the per-case packet that should be used while filling source
   refs, provenance notes, and flags. They are not inputs to the strict
   manuscript package gate until reviewed rows are copied back into
   `data/cases/manuscript_case_sources.reviewed.jsonl`.
   After source review, save the filled workqueue as
   `data/results/manuscript_evidence_workqueue.reviewed.csv` and run:

   ```bash
   make import-manuscript-evidence-workqueue
   ```

   The importer validates all 64 rows against the original template, rejects
   placeholder refs and container flags, requires `reviewer_id` and
   `reviewed_at`, and writes `data/cases/manuscript_case_sources.reviewed.jsonl`
   only when the reviewed workqueue is valid.

2. Build the manuscript case file at `data/cases/manuscript_cases.unadjudicated.jsonl`.
   The file should preserve the eight-regime, eight-degradation, and
   eight-question-family coverage already exercised by the draft scaffold, but
   each case must be backed by reviewed non-fixture evidence.
   Once the reviewed source rows have been saved as
   `data/cases/manuscript_case_sources.reviewed.jsonl`, run:

   ```bash
   make convert-manuscript-case-sources
   ```

   The converter refuses to write `manuscript_cases.unadjudicated.jsonl` while
   rows remain marked `requires_non_fixture_evidence`, while source-reference
   slots are empty, or while container flags still contain placeholders.

3. Write deterministic construction-derived oracle labels in
   `data/annotations/manuscript_annotations.jsonl` and promoted manuscript
   cases in `data/cases/manuscript_cases.jsonl`:

   ```bash
   make write-manuscript-construction-oracle
   ```

   The target computes each property category from the case
   `degradation_condition` using the versioned rule spec at
   `data/oracle/construction_oracle_v1.yaml`. It keeps two mechanical oracle
   passes to preserve calibration and adjudication mechanics, but the metadata
   marks the output as `construction_oracle_v1`; do not describe it as human
   annotation or LLM judgement. The command writes the oracle spec SHA-256 plus
   input/output hashes into `data/results/manuscript_construction_oracle.json`.
   It refuses to overwrite existing annotation or case outputs unless run with
   `MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE=1`.

   If the label policy is intentionally changed away from construction rules,
   start from the guarded annotation workbook:

   ```bash
   make export-manuscript-annotation-workbook
   ```

   This writes `data/results/manuscript_annotation_workbook.csv` and `.jsonl`
   with one row per case, property, and annotator. The exported rows use
   `annotation_status=todo` and `category=__SELECT_CATEGORY__`; they are not
   importable until both annotator passes are filled. Save the completed file
   as `data/results/manuscript_annotation_workbook.reviewed.csv` and import it:

   To work incrementally, export a guarded slice:

   ```bash
   make export-manuscript-annotation-slice
   ```

   The default slice selects one case per regime and includes the full
   two-annotator, eight-property grid for each selected case. Save the filled
   slice as `data/results/manuscript_annotation_slice.reviewed.csv`, then run:

   ```bash
   make validate-manuscript-annotation-slice
   make merge-manuscript-annotation-slice
   ```

   The merge output is
   `data/results/manuscript_annotation_workbook.merged_from_slice.csv`; it
   remains an authoring aid and is not imported automatically.

   ```bash
   make import-manuscript-annotation-workbook
   ```

   The importer writes `data/annotations/manuscript_annotations.jsonl` only if
   all 1024 workbook rows are marked `annotation_status=annotated`, use valid
   property categories, cover exactly two annotators, and preserve the
   case/property grid.

4. Run calibration and review:

   ```bash
   make calibrate-manuscript-labels

   make review-manuscript-labels
   ```

5. If using construction oracle labels, `data/cases/manuscript_cases.jsonl` is
   already written by `make write-manuscript-construction-oracle`. If using a
   non-oracle annotation policy, adjudicate disagreements into
   `data/cases/manuscript_cases.jsonl`:

   ```bash
   make write-manuscript-adjudication-overrides-template
   make adjudicate-manuscript-labels
   ```

   Omit `--overrides` only when the label review shows no unresolved
   disagreements.

6. Produce candidate scorer outputs at
   `data/scorers/decision_trace_reconstructor_outputs.jsonl`:

   ```bash
   make write-manuscript-deterministic-scorer
   ```

   The target first writes the scorer-facing redacted input with
   `make write-manuscript-scorer-input`; this creates
   `data/cases/manuscript_scorer_input_cases.jsonl` plus the private
   `data/cases/manuscript_scorer_input_case_id_map.jsonl`. It then applies
   deterministic property rules to visible redacted fields only and maps the
   outputs back to original case IDs through the private map. These outputs are
   not human labels, LLM judgements, or construction-oracle label generation.

   If the protocol intentionally switches to an external Decision Trace
   Reconstructor run, export `data/results/manuscript_scorer_workbook.csv` with
   `make export-manuscript-scorer-workbook`, save the reviewed run as
   `data/results/manuscript_scorer_workbook.reviewed.csv`, then run
   `make import-manuscript-scorer-workbook`. The workbook must keep the
   redacted `case-000001` identifiers and redaction metadata; the importer maps
   them back to original case IDs through the private map.

7. Optional: produce pinned LLM-judge baseline outputs at
   `data/baselines/llm_judge_outputs.jsonl`. First add `llm_judge` to
   `MANUSCRIPT_BASELINES`. Then export
   `data/results/manuscript_llm_judge_workbook.csv` with
   `make export-manuscript-llm-judge-workbook`, save the reviewed prompt run as
   `data/results/manuscript_llm_judge_workbook.reviewed.csv`, then run
   `make import-manuscript-llm-judge-workbook`. This path uses the same
   redacted scorer-input cases and private ID map. The default no-human package
   does not require this artifact.

7a. Audit scorer-facing artifacts for obvious oracle leakage:

   ```bash
   make audit-manuscript-label-leakage
   ```

   This writes `data/results/manuscript_label_leakage_audit.json`. It should
   pass before Section 7 uses scorer or LLM-judge outputs. A failure means that
   scorer-facing rows expose `degradation_condition`, embedded property labels,
   original case IDs, or degradation-condition tokens in source refs and should
   be regenerated from the redacted scorer-input path.

8. Promote `data/corpus/manuscript_corpus.template.yaml` to
   `data/corpus/manuscript_corpus.yaml` only after the referenced files exist
   and have passed review:

   ```bash
   make write-manuscript-corpus-manifest
   ```

   The target refuses to write the corpus manifest until adjudicated cases,
   annotation JSONL, and candidate scorer JSONL exist. It requires LLM-judge
   JSONL only when `llm_judge` is included in `MANUSCRIPT_BASELINES`.

9. Build, validate, and export the manuscript package with the strict gate:

   ```bash
   make verify-manuscript-package
   ```

   To inspect blockers before running the strict package target, run:

   ```bash
   make manuscript-authoring-status
   ```

   This writes `data/results/manuscript_authoring_status.json` and does not
   create result artifacts.

   The target first runs `check-manuscript-inputs`, writing
   `data/results/manuscript_input_preflight.json` and stopping before package
   assembly if any required input is absent. It uses these default inputs:

   - `data/corpus/manuscript_corpus.yaml`
   - `data/cases/manuscript_cases.jsonl`
   - `data/annotations/manuscript_annotations.jsonl`
   - `data/scorers/decision_trace_reconstructor_outputs.jsonl`
   - optional `data/baselines/llm_judge_outputs.jsonl` when `llm_judge` is
     selected

   It includes `data/annotations/manuscript_adjudication_overrides.jsonl`
   automatically when that file exists. Override any path with the matching
   `MANUSCRIPT_*` Make variable when needed.

   The equivalent explicit package command is:

   ```bash
   decision-evidence-benchmark build-result-package \
     --corpus-manifest data/corpus/manuscript_corpus.yaml \
     --cases data/cases/manuscript_cases.jsonl \
     --annotations data/annotations/manuscript_annotations.jsonl \
     --scorer-predictions data/scorers/decision_trace_reconstructor_outputs.jsonl \
     --baseline trace_present \
     --baseline ledger_present \
     --baseline schema_present \
     --baseline container_checklist \
     --baseline source_specific_validator \
     --out-dir data/results \
     --prefix manuscript \
     --run-claim-status manuscript_result_candidate \
     --fail-on-blockers
   ```

10. The equivalent explicit validation and export commands are:

   ```bash
   decision-evidence-benchmark validate-result-package \
     --manifest data/results/manuscript_package_manifest.json \
     --out data/results/manuscript_package_validation.json

   decision-evidence-benchmark export-manuscript-tables \
     --package-manifest data/results/manuscript_package_manifest.json \
     --out-dir data/results \
     --prefix manuscript
   ```

Only after the strict package command and validation/export commands pass
without manuscript blockers should Paper24 Section 7 use the exported tables.
