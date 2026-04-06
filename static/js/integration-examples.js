/**
 * Ejemplos de Integración con Componentes
 * Muestra cómo usar los componentes en el dashboard
 */

// ===== EJEMPLO 1: Cargar y mostrar señales con componentes =====
async function loadSignalsWithComponents() {
  try {
    // Obtener datos del API
    const signals = await api.signals.getSignalsBatch(
      ['EURUSD', 'XAUUSD', 'GBPUSD']
    );

    // Crear tabla 
    const table = TableComponent.create({
      headers: ['Symbol', 'Signal', 'Entry', 'SL', 'TP', 'R:R', 'Status'],
      rows: signals.map(s => ({
        symbol: s.symbol,
        signal: BadgeComponent.create(s.action, s.action.toLowerCase()),
        entry: Utils.formatCurrency(s.entry),
        sl: Utils.formatCurrency(s.sl),
        tp: Utils.formatCurrency(s.tp),
        rr: `${s.rr.toFixed(1)}x`,
        status: BadgeComponent.create(
          s.status.toUpperCase(),
          `badge-${s.status}`
        )
      }))
    });

    // Mostrar en document
    document.getElementById('signalsContainer').innerHTML = '';
    document.getElementById('signalsContainer').appendChild(table);

    // Mostrar notificación
    ToastComponent.show({
      message: `${signals.length} señales cargadas`,
      type: 'success'
    });
  } catch (error) {
    ToastComponent.show({
      message: `Error: ${error.message}`,
      type: 'error'
    });
  }
}

// ===== EJEMPLO 2: Mostrar métrica de portfolio =====
async function loadPortfolioMetricsWithComponents() {
  try {
    const portfolio = await api.portfolio.getPortfolio();
    const metrics = await api.portfolio.getMetrics();

    const metricsContainer = document.getElementById('portfolioMetrics');
    metricsContainer.innerHTML = '';

    // Crear tarjetas de métrica
    const cards = [
      MetricCardComponent.create({
        label: 'Equity Total',
        value: Utils.formatCurrency(portfolio.total_capital),
        bar: {
          percent: 100,
          color: 'var(--blue)'
        }
      }),
      MetricCardComponent.create({
        label: 'P&L Hoy',
        value: Utils.formatCurrency(portfolio.daily_pnl),
        sub: Utils.formatPercent(portfolio.daily_pnl_pct),
        color: portfolio.daily_pnl >= 0 ? 'var(--green)' : 'var(--red)'
      }),
      MetricCardComponent.create({
        label: 'Sharpe Ratio',
        value: portfolio.sharpe_ratio.toFixed(2),
        bar: {
          percent: Math.min(portfolio.sharpe_ratio / 3 * 100, 100),
          color: 'var(--blue)'
        }
      }),
      MetricCardComponent.create({
        label: 'Max Drawdown',
        value: Utils.formatPercent(portfolio.drawdown_current),
        bar: {
          percent: Math.min(portfolio.drawdown_current / 0.2 * 100, 100),
          color: 'var(--amber)'
        }
      })
    ];

    cards.forEach(card => {
      metricsContainer.appendChild(card);
    });
  } catch (error) {
    console.error('Error loading portfolio metrics:', error);
  }
}

// ===== EJEMPLO 3: Mostrar agentes con componentes =====
async function loadAgentsWithComponents(symbol) {
  try {
    const features = await api.market.getMarketData(symbol, '1wk');

    const agentsList = [
      {
        name: 'TechnicalAgent',
        score: features.technical_score || 0.3,
        status: features.technical_score > 0 ? 'bullish' : 'bearish'
      },
      {
        name: 'RegimeAgent',
        score: features.regime_score || 0.5,
        status: features.regime_score > 0.3 ? 'bullish' : 'bearish'
      },
      {
        name: 'MicrostructureAgent',
        score: features.micro_score || 0.1,
        status: features.micro_score > 0 ? 'positive' : 'negative'
      }
    ];

    const container = document.getElementById('agentRows');
    container.innerHTML = '';

    const agentsList_html = AgentRowComponent.createList(agentsList);
    container.appendChild(agentsList_html);

    // Actualizar consenso gauge
    const consensus = features.consensus_score || 0;
    GaugeComponent.updateCircularGauge(
      'consensusGauge',
      consensus,
      1,
      'Consensus Score'
    );
  } catch (error) {
    console.error('Error loading agents:', error);
  }
}

// ===== EJEMPLO 4: Mostrar posiciones con componentes =====
async function loadPositionsWithComponents() {
  try {
    const positions = await api.portfolio.getPositions();

    const container = document.getElementById('positionsList');
    container.innerHTML = '';

    if (!positions || positions.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-state-text';
      empty.textContent = 'No hay posiciones abiertas';
      container.appendChild(empty);
      return;
    }

    const list = PositionRowComponent.createList(
      positions.map(p => ({
        symbol: p.symbol,
        quantity: `${p.size} ${p.side}`,
        pnl: p.pnl || 0,
        status: 'open'
      }))
    );

    container.appendChild(list);

    // Calcular P&L total
    const totalPnl = positions.reduce((sum, p) => sum + (p.pnl || 0), 0);
    document.getElementById('totalOpenPnl').textContent =
      Utils.formatCurrency(totalPnl);
    document.getElementById('totalOpenPnl').style.color =
      totalPnl >= 0 ? 'var(--green)' : 'var(--red)';
  } catch (error) {
    console.error('Error loading positions:', error);
  }
}

// ===== EJEMPLO 5: Mostrar métricas de riesgo =====
async function loadRiskMetricsWithComponents() {
  try {
    const riskData = await api.risk.getRiskMetrics();

    const riskMetrics = document.getElementById('riskMetrics');
    riskMetrics.innerHTML = '';

    const getBarColor = (current, limit) => {
      const percentUsed = limit > 0 ? current / limit : 0;
      return percentUsed < 0.5
        ? 'var(--green)'
        : percentUsed < 0.8
          ? 'var(--amber)'
          : 'var(--red)';
    };

    const cards = [
      MetricCardComponent.create({
        label: 'Exposición Total',
        value: Utils.formatPercent(riskData.total_exposure_pct),
        bar: {
          percent: Math.min(
            riskData.total_exposure_pct / riskData.max_portfolio_risk_pct * 100,
            100
          ),
          color: getBarColor(
            riskData.total_exposure_pct,
            riskData.max_portfolio_risk_pct
          )
        }
      }),
      MetricCardComponent.create({
        label: 'Pérdida Diaria',
        value: Utils.formatPercent(riskData.daily_loss_current),
        bar: {
          percent: Math.min(
            riskData.daily_loss_current / riskData.daily_loss_limit * 100,
            100
          ),
          color: getBarColor(riskData.daily_loss_current, riskData.daily_loss_limit)
        }
      }),
      MetricCardComponent.create({
        label: 'Drawdown',
        value: Utils.formatPercent(riskData.drawdown_current),
        bar: {
          percent: Math.min(
            riskData.drawdown_current / riskData.max_drawdown_pct * 100,
            100
          ),
          color: getBarColor(riskData.drawdown_current, riskData.max_drawdown_pct)
        }
      })
    ];

    cards.forEach(card => {
      riskMetrics.appendChild(card);
    });
  } catch (error) {
    console.error('Error loading risk metrics:', error);
  }
}

// ===== EJEMPLO 6: Mostrar modal de confirmación de orden =====
function showOrderConfirmationModal(orderData) {
  const content = document.createElement('div');
  content.innerHTML = `
    <div style="margin-bottom: 16px;">
      <div style="color: var(--text3); margin-bottom: 4px;">Símbolo</div>
      <div style="color: var(--text1); font-weight: 600;">${orderData.symbol}</div>
    </div>
    <div style="margin-bottom: 16px;">
      <div style="color: var(--text3); margin-bottom: 4px;">Lado</div>
      <div style="display: flex; gap: 8px;">
        ${BadgeComponent.create(orderData.side, orderData.side === 'BUY' ? 'buy' : 'sell').outerHTML}
      </div>
    </div>
    <div style="margin-bottom: 16px;">
      <div style="color: var(--text3); margin-bottom: 4px;">Entrada</div>
      <div style="color: var(--text1); font-weight: 600;">${Utils.formatCurrency(orderData.entry)}</div>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
      <div>
        <div style="color: var(--text3); margin-bottom: 4px;">S/L</div>
        <div style="color: var(--red);">${Utils.formatCurrency(orderData.sl)}</div>
      </div>
      <div>
        <div style="color: var(--text3); margin-bottom: 4px;">T/P</div>
        <div style="color: var(--green);">${Utils.formatCurrency(orderData.tp)}</div>
      </div>
    </div>
  `;

  const modal = ModalComponent.create({
    title: 'Confirmar Orden',
    content: content,
    onClose: () => {
      api.execution.placeOrder(orderData).then(() => {
        ToastComponent.show({
          message: 'Orden executada',
          type: 'success'
        });
      }).catch(error => {
        ToastComponent.show({
          message: `Error: ${error.message}`,
          type: 'error'
        });
      });
    }
  });

  ModalComponent.show(modal.id);
}

// ===== EJEMPLO 7: Debounce búsqueda de símbolos =====
const searchSymbols = Utils.debounce(async (query) => {
  if (!query) return;

  const symbols = ['EURUSD', 'GBPUSD', 'XAUUSD', 'US500', 'US30', 'USDJPY'];
  const filtered = symbols.filter(s =>
    s.toLowerCase().includes(query.toLowerCase())
  );

  const container = document.getElementById('searchResults');
  container.innerHTML = '';

  filtered.forEach(symbol => {
    const btn = document.createElement('button');
    btn.className = 'symbol-btn';
    btn.textContent = symbol;
    btn.onclick = () => {
      loadMarketData(symbol);
      container.innerHTML = '';
    };
    container.appendChild(btn);
  });
}, 300);

// ===== USO EN HTML =====
/*
<div id="signals-section">
  <h2 class="section-title">Señales Recientes</h2>
  <div id="signalsContainer"></div>
  <button onclick="loadSignalsWithComponents()" class="btn btn-primary">
    Cargar Señales
  </button>
</div>

<div id="portfolio-section">
  <h2 class="section-title">Portfolio</h2>
  <div class="grid4" id="portfolioMetrics"></div>
  <button onclick="loadPortfolioMetricsWithComponents()" class="btn btn-primary">
    Cargar Métricas
  </button>
</div>

<div id="agents-section">
  <h2 class="section-title">Agentes IA</h2>
  <div id="agentRows"></div>
  <button onclick="loadAgentsWithComponents('EURUSD')" class="btn btn-primary">
    Cargar Agentes
  </button>
</div>

<div id="risk-section">
  <h2 class="section-title">Riesgo</h2>
  <div class="grid4" id="riskMetrics"></div>
  <button onclick="loadRiskMetricsWithComponents()" class="btn btn-primary">
    Cargar Métricas de Riesgo
  </button>
</div>

<div id="search-section">
  <input
    type="text"
    placeholder="Buscar símbolo..."
    onkeyup="searchSymbols(this.value)"
    style="padding: 8px; border-radius: 4px;"
  />
  <div id="searchResults"></div>
</div>
*/
