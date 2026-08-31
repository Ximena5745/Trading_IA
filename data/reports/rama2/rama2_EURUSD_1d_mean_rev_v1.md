# Edge Robustness — 2026-08-31T04:58:08.239387+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## EURUSD — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **0.6924** (aprobado: None) · holdout bars = 752 · turnover = 34.0 · cost drag = 0.0109
- **Monte Carlo (holdout)** 500 paths: CI95 = [-0.5445, 1.7432], P(Sharpe>0) = 0.858 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.3979, 0.6456], P(Sharpe>0) = 0.68
- **Cost sweep**: Sharpe neto ×2 = 0.6814; anulación (≤0) en ×None; < gate 0.8 en ×1.0 -> PASS
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 1/2, single-regime = True -> FAIL
- **Anchored WF**: 57 folds, 32 positivos, OOS Sharpe neto = 0.5265 -> PASS

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | 0.6924 |
| 1.25 | 0.6896 |
| 1.5 | 0.6869 |
| 1.75 | 0.6842 |
| 2.0 | 0.6814 |
| 2.5 | 0.676 |
| 3.0 | 0.6705 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -3.0606 | -0.7471 |
| 2 | 189 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.9538 | -3.0992 |
| 3 | 252 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.9525 | 1.8552 |
| 4 | 315 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0509 | -1.1217 |
| 5 | 378 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2493 | -2.5523 |
| 6 | 441 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.314 | 1.0166 |
| 7 | 504 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.1159 | 1.8925 |
| 8 | 567 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1004 | 0.8503 |
| 9 | 630 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1301 | 3.0977 |
| 10 | 693 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5292 | 4.1819 |
| 11 | 756 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 1.0431 | 0.7832 |
| 12 | 819 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.9767 | -1.4427 |
| 13 | 882 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.8459 | -0.1618 |
| 14 | 945 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.7731 | 0.9973 |
| 15 | 1008 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.8531 | -2.4341 |
| 16 | 1071 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6816 | -1.5541 |
| 17 | 1134 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6043 | 1.2183 |
| 18 | 1197 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6292 | 2.0516 |
| 19 | 1260 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.7302 | -0.2751 |
| 20 | 1323 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6658 | -2.6254 |
| 21 | 1386 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5572 | -1.6608 |
| 22 | 1449 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5052 | 0.4693 |
| 23 | 1512 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5013 | -1.5953 |
| 24 | 1575 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4537 | 0.0758 |
| 25 | 1638 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4412 | -2.3461 |
| 26 | 1701 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3644 | 2.2868 |
| 27 | 1764 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4338 | 0.1076 |
| 28 | 1827 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.42 | 0.2997 |
| 29 | 1890 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4144 | 1.3108 |
| 30 | 1953 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4156 | -0.2666 |
| 31 | 2016 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4075 | -3.0013 |
| 32 | 2079 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3596 | 3.1629 |
| 33 | 2142 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4415 | 3.2752 |
| 34 | 2205 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5421 | -0.2987 |
| 35 | 2268 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.518 | 0.5478 |
| 36 | 2331 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5257 | 0.6344 |
| 37 | 2394 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5243 | 3.3263 |
| 38 | 2457 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5912 | -4.0078 |
| 39 | 2520 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5368 | 0.4078 |
| 40 | 2583 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5416 | 4.1323 |
| 41 | 2646 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6553 | 0.7153 |
| 42 | 2709 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6504 | 1.0655 |
| 43 | 2772 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6495 | -2.117 |
| 44 | 2835 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5895 | -1.3658 |
| 45 | 2898 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5625 | 1.4696 |
| 46 | 2961 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5819 | -3.3766 |
| 47 | 3024 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5165 | -0.7468 |
| 48 | 3087 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4898 | -0.985 |
| 49 | 3150 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4771 | 0.6103 |
| 50 | 3213 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4782 | -1.3252 |
| 51 | 3276 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4591 | -0.8536 |
| 52 | 3339 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4366 | 4.0173 |
| 53 | 3402 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5388 | 1.6321 |
| 54 | 3465 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5636 | 0.231 |
| 55 | 3528 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5558 | 0.2387 |
| 56 | 3591 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5568 | -0.6634 |
| 57 | 3654 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5398 | 0.5097 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
