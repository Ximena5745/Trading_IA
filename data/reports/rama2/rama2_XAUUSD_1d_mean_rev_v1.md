# Edge Robustness — 2026-08-31T04:56:39.264306+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## XAUUSD — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **-0.543** (aprobado: None) · holdout bars = 1497 · turnover = 126.0 · cost drag = 0.0608
- **Monte Carlo (holdout)** 500 paths: CI95 = [-1.4152, 0.1415], P(Sharpe>0) = 0.072 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.7054, -0.051], P(Sharpe>0) = 0.014
- **Cost sweep**: Sharpe neto ×2 = -0.6038; anulación (≤0) en ×1.0; < gate 0.8 en ×1.0 -> FAIL
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 0/2, single-regime = True -> FAIL
- **Anchored WF**: 116 folds, 50 positivos, OOS Sharpe neto = -0.4117 -> FAIL

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | -0.543 |
| 1.25 | -0.5582 |
| 1.5 | -0.5734 |
| 1.75 | -0.5886 |
| 2.0 | -0.6038 |
| 2.5 | -0.6342 |
| 3.0 | -0.6646 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 1.48 | 0.0 |
| 2 | 189 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 1.2067 | -0.3696 |
| 3 | 252 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.9786 | 2.8189 |
| 4 | 315 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 1.4625 | -3.3594 |
| 5 | 378 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.6903 | 1.2144 |
| 6 | 441 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.4551 | 0.223 |
| 7 | 504 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.365 | -1.2499 |
| 8 | 567 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3892 | -1.2715 |
| 9 | 630 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3791 | -2.27 |
| 10 | 693 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.3569 | 1.8912 |
| 11 | 756 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.223 | -1.3334 |
| 12 | 819 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.3205 | 1.3833 |
| 13 | 882 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.2325 | -1.1325 |
| 14 | 945 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.29 | -1.0446 |
| 15 | 1008 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.3354 | -1.9891 |
| 16 | 1071 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.3855 | 3.0097 |
| 17 | 1134 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.227 | 1.4078 |
| 18 | 1197 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.1772 | -0.5517 |
| 19 | 1260 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.1984 | -0.5145 |
| 20 | 1323 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2034 | -0.4853 |
| 21 | 1386 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2005 | 2.3689 |
| 22 | 1449 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.1307 | -0.158 |
| 23 | 1512 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.0952 | -1.3474 |
| 24 | 1575 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.1152 | 2.5951 |
| 25 | 1638 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.0598 | 1.4716 |
| 26 | 1701 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.0131 | -3.7512 |
| 27 | 1764 | {'rsi_overbought': 70, 'rsi_oversold': 30} | -0.0795 | 0.3102 |
| 28 | 1827 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.0484 | -2.5339 |
| 29 | 1890 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.0912 | -2.9249 |
| 30 | 1953 | {'rsi_overbought': 70, 'rsi_oversold': 25} | -0.1488 | -1.9364 |
| 31 | 2016 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1966 | 0.3405 |
| 32 | 2079 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1893 | 1.0002 |
| 33 | 2142 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1085 | -1.6099 |
| 34 | 2205 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.141 | 0.9897 |
| 35 | 2268 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.131 | 1.7249 |
| 36 | 2331 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0633 | 2.9944 |
| 37 | 2394 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0264 | 2.9138 |
| 38 | 2457 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0225 | -1.65 |
| 39 | 2520 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0589 | -2.4792 |
| 40 | 2583 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1323 | 3.4153 |
| 41 | 2646 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.02 | 0.4641 |
| 42 | 2709 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0078 | -0.4584 |
| 43 | 2772 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0227 | -1.71 |
| 44 | 2835 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.064 | 0.5947 |
| 45 | 2898 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0465 | 1.5599 |
| 46 | 2961 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0232 | -2.5791 |
| 47 | 3024 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0463 | -2.2072 |
| 48 | 3087 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0702 | 0.0 |
| 49 | 3150 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.0695 | -1.5682 |
| 50 | 3213 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0973 | 0.1903 |
| 51 | 3276 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0939 | 0.1887 |
| 52 | 3339 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0899 | 1.8278 |
| 53 | 3402 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0675 | 2.23 |
| 54 | 3465 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0549 | -2.9151 |
| 55 | 3528 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0644 | 0.0138 |
| 56 | 3591 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0625 | 2.5497 |
| 57 | 3654 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0335 | -0.0075 |
| 58 | 3717 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0691 | -0.5976 |
| 59 | 3780 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0735 | 0.0 |
| 60 | 3843 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0724 | 1.1265 |
| 61 | 3906 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0666 | 1.3863 |
| 62 | 3969 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0466 | -1.3232 |
| 63 | 4032 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0686 | -2.5496 |
| 64 | 4095 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.185 | 0.8635 |
| 65 | 4158 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1752 | 2.9205 |
| 66 | 4221 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1581 | 1.0072 |
| 67 | 4284 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1428 | -1.9468 |
| 68 | 4347 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1488 | -0.2076 |
| 69 | 4410 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1486 | 1.3076 |
| 70 | 4473 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1212 | -3.4367 |
| 71 | 4536 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1522 | 0.0 |
| 72 | 4599 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.1511 | -1.6089 |
| 73 | 4662 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.173 | -1.3932 |
| 74 | 4725 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1812 | -2.0881 |
| 75 | 4788 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.201 | 0.0092 |
| 76 | 4851 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1994 | 0.0 |
| 77 | 4914 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1981 | 0.0765 |
| 78 | 4977 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1957 | 1.0917 |
| 79 | 5040 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.188 | -3.6839 |
| 80 | 5103 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2053 | 1.6868 |
| 81 | 5166 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2012 | -2.1417 |
| 82 | 5229 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2079 | -0.4894 |
| 83 | 5292 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.2096 | 1.9378 |
| 84 | 5355 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2033 | -0.9096 |
| 85 | 5418 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2084 | 2.7226 |
| 86 | 5481 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.1999 | -2.3463 |
| 87 | 5544 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2063 | 0.535 |
| 88 | 5607 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2026 | -3.0745 |
| 89 | 5670 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2251 | -2.0161 |
| 90 | 5733 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2241 | -2.7921 |
| 91 | 5796 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2463 | -1.6412 |
| 92 | 5859 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2669 | -4.0232 |
| 93 | 5922 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3055 | -0.8726 |
| 94 | 5985 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3098 | 0.2495 |
| 95 | 6048 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3057 | 1.3722 |
| 96 | 6111 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2876 | -1.0265 |
| 97 | 6174 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2941 | 0.3606 |
| 98 | 6237 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2889 | -2.2077 |
| 99 | 6300 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2923 | -0.7062 |
| 100 | 6363 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2978 | -1.6396 |
| 101 | 6426 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3053 | 0.7828 |
| 102 | 6489 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2961 | -2.9193 |
| 103 | 6552 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.303 | 0.9129 |
| 104 | 6615 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2986 | 1.2692 |
| 105 | 6678 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2921 | -3.1172 |
| 106 | 6741 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.306 | 0.4526 |
| 107 | 6804 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2996 | -4.6848 |
| 108 | 6867 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3357 | -2.9923 |
| 109 | 6930 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3472 | 1.4505 |
| 110 | 6993 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3346 | -1.3421 |
| 111 | 7056 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3399 | -3.8832 |
| 112 | 7119 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3568 | -1.5527 |
| 113 | 7182 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3693 | -0.3218 |
| 114 | 7245 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.369 | 0.9505 |
| 115 | 7308 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3429 | 0.7277 |
| 116 | 7371 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2935 | -2.5063 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
