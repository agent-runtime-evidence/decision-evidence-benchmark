from pathlib import Path

from decision_evidence_benchmark.corpus import validate_corpus_manifest


def test_smoke_corpus_manifest_validates() -> None:
    summary = validate_corpus_manifest(Path("data/corpus/smoke_corpus.yaml"))

    assert summary["valid"] is True
    assert summary["case_count"] == 8
    assert summary["regime_counts"] == {
        "aegis_ntc": 1,
        "aer": 1,
        "dcc_hdp": 1,
        "dynamic_capabilities": 1,
        "ieec": 1,
        "llm_audit_trails": 1,
        "mat": 1,
        "prov": 1,
    }
    assert summary["question_family_counts"] == {"policy_basis": 8}
    assert summary["degradation_condition_counts"] == {"missing_policy": 8}
    assert summary["strict_sufficiency_counts"] == {"insufficient": 8, "sufficient": 0}
    assert summary["property_category_counts"]["actor_identity"] == {"complete": 8}
    assert summary["property_category_counts"]["policy_basis"] == {"opaque": 8}
    assert summary["property_category_counts"]["principal_authority"] == {
        "complete": 1,
        "opaque": 1,
        "partial": 6,
    }


def test_corpus_validator_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    case_file = tmp_path / "cases.jsonl"
    case_line = Path("data/fixtures/smoke_cases.jsonl").read_text()
    case_file.write_text(case_line + case_line)
    manifest = tmp_path / "corpus.yaml"
    manifest.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "corpus_id: duplicate-check",
                "version: 0.0.0-test",
                "claim_status: test_only",
                "expected_regimes:",
                "  - dcc_hdp",
                "case_files:",
                f"  - path: {case_file}",
                "    regime: dcc_hdp",
                "    role: case_manifest_jsonl",
                "label_contract:",
                "  mode: embedded_property_labels",
                "",
            ]
        )
    )

    summary = validate_corpus_manifest(manifest)

    assert summary["valid"] is False
    assert any(issue["issue"] == "duplicate_case_id" for issue in summary["issues"])
