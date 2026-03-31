La ventaja competitiva real del TRADER AI no es “otro bot de trading”, sino:
•	Sistema multi-agente con voto ponderado inteligente (no un solo modelo black-box).
•	Explicabilidad total (XAI) de cada señal (único en el mercado retail).
•	Adaptación automática al régimen de mercado + reentrenamiento.
•	Risk engine con Kill Switch proactivo (no reactivo).
•	Consenso conflictivo auditado + transparencia total.

FASE PRE — LÓGICA CORE Y VENTAJA COMPETITIVA (duración estimada: 5-7 días)
PRE-1. Auditoría y consolidación de la lógica actual (Día 1)
•	Crear documento LOGICA_CORE.md (nuevo archivo en raíz) con:
o	Diagrama de flujo completo del ciclo de señal (desde ingestion → 4 agentes → consenso → risk → execution).
o	Tabla detallada de cada agente (input, modelo, output, peso, fallback).
o	Algoritmo exacto de VotingEngine (fórmula matemática de consenso ponderado + umbral).
o	Reglas completas del RiskManager + Kill Switch (todas las 7 condiciones).
o	Flujo de XAI (cómo se genera la explicación SHAP en lenguaje natural).
o	Diagrama de adaptación de régimen (RegimeWatcher + Retraining trigger).
PRE-2. Definición cuantitativa de la ventaja competitiva (Día 2)
•	Crear tabla comparativa VENTAJA_COMPETITIVA.md vs principales competidores


. Estrategias Estadísticas (StatArb) – Mayor efectividad actual en pares cointegrados
Estas son las más robustas y de bajo drawdown en mercados 2025-2026.
Estrategia / Modelo	Por qué es efectiva en 2026	Cómo integrarla en TRADER AI	Impacto esperado	Prioridad
Pairs Trading con Cointegration (Johansen / Engle-Granger)	Win-rate ~70-72 %, Sharpe 1.4-2.0 en pares BTC-ETH, EURUSD-GBPUSD. Detecta spreads estacionarios y mean-reversion.	Nuevo agente StatisticalArbAgent (usa statsmodels para cointegration test + Kalman filter para hedge ratio dinámico). Voto 25-30 % en forex/crypto.	Reduce DD en lateral y mejora win-rate en regímenes neutrales.	★★★★★ (Fácil + alto impacto)
Mean Reversion Multi-Asset (Basket Trading)	Excelente en 3-5 activos correlacionados. Usa z-score + half-life de reversión.	Extender RegimeAgent o nuevo MeanReversionAgent. Usa InstrumentConfig ya existente.	Complementa perfectamente al agente Técnico actual.	★★★★
Kalman Filter Dynamic Hedging	Filtra ruido y actualiza ratios de cointegración en tiempo real.	Agregar como feature en FeatureEngine + sub-módulo en StatisticalArbAgent.	Mayor estabilidad que EMA simple.	★★★★

Acción inmediata recomendada: Crear core/agents/statistical_arb_agent.py (basado en el schema de technical_agent.py).
2. Modelos Matemáticos / Quantitative (Alta adaptabilidad)
Son los que más han avanzado con IA en 2025-2026.
Modelo / Estrategia	Por qué destaca en 2026	Integración en TRADER AI	Impacto	Prioridad
Reinforcement Learning (PPO / A2C)	State-of-the-art en portfolio management y optimal execution. Supera benchmarks en Sharpe y adapta en vivo.	Nuevo agente RLAgent (usa Stable-Baselines3 o Torch). Recompensa = Sharpe + penalización de drawdown. Entrena con datos históricos + online fine-tuning.	Agente “inteligente” que aprende de errores reales. Ideal para PositionSizer y Execution.	★★★★★ (Transformacional)
Temporal Fusion Transformer (TFT) o Mamba	Mejor forecasting multi-horizon que LSTM/LightGBM. Menos computación que Transformers clásicos.	Reemplazo opcional o paralelo al TechnicalAgent. Nuevo modelo en data/models/.	Mejora precisión de señales técnicas en 15-25 %.	★★★★
Graph Neural Networks (GNN) para Microestructura	Analiza relaciones entre órdenes, wallets (on-chain) y liquidez.	Mejorar MicrostructureAgent con GNN (usa PyTorch Geometric).	Ventaja real en crypto y MT5 (order-book + on-chain).	★★★
Symmetry-Aware Transformers / Quant-LLMs	Capturan relaciones causales asimétricas en series temporales ruidosas.	Agente opcional AdvancedForecastAgent (opcional para Fase 5).	Explicabilidad XAI aún más potente.	★★★
Acción recomendada: Empezar por PPO Agent (es el que más diferencia genera en multi-agente).
3. Estrategias Algorítmicas Emergentes (Alta efectividad en crypto + forex)
Estrategia	Efectividad 2026	Integración	Impacto	Prioridad
Arbitrage con Masking (Crypto + Forex)	Aún rentable si se usa randomización y AI-masking contra detección.	Nuevo agente ArbitrageAgent (cross-exchange Binance-Bybit + MT5).	Genera alpha puro con riesgo casi nulo.	★★★★
Volatility Trading + Breakout Momentum	Funciona muy bien en regímenes de alta volatilidad (post-2025).	Nueva estrategia en StrategyBuilder (volatility_breakout.py).	Complementa al agente de Régimen.	★★★
On-Chain Analytics + Advanced Sentiment	Leading indicator en crypto (whale flows, exchange inflows).	Mejorar FundamentalAgent con datos de Glassnode / Dune (API).	Filtro contrarian más potente.	★★★
Multi-Agent LLM Framework (TradingAgents style)	Colabora entre analistas (fundamental, sentiment, técnico, risk). Ya hay papers que muestran + Sharpe.	Evolucionar el consenso actual a LLM-orchestrated (opcional Fase 5).	Hace el sistema más “humano” y robusto.	★★★ (Futuro)
Plan de Trabajo Recomendado (FASE PRE-2 — Lógica Avanzada)
Duración estimada: 10-14 días (puedes hacerlo en paralelo con FASE A del PLAN_TRABAJO.md).
1.	Día 1-2: Crear LOGICA_CORE_EXTENDIDA.md con diagramas de los nuevos agentes y cómo votan en el VotingEngine (actualizar pesos por asset_class).
2.	Día 3-5: Implementar StatisticalArbAgent (prioridad máxima) + tests de cointegration.
3.	Día 6-8: Implementar RLAgent (PPO) como agente de decisión final / position sizing.
4.	Día 9-10: Actualizar VotingEngine, RiskManager y StrategyBuilder para soportar los nuevos agentes/estrategias.
5.	Día 11-12: Backtest walk-forward de las nuevas estrategias (debe pasar Sharpe ≥ 1.0 y DD ≤ 20 %).
6.	Día 13-14: Actualizar XAI para explicar también las nuevas señales (SHAP + texto natural de RL/cointegration).


[ ] Lógica de Estrategia y Alpha (Nueva Fase)
•	[ ] Definir Set de Indicadores "Smart Money": En lugar de RSI simple, configurar el FeatureEngine para detectar quiebres de estructura (MSB) y vacíos de liquidez (FVG).
•	[ ] Configurar Pesos de Consenso Dinámicos: Implementar que el RegimeAgent pueda reducir el peso del TechnicalAgent al 20% en mercados laterales.
•	[ ] Entrenamiento de Modelos con SHAP: Ejecutar scripts/retrain.py asegurando que los valores SHAP identifiquen qué indicadores son realmente predictivos y descartar el "ruido".
•	[ ] Validación de Correlación: En el PortfolioManager, añadir una lógica que impida abrir posiciones en BTC y ETH simultáneamente si la correlación es > 0.90, para evitar duplicar el riesgo.

1. Lógica Específica por Clase de Activo
Tu sistema de 4 agentes debe operar con reglas de "Alpha" diferenciadas para maximizar la efectividad:
Activo	Estrategia de Ventaja (Alpha)	Indicadores Clave en TechnicalAgent
Forex	Reversión a la media y Sesiones. El mercado de divisas tiende a ser lateral.	RSI (periodos largos), Bandas de Bollinger y correlaciones entre divisas.
Commodities (Oro)	Refugio Seguro y Volatilidad. Reacciona violentamente a noticias geopolíticas.	ATR para stop-loss dinámicos y volumen real de futuros (vía MT5).
Índices (US500)	Seguimiento de Tendencia. Los índices están diseñados para subir a largo plazo.	EMAs de 50/200, MACD y perfiles de volumen.
Bitcoin	Momentum e Ineficiencias de Liquidez. Altamente especulativo y 24/7.	Order Flow Imbalance (OBI) y sentimiento de redes sociales.



2. Definición de la Ventaja Competitiva
Para diferenciarte de los bots estándar, implementaremos tres capas de lógica avanzada:
A. Pesos de Consenso Dinámicos (E7)
El sistema no dará el mismo peso a los agentes en todos los activos. En Forex, el MicrostructureAgent tendrá peso 0 porque el mercado es descentralizado, mientras que en Cripto será vital.
B. Filtro Macroeconómico de Alto Impacto (E8)
A diferencia de otros bots que "explotan" durante noticias, tu sistema usará un FundamentalAgent que bloquea operaciones en Forex/Índices ±30 minutos antes y después de eventos como el NFP o decisiones de tasas de la FED.
C. Gestión de Riesgo Multi-Asset (E5)
El cálculo de lotaje será inteligente. El sistema convertirá automáticamente "Pips" (Forex), "Puntos" (Índices) y "Dólares" (Bitcoin) a una unidad de riesgo uniforme basada en el InstrumentConfig.

Ventaja competitiva recomendada
🔥 “Sistema adaptativo multi-estrategia con detección de régimen + optimización continua + validación estadística real”
En términos más técnicos:
Un Meta-Sistema de Trading que:
•	Detecta el régimen de mercado 
•	Selecciona la mejor estrategia para ese régimen 
•	Ajusta parámetros dinámicamente 
•	Valida estadísticamente en tiempo real 
•	Penaliza estrategias que pierden edge
•	3. Arquitectura lógica objetivo (nivel superior)
•	Debes evolucionar a esta capa:
                ┌─────────────────────────┐
                │ Regime Detection Engine │
                └────────────┬────────────┘
                             ↓
         ┌───────────────────────────────┐
         │ Strategy Selection Engine     │
         │ (Meta-Model / Ensemble)       │
         └────────────┬──────────────────┘
                      ↓
     ┌────────────────────────────────────┐
     │ Strategy Layer (portfolio de edge) │
     │ - Trend Following                 │
     │ - Mean Reversion                 │
     │ - Breakout                      │
     │ - Market Making (futuro)        │
     └────────────┬─────────────────────┘
                  ↓
      ┌───────────────────────────────┐
      │ Execution + Risk Engine       │
      └───────────────────────────────┘



4. Modelos y estrategias que debes incorporar (priorizados)
4.1. Nivel 1 — Base sólida (obligatorio)
A. Modelos de régimen (CRÍTICO)
•	Hidden Markov Models (HMM) 
•	Clustering (K-Means sobre volatilidad/retornos) 
•	Regime Switching Models

B. Estrategias core
1. Trend Following (alta robustez)
•	EMA crossover adaptativo 
•	Breakouts (Donchian Channels) 
•	Momentum multi-timeframe 
2. Mean Reversion (alta frecuencia)
•	Z-score de desviación 
•	Bollinger Bands + filtro de volumen 
•	RSI extremo con confirmación 
3. Volatility strategies
•	ATR expansion 
•	Volatility breakout


4.2. Nivel 2 — Diferenciación real
A. Meta-modelo (clave de ventaja)
Un modelo que decide:
“¿Qué estrategia usar ahora?”
Modelos recomendados:
•	Gradient Boosting (LightGBM/XGBoost) 
•	Random Forest 
•	Logistic meta-labeling (López de Prado) 
Input:
•	Volatilidad 
•	Tendencia 
•	Liquidez 
•	Drawdown reciente 
•	Performance por estrategia

B. Meta-labeling (MUY importante)
Concepto:
No decides BUY/SELL → decides si una señal es válida o no
C. Ensemble de estrategias
•	Voting ponderado entre estrategias 
•	Pesos dinámicos según performance reciente
4.3. Nivel 3 — Edge avanzado (alto valor)
A. Feature engineering avanzado
•	Order flow imbalance 
•	Volume profile 
•	Market microstructure signals 
•	Liquidity gaps 
________________________________________
B. Reinforcement Learning (futuro)
•	Para sizing y timing 
•	No para señales base (muy inestable al inicio) 

5. Indicadores clave (los que realmente importan)
Olvida solo RSI/MACD.
Indicadores de performance (estratégicos)
•	Sharpe Ratio 
•	Sortino Ratio 
•	Calmar Ratio 
•	Max Drawdown 
•	Profit Factor 
•	Expectancy 
________________________________________
Indicadores de calidad del modelo
•	Precision/Recall de señales 
•	Hit ratio por régimen 
•	Stability (variance del Sharpe) 
________________________________________
Indicadores operativos (clave diferencial)
•	Edge decay (pérdida de efectividad) 
•	Time under water 
•	Regime performance matrix 
1. Objetivo formal del meta-modelo
Predecir qué estrategia tiene mayor probabilidad de generar retorno ajustado por riesgo en el siguiente intervalo de tiempo.
No predice precio.
No predice BUY/SELL.
👉 Predice:
“¿Qué estrategia usar ahora?”
________________________________________
2. Formulación del problema
Tipo de problema
Clasificación multiclase:
y ∈ {trend_following, mean_reversion, breakout, no_trade}
O versión más avanzada:
👉 Ranking / scoring continuo por estrategia
score_strategy_i = f(features)
________________________________________
3. Features (la parte más importante)
3.1. Bloque 1 — Contexto de mercado (macro)
features_market = [
    volatility_rolling_24h,
    volatility_rolling_7d,
    atr_normalized,
    realized_volatility,
    
    trend_strength_adx,
    ema_slope_50,
    ema_slope_200,
    
    return_1h,
    return_24h,
    return_7d,
    
    skewness_returns,
    kurtosis_returns
]
________________________________________
3.2. Bloque 2 — Estructura de mercado (micro)
features_micro = [
    bid_ask_spread,
    order_book_imbalance,
    volume_delta,
    liquidity_depth,
    
    trade_intensity,
    price_impact_estimate
]
________________________________________
3.3. Bloque 3 — Régimen de mercado
(Salida de tu RegimeWatcher, pero mejorado)
features_regime = [
    regime_label,              # bull, bear, sideways, high_vol
    regime_confidence,
    regime_duration,
    
    volatility_regime,
    trend_regime_score
]
________________________________________
3.4. Bloque 4 — Performance de estrategias (CLAVE DIFERENCIAL)
👉 Aquí está el edge real
features_strategy_perf = [
    sharpe_last_20_trades,
    winrate_last_20,
    avg_return_last_20,
    max_drawdown_last_20,
    
    sharpe_last_100,
    performance_decay,         # slope performance
    
    trades_last_hour,
    trades_last_day
]
________________________________________
3.5. Bloque 5 — Estado del portafolio
features_portfolio = [
    current_drawdown,
    daily_pnl,
    exposure_total,
    exposure_per_asset,
    
    consecutive_losses,
    risk_utilization
]
________________________________________
3.6. Vector final
X = concat(
    features_market,
    features_micro,
    features_regime,
    features_strategy_perf,
    features_portfolio
)
________________________________________
4. Target (cómo entrenar el modelo)
Opción A — Mejor estrategia ex-post
Para cada timestamp:
y = argmax(strategy_returns_next_window)
________________________________________
Opción B — Meta-labeling (más robusto)
Para cada estrategia:
y_strategy_i = 1 if return_i > threshold else 0
Luego:
👉 Modelo binario por estrategia
________________________________________
Opción C — Score continuo (recomendado)
y_strategy_i = sharpe_forward_window
________________________________________
5. Arquitectura del modelo
Modelo base recomendado
🔹 LightGBM (óptimo en tu caso)
•	Maneja no linealidad 
•	Rápido 
•	Buen performance tabular 
________________________________________
Arquitectura general
MetaModel:
    input: feature_vector (X)
    model: LightGBM / XGBoost
    
    output:
        scores = {
            "trend": 0.72,
            "mean_reversion": 0.41,
            "breakout": 0.63,
            "no_trade": 0.20
        }
________________________________________
Lógica de decisión
selected_strategy = argmax(scores)

if max(scores) < threshold:
    return NO_TRADE
________________________________________
6. Pipeline completo (integrado con tu sistema)
Market Data → Feature Engine → Regime Detection
                           ↓
                Strategy Performance Tracker
                           ↓
                      Meta Model
                           ↓
              Strategy Selector Engine
                           ↓
                  Strategy Execution
                           ↓
                     Risk Manager
                           ↓
                     Portfolio Update
________________________________________
7. Pseudocódigo completo
7.1. Entrenamiento
def build_dataset(market_data, strategies):
    dataset = []

    for t in timeline:
        X = extract_features(t)
        
        future_returns = {}
        for strategy in strategies:
            future_returns[strategy] = simulate_strategy(
                strategy, t, horizon=H
            )
        
        y = argmax(future_returns)
        
        dataset.append((X, y))
    
    return dataset
________________________________________
def train_meta_model(dataset):
    X, y = split(dataset)
    
    model = LightGBM(
        num_leaves=64,
        learning_rate=0.01,
        n_estimators=500
    )
    
    model.fit(X, y)
    
    return model
________________________________________
7.2. Inferencia en tiempo real
def select_strategy(current_state):
    X = extract_features(current_state)
    
    scores = model.predict_proba(X)
    
    best_strategy = argmax(scores)
    
    if scores[best_strategy] < CONFIDENCE_THRESHOLD:
        return "no_trade"
    
    return best_strategy
________________________________________
7.3. Integración con tu sistema
def run_pipeline():
    market_data = get_market_data()
    
    features = feature_engine(market_data)
    
    regime = regime_detector(features)
    
    strategy_scores = meta_model.predict(features)
    
    selected_strategy = strategy_selector(strategy_scores)
    
    signal = strategies[selected_strategy].generate_signal()
    
    if risk_manager.validate(signal):
        execute(signal)
    
    portfolio.update()
________________________________________
8. Módulos que debes crear (en tu repo)
Basado en tu estructura:
core/
├── meta_model/
│   ├── model.py
│   ├── trainer.py
│   ├── dataset_builder.py
│   ├── feature_builder.py
│   └── selector.py
________________________________________
9. Métricas de validación (CRÍTICAS)
No evalúes solo accuracy.
Usa:
•	Sharpe del sistema completo 
•	Drawdown vs baseline 
•	Strategy selection accuracy 
•	Profit factor global 
•	Stability (variance del Sharpe)


1.3 Modelos ML por agente (mejora del actual TechnicalAgent)
El agente técnico actual usa LightGBM con features genéricas. Para lograr ventaja, se propone:
•	Cripto: Modelo de clasificación con LightGBM + features derivadas de orden límite (depth) y datos on chain. Entrenar con walk forward y usar ensemble de reglas de momentum/mean reversion.
•	Forex/Índices: Modelo de tendencia con LSTM + atención, combinado con un modelo de cambio de régimen (HMM) que detecte periodos de trending/ranging.
•	Materias primas: Modelo basado en reglas estacionales y regresión con variables macro.
Entregable: Una matriz de decisión por clase de activo que especifique:
•	Indicadores técnicos seleccionados.
•	Features derivadas (ej. ratios, diferencias normalizadas).
•	Arquitectura de modelo (LightGBM, LSTM, reglas).
•	Peso del agente en el consenso (actualmente técnico 45%, pero puede variar por activo).


Fase 3. Mejora del motor de riesgo y gestión de capital
El riesgo actual es sólido pero se puede refinar para adaptarse a la volatilidad de cada activo.
Mejora	Implementación
Riesgo dinámico por activo	Límites de drawdown y pérdida diaria individualizados (ej. cripto 10%, forex 3%).
Kelly fraccional	Actualmente se usa Kelly; añadir un factor de seguridad (Kelly/2) y ajustar por correlación entre activos.
Volatilidad objetivo	Escalar tamaño de posición para mantener volatilidad anualizada constante (por ej. 20%).
Stop loss dinámico	Usar ATR × múltiplo (ej. 2×ATR) en lugar de stop fijo, adaptado a cada activo.
Gestión de exposición	Limitar exposición total y por sector (ej. no más de 30% en cripto).



1. ¿Por qué modelos avanzados?
Limitación de modelos actuales	Solución con modelos avanzados
LightGBM usa features estáticas de ventanas fijas (ej. valores de RSI, MACD). No captura dependencias temporales largas.	Redes recurrentes (LSTM, GRU) o Transformer que aprenden secuencias completas de precios.
El agente de régimen clasifica manualmente (ej. usando HMM simple). No aprovecha toda la información de mercado.	Modelos de cambio de régimen basados en deep learning o Bayesian structural time series.
El agente de microestructura usa reglas básicas (spread, depth). No modela dinámica de orden límite.	Modelos generativos de libro de órdenes (LOB) o redes neuronales gráficas (GNN) para capturar interacciones entre niveles.
El consenso es estático (pesos fijos). No se adapta a la calidad reciente de cada agente.	Meta aprendizaje o ponderación dinámica basada en desempeño reciente en papel.
No se aprovechan datos alternativos (noticias, on chain, macro).	Integración de embeddings de noticias (BERT financiero), on chain metrics, y datos macro como variables exógenas.
________________________________________
2. Modelos avanzados por agente
2.1 Agente Técnico (actual LightGBM) → Modelo de series temporales híbrido
Se propone reemplazar o complementar el agente técnico con un ensemble que combine:
•	LSTM con atención para capturar dependencias a largo plazo. La entrada será una secuencia de (open, high, low, close, volume) de los últimos N periodos (ej. 60 velas de 1h). La salida puede ser:
o	Clasificación: {buy, sell, hold}.
o	Regresión: retorno esperado en el siguiente periodo.
•	Temporal Convolutional Network (TCN) – alternativa más rápida que LSTM, con menos riesgo de overfitting en datos financieros.
•	Transformer con positional encoding – para modelar relaciones a largo plazo y detectar patrones de reversión o momentum.
Integración:
Estos modelos se entrenarán como predictores adicionales y sus señales se incorporarán al agente técnico actual (ponderación dinámica). Se puede usar un ensemble stacking: LightGBM + LSTM + TCN, donde la combinación se optimiza en backtesting walk forward.
Feature engineering mejorada:
Además de los OHLCV, incluir indicadores técnicos ya calculados (RSI, MACD, etc.) como canales adicionales, permitiendo al modelo aprender combinaciones no lineales.
2.2 Agente de Régimen → Modelo de cambio de régimen probabilístico
El régimen actual se basa en clasificación manual (alcista, bajista, lateral, crash). Se puede mejorar con:
•	Hidden Markov Model (HMM) con observaciones multivariadas: Entrenar con features como volatilidad realizada, skewness de retornos, correlación con otros activos, VIX, etc. El HMM inferirá el régimen latente en tiempo real.
•	Bayesian Change Point Detection: Detectar cambios estructurales en la media/varianza de los retornos.
•	Red neuronal con ventana deslizante: Clasificar régimen usando una red simple con capas densas, donde la entrada es un vector de features de mercado.
Integración:
El régimen inferido se usa para:
•	Ajustar pesos de los agentes (ej. en mercados laterales dar más peso al agente de mean reversion).
•	Modificar parámetros de riesgo (aumentar stop loss en alta volatilidad).
•	Activar/desactivar ciertas estrategias.
2.3 Agente de Microestructura → Modelado de libro de órdenes con GNN
Para activos con alta liquidez (cripto, futures), se puede utilizar:
•	Gráficos de libro de órdenes: Cada nivel de precio es un nodo con atributos (volumen, distancia al mid price). Una Graph Neural Network (GNN) aprende representaciones que predicen movimientos inminentes.
•	Modelos de orden límite (LOB): redes convolucionales 1D sobre el depth (ej. DeepLOB o LOBSTER). Son capaces de capturar patrones de presión de compra/venta.
Integración:
El modelo se ejecuta cada vez que se recibe un snapshot del libro de órdenes (WebSocket) y emite una señal de dirección (buy/sell) basada en el imbalance. Esta señal se combina con la del agente técnico en el consenso.
2.4 Agente Fundamental → Análisis de sentimiento y datos alternativos
Actualmente usa Fear & Greed Index y CoinGecko. Se puede expandir con:
•	NLP sobre noticias financieras: Utilizar modelos preentrenados como FinBERT para clasificar sentimiento de titulares de Bloomberg, Reuters, o feeds de Twitter. La salida es un puntaje de sentimiento ( 1 a 1) que se incorpora como feature.
•	On chain metrics (cripto): Datos como hash rate, reservas de exchanges, MVRV, ratio de transacciones. Se pueden usar como features en un modelo de regresión logística o como entrada a un modelo LSTM junto con precios.
•	Macro económicos (forex/índices): Incorporar variables como PMI, tasas de interés, inflación, empleo (con periodicidad diaria/semanal). Un modelo de series temporales con variables exógenas (SARIMAX, LSTM multivariado) mejora la predicción.
Integración:
El agente fundamental puede emitir un filtro (no una señal directa) que veto señales en condiciones extremas (ej. sentimiento muy negativo sin fundamentos). Su peso en el consenso es bajo (actualmente 0% en votación, solo filtro), pero se puede otorgar un peso pequeño si se valida que mejora el Sharpe.
________________________________________
3. Nuevos agentes y meta aprendizaje
3.1 Agente de Aprendizaje por Refuerzo (RL) para ejecución y sizing
El RL puede optimizar no solo la dirección, sino también el timing de entrada/salida y el tamaño de posición. Se puede implementar:
•	Deep Q Network (DQN) o Proximal Policy Optimization (PPO) que, dado el estado actual (precios, posiciones abiertas, riesgo), decida:
o	{buy, sell, hold}.
o	Cantidad (fracción de capital).
•	El entorno de simulación (core/simulation/) se usa para entrenar el agente en un entorno con costos reales. La recompensa puede ser Sharpe, P&L o una métrica ajustada por riesgo.
Integración:
El agente RL puede actuar como un ejecutor dentro del módulo de ejecución, tomando decisiones de entrada/salida después de que el consenso haya generado una señal. O bien, puede ser un agente más en el consenso, con un peso que se ajusta según su desempeño reciente.
3.2 Meta aprendizaje: ponderación dinámica de agentes
En lugar de pesos fijos (45% técnico, 35% régimen, 20% microestructura), se puede utilizar un meta aprendiz que aprende a combinar las señales basándose en el desempeño histórico reciente de cada agente.
•	Método simple: Calcular la correlación entre la señal de cada agente y el retorno real en las últimas N operaciones; asignar pesos proporcionales al desempeño.
•	Método avanzado: Un pequeño modelo (ej. regresión logística) que toma como entrada las señales de los agentes y features de mercado (volatilidad, volumen) y decide la señal final.
________________________________________
4. Manejo de datos y entrenamiento
4.1 Datos necesarios
Modelo	Datos requeridos	Fuente
LSTM/Transformer	Secuencias OHLCV + indicadores	Binance, Yahoo Finance, Alpha Vantage
GNN para LOB	Snapshots de libro de órdenes	WebSocket Binance/Bybit
FinBERT	Noticias financieras históricas	APIs de noticias (NewsAPI, Bloomberg), scraping
On chain	Hash rate, MVRV, etc.	Glassnode, CoinMetrics
Macro	PMI, tasas, empleo	FRED, Investing.com

4.2 Estrategia de entrenamiento
•	Walk forward: Se entrena cada modelo con una ventana de 2 años y se evalúa en los siguientes 3 meses, deslizando cada trimestre. Esto asegura que los modelos no memorizan el futuro.
•	Validación cruzada temporal: No mezclar datos futuros en entrenamiento.
•	Regularización: Uso de dropout, early stopping, y penalizaciones para evitar sobreajuste.
•	Transfer learning: Para activos con pocos datos (materias primas), se puede pre entrenar en datos de índices y luego fine tune.
4.3 Computación y escalabilidad
•	GPU: Para entrenar LSTM/Transformer, GNN, y RL se recomienda una GPU (local o en la nube). En producción, la inferencia puede ser en CPU con modelos optimizados (ONNX, TensorRT).
•	Orquestación: Usar Celery o Airflow para distribuir tareas de entrenamiento periódico (retraining) sin afectar el pipeline en tiempo real.
________________________________________
5. XAI para modelos avanzados
La explicabilidad es crucial para confianza y auditoría. Para cada modelo avanzado se debe implementar:
•	LSTM/Transformer: Visualización de atención para ver qué timesteps son más relevantes.
•	GNN: Análisis de importancia de nodos (niveles de precio) usando gradientes.
•	RL: Interpretación a través de análisis de políticas (ej. qué estados llevan a acciones específicas).
•	Meta aprendiz: Mostrar los pesos asignados a cada agente y su evolución.
El módulo xai_module.py debe extenderse para aceptar cualquier modelo y generar explicaciones en texto.
