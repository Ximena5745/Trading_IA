"""
Module: core/ml/i1_gate_validator/windows.py
Responsibility: Walk-forward window sizing, adapted to series length
"""
from __future__ import annotations


def wf_params(n_bars: int) -> tuple[int, int, int]:
    """Return (train_window, test_window, step) adapted to series length."""
    if n_bars >= 12000:
        return 252 * 24 * 2, 30 * 24, 7 * 24
    if n_bars >= 8000:
        return 252 * 24, 60 * 24, 30 * 24
    # ~5k bars (indices): shorter windows per I1 plan
    train = min(252 * 24, int(n_bars * 0.55))
    test = min(60 * 24, max(int(n_bars * 0.10), 120))
    step = max(test // 2, 30 * 12)
    if train + test > n_bars:
        train = int(n_bars * 0.5)
        test = int(n_bars * 0.15)
        step = max(test // 2, 60)
    return max(train, 400), max(test, 100), max(step, 50)


def iter_wf_windows(n_bars: int) -> list[dict[str, int]]:
    train_w, test_w, step = wf_params(n_bars)
    windows: list[dict[str, int]] = []
    i = 0
    while i + train_w + test_w <= n_bars:
        windows.append(
            {
                "train_start": i,
                "train_end": i + train_w,
                "test_start": i + train_w,
                "test_end": i + train_w + test_w,
            }
        )
        i += step
    return windows
