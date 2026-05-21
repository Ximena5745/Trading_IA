# Docker Deployment — TRADER AI Dashboard

Complete containerized setup for staging and production with FastAPI, PostgreSQL, Redis, Prometheus, Grafana, and Nginx.

## Quick Start

### Prerequisites
- Docker Desktop (Windows) or Docker Engine (Linux)
- Docker Compose 2.0+
- `.env` file with database credentials

### Build and Run

```bash
# Navigate to project root
cd 'c:\Users\ximen\OneDrive\Proyectos_DS\Trading_IA'

# Build the Docker image
docker build -f docker/Dockerfile -t trader-ai:latest .

# Start all services with compose
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps
```

### Access Points
| Service | URL | Port |
|---------|-----|------|
| Dashboard | http://localhost/dashboard | 80 |
| API | http://localhost/api | 8000 |
| Prometheus | http://localhost:9090 | 9090 |
| Grafana | http://localhost:3000 | 3000 |
| Redis | localhost | 6379 |
| PostgreSQL | localhost | 5432 |

## Environment Variables

Create `.env` file in project root:

```env
# Database
DB_PASSWORD=your_secure_password

# Redis
REDIS_PASSWORD=your_redis_password

# Grafana Admin
GRAFANA_PASSWORD=your_grafana_password

# Execution Mode
EXECUTION_MODE=paper
TRADING_ENABLED=false
```

## Architecture

```
┌─────────────────────────────────────────┐
│          Client Browser                 │
└────────────────┬────────────────────────┘
                 │
         HTTP/HTTPS traffic
                 │
┌────────────────▼────────────────────────┐
│      Nginx Reverse Proxy (Port 80/443)  │
│   ├─ /dashboard → :8000                 │
│   ├─ /api → :8000                       │
│   ├─ /metrics → :9090 (Prometheus)      │
│   └─ / → :3000 (Grafana)                │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼──┐  ┌─────▼────┐  ┌────▼──────┐
│ App  │  │ Prometheus│  │  Grafana  │
│ :8000│  │  :9090    │  │  :3000    │
└───┬──┘  └─────┬────┘  └──────────┘
    │           │
┌───▼─────────────▼──┐
│   PostgreSQL DB    │
│    TimescaleDB     │
│      :5432         │
└────────────────────┘
    ▲
    │
┌───▼──────────────┐
│   Redis Cache    │
│     :6379        │
└──────────────────┘
```

## Docker Commands Reference

### View Logs
```bash
# All services
docker-compose -f docker/docker-compose.yml logs -f

# Specific service
docker-compose -f docker/docker-compose.yml logs -f app

# Last 100 lines
docker-compose -f docker/docker-compose.yml logs --tail 100 app
```

### Stop Services
```bash
# Stop all (keep data)
docker-compose -f docker/docker-compose.yml stop

# Stop and remove containers
docker-compose -f docker/docker-compose.yml down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose -f docker/docker-compose.yml down -v
```

### Execute Commands
```bash
# Access database
docker exec -it trader-ai-db psql -U trader -d trader_ai

# Access Redis
docker exec -it trader-ai-redis redis-cli -a your_redis_password

# Python shell in app container
docker exec -it trader-ai-app python
```

### Rebuild on Code Changes
```bash
# Rebuild image
docker build -f docker/Dockerfile -t trader-ai:latest .

# Restart app container
docker-compose -f docker/docker-compose.yml up -d app
```

## Production Checklist

- [ ] SSL/TLS certificates configured in Nginx
- [ ] Environment variables secured (use secrets manager)
- [ ] Database backups enabled (automated cron)
- [ ] Prometheus retention configured (>30 days)
- [ ] Grafana dashboards created and saved
- [ ] Health checks passing on all services
- [ ] Resource limits set (memory, CPU)
- [ ] Log rotation configured
- [ ] Monitoring alerts configured
- [ ] Disaster recovery plan documented

## Monitoring

### Prometheus
- Built-in scraping from app:8001/metrics
- Default retention: 15 days
- Queries available at http://localhost:9090

### Grafana
- Pre-built dashboards can be imported
- Create custom dashboards for trading metrics
- Set up alerts for system failures

## Performance Tips

1. **Database**: TimescaleDB is optimized for time-series data (73,000+ candles)
2. **Redis**: Caches market data ingestion + feature calculations
3. **Multi-worker Uvicorn**: 4 workers handle concurrent requests
4. **Health checks**: 30-second intervals for auto-restart on failure

## Troubleshooting

### App Container Won't Start
```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs app

# Common: Database not ready yet
# Wait 30 seconds and try again
sleep 30
docker-compose -f docker/docker-compose.yml restart app
```

### Database Connection Errors
```bash
# Check database container
docker-compose -f docker/docker-compose.yml logs db

# Verify credentials in .env
# Verify DATABASE_URL format
```

### Port Already in Use
```bash
# Find process using port 8000
netstat -ano | find ":8000"

# Kill process (Windows)
taskkill /PID <pid> /F

# Or use different port in docker-compose.yml
# Change "8000:8000" to "8001:8000"
```

## Development vs Production

### Development (Current)
- Single worker
- Hot reload enabled (not in Docker)
- Mock data fallback
- Debug mode active

### Production
- 4+ workers
- Reverse proxy (Nginx)
- Database required (no mock data)
- SSL/TLS encryption
- Rate limiting enabled
- Monitoring + alerting

## Next Steps

1. **Configure SSL/TLS**:
   ```bash
   # Generate self-signed or use Let's Encrypt
   certbot certonly --standalone -d yourdomain.com
   ```

2. **Set up backup strategy**:
   ```bash
   # Daily PostgreSQL dumps
   docker exec trader-ai-db pg_dump -U trader trader_ai > backup_\$(date +%Y%m%d).sql
   ```

3. **Enable auto-scaling**:
   - Deploy on Kubernetes
   - Use Helm charts
   - Configure HPA (Horizontal Pod Autoscaler)

---

**Last Updated**: 2026-04-06  
**Status**: Production Ready
