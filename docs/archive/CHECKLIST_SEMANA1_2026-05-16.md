# CHECKLIST DE IMPLEMENTACIÓN — SEMANA 1
**Período:** 2026-05-16 a 2026-05-22  
**Objetivo:** Desbloquear los 4 blockers críticos + agregar features cuantitativas base

---

## LUNES 2026-05-16 (HOY) — QW-TECH Phase 1

### Mañana (4h)

- [ ] **QWT-1** (1h) — Eliminar `and False` en JWT validator
  - Archivo: `core/config/settings.py:106`
  - Cambio: `if v == "change-me-in-production" and False:` → `if v == "change-me-in-production":`
  - Test: `pytest tests/unit/test_settings.py::test_jwt_validator`
  - Commit: "fix: enable JWT secret validation in production"

- [ ] **QWT-3** (1h) — Fix docker-compose.yml
  - Archivo: `docker/docker-compose.yml`
  - Cambio: Eliminar líneas 131-153 (bloques `grafana:`, `prometheus:` fuera de `services:`)
  - Test: `docker-compose config` (sin errores YAML)
  - Commit: "fix: remove duplicate docker-compose entries"

- [ ] **QWT-5** (0.5h) — Unificar BINANCE_API_SECRET vs BINANCE_SECRET_KEY
  - Archivo 1: `.github/workflows/ci.yml:56`
  - Cambio: `BINANCE_API_SECRET=` → `BINANCE_SECRET_KEY=`
  - Archivo 2: `core/config/settings.py` (verificar que el campo es BINANCE_SECRET_KEY)
  - Test: `grep -r BINANCE_SECRET_KEY core/` (sin referencias a BINANCE_API_SECRET)
  - Commit: "fix: standardize Binance API key naming"

- [ ] **QWT-7** (1h) — Cancelación correcta de tarea async
  - Archivo: `api/main.py`
  - Cambio en lifespan:
    ```python
    _fundamental_task = asyncio.create_task(_refresh_fundamental())
    
    yield
    
    if _fundamental_task and not _fundamental_task.done():
        _fundamental_task.cancel()
    ```
  - Test: Verificar no hay "Task was destroyed but pending" en logs de shutdown
  - Commit: "fix: properly cancel async tasks on shutdown"

### Tarde (3h)

- [ ] **QWT-4** (2h) — Fix `user.get("sub")` → `user.get("user_id")`
  - Archivos: 
    - `api/routes/execution.py`
    - `api/routes/marketplace.py`
    - `api/routes/simulation.py`
    - `api/routes/portfolio.py`
  - Cambio: Buscar y reemplazar todas las instancias
  - Test: `grep -n 'user.get("sub")' api/routes/*.py` (debe estar vacío)
  - Commit: "fix: correct JWT user_id extraction in API routes"

**Fin de día:** 2 PRs abiertas, CI verde

---

## MARTES 2026-05-17 — QW-TECH Phase 2 + QW-QUANT Phase 1

### Mañana (4h)

- [ ] **QWT-2** (2h) — Fix `explanation=None` en Signal
  - Archivo: `api/routes/execution.py:71-83`
  - Cambio 1: `explanation=None,` → `explanation=[],`
  - Cambio 2: Verificar que el field en `core/models.py` acepta `Optional[list]` o `list`
  - Test: `pytest tests/unit/test_models.py::test_signal_creation`
  - Test 2: `curl -X POST http://localhost:8000/execution -H "Authorization: Bearer xxx"`
  - Commit: "fix: correct Signal explanation field type"

- [ ] **QWT-10** (2h) — Refactorizar validate_signal para aceptar Signal | dict
  - Archivo: `core/risk/risk_manager.py`
  - Cambio: Actualizar signature de `validate_signal` para aceptar `Signal | dict`
  - Opción A: `Union[Signal, dict]` en tipo hint
  - Opción B: Convertir en `api/routes/execution.py` antes de llamar: `signal_dict = signal.model_dump()`
  - Test: Ambos tipos funcionan sin error
  - Commit: "refactor: make validate_signal accept both Signal and dict"

### Tarde (4h)

- [ ] **QWQ-1 inicio** (2h) — Comenzar agregar retornos lagged
  - Archivo: `core/features/indicators.py`
  - Agregar función:
    ```python
    def calculate_lagged_returns(df: pd.DataFrame, periods=[1, 3, 6, 12, 24]) -> dict:
        """Calculate lagged returns for given periods."""
        for p in periods:
            df[f'ret_{p}'] = df['close'].pct_change(p)
        return df
    ```
  - Verificar que NO hay look-ahead (usar .shift() correctamente)
  - Test: `pytest tests/unit/test_features.py::test_lagged_returns`
  - Commit: "feat: add lagged returns features (P0)"

- [ ] **QWQ-2 inicio** (2h) — Comenzar target ternario
  - Archivo: `core/agents/technical_agent.py`
  - Agregar función:
    ```python
    def build_ternary_target(df: pd.DataFrame, forward_bars=6):
        """BUY/SELL/HOLD based on ATR% dead zone."""
        atr_pct = df['atr_14'] / df['close']
        threshold = df['close'].pct_change().abs().rolling(252).quantile(0.30)
        forward_ret = df['close'].pct_change(forward_bars).shift(-forward_bars)
        target = np.where(forward_ret > atr_pct * threshold, 1,
                 np.where(forward_ret < -atr_pct * threshold, -1, 0))
        return pd.Series(target)
    ```
  - Test: Verificar que el target es {-1, 0, 1}
  - Commit: "feat: implement ternary target with dead zone (P0)"

**Fin de día:** 4 PRs abiertas, `POST /execution` funciona sin errores de tipo

---

## MIÉRCOLES 2026-05-18 — QW-TECH Phase 3 + QW-QUANT Phase 1 cont.

### Mañana (5h)

- [ ] **QWT-6** (4h) — Aplicar rate limiting en endpoints críticos
  - Archivo: `api/routes/auth.py`, `execution.py`, `risk.py`
  - Cambio:
    ```python
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @router.post("/login")
    @limiter.limit("100/minute")
    async def login(...):
        ...
    
    @router.post("/execution")
    @limiter.limit("50/minute")
    async def execute(...):
        ...
    
    @router.post("/kill-switch/activate")
    @limiter.limit("10/minute")
    async def activate_kill_switch(...):
        ...
    ```
  - Test: Hacer 101 requests a `/login` en 1 minuto → debe retornar 429
  - Commit: "feat: add rate limiting to critical endpoints"

- [ ] **QWT-8** (1h) — Mover `_load_parquet_data` a asyncio.to_thread
  - Archivo: `api/main.py:215`
  - Cambio:
    ```python
    # ANTES:
    _load_parquet_data()
    
    # DESPUÉS:
    await asyncio.to_thread(_load_parquet_data)
    ```
  - Test: Verificar que no hay "blocking call" warnings en startup
  - Commit: "fix: run blocking parquet loading in thread pool"

### Tarde (3h)

- [ ] **QWQ-3 (embargo)** — Empezar setup de validación con embargo
  - Archivo: `core/ml/validation.py` (crear si no existe)
  - Agregar clase:
    ```python
    class PurgedKFold:
        def __init__(self, n_splits=5, embargo_bars=5):
            self.n_splits = n_splits
            self.embargo_bars = embargo_bars
        
        def split(self, X, y, groups=None):
            """Yield (train_idx, test_idx) with embargo."""
            # TODO: implementar splits con embargo
    ```
  - Commit: "feat: initialize PurgedKFold with embargo (WIP)"

**Fin de día:** 3 PRs más, rate limiting funcional

---

## JUEVES 2026-05-19 — QW-TECH Phase 4 + QW-QUANT Phase 1 cont.

### Mañana (3h)

- [ ] **QWT-9** (3h) — Auth en drawings e indicators
  - Archivos: `api/routes/drawings.py`, `indicators.py`
  - Cambio: Agregar `Depends(get_current_user)` en TODOS los endpoints
  - Ejemplo:
    ```python
    @router.get("/drawings")
    async def get_drawings(current_user: dict = Depends(get_current_user)):
        # Only logged-in users can access
        user_id = current_user["user_id"]
        ...
    ```
  - Test: Request sin token → 401. Request con token → 200.
  - Commit: "fix: require authentication for drawings and indicators endpoints"

### Tarde (4h)

- [ ] **QWQ-4** (2h) — Agregar ADX como feature
  - Archivo: `core/features/indicators.py`
  - Agregar:
    ```python
    def calculate_adx(df: pd.DataFrame, period=14):
        """Average Directional Index — measures trend strength."""
        # Usar pandas-ta: adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        # o implementar manualmente con +DM, -DM, ATR
    ```
  - Test: `pytest tests/unit/test_features.py::test_adx`
  - Commit: "feat: add ADX (Average Directional Index) as feature (P0)"

- [ ] **QWQ-5** (2h) — Agregar Hurst Exponent
  - Archivo: `core/features/hurst_engine.py` (ya existe)
  - Actualizar/mejorar si es necesario
  - Test: `pytest tests/unit/test_features.py::test_hurst`
  - Commit: "feat: add rolling Hurst Exponent (100, 250, 500 bar windows)"

**Fin de día:** 3 PRs más, todos los endpoints protegidos

---

## VIERNES 2026-05-20 — QW-QUANT Phase 2 + Phase 1 Cleanup

### Mañana (3h)

- [ ] **QWQ-6** (1h) — Dynamic SL/TP por activo
  - Archivo: `core/risk/mtf_sl_tp_manager.py` (ya existe, mejorar)
  - Actualizar diccionario de multiplicadores por asset:
    ```python
    ATR_MULTIPLIERS_BY_ASSET = {
        "BTCUSDT": 1.5,    # crypto volatile
        "ETHUSDT": 1.5,
        "EURUSD": 2.0,     # forex stable
        "GBPUSD": 2.0,
        "SPX500": 2.0,     # indices
        "XAUUSD": 2.5,     # commodities volatile
        "USOIL": 3.0,      # oil very volatile
    }
    ```
  - Test: Verificar que SL/TP se calculan correctamente por activo
  - Commit: "feat: implement adaptive SL/TP by asset class"

- [ ] **QWQ-7** (0.5h) — Cooldown entre señales
  - Archivo: `core/signals/signal_engine.py`
  - Agregar lógica:
    ```python
    SIGNAL_COOLDOWN_BARS = 3
    last_signal_bar = {}  # symbol -> bar_index
    
    def should_generate_signal(symbol, current_bar):
        if symbol not in last_signal_bar:
            return True
        bars_since = current_bar - last_signal_bar[symbol]
        return bars_since >= SIGNAL_COOLDOWN_BARS
    ```
  - Test: Verificar no hay 2 señales en < 3 barras para el mismo símbolo
  - Commit: "feat: add 3-bar cooldown between signals per symbol"

- [ ] **QWQ-8** (0.5h) — Risk exposure real
  - Archivo: `core/risk/risk_manager.py`
  - Cambiar cálculo de `_update_risk_exposure`:
    ```python
    # ANTES: exposición nominal
    # exposure = abs(entry_price - 0) * qty / total_capital
    
    # DESPUÉS: riesgo real (hasta SL)
    # risk = abs(entry_price - stop_loss) * qty / total_capital
    ```
  - Test: Verificar que el riesgo es más realista
  - Commit: "fix: calculate risk exposure from entry to stop-loss, not to zero"

### Tarde (2h)

- [ ] **QWQ-9** (0.5h) — Annualization dinámica
  - Archivo: `core/backtesting/backtest_engine.py` o `core/backtesting/metrics.py`
  - Cambiar:
    ```python
    # ANTES: sqrt(252) para todo
    # DESPUÉS: sqrt(periods_per_year) dinámico
    
    def annualize_sharpe(sharpe, periods_per_year):
        return sharpe * np.sqrt(periods_per_year)
    
    # Crypto 1h: 252 * 24 = 6048
    # Forex 1h: 252 * 8 = 2016
    # Daily: 252
    ```
  - Test: Verificar que Sharpe es comparable entre timeframes
  - Commit: "fix: dynamic Sharpe annualization based on timeframe"

- [ ] **QWQ-10 (inicio)** (1h) — Walk-forward reentrenamiento
  - Archivo: `core/backtesting/engine.py` o `core/backtesting/backtest_engine.py`
  - Crear función:
    ```python
    def run_walk_forward(df, train_window=252*24, test_window=30*24, embargo_bars=5):
        """Train on window, test on next window, repeat."""
        results = []
        for i in range(0, len(df) - test_window, test_window):
            train_start = i
            train_end = i + train_window
            test_start = train_end + embargo_bars
            test_end = test_start + test_window
            
            if test_end > len(df):
                break
            
            train_df = df.iloc[train_start:train_end]
            test_df = df.iloc[test_start:test_end]
            
            # Train model on train_df
            model = train_model(train_df)
            
            # Evaluate on test_df
            preds = model.predict(test_df)
            sharpe_oos = calculate_sharpe(preds, test_df)
            results.append(sharpe_oos)
        
        return results
    ```
  - Test: `pytest tests/unit/test_backtest.py::test_walk_forward`
  - Commit: "feat: implement walk-forward validation with retraining (WIP)"

**Fin de semana 1:** 
- ✅ 10 PRs merged
- ✅ 0 errores críticos en CI
- ✅ Sistema inicia sin crashes
- ✅ Features base agregadas
- ✅ Ready para Fase 1 (BD + Pipeline)

---

## PRÓXIMOS PASOS (Semana 2 — Fase 1)

- Lunes-Martes: **M1.1 — Database** (migraciones Alembic)
- Martes-Miércoles: **M1.2 — Auth completa** (token blacklist)
- Miércoles-Viernes: **M1.3 — APScheduler pipeline**
- Semana 3: **M1.4 — Paper executor** + **M1.5 — Redis**

**Meta:** Primera orden en papel generada autónomamente

---

**Checklist generado:** 2026-05-16  
**Actualizar este documento:** cada fin de semana  
**Status:** 🟢 NO INICIADO → 🟡 EN PROGRESO → 🔵 COMPLETADO
