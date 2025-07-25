import pandas as pd
import os
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from datetime import datetime
from core.main_record import load_main_record
from core.sold_record import update_sold_record
from core.loader import load_inventory_csv, load_parquet_dataset, parallel_chunk_process
from core.config import RAW_DATA_PATH
from core.summarizer import update_dealer_sales_summary, update_dealer_sales_by_model

def process_analysis(today_path, today_date, max_workers=4):
    print(f"[POST-ETL] Running analysis only. Main record will not be updated.")
    start_time = time.time()
    main_df = load_main_record()
    print(f"[POST-ETL] Main record loaded. Rows: {len(main_df)}")
    # Collect today's VINs (for sold detection)
    if os.path.isdir(today_path) or today_path.endswith('.parquet/'):
        def get_vins(chunk_path):
            chunk = pd.read_parquet(chunk_path)
            return set(chunk['vin'])
        vin_sets = []
        for batch in parallel_chunk_process(today_path, get_vins, max_workers=max_workers):
            vin_sets.extend(batch)
        today_vins = set().union(*vin_sets)
    else:
        today_vins = set()
        for i, chunk in enumerate(load_inventory_csv(today_path)):
            today_vins.update(chunk['vin'])
    print(f"[POST-ETL] VIN collection complete. Unique VINs today: {len(today_vins)}")
    # Update sold record
    sold_record = update_sold_record(main_df, pd.DataFrame({'vin': list(today_vins)}), today_date)
    print(f"[POST-ETL] Sold record updated. Rows: {len(sold_record)}")
    # Update dealer summaries
    summary = update_dealer_sales_summary()
    print(f"[POST-ETL] Dealer sales summary updated. Dealers: {len(summary)}")
    by_model = update_dealer_sales_by_model()
    print(f"[POST-ETL] Dealer sales by model updated. Dealer-models: {len(by_model)}")
    # Monitoring sample file
    monitor_path = "state/monitoring_sample_post.csv"
    monitor_rows = []
    monitor_rows.append(pd.DataFrame({'section': 'main_record', **main_df.head(100)}))
    monitor_rows.append(pd.DataFrame({'section': 'sold_record', **sold_record.head(100)}))
    elapsed = time.time() - start_time
    elapsed_min = round(elapsed / 60, 2)
    summary_row = pd.DataFrame([{
        'section': 'summary',
        'main_record_rows': len(main_df),
        'sold_record_rows': len(sold_record),
        'dealers': len(summary),
        'dealer_models': len(by_model),
        'time_min': elapsed_min
    }])
    monitor_rows.append(summary_row)
    pd.concat(monitor_rows, ignore_index=True).to_csv(monitor_path, index=False)
    print(f"[POST-ETL] Monitoring sample written to {monitor_path}")
    print(f"[POST-ETL] Total analysis time: {elapsed_min} minutes")
    print("[POST-ETL] Analysis complete.")

if __name__ == "__main__":
    # Usage: python features/etl_post_main.py [input_path] [date] [max_workers]
    if len(sys.argv) >= 2:
        today_path = sys.argv[1]
    else:
        today_path = os.path.join(RAW_DATA_PATH, "filtered_mc_new_20250723_dataset")
    if len(sys.argv) >= 3:
        today_date = sys.argv[2]
    else:
        today_date = "2025-07-23"
    if len(sys.argv) >= 4:
        max_workers = int(sys.argv[3])
    else:
        max_workers = 4
    process_analysis(today_path, today_date, max_workers=max_workers) 