"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from decision_evidence_benchmark.adapters.registry import NATIVE_ADAPTERS, adapt_native_record
from decision_evidence_benchmark.artifacts import build_run_manifest
from decision_evidence_benchmark.baselines import (
    BASELINE_REGISTRY,
    ImportedBaseline,
    baseline_result_rows,
    validate_imported_baselines,
)
from decision_evidence_benchmark.corpus import validate_corpus_manifest
from decision_evidence_benchmark.evaluation import evaluate_scorer_outputs, validate_scorer_outputs
from decision_evidence_benchmark.generation import (
    DEFAULT_DRAFT_ANNOTATIONS_PATH,
    DEFAULT_DRAFT_CASES_PATH,
    DEFAULT_DRAFT_CORPUS_MANIFEST_PATH,
    DEFAULT_DRAFT_SCORER_OUTPUTS_PATH,
    write_draft_corpus_artifacts,
)
from decision_evidence_benchmark.io import (
    read_cases_jsonl,
    read_scorer_outputs_jsonl,
    write_cases_jsonl,
    write_json,
    write_jsonl,
)
from decision_evidence_benchmark.labels import (
    adjudicate_cases,
    calibration_summary,
    label_review_summary,
    read_adjudication_overrides_jsonl,
    read_annotations_jsonl,
    write_adjudication_override_template_jsonl,
    write_label_review_csv,
)
from decision_evidence_benchmark.manuscript_tables import export_manuscript_tables
from decision_evidence_benchmark.metrics.overclaim import summarize_outputs
from decision_evidence_benchmark.readiness import build_readiness_report
from decision_evidence_benchmark.readiness_gaps import build_readiness_gap_report
from decision_evidence_benchmark.result_package import (
    build_result_package,
    validate_result_package_file,
)


def run_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    baseline_names = tuple(args.baseline or sorted(BASELINE_REGISTRY))
    imported_baselines = _imported_baselines_from_args(args)
    rows = baseline_result_rows(
        cases,
        baseline_names,
        imported_baselines=imported_baselines,
    )

    write_jsonl(Path(args.out), rows)
    write_json(Path(args.summary), summarize_outputs(rows))
    if args.run_manifest:
        write_json(
            Path(args.run_manifest),
            build_run_manifest(
                cases_path=Path(args.cases),
                output_paths=(Path(args.out), Path(args.summary)),
                case_count=len(cases),
                baselines=baseline_names,
                supporting_input_paths=(
                    *(Path(path) for path in args.supporting_input),
                    *(
                        imported.source_path
                        for imported in imported_baselines.values()
                        if imported.source_path
                    ),
                ),
                claim_status=str(args.run_claim_status),
            ),
        )
    return 0


def _imported_baselines_from_args(args: argparse.Namespace) -> dict[str, ImportedBaseline]:
    imported_baselines: dict[str, ImportedBaseline] = {}
    llm_judge_predictions = getattr(args, "llm_judge_predictions", None)
    if llm_judge_predictions:
        path = Path(llm_judge_predictions)
        imported_baselines["llm_judge"] = ImportedBaseline(
            name="llm_judge",
            outputs=tuple(read_scorer_outputs_jsonl(path)),
            source_path=path,
        )
    return imported_baselines


def adapt_dcc_hdp_command(args: argparse.Namespace) -> int:
    record = json.loads(Path(args.input).read_text())
    case = adapt_native_record("dcc_hdp", record)
    write_cases_jsonl(Path(args.out), [case])
    return 0


def adapt_command(args: argparse.Namespace) -> int:
    record = json.loads(Path(args.input).read_text())
    case = adapt_native_record(str(args.regime), record)
    write_cases_jsonl(Path(args.out), [case])
    return 0


def validate_corpus_command(args: argparse.Namespace) -> int:
    summary = validate_corpus_manifest(Path(args.manifest))
    if args.out:
        write_json(Path(args.out), summary)
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 1


def evaluate_scorer_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    outputs = read_scorer_outputs_jsonl(Path(args.predictions))
    evaluation = evaluate_scorer_outputs(cases, outputs)
    write_jsonl(Path(args.out), evaluation["rows"])
    write_json(Path(args.summary), evaluation["summary"])
    return 0 if evaluation["summary"]["valid"] else 1


def validate_scorer_predictions_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    outputs = read_scorer_outputs_jsonl(Path(args.predictions))
    summary = validate_scorer_outputs(
        cases,
        outputs,
        required_scorers=args.required_scorer,
    )
    if args.out:
        write_json(Path(args.out), summary)
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 1


def validate_baseline_predictions_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    predictions_path = Path(args.predictions)
    imported = ImportedBaseline(
        name=str(args.baseline),
        outputs=tuple(read_scorer_outputs_jsonl(predictions_path)),
        source_path=predictions_path,
    )
    summary = validate_imported_baselines(
        cases,
        (str(args.baseline),),
        imported_baselines={str(args.baseline): imported},
    )
    if args.out:
        write_json(Path(args.out), summary)
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 1


def calibrate_labels_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    annotations = read_annotations_jsonl(Path(args.annotations))
    summary = calibration_summary(cases, annotations)
    write_json(Path(args.summary), summary)
    return 0 if summary["valid"] else 1


def review_labels_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    annotations = read_annotations_jsonl(Path(args.annotations))
    review = label_review_summary(cases, annotations)
    write_json(Path(args.out), review)
    if args.csv_out:
        write_label_review_csv(Path(args.csv_out), review)
    return 0 if review["valid"] else 1


def write_adjudication_overrides_template_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    annotations = read_annotations_jsonl(Path(args.annotations))
    review = label_review_summary(cases, annotations)
    write_adjudication_override_template_jsonl(
        Path(args.out),
        review,
        adjudicator_id=str(args.adjudicator_id),
    )
    return 0 if review["valid"] else 1


def adjudicate_labels_command(args: argparse.Namespace) -> int:
    cases = read_cases_jsonl(Path(args.cases))
    annotations = read_annotations_jsonl(Path(args.annotations))
    overrides = (
        read_adjudication_overrides_jsonl(Path(args.overrides)) if args.overrides else []
    )
    adjudicated_cases, report = adjudicate_cases(cases, annotations, overrides)
    write_json(Path(args.report), report)
    if report["valid"] or args.allow_unresolved:
        write_cases_jsonl(Path(args.out_cases), adjudicated_cases)
    return 0 if report["valid"] else 1


def generate_draft_corpus_command(args: argparse.Namespace) -> int:
    paths = write_draft_corpus_artifacts(
        cases_path=Path(args.cases),
        annotations_path=Path(args.annotations),
        scorer_outputs_path=Path(args.scorer_outputs),
        manifest_path=Path(args.manifest),
        case_count=int(args.case_count),
    )
    payload = {
        "cases": str(paths.cases),
        "annotations": str(paths.annotations),
        "scorer_outputs": str(paths.scorer_outputs),
        "manifest": str(paths.manifest),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_result_package_command(args: argparse.Namespace) -> int:
    package_manifest = build_result_package(
        corpus_manifest_path=Path(args.corpus_manifest),
        cases_path=Path(args.cases),
        annotations_path=Path(args.annotations),
        scorer_predictions_path=Path(args.scorer_predictions),
        out_dir=Path(args.out_dir),
        prefix=str(args.prefix),
        baselines=args.baseline,
        run_claim_status=str(args.run_claim_status),
        adjudication_overrides_path=(
            Path(args.adjudication_overrides) if args.adjudication_overrides else None
        ),
        llm_judge_predictions_path=(
            Path(args.llm_judge_predictions) if args.llm_judge_predictions else None
        ),
    )
    print(json.dumps(package_manifest, indent=2, sort_keys=True))
    if args.fail_on_blockers:
        return 0 if package_manifest["manuscript_result_ready"] else 1
    return 0 if package_manifest["mechanics_valid"] else 1


def validate_result_package_command(args: argparse.Namespace) -> int:
    summary = validate_result_package_file(
        Path(args.manifest),
        verify_files=not bool(args.no_verify_files),
    )
    if args.out:
        write_json(Path(args.out), summary)
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 1


def readiness_report_command(args: argparse.Namespace) -> int:
    report = build_readiness_report(
        corpus_validation_path=Path(args.corpus_validation),
        label_calibration_path=Path(args.label_calibration),
        label_review_path=Path(args.label_review) if args.label_review else None,
        label_adjudication_path=(
            Path(args.label_adjudication) if args.label_adjudication else None
        ),
        scorer_validation_path=(
            Path(args.scorer_validation) if args.scorer_validation else None
        ),
        scorer_summary_path=Path(args.scorer_summary),
        baseline_validation_path=(
            Path(args.baseline_validation) if args.baseline_validation else None
        ),
        baseline_summary_path=Path(args.baseline_summary),
        run_manifest_path=Path(args.run_manifest),
        min_cases=int(args.min_cases),
        min_regimes=int(args.min_regimes),
        min_degradation_conditions=int(args.min_degradation_conditions),
        min_question_families=int(args.min_question_families),
        min_cases_per_regime=int(args.min_cases_per_regime),
        min_cases_per_degradation_condition=int(args.min_cases_per_degradation_condition),
        min_cases_per_question_family=int(args.min_cases_per_question_family),
        min_strict_sufficient_cases=int(args.min_strict_sufficient_cases),
        min_strict_insufficient_cases=int(args.min_strict_insufficient_cases),
        min_complete_labels_per_property=int(args.min_complete_labels_per_property),
        min_non_complete_labels_per_property=int(args.min_non_complete_labels_per_property),
        min_label_cohen_kappa=float(args.min_label_cohen_kappa),
        min_label_property_cohen_kappa=float(args.min_label_property_cohen_kappa),
        required_corpus_claim_status=str(args.required_corpus_claim_status),
        required_run_claim_status=str(args.required_run_claim_status),
        required_baselines=args.required_baseline,
        required_candidate_scorers=args.required_candidate_scorer,
        disallowed_baseline_implementation_statuses=(
            args.disallowed_baseline_implementation_status
        ),
        disallowed_candidate_fixture_statuses=args.disallowed_candidate_fixture_status,
        disallowed_label_calibration_statuses=args.disallowed_label_calibration_status,
    )
    write_json(Path(args.out), report)
    if args.fail_on_blockers:
        return 0 if report["manuscript_result_ready"] else 1
    return 0 if report["mechanics_valid"] else 1


def readiness_gaps_command(args: argparse.Namespace) -> int:
    readiness_report = json.loads(Path(args.readiness_report).read_text())
    gap_report = build_readiness_gap_report(readiness_report)
    if args.out:
        write_json(Path(args.out), gap_report)
    else:
        print(json.dumps(gap_report, indent=2, sort_keys=True))
    return 0 if gap_report["valid"] else 1


def export_manuscript_tables_command(args: argparse.Namespace) -> int:
    summary = export_manuscript_tables(
        package_manifest_path=Path(args.package_manifest),
        out_dir=Path(args.out_dir),
        prefix=str(args.prefix) if args.prefix else None,
    )
    if args.summary_out:
        write_json(Path(args.summary_out), summary)
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decision-evidence-benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run deterministic baselines on JSONL cases")
    run.add_argument("--cases", required=True, help="Input case manifest JSONL")
    run.add_argument("--out", required=True, help="Output per-case scorer JSONL")
    run.add_argument("--summary", required=True, help="Output aggregate summary JSON")
    run.add_argument("--run-manifest", help="Optional output manifest with artifact checksums")
    run.add_argument(
        "--supporting-input",
        action="append",
        default=[],
        help="Additional input artifact to checksum in the run manifest; repeatable.",
    )
    run.add_argument(
        "--baseline",
        action="append",
        choices=sorted(BASELINE_REGISTRY),
        help="Baseline to run; repeatable. Defaults to all baselines.",
    )
    run.add_argument(
        "--llm-judge-predictions",
        help=(
            "Optional pinned JSONL outputs for the llm_judge baseline. "
            "When provided, these replace fixture-backed llm_judge outputs."
        ),
    )
    run.add_argument(
        "--run-claim-status",
        default="mechanical_run_only",
        choices=("mechanical_run_only", "manuscript_result_candidate"),
        help=(
            "Claim status to write into the run manifest. Use manuscript_result_candidate "
            "only for audited manuscript-scale runs."
        ),
    )
    run.set_defaults(func=run_command)

    generic_adapt = subparsers.add_parser(
        "adapt",
        help="Convert one native fixture JSON file into case manifest JSONL",
    )
    generic_adapt.add_argument("--regime", required=True, choices=sorted(NATIVE_ADAPTERS))
    generic_adapt.add_argument("--input", required=True, help="Input native fixture")
    generic_adapt.add_argument("--out", required=True, help="Output case manifest JSONL")
    generic_adapt.set_defaults(func=adapt_command)

    adapt = subparsers.add_parser(
        "adapt-dcc-hdp",
        help="Convert one native DCC/HDP fixture JSON file into case manifest JSONL",
    )
    adapt.add_argument("--input", required=True, help="Input native DCC/HDP JSON fixture")
    adapt.add_argument("--out", required=True, help="Output case manifest JSONL")
    adapt.set_defaults(func=adapt_dcc_hdp_command)

    validate_corpus = subparsers.add_parser(
        "validate-corpus",
        help="Validate a corpus manifest and its referenced case files",
    )
    validate_corpus.add_argument("--manifest", required=True, help="Input corpus manifest YAML")
    validate_corpus.add_argument("--out", help="Optional output validation summary JSON")
    validate_corpus.set_defaults(func=validate_corpus_command)

    evaluate_scorer = subparsers.add_parser(
        "evaluate-scorer",
        help="Evaluate property-level scorer predictions against case labels",
    )
    evaluate_scorer.add_argument("--cases", required=True, help="Input case manifest JSONL")
    evaluate_scorer.add_argument("--predictions", required=True, help="Input scorer output JSONL")
    evaluate_scorer.add_argument("--out", required=True, help="Output per-case evaluation JSONL")
    evaluate_scorer.add_argument("--summary", required=True, help="Output aggregate summary JSON")
    evaluate_scorer.set_defaults(func=evaluate_scorer_command)

    validate_scorer = subparsers.add_parser(
        "validate-scorer-predictions",
        help="Validate candidate scorer JSONL coverage and property predictions",
    )
    validate_scorer.add_argument("--cases", required=True, help="Input case manifest JSONL")
    validate_scorer.add_argument("--predictions", required=True, help="Input scorer output JSONL")
    validate_scorer.add_argument("--out", help="Optional output validation summary JSON")
    validate_scorer.add_argument(
        "--required-scorer",
        action="append",
        help=(
            "Scorer that must cover every case; repeatable. "
            "Defaults to decision_trace_reconstructor."
        ),
    )
    validate_scorer.set_defaults(func=validate_scorer_predictions_command)

    validate_baseline = subparsers.add_parser(
        "validate-baseline-predictions",
        help="Validate imported baseline JSONL coverage before metric use",
    )
    validate_baseline.add_argument("--cases", required=True, help="Input case manifest JSONL")
    validate_baseline.add_argument(
        "--baseline",
        required=True,
        choices=sorted(BASELINE_REGISTRY),
        help="Baseline name expected in the prediction JSONL.",
    )
    validate_baseline.add_argument(
        "--predictions",
        required=True,
        help="Input baseline prediction JSONL.",
    )
    validate_baseline.add_argument("--out", help="Optional output validation summary JSON")
    validate_baseline.set_defaults(func=validate_baseline_predictions_command)

    calibrate_labels = subparsers.add_parser(
        "calibrate-labels",
        help="Compute two-annotator calibration diagnostics for property labels",
    )
    calibrate_labels.add_argument("--cases", required=True, help="Input case manifest JSONL")
    calibrate_labels.add_argument("--annotations", required=True, help="Input annotation JSONL")
    calibrate_labels.add_argument(
        "--summary",
        required=True,
        help="Output calibration summary JSON",
    )
    calibrate_labels.set_defaults(func=calibrate_labels_command)

    review_labels = subparsers.add_parser(
        "review-labels",
        help="Write detailed two-annotator label review rows",
    )
    review_labels.add_argument("--cases", required=True, help="Input case manifest JSONL")
    review_labels.add_argument("--annotations", required=True, help="Input annotation JSONL")
    review_labels.add_argument("--out", required=True, help="Output review summary JSON")
    review_labels.add_argument(
        "--csv-out",
        help="Optional output CSV for manual adjudication review.",
    )
    review_labels.set_defaults(func=review_labels_command)

    adjudication_template = subparsers.add_parser(
        "write-adjudication-overrides-template",
        help="Write a fill-in JSONL template for annotation disagreements",
    )
    adjudication_template.add_argument("--cases", required=True, help="Input case manifest JSONL")
    adjudication_template.add_argument(
        "--annotations",
        required=True,
        help="Input annotation JSONL",
    )
    adjudication_template.add_argument("--out", required=True, help="Output template JSONL")
    adjudication_template.add_argument(
        "--adjudicator-id",
        default="",
        help="Optional adjudicator identifier to prefill in template rows.",
    )
    adjudication_template.set_defaults(func=write_adjudication_overrides_template_command)

    adjudicate_labels = subparsers.add_parser(
        "adjudicate-labels",
        help="Promote two-annotator labels into case manifests",
    )
    adjudicate_labels.add_argument("--cases", required=True, help="Input case manifest JSONL")
    adjudicate_labels.add_argument("--annotations", required=True, help="Input annotation JSONL")
    adjudicate_labels.add_argument(
        "--overrides",
        help="Optional adjudication override JSONL for label disagreements.",
    )
    adjudicate_labels.add_argument("--out-cases", required=True, help="Output case JSONL")
    adjudicate_labels.add_argument("--report", required=True, help="Output adjudication report")
    adjudicate_labels.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Write output cases even when unresolved disagreements remain.",
    )
    adjudicate_labels.set_defaults(func=adjudicate_labels_command)

    generate_draft_corpus = subparsers.add_parser(
        "generate-draft-corpus",
        help="Write a balanced draft corpus scaffold for pipeline exercise",
    )
    generate_draft_corpus.add_argument(
        "--cases",
        default=str(DEFAULT_DRAFT_CASES_PATH),
        help="Output draft case manifest JSONL.",
    )
    generate_draft_corpus.add_argument(
        "--annotations",
        default=str(DEFAULT_DRAFT_ANNOTATIONS_PATH),
        help="Output draft two-annotator fixture labels JSONL.",
    )
    generate_draft_corpus.add_argument(
        "--scorer-outputs",
        default=str(DEFAULT_DRAFT_SCORER_OUTPUTS_PATH),
        help="Output draft candidate scorer JSONL.",
    )
    generate_draft_corpus.add_argument(
        "--manifest",
        default=str(DEFAULT_DRAFT_CORPUS_MANIFEST_PATH),
        help="Output draft corpus manifest YAML.",
    )
    generate_draft_corpus.add_argument(
        "--case-count",
        type=int,
        default=64,
        help="Draft case count. Must be a multiple of 64.",
    )
    generate_draft_corpus.set_defaults(func=generate_draft_corpus_command)

    result_package = subparsers.add_parser(
        "build-result-package",
        help="Run the full result-artifact sequence for a corpus",
    )
    result_package.add_argument("--corpus-manifest", required=True)
    result_package.add_argument("--cases", required=True, help="Input case manifest JSONL")
    result_package.add_argument("--annotations", required=True, help="Input annotation JSONL")
    result_package.add_argument(
        "--scorer-predictions",
        required=True,
        help="Input candidate scorer output JSONL.",
    )
    result_package.add_argument(
        "--llm-judge-predictions",
        help=(
            "Optional pinned JSONL outputs for the llm_judge baseline. "
            "When provided, these replace fixture-backed llm_judge outputs."
        ),
    )
    result_package.add_argument(
        "--adjudication-overrides",
        help="Optional adjudication override JSONL for label disagreements.",
    )
    result_package.add_argument("--out-dir", required=True, help="Output directory")
    result_package.add_argument("--prefix", default="benchmark", help="Output filename prefix")
    result_package.add_argument(
        "--baseline",
        action="append",
        choices=sorted(BASELINE_REGISTRY),
        help="Baseline to run; repeatable. Defaults to all baselines.",
    )
    result_package.add_argument(
        "--run-claim-status",
        default="mechanical_run_only",
        choices=("mechanical_run_only", "manuscript_result_candidate"),
        help=(
            "Claim status to write into the run manifest. Use manuscript_result_candidate "
            "only for audited manuscript-scale runs."
        ),
    )
    result_package.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Exit nonzero when the assembled package is not manuscript-ready.",
    )
    result_package.set_defaults(func=build_result_package_command)

    validate_result_package = subparsers.add_parser(
        "validate-result-package",
        help="Validate result package artifact checksums",
    )
    validate_result_package.add_argument("--manifest", required=True)
    validate_result_package.add_argument("--out", help="Optional output validation JSON")
    validate_result_package.add_argument(
        "--no-verify-files",
        action="store_true",
        help="Validate manifest structure without reading referenced artifacts.",
    )
    validate_result_package.set_defaults(func=validate_result_package_command)

    readiness_report = subparsers.add_parser(
        "readiness-report",
        help="Assemble a machine-readable result readiness report",
    )
    readiness_report.add_argument("--corpus-validation", required=True)
    readiness_report.add_argument("--label-calibration", required=True)
    readiness_report.add_argument("--label-review")
    readiness_report.add_argument("--label-adjudication")
    readiness_report.add_argument("--scorer-validation")
    readiness_report.add_argument("--scorer-summary", required=True)
    readiness_report.add_argument("--baseline-validation")
    readiness_report.add_argument("--baseline-summary", required=True)
    readiness_report.add_argument("--run-manifest", required=True)
    readiness_report.add_argument("--out", required=True)
    readiness_report.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Exit nonzero when mechanics pass but manuscript readiness is blocked.",
    )
    readiness_report.add_argument("--min-cases", type=int, default=64)
    readiness_report.add_argument("--min-regimes", type=int, default=8)
    readiness_report.add_argument("--min-degradation-conditions", type=int, default=8)
    readiness_report.add_argument("--min-question-families", type=int, default=8)
    readiness_report.add_argument("--min-cases-per-regime", type=int, default=8)
    readiness_report.add_argument("--min-cases-per-degradation-condition", type=int, default=8)
    readiness_report.add_argument("--min-cases-per-question-family", type=int, default=8)
    readiness_report.add_argument("--min-strict-sufficient-cases", type=int, default=8)
    readiness_report.add_argument("--min-strict-insufficient-cases", type=int, default=8)
    readiness_report.add_argument("--min-complete-labels-per-property", type=int, default=1)
    readiness_report.add_argument("--min-non-complete-labels-per-property", type=int, default=1)
    readiness_report.add_argument("--min-label-cohen-kappa", type=float, default=0.6)
    readiness_report.add_argument("--min-label-property-cohen-kappa", type=float, default=0.6)
    readiness_report.add_argument(
        "--required-corpus-claim-status",
        default="manuscript_result_candidate",
        help="Corpus claim status required for manuscript readiness.",
    )
    readiness_report.add_argument(
        "--required-run-claim-status",
        default="manuscript_result_candidate",
        help="Run manifest claim status required for manuscript readiness.",
    )
    readiness_report.add_argument(
        "--required-baseline",
        action="append",
        choices=sorted(BASELINE_REGISTRY),
        help="Baseline required for manuscript readiness; repeatable. Defaults to all baselines.",
    )
    readiness_report.add_argument(
        "--required-candidate-scorer",
        action="append",
        help=(
            "Candidate scorer required for manuscript readiness; repeatable. "
            "Defaults to decision_trace_reconstructor."
        ),
    )
    readiness_report.add_argument(
        "--disallowed-baseline-implementation-status",
        action="append",
        help=(
            "Baseline implementation status that blocks manuscript readiness; repeatable. "
            "Defaults to fixture_placeholder."
        ),
    )
    readiness_report.add_argument(
        "--disallowed-candidate-fixture-status",
        action="append",
        help=(
            "Candidate scorer fixture status that blocks manuscript readiness; repeatable. "
            "Defaults to draft_synthetic_oracle and smoke_only."
        ),
    )
    readiness_report.add_argument(
        "--disallowed-label-calibration-status",
        action="append",
        help=(
            "Label calibration status that blocks manuscript readiness; repeatable. "
            "Defaults to draft_two_annotator_fixture and smoke_two_annotator_fixture."
        ),
    )
    readiness_report.set_defaults(func=readiness_report_command)

    readiness_gaps = subparsers.add_parser(
        "readiness-gaps",
        help="Explain readiness blockers as actionable manuscript gaps",
    )
    readiness_gaps.add_argument("--readiness-report", required=True)
    readiness_gaps.add_argument("--out", help="Optional output gap report JSON")
    readiness_gaps.set_defaults(func=readiness_gaps_command)

    manuscript_tables = subparsers.add_parser(
        "export-manuscript-tables",
        help="Export package gate, blocker, and artifact tables for manuscript drafting",
    )
    manuscript_tables.add_argument("--package-manifest", required=True)
    manuscript_tables.add_argument("--out-dir", required=True)
    manuscript_tables.add_argument(
        "--prefix",
        help=(
            "Output filename prefix. Defaults to the package manifest stem with "
            "_package_manifest removed."
        ),
    )
    manuscript_tables.add_argument(
        "--summary-out",
        help="Optional JSON summary path. The summary is always written into out-dir too.",
    )
    manuscript_tables.set_defaults(func=export_manuscript_tables_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))
