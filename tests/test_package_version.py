"""Guard against version drift between the package and its metadata."""

from importlib.metadata import version

import decision_evidence_benchmark


def test_version_matches_installed_metadata() -> None:
    assert decision_evidence_benchmark.__version__ == version("decision-evidence-benchmark")
