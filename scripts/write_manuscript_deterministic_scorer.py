"""Write deterministic no-human candidate scorer outputs for manuscript cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from decision_evidence_benchmark.deterministic_predictions import (
    write_deterministic_property_scorer_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORER_INPUT = ROOT / "data/cases/manuscript_scorer_input_cases.jsonl"
DEFAULT_CASE_ID_MAP = ROOT / "data/cases/manuscript_scorer_input_case_id_map.jsonl"
DEFAULT_OUT = ROOT / "data/scorers/decision_trace_reconstructor_outputs.jsonl"
DEFAULT_REPORT = ROOT / "data/results/manuscript_scorer_import.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorer-input", default=str(DEFAULT_SCORER_INPUT))
    parser.add_argument("--case-id-map", default=str(DEFAULT_CASE_ID_MAP))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    valid, report = write_deterministic_property_scorer_outputs(
        scorer_input_path=Path(args.scorer_input),
        case_id_map_path=Path(args.case_id_map),
        out_path=Path(args.out),
        report_path=Path(args.report),
        force=bool(args.force),
    )
    print(
        json.dumps(
            {
                "artifact_kind": report["artifact_kind"],
                "valid": report["valid"],
                "case_count": report["case_count"],
                "output_count": report["output_count"],
                "implementation_status": report["implementation_status"],
                "wrote_outputs": report["wrote_outputs"],
                "issue_count": len(report["issues"]),
                "report": str(Path(args.report)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
