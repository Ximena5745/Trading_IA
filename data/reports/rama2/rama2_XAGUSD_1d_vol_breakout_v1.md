# Edge Robustness — 2026-08-31T04:57:17.616917+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## XAGUSD — vol_breakout_v1 {'lookback': 20, 'atr_mult': 2.0} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **0.3644** (aprobado: None) · holdout bars = 1256 · turnover = 142.0 · cost drag = 0.0881
- **Monte Carlo (holdout)** 500 paths: CI95 = [-0.5286, 1.3059], P(Sharpe>0) = 0.806 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.1322, 0.5892], P(Sharpe>0) = 0.874
- **Cost sweep**: Sharpe neto ×2 = 0.2767; anulación (≤0) en ×None; < gate 0.8 en ×1.0 -> PASS
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 2/2, single-regime = True -> FAIL
- **Anchored WF**: 97 folds, 50 positivos, OOS Sharpe neto = 0.1634 -> PASS

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | 0.3644 |
| 1.25 | 0.3424 |
| 1.5 | 0.3205 |
| 1.75 | 0.2985 |
| 2.0 | 0.2767 |
| 2.5 | 0.2329 |
| 3.0 | 0.1894 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'atr_mult': 1.5, 'lookback': 15} | 2.013 | -0.5723 |
| 2 | 189 | {'atr_mult': 1.5, 'lookback': 15} | 0.4239 | 2.7193 |
| 3 | 252 | {'atr_mult': 1.5, 'lookback': 15} | 1.1634 | -1.4617 |
| 4 | 315 | {'atr_mult': 1.5, 'lookback': 15} | 0.2341 | -2.6376 |
| 5 | 378 | {'atr_mult': 1.5, 'lookback': 20} | -0.5141 | -1.3817 |
| 6 | 441 | {'atr_mult': 1.5, 'lookback': 15} | -0.0185 | -3.4786 |
| 7 | 504 | {'atr_mult': 1.5, 'lookback': 15} | -0.5105 | 1.6732 |
| 8 | 567 | {'atr_mult': 1.5, 'lookback': 15} | -0.1902 | 1.8455 |
| 9 | 630 | {'atr_mult': 1.5, 'lookback': 15} | 0.0385 | -4.7024 |
| 10 | 693 | {'atr_mult': 1.5, 'lookback': 15} | -0.2097 | 1.136 |
| 11 | 756 | {'atr_mult': 1.5, 'lookback': 15} | -0.129 | -1.0114 |
| 12 | 819 | {'atr_mult': 1.5, 'lookback': 15} | -0.181 | 0.4464 |
| 13 | 882 | {'atr_mult': 1.5, 'lookback': 15} | -0.0928 | -0.5287 |
| 14 | 945 | {'atr_mult': 1.5, 'lookback': 15} | -0.1611 | 0.3959 |
| 15 | 1008 | {'atr_mult': 1.5, 'lookback': 20} | -0.0582 | 1.1372 |
| 16 | 1071 | {'atr_mult': 1.5, 'lookback': 20} | -0.0027 | -1.0878 |
| 17 | 1134 | {'atr_mult': 1.5, 'lookback': 15} | -0.0301 | -4.4858 |
| 18 | 1197 | {'atr_mult': 1.5, 'lookback': 20} | -0.2317 | -1.9805 |
| 19 | 1260 | {'atr_mult': 1.5, 'lookback': 15} | -0.2238 | 1.2411 |
| 20 | 1323 | {'atr_mult': 1.5, 'lookback': 20} | -0.1585 | 1.5757 |
| 21 | 1386 | {'atr_mult': 1.5, 'lookback': 15} | -0.0465 | -2.6218 |
| 22 | 1449 | {'atr_mult': 1.5, 'lookback': 15} | -0.1118 | 1.8594 |
| 23 | 1512 | {'atr_mult': 1.5, 'lookback': 15} | 0.005 | 2.213 |
| 24 | 1575 | {'atr_mult': 1.5, 'lookback': 15} | 0.0459 | 1.1919 |
| 25 | 1638 | {'atr_mult': 1.5, 'lookback': 15} | 0.126 | -0.9956 |
| 26 | 1701 | {'atr_mult': 1.5, 'lookback': 15} | 0.1012 | -0.1544 |
| 27 | 1764 | {'atr_mult': 1.5, 'lookback': 15} | 0.0862 | 0.9906 |
| 28 | 1827 | {'atr_mult': 1.5, 'lookback': 15} | 0.1147 | 0.8701 |
| 29 | 1890 | {'atr_mult': 1.5, 'lookback': 15} | 0.1392 | -1.6187 |
| 30 | 1953 | {'atr_mult': 1.5, 'lookback': 15} | 0.0966 | -0.1247 |
| 31 | 2016 | {'atr_mult': 1.5, 'lookback': 15} | 0.0904 | -3.7348 |
| 32 | 2079 | {'atr_mult': 1.5, 'lookback': 15} | -0.0129 | 2.1077 |
| 33 | 2142 | {'atr_mult': 1.5, 'lookback': 15} | 0.0364 | 0.4922 |
| 34 | 2205 | {'atr_mult': 1.5, 'lookback': 15} | 0.0502 | 1.0917 |
| 35 | 2268 | {'atr_mult': 1.5, 'lookback': 15} | 0.0749 | 4.3832 |
| 36 | 2331 | {'atr_mult': 1.5, 'lookback': 15} | 0.3066 | 1.1478 |
| 37 | 2394 | {'atr_mult': 1.5, 'lookback': 15} | 0.3216 | 0.7296 |
| 38 | 2457 | {'atr_mult': 1.5, 'lookback': 15} | 0.3382 | 2.1239 |
| 39 | 2520 | {'atr_mult': 1.5, 'lookback': 15} | 0.3854 | -3.8998 |
| 40 | 2583 | {'atr_mult': 1.5, 'lookback': 15} | 0.3286 | -2.6213 |
| 41 | 2646 | {'atr_mult': 1.5, 'lookback': 15} | 0.2766 | -2.7747 |
| 42 | 2709 | {'atr_mult': 1.5, 'lookback': 15} | 0.2212 | 2.9121 |
| 43 | 2772 | {'atr_mult': 1.5, 'lookback': 15} | 0.2555 | 1.3627 |
| 44 | 2835 | {'atr_mult': 1.5, 'lookback': 15} | 0.2725 | 2.9052 |
| 45 | 2898 | {'atr_mult': 1.5, 'lookback': 15} | 0.3698 | -0.5384 |
| 46 | 2961 | {'atr_mult': 1.5, 'lookback': 15} | 0.358 | 0.7823 |
| 47 | 3024 | {'atr_mult': 1.5, 'lookback': 15} | 0.3654 | -2.2302 |
| 48 | 3087 | {'atr_mult': 1.5, 'lookback': 15} | 0.3368 | 3.1156 |
| 49 | 3150 | {'atr_mult': 1.5, 'lookback': 15} | 0.3737 | 2.5589 |
| 50 | 3213 | {'atr_mult': 1.5, 'lookback': 15} | 0.3983 | -1.2566 |
| 51 | 3276 | {'atr_mult': 1.5, 'lookback': 15} | 0.3757 | -1.0659 |
| 52 | 3339 | {'atr_mult': 1.5, 'lookback': 15} | 0.3368 | 2.3903 |
| 53 | 3402 | {'atr_mult': 1.5, 'lookback': 15} | 0.3655 | -0.5138 |
| 54 | 3465 | {'atr_mult': 1.5, 'lookback': 15} | 0.3562 | -3.6823 |
| 55 | 3528 | {'atr_mult': 1.5, 'lookback': 15} | 0.3133 | -0.1892 |
| 56 | 3591 | {'atr_mult': 1.5, 'lookback': 15} | 0.3059 | 1.1059 |
| 57 | 3654 | {'atr_mult': 1.5, 'lookback': 15} | 0.3108 | -0.8506 |
| 58 | 3717 | {'atr_mult': 1.5, 'lookback': 15} | 0.3027 | 2.2748 |
| 59 | 3780 | {'atr_mult': 1.5, 'lookback': 15} | 0.3324 | 0.0576 |
| 60 | 3843 | {'atr_mult': 1.5, 'lookback': 15} | 0.3294 | 0.036 |
| 61 | 3906 | {'atr_mult': 1.5, 'lookback': 15} | 0.3267 | -0.5584 |
| 62 | 3969 | {'atr_mult': 1.5, 'lookback': 15} | 0.3199 | -0.6282 |
| 63 | 4032 | {'atr_mult': 1.5, 'lookback': 15} | 0.3123 | -0.2213 |
| 64 | 4095 | {'atr_mult': 1.5, 'lookback': 15} | 0.3073 | -2.4636 |
| 65 | 4158 | {'atr_mult': 1.5, 'lookback': 15} | 0.2861 | 0.2231 |
| 66 | 4221 | {'atr_mult': 1.5, 'lookback': 15} | 0.2834 | -2.568 |
| 67 | 4284 | {'atr_mult': 1.5, 'lookback': 15} | 0.2574 | 2.7158 |
| 68 | 4347 | {'atr_mult': 1.5, 'lookback': 15} | 0.2703 | -3.1816 |
| 69 | 4410 | {'atr_mult': 1.5, 'lookback': 15} | 0.2516 | 2.9014 |
| 70 | 4473 | {'atr_mult': 1.5, 'lookback': 15} | 0.2801 | -2.2531 |
| 71 | 4536 | {'atr_mult': 1.5, 'lookback': 15} | 0.2479 | -1.8527 |
| 72 | 4599 | {'atr_mult': 1.5, 'lookback': 15} | 0.2289 | 3.4946 |
| 73 | 4662 | {'atr_mult': 1.5, 'lookback': 15} | 0.3182 | 3.2574 |
| 74 | 4725 | {'atr_mult': 1.5, 'lookback': 15} | 0.3906 | 0.3735 |
| 75 | 4788 | {'atr_mult': 1.5, 'lookback': 15} | 0.3901 | -3.5091 |
| 76 | 4851 | {'atr_mult': 1.5, 'lookback': 15} | 0.3145 | -1.5255 |
| 77 | 4914 | {'atr_mult': 1.5, 'lookback': 15} | 0.2965 | 0.2796 |
| 78 | 4977 | {'atr_mult': 1.5, 'lookback': 15} | 0.2963 | -1.4444 |
| 79 | 5040 | {'atr_mult': 1.5, 'lookback': 15} | 0.2786 | 0.1294 |
| 80 | 5103 | {'atr_mult': 1.5, 'lookback': 15} | 0.277 | 1.8744 |
| 81 | 5166 | {'atr_mult': 1.5, 'lookback': 15} | 0.2887 | 0.4996 |
| 82 | 5229 | {'atr_mult': 1.5, 'lookback': 15} | 0.2914 | -1.3993 |
| 83 | 5292 | {'atr_mult': 1.5, 'lookback': 15} | 0.2756 | -1.1065 |
| 84 | 5355 | {'atr_mult': 1.5, 'lookback': 15} | 0.2613 | 0.4537 |
| 85 | 5418 | {'atr_mult': 1.5, 'lookback': 15} | 0.2633 | 0.2372 |
| 86 | 5481 | {'atr_mult': 1.5, 'lookback': 15} | 0.263 | 1.4421 |
| 87 | 5544 | {'atr_mult': 1.5, 'lookback': 15} | 0.2747 | -1.9566 |
| 88 | 5607 | {'atr_mult': 1.5, 'lookback': 15} | 0.2527 | 1.2032 |
| 89 | 5670 | {'atr_mult': 1.5, 'lookback': 15} | 0.257 | 0.8401 |
| 90 | 5733 | {'atr_mult': 1.5, 'lookback': 15} | 0.2635 | -3.1318 |
| 91 | 5796 | {'atr_mult': 1.5, 'lookback': 15} | 0.2354 | -0.7236 |
| 92 | 5859 | {'atr_mult': 1.5, 'lookback': 15} | 0.2251 | -3.3853 |
| 93 | 5922 | {'atr_mult': 1.5, 'lookback': 15} | 0.1926 | 0.1365 |
| 94 | 5985 | {'atr_mult': 1.5, 'lookback': 15} | 0.192 | 1.2355 |
| 95 | 6048 | {'atr_mult': 1.5, 'lookback': 15} | 0.2013 | -0.2702 |
| 96 | 6111 | {'atr_mult': 1.5, 'lookback': 20} | 0.2008 | 1.2132 |
| 97 | 6174 | {'atr_mult': 1.5, 'lookback': 20} | 0.2258 | -0.9117 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
