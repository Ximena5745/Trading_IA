// lightweight-charts-manager.js
// Gestor de gráficos de trading con Lightweight Charts (TradingView)
// Reemplaza Plotly para mejor rendimiento con grandes datasets

class LightweightChartsManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
        this.candlestickSeries = null;
        this.lineSeries = {}; // Para EMAs, SMAs, indicadores
        this.currentData = [];
        this.selectedIndicators = {};
        this.isInitialized = false;
        console.log(`[LWC] Manager created for container: ${containerId}`);
    }

    initialize() {
        // Verificar que LightweightCharts esté disponible
        const LWC = window.LightweightCharts || window.lightweightCharts;
        if (!LWC) {
            console.error('[LWC] LightweightCharts not available in window');
            console.error('[LWC] Available: window.LightweightCharts =', window.LightweightCharts);
            console.error('[LWC] Available: window.lightweightCharts =', window.lightweightCharts);
            return false;
        }
        console.log('[LWC] LightweightCharts library found');

        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`[LWC] Container ${this.containerId} not found`);
            return false;
        }
        console.log(`[LWC] Container found, dimensions: ${container.clientWidth}x${container.clientHeight}`);

        // Asegurar que el contenedor tenga dimensiones
        if (container.clientWidth === 0 || container.clientHeight === 0) {
            console.warn('[LWC] Container has 0 dimensions, setting defaults');
            container.style.width = '100%';
            container.style.height = '300px';
        }

        try {
            // Limpiar contenedor anterior si existe
            container.innerHTML = '';
            
            console.log('[LWC] Creating chart instance...');
            // Crear gráfico
            const createChart = LWC.createChart || LWC.default.createChart;
            if (!createChart) {
                console.error('[LWC] createChart function not found');
                console.log('[LWC] LWC object keys:', Object.keys(LWC));
                return false;
            }

            this.chart = createChart(container, {
                layout: {
                    background: { color: '#151a22' },
                    textColor: '#8c99b0',
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono'
                },
                width: container.clientWidth,
                height: container.clientHeight || 300,
                timeScale: {
                    timeVisible: true,
                    secondsVisible: false,
                    rightOffset: 12,
                    barSpacing: 6,
                    lockVisibleTimeRangeOnResize: true
                },
                crosshair: {
                    mode: 1, // Magnet mode
                    vertLine: { color: '#404854', width: 1, style: 1 },
                    horzLine: { color: '#404854', width: 1, style: 1 }
                },
                watermark: {
                    visible: false
                }
            });
            console.log('[LWC] Chart instance created');

            // Crear serie de candlesticks
            const addCandlestickSeries = this.chart.addCandlestickSeries;
            if (!addCandlestickSeries) {
                console.error('[LWC] addCandlestickSeries method not found');
                console.log('[LWC] Chart methods:', Object.getOwnPropertyNames(this.chart));
                return false;
            }

            this.candlestickSeries = this.chart.addCandlestickSeries({
                upColor: '#00d084',
                downColor: '#ff4757',
                borderDownColor: '#ff4757',
                borderUpColor: '#00d084',
                wickDownColor: '#ff4757',
                wickUpColor: '#00d084',
                priceFormat: {
                    type: 'price',
                    precision: 4,
                    minMove: 0.0001
                }
            });
            console.log('[LWC] Candlestick series added');

            // Ajustar dimensiones al redimensionar
            this.handleWindowResize();
            this.isInitialized = true;
            console.log('[LWC] Manager initialized successfully ✓');
            return true;
        } catch (error) {
            console.error('[LWC] Initialization failed:', error);
            console.error('[LWC] Stack:', error.stack);
            return false;
        }
    }

    handleWindowResize() {
        window.addEventListener('resize', () => {
            if (this.chart) {
                const container = document.getElementById(this.containerId);
                if (container) {
                    this.chart.applyOptions({
                        width: container.clientWidth,
                        height: container.clientHeight || 300
                    });
                }
            }
        });
    }

    loadData(data) {
        if (!this.chart || !this.candlestickSeries) {
            console.error('[LWC] Chart not initialized');
            return;
        }

        if (!data || data.length === 0) {
            console.error('[LWC] No data provided');
            return;
        }
        
        console.log(`[LWC] Loading ${data.length} candles...`);
        this.currentData = data;
        
        // Convertir timestamp ISO o fecha a unix time
        const convertToUnixTime = (ts) => {
            if (typeof ts === 'number') return ts; // Ya es unix time
            if (ts instanceof Date) return Math.floor(ts.getTime() / 1000);
            if (typeof ts === 'string') {
                try {
                    return Math.floor(new Date(ts).getTime() / 1000);
                } catch (e) {
                    console.warn(`[LWC] Invalid timestamp: ${ts}`, e);
                    return null;
                }
            }
            return null;
        };

        try {
            // Formatear datos para Lightweight Charts
            const formattedData = data.map((candle, idx) => {
                const unixTime = convertToUnixTime(candle.timestamp);
                if (!unixTime) {
                    console.warn(`[LWC] Skipping candle ${idx}: invalid timestamp`, candle.timestamp);
                    return null;
                }
                return {
                    time: unixTime,
                    open: parseFloat(candle.open) || 0,
                    high: parseFloat(candle.high) || 0,
                    low: parseFloat(candle.low) || 0,
                    close: parseFloat(candle.close) || 0
                };
            }).filter(c => c !== null);

            if (formattedData.length === 0) {
                console.error('[LWC] No valid candlestick data after formatting');
                return;
            }

            console.log(`[LWC] Formatted ${formattedData.length} valid candles (${data.length - formattedData.length} skipped)`);
            console.log('[LWC] Sample candle:', formattedData[0]);

            // Cargar candlesticks
            this.candlestickSeries.setData(formattedData);
            console.log('[LWC] Data set on candlestick series');
            
            // Fit content
            this.chart.timeScale().fitContent();
            console.log('[LWC] Time scale fitted ✓');
        } catch (error) {
            console.error('[LWC] Error loading data:', error);
            console.error('[LWC] Stack:', error.stack);
        }
    }

    addEMA(periodLabel, emaseries, color) {
        if (!this.chart) return;
        
        if (!this.lineSeries[periodLabel]) {
            this.lineSeries[periodLabel] = this.chart.addLineSeries({
                color: color,
                lineWidth: 2,
                title: periodLabel,
                priceFormat: {
                    type: 'price',
                    precision: 4,
                    minMove: 0.0001
                }
            });
        }

        // Formatear datos EMA
        const formattedEMA = this.currentData.map((candle, i) => ({
            time: new Date(candle.timestamp).getTime() / 1000,
            value: emaseries[i]
        })).filter(item => item.value !== undefined && item.value !== null);

        this.lineSeries[periodLabel].setData(formattedEMA);
    }

    addIndicatorLine(name, values, color, isSecondaryAxis = false) {
        if (!this.chart || !this.currentData) return;
        
        if (!this.lineSeries[name]) {
            this.lineSeries[name] = this.chart.addLineSeries({
                color: color,
                lineWidth: 1.5,
                title: name,
                priceFormat: {
                    type: 'price',
                    precision: 4,
                    minMove: 0.0001
                }
            });
        }

        const formattedData = this.currentData.map((candle, i) => ({
            time: new Date(candle.timestamp).getTime() / 1000,
            value: values[i]
        })).filter(item => item.value !== undefined && item.value !== null);

        this.lineSeries[name].setData(formattedData);
    }

    removeSeries(name) {
        if (this.lineSeries[name] && this.chart) {
            this.chart.removeSeries(this.lineSeries[name]);
            delete this.lineSeries[name];
        }
    }

    clearAllSeries() {
        for (let key in this.lineSeries) {
            if (this.chart) {
                this.chart.removeSeries(this.lineSeries[key]);
            }
            delete this.lineSeries[key];
        }
    }

    updateColor(seriesName, color) {
        if (this.lineSeries[seriesName]) {
            this.lineSeries[seriesName].applyOptions({ color: color });
        }
    }

    syncCharts(otherChartId) {
        if (!this.chart) return;
        
        const timeScale = this.chart.timeScale();
        timeScale.subscribeVisibleTimeRangeChange(() => {
            const visibleRange = timeScale.getVisibleRange();
            if (visibleRange && window.chartsSync) {
                window.chartsSync(visibleRange);
            }
        });
    }

    fitContent() {
        if (this.chart) {
            this.chart.timeScale().fitContent();
        }
    }

    takeScreenshot() {
        if (this.chart) {
            return this.chart.takeScreenshot();
        }
    }

    destroy() {
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
        }
    }
}

// Exportar para uso global
window.LightweightChartsManager = LightweightChartsManager;
