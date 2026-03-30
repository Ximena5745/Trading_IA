# 🚀 Guía de Despliegue - Trading IA

**Última actualización**: 2026-03-30
**Versión**: 2.0.0

---

## 📋 Tabla de Contenidos

1. [Opciones de Despliegue](#opciones-de-despliegue)
2. [Setup Local/Development](#setup-localdev)
3. [Despliegue en VPS](#despliegue-en-vps)
4. [Despliegue con Docker](#despliegue-con-docker)
5. [Despliegue en Cloud](#despliegue-en-cloud)
6. [Configuración de Seguridad](#configuración-de-seguridad)
7. [Monitoreo y Mantenimiento](#monitoreo-y-mantenimiento)

---

## 🎯 Opciones de Despliegue

### Comparativa

| Opción | Costo | Setup | Escalabilidad | Recomendación |
|---|---|---|---|---|
| **Local/Dev** | Gratis | 15 min | Baja | Desarrollo |
| **VPS (Hetzner)** | €5/mes | 30 min | Media | Inicio |
| **VPS (DigitalOcean)** | $12/mes | 30 min | Media | Inicio |
| **Docker (local)** | Gratis | 20 min | Media | Testing |
| **AWS EC2** | $15-50/mes | 30 min | Alta | Enterprise |
| **Railway** | $5-50/mes | 10 min | Alta | Principiantes |

---

## 🏠 Setup Local/Dev

### Requerimientos
```bash
# Ya completado en SETUP_MANUAL.md
# Solo para recordatorio:

✅ Python 3.10+
✅ PostgreSQL (local o Docker)
✅ Redis (local o Docker)
✅ Git
```

### Iniciar en Local

```bash
# 1. Clonar repo
git clone https://github.com/Ximena5745/Trading_IA.git
cd "Trading IA"

# 2. Virtual env
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 3. Dependencias
pip install -r requirements.txt -r requirements-multiactivos.txt

# 4. Setup .env
cp .env.example .env
# Editar con valores locales

# 5. Servicios
docker-compose up -d db redis  # O instalar en local

# 6. Iniciar
uvicorn api.main:app --reload   # Terminal 1
streamlit run app/main.py        # Terminal 2
```

---

## 🖥️ Despliegue en VPS

### Opción A: Hetzner CX21 (Recomendado - €5/mes)

#### 1. Crear VPS

1. Ir a https://www.hetzner.com/
2. Sign up / Login
3. Cloud → Crear servidor
4. **Specs recomendadas:**
   - CPUs: 2 vCPU
   - RAM: 4 GB
   - Disk: 40 GB SSD
   - OS: Ubuntu 22.04 LTS
5. Seleccionar SSH key o crear una
6. Crear servidor

#### 2. Conectarse por SSH

```bash
# En tu máquina local
ssh root@<IP_DEL_SERVIDOR>

# Anotar la IP para referencias futuras
```

#### 3. Preparar Servidor

```bash
# Actualizar sistema
apt-get update && apt-get upgrade -y

# Instalar dependencias
apt-get install -y curl wget git build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev llvm libncurses5-dev \
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev

# Instalar Python 3.10
apt-get install -y python3.10 python3.10-venv python3-pip

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Instalar Git
apt-get install -y git

# Crear usuario no-root (recomendado)
adduser trader
usermod -aG docker trader
su - trader
```

#### 4. Clonar y Configurar Proyecto

```bash
# Como usuario 'trader'
cd /home/trader

# Clonar
git clone https://github.com/Ximena5745/Trading_IA.git
cd Trading_IA

# Virtual env
python3.10 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt -r requirements-multiactivos.txt

# Copiar .env
cp .env.example .env

# Editar .env con valores de PRODUCCIÓN
nano .env
```

#### 5. Configurar .env para Producción

```env
# SECURITY
EXECUTION_MODE=paper          # O 'live' si estás listo
TRADING_ENABLED=false         # Cambiar a true solo cuando estés seguro
JWT_SECRET_KEY=<GENERA_UNA_CLAVE_SEGURA_DE_64_CHARS>

# DATABASE (PostgreSQL en Docker)
DATABASE_URL=postgresql+asyncpg://trader:contraseña_fuerte@localhost:5432/trader_ai

# REDIS
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000

# EXCHANGES
BINANCE_ENABLED=true
BINANCE_TESTNET=true
BINANCE_API_KEY=<tu_testnet_key>
BINANCE_SECRET_KEY=<tu_testnet_secret>

IB_ENABLED=false  # Cambiar a true si configuraste IB
IB_HOST=127.0.0.1
IB_PORT=7498

# NOTIFICATIONS (opcional)
NOTIFICATIONS_ENABLED=false
TELEGRAM_BOT_TOKEN=<optional>
TELEGRAM_CHAT_ID=<optional>
```

#### 6. Iniciar Servicios con Docker Compose

```bash
# Desde la carpeta del proyecto
cd docker

# Iniciar PostgreSQL, Redis, Grafana, Prometheus
docker-compose up -d

# Verificar
docker-compose ps

# Ver logs
docker-compose logs -f
```

#### 7. Iniciar API en Background

```bash
# Opción A: Using systemd (recomendado)

# Crear archivo systemd
sudo nano /etc/systemd/system/trader-api.service
```

**Contenido de `/etc/systemd/system/trader-api.service`:**
```ini
[Unit]
Description=Trading IA API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=notify
User=trader
WorkingDirectory=/home/trader/Trading_IA
Environment="PATH=/home/trader/Trading_IA/venv/bin"
ExecStart=/home/trader/Trading_IA/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar
sudo systemctl daemon-reload
sudo systemctl enable trader-api
sudo systemctl start trader-api
sudo systemctl status trader-api

# Ver logs
sudo journalctl -u trader-api -f
```

#### 8. Configurar Nginx como Reverse Proxy

```bash
# Instalar Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Crear configuración
sudo nano /etc/nginx/sites-available/trader-api
```

**Contenido de `/etc/nginx/sites-available/trader-api`:**
```nginx
upstream trader_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name tu-dominio.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://trader_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location /metrics {
        proxy_pass http://127.0.0.1:9090;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/trader-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# SSL con Let's Encrypt (HTTPS)
sudo certbot --nginx -d tu-dominio.com
```

#### 9. Verificar Despliegue

```bash
# API
curl -X GET http://tu-dominio.com/health

# Swagger UI
curl -X GET http://tu-dominio.com/docs

# Métricas
curl -X GET http://tu-dominio.com/metrics
```

---

## 🐳 Despliegue con Docker

### Local con Docker Compose

```bash
# Build image
docker build -t trader-ai:latest .

# Ver docker-compose.yml
cat docker/docker-compose.yml

# Iniciar todo
cd docker
docker-compose up -d

# Servicios disponibles:
# - API: http://localhost:8000
# - Grafana: http://localhost:3000
# - Prometheus: http://localhost:9090
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### Dockerfile Personalizado

Si necesitas un Dockerfile:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt requirements-multiactivos.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-multiactivos.txt

# Código
COPY . .

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Iniciar
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ☁️ Despliegue en Cloud

### Opción A: Railway (Más simple - $5-50/mes)

#### 1. Crear Cuenta y Proyecto

1. Ir a https://railway.app/
2. Sign up con GitHub
3. Crear nuevo proyecto

#### 2. Conectar Repositorio

```bash
# Railway conectará directamente desde GitHub
# Solo necesitas autorizar el acceso
```

#### 3. Configurar Variables de Entorno

En Railway dashboard:
```
EXECUTION_MODE=paper
TRADING_ENABLED=false
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET_KEY=...
```

#### 4. Deploy

Railway detectará automáticamente `docker-compose.yml` y deployará.

### Opción B: AWS EC2 (Más control - $15-50/mes)

#### 1. Crear Instancia

```bash
# Ir a AWS Console → EC2
# Crear instancia:
# - AMI: Ubuntu 22.04 LTS
# - Tipo: t3.small (2 vCPU, 2 GB RAM)
# - Security group: Abrir puertos 80, 443, 22
```

#### 2. Conectarse

```bash
# Descargar key pair y conectar
ssh -i tu-key.pem ec2-user@tu-ip.amazonaws.com
```

#### 3. Seguir pasos de VPS (Hetzner) adaptado a AWS

El proceso es similar al VPS, solo cambian los comandos iniciales.

---

## 🔒 Configuración de Seguridad

### Checklist Pre-Producción

```bash
# 1. Firewall
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # PostgreSQL no expuesto
sudo ufw deny 6379/tcp  # Redis no expuesto

# 2. SSH
sudo nano /etc/ssh/sshd_config
# Cambiar: PermitRootLogin no
# Cambiar: PasswordAuthentication no

sudo systemctl restart ssh

# 3. Certificado SSL
# Ya configurado con Let's Encrypt

# 4. Database
# Cambiar contraseña por defecto:
psql -U trader -h localhost -d trader_ai
ALTER USER trader WITH PASSWORD 'nueva_contraseña_fuerte';

# 5. JWT Secret
# Generar: python -c "import secrets; print(secrets.token_urlsafe(64))"
# Actualizar en .env

# 6. Rate limiting
# Ya configurado en FastAPI (slowapi)

# 7. CORS
# Verificar en api/main.py que solo dominios autorizados
```

### Variables Sensibles

```bash
# NUNCA commitar:
# - .env con credenciales reales
# - API keys de exchanges
# - Contraseñas de BD

# Usar en su lugar:
# - Secrets de GitHub (si usas CI/CD)
# - Sistema de secretos de tu proveedor cloud
# - Variables de entorno del sistema
```

---

## 📊 Monitoreo y Mantenimiento

### Dashboards

- **Grafana**: http://tu-dominio.com/grafana (puerto 3000)
  - Usuario: admin
  - Contraseña: admin (CAMBIAR)
- **Prometheus**: http://tu-dominio.com/prometheus (puerto 9090)

### Logs

```bash
# API logs
sudo journalctl -u trader-api -f

# Docker logs
docker logs -f trader-db
docker logs -f trader-redis

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Backups

```bash
# PostgreSQL backup diario
0 2 * * * pg_dump -U trader trader_ai > /backups/trader_ai_$(date +\%Y\%m\%d).sql

# Redis dump
SAVE 900 1     # En redis.conf
SAVE 300 10
SAVE 60 10000
```

### Monitoreo de Procesos

```bash
# Instalar Supervisor (optional)
sudo apt-get install -y supervisor

# Crear configuración
sudo nano /etc/supervisor/conf.d/trader-api.conf
```

```ini
[program:trader-api]
command=/home/trader/Trading_IA/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
directory=/home/trader/Trading_IA
user=trader
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/trader-api.log
```

---

## 🚨 Troubleshooting en Producción

### Problema: API no responde

```bash
# Verificar servicio
sudo systemctl status trader-api

# Revisar logs
sudo journalctl -u trader-api -n 50

# Reiniciar
sudo systemctl restart trader-api
```

### Problema: Conexión a BD

```bash
# Verificar PostgreSQL
sudo systemctl status postgresql
docker ps | grep postgres

# Probar conexión
psql -U trader -h localhost -d trader_ai -c "SELECT 1"
```

### Problema: Memoria llena

```bash
# Ver uso
free -h
df -h

# Limpiar logs antiguos
sudo journalctl --vacuum=7d

# Limpiar Docker
docker system prune -a
```

### Problema: CPU alta

```bash
# Identificar proceso
top
htop

# Revisar logs de API
sudo journalctl -u trader-api -f | grep -i error
```

---

## 📈 Escalado

### Cuando crezca

```bash
# Load Balancer (Nginx upstream)
# Múltiples instancias de API
# Base de datos dedicada
# Redis dedicado
# CDN para assets estáticos
```

### Configuración Escalada

```nginx
upstream trader_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}
```

---

## ✅ Checklist de Despliegue

- [ ] Código commiteado y pusheado
- [ ] Tests pasando (pytest)
- [ ] `.env` configurado para producción
- [ ] SSL/HTTPS configurado
- [ ] Firewall configurado
- [ ] Backups configurados
- [ ] Monitoreo configurado
- [ ] Alertas (Telegram) configuradas
- [ ] Domain pointeando a servidor
- [ ] Health check respondiendo
- [ ] API documentada en /docs
- [ ] Métricas en Prometheus

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisa logs**: `sudo journalctl -u trader-api -f`
2. **Verifica conectividad**: `curl http://localhost:8000/health`
3. **Resetea servicios**: `docker-compose restart`
4. **Revisa documentación**: `SETUP_MANUAL.md`
5. **Issues en GitHub**: https://github.com/Ximena5745/Trading_IA/issues

---

**¡Despliegue completado!** 🚀
