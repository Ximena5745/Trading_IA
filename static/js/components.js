/**
 * Reusable Components for TRADER·IA Dashboard
 * Encapsulates common patterns and API interactions
 */

// ===== API CLIENT =====
class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL || '';
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  // Market endpoints
  market = {
    getMarketData: (symbol, timeframe) =>
      this.request(`/api/market/${symbol}/${timeframe}`),
    getMarketDataBatch: (symbols, timeframe) =>
      this.request(`/api/market/batch/${timeframe}`, {
        method: 'POST',
        body: JSON.stringify({ symbols }),
      }),
    getFeaturesCache: () => this.request('/api/market/features'),
    getRegimeCache: () => this.request('/api/market/regime'),
  };

  // Signals endpoints
  signals = {
    getSignals: (symbol) => this.request(`/api/signals/${symbol}`),
    getSignalsBatch: (symbols) =>
      this.request('/api/signals/batch', {
        method: 'POST',
        body: JSON.stringify({ symbols }),
      }),
    getConsensus: (symbol) => this.request(`/api/signals/${symbol}/consensus`),
  };

  // Portfolio endpoints
  portfolio = {
    getPortfolio: () => this.request('/api/portfolio'),
    getPositions: () => this.request('/api/portfolio/positions'),
    getEquityCurve: () => this.request('/api/portfolio/equity-curve'),
    getMetrics: () => this.request('/api/portfolio/metrics'),
  };

  // Risk endpoints
  risk = {
    getRiskMetrics: () => this.request('/api/risk/metrics'),
    getKillSwitchStatus: () => this.request('/api/risk/kill-switch'),
    getLimits: () => this.request('/api/risk/limits'),
    getExposure: () => this.request('/api/risk/exposure'),
  };

  // Execution endpoints
  execution = {
    getOrders: () => this.request('/api/execution/orders'),
    getOrder: (orderId) => this.request(`/api/execution/orders/${orderId}`),
    placeOrder: (orderData) =>
      this.request('/api/execution/orders', {
        method: 'POST',
        body: JSON.stringify(orderData),
      }),
    cancelOrder: (orderId) =>
      this.request(`/api/execution/orders/${orderId}`, { method: 'DELETE' }),
  };
}

// ===== BADGE COMPONENT =====
class BadgeComponent {
  static create(text, type = 'hold') {
    const badge = document.createElement('span');
    badge.className = `badge badge-${type}`;
    badge.textContent = text;
    return badge;
  }

  static createSignalBadges(signal) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.gap = '4px';

    const signalBadge = this.create(signal.toUpperCase(), signal.toLowerCase());
    container.appendChild(signalBadge);

    return container;
  }
}

// ===== METRIC CARD COMPONENT =====
class MetricCardComponent {
  static create({ label, value, sub = '', bar = null, color = null }) {
    const card = document.createElement('div');
    card.className = 'metric-card';

    const labelEl = document.createElement('div');
    labelEl.className = 'metric-label';
    labelEl.textContent = label;
    card.appendChild(labelEl);

    const valueEl = document.createElement('div');
    valueEl.className = 'metric-value';
    if (color) valueEl.style.color = color;
    valueEl.textContent = value;
    card.appendChild(valueEl);

    if (sub) {
      const subEl = document.createElement('div');
      subEl.className = 'metric-sub';
      subEl.textContent = sub;
      card.appendChild(subEl);
    }

    if (bar) {
      const barEl = document.createElement('div');
      barEl.className = 'metric-bar';
      const fillEl = document.createElement('div');
      fillEl.className = 'metric-bar-fill';
      if (bar.color) fillEl.style.background = bar.color;
      fillEl.style.width = `${bar.percent}%`;
      barEl.appendChild(fillEl);
      card.appendChild(barEl);
    }

    return card;
  }

  static createGrid(metrics) {
    const container = document.createElement('div');
    container.className = 'grid4';

    metrics.forEach((metric) => {
      container.appendChild(this.create(metric));
    });

    return container;
  }
}

// ===== AGENT ROW COMPONENT =====
class AgentRowComponent {
  static create({ name, score, status = 'neutral' }) {
    const row = document.createElement('div');
    row.className = 'agent-row';

    const dot = document.createElement('div');
    dot.className = 'agent-dot';
    dot.style.background = this.getStatusColor(status);
    row.appendChild(dot);

    const nameEl = document.createElement('div');
    nameEl.className = 'agent-name';
    nameEl.textContent = name;
    row.appendChild(nameEl);

    const barContainer = document.createElement('div');
    barContainer.className = 'agent-score-bar';
    const barFill = document.createElement('div');
    barFill.className = 'agent-score-fill';
    barFill.style.background = this.getStatusColor(status);
    barFill.style.width = `${Math.max(0, Math.min(100, score * 100))}%`;
    barContainer.appendChild(barFill);
    row.appendChild(barContainer);

    const valueEl = document.createElement('div');
    valueEl.className = 'agent-value';
    valueEl.textContent = score.toFixed(2);
    row.appendChild(valueEl);

    return row;
  }

  static getStatusColor(status) {
    const colors = {
      bullish: 'var(--green)',
      bearish: 'var(--red)',
      sideways: 'var(--amber)',
      neutral: 'var(--text3)',
      positive: 'var(--green)',
      negative: 'var(--red)',
    };
    return colors[status] || 'var(--text3)';
  }

  static createList(agents) {
    const container = document.createElement('div');

    agents.forEach((agent) => {
      container.appendChild(this.create(agent));
    });

    return container;
  }
}

// ===== TABLE COMPONENT =====
class TableComponent {
  static create({ headers, rows, className = 'signal-table' }) {
    const table = document.createElement('table');
    table.className = className;

    // Header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headers.forEach((header) => {
      const th = document.createElement('th');
      th.textContent = header;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    rows.forEach((row) => {
      const tr = document.createElement('tr');
      Object.values(row).forEach((cell) => {
        const td = document.createElement('td');
        if (typeof cell === 'string') {
          td.textContent = cell;
        } else {
          td.appendChild(cell);
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    return table;
  }
}

// ===== CHART HELPER =====
class ChartHelper {
  static formatLayout(title, subtitle = '') {
    return {
      title: {
        text: subtitle ? `${title} · ${subtitle}` : title,
        font: { family: "'JetBrains Mono', monospace", size: 13, color: '#e8edf5' },
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: '#151a22',
      margin: { l: 40, r: 20, t: 30, b: 30 },
      hovermode: 'x unified',
      xaxis: {
        color: '#4d5a70',
        gridcolor: 'rgba(255,255,255,0.07)',
      },
      yaxis: {
        color: '#4d5a70',
        gridcolor: 'rgba(255,255,255,0.07)',
      },
      font: { family: "'JetBrains Mono', monospace", color: '#8c99b0' },
    };
  }

  static formatConfig() {
    return {
      responsive: true,
      displayModeBar: false,
      displaylogo: false,
    };
  }

  static getCandleTrace(data) {
    return {
      x: data.map((d) => d.date),
      open: data.map((d) => d.open),
      high: data.map((d) => d.high),
      low: data.map((d) => d.low),
      close: data.map((d) => d.close),
      type: 'candlestick',
      increasing: { fillcolor: '#00d084', line: { color: '#00d084' } },
      decreasing: { fillcolor: '#ff4757', line: { color: '#ff4757' } },
      hoverinfo: 'x<br>Open: %{open}<br>High: %{high}<br>Low: %{low}<br>Close: %{close}',
    };
  }

  static getLineTrace(data, name, color) {
    return {
      x: data.map((d) => d.date),
      y: data.map((d) => d.value),
      type: 'scatter',
      mode: 'lines',
      name: name,
      line: { color: color, width: 2 },
      hovertemplate: `<b>${name}</b><br>%{x}<br>%{y:.4f}<extra></extra>`,
    };
  }

  static getBarTrace(data, name, color, textposition = 'outside') {
    return {
      x: data.map((d) => d.label),
      y: data.map((d) => d.value),
      type: 'bar',
      name: name,
      marker: { color: color },
      hovertemplate: '<b>%{x}</b><br>%{y:.4f}<extra></extra>',
      textposition: textposition,
      text: data.map((d) => d.value.toFixed(2)),
    };
  }
}

// ===== GAUGE COMPONENT =====
class GaugeComponent {
  static updateCircularGauge(svgId, value, max = 100, label = '') {
    const svg = document.getElementById(svgId);
    if (!svg) return;

    const circumference = 2 * Math.PI * 45; // r=45
    const offset = circumference - (Math.abs(value) / max) * circumference;

    const arc = svg.querySelector('#gaugeArc');
    if (arc) {
      arc.setAttribute('stroke-dashoffset', offset);
      arc.setAttribute('stroke', value >= 0 ? 'var(--green)' : 'var(--red)');
    }

    const text = svg.querySelector('#gaugeText');
    if (text) {
      text.textContent = value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
      text.setAttribute('fill', value >= 0 ? 'var(--green)' : 'var(--red)');
    }
  }
}

// ===== PROGRESS BAR COMPONENT =====
class ProgressBarComponent {
  static create({ value, max = 100, color = 'var(--green)', label = '' }) {
    const container = document.createElement('div');
    container.style.marginBottom = '8px';

    if (label) {
      const labelEl = document.createElement('div');
      labelEl.style.fontSize = '10px';
      labelEl.style.color = 'var(--text3)';
      labelEl.style.marginBottom = '4px';
      labelEl.textContent = label;
      container.appendChild(labelEl);
    }

    const bar = document.createElement('div');
    bar.className = 'progress-bar';
    const fill = document.createElement('div');
    fill.className = 'progress-fill';
    fill.style.background = color;
    fill.style.width = `${Math.min(100, (value / max) * 100)}%`;
    bar.appendChild(fill);
    container.appendChild(bar);

    return container;
  }
}

// ===== POSITION ROW COMPONENT =====
class PositionRowComponent {
  static create({ symbol, quantity, pnl, status = 'open' }) {
    const row = document.createElement('div');
    row.className = 'position-row';

    const dot = document.createElement('div');
    dot.className = 'position-dot';
    dot.style.background = pnl >= 0 ? 'var(--green)' : 'var(--red)';
    row.appendChild(dot);

    const symbolEl = document.createElement('div');
    symbolEl.className = 'position-symbol';
    symbolEl.textContent = symbol;
    row.appendChild(symbolEl);

    const qtyEl = document.createElement('div');
    qtyEl.className = 'position-qty';
    qtyEl.textContent = quantity;
    row.appendChild(qtyEl);

    const pnlEl = document.createElement('div');
    pnlEl.className = 'position-pnl';
    pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';
    pnlEl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
    row.appendChild(pnlEl);

    return row;
  }

  static createList(positions) {
    const container = document.createElement('div');

    if (!positions || positions.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-state-text';
      empty.textContent = 'No open positions';
      container.appendChild(empty);
      return container;
    }

    positions.forEach((pos) => {
      container.appendChild(this.create(pos));
    });

    return container;
  }
}

// ===== SHAP VALUES COMPONENT =====
class ShapComponent {
  static createBar({ label, positive, negative, value }) {
    const row = document.createElement('div');
    row.className = 'shap-row';

    const labelEl = document.createElement('div');
    labelEl.className = 'shap-label';
    labelEl.textContent = label;
    row.appendChild(labelEl);

    const track = document.createElement('div');
    track.className = 'shap-track';

    if (positive > 0) {
      const posFill = document.createElement('div');
      posFill.className = 'shap-fill-pos';
      posFill.style.width = `${positive * 50}%`;
      track.appendChild(posFill);
    }

    if (negative > 0) {
      const negFill = document.createElement('div');
      negFill.className = 'shap-fill-neg';
      negFill.style.width = `${negative * 50}%`;
      track.appendChild(negFill);
    }

    row.appendChild(track);

    const valueEl = document.createElement('div');
    valueEl.className = 'shap-value';
    valueEl.textContent = value.toFixed(3);
    row.appendChild(valueEl);

    return row;
  }

  static createSummary(text) {
    const summary = document.createElement('div');
    summary.className = 'xai-summary';

    const label = document.createElement('div');
    label.className = 'xai-summary-label';
    label.textContent = 'Resumen XAI';
    summary.appendChild(label);

    const textEl = document.createElement('div');
    textEl.className = 'xai-summary-text';
    textEl.textContent = text;
    summary.appendChild(textEl);

    return summary;
  }
}

// ===== MODAL COMPONENT =====
class ModalComponent {
  static create({ title, content, onClose = null }) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = `modal-${Date.now()}`;

    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';

    const header = document.createElement('div');
    header.className = 'modal-header';

    const titleEl = document.createElement('h2');
    titleEl.className = 'modal-title';
    titleEl.textContent = title;
    header.appendChild(titleEl);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close';
    closeBtn.textContent = '×';
    closeBtn.onclick = () => {
      modal.classList.remove('active');
      if (onClose) onClose();
    };
    header.appendChild(closeBtn);

    modalContent.appendChild(header);

    const body = document.createElement('div');
    body.className = 'modal-body';
    if (typeof content === 'string') {
      body.innerHTML = content;
    } else {
      body.appendChild(content);
    }
    modalContent.appendChild(body);

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // Close on outside click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
        if (onClose) onClose();
      }
    });

    return modal;
  }

  static show(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
  }

  static hide(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
  }
}

// ===== LOADING STATE COMPONENT =====
class LoadingComponent {
  static create() {
    const container = document.createElement('div');
    container.className = 'loading';
    container.textContent = 'Loading...';
    return container;
  }

  static createSkeleton(lines = 3) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '8px';

    for (let i = 0; i < lines; i++) {
      const skeleton = document.createElement('div');
      skeleton.style.height = '20px';
      skeleton.style.background = 'var(--bg3)';
      skeleton.style.borderRadius = '4px';
      skeleton.style.animation = 'pulse 2s infinite';
      container.appendChild(skeleton);
    }

    return container;
  }
}

// ===== TOAST NOTIFICATION COMPONENT =====
class ToastComponent {
  static show({ message, type = 'info', duration = 3000 }) {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '12px 16px';
    toast.style.borderRadius = '6px';
    toast.style.zIndex = '9999';
    toast.style.animation = 'slideIn 0.3s ease';
    toast.style.fontFamily = "'JetBrains Mono', monospace";
    toast.style.fontSize = '12px';

    const colorMap = {
      success: { bg: 'var(--green2)', color: 'var(--green)' },
      error: { bg: 'var(--red2)', color: 'var(--red)' },
      warning: { bg: 'var(--amber2)', color: 'var(--amber)' },
      info: { bg: 'var(--blue2)', color: 'var(--blue)' },
    };

    const colors = colorMap[type] || colorMap.info;
    toast.style.background = colors.bg;
    toast.style.color = colors.color;
    toast.style.border = `1px solid ${colors.color}`;

    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'fadeOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
}

// ===== UTILITY FUNCTIONS =====
const Utils = {
  formatCurrency: (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  },

  formatPercent: (value) => {
    return `${(value * 100).toFixed(2)}%`;
  },

  formatNumber: (value, decimals = 2) => {
    return Number(value).toFixed(decimals);
  },

  getStatusColor: (status) => {
    const colors = {
      up: 'var(--green)',
      down: 'var(--red)',
      neutral: 'var(--text3)',
      buy: 'var(--green)',
      sell: 'var(--red)',
      hold: 'var(--amber)',
    };
    return colors[status] || 'var(--text2)';
  },

  debounce: (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  throttle: (func, limit) => {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), limit);
      }
    };
  },

  delay: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
};

// ===== EXPORT =====
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    APIClient,
    BadgeComponent,
    MetricCardComponent,
    AgentRowComponent,
    TableComponent,
    ChartHelper,
    GaugeComponent,
    ProgressBarComponent,
    PositionRowComponent,
    ShapComponent,
    ModalComponent,
    LoadingComponent,
    ToastComponent,
    Utils,
  };
}
