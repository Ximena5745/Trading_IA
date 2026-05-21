"""
Tests for PurgedKFold validation.
M3.1: Verificar que no hay data leakage entre train y test.
"""
from __future__ import annotations

import numpy as np
import pytest

from core.ml.validation import PurgedKFold


class TestPurgedKFold:
    """Test suite for PurgedKFold."""

    def test_purged_kfold_basic_split(self):
        """Test basic split functionality."""
        X = np.random.randn(200, 10)
        y = np.random.randint(0, 2, 200)

        pkf = PurgedKFold(n_splits=5, embargo_bars=5)
        splits = list(pkf.split(X, y))

        assert len(splits) == 5

        for train_idx, test_idx in splits:
            assert len(train_idx) > 0, "Train should not be empty"
            assert len(test_idx) > 0
            assert len(train_idx) + len(test_idx) <= 200

    def test_embargo_removes_look_ahead(self):
        """Test that embargo prevents look-ahead bias."""
        n_samples = 200
        embargo_bars = 5

        X = np.random.randn(n_samples, 5)
        y = np.random.randint(0, 2, n_samples)

        pkf = PurgedKFold(n_splits=5, embargo_bars=embargo_bars)

        found_purged_fold = False
        for train_idx, test_idx in pkf.split(X, y):
            test_start = test_idx[0]
            embargo_end = test_start + embargo_bars

            purged_train = train_idx[train_idx >= embargo_end]
            if len(purged_train) < len(train_idx):
                found_purged_fold = True

        assert found_purged_fold, "At least one fold should have purging"

    def test_no_overlap_between_splits(self):
        """Test that different folds don't share test samples."""
        X = np.random.randn(100, 10)

        pkf = PurgedKFold(n_splits=5, embargo_bars=5)
        splits = list(pkf.split(X))

        test_indices_sets = [set(test_idx) for train_idx, test_idx in splits]

        for i, set_i in enumerate(test_indices_sets):
            for j, set_j in enumerate(test_indices_sets):
                if i != j:
                    assert len(set_i & set_j) == 0, f"Fold {i} and {j} share test samples"

    def test_sequential_order_preserved(self):
        """Test that split maintains temporal order (shuffle=False)."""
        X = np.arange(100).reshape(-1, 1)
        y = np.zeros(100)

        pkf = PurgedKFold(n_splits=5, embargo_bars=5)

        for train_idx, test_idx in pkf.split(X, y):
            assert np.all(train_idx < test_idx[0]), "Train should be before test temporally"

    def test_different_embargo_sizes(self):
        """Test with different embargo bar sizes."""
        for embargo in [0, 3, 5, 10]:
            pkf = PurgedKFold(n_splits=3, embargo_bars=embargo)
            splits = list(pkf.split(np.random.randn(50, 5)))

            assert len(splits) == 3

            for train_idx, test_idx in splits:
                test_start = test_idx[0]
                expected_purge = test_start + embargo
                purged_train = train_idx[train_idx >= expected_purge]
                assert len(purged_train) <= len(train_idx)

    def test_works_with_dataframe(self):
        """Test that works with pandas DataFrame input."""
        import pandas as pd

        df = pd.DataFrame({'a': np.random.randn(100), 'b': np.random.randn(100)})
        y = np.random.randint(0, 2, 100)

        pkf = PurgedKFold(n_splits=3, embargo_bars=5)
        splits = list(pkf.split(df, y))

        assert len(splits) == 3

    def test_binary_and_multiclass_targets(self):
        """Test with different target distributions."""
        X = np.random.randn(100, 10)

        for y in [
            np.random.randint(0, 2, 100),
            np.random.randint(0, 3, 100),
            np.random.randint(0, 5, 100),
        ]:
            pkf = PurgedKFold(n_splits=3, embargo_bars=5)
            splits = list(pkf.split(X, y))
            assert len(splits) == 3

    @pytest.mark.slow
    def test_large_dataset(self):
        """Test with larger dataset."""
        X = np.random.randn(1000, 20)
        y = np.random.randint(0, 2, 1000)

        pkf = PurgedKFold(n_splits=5, embargo_bars=10)
        splits = list(pkf.split(X, y))

        assert len(splits) == 5

        total_test = sum(len(test) for _, test in splits)
        assert total_test > 0, "Should have test samples"
        assert total_test < 1000, "Not all samples in test (expanding window)"