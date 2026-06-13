# Changelog

All notable changes to DEMM-Bench will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Test collection now works under a bare `pytest` invocation: the suite
  imports helpers from `scripts/` as a namespace package, which previously
  resolved only because `make test` runs `python -m pytest` with the
  repository root on `sys.path`; `pythonpath = ["."]` in the pytest config
  makes both invocations equivalent.
- `decision_evidence_benchmark.__version__` now matches the released
  version line (it had stayed at 0.1.0a0), with a test pinning it against
  the installed package metadata.

### Added

- Dependabot configuration for pip dependencies and GitHub Actions.
- `DATASHEET.md` per Gebru et al. (2021) schema (motivation, composition,
  collection process, preprocessing, uses, distribution, maintenance).
- `CITATION.cff` with paper and software citation metadata, ORCID, and
  Zenodo-deposit pointer placeholder.
- `LICENSE-DATA` declaring CC-BY-4.0 for everything under `data/`.
- `CONTRIBUTING.md` describing the contribution workflow and review
  expectations.
- `.github/workflows/ci.yml` minimal continuous integration workflow
  exercising the Python 3.11 / 3.12 / 3.13 / 3.14 matrix declared in
  `pyproject.toml`.
- `tests/test_manuscript_headline_numbers.py` regression test asserting the
  canonical paper headline values (0.75 / 0.50 / 0.5625 / kappa = 1.0).
- Compute-requirements section in `README.md` documenting the "under 60
  seconds per case end-to-end" claim from paper §3.1.

### Changed
- Replaced `LICENSE` placeholder with the full Apache-2.0 license text and
  a dual-licensing notice referencing `LICENSE-DATA`.
- Expanded `make verify` lint scope to include `scripts/` so dev scripts
  stay on the same ruff bar as `src/` and `tests/`.
- `.gitignore` now excludes `scratch_*` and `fill_*` patterns at repo root.
- `adapters/registry.py` import style for `dcc_hdp` aligned with the other
  seven adapters.

### Removed
- Dev-only scratch files at repo root: `scratch_analyze.py`,
  `scratch_patterns.txt`, `fill_slice.py`, `fill_workbook.py`.

### Fixed
- `scripts/update_checksums.py` unused `typing.Any` import.
- `scripts/verify_checksums.py` import-block formatting.

## [0.1.0a0] — 2026-05-25

### Added
- First deterministic 64-case manuscript package, folded against
  construction-oracle ground truth at commit
  `6de6250e92e3102ee24918fb8773ffc59b74708c`.
- Eight evidence-regime adapters: AER, MAT, IEEC, DCC/HDP, PROV, LLM Audit
  Trails, AEGIS-NTC, Dynamic Capabilities.
- Five default deterministic baselines: trace-present, ledger-present,
  schema-present, container-checklist, source-specific-validator. Optional
  sixth (llm-judge) for pinned external outputs.
- Redacted property-rule candidate scorer (v1) over the eight-property
  Decision Event Schema.
- Eight deterministic degradation conditions: complete, missing-delegation,
  missing-policy, missing-context, conflicting-identity, partial-graph,
  final-only, artifact-only.
- Two primary metrics: Property Sufficiency Accuracy (PSA) and Overclaim
  Rate. Secondary metrics: Gap Localization F1, Evidence Strength
  Calibration, Cross-Regime Transfer, Degradation Sensitivity.
- Source-review promotion gate (`scripts/audit_manuscript_source_roots.py`)
  separating authoring packets from reviewed source rows from promoted case
  manifests.
- 178 unit and integration tests; mypy strict; ruff clean.
- `manifest.yaml` package manifest enumerating four input artifacts and
  sixteen output artifacts with SHA-256 hashes in `checksums.txt`.
