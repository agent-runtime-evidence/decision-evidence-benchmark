---
license: cc-by-4.0
language:
- en
pretty_name: DEMM-Bench
tags:
- ai-governance
- benchmark
- agent-runtime
- decision-evidence
- governance-evidence-sufficiency
- overclaim
- assurance-case
size_categories:
- n<1K
task_categories:
- other
configs:
- config_name: manuscript_64
  data_files:
  - split: cases
    path: data/cases/manuscript_scorer_input_cases.jsonl
---

# DEMM-Bench: A Cross-Regime Benchmark for Agent-Runtime Governance-Evidence Sufficiency

DEMM-Bench measures whether the records an agent-runtime system emits — traces, ledgers, provenance graphs, policy logs, delegation tokens, cache events, tool-firewall records — are **sufficient** to answer governance questions about a specific decision, rather than merely **present**. It is a property-level scoring benchmark in the assurance-case tradition, grounded in the Decision Evidence Maturity Model (DEMM).

> This dataset is the artifact mirror of the benchmark described in the accompanying paper, *"DEMM-Bench: A Cross-Regime Benchmark for Agent-Runtime Governance-Evidence Sufficiency."* The canonical code repository is on GitHub and the citable archival deposit is on Zenodo (links below).

## What it measures

The benchmark normalizes records from **eight evidence regimes** through adapters (AER, MAT, IEEC, DCC/HDP, PROV, LLM Audit Trails, AEGIS-NTC, Dynamic Capabilities replay), then asks property-level governance questions over **eight decision properties**:

1. actor identity
2. principal authority
3. action boundary
4. policy basis
5. decision basis
6. data-and-resource touch
7. lifecycle context
8. verification strength

It applies **eight deterministic degradation conditions** (complete, missing-delegation, missing-policy, missing-context, conflicting-identity, partial-graph, final-only, artifact-only) that introduce controlled evidence gaps before scoring.

## Metrics

- **Overclaim Rate** (lead diagnostic): a scorer overclaims when it returns case-level "sufficient" while the property-level ground truth marks a required property as insufficient under the strict mapping.
- **Property Sufficiency Accuracy (PSA)**: per-property correctness against construction-oracle labels.
- **Underclaim Rate** and **Sufficient-claim Rate**: asymmetry controls against trivial baselines.

## Default baselines

Five container-presence baselines operationalize common "the container is present, therefore sufficient" predicates: `trace-present`, `ledger-present`, `schema-present`, `container-checklist`, `source-specific-validator`. (An LLM-judge component is optional and not part of the deterministic package.)

## Headline result (64-case deterministic package)

Across 64 cases, the `trace-present` and `schema-present` baselines overclaim sufficiency on **75%** of cases and `ledger-present` on **50%**, while a property-level candidate scorer records **zero overclaim** at **56.25% mean PSA**. Ground truth is established by a versioned construction-oracle rule file with **paired-oracle self-consistency (kappa 1.0)** over 512 paired property labels — deterministic rule reproducibility, not human inter-rater agreement.

## Ground truth and provenance

Labels are generated deterministically from each scenario specification and degradation condition by a construction-oracle rule file (not human annotation). Scenarios are **synthetic**, derived from published incident framings (e.g., AI Incident Database entries); they are **not field-captured production truth** and do not establish the empirical prevalence of failures in deployed systems. No human or animal subjects research was conducted and no personal data is processed. The pipeline runs deterministically on a consumer laptop in under 60 seconds per case.

Intended use, out-of-scope uses, limitations, and misuse risks are documented in [`RESPONSIBLE_AI.md`](RESPONSIBLE_AI.md). A dataset datasheet is in `DATASHEET.md` in the code repository.

## Dataset layout

- `data/cases/` — the manuscript 64-case corpus: `manuscript_scorer_input_cases.jsonl` (redacted scorer inputs), `manuscript_cases.jsonl` (adjudicated cases), and one regime-native example per regime under `data/cases/<regime>/`
- `data/annotations/` — paired property labels
- `data/oracle/` — construction-oracle rule file
- `data/corpus/` — corpus manifest
- `data/scorers/` — reference candidate-scorer (Decision Trace Reconstructor) outputs
- `data/sources/` — per-case evidence source records

The full result package (baseline and scorer results, summaries, run/readiness and artifact manifests, `checksums.txt`) and the benchmark code live in the canonical GitHub repository and the Zenodo deposit linked below; this Hugging Face mirror carries the dataset inputs, labels, oracle, corpus, and the candidate-scorer reference output.

## Links

- **Code (canonical):** https://github.com/agent-runtime-evidence/decision-evidence-benchmark
- **Archival deposit (citable):** Zenodo DOI [10.5281/zenodo.20426092](https://doi.org/10.5281/zenodo.20426092) (concept DOI [10.5281/zenodo.20408699](https://doi.org/10.5281/zenodo.20408699))
- **Paper:** see `CITATION.cff` in the code repository.

## License

- **Dataset** (everything under `data/`): **Creative Commons Attribution 4.0 International (CC-BY-4.0)**.
- **Code, construction-oracle rules, and degradation transformations:** Apache License 2.0.

## Citation

Please cite both the software artifact (Zenodo DOI above) and the accompanying paper. A machine-readable `CITATION.cff` is provided in the code repository.
