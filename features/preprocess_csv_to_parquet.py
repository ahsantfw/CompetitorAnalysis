import pandas as pd
import os
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES

# Usage: python features/preprocess_csv_to_parquet.py data/yourfile.csv data/yourfile.parquet

def csv_to_parquet(csv_path, parquet_path, chunksize=100_000):
    first = True
    for chunk in pd.read_csv(csv_path, usecols=ESSENTIAL_COLUMNS, dtype=str, chunksize=chunksize):
        # Type cast columns as per config
        for col, dtype in COLUMN_DTYPES.items():
            if col in chunk.columns:
                try:
                    chunk[col] = chunk[col].astype(dtype)
                except Exception:
                    pass
        if first:
            chunk.to_parquet(parquet_path, index=False)
            first = False
        else:
            # Append to Parquet (using pyarrow engine)
            chunk.to_parquet(parquet_path, index=False, append=True, engine='pyarrow')
        print(f"Processed {len(chunk)} rows...")
    print(f"Conversion complete: {parquet_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python features/preprocess_csv_to_parquet.py input.csv output.parquet")
        sys.exit(1)
    csv_path = sys.argv[1]
    parquet_path = sys.argv[2]
    csv_to_parquet(csv_path, parquet_path) 