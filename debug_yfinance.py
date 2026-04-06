#!/usr/bin/env python
"""Debug yfinance data structure"""
import yfinance as yf
import pandas as pd

print("Downloading BTC-USD data (30 days, 1h interval)...")
data = yf.download('BTC-USD', period='30d', interval='1h', progress=False)

print(f"\n=== DATA STRUCTURE ===")
print(f"Type: {type(data)}")
print(f"Shape: {data.shape}")
print(f"Length: {len(data)}")
print(f"Empty: {data.empty if hasattr(data, 'empty') else 'N/A'}")
print(f"Columns: {list(data.columns)}")
print(f"Index type: {type(data.index)}")
print(f"Index (first 5): {list(data.index[:5])}")

print(f"\n=== FIRST ROWS ===")
print(data.head(3))

print(f"\n=== TEST ITERROWS ===")
count = 0
for idx, row in data.iterrows():
    count += 1
    if count <= 2:
        print(f"  Row {count}: idx={idx}, type(row)={type(row)}, Close={row['Close']}")

print(f"Total rows from iterrows: {count}")

print(f"\n=== TEST DIRECT ACCESS ===")
if len(data) > 0:
    print("data.iloc[0]:")
    print(data.iloc[0])
    print("\ndata.iloc[0].get('Close'):", data.iloc[0].get('Close', 'NOT FOUND'))
