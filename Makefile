PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)
BENCH ?= $(if $(wildcard .venv/bin/decision-evidence-benchmark),.venv/bin/decision-evidence-benchmark,decision-evidence-benchmark)
MANUSCRIPT_PREFIX ?= manuscript
MANUSCRIPT_CORPUS ?= data/corpus/manuscript_corpus.yaml
MANUSCRIPT_CASES ?= data/cases/manuscript_cases.jsonl
MANUSCRIPT_CORPUS_TEMPLATE ?= data/corpus/manuscript_corpus.template.yaml
MANUSCRIPT_ANNOTATIONS ?= data/annotations/manuscript_annotations.jsonl
MANUSCRIPT_ADJUDICATION_OVERRIDES ?= data/annotations/manuscript_adjudication_overrides.jsonl
MANUSCRIPT_SCORER_OUTPUTS ?= data/scorers/decision_trace_reconstructor_outputs.jsonl
MANUSCRIPT_LLM_JUDGE_OUTPUTS ?= data/baselines/llm_judge_outputs.jsonl
MANUSCRIPT_BASELINES ?= trace_present ledger_present schema_present container_checklist source_specific_validator
MANUSCRIPT_BASELINE_ARGS = $(foreach baseline,$(MANUSCRIPT_BASELINES),--baseline $(baseline) )
MANUSCRIPT_LLM_JUDGE_PACKAGE_ARG = $(if $(filter llm_judge,$(MANUSCRIPT_BASELINES)),--llm-judge-predictions $(MANUSCRIPT_LLM_JUDGE_OUTPUTS) ,)
MANUSCRIPT_LLM_JUDGE_PREFLIGHT_ARG = $(if $(filter llm_judge,$(MANUSCRIPT_BASELINES)),--required llm_judge_jsonl:$(MANUSCRIPT_LLM_JUDGE_OUTPUTS) --required llm_judge_import_report:$(MANUSCRIPT_LLM_JUDGE_IMPORT_REPORT) ,--optional llm_judge_jsonl:$(MANUSCRIPT_LLM_JUDGE_OUTPUTS) --optional llm_judge_import_report:$(MANUSCRIPT_LLM_JUDGE_IMPORT_REPORT) )
MANUSCRIPT_LLM_JUDGE_MANIFEST_REQUIRED_ARG = $(if $(filter llm_judge,$(MANUSCRIPT_BASELINES)),--required llm_judge_jsonl:$(MANUSCRIPT_LLM_JUDGE_OUTPUTS) ,)
MANUSCRIPT_LLM_JUDGE_STATUS_ARG = $(if $(filter llm_judge,$(MANUSCRIPT_BASELINES)),--include-llm-judge ,)
MANUSCRIPT_ADJUDICATION_OVERRIDES_ARG = $(if $(wildcard $(MANUSCRIPT_ADJUDICATION_OVERRIDES)),--adjudication-overrides $(MANUSCRIPT_ADJUDICATION_OVERRIDES) ,)
MANUSCRIPT_PREFLIGHT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_input_preflight.json
MANUSCRIPT_CASE_SOURCE_TEMPLATE ?= data/cases/manuscript_case_sources.template.jsonl
MANUSCRIPT_EVIDENCE_SOURCE_ROOT ?= data/sources/$(MANUSCRIPT_PREFIX)_corpus
MANUSCRIPT_CASE_SOURCE_REVIEWED ?= data/cases/manuscript_case_sources.reviewed.jsonl
MANUSCRIPT_CASE_SOURCE_INTAKE ?= $(if $(wildcard $(MANUSCRIPT_CASE_SOURCE_REVIEWED)),$(MANUSCRIPT_CASE_SOURCE_REVIEWED),$(MANUSCRIPT_CASE_SOURCE_TEMPLATE))
MANUSCRIPT_UNADJUDICATED_CASES ?= data/cases/manuscript_cases.unadjudicated.jsonl
MANUSCRIPT_CASE_SOURCE_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_case_source_conversion.json
MANUSCRIPT_ANNOTATION_WORKBOOK_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_workbook.csv
MANUSCRIPT_ANNOTATION_WORKBOOK_JSONL ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_workbook.jsonl
MANUSCRIPT_ANNOTATION_WORKBOOK_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_workbook.reviewed.csv
MANUSCRIPT_ANNOTATION_SLICE_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_slice.csv
MANUSCRIPT_ANNOTATION_SLICE_SUMMARY ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_slice.json
MANUSCRIPT_ANNOTATION_SLICE_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_slice.reviewed.csv
MANUSCRIPT_ANNOTATION_SLICE_VALIDATION ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_slice_validation.json
MANUSCRIPT_ANNOTATION_WORKBOOK_MERGED ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_workbook.merged_from_slice.csv
MANUSCRIPT_ANNOTATION_IMPORT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_annotation_import.json
MANUSCRIPT_LABEL_CALIBRATION ?= data/results/$(MANUSCRIPT_PREFIX)_label_calibration.json
MANUSCRIPT_LABEL_REVIEW ?= data/results/$(MANUSCRIPT_PREFIX)_label_review.json
MANUSCRIPT_LABEL_REVIEW_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_label_review.csv
MANUSCRIPT_LABEL_ADJUDICATION ?= data/results/$(MANUSCRIPT_PREFIX)_label_adjudication.json
MANUSCRIPT_ADJUDICATION_OVERRIDES_TEMPLATE ?= data/annotations/$(MANUSCRIPT_PREFIX)_adjudication_overrides.template.jsonl
MANUSCRIPT_ADJUDICATION_CLI_OVERRIDES_ARG = $(if $(wildcard $(MANUSCRIPT_ADJUDICATION_OVERRIDES)),--overrides $(MANUSCRIPT_ADJUDICATION_OVERRIDES) ,)
MANUSCRIPT_CONSTRUCTION_ORACLE_SPEC ?= data/oracle/construction_oracle_v1.yaml
MANUSCRIPT_CONSTRUCTION_ORACLE_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_construction_oracle.json
MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE ?=
MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE_ARG = $(if $(MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE),--force ,)
MANUSCRIPT_DETERMINISTIC_SCORER_FORCE ?=
MANUSCRIPT_DETERMINISTIC_SCORER_FORCE_ARG = $(if $(MANUSCRIPT_DETERMINISTIC_SCORER_FORCE),--force ,)
MANUSCRIPT_SCORER_WORKBOOK_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_scorer_workbook.csv
MANUSCRIPT_SCORER_WORKBOOK_JSONL ?= data/results/$(MANUSCRIPT_PREFIX)_scorer_workbook.jsonl
MANUSCRIPT_SCORER_WORKBOOK_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_scorer_workbook.reviewed.csv
MANUSCRIPT_SCORER_IMPORT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_scorer_import.json
MANUSCRIPT_SCORER_INPUT_CASES ?= data/cases/$(MANUSCRIPT_PREFIX)_scorer_input_cases.jsonl
MANUSCRIPT_SCORER_INPUT_CASE_ID_MAP ?= data/cases/$(MANUSCRIPT_PREFIX)_scorer_input_case_id_map.jsonl
MANUSCRIPT_SCORER_INPUT_REDACTION_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_scorer_input_redaction.json
MANUSCRIPT_LLM_JUDGE_WORKBOOK_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_llm_judge_workbook.csv
MANUSCRIPT_LLM_JUDGE_WORKBOOK_JSONL ?= data/results/$(MANUSCRIPT_PREFIX)_llm_judge_workbook.jsonl
MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_llm_judge_workbook.reviewed.csv
MANUSCRIPT_LLM_JUDGE_IMPORT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_llm_judge_import.json
MANUSCRIPT_AUTHORING_STATUS ?= data/results/$(MANUSCRIPT_PREFIX)_authoring_status.json
MANUSCRIPT_STALE_REVIEWED_ARCHIVE_DIR ?= data/results/$(MANUSCRIPT_PREFIX)_stale_reviewed_workbook_archive
MANUSCRIPT_STALE_REVIEWED_ARCHIVE_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_stale_reviewed_workbook_archive.json
MANUSCRIPT_CORPUS_PROMOTION_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_corpus_manifest_promotion.json
MANUSCRIPT_SOURCE_AUDIT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_source_root_audit.json
MANUSCRIPT_SOURCE_CANDIDATES_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_source_candidates.csv
MANUSCRIPT_SOURCE_CANDIDATES_JSONL ?= data/results/$(MANUSCRIPT_PREFIX)_source_candidates.jsonl
MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_workbook.csv
MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_JSONL ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_workbook.jsonl
MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_workbook.reviewed.csv
MANUSCRIPT_SOURCE_REVIEW_IMPORT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_import.json
MANUSCRIPT_SOURCE_REVIEW_PACKET_DIR ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_packets
MANUSCRIPT_SOURCE_REVIEW_PACKET_INDEX ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_packets.csv
MANUSCRIPT_SOURCE_REVIEW_PACKET_SUMMARY ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_packets.json
MANUSCRIPT_SOURCE_REVIEW_SLICE_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_slice.csv
MANUSCRIPT_SOURCE_REVIEW_SLICE_SUMMARY ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_slice.json
MANUSCRIPT_SOURCE_REVIEW_SLICE_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_slice.reviewed.csv
MANUSCRIPT_SOURCE_REVIEW_SLICE_VALIDATION ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_slice_validation.json
MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_MERGED ?= data/results/$(MANUSCRIPT_PREFIX)_source_review_workbook.merged_from_slice.csv
MANUSCRIPT_EVIDENCE_INTAKE_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_evidence_intake.json
MANUSCRIPT_EVIDENCE_WORKQUEUE_CSV ?= data/results/$(MANUSCRIPT_PREFIX)_evidence_workqueue.csv
MANUSCRIPT_EVIDENCE_WORKQUEUE_JSONL ?= data/results/$(MANUSCRIPT_PREFIX)_evidence_workqueue.jsonl
MANUSCRIPT_EVIDENCE_WORKQUEUE_REVIEWED ?= data/results/$(MANUSCRIPT_PREFIX)_evidence_workqueue.reviewed.csv
MANUSCRIPT_EVIDENCE_WORKQUEUE_IMPORT_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_evidence_workqueue_import.json
MANUSCRIPT_SOURCE_MATERIALIZATION_REPORT ?= data/results/$(MANUSCRIPT_PREFIX)_source_materialization.json
MANUSCRIPT_LABEL_LEAKAGE_AUDIT ?= data/results/$(MANUSCRIPT_PREFIX)_label_leakage_audit.json
MANUSCRIPT_SCORER_WORKBOOK_REVIEWED_ARTIFACT_ARG = $(if $(wildcard $(MANUSCRIPT_SCORER_WORKBOOK_REVIEWED)),--artifact scorer_workbook_reviewed:$(MANUSCRIPT_SCORER_WORKBOOK_REVIEWED) ,)
MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED_ARTIFACT_ARG = $(if $(wildcard $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED)),--artifact llm_judge_workbook_reviewed:$(MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED) ,)
OEP_ROOT ?= ../operational-evidence-plane
PILOT_ROOT ?= ../anchor-level-reconstructability-pilot

.PHONY: verify test lint typecheck verify-manifest validate-smoke-corpus calibrate-smoke-labels review-smoke-labels adjudicate-smoke-labels validate-smoke-scorer evaluate-smoke-scorer generate-draft-corpus write-manuscript-case-source-template init-manuscript-evidence-source materialize-manuscript-source-review audit-manuscript-source-roots audit-manuscript-label-leakage export-manuscript-source-candidates export-manuscript-source-review-workbook export-manuscript-source-review-packets export-manuscript-source-review-slice validate-manuscript-source-review-slice merge-manuscript-source-review-slice import-manuscript-source-review-workbook build-manuscript-evidence-intake export-manuscript-evidence-workqueue import-manuscript-evidence-workqueue convert-manuscript-case-sources export-manuscript-annotation-workbook export-manuscript-annotation-slice validate-manuscript-annotation-slice merge-manuscript-annotation-slice import-manuscript-annotation-workbook write-manuscript-construction-oracle calibrate-manuscript-labels review-manuscript-labels write-manuscript-adjudication-overrides-template adjudicate-manuscript-labels write-manuscript-scorer-input write-manuscript-deterministic-scorer clean-manuscript-stale-reviewed-workbooks export-manuscript-scorer-workbook import-manuscript-scorer-workbook export-manuscript-llm-judge-workbook import-manuscript-llm-judge-workbook manuscript-authoring-status write-manuscript-corpus-manifest build-smoke-package validate-smoke-package export-smoke-manuscript-tables verify-draft-package build-draft-package validate-draft-package export-draft-manuscript-tables check-manuscript-inputs verify-manuscript-package build-manuscript-package validate-manuscript-package export-manuscript-package-tables update-checksums run-smoke readiness-smoke readiness-gaps-smoke clean

verify: lint typecheck test verify-manifest validate-smoke-corpus calibrate-smoke-labels review-smoke-labels adjudicate-smoke-labels validate-smoke-scorer evaluate-smoke-scorer run-smoke readiness-smoke readiness-gaps-smoke build-smoke-package validate-smoke-package export-smoke-manuscript-tables

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests scripts

typecheck:
	$(PYTHON) -m mypy src tests

verify-manifest:
	$(PYTHON) scripts/verify_checksums.py

validate-smoke-corpus:
	$(BENCH) validate-corpus \
		--manifest data/corpus/smoke_corpus.yaml \
		--out data/results/smoke_corpus_validation.json

calibrate-smoke-labels:
	$(BENCH) calibrate-labels \
		--cases data/fixtures/smoke_cases.jsonl \
		--annotations data/annotations/smoke_annotations.jsonl \
		--summary data/results/smoke_label_calibration.json

review-smoke-labels:
	$(BENCH) review-labels \
		--cases data/fixtures/smoke_cases.jsonl \
		--annotations data/annotations/smoke_annotations.jsonl \
		--out data/results/smoke_label_review.json \
		--csv-out data/results/smoke_label_review.csv

adjudicate-smoke-labels:
	$(BENCH) adjudicate-labels \
		--cases data/fixtures/smoke_cases.jsonl \
		--annotations data/annotations/smoke_annotations.jsonl \
		--out-cases data/results/smoke_adjudicated_cases.jsonl \
		--report data/results/smoke_label_adjudication.json

validate-smoke-scorer:
	$(BENCH) validate-scorer-predictions \
		--cases data/fixtures/smoke_cases.jsonl \
		--predictions data/fixtures/smoke_scorer_outputs.jsonl \
		--out data/results/smoke_scorer_validation.json

evaluate-smoke-scorer:
	$(BENCH) evaluate-scorer \
		--cases data/fixtures/smoke_cases.jsonl \
		--predictions data/fixtures/smoke_scorer_outputs.jsonl \
		--out data/results/smoke_scorer_results.jsonl \
		--summary data/results/smoke_scorer_summary.json

generate-draft-corpus:
	$(BENCH) generate-draft-corpus

write-manuscript-case-source-template:
	$(PYTHON) scripts/write_manuscript_case_source_template.py \
		--out $(MANUSCRIPT_CASE_SOURCE_TEMPLATE)

init-manuscript-evidence-source: write-manuscript-case-source-template
	$(PYTHON) scripts/init_manuscript_evidence_source.py \
		--template $(MANUSCRIPT_CASE_SOURCE_TEMPLATE) \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT)

materialize-manuscript-source-review: write-manuscript-case-source-template
	$(PYTHON) scripts/materialize_manuscript_source_review.py \
		--template $(MANUSCRIPT_CASE_SOURCE_TEMPLATE) \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--reviewed-sources $(MANUSCRIPT_CASE_SOURCE_REVIEWED) \
		--source-workbook $(MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_REVIEWED) \
		--evidence-workqueue $(MANUSCRIPT_EVIDENCE_WORKQUEUE_REVIEWED) \
		--report $(MANUSCRIPT_SOURCE_MATERIALIZATION_REPORT)

audit-manuscript-source-roots:
	$(PYTHON) scripts/audit_manuscript_source_roots.py \
		--template $(MANUSCRIPT_CASE_SOURCE_TEMPLATE) \
		--manuscript-source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--oep-root $(OEP_ROOT) \
		--pilot-root $(PILOT_ROOT) \
		--out $(MANUSCRIPT_SOURCE_AUDIT_REPORT)

audit-manuscript-label-leakage: write-manuscript-scorer-input export-manuscript-scorer-workbook export-manuscript-llm-judge-workbook
	$(PYTHON) scripts/audit_manuscript_label_leakage.py \
		--oracle-spec $(MANUSCRIPT_CONSTRUCTION_ORACLE_SPEC) \
		--artifact scorer_input:$(MANUSCRIPT_SCORER_INPUT_CASES) \
		--artifact scorer_workbook:$(MANUSCRIPT_SCORER_WORKBOOK_CSV) \
		$(MANUSCRIPT_SCORER_WORKBOOK_REVIEWED_ARTIFACT_ARG)--artifact llm_judge_workbook:$(MANUSCRIPT_LLM_JUDGE_WORKBOOK_CSV) \
		$(MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED_ARTIFACT_ARG) \
		--out $(MANUSCRIPT_LABEL_LEAKAGE_AUDIT)

export-manuscript-source-candidates: audit-manuscript-source-roots
	$(PYTHON) scripts/export_manuscript_source_candidates.py \
		--audit $(MANUSCRIPT_SOURCE_AUDIT_REPORT) \
		--csv-out $(MANUSCRIPT_SOURCE_CANDIDATES_CSV) \
		--jsonl-out $(MANUSCRIPT_SOURCE_CANDIDATES_JSONL)

export-manuscript-source-review-workbook:
	$(PYTHON) scripts/export_manuscript_source_review_workbook.py \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--csv-out $(MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_CSV) \
		--jsonl-out $(MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_JSONL)

export-manuscript-source-review-packets: export-manuscript-source-candidates
	$(PYTHON) scripts/export_manuscript_source_review_packets.py \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--source-candidates $(MANUSCRIPT_SOURCE_CANDIDATES_CSV) \
		--packet-dir $(MANUSCRIPT_SOURCE_REVIEW_PACKET_DIR) \
		--index-csv $(MANUSCRIPT_SOURCE_REVIEW_PACKET_INDEX) \
		--summary $(MANUSCRIPT_SOURCE_REVIEW_PACKET_SUMMARY)

export-manuscript-source-review-slice: export-manuscript-source-review-packets
	$(PYTHON) scripts/export_manuscript_source_review_slice.py \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--packet-index $(MANUSCRIPT_SOURCE_REVIEW_PACKET_INDEX) \
		--csv-out $(MANUSCRIPT_SOURCE_REVIEW_SLICE_CSV) \
		--summary $(MANUSCRIPT_SOURCE_REVIEW_SLICE_SUMMARY)

validate-manuscript-source-review-slice: export-manuscript-source-review-slice
	$(PYTHON) scripts/merge_manuscript_source_review_slice.py \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--expected-slice $(MANUSCRIPT_SOURCE_REVIEW_SLICE_CSV) \
		--reviewed-slice $(MANUSCRIPT_SOURCE_REVIEW_SLICE_REVIEWED) \
		--report $(MANUSCRIPT_SOURCE_REVIEW_SLICE_VALIDATION)

merge-manuscript-source-review-slice: export-manuscript-source-review-workbook export-manuscript-source-review-slice
	$(PYTHON) scripts/merge_manuscript_source_review_slice.py \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--expected-slice $(MANUSCRIPT_SOURCE_REVIEW_SLICE_CSV) \
		--reviewed-slice $(MANUSCRIPT_SOURCE_REVIEW_SLICE_REVIEWED) \
		--base-workbook $(MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_CSV) \
		--merged-workbook-out $(MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_MERGED) \
		--report $(MANUSCRIPT_SOURCE_REVIEW_SLICE_VALIDATION)

import-manuscript-source-review-workbook:
	$(PYTHON) scripts/import_manuscript_source_review_workbook.py \
		--source-root $(MANUSCRIPT_EVIDENCE_SOURCE_ROOT) \
		--workbook $(MANUSCRIPT_SOURCE_REVIEW_WORKBOOK_REVIEWED) \
		--report $(MANUSCRIPT_SOURCE_REVIEW_IMPORT_REPORT)

build-manuscript-evidence-intake: audit-manuscript-source-roots
	$(PYTHON) scripts/build_manuscript_evidence_intake.py \
		--template $(MANUSCRIPT_CASE_SOURCE_INTAKE) \
		--source-audit $(MANUSCRIPT_SOURCE_AUDIT_REPORT) \
		--out $(MANUSCRIPT_EVIDENCE_INTAKE_REPORT)

export-manuscript-evidence-workqueue: build-manuscript-evidence-intake export-manuscript-source-review-packets
	$(PYTHON) scripts/export_manuscript_evidence_workqueue.py \
		--template $(MANUSCRIPT_CASE_SOURCE_INTAKE) \
		--intake $(MANUSCRIPT_EVIDENCE_INTAKE_REPORT) \
		--packet-index $(MANUSCRIPT_SOURCE_REVIEW_PACKET_INDEX) \
		--csv-out $(MANUSCRIPT_EVIDENCE_WORKQUEUE_CSV) \
		--jsonl-out $(MANUSCRIPT_EVIDENCE_WORKQUEUE_JSONL)

import-manuscript-evidence-workqueue:
	$(PYTHON) scripts/import_manuscript_evidence_workqueue.py \
		--template $(MANUSCRIPT_CASE_SOURCE_TEMPLATE) \
		--workqueue $(MANUSCRIPT_EVIDENCE_WORKQUEUE_REVIEWED) \
		--out $(MANUSCRIPT_CASE_SOURCE_REVIEWED) \
		--report $(MANUSCRIPT_EVIDENCE_WORKQUEUE_IMPORT_REPORT)

convert-manuscript-case-sources:
	$(PYTHON) scripts/convert_manuscript_case_sources.py \
		--sources $(MANUSCRIPT_CASE_SOURCE_REVIEWED) \
		--out $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--report $(MANUSCRIPT_CASE_SOURCE_REPORT)

export-manuscript-annotation-workbook:
	$(PYTHON) scripts/export_manuscript_annotation_workbook.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--csv-out $(MANUSCRIPT_ANNOTATION_WORKBOOK_CSV) \
		--jsonl-out $(MANUSCRIPT_ANNOTATION_WORKBOOK_JSONL)

export-manuscript-annotation-slice: export-manuscript-annotation-workbook
	$(PYTHON) scripts/export_manuscript_annotation_slice.py \
		--workbook $(MANUSCRIPT_ANNOTATION_WORKBOOK_CSV) \
		--csv-out $(MANUSCRIPT_ANNOTATION_SLICE_CSV) \
		--summary $(MANUSCRIPT_ANNOTATION_SLICE_SUMMARY)

validate-manuscript-annotation-slice: export-manuscript-annotation-slice
	$(PYTHON) scripts/merge_manuscript_annotation_slice.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--expected-slice $(MANUSCRIPT_ANNOTATION_SLICE_CSV) \
		--reviewed-slice $(MANUSCRIPT_ANNOTATION_SLICE_REVIEWED) \
		--report $(MANUSCRIPT_ANNOTATION_SLICE_VALIDATION)

merge-manuscript-annotation-slice: export-manuscript-annotation-workbook export-manuscript-annotation-slice
	$(PYTHON) scripts/merge_manuscript_annotation_slice.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--expected-slice $(MANUSCRIPT_ANNOTATION_SLICE_CSV) \
		--reviewed-slice $(MANUSCRIPT_ANNOTATION_SLICE_REVIEWED) \
		--base-workbook $(MANUSCRIPT_ANNOTATION_WORKBOOK_CSV) \
		--merged-workbook-out $(MANUSCRIPT_ANNOTATION_WORKBOOK_MERGED) \
		--report $(MANUSCRIPT_ANNOTATION_SLICE_VALIDATION)

import-manuscript-annotation-workbook:
	$(PYTHON) scripts/import_manuscript_annotation_workbook.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--workbook $(MANUSCRIPT_ANNOTATION_WORKBOOK_REVIEWED) \
		--out $(MANUSCRIPT_ANNOTATIONS) \
		--report $(MANUSCRIPT_ANNOTATION_IMPORT_REPORT)

write-manuscript-construction-oracle:
	$(PYTHON) scripts/write_manuscript_construction_oracle.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--annotations-out $(MANUSCRIPT_ANNOTATIONS) \
		--cases-out $(MANUSCRIPT_CASES) \
		--report $(MANUSCRIPT_CONSTRUCTION_ORACLE_REPORT) \
		--oracle-spec $(MANUSCRIPT_CONSTRUCTION_ORACLE_SPEC) \
		$(MANUSCRIPT_CONSTRUCTION_ORACLE_FORCE_ARG)

calibrate-manuscript-labels:
	$(BENCH) calibrate-labels \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--annotations $(MANUSCRIPT_ANNOTATIONS) \
		--summary $(MANUSCRIPT_LABEL_CALIBRATION)

review-manuscript-labels:
	$(BENCH) review-labels \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--annotations $(MANUSCRIPT_ANNOTATIONS) \
		--out $(MANUSCRIPT_LABEL_REVIEW) \
		--csv-out $(MANUSCRIPT_LABEL_REVIEW_CSV)

write-manuscript-adjudication-overrides-template:
	$(BENCH) write-adjudication-overrides-template \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--annotations $(MANUSCRIPT_ANNOTATIONS) \
		--out $(MANUSCRIPT_ADJUDICATION_OVERRIDES_TEMPLATE)

adjudicate-manuscript-labels:
	$(BENCH) adjudicate-labels \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--annotations $(MANUSCRIPT_ANNOTATIONS) \
		$(MANUSCRIPT_ADJUDICATION_CLI_OVERRIDES_ARG)--out-cases $(MANUSCRIPT_CASES) \
		--report $(MANUSCRIPT_LABEL_ADJUDICATION)

write-manuscript-scorer-input:
	$(PYTHON) scripts/write_manuscript_scorer_input.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--out $(MANUSCRIPT_SCORER_INPUT_CASES) \
		--case-id-map $(MANUSCRIPT_SCORER_INPUT_CASE_ID_MAP) \
		--report $(MANUSCRIPT_SCORER_INPUT_REDACTION_REPORT)

write-manuscript-deterministic-scorer: write-manuscript-scorer-input
	$(PYTHON) scripts/write_manuscript_deterministic_scorer.py \
		--scorer-input $(MANUSCRIPT_SCORER_INPUT_CASES) \
		--case-id-map $(MANUSCRIPT_SCORER_INPUT_CASE_ID_MAP) \
		--out $(MANUSCRIPT_SCORER_OUTPUTS) \
		--report $(MANUSCRIPT_SCORER_IMPORT_REPORT) \
		$(MANUSCRIPT_DETERMINISTIC_SCORER_FORCE_ARG)

clean-manuscript-stale-reviewed-workbooks:
	$(PYTHON) scripts/archive_stale_manuscript_reviewed_workbooks.py \
		--scorer-workbook-reviewed $(MANUSCRIPT_SCORER_WORKBOOK_REVIEWED) \
		--llm-judge-workbook-reviewed $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED) \
		--archive-dir $(MANUSCRIPT_STALE_REVIEWED_ARCHIVE_DIR) \
		--report $(MANUSCRIPT_STALE_REVIEWED_ARCHIVE_REPORT)

export-manuscript-scorer-workbook: write-manuscript-scorer-input
	$(PYTHON) scripts/export_manuscript_scorer_workbook.py \
		--cases $(MANUSCRIPT_SCORER_INPUT_CASES) \
		--csv-out $(MANUSCRIPT_SCORER_WORKBOOK_CSV) \
		--jsonl-out $(MANUSCRIPT_SCORER_WORKBOOK_JSONL)

import-manuscript-scorer-workbook:
	$(PYTHON) scripts/import_manuscript_scorer_workbook.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--workbook $(MANUSCRIPT_SCORER_WORKBOOK_REVIEWED) \
		--case-id-map $(MANUSCRIPT_SCORER_INPUT_CASE_ID_MAP) \
		--out $(MANUSCRIPT_SCORER_OUTPUTS) \
		--report $(MANUSCRIPT_SCORER_IMPORT_REPORT)

export-manuscript-llm-judge-workbook: write-manuscript-scorer-input
	$(PYTHON) scripts/export_manuscript_llm_judge_workbook.py \
		--cases $(MANUSCRIPT_SCORER_INPUT_CASES) \
		--csv-out $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_CSV) \
		--jsonl-out $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_JSONL)

import-manuscript-llm-judge-workbook:
	$(PYTHON) scripts/import_manuscript_llm_judge_workbook.py \
		--cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--workbook $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED) \
		--case-id-map $(MANUSCRIPT_SCORER_INPUT_CASE_ID_MAP) \
		--out $(MANUSCRIPT_LLM_JUDGE_OUTPUTS) \
		--report $(MANUSCRIPT_LLM_JUDGE_IMPORT_REPORT)

manuscript-authoring-status:
	mkdir -p data/results
	$(PYTHON) scripts/manuscript_authoring_status.py \
		--case-source-reviewed $(MANUSCRIPT_CASE_SOURCE_REVIEWED) \
		--unadjudicated-cases $(MANUSCRIPT_UNADJUDICATED_CASES) \
		--case-source-report $(MANUSCRIPT_CASE_SOURCE_REPORT) \
		--annotation-workbook $(MANUSCRIPT_ANNOTATION_WORKBOOK_CSV) \
		--annotation-workbook-reviewed $(MANUSCRIPT_ANNOTATION_WORKBOOK_REVIEWED) \
		--construction-oracle $(MANUSCRIPT_CONSTRUCTION_ORACLE_REPORT) \
		--annotations $(MANUSCRIPT_ANNOTATIONS) \
		--label-calibration $(MANUSCRIPT_LABEL_CALIBRATION) \
		--label-review $(MANUSCRIPT_LABEL_REVIEW) \
		--label-adjudication $(MANUSCRIPT_LABEL_ADJUDICATION) \
		--adjudicated-cases $(MANUSCRIPT_CASES) \
		--scorer-input-redaction $(MANUSCRIPT_SCORER_INPUT_REDACTION_REPORT) \
		--scorer-workbook $(MANUSCRIPT_SCORER_WORKBOOK_CSV) \
		--scorer-workbook-reviewed $(MANUSCRIPT_SCORER_WORKBOOK_REVIEWED) \
		--scorer-outputs $(MANUSCRIPT_SCORER_OUTPUTS) \
		--scorer-import-report $(MANUSCRIPT_SCORER_IMPORT_REPORT) \
		--llm-judge-workbook $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_CSV) \
		--llm-judge-workbook-reviewed $(MANUSCRIPT_LLM_JUDGE_WORKBOOK_REVIEWED) \
		--llm-judge-outputs $(MANUSCRIPT_LLM_JUDGE_OUTPUTS) \
		--llm-judge-import-report $(MANUSCRIPT_LLM_JUDGE_IMPORT_REPORT) \
		--label-leakage-audit $(MANUSCRIPT_LABEL_LEAKAGE_AUDIT) \
		--corpus $(MANUSCRIPT_CORPUS) \
		--preflight-report $(MANUSCRIPT_PREFLIGHT_REPORT) \
		--adjudication-overrides $(MANUSCRIPT_ADJUDICATION_OVERRIDES) \
		$(MANUSCRIPT_LLM_JUDGE_STATUS_ARG) \
		--out $(MANUSCRIPT_AUTHORING_STATUS)

write-manuscript-corpus-manifest:
	mkdir -p data/results
	$(PYTHON) scripts/write_manuscript_corpus_manifest.py \
		--template $(MANUSCRIPT_CORPUS_TEMPLATE) \
		--out $(MANUSCRIPT_CORPUS) \
		--report $(MANUSCRIPT_CORPUS_PROMOTION_REPORT) \
		--required case_manifest_jsonl:$(MANUSCRIPT_CASES) \
		--required annotation_jsonl:$(MANUSCRIPT_ANNOTATIONS) \
		--required scorer_jsonl:$(MANUSCRIPT_SCORER_OUTPUTS) \
		$(MANUSCRIPT_LLM_JUDGE_MANIFEST_REQUIRED_ARG)

verify-draft-package: build-draft-package validate-draft-package export-draft-manuscript-tables

build-smoke-package:
	$(BENCH) build-result-package \
		--corpus-manifest data/corpus/smoke_corpus.yaml \
		--cases data/fixtures/smoke_cases.jsonl \
		--annotations data/annotations/smoke_annotations.jsonl \
		--scorer-predictions data/fixtures/smoke_scorer_outputs.jsonl \
		--out-dir data/results \
		--prefix smoke_package

validate-smoke-package:
	$(BENCH) validate-result-package \
		--manifest data/results/smoke_package_package_manifest.json \
		--out data/results/smoke_package_validation.json

export-smoke-manuscript-tables:
	$(BENCH) export-manuscript-tables \
		--package-manifest data/results/smoke_package_package_manifest.json \
		--out-dir data/results \
		--prefix smoke_package

build-draft-package:
	$(BENCH) build-result-package \
		--corpus-manifest data/corpus/draft_balanced_64_corpus.yaml \
		--cases data/cases/draft_balanced_64_cases.jsonl \
		--annotations data/annotations/draft_balanced_64_annotations.jsonl \
		--scorer-predictions data/scorers/draft_balanced_64_scorer_outputs.jsonl \
		--out-dir data/results \
		--prefix draft_package

validate-draft-package:
	$(BENCH) validate-result-package \
		--manifest data/results/draft_package_package_manifest.json \
		--out data/results/draft_package_validation.json

export-draft-manuscript-tables:
	$(BENCH) export-manuscript-tables \
		--package-manifest data/results/draft_package_package_manifest.json \
		--out-dir data/results \
		--prefix draft_package

check-manuscript-inputs:
	mkdir -p data/results
	$(PYTHON) scripts/check_manuscript_inputs.py \
		--required corpus_manifest:$(MANUSCRIPT_CORPUS) \
		--required case_manifest_jsonl:$(MANUSCRIPT_CASES) \
		--required annotation_jsonl:$(MANUSCRIPT_ANNOTATIONS) \
		--required scorer_jsonl:$(MANUSCRIPT_SCORER_OUTPUTS) \
		--required scorer_input_redaction_report:$(MANUSCRIPT_SCORER_INPUT_REDACTION_REPORT) \
		--required scorer_import_report:$(MANUSCRIPT_SCORER_IMPORT_REPORT) \
		--required label_leakage_audit_report:$(MANUSCRIPT_LABEL_LEAKAGE_AUDIT) \
		$(MANUSCRIPT_LLM_JUDGE_PREFLIGHT_ARG) \
		--optional adjudication_overrides_jsonl:$(MANUSCRIPT_ADJUDICATION_OVERRIDES) \
		--out $(MANUSCRIPT_PREFLIGHT_REPORT)

verify-manuscript-package: write-manuscript-deterministic-scorer audit-manuscript-label-leakage write-manuscript-corpus-manifest check-manuscript-inputs build-manuscript-package validate-manuscript-package export-manuscript-package-tables

build-manuscript-package:
	$(BENCH) build-result-package \
		--corpus-manifest $(MANUSCRIPT_CORPUS) \
		--cases $(MANUSCRIPT_CASES) \
		--annotations $(MANUSCRIPT_ANNOTATIONS) \
		$(MANUSCRIPT_ADJUDICATION_OVERRIDES_ARG)--scorer-predictions $(MANUSCRIPT_SCORER_OUTPUTS) \
		$(MANUSCRIPT_BASELINE_ARGS) \
		$(MANUSCRIPT_LLM_JUDGE_PACKAGE_ARG) \
		--out-dir data/results \
		--prefix $(MANUSCRIPT_PREFIX) \
		--run-claim-status manuscript_result_candidate \
		--fail-on-blockers

validate-manuscript-package:
	$(BENCH) validate-result-package \
		--manifest data/results/$(MANUSCRIPT_PREFIX)_package_manifest.json \
		--out data/results/$(MANUSCRIPT_PREFIX)_package_validation.json

export-manuscript-package-tables:
	$(BENCH) export-manuscript-tables \
		--package-manifest data/results/$(MANUSCRIPT_PREFIX)_package_manifest.json \
		--out-dir data/results \
		--prefix $(MANUSCRIPT_PREFIX)

update-checksums:
	$(PYTHON) scripts/update_checksums.py --write

run-smoke:
	$(BENCH) run \
		--cases data/fixtures/smoke_cases.jsonl \
		--out data/results/smoke_results.jsonl \
		--summary data/results/smoke_summary.json \
		--supporting-input data/results/smoke_corpus_validation.json \
		--supporting-input data/results/smoke_label_calibration.json \
		--supporting-input data/results/smoke_label_review.json \
		--supporting-input data/results/smoke_label_adjudication.json \
		--supporting-input data/results/smoke_scorer_validation.json \
		--supporting-input data/results/smoke_scorer_summary.json \
		--run-manifest data/results/smoke_run_manifest.json

readiness-smoke:
	$(BENCH) readiness-report \
		--corpus-validation data/results/smoke_corpus_validation.json \
		--label-calibration data/results/smoke_label_calibration.json \
		--label-review data/results/smoke_label_review.json \
		--label-adjudication data/results/smoke_label_adjudication.json \
		--scorer-validation data/results/smoke_scorer_validation.json \
		--scorer-summary data/results/smoke_scorer_summary.json \
		--baseline-summary data/results/smoke_summary.json \
		--run-manifest data/results/smoke_run_manifest.json \
		--out data/results/smoke_readiness_report.json

readiness-gaps-smoke:
	$(BENCH) readiness-gaps \
		--readiness-report data/results/smoke_readiness_report.json \
		--out data/results/smoke_readiness_gaps.json

clean:
	rm -f data/results/smoke_results.jsonl data/results/smoke_summary.json \
		data/results/smoke_run_manifest.json data/results/smoke_corpus_validation.json \
		data/results/smoke_label_calibration.json data/results/smoke_scorer_results.jsonl \
		data/results/smoke_label_review.json data/results/smoke_label_review.csv \
		data/results/smoke_adjudicated_cases.jsonl data/results/smoke_label_adjudication.json \
		data/results/smoke_scorer_validation.json data/results/smoke_scorer_summary.json \
		data/results/smoke_readiness_report.json data/results/smoke_readiness_gaps.json \
		data/results/smoke_package_*.json data/results/smoke_package_*.jsonl \
		data/results/smoke_package_*.csv data/results/smoke_package_*.yaml \
		data/results/draft_package_*.json data/results/draft_package_*.jsonl \
		data/results/draft_package_*.csv data/results/draft_package_*.yaml \
		data/results/$(MANUSCRIPT_PREFIX)_*.json \
		data/results/$(MANUSCRIPT_PREFIX)_*.jsonl \
		data/results/$(MANUSCRIPT_PREFIX)_*.csv \
		data/results/$(MANUSCRIPT_PREFIX)_*.yaml
