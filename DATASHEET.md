# Datasheet for DEMM-Bench

This datasheet documents the Decision Evidence Maturity Model Benchmark
(DEMM-Bench) v0.1.0a0, following the schema proposed by Gebru et al. (2021),
"Datasheets for Datasets" (Communications of the ACM 64(12), 86-92,
<https://doi.org/10.1145/3458723>). The intent is to make the dataset's
purpose, composition, construction, intended use, and maintenance auditable by
external reviewers before they treat any reported numbers as evidence.

The benchmark is deposited together with the accompanying paper. The 64-case
deterministic manuscript package is folded at commit
`6de6250e92e3102ee24918fb8773ffc59b74708c` and reproduces bit-exactly across
the supported Python versions: trace-present and schema-present baselines
each overclaim on 48 / 64 cases (Overclaim Rate 0.75), ledger-present
overclaims on 32 / 64 (0.50), container-checklist and source-specific-validator
overclaim on 0 / 64, and the redacted property-rule candidate scorer reports
mean Property Sufficiency Accuracy 0.5625 with zero overclaim cases and
paired-oracle Cohen kappa 1.0.

## 1. Motivation

**For what purpose was the dataset created?**
DEMM-Bench was created to measure decision-evidence sufficiency under
controlled degradation across eight evidence regimes (AER, MAT, IEEC, DCC/HDP,
PROV, LLM Audit Trails, AEGIS-NTC, Dynamic Capabilities). It provides a
reproducible benchmark for evaluating whether container-presence baselines
overclaim governance-evidence sufficiency and how a property-level candidate
scorer behaves under the same degradation conditions. The benchmark
operationalises the cross-regime measurement question motivated by the
Decision Evidence Maturity Model and the accompanying paper.

**Who created the dataset and on behalf of what entity?**
Oleg Solozobov (ORCID `0009-0009-0105-7459`), as an independent research
artifact accompanying the DEMM-Bench paper. The work is not affiliated with
or sponsored by any institution.

**Who funded the creation of the dataset?**
The dataset is self-funded. There is no external sponsor, no commissioning
organisation, and no industry partner with rights over the construction
process or the released artifacts.

**Any other comments?**
The dataset is the executable counterpart to the DEMM-Bench paper (paper24
in the accompanying research portfolio). It is built to be a measurement
benchmark, not a training set, and it is intentionally synthetic so that
construction-oracle labels are the only label authority on the deposited
package.

## 2. Composition

**What do the instances that comprise the dataset represent?**
Each instance is a decision-event case: a synthetic agent-runtime decision
together with the regime-native evidence available for reconstructing that
decision, the governance question being asked, the target decision identifier,
the degradation condition applied to the evidence, and the construction-oracle
property labels for the eight Decision Event Schema properties.

**How many instances are there in total?**
The v1 manuscript package contains 64 cases, generated as 8 cases per
degradation condition across 8 conditions. Each case carries 8 paired property
labels (one per property family), for a total of 512 paired property labels.
The package is balanced across the 8 evidence regimes and the 8
question-family axes such that every (regime, condition) and every
(question-family, condition) intersection contributes at least one case.

**Does the dataset contain all possible instances or a sample?**
DEMM-Bench is constructed by deterministic enumeration, not by sampling from a
larger population. The 8 conditions x 8 cases per condition layout exhausts
the construction-oracle's rule space at the manuscript package's grain. It is
not a statistical sample from production decision logs and is not intended as
a prevalence estimator.

**What data does each instance consist of?**
Each case manifest includes:

- `case_id`: a stable identifier.
- `regime`: one of the eight evidence regimes.
- `question_family`: the governance question family (e.g., `actor_identity`,
  `policy_basis`, `verification_strength`).
- `degradation_condition`: one of `complete`, `missing_delegation`,
  `missing_policy`, `missing_context`, `conflicting_identity`,
  `partial_graph`, `final_only`, `artifact_only`.
- `evidence`: regime-native evidence fragments and provenance pointers to
  the case's evidence-source root.
- `container_flags`: binary presence indicators (`trace_present`,
  `ledger_present`, `schema_valid`, `checklist_complete`,
  `source_validator_passed`).
- `property_labels`: the eight construction-oracle Decision Event Schema
  labels, with category in `{complete, partial, opaque, conflicting,
  structurally_unfillable}`.
- `metadata`: oracle spec SHA-256, label adjudication mode, label basis,
  and result-honesty disclosure.

The repository also publishes case-level adjudicated and unadjudicated
manifests (`data/cases/manuscript_cases.jsonl` and
`data/cases/manuscript_cases.unadjudicated.jsonl`), the construction-oracle
rule spec (`data/oracle/construction_oracle_v1.yaml`), per-regime native
fixtures under `data/cases/<regime>/`, baseline and candidate scorer outputs
under `data/baselines/` and `data/scorers/`, and reference result artifacts
under `data/results/`.

**Is there a label or target associated with each instance?**
Yes. Each case has eight construction-oracle property-category labels and a
derived case-level strict sufficiency verdict (`sufficient` or
`insufficient`). The labels are deterministic outputs of the
`construction_oracle_v1.yaml` rule spec, applied to the degradation condition
of the case.

**Is any information missing from individual instances?**
The deposited package operationalises four levels of the Decision Evidence
Maturity Model. The fifth-level maturity rubric (RQ4 in the accompanying
paper) is documented but not operationalised in v1. Broader substitution axes
(question-family variants beyond eight, scorer ecosystem beyond one redacted
property-rule scorer, more than five default baselines) are also out of scope
for v1 and tracked as future work.

**Are relationships between individual instances made explicit?**
Yes. Cases are organised by `regime`, `question_family`, and
`degradation_condition`. The corpus manifest at
`data/corpus/manuscript_corpus.template.yaml` describes the package layout,
and the result-package CSV exports list the same cases by all three slice
keys. Cases sharing a degradation condition share construction-oracle
overrides; cases sharing a regime share the regime-native adapter behaviour.

**Are there recommended data splits?**
No. DEMM-Bench is a measurement benchmark, not an ML training set. There is
no train / val / test partition. The full 64-case package is a leave-out test
set on which scorers and baselines are evaluated end-to-end.

**Are there any errors, sources of noise, or redundancies in the dataset?**
Labels are deterministic construction-oracle outputs, so there is no human
label noise. Paired-oracle Cohen kappa is 1.0 by construction and is reported
as a self-consistency diagnostic, not as inter-rater agreement among
independent humans. The construction-oracle is the only label authority on
the deposited package; the result-honesty fields in each case make this
explicit.

**Is the dataset self-contained, or does it link to or rely on external
resources?**
The dataset is self-contained. There is one motivating real-world reference
(AI Incident Database #1433, the Antigravity 1.0 D-drive incident) cited in
the paper's introduction for context only; no incident data is included in
or required by the dataset. No network access, external API call, or
credentialed resource is required to reproduce the package.

**Does the dataset contain data that might be considered confidential?**
No. The dataset is entirely synthetic. It contains no personal data, no
production system traces, no proprietary configuration, and no operator
identifiers.

**Does the dataset contain data that, if viewed directly, might be offensive,
insulting, threatening, or might otherwise cause anxiety?**
No.

**Does the dataset identify any subpopulations (e.g., by age, gender)?**
No. The dataset describes synthetic agent-runtime decisions; it does not
describe individuals.

**Is it possible to identify individuals from the dataset?**
No. The synthetic cases do not represent natural persons.

**Does the dataset contain data that might be considered sensitive in any
way?**
No.

## 3. Collection Process

**How was the data associated with each instance acquired?**
Cases were constructed synthetically via deterministic rules. There is no
external acquisition: nothing is scraped, observed, sampled, or otherwise
collected from third-party systems.

**What mechanisms or procedures were used to collect the data?**
The construction pipeline is implemented in this repository. The
construction-oracle rule spec at `data/oracle/construction_oracle_v1.yaml`
defines per-degradation-condition property overrides. The case-construction
scripts under `src/decision_evidence_benchmark/` and `scripts/` apply those
rules to generate native fixtures per regime, normalise the fixtures through
per-regime adapters, attach container-presence flags consistent with the
degradation condition, and emit case manifests.

**If the dataset is a sample from a larger set, what was the sampling
strategy?**
Not applicable. The dataset is a deterministic full enumeration of
8 conditions x 8 cases per condition, balanced across the 8 regimes and the
8 question-family axes.

**Who was involved in the data collection process and how were they
compensated?**
The sole author Oleg Solozobov performed all dataset construction. No
external annotators, vendors, or crowd workers were used.

**Over what timeframe was the data collected?**
Construction took place in 2026 Q2. The construction-oracle rule spec
`data/oracle/construction_oracle_v1.yaml` was committed before the result
fold at `6de6250e92e3102ee24918fb8773ffc59b74708c`. The deposited package's
supersession timestamp is `2026-05-25`.

**Were any ethical review processes conducted?**
No formal ethics review was conducted. The dataset is entirely synthetic, has
no human or animal subjects, and contains no personal data, so an Institutional
Review Board determination is not required. The deposited result-honesty
fields and `AGENTS.md` scope statement document the absence of human subjects.

**Did you collect the data from the individuals in question directly, or
obtain it via third parties or other sources?**
Not applicable; the dataset is synthetic.

**Were the individuals in question notified about the data collection?**
Not applicable; the dataset is synthetic.

**Did the individuals in question consent to the collection and use of their
data?**
Not applicable; the dataset is synthetic.

**If consent was obtained, were the consenting individuals provided with a
mechanism to revoke their consent in the future or for certain uses?**
Not applicable; the dataset is synthetic.

**Has an analysis of the potential impact of the dataset and its use on data
subjects been conducted?**
Not applicable; the dataset has no data subjects.

## 4. Preprocessing / Cleaning / Labeling

**Was any preprocessing / cleaning / labeling of the data done?**
Yes. Each case's regime-native record is normalised through a regime-specific
adapter (eight adapters, one per regime) into the shared `CaseManifest`
schema with a property-fragment bundle. Construction-oracle property labels
are applied deterministically by evaluating the case's degradation condition
against `data/oracle/construction_oracle_v1.yaml`. The redacted scorer-input
artifact and the case-id map are produced by the redaction pipeline before
candidate-scorer outputs are written. A label-leakage audit
(`scripts/audit_manuscript_label_leakage.py`) confirms that scorer-facing
artifacts do not expose degradation conditions, embedded labels, or case
identifiers that encode the degradation condition.

**Was the "raw" data saved in addition to the preprocessed / cleaned /
labeled data?**
Yes. The construction-oracle rule spec is the canonical "raw" specification
of label assignment; combined with the per-regime native fixtures under
`data/cases/<regime>/` and the case-construction scripts, the deposited
package can be fully reconstituted from the raw inputs. The result-package
manifest references all inputs and outputs by SHA-256 in `checksums.txt`.

**Is the software that was used to preprocess / clean / label the data
available?**
Yes. The complete construction, scoring, and reporting pipeline is open source
under Apache-2.0 (code) and CC-BY-4.0 (data) and is published in this
repository.

## 5. Uses

**Has the dataset been used for any tasks already?**
Yes. The accompanying paper (paper24) reports primary results for five default
container-presence baselines and one redacted property-rule candidate scorer
over the 64-case manuscript package. The headline metrics are: Overclaim Rate
0.75 for trace-present and schema-present (48 / 64 overclaim cases each), 0.50
for ledger-present (32 / 64), and 0.00 for container-checklist and
source-specific-validator (0 / 64 each); candidate scorer mean Property
Sufficiency Accuracy 0.5625 with zero overclaim cases; paired-oracle Cohen
kappa 1.0 overall and for every property family.

**Is there a repository that links to any or all papers or systems that use
the dataset?**
Yes. This repository (the DEMM-Bench backend) and the accompanying paper24
manuscript are co-released. The Zenodo deposit pins the release artifact for
external citation; the GitHub repository hosts the canonical source.

**What other tasks could the dataset be used for?**
Anticipated reuse paths include:

- Property-level scorer development and benchmarking.
- Governance-evidence sufficiency studies in additional regimes.
- Comparative diagnostics for container-fallacy patterns across baselines.
- Methodology pilots for evidence-regime adapter design.
- Replication studies of the cross-regime measurement claim under independent
  construction-oracle rule variants.

**Is there anything about the composition of the dataset or the way it was
collected and preprocessed/cleaned/labeled that might impact future uses?**
Yes. The accompanying paper records four explicit threats to validity that
external users should retain when reasoning about future use:

- T1 (synthetic-versus-production prevalence): the 64-case construction is
  not a random sample from production decision logs.
- T2 (baselines as deliberately weak lower bounds): the five default
  baselines are container-presence predicates by design; they are not
  claims about a vendor's best system.
- T3 (paired-oracle kappa 1.0 is rule-reproducibility, not human inter-rater
  agreement): kappa is reported as a self-consistency diagnostic only.
- T4 (scope is 8 regimes x 8 conditions x 1 candidate scorer): broader
  scorer ecosystems and substitution axes are future-work.

**Are there tasks for which the dataset should not be used?**
Yes. DEMM-Bench is not a legal-adequacy oracle, not a regulatory
certification tool, not a production-prevalence estimator, and not a
competitor capability benchmark. The benchmark backend scope document
(`docs/benchmark_backend_scope.md`) and paper24 §3.1 record these non-goals
explicitly.

**Any other comments?**
The benchmark separates manuscript-package authority (deterministic
construction-oracle labels) from optional audit artifacts (LLM-judge outputs,
external human review). Users should preserve that separation when extending
or comparing.

## 6. Distribution

**Will the dataset be distributed to third parties outside of the entity on
behalf of which the dataset was created?**
Yes. The dataset is being released publicly as part of the DEMM-Bench paper
submission package.

**How will the dataset be distributed?**
The dataset is distributed through three channels:

- A Zenodo deposit pinned to a DOI (to be assigned at deposit time).
- The public GitHub repository for ongoing development.
- A `pip`-installable Python package (`decision-evidence-benchmark`) that
  bundles code and reference data files.

**When will the dataset be distributed?**
Concurrent with the paper24 submission and the assignment of the Zenodo DOI.

**Will the dataset be distributed under a copyright or other intellectual
property (IP) license, and/or under applicable terms of use (ToU)?**
Yes. Code is licensed under Apache-2.0 (see `LICENSE`). Data, labels,
annotations, manifests, and adjudication artifacts under `data/` are licensed
under CC-BY-4.0 (see `LICENSE-DATA`). Citation is requested through the
`CITATION.cff` file and the README.

**Have any third parties imposed IP-based or other restrictions on the data
associated with the instances?**
No. The dataset is entirely synthetic and constructed without third-party
data.

**Do any export controls or other regulatory restrictions apply to the
dataset or to individual instances?**
No. The dataset is synthetic governance-research data with no export-controlled
content.

## 7. Maintenance

**Who will be supporting / hosting / maintaining the dataset?**
Oleg Solozobov, through the public GitHub repository and the Zenodo deposit
record.

**How can the owner / curator / manager of the dataset be contacted?**
Via GitHub issues on the public repository (the canonical contact channel)
and via the paper24 corresponding-author channel published with the paper.

**Is there an erratum?**
None at v0.1.0a0. Future errata are tracked in `CHANGELOG.md` and reflected
in re-released Zenodo records.

**Will the dataset be updated (e.g., to correct labeling errors, add new
instances, delete instances)?**
Yes. Future releases will extend the regime set, baseline set, candidate
scorer ecosystem, and substitution axes as documented in the paper's future
work section (F1-F6 in paper24 §9). Updates are version-pinned through the
`CITATION.cff` version field, the `manifest.yaml` schema version, and the
Zenodo deposit DOI.

**If the dataset relates to people, are there applicable limits on the
retention of the data associated with the instances?**
Not applicable; the dataset is synthetic.

**Will older versions of the dataset continue to be supported / hosted /
maintained?**
Each released version is pinned to a Zenodo DOI. The reproducibility-of-record
guarantee is preserved per release: the manuscript-package commit hash and
SHA-256 checksums in the repository, the Zenodo deposit, and the
accompanying paper jointly identify a single bit-exact artifact.

**If others want to extend / augment / build on / contribute to the dataset,
is there a mechanism for them to do so?**
Yes. The adapter contract separates regime parsing from scoring, so new
regime adapters can be contributed independently via the documented
`from_native_record` contract (paper24 §4.4). New baselines slot into
`src/decision_evidence_benchmark/baselines/registry.py`. New property-level
scorers follow the contract demonstrated by the redacted property-rule
candidate scorer (`src/decision_evidence_benchmark/deterministic_predictions.py`).
See `CONTRIBUTING.md` for the contribution workflow, code-style requirements,
and test expectations.

---

This DATASHEET accompanies the public release of DEMM-Bench v0.1.0a0 and
should be cited alongside the dataset and the paper:

Solozobov, O. (2026). DEMM-Bench: A Decision Evidence Maturity Benchmark for
Agent-Runtime Decisions Across Eight Evidence Regimes. Zenodo DOI: <pending>.

Schema source: Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W.,
Wallach, H., Daumé III, H., & Crawford, K. (2021). Datasheets for Datasets.
Communications of the ACM, 64(12), 86-92. <https://doi.org/10.1145/3458723>
