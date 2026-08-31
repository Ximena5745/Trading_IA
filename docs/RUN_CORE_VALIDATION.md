# RUN_CORE_VALIDATION — arranque reproducible del stack + un ciclo del pipeline

> Runbook de la Fase 1 (entregable 1.9). Objetivo: que cualquiera levante el
> stack completo de forma determinista y ejecute un ciclo del pipeline contra
> **Binance testnet + datos reales**, con migraciones aplicadas y trazabilidad.
>
> Relacionado: ADR-003/004/005, SPEC-A02/A03/B03/B04/B06, `docs/PROGRESS.md`.

---

## 1. Requisitos

- Docker + Docker Compose v2 (`docker compose version` ≥ 2.20).
- Repo clonado; trabajar **desde la raíz del repo**.
- Claves de **Binance testnet** (https://testnet.binance.vision/ → *Generate HMAC_SHA256 Key*).

## 2. Configurar `.env`

```bash
cp .env.example .env
```

Editar `.env` y fijar como mínimo:

| Variable | Valor |
|---|---|
| `JWT_SECRET_KEY` | 64 hex chars — generar: `python -c "import secrets; print(secrets.token_hex(32))"` (se **valida**: ≥32 y ≠ default) |
| `DB_PASSWORD` | contraseña de Postgres (cualquiera, sin `@` ni `:`) |
| `REDIS_PASSWORD` | contraseña de Redis |
| `GRAFANA_PASSWORD` | contraseña de Grafana |
| `BINANCE_API_KEY` / `BINANCE_SECRET_KEY` | claves de **testnet** |
| `BINANCE_TESTNET` | `true` |
| `EXECUTION_MODE` | `paper` (no cambiar) |
| `TRADING_ENABLED` | `false` |
| `REGISTRATION_ENABLED` | `false` |
| `ALLOW_INSECURE_JWT` | `false` |

> `DB_PASSWORD` / `REDIS_PASSWORD` / `GRAFANA_PASSWORD` se usan en la
> **sustitución `${...}`** de `docker/docker-compose.yml`; por eso el comando de
> arranque pasa `--env-file .env`.

## 3. Levantar el stack

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d db redis
docker compose --env-file .env -f docker/docker-compose.yml up migrate      # one-shot, debe salir con code 0
docker compose --env-file .env -f docker/docker-compose.yml up -d app worker
```

O todo de una (compose respeta `depends_on` → `migrate` corre antes que `app`/`worker`):

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

Servicios esperados: `db`, `redis`, `migrate` (Exited 0), `app`, `worker`
(+ `prometheus`, `grafana`, `nginx`).

## 4. Verificaciones de arranque

**4.1 Migraciones aplicadas**
```bash
docker compose --env-file .env -f docker/docker-compose.yml logs migrate | grep alembic_migrations_applied
docker compose --env-file .env -f docker/docker-compose.yml exec db \
  psql -U trader -d trader_ai -c "select version_num from alembic_version;"
```

**4.2 API arriba con DB (SPEC-A03)**
```bash
curl -s http://localhost:8000/health | python -m json.tool
# → {"status":"ok", ..., "db_initialized": true}
```

**4.3 Worker = único dueño del scheduler (SPEC-A02 / F-04)**
```bash
docker compose --env-file .env -f docker/docker-compose.yml logs worker | grep scheduler_owner_acquired
docker compose --env-file .env -f docker/docker-compose.yml exec redis \
  redis-cli -a "$REDIS_PASSWORD" get trader:scheduler:owner
```
La API **no** programa jobs: sus logs no deben tener `scheduler_started` ni `job_scheduled`.

**4.4 Un universo de activos (SPEC-B03)**
```bash
curl -s http://localhost:8000/market/symbols
# → 8 símbolos = core.config.constants.TRADED_UNIVERSE
```

## 5. Ejecutar un ciclo del pipeline

El pipeline solo emite señales para símbolos con `data/models/i1_params/<SYMBOL>.json`
aprobado (ADR-003, fail-safe quant). Hoy solo **XAUUSD** está aprobado, y XAUUSD
requiere MT5 (no configurado). Por eso hay dos modos:

**5.1 Smoke — prueba que el stack y los gates funcionan (Binance testnet, crypto)**
```bash
docker compose --env-file .env -f docker/docker-compose.yml exec worker \
  python scripts/run_pipeline.py --once BTCUSDT
```
Esperado en logs: `cycle_start` → OHLCV real de Binance testnet → `no_approved_strategy`
(BTCUSDT no tiene `i1_params` aprobado). Esto **demuestra** que:
- el worker conecta a Binance testnet y trae datos reales,
- el gate de estrategia aprobada bloquea correctamente,
- no hay ejecución sin edge validado.

**5.2 Ciclo completo productor de señal**

Requiere un símbolo **crypto** aprobado por el gate I1. Para validar el core
end-to-end (Fase 2, Track A) se corre el gate y se genera el `<SYMBOL>.json`:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec worker \
  python scripts/run_i1_edge_research.py --symbols BTCUSDT --strict --bootstrap 200
# si pasa → escribe data/models/i1_params/BTCUSDT.json
docker compose --env-file .env -f docker/docker-compose.yml exec worker \
  python scripts/run_pipeline.py --once BTCUSDT
```
Ahora el ciclo recorre features → agentes → consenso → señal → riesgo →
ejecución paper → persistencia → alerta, y emite un `correlation_id`.

## 6. Trazabilidad de la decisión (SPEC-B04)

Tomar el `correlation_id` de los logs del ciclo (`grep correlation_id`) y:

```bash
# necesita un token de trader; crear el admin seed y luego un trader:
TOKEN=...   # JWT de un usuario con rol >= trader
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/trace/<correlation_id> | python -m json.tool
```
Devuelve las etapas `market_data → features → agent_output → consensus → signal →
risk_check → execution → portfolio` con `complete: true` para un ciclo que llegó
hasta el final.

## 7. Parar / limpiar

```bash
docker compose --env-file .env -f docker/docker-compose.yml down            # conserva volúmenes
docker compose --env-file .env -f docker/docker-compose.yml down -v         # borra DB/Redis/Grafana
```

## 8. Prueba de reproducibilidad (adelanto de F2.2)

```bash
docker compose ... exec worker python scripts/run_pipeline.py --once BTCUSDT   # corrida A
docker compose ... exec worker python scripts/run_pipeline.py --once BTCUSDT   # corrida B
```
Con el mismo conjunto de velas, señales/órdenes/snapshots deben ser idénticos.
Cualquier no-determinismo se documenta y elimina en la Fase 2.

---

## Troubleshooting

| Síntoma | Causa | Fix |
|---|---|---|
| `migrate` sale con code ≠ 0 | `DATABASE_URL` mal / `db` no healthy | revisar `.env`, `docker compose logs db` |
| `/health` → `db_initialized: false` en `paper` | DB no inicializó | `docker compose logs app \| grep database_init_failed` |
| API no arranca, exit ≠ 0 con `EXECUTION_MODE=live` | política fail-fast (SPEC-A03) | arreglar DB **o** volver a `paper` |
| `ValidationError: JWT_SECRET_KEY` | secreto < 32 o = default | generar uno nuevo (paso 2) |
| worker: `scheduler_owner_standby` en bucle | otro proceso tiene el lock | `redis-cli get trader:scheduler:owner`; matar el duplicado |
| `no_approved_strategy` para todos | sin `i1_params/<SYMBOL>.json` | correr el gate I1 (paso 5.2) — comportamiento **esperado** |
