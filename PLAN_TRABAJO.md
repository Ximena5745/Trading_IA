# TRADER AI — Plan de Trabajo
> v1.0 · 2026-03-29 · Basado en spec v2.4 (PROYECTO.md)
> Actualizar el estado de cada tarea al completarla.

---

## Cómo usar este documento
- Cada fase tiene un **bloque de tareas** con estado: `[ ]` pendiente · `[x]` completo · `[~]` en curso
- No empezar una fase hasta que la anterior esté **100% completa** (salvo las marcadas como paralelas)
- Al iniciar una sesión de desarrollo: indicar la fase y módulo en el **Prompt Maestro** (sección 9 de PROYECTO.md)
- La fase actual se indica al inicio del documento ↓

---

## FASE ACTUAL: **A → completar pasos manuales** *(código de B, C, D, E, F también listo — 2026-03-29)*

---

## FASE A — Infraestructura base
> Bloqueante. Sin esta fase ningún módulo funciona en producción.

### A1 · Levantar servicios Docker
- [ ] Verificar que Docker Desktop esté corriendo en Windows
- [ ] Ejecutar desde `docker/`: `docker compose up db redis -d`
- [ ] Confirmar estado: `docker compose -f docker/docker-compose.yml ps` → ambos `Up (healthy)`
- [ ] Ver nombre real de contenedores: `docker ps --format "table {{.Names}}`t`{{.Status}}"`
- [ ] Probar conexión a PostgreSQL: `docker exec -it docker-db-1 psql -U trader -d trader_ai -c "\dt"`

### A2 · Base de datos operativa
Schema SQL actualizado (2026-03-29): tablas `users`, `portfolio_snapshots`, `backtest_results` añadidas.

**Opción rápida — schema SQL existente (recomendada para empezar):**
- [ ] `Get-Content "scripts\migrations\001_initial_schema.sql" | docker exec -i docker-db-1 psql -U trader -d trader_ai`
- [ ] `Get-Content "scripts\migrations\002_instruments.sql" | docker exec -i docker-db-1 psql -U trader -d trader_ai`
- [ ] Verificar tablas: `docker exec -it docker-db-1 psql -U trader -d trader_ai -c "\dt"`

**Opción robusta — Alembic (recomendada para producción):**
- [ ] `pip install -r requirements.txt`
- [ ] `alembic init alembic`
- [ ] Crear modelos SQLAlchemy en `core/db/models.py` (basarse en 001_initial_schema.sql)
- [ ] `alembic revision --autogenerate -m "initial_schema"`
- [ ] `alembic upgrade head`
- [ ] Verificar tablas creadas

> **Tablas incluidas en el schema:** `market_data`, `features`, `signals`, `orders`, `strategies`, `users`, `portfolio_snapshots`, `backtest_results`

### A3 · Variables de entorno reales
`.env.example` actualizado (2026-03-29): añadidos `DB_PASSWORD=trader` y `PORTFOLIO_BASE_CURRENCY=USD`.
- [ ] `Copy-Item .env.example .env`
- [ ] Generar `JWT_SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Obtener claves testnet Binance en https://testnet.binance.vision/ → configurar `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`
- [ ] Verificar settings: `python -c "from core.config.settings import Settings; s=Settings(); print(s.EXECUTION_MODE, s.TRADING_ENABLED)"`
- [ ] Confirmar output: `paper False`

### A4 · Telegram bot — alertas internas
- [ ] Crear bot con @BotFather → obtener `BOT_TOKEN`
- [ ] Crear canal/grupo privado de alertas → obtener `CHAT_ID`
- [ ] Configurar `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`
- [ ] Levantar la API → verificar que llega mensaje "Sistema reiniciado" al canal
- [ ] Alertas activas: señal ✅ kill switch ✅ error crítico ✅ reinicio ✅ (código actualizado 2026-03-29)

### A5 · Script backup automático a OneDrive
`scripts/backup_db.py` creado (2026-03-29): pg_dump via docker exec → .sql.gz → rclone upload → retención 30 días.
- [ ] Instalar rclone: https://rclone.org/downloads/ (Windows binary, añadir al PATH)
- [ ] Configurar remote OneDrive: `rclone config` → tipo "onedrive" → nombre "onedrive"
- [ ] Test rclone: `rclone ls onedrive:trader_ai_backups` (crea la carpeta si no existe)
- [ ] Probar script: `python scripts/backup_db.py --dry-run`
- [ ] Probar upload real: `python scripts/backup_db.py`
- [ ] Verificar archivo `.sql.gz` visible en OneDrive carpeta `trader_ai_backups`
- [ ] Crear tarea Windows Task Scheduler: programa=`python`, args=`"C:\ruta\scripts\backup_db.py"`, trigger=diario 03:00 AM

### A6 · Checklist de arranque completo
- [ ] `docker compose up db redis -d` (desde carpeta `docker/`) → ambos `Up (healthy)`
- [ ] `.env` con `JWT_SECRET_KEY` + claves Binance testnet configurado
- [ ] `python scripts/seed_admin.py --email admin@traderai.local --password <min 12 chars>`
- [ ] `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- [ ] Verificar API: `Invoke-RestMethod -Uri "http://localhost:8000/health"` → `{"status":"ok"}`
- [ ] Verificar login: `Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"admin@traderai.local","password":"<tu_password"}'` → JWT recibido
- [ ] Telegram: mensaje de prueba recibido en el canal (opcional — requiere token)
- [ ] Backup: archivo `.sql.gz` visible en OneDrive (opcional — requiere rclone)

**FASE A COMPLETADA cuando:** todos los checks de A6 pasan. ✅

---

## FASE B — Datos históricos y modelos ML
> Requisito: FASE A completada.

### B1 · Script de descarga de datos históricos
`scripts/download_data.py` creado (2026-03-29): incremental, gap detection, parquet output.
- [ ] `python scripts/download_data.py --symbol BTCUSDT --timeframe 1h --years 2`
- [ ] `python scripts/download_data.py --symbol ETHUSDT --timeframe 1h --years 2`
- [ ] Verificar archivos en `data/raw/`: `BTCUSDT_1h.parquet`, `ETHUSDT_1h.parquet`

### B2 · Entrenar modelos ML
`scripts/retrain.py` reescrito (2026-03-29): carga parquet → FeatureEngine → LightGBM → `.pkl`.
- [ ] `python scripts/retrain.py --asset-class crypto --timeframe 1h`
- [ ] Verificar `data/models/technical_crypto_v1.pkl` existe y tiene tamaño > 0
- [ ] `python -c "from core.agents.technical_agent import TechnicalAgent; a=TechnicalAgent('data/models/technical_crypto_v1.pkl'); print(a.is_ready())"`

> `technical_crypto_v1.pkl` sirve para BTCUSDT y ETHUSDT. Forex/índices en FASE E.

**FASE B COMPLETADA cuando:** `data/models/technical_crypto_v1.pkl` existe y `TechnicalAgent.is_ready()` retorna `True`. ✅

---

## FASE C — Pipeline automático de señales
> Requisito: FASES A + B completadas. Componente más crítico que falta.

### C1 · Pipeline y scheduler
`scripts/run_pipeline.py` creado (2026-03-29): ciclo completo 12 pasos + APScheduler.
`core/db/session.py` + `core/db/repository.py` creados (2026-03-29): asyncpg pool + CRUD.
`api/main.py` actualizado: inicia pool DB y APScheduler al arrancar la API.
- [ ] `pip install apscheduler==3.10.4` (añadido a requirements.txt)
- [ ] Probar ciclo único: `python scripts/run_pipeline.py --once BTCUSDT`
- [ ] Verificar en DB: `SELECT * FROM signals LIMIT 5;`
- [ ] Verificar alerta Telegram recibida con la señal
- [ ] Levantar API: `uvicorn api.main:app --reload` → verificar log "pipeline_scheduler_started"

### C2 · Validación del pipeline
- [ ] Correr 24h continuas sin errores no controlados en los logs
- [ ] Confirmar señales persistidas en DB tras reinicio del servidor
- [ ] Verificar logs con context: `symbol`, `asset_class`, `strategy_id`

**FASE C COMPLETADA cuando:** el pipeline corre automáticamente cada hora, persiste en DB y envía alertas Telegram. ✅

---

## FASE D — Autenticación real
> Puede hacerse en paralelo con FASE C.

### D1 · Auth real con DB
`core/db/user_repository.py` creado (2026-03-29): get_user_by_email, create_user, verify_password con bcrypt.
`api/routes/auth.py` reescrito (2026-03-29): sin hardcoded _USERS — usa user_repository.
`scripts/seed_admin.py` creado (2026-03-29): crea primer admin, idempotente.
- [ ] Tabla `users` creada en DB (incluida en 001_initial_schema.sql desde FASE A)
- [ ] `python scripts/seed_admin.py --email admin@traderai.local --password <min 12 chars>`
- [ ] Verificar login: `Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"admin@traderai.local","password":"..."}'` → JWT válido
- [ ] Verificar que credenciales incorrectas devuelven 401

**FASE D COMPLETADA cuando:** la autenticación usa DB con bcrypt y no existe ningún usuario hardcodeado en código. ✅

---

## FASE E — Expansión multi-asset con MT5
> Requisito: FASES A-C completadas **y** cripto corriendo en papel ≥ 2 semanas sin interrupciones.
> 12 sub-tareas con dependencias en cadena. No saltarse el orden.

### E1 · MT5Client
`core/ingestion/providers/mt5_client.py` creado (2026-03-29): connect con backoff × 5, get_historical_klines, get_tick, place_order, get_account_balance, get_symbol_info.
- [ ] Instalar (requiere MT5 terminal instalado en Windows): `pip install MetaTrader5==5.0.5640`
- [ ] Probar conexión a IC Markets demo: configurar `MT5_SERVER`, `MT5_LOGIN`, `MT5_PASSWORD` en `.env`

### E2 · Modelos de datos multi-asset
`AssetClass` enum y `InstrumentConfig` dataclass añadidos a `core/models.py` (2026-03-29). 11 instrumentos IC Markets + 2 Binance crypto configurados con pip_value, lot_size, spread_pips, swap_long/short.
- [ ] Verificar `from core.models import get_instrument; print(get_instrument("EURUSD").pip_value)` → `10.0`

### E3 · Tabla instruments en DB
`scripts/migrations/002_instruments.sql` creado (2026-03-29): tabla `instruments` + seed de 13 instrumentos activos.
> Ya aplicado en FASE A junto con 001_initial_schema.sql
- [ ] Verificar: `docker exec -it docker-db-1 psql -U trader -d trader_ai -c "SELECT symbol, asset_class FROM instruments;"`

### E4 · MarketCalendar
`core/ingestion/market_calendar.py` creado (2026-03-29): sesiones UTC (Sydney/Tokyo/Londres/NY), is_market_open, is_low_liquidity, is_high_impact_event_window, ForexFactory RSS con caché 4h.
- [ ] Test sesiones: `from core.ingestion.market_calendar import get_calendar; c=get_calendar(); print(c.is_market_open("EURUSD"))`

### E5 · PositionSizer multi-asset
`core/risk/position_sizer.py` reescrito (2026-03-29): _forex_sizing (lotes), _cfd_sizing (contratos), _crypto_sizing (unidades). Usa InstrumentConfig.pip_value y lot_size. API backward-compatible.
- [ ] Verificar con test manual para EURUSD: `calculate("EURUSD", 10000, 10000, 1.1000, 1.0950)` → lots ≤ 0.1

### E6 · CostModel + swap overnight
`core/backtesting/costs.py` reescrito (2026-03-29): _apply_crypto (commission_pct + slippage_pct), _apply_mt5 (spread_pips × pip_value × lots + swap), get_swap_cost usa swap_long/short de InstrumentConfig.
- [ ] Verificar costo EURUSD 0.01 lots spread 0.6 pips = $0.06: `CostModel().get_spread_cost("EURUSD", 0.01)`

### E7 · Pesos consenso condicionales por asset_class
`core/consensus/voting_engine.py` reescrito (2026-03-29): AGENT_WEIGHTS_CRYPTO (tech 45%, regime 35%, micro 20%), AGENT_WEIGHTS_MT5 (tech 55%, regime 45%, micro 0%). Selección automática por asset_class.
- [ ] Verificar que micro no contribuye en EURUSD: revisar log `weight_mode: "mt5"` en señal forex

### E8 · FundamentalAgent Forex
`core/agents/fundamental_agent.py` actualizado (2026-03-29): is_blocked_by_event(symbol) → True si evento alto impacto ±30 min en divisa afectada, usando ForexFactory RSS via MarketCalendar. Solo aplica a no-CRYPTO.
- [ ] Test manual durante un NFP: verificar que señal EURUSD es bloqueada en ventana ±30 min

### E9 · confirmation_timeframe en StrategyBuilder
`core/strategies/strategy_builder.py` actualizado (2026-03-29): campo opcional `confirmation_timeframe` en config. Validado contra SUPPORTED_TIMEFRAMES. Desactivado por defecto.
- [ ] Verificar que estrategia sin `confirmation_timeframe` funciona igual que antes

### E10 · LOW_LIQUIDITY log en RegimeAgent
`core/agents/regime_agent.py` actualizado (2026-03-29): detecta sesión asiática via MarketCalendar, emite `log.warning("LOW_LIQUIDITY")` con nota "signals allowed per decision v2.4". NO bloquea ejecución.
- [ ] Verificar log durante sesión asiática (Tokyo open, London+NY closed)

### E11 · Datos MT5 + modelos forex
`scripts/download_data.py` actualizado (2026-03-29): `--provider mt5` usa MT5Client.get_historical_klines().
`scripts/retrain.py` actualizado (2026-03-29): soporta `--asset-class forex`.
- [ ] Conectar MT5 a IC Markets demo → `python scripts/download_data.py --symbol EURUSD --timeframe 1h --years 2 --provider mt5`
- [ ] `python scripts/retrain.py --asset-class forex --timeframe 1h`
- [ ] Verificar `data/models/technical_forex_v1.pkl` existe

### E12 · MT5Executor — live trading MT5
`core/execution/mt5_executor.py` creado (2026-03-29): _safety_checks (EXECUTION_MODE=live, TRADING_ENABLED=True, kill_switch), idempotency check, resolución de mt5_symbol via InstrumentConfig, place_order con IC Markets.
- [ ] Test integración en cuenta demo IC Markets (paper, no live)
- [ ] Verificar orden visible en terminal MT5 tras test

**FASE E COMPLETADA cuando:** pipeline completo corre para EURUSD, XAUUSD y US500 en papel via MT5, con costos reales y bloqueo de eventos macro. ✅

---

## FASE F — Despliegue en VPS Windows
> Puede iniciarse en paralelo con FASE E.

### F1 · Configurar VPS Windows
`scripts/setup_vps.ps1` creado (2026-03-29): instala Git + Python 3.11 vía winget, verifica Docker, clona repo, crea venv, aplica migraciones SQL, registra tarea backup en Task Scheduler.
- [ ] Contratar VPS (recomendado: Hetzner CPX21 Windows ~15 €/mes)
- [ ] Instalar Docker Desktop for Windows en el VPS
- [ ] Instalar MT5 terminal + abrir sesión con cuenta IC Markets demo en el VPS
- [ ] Ejecutar como Administrador: `powershell -ExecutionPolicy Bypass -File scripts\setup_vps.ps1 -Domain "tu-dominio.com"`

### F2 · Nginx + HTTPS
`docker/nginx.conf` creado (2026-03-29): HTTP→HTTPS redirect, SSL TLS 1.2/1.3, rate limit 30r/m, proxy a FastAPI:8000 + Streamlit:8501 + Grafana:3000, Prometheus bloqueado, security headers (HSTS, X-Frame-Options, etc.).
- [ ] Descargar Nginx para Windows desde https://nginx.org/en/download.html → extraer a `C:\nginx`
- [ ] Ejecutar setup_vps.ps1 (copia nginx.conf automáticamente con tu dominio)
- [ ] Instalar win-acme: https://www.win-acme.com/ → obtener certificado Let's Encrypt
- [ ] Actualizar rutas de certificado en nginx.conf: `C:/win-acme/certs/TU_DOMINIO/fullchain.pem`
- [ ] Firewall: `netsh advfirewall firewall add rule name="HTTP" dir=in action=allow protocol=TCP localport=80`
- [ ] Firewall: `netsh advfirewall firewall add rule name="HTTPS" dir=in action=allow protocol=TCP localport=443`
- [ ] RDP: restringir a IP específica en el panel del proveedor VPS

### F3 · Despliegue de la aplicación
- [ ] Completar pasos F1 y F2 en el VPS
- [ ] Configurar `.env` con variables de producción (JWT_SECRET_KEY rotada, API keys reales)
- [ ] `docker compose up db redis -d` (desde carpeta `docker/`) → `Up (healthy)`
- [ ] `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000` → arrancar
- [ ] Verificar `GET https://tu-dominio/health` → `200 OK`
- [ ] Verificar backup Task Scheduler: `Get-ScheduledTask -TaskName "TraderAI_Backup"`

**FASE F COMPLETADA cuando:** aplicación accesible via HTTPS, backup automático funcionando. ✅

---

## FASE G — Validación en papel (≥ 2 semanas)
> Solo comenzar cuando FASES A-C (y F si VPS) están completas.

### Cripto (obligatorio)
- [ ] Sistema corriendo ≥ 2 semanas sin interrupciones
- [ ] Sharpe sostenido ≥ 1.0 durante el periodo
- [ ] Kill Switch: activar manualmente y verificar reset correcto
- [ ] Alertas Telegram: llegan en < 30 segundos
- [ ] Persistencia DB: portafolio correcto tras reinicio del servidor
- [ ] Revisión manual de ≥ 20 señales (motivación + resultado)
- [ ] P&L diario: no supera 5% en ninguna sesión
- [ ] Backup OneDrive: archivos presentes cada mañana

### MT5 / multi-asset (solo si FASE E completada)
- [ ] Señales Forex bloqueadas fuera de sesión de mercado
- [ ] Señales bloqueadas en ventanas NFP/CPI/tasas ±30 min
- [ ] Position sizing correcto en lotes para EURUSD
- [ ] Swap overnight descontado correctamente del P&L

**FASE G COMPLETADA cuando:** todos los checks marcados. ✅

---

## FASE H — Live trading
> Solo ejecutar cuando FASE G esté completamente validada.
> Capital inicial < $1,000. Escalar gradualmente.

### Configuración inicial
- [ ] Cambiar en `.env`: `EXECUTION_MODE=live`, `TRADING_ENABLED=true`, `BINANCE_TESTNET=false`
- [ ] Verificar API keys Binance con solo permiso de trading (sin retiros)
- [ ] Configurar capital inicial: 5% del total (< $50 primera semana)

### Calendario de escalado

| Periodo | Capital | Activos | Condición |
|---|---|---|---|
| Semana 1-2 | 5% del total | Solo BTCUSDT spot | Primer live — siempre |
| Semana 3-4 | +5% | Añadir ETHUSDT | Sharpe ≥ 1.0 en semanas 1-2 |
| Mes 2 (post FASE E) | +5% | Añadir EURUSD + XAUUSD via MT5 | FASE E completada + paper MT5 validado |
| Mes 3+ | Escalar por resultados | US500, GBPUSD, USDJPY… | Performance real ≥ umbral |

- [ ] Semana 1-2 live completada con Sharpe ≥ 1.0
- [ ] Semana 3-4: añadir ETHUSDT
- [ ] Mes 2: añadir MT5 (solo si FASE E validada)

**FASE H ACTIVA cuando:** primera semana live sin incidentes y Kill Switch nunca activado. ✅

---

## Dependencias entre fases

```
A (infraestructura) ──┬──> B (datos + ML) ──> C (pipeline) ──> G (validación papel) ──> H (live)
                      │
                      └──> D (auth real)    ← paralela con C

C completado + 2 semanas papel ──> E (MT5 multi-asset) ──> G (validación MT5)

F (VPS) ← puede iniciarse en paralelo con E
```

---

## Registro de progreso

| Fase | Inicio | Completada | Notas |
|---|---|---|---|
| A | 2026-03-29 | — | Código completo. Pendiente: Docker up, .env real, Telegram token, rclone |
| B | 2026-03-29 | — | Código completo. Pendiente: descargar datos y ejecutar retrain |
| C | 2026-03-29 | — | Código completo. Pendiente: probar --once y validar 24h |
| D | 2026-03-29 | — | Código completo. Pendiente: seed_admin y probar login |
| E | 2026-03-29 | — | Código completo (E1-E12). Pendiente: instalar MT5, conectar demo IC Markets, descargar datos forex, retrain |
| F | 2026-03-29 | — | Código completo (nginx.conf + setup_vps.ps1). Pendiente: contratar VPS, instalar Nginx, win-acme HTTPS |
| G | — | — | — |
| H | — | — | — |

---

## Sesión de desarrollo — cómo empezar

1. Abrir este documento y localizar la **FASE ACTUAL**
2. Identificar la primera tarea `[ ]` sin completar
3. Copiar el **Prompt Maestro** de la sección 9 de `PROYECTO.md`
4. Completar los campos: `FASE ACTUAL`, `MÓDULO EN DESARROLLO`, `ASSET CLASS EN SCOPE`, `BROKER MT5 ACTIVO`
5. Pegar el prompt al inicio de la sesión de Claude Code
6. Al terminar: marcar las tareas completadas con `[x]` y actualizar el **Registro de progreso**

---

> TRADER AI v2.4 · Plan de trabajo v1.0 · 2026-03-29
