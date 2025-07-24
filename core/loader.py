import pandas as pd
from core.config import ESSENTIAL_COLUMNS, COLUMN_DTYPES

def load_inventory_csv(path, chunksize=100_000):
    for chunk in pd.read_csv(path, usecols=ESSENTIAL_COLUMNS, chunksize=chunksize, dtype=str):
        # Type cast columns as per config
        for col, dtype in COLUMN_DTYPES.items():
            if col in chunk.columns:
                try:
                    chunk[col] = chunk[col].astype(dtype)
                except Exception:
                    pass  # fallback: keep as string if conversion fails
        yield chunk 