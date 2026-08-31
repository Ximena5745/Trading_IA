# Edge Robustness — 2026-08-31T04:59:48.688446+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## USDJPY — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **0.3471** (aprobado: None) · holdout bars = 752 · turnover = 60.0 · cost drag = 0.0003
- **Monte Carlo (holdout)** 500 paths: CI95 = [-0.9361, 1.2628], P(Sharpe>0) = 0.726 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.2202, 0.7086], P(Sharpe>0) = 0.862
- **Cost sweep**: Sharpe neto ×2 = 0.3468; anulación (≤0) en ×None; < gate 0.8 en ×1.0 -> PASS
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 2/2, single-regime = True -> FAIL
- **Anchored WF**: 57 folds, 27 positivos, OOS Sharpe neto = 0.1171 -> FAIL

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | 0.3471 |
| 1.25 | 0.347 |
| 1.5 | 0.3469 |
| 1.75 | 0.3468 |
| 2.0 | 0.3468 |
| 2.5 | 0.3466 |
| 3.0 | 0.3465 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 3.3928 | -2.4681 |
| 2 | 189 | {'rsi_overbought': 75, 'rsi_oversold': 25} | 1.4834 | -2.4506 |
| 3 | 252 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.5741 | -1.5436 |
| 4 | 315 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.732 | -0.1167 |
| 5 | 378 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2675 | 0.0 |
| 6 | 441 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2476 | -0.7059 |
| 7 | 504 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.249 | 0.0 |
| 8 | 567 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2347 | 2.1321 |
| 9 | 630 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1679 | 0.4021 |
| 10 | 693 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1406 | 0.7639 |
| 11 | 756 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.1007 | -0.4545 |
| 12 | 819 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0902 | 1.8889 |
| 13 | 882 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2059 | -0.7632 |
| 14 | 945 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0855 | 1.3796 |
| 15 | 1008 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.151 | 2.0021 |
| 16 | 1071 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3245 | 2.2217 |
| 17 | 1134 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4018 | 0.5824 |
| 18 | 1197 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4085 | -3.0858 |
| 19 | 1260 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.179 | 1.8106 |
| 20 | 1323 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2549 | -0.3015 |
| 21 | 1386 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2446 | 3.7059 |
| 22 | 1449 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.42 | -0.9126 |
| 23 | 1512 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3821 | -0.2201 |
| 24 | 1575 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3605 | -2.0438 |
| 25 | 1638 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3815 | 1.9325 |
| 26 | 1701 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4083 | 0.0 |
| 27 | 1764 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4009 | -0.4778 |
| 28 | 1827 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.365 | 1.0374 |
| 29 | 1890 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3736 | -1.1319 |
| 30 | 1953 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3484 | 3.1945 |
| 31 | 2016 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3588 | 1.0972 |
| 32 | 2079 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3824 | 1.9818 |
| 33 | 2142 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4695 | 1.3946 |
| 34 | 2205 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4853 | 1.6246 |
| 35 | 2268 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.5209 | 2.4883 |
| 36 | 2331 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.5514 | -3.0807 |
| 37 | 2394 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4836 | 0.0 |
| 38 | 2457 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4773 | 0.1742 |
| 39 | 2520 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4719 | 2.982 |
| 40 | 2583 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.4803 | -1.617 |
| 41 | 2646 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.437 | -1.601 |
| 42 | 2709 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3708 | -2.2401 |
| 43 | 2772 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3111 | 0.4901 |
| 44 | 2835 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3158 | -0.5664 |
| 45 | 2898 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2976 | -1.146 |
| 46 | 2961 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3025 | 0.0 |
| 47 | 3024 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2993 | 0.6199 |
| 48 | 3087 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3055 | -0.1714 |
| 49 | 3150 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2992 | 1.8197 |
| 50 | 3213 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.3474 | -3.4469 |
| 51 | 3276 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2393 | 1.4966 |
| 52 | 3339 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2531 | -0.7328 |
| 53 | 3402 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2351 | -1.6405 |
| 54 | 3465 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.2202 | 1.4881 |
| 55 | 3528 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.2506 | 0.7561 |
| 56 | 3591 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.2584 | -0.0564 |
| 57 | 3654 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.2533 | 2.4999 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
