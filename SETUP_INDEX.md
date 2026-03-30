# 📚 Guía de Instalación y Configuración - Trading IA

**Última actualización**: 2026-03-30
**Estado**: Completo para Multiactivos (IB + MT5)

---

## 🗂️ Índice de Documentación

### Inicio Rápido
- **Crypto only (Binance)** → Directo a [SETUP_MANUAL.md](./SETUP_MANUAL.md) Fase 0-4
- **Multiactivos + IB** → [SETUP_MANUAL.md](./SETUP_MANUAL.md) Fases 0-7 + IB (Fase 5)
- **Multiactivos + MT5** → [SETUP_MANUAL.md](./SETUP_MANUAL.md) Fases 0-7 + MT5 (Fase 6)
- **Todo integrado** → Seguir [SETUP_MANUAL.md](./SETUP_MANUAL.md) Fases 0-11

### Documentación Principal

#### [📖 SETUP_MANUAL.md](./SETUP_MANUAL.md)
Guía paso-a-paso de 12 fases para configurar el proyecto completo.
- **Tiempo estimado**: 45-90 minutos
- **Cobertura**: Ambiente local, dependencias, bases de datos, brokers, Docker
- **Mejor para**: Configuración desde cero

| Fase | Título | Tiempo | Requisitos |
|------|--------|--------|------------|
| 0 | Preparar ambiente | 5 min | PC + internet |
| 1 | Instalar dependencias | 10 min | Python 3.10+ |
| 2 | Configurar .env | 5 min | Editor de texto |
| 3 | PostgreSQL setup | 10 min | Docker o local |
| 4 | Redis setup | 5 min | Docker o local |
| 5 | Interactive Brokers | 15 min | Cuenta IB |
| 6 | MetaTrader 5 | 10 min | Windows + MT5 |
| 7 | Docker Compose | 10 min | Docker instalado |
| 8 | Descargar datos | 30 min | Red estable |
| 9 | Entrenar modelos | 60+ min | GPU recomendada |
| 10 | Iniciar app | 5 min | Servicios corriendo |
| 11 | Validar | 10 min | - |

#### [🎯 MULTIACTIVOS_CHECKLIST.md](./MULTIACTIVOS_CHECKLIST.md)
Resumen de capabilidades de multiactivos implementadas.
- **Tiempo estimado**: 5 minutos lectura
- **Mejor para**: Entender qué se puede hacer con cada broker

#### [🔗 docs/INTEGRACION_MULTIACTIVOS.md](./docs/INTEGRACION_MULTIACTIVOS.md)
Guía técnica de integración entre plataformas.
- **Tiempo estimado**: 20 minutos lectura
- **Mejor para**: Desarrolladores que quieren extender las integraciones

#### [🚀 DEPLOYMENT.md](./DEPLOYMENT.md)
Guía completa de despliegue en producción.
- **Tiempo estimado**: 60-120 minutos
- **Cobertura**: VPS (Hetzner), Cloud (Railway, AWS), Docker, Seguridad
- **Mejor para**: Llevar a producción

---

## 🎯 Rutas Recomendadas por Caso de Uso

### 1️⃣ Solo Crypto (Binance)
```
SETUP_MANUAL.md (Fases 0-4)
  ↓
scripts/download_data.py --symbol BTCUSDT
  ↓
scripts/retrain.py --symbol BTCUSDT
  ↓
Iniciar en local: uvicorn + streamlit
```
**Tiempo total**: ~30 minutos

### 2️⃣ Multiactivos con Interactive Brokers
```
SETUP_MANUAL.md (Fases 0-7, especialmente Fase 5)
  ↓
Verificar conexión: python scripts/validate_setup.py
  ↓
Descargar datos multiactivos
  ↓
Entrenar modelos para EURUSD, SPX500, XAUUSD, etc.
  ↓
Deployar en VPS (DEPLOYMENT.md)
```
**Tiempo total**: ~90 minutos + deploy

### 3️⃣ Multiactivos con MetaTrader 5 (Windows)
```
SETUP_MANUAL.md (Fases 0-7, especialmente Fase 6)
  ↓
Instalar MT5 + abrir cuenta demo
  ↓
Descargar datos via MT5
  ↓
Entrenar y operar
```
**Tiempo total**: ~60 minutos

### 4️⃣ Setup Completo (Crypto + IB + MT5)
```
SETUP_MANUAL.md (Fases 0-11 completas)
  ↓
DEPLOYMENT.md (VPS o Cloud)
  ↓
Monitoreo con Prometheus/Grafana
```
**Tiempo total**: ~120 minutos + deploy

---

## ✅ Checklist Pre-Setup

- [ ] Python 3.10 o superior instalado
- [ ] Git configurado
- [ ] Editor de código (VS Code, PyCharm, etc.)
- [ ] Docker instalado (opcional pero recomendado)
- [ ] Conexión estable a internet
- [ ] Terminal/PowerShell accesible

### Para IB (Interactive Brokers)
- [ ] Cuenta IB abierta (demo o real)
- [ ] TWS o IB Gateway instalado en tu máquina
- [ ] API habilitada en Settings

### Para MT5 (MetaTrader 5)
- [ ] Windows (MT5 no está disponible en macOS/Linux)
- [ ] MetaTrader 5 instalado
- [ ] Cuenta MT5 abierta (demo o real)

---

## 📋 Estructura del Proyecto

```
Trading_IA/
├── api/                           # FastAPI backend
│   ├── main.py                   # Punto de entrada
│   ├── routes/                   # Endpoints
│   └── models/                   # Schemas
├── app/                           # Streamlit frontend
│   ├── main.py                   # Dashboard
│   └── pages/                    # Subpáginas
├── core/                          # Lógica central
│   ├── models/                   # Modelos de datos
│   ├── ingestion/
│   │   ├── exchange_adapter.py   # Interfaz multi-exchange
│   │   └── providers/
│   │       ├── binance_client.py
│   │       ├── ib_client.py      # ✨ Nuevo
│   │       ├── mt5_client.py     # ✨ Nuevo
│   │       └── ...
│   ├── trading/                  # Lógica de trading
│   └── observability/            # Logging, métricas
├── scripts/                       # Utilidades
│   ├── download_data.py          # Descargar OHLCV
│   ├── retrain.py                # Entrenar modelos
│   ├── validate_setup.py         # ✨ Validar setup
│   └── examples_multiactivos.py  # ✨ Ejemplos
├── docker/                        # Configuraciones Docker
│   └── docker-compose.yml
├── SETUP_INDEX.md                # Este archivo
├── SETUP_MANUAL.md               # Guía detallada
├── MULTIACTIVOS_CHECKLIST.md    # Resumen de capacidades
├── DEPLOYMENT.md                 # Guía de despliegue
└── requirements*.txt             # Dependencias
```

---

## 🚀 Comando Rápido (Setup Mínimo)

```bash
# 1. Clonar
git clone https://github.com/Ximena5745/Trading_IA.git
cd Trading_IA

# 2. Ambiente
python -m venv venv
source venv/bin/activate  # macOS/Linux
# O en Windows:
venv\Scripts\activate

# 3. Dependencias
pip install -r requirements.txt -r requirements-multiactivos.txt

# 4. Configurar
cp .env.example .env
nano .env  # Editar con tus valores

# 5. Servicios (Docker)
docker-compose -f docker/docker-compose.yml up -d

# 6. Validar
python scripts/validate_setup.py

# 7. Iniciar (dos terminales)
# Terminal 1:
uvicorn api.main:app --reload

# Terminal 2:
streamlit run app/main.py
```

---

## 🔗 Links Importantes

- **GitHub**: https://github.com/Ximena5745/Trading_IA
- **Interactive Brokers**: https://www.interactivebrokers.com/
- **MetaTrader 5**: https://www.metatrader5.com/
- **Binance**: https://www.binance.com/
- **Docker**: https://docs.docker.com/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Streamlit**: https://docs.streamlit.io/

---

## 🆘 Soporte y Troubleshooting

Si encuentras problemas:

1. **Revisa logs**: `cat logs/*.log` (o `type logs\*.log` en Windows)
2. **Ejecuta validación**: `python scripts/validate_setup.py`
3. **Consulta ejemplos**: `python scripts/examples_multiactivos.py`
4. **Revisa documentación específica**:
   - Errores Python → SETUP_MANUAL.md (Troubleshooting)
   - Errores de conexión IB → INTEGRACION_MULTIACTIVOS.md
   - Errores de despliegue → DEPLOYMENT.md

---

**¿Listo para comenzar?** → Ve a [SETUP_MANUAL.md](./SETUP_MANUAL.md) 🎯
