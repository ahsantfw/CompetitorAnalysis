import pandas as pd

def aggregate_sales(df):
    total = df['vin'].nunique()
    by_make_model = df.groupby(['make', 'model', 'inventory_type'])['vin'].nunique().reset_index(name='sales_count')
    return total, by_make_model

def precompute_dealer_stats(df):
    # Ensure status_date is datetime
    df['status_date'] = pd.to_datetime(df['status_date'], errors='coerce')
    # Only keep new cars (should already be filtered, but double-check)
    if 'inventory_type' in df.columns:
        df = df[df['inventory_type'].str.lower() == 'new']
    # Ensure mc_dealer_id is int
    if 'mc_dealer_id' in df.columns:
        df['mc_dealer_id'] = pd.to_numeric(df['mc_dealer_id'], errors='coerce').astype('Int64')
    # Compute period_start as first day of month
    df['period_start'] = df['status_date'].values.astype('datetime64[M]')
    df['period_end'] = df['period_start'] + pd.offsets.MonthEnd(0)
    # Normalize types before groupby
    df['mc_dealer_id'] = pd.to_numeric(df['mc_dealer_id'], errors='coerce').astype(int)
    df['period_start'] = pd.to_datetime(df['status_date']).dt.to_period('M').dt.to_timestamp()
    df['make'] = df['make'].astype(str).str.strip().str.lower()
    df['model'] = df['model'].astype(str).str.strip().str.lower()
    df['inventory_type'] = df['inventory_type'].astype(str).str.strip().str.lower()

    # Dealer sales summary: count all rows (not just unique VINs)
    summary = df.groupby(['mc_dealer_id', 'period_start'], as_index=False).agg(
        total_sales=('vin', 'count'),
        new_sales=('inventory_type', lambda x: (x == 'new').sum())
    )
    summary = summary.rename(columns={'mc_dealer_id': 'dealer_id'})
    summary['dealer_id'] = summary['dealer_id'].astype(int)
    summary['period_end'] = pd.to_datetime(summary['period_start']) + pd.offsets.MonthEnd(0)
    summary['last_updated'] = pd.Timestamp.now()

    # Dealer sales by model: count all rows
    by_model = df.groupby(['mc_dealer_id', 'period_start', 'make', 'model', 'inventory_type'], as_index=False).agg(
        sales_count=('vin', 'count')
    )
    by_model = by_model.rename(columns={'mc_dealer_id': 'dealer_id'})
    by_model['dealer_id'] = by_model['dealer_id'].astype(int)
    by_model['period_start'] = pd.to_datetime(by_model['period_start'])
    by_model['period_end'] = by_model['period_start'] + pd.offsets.MonthEnd(0)
    by_model['last_updated'] = pd.Timestamp.now()

    return summary, by_model 