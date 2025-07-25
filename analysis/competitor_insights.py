import pandas as pd
import os

SUMMARY_PATH = "state/dealer_sales_summary.parquet"
BY_MODEL_PATH = "state/dealer_sales_by_model.parquet"
RAW_PATH = "state/main_record.parquet"  # For dealer info lookup

# Simple zip code group filter (can be replaced with radius logic)
def dealers_in_zip_group(raw_df, target_zip, zip_group=0):
    # For now, just match zip exactly or within +/- zip_group
    return raw_df[(raw_df['zip'] >= target_zip - zip_group) & (raw_df['zip'] <= target_zip + zip_group)]['mc_dealer_id'].unique()

def competitor_analysis(make, model, target_zip, client_dealer_id, zip_group=0):
    print("[ANALYSIS] Loading summary and raw data...")
    if not os.path.exists(BY_MODEL_PATH) or not os.path.exists(RAW_PATH):
        print("Required summary or raw file not found.")
        return
    by_model = pd.read_parquet(BY_MODEL_PATH)
    raw_df = pd.read_parquet(RAW_PATH)
    print(f"[ANALYSIS] Loaded by_model rows: {len(by_model)}, raw_df rows: {len(raw_df)}")
    # Deduplicate
    by_model = by_model.drop_duplicates(['mc_dealer_id', 'neo_make', 'neo_model'], keep='first')
    raw_df = raw_df.drop_duplicates('vin', keep='first')
    # Find dealers in zip group
    dealers = dealers_in_zip_group(raw_df, target_zip, zip_group)
    print(f"[ANALYSIS] Dealers in zip group: {len(dealers)}")
    # Filter by make/model and dealers in area (sold)
    # Use neo_make, neo_model, neo_year for filtering
    filtered = by_model[(by_model['neo_make'].str.lower() == make.lower()) &
                        (by_model['neo_model'].str.lower() == model.lower()) &
                        (by_model['mc_dealer_id'].isin(dealers))]
    print(f"[ANALYSIS] Filtered by_model rows: {len(filtered)}")
    # Inventory for make/model by dealer
    inv = raw_df[(raw_df['neo_make'].str.lower() == make.lower()) &
                 (raw_df['neo_model'].str.lower() == model.lower()) &
                 (raw_df['mc_dealer_id'].isin(dealers))]
    print(f"[ANALYSIS] Filtered inventory rows: {len(inv)}")
    inv_counts = inv.groupby('mc_dealer_id').size().reset_index(name='current_inventory')
    # Dealer info lookup (enriched)
    dealer_info_cols = ['mc_dealer_id', 'seller_name', 'city', 'state', 'zip']
    for col in [
        'mc_dealership_group_name', 'dealer_type', 'source',
        'latitude', 'longitude', 'seller_phone', 'seller_email',
        'car_seller_name', 'car_address', 'photo_links']:
        if col in raw_df.columns:
            dealer_info_cols.append(col)
    dealer_info = raw_df.drop_duplicates('mc_dealer_id')[dealer_info_cols]
    merged = filtered.merge(dealer_info, on='mc_dealer_id', how='left').merge(inv_counts, on='mc_dealer_id', how='left')
    merged['current_inventory'] = merged['current_inventory'].fillna(0).astype(int)
    print(f"[ANALYSIS] Merged competitor analysis rows: {len(merged)}")
    # Show top competitors
    print(f"\nDealers in zip group {target_zip} +/- {zip_group} who sold {make} {model}:")
    display_cols = ['seller_name', 'city', 'state', 'zip', 'current_inventory', 'sales_count']
    for col in [
        'mc_dealership_group_name', 'dealer_type', 'source',
        'latitude', 'longitude', 'seller_phone', 'seller_email',
        'car_seller_name', 'car_address', 'photo_links']:
        if col in merged.columns:
            display_cols.append(col)
    print(merged.sort_values('sales_count', ascending=False)[display_cols].head(10))
    # Show client dealer's performance
    client_row = merged[merged['mc_dealer_id'] == client_dealer_id]
    if not client_row.empty:
        print(f"\nYour dealership ({client_row.iloc[0]['seller_name']}) has {client_row.iloc[0]['current_inventory']} {make} {model} in inventory and sold {client_row.iloc[0]['sales_count']} in this area.")
        if 'mc_dealership_group_name' in client_row.columns:
            print(f"Dealer group: {client_row.iloc[0].get('mc_dealership_group_name', '')}")
        if 'dealer_type' in client_row.columns:
            print(f"Dealer type: {client_row.iloc[0].get('dealer_type', '')}")
    else:
        print("\nYour dealership did not sell this make/model in this area in the selected period.")

def main():
    # Example usage: Chevy Silverado in zip 90210, client dealer_id 1234567
    make = input("Enter make (e.g., Chevrolet): ")
    model = input("Enter model (e.g., Silverado 1500): ")
    target_zip = int(input("Enter target zip code: "))
    client_dealer_id = int(input("Enter your dealer_id: "))
    zip_group = int(input("Enter zip code group/radius (e.g., 0 for exact, 10 for +/-10): "))
    competitor_analysis(make, model, target_zip, client_dealer_id, zip_group)

if __name__ == "__main__":
    main() 