# Governance & Technical Standards

> Sistema de gobierno técnico, ownership y procesos

---

## 1. GOVERNANCE FRAMEWORK

### 1.1 Principios de Gobierno

| Principio | Descripción |
|-----------|-------------|
| **SPEC-DRIVEN** | Toda feature comienza con SPEC |
| **CLEAN ARCHITECTURE** | Separación estricta de capas |
| **SOLID** | Principios de diseño |
| **TEST-FIRST** | Tests antes de código |
| **SECURITY-FIRST** | Security por defecto |
| **OBSERVABILITY** | Logging y métricas desde day 1 |

### 1.2 Niveles de Decisión

| Nivel | Decisiones | Aprobación |
|-------|------------|------------|
| Architecture | Patrones, stack, estructura | Tech Lead |
| Module | APIs, contracts, dependencies | Module Owner |
| Code | Implementación | Peer Review |
| Config | Settings, constants | Module Owner |

---

## 2. ROLES Y RESPONSIBILITIES

### 2.1 Roles Técnicos

| Rol | Responsabilidad | Coverage |
|-----|-----------------|-----------|
| **Architect** | Arquitectura general, patterns | Todo el sistema |
| **Module Owner** | módulo específico | Su módulo |
| **Tech Lead** | Decisiones técnicas | Proyecto |
| **Code Reviewer** | Peer review | PRs asignados |

### 2.2 Roles de Proyecto

| Rol | Responsibilities |
|-----|------------------|
| **Quant Lead** | Estrategias, ML, backtesting |
| **DevOps Lead** | Infra, deployment, CI/CD |
| **Security Lead** | Security, compliance |
| **Product Owner** | Priorización, roadmap |

---

## 3. OWNERSHIP MATRIX

### 3.1 Module Ownership

| Módulo | Owner | Backup |
|--------|-------|--------|
| Agent System | Quant Lead | ML Engineer |
| Consensus | Quant Lead | - |
| Signal Engine | Quant Lead | - |
| Risk Engine | Security Lead | Risk Engineer |
| Execution | DevOps Lead | Backend Dev |
| Portfolio | Quant Lead | - |
| Ingestion | Backend Dev | DevOps |
| Auth | Security Lead | - |
| ML Pipelines | ML Engineer | Quant Lead |
| Observability | DevOps Lead | - |

### 3.2 File Ownership

```
core/
├── agents/              → Quant Lead
├── consensus/           → Quant Lead
├── signals/             → Quant Lead
├── risk/                → Security Lead
├── execution/           → DevOps Lead
├── portfolio/           → Quant Lead
├── ingestion/           → Backend Dev
├── auth/                → Security Lead
├── ml/                  → ML Engineer
├── observability/       → DevOps Lead
└── config/              → Architect

api/
└── routes/              → Backend Dev

domain/
└── entities/            → Architect

tests/                   →/shared
```

---

## 4. REVIEW PROCESS

### 4.1 Code Review

```python
# PR Requirements
- 1 approval mínimo (2 para critical paths)
- Todos los tests passing
- Coverage > 80% (unit)
- No security issues (bandit, safety)
- Type checks passing (mypy)
- Linting passing (ruff)
```

### 4.2 Architecture Review

```
Changes that require Architecture Review:
- Nuevas dependencias externas
- Cambios en contratos de API
- Nuevos módulos
- Cambios en patrones arquitectónicos
- Cambios en seguridad
- Cambios en base de datos

Process:
1. Draft ADR (Architecture Decision Record)
2. Presentar a Architect
3. Discutir y decidir
4. Documentar decisión
```

### 4.3 Quant Review

```
Changes that require Quant Review:
- Nuevas estrategias
- Cambios en parámetros de riesgo
- Nuevos modelos ML
- Cambios en validación cuantitativa

Process:
1. Documentar estrategia con SPEC
2. Walk-forward backtest
3. Peer review de resultados
4. Approve/Reject
```

---

## 5. RACI MATRIX

### 5.1 Feature Development

| Actividad | Architect | Module Owner | Dev | QA | Security |
|-----------|-----------|--------------|-----|-----|----------|
| SPEC creation | A | R | C | C | C |
| Implementation | I | A | R | - | C |
| Code Review | I | A | R | - | C |
| Testing | I | C | R | R | - |
| Security Review | A | C | I | - | R |
| Deployment | I | I | C | - | A |

### 5.2 Legend

- **R** - Responsible (ejecuta)
- **A** - Accountable (aprueba)
- **C** - Consulted (consultado)
- **I** - Informed (informado)

---

## 6. TECHNICAL STANDARDS

### 6.1 Coding Standards

| Estándar | Herramienta | Target |
|----------|-------------|--------|
| Formatting | Black | 100% |
| Linting | Ruff | 0 errors |
| Types | MyPy | strict |
| Security | Bandit | 0 highs |
| Complexity | SonarCloud | A |

### 6.2 Testing Standards

| Tipo | Target | Herramienta |
|------|--------|-------------|
| Unit | 80% | pytest |
| Integration | 50% | pytest |
| E2E | Critical paths | playwright |
| Performance | Baseline | locust |

### 6.3 Documentation Standards

| Tipo | Required | Location |
|------|----------|----------|
| SPEC | Yes | specs/ |
| Module doc | Yes | docs/modules/ |
| API doc | Yes | docs/api/ |
| README | New modules | In module |
| Changelog | Yes | CHANGELOG.md |

---

## 7. COMPLIANCE

### 7.1 Auditorías

| Auditoría | Frecuencia | Owner |
|-----------|------------|-------|
| Security | Trimestral | Security Lead |
| Code Quality | Mensual | Tech Lead |
| Performance | Trimestral | DevOps |
| Compliance | Anual | External |

### 7.2 Requirements

- Logs de auditoría para acciones sensitive
- Retención de logs: 1 año
- Backup: daily, retención 30 días
- Disaster recovery plan documentado

---

## 8. TECHNICAL DEBT

### 8.1 Tracking

```markdown
# Technical Debt Registry

## Prioritized

| ID | Description | Impact | Effort | Owner | Due |
|----|-------------|--------|--------|-------|-----|
| TD-001 | Migrate to Python 3.11 | Medium | High | Backend | Q3 |
| TD-002 | Refactor ML pipeline | Medium | Medium | ML | Q2 |
| TD-003 | Add circuit breaker | High | Low | Backend | Q2 |

## Backlog

| ID | Description | Impact | Effort |
|----|-------------|--------|--------|
| TD-004 | Migrate from REST to gRPC | Low | High |
```

### 8.2 Governance

- Review de technical debt: semanal
- Budget de tiempo: 20% para debt reduction
- No new features con TD-001+ unresolved

---

## 9. CHANGE MANAGEMENT

### 9.1 Types of Changes

| Type | Approval | Testing | Rollback |
|------|----------|---------|----------|
| Hotfix | Fast track | Critical only | Required |
| Minor | Module Owner | Standard | Required |
| Major | Architect | Full | Required |
| Breaking | RFC + approbal | Full + migration | Required |

### 9.2 Change Process

```
1. Create issue with:
   - Description
   - Impact assessment
   - Test plan
   - Rollback plan
   
2. Get approval based on type

3. Implement with feature branch

4. Pass all gates:
   - Tests
   - Code review
   - Security scan
   - Performance test (if major)
   
5. Deploy with monitoring

6. Verify and close
```

---

## 10. INCIDENT RESPONSE

### 10.1 Severity Levels

| Level | Response Time | Examples |
|-------|---------------|----------|
| Critical (P1) | 15 min | System down, data loss |
| High (P2) | 1 hour | Major feature broken |
| Medium (P3) | 4 hours | Minor feature broken |
| Low (P4) | 24 hours | Cosmetic issues |

### 10.2 Escalation

```
P1 → Tech Lead + Architect + Product Owner
P2 → Module Owner + Tech Lead
P3 → Module Owner
P4 → Team triage
```

---

## 11. CONTINUOUS IMPROVEMENT

### 11.1 Retrospectives

- **Frecuencia**: Quincenal
- **Asistentes**: Todo el equipo
- **Outputs**: Action items, improvements

### 11.2 Metrics

| Métrica | Target | Review |
|---------|--------|--------|
| Lead time | < 2 días | Weekly |
| Cycle time | < 5 días | Weekly |
| Pass rate | > 90% | Daily |
| Tech debt ratio | < 10% | Monthly |

---

*Volver al [INDEX](INDEX.md)*