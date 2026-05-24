import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

SCRIPT = Path("scripts/audit_manuscript_source_roots.py")


def test_audit_manuscript_source_roots_reports_scope_blockers(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    template.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")
    manuscript_root = tmp_path / "manuscript-corpus"
    oep_root = tmp_path / "operational-evidence-plane"
    pilot_root = tmp_path / "anchor-level-reconstructability-pilot"
    _write_oep_files(oep_root)
    _write_pilot_files(pilot_root)
    out = tmp_path / "audit.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--manuscript-source-root",
            str(manuscript_root),
            "--oep-root",
            str(oep_root),
            "--pilot-root",
            str(pilot_root),
            "--out",
            str(out),
            "--min-cases",
            "1",
            "--fail-on-blockers",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    assert result.returncode == 1
    assert payload["manuscript_case_source_ready"] is False
    assert payload["template"]["row_count"] == 1
    assert {root["name"] for root in payload["source_roots"]} == {
        "manuscript_corpus_source",
        "operational_evidence_plane",
        "anchor_level_reconstructability_pilot",
    }
    assert {
        blocker["area"] for blocker in payload["promotion_blockers"]
    } == {"manuscript_corpus_source"}
    assert {
        blocker["area"] for blocker in payload["advisory_blockers"]
    } == {"operational_evidence_plane", "anchor_level_reconstructability_pilot"}


def test_audit_manuscript_source_roots_promotes_only_required_source_root(
    tmp_path: Path,
) -> None:
    row = _reviewed_row()
    template = tmp_path / "template.jsonl"
    template.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")
    manuscript_root = tmp_path / "manuscript-corpus"
    _write_ready_manuscript_root(manuscript_root, row)
    oep_root = tmp_path / "operational-evidence-plane"
    pilot_root = tmp_path / "anchor-level-reconstructability-pilot"
    _write_oep_files(oep_root)
    _write_pilot_files(pilot_root)
    out = tmp_path / "audit.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--manuscript-source-root",
            str(manuscript_root),
            "--oep-root",
            str(oep_root),
            "--pilot-root",
            str(pilot_root),
            "--out",
            str(out),
            "--min-cases",
            "1",
            "--fail-on-blockers",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    required_root = next(
        root for root in payload["source_roots"] if root["name"] == "manuscript_corpus_source"
    )
    assert result.returncode == 0
    assert payload["manuscript_case_source_ready"] is True
    assert payload["promotion_blockers"] == []
    assert payload["advisory_blockers"]
    assert required_root["promotion_ready"] is True
    assert required_root["row_audit"]["reviewed_row_count"] == 1


def _write_oep_files(root: Path) -> None:
    files = {
        "README.md": "This is a deterministic code-review demo with mocked LLM behavior.",
        "docs/public_claims.md": "Not production-ready. Not a benchmark.",
        "manifest/examples/code_review_agent_release.v0.json": "{}",
        "events/examples/code_review_agent_step.v0.json": "{}",
        "events/examples/code_review_agent_denied_step.v0.json": "{}",
        "permissions/examples/code_review_tool_permission.v0.json": "{}",
        "permissions/examples/code_review_tool_permission_denied.v0.json": "{}",
        "traces/examples/code_review_agent_trace.v0.json": "{}",
        "traces/examples/code_review_agent_denied_trace.v0.json": "{}",
        "traces/examples/code_review_agent_eval.v0.json": "{}",
        "traces/examples/code_review_agent_denied_eval.v0.json": "{}",
        "playbooks/examples/code_review_reconstruction_packet.v0.json": "{}",
        "playbooks/examples/code_review_denied_reconstruction_packet.v0.json": "{}",
        "integrations/decision-trace-reconstructor/code_review_agent.jsonl": "{}\n",
        "integrations/decision-trace-reconstructor/code_review_agent_denied.jsonl": "{}\n",
    }
    _write_files(root, files)


def _write_pilot_files(root: Path) -> None:
    files = {
        "README.md": (
            "These are not real captured production traces. "
            "Not a corpus benchmark; anchor-sized n=1 per cell."
        ),
        "manifest.yaml": "artefact: {}\n",
        "reference_output.md": "table\n",
        "data/results/bedrock/01_dtr_anchor.report/feasibility.json": "{}",
        "data/results/langsmith/01_dtr_anchor.report/feasibility.json": "{}",
        "data/results/anthropic/01_dtr_anchor.report/feasibility.json": "{}",
        "data/results/openai_agents/01_dtr_anchor.report/feasibility.json": "{}",
        "data/results/otlp/01_dtr_anchor.report/feasibility.json": "{}",
        "data/results/mcp/01_dtr_anchor.report/feasibility.json": "{}",
        "data/results/oep/02_oep_specific.report/feasibility.json": "{}",
        "data/results/oep/02_oep_specific.report/trace.jsonld": "{}",
        "data/results/replit_drop_database/report/feasibility.json": "{}",
    }
    _write_files(root, files)


def _reviewed_row() -> dict[str, object]:
    row = template_rows()[0]
    row["template_status"] = "reviewed_non_fixture_evidence"
    row["source_requirements"] = {
        "native_evidence_refs": ["native:case-001"],
        "reviewed_source_refs": ["review:case-001"],
        "evidence_plane_refs": ["plane:case-001"],
        "provenance_notes": "Reviewed case source.",
    }
    row["container_flags"] = {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": True,
        "source_validator_passed": True,
        "llm_judge_verdict": "sufficient",
    }
    row["metadata"]["reviewer_id"] = "reviewer_1"
    row["metadata"]["reviewed_at"] = "2026-05-25T00:00:00Z"
    return row


def _write_ready_manuscript_root(root: Path, row: dict[str, object]) -> None:
    files = {
        "source_manifest.json": json.dumps(
            {
                "source_scope": "manuscript_corpus_evidence",
                "source_status": "reviewed_non_fixture_evidence",
                "case_source_file": "case_evidence_sources.jsonl",
                "expected_case_count": 1,
            }
        ),
        "case_evidence_sources.jsonl": json.dumps(row, sort_keys=True) + "\n",
    }
    _write_files(root, files)


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative_path, text in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
