"""
F1.8 (SPEC-B01 / SPEC-A07 subset) — the hermetic-test wiring itself.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_integration_marker_registered_and_default_excluded():
    ini = (REPO / "pytest.ini").read_text(encoding="utf-8")
    assert "integration:" in ini
    assert 'addopts = -m "not integration"' in ini


def test_dashboard_e2e_is_integration_marked():
    src = (REPO / "tests" / "test_dashboard_e2e.py").read_text(encoding="utf-8")
    assert "pytestmark = pytest.mark.integration" in src
    assert "live_server" in src  # uses the fixture, not a hardcoded :8000 server
    assert "http://127.0.0.1:8000" not in src.split("_bind_live_server")[1]


def test_integration_conftest_auto_marks_only_that_dir():
    src = (REPO / "tests" / "integration" / "conftest.py").read_text(encoding="utf-8")
    assert "pytest_collection_modifyitems" in src
    assert "_INTEGRATION_DIR in path.parents" in src


def test_ci_typo_fixed_and_hermetic_services():
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "bandita" not in ci
    assert "pip install ruff black bandit" in ci
    assert "postgres:15-alpine" in ci and "redis:7-alpine" in ci
    assert "-m integration" in ci


def test_fixtures_importable():
    import tests.conftest as ct

    assert hasattr(ct, "docker_services")
    assert hasattr(ct, "live_server")
