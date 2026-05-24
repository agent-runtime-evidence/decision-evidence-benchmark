"""Canonical benchmark regime identifiers and native adapter dispatch."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from decision_evidence_benchmark.adapters.aegis_ntc import (
    from_native_record as aegis_ntc_from_native_record,
)
from decision_evidence_benchmark.adapters.aer import from_native_record as aer_from_native_record
from decision_evidence_benchmark.adapters.dcc_hdp import (
    from_native_record as dcc_hdp_from_native_record,
)
from decision_evidence_benchmark.adapters.dynamic_capabilities import (
    from_native_record as dynamic_capabilities_from_native_record,
)
from decision_evidence_benchmark.adapters.ieec import from_native_record as ieec_from_native_record
from decision_evidence_benchmark.adapters.llm_audit_trails import (
    from_native_record as llm_audit_trails_from_native_record,
)
from decision_evidence_benchmark.adapters.mat import from_native_record as mat_from_native_record
from decision_evidence_benchmark.adapters.prov import from_native_record as prov_from_native_record
from decision_evidence_benchmark.schema import CaseManifest

REGIME_IDS = (
    "aer",
    "mat",
    "ieec",
    "dcc_hdp",
    "prov",
    "llm_audit_trails",
    "aegis_ntc",
    "dynamic_capabilities",
)

NativeAdapter = Callable[[dict[str, Any]], CaseManifest]

NATIVE_ADAPTERS: dict[str, NativeAdapter] = {
    "aegis_ntc": aegis_ntc_from_native_record,
    "aer": aer_from_native_record,
    "dcc_hdp": dcc_hdp_from_native_record,
    "dynamic_capabilities": dynamic_capabilities_from_native_record,
    "ieec": ieec_from_native_record,
    "llm_audit_trails": llm_audit_trails_from_native_record,
    "mat": mat_from_native_record,
    "prov": prov_from_native_record,
}


def adapt_native_record(regime: str, record: dict[str, Any]) -> CaseManifest:
    try:
        adapter = NATIVE_ADAPTERS[regime]
    except KeyError as exc:
        known = ", ".join(sorted(NATIVE_ADAPTERS))
        message = f"no native adapter registered for {regime!r}; available: {known}"
        raise ValueError(message) from exc
    return adapter(record)
