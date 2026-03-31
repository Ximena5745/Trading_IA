import pandas as pd
from pathlib import Path
files = sorted(Path('data/raw').glob('*.parquet'))
print('Archivos descargados:', len(files))
for f in files:
    df = pd.read_parquet(f)
    print(f.name, '| rows:', len(df), 'range', df['timestamp'].min(), 'a', df['timestamp'].max())
