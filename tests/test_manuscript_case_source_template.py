import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from decision_evidence_benchmark.adapters.registry import REGIME_IDS
from decision_evidence_benchmark.generation import DEGRADATION_CONDITIONS
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES

SCRIPT = Path("scripts/write_manuscript_case_source_template.py")


def test_write_manuscript_case_source_template_covers_required_cells(
    tmp_path: Path,
) -> None:
    out = tmp_path / "case_sources.jsonl"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        capture_output=True,
        check=False,
        text=True,
    )

    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert result.returncode == 0
    assert json.loads(result.stdout)["case_count"] == 64
    assert len(rows) == 64
    assert Counter(row["regime"] for row in rows) == {regime: 8 for regime in REGIME_IDS}
    assert Counter(row["degradation_condition"] for row in rows) == {
        condition: 8 for condition in DEGRADATION_CONDITIONS
    }
    assert Counter(row["question_family"] for row in rows) == {
        property_name: 8 for property_name in DECISION_EVENT_PROPERTIES
    }


def test_manuscript_case_source_template_is_not_promoted_evidence(
    tmp_path: Path,
) -> None:
    out = tmp_path / "case_sources.jsonl"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        capture_output=True,
        check=True,
        text=True,
    )

    row = json.loads(out.read_text().splitlines()[0])
    assert row["template_status"] == "requires_non_fixture_evidence"
    assert row["source_requirements"]["native_evidence_refs"] == []
    assert row["container_flags"]["trace_present"] == "__SET_BOOL__"
    assert {
        label["category"] for label in row["property_label_authoring"]
    } == {"__SELECT_CATEGORY__"}

