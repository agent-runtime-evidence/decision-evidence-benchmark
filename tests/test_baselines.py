from pathlib import Path

import pytest

from decision_evidence_benchmark.baselines import (
    IMPORTED_BASELINE_IMPLEMENTATION_STATUS,
    ImportedBaseline,
    baseline_result_rows,
    run_baseline,
    validate_imported_baselines,
)
from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.schema import ScorerOutput


def test_container_baselines_on_smoke_fixture() -> None:
    case = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))[0]

    assert run_baseline("trace_present", case).verdict == "sufficient"
    assert run_baseline("ledger_present", case).verdict == "sufficient"
    assert run_baseline("schema_present", case).verdict == "sufficient"
    assert run_baseline("container_checklist", case).verdict == "insufficient"
    assert run_baseline("source_specific_validator", case).verdict == "sufficient"
    llm_judge_output = run_baseline("llm_judge", case)
    assert llm_judge_output.verdict == "sufficient"
    assert llm_judge_output.metadata["implementation_status"] == "fixture_placeholder"


def test_imported_llm_judge_outputs_replace_fixture_baseline(tmp_path: Path) -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))[:2]
    source_path = tmp_path / "llm_judge_outputs.jsonl"
    imported = ImportedBaseline(
        name="llm_judge",
        outputs=tuple(
            ScorerOutput(
                case_id=case.case_id,
                scorer="llm_judge",
                verdict="insufficient",
            )
            for case in cases
        ),
        source_path=source_path,
    )

    rows = baseline_result_rows(
        cases,
        ("llm_judge",),
        imported_baselines={"llm_judge": imported},
    )

    assert len(rows) == 2
    assert rows[0]["scorer"] == "llm_judge"
    assert rows[0]["verdict"] == "insufficient"
    assert rows[0]["metadata"]["implementation_status"] == (
        IMPORTED_BASELINE_IMPLEMENTATION_STATUS
    )
    assert rows[0]["metadata"]["import_source_path"] == str(source_path)
    validation = validate_imported_baselines(
        cases,
        ("llm_judge",),
        imported_baselines={"llm_judge": imported},
    )
    assert validation["valid"] is True
    assert validation["baselines"]["llm_judge"]["known_cases"] == 2


def test_imported_baseline_outputs_must_cover_selected_cases() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))[:2]
    imported = ImportedBaseline(
        name="llm_judge",
        outputs=(
            ScorerOutput(
                case_id=cases[0].case_id,
                scorer="llm_judge",
                verdict="insufficient",
            ),
        ),
    )

    validation = validate_imported_baselines(
        cases,
        ("llm_judge",),
        imported_baselines={"llm_judge": imported},
    )

    assert validation["valid"] is False
    assert validation["issues"][0]["issue"] == "missing_baseline_cases"
    with pytest.raises(ValueError, match="missing_baseline_cases"):
        baseline_result_rows(
            cases,
            ("llm_judge",),
            imported_baselines={"llm_judge": imported},
        )
