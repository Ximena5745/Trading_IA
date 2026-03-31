# Docker y Despliegue

> Infraestructura Docker, monitoreo y guía de despliegue

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `docker-compose.yml` | Orquestación de servicios |
| `docker/nginx.conf` | Configuración reverse proxy |
| `docker/prometheus.yml` | Configuración métricas |
| `scripts/setup_vps.ps1` | Script de setup VPS |

---

## Arquitectura Docker

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE SERVICES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ┌─────────────────────────┐                             │
│                    │         NGINX           │                             │
│                    │    (Reverse Proxy)      │                             │
│                    │        :80, :443        │                             │
│                    └───────────┬─────────────┘                             │
│                                │                                            │
│            ┌───────────────────┼───────────────────┐                       │
│            │                   │                   │                       │
│            ▼                   ▼                   ▼                       │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐            │
│   │      APP        │ │    GRAFANA      │ │   PROMETHEUS    │            │
│   │   (FastAPI +    │ │  (Dashboards)   │ │   (Metrics)     │            │
│   │   Streamlit)    │ │     :3000       │ │     :9090       │            │
│   │     :8000       │ └─────────────────┘ └─────────────────┘            │
│   └────────┬────────┘                                                     │
│            │                                                               │
│            ├─────────────────────────────────────────────────────┐        │
│            │                                                     │        │
│            ▼                                                     ▼        │
│   ┌─────────────────┐                                   ┌─────────────────┐
│   │   DATABASE      │                                   │     REDIS       │
│   │  (TimescaleDB)  │                                   │   (Cache)       │
│   │     :5432       │                                   │     :6379       │
│   └─────────────────┘                                   └─────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Servicios

### App (FastAPI + Streamlit)

```yaml
app:
  build:
    context: ..
    dockerfile: docker/Dockerfile
  ports:
    - "8000:8000"   # FastAPI
    - "8501:8501"   # Streamlit
  environment:
    - DATABASE_URL=postgresql+asyncpg://trader:trader@db:5432/trader_ai
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    - db
    - redis
  volumes:
    - ../data:/app/data
    - ../logs:/app/logs
```

### Database (TimescaleDB)

```yaml
db:
  image: timescale/timescaledb:latest-pg16
  ports:
    - "5432:5432"
  environment:
    - POSTGRES_USER=trader
    - POSTGRES_PASSWORD=trader
    - POSTGRES_DB=trader_ai
  volumes:
    - pgdata:/var/lib/postgresql/data
    - ../scripts/migrations:/docker-entrypoint-initdb.d
```

### Redis

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redisdata:/data
```

### Grafana

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - grafanadata:/var/lib/grafana
    - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
```

### Prometheus

```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - promdata:/prometheus
```

---

## Comandos Docker

### Iniciar Servicios

```bash
# Iniciar todo
cd docker
docker-compose up -d

# Verificar estado
docker-compose ps

# Ver logs
docker-compose logs -f app
docker-compose logs -f db
```

### Detener Servicios

```bash
# Detener todo
docker-compose down

# Detener y eliminar volúmenes (CUIDADO: elimina datos)
docker-compose down -v
```

### Reconstruir

```bash
# Reconstruir app
docker-compose build --no-cache app

# Aplicar cambios
docker-compose up -d app
```

### Ejecutar Comandos

```bash
# Ejecutar pipeline un ciclo
docker-compose exec app python scripts/run_pipeline.py --once BTCUSDT

# Ejecutar tests
docker-compose exec app pytest tests/ -v

# Ejecutar migración
docker-compose exec app python scripts/migrate.py
```

---

## Configuración Nginx

### nginx.conf

```nginx
upstream api {
    server app:8000;
}

upstream streamlit {
    server app:8501;
}

server {
    listen 80;
    server_name trader-ai.local;

    # API
    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Streamlit
    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://grafana:3000/;
    }
}
```

---

## Prometheus Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'trader-ai'
    static_configs:
      - targets: ['app:8001']
    
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

---

## Variables de Entorno

### .env (Producción)

```env
# ─── Execution ─────────────────────────────────────────────────────
EXECUTION_MODE=paper
TRADING_ENABLED=false

# ─── Database ──────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://trader:trader@db:5432/trader_ai
REDIS_URL=redis://redis:6379/0

# ─── Security ──────────────────────────────────────────────────────
JWT_SECRET_KEY=<generar-64-chars-aleatorios>

# ─── Binance ───────────────────────────────────────────────────────
BINANCE_API_KEY=<clave-testnet>
BINANCE_SECRET_KEY=<secreto-testnet>
BINANCE_TESTNET=true

# ─── MT5 (IC Markets) ─────────────────────────────────────────────
MT5_LOGIN=0
MT5_PASSWORD=
MT5_SERVER=ICMarketsSC-Demo

# ─── Telegram ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ─── Alerts ────────────────────────────────────────────────────────
ALERT_DAILY_LOSS_PCT=0.10
ALERT_DRAWDOWN_PCT=0.20
```

---

## Despliegue en VPS

### Proveedores Recomendados

| Proveedor | Specs | Costo | Uso |
|-----------|-------|-------|-----|
| Hetzner CX21 | 2 vCPU / 4 GB | ~5 €/mes | Paper trading |
| DigitalOcean | 1 vCPU / 2 GB | ~12 USD/mes | Paper trading |
| AWS t3.small | 2 vCPU / 2 GB | ~15 USD/mes | Producción |

### Script de Setup

```bash
# En el servidor
curl -fsSL https://get.docker.com | sh
git clone https://github.com/Ximena5745/Trading_IA.git
cd Trading_IA
cp .env.example .env
nano .env  # Configurar variables
docker-compose up -d
curl http://localhost:8000/health
```

### Checklist de Seguridad

- [ ] Nginx con HTTPS (Let's Encrypt)
- [ ] Firewall: solo puertos 80, 443, SSH
- [ ] Cambiar contraseña default de Grafana
- [ ] Verificar rate limiting
- [ ] Rotar JWT_SECRET_KEY regularmente
- [ ] Usar VPN para acceder a Grafana

---

## Monitoreo

### Endpoints de Health

```bash
# Health check
curl http://localhost:8000/health

# Response:
{
    "status": "ok",
    "version": "2.0.0",
    "execution_mode": "paper",
    "trading_enabled": false
}

# Métricas Prometheus
curl http://localhost:8001/metrics
```

### Grafana Dashboards

| Dashboard | Métricas |
|-----------|----------|
| System | CPU, Memory, Disk |
| Pipeline | Cycles/min, Errors, Latency |
| Trading | PnL, Win Rate, Drawdown |
| Risk | Kill Switch, Exposure |

### URLs de Acceso

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Streamlit | http://localhost:8501 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

---

## Backup

### Backup PostgreSQL

```bash
# Backup completo
docker-compose exec db pg_dump -U trader trader_ai > backup.sql

# Backup comprimido
docker-compose exec db pg_dump -U trader trader_ai | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Backup Modelos

```bash
# Copiar modelos entrenados
cp -r data/models/ backups/models_$(date +%Y%m%d)/
```

### Script Automático

```bash
# Agregar a cron (daily at 2 AM)
0 2 * * * cd /path/to/project && ./scripts/backup_db.sh
```

---

## Troubleshooting

### Problemas Comunes

| Problema | Solución |
|----------|----------|
| Container no inicia | `docker-compose logs <service>` |
| DB connection failed | Verificar DATABASE_URL |
| Redis connection failed | Verificar REDIS_URL |
| MT5 no conecta | Verificar MT5_LOGIN, MT5_PASSWORD |
| Sin datos | Verificar Binance API keys |

### Comandos de Debug

```bash
# Ver logs detallados
docker-compose logs -f --tail=100 app

# Entrar al container
docker-compose exec app bash

# Verificar conexión DB
docker-compose exec db psql -U trader -d trader_ai -c "SELECT 1"

# Verificar Redis
docker-compose exec redis redis-cli ping
```

---

## CI/CD

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest tests/ -v
      - run: python scripts/ci_backtest_gate.py
```

---

*Volver al [índice de integración técnica](README.md)*
