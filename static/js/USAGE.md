# TRADER·IA Dashboard Components - Guía de Uso

## Overview

El sistema de componentes reutilizables proporciona:
- **APIClient**: Cliente para interactuar con endpoints FastAPI
- **Componentes UI**: Tarjetas, badges, tablas, gráficos, etc.
- **Utilidades**: Formatos, colores, animaciones

## APIClient

El cliente API maneja todas las peticiones al backend FastAPI.

### Uso Básico

```javascript
// Ya inicializado en dashboard.html
const api = new APIClient('');  // URL vacía = mismo dominio

// Realizar peticiones
const data = await api.market.getMarketData('EURUSD', '1wk');
```

### Endpoints Disponibles

#### Market
```javascript
// Obtener datos de mercado
api.market.getMarketData(symbol, timeframe)
api.market.getMarketDataBatch(symbols, timeframe)
api.market.getFeaturesCache()
api.market.getRegimeCache()
```

#### Signals
```javascript
// Obtener señales
api.signals.getSignals(symbol)
api.signals.getSignalsBatch(symbols)
api.signals.getConsensus(symbol)
```

#### Portfolio
```javascript
// Información de portfolio
api.portfolio.getPortfolio()
api.portfolio.getPositions()
api.portfolio.getEquityCurve()
api.portfolio.getMetrics()
```

#### Risk
```javascript
// Métricas de riesgo
api.risk.getRiskMetrics()
api.risk.getKillSwitchStatus()
api.risk.getLimits()
api.risk.getExposure()
```

#### Execution
```javascript
// Gestión de órdenes
api.execution.getOrders()
api.execution.getOrder(orderId)
api.execution.placeOrder(orderData)
api.execution.cancelOrder(orderId)
```

## Componentes UI

### BadgeComponent

Crear badges para estados y señales.

```javascript
// Estado simple
const badge = BadgeComponent.create('BUY', 'buy');

// Badges de señal
const signalBadges = BadgeComponent.createSignalBadges('buy');

// Uso en HTML
element.appendChild(badge);
```

Tipos disponibles: `buy`, `sell`, `hold`, `fill`, `reject`, `skip`, `pending`, `executed`, `ok`, `watch`, `danger`, `clear`, `blocked`, `warning`, `info`

### MetricCardComponent

Crear tarjetas de métrica con valores y barras de progreso.

```javascript
// Tarjeta simple
const card = MetricCardComponent.create({
  label: 'Equity Total',
  value: '$10,500.00',
  sub: '+1.2%',
  color: 'var(--green)'
});

// Tarjeta con barra de progreso
const card = MetricCardComponent.create({
  label: 'Exposición',
  value: '45%',
  bar: {
    percent: 45,
    color: 'var(--green)'
  }
});

// Grid de múltiples tarjetas
const grid = MetricCardComponent.createGrid([
  { label: 'Metric 1', value: '100' },
  { label: 'Metric 2', value: '200' },
  // ...
]);
```

### AgentRowComponent

Mostrar agentes IA con puntuaciones.

```javascript
// Fila simple
const row = AgentRowComponent.create({
  name: 'TechnicalAgent',
  score: 0.75,
  status: 'bullish'  // bullish, bearish, sideways, neutral
});

// Lista de agentes
const list = AgentRowComponent.createList([
  { name: 'AgentA', score: 0.65, status: 'bullish' },
  { name: 'AgentB', score: -0.20, status: 'bearish' },
  // ...
]);
```

Estados disponibles: `bullish`, `bearish`, `sideways`, `neutral`, `positive`, `negative`

### TableComponent

Crear tablas dinámicas.

```javascript
const table = TableComponent.create({
  headers: ['Símbolo', 'Acción', 'Entrada', 'SL', 'TP', 'R:R'],
  rows: [
    {
      symbol: 'EURUSD',
      action: BadgeComponent.create('BUY', 'buy'),
      entry: '1.0845',
      sl: '1.0790',
      tp: '1.0920',
      rr: '1.4x'
    },
    // ...
  ],
  className: 'signal-table'
});

element.appendChild(table);
```

### ChartHelper

Utilidades para crear gráficos con Plotly.

```javascript
// Layouts
const layout = ChartHelper.formatLayout('EURUSD', '1W · Datos reales');
const config = ChartHelper.formatConfig();

// Traces
const candleTrace = ChartHelper.getCandleTrace(data);
const lineTrace = ChartHelper.getLineTrace(data, 'SMA20', 'var(--blue)');
const barTrace = ChartHelper.getBarTrace(data, 'Volume', 'var(--green)');

// Plotly
Plotly.newPlot('chartId', [candleTrace], layout, config);
```

### PositionRowComponent

Mostrar posiciones abiertas.

```javascript
// Fila de posición
const row = PositionRowComponent.create({
  symbol: 'EURUSD',
  quantity: '1 LOT',
  pnl: 150.50,
  status: 'open'
});

// Lista de posiciones
const list = PositionRowComponent.createList([
  { symbol: 'EURUSD', quantity: '1', pnl: 150 },
  { symbol: 'XAUUSD', quantity: '0.5', pnl: -25 },
  // ...
]);
```

### ShapComponent

Mostrar valores SHAP para explicabilidad.

```javascript
// Barra SHAP
const bar = ShapComponent.createBar({
  label: 'EMA Cross',
  positive: 0.25,
  negative: 0,
  value: 0.250
});

// Resumen
const summary = ShapComponent.createSummary(
  'Cruce alcista de EMAs con MACD positivo'
);
```

### ModalComponent

Diálogos modales.

```javascript
const modal = ModalComponent.create({
  title: 'Confirmar Orden',
  content: 'html string o element',
  onClose: () => console.log('Modal cerrado')
});

// Mostrar/ocultar
ModalComponent.show(modal.id);
ModalComponent.hide(modal.id);
```

### LoadingComponent

Estados de carga.

```javascript
// Loading simple
const loading = LoadingComponent.create();

// Skeleton placeholders
const skeleton = LoadingComponent.createSkeleton(3);  // 3 líneas
```

### ToastComponent

Notificaciones emergentes.

```javascript
ToastComponent.show({
  message: 'Orden ejecutada',
  type: 'success',    // success, error, warning, info
  duration: 3000
});
```

## Utilidades

### Utils functions

```javascript
// Formato
Utils.formatCurrency(1000.50)      // "$1,000.50"
Utils.formatPercent(0.52)           // "52.00%"
Utils.formatNumber(3.14159, 2)      // "3.14"

// Colores
Utils.getStatusColor('up')          // "var(--green)"

// Funciones utilitarias
const debouncedFn = Utils.debounce(fn, 300);
const throttledFn = Utils.throttle(fn, 100);
const promise = Utils.delay(1000);
```

## Tokens CSS

Todos los valores están definidos como CSS variables en `variables.css`:

### Colores
- `--bg0, --bg1, --bg2, --bg3, --bg4`: Backgrounds
- `--text1, --text2, --text3`: Textos
- `--green, --red, --blue, --amber, --purple`: Semánticos

### Spacing
- `--space-1` a `--space-9`: 2px a 32px

### Typography
- `--mono`: JetBrains Mono
- `--sans`: Syne

## Ejemplo Completo

```javascript
// 1. Obtener datos
const signal = await api.signals.getSignals('EURUSD');

// 2. Crear componentes
const badgeEl = BadgeComponent.create(signal.action, signal.action.toLowerCase());
const cardEl = MetricCardComponent.create({
  label: 'Consenso',
  value: (signal.consensus * 100).toFixed(1) + '%',
  bar: {
    percent: signal.consensus * 100,
    color: signal.consensus > 0 ? 'var(--green)' : 'var(--red)'
  }
});

// 3. Mostrar
document.getElementById('container').appendChild(badgeEl);
document.getElementById('container').appendChild(cardEl);

// 4. Notificar usuario
ToastComponent.show({
  message: `Señal ${signal.action} para ${signal.symbol}`,
  type: 'info'
});
```

## Integración con FastAPI

El cliente ya maneja:
- Content-Type: application/json
- Errores HTTP con mensajes claros
- Respuestas JSON automáticamente

Los endpoints deben retornar JSON:

```python
@app.get("/api/signals/{symbol}")
async def get_signals(symbol: str):
    return {
        "symbol": symbol,
        "action": "BUY",
        "consensus": 0.65,
        # ...
    }
```

## Performance Tips

1. **Debounce** en búsquedas: `Utils.debounce(search, 300)`
2. **Throttle** en scroll: `Utils.throttle(trackPosition, 100)`
3. **Lazy load** componentes no visibles
4. **Cache** datos de API con TTL
5. **Virtualizar** listas largas

## Próximos Pasos

1. Migrar funciones render* a componentes
2. Añadir validación de formularios
3. Implementar estado global con localStorage
4. Añadir offline support
5. Mejorar animations con CSS
