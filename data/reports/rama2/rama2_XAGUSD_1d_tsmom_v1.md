# Edge Robustness — 2026-08-31T04:57:02.381177+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## XAGUSD — tsmom_v1 {'lookback': 12, 'min_adx': 20} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **0.1271** (aprobado: None) · holdout bars = 1256 · turnover = 206.0 · cost drag = 0.0584
- **Monte Carlo (holdout)** 500 paths: CI95 = [-0.684, 1.1264], P(Sharpe>0) = 0.652 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.07, 0.6524], P(Sharpe>0) = 0.96
- **Cost sweep**: Sharpe neto ×2 = 0.069; anulación (≤0) en ×None; < gate 0.8 en ×1.0 -> PASS
- **Regime**: ADX+ buckets = 1/2, vol+ buckets = 2/2, single-regime = True -> FAIL
- **Anchored WF**: 97 folds, 54 positivos, OOS Sharpe neto = 0.3431 -> PASS

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | 0.1271 |
| 1.25 | 0.1126 |
| 1.5 | 0.098 |
| 1.75 | 0.0835 |
| 2.0 | 0.069 |
| 2.5 | 0.0401 |
| 3.0 | 0.0112 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'lookback': 24, 'min_adx': 22} | 0.0088 | 0.2072 |
| 2 | 189 | {'lookback': 10, 'min_adx': 18} | 0.4661 | 0.2455 |
| 3 | 252 | {'lookback': 24, 'min_adx': 22} | 0.4738 | -0.8225 |
| 4 | 315 | {'lookback': 24, 'min_adx': 18} | 0.1948 | 2.8078 |
| 5 | 378 | {'lookback': 24, 'min_adx': 18} | 0.761 | -1.5923 |
| 6 | 441 | {'lookback': 12, 'min_adx': 22} | 0.6912 | -2.1436 |
| 7 | 504 | {'lookback': 12, 'min_adx': 22} | 0.3515 | 1.7651 |
| 8 | 567 | {'lookback': 12, 'min_adx': 22} | 0.4876 | -1.8377 |
| 9 | 630 | {'lookback': 12, 'min_adx': 22} | 0.195 | -2.661 |
| 10 | 693 | {'lookback': 12, 'min_adx': 18} | 0.0232 | -0.5731 |
| 11 | 756 | {'lookback': 10, 'min_adx': 18} | 0.0564 | -3.7959 |
| 12 | 819 | {'lookback': 12, 'min_adx': 18} | 0.0612 | -0.4231 |
| 13 | 882 | {'lookback': 12, 'min_adx': 22} | 0.0648 | 2.0583 |
| 14 | 945 | {'lookback': 12, 'min_adx': 22} | 0.3334 | -0.7092 |
| 15 | 1008 | {'lookback': 10, 'min_adx': 18} | 0.329 | 0.8888 |
| 16 | 1071 | {'lookback': 10, 'min_adx': 18} | 0.3463 | 0.6639 |
| 17 | 1134 | {'lookback': 10, 'min_adx': 18} | 0.3626 | -0.07 |
| 18 | 1197 | {'lookback': 10, 'min_adx': 18} | 0.3303 | 1.385 |
| 19 | 1260 | {'lookback': 10, 'min_adx': 18} | 0.3664 | 1.0091 |
| 20 | 1323 | {'lookback': 10, 'min_adx': 18} | 0.378 | 1.7968 |
| 21 | 1386 | {'lookback': 10, 'min_adx': 18} | 0.4396 | 1.9414 |
| 22 | 1449 | {'lookback': 10, 'min_adx': 18} | 0.4949 | 2.7055 |
| 23 | 1512 | {'lookback': 10, 'min_adx': 18} | 0.6204 | 0.4581 |
| 24 | 1575 | {'lookback': 10, 'min_adx': 18} | 0.6134 | 0.2964 |
| 25 | 1638 | {'lookback': 10, 'min_adx': 18} | 0.5653 | -0.9789 |
| 26 | 1701 | {'lookback': 10, 'min_adx': 18} | 0.4924 | 2.4898 |
| 27 | 1764 | {'lookback': 10, 'min_adx': 18} | 0.5615 | 2.8299 |
| 28 | 1827 | {'lookback': 10, 'min_adx': 18} | 0.6415 | 0.3605 |
| 29 | 1890 | {'lookback': 10, 'min_adx': 18} | 0.6373 | -0.5097 |
| 30 | 1953 | {'lookback': 10, 'min_adx': 18} | 0.6135 | 2.4217 |
| 31 | 2016 | {'lookback': 10, 'min_adx': 18} | 0.6708 | -4.5279 |
| 32 | 2079 | {'lookback': 10, 'min_adx': 18} | 0.5551 | 2.5611 |
| 33 | 2142 | {'lookback': 10, 'min_adx': 18} | 0.5804 | -1.1501 |
| 34 | 2205 | {'lookback': 10, 'min_adx': 18} | 0.5378 | -0.0352 |
| 35 | 2268 | {'lookback': 10, 'min_adx': 18} | 0.5235 | 3.0672 |
| 36 | 2331 | {'lookback': 10, 'min_adx': 18} | 0.6346 | -1.987 |
| 37 | 2394 | {'lookback': 10, 'min_adx': 18} | 0.5666 | 0.2048 |
| 38 | 2457 | {'lookback': 10, 'min_adx': 18} | 0.5509 | 0.5078 |
| 39 | 2520 | {'lookback': 10, 'min_adx': 18} | 0.5499 | 0.3347 |
| 40 | 2583 | {'lookback': 10, 'min_adx': 18} | 0.545 | -0.4534 |
| 41 | 2646 | {'lookback': 10, 'min_adx': 18} | 0.5243 | -1.3861 |
| 42 | 2709 | {'lookback': 10, 'min_adx': 18} | 0.4956 | 3.0478 |
| 43 | 2772 | {'lookback': 10, 'min_adx': 18} | 0.5287 | 2.4541 |
| 44 | 2835 | {'lookback': 10, 'min_adx': 18} | 0.5628 | 2.4444 |
| 45 | 2898 | {'lookback': 10, 'min_adx': 18} | 0.6065 | 0.338 |
| 46 | 2961 | {'lookback': 10, 'min_adx': 18} | 0.6 | -0.0118 |
| 47 | 3024 | {'lookback': 10, 'min_adx': 18} | 0.5776 | -1.336 |
| 48 | 3087 | {'lookback': 10, 'min_adx': 18} | 0.5509 | 0.709 |
| 49 | 3150 | {'lookback': 10, 'min_adx': 18} | 0.5512 | 0.6093 |
| 50 | 3213 | {'lookback': 10, 'min_adx': 18} | 0.5521 | 4.4401 |
| 51 | 3276 | {'lookback': 10, 'min_adx': 18} | 0.5891 | -5.1057 |
| 52 | 3339 | {'lookback': 10, 'min_adx': 18} | 0.4828 | -0.1282 |
| 53 | 3402 | {'lookback': 10, 'min_adx': 18} | 0.4792 | -1.5324 |
| 54 | 3465 | {'lookback': 10, 'min_adx': 18} | 0.4551 | -0.6209 |
| 55 | 3528 | {'lookback': 10, 'min_adx': 18} | 0.4421 | -0.2872 |
| 56 | 3591 | {'lookback': 10, 'min_adx': 18} | 0.4251 | -0.3738 |
| 57 | 3654 | {'lookback': 10, 'min_adx': 18} | 0.4159 | 2.1211 |
| 58 | 3717 | {'lookback': 10, 'min_adx': 18} | 0.436 | 0.9868 |
| 59 | 3780 | {'lookback': 10, 'min_adx': 18} | 0.4432 | 0.1107 |
| 60 | 3843 | {'lookback': 10, 'min_adx': 18} | 0.4345 | 1.7811 |
| 61 | 3906 | {'lookback': 10, 'min_adx': 18} | 0.4549 | 0.3585 |
| 62 | 3969 | {'lookback': 10, 'min_adx': 18} | 0.4536 | 2.2956 |
| 63 | 4032 | {'lookback': 10, 'min_adx': 18} | 0.463 | -0.1171 |
| 64 | 4095 | {'lookback': 10, 'min_adx': 18} | 0.4528 | -0.73 |
| 65 | 4158 | {'lookback': 10, 'min_adx': 18} | 0.4444 | 1.6163 |
| 66 | 4221 | {'lookback': 10, 'min_adx': 18} | 0.4541 | -4.2201 |
| 67 | 4284 | {'lookback': 10, 'min_adx': 18} | 0.4186 | -0.7762 |
| 68 | 4347 | {'lookback': 10, 'min_adx': 18} | 0.4111 | -2.6319 |
| 69 | 4410 | {'lookback': 10, 'min_adx': 18} | 0.3926 | 3.92 |
| 70 | 4473 | {'lookback': 10, 'min_adx': 18} | 0.4249 | -2.9937 |
| 71 | 4536 | {'lookback': 10, 'min_adx': 18} | 0.387 | -1.1779 |
| 72 | 4599 | {'lookback': 10, 'min_adx': 18} | 0.373 | 1.9492 |
| 73 | 4662 | {'lookback': 10, 'min_adx': 18} | 0.4054 | 3.4569 |
| 74 | 4725 | {'lookback': 10, 'min_adx': 18} | 0.4784 | -0.7038 |
| 75 | 4788 | {'lookback': 10, 'min_adx': 18} | 0.4625 | 0.6666 |
| 76 | 4851 | {'lookback': 10, 'min_adx': 18} | 0.4656 | -1.9418 |
| 77 | 4914 | {'lookback': 10, 'min_adx': 18} | 0.4414 | 2.0188 |
| 78 | 4977 | {'lookback': 10, 'min_adx': 18} | 0.4538 | 1.2273 |
| 79 | 5040 | {'lookback': 10, 'min_adx': 18} | 0.4571 | -0.6408 |
| 80 | 5103 | {'lookback': 10, 'min_adx': 18} | 0.4505 | 0.9069 |
| 81 | 5166 | {'lookback': 10, 'min_adx': 18} | 0.4531 | -0.1592 |
| 82 | 5229 | {'lookback': 10, 'min_adx': 18} | 0.4506 | -4.3875 |
| 83 | 5292 | {'lookback': 10, 'min_adx': 18} | 0.385 | 1.2039 |
| 84 | 5355 | {'lookback': 10, 'min_adx': 18} | 0.3948 | 1.0781 |
| 85 | 5418 | {'lookback': 10, 'min_adx': 18} | 0.4012 | 0.0662 |
| 86 | 5481 | {'lookback': 10, 'min_adx': 18} | 0.3983 | 0.9966 |
| 87 | 5544 | {'lookback': 10, 'min_adx': 18} | 0.3979 | 0.5794 |
| 88 | 5607 | {'lookback': 10, 'min_adx': 18} | 0.3989 | 0.3872 |
| 89 | 5670 | {'lookback': 10, 'min_adx': 18} | 0.3963 | -0.5315 |
| 90 | 5733 | {'lookback': 10, 'min_adx': 18} | 0.3758 | -0.2937 |
| 91 | 5796 | {'lookback': 10, 'min_adx': 18} | 0.3706 | -1.2721 |
| 92 | 5859 | {'lookback': 10, 'min_adx': 18} | 0.3546 | 1.0178 |
| 93 | 5922 | {'lookback': 10, 'min_adx': 18} | 0.3621 | -0.5893 |
| 94 | 5985 | {'lookback': 10, 'min_adx': 18} | 0.3513 | 4.4038 |
| 95 | 6048 | {'lookback': 10, 'min_adx': 18} | 0.3785 | 2.6279 |
| 96 | 6111 | {'lookback': 10, 'min_adx': 18} | 0.4145 | 0.7687 |
| 97 | 6174 | {'lookback': 10, 'min_adx': 18} | 0.4235 | -0.101 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
