# I1 Gate Report — Sharpe OOS Walk-Forward

Generated: 2026-05-17T06:34:03.601834+00:00

## Gate criteria
- `sharpe_net_wf >= 0.8`
- `p_value_wf < 0.05`

| Symbol | Strategy | Sharpe gross WF | Sharpe net WF | Cost drag | Turnover | p-value WF | Trades | PASS |
|--------|----------|-----------------|---------------|-----------|----------|-----------|--------|------|
| BTCUSDT | ml_lgb_v1 | 7.443 | 3.203 | 4.240 | 1823.0 | 0.0050 | 1090 | PASS |
| ETHUSDT | ml_lgb_v1 | 10.094 | 7.445 | 2.648 | 1789.0 | 0.0000 | 1064 | PASS |
| EURUSD | mean_rev_v1 | 2.756 | 2.611 | 0.145 | 454.0 | 0.0090 | 454 | PASS |
| GBPUSD | ema_rsi_v1 | 3.819 | 2.216 | 1.603 | 2329.0 | 0.0270 | 2226 | PASS |
| USDJPY | vol_breakout_v1 | 2.976 | 2.969 | 0.007 | 1654.0 | 0.0030 | 1647 | PASS |
| US500 | ml_lgb_v1 | 12.061 | 10.076 | 1.985 | 671.0 | 0.0000 | 394 | PASS |
| US30 | mean_rev_v1 | 4.076 | 3.320 | 0.755 | 28.0 | 0.0310 | 28 | PASS |
| XAUUSD | Momentum | 2.614 | 2.609 | 0.005 | 1653.0 | 0.0010 | 1064 | PASS |

**GATE FASE 5:** APPROVED (8/8)