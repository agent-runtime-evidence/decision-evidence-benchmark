from pathlib import Path

from decision_evidence_benchmark.baselines import run_baseline
from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.metrics.overclaim import (
    OVERCLAIM_SUMMARY_METRIC_CONTRACT,
    result_row,
    summarize_outputs,
)


def test_overclaim_summary_on_smoke_fixture() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    case = cases[0]
    prov_case = cases[1]
    llm_audit_case = cases[2]
    aer_case = cases[3]
    mat_case = cases[4]
    ieec_case = cases[5]
    aegis_ntc_case = cases[6]
    dynamic_capabilities_case = cases[7]
    rows = [
        result_row(case, run_baseline("trace_present", case)),
        result_row(case, run_baseline("container_checklist", case)),
        result_row(prov_case, run_baseline("trace_present", prov_case)),
        result_row(llm_audit_case, run_baseline("trace_present", llm_audit_case)),
        result_row(llm_audit_case, run_baseline("source_specific_validator", llm_audit_case)),
        result_row(aer_case, run_baseline("trace_present", aer_case)),
        result_row(aer_case, run_baseline("source_specific_validator", aer_case)),
        result_row(mat_case, run_baseline("trace_present", mat_case)),
        result_row(mat_case, run_baseline("source_specific_validator", mat_case)),
        result_row(ieec_case, run_baseline("trace_present", ieec_case)),
        result_row(ieec_case, run_baseline("source_specific_validator", ieec_case)),
        result_row(aegis_ntc_case, run_baseline("trace_present", aegis_ntc_case)),
        result_row(aegis_ntc_case, run_baseline("source_specific_validator", aegis_ntc_case)),
        result_row(
            dynamic_capabilities_case,
            run_baseline("trace_present", dynamic_capabilities_case),
        ),
        result_row(
            dynamic_capabilities_case,
            run_baseline("source_specific_validator", dynamic_capabilities_case),
        ),
        result_row(case, run_baseline("llm_judge", case)),
    ]

    summary = summarize_outputs(rows)

    assert summary["metric_contract"] == OVERCLAIM_SUMMARY_METRIC_CONTRACT
    assert rows[0]["ground_truth_sufficient"] is False
    assert rows[0]["overclaim"] is True
    assert rows[1]["overclaim"] is False
    assert rows[2]["overclaim"] is True
    assert rows[3]["overclaim"] is True
    assert rows[4]["overclaim"] is False
    assert rows[5]["overclaim"] is True
    assert rows[6]["overclaim"] is True
    assert rows[7]["overclaim"] is True
    assert rows[8]["overclaim"] is True
    assert rows[9]["overclaim"] is True
    assert rows[10]["overclaim"] is True
    assert rows[11]["overclaim"] is True
    assert rows[12]["overclaim"] is True
    assert rows[13]["overclaim"] is True
    assert rows[14]["overclaim"] is True
    assert summary["scorers"]["trace_present"]["overclaim_rate"] == 1.0
    assert summary["scorers"]["container_checklist"]["overclaim_rate"] == 0.0
    assert summary["scorers"]["llm_judge"]["implementation_statuses"] == {
        "fixture_placeholder": 1
    }
    assert summary["scorers"]["source_specific_validator"]["overclaim_rate"] == 5 / 6
    assert summary["slices"]["regime"]["dcc_hdp"]["trace_present"]["overclaim_rate"] == 1.0
    assert summary["slices"]["regime"]["prov"]["trace_present"]["overclaim_rate"] == 1.0
    assert (
        summary["slices"]["regime"]["llm_audit_trails"]["trace_present"]["overclaim_rate"]
        == 1.0
    )
    assert summary["slices"]["regime"]["aer"]["trace_present"]["overclaim_rate"] == 1.0
    assert (
        summary["slices"]["regime"]["aer"]["source_specific_validator"]["overclaim_rate"]
        == 1.0
    )
    assert summary["slices"]["regime"]["mat"]["trace_present"]["overclaim_rate"] == 1.0
    assert (
        summary["slices"]["regime"]["mat"]["source_specific_validator"]["overclaim_rate"]
        == 1.0
    )
    assert summary["slices"]["regime"]["ieec"]["trace_present"]["overclaim_rate"] == 1.0
    assert (
        summary["slices"]["regime"]["ieec"]["source_specific_validator"]["overclaim_rate"]
        == 1.0
    )
    assert summary["slices"]["regime"]["aegis_ntc"]["trace_present"]["overclaim_rate"] == 1.0
    assert (
        summary["slices"]["regime"]["aegis_ntc"]["source_specific_validator"]["overclaim_rate"]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["dynamic_capabilities"]["trace_present"]["overclaim_rate"]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["dynamic_capabilities"]["source_specific_validator"][
            "overclaim_rate"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["degradation_condition"]["missing_policy"]["trace_present"][
            "overclaim_rate"
        ]
        == 1.0
    )
