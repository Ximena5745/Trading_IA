# API Reference — Dashboard Endpoints

## 🎯 Quick Start

```bash
# Start server
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Access dashboard
http://127.0.0.1:8000/dashboard

# Check health
http://127.0.0.1:8000/health

# View metrics
http://127.0.0.1:8001/metrics
```

---

## 📊 Market Data Endpoints

### Get All Symbols
```
GET /market/symbols

Response:
["EURUSD", "GBPUSD", "USDJPY", "US30", "US500", "XAUUSD"]
```

### Get Market Data (OHLCV + Indicators)
```
GET /market/{symbol}/data
  ?limit=100          (default: 100, max: 500)
  &timeframe=1d       (required: 1d, 1h, 4h, 1wk, 1mo, 6mo)

Response:
{
  "symbol": "EURUSD",
  "timeframe": "1d",
  "count": 518,
  "data": [
    {
      "timestamp": "2024-01-02T00:00:00",
      "open": 1.0820,
      "high": 1.0845,
      "low": 1.0810,
      "close": 1.0835,
      "volume": 2500000,
      "rsi_14": 45.23,
      "rsi_7": 42.10,
      "macd_line": -0.0025,
      "macd_signal": -0.0020,
      "macd_histogram": -0.0005,
      "bb_upper": 1.0890,
      "bb_lower": 1.0780,
      "bb_width": 0.0110,
      "atr_14": 0.0035,
      "volume_ratio": 1.2,
      "ema_9": 1.0825
    },
    ...
  ]
}
```

### Get Technical Features
```
GET /market/{symbol}/features

Response:
{
  "rsi_14": 45.23,
  "rsi_7": 42.10,
  "macd_line": -0.0025,
  "macd_signal": -0.0020,
  "macd_histogram": -0.0005,
  "bb_upper": 1.0890,
  "bb_lower": 1.0780,
  "bb_width": 0.0110,
  "atr_14": 0.0035,
  "volume_ratio": 1.2,
  "technical_score": 0.3,
  "regime_score": 0.5,
  "micro_score": 0.1,
  "regime": "BULL TRENDING",
  "fundamental_status": "CLEAR",
  "consensus_score": 0.45,
  "sl": 1.0780,
  "tp": 1.0890
}
```

**Available Symbols**: EURUSD, GBPUSD, USDJPY, US30, US500, XAUUSD  
**Available Timeframes**: 1d, 1h, 4h, 1wk, 1mo (limited), 6mo (limited)

---

## 📈 Signals Endpoints

### List All Signals
```
GET /signals
  ?symbol=EURUSD      (optional filter)
  &status=pending     (optional: pending, executed, cancelled)
  &limit=50           (default: 50, max: 200)

Response:
{
  "count": 2,
  "signals": [
    {
      "id": "sig_001",
      "symbol": "EURUSD",
      "action": "BUY",
      "entry": 1.0845,
      "sl": 1.0790,
      "tp": 1.0920,
      "rr": 1.4,
      "confidence": 0.62,
      "status": "pending",
      "timestamp": "2026-04-06T03:00:00",
      "explanation": [
        {
          "factor": "EMA Cross",
          "weight": 0.25,
          "direction": "bullish"
        }
      ],
      "summary": "Bullish EMA crossover on weekly chart..."
    },
    ...
  ]
}
```

### Get Latest Signal for Symbol
```
GET /signals/latest/{symbol}

Response:
{
  "id": "sig_001",
  "symbol": "EURUSD",
  "action": "BUY",
  "entry": 1.0845,
  ...
}
```

---

## 💼 Portfolio Endpoints (Public)

### Get Portfolio State
```
GET /portfolio/public

Response:
{
  "user_id": "demo",
  "total_capital": 10000.0,
  "available_capital": 9500.0,
  "positions": [],
  "pnl_daily": 0.0,
  "pnl_ytd": 250.0,
  "margin_used": 500.0,
  "margin_available": 4500.0
}
```

### Get Open Positions
```
GET /portfolio/positions/public

Response:
{
  "positions": [
    {
      "symbol": "EURUSD",
      "entry_price": 1.0850,
      "current_price": 1.0860,
      "quantity": 1.0,
      "pnl": 10.00,
      "pnl_percent": 0.92,
      "status": "open",
      "entry_time": "2026-04-05T09:30:00",
      "sl": 1.0790,
      "tp": 1.0920
    }
  ],
  "total": 1
}
```

### Get Portfolio History
```
GET /portfolio/history/public
  ?limit=100          (default: 100)

Response:
{
  "snapshots": [
    {
      "timestamp": "2026-04-05T09:30:00",
      "capital": 10000.0
    },
    {
      "timestamp": "2026-04-05T09:35:00",
      "capital": 10010.0
    },
    ...
  ],
  "count": 90
}
```

### Get Performance Metrics
```
GET /portfolio/performance

Response:
{
  "strategies": {
    "ema_rsi_v1": {
      "trades": 45,
      "wins": 28,
      "losses": 17,
      "win_rate": 0.62,
      "avg_win": 125.50,
      "avg_loss": -85.30,
      "profit_factor": 1.82,
      "sharpe_ratio": 1.45,
      "max_drawdown": -2200.00
    }
  },
  "total_strategies": 1
}
```

---

## ⚠️ Risk Management Endpoints (Public)

### Get Risk Status
```
GET /risk/status/public

Response:
{
  "kill_switch": {
    "active": false,
    "triggered_by": null,
    "triggered_at": null,
    "reset_at": null
  },
  "daily_loss_current": -150.00,
  "daily_loss_limit": -2000.00,
  "consecutive_losses": 2,
  "max_consecutive_losses": 5
}
```

**Status Codes**:
- `kill_switch.active`: true = trading disabled
- `daily_loss_current`: Current P&L for the day
- `daily_loss_limit`: Max loss allowed before auto-stop
- `consecutive_losses`: Current losing streak

---

## 🔐 Protected Endpoints (Require Auth)

### Modify Portfolio
```
POST /portfolio/reset-daily
  Authorization: Bearer {token}
```

### Execute Trade
```
POST /execution/place-order
  Authorization: Bearer {token}
  
Body:
{
  "symbol": "EURUSD",
  "action": "BUY",    # or "SELL", "CLOSE"
  "quantity": 1.0,
  "entry_price": 1.0850,
  "sl": 1.0790,
  "tp": 1.0920,
  "order_type": "limit"  # or "market"
}
```

### Activate Kill Switch
```
POST /risk/kill-switch/activate
  Authorization: Bearer {admin_token}
```

---

## 🎯 Error Responses

### 404 Not Found
```json
{
  "detail": "Symbol INVALIDUSD not supported"
}
```

### 400 Bad Request
```json
{
  "detail": "timeframe must be one of: 1d, 1h, 4h, 1wk, 1mo, 6mo"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded: 100 requests per minute"
}
```

---

## 💡 Dashboard Usage

### Real-time Chart Features
1. **Candlestick Chart**
   - Shows 518 EURUSD 1d candles by default
   - Hover to see OHLCV values
   - Zoom: Box select on chart
   - Pan: Drag horizontally
   - Reset: Click "Reset Zoom" in toolbar
   - Download: Right-click → Save image

2. **RSI Indicator**
   - Full 518-candle history
   - Reference lines at 70/30
   - Color-coded: Green < 30 (oversold), Red > 70 (overbought)
   - Same hover + zoom + pan controls

3. **MACD Indicator**
   - Histogram (bars): Positive=green, Negative=red
   - MACD Line (orange)
   - Signal Line (cyan, dashed)
   - Legend: Click trace name to toggle visibility

4. **Bollinger Bands**
   - Upper Band (red)
   - SMA(20) Middle (white)
   - Lower Band (green)
   - Fill between bands for visual clarity

### Timeframe Selector
Buttons at top: 1D | 1W | 1M
- Switches chart to different timeframe
- Reloads data from API
- All indicators update simultaneously

### Tab Navigation
- **Market View**: Price charts + indicators (default)
- **Signals**: Active + historical trading signals
- **Portfolio**: Positions + equity history
- **Risk**: Kill switch + loss tracking
- **CRYPTO**: Crypto validation dashboard (iframe)

---

## 📞 Support & Debugging

### Check Server is Running
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health"
# Should return: HTTP 200 OK
```

### View Logs
```powershell
# Terminal output shows structured JSON logs
# Example:
# {"symbol": "EURUSD", "timeframe": "1d", "count": 518, "event": "data_loaded"}
```

### Metrics & Monitoring
```
Prometheus metrics: http://127.0.0.1:8001/metrics
Includes:
  - Request counts by endpoint
  - Response times (histogram)
  - Active connections
  - Cache hit rates
```

### Common Issues

**Issue**: Dashboard shows empty charts
- Check: GET /market/symbols returns EURUSD?
- Check: GET /market/EURUSD/data?limit=100&timeframe=1d returns 518 candles?
- Browser console: Open F12 → Console → Look for errors

**Issue**: "Not Found" (404) errors
- This has been fixed! All endpoints now have public versions
- Old endpoint: /portfolio → New: /portfolio/public
- Old endpoint: /risk/status → New: /risk/status/public

**Issue**: Slow chart rendering
- Reduce limit parameter: ?limit=100 (max: 500)
- Use shorter timeframe: 1wk instead of 1h
- Check CPU usage: May be system limitation

---

## 🔗 Related Documentation

- [DASHBOARD_UPDATES_2026_04_05.md](DASHBOARD_UPDATES_2026_04_05.md) — Detailed changes
- [CHANGELOG.md](CHANGELOG.md) — Brief changelog
- [ESTADO_PROYECTO.md](ESTADO_PROYECTO.md) — Project status report
- [DEPLOYMENT.md](DEPLOYMENT.md) — Production deployment guide

---

**Last Updated**: 2026-04-06  
**API Version**: 2.0.0
