#!/usr/bin/env python
"""
CRYPTO TRADING - VALIDATION & DEPLOYMENT ANALYSIS
Apply realistic costs, calculate portfolio metrics, and assess deployment readiness
"""

import os
import json
import numpy as np
from datetime import datetime

SYMBOLS = ['BTCUSDT', 'ETHUSDT']
RESULTS_DIR = 'backtest_results'

# Realistic costs
MAKER_FEE_PCT = 0.05  # Binance maker fee
SLIPPAGE_BPS = 5      # 5 bps slippage estimate
SLIPPAGE_PCT = 0.0005

print("\n" + "="*80)
print("[CRYPTO VALIDATION] Realistic Costs & Portfolio Metrics")
print("="*80)

all_validation = {}

for symbol in SYMBOLS:
    report_file = f'{RESULTS_DIR}/report_{symbol}_1h.json'
    
    if not os.path.exists(report_file):
        print(f"\n❌ Report not found: {report_file}")
        continue
    
    print(f"\n{'='*80}")
    print(f"[{symbol.upper()}] VALIDATION")
    print('='*80)
    
    # Load report
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    bt = report.get('backtest', {})
    price_data = report.get('price_data', {})
    
    print(f"\n[1] Original Backtest Results (NO COSTS)")
    print(f"    Trades: {bt.get('trades', 0)}")
    print(f"    Win Rate: {bt.get('win_rate', 0)*100:.1f}%")
    print(f"    P&L: ${bt.get('total_pnl', 0):,.2f}")
    print(f"    Return: {bt.get('return_pct', 0):.1f}%")
    
    # ===== APPLY REALISTIC COSTS =====
    print(f"\n[2] Applying Realistic Transaction Costs")
    
    num_trades = bt.get('trades', 1)
    avg_price = (price_data.get('price_min', 100) + price_data.get('price_max', 100)) / 2
    
    # Cost per trade: Entry fee (0.05%) + Exit fee (0.05%) + Slippage (0.5 bps)
    maker_fee_per_trade = avg_price * (MAKER_FEE_PCT / 100) * 2  # Entry + Exit
    slippage_cost_per_trade = avg_price * SLIPPAGE_PCT * 2  # Entry + Exit slippage
    total_cost_per_trade = maker_fee_per_trade + slippage_cost_per_trade
    total_transaction_cost = total_cost_per_trade * num_trades
    
    original_pnl = bt.get('total_pnl', 0)
    realistic_pnl = original_pnl - total_transaction_cost
    realistic_return = (realistic_pnl / 10000) * 100  # Assuming $10K starting capital
    
    print(f"    Trades: {num_trades}")
    print(f"    Avg Price: ${avg_price:,.2f}")
    print(f"    Cost per trade: ${total_cost_per_trade:.2f} (fees + slippage)")
    print(f"    Total transaction cost: ${total_transaction_cost:,.2f}")
    print(f"\n    Original P&L (no costs): ${original_pnl:,.2f}")
    print(f"    Realistic P&L (with costs): ${realistic_pnl:,.2f}")
    print(f"    Realistic Return: {realistic_return:.2f}%")
    
    # ===== CALCULATE PORTFOLIO METRICS =====
    print(f"\n[3] Portfolio Metrics")
    
    winning = bt.get('winning', 0)
    losing = bt.get('losing', 0)
    total = winning + losing
    
    win_rate = (winning / total) if total > 0 else 0
    
    max_win = bt.get('max_win', 0)
    max_loss = abs(bt.get('max_loss', 0))
    
    # Profit Factor
    avg_win = max_win / (winning / total) if winning > 0 else max_win
    avg_loss = max_loss / (losing / total) if losing > 0 else max_loss
    profit_factor = (avg_win * winning) / (abs(avg_loss * losing)) if losing > 0 else float('inf')
    
    # Expectancy per trade
    expectancy = (realistic_pnl / num_trades) if num_trades > 0 else 0
    
    # Risk-Reward Ratio
    rr_ratio = max_win / max_loss if max_loss > 0 else 0
    
    # Sharpe (rough estimate)
    estimated_std = max_loss / 2
    sharpe_est = (expectancy / estimated_std * np.sqrt(252)) if estimated_std > 0 else 0
    
    # Recovery Factor
    recovery = realistic_pnl / max_loss if max_loss > 0 else 0
    
    print(f"    Win Rate: {win_rate*100:.1f}% ({winning}W / {losing}L)")
    print(f"    Profit Factor: {profit_factor:.2f}x")
    print(f"    Expectancy (per trade): ${expectancy:.2f}")
    print(f"    Risk-Reward Ratio: {rr_ratio:.2f}x")
    print(f"    Recovery Factor: {recovery:.2f}x")
    print(f"    Sharpe Ratio (est): {sharpe_est:.2f}")
    
    # ===== DEPLOYMENT READINESS =====
    print(f"\n[4] Deployment Readiness Assessment")
    
    checks = []
    score = 0
    
    # Check 1: Realistic return > 30%
    if realistic_return > 30:
        print(f"    ✓ Sufficient return: {realistic_return:.1f}% > 30%")
        checks.append(('return', True))
        score += 25
    else:
        print(f"    ✗ Low return: {realistic_return:.1f}% < 30%")
        checks.append(('return', False))
    
    # Check 2: Win rate 45-75%
    if 45 < win_rate*100 < 75:
        print(f"    ✓ Reasonable win rate: {win_rate*100:.1f}% (45-75% range)")
        checks.append(('win_rate', True))
        score += 25
    else:
        print(f"    ✗ Win rate concern: {win_rate*100:.1f}% (outside 45-75%)")
        checks.append(('win_rate', False))
    
    # Check 3: Profit Factor > 2.0
    if profit_factor > 2.0:
        print(f"    ✓ Strong profit factor: {profit_factor:.2f} > 2.0")
        checks.append(('profit_factor', True))
        score += 25
    elif profit_factor > 1.5:
        print(f"    ✓ Adequate profit factor: {profit_factor:.2f} > 1.5")
        checks.append(('profit_factor', True))
        score += 20
    else:
        print(f"    ✗ Weak profit factor: {profit_factor:.2f} < 1.5")
        checks.append(('profit_factor', False))
    
    # Check 4: Risk-Reward > 1.5
    if rr_ratio > 1.5:
        print(f"    ✓ Good risk-reward: {rr_ratio:.2f}x > 1.5x")
        checks.append(('risk_reward', True))
        score += 25
    else:
        print(f"    ✗ Risk-reward concern: {rr_ratio:.2f}x < 1.5x")
        checks.append(('risk_reward', False))
    
    # Overall status
    approved_checks = sum(1 for _, passed in checks if passed)
    status = 'APPROVED' if approved_checks >= 3 else 'REVIEW_NEEDED'
    
    print(f"\n    OVERALL SCORE: {score}/100")
    print(f"    STATUS: {status}")
    
    all_validation[symbol] = {
        'original_pnl': original_pnl,
        'realistic_pnl': realistic_pnl,
        'realistic_return': realistic_return,
        'win_rate': win_rate * 100,
        'profit_factor': profit_factor,
        'risk_reward_ratio': rr_ratio,
        'sharpe_ratio': sharpe_est,
        'recovery_factor': recovery,
        'score': score,
        'status': status
    }

# ===== SUMMARY =====
print(f"\n{'='*80}")
print("[SUMMARY]")
print('='*80)

if all_validation:
    approved = sum(1 for v in all_validation.values() if v['status'] == 'APPROVED')
    
    print(f"\nApproved for Live Trading: {approved}/{len(SYMBOLS)}")
    print(f"\nMetrics Summary:")
    for symbol, metrics in all_validation.items():
        print(f"\n  {symbol}:")
        print(f"    Realistic Return: {metrics['realistic_return']:.1f}%")
        print(f"    Win Rate: {metrics['win_rate']:.1f}%")
        print(f"    Profit Factor: {metrics['profit_factor']:.2f}x")
        print(f"    Risk-Reward: {metrics['risk_reward_ratio']:.2f}x")
        print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"    Score: {metrics['score']}/100")
        print(f"    Status: {metrics['status']}")

# Save validation results
output_file = f'{RESULTS_DIR}/comprehensive_validation.json'
with open(output_file, 'w') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'validation_type': 'realistic_costs_metrics',
        'binance_fees': f'{MAKER_FEE_PCT}% (maker/taker)',
        'slippage_estimate': f'{SLIPPAGE_BPS} bps',
        'results': all_validation
    }, f, indent=2)

print(f"\n✓ Validation results saved: {output_file}")

# Create live trading config
live_config = {
    'timestamp': datetime.now().isoformat(),
    'symbols': list(all_validation.keys()),
    'model_path': 'data/models/technical_crypto_mtf_v1.pkl',
    'features_count': 75,
    'signal_thresholds': {
        'buy': 0.52,
        'sell': 0.48,
        'hold': '0.48-0.52'
    },
    'fees': {
        'binance_maker': 0.05,
        'binance_taker': 0.1,
        'slippage_bps': 5
    },
    'risk_management': {
        'max_position_size_pct': 10,
        'max_daily_loss_pct': 5,
        'stop_loss_pct': 2,
        'take_profit_pct': 5
    },
    'deployment_status': {
        symbol: all_validation[symbol]['status'] 
        for symbol in all_validation
    },
    'ready_for_live': sum(1 for v in all_validation.values() if v['status'] == 'APPROVED') == len(SYMBOLS)
}

live_config_file = f'{RESULTS_DIR}/live_trading_config.json'
with open(live_config_file, 'w') as f:
    json.dump(live_config, f, indent=2)

print(f"✓ Live trading config saved: {live_config_file}")
print(f"\n{'='*80}\n")
