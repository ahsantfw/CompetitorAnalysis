import sys
from core.loader import load_marketcheck_data
import pandas as pd

# Usage: python logic/basic_insights.py data/inventory_2025_07.csv

def main(file_path):
    print(f"\n🚗 Loading data from: {file_path}")
    columns = [
        'id', 'seller_name', 'mc_dealer_id', 'status_date', 'vin', 'make', 'model', 'body_type', 'city', 'state', 'zip'
    ]
    df = load_marketcheck_data(file_path, columns=columns)
    # Ensure correct types
    df['mc_dealer_id'] = pd.to_numeric(df['mc_dealer_id'], errors='coerce').astype('Int64')
    df['zip'] = pd.to_numeric(df['zip'], errors='coerce').astype('Int64')
    print(f"✅ Loaded {len(df):,} rows, {len(df.columns)} columns.")
    print(f"Columns: {list(df.columns)}\n")

    # Total sales (unique VINs)
    total_sales = df['vin'].nunique()
    print(f"Total vehicles sold (unique VINs): {total_sales:,}")

    # Top 10 Dealers
    print("\nTop 10 Dealers by Sales:")
    top_dealers = df.groupby(['mc_dealer_id', 'seller_name'])['vin'].nunique().reset_index(name='sales_count')
    print(top_dealers.sort_values('sales_count', ascending=False).head(10))

    # Top 10 Models
    print("\nTop 10 Models by Sales:")
    top_models = df.groupby(['make', 'model'])['vin'].nunique().reset_index(name='sales_count')
    print(top_models.sort_values('sales_count', ascending=False).head(10))

    # Top 10 Cities
    print("\nTop 10 Cities by Sales:")
    top_cities = df.groupby(['city', 'state'])['vin'].nunique().reset_index(name='sales_count')
    print(top_cities.sort_values('sales_count', ascending=False).head(10))

    print("\n--- Basic Insights Complete ---\n")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/inventory_2025_07.csv"
    main(file_path) 