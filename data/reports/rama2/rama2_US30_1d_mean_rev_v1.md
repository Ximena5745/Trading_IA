# Edge Robustness — 2026-08-31T05:01:29.135335+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## US30 — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **-0.4911** (aprobado: None) · holdout bars = 726 · turnover = 7.0 · cost drag = 0.0014
- **Monte Carlo (holdout)** 500 paths: CI95 = [-1.5067, 0.6068], P(Sharpe>0) = 0.186 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.6519, 0.3923], P(Sharpe>0) = 0.296
- **Cost sweep**: Sharpe neto ×2 = -0.4925; anulación (≤0) en ×1.0; < gate 0.8 en ×1.0 -> FAIL
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 1/2, single-regime = True -> FAIL
- **Anchored WF**: 55 folds, 23 positivos, OOS Sharpe neto = -0.325 -> FAIL

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | -0.4911 |
| 1.25 | -0.4914 |
| 1.5 | -0.4918 |
| 1.75 | -0.4921 |
| 2.0 | -0.4925 |
| 2.5 | -0.4932 |
| 3.0 | -0.4939 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.5885 | -2.47 |
| 2 | 189 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -1.1517 | 0.0 |
| 3 | 252 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.215 | -0.2338 |
| 4 | 315 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.2302 | 2.6216 |
| 5 | 378 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.2821 | 0.4065 |
| 6 | 441 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.238 | 1.588 |
| 7 | 504 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3986 | -1.5621 |
| 8 | 567 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.1701 | 0.2788 |
| 9 | 630 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2141 | 0.0 |
| 10 | 693 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2041 | 0.0 |
| 11 | 756 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1954 | -0.1495 |
| 12 | 819 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1355 | 0.8318 |
| 13 | 882 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1999 | 0.9949 |
| 14 | 945 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2781 | 0.1706 |
| 15 | 1008 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2569 | 1.265 |
| 16 | 1071 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3146 | 6.4311 |
| 17 | 1134 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5392 | 2.3175 |
| 18 | 1197 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5975 | 2.1976 |
| 19 | 1260 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.649 | 2.6926 |
| 20 | 1323 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.7113 | 6.4674 |
| 21 | 1386 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.8664 | 0.3249 |
| 22 | 1449 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.816 | 0.3447 |
| 23 | 1512 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.7827 | 1.3487 |
| 24 | 1575 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.7994 | -0.8331 |
| 25 | 1638 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.6912 | -1.1554 |
| 26 | 1701 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5619 | -0.1007 |
| 27 | 1764 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.5334 | -0.5461 |
| 28 | 1827 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4723 | -3.1423 |
| 29 | 1890 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3713 | 2.1093 |
| 30 | 1953 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4561 | -0.285 |
| 31 | 2016 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2822 | -4.3155 |
| 32 | 2079 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2024 | -0.8824 |
| 33 | 2142 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.1826 | -2.7953 |
| 34 | 2205 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2132 | 2.4006 |
| 35 | 2268 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2692 | 0.1258 |
| 36 | 2331 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2633 | 1.6388 |
| 37 | 2394 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2898 | -1.1748 |
| 38 | 2457 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2499 | -1.9758 |
| 39 | 2520 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.1692 | 0.4773 |
| 40 | 2583 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.1765 | -3.5741 |
| 41 | 2646 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.08 | -1.4864 |
| 42 | 2709 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0477 | -0.0241 |
| 43 | 2772 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0463 | -1.9905 |
| 44 | 2835 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.0274 | -3.2181 |
| 45 | 2898 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0575 | -5.9494 |
| 46 | 2961 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.072 | -0.0104 |
| 47 | 3024 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.07 | -1.4477 |
| 48 | 3087 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.0627 | -1.966 |
| 49 | 3150 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.0347 | 1.291 |
| 50 | 3213 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.0499 | 0.9642 |
| 51 | 3276 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.0713 | -2.5536 |
| 52 | 3339 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0476 | -1.1681 |
| 53 | 3402 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0317 | -1.9365 |
| 54 | 3465 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0483 | -1.4971 |
| 55 | 3528 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0308 | -3.2832 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
