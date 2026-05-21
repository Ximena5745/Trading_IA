// indicators-config.js
// Phase 3: Indicator registry for TRADER·IA dashboard
// Author: Copilot (2026)

const INDICATORS = {
  RSI: {
    name: 'RSI',
    color: '#f5a623',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 14 }],
    yAxis: 'secondary',
    min: 0,
    max: 100
  },
  MACD: {
    name: 'MACD',
    colors: { line: '#00d9ff', signal: '#ff6b6b', histogram: '#4ecdc4' },
    params: [
      { key: 'fast', label: 'Fast EMA', type: 'number', min: 2, max: 50, default: 12 },
      { key: 'slow', label: 'Slow EMA', type: 'number', min: 2, max: 100, default: 26 },
      { key: 'signal', label: 'Signal', type: 'number', min: 2, max: 30, default: 9 }
    ],
    yAxis: 'secondary'
  },
  BB: {
    name: 'Bollinger Bands',
    colors: { upper: '#ff4757', middle: '#a4b0bd', lower: '#00d084' },
    params: [
      { key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 20 },
      { key: 'stdDev', label: 'Std Dev', type: 'number', min: 1, max: 5, default: 2 }
    ],
    yAxis: 'main'
  },
  ATR: {
    name: 'ATR',
    color: '#ff4757',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 14 }],
    yAxis: 'secondary'
  },
  EMA: {
    name: 'EMA',
    colors: { ema9: '#3d8ef8', ema21: '#a78bfa' },
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 9 }],
    yAxis: 'main'
  },
  SMA: {
    name: 'SMA',
    color: '#ff9f43',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 20 }],
    yAxis: 'main'
  },
  ROC: {
    name: 'ROC',
    color: '#a29bfe',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 12 }],
    yAxis: 'secondary'
  },
  Stochastic: {
    name: 'Stochastic',
    colors: { k: '#fd79a8', d: '#74b9ff' },
    params: [
      { key: 'k', label: '%K', type: 'number', min: 2, max: 50, default: 14 },
      { key: 'd', label: '%D', type: 'number', min: 2, max: 50, default: 3 }
    ],
    yAxis: 'secondary',
    min: 0,
    max: 100
  },
  CCI: {
    name: 'CCI',
    color: '#74b9ff',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 20 }],
    yAxis: 'secondary'
  },
  ADX: {
    name: 'ADX',
    color: '#fab1a0',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 14 }],
    yAxis: 'secondary',
    min: 0,
    max: 100
  },
  VWAP: {
    name: 'VWAP',
    color: '#00cec9',
    params: [],
    yAxis: 'main'
  },
  Ichimoku: {
    name: 'Ichimoku',
    color: '#6c5ce7',
    params: [
      { key: 'tenkan', label: 'Tenkan', type: 'number', min: 2, max: 20, default: 9 },
      { key: 'kijun', label: 'Kijun', type: 'number', min: 2, max: 30, default: 26 },
      { key: 'senkou', label: 'Senkou', type: 'number', min: 2, max: 60, default: 52 }
    ],
    yAxis: 'main'
  },
  OBV: {
    name: 'OBV',
    color: '#fdcb6e',
    params: [],
    yAxis: 'secondary'
  },
  MFI: {
    name: 'MFI',
    color: '#e17055',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 14 }],
    yAxis: 'secondary',
    min: 0,
    max: 100
  },
  WilliamsR: {
    name: 'Williams %R',
    color: '#0984e3',
    params: [{ key: 'period', label: 'Period', type: 'number', min: 2, max: 50, default: 14 }],
    yAxis: 'secondary',
    min: -100,
    max: 0
  }
};

function getIndicatorConfig(key) {
  return INDICATORS[key];
}

window.INDICATORS = INDICATORS;
window.getIndicatorConfig = getIndicatorConfig;
