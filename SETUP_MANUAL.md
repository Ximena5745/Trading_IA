# 📖 Guía Manual Detallada de Configuración - Trading IA

**Última actualización**: 2026-03-30
**Versión**: 2.0.0
**Estado**: Completo

> Este documento proporciona instrucciones paso-a-paso para configurar Trading IA con soporte multiactivos (Crypto, Forex, Índices, Commodities).

---

## 📋 Tabla de Contenidos

1. [Fase 0: Preparar Ambiente](#fase-0-preparar-ambiente)
2. [Fase 1: Instalar Dependencias](#fase-1-instalar-dependencias)
3. [Fase 2: Configurar Variables de Entorno](#fase-2-configurar-variables-de-entorno)
4. [Fase 3: PostgreSQL Setup](#fase-3-postgresql-setup)
5. [Fase 4: Redis Setup](#fase-4-redis-setup)
6. [Fase 5: Interactive Brokers (IB)](#fase-5-interactive-brokers-ib)
7. [Fase 6: MetaTrader 5 (MT5)](#fase-6-metatrader-5-mt5)
8. [Fase 7: Docker Compose](#fase-7-docker-compose)
9. [Fase 8: Descargar Datos Históricos](#fase-8-descargar-datos-históricos)
10. [Fase 9: Entrenar Modelos ML](#fase-9-entrenar-modelos-ml)
11. [Fase 10: Iniciar Aplicación](#fase-10-iniciar-aplicación)
12. [Fase 11: Validación y Testing](#fase-11-validación-y-testing)
13. [Troubleshooting](#troubleshooting)
14. [Checklist Completo](#checklist-completo)

---

## Fase 0: Preparar Ambiente

### 0.1 Requisitos Previos

Verifica que tengas:

```bash
# Windows
cmd /c "ver"                                    # Ver versión Windows
python --version                               # Python 3.10+
git --version                                  # Git 2.30+

# macOS
system_profiler SPSoftwareDataType
python3 --version
git --version

# Linux
cat /etc/os-release
python3 --version
git --version
```

**Versiones mínimas requeridas:**
- Python: 3.10.x
- Git: 2.30.x
- Docker: 20.10.x (opcional pero recomendado)

### 0.2 Clonar Repositorio

```bash
# Elegir ubicación (sin espacios si es posible)
cd ~
# O en Windows: cd %USERPROFILE%

# Clonar
git clone https://github.com/Ximena5745/Trading_IA.git
cd Trading_IA

# Verificar estructura
ls -la  # macOS/Linux
dir     # Windows
```

**Estructura esperada:**
```
Trading_IA/
├── api/
├── app/
├── core/
├── scripts/
├── docker/
├── data/
├── requirements.txt
└── .env.example
```

### 0.3 Crear Virtual Environment

```bash
# macOS/Linux
python3.10 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (CMD)
python -m venv venv
venv\Scripts\activate.bat

# Verificar
python --version              # Debe mostrar 3.10.x
which python                  # macOS/Linux - debe apuntar a venv
where python                  # Windows - debe apuntar a venv
```

---

## Fase 1: Instalar Dependencias

### 1.1 Actualizar pip

```bash
python -m pip install --upgrade pip setuptools wheel
pip --version  # Verificar
```

### 1.2 Instalar Core Requirements

```bash
pip install -r requirements.txt
```

**Principales paquetes:**
- fastapi==0.104.1
- streamlit==1.30.0
- pandas==2.1.3
- numpy==1.24.3
- scikit-learn==1.3.2
- xgboost==2.0.0
- sqlalchemy==2.0.23
- asyncpg==0.29.0
- redis==5.0.1

### 1.3 Instalar Multiactivos Requirements

```bash
pip install -r requirements-multiactivos.txt
```

**Paquetes adicionales:**
- ib_insync==10.28.0 (Interactive Brokers)
- MetaTrader5==5.0.5640 (Windows only)
- binance-connector==3.4.0

### 1.4 Validar Instalación

```bash
# Verificar que se instaló todo
python -c "import fastapi; import streamlit; import pandas; import numpy; print('✅ Core installed')"
python -c "import ib_insync; print('✅ IB installed')"

# En Windows, MT5 podría fallar si no está en la ruta correcta
# Continuaremos en Fase 6
```

---

## Fase 2: Configurar Variables de Entorno

### 2.1 Copiar .env.example

```bash
# macOS/Linux
cp .env.example .env

# Windows
copy .env.example .env
```

### 2.2 Editar .env

```bash
# Usar tu editor preferido
nano .env          # macOS/Linux
code .env          # VS Code (cualquier plataforma)
notepad .env       # Windows CMD
```

### 2.3 Configuración Esencial

```env
# ─ PROYECTO ─────────────────────────────────────
PROJECT_NAME=Trading IA
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# ─ SEGURIDAD ─────────────────────────────────────
EXECUTION_MODE=paper          # paper|live (recomendado: paper para testing)
TRADING_ENABLED=false         # Cambiar a true solo cuando estés listo
JWT_SECRET_KEY=<GENERA_CON_PYTHON_ABAJO>  # Ver sección 2.4

# ─ DATABASE (PostgreSQL) ────────────────────────
DATABASE_URL=postgresql+asyncpg://trader:contraseña@localhost:5432/trader_ai
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# ─ REDIS ─────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# ─ API ───────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8501"]

# ─ BINANCE (Crypto) ──────────────────────────────
BINANCE_ENABLED=true
BINANCE_TESTNET=true
BINANCE_API_KEY=your_testnet_key
BINANCE_SECRET_KEY=your_testnet_secret

# ─ INTERACTIVE BROKERS ───────────────────────────
IB_ENABLED=false              # Cambiar a true cuando tengas cuenta
IB_HOST=127.0.0.1
IB_PORT=7498                  # 7498=paper, 7497=live
IB_CLIENT_ID=1
IB_ACCOUNT_ID=your_account    # P123456789 (papel) o U123456789 (live)

# ─ METATRADER 5 ──────────────────────────────────
MT5_ENABLED=false             # Cambiar a true en Windows con MT5
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=ICMarketsSC-Demo04

# ─ NOTIFICACIONES (Opcional) ────────────────────
NOTIFICATIONS_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### 2.4 Generar JWT Secret Key

```bash
# Opción 1: Python
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"

# Opción 2: OpenSSL (macOS/Linux)
openssl rand -hex 32

# Copiar el valor a JWT_SECRET_KEY en .env
```

### 2.5 Verificar .env

```bash
# Verificar que no hay errores de sintaxis
python -c "from dotenv import load_dotenv; load_dotenv('.env'); print('✅ .env loaded successfully')"
```

---

## Fase 3: PostgreSQL Setup

### 3.1 Opción A: Docker (Recomendado)

```bash
# Crear red Docker
docker network create trader_network 2>/dev/null || true

# Ejecutar PostgreSQL
docker run -d \
  --name trader-postgres \
  --network trader_network \
  -e POSTGRES_USER=trader \
  -e POSTGRES_PASSWORD=contraseña \
  -e POSTGRES_DB=trader_ai \
  -p 5432:5432 \
  -v trader_postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Esperar a que inicie
sleep 5

# Verificar
docker ps | grep postgres
```

### 3.2 Opción B: Local (macOS/Linux)

```bash
# macOS (con Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Linux (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 3.3 Opción C: Local (Windows)

1. Descargar: https://www.postgresql.org/download/windows/
2. Ejecutar instalador
3. Recordar contraseña de `postgres`
4. Seleccionar puerto 5432
5. Instalar pgAdmin (opcional)

### 3.4 Crear Database y Usuario

```bash
# Conectarse (requiere contraseña)
psql -U postgres -h localhost

# Dentro de psql:
CREATE USER trader WITH PASSWORD 'contraseña';
CREATE DATABASE trader_ai OWNER trader;
GRANT ALL PRIVILEGES ON DATABASE trader_ai TO trader;

# Verificar
\du
\l

# Salir
\q
```

### 3.5 Ejecutar Migraciones

```bash
# Desde la carpeta raíz del proyecto
alembic upgrade head

# O si está en el código:
python -m core.database.migrate
```

---

## Fase 4: Redis Setup

### 4.1 Opción A: Docker

```bash
# Ejecutar Redis
docker run -d \
  --name trader-redis \
  --network trader_network \
  -p 6379:6379 \
  redis:7-alpine

# Verificar
docker exec trader-redis redis-cli ping
```

### 4.2 Opción B: Local (macOS)

```bash
brew install redis
brew services start redis

# Verificar
redis-cli ping
```

### 4.3 Opción C: Local (Linux)

```bash
sudo apt-get install -y redis-server
sudo systemctl start redis-server
redis-cli ping
```

### 4.4 Opción D: Local (Windows)

1. Opción 1: Usar WSL2 + Linux instructions
2. Opción 2: https://github.com/microsoftarchive/redis/releases
3. Opción 3: Docker (recomendado)

---

## Fase 5: Interactive Brokers (IB)

### 5.1 Crear Cuenta

1. Ir a https://www.interactivebrokers.com/
2. Crear cuenta (demo/paper o live)
3. Completar KYC si es needed
4. Obtener Account ID (ej: P123456789 para paper, U para live)

### 5.2 Instalar TWS o IB Gateway

#### Opción A: IB Gateway (Ligero)

1. Descargar: https://www.interactivebrokers.com/en/index.php?f=16044
2. Instalar
3. Seleccionar: `Live Trading` o `Paper Trading`
4. Ingresar credentials

#### Opción B: Trader Workstation (Completo)

1. Descargar: https://www.interactivebrokers.com/en/index.php?f=14099
2. Instalar
3. Iniciar
4. Settings → API → Enable Socket Client

### 5.3 Configurar API

**En TWS/IB Gateway:**

1. File → Global Configuration
2. API → Settings
3. Habilitar: "Enable ActiveX and Socket Clients"
4. Puerto: 7498 (paper) o 7497 (live)
5. Permitir: Acceso local (127.0.0.1)

### 5.4 Probar Conexión

```bash
python -c "
from ib_insync import IB, Stock

ib = IB()
ib.connect('127.0.0.1', 7498, clientId=1)
print('✅ Connected to IB' if ib.isConnected() else '❌ Failed')
ib.disconnect()
"
```

### 5.5 Actualizar .env

```env
IB_ENABLED=true
IB_HOST=127.0.0.1
IB_PORT=7498              # Cambiar a 7497 si es live
IB_CLIENT_ID=1
IB_ACCOUNT_ID=P123456789  # Tu account ID
```

---

## Fase 6: MetaTrader 5 (MT5)

⚠️ **Nota**: MT5 solo funciona en Windows. Salta esta fase si usas macOS/Linux.

### 6.1 Instalar MT5

1. Descargar desde broker (ej: IC Markets, Pepperstone, etc.)
2. Ejecutar instalador
3. Crear/importar cuenta (demo recomendado)
4. Hacer login

### 6.2 Habilitar Python Integration

**En MT5:**

1. Tools → Options → Expert Advisors
2. Habilitar: "Allow algorithmictrading"
3. Habilitar: "Allow DLL imports"

### 6.3 Probar Conexión

```bash
# Windows PowerShell
python -c "
import MetaTrader5 as mt5

if mt5.initialize():
    print('✅ MT5 connected')
    mt5.shutdown()
else:
    print('❌ MT5 failed to connect')
"
```

### 6.4 Actualizar .env

```env
MT5_ENABLED=true
MT5_LOGIN=12345678        # Tu login MT5
MT5_PASSWORD=password     # Tu password
MT5_SERVER=ICMarketsSC-Demo04  # Nombre del servidor (copy/paste de MT5)
```

---

## Fase 7: Docker Compose

### 7.1 Verificar Docker

```bash
docker --version
docker-compose --version

# Ambos deben mostrar versión
```

### 7.2 Ver archivo docker-compose.yml

```bash
cat docker/docker-compose.yml  # macOS/Linux
type docker\docker-compose.yml # Windows
```

### 7.3 Iniciar Stack

```bash
cd docker
docker-compose up -d

# Esperar ~10 segundos
sleep 10

# Verificar
docker-compose ps
```

**Servicios levantados:**
- PostgreSQL (puerto 5432)
- Redis (puerto 6379)
- Prometheus (puerto 9090)
- Grafana (puerto 3000)

### 7.4 Acceder a Servicios

```bash
# PostgreSQL
psql -U trader -h localhost -d trader_ai

# Redis
redis-cli -h localhost -p 6379

# Grafana
# Browser: http://localhost:3000
# Usuario: admin, Contraseña: admin

# Prometheus
# Browser: http://localhost:9090
```

---

## Fase 8: Descargar Datos Históricos

### 8.1 Descargar Crypto (Binance)

```bash
# Bitcoin
python scripts/download_data.py --symbol BTCUSDT --timeframe 1h --years 2

# Ethereum
python scripts/download_data.py --symbol ETHUSDT --timeframe 1h --years 2

# Múltiples
for symbol in BTCUSDT ETHUSDT BNBUSDT; do
  python scripts/download_data.py --symbol $symbol --timeframe 1h --years 1
done
```

### 8.2 Descargar Forex (Interactive Brokers)

```bash
# Primero: Verificar que TWS/IB Gateway está corriendo

# EUR/USD
python scripts/download_data.py --symbol EURUSD --timeframe 1h --years 2 --provider ib

# GBP/USD
python scripts/download_data.py --symbol GBPUSD --timeframe 1h --years 2 --provider ib

# Índices
python scripts/download_data.py --symbol SPX500 --timeframe 1h --years 1 --provider ib
python scripts/download_data.py --symbol NAS100 --timeframe 1h --years 1 --provider ib

# Commodities
python scripts/download_data.py --symbol XAUUSD --timeframe 1h --years 1 --provider ib  # Gold
```

### 8.3 Descargar Forex (MetaTrader 5 - Windows)

```bash
# Primero: Verificar que MT5 está abierto y logeado

python scripts/download_data.py --symbol EURUSD --timeframe 1h --years 2 --provider mt5
python scripts/download_data.py --symbol GBPUSD --timeframe 1h --years 2 --provider mt5
```

### 8.4 Verificar Datos

```bash
# Ver archivos descargados
ls -la data/raw/  # macOS/Linux
dir data\raw\    # Windows

# Python check
python -c "
import pandas as pd
df = pd.read_parquet('data/raw/BTCUSDT_1h.parquet')
print(f'✅ {len(df)} candles loaded')
print(df.head())
"
```

---

## Fase 9: Entrenar Modelos ML

### 9.1 Entrenar Modelos Binance

```bash
# Bitcoin
python scripts/retrain.py --symbol BTCUSDT --timeframe 1h

# Ethereum
python scripts/retrain.py --symbol ETHUSDT --timeframe 1h
```

### 9.2 Entrenar Modelos Forex

```bash
# EUR/USD
python scripts/retrain.py --symbol EURUSD --timeframe 1h --exchange ib

# SPX500 (S&P 500)
python scripts/retrain.py --symbol SPX500 --timeframe 1h --exchange ib
```

### 9.3 Monitorear Entrenamiento

```bash
# Ver logs en tiempo real
tail -f logs/training.log          # macOS/Linux
Get-Content logs\training.log -Tail 20 -Wait  # Windows
```

### 9.4 Modelos Disponibles

```bash
# Listar modelos entrenados
ls -la data/models/  # macOS/Linux
dir data\models\    # Windows

# Ejemplo de salida:
# BTCUSDT_1h_model.joblib
# EURUSD_1h_model.joblib
# SPX500_1h_model.joblib
```

---

## Fase 10: Iniciar Aplicación

### 10.1 Verificar Setup

```bash
python scripts/validate_setup.py

# Debe mostrar:
# ✅ Python version 3.10.x
# ✅ .env loaded
# ✅ Project structure OK
# ✅ Dependencies installed
# ✅ PostgreSQL connected
# ✅ Redis connected
# ✅ ... etc
```

### 10.2 Iniciar API (Terminal 1)

```bash
# Asegurar que venv está activado
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\Activate  # Windows

# Iniciar
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Debe mostrar:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### 10.3 Iniciar Streamlit (Terminal 2)

```bash
# Activar venv
source venv/bin/activate

# Iniciar
streamlit run app/main.py

# Debe mostrar:
# You can now view your Streamlit app in your browser.
# URL: http://localhost:8501
```

### 10.4 Acceder a Aplicación

```
API:        http://localhost:8000
Swagger:    http://localhost:8000/docs
Streamlit:  http://localhost:8501
Redis:      localhost:6379
PostgreSQL: localhost:5432
```

---

## Fase 11: Validación y Testing

### 11.1 API Health Check

```bash
# Verificar que API está vivo
curl http://localhost:8000/health

# Respuesta esperada:
# {"status": "ok", "timestamp": "2026-03-30T..."}
```

### 11.2 API Documentation

```
Visita en navegador:
http://localhost:8000/docs

Aquí puedes probar todos los endpoints interactivamente
```

### 11.3 Verificar Datos

```bash
# En Python
python -c "
import asyncio
from core.ingestion.providers.binance_client import BinanceClient

async def test():
    client = BinanceClient()
    await client.connect()
    data = await client.get_klines('BTCUSDT', '1h', limit=10)
    print(f'✅ {len(data)} candles from Binance')
    await client.disconnect()

asyncio.run(test())
"
```

### 11.4 Testing Multiactivos

```bash
# Ver ejemplos
python scripts/examples_multiactivos.py

# Ejecutar ejemplo específico:
python -c "
import asyncio
from scripts.examples_multiactivos import example_1_ib_basic
asyncio.run(example_1_ib_basic())
"
```

---

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'core'"

**Solución:**
```bash
# Verificar que estás en la carpeta raíz
pwd          # macOS/Linux
cd           # Windows

# Verificar venv está activado
which python # Debe mostrar ruta con 'venv'

# Reinstalar
pip install -e .
```

### Error: "PostgreSQL connection refused"

**Solución:**
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres  # Si uses Docker

# O si es local
sudo systemctl status postgresql  # Linux

# Verificar credenciales en .env
# DATABASE_URL debe ser correcta

# Probar conexión
psql -U trader -h localhost -d trader_ai -c "SELECT 1"
```

### Error: "Redis connection refused"

**Solución:**
```bash
# Verificar Redis
docker ps | grep redis  # Docker
redis-cli ping          # Local

# Reiniciar
docker-compose restart redis
```

### Error: "IB connection failed"

**Solución:**
```bash
# Verificar TWS/IB Gateway está corriendo
# Puerto 7498 (paper) debe estar abierto

netstat -an | grep 7498  # macOS/Linux
netstat -an | find "7498"  # Windows

# Si no funciona:
# 1. Cierra y reabre TWS/IB Gateway
# 2. Verifica Settings → API → Enable Socket Client
# 3. Intenta desde otro clientId: IB_CLIENT_ID=2
```

### Error: "MT5 Python integration failed" (Windows)

**Solución:**
```bash
# MT5 podría no estar en PATH
# Opción 1: Abrir MT5 primero (importante!)
# Opción 2: Reinstalar con MT5 installed

pip uninstall MetaTrader5
pip install MetaTrader5==5.0.5640 --force-reinstall
```

### Aplicación lenta / Alto uso de memoria

**Solución:**
```bash
# Verificar procesos
ps aux | grep python  # macOS/Linux
Get-Process python    # Windows

# Limpiar caché
rm -rf __pycache__  # macOS/Linux
dir __pycache__ /s /b | del  # Windows

# Reiniciar servicios
docker-compose restart
```

---

## Checklist Completo

- [ ] **Fase 0**: Ambiente preparado, repo clonado
- [ ] **Fase 1**: Todas las dependencias instaladas (`pip list | grep ...`)
- [ ] **Fase 2**: .env creado y configurado
- [ ] **Fase 3**: PostgreSQL corriendo, BD `trader_ai` creada
- [ ] **Fase 4**: Redis corriendo, `redis-cli ping` → PONG
- [ ] **Fase 5**: IB configurado (solo si usas IB)
  - [ ] TWS/IB Gateway corriendo
  - [ ] API habilitada
  - [ ] Conexión prueba exitosa
- [ ] **Fase 6**: MT5 configurado (solo si usas MT5 + Windows)
  - [ ] MT5 instalado
  - [ ] Login exitoso
  - [ ] Python integration OK
- [ ] **Fase 7**: Docker stack corriendo
  - [ ] `docker-compose ps` muestra 4+ servicios
- [ ] **Fase 8**: Datos descargados
  - [ ] `data/raw/*.parquet` existen
  - [ ] Archivos tienen contenido
- [ ] **Fase 9**: Modelos entrenados
  - [ ] `data/models/*.joblib` existen
  - [ ] `retrain.py` completo sin errores
- [ ] **Fase 10**: Aplicación corriendo
  - [ ] API en http://localhost:8000
  - [ ] Streamlit en http://localhost:8501
  - [ ] Ambas terminales sin errores
- [ ] **Fase 11**: Validación completa
  - [ ] `validate_setup.py` pasa todos los checks
  - [ ] `/health` endpoint responde
  - [ ] Datos se cargan correctamente

---

**Próximo paso:** Ir a [DEPLOYMENT.md](./DEPLOYMENT.md) para desplegar en producción, o comienza a operar con [examples_multiactivos.py](./scripts/examples_multiactivos.py)

¡Felicidades! 🎉 Trading IA está listo para multiactivos.
