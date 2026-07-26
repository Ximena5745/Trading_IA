# I1 Gate Report — Sharpe OOS Walk-Forward

Generated: 2026-07-26T06:54:29.385961+00:00

## Gate criteria
- `sharpe_net_wf >= 0.8`
- `p_value_wf < 0.05`
- `sharpe_net_holdout >= 0.8` (unseen 20% holdout, never used in WF param search)

| Symbol | Strategy | Sharpe gross WF | Sharpe net WF | Sharpe net Holdout | Cost drag | Turnover | p-value WF | Trades | PASS |
|--------|----------|-----------------|---------------|---------------------|-----------|----------|-----------|--------|------|
| BTCUSDT | vol_breakout_v1 | 3.051 | 1.698 | -2.170 | 1.352 | 405.0 | 0.0470 | 405 | FAIL |
| ETHUSDT | vol_breakout_v1 | 2.650 | 1.874 | -2.102 | 0.776 | 355.0 | 0.0490 | 355 | FAIL |
| EURUSD | BB_ZScore | 2.683 | 2.446 | -0.977 | 0.237 | 1051.0 | 0.0150 | 1042 | FAIL |
| GBPUSD | ema_rsi_v1 | 3.819 | 2.216 | -0.951 | 1.603 | 2329.0 | 0.0270 | 2226 | FAIL |
| USDJPY | vol_breakout_v1 | 2.976 | 2.969 | -1.487 | 0.007 | 1654.0 | 0.0030 | 1647 | FAIL |
| US500 | tsmom_v1 | 3.461 | 2.440 | -3.961 | 1.021 | 309.0 | 0.1000 | 197 | FAIL |
| US30 | mean_rev_v1 | 4.076 | 3.320 | 0.640 | 0.755 | 28.0 | 0.0310 | 28 | FAIL |
| XAUUSD | Momentum | 2.614 | 2.609 | 1.323 | 0.005 | 1653.0 | 0.0010 | 1064 | PASS |

**GATE FASE 5:** BLOCKED (1/8)