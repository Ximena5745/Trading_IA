# ADR-004 — Universo de activos canónico y nomenclatura de índices

- **Estado:** Aceptado (2026-08-28)
- **Fase:** F0 · entregable 0.1 del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`
- **Contexto base:** `docs/AUDITORIA_INTEGRAL_2026-08-28.md` (G-10, D-11), `docs/SPEC_BACKLOG_2026-08-28.md` (SPEC-B03)
- **Relacionada:** ADR-003 (estrategias), ADR-007 (ruta a producción)

## Contexto

Hay cuatro fuentes de "universo" inconsistentes entre sí:

| Fuente | Símbolos | Nomenclatura de índices |
|---|---|---|
| `core/config/constants.py` → `ASSET_CLASS_SYMBOLS` / `SUPPORTED_SYMBOLS` | 28 (incluye SOLUSDT, BNBUSDT, XAGUSD, USOIL, DE40, JP225…) | `SPX500`, `NAS100` |
| `scripts/run_pipeline.py` → `SCHEDULE` | 12 (añade AUDUSD, USDCHF, USDCAD, UK100) | `US500`, `US30`, `UK100` |
| `core/ml/i1_gate_validator/config.py` → `PIPELINE_SYMBOLS` | 8 | `US500`, `US30` |
| `data/raw/parquet/1h/` | 6 no-crypto: `eurusd, gbpusd, usdjpy, us30, us500, xauusd` | `us500`, `us30` |

El pipeline, el gate y los datos ya usan la familia `US###`; solo `constants.py` diverge con `SPX500`/`NAS100`. No hay un único punto que defina "qué se puede operar" ni un mapeo documentado a símbolos de broker.

## Decisión

1. **Fuente única: `TRADED_UNIVERSE` en `core/config/constants.py`.** Es la lista canónica de símbolos que el sistema puede llegar a operar. La consumen por import: `settings.SUPPORTED_SYMBOLS`, `run_pipeline.SCHEDULE`, `i1_gate_validator.PIPELINE_SYMBOLS`. Ningún otro módulo define su propia lista.

2. **Contenido inicial de `TRADED_UNIVERSE` (8 símbolos)** — la intersección de "candidato del pipeline" y "candidato del gate I1":

   ```
   BTCUSDT, ETHUSDT, EURUSD, GBPUSD, USDJPY, XAUUSD, US500, US30
   ```

3. **Nomenclatura canónica de índices: familia `US###` / `UK###` / `DE##` / `JP###`.** Se adopta `US500`, `US30` (y, cuando se incorporen, `UK100`, `DE40`, `JP225`, `NAS100`→se mantiene `NAS100`). Se **elimina** `SPX500` como alias en `constants.py`. Motivo: el gate I1, el pipeline y los parquet ya usan esta familia; cambiar tres consumidores es más caro que cambiar uno.

4. **Mapeo a símbolos de broker en un único dict** `BROKER_SYMBOL_MAP: dict[str, dict[str, str]]` en `core/config/constants.py` (`{símbolo_canónico: {"binance": "...", "mt5": "..."}}`). Los adapters de exchange traducen solo a través de este dict.

5. **Disponibilidad de datos explícita.** Un símbolo de `TRADED_UNIVERSE` sin parquet en `data/raw/` se marca `data_available: false`; el pipeline lo **salta con log** (`symbol_skipped_no_data`, con `correlation_id`), no falla el ciclo.

6. **Universo extendido (no operable).** SOLUSDT, BNBUSDT, resto de forex majors, XAGUSD, USOIL/UKOIL, NATGAS, WHEAT, DE40, JP225, NAS100, UK100 quedan como **catálogo de referencia** (`ASSET_CLASS_SYMBOLS`) pero fuera de `TRADED_UNIVERSE`. Entran a `TRADED_UNIVERSE` solo cuando (a) tienen datos y (b) pasan el gate I1 (ADR-003).

## Consecuencias

**Positivas**
- `test_universe_is_single_source` (F1.3): los tres consumidores producen el mismo set.
- Un solo lugar para añadir/quitar un activo; los offsets de `SCHEDULE` se derivan de la lista.
- El mapeo a broker deja de estar disperso en if/elif por exchange.

**Negativas / coste**
- Hay que reescribir `constants.py` (`SPX500`→`US500`, `NAS100` se mantiene) y revisar todo `grep -rn "SPX500"` en código, tests y datos.
- `settings.SUPPORTED_SYMBOLS` pasa de 10–28 a 8; cualquier test o doc que asuma el set viejo se actualiza.
- `run_pipeline.SCHEDULE` pierde AUDUSD/USDCHF/USDCAD/UK100 hasta que entren por el gate.

**Neutras**
- El catálogo extendido sigue visible para la API `/strategies` y el simulador como universo de exploración.

## Alternativas consideradas

- **A. Adoptar `SPX500`/`NAS100` como canónico.** Rechazada: obliga a tocar el gate I1, el pipeline y a renombrar los parquet; tres cambios en vez de uno.
- **B. `TRADED_UNIVERSE` = los 12 de `SCHEDULE`.** Rechazada: 4 de ellos no tienen datos ni corren en el gate; contradice el fail-safe de ADR-003.
- **C. `TRADED_UNIVERSE` = solo los símbolos con `i1_params` aprobado (hoy: XAUUSD).** Rechazada: mezcla dos conceptos. `TRADED_UNIVERSE` = "qué puede evaluar el gate y el pipeline"; `i1_params/<symbol>.json` = "qué opera de verdad ahora". El fail-safe de ADR-003 ya restringe la operativa al segundo conjunto.
