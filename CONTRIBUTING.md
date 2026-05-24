# Contributing to DEMM-Bench

Thanks for your interest in DEMM-Bench. This document describes the
contribution workflow, code-style requirements, and review expectations.

## Development Environment

Install the package in editable mode with the dev extras:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Python 3.11, 3.12, 3.13, and 3.14 are supported (see `pyproject.toml`). The
project depends only on the Python standard library and `pyyaml>=6,<7`; the
dev extras add `pytest`, `ruff`, `mypy`, and `types-PyYAML`.

## Running the Test Suite

Run the full verification gate the same way CI does:

```bash
make verify
```

`make verify` runs ruff, mypy strict, pytest, the manifest checksum verifier,
and the smoke-corpus / smoke-package end-to-end pipeline. All targets must
pass before a contribution is reviewed.

## Code Style

- Lines must be 100 characters or fewer (`tool.ruff.line-length = 100`).
- Ruff is the linter (`ruff check src tests scripts`). Selected rules:
  `E`, `F`, `I`, `UP`, `B`. Run `make lint` to apply locally.
- Mypy is run in strict mode (`disallow_untyped_defs = true`,
  `no_implicit_optional = true`). Every function must have full type
  annotations on parameters and return values. Run `make typecheck` locally.
- Imports are organised in three blocks: standard library, third-party,
  first-party (`decision_evidence_benchmark.*`).
- Public API additions must include docstrings.

## Adding a New Evidence Regime

The repository ships eight regime adapters under
`src/decision_evidence_benchmark/adapters/` (`aegis_ntc`, `aer`, `dcc_hdp`,
`dynamic_capabilities`, `ieec`, `llm_audit_trails`, `mat`, `prov`). Each
adapter exposes a `from_native_record(record: dict[str, Any]) -> CaseManifest`
callable and is registered in
`src/decision_evidence_benchmark/adapters/registry.py`. To add a regime:

1. Create `src/decision_evidence_benchmark/adapters/<regime>.py` implementing
   `from_native_record` against the shared `CaseManifest` schema in
   `src/decision_evidence_benchmark/schema.py`.
2. Register the adapter and the regime identifier in `adapters/registry.py`
   (both `REGIME_IDS` and `NATIVE_ADAPTERS`).
3. Add per-regime native fixtures under `data/cases/<regime>/`.
4. Add a `tests/test_adapter_<regime>.py` test module mirroring the existing
   adapter tests.

## Adding a New Baseline

Baselines live in `src/decision_evidence_benchmark/baselines/registry.py` and
follow the `BaselineFn = Callable[[CaseManifest], ScorerOutput]` contract.
Register the new baseline in `BASELINE_REGISTRY` so it is reachable via
`run_baseline(name, case)` and the `--baseline` CLI flag.

## Adding a New Property-Level Scorer

The reference candidate scorer is the redacted property-rule scorer at
`src/decision_evidence_benchmark/deterministic_predictions.py`. Use it as a
template. The scorer must consume only the redacted scorer-facing case rows
plus the private case-id map; it must not read degradation conditions, oracle
labels, or source references. The `label-leakage-audit` target enforces this
contract.

## Determinism Requirement

Contributions to the scoring path must be deterministic. Do not introduce
`random`, system clocks, environment-dependent behaviour, or network calls.
The only place where time-dependent metadata is permitted is
`src/decision_evidence_benchmark/artifacts.py`, where it is isolated and
documented.

## Testing Requirement

Every new module must come with a corresponding `tests/test_<module>.py` file.
New public API must be type-annotated and documented. Mypy strict must pass.
The full test suite must pass on all four supported Python versions.

## Commit Message Conventions

- Use imperative present tense (`add adapter for X`, not `added` or `adds`).
- Reference the impacted module or area where helpful (`baselines:`,
  `adapters/ieec:`, `docs:`).
- Avoid generic messages such as `ref`, `fix`, or `update`.

## Pull Request Review Expectations

- All four CI jobs (Python 3.11, 3.12, 3.13, 3.14) must pass before review.
- Contributions that affect published claims must update both the code and
  the corresponding documentation in `docs/` and `CHANGELOG.md`.
- Changes to manifest-tracked files require an updated `checksums.txt`
  (`make update-checksums`) in the same commit.

## License

By contributing, you agree that your contributions will be licensed under
Apache-2.0 (code) or CC-BY-4.0 (data) as appropriate. See `LICENSE` and
`LICENSE-DATA` for the full terms.
