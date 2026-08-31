# Edge Robustness — 2026-08-31T04:56:32.333127+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## XAUUSD — vol_breakout_v1 {'lookback': 20, 'atr_mult': 2.0} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **0.4272** (aprobado: None) · holdout bars = 1497 · turnover = 170.0 · cost drag = 0.0881
- **Monte Carlo (holdout)** 500 paths: CI95 = [-0.3705, 1.1292], P(Sharpe>0) = 0.848 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.2036, 0.4596], P(Sharpe>0) = 0.802
- **Cost sweep**: Sharpe neto ×2 = 0.3393; anulación (≤0) en ×None; < gate 0.8 en ×1.0 -> PASS
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 2/2, single-regime = True -> FAIL
- **Anchored WF**: 116 folds, 61 positivos, OOS Sharpe neto = 0.1318 -> PASS

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | 0.4272 |
| 1.25 | 0.4052 |
| 1.5 | 0.3833 |
| 1.75 | 0.3613 |
| 2.0 | 0.3393 |
| 2.5 | 0.2955 |
| 3.0 | 0.2517 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'atr_mult': 1.5, 'lookback': 15} | -1.0887 | -3.4472 |
| 2 | 189 | {'atr_mult': 1.5, 'lookback': 20} | -1.5106 | 1.5701 |
| 3 | 252 | {'atr_mult': 1.5, 'lookback': 20} | -0.9926 | -2.038 |
| 4 | 315 | {'atr_mult': 1.5, 'lookback': 20} | -1.2523 | 2.8718 |
| 5 | 378 | {'atr_mult': 1.5, 'lookback': 20} | 0.681 | 0.2374 |
| 6 | 441 | {'atr_mult': 1.5, 'lookback': 20} | 0.5775 | 0.1473 |
| 7 | 504 | {'atr_mult': 1.5, 'lookback': 20} | 0.5314 | -1.7616 |
| 8 | 567 | {'atr_mult': 1.5, 'lookback': 20} | 0.3895 | -1.9659 |
| 9 | 630 | {'atr_mult': 1.5, 'lookback': 20} | 0.3219 | -0.6124 |
| 10 | 693 | {'atr_mult': 1.5, 'lookback': 20} | 0.2723 | -2.3195 |
| 11 | 756 | {'atr_mult': 1.5, 'lookback': 20} | 0.1316 | 0.8029 |
| 12 | 819 | {'atr_mult': 1.5, 'lookback': 20} | 0.1957 | -2.3295 |
| 13 | 882 | {'atr_mult': 1.5, 'lookback': 20} | 0.0485 | 0.8947 |
| 14 | 945 | {'atr_mult': 1.5, 'lookback': 20} | 0.1096 | 1.6812 |
| 15 | 1008 | {'atr_mult': 1.5, 'lookback': 20} | 0.2026 | 0.2702 |
| 16 | 1071 | {'atr_mult': 1.5, 'lookback': 20} | 0.2024 | 1.492 |
| 17 | 1134 | {'atr_mult': 1.5, 'lookback': 20} | 0.2265 | -2.5811 |
| 18 | 1197 | {'atr_mult': 1.5, 'lookback': 20} | 0.1133 | -0.5071 |
| 19 | 1260 | {'atr_mult': 1.5, 'lookback': 20} | 0.0785 | 0.046 |
| 20 | 1323 | {'atr_mult': 1.5, 'lookback': 20} | 0.0772 | 1.6195 |
| 21 | 1386 | {'atr_mult': 1.5, 'lookback': 20} | 0.1181 | -2.6958 |
| 22 | 1449 | {'atr_mult': 1.5, 'lookback': 20} | 0.0211 | -0.7787 |
| 23 | 1512 | {'atr_mult': 1.5, 'lookback': 20} | -0.0499 | -3.2563 |
| 24 | 1575 | {'atr_mult': 1.5, 'lookback': 20} | -0.1325 | -3.4166 |
| 25 | 1638 | {'atr_mult': 1.5, 'lookback': 20} | -0.2215 | -1.8706 |
| 26 | 1701 | {'atr_mult': 1.5, 'lookback': 20} | -0.2852 | 3.0072 |
| 27 | 1764 | {'atr_mult': 1.5, 'lookback': 20} | -0.2212 | -1.2458 |
| 28 | 1827 | {'atr_mult': 1.5, 'lookback': 20} | -0.2401 | 1.3822 |
| 29 | 1890 | {'atr_mult': 1.5, 'lookback': 20} | -0.207 | 2.7791 |
| 30 | 1953 | {'atr_mult': 1.5, 'lookback': 20} | -0.1449 | 2.5878 |
| 31 | 2016 | {'atr_mult': 1.5, 'lookback': 20} | -0.0397 | 0.7277 |
| 32 | 2079 | {'atr_mult': 1.5, 'lookback': 20} | -0.0144 | 1.3395 |
| 33 | 2142 | {'atr_mult': 1.5, 'lookback': 20} | 0.0928 | 0.4035 |
| 34 | 2205 | {'atr_mult': 1.5, 'lookback': 20} | 0.1444 | 0.2399 |
| 35 | 2268 | {'atr_mult': 1.5, 'lookback': 20} | 0.1468 | -1.6769 |
| 36 | 2331 | {'atr_mult': 1.5, 'lookback': 20} | 0.1011 | -3.3577 |
| 37 | 2394 | {'atr_mult': 1.5, 'lookback': 20} | 0.064 | -0.6401 |
| 38 | 2457 | {'atr_mult': 1.5, 'lookback': 20} | 0.0556 | 1.0551 |
| 39 | 2520 | {'atr_mult': 1.5, 'lookback': 20} | 0.0851 | 1.2402 |
| 40 | 2583 | {'atr_mult': 1.5, 'lookback': 20} | 0.1201 | -3.0564 |
| 41 | 2646 | {'atr_mult': 1.5, 'lookback': 20} | 0.0345 | 1.8527 |
| 42 | 2709 | {'atr_mult': 1.5, 'lookback': 20} | 0.0856 | 0.0426 |
| 43 | 2772 | {'atr_mult': 1.5, 'lookback': 20} | 0.0836 | 1.3029 |
| 44 | 2835 | {'atr_mult': 1.5, 'lookback': 20} | 0.1164 | -3.7702 |
| 45 | 2898 | {'atr_mult': 1.5, 'lookback': 20} | 0.0076 | -3.4626 |
| 46 | 2961 | {'atr_mult': 1.5, 'lookback': 20} | -0.0475 | -1.8105 |
| 47 | 3024 | {'atr_mult': 1.5, 'lookback': 20} | -0.0681 | 0.1639 |
| 48 | 3087 | {'atr_mult': 1.5, 'lookback': 20} | -0.0586 | -3.5561 |
| 49 | 3150 | {'atr_mult': 1.5, 'lookback': 20} | -0.1183 | -0.1179 |
| 50 | 3213 | {'atr_mult': 1.5, 'lookback': 20} | -0.1184 | -2.7963 |
| 51 | 3276 | {'atr_mult': 1.5, 'lookback': 20} | -0.1522 | -2.0775 |
| 52 | 3339 | {'atr_mult': 1.5, 'lookback': 20} | -0.1763 | -1.0781 |
| 53 | 3402 | {'atr_mult': 1.5, 'lookback': 20} | -0.189 | 2.4771 |
| 54 | 3465 | {'atr_mult': 1.5, 'lookback': 20} | -0.1523 | -0.576 |
| 55 | 3528 | {'atr_mult': 1.5, 'lookback': 20} | -0.1556 | 1.3175 |
| 56 | 3591 | {'atr_mult': 1.5, 'lookback': 20} | -0.0983 | 2.3357 |
| 57 | 3654 | {'atr_mult': 1.5, 'lookback': 20} | -0.058 | -0.0923 |
| 58 | 3717 | {'atr_mult': 1.5, 'lookback': 20} | -0.0282 | -1.3913 |
| 59 | 3780 | {'atr_mult': 1.5, 'lookback': 20} | -0.0415 | -3.6856 |
| 60 | 3843 | {'atr_mult': 1.5, 'lookback': 20} | -0.1 | -0.3184 |
| 61 | 3906 | {'atr_mult': 1.5, 'lookback': 20} | -0.1006 | -2.0167 |
| 62 | 3969 | {'atr_mult': 1.5, 'lookback': 20} | -0.1243 | 0.59 |
| 63 | 4032 | {'atr_mult': 1.5, 'lookback': 20} | -0.1173 | 1.327 |
| 64 | 4095 | {'atr_mult': 1.5, 'lookback': 20} | -0.0524 | 1.1602 |
| 65 | 4158 | {'atr_mult': 1.5, 'lookback': 20} | -0.0409 | -2.0183 |
| 66 | 4221 | {'atr_mult': 1.5, 'lookback': 20} | -0.0774 | 1.6224 |
| 67 | 4284 | {'atr_mult': 1.5, 'lookback': 20} | -0.0608 | 1.4505 |
| 68 | 4347 | {'atr_mult': 1.5, 'lookback': 20} | -0.0561 | -3.0415 |
| 69 | 4410 | {'atr_mult': 1.5, 'lookback': 20} | -0.0894 | 0.3223 |
| 70 | 4473 | {'atr_mult': 1.5, 'lookback': 20} | -0.0849 | 2.1932 |
| 71 | 4536 | {'atr_mult': 1.5, 'lookback': 20} | -0.0591 | -1.0508 |
| 72 | 4599 | {'atr_mult': 1.5, 'lookback': 20} | -0.0623 | 2.3616 |
| 73 | 4662 | {'atr_mult': 1.5, 'lookback': 20} | -0.0304 | 0.5502 |
| 74 | 4725 | {'atr_mult': 1.5, 'lookback': 20} | -0.024 | 2.1815 |
| 75 | 4788 | {'atr_mult': 1.5, 'lookback': 20} | -0.0004 | -0.2737 |
| 76 | 4851 | {'atr_mult': 1.5, 'lookback': 20} | -0.0017 | -0.6215 |
| 77 | 4914 | {'atr_mult': 1.5, 'lookback': 20} | -0.0063 | -0.5291 |
| 78 | 4977 | {'atr_mult': 1.5, 'lookback': 20} | -0.0104 | 0.3668 |
| 79 | 5040 | {'atr_mult': 1.5, 'lookback': 20} | -0.0078 | 3.3214 |
| 80 | 5103 | {'atr_mult': 1.5, 'lookback': 20} | 0.0085 | 1.1277 |
| 81 | 5166 | {'atr_mult': 1.5, 'lookback': 20} | 0.0149 | 0.4557 |
| 82 | 5229 | {'atr_mult': 1.5, 'lookback': 20} | 0.0172 | 0.2156 |
| 83 | 5292 | {'atr_mult': 1.5, 'lookback': 20} | 0.0186 | -1.0338 |
| 84 | 5355 | {'atr_mult': 1.5, 'lookback': 20} | 0.0118 | 0.9231 |
| 85 | 5418 | {'atr_mult': 1.5, 'lookback': 20} | 0.0187 | -0.2487 |
| 86 | 5481 | {'atr_mult': 1.5, 'lookback': 20} | 0.0175 | 1.9427 |
| 87 | 5544 | {'atr_mult': 1.5, 'lookback': 20} | 0.0282 | -0.7424 |
| 88 | 5607 | {'atr_mult': 1.5, 'lookback': 20} | 0.0236 | 2.4811 |
| 89 | 5670 | {'atr_mult': 1.5, 'lookback': 20} | 0.0514 | -1.9635 |
| 90 | 5733 | {'atr_mult': 1.5, 'lookback': 20} | 0.0416 | 1.3833 |
| 91 | 5796 | {'atr_mult': 1.5, 'lookback': 20} | 0.0494 | 3.0295 |
| 92 | 5859 | {'atr_mult': 1.5, 'lookback': 20} | 0.0882 | 1.4604 |
| 93 | 5922 | {'atr_mult': 1.5, 'lookback': 20} | 0.1028 | -1.0631 |
| 94 | 5985 | {'atr_mult': 1.5, 'lookback': 20} | 0.1007 | -1.9909 |
| 95 | 6048 | {'atr_mult': 1.5, 'lookback': 20} | 0.0698 | -2.6457 |
| 96 | 6111 | {'atr_mult': 1.5, 'lookback': 20} | 0.043 | 2.5766 |
| 97 | 6174 | {'atr_mult': 1.5, 'lookback': 20} | 0.0615 | -1.4511 |
| 98 | 6237 | {'atr_mult': 1.5, 'lookback': 20} | 0.0488 | 1.7473 |
| 99 | 6300 | {'atr_mult': 1.5, 'lookback': 20} | 0.0561 | -1.1298 |
| 100 | 6363 | {'atr_mult': 1.5, 'lookback': 20} | 0.0414 | 1.8011 |
| 101 | 6426 | {'atr_mult': 1.5, 'lookback': 20} | 0.0559 | -1.3682 |
| 102 | 6489 | {'atr_mult': 1.5, 'lookback': 20} | 0.0431 | 1.1148 |
| 103 | 6552 | {'atr_mult': 1.5, 'lookback': 20} | 0.0558 | -5.5657 |
| 104 | 6615 | {'atr_mult': 1.5, 'lookback': 20} | 0.0286 | -2.4948 |
| 105 | 6678 | {'atr_mult': 1.5, 'lookback': 20} | 0.0101 | 3.6949 |
| 106 | 6741 | {'atr_mult': 1.5, 'lookback': 20} | 0.0266 | 0.9854 |
| 107 | 6804 | {'atr_mult': 1.5, 'lookback': 20} | 0.0319 | 4.8099 |
| 108 | 6867 | {'atr_mult': 1.5, 'lookback': 20} | 0.0656 | -2.1802 |
| 109 | 6930 | {'atr_mult': 1.5, 'lookback': 20} | 0.0445 | -1.3447 |
| 110 | 6993 | {'atr_mult': 1.5, 'lookback': 20} | 0.0347 | 1.0687 |
| 111 | 7056 | {'atr_mult': 1.5, 'lookback': 20} | 0.042 | 4.4886 |
| 112 | 7119 | {'atr_mult': 1.5, 'lookback': 20} | 0.0681 | -0.3113 |
| 113 | 7182 | {'atr_mult': 1.5, 'lookback': 20} | 0.0634 | -0.8049 |
| 114 | 7245 | {'atr_mult': 1.5, 'lookback': 20} | 0.0568 | 1.5226 |
| 115 | 7308 | {'atr_mult': 1.5, 'lookback': 20} | 0.072 | 1.1831 |
| 116 | 7371 | {'atr_mult': 1.5, 'lookback': 20} | 0.0949 | 2.4802 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
