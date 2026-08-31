# Edge Robustness — 2026-08-31T05:00:37.850601+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## US500 — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **-0.0198** (aprobado: None) · holdout bars = 726 · turnover = 26.0 · cost drag = 0.0091
- **Monte Carlo (holdout)** 500 paths: CI95 = [-1.1358, 1.0324], P(Sharpe>0) = 0.434 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.4312, 0.5159], P(Sharpe>0) = 0.56
- **Cost sweep**: Sharpe neto ×2 = -0.0289; anulación (≤0) en ×1.0; < gate 0.8 en ×1.0 -> FAIL
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 2/2, single-regime = True -> FAIL
- **Anchored WF**: 55 folds, 26 positivos, OOS Sharpe neto = -0.0552 -> FAIL

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | -0.0198 |
| 1.25 | -0.0221 |
| 1.5 | -0.0244 |
| 1.75 | -0.0267 |
| 2.0 | -0.0289 |
| 2.5 | -0.0335 |
| 3.0 | -0.038 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.8963 | 0.834 |
| 2 | 189 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.8954 | 2.1408 |
| 3 | 252 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.2203 | 1.9659 |
| 4 | 315 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.3562 | 2.4056 |
| 5 | 378 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.5419 | 1.6343 |
| 6 | 441 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.5044 | 2.3343 |
| 7 | 504 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.597 | -1.6669 |
| 8 | 567 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.2093 | 1.632 |
| 9 | 630 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.2463 | 1.5183 |
| 10 | 693 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.2636 | 0.0046 |
| 11 | 756 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.1526 | 0.0144 |
| 12 | 819 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.99 | 0.8498 |
| 13 | 882 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.9599 | 1.7531 |
| 14 | 945 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 1.0295 | 0.3066 |
| 15 | 1008 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.9527 | 1.5099 |
| 16 | 1071 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.9879 | 0.4987 |
| 17 | 1134 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.9672 | -2.9011 |
| 18 | 1197 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.8949 | 2.2537 |
| 19 | 1260 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.9382 | 0.9484 |
| 20 | 1323 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.9338 | -3.3055 |
| 21 | 1386 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.847 | -0.1042 |
| 22 | 1449 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.7728 | -0.4044 |
| 23 | 1512 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.7028 | 3.8596 |
| 24 | 1575 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.7809 | -0.9562 |
| 25 | 1638 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.7181 | -0.6413 |
| 26 | 1701 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.6492 | -0.5809 |
| 27 | 1764 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.6103 | 0.515 |
| 28 | 1827 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.612 | 5.1204 |
| 29 | 1890 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.7111 | -1.4359 |
| 30 | 1953 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.5946 | -0.5172 |
| 31 | 2016 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.4604 | -1.4915 |
| 32 | 2079 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3781 | -1.2297 |
| 33 | 2142 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.3136 | -0.8992 |
| 34 | 2205 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.2875 | -1.6135 |
| 35 | 2268 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.2449 | -1.7368 |
| 36 | 2331 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.2191 | -1.3952 |
| 37 | 2394 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.1817 | 0.5626 |
| 38 | 2457 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.1933 | 2.1201 |
| 39 | 2520 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.2661 | -0.6323 |
| 40 | 2583 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.2272 | -2.4964 |
| 41 | 2646 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.17 | 0.0 |
| 42 | 2709 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.1681 | -0.1262 |
| 43 | 2772 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.1615 | -4.6994 |
| 44 | 2835 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0981 | -0.5084 |
| 45 | 2898 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0876 | -3.1588 |
| 46 | 2961 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0476 | -1.0553 |
| 47 | 3024 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0287 | -4.2836 |
| 48 | 3087 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0322 | 3.8112 |
| 49 | 3150 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0369 | 0.6116 |
| 50 | 3213 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0479 | 1.6271 |
| 51 | 3276 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.1096 | -3.8997 |
| 52 | 3339 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0255 | -3.8031 |
| 53 | 3402 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0072 | -0.8679 |
| 54 | 3465 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0114 | 1.4395 |
| 55 | 3528 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 0.0162 | -4.5346 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
