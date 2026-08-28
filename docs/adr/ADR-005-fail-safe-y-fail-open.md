# ADR-005 — Kill switch fail-safe obligatorio; blacklist de JWT fail-open aceptada

- **Estado:** Aceptado (2026-08-28)
- **Fase:** F0 · entregable 0.1 del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`
- **Contexto base:** `docs/AUDITORIA_INTEGRAL_2026-08-28.md` (S-04, S-06), auditorías 2026-05 / 2026-07 (kill switch fail-open, ya resuelto)
- **Relacionada:** ADR-001 (2 procesos), SPEC-G01 (F8, `python-jose` → `PyJWT`)

## Contexto

Dos componentes dependen de Redis y pueden degradar ante su caída, en direcciones opuestas de seguridad:

- **Kill switch** (`core/risk/kill_switch_redis.py`): si falla abierto (asume "inactivo" sin Redis), el sistema puede seguir operando mientras un límite de riesgo ya se cruzó. Impacto: pérdida de capital no acotada. Auditorías previas lo marcaron crítico; ya se corrigió a fail-safe (`is_active()` → `True` si Redis no responde; `KillSwitchRedisUnavailableError` propaga en `activate/reset`).
- **Blacklist de JWT** (`core/auth/token_blacklist.py`): si falla cerrado (rechaza todo token sin Redis), cualquier parpadeo de Redis tira abajo toda la autenticación. Si falla abierto, un token revocado sigue válido hasta su propia expiración (≤ 60 min access / ≤ 7 días refresh).

Se necesita una política escrita e inequívoca para no re-litigar esto en cada revisión de seguridad.

## Decisión

1. **El kill switch es fail-safe (fail-closed) de forma obligatoria.** Ante indisponibilidad de Redis o estado ilegible:
   - `is_active()` devuelve `True` (bloquea trading).
   - `activate()` / `reset()` propagan `KillSwitchRedisUnavailableError` (no silencian).
   - Se emite log `critical` (`kill_switch_fail_closed_redis_unavailable`).
   - Ningún cambio futuro puede introducir un camino en que la ausencia de Redis permita operar. Un test lo fija (`tests/unit/test_kill_switch.py`).

2. **La blacklist de JWT es fail-open, y se acepta como decisión consciente.** Ante indisponibilidad de Redis:
   - `is_blacklisted()` devuelve `False` (el token se evalúa por su firma/expiración normal).
   - `add()` no lanza; la revocación se pierde hasta que Redis vuelva.
   - Ventana de exposición acotada por el TTL del propio JWT (≤ 60 min access / ≤ 7 días refresh).
   - **Mitigaciones exigidas:** (a) alerta cuando Redis no está disponible para la blacklist; (b) F8/SPEC-G01 reduce la ventana revocando también el `jti` del refresh en logout y bajando/acotando TTLs; (c) `KillSwitchRedis.reset` valida el token dentro de la función (defensa en profundidad, S-06), no solo vía `require_admin` en la ruta.

3. **Regla general para componentes nuevos:** todo lo que gobierne **riesgo, ejecución o límites de capital** es fail-safe (ante duda, no opera). Lo que gobierne **disponibilidad de un servicio de autenticación/lectura** puede ser fail-open solo si (a) la ventana de exposición está acotada por un TTL, (b) hay alerta de la degradación y (c) queda registrado en un ADR.

## Consecuencias

**Positivas**
- Política única y citable; las revisiones de seguridad futuras verifican contra este ADR en vez de reabrir el debate.
- El peor caso del kill switch es "trading detenido de más" (recuperable); nunca "trading permitido de menos".
- El peor caso de la blacklist es una ventana ≤ TTL con un token revocado aún válido, con alerta, en vez de una caída total de auth por un blip de Redis.

**Negativas / coste**
- Fail-safe del kill switch: una caída de Redis detiene toda la operativa aunque no haya condición de riesgo real. Se asume; la mitigación es la disponibilidad de Redis (F8) y el arranque en 2 procesos (ADR-001).
- Fail-open de la blacklist: aceptamos una ventana de token revocado-pero-válido. Requiere las mitigaciones (a)/(b)/(c) para cerrarse en F8; hasta entonces es deuda de seguridad conocida (S-03, S-04).
- Obliga a que toda alerta de "Redis no disponible para blacklist" tenga un canal real (Telegram) — entra en F8 (SPEC-G02).

**Neutras**
- No cambia el comportamiento actual del código: ambos componentes ya se comportan así. El ADR lo ratifica y fija la regla para lo nuevo.

## Alternativas consideradas

- **A. Blacklist fail-closed.** Rechazada: un parpadeo de Redis deja fuera a todos los usuarios; radio de impacto mucho mayor que la ventana ≤ TTL que se evita.
- **B. Kill switch fail-open "para no frenar el negocio".** Rechazada de plano: contradice el principio rector de fail-safe by default; es exactamente el hallazgo crítico que las auditorías de mayo/julio obligaron a corregir.
- **C. Persistir el estado del kill switch y la blacklist en Postgres además de Redis.** Diferida: reduce la probabilidad de degradación pero añade acoplamiento y latencia; se revisará en F10 (HA) si la disponibilidad de Redis resulta insuficiente en paper.
