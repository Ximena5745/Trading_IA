"""
F2.2 — reproducibility harness. Unit-level checks on the pure helpers; the full
two-pass digest run is exercised by the script itself.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.check_reproducibility import (
    _METADATA_PATTERNS,
    _RNG_PATTERN,
    _SEED_PATTERN,
    _digest_sha,
    _scan_nondeterminism,
    _series_sha,
)


def test_series_sha_is_stable_and_order_sensitive():
    s = pd.Series([0.0, 1.0, -1.0, 0.0, 1.0])
    assert _series_sha(s) == _series_sha(s.copy())
    assert _series_sha(s) != _series_sha(s.iloc[::-1])


def test_digest_sha_ignores_key_order():
    a = {"x": 1, "y": {"b": 2, "a": 3}}
    b = {"y": {"a": 3, "b": 2}, "x": 1}
    assert _digest_sha(a) == _digest_sha(b)


def test_rng_pattern_flags_unseeded_calls_only():
    assert _RNG_PATTERN.search("v = np.random.choice(arr)")
    assert _RNG_PATTERN.search("random.shuffle(items)")
    # seeded / generator-based usage is not a decision hazard
    assert not _RNG_PATTERN.search("rng = np.random.default_rng(42)")
    assert not _RNG_PATTERN.search("np.random.seed(42)")


def test_seed_pattern_detects_mitigation():
    assert _SEED_PATTERN.search("np.random.seed(42)")
    assert _SEED_PATTERN.search("GaussianHMM(random_state=42)")
    assert _SEED_PATTERN.search("rng = np.random.default_rng(0)")


def test_metadata_patterns_cover_uuid_and_clock():
    assert _METADATA_PATTERNS["uuid4"].search("cid = str(uuid4())")
    assert _METADATA_PATTERNS["datetime_now"].search("datetime.now(timezone.utc)")


def test_scan_reports_classified_findings():
    findings = _scan_nondeterminism()
    assert isinstance(findings, list)
    for f in findings:
        assert f["severity"] in ("metadata", "decision")
        assert set(f) >= {"file", "line", "kind", "severity", "mitigated", "code"}
    # decision-path RNG, if any, must be seed-mitigated
    unmitigated = [
        f for f in findings if f["severity"] == "decision" and not f["mitigated"]
    ]
    assert unmitigated == [], f"unseeded RNG on decision path: {unmitigated}"
