import pandas as pd
import os

SUMMARY_PATH = "state/dealer_sales_summary.parquet"
BY_MODEL_PATH = "state/dealer_sales_by_model.parquet"

# Load summaries
def load_summaries():
    if not os.path.exists(SUMMARY_PATH):
        print(f"Summary file not found: {SUMMARY_PATH}")
        return None, None
    summary = pd.read_parquet(SUMMARY_PATH)
    by_model = pd.read_parquet(BY_MODEL_PATH) if os.path.exists(BY_MODEL_PATH) else None
    return summary, by_model

def print_top_dealers(summary, top_n=10):
    print("\nTop Dealers by Total Sold:")
    print(summary.sort_values('total_sold', ascending=False).head(top_n)[['mc_dealer_id', 'active_inventory', 'total_sold']])
    print("\nTop Dealers by Active Inventory:")
    print(summary.sort_values('active_inventory', ascending=False).head(top_n)[['mc_dealer_id', 'active_inventory', 'total_sold']])

def main():
    summary, by_model = load_summaries()
    if summary is None:
        return
    print_top_dealers(summary)
    # Add more business analysis as needed

if __name__ == "__main__":
    main() 