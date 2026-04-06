# 🎨 TRADER·IA Dashboard - Design System Completo

## 📁 Archivos Creados/Modificados

### 1. **static/css/styles.css** (Nuevo)
Design system completo con:
- ✅ CSS Variables (tokens) para colores, espacios, tipografía
- ✅ Diseño responsivo con grid layouts
- ✅ Componentes base: cards, badges, buttons, tables
- ✅ Estados y animaciones
- ✅ Temas claros y accesibles
- ✅ ~800 líneas de CSS bien organizado

**Características principales:**
```css
:root {
  /* Colores semánticos */
  --green, --red, --blue, --amber, --purple
  
  /* Espacios */
  --space-1 a --space-9 (2px a 32px)
  
  /* Tipografía */
  --mono (JetBrains Mono)
  --sans (Syne)
  
  /* Transiciones y Z-index */
  --transition-fast, --transition-smooth
  --z-dropdown, --z-sticky, --z-modal
}
```

### 2. **static/js/components.js** (Nuevo)
Librería de componentes reutilizables con:
- ✅ **APIClient**: Cliente HTTP para FastAPI
- ✅ **BadgeComponent**: Estados y señales
- ✅ **MetricCardComponent**: Tarjetas con métricas
- ✅ **AgentRowComponent**: Filas de agentes IA
- ✅ **TableComponent**: Tablas dinámicas
- ✅ **ChartHelper**: Utilidades para Plotly
- ✅ **PositionRowComponent**: Posiciones abiertas
- ✅ **ShapComponent**: Valores SHAP/XAI
- ✅ **ModalComponent**: Diálogos
- ✅ **LoadingComponent**: Estados de carga
- ✅ **ToastComponent**: Notificaciones
- ✅ **Utils**: Funciones de utilidad

### 3. **static/dashboard.html** (Mejorado)
Dashboard actualizado:
- ✅ Enlaza `styles.css` de forma externa
- ✅ Enlaza `components.js` para reutilización
- ✅ Inicializa `APIClient` automáticamente
- ✅ Mantiene toda la funcionalidad anterior
- ✅ CSS limpio y organizado

### 4. **static/js/USAGE.md** (Nuevo)
Documentación completa con:
- ✅ Guía de APIClient y endpoints
- ✅ Ejemplos de cada componente
- ✅ Patrones de uso
- ✅ Integración con FastAPI

### 5. **static/js/integration-examples.js** (Nuevo)
7 ejemplos prácticos listos para copiar/pegar:
1. Cargar y mostrar señales
2. Mostrar métricas de portfolio
3. Cargar agentes IA
4. Mostrar posiciones abiertas
5. Mostrar métricas de riesgo
6. Modal de confirmación de orden
7. Debounce para búsqueda

---

## 🚀 Cómo Usar

### Instalación Rápida

```html
<!-- Incluir en <head> -->
<link rel="stylesheet" href="/css/styles.css">
<script src="/js/components.js"></script>

<!-- en <body> al final -->
<script>
  const api = new APIClient('');
  
  // Usar componentes
  const badge = BadgeComponent.create('BUY', 'buy');
  document.body.appendChild(badge);
</script>
```

### Ejemplo Básico

```javascript
// 1. Obtener datos del API
const signals = await api.signals.getSignalsBatch(['EURUSD', 'XAUUSD']);

// 2. Crear componente
const badge = BadgeComponent.create(signals[0].action, 'buy');

// 3. Mostrar
document.getElementById('container').appendChild(badge);

// 4. Notificar usuario
ToastComponent.show({
  message: 'Señal cargada',
  type: 'success'
});
```

---

## 📊 Estructura de Tokens CSS

### Colores
```css
--bg0, --bg1, --bg2, --bg3, --bg4  /* Backgrounds */
--text1, --text2, --text3           /* Textos */
--green, --red, --blue, --amber     /* Semánticos */
```

### Espacios
```css
--space-1: 2px;    --space-2: 4px;    --space-3: 6px;
--space-4: 8px;    --space-5: 12px;   --space-6: 16px;
--space-7: 20px;   --space-8: 24px;   --space-9: 32px;
```

### Tipografía
```css
--mono: 'JetBrains Mono', monospace
--sans: 'Syne', sans-serif
--font-weight-regular: 400;
--font-weight-semibold: 600;
```

---

## 🎯 Componentes Disponibles

### APIClient
```javascript
const api = new APIClient('');

// Market
api.market.getMarketData(symbol, timeframe)
api.market.getFeaturesCache()

// Signals
api.signals.getSignals(symbol)
api.signals.getConsensus(symbol)

// Portfolio
api.portfolio.getPortfolio()
api.portfolio.getPositions()

// Risk
api.risk.getRiskMetrics()
api.risk.getKillSwitchStatus()

// Execution
api.execution.getOrders()
api.execution.placeOrder(orderData)
```

### UI Components
```javascript
// Badges
BadgeComponent.create('BUY', 'buy')

// Tarjetas
MetricCardComponent.create({ 
  label: 'Equity',
  value: '$10,500',
  bar: { percent: 85, color: 'var(--green)' }
})

// Agentes
AgentRowComponent.create({ 
  name: 'TechnicalAgent', 
  score: 0.75 
})

// Tablas
TableComponent.create({
  headers: ['Symbol', 'Signal'],
  rows: [{ symbol: 'EURUSD', signal: '...' }]
})

// Modales
ModalComponent.create({
  title: 'Confirmar',
  content: 'HTML content'
})

// Notificaciones
ToastComponent.show({
  message: 'Orden ejecutada',
  type: 'success'
})
```

---

## 🔗 Integración con FastAPI

Los endpoints esperados por `APIClient`:

```python
# Market
GET  /api/market/{symbol}/{timeframe}
POST /api/market/batch/{timeframe}
GET  /api/market/features
GET  /api/market/regime

# Signals
GET  /api/signals/{symbol}
POST /api/signals/batch
GET  /api/signals/{symbol}/consensus

# Portfolio
GET  /api/portfolio
GET  /api/portfolio/positions
GET  /api/portfolio/equity-curve
GET  /api/portfolio/metrics

# Risk
GET  /api/risk/metrics
GET  /api/risk/kill-switch
GET  /api/risk/limits
GET  /api/risk/exposure

# Execution
GET  /api/execution/orders
POST /api/execution/orders
GET  /api/execution/orders/{order_id}
DELETE /api/execution/orders/{order_id}
```

---

## 📈 Ventajas del Design System

✅ **Reutilización**: 15+ componentes listos para usar
✅ **Consistencia**: Tokens CSS unificados
✅ **Responsividad**: Mobile-first, grid fluido
✅ **Accesibilidad**: Contraste de colores, navegación clara
✅ **Mantenibilidad**: CSS modular, sin estilos inline
✅ **Performance**: Animaciones optimizadas
✅ **Documentación**: Ejemplos listos para copiar/pegar

---

## 📚 Ejemplos de Uso

Ver `static/js/integration-examples.js` para 7 ejemplos completos:

1. **loadSignalsWithComponents()** - Cargar y render de señales
2. **loadPortfolioMetricsWithComponents()** - Métricas de portfolio
3. **loadAgentsWithComponents()** - Agentes IA
4. **loadPositionsWithComponents()** - Posiciones abiertas
5. **loadRiskMetricsWithComponents()** - Métricas de riesgo
6. **showOrderConfirmationModal()** - Modal de orden
7. **searchSymbols** - Debounce búsqueda

---

## 🎓 Próximos Pasos

1. **Migrar funciones render* existentes** a componentes
2. **Validación de formularios** en modales
3. **Estado global** con localStorage
4. **Offline support** con Service Workers
5. **Temas personalizados** (light/dark mode)
6. **Internacionalización** (i18n)

---

## 📞 Soporte

- Documentación: `static/js/USAGE.md`
- Ejemplos: `static/js/integration-examples.js`
- Estilos: `static/css/styles.css`
- Componentes: `static/js/components.js`

---

## ✨ Resumen

Se ha creado un **design system profesional y completo** que:

- Elimina estilos inline del HTML
- Proporciona 15+ componentes reutilizables
- Conecta automáticamente con FastAPI
- Incluye 7 ejemplos prácticos de integración
- Define tokens CSS para toda la aplicación
- Mantiene compatibilidad con código existente

**Listo para extender y mejorar el dashboard** 🚀
