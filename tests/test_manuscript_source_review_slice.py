import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

INIT_SCRIPT = Path("scripts/init_manuscript_evidence_source.py")
SCRIPT = Path("scripts/export_manuscript_source_review_slice.py")


def test_export_source_review_slice_selects_one_case_per_regime(
    tmp_path: Path,
) -> None:
    source_root = _initialized_source_root(tmp_path, row_count=3)
    packet_index = tmp_path / "packet_index.csv"
    csv_out = tmp_path / "slice.csv"
    summary = tmp_path / "slice.json"
    _write_packet_index(packet_index, template_rows()[:3])

    result = _run_export(source_root, packet_index, csv_out, summary, "--slice-size", "2")

    rows = list(csv.DictReader(csv_out.open()))
    payload = json.loads(summary.read_text())
    assert result.returncode == 0
    assert len(rows) == 2
    assert [row["regime"] for row in rows] == ["aer", "mat"]
    assert rows[0]["packet_path"].endswith(".md")
    assert rows[0]["review_status"] == ""
    assert rows[0]["native_evidence_refs"] == ""
    assert rows[0]["trace_present"] == ""
    assert rows[0]["slice_status"] == "source_review_slice_not_importable"
    assert payload["slice_strategy"] == "one_per_regime"
    assert payload["selected_case_count"] == 2
    assert "not a complete 64-row reviewed workbook" in payload["result_honesty"]


def test_export_source_review_slice_preserves_explicit_case_order(
    tmp_path: Path,
) -> None:
    source_root = _initialized_source_root(tmp_path, row_count=3)
    packet_index = tmp_path / "packet_index.csv"
    csv_out = tmp_path / "slice.csv"
    summary = tmp_path / "slice.json"
    rows = template_rows()[:3]
    _write_packet_index(packet_index, rows)

    result = _run_export(
        source_root,
        packet_index,
        csv_out,
        summary,
        "--case-id",
        rows[2]["case_id"],
        "--case-id",
        rows[0]["case_id"],
    )

    slice_rows = list(csv.DictReader(csv_out.open()))
    payload = json.loads(summary.read_text())
    assert result.returncode == 0
    assert [row["case_id"] for row in slice_rows] == [
        rows[2]["case_id"],
        rows[0]["case_id"],
    ]
    assert payload["slice_strategy"] == "explicit_case_ids"
    assert payload["selected_regime_count"] == 2


def _initialized_source_root(tmp_path: Path, *, row_count: int) -> Path:
    template = tmp_path / "template.jsonl"
    source_root = tmp_path / "source_root"
    rows = template_rows()[:row_count]
    template.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    result = subprocess.run(
        [
            sys.executable,
            str(INIT_SCRIPT),
            "--template",
            str(template),
            "--source-root",
            str(source_root),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return source_root


def _write_packet_index(path: Path, source_rows: list[dict[str, object]]) -> None:
    rows = [
        {
            "row_index": str(index + 1),
            "case_id": str(row["case_id"]),
            "regime": str(row["regime"]),
            "degradation_condition": str(row["degradation_condition"]),
            "question_family": str(row["question_family"]),
            "packet_path": str(path.parent / f"packet_{index + 1}.md"),
            "template_status": "requires_non_fixture_evidence",
            "review_status": "todo",
            "missing_source_fields": "native_evidence_refs",
            "missing_container_flags": "trace_present",
            "missing_review_fields": "review_status",
            "required_candidate_ref_count": "2",
            "advisory_ref_count": "23",
            "candidate_ref_count": "25",
        }
        for index, row in enumerate(source_rows)
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _run_export(
    source_root: Path,
    packet_index: Path,
    csv_out: Path,
    summary: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(source_root),
            "--packet-index",
            str(packet_index),
            "--csv-out",
            str(csv_out),
            "--summary",
            str(summary),
            *extra_args,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
