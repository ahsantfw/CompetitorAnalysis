import pandas as pd
from core.config import CHUNK_SIZE

def load_csv_chunked(path, columns=None, dtypes=None, date_col=None, start=None, end=None):
    chunks = []
    for chunk in pd.read_csv(path, usecols=columns, dtype=dtypes, low_memory=False, chunksize=CHUNK_SIZE, parse_dates=[date_col] if date_col else None):
        if date_col and (start or end):
            if start:
                chunk = chunk[chunk[date_col] >= start]
            if end:
                chunk = chunk[chunk[date_col] <= end]
        chunks.append(chunk)
    if chunks:
        return pd.concat(chunks, ignore_index=True)
    return pd.DataFrame(columns=columns) 