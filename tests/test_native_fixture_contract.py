import json
from pathlib import Path

from decision_evidence_benchmark.adapters.registry import NATIVE_ADAPTERS, adapt_native_record
from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.schema import CaseManifest

NATIVE_FIXTURES = {
    "aegis_ntc": Path("data/cases/aegis_ntc/missing_policy_001.native.json"),
    "aer": Path("data/cases/aer/missing_policy_001.native.json"),
    "dcc_hdp": Path("data/cases/dcc_hdp/missing_policy_001.native.json"),
    "dynamic_capabilities": Path(
        "data/cases/dynamic_capabilities/missing_policy_001.native.json"
    ),
    "ieec": Path("data/cases/ieec/missing_policy_001.native.json"),
    "llm_audit_trails": Path("data/cases/llm_audit_trails/missing_policy_001.native.json"),
    "mat": Path("data/cases/mat/missing_policy_001.native.json"),
    "prov": Path("data/cases/prov/missing_policy_001.native.json"),
}


def test_native_fixture_inventory_matches_registered_adapters() -> None:
    assert set(NATIVE_FIXTURES) == set(NATIVE_ADAPTERS)


def test_native_fixture_adapters_match_smoke_case_manifest_labels() -> None:
    smoke_cases = {
        case.regime: case for case in read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    }

    for regime, fixture_path in NATIVE_FIXTURES.items():
        record = json.loads(fixture_path.read_text())
        case = adapt_native_record(regime, record)
        expected = smoke_cases[regime]

        assert case.case_id == expected.case_id
        assert case.regime == expected.regime
        assert case.question_family == expected.question_family
        assert case.degradation_condition == expected.degradation_condition
        assert case.container_flags == expected.container_flags
        assert _label_categories(case) == _label_categories(expected)


def _label_categories(case: CaseManifest) -> dict[str, str]:
    return {label.property: label.category for label in case.property_labels}
