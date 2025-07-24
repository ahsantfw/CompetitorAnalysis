import sys
import os
import pandas as pd
import sys, os
print(sys.path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES

# Usage: python features/preprocess_csv_to_parquet.py data/yourfile.csv data/yourfile.parquet

def csv_to_parquet_dataset(csv_path, dataset_dir, chunksize=100_000):
    os.makedirs(dataset_dir, exist_ok=True)
    total_rows = 0
    for i, chunk in enumerate(pd.read_csv(csv_path, usecols=ESSENTIAL_COLUMNS, dtype=str, chunksize=chunksize)):
        for col, dtype in COLUMN_DTYPES.items():
            if col in chunk.columns:
                try:
                    chunk[col] = chunk[col].astype(dtype)
                except Exception:
                    pass
        chunk_file = os.path.join(dataset_dir, f"chunk_{i}.parquet")
        chunk.to_parquet(chunk_file, index=False)
        total_rows += len(chunk)
        print(f"[Chunk {i+1}] Processed {len(chunk)} rows into {chunk_file} (Total rows so far: {total_rows})")
    print(f"[DONE] Parquet dataset created at: {dataset_dir} | Total chunks: {i+1}, Total rows: {total_rows}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python features/preprocess_csv_to_parquet.py input.csv output_dataset_dir")
        sys.exit(1)
    csv_path = sys.argv[1]
    dataset_dir = sys.argv[2]
    csv_to_parquet_dataset(csv_path, dataset_dir) 