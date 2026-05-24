"""Write deterministic construction-oracle manuscript labels and cases."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.construction_oracle import (
    CONSTRUCTION_ORACLE_ANNOTATOR_IDS,
    DEFAULT_ORACLE_SPEC_PATH,
    ConstructionOracleSpec,
    labels_for_case,
    load_oracle_spec,
    oracle_spec_sha256,
    rule_id_for_degradation,
)
from decision_evidence_benchmark.io import read_cases_jsonl, write_cases_jsonl, write_jsonl
from decision_evidence_benchmark.labels.adjudication import adjudicate_cases
from decision_evidence_benchmark.labels.calibration import AnnotationRecord, calibration_summary
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_ANNOTATIONS_OUT = ROOT / "data/annotations/manuscript_annotations.jsonl"
DEFAULT_CASES_OUT = ROOT / "data/cases/manuscript_cases.jsonl"
DEFAULT_REPORT = ROOT / "data/results/manuscript_construction_oracle.json"


def write_construction_oracle(
    *,
    cases_path: Path,
    annotations_out: Path,
    cases_out: Path,
    report_path: Path,
    oracle_spec_path: Path = DEFAULT_ORACLE_SPEC_PATH,
    force: bool = False,
) -> tuple[bool, dict[str, Any]]:
    oracle_spec = load_oracle_spec(oracle_spec_path)
    cases = read_cases_jsonl(cases_path)
    issues = _case_issues(cases, oracle_spec=oracle_spec)
    issues.extend(_output_issues((annotations_out, cases_out), force=force))

    annotations: list[dict[str, Any]] = []
    promoted_cases: list[CaseManifest] = []
    label_adjudication: dict[str, Any] | None = None
    calibration: dict[str, Any] | None = None
    wrote_outputs = False

    if not any(issue["severity"] == "error" for issue in issues):
        annotations = annotation_records(cases, oracle_spec=oracle_spec)
        annotation_models = [AnnotationRecord.from_dict(row) for row in annotations]
        calibration = calibration_summary(cases, annotation_models)
        promoted_cases, label_adjudication = adjudicate_cases(cases, annotation_models)
        promoted_cases = [
            _case_with_oracle_honesty(case, oracle_spec=oracle_spec)
            for case in promoted_cases
        ]

        write_jsonl(annotations_out, annotations)
        write_cases_jsonl(cases_out, promoted_cases)
        wrote_outputs = True

    report = _report(
        cases=cases,
        annotations=annotations,
        promoted_cases=promoted_cases,
        calibration=calibration,
        label_adjudication=label_adjudication,
        cases_path=cases_path,
        annotations_out=annotations_out,
        cases_out=cases_out,
        oracle_spec=oracle_spec,
        oracle_spec_path=oracle_spec_path,
        wrote_outputs=wrote_outputs,
        force=force,
        issues=issues,
    )
    _write_json(report_path, report)
    return bool(report["valid"]), report


def annotation_records(
    cases: list[CaseManifest],
    *,
    oracle_spec: ConstructionOracleSpec | None = None,
) -> list[dict[str, Any]]:
    spec = oracle_spec or load_oracle_spec(DEFAULT_ORACLE_SPEC_PATH)
    records: list[dict[str, Any]] = []
    for case in cases:
        labels = [
            label.to_dict()
            for label in labels_for_case(
                case,
                source=spec.annotation_source,
                spec=spec,
            )
        ]
        for annotator_id in CONSTRUCTION_ORACLE_ANNOTATOR_IDS:
            records.append(
                {
                    "case_id": case.case_id,
                    "annotator_id": annotator_id,
                    "property_labels": labels,
                    "metadata": {
                        "annotation_status": spec.annotation_status,
                        "annotation_source": spec.oracle_version,
                        "annotation_scope": "construction_derived_property_labels",
                        "calibration_status": spec.calibration_status,
                        "case_source_status": case.metadata.get("case_source_status"),
                        "oracle_basis": "degradation_condition",
                        "oracle_rule_id": rule_id_for_degradation(
                            case.degradation_condition,
                            spec=spec,
                        ),
                        "oracle_spec_sha256": oracle_spec_sha256(spec.path),
                        "result_honesty": (
                            "Deterministic construction-derived label record. This is "
                            "not human annotation, not LLM judgement, and not candidate "
                            "scorer output."
                        ),
                    },
                }
            )
    return records


def _case_with_oracle_honesty(
    case: CaseManifest,
    *,
    oracle_spec: ConstructionOracleSpec,
) -> CaseManifest:
    metadata = dict(case.metadata)
    metadata["label_oracle"] = oracle_spec.oracle_version
    metadata["label_basis"] = "degradation_condition"
    metadata["oracle_spec_sha256"] = oracle_spec_sha256(oracle_spec.path)
    metadata["result_honesty"] = (
        "Construction-derived oracle labels from explicit degradation-condition rules. "
        "This artifact is ground-truth label construction, not human annotation, not "
        "LLM judgement, and not candidate scorer output."
    )
    return CaseManifest(
        case_id=case.case_id,
        regime=case.regime,
        question_family=case.question_family,
        degradation_condition=case.degradation_condition,
        evidence=dict(case.evidence),
        container_flags=dict(case.container_flags),
        property_labels=tuple(case.property_labels),
        metadata=metadata,
    )


def _case_issues(
    cases: list[CaseManifest],
    *,
    oracle_spec: ConstructionOracleSpec,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not cases:
        issues.append({"severity": "error", "issue": "empty_case_file"})

    case_ids = [case.case_id for case in cases]
    for case_id, count in Counter(case_ids).items():
        if count > 1:
            issues.append(
                {
                    "severity": "error",
                    "issue": "duplicate_case_id",
                    "case_id": case_id,
                }
            )

    for case in cases:
        try:
            labels_for_case(case, spec=oracle_spec)
        except ValueError as exc:
            issues.append(
                {
                    "severity": "error",
                    "issue": "unsupported_degradation_condition",
                    "case_id": case.case_id,
                    "degradation_condition": case.degradation_condition,
                    "error": str(exc),
                }
            )
    return issues


def _output_issues(paths: tuple[Path, ...], *, force: bool) -> list[dict[str, Any]]:
    if force:
        return []
    return [
        {
            "severity": "error",
            "issue": "output_exists",
            "path": str(path),
            "resolution": (
                "rerun with --force after verifying the existing artifact is safe to replace"
            ),
        }
        for path in paths
        if path.exists()
    ]


def _report(
    *,
    cases: list[CaseManifest],
    annotations: list[dict[str, Any]],
    promoted_cases: list[CaseManifest],
    calibration: dict[str, Any] | None,
    label_adjudication: dict[str, Any] | None,
    cases_path: Path,
    annotations_out: Path,
    cases_out: Path,
    oracle_spec: ConstructionOracleSpec,
    oracle_spec_path: Path,
    wrote_outputs: bool,
    force: bool,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    valid = not any(issue["severity"] == "error" for issue in issues)
    return {
        "artifact_kind": "decision_evidence_manuscript_construction_oracle",
        "valid": valid,
        "oracle_version": oracle_spec.oracle_version,
        "calibration_status": oracle_spec.calibration_status,
        "label_source": oracle_spec.label_source,
        "oracle_spec": str(oracle_spec_path),
        "oracle_spec_sha256": oracle_spec_sha256(oracle_spec_path),
        "cases": str(cases_path),
        "cases_sha256": _sha256_if_exists(cases_path),
        "annotations_out": str(annotations_out),
        "annotations_out_sha256": _sha256_if_exists(annotations_out),
        "cases_out": str(cases_out),
        "cases_out_sha256": _sha256_if_exists(cases_out),
        "force": force,
        "wrote_outputs": wrote_outputs,
        "case_count": len(cases),
        "annotation_record_count": len(annotations),
        "property_count": len(DECISION_EVENT_PROPERTIES),
        "property_label_count": len(promoted_cases) * len(DECISION_EVENT_PROPERTIES),
        "strict_sufficiency_counts": _strict_sufficiency_counts(promoted_cases),
        "degradation_condition_counts": dict(
            sorted(Counter(case.degradation_condition for case in promoted_cases).items())
        ),
        "oracle_rule_counts": _oracle_rule_counts(promoted_cases, oracle_spec=oracle_spec),
        "oracle_rule_table": _oracle_rule_table(oracle_spec),
        "property_category_counts": _property_category_counts(promoted_cases),
        "calibration": calibration,
        "label_adjudication": label_adjudication,
        "issues": issues,
        "result_honesty": (
            "This script derives labels from explicit benchmark-construction rules. "
            "It is intended to remove ad-hoc human or LLM category assignment from "
            "ground-truth construction. It does not run the Decision Trace "
            "Reconstructor and does not create LLM-judge baseline outputs."
        ),
    }


def _strict_sufficiency_counts(cases: list[CaseManifest]) -> dict[str, int]:
    return {
        "sufficient": sum(case.ground_truth_sufficient() for case in cases),
        "insufficient": sum(not case.ground_truth_sufficient() for case in cases),
    }


def _property_category_counts(cases: list[CaseManifest]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for property_name in DECISION_EVENT_PROPERTIES:
        counts[property_name] = dict(
            sorted(
                Counter(
                    label.category
                    for case in cases
                    for label in case.property_labels
                    if label.property == property_name
                ).items()
            )
        )
    return counts


def _oracle_rule_counts(
    cases: list[CaseManifest],
    *,
    oracle_spec: ConstructionOracleSpec,
) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                rule_id_for_degradation(case.degradation_condition, spec=oracle_spec)
                for case in cases
            ).items()
        )
    )


def _oracle_rule_table(oracle_spec: ConstructionOracleSpec) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for degradation_condition, rule in oracle_spec.degradation_conditions.items():
        rows.append(
            {
                "degradation_condition": degradation_condition,
                "rule_id": rule.rule_id,
                "description": rule.description,
                "overrides": dict(sorted(rule.overrides.items())),
            }
        )
    return rows


def _sha256_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def console_summary(report: dict[str, Any], *, report_path: Path) -> dict[str, Any]:
    issues = [issue for issue in report["issues"] if isinstance(issue, dict)]
    return {
        "artifact_kind": report["artifact_kind"],
        "valid": report["valid"],
        "oracle_version": report["oracle_version"],
        "case_count": report["case_count"],
        "annotation_record_count": report["annotation_record_count"],
        "wrote_outputs": report["wrote_outputs"],
        "issue_count": len(issues),
        "issue_counts": dict(
            sorted(Counter(str(issue.get("issue", "")) for issue in issues).items())
        ),
        "report": str(report_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--annotations-out", default=str(DEFAULT_ANNOTATIONS_OUT))
    parser.add_argument("--cases-out", default=str(DEFAULT_CASES_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--oracle-spec", default=str(DEFAULT_ORACLE_SPEC_PATH))
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    valid, report = write_construction_oracle(
        cases_path=Path(args.cases),
        annotations_out=Path(args.annotations_out),
        cases_out=Path(args.cases_out),
        report_path=Path(args.report),
        oracle_spec_path=Path(args.oracle_spec),
        force=bool(args.force),
    )
    print(
        json.dumps(
            console_summary(report, report_path=Path(args.report)),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
