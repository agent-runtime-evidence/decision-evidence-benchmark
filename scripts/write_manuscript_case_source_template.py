"""Write the 64-cell manuscript case source authoring template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.adapters.registry import REGIME_IDS
from decision_evidence_benchmark.generation import DEGRADATION_CONDITIONS
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES

DEFAULT_OUT = Path("data/cases/manuscript_case_sources.template.jsonl")
TEMPLATE_STATUS = "requires_non_fixture_evidence"


def template_rows(case_count: int = 64) -> list[dict[str, Any]]:
    cycle_size = len(REGIME_IDS) * len(DEGRADATION_CONDITIONS)
    if case_count < cycle_size or case_count % cycle_size != 0:
        raise ValueError(f"case_count must be a positive multiple of {cycle_size}")

    rows: list[dict[str, Any]] = []
    for index in range(case_count):
        regime_index = index % len(REGIME_IDS)
        cycle_index = index // len(REGIME_IDS)
        regime = REGIME_IDS[regime_index]
        degradation_condition = DEGRADATION_CONDITIONS[
            cycle_index % len(DEGRADATION_CONDITIONS)
        ]
        question_family = DECISION_EVENT_PROPERTIES[
            (cycle_index + regime_index) % len(DECISION_EVENT_PROPERTIES)
        ]
        rows.append(
            {
                "case_id": (
                    f"manuscript-{regime}-{degradation_condition}-"
                    f"{question_family}-{index + 1:03d}"
                ),
                "template_status": TEMPLATE_STATUS,
                "regime": regime,
                "degradation_condition": degradation_condition,
                "question_family": question_family,
                "source_requirements": {
                    "native_evidence_refs": [],
                    "reviewed_source_refs": [],
                    "evidence_plane_refs": [],
                    "provenance_notes": "",
                },
                "container_flags": {
                    "trace_present": "__SET_BOOL__",
                    "ledger_present": "__SET_BOOL__",
                    "schema_valid": "__SET_BOOL__",
                    "checklist_complete": "__SET_BOOL__",
                    "source_validator_passed": "__SET_BOOL__",
                    "llm_judge_verdict": "__SET_VERDICT__",
                },
                "property_label_authoring": [
                    {
                        "property": property_name,
                        "category": "__SELECT_CATEGORY__",
                        "required": True,
                        "source": "manuscript_annotation_required",
                        "notes": "",
                    }
                    for property_name in DECISION_EVENT_PROPERTIES
                ],
                "metadata": {
                    "authoring_status": "todo",
                    "result_honesty": (
                        "Template row only. Replace with reviewed non-fixture evidence "
                        "before emitting manuscript_cases JSONL."
                    ),
                },
            }
        )
    return rows


def write_template(path: Path, *, case_count: int = 64) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in template_rows(case_count=case_count):
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--case-count", type=int, default=64)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    write_template(Path(args.out), case_count=int(args.case_count))
    print(
        json.dumps(
            {
                "artifact_kind": "decision_evidence_manuscript_case_source_template",
                "path": str(args.out),
                "case_count": int(args.case_count),
                "template_status": TEMPLATE_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

