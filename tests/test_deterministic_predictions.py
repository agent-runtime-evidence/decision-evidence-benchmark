import json
from pathlib import Path

from decision_evidence_benchmark.deterministic_predictions import (
    DETERMINISTIC_PROPERTY_SCORER_VERSION,
    write_deterministic_property_scorer_outputs,
)


def test_write_deterministic_property_scorer_outputs_from_redacted_rows(
    tmp_path: Path,
) -> None:
    scorer_input = tmp_path / "scorer_input.jsonl"
    case_id_map = tmp_path / "case_id_map.jsonl"
    out = tmp_path / "outputs.jsonl"
    report = tmp_path / "report.json"
    scorer_input.write_text(
        "\n".join(
            [
                json.dumps(_redacted_case("case-000001", trace=True, ledger=True)),
                json.dumps(_redacted_case("case-000002", trace=False, ledger=False)),
            ]
        )
        + "\n"
    )
    case_id_map.write_text(
        "\n".join(
            [
                json.dumps(
                    {"case_id": "case-000001", "original_case_id": "manuscript-case-1"}
                ),
                json.dumps(
                    {"case_id": "case-000002", "original_case_id": "manuscript-case-2"}
                ),
            ]
        )
        + "\n"
    )

    valid, payload = write_deterministic_property_scorer_outputs(
        scorer_input_path=scorer_input,
        case_id_map_path=case_id_map,
        out_path=out,
        report_path=report,
    )

    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert valid is True
    assert payload["valid"] is True
    assert payload["redacted_input"] is True
    assert payload["implementation_status"] == DETERMINISTIC_PROPERTY_SCORER_VERSION
    assert {row["case_id"] for row in rows} == {
        "manuscript-case-1",
        "manuscript-case-2",
    }
    assert {row["metadata"]["model"] for row in rows} == {"none"}
    assert {row["metadata"]["prediction_source"] for row in rows} == {
        "redacted_input_rule_scorer"
    }
    first_categories = {
        prediction["property"]: prediction["category"]
        for prediction in rows[0]["property_predictions"]
    }
    second_categories = {
        prediction["property"]: prediction["category"]
        for prediction in rows[1]["property_predictions"]
    }
    assert first_categories["actor_identity"] == "complete"
    assert first_categories["principal_authority"] == "complete"
    assert second_categories["actor_identity"] == "opaque"
    assert second_categories["principal_authority"] == "opaque"


def test_write_deterministic_property_scorer_outputs_rejects_missing_map(
    tmp_path: Path,
) -> None:
    scorer_input = tmp_path / "scorer_input.jsonl"
    case_id_map = tmp_path / "case_id_map.jsonl"
    out = tmp_path / "outputs.jsonl"
    report = tmp_path / "report.json"
    scorer_input.write_text(json.dumps(_redacted_case("case-000001")) + "\n")
    case_id_map.write_text("")

    valid, payload = write_deterministic_property_scorer_outputs(
        scorer_input_path=scorer_input,
        case_id_map_path=case_id_map,
        out_path=out,
        report_path=report,
    )

    assert valid is False
    assert payload["valid"] is False
    assert not out.exists()
    assert {issue["issue"] for issue in payload["issues"]} == {
        "missing_case_id_map_rows",
        "output_count_mismatch",
    }


def _redacted_case(
    case_id: str,
    *,
    trace: bool = True,
    ledger: bool = True,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "evidence": {
            "evidence_plane": "reviewed_non_fixture",
            "source_ref_counts": {
                "native_evidence_refs": 1,
                "reviewed_source_refs": 1,
                "evidence_plane_refs": 1,
            },
        },
        "container_flags": {
            "trace_present": trace,
            "ledger_present": ledger,
            "schema_valid": True,
            "checklist_complete": True,
            "source_validator_passed": True,
        },
        "metadata": {"case_source_status": "reviewed_non_fixture_evidence"},
    }
