# Edge Robustness — 2026-08-31T04:58:54.151343+00:00

Gate F2-(b) criteria · timeframe: 1d · periods/year: 252 · paths: 500 · block: 5 bars

## GBPUSD — mean_rev_v1 {'rsi_oversold': 30, 'rsi_overbought': 70} — **FRAGILE**

- Holdout Sharpe neto (recalculado): **0.4138** (aprobado: None) · holdout bars = 752 · turnover = 62.0 · cost drag = 0.0576
- **Monte Carlo (holdout)** 500 paths: CI95 = [-0.8104, 1.4327], P(Sharpe>0) = 0.75 -> FAIL
- Monte Carlo (full sample, contexto): CI95 = [-0.4349, 0.5986], P(Sharpe>0) = 0.64
- **Cost sweep**: Sharpe neto ×2 = 0.3562; anulación (≤0) en ×None; < gate 0.8 en ×1.0 -> PASS
- **Regime**: ADX+ buckets = 2/2, vol+ buckets = 1/2, single-regime = True -> FAIL
- **Anchored WF**: 57 folds, 30 positivos, OOS Sharpe neto = 0.0205 -> PASS

| Cost × | Sharpe net |
|--:|--:|
| 1.0 | 0.4138 |
| 1.25 | 0.3994 |
| 1.5 | 0.385 |
| 1.75 | 0.3706 |
| 2.0 | 0.3562 |
| 2.5 | 0.3273 |
| 3.0 | 0.2984 |

| Fold | train bars | best params | IS Sharpe | OOS Sharpe |
|--:|--:|---|--:|--:|
| 1 | 126 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -0.3278 | -3.8465 |
| 2 | 189 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -1.6418 | 0.4309 |
| 3 | 252 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -1.095 | -1.6343 |
| 4 | 315 | {'rsi_overbought': 75, 'rsi_oversold': 25} | -1.1943 | 1.117 |
| 5 | 378 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.3708 | -3.0784 |
| 6 | 441 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.6862 | 1.883 |
| 7 | 504 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.2109 | 3.7418 |
| 8 | 567 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0228 | -0.7027 |
| 9 | 630 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0211 | 1.7155 |
| 10 | 693 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.2648 | -0.8991 |
| 11 | 756 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.1561 | -0.9928 |
| 12 | 819 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0003 | 1.5369 |
| 13 | 882 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0414 | -3.3449 |
| 14 | 945 | {'rsi_overbought': 75, 'rsi_oversold': 30} | -0.0382 | 1.5626 |
| 15 | 1008 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.1038 | -1.4218 |
| 16 | 1071 | {'rsi_overbought': 75, 'rsi_oversold': 30} | 0.0216 | -1.1644 |
| 17 | 1134 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3721 | -2.5089 |
| 18 | 1197 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1943 | 2.9285 |
| 19 | 1260 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.282 | 2.0969 |
| 20 | 1323 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3429 | 2.411 |
| 21 | 1386 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3902 | -0.4085 |
| 22 | 1449 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3677 | 2.3864 |
| 23 | 1512 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3822 | -1.6213 |
| 24 | 1575 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.307 | 0.9581 |
| 25 | 1638 | {'rsi_overbought': 70, 'rsi_oversold': 30} | 0.3255 | -1.0121 |
| 26 | 1701 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3192 | 3.209 |
| 27 | 1764 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4104 | 1.7056 |
| 28 | 1827 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.431 | 1.5215 |
| 29 | 1890 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4467 | 2.9686 |
| 30 | 1953 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4915 | -2.6315 |
| 31 | 2016 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4022 | 2.4351 |
| 32 | 2079 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.4467 | -2.1427 |
| 33 | 2142 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2836 | -3.5093 |
| 34 | 2205 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2288 | 2.3591 |
| 35 | 2268 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.257 | -0.1252 |
| 36 | 2331 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2497 | 1.4731 |
| 37 | 2394 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2576 | 1.2859 |
| 38 | 2457 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2773 | 4.277 |
| 39 | 2520 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3165 | 2.501 |
| 40 | 2583 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3383 | -1.7238 |
| 41 | 2646 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2814 | 2.0976 |
| 42 | 2709 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.3313 | -1.7266 |
| 43 | 2772 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2349 | -1.3993 |
| 44 | 2835 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2261 | 3.3807 |
| 45 | 2898 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2398 | -2.6762 |
| 46 | 2961 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1917 | 3.204 |
| 47 | 3024 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2121 | 0.8036 |
| 48 | 3087 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2193 | -1.6613 |
| 49 | 3150 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2039 | -2.8485 |
| 50 | 3213 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.175 | -1.631 |
| 51 | 3276 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1572 | 2.0635 |
| 52 | 3339 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1759 | 2.3277 |
| 53 | 3402 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2247 | -0.7696 |
| 54 | 3465 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2176 | 1.127 |
| 55 | 3528 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.2217 | -0.9015 |
| 56 | 3591 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.216 | -1.1521 |
| 57 | 3654 | {'rsi_overbought': 70, 'rsi_oversold': 25} | 0.1955 | 1.2392 |

_Generated by scripts/run_edge_robustness.py — SPEC-C02._
