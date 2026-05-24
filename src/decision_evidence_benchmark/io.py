"""JSONL helpers for benchmark cases and outputs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, ScorerOutput


def read_cases_jsonl(path: Path) -> list[CaseManifest]:
    cases: list[CaseManifest] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                cases.append(CaseManifest.from_dict(json.loads(stripped)))
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: invalid case record") from exc
    return cases


def read_scorer_outputs_jsonl(path: Path) -> list[ScorerOutput]:
    outputs: list[ScorerOutput] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                outputs.append(ScorerOutput.from_dict(json.loads(stripped)))
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: invalid scorer output record") from exc
    return outputs


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def write_cases_jsonl(path: Path, cases: Iterable[CaseManifest]) -> None:
    write_jsonl(path, (case.to_dict() for case in cases))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
