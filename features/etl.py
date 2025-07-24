import pandas as pd
import os
import glob
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from core.main_record import update_main_record_from_feed, load_main_record
from core.sold_record import update_sold_record
from core.loader import load_inventory_csv, load_parquet_dataset, parallel_chunk_process
from core.config import RAW_DATA_PATH
from core.summarizer import update_dealer_sales_summary, update_dealer_sales_by_model

def cleanup_old_files(data_dir, keep_days=2):
    print(f"[CLEANUP] Checking for old files in {data_dir} (keep {keep_days} days)...")
    now = time.time()
    deleted = 0
    for f in glob.glob(os.path.join(data_dir, '*.csv')):
        if os.stat(f).st_mtime < now - keep_days * 86400:
            print(f"[CLEANUP] Deleting old file: {f}")
            os.remove(f)
            deleted += 1
    print(f"[CLEANUP] Done. Deleted {deleted} old files.")

def process_daily_feed(today_path, today_date, max_workers=4):
    print(f"[ETL] Processing daily feed: {today_path}")
    start_time = time.time()
    # Update main record from today's feed (chunked, parallel for Parquet)
    main_df = update_main_record_from_feed(today_path, max_workers=max_workers)
    print(f"[ETL] Main record updated. Rows: {len(main_df)}")
    # Choose loader based on file type
    if os.path.isdir(today_path) or today_path.endswith('.parquet/'):
        # Parallel processing for Parquet dataset
        def get_vins(chunk_path):
            chunk = pd.read_parquet(chunk_path)
            return set(chunk['vin'])
        def get_sample_rows(chunk_path):
            chunk = pd.read_parquet(chunk_path)
            return chunk.head(100)
        # VIN collection
        vin_sets = parallel_chunk_process(today_path, get_vins, max_workers=max_workers)
        today_vins = set().union(*vin_sets)
        # Sample rows (just from the first chunk)
        chunk_files = sorted([os.path.join(today_path, f) for f in os.listdir(today_path) if f.endswith('.parquet')])
        sample_rows = pd.read_parquet(chunk_files[0]).head(100) if chunk_files else None
    else:
        # Sequential for CSV
        today_vins = set()
        sample_rows = None
        for i, chunk in enumerate(load_inventory_csv(today_path)):
            today_vins.update(chunk['vin'])
            if i == 0:
                sample_rows = chunk.head(100)
    print(f"[ETL] VIN collection complete. Unique VINs today: {len(today_vins)}")
    # Use main_df for sold detection
    sold_record = update_sold_record(main_df, pd.DataFrame({'vin': list(today_vins)}), today_date)
    print(f"[ETL] Sold record updated. Rows: {len(sold_record)}")
    # Update dealer summaries
    summary = update_dealer_sales_summary()
    print(f"[ETL] Dealer sales summary updated. Dealers: {len(summary)}")
    by_model = update_dealer_sales_by_model()
    print(f"[ETL] Dealer sales by model updated. Dealer-models: {len(by_model)}")
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
    print(f"[ETL] Monitoring sample written to {monitor_path}")
    print(f"[ETL] Total ETL time: {elapsed_min} minutes")
    # Clean up old files
    cleanup_old_files(os.path.dirname(today_path), keep_days=2)
    print("[ETL] ETL complete.")

if __name__ == "__main__":
    # Usage: python features/etl.py [input_path] [date] [max_workers]
    if len(sys.argv) >= 2:
        today_path = sys.argv[1]
    else:
        today_path = os.path.join(RAW_DATA_PATH, "filtered_mc_new_20250723_dataset")  # Default to Parquet dataset dir
    if len(sys.argv) >= 3:
        today_date = sys.argv[2]
    else:
        today_date = "2025-07-23"
    if len(sys.argv) >= 4:
        max_workers = int(sys.argv[3])
    else:
        max_workers = 4
    process_daily_feed(today_path, today_date, max_workers=max_workers) 