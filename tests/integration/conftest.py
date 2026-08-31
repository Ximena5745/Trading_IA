"""Everything under tests/integration/ is an integration test (SPEC-B01).

Auto-applies the `integration` marker so the default `-m "not integration"`
signal excludes them; CI opts in with `-m integration`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_INTEGRATION_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    for item in items:
        try:
            path = Path(str(item.fspath))
        except Exception:  # noqa: BLE001
            continue
        if _INTEGRATION_DIR in path.parents:
            item.add_marker(pytest.mark.integration)
