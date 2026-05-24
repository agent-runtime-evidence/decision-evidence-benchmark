# Corpus Manifests

Corpus manifests define which case-manifest JSONL files belong to a benchmark
run and what label contract they must satisfy.

The smoke corpus and draft balanced corpus use embedded property labels because
they exist only to verify mechanics. Full benchmark corpora should keep native
evidence fixtures, adapted case manifests, and annotation provenance under
explicit manifests before any result artifact is treated as manuscript-ready
evidence.

Use `manuscript_corpus.template.yaml` as the starting point for the
manuscript-scale corpus manifest. Copy it to a non-template manifest only after
the referenced case and annotation files exist and have passed review.

The manuscript template currently declares
`calibration_status: construction_rule_oracle_v1`, matching the deterministic
construction-oracle label path in `data/oracle/construction_oracle_v1.yaml`. If
the label policy changes, update the oracle spec, template, and readiness
evidence together rather than editing the promoted manifest by hand.
