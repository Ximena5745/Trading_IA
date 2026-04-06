"""
Module: api/routes/dashboard.py
Responsibility: Serve crypto validation dashboard with real data
Dependencies: FastAPI
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pathlib import Path
import json

from api.dependencies import require_trader

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _load_dashboard_html() -> str:
    """Load dashboard HTML with validation data"""
    results_dir = Path("backtest_results")
    val_file = results_dir / "comprehensive_validation.json"
    
    # Load validation data
    validation_data = {}
    if val_file.exists():
        try:
            with open(val_file, 'r') as f:
                validation_data = json.load(f)
        except Exception as e:
            validation_data = {"error": f"Failed to load data: {str(e)}"}
    else:
        validation_data = {"error": "comprehensive_validation.json not found"}
    
    # Convert to JavaScript-safe JSON
    validation_json = json.dumps(validation_data)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Trading Validation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Syne', sans-serif;
            background: linear-gradient(135deg, #0a0d11 0%, #1c2330 100%);
            color: #e8edf5;
            padding: 20px;
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            padding-bottom: 20px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #e8edf5;
            font-weight: 700;
        }}
        
        .header p {{
            opacity: 0.7;
            margin-bottom: 15px;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.95em;
            font-weight: 600;
            background-color: #00d084;
            color: #0a0d11;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }}
        
        .card:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.15);
        }}
        
        .card h2 {{
            font-size: 1.3em;
            margin-bottom: 15px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            padding-bottom: 10px;
            font-weight: 700;
        }}
        
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .metric:last-child {{
            border-bottom: none;
        }}
        
        .metric-label {{
            font-size: 0.95em;
            opacity: 0.7;
        }}
        
        .metric-value {{
            font-size: 1.1em;
            font-weight: 700;
            color: #00d084;
            text-align: right;
        }}
        
        .metric-value.status {{
            color: #00d084;
            background: rgba(0, 208, 132, 0.15);
            padding: 4px 12px;
            border-radius: 4px;
        }}
        
        .chart-container {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
            margin-bottom: 20px;
        }}
        
        .chart-container h2 {{
            margin-bottom: 20px;
            font-size: 1.3em;
            font-weight: 700;
        }}
        
        .warning-box {{
            background: rgba(245, 166, 35, 0.1);
            border: 2px solid rgba(245, 166, 35, 0.5);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .warning-title {{
            font-weight: 700;
            color: #f5a623;
            margin-bottom: 12px;
            font-size: 1.05em;
        }}
        
        .warning-item {{
            margin-bottom: 8px;
            padding-left: 20px;
            opacity: 0.95;
        }}
        
        .timestamp {{
            opacity: 0.6;
            font-size: 0.9em;
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-family: 'JetBrains Mono', monospace;
        }}

        .error-box {{
            background: rgba(255, 100, 100, 0.1);
            border: 2px solid rgba(255, 100, 100, 0.5);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            color: #ff6464;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>🚀 CRYPTO TRADING VALIDATION DASHBOARD</h1>
            <p>Walk-Forward Analysis with Realistic Transaction Costs</p>
            <span class="status-badge">✓ LIVE ENDPOINT</span>
        </div>

        <!-- ERROR BOX (if data loading fails) -->
        <div id="errorBox" style="display:none;" class="error-box"></div>

        <!-- WARNINGS -->
        <div class="warning-box" id="warningsContainer" style="display:none;">
            <div class="warning-title">⚠️ Critical Findings</div>
            <div id="warningsContent"></div>
        </div>

        <!-- SUMMARY CARDS -->
        <div class="grid">
            <div class="card" id="btcCard">Loading BTCUSDT...</div>
            <div class="card" id="ethCard">Loading ETHUSDT...</div>
            <div class="card" id="summaryCard">Loading Summary...</div>
        </div>

        <!-- CHARTS -->
        <div class="chart-container">
            <h2>💰 Realistic P&L (After Binance Fees + Slippage)</h2>
            <canvas id="pnlChart"></canvas>
        </div>

        <div class="chart-container">
            <h2>📊 Quality Metrics Comparison</h2>
            <canvas id="metricsChart"></canvas>
        </div>

        <div class="timestamp">
            <strong>Last Updated:</strong> <span id="timestamp">Loading...</span><br>
            <small>Data Source: backtest_results/comprehensive_validation.json</small>
        </div>
    </div>

    <script>
        // Load data directly from server
        const validationData = JSON.parse('{validation_json}');
        
        function renderDashboard() {{
            // Check for errors
            if (validationData.error) {{
                document.getElementById('errorBox').style.display = 'block';
                document.getElementById('errorBox').innerHTML = `
                    <strong>❌ Error Loading Data:</strong><br>
                    ${{validationData.error}}
                `;
                return;
            }}
            
            const results = validationData.results || {{}};
            
            // Check if results exist
            if (Object.keys(results).length === 0) {{
                document.getElementById('errorBox').style.display = 'block';
                document.getElementById('errorBox').innerHTML = `
                    <strong>❌ No Results Found:</strong><br>
                    The validation data is empty. Please run the backtesting pipeline first.
                `;
                return;
            }}
            
            // Render symbol cards
            ['BTCUSDT', 'ETHUSDT'].forEach(symbol => {{
                const cardId = symbol === 'BTCUSDT' ? 'btcCard' : 'ethCard';
                const data = results[symbol] || {{}};
                renderSymbolCard(cardId, symbol, data);
            }});
            
            // Render summary
            renderSummaryCard(results);
            
            // Render warnings
            renderWarnings(results);
            
            // Render charts
            setTimeout(() => renderCharts(results), 100);
            
            // Timestamp
            if (validationData.timestamp) {{
                const dt = new Date(validationData.timestamp);
                document.getElementById('timestamp').textContent = dt.toLocaleString();
            }}
        }}

        function renderSymbolCard(cardId, symbol, data) {{
            if (!data || !data.realistic_return) {{
                document.getElementById(cardId).innerHTML = `<h2>${{symbol}}</h2><p>No data available</p>`;
                return;
            }}

            const html = `
                <h2>${{symbol}}</h2>
                <div class="metric">
                    <span class="metric-label">Realistic Return</span>
                    <span class="metric-value">${{(data.realistic_return || 0).toFixed(0)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Win Rate</span>
                    <span class="metric-value">${{(data.win_rate || 0).toFixed(1)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Profit Factor</span>
                    <span class="metric-value">${{(data.profit_factor || 0).toFixed(2)}}x</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sharpe Ratio</span>
                    <span class="metric-value">${{(data.sharpe_ratio || 0).toFixed(2)}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Recovery Factor</span>
                    <span class="metric-value">${{(data.recovery_factor || 0).toFixed(0)}}x</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value status">${{data.status || 'UNKNOWN'}}</span>
                </div>
            `;
            document.getElementById(cardId).innerHTML = html;
        }}

        function renderSummaryCard(results) {{
            const btc = results.BTCUSDT || {{}};
            const eth = results.ETHUSDT || {{}};
            
            const avgReturn = ((btc.realistic_return || 0) + (eth.realistic_return || 0)) / 2;
            const avgWR = ((btc.win_rate || 0) + (eth.win_rate || 0)) / 2;
            const avgSharpe = ((btc.sharpe_ratio || 0) + (eth.sharpe_ratio || 0)) / 2;
            const approved = Object.values(results).filter(r => r.status === 'APPROVED').length;
            
            const html = `
                <h2>📊 Portfolio Summary</h2>
                <div class="metric">
                    <span class="metric-label">Average Return</span>
                    <span class="metric-value">${{avgReturn.toFixed(0)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Average Win Rate</span>
                    <span class="metric-value">${{avgWR.toFixed(1)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Average Sharpe</span>
                    <span class="metric-value">${{avgSharpe.toFixed(2)}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Models Approved</span>
                    <span class="metric-value status">${{approved}}/2</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Model Type</span>
                    <span class="metric-value">LightGBM</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Features</span>
                    <span class="metric-value">75 Technical</span>
                </div>
            `;
            document.getElementById('summaryCard').innerHTML = html;
        }}

        function renderWarnings(results) {{
            const warnings = [];
            
            Object.entries(results).forEach(([symbol, data]) => {{
                if (!data.win_rate) return;
                
                if (data.win_rate > 90) {{
                    warnings.push(
                        `<div class="warning-item">📌 ${{symbol}}: Win rate ${{data.win_rate.toFixed(1)}}% is very high — expect 60-70% in live trading (backtest bias)</div>`
                    );
                }}
                
                if (data.sharpe_ratio > 5) {{
                    warnings.push(
                        `<div class="warning-item">📌 ${{symbol}}: Sharpe ${{data.sharpe_ratio.toFixed(1)}} is excellent but may be optimistic</div>`
                    );
                }}
            }});
            
            if (warnings.length > 0) {{
                document.getElementById('warningsContainer').style.display = 'block';
                document.getElementById('warningsContent').innerHTML = warnings.join('');
            }}
        }}

        function renderCharts(results) {{
            const btc = results.BTCUSDT || {{}};
            const eth = results.ETHUSDT || {{}};
            
            // Only render if we have data
            if (!btc.realistic_pnl || !eth.realistic_pnl) {{
                console.warn('Missing PNL data for charts');
                return;
            }}
            
            try {{
                // P&L Chart
                const ctx1 = document.getElementById('pnlChart');
                if (ctx1) {{
                    new Chart(ctx1, {{
                        type: 'bar',
                        data: {{
                            labels: ['BTCUSDT', 'ETHUSDT'],
                            datasets: [{{
                                label: 'Realistic P&L ($)',
                                data: [btc.realistic_pnl || 0, eth.realistic_pnl || 0],
                                backgroundColor: ['rgba(0, 208, 132, 0.7)', 'rgba(61, 142, 248, 0.7)'],
                                borderColor: ['rgba(0, 208, 132, 1)', 'rgba(61, 142, 248, 1)'],
                                borderWidth: 2,
                                borderRadius: 4
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {{
                                legend: {{ labels: {{ color: '#e8edf5', font: {{ size: 12 }} }} }}
                            }},
                            scales: {{
                                y: {{
                                    ticks: {{ color: '#e8edf5' }},
                                    grid: {{ color: 'rgba(255,255,255,0.1)' }},
                                    beginAtZero: true
                                }},
                                x: {{
                                    ticks: {{ color: '#e8edf5' }},
                                    grid: {{ color: 'rgba(255,255,255,0.1)' }}
                                }}
                            }}
                        }}
                    }});
                }}
            }} catch (e) {{
                console.error('Error rendering P&L chart:', e);
            }}
            
            try {{
                // Metrics Radar Chart
                const ctx2 = document.getElementById('metricsChart');
                if (ctx2) {{
                    new Chart(ctx2, {{
                        type: 'radar',
                        data: {{
                            labels: ['Win Rate %', 'Profit Factor', 'Sharpe Ratio'],
                            datasets: [
                                {{
                                    label: 'BTCUSDT',
                                    data: [
                                        btc.win_rate || 0,
                                        (btc.profit_factor || 0) * 20,
                                        (btc.sharpe_ratio || 0) * 15
                                    ],
                                    borderColor: 'rgba(0, 208, 132, 1)',
                                    backgroundColor: 'rgba(0, 208, 132, 0.2)',
                                    borderWidth: 2,
                                    pointBackgroundColor: 'rgba(0, 208, 132, 1)',
                                    pointBorderColor: '#fff',
                                    pointBorderWidth: 2
                                }},
                                {{
                                    label: 'ETHUSDT',
                                    data: [
                                        eth.win_rate || 0,
                                        (eth.profit_factor || 0) * 20,
                                        (eth.sharpe_ratio || 0) * 15
                                    ],
                                    borderColor: 'rgba(61, 142, 248, 1)',
                                    backgroundColor: 'rgba(61, 142, 248, 0.2)',
                                    borderWidth: 2,
                                    pointBackgroundColor: 'rgba(61, 142, 248, 1)',
                                    pointBorderColor: '#fff',
                                    pointBorderWidth: 2
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {{
                                legend: {{ labels: {{ color: '#e8edf5', font: {{ size: 12 }} }} }}
                            }},
                            scales: {{
                                r: {{
                                    grid: {{ color: 'rgba(255,255,255,0.1)' }},
                                    ticks: {{ color: '#e8edf5' }},
                                    beginAtZero: true
                                }}
                            }}
                        }}
                    }});
                }}
            }} catch (e) {{
                console.error('Error rendering metrics chart:', e);
            }}
        }}

        // Load on page ready
        document.addEventListener('DOMContentLoaded', renderDashboard);
    </script>
</body>
</html>
"""
    return html_content


@router.get("/crypto", response_class=HTMLResponse)
async def get_crypto_dashboard_authenticated(_: dict = Depends(require_trader)):
    """
    Serve Crypto Trading Validation Dashboard (Authenticated)
    Requires Bearer token with TRADER role
    """
    return _load_dashboard_html()


@router.get("/crypto/public", response_class=HTMLResponse)
async def get_crypto_dashboard_public():
    """
    Serve Crypto Trading Validation Dashboard (Public - Development)
    No authentication required - for demo purposes only
    """
    return _load_dashboard_html()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Trading Validation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Syne', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0d11 0%, #1c2330 100%);
            color: #e8edf5;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            padding-bottom: 20px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #e8edf5;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            background-color: #00d084;
            color: #0a0d11;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }}
        
        .card h2 {{
            font-size: 1.2em;
            margin-bottom: 15px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            padding-bottom: 10px;
        }}
        
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .metric:last-child {{
            border-bottom: none;
        }}
        
        .metric-label {{
            font-size: 0.95em;
            opacity: 0.7;
        }}
        
        .metric-value {{
            font-size: 1.1em;
            font-weight: bold;
            color: #00d084;
        }}
        
        .chart-container {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
            margin-bottom: 20px;
        }}
        
        .chart-container h2 {{
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .warning-box {{
            background: rgba(245, 166, 35, 0.1);
            border: 2px solid rgba(245, 166, 35, 0.5);
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }}
        
        .warning-title {{
            font-weight: bold;
            color: #f5a623;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            opacity: 0.6;
            font-size: 0.9em;
            text-align: center;
            margin-top: 20px;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>🚀 CRYPTO TRADING VALIDATION</h1>
            <p>Walk-Forward Validated with Realistic Costs</p>
            <span class="status-badge">✓ DEPLOYMENT APPROVED</span>
        </div>

        <!-- WARNINGS -->
        <div class="warning-box" id="warningsContainer" style="display:none;">
            <div class="warning-title">⚠️ Important Findings</div>
            <div id="warningsContent"></div>
        </div>

        <!-- SUMMARY CARDS -->
        <div class="grid">
            <div class="card" id="btcCard"></div>
            <div class="card" id="ethCard"></div>
            <div class="card" id="summaryCard"></div>
        </div>

        <!-- CHARTS -->
        <div class="chart-container">
            <h2>📊 Realistic P&L Comparison</h2>
            <canvas id="pnlChart"></canvas>
        </div>

        <div class="chart-container">
            <h2>📈 Quality Metrics (Sharpe, Profit Factor)</h2>
            <canvas id="metricsChart"></canvas>
        </div>

        <div class="timestamp">
            Last updated: <span id="timestamp">Loading...</span>
        </div>
    </div>

    <script>
        // Load data directly from JSON
        const validationData = {validation_json};
        
        function renderDashboard() {{
            const results = validationData.results || {{}};
            
            // Render symbol cards
            ['BTCUSDT', 'ETHUSDT'].forEach(symbol => {{
                const cardId = symbol === 'BTCUSDT' ? 'btcCard' : 'ethCard';
                const data = results[symbol] || {{}};
                renderSymbolCard(cardId, symbol, data);
            }});
            
            // Render summary
            renderSummaryCard(results);
            
            // Render warnings
            renderWarnings(results);
            
            // Render charts
            renderCharts(results);
            
            // Timestamp
            document.getElementById('timestamp').textContent = 
                new Date(validationData.timestamp).toLocaleString();
        }}

        function renderSymbolCard(cardId, symbol, data) {{
            const html = `
                <h2>${{symbol}}</h2>
                <div class="metric">
                    <span class="metric-label">Realistic Return</span>
                    <span class="metric-value">${{(data.realistic_return || 0).toFixed(0)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Win Rate</span>
                    <span class="metric-value">${{(data.win_rate || 0).toFixed(1)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Profit Factor</span>
                    <span class="metric-value">${{(data.profit_factor || 0).toFixed(2)}}x</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sharpe Ratio</span>
                    <span class="metric-value">${{(data.sharpe_ratio || 0).toFixed(2)}}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Risk-Reward</span>
                    <span class="metric-value">${{(data.risk_reward_ratio || 0).toFixed(2)}}x</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value">${{data.status}}</span>
                </div>
            `;
            document.getElementById(cardId).innerHTML = html;
        }}

        function renderSummaryCard(results) {{
            const btc = results.BTCUSDT || {{}};
            const eth = results.ETHUSDT || {{}};
            
            const avgReturn = ((btc.realistic_return || 0) + (eth.realistic_return || 0)) / 2;
            const avgWR = ((btc.win_rate || 0) + (eth.win_rate || 0)) / 2;
            const approved = Object.values(results).filter(r => r.status === 'APPROVED').length;
            
            const html = `
                <h2>📊 Portfolio Summary</h2>
                <div class="metric">
                    <span class="metric-label">Avg Return</span>
                    <span class="metric-value">${{avgReturn.toFixed(0)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Win Rate</span>
                    <span class="metric-value">${{avgWR.toFixed(1)}}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Models Approved</span>
                    <span class="metric-value">${{approved}}/2</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Model Features</span>
                    <span class="metric-value">75 Technical</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Deployment</span>
                    <span class="metric-value">APPROVED ✓</span>
                </div>
            `;
            document.getElementById('summaryCard').innerHTML = html;
        }}

        function renderWarnings(results) {{
            const warnings = [];
            
            Object.entries(results).forEach(([symbol, data]) => {{
                if (data.win_rate > 90) {{
                    warnings.push(`⚠️ ${{symbol}} win rate ${{data.win_rate.toFixed(1)}}% suggests overfitting. Expect 60-70% live.`);
                }}
            }});
            
            if (warnings.length > 0) {{
                document.getElementById('warningsContainer').style.display = 'block';
                document.getElementById('warningsContent').innerHTML = 
                    warnings.map(w => `<div style="margin-bottom: 5px;">${{w}}</div>`).join('');
            }}
        }}

        function renderCharts(results) {{
            const btc = results.BTCUSDT || {{}};
            const eth = results.ETHUSDT || {{}};
            
            // P&L Chart
            const ctx1 = document.getElementById('pnlChart').getContext('2d');
            new Chart(ctx1, {{
                type: 'bar',
                data: {{
                    labels: ['BTCUSDT', 'ETHUSDT'],
                    datasets: [{{
                        label: 'Realistic P&L ($)',
                        data: [btc.realistic_pnl || 0, eth.realistic_pnl || 0],
                        backgroundColor: 'rgba(0, 208, 132, 0.5)',
                        borderColor: 'rgba(0, 208, 132, 1)',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ labels: {{ color: '#e8edf5' }} }}
                    }},
                    scales: {{
                        y: {{
                            ticks: {{ color: '#e8edf5' }},
                            grid: {{ color: 'rgba(255,255,255,0.1)' }}
                        }},
                        x: {{
                            ticks: {{ color: '#e8edf5' }},
                            grid: {{ color: 'rgba(255,255,255,0.1)' }}
                        }}
                    }}
                }}
            }});
            
            // Metrics Chart
            const ctx2 = document.getElementById('metricsChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'radar',
                data: {{
                    labels: ['Win Rate', 'Profit Factor', 'Risk-Reward', 'Sharpe Ratio'],
                    datasets: [
                        {{
                            label: 'BTCUSDT',
                            data: [
                                btc.win_rate || 0,
                                (btc.profit_factor || 0) * 20,
                                (btc.risk_reward_ratio || 0) * 20,
                                (btc.sharpe_ratio || 0) * 10
                            ],
                            borderColor: 'rgba(61, 142, 248, 1)',
                            backgroundColor: 'rgba(61, 142, 248, 0.2)',
                            borderWidth: 2
                        }},
                        {{
                            label: 'ETHUSDT',
                            data: [
                                eth.win_rate || 0,
                                (eth.profit_factor || 0) * 20,
                                (eth.risk_reward_ratio || 0) * 20,
                                (eth.sharpe_ratio || 0) * 10
                            ],
                            borderColor: 'rgba(0, 208, 132, 1)',
                            backgroundColor: 'rgba(0, 208, 132, 0.2)',
                            borderWidth: 2
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ labels: {{ color: '#e8edf5' }} }}
                    }},
                    scales: {{
                        r: {{
                            grid: {{ color: 'rgba(255,255,255,0.1)' }},
                            ticks: {{ color: '#e8edf5' }}
                        }}
                    }}
                }}
            }});
        }}

        // Load on page ready
        renderDashboard();
    </script>
</body>
</html>
"""
    
    return html_content
