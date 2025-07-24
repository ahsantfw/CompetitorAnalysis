import pandas as pd
import os
import glob
import time
from datetime import datetime
from core.main_record import update_main_record_from_feed, load_main_record
from core.sold_record import update_sold_record
from core.loader import load_inventory_csv
from core.config import RAW_DATA_PATH
from core.summarizer import update_dealer_sales_summary, update_dealer_sales_by_model

def cleanup_old_files(data_dir, keep_days=2):
    now = time.time()
    for f in glob.glob(os.path.join(data_dir, '*.csv')):
        if os.stat(f).st_mtime < now - keep_days * 86400:
            print(f"Deleting old file: {f}")
            os.remove(f)

def process_daily_feed(today_path, today_date):
    print(f"Processing daily feed: {today_path}")
    start_time = time.time()
    # Update main record from today's feed (chunked)
    main_df = update_main_record_from_feed(today_path)
    # Build set of all VINs from today's file (chunked, memory-safe)
    today_vins = set()
    sample_rows = None
    for i, chunk in enumerate(load_inventory_csv(today_path)):
        today_vins.update(chunk['vin'])
        if i == 0:
            sample_rows = chunk.head(100)
    # Use main_df for sold detection
    sold_record = update_sold_record(main_df, pd.DataFrame({'vin': list(today_vins)}), today_date)
    print(f"Sold cars updated: {len(sold_record)} total")
    # Update dealer summaries
    summary = update_dealer_sales_summary()
    by_model = update_dealer_sales_by_model()
    print(f"Dealer summary updated: {len(summary)} dealers, {len(by_model)} dealer-models")
    # Monitoring sample file
    monitor_path = "state/monitoring_sample.csv"
    monitor_rows = []
    # 100 sample rows from input, main, sold
    monitor_rows.append(pd.DataFrame({'section': 'input_today', **sample_rows}) if sample_rows is not None else pd.DataFrame())
    monitor_rows.append(pd.DataFrame({'section': 'main_record', **main_df.head(100)}))
    monitor_rows.append(pd.DataFrame({'section': 'sold_record', **sold_record.head(100)}))
    # Summary row
    elapsed = time.time() - start_time
    elapsed_min = round(elapsed / 60, 2)
    summary_row = pd.DataFrame([{
        'section': 'summary',
        'input_rows': len(today_vins),
        'main_record_rows': len(main_df),
        'sold_record_rows': len(sold_record),
        'dealers': len(summary),
        'dealer_models': len(by_model),
        'time_min': elapsed_min
    }])
    monitor_rows.append(summary_row)
    pd.concat(monitor_rows, ignore_index=True).to_csv(monitor_path, index=False)
    print(f"Monitoring sample written to {monitor_path}")
    print(f"Total ETL time: {elapsed_min} minutes")
    # Clean up old files
    cleanup_old_files(os.path.dirname(today_path), keep_days=2)
    print("ETL complete.")

if __name__ == "__main__":
    # Example usage: process today's file
    today_path = os.path.join(RAW_DATA_PATH, "inventory_2025_07_24.csv")
    today_date = "2025-07-24"
    process_daily_feed(today_path, today_date) 