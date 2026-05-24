"""Agreement metrics for calibration labels."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence


def cohen_kappa(left: Sequence[str], right: Sequence[str]) -> float:
    """Return Cohen kappa for two same-length nominal label sequences."""

    if len(left) != len(right):
        raise ValueError("cohen_kappa requires same-length label sequences")
    if not left:
        raise ValueError("cohen_kappa requires at least one label")

    total = len(left)
    observed = sum(1 for a, b in zip(left, right, strict=True) if a == b) / total
    left_counts = Counter(left)
    right_counts = Counter(right)
    labels = set(left_counts) | set(right_counts)
    expected = sum((left_counts[label] / total) * (right_counts[label] / total) for label in labels)

    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)

