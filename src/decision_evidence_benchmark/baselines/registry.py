"""Container-presence baselines for the benchmark."""

from __future__ import annotations

from collections.abc import Callable

from decision_evidence_benchmark.schema import CaseManifest, ScorerOutput, Verdict

BaselineFn = Callable[[CaseManifest], ScorerOutput]


def _flag(case: CaseManifest, name: str) -> bool:
    return bool(case.container_flags.get(name, False))


def _output(case: CaseManifest, scorer: str, verdict: Verdict, **metadata: object) -> ScorerOutput:
    return ScorerOutput(case_id=case.case_id, scorer=scorer, verdict=verdict, metadata=metadata)


def trace_present(case: CaseManifest) -> ScorerOutput:
    verdict: Verdict = "sufficient" if _flag(case, "trace_present") else "insufficient"
    return _output(case, "trace_present", verdict, predicate="container_flags.trace_present")


def ledger_present(case: CaseManifest) -> ScorerOutput:
    verdict: Verdict = "sufficient" if _flag(case, "ledger_present") else "insufficient"
    return _output(case, "ledger_present", verdict, predicate="container_flags.ledger_present")


def schema_present(case: CaseManifest) -> ScorerOutput:
    verdict: Verdict = "sufficient" if _flag(case, "schema_valid") else "insufficient"
    return _output(case, "schema_present", verdict, predicate="container_flags.schema_valid")


def container_checklist(case: CaseManifest) -> ScorerOutput:
    verdict: Verdict = "sufficient" if _flag(case, "checklist_complete") else "insufficient"
    return _output(
        case,
        "container_checklist",
        verdict,
        predicate="container_flags.checklist_complete",
    )


def source_specific_validator(case: CaseManifest) -> ScorerOutput:
    verdict: Verdict = "sufficient" if _flag(case, "source_validator_passed") else "insufficient"
    return _output(
        case,
        "source_specific_validator",
        verdict,
        predicate="container_flags.source_validator_passed",
    )


def llm_judge(case: CaseManifest) -> ScorerOutput:
    """Fixture-backed placeholder for the LLM-judge baseline.

    The final benchmark must run documented prompts across at least two model
    families. Until then, smoke fixtures may carry a deterministic
    `llm_judge_verdict` field so the runner shape is testable without network
    calls.
    """

    raw = case.container_flags.get("llm_judge_verdict", "abstain")
    if raw not in {"sufficient", "insufficient", "abstain"}:
        raise ValueError(f"invalid llm_judge_verdict for {case.case_id}: {raw}")
    return _output(
        case,
        "llm_judge",
        raw,  # type: ignore[arg-type]
        predicate="container_flags.llm_judge_verdict",
        implementation_status="fixture_placeholder",
    )


BASELINE_REGISTRY: dict[str, BaselineFn] = {
    "trace_present": trace_present,
    "ledger_present": ledger_present,
    "schema_present": schema_present,
    "container_checklist": container_checklist,
    "source_specific_validator": source_specific_validator,
    "llm_judge": llm_judge,
}


def run_baseline(name: str, case: CaseManifest) -> ScorerOutput:
    try:
        baseline = BASELINE_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"unknown baseline: {name}") from exc
    return baseline(case)
