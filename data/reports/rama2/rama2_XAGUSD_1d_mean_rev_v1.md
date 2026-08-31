# Edge Robustness — 2026-08-31T04:57:26.987189+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## XAGUSD — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **-0.2761** (aprobado: None) · holdout bars = 1256 · turnover = 103.0 · cost drag = 0.0594
- **Monte Carlo (holdout)** 500 paths: CI95 = [-1.2707, 0.4418], P(Sharpe>0) = 0.252 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.6972, 0.041], P(Sharpe>0) = 0.052
- **Cost sweep**: Sharpe neto ×2 = -0.3356; anulación (≤0) en ×1.0; < gate 0.8 en ×1.0 -> FAIL
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 0/2, single-regime = True -> FAIL
- **Anchored WF**: 97 folds, 42 positivos, OOS Sharpe neto = -0.1531 -> FAIL

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | -0.2761 |
| 1.25 | -0.291 |
| 1.5 | -0.3059 |
| 1.75 | -0.3207 |
| 2.0 | -0.3356 |
| 2.5 | -0.3655 |
| 3.0 | -0.3953 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.88 | -2.9965 |
| 2 | 189 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.3483 | -2.6747 |
| 3 | 252 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.9636 | 2.096 |
| 4 | 315 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.0828 | -0.6154 |
| 5 | 378 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.2098 | 1.9696 |
| 6 | 441 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1116 | -1.1964 |
| 7 | 504 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.1024 | -1.8113 |
| 8 | 567 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.3777 | -1.8628 |
| 9 | 630 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.5583 | -0.743 |
| 10 | 693 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.481 | -1.2608 |
| 11 | 756 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.5381 | 0.5726 |
| 12 | 819 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.4777 | -0.2756 |
| 13 | 882 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.4483 | -0.1222 |
| 14 | 945 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2667 | -1.1457 |
| 15 | 1008 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3648 | -1.1576 |
| 16 | 1071 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.4015 | -0.0807 |
| 17 | 1134 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3898 | 3.376 |
| 18 | 1197 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2143 | -1.5365 |
| 19 | 1260 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2132 | -0.8766 |
| 20 | 1323 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.221 | -0.5414 |
| 21 | 1386 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2241 | 1.0488 |
| 22 | 1449 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1915 | 0.1249 |
| 23 | 1512 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1682 | 2.9288 |
| 24 | 1575 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.072 | -2.574 |
| 25 | 1638 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2161 | 0.8676 |
| 26 | 1701 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1886 | 2.5991 |
| 27 | 1764 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1597 | 2.1637 |
| 28 | 1827 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0856 | -2.864 |
| 29 | 1890 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1537 | 0.0 |
| 30 | 1953 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1333 | 0.4782 |
| 31 | 2016 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1222 | 0.0 |
| 32 | 2079 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1203 | -0.9477 |
| 33 | 2142 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1345 | 0.8967 |
| 34 | 2205 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1293 | 1.1388 |
| 35 | 2268 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0995 | 2.3121 |
| 36 | 2331 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0298 | -1.116 |
| 37 | 2394 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0333 | -1.1253 |
| 38 | 2457 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0982 | 2.9422 |
| 39 | 2520 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0532 | 0.236 |
| 40 | 2583 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0502 | 0.2445 |
| 41 | 2646 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0456 | 1.4131 |
| 42 | 2709 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0289 | -2.6144 |
| 43 | 2772 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0618 | -1.5499 |
| 44 | 2835 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0844 | -2.7849 |
| 45 | 2898 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1987 | 0.3677 |
| 46 | 2961 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1901 | -2.6195 |
| 47 | 3024 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2333 | 0.4868 |
| 48 | 3087 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2293 | -0.3567 |
| 49 | 3150 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2295 | 1.6038 |
| 50 | 3213 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2141 | -0.9262 |
| 51 | 3276 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2192 | -0.9075 |
| 52 | 3339 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2295 | -2.0688 |
| 53 | 3402 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2394 | 1.0095 |
| 54 | 3465 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2257 | 1.7499 |
| 55 | 3528 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2128 | -1.8036 |
| 56 | 3591 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2253 | -2.3279 |
| 57 | 3654 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2377 | -0.5127 |
| 58 | 3717 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.237 | -2.8598 |
| 59 | 3780 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.285 | -0.367 |
| 60 | 3843 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2855 | 1.9191 |
| 61 | 3906 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2781 | 0.9512 |
| 62 | 3969 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2715 | -3.5458 |
| 63 | 4032 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2888 | -2.1564 |
| 64 | 4095 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2929 | 2.7115 |
| 65 | 4158 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2619 | -0.0329 |
| 66 | 4221 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2454 | 0.0 |
| 67 | 4284 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2436 | -2.2359 |
| 68 | 4347 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2545 | 0.5126 |
| 69 | 4410 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2514 | -0.8325 |
| 70 | 4473 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2565 | 2.095 |
| 71 | 4536 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2136 | 0.7134 |
| 72 | 4599 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2044 | -3.6509 |
| 73 | 4662 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3207 | -0.3162 |
| 74 | 4725 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3103 | -1.0309 |
| 75 | 4788 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3222 | 3.4117 |
| 76 | 4851 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2371 | 3.409 |
| 77 | 4914 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.205 | -0.659 |
| 78 | 4977 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2071 | 0.0225 |
| 79 | 5040 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1961 | 1.772 |
| 80 | 5103 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1857 | -1.0998 |
| 81 | 5166 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.193 | -1.6506 |
| 82 | 5229 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2064 | 2.9083 |
| 83 | 5292 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1868 | 0.1735 |
| 84 | 5355 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1831 | 0.5462 |
| 85 | 5418 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1788 | 1.5218 |
| 86 | 5481 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1689 | -1.6316 |
| 87 | 5544 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.171 | -2.8544 |
| 88 | 5607 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1797 | -2.4112 |
| 89 | 5670 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2009 | -1.1107 |
| 90 | 5733 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2131 | 1.9421 |
| 91 | 5796 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2053 | 0.2763 |
| 92 | 5859 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.201 | 2.3565 |
| 93 | 5922 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1795 | -2.1586 |
| 94 | 5985 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1875 | -2.8567 |
| 95 | 6048 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2079 | -1.2611 |
| 96 | 6111 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2314 | 1.9453 |
| 97 | 6174 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1275 | 1.9666 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
