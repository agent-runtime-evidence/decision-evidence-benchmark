import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

INIT_SCRIPT = Path("scripts/init_manuscript_evidence_source.py")
SCRIPT = Path("scripts/export_manuscript_source_review_packets.py")


def test_export_source_review_packets_writes_per_case_authoring_packet(
    tmp_path: Path,
) -> None:
    source_root = _initialized_source_root(tmp_path)
    candidates = tmp_path / "candidates.csv"
    packet_dir = tmp_path / "packets"
    index_csv = tmp_path / "packet_index.csv"
    summary_json = tmp_path / "packet_summary.json"
    _write_candidate_csv(candidates)

    result = _run_export(source_root, candidates, packet_dir, index_csv, summary_json)

    index_rows = list(csv.DictReader(index_csv.open()))
    summary = json.loads(summary_json.read_text())
    packet_text = Path(index_rows[0]["packet_path"]).read_text()
    case_id = template_rows()[0]["case_id"]
    assert result.returncode == 0
    assert len(index_rows) == 1
    assert index_rows[0]["case_id"] == case_id
    assert index_rows[0]["required_candidate_ref_count"] == "1"
    assert index_rows[0]["advisory_ref_count"] == "1"
    assert summary["packet_count"] == 1
    assert summary["advisory_ref_count"] == 1
    assert case_id in packet_text
    assert "Regime: `aer`" in packet_text
    assert "`native_evidence_refs`" in packet_text
    assert "`trace_present`: `true` or `false`" in packet_text
    assert "manifest/examples/code_review_agent_release.v0.json" in packet_text
    assert "Source-review packets are authoring aids only" in packet_text


def test_export_source_review_packets_indexes_missing_review_fields(
    tmp_path: Path,
) -> None:
    source_root = _initialized_source_root(tmp_path)
    candidates = tmp_path / "candidates.csv"
    packet_dir = tmp_path / "packets"
    index_csv = tmp_path / "packet_index.csv"
    summary_json = tmp_path / "packet_summary.json"
    _write_candidate_csv(candidates)

    result = _run_export(source_root, candidates, packet_dir, index_csv, summary_json)

    index_row = list(csv.DictReader(index_csv.open()))[0]
    assert result.returncode == 0
    assert "native_evidence_refs" in index_row["missing_source_fields"]
    assert "provenance_notes" in index_row["missing_source_fields"]
    assert "trace_present" in index_row["missing_container_flags"]
    assert "llm_judge_verdict" in index_row["missing_container_flags"]
    assert "review_status" in index_row["missing_review_fields"]
    assert "reviewer_id" in index_row["missing_review_fields"]
    assert "reviewed_at" in index_row["missing_review_fields"]


def _initialized_source_root(tmp_path: Path) -> Path:
    template = tmp_path / "template.jsonl"
    source_root = tmp_path / "source_root"
    template.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")
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


def _write_candidate_csv(path: Path) -> None:
    rows = [
        {
            "source_root": "manuscript_corpus",
            "scope": "manuscript_corpus_evidence_source_template",
            "promotion_ready": "false",
            "source_use": "manuscript_corpus_source_needs_review",
            "candidate_ref": "case_evidence_sources.jsonl",
            "promotion_blockers": "source_scope_not_manuscript_corpus_ready",
            "blocking_indicators": "",
            "review_instruction": "Fill the manuscript-corpus source rows.",
        },
        {
            "source_root": "operational_evidence_plane",
            "scope": "reference_demo_substrate",
            "promotion_ready": "false",
            "source_use": "reference_context_only_until_corpus_scope_exists",
            "candidate_ref": "manifest/examples/code_review_agent_release.v0.json",
            "promotion_blockers": "source_scope_not_manuscript_corpus_ready",
            "blocking_indicators": "README.md: deterministic code-review demo",
            "review_instruction": "Use as background or reproducibility context only.",
        },
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _run_export(
    source_root: Path,
    source_candidates: Path,
    packet_dir: Path,
    index_csv: Path,
    summary: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(source_root),
            "--source-candidates",
            str(source_candidates),
            "--packet-dir",
            str(packet_dir),
            "--index-csv",
            str(index_csv),
            "--summary",
            str(summary),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
