# TRADER·IA Dashboard (SPA nativa)

Aplicación web oficial del proyecto: HTML/CSS/JS vanilla servido por FastAPI en `/` y `/dashboard`.
Sin framework, sin build step. Única dependencia externa: Plotly.js por CDN.

## Archivos

| Archivo | Rol |
|---|---|
| `dashboard.html` | La SPA completa: markup de las 9 pestañas + todo el JS inline (fetch helpers, render de cada panel, gráficos Plotly, WebSocket de precios, herramientas de dibujo, tema claro/oscuro). |
| `css/styles.css` | Design system: tokens CSS (`--bg0..4`, `--text1..3`, `--border`, acentos `--green/--red/--blue/--amber/--purple`), layout de sidebar + topbar, componentes (cards, badges, tablas, métricas), paleta índigo/cian/púrpura, bloque `:root[data-theme="light"]` para el modo claro, y media queries responsive (≤768px). |
| `css/drawing.css` | Toolbar de dibujo (lateral en desktop, barra inferior colapsable en móvil) + overlay canvas + modal de indicadores. |
| `js/drawing.js` | `DrawingManager` + 10 herramientas de dibujo (línea, rectángulo, triángulo, texto, paralela, curva, rayo, extendida, Fibonacci, Elliott Wave). Se conecta a la toolbar en `setupDrawing()` de `dashboard.html`. |
| `js/indicators-config.js` | Catálogo `INDICATORS` (nombre, parámetros configurables, colores por defecto) que alimenta el modal de indicadores. |
| `crypto-dashboard.html` | Dashboard standalone de validación cripto, embebido vía `<iframe>` en la pestaña "Crypto". |

## Cómo habla con el backend

No hay capa de cliente: `dashboard.html` llama a los endpoints REST de FastAPI directamente con dos helpers inline:

- `fetchAPI(path)` — GET público, devuelve el JSON o `null` (degrada a datos mock).
- `fetchAPIAuth(path, options)` — añade `Authorization: Bearer <token>` desde `localStorage.trader_ia_token`; devuelve `{ok, status, data, noToken}`.

Las rutas son las reales del backend (`/market/...`, `/signals`, `/risk/...`, `/portfolio/...`, `/execution`, `/backtest`, `/simulation`, `/strategies`, `/models`, `/monitoring/...`), sin prefijo `/api`.

> **Nota histórica:** existió `static/js/components.js` (librería `APIClient` + 12 componentes UI) que apuntaba a rutas `/api/...` inexistentes y nunca se usó realmente (solo se instanciaba `APIClient`, sin una sola llamada). Se retiró el 2026-08-28 junto con su `USAGE.md`. El patrón vigente son los helpers inline + funciones `render*` en `dashboard.html`.

## Estado en tiempo real

`dashboard.html` abre `ws://.../ws/prices/{symbol}?token=<jwt>` (mismo token del login) para actualizaciones del último candle en Market View, con reconexión por backoff. El resto de vistas hace fetch bajo demanda al cambiar de pestaña.

## Preferencias persistidas (localStorage)

`trader_ia_token` / `trader_ia_refresh_token` (sesión) · `trader_ia_theme` (claro/oscuro) · `trader_ia_custom_indicators` (recetas del constructor de indicadores) · presets de dibujo.
