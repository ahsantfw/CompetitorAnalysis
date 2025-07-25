import pandas as pd
import os
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.main_record import load_main_record
from core.sold_record import load_sold_record

SUMMARY_PATH = "state/dealer_sales_summary.parquet"
BY_MODEL_PATH = "state/dealer_sales_by_model.parquet"

# Update dealer sales summary (total and sold cars by dealer)
def update_dealer_sales_summary():
    print("[SUMMARY] Loading main and sold records...")
    main_df = load_main_record()
    sold_df = load_sold_record()
    print(f"[SUMMARY] Main record rows: {len(main_df)}, Sold record rows: {len(sold_df)}")
    # Deduplicate by VIN in both
    main_df = main_df.drop_duplicates('vin', keep='first')
    sold_df = sold_df.drop_duplicates('vin', keep='first')
    # Total inventory by dealer
    inv_summary = main_df.groupby('mc_dealer_id').size().reset_index(name='active_inventory')
    # Total sold by dealer
    sold_summary = sold_df.groupby('mc_dealer_id').size().reset_index(name='total_sold')
    # Merge
    summary = pd.merge(inv_summary, sold_summary, on='mc_dealer_id', how='outer').fillna(0)
    summary['active_inventory'] = summary['active_inventory'].astype(int)
    summary['total_sold'] = summary['total_sold'].astype(int)
    # Deduplicate by dealer
    summary = summary.drop_duplicates('mc_dealer_id', keep='first')
    os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
    summary.to_parquet(SUMMARY_PATH, index=False)
    print(f"[SUMMARY] Dealer sales summary saved. Dealers: {len(summary)}")
    return summary

# Update dealer sales by model (sold cars)
def update_dealer_sales_by_model():
    print("[SUMMARY] Loading sold record for by-model summary...")
    sold_df = load_sold_record()
    print(f"[SUMMARY] Sold record rows: {len(sold_df)}")
    # Deduplicate by VIN
    sold_df = sold_df.drop_duplicates('vin', keep='first')
    by_model = sold_df.groupby(['mc_dealer_id', 'neo_make', 'neo_model']).size().reset_index(name='sales_count')
    # Deduplicate by dealer/make/model
    by_model = by_model.drop_duplicates(['mc_dealer_id', 'neo_make', 'neo_model'], keep='first')
    os.makedirs(os.path.dirname(BY_MODEL_PATH), exist_ok=True)
    by_model.to_parquet(BY_MODEL_PATH, index=False)
    print(f"[SUMMARY] Dealer sales by model saved. Dealer-models: {len(by_model)}")
    return by_model 