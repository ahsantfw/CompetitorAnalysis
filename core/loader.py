import pandas as pd
import os
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_inventory_csv(path, chunksize=100_000):
    # CSV loader (legacy)
    for chunk in pd.read_csv(path, usecols=ESSENTIAL_COLUMNS, chunksize=chunksize, dtype=str):
        for col, dtype in COLUMN_DTYPES.items():
            if col in chunk.columns:
                try:
                    chunk[col] = chunk[col].astype(dtype)
                except Exception:
                    pass
        yield chunk

def load_parquet_dataset(dataset_dir):
    # Loads each Parquet file in a dataset directory as a chunk
    files = sorted([f for f in os.listdir(dataset_dir) if f.endswith('.parquet')])
    for f in files:
        chunk = pd.read_parquet(os.path.join(dataset_dir, f))
        yield chunk

def parallel_chunk_process(dataset_dir, func, max_workers=4):
    # Applies func(chunk_path) in parallel to all Parquet chunk files, returns list of results
    files = sorted([os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir) if f.endswith('.parquet')])
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, f) for f in files]
        for future in as_completed(futures):
            results.append(future.result())
    return results 