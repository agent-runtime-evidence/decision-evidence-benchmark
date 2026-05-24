import json
from pathlib import Path

import pytest

from decision_evidence_benchmark.adapters.registry import (
    NATIVE_ADAPTERS,
    REGIME_IDS,
    adapt_native_record,
)


def test_registry_lists_all_target_regimes_and_registered_native_adapters() -> None:
    assert len(REGIME_IDS) == 8
    assert "aegis_ntc" in REGIME_IDS
    assert "aer" in REGIME_IDS
    assert "dcc_hdp" in REGIME_IDS
    assert "dynamic_capabilities" in REGIME_IDS
    assert "ieec" in REGIME_IDS
    assert "llm_audit_trails" in REGIME_IDS
    assert "mat" in REGIME_IDS
    assert "prov" in REGIME_IDS
    assert sorted(NATIVE_ADAPTERS) == [
        "aegis_ntc",
        "aer",
        "dcc_hdp",
        "dynamic_capabilities",
        "ieec",
        "llm_audit_trails",
        "mat",
        "prov",
    ]


def test_registry_dispatches_dcc_hdp_adapter() -> None:
    record = json.loads(Path("data/cases/dcc_hdp/missing_policy_001.native.json").read_text())
    case = adapt_native_record("dcc_hdp", record)

    assert case.case_id == "smoke-dcc-missing-policy-001"
    assert case.regime == "dcc_hdp"


def test_registry_dispatches_prov_adapter() -> None:
    record = json.loads(Path("data/cases/prov/missing_policy_001.native.json").read_text())
    case = adapt_native_record("prov", record)

    assert case.case_id == "smoke-prov-missing-policy-001"
    assert case.regime == "prov"


def test_registry_dispatches_llm_audit_trails_adapter() -> None:
    record = json.loads(
        Path("data/cases/llm_audit_trails/missing_policy_001.native.json").read_text()
    )
    case = adapt_native_record("llm_audit_trails", record)

    assert case.case_id == "smoke-llm-audit-missing-policy-001"
    assert case.regime == "llm_audit_trails"


def test_registry_dispatches_aer_adapter() -> None:
    record = json.loads(Path("data/cases/aer/missing_policy_001.native.json").read_text())
    case = adapt_native_record("aer", record)

    assert case.case_id == "smoke-aer-missing-policy-001"
    assert case.regime == "aer"


def test_registry_dispatches_mat_adapter() -> None:
    record = json.loads(Path("data/cases/mat/missing_policy_001.native.json").read_text())
    case = adapt_native_record("mat", record)

    assert case.case_id == "smoke-mat-missing-policy-001"
    assert case.regime == "mat"


def test_registry_dispatches_ieec_adapter() -> None:
    record = json.loads(Path("data/cases/ieec/missing_policy_001.native.json").read_text())
    case = adapt_native_record("ieec", record)

    assert case.case_id == "smoke-ieec-missing-policy-001"
    assert case.regime == "ieec"


def test_registry_dispatches_aegis_ntc_adapter() -> None:
    record = json.loads(Path("data/cases/aegis_ntc/missing_policy_001.native.json").read_text())
    case = adapt_native_record("aegis_ntc", record)

    assert case.case_id == "smoke-aegis-ntc-missing-policy-001"
    assert case.regime == "aegis_ntc"


def test_registry_dispatches_dynamic_capabilities_adapter() -> None:
    record = json.loads(
        Path("data/cases/dynamic_capabilities/missing_policy_001.native.json").read_text()
    )
    case = adapt_native_record("dynamic_capabilities", record)

    assert case.case_id == "smoke-dynamic-capabilities-missing-policy-001"
    assert case.regime == "dynamic_capabilities"


def test_registry_rejects_unimplemented_regime() -> None:
    with pytest.raises(ValueError, match="no native adapter registered"):
        adapt_native_record("unknown_regime", {})
