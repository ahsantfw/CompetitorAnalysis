import pandas as pd
import os
from core.main_record import load_main_record
from core.sold_record import load_sold_record

SUMMARY_PATH = "state/dealer_sales_summary.parquet"
BY_MODEL_PATH = "state/dealer_sales_by_model.parquet"

# Update dealer sales summary (total and sold cars by dealer)
def update_dealer_sales_summary():
    main_df = load_main_record()
    sold_df = load_sold_record()
    # Total inventory by dealer
    inv_summary = main_df.groupby('mc_dealer_id').size().reset_index(name='active_inventory')
    # Total sold by dealer
    sold_summary = sold_df.groupby('mc_dealer_id').size().reset_index(name='total_sold')
    # Merge
    summary = pd.merge(inv_summary, sold_summary, on='mc_dealer_id', how='outer').fillna(0)
    summary['active_inventory'] = summary['active_inventory'].astype(int)
    summary['total_sold'] = summary['total_sold'].astype(int)
    summary.to_parquet(SUMMARY_PATH, index=False)
    return summary

# Update dealer sales by model (sold cars)
def update_dealer_sales_by_model():
    sold_df = load_sold_record()
    by_model = sold_df.groupby(['mc_dealer_id', 'make', 'model']).size().reset_index(name='sales_count')
    by_model.to_parquet(BY_MODEL_PATH, index=False)
    return by_model 