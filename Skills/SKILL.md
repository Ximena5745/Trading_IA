---
name: trader-ia-dashboard
description: |
  Skill para construir, mejorar o regenerar el frontend del dashboard TRADER IA.
  Aplica el sistema de diseño completo — dark mode profesional estilo Bloomberg/TradingView —
  en cualquier stack (Streamlit, React, Next.js, Vue, HTML/CSS/JS puro).

  USAR ESTE SKILL SIEMPRE QUE el usuario mencione:
  - Mejorar, rediseñar o reforzar el dashboard / frontend de TRADER IA
  - Implementar cualquiera de las 4 páginas: Market View, Signals, Portfolio, Risk Monitor
  - Agregar gráficas (candlestick, equity curve, SHAP, MACD, RSI, Bollinger)
  - Construir componentes de UI: ticker bar, metric cards, signal table, kill switch, agentes IA
  - Migrar o portar el diseño a un stack diferente
  - Aplicar el sistema de colores, tipografía o tokens de diseño del proyecto

  No preguntar por el stack — leer el contexto. Si no está claro, preguntar UNA sola vez.
---

# TRADER IA — Dashboard Design System & Implementation Skill

Sistema de diseño completo y guía de implementación del frontend de TRADER IA.
Stack-agnóstico: las especificaciones aplican a cualquier tecnología.

---

## 1. IDENTIDAD VISUAL

### Concepto
Dark mode profesional. Terminal financiero de alta densidad informativa.
Inspiración: Bloomberg Terminal + TradingView + Binance Pro.
**Una pantalla, muchos datos, cero ruido.**

### Tipografía

| Rol | Fuente | Uso |
|-----|--------|-----|
| **Display / UI** | `Syne` (400, 500, 600, 700) | Títulos, nav, labels, secciones |
| **Datos / Monospace** | `JetBrains Mono` (400, 500, 600) | Precios, porcentajes, valores numéricos, badges, código |

```
Google Fonts CDN:
https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@400;500;600;700
```

**Regla:** Todo número financiero → `JetBrains Mono`. Todo texto UI → `Syne`.

---

## 2. DESIGN TOKENS — PALETA COMPLETA

### Variables CSS (copiar tal cual)

```css
:root {
  /* ── Fondos (de más oscuro a más claro) ─────────────────── */
  --bg0:    #0a0d11;   /* fondo raíz / página */
  --bg1:    #0f1318;   /* nav, ticker bar */
  --bg2:    #151a22;   /* cards principales */
  --bg3:    #1c2330;   /* cards secundarias, hover rows */
  --bg4:    #232c3b;   /* elementos interactivos, inputs */

  /* ── Bordes ──────────────────────────────────────────────── */
  --border:  rgba(255,255,255,0.07);   /* borde sutil (cards) */
  --border2: rgba(255,255,255,0.13);   /* borde énfasis (hover) */

  /* ── Texto ───────────────────────────────────────────────── */
  --text1: #e8edf5;   /* texto principal */
  --text2: #8c99b0;   /* texto secundario */
  --text3: #4d5a70;   /* texto terciario / labels */

  /* ── Semánticos ──────────────────────────────────────────── */
  --green:  #00d084;                    /* BUY, profit, OK */
  --green2: rgba(0,208,132,0.12);       /* fondo badge verde */
  --red:    #ff4757;                    /* SELL, loss, danger */
  --red2:   rgba(255,71,87,0.12);       /* fondo badge rojo */
  --blue:   #3d8ef8;                    /* info, TechnicalAgent, links */
  --blue2:  rgba(61,142,248,0.12);      /* fondo badge azul */
  --amber:  #f5a623;                    /* warning, WATCH, RSI neutro */
  --amber2: rgba(245,166,35,0.12);      /* fondo badge ámbar */
  --purple: #a78bfa;                    /* RegimeAgent */

  /* ── Tipografía ──────────────────────────────────────────── */
  --mono: 'JetBrains Mono', monospace;
  --sans: 'Syne', sans-serif;
}
```

### Uso de colores por significado

| Color | Usar para |
|-------|-----------|
| `--green` | BUY, profit, OK, señales positivas, FILL |
| `--red` | SELL, loss, danger, kill switch, REJECT |
| `--blue` | Info, TechnicalAgent, equity curve, links |
| `--amber` | Warning, WATCH, RSI zona neutra, PAPER mode |
| `--purple` | RegimeAgent, consenso |
| `--text3` | Labels, ejes de gráficas, valores secundarios |

---

## 3. ESTRUCTURA DE PÁGINAS

El dashboard tiene **4 páginas** en una navegación horizontal + **ticker bar** global.

```
┌─────────────────────────────────────────────────────────────────┐
│  NAV: TRADER·IA | Market View | Signals | Portfolio | Risk      │
│                                              [● LIVE] [PAPER]   │
├─────────────────────────────────────────────────────────────────┤
│  TICKER: BTC/USDT +2.34% │ ETH/USDT +1.12% │ EUR/USD -0.18%... │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    CONTENIDO DE LA PÁGINA                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES GLOBALES

### 4.1 Navigation Bar

```
Altura: 44px
Fondo: --bg1
Borde inferior: 1px solid --border
Padding horizontal: 16px

Logo "TRADER·IA":
  - Fuente: JetBrains Mono, 13px, weight 600
  - Color: --blue
  - Letter-spacing: 2px
  - Margin-right: 24px

Tabs de navegación:
  - Fuente: Syne, 11px, weight 500, UPPERCASE, letter-spacing: 0.5px
  - Color inactivo: --text3
  - Color hover: --text2
  - Color activo: --text1
  - Indicador activo: border-bottom 2px solid --blue
  - Altura: 44px (ocupa todo el nav)

Zona derecha (flex, gap 12px):
  - Dot pulsante: 6px, color --green, animation pulse 2s infinite
  - Badge modo: "PAPER" → fondo --amber2, color --amber
                "LIVE"  → fondo --green2, color --green
  - Fuente badge: JetBrains Mono, 10px, weight 600, letter-spacing 0.5px
```

### 4.2 Ticker Bar

```
Altura: ~36px
Fondo: --bg1
Borde inferior: 1px solid --border
Padding: 8px 16px
Overflow-x: auto (scroll horizontal sin scrollbar visible)
Scroll automático o estático

Por cada símbolo (gap 24px, flex-shrink: 0):
  SÍMBOLO   → JetBrains Mono, 11px, weight 600, --text2, letter-spacing 0.5px
  PRECIO    → JetBrains Mono, 12px, --text1
  CAMBIO %  → Badge: fondo --green2/--red2, color --green/--red
              JetBrains Mono, 10px, padding 2px 5px, border-radius 3px

Símbolos a mostrar:
  BTC/USDT | ETH/USDT | EUR/USD | GBP/USD | XAU/USD | US500 | USD/JPY
```

### 4.3 Card Base

```css
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
}
```

### 4.4 Metric Card

```
Estructura (padding 14px 16px):
  LABEL   → Syne, 10px, weight 600, --text3, UPPERCASE, letter-spacing 0.8px
  VALOR   → JetBrains Mono, 22px, weight 600, --text1 (o semántico)
  SUB     → JetBrains Mono, 11px, --text3 o semántico
  BARRA   → height 2px, fondo --bg3, fill con color semántico (opcional)

Grilla estándar: 4 columnas (gap 12px)
En móvil colapsar a 2 columnas
```

### 4.5 Badges / Pills

```
Estructura: display inline-block, padding 2px 7px, border-radius 3px
Fuente: JetBrains Mono, 10px, weight 600, letter-spacing 0.5px

Variantes:
  BUY    → fondo --green2, color --green
  SELL   → fondo --red2,   color --red
  FILL   → fondo --green2, color --green
  REJECT → fondo --red2,   color --red
  SKIP   → fondo --amber2, color --amber
  HOLD   → fondo --bg3,    color --text3
  OK     → fondo --green2, color --green
  WATCH  → fondo --amber2, color --amber
  CLEAR  → fondo --green2, color --green  (FundamentalAgent)
```

---

## 5. PÁGINA 1 — MARKET VIEW

### Layout

```
[Selector de símbolo: botones pill]
[Candlestick Chart + Volume]
[RSI mini] [MACD mini] [Bollinger mini]
[Market Regime + Agents]  [Consensus Gauge]
```

### 5.1 Selector de Símbolo

```
Botones: BTCUSDT | ETHUSDT | EURUSD | XAUUSD | US500
Estilo inactivo: border 1px solid --border, fondo transparent, color --text2
Estilo activo:   border 1px solid --blue, fondo --blue2, color --blue
Fuente: JetBrains Mono, 10px, letter-spacing 0.5px
Border-radius: 4px, padding: 4px 10px
```

### 5.2 Candlestick Chart

```
Header del card:
  Izquierda: "[SÍMBOLO]" (JetBrains Mono 15px weight 600 --text1)
             "1H · 250 velas" (JetBrains Mono 12px --text3)
  Derecha:   Precio actual (JetBrains Mono 12px --green/--red)
             Variación con ▲/▼

Gráfica SVG / librería:
  Altura: 200px  |  Velas: 60 (o las disponibles)
  Colores:
    Vela alcista: #00d084 (--green), opacidad body 0.9
    Vela bajista: #ff4757 (--red),   opacidad body 0.85
    Mecha: mismo color, stroke-width 0.8px

  Overlays sobre el candlestick:
    EMA 9  → línea sólida #3d8ef8, stroke 1.5px
    EMA 21 → línea punteada (dash 4,3) #a78bfa, stroke 1.5px

Volume bars (debajo del candlestick, altura 40px):
  Alcista: rgba(0,208,132,0.4)
  Bajista: rgba(255,71,87,0.4)

Alternativas de librería por stack:
  Streamlit  → st.plotly_chart con go.Candlestick
  React/Vue  → lightweight-charts (TradingView), recharts, Chart.js financial
  HTML puro  → SVG manual o Plotly.js CDN
```

### 5.3 Mini-Charts de Indicadores

**Grilla 3 columnas. Cada uno es un card.**

#### RSI (14)
```
Mini line chart: 30 puntos, área bajo la curva
Color línea: --amber, fill rgba(245,166,35,0.08)
Zona sobrecompra (>70): línea punteada roja, zona rellena rojo suave
Zona sobreventa (<30): línea punteada verde, zona rellena verde suave
Footer: "30" | valor actual (JetBrains Mono 13px --amber) | "70"
```

#### MACD
```
Histograma de barras: barras positivas --green 0.7 opacidad,
                      barras negativas --red 0.7 opacidad
Footer: "Line" | valor actual (--green/--red) | "Hist"
```

#### Bollinger Bands
```
3 líneas: Upper (--red 0.5 opacidad), Middle (--text1 0.6), Lower (--green 0.5)
Footer: "Low [precio]" | "Up [precio]" (JetBrains Mono 9px --text3)
```

### 5.4 Panel Agentes + Régimen

**Card izquierdo: Market Regime + Agentes**

```
Régimen actual:
  Badge grande: "BULL TRENDING" → fondo --green2, border --green, color --green
               "BEAR TRENDING" → fondo --red2, border --red, color --red
               "SIDEWAYS"      → fondo --bg3, color --text2
               "VOLATILE_CRASH"→ fondo --red2, border --red (SEÑALES BLOQUEADAS)
  Label descriptivo a la derecha (Syne 11px --text3)

Por cada agente (fila, border-bottom --border):
  Dot 8px (color del agente) | Nombre (Syne 11px --text1) |
  Score bar (80px, fondo --bg3, fill color del agente) |
  Valor numérico (JetBrains Mono 11px --green/--red)

  Colores por agente:
    TechnicalAgent     → --blue
    RegimeAgent        → --purple
    MicrostructureAgent→ --amber
    FundamentalAgent   → --text3 + badge "CLEAR"/"BLOCKED"

  FundamentalAgent no tiene score bar, muestra badge de estado.
```

**Card derecho: Consensus Gauge**

```
SVG circular (120x120px):
  Track exterior: fondo --bg3, stroke-width 10
  Fill arco: --green (BUY) o --red (SELL), stroke-linecap round
  El arco parte de -90° y avanza según score (0–100% del perímetro)
  Texto central: score (JetBrains Mono 20px weight 600 --text1)
  Subtexto: "CONSENSUS" (JetBrains Mono 9px --text3)

Debajo del gauge:
  Label "Señal generada"
  Badge grande: BUY / SELL / HOLD

Grid 2 columnas (fondo --bg3, border-radius 6px, padding 8px):
  SL: JetBrains Mono 11px --red
  TP: JetBrains Mono 11px --green
```

---

## 6. PÁGINA 2 — SIGNALS

### Layout

```
[4 Metric Cards]
[Tabla de señales]
[Panel XAI SHAP]
```

### 6.1 Metric Cards (4 columnas)

```
Señales hoy     | Ejecutadas  | Win Rate (barra)  | Bloqueadas riesgo
valor --text1   | valor       | valor --green      | valor --amber
```

### 6.2 Tabla de Señales

```
Columnas: Símbolo | Señal | Entrada | SL | TP | R:R | Confianza | Estado

Encabezados:
  Syne, 9px, UPPERCASE, letter-spacing 0.8px, --text3, weight 600
  Padding: 0 8px 8px

Filas:
  JetBrains Mono, 11px, --text2
  Padding: 8px
  Border-top: 1px solid --border
  Hover: fondo --bg3

Columna Símbolo: --text1 (destacado)
Columna SL: --red
Columna TP: --green
Columna R:R: --amber
Columna Señal: badge BUY/SELL
Columna Estado: badge FILL/REJECT/SKIP
```

### 6.3 Panel XAI — SHAP Values

```
Header:
  Título: "Explicabilidad XAI — SHAP Values · [SÍMBOLO] [SEÑAL]"
  Label derecho: nombre del agente en --blue

Descripción (Syne 11px --text3):
  "Contribución de cada indicador a la señal [X]
   (verde = pro-[X], rojo = en contra)"

Por cada feature (fila):
  LABEL  → JetBrains Mono 10px, --text2, width 100px fijo
  TRACK  → flex 1, height 6px, fondo --bg3, border-radius 3px
    Fill positivo (BUY): --green, desde la izquierda
    Fill negativo: --red, desde la derecha (float right)
  VALOR  → JetBrains Mono 10px, width 36px, text-align right,
            --green (positivo) o --red (negativo)

Features a mostrar (ordenadas por |valor| desc):
  EMA Cross | MACD Hist | Volume Ratio | RSI 14 | BB Width | ATR 14 | OBV

Recuadro resumen XAI (abajo):
  Fondo: --bg3
  Border-left: 3px solid --blue
  Border-radius: 6px
  Padding: 10px
  Label: "Resumen XAI" (Syne 10px --text3)
  Texto: explicación en lenguaje natural (Syne 11px --text2)
```

---

## 7. PÁGINA 3 — PORTFOLIO

### Layout

```
[4 Metric Cards]
[Equity Curve — ancho completo]
[Posiciones Abiertas]  [PnL por Símbolo]
```

### 7.1 Metric Cards

```
Equity Total    → valor JetBrains Mono 22px --text1, sub % total --green
PnL Hoy         → valor --green (positivo) o --red (negativo)
Sharpe Ratio    → valor --blue + barra proporcional (máx 3.0)
Max Drawdown    → valor --amber + barra proporcional (máx 20%)
```

### 7.2 Equity Curve

```
Tipo: line chart con área rellena
Color línea: --blue (#3d8ef8), stroke-width 2px
Puntos: radius 3px, color --blue
Tensión (smooth): 0.4
Relleno: gradiente vertical de rgba(61,142,248,0.25) → rgba(61,142,248,0.01)
Eje X: fechas (Syne 10px --text3)
Eje Y: valores en $ (Syne 10px --text3, formato $10,000)
Grilla: rgba(255,255,255,0.04)
Altura mínima: 180px

Header del card:
  Izquierda: "Equity Curve"
  Derecha: "Sortino: [valor --green]" | "Profit Factor: [valor --green]"
```

### 7.3 Posiciones Abiertas

```
Por posición (fila):
  Dot 8px (--green abierta ganando, --red perdiendo)
  Símbolo (Syne 11px --text1)
  Cantidad/lotes (JetBrains Mono 10px --text3)
  PnL abierto (JetBrains Mono 11px --green/--red)

Footer (border-top --border):
  "PnL abierto" | valor total --green/--red
```

### 7.4 PnL por Símbolo

```
Tipo: horizontal bar chart
Barras positivas: rgba(0,208,132,0.7) — --green
Barras negativas: rgba(255,71,87,0.7) — --red
Border-radius en barras: 3px
Labels eje Y: JetBrains Mono 10px --text2
Labels eje X: formato $[valor]
Altura: ~160px (ajustar según cantidad de símbolos)
```

---

## 8. PÁGINA 4 — RISK MONITOR

### Layout

```
[4 Metric Cards con barras de progreso]
[Kill Switch Card]  [Exposición Donut]
[Hard Limits Table]
```

### 8.1 Metric Cards con Límites

```
Cada card muestra:
  LABEL         → nombre del límite
  VALOR ACTUAL  → JetBrains Mono 22px, color según umbral
  BARRA         → progreso del uso (actual/límite × 100%)
  SUBLABEL      → "Límite: X%"

Lógica de color de la barra:
  < 50% del límite → --green
  50–80%           → --amber
  > 80%            → --red

Límites a mostrar:
  Exposición total   / 15%
  Pérdida diaria     / 10%
  Drawdown actual    / 20%
  Pérdidas consec.   / 7
```

### 8.2 Kill Switch

```
Estado INACTIVO:
  Dot pulsante verde | "INACTIVO" (JetBrains Mono 13px --green weight 600)
  Descripción (Syne 11px --text3): sistema operando normalmente
  Lista de triggers con estado OK (JetBrains Mono 11px --green)

Estado ACTIVO:
  Dot rojo pulsante | "ACTIVO" (JetBrains Mono 13px --red)
  Descripción: todas las órdenes bloqueadas

Botón:
  Inactivo: border --red, fondo --red2, color --red, texto "ACTIVAR KILL SWITCH"
  Armado:   fondo --red, color #fff, box-shadow 0 0 20px rgba(255,71,87,0.4)
  Fuente: JetBrains Mono 12px weight 600 letter-spacing 1px
  Width: 100%, border-radius 8px, padding 10px
```

### 8.3 Gráfico de Exposición (Donut)

```
Tipo: doughnut chart
Cutout: 72%
Segmentos:
  BTCUSDT → rgba(0,208,132,0.8)
  EURUSD  → rgba(255,71,87,0.8)
  XAUUSD  → rgba(245,166,35,0.8)
  Libre   → rgba(28,35,48,0.9)
Leyenda: posición right, Syne 10px --text2, boxWidth 10
Sin borde entre segmentos
```

### 8.4 Hard Limits Table

```
Columnas: Límite | Configurado | Actual | Uso % | Estado

Columna "Uso %": mini progress bar inline
  width 80px, height 4px, fondo --bg3
  Fill: --green / --amber / --red según umbral

Columna Estado: badge OK / WATCH / DANGER
```

---

## 9. ANIMACIONES Y MICROINTERACCIONES

```
Dot pulsante (live/inactivo):
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  animation: pulse 2s infinite

Transiciones de botones:
  transition: all 0.15s ease

Hover en filas de tabla:
  background: --bg3

Hover en nav tabs:
  color: --text2

Kill switch armado:
  box-shadow animado: 0 0 20px rgba(255,71,87,0.4)

Gauge SVG (consensus):
  stroke-dashoffset transition: 0.5s ease

Cambio de símbolo (candlestick):
  Redibujar sin transición abrupta
```

---

## 10. IMPLEMENTACIÓN POR STACK

### Streamlit

```python
# Importaciones clave
import plotly.graph_objects as go
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="TRADER IA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inyección de CSS (Design Tokens)
st.markdown("""<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@400;500;600;700');
  /* ... tokens CSS ... */
</style>""", unsafe_allow_html=True)

# Candlestick con Plotly
fig = go.Figure(data=[
    go.Candlestick(
        x=df.index, open=df.open, high=df.high, low=df.low, close=df.close,
        increasing_fillcolor='#00d084', increasing_line_color='#00d084',
        decreasing_fillcolor='#ff4757', decreasing_line_color='#ff4757'
    )
])
fig.update_layout(
    paper_bgcolor='#151a22', plot_bgcolor='#151a22',
    font=dict(family='JetBrains Mono', color='#8c99b0'),
    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)'),
    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)'),
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False
)
st.plotly_chart(fig, use_container_width=True)

# Metric cards con columnas
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Equity Total", "$10,482", "+4.82%")
```

### React / Next.js

```jsx
// Stack recomendado
// - lightweight-charts (TradingView) para candlestick
// - recharts o Chart.js para equity curve, RSI, MACD
// - CSS variables para theming

import { createChart } from 'lightweight-charts';

// Candlestick
const chart = createChart(container, {
  layout: { background: { color: '#151a22' }, textColor: '#8c99b0' },
  grid: { vertLines: { color: 'rgba(255,255,255,0.04)' },
          horzLines: { color: 'rgba(255,255,255,0.04)' } },
  crosshair: { mode: 1 },
  width: container.clientWidth,
  height: 200,
});

const candleSeries = chart.addCandlestickSeries({
  upColor: '#00d084', downColor: '#ff4757',
  borderUpColor: '#00d084', borderDownColor: '#ff4757',
  wickUpColor: '#00d084', wickDownColor: '#ff4757',
});
```

### Vue 3

```javascript
// Usar Chart.js + vue-chartjs, o lightweight-charts
// Los tokens CSS y el layout son idénticos al HTML/CSS puro
// Componentes sugeridos: CandlestickChart.vue, MetricCard.vue,
//                        ShapBar.vue, KillSwitch.vue, AgentRow.vue
```

### HTML / CSS / JS Puro

```javascript
// Chart.js para todos los gráficos excepto candlestick
// Candlestick: SVG manual o Plotly.js
// <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js">
// <script src="https://cdn.plot.ly/plotly-2.26.0.min.js">

// Config base de Chart.js para dark mode
const darkDefaults = {
  color: '#8c99b0',
  borderColor: 'rgba(255,255,255,0.04)',
  backgroundColor: 'rgba(255,255,255,0)',
};

// Equity curve
new Chart(ctx, {
  type: 'line',
  data: { labels, datasets: [{
    data: equityData,
    borderColor: '#3d8ef8',
    borderWidth: 2,
    tension: 0.4,
    fill: true,
    backgroundColor: (ctx) => {
      const g = ctx.chart.ctx.createLinearGradient(0,0,0,200);
      g.addColorStop(0, 'rgba(61,142,248,0.25)');
      g.addColorStop(1, 'rgba(61,142,248,0.01)');
      return g;
    }
  }]},
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#4d5a70', font: { size: 10 } },
           grid: { color: 'rgba(255,255,255,0.04)' } },
      y: { ticks: { color: '#4d5a70', font: { size: 10 },
                    callback: v => '$' + v.toLocaleString() },
           grid: { color: 'rgba(255,255,255,0.04)' } }
    }
  }
});
```

---

## 11. GRIDS Y LAYOUTS

```css
/* 4 columnas — metric cards */
.grid4 { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; }

/* 3 columnas — mini charts indicadores */
.grid3 { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; }

/* 2 columnas — paneles lado a lado */
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }

/* Responsive */
@media (max-width: 768px) {
  .grid4 { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .grid3 { grid-template-columns: repeat(1, minmax(0,1fr)); }
  .grid2 { grid-template-columns: repeat(1, minmax(0,1fr)); }
}
```

---

## 12. DATOS NECESARIOS POR PÁGINA

### Market View
```
- OHLCV (250 velas 1H por símbolo): open, high, low, close, volume
- EMA9, EMA21 (calculados)
- RSI(14), MACD(line, signal, histogram), BB(upper, lower, width)
- Régimen de mercado: string del RegimeAgent
- Score de cada agente: float -1.0 a +1.0
- Consensus score + señal (BUY/SELL/HOLD) + SL + TP
- Estado FundamentalAgent: CLEAR / BLOCKED
```

### Signals
```
- Lista de señales: {symbol, direction, entry, sl, tp, rr, confidence, status}
- SHAP values: {feature_name: float} ordenados por |valor|
- Métricas del día: total, ejecutadas, win_rate, bloqueadas
```

### Portfolio
```
- Serie temporal de equity: [{date, equity}]
- Posiciones abiertas: {symbol, quantity, pnl_open}
- PnL por símbolo: {symbol: float}
- Métricas: sharpe, sortino, profit_factor, max_drawdown, total_pnl
```

### Risk Monitor
```
- Exposición actual: {total_pct, by_symbol: {symbol: pct}}
- Pérdida diaria actual: float
- Drawdown actual: float
- Pérdidas consecutivas: int
- Estado kill switch: bool
- Hard limits: dict con configurados y actuales
```

---

## 13. CHECKLIST DE IMPLEMENTACIÓN

```
□ Fuentes Google Fonts cargadas (JetBrains Mono + Syne)
□ CSS tokens definidos como variables
□ Nav con tabs funcionales y estado activo
□ Ticker bar con datos de 7 símbolos
□ Page: Market View
  □ Selector de símbolo funcional
  □ Candlestick con colores correctos + volumen
  □ EMA9 y EMA21 overlay
  □ Mini-charts RSI, MACD, Bollinger
  □ Panel de agentes con score bars y colores
  □ Consensus gauge SVG circular
  □ Badge de señal + SL + TP
□ Page: Signals
  □ 4 metric cards
  □ Tabla de señales con todos los badges
  □ SHAP bars con fill positivo/negativo
  □ Recuadro resumen XAI
□ Page: Portfolio
  □ 4 metric cards (incluye barra sharpe/drawdown)
  □ Equity curve con gradiente
  □ Posiciones abiertas
  □ PnL horizontal bar chart
□ Page: Risk Monitor
  □ 4 metric cards con progress bars
  □ Kill switch funcional (toggle estado)
  □ Donut de exposición
  □ Hard limits table con mini bars
□ Responsive (colapso a 2 cols en móvil)
□ Sin texto hardcodeado — datos vienen de API/backend
```

---

## 14. REFERENCIA VISUAL RÁPIDA

```
╔═══════════════════════════════════════════════════════════╗
║  TRADER·IA  │ Market View │ Signals │ Portfolio │ Risk   ║
║                                           [● LIVE][PAPER]║
╠═══════════════════════════════════════════════════════════╣
║ BTC +2.3% │ ETH +1.1% │ EUR -0.2% │ XAU +0.9% │ US500  ║
╠═══════════════════════════════════════════════════════════╣
║ [BTCUSDT][ETHUSDT][EURUSD][XAUUSD][US500]                ║
║ ┌─────────────────────────────────────────────────────┐  ║
║ │ BTC/USDT 1H · 250 velas          67,420 ▲ +2.34%  │  ║
║ │  ┌──┐  ┌──┐      ┌──┐                              │  ║
║ │  │  │  │  │  │   │  │ ~~EMA9~~ ---EMA21---         │  ║
║ │  └──┘  └──┘  │   └──┘                              │  ║
║ │  ▓▓▓▒▒▓▓▓▒▒▒▒▓▓▓▓▓▓▒▒▒▒  (volumen)                │  ║
║ └─────────────────────────────────────────────────────┘  ║
║ ┌───────────┐ ┌───────────┐ ┌───────────┐               ║
║ │ RSI 58.4  │ │ MACD +124 │ │ BB Bands  │               ║
║ │ ~~~amber~ │ │ ▓▒▓▓▒▒▓▓▓ │ │ ─ · · ─  │               ║
║ └───────────┘ └───────────┘ └───────────┘               ║
║ ┌─────────────────────┐  ┌──────────────────────┐       ║
║ │ BULL TRENDING ✓     │  │     (+0.68)           │       ║
║ │ ● TechnicalAgent    │  │  ○──────────────○     │       ║
║ │ ● RegimeAgent       │  │     CONSENSUS         │       ║
║ │ ● Microstructure    │  │   [ BUY ]             │       ║
║ │ ● Fundamental CLEAR │  │  SL 65,580 TP 69,740  │       ║
║ └─────────────────────┘  └──────────────────────┘       ║
╚═══════════════════════════════════════════════════════════╝
```

---

*TRADER IA Dashboard Design System v1.0*
*Generado: Abril 2026 | Compatible con: Streamlit, React, Vue, Next.js, HTML/CSS/JS*
