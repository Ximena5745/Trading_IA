# TRADER AI — Dashboards

## Dashboard HTML/JS Nativo (Activo — Recomendado)

Servido directamente por FastAPI en `http://localhost:8000/`. Sin dependencias externas.

### Inicio rápido

```bash
# Instalar dependencias
pip install fastapi uvicorn pandas pyarrow structlog slowapi python-jose passlib

# Iniciar servidor
python -m uvicorn api.main:app --reload --port 8000

# Abrir en navegador
http://localhost:8000/
```

### Características

| Página | Contenido |
|---|---|
| **Market View** | Candlestick interactivo (Plotly.js), selector símbolo + temporalidad (1W/1M/6M), RSI/MACD/Bollinger mini-charts, panel Agentes IA + Consensus Gauge SVG |
| **Signals** | Señales recientes, tabla con badges, panel SHAP con barras horizontales, resumen XAI |
| **Portfolio** | Métricas (Equity, P&L, Sharpe, Drawdown), Equity Curve, Posiciones abiertas, P&L por símbolo |
| **Risk Monitor** | Kill Switch status, métricas de riesgo con progress bars, Donut de exposición, Tabla Hard Limits |

### Datos

| Fuente | Símbolos | Timeframes | Estado |
|---|---|---|---|
| **Parquet reales** | EURUSD, GBPUSD, USDJPY, US30, US500, XAUUSD | 1wk (262 velas) | ✅ Cargados al startup |
| **Mock** | BTCUSDT, ETHUSDT | — | ⚠️ Simulados |

### Diseño

- Fuentes: **Syne** (UI) + **JetBrains Mono** (datos)
- Tema: Dark mode profesional (tokens CSS `--bg0` a `--bg4`)
- Gráficos: Plotly.js CDN
- API: Endpoints GET públicos (sin auth) para lectura

---

## Dashboard Streamlit (Legacy — 7 páginas)

### Deploy to Streamlit Cloud

1. Push this `app/` folder to your GitHub repository
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Set requirements file: `app/requirements.txt`
5. Set main file path: `app/dashboard.py`
6. Add environment variable: `API_URL` = your deployed API URL

### Environment Variables

- `API_URL` - URL of the deployed FastAPI (e.g., https://your-api.onrender.com)

### Features

- 📊 Market View - Real-time charts
- ⚡ Signals - Trading signals with XAI
- 🧠 Strategies - Management
- 💼 Portfolio - P&L tracking
- 🔁 Backtesting - Historical tests
- 🎮 Simulator - What-if analysis
- 🛡️ Risk Monitor - Risk management
